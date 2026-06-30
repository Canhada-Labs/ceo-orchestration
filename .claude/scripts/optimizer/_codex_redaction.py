"""Pure redaction + hashing helpers for the WS-3 Codex phase-gate driver.

The phase-gate driver crosses an LLM trust boundary: it takes Codex (a *lower*
trust channel) output and folds a verdict into the higher-trust audit channel.
NOTHING from the Codex side may be laundered verbatim into that channel — not a
thread id, not a prompt body, not a summary, not a secret (S190 prompt-leak P0).
So everything that leaves this boundary is either an enum, a bounded int, or a
**stable opaque hash** of the raw text. These helpers produce only those forms.

All functions are pure (no IO, no env, no clock), deterministic, and NEVER raise
— a redaction failure must degrade to an empty/sentinel hash, never crash the
gate. Hashing is ``hashlib.sha256`` (stdlib); we expose only a short hex prefix
so the value is an opaque correlation token, not a reversible payload.

ReDoS discipline (S190 caught ``first.*?then`` at 222ms): any regex in this
package uses ONLY bounded char classes with explicit ``{m,n}`` length limits —
NO nested quantifiers, NO ambiguous ``.*?``/``.+?`` across alternations. Every
scan is additionally length-capped before the match so worst-case work is O(cap).
"""

from __future__ import annotations

import hashlib
import re
from typing import Optional

# Hard cap on how much raw text we will hash/scan. A Codex result is normally a
# few KB; we never need to walk an unbounded blob, and capping first makes every
# regex below provably O(_SCAN_CAP).
_SCAN_CAP: int = 20000

# Length of the hex prefix we expose. 16 hex chars = 64 bits of the digest —
# plenty to correlate two events without being a reversible payload.
_SHORT_HASH_LEN: int = 16

# Sentinel returned when there is genuinely nothing to hash (empty/blank input).
# A fixed, recognisable, NON-secret token so a downstream reader can tell
# "no thread id" from a real (hashed) one without us echoing the raw value.
_EMPTY_SENTINEL: str = "none"

# ReDoS-safe thread-id extractor. Codex thread ids look like ``019e7ebc...`` or
# ``wf_7247d2b1-...`` or a UUID-ish ``0193-abcd``. We do NOT try to be clever:
# bounded char class, explicit {8,64} length, anchored at a word boundary, NO
# nested/ambiguous quantifier. Used only to FIND a token to hash — we never emit
# the captured text, only its hash.
_RE_THREAD_TOKEN = re.compile(r"\b[0-9a-fA-F][0-9a-fA-F_-]{7,63}\b")


def _sha_short(text: str) -> str:
    """Stable 16-hex-char sha256 prefix of ``text`` (utf-8). Never raises."""
    try:
        digest = hashlib.sha256(text.encode("utf-8", "replace")).hexdigest()
        return digest[:_SHORT_HASH_LEN]
    except Exception:
        # A hashing failure must never surface raw bytes; degrade to sentinel.
        return _EMPTY_SENTINEL


def summary_hash(text: Optional[str]) -> str:
    """Opaque, stable hex hash of a Codex summary/diff. NEVER the raw text.

    Returns a 16-char lowercase hex digest of the (length-capped) input, or the
    ``"none"`` sentinel for an empty/blank/non-str input. Deterministic: equal
    inputs → equal output. This is the ONLY function that should ever turn Codex
    free-text into an audit-bound value, guaranteeing no prompt/summary body is
    laundered into the higher-trust channel.
    """
    try:
        if not isinstance(text, str):
            return _EMPTY_SENTINEL
        capped = text[:_SCAN_CAP]
        if not capped.strip():
            return _EMPTY_SENTINEL
        return _sha_short(capped)
    except Exception:
        return _EMPTY_SENTINEL


def redact_thread_id(raw: Optional[str]) -> str:
    """Turn a raw Codex thread id into a stable short hash. NEVER the raw id.

    Accepts the full thread id (``019e7ebc...``), a noisy line that *contains*
    one, or junk. We length-cap, pull the first bounded id-shaped token with a
    ReDoS-safe regex (falling back to the whole capped string if none matches),
    and return its 16-char sha256 prefix. Empty/blank/non-str → ``"none"``.

    The output is an opaque correlation token: two events about the same Codex
    thread share a ``thread_id_redacted`` without the raw id ever leaving this
    boundary (S190 prompt-leak defense).
    """
    try:
        if not isinstance(raw, str):
            return _EMPTY_SENTINEL
        capped = raw[:_SCAN_CAP]
        if not capped.strip():
            return _EMPTY_SENTINEL
        match = _RE_THREAD_TOKEN.search(capped)
        token = match.group(0) if match is not None else capped.strip()
        return _sha_short(token)
    except Exception:
        return _EMPTY_SENTINEL
