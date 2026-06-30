"""PLAN-099 Wave A.5 / A.6 — Stage-2 sentinel verifier fixtures (AC22).

AC22 requires test fixtures for the SECOND stage of the 2-stage sentinel
verifier (`_lib.sentinel_signers.is_valid_signer`) failure modes:

- signer-expired
- signer-revoked
- signer-not-in-registry

These can't be tested by feeding bad GPG signatures because Stage 1
(`_lib.gpg_verify.verify_detached`) would reject before Stage 2 runs.
Instead, we monkey-patch `verify_detached` to return
``(True, owner_fpr, "")`` and exercise the registry-driven Stage-2
logic with controlled SignerRecord fixtures.

Tests:

- ``test_stage2_signer_expired`` — registry has Owner with `expires_at`
  in the past → fail-CLOSED with ``signer_invalid:expired:<iso>``.
- ``test_stage2_signer_revoked`` — registry has Owner with `revoked_at`
  set → fail-CLOSED with ``signer_invalid:revoked:<iso>``.
- ``test_stage2_signer_not_in_registry`` — empty registry → fail-CLOSED
  with ``signer_invalid:unknown_key``.
- ``test_stage2_signer_valid_passes`` — registry has Owner valid + not
  revoked + not expired → both stages return ``(True, "")``.
"""
from __future__ import annotations

import datetime as _dt
import importlib.util
import sys
import tempfile
import unittest
from importlib.machinery import SourceFileLoader
from pathlib import Path


def _repo_root() -> Path:
    cur = Path(__file__).resolve()
    for parent in [cur.parent, *cur.parents]:
        if (parent / ".claude").is_dir() and (parent / "VERSION").is_file():
            return parent
    raise RuntimeError("repo root not found from " + str(cur))


_REPO_ROOT = _repo_root()
_FED_CANONICAL = _REPO_ROOT / ".claude" / "hooks" / "_lib" / "federation"
_FED_DRAFT = _REPO_ROOT / ".claude" / "plans" / "PLAN-099" / "federation"


def _resolve(name: str) -> Path:
    canon = _FED_CANONICAL / "{0}.py".format(name)
    draft = _FED_DRAFT / "{0}.py.draft".format(name)
    if canon.exists():
        return canon
    if draft.exists():
        return draft
    raise RuntimeError("could not find " + name + ".py or .py.draft")


def _load(name: str, p: Path):
    loader = SourceFileLoader(name, str(p))
    spec = importlib.util.spec_from_loader(name, loader)
    assert spec is not None
    mod = importlib.util.module_from_spec(spec)
    sys.modules[name] = mod
    loader.exec_module(mod)
    return mod


identity = _load("federation_identity_stage2", _resolve("identity"))


OWNER_FPR = "0000000000000000000000000000000000000000"


def _write_registry(entries):
    """Write a transient signers registry JSON for is_valid_signer to load."""
    td = Path(tempfile.mkdtemp(prefix="fed_stage2_"))
    p = td / "sentinel-signers-registry.yaml"
    # Use JSON shape (sentinel_signers.load_registry falls back to JSON
    # when YAML parse fails) — simpler + deterministic for fixtures.
    import json
    p.write_text(json.dumps({"signers": entries}), encoding="utf-8")
    return td, p


def _stage1_always_ok(*args, **kwargs):
    """Monkey-patch substitute for verify_detached returning OK + Owner fpr."""
    return True, OWNER_FPR, ""


class TestStage2SignerFailureModes(unittest.TestCase):
    """AC22 Stage-2 fixtures — exercise is_valid_signer paths."""

    def setUp(self):
        # Resolve sentinel_signers / gpg_verify via sys.path probe so we
        # patch the same instance that identity.py imports lazily.
        hooks_dir = _REPO_ROOT / ".claude" / "hooks"
        if str(hooks_dir) not in sys.path:
            sys.path.insert(0, str(hooks_dir))
        from _lib import gpg_verify, sentinel_signers  # noqa: E402
        self._gpg_verify = gpg_verify
        self._signers = sentinel_signers
        # Monkey-patch verify_detached for the duration of each test —
        # restored in tearDown.
        self._orig_verify = gpg_verify.verify_detached
        gpg_verify.verify_detached = _stage1_always_ok

    def tearDown(self):
        self._gpg_verify.verify_detached = self._orig_verify

    def _call(self, registry_path: Path, now: _dt.datetime):
        # Use a fake signed/sig path — Stage 1 is patched, files don't
        # need to exist for the substitute.
        td = Path(tempfile.mkdtemp(prefix="fed_stage2_files_"))
        signed = td / "enabled.md"
        signed.write_text("ENABLED", encoding="utf-8")
        sig = td / "enabled.md.asc"
        sig.write_text("dummy-sig", encoding="utf-8")
        return identity.verify_enable_sentinel_pair(
            signed, sig, [OWNER_FPR],
            signer_registry_path=registry_path,
            now=now,
        )

    def test_stage2_signer_not_in_registry(self):
        # Registry has ONE entry but for a different key — Owner fpr is
        # absent. Forces is_valid_signer to return "unknown_key".
        # (Empty signers list would either raise RegistryParseError OR
        # return an empty dict depending on the parser; we sidestep that
        # ambiguity by registering an unrelated key.)
        td, p = _write_registry([{
            "key_id": "F" * 40,  # unrelated fpr
            "key_type": "hot",
            "created_at": "2026-01-01T00:00:00Z",
            "expires_at": "2027-01-01T00:00:00Z",
            "revoked_at": None,
            "notes": "test-unrelated",
        }])
        ok, reason = self._call(p, _dt.datetime(2026, 5, 17, tzinfo=_dt.timezone.utc))
        self.assertFalse(ok)
        self.assertTrue(
            reason.startswith("signer_invalid:unknown_key"),
            "expected signer_invalid:unknown_key, got {0!r}".format(reason),
        )

    def test_stage2_signer_expired(self):
        td, p = _write_registry([{
            "key_id": OWNER_FPR,
            "key_type": "hot",
            "created_at": "2026-01-01T00:00:00Z",
            "expires_at": "2026-02-01T00:00:00Z",  # in the past relative to test now
            "revoked_at": None,
            "notes": "test-expired",
        }])
        # Now is well past expires_at.
        ok, reason = self._call(p, _dt.datetime(2026, 5, 17, tzinfo=_dt.timezone.utc))
        self.assertFalse(ok)
        self.assertTrue(
            reason.startswith("signer_invalid:expired"),
            "expected signer_invalid:expired:..., got {0!r}".format(reason),
        )

    def test_stage2_signer_revoked(self):
        td, p = _write_registry([{
            "key_id": OWNER_FPR,
            "key_type": "hot",
            "created_at": "2026-01-01T00:00:00Z",
            "expires_at": "2027-01-01T00:00:00Z",  # would be valid by date
            "revoked_at": "2026-03-01T00:00:00Z",  # but revoked
            "notes": "test-revoked",
        }])
        ok, reason = self._call(p, _dt.datetime(2026, 5, 17, tzinfo=_dt.timezone.utc))
        self.assertFalse(ok)
        self.assertTrue(
            reason.startswith("signer_invalid:revoked"),
            "expected signer_invalid:revoked:..., got {0!r}".format(reason),
        )

    def test_stage2_signer_valid_passes_both_stages(self):
        td, p = _write_registry([{
            "key_id": OWNER_FPR,
            "key_type": "hot",
            "created_at": "2026-01-01T00:00:00Z",
            "expires_at": "2027-01-01T00:00:00Z",
            "revoked_at": None,
            "notes": "test-valid",
        }])
        ok, reason = self._call(p, _dt.datetime(2026, 5, 17, tzinfo=_dt.timezone.utc))
        self.assertTrue(ok, "expected ok=True, reason was: {0!r}".format(reason))
        self.assertEqual(reason, "")

    def test_stage2_missing_registry_file(self):
        # setUp patches `verify_detached` to always return OK + Owner fpr,
        # so Stage-1 succeeds and we reach Stage-2 with a nonexistent
        # registry path. Expected fail-CLOSED reason: ``signer_invalid:
        # registry_missing``.
        td = Path(tempfile.mkdtemp(prefix="fed_stage2_files_"))
        signed = td / "enabled.md"
        signed.write_text("ENABLED", encoding="utf-8")
        sig = td / "enabled.md.asc"
        sig.write_text("dummy-sig", encoding="utf-8")
        ok, reason = identity.verify_enable_sentinel_pair(
            signed, sig, [OWNER_FPR],
            signer_registry_path=Path("/nonexistent/registry.yaml"),
            now=_dt.datetime(2026, 5, 17, tzinfo=_dt.timezone.utc),
        )
        self.assertFalse(ok)
        self.assertEqual(reason, "signer_invalid:registry_missing")


if __name__ == "__main__":
    unittest.main()
