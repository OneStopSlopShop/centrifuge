"""
Drive Claude Code (subprocess) instead of the Anthropic API.

Useful for users who have Claude Code installed (Pro / Max / Team plan) but
no Anthropic API key.  The work is done by the `serum-preset-builder` and
`sound-design-expert` subagents defined in `.claude/agents/`.
"""

from __future__ import annotations

import json
import queue
import shutil
import subprocess
import threading
import time
from pathlib import Path
from typing import Any

DEFAULT_MAX_TURNS = 8
DEFAULT_TIMEOUT_S = 600


def check_claude_available() -> str:
    """Return the path to the `claude` CLI, or raise with install instructions."""
    p = shutil.which("claude")
    if not p:
        raise RuntimeError(
            "`claude` CLI not found on PATH. "
            "Install Claude Code from https://claude.com/claude-code "
            "or use --local for the offline algorithmic mode."
        )
    return p


def generate_preset_noapi(
    description: str,
    output_path: Path,
    audio_path: Path | None = None,
    base_factory: Path | None = None,
    max_turns: int = DEFAULT_MAX_TURNS,
    timeout_s: int = DEFAULT_TIMEOUT_S,
    progress: Any = None,
) -> Path:
    """
    Invoke Claude Code to build a preset via the serum-preset-builder subagent.

    If `audio_path` is provided, librosa features are extracted in-process and
    injected into the prompt so the sound-design-expert subagent can refine
    the recipe based on the reference audio.

    Returns the output path on success; raises RuntimeError otherwise.
    """
    from centrifuge.progress import null_progress
    progress = progress or null_progress()

    check_claude_available()
    output_path = Path(output_path).resolve()
    output_path.parent.mkdir(parents=True, exist_ok=True)

    audio_clause = ""
    if audio_path is not None:
        progress.step("Extract audio features (librosa)")
        from centrifuge.audio import extract_features
        features = extract_features(audio_path)
        progress.update(f"{len(features)} features")
        progress.log(
            f"centroid={features.get('spectral_centroid_hz', '?')}Hz "
            f"attack={features.get('attack_time_ms', '?')}ms "
            f"harmonicity={features.get('harmonicity', '?')}"
        )
        audio_clause = (
            "\n\nReference audio features (extracted with librosa from "
            f"{audio_path}):\n"
            f"```json\n{json.dumps(features, indent=2)}\n```\n"
            "Use these to refine the recipe — see the sound-design-expert "
            "agent's audio interpretation guide."
        )

    base_clause = f"\nBase factory preset: {base_factory}" if base_factory else ""
    prompt = (
        "Build a Serum 2 preset using exactly two subagent calls in sequence — "
        "do not deviate.\n\n"
        f"Description: {description}{audio_clause}\n"
        f"Output path (absolute): {output_path}{base_clause}\n\n"
        "Step 1 — call `sound-design-expert` ONCE via the Task tool. Pass the "
        "description verbatim, plus the audio features block if present. Wait "
        "for the recipe JSON.\n\n"
        "Step 2 — call `serum-preset-builder` ONCE via the Task tool. In the "
        "prompt give it: (a) the recipe JSON from step 1, (b) the absolute "
        "output path above, (c) the base factory preset path (if any). It will "
        "build the preset.\n\n"
        "Step 3 — report the output path and stop.\n\n"
        "Hard rules:\n"
        "- Do NOT run `centrifuge` commands yourself — only the subagents do that.\n"
        "- Do NOT call either subagent more than once.\n"
        "- Do NOT verify with `centrifuge show` or any other read.\n"
        "- A correct run uses 3 turns at this level."
    )

    progress.step("Claude Code subagent")

    log_path = output_path.with_suffix(output_path.suffix + ".noapi.log")
    progress.log(f"session log: {log_path}")

    # Use stream-json so we can show live progress.  Falls back to plain run
    # if streaming fails for any reason.
    final_text = None
    with log_path.open("w", encoding="utf-8") as log_file:
        log_file.write(f"# centrifuge --noapi session\n# prompt:\n{prompt}\n\n")
        log_file.flush()
        try:
            final_text = _run_streaming(prompt, max_turns, timeout_s, progress, log_file)
        except _StreamingUnsupportedError:
            _run_blocking(prompt, max_turns, timeout_s, progress, log_file)

    if not output_path.exists():
        msg = [f"Claude Code finished but no preset was written at {output_path}."]
        if final_text:
            msg.append(f"Agent's final message: {final_text.strip()[:600]}")
        msg.append(f"Full session log: {log_path}")
        raise RuntimeError("\n".join(msg))

    progress.done()
    return output_path


# ---------------------------------------------------------------------------
# Internals
# ---------------------------------------------------------------------------

class _StreamingUnsupportedError(Exception):
    pass


def _run_streaming(prompt: str, max_turns: int, timeout_s: int, progress: Any,
                   log_file: Any) -> str | None:
    """
    Run claude with --output-format stream-json and parse events as they arrive.

    Each `assistant` event in the stream represents one turn — we use that as
    the iteration counter and surface tool names / brief text snippets when
    verbose mode is on. Every raw event line is also teed to ``log_file``
    along with stderr, and the final ``result.result`` text is returned so
    the caller can surface it on failure.
    """
    cmd = [
        "claude", "-p", prompt,
        "--output-format", "stream-json",
        "--verbose",  # required by claude CLI when stream-json is used
        "--max-turns", str(max_turns),
        # Headless `claude -p` denies Bash by default. Pre-approve only the
        # tools the agents actually need: Task (for subagent calls), Read
        # (for sound-design-expert), and the centrifuge CLI itself.
        "--allowedTools", "Task,Read,Bash(centrifuge:*)",
    ]

    process = subprocess.Popen(
        cmd,
        stdout=subprocess.PIPE,
        stderr=subprocess.PIPE,
        text=True,
        bufsize=1,
    )

    line_q: queue.Queue = queue.Queue()
    err_buf: list[str] = []

    def reader(pipe, q, kind):
        try:
            for raw in pipe:
                q.put((kind, raw))
        finally:
            q.put((kind, None))

    threading.Thread(target=reader, args=(process.stdout, line_q, "out"), daemon=True).start()
    threading.Thread(target=reader, args=(process.stderr, line_q, "err"), daemon=True).start()

    start = time.monotonic()
    closed = {"out": False, "err": False}
    turns = 0
    saw_init = False
    final_result: str | None = None

    while not (closed["out"] and closed["err"]):
        try:
            kind, raw = line_q.get(timeout=1.0)
        except queue.Empty:
            if time.monotonic() - start > timeout_s:
                process.kill()
                raise RuntimeError(
                    f"Claude Code timed out after {timeout_s}s. "
                    f"Increase --noapi-timeout or simplify the description."
                )
            progress.update(f"{turns} turns" if turns else "")
            continue

        if raw is None:
            closed[kind] = True
            continue

        if kind == "err":
            err_buf.append(raw)
            log_file.write(f"[stderr] {raw}")
            log_file.flush()
            continue

        line = raw.strip()
        if not line:
            continue

        log_file.write(raw if raw.endswith("\n") else raw + "\n")
        log_file.flush()

        try:
            event = json.loads(line)
        except json.JSONDecodeError:
            # Plain (non-JSON) output usually means stream-json isn't supported
            # by this version of claude — fall back to the blocking path.
            process.kill()
            raise _StreamingUnsupportedError(line)

        etype = event.get("type")
        if etype == "system":
            saw_init = True
            tools = event.get("tools") or []
            progress.log(
                f"session start · model={event.get('model', '?')} · "
                f"tools={len(tools)}"
            )
        elif etype == "assistant":
            turns += 1
            content = event.get("message", {}).get("content", []) or []
            text_blocks = [b for b in content if b.get("type") == "text"]
            tool_blocks = [b for b in content if b.get("type") == "tool_use"]
            metric_parts = [f"{turns} turns"]
            if tool_blocks:
                metric_parts.append(f"{len(tool_blocks)} tools")
            usage = event.get("message", {}).get("usage")
            if usage:
                metric_parts.append(
                    f"out={usage.get('output_tokens', '?')}"
                )
            progress.update(" ".join(metric_parts), count=turns)

            for tb in tool_blocks:
                progress.log(f"tool: {tb.get('name', '?')}")
            for txt in text_blocks:
                snippet = (txt.get("text") or "").strip()
                if snippet:
                    progress.log(f"assistant: {snippet[:80]}")
        elif etype == "user":
            # tool_result echoed back — only surface failures, skip the rest
            content = event.get("message", {}).get("content", []) or []
            for block in content:
                if block.get("type") != "tool_result" or not block.get("is_error"):
                    continue
                result = block.get("content")
                if isinstance(result, list):
                    text = " ".join(
                        b.get("text", "") for b in result if b.get("type") == "text"
                    )
                else:
                    text = str(result or "")
                snippet = text.strip().replace("\n", " ")[:200]
                if snippet:
                    progress.log(f"tool error: {snippet}")
        elif etype == "result":
            duration_ms = event.get("duration_ms")
            cost = event.get("total_cost_usd")
            num_turns = event.get("num_turns")
            final_result = event.get("result") or final_result
            if event.get("is_error"):
                progress.log(f"result is_error=true subtype={event.get('subtype')}")
            if duration_ms is not None:
                progress.update(
                    f"{num_turns or turns} turns · {duration_ms}ms"
                    + (f" · ${cost:.4f}" if cost is not None else ""),
                    count=num_turns or turns,
                )

    process.wait(timeout=5)
    if process.returncode != 0:
        raise RuntimeError(
            f"Claude Code exited with code {process.returncode}.\n"
            f"stderr: {''.join(err_buf).strip()[-800:]}"
        )
    return final_result


def _run_blocking(prompt: str, max_turns: int, timeout_s: int, progress: Any,
                  log_file: Any) -> str | None:
    """Fallback when stream-json is unavailable: just run and wait."""
    progress.update("(streaming unavailable; running blocking)")
    try:
        result = subprocess.run(
            [
                "claude", "-p", prompt,
                "--output-format", "json",
                "--max-turns", str(max_turns),
                "--allowedTools", "Task,Read,Bash(centrifuge:*)",
            ],
            capture_output=True,
            text=True,
            timeout=timeout_s,
        )
    except subprocess.TimeoutExpired as e:
        raise RuntimeError(
            f"Claude Code timed out after {timeout_s}s."
        ) from e
    log_file.write(result.stdout)
    if result.stderr:
        log_file.write(f"\n[stderr]\n{result.stderr}\n")
    log_file.flush()
    if result.returncode != 0:
        raise RuntimeError(
            f"Claude Code exited with code {result.returncode}.\n"
            f"stderr: {result.stderr.strip()}\n"
            f"stdout: {result.stdout.strip()[-1000:]}"
        )
    try:
        return json.loads(result.stdout).get("result")
    except (json.JSONDecodeError, AttributeError):
        return None
