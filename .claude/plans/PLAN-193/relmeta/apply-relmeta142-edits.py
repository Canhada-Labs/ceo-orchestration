#!/usr/bin/env python3
"""Material VERSIONADO da cerimonia relmeta-142 (PLAN-193 W6, corte da v1.4.2).

Aplica as CINCO edicoes que destravam `release.sh` para a v1.4.2:

  1. o bloco PER-RELEASE do driver (TARGET_BASE, titulo, escopo, headline);
  2. o `--yes` no probe de assinatura do preflight (o `mktemp` CRIA o arquivo
     e `gpg --output` sobre arquivo existente pergunta «Overwrite?» no tty);
  3. o sha256 do driver no manifesto ADR-192 (canonico);
  4. o re-pin CONSCIENTE do teste que fixa o escopo da anotacao da tag;
  5. o controle do item 2 no mesmo arquivo de testes.

Clonado de `PLAN-192/relmeta/apply-relmeta141-edits.py`. O que muda de verdade:

- a faixa e `v1.4.1..HEAD` e a derivacao roda DEPOIS de todos os lands da
  1.4.2 (o escopo so e verdadeiro sobre a arvore pos-lands; o patch e
  REGENERADO na manha, nunca reaproveitado de um HEAD anterior);
- cada paragrafo da headline tem ANCORAS conferidas sobre a arvore derivada
  (`CLAIMS`). Duas sao sondas de RUNTIME: a do FN-04 (o hook roda num
  ambiente descartavel, a arvore de estado e varrida atras dos bytes de um
  canario, e um relaunch sem a copia do PostToolUse tem de sair 7 sem criar
  o --out) e a do piso do Claude Code (a funcao do install.sh e do
  upgrade.sh roda contra um claude FALSO de cada versao). As outras sao
  tripwires de presenca. Ancora que falha = recusa NOMEADA; ancora que
  passa NAO prova que a prosa descreve o diff (o Residual do sentinel);
- o CHANGELOG segue PRE-CONDICAO (nunca alvo de escrita): secao [1.4.2]
  DATADA, a re-declaracao do anexo da v1.4.0 SEM release atribuida, e os
  known-open que a headline cita.

  python3 apply-relmeta142-edits.py --repo <root> [--check | --claims-only]

`--check` nao escreve nada no repositorio: imprime as derivacoes e valida
TODAS as ancoras e pre-condicoes. `--claims-only` roda so as ancoras da
headline e imprime uma linha PASS/FAIL por paragrafo (rc 0 = todas passam).
A sonda do FN-04 escreve SO num diretorio temporario proprio, removido ao
fim. stdlib only, Python >= 3.9.

POR QUE ISTO E UMA CERIMONIA. `.claude/governance/gate-scripts-manifest.txt` e
CANONICO, e `.claude/scripts/local/release.sh` e MEMBRO dele: mudar um byte do
driver sem re-pinar o sha derruba os workflows que conferem o manifesto. E o
titulo, o escopo e a headline vao para DENTRO da anotacao ASSINADA da tag.
"""
from __future__ import annotations

import argparse
import hashlib
import json
import os
import pathlib
import re
import secrets
import shutil
import stat
import subprocess
import sys
import tempfile
import time
from typing import Any, Dict, List, Optional, Tuple

EDIT_COUNT_DECLARED = 5

RELEASE_SH = ".claude/scripts/local/release.sh"
MANIFEST = ".claude/governance/gate-scripts-manifest.txt"
SCOPE_TEST = ".claude/scripts/tests/test_release_bump_sites.py"
CHANGELOG = "CHANGELOG.md"
PACK_DIR = ".claude/plans/PLAN-193/relmeta"

BASE_TAG = "v1.4.1"
PREV_BASE = "1.4.1"
TARGET_BASE = "1.4.2"
# o plano desta release: o commit dos materiais o cita, entao ele TEM de ja
# estar no trem — senao commitar os materiais mudaria o escopo derivado
OWN_PLAN = "PLAN-193"

# --- ancoras da headline (conferidas sobre a arvore derivada) ---------------
OPUS_ID = "claude-opus-5-5"
OPUS_FALLBACK = "claude-opus-5"
CC_MIN = "2.1.280"
FRESH_EFFORT = "xhigh"
CODEX_VER = "0.156.1"
SETTINGS_PINNED = (
    ".claude/settings.json",
    "templates/settings/settings.base.json",
    "templates/settings/settings.user.json",
)
FRESH_TEMPLATES = (
    "templates/settings/settings.base.json",
    "templates/settings/settings.user.json",
)
UPGRADE_SH = "scripts/upgrade.sh"
INSTALL_SH = "scripts/install.sh"
UPGRADE_OPT_IN_FLAG = "--adopt-setting"
# o piso do Claude Code (PLAN-193 OQ-9): o bloco entre estes marcadores e o
# mesmo no install.sh e no upgrade.sh; a sonda o roda contra um claude FALSO
CC_FLOOR_BEGIN_RX = r"(?m)^# >>> claude-code-floor\b[^\n]*\n"
CC_FLOOR_END_RX = r"(?m)^# <<< claude-code-floor\b[^\n]*$"
CC_FLOOR_FN = "_claude_code_floor_check"
CC_FLOOR_OVERRIDE = "--allow-old-claude-code"
CC_FLOOR_EXIT = "6"
T54_VAR = "_T54_BASELINES_JSON"
AGENTS_DIR = ".claude/agents"
ADR149 = ".claude/adr/ADR-149-model-id-allowlist.md"
# ADR-149 A3.3, com o espaco em branco normalizado (a quebra de linha do
# markdown nao conta): onde o pin do arquivo de agente nao vale
ADR149_SESSION_MODEL_DECL = (
    "Mitigated dispatch (`subagent_type: general-purpose`",
    "and Workflow agents, when passed no model, run on the model the session "
    "runs at that moment: the pin `claude-opus-5-5`",
)
FN04_SENTINEL = ".claude/plans/PLAN-193/wave-fn04-approved.md"
FN04_CLASS_NOT_EXHAUSTED = "A classe não se esgota neste hook"
SUPPORT_MD = "SUPPORT.md"
AGENT_FRONTMATTER = ".claude/hooks/_lib/agent_frontmatter.py"
GEN_AVAILABLE = ".claude/scripts/generate-available-models.py"
CODEX_MANIFEST = ".claude/governance/codex-cli-pin-manifest.json"
CODEX_PIN_TXT = ".claude/governance/codex-cli-pin.txt"
WORKFLOW_HOOK = ".claude/hooks/check_workflow_launch.py"
RELAUNCH_CLI = ".claude/scripts/ceo-launches.py"
RELAUNCH_PLAN = ".claude/plans/PLAN-190-FOLLOWUP-relaunch-out-partial-write.md"
RELAUNCH_DOC = "docs/workflow-recovery.md"
FASTLANE_TOOLS = (
    ".claude/scripts/re-pin-codex.py",
    ".claude/scripts/check-substrate-drift.py",
    ".claude/scripts/derive-settings-baselines.py",
)
HOOK_REGISTRIES = (
    ".claude/settings.json",
    "templates/settings/settings.base.json",
    "templates/settings/settings.user.json",
)
V140_ENVELOPE = ".claude/governance/pair-rail-verdict-v1.4.0.md"

RELEASE_TITLE = (
    "Opus 5.5 as session default + Codex CLI re-pin + Workflow ledger fixes"
    " (express release)"
)

# Vai para DENTRO da anotacao assinada da tag. ASCII, sem crase, sem cifrao, e
# toda versao escrita com o prefixo v (um semver NU aqui reprovaria o teste
# test_driver_derives_every_version_string_from_target_base). Cada paragrafo
# tem ancora em CLAIMS; a leitura antes do Enter continua sendo do Owner.
RELEASE_HEADLINE = """Release expressa. O Opus 5.5 vira o modelo padrao: claude-opus-5-5
entra na lista de modelos do ADR-149, fica elegivel ao piso de VETO
e vira o pin de sessao dos settings enviados; no template base o
fallback segue claude-opus-5. Nenhum arquivo de agente muda de
modelo: os agentes de veto seguem no pin deles. Um despacho sem
modelo proprio que nao le o pin de um arquivo de agente (o
general-purpose mitigado, os agentes de Workflow) roda no modelo da
sessao, cujo pin passa a ser claude-opus-5-5.

Esta release exige Claude Code v2.1.280 ou mais novo, qualquer que
seja o modelo: install.sh e upgrade.sh recusam, com saida 6, um
claude mais antigo no PATH, salvo com --allow-old-claude-code (num
dry-run so nomeiam a recusa); uma versao com sufixo colado aos tres
numeros (um pre-release, por exemplo) conta como abaixo do piso. Sem
claude no PATH, ou sem versao legivel, so avisam. Instalacao nova
sai com esforco xhigh. Numa instalacao existente o upgrade troca por
claude-opus-5-5 o pin claude-opus-5 de uma release anterior, ou poe
o pin onde nao havia, se a lista de modelos efetiva o nomeia; quando
troca a partir do claude-opus-5 e o arquivo nao define esforco,
grava high, que passa a valer sobre o nivel salvo com /effort. Um
esforco ja definido nunca e sobrescrito; xhigh numa instalacao
existente so por opt-in (--adopt-setting effortLevel) ou a mao.

Pair-rail: o pin do Codex CLI avanca para v0.156.1, um binario por
versao exata, conferido por sha256.

Correcoes: no PreToolUse, o hook do Workflow nao grava mais os bytes
do arquivo que um scriptPath nomeia; dele, antes da decisao de
permissao do harness, ficam gravados so o caminho, o sha256 e o
tamanho. Isto cura o caso do Workflow na classe declarada no
material do GA da v1.4.1; a classe nao se esgota nesse hook. A copia
de um scriptPath passa a ser tirada so pelo PostToolUse da mesma
chamada; sem ela, relaunch sai com codigo 7 e relaunch --out nao
cria arquivo. As copias que a v1.4.1 ja gravou ficam em launches/.
E relaunch --out publica por link um temporario
ja completo e nunca apaga nem substitui o destino: um arquivo
parcial nunca aparece sob o nome pedido, nos limites declarados em
docs/workflow-recovery.md.

Via expressa: tres ferramentas de operador, sem hook que as imponha,
geram o pacote de re-pin do Codex, apontam deriva entre o Codex, o
Claude Code e os modelos instalados e o que o framework registra, e
derivam das tags GA os baselines de migracao do upgrade.

A parte honesta: a cura dos achados P1 do anexo do envelope assinado
da v1.4.0 nao faz parte desta release; o anexo segue aberto, sem
release atribuida. E esta release declara que a limpeza do Claude
Code (cleanupPeriodDays, 30 dias por padrao) pode apagar o log de
auditoria e os arquivos dele; nenhum plano carrega a cura. Sem
afirmacao de velocidade — governanca e auditabilidade, como sempre."""

# O probe do preflight (edicao 2): ancoras EXATAS no driver.
PROBE_MKTEMP = '  sig_probe="$(mktemp)"\n'
PROBE_GPG_OLD = ('      | gpg --local-user "$SIGN_KEY" --armor --detach-sign'
                 ' --output "$sig_probe" \\\n')
PROBE_GPG_NEW = ('      | gpg --yes --local-user "$SIGN_KEY" --armor --detach-sign'
                 ' --output "$sig_probe" \\\n')
PROBE_COMMENT = (
    "  # --yes: mktemp has just CREATED this file, and gpg --output over an\n"
    "  # existing file asks \"Overwrite? (y/N)\" on /dev/tty; the default answer\n"
    "  # made this probe report a working key as unable to sign (PLAN-193 W6).\n"
)

# O controle da edicao 2 (edicao 5), inserido antes deste bloco do teste.
PROBE_TEST_ANCHOR = (
    '@pytest.mark.parametrize(\n'
    '    "src", [DRIVER_SRC, SITES_SRC], ids=["driver", "site-module"]\n'
    ')\n'
    'def test_release_surfaces_make_no_site_count_claim_in_comments(src):\n'
)
PROBE_TEST = r'''_GPGPROBE_HEREDOC_RX = re.compile(r"<<(-?)[ \t]*(['\"]?)([A-Za-z_][A-Za-z0-9_]*)\2")
_GPGPROBE_SPLIT_RX = re.compile(r"\|\||&&|[;|&(){}`]")


def _gpgprobe_strip_comment(line):
    """Tira o comentario de UMA linha fisica: um # que comeca palavra, fora de
    aspas. No bash o comentario acaba na quebra de linha: uma barra no fim
    dele nao continua o comando."""
    quote = None
    for i, ch in enumerate(line):
        if quote:
            if ch == quote:
                quote = None
        elif ch in "'\"":
            quote = ch
        elif ch == "#" and (i == 0 or line[i - 1] in " \t"):
            return line[:i]
    return line


def _gpgprobe_output_commands(text):
    """Os comandos gpg que escrevem com --output, pela forma do shell: corpo
    de heredoc e dado; ; && || | & ( ) { } e crase separam comandos; um
    comando gpg tem gpg (ou um caminho que termina em /gpg) como primeira
    palavra depois de atribuicoes VAR=valor."""
    logical, cur, end_word = [], "", None
    for raw in text.splitlines():
        if end_word is not None:
            if raw.strip() == end_word:
                end_word = None
            continue
        line = _gpgprobe_strip_comment(raw)
        found = list(_GPGPROBE_HEREDOC_RX.finditer(line.replace("<<<", "   ")))
        if found:
            end_word = found[-1].group(3)
        if line.rstrip().endswith("\\"):
            cur += line.rstrip()[:-1] + " "
            continue
        logical.append(cur + line)
        cur = ""
    if cur:
        logical.append(cur)
    commands = []
    for ln in logical:
        for seg in _GPGPROBE_SPLIT_RX.split(ln):
            words = seg.split()
            while words and re.match(r"[A-Za-z_][A-Za-z0-9_]*=", words[0]):
                words.pop(0)
            if words and words[0] in ("!", "command", "exec"):
                words.pop(0)
            if not words or not re.fullmatch(r"(?:\S*/)?gpg2?", words[0]):
                continue
            if "--output" in words or "-o" in words or any(
                    w.startswith("--output=") for w in words):
                commands.append(" ".join(words))
    return commands


def _gpgprobe_missing_yes(commands):
    return [c for c in commands if "--yes" not in c.split()]


@pytest.mark.parametrize("src, found, missing", [
    ("gpg --detach-sign --output sig # --yes\n", 1, 1),
    ("gpg --yes --output good ; gpg --output bad\n", 2, 1),
    ("cat <<EOF\ngpg --yes --output ignored\nEOF\n", 0, 0),
    ("cat <<'EOF'\ngpg --output ignored\nEOF\ngpg --yes --output real\n", 1, 0),
    ("# a comment \\\ngpg --output x\n", 1, 1),
    ("/usr/bin/gpg --output x\n", 1, 1),
    ("X=1 gpg -o x --armor\n", 1, 1),
    ("printf x \\\n  | gpg --yes --local-user K --output \"$f\" \\\n  >/dev/null 2>&1\n", 1, 0),
], ids=["trailing-comment", "two-commands", "heredoc-only", "heredoc-then-real",
        "comment-backslash", "absolute-path", "assignment-and-short-flag", "continued-probe"])
def test_gpg_output_scanner_reads_commands_not_lines(src, found, missing):
    """Controle do instrumento do teste seguinte (rail relmeta-142): cada
    forma que um scanner POR LINHA errava tem o resultado certo aqui."""
    commands = _gpgprobe_output_commands(src)
    assert len(commands) == found, commands
    assert len(_gpgprobe_missing_yes(commands)) == missing, commands


def test_preflight_signature_probe_answers_its_own_overwrite_question():
    """PLAN-193 W6 (relmeta-142). O probe de assinatura do preflight escreve
    num arquivo que o proprio ``mktemp`` acabou de CRIAR. ``gpg --output``
    sobre um arquivo existente, sem ``--yes``, pergunta ``Overwrite? (y/N)``
    direto no /dev/tty (o ``>/dev/null 2>&1`` do driver nao a esconde) e, com
    a resposta padrao, o preflight morria dizendo que a chave nao conseguia
    assinar -- uma chave integra. Todo comando gpg do driver que escreve com
    ``--output`` (lido por comando, nao por linha: o instrumento tem controle
    proprio acima) carrega ``--yes``; o controle exige ter achado ao menos
    um, para nunca passar vazio."""
    commands = _gpgprobe_output_commands(DRIVER_SRC.read_text(encoding="utf-8"))
    assert commands, "no gpg --output command found in the driver: control is blind"
    missing = _gpgprobe_missing_yes(commands)
    assert not missing, "gpg --output without --yes:\n%s" % "\n".join(missing)


'''


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


def git_rc(repo: pathlib.Path, *args: str) -> int:
    return subprocess.run(
        ["git", "-C", str(repo)] + list(args),
        stdout=subprocess.DEVNULL, stderr=subprocess.DEVNULL).returncode


def assert_base_tag(repo: pathlib.Path) -> None:
    if git_rc(repo, "rev-parse", "-q", "--verify", "refs/tags/%s" % BASE_TAG) != 0:
        die("tag %s ausente — a relmeta-142 so deriva DEPOIS do corte do GA %s"
            % (BASE_TAG, BASE_TAG))
    if git_rc(repo, "merge-base", "--is-ancestor", BASE_TAG, "HEAD") != 0:
        die("%s nao e ancestral do HEAD" % BASE_TAG)


def derive_train(repo: pathlib.Path) -> Tuple[List[str], List[str]]:
    """Planos citados nos assuntos de commit + ADRs tocados na faixa.

    Um conjunto VAZIO de ADRs e legitimo e e escrito como «nenhum». Um conjunto
    vazio de PLANOS nao e: a faixa estaria errada. E o plano desta release tem
    de estar no trem ANTES dos materiais (idempotencia do commit deles).
    """
    log = run(repo, "log", "--format=%s", "%s..HEAD" % BASE_TAG)
    plans = sorted(set(re.findall(r"PLAN-\d{3}", log)))
    names = run(repo, "diff", "--name-only", "%s..HEAD" % BASE_TAG,
                "--", ".claude/adr/")
    adrs = sorted(set(re.findall(r"ADR-\d{3}", names)))
    if not plans:
        die("nenhum PLAN-NNN na faixa %s..HEAD — faixa errada?" % BASE_TAG)
    if OWN_PLAN not in plans:
        die("%s ausente dos assuntos de %s..HEAD: o commit dos materiais (que o "
            "cita) mudaria o escopo derivado. Lande antes os lands da 1.4.2 que "
            "citam %s." % (OWN_PLAN, BASE_TAG, OWN_PLAN))
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
    try:
        d = json.loads(proc.stdout)
    except Exception:
        die("verify-counts --json ilegivel (rc=%d): %r"
            % (proc.returncode, proc.stdout[:400]))
    viol = d.get("violations") or []
    if viol:
        die("verify-counts reporta %d drift(s) — corrija ANTES da cerimonia:\n  %s"
            % (len(viol), "\n  ".join(str(v) for v in viol[:6])))
    live = d.get("live") or {}
    out = {}
    for k in ("skills", "commands", "adrs", "lib"):
        v = live.get(k)
        if not isinstance(v, int):
            die("verify-counts sem contagem inteira para %r" % k)
        out[k] = v
    return out


# --------------------------------------------------------------------------
# ancoras da headline
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


def _probe_env(tmp: pathlib.Path) -> Dict[str, str]:
    """Ambiente de subprocesso que nao alcanca o HOME, o projeto, a cadeia de
    auditoria nem o TMPDIR reais: nada de CLAUDE_*, CEO_* ou PYTHONPATH
    herdado, e o TMPDIR aponta para um diretorio da propria sonda (que ela
    varre junto)."""
    env = {k: v for k, v in os.environ.items()
           if not k.startswith(("CLAUDE_", "CEO_")) and k != "PYTHONPATH"}
    env["HOME"] = str(tmp / "home")
    env["CLAUDE_PROJECT_DIR_NATIVE"] = str(tmp / "state")
    env["PYTHONDONTWRITEBYTECODE"] = "1"
    env["TMPDIR"] = str(tmp / "tmpdir")
    return env


def _agent_models(repo: pathlib.Path, ref: Optional[str]) -> Dict[str, Optional[str]]:
    """{arquivo de agente: valor da linha model:} na ref (ou no disco, ref=None)."""
    out: Dict[str, Optional[str]] = {}
    if ref is None:
        names = sorted(p.name for p in (repo / AGENTS_DIR).glob("*.md")
                       if p.is_file() and not p.is_symlink())
    else:
        names = sorted(os.path.basename(n) for n in run(
            repo, "ls-tree", "--name-only", ref, "--", AGENTS_DIR + "/").splitlines()
            if n.endswith(".md"))
    for name in names:
        rel = "%s/%s" % (AGENTS_DIR, name)
        text = (_read_text(repo, rel) if ref is None
                else run(repo, "show", "%s:%s" % (ref, rel)))
        m = re.search(r"(?m)^model:\s*(\S+)\s*$", text or "")
        out[name] = m.group(1) if m else None
    return out


def claim_opus(repo: pathlib.Path) -> Tuple[bool, str]:
    bad = []
    for rel in SETTINGS_PINNED:
        d, why = _read_json(repo, rel)
        if d is None:
            bad.append(why)
            continue
        if d.get("model") != OPUS_ID:
            bad.append("%s: model=%r (esperado %s)" % (rel, d.get("model"), OPUS_ID))
    base, why = _read_json(repo, "templates/settings/settings.base.json")
    if base is not None:
        if OPUS_ID not in (base.get("availableModels") or []):
            bad.append("settings.base.json: availableModels sem %s" % OPUS_ID)
        if base.get("fallbackModel") != [OPUS_FALLBACK]:
            bad.append("settings.base.json: fallbackModel=%r (esperado [%s])"
                       % (base.get("fallbackModel"), OPUS_FALLBACK))
    # «nenhum agente de veto muda de modelo»: nenhuma linha model: de agente
    # que ja existia na tag base mudou (o id novo so fica ELEGIVEL ao piso)
    before, now = _agent_models(repo, BASE_TAG), _agent_models(repo, None)
    if not before:
        bad.append("nenhum agente em %s na %s — ancora cega" % (AGENTS_DIR, BASE_TAG))
    moved = ["%s: %s -> %s" % (n, before[n], now.get(n)) for n in sorted(before)
             if n in now and now[n] != before[n]]
    if moved:
        bad.append("agente(s) mudaram de modelo desde %s: %s" % (BASE_TAG, "; ".join(moved)))
    # «um despacho sem modelo proprio que nao le o pin de um arquivo de agente
    # roda no modelo da sessao»: a declaracao pela forma do ADR-149 A3.3
    adr = " ".join((_read_text(repo, ADR149) or "").split())
    for frag in ADR149_SESSION_MODEL_DECL:
        if frag not in adr:
            bad.append("%s sem a declaracao %r (despacho sem modelo proprio roda no "
                       "modelo da sessao)" % (ADR149, frag))
    live, why = _read_json(repo, ".claude/settings.json")
    if live is not None and OPUS_ID not in (live.get("availableModels") or []):
        bad.append(".claude/settings.json: availableModels sem %s" % OPUS_ID)
    proc = subprocess.run(
        [sys.executable, GEN_AVAILABLE, "--check"], cwd=str(repo),
        stdout=subprocess.PIPE, stderr=subprocess.PIPE, universal_newlines=True)
    if proc.returncode != 0:
        bad.append("generate-available-models.py --check rc=%d (settings x ADR-149)"
                   % proc.returncode)
    tmp = pathlib.Path(tempfile.mkdtemp(prefix="relmeta142-veto."))
    try:
        for sub in ("home", "state", "tmpdir"):
            (tmp / sub).mkdir()
        prog = ("import json, sys; sys.path.insert(0, '.claude/hooks'); "
                "from _lib import agent_frontmatter as a; "
                "print(json.dumps(sorted(a.VETO_FLOOR_ALLOWED)))")
        proc = subprocess.run(
            [sys.executable, "-c", prog], cwd=str(repo), env=_probe_env(tmp),
            stdout=subprocess.PIPE, stderr=subprocess.PIPE, universal_newlines=True,
            timeout=60)
        try:
            floor = json.loads(proc.stdout.strip().splitlines()[-1])
        except Exception:
            floor = None
        if not isinstance(floor, list):
            bad.append("VETO_FLOOR_ALLOWED ilegivel em runtime (rc=%d)" % proc.returncode)
        elif OPUS_ID not in floor:
            bad.append("VETO_FLOOR_ALLOWED (runtime) sem %s" % OPUS_ID)
    finally:
        shutil.rmtree(str(tmp), ignore_errors=True)
    if bad:
        return False, "; ".join(bad)
    return True, ("pin %s nos settings enviados, working set (--check MATCH), piso de "
                  "VETO em runtime, %d agente(s) com o modelo da %s, despacho sem modelo "
                  "proprio no modelo da sessao declarado no ADR-149, fallback %s no "
                  "template base" % (OPUS_ID, len(before), BASE_TAG, OPUS_FALLBACK))


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
    tmp = pathlib.Path(tempfile.mkdtemp(prefix="relmeta142-ccfloor."))
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


def _t54_table(repo: pathlib.Path) -> Tuple[Optional[dict], str]:
    """A tabela normativa de migracao do upgrade.sh (o que
    ``--print-settings-baselines`` imprime), lida do literal, sem executar."""
    text = _read_text(repo, UPGRADE_SH)
    if text is None:
        return None, "%s ausente" % UPGRADE_SH
    m = re.findall(r"(?ms)^%s='(.*?)'$" % re.escape(T54_VAR), text)
    if len(m) != 1:
        return None, "%s: %d literais %s (exigido: 1)" % (UPGRADE_SH, len(m), T54_VAR)
    try:
        d = json.loads(m[0])
    except Exception as exc:
        return None, "%s: %s ilegivel (%s)" % (UPGRADE_SH, T54_VAR, type(exc).__name__)
    return (d, "") if isinstance(d, dict) else (None, "%s nao e objeto" % T54_VAR)


def claim_ccfloor_effort(repo: pathlib.Path) -> Tuple[bool, str]:
    bad: List[str] = []
    for rel in (INSTALL_SH, UPGRADE_SH):
        bad.extend(_floor_probe(repo, rel))
    sup = _read_text(repo, SUPPORT_MD) or ""
    if not any(CC_MIN in ln and OPUS_ID in ln for ln in sup.splitlines()):
        bad.append("%s sem linha que cite Claude Code %s e %s" % (SUPPORT_MD, CC_MIN, OPUS_ID))
    for rel in FRESH_TEMPLATES:
        d, why = _read_json(repo, rel)
        if d is None:
            bad.append(why)
        elif d.get("effortLevel") != FRESH_EFFORT:
            bad.append("%s: effortLevel=%r (esperado %s)"
                       % (rel, d.get("effortLevel"), FRESH_EFFORT))
    t54, why = _t54_table(repo)
    if t54 is None:
        bad.append(why)
    else:
        mdl, eff = t54.get("model") or {}, t54.get("effortLevel") or {}
        if not (mdl.get("old") is None and mdl.get("new") == OPUS_ID
                and OPUS_FALLBACK in (mdl.get("superseded") or [])
                and mdl.get("requires_member_of") == "availableModels"):
            bad.append("%s: linha model da tabela nao troca %s -> %s (ausente ou enviado, "
                       "exigindo a lista de modelos): %r" % (UPGRADE_SH, OPUS_FALLBACK, OPUS_ID, mdl))
        if not (eff.get("new") == FRESH_EFFORT and eff.get("opt_in") is True
                and eff.get("on_migrate_of") == {"model": {OPUS_FALLBACK: "high"}}):
            bad.append("%s: linha effortLevel da tabela nao e opt-in %s com high na troca "
                       "a partir de %s: %r" % (UPGRADE_SH, FRESH_EFFORT, OPUS_FALLBACK,
                                               {k: eff.get(k) for k in ("new", "opt_in", "on_migrate_of")}))
    up = _read_text(repo, UPGRADE_SH) or ""
    if UPGRADE_OPT_IN_FLAG not in up:
        bad.append("%s sem a rota de opt-in %s" % (UPGRADE_SH, UPGRADE_OPT_IN_FLAG))
    sec = _changelog_section(repo)
    if not re.search(r"(?is)outranks[^.]{0,120}/effort", sec):
        bad.append("CHANGELOG [%s] nao declara que o effortLevel do projeto passa a valer "
                   "sobre o nivel salvo com /effort" % TARGET_BASE)
    if not re.search(r"(?i)\bnever\s+overwritten\b", sec):
        bad.append("CHANGELOG [%s] nao declara que um effortLevel definido nunca e "
                   "sobrescrito" % TARGET_BASE)
    if bad:
        return False, "; ".join(bad)
    return True, ("piso %s rodado contra um claude falso no install.sh e no upgrade.sh "
                  "(recusa abaixo e com sufixo colado, le so a linha (Claude Code), saida %s "
                  "no topo; override, ausencia, versao ilegivel e --version parado so avisam); "
                  "tabela do upgrade troca o pin e grava high; %s no template novo"
                  % (CC_MIN, CC_FLOOR_EXIT, FRESH_EFFORT))


def _semver(v: str) -> Tuple[int, int, int]:
    m = re.fullmatch(r"(\d+)\.(\d+)\.(\d+)", v.strip())
    if not m:
        raise ValueError(v)
    return int(m.group(1)), int(m.group(2)), int(m.group(3))


def claim_codex(repo: pathlib.Path) -> Tuple[bool, str]:
    d, why = _read_json(repo, CODEX_MANIFEST)
    if d is None:
        return False, why
    bad = []
    if d.get("package_version") != CODEX_VER:
        bad.append("%s: package_version=%r (esperado %s — o re-pin landou?)"
                   % (CODEX_MANIFEST, d.get("package_version"), CODEX_VER))
    pays = d.get("payloads")
    if not isinstance(pays, dict) or not pays or not all(
            isinstance(p, dict) and re.fullmatch(r"[0-9a-f]{64}", str(p.get("sha256", "")))
            for p in pays.values()):
        bad.append("%s: payloads sem sha256 de 64 hex" % CODEX_MANIFEST)
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
    if bad:
        return False, "; ".join(bad)
    return True, "manifesto pina %s por sha256; range do pin o admite" % CODEX_VER


def _repo_files_written_since(repo: pathlib.Path, t0: float) -> List[pathlib.Path]:
    """Arquivos do repositorio que a sonda pode ter escrito: nao rastreados
    (IGNORADOS inclusos: sem --exclude-standard) e rastreados modificados,
    com mtime depois do inicio da sonda."""
    out: List[pathlib.Path] = []
    for args in (("ls-files", "-z", "--others"), ("diff", "--name-only", "-z")):
        proc = subprocess.run(["git", "-C", str(repo)] + list(args),
                              stdout=subprocess.PIPE, stderr=subprocess.DEVNULL)
        if proc.returncode != 0:
            raise RuntimeError("git %s rc=%d no repositorio sondado" % (args[0], proc.returncode))
        for rel in proc.stdout.decode("utf-8", "surrogateescape").split("\0"):
            if not rel:
                continue
            p = repo / rel
            try:
                st = p.lstat()
            except OSError:
                continue
            if stat.S_ISREG(st.st_mode) and st.st_mtime >= t0 - 2:
                out.append(p)
    return out


def _json_docs(data: bytes) -> List[Any]:
    """O arquivo como UM documento JSON, ou como JSONL; o que nao e JSON sai."""
    try:
        text = data.decode("utf-8")
    except UnicodeDecodeError:
        return []
    try:
        return [json.loads(text)]
    except ValueError:
        pass
    docs = []
    for ln in text.splitlines():
        try:
            docs.append(json.loads(ln))
        except ValueError:
            continue
    return docs


def _dict_holds(doc: Any, sha: str, size: int) -> bool:
    """Algum objeto do documento guarda o sha256 E o tamanho (um inteiro) juntos."""
    stack = [doc]
    while stack:
        cur = stack.pop()
        if isinstance(cur, dict):
            vals = list(cur.values())
            if sha in vals and any(isinstance(v, int) and not isinstance(v, bool)
                                   and v == size for v in vals):
                return True
            stack.extend(vals)
        elif isinstance(cur, list):
            stack.extend(cur)
    return False


def claim_fn04(repo: pathlib.Path) -> Tuple[bool, str]:
    """Sonda de RUNTIME da classe da condicao 23 do GA da v1.4.1 (o caso do
    Workflow: o hook que roda antes da decisao de permissao).

    O hook roda como o harness o roda (stdin JSON, processo proprio), com
    HOME, estado e TMPDIR num diretorio temporario, para duas chamadas
    PreToolUse do Workflow: `scriptPath` ABSOLUTO fora do projeto e RELATIVO
    ao cwd dentro dele, cada um apontando para um canario com um token
    aleatorio PROPRIO. Nenhum PostToolUse vem (a chamada negada). Depois,
    cada lancamento e vinculado a mao (`ceo-launches.py bind`, que nao tira
    copia) e `relaunch <run> --out <arquivo>` tem de sair 7 sem criar o
    arquivo. Por fim sao varridos a arvore temporaria inteira (menos os
    canarios) e os arquivos do repositorio escritos durante a sonda
    (ignorados inclusos): um token em qualquer um = bytes persistidos
    (reprova). Controle POSITIVO por chamada contra verde-vacuo: o sha256 e
    o tamanho de CADA canario gravados juntos num objeto de registro."""
    hook, cli = repo / WORKFLOW_HOOK, repo / RELAUNCH_CLI
    for p, rel in ((hook, WORKFLOW_HOOK), (cli, RELAUNCH_CLI)):
        if p.is_symlink() or not p.is_file():
            return False, "%s ausente" % rel
    tmp = pathlib.Path(tempfile.mkdtemp(prefix="relmeta142-fn04."))
    try:
        proj, outside, outdir = tmp / "proj", tmp / "outside", tmp / "outdir"
        for p in (tmp / "home", tmp / "state", tmp / "tmpdir", proj / "wf", outside, outdir):
            p.mkdir(parents=True)
        tokens = ["RELMETA142-FN04-CANARY-%s" % secrets.token_hex(16) for _ in range(2)]
        bodies = [("// %s\nexport const meta = {};\n" % t).encode("ascii") for t in tokens]
        canaries = [outside / "canary-out.js", proj / "wf" / "canary-in.js"]
        for f, b in zip(canaries, bodies):
            f.write_bytes(b)
        shas = [hashlib.sha256(b).hexdigest() for b in bodies]
        env = _probe_env(tmp)
        env["CLAUDE_PROJECT_DIR"] = str(proj)
        calls = ({"scriptPath": str(canaries[0])}, {"scriptPath": "wf/canary-in.js"})
        t0 = time.time()
        for i, ti in enumerate(calls):
            ti = dict(ti)
            ti["args"] = {"relmeta142_probe": i}
            ev = {"hook_event_name": "PreToolUse", "tool_name": "Workflow",
                  "tool_input": ti, "session_id": "relmeta142-fn04-probe",
                  "tool_use_id": "toolu_relmeta142_probe_%d" % i, "cwd": str(proj)}
            try:
                proc = subprocess.run(
                    [sys.executable, str(hook)], input=json.dumps(ev), cwd=str(proj),
                    env=env, stdout=subprocess.PIPE, stderr=subprocess.PIPE,
                    universal_newlines=True, timeout=90)
            except subprocess.TimeoutExpired:
                return False, "o hook passou de 90 s na chamada %d" % i
            if proc.returncode != 0:
                return False, "o hook saiu rc=%d na chamada %d" % (proc.returncode, i)
        # o que a PreToolUse gravou, ANTES de qualquer outro passo tocar o estado
        leaked: List[str] = []
        scanned: List[pathlib.Path] = []

        def sweep() -> None:
            del scanned[:]
            for root in (tmp / "state", tmp / "home", tmp / "tmpdir", outdir, proj):
                for p in sorted(root.rglob("*")):
                    if p in canaries or p.is_symlink() or not p.is_file():
                        continue
                    scanned.append(p)
            scanned.extend(_repo_files_written_since(repo, t0))
            for p in scanned:
                data = p.read_bytes()
                if any(t.encode() in data for t in tokens):
                    rel = str(p.relative_to(tmp)) if tmp in p.parents else str(p)
                    if rel not in leaked:
                        leaked.append(rel)

        sweep()
        if leaked:
            return False, ("o PreToolUse gravou os bytes do scriptPath em %s — a cura do "
                           "FN-04 nao esta no HEAD" % ", ".join(leaked[:4]))
        docs = [(p, _json_docs(p.read_bytes())) for p in scanned]
        missing = [str(k) for k, (s, b) in enumerate(zip(shas, bodies))
                   if not any(_dict_holds(d, s, len(b)) for _p, ds in docs for d in ds)]
        if missing:
            return False, ("sonda VAZIA na(s) chamada(s) %s: nenhum registro guarda o sha256 "
                           "e o tamanho do canario — nada provado" % ", ".join(missing))
        idx = [p for p in scanned if p.name == "launches.jsonl"]
        if len(idx) != 1:
            return False, "%d indices launches.jsonl na arvore da sonda (exigido: 1)" % len(idx)
        rows = [r for r in _json_docs(idx[0].read_bytes())
                if isinstance(r, dict) and r.get("kind") == "launch"]
        if len(rows) != 2 or not all(isinstance(r.get("launch_id"), str) for r in rows):
            return False, "o indice tem %d lancamentos com id (exigido: 2)" % len(rows)
        for k, row in enumerate(rows):
            run_id = "wf_%s" % secrets.token_hex(4)
            out = outdir / ("relaunch-%d.js" % k)
            steps = ((["bind", row["launch_id"], run_id], 0),
                     (["relaunch", run_id, "--out", str(out)], 7))
            for argv, want in steps:
                try:
                    proc = subprocess.run(
                        [sys.executable, str(cli)] + argv, cwd=str(proj), env=env,
                        stdout=subprocess.PIPE, stderr=subprocess.PIPE,
                        universal_newlines=True, timeout=90)
                except subprocess.TimeoutExpired:
                    return False, "ceo-launches.py %s passou de 90 s" % argv[0]
                if proc.returncode != want:
                    return False, ("ceo-launches.py %s do lancamento %d saiu rc=%d (esperado %d): %s"
                                   % (argv[0], k, proc.returncode, want,
                                      proc.stderr.strip()[-200:]))
            if os.path.lexists(str(out)):
                return False, ("relaunch --out sem a copia do PostToolUse CRIOU %s"
                               % out.relative_to(tmp))
        sweep()
        if leaked:
            return False, ("bytes do scriptPath gravados depois do bind/relaunch em %s"
                           % ", ".join(leaked[:4]))
        return True, ("PreToolUse gravou sha256 e tamanho de cada canario sem os bytes "
                      "(fora e dentro do projeto; estado, HOME, TMPDIR e repo varridos); "
                      "relaunch sem a copia do PostToolUse saiu 7 sem criar o --out")
    finally:
        shutil.rmtree(str(tmp), ignore_errors=True)


def claim_relaunch(repo: pathlib.Path) -> Tuple[bool, str]:
    bad = []
    rc = git_rc(repo, "diff", "--quiet", BASE_TAG, "HEAD", "--", RELAUNCH_CLI)
    if rc == 0:
        bad.append("%s identico ao de %s (a opcao B nao landou)" % (RELAUNCH_CLI, BASE_TAG))
    elif rc != 1:  # 1 = difere; qualquer outro = o git nao respondeu (nunca verde)
        bad.append("git diff %s..HEAD de %s falhou (rc=%d)" % (BASE_TAG, RELAUNCH_CLI, rc))
    src = _read_text(repo, RELAUNCH_CLI) or ""
    if "os.link(" not in src:
        bad.append("%s sem a publicacao por link" % RELAUNCH_CLI)
    if not (repo / RELAUNCH_PLAN).is_file():
        bad.append("%s ausente" % RELAUNCH_PLAN)
    doc = _read_text(repo, RELAUNCH_DOC) or ""
    if "`relaunch --out` (declared)" not in doc:
        bad.append("%s sem a secao de limites declarados do relaunch --out" % RELAUNCH_DOC)
    if bad:
        return False, "; ".join(bad)
    return True, "opcao B no HEAD (link, plano e limites declarados)"


def claim_fastlane(repo: pathlib.Path) -> Tuple[bool, str]:
    bad = []
    for rel in FASTLANE_TOOLS:
        p = repo / rel
        if p.is_symlink() or not p.is_file():
            bad.append("%s ausente" % rel)
    for reg in HOOK_REGISTRIES:
        t = _read_text(repo, reg) or ""
        for rel in FASTLANE_TOOLS:
            if os.path.basename(rel) in t:
                bad.append("%s registra %s (a headline diz sem hook)"
                           % (reg, os.path.basename(rel)))
    if bad:
        return False, "; ".join(bad)
    return True, "as tres ferramentas no HEAD, nenhuma registrada como hook"


def _changelog_section(repo: pathlib.Path) -> str:
    return _section(_read_text(repo, CHANGELOG) or "", TARGET_BASE)


def _known_open_subsections(sec: str) -> List[str]:
    subs = []
    for ko in re.finditer(r"(?m)^###[^\n]*Known-open[^\n]*\n", sec):
        tail = sec[ko.end():]
        nxt = re.search(r"(?m)^#{2,3} ", tail)
        subs.append(tail[: nxt.start()] if nxt else tail)
    return subs


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
    if not re.search(r"(?i)\bno\s+release\s+(?:is\s+)?assigned\b|\bnot\s+assigned\s+to\s+"
                     r"(?:a|any)\s+release\b|\bunassigned\b", kosec):
        return ("a subsecao Known-open da [%s] que re-declara o anexo da v1.4.0 nao diz que "
                "nenhuma release esta atribuida a cura (PLAN-193 OQ-3)" % TARGET_BASE)
    # pela FORMA: re-declarar sem prometer = nenhuma versao DO FRAMEWORK (mesmo
    # major da release) depois desta nomeada ali. Versoes de outras ferramentas
    # (Claude Code, Codex, gpg, git) tem outro major e nao sao promessa.
    tgt = _semver(TARGET_BASE)
    later = sorted({v for v in re.findall(r"\b(\d+\.\d+\.\d+)\b", kosec)
                    if _semver(v)[0] == tgt[0] and _semver(v) > tgt})
    if later:
        return ("a subsecao Known-open da [%s] que re-declara o anexo nomeia versao "
                "posterior do framework (%s) — o plano nao carrega essa cura"
                % (TARGET_BASE, ", ".join(later)))
    return None


def claim_fn04_all(repo: pathlib.Path) -> Tuple[bool, str]:
    ok, detail = claim_fn04(repo)
    if not ok:
        return ok, detail
    # «a classe nao se esgota nesse hook»: a mesma declaracao, pela forma, no
    # sentinel que o Owner assina para a cura (o residual dele)
    sent = " ".join((_read_text(repo, FN04_SENTINEL) or "").split())
    if FN04_CLASS_NOT_EXHAUSTED not in sent:
        return False, ("%s ausente ou sem o residual %r — a headline diz que a classe nao "
                       "se esgota no hook do Workflow" % (FN04_SENTINEL, FN04_CLASS_NOT_EXHAUSTED))
    subs = _known_open_subsections(_changelog_section(repo))
    if not any(re.search(r"launches/", s) and re.search(
            r"(?i)\b(?:stay|stays|remain|remains|removes\s+none|not\s+removed)\b", s)
               for s in subs):
        return False, ("CHANGELOG [%s]: nenhum Known-open declara que as copias gravadas "
                       "pela v%s ficam em launches/" % (TARGET_BASE, PREV_BASE))
    return True, detail + ("; copias da v%s em launches/ declaradas no Known-open; o sentinel "
                           "do FN-04 declara que a classe nao se esgota no hook" % PREV_BASE)


def claim_annex(repo: pathlib.Path) -> Tuple[bool, str]:
    if not (repo / V140_ENVELOPE).is_file():
        return False, "%s ausente" % V140_ENVELOPE
    sec = _changelog_section(repo)
    why = _annex_problem(sec)
    if why is not None:
        return False, why
    if not re.search(r"cleanupPeriodDays", sec) or not re.search(r"(?i)\bdefault\s+30\b", sec):
        return False, ("CHANGELOG [%s] nao cita cleanupPeriodDays com o padrao de 30 dias"
                       % TARGET_BASE)
    if not any(re.search(r"(?is)\baudit\b.{0,200}\bdelet", s) and re.search(r"(?i)\bno\s+plan\b", s)
               for s in _known_open_subsections(sec)):
        return False, ("CHANGELOG [%s]: nenhum Known-open declara que a limpeza do Claude Code "
                       "pode apagar o log de auditoria sem plano de cura" % TARGET_BASE)
    return True, ("envelope da v1.4.0 presente; o Known-open da [%s] re-declara o anexo sem "
                  "release atribuida e declara a limpeza do log de auditoria sem plano"
                  % TARGET_BASE)


CLAIMS = (
    ("opus55", "Opus 5.5 padrao + piso de VETO", claim_opus),
    ("ccfloor", "piso do Claude Code + esforco no install e no upgrade", claim_ccfloor_effort),
    ("codex", "pin do Codex CLI", claim_codex),
    ("fn04", "FN-04: sem bytes do scriptPath antes da permissao", claim_fn04_all),
    ("relaunch", "relaunch --out por link", claim_relaunch),
    ("fastlane", "ferramentas da via expressa", claim_fastlane),
    ("annex", "parte honesta: anexo da v1.4.0 e log de auditoria", claim_annex),
)


def check_claims(repo: pathlib.Path) -> List[Tuple[str, str, bool, str]]:
    out = []
    for key, name, fn in CLAIMS:
        try:
            ok, detail = fn(repo)
        except Exception as exc:  # uma ancora que quebra NAO passa
            ok, detail = False, "a ancora quebrou (%s: %s)" % (type(exc).__name__, exc)
        out.append((key, name, ok, detail))
    return out


def assert_claims(repo: pathlib.Path) -> List[Tuple[str, str, bool, str]]:
    res = check_claims(repo)
    bad = [r for r in res if not r[2]]
    if bad:
        die("a headline afirma o que o HEAD nao sustenta:\n  %s\n"
            "Lande a peca que falta (ordem da manha) e re-derive. Se ela ficou de "
            "fora de proposito, a headline tem de mudar ANTES: edite RELEASE_HEADLINE "
            "e CLAIMS neste derivador, commite e re-derive."
            % "\n  ".join("[%s] %s: %s" % (k, n, d) for k, n, _ok, d in bad))
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
        '# .claude/plans/PLAN-193/relmeta/apply-relmeta142-edits.py\n'
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


def edit_probe_yes(text: str) -> str:
    """`--yes` no probe de assinatura do preflight + o comentario do porque."""
    for anchor, what in ((PROBE_MKTEMP, "mktemp do probe"),
                         (PROBE_GPG_OLD, "comando gpg do probe")):
        if text.count(anchor) != 1:
            die("ancora do %s ausente ou nao unica em %s" % (what, RELEASE_SH))
    if "--yes" in text:
        die("%s ja carrega --yes — esta edicao ja foi aplicada?" % RELEASE_SH)
    text = text.replace(PROBE_MKTEMP, PROBE_COMMENT + PROBE_MKTEMP, 1)
    return text.replace(PROBE_GPG_OLD, PROBE_GPG_NEW, 1)


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

    doc_old = ("    Trem %s (re-pinado na cerimonia relmeta-141, PLAN-192): derivado por\n"
               % PREV_BASE)
    if out.count(doc_old) != 1:
        die("teste de escopo: ancora do docstring do trem anterior ausente ou nao unica")
    doc_new = (
        "    Trem %s (re-pinado na cerimonia relmeta-142, PLAN-193): derivado por\n"
        "    apply-relmeta142-edits.py de `git log %s..HEAD` DEPOIS de todos os\n"
        "    lands da release; o trem da %s vira assercao negativa.\n"
        "\n" % (TARGET_BASE, BASE_TAG, PREV_BASE))
    return out.replace(doc_old, doc_new + doc_old, 1)


def edit_add_probe_test(text: str) -> str:
    if text.count(PROBE_TEST_ANCHOR) != 1:
        die("teste: ancora do controle de contagem de sitios ausente ou nao unica")
    if "def test_preflight_signature_probe_answers_its_own_overwrite_question" in text:
        die("teste: o controle do --yes ja existe — esta edicao ja foi aplicada?")
    return text.replace(PROBE_TEST_ANCHOR, PROBE_TEST + PROBE_TEST_ANCHOR, 1)


def current_scope(release_text: str) -> str:
    m = re.findall(r'(?m)^RELEASE_SCOPE="([^"\n]*)"$', release_text)
    if len(m) != 1:
        die("driver com %d linhas RELEASE_SCOPE de uma linha (exigido: 1)" % len(m))
    return m[0]


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
        # «as of v1.4.1» so segue verdadeiro se o preambulo e EXATAMENTE o que a
        # v1.4.1 publicou (e as contagens, conferidas acima, nao mudaram)
        if label != PREV_BASE:
            die("o claim de contagens do preambulo diz v%s; esperado v%s (ou v%s "
                "intocado desde a tag)" % (label, TARGET_BASE, PREV_BASE))
        old = run(repo, "show", "%s:%s" % (BASE_TAG, CHANGELOG))
        if _preamble(old) != preamble:
            die("o preambulo do CHANGELOG diz v%s mas nao e o que a %s publicou — "
                "atualize o rotulo para v%s" % (PREV_BASE, BASE_TAG, TARGET_BASE))
    sec = _section(text, TARGET_BASE)
    # a anotacao da tag termina em «See CHANGELOG.md [1.4.2]»: a entrada que
    # ela aponta tem de estar DATADA, como a de toda rc anterior
    head = sec.splitlines()[0] if sec else ""
    if not re.fullmatch(r"## \[%s\] [-—] \d{4}-\d{2}-\d{2}\s*" % re.escape(TARGET_BASE), head):
        die("a secao [%s] do CHANGELOG nao esta datada (%r; exigido '## [%s] - AAAA-MM-DD'): "
            "a anotacao da tag aponta para ela" % (TARGET_BASE, head, TARGET_BASE))
    why = _annex_problem(sec)
    if why is not None:
        die(why)
    return label


def main() -> int:
    ap = argparse.ArgumentParser()
    ap.add_argument("--repo", required=True)
    g = ap.add_mutually_exclusive_group()
    g.add_argument("--check", action="store_true")
    g.add_argument("--claims-only", action="store_true")
    a = ap.parse_args()
    repo = pathlib.Path(a.repo).resolve()
    if not (repo / ".git").exists():
        die("%s nao parece a raiz de um repositorio" % repo)

    if a.claims_only:
        res = check_claims(repo)
        for key, name, ok, detail in res:
            sys.stdout.write("%s  [%s] %s: %s\n"
                             % ("PASS" if ok else "FAIL", key, name, detail))
        return 0 if all(r[2] for r in res) else 1

    assert_base_tag(repo)
    plans, adrs = derive_train(repo)
    counts = derive_counts(repo)
    scope = scope_string(plans, adrs)
    block = build_per_release_block(scope)
    assert_block_is_inert(block)
    assert_no_bare_semver(block)
    assert_no_site_count_or_publish_claim(block)

    rp, cp, mp, tp = (repo / RELEASE_SH, repo / CHANGELOG, repo / MANIFEST,
                      repo / SCOPE_TEST)
    for p in (rp, cp, mp, tp):
        if p.is_symlink() or not p.is_file():
            die("alvo nao e arquivo regular: %s" % p)

    label = assert_changelog_ready(repo, cp.read_text(encoding="utf-8"), counts)
    claims = assert_claims(repo)

    rel_old = rp.read_text(encoding="utf-8")
    old_scope = current_scope(rel_old)
    rel_new = edit_probe_yes(edit_release_sh(rel_old, block))
    if current_scope(rel_new) != scope:
        die("o escopo gravado no driver nao e o derivado")
    rel_sha = hashlib.sha256(rel_new.encode("utf-8")).hexdigest()
    man_old = mp.read_text(encoding="utf-8")
    man_new = edit_manifest(man_old, rel_sha)
    changed = [k for k, (x, y) in enumerate(zip(man_old.splitlines(),
                                                man_new.splitlines())) if x != y]
    if len(changed) != 1 or len(man_old.splitlines()) != len(man_new.splitlines()):
        die("o re-pin do manifesto mudou %d linhas (exigido: 1)" % len(changed))
    tst_new = edit_add_probe_test(
        edit_scope_test(tp.read_text(encoding="utf-8"), old_scope, scope, block))

    applied = 0
    if not a.check:
        rp.write_text(rel_new, encoding="utf-8")
        mp.write_text(man_new, encoding="utf-8")
        tp.write_text(tst_new, encoding="utf-8")
        applied = EDIT_COUNT_DECLARED  # bloco + --yes + manifesto + re-pin + controle
        on_disk = hashlib.sha256(rp.read_bytes()).hexdigest()
        if on_disk != rel_sha:
            die("sha de release.sh em disco (%s) != o gravado no manifesto (%s)"
                % (on_disk, rel_sha))

    sys.stdout.write("scope: %s\n" % scope)
    sys.stdout.write("counts: %s (rotulo do preambulo: v%s)\n"
                     % (json.dumps(counts, sort_keys=True), label))
    for key, name, _ok, detail in claims:
        sys.stdout.write("claim PASS [%s] %s: %s\n" % (key, name, detail))
    sys.stdout.write(
        "release.sh sha256 (pos-edicao): %s\n"
        "edits: %d/%d (CHANGELOG: pre-condicao CONFERIDA, nao escrita)%s\n"
        % (rel_sha, applied, EDIT_COUNT_DECLARED,
           "  (--check: NADA escrito)" if a.check else ""))
    return 0


if __name__ == "__main__":
    sys.exit(main())
