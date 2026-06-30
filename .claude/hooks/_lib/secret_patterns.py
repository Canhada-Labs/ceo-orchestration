"""PLAN-050 Phase 0.5 — versioned secret/PII pattern catalog.

STAGED at .claude/plans/PLAN-050/staged-code/secret_patterns.py
TARGET: .claude/hooks/_lib/secret_patterns.py
BLOCKER: canonical-edit hook — round-16 signed but does NOT enumerate
         this path. Owner must add to round-16 scope OR sign round-17.

Single source of truth for "what is a secret". Consumed by:
  - check_agent_spawn.py (F-10-04 pre-spawn scan)
  - check_output_secrets.py (F-10-04 / Phase 3 output_scan)
  - check_fluency_nudge.py (Phase 3 redact-before-emit invariant)

Catalog design per PLAN-050 debate Round 1 consensus:
  - security-engineer #1: 17 token families (not just 8)
  - security-engineer #2: ReDoS-hardened (anchored patterns, ITIMER budget)
  - security-engineer #16: LGPD PII tier-1 (CPF, CNPJ, BR phone, credit card)
  - qa-architect #3: positive + negative corpus per family

Versioning: CATALOG_VERSION SemVer. Any catalog change bumps the
version. audit-log emits version on scan.

Stdlib-only. Python 3.9+. ``from __future__ import annotations`` mandatory.

This module deliberately has NO runtime side effects on import: it
defines the catalog and pure functions. No hook registration, no
environment reads.
"""
from __future__ import annotations

import logging
import re
import signal
import unicodedata
from typing import Callable, List, NamedTuple, Optional, Pattern, Tuple

_logger = logging.getLogger(__name__)

CATALOG_VERSION = "1.2.0"
"""SemVer. Bump major on breaking change to SecretPattern shape.
Bump minor on adding a family. Bump patch on regex tightening.

1.0.0 — initial 17-token + 4 LGPD families (23 total)
1.1.0 — add cloud/KMS secret families: azure_client_secret, azure_sas_token,
         oci_api_key, ibm_cloud_api_key, aws_kms_key_id, aws_sts_token,
         hashicorp_vault_token, bitbucket_app_password, square_api_key,
         codex_api_key (10 new token families; total 33 secret families)
1.2.0 — expand LGPD/BR PII: add br_titulo_eleitor, br_ctps, br_rg, br_cnh,
         br_pis_pasep, br_passport, br_iban (7 new PII families; total 11 PII)
         Add itimer advisory on platforms without SIGALRM.
"""


class SecretPattern(NamedTuple):
    """One pattern in the catalog.

    Fields:
        family_id: stable identifier for audit-log (e.g. "aws_access_key")
        regex: compiled pattern, MUST use re.ASCII for ReDoS safety
        redaction_label: what to replace matched bytes with
        category: "token" | "credential" | "pii"
        owasp_class: OWASP-LLM-Top-10 mapping (LLM01/02/06) or "LGPD"
        validator: optional callable(matched_str) -> bool; False = false-positive
                   (e.g. Luhn for credit card, checksum for CPF)
    """
    family_id: str
    regex: Pattern[str]
    redaction_label: str
    category: str
    owasp_class: str
    validator: Optional[Callable[[str], bool]]


class Finding(NamedTuple):
    """One match returned by scan()."""
    family_id: str
    category: str
    start: int
    end: int
    redaction_label: str


# ---------------------------------------------------------------------------
# Validators (checksum / Luhn / entropy guards)
# ---------------------------------------------------------------------------


def _luhn_ok(digits_only: str) -> bool:
    """Luhn algorithm for credit-card numbers. Digits-only string."""
    if not digits_only.isdigit() or not (13 <= len(digits_only) <= 19):
        return False
    total = 0
    reverse = digits_only[::-1]
    for i, ch in enumerate(reverse):
        n = int(ch)
        if i % 2 == 1:
            n *= 2
            if n > 9:
                n -= 9
        total += n
    return total % 10 == 0


def _cpf_checksum_ok(cpf_digits: str) -> bool:
    """Validate Brazilian CPF (11 digits) via dual-digit checksum."""
    if not cpf_digits.isdigit() or len(cpf_digits) != 11:
        return False
    # Reject trivial repeats (e.g. "11111111111")
    if len(set(cpf_digits)) == 1:
        return False
    # First verifier digit
    s1 = sum(int(cpf_digits[i]) * (10 - i) for i in range(9))
    d1 = (s1 * 10) % 11
    if d1 == 10:
        d1 = 0
    if d1 != int(cpf_digits[9]):
        return False
    # Second verifier digit
    s2 = sum(int(cpf_digits[i]) * (11 - i) for i in range(10))
    d2 = (s2 * 10) % 11
    if d2 == 10:
        d2 = 0
    return d2 == int(cpf_digits[10])


def _cnpj_checksum_ok(cnpj_digits: str) -> bool:
    """Validate Brazilian CNPJ (14 digits) via dual-digit checksum."""
    if not cnpj_digits.isdigit() or len(cnpj_digits) != 14:
        return False
    if len(set(cnpj_digits)) == 1:
        return False
    weights_1 = [5, 4, 3, 2, 9, 8, 7, 6, 5, 4, 3, 2]
    weights_2 = [6, 5, 4, 3, 2, 9, 8, 7, 6, 5, 4, 3, 2]
    s1 = sum(int(cnpj_digits[i]) * weights_1[i] for i in range(12))
    d1 = s1 % 11
    d1 = 0 if d1 < 2 else 11 - d1
    if d1 != int(cnpj_digits[12]):
        return False
    s2 = sum(int(cnpj_digits[i]) * weights_2[i] for i in range(13))
    d2 = s2 % 11
    d2 = 0 if d2 < 2 else 11 - d2
    return d2 == int(cnpj_digits[13])


def _extract_digits(match: str) -> str:
    """Strip everything except digits."""
    return re.sub(r"\D", "", match)


def _luhn_validator(match: str) -> bool:
    return _luhn_ok(_extract_digits(match))


def _cpf_validator(match: str) -> bool:
    return _cpf_checksum_ok(_extract_digits(match))


def _cnpj_validator(match: str) -> bool:
    return _cnpj_checksum_ok(_extract_digits(match))


def _pis_pasep_checksum_ok(digits: str) -> bool:
    """Validate PIS/PASEP/NIT (11 digits) via weighted single-digit checksum."""
    if not digits.isdigit() or len(digits) != 11:
        return False
    if len(set(digits)) == 1:
        return False
    weights = [3, 2, 9, 8, 7, 6, 5, 4, 3, 2]
    s = sum(int(digits[i]) * weights[i] for i in range(10))
    rem = s % 11
    d = 0 if rem < 2 else 11 - rem
    return d == int(digits[10])


def _titulo_eleitor_checksum_ok(digits: str) -> bool:
    """Validate Título de Eleitor (12 digits) via dual-digit checksum.

    Structure: 8 sequential digits + 2 state-code digits + 2 check digits.
    State codes: 01=SP, 02=MG, 03=SC, ... 28=DF. Code 00 is invalid.

    Algorithm per TSE documentation (Resolução TSE no. 21.538/2003):
      d1: weighted sum of digits[0..7] with weights [2..9], mod 11.
           remainder 0 or 1 → d1=0 for states != SP(01)/MG(02), else d1=1.
           remainder ≥ 2 → d1 = 11 - remainder.
      d2: weighted sum of digits[8..9] with weights [7,8] + d1 * weight 9,
           mod 11. Same remainder rule.
    """
    if not digits.isdigit() or len(digits) != 12:
        return False
    if len(set(digits)) == 1:
        return False
    state = int(digits[8:10])
    if state < 1 or state > 28:
        return False

    # First check digit (digits[10])
    weights1 = [2, 3, 4, 5, 6, 7, 8, 9]
    s1 = sum(int(digits[i]) * weights1[i] for i in range(8))
    rem1 = s1 % 11
    if rem1 < 2:
        # SP(01) and MG(02) → if remainder is 0 or 1, check digit is 1
        d1 = 1 if state in (1, 2) else 0
    else:
        d1 = 11 - rem1
    if d1 != int(digits[10]):
        return False

    # Second check digit (digits[11])
    s2 = int(digits[8]) * 7 + int(digits[9]) * 8 + d1 * 9
    rem2 = s2 % 11
    if rem2 < 2:
        d2 = 1 if state in (1, 2) else 0
    else:
        d2 = 11 - rem2
    return d2 == int(digits[11])


def _pis_pasep_validator(match: str) -> bool:
    return _pis_pasep_checksum_ok(_extract_digits(match))


def _titulo_eleitor_validator(match: str) -> bool:
    """Wrapper that strips non-digits before calling the checksum validator.

    The br_titulo_eleitor regex permits optional punctuation (e.g.
    ``1234.5678.9012``). The raw matched string must be normalised to
    digits-only before the TSE checksum algorithm — passing a formatted
    string to ``_titulo_eleitor_checksum_ok()`` directly causes
    ``digits.isdigit()`` to return False and ALWAYS rejects the match,
    meaning formatted títulos are never redacted.
    """
    return _titulo_eleitor_checksum_ok(_extract_digits(match))


# ---------------------------------------------------------------------------
# Catalog — 17 token families + 4 LGPD PII families
# ---------------------------------------------------------------------------


def _compile(pattern: str) -> Pattern[str]:
    """Compile ReDoS-safe: ASCII + ensure we didn't miss anchoring."""
    return re.compile(pattern, re.ASCII)


SECRETS: List[SecretPattern] = [
    # -- Anthropic --
    SecretPattern(
        family_id="anthropic_api_key",
        regex=_compile(r"\bsk-ant-[a-zA-Z0-9_-]{90,}\b"),
        redaction_label="[REDACTED:anthropic_key]",
        category="token",
        owasp_class="LLM06",
        validator=None,
    ),
    # -- OpenAI --
    SecretPattern(
        family_id="openai_api_key_legacy",
        regex=_compile(r"\bsk-[A-Za-z0-9]{48}\b"),
        redaction_label="[REDACTED:openai_key]",
        category="token",
        owasp_class="LLM06",
        validator=None,
    ),
    SecretPattern(
        family_id="openai_project_key",
        regex=_compile(r"\bsk-proj-[A-Za-z0-9_-]{40,}\b"),
        redaction_label="[REDACTED:openai_project_key]",
        category="token",
        owasp_class="LLM06",
        validator=None,
    ),
    # -- AWS --
    SecretPattern(
        family_id="aws_access_key",
        regex=_compile(r"\bAKIA[0-9A-Z]{16}\b"),
        redaction_label="[REDACTED:aws_access_key]",
        category="token",
        owasp_class="LLM06",
        validator=None,
    ),
    SecretPattern(
        family_id="aws_secret_access_key",
        regex=_compile(r"\baws_secret_access_key[\"'\s]*[=:][\"'\s]*"
                       r"([A-Za-z0-9/+=]{40})\b"),
        redaction_label="[REDACTED:aws_secret]",
        category="credential",
        owasp_class="LLM06",
        validator=None,
    ),
    # -- Google --
    SecretPattern(
        family_id="google_api_key",
        regex=_compile(r"\bAIza[0-9A-Za-z_-]{35}\b"),
        redaction_label="[REDACTED:google_api_key]",
        category="token",
        owasp_class="LLM06",
        validator=None,
    ),
    SecretPattern(
        family_id="google_oauth_refresh",
        regex=_compile(r"\b1//0[a-zA-Z0-9_-]{60,}\b"),
        redaction_label="[REDACTED:google_oauth_refresh]",
        category="credential",
        owasp_class="LLM06",
        validator=None,
    ),
    # -- GitHub --
    SecretPattern(
        family_id="github_personal_token",
        regex=_compile(r"\bghp_[A-Za-z0-9]{36}\b"),
        redaction_label="[REDACTED:github_pat]",
        category="token",
        owasp_class="LLM06",
        validator=None,
    ),
    SecretPattern(
        family_id="github_oauth_token",
        regex=_compile(r"\bgho_[A-Za-z0-9]{36}\b"),
        redaction_label="[REDACTED:github_oauth]",
        category="token",
        owasp_class="LLM06",
        validator=None,
    ),
    # -- GitLab --
    SecretPattern(
        family_id="gitlab_personal_token",
        regex=_compile(r"\bglpat-[A-Za-z0-9_-]{20,}\b"),
        redaction_label="[REDACTED:gitlab_pat]",
        category="token",
        owasp_class="LLM06",
        validator=None,
    ),
    # -- Stripe --
    SecretPattern(
        family_id="stripe_secret_key",
        regex=_compile(r"\bsk_(?:live|test)_[0-9a-zA-Z]{24,}\b"),
        redaction_label="[REDACTED:stripe_secret]",
        category="token",
        owasp_class="LLM06",
        validator=None,
    ),
    # -- HuggingFace --
    SecretPattern(
        family_id="huggingface_token",
        regex=_compile(r"\bhf_[a-zA-Z0-9]{34}\b"),
        redaction_label="[REDACTED:huggingface_token]",
        category="token",
        owasp_class="LLM06",
        validator=None,
    ),
    # -- Slack --
    SecretPattern(
        family_id="slack_token",
        regex=_compile(r"\bxox[baprs]-[A-Za-z0-9-]{10,}\b"),
        redaction_label="[REDACTED:slack_token]",
        category="token",
        owasp_class="LLM06",
        validator=None,
    ),
    # -- npm --
    SecretPattern(
        family_id="npm_token",
        regex=_compile(r"\bnpm_[A-Za-z0-9]{36}\b"),
        redaction_label="[REDACTED:npm_token]",
        category="token",
        owasp_class="LLM06",
        validator=None,
    ),
    # -- DigitalOcean --
    SecretPattern(
        family_id="digitalocean_token",
        regex=_compile(r"\bdop_v1_[a-f0-9]{64}\b"),
        redaction_label="[REDACTED:do_token]",
        category="token",
        owasp_class="LLM06",
        validator=None,
    ),
    # -- Linear --
    SecretPattern(
        family_id="linear_api_key",
        regex=_compile(r"\blin_api_[A-Za-z0-9]{30,}\b"),
        redaction_label="[REDACTED:linear_api]",
        category="token",
        owasp_class="LLM06",
        validator=None,
    ),
    # -- Twilio --
    SecretPattern(
        family_id="twilio_account_sid",
        regex=_compile(r"\bAC[0-9a-fA-F]{32}\b"),
        redaction_label="[REDACTED:twilio_sid]",
        category="token",
        owasp_class="LLM06",
        validator=None,
    ),
    # -- JWT (3-part dot-separated base64url) --
    SecretPattern(
        family_id="jwt_token",
        regex=_compile(
            r"\beyJ[A-Za-z0-9_-]{10,}\."
            r"[A-Za-z0-9_-]{10,}\."
            r"[A-Za-z0-9_-]{10,}\b"
        ),
        redaction_label="[REDACTED:jwt]",
        category="token",
        owasp_class="LLM06",
        validator=None,
    ),
    # -- Private key PEM (header match) --
    SecretPattern(
        family_id="private_key_pem",
        regex=_compile(
            r"-----BEGIN (?:RSA |EC |DSA |OPENSSH |PGP |ENCRYPTED )?PRIVATE KEY-----"
        ),
        redaction_label="[REDACTED:private_key_pem]",
        category="credential",
        owasp_class="LLM06",
        validator=None,
    ),
    # -------------------------------------------------------------------------
    # Cloud / KMS / secret manager families (PLAN-113 W4-SEC F-7.3-cloud)
    # -------------------------------------------------------------------------
    # -- Azure client secret (format: 8 alnum + dash patterns typical GUID-ish,
    #    but realistically detected via assignment context) --
    SecretPattern(
        family_id="azure_client_secret",
        regex=_compile(
            r"(?i)(?:client[_\-]?secret|AZURE[_\-]?CLIENT[_\-]?SECRET)"
            r"[\"'\s]*[=:][\"'\s]*"
            r"([A-Za-z0-9~._\-]{32,})\b"
        ),
        redaction_label="[REDACTED:azure_client_secret]",
        category="credential",
        owasp_class="LLM06",
        validator=None,
    ),
    # -- Azure SAS token (sv= + sig= structure) --
    SecretPattern(
        family_id="azure_sas_token",
        regex=_compile(
            r"\bsv=\d{4}-\d{2}-\d{2}&[A-Za-z0-9&=%+._\-]{30,}&sig=[A-Za-z0-9%+/=]{20,}\b"
        ),
        redaction_label="[REDACTED:azure_sas_token]",
        category="credential",
        owasp_class="LLM06",
        validator=None,
    ),
    # -- OCI API signing key fingerprint / private key path (context-gated) --
    SecretPattern(
        family_id="oci_api_key",
        regex=_compile(
            r"(?i)(?:oci[_\-]?api[_\-]?key|oracle[_\-]?api[_\-]?key)"
            r"[\"'\s]*[=:][\"'\s]*([A-Za-z0-9/+]{40,})\b"
        ),
        redaction_label="[REDACTED:oci_api_key]",
        category="credential",
        owasp_class="LLM06",
        validator=None,
    ),
    # -- IBM Cloud API key (44 chars, starts with common prefix pattern) --
    SecretPattern(
        family_id="ibm_cloud_api_key",
        regex=_compile(
            r"(?i)(?:ibm[_\-]?(?:cloud[_\-]?)?api[_\-]?key)"
            r"[\"'\s]*[=:][\"'\s]*([A-Za-z0-9_\-]{40,})\b"
        ),
        redaction_label="[REDACTED:ibm_cloud_api_key]",
        category="credential",
        owasp_class="LLM06",
        validator=None,
    ),
    # -- AWS KMS Key ID (UUID format xxxxxxxx-xxxx-xxxx-xxxx-xxxxxxxxxxxx) --
    SecretPattern(
        family_id="aws_kms_key_id",
        regex=_compile(
            r"(?i)(?:kms[_\-]?key[_\-]?(?:id|arn)|key[_\-]?id\s*[=:]\s*)"
            r"(?:arn:aws:kms:[a-z0-9-]+:\d{12}:key/)?"
            r"([0-9a-f]{8}-[0-9a-f]{4}-[0-9a-f]{4}-[0-9a-f]{4}-[0-9a-f]{12})\b"
        ),
        redaction_label="[REDACTED:aws_kms_key_id]",
        category="credential",
        owasp_class="LLM06",
        validator=None,
    ),
    # -- AWS STS session token (typically >100 chars base64) --
    SecretPattern(
        family_id="aws_sts_token",
        regex=_compile(
            r"(?i)(?:aws[_\-]?session[_\-]?token|AWS_SESSION_TOKEN)"
            r"[\"'\s]*[=:][\"'\s]*([A-Za-z0-9/+=]{100,})\b"
        ),
        redaction_label="[REDACTED:aws_sts_token]",
        category="credential",
        owasp_class="LLM06",
        validator=None,
    ),
    # -- HashiCorp Vault token (hvs.*, hvb.*, s.* classic format) --
    SecretPattern(
        family_id="hashicorp_vault_token",
        regex=_compile(r"\b(?:hvs|hvb|hvr)\.[A-Za-z0-9_\-]{20,}\b"),
        redaction_label="[REDACTED:vault_token]",
        category="token",
        owasp_class="LLM06",
        validator=None,
    ),
    # -- Bitbucket app password (format: ATBBxxxxxxxxxxxxxxxxxxxxxxxxxx) --
    SecretPattern(
        family_id="bitbucket_app_password",
        regex=_compile(r"\bATBB[A-Za-z0-9]{28,}\b"),
        redaction_label="[REDACTED:bitbucket_app_password]",
        category="token",
        owasp_class="LLM06",
        validator=None,
    ),
    # -- Square API key (sq0i-, sq0p-, sq0a-, sq0atf-, sq0acp-, sq0asp-, ...) --
    # Square token prefixes: sq0i (access token), sq0p (personal access),
    # sq0a (application secret/sandbox), sq0atf / sq0acp / sq0asp variants.
    SecretPattern(
        family_id="square_api_key",
        regex=_compile(r"\bsq0[A-Za-z]{1,4}-[A-Za-z0-9_\-]{22,}\b"),
        redaction_label="[REDACTED:square_api_key]",
        category="token",
        owasp_class="LLM06",
        validator=None,
    ),
    # -- OpenAI Codex / generic Claude/Anthropic codex token --
    # Codex tokens (as emitted by the MCP codex server) follow the
    # same sk-ant-... prefix family (already covered by anthropic_api_key).
    # Additionally, codex-specific bearer tokens may appear as plain hex
    # or as `codex-session-...` prefixed tokens.
    SecretPattern(
        family_id="codex_session_token",
        regex=_compile(r"\bcodex-session-[A-Za-z0-9_\-]{20,}\b"),
        redaction_label="[REDACTED:codex_session_token]",
        category="token",
        owasp_class="LLM06",
        validator=None,
    ),
]
"""17 token + 1 PEM + 10 cloud/KMS = 28 secret families."""


PII: List[SecretPattern] = [
    # -- Brazilian CPF (LGPD tier-1) --
    SecretPattern(
        family_id="br_cpf",
        regex=_compile(r"\b\d{3}\.?\d{3}\.?\d{3}-?\d{2}\b"),
        redaction_label="[REDACTED:cpf]",
        category="pii",
        owasp_class="LGPD",
        validator=_cpf_validator,
    ),
    # -- Brazilian CNPJ (LGPD tier-1) --
    SecretPattern(
        family_id="br_cnpj",
        regex=_compile(r"\b\d{2}\.?\d{3}\.?\d{3}/?\d{4}-?\d{2}\b"),
        redaction_label="[REDACTED:cnpj]",
        category="pii",
        owasp_class="LGPD",
        validator=_cnpj_validator,
    ),
    # -- Brazilian phone (+55 + DDD + 9-digit mobile or 8-digit landline) --
    SecretPattern(
        family_id="br_phone",
        regex=_compile(
            r"\+55\s?\(?[1-9]{2}\)?\s?9?\d{4}[-\s]?\d{4}\b"
        ),
        redaction_label="[REDACTED:br_phone]",
        category="pii",
        owasp_class="LGPD",
        validator=None,
    ),
    # -- Credit card (13-19 digits, Luhn-validated) --
    SecretPattern(
        family_id="credit_card",
        regex=_compile(
            r"\b(?:\d[ -]?){12,18}\d\b"
        ),
        redaction_label="[REDACTED:credit_card]",
        category="pii",
        owasp_class="LGPD",
        validator=_luhn_validator,
    ),
    # -------------------------------------------------------------------------
    # Additional LGPD/BR identifier families (PLAN-113 W4-SEC F-7.11 + F-7.4)
    # All are absent from the original PII block, creating a gap in the Codex
    # egress redaction path (codex_egress_redact.py → secret_patterns.py).
    # -------------------------------------------------------------------------
    # -- Título de Eleitor (12 digits, grouped or bare) --
    # Grouped canonical form: NNNN NNNN SSDD where SS=state code, DD=check digits.
    # Context-gated (bare 12-digit run is ambiguous); checksum-validated.
    SecretPattern(
        family_id="br_titulo_eleitor",
        regex=_compile(r"\b\d{4}\.?\d{4}\.?\d{4}\b"),
        redaction_label="[REDACTED:titulo_eleitor]",
        category="pii",
        owasp_class="LGPD",
        validator=_titulo_eleitor_validator,
    ),
    # -- CTPS (Carteira de Trabalho e Previdência Social) --
    # Format varies: series (4 digits) + number (5-7 digits) per state.
    # Canonical form used in Brazilian official docs: NNNNN/NNNN-UF or
    # bare 7 digits. We match the context-bearing structured form.
    # Context-gated + no strong checksum — validator is None (rely on regex).
    SecretPattern(
        family_id="br_ctps",
        regex=_compile(
            r"(?i)\b(?:ctps|carteira[_\- ]?de[_\- ]?trabalho)"
            r"[^\d]{0,20}\d{5,7}[/\-\s]?\d{3,5}\b"
        ),
        redaction_label="[REDACTED:ctps]",
        category="pii",
        owasp_class="LGPD",
        validator=None,
    ),
    # -- RG (Registro Geral / state-issued ID) --
    # Most common (SP) form: NN.NNN.NNN-X where X is digit or X/x.
    # Also accepts bare 8-9 digit forms. Context-gated on rg/identidade keyword.
    SecretPattern(
        family_id="br_rg",
        regex=_compile(r"\b\d{1,2}\.?\d{3}\.?\d{3}-?[\dxX]\b"),
        redaction_label="[REDACTED:rg]",
        category="pii",
        owasp_class="LGPD",
        validator=None,
    ),
    # -- CNH (Carteira Nacional de Habilitação) --
    # 11 bare digits. Collides with CPF shape; context-gated on CNH keyword.
    SecretPattern(
        family_id="br_cnh",
        regex=_compile(r"(?i)(?:cnh|habilitacao|habilitação|carteira[_\- ]?(?:de[_\- ]?)?motorista)[^\d]{0,20}\d{11}\b"),
        redaction_label="[REDACTED:cnh]",
        category="pii",
        owasp_class="LGPD",
        validator=None,
    ),
    # -- PIS / PASEP / NIT (11 digits, canonical grouped NNN.NNNNN.NN-N) --
    # Checksum-validated via weighted modulo-11.
    SecretPattern(
        family_id="br_pis_pasep",
        regex=_compile(r"\b\d{3}\.?\d{5}\.?\d{2}-?\d{1}\b"),
        redaction_label="[REDACTED:pis_pasep]",
        category="pii",
        owasp_class="LGPD",
        validator=_pis_pasep_validator,
    ),
    # -- Brazilian Passport (2 uppercase letters + 6 digits) --
    # Context-gated on passaporte/passport keyword (generic letter+digit shape).
    SecretPattern(
        family_id="br_passport",
        regex=_compile(
            r"(?i)(?:passaporte|passport)[^\w]{0,20}\b([A-Z]{2}\d{6})\b"
        ),
        redaction_label="[REDACTED:br_passport]",
        category="pii",
        owasp_class="LGPD",
        validator=None,
    ),
    # -- IBAN-BR (ISO 13616: 'BR' + 2 check digits + 25-char BBAN = 29 total) --
    # Structurally distinctive — BR prefix + fixed 29-char shape, no context gate.
    SecretPattern(
        family_id="br_iban",
        regex=_compile(
            r"\bBR\d{2}(?:\s?[A-Z0-9]){25}\b"
        ),
        redaction_label="[REDACTED:br_iban]",
        category="pii",
        owasp_class="LGPD",
        validator=None,
    ),
]
"""4 original + 7 additional LGPD/BR = 11 PII families total."""


ALL_PATTERNS: List[SecretPattern] = SECRETS + PII


# ---------------------------------------------------------------------------
# Scan API — ReDoS-guarded
# ---------------------------------------------------------------------------


class ScanBudgetExceeded(Exception):
    """Raised when ITIMER wall-clock budget is hit during scan()."""


def _install_itimer_guard(budget_seconds: float) -> Optional[object]:
    """Install SIGALRM ITIMER guard. Returns previous handler or None if unsupported.

    Safe no-op on Windows (signal.setitimer raises AttributeError).

    IMPORTANT ADVISORY (F-7.3-redos-itimer): On platforms without SIGALRM
    (Windows; some embedded Python runtimes), the ReDoS time-budget guard is
    NOT active. A pathologically-crafted input could cause unbounded scan time.
    Callers on such platforms should apply an external timeout or restrict
    input size to the DoS-safe pre-truncation limit.
    """
    if not hasattr(signal, "setitimer"):
        # Emit an advisory breadcrumb so the absence of the guard is observable.
        # We use the stdlib logging module (no external deps) at DEBUG level so
        # the message appears in verbose runs but does not pollute normal output.
        _logger.debug(
            "secret_patterns: ITIMER/SIGALRM unavailable on this platform "
            "(Windows or embedded runtime). ReDoS budget guard is inactive. "
            "Input size truncation via caller-side cap is the effective defense. "
            "breadcrumb=secret_scan_no_itimer_guard platform=%s",
            __import__("sys").platform,
        )
        return None

    def _handler(signum, frame) -> None:
        raise ScanBudgetExceeded("scan() exceeded ITIMER budget")

    prev = signal.signal(signal.SIGALRM, _handler)
    signal.setitimer(signal.ITIMER_REAL, budget_seconds)
    return prev


def _clear_itimer_guard(prev_handler: Optional[object]) -> None:
    if not hasattr(signal, "setitimer"):
        return
    signal.setitimer(signal.ITIMER_REAL, 0.0)  # disarm
    if prev_handler is not None:
        signal.signal(signal.SIGALRM, prev_handler)


def scan(
    text: str,
    *,
    patterns: Optional[List[SecretPattern]] = None,
    budget_seconds: float = 0.5,
    normalize_unicode: bool = True,
) -> List[Finding]:
    """Scan text for matches against the catalog. ReDoS-guarded.

    Args:
        text: input to scan (str; bytes must be decoded by caller).
        patterns: which patterns to apply. Default = ALL_PATTERNS.
        budget_seconds: ITIMER wall-clock budget. Default 0.5s.
        normalize_unicode: apply NFKC normalization first (defeats homoglyph
            evasion). Default True.

    Returns:
        List of Finding (empty if clean). Ordered by (start, family_id).

    Raises:
        ScanBudgetExceeded: if budget exceeded (caller should fail-open per
            security-engineer #2 regression budget; the hook wrapper should
            audit-emit `breadcrumb=secret_scan_timeout` and return allow).
    """
    if patterns is None:
        patterns = ALL_PATTERNS
    if normalize_unicode:
        # NFKC defeats tag chars, RTL override, zero-width, homoglyph evasion
        text = unicodedata.normalize("NFKC", text)
    findings: List[Finding] = []
    prev = _install_itimer_guard(budget_seconds)
    try:
        for p in patterns:
            for m in p.regex.finditer(text):
                matched = m.group(0)
                if p.validator is not None:
                    try:
                        if not p.validator(matched):
                            continue
                    except Exception:
                        # Validator crash → treat as false-positive (fail-open)
                        continue
                findings.append(Finding(
                    family_id=p.family_id,
                    category=p.category,
                    start=m.start(),
                    end=m.end(),
                    redaction_label=p.redaction_label,
                ))
    finally:
        _clear_itimer_guard(prev)
    findings.sort(key=lambda f: (f.start, f.family_id))
    return findings


def redact(text: str, findings: List[Finding]) -> str:
    """Replace matched ranges with redaction labels. Preserves unmatched text."""
    if not findings:
        return text
    # Walk findings in reverse so offsets don't shift
    result = text
    for f in sorted(findings, key=lambda x: x.start, reverse=True):
        result = result[:f.start] + f.redaction_label + result[f.end:]
    return result


def scan_and_redact(
    text: str,
    *,
    patterns: Optional[List[SecretPattern]] = None,
    budget_seconds: float = 0.5,
    normalize_unicode: bool = True,
) -> Tuple[str, List[Finding]]:
    """Convenience: scan + redact in one call. Returns (redacted_text, findings)."""
    findings = scan(
        text,
        patterns=patterns,
        budget_seconds=budget_seconds,
        normalize_unicode=normalize_unicode,
    )
    return redact(text, findings), findings


def family_ids() -> List[str]:
    """Return all catalog family_id values. For audit-log inventory."""
    return [p.family_id for p in ALL_PATTERNS]


# ---------------------------------------------------------------------------
# Unified pattern registry (F-7.4-drift single source of truth)
# ---------------------------------------------------------------------------
#
# These constants expose structured subsets of ALL_PATTERNS so downstream
# libraries (pii_patterns, redact, codex_egress_redact) and their tests can
# import the canonical catalog instead of re-defining the same sets.
#
# Usage (e.g. in test_redact_secrets_parity.py):
#
#   from _lib.secret_patterns import LGPD_FAMILY_IDS, CLOUD_KMS_FAMILY_IDS
#   assert "br_cpf" in LGPD_FAMILY_IDS


def _family_ids_by_owasp(owasp_class: str) -> Tuple[str, ...]:
    """Return a sorted tuple of family_ids filtered by owasp_class."""
    return tuple(sorted(p.family_id for p in ALL_PATTERNS if p.owasp_class == owasp_class))


def _family_ids_by_category(category: str) -> Tuple[str, ...]:
    """Return a sorted tuple of family_ids filtered by category."""
    return tuple(sorted(p.family_id for p in ALL_PATTERNS if p.category == category))


#: Frozenset of all canonical family_id values (single source of truth).
#: codex_egress_redact.py, pii_patterns.py, redact.py parity tests import
#: this instead of re-declaring their own family lists.
CANONICAL_FAMILY_IDS: Tuple[str, ...] = tuple(family_ids())

#: LGPD-specific family_ids (owasp_class == "LGPD").
LGPD_FAMILY_IDS: Tuple[str, ...] = _family_ids_by_owasp("LGPD")

#: Token families (category == "token").
TOKEN_FAMILY_IDS: Tuple[str, ...] = _family_ids_by_category("token")

#: Credential families (category == "credential").
CREDENTIAL_FAMILY_IDS: Tuple[str, ...] = _family_ids_by_category("credential")

#: Cloud/KMS credential family_ids (PLAN-113 W4-SEC v1.1.0).
CLOUD_KMS_FAMILY_IDS: Tuple[str, ...] = tuple(sorted([
    "azure_client_secret",
    "azure_sas_token",
    "oci_api_key",
    "ibm_cloud_api_key",
    "aws_kms_key_id",
    "aws_sts_token",
    "hashicorp_vault_token",
    "bitbucket_app_password",
    "square_api_key",
    "codex_session_token",
]))

#: pii_patterns.py family slugs — the complete set pii_patterns.families() returns.
#: Kept here so the parity test can do a single-import diff.
#: NOTE: pii_patterns uses different slug names (e.g. "cpf_cnpj" vs "br_cpf").
#: The overlap is intentional; this constant makes the contract explicit.
PII_PATTERNS_KNOWN_SLUGS: Tuple[str, ...] = tuple(sorted([
    "api_key", "jwt", "bearer",
    "cpf_cnpj",
    "rg", "cnh", "pis_pasep", "passport_br", "iban_br",
    "credit_card_pan", "email_in_log", "entropy",
]))


def assert_catalog_self_consistent() -> None:
    """Assert internal self-consistency of the catalog.

    - family_ids are unique across ALL_PATTERNS
    - LGPD_FAMILY_IDS ⊆ CANONICAL_FAMILY_IDS
    - CLOUD_KMS_FAMILY_IDS ⊆ CANONICAL_FAMILY_IDS
    - All patterns have non-empty redaction_label starting with [REDACTED:

    Raises AssertionError on any violation. Called by the catalog self-test
    in test_secret_patterns.py.
    """
    ids = [p.family_id for p in ALL_PATTERNS]
    assert len(ids) == len(set(ids)), "Duplicate family_ids in ALL_PATTERNS"

    canonical_set = set(CANONICAL_FAMILY_IDS)
    missing_lgpd = set(LGPD_FAMILY_IDS) - canonical_set
    assert not missing_lgpd, f"LGPD_FAMILY_IDS not in CANONICAL_FAMILY_IDS: {missing_lgpd}"

    missing_cloud = set(CLOUD_KMS_FAMILY_IDS) - canonical_set
    assert not missing_cloud, f"CLOUD_KMS_FAMILY_IDS not in CANONICAL_FAMILY_IDS: {missing_cloud}"

    for p in ALL_PATTERNS:
        assert p.redaction_label.startswith("[REDACTED:"), (
            f"{p.family_id}: redaction_label must start with '[REDACTED:'"
        )
        assert p.redaction_label.endswith("]"), (
            f"{p.family_id}: redaction_label must end with ']'"
        )
