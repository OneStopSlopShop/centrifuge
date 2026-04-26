"""Tests for the --noapi mode (Claude Code subprocess wrapper)."""

import shutil
import subprocess
from pathlib import Path
from unittest.mock import patch

import pytest

from centrifuge.agents.noapi import (
    check_claude_available,
    generate_preset_noapi,
)


# ---------------------------------------------------------------------------
# check_claude_available
# ---------------------------------------------------------------------------

def test_check_claude_available_raises_when_missing():
    with patch("centrifuge.agents.noapi.shutil.which", return_value=None):
        with pytest.raises(RuntimeError, match="not found on PATH"):
            check_claude_available()


def test_check_claude_available_returns_path_when_found():
    with patch("centrifuge.agents.noapi.shutil.which", return_value="/usr/bin/claude"):
        assert check_claude_available() == "/usr/bin/claude"


# ---------------------------------------------------------------------------
# generate_preset_noapi — argument shape
# ---------------------------------------------------------------------------

def _fake_completed(returncode=0, stdout="ok", stderr=""):
    return subprocess.CompletedProcess(
        args=[], returncode=returncode, stdout=stdout, stderr=stderr,
    )


def test_invokes_claude_with_correct_args(tmp_path):
    out = tmp_path / "result.SerumPreset"
    out.write_bytes(b"fake")  # subagent "writes" the file

    with patch("centrifuge.agents.noapi.shutil.which", return_value="/usr/bin/claude"), \
         patch("centrifuge.agents.noapi.subprocess.run") as run_mock:
        run_mock.return_value = _fake_completed()
        generate_preset_noapi("warm pad", out)

    assert run_mock.called
    call_args = run_mock.call_args
    cmd = call_args.args[0]
    assert cmd[0] == "claude"
    assert "-p" in cmd
    assert "--output-format" in cmd
    assert "json" in cmd
    assert "--max-turns" in cmd
    # The prompt must mention the subagent and the output path
    prompt_idx = cmd.index("-p") + 1
    prompt = cmd[prompt_idx]
    assert "serum-preset-builder" in prompt
    assert "warm pad" in prompt
    assert str(out) in prompt


def test_includes_base_factory_in_prompt(tmp_path):
    out = tmp_path / "result.SerumPreset"
    out.write_bytes(b"fake")
    base = Path("/tmp/factory.SerumPreset")

    with patch("centrifuge.agents.noapi.shutil.which", return_value="/usr/bin/claude"), \
         patch("centrifuge.agents.noapi.subprocess.run") as run_mock:
        run_mock.return_value = _fake_completed()
        generate_preset_noapi("desc", out, base_factory=base)

    cmd = run_mock.call_args.args[0]
    prompt = cmd[cmd.index("-p") + 1]
    assert str(base) in prompt


def test_audio_features_injected_into_prompt(tmp_path):
    """When audio_path is given, librosa features should appear in the prompt."""
    out = tmp_path / "result.SerumPreset"
    out.write_bytes(b"fake")
    fake_features = {
        "spectral_centroid_hz": 2400.0,
        "attack_time_ms": 8.5,
        "harmonicity": 0.78,
        "is_percussive": False,
    }

    with patch("centrifuge.agents.noapi.shutil.which", return_value="/usr/bin/claude"), \
         patch("centrifuge.agents.noapi.subprocess.run") as run_mock, \
         patch("centrifuge.audio.extract_features", return_value=fake_features):
        run_mock.return_value = _fake_completed()
        generate_preset_noapi("match this", out, audio_path=Path("ref.wav"))

    cmd = run_mock.call_args.args[0]
    prompt = cmd[cmd.index("-p") + 1]
    assert "Reference audio features" in prompt
    assert "spectral_centroid_hz" in prompt
    assert "2400" in prompt
    assert "ref.wav" in prompt


def test_no_audio_clause_when_audio_path_omitted(tmp_path):
    out = tmp_path / "result.SerumPreset"
    out.write_bytes(b"fake")

    with patch("centrifuge.agents.noapi.shutil.which", return_value="/usr/bin/claude"), \
         patch("centrifuge.agents.noapi.subprocess.run") as run_mock, \
         patch("centrifuge.audio.extract_features") as extract_mock:
        run_mock.return_value = _fake_completed()
        generate_preset_noapi("just text", out)

    extract_mock.assert_not_called()
    cmd = run_mock.call_args.args[0]
    prompt = cmd[cmd.index("-p") + 1]
    assert "Reference audio features" not in prompt


# ---------------------------------------------------------------------------
# generate_preset_noapi — error paths
# ---------------------------------------------------------------------------

def test_raises_when_claude_exits_nonzero(tmp_path):
    out = tmp_path / "result.SerumPreset"

    with patch("centrifuge.agents.noapi.shutil.which", return_value="/usr/bin/claude"), \
         patch("centrifuge.agents.noapi.subprocess.run") as run_mock:
        run_mock.return_value = _fake_completed(returncode=1, stderr="oops")
        with pytest.raises(RuntimeError, match="exited with code 1"):
            generate_preset_noapi("desc", out)


def test_raises_when_no_file_produced(tmp_path):
    out = tmp_path / "missing.SerumPreset"

    with patch("centrifuge.agents.noapi.shutil.which", return_value="/usr/bin/claude"), \
         patch("centrifuge.agents.noapi.subprocess.run") as run_mock:
        run_mock.return_value = _fake_completed(returncode=0, stdout="done")
        with pytest.raises(RuntimeError, match="no preset was written"):
            generate_preset_noapi("desc", out)


def test_raises_on_timeout(tmp_path):
    out = tmp_path / "result.SerumPreset"

    with patch("centrifuge.agents.noapi.shutil.which", return_value="/usr/bin/claude"), \
         patch("centrifuge.agents.noapi.subprocess.run") as run_mock:
        run_mock.side_effect = subprocess.TimeoutExpired(cmd=["claude"], timeout=600)
        with pytest.raises(RuntimeError, match="timed out"):
            generate_preset_noapi("desc", out)


# ---------------------------------------------------------------------------
# Integration smoke test (requires `claude` on PATH; auto-skipped otherwise)
# ---------------------------------------------------------------------------

@pytest.mark.skipif(
    shutil.which("claude") is None,
    reason="claude CLI not installed",
)
@pytest.mark.skip(reason="Live Claude Code call — only run manually")
def test_live_smoke(tmp_path):
    """Manual: drop the @skip and run with `pytest -k live_smoke -s` to actually call Claude Code."""
    out = tmp_path / "smoke.SerumPreset"
    result = generate_preset_noapi("warm pad", out, timeout_s=180)
    assert result.exists()
