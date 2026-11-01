#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""Compatibility entry point for the installer write-safety census.

The implementation is split into the ``_installer_write_safety`` package. This
file deliberately re-exports its complete module namespace: callers can keep
importing this historical path, including parser and verdict helpers used by
downstream regression harnesses.
"""

from __future__ import annotations

import sys
from pathlib import Path

_SCRIPTS_DIR = Path(__file__).resolve().parent
if str(_SCRIPTS_DIR) not in sys.path:
    sys.path.insert(0, str(_SCRIPTS_DIR))

from _installer_write_safety import bind as _bind_legacy_api

_bind_legacy_api(globals())


if __name__ == "__main__":
    sys.exit(main())
