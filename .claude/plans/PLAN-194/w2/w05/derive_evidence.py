#!/usr/bin/env python3
"""Deriva `results/` da W0.5 no HEAD (PLAN-194) a partir dos artefatos do run.

  python3 .claude/plans/PLAN-194/w2/w05/derive_evidence.py --pack DIR [--check]

`--pack` é o checkpoint fora do repositório (`s363-packs/fd12/`), com os summaries e o
`calls.json` originais, os `raw.jsonl` por processo e as marcas do guard do X7; cada
fonte tem o sha256 PINADO abaixo e uma fonte divergente é recusa nomeada. Saídas, em
`results/` ao lado deste arquivo:

  summary-a.json, summary-b.json, summary-info5s.json, x7-calls.json, guard-C1.mark,
  guard-C2.mark   cópias SANITIZADAS só em caminhos pessoais (regra personal-path do
                  check_contamination); números intactos, conferidos folha a folha
  evidence.json   derivado dos raw e das marcas: última marca de cada morte (a regra
                  `_last_mark` do instrumento v2, importada dele), máximo e 2.º da
                  latência, saídas acima de 3.000 ms, descartes pelo critério v1 e pelo
                  critério (ii) do pré-registro pós-cura, máximo e p95 da X5, o
                  `timeout_ms_of_run` de cada braço e os drains do X7
  SHA256SUMS      cópia, origem e raw de cada arquivo, e o sha256 deste derivador

`--check` refaz tudo em memória e compara byte a byte com o que está em `results/`, sem
escrever. Stdlib only, Python >= 3.9; nada roda no import.
"""

from __future__ import annotations

import argparse
import hashlib
import importlib.util
import json
import math
import re
import sys
from pathlib import Path
from typing import Any, Dict, List, Optional, Tuple

HERE = Path(__file__).resolve().parent
RESULTS = HERE / "results"
INSTRUMENT = HERE / "w05_harness.py"
T_MS = 3000.0

RAW: Dict[str, Tuple[str, str]] = {
    "a": ("runs/head-20261009T114839Z/raw.jsonl", "8328ad79feae9809068dd359bb3c99f14e1fc42a4edd81786d711fe6a1547e13"),
    "b": ("runs/head-20261009T115531Z/raw.jsonl", "5ded17159a1520bed6057b67cd00e2feadf9f33f43f82cca4108486b16156f33"),
    "info5s": ("runs/head-20261009T120436Z/raw.jsonl", "7d0e21cb2660374796f7cd4431ebcc676ac89949e9fec7d7187a4e257357ca34"),
}
COPIES: Dict[str, Tuple[str, str, str]] = {
    "summary-a.json": ("runs/head-20261009T114839Z/summary.json", "0ec74907126354b75b8bdbfda07e79ecc80083cefc6e0831328451f1828285ec", "a"),
    "summary-b.json": ("runs/head-20261009T115531Z/summary.json", "f9e61739adbd369a76583a09479e16f07ad626a459425244f6507be39d7a5754", "b"),
    "summary-info5s.json": ("runs/head-20261009T120436Z/summary.json", "5e120f0b38f656f08688c754e6ce5b65503dd2aa4269c65430b32a4ffa9d6d51", "info5s"),
    "x7-calls.json": ("x7/calls.json", "281c5c1b0866efa10b2a2255df6a12143dc6f3028a5aface9dced81e084c55c2", ""),
}
MARKS: Dict[str, Tuple[str, str]] = {
    "guard-C1.mark": ("x7/guard-C1.mark", "8fc4d85f021af536490979a2fbe4ee7156a60b94094988a23a5f3a387ea6782e"),
    "guard-C2.mark": ("x7/guard-C2.mark", "1f7341b13989e665fbd1ee3ca4502966933b84f66f93a48c9f6c55ee2a1881b8"),
}
# A raiz das homes do macOS entra por constante: o padrão GENÉRICO dos regex abaixo não é
# caminho pessoal, e escrito por extenso a regra personal-path do check_contamination o lê
# como se fosse um.
_ROOT = "Users"
SUBS = [
    (re.compile(r"/private/tmp/claude-\d+/-" + _ROOT + r"-[A-Za-z0-9._]+-[A-Za-z0-9._-]*?/"
                r"[0-9a-f]{8}-[0-9a-f]{4}-[0-9a-f]{4}-[0-9a-f]{4}-[0-9a-f]{12}/scratchpad"), "<SCRATCH>"),
    (re.compile(r"/" + _ROOT + r"/[A-Za-z0-9._-]+"), "<HOME>"),
    (re.compile(r"-" + _ROOT + r"-[A-Za-z0-9._]+-"), "-" + _ROOT + "-<user>-"),
    (re.compile(r"/var/folders/[A-Za-z0-9_]+/[A-Za-z0-9_]+/T/"), "<TMPDIR>/"),
]
HEADER = [
    "# W0.5 no HEAD (PLAN-194) — resultados; 2026-10-09, S363 (FD-12).",
    "# Instrumento v1: .claude/plans/PLAN-194/w2/w05/w05_harness.py sha256 "
    "27473c1d8ab7fcad41c4e98bafee1ecb0d9431468dda429938e3651cc1e98f8c (mediu o HEAD).",
    "# Cópias SANITIZADAS só em caminhos pessoais (regra personal-path do",
    "# check_contamination): scratch da sessão -> <SCRATCH>, /Users/<nome> -> <HOME>,",
    "# -Users-<nome>- -> -Users-<user>-, /var/folders/../T/ -> <TMPDIR>/. Números intactos",
    "# (conferidos folha a folha). Originais e raw.jsonl ficam FORA do repositório",
    "# (checkpoint s363-packs/fd12/); o sha256 do original vai em «origem».",
    "# Tudo aqui é refeito por ../derive_evidence.py --pack <checkpoint> (--check confere).",
    "",
]


def _die(msg: str) -> None:
    sys.stderr.write("derive_evidence: ERRO: %s\n" % msg)
    raise SystemExit(2)


def _sha(b: bytes) -> str:
    return hashlib.sha256(b).hexdigest()


def _read_pinned(pack: Path, rel: str, want: str) -> bytes:
    b = (pack / rel).read_bytes()
    if _sha(b) != want:
        _die("fonte divergente do sha256 pinado: %s" % rel)
    return b


def _sanitize(txt: str) -> str:
    for rx, rep in SUBS:
        txt = rx.sub(rep, txt)
    if ("/" + _ROOT + "/") in txt or re.search(r"-" + _ROOT + r"-(?!<user>-)", txt):
        _die("caminho pessoal residual depois da sanitização")
    return txt


def _leaves(o: Any, path: str = ""):
    if isinstance(o, dict):
        for k, v in o.items():
            yield from _leaves(v, path + "/" + str(k))
    elif isinstance(o, list):
        for i, v in enumerate(o):
            yield from _leaves(v, path + "/" + str(i))
    else:
        yield path, o


def _instrument_last_mark():
    spec = importlib.util.spec_from_file_location("w05_harness_v2", str(INSTRUMENT))
    mod = importlib.util.module_from_spec(spec)
    prev, sys.dont_write_bytecode = sys.dont_write_bytecode, True  # sem __pycache__ no repo
    try:
        spec.loader.exec_module(mod)  # o instrumento não roda nada no import
    finally:
        sys.dont_write_bytecode = prev
    return mod._last_mark


def _pct(vals: List[float], p: float) -> float:
    s = sorted(vals)
    return s[max(1, int(math.ceil(p * len(s)))) - 1]


def _cells(recs: List[Dict[str, Any]], last_mark) -> Dict[str, Any]:
    out: Dict[str, Any] = {}
    for c in sorted({r["cell"] for r in recs if not r["cell"].startswith(("WARMUP", "CTRL"))}):
        rr = [r for r in recs if r["cell"] == c]
        lat = sorted((r["lat_exit_ms"] for r in rr if r["lat_exit_ms"] is not None), reverse=True)
        deaths = [{"unit": r["unit"], "slot": r["slot"], "last_mark": last_mark(r), "lat_exit_ms": r["lat_exit_ms"]}
                  for r in rr if r["killed"]]
        lm: Dict[str, int] = {}
        for d in deaths:
            lm[d["last_mark"]] = lm.get(d["last_mark"], 0) + 1
        over = [r for r in rr if (r["lat_exit_ms"] or 0) > T_MS]
        e: Dict[str, Any] = {
            "N": len(rr), "killed": len(deaths), "killed_last_marks": lm,
            "exits_over_3000ms": len(over),
            "exits_over_3000ms_delivered_by_v1": sum(1 for r in over if r["delivered"]),
            "discarded_v1": sum(1 for r in rr if not r["delivered"]),
            "discarded_killed_or_over_3000ms": sum(1 for r in rr if (not r["delivered"]) or (r["lat_exit_ms"] or 0) > T_MS),
            "lat_exit_max_ms": lat[0] if lat else None,
            "lat_exit_2nd_ms": lat[1] if len(lat) > 1 else None,
            "deaths": deaths,
            "over_3000ms_exits": [{"unit": r["unit"], "slot": r["slot"], "lat_exit_ms": r["lat_exit_ms"],
                                   "killed": r["killed"], "delivered_v1": r["delivered"]} for r in over],
        }
        x5 = [r["x5_ms"] for r in rr if r.get("x5_ms") is not None]
        if x5:
            e["x5_N"], e["x5_max_ms"] = len(x5), max(x5)
            e["x5_p95_ms"] = _pct(x5, 0.95) if len(x5) >= 100 else None
        out[c] = e
    return out


def derive(pack: Path) -> Dict[str, bytes]:
    files: Dict[str, bytes] = {}
    timeouts: Dict[str, float] = {}
    for dst, (rel, want, arm) in COPIES.items():
        raw = _read_pinned(pack, rel, want)
        txt = _sanitize(raw.decode("utf-8"))
        a, b = json.loads(raw), json.loads(txt)
        if [x for x in _leaves(a) if not isinstance(x[1], str)] != [x for x in _leaves(b) if not isinstance(x[1], str)]:
            _die("a sanitização mudou um número em %s" % dst)
        files[dst] = txt.encode("utf-8")
        if arm:
            timeouts[arm] = float(a["substrate_start"]["hook_timeout_s"]) * 1000.0
    last_mark = _instrument_last_mark()
    ev: Dict[str, Any] = {
        "schema": "w05-evidence-r3", "timeout_ms": T_MS,
        "nota": "derivado por derive_evidence.py dos raw.jsonl e das marcas do guard do X7 (fora do repositorio, "
                "sha256 abaixo); ultima marca = regra _last_mark do instrumento v2 (marcas com instante, inclusive o "
                "retorno de cada drain; contadores fora); os campos *_3000ms usam o corte FIXO de 3.000 ms, inclusive "
                "no braco info5s, cujo run matava aos timeout_ms_of_run = 5.000 ms; discarded_v1 = criterio do "
                "instrumento v1 (morta pelo driver); discarded_killed_or_over_3000ms = criterio (ii) do pre-registro "
                "pos-cura",
        "sources": {}, "arms": {},
    }
    for arm, (rel, want) in RAW.items():
        b = _read_pinned(pack, rel, want)
        recs = [json.loads(l) for l in b.decode("utf-8").splitlines() if l.strip()]
        ev["sources"][arm] = {"raw": "s363-packs/fd12/" + rel, "sha256": want, "records": len(recs)}
        ev["arms"][arm] = {"timeout_ms_of_run": timeouts[arm], "cells": _cells(recs, last_mark)}
    x7: Dict[str, Any] = {}
    for dst, (rel, want) in MARKS.items():
        txt = _sanitize(_read_pinned(pack, rel, want).decode("utf-8"))
        files[dst] = txt.encode("utf-8")
        marks: Dict[str, int] = {}
        drains = []
        for line in txt.splitlines():
            parts = line.split(" ", 2)
            if len(parts) < 2:
                continue
            if parts[0] == "drain":
                drains.append(json.loads(parts[2]))
            elif parts[0] not in marks:
                marks[parts[0]] = int(parts[1])
        x7[dst.split("-")[1].split(".")[0]] = {
            "source": "results/" + dst, "origin_sha256": want, "start": marks.get("start"),
            "flushed": marks.get("flushed"), "exit_sleep_begin": marks.get("exit_sleep_begin"),
            "atexit_last_present": "atexit_last" in marks,
            "flush_after_start_ms": (marks["flushed"] - marks["start"]) / 1e6 if "flushed" in marks else None,
            "drains": [{"t0": d["t0"], "force": d["force"], "ok": d["ok"], "appended": d["appended"],
                        "after_start_s": (d["t0"] - marks["start"]) / 1e9} for d in drains],
        }
    ev["x7"] = x7
    evtxt = _sanitize(json.dumps(ev, indent=1, sort_keys=True, ensure_ascii=False) + "\n")
    files["evidence.json"] = evtxt.encode("utf-8")
    lines = list(HEADER)
    for dst, (rel, want, arm) in COPIES.items():
        lines.append("%s  %s" % (_sha(files[dst]), dst))
        lines.append("#   origem: %s  s363-packs/fd12/%s" % (want, rel))
        if arm:
            lines.append("#   raw (nao commitado): %s  s363-packs/fd12/%s" % (RAW[arm][1], RAW[arm][0]))
    for dst, (rel, want) in MARKS.items():
        lines.append("%s  %s" % (_sha(files[dst]), dst))
        lines.append("#   origem: %s  s363-packs/fd12/%s" % (want, rel))
    lines.append("%s  evidence.json" % _sha(files["evidence.json"]))
    for rel, want in list(RAW.values()) + list(MARKS.values()):
        lines.append("#   derivado de: %s  s363-packs/fd12/%s" % (want, rel))
    lines.append("%s  ../derive_evidence.py" % _sha(Path(__file__).resolve().read_bytes()))
    lines.append("#   o derivador; usa _last_mark de ../w05_harness.py (sha256 %s)" % _sha(INSTRUMENT.read_bytes()))
    files["SHA256SUMS"] = ("\n".join(lines) + "\n").encode("utf-8")
    return files


def main(argv: Optional[List[str]] = None) -> int:
    ap = argparse.ArgumentParser(description="deriva results/ da W0.5 no HEAD (PLAN-194)")
    ap.add_argument("--pack", required=True, help="checkpoint s363-packs/fd12/ (fora do repositório)")
    ap.add_argument("--check", action="store_true", help="compara sem escrever")
    a = ap.parse_args(argv)
    files = derive(Path(a.pack).expanduser())
    bad = 0
    for name, data in files.items():
        p = RESULTS / name
        if a.check:
            same = p.is_file() and p.read_bytes() == data
            bad += 0 if same else 1
            sys.stdout.write("%s %s\n" % ("OK  " if same else "DIFF", name))
        else:
            RESULTS.mkdir(parents=True, exist_ok=True)
            p.write_bytes(data)
            sys.stdout.write("escrito %s\n" % name)
    return 1 if bad else 0


if __name__ == "__main__":
    raise SystemExit(main())
