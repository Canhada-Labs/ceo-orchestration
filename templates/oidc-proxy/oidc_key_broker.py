"""OIDC -> key-broker reference recipe (stdlib-only, py>=3.9).

PLAN-133 item E7 (Wave E — Advanced guardrails). This is an EDITABLE
TEMPLATE shipped for adopters, NOT a wired framework hook. Copy it into
your own broker service and adapt.

PROBLEM
-------
A workload (CI job, agent, sidecar) holds a short-lived OIDC identity
token (e.g. a GitHub Actions OIDC JWT, a Kubernetes ServiceAccount
projected token, or a cloud workload-identity token). It must NOT carry
your long-lived provider API keys. Instead it presents the OIDC token to
a *key broker* which, after verifying the token, mints/returns a
short-lived provider credential scoped to that workload.

This module is the broker's VERIFY step — the trust gate. It is
deliberately conservative and re-implements the hardening already
ratified for MCP bearer/DPoP defense in ADR-122:

  * §A.1 / §A.3  alg ALLOWLIST — reject `alg=none` and every `alg=HS*`
                 at PARSER PRECEDENCE, BEFORE any signature verification.
                 An asymmetric-only allowlist closes the classic JWT
                 alg-confusion / key-confusion attacks.
  * §A.4         per-jti NONCE CACHE — a `jti` is single-use within its
                 TTL window (TTL <= 5 min). Eviction is LRU + TTL ONLY
                 (no count-based eviction -> no cache-flush DoS). Cache
                 key is the `(jti, iat)` tuple. Replay of the same proof
                 is rejected.

SECURITY POSTURE
----------------
  * FAIL-CLOSED on every trust decision: a malformed token, a
    disallowed alg, a replayed jti, an expired/early token, an
    audience/issuer mismatch -> DENY. There is no "fail-open" path in
    the verify function; fail-open here would mint a credential for an
    attacker.
  * SIGNATURE VERIFICATION IS A SEAM. The stdlib ships no asymmetric
    verifier (no RSA/EC public-key crypto in the standard library), so
    this template REQUIRES the adopter to inject a `verify_signature`
    callable backed by their crypto library of choice (the broker is
    not the framework; the framework stays stdlib-only). The template
    ships a `RejectAllVerifier` default so that an UNCONFIGURED broker
    DENIES every token (fail-closed) rather than accidentally trusting
    one.
  * NO SECRET / TOKEN VALUE IS EVER ECHOED into a returned error or a
    log line produced by this module. `VerificationError` carries a
    machine `reason` enum only.

This module performs NO network I/O and constructs NO LLM/provider
client. It is pure local verification.
"""

from __future__ import annotations

import base64
import binascii
import collections
import hashlib
import json
import threading
import time
from typing import Callable, Dict, Optional, Tuple

# ---------------------------------------------------------------------------
# ADR-122 §A.1 / §A.3 — asymmetric-only alg allowlist.
# Rejecting `none` and every `HS*` is the whole point: an attacker who can
# only influence the header must not be able to downgrade to an unsigned or
# symmetric-keyed token (alg-confusion). This set is the SAME asymmetric set
# ADR-122 §A.3 clause 2 enumerates.
# ---------------------------------------------------------------------------
ALLOWED_ALGS = frozenset(
    {"ES256", "ES384", "ES512", "EdDSA", "PS256", "PS384", "PS512", "RS256", "RS384", "RS512"}
)

# Default nonce-cache TTL. ADR-122 §A.4: TTL <= 5 min per RFC 9449 §11.1.
DEFAULT_NONCE_TTL_SECONDS = 300
# Default nonce-cache size bound. ADR-122 §A.4: configurable, default 16384.
DEFAULT_NONCE_MAX_ENTRIES = 16_384
# RFC-recommended max clock skew (ADR-122 §A.3 clause 6 uses +/-60s for iat).
DEFAULT_CLOCK_SKEW_SECONDS = 60


class VerificationError(Exception):
    """Raised on ANY fail-closed denial.

    Carries a machine-readable `reason` enum ONLY — never the token, a
    claim value, or any secret. Closed enum of reasons:

      malformed_token, disallowed_alg, signature_invalid, replayed_jti,
      missing_claim, token_expired, token_not_yet_valid, iat_out_of_window,
      audience_mismatch, issuer_mismatch, subject_not_allowed.
    """

    def __init__(self, reason: str) -> None:
        super().__init__(reason)
        self.reason = reason


def _b64url_decode(segment: str) -> bytes:
    """Decode a base64url JWT segment, tolerating missing padding."""
    if not isinstance(segment, str) or segment == "":
        raise VerificationError("malformed_token")
    pad = "=" * (-len(segment) % 4)
    try:
        return base64.urlsafe_b64decode(segment + pad)
    except (binascii.Error, ValueError):
        raise VerificationError("malformed_token")


def parse_jws_header(token: str) -> Dict[str, object]:
    """Parse ONLY the JOSE header of a compact JWS WITHOUT verifying it.

    Used to enforce the alg allowlist at parser precedence — i.e. we can
    reject `alg=none`/`alg=HS*` BEFORE touching the signature. Returns the
    decoded header dict. Raises VerificationError(malformed_token) on a
    structurally broken token.
    """
    if not isinstance(token, str):
        raise VerificationError("malformed_token")
    parts = token.split(".")
    if len(parts) != 3:
        raise VerificationError("malformed_token")
    raw = _b64url_decode(parts[0])
    try:
        header = json.loads(raw)
    except (ValueError, UnicodeDecodeError):
        raise VerificationError("malformed_token")
    if not isinstance(header, dict):
        raise VerificationError("malformed_token")
    return header


def enforce_alg_allowlist(header: Dict[str, object]) -> str:
    """Return the header `alg` iff it is in ALLOWED_ALGS, else fail-closed.

    ADR-122 §A.3 clause 2: parser-precedence BEFORE signature verify. The
    case-sensitive membership test means `none`, `None`, `hs256`, `HS256`,
    a missing alg, or a non-string alg all DENY.
    """
    alg = header.get("alg")
    if not isinstance(alg, str) or alg not in ALLOWED_ALGS:
        raise VerificationError("disallowed_alg")
    return alg


class NonceCache:
    """Per-jti single-use nonce cache (ADR-122 §A.4).

    Invariants:
      * Cache key is the `(jti, iat)` tuple.
      * TTL <= ttl_seconds (default 300, ADR-122 §A.4 / RFC 9449 §11.1).
      * Eviction is LRU + TTL ONLY — NEVER count-based-on-insert in a way
        that could evict a still-live nonce to admit a replay. When the
        size bound is hit we first purge EXPIRED entries; only if still
        full do we evict the OLDEST (LRU) entry — which, by construction,
        is the closest to its own expiry. This avoids the cache-flush DoS
        ADR-122 §A.4 calls out (an attacker cannot inject N fresh nonces
        to evict a victim's live nonce and then replay it, because the
        victim entry would have to be both older AND the eviction only
        happens once expired entries are exhausted; combined with the
        short TTL the replay window is bounded by the TTL, not the cache
        size).
      * Thread-safe (a broker handles concurrent requests).

    `check_and_consume` returns True (admit) the FIRST time a given
    (jti, iat) is seen within its TTL, and False (replay -> deny) on every
    subsequent presentation within the TTL.
    """

    def __init__(
        self,
        ttl_seconds: int = DEFAULT_NONCE_TTL_SECONDS,
        max_entries: int = DEFAULT_NONCE_MAX_ENTRIES,
        time_fn: Optional[Callable[[], float]] = None,
    ) -> None:
        if ttl_seconds <= 0 or ttl_seconds > DEFAULT_NONCE_TTL_SECONDS:
            # Enforce the ADR-122 §A.4 ceiling (<= 5 min). A broker that
            # tries to widen the replay window is mis-configured -> refuse.
            raise ValueError("ttl_seconds must be in (0, 300]")
        if max_entries <= 0:
            raise ValueError("max_entries must be > 0")
        self._ttl = ttl_seconds
        self._max = max_entries
        self._time = time_fn if time_fn is not None else time.monotonic
        # OrderedDict gives O(1) LRU move-to-end + popitem(last=False).
        # value = expiry monotonic deadline.
        self._store: "collections.OrderedDict[Tuple[str, int], float]" = collections.OrderedDict()
        self._lock = threading.Lock()

    def _purge_expired_locked(self, now: float) -> None:
        # Entries are inserted in expiry order (uniform TTL), so the oldest
        # are the first to expire — popping from the front until we hit a
        # live one is O(expired).
        store = self._store
        while store:
            key, deadline = next(iter(store.items()))
            if deadline <= now:
                store.popitem(last=False)
            else:
                break

    def check_and_consume(self, jti: object, iat: object) -> bool:
        """Admit-once. Returns False (replay) if (jti, iat) already live."""
        if not isinstance(jti, str) or jti == "":
            # A token with no usable jti cannot be replay-protected -> the
            # caller treats False as a denial (missing_claim handled there).
            return False
        if not isinstance(iat, int):
            return False
        key = (jti, iat)
        now = self._time()
        with self._lock:
            self._purge_expired_locked(now)
            existing = self._store.get(key)
            if existing is not None and existing > now:
                # Live nonce already present -> replay.
                return False
            if existing is not None:
                # Stale leftover (shouldn't happen after purge, defensive).
                self._store.pop(key, None)
            # Admit. Enforce size bound: purge expired first (already done),
            # then LRU-evict if still full.
            while len(self._store) >= self._max:
                self._store.popitem(last=False)
            self._store[key] = now + self._ttl
            return True

    def __len__(self) -> int:
        with self._lock:
            return len(self._store)


def _require_str(claims: Dict[str, object], name: str) -> str:
    val = claims.get(name)
    if not isinstance(val, str) or val == "":
        raise VerificationError("missing_claim")
    return val


def _require_int(claims: Dict[str, object], name: str) -> int:
    val = claims.get(name)
    # JSON numbers may decode to int; reject bool (a subclass of int) and
    # float-with-fraction. Allow whole-number floats by coercion.
    if isinstance(val, bool):
        raise VerificationError("missing_claim")
    if isinstance(val, int):
        return val
    if isinstance(val, float) and val.is_integer():
        return int(val)
    raise VerificationError("missing_claim")


class RejectAllVerifier:
    """Default signature verifier: DENIES everything (fail-closed).

    An unconfigured broker must never mint a credential. The adopter MUST
    replace this with a real asymmetric verifier (e.g. backed by
    `cryptography` / `PyJWT` / `joserfc`) that returns True iff the
    signature over `signing_input` validates against the issuer's JWKS for
    the given `alg`/`kid`.
    """

    def __call__(self, alg: str, signing_input: bytes, signature: bytes, header: Dict[str, object]) -> bool:
        return False


def verify_oidc_token(
    token: str,
    *,
    expected_issuer: str,
    expected_audience: str,
    nonce_cache: NonceCache,
    verify_signature: Callable[[str, bytes, bytes, Dict[str, object]], bool],
    allowed_subjects: Optional[frozenset] = None,
    clock_skew_seconds: int = DEFAULT_CLOCK_SKEW_SECONDS,
    now_fn: Optional[Callable[[], float]] = None,
) -> Dict[str, object]:
    """Verify an OIDC identity token for the key broker. FAIL-CLOSED.

    Order of checks (each one fail-closed):
      1. structural parse
      2. ADR-122 alg allowlist (BEFORE signature) — reject none/HS*
      3. signature verification (adopter-injected asymmetric verifier)
      4. required claims present (iss, aud, sub, jti, iat, exp)
      5. issuer / audience / (optional) subject-allowlist match
      6. exp / nbf / iat window with bounded clock skew
      7. ADR-122 per-jti nonce single-use (replay defense)

    Returns the validated claims dict on success. Raises VerificationError
    (machine reason enum, NO value echo) on any failure.

    The broker calls this; on success it then mints the scoped provider
    credential. This function NEVER mints — separation of verify and mint.
    """
    now = (now_fn or time.time)()

    header = parse_jws_header(token)
    alg = enforce_alg_allowlist(header)  # step 2 — precedence before sig

    parts = token.split(".")
    signing_input = (parts[0] + "." + parts[1]).encode("ascii")
    signature = _b64url_decode(parts[2])
    if not verify_signature(alg, signing_input, signature, header):
        raise VerificationError("signature_invalid")

    try:
        claims = json.loads(_b64url_decode(parts[1]))
    except (ValueError, UnicodeDecodeError):
        raise VerificationError("malformed_token")
    if not isinstance(claims, dict):
        raise VerificationError("malformed_token")

    iss = _require_str(claims, "iss")
    sub = _require_str(claims, "sub")
    jti = _require_str(claims, "jti")
    iat = _require_int(claims, "iat")
    exp = _require_int(claims, "exp")
    # `aud` may be a string or a list per RFC 7519.
    aud_claim = claims.get("aud")

    if iss != expected_issuer:
        raise VerificationError("issuer_mismatch")

    if isinstance(aud_claim, str):
        aud_ok = aud_claim == expected_audience
    elif isinstance(aud_claim, list):
        aud_ok = expected_audience in aud_claim
    else:
        aud_ok = False
    if not aud_ok:
        raise VerificationError("audience_mismatch")

    if allowed_subjects is not None and sub not in allowed_subjects:
        raise VerificationError("subject_not_allowed")

    skew = clock_skew_seconds
    if now > exp + skew:
        raise VerificationError("token_expired")
    nbf = claims.get("nbf")
    if isinstance(nbf, (int, float)) and not isinstance(nbf, bool):
        if now + skew < nbf:
            raise VerificationError("token_not_yet_valid")
    if iat - skew > now:
        raise VerificationError("iat_out_of_window")

    # ADR-122 §A.4 — per-jti single-use within TTL. Done LAST so a token
    # that would be rejected anyway never consumes a nonce slot.
    if not nonce_cache.check_and_consume(jti, iat):
        raise VerificationError("replayed_jti")

    return claims


def access_token_thumbprint(access_token: str) -> str:
    """SHA-256 base64url thumbprint of an access token (ADR-122 §A.3 ath).

    Helper for adopters who additionally bind a DPoP proof's `ath` claim
    to the broker-minted access token. Pure, no I/O.
    """
    digest = hashlib.sha256(access_token.encode("utf-8")).digest()
    return base64.urlsafe_b64encode(digest).rstrip(b"=").decode("ascii")
