"""Stdlib-only deterministic property tests for chain invariants (PLAN-086 Wave G, M-12 fold).

Trade-off rationale: ``hypothesis`` is intentionally excluded. These tests use
``random.seed(42)`` + 200 iterations for deterministic, reproducible property
coverage without adding a pip dependency. Satisfies ADR-115 anti-churn + C7/M-12.

Invariants verified:
1. HMAC-chain determinism: same (key, prev_hmac, entry) → same HMAC.
2. HMAC-chain sensitivity: bit-flip in prev_hmac yields different HMAC.
3. Sentinel-discovery glob coverage: every planted approved.md discovered.
4. Canonical-guard idempotence: same (tool, params, repo_root) → same dict.
"""

from __future__ import annotations

import random
import sys
import tempfile
import unittest
from pathlib import Path
from typing import Any, Dict

_HOOKS_DIR = Path(__file__).resolve().parent.parent
sys.path.insert(0, str(_HOOKS_DIR))

from _lib import audit_hmac  # noqa: E402


def _random_entry(rng: random.Random, i: int) -> Dict[str, Any]:
    return {
        "action": rng.choice(["agent_spawn", "audit_log_rotate", "benchmark_run"]),
        "ts": "2026-05-{day:02d}T10:{min:02d}:00Z".format(
            day=(i % 28) + 1, min=i % 60
        ),
        "seq": i,
        "hook": "test_property",
    }


class TestHmacChainDeterminism(unittest.TestCase):
    """Invariants 1+2 — 200 seeded iterations each."""

    def test_hmac_determinism_200_iters(self) -> None:
        rng = random.Random(42)
        for i in range(200):
            key = bytes(rng.randint(0, 255) for _ in range(audit_hmac.KEY_BYTES))
            prev_hmac = bytes(rng.randint(0, 255) for _ in range(audit_hmac.HMAC_BYTES))
            entry = _random_entry(rng, i)
            a = audit_hmac.compute_entry_hmac(key, prev_hmac, entry)
            b = audit_hmac.compute_entry_hmac(key, prev_hmac, entry)
            self.assertEqual(a, b, f"iter {i}: not deterministic")
            self.assertEqual(len(a), audit_hmac.HMAC_BYTES)

    def test_hmac_chain_bit_flip_200_iters(self) -> None:
        rng = random.Random(42)
        collisions = 0
        for i in range(200):
            key = bytes(rng.randint(0, 255) for _ in range(audit_hmac.KEY_BYTES))
            prev_hmac = bytes(rng.randint(0, 255) for _ in range(audit_hmac.HMAC_BYTES))
            entry = _random_entry(rng, i)
            orig = audit_hmac.compute_entry_hmac(key, prev_hmac, entry)
            flip_idx = i % audit_hmac.HMAC_BYTES
            mutated = (
                prev_hmac[:flip_idx]
                + bytes([prev_hmac[flip_idx] ^ 0x01])
                + prev_hmac[flip_idx + 1:]
            )
            mutated_hmac = audit_hmac.compute_entry_hmac(key, mutated, entry)
            if orig == mutated_hmac:
                collisions += 1
        self.assertEqual(collisions, 0, f"HMAC collisions on bit-flip: {collisions}/200")


class TestSentinelDiscoveryGlobCoverage(unittest.TestCase):
    """Invariant 3 — _find_sentinels discovers every planted approved.md."""

    def test_glob_discovers_planted_200_rounds(self) -> None:
        from check_canonical_edit import _find_sentinels
        rng = random.Random(42)
        with tempfile.TemporaryDirectory() as tmp:
            tmp_root = Path(tmp)
            plans_base = tmp_root / ".claude" / "plans"
            plans_base.mkdir(parents=True)
            planted = []
            for i in range(200):
                plan_n = rng.randint(1, 999)
                round_n = rng.randint(1, 50)
                sd = plans_base / f"PLAN-{plan_n:03d}" / "architect" / f"round-{round_n}"
                sd.mkdir(parents=True, exist_ok=True)
                sf = sd / "approved.md"
                if not sf.exists():
                    sf.write_text("placeholder\n", encoding="utf-8")
                    planted.append(sf)
            discovered = _find_sentinels(tmp_root)
            discovered_set = {str(p.resolve()) for p in discovered}
            for p in planted:
                self.assertIn(str(p.resolve()), discovered_set, f"missed: {p}")


class TestCanonicalGuardIdempotence(unittest.TestCase):
    """Invariant 4 — check_mcp_call same input → same dict."""

    def test_idempotence_200_iters(self) -> None:
        from _lib.mcp.canonical_guard import check_mcp_call
        rng = random.Random(42)
        tools = [
            "mcp__codex__apply_patch",
            "mcp__codex__write_file",
            "mcp__filesystem__write_file",
            "bash_execute",
            "mcp__unknown__noop",
        ]
        paths = [
            ".claude/hooks/_lib/redact.py",
            ".claude/hooks/check_agent_spawn.py",
            "README.md",
            "src/main.py",
            ".github/workflows/validate.yml",
        ]
        with tempfile.TemporaryDirectory() as tmp:
            repo_root = Path(tmp)
            for i in range(200):
                tool = rng.choice(tools)
                fp = rng.choice(paths)
                params = {"file_path": fp, "content": f"iteration-{i}"}
                a = check_mcp_call(tool, params, repo_root=repo_root)
                b = check_mcp_call(tool, params, repo_root=repo_root)
                self.assertEqual(a, b, f"iter {i}: not idempotent tool={tool} fp={fp}")


if __name__ == "__main__":
    unittest.main()
