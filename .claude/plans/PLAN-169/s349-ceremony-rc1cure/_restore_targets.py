#!/usr/bin/env python3
"""Restaura os alvos da cerimonia a partir de um snapshot em BYTES.

Existe porque `git checkout -- <path>` e recusado sobre caminho canonico pelo
interceptor de edicao: o comando morre, o `|| true` engole, e a arvore fica
suja. Escrita Python passa, e o snapshot dispensa o git por completo.

  python3 _restore_targets.py <snapshot-dir> <repo-root>

O snapshot e um diretorio com um arquivo por alvo, nomeado pelo caminho
relativo com `/` trocado por `%`. Sai 0 se restaurou tudo, 1 se faltou algum —
nunca silenciosamente parcial.
"""
from __future__ import annotations

import pathlib
import sys


def main() -> int:
    if len(sys.argv) != 3:
        sys.stderr.write("uso: _restore_targets.py <snapshot-dir> <repo-root>\n")
        return 2
    snap = pathlib.Path(sys.argv[1])
    root = pathlib.Path(sys.argv[2])
    if not snap.is_dir():
        sys.stderr.write("FATAL: snapshot ausente: %s\n" % snap)
        return 1
    bad = []
    n = 0
    for f in sorted(snap.iterdir()):
        if not f.is_file() or f.name == "MANIFEST":
            continue
        rel = f.name.replace("%", "/")
        dst = root / rel
        try:
            if dst.is_symlink():
                bad.append("%s virou symlink" % rel)
                continue
            dst.write_bytes(f.read_bytes())
            n += 1
        except OSError as exc:
            bad.append("%s: %s" % (rel, exc))
    if bad:
        sys.stderr.write("FATAL: restauracao incompleta:\n  %s\n"
                         % "\n  ".join(bad))
        return 1
    sys.stderr.write("   (restaurados %d alvo(s) do snapshot PRE-edicao)\n" % n)
    return 0


if __name__ == "__main__":
    sys.exit(main())
