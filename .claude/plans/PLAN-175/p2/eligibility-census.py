"""PLAN-175 W0a (AC-0.7): censo de elegibilidade das skills core, GERADO.

Transforma em programa o heredoc do §2.1 do plano. Para cada skill core
(``.claude/skills/core/*/SKILL.md``) lista os canais que a citam por limite
de palavra -- ``CLAUDE.md``, ``.claude/commands/*.md``, ``.claude/agents/*.md``
e o SKILL MAP (``.claude/team.md`` + ``.claude/frontend-team.md``) -- e conta
as candidatas de cada arquitetura da perna 0: A (exclui a união dos quatro
canais), B (sai ``.claude/commands/``), C (override = Gate 2 do ``CLAUDE.md``
mais o piso de VETO); D não é mensurável hoje e sai com o motivo.

Nenhum nome de skill ou de arquétipo é digitado aqui: o piso de VETO vem do
frontmatter ``veto_floor: true`` de ``.claude/agents/*.md`` e o override de
C vem da seção «Gate 2» do ``CLAUDE.md``.

Uso: python3 .claude/plans/PLAN-175/p2/eligibility-census.py [--repo PATH]
         [--json] [--with-telemetry] [--no-timestamp]

``--with-telemetry`` (desligado por padrão) acrescenta o uso por skill lido
por ``skill-health.py --include-rotated --since all --json``. O leitor resolve
o diretório de estado pelo resolvedor por projeto: uma sombra vê o slug DELA
e nenhum log -- rode do checkout do projeto.

Saída: 0 censo gerado; 2 bandeira desconhecida ou entrada ausente (nenhuma
skill core, CLAUDE.md sem seção «Gate 2», nenhum agente ``veto_floor: true``);
3 ``--with-telemetry`` pedido e o uso NÃO foi medido -- sem log, leitura
incompleta (o leitor avisou linha ou arquivo ilegível) ou cadeia HMAC não
íntegra; log íntegro e vazio conta como medido, com zero (o JSON sai mesmo
assim, com o motivo). Só lê arquivos (o leitor roda com ``-B``, sem
bytecode). Biblioteca padrão, Python >= 3.9.

Saída de texto: as 8 primeiras linhas (core, os quatro canais, A, B, C) têm
o formato das linhas do heredoc do §2.1; as linhas D e telemetria são
acréscimos deste script.
"""
from __future__ import annotations

import argparse
import datetime as dt
import hashlib
import json
import os
import re
import subprocess
import sys
from pathlib import Path
from typing import Any, Dict, List, Optional

BOUNDARY = r"(?<![A-Za-z0-9_-])%s(?![A-Za-z0-9_-])"  # o mesmo do heredoc do §2.1
CORE_GLOB = ".claude/skills/core/*/SKILL.md"
CHANNELS = {  # canal -> padrões relativos ao repo, na ordem do §2.1
    "CLAUDE.md": ["CLAUDE.md"],
    "commands": [".claude/commands/*.md"],
    "agents": [".claude/agents/*.md"],
    "SKILLMAP": [".claude/team.md", ".claude/frontend-team.md"],
}
B_EXCLUDES = {"SKILLMAP", "agents", "CLAUDE.md"}  # arquitetura B: sai commands
READER = ".claude/scripts/skill-health.py --include-rotated --since all --json"
D_REASON = (
    "o canal de invocação por assento e por comando não emite evento; a "
    "perna 0 só encolhe depois que esse canal ganhar instrumento (emissão "
    "sob .claude/hooks/, caminho canônico) e de uma janela de observação "
    "posterior -- §2.1, linha D"
)
GATE2_HEAD = re.compile(r"^#{1,6}\s+Gate 2\b")
ANY_HEAD = re.compile(r"^(#{1,6})\s")
FENCE = re.compile(r"^\s{0,3}(```|~~~)")
READER_WARN = re.compile(r"^\[skill-health\] (?:WARN|ERROR):")  # linha/arquivo ilegível
FM_KEY = re.compile(r"^([A-Za-z_][A-Za-z0-9_\-]*)\s*:\s*(.*)$")  # = _lib/frontmatter
TRUTHY = ("true", "yes", "1")  # = test_veto_floor_bijection._is_truthy


class InputError(Exception):
    pass


def frontmatter(text: str) -> Dict[str, str]:
    lines = text.splitlines()
    if not lines or lines[0] != "---":
        return {}
    meta: Dict[str, str] = {}
    for raw in lines[1:]:
        if raw == "---":
            return meta
        s = raw.strip()
        m = FM_KEY.match(s) if s and not s.startswith("#") else None
        if m:
            v = m.group(2).strip()
            if len(v) >= 2 and v[0] == v[-1] and v[0] in "\"'":
                v = v[1:-1]
            meta[m.group(1)] = v
    return {}  # sem delimitador de fechamento: não é frontmatter


def gate2_text(claude_md: str) -> str:
    """Do título «Gate 2» até o próximo título de nível igual ou maior, fora de cerca de código."""
    out: List[str] = []
    level, fence = 0, ""
    for line in claude_md.splitlines():
        f = FENCE.match(line)
        if f:
            fence = "" if fence == f.group(1) else (fence or f.group(1))
        h = None if fence or f else ANY_HEAD.match(line)
        if h and level and len(h.group(1)) <= level:
            break
        if h and not level and GATE2_HEAD.match(line):
            level = len(h.group(1))
        if level:
            out.append(line)
    if not out:
        raise InputError("CLAUDE.md sem seção «Gate 2»")
    return "\n".join(out)


def head_sha(repo: Path) -> Optional[str]:
    try:
        p = subprocess.run(["git", "rev-parse", "--show-toplevel", "HEAD"], cwd=str(repo),
                           capture_output=True, text=True, timeout=30)
    except (OSError, subprocess.TimeoutExpired):
        return None
    out = p.stdout.splitlines()  # linhas, não espaços: caminho com espaço é válido
    if p.returncode != 0 or len(out) != 2 or Path(out[0]).resolve() != repo:
        return None  # fora de git, ou o repo é subdiretório de outro checkout
    return out[1] if re.fullmatch(r"[0-9a-f]{40,64}", out[1]) else None


def census(repo: Path) -> Dict[str, Any]:
    core = sorted(p.parent.name for p in repo.glob(CORE_GLOB))
    if not core:
        raise InputError("nenhuma skill core em %s sob --repo" % CORE_GLOB)
    pat = {s: re.compile(BOUNDARY % re.escape(s)) for s in core}
    texts: Dict[str, Dict[str, str]] = {}
    for ch, globs in CHANNELS.items():
        texts[ch] = {}
        for g in globs:
            for p in sorted(x for x in repo.glob(g) if x.is_file()):
                texts[ch][p.relative_to(repo).as_posix()] = p.read_text(
                    encoding="utf-8", errors="replace")
    if "CLAUDE.md" not in texts["CLAUDE.md"]:
        raise InputError("CLAUDE.md ausente sob --repo")
    cited: Dict[str, Dict[str, List[str]]] = {s: {} for s in core}
    for ch, files in texts.items():
        for rel, txt in files.items():
            for s in core:
                if pat[s].search(txt):
                    cited[s].setdefault(ch, []).append(rel)
    veto_agents = [rel for rel, txt in texts["agents"].items()
                   if frontmatter(txt).get("veto_floor", "").strip().lower() in TRUTHY]
    if not veto_agents:
        raise InputError("nenhum .claude/agents/*.md com veto_floor: true")
    veto = sorted({s for rel in veto_agents for s in core
                   if pat[s].search(texts["agents"][rel])})
    gate2 = gate2_text(texts["CLAUDE.md"]["CLAUDE.md"])
    gate2_skills = [s for s in core if pat[s].search(gate2)]
    keep = set(veto) | set(gate2_skills)
    cand = {"A": [s for s in core if not cited[s]],
            "B": [s for s in core if not set(cited[s]) & B_EXCLUDES],
            "C": [s for s in core if s not in keep]}
    digest = hashlib.sha256("\n".join(core).encode("utf-8"))
    for rel in sorted(r for files in texts.values() for r in files):
        ch = next(c for c in CHANNELS if rel in texts[c])
        digest.update(b"\0" + rel.encode("utf-8") + b"\0" + texts[ch][rel].encode("utf-8"))
    return {
        "schema": "plan175-eligibility-census/1",
        "inputs": {
            "head_sha": head_sha(repo),
            "word_boundary_regex": BOUNDARY % "<re.escape(nome)>",
            "core_glob": CORE_GLOB,
            "channel_files": {c: list(f) for c, f in texts.items()},
            "inputs_sha256": digest.hexdigest(),
            "veto_floor_rule": ".claude/agents/*.md com veto_floor: true no frontmatter",
            "c_override_rule": "seção «Gate 2» do CLAUDE.md + skills citadas pelos agentes do piso de VETO",
        },
        "core": {"count": len(core), "names": core},
        "channels": {c: {"count": sum(1 for s in core if c in cited[s]),
                         "names": [s for s in core if c in cited[s]]} for c in CHANNELS},
        "skills": {s: {"cited_by": cited[s], "candidate_in": [a for a in "ABC" if s in cand[a]],
                       "invocations": None} for s in core},
        "veto_floor": {"agents": [Path(r).stem for r in veto_agents], "skills": veto},
        "gate2": {"skills": gate2_skills},
        "candidates_by_architecture": {"A": len(cand["A"]), "B": len(cand["B"]),
                                       "C": len(cand["C"]), "D": "not-measurable"},
        "candidates": cand,
        "not_measurable": {"D": D_REASON},
        "telemetry": {"status": "off"},
    }


def telemetry(repo: Path, core: List[str]) -> Dict[str, Any]:
    base: Dict[str, Any] = {"reader": "python3 -B " + READER, "state_dir_from": next(
        (k for k in ("CLAUDE_PROJECT_DIR_NATIVE", "CLAUDE_PROJECT_DIR") if os.environ.get(k)), "cwd")}
    try:
        p = subprocess.run([sys.executable, "-B"] + READER.split(), cwd=str(repo),
                           capture_output=True, text=True, timeout=900)
        d = json.loads(p.stdout) if p.returncode == 0 else None
    except (OSError, subprocess.TimeoutExpired, ValueError) as e:
        return dict(base, status="unavailable", reason=type(e).__name__)
    if not isinstance(d, dict):
        return dict(base, status="unavailable", reason="rc=%d" % p.returncode)
    if not d.get("log_found"):
        return dict(base, status="no-log", reason="o leitor não achou log no diretório "
                    "de estado deste projeto (sombra? rode do checkout do projeto)")
    warned = sum(1 for ln in (p.stderr or "").splitlines() if READER_WARN.match(ln))
    chain = str(d.get("chain_status") or "")
    if warned or not chain.startswith("intact"):  # zero de leitura falha não é uso medido
        return dict(base, status="unavailable", chain_status=chain, reader_warnings=warned,
                    reason="leitura incompleta (%d aviso(s) de linha ou arquivo ilegível) ou "
                    "cadeia HMAC não íntegra (%s)" % (warned, chain or "ausente"))
    inv = {r.get("skill"): r.get("invocations", 0) for r in d.get("skills") or []}
    dh = d.get("discovery_health") or {}
    per = {s: int(inv.get(s) or 0) for s in core}
    return dict(base, status="measured", window=d.get("window"),
                log_files=len(d.get("log_paths") or []), chain_status=d.get("chain_status"),
                events_scanned=d.get("events_scanned"), events_in_window=d.get("events_in_window"),
                discovery_health={k: dh.get(k) for k in (
                    "total_invocations", "invoked_known_skills",
                    "unknown_invocation_count", "unknown_invocation_ratio")},
                core_invoked=sum(1 for n in per.values() if n > 0),
                core_zero_invocations=sum(1 for n in per.values() if n == 0), per_skill=per)


def render(obj: Dict[str, Any]) -> str:
    """JSON determinístico: chaves de 1.º e 2.º nível em linhas próprias, o resto em linha."""
    def one(v: Any) -> str:
        return json.dumps(v, sort_keys=True, ensure_ascii=False)
    out = ["{"]
    top = sorted(obj.items())
    for i, (k, v) in enumerate(top):
        end = "," if i < len(top) - 1 else ""
        if isinstance(v, dict) and v:
            out.append("  %s: {" % one(k))
            sub = sorted(v.items())
            out += ["    %s: %s%s" % (one(k2), one(v2), "," if j < len(sub) - 1 else "")
                    for j, (k2, v2) in enumerate(sub)]
            out.append("  }" + end)
        else:
            out.append("  %s: %s%s" % (one(k), one(v), end))
    return "\n".join(out + ["}"])


def main(argv: Optional[List[str]] = None) -> int:
    ap = argparse.ArgumentParser(description=(__doc__ or "").split("\n")[0])
    ap.add_argument("--repo", default=".", help="raiz do repositório (padrão: .)")
    ap.add_argument("--json", action="store_true", help="saída JSON")
    ap.add_argument("--with-telemetry", action="store_true", help="acrescenta o uso por skill")
    ap.add_argument("--no-timestamp", action="store_true", help="omite generated_at")
    a = ap.parse_args(argv)
    repo = Path(a.repo).resolve()
    try:
        d = census(repo)
    except InputError as e:
        print("eligibility-census: ERRO: %s" % e, file=sys.stderr)
        return 2
    if not a.no_timestamp:
        d["inputs"]["generated_at"] = dt.datetime.now(dt.timezone.utc).strftime("%Y-%m-%dT%H:%M:%SZ")
    if a.with_telemetry:
        d["telemetry"] = telemetry(repo, d["core"]["names"])
        for s, n in (d["telemetry"].pop("per_skill", None) or {}).items():
            d["skills"][s]["invocations"] = n
    if a.json:
        print(render(d))
    else:
        n = d["core"]["count"]
        print("core = %d" % n)
        for c, v in d["channels"].items():
            print("  canal %-10s nomeia %d/%d" % (c, v["count"], n))
        c = d["candidates_by_architecture"]
        print("A candidatas = %d" % c["A"])
        print("B candidatas = %d %s" % (c["B"], d["candidates"]["B"]))
        print("C override = %s -> candidatas = %d" % (sorted(set(d["veto_floor"]["skills"])
              | set(d["gate2"]["skills"])), c["C"]))
        print("D = %s (%s)" % (c["D"], d["not_measurable"]["D"]))
        print("telemetria = %s" % d["telemetry"]["status"])
    if a.with_telemetry and d["telemetry"]["status"] != "measured":
        print("eligibility-census: uso NÃO medido: %s" % d["telemetry"].get("reason"), file=sys.stderr)
        return 3
    return 0


if __name__ == "__main__":
    sys.exit(main())
