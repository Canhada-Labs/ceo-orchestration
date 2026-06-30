#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
test_trading_readonly.py — PLAN-083 Wave 2 sub-agent 2.7 tests.

Stdlib unittest covering all 5 R1-fortified §7 guardrails plus Wave 3
purple-team scenarios. Stdlib-only (Python 3.9+).

Test plan (≥25 tests total):

    Guardrail (a) — write override                                    8
    Guardrail (b) — secret scan output                                6
    Guardrail (c) — manual-review paths                               5
    Guardrail (d) — kill-switch FAIL-CLOSED + escape-hatch            6
    Guardrail (e) — 7-day banner                                      3
    Purple-team (Wave 3.3 foreshadowing)                              3
    Audit-emit field allowlist (Sec MF-3)                             2

    TOTAL                                                            33

Each test maps to PLAN-083 §7.N + R1 verdict ID in its docstring.
"""

from __future__ import annotations

import datetime as _dt
import importlib.util
import os
import sys
import tempfile
import textwrap
import unittest
from pathlib import Path
from typing import Dict, List, Optional
from unittest import mock


# ---------------------------------------------------------------------------
# Locate the staged module under test by path-based import.
# ---------------------------------------------------------------------------

_THIS_DIR = Path(__file__).resolve().parent
_STAGING_DIR = _THIS_DIR.parent
_MODULE_PATH = _STAGING_DIR / "trading-readonly-guardrails.py"


def _load_module():
    spec = importlib.util.spec_from_file_location(
        "trading_readonly_guardrails", str(_MODULE_PATH)
    )
    if spec is None or spec.loader is None:
        raise RuntimeError(f"cannot load {_MODULE_PATH}")
    mod = importlib.util.module_from_spec(spec)
    sys.modules["trading_readonly_guardrails"] = mod
    spec.loader.exec_module(mod)  # type: ignore[union-attr]
    return mod


GR = _load_module()


# ---------------------------------------------------------------------------
# Test fixtures
# ---------------------------------------------------------------------------


def _make_profile(
    risk_class: str = "trading-readonly",
    created_at: Optional[str] = None,
    manual_review_paths: Optional[List[str]] = None,
) -> str:
    if created_at is None:
        created_at = (_dt.datetime.now(tz=_dt.timezone.utc)
                      .replace(microsecond=0).isoformat().replace("+00:00", "Z"))
    body = textwrap.dedent(f"""\
        # .claude/repo-profile.yaml
        ---
        schema_version: "1"
        risk_class: "{risk_class}"
        detected_at: "{created_at}"
        confidence: "high"
        manual_override: false
        created_at: "{created_at}"
        signals: []
    """)
    if manual_review_paths is not None:
        body += "manual_review_paths:\n"
        for p in manual_review_paths:
            body += f'  - "{p}"\n'
    return body


def _make_secret_patterns_yaml() -> str:
    """Minimal but realistic secret-patterns subset for tests."""
    return textwrap.dedent("""\
        version: 1
        schema_version: 1
        catalog_version: "0.1.0"
        patterns:
          - id: binance-api-key-hex
            family: binance
            regex: '\\b[A-Fa-f0-9]{64}\\b'
            description: 'Binance API key (64 hex)'
            redaction_label: '[REDACTED:binance_key]'
            confidence: high
            fpr_target: 0.15
            context_hint: '(?i)binance|api[_-]?key'
            require_context: true
          - id: evm-private-key
            family: evm
            regex: '\\b0x[0-9a-fA-F]{64}\\b'
            description: 'EVM private key'
            redaction_label: '[REDACTED:evm_private_key]'
            confidence: high
            fpr_target: 0.10
            context_hint: ''
            require_context: false
          - id: generic-api-key-assignment
            family: generic
            regex: '(?i)(?:api[_-]?key|api[_-]?secret|passphrase)\\s*[:=]\\s*[''"]?([A-Za-z0-9+/=_-]{16,})[''"]?'
            description: 'Generic API key assignment'
            redaction_label: '[REDACTED:generic_api_credential]'
            confidence: medium
            fpr_target: 0.15
            context_hint: ''
            require_context: false
          - id: coinbase-passphrase
            family: coinbase
            regex: '(?i)(?:cb[_-]?access[_-]?passphrase|coinbase[_-]?passphrase)\\s*[:=]\\s*[''"]?([A-Za-z0-9_!@#$%^&*-]{8,64})[''"]?'
            description: 'Coinbase passphrase label-anchored'
            redaction_label: '[REDACTED:coinbase_passphrase]'
            confidence: high
            fpr_target: 0.05
            context_hint: ''
            require_context: false
    """)


class _Base(unittest.TestCase):
    """Test base providing isolated tmp profile + audit silencer."""

    def setUp(self) -> None:
        self.tmpdir = tempfile.TemporaryDirectory()
        self.addCleanup(self.tmpdir.cleanup)
        self.root = Path(self.tmpdir.name)
        (self.root / ".claude").mkdir()
        self.profile_path = self.root / ".claude" / "repo-profile.yaml"
        self.patterns_path = self.root / ".claude" / "secret-patterns-exchange.yaml"
        self.patterns_path.write_text(_make_secret_patterns_yaml(), encoding="utf-8")

        # Capture audit emit calls so we can assert on them.
        self.audit_calls: List[Dict[str, object]] = []

        def _fake_emit(action, **fields):
            self.audit_calls.append({"action": action, **fields})

        self._emit_patcher = mock.patch.object(GR, "_emit_audit", side_effect=_fake_emit)
        self._emit_patcher.start()
        self.addCleanup(self._emit_patcher.stop)

    def write_profile(self, **kwargs) -> None:
        self.profile_path.write_text(_make_profile(**kwargs), encoding="utf-8")

    def emitted_actions(self) -> List[str]:
        return [c["action"] for c in self.audit_calls]


# ===========================================================================
# Guardrail (a) — write override (PLAN-083 §7.2 R1 Sec P0-2)
# ===========================================================================


class TestWriteOverride(_Base):

    def test_bare_env_without_justification_rejected(self):
        """§7.2 — bare `=1` toggle without justification REJECTED."""
        self.write_profile()
        allowed, reason = GR.check_write_override(
            env={GR.ENV_WRITE_OVERRIDE: "1"},
            target_path="src/strategies/foo.py",
            justification=None,
        )
        self.assertFalse(allowed)
        self.assertEqual(reason, "justification_missing")
        self.assertIn("trading_write_override_used", self.emitted_actions())

    def test_justification_too_short_rejected(self):
        """§7.2 — justification <20 chars rejected."""
        allowed, reason = GR.check_write_override(
            env={GR.ENV_WRITE_OVERRIDE: "1"},
            target_path="src/strategies/foo.py",
            justification="too short",
        )
        self.assertFalse(allowed)
        self.assertEqual(reason, "justification_too_short")

    def test_valid_override_accepted_and_audit_emitted(self):
        """§7.2 — valid override accepted + audit emitted."""
        allowed, reason = GR.check_write_override(
            env={GR.ENV_WRITE_OVERRIDE: "1"},
            target_path="src/strategies/foo.py",
            justification="Owner-acked HOTFIX-2026-05-11 for arbitrage timing",
        )
        self.assertTrue(allowed)
        self.assertEqual(reason, "ok")
        self.assertEqual(self.emitted_actions().count("trading_write_override_used"), 1)
        # Verify audit row carries SHA-prefixed justification, not body.
        last = self.audit_calls[-1]
        self.assertIn("justification_sha256_prefix", last)
        self.assertNotIn("justification_text", last)

    def test_env_not_set_returns_denial(self):
        """§7.2 — when env var not set, denial returned (NOT an error)."""
        allowed, reason = GR.check_write_override(
            env={},
            target_path="src/strategies/foo.py",
            justification="x" * 30,
        )
        self.assertFalse(allowed)
        self.assertEqual(reason, "override_env_not_set")

    def test_glob_target_path_rejected(self):
        """§7.2 — target MUST be a single canonical path, not a glob."""
        allowed, reason = GR.check_write_override(
            env={GR.ENV_WRITE_OVERRIDE: "1"},
            target_path="src/strategies/*.py",
            justification="x" * 30,
        )
        self.assertFalse(allowed)
        self.assertEqual(reason, "target_path_is_glob")

    def test_path_traversal_blocked(self):
        """§7.2 — path-traversal guard rejects null/CR/LF bytes."""
        allowed, reason = GR.check_write_override(
            env={GR.ENV_WRITE_OVERRIDE: "1"},
            target_path="src/foo\x00bar.py",
            justification="x" * 30,
        )
        self.assertFalse(allowed)
        self.assertEqual(reason, "target_path_invalid")

    def test_oversized_justification_rejected(self):
        """§7.2 — defense-in-depth: oversized justification rejected."""
        allowed, reason = GR.check_write_override(
            env={GR.ENV_WRITE_OVERRIDE: "1"},
            target_path="src/strategies/foo.py",
            justification="x" * (GR.MAX_JUSTIFICATION_CHARS + 1),
        )
        self.assertFalse(allowed)
        self.assertEqual(reason, "justification_too_long")

    def test_override_is_per_invocation_not_session(self):
        """§7.2 — override env is per-invocation; reading env twice with
        different values yields different allows (no implicit caching)."""
        # First call WITH env → allowed.
        a1, r1 = GR.check_write_override(
            env={GR.ENV_WRITE_OVERRIDE: "1"},
            target_path="src/strategies/foo.py",
            justification="HOTFIX-2026-05-11 arbitrage timing window slip",
        )
        # Second call WITHOUT env → denied (no caching).
        a2, r2 = GR.check_write_override(
            env={},
            target_path="src/strategies/foo.py",
            justification="HOTFIX-2026-05-11 arbitrage timing window slip",
        )
        self.assertTrue(a1)
        self.assertFalse(a2)
        self.assertEqual(r2, "override_env_not_set")


# ===========================================================================
# Guardrail (b) — secret-scan output (PLAN-083 §7.3 Codex P0 broader scope)
# ===========================================================================


class TestSecretScan(_Base):

    def test_evm_private_key_detected(self):
        """§7.3 — EVM private key (0x + 64 hex) detected without context."""
        self.write_profile()
        text = "leak: 0x" + "a" * 64
        matches = GR.scan_output_for_secrets(
            text,
            profile_yaml_path=self.profile_path,
            secret_patterns_path=self.patterns_path,
        )
        families = {m.family for m in matches}
        self.assertIn("evm", families)

    def test_binance_key_requires_context(self):
        """§7.3 — 64-hex without 'binance' context does NOT match
        (context_hint anchoring); WITH context, matches."""
        self.write_profile()
        # Without context (just bare 64 hex).
        text_no_ctx = "release sha256: " + ("e3b0c442" * 8)  # 64 hex
        matches_no_ctx = GR.scan_output_for_secrets(
            text_no_ctx,
            profile_yaml_path=self.profile_path,
            secret_patterns_path=self.patterns_path,
        )
        bn_no = [m for m in matches_no_ctx if m.pattern_id == "binance-api-key-hex"]
        self.assertEqual(bn_no, [])
        # With context.
        text_ctx = "BINANCE_API_KEY=" + ("e3b0c442" * 8)
        matches_ctx = GR.scan_output_for_secrets(
            text_ctx,
            profile_yaml_path=self.profile_path,
            secret_patterns_path=self.patterns_path,
        )
        bn_ctx = [m for m in matches_ctx if m.pattern_id == "binance-api-key-hex"]
        self.assertTrue(len(bn_ctx) >= 1)

    def test_generic_api_key_assignment_detected(self):
        """§7.3 — label-anchored generic fallback detects assignment shape."""
        self.write_profile()
        text = 'config: api_key="abc123XYZsecretValue99"'
        matches = GR.scan_output_for_secrets(
            text,
            profile_yaml_path=self.profile_path,
            secret_patterns_path=self.patterns_path,
        )
        ids = {m.pattern_id for m in matches}
        self.assertIn("generic-api-key-assignment", ids)

    def test_match_record_never_contains_raw_text(self):
        """Sec MF-3 — Match.to_dict() yields ONLY sha-prefixed identifiers."""
        self.write_profile()
        text = "leak: 0x" + "f" * 64
        matches = GR.scan_output_for_secrets(
            text,
            profile_yaml_path=self.profile_path,
            secret_patterns_path=self.patterns_path,
        )
        self.assertTrue(matches)
        d = matches[0].to_dict()
        self.assertIn("match_sha256_prefix", d)
        self.assertIn("match_offset_bucket", d)
        self.assertNotIn("match_text", d)
        # No 64-hex string leaked into any field value.
        for v in d.values():
            if isinstance(v, str):
                # The sha256_prefix is 16 hex — accept that.
                self.assertNotEqual(len(v), 64, f"raw match text leaked: {v!r}")

    def test_scan_skips_when_profile_not_trading(self):
        """§7.3 — secret scan is trading-readonly-scoped: profile=engine
        returns empty (caller uses generic output_safety_flag path)."""
        self.write_profile(risk_class="engine")
        text = "leak: 0x" + "1" * 64
        matches = GR.scan_output_for_secrets(
            text,
            profile_yaml_path=self.profile_path,
            secret_patterns_path=self.patterns_path,
        )
        self.assertEqual(matches, [])

    def test_negative_fixture_low_fpr_on_commit_sha(self):
        """§7.3 AC5b — sha256-style commit hashes do NOT trip Binance
        regex (the hex is 40 chars, not 64 — so it must not match)."""
        self.write_profile()
        text = "commit a4f3c20be8d12f456789012345678901234567890"
        matches = GR.scan_output_for_secrets(
            text,
            profile_yaml_path=self.profile_path,
            secret_patterns_path=self.patterns_path,
        )
        # 40-hex commit SHA must NOT trip the 64-hex Binance pattern.
        bn = [m for m in matches if m.pattern_id == "binance-api-key-hex"]
        self.assertEqual(bn, [])


# ===========================================================================
# Guardrail (c) — manual-review paths (PLAN-083 §7.4 CR NTH ≥10 fixtures)
# ===========================================================================


class TestManualReviewPaths(_Base):

    def test_default_list_blocks_strategies(self):
        """§7.4 — strategies/** path matches default deny-list."""
        self.write_profile()
        self.assertTrue(GR.is_manual_review_path(
            "strategies/arbitrage.py", profile_yaml_path=self.profile_path
        ))

    def test_default_list_blocks_concurrency_glob(self):
        """§7.4 — **/concurrency.py blocks nested concurrency files."""
        self.write_profile()
        self.assertTrue(GR.is_manual_review_path(
            "src/bot/concurrency.py", profile_yaml_path=self.profile_path
        ))

    def test_default_list_blocks_env_files(self):
        """§7.4 — .env files in any dir blocked."""
        self.write_profile()
        self.assertTrue(GR.is_manual_review_path(
            "config/.env.production", profile_yaml_path=self.profile_path
        ))

    def test_normal_path_not_blocked(self):
        """§7.4 — README.md does NOT match deny-list."""
        self.write_profile()
        self.assertFalse(GR.is_manual_review_path(
            "README.md", profile_yaml_path=self.profile_path
        ))

    def test_ten_path_fixtures_all_blocked(self):
        """§7.4 CR NTH — verify ≥10 distinct path patterns are blocked."""
        self.write_profile()
        fixtures = [
            "strategies/arbitrage.py",
            "arbitrage/binance.py",
            "exchanges/coinbase.py",
            "bot/main.py",
            "trading/order_book.py",
            "src/strategies/foo.py",
            "src/exchanges/bar.py",
            "src/arbitrage/baz.py",
            "core/concurrency.py",
            "lib/latency.py",
            "math/precision.py",
            "engine/order_book.py",
            "feeds/market_data.py",
            ".env",
            ".env.local",
        ]
        for f in fixtures:
            self.assertTrue(
                GR.is_manual_review_path(f, profile_yaml_path=self.profile_path),
                msg=f"manual-review fixture failed for path: {f}",
            )
        self.assertGreaterEqual(len(fixtures), 10)


# ===========================================================================
# Guardrail (d) — kill-switch FAIL-CLOSED (PLAN-083 §7.5 Codex P0)
# ===========================================================================


class TestKillSwitch(_Base):

    def test_missing_profile_disables_trading(self):
        """§7.5 — missing repo-profile.yaml → DISABLED (fail-CLOSED)."""
        # Profile not written.
        self.assertTrue(GR.kill_switch_disabled(self.profile_path))
        # Audit row emitted with reason=profile_missing.
        reasons = [c.get("reason") for c in self.audit_calls
                   if c["action"] == "trading_kill_switch_invoked"]
        self.assertIn("profile_missing", reasons)

    def test_missing_profile_does_NOT_downgrade_to_generic(self):
        """§7.5 Codex P0 — deletion does NOT silently become generic mode."""
        # Profile not written.
        # kill_switch_disabled must return True.
        self.assertTrue(GR.kill_switch_disabled(self.profile_path))
        # is_manual_review_path still falls back to default deny-list
        # (NOT generic-mode no-op): verify a trading path still blocks.
        self.assertTrue(GR.is_manual_review_path(
            "strategies/arbitrage.py", profile_yaml_path=self.profile_path
        ))

    def test_generic_only_reachable_via_explicit_authoring(self):
        """§7.5 — `generic` mode reachable ONLY by explicit profile, not deletion."""
        self.write_profile(risk_class="generic")
        # kill_switch_disabled now returns False (profile present + valid).
        self.assertFalse(GR.kill_switch_disabled(self.profile_path))

    def test_unknown_needs_confirmation_disables(self):
        """§7.5 — risk_class=unknown-needs-owner-confirmation → DISABLED."""
        self.write_profile(risk_class="unknown-needs-owner-confirmation")
        self.assertTrue(GR.kill_switch_disabled(self.profile_path))

    def test_malformed_profile_fails_closed(self):
        """§7.5 — malformed YAML → DISABLED (fail-CLOSED on parse error)."""
        # Write garbage that the loose parser rejects.
        self.profile_path.write_text(
            "&anchor garbage\n!!tag !!nope\n",
            encoding="utf-8",
        )
        self.assertTrue(GR.kill_switch_disabled(self.profile_path))
        reasons = [c.get("reason") for c in self.audit_calls
                   if c["action"] == "trading_kill_switch_invoked"]
        self.assertTrue(any(r in {"profile_malformed", "profile_missing", "risk_class_missing"} for r in reasons))

    def test_escape_hatch_script_exists_and_invocable(self):
        """§7.5 — escape-hatch script lives in staging + is executable
        contract documented + idempotent + requires GPG sign."""
        script = _STAGING_DIR / "trading-readonly-escape-hatch.sh"
        self.assertTrue(script.is_file())
        body = script.read_text(encoding="utf-8")
        # Sentinel content checks (no exec; we only verify shape).
        self.assertIn("trading_kill_switch_disabled", body)
        self.assertIn("gpg", body)
        self.assertIn("escape-hatch-justification", body)
        # Required header sentinel.
        self.assertIn("# Trading kill-switch escape hatch", body)

    def test_escape_hatch_emits_real_audit_event_not_stub(self):
        """PLAN-136 W4 F3 — script issues a REAL emit, not the v1.19.0 stub.

        The pre-F3 body only printed `stub: would emit ...`; the audit row
        was never written so `trading_kill_switch_disabled` was forensically
        invisible. F3 wires `_lib.audit_emit.emit_generic` with the four
        Sec MF-3 allowlisted fields. Assert the stub line is GONE and the
        real emit (with each allowlisted field) is present.
        """
        script = _STAGING_DIR / "trading-readonly-escape-hatch.sh"
        body = script.read_text(encoding="utf-8")
        # The v1.19.0 placeholder must be gone.
        self.assertNotIn("stub: would emit", body)
        # A real emit through the framework emitter must be present.
        self.assertIn("emit_generic", body)
        self.assertIn('"trading_kill_switch_disabled"', body)
        # Each Sec MF-3 allowlisted field for this action must be wired
        # (matches _TRADING_KILL_SWITCH_DISABLED_ALLOWLIST in audit_emit.py).
        for field in (
            "justification_sha256_prefix",
            "signer_fingerprint_prefix",
            "signed_new",
            "justification_length",
        ):
            self.assertIn(field, body, msg=f"emit missing allowlisted field {field!r}")

    def test_escape_hatch_emit_is_fail_soft(self):
        """PLAN-136 W4 F3 — emit failure degrades gracefully (fail-soft).

        Per the framework rule (CLAUDE.md §5) infra hooks never crash the
        ceremony. The emit runs in a subshell with stderr swallowed and a
        defined `AUDIT_OK="failed"` branch + bounded exit code 4 — it must
        NOT `exit` from inside the emit block nor propagate the Python
        traceback as an unhandled crash.
        """
        script = _STAGING_DIR / "trading-readonly-escape-hatch.sh"
        body = script.read_text(encoding="utf-8")
        # The emit is guarded by an if/then that records a status string
        # rather than aborting; a "failed" branch exists.
        self.assertIn('AUDIT_OK="failed"', body)
        # The Python heredoc traps its own exceptions before re-signalling.
        self.assertIn("except Exception as exc", body)

    def test_escape_hatch_both_copies_identical(self):
        """PLAN-136 W4 F3 — the two on-disk copies are byte-identical.

        `.claude/scripts/trading-readonly-escape-hatch.sh` (under the
        skill tree) and `scripts/local/trading-readonly-escape-hatch.sh`
        (the install-into-target source) MUST not drift. F3 reconciled the
        stub copy to the real implementation; this guards the empty-diff
        invariant going forward.
        """
        repo_root = _THIS_DIR.parent.parent.parent
        a = _STAGING_DIR / "trading-readonly-escape-hatch.sh"
        b = repo_root / "scripts" / "local" / "trading-readonly-escape-hatch.sh"
        self.assertTrue(a.is_file(), msg=f"missing {a}")
        self.assertTrue(b.is_file(), msg=f"missing {b}")
        self.assertEqual(
            a.read_bytes(),
            b.read_bytes(),
            msg="the two escape-hatch copies diverged (must be byte-identical)",
        )


# ===========================================================================
# Guardrail (e) — 7-day banner (PLAN-083 §7.6)
# ===========================================================================


class TestSevenDayBanner(_Base):

    def test_banner_visible_within_7_days(self):
        """§7.6 — banner visible when created_at < 7 days ago."""
        self.write_profile()  # Default: created_at = now (UTC).
        self.assertTrue(GR.seven_day_banner_visible(self.profile_path))

    def test_banner_hidden_after_7_days(self):
        """§7.6 — banner hidden when created_at > 7 days old."""
        old = (
            _dt.datetime.now(tz=_dt.timezone.utc) - _dt.timedelta(days=10)
        ).replace(microsecond=0).isoformat().replace("+00:00", "Z")
        self.write_profile(created_at=old)
        self.assertFalse(GR.seven_day_banner_visible(self.profile_path))

    def test_banner_persists_even_with_override(self):
        """§7.6 Codex `019e1803` — banner appears even with override."""
        self.write_profile()
        # Override is set.
        env = {GR.ENV_WRITE_OVERRIDE: "1"}
        allowed, _ = GR.check_write_override(
            env=env,
            target_path="src/strategies/foo.py",
            justification="HOTFIX-2026-05-11 valid justification body long",
        )
        self.assertTrue(allowed)
        # Banner remains visible.
        self.assertTrue(GR.seven_day_banner_visible(self.profile_path))


# ===========================================================================
# Wave 3 purple-team scenarios (foreshadowing 3.3 smoke)
# ===========================================================================


class TestPurpleTeamScenarios(_Base):

    def test_malicious_edit_on_canonical_blocked(self):
        """Wave 3.3 — edit on `strategies/**` MUST be in deny-list."""
        self.write_profile()
        # The hook layer will consult both is_manual_review_path AND
        # check_write_override. Without override → manual-review trips
        # AND override returns deny → write blocked.
        is_review = GR.is_manual_review_path(
            "strategies/arbitrage.py", profile_yaml_path=self.profile_path
        )
        allowed, reason = GR.check_write_override(
            env={},  # No override set.
            target_path="strategies/arbitrage.py",
            justification=None,
        )
        self.assertTrue(is_review)
        self.assertFalse(allowed)

    def test_secret_leak_via_stdout_triggers_alert(self):
        """Wave 3.3 — secret leak via stdout MUST trigger scan finding."""
        self.write_profile()
        text = "log: BINANCE_API_KEY=" + ("ab" * 32)
        matches = GR.scan_output_for_secrets(
            text,
            profile_yaml_path=self.profile_path,
            secret_patterns_path=self.patterns_path,
        )
        self.assertTrue(len(matches) >= 1)
        # The Match record yields an audit-emit-shaped dict (Sec MF-3 safe).
        d = matches[0].to_dict()
        self.assertIn("redaction_label", d)

    def test_concurrency_tweak_edit_blocked(self):
        """Wave 3.3 — edit on `**/concurrency.py` MUST be in deny-list."""
        self.write_profile()
        self.assertTrue(GR.is_manual_review_path(
            "core/concurrency.py", profile_yaml_path=self.profile_path
        ))
        # And without override is rejected.
        allowed, reason = GR.check_write_override(
            env={},
            target_path="core/concurrency.py",
            justification=None,
        )
        self.assertFalse(allowed)


# ===========================================================================
# Sec MF-3 — audit-emit field allowlist
# ===========================================================================


class TestAuditEmitAllowlist(_Base):

    def test_override_audit_carries_only_sha_prefixed_fields(self):
        """Sec MF-3 — audit row carries SHA-prefixes, NOT raw text bodies."""
        self.write_profile()
        GR.check_write_override(
            env={GR.ENV_WRITE_OVERRIDE: "1"},
            target_path="src/strategies/foo.py",
            justification="MUST contain enough chars to be valid override",
        )
        rows = [c for c in self.audit_calls
                if c["action"] == "trading_write_override_used"]
        self.assertTrue(rows)
        row = rows[-1]
        forbidden_keys = {
            "target_path",
            "justification",
            "justification_text",
            "raw_text",
            "raw_body",
            "secret_text",
        }
        for k in forbidden_keys:
            self.assertNotIn(k, row, msg=f"forbidden key {k!r} leaked into audit row")

    def test_kill_switch_audit_only_carries_reason_enum(self):
        """Sec MF-3 — kill-switch audit row carries closed-enum reason only."""
        # Trigger kill-switch (no profile).
        GR.kill_switch_disabled(self.profile_path)
        rows = [c for c in self.audit_calls
                if c["action"] == "trading_kill_switch_invoked"]
        self.assertTrue(rows)
        row = rows[-1]
        allowed_keys = {
            "action", "reason", "profile_path_sha256_prefix",
        }
        leaked = set(row.keys()) - allowed_keys
        self.assertEqual(
            leaked, set(),
            msg=f"kill_switch_invoked audit row contains forbidden keys: {leaked}",
        )


# ---------------------------------------------------------------------------
# CLI run
# ---------------------------------------------------------------------------


if __name__ == "__main__":
    unittest.main(verbosity=2)
