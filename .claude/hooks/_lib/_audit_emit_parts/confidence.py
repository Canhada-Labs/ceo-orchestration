"""Confidence.

Internal declarations exported by the audit_emit compatibility facade.
"""

from __future__ import annotations

__all__ = ('_safe_claim_id_hash', '_safe_payload_hash', '_safe_verifier_outcome', '_CLAIM_EMITTED_ALLOWLIST', '_CONFIDENCE_GATE_VERDICT_ALLOWLIST', '_CONFIDENCE_GATE_VERDICTS', '_CLAIM_SEVERITIES', 'emit_claim_emitted', 'emit_confidence_gate_verdict', '_CONFIDENCE_GATE_BLOCKED_ALLOWLIST', '_CONFIDENCE_GATE_FP_DRIFT_DETECTED_ALLOWLIST', 'emit_confidence_gate_blocked', 'emit_confidence_gate_fp_drift_detected')

# -----------------------------------------------------------------------------
# PLAN-090-FOLLOWUP Wave A — claim producer pair (S138 R2 ACCEPT).
# Kernel-protected; registered via CEO_KERNEL_OVERRIDE=PLAN-090-FOLLOWUP-
# PRODUCER-PAIR + CEO_KERNEL_OVERRIDE_ACK=I-ACCEPT.
# Sec MF-3 caller-field deny-by-default per action.
# Raw claim bodies + verifier free-text NEVER persisted (LLM06 hold).
# -----------------------------------------------------------------------------

def _safe_claim_id_hash(raw: str) -> str:
    """Return collision-safe claim_id of form '<claim_type>:<12-hex>'.

    Accepts pre-formatted claim_id ('<type>:<12-hex>') ONLY if the
    prefix matches the KNOWN_KINDS grammar `^[a-z_]{1,32}$`; else
    rehashes raw via NFKC + sha256[:12] (Codex iter-1 P0-3 fold —
    prior version accepted ARBITRARY prefix, allowing a direct
    `emit_generic(claim_id="password=hunter2:deadbeefdead")` to
    persist the secret unchanged through the "defensive" path).

    Force `unknown:` prefix on rehash (no inheritance of caller
    prefix; mirrors `_persona_demand_safe_hash` strictness).
    """
    import hashlib
    import re
    import unicodedata
    s = str(raw or "").strip()
    _PREFIX_RE = re.compile(r"^[a-z_]{1,32}$")
    if ":" in s:
        prefix, _, suffix = s.partition(":")
        if (
            _PREFIX_RE.match(prefix)
            and len(suffix) == 12
            and all(c in "0123456789abcdef" for c in suffix.lower())
        ):
            return f"{prefix}:{suffix.lower()}"
    norm = unicodedata.normalize("NFKC", s)
    digest = hashlib.sha256(norm.encode("utf-8", errors="replace")).hexdigest()[:12]
    return f"unknown:{digest}"


def _safe_payload_hash(raw: str) -> str:
    """Return bare 12-hex payload_hash.

    Distinct from `_safe_claim_id_hash` (P0-4 fold): the `payload_hash`
    audit field is the bare digest with NO `<type>:` prefix, so a
    pre-hashed caller value of exactly 12-hex MUST round-trip unchanged
    (otherwise determinism breaks between call sites — producer in
    `confidence_gate.py:_format_json` and re-hash defense at
    `emit_generic`).
    """
    import hashlib
    import unicodedata
    s = str(raw or "").strip().lower()
    if len(s) == 12 and all(c in "0123456789abcdef" for c in s):
        return s
    norm = unicodedata.normalize("NFKC", s)
    return hashlib.sha256(norm.encode("utf-8", errors="replace")).hexdigest()[:12]


def _safe_verifier_outcome(raw: str, claim_args: str = "") -> str:
    """Return redacted + truncated verifier_outcome (security iter-1 P1-B fold).

    `r.detail` is verifier free-text output (e.g. `f"path {path} does
    not exist"` for path_exists verifier). It echoes `r.claim.args`
    fragments and can leak absolute paths, username, or claim payload
    via the free-text channel.

    Pipeline (defense-in-depth):
      1. PII redact via shipped `_lib.redact.redact_secrets` — fail-
         CLOSED to empty string if redactor not importable.
      2. Overlap scrub: any contiguous substring of length >=8 chars
         that also appears in `claim_args` is replaced with
         `<redacted>` (catches r.detail echoing r.claim.args).
      3. NFKC normalize + clip to 64 chars.
    """
    try:
        from _lib.redact import redact_secrets as _redact
        s = _redact(str(raw or ""))
    except Exception:
        # Fail-CLOSED on missing redactor.
        return ""
    ca = str(claim_args or "")
    if ca:
        for i in range(0, max(0, len(ca) - 8 + 1)):
            window = ca[i:i + 8]
            if window in s:
                s = s.replace(window, "<redacted>")
    import unicodedata
    return unicodedata.normalize("NFKC", s)[:64]


_CLAIM_EMITTED_ALLOWLIST = frozenset({
    "action", "ts", "session_id", "project", "event_schema",
    "tokens_in", "tokens_out", "tokens_total",
    "hmac", "hmac_error",
    "claim_id", "claim_type", "severity",
    "verifier_kind", "agent_name", "source",
    "line_num", "payload_hash",
    "kind_supported",
})


_CONFIDENCE_GATE_VERDICT_ALLOWLIST = frozenset({
    "action", "ts", "session_id", "project", "event_schema",
    "tokens_in", "tokens_out", "tokens_total",
    "hmac", "hmac_error",
    "claim_id", "verdict", "was_false_positive",
    "verifier_kind", "verifier_outcome",
    "agent_name", "source",
    "kind_supported",
})


# Closed enum for verdict. Per P1-1 fold: invalid values fall back to
# "fail" (non-inflammatory) NOT "refuted" — "refuted" is the FP signal
# in backfill line 134 and a parser sentinel must NOT pollute the FPR
# numerator.
_CONFIDENCE_GATE_VERDICTS = frozenset({"pass", "fail", "refuted"})


# Closed enum for severity (anchored to ADR-018 claim taxonomy).
_CLAIM_SEVERITIES = frozenset({"info", "warn", "critical"})


def emit_claim_emitted(
    claim_id: str,
    claim_type: str,
    severity: str,
    verifier_kind: str,
    payload_hash: str,
    kind_supported: bool,
    line_num: int = 0,
    agent_name: str = "",
    source: str = "",
    session_id: str = "",
    project: str = "",
) -> None:
    """Emit claim_emitted (PLAN-090-FOLLOWUP Wave A; S138 R2).

    Fired by check_confidence_gate.py once per CLAIM token the gate
    evaluates. payload_hash is sha256[:12] of NFKC-normalized claim
    body; raw claim text NEVER persisted (LLM06 hold).

    kind_supported is the boolean shipped as the extraction-FP signal
    (P0-1 fold). False means the CLAIM:<kind>:... token used a kind
    NOT in `confidence_gate.KNOWN_KINDS`; the gate cannot verify it
    and treats it as an extraction-level false-positive.

    Severity is the ADR-018 closed enum {info, warn, critical};
    invalid values dropped to 'info' (forensic-safe sentinel).
    """
    sev = str(severity)[:16]
    if sev not in _CLAIM_SEVERITIES:
        sev = "info"
    event: Dict[str, Any] = {
        "action": "claim_emitted",
        "claim_id": _safe_claim_id_hash(claim_id),
        "claim_type": str(claim_type)[:32],
        "severity": sev,
        "verifier_kind": str(verifier_kind)[:32],
        "payload_hash": _safe_payload_hash(payload_hash),
        "kind_supported": bool(kind_supported),
        "line_num": int(line_num),
        "agent_name": str(agent_name)[:64],
        "source": str(source)[:32],
        "session_id": session_id,
        "project": project,
    }
    _write_event(event)


def emit_confidence_gate_verdict(
    claim_id: str,
    verdict: str,
    was_false_positive: bool,
    kind_supported: bool,
    verifier_kind: str = "",
    verifier_outcome: str = "",
    agent_name: str = "",
    source: str = "",
    session_id: str = "",
    project: str = "",
) -> None:
    """Emit confidence_gate_verdict (PLAN-090-FOLLOWUP Wave A).

    Fired by check_confidence_gate.py AFTER claim_emitted, paired via
    claim_id.

    verdict is the closed enum {pass, fail, refuted}; invalid values
    dropped to 'fail' (P1-1 fold — NOT 'refuted', because backfill
    treats 'refuted' as an FP signal and a parser-sentinel must NOT
    pollute the FPR numerator).

    was_false_positive is the boolean PLAN-100 baseline analysis
    consumes (paired with claim_id to compute FPR per class). PLAN-090-
    FOLLOWUP shipping rule (P0-1 fold — no chicken-and-egg with PLAN-
    100 drift detector):

      was_false_positive = (NOT kind_supported)

    Caller is expected to derive this at the producer site
    (`confidence_gate._format_json`); the emit fn does not enforce
    the rule itself — only the emit signature carries both fields
    independently to allow future expansion when PLAN-100 Wave B.3
    drift detector emits additional verdicts with was_false_positive=True
    from cross-verifier disagreement.
    """
    v = str(verdict)[:16].lower()
    if v not in _CONFIDENCE_GATE_VERDICTS:
        v = "fail"
    event: Dict[str, Any] = {
        "action": "confidence_gate_verdict",
        "claim_id": _safe_claim_id_hash(claim_id),
        "verdict": v,
        "was_false_positive": bool(was_false_positive),
        "kind_supported": bool(kind_supported),
        "verifier_kind": str(verifier_kind)[:32],
        "verifier_outcome": _safe_verifier_outcome(verifier_outcome, ""),
        "agent_name": str(agent_name)[:64],
        "source": str(source)[:32],
        "session_id": session_id,
        "project": project,
    }
    _write_event(event)


# -----------------------------------------------------------------------------
# PLAN-100 Wave B — per-class block-mode (S139 R2 ACCEPT; ADR-019-AMEND-1).
# Kernel-protected; registered via CEO_KERNEL_OVERRIDE=PLAN-100-WAVE-B-
# AUDIT-EMIT-EXTENSION + CEO_KERNEL_OVERRIDE_ACK=I-ACCEPT.
# Sec MF-3 caller-field deny-by-default per action.
# -----------------------------------------------------------------------------

_CONFIDENCE_GATE_BLOCKED_ALLOWLIST = frozenset({
    "action",
    "ts",
    "session_id",
    "project",
    "agent_name",
    "source",
    "blocking_classes",   # list[str] of HIGH_CONFIDENCE_BLOCK kinds that fired
    "fail_count",         # int — total fail_count from gate payload
    "hmac",
    "hmac_error",
    "record_id",
    "tokens_in",
    "tokens_out",
    "tokens_total",
    "wall_ns",
    "pid",
    "spool_uuid",
    "ordinal_within_file",
    "_drain_sha256",
    "_drain_epoch",
    "event_schema",
})


_CONFIDENCE_GATE_FP_DRIFT_DETECTED_ALLOWLIST = frozenset({
    "action",
    "ts",
    "session_id",
    "project",
    "agent_name",
    "source",
    "drift_class",        # str — class with drift detected
    "window_days",        # int — rolling window (7 in v1.34.0)
    "fpr_bps",            # int — observed FPR in basis points
    "threshold_bps",      # int — drift threshold (200 = 2.0%)
    "sample_n",           # int — events in window
    "auto_demote_at",     # str ISO8601 — wall-clock when auto-demotion fires
    "hmac",
    "hmac_error",
    "record_id",
    "tokens_in",
    "tokens_out",
    "tokens_total",
    "wall_ns",
    "pid",
    "spool_uuid",
    "ordinal_within_file",
    "_drain_sha256",
    "_drain_epoch",
    "event_schema",
})


def emit_confidence_gate_blocked(
    blocking_classes,
    fail_count,
    agent_name: str = "",
    source: str = "",
    session_id: str = "",
    project: str = "",
) -> None:
    """Emit `confidence_gate_blocked` when ADR-019-AMEND-1 per-class
    block-mode fires. Caller fields scrubbed via
    `_CONFIDENCE_GATE_BLOCKED_ALLOWLIST`.

    `blocking_classes` is a list[str] of HIGH_CONFIDENCE_BLOCK kinds
    that fired (sorted/deduped by caller; defense-in-depth re-validation
    at emit_generic dispatch).
    """
    classes = []
    if isinstance(blocking_classes, (list, tuple)):
        for c in blocking_classes:
            if isinstance(c, str) and 0 < len(c) <= 64:
                classes.append(c)
    try:
        n_fail = int(fail_count)
    except (TypeError, ValueError):
        n_fail = 0
    event: Dict[str, Any] = {
        "action": "confidence_gate_blocked",
        "blocking_classes": classes,
        "fail_count": n_fail,
        "agent_name": str(agent_name)[:64],
        "source": str(source)[:32],
        "session_id": session_id,
        "project": project,
    }
    _write_event(event)


def emit_confidence_gate_fp_drift_detected(
    drift_class: str,
    window_days,
    fpr_bps,
    threshold_bps,
    sample_n,
    auto_demote_at: str,
    agent_name: str = "",
    source: str = "",
    session_id: str = "",
    project: str = "",
) -> None:
    """Emit `confidence_gate_fp_drift_detected` when drift detector
    observes 7d rolling FPR exceeding threshold for a
    HIGH_CONFIDENCE_BLOCK class. Per ADR-019-AMEND-1 §6.

    Fail-CLOSED on malformed numeric fields (no emit) to avoid
    polluting drift signal with garbage.
    """
    try:
        n_w = int(window_days)
        n_fpr = int(fpr_bps)
        n_thr = int(threshold_bps)
        n_s = int(sample_n)
    except (TypeError, ValueError):
        return
    event: Dict[str, Any] = {
        "action": "confidence_gate_fp_drift_detected",
        "drift_class": str(drift_class)[:64],
        "window_days": n_w,
        "fpr_bps": n_fpr,
        "threshold_bps": n_thr,
        "sample_n": n_s,
        "auto_demote_at": str(auto_demote_at)[:32],
        "agent_name": str(agent_name)[:64],
        "source": str(source)[:32],
        "session_id": session_id,
        "project": project,
    }
    _write_event(event)
