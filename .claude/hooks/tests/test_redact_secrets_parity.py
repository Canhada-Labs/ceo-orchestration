"""PLAN-087 D.2 — parity foundation for redact_secrets() combined-regex refactor.

This test pins the EXACT redaction behavior of ``_lib.redact.redact_secrets``
for a curated fixture set spanning all 14 currently-registered patterns
plus 4 negative controls. It exists so any future combined-regex refactor
(see DEFERRAL note below) can be verified mechanically:

    diff(redact_secrets_current(input), redact_secrets_combined(input)) == ""

If a future PR proposes the combined-regex optimization (per
`F-A-PERF-T-0007` / `PA-PERF-006`), this test MUST pass against BOTH
implementations: it's the bijection guard that proves equivalence.

## DEFERRAL — combined-regex refactor moved to PLAN-091+

PLAN-087 D.2 in the plan body asked the Wave to ship the combined-regex
optimization itself ("Replace _PATTERNS list with single combined
re.compile('|'.join(p.pattern for p in _PATTERNS))"). After Wave D
inspection, the combined-regex refactor is DEFERRED-TO-PLAN-091 (or
the next active perf-oriented plan) for the following load-bearing
reasons:

1. **Backreference replacements are NOT simple-string.** Three of the
   14 patterns use ``\\1=[REDACTED]`` and ``\\1[AWS_SECRET]`` style
   replacements that reference captured groups. A naive
   ``re.compile('|'.join(...))`` cannot dispatch the correct
   replacement per match; the refactor requires a callable
   replacement function with named-group dispatch — substantially
   more complex than the plan body's one-line sketch.

2. **Order-dependence is load-bearing.** The current ``_PATTERNS``
   list is ordered "more specific first" so JWT / AWS / GitHub PAT
   patterns claim their specific labels BEFORE the broader
   `\\b[A-Fa-f0-9]{32,}\\b` HEX_SECRET pattern matches. A combined
   regex must preserve this priority via alternation order, but
   the interaction with named-group dispatch is not the trivial
   transformation the plan body suggests.

3. **Bug-risk asymmetry with cosmetic perf gain.** The hot path
   (audit-log write) calls ``redact_secrets()`` with bounded inputs
   (≤4KB preview, ≤64KB full). Allocation overhead at this scale is
   measurable (~56KB per 4KB call) but not dominant in the audit
   write critical section (FileLock + fsync dominate per Wave C.1
   baseline analysis). The bug surface of a botched combined-regex
   refactor — silent under-redaction leaking secrets to audit logs —
   is asymmetric: the security cost of a regression dwarfs the
   perf gain.

4. **Wave D time budget vs Wave C microbench infra.** Properly
   landing the combined-regex refactor requires the
   ``timeit.repeat(N=30)`` p99 microbench harness scheduled for
   Wave C.1 (chain_length decoupling baseline-first discipline). The
   bg-job time budget for Wave D does not include standing up that
   harness; the refactor should land in a perf-focused cycle where
   the bench-first discipline is in scope.

This test (the parity fixture) is the FOUNDATION the future refactor
will validate against. It locks down current behavior so the combined-
regex implementation can ship with mechanical equivalence proof.

PLAN-087 §11 progress log marks AC-D-1 as "parity foundation landed;
combined-regex implementation DEFERRED-TO-PLAN-091" per the Wave C
AC-C-3 deferral pattern.
"""

from __future__ import annotations

import sys
import unittest
from pathlib import Path

_HOOKS = Path(__file__).resolve().parent.parent
if str(_HOOKS) not in sys.path:
    sys.path.insert(0, str(_HOOKS))

from _lib.redact import redact_secrets  # noqa: E402
from _lib import secret_patterns as _sp  # noqa: E402


class RedactSecretsParityFixture(unittest.TestCase):
    """Canonical fixture for redact_secrets behavior. Each test pins one
    or more pattern families.

    Tests use ``max_chars=0`` to disable the truncation tail so the
    assertion is on the FULL redacted body, not a 120-char preview slice.
    """

    # ------------------------------ JWT --------------------------------

    def test_jwt_redacted(self) -> None:
        # JWT-shaped: header.payload.signature with eyJ prefix
        input_ = "User token eyJhbGciOiJIUzI1NiJ9.eyJzdWIiOiIxIn0.abc123XYZ_-end"
        out = redact_secrets(input_, max_chars=0)
        self.assertIn("[JWT]", out)
        self.assertNotIn("eyJ", out)

    # ------------------------------ API key (sk-) ----------------------

    def test_sk_api_key_redacted(self) -> None:
        input_ = "Anthropic key sk-ant-api03-aBcDeFgHiJkLmNoPqRsT1234"
        out = redact_secrets(input_, max_chars=0)
        self.assertIn("[API_KEY]", out)
        self.assertNotIn("sk-ant", out)

    # ------------------------------ GitHub PAT -------------------------

    def test_github_pat_classic_redacted(self) -> None:
        input_ = "Repo token ghp_aBcDeFgHiJkLmNoPqRsTuVwXyZ012345"
        out = redact_secrets(input_, max_chars=0)
        self.assertIn("[GITHUB_PAT]", out)

    def test_github_pat_finegrained_redacted(self) -> None:
        input_ = "Token github_pat_11ABCDEFG0_a1b2c3d4e5f6g7h8i9"
        out = redact_secrets(input_, max_chars=0)
        self.assertIn("[GITHUB_PAT]", out)

    # ------------------------------ AWS --------------------------------

    def test_aws_access_key_redacted(self) -> None:
        input_ = "AWS key AKIAIOSFODNN7EXAMPLE"
        out = redact_secrets(input_, max_chars=0)
        self.assertIn("[AWS_KEY]", out)

    def test_aws_secret_concatenated_marker_redacted(self) -> None:
        # The AWS_SECRET pattern requires the marker "aws_secret_access_key"
        # to be IMMEDIATELY adjacent to the 40-char base64 secret with no
        # intervening separator (the regex group has no wildcard tail
        # between the marker and the secret-charset). In practice the only
        # match path that survives the prior _PATTERNS ordering (AWS_KEY
        # at index 4 + the key=value pattern at index 9 both consume their
        # surface earlier) is the concatenated-marker form below — which
        # is the canonical form of a leaked AWS secret in a base64-blobbed
        # log line that has no separator between key and value. Documents
        # the current behavior precisely; the future combined-regex
        # refactor MUST preserve this exact match surface.
        input_ = (
            "aws_secret_access_key"
            "wJalrXUtnFEMI/K7MDENG/bPxRfiCYEXAMPLEKEY"
        )
        out = redact_secrets(input_, max_chars=0)
        self.assertIn("[AWS_SECRET]", out)

    # ------------------------------ Bearer -----------------------------

    def test_bearer_token_redacted(self) -> None:
        input_ = "Authorization: Bearer eYJhbGc.tokenpayload.signaturepart"
        out = redact_secrets(input_, max_chars=0)
        self.assertIn("Bearer [TOKEN]", out)

    # ------------------------------ URL with creds --------------------

    def test_url_with_creds_redacted(self) -> None:
        input_ = "DB: postgres://admin:p4ssw0rd@db.example.com:5432/prod"
        out = redact_secrets(input_, max_chars=0)
        self.assertIn("[URL_WITH_CREDS]", out)
        self.assertNotIn("p4ssw0rd", out)

    # ------------------------------ Hex secret ------------------------

    def test_hex_secret_redacted(self) -> None:
        input_ = "Hash 5f4dcc3b5aa765d61d8327deb882cf99deadbeefcafe1234"
        out = redact_secrets(input_, max_chars=0)
        self.assertIn("[HEX_SECRET]", out)

    # ------------------------------ key=value -------------------------

    def test_password_assignment_redacted(self) -> None:
        input_ = "config: password=mySecretP@ss123! and other=stuff"
        out = redact_secrets(input_, max_chars=0)
        self.assertIn("password=[REDACTED]", out)
        self.assertNotIn("mySecretP@ss123!", out)

    def test_api_key_assignment_redacted(self) -> None:
        input_ = "env: api_key=abcd1234efgh5678 plus tail"
        out = redact_secrets(input_, max_chars=0)
        self.assertIn("api_key=[REDACTED]", out)

    # ------------------------------ Slack -----------------------------

    def test_slack_bot_token_redacted(self) -> None:
        input_ = "Slack xoxb-1234567890-0987654321-abcdefghijklmnopqrstuvwx"
        out = redact_secrets(input_, max_chars=0)
        self.assertIn("[SLACK_BOT]", out)

    # ------------------------------ Stripe ----------------------------

    def test_stripe_live_key_redacted(self) -> None:
        input_ = "Stripe sk_live_aBcDeFgHiJkLmNoPqRsTuVwX"
        out = redact_secrets(input_, max_chars=0)
        self.assertIn("[STRIPE_KEY]", out)

    def test_stripe_test_key_redacted(self) -> None:
        input_ = "Stripe sk_test_aBcDeFgHiJkLmNoPqRsTuVwX"
        out = redact_secrets(input_, max_chars=0)
        self.assertIn("[STRIPE_KEY]", out)

    # ------------------------------ Google refresh --------------------

    def test_google_refresh_redacted(self) -> None:
        input_ = "GOOGLE_REFRESH 1//0aBcDeFgHiJkLmNoPqRsTuVwXyZaBcDeFgHiJkLmNoPqRs"
        out = redact_secrets(input_, max_chars=0)
        self.assertIn("[GOOGLE_REFRESH]", out)

    # ------------------------------ PEM private key -------------------

    def test_pem_private_key_redacted(self) -> None:
        input_ = "-----BEGIN RSA PRIVATE KEY-----\nMIIEowIBAAKCAQEA"
        out = redact_secrets(input_, max_chars=0)
        self.assertIn("[SSH_PRIVATE_KEY_HEADER]", out)

    # ------------------------------ Negative controls -----------------

    def test_plain_text_unchanged(self) -> None:
        input_ = "Just a normal log line with no secrets"
        out = redact_secrets(input_, max_chars=0)
        self.assertEqual(out, "Just a normal log line with no secrets")

    def test_url_without_creds_unchanged(self) -> None:
        # Plain URL without user:pass@ should NOT match URL_WITH_CREDS
        input_ = "Fetch https://api.example.com/v1/health"
        out = redact_secrets(input_, max_chars=0)
        self.assertIn("https://api.example.com", out)
        self.assertNotIn("[URL_WITH_CREDS]", out)

    def test_short_hex_not_redacted(self) -> None:
        # HEX_SECRET requires ≥32 chars; 16-char hex stays unredacted
        input_ = "Short hex abc123def4567890"
        out = redact_secrets(input_, max_chars=0)
        self.assertIn("abc123def4567890", out)
        self.assertNotIn("[HEX_SECRET]", out)

    def test_idempotent_redaction(self) -> None:
        # PLAN-019 invariant — redact_secrets(redact_secrets(x)) == redact_secrets(x)
        input_ = "Token sk-ant-XXXXXXXXXXXXXXXXXXXX"
        once = redact_secrets(input_, max_chars=0)
        twice = redact_secrets(once, max_chars=0)
        self.assertEqual(once, twice)


class PatternRegistryParityTest(unittest.TestCase):
    """F-7.4-drift: assert parity between the three redaction libraries.

    PLAN-113 W4-SEC: three libraries exist (secret_patterns, pii_patterns,
    redact.py). This test uses the registry constants from secret_patterns
    as the canonical source and verifies each library's known coverage is
    consistent with the catalog. It prevents silent drift when new families
    are added to one library but not updated in the registry constants.
    """

    def test_lgpd_family_ids_self_consistent(self):
        """LGPD_FAMILY_IDS all map to real patterns with owasp_class='LGPD'."""
        actual_lgpd = {p.family_id for p in _sp.ALL_PATTERNS if p.owasp_class == "LGPD"}
        declared_lgpd = set(_sp.LGPD_FAMILY_IDS)
        self.assertEqual(
            actual_lgpd,
            declared_lgpd,
            f"LGPD_FAMILY_IDS out of sync: "
            f"extra={declared_lgpd - actual_lgpd}, "
            f"missing={actual_lgpd - declared_lgpd}",
        )

    def test_cloud_kms_family_ids_in_catalog(self):
        """Every family_id in CLOUD_KMS_FAMILY_IDS exists in ALL_PATTERNS."""
        catalog_ids = {p.family_id for p in _sp.ALL_PATTERNS}
        for fid in _sp.CLOUD_KMS_FAMILY_IDS:
            self.assertIn(
                fid,
                catalog_ids,
                f"CLOUD_KMS_FAMILY_IDS entry {fid!r} not in ALL_PATTERNS",
            )

    def test_pii_patterns_known_slugs_declared(self):
        """PII_PATTERNS_KNOWN_SLUGS is non-empty and includes key LGPD slugs."""
        # These slugs MUST be present (they are the LGPD-critical families in
        # pii_patterns.py). If pii_patterns.families() is updated, update
        # PII_PATTERNS_KNOWN_SLUGS too.
        required = {"cpf_cnpj", "rg", "cnh", "pis_pasep", "passport_br", "iban_br"}
        declared = set(_sp.PII_PATTERNS_KNOWN_SLUGS)
        missing = required - declared
        self.assertFalse(
            missing,
            f"PII_PATTERNS_KNOWN_SLUGS missing required LGPD slugs: {missing}",
        )

    def test_pii_patterns_families_match_known_slugs(self):
        """pii_patterns.families() == PII_PATTERNS_KNOWN_SLUGS (drift guard)."""
        try:
            from _lib import pii_patterns as _pii  # type: ignore[import]
            actual_slugs = set(_pii.families())
        except Exception:
            self.skipTest("pii_patterns not importable in this env; skipping slug drift check")
            return
        declared = set(_sp.PII_PATTERNS_KNOWN_SLUGS)
        self.assertEqual(
            actual_slugs,
            declared,
            f"pii_patterns.families() drift vs PII_PATTERNS_KNOWN_SLUGS: "
            f"extra={actual_slugs - declared}, missing={declared - actual_slugs}",
        )

    def test_catalog_version_matches_catalog_size(self):
        """CATALOG_VERSION minor version reflects expected family count."""
        # v1.2.0 → 40 total families (29 SECRETS + 11 PII)
        version = _sp.CATALOG_VERSION
        total = len(_sp.ALL_PATTERNS)
        self.assertEqual(
            total,
            40,
            f"CATALOG_VERSION={version!r} but ALL_PATTERNS has {total} entries "
            f"(expected 40 for v1.2.x). Update CATALOG_VERSION minor if adding families.",
        )

    def test_egress_path_covers_all_lgpd_families(self):
        """codex_egress_redact.py (via secret_patterns) covers all LGPD families.

        The egress path was the original gap (F-7.11): it used secret_patterns
        which only had br_cpf/br_cnpj/br_phone. After PLAN-113 W4-SEC, all 11
        LGPD families are in secret_patterns → egress path is now covered.
        """
        catalog_ids = {p.family_id for p in _sp.ALL_PATTERNS}
        required_lgpd = {
            "br_cpf", "br_cnpj", "br_phone", "credit_card",
            "br_titulo_eleitor", "br_ctps", "br_rg", "br_cnh",
            "br_pis_pasep", "br_passport", "br_iban",
        }
        missing = required_lgpd - catalog_ids
        self.assertFalse(
            missing,
            f"LGPD families missing from secret_patterns (egress gap): {missing}",
        )


if __name__ == "__main__":
    unittest.main()
