"""Unit tests for debate-orchestrate.py.

PLAN-011 Phase 5. Tests cover:

- --max-rounds cap (default 5; hard cap 10; argparse rejects out-of-range)
- --archetypes CSV parse (known + unknown)
- Round-1 file generation (proposal.md + one file per archetype)
- Round-2 consumes round-1 consolidated critiques with redaction (M6)
- Redaction fixture: secret in round-1 risk text is redacted in
  round-2 input (M6 verification)
- Red Team prompt file generated when Jaccard >= 0.7 at round 2 (M1)
- Audit emit is invoked (through subprocess / fail-open contract)
- CEO_SOTA_DISABLE fallback — single-round mode only
- Plan ID validation
- No emoji / stdlib-only at runtime
"""

from __future__ import annotations

import importlib.util
import io
import os
import shutil
import subprocess
import sys
import tempfile
import unittest
from contextlib import redirect_stdout, redirect_stderr
from pathlib import Path

_SCRIPTS = Path(__file__).resolve().parent.parent
_SCRIPT = _SCRIPTS / "debate-orchestrate.py"
_FIXTURES = Path(__file__).resolve().parent / "fixtures" / "debate_convergence"

_spec = importlib.util.spec_from_file_location("debate_orchestrate", _SCRIPT)
assert _spec is not None and _spec.loader is not None
do = importlib.util.module_from_spec(_spec)
# Register module in sys.modules before exec — required for dataclass
# annotation resolution on Python 3.9 when the class is defined in a
# dynamically loaded module (see also test_debate_converge.py).
sys.modules["debate_orchestrate"] = do
_spec.loader.exec_module(do)


class _EnvIsolatedTest(unittest.TestCase):
    """Snapshot/restore CEO_* env vars + HOME; tempdir plans root."""

    def setUp(self):
        self._snap = {}
        for k in list(os.environ.keys()):
            if k.startswith("CEO_") or k.startswith("CLAUDE_") or k == "HOME":
                self._snap[k] = os.environ.get(k)
        self._tmp = Path(tempfile.mkdtemp(prefix="orchestrate-test-"))
        self._home = self._tmp / "home"
        self._home.mkdir()
        self._audit_dir = self._home / ".claude" / "projects" / "test"
        self._audit_dir.mkdir(parents=True)
        os.environ["HOME"] = str(self._home)
        os.environ["CEO_AUDIT_LOG_DIR"] = str(self._audit_dir)
        os.environ["CEO_AUDIT_LOG_PATH"] = str(self._audit_dir / "audit-log.jsonl")
        os.environ["CEO_AUDIT_LOG_ERR"] = str(self._audit_dir / "audit-log.errors")
        os.environ["CEO_AUDIT_LOG_LOCK"] = str(self._audit_dir / "audit-log.lock")
        # PLAN-107 Wave A.4: force sync mode for emit-read tests
        os.environ["CEO_AUDIT_SYNC_MODE"] = "1"
        # Ensure SOTA is enabled unless a test opts out
        os.environ.pop("CEO_SOTA_DISABLE", None)
        # Plans root inside tempdir
        self._plans_root = self._tmp / "plans"
        self._plans_root.mkdir()

    def tearDown(self):
        for k in list(os.environ.keys()):
            if k.startswith("CEO_") or k.startswith("CLAUDE_") or k == "HOME":
                if k not in self._snap:
                    del os.environ[k]
        for k, v in self._snap.items():
            if v is None:
                os.environ.pop(k, None)
            else:
                os.environ[k] = v
        shutil.rmtree(self._tmp, ignore_errors=True)


class TestArgParsing(_EnvIsolatedTest):

    def test_default_archetypes_parse(self):
        parsed = do._parse_archetypes(",".join(do.DEFAULT_ARCHETYPES))
        self.assertEqual(len(parsed), 6)
        self.assertIn("VPE", parsed)
        self.assertIn("Security", parsed)

    def test_unknown_archetype_rejected(self):
        with self.assertRaises(ValueError):
            do._parse_archetypes("VPE,NotAnArchetype")

    def test_duplicate_archetype_deduped(self):
        parsed = do._parse_archetypes("VPE,VPE,Security")
        self.assertEqual(parsed, ["VPE", "Security"])

    def test_empty_csv_rejected(self):
        with self.assertRaises(ValueError):
            do._parse_archetypes("")

    def test_max_rounds_default_is_5(self):
        # Simulate CLI with only required flags — argparse default
        ns = do._parse(["--plan", "PLAN-999", "--proposal", "test"])
        self.assertEqual(ns.max_rounds, 5)

    def test_max_rounds_hard_cap_enforced(self):
        buf = io.StringIO()
        with redirect_stderr(buf):
            rc = do.main(
                [
                    "--plan",
                    "PLAN-999",
                    "--proposal",
                    "p",
                    "--max-rounds",
                    "11",
                    "--plans-root",
                    str(self._plans_root),
                    "--dry-run",
                ]
            )
        self.assertEqual(rc, 1)
        self.assertIn("max-rounds", buf.getvalue().lower())

    def test_plan_id_format_validated(self):
        buf = io.StringIO()
        with redirect_stderr(buf):
            rc = do.main(
                [
                    "--plan",
                    "notaplan",
                    "--proposal",
                    "p",
                    "--plans-root",
                    str(self._plans_root),
                    "--dry-run",
                ]
            )
        self.assertEqual(rc, 1)


class TestRound1Generation(_EnvIsolatedTest):

    def test_round_1_creates_proposal_and_agent_files(self):
        buf = io.StringIO()
        with redirect_stdout(buf):
            rc = do.main(
                [
                    "--plan",
                    "PLAN-999",
                    "--proposal",
                    "Test proposal body.",
                    "--plans-root",
                    str(self._plans_root),
                    "--archetypes",
                    "VPE,Security,QA",
                    "--dry-run",
                ]
            )
        self.assertEqual(rc, 0)
        round_dir = self._plans_root / "PLAN-999" / "debate" / "round-1"
        self.assertTrue((round_dir / "proposal.md").is_file())
        self.assertTrue((round_dir / "vp-engineering.md").is_file())
        self.assertTrue((round_dir / "security-engineer.md").is_file())
        self.assertTrue((round_dir / "qa-architect.md").is_file())

    def test_round_1_proposal_has_frontmatter(self):
        do.main(
            [
                "--plan",
                "PLAN-999",
                "--proposal",
                "Hello world proposal",
                "--plans-root",
                str(self._plans_root),
                "--archetypes",
                "VPE",
                "--dry-run",
            ]
        )
        text = (
            self._plans_root / "PLAN-999" / "debate" / "round-1" / "proposal.md"
        ).read_text(encoding="utf-8")
        self.assertTrue(text.startswith("---"))
        self.assertIn("plan: PLAN-999", text)
        self.assertIn("Hello world proposal", text)

    def test_round_1_agent_prompt_has_required_sections(self):
        do.main(
            [
                "--plan",
                "PLAN-999",
                "--proposal",
                "p",
                "--plans-root",
                str(self._plans_root),
                "--archetypes",
                "VPE",
                "--dry-run",
            ]
        )
        text = (
            self._plans_root / "PLAN-999" / "debate" / "round-1" / "vp-engineering.md"
        ).read_text(encoding="utf-8")
        for required in (
            "## Verdict",
            "## Summary",
            "## Risks",
            "## Must-fix",
            "## Nice-to-have",
            "## Unseen",
            "## What I would NOT change",
        ):
            self.assertIn(required, text)


class TestRound2Redaction(_EnvIsolatedTest):
    """M6 verification: secret in round-1 -> redacted in round-2 input."""

    def test_secret_in_round_1_is_redacted_in_round_2_input(self):
        # Copy the with-secret fixture's round-1 into our tempdir
        src = _FIXTURES / "with-secret" / "round-1"
        dst_round_1 = self._plans_root / "PLAN-999" / "debate" / "round-1"
        dst_round_1.mkdir(parents=True)
        for f in src.iterdir():
            shutil.copy(f, dst_round_1 / f.name)
        # Generate round-2 — should consume round-1 consolidated+redacted
        buf = io.StringIO()
        with redirect_stdout(buf):
            rc = do.main(
                [
                    "--plan",
                    "PLAN-999",
                    "--round",
                    "2",
                    "--plans-root",
                    str(self._plans_root),
                    "--archetypes",
                    "VPE",
                    "--dry-run",
                ]
            )
        # rc may be 0 or 2 (convergence may fire if risks overlap)
        self.assertIn(rc, (0, 2))
        round_2_file = (
            self._plans_root / "PLAN-999" / "debate" / "round-2" / "vp-engineering.md"
        )
        self.assertTrue(round_2_file.is_file())
        text = round_2_file.read_text(encoding="utf-8")

        # The with-secret fixture contains the literal sk-abcdef...
        # which must be redacted in the round-2 prompt block.
        self.assertNotIn("sk-abcdef0123456789abcdef012345", text)
        # redact_secrets replaces sk-* with [API_KEY]
        self.assertIn("[API_KEY]", text)
        # Also verify the ghp_ GitHub PAT was redacted
        self.assertNotIn("ghp_aBcDeFgHiJkLmNoPqRsTuVwXyZ0123456789", text)
        self.assertIn("[GITHUB_PAT]", text)

    def test_redact_consolidated_is_idempotent_and_nonexpanding(self):
        """Smoke — redaction should not explode the text length."""
        raw = "hello world" * 50
        out1 = do.redact_consolidated(raw)
        out2 = do.redact_consolidated(out1)
        self.assertEqual(out1, out2)
        self.assertLessEqual(len(out1), len(raw) * 2)

    def test_consolidate_round_excludes_non_critique_files(self):
        round_dir = self._plans_root / "r"
        round_dir.mkdir()
        (round_dir / "proposal.md").write_text("PROPOSAL_MARKER", encoding="utf-8")
        (round_dir / "consensus.md").write_text("CONSENSUS_MARKER", encoding="utf-8")
        (round_dir / "agent-a.md").write_text("AGENT_A_MARKER", encoding="utf-8")
        (round_dir / "red-team.md").write_text("RED_TEAM_MARKER", encoding="utf-8")
        out = do.consolidate_round(round_dir)
        self.assertIn("AGENT_A_MARKER", out)
        self.assertNotIn("PROPOSAL_MARKER", out)
        self.assertNotIn("CONSENSUS_MARKER", out)
        self.assertNotIn("RED_TEAM_MARKER", out)

    def test_consolidate_round_anonymizes_critiques(self):
        # DEBATE-SCHEMA §13.2 (PLAN-134 W1, Codex S228 R2 P2): consolidation
        # relabels critiques as Critic-A/B, strips identifying frontmatter,
        # scrubs archetype-name strings (incl. space variants) from bodies,
        # and writes the audit map.
        round_dir = self._plans_root / "PLAN-998" / "debate" / "round-1"
        round_dir.mkdir(parents=True)
        (round_dir / "security-engineer.md").write_text(
            "---\nround: 1\narchetype: Security Engineer\nskill: security-and-auth\n"
            "agent_persona: Marcus\n---\n\n## Risks\n\n"
            "- as security-engineer I flag X\n- the security engineer disagrees\n",
            encoding="utf-8",
        )
        (round_dir / "qa-architect.md").write_text(
            "---\nround: 1\narchetype: QA Architect\n---\n\n## Risks\n\n- QA_MARKER\n",
            encoding="utf-8",
        )
        out = do.consolidate_round(round_dir)
        # labels by sorted filename: qa-architect → Critic-A, security-engineer → Critic-B
        self.assertIn("### Critic-A", out)
        self.assertIn("### Critic-B", out)
        self.assertNotIn("### qa-architect.md", out)
        self.assertNotIn("security-engineer", out)
        self.assertNotIn("security engineer", out)
        self.assertNotIn("archetype:", out)
        self.assertNotIn("skill:", out)
        self.assertNotIn("agent_persona:", out)
        self.assertIn("QA_MARKER", out)  # content survives
        map_file = round_dir / "anonymization-map.md"
        self.assertTrue(map_file.is_file())
        map_text = map_file.read_text(encoding="utf-8")
        self.assertIn("plan: PLAN-998", map_text)
        self.assertIn("round: 1", map_text)
        self.assertIn("Critic-A: qa-architect", map_text)
        self.assertIn("Critic-B: security-engineer", map_text)
        # idempotent re-run: map is NOT consumed as a critique
        out2 = do.consolidate_round(round_dir)
        self.assertEqual(out, out2)


class TestRedTeamTrigger(_EnvIsolatedTest):
    """M1 gate: Jaccard >= 0.7 at round <= 2 -> red-team prompt file."""

    def _write_round(self, num: int, risks: list):
        d = self._plans_root / "PLAN-999" / "debate" / f"round-{num}"
        d.mkdir(parents=True, exist_ok=True)
        bullets = "\n".join(f"- {r}" for r in risks)
        (d / "a.md").write_text(f"## Risks\n\n{bullets}\n", encoding="utf-8")

    def test_red_team_file_generated_when_converged_at_round_2(self):
        # Write round-1 with risks
        self._write_round(
            1,
            [
                "auth token leakage in logs",
                "rate limit missing on public endpoint",
                "redis connection exhaustion in burst",
                "schema migration missing rollback",
            ],
        )
        # Write round-2 with same risks so Jaccard == 1.0
        self._write_round(
            2,
            [
                "auth token leakage in logs",
                "rate limit missing on public endpoint",
                "redis connection exhaustion in burst",
                "schema migration missing rollback",
            ],
        )
        # Call the orchestrator's direct red-team helper
        rt_path = do.maybe_trigger_red_team(
            self._plans_root,
            "PLAN-999",
            2,
            0.7,
            dry_run=True,
        )
        self.assertIsNotNone(rt_path)
        self.assertTrue(rt_path.is_file())
        text = rt_path.read_text(encoding="utf-8")
        self.assertIn("archetype: Red Team", text)
        self.assertIn("chaos-and-resilience", text)
        self.assertIn("security-and-auth", text)
        self.assertIn("M1 anti-groupthink gate", text)

    def test_no_red_team_when_divergent(self):
        self._write_round(1, ["risk aaa", "risk bbb"])
        self._write_round(2, ["risk ccc", "risk ddd"])
        rt_path = do.maybe_trigger_red_team(
            self._plans_root,
            "PLAN-999",
            2,
            0.7,
            dry_run=True,
        )
        self.assertIsNone(rt_path)

    def test_no_red_team_when_converged_at_round_3(self):
        # Round-3 convergence -> NOT red-team (gate only fires <= 2)
        self._write_round(2, ["x one", "x two", "x three"])
        self._write_round(3, ["x one", "x two", "x three"])
        rt_path = do.maybe_trigger_red_team(
            self._plans_root,
            "PLAN-999",
            3,
            0.7,
            dry_run=True,
        )
        self.assertIsNone(rt_path)


class TestSotaDisableFallback(_EnvIsolatedTest):

    def test_sota_disable_restricts_to_round_1(self):
        os.environ["CEO_SOTA_DISABLE"] = "1"
        buf = io.StringIO()
        err = io.StringIO()
        with redirect_stdout(buf), redirect_stderr(err):
            rc = do.main(
                [
                    "--plan",
                    "PLAN-999",
                    "--proposal",
                    "p",
                    "--round",
                    "2",
                    "--plans-root",
                    str(self._plans_root),
                    "--dry-run",
                ]
            )
        self.assertEqual(rc, 1)
        self.assertIn("SOTA", err.getvalue())

    def test_sota_disable_single_round_succeeds(self):
        os.environ["CEO_SOTA_DISABLE"] = "1"
        buf = io.StringIO()
        with redirect_stdout(buf):
            rc = do.main(
                [
                    "--plan",
                    "PLAN-999",
                    "--proposal",
                    "single round proposal",
                    "--plans-root",
                    str(self._plans_root),
                    "--dry-run",
                ]
            )
        self.assertEqual(rc, 0)
        out = buf.getvalue()
        self.assertIn("SOTA disabled", out)
        self.assertTrue(
            (
                self._plans_root
                / "PLAN-999"
                / "debate"
                / "round-1"
                / "proposal.md"
            ).is_file()
        )


class TestAuditEmission(_EnvIsolatedTest):
    """Verify audit events are emitted per round phase (not dry-run)."""

    def _read_audit_log(self):
        log = self._audit_dir / "audit-log.jsonl"
        if not log.is_file():
            return []
        import json as _json
        out = []
        for line in log.read_text(encoding="utf-8").splitlines():
            line = line.strip()
            if not line:
                continue
            try:
                out.append(_json.loads(line))
            except Exception:
                continue
        return out

    def test_round_1_emits_audit_events(self):
        # Non-dry-run -> audit events should land in the isolated log
        rc = do.main(
            [
                "--plan",
                "PLAN-999",
                "--proposal",
                "p",
                "--plans-root",
                str(self._plans_root),
                "--archetypes",
                "VPE",
            ]
        )
        self.assertEqual(rc, 0)
        events = self._read_audit_log()
        actions = {e.get("action") for e in events}
        self.assertIn("debate_event", actions)
        # Expect at least a 'start' event
        phases = {e.get("phase") for e in events if e.get("action") == "debate_event"}
        self.assertIn("start", phases)


class TestRoundNProgression(_EnvIsolatedTest):

    def test_generate_round_2_requires_round_1(self):
        with self.assertRaises(FileNotFoundError):
            do.generate_round_n(
                self._plans_root, "PLAN-999", 2, ["VPE"], dry_run=True
            )

    def test_generate_round_n_rejects_round_1(self):
        with self.assertRaises(ValueError):
            do.generate_round_n(
                self._plans_root, "PLAN-999", 1, ["VPE"], dry_run=True
            )


class TestMaxRoundsEnforcement(_EnvIsolatedTest):
    """MAX_ROUNDS=5 terminal enforcement (PLAN-012 chaos CRITICAL-2)."""

    def _seed(self, highest: int, risks=None) -> None:
        base = self._plans_root / "PLAN-999" / "debate"
        for r in range(1, highest + 1):
            d = base / f"round-{r}"
            d.mkdir(parents=True, exist_ok=True)
            body = ("\n".join(f"- {x}" for x in risks) + "\n"
                    if risks is not None else f"- unique round {r} risk\n")
            (d / "a.md").write_text(f"## Risks\n\n{body}", encoding="utf-8")

    def _cli(self, dry_run=True):
        args = ["--plan", "PLAN-999", "--round", "5", "--plans-root",
                str(self._plans_root), "--archetypes", "VPE", "--max-rounds", "5"]
        if dry_run:
            args.append("--dry-run")
        buf, err = io.StringIO(), io.StringIO()
        with redirect_stdout(buf), redirect_stderr(err):
            rc = do.main(args)
        return rc, err.getvalue()

    def _audit(self):
        import json as _json
        log = self._audit_dir / "audit-log.jsonl"
        if not log.is_file():
            return []
        out = []
        for line in log.read_text(encoding="utf-8").splitlines():
            try:
                out.append(_json.loads(line))
            except Exception:
                pass
        return out

    def test_exit_code_max_rounds_reached_constant_exists(self):
        self.assertTrue(hasattr(do, "EXIT_MAX_ROUNDS_REACHED"))
        self.assertEqual(do.EXIT_MAX_ROUNDS_REACHED, 3)

    def test_orchestrator_exits_with_max_rounds_code(self):
        self._seed(5)
        rc, err = self._cli()
        self.assertEqual(rc, 3)
        self.assertIn("MAX_ROUNDS", err)
        self.assertIn("Terminating", err)
        consensus = self._plans_root / "PLAN-999" / "debate" / "round-5" / "consensus.md"
        self.assertTrue(consensus.is_file())
        self.assertIn("status: unresolved", consensus.read_text(encoding="utf-8"))

    def test_orchestrator_emits_audit_on_max_rounds(self):
        self._seed(5)
        rc, _err = self._cli(dry_run=False)
        self.assertEqual(rc, 3)
        term = [e for e in self._audit()
                if e.get("action") == "debate_event"
                and e.get("phase") == "terminated_max_rounds"]
        self.assertEqual(len(term), 1)
        self.assertEqual(term[0].get("round"), 5)
        self.assertEqual(term[0].get("agent"), "orchestrator")

    def test_orchestrator_does_not_trigger_red_team_at_max_rounds(self):
        # Identical risks -> Jaccard=1.0; MAX_ROUNDS still overrides red-team.
        self._seed(5, ["shared a", "shared b", "shared c"])
        rc, _err = self._cli()
        self.assertEqual(rc, 3)  # NOT 2 (red-team) / NOT 0
        red_team = self._plans_root / "PLAN-999" / "debate" / "round-6" / "red-team.md"
        self.assertFalse(red_team.is_file())


if __name__ == "__main__":
    unittest.main()
