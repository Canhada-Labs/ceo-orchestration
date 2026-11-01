"""Ordered PreCompact declarations installed into the hook facade."""
from __future__ import annotations

from pathlib import Path
from typing import Any, Dict, Tuple

_PARTS: Tuple[str, ...] = (
    "snapshot_core", "pressure_sidecar", "ledger_index", "runtime",
)

def install(namespace: Dict[str, Any]) -> None:
    """Compile real declaration modules in the facade namespace and order."""
    directory = Path(__file__).resolve().parent
    for name in _PARTS:
        path = directory / (name + ".py")
        exec(compile(path.read_text(encoding="utf-8"), str(path), "exec"), namespace, namespace)
