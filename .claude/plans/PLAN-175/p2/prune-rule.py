"""PLAN-175 W0a (AC-0.1 a AC-0.4): a regra de poda do §2 vira programa.

Três pernas (§2.1) sobre as skills core, todas lidas de disco:
- perna 0, elegibilidade, arquitetura D (OQ-1 do Owner, 2026-09-07): exclui da
  candidatura toda skill citada por um canal que NÃO emite evento. Enquanto
  nenhum canal emitir (EMITTING_CHANNELS vazio), é a união dos quatro canais
  do censo ``eligibility-census.py``, importado: canais, piso de VETO
  (``veto_floor: true`` em ``.claude/agents/``) e Gate 2 do CLAUDE.md têm uma
  fonte só e nenhum nome é digitado aqui;
- perna 1, denominador: MIN_OBSERVED_SPAWNS eventos ``agent_spawn`` e
  ``--min-window-coverage-days`` dias entre o 1.º e o último evento da família
  (PARÂMETRO; o padrão é o valor escrito no §2.1 até o Owner responder a OQ-2);
- perna 2, telemetria: zero ``agent_spawn`` com ``skill=<nome>``, pelo leitor
  nomeado (READER do censo, rodado com ``-B``).

Três saídas (§2.2): MANTER (não candidata, ou invocada), ARQUIVAR (candidata,
denominador suficiente, cadeia íntegra, zero invocações) e RECUSA, para TODAS,
quando o leitor falha, não acha log ou avisa linha/arquivo ilegível
(``telemetry_unavailable``), a cadeia não sai «intact» (``chain_not_intact``)
ou falta denominador (``insufficient_sample``).

Uso: prune-rule.py [--repo PATH] [--json] [--coverage-observed]
       [--min-window-coverage-days N] [--assert-keep-veto-floor]
       [--disable-eligibility] [--force-empty-telemetry] | --ac-matrix

Saída (§5): 0 a asserção pedida vale (sem ``--assert-keep-veto-floor`` ela é
só «a regra respondeu»); 2 erro de uso (bandeira desconhecida, input ausente,
ou piso de VETO / Gate 2 sem skill core, que tornaria a asserção vácua); 3 skill protegida (Gate 2 + piso de VETO) sairia ARQUIVAR, nomes em
``offenders``; 4 RECUSA. ``--json`` imprime sempre ``inputs``, ``skills[]``,
``exit_reason`` (ok, would_archive, os três motivos de RECUSA acima ou
usage_error) e ``offenders[]``. ``--coverage-observed`` neutraliza SÓ a
cobertura: o piso de spawns segue ativo, senão telemetria vazia com a perna 0
desligada arquivaria tudo (o caso do §4.2). ``--force-empty-telemetry`` não
roda o leitor e simula log vazio e íntegro. ``--ac-matrix`` gera a evidência
datada: os Checks da AC-0.1 a AC-0.4 e o controle do §4.2 sobre UMA leitura.

O leitor resolve o diretório de estado pelo resolvedor por projeto: numa sombra
use ``CLAUDE_PROJECT_DIR=<checkout do projeto>`` (só leitura). Só lê arquivos;
biblioteca padrão, Python >= 3.9.
"""
from __future__ import annotations

import argparse
import collections
import datetime as dt
import hashlib
import importlib.util
import json
import re
import subprocess
import sys
from pathlib import Path
from typing import Any, Dict, List, Optional, Tuple

sys.dont_write_bytecode = True  # importar o censo não deixa __pycache__ na árvore
HERE = Path(__file__).resolve().parent
EMITTING_CHANNELS: Tuple[str, ...] = ()  # §2.1, linha D: nenhum canal emite hoje
MIN_OBSERVED_SPAWNS = 100  # §2.1, perna 1
DEFAULT_MIN_COVERAGE_DAYS = 90  # §2.1 (round 1); OQ-2 do Owner aberta
LOG_NAME = re.compile(r"audit-log[^/]*\.jsonl")  # = o glob do leitor com --include-rotated
MATRIX = (  # (nome, bandeiras): os Checks da W0a e o controle do §4.2
    ("AC-0.1", []),
    ("AC-0.2", ["--coverage-observed", "--assert-keep-veto-floor"]),
    ("AC-0.3", ["--coverage-observed", "--assert-keep-veto-floor", "--disable-eligibility"]),
    ("AC-0.4/1", ["--force-empty-telemetry"]),
    ("AC-0.4/2", ["--coverage-observed"]),
    ("§4.2", ["--force-empty-telemetry", "--coverage-observed", "--assert-keep-veto-floor",
              "--disable-eligibility"]),
)


class UsageError(Exception):
    pass


class Parser(argparse.ArgumentParser):
    def error(self, message: str) -> None:  # type: ignore[override]
        raise UsageError(message)  # bandeira desconhecida ou valor inválido -> rc 2


def load_census() -> Any:
    spec = importlib.util.spec_from_file_location("plan175_census", str(HERE / "eligibility-census.py"))
    if spec is None or spec.loader is None:
        raise UsageError("eligibility-census.py ausente ao lado deste script")
    mod = importlib.util.module_from_spec(spec)
    spec.loader.exec_module(mod)
    return mod


def sha256(p: Path) -> str:
    return hashlib.sha256(p.read_bytes()).hexdigest()


def parse_ts(s: str) -> dt.datetime:
    t = dt.datetime.fromisoformat(s.replace("Z", "+00:00"))
    return t if t.tzinfo else t.replace(tzinfo=dt.timezone.utc)


def coverage(paths: List[Path]) -> Dict[str, Any]:
    """1.º e último ts dos arquivos que o leitor leu (a regra do heredoc JANELA do §4)."""
    first: Optional[str] = None
    last: Optional[str] = None
    partial = 0
    for f in paths:
        if not LOG_NAME.fullmatch(f.name) or not f.is_file():
            raise ValueError("arquivo inesperado do leitor")
        with open(f, "r", encoding="utf-8", errors="replace") as fh:
            for line in fh:
                if not line.endswith("\n"):
                    partial += 1  # cauda ainda sendo escrita: não é evento
                    continue
                if not line.strip():
                    continue
                ev = json.loads(line)  # linha completa ilegível -> ValueError -> RECUSA
                ts = (ev.get("ts") or ev.get("timestamp")) if isinstance(ev, dict) else None
                if isinstance(ts, str) and ts[:4].isdigit():
                    first = ts if first is None or ts < first else first
                    last = ts if last is None or ts > last else last
    days = (parse_ts(last) - parse_ts(first)).total_seconds() / 86400.0 if first and last else 0.0
    return {"since": "all", "first_ts": first, "last_ts": last,
            "coverage_days": int(days * 100) / 100.0,  # trunca: nunca arredonda para cima do piso
            "files": len(paths), "partial_tail_lines": partial}


def read_telemetry(cm: Any, repo: Path) -> Dict[str, Any]:
    t: Dict[str, Any] = {"status": "unavailable", "reader": "python3 -B " + cm.READER}
    try:
        p = subprocess.run([sys.executable, "-B"] + cm.READER.split(), cwd=str(repo),
                           capture_output=True, text=True, timeout=900)
        d = json.loads(p.stdout) if p.returncode == 0 else None
    except (OSError, subprocess.TimeoutExpired, ValueError) as e:
        return dict(t, reason="leitor: %s" % type(e).__name__)
    if not isinstance(d, dict):
        return dict(t, reason="leitor rc=%d" % p.returncode)
    warned = sum(1 for ln in (p.stderr or "").splitlines() if cm.READER_WARN.match(ln))
    t.update(chain_status=str(d.get("chain_status") or ""), reader_warnings=warned,
             events={"scanned": d.get("events_scanned"), "in_window": d.get("events_in_window"),
                     "agent_spawn": (d.get("discovery_health") or {}).get("total_invocations")})
    if not d.get("log_found"):
        return dict(t, reason="sem log no diretório de estado deste projeto (numa sombra: "
                    "CLAUDE_PROJECT_DIR=<checkout do projeto>)")
    if warned:
        return dict(t, reason="%d aviso(s) do leitor: linha ou arquivo ilegível" % warned)
    try:
        t["window"] = coverage([Path(x) for x in d.get("log_paths") or []])
    except (OSError, ValueError) as e:
        return dict(t, reason="cobertura: %s" % type(e).__name__)
    t["invocations"] = {r.get("skill"): int(r.get("invocations") or 0) for r in d.get("skills") or []}
    return dict(t, status="read")


def empty_telemetry(cm: Any) -> Dict[str, Any]:
    return {"status": "forced-empty", "reader": "python3 -B %s (não rodou: --force-empty-telemetry)"
            % cm.READER, "chain_status": "log vazio simulado: íntegro por vacuidade",
            "events": {"scanned": 0, "in_window": 0, "agent_spawn": 0}, "invocations": {},
            "window": {"since": "all", "first_ts": None, "last_ts": None, "coverage_days": 0.0,
                       "files": 0, "partial_tail_lines": 0}}


def evaluate(cm: Any, c: Dict[str, Any], t: Dict[str, Any], a: argparse.Namespace) -> Dict[str, Any]:
    excluded = [] if a.disable_eligibility else [ch for ch in cm.CHANNELS if ch not in EMITTING_CHANNELS]
    protected = set(c["veto_floor"]["skills"]) | set(c["gate2"]["skills"])
    win = dict(t.get("window") or {}, min_window_coverage_days=a.min_window_coverage_days,
               coverage_leg="neutralizada (--coverage-observed)" if a.coverage_observed else "ativa")
    spawns = int((t.get("events") or {}).get("agent_spawn") or 0)
    why: List[List[str]] = []
    if t["status"] == "unavailable":
        why.append(["telemetry_unavailable", t["reason"]])
    if t["status"] == "read" and not t["chain_status"].startswith("intact"):
        why.append(["chain_not_intact", t["chain_status"]])
    if t["status"] != "unavailable" and spawns < MIN_OBSERVED_SPAWNS:
        why.append(["insufficient_sample", "%d agent_spawn < %d" % (spawns, MIN_OBSERVED_SPAWNS)])
    cov = float(win.get("coverage_days") or 0.0)
    if t["status"] != "unavailable" and not a.coverage_observed and cov < a.min_window_coverage_days:
        why.append(["insufficient_sample", "cobertura %.2f d < %d d" % (cov, a.min_window_coverage_days)])
    inv = t.get("invocations")
    skills = []
    for s in c["core"]["names"]:
        cited = sorted(c["skills"][s]["cited_by"])
        cand = not set(cited) & set(excluded)
        n = None if inv is None else int(inv.get(s, 0))
        verdict = "RECUSA" if why else ("MANTER" if not cand or n else "ARQUIVAR")
        skills.append({"skill": s, "verdict": verdict, "candidate": cand, "cited_by": cited,
                       "invocations": n, "protected": s in protected})
    offenders = [x["skill"] for x in skills if x["protected"] and x["verdict"] == "ARQUIVAR"]
    if why:
        reason, rc = why[0][0], 4
    elif offenders:
        reason, rc = "would_archive", (3 if a.assert_keep_veto_floor else 0)
    else:
        reason, rc = "ok", 0
    arch = {"id": "nenhuma (--disable-eligibility)" if a.disable_eligibility else "D",
            "source": "OQ-1 do Owner, 2026-09-07: «D — não mensurável hoje»",
            "emitting_channels": list(EMITTING_CHANNELS), "excluded_channels": excluded}
    inputs = {
        "window": win, "events": dict(t.get("events") or {}, min_observed_spawns=MIN_OBSERVED_SPAWNS),
        "reader": t["reader"], "chain_status": t.get("chain_status"),
        "chain_scope": "log primário (o leitor verifica só ele; os rotacionados não)",
        "eligibility_architecture": arch, "telemetry": {"status": t["status"], "reason": t.get("reason")},
        "protected": {"gate2": c["gate2"]["skills"], "veto_floor_agents": c["veto_floor"]["agents"],
                      "veto_floor_skills": c["veto_floor"]["skills"]},
        "refusal_reasons": why, "census": {k: c["inputs"].get(k) for k in ("head_sha", "inputs_sha256")},
        "rule_sha256": sha256(Path(__file__).resolve()),
        "census_sha256": sha256(HERE / "eligibility-census.py"),
    }
    return {"schema": "plan175-prune-rule/1", "rc": rc, "exit_reason": reason,
            "offenders": offenders, "inputs": inputs, "skills": skills}


def build_parser() -> Parser:
    ap = Parser(description=(__doc__ or "").split("\n")[0])
    ap.add_argument("--repo", default=".", help="raiz do repositório (padrão: .)")
    ap.add_argument("--json", action="store_true", help="saída JSON")
    ap.add_argument("--coverage-observed", action="store_true", help="neutraliza a cobertura (perna 1)")
    ap.add_argument("--min-window-coverage-days", type=int, default=DEFAULT_MIN_COVERAGE_DAYS)
    ap.add_argument("--assert-keep-veto-floor", action="store_true", help="rc 3 se protegida sair ARQUIVAR")
    ap.add_argument("--disable-eligibility", action="store_true", help="desliga a perna 0 (controle)")
    ap.add_argument("--force-empty-telemetry", action="store_true", help="log vazio simulado")
    ap.add_argument("--ac-matrix", action="store_true", help="gera a evidência datada da W0a")
    return ap


def matrix(cm: Any, c: Dict[str, Any], a: argparse.Namespace, now: str) -> Tuple[int, Dict[str, Any]]:
    real = read_telemetry(cm, Path(a.repo).resolve())
    runs: Dict[str, Any] = {}
    inputs: Dict[str, Any] = {}
    per_skill: Dict[str, Any] = {}
    for name, flags in MATRIX:
        ra = build_parser().parse_args(["--min-window-coverage-days", str(a.min_window_coverage_days)] + flags)
        r = evaluate(cm, c, empty_telemetry(cm) if ra.force_empty_telemetry else real, ra)
        runs[name] = {"flags": flags, "rc": r["rc"], "exit_reason": r["exit_reason"],
                      "offenders": r["offenders"], "refusal_reasons": r["inputs"]["refusal_reasons"],
                      "verdicts": dict(sorted(collections.Counter(s["verdict"] for s in r["skills"]).items())),
                      "would_archive": [s["skill"] for s in r["skills"] if s["verdict"] == "ARQUIVAR"]}
        if name == "AC-0.1":
            inputs = dict(r["inputs"], generated_at=now)
            per_skill = {s["skill"]: {k: s[k] for k in ("invocations", "cited_by", "protected")}
                         for s in r["skills"]}
    return (0 if real["status"] == "read" else 4), {
        "schema": "plan175-prune-rule-matrix/1", "inputs": inputs, "runs": runs, "per_skill": per_skill}


def main(argv: Optional[List[str]] = None) -> int:
    raw = list(sys.argv[1:] if argv is None else argv)
    try:
        a = build_parser().parse_args(raw)
        if a.min_window_coverage_days < 0:
            raise UsageError("--min-window-coverage-days não pode ser negativo")
        if a.ac_matrix and (a.coverage_observed or a.assert_keep_veto_floor
                            or a.disable_eligibility or a.force_empty_telemetry):
            raise UsageError("--ac-matrix só aceita --repo e --min-window-coverage-days")
        cm = load_census()
    except (UsageError, OSError) as e:
        return usage_error(str(e), "--json" in raw)
    try:
        c = cm.census(Path(a.repo).resolve())
    except (cm.InputError, OSError) as e:  # input ausente sob --repo
        return usage_error(str(e), "--json" in raw)
    if (a.assert_keep_veto_floor or a.ac_matrix) and not (c["veto_floor"]["skills"] and c["gate2"]["skills"]):
        return usage_error("piso de VETO ou Gate 2 derivado sem skill core: a asserção seria vácua",
                           "--json" in raw)
    now = dt.datetime.now(dt.timezone.utc).strftime("%Y-%m-%dT%H:%M:%SZ")
    if a.ac_matrix:
        rc, out = matrix(cm, c, a, now)
        print(cm.render(out))
        return rc
    t = empty_telemetry(cm) if a.force_empty_telemetry else read_telemetry(cm, Path(a.repo).resolve())
    r = evaluate(cm, c, t, a)
    r["inputs"]["generated_at"] = now
    if a.json:
        print(cm.render(r))
    else:
        w, e = r["inputs"]["window"], r["inputs"]["events"]
        print("arquitetura %s; cobertura %s (mínimo %d d); piso %d agent_spawn" % (
            r["inputs"]["eligibility_architecture"]["id"], w["coverage_leg"],
            a.min_window_coverage_days, MIN_OBSERVED_SPAWNS))
        print("telemetria %s; cadeia %s; agent_spawn %s; cobertura %s d" % (
            t["status"], r["inputs"]["chain_status"], e.get("agent_spawn"), w.get("coverage_days")))
        print("vereditos %s" % dict(sorted(collections.Counter(s["verdict"] for s in r["skills"]).items())))
        print("exit_reason = %s; offenders = %s" % (r["exit_reason"], r["offenders"]))
    return r["rc"]


def usage_error(msg: str, as_json: bool) -> int:
    if as_json:
        print(json.dumps({"exit_reason": "usage_error", "error": msg, "inputs": {}, "skills": [],
                          "offenders": []}, ensure_ascii=False))
    print("prune-rule: ERRO: %s" % msg, file=sys.stderr)
    return 2


if __name__ == "__main__":
    sys.exit(main())
