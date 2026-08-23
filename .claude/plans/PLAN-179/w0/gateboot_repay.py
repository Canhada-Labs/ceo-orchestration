#!/usr/bin/env python3
"""PLAN-179 W0 Secção F -- instrumento do custo de gate-boot re-pago por compactação.

READ-ONLY. Sem rede, sem chamada de API, sem escrita -- não toca a cadeia HMAC
viva nem qualquer audit-log. Lê duas fontes que o harness já grava em disco:
o bloco `compactMetadata` do marcador `compact_boundary` e o `message.usage`
de cada turno não-sidechain do transcript da sessão.

Uso:
    python3 .claude/plans/PLAN-179/w0/gateboot_repay.py [transcript.jsonl]

Sem argumento, varre todos os transcripts do projeto (SLUG abaixo) e usa o
marcador `compact_boundary` encontrado neles (no momento da autoria há
exatamente um, neste projeto). Com um argumento, lê SÓ esse ficheiro --
usado pelo controlo negativo: `.../gateboot_repay.py /dev/null` deve
imprimir "NO compact_boundary found" e sair com status 1.
"""
from __future__ import annotations

import glob
import json
import os
import statistics
import sys
from typing import Dict, List, Optional, Tuple

SLUG = "-Users-joaocanhada-canhada-labs-ceo-orchestration"
PROJ = os.path.expanduser(os.path.join("~/.claude/projects", SLUG))

# Sessões com menos turnos não-sidechain que isto são excluídas da série "F a
# frio" -- tendem a ser probes/one-shots que não pagam o gate-boot completo
# de uma sessão CEO principal e distorceriam a média. O limiar é reportado,
# nunca escondido: cada exclusão é contada por categoria em `main()`.
MIN_TURNS_FOR_COLD_SERIES = 20


def _total_in(usage: Dict) -> int:
    return (int(usage.get("input_tokens") or 0)
            + int(usage.get("cache_read_input_tokens") or 0)
            + int(usage.get("cache_creation_input_tokens") or 0))


def scan(path):
    # type: (str) -> Tuple[Optional[Tuple[int, Dict]], List[Tuple[int, Dict]]]
    """Devolve (boundary, turns).

    boundary = (lineno, compactMetadata) do PRIMEIRO marcador compact_boundary
    encontrado, ou None. turns = lista ordenada por linha de (lineno, usage)
    para turnos com `message.usage`, excluindo isSidechain=true (sub-agentes).
    """
    boundary = None
    turns = []  # type: List[Tuple[int, Dict]]
    with open(path, encoding="utf-8", errors="replace") as fh:
        for lineno, line in enumerate(fh, 1):
            if '"compact_boundary"' in line:
                try:
                    ev = json.loads(line)
                except ValueError:
                    ev = {}
                if boundary is None and ev.get("subtype") == "compact_boundary":
                    boundary = (lineno, ev.get("compactMetadata") or {})
            if '"usage"' not in line:
                continue
            try:
                ev = json.loads(line)
            except ValueError:
                continue
            if ev.get("isSidechain"):
                continue
            msg = ev.get("message")
            if isinstance(msg, dict) and isinstance(msg.get("usage"), dict):
                turns.append((lineno, msg["usage"]))
    return boundary, turns


def main(argv):
    # type: (List[str]) -> int
    paths = [argv[1]] if len(argv) > 1 else sorted(
        glob.glob(os.path.join(PROJ, "*.jsonl")))

    cold = []  # type: List[int]  -- incluídos na série "F a frio"
    excluded_no_turns = 0
    excluded_warm_start = 0  # 1o turno já tem cache_read > 0 (não é arranque a frio)
    excluded_short = 0       # arranque a frio, mas < MIN_TURNS_FOR_COLD_SERIES turnos
    hit = None                # (path, boundary, turns) do ficheiro com compact_boundary

    for path in paths:
        boundary, turns = scan(path)
        if not turns:
            excluded_no_turns += 1
        else:
            first_cr = int(turns[0][1].get("cache_read_input_tokens") or 0)
            if first_cr != 0:
                excluded_warm_start += 1
            elif len(turns) < MIN_TURNS_FOR_COLD_SERIES:
                excluded_short += 1
            else:
                cold.append(_total_in(turns[0][1]))
        if boundary is not None:
            hit = (path, boundary, turns)

    print("scanned_files               = %d" % len(paths))
    print("cold-F censoring            : excluded_no_turns=%d excluded_warm_start=%d "
          "excluded_short(<%d turns)=%d included=%d"
          % (excluded_no_turns, excluded_warm_start, MIN_TURNS_FOR_COLD_SERIES,
             excluded_short, len(cold)))

    if hit is None:
        print("NO compact_boundary found -- nothing to derive")
        return 1

    path, (bline, meta), turns = hit
    post_tokens = int(meta.get("postTokens") or 0)
    pre_tokens = int(meta.get("preTokens") or 0)
    dropped = int(meta.get("cumulativeDroppedTokens") or 0)
    duration_ms = int(meta.get("durationMs") or 0)
    try:
        first_post = next(u for (ln, u) in turns if ln > bline)
    except StopIteration:
        print("boundary found at line %d but NO usage turn after it" % bline)
        return 1

    total_in = _total_in(first_post)
    cache_read = int(first_post.get("cache_read_input_tokens") or 0)
    cache_creation = int(first_post.get("cache_creation_input_tokens") or 0)
    base_in = int(first_post.get("input_tokens") or 0)
    floor = total_in - post_tokens
    recreated = cache_creation - post_tokens

    print("transcript                  = %s" % os.path.basename(path))
    print("boundary line                = %d  trigger=%s" % (bline, meta.get("trigger")))
    print("preTokens  (T, harness)       = %d" % pre_tokens)
    print("postTokens (S, harness)       = %d" % post_tokens)
    print("cumulativeDroppedTokens       = %d  durationMs=%d" % (dropped, duration_ms))
    print("1st post-boundary TOTAL_IN    = %d  (input=%d cache_read=%d cache_creation=%d)"
          % (total_in, base_in, cache_read, cache_creation))
    print("FLOOR re-paid at boundary     = %d   [= TOTAL_IN - postTokens]" % floor)
    print("  of which cache_creation     = %d   [= cache_creation - postTokens]" % recreated)
    print("  of which cache_read         = %d" % cache_read)

    # Controlo intra-sessão: o 1o turno da PRÓPRIA sessão que foi comprimida,
    # medido a frio (antes de qualquer compactação), como segunda rota
    # independente para a mesma grandeza (FLOOR).
    if turns and int(turns[0][1].get("cache_read_input_tokens") or 0) == 0:
        same_session_cold = _total_in(turns[0][1])
        delta = floor - same_session_cold
        print("cold F, same session          = %d  (delta vs FLOOR = %+d, %.2f%%)"
              % (same_session_cold, delta, 100.0 * delta / same_session_cold))
    else:
        print("cold F, same session          = n/a (1o turno da sessão não é arranque a frio)")

    if cold:
        vals = sorted(cold)
        n = len(vals)
        mean = sum(vals) / float(n)
        median = statistics.median(vals)
        # Censo (todas as sessões que sobraram da censura), não amostra de uma
        # população maior -- por isso desvio-padrão POPULACIONAL (divisor n),
        # não amostral (n-1).
        stdev = statistics.pstdev(vals) if n > 1 else 0.0
        spread = vals[-1] - vals[0]
        print("cold F series: n=%d min=%d max=%d mean=%.0f median=%.0f pstdev=%.0f "
              "spread=%d (%.1f%% of mean)"
              % (n, vals[0], vals[-1], mean, median, stdev, spread,
                 100.0 * spread / mean))
    else:
        print("cold F series: n=0 (nenhuma sessão sobrou após censura -- ver linha "
              "cold-F censoring acima)")
    return 0


if __name__ == "__main__":
    sys.exit(main(sys.argv))
