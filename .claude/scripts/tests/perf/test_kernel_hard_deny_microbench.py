"""PLAN-085 Wave E.2 — _KERNEL_PATHS perf-ceiling microbench.

Asserts that matching the full _KERNEL_PATHS list stays fast, per ADR-116
\xa73 + handoff \xa710.1.

Methodology (S166/PLAN-114 C-2 de-flake):
  - N = 50 samples per probe (raised from 30; p99 of 500 = 6th-worst, robust).
  - time.perf_counter_ns() per matching loop.
  - **Blocking gate = otel-style 3-tier on the ABSOLUTE post-extension per-call
    time** (median<500us, p95<1ms, p99<2ms). This is order-independent and
    hardware-tolerant (>>10x headroom over the observed tens-of-µs), unlike the
    prior ``(post_p99 - pre_p99) <= 2ms`` delta which was biased NEGATIVE by
    warm-up order (pre measured cold first, post warm second) and could flake
    on a loaded CI runner.
  - The pre-ext (17-entry) delta is kept as an ADVISORY print only.

Discipline: stdlib-only, Python >= 3.9.
"""

from __future__ import annotations

import sys
import time
import unittest
from pathlib import Path
from typing import List

REPO_ROOT = Path(__file__).resolve().parents[4]
_HOOKS = REPO_ROOT / ".claude" / "hooks"
if str(_HOOKS) not in sys.path:
    sys.path.insert(0, str(_HOOKS))

from check_arbitration_kernel import (  # noqa: E402
    _KERNEL_PATHS,
    _is_kernel_path,
)


# Pre-extension snapshot (14 entries; S110 baseline pre-Wave-E.2).
_PRE_EXT_KERNEL_PATHS = [
    ".claude/hooks/check_agent_spawn.py",
    ".claude/hooks/check_canonical_edit.py",
    ".claude/hooks/check_plan_edit.py",
    ".claude/hooks/check_arbitration_kernel.py",
    ".claude/hooks/check_skill_patch_sentinel.py",
    ".claude/hooks/_lib/contract.py",
    ".claude/hooks/_lib/policy.py",
    ".claude/hooks/_lib/policy_preprocessors.py",
    ".claude/hooks/_lib/redact.py",
    ".claude/hooks/_lib/pii_patterns.py",
    ".claude/hooks/_lib/audit_emit.py",
    ".claude/hooks/_lib/adapters/claude.py",
    ".claude/policies/*.yaml",
    ".claude/policies/*.yml",
    ".claude/policies/fixtures/*.jsonl",
    ".claude/hooks/policy_dispatch.py",
    ".claude/agents/*.md",
]

N_SAMPLES = 50


def _measure_one(probe_paths: List[str], guard_list: List[str]) -> List[int]:
    """Measure ns per probe path against the given guard list."""
    from check_arbitration_kernel import _fnmatch_segments

    samples: List[int] = []
    for probe in probe_paths:
        for _ in range(N_SAMPLES):
            t0 = time.perf_counter_ns()
            # Inline _is_kernel_path-equivalent loop to isolate the
            # fnmatch overhead (the only variable changed by E.2).
            try:
                rel = str(Path(probe))
                for pattern in guard_list:
                    if _fnmatch_segments(rel, pattern):
                        break
            except Exception:  # noqa: BLE001 — defensive
                pass
            t1 = time.perf_counter_ns()
            samples.append(t1 - t0)
    return samples


def _percentile_ns(samples: List[int], pct: float) -> int:
    samples_sorted = sorted(samples)
    idx = int(len(samples_sorted) * pct)
    idx = min(idx, len(samples_sorted) - 1)
    return samples_sorted[idx]


class TestKernelHardDenyMicrobench(unittest.TestCase):
    """E.2 perf-ceiling: p99(post) - p99(pre) <= 2ms."""

    def test_kernel_extension_within_perf_budget(self) -> None:
        # Probe set: 13 ADR-116 new paths + 3 non-kernel probes.
        probes = [
            ".claude/settings.json",
            ".claude/hooks/_python-hook.sh",
            ".claude/hooks/_lib/gpg_verify.py",
            ".claude/hooks/_lib/audit_hmac.py",
            ".claude/hooks/_lib/secret_patterns.py",
            ".claude/hooks/_lib/trusted_env.py",
            ".github/workflows/release.yml",
            "scripts/install.sh",
            "README.md",
            "tests/conftest.py",
        ]

        pre_samples = _measure_one(probes, _PRE_EXT_KERNEL_PATHS)
        post_samples = _measure_one(probes, _KERNEL_PATHS)

        # Advisory only: pre is measured cold (first pass), post warm (second),
        # so the delta is warm-up-order-biased and not an honest ceiling.
        pre_p99 = _percentile_ns(pre_samples, 0.99)
        post_p50 = _percentile_ns(post_samples, 0.50)
        post_p95 = _percentile_ns(post_samples, 0.95)
        post_p99 = _percentile_ns(post_samples, 0.99)
        advisory_delta_ms = (post_p99 - pre_p99) / 1_000_000

        print(
            f"\n[perf] post p50 = {post_p50/1000:.1f} us, "
            f"post p95 = {post_p95/1000:.1f} us, "
            f"post p99 = {post_p99/1000:.1f} us "
            f"(advisory delta-vs-cold-pre = {advisory_delta_ms:.3f} ms)"
        )

        # Blocking gate: otel-style 3-tier on the ABSOLUTE post per-call match
        # cost. Order-independent + hardware-tolerant (>>10x headroom over the
        # observed tens-of-µs); an O(N^2) regression in matching still breaches.
        self.assertLess(
            post_p50, 500_000,
            msg=f"kernel-path match p50 {post_p50/1000:.1f}us >= 500us median ceiling",
        )
        self.assertLess(
            post_p95, 1_000_000,
            msg=f"kernel-path match p95 {post_p95/1000:.1f}us >= 1ms p95 ceiling",
        )
        self.assertLess(
            post_p99, 2_000_000,
            msg=(
                f"kernel-path match p99 {post_p99/1000:.1f}us >= 2ms worst ceiling. "
                f"ADR-116 \xa73 perf-ceiling breached (full _KERNEL_PATHS too slow)."
            ),
        )


if __name__ == "__main__":  # pragma: no cover
    unittest.main()
