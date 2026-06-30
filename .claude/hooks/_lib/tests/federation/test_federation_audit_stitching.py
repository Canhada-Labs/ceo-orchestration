"""PLAN-099 Wave C.4 — cross-node audit-chain stitching tests (AC7).

When a node consumes another node's `/audit-summary`, every remote
event is tagged with `federation_origin` (the peer's DER fingerprint)
and `fed_correlation_id`. Investigators can grep on either tag to
trace events back to the originating node.
"""
from __future__ import annotations

import importlib.util
import sys
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
    raise RuntimeError("could not find " + name + ".py or " + name + ".py.draft")


def _load(name: str, p: Path):
    loader = SourceFileLoader(name, str(p))
    spec = importlib.util.spec_from_loader(name, loader)
    assert spec is not None
    mod = importlib.util.module_from_spec(spec)
    sys.modules[name] = mod
    loader.exec_module(mod)
    return mod


audit_chain = _load("audit_chain", _resolve("audit_chain"))


class TestStitching(unittest.TestCase):

    PEER_FPR = "a" * 64

    def test_remote_summary_each_event_tagged(self):
        # Simulate a remote /audit-summary response with 3 events.
        remote_events = [
            {"action": "agent_spawn", "session_id": "s1"},
            {"action": "veto_triggered", "session_id": "s1"},
            {"action": "skill_patch_applied", "session_id": "s2"},
        ]
        correlation = audit_chain.generate_correlation_id()
        tagged = [
            audit_chain.tag_remote_event(
                ev,
                federation_origin=self.PEER_FPR,
                correlation_id=correlation,
            )
            for ev in remote_events
        ]
        for ev in tagged:
            self.assertEqual(ev["federation_origin"], self.PEER_FPR)
            self.assertEqual(ev["fed_correlation_id"], correlation)
            # Original payload preserved.
            self.assertIn("action", ev)

    def test_correlation_id_propagates_across_local_emits(self):
        # The server side stamps its own emit (e.g.,
        # federation_connection_accepted) with the same correlation id
        # extracted from the request header.
        cid = audit_chain.generate_correlation_id()
        local_emit = audit_chain.stamp_local_with_correlation(
            {"action": "federation_connection_accepted", "peer_id": "p1"},
            cid,
        )
        self.assertEqual(local_emit["fed_correlation_id"], cid)

    def test_round_trip_correlation_match(self):
        # End-to-end: a correlation id flows through (a) the server's
        # accepted emit, (b) the audit-summary response wrap, and (c)
        # the client's stitching of each remote event.
        cid = audit_chain.generate_correlation_id()

        # (a) server-side emit
        server_emit = audit_chain.stamp_local_with_correlation(
            {"action": "federation_connection_accepted", "peer_id": "p2"},
            cid,
        )
        # (b) client receives 1 remote event
        remote_event = {"action": "veto_triggered", "session_id": "s9"}
        # (c) client stitches
        stitched = audit_chain.tag_remote_event(
            remote_event,
            federation_origin=self.PEER_FPR,
            correlation_id=cid,
        )

        # The correlation id is consistent across (a) + (c).
        self.assertEqual(
            server_emit["fed_correlation_id"],
            stitched["fed_correlation_id"],
        )

    def test_upstream_attribution_preserved(self):
        # Federation-of-federations: a node that re-publishes events it
        # received from another node MUST NOT overwrite the upstream
        # attribution.
        original = {
            "action": "agent_spawn",
            "federation_origin": "upstream-fpr",
            "fed_correlation_id": "upstream-cid",
        }
        re_published = audit_chain.tag_remote_event(
            original,
            federation_origin="our-fpr",
            correlation_id="our-cid",
        )
        # The downstream tags do NOT clobber upstream.
        self.assertEqual(re_published["federation_origin"], "upstream-fpr")
        self.assertEqual(re_published["fed_correlation_id"], "upstream-cid")


if __name__ == "__main__":
    unittest.main()
