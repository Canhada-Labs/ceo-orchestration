"""Task: write a tolerant JSON config loader with defaults.

Verifier feeds several config dicts (as JSON files) and checks merge-with-default
behavior + tolerance of a missing file.
"""

from __future__ import annotations

import json
from pathlib import Path

from . import clamp_reward, run_python, _VERIFY_ERROR

_STUB = '''\
import json

DEFAULTS = {"host": "localhost", "port": 8080, "debug": False}


def load_config(path):
    """Read JSON from `path` and return DEFAULTS merged with the file's keys.
    Missing file or invalid JSON -> return a copy of DEFAULTS (never raise).
    """
    raise NotImplementedError
'''


def setup(workdir: Path) -> None:
    (workdir / "solution.py").write_text(_STUB, encoding="utf-8")
    (workdir / "good.json").write_text(
        json.dumps({"port": 9090, "extra": 1}), encoding="utf-8"
    )
    (workdir / "bad.json").write_text("{not json", encoding="utf-8")


def verify(workdir: Path) -> float:
    checks = []
    # 1. merge keeps defaults + overrides + extra
    r = run_python(workdir, "solution.py", func="load_config",
                   args=(str(workdir / "good.json"),))
    ok_merge = (
        isinstance(r, dict)
        and r.get("host") == "localhost"
        and r.get("port") == 9090
        and r.get("debug") is False
        and r.get("extra") == 1
    )
    checks.append(ok_merge)
    # 2. missing file -> defaults, no raise
    r2 = run_python(workdir, "solution.py", func="load_config",
                    args=(str(workdir / "nope.json"),))
    checks.append(
        r2 is not _VERIFY_ERROR
        and isinstance(r2, dict)
        and r2.get("port") == 8080
    )
    # 3. invalid JSON -> defaults, no raise
    r3 = run_python(workdir, "solution.py", func="load_config",
                    args=(str(workdir / "bad.json"),))
    checks.append(
        r3 is not _VERIFY_ERROR
        and isinstance(r3, dict)
        and r3.get("host") == "localhost"
    )
    return clamp_reward(sum(1 for c in checks if c) / len(checks))


TASK = {
    "id": "t03-json-config-parse",
    "title": "Tolerant JSON config loader with defaults",
    "category": "feature",
    "difficulty": "medium",
    "setup": setup,
    "instruction": (
        "Implement load_config(path) in solution.py per its docstring: merge the "
        "file's JSON onto DEFAULTS, and on a missing file or invalid JSON return "
        "a copy of DEFAULTS without raising."
    ),
    "verify": verify,
}
