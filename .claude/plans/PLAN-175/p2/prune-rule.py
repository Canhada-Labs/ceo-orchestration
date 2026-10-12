"""PLAN-175 W0a (AC-0.1 a AC-0.4): a regra de poda do §2 vira programa.

Pernas (§2.1), lidas de disco. 0, elegibilidade, arquitetura D (OQ-1 do Owner,
2026-09-07): exclui toda skill citada por canal que NÃO emite; sem canal
emitindo (EMITTING_CHANNELS vazio) é a união dos quatro canais do censo
``eligibility-census.py``, importado: canais, piso de VETO e Gate 2 têm uma
fonte só e nenhum nome é digitado aqui. 1, denominador: MIN_OBSERVED_SPAWNS
``agent_spawn`` e ``--min-window-coverage-days`` de cobertura (PARÂMETRO; o
padrão é o valor do §2.1 até a OQ-2 do Owner). 2, telemetria: zero
``agent_spawn`` com ``skill=<nome>`` pelo leitor nomeado (READER, com ``-B``).

Saídas (§2.2): MANTER, ARQUIVAR (candidata, denominador, cadeia íntegra, zero
invocações) e RECUSA para todas: ``telemetry_unavailable`` (o leitor falha,
não acha log ou avisa linha/arquivo ilegível), ``chain_not_intact`` (o
``chain_status`` do leitor, que verifica SÓ o log primário: ver
``inputs.chain_scope``; atestar os rotacionados antes de qualquer ARQUIVAR é
condição da W2, AC-2.0 e OQ-3) ou ``insufficient_sample``.

Código (§5): 0 a regra respondeu sem skill protegida (Gate 2 + piso de VETO)
em ARQUIVAR; 2 erro de uso: bandeira desconhecida (abreviação não vale) ou
input ausente, inclusive piso de VETO ou Gate 2 derivado vazio quando
``--assert-keep-veto-floor`` ou ``--ac-matrix`` pedem a asserção, que seria
vácua; 3 skill protegida sairia ARQUIVAR, com ou sem a bandeira, nomes em
``offenders``; 4 RECUSA. Toda saída JSON (``--json``, ``--ac-matrix`` e o erro
de uso com ``--json``) traz ``inputs``, ``skills[]``, ``exit_reason`` e
``offenders[]``. ``--coverage-observed`` neutraliza a perna 1 INTEIRA (§2.1 e
AC-0.2): é controle, para que a única variável entre a AC-0.2 e a AC-0.3 seja
a perna 0. ``--force-empty-telemetry`` simula log vazio e íntegro sem rodar o
leitor. ``--ac-matrix``: o envelope do run padrão (AC-0.1) mais ``runs``, os
Checks da AC-0.1 a AC-0.4 e dois controles do §4.2 sobre UMA leitura, cada um
com o predicado do seu Check; sai 0 se todos valem e 1 se algum reprova (o 1
dos pipes dos Checks; a matriz não é invocação do §5), nomes em
``failed_checks``.

Cobertura, política PRÓPRIA (não a do heredoc JANELA do §4): os arquivos que
o leitor devolveu (relativo = relativo a ``--repo``); linha que não é JSON =
RECUSA, salvo a última sem quebra (``partial_tail_lines``: escrita em curso);
conta ``ts``/``timestamp`` que começa por ano, comparado PARSEADO (ISO-8601
com segundos, fração cortada em microssegundos, sem fuso = UTC, outro formato
= RECUSA); TRUNCADA em centésimos de dia, nunca arredondada para cima do piso.
Numa sombra, rode com ``CLAUDE_PROJECT_DIR=<checkout do projeto>`` (só
leitura). Biblioteca padrão, Python >= 3.9.
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
TS = re.compile(r"(\d{4}-\d{2}-\d{2})[T ](\d{2}:\d{2}:\d{2})(?:[.,](\d+))?(Z|[+-]\d{2}:?\d{2})?")
INPUT_KEYS = {"window", "events", "reader", "chain_status", "eligibility_architecture"}
MATRIX = (  # (nome, bandeiras, predicado do Check sobre o run r e o censo c)
    ("AC-0.1", [], lambda r, c: not INPUT_KEYS - set(r["inputs"])),
    ("AC-0.2", ["--coverage-observed", "--assert-keep-veto-floor"], lambda r, c: r["rc"] == 0),
    ("AC-0.3", ["--coverage-observed", "--assert-keep-veto-floor", "--disable-eligibility"],
     lambda r, c: r["exit_reason"] == "would_archive" and set(c["gate2"]["skills"]) <= set(r["offenders"])),
    ("AC-0.4/1", ["--force-empty-telemetry"], lambda r, c: verdicts(r) == {"RECUSA"}),
    ("AC-0.4/2", ["--coverage-observed"], lambda r, c: verdicts(r) != {"RECUSA"}),
    ("§4.2/perna1", ["--force-empty-telemetry", "--assert-keep-veto-floor", "--disable-eligibility"],
     lambda r, c: r["exit_reason"] == "insufficient_sample" and "ARQUIVAR" not in verdicts(r)),
    ("§4.2/sem-pernas-0-e-1", ["--force-empty-telemetry", "--coverage-observed",
                               "--assert-keep-veto-floor", "--disable-eligibility"],
     lambda r, c: r["exit_reason"] == "would_archive" and protected(c) <= set(r["offenders"])),
)


class UsageError(Exception):
    pass


class Parser(argparse.ArgumentParser):
    def error(self, message: str) -> None:  # type: ignore[override]
        raise UsageError(message)  # bandeira desconhecida ou valor inválido -> rc 2


def verdicts(r: Dict[str, Any]) -> set:
    return {s["verdict"] for s in r["skills"]}


def count(r: Dict[str, Any]) -> Dict[str, int]:
    return dict(sorted(collections.Counter(s["verdict"] for s in r["skills"]).items()))


def protected(c: Dict[str, Any]) -> set:
    return set(c["veto_floor"]["skills"]) | set(c["gate2"]["skills"])


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
    m = TS.fullmatch(s.strip())
    if not m:
        raise ValueError("ts fora do ISO-8601 aceito")
    tz = m.group(4) or "+00:00"
    tz = "+00:00" if tz == "Z" else (tz if ":" in tz else tz[:3] + ":" + tz[3:])
    frac = (m.group(3) or "")[:6].ljust(6, "0")  # fromisoformat do 3.9 só aceita 3 ou 6 casas
    return dt.datetime.fromisoformat("%sT%s.%s%s" % (m.group(1), m.group(2), frac, tz))


def coverage(paths: List[Path]) -> Dict[str, Any]:
    """1.º e último instante dos arquivos que o leitor leu (política no docstring do módulo)."""
    first: Optional[Tuple[dt.datetime, str]] = None
    last: Optional[Tuple[dt.datetime, str]] = None
    partial = 0
    for f in paths:
        if not f.is_file():
            raise ValueError("arquivo do leitor sumiu")
        with open(f, "r", encoding="utf-8", errors="replace") as fh:
            for line in fh:
                if not line.strip():
                    continue
                try:
                    ev = json.loads(line)
                except ValueError:
                    if line.endswith("\n"):
                        raise  # linha completa ilegível -> RECUSA
                    partial += 1  # cauda sem quebra que não parseia: escrita em curso
                    continue
                ts = (ev.get("ts") or ev.get("timestamp")) if isinstance(ev, dict) else None
                if isinstance(ts, str) and ts[:4].isdigit():
                    t = (parse_ts(ts), ts)
                    first = t if first is None or t[0] < first[0] else first
                    last = t if last is None or t[0] > last[0] else last
    days = (last[0] - first[0]).total_seconds() / 86400.0 if first and last else 0.0
    return {"since": "all", "first_ts": first and first[1], "last_ts": last and last[1],
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
    try:  # o leitor rodou com cwd=repo: caminho relativo dele é relativo ao repo
        t["window"] = coverage([x if x.is_absolute() else repo / x
                                for x in map(Path, d.get("log_paths") or [])])
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
    win = dict(t.get("window") or {}, min_window_coverage_days=a.min_window_coverage_days,
               denominator_leg="neutralizada (--coverage-observed)" if a.coverage_observed else "ativa")
    spawns = int((t.get("events") or {}).get("agent_spawn") or 0)
    cov = float(win.get("coverage_days") or 0.0)
    why: List[List[str]] = []
    if t["status"] == "unavailable":
        why.append(["telemetry_unavailable", t["reason"]])
    if t["status"] == "read" and not t["chain_status"].startswith("intact"):
        why.append(["chain_not_intact", t["chain_status"]])
    if t["status"] != "unavailable" and not a.coverage_observed:  # perna 1 inteira
        if spawns < MIN_OBSERVED_SPAWNS:
            why.append(["insufficient_sample", "%d agent_spawn < %d" % (spawns, MIN_OBSERVED_SPAWNS)])
        if cov < a.min_window_coverage_days:
            why.append(["insufficient_sample", "cobertura %.2f d < %d d" % (cov, a.min_window_coverage_days)])
    inv = t.get("invocations")
    prot = protected(c)
    skills = []
    for s in c["core"]["names"]:
        cited = sorted(c["skills"][s]["cited_by"])
        cand = not set(cited) & set(excluded)
        n = None if inv is None else int(inv.get(s, 0))
        verdict = "RECUSA" if why else ("MANTER" if not cand or n else "ARQUIVAR")
        skills.append({"skill": s, "verdict": verdict, "candidate": cand, "cited_by": cited,
                       "invocations": n, "protected": s in prot})
    offenders = [x["skill"] for x in skills if x["protected"] and x["verdict"] == "ARQUIVAR"]
    if why:
        reason, rc = why[0][0], 4
    elif offenders:
        reason, rc = "would_archive", 3  # §5: com ou sem --assert-keep-veto-floor
    else:
        reason, rc = "ok", 0
    arch = {"id": "nenhuma (--disable-eligibility)" if a.disable_eligibility else "D",
            "source": "OQ-1 do Owner, 2026-09-07: «D — não mensurável hoje»",
            "emitting_channels": list(EMITTING_CHANNELS), "excluded_channels": excluded}
    inputs = {
        "window": win, "events": dict(t.get("events") or {}, min_observed_spawns=MIN_OBSERVED_SPAWNS),
        "reader": t["reader"], "chain_status": t.get("chain_status"),
        "chain_scope": {"verified": "só o log primário (chain_status do leitor)",
                        "files_read": win.get("files"), "rotated_attested": False,
                        "note": "atestar os rotacionados antes de ARQUIVAR: W2 (AC-2.0), OQ-3 do Owner"},
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
    ap = Parser(description=(__doc__ or "").split("\n")[0], allow_abbrev=False)
    ap.add_argument("--repo", default=".", help="raiz do repositório (padrão: .)")
    ap.add_argument("--json", action="store_true", help="saída JSON")
    ap.add_argument("--coverage-observed", action="store_true",
                    help="neutraliza a perna 1 inteira (controle)")
    ap.add_argument("--min-window-coverage-days", type=int, default=DEFAULT_MIN_COVERAGE_DAYS)
    ap.add_argument("--assert-keep-veto-floor", action="store_true",
                    help="exige piso de VETO e Gate 2 derivados não vazios")
    ap.add_argument("--disable-eligibility", action="store_true", help="desliga a perna 0 (controle)")
    ap.add_argument("--force-empty-telemetry", action="store_true", help="log vazio simulado")
    ap.add_argument("--ac-matrix", action="store_true", help="gera a evidência datada da W0a")
    return ap


def matrix(cm: Any, c: Dict[str, Any], a: argparse.Namespace, now: str) -> Tuple[int, Dict[str, Any]]:
    real = read_telemetry(cm, Path(a.repo).resolve())
    runs: Dict[str, Any] = {}
    out: Dict[str, Any] = {}
    for name, flags, check in MATRIX:
        ra = build_parser().parse_args(flags + ["--min-window-coverage-days",
                                                str(a.min_window_coverage_days)])
        r = evaluate(cm, c, empty_telemetry(cm) if ra.force_empty_telemetry else real, ra)
        runs[name] = {"flags": flags, "rc": r["rc"], "exit_reason": r["exit_reason"],
                      "offenders": r["offenders"], "refusal_reasons": r["inputs"]["refusal_reasons"],
                      "verdicts": count(r),
                      "would_archive": [s["skill"] for s in r["skills"] if s["verdict"] == "ARQUIVAR"],
                      "check": "pass" if check(r, c) else "FAIL"}
        if name == "AC-0.1":
            out = {k: r[k] for k in ("exit_reason", "offenders", "skills")}
            out["inputs"] = dict(r["inputs"], generated_at=now)
    failed = [n for n, r in runs.items() if r["check"] != "pass"]
    return (1 if failed else 0), dict(out, schema="plan175-prune-rule-matrix/2", runs=runs,
                                      failed_checks=failed)


def main(argv: Optional[List[str]] = None) -> int:
    raw = list(sys.argv[1:] if argv is None else argv)
    as_json = bool({"--json", "--ac-matrix"} & set(raw))  # só até o parse; depois vale o namespace
    try:
        a = build_parser().parse_args(raw)
        as_json = a.json or a.ac_matrix
        if a.min_window_coverage_days < 0:
            raise UsageError("--min-window-coverage-days não pode ser negativo")
        if a.ac_matrix and (a.coverage_observed or a.assert_keep_veto_floor
                            or a.disable_eligibility or a.force_empty_telemetry):
            raise UsageError("--ac-matrix só aceita --repo, --json e --min-window-coverage-days")
        cm = load_census()
    except (UsageError, OSError) as e:
        return usage_error(str(e), as_json)
    try:
        c = cm.census(Path(a.repo).resolve())
    except (cm.InputError, OSError) as e:  # input ausente sob --repo
        return usage_error(str(e), as_json)
    if (a.assert_keep_veto_floor or a.ac_matrix) and not (c["veto_floor"]["skills"] and c["gate2"]["skills"]):
        return usage_error("input ausente: piso de VETO ou Gate 2 derivado sem skill core "
                           "(a asserção seria vácua)", as_json)
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
        print("exit_reason = %s; offenders = %s; vereditos = %s; perna 1 %s; cadeia %s" % (
            r["exit_reason"], r["offenders"], count(r), r["inputs"]["window"]["denominator_leg"],
            r["inputs"]["chain_status"]))
    return r["rc"]


def usage_error(msg: str, as_json: bool) -> int:
    if as_json:
        print(json.dumps({"exit_reason": "usage_error", "error": msg, "inputs": {}, "skills": [],
                          "offenders": []}, ensure_ascii=False))
    print("prune-rule: ERRO: %s" % msg, file=sys.stderr)
    return 2


if __name__ == "__main__":
    sys.exit(main())
