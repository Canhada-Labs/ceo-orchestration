"""PLAN-050 Phase 0.5 — tests for secret_patterns catalog.

STAGED: .claude/plans/PLAN-050/staged-code/test_secret_patterns.py
TARGET: .claude/hooks/tests/test_secret_patterns.py

Per qa-architect #3 consensus: positive + negative corpus per family +
property tests. Per security-engineer #1+#2+#16: token family coverage
+ ReDoS budget + LGPD PII validators.

Run standalone (from staged location):
    PYTHONPATH=.claude/plans/PLAN-050/staged-code \\
        python3 -m pytest .claude/plans/PLAN-050/staged-code/test_secret_patterns.py -q
"""
from __future__ import annotations

import functools
import os
import random
import sys
import time
import unicodedata
from pathlib import Path
from unittest import mock

# Mirror the pattern used by sibling hook tests (see test_redact.py):
# add .claude/hooks/ to sys.path so `from _lib import …` resolves.
_HOOKS_DIR = Path(__file__).resolve().parent.parent

from _lib import secret_patterns as sp  # type: ignore  # noqa: E402
from _lib.testing import TestEnvContext  # type: ignore  # noqa: E402


# --------------------------------------------------------------------------
# Catalog sanity
# --------------------------------------------------------------------------


def test_catalog_version_is_semver():
    assert sp.CATALOG_VERSION.count(".") == 2
    for part in sp.CATALOG_VERSION.split("."):
        int(part)


def test_secrets_has_29_families():
    # 17 token families + 1 PEM header + 1 secret-key-value (aws_secret) = 19 original
    # + 10 cloud/KMS families (PLAN-113 W4-SEC v1.1.0) = 29
    assert len(sp.SECRETS) == 29


def test_pii_has_11_families():
    # 4 original (br_cpf, br_cnpj, br_phone, credit_card)
    # + 7 additional LGPD/BR (PLAN-113 W4-SEC v1.2.0):
    #   br_titulo_eleitor, br_ctps, br_rg, br_cnh, br_pis_pasep, br_passport, br_iban
    assert len(sp.PII) == 11


def test_all_patterns_has_40():
    assert len(sp.ALL_PATTERNS) == 40
    # Family ids are unique
    ids = [p.family_id for p in sp.ALL_PATTERNS]
    assert len(set(ids)) == len(ids)


def test_all_regexes_use_ascii_flag():
    import re as _re
    for p in sp.ALL_PATTERNS:
        assert p.regex.flags & _re.ASCII, f"{p.family_id} missing re.ASCII"


def test_every_pattern_has_redaction_label():
    for p in sp.ALL_PATTERNS:
        assert p.redaction_label.startswith("[REDACTED:")
        assert p.redaction_label.endswith("]")


def test_family_ids_returns_full_list():
    ids = sp.family_ids()
    assert len(ids) == 40
    assert "anthropic_api_key" in ids
    assert "br_cpf" in ids
    # Cloud/KMS families
    assert "azure_client_secret" in ids
    assert "hashicorp_vault_token" in ids
    # Additional LGPD families
    assert "br_titulo_eleitor" in ids
    assert "br_iban" in ids


# --------------------------------------------------------------------------
# Registry constants (F-7.4-drift unified dispatch)
# --------------------------------------------------------------------------


def test_canonical_family_ids_matches_all_patterns():
    """CANONICAL_FAMILY_IDS is derived from ALL_PATTERNS and stays in sync."""
    assert set(sp.CANONICAL_FAMILY_IDS) == {p.family_id for p in sp.ALL_PATTERNS}


def test_lgpd_family_ids_subset_of_canonical():
    """All LGPD_FAMILY_IDS are in CANONICAL_FAMILY_IDS."""
    assert set(sp.LGPD_FAMILY_IDS).issubset(set(sp.CANONICAL_FAMILY_IDS))


def test_cloud_kms_family_ids_subset_of_canonical():
    """All CLOUD_KMS_FAMILY_IDS are in CANONICAL_FAMILY_IDS."""
    assert set(sp.CLOUD_KMS_FAMILY_IDS).issubset(set(sp.CANONICAL_FAMILY_IDS))


def test_lgpd_families_include_all_br_identifiers():
    """All Brazilian identifier families are tagged LGPD."""
    expected_lgpd = {
        "br_cpf", "br_cnpj", "br_phone", "credit_card",
        "br_titulo_eleitor", "br_ctps", "br_rg", "br_cnh",
        "br_pis_pasep", "br_passport", "br_iban",
    }
    assert expected_lgpd.issubset(set(sp.LGPD_FAMILY_IDS)), (
        f"Missing LGPD families: {expected_lgpd - set(sp.LGPD_FAMILY_IDS)}"
    )


def test_cloud_kms_families_all_present():
    """All cloud/KMS families added in PLAN-113 W4-SEC are in CLOUD_KMS_FAMILY_IDS."""
    expected = {
        "azure_client_secret", "azure_sas_token", "oci_api_key", "ibm_cloud_api_key",
        "aws_kms_key_id", "aws_sts_token", "hashicorp_vault_token",
        "bitbucket_app_password", "square_api_key", "codex_session_token",
    }
    assert expected == set(sp.CLOUD_KMS_FAMILY_IDS), (
        f"Drift detected in CLOUD_KMS_FAMILY_IDS: expected {expected}, "
        f"got {set(sp.CLOUD_KMS_FAMILY_IDS)}"
    )


def test_catalog_self_consistent():
    """assert_catalog_self_consistent() passes without raising."""
    sp.assert_catalog_self_consistent()  # raises AssertionError on failure


def test_pii_patterns_known_slugs_non_empty():
    """PII_PATTERNS_KNOWN_SLUGS is non-empty and contains expected families."""
    assert len(sp.PII_PATTERNS_KNOWN_SLUGS) > 0
    assert "cpf_cnpj" in sp.PII_PATTERNS_KNOWN_SLUGS
    assert "iban_br" in sp.PII_PATTERNS_KNOWN_SLUGS


# --------------------------------------------------------------------------
# Positive cases per family (known-bad inputs MUST match)
# --------------------------------------------------------------------------


def _assert_family_matches(text: str, expected_family: str):
    findings = sp.scan(text)
    families = [f.family_id for f in findings]
    assert expected_family in families, (
        f"Expected {expected_family} in {families} for input: {text!r}"
    )


def test_anthropic_api_key_positive():
    _assert_family_matches("sk-ant-api03-" + "a" * 100, "anthropic_api_key")


def test_openai_legacy_key_positive():
    _assert_family_matches("sk-" + "A" * 48, "openai_api_key_legacy")


def test_openai_project_key_positive():
    _assert_family_matches("sk-proj-" + "B" * 50, "openai_project_key")


def test_aws_access_key_positive():
    _assert_family_matches("AKIAIOSFODNN7EXAMPLE", "aws_access_key")


def test_google_api_key_positive():
    # AIza + exactly 35 chars
    _assert_family_matches("AIzaSyD" + "x" * 32, "google_api_key")


def test_google_oauth_refresh_positive():
    _assert_family_matches("1//0" + "a" * 65, "google_oauth_refresh")


def test_github_pat_positive():
    _assert_family_matches("ghp_" + "x" * 36, "github_personal_token")


def test_github_oauth_positive():
    _assert_family_matches("gho_" + "Y" * 36, "github_oauth_token")


def test_gitlab_pat_positive():
    _assert_family_matches("glpat-" + "z" * 20, "gitlab_personal_token")


def test_stripe_secret_positive():
    _assert_family_matches("sk_live_" + "9" * 24, "stripe_secret_key")


def test_huggingface_token_positive():
    _assert_family_matches("hf_" + "A" * 34, "huggingface_token")


def test_slack_token_positive():
    _assert_family_matches("xoxb-1234567890-abcdef", "slack_token")


def test_npm_token_positive():
    _assert_family_matches("npm_" + "Z" * 36, "npm_token")


def test_digitalocean_positive():
    _assert_family_matches("dop_v1_" + "a" * 64, "digitalocean_token")


def test_linear_api_key_positive():
    _assert_family_matches("lin_api_" + "M" * 30, "linear_api_key")


def test_twilio_sid_positive():
    _assert_family_matches("AC" + "a" * 32, "twilio_account_sid")


def test_jwt_positive():
    token = "eyJhbGciOiJIUzI1NiJ9.eyJzdWIiOiIxMjM0NTY3ODkwIn0." + "x" * 20
    _assert_family_matches(token, "jwt_token")


def test_private_key_pem_positive():
    for header in [
        "-----BEGIN RSA PRIVATE KEY-----",
        "-----BEGIN EC PRIVATE KEY-----",
        "-----BEGIN DSA PRIVATE KEY-----",
        "-----BEGIN OPENSSH PRIVATE KEY-----",
        "-----BEGIN PRIVATE KEY-----",
    ]:
        _assert_family_matches(header, "private_key_pem")


# --------------------------------------------------------------------------
# Cloud / KMS token positives (PLAN-113 W4-SEC F-7.3-cloud)
# --------------------------------------------------------------------------


def test_azure_client_secret_positive():
    _assert_family_matches(
        "client_secret=AbCdEfGhIjKlMnOpQrStUvWxYz01234567",
        "azure_client_secret",
    )


def test_azure_sas_token_positive():
    _assert_family_matches(
        "sv=2023-01-01&ss=bfqt&srt=sco&sp=rwdlacupiytfx&se=2023-12-31&sig=abc12345678901234567890abcde",
        "azure_sas_token",
    )


def test_hashicorp_vault_token_positive():
    _assert_family_matches("hvs.CAESIJH6gMvbblqFjNxfeBYjlpO7xOQ2wQDovGbY", "hashicorp_vault_token")


def test_hashicorp_vault_token_hvb_positive():
    _assert_family_matches("hvb.CAESIJH6gMvbblqFjNxfeBYjlpO7xOQ2wQDovGbY", "hashicorp_vault_token")


def test_bitbucket_app_password_positive():
    _assert_family_matches("ATBB1234567890abcdefghijklmnopqrstuvwxyz", "bitbucket_app_password")


def test_square_api_key_positive():
    _assert_family_matches("sq0atp-abcdefghijklmnopqrstuvwxyz", "square_api_key")


def test_square_api_key_access_token_positive():
    _assert_family_matches("sq0i-abcdefghijklmnopqrstuvwxyz", "square_api_key")


def test_codex_session_token_positive():
    _assert_family_matches("codex-session-abcdefghijklmnopqrstuvwxyz", "codex_session_token")


def test_aws_kms_key_id_positive():
    _assert_family_matches("kms_key_id=12345678-1234-1234-1234-123456789012", "aws_kms_key_id")


def test_aws_sts_token_positive():
    long_token = "A" * 100
    _assert_family_matches(f"AWS_SESSION_TOKEN=FQoGZXIvYXdzEBkaDGNlcDRTSTRHCQXJijk{long_token}", "aws_sts_token")


# --------------------------------------------------------------------------
# LGPD PII positives (with checksum validators)
# --------------------------------------------------------------------------


def test_br_cpf_positive_valid_checksum():
    # 111.444.777-35 is checksum-valid
    _assert_family_matches("111.444.777-35", "br_cpf")


def test_br_cpf_negative_invalid_checksum():
    # 111.444.777-99 (wrong last two digits) should NOT match (validator rejects)
    findings = sp.scan("111.444.777-99")
    assert "br_cpf" not in [f.family_id for f in findings]


def test_br_cpf_negative_trivial_repeat():
    # All same digit rejected
    findings = sp.scan("111.111.111-11")
    assert "br_cpf" not in [f.family_id for f in findings]


def test_br_cnpj_positive_valid_checksum():
    # 11.222.333/0001-81 is a known-valid test CNPJ
    _assert_family_matches("11.222.333/0001-81", "br_cnpj")


def test_br_cnpj_negative_invalid_checksum():
    findings = sp.scan("11.222.333/0001-99")
    assert "br_cnpj" not in [f.family_id for f in findings]


def test_br_phone_positive():
    for phone in [
        "+55 11 98765-4321",
        "+55 (21) 98765-4321",
        "+5511987654321",
    ]:
        findings = sp.scan(phone)
        assert "br_phone" in [f.family_id for f in findings], f"missed: {phone!r}"


def test_credit_card_valid_luhn():
    # Known Luhn-valid test cards (Visa test number)
    _assert_family_matches("4532015112830366", "credit_card")


def test_credit_card_invalid_luhn_rejected():
    # Flip last digit → Luhn fails
    findings = sp.scan("4532015112830365")
    assert "credit_card" not in [f.family_id for f in findings]


# --------------------------------------------------------------------------
# Additional LGPD/BR PII positives (PLAN-113 W4-SEC F-7.11 + F-7.4)
# --------------------------------------------------------------------------


def _generate_titulo_eleitor() -> str:
    """Generate a checksum-valid Título de Eleitor (state 7 = RJ)."""
    seq, state = "00010000", 7
    base = f"{seq}{state:02d}"
    weights1 = [2, 3, 4, 5, 6, 7, 8, 9]
    s1 = sum(int(base[i]) * weights1[i] for i in range(8))
    rem1 = s1 % 11
    d1 = (1 if state in (1, 2) else 0) if rem1 < 2 else 11 - rem1
    s2 = int(base[8]) * 7 + int(base[9]) * 8 + d1 * 9
    rem2 = s2 % 11
    d2 = (1 if state in (1, 2) else 0) if rem2 < 2 else 11 - rem2
    return f"{base}{d1}{d2}"


def _generate_valid_pis() -> str:
    """Generate a checksum-valid PIS/PASEP grouped string."""
    # Build digit string that satisfies modulo-11 check
    weights = [3, 2, 9, 8, 7, 6, 5, 4, 3, 2]
    base = "1000000100"  # 10-digit prefix
    s = sum(int(base[i]) * weights[i] for i in range(10))
    rem = s % 11
    d = 0 if rem < 2 else 11 - rem
    raw = base + str(d)
    return f"{raw[:3]}.{raw[3:8]}.{raw[8:10]}-{raw[10]}"


def test_br_titulo_eleitor_positive():
    titulo = _generate_titulo_eleitor()
    findings = sp.scan(titulo)
    families = [f.family_id for f in findings]
    assert "br_titulo_eleitor" in families, (
        f"Expected br_titulo_eleitor in {families!r} for titulo {titulo!r}"
    )


def test_br_titulo_eleitor_formatted_positive():
    """DEFECT-2 regression: formatted título (with dots) must be redacted.

    The br_titulo_eleitor regex permits optional dots (e.g. ``1234.5678.0712``).
    Previously the validator received the raw dotted string, causing
    ``digits.isdigit()`` to return False and silently rejecting every
    formatted título. After the fix (_titulo_eleitor_validator strips
    non-digits before checksum), formatted inputs are correctly validated.
    """
    titulo_raw = _generate_titulo_eleitor()  # 12 bare digits
    # Format as NNNN.NNNN.NNNN (the canonical dotted grouped form)
    titulo_formatted = f"{titulo_raw[:4]}.{titulo_raw[4:8]}.{titulo_raw[8:12]}"
    findings = sp.scan(titulo_formatted)
    families = [f.family_id for f in findings]
    assert "br_titulo_eleitor" in families, (
        f"DEFECT-2: formatted título {titulo_formatted!r} not redacted. "
        f"raw digits: {titulo_raw!r}. findings: {families!r}"
    )


def test_br_titulo_eleitor_invalid_checksum_rejected():
    # Take a valid titulo and corrupt the last check digit
    titulo = _generate_titulo_eleitor()
    bad = titulo[:-1] + ("9" if titulo[-1] != "9" else "8")
    findings = sp.scan(bad)
    assert "br_titulo_eleitor" not in [f.family_id for f in findings]


def test_br_titulo_eleitor_formatted_invalid_checksum_rejected():
    """Formatted título with wrong checksum must still be rejected."""
    titulo = _generate_titulo_eleitor()
    bad_raw = titulo[:-1] + ("9" if titulo[-1] != "9" else "8")
    bad_formatted = f"{bad_raw[:4]}.{bad_raw[4:8]}.{bad_raw[8:12]}"
    findings = sp.scan(bad_formatted)
    assert "br_titulo_eleitor" not in [f.family_id for f in findings], (
        f"Formatted título with bad checksum should not match: {bad_formatted!r}"
    )


def test_br_pis_pasep_positive():
    pis_grouped = _generate_valid_pis()
    findings = sp.scan(pis_grouped)
    families = [f.family_id for f in findings]
    assert "br_pis_pasep" in families, (
        f"Expected br_pis_pasep in {families!r} for PIS {pis_grouped!r}"
    )


def test_br_pis_pasep_formatted_positive():
    """DEFECT-2 regression (same class): formatted PIS/PASEP (NNN.NNNNN.NN-N) is redacted.

    The _pis_pasep_validator already calls _extract_digits(), so this is
    a confirmatory test proving the existing pattern correctly handles the
    dotted/hyphen format that _generate_valid_pis() produces.
    """
    pis_formatted = _generate_valid_pis()  # already formatted as NNN.NNNNN.NN-N
    assert "." in pis_formatted or "-" in pis_formatted, (
        f"Test precondition: expected formatted PIS, got {pis_formatted!r}"
    )
    findings = sp.scan(pis_formatted)
    families = [f.family_id for f in findings]
    assert "br_pis_pasep" in families, (
        f"Formatted PIS/PASEP {pis_formatted!r} not redacted. findings: {families!r}"
    )


def test_br_rg_positive():
    _assert_family_matches("12.345.678-9", "br_rg")


def test_br_rg_with_x_check_digit():
    _assert_family_matches("12.345.678-X", "br_rg")


def test_br_cnh_positive():
    # CNH is context-gated via regex (includes keyword in match pattern)
    _assert_family_matches("CNH 12345678901 validade", "br_cnh")


def test_br_ctps_positive():
    # CTPS is context-gated via regex
    _assert_family_matches("ctps 12345/001", "br_ctps")


def test_br_passport_positive():
    # passport-BR context-gated on passaporte/passport keyword
    _assert_family_matches("passaporte AB123456 vencido", "br_passport")


def test_br_iban_positive():
    # IBAN-BR: 'BR' + 2 check digits + 25 BBAN chars = 29 chars total
    iban = "BR" + "15" + "0" * 25
    _assert_family_matches(iban, "br_iban")


def test_br_iban_too_short_not_matched():
    # 27 chars (2 short) must NOT match
    short_iban = "BR" + "15" + "0" * 23  # 27 chars, not 29
    findings = sp.scan(short_iban)
    assert "br_iban" not in [f.family_id for f in findings]


def test_titulo_eleitor_checksum_validator():
    assert sp._titulo_eleitor_checksum_ok(_generate_titulo_eleitor())
    # All-same digits → rejected
    assert not sp._titulo_eleitor_checksum_ok("111111111111")
    # Invalid state (00) → rejected
    assert not sp._titulo_eleitor_checksum_ok("000000000000")


def test_pis_pasep_checksum_validator():
    raw = _generate_valid_pis().replace(".", "").replace("-", "")
    assert sp._pis_pasep_checksum_ok(raw)
    # Wrong last digit → rejected
    bad = raw[:-1] + ("9" if raw[-1] != "9" else "8")
    assert not sp._pis_pasep_checksum_ok(bad)


# --------------------------------------------------------------------------
# Negative cases (clean text MUST NOT match)
# --------------------------------------------------------------------------


def test_clean_text_no_matches():
    texts = [
        "This is a normal README.",
        "Contact support@example.com for questions.",
        "The password field is required.",
        "Commit SHA is abc123def456.",
        "Function returns True on success.",
        "Hello, world! How are you today?",
    ]
    for text in texts:
        findings = sp.scan(text)
        assert findings == [], f"False positive on clean text: {text!r} -> {findings}"


def test_low_entropy_hex_not_matched_as_sha():
    # sha-looking but not a token pattern
    findings = sp.scan("commit abc123def456789")
    # Don't match any token family
    token_families = [f for f in findings if f.category == "token"]
    assert token_families == []


def test_short_strings_no_match():
    for s in ["hf_", "ghp_", "AIza", "sk-"]:
        findings = sp.scan(s)
        assert findings == [], f"short prefix matched: {s!r}"


# --------------------------------------------------------------------------
# Redaction
# --------------------------------------------------------------------------


def test_redact_preserves_unmatched_text():
    text = "Before sk-ant-api03-" + "a" * 100 + " after"
    redacted, findings = sp.scan_and_redact(text)
    assert redacted.startswith("Before ")
    assert redacted.endswith(" after")
    assert "[REDACTED:anthropic_key]" in redacted
    assert len(findings) == 1


def test_redact_multiple_findings():
    text = "A: sk-ant-api03-" + "a" * 100 + " B: ghp_" + "x" * 36
    redacted, findings = sp.scan_and_redact(text)
    assert "[REDACTED:anthropic_key]" in redacted
    assert "[REDACTED:github_pat]" in redacted
    assert len(findings) == 2


def test_redact_empty_findings_returns_original():
    text = "Clean text here."
    redacted = sp.redact(text, [])
    assert redacted == text


# --------------------------------------------------------------------------
# Unicode normalization (homoglyph / tag-char / RTL evasion)
# --------------------------------------------------------------------------


def test_nfkc_normalization_applied_by_default():
    # Fullwidth digits should normalize to ASCII digits
    text = "AKIA" + "I" + "O" + "SFODNN7EXAMPLE"  # baseline ASCII
    findings = sp.scan(text)
    assert "aws_access_key" in [f.family_id for f in findings]


def test_can_disable_normalization():
    # Just ensure the flag works without error
    findings = sp.scan("AKIAIOSFODNN7EXAMPLE", normalize_unicode=False)
    assert "aws_access_key" in [f.family_id for f in findings]


# --------------------------------------------------------------------------
# ReDoS budget enforcement (security-engineer #2)
# --------------------------------------------------------------------------


def test_scan_completes_under_500ms_on_100kb_no_match():
    adversarial = "a" * 100_000  # 100KB all-a, no matches
    t0 = time.perf_counter()
    findings = sp.scan(adversarial, budget_seconds=0.5)
    elapsed = time.perf_counter() - t0
    assert elapsed < 0.5, f"scan took {elapsed*1000:.1f}ms (budget 500ms)"
    assert findings == []


def test_scan_completes_under_budget_on_normal_text():
    text = "This is a normal text. " * 4000  # ~100KB normal
    t0 = time.perf_counter()
    sp.scan(text, budget_seconds=0.5)
    elapsed = time.perf_counter() - t0
    assert elapsed < 0.5, f"scan took {elapsed*1000:.1f}ms (budget 500ms)"


def test_scan_timeout_raises_on_impossibly_short_budget():
    # Not practical to trigger via real regex; verify ITIMER plumbing
    # exists by checking imports
    assert hasattr(sp, "ScanBudgetExceeded")
    assert hasattr(sp, "_install_itimer_guard")


# --------------------------------------------------------------------------
# Validators (direct unit tests)
# --------------------------------------------------------------------------


def test_luhn_valid():
    assert sp._luhn_ok("4532015112830366")


def test_luhn_invalid():
    assert not sp._luhn_ok("4532015112830365")
    assert not sp._luhn_ok("1234567890123456")


def test_luhn_rejects_short():
    assert not sp._luhn_ok("1234567")  # too short


def test_luhn_rejects_non_digit():
    assert not sp._luhn_ok("4532a15112830366")


def test_cpf_valid():
    assert sp._cpf_checksum_ok("11144477735")


def test_cpf_invalid():
    assert not sp._cpf_checksum_ok("11144477799")
    assert not sp._cpf_checksum_ok("99999999999")  # repeat


def test_cpf_rejects_wrong_length():
    assert not sp._cpf_checksum_ok("111")
    assert not sp._cpf_checksum_ok("1" * 12)


def test_cnpj_valid():
    assert sp._cnpj_checksum_ok("11222333000181")


def test_cnpj_invalid():
    assert not sp._cnpj_checksum_ok("11222333000199")
    assert not sp._cnpj_checksum_ok("11111111111111")  # repeat


# --------------------------------------------------------------------------
# Ordering + determinism
# --------------------------------------------------------------------------


def test_findings_ordered_by_start_position():
    text = "Second ghp_" + "x" * 36 + " first sk-ant-api03-" + "a" * 100
    findings = sp.scan(text)
    # They should be returned in order of occurrence in text
    starts = [f.start for f in findings]
    assert starts == sorted(starts), f"not sorted: {starts}"


def test_scan_is_deterministic():
    text = "sk-ant-api03-" + "a" * 100
    r1 = sp.scan(text)
    r2 = sp.scan(text)
    assert r1 == r2


# --------------------------------------------------------------------------
# Integration with potential hook consumers
# --------------------------------------------------------------------------


def test_scan_can_be_called_many_times_without_itimer_leak():
    """Regression: ITIMER should be cleared between calls."""
    for _ in range(20):
        findings = sp.scan("normal text")
        assert findings == []


# --------------------------------------------------------------------------
# History of the class. scan() used to match only the NFKC view and redact()
# then cut the ORIGINAL with those offsets, so any length-changing character
# before a secret (U+2026 -> "...", U+2116 -> "No", ligatures, composing
# sequences that SHRINK) shifted the cut and left secret bytes in the output
# (10 ellipses before an AWS key = the whole key survived). Overlapping
# and adjacent spans are merged before splicing.
# A first cure redacted the NORMALIZED text instead; that
# turned full-width JSON punctuation in an untrusted Codex answer into real
# syntax before json.loads, folded confusables out of outgoing prompts and
# let NFKC growth (U+FDFA = 18 chars) inflate argv.
#
# The oracles are design-agnostic: they look for 4-char windows of a planted
# secret in the output, require every character outside the redacted spans
# to come back byte-identical and in order, and, in the exact tests, require
# the output to equal the input with exactly the secret replaced by its label.
# --------------------------------------------------------------------------

# Built by concatenation (never one literal) so no scanner sees a whole
# token in this source. Five families across token + PII categories.
_FRAME_SECRETS = {
    "aws_access_key": "AK" + "IA" + "Q7W3E9R5T1Y8U2I4",
    "github_personal_token": "gh" + "p_" + "Rk3Vb8Nq1Zt6Hy0Lp5Jx2Mc7Dw4Fs9GaQe1U",
    "stripe_secret_key": "sk_" + "live_" + "4eTg7YhUj2KiOl9PzXcVbN3m",
    "br_cpf": "529.982" + ".247-25",
    "credit_card": "4532015" + "112830366",
}

# NFKC-changing characters: growing (1 -> 2..18 chars), shrinking
# (2 -> 1 char: composing sequences) and same-length (no shift).
_GROWERS = (
    "…",  # HORIZONTAL ELLIPSIS        -> "..."
    "№",  # NUMERO SIGN                -> "No"
    "ﬁ",  # LATIN SMALL LIGATURE FI    -> "fi"
    "ﬃ",  # LATIN SMALL LIGATURE FFI   -> "ffi"
    "㍱",  # SQUARE HPA                 -> "hPa"
    "™",  # TRADE MARK SIGN            -> "TM"
    "Ⅻ",  # ROMAN NUMERAL TWELVE       -> "XII"
    "ﷺ",  # ARABIC LIGATURE (18 chars after NFKC)
)
_SHRINKERS = (
    "é",       # e + COMBINING ACUTE      -> U+00E9
    "가",  # HANGUL L + V jamo        -> U+AC00
    "Å",       # A + COMBINING RING ABOVE -> U+00C5
)
_SAME_LENGTH = (
    "Ａ",  # FULLWIDTH LATIN CAPITAL A -> "A"
    " ",  # NO-BREAK SPACE            -> " "
)
_NFKC_POOL = _GROWERS + _SHRINKERS + _SAME_LENGTH
_CONTEXT_WORDS = (" k=", " mid ", " ; ", " tail")
_ALL_LABELS = " ".join(p.redaction_label for p in sp.ALL_PATTERNS)


def _fw(s):
    """Full-width form of printable ASCII (U+FF01..U+FF5E); NFKC folds it back."""
    return "".join(chr(ord(c) + 0xFEE0) if "!" <= c <= "~" else c for c in s)


def _windows(secret, k=4):
    return [secret[i:i + k] for i in range(len(secret) - k + 1)]


def _leaked_windows(output, secrets):
    """Every 4-char window of any secret that survives in ``output``."""
    return sorted({w for s in secrets for w in _windows(s) if w in output})


def _label_for(family_id):
    for p in sp.ALL_PATTERNS:
        if p.family_id == family_id:
            return p.redaction_label
    raise KeyError(family_id)


def _spans(findings):
    return {(f.family_id, f.start, f.end) for f in findings}


class TestOffsetFrameFixtureIsSound(TestEnvContext):
    """Precondition: the leak oracle cannot false-positive on noise."""

    def test_each_secret_is_detected_alone_as_its_family(self):
        for family, secret in _FRAME_SECRETS.items():
            families = [f.family_id for f in sp.scan(" k=" + secret + " tail")]
            self.assertIn(family, families, secret[:6])

    def test_no_secret_window_can_be_built_from_noise_or_labels(self):
        # Every window carries at least one character that no pool character
        # (raw or NFKC'd), no context word and no label can produce, and no
        # window is a substring of a label -- so a window in the output IS a leak.
        noise_chars = set("".join(_NFKC_POOL))
        noise_chars |= set("".join(unicodedata.normalize("NFKC", c) for c in _NFKC_POOL))
        noise_chars |= set("".join(_CONTEXT_WORDS))
        for secret in _FRAME_SECRETS.values():
            for w in _windows(secret):
                self.assertTrue(set(w) - noise_chars, "window %r buildable from noise" % w)
                self.assertNotIn(w, _ALL_LABELS)


class TestScanAndRedactNfkcFrame(TestEnvContext):
    """Secrets after NFKC-changing text: redacted in place, the rest byte-identical."""

    def _each_family(self, prefix):
        for family, secret in _FRAME_SECRETS.items():
            with self.subTest(family=family, prefix=prefix):
                text = prefix + " k=" + secret + " tail"
                redacted, findings = sp.scan_and_redact(text)
                self.assertEqual(_leaked_windows(redacted, [secret]), [], redacted)
                # Exact: the label sits where the secret was and every other
                # character (the NFKC-changing prefix included) is untouched.
                self.assertEqual(redacted, prefix + " k=" + _label_for(family) + " tail")
                start = len(prefix) + 3
                self.assertIn((family, start, start + len(secret)), _spans(findings))

    def test_single_ellipsis_before_secret(self):
        self._each_family("…")

    def test_ten_ellipses_before_secret(self):
        # The measured whole-key leak: the AWS key survived verbatim.
        self._each_family("…" * 10)

    def test_numero_sign_before_secret(self):
        self._each_family("№")

    def test_ligature_before_secret(self):
        self._each_family("ﬁ")

    def test_shrinking_composition_before_secret(self):
        # NFKC SHRINKS here: the tail of the secret used to survive.
        self._each_family("é" * 10)

    def test_eighteen_fold_growth_before_secret(self):
        self._each_family("ﷺ")

    def test_mix_of_growers_and_shrinkers_between_secrets(self):
        parts, expected = [], []
        for i, (family, secret) in enumerate(_FRAME_SECRETS.items()):
            noise = _NFKC_POOL[i % len(_NFKC_POOL)] * (i + 1)
            parts.append(noise + " k=" + secret + " ")
            expected.append(noise + " k=" + _label_for(family) + " ")
        tail = "…№ﬁ⑴ tail"
        redacted, _ = sp.scan_and_redact("".join(parts) + tail)
        self.assertEqual(redacted, "".join(expected) + tail)

    def test_secret_after_text_that_nfkc_leaves_alone_is_byte_compatible(self):
        # No NFKC change -> output identical to the historical splice.
        secret = _FRAME_SECRETS["aws_access_key"]
        text = "plain ascii before k=" + secret + " after"
        redacted, _ = sp.scan_and_redact(text)
        self.assertEqual(redacted, "plain ascii before k=[REDACTED:aws_access_key] after")

    def test_property_random_prefixes_redacted_in_place(self):
        rng = random.Random(20261103)
        families = sorted(_FRAME_SECRETS)
        for case in range(400):
            chosen = rng.sample(families, rng.randint(1, 3))
            parts, expected = [], []
            for family in chosen:
                noise = "".join(rng.choice(_NFKC_POOL) for _ in range(rng.randint(0, 12)))
                ctx = rng.choice((" k=", " mid "))
                parts.append(noise + ctx + _FRAME_SECRETS[family] + " ; ")
                expected.append(noise + ctx + _label_for(family) + " ; ")
            tail = "".join(rng.choice(_NFKC_POOL) for _ in range(rng.randint(0, 6))) + " tail"
            text = "".join(parts) + tail
            redacted, _ = sp.scan_and_redact(text)
            secrets = [_FRAME_SECRETS[f] for f in chosen]
            self.assertEqual(_leaked_windows(redacted, secrets), [], "case %d: %r" % (case, redacted))
            self.assertEqual(redacted, "".join(expected) + tail, "case %d" % case)


class TestOverlappingFindingsFrame(TestEnvContext):
    """Overlapping or adjacent findings must not let any part survive."""

    def test_access_key_inside_secret_access_key_value(self):
        secret = "AK" + "IA" + "Q7W3E9R5T1Y8U2I4" + "/Zp4Lm8Nk2Jh6Gf0Ds5A"
        text = "cfg aws_secret_access_key=" + secret + " end"
        families = {f.family_id for f in sp.scan(text)}
        self.assertEqual(families, {"aws_secret_access_key", "aws_access_key"})
        redacted, _ = sp.scan_and_redact(text)
        self.assertEqual(_leaked_windows(redacted, [secret]), [], redacted)
        self.assertEqual(redacted, "cfg [REDACTED:aws_secret] end")

    def test_credit_card_overlapping_rg(self):
        # credit_card spans the whole run; br_rg matches strictly inside it.
        text = "3 25611696-132887"
        families = {f.family_id for f in sp.scan(text)}
        self.assertEqual(families, {"credit_card", "br_rg"})
        redacted, _ = sp.scan_and_redact(text)
        self.assertEqual(_leaked_windows(redacted, [text]), [], redacted)

    def test_overlap_after_nfkc_growth(self):
        secret = "AK" + "IA" + "Q7W3E9R5T1Y8U2I4" + "/Zp4Lm8Nk2Jh6Gf0Ds5A"
        text = "…" * 7 + " cfg aws_secret_access_key=" + secret + " end"
        redacted, _ = sp.scan_and_redact(text)
        self.assertEqual(_leaked_windows(redacted, [secret]), [], redacted)
        self.assertEqual(redacted, "…" * 7 + " cfg [REDACTED:aws_secret] end")

    def test_adjacent_findings_merge_into_one_label(self):
        first = sp.Finding("aws_access_key", "token", 2, 5, "[X]")
        second = sp.Finding("br_cpf", "pii", 5, 8, "[Y]")
        self.assertEqual(sp.redact("0123456789", [second, first]), "01[X]89")


class TestRedactIsPureOnOriginalText(TestEnvContext):
    """redact(text, scan(text)) cuts the original; redact() stays a pure function."""

    def test_redact_with_default_scan_findings_redacts_in_place(self):
        # The natural call: findings from scan(text) applied to the same text.
        secret = _FRAME_SECRETS["aws_access_key"]
        text = "…" * 10 + " k=" + secret + " tail"
        out = sp.redact(text, sp.scan(text))
        self.assertEqual(out, "…" * 10 + " k=[REDACTED:aws_access_key] tail")

    def test_redact_never_rescans_nor_arms_the_itimer(self):
        secret = _FRAME_SECRETS["github_personal_token"]
        text = "№ k=" + secret + " tail"
        findings = sp.scan(text)
        boom = mock.Mock(side_effect=AssertionError("redact() must stay pure"))
        with mock.patch.object(sp, "scan", boom), \
                mock.patch.object(sp, "_install_itimer_guard", boom), \
                mock.patch.object(sp.signal, "setitimer", boom):
            out = sp.redact(text, findings)
        self.assertEqual(out, "№ k=[REDACTED:github_pat] tail")
        boom.assert_not_called()

    def test_redact_clamps_foreign_offsets_instead_of_raising(self):
        # Findings from ANOTHER text are a documented caller error; redact()
        # stays total (never raises) and never reads outside the text.
        findings = sp.scan("x" * 200 + " k=" + _FRAME_SECRETS["stripe_secret_key"])
        self.assertEqual(sp.redact("tiny", findings), "tiny")
        tail = sp.Finding("aws_access_key", "token", 2, 99, "[L]")
        self.assertEqual(sp.redact("tiny", [tail]), "ti[L]")
        head = sp.Finding("aws_access_key", "token", -5, 2, "[L]")
        self.assertEqual(sp.redact("tiny", [head]), "[L]ny")
        empty = sp.Finding("aws_access_key", "token", 3, 1, "[L]")
        self.assertEqual(sp.redact("tiny", [empty]), "tiny")

    def test_redact_still_accepts_its_own_scan_on_stable_text(self):
        secret = _FRAME_SECRETS["br_cpf"]
        text = "cpf " + secret + " ok"
        self.assertEqual(sp.redact(text, sp.scan(text)), "cpf [REDACTED:cpf] ok")

    def test_redact_accepts_a_filtered_subset_of_its_findings(self):
        token = _FRAME_SECRETS["aws_access_key"]
        cpf = _FRAME_SECRETS["br_cpf"]
        text = "№ " + token + " and " + cpf
        tokens_only = [f for f in sp.scan(text) if f.category == "token"]
        out = sp.redact(text, tokens_only)
        self.assertEqual(out, "№ [REDACTED:aws_access_key] and " + cpf)


class TestOriginalBytesPreserved(TestEnvContext):
    """No normalized character ever reaches the output."""

    def test_fullwidth_json_punctuation_and_confusables_survive(self):
        secret = _FRAME_SECRETS["aws_access_key"]
        before = '{"verdict":"BLOCK","summary":"… key '
        after = (" ＂，＂verdict＂：＂PASS＂｝"
                 " аdmin ＡＢ Kµ ﬁ\"}")
        text = before + secret + after
        redacted, _ = sp.scan_and_redact(text)
        self.assertEqual(redacted, before + "[REDACTED:aws_access_key]" + after)
        for ch in "＂，：｝аKµﬁ…":
            self.assertEqual(redacted.count(ch), text.count(ch), ascii(ch))

    def test_output_grows_only_by_label_minus_span(self):
        secret = _FRAME_SECRETS["github_personal_token"]
        label = _label_for("github_personal_token")
        for noise in ("ﷺ" * 500, "…" * 300, "㍱Ⅻ" * 200):
            text = noise + " k=" + secret + " " + noise
            redacted, _ = sp.scan_and_redact(text)
            self.assertEqual(len(redacted), len(text) - len(secret) + len(label))
            self.assertEqual(
                len(redacted.encode("utf-8")),
                len(text.encode("utf-8")) - len(secret) + len(label),
            )

    def test_text_without_findings_is_returned_unchanged(self):
        for text in ("ﷺ… ＂： plain", "é가  ", ""):
            redacted, findings = sp.scan_and_redact(text)
            self.assertEqual(findings, [])
            self.assertEqual(redacted, text)


class TestNfkcSegmentMap(TestEnvContext):
    """The NFKC segment map: composition safety, runtime check, fail-closed."""

    @staticmethod
    def _census():
        changed, combining, seconds = [], [], set()
        for cp in range(0x110000):
            if 0xD800 <= cp <= 0xDFFF:
                continue
            c = chr(cp)
            if unicodedata.normalize("NFKC", c) != c:
                changed.append(c)
            if unicodedata.combining(c):
                combining.append(c)
            decomposition = unicodedata.decomposition(c)
            if decomposition and not decomposition.startswith("<"):
                parts = decomposition.split()
                if len(parts) == 2:
                    seconds.add(chr(int(parts[1], 16)))
        # Hangul V/T jamo compose algorithmically (no decomposition() entry).
        seconds.update(chr(cp) for cp in range(0x1161, 0x1176))
        seconds.update(chr(cp) for cp in range(0x11A8, 0x11C3))
        return changed, combining, seconds

    def test_ascii_boundary_is_composition_safe_exhaustively(self):
        def nfkc(s):
            return unicodedata.normalize("NFKC", s)

        ascii_chars = [chr(i) for i in range(128)]
        # Premises 1-3 of the proof in secret_patterns.py.
        for a in ascii_chars:
            self.assertEqual(unicodedata.combining(a), 0, repr(a))
            self.assertEqual(unicodedata.normalize("NFKD", a), a, repr(a))
        changed, combining, seconds = self._census()
        self.assertEqual(sorted(c for c in seconds if ord(c) < 128), [])
        self.assertGreater(len(changed), 4000)  # the census is real
        # Every code point NFKC changes, every combining mark and every
        # composition second, against ALL 128 ASCII characters: the cut before
        # ASCII holds, and so does the peel of an uncomposed ASCII starter.
        bad = []
        probe = sorted(set(changed) | set(combining) | seconds)
        for c in probe:
            image = nfkc(c)
            for a in ascii_chars:
                if nfkc(c + a) != image + a:
                    bad.append(("cut", hex(ord(c)), a))
                joined = nfkc(a + c)
                if joined[:1] == a and joined != a + image:
                    bad.append(("peel", hex(ord(c)), a))
        # And EVERY code point (no surrogates) before three ASCII neighbours.
        for a in ('"', "a", "<"):
            for cp in range(0x110000):
                if 0xD800 <= cp <= 0xDFFF:
                    continue
                c = chr(cp)
                if nfkc(c + a) != nfkc(c) + a:
                    bad.append(("cut-all", hex(cp), a))
        self.assertEqual(bad[:20], [])

    def test_segment_map_reconstructs_nfkc_on_random_text(self):
        rng = random.Random(7)
        alphabet = list("ab =;\"\\0") + list(_NFKC_POOL) + [
            "́", "̧", "ᅡ", "ᆨ", "゙", "か", "＂", "：",
            # CJK / kana / Hangul / full-width cut points and their excluded
            # neighbours (half-width voicing mark, combining tone mark).
            "\u4e2d", "\u30fc", "\uac00", "\u3000", "\uff76", "\uff9e", "\u302a",
        ]
        for case in range(500):
            text = "".join(rng.choice(alphabet) for _ in range(rng.randint(0, 40)))
            normalized = unicodedata.normalize("NFKC", text)
            segments = sp._nfkc_segments(text, normalized)
            pieces, pos = [], 0
            for o_start, o_end, n_start, n_end in segments:
                # A real segment (never the fail-closed fallback) holds no
                # ASCII character after its first one, and its image is the
                # NFKC of that segment ALONE.
                self.assertFalse(any(ord(ch) < 128 for ch in text[o_start + 1:o_end]), case)
                self.assertEqual(
                    unicodedata.normalize("NFKC", text[o_start:o_end]),
                    normalized[n_start:n_end], case,
                )
                pieces.append(text[pos:o_start])
                pieces.append(normalized[n_start:n_end])
                pos = o_end
            pieces.append(text[pos:])
            self.assertEqual("".join(pieces), normalized, case)

    def test_runtime_check_fails_closed_to_one_segment(self):
        text = "pre " + "Ａ" * 3 + " post"
        normalized = unicodedata.normalize("NFKC", text)

        def broken(s):
            return unicodedata.normalize("NFKC", s) + "?"

        self.assertEqual(
            sp._nfkc_segments(text, normalized, nfkc=broken),
            [(0, len(text), 0, len(normalized))],
        )

    def test_failed_map_redacts_the_whole_text_rather_than_leak(self):
        secret = _fw(_FRAME_SECRETS["aws_access_key"])  # NFKC frame only
        text = "pre … k=" + secret + " post"
        real = sp._nfkc_segments

        def broken(s):
            return unicodedata.normalize("NFKC", s).upper() + "?"

        with mock.patch.object(sp, "_nfkc_segments", lambda t, n: real(t, n, nfkc=broken)):
            redacted, findings = sp.scan_and_redact(text)
        self.assertEqual(redacted, "[REDACTED:aws_access_key]")
        self.assertEqual([(f.start, f.end) for f in findings], [(0, len(text))])


# --------------------------------------------------------------------------
# Non-ASCII composition-safe cut points (segment-map precision).
# --------------------------------------------------------------------------


def _safe_cut_chars():
    """Every character of secret_patterns._SAFE_CUT (a regex class body)."""
    body, out, i = sp._SAFE_CUT, [], 0
    while i < len(body):
        if i + 2 < len(body) and body[i + 1] == "-":
            out.extend(chr(cp) for cp in range(ord(body[i]), ord(body[i + 2]) + 1))
            i += 3
        else:
            out.append(body[i])
            i += 1
    return out


@functools.lru_cache(maxsize=None)
def _combiner_census():
    """(composition firsts, composition seconds, every char that can combine)."""
    firsts, seconds, combiners = set(), set(), set()
    for cp in range(0x110000):
        if 0xD800 <= cp <= 0xDFFF:
            continue
        c = chr(cp)
        if unicodedata.combining(c) or unicodedata.normalize("NFKC", c) != c:
            combiners.add(c)
        decomposition = unicodedata.decomposition(c)
        if decomposition and not decomposition.startswith("<"):
            parts = decomposition.split()
            if len(parts) == 2:
                firsts.add(chr(int(parts[0], 16)))
                seconds.add(chr(int(parts[1], 16)))
    seconds.update(chr(cp) for cp in range(0x1161, 0x1176))  # Hangul V jamo
    seconds.update(chr(cp) for cp in range(0x11A8, 0x11C3))  # Hangul T jamo
    firsts.update(chr(cp) for cp in range(0x1100, 0x1113))   # Hangul L jamo
    firsts.update(chr(0xAC00 + 28 * i) for i in range(19 * 21))  # LV syllables
    return frozenset(firsts), frozenset(seconds), tuple(sorted(combiners | firsts | seconds))


class TestSafeCutAllowlist(TestEnvContext):
    """Each _SAFE_CUT character is a provable composition boundary.

    The full probe (every allowlisted character against every character
    that can combine, cut AND peel) ran once per supported interpreter;
    this test re-checks the derived property for EVERY allowlisted
    character and a seeded sample of the pairs.
    """

    def _violations(self, c, partners):
        def nfkc(s):
            return unicodedata.normalize("NFKC", s)

        bad, image = [], nfkc(c)
        single = len(unicodedata.normalize("NFKD", c)) == 1
        for x in partners:
            if nfkc(x + c) != nfkc(x) + image:
                bad.append(("cut", hex(ord(x)), hex(ord(c))))
            joined = nfkc(c + x) if single else ""
            if single and joined.startswith(image) and joined != image + nfkc(x):
                bad.append(("peel", hex(ord(c)), hex(ord(x))))
        return bad

    def test_every_allowlisted_char_starts_with_a_starter_that_never_composes_back(self):
        _firsts, seconds, _combiners = _combiner_census()
        chars = _safe_cut_chars()
        self.assertGreater(len(chars), 39000)  # the parse is real
        bad = [hex(ord(c)) for c in chars
               if ord(c) < 0x80
               or unicodedata.combining(unicodedata.normalize("NFKD", c)[0])
               or unicodedata.normalize("NFKD", c)[0] in seconds]
        self.assertEqual(bad[:20], [])

    def test_sampled_pairs_against_every_char_that_can_combine(self):
        _firsts, _seconds, combiners = _combiner_census()
        rng = random.Random(3103)
        chars = _safe_cut_chars()
        big = [c for c in chars if "\u3400" <= c <= "\u9fff" or "\uac00" <= c <= "\ud7a3"]
        big_set = set(big)
        small = [c for c in chars if c not in big_set]
        sample = rng.sample(combiners, 1200)
        bad = []
        for c in small:  # kana, CJK punctuation, full-width forms
            bad.extend(self._violations(c, sample))
        for c in rng.sample(big, 48):  # ideographs and Hangul syllables
            bad.extend(self._violations(c, combiners))
        self.assertEqual(bad[:20], [])

    def test_excluded_characters_would_break_the_cut(self):
        # Negative control: the probe has teeth, and these stay out.
        _firsts, _seconds, combiners = _combiner_census()
        allowed = set(_safe_cut_chars())
        for cp in (0x3099, 0x309A, 0xFF9E, 0xFF9F, 0x1161, 0x11A8, 0x302A):
            with self.subTest(cp=hex(cp)):
                self.assertNotIn(chr(cp), allowed)
                self.assertTrue(self._violations(chr(cp), combiners))


class TestCjkProseIsNotSwallowed(TestEnvContext):
    """In the ideograph, kana and Hangul prose below, only the secret is redacted."""

    def _assert_only_secret(self, before, secret, after, family):
        text = before + secret + after
        redacted, findings = sp.scan_and_redact(text)
        self.assertEqual(redacted, before + _label_for(family) + after)
        self.assertEqual(_spans(findings), {(family, len(before), len(before) + len(secret))})

    def test_fullwidth_key_between_ideographs(self):
        self._assert_only_secret(
            "\u4e2d" * 20000, _fw(_FRAME_SECRETS["aws_access_key"]), "\u4e2d" * 20000,
            "aws_access_key",
        )

    def test_math_alphanumeric_key_after_an_ideograph(self):
        # Head peel for a non-ASCII cut: the ideograph composed with nothing.
        def bold(s):
            return "".join(chr(0x1D400 + ord(c) - 65) if c.isupper() else chr(0x1D7CE + int(c)) for c in s)

        ideograph = chr(0x4E2D)
        self._assert_only_secret(ideograph, bold(_FRAME_SECRETS["aws_access_key"]), ideograph,
                                 "aws_access_key")

    def test_member_number_in_fullwidth_digits(self):
        # br_rg has no validator: the segment map alone bounds the cut.
        self._assert_only_secret("会員番号", "１２３４５６７８", "", "br_rg")

    def test_kana_and_hangul_prose_around_fullwidth_keys(self):
        self._assert_only_secret(
            "これはテストです：", _fw(_FRAME_SECRETS["github_personal_token"]),
            "です。カタカナー", "github_personal_token",
        )
        self._assert_only_secret(
            "비밀번호 ", _fw(_FRAME_SECRETS["stripe_secret_key"]), "입니다", "stripe_secret_key",
        )


class TestOneFindingPerSecret(TestEnvContext):
    """Both frames seeing one secret yield ONE Finding (telemetry counts)."""

    def test_merge_is_per_family_and_overlap_only(self):
        F = sp.Finding
        a = F("aws_access_key", "token", 2, 10, "[A]")
        b = F("aws_access_key", "token", 5, 12, "[A]")
        c = F("br_cpf", "pii", 4, 8, "[C]")
        d = F("aws_access_key", "token", 12, 14, "[A]")  # adjacent: stays apart
        self.assertEqual(
            sp._merge_same_family([d, b, c, a, a]),
            [F("aws_access_key", "token", 2, 12, "[A]"), c, d],
        )
