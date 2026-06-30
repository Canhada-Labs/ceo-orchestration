"""MCP auth primitives — HMAC bearer + ACL + CORS (ADR-042 §Auth).

Pure functions, stdlib-only. See ADR-042 §Auth.1-§Auth.6 for the
normative contract; SPEC/v1/mcp-server.schema.md §3 is the grep-able
field inventory.

Design contract:

- **Token format** ``v1.<client_id_hex16>.<nonce_hex16>.<hmac_hex32>`` —
  regex-validated BEFORE any HMAC compute (parse-malformed short-circuit).
- **HMAC compute** uses :func:`hmac.compare_digest` (constant-time).
  Deny messages are generic — no oracle that would distinguish
  "wrong secret" vs "wrong client_id" vs "malformed MAC".
- **Timestamp skew** ±60s vs wall clock. Caller provides ``now_ms``
  (tests inject deterministic values).
- **ACL** empty allowlist = refuse all. Wildcard ``"*"`` also refused
  (per ADR-042 §Auth.2 normative).
- **CORS** default-deny. Only exact-match origins in
  ``cors_origins`` array allowed.
- **Secret file** ``state/mcp_client_secrets/<client_id>.key`` with
  600 perms; loader returns ``None`` if missing or wrong perms,
  failing closed.
- **Fail-closed** on registry parse error (returns empty dict).
  Fail-closed on secret read error (returns ``None``). Fail-closed on
  anything we can't explicitly verify.

Token values MUST NEVER appear in any audit field, log line, or
exception message. This module's functions return booleans / dicts /
None — not the raw token or secret bytes.
"""

from __future__ import annotations

import hashlib
import hmac
import json
import os
import re
import sys
from pathlib import Path
from typing import Any, Dict, Optional


# Token format v1.<client_id_hex16>.<nonce_hex16>.<hmac_hex32>
# Each segment is [0-9a-f] (lowercase hex) — the canonical form.
# HMAC segment is 32 hex chars (128 bits — truncated SHA-256).
_TOKEN_RE = re.compile(
    r"^v1\.([0-9a-f]{16})\.([0-9a-f]{16})\.([0-9a-f]{32})$"
)

# Authorization header format — one or more spaces after "Bearer" per RFC 6750.
_BEARER_RE = re.compile(r"^Bearer\s+(\S.*)$", flags=re.IGNORECASE)

# Skew window in milliseconds (±60s per ADR-042 §Auth.1).
_SKEW_MS = 60_000


def parse_bearer(header: Optional[str]) -> Optional[str]:
    """Extract the raw token from an ``Authorization: Bearer <t>`` header.

    Returns None when the header is None, empty, not ``Bearer``-prefixed,
    or has no token after the scheme. The raw token (when returned) is
    NOT validated by this function — pass to :func:`parse_token` next.
    """
    if not header:
        return None
    m = _BEARER_RE.match(header.strip())
    if not m:
        return None
    tok = m.group(1).strip()
    return tok or None


def parse_token(raw: Optional[str]) -> Optional[Dict[str, str]]:
    """Split a raw bearer token into its three parts.

    Args:
        raw: the bearer token string, e.g.
            ``v1.aaaabbbbccccdddd.1111222233334444.<32-hex-chars>``.

    Returns:
        ``{"client_id": str, "nonce": str, "hmac": str}`` on success,
        or ``None`` on malformed input. Fail-closed: any deviation
        from the regex returns ``None`` without distinguishing why
        (no oracle).
    """
    if not raw:
        return None
    m = _TOKEN_RE.match(raw.strip())
    if not m:
        return None
    return {
        "client_id": m.group(1),
        "nonce": m.group(2),
        "hmac": m.group(3),
    }


def compute_hmac(
    client_id: str, nonce: str, timestamp_ms: int, secret: bytes
) -> str:
    """Compute the HMAC-SHA256 signature truncated to 32 hex chars.

    The body is ``client_id + nonce + str(timestamp_ms)`` (ASCII).
    Per ADR-042 §Auth.1 this is the canonical signing form; both sides
    MUST agree on integer string formatting (no float, no padding, no
    commas).
    """
    body = (client_id + nonce + str(int(timestamp_ms))).encode("ascii")
    mac = hmac.new(secret, body, hashlib.sha256).hexdigest()
    return mac[:32]


def verify_hmac(
    client_id: str,
    nonce: str,
    timestamp_ms: int,
    secret: bytes,
    candidate_hmac: str,
) -> bool:
    """Return True iff the candidate HMAC matches the computed one.

    Uses :func:`hmac.compare_digest` so timing cannot leak secret bits.
    Caller MUST check ``timestamp_ms`` skew separately via
    :func:`verify_timestamp_skew` — this function only verifies the
    MAC, not the freshness.
    """
    if not secret:
        return False
    if not candidate_hmac:
        return False
    expected = compute_hmac(client_id, nonce, timestamp_ms, secret)
    # hmac.compare_digest accepts str-vs-str or bytes-vs-bytes; we feed
    # lowercase hex strings of equal length.
    try:
        return hmac.compare_digest(expected, candidate_hmac.lower())
    except (TypeError, ValueError):
        return False


def verify_timestamp_skew(timestamp_ms: int, now_ms: int) -> bool:
    """Return True iff ``timestamp_ms`` is within ±60s of ``now_ms``.

    Both arguments are integer milliseconds since epoch. Callers inject
    ``now_ms`` from the server's clock (tests inject deterministic
    values).
    """
    try:
        delta = abs(int(timestamp_ms) - int(now_ms))
    except (TypeError, ValueError):
        return False
    return delta <= _SKEW_MS


def load_client_registry(settings_path: Path) -> Dict[str, Any]:
    """Load ``mcp_client_registry`` from ``.claude/settings.json``.

    Fail-closed: any IO error, JSON parse error, or missing top-level
    key returns ``{}`` (empty dict — every subsequent ACL lookup fails).
    Tolerates the ``_comment`` convention used elsewhere in settings.json.

    Returns:
        Dict keyed by ``client_id``. Each value is a dict per
        ADR-042 §Auth.2 with keys ``handlers`` (list[str]),
        ``cors_origins`` (list[str], optional), etc.
    """
    try:
        if not settings_path.is_file():
            return {}
        text = settings_path.read_text(encoding="utf-8")
        data = json.loads(text)
    except (OSError, json.JSONDecodeError, ValueError):
        return {}
    if not isinstance(data, dict):
        return {}
    registry = data.get("mcp_client_registry")
    if not isinstance(registry, dict):
        return {}
    # Filter to entries that are themselves dicts (ignore comment stubs).
    out: Dict[str, Any] = {}
    for k, v in registry.items():
        if isinstance(v, dict):
            out[str(k)] = v
    return out


def check_acl(registry_entry: Optional[Dict[str, Any]], handler_name: str) -> bool:
    """Return True iff the client ACL grants ``handler_name``.

    Rules (ADR-042 §Auth.2):
    - Missing / None registry entry → False.
    - Missing or empty ``handlers`` list → False (empty allowlist =
      refuse all).
    - Wildcard ``"*"`` in the list → False (no wildcard accepted).
    - Exact match on ``handler_name`` → True.

    Handler name comparison is case-sensitive and exact — no prefix
    matching, no glob.
    """
    if not isinstance(registry_entry, dict):
        return False
    handlers = registry_entry.get("handlers")
    if not isinstance(handlers, list) or not handlers:
        return False
    # No wildcard accepted — fail closed if the list contains one.
    for h in handlers:
        if not isinstance(h, str):
            return False
        if h == "*":
            return False
    return handler_name in handlers


def check_cors(
    registry_entry: Optional[Dict[str, Any]], origin: Optional[str]
) -> bool:
    """Return True iff CORS default-deny allows this origin.

    Rules (ADR-042 §Auth.4):
    - stdio path: ``origin is None`` AND no ``cors_origins`` key → True.
      (stdio has no web origin — CORS doesn't apply.)
    - HTTP with no Origin header: True if ``cors_origins`` is absent /
      empty, else False (explicit restriction wins).
    - HTTP with Origin header: True iff exact match in ``cors_origins``
      list. No wildcards. Case-sensitive (URI host comparison).
    """
    if not isinstance(registry_entry, dict):
        return False
    cors = registry_entry.get("cors_origins")
    cors_list: list
    if cors is None:
        cors_list = []
    elif isinstance(cors, list):
        cors_list = [c for c in cors if isinstance(c, str)]
    else:
        # Malformed config — fail closed.
        return False
    # Reject any wildcard entry outright.
    for c in cors_list:
        if c == "*" or c == "null":
            return False
    if origin is None:
        # stdio path, or HTTP without Origin header. Only OK when the
        # registry did not explicitly restrict origins.
        return not cors_list
    return origin in cors_list


def _secrets_dir(project_dir: Path) -> Path:
    """Return the mcp_client_secrets directory path (not created)."""
    return project_dir / "state" / "mcp_client_secrets"


def load_secret(project_dir: Path, client_id: str) -> Optional[bytes]:
    """Load the HMAC shared secret for ``client_id``.

    File layout: ``$CLAUDE_PROJECT_DIR/state/mcp_client_secrets/<client_id>.key``
    — 600 perms, raw bytes (not base64). Per ADR-042 §Auth.1.

    Security gates (any failure → None, fail-closed):

    1. ``client_id`` regex ``^[0-9a-f]{16}$`` (defense-in-depth; already
       validated by :func:`parse_token`).
    2. File MUST exist and be a regular file (no symlinks, no dirs,
       no named pipes).
    3. File perms MUST be 0o600 (owner read/write only). Any other
       bits set → None.
    4. File size in [16, 4096] bytes — rejects empty files and
       pathological huge ones.

    Returns the raw secret bytes or None on any failure. The return value
    MUST NOT appear in any audit field or log line.
    """
    if not re.match(r"^[0-9a-f]{16}$", client_id or ""):
        return None
    try:
        base = _secrets_dir(project_dir).resolve()
        target = (base / f"{client_id}.key").resolve()
    except (OSError, RuntimeError):
        return None
    # Path traversal defense: target MUST remain inside base.
    try:
        target.relative_to(base)
    except ValueError:
        return None
    try:
        if not target.is_file():
            return None
        # Reject symlinks — is_file() follows them, so check again via lstat.
        if os.path.islink(str(target)):
            return None
        st = target.stat()
    except OSError:
        return None
    mode_bits = st.st_mode & 0o777
    if mode_bits != 0o600:
        return None
    if not (16 <= st.st_size <= 4096):
        return None
    try:
        with target.open("rb") as f:
            data = f.read(4097)
    except OSError:
        return None
    if len(data) > 4096:
        return None
    return data


def hash_client_id(client_id: str) -> str:
    """Return a 16-char SHA-256 hex prefix of ``client_id``.

    Used for audit events (ADR-042 §Auth.5). The 16-hex-char client_id
    is already non-sensitive, but we hash it anyway so audit consumers
    cannot correlate across clients without the registry.
    """
    if not client_id:
        return ""
    return hashlib.sha256(client_id.encode("utf-8")).hexdigest()[:16]


__all__ = [
    "parse_bearer",
    "parse_token",
    "compute_hmac",
    "verify_hmac",
    "verify_timestamp_skew",
    "load_client_registry",
    "check_acl",
    "check_cors",
    "load_secret",
    "hash_client_id",
]
