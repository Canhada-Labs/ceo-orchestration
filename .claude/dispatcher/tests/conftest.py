from __future__ import annotations

import sys
from pathlib import Path

# Insert the dispatcher directory into sys.path so that:
#   1. disable_predicate_eval.py can be imported directly by test files.
#   2. routing-matrix-loader.py can be loaded via importlib.util (hyphen in filename).
_DISPATCHER_DIR = Path(__file__).resolve().parent.parent
if str(_DISPATCHER_DIR) not in sys.path:
    sys.path.insert(0, str(_DISPATCHER_DIR))
