"""F4 — security-invariant suite for the HITL crypto rail.

The closing audit (F4) flagged that ``_lib/action_required.py`` ships in
the npm tarball with 0 dedicated test coverage: an adopter who arms the
rail (``CEO_HITL_RAIL=1``) gets unreviewed security crypto. This suite
closes that 0-coverage gap WITHOUT removing the module, asserting the
five must-fix security invariants documented in the module's own
docstring (PLAN-133 §3 doctrine):

1. **CSPRNG single-use** — a token is consumed AT MOST ONCE (replay of
   the same token after a successful consume is rejected).
2. **Replay-reject** — re-presenting a consumed token yields
   ``unknown_token`` (the atomic claim-and-delete burned it).
3. **Cross-session-reject** — a token minted in session A can never
   resume in session B (constant-time session-hash compare).
4. **Fail-CLOSED on expiry** — an expired token is rejected (``expired``)
   and never grants the action.
5. **No raw token persisted in cleartext** — only ``sha256(token)`` is
   ever written; the claim file (name AND body) and the redacted
   display form contain NO live token.

Plus the constant-time-compare invariant: the consume path uses
``hmac.compare_digest`` for both the action-id and session bindings.

Env isolation per repo convention: this test subclasses
``TestEnvContext`` (snapshots + restores every ``CEO_*``/``CLAUDE_*``/
``HOME`` var) and points ``CEO_HITL_RAIL_STORE_DIR`` at a per-test tmp
dir via ``mock.patch.dict`` — it NEVER assigns ``os.environ[...]``
directly and never touches the real claim store under the system temp
root.

Stdlib only. Python >= 3.9.
"""

from __future__ import annotations

import glob
import hashlib
import inspect
import os
from pathlib import Path
from unittest import mock

from _lib import action_required as ar  # noqa: E402
from _lib.testing import TestEnvContext  # noqa: E402


class ActionRequiredInvariantTests(TestEnvContext):
    """Assert the five security invariants of the HITL resume-token rail.

    Each test isolates the single-use claim store to a per-test tmp dir
    (under this test's already-isolated tmp tree) so claim files never
    land in the shared system-temp store and never leak between cases.
    """

    def setUp(self) -> None:
        super().setUp()
        # Per-test claim store under the isolated tmp tree. Created so the
        # module's _store_dir() resolves here, not the shared system temp.
        self._store_dir = self._tmp_root / "hitl-rail-store"
        self._store_dir.mkdir(parents=True, exist_ok=True)
        # mock.patch.dict (NOT os.environ[...]=) per repo env-hygiene gate.
        self._env_patch = mock.patch.dict(
            os.environ,
            {"CEO_HITL_RAIL_STORE_DIR": str(self._store_dir)},
        )
        self._env_patch.start()
        self.addCleanup(self._env_patch.stop)

    # -- helpers ------------------------------------------------------------

    def _mint_and_register(
        self,
        *,
        session_id: str = "sess-A",
        kind: str = "bash_command",
        summary: str = "rm -rf /tmp/scratch",
        ttl_seconds: int = 900,
    ) -> ar.HeldAction:
        held = ar.build_held_action(
            session_id=session_id,
            kind=kind,
            summary=summary,
            ttl_seconds=ttl_seconds,
        )
        self.assertTrue(
            ar.register_held_action(held),
            "register_held_action should succeed on a fresh CSPRNG token",
        )
        return held

    def _resume(self, held: ar.HeldAction, **overrides):
        req = ar.ResumeRequest(
            action_id=overrides.get("action_id", held.action_id),
            session_id=overrides.get("session_id", held.session_id),
            resume_token=overrides.get("resume_token", held.resume_token),
        )
        return ar.consume_resume_token(req, now=overrides.get("now"))

    # -- 1. single-use + 2. replay-reject -----------------------------------

    def test_single_use_then_replay_rejected(self) -> None:
        """First consume succeeds; a second consume of the same token is
        rejected as ``unknown_token`` (the single-use claim was burned)."""
        held = self._mint_and_register()

        first = self._resume(held)
        self.assertTrue(first.ok, f"first consume should grant; got {first.reason}")
        self.assertEqual(first.reason, "ok")
        self.assertEqual(first.action_id, held.action_id)

        replay = self._resume(held)
        self.assertFalse(replay.ok, "replay of a consumed token must be denied")
        self.assertEqual(replay.reason, "unknown_token")

    def test_token_unknown_before_registration(self) -> None:
        """A never-registered token resumes nothing (fail-CLOSED default)."""
        result = ar.consume_resume_token(
            ar.ResumeRequest(
                action_id="ar-nope",
                session_id="sess-A",
                resume_token="this-token-was-never-minted",
            )
        )
        self.assertFalse(result.ok)
        self.assertEqual(result.reason, "unknown_token")

    # -- 3. cross-session-reject --------------------------------------------

    def test_cross_session_rejected(self) -> None:
        """A token minted in session A cannot resume in session B."""
        held = self._mint_and_register(session_id="sess-A")
        result = self._resume(held, session_id="sess-B")
        self.assertFalse(result.ok, "cross-session resume must be denied")
        self.assertEqual(result.reason, "session_mismatch")

    def test_action_id_mismatch_rejected(self) -> None:
        """A token presented against a DIFFERENT action_id is rejected
        (cross-action token-swap guard)."""
        held = self._mint_and_register()
        result = self._resume(held, action_id="ar-some-other-action")
        self.assertFalse(result.ok)
        self.assertEqual(result.reason, "action_id_mismatch")

    # -- 4. fail-CLOSED on expiry -------------------------------------------

    def test_expired_token_fails_closed(self) -> None:
        """A token consumed after its expiry is rejected, never granted."""
        held = self._mint_and_register(ttl_seconds=5)
        # Consume one tick past expiry — fail-CLOSED.
        result = self._resume(held, now=held.expires_at + 1.0)
        self.assertFalse(result.ok, "expired token must never grant the action")
        self.assertEqual(result.reason, "expired")

    def test_malformed_request_rejected(self) -> None:
        """Non-ResumeRequest input and an empty token both fail CLOSED with
        ``malformed_request`` (no crash, no grant)."""
        bad_type = ar.consume_resume_token("not a ResumeRequest")  # type: ignore[arg-type]
        self.assertFalse(bad_type.ok)
        self.assertEqual(bad_type.reason, "malformed_request")

        empty_token = ar.consume_resume_token(
            ar.ResumeRequest(action_id="a", session_id="s", resume_token="")
        )
        self.assertFalse(empty_token.ok)
        self.assertEqual(empty_token.reason, "malformed_request")

    # -- 5. no raw token persisted in cleartext -----------------------------

    def test_no_raw_token_on_disk_in_cleartext(self) -> None:
        """The persisted claim (filename AND body) contains NO live token —
        only the sha256 of it is ever derivable, and the body never even
        stores that. Verifies the 'no raw token on disk' invariant."""
        held = self._mint_and_register()

        claim_files = glob.glob(str(self._store_dir / "claim-*.json"))
        self.assertEqual(
            len(claim_files), 1, "exactly one claim file should be persisted"
        )
        claim_path = Path(claim_files[0])

        # Raw token must not appear in the filename...
        self.assertNotIn(
            held.resume_token,
            claim_path.name,
            "raw resume_token leaked into the claim filename",
        )
        # ...nor anywhere in the claim body.
        body = claim_path.read_text(encoding="utf-8")
        self.assertNotIn(
            held.resume_token,
            body,
            "raw resume_token leaked into the claim file body",
        )
        # The filename is keyed on sha256(token); the body stores only a
        # session HASH, never the token or its hash.
        expected_sha = hashlib.sha256(
            held.resume_token.encode("utf-8")
        ).hexdigest()
        self.assertIn(
            expected_sha,
            claim_path.name,
            "claim filename should be keyed on sha256(token)",
        )
        self.assertNotIn(
            held.resume_token, expected_sha, "sanity: token != its own sha"
        )

    def test_redacted_display_drops_raw_token(self) -> None:
        """The audit/Owner-display form drops the live token entirely; only
        the non-secret token_sha256 correlator survives."""
        held = self._mint_and_register()
        display = held.to_display()
        self.assertNotIn("resume_token", display)
        self.assertNotIn(held.resume_token, str(display))
        self.assertEqual(display.get("token_sha256"), held.token_sha256)

        # held_action_to_json must likewise be token-free.
        serialized = ar.held_action_to_json(held)
        self.assertNotIn(held.resume_token, serialized)

        # The direct redactor entrypoint hard-drops the token under every spelling.
        redacted = ar.redact_for_emit(
            {
                "resume_token": held.resume_token,
                "token": held.resume_token,
                "raw_token": held.resume_token,
                "kind": "bash_command",
            }
        )
        self.assertNotIn("resume_token", redacted)
        self.assertNotIn("token", redacted)
        self.assertNotIn("raw_token", redacted)
        self.assertNotIn(held.resume_token, str(redacted))

    # -- constant-time compare invariant ------------------------------------

    def test_constant_time_compare_used(self) -> None:
        """Both trust bindings (action_id + session) go through a
        constant-time compare (hmac.compare_digest), not ``==``."""
        ct_src = inspect.getsource(ar._ct_eq)
        self.assertIn(
            "compare_digest",
            ct_src,
            "constant-time helper must use hmac.compare_digest",
        )
        # The consume path must route its bindings through _ct_eq (not a
        # raw == on the secret-derived hashes).
        consume_src = inspect.getsource(ar.consume_resume_token)
        self.assertIn("_ct_eq", consume_src)

    # -- CSPRNG entropy invariant -------------------------------------------

    def test_tokens_are_csprng_unique(self) -> None:
        """Minted tokens are unguessable CSPRNG values: high entropy and
        unique across mints (no counter/time-seeded collision)."""
        tokens = {
            ar.build_held_action(
                session_id="s", kind="other", summary="x"
            ).resume_token
            for _ in range(50)
        }
        self.assertEqual(len(tokens), 50, "every minted token must be unique")
        for tok in tokens:
            # secrets.token_urlsafe(32) -> ~43 url-safe chars (256 bits).
            self.assertGreaterEqual(
                len(tok), 40, "token entropy below the 256-bit floor"
            )


if __name__ == "__main__":  # pragma: no cover
    import unittest

    unittest.main()
