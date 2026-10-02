#!/usr/bin/env python3
"""check-w1-shape.py — controle vermelho→verde da W1 do PLAN-194 sobre um validate.yml.

Uso: python3 check-w1-shape.py <validate.yml>
Saída: uma linha por asserção (ok/FALHA) e rc 0 só se todas passam.

O que confere (a forma, não o CI — o CI de verdade é o Check da W1):
  W1.1  na matriz `hook-tests-python-matrix`, a perna 3.9 roda em `ubuntu-24.04` em
        push, pull_request e schedule; as pernas 3.10/3.11/3.12 seguem no `Ceo`;
  W1.3  a perna 3.14 existe SÓ no schedule e roda em `ubuntu-26.04`;
        a matriz de push segue 3.9+3.12 e a de pull_request as quatro (PLAN-184 A0);
  timeout das pernas nos runners padrão = 45 min; no `Ceo` = 25 min;
  W1.2  no job `validate`, nenhum step anterior ao `actions/setup-python` importa
        yaml, e o step dos catálogos YAML vem DEPOIS do pip que instala o PyYAML.

As expressões `${{ }}` são avaliadas com a semântica de `&&`/`||` do Actions (devolvem
o operando, curto-circuito), que é a de `and`/`or` do Python para estes operandos
(strings não vazias e números ≠ 0 são verdadeiros). Uma expressão fora do subconjunto
reconhecido aqui (==, &&, ||, parênteses, literais, fromJSON, matrix.python-version,
github.event_name) REPROVA — nunca é adivinhada.
"""
from __future__ import annotations

import json
import re
import sys
from typing import Dict, List

import yaml

_TOKEN = re.compile(
    r"\s*(?:(?P<str>'[^']*')|(?P<num>\d+)|(?P<op>&&|\|\||==)|(?P<par>[()])"
    r"|(?P<fn>fromJSON)|(?P<var>matrix\.python-version|github\.event_name))"
)


def _translate(expr: str) -> str:
    """Traduz o subconjunto reconhecido para uma expressão Python; recusa o resto."""
    body = expr.strip()
    if not (body.startswith("${{") and body.endswith("}}")):
        raise ValueError("não é uma expressão ${{ }}: %r" % expr)
    body = body[3:-2]
    out: List[str] = []
    pos = 0
    while pos < len(body):
        if body[pos:].strip() == "":
            break
        m = _TOKEN.match(body, pos)
        if not m or m.end() == pos:
            raise ValueError("expressão fora do subconjunto reconhecido, em %r" % body[pos:pos + 40])
        pos = m.end()
        if m.group("str") is not None:
            out.append(repr(m.group("str")[1:-1]))
        elif m.group("num") is not None:
            out.append(m.group("num"))
        elif m.group("op") is not None:
            out.append({"&&": " and ", "||": " or ", "==": " == "}[m.group("op")])
        elif m.group("par") is not None:
            out.append(m.group("par"))
        elif m.group("fn") is not None:
            out.append("_fromjson")
        else:
            out.append({"matrix.python-version": "_ver", "github.event_name": "_event"}[m.group("var")])
    return "".join(out)


def _eval(expr: object, event: str, ver: str = "") -> object:
    if not isinstance(expr, str) or "${{" not in expr:
        return expr  # literal
    py = _translate(" ".join(expr.split()))
    env: Dict[str, object] = {"_fromjson": json.loads, "_ver": ver, "_event": event, "__builtins__": {}}
    return eval(py, env)  # noqa: S307 — só o subconjunto traduzido acima chega aqui


def main(path: str) -> int:
    with open(path, encoding="utf-8") as f:
        doc = yaml.safe_load(f)
    jobs = doc["jobs"]
    fails = 0

    def check(cond: bool, msg: str) -> None:
        nonlocal fails
        print(("   ok: " if cond else "   FALHA: ") + msg)
        if not cond:
            fails += 1

    mx = jobs["hook-tests-python-matrix"]
    want_versions = {
        "push": ["3.9", "3.12"],
        "pull_request": ["3.9", "3.10", "3.11", "3.12"],
        "schedule": ["3.9", "3.10", "3.11", "3.12", "3.14"],
    }
    want_runner = {"3.9": "ubuntu-24.04", "3.10": "Ceo", "3.11": "Ceo", "3.12": "Ceo", "3.14": "ubuntu-26.04"}
    want_timeout = {"3.9": 45, "3.10": 25, "3.11": 25, "3.12": 25, "3.14": 45}
    try:
        for event, versions in want_versions.items():
            got = _eval(mx["strategy"]["matrix"]["python-version"], event)
            check(got == versions, "matriz em %s = %s (esperado %s)" % (event, got, versions))
            for v in got if isinstance(got, list) else []:
                ro = _eval(mx["runs-on"], event, v)
                check(ro == want_runner.get(v), "%s / %s roda em %r (esperado %r)" % (event, v, ro, want_runner.get(v)))
                to = _eval(mx.get("timeout-minutes"), event, v)
                to = int(to) if isinstance(to, (int, str)) and str(to).isdigit() else to
                check(to == want_timeout.get(v), "%s / %s timeout %r min (esperado %r)" % (event, v, to, want_timeout.get(v)))
    except ValueError as exc:
        check(False, "expressão não avaliável: %s" % exc)

    steps = jobs["validate"]["steps"]
    setup_idx = next(i for i, s in enumerate(steps) if "actions/setup-python" in str(s.get("uses", "")))
    early_yaml = [s.get("name") for s in steps[:setup_idx] if "import yaml" in str(s.get("run", ""))]
    check(not early_yaml, "nenhum step antes do setup-python importa yaml (achados: %s)" % early_yaml)
    pip_idx = next((i for i, s in enumerate(steps) if "PyYAML" in str(s.get("run", "")) and "pip install" in str(s.get("run", ""))), -1)
    cat_idx = next((i for i, s in enumerate(steps) if s.get("name") == "Validate settings.json and YAML catalogs"), -1)
    check(pip_idx > setup_idx >= 0, "o pip que instala o PyYAML vem depois do setup-python (pip=%d, setup=%d)" % (pip_idx, setup_idx))
    check(cat_idx > pip_idx >= 0, "o step dos catálogos YAML vem depois do pip (catálogos=%d, pip=%d)" % (cat_idx, pip_idx))
    run = str(steps[cat_idx].get("run", "")) if cat_idx >= 0 else ""
    for y in (".claude/pitfalls-catalog.yaml", ".claude/task-chains.yaml"):
        check(y in run, "o step dos catálogos ainda confere %s" % y)
    print("RESUMO: %s" % ("verde" if fails == 0 else "%d falha(s)" % fails))
    return 0 if fails == 0 else 1


if __name__ == "__main__":
    if len(sys.argv) != 2:
        sys.stderr.write("uso: check-w1-shape.py <validate.yml>\n")
        sys.exit(2)
    sys.exit(main(sys.argv[1]))
