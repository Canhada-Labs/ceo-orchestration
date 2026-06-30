"""Unit tests for mcp-server/auth.py — HMAC bearer + ACL + CORS + secret loader.

ADR-042 §Auth.1-§Auth.6. Tests cover:
- parse_bearer / parse_token (4 malformed shapes minimum)
- compute_hmac determinism
- verify_hmac (hmac.compare_digest path)
- verify_timestamp_skew
- load_client_registry (valid + malformed settings.json)
- check_acl (empty / wildcard / missing / present)
- check_cors (stdio path + HTTP default-deny + exact match + wildcard reject)
- load_secret (perms check + missing + wrong perms + symlink reject + size bounds)
- hash_client_id

Every test subclasses TestEnvContext (xdist-safe).
"""

from __future__ import annotations

import hashlib
import hmac as _hmac
import json
import os
import sys
import unittest
from pathlib import Path

# Bootstrap sys.path so _lib + mcp-server modules import cleanly.
_TESTS_DIR = Path(__file__).resolve().parent
_SERVER_DIR = _TESTS_DIR.parent
_CLAUDE_DIR = _SERVER_DIR.parent.parent
_HOOKS_DIR = _CLAUDE_DIR / "hooks"
for _p in (_HOOKS_DIR, _SERVER_DIR, _SERVER_DIR / "handlers"):
    _sp = str(_p)
    if _sp not in sys.path:
        sys.path.insert(0, _sp)

from _lib.testing import TestEnvContext  # noqa: E402

import auth  # type: ignore[import-not-found]  # noqa: E402


# Test secret used across the suite. 32 raw bytes; well within the
# load_secret 16-4096 byte band.
_SECRET = b"\x42" * 32


def _valid_token(client_id: str, nonce: str, ts_ms: int, secret: bytes) -> str:
    """Build a properly-signed token for tests (mirror ADR-042 signing)."""
    mac = auth.compute_hmac(client_id, nonce, ts_ms, secret)
    return f"v1.{client_id}.{nonce}.{mac}"


class TestParseBearer(TestEnvContext):
    """Authorization header parsing (case-insensitive, RFC 6750)."""

    def test_parse_bearer_standard(self):
        self.assertEqual(
            auth.parse_bearer("Bearer abc123"), "abc123"
        )

    def test_parse_bearer_case_insensitive_scheme(self):
        self.assertEqual(
            auth.parse_bearer("bearer xyz"), "xyz"
        )

    def test_parse_bearer_rejects_none(self):
        self.assertIsNone(auth.parse_bearer(None))

    def test_parse_bearer_rejects_empty(self):
        self.assertIsNone(auth.parse_bearer(""))

    def test_parse_bearer_rejects_no_token(self):
        # "Bearer " with nothing after the scheme.
        self.assertIsNone(auth.parse_bearer("Bearer "))

    def test_parse_bearer_rejects_basic_scheme(self):
        # Wrong auth scheme.
        self.assertIsNone(auth.parse_bearer("Basic dXNlcjpwYXNz"))


class TestParseToken(TestEnvContext):
    """Token regex shape parsing — 4+ malformed shapes."""

    def test_parse_token_valid(self):
        client = "0123456789abcdef"
        nonce = "fedcba9876543210"
        mac = "a" * 32
        result = auth.parse_token(f"v1.{client}.{nonce}.{mac}")
        self.assertEqual(
            result, {"client_id": client, "nonce": nonce, "hmac": mac}
        )

    def test_parse_token_rejects_wrong_version(self):
        self.assertIsNone(
            auth.parse_token("v2.0123456789abcdef.0123456789abcdef." + "a" * 32)
        )

    def test_parse_token_rejects_uppercase_hex(self):
        self.assertIsNone(
            auth.parse_token("v1.ABCDEF0123456789.0123456789abcdef." + "a" * 32)
        )

    def test_parse_token_rejects_short_client_id(self):
        # 15 hex chars instead of 16 — fail closed.
        self.assertIsNone(
            auth.parse_token("v1.0123456789abcde.0123456789abcdef." + "a" * 32)
        )

    def test_parse_token_rejects_missing_segment(self):
        # Missing nonce segment.
        self.assertIsNone(auth.parse_token("v1.0123456789abcdef." + "a" * 32))

    def test_parse_token_rejects_extra_segment(self):
        self.assertIsNone(
            auth.parse_token(
                "v1.0123456789abcdef.0123456789abcdef." + "a" * 32 + ".extra"
            )
        )

    def test_parse_token_rejects_none_and_empty(self):
        self.assertIsNone(auth.parse_token(None))
        self.assertIsNone(auth.parse_token(""))
        self.assertIsNone(auth.parse_token("   "))


class TestComputeAndVerifyHmac(TestEnvContext):
    """Constant-time MAC verify; ensures compare_digest is used."""

    def test_compute_hmac_deterministic(self):
        a = auth.compute_hmac("0123456789abcdef", "1111222233334444", 1700000000000, _SECRET)
        b = auth.compute_hmac("0123456789abcdef", "1111222233334444", 1700000000000, _SECRET)
        self.assertEqual(a, b)
        self.assertEqual(len(a), 32)
        # Hex chars only.
        int(a, 16)

    def test_compute_hmac_matches_stdlib_truncated(self):
        body = b"0123456789abcdef" + b"1111222233334444" + b"1700000000000"
        expected = _hmac.new(_SECRET, body, hashlib.sha256).hexdigest()[:32]
        actual = auth.compute_hmac(
            "0123456789abcdef", "1111222233334444", 1700000000000, _SECRET
        )
        self.assertEqual(actual, expected)

    def test_verify_hmac_accepts_valid(self):
        mac = auth.compute_hmac("c" * 16, "n" * 16, 1700000000000, _SECRET)
        self.assertTrue(
            auth.verify_hmac(
                client_id="c" * 16,
                nonce="n" * 16,
                timestamp_ms=1700000000000,
                secret=_SECRET,
                candidate_hmac=mac,
            )
        )

    def test_verify_hmac_rejects_wrong_secret(self):
        mac = auth.compute_hmac("c" * 16, "n" * 16, 1700000000000, _SECRET)
        self.assertFalse(
            auth.verify_hmac(
                client_id="c" * 16,
                nonce="n" * 16,
                timestamp_ms=1700000000000,
                secret=b"\x99" * 32,
                candidate_hmac=mac,
            )
        )

    def test_verify_hmac_rejects_empty_inputs(self):
        self.assertFalse(
            auth.verify_hmac(
                client_id="c" * 16,
                nonce="n" * 16,
                timestamp_ms=1700000000000,
                secret=b"",
                candidate_hmac="abc",
            )
        )
        self.assertFalse(
            auth.verify_hmac(
                client_id="c" * 16,
                nonce="n" * 16,
                timestamp_ms=1700000000000,
                secret=_SECRET,
                candidate_hmac="",
            )
        )

    def test_verify_hmac_uses_compare_digest(self):
        # Inspect the source line that does the comparison — fail if
        # someone refactors to == (timing-attack vulnerable).
        import inspect
        src = inspect.getsource(auth.verify_hmac)
        self.assertIn("compare_digest", src)


class TestTimestampSkew(TestEnvContext):
    """±60s skew window per ADR-042 §Auth.1."""

    def test_within_skew_allows(self):
        now = 1_700_000_000_000
        self.assertTrue(auth.verify_timestamp_skew(now - 30_000, now))
        self.assertTrue(auth.verify_timestamp_skew(now + 30_000, now))
        # Boundary — exactly 60s.
        self.assertTrue(auth.verify_timestamp_skew(now - 60_000, now))
        self.assertTrue(auth.verify_timestamp_skew(now + 60_000, now))

    def test_outside_skew_denies(self):
        now = 1_700_000_000_000
        self.assertFalse(auth.verify_timestamp_skew(now - 60_001, now))
        self.assertFalse(auth.verify_timestamp_skew(now + 60_001, now))

    def test_invalid_int_denies(self):
        self.assertFalse(auth.verify_timestamp_skew("not-a-number", 1))


class TestLoadClientRegistry(TestEnvContext):
    """Settings.json registry parse — fail-closed on malformed."""

    def test_load_registry_valid(self):
        settings = {
            "mcp_client_registry": {
                "0123456789abcdef": {
                    "handlers": ["list_skills", "get_skill"],
                    "cors_origins": ["https://app.example.com"],
                }
            }
        }
        path = self.write_project_file(
            ".claude/settings.json", json.dumps(settings)
        )
        registry = auth.load_client_registry(path)
        self.assertIn("0123456789abcdef", registry)
        self.assertEqual(
            registry["0123456789abcdef"]["handlers"],
            ["list_skills", "get_skill"],
        )

    def test_load_registry_missing_file(self):
        path = self.project_dir / ".claude" / "missing.json"
        self.assertEqual(auth.load_client_registry(path), {})

    def test_load_registry_malformed_json_fails_closed(self):
        path = self.write_project_file(
            ".claude/settings.json", "{ this is not json"
        )
        self.assertEqual(auth.load_client_registry(path), {})

    def test_load_registry_top_level_not_dict(self):
        path = self.write_project_file(
            ".claude/settings.json", json.dumps([1, 2, 3])
        )
        self.assertEqual(auth.load_client_registry(path), {})

    def test_load_registry_missing_top_key(self):
        path = self.write_project_file(
            ".claude/settings.json", json.dumps({"other_key": {}})
        )
        self.assertEqual(auth.load_client_registry(path), {})

    def test_load_registry_filters_non_dict_entries(self):
        # Tolerate ``_comment``-style annotations (string values).
        settings = {
            "mcp_client_registry": {
                "_comment": "this is a comment, ignore",
                "0123456789abcdef": {"handlers": ["list_skills"]},
            }
        }
        path = self.write_project_file(
            ".claude/settings.json", json.dumps(settings)
        )
        registry = auth.load_client_registry(path)
        self.assertNotIn("_comment", registry)
        self.assertIn("0123456789abcdef", registry)


class TestCheckAcl(TestEnvContext):
    """ACL allowlist semantics: empty/wildcard/missing/present."""

    def test_present_allows(self):
        entry = {"handlers": ["list_skills", "get_skill"]}
        self.assertTrue(auth.check_acl(entry, "list_skills"))

    def test_missing_denies(self):
        entry = {"handlers": ["list_skills"]}
        self.assertFalse(auth.check_acl(entry, "spawn_agent"))

    def test_empty_handlers_denies(self):
        # Empty allowlist = refuse all.
        self.assertFalse(auth.check_acl({"handlers": []}, "list_skills"))

    def test_missing_handlers_key_denies(self):
        self.assertFalse(auth.check_acl({}, "list_skills"))

    def test_none_entry_denies(self):
        self.assertFalse(auth.check_acl(None, "list_skills"))

    def test_wildcard_in_list_denies(self):
        # No wildcard accepted — fail closed.
        self.assertFalse(
            auth.check_acl({"handlers": ["*"]}, "list_skills")
        )

    def test_non_string_in_list_denies(self):
        self.assertFalse(
            auth.check_acl({"handlers": [123]}, "list_skills")
        )

    def test_handlers_not_list_denies(self):
        self.assertFalse(
            auth.check_acl({"handlers": "list_skills"}, "list_skills")
        )


class TestCheckCors(TestEnvContext):
    """CORS default-deny: stdio + HTTP exact match only."""

    def test_stdio_no_cors_key_allowed(self):
        # Origin=None and no cors_origins → True (stdio).
        self.assertTrue(auth.check_cors({}, None))

    def test_http_no_origin_no_restriction_allowed(self):
        self.assertTrue(auth.check_cors({"cors_origins": []}, None))

    def test_http_no_origin_with_restriction_denied(self):
        self.assertFalse(
            auth.check_cors({"cors_origins": ["https://app.example.com"]}, None)
        )

    def test_http_exact_match_allowed(self):
        self.assertTrue(
            auth.check_cors(
                {"cors_origins": ["https://app.example.com"]},
                "https://app.example.com",
            )
        )

    def test_http_origin_mismatch_denied(self):
        self.assertFalse(
            auth.check_cors(
                {"cors_origins": ["https://app.example.com"]},
                "https://evil.example.com",
            )
        )

    def test_wildcard_rejected(self):
        # `*` MUST be refused outright.
        self.assertFalse(
            auth.check_cors({"cors_origins": ["*"]}, "https://anything.com")
        )

    def test_null_origin_rejected(self):
        # `"null"` origin (file://, sandboxed iframe) MUST be refused.
        self.assertFalse(
            auth.check_cors({"cors_origins": ["null"]}, "null")
        )

    def test_malformed_cors_config_denies(self):
        # cors_origins must be a list; non-list = malformed = deny.
        self.assertFalse(
            auth.check_cors({"cors_origins": "not-a-list"}, "https://x.com")
        )

    def test_none_entry_denies(self):
        self.assertFalse(auth.check_cors(None, "https://x.com"))


class TestLoadSecret(TestEnvContext):
    """Secret file loader — perms 0600 + size + symlink + path traversal."""

    def _seed_secret(
        self,
        client_id: str = "0123456789abcdef",
        data: bytes = _SECRET,
        mode: int = 0o600,
    ) -> Path:
        secrets_dir = self.project_dir / "state" / "mcp_client_secrets"
        secrets_dir.mkdir(parents=True, exist_ok=True)
        target = secrets_dir / f"{client_id}.key"
        target.write_bytes(data)
        os.chmod(str(target), mode)
        return target

    def test_load_secret_happy_path(self):
        self._seed_secret()
        loaded = auth.load_secret(self.project_dir, "0123456789abcdef")
        self.assertEqual(loaded, _SECRET)

    def test_load_secret_missing_returns_none(self):
        # No file at all.
        loaded = auth.load_secret(self.project_dir, "0123456789abcdef")
        self.assertIsNone(loaded)

    def test_load_secret_wrong_perms_returns_none(self):
        # Group-readable — fail-closed.
        self._seed_secret(mode=0o644)
        loaded = auth.load_secret(self.project_dir, "0123456789abcdef")
        self.assertIsNone(loaded)

    def test_load_secret_world_readable_returns_none(self):
        self._seed_secret(mode=0o604)
        loaded = auth.load_secret(self.project_dir, "0123456789abcdef")
        self.assertIsNone(loaded)

    def test_load_secret_too_small_returns_none(self):
        # 15 bytes — below the 16-byte floor.
        self._seed_secret(data=b"x" * 15)
        loaded = auth.load_secret(self.project_dir, "0123456789abcdef")
        self.assertIsNone(loaded)

    def test_load_secret_too_large_returns_none(self):
        # 4097 bytes — above the 4096 cap.
        self._seed_secret(data=b"x" * 4097)
        loaded = auth.load_secret(self.project_dir, "0123456789abcdef")
        self.assertIsNone(loaded)

    def test_load_secret_invalid_client_id_returns_none(self):
        # Non-hex client_id — defense-in-depth, even if registry catches first.
        loaded = auth.load_secret(self.project_dir, "../../../etc/passwd")
        self.assertIsNone(loaded)

    def test_load_secret_symlink_rejected(self):
        # Place real file outside, symlink it into the secrets dir.
        secrets_dir = self.project_dir / "state" / "mcp_client_secrets"
        secrets_dir.mkdir(parents=True, exist_ok=True)
        real = self.project_dir / "real_secret.bin"
        real.write_bytes(_SECRET)
        os.chmod(str(real), 0o600)
        link = secrets_dir / "0123456789abcdef.key"
        os.symlink(str(real), str(link))
        loaded = auth.load_secret(self.project_dir, "0123456789abcdef")
        self.assertIsNone(loaded)


class TestHashClientId(TestEnvContext):
    """Stable 16-char hash for audit fields (never the raw token)."""

    def test_hash_deterministic(self):
        a = auth.hash_client_id("0123456789abcdef")
        b = auth.hash_client_id("0123456789abcdef")
        self.assertEqual(a, b)
        self.assertEqual(len(a), 16)

    def test_hash_empty_input(self):
        self.assertEqual(auth.hash_client_id(""), "")

    def test_hash_differs_per_input(self):
        a = auth.hash_client_id("0123456789abcdef")
        b = auth.hash_client_id("fedcba9876543210")
        self.assertNotEqual(a, b)


if __name__ == "__main__":
    unittest.main()
