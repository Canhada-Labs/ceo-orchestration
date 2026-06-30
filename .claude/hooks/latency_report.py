"""
latency_report.py — PLAN-128 Wave-2 latency-tax visibility + fast-path helper.

Measures interpreter cold-start tax and hook registration overhead. Reports
the per-edit interpreter cost without claiming unmeasured throughput gains.

Implements:
  - measure_cold_start_ms(n): time n separate subprocess cold starts
  - count_registered_hooks(settings_path): count hook entries in a settings file
  - should_fast_path(file_path): identify edits that skip expensive verification
  - report(settings_path, n): human-readable latency summary + honest caveats

PLAN-128 §6: measure interpreter latency at scale across Wave-2 edits,
quantify the per-edit tax, and guide fast-path dispatch decisions for edits
that do NOT trigger verification (docs, lock files, configs).

Fail-open: all public functions catch exceptions and return safe defaults.
No network calls. No subshell. Subprocess only in measure_cold_start_ms.
"""
from __future__ import annotations

import json
import os
import subprocess
import sys
import time
from typing import Optional


def measure_cold_start_ms(n: int = 20) -> float:
    """
    Time n separate subprocess cold starts of `python -c pass`.

    Returns the mean time in milliseconds. On any error, returns -1.0.

    Args:
        n: Number of cold-start samples (default 20).

    Returns:
        Mean cold-start time in ms, or -1.0 on error.
    """
    try:
        if n < 1:
            return -1.0

        times_ms: list[float] = []

        for _ in range(n):
            start = time.perf_counter()
            subprocess.run(
                [sys.executable, "-c", "pass"],
                stdout=subprocess.DEVNULL,
                stderr=subprocess.DEVNULL,
                check=True,
                timeout=10,
            )
            end = time.perf_counter()
            times_ms.append((end - start) * 1000.0)

        if not times_ms:
            return -1.0

        return sum(times_ms) / len(times_ms)
    except Exception:
        return -1.0


def count_registered_hooks(settings_path: str) -> int:
    """
    Count the total number of hook entries in a settings file.

    Reads the JSON settings file and sums the length of "hooks" arrays
    across all event matcher blocks.

    Args:
        settings_path: Path to the settings.json file.

    Returns:
        Total hook count, or 0 on error (missing file, parse error, etc.).
    """
    try:
        with open(settings_path, "r") as f:
            settings = json.load(f)

        if not isinstance(settings, dict):
            return 0

        hooks_section = settings.get("hooks", {})
        if not isinstance(hooks_section, dict):
            return 0

        total_hooks = 0
        for event_name, matchers in hooks_section.items():
            if not isinstance(matchers, list):
                continue
            for matcher_block in matchers:
                if not isinstance(matcher_block, dict):
                    continue
                hook_list = matcher_block.get("hooks")
                if isinstance(hook_list, list):
                    total_hooks += len(hook_list)

        return total_hooks
    except Exception:
        return 0


def should_fast_path(file_path: str) -> bool:
    """
    Determine if a file edit can skip expensive verification.

    Fast-path edits:
      - Documentation: .md, .txt, .rst
      - Config: .json, .lock, .cfg, .ini, .toml, .yaml, .yml
      - No extension

    Code edits (.py, .js, .ts, .go, .rs, etc.) require verification.
    Unknown code-like extensions default to False (verify them).

    Args:
        file_path: Path to the edited file.

    Returns:
        True if the edit can skip verification, False otherwise.
    """
    try:
        if not file_path or not isinstance(file_path, str):
            return False

        # Extract extension (everything after the last dot).
        if "." not in file_path:
            # No extension files (e.g., Makefile, Dockerfile) → fast-path.
            return True

        # Get the extension (lowercase for case-insensitive matching).
        _, ext = file_path.rsplit(".", 1)
        ext = "." + ext.lower()

        # Safe-to-skip file types.
        fast_path_exts = frozenset(
            {
                ".md",
                ".txt",
                ".rst",
                ".json",
                ".lock",
                ".cfg",
                ".ini",
                ".toml",
                ".yaml",
                ".yml",
            }
        )

        return ext in fast_path_exts
    except Exception:
        return False


def report(settings_path: Optional[str] = None, n: int = 20) -> str:
    """
    Generate a human-readable latency report with honest caveats.

    Measures cold-start ms, counts hook registrations, estimates per-edit
    interpreter tax, and clarifies that this reports the CURRENT per-edit
    cold-start tax only. Any measurement of latency reduction from
    consolidation requires a before/after comparison.

    Args:
        settings_path: Path to settings.json (optional; if not provided, no
                       hook count is reported).
        n: Number of cold-start samples (default 20).

    Returns:
        A multi-line human-readable summary. Never contains throughput claims.
    """
    try:
        lines: list[str] = []

        # Measure cold-start.
        cold_start_ms = measure_cold_start_ms(n)
        if cold_start_ms >= 0:
            lines.append(f"Cold-start latency: {cold_start_ms:.1f} ms (n={n})")
        else:
            lines.append("Cold-start latency: (measurement failed)")

        # Count hooks.
        hook_count = 0
        if settings_path:
            hook_count = count_registered_hooks(settings_path)
            lines.append(f"Registered hooks: {hook_count}")

        # Estimate per-edit tax.
        if cold_start_ms >= 0 and hook_count > 0:
            per_edit_tax = cold_start_ms * hook_count
            lines.append(
                f"Estimated per-edit interpreter tax: {per_edit_tax:.0f} ms "
                f"({cold_start_ms:.1f} ms × {hook_count} hooks)"
            )

        # Honest caveat: measurement-only, no latency improvement claims.
        lines.append(
            "\nCaveat: This report shows the CURRENT per-edit cold-start tax only. "
            "accel_dispatch already merges the NEW accelerators (#1+#5) into one "
            "process; whether that nets a latency reduction must be confirmed by a "
            "before/after measurement — this tool makes no such claim."
        )

        return "\n".join(lines)
    except Exception:
        return "Latency report: error (see logs)"


def _selftest() -> None:
    """Run self-tests for all public functions."""
    import tempfile

    print("latency_report selftest running...")

    # Test 1: should_fast_path for doc files.
    assert should_fast_path("file.md") is True, "should_fast_path('.md') failed"
    assert should_fast_path("file.txt") is True, "should_fast_path('.txt') failed"
    assert should_fast_path("file.yaml") is True, "should_fast_path('.yaml') failed"
    assert should_fast_path("file.json") is True, "should_fast_path('.json') failed"
    assert should_fast_path("Makefile") is True, "should_fast_path(no-ext) failed"

    # Test 2: should_fast_path for code files.
    assert should_fast_path("file.py") is False, "should_fast_path('.py') failed"
    assert should_fast_path("file.js") is False, "should_fast_path('.js') failed"
    assert should_fast_path("file.go") is False, "should_fast_path('.go') failed"
    assert should_fast_path("file.unknown_code") is False, (
        "should_fast_path(unknown) should default to False"
    )

    # Test 3: count_registered_hooks on missing file.
    count = count_registered_hooks("/nonexistent/settings.json")
    assert count == 0, f"count_registered_hooks(missing) should return 0, got {count}"

    # Test 4: count_registered_hooks on a valid settings file.
    with tempfile.NamedTemporaryFile(
        mode="w", suffix=".json", delete=False
    ) as tmp:
        test_settings = {
            "hooks": {
                "PreToolUse": [{"hooks": ["hook1", "hook2"]}],
                "PostToolUse": [{"hooks": ["hook3"]}, {"hooks": ["hook4", "hook5"]}],
            }
        }
        json.dump(test_settings, tmp)
        tmp_path = tmp.name

    try:
        count = count_registered_hooks(tmp_path)
        expected = 5  # 2 + 1 + 2
        assert count == expected, (
            f"count_registered_hooks should count {expected} hooks, got {count}"
        )
    finally:
        os.unlink(tmp_path)

    # Test 5: measure_cold_start_ms returns a positive number (or -1.0 on error).
    cold_start = measure_cold_start_ms(3)
    assert isinstance(cold_start, float), (
        f"measure_cold_start_ms should return float, got {type(cold_start)}"
    )
    assert cold_start > 0 or cold_start == -1.0, (
        f"measure_cold_start_ms should return positive or -1.0, got {cold_start}"
    )

    # Test 6: report contains "tax" and does NOT contain throughput claims.
    with tempfile.NamedTemporaryFile(
        mode="w", suffix=".json", delete=False
    ) as tmp:
        test_settings = {
            "hooks": {
                "PreToolUse": [{"hooks": ["h1", "h2", "h3"]}],
                "PostToolUse": [{"hooks": ["h4"]}],
            }
        }
        json.dump(test_settings, tmp)
        tmp_path = tmp.name

    try:
        report_text = report(tmp_path, n=2)
        assert "tax" in report_text.lower(), (
            f"report should contain 'tax', got: {report_text}"
        )
        assert "3x" not in report_text and "x throughput" not in report_text, (
            f"report should NOT contain throughput claims, got: {report_text}"
        )
        # If report contains multiplication symbol, it must be in "Estimated" context.
        if "×" in report_text:
            assert "Estimated" in report_text, (
                "report should not contain misleading multiplier claims"
            )
    finally:
        os.unlink(tmp_path)

    # Test 6b: report contains "measurement" and does NOT contain "removes" or "faster".
    with tempfile.NamedTemporaryFile(
        mode="w", suffix=".json", delete=False
    ) as tmp:
        test_settings = {
            "hooks": {
                "PreToolUse": [{"hooks": ["h1"]}],
            }
        }
        json.dump(test_settings, tmp)
        tmp_path = tmp.name

    try:
        report_text = report(tmp_path, n=2)
        assert "measurement" in report_text.lower(), (
            f"report should contain 'measurement' (honesty caveat), got: {report_text}"
        )
        assert "removes" not in report_text.lower(), (
            f"report should NOT contain 'removes' (unmeasured claim), got: {report_text}"
        )
        assert "faster" not in report_text.lower(), (
            f"report should NOT contain 'faster' (unmeasured claim), got: {report_text}"
        )
        # Verify the caveat emphasizes measurement-only and before/after requirement.
        assert "before/after" in report_text or "measurement" in report_text, (
            f"report caveat should mention measurement requirement, got: {report_text}"
        )
    finally:
        os.unlink(tmp_path)

    # Test 7: fail-open on bad inputs.
    assert should_fast_path(None) is False, "should_fast_path(None) should not crash"
    assert should_fast_path("") is False, "should_fast_path('') should not crash"
    assert measure_cold_start_ms(-5) == -1.0, (
        "measure_cold_start_ms(negative) should return -1.0"
    )

    print("latency_report selftest PASS (all assertions passed)")


if __name__ == "__main__":
    if "--selftest" in sys.argv:
        _selftest()
    else:
        print(__doc__)
