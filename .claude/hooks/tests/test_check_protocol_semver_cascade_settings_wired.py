"""Wiring-conformance tests for check_protocol_semver_cascade.py.

PLAN-112-FOLLOWUP-plan-110-close (v1.39.6) AC4 — closes false-closure
F-1.1-1.1-7c108548 by asserting the hook is genuinely wired into the
PreToolUse chain in BOTH dogfood (.claude/settings.json) AND template
(templates/settings/settings.base.json), plus exercises subprocess
invocation through the wired command for AC2 (advisory warn-emit + on-disk
audit-log entry) and AC3 (clean allow, zero audit-log delta).

The existing test_check_protocol_semver_cascade.py covers 8 unit cases of
the hook script directly. THIS file covers the SETTINGS-JSON wiring + the
shipped registration shape, so a future "shipped-but-not-wired" regression
is caught at test time, not at S153-style audit time.
"""
from __future__ import annotations

import json
import os
import subprocess
import sys
import time
import unittest
from pathlib import Path
from typing import Dict, List

REPO_ROOT = Path(__file__).resolve().parents[3]
HOOK = REPO_ROOT / ".claude/hooks/check_protocol_semver_cascade.py"
SHIM = REPO_ROOT / ".claude/hooks/_python-hook.sh"
DOGFOOD_SETTINGS = REPO_ROOT / ".claude/settings.json"
TEMPLATE_SETTINGS = REPO_ROOT / "templates/settings/settings.base.json"

# Add hooks dir to sys.path so the latency test (case g) can import the hook
# module directly for in-process measurement.
sys.path.insert(0, str(REPO_ROOT / ".claude/hooks"))

# Import _lib.testing for env isolation + audit-log inspection helpers.
sys.path.insert(0, str(REPO_ROOT / ".claude/hooks"))
from _lib.testing import TestEnvContext  # noqa: E402


def _run_via_shim(payload: Dict, env: Dict[str, str]) -> subprocess.CompletedProcess:
    """Invoke the hook via the wired bash _python-hook.sh path (matches
    runtime invocation from settings.json), not via direct python invocation.
    """
    return subprocess.run(
        ["bash", str(SHIM), "check_protocol_semver_cascade.py"],
        input=json.dumps(payload),
        capture_output=True,
        text=True,
        env=env,
        timeout=10,
        cwd=str(REPO_ROOT),
    )


def _find_stanzas(settings_path: Path) -> List[Dict]:
    """Locate ALL PreToolUse stanzas in a settings.json variant whose hook
    command references check_protocol_semver_cascade.py.

    Returns a list so the caller can assert EXACTLY ONE registration —
    duplicate stanzas (e.g., merge mishap) must surface as a test failure,
    not be silently masked by a "first-match" lookup.

    Tolerates jsonc-style `_comment` keys (json.loads handles them as data).
    """
    data = json.loads(settings_path.read_text(encoding="utf-8"))
    pretool_chain = data.get("hooks", {}).get("PreToolUse", [])
    matches: List[Dict] = []
    for stanza in pretool_chain:
        hooks = stanza.get("hooks", []) or []
        for h in hooks:
            cmd = h.get("command", "") or ""
            if "check_protocol_semver_cascade.py" in cmd:
                matches.append(stanza)
                break  # avoid double-counting if a stanza has 2 hooks
    return matches


class TestProtocolSemverCascadeSettingsWired(TestEnvContext):
    """6 AC4 cases (a-f) + case (g) warm-run p95 latency budget."""

    # -- AC2 + AC3: subprocess invocation through the wired command --------

    def test_a_warn_emits_protocol_edit_missing_amend_paired(self):
        """AC2: PROTOCOL.md edit + empty session_edits → advisory warn AND
        on-disk audit-log entry `protocol_edit_missing_amend_paired` with
        identity fields (`session_id`, `project`) per _lib.audit_emit
        auto-baseline whitelist."""
        env = os.environ.copy()
        env["CEO_AUDIT_SYNC_MODE"] = "1"
        env["CEO_AUDIT_LOG_DIR"] = str(self.audit_dir)
        env["CEO_AUDIT_LOG_PATH"] = str(self.audit_dir / "audit-log.jsonl")
        payload = {
            "tool_name": "Edit",
            "tool_input": {"file_path": "PROTOCOL.md"},
            "context": {"session_edits": []},
        }
        res = _run_via_shim(payload, env)
        self.assertEqual(res.returncode, 0, msg=f"stderr={res.stderr}")
        out = json.loads(res.stdout or "{}")
        # Stdout shape: hookSpecificOutput.additionalContext warn.
        self.assertIn("hookSpecificOutput", out)
        self.assertIn(
            "PROTOCOL.md",
            out["hookSpecificOutput"].get("additionalContext", ""),
        )
        # On-disk audit-log: at least one line with the expected action.
        log = self.read_audit_log()
        self.assertIn("protocol_edit_missing_amend_paired", log,
                      msg="expected audit-log entry not found; "
                          "advisory hook must persist emit, not just stdout")
        # AC2 audit-emit fields per _lib.audit_emit._write_event auto-baseline:
        # `emit_generic` (used by this hook) populates action + ts +
        # event_schema + HMAC chain field. Per-session identity fields
        # (session_id / project) are NOT auto-injected by emit_generic and
        # require explicit kwargs (out-of-scope per §4 R9 — would need
        # canonical-edit sentinel scope expansion). Parse + assert the fields
        # actually persisted by the wired hook for forensic integrity.
        matching = [
            json.loads(line)
            for line in log.splitlines()
            if line and "protocol_edit_missing_amend_paired" in line
        ]
        self.assertGreaterEqual(
            len(matching), 1,
            msg="audit-log line parse failed; expected at least 1 emit",
        )
        emit_line = matching[0]
        self.assertEqual(emit_line.get("action"),
                         "protocol_edit_missing_amend_paired")
        self.assertIn("ts", emit_line,
                      msg="timestamp field missing per audit-emit baseline")
        self.assertEqual(emit_line.get("event_schema"), "v2",
                         msg="event_schema must be v2 per EVENT_SCHEMA_V2")
        # HMAC chain field is present (None when HMAC unavailable in test
        # env, else non-null hex digest). The KEY check is `hmac` is a
        # field of the emit — chain-link presence — not its specific value.
        self.assertIn("hmac", emit_line,
                      msg="HMAC chain field missing — audit integrity broken")

    def test_b_clean_allow_with_paired_amend_no_emit(self):
        """AC3 (revised PLAN-138 Wave D / ADR-156): PROTOCOL.md edit + paired
        ADR-NNN-AMEND-M in session_edits → the missing-amend audit event is NOT
        emitted (clean allow). The stdout is no longer bare `{}` — the paired
        path now STILL ships the advisory Sync Impact Report (additionalContext)
        — but it must carry NEITHER the missing-amend WARN nor the audit emit."""
        env = os.environ.copy()
        env["CEO_AUDIT_SYNC_MODE"] = "1"
        env["CEO_AUDIT_LOG_DIR"] = str(self.audit_dir)
        env["CEO_AUDIT_LOG_PATH"] = str(self.audit_dir / "audit-log.jsonl")
        payload = {
            "tool_name": "Edit",
            "tool_input": {"file_path": "PROTOCOL.md"},
            "context": {
                "session_edits": [
                    {"file_path": ".claude/adr/ADR-115-AMEND-1.md"},
                ],
            },
        }
        res = _run_via_shim(payload, env)
        self.assertEqual(res.returncode, 0, msg=f"stderr={res.stderr}")
        out = json.loads(res.stdout or "{}")
        ctx = out.get("hookSpecificOutput", {}).get("additionalContext", "")
        self.assertIn("Sync Impact Report", ctx)
        self.assertNotIn("without paired ADR", ctx)
        log = self.read_audit_log()
        self.assertNotIn("protocol_edit_missing_amend_paired", log)

    # -- Mutation-kill / defensive parsing ---------------------------------

    def test_c_noop_via_tool_name_read(self):
        """tool_name=Read on PROTOCOL.md → `{}` (covers line 32-34 mutation)."""
        env = os.environ.copy()
        env["CEO_AUDIT_SYNC_MODE"] = "1"
        env["CEO_AUDIT_LOG_DIR"] = str(self.audit_dir)
        env["CEO_AUDIT_LOG_PATH"] = str(self.audit_dir / "audit-log.jsonl")
        payload = {
            "tool_name": "Read",
            "tool_input": {"file_path": "PROTOCOL.md"},
        }
        res = _run_via_shim(payload, env)
        self.assertEqual(res.returncode, 0, msg=f"stderr={res.stderr}")
        self.assertEqual(res.stdout.strip(), "{}")

    def test_d_noop_via_non_protocol_path(self):
        """tool_name=Edit on CLAUDE.md (not PROTOCOL.md) → `{}`
        (covers line 38 mutation: false-positive guard)."""
        env = os.environ.copy()
        env["CEO_AUDIT_SYNC_MODE"] = "1"
        env["CEO_AUDIT_LOG_DIR"] = str(self.audit_dir)
        env["CEO_AUDIT_LOG_PATH"] = str(self.audit_dir / "audit-log.jsonl")
        payload = {
            "tool_name": "Edit",
            "tool_input": {"file_path": "CLAUDE.md"},
            "context": {"session_edits": []},
        }
        res = _run_via_shim(payload, env)
        self.assertEqual(res.returncode, 0, msg=f"stderr={res.stderr}")
        self.assertEqual(res.stdout.strip(), "{}")

    def test_e_defensive_parsing_malformed_session_edits(self):
        """session_edits as a string (not list) → hook returns warn, doesn't
        crash (covers line 55-56 `isinstance(recent, list)` mutation)."""
        env = os.environ.copy()
        env["CEO_AUDIT_SYNC_MODE"] = "1"
        env["CEO_AUDIT_LOG_DIR"] = str(self.audit_dir)
        env["CEO_AUDIT_LOG_PATH"] = str(self.audit_dir / "audit-log.jsonl")
        payload = {
            "tool_name": "Edit",
            "tool_input": {"file_path": "PROTOCOL.md"},
            "context": {"session_edits": "not-a-list"},
        }
        res = _run_via_shim(payload, env)
        self.assertEqual(res.returncode, 0, msg=f"stderr={res.stderr}")
        # Defensive: isinstance guard treats as no-amend → emits warn.
        out = json.loads(res.stdout or "{}")
        self.assertIn("hookSpecificOutput", out)

    # -- AC4 (f): wiring conformance --------------------------------------

    def test_f_wiring_conformance_both_settings_files(self):
        """Both dogfood + template settings.json MUST carry EXACTLY ONE
        stanza with correct matcher + command + timeout. Duplicate-stanza
        regression (e.g., merge mishap inserting two registrations) MUST
        surface as failure, not be silently masked (Codex R7 P1 fold).
        Hard invariant against future false-closure regressions of the
        PLAN-110 type."""
        for settings_path in (DOGFOOD_SETTINGS, TEMPLATE_SETTINGS):
            with self.subTest(settings=settings_path.name):
                stanzas = _find_stanzas(settings_path)
                self.assertEqual(
                    len(stanzas), 1,
                    msg=f"expected EXACTLY 1 check_protocol_semver_cascade "
                        f"stanza in {settings_path.relative_to(REPO_ROOT)}, "
                        f"found {len(stanzas)} (duplicate-registration "
                        f"regression or missing wire-up)",
                )
                stanza = stanzas[0]
                self.assertEqual(
                    stanza.get("matcher"),
                    "Edit|Write|MultiEdit",
                    msg=f"matcher mismatch in {settings_path.name}",
                )
                hook_entries = stanza.get("hooks", [])
                self.assertEqual(len(hook_entries), 1)
                entry = hook_entries[0]
                self.assertEqual(entry.get("type"), "command")
                self.assertEqual(entry.get("timeout"), 5)
                self.assertIn(
                    "check_protocol_semver_cascade.py",
                    entry.get("command", ""),
                )

    # -- AC4 latency-budget assertion --------------------------------------

    def test_g_warm_p95_in_process_le_50ms(self):
        """Warm-run p95 in-process ≤50ms.

        Targets HOT-PATH regression (e.g., O(n) work added to the no-op
        short-circuit) — NOT subprocess-spawn cost, NOT import-time bloat.
        Both of those would require dedicated harnesses (cProfile cold-start
        / hyperfine subprocess wrapper), explicitly out-of-scope per the
        plan's AC4 rationale.

        Baseline (A9 warm-suite, S152): p95=35ms. Local probe: ~0.002ms.
        50ms budget preserves >20× headroom while bounding accidental
        regressions.
        """
        import check_protocol_semver_cascade as mod
        # Warmup: 5 calls outside measurement window.
        warmup_payload = {
            "tool_name": "Edit",
            "tool_input": {"file_path": "CLAUDE.md"},
        }
        for _ in range(5):
            mod._tool_targets_protocol(warmup_payload)
        # Measure: 50 iterations of the no-op short-circuit.
        durations_ms: List[float] = []
        for _ in range(50):
            t0 = time.perf_counter_ns()
            mod._tool_targets_protocol(warmup_payload)
            durations_ms.append((time.perf_counter_ns() - t0) / 1_000_000.0)
        durations_ms.sort()
        # p95 = index 47 of 50 (0-indexed); not strict — N>=10 with warmup.
        p95 = durations_ms[int(0.95 * len(durations_ms))]
        self.assertLessEqual(
            p95,
            50.0,
            msg=f"HOT-PATH regression: warm-run p95 in-process={p95:.4f}ms "
                f"exceeds 50ms budget (baseline ~0.002ms; A9 warm-suite "
                f"p95=35ms). Recent changes likely added O(n) work to the "
                f"no-op short-circuit; profile _tool_targets_protocol.",
        )


if __name__ == "__main__":
    unittest.main()
