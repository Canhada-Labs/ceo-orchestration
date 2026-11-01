#!/usr/bin/env python3
"""profile-opus-4-7.py — Opus 4.7 framework optimization measurement tool.

PLAN-020 Phase 0 item 6 + 8 deliverable. Stdlib-only.

Modes:

- ``--smoke``: synthetic, no API, tokens mocked. CI-runnable. ≤30s budget.
  Outputs JSON to stdout; exit 0 on success, 1 on internal error, 2 on
  budget overrun.

- ``--baseline``: full baseline capture (requires env to read audit log
  + ANTHROPIC_API_KEY for live cache header probing — Phase 0 item 1
  prerequisites). Outputs JSON + side-effects audit-log entries.
  Reserved for next session post Owner sentinel for hook modifications.

- ``--floor``: re-measure subprocess startup floor on this machine
  (Phase 0 item 8). Cheap; ≤2s. Reports python3 -c 'pass' p50/p95/p99.

Wire-up: validate.yml step ``opus-4-7-profiler-smoke`` (deferred —
needs Owner sentinel for .github/workflows/validate.yml edit). For
now invoke manually:

    python3 .claude/scripts/profile-opus-4-7.py --smoke
    python3 .claude/scripts/profile-opus-4-7.py --floor

Schema:

    {
      "schema": "profile-opus-4-7.v1",
      "mode": "smoke|baseline|floor",
      "measured_at": "<UTC ISO>",
      "python": "<sys.version_info>",
      "subprocess_floor_ns": {"p50": ..., "p95": ..., "p99": ...},
      "decomposition": {
        "gate_boot_tokens_estimate": ...,
        "spawn_prompt_tokens_estimate": ...,
        "...": ...
      },
      "smoke": {
        "elapsed_ms": ...,
        "checks": [...]
      }
    }
"""

from __future__ import annotations

import argparse
import hashlib
import json
import math
import os
import shutil
import subprocess
import sys
import tempfile
import time
from datetime import datetime, timezone
from pathlib import Path
from typing import Any, Callable, Dict, List, Optional, Tuple


# Declarations are cloned and functions execute against this facade's own
# globals; no imported module template is modified by facade monkeypatches.
_HOOKS_DIR = Path(__file__).resolve().parents[1] / "hooks"
if str(_HOOKS_DIR) not in sys.path:
    sys.path.insert(0, str(_HOOKS_DIR))

from _lib._profile_opus_parts import install as _install_parts

_install_parts(globals(), ("smoke", "reference", "latency", "cli"))

if __name__ == "__main__":
    sys.exit(main())
