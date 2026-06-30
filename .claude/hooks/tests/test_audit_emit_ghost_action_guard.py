"""PLAN-113 Phase B B-STRUCTURAL + B5 — ghost-action leak guard.

This file discharges the "ghost-action leak" finding: before PLAN-113,
``audit_emit.emit_generic(action, **kwargs)`` validated ``action`` against
``_KNOWN_ACTIONS``, ran a long ``if/elif action == "..."`` scrub chain, then
called ``_write_event`` with NO terminal ``else`` — so any ``_KNOWN_ACTIONS``
member WITHOUT an explicit branch wrote its caller kwargs VERBATIM into the
HMAC-chained audit log. The ~25 federation actions emitted via
``_lib.federation.*._safe_emit(action, **fields)`` were the live instance of
this leak (peer-influenced fields written raw).

PLAN-113 closes the class with three structural changes in ``audit_emit``:

1. **Per-action scrub branches** for every LIVE federation action (Sec MF-3
   deny-by-default allowlist; the two path fields are re-hashed to 12-hex).
2. **A default-deny ``else``** — any registered action that is neither
   branched, RESERVED, nor a documented verbatim-passthrough has ALL caller
   kwargs dropped (``event = {"action": action}``).
3. **A ``_RESERVED_ACTIONS`` registry** (B5) mapping each registered-but-
   producer-less action to its gating ADR.

The tests below are MECHANICAL — they enumerate ``_KNOWN_ACTIONS`` at runtime
(so a future engineer cannot add a leaky action silently):

* ``TestDefaultDenyGuard`` — every action with NO scrub branch, NOT reserved,
  NOT in the passthrough set has its caller kwargs dropped (default-deny).
* ``TestKnownActionPartition`` — every ``_KNOWN_ACTIONS`` member is EXACTLY
  one of {branched, reserved, passthrough}; no member falls through
  unexpectedly to default-deny.
* ``TestReservedActionsRegistry`` — every ``_RESERVED_ACTIONS`` member has
  ZERO production caller, and the CI-guard: if one ever GROWS a production
  caller, its gating ADR MUST be in an ACCEPTED lifecycle state.
* ``TestFederationScrub`` — federation events keep their legit fields, drop a
  ghost field, and re-hash the two filesystem-path fields.

Stdlib-only, Python >= 3.9, ``from __future__ import annotations``.
"""

from __future__ import annotations

import ast
import inspect
import json
import os
import re
import unittest
from pathlib import Path
from typing import Dict, List, Optional, Set

from _lib import audit_emit  # noqa: E402
from _lib.testing import TestEnvContext  # noqa: E402


# ---------------------------------------------------------------------------
# Static analysis helpers (drift-safe — read the live source at test time)
# ---------------------------------------------------------------------------


def _branched_actions() -> Set[str]:
    """Return every action with an explicit ``action == "X"`` branch in
    ``emit_generic`` (parsed from the live source, so the test follows the
    code automatically)."""
    src = inspect.getsource(audit_emit.emit_generic)
    tree = ast.parse(src)
    out: Set[str] = set()
    for node in ast.walk(tree):
        if (
            isinstance(node, ast.Compare)
            and isinstance(node.left, ast.Name)
            and node.left.id == "action"
        ):
            for comp in node.comparators:
                if isinstance(comp, ast.Constant) and isinstance(comp.value, str):
                    out.add(comp.value)
    return out


_REPO_ROOT = Path(__file__).resolve().parents[3]


def _is_excluded_for_producer_scan(path: Path) -> bool:
    """True for files that must NOT count as a 'production caller'.

    Excludes: tests, staged/dead plan copies, sandbox snapshots, and VCS.
    """
    rel = str(path)
    parts = path.parts
    if any(p in ("tests", "__pycache__", ".git") for p in parts):
        return True
    if path.name.startswith("test_"):
        return True
    # Dead / staged copies live under .claude/plans/** (e.g. wave-d-staging,
    # PLAN-081/staging/phase-*, audit-v2/staged-wave-b). These are NOT live
    # producers.
    if f"{os.sep}.claude{os.sep}plans{os.sep}" in rel:
        return True
    if f"{os.sep}sandbox{os.sep}" in rel:
        return True
    return False


def _production_callers(action: str) -> List[str]:
    """Return ``rel_path:line`` for every LIVE call site that emits ``action``
    via ``emit_generic("action", ...)`` or ``_safe_emit("action", ...)``.

    Excludes tests + staged/dead plan copies + sandbox snapshots.
    """
    hits: List[str] = []
    for path in _REPO_ROOT.rglob("*.py"):
        if _is_excluded_for_producer_scan(path):
            continue
        try:
            tree = ast.parse(path.read_text(encoding="utf-8"), filename=str(path))
        except Exception:
            continue
        for node in ast.walk(tree):
            if not isinstance(node, ast.Call) or not node.args:
                continue
            fnc = node.func
            name: Optional[str] = None
            if isinstance(fnc, ast.Name):
                name = fnc.id
            elif isinstance(fnc, ast.Attribute):
                name = fnc.attr
            if name not in ("emit_generic", "_safe_emit"):
                continue
            a0 = node.args[0]
            if isinstance(a0, ast.Constant) and a0.value == action:
                rel = path.relative_to(_REPO_ROOT)
                hits.append(f"{rel}:{node.lineno}")
    return hits


_ADR_DIR = _REPO_ROOT / ".claude" / "adr"


def _adr_status(adr_id: str) -> Optional[str]:
    """Return the lifecycle status of an ADR id (e.g. ``ADR-133``), reading
    the YAML ``status:`` front-matter (or the ``**Status:**`` markdown form).

    Matches the canonical file for the id (prefers an exact ``<id>-`` stem so
    ``ADR-135`` does not accidentally match ``ADR-135-AMEND-1``).
    """
    candidates = sorted(_ADR_DIR.glob(f"{adr_id}-*.md"))
    # Prefer the file whose stem starts with the EXACT id token followed by a
    # non-digit / non-AMEND boundary (so ADR-135 != ADR-135-AMEND-1).
    exact: List[Path] = []
    for c in candidates:
        rest = c.name[len(adr_id):]
        # rest looks like "-<slug>.md" or "-AMEND-N-<slug>.md"
        if rest.startswith("-AMEND") and "AMEND" not in adr_id:
            continue
        exact.append(c)
    pick = exact[0] if exact else (candidates[0] if candidates else None)
    if pick is None:
        return None
    head = "\n".join(pick.read_text(encoding="utf-8").splitlines()[:40])
    m = re.search(r"(?im)^\s*status\s*:\s*([A-Za-z0-9_-]+)", head)
    if m:
        return m.group(1).strip().upper()
    m = re.search(r"(?im)^\s*\*\*status:\*\*\s*([A-Za-z0-9_-]+)", head)
    if m:
        return m.group(1).strip().upper()
    return None


_ACCEPTED_STATES = {"ACCEPTED", "ACCEPTED-AMENDED"}


# ---------------------------------------------------------------------------
# Test base — isolated audit log + reader
# ---------------------------------------------------------------------------


class _GuardBase(TestEnvContext):
    def _emit_and_read(self, action: str, **kwargs):
        audit_emit.emit_generic(action, **kwargs)
        log = Path(os.environ["CEO_AUDIT_LOG_PATH"])
        events = []
        if log.exists():
            for line in log.read_text(encoding="utf-8").splitlines():
                line = line.strip()
                if line:
                    events.append(json.loads(line))
        return events


# ---------------------------------------------------------------------------
# 1. Default-deny guard — the core leak-class assertion
# ---------------------------------------------------------------------------


class TestDefaultDenyGuard(_GuardBase):
    """Every action with NO branch, NOT reserved, NOT passthrough → default-deny."""

    GHOST = "_ghost_unsafe_field"
    GHOST_VALUE = "LEAK-should-never-persist"

    def test_unbranched_unreserved_nonpassthrough_actions_default_deny(self):
        branched = _branched_actions()
        reserved = set(audit_emit._RESERVED_ACTIONS)
        passthrough = set(audit_emit._EMIT_GENERIC_PASSTHROUGH)
        targets = sorted(
            a
            for a in audit_emit._KNOWN_ACTIONS
            if a not in branched and a not in reserved and a not in passthrough
        )
        # There may be zero such actions today (the set is fully partitioned),
        # in which case the partition test below is the real guard. If any
        # exist, each MUST default-deny.
        for action in targets:
            events = self._emit_and_read(action, **{self.GHOST: self.GHOST_VALUE})
            self.assertEqual(
                len(events), 1, f"{action}: expected exactly 1 event"
            )
            ev = events[0]
            self.assertNotIn(
                self.GHOST,
                ev,
                f"{action}: ghost field leaked into the audit log "
                f"(default-deny failed): {ev!r}",
            )
            self.assertEqual(ev["action"], action)

    def test_synthetic_unbranched_action_default_deny(self):
        """Even if every real action is partitioned, prove the ``else`` path
        works by monkeypatching a synthetic action into the known set + the
        ``_KNOWN_ACTIONS`` membership for one emit call."""
        synthetic = "plan113_synthetic_unhandled_action_xyz"
        orig_known = audit_emit._KNOWN_ACTIONS
        try:
            audit_emit._KNOWN_ACTIONS = set(orig_known) | {synthetic}
            events = self._emit_and_read(
                synthetic, secret_path="/home/me/.ssh/id_rsa", token="LEAK"
            )
        finally:
            audit_emit._KNOWN_ACTIONS = orig_known
        self.assertEqual(len(events), 1)
        ev = events[0]
        self.assertEqual(ev["action"], synthetic)
        self.assertNotIn("secret_path", ev)
        self.assertNotIn("token", ev)


# ---------------------------------------------------------------------------
# 2. Partition invariant — no _KNOWN_ACTIONS member is uncategorised
# ---------------------------------------------------------------------------


class TestKnownActionPartition(unittest.TestCase):
    def test_every_known_action_is_branched_reserved_or_passthrough(self):
        branched = _branched_actions()
        reserved = set(audit_emit._RESERVED_ACTIONS)
        passthrough = set(audit_emit._EMIT_GENERIC_PASSTHROUGH)
        uncategorised = sorted(
            a
            for a in audit_emit._KNOWN_ACTIONS
            if a not in branched and a not in reserved and a not in passthrough
        )
        self.assertEqual(
            uncategorised,
            [],
            "These _KNOWN_ACTIONS members are neither branched, reserved, nor "
            "passthrough — they will hit default-deny (caller kwargs dropped). "
            "Either give them a scrub branch or list them in "
            "_EMIT_GENERIC_PASSTHROUGH: " + repr(uncategorised),
        )

    def test_passthrough_and_branched_are_disjoint(self):
        branched = _branched_actions()
        passthrough = set(audit_emit._EMIT_GENERIC_PASSTHROUGH)
        overlap = sorted(branched & passthrough)
        self.assertEqual(
            overlap, [], f"action both branched AND passthrough: {overlap}"
        )

    def test_passthrough_and_reserved_are_disjoint(self):
        reserved = set(audit_emit._RESERVED_ACTIONS)
        passthrough = set(audit_emit._EMIT_GENERIC_PASSTHROUGH)
        overlap = sorted(reserved & passthrough)
        self.assertEqual(
            overlap, [], f"action both reserved AND passthrough: {overlap}"
        )

    def test_reserved_and_passthrough_are_registered(self):
        """The reserved + passthrough category sets must be subsets of
        _KNOWN_ACTIONS (no dangling category entry).

        (Branched actions are NOT asserted here: emit_generic also branches on
        a handful of registered-elsewhere ``ceo_boot_*`` / non-_KNOWN_ACTIONS
        names handled by their own producers — branched ⊆ known is not an
        invariant, but reserved/passthrough ⊆ known is.)
        """
        known = set(audit_emit._KNOWN_ACTIONS)
        for label, s in (
            ("reserved", set(audit_emit._RESERVED_ACTIONS)),
            ("passthrough", set(audit_emit._EMIT_GENERIC_PASSTHROUGH)),
        ):
            missing = sorted(s - known)
            self.assertEqual(
                missing, [], f"{label} entries not in _KNOWN_ACTIONS: {missing}"
            )


# ---------------------------------------------------------------------------
# 3. RESERVED_ACTIONS registry — zero producers + ADR gate
# ---------------------------------------------------------------------------


class TestReservedActionsRegistry(unittest.TestCase):
    def test_every_reserved_action_is_registered_known(self):
        known = set(audit_emit._KNOWN_ACTIONS)
        for action in audit_emit._RESERVED_ACTIONS:
            self.assertIn(
                action, known, f"reserved action {action!r} not in _KNOWN_ACTIONS"
            )

    def test_every_reserved_action_has_zero_production_caller(self):
        for action in sorted(audit_emit._RESERVED_ACTIONS):
            callers = _production_callers(action)
            self.assertEqual(
                callers,
                [],
                f"RESERVED action {action!r} has gained a production caller "
                f"({callers}). Either remove it from _RESERVED_ACTIONS (it is "
                f"now live — give it a scrub branch) or revert the producer. "
                f"See the CI-guard test for the ADR requirement.",
            )

    def test_reserved_action_gating_adrs_resolve(self):
        """Each reserved action's gating ADR must exist + be parseable."""
        for action, adr_id in sorted(audit_emit._RESERVED_ACTIONS.items()):
            status = _adr_status(adr_id)
            self.assertIsNotNone(
                status,
                f"{action}: gating ADR {adr_id} not found / no status front-matter",
            )

    def test_ci_guard_live_reserved_action_requires_accepted_adr(self):
        """CI-guard: IF a reserved action ever has a production caller, its
        gating ADR MUST be in an ACCEPTED lifecycle state — else FAIL.

        Today every reserved action is producer-less (asserted above), so this
        is a no-op pass. When a future change wires a producer, this test
        forces the gating ADR to be ACCEPTED before the wiring can land green.
        """
        for action, adr_id in sorted(audit_emit._RESERVED_ACTIONS.items()):
            callers = _production_callers(action)
            if not callers:
                continue  # producer-less — gate not yet active
            status = _adr_status(adr_id)
            self.assertIn(
                status,
                _ACCEPTED_STATES,
                f"{action} has a production caller ({callers}) but its gating "
                f"ADR {adr_id} status is {status!r} (must be ACCEPTED).",
            )


# ---------------------------------------------------------------------------
# 4. Federation scrub — legit fields survive, ghost dropped, paths hashed
# ---------------------------------------------------------------------------


class TestFederationScrub(_GuardBase):
    GHOST = "_ghost_unsafe_field"

    def test_peer_registered_keeps_legit_drops_ghost(self):
        events = self._emit_and_read(
            "federation_peer_registered",
            peer_id="peerA",
            route="/federation/peer-register",
            scopes_count=2,
            spki_fingerprint_prefix="abcd1234",
            **{self.GHOST: "LEAK"},
        )
        self.assertEqual(len(events), 1)
        ev = events[0]
        self.assertEqual(ev["peer_id"], "peerA")
        self.assertEqual(ev["scopes_count"], 2)
        self.assertEqual(ev["spki_fingerprint_prefix"], "abcd1234")
        self.assertNotIn(self.GHOST, ev)

    def test_source_path_is_hashed_not_raw(self):
        raw_path = "/home/secret-user/.claude/federation/peers.yaml"
        events = self._emit_and_read(
            "federation_peer_list_reloaded",
            peer_id="peerB",
            peer_count=3,
            reload_reason="content_changed",
            source_path=raw_path,
        )
        self.assertEqual(len(events), 1)
        ev = events[0]
        self.assertIn("source_path", ev)
        self.assertNotEqual(ev["source_path"], raw_path)
        self.assertNotIn("/", ev["source_path"])
        self.assertEqual(len(ev["source_path"]), 12)
        self.assertTrue(all(c in "0123456789abcdef" for c in ev["source_path"]))

    def test_sentinel_path_is_hashed_not_raw(self):
        raw_path = "/home/secret-user/.claude/federation/write-enabled.md.asc"
        events = self._emit_and_read(
            "federation_write_disabled_sentinel_invalid",
            reason_code="gpg_verify_failed",
            sentinel_path=raw_path,
        )
        self.assertEqual(len(events), 1)
        ev = events[0]
        self.assertNotEqual(ev["sentinel_path"], raw_path)
        self.assertEqual(len(ev["sentinel_path"]), 12)

    def test_reserved_federation_action_scrub_branch_drops_ghost(self):
        """A reserved destructive federation action still has a defense-in-
        depth scrub branch (allowlist-bounded if an accidental caller appears)."""
        events = self._emit_and_read(
            "federation_key_floor_rejected",
            peer_id="peerC",
            key_type="RSA",
            key_bits=1024,
            reason_code="key_too_small",
            **{self.GHOST: "LEAK"},
        )
        self.assertEqual(len(events), 1)
        ev = events[0]
        self.assertEqual(ev["peer_id"], "peerC")
        self.assertEqual(ev["key_bits"], 1024)
        self.assertNotIn(self.GHOST, ev)

    def test_message_storm_keeps_ip_prefix_drops_full_ip_field(self):
        events = self._emit_and_read(
            "federation_message_storm_detected",
            peer_id="peerD",
            route="/audit-event",
            ip_prefix="203.0.113.0/24",
            hits_in_window=5,
            window_seconds=900,
            client_ip="203.0.113.42",  # NOT in allowlist → must drop
        )
        self.assertEqual(len(events), 1)
        ev = events[0]
        self.assertEqual(ev["ip_prefix"], "203.0.113.0/24")
        self.assertNotIn("client_ip", ev)


if __name__ == "__main__":
    unittest.main()
