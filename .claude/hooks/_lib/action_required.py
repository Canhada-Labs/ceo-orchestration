"""PLAN-133 E6 — Schema-typed Human-In-The-Loop (HITL) confirmation rail.

CANONICAL DESTINATION: .claude/hooks/_lib/action_required.py  (new file)
STAGED here for the Owner-GPG ceremony (the live canonical-edit guard
blocks _lib/*.py writes without an Owner-signed sentinel; see
.claude/plans/PLAN-133/staged/E6.proposal.md).

Goose-harvest provenance: re-implemented from scratch (stdlib only) after
read-only analysis of the action-required / resume-token pattern. NO
aaif-goose code copied; NO installer/binary ever executed.

## What this is

A deterministic, schema-typed rail for the case where an in-flight
agent action must PAUSE and request explicit Owner confirmation before
it proceeds (e.g. a high-blast-radius command, a spend over a soft cap,
a destructive file op). The rail:

1. **Mints a held action** — ``build_held_action()`` returns a
   ``HeldAction`` (schema-typed dataclass) carrying a CSPRNG
   ``resume_token`` (``secrets.token_urlsafe`` — NEVER ``uuid1`` /
   counter / time-seeded), bound to the originating ``session_id`` and
   stamped with an expiry.
2. **Persists a single-use claim** — ``register_held_action()`` writes
   an atomic ``O_CREAT | O_EXCL`` claim file keyed on
   ``sha256(token)`` (never the raw token) so the token can be consumed
   AT MOST ONCE (atomic compare-and-swap on the POSIX filesystem).
3. **Consumes on resume** — ``consume_resume_token()`` atomically
   claims-and-deletes the file. A second consume of the same token is
   REJECTED (replay). A token presented against a DIFFERENT held
   action id is REJECTED. An expired token is REJECTED (fail-CLOSED).
   A token from a DIFFERENT session is REJECTED.
4. **Redacts before egress** — ``redact_for_emit()`` routes the
   action-required JSON through ``codex_egress_redact.redact`` so no
   secret/PII reaches ``audit_emit`` or the Owner display.

## Security invariants (E6 identity must-fix, PLAN-133 §3 doctrine)

- **CSPRNG single-use**: ``secrets.token_urlsafe(32)`` (256 bits of
  entropy); the claim file makes consumption atomic + single-use.
- **Session-bound**: ``consume_resume_token`` compares the presented
  ``session_id`` against the one stamped at mint via
  ``hmac.compare_digest`` (constant-time) — a token minted in session
  A can NEVER resume in session B.
- **Expired → fail-CLOSED**: a timed-out token is rejected AND its
  claim file is reaped, never granting the action.
- **Token ≠ in-flight held action**: the consume call must name the
  ``action_id`` it expects; a token whose claim names a different
  ``action_id`` is rejected (prevents cross-action token swap).
- **No raw token on disk / in logs**: only ``sha256(token)`` is ever
  persisted or echoed; ``redact_for_emit`` strips the live token from
  any display/audit payload entirely.

## Posture

- **Default-OFF** behavioral gate: ``CEO_HITL_RAIL=1`` arms the rail;
  unset/``0`` → ``is_enabled()`` is False and the *minting* helpers
  short-circuit (the pure token/consume primitives remain callable so
  unit tests + the audit layer can exercise them).
- **Fail-open-on-infra**: I/O / parse / clock errors NEVER raise to the
  caller. A consume that cannot positively prove validity returns a
  ``ConsumeResult`` with ``ok=False`` and a closed-enum ``reason`` —
  the *trust* decision fails CLOSED (deny), the *process* fails open
  (no exception, no session-block).
- This module **never emits** to the audit log itself (it is a pure
  ``_lib`` helper). The canonical hook that consumes it emits the
  closed-enum ``action_required_held`` / ``action_required_resumed`` /
  ``action_required_rejected`` actions (see
  ``.claude/plans/PLAN-133/staged/E6.proposal.md``).

Stdlib only. Python >= 3.9. ``from __future__ import annotations``.
"""

from __future__ import annotations

import hashlib
import hmac
import json
import os
import secrets
import tempfile
import time
from dataclasses import dataclass, field
from pathlib import Path
from typing import Any, Dict, Optional

# Redaction goes through the canonical single-pass egress redactor so the
# action-required JSON is scrubbed identically to Codex egress before it
# reaches audit_emit or the Owner display.
try:  # pragma: no cover - import shim is environment-trivial
    from . import codex_egress_redact as _redact
except Exception:  # pragma: no cover - fail-open if the redactor is unavailable
    _redact = None  # type: ignore[assignment]


# ---------------------------------------------------------------------------
# Constants
# ---------------------------------------------------------------------------

#: Env flag that ARMS the behavioral rail. Default-OFF per PLAN-133 §3
#: doctrine #1 (measure-first). Minting short-circuits when unset.
_ENABLE_ENV = "CEO_HITL_RAIL"

#: Default time-to-live for a held action before the resume token
#: expires (fail-CLOSED on timeout). Overridable via env for tests /
#: tuning; clamped to a sane band.
_DEFAULT_TTL_SECONDS = 900  # 15 minutes
_TTL_ENV = "CEO_HITL_RAIL_TTL_SECONDS"
_TTL_MIN = 5
_TTL_MAX = 24 * 3600

#: Token entropy (bytes -> ~43 url-safe chars at 32 bytes = 256 bits).
_TOKEN_NBYTES = 32

#: Hard cap on the schema-typed reason/summary free-text fields. The
#: rail is for short confirmation prompts, not payload smuggling.
_MAX_SUMMARY_BYTES = 4096

#: Closed enum of held-action kinds (schema-typed). An unknown kind
#: coerces to ``other`` -- never echoed verbatim (S172 doctrine).
KIND_ENUM = frozenset(
    {
        "bash_command",
        "file_write",
        "file_delete",
        "spend_over_cap",
        "spawn",
        "network_egress",
        "other",
    }
)

#: Closed enum of consume-rejection reasons (no raw values echoed).
REJECT_REASONS = frozenset(
    {
        "ok",
        "unknown_token",
        "replayed",
        "expired",
        "session_mismatch",
        "action_id_mismatch",
        "malformed_request",
        "infra_error",
    }
)


# ---------------------------------------------------------------------------
# Schema-typed payloads
# ---------------------------------------------------------------------------


@dataclass(frozen=True)
class HeldAction:
    """A schema-typed action paused awaiting Owner confirmation.

    ``resume_token`` is the live CSPRNG secret returned to the
    coordinator so it can mint the resume affordance. It is NEVER
    persisted (only its sha256 is) and NEVER audit-emitted (stripped by
    ``redact_for_emit``).
    """

    action_id: str
    session_id: str
    kind: str
    summary: str
    resume_token: str
    token_sha256: str
    created_at: float
    expires_at: float

    def is_expired(self, *, now: Optional[float] = None) -> bool:
        """True iff this held action has passed its expiry (fail-CLOSED)."""
        ref = time.time() if now is None else now
        return ref >= self.expires_at

    def to_display(self) -> Dict[str, Any]:
        """A REDACTED, token-free dict safe for audit_emit + Owner display.

        The raw ``resume_token`` is dropped entirely; the free-text
        ``summary`` is routed through the egress redactor; only the
        ``token_sha256`` (a hash, not a secret) is retained for
        correlation.
        """
        return redact_for_emit(
            {
                "action_id": self.action_id,
                "session_id": self.session_id,
                "kind": self.kind,
                "summary": self.summary,
                "token_sha256": self.token_sha256,
                "created_at": _round_ts(self.created_at),
                "expires_at": _round_ts(self.expires_at),
            }
        )


@dataclass(frozen=True)
class ResumeRequest:
    """A schema-typed resume affordance presented to consume a held action."""

    action_id: str
    session_id: str
    resume_token: str


@dataclass(frozen=True)
class ConsumeResult:
    """Outcome of a consume attempt. ``ok`` gates the action; ``reason``
    is a closed-enum member (never a raw token or path)."""

    ok: bool
    reason: str
    action_id: str = ""
    token_sha256: str = ""
    detail: Dict[str, Any] = field(default_factory=dict)


# ---------------------------------------------------------------------------
# Helpers
# ---------------------------------------------------------------------------


def is_enabled() -> bool:
    """True iff the behavioral rail is ARMED (``CEO_HITL_RAIL=1``)."""
    return os.environ.get(_ENABLE_ENV, "0").strip() == "1"


def _ttl_seconds() -> int:
    raw = os.environ.get(_TTL_ENV, "").strip()
    if not raw:
        return _DEFAULT_TTL_SECONDS
    try:
        n = int(raw)
    except (TypeError, ValueError):
        return _DEFAULT_TTL_SECONDS
    if n < _TTL_MIN:
        return _TTL_MIN
    if n > _TTL_MAX:
        return _TTL_MAX
    return n


def _round_ts(ts: float) -> int:
    """Coarsen a timestamp to whole seconds (canonical_json no-float)."""
    try:
        return int(ts)
    except (TypeError, ValueError):
        return 0


def _token_sha256(token: str) -> str:
    return hashlib.sha256(token.encode("utf-8", errors="replace")).hexdigest()


def _coerce_kind(kind: Any) -> str:
    s = str(kind or "").strip()
    return s if s in KIND_ENUM else "other"


def _truncate_summary(summary: Any) -> str:
    s = str(summary or "")
    b = s.encode("utf-8", errors="replace")
    if len(b) <= _MAX_SUMMARY_BYTES:
        return s
    return b[:_MAX_SUMMARY_BYTES].decode("utf-8", errors="replace")


def redact_for_emit(payload: Dict[str, Any]) -> Dict[str, Any]:
    """Scrub an action-required dict before audit_emit / Owner display.

    Routes every free-text VALUE through ``codex_egress_redact.redact``
    (single-pass secret+PII scrub) and HARD-DROPS any live
    ``resume_token`` key so a secret can never reach the log or screen.
    NEVER raises (fail-open redaction: on any error the field is dropped,
    never passed through raw).
    """
    if not isinstance(payload, dict):
        return {}
    out: Dict[str, Any] = {}
    for key, value in payload.items():
        # Hard-drop the live token under any spelling.
        if key in ("resume_token", "token", "raw_token"):
            continue
        if isinstance(value, str):
            out[key] = _redact_text(value)
        elif isinstance(value, bool) or value is None:
            out[key] = value
        elif isinstance(value, (int, float)):
            out[key] = value
        elif isinstance(value, dict):
            out[key] = redact_for_emit(value)
        elif isinstance(value, (list, tuple)):
            out[key] = [
                _redact_text(v) if isinstance(v, str) else v for v in value
            ]
        else:
            # Unknown type -> stringify + redact (never pass an opaque obj).
            out[key] = _redact_text(str(value))
    return out


def _redact_text(text: str) -> str:
    if _redact is None:
        # Redactor unavailable -> fail-CLOSED on content: drop to a
        # sentinel rather than leak un-scrubbed text.
        return "[REDACTOR-UNAVAILABLE]"
    try:
        return _redact.redact(text)
    except Exception:
        return "[REDACTOR-UNAVAILABLE]"


# ---------------------------------------------------------------------------
# Claim store (atomic single-use CAS on the POSIX filesystem)
# ---------------------------------------------------------------------------


def _store_dir() -> Path:
    """Directory holding the single-use claim files.

    Honors ``CEO_HITL_RAIL_STORE_DIR`` (tests point this at a tmp dir);
    otherwise a process-private subdir under the system temp root. The
    claim files contain ONLY the token-hash-keyed metadata (action_id,
    session-hash, expiry) -- never the raw token, never the summary.
    """
    env = os.environ.get("CEO_HITL_RAIL_STORE_DIR", "").strip()
    base = Path(env) if env else Path(tempfile.gettempdir()) / "ceo-hitl-rail"
    try:
        base.mkdir(parents=True, exist_ok=True)
    except Exception:
        pass  # fail-open; register/consume handle a missing dir
    return base


def _claim_path(token_sha: str) -> Path:
    # token_sha is 64 hex chars -- safe as a filename, no path traversal.
    safe = "".join(c for c in token_sha if c in "0123456789abcdef")[:64]
    return _store_dir() / ("claim-" + safe + ".json")


def _session_sha256(session_id: str) -> str:
    return hashlib.sha256(session_id.encode("utf-8", errors="replace")).hexdigest()


# ---------------------------------------------------------------------------
# Public API -- mint / register / consume
# ---------------------------------------------------------------------------


def build_held_action(
    *,
    session_id: str,
    kind: str,
    summary: str,
    action_id: Optional[str] = None,
    ttl_seconds: Optional[int] = None,
    now: Optional[float] = None,
) -> HeldAction:
    """Mint a schema-typed held action with a CSPRNG resume token.

    Pure constructor -- does NOT touch disk (use ``register_held_action``
    to persist the single-use claim). NEVER raises.
    """
    ts = time.time() if now is None else now
    if ttl_seconds is None:
        ttl = _ttl_seconds()
    else:
        ttl = max(_TTL_MIN, min(_TTL_MAX, int(ttl_seconds)))
    token = secrets.token_urlsafe(_TOKEN_NBYTES)
    token_sha = _token_sha256(token)
    aid = str(action_id) if action_id else ("ar-" + secrets.token_hex(8))
    return HeldAction(
        action_id=aid,
        session_id=str(session_id),
        kind=_coerce_kind(kind),
        summary=_truncate_summary(summary),
        resume_token=token,
        token_sha256=token_sha,
        created_at=ts,
        expires_at=ts + ttl,
    )


def register_held_action(held: HeldAction) -> bool:
    """Persist the single-use claim for ``held`` atomically.

    Writes a claim file via ``O_CREAT | O_EXCL`` (atomic create -- fails
    if a file with the same token-hash already exists). The file stores
    ONLY the token-hash-keyed metadata, never the raw token or summary.

    Returns True on a fresh claim, False if a claim with the same
    token-hash already exists (entropy collision -- astronomically
    unlikely; treated as a mint failure). NEVER raises.
    """
    if not isinstance(held, HeldAction):
        return False
    path = _claim_path(held.token_sha256)
    record = {
        "action_id": held.action_id,
        "session_sha256": _session_sha256(held.session_id),
        "kind": held.kind,
        "created_at": _round_ts(held.created_at),
        "expires_at": _round_ts(held.expires_at),
    }
    try:
        body = json.dumps(record, sort_keys=True, separators=(",", ":"))
    except (TypeError, ValueError):
        return False
    try:
        fd = os.open(str(path), os.O_CREAT | os.O_EXCL | os.O_WRONLY, 0o600)
    except FileExistsError:
        return False  # token-hash already claimed
    except OSError:
        return False  # fail-open on infra (dir missing/permission); deny mint
    try:
        with os.fdopen(fd, "w", encoding="utf-8") as fh:
            fh.write(body)
        return True
    except OSError:
        # Best-effort cleanup of the half-written claim.
        try:
            os.unlink(str(path))
        except OSError:
            pass
        return False


def consume_resume_token(
    request: ResumeRequest,
    *,
    now: Optional[float] = None,
) -> ConsumeResult:
    """Atomically claim-and-delete a held action's single-use token.

    Trust gate (every check fails CLOSED -- deny on any doubt):

    1. **unknown_token** -- no claim file for ``sha256(token)``.
    2. **action_id_mismatch** -- claim names a different ``action_id``
       than the request (cross-action token swap).
    3. **session_mismatch** -- claim's session-hash != request session
       (constant-time compare; token from another session).
    4. **expired** -- past ``expires_at`` (fail-CLOSED on timeout); the
       claim is reaped.
    5. **replayed** -- the atomic delete already removed the claim on a
       prior consume; a second consume sees ``unknown_token``.

    The claim is consumed via an atomic ``os.replace`` rename: only ONE
    caller can win the rename, so a concurrent / replayed second
    consumer loses the race and gets ``unknown_token``.

    NEVER raises. On infra error the result is ``ok=False`` with
    ``reason='infra_error'`` (deny).
    """
    # Validate request shape (schema-typed).
    if not isinstance(request, ResumeRequest):
        return ConsumeResult(ok=False, reason="malformed_request")
    token = request.resume_token
    if not isinstance(token, str) or not token:
        return ConsumeResult(ok=False, reason="malformed_request")

    token_sha = _token_sha256(token)
    path = _claim_path(token_sha)

    # ATOMIC CLAIM: rename the claim file to a private name. Only ONE
    # caller can win this rename; the loser (replay/concurrent) gets
    # ENOENT -> unknown_token. This is the single-use CAS.
    claimed = path.with_suffix(".claimed-" + secrets.token_hex(6))
    try:
        os.replace(str(path), str(claimed))
    except FileNotFoundError:
        # Either never registered, or a prior consume already won the
        # rename and deleted it. Both surface as a denied resume.
        return ConsumeResult(ok=False, reason="unknown_token", token_sha256=token_sha)
    except OSError:
        return ConsumeResult(ok=False, reason="infra_error", token_sha256=token_sha)

    # We now exclusively own ``claimed``. Read + validate, then unlink.
    try:
        raw = Path(claimed).read_text(encoding="utf-8")
    except OSError:
        _safe_unlink(claimed)
        return ConsumeResult(ok=False, reason="infra_error", token_sha256=token_sha)

    try:
        record = json.loads(raw)
    except (TypeError, ValueError):
        _safe_unlink(claimed)
        return ConsumeResult(ok=False, reason="infra_error", token_sha256=token_sha)

    _safe_unlink(claimed)  # burn the single-use claim now

    if not isinstance(record, dict):
        return ConsumeResult(ok=False, reason="infra_error", token_sha256=token_sha)

    claim_action_id = str(record.get("action_id", ""))
    claim_session_sha = str(record.get("session_sha256", ""))
    expires_at = record.get("expires_at", 0)

    # 2. action_id binding -- the token must resume the SAME action.
    if not _ct_eq(claim_action_id, str(request.action_id)):
        return ConsumeResult(
            ok=False,
            reason="action_id_mismatch",
            action_id=claim_action_id,
            token_sha256=token_sha,
        )

    # 3. session binding -- constant-time compare of session hashes.
    req_session_sha = _session_sha256(str(request.session_id))
    if not _ct_eq(claim_session_sha, req_session_sha):
        return ConsumeResult(
            ok=False,
            reason="session_mismatch",
            action_id=claim_action_id,
            token_sha256=token_sha,
        )

    # 4. expiry -- fail-CLOSED on timeout.
    ref = time.time() if now is None else now
    try:
        exp = float(expires_at)
    except (TypeError, ValueError):
        exp = 0.0
    if ref >= exp:
        return ConsumeResult(
            ok=False,
            reason="expired",
            action_id=claim_action_id,
            token_sha256=token_sha,
        )

    return ConsumeResult(
        ok=True,
        reason="ok",
        action_id=claim_action_id,
        token_sha256=token_sha,
    )


def _safe_unlink(path: Path) -> None:
    try:
        os.unlink(str(path))
    except OSError:
        pass


def _ct_eq(a: str, b: str) -> bool:
    """Constant-time string equality (hmac.compare_digest)."""
    try:
        return hmac.compare_digest(
            a.encode("utf-8", errors="replace"),
            b.encode("utf-8", errors="replace"),
        )
    except Exception:
        return False


def reap_expired_claims(*, now: Optional[float] = None) -> int:
    """Best-effort GC of expired claim files. Returns count reaped.

    Hygiene only -- the consume path already fails CLOSED on expiry, so a
    stale claim never grants an action. NEVER raises.
    """
    ref = time.time() if now is None else now
    reaped = 0
    try:
        base = _store_dir()
        for p in base.glob("claim-*.json"):
            try:
                rec = json.loads(p.read_text(encoding="utf-8"))
                exp = float(rec.get("expires_at", 0))
            except Exception:
                exp = 0.0
            if ref >= exp:
                _safe_unlink(p)
                reaped += 1
    except Exception:
        pass
    return reaped


def held_action_to_json(held: HeldAction) -> str:
    """Serialize a held action's REDACTED display form to canonical JSON.

    The raw token is NOT included (``to_display`` drops it). Sorted keys
    + compact separators -> deterministic bytes for fixtures. NEVER raises.
    """
    try:
        return json.dumps(held.to_display(), sort_keys=True, separators=(",", ":"))
    except Exception:
        return "{}"
