"""cenv (PLAN-194): passada dura de sintaxe dos caminhos Python do patch.

Recebe os caminhos como argumentos e faz ``ast.parse`` dos bytes de cada um,
sem compilar para arquivo e sem gravar bytecode. Sai com rc 0 só quando todos
analisam; arquivo ilegível, ``SyntaxError``, ``ValueError`` (por exemplo, byte
NUL) ou nenhum argumento saem com rc 1. É a passada ``ast.parse`` do SIGN
anterior do pacote, chamada pela forma 3 do molde sign-min
(``python3 <script>.py <caminhos>``), que não aceita ``python3 -c``.

Stdlib, Python >= 3.9.
"""

from __future__ import annotations

import ast
import sys
from typing import List


def main(caminhos: List[str]) -> int:
    if not caminhos:
        sys.stdout.write("sintaxe: nenhum caminho informado\n")
        return 1
    for caminho in caminhos:
        try:
            with open(caminho, "rb") as arquivo:
                ast.parse(arquivo.read(), filename=caminho)
        except (OSError, SyntaxError, ValueError) as erro:
            sys.stdout.write("sintaxe: %s reprovou (%s)\n" % (caminho, type(erro).__name__))
            return 1
    sys.stdout.write("sintaxe: %d arquivo(s) analisado(s)\n" % len(caminhos))
    return 0


if __name__ == "__main__":
    sys.exit(main(sys.argv[1:]))
