"""Reusable behavioral probe for the literal-path re-pin guard."""
from __future__ import annotations

import re
import subprocess
from pathlib import Path
from typing import Any

from _subprocess_helpers import run_in_process_group

def run_literal_guard(case: Any, script: Path, dry: str, todo: bool) -> subprocess.CompletedProcess:
    """Run the emitted guard after hostile mold-variable assignments."""
    lines = script.read_text().splitlines()
    start = next(i for i, line in enumerate(lines) if line.startswith("# [") and "re-pin-codex" in line)
    end = next(i for i in range(start, len(lines)) if lines[i] == "fi")
    paths = re.findall(r"'([^']+)'", lines[start + 2])[-2:]
    assert len(paths) == 2
    sent, pin = [case.repo / path for path in paths]
    sent.write_text("TODO(owner): falta\n" if todo else "pronto\n")
    pin.write_text("# ok\n")
    harness = "\n".join([
        "set -euo pipefail", "die() { printf 'DIE: %s\\n' \"$*\"; exit 1; }",
        "DRY=" + dry, "SENT=/dev/null", "SRC_PIN=/dev/null", "SENT[0]=/dev/null",
        "for SRC_PIN in /dev/null; do :; done",
    ] + lines[start:end + 1] + ["echo PASSED"])
    return run_in_process_group(["bash", "-c", harness], cwd=str(case.repo), capture_output=True,
                                text=True, timeout=60, check=False)
