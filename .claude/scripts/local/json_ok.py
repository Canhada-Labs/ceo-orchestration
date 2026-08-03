#!/usr/bin/env python3
"""Assert each argv path parses as JSON (preflight helper)."""

from __future__ import annotations

import json
import sys

for p in sys.argv[1:]:
    json.load(open(p, encoding="utf-8"))
print("json ok: %d file(s)" % (len(sys.argv) - 1))
