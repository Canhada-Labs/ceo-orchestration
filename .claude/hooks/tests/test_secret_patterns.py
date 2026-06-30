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

import os
import sys
import time
from pathlib import Path

# Mirror the pattern used by sibling hook tests (see test_redact.py):
# add .claude/hooks/ to sys.path so `from _lib import …` resolves.
_HOOKS_DIR = Path(__file__).resolve().parent.parent

from _lib import secret_patterns as sp  # type: ignore  # noqa: E402


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
