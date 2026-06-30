#!/usr/bin/env python3
"""Unit tests for statusline-ceo.py (PLAN-135 W5 O4).

Hermetic + offline. The script is a standalone stdlib CLI that reads the
Claude Code statusLine stdin JSON contract, renders ONE line to stdout, and
tees an atomic sidecar JSON to the project state dir. These tests:

  * drive it via subprocess with FIXTURE stdin (the real invocation shape);
  * point CEO_STATUSLINE_SIDECAR / CEO_AUDIT_LOG_DIR at a tmp dir so $HOME
    and the real audit log are never touched;
  * assert the verified field contract (rate_limits epoch resets_at,
    context_window.used_percentage, model, worktree, plan-id);
  * assert fail-soft (garbage / empty stdin → exit 0 + a line);
  * never make a network call and never spend (the status line runs LOCALLY
    and consumes NO API tokens — Claude Code docs).

Run: python3 -m pytest .claude/scripts/tests/test_statusline_ceo.py -q
"""
from __future__ import annotations

import json
import os
import subprocess
import sys
from pathlib import Path

import pytest

REPO_ROOT = Path(__file__).resolve().parents[3]
SCRIPT = REPO_ROOT / ".claude" / "scripts" / "statusline-ceo.py"

# Import the module directly too (for unit-level function tests), via a
# path insert — the file has a hyphen so a plain import won't work.
import importlib.util

_spec = importlib.util.spec_from_file_location("statusline_ceo", str(SCRIPT))
assert _spec and _spec.loader
mod = importlib.util.module_from_spec(_spec)
_spec.loader.exec_module(mod)  # type: ignore[union-attr]


# --------------------------------------------------------------------------
# Fixtures
# --------------------------------------------------------------------------


def _full_payload() -> dict:
    """A realistic statusLine stdin object per the verified contract."""
    return {
        "cwd": "/work/proj",
        "session_id": "abc123def456",
        "transcript_path": "/path/to/transcript.jsonl",
        "model": {"id": "claude-opus-4-8", "display_name": "Opus"},
        "workspace": {
            "current_dir": "/work/proj",
            "project_dir": "/work/proj",
            "added_dirs": [],
        },
        "version": "2.1.177",
        "output_style": {"name": "default"},
        "cost": {
            "total_cost_usd": 1.2345,
            "total_duration_ms": 45000,
            "total_lines_added": 156,
            "total_lines_removed": 23,
        },
        "context_window": {
            "total_input_tokens": 15500,
            "total_output_tokens": 1200,
            "context_window_size": 200000,
            "used_percentage": 8,
            "remaining_percentage": 92,
            "current_usage": {
                "input_tokens": 8500,
                "output_tokens": 1200,
                "cache_creation_input_tokens": 5000,
                "cache_read_input_tokens": 2000,
            },
        },
        "exceeds_200k_tokens": False,
        # Verified: nested buckets, used_percentage 0-100, resets_at EPOCH SECONDS.
        "rate_limits": {
            "five_hour": {"used_percentage": 23.5, "resets_at": 1738425600},
            "seven_day": {"used_percentage": 41.2, "resets_at": 1738857600},
        },
    }


@pytest.fixture()
def env(tmp_path: Path) -> dict:
    e = dict(os.environ)
    e["CEO_AUDIT_LOG_DIR"] = str(tmp_path / "state-base")
    e["CEO_STATUSLINE_SIDECAR"] = str(tmp_path / "sidecar.json")
    # Quiet the emit path by default — exercised explicitly elsewhere.
    e["CEO_STATUSLINE_EMIT"] = "0"
    return e


def _run(stdin: str, env: dict) -> subprocess.CompletedProcess:
    return subprocess.run(
        [sys.executable, str(SCRIPT)],
        input=stdin,
        capture_output=True,
        text=True,
        env=env,
        timeout=20,
    )


# --------------------------------------------------------------------------
# CLI / subprocess (the real invocation shape)
# --------------------------------------------------------------------------


class TestRenderCli:
    def test_full_payload_renders_and_writes_sidecar(self, env):
        cp = _run(json.dumps(_full_payload()), env)
        assert cp.returncode == 0, cp.stderr
        line = cp.stdout.strip()
        assert line, "must render a non-empty line"
        # one line only
        assert "\n" not in cp.stdout.strip()
        # key facets present
        assert "Opus" in line
        assert "ctx:8%" in line
        assert "5h:24%" in line or "5h:23%" in line  # round(23.5)=24 banker? -> 24
        assert "wk:41%" in line
        assert "$1.23" in line
        # sidecar written + valid + correct schema
        side = Path(env["CEO_STATUSLINE_SIDECAR"])
        assert side.is_file()
        snap = json.loads(side.read_text())
        assert snap["schema"] == "statusline-sidecar/v1"
        assert snap["model_id"] == "claude-opus-4-8"
        assert snap["context_pct"] == 8.0
        assert snap["rate_limits_available"] is True
        assert set(snap["rate_limits"]) == {"five_hour", "seven_day"}
        assert snap["rate_limits"]["five_hour"]["used_pct"] == 23.5
        assert snap["cost"]["total_cost_usd"] == 1.2345

    def test_empty_stdin_fail_soft(self, env):
        cp = _run("", env)
        assert cp.returncode == 0
        assert cp.stdout.strip() != ""

    def test_garbage_stdin_fail_soft(self, env):
        cp = _run("}{not json at all<<<", env)
        assert cp.returncode == 0
        assert cp.stdout.strip() != ""
        # no sidecar written on un-parseable payload
        assert not Path(env["CEO_STATUSLINE_SIDECAR"]).exists()

    def test_non_object_json_fail_soft(self, env):
        cp = _run("[1, 2, 3]", env)
        assert cp.returncode == 0
        assert not Path(env["CEO_STATUSLINE_SIDECAR"]).exists()

    def test_disable_flag_renders_but_no_sidecar(self, env):
        env = dict(env, CEO_STATUSLINE_DISABLE="1")
        cp = _run(json.dumps(_full_payload()), env)
        assert cp.returncode == 0
        assert cp.stdout.strip()
        assert not Path(env["CEO_STATUSLINE_SIDECAR"]).exists()

    def test_minimal_payload_no_rate_limits(self, env):
        # Free-tier session: rate_limits absent (Pro/Max only per contract).
        payload = {"model": {"display_name": "Haiku"},
                   "workspace": {"project_dir": "/x"}}
        cp = _run(json.dumps(payload), env)
        assert cp.returncode == 0
        snap = json.loads(Path(env["CEO_STATUSLINE_SIDECAR"]).read_text())
        assert snap["rate_limits"] == {}
        assert snap["rate_limits_available"] is False

    def test_debug_tees_raw_stdin(self, env):
        env = dict(env, CEO_STATUSLINE_DEBUG="1")
        payload = _full_payload()
        cp = _run(json.dumps(payload), env)
        assert cp.returncode == 0
        dbg = Path(env["CEO_STATUSLINE_SIDECAR"] + ".debug.json")
        assert dbg.is_file()
        # debug copy is the RAW payload (includes transcript_path, which the
        # sanitized sidecar deliberately drops)
        assert json.loads(dbg.read_text())["transcript_path"] == payload["transcript_path"]
        side = json.loads(Path(env["CEO_STATUSLINE_SIDECAR"]).read_text())
        assert "transcript_path" not in side


# --------------------------------------------------------------------------
# rate_limits normalization (verified contract)
# --------------------------------------------------------------------------


class TestNormalizeRateLimits:
    def test_nested_buckets(self):
        out = mod.normalize_rate_limits(
            {"five_hour": {"used_percentage": 23.5, "resets_at": 1738425600},
             "seven_day": {"used_percentage": 41.2, "resets_at": 1738857600}})
        assert out["five_hour"]["used_pct"] == 23.5
        assert out["seven_day"]["used_pct"] == 41.2
        # epoch kept as a clean digit token
        assert out["five_hour"]["resets_at"] == "1738425600"

    def test_one_window_absent(self):
        out = mod.normalize_rate_limits(
            {"five_hour": {"used_percentage": 10, "resets_at": 1738425600}})
        assert set(out) == {"five_hour"}

    def test_flat_shape_tolerated(self):
        out = mod.normalize_rate_limits({"used_percentage": 55, "resets_at": 1738425600})
        assert "primary" in out
        assert out["primary"]["used_pct"] == 55.0

    def test_non_dict_returns_empty(self):
        assert mod.normalize_rate_limits(None) == {}
        assert mod.normalize_rate_limits("nope") == {}
        assert mod.normalize_rate_limits([1, 2]) == {}

    def test_no_free_text_leaks(self):
        # An adversarial extra string field must NOT appear in the output.
        out = mod.normalize_rate_limits(
            {"five_hour": {"used_percentage": 5, "resets_at": 1738425600,
                           "note": "SECRET-LEAK-token"}})
        blob = json.dumps(out)
        assert "SECRET-LEAK" not in blob

    def test_future_agent_sdk_bucket_passes_through(self):
        out = mod.normalize_rate_limits(
            {"five_hour": {"used_percentage": 5, "resets_at": 1738425600},
             "agent_sdk": {"used_percentage": 12, "resets_at": 1738425600}})
        assert "agent_sdk" in out
        assert mod._bucket_label("agent_sdk") == "sdk"


# --------------------------------------------------------------------------
# resets_at formatting — epoch AND iso
# --------------------------------------------------------------------------


class TestFmtResets:
    def test_epoch_seconds(self):
        s = mod._fmt_resets("1738425600")
        assert s.startswith("(r") and s.endswith(")") and ":" in s

    def test_iso_string(self):
        s = mod._fmt_resets("2026-06-13T12:30:00Z")
        assert s.startswith("(r") and ":" in s

    def test_empty_and_garbage(self):
        assert mod._fmt_resets(None) == ""
        assert mod._fmt_resets("") == ""
        assert mod._fmt_resets("not-a-time") == ""

    def test_renders_reset_marker_in_line(self):
        snap = mod.build_snapshot(_full_payload())
        line = mod.render_line(snap)
        assert "(r" in line  # at least one bucket carries a reset marker


# --------------------------------------------------------------------------
# context_pct
# --------------------------------------------------------------------------


class TestContextPct:
    def test_used_percentage_direct(self):
        assert mod.context_pct({"context_window": {"used_percentage": 8}}) == 8.0

    def test_token_ratio_fallback(self):
        pct = mod.context_pct({"context_window": {
            "total_input_tokens": 100000, "context_window_size": 200000}})
        assert pct == 50.0

    def test_null_used_percentage_no_tokens(self):
        # used_percentage may be null early in a session (contract).
        assert mod.context_pct({"context_window": {"used_percentage": None}}) is None

    def test_absent(self):
        assert mod.context_pct({}) is None


# --------------------------------------------------------------------------
# _pct_to_bps — HMAC-covered float->int basis-points (PLAN-135-FOLLOWUP-2, S234)
# --------------------------------------------------------------------------


class TestPctToBps:
    """The signed statusline breadcrumb must carry percentages as integer
    basis-points (pct * 100), never float — the canonical HMAC encoder forbids
    float (S181). The S234 bug shipped these as float -> hmac=null on every
    emit since v2.44. Regression-fence the integer contract here."""

    def test_round_to_basis_points(self):
        # 8.34% -> 834 bps (banker's-safe: round(834.0) == 834)
        assert mod._pct_to_bps(8.34) == 834

    def test_none_passes_through(self):
        assert mod._pct_to_bps(None) is None

    def test_returns_int_type(self):
        out = mod._pct_to_bps(23.5)
        assert isinstance(out, int) and not isinstance(out, bool)
        assert out == 2350

    def test_context_cap_10000(self):
        # context_pct is 0..100% -> default cap 10000; an over-100% input clamps.
        assert mod._pct_to_bps(100.0) == 10000
        assert mod._pct_to_bps(150.0) == 10000

    def test_buckets_cap_99900(self):
        # buckets carry up to 999% (no 100% ceiling) -> cap 99900 preserves burst.
        assert mod._pct_to_bps(250.0, cap_bps=99900) == 25000
        assert mod._pct_to_bps(999.0, cap_bps=99900) == 99900
        assert mod._pct_to_bps(1500.0, cap_bps=99900) == 99900

    def test_negative_clamps_to_zero(self):
        assert mod._pct_to_bps(-5.0) == 0

    def test_infinity_overflow_caught(self):
        # int(round(inf)) raises OverflowError (not ValueError) -> None.
        assert mod._pct_to_bps(float("inf")) is None

    def test_garbage_string_caught(self):
        # float("garbage") raises ValueError -> None (fail-soft, no emit crash).
        assert mod._pct_to_bps("not-a-number") is None  # type: ignore[arg-type]


# --------------------------------------------------------------------------
# Sidecar sanitization / atomic write
# --------------------------------------------------------------------------


class TestSnapshotSanitization:
    def test_only_numbers_and_ids_no_free_text(self):
        payload = _full_payload()
        payload["output_style"] = {"name": "INJECT<script>"}
        payload["cost"]["weird_text_field"] = "DROP-ME"
        snap = mod.build_snapshot(payload)
        blob = json.dumps(snap)
        assert "INJECT" not in blob
        assert "DROP-ME" not in blob
        # transcript_path never echoed
        assert "transcript_path" not in snap

    def test_atomic_write_roundtrips(self, tmp_path):
        side = tmp_path / "nested" / "snap.json"
        ok = mod.write_sidecar_atomic(side, {"schema": mod.SCHEMA, "x": 1})
        assert ok and side.is_file()
        assert json.loads(side.read_text())["x"] == 1
        # no .tmp leftovers
        assert not list(side.parent.glob("*.tmp.*"))

    def test_digest_ignores_clock_and_cost(self):
        a = mod.build_snapshot(_full_payload())
        b = mod.build_snapshot(_full_payload())
        b["captured_at"] = "2099-01-01T00:00:00Z"
        b["cost"] = {"total_cost_usd": 999.0}
        assert mod.snapshot_digest(a) == mod.snapshot_digest(b)

    def test_digest_changes_on_plan_or_bucket(self):
        a = mod.build_snapshot(_full_payload())
        b = dict(a)
        b["plan_id"] = "PLAN-999"
        assert mod.snapshot_digest(a) != mod.snapshot_digest(b)


# --------------------------------------------------------------------------
# Repo-derived plan-id + worktree (filesystem-isolated)
# --------------------------------------------------------------------------


class TestRepoDerived:
    def test_active_plan_id_single(self, tmp_path):
        plans = tmp_path / ".claude" / "plans"
        plans.mkdir(parents=True)
        (plans / "PLAN-042-foo.md").write_text("---\nstatus: executing\n---\n")
        (plans / "PLAN-007-bar.md").write_text("---\nstatus: reviewed\n---\n")
        assert mod.active_plan_id(tmp_path) == "PLAN-042"

    def test_active_plan_id_multiple(self, tmp_path):
        plans = tmp_path / ".claude" / "plans"
        plans.mkdir(parents=True)
        (plans / "PLAN-001-a.md").write_text("status: executing\n")
        (plans / "PLAN-002-b.md").write_text("status: executing\n")
        out = mod.active_plan_id(tmp_path)
        assert out == "PLAN-001+1"

    def test_active_plan_id_none(self, tmp_path):
        (tmp_path / ".claude" / "plans").mkdir(parents=True)
        assert mod.active_plan_id(tmp_path) is None

    def test_active_plan_id_missing_dir(self, tmp_path):
        assert mod.active_plan_id(tmp_path) is None

    def test_worktree_branch_from_head(self, tmp_path):
        git = tmp_path / ".git"
        git.mkdir()
        (git / "HEAD").write_text("ref: refs/heads/plan-135-exec\n")
        info = mod.worktree_info(tmp_path)
        assert info["branch"] == "plan-135-exec"
        assert info["dir"] == tmp_path.name

    def test_worktree_no_git(self, tmp_path):
        info = mod.worktree_info(tmp_path)
        assert info["branch"] is None
        assert info["dir"] == tmp_path.name


# --------------------------------------------------------------------------
# Debounced emit (mock the audit_emit module; never touch real audit log)
# --------------------------------------------------------------------------


class TestDebounceLogic:
    def test_should_emit_first_time(self, tmp_path):
        assert mod.should_emit(tmp_path / "nope.json", "d1", 1000.0, 300) is True

    def test_should_not_reemit_same_digest(self, tmp_path):
        marker = tmp_path / "m.json"
        mod._write_marker(marker, "d1", 1000.0)
        assert mod.should_emit(marker, "d1", 1000.0 + 9999, 300) is False

    def test_reemit_on_new_digest_after_interval(self, tmp_path):
        marker = tmp_path / "m.json"
        mod._write_marker(marker, "d1", 1000.0)
        assert mod.should_emit(marker, "d2", 1000.0 + 301, 300) is True

    def test_no_reemit_new_digest_within_interval(self, tmp_path):
        marker = tmp_path / "m.json"
        mod._write_marker(marker, "d1", 1000.0)
        assert mod.should_emit(marker, "d2", 1000.0 + 10, 300) is False

    def test_maybe_emit_calls_audit_emit_fail_soft(self, tmp_path, monkeypatch):
        # Stand up a fake _lib.audit_emit on a fake hooks dir so the deferred
        # import inside maybe_emit resolves to our spy — no real audit write.
        import types
        calls = []
        fake_pkg = types.ModuleType("_lib")
        fake_pkg.__path__ = []  # mark as package
        fake_ae = types.ModuleType("_lib.audit_emit")

        def _emit_generic(action, **kw):
            calls.append((action, kw))

        fake_ae.emit_generic = _emit_generic
        monkeypatch.setitem(sys.modules, "_lib", fake_pkg)
        monkeypatch.setitem(sys.modules, "_lib.audit_emit", fake_ae)
        fake_pkg.audit_emit = fake_ae

        # Point project_dir at a tree that HAS .claude/hooks/_lib so the
        # path-probe branch engages (content irrelevant — import is faked).
        proj = tmp_path / "proj"
        (proj / ".claude" / "hooks" / "_lib").mkdir(parents=True)
        sidecar = tmp_path / "sc.json"
        monkeypatch.setenv("CEO_STATUSLINE_EMIT", "1")
        snap = mod.build_snapshot(
            {"workspace": {"project_dir": str(proj)},
             # a real context_pct so the HMAC-covered bps field is a present int
             "context_window": {"used_percentage": 8},
             "rate_limits": {"five_hour": {"used_percentage": 9, "resets_at": 1738425600}}})
        mod.maybe_emit(sidecar, snap)
        assert len(calls) == 1
        action, kw = calls[0]
        assert action == "statusline_sidecar_write"
        assert kw["bucket_count"] == 1
        # HMAC-covered percentages MUST be integer basis-points, never float
        # (S181 canonical encoder forbids float -> the S234 regression-fence).
        assert isinstance(kw["context_pct_bps"], int)
        assert not isinstance(kw["context_pct_bps"], bool)
        assert isinstance(kw["buckets_used_pct_max_bps"], int)
        assert not isinstance(kw["buckets_used_pct_max_bps"], bool)
        # never carries free text / key material
        assert "transcript_path" not in kw

    def test_maybe_emit_disabled_env_no_call(self, tmp_path, monkeypatch):
        monkeypatch.setenv("CEO_STATUSLINE_EMIT", "0")
        snap = mod.build_snapshot(_full_payload())
        # Should return without importing anything — no exception.
        mod.maybe_emit(tmp_path / "sc.json", snap)


# --------------------------------------------------------------------------
# Hermeticity guard
# --------------------------------------------------------------------------


def test_does_not_touch_real_home(env, tmp_path):
    # Run with a payload and assert nothing landed under a real ~/.claude.
    cp = _run(json.dumps(_full_payload()), env)
    assert cp.returncode == 0
    # the sidecar we configured is the ONLY thing written, under tmp_path
    assert Path(env["CEO_STATUSLINE_SIDECAR"]).is_file()
    assert str(tmp_path) in env["CEO_STATUSLINE_SIDECAR"]


# --------------------------------------------------------------------------
# CEO_STATUSLINE_SIDECAR override safety (PLAN-135-FOLLOWUP, Codex R5 P1-3)
# --------------------------------------------------------------------------


class TestSidecarOverrideSafety:
    """The documented full-path override is accepted for a plain target but
    REJECTED (→ default) for a symlink target, a symlinked parent, or a literal
    '..' traversal segment — a-symlink defense-in-depth against a tampered
    settings `env` block steering the always-on writer at an attacker symlink.
    RESIDUAL (intentional): a plain absolute path to an attacker-writable dir on
    the same host still passes; the real control there is effective_config's
    settings-layer tamper detection (P1-3 option b)."""

    def test_plain_path_accepted(self, tmp_path, monkeypatch):
        target = tmp_path / "ok.json"
        monkeypatch.setenv("CEO_STATUSLINE_SIDECAR", str(target))
        assert mod._sidecar_path() == target

    def test_symlink_target_rejected_falls_back(self, tmp_path, monkeypatch):
        real = tmp_path / "real.json"
        real.write_text("{}")
        link = tmp_path / "link.json"
        link.symlink_to(real)
        monkeypatch.setenv("CEO_STATUSLINE_SIDECAR", str(link))
        monkeypatch.setenv("CEO_AUDIT_LOG_DIR", str(tmp_path / "audit"))
        got = mod._sidecar_path()
        assert got != link
        assert got == mod._default_sidecar_path()

    def test_symlinked_parent_rejected(self, tmp_path, monkeypatch):
        realdir = tmp_path / "realdir"
        realdir.mkdir()
        linkdir = tmp_path / "linkdir"
        linkdir.symlink_to(realdir, target_is_directory=True)
        monkeypatch.setenv("CEO_STATUSLINE_SIDECAR", str(linkdir / "snap.json"))
        monkeypatch.setenv("CEO_AUDIT_LOG_DIR", str(tmp_path / "audit"))
        assert mod._sidecar_path() == mod._default_sidecar_path()

    def test_dotdot_traversal_rejected(self, tmp_path, monkeypatch):
        monkeypatch.setenv("CEO_STATUSLINE_SIDECAR", str(tmp_path) + "/a/../b.json")
        monkeypatch.setenv("CEO_AUDIT_LOG_DIR", str(tmp_path / "audit"))
        assert mod._sidecar_path() == mod._default_sidecar_path()

    def test_unset_uses_default(self, tmp_path, monkeypatch):
        monkeypatch.delenv("CEO_STATUSLINE_SIDECAR", raising=False)
        monkeypatch.setenv("CEO_AUDIT_LOG_DIR", str(tmp_path / "audit"))
        assert mod._sidecar_path() == mod._default_sidecar_path()
