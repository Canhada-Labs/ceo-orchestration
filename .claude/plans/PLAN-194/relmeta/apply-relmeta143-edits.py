#!/usr/bin/env python3
"""Material VERSIONADO da cerimonia relmeta-143 (PLAN-194, RM da v1.4.3).

Aplica as TRES edicoes que destravam `release.sh` para a v1.4.3:

  1. o bloco PER-RELEASE do driver (TARGET_BASE, titulo, escopo, headline);
  2. o sha256 do driver no manifesto ADR-192 (canonico);
  3. o re-pin CONSCIENTE do teste que fixa o escopo da anotacao da tag.

Clonado POR REMOCAO de `PLAN-193/relmeta/apply-relmeta142-edits.py`. O que
sai: as edicoes do `--yes` do probe GPG e do controle dele (ja estao no HEAD
desde 36bbe90c) e as ancoras da 1.4.2 que nao descrevem esta release (Opus
5.5, esforco e T54 do piso, FN-04, relaunch, via expressa). O que muda:

- a faixa e `BASE_SHA..HEAD`, com BASE_SHA o commit da v1.4.2 (b55084da); a
  tag `v1.4.2`, quando existe, tem de descascar para ele;
- cada ancora separa a parte de CODIGO (arquivos, AST, ancestralidade, sondas)
  da parte de TEXTO (frases da secao [1.4.3] do CHANGELOG, com o espaco em
  branco normalizado): o controle vermelho roda a arvore da v1.4.2 com o
  CHANGELOG do HEAD sobreposto e le as duas partes em separado;
- o modo `--verify` e a linha hard do SIGN: re-deriva, a partir das
  PRE-imagens do HEAD (`git cat-file blob HEAD:<alvo>`), o escopo, o bloco, o
  manifesto e o teste, e exige igualdade BYTE A BYTE com os 3 arquivos da
  arvore (que no SIGN ja tem o patch aplicado); confere a secao do texto da
  tag e as linhas Derived-From e Scope-Derived do sentinel, e o CHANGELOG como
  pre-condicao. Sem `git status`: so plumbing, com GIT_OPTIONAL_LOCKS=0. As
  ancoras NAO rodam no `--verify` (sondas de runtime ficam fora do SIGN): elas
  rodam no `--claims-only`, manual antes da rc.1 e do GA.

  python3 apply-relmeta143-edits.py --repo <root> [--check | --claims-only | --verify | --tag-text]

`--check` nao escreve nada: imprime as derivacoes e valida ancoras e
pre-condicoes. `--claims-only` roda so as ancoras e imprime uma linha
PASS/FAIL por ancora, com o resultado de codigo e o de texto (rc 0 = todas
passam). `--tag-text` imprime so o texto da tag derivado (o derive o grava no
sentinel). As sondas escrevem SO em diretorios temporarios proprios,
removidos ao fim. stdlib only, Python >= 3.9.

POR QUE ISTO E UMA CERIMONIA. `.claude/governance/gate-scripts-manifest.txt` e
CANONICO, e `.claude/scripts/local/release.sh` e MEMBRO dele: mudar um byte do
driver sem re-pinar o sha derruba os workflows que conferem o manifesto. E o
titulo, o escopo e a headline vao para DENTRO da anotacao ASSINADA da tag.
"""
from __future__ import annotations

import argparse
import ast
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
from typing import Callable, Dict, List, Optional, Tuple

EDIT_COUNT_DECLARED = 3

RELEASE_SH = ".claude/scripts/local/release.sh"
MANIFEST = ".claude/governance/gate-scripts-manifest.txt"
SCOPE_TEST = ".claude/scripts/tests/test_release_bump_sites.py"
CHANGELOG = "CHANGELOG.md"
PACK_DIR = ".claude/plans/PLAN-194/relmeta"
SENTINEL = ".claude/plans/PLAN-194/relmeta-approved.md"
TARGETS = (RELEASE_SH, MANIFEST, SCOPE_TEST)

BASE_TAG = "v1.4.2"
# o commit da v1.4.2 (o mesmo literal da constante V142 de PLAN-183/w7a/hard-w7a.sh)
BASE_SHA = "b55084da6dd8e4a05fc9893b2690df8aebcfd0ca"
PREV_BASE = "1.4.2"
TARGET_BASE = "1.4.3"
# a cerimonia anterior, citada no docstring do teste de escopo
PREV_RELMETA = "relmeta-142"
PREV_OWN_PLAN = "PLAN-193"
# o plano desta release: o commit dos materiais o cita, entao ele TEM de ja
# estar no trem — senao commitar os materiais mudaria o escopo derivado
OWN_PLAN = "PLAN-194"

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
CODEX_MANIFEST = ".claude/governance/codex-cli-pin-manifest.json"
CODEX_PIN_TXT = ".claude/governance/codex-cli-pin.txt"
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
AUDIT_LOG = ".claude/hooks/audit_log.py"
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
V140_ENVELOPE = ".claude/governance/pair-rail-verdict-v1.4.0.md"
V142_RC1_ENVELOPE = ".claude/governance/pair-rail-verdict-v1.4.2-rc.1.md"
DR_GUIDE = "docs/DISASTER-RECOVERY.md"

RELEASE_TITLE = (
    "Maintenance release: harness-config gate cured for the default ceremony on upgrade"
    " and fresh install, condition 67 of v1.4.0-rc.1 retired, Codex CLI re-pin"
)

# Vai para DENTRO da anotacao assinada da tag. ASCII, sem crase, sem cifrao,
# sem barra invertida, sem aspa dupla, e toda versao escrita com o prefixo v
# (um semver NU aqui reprovaria o teste
# test_driver_derives_every_version_string_from_target_base). Cada paragrafo
# tem ancora em CLAIMS e fonte na secao [1.4.3] do CHANGELOG.
RELEASE_HEADLINE = """Release de manutencao (PLAN-194). Os requisitos nao mudam desde a
v1.4.2: Claude Code v2.1.280 ou mais novo (install.sh e upgrade.sh
seguem recusando, com saida 6, um claude mais antigo no PATH, salvo
com --allow-old-claude-code), Python 3.9 ou mais novo e Node.js 20
ou mais novo para o shim do npm.

O gate de configuracao do harness do /ceo-boot reprovava nas
instalacoes: as fixtures do replay moravam num diretorio que a
instalacao nao recebe. Elas passam a morar em
.claude/hooks/_lib/harness_replay/. Na cerimonia padrao
(maintainer), o gate sai verde numa instalacao feita da v1.4.2 e
atualizada pelo upgrade.sh desta release e numa instalacao nova;
testes no CI provam os dois casos para uma forma de instalacao
(--profile core --ceremony maintainer), e a arvore de antes da cura
reproduz o vermelho. A instalacao com --ceremony user nao e coberta
por esta afirmacao (Known-open do CHANGELOG). O gate fica mais
estrito: as leituras de JSON dele recusam os tokens NaN e Infinity.

O gravador do agent_spawn passa a ler o elo anterior da cadeia,
calcular o HMAC, gravar a linha e atualizar o sidecar sob uma unica
trava do log. Isto aposenta a condicao 67 assinada da v1.4.0-rc.1:
a quebra de cadeia quando esse gravador lia o elo anterior antes de
pegar a trava. As quebras que a corrida ja gravou ficam nos logs, e
gravadores que resolvem travas diferentes para o mesmo log seguem
sem se excluir.

Uma instalacao nova com --ceremony user grava
permissions.defaultMode com o valor manual quando o settings.json
produzido por essa mesma execucao nao tem defaultMode, salvo com
CEO_INSTALL_SKIP_DENY_BASELINE=1. Um settings.json que ja existia
antes da instalacao nunca e tocado, e o upgrade.sh nao muda.

Numa instalacao que registrou a mao o hook do envelope de custo, um
bloqueio passa a ser gravado no log de auditoria; nenhuma release
anterior o gravava. Nenhum template de settings enviado registra
esse hook. Correcoes em audit-query.py, /status, /ceo-boot e
check-substrate-drift.py.

Pair-rail: o revisor e re-pinado no Codex CLI v0.160.0; o manifesto
do payload pina esse binario por sha256, para uma plataforma so.
Numa instalacao o pin resolve como infraestrutura e segue advisory,
como antes.

A parte honesta: este trem saiu para curar o spool de auditoria, e
essa cura nao entrou no corte; o spool deixa arquivos por processo
para tras, e a drenagem forcada dele pode passar do timeout de um
hook. Do anexo assinado da v1.4.0 esta release cura so a condicao
67; o resto segue aberto, sem release atribuida a cura, e o mesmo
vale para os tres achados P1 do anexo assinado da v1.4.2-rc.1. A
limpeza do Claude Code (cleanupPeriodDays, 30 dias por padrao)
ainda pode apagar o log de auditoria, e nenhum plano desta release
carrega uma cura estrutural; o backup deixa de fora o material de
chave, entre ele a chave HMAC e o sal. Quatro merges de pull
request trouxeram arquivos do framework ao main sem a cerimonia de
assinatura, e nada no repositorio impede a repeticao (medido em
2026-10-14). Os demais residuos estao no Known-open da entrada do
CHANGELOG."""

# Texto da 1.4.2 (e anterior) que nao pode sobreviver no bloco novo.
FORBID = (
    "0.156.1", "Opus 5.5", "claude-opus-5-5", "FN-04", "relaunch",
    "Release expressa", "Via expressa", "express", "PLAN-190 / PLAN-193",
    "PLAN-169 / PLAN-189 / PLAN-190", "PLAN-119 / PLAN-169 / PLAN-170",
    "PLAN-162 / PLAN-165",
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


def assert_base(repo: pathlib.Path, tag_required: bool) -> None:
    """BASE_SHA ancestral do HEAD; a tag BASE_TAG, se existe, descasca nele.

    Na derivacao a tag e obrigatoria; no --verify e opcional (o clone do
    roteiro pode nao trazer tags), mas, presente, tem de ser a da v1.4.2."""
    if git_rc(repo, "cat-file", "-e", "%s^{commit}" % BASE_SHA) != 0:
        die("o commit %s (v%s) nao esta no repositorio" % (BASE_SHA[:12], PREV_BASE))
    if git_rc(repo, "merge-base", "--is-ancestor", BASE_SHA, "HEAD") != 0:
        die("%s (v%s) nao e ancestral do HEAD" % (BASE_SHA[:12], PREV_BASE))
    has_tag = git_rc(repo, "rev-parse", "-q", "--verify", "refs/tags/%s" % BASE_TAG) == 0
    if not has_tag:
        if tag_required:
            die("tag %s ausente — a relmeta-143 deriva com a tag do GA %s no repositorio"
                % (BASE_TAG, BASE_TAG))
        return
    peeled = run(repo, "rev-parse", "--verify", "refs/tags/%s^{commit}" % BASE_TAG).strip()
    if peeled != BASE_SHA:
        die("a tag %s descasca para %s, nao para %s" % (BASE_TAG, peeled, BASE_SHA))


def derive_train(repo: pathlib.Path) -> Tuple[List[str], List[str]]:
    """Planos citados nos assuntos de commit + ADRs tocados na faixa.

    A regra e a do G0 do corte (OWNER-RC1-CUT.sh, assert_release_scope_covers_log):
    QUALQUER PLAN-NNN citado num assunto da faixa entra, inclusive planos
    abandonados ou que so aparecem num commit de fechamento. Um conjunto VAZIO
    de ADRs e legitimo e e escrito como «nenhum». Um conjunto vazio de PLANOS
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
    return plans, adrs


def scope_string(plans: List[str], adrs: List[str]) -> str:
    # Os ADRs sao LISTADOS, nunca escritos como faixa `primeiro -> ultimo`.
    return "%s (ADRs tocados: %s)" % (
        " / ".join(plans), " ".join(adrs) if adrs else "nenhum")


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
        bad.append("%s (%s) nao e ancestral do HEAD" % (commit, what))
    elif rc != 0:
        bad.append("%s (%s) ausente do repositorio (rc=%d)" % (commit, what, rc))


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
    tmp = pathlib.Path(tempfile.mkdtemp(prefix="relmeta143-ccfloor."))
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


def _phrases(sec: str, phrases: Tuple[str, ...]) -> List[str]:
    flat = _norm(sec)
    return ["a secao [%s] do CHANGELOG nao diz %r" % (TARGET_BASE, p)
            for p in phrases if _norm(p) not in flat]


def _changelog_section(repo: pathlib.Path) -> str:
    return _section(_read_text(repo, CHANGELOG) or "", TARGET_BASE)


def _known_open_subsections(sec: str) -> List[str]:
    subs = []
    for ko in re.finditer(r"(?m)^###[^\n]*Known-open[^\n]*\n", sec):
        tail = sec[ko.end():]
        nxt = re.search(r"(?m)^#{2,3} ", tail)
        subs.append(tail[: nxt.start()] if nxt else tail)
    return subs


# versao com ou sem o prefixo v: «v1.4.4» tambem e promessa (a 142 so via
# o semver NU, porque \b nao separa o v do digito)
_LATER_RX = re.compile(r"(?<![\d.])v?(\d+\.\d+\.\d+)\b")
# Versoes de ferramentas EXTERNAS que a [1.4.3] e a headline citam, declaradas
# uma a uma: qualquer outra versao posterior a TARGET_BASE, em QUALQUER major e
# com ou sem o prefixo v, e tratada como versao do framework (promessa).
EXTERNAL_VERSIONS = {
    "2.1.280": "Claude Code", "2.1.284": "Claude Code", "2.1.285": "Claude Code",
    "2.1.293": "Claude Code", "2.1.295": "Claude Code",
    "11.5.1": "npm", "11.20.0": "npm",
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


# --------------------------------------------------------------------------
# ancoras: uma por paragrafo da headline; CODIGO e TEXTO em separado
# --------------------------------------------------------------------------
def code_ccfloor(repo: pathlib.Path) -> List[str]:
    bad: List[str] = []
    for rel in (INSTALL_SH, UPGRADE_SH):
        bad.extend(_floor_probe(repo, rel))
        # «inalterado»: o bloco do piso e byte a byte o da v1.4.2
        now = _floor_block(_read_text(repo, rel) or "")
        then = _floor_block(run(repo, "show", "%s:%s" % (BASE_SHA, rel)))
        if now is None or then is None or now != then:
            bad.append("%s: o bloco do piso difere do da v%s (ou falta)" % (rel, PREV_BASE))
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


def text_ccfloor(sec: str) -> List[str]:
    return _phrases(sec, ("The requirements do not change from v1.4.2",
                          "Claude Code 2.1.280 or later", "Python 3.9 or later",
                          "Node.js 20 or later"))


def _harness_gate_probe(repo: pathlib.Path) -> List[str]:
    """O gate no modo do CI, na raiz, no ambiente do clean_run da hard-w7a."""
    tmp = pathlib.Path(tempfile.mkdtemp(prefix="relmeta143-harness."))
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
                   % (falta, TARGET_BASE, list(USER_DENY_GAP)))
    return bad, falta


def text_harness(sec: str) -> List[str]:
    bad = _phrases(sec, (
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
            bad.append("a secao [%s] nao nomeia a entrada de deny `%s`" % (TARGET_BASE, e))
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
        return ["%s nao parseia (%s)" % (AUDIT_LOG, exc)]
    fns = [n for n in ast.walk(tree) if isinstance(n, ast.FunctionDef) and n.name == "append_entry"]
    if len(fns) != 1:
        return ["%s: %d funcoes append_entry (exigido: 1)" % (AUDIT_LOG, len(fns))]
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
    bad: List[str] = []
    src = _need_text(repo, AUDIT_LOG, bad)
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


def text_cond67(sec: str) -> List[str]:
    return _phrases(sec, (
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
        bad.append("%s mudou desde a v%s (blob %s -> %s)" % (UPGRADE_SH, PREV_BASE, a[:12], b[:12]))
    return bad


def text_defaultmode(sec: str) -> List[str]:
    return _phrases(sec, (
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


def text_cenv(sec: str) -> List[str]:
    return _phrases(sec, (
        "On an install that registered the cost-envelope hook by hand, a block is now "
        "recorded in the audit log",
        "No earlier release recorded it",
        "No shipped settings template registers this hook"))


def code_fixes(repo: pathlib.Path) -> List[str]:
    bad: List[str] = []
    st = _need_text(repo, STATUS_PY, bad)
    if st and "--as-json" in st:
        bad.append("%s ainda passa --as-json" % STATUS_PY)
    sd = _need_text(repo, SUBSTRATE_DRIFT, bad)
    if sd and "COMPONENT_CHECK_ERROR" not in sd:
        bad.append("%s sem COMPONENT_CHECK_ERROR" % SUBSTRATE_DRIFT)
    boot = _need_text(repo, CEO_BOOT_PY, bad)
    if boot and "external_wait" not in boot:
        bad.append("%s sem external_wait (plano que declara a espera)" % CEO_BOOT_PY)
    p = repo / AUDIT_QUERY_TEST
    if p.is_symlink() or not p.is_file():
        bad.append("%s ausente" % AUDIT_QUERY_TEST)
    return bad


def text_fixes(sec: str) -> List[str]:
    hdr = "### Fixed — `audit-query.py`, `/status`, `/ceo-boot` and `check-substrate-drift.py`"
    if hdr not in sec.splitlines():
        return ["a secao [%s] do CHANGELOG sem o cabecalho %r" % (TARGET_BASE, hdr)]
    return []


def code_codex(repo: pathlib.Path) -> List[str]:
    d, why = _read_json(repo, CODEX_MANIFEST)
    if d is None:
        return [why]
    bad: List[str] = []
    if d.get("package_version") != CODEX_VER:
        bad.append("%s: package_version=%r (esperado %s — o re-pin landou?)"
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
    m = re.fullmatch(r">=(\d+\.\d+\.\d+),<(\d+\.\d+\.\d+)", body[-1]) if body else None
    if not m:
        bad.append("%s sem range >=A,<B legivel" % CODEX_PIN_TXT)
    else:
        try:
            if not (_semver(m.group(1)) <= _semver(CODEX_VER) < _semver(m.group(2))):
                bad.append("%s: %s fora do range %s" % (CODEX_PIN_TXT, CODEX_VER, body[-1]))
        except ValueError:
            bad.append("%s: range ilegivel" % CODEX_PIN_TXT)
    _ancestor(repo, CODEX_REPIN_COMMIT, bad, "SIGN do re-pin 0.160.0")
    return bad


def text_codex(sec: str) -> List[str]:
    return _phrases(sec, (
        "re-pinned to Codex CLI 0.160.0", "for one platform only",
        "There the pin resolves as infrastructure and fails open (advisory)"))


def code_annex(repo: pathlib.Path) -> List[str]:
    bad: List[str] = []
    for rel in (V140_ENVELOPE, V142_RC1_ENVELOPE):
        p = repo / rel
        if p.is_symlink() or not p.is_file():
            bad.append("%s ausente" % rel)
    # acoplamento: a [1.4.3] diz que o guia de recuperacao NAO fala do
    # material de chave; o guia que passar a falar torna a frase falsa
    dr = _need_text(repo, DR_GUIDE, bad)
    if re.search(r"audit-key|\.salt\b", dr):
        bad.append("%s cita audit-key ou .salt, e a [%s] diz que o guia nao fala disso"
                   % (DR_GUIDE, TARGET_BASE))
    return bad


def text_annex(sec: str) -> List[str]:
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
    bad.extend(_phrases(sec, (
        "set out to cure the audit spool, and that cure did not make the cut",
        "The three P1 findings of the signed rc.1 annex",
        "It does not archive the key material",
        "the disaster-recovery guide does not say so",
        "Four GitHub pull-request merges brought framework files into `main` without "
        "the signing ceremony",
        "Nothing in the repository prevents a repeat",
        "2026-10-14",
        "There is no plan in this release with a structural cure")))
    return bad


Claim = Tuple[str, str, Callable[[pathlib.Path], List[str]], Callable[[str], List[str]], str]
CLAIMS: Tuple[Claim, ...] = (
    ("ccfloor", "requisitos inalterados (piso do Claude Code, Node.js do shim)", code_ccfloor,
     text_ccfloor,
     "piso %s rodado contra um claude falso no install.sh e no upgrade.sh (recusa abaixo e com "
     "sufixo colado, saida %s no topo; override, ausencia, versao ilegivel e --version parado so "
     "avisam); o bloco do piso byte a byte o da v%s nos dois; SUPPORT.md cita %s; engines.node "
     ">=20" % (CC_MIN, CC_FLOOR_EXIT, PREV_BASE, CC_MIN)),
    ("harness", "gate do harness: fixtures num caminho entregue", code_harness, text_harness,
     "REPLAY_FIXTURES_REL e o marcador novos; a pasta nova so com os 3 .json; a antiga ausente; "
     "os grupos harness-* no teste historico e o smoke-install.yml rodando-o; C9 e o SIGN da W7a "
     "ancestrais; o deny da instalacao user sem exatamente as 4 entradas do DENY_BASELINE do "
     "gate que a [1.4.3] declara; o gate no modo do CI na raiz verde (HOME proprio, sem "
     "CLAUDE_*/CEO_*)"),
    ("cond67", "condicao 67: o elo lido dentro da trava", code_cond67, text_cond67,
     "por AST, a leitura do elo, a escrita da linha e a atualizacao do sidecar de append_entry "
     "num MESMO with FileLock(paths[\"lock\"]); sentinel e .asc da cura presentes, SIGN "
     "ancestral; a condicao 67 no envelope da v1.4.0-rc.1"),
    ("defaultmode", "defaultMode manual no install user", code_defaultmode, text_defaultmode,
     "install.sh com DEFAULT_MODE_BASELINE=\"manual\" (1 linha), as rotas jq e python e o skip "
     "por ambiente; o template user sem permissions.defaultMode (JSON); upgrade.sh com o mesmo "
     "blob da v%s" % PREV_BASE),
    ("cenv", "cost_envelope_capped gravado; nenhum template registra", code_cenv, text_cenv,
     "por AST, uma chamada emit_generic(%r) com kwargs = %s, sem action; nenhum "
     "templates/settings/*.json registra o hook; SIGN do cenv ancestral"
     % (COST_EVENT, ", ".join(sorted(COST_KWARGS)))),
    ("fixes", "correcoes de audit-query, /status, /ceo-boot e check-substrate-drift", code_fixes,
     text_fixes,
     "status.py sem --as-json; check-substrate-drift.py com COMPONENT_CHECK_ERROR; ceo-boot.py "
     "com external_wait; o teste novo da ordem dos flags do audit-query presente"),
    ("codex", "pin do Codex CLI 0.160.0, uma plataforma", code_codex, text_codex,
     "manifesto pina %s por sha256 so para %s; o range do pin o admite; SIGN do re-pin "
     "ancestral" % (CODEX_VER, ", ".join(sorted(CODEX_PLATFORMS)))),
    ("annex", "parte honesta: residuos declarados", code_annex, text_annex,
     "envelopes da v1.4.0 e da v1.4.2-rc.1 presentes; o guia de recuperacao sem audit-key nem "
     ".salt (a frase «does not say so» segue verdadeira)"),
)

ClaimResult = Tuple[str, str, bool, str, bool, str]


def check_claims(repo: pathlib.Path) -> List[ClaimResult]:
    """(chave, nome, codigo ok, detalhe do codigo, texto ok, detalhe do texto)."""
    sec = _changelog_section(repo)
    out: List[ClaimResult] = []
    for key, name, code_fn, text_fn, proves in CLAIMS:
        parts = []
        for fn, arg, ok_detail in ((code_fn, repo, proves),
                                   (text_fn, sec, "as frases ancoradas estao na [%s]" % TARGET_BASE)):
            try:
                bad = fn(arg)  # type: ignore[operator]
            except Exception as exc:  # uma ancora que quebra NAO passa
                bad = ["a ancora quebrou (%s: %s)" % (type(exc).__name__, exc)]
            parts.append((not bad, "; ".join(bad) if bad else ok_detail))
        out.append((key, name, parts[0][0], parts[0][1], parts[1][0], parts[1][1]))
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
        '# .claude/plans/PLAN-194/relmeta/apply-relmeta143-edits.py\n'
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
    truncar prosa que vai para a anotacao ASSINADA da tag.
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
        stripped = value.replace("—", "")
        try:
            stripped.encode("ascii")
        except UnicodeError:
            bad.append("%s contem nao-ASCII alem do travessao" % name)
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
    start = 'TARGET_BASE="%s"\n' % PREV_BASE
    end = '\nRC_NUM="1"\n'
    if text.count(start) != 1:
        die("ancora inicial do bloco PER-RELEASE ausente ou nao unica em %s"
            " (TARGET_BASE ja nao e %s?)" % (RELEASE_SH, PREV_BASE))
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
               % (PREV_BASE, PREV_RELMETA, PREV_OWN_PLAN))
    if out.count(doc_old) != 1:
        die("teste de escopo: ancora do docstring do trem anterior ausente ou nao unica")
    doc_new = (
        "    Trem %s (re-pinado na cerimonia relmeta-143, %s): derivado por\n"
        "    apply-relmeta143-edits.py de `git log %s..HEAD` DEPOIS de todos os\n"
        "    lands da release; o trem da %s vira assercao negativa.\n"
        "\n" % (TARGET_BASE, OWN_PLAN, BASE_TAG, PREV_BASE))
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


def assert_changelog_ready(repo: pathlib.Path, text: str, counts: Dict[str, int]) -> str:
    """A entrada da release ja tem de estar la; devolve o rotulo do preambulo."""
    secs = re.findall(r"(?m)^## \[%s\]" % re.escape(TARGET_BASE), text)
    if len(secs) != 1:
        die("CHANGELOG com %d secoes [%s] (exigido: exatamente 1). Esta cerimonia "
            "NAO escreve o CHANGELOG." % (len(secs), TARGET_BASE))
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
        # «as of v1.4.2» so segue verdadeiro se o preambulo e EXATAMENTE o que a
        # v1.4.2 publicou (e as contagens, conferidas acima, nao mudaram)
        if label != PREV_BASE:
            die("o claim de contagens do preambulo diz v%s; esperado v%s (ou v%s "
                "intocado desde a tag)" % (label, TARGET_BASE, PREV_BASE))
        old = run(repo, "show", "%s:%s" % (BASE_SHA, CHANGELOG))
        if _preamble(old) != preamble:
            die("o preambulo do CHANGELOG diz v%s mas nao e o que a %s publicou — "
                "atualize o rotulo para v%s" % (PREV_BASE, BASE_TAG, TARGET_BASE))
    sec = _section(text, TARGET_BASE)
    # a anotacao da tag termina em «See CHANGELOG.md [1.4.3]»: a entrada que
    # ela aponta tem de estar DATADA, como a de toda rc anterior
    head = sec.splitlines()[0] if sec else ""
    if not re.fullmatch(r"## \[%s\] [-—] \d{4}-\d{2}-\d{2}\s*" % re.escape(TARGET_BASE), head):
        die("a secao [%s] do CHANGELOG nao esta datada (%r; exigido '## [%s] - AAAA-MM-DD'): "
            "a anotacao da tag aponta para ela" % (TARGET_BASE, head, TARGET_BASE))
    why = _annex_problem(sec)
    if why is not None:
        die(why)
    later = _later_framework_versions(sec)
    if later:
        die("a secao [%s] do CHANGELOG nomeia versao posterior (%s) fora da tabela de "
            "versoes de ferramentas externas (EXTERNAL_VERSIONS) — promessa de versao"
            % (TARGET_BASE, ", ".join(later)))
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
    ap.add_argument("--repo", required=True)
    g = ap.add_mutually_exclusive_group()
    g.add_argument("--check", action="store_true")
    g.add_argument("--claims-only", action="store_true")
    g.add_argument("--verify", action="store_true")
    g.add_argument("--tag-text", action="store_true")
    a = ap.parse_args()
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
