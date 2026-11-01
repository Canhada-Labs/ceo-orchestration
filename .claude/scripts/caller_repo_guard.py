#!/usr/bin/env python3
"""Fotografa o repositório que chamou um harness e acusa o que mudou nele.

Item 14 (b) do PLAN-194-FOLLOWUP-v1-4-4-backlog. Duas vezes na S363 um harness ou uma
lane de revisão mexeu no checkout principal sem nenhum vermelho: crases num comentário
dentro de um heredoc sem aspas rodaram ``git switch -c`` no cwd do chamador, e um
``cd <sombra> ; git checkout`` cujo ``cd`` falhou rodou o ``git`` no checkout principal.
Nos dois a ref ``main`` e a árvore ficaram intactas, então só o HEAD contava a história.

A regressão de todo harness é esta: HEAD, ``symbolic-ref`` e ``for-each-ref`` do
repositório chamador iguais antes e depois da corrida.

Uso num harness Python::

    antes = caller_repo_guard.snapshot(REPO)
    ...
    problemas = caller_repo_guard.differences(antes, caller_repo_guard.snapshot(REPO))

Uso num harness de shell::

    python3 .claude/scripts/caller_repo_guard.py snapshot --repo "$R" --out "$T/antes.json"
    ...
    python3 .claude/scripts/caller_repo_guard.py verify --repo "$R" --from "$T/antes.json"

Saída da CLI: 0 igual (ou fotografia gravada); 1 mudou (uma linha por diferença);
2 entrada ilegível ou ``git`` sem resposta: sem fotografia não há como afirmar nada.

Fica fora, por desenho: a árvore de trabalho e o índice, que um harness de cerimônia
pode tocar de propósito. Uma corrida legítima que crie refs no próprio repositório ao
mesmo tempo aparece como diferença: harness roda em clone próprio.

Só stdlib, Python >= 3.9.
"""
from __future__ import annotations

import argparse
import json
import os
import subprocess
import sys
from typing import Dict, List, Optional

_TIMEOUT_S = 30


class GuardError(Exception):
    """O git não respondeu, ou a fotografia gravada não pode ser lida."""


def _git(repo: str, args: List[str], ok_codes: tuple = (0,)) -> "subprocess.CompletedProcess[str]":
    # `-C` só para leitura; o ambiente que reaponta o repositório não pode decidir a
    # resposta: o harness pergunta pelo REPO que nomeou.
    env = {k: v for k, v in os.environ.items() if k not in ("GIT_DIR", "GIT_WORK_TREE")}
    try:
        proc = subprocess.run(["git", "-C", repo] + args, capture_output=True, text=True,
                              timeout=_TIMEOUT_S, env=env, check=False)
    except (OSError, subprocess.SubprocessError) as exc:
        raise GuardError("git %s: %s" % (args[0], type(exc).__name__)) from None
    if proc.returncode not in ok_codes:
        raise GuardError("git %s saiu com rc %d" % (args[0], proc.returncode))
    return proc


def snapshot(repo: str) -> Dict[str, str]:
    """HEAD resolvido, para onde ele aponta (``""`` = destacado) e todas as refs."""
    head = _git(repo, ["rev-parse", "--verify", "-q", "HEAD"], ok_codes=(0, 1)).stdout.strip()
    symbolic = _git(repo, ["symbolic-ref", "-q", "HEAD"], ok_codes=(0, 1)).stdout.strip()
    refs = _git(repo, ["for-each-ref", "--format=%(refname) %(objectname)"]).stdout
    return {"head": head, "symbolic_ref": symbolic, "refs": refs}


def differences(before: Dict[str, str], after: Dict[str, str]) -> List[str]:
    """Uma frase por diferença; lista vazia = o repositório chamador está intacto."""
    out: List[str] = []
    if before.get("symbolic_ref") != after.get("symbolic_ref"):
        out.append("HEAD apontava para %r e agora aponta para %r"
                   % (before.get("symbolic_ref") or "(destacado)",
                      after.get("symbolic_ref") or "(destacado)"))
    if before.get("head") != after.get("head"):
        out.append("HEAD era %r e agora é %r" % (before.get("head"), after.get("head")))
    was = set((before.get("refs") or "").splitlines())
    now = set((after.get("refs") or "").splitlines())
    out.extend("ref sumiu ou mudou: %s" % line for line in sorted(was - now))
    out.extend("ref nova ou mudada: %s" % line for line in sorted(now - was))
    return out


def _load(path: str) -> Dict[str, str]:
    try:
        with open(path, encoding="utf-8") as handle:
            data = json.load(handle)
    except (OSError, ValueError, RecursionError) as exc:
        raise GuardError("fotografia ilegível: %s" % type(exc).__name__) from None
    if not isinstance(data, dict) or set(data) != {"head", "symbolic_ref", "refs"} \
            or not all(isinstance(v, str) for v in data.values()):
        raise GuardError("fotografia ilegível: formato inesperado")
    return data


def main(argv: Optional[List[str]] = None) -> int:
    parser = argparse.ArgumentParser(description=__doc__.splitlines()[0])
    sub = parser.add_subparsers(dest="command", required=True)
    take = sub.add_parser("snapshot")
    take.add_argument("--repo", required=True)
    take.add_argument("--out", required=True)
    check = sub.add_parser("verify")
    check.add_argument("--repo", required=True)
    check.add_argument("--from", dest="source", required=True)
    args = parser.parse_args(argv)
    try:
        if args.command == "snapshot":
            data = snapshot(args.repo)
            try:
                with open(args.out, "w", encoding="utf-8") as handle:
                    json.dump(data, handle)
            except OSError as exc:
                raise GuardError("não gravei a fotografia: %s" % type(exc).__name__) from None
            return 0
        found = differences(_load(args.source), snapshot(args.repo))
    except GuardError as exc:
        print("caller-repo-guard: %s" % exc, file=sys.stderr)
        return 2
    for line in found:
        print("caller-repo-guard: %s" % line)
    return 1 if found else 0


if __name__ == "__main__":
    sys.exit(main())
