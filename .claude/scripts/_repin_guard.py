"""Owned shell guard emitted by the Codex re-pin generator."""
from __future__ import annotations

from typing import Any, List

TODO_MARK = "TODO(owner)"
PIN_OUT = "codex-cli-pin.txt.new"

GUARD = [
    "# [.claude/scripts/re-pin-codex.py] a justificativa humana do pack fica em TODO(owner):",
    "# o run real recusa assinar enquanto restar um; o ensaio só avisa.",
    "if env -u GREP_OPTIONS LC_ALL=C grep -Fn -- 'TODO(owner)' '@SENT@' '@PIN@' 2>/dev/null; then",
    "  [ \"$DRY\" = \"1\" ] || die \"TODO(owner) pendente nos materiais (linhas acima) — escreva a justificativa antes de assinar\"",
    "  printf '   AVISO: TODO(owner) pendente — o run real vai recusar\\n'",
    "else",
    "  rc=$?; [ \"$rc\" = \"1\" ] || die \"não consegui conferir TODO(owner) nos materiais\"",
    "fi",
]


def guard(ctx: Any) -> List[str]:
    """Render pack-owned paths literally so mold assignments cannot redirect it."""
    paths = (f"{ctx['pack_dir']}/{ctx['sentinel_name']}", f"{ctx['pack_dir']}/{PIN_OUT}")
    return [line.replace("@SENT@", paths[0]).replace("@PIN@", paths[1]) for line in GUARD]
