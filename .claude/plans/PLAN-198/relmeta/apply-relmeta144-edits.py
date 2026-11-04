#!/usr/bin/env python3
"""Material VERSIONADO da cerimonia relmeta-144 (PLAN-198, RM da v1.4.4).

Aplica as TRES edicoes que destravam `release.sh` para a v1.4.4:

  1. o bloco PER-RELEASE do driver (TARGET_BASE, titulo, escopo, headline);
  2. o sha256 do driver no manifesto ADR-192 (canonico);
  3. o re-pin CONSCIENTE do teste que fixa o escopo da anotacao da tag.

Clonado POR REMOCAO de `PLAN-194/relmeta/apply-relmeta143-edits.py`. O que
sai: as ancoras da 1.4.3 que o HEAD ja nao sustenta como estavam (o gravador
da condicao 67 mudou para `_lib/_audit_log_parts/rotation_storage.py`, o
`external_wait` do /ceo-boot para `_lib/_ceo_boot_parts/`, e o range do pin
do Codex perdeu o limite superior), re-ancoradas no codigo que as sustenta
hoje; o acoplamento com o guia de recuperacao; a tolerancia a um preambulo
com o rotulo da release anterior. O que muda:

- a constante PREV_BASE da 1.4.3 vira DUAS: o alvo anterior do driver
  (PREV_TARGET, 1.4.3, a ancora inicial do bloco) e a base da faixa
  (RANGE_BASE, 1.4.2, o commit da tag v1.4.2): a v1.4.3 so teve a rc.1, e a
  tag da 1.4.4 vale pelo trem inteiro `v1.4.2..HEAD`;
- as ancoras herdadas leem as frases na secao [1.4.3] do CHANGELOG (que segue
  byte a byte a assinada pela rc.1) e as novas na secao [1.4.4]; cada
  paragrafo da headline tem uma frase na [1.4.4] (PARAGRAPH_LINKS; a mesma
  frase serve aos paragrafos 2 e 3);
- titulo e headline em ingles, ASCII estrito, nenhuma linha que comece com
  `#`, nenhuma palavra de publicacao;
- o derivador confere, por AST, que todo nome que ele le e definido em algum
  lugar do arquivo (assert_no_dangling_names, a licao do molde clonado), em
  todo modo, antes de qualquer outra coisa; um nome definido so como local de
  outra funcao nao e pego ali e falha (NameError) ao rodar.

  python3 apply-relmeta144-edits.py [--repo <root>] [--check | --claims-only | --verify | --tag-text | --self-check]

(`--repo` vale, por padrão, o diretório atual: a linha Check da W2 do PLAN-198 roda o `--claims-only` da raiz.)

`--check` nao escreve nada: imprime as derivacoes e valida ancoras e
pre-condicoes. `--claims-only` roda so as ancoras e imprime uma linha
PASS/FAIL por ancora, com o resultado de codigo e o de texto (rc 0 = todas
passam). `--tag-text` imprime so o texto da tag derivado (o derive o grava no
sentinel). `--self-check` roda so a conferencia de nomes. O `--verify` e o
ultimo passo da linha hard `hard-relmeta.sh` do SIGN, que o roda isolado
(`python3 -I -B`: nem o diretorio deste script nem o site do usuario entram
no sys.path, e ele so importa a stdlib): re-deriva, a partir das
PRE-imagens do HEAD, o escopo, o bloco, o manifesto e o teste, e exige
igualdade BYTE A BYTE com os 3 arquivos
da arvore (que no SIGN ja tem o patch aplicado); confere a secao do texto da
tag e as linhas Derived-From e Scope-Derived do sentinel, e o CHANGELOG como
pre-condicao. Sem `git status`: so plumbing, com GIT_OPTIONAL_LOCKS=0. As
ancoras NAO rodam no `--verify`: elas rodam no `--claims-only`, manual antes
da rc.1 e do GA. As sondas escrevem SO em diretorios temporarios proprios,
removidos ao fim. stdlib only, Python >= 3.9.

POR QUE ISTO E UMA CERIMONIA. `.claude/governance/gate-scripts-manifest.txt` e
CANONICO, e `.claude/scripts/local/release.sh` e MEMBRO dele: mudar um byte do
driver sem re-pinar o sha derruba os workflows que conferem o manifesto. E o
titulo, o escopo e a headline vao para DENTRO da anotacao ASSINADA da tag.
"""
from __future__ import annotations

import argparse
import ast
import builtins
import hashlib
import json
import os
import pathlib
import re
import shutil
import subprocess
import sys
import tempfile
import time
from typing import Callable, Dict, List, Optional, Set, Tuple

EDIT_COUNT_DECLARED = 3

RELEASE_SH = ".claude/scripts/local/release.sh"
MANIFEST = ".claude/governance/gate-scripts-manifest.txt"
SCOPE_TEST = ".claude/scripts/tests/test_release_bump_sites.py"
CHANGELOG = "CHANGELOG.md"
PACK_DIR = ".claude/plans/PLAN-198/relmeta"
SENTINEL = ".claude/plans/PLAN-198/relmeta-approved.md"
TARGETS = (RELEASE_SH, MANIFEST, SCOPE_TEST)

BASE_TAG = "v1.4.2"
# o commit da v1.4.2 (o mesmo literal da relmeta-143)
BASE_SHA = "b55084da6dd8e4a05fc9893b2690df8aebcfd0ca"
# a base da FAIXA (a ultima release publicada, v1.4.2) e o alvo ANTERIOR do
# driver (1.4.3, que so teve a rc.1): na relmeta-143 eram a mesma constante
RANGE_BASE = "1.4.2"
PREV_TARGET = "1.4.3"
TARGET_BASE = "1.4.4"
# a cerimonia anterior, citada no docstring do teste de escopo
PREV_RELMETA = "relmeta-143"
PREV_OWN_PLAN = "PLAN-194"
# o plano desta release: o commit dos materiais o cita, entao ele TEM de ja
# estar no trem — senao commitar os materiais mudaria o escopo derivado
OWN_PLAN = "PLAN-198"
# planos que o escopo desta release TEM de conter (PLAN-198, Approach 1)
REQUIRED_PLANS = ("PLAN-197", "PLAN-198")
# nomes da relmeta-143 que sairam deste derivador: nenhum pode ser lido aqui
REMOVED_NAMES = ("PREV_BASE", "DR_GUIDE", "AUDIT_QUERY_TEST_OLD")

# marcadores da secao derivada do sentinel
TAG_TEXT_BEGIN = "<!-- texto-da-tag: derivado -->"
TAG_TEXT_END = "<!-- fim do texto-da-tag -->"
# a mensagem que o driver assina (release.sh, fase tag): a secao do sentinel a
# reproduz; o --verify exige este molde UMA vez no driver com o patch
TAG_MSG_TEMPLATE = (
    'msg="$TARGET_TAG — $RELEASE_TITLE\n'
    '\n'
    'Anchor: $anchor\n'
    'Scope:  $RELEASE_SCOPE\n'
    '\n'
    'Headline: $RELEASE_HEADLINE\n'
    '\n'
    'No speed claim. See CHANGELOG.md [$TARGET_BASE]."\n'
)

# --- ancoras (conferidas sobre a arvore) ------------------------------------
CC_MIN = "2.1.280"
CODEX_VER = "0.160.0"
CODEX_PLATFORMS = frozenset(["aarch64-apple-darwin"])
UPGRADE_SH = "scripts/upgrade.sh"
INSTALL_SH = "scripts/install.sh"
# o piso do Claude Code (PLAN-193 OQ-9): o bloco entre estes marcadores e o
# mesmo no install.sh e no upgrade.sh; a sonda o roda contra um claude FALSO
CC_FLOOR_BEGIN_RX = r"(?m)^# >>> claude-code-floor\b[^\n]*\n"
CC_FLOOR_END_RX = r"(?m)^# <<< claude-code-floor\b[^\n]*$"
CC_FLOOR_FN = "_claude_code_floor_check"
CC_FLOOR_OVERRIDE = "--allow-old-claude-code"
CC_FLOOR_EXIT = "6"
SUPPORT_MD = "SUPPORT.md"
NPM_PACKAGE = "npm/package.json"
NPM_PUBLISH_YML = ".github/workflows/npm-publish.yml"
NPM_RC_SKIP = "if: \"!contains(github.ref, '-rc.')\""
# o commit da v1.4.3-rc.1 (a tag descasca nele; o clone do SIGN pode nao ter tags)
RC1_SHA = "5e7cb65ebc259da586256ddb6b29918ba3a39ab6"
CODEX_MANIFEST = ".claude/governance/codex-cli-pin-manifest.json"
CODEX_PIN_TXT = ".claude/governance/codex-cli-pin.txt"
CODEX_PIN_FLOOR_BODY = ">=0.128.0"
CLI_CURRENCY = ".claude/hooks/_lib/cli_currency.py"
PAIR_RAIL_PARTS = ".claude/hooks/_lib/_pair_rail_parts"
CODEX_REPIN_COMMIT = "4a1eec73e630"
HARNESS_HOOK = ".claude/hooks/check_harness_config.py"
HARNESS_DIR = ".claude/hooks/_lib/harness_replay"
HARNESS_OLD_DIR = ".claude/hooks/tests/fixtures/harness-config/replay"
HARNESS_PLACEHOLDER = "@HARNESS_REPLAY_PROJECT_DIR@"
HARNESS_FIXTURES = frozenset([
    "agent_spawn_named_no_skill_content.json",
    "bash_safety_destructive.json",
    "canonical_edit_unauthorized.json",
])
HARNESS_GATE_PREFIX = "OK: harness-config gate green (static=yes, replay=yes, "
# as entradas do DENY_BASELINE do gate que a instalacao --ceremony user nao grava
# (residuo declarado na [1.4.3]; a ancora exige EXATAMENTE este conjunto)
USER_DENY_GAP = ("Bash(git push --force*)", "Edit(PROTOCOL.md)", "Edit(.claude/settings.json)",
                 "Edit(SPEC/**)")
HIST_SCRIPT = "scripts/tests/test-upgrade-historical-adopter.sh"
HIST_GROUPS_NEW = ("harness-upgrade", "harness-fresh", "harness-red")
SMOKE_YML = ".github/workflows/smoke-install.yml"
# o land do C9 (perna livre do upgrade) e o SIGN da W7a
HARNESS_COMMITS = ("7428d25bb520", "b0f5fd453fb9")
# a condicao 67: a fachada audit_log.py executa as partes de _lib/_audit_log_parts/,
# e o append_entry mora hoje em rotation_storage.py
AUDIT_LOG = ".claude/hooks/audit_log.py"
AUDIT_LOG_PARTS = ".claude/hooks/_lib/_audit_log_parts"
AUDIT_LOG_WRITER = ".claude/hooks/_lib/_audit_log_parts/rotation_storage.py"
AUDIT_LOG_WRITER_PART = "rotation_storage"
AUDITRACE_SENT = ".claude/plans/PLAN-194/wave-auditrace-approved.md"
AUDITRACE_COMMIT = "65cd50d7df68"
V140_RC1_ENVELOPE = ".claude/governance/pair-rail-verdict-v1.4.0-rc.1.md"
COND67_DECL = "67. **`append_entry` lê o predecessor e calcula o HMAC FORA do lock**"
DEFAULT_MODE_LINE = 'DEFAULT_MODE_BASELINE="manual"'
DEFAULT_MODE_JQ = 'has("defaultMode")'
DEFAULT_MODE_PY = 'perms.setdefault("defaultMode", sys.argv[3])'
DEFAULT_MODE_SKIP = "CEO_INSTALL_SKIP_DENY_BASELINE"
USER_TEMPLATE = "templates/settings/settings.user.json"
TEMPLATES_DIR = "templates/settings"
COST_HOOK = ".claude/hooks/check_cost_envelope.py"
COST_EVENT = "cost_envelope_capped"
COST_KWARGS = frozenset([
    "class_tier", "window_breached", "cap_cents", "current_cents", "session_id", "project",
])
CENV_COMMIT = "1142884039f8"
STATUS_PY = ".claude/scripts/status.py"
SUBSTRATE_DRIFT = ".claude/scripts/check-substrate-drift.py"
AUDIT_QUERY_TEST = ".claude/scripts/tests/test_audit_query_shared_flags_order.py"
CEO_BOOT_PY = ".claude/scripts/ceo-boot.py"
CEO_BOOT_PARTS = ".claude/hooks/_lib/_ceo_boot_parts"
CEO_BOOT_INSTALL = "from _lib._ceo_boot_parts import install"
V140_ENVELOPE = ".claude/governance/pair-rail-verdict-v1.4.0.md"
V142_RC1_ENVELOPE = ".claude/governance/pair-rail-verdict-v1.4.2-rc.1.md"
BACKUP_SH = ".claude/scripts/ceo-backup.sh"
# a guarda de Bash contra execucao indireta (PLAN-195, ADR-201)
BASH_SAFETY = ".claude/hooks/check_bash_safety.py"
BASH_SAFETY_PARTS = ".claude/hooks/_lib/_bash_safety_parts"
BASH_POSTURE_SCAN = ".claude/hooks/_lib/_bash_safety_parts/posture_scan.py"
INDIRECT_GUARD = ".claude/hooks/_lib/bash_indirect_guard.py"
INDIRECT_SWITCHES = ("CEO_BASH_INDIRECT_GUARD", "CEO_BASH_INDIRECT_HEURISTICS")
INDIRECT_GATE_LINE = ('indirect_hit = None if _indirect_switch == "0" '
                      'else _indirect_guard.scan(')
ADR_201 = ".claude/adr/ADR-201-bash-guard-indirect-execution.md"
# a divisao em modulos (PLAN-197, ADR-202)
AUDIT_EMIT = ".claude/hooks/_lib/audit_emit.py"
AUDIT_EMIT_PARTS = ".claude/hooks/_lib/_audit_emit_parts"
ADR_202 = ".claude/adr/ADR-202-kernel-and-hooks-modularization.md"
THIN_LIMITS = ((BASH_SAFETY, 100), (AUDIT_EMIT, 1000))
# o spool: um hook registrado sai sem drenar
PYTHON_HOOK_SH = ".claude/hooks/_python-hook.sh"
BOUNDED_EXIT_LINE = "export CEO_HOOK_BOUNDED_EXIT=1"
SPOOL_WRITER = ".claude/hooks/_lib/spool_writer.py"
# as duas correcoes desta release (commits assinados pelo maintainer)
KERNEL_HOOK = ".claude/hooks/check_arbitration_kernel.py"
KERNEL_FIX_COMMIT = "161e1dc3331e71f26e2d5a18eebea22e421068a4"
KERNEL_GUARD_TEST = ".claude/hooks/tests/test_kernel_decomposition_coverage.py"
KERNEL_PACKAGES = (
    ".claude/hooks/_lib/canonical_edit", ".claude/hooks/_lib/agent_spawn",
    ".claude/hooks/_lib/_policy_parts", ".claude/hooks/_lib/_audit_emit_parts",
    ".claude/hooks/_lib/_pair_rail_parts", ".claude/hooks/_lib/_audit_log_parts",
    ".claude/hooks/_lib/_bash_safety_parts", ".claude/hooks/_lib/adapters/live",
)
KERNEL_FLAT = (
    ".claude/hooks/_lib/model_currency.py", ".claude/hooks/_lib/cli_currency.py",
    ".claude/hooks/_lib/plan_paths.py", ".claude/hooks/_lib/bash_indirect_guard.py",
    ".claude/hooks/_lib/bash_indirect_telemetry.py",
)
REDACTOR = ".claude/hooks/_lib/secret_patterns.py"
EGRESS_REDACTOR = ".claude/hooks/_lib/codex_egress_redact.py"
REDACTOR_FIX_COMMIT = "54bab3cc1a3b1e98117b707e3d435809e7149694"
REDACTOR_TEST = ".claude/hooks/tests/test_secret_patterns.py"
# a condicao 58 do envelope assinado da v1.4.0 e o defeito dos offsets que o 54bab3cc corrige
COND58_DECL = "58. **O redator de saída para o Codex aplica spans NFKC no texto original**"
# os merges de pull request da faixa: #6 e #7 depois da rc.1
PR6_SHA = "d5e6d3885278611c7be58a4915a01d13259e9b46"
PR7_SHA = "888e9e6ca0adc292faf9be33ed6223583e1d2118"
PR_BEFORE_RC1 = 4
PR_AFTER_RC1 = (6, 7)
CANON_ORACLE = ".claude/hooks/check_canonical_edit.py"
PR_CANONICAL = 233
PR_KERNEL_AS_MERGED = 15
# o piso do VETO e o allowlist de modelos (PLAN-176, ADR-149 Amendment 4)
MODEL_CURRENCY = ".claude/hooks/_lib/model_currency.py"
MODEL_LEDGER = ".claude/scripts/model-deprecations.json"
MODEL_CALLERS = (".claude/hooks/_lib/agent_frontmatter.py", ".claude/hooks/_lib/escalation_signals.py",
                 ".claude/hooks/_lib/effective_config.py")
# (id, predicado, retirada no ledger ou None): o que a frase afirma, sondado
MODEL_PROBES = (
    ("claude-opus-4-1-20250805", "is_veto_floor_model", "2026-08-05"),
    ("gpt-5", "is_veto_floor_model", None),
    ("claude-sonnet-4-20250514", "is_allowed_model", "2026-06-15"),
    ("gemini-2.5-pro", "is_allowed_model", None),
    ("grok-4", "is_allowed_model", None),
)

RELEASE_TITLE = (
    "Maintenance release: the train since v1.4.2, with a Bash guard against indirect"
    " execution, hooks split into modules, and fixes to the kernel hard-deny list and"
    " the secret redactor"
)

# Vai para DENTRO da anotacao assinada da tag (rc e GA: nenhuma palavra de
# publicacao). ASCII estrito, sem crase, sem cifrao, sem barra invertida, sem
# aspa dupla, nenhuma linha que comece com # (a limpeza padrao do git a
# apagaria), e toda versao x.y.z escrita com o prefixo v (um semver NU aqui
# reprovaria test_driver_derives_every_version_string_from_target_base). Cada
# paragrafo tem ancora em CLAIMS e uma frase na secao [1.4.4] do CHANGELOG
# (PARAGRAPH_LINKS; a mesma frase serve aos paragrafos 2 e 3).
RELEASE_HEADLINE = """Maintenance release (PLAN-198). v1.4.3 never reached npm: only
v1.4.3-rc.1 was tagged, so this release covers the whole train since
v1.4.2, and everything in the v1.4.3 entry of the CHANGELOG is part
of it, as changed by the v1.4.4 entry. The requirements do not
change from v1.4.2: Claude Code v2.1.280 or later (install.sh and
upgrade.sh still refuse an older claude on the PATH with exit 6,
unless --allow-old-claude-code is given), Python 3.9 or later and
Node.js 20 or later for the npm shim.

From the v1.4.3 entry: the harness-config gate of /ceo-boot turns
green with the default ceremony (maintainer), both on an install
upgraded from v1.4.2 with upgrade.sh and on a fresh install; this
green is claimed for the default ceremony only. The agent_spawn
writer reads the previous chain link, computes the HMAC, writes the
line and updates the sidecar under one lock of the log, which retires
signed condition 67 of v1.4.0-rc.1; breaks the race already wrote
stay in the logs, and writers that resolve different locks for the
same log still do not exclude each other.

Also from that entry: a fresh --ceremony user install writes
permissions.defaultMode with the value manual when the settings.json
produced by that same run has none, unless
CEO_INSTALL_SKIP_DENY_BASELINE=1, and a settings.json that existed
before the install is never touched. On an install that registered
the cost-envelope hook by hand, a block is recorded in the audit log;
no shipped settings template registers that hook. Fixes to
audit-query.py, /status, /ceo-boot and check-substrate-drift.py.

New since v1.4.3-rc.1: a bounded scan in the Bash guard against
indirect execution, on by default (PLAN-195, ADR-201); it only adds
blocks, and CEO_BASH_INDIRECT_GUARD=0 turns it off. Several of the
largest hooks and scripts become thin entry points over modules
under .claude/hooks/_lib/ (PLAN-197, ADR-202): a hook patched by hand
must be patched again in its module. A registered hook no longer
drains the audit spool at exit, a partial cure.

The preparation of this release found that the kernel's hard-deny
list had not followed the code that moved out of seven kernel entry
points; that code is hard-deny again. The secret redactor that the
Codex and Grok egress uses had, since v1.0.0, cut the text at offsets
taken from its normalized form, which the signed v1.4.0 verdict had
declared as its condition 58; its scan() offsets now index the text
passed in. Neither fix has a sentinel file.

The honest part: most of this train after v1.4.3-rc.1 reached main
through two pull-request merges, without the signing ceremony; four
earlier ones are in the v1.4.3 entry. The two changed 233 canonical
paths, 15 of them kernel paths by the list as merged, and with them
the meaning of three governance checks: the VETO floor and the model
allowlist now accept model families, retired ids among them, and a
Codex CLI newer than the one the manifest pins by sha256 (v0.160.0,
one platform) passes on a version floor, without a matching hash. No
signed sentinel ratifies those files, and main has no branch
protection and no ruleset (measured through the GitHub API on
2026-11-03).

Declared, with no release assigned to their cure: the audit spool
cure is partial, the new guard's false-positive limits were never
measured on this implementation, and the backup leaves out the key
material. One condition of the redactor fix is declared too: the
ingress path redacts the raw answer text before parsing it, so a
redaction can change whether an answer parses; its structural cure
is scheduled for the next release. Of the signed v1.4.0 annex,
conditions 67 and 58 are cured, and this release does not claim the
cure of any other annex condition. This release does not claim the
cure of the three P1 findings of the signed v1.4.2-rc.1 annex.
Claude Code's cleanup (cleanupPeriodDays, default 30) can still
delete the audit logs, and no plan in this release carries a
structural cure. Everything else that stays open is in the
Known-open of the CHANGELOG entry."""

# Uma frase da secao [1.4.4] por paragrafo da headline, NA ORDEM: o paragrafo
# so existe se a entrada desta release diz o mesmo (as ancoras de cada
# paragrafo conferem o resto, na [1.4.4] ou na [1.4.3] herdada).
PARAGRAPH_LINKS = (
    "**v1.4.3 never reached npm.**",
    "everything in `[1.4.3]` is part of this release",
    "everything in `[1.4.3]` is part of this release",
    "A new scan in the Bash guard blocks a destructive command that is reached indirectly, on by "
    "default (PLAN-195, ADR-201).",
    "Two of the defects this release fixes: the preparation of this release found that the kernel's "
    "hard-deny list had not followed the code that moved out of seven kernel entry points; and the "
    "secret redactor, since v1.0.0, cut the text at offsets taken from its normalized form, which "
    "the signed v1.4.0 verdict had declared as its condition 58.",
    "The honest part: most of this train after v1.4.3-rc.1 reached `main` through two pull-request "
    "merges, without the signing ceremony.",
    "No release is assigned to its cure yet.",
)

# Texto da 1.4.3 (e anterior) que nao pode sobreviver no bloco novo.
FORBID = (
    "Release de manutencao", "(PLAN-194)", "Os requisitos nao mudam", "(ADRs tocados:",
    "condicao 67", "A parte honesta", "Quatro merges", "2026-10-14", "re-pinado",
    "0.156.1", "Opus 5.5", "PLAN-190 / PLAN-193", "PLAN-162 / PLAN-165",
)


def die(msg: str) -> None:
    sys.stderr.write("FATAL: %s\n" % msg)
    raise SystemExit(2)


def run(repo: pathlib.Path, *args: str) -> str:
    """git com rc CONFERIDO: um produtor que morre nunca vira string vazia."""
    proc = subprocess.run(
        ["git", "-C", str(repo)] + list(args),
        stdout=subprocess.PIPE, stderr=subprocess.PIPE, universal_newlines=True)
    if proc.returncode != 0:
        die("git %s rc=%d: %s" % (" ".join(args), proc.returncode,
                                  proc.stderr.strip()))
    return proc.stdout


def run_bytes(repo: pathlib.Path, *args: str) -> bytes:
    proc = subprocess.run(
        ["git", "-C", str(repo)] + list(args),
        stdout=subprocess.PIPE, stderr=subprocess.PIPE)
    if proc.returncode != 0:
        die("git %s rc=%d: %s" % (" ".join(args), proc.returncode,
                                  proc.stderr.decode("utf-8", "replace").strip()))
    return proc.stdout


def git_rc(repo: pathlib.Path, *args: str) -> int:
    return subprocess.run(
        ["git", "-C", str(repo)] + list(args),
        stdout=subprocess.DEVNULL, stderr=subprocess.DEVNULL).returncode


def git_out(repo: pathlib.Path, *args: str) -> Tuple[int, str]:
    """git cujo rc a ANCORA julga (nunca die): (rc, stdout)."""
    proc = subprocess.run(
        ["git", "-C", str(repo)] + list(args),
        stdout=subprocess.PIPE, stderr=subprocess.DEVNULL, universal_newlines=True)
    return proc.returncode, proc.stdout


# --------------------------------------------------------------------------
# a licao do molde clonado: nenhum nome lido sem definicao
# --------------------------------------------------------------------------
def _stored_names(node: ast.AST) -> Set[str]:
    """Nomes que um escopo define: alvos de atribuicao, for, with, except,
    import, def/class aninhados, argumentos e declaracoes global/nonlocal."""
    out: Set[str] = set()
    for n in ast.walk(node):
        if isinstance(n, ast.Name) and isinstance(n.ctx, (ast.Store, ast.Del)):
            out.add(n.id)
        elif isinstance(n, (ast.FunctionDef, ast.AsyncFunctionDef, ast.ClassDef)):
            out.add(n.name)
        elif isinstance(n, (ast.Import, ast.ImportFrom)):
            for a in n.names:
                out.add((a.asname or a.name).split(".")[0])
        elif isinstance(n, ast.ExceptHandler) and n.name:
            out.add(n.name)
        elif isinstance(n, ast.arg):
            out.add(n.arg)
        elif isinstance(n, (ast.Global, ast.Nonlocal)):
            out.update(n.names)
    return out


def dangling_names(src: str) -> List[str]:
    """Os nomes LIDOS (ast.Name em Load) que nenhuma parte do arquivo define
    (atribuicao, for, with, except, import, def/class, argumento ou
    global/nonlocal, em QUALQUER escopo), nem os builtins. Pega um nome lido
    sem definicao em lugar nenhum do arquivo (uma constante de modulo
    removida); NAO pega um nome definido so como local de outra funcao e lido
    fora dela, que falha (NameError) ao rodar."""
    tree = ast.parse(src)
    module_names = _stored_names(tree) | set(dir(builtins)) | {"__file__", "__name__", "__doc__"}
    bad: Set[str] = set()

    def visit(node: ast.AST, visible: Set[str]) -> None:
        for child in ast.iter_child_nodes(node):
            if isinstance(child, (ast.FunctionDef, ast.AsyncFunctionDef, ast.Lambda)):
                inner = visible | _stored_names(child)
                for d in getattr(child, "decorator_list", []):
                    visit(d, visible)
                visit(child, inner)
            elif isinstance(child, ast.Name) and isinstance(child.ctx, ast.Load):
                if child.id not in visible:
                    bad.add("%s (linha %d)" % (child.id, child.lineno))
            else:
                visit(child, visible)

    visit(tree, module_names)
    return sorted(bad)


def assert_no_dangling_names() -> None:
    """Roda em TODO modo, antes de qualquer outra coisa: o derivador que le
    uma constante removida no clone por remocao nunca chega a derivar."""
    src = pathlib.Path(__file__).read_text(encoding="utf-8")
    bad = dangling_names(src)
    tree = ast.parse(src)
    lidos = {n.id for n in ast.walk(tree) if isinstance(n, ast.Name)}
    removidos = sorted(set(REMOVED_NAMES) & lidos)
    if bad or removidos:
        die("o derivador le nome sem definicao (licao do molde clonado): %s%s"
            % (", ".join(bad), ("; nomes removidos ainda usados: %s" % ", ".join(removidos))
               if removidos else ""))


def assert_base(repo: pathlib.Path, tag_required: bool) -> None:
    """BASE_SHA ancestral do HEAD; a tag BASE_TAG, se existe, descasca nele.

    Na derivacao a tag e obrigatoria; no --verify e opcional (o clone do
    roteiro pode nao trazer tags), mas, presente, tem de ser a da v1.4.2."""
    if git_rc(repo, "cat-file", "-e", "%s^{commit}" % BASE_SHA) != 0:
        die("o commit %s (v%s) nao esta no repositorio" % (BASE_SHA[:12], RANGE_BASE))
    if git_rc(repo, "merge-base", "--is-ancestor", BASE_SHA, "HEAD") != 0:
        die("%s (v%s) nao e ancestral do HEAD" % (BASE_SHA[:12], RANGE_BASE))
    has_tag = git_rc(repo, "rev-parse", "-q", "--verify", "refs/tags/%s" % BASE_TAG) == 0
    if not has_tag:
        if tag_required:
            die("tag %s ausente — a relmeta-144 deriva com a tag do GA %s no repositorio"
                % (BASE_TAG, BASE_TAG))
        return
    peeled = run(repo, "rev-parse", "--verify", "refs/tags/%s^{commit}" % BASE_TAG).strip()
    if peeled != BASE_SHA:
        die("a tag %s descasca para %s, nao para %s" % (BASE_TAG, peeled, BASE_SHA))


def derive_train(repo: pathlib.Path) -> Tuple[List[str], List[str]]:
    """Planos citados nos assuntos de commit + ADRs tocados na faixa.

    A regra e a do G0 do corte (e a do scope_check do kit do PLAN-198):
    QUALQUER PLAN-NNN citado num assunto da faixa entra, inclusive planos
    abandonados ou que so aparecem num commit de fechamento. Um conjunto VAZIO
    de ADRs e legitimo e e escrito como «none». Um conjunto vazio de PLANOS
    nao e: a faixa estaria errada. E o plano desta release tem de estar no trem
    ANTES dos materiais (idempotencia do commit deles).
    """
    log = run(repo, "log", "--format=%s", "%s..HEAD" % BASE_SHA)
    plans = sorted(set(re.findall(r"PLAN-\d{3}", log)))
    names = run(repo, "diff", "--name-only", "%s..HEAD" % BASE_SHA,
                "--", ".claude/adr/")
    adrs = sorted(set(re.findall(r"ADR-\d{3}", names)))
    if not plans:
        die("nenhum PLAN-NNN na faixa %s..HEAD — faixa errada?" % BASE_TAG)
    if OWN_PLAN not in plans:
        die("%s ausente dos assuntos de %s..HEAD: o commit dos materiais (que o "
            "cita) mudaria o escopo derivado. Lande antes os lands da %s que "
            "citam %s." % (OWN_PLAN, BASE_TAG, TARGET_BASE, OWN_PLAN))
    falta = [p for p in REQUIRED_PLANS if p not in plans]
    if falta:
        die("o escopo derivado de %s..HEAD nao contem %s (PLAN-198 exige %s)"
            % (BASE_TAG, ", ".join(falta), ", ".join(REQUIRED_PLANS)))
    return plans, adrs


def scope_string(plans: List[str], adrs: List[str]) -> str:
    # Os ADRs sao LISTADOS, nunca escritos como faixa `primeiro -> ultimo`.
    return "%s (ADRs touched: %s)" % (
        " / ".join(plans), " ".join(adrs) if adrs else "none")


def derive_counts(repo: pathlib.Path) -> Dict[str, int]:
    """Contagens VIVAS pelo mesmo oraculo que o gate usa."""
    proc = subprocess.run(
        ["bash", ".claude/scripts/local/verify-counts.sh", "--json",
         "--no-tests"],
        cwd=str(repo), stdout=subprocess.PIPE, stderr=subprocess.PIPE,
        universal_newlines=True)
    # o produtor tem de sair rc 0 e o JSON tem de ter os campos obrigatorios com
    # os tipos certos: nenhum campo ausente vira lista vazia ou contagem padrao
    if proc.returncode != 0:
        die("verify-counts --json saiu rc=%d (exigido: 0): %r"
            % (proc.returncode, (proc.stderr or proc.stdout)[-400:]))
    try:
        d = json.loads(proc.stdout)
    except Exception:
        die("verify-counts --json ilegivel: %r" % proc.stdout[:400])
    if not isinstance(d, dict):
        die("verify-counts --json nao e um objeto")
    viol = d.get("violations")
    if "violations" not in d or not isinstance(viol, list):
        die("verify-counts --json sem o campo violations como lista")
    if viol:
        die("verify-counts reporta %d drift(s) — corrija ANTES da cerimonia:\n  %s"
            % (len(viol), "\n  ".join(str(v) for v in viol[:6])))
    live = d.get("live")
    if not isinstance(live, dict):
        die("verify-counts --json sem o campo live como objeto")
    out = {}
    for k in ("skills", "commands", "adrs", "lib"):
        v = live.get(k)
        if not isinstance(v, int) or isinstance(v, bool) or v < 0:
            die("verify-counts sem contagem inteira nao negativa para %r" % k)
        out[k] = v
    return out


# --------------------------------------------------------------------------
# ancoras: utilitarios
# --------------------------------------------------------------------------
def _read_json(repo: pathlib.Path, rel: str) -> Tuple[Optional[dict], str]:
    p = repo / rel
    if p.is_symlink() or not p.is_file():
        return None, "%s ausente ou nao-regular" % rel
    try:
        d = json.loads(p.read_text(encoding="utf-8"))
    except Exception as exc:
        return None, "%s ilegivel (%s)" % (rel, type(exc).__name__)
    if not isinstance(d, dict):
        return None, "%s nao e um objeto JSON" % rel
    return d, ""


def _read_text(repo: pathlib.Path, rel: str) -> Optional[str]:
    p = repo / rel
    if p.is_symlink() or not p.is_file():
        return None
    try:
        return p.read_text(encoding="utf-8")
    except Exception:
        return None


def _need_text(repo: pathlib.Path, rel: str, bad: List[str]) -> str:
    """O texto de um arquivo que TEM de existir: ausente ou ilegivel e um achado
    (uma ancora de AUSENCIA nunca passa porque o arquivo sumiu)."""
    t = _read_text(repo, rel)
    if t is None:
        bad.append("%s ausente, nao-regular ou ilegivel" % rel)
        return ""
    return t


def _ancestor(repo: pathlib.Path, commit: str, bad: List[str], what: str) -> None:
    rc = git_rc(repo, "merge-base", "--is-ancestor", commit, "HEAD")
    if rc == 1:
        bad.append("%s (%s) nao e ancestral do HEAD" % (commit[:12], what))
    elif rc != 0:
        bad.append("%s (%s) ausente do repositorio (rc=%d)" % (commit[:12], what, rc))


def _probe_env(tmp: pathlib.Path) -> Dict[str, str]:
    """Ambiente de subprocesso que nao alcanca o HOME, o projeto, a cadeia de
    auditoria nem o TMPDIR reais: nada de CLAUDE_*, CEO_* ou PYTHONPATH
    herdado (o que tira CEO_SOTA_DISABLE, CLAUDE_PROJECT_DIR e
    CLAUDE_PROJECT_DIR_NATIVE, como o clean_run da hard-w7a), HOME e TMPDIR
    num diretorio da propria sonda (que ela varre junto)."""
    env = {k: v for k, v in os.environ.items()
           if not k.startswith(("CLAUDE_", "CEO_")) and k != "PYTHONPATH"}
    env["HOME"] = str(tmp / "home")
    env["PYTHONDONTWRITEBYTECODE"] = "1"
    env["TMPDIR"] = str(tmp / "tmpdir")
    return env


def _python_probe(repo: pathlib.Path, prefix: str, prog: List[str], args: List[str],
                  entrada: str = "", timeout: int = 180) -> Tuple[int, str, str]:
    """Roda `python3 -I -B <prog> args...` (prog = ["-c", codigo] ou [script]) com
    cwd na raiz, no ambiente da sonda (HOME e TMPDIR proprios, varridos ao fim):
    (rc, stdout, stderr)."""
    tmp = pathlib.Path(tempfile.mkdtemp(prefix=prefix))
    try:
        for sub in ("home", "tmpdir"):
            (tmp / sub).mkdir()
        try:
            proc = subprocess.run(
                [sys.executable, "-I", "-B"] + prog + args, cwd=str(repo),
                env=_probe_env(tmp), input=entrada, stdout=subprocess.PIPE,
                stderr=subprocess.PIPE, universal_newlines=True, timeout=timeout)
        except subprocess.TimeoutExpired:
            return 124, "", "a sonda passou de %d s" % timeout
        return proc.returncode, proc.stdout, proc.stderr
    finally:
        shutil.rmtree(str(tmp), ignore_errors=True)


def _floor_probe(repo: pathlib.Path, rel: str) -> List[str]:
    """Roda a funcao do piso do Claude Code de ``rel`` contra um claude FALSO.

    Extrai o bloco entre os marcadores, roda-o num bash proprio com PATH so
    com o diretorio do claude falso e o do bash/grep/head, e confere: abaixo
    do piso recusa (rc 1) por ordem NUMERICA (2.1.99 < 2.1.280); no piso e
    acima passa; com a flag de override passa avisando; sem claude no PATH e
    sem versao legivel passa avisando. E a chamada no nivel de topo do
    script sai 6 na recusa."""
    bad: List[str] = []
    text = _read_text(repo, rel)
    if text is None:
        return ["%s ausente" % rel]
    b = list(re.finditer(CC_FLOOR_BEGIN_RX, text))
    e = list(re.finditer(CC_FLOOR_END_RX, text))
    if len(b) != 1 or len(e) != 1 or e[0].start() < b[0].end():
        return ["%s: bloco do piso do Claude Code ausente ou nao unico" % rel]
    block = text[b[0].end():e[0].start()]
    if not re.search(r'(?m)^CC_FLOOR_VERSION="%s"$' % re.escape(CC_MIN), block):
        bad.append('%s: CC_FLOOR_VERSION != "%s"' % (rel, CC_MIN))
    if CC_FLOOR_OVERRIDE not in text:
        bad.append("%s sem a flag %s" % (rel, CC_FLOOR_OVERRIDE))
    if not re.search(r"(?m)^if ! %s [^\n]*; then\n[ \t]+exit %s\n"
                     % (re.escape(CC_FLOOR_FN), CC_FLOOR_EXIT), text[e[0].end():]):
        bad.append("%s: a chamada de %s no nivel de topo nao sai %s na recusa"
                   % (rel, CC_FLOOR_FN, CC_FLOOR_EXIT))
    tools = sorted({os.path.dirname(p) for p in (shutil.which("grep"), shutil.which("head"),
                                                  shutil.which("sleep"))
                    if p})
    bash = shutil.which("bash") or "/bin/bash"
    tmp = pathlib.Path(tempfile.mkdtemp(prefix="relmeta144-ccfloor."))
    try:
        (tmp / "bin").mkdir()
        harness = tmp / "floor.sh"
        harness.write_text(block + '\n%s "$1" "$2"\n' % CC_FLOOR_FN, encoding="utf-8")
        # o claude que NAO termina: o mesmo bloco, com o limite da sonda em 1 s
        # (o valor de producao e do bloco; aqui so a forma da parada e provada)
        harness_hang = tmp / "floor-hang.sh"
        harness_hang.write_text(block + '\nCC_FLOOR_PROBE_SECONDS=1\n%s "$1" "$2"\n'
                                % CC_FLOOR_FN, encoding="utf-8")
        claude = tmp / "bin" / "claude"
        hang = "#!/bin/sh\nexec sleep 60\n"
        # (saida do claude falso, override, dry-run, rc esperado, aviso
        #  esperado); o dry-run abaixo do piso passa NOMEANDO a recusa; uma
        #  versao com sufixo colado aos tres numeros conta como abaixo do piso
        #  (mesmo acima dele); so a linha que nomeia (Claude Code) e lida; um
        #  --version que nao termina e parado e so avisa
        cases = (("2.1.279 (Claude Code)", "0", "0", 1, False),
                 ("2.1.99 (Claude Code)", "0", "0", 1, False),
                 ("%s (Claude Code)" % CC_MIN, "0", "0", 0, False),
                 ("2.2.0 (Claude Code)", "0", "0", 0, False),
                 ("2.2.0-beta.1 (Claude Code)", "0", "0", 1, False),
                 ("%s-rc.1 (Claude Code)" % CC_MIN, "0", "0", 1, False),
                 ("other-tool 9.9.9\n2.1.279 (Claude Code)", "0", "0", 1, False),
                 ("2.1.279 (Claude Code)", "1", "0", 0, True),
                 ("2.1.279 (Claude Code)", "0", "1", 0, False),
                 ("sem numero de versao", "0", "0", 0, True),
                 (hang, "0", "0", 0, True),
                 (None, "0", "0", 0, True))
        for ver, allow, dry, want_rc, want_warn in cases:
            script = harness
            if ver is None:
                if claude.exists():
                    claude.unlink()
            elif ver == hang:
                claude.write_text(hang, encoding="utf-8")
                claude.chmod(0o755)
                script = harness_hang
            else:
                claude.write_text("#!/bin/sh\ncat <<'EOF_VER'\n%s\nEOF_VER\n" % ver,
                                  encoding="utf-8")
                claude.chmod(0o755)
            env = {"PATH": ":".join([str(tmp / "bin")] + tools), "HOME": str(tmp),
                   "LC_ALL": "C"}
            t0 = time.time()
            try:
                proc = subprocess.run([bash, str(script), allow, dry], env=env,
                                      stdout=subprocess.PIPE, stderr=subprocess.PIPE,
                                      universal_newlines=True, timeout=30)
            except subprocess.TimeoutExpired:
                bad.append("%s: claude %r: a funcao do piso passou de 30 s" % (rel, ver))
                continue
            took = time.time() - t0
            warned = "WARNING" in proc.stderr
            what = "que nao termina" if ver == hang else repr(ver)
            if proc.returncode != want_rc or warned != want_warn:
                bad.append("%s: claude %s override=%s dry-run=%s -> rc=%d aviso=%s (esperado "
                           "rc=%d aviso=%s)" % (rel, what, allow, dry, proc.returncode, warned,
                                                 want_rc, want_warn))
            elif dry == "1" and not re.search(r"(?i)refuse", proc.stderr):
                bad.append("%s: dry-run abaixo do piso nao nomeia a recusa" % rel)
            elif ver == hang and (took > 15 or "did not finish" not in proc.stderr):
                bad.append("%s: claude que nao termina: %.1f s, aviso %r (esperado: parado "
                           "pelo limite, aviso nomeando)" % (rel, took, proc.stderr.strip()[-160:]))
    finally:
        shutil.rmtree(str(tmp), ignore_errors=True)
    return bad


def _floor_block(text: str) -> Optional[str]:
    b = list(re.finditer(CC_FLOOR_BEGIN_RX, text))
    e = list(re.finditer(CC_FLOOR_END_RX, text))
    if len(b) != 1 or len(e) != 1 or e[0].start() < b[0].end():
        return None
    return text[b[0].start():e[0].end()]


def _semver(v: str) -> Tuple[int, int, int]:
    m = re.fullmatch(r"(\d+)\.(\d+)\.(\d+)", v.strip())
    if not m:
        raise ValueError(v)
    return int(m.group(1)), int(m.group(2)), int(m.group(3))


def _norm(text: str) -> str:
    """Espaco em branco normalizado: a quebra de linha do markdown nao conta."""
    return " ".join(text.split())


def _phrases(secs: Dict[str, str], version: str, phrases: Tuple[str, ...]) -> List[str]:
    flat = _norm(secs.get(version, ""))
    return ["a secao [%s] do CHANGELOG nao diz %r" % (version, p)
            for p in phrases if _norm(p) not in flat]


def _changelog_sections(repo: pathlib.Path) -> Dict[str, str]:
    text = _read_text(repo, CHANGELOG) or ""
    return {v: _section(text, v) for v in (TARGET_BASE, PREV_TARGET)}


def _known_open_subsections(sec: str) -> List[str]:
    return [corpo for _cab, corpo in _known_open_headed(sec)]


def _known_open_headed(sec: str) -> List[Tuple[str, str]]:
    """(cabecalho, corpo) de cada subsecao Known-open da secao."""
    subs = []
    for ko in re.finditer(r"(?m)^###[^\n]*Known-open[^\n]*\n", sec):
        tail = sec[ko.end():]
        nxt = re.search(r"(?m)^#{2,3} ", tail)
        subs.append((ko.group(0).strip(), tail[: nxt.start()] if nxt else tail))
    return subs


# versao com ou sem o prefixo v: «v1.4.5» tambem e promessa
_LATER_RX = re.compile(r"(?<![\d.])v?(\d+\.\d+\.\d+)\b")
# Versoes de ferramentas EXTERNAS que a [1.4.4] e a headline citam, declaradas
# uma a uma: qualquer outra versao posterior a TARGET_BASE, em QUALQUER major e
# com ou sem o prefixo v, e tratada como versao do framework (promessa).
EXTERNAL_VERSIONS = {
    "2.1.280": "Claude Code",
    "11.20.0": "npm",
}


def _later_framework_versions(text: str) -> List[str]:
    """Versoes posteriores a TARGET_BASE, em QUALQUER major, fora da tabela
    EXTERNAL_VERSIONS de ferramentas externas declaradas."""
    tgt = _semver(TARGET_BASE)
    return sorted({v for v in _LATER_RX.findall(text)
                   if _semver(v) > tgt and v not in EXTERNAL_VERSIONS})


def _annex_problem(sec: str) -> Optional[str]:
    """A re-declaracao do anexo da v1.4.0 na entrada desta release: None se
    ela esta la, sem release atribuida e sem prometer versao posterior."""
    if not sec:
        return "o CHANGELOG nao tem a entrada [%s]" % TARGET_BASE
    subs = _known_open_subsections(sec)
    if not subs:
        return ("a entrada [%s] do CHANGELOG nao tem subsecao Known-open (a re-declaracao "
                "do anexo da v1.4.0 mora nela)" % TARGET_BASE)
    annex = [s for s in subs if re.search(r"(?i)\bannex", s) and "1.4.0" in s]
    if not annex:
        return "nenhuma subsecao Known-open da [%s] re-declara o anexo da v1.4.0" % TARGET_BASE
    kosec = annex[0]
    # o paragrafo DESTA entrada, nao a frase historica: um item que cita a entrada
    # de outra release («the `[1.4.2]` entry declared …») nao conta
    itens = re.split(r"\n\s*- ", "\n" + kosec)
    norel = re.compile(r"(?i)\bno\s+release\s+(?:is\s+)?assigned\b|\bnot\s+assigned\s+to\s+"
                       r"(?:a|any)\s+release\b|\bunassigned\b")
    if not any(norel.search(i) and not re.search(r"\[\d+\.\d+\.\d+\]", i) for i in itens):
        return ("a subsecao Known-open da [%s] que re-declara o anexo da v1.4.0 nao diz, num "
                "item proprio (que nao cite a entrada de outra release), que nenhuma release esta "
                "atribuida a cura (PLAN-193 OQ-3)" % TARGET_BASE)
    # pela FORMA: re-declarar sem prometer = nenhuma versao posterior a esta,
    # em qualquer major e com ou sem o prefixo v, fora de frase de ferramenta externa
    later = _later_framework_versions(kosec)
    if later:
        return ("a subsecao Known-open da [%s] que re-declara o anexo nomeia versao "
                "posterior do framework (%s) — o plano nao carrega essa cura"
                % (TARGET_BASE, ", ".join(later)))
    return None


def headline_paragraphs() -> List[str]:
    return [p for p in RELEASE_HEADLINE.split("\n\n") if p.strip()]


def paragraph_links_problem(sec: str) -> List[str]:
    """Um paragrafo da headline por frase de PARAGRAPH_LINKS, cada frase na [1.4.4]."""
    bad: List[str] = []
    n = len(headline_paragraphs())
    if n != len(PARAGRAPH_LINKS):
        bad.append("a headline tem %d paragrafo(s) e PARAGRAPH_LINKS %d" % (n, len(PARAGRAPH_LINKS)))
    flat = _norm(sec)
    for k, p in enumerate(PARAGRAPH_LINKS, 1):
        if _norm(p) not in flat:
            bad.append("paragrafo %d da headline: a secao [%s] nao diz %r" % (k, TARGET_BASE, p))
    return bad


def _calls_named(fn: ast.AST, attr: str) -> List[ast.Call]:
    return [n for n in ast.walk(fn) if isinstance(n, ast.Call)
            and isinstance(n.func, ast.Attribute) and n.func.attr == attr]


def _is_filelock_lock(item: ast.withitem) -> bool:
    """`FileLock(paths["lock"], ...)` como item de um `with`."""
    c = item.context_expr
    if not (isinstance(c, ast.Call) and isinstance(c.func, ast.Name) and c.func.id == "FileLock"
            and c.args):
        return False
    a = c.args[0]
    if not (isinstance(a, ast.Subscript) and isinstance(a.value, ast.Name) and a.value.id == "paths"):
        return False
    sl = a.slice
    if isinstance(sl, ast.Index):  # Python 3.8 e anterior
        sl = sl.value  # type: ignore[attr-defined]
    return isinstance(sl, ast.Constant) and sl.value == "lock"


def _module_tuple(src: str, name: str) -> Optional[List[str]]:
    """O valor de uma atribuicao de modulo `name = ("a", "b", ...)` (com ou sem
    anotacao), ou None se ela nao existe ou nao e uma tupla de strings."""
    try:
        tree = ast.parse(src)
    except SyntaxError:
        return None
    for node in tree.body:
        alvo = node.target if isinstance(node, ast.AnnAssign) else (
            node.targets[0] if isinstance(node, ast.Assign) and len(node.targets) == 1 else None)
        if isinstance(alvo, ast.Name) and alvo.id == name and isinstance(
                getattr(node, "value", None), ast.Tuple):
            vals = [e.value for e in node.value.elts  # type: ignore[union-attr]
                    if isinstance(e, ast.Constant) and isinstance(e.value, str)]
            return vals
    return None


# --------------------------------------------------------------------------
# ancoras: uma por frase da headline; CODIGO e TEXTO em separado
# --------------------------------------------------------------------------
def code_train(repo: pathlib.Path) -> List[str]:
    bad: List[str] = []
    _ancestor(repo, RC1_SHA, bad, "commit da v1.4.3-rc.1")
    yml = _need_text(repo, NPM_PUBLISH_YML, bad)
    if yml and not any(ln.strip() == NPM_RC_SKIP for ln in yml.splitlines()):
        bad.append("%s sem a linha %s (o workflow do npm pula as tags -rc.)" % (NPM_PUBLISH_YML, NPM_RC_SKIP))
    return bad


def text_train(secs: Dict[str, str]) -> List[str]:
    return _phrases(secs, TARGET_BASE, (
        "**v1.4.3 never reached npm.**",
        "Only `v1.4.3-rc.1` was tagged",
        "The npm workflow does not publish an rc tag",
        "This entry covers the whole train since v1.4.2: everything in `[1.4.3]` is part of this "
        "release"))


def code_ccfloor(repo: pathlib.Path) -> List[str]:
    bad: List[str] = []
    for rel in (INSTALL_SH, UPGRADE_SH):
        bad.extend(_floor_probe(repo, rel))
        # «inalterado»: o bloco do piso e byte a byte o da v1.4.2
        now = _floor_block(_read_text(repo, rel) or "")
        then = _floor_block(run(repo, "show", "%s:%s" % (BASE_SHA, rel)))
        if now is None or then is None or now != then:
            bad.append("%s: o bloco do piso difere do da v%s (ou falta)" % (rel, RANGE_BASE))
    sup = _need_text(repo, SUPPORT_MD, bad)
    if sup and not any(CC_MIN in ln and "Claude Code" in ln for ln in sup.splitlines()):
        bad.append("%s sem linha que cite Claude Code %s" % (SUPPORT_MD, CC_MIN))
    pkg, why = _read_json(repo, NPM_PACKAGE)
    if pkg is None:
        bad.append(why)
    elif (pkg.get("engines") or {}).get("node") != ">=20":
        bad.append("%s: engines.node=%r (esperado >=20)"
                   % (NPM_PACKAGE, (pkg.get("engines") or {}).get("node")))
    return bad


def text_ccfloor(secs: Dict[str, str]) -> List[str]:
    return _phrases(secs, TARGET_BASE, (
        "The requirements do not change from v1.4.2: Claude Code 2.1.280 or later, Python 3.9 or "
        "later, and Node.js 20 or later for the npm shim.",)) + _phrases(secs, PREV_TARGET, (
            "Install and upgrade refuse an older `claude` on `PATH` with exit 6, unless you pass "
            "`--allow-old-claude-code`.",))


# a frase da [1.4.4] que liga cada ancora herdada ao trem desta release
LINK_143 = "everything in `[1.4.3]` is part of this release"


def _inherited(secs: Dict[str, str], phrases: Tuple[str, ...]) -> List[str]:
    return _phrases(secs, PREV_TARGET, phrases) + _phrases(secs, TARGET_BASE, (LINK_143,))


def _harness_gate_probe(repo: pathlib.Path) -> List[str]:
    """O gate no modo do CI, na raiz, no ambiente do clean_run da hard-w7a."""
    tmp = pathlib.Path(tempfile.mkdtemp(prefix="relmeta144-harness."))
    try:
        for sub in ("home", "tmpdir"):
            (tmp / sub).mkdir()
        try:
            proc = subprocess.run(
                [sys.executable, "-B", HARNESS_HOOK], cwd=str(repo), env=_probe_env(tmp),
                stdin=subprocess.DEVNULL, stdout=subprocess.PIPE, stderr=subprocess.STDOUT,
                universal_newlines=True, timeout=180)
        except subprocess.TimeoutExpired:
            return ["o gate do harness passou de 180 s"]
        lines = [ln for ln in proc.stdout.splitlines() if ln.strip()]
        last = lines[-1] if lines else ""
        if proc.returncode != 0 or not last.startswith(HARNESS_GATE_PREFIX):
            return ["o gate do harness na raiz saiu rc=%d, ultima linha %r"
                    % (proc.returncode, last[-200:])]
        return []
    finally:
        shutil.rmtree(str(tmp), ignore_errors=True)


def code_harness(repo: pathlib.Path) -> List[str]:
    bad: List[str] = []
    src = _need_text(repo, HARNESS_HOOK, bad)
    for name, val in (("REPLAY_FIXTURES_REL", HARNESS_DIR),
                      ("FIXTURE_PROJECT_PLACEHOLDER", HARNESS_PLACEHOLDER)):
        got = re.findall(r'(?m)^%s = "([^"\n]*)"$' % name, src)
        if got != [val]:
            bad.append("%s: %s=%r (esperado [%r])" % (HARNESS_HOOK, name, got, val))
    d = repo / HARNESS_DIR
    if d.is_symlink() or not d.is_dir():
        bad.append("%s ausente" % HARNESS_DIR)
    else:
        names = set(p.name for p in d.iterdir())
        if names != HARNESS_FIXTURES:
            bad.append("%s contem %s (esperado exatamente os 3 .json, sem __init__.py)"
                       % (HARNESS_DIR, sorted(names)))
    if os.path.lexists(str(repo / HARNESS_OLD_DIR)):
        bad.append("%s ainda existe" % HARNESS_OLD_DIR)
    hist = _need_text(repo, HIST_SCRIPT, bad)
    groups = re.findall(r'(?m)^HIST_GROUPS="([^"\n]*)"$', hist)
    if len(groups) != 1 or not all(g in groups[0].split() for g in HIST_GROUPS_NEW):
        bad.append("%s: HIST_GROUPS sem os grupos %s" % (HIST_SCRIPT, ", ".join(HIST_GROUPS_NEW)))
    yml = _need_text(repo, SMOKE_YML, bad)
    if yml and not re.search(r"(?m)^\s+.*python3 scripts/tests/historical-parallel\.py\b", yml):
        bad.append("%s nao roda scripts/tests/historical-parallel.py" % SMOKE_YML)
    for c, what in zip(HARNESS_COMMITS, ("land do C9", "SIGN da W7a")):
        _ancestor(repo, c, bad, what)
    if not bad:
        bad.extend(_user_deny_gap(repo)[0])
    if not bad:
        bad.extend(_harness_gate_probe(repo))
    return bad


def _user_deny_gap(repo: pathlib.Path) -> Tuple[List[str], List[str]]:
    """O residuo da cerimonia user, preso ao codigo: as entradas do DENY_BASELINE
    do gate que o deny da instalacao user (DENY_BASELINE_ENTRIES do install.sh;
    o template user nao traz bloco permissions) nao tem. Devolve (achados, falta);
    achado se a falta nao e EXATAMENTE a que a [1.4.3] declara."""
    bad: List[str] = []
    src = _need_text(repo, HARNESS_HOOK, bad)
    gate: List[str] = []
    try:
        for node in ast.parse(src).body if src else []:
            alvo = node.target if isinstance(node, ast.AnnAssign) else (
                node.targets[0] if isinstance(node, ast.Assign) and len(node.targets) == 1 else None)
            if isinstance(alvo, ast.Name) and alvo.id == "DENY_BASELINE" and node.value is not None:
                gate = [e.value for e in getattr(node.value, "elts", [])
                        if isinstance(e, ast.Constant) and isinstance(e.value, str)]
    except SyntaxError as exc:
        return ["%s nao parseia (%s)" % (HARNESS_HOOK, exc)], []
    inst = _need_text(repo, INSTALL_SH, bad)
    m = re.findall(r"(?ms)^DENY_BASELINE_ENTRIES=\(\n(.*?)^\)$", inst)
    if not gate or len(m) != 1:
        bad.append("DENY_BASELINE do gate ou DENY_BASELINE_ENTRIES do install.sh ilegivel")
        return bad, []
    entradas = re.findall(r'(?m)^\s*"([^"\n]*)"\s*$', m[0])
    tpl, why = _read_json(repo, USER_TEMPLATE)
    if tpl is None:
        bad.append(why)
    elif "permissions" in tpl:
        bad.append("%s passou a trazer um bloco permissions" % USER_TEMPLATE)
    falta = [g for g in gate if g not in entradas]
    if sorted(falta) != sorted(USER_DENY_GAP):
        bad.append("o deny da instalacao user nao cobre %s (a [%s] declara exatamente %s)"
                   % (falta, PREV_TARGET, list(USER_DENY_GAP)))
    return bad, falta


def text_harness(secs: Dict[str, str]) -> List[str]:
    sec = secs.get(PREV_TARGET, "")
    bad = _inherited(secs, (
        "With the default ceremony (`maintainer`) it now turns green, both on an install "
        "upgraded from v1.4.2 with `upgrade.sh` and on a fresh install",
        "tests in CI prove both cases for one install shape",
        "A `--ceremony user` install is not covered (Known-open below).",
        "The green above is claimed for the default ceremony (`maintainer`) only",
        "The green is claimed for the default ceremony (`maintainer`) only. The gate's "
        "`deny_baseline` check requires, in a settings file that declares `permissions`, "
        "four deny entries",
        "and a `--ceremony user` install does not write them.",
        "This gap predates this release, and no release is assigned to its cure.",
        "The upgrade does not cover a `--ceremony user` install",
        "All three reads refuse `NaN` and `Infinity`"))
    for e in USER_DENY_GAP:
        if "`%s`" % e not in sec:
            bad.append("a secao [%s] nao nomeia a entrada de deny `%s`" % (PREV_TARGET, e))
    return bad


def cond67_ast(src: str) -> List[str]:
    """Por AST: em append_entry, a leitura do elo (read_prev_hmac), a escrita da
    linha (uma chamada .write) e a atualizacao do sidecar (write_last_hmac) estao
    TODAS dentro de UM MESMO `with FileLock(paths["lock"], ...)`. Duas travas
    separadas (ler sob uma, gravar sob outra) e a forma da corrida e reprovam."""
    bad: List[str] = []
    try:
        tree = ast.parse(src)
    except SyntaxError as exc:
        return ["%s nao parseia (%s)" % (AUDIT_LOG_WRITER, exc)]
    fns = [n for n in ast.walk(tree) if isinstance(n, ast.FunctionDef) and n.name == "append_entry"]
    if len(fns) != 1:
        return ["%s: %d funcoes append_entry (exigido: 1)" % (AUDIT_LOG_WRITER, len(fns))]
    fn = fns[0]
    locks = [w for w in ast.walk(fn) if isinstance(w, ast.With)
             and any(_is_filelock_lock(i) for i in w.items)]

    def dentro(w: ast.With) -> set:
        ids = set()
        for stmt in w.body:
            ids.update(id(n) for n in ast.walk(stmt))
        return ids

    inside = set()
    for w in locks:
        inside |= dentro(w)
    partes = {a: _calls_named(fn, a) for a in ("read_prev_hmac", "write_last_hmac", "write")}
    for attr in ("read_prev_hmac", "write_last_hmac"):
        if not partes[attr]:
            bad.append("append_entry sem chamada a %s" % attr)
        out = [c.lineno for c in partes[attr] if id(c) not in inside]
        if out:
            bad.append("append_entry chama %s FORA do with FileLock(paths[\"lock\"]) "
                       "(linha(s) %s)" % (attr, ", ".join(str(x) for x in out)))
    if not partes["write"]:
        bad.append("append_entry sem a escrita da linha (chamada .write)")
    if not bad:
        juntos = [w for w in locks
                  if all(id(c) in dentro(w) for a in ("read_prev_hmac", "write_last_hmac")
                         for c in partes[a])
                  and any(id(c) in dentro(w) for c in partes["write"])]
        if not juntos:
            bad.append("append_entry nao le o elo, grava a linha e atualiza o sidecar num MESMO "
                       "with FileLock(paths[\"lock\"]) (%d bloco(s) de trava)" % len(locks))
    return bad


def code_cond67(repo: pathlib.Path) -> List[str]:
    """O gravador do agent_spawn hoje: a fachada audit_log.py executa as partes
    de _lib/_audit_log_parts/ (tupla _PARTS), e o UNICO append_entry delas mora
    em rotation_storage.py; a fachada nao define outro."""
    bad: List[str] = []
    facade = _need_text(repo, AUDIT_LOG, bad)
    if facade:
        parts = _module_tuple(facade, "_PARTS")
        if parts is None or AUDIT_LOG_WRITER_PART not in parts:
            bad.append("%s sem _PARTS que inclua %r" % (AUDIT_LOG, AUDIT_LOG_WRITER_PART))
        if "_audit_log_parts" not in facade:
            bad.append("%s nao executa as partes de %s" % (AUDIT_LOG, AUDIT_LOG_PARTS))
        try:
            ftree = ast.parse(facade)
            if any(isinstance(n, ast.FunctionDef) and n.name == "append_entry"
                   for n in ast.walk(ftree)):
                bad.append("%s ainda define append_entry" % AUDIT_LOG)
        except SyntaxError as exc:
            bad.append("%s nao parseia (%s)" % (AUDIT_LOG, exc))
    d = repo / AUDIT_LOG_PARTS
    if d.is_symlink() or not d.is_dir():
        bad.append("%s ausente" % AUDIT_LOG_PARTS)
    else:
        onde = []
        for p in sorted(d.glob("*.py")):
            try:
                t = ast.parse(p.read_text(encoding="utf-8"))
            except (SyntaxError, UnicodeDecodeError, OSError) as exc:
                bad.append("%s ilegivel (%s)" % (p.name, type(exc).__name__))
                continue
            n = sum(1 for x in ast.walk(t) if isinstance(x, ast.FunctionDef) and x.name == "append_entry")
            onde.extend([p.name] * n)
        if onde != [AUDIT_LOG_WRITER_PART + ".py"]:
            bad.append("%s: append_entry definido em %s (exigido: so em %s.py, uma vez)"
                       % (AUDIT_LOG_PARTS, onde, AUDIT_LOG_WRITER_PART))
    src = _need_text(repo, AUDIT_LOG_WRITER, bad)
    if src:
        bad.extend(cond67_ast(src))
    for rel in (AUDITRACE_SENT, AUDITRACE_SENT + ".asc"):
        p = repo / rel
        if p.is_symlink() or not p.is_file():
            bad.append("%s ausente" % rel)
    _ancestor(repo, AUDITRACE_COMMIT, bad, "SIGN da cura da condicao 67")
    env = " ".join((_need_text(repo, V140_RC1_ENVELOPE, bad)).split())
    if env and COND67_DECL not in env:
        bad.append("%s sem a condicao 67 (%r)" % (V140_RC1_ENVELOPE, COND67_DECL[:40]))
    return bad


def text_cond67(secs: Dict[str, str]) -> List[str]:
    return _inherited(secs, (
        "This release retires signed condition 67 of v1.4.0-rc.1",
        "Breaks the race already wrote stay",
        "Writers that resolve different locks for the same log still do not exclude each other"))


def code_defaultmode(repo: pathlib.Path) -> List[str]:
    bad: List[str] = []
    src = _need_text(repo, INSTALL_SH, bad)
    if src:
        n = len(re.findall(r"(?m)^%s$" % re.escape(DEFAULT_MODE_LINE), src))
        if n != 1:
            bad.append("%s: %d linhas %s (exigido: 1) — DEFAULT_MODE_BASELINE ausente?"
                       % (INSTALL_SH, n, DEFAULT_MODE_LINE))
        for frag, what in ((DEFAULT_MODE_JQ, "a rota jq"), (DEFAULT_MODE_PY, "a rota python"),
                           (DEFAULT_MODE_SKIP, "o skip por ambiente")):
            if frag not in src:
                bad.append("%s sem %s (%s)" % (INSTALL_SH, what, frag))
    tpl, why = _read_json(repo, USER_TEMPLATE)
    if tpl is None:
        bad.append(why)
    else:
        perms = tpl.get("permissions")
        if isinstance(perms, dict) and "defaultMode" in perms:
            bad.append("%s traz permissions.defaultMode" % USER_TEMPLATE)
    a = run(repo, "rev-parse", "%s:%s" % (BASE_SHA, UPGRADE_SH)).strip()
    b = run(repo, "rev-parse", "HEAD:%s" % UPGRADE_SH).strip()
    if a != b:
        bad.append("%s mudou desde a v%s (blob %s -> %s)" % (UPGRADE_SH, RANGE_BASE, a[:12], b[:12]))
    return bad


def text_defaultmode(secs: Dict[str, str]) -> List[str]:
    return _inherited(secs, (
        "produced by that same run has no `permissions.defaultMode`",
        "A `.claude/settings.json` that existed before the install is never touched",
        "`upgrade.sh` does not change",
        "`CEO_INSTALL_SKIP_DENY_BASELINE=1` skips both the deny baseline and the `defaultMode`"))


def code_cenv(repo: pathlib.Path) -> List[str]:
    bad: List[str] = []
    src = _need_text(repo, COST_HOOK, bad)
    if src:
        try:
            tree = ast.parse(src)
        except SyntaxError as exc:
            return ["%s nao parseia (%s)" % (COST_HOOK, exc)]
        calls = [c for c in _calls_named(tree, "emit_generic")
                 if c.args and isinstance(c.args[0], ast.Constant) and c.args[0].value == COST_EVENT]
        if len(calls) != 1:
            bad.append("%s: %d chamadas emit_generic(%r) (exigido: 1)" % (COST_HOOK, len(calls), COST_EVENT))
        else:
            kws = [k.arg for k in calls[0].keywords]
            if None in kws or len(kws) != len(set(kws)) or set(kws) != COST_KWARGS:
                bad.append("%s: emit_generic(%r) com kwargs %s (esperado %s; sem action)"
                           % (COST_HOOK, COST_EVENT, sorted(str(k) for k in kws), sorted(COST_KWARGS)))
    d = repo / TEMPLATES_DIR
    tpls = sorted(p for p in d.glob("*.json") if p.is_file() and not p.is_symlink()) if d.is_dir() else []
    names = set(p.name for p in tpls)
    if not {"settings.base.json", "settings.user.json"} <= names:
        bad.append("%s sem settings.base.json e settings.user.json" % TEMPLATES_DIR)
    for p in tpls:
        if "check_cost_envelope" in p.read_text(encoding="utf-8"):
            bad.append("%s/%s registra check_cost_envelope" % (TEMPLATES_DIR, p.name))
    _ancestor(repo, CENV_COMMIT, bad, "SIGN do cenv")
    return bad


def text_cenv(secs: Dict[str, str]) -> List[str]:
    return _inherited(secs, (
        "On an install that registered the cost-envelope hook by hand, a block is now "
        "recorded in the audit log",
        "No earlier release recorded it",
        "No shipped settings template registers this hook"))


def code_fixes(repo: pathlib.Path) -> List[str]:
    """O external_wait do /ceo-boot mora hoje no pacote _lib/_ceo_boot_parts/,
    que a fachada ceo-boot.py instala."""
    bad: List[str] = []
    st = _need_text(repo, STATUS_PY, bad)
    if st and "--as-json" in st:
        bad.append("%s ainda passa --as-json" % STATUS_PY)
    sd = _need_text(repo, SUBSTRATE_DRIFT, bad)
    if sd and "COMPONENT_CHECK_ERROR" not in sd:
        bad.append("%s sem COMPONENT_CHECK_ERROR" % SUBSTRATE_DRIFT)
    boot = _need_text(repo, CEO_BOOT_PY, bad)
    if boot and CEO_BOOT_INSTALL not in boot:
        bad.append("%s nao instala %s" % (CEO_BOOT_PY, CEO_BOOT_PARTS))
    d = repo / CEO_BOOT_PARTS
    if d.is_symlink() or not d.is_dir():
        bad.append("%s ausente" % CEO_BOOT_PARTS)
    elif not any("external_wait" in (p.read_text(encoding="utf-8", errors="replace"))
                 for p in sorted(d.glob("*.py"))):
        bad.append("%s sem external_wait (plano que declara a espera)" % CEO_BOOT_PARTS)
    p = repo / AUDIT_QUERY_TEST
    if p.is_symlink() or not p.is_file():
        bad.append("%s ausente" % AUDIT_QUERY_TEST)
    return bad


def text_fixes(secs: Dict[str, str]) -> List[str]:
    hdr = "### Fixed — `audit-query.py`, `/status`, `/ceo-boot` and `check-substrate-drift.py`"
    bad = _phrases(secs, TARGET_BASE, (LINK_143,))
    if hdr not in secs.get(PREV_TARGET, "").splitlines():
        bad.append("a secao [%s] do CHANGELOG sem o cabecalho %r" % (PREV_TARGET, hdr))
    return bad


def code_guard(repo: pathlib.Path) -> List[str]:
    """A guarda de execucao indireta: ligada salvo com o interruptor em 0, e o
    acerto dela so devolve bloqueio."""
    bad: List[str] = []
    fac = _need_text(repo, BASH_SAFETY, bad)
    if fac:
        parts = _module_tuple(fac, "_PARTS")
        if parts is None or "posture_scan" not in parts:
            bad.append("%s sem _PARTS que inclua 'posture_scan'" % BASH_SAFETY)
    src = _need_text(repo, BASH_POSTURE_SCAN, bad)
    if src:
        if not re.search(r"(?m)^\s*from _lib import bash_indirect_guard as _indirect_guard$", src):
            bad.append("%s nao importa bash_indirect_guard" % BASH_POSTURE_SCAN)
        for sw in INDIRECT_SWITCHES:
            if 'get_trusted("%s")' % sw not in src:
                bad.append("%s nao le o interruptor %s" % (BASH_POSTURE_SCAN, sw))
        n = sum(1 for ln in src.splitlines() if ln.strip() == INDIRECT_GATE_LINE)
        if n != 1:
            bad.append("%s: %d linha(s) %r (exigido: 1; desligada so com o valor 0)"
                       % (BASH_POSTURE_SCAN, n, INDIRECT_GATE_LINE))
        try:
            tree = ast.parse(src)
        except SyntaxError as exc:
            return bad + ["%s nao parseia (%s)" % (BASH_POSTURE_SCAN, exc)]
        ifs = [n for n in ast.walk(tree) if isinstance(n, ast.If)
               and isinstance(n.test, ast.Compare) and isinstance(n.test.left, ast.Name)
               and n.test.left.id == "indirect_hit" and len(n.test.ops) == 1
               and isinstance(n.test.ops[0], ast.IsNot)]
        if len(ifs) != 1:
            bad.append("%s: %d ramo(s) `if indirect_hit is not None` (exigido: 1)" % (BASH_POSTURE_SCAN, len(ifs)))
        else:
            rets = [r for st in ifs[0].body for r in ast.walk(st) if isinstance(r, ast.Return)]
            ok = bool(rets)
            for r in rets:
                v = r.value
                allow = [k.value for k in getattr(v, "keywords", []) if k.arg == "allow"]
                if not (isinstance(v, ast.Call) and isinstance(v.func, ast.Name) and v.func.id == "Decision"
                        and len(allow) == 1 and isinstance(allow[0], ast.Constant) and allow[0].value is False):
                    ok = False
            if not ok:
                bad.append("%s: o ramo do acerto da guarda nao devolve so Decision(allow=False, ...)"
                           % BASH_POSTURE_SCAN)
    g = _need_text(repo, INDIRECT_GUARD, bad)
    if g and not re.search(r"(?m)^def scan\(", g):
        bad.append("%s sem def scan(" % INDIRECT_GUARD)
    p = repo / ADR_201
    if p.is_symlink() or not p.is_file():
        bad.append("%s ausente" % ADR_201)
    return bad


def text_guard(secs: Dict[str, str]) -> List[str]:
    return _phrases(secs, TARGET_BASE, (
        "A new scan in the Bash guard blocks a destructive command that is reached indirectly, on "
        "by default (PLAN-195, ADR-201).",
        "runs one bounded scan",
        "It only adds blocks; an earlier BLOCK stays BLOCK.",
        "`CEO_BASH_INDIRECT_GUARD=0` turns off the scan"))


def code_split(repo: pathlib.Path) -> List[str]:
    bad: List[str] = []
    for rel, limite in THIN_LIMITS:
        t = _need_text(repo, rel, bad)
        if t and len(t.splitlines()) > limite:
            bad.append("%s tem %d linhas (a fachada fina tem no maximo %d)" % (rel, len(t.splitlines()), limite))
    for pkg in (BASH_SAFETY_PARTS, AUDIT_EMIT_PARTS):
        d = repo / pkg
        if d.is_symlink() or not d.is_dir() or not any(d.glob("*.py")):
            bad.append("%s ausente ou sem modulos" % pkg)
    p = repo / ADR_202
    if p.is_symlink() or not p.is_file():
        bad.append("%s ausente" % ADR_202)
    return bad


def text_split(secs: Dict[str, str]) -> List[str]:
    return _phrases(secs, TARGET_BASE, (
        "Several of the largest hooks and scripts become thin entry points over modules under "
        "`.claude/hooks/_lib/` (PLAN-197, ADR-202).",
        "A hook you patched by hand must be patched again in its module."))


def code_spool(repo: pathlib.Path) -> List[str]:
    bad: List[str] = []
    sh = _need_text(repo, PYTHON_HOOK_SH, bad)
    if sh and sum(1 for ln in sh.splitlines() if ln.strip() == BOUNDED_EXIT_LINE) != 1:
        bad.append("%s sem exatamente uma linha %s" % (PYTHON_HOOK_SH, BOUNDED_EXIT_LINE))
    sw = _need_text(repo, SPOOL_WRITER, bad)
    if sw and ("CEO_HOOK_BOUNDED_EXIT" not in sw or "exit_deadline_skip" not in sw):
        bad.append("%s nao le CEO_HOOK_BOUNDED_EXIT nem grava exit_deadline_skip" % SPOOL_WRITER)
    return bad


def text_spool(secs: Dict[str, str]) -> List[str]:
    return _phrases(secs, TARGET_BASE, (
        "A registered hook no longer drains the audit spool at exit (a partial cure).",
        "The spool cure is partial"))


_KERNEL_CODE = (
    "import importlib.util, sys\n"
    "from pathlib import Path\n"
    "spec = importlib.util.spec_from_file_location('relmeta144_kernel', sys.argv[1])\n"
    "mod = importlib.util.module_from_spec(spec)\n"
    "spec.loader.exec_module(mod)\n"
    "raiz = Path(sys.argv[2])\n"
    "for linha in sys.stdin.read().splitlines():\n"
    "    sys.stdout.write('%s\\t%d\\n' % (linha, 1 if mod._is_kernel_path(str(raiz / linha), raiz) else 0))\n"
)


def _kernel_flags(repo: pathlib.Path, kernel_file: str, paths: List[str]) -> Tuple[Optional[Dict[str, int]], str]:
    """O predicado do kernel de ``kernel_file`` sobre ``paths`` (relativos a raiz),
    num processo proprio: ({caminho: 0|1}, '') ou (None, motivo)."""
    rc, out, err = _python_probe(repo, "relmeta144-kernel.", ["-c", _KERNEL_CODE],
                                 [kernel_file, str(repo)], "".join(p + "\n" for p in paths))
    linhas = out.split("\n")
    if rc != 0 or len(linhas) != len(paths) + 1 or linhas[-1] != "":
        return None, "o predicado do kernel saiu rc=%d (%s)" % (rc, err.strip()[-160:])
    flags: Dict[str, int] = {}
    for p, ln in zip(paths, linhas):
        if ln not in (p + "\t0", p + "\t1"):
            return None, "o predicado do kernel respondeu fora da forma"
        flags[p] = int(ln[-1])
    return flags, ""


def code_kernelfix(repo: pathlib.Path) -> List[str]:
    """Pelo predicado do kernel do HEAD: todo arquivo rastreado de cada pacote
    que recebeu o codigo das fachadas do kernel (e do pacote dos adaptadores
    live) e os cinco modulos planos sao caminhos do kernel."""
    bad: List[str] = []
    paths: List[str] = []
    for pkg in KERNEL_PACKAGES:
        rc, out = git_out(repo, "ls-files", "-z", "--", pkg)
        files = [f for f in out.split("\0") if f]
        if rc != 0 or not files:
            bad.append("%s ausente (nenhum arquivo rastreado)" % pkg)
        paths.extend(files)
    for rel in KERNEL_FLAT:
        if not (repo / rel).is_file():
            bad.append("%s ausente" % rel)
        paths.append(rel)
    if not bad:
        flags, why = _kernel_flags(repo, str(repo / KERNEL_HOOK), paths)
        if flags is None:
            bad.append(why)
        else:
            fora = [p for p in paths if flags[p] != 1]
            if fora:
                bad.append("%d caminho(s) fora do kernel, o primeiro %s" % (len(fora), fora[0]))
    p = repo / KERNEL_GUARD_TEST
    if p.is_symlink() or not p.is_file():
        bad.append("%s ausente" % KERNEL_GUARD_TEST)
    _ancestor(repo, KERNEL_FIX_COMMIT, bad, "commit assinado da lista do kernel")
    return bad


def text_kernelfix(secs: Dict[str, str]) -> List[str]:
    return _phrases(secs, TARGET_BASE, (
        "the preparation of this release found that the kernel's hard-deny list had not followed "
        "the code that moved out of seven kernel entry points",
        "so that code is hard-deny again",
        "The fix is a commit the maintainer signed, after review by two Claude refuters and Codex. "
        "No sentinel file covers it."))


# o defeito corrigido em 54bab3cc: uma reticencia antes de um token desloca o corte
_REDACT_CODE = (
    "import json, sys\n"
    "sys.path.insert(0, sys.argv[1])\n"
    "from _lib import secret_patterns as sp\n"
    "tok = 'ghp_' + 'Zq7' * 12\n"
    "texto = 'note\\u2026 ' + tok + ' end'\n"
    "saida, achados = sp.scan_and_redact(texto)\n"
    "sys.stdout.write(json.dumps([saida, len(achados)]))\n"
)
REDACT_WANT = ["note… [REDACTED:github_pat] end", 1]


def code_redactor(repo: pathlib.Path) -> List[str]:
    bad: List[str] = []
    rc, out, err = _python_probe(repo, "relmeta144-redact.", ["-c", _REDACT_CODE],
                                 [str(repo / ".claude/hooks")])
    try:
        got = json.loads(out) if rc == 0 else None
    except ValueError:
        got = None
    if got != REDACT_WANT:
        bad.append("scan_and_redact com uma reticencia antes do token devolveu %r (rc=%d, esperado %r)"
                   % (got if got is not None else (err.strip()[-160:] or out[-160:]), rc, REDACT_WANT))
    eg = _need_text(repo, EGRESS_REDACTOR, bad)
    if eg and "scan_and_redact" not in eg:
        bad.append("%s nao chama scan_and_redact" % EGRESS_REDACTOR)
    p = repo / REDACTOR_TEST
    if p.is_symlink() or not p.is_file():
        bad.append("%s ausente" % REDACTOR_TEST)
    _ancestor(repo, REDACTOR_FIX_COMMIT, bad, "commit assinado do redator")
    # «which the signed v1.4.0 verdict had declared as its condition 58»: o envelope
    # assinado da v1.4.0 traz a condicao 58 com o titulo do defeito dos offsets
    env = " ".join((_need_text(repo, V140_ENVELOPE, bad)).split())
    if env and COND58_DECL not in env:
        bad.append("%s sem a condicao 58 (%r)" % (V140_ENVELOPE, COND58_DECL[:40]))
    return bad


def text_redactor(secs: Dict[str, str]) -> List[str]:
    return _phrases(secs, TARGET_BASE, (
        "the secret redactor, since v1.0.0, cut the text at offsets taken from its normalized form, "
        "which the signed v1.4.0 verdict had declared as its condition 58",
        "The signed v1.4.0 verdict declared this defect as its condition 58.",
        "Its `scan()` offsets now index the text passed in",
        "The Codex and Grok egress redactor (`_lib/codex_egress_redact.py`) uses these functions.",
        "The fix is a commit the maintainer signed, after review by Codex and two Claude refuters "
        "over several rounds.",
        "is declared in Known-open. No sentinel file covers it."))


def _pr_numbers(repo: pathlib.Path, rng: str) -> Optional[List[int]]:
    rc, out = git_out(repo, "log", "--merges", "--format=%s", rng)
    if rc != 0:
        return None
    return sorted(int(m.group(1)) for m in
                  (re.match(r"^Merge pull request #(\d+) ", ln) for ln in out.splitlines()) if m)


def code_merges(repo: pathlib.Path) -> List[str]:
    """Os merges de pull request da faixa, pelos assuntos; os caminhos que os dois
    depois da rc.1 trouxeram, pelo oraculo de canonicos do HEAD e pelo predicado
    do kernel da lista como mergeada (a de 888e9e6c)."""
    bad: List[str] = []
    _ancestor(repo, RC1_SHA, bad, "commit da v1.4.3-rc.1")
    for c, n in ((PR6_SHA, 6), (PR7_SHA, 7)):
        _ancestor(repo, c, bad, "merge do pull request #%d" % n)
    if bad:
        return bad
    antes = _pr_numbers(repo, "%s..%s" % (BASE_SHA, RC1_SHA))
    depois = _pr_numbers(repo, "%s..HEAD" % RC1_SHA)
    if antes is None or len(antes) != PR_BEFORE_RC1:
        bad.append("merges de pull request em v%s..v%s-rc.1: %r (exigido: %d)"
                   % (RANGE_BASE, PREV_TARGET, antes, PR_BEFORE_RC1))
    if depois is None or tuple(depois) != PR_AFTER_RC1:
        bad.append("merges de pull request depois da v%s-rc.1: %r (exigido: %r)"
                   % (PREV_TARGET, depois, list(PR_AFTER_RC1)))
    rc, out = git_out(repo, "diff", "--name-only", "--no-renames", "%s..%s" % (RC1_SHA, PR7_SHA))
    paths = [p for p in out.splitlines() if p]
    if rc != 0 or not paths:
        return bad + ["git diff %s..%s falhou ou saiu vazio" % (RC1_SHA[:12], PR7_SHA[:12])]
    asc = [p for p in paths if p.endswith(".asc")]
    if asc:
        bad.append("os merges trouxeram %d arquivo(s) .asc, o primeiro %s" % (len(asc), asc[0]))
    rc, oout, oerr = _python_probe(repo, "relmeta144-oracle.", [CANON_ORACLE],
                                   ["--is-canonical", "-"], "".join(p + "\n" for p in paths))
    linhas = oout.split("\n")
    if rc != 0 or len(linhas) != len(paths) + 1:
        bad.append("o oraculo de canonicos saiu rc=%d ou fora da forma (%s)" % (rc, oerr.strip()[-160:]))
    else:
        canon = [p for p, ln in zip(paths, linhas) if ln == p + "\t1"]
        if len(canon) != PR_CANONICAL or any(ln not in (p + "\t0", p + "\t1") for p, ln in zip(paths, linhas)):
            bad.append("caminhos canonicos dos dois merges: %d (exigido: %d)" % (len(canon), PR_CANONICAL))
    tmp = pathlib.Path(tempfile.mkdtemp(prefix="relmeta144-kernel-merged."))
    try:
        kf = tmp / "check_arbitration_kernel.py"
        kf.write_bytes(run_bytes(repo, "show", "%s:%s" % (PR7_SHA, KERNEL_HOOK)))
        flags, why = _kernel_flags(repo, str(kf), paths)
    finally:
        shutil.rmtree(str(tmp), ignore_errors=True)
    if flags is None:
        bad.append(why)
    elif sum(flags.values()) != PR_KERNEL_AS_MERGED:
        bad.append("caminhos do kernel pela lista como mergeada: %d (exigido: %d)"
                   % (sum(flags.values()), PR_KERNEL_AS_MERGED))
    return bad


def text_merges(secs: Dict[str, str]) -> List[str]:
    return _phrases(secs, TARGET_BASE, (
        "The honest part: most of this train after v1.4.3-rc.1 reached `main` through two pull-request "
        "merges, without the signing ceremony.",
        "They changed 233 canonical paths, 15 of them kernel paths by the list as merged, and with them "
        "the meaning of three governance checks: the VETO floor, the model allowlist and the Codex pin.",
        "No signed sentinel ratifies those files as of this entry",
        "`main` has no branch protection and no ruleset (measured through the GitHub API on "
        "2026-11-03)")) + _phrases(secs, PREV_TARGET, (
            "Four GitHub pull-request merges brought framework files into `main` without the signing "
            "ceremony.",))


_MODEL_CODE = (
    "import importlib.util, json, sys\n"
    "spec = importlib.util.spec_from_file_location('relmeta144_mc', sys.argv[1])\n"
    "mod = importlib.util.module_from_spec(spec)\n"
    "spec.loader.exec_module(mod)\n"
    "pares = json.loads(sys.argv[2])\n"
    "sys.stdout.write(json.dumps([bool(getattr(mod, f)(i)) for i, f in pares]))\n"
)


def code_models(repo: pathlib.Path) -> List[str]:
    bad: List[str] = []
    if not (repo / MODEL_CURRENCY).is_file():
        return ["%s ausente" % MODEL_CURRENCY]
    pares = [[i, f] for i, f, _r in MODEL_PROBES]
    rc, out, err = _python_probe(repo, "relmeta144-models.", ["-c", _MODEL_CODE],
                                 [str(repo / MODEL_CURRENCY), json.dumps(pares)])
    try:
        got = json.loads(out) if rc == 0 else None
    except ValueError:
        got = None
    if got != [True] * len(MODEL_PROBES):
        bad.append("model_currency sobre %s devolveu %r (rc=%d; esperado todos admitidos) %s"
                   % ([i for i, _f, _r in MODEL_PROBES], got, rc, err.strip()[-120:]))
    led, why = _read_json(repo, MODEL_LEDGER)
    if led is None:
        bad.append(why)
    else:
        por_id = {m.get("model_id"): m for m in (led.get("models") or []) if isinstance(m, dict)}
        for i, _f, ret in MODEL_PROBES:
            if ret is not None and (por_id.get(i) or {}).get("retirement") != ret:
                bad.append("%s: o ledger nao lista %s com retirement %s" % (MODEL_LEDGER, i, ret))
    for rel in MODEL_CALLERS:
        t = _need_text(repo, rel, bad)
        if t and "model_currency" not in t:
            bad.append("%s nao chama model_currency" % rel)
    return bad


def text_models(secs: Dict[str, str]) -> List[str]:
    return _phrases(secs, TARGET_BASE, (
        "The model checks accept model families, among them other vendors' ids and retired ids",
        "lists as retired or retiring",
        "Now all three call `is_allowed_model` in `_lib/model_currency.py`"))


def code_codex(repo: pathlib.Path) -> List[str]:
    d, why = _read_json(repo, CODEX_MANIFEST)
    if d is None:
        return [why]
    bad: List[str] = []
    if d.get("package_version") != CODEX_VER:
        bad.append("%s: package_version=%r (esperado %s)"
                   % (CODEX_MANIFEST, d.get("package_version"), CODEX_VER))
    pays = d.get("payloads")
    if not isinstance(pays, dict) or set(pays) != CODEX_PLATFORMS or not all(
            isinstance(p, dict) and re.fullmatch(r"[0-9a-f]{64}", str(p.get("sha256", "")))
            for p in pays.values()):
        bad.append("%s: payloads != {%s} com sha256 de 64 hex"
                   % (CODEX_MANIFEST, ", ".join(sorted(CODEX_PLATFORMS))))
    txt = _read_text(repo, CODEX_PIN_TXT)
    body = [ln.strip() for ln in (txt or "").splitlines()
            if ln.strip() and not ln.lstrip().startswith("#")]
    if body != [CODEX_PIN_FLOOR_BODY]:
        bad.append("%s: corpo %r (esperado so %r, o piso sem limite superior)"
                   % (CODEX_PIN_TXT, body, CODEX_PIN_FLOOR_BODY))
    cc = _need_text(repo, CLI_CURRENCY, bad)
    if cc and re.findall(r'(?m)^CODEX_VERSION_FLOOR = "([^"\n]*)"$', cc) != [CODEX_VER]:
        bad.append('%s sem a linha unica CODEX_VERSION_FLOOR = "%s"' % (CLI_CURRENCY, CODEX_VER))
    pr = repo / PAIR_RAIL_PARTS
    if pr.is_symlink() or not pr.is_dir() or not any(
            '"version_floor_only"' in p.read_text(encoding="utf-8", errors="replace")
            for p in sorted(pr.glob("*.py"))):
        bad.append("%s sem o resultado version_floor_only" % PAIR_RAIL_PARTS)
    _ancestor(repo, CODEX_REPIN_COMMIT, bad, "SIGN do re-pin 0.160.0")
    return bad


def text_codex(secs: Dict[str, str]) -> List[str]:
    return _phrases(secs, TARGET_BASE, (
        "which pins one binary of Codex CLI 0.160.0",
        "Now a Codex CLI newer than the manifest version passes as `compatible/version_floor_only`",
        "on this route a mismatch with the manifest no longer fails",
        "the Codex pin check accepts a newer Codex CLI on a version floor, without a matching hash")
    ) + _phrases(secs, PREV_TARGET, ("for one platform only",))


def code_annex(repo: pathlib.Path) -> List[str]:
    bad: List[str] = []
    for rel in (V140_ENVELOPE, V142_RC1_ENVELOPE):
        p = repo / rel
        if p.is_symlink() or not p.is_file():
            bad.append("%s ausente" % rel)
    # acoplamento: a headline diz que o backup deixa de fora o material de chave;
    # um ceo-backup.sh que passe a citar audit-key ou .salt torna a frase suspeita
    bk = _need_text(repo, BACKUP_SH, bad)
    if re.search(r"audit-key|\.salt\b", bk):
        bad.append("%s cita audit-key ou .salt, e a headline diz que o backup os deixa de fora"
                   % BACKUP_SH)
    return bad


# o item do anexo da v1.4.0 no Known-open da [1.4.4]: as duas curas e nenhuma outra
ANNEX_CURES = (
    "v1.4.3-rc.1 retired signed condition 67, and that cure is part of this release.",
    "Signed condition 58 is the redactor offsets defect fixed above.",
    "This release does not claim the cure of any other annex condition.",
)


def text_annex(secs: Dict[str, str]) -> List[str]:
    sec = secs.get(TARGET_BASE, "")
    why = _annex_problem(sec)
    if why is not None:
        return [why]
    bad: List[str] = []
    later = _later_framework_versions(sec)
    if later:
        bad.append("a secao [%s] nomeia versao posterior do framework (%s)"
                   % (TARGET_BASE, ", ".join(later)))
    if not re.search(r"cleanupPeriodDays", sec) or not re.search(r"(?i)\bdefault\s+30\b", sec):
        bad.append("a secao [%s] nao cita cleanupPeriodDays com o padrao de 30 dias" % TARGET_BASE)
    subs = _known_open_subsections(sec)
    if not any(re.search(r"(?is)\baudit\b.{0,200}\bdelet", s) and re.search(r"(?i)\bno\s+plan\b", s)
               for s in subs):
        bad.append("nenhum Known-open da [%s] declara que a limpeza do Claude Code pode apagar "
                   "o log de auditoria sem plano de cura" % TARGET_BASE)
    if not any("**The audit spool.**" in s for s in subs):
        bad.append("nenhum Known-open da [%s] tem a subsecao do spool de auditoria" % TARGET_BASE)
    # «Of the signed v1.4.0 annex, conditions 67 and 58 are cured, and this release does
    # not claim the cure of any other annex condition»: as tres frases no item do anexo da
    # v1.4.0, e o cabecalho da subsecao dele sem «NOT cured» (contradiria as curas)
    for cab, corpo in _known_open_headed(sec):
        if not (re.search(r"(?i)\bannex", corpo) and "1.4.0" in corpo):
            continue
        if re.search(r"(?i)\bnot\s+cured\b", cab):
            bad.append("o cabecalho %r diz NOT cured sobre o anexo da v1.4.0, que nomeia as curas "
                       "das condicoes 67 e 58" % cab)
        flat = _norm(corpo)
        bad.extend("a subsecao %r nao diz %r" % (cab, f) for f in ANNEX_CURES if _norm(f) not in flat)
        break
    bad.extend(_phrases(secs, TARGET_BASE, ANNEX_CURES + (
        "This release does not claim the cure of its three P1 findings",
        "The key material (`audit-key`, `.salt`) is still not archived.",
        "Keep your own copy of `audit-key` and `.salt`, because the backup leaves them out.",
        "the new guard's false-positive limits were never measured on this implementation",
        "The ingress path redacts the raw answer text before parsing it, so a redaction can change "
        "whether an answer parses.",
        "is scheduled for the next release.",
        "There is no plan in this release with a structural cure.")))
    return bad


Claim = Tuple[str, str, Callable[[pathlib.Path], List[str]], Callable[[Dict[str, str]], List[str]], str]
CLAIMS: Tuple[Claim, ...] = (
    ("train", "a v1.4.3 nao chegou ao npm; o trem inteiro desde a v1.4.2", code_train, text_train,
     "o commit da v1.4.3-rc.1 (%s) ancestral do HEAD; o npm-publish.yml pula as tags -rc." % RC1_SHA[:8]),
    ("ccfloor", "requisitos inalterados (piso do Claude Code, Node.js do shim)", code_ccfloor,
     text_ccfloor,
     "piso %s rodado contra um claude falso no install.sh e no upgrade.sh (recusa abaixo e com "
     "sufixo colado, saida %s no topo; override, ausencia, versao ilegivel e --version parado so "
     "avisam); o bloco do piso byte a byte o da v%s nos dois; SUPPORT.md cita %s; engines.node "
     ">=20" % (CC_MIN, CC_FLOOR_EXIT, RANGE_BASE, CC_MIN)),
    ("harness", "gate do harness: fixtures num caminho entregue (herdada da [1.4.3])", code_harness,
     text_harness,
     "REPLAY_FIXTURES_REL e o marcador novos; a pasta nova so com os 3 .json; a antiga ausente; "
     "os grupos harness-* no teste historico e o smoke-install.yml rodando-o; C9 e o SIGN da W7a "
     "ancestrais; o deny da instalacao user sem exatamente as 4 entradas do DENY_BASELINE do "
     "gate que a [1.4.3] declara; o gate no modo do CI na raiz verde (HOME proprio, sem "
     "CLAUDE_*/CEO_*)"),
    ("cond67", "condicao 67: o elo lido dentro da trava (herdada, re-ancorada)", code_cond67, text_cond67,
     "a fachada audit_log.py executa as partes de _lib/_audit_log_parts/ (rotation_storage na tupla "
     "_PARTS) e nao define append_entry; o unico append_entry do pacote mora em rotation_storage.py; "
     "por AST, a leitura do elo, a escrita da linha e a atualizacao do sidecar dele num MESMO with "
     "FileLock(paths[\"lock\"]); sentinel e .asc da cura presentes, SIGN ancestral; a condicao 67 no "
     "envelope da v1.4.0-rc.1"),
    ("defaultmode", "defaultMode manual no install user (herdada)", code_defaultmode, text_defaultmode,
     "install.sh com DEFAULT_MODE_BASELINE=\"manual\" (1 linha), as rotas jq e python e o skip "
     "por ambiente; o template user sem permissions.defaultMode (JSON); upgrade.sh com o mesmo "
     "blob da v%s" % RANGE_BASE),
    ("cenv", "cost_envelope_capped gravado; nenhum template registra (herdada)", code_cenv, text_cenv,
     "por AST, uma chamada emit_generic(%r) com kwargs = %s, sem action; nenhum "
     "templates/settings/*.json registra o hook; SIGN do cenv ancestral"
     % (COST_EVENT, ", ".join(sorted(COST_KWARGS)))),
    ("fixes", "correcoes de audit-query, /status, /ceo-boot e check-substrate-drift (herdada, "
     "re-ancorada)", code_fixes, text_fixes,
     "status.py sem --as-json; check-substrate-drift.py com COMPONENT_CHECK_ERROR; ceo-boot.py "
     "instala _lib/_ceo_boot_parts/, que tem o external_wait; o teste da ordem dos flags do "
     "audit-query presente"),
    ("guard", "guarda de Bash contra execucao indireta, ligada por padrao", code_guard, text_guard,
     "check_bash_safety.py executa posture_scan (tupla _PARTS); posture_scan.py importa "
     "bash_indirect_guard, le os dois interruptores e so desliga a varredura com o valor 0; o ramo "
     "do acerto devolve so Decision(allow=False, ...); bash_indirect_guard.py define scan; ADR-201 "
     "presente"),
    ("split", "ganchos e scripts divididos em modulos", code_split, text_split,
     "check_bash_safety.py com no maximo 100 linhas e _lib/audit_emit.py com no maximo 1000; os "
     "pacotes _lib/_bash_safety_parts/ e _lib/_audit_emit_parts/ com modulos; ADR-202 presente"),
    ("spool", "um gancho registrado sai sem drenar o spool", code_spool, text_spool,
     "_python-hook.sh com uma linha export CEO_HOOK_BOUNDED_EXIT=1; spool_writer.py le a variavel "
     "e grava exit_deadline_skip"),
    ("kernelfix", "a lista do kernel cobre o codigo das fachadas do kernel", code_kernelfix,
     text_kernelfix,
     "pelo predicado do kernel do HEAD (check_arbitration_kernel._is_kernel_path, num processo "
     "proprio), todo arquivo rastreado dos 8 pacotes (os 7 que receberam o codigo das fachadas e "
     "adapters/live) e os 5 modulos planos e caminho do kernel; o teste "
     "test_kernel_decomposition_coverage.py presente; o commit %s ancestral" % KERNEL_FIX_COMMIT[:8]),
    ("redactor", "os offsets do redator indexam o texto recebido", code_redactor, text_redactor,
     "scan_and_redact, num processo proprio, sobre um texto com uma reticencia antes de um token "
     "de exemplo: a saida e o texto com so o token trocado pelo rotulo; codex_egress_redact.py "
     "chama scan_and_redact; test_secret_patterns.py presente; o commit %s ancestral; a condicao "
     "58 do envelope assinado da v1.4.0 com o titulo do defeito dos offsets"
     % REDACTOR_FIX_COMMIT[:8]),
    ("merges", "merges de pull request sem a cerimonia de assinatura", code_merges, text_merges,
     "pelos assuntos, 4 merges de pull request em v1.4.2..v1.4.3-rc.1 e os #6 e #7 depois; nos "
     "caminhos de v1.4.3-rc.1..%s, %d canonicos pelo oraculo do HEAD e %d do kernel pela lista "
     "como mergeada (a de %s), e nenhum .asc" % (PR7_SHA[:8], PR_CANONICAL, PR_KERNEL_AS_MERGED, PR7_SHA[:8])),
    ("models", "piso do VETO e allowlist de modelos por familia", code_models, text_models,
     "model_currency, num processo proprio, admite %s; o ledger lista os ids datados com a "
     "retirada; agent_frontmatter.py, escalation_signals.py e effective_config.py chamam "
     "model_currency" % ", ".join("%s (%s)" % (i, f) for i, f, _r in MODEL_PROBES)),
    ("codex", "pin do Codex: um binario por sha256, piso de versao", code_codex, text_codex,
     "o manifesto pina %s por sha256 so para %s; o corpo do pin e %s, sem limite superior; "
     "cli_currency.py com CODEX_VERSION_FLOOR = \"%s\"; _lib/_pair_rail_parts/ com o resultado "
     "version_floor_only; SIGN do re-pin ancestral"
     % (CODEX_VER, ", ".join(sorted(CODEX_PLATFORMS)), CODEX_PIN_FLOOR_BODY, CODEX_VER)),
    ("annex", "parte declarada: o que fica aberto; do anexo da v1.4.0, as condicoes 67 e 58",
     code_annex, text_annex,
     "envelopes da v1.4.0 e da v1.4.2-rc.1 presentes; ceo-backup.sh sem audit-key nem .salt (a "
     "frase «the backup leaves out the key material» segue verdadeira)"),
)

ClaimResult = Tuple[str, str, bool, str, bool, str]


def check_claims(repo: pathlib.Path) -> List[ClaimResult]:
    """(chave, nome, codigo ok, detalhe do codigo, texto ok, detalhe do texto)."""
    secs = _changelog_sections(repo)
    out: List[ClaimResult] = []
    for key, name, code_fn, text_fn, proves in CLAIMS:
        parts = []
        for fn, arg, ok_detail in ((code_fn, repo, proves),
                                   (text_fn, secs, "as frases ancoradas estao no CHANGELOG")):
            try:
                bad = fn(arg)  # type: ignore[operator]
            except Exception as exc:  # uma ancora que quebra NAO passa
                bad = ["a ancora quebrou (%s: %s)" % (type(exc).__name__, exc)]
            parts.append((not bad, "; ".join(bad) if bad else ok_detail))
        out.append((key, name, parts[0][0], parts[0][1], parts[1][0], parts[1][1]))
    links = paragraph_links_problem(secs.get(TARGET_BASE, ""))
    out.append(("paragrafos", "cada paragrafo da headline tem uma frase na [%s]" % TARGET_BASE,
                True, "sem parte de codigo (conferencia de texto)", not links,
                "; ".join(links) if links else "os %d paragrafos" % len(PARAGRAPH_LINKS)))
    return out


def assert_claims(repo: pathlib.Path) -> List[ClaimResult]:
    res = check_claims(repo)
    bad = [r for r in res if not (r[2] and r[4])]
    if bad:
        die("a headline afirma o que o HEAD nao sustenta:\n  %s\n"
            "Lande a peca que falta e re-derive. Se ela ficou de fora de proposito, a "
            "headline tem de mudar ANTES: edite RELEASE_HEADLINE e CLAIMS neste "
            "derivador, commite e re-derive."
            % "\n  ".join("[%s] %s: codigo: %s; texto: %s" % (k, n, cd, td)
                          for k, n, _c, cd, _t, td in bad))
    return res


# --------------------------------------------------------------------------
# bloco PER-RELEASE e edicoes
# --------------------------------------------------------------------------
def build_per_release_block(scope: str) -> str:
    return (
        'TARGET_BASE="%s"\n'
        'RELEASE_TITLE="%s"\n'
        '# O tag vale pelo TREM INTEIRO da entrada do CHANGELOG desta versao,\n'
        '# nunca pelo plano\n'
        '# mais novo. Este bloco e DERIVADO por\n'
        '# .claude/plans/PLAN-198/relmeta/apply-relmeta144-edits.py\n'
        '# a partir de `git log %s..HEAD` (planos CITADOS nos assuntos de\n'
        '# commit da faixa, DEPOIS de todos os lands da release) e do conjunto\n'
        '# de ADRs tocados na mesma faixa — nao digite nada aqui a mao.\n'
        'RELEASE_SCOPE="%s"\n'
        'RELEASE_HEADLINE="%s"\n'
        % (TARGET_BASE, RELEASE_TITLE, BASE_TAG, scope, RELEASE_HEADLINE)
    )


def assert_block_is_inert(block: str) -> None:
    """O bloco PER-RELEASE vira quatro strings de ASPAS DUPLAS em bash.

    Dentro delas, crase e substituicao de comando, ``$NOME`` e expansao, e uma
    aspa dupla FECHA a string. Qualquer um dos tres faria o driver executar ou
    truncar prosa que vai para a anotacao ASSINADA da tag. Titulo e headline sao
    ASCII estrito, e nenhuma linha deles comeca com # (a limpeza padrao do git
    apaga essa linha da mensagem da tag).
    """
    bad = []
    lines = block.splitlines()
    headline_at = next(
        (k for k, ln in enumerate(lines) if ln.startswith('RELEASE_HEADLINE="')),
        len(lines))
    for lineno, line in enumerate(lines, 1):
        if lineno - 1 < headline_at and line.lstrip().startswith("#"):
            continue
        if "`" in line:
            bad.append("linha %d: crase (substituicao de comando)" % lineno)
        for m in re.finditer(r"(?<!\\)\$", line):
            bad.append("linha %d, col %d: cifrao nao escapado"
                       % (lineno, m.start() + 1))
        if "\\" in line:
            bad.append("linha %d: barra invertida (escape em aspas duplas)" % lineno)
    for name, value in (("RELEASE_TITLE", RELEASE_TITLE),
                        ("RELEASE_HEADLINE", RELEASE_HEADLINE)):
        if '"' in value:
            bad.append("%s contem aspa dupla — fecharia a string do bash" % name)
        try:
            value.encode("ascii")
        except UnicodeError:
            bad.append("%s contem nao-ASCII" % name)
        for k, ln in enumerate(value.split("\n"), 1):
            if ln.lstrip().startswith("#"):
                bad.append("%s, linha %d: comeca com # (a limpeza do git a apagaria)" % (name, k))
        if re.search(r"(?i)publish|publica", value):
            bad.append("%s contem palavra de publicacao (o texto vale para a rc e o GA)" % name)
        for m in re.finditer(r"(?<![\w.])(\d+\.\d+\.\d+)", value):
            bad.append("%s: versao %s sem o prefixo v" % (name, m.group(1)))
    if "\n" in RELEASE_TITLE:
        bad.append("RELEASE_TITLE tem quebra de linha")
    if bad:
        die("bloco PER-RELEASE nao e inerte em aspas duplas:\n  %s"
            % "\n  ".join(bad))


def assert_no_bare_semver(block: str) -> None:
    """Espelha test_driver_derives_every_version_string_from_target_base."""
    rx = re.compile(r"\b\d+\.\d+\.\d+\b")
    bad = []
    for lineno, line in enumerate(block.splitlines(), 1):
        if line.strip() == 'TARGET_BASE="%s"' % TARGET_BASE:
            continue
        for hit in rx.findall(line):
            if re.search(r"v%s-rc\.\d+" % re.escape(hit), line):
                continue
            bad.append("linha %d: semver nu %s" % (lineno, hit))
    if bad:
        die("bloco PER-RELEASE com literal de versao nao derivado:\n  %s"
            % "\n  ".join(bad))


def assert_no_site_count_or_publish_claim(block: str) -> None:
    """Espelha os dois testes de prosa que leem o driver inteiro."""
    site_rx = re.compile(
        r"\b(?:one|two|three|four|five|six|seven|eight|nine|ten|"
        r"\d+(?:st|nd|rd|th)?)\s+(?:\w+\s+)?sites?\b", re.IGNORECASE)
    bad = ["linha %d: contagem de sitios" % n
           for n, ln in enumerate(block.splitlines(), 1) if site_rx.search(ln)]
    if "publishes to npm" in block:
        bad.append("'publishes to npm' fora do contexto que o teste de atribuicao exige")
    if bad:
        die("bloco PER-RELEASE reprovaria os testes de prosa do driver:\n  %s"
            % "\n  ".join(bad))


def assert_no_stale_text(block: str) -> None:
    """Nenhuma frase da release anterior e nenhuma promessa de versao futura."""
    bad = ["texto da release anterior: %r" % f for f in FORBID if f in block]
    later = _later_framework_versions(block)
    if later:
        bad.append("versao posterior do framework nomeada (%s)" % ", ".join(later))
    if bad:
        die("bloco PER-RELEASE com texto velho ou promessa:\n  %s" % "\n  ".join(bad))


def edit_release_sh(text: str, block: str) -> str:
    """Substitui o bloco PER-RELEASE inteiro, ancorado nas duas pontas."""
    start = 'TARGET_BASE="%s"\n' % PREV_TARGET
    end = '\nRC_NUM="1"\n'
    if text.count(start) != 1:
        die("ancora inicial do bloco PER-RELEASE ausente ou nao unica em %s"
            " (TARGET_BASE ja nao e %s?)" % (RELEASE_SH, PREV_TARGET))
    i = text.find(start)
    j = text.find(end, i)
    if j < 0:
        die("ancora final (RC_NUM) ausente depois do bloco PER-RELEASE")
    return text[:i] + block + text[j + 1:]


def edit_manifest(text: str, new_sha: str) -> str:
    """Re-pin do sha de release.sh no manifesto ADR-192 (linha unica)."""
    lines = text.splitlines(True)
    hits = [k for k, ln in enumerate(lines)
            if ln.rstrip("\n").endswith("  " + RELEASE_SH)]
    if len(hits) != 1:
        die("manifesto ADR-192 com %d linhas para %s (exigido: 1)"
            % (len(hits), RELEASE_SH))
    lines[hits[0]] = "%s  %s\n" % (new_sha, RELEASE_SH)
    return "".join(lines)


def _wrap_literal(scope: str, indent: str) -> str:
    """O escopo como literais adjacentes de no maximo ~70 colunas uteis."""
    words = scope.split(" ")
    chunks, cur = [], ""
    for w in words:
        cand = (cur + " " + w) if cur else w
        if len(cand) > 66 and cur:
            chunks.append(cur + " ")
            cur = w
        else:
            cur = cand
    chunks.append(cur)
    for c in chunks:
        if '"' in c or "\\" in c:
            die("escopo com aspa ou barra invertida — nao cabe num literal simples")
    return "\n".join('%s"%s"' % (indent, c) for c in chunks)


def negative_for(old_scope: str, new_block: str) -> str:
    """A assercao NEGATIVA do trem anterior: os tres primeiros planos dele, ou o
    escopo inteiro quando o prefixo tambem cabe no trem novo. Nunca uma string
    que a anotacao nova contenha (o teste reprovaria por construcao)."""
    head = old_scope.split(" (ADRs")[0]
    first_three = " / ".join(head.split(" / ")[:3])
    for cand in (first_three, old_scope):
        if cand and cand not in new_block:
            return cand
    die("nenhuma assercao negativa possivel: o trem anterior (%s) esta contido no "
        "bloco novo" % old_scope)
    return ""  # pragma: no cover


def edit_scope_test(text: str, old_scope: str, new_scope: str, new_block: str) -> str:
    """Re-pin CONSCIENTE do teste que fixa o escopo da anotacao.

    Ancora = o bloco `assert ( <literais> in proc.stdout )` que reconstitui
    EXATAMENTE o escopo anterior. O escopo anterior vira assercao NEGATIVA:
    nenhuma string da release passada pode sobreviver na anotacao.
    """
    rx = re.compile(
        r'    assert \(\n((?:        "[^"\n]*"\n?)+?) in proc\.stdout\n    \)\n')
    hits = []
    for m in rx.finditer(text):
        lit = "".join(re.findall(r'"([^"\n]*)"', m.group(1)))
        if lit == old_scope:
            hits.append(m)
    if len(hits) != 1:
        die("teste de escopo: %d blocos reconstituem o escopo anterior (exigido: 1)"
            % len(hits))
    m = hits[0]
    neg = negative_for(old_scope, new_block)
    comment = "    # o trem da release ANTERIOR nao pode ter sobrevivido na anotacao\n"
    after = text[m.end():]
    if after.startswith(comment):  # o comentario ja esta la: a negativa nova entra sob ele
        after = after[len(comment):]
    new_assert = (
        "    assert (\n%s in proc.stdout\n    )\n%s"
        "    assert \"%s\" not in proc.stdout\n"
        % (_wrap_literal(new_scope, "        "), comment, neg))
    out = text[:m.start()] + new_assert + after

    doc_old = ("    Trem %s (re-pinado na cerimonia %s, %s): derivado por\n"
               % (PREV_TARGET, PREV_RELMETA, PREV_OWN_PLAN))
    if out.count(doc_old) != 1:
        die("teste de escopo: ancora do docstring do trem anterior ausente ou nao unica")
    doc_new = (
        "    Trem %s (re-pinado na cerimonia relmeta-144, %s): derivado por\n"
        "    apply-relmeta144-edits.py de `git log %s..HEAD` DEPOIS de todos os\n"
        "    lands da release (a %s so teve a rc.1); o trem da %s vira\n"
        "    assercao negativa.\n"
        "\n" % (TARGET_BASE, OWN_PLAN, BASE_TAG, PREV_TARGET, PREV_TARGET))
    return out.replace(doc_old, doc_new + doc_old, 1)


def current_scope(release_text: str) -> str:
    m = re.findall(r'(?m)^RELEASE_SCOPE="([^"\n]*)"$', release_text)
    if len(m) != 1:
        die("driver com %d linhas RELEASE_SCOPE de uma linha (exigido: 1)" % len(m))
    return m[0]


def derive_edits(rel_old: str, man_old: str, tst_old: str, scope: str,
                 block: str) -> Tuple[str, str, str, str]:
    """As 3 edicoes a partir das pre-imagens: (release.sh, manifesto, teste, sha)."""
    old_scope = current_scope(rel_old)
    rel_new = edit_release_sh(rel_old, block)
    if current_scope(rel_new) != scope:
        die("o escopo gravado no driver nao e o derivado")
    if rel_new.count(TAG_MSG_TEMPLATE) != 1:
        die("o driver nao monta a anotacao da tag pelo molde que o sentinel reproduz")
    rel_sha = hashlib.sha256(rel_new.encode("utf-8")).hexdigest()
    man_new = edit_manifest(man_old, rel_sha)
    changed = [k for k, (x, y) in enumerate(zip(man_old.splitlines(),
                                                man_new.splitlines())) if x != y]
    if len(changed) != 1 or len(man_old.splitlines()) != len(man_new.splitlines()):
        die("o re-pin do manifesto mudou %d linhas (exigido: 1)" % len(changed))
    tst_new = edit_scope_test(tst_old, old_scope, scope, block)
    return rel_new, man_new, tst_new, rel_sha


def tag_text(scope: str) -> str:
    """O texto que vai para a anotacao da tag, na forma de TAG_MSG_TEMPLATE;
    `<tag>` e `<commit do corte>` sao preenchidos pelo driver no corte."""
    return ("<tag> — %s\n\nAnchor: <commit do corte>\nScope:  %s\n\nHeadline: %s\n\n"
            "No speed claim. See CHANGELOG.md [%s].\n"
            % (RELEASE_TITLE, scope, RELEASE_HEADLINE, TARGET_BASE))


def tag_text_section(scope: str) -> str:
    """A secao derivada do sentinel, entre os marcadores (inclusive)."""
    return "%s\n```text\n%s```\n%s\n" % (TAG_TEXT_BEGIN, tag_text(scope), TAG_TEXT_END)


# --------------------------------------------------------------------------
# CHANGELOG: PRE-CONDICAO, nunca alvo de escrita
# --------------------------------------------------------------------------
_HDR_RX = re.compile(
    r"v([\d.]+): (\d+) skills, (\d+) slash commands, (\d+) ADRs, "
    r"(\d+) `_lib` modules\)")


def _preamble(text: str) -> str:
    body_at = re.search(r"(?m)^## \[", text)
    if not body_at:
        die("CHANGELOG sem nenhuma secao '## [' — arquivo errado?")
    return text[:body_at.start()]


def _section(text: str, version: str) -> str:
    at = re.search(r"(?m)^## \[%s\]" % re.escape(version), text)
    if not at:
        return ""
    rest = text[at.start():]
    nxt = re.search(r"(?m)^## \[", rest[4:])
    return rest[: nxt.start() + 4] if nxt else rest


def _dated_header(sec: str, version: str) -> bool:
    head = sec.splitlines()[0] if sec else ""
    return bool(re.fullmatch(r"## \[%s\] [-—] \d{4}-\d{2}-\d{2}\s*" % re.escape(version), head))


def assert_changelog_ready(repo: pathlib.Path, text: str, counts: Dict[str, int]) -> str:
    """A entrada da release ja tem de estar la; devolve o rotulo do preambulo."""
    for v in (TARGET_BASE, PREV_TARGET):
        secs = re.findall(r"(?m)^## \[%s\]" % re.escape(v), text)
        if len(secs) != 1:
            die("CHANGELOG com %d secoes [%s] (exigido: exatamente 1). Esta cerimonia "
                "NAO escreve o CHANGELOG." % (len(secs), v))
    if re.search(r"(?m)^## \[Unreleased\]", text):
        die("CHANGELOG ainda tem uma secao [Unreleased] — o que ela descreve "
            "entra ou nao nesta release?")
    preamble = _preamble(text)
    ms = list(_HDR_RX.finditer(preamble))
    if len(ms) != 1:
        die("CHANGELOG: %d claims de contagem no preambulo (exigido: 1)" % len(ms))
    m = ms[0]
    got = {"skills": int(m.group(2)), "commands": int(m.group(3)),
           "adrs": int(m.group(4)), "lib": int(m.group(5))}
    bad = ["%s: preambulo=%d vivo=%d" % (k, got[k], counts[k])
           for k in ("skills", "commands", "adrs", "lib") if got[k] != counts[k]]
    if bad:
        die("claim de contagens do CHANGELOG defasado: %s" % "; ".join(bad))
    label = m.group(1)
    if label != TARGET_BASE:
        die("o claim de contagens do preambulo diz v%s; esperado v%s" % (label, TARGET_BASE))
    sec = _section(text, TARGET_BASE)
    # a anotacao da tag termina em «See CHANGELOG.md [1.4.4]»: a entrada que
    # ela aponta tem de estar DATADA, como a de toda rc anterior; a [1.4.3]
    # (a fonte das ancoras herdadas) tambem
    for v, s in ((TARGET_BASE, sec), (PREV_TARGET, _section(text, PREV_TARGET))):
        if not _dated_header(s, v):
            die("a secao [%s] do CHANGELOG nao esta datada (exigido '## [%s] - AAAA-MM-DD')" % (v, v))
    why = _annex_problem(sec)
    if why is not None:
        die(why)
    later = _later_framework_versions(sec)
    if later:
        die("a secao [%s] do CHANGELOG nomeia versao posterior (%s) fora da tabela de "
            "versoes de ferramentas externas (EXTERNAL_VERSIONS) — promessa de versao"
            % (TARGET_BASE, ", ".join(later)))
    links = paragraph_links_problem(sec)
    if links:
        die("a headline tem paragrafo sem frase na secao [%s]:\n  %s" % (TARGET_BASE, "\n  ".join(links)))
    return label


# --------------------------------------------------------------------------
# --verify: a linha hard do SIGN
# --------------------------------------------------------------------------
def _sentinel_field(lines: List[str], key: str, rx: str) -> str:
    got = [ln[len(key) + 2:] for ln in lines if ln.startswith(key + ": ")]
    if len(got) != 1 or not re.fullmatch(rx, got[0]):
        die("sentinel: linha %s ausente, repetida ou fora da forma" % key)
    return got[0]


def verify(repo: pathlib.Path) -> int:
    """Re-deriva a partir das pre-imagens do HEAD e exige igualdade byte a byte
    com a arvore (que no SIGN ja tem o patch aplicado). So plumbing."""
    os.environ["GIT_OPTIONAL_LOCKS"] = "0"
    assert_base(repo, tag_required=False)
    sent = run_bytes(repo, "cat-file", "blob", "HEAD:%s" % SENTINEL).decode("utf-8")
    lines = sent.split("\n")
    derived_from = _sentinel_field(lines, "Derived-From", r"[0-9a-f]{40}")
    scope_pinned = _sentinel_field(lines, "Scope-Derived", r"[^\n]+")
    # «materiais sao o ultimo land»: nenhum commit depois da base que toque caminho
    # fora do pacote, inclusive por merge (--full-history: sem a simplificacao que
    # esconde o lado de um `merge -s ours`), e nenhum commit nao-merge vazio
    if git_rc(repo, "merge-base", "--is-ancestor", derived_from, "HEAD") != 0:
        die("Derived-From do sentinel (%s) nao e ancestral do HEAD" % derived_from[:12])
    base_eff = run(repo, "log", "-1", "--format=%H", "HEAD", "--", ".",
                   ":(exclude)%s" % PACK_DIR, ":(exclude)%s" % SENTINEL).strip()
    fora = run(repo, "rev-list", "--full-history", "%s..HEAD" % derived_from, "--", ".",
               ":(exclude)%s" % PACK_DIR, ":(exclude)%s" % SENTINEL).split()
    if base_eff != derived_from or fora:
        after = run(repo, "log", "--full-history", "--format=%h %s", "%s..HEAD" % derived_from,
                    "--", ".", ":(exclude)%s" % PACK_DIR, ":(exclude)%s" % SENTINEL).strip()
        die("Derived-From do sentinel (%s) nao e o ultimo commit fora de %s (%s); "
            "commit(s) depois da derivacao que tocam fora do pacote:\n  %s\nRe-derive, re-rode o "
            "rail e re-commite os materiais."
            % (derived_from[:12], PACK_DIR, base_eff[:12], after.replace("\n", "\n  ") or "(nenhum)"))
    for c in run(repo, "rev-list", "--no-merges", "%s..HEAD" % derived_from).split():
        if not run(repo, "diff-tree", "--no-commit-id", "-r", "--name-only", c).strip():
            die("Derived-From do sentinel (%s): o commit %s depois da derivacao e vazio "
                "(nenhum caminho); re-derive e re-commite os materiais" % (derived_from[:12], c[:12]))
    plans, adrs = derive_train(repo)
    scope = scope_string(plans, adrs)
    if scope != scope_pinned:
        die("escopo re-derivado do HEAD difere do Scope-Derived do sentinel:\n"
            "  sentinel:     %s\n  re-derivado:  %s" % (scope_pinned, scope))
    block = build_per_release_block(scope)
    assert_block_is_inert(block)
    assert_no_bare_semver(block)
    assert_no_site_count_or_publish_claim(block)
    assert_no_stale_text(block)
    pre = {}
    for rel in TARGETS:
        pre[rel] = run_bytes(repo, "cat-file", "blob", "HEAD:%s" % rel).decode("utf-8")
    rel_new, man_new, tst_new, rel_sha = derive_edits(
        pre[RELEASE_SH], pre[MANIFEST], pre[SCOPE_TEST], scope, block)
    for rel, want in ((RELEASE_SH, rel_new), (MANIFEST, man_new), (SCOPE_TEST, tst_new)):
        p = repo / rel
        if p.is_symlink() or not p.is_file():
            die("alvo nao e arquivo regular: %s" % rel)
        if p.read_bytes() != want.encode("utf-8"):
            die("%s na arvore difere da re-derivacao a partir de HEAD:%s" % (rel, rel))
    i = sent.find(TAG_TEXT_BEGIN + "\n")
    j = sent.find(TAG_TEXT_END + "\n")
    if sent.count(TAG_TEXT_BEGIN) != 1 or sent.count(TAG_TEXT_END) != 1 or i < 0 or j < i:
        die("sentinel: marcadores do texto da tag ausentes, repetidos ou fora de ordem")
    if sent[i:j + len(TAG_TEXT_END) + 1] != tag_text_section(scope):
        die("sentinel: a secao do texto da tag difere da derivada do HEAD")
    counts = derive_counts(repo)
    cp = repo / CHANGELOG
    if cp.is_symlink() or not cp.is_file():
        die("CHANGELOG nao e arquivo regular")
    label = assert_changelog_ready(repo, cp.read_text(encoding="utf-8"), counts)
    sys.stdout.write("verify OK: base %s ancestral; Derived-From %s = ultimo commit fora do "
                     "pacote; escopo %s\n" % (BASE_SHA[:12], derived_from[:12], scope))
    sys.stdout.write("verify OK: os 3 alvos = re-derivacao byte a byte a partir do HEAD "
                     "(release.sh sha256 %s); texto da tag do sentinel = derivado; CHANGELOG "
                     "pronto (rotulo do preambulo v%s, contagens %s)\n"
                     % (rel_sha, label, json.dumps(counts, sort_keys=True)))
    return 0


def main() -> int:
    ap = argparse.ArgumentParser()
    ap.add_argument("--repo", default=".")
    g = ap.add_mutually_exclusive_group()
    g.add_argument("--check", action="store_true")
    g.add_argument("--claims-only", action="store_true")
    g.add_argument("--verify", action="store_true")
    g.add_argument("--tag-text", action="store_true")
    g.add_argument("--self-check", action="store_true")
    a = ap.parse_args()
    assert_no_dangling_names()
    if a.self_check:
        sys.stdout.write("self-check OK: nenhum nome lido sem definicao no arquivo; nenhum de %s em uso\n"
                         % ", ".join(REMOVED_NAMES))
        return 0
    repo = pathlib.Path(a.repo).resolve()
    if not (repo / ".git").exists():
        die("%s nao parece a raiz de um repositorio" % repo)

    if a.claims_only:
        res = check_claims(repo)
        for key, name, cok, cdet, tok, tdet in res:
            sys.stdout.write("%s  [%s] %s\n      codigo: %s — %s\n      texto:  %s — %s\n"
                             % ("PASS" if cok and tok else "FAIL", key, name,
                                "PASS" if cok else "FAIL", cdet,
                                "PASS" if tok else "FAIL", tdet))
        return 0 if all(r[2] and r[4] for r in res) else 1

    if a.verify:
        return verify(repo)

    assert_base(repo, tag_required=True)
    plans, adrs = derive_train(repo)
    scope = scope_string(plans, adrs)
    if a.tag_text:
        sys.stdout.write(tag_text_section(scope))
        return 0
    counts = derive_counts(repo)
    block = build_per_release_block(scope)
    assert_block_is_inert(block)
    assert_no_bare_semver(block)
    assert_no_site_count_or_publish_claim(block)
    assert_no_stale_text(block)

    rp, cp, mp, tp = (repo / RELEASE_SH, repo / CHANGELOG, repo / MANIFEST,
                      repo / SCOPE_TEST)
    for p in (rp, cp, mp, tp):
        if p.is_symlink() or not p.is_file():
            die("alvo nao e arquivo regular: %s" % p)

    label = assert_changelog_ready(repo, cp.read_text(encoding="utf-8"), counts)
    claims = assert_claims(repo)

    rel_new, man_new, tst_new, rel_sha = derive_edits(
        rp.read_text(encoding="utf-8"), mp.read_text(encoding="utf-8"),
        tp.read_text(encoding="utf-8"), scope, block)

    applied = 0
    if not a.check:
        rp.write_text(rel_new, encoding="utf-8")
        mp.write_text(man_new, encoding="utf-8")
        tp.write_text(tst_new, encoding="utf-8")
        applied = EDIT_COUNT_DECLARED  # bloco + manifesto + re-pin do teste
        on_disk = hashlib.sha256(rp.read_bytes()).hexdigest()
        if on_disk != rel_sha:
            die("sha de release.sh em disco (%s) != o gravado no manifesto (%s)"
                % (on_disk, rel_sha))

    sys.stdout.write("scope: %s\n" % scope)
    sys.stdout.write("counts: %s (rotulo do preambulo: v%s)\n"
                     % (json.dumps(counts, sort_keys=True), label))
    for key, name, _c, cdet, _t, tdet in claims:
        sys.stdout.write("claim PASS [%s] %s: codigo: %s; texto: %s\n" % (key, name, cdet, tdet))
    sys.stdout.write(
        "release.sh sha256 (pos-edicao): %s\n"
        "edits: %d/%d (CHANGELOG: pre-condicao CONFERIDA, nao escrita)%s\n"
        % (rel_sha, applied, EDIT_COUNT_DECLARED,
           "  (--check: NADA escrito)" if a.check else ""))
    return 0


if __name__ == "__main__":
    sys.exit(main())
