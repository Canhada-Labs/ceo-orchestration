"""PLAN-050 Phase 7b (C4) — swarm benchmark replay harness.

Loads a manifest (JSON — stdlib-only; YAML adapter is adopter-owned),
runs each task deterministically against a pinned callable, and
reports per-task + aggregate ``BenchmarkResult`` with:

- ``score``           — raw task score (caller-defined domain; normalized 0..1)
- ``work_latency_ms`` — task callable wall-clock
- ``git_overhead_ms`` — pool acquire/release overhead (separate per C4)
- ``regressed``       — True if score < manifest baseline (hard-fail row)

## Local replay without live API

The harness is intentionally transport-agnostic: caller supplies
``task_fn(task_input) -> score``. Live-API replay is simulated by a
caller-controlled stub or cached-response fixture. This lets the
CI benchmark-regression gate run offline without burning API credits
and without flakiness from upstream rate-limits.

## Manifest schema

```json
{
  "manifest_version": 1,
  "baseline_sha": "abc123…",
  "tasks": [
    {
      "id": "task-01",
      "input": {...any JSON...},
      "baseline_score": 0.85,
      "regression_tolerance": 0.02
    },
    ...
  ]
}
```

## Git-overhead measurement

When a ``WorktreePool`` is provided, every task's acquire/release
latency is measured separately from the task callable and reported
as ``git_overhead_ms``. Pool-less runs report ``0.0``.
"""
from __future__ import annotations

import json
import time
from dataclasses import dataclass, field
from pathlib import Path
from typing import Any, Callable, Dict, List, Optional


SCORE_DEFAULT_TOLERANCE = 0.02  # 2% regression tolerance default


class BenchmarkManifestError(ValueError):
    """Raised when a manifest is malformed."""


@dataclass
class TaskResult:
    """Single-task outcome."""

    task_id: str
    score: float
    baseline_score: float
    regression_tolerance: float
    work_latency_ms: float
    git_overhead_ms: float = 0.0
    error: Optional[str] = None

    @property
    def regressed(self) -> bool:
        return self.score < (self.baseline_score - self.regression_tolerance)

    @property
    def improved(self) -> bool:
        return self.score > (self.baseline_score + self.regression_tolerance)

    def to_dict(self) -> Dict[str, Any]:
        return {
            "task_id": self.task_id,
            "score": self.score,
            "baseline_score": self.baseline_score,
            "regression_tolerance": self.regression_tolerance,
            "work_latency_ms": self.work_latency_ms,
            "git_overhead_ms": self.git_overhead_ms,
            "regressed": self.regressed,
            "improved": self.improved,
            "error": self.error,
        }


@dataclass
class BenchmarkResult:
    """Aggregate across all tasks."""

    manifest_version: int
    baseline_sha: str
    tasks: List[TaskResult] = field(default_factory=list)

    @property
    def n_tasks(self) -> int:
        return len(self.tasks)

    @property
    def n_regressed(self) -> int:
        return sum(1 for t in self.tasks if t.regressed)

    @property
    def n_improved(self) -> int:
        return sum(1 for t in self.tasks if t.improved)

    @property
    def mean_score(self) -> float:
        if not self.tasks:
            return 0.0
        return sum(t.score for t in self.tasks) / len(self.tasks)

    @property
    def mean_work_latency_ms(self) -> float:
        if not self.tasks:
            return 0.0
        return sum(t.work_latency_ms for t in self.tasks) / len(self.tasks)

    @property
    def mean_git_overhead_ms(self) -> float:
        if not self.tasks:
            return 0.0
        return sum(t.git_overhead_ms for t in self.tasks) / len(self.tasks)

    def pass_regression_gate(self) -> bool:
        """C4 gate: zero regressed tasks."""
        return self.n_regressed == 0

    def to_dict(self) -> Dict[str, Any]:
        return {
            "manifest_version": self.manifest_version,
            "baseline_sha": self.baseline_sha,
            "summary": {
                "n_tasks": self.n_tasks,
                "n_regressed": self.n_regressed,
                "n_improved": self.n_improved,
                "mean_score": self.mean_score,
                "mean_work_latency_ms": self.mean_work_latency_ms,
                "mean_git_overhead_ms": self.mean_git_overhead_ms,
                "passes_regression_gate": self.pass_regression_gate(),
            },
            "tasks": [t.to_dict() for t in self.tasks],
        }


# ---------------------------------------------------------------------------
# Manifest loader
# ---------------------------------------------------------------------------
def load_manifest(path: Path) -> Dict[str, Any]:
    """Load + validate a benchmark manifest JSON file."""
    try:
        payload = json.loads(Path(path).read_text(encoding="utf-8"))
    except json.JSONDecodeError as e:
        raise BenchmarkManifestError(f"{path}: invalid JSON: {e}")
    except OSError as e:
        raise BenchmarkManifestError(f"{path}: cannot read: {e}")
    _validate_manifest(payload)
    return payload


def _validate_manifest(payload: Dict[str, Any]) -> None:
    if not isinstance(payload, dict):
        raise BenchmarkManifestError("manifest must be a JSON object")
    if payload.get("manifest_version") != 1:
        raise BenchmarkManifestError(
            f"manifest_version must be 1; got {payload.get('manifest_version')}"
        )
    tasks = payload.get("tasks")
    if not isinstance(tasks, list) or not tasks:
        raise BenchmarkManifestError("manifest.tasks must be a non-empty list")
    seen_ids = set()
    for i, t in enumerate(tasks):
        if not isinstance(t, dict):
            raise BenchmarkManifestError(f"tasks[{i}] must be an object")
        tid = t.get("id")
        if not isinstance(tid, str) or not tid:
            raise BenchmarkManifestError(f"tasks[{i}].id must be non-empty str")
        if tid in seen_ids:
            raise BenchmarkManifestError(f"tasks[{i}].id duplicated: {tid!r}")
        seen_ids.add(tid)
        if "baseline_score" not in t:
            raise BenchmarkManifestError(f"tasks[{i}] missing baseline_score")
        try:
            float(t["baseline_score"])
        except (TypeError, ValueError):
            raise BenchmarkManifestError(
                f"tasks[{i}].baseline_score must be numeric"
            )


# ---------------------------------------------------------------------------
# Replay driver
# ---------------------------------------------------------------------------
def replay(
    manifest: Dict[str, Any],
    task_fn: Callable[[Dict[str, Any]], float],
    *,
    pool: Optional[Any] = None,  # duck-typed WorktreePool
) -> BenchmarkResult:
    """Run every manifest task against ``task_fn``; return BenchmarkResult.

    Tasks that raise are recorded with ``error=<repr>`` and ``score=0.0``
    (counted as regressed automatically since 0 < any positive baseline).
    """
    result = BenchmarkResult(
        manifest_version=manifest["manifest_version"],
        baseline_sha=manifest.get("baseline_sha", ""),
    )
    for t in manifest["tasks"]:
        task_id = t["id"]
        baseline = float(t["baseline_score"])
        tolerance = float(t.get("regression_tolerance", SCORE_DEFAULT_TOLERANCE))
        task_input = t.get("input", {})
        git_overhead_ms = 0.0
        wt_path = None
        try:
            if pool is not None:
                t0 = time.monotonic()
                wt_path = pool.acquire(task_id)
                git_overhead_ms += (time.monotonic() - t0) * 1000.0
            t1 = time.monotonic()
            score = float(task_fn(task_input))
            work_latency_ms = (time.monotonic() - t1) * 1000.0
            tr = TaskResult(
                task_id=task_id,
                score=score,
                baseline_score=baseline,
                regression_tolerance=tolerance,
                work_latency_ms=work_latency_ms,
                git_overhead_ms=git_overhead_ms,
            )
        except Exception as e:
            tr = TaskResult(
                task_id=task_id,
                score=0.0,
                baseline_score=baseline,
                regression_tolerance=tolerance,
                work_latency_ms=0.0,
                git_overhead_ms=git_overhead_ms,
                error=f"{type(e).__name__}: {e}",
            )
        finally:
            if pool is not None and wt_path is not None:
                t2 = time.monotonic()
                try:
                    pool.release(wt_path)
                except Exception:
                    pass
                git_overhead_ms += (time.monotonic() - t2) * 1000.0
                tr.git_overhead_ms = git_overhead_ms
        result.tasks.append(tr)
    return result
