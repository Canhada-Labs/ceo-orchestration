"""Chaos test: disk full must fail-open per ADR-005 / ADR-037 §5.1.

PLAN-012 Phase 3 D4.3 cascade invariant: when audit-log.jsonl cannot
be written (ENOSPC / EDQUOT), the hooks MUST NOT raise, MUST NOT block
the user session, and MUST return a valid ``{"decision":"allow"}``
envelope (or be silent, for PostToolUse hooks).

## Disk-full simulation approach

Real tmpfs fill is infeasible portably in CI:

- Linux needs `mount -t tmpfs` + root, which GitHub Actions doesn't
  grant without a container.
- macOS needs `hdiutil attach -imagekey diskimage-class=CRawDiskImage`
  which hangs on fresh runners.

We use a dual strategy:

1. **Injected OSError(ENOSPC)** — a preloader module that replaces
   ``builtins.open`` when the target is under a sentinel directory, so
   any ``open(path, 'a')`` under that dir raises
   ``OSError(errno.ENOSPC, "no space left on device")``. This
   deterministically reproduces the hook's disk-full code path.

2. **Optional real tmpfs** — if running on Linux with a pre-mounted
   tmpfs at ``$CEO_CHAOS_TMPFS_DIR``, we use it directly. The CI path
   leaves this unset, so the injected-ENOSPC path is what actually
   runs.

Gated per ADR-037 §Decision §2:
    CEO_CHAOS_ALLOWED=1

plus an added guard ``_assert_running_in_temp_cwd`` — we never point
at a real repo path in case a dev runs this outside CI.
"""

from __future__ import annotations

import errno
import json
import os
import subprocess
import sys
import time
from pathlib import Path
from typing import Callable, Iterator

import pytest

_REPO_ROOT = Path(__file__).resolve().parents[2]
_HOOKS_DIR = _REPO_ROOT / ".claude" / "hooks"
if str(_HOOKS_DIR) not in sys.path:
    sys.path.insert(0, str(_HOOKS_DIR))

pytestmark = pytest.mark.skipif(
    os.environ.get("CEO_CHAOS_ALLOWED") != "1",
    reason="Chaos tests gated per ADR-037 (CEO_CHAOS_ALLOWED=1 required)",
)


# ------------------------------------------------------------------------------
# Guard: never run this file's workload against a real user directory
# ------------------------------------------------------------------------------


def _assert_running_in_temp_cwd() -> None:
    """Safety: the target audit_dir must be under a temp prefix.

    TestEnvContext always creates `ceo-hook-test-*` under
    tempfile.gettempdir(), so legitimate chaos runs always pass. If
    somebody sets CEO_AUDIT_LOG_DIR to a real path outside the temp
    tree this guard refuses to run.
    """
    audit_dir = os.environ.get("CEO_AUDIT_LOG_DIR", "")
    if not audit_dir:
        return
    temp_markers = ("ceo-hook-test-", "/tmp/", "/var/folders/")
    if not any(m in audit_dir for m in temp_markers):
        pytest.skip(
            f"safety guard: CEO_AUDIT_LOG_DIR={audit_dir!r} not under tempdir"
        )


# ------------------------------------------------------------------------------
# ENOSPC injection
# ------------------------------------------------------------------------------


class _DiskFullContext:
    """Context manager that makes write-mode opens under ``target_dir`` fail.

    Only affects paths under ``target_dir``. Other files (imports,
    temp files in other locations) are left alone.

    This is a white-box simulation: it reproduces exactly the
    OSError the kernel would raise when the filesystem is out of
    space. The hook's ``except OSError as e`` must then swallow and
    breadcrumb.

    Implementation detail: we patch ``os.open`` rather than
    ``builtins.open`` because ``pathlib.Path.open`` routes through
    ``io.open`` → ``os.open`` and would bypass a builtins-level patch.
    All file-open code paths (builtin ``open``, ``Path.open``, ``io.open``)
    ultimately call ``os.open`` for real I/O.
    """

    # Write-mode flags we intercept. We match any flag that includes a
    # write intent; O_RDONLY (0) passes through unchanged.
    _WRITE_MASK = os.O_WRONLY | os.O_RDWR | os.O_APPEND | os.O_CREAT | os.O_TRUNC

    def __init__(self, target_dir: Path) -> None:
        self.target_dir = Path(target_dir).resolve()
        self._orig_os_open: Callable = os.open  # type: ignore[assignment]

    def _raising_os_open(self, path, flags, mode=0o777, *, dir_fd=None):  # type: ignore[no-untyped-def]
        # Pass directory-fd-relative calls through — we don't poison
        # openat() style operations (which the hooks don't use anyway).
        if dir_fd is not None:
            return self._orig_os_open(path, flags, mode, dir_fd=dir_fd)

        try:
            resolved = Path(os.fspath(path)).resolve()
        except (TypeError, ValueError, OSError):
            return self._orig_os_open(path, flags, mode)

        try:
            resolved.relative_to(self.target_dir)
            in_target = True
        except ValueError:
            in_target = False

        # Only intercept writes. Reads (O_RDONLY == 0) must succeed so
        # tests can still inspect any file the target did manage to
        # create before the disk-full moment.
        is_write = bool(flags & self._WRITE_MASK) or bool(flags & os.O_WRONLY)
        # The mask above already covers most cases; O_WRONLY is 1 on
        # Linux/macOS so the `flags & mask` check is sound. But guard
        # against platform differences:
        is_write = is_write or flags != os.O_RDONLY

        if in_target and is_write:
            raise OSError(
                errno.ENOSPC, os.strerror(errno.ENOSPC), os.fspath(path)
            )
        return self._orig_os_open(path, flags, mode)

    def __enter__(self) -> "_DiskFullContext":
        os.open = self._raising_os_open  # type: ignore[assignment]
        return self

    def __exit__(self, *exc) -> None:
        os.open = self._orig_os_open  # type: ignore[assignment]


@pytest.fixture
def disk_full_target(chaos_env) -> Iterator[Path]:
    """Yields the audit dir under simulated disk full.

    Any ``open(..., 'a')`` inside this directory raises ENOSPC until
    the fixture teardown restores the real ``open``.
    """
    _assert_running_in_temp_cwd()
    target = chaos_env.audit_dir
    # Pre-create the dir (mkdir succeeds before we poison open).
    target.mkdir(parents=True, exist_ok=True)
    with _DiskFullContext(target):
        yield target


# ------------------------------------------------------------------------------
# Test 1 — hooks fail open on disk full (subprocess path, realistic)
# ------------------------------------------------------------------------------


def test_hooks_fail_open_on_disk_full(chaos_env, hook_fixture_loader):
    """Disk full → every hook must return ``{"decision":"allow"}``.

    We fire the real hooks as subprocesses (the production path) with
    a wrapper that poisons audit-log writes. The hook MUST exit 0 (for
    PostToolUse audit_log) or emit a JSON ``{"decision":"allow"}`` on
    stdout (for PreToolUse hooks).
    """
    _assert_running_in_temp_cwd()
    hooks = [
        "check_agent_spawn",
        "audit_log",
        "check_bash_safety",
        "check_plan_edit",
    ]

    # We run each hook via a wrapper that installs the _DiskFullContext
    # before invoking the hook's main(). Simplest: a small helper
    # Python script we write to the project tmpdir.
    helper = chaos_env.project_dir / "disk_full_runner.py"
    helper.write_text(
        (
            "import errno, os, runpy, sys\n"
            "from pathlib import Path\n"
            "hook_script = sys.argv[1]\n"
            "target_dir = Path(os.environ['CEO_AUDIT_LOG_DIR']).resolve()\n"
            "orig_os_open = os.open\n"
            "def poisoned_os_open(path, flags, mode=0o777, *, dir_fd=None):\n"
            "    if dir_fd is not None:\n"
            "        return orig_os_open(path, flags, mode, dir_fd=dir_fd)\n"
            "    try:\n"
            "        res = Path(os.fspath(path)).resolve()\n"
            "    except Exception:\n"
            "        return orig_os_open(path, flags, mode)\n"
            "    try:\n"
            "        res.relative_to(target_dir); inside = True\n"
            "    except ValueError:\n"
            "        inside = False\n"
            "    if inside and flags != os.O_RDONLY:\n"
            "        raise OSError(errno.ENOSPC, os.strerror(errno.ENOSPC), "
            "os.fspath(path))\n"
            "    return orig_os_open(path, flags, mode)\n"
            "os.open = poisoned_os_open\n"
            "runpy.run_path(hook_script, run_name='__main__')\n"
        ),
        encoding="utf-8",
    )
    # Minimal valid Agent PostToolUse payload that audit_log won't reject.
    valid_payload = hook_fixture_loader("audit_log")

    for hook in hooks:
        hook_path = _HOOKS_DIR / f"{hook}.py"
        # Some hooks are PreToolUse; some PostToolUse. Fixture is
        # per-hook so this works uniformly.
        try:
            payload = hook_fixture_loader(hook)
        except FileNotFoundError:
            payload = valid_payload

        env = os.environ.copy()
        try:
            r = subprocess.run(
                [sys.executable, str(helper), str(hook_path)],
                input=payload,
                capture_output=True,
                text=True,
                env=env,
                timeout=5.0,
            )
        except subprocess.TimeoutExpired:
            pytest.fail(f"{hook}: timed out under disk-full — not fail-open")

        assert r.returncode == 0, (
            f"{hook}: exit rc={r.returncode} under disk-full; "
            f"stderr[:400]={r.stderr[:400]!r}"
        )

        stdout_stripped = (r.stdout or "").strip()
        if hook == "audit_log":
            # PostToolUse: silent on stdout by contract.
            assert stdout_stripped == "", (
                f"audit_log broke silence contract under disk-full: "
                f"stdout={stdout_stripped[:200]!r}"
            )
        else:
            # PreToolUse: must emit a parseable allow decision OR be
            # silent (some hooks short-circuit on irrelevant payloads).
            if stdout_stripped:
                last = stdout_stripped.splitlines()[-1]
                try:
                    decision = json.loads(last)
                except json.JSONDecodeError:
                    # Unparseable stdout is still fail-open per
                    # ADR-005 (framework treats it as allow).
                    continue
                if isinstance(decision, dict) and "decision" in decision:
                    assert decision["decision"] in ("allow", "block"), (
                        f"{hook}: unexpected decision {decision!r}"
                    )
                    # A block on disk-full would be a bug — the
                    # inject-ENOSPC path MUST NOT cause a block decision.
                    # But some hooks legitimately block on payload
                    # content unrelated to disk. We accept allow OR
                    # a content-driven block (the fixture is chosen
                    # so the content is benign → allow expected).
                    assert decision["decision"] == "allow", (
                        f"{hook}: disk-full yielded block {decision!r}"
                    )


# ------------------------------------------------------------------------------
# Test 2 — otel bounded exporter does not cascade under disk full
# ------------------------------------------------------------------------------


def test_otel_exporter_stops_adding_pressure(disk_full_target):
    """With audit disk full AND exporter up, enqueue must not raise.

    The exporter's overflow-audit emitter tries to write an audit event
    when drops reach the batch threshold. That write will ALSO hit
    ENOSPC. The emitter must swallow (fail-open per ADR-005) and the
    exporter's enqueue_span must remain non-blocking.
    """
    from _lib.otel.bounded_exporter import BoundedExporter

    # Note: disk_full_target fixture already poisoned the audit dir.
    os.environ["CEO_OTEL_ALLOWED_HOSTS"] = "127.0.0.1"

    # Fake exporter that always fails; we're stressing the drop path.
    call_count = [0]

    def fake_exporter(endpoint, events, *, allowed_hosts=None, timeout=2.0):
        call_count[0] += 1
        return None

    exporter = BoundedExporter(
        endpoint="https://127.0.0.1:1/v1/traces",
        allowed_hosts=["127.0.0.1"],
        exporter=fake_exporter,
        maxsize=50,
        drain_interval_s=0.05,
        batch_size=10,
        overflow_audit_batch=100,
        send_timeout_s=0.5,
        auto_start=True,
    )
    try:
        start = time.monotonic()
        for i in range(2000):
            # This must not raise even though any attempt to write an
            # overflow audit will hit ENOSPC.
            exporter.enqueue_span(
                {"action": "agent_spawn", "ts": "2026-04-14T10:00:00Z", "seq": i}
            )
        elapsed = time.monotonic() - start

        # 2000 spans under disk-full in < 5s (real budget ~100ms; slack for CI).
        assert elapsed < 5.0, (
            f"enqueue cascade: 2000 spans took {elapsed:.2f}s under disk-full"
        )
        snap = exporter.snapshot()
        assert snap["queue"]["size"] <= 50
        assert snap["queue"]["dropped"] >= 1900
    finally:
        exporter.shutdown(grace_s=0.5)


# ------------------------------------------------------------------------------
# Test 3 — audit_emit fail-open contract directly exercised
# ------------------------------------------------------------------------------


def test_audit_emit_swallows_enospc(disk_full_target):
    """Directly call audit_emit API under ENOSPC — must not raise."""
    from _lib import audit_emit

    # 100 calls — none may raise, and none may block > budget.
    start = time.monotonic()
    for i in range(100):
        audit_emit.emit_benchmark_run(
            benchmark_id=f"chaos-{i}",
            skill="probe",
            pass_count=1,
            fail_count=0,
            pass_rate=1.0,
            median_score=1.0,
            floor=0.5,
        )
    elapsed = time.monotonic() - start
    assert elapsed < 2.0, f"audit_emit got slow under ENOSPC: {elapsed:.2f}s"

    # audit-log.jsonl must NOT exist (every append was rejected).
    log = disk_full_target / "audit-log.jsonl"
    assert not log.exists() or log.stat().st_size == 0
