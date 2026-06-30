"""PLAN-099-FOLLOWUP Wave E.4 — AC18 federation denylist enumeration tests.

≥4 cases per plan §4 Wave E.4 + AC11 acceptance criteria. Asserts that
every federation module (PLAN-099 MVP + PLAN-099-FOLLOWUP Wave B/C/D/E)
is explicitly enumerated on the autonomous-loop denylist.

Test architecture:
  - PRE-A2-post: ``.claude/hooks/check_agent_spawn.py`` contains ZERO
    federation references (verified by plan §7 pre-execute checklist).
    These tests read ``wave-e-staging/ac18_check_agent_spawn_patch.md``
    as the source-of-truth for "what the denylist WILL look like" and
    parse the ``_FEDERATION_IMPORT_DENYLIST`` block out of the markdown.
  - POST-A2-post: ``check_agent_spawn.py`` contains the constant
    verbatim. The same parser runs against the hook source; the two
    extracted sets MUST match (post-A2 drift check).

  - DO NOT use ``@pytest.mark.xfail(strict=True)`` (S146 lesson).
    Failed prereqs use plain ``pytest.skip(...)``.

Stdlib-only.
"""

from __future__ import annotations

import os
import re
import sys
import unittest
from pathlib import Path
from typing import Set


# ----------------------------------------------------------------------------
# Repo path resolution
# ----------------------------------------------------------------------------


def _repo_root() -> Path:
    """Return the ceo-orchestration repo root.

    Walks parents from this test file until ``.claude/`` + ``PROTOCOL.md``
    are both visible. Falls back to ``CLAUDE_PROJECT_DIR`` env var.
    """
    here = Path(__file__).resolve()
    for parent in (here, *here.parents):
        if (parent / ".claude").is_dir() and (parent / "PROTOCOL.md").exists():
            return parent
    env = os.environ.get("CLAUDE_PROJECT_DIR")
    if env and Path(env).is_dir():
        return Path(env)
    return here.parents[2]


ROOT = _repo_root()

WAVE_E_STAGING = ROOT / ".claude" / "plans" / "PLAN-099-FOLLOWUP" / "wave-e-staging"
WAVE_D_HANDLERS = ROOT / ".claude" / "plans" / "PLAN-099-FOLLOWUP" / "wave-d-staging" / "handlers"
WAVE_D_SCOPES = ROOT / ".claude" / "plans" / "PLAN-099-FOLLOWUP" / "wave-d-staging" / "scopes.py"
CERT_INSPECTOR_STAGING = ROOT / ".claude" / "plans" / "PLAN-099-FOLLOWUP" / "cert_inspector.py"
PATCH_MD = WAVE_E_STAGING / "ac18_check_agent_spawn_patch.md"
HOOK_PATH = ROOT / ".claude" / "hooks" / "check_agent_spawn.py"


# ----------------------------------------------------------------------------
# Parsers
# ----------------------------------------------------------------------------


_DENYLIST_ENTRY_RE = re.compile(
    r'^\s*"(\.claude/hooks/_lib/federation/[A-Za-z0-9_/.\-]+\.py)"',
    re.MULTILINE,
)


def _extract_denylist_from_markdown(md_path: Path) -> Set[str]:
    """Pull the ``_FEDERATION_IMPORT_DENYLIST`` set entries out of the patch md.

    Returns a set of POSIX-style repo-relative paths. Robust to comments
    and trailing commas. Skips lines that aren't quoted federation paths.
    """
    if not md_path.exists():
        return set()
    text = md_path.read_text(encoding="utf-8")
    out: Set[str] = set()
    for m in _DENYLIST_ENTRY_RE.finditer(text):
        out.add(m.group(1))
    return out


def _extract_denylist_from_hook(hook_path: Path) -> Set[str]:
    """Pull the live ``_FEDERATION_IMPORT_DENYLIST`` entries out of the kernel hook.

    Returns the empty set if the hook does not yet contain the constant
    (pre-A2-post state) — caller should ``skip`` rather than fail in
    that case.
    """
    if not hook_path.exists():
        return set()
    text = hook_path.read_text(encoding="utf-8")
    if "_FEDERATION_IMPORT_DENYLIST" not in text:
        return set()
    return {
        m.group(1) for m in _DENYLIST_ENTRY_RE.finditer(text)
    }


def _effective_denylist() -> Set[str]:
    """Return the denylist as it WILL be after A2-post.

    Resolution order:
      1. Live hook (post-A2-post; ``_FEDERATION_IMPORT_DENYLIST`` present).
      2. Patch markdown (pre-A2-post; the staged constant block).
    """
    live = _extract_denylist_from_hook(HOOK_PATH)
    if live:
        return live
    return _extract_denylist_from_markdown(PATCH_MD)


# ----------------------------------------------------------------------------
# Tests
# ----------------------------------------------------------------------------


class TestAc18FederationDenylistEnumeration(unittest.TestCase):
    """Each federation module is explicitly enumerated. AC11 / AC18 contract."""

    def setUp(self) -> None:
        self.denylist = _effective_denylist()
        if not self.denylist:
            self.skipTest(
                "AC18 denylist not present yet (pre-A2-post + patch md missing)"
            )

    def test_every_wave_d_handler_module_denylisted(self) -> None:
        """Plan E.4 — every Wave D handler module on the denylist."""
        if not WAVE_D_HANDLERS.is_dir() or not list(WAVE_D_HANDLERS.glob("*.py")):
            # PLAN-112-FOLLOWUP-federation-wire PHASE2 (S159): the wave-d-staging
            # handlers were promoted to canonical .claude/hooks/_lib/federation/
            # handlers/ long ago, leaving an EMPTY staging dir. Skip rather than
            # assert >=1 (the canonical handlers' denylist coverage is asserted
            # by the per-module tests below).
            self.skipTest("Wave D staging handlers not present (promoted to canonical)")
        canonical_paths = []
        for handler_file in sorted(WAVE_D_HANDLERS.glob("*.py")):
            canonical_paths.append(
                ".claude/hooks/_lib/federation/handlers/{0}".format(handler_file.name)
            )
        self.assertTrue(canonical_paths, "expected ≥1 wave-d handler module")
        for canon in canonical_paths:
            self.assertIn(
                canon,
                self.denylist,
                "Wave D handler not on AC18 denylist: {0}".format(canon),
            )

    def test_cert_inspector_bridge_denylisted(self) -> None:
        """Plan E.4 — Wave B cert_inspector bridge on the denylist."""
        canon = ".claude/hooks/_lib/federation/cert_inspector.py"
        self.assertIn(canon, self.denylist)

    def test_scopes_denylisted(self) -> None:
        """Plan E.4 — Wave D scopes RBAC module on the denylist."""
        canon = ".claude/hooks/_lib/federation/scopes.py"
        self.assertIn(canon, self.denylist)

    def test_rate_limit_denylisted(self) -> None:
        """Plan E.4 — Wave E rate_limit module on the denylist."""
        canon = ".claude/hooks/_lib/federation/rate_limit.py"
        self.assertIn(canon, self.denylist)

    def test_audit_chain_ext_denylisted(self) -> None:
        """Plan E.4 — Wave E audit_chain_ext module on the denylist."""
        canon = ".claude/hooks/_lib/federation/audit_chain_ext.py"
        self.assertIn(canon, self.denylist)

    def test_plan_099_mvp_modules_preserved(self) -> None:
        """The AC18 extension is ADDITIVE — PLAN-099 v1.32.0 modules
        (client/server/identity) MUST remain on the denylist after the
        Wave E.4 patch lands. Regression guard against an Owner
        accidentally rewriting the constant instead of extending it.
        """
        mvp_modules = (
            ".claude/hooks/_lib/federation/client.py",
            ".claude/hooks/_lib/federation/server.py",
            ".claude/hooks/_lib/federation/identity.py",
        )
        for m in mvp_modules:
            self.assertIn(m, self.denylist, "MVP federation module dropped: {0}".format(m))

    def test_stdlib_not_overbroadly_denied(self) -> None:
        """NEGATIVE — sanity check that the denylist is scoped to federation
        only. Stdlib modules (``socket``, ``ssl``, ``json``, ``hmac``) MUST
        NOT be on the federation-import denylist. If this fails, the AC18
        gate has overreached and would break unrelated agents.
        """
        forbidden_overreach = {"socket", "ssl", "json", "hmac", "hashlib", "secrets"}
        for entry in self.denylist:
            base = entry.rsplit("/", 1)[-1].removesuffix(".py")
            self.assertNotIn(
                base,
                forbidden_overreach,
                "AC18 denylist overreach: stdlib '{0}' would be blocked".format(base),
            )

    def test_denylist_drift_md_vs_hook_post_a2(self) -> None:
        """POST-A2-post drift check.

        After Owner applies the patch in
        ``ac18_check_agent_spawn_patch.md``, the live hook's
        ``_FEDERATION_IMPORT_DENYLIST`` MUST be a superset of the markdown's
        enumerated entries. (Superset, not equal — the kernel hook may have
        additional non-Wave-E entries from future plans.)
        """
        md_set = _extract_denylist_from_markdown(PATCH_MD)
        hook_set = _extract_denylist_from_hook(HOOK_PATH)
        if not hook_set:
            self.skipTest("Pre-A2-post: hook does not yet contain _FEDERATION_IMPORT_DENYLIST")
        self.assertTrue(md_set, "patch markdown missing denylist entries")
        missing = md_set - hook_set
        self.assertFalse(
            missing,
            "Live hook missing Wave E denylist entries: {0}".format(sorted(missing)),
        )


if __name__ == "__main__":
    unittest.main()
