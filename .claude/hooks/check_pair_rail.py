#!/usr/bin/env python3
"""PLAN-091 PRODUCTION pair-rail hook compatibility facade.

Implementation is split into private declarations while this module owns all
runtime globals. That preserves dynamic monkeypatch lookups by callers.
"""
from __future__ import annotations

import json
import os
import re
import subprocess
import sys
from pathlib import Path
from typing import Any, Dict, List, Optional, Tuple

_HOOKS_DIR = Path(__file__).resolve().parent
if str(_HOOKS_DIR) not in sys.path:
    sys.path.insert(0, str(_HOOKS_DIR))

from _lib._pair_rail_parts import install as _install_parts

_install_parts(globals(), ('part_01', 'part_02', 'part_03', 'part_04'))

if __name__ == "__main__":
    if len(sys.argv) > 1 and sys.argv[1] == "--verify-codex-pin":
        sys.exit(_verify_pin_cli(sys.argv[2:]))
    sys.exit(main())
