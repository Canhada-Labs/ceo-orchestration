"""Ordered ceo-boot declarations for the public script facade.

Each part is ordinary Python source. The loader compiles it with its real
filename and executes it in the facade dictionary, retaining legacy global
lookup and monkeypatch behavior without proxies.
"""
from __future__ import annotations

from pathlib import Path
from typing import Any, Dict, Tuple

_PARTS: Tuple[str, ...] = (
    "state_plan_audit", "harness_governance", "model_persona",
    "persona_confidence", "liveness_schedule", "scheduled_cache",
    "cache_recommendations", "telemetry_candidates", "candidates_lessons",
    "lessons_cli",
)


def install(namespace: Dict[str, Any]) -> None:
    """Execute real declaration files in their original dependency order."""
    directory = Path(__file__).resolve().parent
    for name in _PARTS:
        path = directory / (name + ".py")
        code = compile(path.read_text(encoding="utf-8"), str(path), "exec")
        exec(code, namespace)
