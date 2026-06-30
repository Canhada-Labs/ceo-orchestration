"""Unit tests for _lib.pii_patterns (Sprint 11 Phase 9 / ADR-036).

Behavior assertions (consensus S5):
- Each family detected on positive sample
- Each family NOT detected on control sample
- Shannon entropy correctness
- NFKC normalization strips full-width to ascii
- Zero-width / bidi strip
- Base64 decode one level only (depth cap respected)
- Luhn validator
- CPF/CNPJ context-gated (raw digits without keyword do NOT match)

All scan calls run the 5-step pipeline in order:
    NFKC → strip invisibles → b64 decode (depth 1) → entropy → regex

Stdlib only. TestEnvContext for env isolation.
"""

from __future__ import annotations

import base64
import math
import os
import sys
import unittest
from pathlib import Path

_HOOKS_DIR = Path(__file__).resolve().parent.parent

from _lib import pii_patterns as pp  # noqa: E402
from _lib.testing import TestEnvContext  # noqa: E402

_FIXTURE_DIR = Path(__file__).resolve().parent / "fixtures" / "output_safety"


# ---------------------------------------------------------------------------
# Entropy + helper unit tests
# ---------------------------------------------------------------------------


class TestShannonEntropy(unittest.TestCase):
    def test_empty_string(self):
        self.assertEqual(pp.shannon_entropy(""), 0.0)

    def test_uniform_distribution(self):
        # 4 unique chars, equal frequency → entropy = log2(4) = 2.0
        self.assertAlmostEqual(pp.shannon_entropy("abcd"), 2.0, places=5)

    def test_skewed_distribution_low_entropy(self):
        # Mostly one char — entropy should be well below uniform
        h = pp.shannon_entropy("aaaaaaaab")
        self.assertLess(h, 0.6)

    def test_hex_string_entropy_bounded(self):
        # Random-looking hex maxes at log2(16) = 4.0
        h = pp.shannon_entropy("a3b8c1d6e9f20471c2e3fa9b1c8d7e6f")
        self.assertLess(h, 4.05)

    def test_high_entropy_long_b64(self):
        # Long base64-ish token should exceed threshold
        token = "sk-abcDEF1234567890xyzABCDEFGHIJKL"
        self.assertGreater(pp.shannon_entropy(token), 4.5)


class TestLuhnValidator(unittest.TestCase):
    def test_known_valid_visa(self):
        self.assertTrue(pp.luhn_valid("4532015112830366"))

    def test_known_invalid_visa(self):
        self.assertFalse(pp.luhn_valid("4532015112830367"))

    def test_with_dashes_and_spaces(self):
        self.assertTrue(pp.luhn_valid("4532-0151-1283-0366"))
        self.assertTrue(pp.luhn_valid("4532 0151 1283 0366"))

    def test_too_short_returns_false(self):
        self.assertFalse(pp.luhn_valid("12345"))

    def test_too_long_returns_false(self):
        self.assertFalse(pp.luhn_valid("1" * 25))


# ---------------------------------------------------------------------------
# Step 1 NFKC — full-width / compatibility attack
# ---------------------------------------------------------------------------


class TestNfkcNormalization(unittest.TestCase):
    def test_full_width_sk_dash_collapses(self):
        # Full-width "sk-" -> ascii "sk-" via NFKC
        attack = "\uff53\uff4b\uff0d" + "abcDEF1234567890xyzABCDEFGHIJKL"
        self.assertNotIn("sk-", attack)  # pre-normalization: no ascii match
        result = pp.scan(attack)
        # The pipeline MUST normalize before regex
        self.assertTrue(result.matched)
        self.assertIn("api_key", result.family_counts)

    def test_nfkc_step_counts_recorded(self):
        attack = "\uff53\uff4b\uff0d" + "abcDEF1234567890xyzABCDEFGHIJKL"
        result = pp.scan(attack)
        self.assertGreater(result.pipeline_step_counts["nfkc_changed_chars"], 0)


# ---------------------------------------------------------------------------
# Step 2 invisibles + bidi strip
# ---------------------------------------------------------------------------


class TestStripInvisibles(unittest.TestCase):
    def test_zero_width_space_stripped(self):
        # ZWSP between 's' and 'k-' defeats a literal regex
        attack = "s\u200bk-abcDEF1234567890xyzABCDEFGHIJKL"
        result = pp.scan(attack)
        self.assertTrue(result.matched)
        self.assertIn("api_key", result.family_counts)
        self.assertGreaterEqual(
            result.pipeline_step_counts["invisibles_stripped"], 1
        )

    def test_bidi_override_stripped(self):
        # U+202E RIGHT-TO-LEFT OVERRIDE between chars
        attack = "s\u202ek-abcDEF1234567890xyzABCDEFGHIJKL"
        result = pp.scan(attack)
        self.assertTrue(result.matched)
        self.assertGreaterEqual(
            result.pipeline_step_counts["invisibles_stripped"], 1
        )

    def test_newline_tab_preserved(self):
        # Step 2 must NOT strip \n/\t (regex line anchors need them)
        text = "clean line one\nclean line two\twith tab"
        result = pp.scan(text)
        self.assertEqual(result.pipeline_step_counts["invisibles_stripped"], 0)


# ---------------------------------------------------------------------------
# Step 3 bounded base64 decode depth=1
# ---------------------------------------------------------------------------


class TestBase64Decode(unittest.TestCase):
    def test_one_level_decode_catches_secret(self):
        secret = "sk-abcDEF1234567890xyzABCDEFGHIJKL"
        encoded = base64.b64encode(secret.encode()).decode()
        wrapper = f"Config: {encoded}"
        result = pp.scan(wrapper)
        self.assertTrue(result.matched)
        self.assertGreaterEqual(
            result.pipeline_step_counts["b64_tokens_decoded"], 1
        )

    def test_depth_cap_no_double_decode(self):
        # Double-b64 the secret; scanner decodes ONE level only.
        # After 1 decode we have a base64 string (still not the secret).
        # So if the decoded layer happens to not match any pattern, that's
        # fine — the point is we do NOT recurse.
        secret = "sk-abcDEF1234567890xyzABCDEFGHIJKL"
        once = base64.b64encode(secret.encode()).decode()
        twice = base64.b64encode(once.encode()).decode()
        result = pp.scan(f"wrap {twice}")
        # decoded_count <= 1 (only one token decoded once)
        self.assertLessEqual(result.pipeline_step_counts["b64_tokens_decoded"], 1)

    def test_non_base64_not_decoded(self):
        # Regular prose won't meet the b64 gate (low entropy, bad alphabet)
        text = "The quick brown fox jumps over the lazy dog many times repeat"
        result = pp.scan(text)
        self.assertEqual(result.pipeline_step_counts["b64_tokens_decoded"], 0)

    def test_urlsafe_b64_decode(self):
        secret = "sk-abcDEF1234567890xyzABCDEFGHIJKL"
        encoded = base64.urlsafe_b64encode(secret.encode()).decode().rstrip("=")
        wrapper = f"token {encoded}"
        result = pp.scan(wrapper)
        self.assertTrue(result.matched)


# ---------------------------------------------------------------------------
# Step 4 entropy flagging
# ---------------------------------------------------------------------------


class TestEntropyStep(unittest.TestCase):
    def test_high_entropy_long_token_flagged(self):
        # 40-char high-entropy token that doesn't match any other family
        token = "A1b2C3d4E5f6G7h8I9j0K1L2M3N4O5P6Q7R8S9T0"
        result = pp.scan(token)
        self.assertGreaterEqual(
            result.pipeline_step_counts["entropy_tokens_flagged"], 1
        )

    def test_english_prose_not_flagged_by_entropy(self):
        # A whole paragraph of English — too low entropy per token
        text = "This is a normal sentence that describes the weather"
        result = pp.scan(text)
        self.assertEqual(
            result.pipeline_step_counts["entropy_tokens_flagged"], 0
        )


# ---------------------------------------------------------------------------
# Step 5 regex family detection (positive + control)
# ---------------------------------------------------------------------------


class TestFamilyDetectionPositive(unittest.TestCase):
    """Each positive fixture must match at least one expected family."""

    def _load(self, name: str) -> str:
        return (_FIXTURE_DIR / "positive" / name).read_text(encoding="utf-8")

    def test_01_api_key_anthropic(self):
        r = pp.scan(self._load("01_api_key_anthropic.txt"))
        self.assertIn("api_key", r.family_counts)

    def test_02_api_key_github_pat_classic(self):
        r = pp.scan(self._load("02_api_key_github_pat_classic.txt"))
        self.assertIn("api_key", r.family_counts)

    def test_03_api_key_github_fine_grained(self):
        r = pp.scan(self._load("03_api_key_github_fine_grained.txt"))
        self.assertIn("api_key", r.family_counts)

    def test_04_api_key_aws_access(self):
        r = pp.scan(self._load("04_api_key_aws_access_key.txt"))
        self.assertIn("api_key", r.family_counts)

    def test_05_api_key_aws_secret_assignment(self):
        r = pp.scan(self._load("05_api_key_aws_secret_assignment.txt"))
        self.assertIn("api_key", r.family_counts)

    def test_06_jwt(self):
        r = pp.scan(self._load("06_jwt.txt"))
        self.assertIn("jwt", r.family_counts)

    def test_07_bearer(self):
        r = pp.scan(self._load("07_bearer.txt"))
        self.assertIn("bearer", r.family_counts)

    def test_08_cpf_with_context(self):
        r = pp.scan(self._load("08_cpf_with_context.txt"))
        self.assertIn("cpf_cnpj", r.family_counts)

    def test_09_cnpj_with_context(self):
        r = pp.scan(self._load("09_cnpj_with_context.txt"))
        self.assertIn("cpf_cnpj", r.family_counts)

    def test_10_credit_card_luhn(self):
        r = pp.scan(self._load("10_credit_card_luhn_valid.txt"))
        self.assertIn("credit_card_pan", r.family_counts)

    def test_11_email_in_login_context(self):
        r = pp.scan(self._load("11_email_in_login_context.txt"))
        self.assertIn("email_in_log", r.family_counts)

    def test_12_nfkc_full_width(self):
        r = pp.scan(self._load("12_nfkc_full_width.txt"))
        self.assertIn("api_key", r.family_counts)

    def test_13_zero_width_evasion(self):
        r = pp.scan(self._load("13_zero_width_evasion.txt"))
        self.assertIn("api_key", r.family_counts)

    def test_14_bidi_evasion(self):
        r = pp.scan(self._load("14_bidi_evasion.txt"))
        self.assertIn("api_key", r.family_counts)

    def test_15_base64_encoded_secret(self):
        r = pp.scan(self._load("15_base64_encoded_secret.txt"))
        # Either the decoded layer matches api_key, or entropy family fires
        self.assertTrue(
            "api_key" in r.family_counts or "entropy" in r.family_counts
        )


class TestFamilyDetectionControl(unittest.TestCase):
    """Every control fixture must be CLEAN — no match, zero false-positives."""

    def _load(self, name: str) -> str:
        return (_FIXTURE_DIR / "control" / name).read_text(encoding="utf-8")

    def test_01_random_hash_log(self):
        r = pp.scan(self._load("01_random_hash_log.txt"))
        self.assertFalse(
            r.matched,
            f"Control fixture matched unexpectedly: families={r.family_counts}",
        )

    def test_02_docs_email_no_address(self):
        r = pp.scan(self._load("02_docs_mention_email_no_address.txt"))
        self.assertFalse(r.matched)

    def test_03_partial_jwt_two_segments(self):
        r = pp.scan(self._load("03_partial_jwt_two_segments.txt"))
        # two segments is NOT a JWT → jwt family must not fire
        self.assertNotIn("jwt", r.family_counts)

    def test_04_random_digits_no_cpf_context(self):
        r = pp.scan(self._load("04_random_11_digits_no_cpf_context.txt"))
        self.assertNotIn("cpf_cnpj", r.family_counts)

    def test_05_credit_card_invalid_luhn(self):
        r = pp.scan(self._load("05_credit_card_shape_invalid_luhn.txt"))
        self.assertNotIn("credit_card_pan", r.family_counts)


# ---------------------------------------------------------------------------
# CPF/CNPJ context-gating edge cases
# ---------------------------------------------------------------------------


class TestCpfCnpjContextGating(unittest.TestCase):
    def test_raw_cpf_no_context_not_flagged(self):
        # 11 digits, shaped like a CPF, but no keyword within 40 chars
        text = "Sequence 12345678901 appeared in the stream."
        r = pp.scan(text)
        self.assertNotIn("cpf_cnpj", r.family_counts)

    def test_cpf_with_prefix_keyword_flagged(self):
        text = "CPF: 123.456.789-09 registered"
        r = pp.scan(text)
        self.assertIn("cpf_cnpj", r.family_counts)

    def test_cnpj_with_prefix_keyword_flagged(self):
        text = "cnpj 12.345.678/0001-95 confirmed"
        r = pp.scan(text)
        self.assertIn("cpf_cnpj", r.family_counts)

    def test_keyword_within_window_flagged(self):
        text = "Campo CPF obrigatório — 123.456.789-09"
        r = pp.scan(text)
        self.assertIn("cpf_cnpj", r.family_counts)


# ---------------------------------------------------------------------------
# PLAN-113 W4-SEC — additional Brazilian LGPD identifier families
# (RG, CNH, PIS/PASEP, passport-BR, IBAN-BR). Positive + negative + redact.
# ---------------------------------------------------------------------------


class TestRgFamily(unittest.TestCase):
    def test_rg_with_context_grouped_flagged(self):
        r = pp.scan("RG 12.345.678-9 emitido em SP")
        self.assertIn("rg", r.family_counts)

    def test_rg_with_context_check_char_x_flagged(self):
        r = pp.scan("RG: 12.345.678-X")
        self.assertIn("rg", r.family_counts)

    def test_rg_identidade_keyword_flagged(self):
        r = pp.scan("Identidade 123456789 do titular")
        self.assertIn("rg", r.family_counts)

    def test_rg_without_context_not_flagged(self):
        # Same digit shape but no RG/identidade keyword nearby.
        r = pp.scan("valor 12.345.678-9 avulso na nota")
        self.assertNotIn("rg", r.family_counts)

    def test_rg_redacted(self):
        r = pp.scan("RG 12.345.678-9 emitido", mode="redact")
        self.assertIn("[REDACTED:RG]", r.redacted_text)
        self.assertNotIn("12.345.678-9", r.redacted_text)


class TestCnhFamily(unittest.TestCase):
    def test_cnh_with_context_flagged(self):
        r = pp.scan("CNH 12345678901 valida")
        self.assertIn("cnh", r.family_counts)

    def test_cnh_habilitacao_keyword_flagged(self):
        r = pp.scan("habilitação numero 98765432100 vencida")
        self.assertIn("cnh", r.family_counts)

    def test_cnh_without_context_not_flagged(self):
        # 11 bare digits without CNH context (and no CPF context either).
        r = pp.scan("sequence 12345678901 in the stream")
        self.assertNotIn("cnh", r.family_counts)
        self.assertNotIn("cpf_cnpj", r.family_counts)

    def test_cnh_redacted(self):
        r = pp.scan("CNH 12345678901 valida", mode="redact")
        self.assertIn("[REDACTED:CNH]", r.redacted_text)
        self.assertNotIn("12345678901", r.redacted_text)


class TestPisPasepFamily(unittest.TestCase):
    def test_pis_grouped_with_context_flagged(self):
        r = pp.scan("PIS 123.45678.90-1 cadastrado")
        self.assertIn("pis_pasep", r.family_counts)

    def test_pasep_keyword_flagged(self):
        r = pp.scan("PASEP: 120.12345.67-8 registrado")
        self.assertIn("pis_pasep", r.family_counts)

    def test_nit_bare_with_context_flagged(self):
        r = pp.scan("NIT 12012345678 do segurado")
        self.assertIn("pis_pasep", r.family_counts)

    def test_pis_without_context_not_flagged(self):
        r = pp.scan("valor 123.45678.90-1 avulso")
        self.assertNotIn("pis_pasep", r.family_counts)

    def test_pis_redacted(self):
        r = pp.scan("PIS 123.45678.90-1 cadastrado", mode="redact")
        self.assertIn("[REDACTED:PIS_PASEP]", r.redacted_text)
        self.assertNotIn("123.45678.90-1", r.redacted_text)


class TestPassportBrFamily(unittest.TestCase):
    def test_passport_with_context_flagged(self):
        r = pp.scan("passaporte AB123456 valido ate 2030")
        self.assertIn("passport_br", r.family_counts)

    def test_passport_english_keyword_flagged(self):
        r = pp.scan("passport YA999888 issued")
        self.assertIn("passport_br", r.family_counts)

    def test_passport_without_context_not_flagged(self):
        # Generic 2-letter + 6-digit code without passport context.
        r = pp.scan("codigo AB123456 do produto")
        self.assertNotIn("passport_br", r.family_counts)

    def test_passport_redacted(self):
        r = pp.scan("passaporte AB123456 valido", mode="redact")
        self.assertIn("[REDACTED:PASSPORT_BR]", r.redacted_text)
        self.assertNotIn("AB123456", r.redacted_text)


class TestIbanBrFamily(unittest.TestCase):
    def test_iban_br_no_context_needed_flagged(self):
        # Structurally distinctive — matches WITHOUT a context keyword.
        r = pp.scan("BR1500000000000010932840814P2")
        self.assertIn("iban_br", r.family_counts)

    def test_iban_br_with_label_flagged(self):
        r = pp.scan("IBAN BR9700360305000010009795493P1 confirmado")
        self.assertIn("iban_br", r.family_counts)

    def test_iban_br_spaced_groups_flagged(self):
        r = pp.scan("conta BR15 0000 0000 0000 1093 2840 814P 2 aqui")
        self.assertIn("iban_br", r.family_counts)

    def test_iban_br_too_short_not_flagged(self):
        r = pp.scan("not an iban BR12 short here")
        self.assertNotIn("iban_br", r.family_counts)

    def test_iban_br_too_long_not_flagged(self):
        # 'BR'+2+25 then EXTRA chars → \b boundary fails, no match.
        r = pp.scan("over BR1500000000000010932840814P2EXTRA done")
        self.assertNotIn("iban_br", r.family_counts)

    def test_iban_non_br_country_not_flagged(self):
        # A German IBAN must not match the BR-specific family.
        r = pp.scan("DE89370400440532013000 is German")
        self.assertNotIn("iban_br", r.family_counts)

    def test_iban_br_redacted(self):
        r = pp.scan("conta BR1500000000000010932840814P2 ok", mode="redact")
        self.assertIn("[REDACTED:IBAN_BR]", r.redacted_text)
        self.assertNotIn("BR1500000000000010932840814P2", r.redacted_text)


class TestNewFamiliesInPublicSurface(unittest.TestCase):
    def test_families_list_includes_new(self):
        fams = pp.families()
        for fam in ("rg", "cnh", "pis_pasep", "passport_br", "iban_br"):
            self.assertIn(fam, fams, f"families() must list {fam!r}")

    def test_clean_brazilian_prose_no_false_positives(self):
        # A paragraph that mentions documents WITHOUT actual identifiers
        # must stay clean (no over-broad regex firing).
        text = (
            "O cliente apresentou seus documentos pessoais na agência "
            "para abertura de conta corrente nova hoje."
        )
        r = pp.scan(text)
        self.assertFalse(
            r.matched,
            f"clean prose matched unexpectedly: {r.family_counts}",
        )


# ---------------------------------------------------------------------------
# Mode flag vs redact
# ---------------------------------------------------------------------------


class TestScanModes(unittest.TestCase):
    def test_flag_mode_preserves_text(self):
        text = "leak sk-abcDEF1234567890xyzABCDEFGHIJKL here"
        r = pp.scan(text, mode="flag")
        self.assertTrue(r.matched)
        self.assertEqual(r.redacted_text, text)

    def test_redact_mode_replaces_with_token(self):
        text = "leak sk-abcDEF1234567890xyzABCDEFGHIJKL here"
        r = pp.scan(text, mode="redact")
        self.assertTrue(r.matched)
        self.assertIn("[REDACTED:API_KEY]", r.redacted_text)
        self.assertNotIn("sk-abcDEF1234567890", r.redacted_text)

    def test_invalid_mode_falls_back_to_flag(self):
        text = "leak sk-abcDEF1234567890xyzABCDEFGHIJKL here"
        r = pp.scan(text, mode="bogus")
        self.assertEqual(r.redacted_text, text)


# ---------------------------------------------------------------------------
# ScanResult / SCANNER_PIPELINE surface
# ---------------------------------------------------------------------------


class TestPublicSurface(unittest.TestCase):
    def test_families_list(self):
        fams = pp.families()
        self.assertIn("api_key", fams)
        self.assertIn("jwt", fams)
        self.assertIn("bearer", fams)
        self.assertIn("cpf_cnpj", fams)
        self.assertIn("credit_card_pan", fams)
        self.assertIn("email_in_log", fams)
        self.assertIn("entropy", fams)

    def test_scanner_pipeline_alias(self):
        self.assertIs(pp.SCANNER_PIPELINE, pp.scan)

    def test_truncation_bound(self):
        # >1 MiB input should set truncated=True
        huge = "a" * (1024 * 1024 + 100)
        r = pp.scan(huge)
        self.assertTrue(r.truncated)
        self.assertEqual(r.bytes_scanned, 1024 * 1024)

    def test_none_input_returns_empty_result(self):
        r = pp.scan(None)  # type: ignore[arg-type]
        self.assertFalse(r.matched)
        self.assertEqual(r.match_count, 0)

    def test_clean_input_matched_false(self):
        r = pp.scan("Nothing to see here.")
        self.assertFalse(r.matched)
        self.assertEqual(r.family_counts, {})


# ---------------------------------------------------------------------------
# Env-isolated integration to confirm no HOME/CLAUDE_PROJECT_DIR side effects
# ---------------------------------------------------------------------------


class TestEnvIsolation(TestEnvContext):
    def test_scan_does_not_touch_audit_dir(self):
        pp.scan("sk-abcDEF1234567890xyzABCDEFGHIJKL")
        # pure function — must not create audit log
        self.assertFalse((self.audit_dir / "audit-log.jsonl").exists())


if __name__ == "__main__":
    unittest.main()
