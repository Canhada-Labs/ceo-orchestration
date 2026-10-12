#!/usr/bin/env python3
"""PLAN-186 W0, item C2 (S363) -- re-derivação do split construtor/refutador
da noite S338 com o instrumento SHIPADO, e da figura de -US$ 1.369/mês.

READ-ONLY. Sem rede, sem escrita, não toca o audit log. Importa
`.claude/scripts/ceo-cost-transcripts.py` como biblioteca e usa AS MESMAS
funções que a CLI usa (`_extract_record`, `scan_files`, `dedup`,
`load_pricing`, `price_records`). O papel de cada agente vem do registro da
corrida `<project-dir>/<session>/workflows/<run>.json` (`workflowProgress[]`,
tipo `workflow_agent`: `agentId` + `phaseTitle`), porque os sidecars
`agent-*.meta.json` dessa corrida só carregam `agentType` e `spawnDepth`.
Imprime JSON com ids, contagens, classes de token e USD -- nunca texto de
prompt, rótulo ou caminho.

Uso (da raiz do repo):
    python3 .claude/plans/PLAN-186/w0/c2-split-rederivation-S363/classify-s338.py
    ... --figure   # + perfil de 30 d (lê o corpus inteiro: PESADO)

rc 0 = ok; rc 2 = entrada recusada pelo nome (registro ausente ou ilegível,
fase desconhecida, agente sem transcript ou transcript sem agente).
"""
from __future__ import annotations

import argparse
import dataclasses
import importlib.util
import json
import sys
from pathlib import Path
from typing import Any, Dict, List

_REPO = Path(__file__).resolve().parents[5]
_INSTRUMENT = _REPO / ".claude" / "scripts" / "ceo-cost-transcripts.py"

#: `phaseTitle` do registro -> papel. Qualquer outra fase é RECUSADA (rc 2).
PHASE_ROLE = {"Cure": "construtor", "Build": "construtor", "Verify": "refutador"}
#: Desenho = atribuição DECLARADA do relatório 05 §2.2 (política C), não derivada.
DESIGN_DEFAULT = "aeee4ec1aac1a5e3c"
#: Janela de 30 d do relatório 05, como o AC-1 do PLAN-186 a reproduz (S344).
AC1_SINCE_AT = "2026-08-03T00:00:00Z"
AC1_UNTIL = "2026-09-02T12:55:05.807Z"
CLASSES = ("input_tokens", "output_tokens", "cache_read_tokens",
           "cache_write_5m", "cache_write_1h")
#: Os três modelos da figura: (i) 100 % opus-5 contra (iv) b sonnet-5 + (1-b) fable-5-1.
FIG_BASE, FIG_BUILDER, FIG_REST = "claude-opus-5", "claude-sonnet-5", "claude-fable-5-1"


class Refused(Exception):
    pass


def load_instrument() -> Any:
    spec = importlib.util.spec_from_file_location("ceo_cost_transcripts", _INSTRUMENT)
    if spec is None or spec.loader is None:
        raise Refused("instrumento ausente: %s" % _INSTRUMENT.name)
    mod = importlib.util.module_from_spec(spec)
    sys.modules[spec.name] = mod  # os @dataclass do instrumento resolvem o módulo por nome
    spec.loader.exec_module(mod)
    return mod


def phases_from_run(run_json: Path) -> Dict[str, str]:
    try:
        obj = json.loads(run_json.read_bytes())
    except (OSError, ValueError) as exc:
        raise Refused("registro da corrida ilegível (%s)" % type(exc).__name__)
    progress = obj.get("workflowProgress") if isinstance(obj, dict) else None
    if not isinstance(progress, list):
        raise Refused("registro sem lista workflowProgress")
    out: Dict[str, str] = {}
    for item in progress:
        if not isinstance(item, dict) or item.get("type") != "workflow_agent":
            continue
        agent, phase = item.get("agentId"), item.get("phaseTitle")
        if not isinstance(agent, str) or not agent or agent in out:
            raise Refused("workflow_agent sem agentId ou repetido")
        if phase not in PHASE_ROLE:
            raise Refused("fase desconhecida no registro: %r" % (phase,))
        out[agent] = phase
    if not out:
        raise Refused("registro sem nenhum workflow_agent")
    return out


def records_05style(cct: Any, path: Path) -> List[Any]:
    """O agregador do relatório 05: chave (requestId, apiBlockIndex,
    message.id) e a PRIMEIRA linha vence (o defeito que a W0 curou)."""
    seen: Dict[Any, Any] = {}
    counters = cct.ScanCounters()
    with path.open("rb") as f:
        for raw in f:
            if b'"assistant"' not in raw or b'"usage"' not in raw:
                continue
            try:
                obj = json.loads(raw)
            except ValueError:
                continue
            if not isinstance(obj, dict):
                continue
            rec = cct._extract_record(obj, "subagent", path.parent.name, counters)
            if rec is None:
                continue
            msg = obj.get("message") or {}
            seen.setdefault((obj.get("requestId"), obj.get("apiBlockIndex"), msg.get("id")), rec)
    return list(seen.values())


def totals(cct: Any, recs: List[Any], table: Dict[str, Any]) -> Dict[str, Any]:
    priced = cct.price_records(recs, table)
    t: Dict[str, Any] = {c: sum(getattr(p.rec, c) for p in priced) for c in CLASSES}
    t["turns"] = len(priced)
    t["raw_tokens"] = sum(t[c] for c in CLASSES)
    t["usd"] = round(sum(p.cost_usd for p in priced), 6)
    t["unresolved_turns"] = sum(1 for p in priced if not p.resolved)
    return t


def split(agents: List[Dict[str, Any]], key: str, design: str) -> Dict[str, Any]:
    out: Dict[str, Any] = {}
    for name, cls_of in (("duas_vias", lambda a: a["role"]),
                         ("tres_vias", lambda a: "desenho" if a["agent"] == design else a["role"])):
        sums: Dict[str, float] = {}
        for a in agents:
            sums[cls_of(a)] = sums.get(cls_of(a), 0) + a["instrumento"][key]
        whole = sum(sums.values())
        out[name] = {k: {"abs": round(v, 6), "share": round(v / whole, 6) if whole else None}
                     for k, v in sorted(sums.items())}
    return out


def figure(cct: Any, project_dir: Path, table: Dict[str, Any], b_values: Dict[str, float]) -> Dict[str, Any]:
    _, sub = cct.discover_files(project_dir)
    recs = cct.scan_files(sub, "subagent", project_dir, cct.ScanCounters())
    lo, hi = cct._parse_instant(AC1_SINCE_AT, "--since-at"), cct._parse_instant(AC1_UNTIL)
    recs, _ = cct.dedup([r for r in recs if lo <= r.ts <= hi])
    all_as = {m: round(sum(p.cost_usd for p in cct.price_records(
        [dataclasses.replace(r, model=m) for r in recs], table)), 6) for m in (FIG_BASE, FIG_BUILDER, FIG_REST)}
    delta = {k: round(b * all_as[FIG_BUILDER] + (1 - b) * all_as[FIG_REST] - all_as[FIG_BASE], 6)
             for k, b in sorted(b_values.items())}
    return {"janela": [AC1_SINCE_AT, AC1_UNTIL], "servido": totals(cct, recs, table),
            "tudo_em": all_as, "delta_iv_menos_i": delta}


def main(argv: List[str]) -> int:
    p = argparse.ArgumentParser(prog="classify-s338.py")
    p.add_argument("--project-dir", default=None)
    p.add_argument("--session", default="f52979b1-4c83-4346-9217-5f07d8d51bde")
    p.add_argument("--run", default="wf_e3144372-b04")
    p.add_argument("--design-agent", default=DESIGN_DEFAULT)
    p.add_argument("--figure", action="store_true")
    args = p.parse_args(argv)
    try:
        cct = load_instrument()
        project_dir = Path(args.project_dir) if args.project_dir else cct._default_project_dir()
        if project_dir is None or not project_dir.is_dir():
            raise Refused("--project-dir inexistente")
        base = project_dir / args.session
        phases = phases_from_run(base / "workflows" / (args.run + ".json"))
        run_dir = base / "subagents" / "workflows" / args.run
        files = {f.name[len("agent-"):-len(".jsonl")]: f for f in sorted(run_dir.glob("agent-*.jsonl"))}
        if set(files) != set(phases):
            raise Refused("agentes do registro != transcripts da corrida (%d vs %d)" % (len(phases), len(files)))
    except Refused as exc:
        sys.stderr.write("classify-s338: RECUSADO: %s\n" % exc)
        return 2
    table = cct.load_pricing(None).table
    agents: List[Dict[str, Any]] = []
    for agent in sorted(files):
        recs, _ = cct.dedup(cct.scan_files([files[agent]], "subagent", project_dir, cct.ScanCounters()))
        agents.append({
            "agent": agent, "phase": phases[agent], "role": PHASE_ROLE[phases[agent]],
            "models": sorted({r.model for r in recs}),
            "ts": [min(r.ts for r in recs).isoformat(), max(r.ts for r in recs).isoformat()] if recs else None,
            "instrumento": totals(cct, recs, table),
            "relatorio05": totals(cct, records_05style(cct, files[agent]), table),
        })
    out: Dict[str, Any] = {
        "agentes": agents,
        "soma": {},
        "split_raw_tokens": split(agents, "raw_tokens", args.design_agent),
        "split_usd": split(agents, "usd", args.design_agent),
    }
    for view in ("instrumento", "relatorio05"):
        out["soma"][view] = {k: round(sum(a[view][k] for a in agents), 6)
                             for k in ("turns", "raw_tokens", "usd") + CLASSES}
    if args.figure:
        b = {"publicado_0.80": 0.80,
             "rederivado_raw": out["split_raw_tokens"]["duas_vias"]["construtor"]["share"],
             "rederivado_usd": out["split_usd"]["duas_vias"]["construtor"]["share"]}
        out["figura"] = figure(cct, project_dir, table, b)
    print(json.dumps(out, indent=2, sort_keys=True))
    return 0


if __name__ == "__main__":
    sys.exit(main(sys.argv[1:]))
