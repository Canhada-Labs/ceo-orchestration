#!/usr/bin/env python3
"""check-ceremony-script.py — lint de scripts de cerimônia (PLAN-174 W2).

Descoberta por PROPRIEDADE DE CONTEÚDO, nunca por glob de nome (debate
r1 F4: a classe `grep|tail` tinha ZERO ocorrências dentro do glob
`OWNER-*.sh` e 4 fora dele). Um candidato é todo `*.sh` sob as raízes
com shebang bash E pelo menos uma operação de cerimônia no corpo
(gpg / git tag / gh release / npm publish / sentinel / approved.md /
VERDICT).

Regras (catálogo W1, seção A — `.claude/plans/PLAN-174/catalog.md`):
  R1  BLOCKING  proveniência: sem marca AUTO-GENERATED e sem exceção
                explícita (`CEREMONY-LINT: handwritten-exception:`)
  R2  BLOCKING  `|| true` na MESMA linha de operação remota
                irreversível (gpg/git tag/git push/gh release/npm
                publish) — a forma semântica do P1 OWNER-GA-CUT.sh:721
  R2a ADVISORY  `|| true` cru (taxa publicada, nunca bloqueia)
  R3  BLOCKING  `grep … | tail` em parsing de VERDICT
  R4  BLOCKING  `git add` de diretório (`-A`/`--all`/`.`/`dir/`)
  R5  ADVISORY  cp/mv para destino em variável sem teste `-L` nas 5
                linhas anteriores (escrita através de symlink no
                DESTINO — round 25)
  R6  ADVISORY  `shasum/sha256sum -c` sem asserção de conjunto próxima
                (set-equality — classe S272)
  R8  BLOCKING  exec-bit no índice git (modo 100755) — classe
                reincidente (rounds 8/9/12 + fix-forwards S314)

FP (AC reescrito pelo debate): zero-FP exigido SÓ das BLOCKING; resíduo
histórico = waiver pinado por sha256 do CONTEÚDO em
`ceremony-lint-waivers.json` (re-arma quando o arquivo muda), datado,
com motivo; waiver por caminho NÃO existe. Baseline só encolhe.

Escape hatch (padrão ADR-186, forma fixada pelo consenso):
`CEO_CEREMONY_LINT_UNLOCK=<sha256 do arquivo>` +
`CEO_CEREMONY_LINT_UNLOCK_REASON` OBRIGATÓRIO — sem motivo, o bloqueio
é MANTIDO. O unlock é gravado no audit trail (fail-open) e vale só para
o run corrente.

AUTOLIMITAÇÃO (obrigatória — debate r1 F6): a saída SEMPRE carrega a
linha declarando o que este lint NÃO cobre. Verde aqui nunca encurta a
pauta do rail sobre a seção B do catálogo.

Exit: 0 = sem blocking não-waivado e piso de descoberta satisfeito;
1 = blocking OU piso violado (fail-closed em INPUT); 3 = erro de
infraestrutura do próprio lint (CI trata como vermelho).

Stdlib-only, Python >= 3.9.
"""
from __future__ import annotations

import argparse
import hashlib
import json
import os
import re
import subprocess
import sys
from typing import Dict, List, Optional

REPO_ROOT = os.path.abspath(os.path.join(os.path.dirname(__file__), "..", ".."))

DISCOVERY_ROOTS = [
    ".claude/plans",
    ".claude/scripts/local/historical",
]
EXPLICIT_FILES = [
    ".claude/scripts/local/generate-ceremony.sh",
]

SHEBANG_RE = re.compile(r"\A#!\s*(?:/bin/|/usr/bin/env\s+)(?:ba)?sh")
CEREMONY_OPS_RE = re.compile(
    r"\bgpg\b|git tag|gh release|npm publish|sentinel|approved\.md|VERDICT"
)
IRREVERSIBLE_RE = re.compile(
    r"\bgpg\b|git tag|git push|gh release|npm publish|gh api"
)
OR_TRUE_RE = re.compile(r"\|\|\s*true\b")
GREP_TAIL_RE = re.compile(r"grep[^\n|]*\|\s*tail\b")
GIT_ADD_DIR_RE = re.compile(r"git add\s+(?:-A\b|--all\b|\.(?:\s|$)|\S+/\s*$|\S+/\s)")
CP_MV_VARDEST_RE = re.compile(r"\b(?:cp|mv)\b[^\n]*\s\"?\$\{?[A-Za-z_][A-Za-z_0-9]*\}?\"?\s*$")
SYMLINK_TEST_RE = re.compile(r"\[\s+-L\b|test\s+-L\b")
SHASUM_C_RE = re.compile(r"(?:shasum|sha256sum)\b[^\n]*\s-c\b")
SET_EQ_NEAR_RE = re.compile(r"wc -l|comm\b|sort\b.*diff|diff\b.*sort")
PROVENANCE_MARK = "AUTO-GENERATED"
EXCEPTION_MARK = "CEREMONY-LINT: handwritten-exception:"

SELF_LIMITATION = (
    "ceremony-lint cobre as classes sintáticas da seção A do catálogo; "
    "NÃO cobre retomada, idempotência, fronteira irreversível remota nem "
    "binding de evidência por conteúdo (seção B) — pauta permanente do rail."
)

DEFAULT_WAIVERS = os.path.join(
    REPO_ROOT, ".claude", "scripts", "ceremony-lint-waivers.json"
)
# Piso de descoberta (arquivos RASTREADOS): pinado no primeiro censo
# S316 (41 rastreados de 54 descobertos). Falha quando o conjunto
# ENCOLHE — a pergunta "o guard vê o meu alvo?" respondida em toda
# execução.
DEFAULT_FLOOR = 41


def _sha256(path: str) -> str:
    h = hashlib.sha256()
    with open(path, "rb") as fh:
        for chunk in iter(lambda: fh.read(65536), b""):
            h.update(chunk)
    return h.hexdigest()


def _git_tracked_modes(root: str) -> Dict[str, str]:
    try:
        out = subprocess.run(
            ["git", "-C", root, "ls-files", "--stage"],
            capture_output=True, text=True, timeout=30, check=False,
        ).stdout
    except Exception:
        return {}
    modes: Dict[str, str] = {}
    for line in out.splitlines():
        parts = line.split(None, 3)
        if len(parts) == 4:
            modes[parts[3]] = parts[0]
    return modes


def discover(root: str) -> List[str]:
    """Candidatos por propriedade de conteúdo (os.walk — vê dirs ocultos,
    ao contrário de glob.glob; achado do debate r1)."""
    found: List[str] = []
    roots = [os.path.join(root, r) for r in DISCOVERY_ROOTS]
    for base in roots:
        if not os.path.isdir(base):
            continue
        for dirpath, _dirnames, filenames in os.walk(base):
            for fn in filenames:
                if not fn.endswith(".sh"):
                    continue
                p = os.path.join(dirpath, fn)
                try:
                    with open(p, errors="replace") as fh:
                        body = fh.read()
                except OSError:
                    found.append(p)  # ilegível = candidato (fail-closed)
                    continue
                if SHEBANG_RE.match(body) and CEREMONY_OPS_RE.search(body):
                    found.append(p)
    for rel in EXPLICIT_FILES:
        p = os.path.join(root, rel)
        if os.path.isfile(p):
            found.append(p)
    return sorted(set(found))


def lint_file(path: str, rel: str, git_mode: Optional[str]) -> List[dict]:
    findings: List[dict] = []
    try:
        with open(path, errors="replace") as fh:
            body = fh.read()
    except OSError as exc:
        return [{"rule": "R0", "sev": "BLOCKING", "line": 0,
                 "msg": f"ilegível ({exc}) — input fail-closed"}]
    lines = body.splitlines()

    if PROVENANCE_MARK not in body and EXCEPTION_MARK not in body:
        findings.append({"rule": "R1", "sev": "BLOCKING", "line": 1,
                         "msg": "sem marca AUTO-GENERATED e sem exceção explícita"})
    for i, ln in enumerate(lines, 1):
        if OR_TRUE_RE.search(ln):
            if IRREVERSIBLE_RE.search(ln):
                findings.append({"rule": "R2", "sev": "BLOCKING", "line": i,
                                 "msg": "`|| true` sobre operação remota irreversível"})
            else:
                findings.append({"rule": "R2a", "sev": "ADVISORY", "line": i,
                                 "msg": "`|| true` cru"})
        if GREP_TAIL_RE.search(ln):
            findings.append({"rule": "R3", "sev": "BLOCKING", "line": i,
                             "msg": "grep|tail em parsing de VERDICT"})
        if GIT_ADD_DIR_RE.search(ln):
            findings.append({"rule": "R4", "sev": "BLOCKING", "line": i,
                             "msg": "git add de diretório"})
        if CP_MV_VARDEST_RE.search(ln):
            ctx = "\n".join(lines[max(0, i - 6):i - 1])
            if not SYMLINK_TEST_RE.search(ctx):
                findings.append({"rule": "R5", "sev": "ADVISORY", "line": i,
                                 "msg": "cp/mv p/ destino em variável sem teste -L próximo"})
        if SHASUM_C_RE.search(ln):
            ctx = "\n".join(lines[max(0, i - 4):min(len(lines), i + 3)])
            if not SET_EQ_NEAR_RE.search(ctx):
                findings.append({"rule": "R6", "sev": "ADVISORY", "line": i,
                                 "msg": "shasum -c sem asserção de conjunto (set-equality)"})
    # R8 só na superfície de binding assinado (.claude/plans/): exec-bit
    # em ferramenta de scripts/local/ é legítimo (invocada diretamente).
    if git_mode == "100755" and rel.startswith(".claude/plans/"):
        findings.append({"rule": "R8", "sev": "BLOCKING", "line": 0,
                         "msg": "exec-bit no índice git (modo 100755)"})
    return findings


def _emit_unlock_audit(sha: str, reason: str) -> None:
    """Advisory, fail-open: emissor canônico; senão, breadcrumb durável.

    RESTAURADO (S318, pack SENT-S318 — o mesmo pack que registrou a ação
    ``ceremony_lint_unlock_used`` nas DUAS fontes canônicas que o gate
    ``check-audit-registry-coverage.py`` exige: ``_KNOWN_ACTIONS`` em
    ``.claude/hooks/_lib/audit_emit.py`` e a tabela por-ação de
    ``SPEC/v1/audit-log.schema.md``). Histórico: o PLAN-174 W1 (7d467a8)
    embarcou este emissor SEM a metade canônica do registro, o gate pegou o
    órfão (6 jobs vermelhos), e a S317 (908707e) parcou o emit fixando a
    regra "um emissor não embarca antes do registro dele" — precedente
    v2.51 / SENT-GK-F.

    Wire metadata-only (LLM06): ``file_sha256`` = prefixo 16-hex do sha256
    do script destravado; ``reason_len`` = comprimento do
    ``CEO_CEREMONY_LINT_UNLOCK_REASON``. O TEXTO do motivo nunca vai ao
    log — fica só no stderr do operador (abaixo).

    Fail-open em TODA rota (um unlock advisory nunca pode quebrar o lint):
    emissor indisponível ⇒ breadcrumb durável em ``audit-log.errors`` — o
    mesmo destino que a versão parcada usava — e o stderr sempre imprime.
    """
    line = (f"ceremony-lint UNLOCK usado sha={sha[:16]} "
            f"reason_len={len(reason)}")
    try:
        sys.path.insert(0, os.path.join(REPO_ROOT, ".claude", "hooks"))
        from _lib import audit_emit  # type: ignore
        fn = getattr(audit_emit, "emit_generic", None)
        if callable(fn):
            # emit_generic takes **kwargs as TOP-LEVEL event fields — the
            # 7d467a8 shape (`fields={...}`) nested the payload under a
            # single "fields" key the scrub correctly drops (caught by the
            # S318 clone-sim; the parked emitter had never run live).
            fn(action="ceremony_lint_unlock_used",
               file_sha256=sha[:16], reason_len=len(reason))
        else:
            crumb = getattr(audit_emit, "_breadcrumb", None)
            if callable(crumb):
                crumb(line)
    except Exception:
        try:
            from _lib import audit_emit as _ae  # type: ignore
            crumb = getattr(_ae, "_breadcrumb", None)
            if callable(crumb):
                crumb(line)
        except Exception:
            pass
    print(f"ceremony-lint: UNLOCK usado sha={sha[:16]} motivo={reason!r}",
          file=sys.stderr)


def main(argv: Optional[List[str]] = None) -> int:
    ap = argparse.ArgumentParser(prog="check-ceremony-script")
    ap.add_argument("--root", default=REPO_ROOT,
                    help="raiz do repo (testes usam tmp dir)")
    ap.add_argument("--waivers", default=None,
                    help="path do JSON de waivers (default: ao lado do lint)")
    ap.add_argument("--floor", type=int, default=None,
                    help=f"piso do conjunto RASTREADO descoberto (default {DEFAULT_FLOOR})")
    ap.add_argument("--json", action="store_true")
    ap.add_argument("--list", action="store_true",
                    help="só imprime os arquivos descobertos (um por linha)")
    ap.add_argument("--print-waiver-template", action="store_true",
                    help="emite entradas de waiver p/ os arquivos hoje em BLOCKING")
    args = ap.parse_args(argv)

    root = os.path.abspath(args.root)
    try:
        files = discover(root)
    except Exception as exc:  # infra do próprio lint
        print(f"ceremony-lint: INFRA error na descoberta: {exc}", file=sys.stderr)
        return 3

    modes = _git_tracked_modes(root)
    rels = {f: os.path.relpath(f, root) for f in files}
    tracked = [f for f in files if rels[f] in modes]

    if args.list:
        for f in files:
            print(rels[f])
        return 0

    waivers_path = args.waivers or (
        DEFAULT_WAIVERS if root == REPO_ROOT
        else os.path.join(root, ".claude", "scripts", "ceremony-lint-waivers.json")
    )
    waived_shas = set()
    waiver_entries: List[dict] = []
    if os.path.isfile(waivers_path):
        try:
            waiver_entries = json.load(open(waivers_path))
            waived_shas = {w["sha256"] for w in waiver_entries
                           if w.get("sha256") and w.get("reason") and w.get("date")}
        except Exception as exc:
            print(f"ceremony-lint: waivers ilegíveis ({exc}) — input fail-closed, "
                  "nenhum waiver aplicado", file=sys.stderr)

    unlock_sha = (os.environ.get("CEO_CEREMONY_LINT_UNLOCK") or "").strip().lower()
    unlock_reason = (os.environ.get("CEO_CEREMONY_LINT_UNLOCK_REASON") or "").strip()

    report: List[dict] = []
    blocking_live = 0
    advisory_counts: Dict[str, int] = {}
    for f in files:
        sha = _sha256(f)
        findings = lint_file(f, rels[f], modes.get(rels[f]))
        waived = sha in waived_shas
        if not waived and unlock_sha and sha == unlock_sha:
            if unlock_reason:
                waived = True
                _emit_unlock_audit(sha, unlock_reason)
            else:
                print("ceremony-lint: CEO_CEREMONY_LINT_UNLOCK sem "
                      "CEO_CEREMONY_LINT_UNLOCK_REASON — bloqueio MANTIDO",
                      file=sys.stderr)
        is_tracked = rels[f] in modes
        n_block = sum(1 for x in findings if x["sev"] == "BLOCKING")
        for x in findings:
            if x["sev"] == "ADVISORY":
                advisory_counts[x["rule"]] = advisory_counts.get(x["rule"], 0) + 1
        # O gate conta SÓ arquivos rastreados: o CI clona o repo e nunca
        # vê untracked/gitignored (ponto cego DECLARADO no catálogo —
        # reportado no relatório, nunca fingido como coberto).
        if n_block and not waived and is_tracked:
            blocking_live += n_block
        report.append({"file": rels[f], "sha256": sha, "tracked": rels[f] in modes,
                       "waived": waived, "findings": findings})

    floor = args.floor if args.floor is not None else DEFAULT_FLOOR
    floor_ok = len(tracked) >= floor

    if args.print_waiver_template:
        tmpl = [{"sha256": r["sha256"], "path_hint": r["file"],
                 "reason": "PREENCHER", "date": "PREENCHER"}
                for r in report
                if any(x["sev"] == "BLOCKING" for x in r["findings"])
                and not r["waived"]]
        print(json.dumps(tmpl, indent=1, ensure_ascii=False))
        return 0

    result = {
        "discovered_total": len(files),
        "discovered_tracked": len(tracked),
        "floor": floor,
        "floor_ok": floor_ok,
        "blocking_unwaived": blocking_live,
        "advisory_rates": advisory_counts,
        "waivers_active": len(waived_shas),
        "self_limitation": SELF_LIMITATION,
        "files": report,
    }
    if args.json:
        print(json.dumps(result, indent=1, ensure_ascii=False))
    else:
        print(f"ceremony-lint: {len(files)} descobertos "
              f"({len(tracked)} rastreados; piso {floor} "
              f"{'OK' if floor_ok else 'VIOLADO'})")
        for r in report:
            for x in r["findings"]:
                tag = "waived" if r["waived"] and x["sev"] == "BLOCKING" else x["sev"]
                print(f"  [{x['rule']}/{tag}] {r['file']}:{x['line']} — {x['msg']}")
        print(f"blocking não-waivado: {blocking_live} | advisory: {advisory_counts} "
              f"| waivers ativos: {len(waived_shas)}")
        print(SELF_LIMITATION)
    return 0 if (blocking_live == 0 and floor_ok) else 1


if __name__ == "__main__":
    sys.exit(main())
