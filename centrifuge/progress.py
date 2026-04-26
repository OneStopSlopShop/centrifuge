"""
Progress reporter with two-line in-place updates.

Layout per step:
  [N/total] Step name...
    iter K · metric · X.Xs        ← updates in place via ANSI

In verbose mode, log lines slot between the step name and the progress line:
  [N/total] Step name...
    > tool: preset_set(Env0={kParamAttack=0.4})
    > assistant: applied envelope
    iter K · X.Xs

When a step completes (or the next step starts), the block is "frozen":
  [N/total] Step name ✓ X.Xs (K iters)
    > log lines (verbose only)

Auto-detects non-TTY streams (pipes/redirects) and falls back to one line per
step with no in-place updates so log files stay clean.
"""

from __future__ import annotations

import sys
import time
from contextlib import contextmanager
from typing import Optional, TextIO

# ANSI escape codes
_CLEAR_LINE = "\r\033[K"
_UP_AND_CLEAR = "\033[A\r\033[K"

# Styling
_BOLD = "\033[1m"
_DIM = "\033[2m"
_GREEN = "\033[32m"
_RED = "\033[31m"
_RESET = "\033[0m"

# Status marks
_DONE = f"{_GREEN}✓{_RESET}"
_FAIL = f"{_RED}✗{_RESET}"
_SEP = f"{_DIM}·{_RESET}"


class Progress:
    """Step-by-step progress reporter with optional verbose logs."""

    def __init__(
        self,
        *,
        verbose: bool = False,
        total_steps: Optional[int] = None,
        stream: TextIO = sys.stderr,
    ) -> None:
        self.verbose = verbose
        self.total_steps = total_steps
        self.stream = stream
        # Disable ANSI when not a real terminal (pipes, redirects, CI)
        self.enabled = stream.isatty() if hasattr(stream, "isatty") else False

        self.step_idx = 0
        self.step_name = ""
        self.step_start = 0.0
        self.iter_count = 0
        self.last_metric = ""
        self.log_lines: list[str] = []

        self._step_active = False
        self._final_mark = ""
        self._block_height = 0  # how many on-screen lines belong to current block

    # ------------------------------------------------------------------
    # Public API
    # ------------------------------------------------------------------

    def step(self, name: str) -> None:
        """Start a new step; finalises the previous one with a checkmark."""
        if self._step_active:
            self._finalize(_DONE)
        self.step_idx += 1
        self.step_name = name
        self.step_start = time.monotonic()
        self.iter_count = 0
        self.last_metric = ""
        self.log_lines = []
        self._step_active = True
        self._final_mark = ""
        self._block_height = 0

        if self.enabled:
            self._draw()
        else:
            self.stream.write(self._step_line() + "\n")
            self.stream.flush()

    def update(self, metric: str = "", *, count: Optional[int] = None) -> None:
        """Update the in-progress line with a new iter count or metric text."""
        if count is not None:
            self.iter_count = count
        else:
            self.iter_count += 1
        self.last_metric = metric
        if self.enabled:
            self._erase()
            self._draw()
        # Non-TTY: silent updates (would spam log files otherwise)

    def log(self, line: str) -> None:
        """Verbose: stash a contextual line that will appear under the step name."""
        if not self.verbose:
            return
        formatted = f"  {_DIM}>{_RESET} {line}" if self.enabled else f"  > {line}"
        self.log_lines.append(formatted)
        if self.enabled:
            self._erase()
            self._draw()
        else:
            self.stream.write(formatted + "\n")
            self.stream.flush()

    def done(self, summary: str = "") -> None:
        """Finalise the active step (if any) and optionally print a summary."""
        if self._step_active:
            self._finalize(_DONE)
        if summary:
            self.stream.write(summary + "\n")
            self.stream.flush()

    def fail(self, msg: str = "") -> None:
        """Mark the current step as failed and optionally print an error."""
        if self._step_active:
            self._finalize(_FAIL)
        if msg:
            self.stream.write(f"{_RED}error:{_RESET} {msg}\n" if self.enabled else f"error: {msg}\n")
            self.stream.flush()

    # ------------------------------------------------------------------
    # Context manager
    # ------------------------------------------------------------------

    def __enter__(self) -> "Progress":
        return self

    def __exit__(self, exc_type, *_args) -> None:
        if self._step_active:
            self._finalize(_FAIL if exc_type is not None else _DONE)

    # ------------------------------------------------------------------
    # Internals
    # ------------------------------------------------------------------

    def _step_line(self) -> str:
        prefix = f"{_DIM}[{self.step_idx}/{self.total_steps}]{_RESET} " if self.total_steps and self.enabled else (
            f"[{self.step_idx}/{self.total_steps}] " if self.total_steps else ""
        )
        if not self._step_active:
            elapsed = time.monotonic() - self.step_start
            extra = f" ({self.iter_count} iters)" if self.iter_count > 1 else ""
            mark = self._final_mark or _DONE
            return f"{prefix}{_BOLD}{self.step_name}{_RESET} {mark} {elapsed:.1f}s{extra}" if self.enabled \
                else f"{prefix}{self.step_name} done {elapsed:.1f}s{extra}"
        return f"{prefix}{_BOLD}{self.step_name}{_RESET}..." if self.enabled else f"{prefix}{self.step_name}..."

    def _progress_line(self) -> str:
        elapsed = time.monotonic() - self.step_start
        parts = []
        if self.iter_count > 0:
            parts.append(f"iter {self.iter_count}")
        if self.last_metric:
            parts.append(self.last_metric)
        parts.append(f"{elapsed:.1f}s")
        sep = f" {_SEP} " if self.enabled else " · "
        return "  " + sep.join(parts) if self.enabled else "  " + " · ".join(parts)

    def _erase(self) -> None:
        if self._block_height == 0:
            return
        # Cursor is on the last line of the block.
        self.stream.write(_CLEAR_LINE)
        for _ in range(self._block_height - 1):
            self.stream.write(_UP_AND_CLEAR)
        self._block_height = 0

    def _draw(self) -> None:
        lines = [self._step_line()]
        if self.verbose:
            lines.extend(self.log_lines)
        if self._step_active:
            lines.append(self._progress_line())

        for i, line in enumerate(lines):
            self.stream.write(line)
            if i < len(lines) - 1:
                self.stream.write("\n")

        if not self._step_active:
            # Frozen — advance cursor below so future writes go on a fresh line
            self.stream.write("\n")

        self._block_height = len(lines)
        self.stream.flush()

    def _finalize(self, mark: str) -> None:
        self._final_mark = mark
        if self.enabled:
            self._erase()
            self._step_active = False
            self._draw()
        else:
            elapsed = time.monotonic() - self.step_start
            extra = f" ({self.iter_count} iters)" if self.iter_count > 1 else ""
            human_mark = "done" if mark == _DONE else "fail"
            self.stream.write(f"  {human_mark} {elapsed:.1f}s{extra}\n")
            self.stream.flush()
        self._step_active = False
        self._block_height = 0


class _NullProgress:
    """Silent progress — used for --quiet and as the default when callers don't pass one."""
    verbose = False

    def step(self, name: str) -> None: ...
    def update(self, metric: str = "", *, count: Optional[int] = None) -> None: ...
    def log(self, line: str) -> None: ...
    def done(self, summary: str = "") -> None: ...
    def fail(self, msg: str = "") -> None: ...

    def __enter__(self): return self
    def __exit__(self, *_args): ...


@contextmanager
def progress_reporter(
    *,
    enabled: bool = True,
    verbose: bool = False,
    total_steps: Optional[int] = None,
    stream: TextIO = sys.stderr,
):
    """Yield a Progress (or a no-op variant when disabled)."""
    if not enabled:
        yield _NullProgress()
        return
    p = Progress(verbose=verbose, total_steps=total_steps, stream=stream)
    with p:
        yield p


def null_progress() -> _NullProgress:
    """Return a no-op progress reporter for callers that don't want output."""
    return _NullProgress()
