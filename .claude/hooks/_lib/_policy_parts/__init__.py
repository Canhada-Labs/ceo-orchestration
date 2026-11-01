"""Ordered source fragments for the policy facade."""
from __future__ import annotations
from pathlib import Path
from typing import Any, Dict, Tuple

_PARTS: Tuple[str, ...] = (
    "yaml_blocks", "yaml_flows", "yaml_scalars", "predicates", "decisions", "loading",
)

def install(namespace: Dict[str, Any]) -> None:
    """Execute inspectable declarations in the policy facade namespace."""
    directory = Path(__file__).resolve().parent
    for name in _PARTS:
        path = directory / (name + ".py")
        exec(compile(path.read_text(encoding="utf-8"), str(path), "exec"), namespace, namespace)
