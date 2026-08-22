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
from typing import Any, Dict, List, Optional

REPO_ROOT = os.path.abspath(os.path.join(os.path.dirname(__file__), "..", ".."))

SCAN_ROOTS = [".claude/hooks", ".claude/scripts", "scripts", "templates",
              ".github/workflows", "SPEC", "docs", "dist",
              # PLAN-182 W3 (S321): `tests/` was outside the census, so the
              # root-level suite was invisible to every count this tool
              # publishes. Adding it changes the SET that is reported; it
              # does NOT change the --assert-migrated verdict, because
              # artefato == "test" stays out of that offender set.
              "tests"]
SCAN_TOP_FILES = ["install.sh", "upgrade.sh"]

M1_RE = re.compile(r"\.claude(?:['\"]?\s*[,/+]\s*['\"]?|/)projects[^\n]{0,80}ceo-orchestration"
                   r"|projects/ceo-orchestration"
                   r"|['\"]ceo-orchestration['\"]")

# PLAN-182 W1 — refinamentos do predicado M1 (a licao dos "5/5 numeros
# errados": o censo e comportamental, e o comportamento tem 3 excecoes
# LEGITIMAS que a primeira redacao contava como divida):
#   (a) linhas com o marcador explicito `rp-allow:` sao rotulos de
#       produto (service-name OTel, vendor de SBOM), nao caminhos;
#   (b) `skills/core/ceo-orchestration` e o NOME DA SKILL, nao o dir de
#       runtime state;
#   (c) DONOS SANCIONADOS do literal: runtime_paths.py (unico modulo
#       autorizado a construi-lo — legacy_state_dir p/ tooling de
#       migracao W2) e este proprio censo (o regex acima).
M1_ALLOW_MARK = "rp-allow:"
M1_SKILL_CTX = (
    "skills/core/ceo-orchestration",
    'skills" / "core" / "ceo-orchestration"',
    "skills' / 'core' / 'ceo-orchestration'",
)
M1_SANCTIONED = (
    ".claude/hooks/_lib/runtime_paths.py",
    ".claude/scripts/derive-audit-family.py",
    "dist/ceo-plugin/hooks/_lib/runtime_paths.py",
)


def _m1_hit(rel, body):
    """M1 comportamental com as 3 excecoes documentadas acima."""
    if rel in M1_SANCTIONED:
        return False
    kept = []
    for ln in body.splitlines():
        if M1_ALLOW_MARK in ln:
            continue
        if any(c in ln for c in M1_SKILL_CTX):
            continue
        # Fixture-data shape: valores de campo `project` em eventos
        # sinteticos de smoke/fixtures sao DADO, nao construcao de path.
        if '"project"' in ln and "ceo-orchestration" in ln:
            continue
        kept.append(ln)
    return bool(M1_RE.search("\n".join(kept)))
# ---------------------------------------------------------------------------
# M4 — RE-DERIVAÇÃO LOCAL DO SLUG (PLAN-182 W3, S321)
#
# Por que este marcador existe. O gate `--assert-migrated` pergunta uma
# coisa só: "algum módulo runtime ainda constrói o LITERAL
# `~/.claude/projects/ceo-orchestration`?" — e a resposta é 0 desde a W1.
# Mas o contrato que `runtime_paths` declara (item 2: nenhum arquivo
# re-deriva o caminho localmente) tem uma SEGUNDA metade que nenhum
# instrumento media: módulos que não usam o literal e mesmo assim
# constroem o slug por conta própria.
#
# Medido na S321: ~18 call sites vivos em 4 grafias distintas
# (`.lstrip('-')`, `.strip('-')`, `'-' + x.lstrip('/')`, `.resolve()`
# antes do slug) que produzem TRÊS diretórios diferentes para o MESMO
# projeto — ex. com CLAUDE_PROJECT_DIR=/tmp/adopter-one:
# `-tmp-adopter-one` vs `-private-tmp-adopter-one` vs `tmp-adopter-one`.
# Um gate verde ao lado de três diretórios divergentes é a classe
# "instrumento verde cuja pergunta envelheceu".
#
# ESCOPO DELIBERADO: M4 é VISÍVEL (aparece nos marcadores, tem modo
# próprio `--assert-no-local-slug`) mas NÃO entra no offender-set do
# `--assert-migrated`. Os dois medem perguntas diferentes e a resposta de
# um não deve mascarar a do outro; flipar o gate é decisão do Owner sobre
# uma janela advisory, no molde de CEO_SPAWN_FILE_ASSIGNMENT_REQUIRED.
M4_RE = re.compile(
    r"""replace\(\s*['"]/['"]\s*,\s*['"]-['"]\s*\)"""      # slug: '/' -> '-'
    r"""|lstrip\(\s*['"]-['"]\s*\)"""                       # normalização do slug
    r"""|strip\(\s*['"]-['"]\s*\)"""
)
# Só conta quando a linha está NO CONTEXTO de resolução de estado — senão
# um `.replace('/', '-')` de slugify de nome de arquivo entraria como dívida.
M4_CTX = ("projects", "audit", "state_dir", "statedir", "slug", "runtime_state")


def _m4_hits(rel, body):
    """Linhas que re-derivam o slug localmente, com contexto de estado."""
    if rel in M1_SANCTIONED:
        return []
    hits = []
    for i, ln in enumerate(body.splitlines(), start=1):
        if M1_ALLOW_MARK in ln:
            continue
        if not M4_RE.search(ln):
            continue
        low = ln.lower()
        if any(c in low for c in M4_CTX):
            hits.append(i)
    return hits


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
        if _m1_hit(rel, body):
            markers.append("M1-constroi-caminho")
        if p.endswith(".py") and M2_RE.search(body):
            markers.append("M2-importa-resolvedor")
        if any(e in body for e in M3_ENVS):
            markers.append("M3-consome-env")
        m4 = _m4_hits(rel, body) if p.endswith((".py", ".sh")) else []
        if m4:
            markers.append("M4-rederiva-slug-local")
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
                    "m4_linhas": m4,
                    "na_cura_w1": art in ("hook", "script", "installer",
                                          "dist", "ci", "template", "test")})
    return fam


# US2 — matriz ARTEFATO × env. Cada coluna roda UMA subprocess com HOME
# isolado (nunca toca o estado do operador) que resolve TODOS os anchors de
# uma vez; a forma ingênua (uma subprocess por célula) custaria 18× mais
# processos para a mesma resposta.
#
# Os anchors cobrem a lista fechada da US5 (`PLAN-182/w0-medicao-S316.md`),
# colapsando as 19 rotações de log num único anchor de log: o que a matriz
# precisa provar é QUAL MÓDULO decide cada caminho, não quantos arquivos o
# padrão gerou.
#
# Duas ausências DECLARADAS, não silenciadas: `filelock` não resolve caminho
# (recebe o path pronto — é o chamador que decide) e `scratchpad_lib` resolve
# por sessão, não por env de projeto. Fingir um anchor para eles produziria
# célula verde sem sujeito.
ARTIFACT_ANCHORS = {
    # artefato .salt / dir do slug
    "injection_salt(dir do salt)": (
        "from _lib import injection_salt as s; "
        "_r(getattr(s, '_salt_path', None))"),
    "injection_salt._slug_dir": (
        "from _lib import injection_salt as s; _r(getattr(s, '_slug_dir', None))"),
    # artefatos audit-log.*
    "audit_emit._audit_dir": (
        "from _lib import audit_emit as m; _r(getattr(m, '_audit_dir', None))"),
    "audit_emit._log_path": (
        "from _lib import audit_emit as m; _r(getattr(m, '_log_path', None))"),
    "audit_emit._lock_path": (
        "from _lib import audit_emit as m; _r(getattr(m, '_lock_path', None))"),
    "audit_emit._errors_path": (
        "from _lib import audit_emit as m; _r(getattr(m, '_errors_path', None))"),
    "audit_emit._fallback_log_path": (
        "from _lib import audit_emit as m; "
        "_r(getattr(m, '_fallback_log_path', None))"),
    # artefatos audit-key / last-hmac / chain-length
    "audit_hmac._audit_dir_from_env": (
        "from _lib import audit_hmac as m; "
        "_r(getattr(m, '_audit_dir_from_env', None))"),
    "audit_hmac.key_path": (
        "from _lib import audit_hmac as m; _r(getattr(m, 'key_path', None))"),
    "audit_hmac.last_hmac_path": (
        "from _lib import audit_hmac as m; "
        "_r(getattr(m, 'last_hmac_path', None))"),
    "audit_hmac.chain_length_path": (
        "from _lib import audit_hmac as m; "
        "_r(getattr(m, 'chain_length_path', None))"),
    # artefato state/
    "state_store._state_root": (
        "from _lib import state_store as m; _r(getattr(m, '_state_root', None))"),
    # artefato memory-shared/
    "memory_shared._storage_root": (
        "from _lib import memory_shared as m; "
        "_r(getattr(m, '_storage_root', None))"),
    "memory_shared._index_path": (
        "from _lib import memory_shared as m; _r(getattr(m, '_index_path', None))"),
    "memory_shared._lock_path": (
        "from _lib import memory_shared as m; _r(getattr(m, '_lock_path', None))"),
    # spool (o caminho paralelo que tambem escreve log/errors)
    "spool_writer._project_dir_from_env": (
        "from _lib import spool_writer as m; "
        "_r(getattr(m, '_project_dir_from_env', None))"),
    "spool_writer._state_dir": (
        "from _lib import spool_writer as m; _r(getattr(m, '_state_dir', None))"),
    "spool_writer._canonical_log_path": (
        "from _lib import spool_writer as m; "
        "_r(getattr(m, '_canonical_log_path', None))"),
    "spool_writer._errors_path": (
        "from _lib import spool_writer as m; _r(getattr(m, '_errors_path', None))"),
}

# Compatibilidade: o nome antigo segue apontando para os 3 resolvedores
# centrais, porque o pytest da S316 asserta por chave literal.
RESOLVERS = {k: ARTIFACT_ANCHORS[k] for k in (
    "audit_emit._audit_dir", "state_store._state_root",
    "injection_salt(dir do salt)")}

# BOUNDING RULE (US2). O plano fala em "as 33 vars de env-inventory.json".
# Nem 33 nem 500 (o total do inventario) e o dominio: o dominio sao as vars
# que os 8 modulos da familia REALMENTE leem — derivado por `--env-domain`,
# 21 hoje, das quais HOME/USER/PYTEST_CURRENT_TEST nem constam do inventario.
# Destas 21, as colunas abaixo sao as PATH-RELEVANTES; as demais
# (CEO_AUDIT_HMAC_DISABLE, CEO_AUDIT_LOG_ROTATE_BYTES, CEO_AUDIT_SYNC_MODE,
# CEO_TEST_HARNESS, PYTEST_CURRENT_TEST, CLAUDE_SESSION_ID) sao flags de
# COMPORTAMENTO: nao entram na matriz de caminho, e `--env-domain` as
# classifica para que a exclusao seja auditavel em vez de tacita.
_FAKE = "/tmp/fake"
ENV_COMBOS = {
    # "sem-env" e o caso PATH-only: so HOME/PATH/PYTHONDONTWRITEBYTECODE.
    "sem-env": {},
    "CLAUDE_PROJECT_DIR": {"CLAUDE_PROJECT_DIR": _FAKE + "-proj"},
    "CEO_STATE_ROOT": {"CEO_STATE_ROOT": _FAKE + "-state-root"},
    "CEO_PROJECT_NAME": {"CEO_PROJECT_NAME": "outro-projeto"},
    "CEO_AUDIT_LOG_DIR": {"CEO_AUDIT_LOG_DIR": _FAKE + "-audit"},
    "CEO_AUDIT_LOG_PATH": {"CEO_AUDIT_LOG_PATH": _FAKE + "-audit/log.jsonl"},
    "CEO_AUDIT_LOG_LOCK": {"CEO_AUDIT_LOG_LOCK": _FAKE + "-audit/log.lock"},
    "CEO_AUDIT_LOG_ERR": {"CEO_AUDIT_LOG_ERR": _FAKE + "-audit/log.errors"},
    "CEO_AUDIT_LOG_FALLBACK_PATH": {
        "CEO_AUDIT_LOG_FALLBACK_PATH": _FAKE + "-fallback/log.jsonl"},
    "CEO_AUDIT_KEY_PATH": {"CEO_AUDIT_KEY_PATH": _FAKE + "-keys/audit-key"},
    "CEO_AUDIT_LAST_HMAC_PATH": {
        "CEO_AUDIT_LAST_HMAC_PATH": _FAKE + "-keys/last-hmac"},
    "CEO_AUDIT_CHAIN_LENGTH_PATH": {
        "CEO_AUDIT_CHAIN_LENGTH_PATH": _FAKE + "-keys/chain-length"},
    "CEO_PROJECT_STATE_DIR": {"CEO_PROJECT_STATE_DIR": _FAKE + "-pstate"},
    "CEO_MEMORY_SHARED_PATH": {"CEO_MEMORY_SHARED_PATH": _FAKE + "-mem"},
}

# Modulos da familia que NAO resolvem caminho — declarados para que a
# ausencia deles na matriz seja uma decisao lida, nao um esquecimento.
ANCHORLESS_MODULES = {
    "filelock": "recebe o path pronto do chamador; nao decide caminho",
    "scratchpad_lib": "resolve por sessao (CLAUDE_SESSION_ID), nao por env de projeto",
}

# Vars do dominio que sao flags de COMPORTAMENTO, nao de caminho.
BEHAVIOR_ONLY_ENVS = (
    "CEO_AUDIT_HMAC_DISABLE", "CEO_AUDIT_LOG_ROTATE_BYTES",
    "CEO_AUDIT_SYNC_MODE", "CEO_TEST_HARNESS", "PYTEST_CURRENT_TEST",
    "CLAUDE_SESSION_ID",
)

_PROBE_PREAMBLE = (
    "import sys, json\n"
    "sys.path.insert(0, {hooks!r})\n"
    "_out = {{}}\n"
    "def _r(fn):\n"
    "    _out[_k] = 'API-DRIFT' if not callable(fn) else str(fn())\n"
)


def _probe_source(hooks: str) -> str:
    """Fonte do probe: resolve TODOS os anchors numa unica subprocess.

    Cada anchor roda dentro de try/except proprio — um modulo que falhe ao
    importar degrada SUA celula para ``ERRO: ...`` em vez de derrubar a
    coluna inteira (o modo de falha que a forma uma-subprocess-por-coluna
    introduziria se o corpo fosse monolitico).
    """
    lines = [
        "import sys, json",
        "sys.path.insert(0, {0!r})".format(hooks),
        "_out = {}",
        "_k = None",
        "def _r(fn):",
        "    _out[_k] = 'API-DRIFT' if not callable(fn) else str(fn())",
    ]
    for key, body in ARTIFACT_ANCHORS.items():
        lines.append("_k = {0!r}".format(key))
        lines.append("try:")
        for stmt in body.split("; "):
            lines.append("    " + stmt)
        lines.append("except Exception as _e:")
        lines.append("    _out[_k] = 'ERRO: %s' % _e")
    lines.append("print(json.dumps(_out))")
    return "\n".join(lines)


def matrix() -> Dict[str, Dict[str, str]]:
    """Matriz ARTEFATO x env: linha = anchor, coluna = combinacao de env."""
    hooks = os.path.join(REPO_ROOT, ".claude", "hooks")
    code = _probe_source(hooks)
    out: Dict[str, Dict[str, str]] = {k: {} for k in ARTIFACT_ANCHORS}
    with tempfile.TemporaryDirectory() as fake_home:
        for cname, extra in ENV_COMBOS.items():
            env = {"HOME": fake_home, "PATH": os.environ.get("PATH", ""),
                   "PYTHONDONTWRITEBYTECODE": "1"}
            env.update(extra)
            try:
                r = subprocess.run(
                    [sys.executable, "-c", code],
                    capture_output=True, text=True, timeout=60, env=env)
                col = json.loads(r.stdout) if r.stdout.strip() else {}
            except Exception as exc:
                col = {}
                for k in ARTIFACT_ANCHORS:
                    col[k] = "ERRO: {0}".format(exc)
            for k in ARTIFACT_ANCHORS:
                out[k][cname] = col.get(k, "(vazio)")
    return out


def env_domain() -> Dict[str, Any]:
    """Bounding rule da US2: o dominio de env, derivado do CODIGO.

    O plano fala em "as 33 vars de env-inventory.json". Nem 33 nem 500 (o
    total do inventario) e o dominio da familia: o dominio e o conjunto que
    os 8 modulos de ``M2_MODULES`` efetivamente LEEM. Tudo fora dele nao
    pode mover caminho — e essa e a regra que limita a matriz.
    """
    lib = os.path.join(REPO_ROOT, ".claude", "hooks", "_lib")
    upper = "[A-Z][A-Z0-9_]*"
    pat = re.compile(
        r"os\.environ(?:\.get)?\(\s*[\"']({u})[\"']"
        r"|getenv\(\s*[\"']({u})[\"']"
        r"|os\.environ\[\s*[\"']({u})[\"']".format(u=upper))
    domain: Dict[str, List[str]] = {}
    for mod in M2_MODULES:
        path = os.path.join(lib, mod + ".py")
        if not os.path.isfile(path):
            continue
        with open(path, encoding="utf-8") as fh:
            text = fh.read()
        for match in pat.finditer(text):
            for grp in match.groups():
                if grp:
                    domain.setdefault(grp, [])
                    if mod not in domain[grp]:
                        domain[grp].append(mod)
    inv_path = os.path.join(REPO_ROOT, ".claude", "scripts",
                            "env-inventory.json")
    inventory: List[str] = []
    try:
        with open(inv_path, encoding="utf-8") as fh:
            inventory = list(json.load(fh).get("vars", {}))
    except Exception:
        inventory = []
    return {
        "domain_size": len(domain),
        "domain": {k: sorted(v) for k, v in sorted(domain.items())},
        "path_relevant_columns": sorted(ENV_COMBOS),
        "behavior_only": sorted(BEHAVIOR_ONLY_ENVS),
        "anchorless_modules": ANCHORLESS_MODULES,
        "inventory_total": len(inventory),
        "domain_absent_from_inventory": sorted(
            k for k in domain if k not in inventory),
    }


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
    ap.add_argument("--env-domain", action="store_true")
    ap.add_argument("--surfaces", action="store_true")
    ap.add_argument("--assert-migrated", action="store_true")
    ap.add_argument(
        "--assert-no-local-slug", action="store_true",
        help="PLAN-182 W3: falha se algum módulo runtime re-derivar o slug "
             "localmente (M4). ADVISORY hoje — só falha sob "
             "CEO_AUDIT_FAMILY_M4_REQUIRED=1; ver o comentário do M4.")
    args = ap.parse_args(argv)

    if args.env_domain:
        print(json.dumps(env_domain(), indent=1, ensure_ascii=False))
        return 0
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
        # Escopo declarado no PRÓPRIO instrumento (S321): este gate mede o
        # LITERAL e nada mais. Quem responde pela segunda metade do
        # contrato é --assert-no-local-slug.
        m4n = sum(1 for f in fam
                  if f["artefato"] in ("hook", "script", "installer", "dist")
                  and "M4-rederiva-slug-local" in f["marcadores"])
        print(f"  (escopo: literal apenas — {m4n} módulo(s) runtime "
              "re-derivam o slug localmente; ver --assert-no-local-slug)")
        return 1 if offenders else 0

    if args.assert_no_local_slug:
        offenders = [f for f in fam
                     if f["artefato"] in ("hook", "script", "installer", "dist")
                     and "M4-rederiva-slug-local" in f["marcadores"]]
        for f in sorted(offenders, key=lambda x: x["modulo"]):
            print("{}: linhas {}".format(
                f["modulo"], ",".join(str(n) for n in f["m4_linhas"])))
        required = os.environ.get("CEO_AUDIT_FAMILY_M4_REQUIRED") == "1"
        print(f"assert-no-local-slug: {len(offenders)} módulo(s) runtime "
              "re-derivam o slug localmente "
              f"({'ENFORCED' if required else 'ADVISORY'})")
        return 1 if (offenders and required) else 0

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
