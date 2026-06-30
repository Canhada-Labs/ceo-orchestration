"""Unit tests for the OIDC -> key-broker reference recipe (PLAN-133 E7).

stdlib-only, py>=3.9. This recipe lives under `templates/` which is NOT in
the pinned `pytest.ini :: testpaths`, so these tests are run on demand:

    python -m pytest templates/oidc-proxy/tests/ -q

They prove the two ADR-122 guarantees E7 ships:
  * §A.1/§A.3 alg allowlist — `alg=none` / `alg=HS*` rejected at parser
    precedence, BEFORE signature verification is ever attempted.
  * §A.4 per-jti nonce cache — a `jti` is single-use within its TTL; a
    replay is denied; eviction is LRU+TTL only; the no-value-echo property
    of VerificationError.
"""

from __future__ import annotations

import base64
import json
import os
import sys
import unittest

# Make the sibling module importable without packaging the template.
sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

from oidc_key_broker import (  # noqa: E402
    ALLOWED_ALGS,
    DEFAULT_NONCE_TTL_SECONDS,
    NonceCache,
    RejectAllVerifier,
    VerificationError,
    access_token_thumbprint,
    enforce_alg_allowlist,
    parse_jws_header,
    verify_oidc_token,
)


def _b64url(raw: bytes) -> str:
    return base64.urlsafe_b64encode(raw).rstrip(b"=").decode("ascii")


def _seg(obj: dict) -> str:
    return _b64url(json.dumps(obj).encode("utf-8"))


def _make_token(header: dict, claims: dict, signature: bytes = b"sig") -> str:
    return _seg(header) + "." + _seg(claims) + "." + _b64url(signature)


def _accept_all(alg, signing_input, signature, header):
    return True


# A fake clock so nonce-TTL tests are deterministic (ADR-122 §A.5: no
# time.time() inside the security-relevant path under test).
class FakeClock:
    def __init__(self, t: float = 1000.0) -> None:
        self.t = t

    def __call__(self) -> float:
        return self.t

    def advance(self, dt: float) -> None:
        self.t += dt


def _valid_claims(now: float = 1_000_000.0, jti: str = "jti-1") -> dict:
    return {
        "iss": "https://issuer.example",
        "aud": "key-broker",
        "sub": "repo:acme/app:ref:refs/heads/main",
        "jti": jti,
        "iat": int(now) - 5,
        "exp": int(now) + 300,
    }


# ---------------------------------------------------------------------------
# ADR-122 §A.1 / §A.3 — alg allowlist (parser precedence)
# ---------------------------------------------------------------------------
class TestAlgAllowlist(unittest.TestCase):
    def test_none_alg_rejected(self):
        with self.assertRaises(VerificationError) as ctx:
            enforce_alg_allowlist({"alg": "none"})
        self.assertEqual(ctx.exception.reason, "disallowed_alg")

    def test_none_alg_case_variants_rejected(self):
        for bad in ("None", "NONE", "nOnE", ""):
            with self.assertRaises(VerificationError) as ctx:
                enforce_alg_allowlist({"alg": bad})
            self.assertEqual(ctx.exception.reason, "disallowed_alg")

    def test_hs_family_rejected(self):
        for bad in ("HS256", "HS384", "HS512", "hs256"):
            with self.assertRaises(VerificationError) as ctx:
                enforce_alg_allowlist({"alg": bad})
            self.assertEqual(ctx.exception.reason, "disallowed_alg")

    def test_missing_or_nonstring_alg_rejected(self):
        for header in ({}, {"alg": None}, {"alg": 256}, {"alg": ["ES256"]}):
            with self.assertRaises(VerificationError) as ctx:
                enforce_alg_allowlist(header)
            self.assertEqual(ctx.exception.reason, "disallowed_alg")

    def test_asymmetric_algs_allowed(self):
        for good in ("ES256", "EdDSA", "PS256", "RS256", "ES512"):
            self.assertEqual(enforce_alg_allowlist({"alg": good}), good)

    def test_allowlist_has_no_symmetric_or_none(self):
        self.assertNotIn("none", ALLOWED_ALGS)
        self.assertFalse(any(a.startswith("HS") for a in ALLOWED_ALGS))

    def test_alg_enforced_before_signature_in_full_verify(self):
        # An alg=none token must be rejected with disallowed_alg even though
        # the signature verifier here would ACCEPT anything — proving the
        # allowlist runs at parser precedence, before the signature seam.
        token = _make_token({"alg": "none", "typ": "JWT"}, _valid_claims())
        calls = {"n": 0}

        def spy(alg, signing_input, signature, header):
            calls["n"] += 1
            return True

        with self.assertRaises(VerificationError) as ctx:
            verify_oidc_token(
                token,
                expected_issuer="https://issuer.example",
                expected_audience="key-broker",
                nonce_cache=NonceCache(time_fn=FakeClock()),
                verify_signature=spy,
                now_fn=lambda: 1_000_000.0,
            )
        self.assertEqual(ctx.exception.reason, "disallowed_alg")
        self.assertEqual(calls["n"], 0, "signature verifier ran before alg gate")


# ---------------------------------------------------------------------------
# ADR-122 §A.4 — per-jti nonce cache
# ---------------------------------------------------------------------------
class TestNonceCache(unittest.TestCase):
    def test_admit_once_then_replay_denied(self):
        clock = FakeClock()
        cache = NonceCache(time_fn=clock)
        self.assertTrue(cache.check_and_consume("jti-A", 100))
        self.assertFalse(cache.check_and_consume("jti-A", 100))  # replay
        self.assertFalse(cache.check_and_consume("jti-A", 100))

    def test_distinct_iat_is_distinct_key(self):
        cache = NonceCache(time_fn=FakeClock())
        self.assertTrue(cache.check_and_consume("jti-A", 100))
        self.assertTrue(cache.check_and_consume("jti-A", 101))  # (jti,iat) key

    def test_nonce_reusable_after_ttl_expiry(self):
        clock = FakeClock()
        cache = NonceCache(ttl_seconds=300, time_fn=clock)
        self.assertTrue(cache.check_and_consume("jti-B", 7))
        clock.advance(301)
        # Expired -> the same jti is admittable again (it is a fresh window).
        self.assertTrue(cache.check_and_consume("jti-B", 7))

    def test_ttl_ceiling_enforced(self):
        with self.assertRaises(ValueError):
            NonceCache(ttl_seconds=DEFAULT_NONCE_TTL_SECONDS + 1)
        with self.assertRaises(ValueError):
            NonceCache(ttl_seconds=0)

    def test_lru_eviction_only_after_expired_purge(self):
        clock = FakeClock()
        cache = NonceCache(ttl_seconds=300, max_entries=2, time_fn=clock)
        self.assertTrue(cache.check_and_consume("j1", 1))
        self.assertTrue(cache.check_and_consume("j2", 2))
        # Cache full; admitting j3 evicts the oldest live entry (j1).
        self.assertTrue(cache.check_and_consume("j3", 3))
        self.assertEqual(len(cache), 2)
        # j2 and j3 still protected against replay.
        self.assertFalse(cache.check_and_consume("j2", 2))
        self.assertFalse(cache.check_and_consume("j3", 3))

    def test_empty_or_nonstring_jti_denied(self):
        cache = NonceCache(time_fn=FakeClock())
        self.assertFalse(cache.check_and_consume("", 1))
        self.assertFalse(cache.check_and_consume(None, 1))
        self.assertFalse(cache.check_and_consume("ok", "1"))  # iat not int

    def test_size_bound_never_admits_replay_via_flush(self):
        # An attacker floods the cache with fresh nonces; the victim's live
        # nonce must still be protected within its TTL. With max_entries=4
        # and TTL active, replaying the victim must still be denied as long
        # as the victim entry has not been LRU-evicted by newer inserts.
        clock = FakeClock()
        cache = NonceCache(ttl_seconds=300, max_entries=4, time_fn=clock)
        self.assertTrue(cache.check_and_consume("victim", 1))
        # 3 more fill the cache without evicting the victim (LRU front).
        for i in range(2, 5):
            cache.check_and_consume("flood-%d" % i, i)
        # Replay of victim while still resident -> denied.
        self.assertFalse(cache.check_and_consume("victim", 1))


# ---------------------------------------------------------------------------
# Full verify path — fail-closed everywhere
# ---------------------------------------------------------------------------
class TestVerifyOidcToken(unittest.TestCase):
    def _verify(self, token, **over):
        kwargs = dict(
            expected_issuer="https://issuer.example",
            expected_audience="key-broker",
            nonce_cache=NonceCache(time_fn=FakeClock()),
            verify_signature=_accept_all,
            now_fn=lambda: 1_000_000.0,
        )
        kwargs.update(over)
        return verify_oidc_token(token, **kwargs)

    def test_happy_path_returns_claims(self):
        token = _make_token({"alg": "ES256", "typ": "JWT"}, _valid_claims())
        claims = self._verify(token)
        self.assertEqual(claims["sub"], "repo:acme/app:ref:refs/heads/main")

    def test_replayed_token_denied(self):
        token = _make_token({"alg": "ES256"}, _valid_claims(jti="reuse"))
        cache = NonceCache(time_fn=FakeClock())
        self._verify(token, nonce_cache=cache)  # first ok
        with self.assertRaises(VerificationError) as ctx:
            self._verify(token, nonce_cache=cache)  # replay
        self.assertEqual(ctx.exception.reason, "replayed_jti")

    def test_bad_signature_denied_and_no_nonce_consumed(self):
        token = _make_token({"alg": "ES256"}, _valid_claims(jti="sig-test"))
        cache = NonceCache(time_fn=FakeClock())
        with self.assertRaises(VerificationError) as ctx:
            self._verify(token, nonce_cache=cache, verify_signature=lambda *a: False)
        self.assertEqual(ctx.exception.reason, "signature_invalid")
        # A rejected token must NOT have consumed the nonce slot.
        self.assertEqual(len(cache), 0)

    def test_default_verifier_rejects_everything(self):
        token = _make_token({"alg": "ES256"}, _valid_claims())
        with self.assertRaises(VerificationError) as ctx:
            self._verify(token, verify_signature=RejectAllVerifier())
        self.assertEqual(ctx.exception.reason, "signature_invalid")

    def test_issuer_mismatch_denied(self):
        c = _valid_claims()
        c["iss"] = "https://evil.example"
        token = _make_token({"alg": "ES256"}, c)
        with self.assertRaises(VerificationError) as ctx:
            self._verify(token)
        self.assertEqual(ctx.exception.reason, "issuer_mismatch")

    def test_audience_mismatch_denied(self):
        c = _valid_claims()
        c["aud"] = "other-service"
        token = _make_token({"alg": "ES256"}, c)
        with self.assertRaises(VerificationError) as ctx:
            self._verify(token)
        self.assertEqual(ctx.exception.reason, "audience_mismatch")

    def test_audience_list_match(self):
        c = _valid_claims()
        c["aud"] = ["other", "key-broker"]
        token = _make_token({"alg": "ES256"}, c)
        self.assertEqual(self._verify(token)["aud"], ["other", "key-broker"])

    def test_subject_allowlist_denied(self):
        token = _make_token({"alg": "ES256"}, _valid_claims())
        with self.assertRaises(VerificationError) as ctx:
            self._verify(token, allowed_subjects=frozenset({"repo:other/x:ref:y"}))
        self.assertEqual(ctx.exception.reason, "subject_not_allowed")

    def test_expired_token_denied(self):
        c = _valid_claims()
        c["exp"] = 1_000_000 - 1000
        c["iat"] = 1_000_000 - 2000
        token = _make_token({"alg": "ES256"}, c)
        with self.assertRaises(VerificationError) as ctx:
            self._verify(token)
        self.assertEqual(ctx.exception.reason, "token_expired")

    def test_iat_in_future_denied(self):
        c = _valid_claims()
        c["iat"] = 1_000_000 + 5000
        token = _make_token({"alg": "ES256"}, c)
        with self.assertRaises(VerificationError) as ctx:
            self._verify(token)
        self.assertEqual(ctx.exception.reason, "iat_out_of_window")

    def test_nbf_in_future_denied(self):
        c = _valid_claims()
        c["nbf"] = 1_000_000 + 5000
        token = _make_token({"alg": "ES256"}, c)
        with self.assertRaises(VerificationError) as ctx:
            self._verify(token)
        self.assertEqual(ctx.exception.reason, "token_not_yet_valid")

    def test_missing_claims_denied(self):
        for drop in ("iss", "aud", "sub", "jti", "iat", "exp"):
            c = _valid_claims()
            del c[drop]
            token = _make_token({"alg": "ES256"}, c)
            with self.assertRaises(VerificationError):
                self._verify(token)

    def test_malformed_token_denied(self):
        for bad in ("not-a-jwt", "a.b", "a.b.c.d", "", "..", "@.@.@"):
            with self.assertRaises(VerificationError):
                self._verify(bad)


# ---------------------------------------------------------------------------
# No-value-echo property — the error must never leak the token or a claim.
# ---------------------------------------------------------------------------
class TestNoValueEcho(unittest.TestCase):
    def test_error_reason_is_closed_enum_no_token_echo(self):
        secret_jti = "SUPER-SECRET-JTI-DO-NOT-LEAK"
        c = _valid_claims(jti=secret_jti)
        c["iss"] = "https://evil.example"  # force a denial
        token = _make_token({"alg": "ES256"}, c)
        try:
            verify_oidc_token(
                token,
                expected_issuer="https://issuer.example",
                expected_audience="key-broker",
                nonce_cache=NonceCache(time_fn=FakeClock()),
                verify_signature=_accept_all,
                now_fn=lambda: 1_000_000.0,
            )
            self.fail("expected denial")
        except VerificationError as exc:
            blob = str(exc) + "!" + repr(exc) + "!" + exc.reason
            self.assertNotIn(secret_jti, blob)
            self.assertNotIn(token, blob)
            self.assertNotIn("evil.example", blob)
            self.assertEqual(exc.reason, "issuer_mismatch")

    def test_disallowed_alg_error_does_not_echo_header(self):
        token = _make_token({"alg": "HS256", "kid": "leak-me-please"}, _valid_claims())
        try:
            parse_and_check = parse_jws_header(token)
            enforce_alg_allowlist(parse_and_check)
            self.fail("expected denial")
        except VerificationError as exc:
            self.assertNotIn("HS256", str(exc) + repr(exc))
            self.assertNotIn("leak-me-please", str(exc) + repr(exc))
            self.assertEqual(exc.reason, "disallowed_alg")


class TestThumbprint(unittest.TestCase):
    def test_thumbprint_is_unpadded_b64url(self):
        tp = access_token_thumbprint("an-access-token")
        self.assertNotIn("=", tp)
        self.assertNotIn("+", tp)
        self.assertNotIn("/", tp)
        # deterministic
        self.assertEqual(tp, access_token_thumbprint("an-access-token"))


if __name__ == "__main__":
    unittest.main()
