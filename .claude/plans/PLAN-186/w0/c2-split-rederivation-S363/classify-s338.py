#!/usr/bin/env python3
"""PLAN-186 W0 C2 (S363): re-derivação do split construtor/refutador da noite S338 e
da figura de -US$ 1.369/mês com o instrumento SHIPADO (`.claude/scripts/
ceo-cost-transcripts.py`, importado como biblioteca: as MESMAS funções da CLI).
Papel = `phaseTitle` do registro `<project-dir>/<session>/workflows/<run>.json`
(`workflowProgress[]`); os sidecars `agent-*.meta.json` só têm `agentType` e
`spawnDepth`. Sem rede; não escreve no repo nem no corpus (`--selftest` escreve só num
diretório temporário). Imprime ids, contagens e USD, nunca prompt, rótulo ou caminho.

Uso, da raiz do repo: sem flag = os 7 transcripts; `--figure` = + perfil de 30 d (corpus
inteiro: PESADO); `--selftest` = recusas em fixtures sintéticas (não lê o corpus).
rc 0 = ok; rc 1 = selftest falhou; rc 2 = entrada recusada pelo nome (registro ausente
ou ilegível, fase desconhecida ou não-texto, agente sem transcript ou transcript sem agente).
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
CLASSES = ("input_tokens", "output_tokens", "cache_read_tokens", "cache_write_5m", "cache_write_1h")
#: Os três modelos da figura: (i) 100 % opus-5 contra (iv) b sonnet-5 + (1-b) fable-5-1.
FIG_BASE, FIG_BUILDER, FIG_REST = "claude-opus-5", "claude-sonnet-5", "claude-fable-5-1"
#: 05 §1.4, coluna «subagentes» dos contrafactuais (perfil de 30 d todo num modelo).
PUB_S = {FIG_BASE: 2905.12, FIG_BUILDER: 1162.05, FIG_REST: 3043.47}
#: 05 §2.1 por agente: turnos, input, cache write, cache read, output, USD.
PUB_05 = {
    "ab057190f4e9d6857": (143, 19834, 4389481, 36445447, 23102, 65.33),
    "aeee4ec1aac1a5e3c": (262, 26238, 2609747, 97752023, 10585, 57.85),
    "a4df5635cd955284b": (68, 15282, 2327792, 11036638, 9563, 32.49),
    "aaec11aac18b6d0f3": (84, 10588, 1229934, 16904021, 4954, 19.95),
    "a506a7af45201e703": (144, 13292, 926165, 30292512, 6825, 19.62),
    "a27d43c4c3afec442": (64, 10043, 1138823, 8223927, 7756, 16.78),
    "aaaed0571dadc41d4": (78, 11135, 586043, 12643311, 17453, 11.47),
}


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
        if not isinstance(phase, str) or phase not in PHASE_ROLE:
            raise Refused("fase desconhecida no registro: %r" % (phase,))
        out[agent] = phase
    if not out:
        raise Refused("registro sem nenhum workflow_agent")
    return out


def records_05style(cct: Any, path: Path) -> List[Any]:
    """Agregador do 05: chave (requestId, apiBlockIndex, message.id), 1.ª linha vence (defeito da W0)."""
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
            rec = cct._extract_record(obj, "subagent", path.parent.name, counters) if isinstance(obj, dict) else None
            if rec is not None:
                key = (obj.get("requestId"), obj.get("apiBlockIndex"), (obj.get("message") or {}).get("id"))
                seen.setdefault(key, rec)
    return list(seen.values())


def totals(cct: Any, recs: List[Any], table: Dict[str, Any]) -> Dict[str, Any]:
    priced = cct.price_records(recs, table)
    t: Dict[str, Any] = {c: sum(getattr(p.rec, c) for p in priced) for c in CLASSES}
    t["turns"] = len(priced)
    t["raw_tokens"] = sum(t[c] for c in CLASSES)
    t["usd"] = round(sum(p.cost_usd for p in priced), 6)
    t["unresolved_turns"] = sum(1 for p in priced if not p.resolved)
    return t


def cells_05(t: Dict[str, Any]) -> tuple:
    return (t["turns"], t["input_tokens"], t["cache_write_5m"] + t["cache_write_1h"],
            t["cache_read_tokens"], t["output_tokens"], round(t["usd"], 2))


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


def deltas(s: Dict[str, float], b_values: Dict[str, float]) -> Dict[str, Any]:
    """Δ(b) = b·S(sonnet-5) + (1 − b)·S(fable-5-1) − S(opus-5), e a fração de S(opus-5)."""
    out: Dict[str, Any] = {}
    for k, b in sorted(b_values.items()):
        d = b * s[FIG_BUILDER] + (1 - b) * s[FIG_REST] - s[FIG_BASE]
        out[k] = {"abs": round(d, 6), "fracao": round(d / s[FIG_BASE], 6) if s[FIG_BASE] else None}
    return out


def ratio(num: float, den: float) -> Any:
    return round(num / den, 4) if den else None


def figure(cct: Any, project_dir: Path, table: Dict[str, Any], b_values: Dict[str, float]) -> Dict[str, Any]:
    _, sub = cct.discover_files(project_dir)
    recs = cct.scan_files(sub, "subagent", project_dir, cct.ScanCounters())
    lo, hi = cct._parse_instant(AC1_SINCE_AT, "--since-at"), cct._parse_instant(AC1_UNTIL)
    recs, _ = cct.dedup([r for r in recs if lo <= r.ts <= hi])
    all_as = {m: round(sum(p.cost_usd for p in cct.price_records(
        [dataclasses.replace(r, model=m) for r in recs], table)), 6) for m in (FIG_BASE, FIG_BUILDER, FIG_REST)}
    return {"janela": [AC1_SINCE_AT, AC1_UNTIL], "servido": totals(cct, recs, table),
            # o que o corpus VIVO ainda cobre da janela (registro mais antigo e mais novo)
            "cobertura": [min(r.ts for r in recs).isoformat(), max(r.ts for r in recs).isoformat()] if recs else None,
            "tudo_em": all_as, "delta_iv_menos_i": deltas(all_as, b_values)}


def selftest() -> int:
    """Recusas rc 2 e um rc 0 positivo sobre fixtures sintéticas num diretório temporário."""
    import contextlib, io, tempfile
    turn = json.dumps({"type": "assistant", "timestamp": "2026-09-02T02:00:00Z", "message": {
        "id": "m1", "model": "claude-fable-5-1", "usage": {"input_tokens": 1, "output_tokens": 1}}})
    cases = (("valido", ["Build"], "a", 0), ("registro ausente", None, "a", 2),
             ("fase desconhecida", ["Plan"], "a", 2), ("fase lista", [[]], "a", 2),
             ("fase dict", [{}], "a", 2), ("agente sem transcript", ["Build", "Verify"], "a", 2),
             ("transcript sem agente", ["Build"], "ab", 2))
    bad = 0
    for name, phases, transcripts, want in cases:
        with tempfile.TemporaryDirectory() as d:
            run = Path(d, "s", "subagents", "workflows", "wf")
            run.mkdir(parents=True)
            Path(d, "s", "workflows").mkdir()
            if phases is not None:
                Path(d, "s", "workflows", "wf.json").write_text(json.dumps({"workflowProgress": [
                    {"type": "workflow_agent", "agentId": "abc"[i], "phaseTitle": ph} for i, ph in enumerate(phases)]}))
            for a in transcripts:
                (run / ("agent-%s.jsonl" % a)).write_text(turn + "\n")
            with contextlib.redirect_stdout(io.StringIO()), contextlib.redirect_stderr(io.StringIO()):
                rc = main(["--project-dir", d, "--session", "s", "--run", "wf"])
        bad += rc != want
        print("selftest %-22s rc=%d esperado=%d %s" % (name, rc, want, "ok" if rc == want else "FALHOU"))
    return 1 if bad else 0


def main(argv: List[str]) -> int:
    p = argparse.ArgumentParser(prog="classify-s338.py")
    p.add_argument("--project-dir", default=None)
    p.add_argument("--session", default="f52979b1-4c83-4346-9217-5f07d8d51bde")
    p.add_argument("--run", default="wf_e3144372-b04")
    p.add_argument("--design-agent", default=DESIGN_DEFAULT)
    p.add_argument("--figure", action="store_true")
    p.add_argument("--selftest", action="store_true")
    args = p.parse_args(argv)
    if args.selftest:
        return selftest()
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
            "agent": agent, "phase": phases[agent], "role": PHASE_ROLE[phases[agent]], "models": sorted({r.model for r in recs}),
            "ts": [min(r.ts for r in recs).isoformat(), max(r.ts for r in recs).isoformat()] if recs else None,
            "instrumento": totals(cct, recs, table),
            "relatorio05": totals(cct, records_05style(cct, files[agent]), table),
        })
    out: Dict[str, Any] = {"agentes": agents, "soma": {},
                           "split_raw_tokens": split(agents, "raw_tokens", args.design_agent),
                           "split_usd": split(agents, "usd", args.design_agent)}
    for view in ("instrumento", "relatorio05"):
        out["soma"][view] = {k: round(sum(a[view][k] for a in agents), 6)
                             for k in ("turns", "raw_tokens", "usd") + CLASSES}
    # K0: células da tabela 05 §2.1 que o leitor «estilo 05» reproduz exatamente.
    out["k0_celulas_05"] = [sum(1 for a in agents for x, y in zip(cells_05(a["relatorio05"]),
                                PUB_05.get(a["agent"], ())) if x == y), 6 * len(PUB_05)]
    # K3: razão «estilo 05» / instrumento, por papel e no total.
    out["inflacao_05_sobre_instrumento"] = {
        role or "total": {k: ratio(sum(a["relatorio05"][k] for a in agents if role in (None, a["role"])),
                                   sum(a["instrumento"][k] for a in agents if role in (None, a["role"])))
                          for k in ("raw_tokens", "turns", "usd")}
        for role in ("construtor", "refutador", None)}
    b = {"publicado_0.80": 0.80,
         "rederivado_raw": out["split_raw_tokens"]["duas_vias"]["construtor"]["share"],
         "rederivado_usd": out["split_usd"]["duas_vias"]["construtor"]["share"],
         "sem_desenho_raw": out["split_raw_tokens"]["tres_vias"]["construtor"]["share"]}
    # só o split muda: a fórmula sobre os contrafactuais PUBLICADOS do 05 §1.4.
    out["figura_contrafactuais_05"] = deltas(PUB_S, b)
    if args.figure:
        out["figura"] = figure(cct, project_dir, table, b)
    print(json.dumps(out, indent=2, sort_keys=True))
    return 0


if __name__ == "__main__":
    sys.exit(main(sys.argv[1:]))
