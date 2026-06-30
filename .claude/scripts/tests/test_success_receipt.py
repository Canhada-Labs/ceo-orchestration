"""Unit tests for success-receipt.py (PLAN-083 Wave 2 sub-2.3).

Stdlib unittest, no third-party imports. The module under test is loaded
by `importlib.util.spec_from_file_location` so the hyphen in the
filename doesn't block normal `import`.

Coverage targets (per task brief):

- 5-section structure always present (even with empty data)
- Sec MF-3 — file paths bucketed not leaked
- Risk severity aggregation correct
- `--for-ctov` adds methodology disclaimers
- `--json` schema valid
- Cost USD derived from audit events (mirrors budget-summary pricing)
- Top-3 next-move recommendations gated on signals
"""

from __future__ import annotations

import importlib.util
import io
import json
import os
import tempfile
import unittest
from datetime import datetime, timedelta, timezone
from pathlib import Path
from typing import Any, Dict, List


# ---------------------------------------------------------------------------
# Module load (handle hyphen in filename)
# ---------------------------------------------------------------------------

_HERE = Path(__file__).resolve().parent
_SRC = _HERE.parent / "success-receipt.py"
_spec = importlib.util.spec_from_file_location("success_receipt", str(_SRC))
assert _spec is not None and _spec.loader is not None
sr = importlib.util.module_from_spec(_spec)
_spec.loader.exec_module(sr)  # type: ignore[union-attr]


# ---------------------------------------------------------------------------
# Fixture helpers
# ---------------------------------------------------------------------------


def _ev(action: str, **kw: Any) -> Dict[str, Any]:
    """Build a minimal event dict with a stable canonical timestamp."""
    base: Dict[str, Any] = {
        "action": action,
        "ts": kw.pop("ts", "2026-05-11T12:00:00+0000"),
        "session_id": kw.pop("session_id", "S-TEST"),
        "project": kw.pop("project", "ceo-orchestration"),
        "event_schema": kw.pop("event_schema", "v2"),
    }
    base.update(kw)
    return base


def _write_log(events: List[Dict[str, Any]]) -> Path:
    """Write events to a tempdir audit-log.jsonl; return the dir."""
    tmpdir = Path(tempfile.mkdtemp(prefix="receipt-test-"))
    logp = tmpdir / "audit-log.jsonl"
    with logp.open("w", encoding="utf-8") as f:
        for ev in events:
            f.write(json.dumps(ev) + "\n")
    return tmpdir


# ---------------------------------------------------------------------------
# Tests
# ---------------------------------------------------------------------------


class StructuralInvariants(unittest.TestCase):
    """5-section structure always present, even on empty data."""

    def test_empty_input_still_returns_all_5_sections(self) -> None:
        tmpdir = _write_log([])
        payload = sr.assemble_receipt(audit_dir=tmpdir)
        for key in ("files_inspected", "risks_found", "actions_taken",
                    "value_created", "next_move"):
            self.assertIn(key, payload, f"missing section: {key}")

    def test_files_inspected_zero_state(self) -> None:
        tmpdir = _write_log([])
        payload = sr.assemble_receipt(audit_dir=tmpdir)
        files = payload["files_inspected"]
        self.assertEqual(files["total"], 0)
        self.assertEqual(files["top_categories"], [])
        self.assertEqual(files["categories_seen"], 0)

    def test_risks_zero_state_has_all_three_severities(self) -> None:
        tmpdir = _write_log([])
        payload = sr.assemble_receipt(audit_dir=tmpdir)
        sev = payload["risks_found"]["by_severity"]
        for k in ("critical", "error", "warn"):
            self.assertIn(k, sev)
            self.assertEqual(sev[k], 0)

    def test_value_created_zero_state_is_well_formed(self) -> None:
        tmpdir = _write_log([])
        payload = sr.assemble_receipt(audit_dir=tmpdir)
        v = payload["value_created"]
        self.assertEqual(v["bugs_caught"], 0)
        self.assertEqual(v["artifacts_produced"], 0)
        self.assertEqual(v["tokens_total"], 0)
        self.assertIsNone(v["cost_usd"])

    def test_next_move_zero_state_has_default_rec(self) -> None:
        tmpdir = _write_log([])
        payload = sr.assemble_receipt(audit_dir=tmpdir)
        recs = payload["next_move"]["recommendations"]
        self.assertEqual(len(recs), 1)
        self.assertEqual(recs[0]["action"], "review-summary-and-plan-next")


class FilePathBucketing(unittest.TestCase):
    """Sec MF-3 — raw paths bucketed into category counters, never leaked."""

    def test_bucket_classification_known_categories(self) -> None:
        self.assertEqual(sr.bucket_path(".claude/plans/PLAN-083.md"), "plans")
        self.assertEqual(sr.bucket_path(".claude/hooks/check_x.py"), "hooks")
        self.assertEqual(sr.bucket_path(".claude/skills/core/x/SKILL.md"), "skills")
        self.assertEqual(sr.bucket_path(".claude/adr/ADR-001.md"), "adrs")
        self.assertEqual(sr.bucket_path(".claude/scripts/foo.py"), "scripts")
        self.assertEqual(sr.bucket_path(".claude/policies/x.yaml"), "policies")
        self.assertEqual(sr.bucket_path("tests/test_foo.py"), "tests")
        self.assertEqual(sr.bucket_path("README.md"), "docs")
        self.assertEqual(sr.bucket_path("repo-profile.yaml"), "config")
        self.assertEqual(sr.bucket_path("main.py"), "source")

    def test_bucket_returns_other_for_unknown(self) -> None:
        self.assertEqual(sr.bucket_path("/etc/passwd"), "other")
        self.assertEqual(sr.bucket_path(""), "other")

    def test_paths_never_appear_in_rendered_markdown(self) -> None:
        # Sensitive paths in events — must not appear verbatim in output.
        sensitive_paths = [
            "/Users/devuser/secret-token.txt",
            ".env",
            ".claude/plans/PLAN-099-confidential.md",
            "/root/.ssh/id_rsa",
            "src/proprietary_strategy.py",
        ]
        events = [_ev("edit_applied", file_path=p) for p in sensitive_paths]
        tmpdir = _write_log(events)
        payload = sr.assemble_receipt(audit_dir=tmpdir)
        md = sr.render_markdown(payload)
        j = sr.render_json(payload)
        for p in sensitive_paths:
            # Match on the leaf-name part of each path (most-likely to slip).
            leaf = os.path.basename(p)
            self.assertNotIn(leaf, md,
                             f"leaked leaf {leaf!r} in markdown")
            self.assertNotIn(leaf, j,
                             f"leaked leaf {leaf!r} in JSON")

    def test_bucket_counts_are_emitted_not_raw_paths(self) -> None:
        events = [
            _ev("edit_applied", file_path=".claude/plans/p.md",
                ts="2026-05-11T12:00:01+0000"),
            _ev("edit_applied", file_path=".claude/plans/q.md",
                ts="2026-05-11T12:00:02+0000"),
            _ev("edit_applied", file_path=".claude/hooks/h.py",
                ts="2026-05-11T12:00:03+0000"),
        ]
        tmpdir = _write_log(events)
        payload = sr.assemble_receipt(audit_dir=tmpdir)
        files = payload["files_inspected"]
        self.assertEqual(files["total"], 3)
        cats = {row["category"]: row["count"] for row in files["top_categories"]}
        self.assertEqual(cats.get("plans"), 2)
        self.assertEqual(cats.get("hooks"), 1)


class RiskSeverityAggregation(unittest.TestCase):
    """Risk events grouped by severity bucket."""

    def test_three_severities_aggregate_correctly(self) -> None:
        events = [
            _ev("mcp_canonical_guard_blocked"),    # critical
            _ev("injection_flag"),                 # error
            _ev("confidence_gate"),                # warn
        ]
        tmpdir = _write_log(events)
        payload = sr.assemble_receipt(audit_dir=tmpdir)
        sev = payload["risks_found"]["by_severity"]
        self.assertEqual(sev["critical"], 1)
        self.assertEqual(sev["error"], 1)
        self.assertEqual(sev["warn"], 1)
        self.assertEqual(payload["risks_found"]["total"], 3)

    def test_unknown_action_not_counted_as_risk(self) -> None:
        events = [
            _ev("agent_spawn"),  # not a risk
            _ev("plan_status_transition"),  # not a risk
        ]
        tmpdir = _write_log(events)
        payload = sr.assemble_receipt(audit_dir=tmpdir)
        self.assertEqual(payload["risks_found"]["total"], 0)

    def test_top_actions_sorted_descending(self) -> None:
        # Each event must be canonically unique (different ts) to bypass
        # the rotation-overlap dedup (see _canonical_event_sha256).
        events = [
            _ev("injection_flag", ts="2026-05-11T12:00:01+0000"),
            _ev("injection_flag", ts="2026-05-11T12:00:02+0000"),
            _ev("injection_flag", ts="2026-05-11T12:00:03+0000"),
            _ev("confidence_gate", ts="2026-05-11T12:00:04+0000"),
        ]
        tmpdir = _write_log(events)
        payload = sr.assemble_receipt(audit_dir=tmpdir)
        top = payload["risks_found"]["top_actions"]
        self.assertEqual(top[0]["action"], "injection_flag")
        self.assertEqual(top[0]["count"], 3)


class ActionsTaken(unittest.TestCase):
    """Edits / commits / GPG / spawns / transitions bucketed correctly."""

    def test_five_action_kinds_aggregate(self) -> None:
        events = [
            _ev("edit_applied"),
            _ev("git_commit"),
            _ev("sentinel_signed"),
            _ev("agent_spawn"),
            _ev("plan_status_transition", plan_id="PLAN-083",
                to_status="executing"),
        ]
        tmpdir = _write_log(events)
        payload = sr.assemble_receipt(audit_dir=tmpdir)
        kinds = payload["actions_taken"]["by_kind"]
        self.assertEqual(kinds["edits_writes"], 1)
        self.assertEqual(kinds["commits"], 1)
        self.assertEqual(kinds["gpg_ceremonies"], 1)
        self.assertEqual(kinds["subagent_spawns"], 1)
        self.assertEqual(kinds["plan_transitions"], 1)


class ValueCreated(unittest.TestCase):
    """Cost USD derived from token-bearing events."""

    def test_cost_usd_computed_for_known_model(self) -> None:
        events = [
            _ev("agent_spawn", model="claude-sonnet-4-5",
                tokens_in=10000, tokens_out=5000),
        ]
        tmpdir = _write_log(events)
        payload = sr.assemble_receipt(audit_dir=tmpdir)
        # sonnet-4-5: in=0.003/1k * 10k + out=0.015/1k * 5k = 0.03 + 0.075 = 0.105
        self.assertAlmostEqual(payload["value_created"]["cost_usd"],
                               0.105, places=4)

    def test_cost_usd_none_when_no_known_model(self) -> None:
        events = [_ev("agent_spawn", tokens_in=10000, tokens_out=5000)]
        tmpdir = _write_log(events)
        payload = sr.assemble_receipt(audit_dir=tmpdir)
        self.assertIsNone(payload["value_created"]["cost_usd"])

    def test_bugs_caught_counts_critical_plus_error(self) -> None:
        events = [
            _ev("mcp_canonical_guard_blocked"),  # critical
            _ev("injection_flag"),               # error
            _ev("confidence_gate"),              # warn — not counted
        ]
        tmpdir = _write_log(events)
        payload = sr.assemble_receipt(audit_dir=tmpdir)
        self.assertEqual(payload["value_created"]["bugs_caught"], 2)

    def test_tokens_saved_estimate_nonnegative(self) -> None:
        events = [
            _ev("agent_spawn", model="claude-sonnet-4-5",
                tokens_in=1000, tokens_out=1000),
        ]
        tmpdir = _write_log(events)
        payload = sr.assemble_receipt(audit_dir=tmpdir)
        # Should always be >= 0 (clamped).
        self.assertGreaterEqual(
            payload["value_created"]["tokens_saved_usd_estimate"], 0.0
        )


class NextMoveRecommender(unittest.TestCase):
    """Top-3 next-move recommendations gated on signals."""

    def test_critical_risk_triggers_investigate_rec(self) -> None:
        events = [_ev("mcp_canonical_guard_blocked")]
        tmpdir = _write_log(events)
        payload = sr.assemble_receipt(audit_dir=tmpdir)
        recs = payload["next_move"]["recommendations"]
        self.assertEqual(recs[0]["action"], "investigate-critical-risks")

    def test_executing_plan_triggers_continue_rec(self) -> None:
        events = [
            _ev("plan_status_transition", plan_id="PLAN-083",
                to_status="executing"),
        ]
        tmpdir = _write_log(events)
        payload = sr.assemble_receipt(audit_dir=tmpdir)
        actions_set = {r["action"] for r in payload["next_move"]["recommendations"]}
        self.assertIn("continue-plan-execution", actions_set)

    def test_max_three_recommendations(self) -> None:
        events = [
            _ev("mcp_canonical_guard_blocked"),
            _ev("injection_flag"),
            _ev("plan_status_transition", plan_id="PLAN-083",
                to_status="executing"),
            _ev("git_commit"),
            _ev("plan_status_transition", plan_id="PLAN-084",
                to_status="reviewed"),
        ]
        tmpdir = _write_log(events)
        payload = sr.assemble_receipt(audit_dir=tmpdir)
        self.assertLessEqual(len(payload["next_move"]["recommendations"]), 3)


class CtovFlagBehavior(unittest.TestCase):
    """`--for-ctov` adds methodology disclaimers."""

    def test_markdown_with_ctov_includes_methodology_section(self) -> None:
        tmpdir = _write_log([_ev("agent_spawn")])
        payload = sr.assemble_receipt(audit_dir=tmpdir)
        md_plain = sr.render_markdown(payload, for_ctov=False)
        md_ctov = sr.render_markdown(payload, for_ctov=True)
        self.assertNotIn("Methodology (for CTO review)", md_plain)
        self.assertIn("Methodology (for CTO review)", md_ctov)
        # Concrete disclaimer phrases per Codex P1:
        self.assertIn("estimates", md_ctov.lower())
        self.assertIn("baseline", md_ctov.lower())

    def test_json_with_ctov_adds_disclaimers_array(self) -> None:
        tmpdir = _write_log([_ev("agent_spawn")])
        payload = sr.assemble_receipt(audit_dir=tmpdir)
        j_plain = json.loads(sr.render_json(payload, for_ctov=False))
        j_ctov = json.loads(sr.render_json(payload, for_ctov=True))
        self.assertNotIn("methodology_disclaimers", j_plain)
        self.assertIn("methodology_disclaimers", j_ctov)
        self.assertGreaterEqual(len(j_ctov["methodology_disclaimers"]), 3)


class JsonSchemaShape(unittest.TestCase):
    """`--json` output is valid JSON with the required top-level keys."""

    def test_json_valid_and_has_required_keys(self) -> None:
        tmpdir = _write_log([_ev("agent_spawn")])
        payload = sr.assemble_receipt(audit_dir=tmpdir)
        j = sr.render_json(payload)
        parsed = json.loads(j)
        for key in (
            "schema_version", "generated_at", "scope",
            "files_inspected", "risks_found", "actions_taken",
            "value_created", "next_move",
        ):
            self.assertIn(key, parsed, f"missing top-level key: {key}")

    def test_schema_version_is_v1(self) -> None:
        tmpdir = _write_log([])
        payload = sr.assemble_receipt(audit_dir=tmpdir)
        self.assertEqual(payload["schema_version"], "v1")


class ScopeFiltering(unittest.TestCase):
    """Session / plan / since filters apply correctly."""

    def test_session_id_filter_restricts_events(self) -> None:
        events = [
            _ev("agent_spawn", session_id="S-1"),
            _ev("agent_spawn", session_id="S-2"),
        ]
        tmpdir = _write_log(events)
        payload = sr.assemble_receipt(audit_dir=tmpdir, session_id="S-1")
        self.assertEqual(payload["events_in_scope"], 1)
        self.assertEqual(payload["scope"]["session_id"], "S-1")

    def test_plan_id_filter_restricts_events(self) -> None:
        events = [
            _ev("agent_spawn", plan_id="PLAN-083"),
            _ev("agent_spawn", plan_id="PLAN-084"),
            _ev("agent_spawn"),  # no plan_id
        ]
        tmpdir = _write_log(events)
        payload = sr.assemble_receipt(audit_dir=tmpdir, plan_id="PLAN-083")
        self.assertEqual(payload["events_in_scope"], 1)

    def test_since_filter_respects_cutoff(self) -> None:
        events = [
            _ev("agent_spawn", ts="2026-05-01T00:00:00+0000"),  # old
            _ev("agent_spawn", ts="2026-05-11T12:00:00+0000"),  # recent
        ]
        tmpdir = _write_log(events)
        now = datetime(2026, 5, 11, 13, 0, 0, tzinfo=timezone.utc)
        payload = sr.assemble_receipt(
            audit_dir=tmpdir,
            since=timedelta(hours=2),
            now=now,
        )
        self.assertEqual(payload["events_in_scope"], 1)


class CliEndToEnd(unittest.TestCase):
    """`main()` produces JSON when --json is given."""

    def test_main_json_returns_zero_exit(self) -> None:
        events = [_ev("agent_spawn", model="claude-sonnet-4-5",
                      tokens_in=1000, tokens_out=500)]
        tmpdir = _write_log(events)
        # Redirect stdout to capture.
        import contextlib
        buf = io.StringIO()
        with contextlib.redirect_stdout(buf):
            rc = sr.main([
                "--audit-dir", str(tmpdir), "--json",
            ])
        self.assertEqual(rc, 0)
        parsed = json.loads(buf.getvalue())
        self.assertEqual(parsed["schema_version"], "v1")

    def test_main_rejects_invalid_plan_id(self) -> None:
        rc = sr.main(["--plan-id", "not-a-plan"])
        self.assertEqual(rc, 2)

    def test_main_rejects_invalid_since(self) -> None:
        rc = sr.main(["--since", "forever"])
        self.assertEqual(rc, 2)


class MarkdownStructure(unittest.TestCase):
    """Markdown receipt has all 5 numbered section headings."""

    def test_markdown_contains_all_5_section_headings(self) -> None:
        tmpdir = _write_log([])
        payload = sr.assemble_receipt(audit_dir=tmpdir)
        md = sr.render_markdown(payload)
        for heading in (
            "## 1. Files inspected",
            "## 2. Risks found",
            "## 3. Actions taken",
            "## 4. Value created",
            "## 5. Next move",
        ):
            self.assertIn(heading, md, f"missing section heading: {heading}")


if __name__ == "__main__":
    unittest.main()
