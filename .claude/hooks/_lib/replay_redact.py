"""replay_redact_lib — PII redaction + HMAC salt rebind for replay capture.

PLAN-069 Phase 1 production. Wraps `pii_patterns.SCANNER_PIPELINE(mode='redact')`
plus a thin OS-username preprocessor (Phase 0.5 PoC surfaced Class A
`/Users/<NAME>/` paths leak through SCANNER_PIPELINE because pii_patterns
has no `os_path` family — see REPRODUCER-NOTES §5).

This file is intentionally placed under `.claude/scripts/replay/` (non-
canonical) for Wave A staging; it MOVES to `.claude/hooks/_lib/replay_redact.py`
in the Owner GPG ceremony (Wave D) per Round 1 condition #1.

## Round 1 lift conditions (PLAN-069 debate/round-1/security-engineer.md)

This module wires the following:

1. `redact_event(event, ...)` walks every string leaf via `SCANNER_PIPELINE`
   plus `_strip_os_username` preprocessor. Fail-CLOSED on pipeline exception
   (raises `RedactionFailure`).
2. CLI parses single literal `enforced` only — handled by caller in
   replay-session.py argparse choices.
3. Per-fixture HMAC-SHA256 salt rebind: `os.urandom(32)` nonce stored in
   fixture `_meta.salt_b64`. Formula: `HMAC(nonce, field_name || 0x1F || value)`.
   Truncated to 16 hex chars to match `canonical_payload_hash`.
4. Adversarial fixture corpus: tests live at
   `.claude/scripts/replay/tests/fixtures/` — populated in Wave B by QA.
5. `replay_capture_started` / `replay_capture_completed` actions: registered
   in `audit_emit._KNOWN_ACTIONS` during Wave D (canonical ceremony).
6. Trust boundary: `verify_fixture_meta()` enforces salt-nonce presence,
   schema-version-not-newer, and post-load `pii_patterns.scan(mode='flag')`
   defense-in-depth.

## Stdlib-only

Imports: `base64`, `hashlib`, `hmac`, `json`, `os`, `re`, `secrets`, `sys`,
`unicodedata`, plus the framework's own `pii_patterns` (read but not modified).
"""

from __future__ import annotations

import base64
import hashlib
import hmac
import json
import os
import re
import secrets
import sys
import unicodedata
from dataclasses import dataclass, field
from pathlib import Path
from typing import Any, Dict, List, Optional, Tuple


# ---------------------------------------------------------------------------
# Path bootstrap for pii_patterns import (match replay-session.py pattern)
# ---------------------------------------------------------------------------

_SCRIPT_DIR = Path(__file__).resolve().parent
_HOOKS_DIR = _SCRIPT_DIR.parent.parent / "hooks"
if str(_HOOKS_DIR) not in sys.path:
    sys.path.insert(0, str(_HOOKS_DIR))

from _lib import pii_patterns  # noqa: E402


# ---------------------------------------------------------------------------
# Versioning. Two fields per Phase 0.5 §6 disposition (forward-drift defense):
#   - PII_PATTERNS_VERSION mirrors the upstream library version
#   - REPLAY_REDACT_VERSION is this wrapper's contract version
# ---------------------------------------------------------------------------

PII_PATTERNS_VERSION = "1.0.0"
REPLAY_REDACT_VERSION = "1.0.0"

# Schema version — bump on breaking changes to fixture _meta layout.
FIXTURE_SCHEMA = "v2.16"

# Salt-nonce length (bytes); HMAC-SHA256 truncated to 16 hex chars.
_SALT_NONCE_BYTES = 32
_HMAC_TRUNCATE_HEX = 16

# Field-binding separator — ASCII Unit Separator U+001F. Never appears in
# JSON values, so `field || 0x1F || value` is unambiguous.
_FIELD_BINDING_SEP = b"\x1f"


# ---------------------------------------------------------------------------
# OS-username preprocessor — Phase 0.5 finding: pii_patterns has no
# `os_path` family. This thin preprocessor strips usernames from common
# OS path layouts BEFORE handing strings to SCANNER_PIPELINE.
# ---------------------------------------------------------------------------

# POSIX/macOS user homes
_RE_POSIX_USERS = re.compile(r"/Users/[A-Za-z][A-Za-z0-9._\-]+/")
# Linux user homes
_RE_LINUX_HOME = re.compile(r"/home/[A-Za-z_][A-Za-z0-9._\-]*/")
# macOS scratch / sandbox / launch agents
_RE_MACOS_SCRATCH = re.compile(
    r"/private/var/folders/[A-Za-z0-9._/+\-]+"
)
# Windows user homes (both backslash and forward-slash variants)
_RE_WIN_USERS_BACKSLASH = re.compile(
    r"[A-Za-z]:\\Users\\[A-Za-z][A-Za-z0-9._\-]+\\"
)
_RE_WIN_USERS_FORWARDSLASH = re.compile(
    r"[A-Za-z]:/Users/[A-Za-z][A-Za-z0-9._\-]+/"
)
# macOS network volumes
_RE_VOLUMES = re.compile(r"/Volumes/[A-Za-z0-9._\-]+/")


def _strip_os_username(text: str) -> str:
    """Replace OS-user paths with `[REDACTED:OS_PATH]` token.

    Runs BEFORE SCANNER_PIPELINE because pii_patterns has no `os_path`
    family (Phase 0.5 PoC §3 confirmed: Class A leaks 10/10 in Pass 2).
    Token shape mirrors `pii_patterns._apply_redactions` for consumer
    consistency.

    Wave B QA finding (P1-A): NFKC normalization MUST run before regex
    so full-width ／Ｕｓｅｒｓ／ doesn't bypass `/Users/`. SCANNER_PIPELINE
    re-NFKCs internally so this preprocessor's normalization is local
    only — original `text` parameter is not mutated.
    """
    if not text:
        return text
    s = unicodedata.normalize("NFKC", text)
    s = _RE_POSIX_USERS.sub("[REDACTED:OS_PATH]/", s)
    s = _RE_LINUX_HOME.sub("[REDACTED:OS_PATH]/", s)
    s = _RE_MACOS_SCRATCH.sub("[REDACTED:OS_PATH]", s)
    s = _RE_WIN_USERS_BACKSLASH.sub("[REDACTED:OS_PATH]\\\\", s)
    s = _RE_WIN_USERS_FORWARDSLASH.sub("[REDACTED:OS_PATH]/", s)
    s = _RE_VOLUMES.sub("[REDACTED:OS_PATH]/", s)
    return s


# ---------------------------------------------------------------------------
# Fail-CLOSED exception (Round 1 condition #1)
# ---------------------------------------------------------------------------


class RedactionFailure(Exception):
    """Raised when the pipeline fails in any unrecoverable way.

    Caller (replay-session.py capture mode) MUST abort the capture and
    NOT write the fixture — fail-CLOSED on security surfaces per
    PROTOCOL.md and `audit_emit.py:184` precedent.
    """


# ---------------------------------------------------------------------------
# Per-fixture salt scaffolding (Round 1 condition #3)
# ---------------------------------------------------------------------------


def new_fixture_salt() -> bytes:
    """Generate a fresh 32-byte nonce. Consumer stores in `_meta.salt_b64`.

    Uses `secrets.token_bytes` (CSPRNG) per stdlib best practice. NEVER
    persisted outside the fixture; per-fixture scope drops the cross-corpus
    oracle from the per-installation `injection_salt.py` (Round 1 P0-SEC-03).
    """
    return secrets.token_bytes(_SALT_NONCE_BYTES)


def encode_salt(nonce: bytes) -> str:
    return base64.b64encode(nonce).decode("ascii")


def decode_salt(salt_b64: str) -> bytes:
    raw = base64.b64decode(salt_b64.encode("ascii"), validate=True)
    if len(raw) != _SALT_NONCE_BYTES:
        raise RedactionFailure(
            f"salt_b64 decoded to {len(raw)} bytes; expected {_SALT_NONCE_BYTES}"
        )
    return raw


def rebind_hash(field_name: str, original_value: str, nonce: bytes) -> str:
    """HMAC-SHA256 keyed-MAC over `field || 0x1F || value`, truncated.

    Defeats offline brute-force on the unsalted `desc_hash` cross-corpus
    oracle (Round 1 P0-SEC-03). Truncation is RFC 2104 §5 safe at 64 bits.
    Field-name binding prevents cross-field hash-confusion.
    """
    if not isinstance(original_value, str):
        original_value = "" if original_value is None else str(original_value)
    msg = field_name.encode("utf-8") + _FIELD_BINDING_SEP + original_value.encode(
        "utf-8", errors="replace"
    )
    digest = hmac.new(nonce, msg, hashlib.sha256).hexdigest()
    return digest[:_HMAC_TRUNCATE_HEX]


# Field names whose values MUST be rebound under the per-fixture nonce.
# Source: AUDIT-LOG-SCHEMA §93-98 + Round 1 P0-SEC-03.
_HASH_FIELDS_TO_REBIND = frozenset({
    "prompt_sha256",
    "desc_hash",
    "payload_hash",
})


# ---------------------------------------------------------------------------
# Core API — redact_text + redact_event
# ---------------------------------------------------------------------------


@dataclass
class RedactionStats:
    """Per-call diagnostic counts. Caller may emit as breadcrumb."""

    fields_redacted: int = 0
    fields_rebound: int = 0
    pipeline_calls: int = 0
    bytes_in: int = 0
    bytes_out: int = 0
    family_counts: Dict[str, int] = field(default_factory=dict)


def redact_text(
    text: str,
    stats: Optional[RedactionStats] = None,
) -> str:
    """Redact a single string via OS-username preprocess + SCANNER_PIPELINE.

    Fail-CLOSED — wraps `pii_patterns.scan()` in try/except; any exception
    re-raises as `RedactionFailure` (caller aborts the capture).
    """
    if text is None:
        return ""
    if not isinstance(text, str):
        text = str(text)
    if not text:
        return text

    if stats is not None:
        stats.bytes_in += len(text.encode("utf-8", errors="replace"))

    # Step 1 — strip OS-username paths (Phase 0.5 surprise).
    pre = _strip_os_username(text)

    # Step 2 — SCANNER_PIPELINE (NFKC + invisibles + base64 + entropy + regex).
    try:
        result = pii_patterns.scan(pre, mode="redact")
    except Exception as exc:  # noqa: BLE001
        raise RedactionFailure(
            f"pii_patterns.scan raised {type(exc).__name__}: {exc}"
        ) from exc

    redacted = result.redacted_text

    # Entropy redaction patch (Codex Session 81 P1#1 close):
    # `pii_patterns.scan(mode='redact')` excludes entropy hits from the
    # redacted-text rescan (pii_patterns.py:640-651) — entropy is high
    # false-positive in advisory mode. For capture-mode fixtures we want
    # stricter behavior because the fixture is committed regression data;
    # an unredacted high-entropy token is a real secret leak. Apply our
    # own entropy span replacement here, computed against the
    # post-regex-redacted text so spans line up. Idempotent: tokens
    # already redacted as `[REDACTED:FAMILY]` are short enough (<24 chars)
    # to escape entropy detection (threshold 24+ char tokens).
    if result.family_counts.get("entropy", 0) > 0:
        spans = pii_patterns._find_entropy_hits(redacted)
        for start, end, _token in sorted(spans, key=lambda s: s[0], reverse=True):
            redacted = redacted[:start] + "[REDACTED:ENTROPY]" + redacted[end:]

    if stats is not None:
        stats.pipeline_calls += 1
        if result.match_count > 0:
            stats.fields_redacted += 1
        for fam, count in result.family_counts.items():
            stats.family_counts[fam] = stats.family_counts.get(fam, 0) + count
        stats.bytes_out += len(redacted.encode("utf-8", errors="replace"))

    return redacted


def redact_event(
    event: Dict[str, Any],
    nonce: Optional[bytes] = None,
    stats: Optional[RedactionStats] = None,
) -> Dict[str, Any]:
    """Recursively redact every string leaf and rebind known hash fields.

    Args:
        event: arbitrary JSON dict (audit-log entry, spawn record, etc.).
        nonce: per-fixture salt (from `new_fixture_salt()`). When ``None``,
            hash-rebind is SKIPPED (used by R9 raw-write fix in dry_run /
            execute modes — those write per-run artifacts, not committed
            fixtures, so cross-corpus oracle does not apply). When provided,
            keys in ``_HASH_FIELDS_TO_REBIND`` are HMAC-rebound.
        stats: optional RedactionStats accumulator.

    Returns:
        New dict (event is NOT mutated). All string leaves passed through
        `redact_text`. With nonce: keys in `_HASH_FIELDS_TO_REBIND` are
        HMAC-rebound. Without nonce: those values are left as-is (still
        salt-hashed by `injection_salt.py`, so per-installation scope holds;
        only cross-corpus capture mode requires the nonce-rebind layer).
        Non-string scalars (int/float/bool/None) pass through unchanged.

    Raises:
        RedactionFailure on any pipeline exception (fail-CLOSED).
    """
    if not isinstance(event, dict):
        raise RedactionFailure(
            f"redact_event expects dict, got {type(event).__name__}"
        )
    if nonce is not None and len(nonce) != _SALT_NONCE_BYTES:
        raise RedactionFailure(
            f"nonce length {len(nonce)} != {_SALT_NONCE_BYTES}"
        )

    def _walk(obj: Any, key_hint: str = "") -> Any:
        if isinstance(obj, str):
            if nonce is not None and key_hint in _HASH_FIELDS_TO_REBIND:
                if stats is not None:
                    stats.fields_rebound += 1
                return rebind_hash(key_hint, obj, nonce)
            return redact_text(obj, stats=stats)
        if isinstance(obj, dict):
            return {k: _walk(v, key_hint=k) for k, v in obj.items()}
        if isinstance(obj, list):
            return [_walk(item, key_hint=key_hint) for item in obj]
        # int / float / bool / None pass through
        return obj

    return _walk(event)


# ---------------------------------------------------------------------------
# Fixture _meta builder + verifier (Round 1 condition #6)
# ---------------------------------------------------------------------------


def build_meta(
    nonce: bytes,
    captured_at_iso: str,
    plan_id: str,
    original_session_id: str,
    event_count: int,
    pre_meta_content_sha256: str = "",
) -> Dict[str, Any]:
    """Build the `_meta` dict written as the FIRST line of the fixture.

    `pre_meta_content_sha256` is the SHA-256 over the JSONL bytes of the
    redacted events (computed by the caller after writing them in order
    BUT before serializing _meta). Defeats P1-SEC-01 fixture forgery.
    """
    return {
        "_meta": True,
        "schema": FIXTURE_SCHEMA,
        "salt_b64": encode_salt(nonce),
        "pii_patterns_version": PII_PATTERNS_VERSION,
        "replay_redact_version": REPLAY_REDACT_VERSION,
        "captured_at": captured_at_iso,
        "plan_id": plan_id,
        "original_session_id": original_session_id,
        "event_count": event_count,
        "captured_by_hash": pre_meta_content_sha256,
    }


def _parse_schema(s: Any) -> Optional[Tuple[int, int]]:
    """Parse 'v<major>.<minor>' to (major, minor) tuple.

    Returns ``None`` on malformed input. Used by `verify_fixture_meta`
    for semantic comparison instead of lexicographic (Codex Session 81
    P1#2 close: ``v10.0`` < ``v2.16`` as strings, but ``10 > 2``
    numerically — the original `>` compare would silently accept
    fixtures from a future major schema).
    """
    if not isinstance(s, str) or not s.startswith("v"):
        return None
    try:
        parts = s[1:].split(".")
        if len(parts) != 2:
            return None
        return (int(parts[0]), int(parts[1]))
    except (ValueError, AttributeError):
        return None


def verify_fixture_meta(meta: Dict[str, Any]) -> Tuple[bool, str]:
    """Validate a fixture's `_meta` line against the trust boundary.

    Returns ``(ok, reason)``. ``ok=False`` MUST cause caller to abort
    fixture load — fail-CLOSED per Round 1 condition #6.
    """
    if not isinstance(meta, dict):
        return False, "meta is not a dict"
    if not meta.get("_meta"):
        return False, "missing or falsy _meta marker"
    schema = meta.get("schema")
    if not isinstance(schema, str):
        return False, "schema is not a string"
    # Codex Session 81 P1#2 close: semantic version compare, not lexicographic.
    schema_v = _parse_schema(schema)
    fixture_v = _parse_schema(FIXTURE_SCHEMA)
    if schema_v is None:
        return False, (
            f"schema {schema!r} unparseable (expected vMAJOR.MINOR)"
        )
    if fixture_v is None:
        return False, (
            f"FIXTURE_SCHEMA {FIXTURE_SCHEMA!r} unparseable (internal error)"
        )
    if schema_v > fixture_v:
        return False, (
            f"fixture schema {schema!r} newer than supported {FIXTURE_SCHEMA!r} "
            "(refuse — schema-version-not-newer invariant)"
        )
    salt_b64 = meta.get("salt_b64")
    if not isinstance(salt_b64, str) or not salt_b64:
        return False, "salt_b64 missing or empty"
    # Wave B QA finding (P1-B): malformed base64 raises `binascii.Error`,
    # not `RedactionFailure` — fail-CLOSED contract requires catching it
    # too. ValueError is included for defensive completeness.
    import binascii  # local import — only path that needs it
    try:
        nonce = decode_salt(salt_b64)
    except (RedactionFailure, binascii.Error, ValueError) as exc:
        return False, f"salt_b64 invalid: {exc}"
    if len(nonce) != _SALT_NONCE_BYTES:
        return False, f"salt nonce length {len(nonce)} != {_SALT_NONCE_BYTES}"
    pp_ver = meta.get("pii_patterns_version")
    if not isinstance(pp_ver, str) or not pp_ver:
        return False, "pii_patterns_version missing"
    rr_ver = meta.get("replay_redact_version")
    if not isinstance(rr_ver, str) or not rr_ver:
        return False, "replay_redact_version missing"
    if not isinstance(meta.get("event_count"), int):
        return False, "event_count missing or not an int"
    return True, "ok"


def post_load_defense_in_depth(
    event: Dict[str, Any],
) -> Tuple[bool, List[str]]:
    """Run `pii_patterns.scan(mode='flag')` over every string leaf.

    Returns ``(clean, leaks)`` where ``leaks`` is a list of family
    labels found post-load. Round 1 condition #6: defense-in-depth
    catches a tampered fixture that smuggled raw PII past producer-side
    redaction (e.g., a hand-edited `.jsonl` with re-injected secrets).
    """
    leaks: List[str] = []

    def _walk_flag(obj: Any) -> None:
        if isinstance(obj, str) and obj:
            try:
                result = pii_patterns.scan(obj, mode="flag")
            except Exception:  # noqa: BLE001
                # Defense-in-depth scan should never crash the loader;
                # if pipeline fails here we record a generic flag and move on.
                leaks.append("scan_error")
                return
            if result.match_count > 0:
                for fam in result.family_counts:
                    leaks.append(fam)
        elif isinstance(obj, dict):
            for v in obj.values():
                _walk_flag(v)
        elif isinstance(obj, list):
            for item in obj:
                _walk_flag(item)

    _walk_flag(event)
    return (not leaks), leaks


# ---------------------------------------------------------------------------
# Fixture write helpers (newline-delimited JSON, deterministic key order)
# ---------------------------------------------------------------------------


def serialize_event(event: Dict[str, Any]) -> str:
    """Serialize a redacted event for fixture write.

    Deterministic key order (sort_keys=True), no NaN/Inf, no escape on
    non-ASCII (ensure_ascii=False). Trailing newline is the caller's job.
    """
    return json.dumps(event, sort_keys=True, ensure_ascii=False)


def fixture_content_sha256(event_lines: List[str]) -> str:
    """SHA-256 over the concatenation of event lines (each ending in \\n).

    Used by `build_meta(pre_meta_content_sha256=...)` for `captured_by_hash`.
    """
    h = hashlib.sha256()
    for line in event_lines:
        h.update(line.encode("utf-8", errors="replace"))
        h.update(b"\n")
    return h.hexdigest()


# ---------------------------------------------------------------------------
# Module banner — verifies imports work end-to-end on `python -m` / direct.
# ---------------------------------------------------------------------------


if __name__ == "__main__":
    sys.stdout.write(
        "replay_redact_lib loaded; "
        f"pii_patterns_version={PII_PATTERNS_VERSION} "
        f"replay_redact_version={REPLAY_REDACT_VERSION} "
        f"fixture_schema={FIXTURE_SCHEMA} "
        f"families={pii_patterns.families()}\n"
    )
