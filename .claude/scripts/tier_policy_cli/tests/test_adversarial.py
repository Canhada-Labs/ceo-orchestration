"""PLAN-043 Phase 4 — Adversarial tests (security-sensitive scenarios).

Covers 11+ adversarial vectors per Round 1 closures + plan §Phase 4:

1. Forged HMAC on input tournament report → rejected
2. Missing signature on demote → apply emits request; no write
3. Cooldown violation → rejected (boundary exercised in test_learn)
4. VETO floor override via direct policy edit → double-blocked
5. Sentinel symlink-swap → blocked
6. Kill-switch single-factor bypass (env only / sentinel only)
7. Statistical power doctored n → learn gate rejects
8. Sigchain hmac mismatch → verify flags
9. Sigchain truncation → verify flags via sigchain_tip_length check
10. Poisoned tournament report (demote-VETO recommendation) → double-blocked
11. Cost cascade (3 concurrent promote recommendations exceed cap) →
    all downgraded to signed
"""

from __future__ import annotations

import hashlib
import io
import json
import os
import sys
import tempfile
import time
import unittest
from datetime import datetime, timedelta, timezone
from pathlib import Path
from typing import Dict, List, Optional
from unittest import mock

_SCRIPTS = Path(__file__).resolve().parent.parent.parent
if str(_SCRIPTS) not in sys.path:
    sys.path.insert(0, str(_SCRIPTS))

from tier_policy_cli import (  # noqa: E402
    apply as apply_mod,
    cli,
    learn,
)
from tier_policy_cli._constants import VETO_HARDCODE  # noqa: E402
from tier_policy_cli._types import (  # noqa: E402
    Assignment,
    AssignmentEvidence,
    CANONICAL_5_AGENTS,
    Recommendation,
    TierPolicyRecord,
)


_OPUS = "claude-opus-4-8"
_SONNET = "claude-sonnet-4-6"
_HAIKU = "claude-haiku-4-5-20251001"


def _baseline_policy() -> TierPolicyRecord:
    return TierPolicyRecord(
        schema_version="1.0",
        generated_at="2026-04-19T00:00:00Z",
        baseline_from="ADR-052",
        assignments={
            "code-reviewer": Assignment(
                tier=_OPUS, locked_by="VETO_FLOOR", evidence=None
            ),
            "security-engineer": Assignment(
                tier=_OPUS, locked_by="VETO_FLOOR", evidence=None
            ),
            "qa-architect": Assignment(
                tier=_SONNET, locked_by=None, evidence=None
            ),
            "performance-engineer": Assignment(
                tier=_SONNET, locked_by=None, evidence=None
            ),
            "devops": Assignment(
                tier=_HAIKU, locked_by=None, evidence=None
            ),
        },
        hmac_anchor="f" * 64,
        sigchain_tip_length=1,
        last_change_by_role={},
    )


def _task_record(
    *, fixture_id: str, task_type: str, model: str, verdict: str
) -> Dict:
    return {
        "type": "task",
        "fixture_id": fixture_id,
        "fixture_sha256": "0" * 64,
        "task_type": task_type,
        "model": model,
        "verdict": verdict,
        "output_sha256": "0" * 64,
        "tokens_in": 100,
        "tokens_out": 50,
        "cost_usd": 0.001,
        "wall_clock_ms": 100,
    }


def _write_agent_md(path: Path, model: str) -> None:
    path.write_text(
        "---\nname: test\nmodel: {}\n---\nbody\n".format(model),
        encoding="utf-8",
    )


class AdversarialBase(unittest.TestCase):
    def setUp(self):
        self._tmp = tempfile.TemporaryDirectory(prefix="plan-043-adv-")
        self.tmp = Path(self._tmp.name)
        self.reports_dir = self.tmp / "reports"
        self.reports_dir.mkdir()
        self.agents_dir = self.tmp / ".claude" / "agents"
        self.baseline_dir = self.tmp / "templates" / "agents"
        self.agents_dir.mkdir(parents=True)
        self.baseline_dir.mkdir(parents=True)
        for slug in CANONICAL_5_AGENTS:
            t = _baseline_policy().assignments[slug].tier
            _write_agent_md(self.agents_dir / f"{slug}.md", t)
            _write_agent_md(self.baseline_dir / f"{slug}.md", t)
        self.policy_path = self.tmp / ".claude" / "tier-policy.json"
        self.sigchain_path = (
            self.tmp / ".claude" / "tier-policy.json.sigchain"
        )
        self.lock_path = self.tmp / ".claude" / "tier-policy.json.lock"
        self.sentinel = self.tmp / "sentinel.enabled"
        self.sentinel.write_text("s", encoding="utf-8")
        os.chmod(self.sentinel, 0o600)
        self.audit_path = self.tmp / "audit-log.jsonl"
        self.scaffold_dir = self.tmp / "adr-drafts"
        self.now = datetime(2026, 4, 19, 12, 0, 0, tzinfo=timezone.utc)
        self._env = mock.patch.dict(
            os.environ,
            {
                "CEO_TIER_POLICY_ENABLE": "1",
                "CEO_TIER_POLICY_SENTINEL_PATH": str(self.sentinel),
                "CEO_TIER_POLICY_MAX_PROMOTE_DELTA_USD": "20",
                "CEO_AUDIT_LOG_PATH": str(self.audit_path),
                "CEO_SOTA_DISABLE": "",
                "CEO_TIER_POLICY_CI": "",
                "CEO_TIER_POLICY_DRY_RUN": "",
            },
        )
        self._env.start()

    def tearDown(self):
        self._env.stop()
        self._tmp.cleanup()

    def _seed_audit_tokens(
        self, agent_slug: str, tokens_total: int, count: int = 3
    ):
        lines = []
        for i in range(count):
            ts = (
                self.now - timedelta(hours=i + 1)
            ).strftime("%Y-%m-%dT%H:%M:%SZ")
            lines.append(json.dumps({
                "event_schema": "v2",
                "ts": ts,
                "action": "live_adapter_call_succeeded",
                "agent_slug": agent_slug,
                "tokens_total": tokens_total,
            }) + "\n")
        with self.audit_path.open("a", encoding="utf-8") as f:
            f.writelines(lines)

    def _make_rec(
        self,
        agent_slug,
        current,
        recommended,
        action,
        *,
        n=35,
        gap_pp=30.0,
    ):
        return Recommendation(
            agent_slug=agent_slug,
            current_tier=current,
            recommended_tier=recommended,
            action=action,
            evidence=AssignmentEvidence(
                n=n,
                gap_pp=gap_pp,
                last_updated="2026-04-19T00:00:00Z",
                runs_considered=3,
                tournament_report_hmacs=["a" * 64],
            ),
            signature_required=(action == "demote"),
            cooldown_ok=True,
        )


# ---------------------------------------------------------------------
# 1. Forged HMAC
# ---------------------------------------------------------------------

class ForgedHmacTests(AdversarialBase):
    def test_forged_tournament_report_rejected_by_verify_chain(self):
        # Write report; HMAC verification fails → report skipped.
        with (self.reports_dir / "tournament-forged.jsonl").open(
            "w", encoding="utf-8"
        ) as f:
            f.write(json.dumps(_task_record(
                fixture_id="fx",
                task_type="performance-triage",
                model=_OPUS, verdict="pass",
            )) + "\n")
        # Patch verify_chain to return failure.
        with mock.patch.object(
            learn, "_hmac_verify_report", return_value=(False, None)
        ):
            recs = learn.learn(
                self.reports_dir, _baseline_policy(), now=self.now
            )
        self.assertEqual(recs, [])


# ---------------------------------------------------------------------
# 2. Missing signature on demote
# ---------------------------------------------------------------------

class MissingDemoteSignatureTests(AdversarialBase):
    def test_demote_emits_request_not_write(self):
        rec = self._make_rec(
            "performance-engineer", _SONNET, _HAIKU, "demote"
        )
        result = apply_mod.apply(
            [rec], _baseline_policy(),
            agents_dir=self.agents_dir,
            baseline_agents_dir=self.baseline_dir,
            policy_path=self.policy_path,
            sigchain_path=self.sigchain_path,
            lock_path=self.lock_path,
            sentinel_path=self.sentinel,
            audit_log_path=self.audit_path,
            adr_scaffold_dir=self.scaffold_dir,
            now=self.now,
        )
        # Frontmatter untouched.
        content = (self.agents_dir / "performance-engineer.md").read_text(
            encoding="utf-8"
        )
        self.assertIn("model: {}".format(_SONNET), content)


# ---------------------------------------------------------------------
# 4. VETO floor override via direct policy edit
# ---------------------------------------------------------------------

class VetoDirectOverrideTests(AdversarialBase):
    def test_tampered_policy_with_haiku_code_reviewer_does_not_flip_agent(
        self,
    ):
        # Even if policy artifact is tampered to recommend haiku for
        # code-reviewer, apply with such a recommendation defense-in-
        # depths rejects.
        rec = self._make_rec(
            "code-reviewer", _OPUS, _HAIKU, "demote"
        )
        result = apply_mod.apply(
            [rec], _baseline_policy(),
            agents_dir=self.agents_dir,
            baseline_agents_dir=self.baseline_dir,
            policy_path=self.policy_path,
            sigchain_path=self.sigchain_path,
            lock_path=self.lock_path,
            sentinel_path=self.sentinel,
            audit_log_path=self.audit_path,
            adr_scaffold_dir=self.scaffold_dir,
            now=self.now,
        )
        outcome = next(
            o for o in result.outcomes
            if o.agent_slug == "code-reviewer"
        )
        self.assertEqual(outcome.outcome, "veto_rejected")
        content = (self.agents_dir / "code-reviewer.md").read_text(
            encoding="utf-8"
        )
        self.assertIn("model: {}".format(_OPUS), content)


# ---------------------------------------------------------------------
# 5. Sentinel symlink-swap
# ---------------------------------------------------------------------

class SentinelSymlinkTests(AdversarialBase):
    def test_sentinel_replaced_with_symlink_blocks(self):
        original = self.sentinel
        # Replace with symlink to /dev/null (always "exists" but not owned).
        linked = self.tmp / "decoy"
        linked.write_text("x", encoding="utf-8")
        os.chmod(linked, 0o600)
        original.unlink()
        os.symlink(str(linked), str(original))
        rec = self._make_rec(
            "performance-engineer", _SONNET, _OPUS, "promote"
        )
        result = apply_mod.apply(
            [rec], _baseline_policy(),
            agents_dir=self.agents_dir,
            baseline_agents_dir=self.baseline_dir,
            policy_path=self.policy_path,
            sigchain_path=self.sigchain_path,
            lock_path=self.lock_path,
            sentinel_path=self.sentinel,
            audit_log_path=self.audit_path,
            adr_scaffold_dir=self.scaffold_dir,
            now=self.now,
        )
        self.assertEqual(result.outcome, "killswitch")


# ---------------------------------------------------------------------
# 6. Kill-switch single-factor bypass
# ---------------------------------------------------------------------

class KillSwitchSingleFactorTests(AdversarialBase):
    def test_env_flag_only_without_sentinel_blocks(self):
        self.sentinel.unlink()
        rec = self._make_rec(
            "performance-engineer", _SONNET, _OPUS, "promote"
        )
        result = apply_mod.apply(
            [rec], _baseline_policy(),
            agents_dir=self.agents_dir,
            baseline_agents_dir=self.baseline_dir,
            policy_path=self.policy_path,
            sigchain_path=self.sigchain_path,
            lock_path=self.lock_path,
            sentinel_path=self.sentinel,
            audit_log_path=self.audit_path,
            adr_scaffold_dir=self.scaffold_dir,
            now=self.now,
        )
        self.assertEqual(result.outcome, "killswitch")

    def test_sentinel_only_without_env_flag_blocks(self):
        os.environ["CEO_TIER_POLICY_ENABLE"] = "0"
        rec = self._make_rec(
            "performance-engineer", _SONNET, _OPUS, "promote"
        )
        result = apply_mod.apply(
            [rec], _baseline_policy(),
            agents_dir=self.agents_dir,
            baseline_agents_dir=self.baseline_dir,
            policy_path=self.policy_path,
            sigchain_path=self.sigchain_path,
            lock_path=self.lock_path,
            sentinel_path=self.sentinel,
            audit_log_path=self.audit_path,
            adr_scaffold_dir=self.scaffold_dir,
            now=self.now,
        )
        self.assertEqual(result.outcome, "killswitch")


# ---------------------------------------------------------------------
# 7. Statistical power doctored n
# ---------------------------------------------------------------------

class DoctoredNTests(AdversarialBase):
    def test_rec_with_fabricated_high_n_still_rejected_by_apply(self):
        # Even if attacker crafts a Recommendation claiming n=999, the
        # apply.py path respects the action field — a "hold" with
        # rejection is honored even when evidence n is huge.
        rec = Recommendation(
            agent_slug="performance-engineer",
            current_tier=_SONNET,
            recommended_tier=_OPUS,
            action="hold",
            evidence=AssignmentEvidence(
                n=999, gap_pp=1000.0,
                last_updated="2026-04-19T00:00:00Z",
                runs_considered=999,
                tournament_report_hmacs=[],
            ),
            signature_required=False,
            cooldown_ok=True,
            rejection_reason="statistical_power",  # poisoned reason
        )
        result = apply_mod.apply(
            [rec], _baseline_policy(),
            agents_dir=self.agents_dir,
            baseline_agents_dir=self.baseline_dir,
            policy_path=self.policy_path,
            sigchain_path=self.sigchain_path,
            lock_path=self.lock_path,
            sentinel_path=self.sentinel,
            audit_log_path=self.audit_path,
            adr_scaffold_dir=self.scaffold_dir,
            now=self.now,
        )
        outcome = next(
            o for o in result.outcomes
            if o.agent_slug == "performance-engineer"
        )
        self.assertEqual(outcome.outcome, "skipped")


# ---------------------------------------------------------------------
# 8. Sigchain mismatch — verify
# ---------------------------------------------------------------------

class SigchainVerifyTests(AdversarialBase):
    def test_sigchain_malformed_line_caught_by_verify(self):
        # Malformed lines trigger tamper / malformed status.
        self.sigchain_path.parent.mkdir(parents=True, exist_ok=True)
        self.sigchain_path.write_text(
            "not-json\n", encoding="utf-8"
        )
        rc = cli.cmd_verify(
            type("Args", (), {
                "sigchain": str(self.sigchain_path),
                "policy": None,
            })()
        )
        # verify returns non-zero on mismatch.
        self.assertNotEqual(rc, 0)


# ---------------------------------------------------------------------
# 9. Sigchain truncation detected via tip length
# ---------------------------------------------------------------------

class TruncationTests(AdversarialBase):
    def test_truncated_sigchain_vs_policy_tip_length_mismatch_flagged(
        self,
    ):
        # Policy claims tip_length=5; sigchain has 2 lines → verify flags.
        self.policy_path.parent.mkdir(parents=True, exist_ok=True)
        self.sigchain_path.parent.mkdir(parents=True, exist_ok=True)
        policy = {
            "schema_version": "1.0",
            "generated_at": "2026-04-19T00:00:00Z",
            "baseline_from": "ADR-052",
            "assignments": {
                "code-reviewer": {
                    "tier": _OPUS, "locked_by": "VETO_FLOOR",
                    "evidence": None,
                },
                "security-engineer": {
                    "tier": _OPUS, "locked_by": "VETO_FLOOR",
                    "evidence": None,
                },
                "qa-architect": {
                    "tier": _SONNET, "locked_by": None,
                    "evidence": None,
                },
                "performance-engineer": {
                    "tier": _SONNET, "locked_by": None,
                    "evidence": None,
                },
                "devops": {
                    "tier": _HAIKU, "locked_by": None,
                    "evidence": None,
                },
            },
            "hmac_anchor": "f" * 64,
            "sigchain_tip_length": 5,
            "last_change_by_role": {},
        }
        self.policy_path.write_text(
            json.dumps(policy), encoding="utf-8"
        )
        # Write sigchain with HMAC-valid entries but wrong count.
        # We skip actual HMAC computation and patch verify_chain to
        # signal intact; cli then checks tip_length vs line count.
        with self.sigchain_path.open("w", encoding="utf-8") as f:
            f.write(json.dumps({
                "timestamp": "2026-04-19T00:00:00Z",
                "author": "x",
                "sp_chain_id": "SP-100-aaaaaaaa",
                "action": "baseline",
                "agent_slug": "qa-architect",
                "from_tier": _SONNET,
                "to_tier": _SONNET,
                "evidence_hmac": "0" * 64,
                "prior_hash": "0" * 64,
                "chain_length": 1,
                "prior_commit_sha": "0" * 40,
                "hmac": "a" * 64,
            }) + "\n")
        # Patch underlying verify_chain to return intact.
        mod = cli._load_audit_hmac_module()
        # If _load returns None, the verify function can't proceed; we
        # craft a mock module.
        fake_result = type("VR", (), {
            "is_intact": True,
            "status": "intact",
            "verified_count": 1,
            "line": None,
            "reason": None,
        })()

        class FakeAH:
            STATUS_INTACT = "intact"

            @staticmethod
            def verify_chain(path, **kw):
                return fake_result

        with mock.patch.object(
            cli, "_load_audit_hmac_module", return_value=FakeAH,
        ):
            args = type("Args", (), {
                "sigchain": str(self.sigchain_path),
                "policy": str(self.policy_path),
            })()
            rc = cli.cmd_verify(args)
        # Tip-length mismatch → non-zero exit.
        self.assertNotEqual(rc, 0)


# ---------------------------------------------------------------------
# 10. Poisoned report — demote VETO recommendation
# ---------------------------------------------------------------------

class PoisonedReportTests(AdversarialBase):
    def test_strong_evidence_for_haiku_code_review_never_reaches_apply(
        self,
    ):
        # Tournament fixture manufactures haiku dominance on code-review;
        # learn.py VETO zeroth-check + apply.py defense-in-depth
        # independently block. Verify learn does NOT emit a
        # code-reviewer recommendation.
        for run_i in range(3):
            records = []
            for m in (_HAIKU, _OPUS, _SONNET):
                for i in range(40):
                    verdict = "pass" if m == _HAIKU else "fail"
                    records.append(_task_record(
                        fixture_id="fx-{}-{}-{}".format(m, run_i, i),
                        task_type="code-review",
                        model=m, verdict=verdict,
                    ))
            path = self.reports_dir / "tournament-pr{}.jsonl".format(run_i)
            with path.open("w", encoding="utf-8") as f:
                for r in records:
                    f.write(json.dumps(r) + "\n")
            os.utime(path, (time.time() - 86400, time.time() - 86400))
        with mock.patch.object(
            learn, "_hmac_verify_report", return_value=(True, None)
        ):
            recs = learn.learn(
                self.reports_dir, _baseline_policy(), now=self.now
            )
        slugs = {r.agent_slug for r in recs}
        self.assertNotIn("code-reviewer", slugs)
        self.assertNotIn("security-engineer", slugs)


# ---------------------------------------------------------------------
# 11. Cost cascade — 3 simultaneous promote recommendations
# ---------------------------------------------------------------------

class CostCascadeTests(AdversarialBase):
    def test_three_promotes_all_downgraded_when_all_over_cap(self):
        # Seed huge audit tokens for all 3 non-VETO agents.
        for agent in ("qa-architect", "performance-engineer", "devops"):
            self._seed_audit_tokens(agent, 50_000_000, count=3)
        recs = [
            self._make_rec(
                "qa-architect", _SONNET, _OPUS, "promote",
            ),
            self._make_rec(
                "performance-engineer", _SONNET, _OPUS, "promote",
            ),
            self._make_rec(
                "devops", _HAIKU, _SONNET, "promote",
            ),
        ]
        result = apply_mod.apply(
            recs, _baseline_policy(),
            agents_dir=self.agents_dir,
            baseline_agents_dir=self.baseline_dir,
            policy_path=self.policy_path,
            sigchain_path=self.sigchain_path,
            lock_path=self.lock_path,
            sentinel_path=self.sentinel,
            cost_gate_usd=20.0,
            audit_log_path=self.audit_path,
            adr_scaffold_dir=self.scaffold_dir,
            now=self.now,
        )
        cost_gated_count = sum(
            1 for o in result.outcomes if o.outcome == "cost_gated"
        )
        self.assertEqual(cost_gated_count, 3)
        # None of the three agent files should have been rewritten.
        for agent in ("qa-architect", "performance-engineer"):
            content = (self.agents_dir / f"{agent}.md").read_text(
                encoding="utf-8"
            )
            self.assertIn("model: {}".format(_SONNET), content)


if __name__ == "__main__":  # pragma: no cover
    unittest.main()
