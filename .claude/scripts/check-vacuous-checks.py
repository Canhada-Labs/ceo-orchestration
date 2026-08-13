#!/usr/bin/env python3
"""check-vacuous-checks.py — lint de vacuidade dos checks do /ceo-boot.

PLAN-178 W-C Lote A (C3), perna R1. Classe-alvo (S287/S292 +
feedback-check-tier-a-spec-version-drift-vacuous): um ``check_*`` que
nao consegue DISCRIMINAR — nenhum caminho alcancavel muda a cor com o
estado do mundo — e verde decorativo: parece instrumento, nao mede.

Regra R1 (heuristica conservadora, stdlib-only; codex Lote-A P2-2 —
os status sao derivados EXCLUSIVAMENTE dos nos ``return``, nunca do
texto do corpo, senao um literal em docstring/dict/branch morto conta
como discriminacao):
- ``ok``       — os ``return``s da funcao devolvem >= 2 literais de
                 status distintos dentre {green, yellow, red}.
- ``indirect`` — algum ``return`` devolve o status por VARIAVEL ou
                 CHAMADA (helper/delegacao): nao-decidivel
                 estaticamente; contado e pulado, nunca flagrado.
- ``waived``   — comentario ESTRUTURADO ``# CEO-INFORMATIONAL-ONLY:
                 <razao>`` na linha do ``def`` ou na anterior — e SO
                 ai; mencao em docstring/string nao waiva (espelha
                 ``# CEO-DEBT:`` do nightly dim viii). Para checks
                 deliberadamente informacionais (contadores sem
                 limiar).
- ``VACUOUS``  — nada acima: so consegue devolver UMA cor. Exit 1.

A perna R2 da cura (positive control POR check) vive nos testes de
``.claude/scripts/tests/`` — este lint nao a substitui.

Exit: 0 = limpo; 1 = candidato(s) vacuoso(s); 2 = erro de uso/parse.
A medicao imprime seus INPUTS (licao S285).
"""
from __future__ import annotations

import ast
import re
import sys
from typing import Iterator, List, Optional, Set, Tuple

STATUSES = ("green", "yellow", "red")
WAIVER_MARK = "CEO-INFORMATIONAL-ONLY"
# Waiver ESTRUTURADO (codex r2 P2-4): comentario com razao nao-vazia —
# mencao em docstring/string NUNCA waiva.
_WAIVER_RE = re.compile(r"#[ \t]*" + WAIVER_MARK + r"[ \t]*:[ \t]*\S")


def _iter_local_returns(node: ast.FunctionDef) -> Iterator[ast.Return]:
    """Returns PROPRIOS da funcao, alcancaveis (codex r2 P2-3).

    Nao desce em def/class aninhados (returns de helper nao contam) e
    poda branches estaticamente mortos (``if False:`` / ``if True:``
    elide o lado morto).
    """
    def walk(stmts):
        for st in stmts:
            if isinstance(st, (ast.FunctionDef, ast.AsyncFunctionDef,
                               ast.ClassDef)):
                continue
            if isinstance(st, ast.Return):
                yield st
                continue
            if isinstance(st, ast.If) and isinstance(st.test, ast.Constant):
                yield from walk(st.body if st.test.value else st.orelse)
                continue
            for field in ("body", "orelse", "finalbody"):
                sub = getattr(st, field, None)
                if sub:
                    yield from walk(sub)
            for handler in getattr(st, "handlers", []) or []:
                yield from walk(handler.body)
    yield from walk(node.body)


def _return_status_profile(node: ast.FunctionDef) -> Tuple[Set[str], bool]:
    """(literais de status devolvidos, ha_return_indireto).

    Olha SO o primeiro elemento de cada ``return`` local alcancavel.
    Literal fora de {green,yellow,red} e ignorado; nao-literal
    (Name/Call/IfExp/...) marca a funcao como indireta.
    """
    found: Set[str] = set()
    indirect = False
    for sub in _iter_local_returns(node):
        if sub.value is None:
            continue
        val = sub.value
        first = val.elts[0] if isinstance(val, ast.Tuple) and val.elts else val
        if isinstance(first, ast.Constant) and isinstance(first.value, str):
            if first.value in STATUSES:
                found.add(first.value)
        else:
            indirect = True
    return found, indirect


def scan_file(path: str) -> Tuple[int, List[str]]:
    try:
        with open(path, "r", encoding="utf-8") as fh:
            src = fh.read()
        tree = ast.parse(src)
    except (OSError, SyntaxError) as exc:  # fail-loud: lint nao adivinha
        return 2, ["PARSE-ERROR %s: %s" % (path, exc)]

    lines = src.splitlines()
    ok = waived = indirect = 0
    flagged: List[str] = []
    for node in ast.walk(tree):
        if not (isinstance(node, ast.FunctionDef)
                and node.name.startswith("check_")):
            continue
        head = "\n".join(lines[max(0, node.lineno - 2):node.lineno + 1])
        returned, has_indirect = _return_status_profile(node)
        if len(returned) >= 2:
            ok += 1
        elif has_indirect:
            indirect += 1
        elif _WAIVER_RE.search(head):
            waived += 1
        else:
            found = sorted(returned) or ["<none>"]
            flagged.append("VACUOUS %s:%d %s statuses=%s"
                           % (path, node.lineno, node.name, found))
    total = ok + waived + indirect + len(flagged)
    print("INPUTS: file=%s checks=%d rule=discriminate>=2of%s waiver=%s"
          % (path, total, list(STATUSES), WAIVER_MARK))
    print("ok=%d indirect=%d waived=%d flagged=%d"
          % (ok, indirect, waived, len(flagged)))
    return (1 if flagged else 0), flagged


def main(argv: Optional[List[str]] = None) -> int:
    args = list(sys.argv[1:] if argv is None else argv)
    if not args:
        args = [".claude/scripts/ceo-boot.py"]
    worst = 0
    for path in args:
        code, flagged = scan_file(path)
        for line in flagged:
            print("  " + line)
        worst = max(worst, code)
    return worst


if __name__ == "__main__":
    sys.exit(main())
