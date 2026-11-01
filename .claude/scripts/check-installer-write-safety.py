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

# Runtime components ship under hooks/_lib, whose subdirectories the installer
# copies recursively.  The adjacent fallback serves isolated legacy test
# fixtures that materialize only this entry point and its implementation.
_HOOKS_DIR = _SCRIPTS_DIR.parent / "hooks"
if (_HOOKS_DIR / "_lib").is_dir():
    if str(_HOOKS_DIR) not in sys.path:
        sys.path.insert(0, str(_HOOKS_DIR))
    from _lib._installer_write_safety import bind as _bind_legacy_api
else:
    from _installer_write_safety import bind as _bind_legacy_api

_bind_legacy_api(globals())


if __name__ == "__main__":
    sys.exit(main())
