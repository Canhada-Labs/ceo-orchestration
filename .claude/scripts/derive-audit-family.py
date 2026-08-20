#!/usr/bin/env python3
"""derive-audit-family.py — censo COMPORTAMENTAL da família de runtime
state (PLAN-182 W0-US1/US2; ADR-001).

Por que não grep: SPEC, docs e testes mantêm o literal legitimamente
(lição [[feedback-grep-counts-are-wrong-derive-behaviorally]] + AC-1 do
plano: "grep pelo literal NÃO é oráculo"). Este censo deriva a família
por MARCADORES DE COMPORTAMENTO e aplica uma regra de allowlist
EXPLÍCITA por papel de artefato:

Marcadores (qualquer um coloca o arquivo na família):
  M1 constrói caminho de runtime state (o literal `ceo-orchestration`
     sob `~/.claude/projects`, em .py/.sh executável);
  M2 importa um módulo resolvedor/consumidor da família
     (audit_emit, state_store, spool_writer, scratchpad_lib,
     injection_salt, memory_shared, audit_hmac, filelock);
  M3 consome env da família (CEO_AUDIT_LOG_DIR, CEO_STATE_ROOT,
     CEO_PROJECT_NAME, CLAUDE_PROJECT_DIR, CLAUDE_PROJECT_DIR_NATIVE,
     CEO_SESSION_ANCHOR_SHA de state).

Regra de allowlist (explícita — AC-1): artefatos com papel
`spec`/`doc`/`plan` ficam FORA do conjunto de cura da W1 mesmo contendo
o literal (mantê-lo ali é legítimo); `test` entra como família mas em
classe própria (curado JUNTO, nunca esquecido); `template`/`installer`/
`ci` entram como superfícies de entrega (US4).

Modos:
  --json               censo completo (modulo/artefato/papel/marcadores)
  --matrix             US2: matriz artefato × env — roda os resolvedores
                       REAIS em subprocess com HOME isolado e imprime o
                       caminho resolvido por célula
  --assert-migrated    gate FUTURO da W1 (sai 1 enquanto qualquer módulo
                       runtime construir o literal sem delegar ao
                       resolvedor único) — HOJE falha por design
  --surfaces           US4: superfícies de entrega (templates, installer,
                       CI, dist)

Stdlib-only, Python >= 3.9. Read-only (nunca escreve).
"""
from __future__ import annotations

import argparse
import json
import os
import re
import subprocess
import sys
import tempfile
from typing import Dict, List, Optional

REPO_ROOT = os.path.abspath(os.path.join(os.path.dirname(__file__), "..", ".."))

SCAN_ROOTS = [".claude/hooks", ".claude/scripts", "scripts", "templates",
              ".github/workflows", "SPEC", "docs", "dist"]
SCAN_TOP_FILES = ["install.sh", "upgrade.sh"]

M1_RE = re.compile(r"\.claude(?:['\"]?\s*[,/+]\s*['\"]?|/)projects[^\n]{0,80}ceo-orchestration"
                   r"|projects/ceo-orchestration"
                   r"|['\"]ceo-orchestration['\"]")
M2_MODULES = ("audit_emit", "state_store", "spool_writer", "scratchpad_lib",
              "injection_salt", "memory_shared", "audit_hmac", "filelock")
_M2_ALT = "|".join(M2_MODULES)
M2_RE = re.compile(
    r"(?:from\s+_lib(?:\.\w+)*\s+import\s+[\w, ]*(?:{alt})"
    r"|from\s+_lib\.(?:{alt})\s+import"
    r"|import\s+(?:{alt})\b)".format(alt=_M2_ALT))
M3_ENVS = ("CEO_AUDIT_LOG_DIR", "CEO_STATE_ROOT", "CEO_PROJECT_NAME",
           "CLAUDE_PROJECT_DIR_NATIVE", "CLAUDE_PROJECT_DIR")
WRITER_RE = re.compile(r"emit_|open\([^)]*['\"][aw]b?['\"]|\.write\(|\.append\(|write_text\(|json\.dump\(")
LOCK_RE = re.compile(r"filelock|\.lock\b|flock")
SALT_RE = re.compile(r"injection_salt|\.salt\b|get_instance_salt")
KEY_RE = re.compile(r"audit-key|audit_hmac|hmac")


def _artefato(rel: str) -> str:
    if "/tests/" in rel or rel.startswith("tests/") or "/test_" in rel:
        return "test"
    if rel.startswith("templates/"):
        return "template"
    if rel in ("install.sh", "upgrade.sh") or "/install" in rel or "/upgrade" in rel:
        return "installer"
    if rel.startswith(".github/"):
        return "ci"
    if rel.startswith("SPEC/"):
        return "spec"
    if rel.startswith("docs/") or rel.endswith(".md"):
        return "doc"
    if rel.startswith("dist/"):
        return "dist"
    if rel.startswith(".claude/hooks/"):
        return "hook"
    if rel.startswith((".claude/scripts/", "scripts/")):
        return "script"
    return "outro"


def scan() -> List[dict]:
    fam: List[dict] = []
    cands: List[str] = []
    for root in SCAN_ROOTS:
        base = os.path.join(REPO_ROOT, root)
        if not os.path.isdir(base):
            continue
        for dirpath, dirnames, filenames in os.walk(base):
            dirnames[:] = [d for d in dirnames if d not in ("__pycache__", ".git", "node_modules")]
            for fn in filenames:
                if fn.endswith((".py", ".sh", ".yml", ".yaml", ".md", ".json", ".template")):
                    cands.append(os.path.join(dirpath, fn))
    for t in SCAN_TOP_FILES:
        p = os.path.join(REPO_ROOT, t)
        if os.path.isfile(p):
            cands.append(p)
    for p in sorted(set(cands)):
        rel = os.path.relpath(p, REPO_ROOT)
        try:
            body = open(p, errors="replace").read()
        except OSError:
            continue
        markers: List[str] = []
        if M1_RE.search(body):
            markers.append("M1-constroi-caminho")
        if p.endswith(".py") and M2_RE.search(body):
            markers.append("M2-importa-resolvedor")
        if any(e in body for e in M3_ENVS):
            markers.append("M3-consome-env")
        if not markers:
            continue
        art = _artefato(rel)
        papel: List[str] = []
        if art in ("hook", "script", "installer", "dist"):
            if WRITER_RE.search(body):
                papel.append("writer")
            else:
                papel.append("reader")
            if LOCK_RE.search(body):
                papel.append("lock")
            if SALT_RE.search(body):
                papel.append("salt")
            if KEY_RE.search(body):
                papel.append("hmac-key")
        elif art == "test":
            papel.append("test-da-familia")
        else:
            papel.append("referencia-legitima")
        fam.append({"modulo": rel, "artefato": art, "papel": papel,
                    "marcadores": markers,
                    "na_cura_w1": art in ("hook", "script", "installer",
                                          "dist", "ci", "template", "test")})
    return fam


# US2 — matriz artefato × env. Cada célula roda o resolvedor REAL em
# subprocess com HOME isolado (nunca toca o estado do operador).
RESOLVERS = {
    "audit_emit._audit_dir": (
        "import sys; sys.path.insert(0, {hooks!r}); "
        "from _lib import audit_emit; print(audit_emit._audit_dir())"),
    "state_store._state_root": (
        "import sys; sys.path.insert(0, {hooks!r}); "
        "from _lib import state_store; print(state_store._state_root())"),
    "injection_salt(dir do salt)": (
        "import sys; sys.path.insert(0, {hooks!r}); "
        "from _lib import injection_salt as s; "
        "print(getattr(s, '_salt_path', getattr(s, 'SALT_PATH', lambda: 'API-DRIFT'))() "
        "if callable(getattr(s, '_salt_path', None)) else 'API-DRIFT')"),
}
ENV_COMBOS = {
    "sem-env": {},
    "CLAUDE_PROJECT_DIR": {"CLAUDE_PROJECT_DIR": "/tmp/fake-proj"},
    "CEO_STATE_ROOT": {"CEO_STATE_ROOT": "/tmp/fake-state-root"},
    "CEO_PROJECT_NAME": {"CEO_PROJECT_NAME": "outro-projeto"},
    "CEO_AUDIT_LOG_DIR": {"CEO_AUDIT_LOG_DIR": "/tmp/fake-audit"},
}


def matrix() -> Dict[str, Dict[str, str]]:
    hooks = os.path.join(REPO_ROOT, ".claude", "hooks")
    out: Dict[str, Dict[str, str]] = {}
    with tempfile.TemporaryDirectory() as fake_home:
        for rname, code in RESOLVERS.items():
            row: Dict[str, str] = {}
            for cname, extra in ENV_COMBOS.items():
                env = {"HOME": fake_home, "PATH": os.environ.get("PATH", ""),
                       "PYTHONDONTWRITEBYTECODE": "1"}
                env.update(extra)
                try:
                    r = subprocess.run(
                        [sys.executable, "-c", code.format(hooks=hooks)],
                        capture_output=True, text=True, timeout=20, env=env)
                    val = (r.stdout.strip() or r.stderr.strip().splitlines()[-1:] or ["(vazio)"])
                    row[cname] = val if isinstance(val, str) else val[0]
                except Exception as exc:
                    row[cname] = f"ERRO: {exc}"
            out[rname] = row
    return out


def surfaces() -> List[str]:
    out = []
    for rel in ("templates", "install.sh", "upgrade.sh",
                "templates/settings/settings.base.json", "dist/ceo-plugin/hooks"):
        p = os.path.join(REPO_ROOT, rel)
        if os.path.exists(p):
            n = sum(len(fs) for _, _, fs in os.walk(p)) if os.path.isdir(p) else 1
            out.append(f"{rel} ({n} arquivo(s))")
    return out


def main(argv: Optional[List[str]] = None) -> int:
    ap = argparse.ArgumentParser(prog="derive-audit-family")
    ap.add_argument("--json", action="store_true")
    ap.add_argument("--matrix", action="store_true")
    ap.add_argument("--surfaces", action="store_true")
    ap.add_argument("--assert-migrated", action="store_true")
    args = ap.parse_args(argv)

    if args.matrix:
        m = matrix()
        print(json.dumps(m, indent=1, ensure_ascii=False))
        return 0
    if args.surfaces:
        for s in surfaces():
            print(s)
        return 0

    fam = scan()
    if args.assert_migrated:
        # Gate FUTURO da W1: nenhum módulo runtime constrói o literal.
        offenders = [f for f in fam
                     if f["artefato"] in ("hook", "script", "installer", "dist")
                     and "M1-constroi-caminho" in f["marcadores"]]
        print(f"assert-migrated: {len(offenders)} módulo(s) runtime ainda "
              "constroem o caminho literal")
        return 1 if offenders else 0

    if args.json:
        print(json.dumps({"total_familia": len(fam),
                          "por_artefato": _tally(fam, "artefato"),
                          "na_cura_w1": sum(1 for f in fam if f["na_cura_w1"]),
                          "familia": fam}, indent=1, ensure_ascii=False))
    else:
        t = _tally(fam, "artefato")
        print(f"família derivada: {len(fam)} arquivos — {t}")
        print(f"no conjunto de cura da W1: {sum(1 for f in fam if f['na_cura_w1'])}")
        print("(allowlist explícita: spec/doc/plan mantêm o literal "
              "legitimamente e ficam fora da cura)")
    return 0


def _tally(fam: List[dict], key: str) -> Dict[str, int]:
    t: Dict[str, int] = {}
    for f in fam:
        t[f[key]] = t.get(f[key], 0) + 1
    return dict(sorted(t.items(), key=lambda kv: -kv[1]))


if __name__ == "__main__":
    sys.exit(main())
