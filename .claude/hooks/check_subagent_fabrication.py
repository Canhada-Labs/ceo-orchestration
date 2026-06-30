#!/usr/bin/env python3
"""PostToolUse Agent hook — sub-agent fabrication detection (ADR-080).

Thin wrapper around `.claude/scripts/swarm/_subagent_fabrication.py`
detection library. Default ADVISORY mode emits ``veto_triggered``
audit event with ``reason_code=subagent_fabrication_detected``;
``CEO_SUBAGENT_FABRICATION_BLOCK=1`` escalates to a ``systemMessage``
warning. ``CEO_SUBAGENT_FABRICATION_DEBUG=1`` writes the full
response to ``/tmp/h4-fabrication-<sha8>.json`` for forensic
inspection.

See ADR-080 for full design + alternatives + Owner ceremony record.
Fail-open contract: any internal exception → exit 0.
"""

from __future__ import annotations

import sys
from pathlib import Path

# Make swarm package importable
_REPO_ROOT = Path(__file__).resolve().parent.parent
_SCRIPTS_DIR = _REPO_ROOT / "scripts"
if str(_SCRIPTS_DIR) not in sys.path:
    sys.path.insert(0, str(_SCRIPTS_DIR))

# PLAN-114 F-1.10-9e327d7d — honour the fail-open contract (docstring) at
# the module-import boundary: if the swarm package is unavailable (e.g. an
# adopter installed the framework without it), a bare import would die
# exit!=0 instead of emitting the schema-compliant {} allow. Guard it.
try:
    from swarm._subagent_fabrication import _cli_main  # noqa: E402

    _SWARM_AVAILABLE = True
except Exception:  # pragma: no cover — import-boundary fail-open
    _SWARM_AVAILABLE = False
    _cli_main = None  # type: ignore[assignment]


if __name__ == "__main__":
    if not _SWARM_AVAILABLE:
        # Fail-open: swarm detection lib unavailable -> schema-compliant allow.
        sys.stdout.write("{}\n")
        sys.exit(0)
    sys.exit(_cli_main(["--hook"]))
