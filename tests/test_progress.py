"""Tests for the Progress reporter."""

import io
import re

import pytest

from centrifuge.progress import (
    Progress,
    null_progress,
    progress_reporter,
)

ANSI_RE = re.compile(r"\033\[[0-9;?]*[A-Za-z]")


def _strip_ansi(s: str) -> str:
    return ANSI_RE.sub("", s).replace("\r", "")


# ---------------------------------------------------------------------------
# Non-TTY mode (the easy case to verify)
# ---------------------------------------------------------------------------

def _make_buffer_progress(verbose=False, total=None):
    """Build a Progress against a StringIO (which has isatty()=False)."""
    buf = io.StringIO()
    p = Progress(verbose=verbose, total_steps=total, stream=buf)
    assert p.enabled is False
    return p, buf


def test_non_tty_step_prints_one_line():
    p, buf = _make_buffer_progress(total=2)
    p.step("First")
    p.step("Second")
    p.done()
    out = buf.getvalue()
    assert "[1/2] First..." in out
    assert "[2/2] Second..." in out
    # Two "done" markers
    assert out.count("done") == 2


def test_non_tty_no_inline_updates():
    """Update calls should be silent in non-TTY mode (would spam log files)."""
    p, buf = _make_buffer_progress()
    p.step("Working")
    before = buf.getvalue()
    p.update("iter 1")
    p.update("iter 2")
    p.update("iter 3")
    after_updates = buf.getvalue()
    # No new content — non-TTY suppresses in-place updates
    assert after_updates == before
    p.done()


def test_non_tty_logs_print_immediately_in_verbose():
    p, buf = _make_buffer_progress(verbose=True)
    p.step("Working")
    p.log("hello")
    p.log("world")
    p.done()
    out = buf.getvalue()
    assert "> hello" in out
    assert "> world" in out


def test_non_tty_logs_suppressed_when_not_verbose():
    p, buf = _make_buffer_progress(verbose=False)
    p.step("Working")
    p.log("should not appear")
    p.done()
    assert "should not appear" not in buf.getvalue()


def test_done_with_summary():
    p, buf = _make_buffer_progress()
    p.step("Working")
    p.done("All done!")
    assert "All done!" in buf.getvalue()


def test_fail_marks_step():
    p, buf = _make_buffer_progress()
    p.step("Working")
    p.fail("something broke")
    out = buf.getvalue()
    assert "fail" in out
    assert "something broke" in out


def test_iter_count_appears_when_more_than_one():
    p, buf = _make_buffer_progress()
    p.step("Working")
    p.update()  # iter 1
    p.update()  # iter 2
    p.update()  # iter 3
    p.done()
    out = buf.getvalue()
    assert "(3 iters)" in out


# ---------------------------------------------------------------------------
# TTY mode (with ANSI codes)
# ---------------------------------------------------------------------------

class _FakeTTY(io.StringIO):
    def isatty(self):
        return True


def test_tty_uses_ansi_escapes():
    buf = _FakeTTY()
    p = Progress(stream=buf)
    assert p.enabled is True
    p.step("Working")
    p.update("metric")
    p.done()
    raw = buf.getvalue()
    # Should contain ANSI clear-line and escape sequences
    assert "\033[" in raw
    # And after stripping, should still be readable
    clean = _strip_ansi(raw)
    assert "Working" in clean


def test_tty_renders_log_lines_in_block():
    buf = _FakeTTY()
    p = Progress(verbose=True, stream=buf)
    p.step("Working")
    p.log("first log")
    p.log("second log")
    p.done()
    clean = _strip_ansi(buf.getvalue())
    assert "first log" in clean
    assert "second log" in clean


# ---------------------------------------------------------------------------
# Null progress + context manager
# ---------------------------------------------------------------------------

def test_null_progress_is_silent():
    np = null_progress()
    np.step("Working")
    np.update("metric")
    np.log("logged")
    np.done("summary")
    np.fail("error")
    # No exception, no output


def test_progress_reporter_disabled_yields_null():
    with progress_reporter(enabled=False) as p:
        p.step("Working")
        p.update("metric")
        p.done()
    # No exception; behaves like null


def test_progress_reporter_finalizes_on_exit():
    buf = _FakeTTY()
    p = Progress(stream=buf)
    with p:
        p.step("Working")
        p.update("metric")
        # Don't call done() — context manager should finalize
    clean = _strip_ansi(buf.getvalue())
    # Should have a finalized step in the output
    assert "Working" in clean
    # Should have either ✓ or "done"
    assert "✓" in clean or "done" in clean


def test_progress_reporter_marks_failure_on_exception():
    buf = _FakeTTY()
    p = Progress(stream=buf)
    with pytest.raises(ValueError):
        with p:
            p.step("Working")
            raise ValueError("boom")
    clean = _strip_ansi(buf.getvalue())
    assert "✗" in clean or "fail" in clean


# ---------------------------------------------------------------------------
# Step counter + total
# ---------------------------------------------------------------------------

def test_step_prefix_with_total():
    p, buf = _make_buffer_progress(total=3)
    p.step("One")
    p.step("Two")
    p.step("Three")
    p.done()
    out = buf.getvalue()
    assert "[1/3]" in out
    assert "[2/3]" in out
    assert "[3/3]" in out


def test_step_prefix_omitted_without_total():
    p, buf = _make_buffer_progress(total=None)
    p.step("Just one")
    p.done()
    out = buf.getvalue()
    assert "[" not in out
    assert "Just one" in out
