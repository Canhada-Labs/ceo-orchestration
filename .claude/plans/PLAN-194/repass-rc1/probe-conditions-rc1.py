#!/usr/bin/env python3
"""Sonda das condicoes da v1.4.3-rc.1 (PLAN-194): cada afirmacao sobre CODIGO do
CONDITIONS-rc1.md e conferida aqui contra um commit, ANTES do re-pass.

  python3 probe-conditions-rc1.py --root DIR --base REV --head REV [--sizes] [--only ID,..]

--root  checkout onde os comportamentos rodam (o worktree do candidato no runner;
        a arvore viva no G0 do OWNER-RC1-CUT.sh). Os arquivos RASTREADOS da arvore
        tem de ser os de --head (conferido; a sonda recusa uma arvore que difere).
--base  a tag base resolvida (v1.4.2^{commit}); --head o commit sob revisao.
--sizes projeta o payload de cada parte com as funcoes do PROPRIO runner (pathspec,
        rotulo, cobertura, cabecalho do prompt) e recusa uma parte acima de
        MAX_RAW_BYTES - 16 KiB, sem arquivo, ou com menos de 50 linhas de diff.
--only  so os ids pedidos; um id desconhecido e recusa (rc 2), nunca verde vacuo.

Saida: uma linha `OK|FAIL <id>: <o que>` por afirmacao, a linha MAPA (que ids conferem cada
condicao) e a linha SONDA; rc 0 = todas OK, rc 1 = alguma FALSA (o re-pass NAO pode rodar
com este texto: corrija o codigo ou as condicoes), rc 2 = a sonda nao conseguiu medir
(infraestrutura; nunca vira OK). Nenhuma escrita fora de um diretorio temporario do
sistema, removido na saida; nenhum .pyc (PYTHONDONTWRITEBYTECODE).
DERIVADO por .claude/plans/PLAN-194/derive-kit-143.py — NAO edite a mao. stdlib, >= 3.9.
"""
from __future__ import annotations

import argparse
import ast
import hashlib
import json
import os
import re
import shutil
import subprocess
import sys
import tempfile
from pathlib import Path
from typing import Callable, Dict, List, Optional, Sequence, Tuple

sys.dont_write_bytecode = True

CODEX_PIN = "0.160.0"
RELEASE_VERSION = "1.4.3"
MAX_RAW_BYTES = 262000
SIZE_MARGIN = 16384
MIN_DIFF_LINES = 50
EV_REL = ".claude/plans/PLAN-194/repass-rc1"
RUNNER_REL = EV_REL + "/run-rc1-repass.sh"
CONDITIONS_REL = EV_REL + "/CONDITIONS-rc1.md"
PLAN_FILE_REL = ".claude/plans/PLAN-194-maintenance-train-v1-4-3.md"
PLAN_DECISIONS_HEAD = "## Decisões do Owner — S362 (2026-10-02)"
GA_ENVELOPE = ".claude/governance/pair-rail-verdict-v1.4.2.md"
RC_ENVELOPE = ".claude/governance/pair-rail-verdict-v1.4.2-rc.1.md"
GA_CONDITIONS = ".claude/plans/PLAN-193/repass-ga/CONDITIONS-ga.md"
PIN_SENTINEL = ".claude/plans/PLAN-194/codex-pin-0160/pin-0160-approved.md"
NPM_PUBLISH_WF = ".github/workflows/npm-publish.yml"
RC_PROOF_JOB_ID = "rc-toolchain-proof"
RC_PROOF_JOB_NAME = "RC toolchain proof (no publish)"
# Os arquivos que os vereditos da v1.4.0 (PLAN-169) citam e que mudam nesta faixa: a
# condicao 1 os declara pela FORMA. As classes sao enumeradas AQUI (codigo), nunca no
# texto assinado.
V140_VERDICT_DIRS = (".claude/plans/PLAN-169/repass-rc1", ".claude/plans/PLAN-169/repass-ga")
V140_VERSION_SITES = frozenset([
    "VERSION", "pyproject.toml", "npm/package.json", ".claude/.framework-version",
    ".claude-plugin/plugin.json", ".claude-plugin/marketplace.json"])
V140_TEXT_RE = re.compile(
    r"^(?:CHANGELOG|README(?:\.[A-Za-z-]+)?|INSTALL|SECURITY|VERSIONING|SBOM|SUPPORT)\.md$"
    r"|^npm/README\.md$|^docs/(?!research/)[^/]+\.md$")
V140_SETTINGS_RE = re.compile(r"^templates/settings/[^/]+\.json$")
V140_SCRIPTS = frozenset(["scripts/upgrade.sh", "scripts/install.sh"])
V140_WORKFLOWS_RE = re.compile(r"^\.github/workflows/[^/]+\.yml$")
V140_HOOKS_RE = re.compile(r"^\.claude/hooks/(?!tests/).+\.py$")
V140_TESTS_RE = re.compile(r"(?:^|/)tests/")
GOV_ALLOWED = frozenset([".claude/governance/codex-cli-pin.txt",
                         ".claude/governance/codex-cli-pin-manifest.json",
                         ".claude/governance/gate-scripts-manifest.txt",
                         ".claude/governance/npm-trusted-publisher.txt"])
LOCAL_ALLOWED = frozenset([".claude/scripts/local/release.sh"])
README_REL = EV_REL + "/README-rc1.md"
CHANGELOG = "CHANGELOG.md"
# A marca do conteudo provisorio do K1 (derive-kit-143.py): nunca num corte (C17). Escrita pelo
# derivador a partir da constante dele (uma fonte so).
PROVISIONAL_MARK = "CONTEÚDO PROVISÓRIO (derivação K1)"
# Condicoes 1 e 3: o CASO da condicao 67 da v1.4.0-rc.1 (o verificador AST e o da relmeta-143).
AUDIT_LOG = ".claude/hooks/audit_log.py"
COND67_DECL = "67. **`append_entry` lê o predecessor e calcula o HMAC FORA do lock**"
V140_ENVELOPES = (".claude/governance/pair-rail-verdict-v1.4.0-rc.1.md",
                  ".claude/governance/pair-rail-verdict-v1.4.0.md")
CURE67_PHRASES = ("This retires signed condition 67 of v1.4.0-rc.1",
                  "This release cures one of them: signed condition 67",
                  "The condition-67 cure has declared limits",
                  # os limites que a condicao 3 cita, entre eles (o texto do Known-open)
                  "Breaks the race already wrote stay",
                  "Writers that resolve different locks for the same log still do not exclude each other",
                  "The first mint of the per-project HMAC key is still not exclusive",
                  "Under lock saturation")
# Condicoes 2 e 4: o P2 da parte 3 do re-pass do GA v1.4.2 (o ledger de forma errada).
DRIFT_REL = ".claude/scripts/check-substrate-drift.py"
GA_P2_VERDICT = ".claude/plans/PLAN-193/repass-ga/verdict-ga-3.txt"
GA_P2_TITLE = "Malformed ledger discards already-detected Codex drift"
GA_P2_PHRASES = ("This cures a P2 finding of the v1.4.2 GA re-pass",
                 "`/ceo-boot` does not run this tool", "CC_LEDGER_UNREADABLE", "COMPONENT_CHECK_ERROR")
# Condicoes 7 e 8: o exemplo de upgrade do INSTALL.md durante o hold, e o adapter intacto (D-10).
INSTALL_PIN_RE = r"--pin v([0-9]+\.[0-9]+\.[0-9]+)([^\s`]*)"
BUMP_SITES_REL = ".claude/scripts/local/_release_bump_sites.py"
BUMP_SITE_INSTALL = '("INSTALL.md", PLAIN, r"(--pin v)" + SEMVER)'
ADAPTER_REL = ".claude/hooks/_lib/adapters/live/claude.py"


class Infra(Exception):
    """A sonda nao conseguiu medir: rc 2, nunca OK."""


def run(cmd: Sequence[str], cwd: Optional[str] = None, env: Optional[Dict[str, str]] = None,
        stdin: Optional[bytes] = None, timeout: int = 300) -> subprocess.CompletedProcess:
    try:
        return subprocess.run(list(cmd), cwd=cwd, env=env, input=stdin, stdout=subprocess.PIPE,
                              stderr=subprocess.PIPE, timeout=timeout)
    except (OSError, subprocess.TimeoutExpired) as exc:
        raise Infra("%s: %s" % (cmd[0], exc))


class Tree:
    def __init__(self, root: str, base: str, head: str) -> None:
        # ABSOLUTO: os comportamentos rodam com outro cwd (um --root relativo apontaria
        # para dentro do diretorio temporario do ensaio).
        self.root = os.path.abspath(root)
        self.base = base
        self.head = head

    def git(self, *args: str) -> str:
        p = run(["git", "-C", self.root] + list(args))
        if p.returncode != 0:
            raise Infra("git %s: rc %d: %s" % (" ".join(args[:3]), p.returncode,
                                               p.stderr.decode("utf-8", "replace")[:200]))
        return p.stdout.decode("utf-8", "surrogateescape")

    def show(self, rev: str, path: str) -> Optional[str]:
        p = run(["git", "-C", self.root, "show", "%s:%s" % (rev, path)])
        if p.returncode != 0:
            return None
        return p.stdout.decode("utf-8", "surrogateescape")

    def changed(self, *pathspec: str) -> List[str]:
        out = self.git("diff", "--name-only", "--no-renames", self.base, self.head, "--", *pathspec)
        return sorted(ln for ln in out.splitlines() if ln)

    def path(self, rel: str) -> Path:
        return Path(self.root) / rel


def _norm(text: str) -> str:
    return " ".join(text.split())


def _env(extra: Optional[Dict[str, str]] = None) -> Dict[str, str]:
    env = {k: v for k, v in os.environ.items()
           if not k.startswith(("CEO_", "CLAUDE_")) and k not in ("PYTHONPATH",)}
    env["PYTHONDONTWRITEBYTECODE"] = "1"
    if extra:
        env.update(extra)
    return env


# ---------------------------------------------------------------------------
# afirmacoes
# ---------------------------------------------------------------------------
def c0_tree(t: Tree) -> str:
    """A arvore onde os comportamentos rodam e o commit sob revisao."""
    if t.git("rev-parse", "HEAD").strip() != t.git("rev-parse", t.head).strip():
        raise AssertionError("o HEAD de %s nao e o commit sob revisao" % t.root)
    dirty = [ln for ln in t.git("status", "--porcelain=v1", "--untracked-files=no").splitlines()
             if ln and not ln[3:].startswith(".claude/plans/")]
    if dirty:
        raise AssertionError("arquivo rastreado difere do commit: %s" % ", ".join(d[3:] for d in dirty[:5]))
    anc = run(["git", "-C", t.root, "merge-base", "--is-ancestor", t.base, t.head])
    if anc.returncode == 1:
        raise AssertionError("a base %s nao e ancestral do commit sob revisao" % t.base[:12])
    if anc.returncode != 0:
        raise Infra("git merge-base --is-ancestor rc %d" % anc.returncode)
    return "arvore == %s; base ancestral" % t.head[:12]


def c0_npm_rc(t: Tree) -> str:
    wf = t.show(t.head, ".github/workflows/npm-publish.yml") or ""
    ifs = [ln.strip() for ln in _code_lines(_job_block(wf, "publish") or "") if re.match(r"^    if:", ln)]
    if ifs != ["if: \"!contains(github.ref, '-rc.')\""]:
        raise AssertionError("o job publish do npm-publish.yml nao pula mais as tags -rc. (if: %r)" % ifs)
    return "a rc nao publica no npm (npm-publish.yml pula -rc.)"


def _job_block(wf: str, job_id: str) -> Optional[str]:
    """O bloco do job `<job_id>:` (indentado 2 espacos sob `jobs:`), ou None."""
    m = re.search(r"(?m)^  %s:[ \t]*\n" % re.escape(job_id), wf)
    if not m:
        return None
    rest = wf[m.end():]
    nxt = re.search(r"(?m)^  [A-Za-z0-9_-]+:[ \t]*$|^[^ \t\n#]", rest)
    return wf[m.start():m.end() + (nxt.start() if nxt else len(rest))]


def _code_lines(block: str) -> List[str]:
    """As linhas do bloco fora de comentario (YAML: `#` no inicio, depois de espacos)."""
    return [ln for ln in block.splitlines() if ln.strip() and not ln.strip().startswith("#")]


def _toolchain_parity(wf: str) -> List[str]:
    """O que impede a prova da rc de divergir do toolchain do publish: as duas variaveis
    definidas UMA vez no `env:` do workflow, lidas pelos DOIS jobs pelas mesmas linhas e
    redefinidas por nenhum, e os dois jobs na mesma imagem declarada (`ubuntu-latest`)."""
    bad = []
    top = re.search(r"(?m)^env:[ \t]*\n((?:[ \t]+[^\n]*\n|[ \t]*\n)+)", wf)
    for var in ("PUBLISH_NODE_MAJOR", "PUBLISH_NPM_VERSION"):
        defs = re.findall(r"(?m)^[ \t]+%s:" % var, wf)
        if not top or not re.search(r"(?m)^  %s:[ \t]*\S" % var, top.group(1)) or len(defs) != 1:
            bad.append("%s nao e definida exatamente uma vez, no env: do workflow (%d definicao(oes))"
                       % (var, len(defs)))
    for job in ("publish", RC_PROOF_JOB_ID):
        blk = _job_block(wf, job)
        code = [ln.strip() for ln in _code_lines(blk or "")]
        if blk is None:
            bad.append("o workflow sem o job %s" % job)
            continue
        for line in ("node-version: ${{ env.PUBLISH_NODE_MAJOR }}",
                     'npm install -g "npm@${PUBLISH_NPM_VERSION}"', "runs-on: ubuntu-latest"):
            if code.count(line) != 1:
                bad.append("o job %s nao tem exatamente uma linha %r" % (job, line))
        # uma redefinicao por $GITHUB_ENV muda os passos seguintes sem chave YAML nenhuma
        for ln in code:
            if "GITHUB_ENV" in ln and ("PUBLISH_NODE_MAJOR" in ln or "PUBLISH_NPM_VERSION" in ln):
                bad.append("o job %s redefine o toolchain por $GITHUB_ENV (%r)" % (job, ln[:80]))
    return bad


def c17_final_text(t: Tree) -> str:
    """Cabecalho: as condicoes e o README do candidato sao o conteudo FINAL da release (nunca
    o provisorio do K1, que o derivador so escreve com --provisional)."""
    for rel in (CONDITIONS_REL, README_REL):
        txt = t.show(t.head, rel)
        if txt is None:
            raise AssertionError("%s ausente" % rel)
        if PROVISIONAL_MARK in txt:
            raise AssertionError("%s carrega a marca do conteudo provisorio (%r)" % (rel, PROVISIONAL_MARK))
    return "as condicoes e o README do kit sao o conteudo final (sem a marca do provisorio do K1)"


def c0_rc_proof(t: Tree) -> str:
    """Condicao 6: o job da prova do toolchain da rc (W4) — nome, gatilho, permissoes,
    nenhum caminho de credencial ou de escrita no registry, e a paridade de toolchain com o
    job do publish."""
    wf = t.show(t.head, NPM_PUBLISH_WF)
    if wf is None:
        raise AssertionError("%s ausente" % NPM_PUBLISH_WF)
    blk = _job_block(wf, RC_PROOF_JOB_ID)
    if blk is None:
        raise AssertionError("%s sem o job %s (a W4 nao landou?)" % (NPM_PUBLISH_WF, RC_PROOF_JOB_ID))
    code = _code_lines(blk)
    names = [ln.split(":", 1)[1].strip() for ln in code if re.match(r"^    name:", ln)]
    if names != [RC_PROOF_JOB_NAME]:
        raise AssertionError("o job %s se chama %r (o passo 18 exige %r)" % (RC_PROOF_JOB_ID, names, RC_PROOF_JOB_NAME))
    ifs = [ln.split(":", 1)[1].strip() for ln in code if re.match(r"^    if:", ln)]
    if ifs != ["contains(github.ref, '-rc.')"]:
        raise AssertionError("o job %s nao roda so nas tags -rc. (if: %r)" % (RC_PROOF_JOB_ID, ifs))
    perm = re.search(r"(?m)^    permissions:[ \t]*\n((?:      [^\n]*\n|[ \t]*#[^\n]*\n)+)", blk)
    plines = _code_lines(perm.group(1)) if perm else []
    if [ln.strip() for ln in plines] != ["contents: read"]:
        raise AssertionError("o job %s tem permissions %r (a condicao 6 diz: so contents: read)"
                             % (RC_PROOF_JOB_ID, [ln.strip() for ln in plines]))
    joined = "\n".join(code)
    for bad, why in (("id-token", "uma permissao de token OIDC"), ("secrets.", "um segredo"),
                     ("\n    environment:", "um environment")):
        if bad in "\n" + joined:
            raise AssertionError("o job %s cita %s (%r)" % (RC_PROOF_JOB_ID, why, bad))
    if re.search(r"\bnpm\s+publish\b", joined):
        raise AssertionError("um passo do job %s chama npm publish" % RC_PROOF_JOB_ID)
    par = _toolchain_parity(wf)
    if par:
        raise AssertionError("paridade de toolchain com o publish (condicao 6): %s" % "; ".join(par))
    return ("job %s «%s»: so nas tags -rc., permissions contents: read, sem id-token/environment/secrets, "
            "sem npm publish; Node e npm das MESMAS variaveis do workflow que o publish (PUBLISH_NODE_MAJOR, "
            "PUBLISH_NPM_VERSION), ambos em ubuntu-latest" % (RC_PROOF_JOB_ID, RC_PROOF_JOB_NAME))


def c1_annex(t: Tree) -> str:
    env = _norm(t.show(t.head, GA_ENVELOPE) or "")
    for need in ("release_tag: v1.4.2 ", "O anexo P1 da v1.4.0 segue ABERTO", "nenhuma versão está prometida"):
        if need not in env + " ":
            raise AssertionError("o envelope do GA (%s) nao carrega %r" % (GA_ENVELOPE, need))
    if t.show(t.head, ".claude/governance/pair-rail-verdict-v1.4.0.md") is None:
        raise AssertionError("envelope da v1.4.0 ausente")
    # arquivos citados pelos vereditos da v1.4.0 que mudam na faixa: todos numa classe
    texts: List[str] = []
    for d in V140_VERDICT_DIRS:
        for name in t.git("ls-tree", "--name-only", t.head, d + "/").splitlines():
            if re.search(r"/verdict-[^/]*\.txt$", name):
                texts.append(t.show(t.head, name) or "")
    if len(texts) != 14:
        raise AssertionError("%d vereditos da v1.4.0 (esperado 14)" % len(texts))
    hits = []
    for p in t.changed():
        pat = re.compile(r"(?<![\w./-])" + re.escape(p) + r"(?![\w-])")
        if any(pat.search(x) for x in texts):
            hits.append(p)
    stray = [p for p in hits if not (p in V140_VERSION_SITES or V140_TEXT_RE.match(p)
                                     or V140_SETTINGS_RE.match(p) or p in V140_SCRIPTS
                                     or V140_WORKFLOWS_RE.match(p) or V140_HOOKS_RE.match(p)
                                     or V140_TESTS_RE.search(p) or p == "CLAUDE.md")]
    if stray:
        raise AssertionError("arquivo citado pelos vereditos da v1.4.0 muda fora das classes "
                             "declaradas: %s" % ", ".join(stray))
    if not hits:
        raise AssertionError("nenhum arquivo citado pelos vereditos da v1.4.0 muda na faixa — "
                             "a condicao 1 diz que mudam")
    return "anexo da v1.4.0 re-declarado (envelope do GA v1.4.2); %d citado(s) mudam, todos nas classes" % len(hits)


def _sha_at(t: Tree, rel: str) -> Optional[str]:
    p = run(["git", "-C", t.root, "show", "%s:%s" % (t.head, rel)])
    if p.returncode != 0:
        return None
    return hashlib.sha256(p.stdout).hexdigest()


def envelope_verdict_pins(t: Tree, rel: str) -> Tuple[List[Tuple[str, str]], List[Tuple[str, str]]]:
    """Os vereditos que um envelope assinado PINA, pela FORMA: (a) os `verdict-*.txt` do
    MANIFEST da evidencia (`delta_manifest`), cujo sha256 o envelope carrega
    (`delta_manifest_sha256`); (b) cada `` `verdict-*.txt` <sha256> `` escrito numa condicao,
    no diretorio da ultima `arquivada em `<dir>/`` que o precede. Devolve (manifesto,
    condicoes), cada uma como [(caminho, sha256 pinado)]."""
    env = t.show(t.head, rel)
    if env is None:
        raise AssertionError("%s ausente" % rel)
    dm = re.findall(r"(?m)^delta_manifest: (\S+)$", env)
    ds = re.findall(r"(?m)^delta_manifest_sha256: ([0-9a-f]{64})$", env)
    if len(dm) != 1 or len(ds) != 1:
        raise AssertionError("%s sem UM delta_manifest e UM delta_manifest_sha256" % rel)
    if _sha_at(t, dm[0]) != ds[0]:
        raise AssertionError("%s: o MANIFEST %s nao tem o sha256 pinado" % (rel, dm[0]))
    mdir = dm[0].rsplit("/", 1)[0]
    man = []
    for ln in (t.show(t.head, dm[0]) or "").splitlines():
        m = re.match(r"^([0-9a-f]{64})\s+\*?(verdict-[A-Za-z0-9._-]+\.txt)$", ln)
        if m:
            man.append(("%s/%s" % (mdir, m.group(2)), m.group(1)))
    marks = [(m.start(), m.group(1).rstrip("/"))
             for m in re.finditer(r"arquivada em `(\.claude/plans/[^`]+)`", env)]
    cond = []
    for m in re.finditer(r"`(verdict-[A-Za-z0-9._-]+\.txt)` ([0-9a-f]{64})", env):
        dirs = [d for pos, d in marks if pos < m.start()]
        if not dirs:
            raise AssertionError("%s: %s pinado sem o diretorio (`arquivada em`) antes dele"
                                 % (rel, m.group(1)))
        cond.append(("%s/%s" % (dirs[-1], m.group(1)), m.group(2)))
    return man, cond


def c2_carried(t: Tree) -> str:
    seen: Dict[str, str] = {}
    counts = []
    for rel in (GA_ENVELOPE, RC_ENVELOPE):
        man, cond = envelope_verdict_pins(t, rel)
        if not man:
            raise AssertionError("%s: o MANIFEST pinado nao lista veredito nenhum" % rel)
        for path, want in man + cond:
            got = _sha_at(t, path)
            if got is None:
                raise AssertionError("veredito pinado por %s ausente: %s" % (rel, path))
            if got != want:
                raise AssertionError("veredito pinado por %s nao tem o sha256 pinado: %s" % (rel, path))
            seen[path] = want
        for path, _w in man:
            lines = [ln for ln in (t.show(t.head, path) or "").splitlines() if ln.startswith("VERDICT:")]
            if len(lines) != 1 or not re.match(r"VERDICT: (GO|GO-WITH-CONDITIONS)(\s|$)", lines[0]):
                raise AssertionError("%s (no MANIFEST de %s) sem um VERDICT GO/GWC unico" % (path, rel))
        counts.append("%s: %d pelo MANIFEST + %d por condicao" % (rel.rsplit("/", 1)[1], len(man), len(cond)))
    gc = _norm(t.show(t.head, GA_CONDITIONS) or "")
    for need in ("13. **Os três P1 do anexo assinado da rc.1 seguem ABERTOS no GA",
                 "14. **Os P2 dos quatro vereditos da rc.1 seguem ABERTOS no GA",
                 "15. **O P2 da parte 1 dependia de a tag `v1.4.2` não existir"):
        if need not in gc:
            raise AssertionError("%s nao numera mais %r (a condicao 2 cita as condicoes 13 a 15 dele)"
                                 % (GA_CONDITIONS, need[:40]))
    return "%d veredito(s) pinado(s), todos presentes com o sha256 pinado (%s); GA: 13 a 15" % (
        len(seen), "; ".join(counts))


def c9_codex(t: Tree) -> str:
    man = json.loads(t.show(t.head, ".claude/governance/codex-cli-pin-manifest.json") or "{}")
    if man.get("package_version") != CODEX_PIN:
        raise AssertionError("o manifesto ADR-182 pina %r (esperado %s: o re-pin landou?)"
                             % (man.get("package_version"), CODEX_PIN))
    for rel in (PIN_SENTINEL, PIN_SENTINEL + ".asc"):
        if t.show(t.head, rel) is None:
            raise AssertionError("%s ausente (a cerimonia do re-pin nao landou)" % rel)
    return "manifesto ADR-182 pina %s; cerimonia do re-pin landada" % CODEX_PIN


def c13_route1(t: Tree) -> str:
    """Condicao 5: o runner do candidato resolve o codex SO pela rota 1 (D-4)."""
    runner = t.show(t.head, RUNNER_REL)
    if runner is None:
        raise AssertionError("%s ausente" % RUNNER_REL)
    code = "\n".join(ln for ln in runner.splitlines() if not ln.lstrip().startswith("#"))
    if re.search(r"\bnpx\s+(?:-y\b|--yes\b|-p\b|--package\b|@|\"?\$)|command -v npx\b", code):
        raise AssertionError("o runner do candidato ainda invoca npx (a rota 2 viva)")
    for need in ("e RECUSA NOMEADA nesta release (PLAN-194 D-4): nada foi baixado nem executado",
                 '--verify-codex-pin "$_glob"', 'CODEX_ROUTE="binario global (versao pinada, payload verificado)"',
                 # o residuo da condicao 5: o shim executa o lancador global (o `codex` do PATH)
                 'CODEX_LAUNCHER="$_glob"', "printf 'exec %s \"$@\"\\n' \"$(printf '%q' \"$CODEX_LAUNCHER\")\""):
        if need not in runner:
            raise AssertionError("o runner do candidato sem %r" % need)
    # LDR2-05: a atribuicao em QUALQUER forma nas linhas de codigo (export, declare, typeset,
    # readonly, local, `+=`, `${CODEX_LAUNCHER:=...}`, read, printf -v e unset), nao so a linha
    # que comeca por CODEX_LAUNCHER=.
    assign_re = re.compile(r"(?<![\w$])CODEX_LAUNCHER\+?=|\$\{CODEX_LAUNCHER:?=|"
                           r"\bread\b[^;&|\n]*\bCODEX_LAUNCHER\b|\bprintf\s+-v\s*CODEX_LAUNCHER\b|"
                           r"\bunset\b[^;&|\n]*\bCODEX_LAUNCHER\b")
    assigns = [ln.strip() for ln in runner.splitlines()
               if not ln.lstrip().startswith("#") and assign_re.search(ln)]
    if assigns != ['CODEX_LAUNCHER=""', 'CODEX_LAUNCHER="$_glob"']:
        raise AssertionError("o runner do candidato atribui CODEX_LAUNCHER %r (exigido: \"\" e depois $_glob, "
                             "so)" % assigns)
    i_or = runner.find('--verify-codex-pin "$_glob"')
    i_ex = runner.find('"$_glob" --version')
    if i_ex < 0 or i_or < 0 or i_ex < i_or:
        raise AssertionError("no runner do candidato o `--version` do codex global nao vem DEPOIS do oraculo")
    return ("o runner do candidato: rota 1 so (oraculo antes de executar), rota 2 recusa nomeada, nenhum npx; "
            "o shim executa o codex global do PATH (o lancador)")


def _plan_decision(plan: str, n: str) -> Optional[str]:
    """A linha `| D-<n> | ... |` da tabela de decisoes do Owner do plano."""
    i = plan.find(PLAN_DECISIONS_HEAD)
    if i < 0:
        return None
    m = re.search(r"(?m)^\| D-%s \|[^\n]*\|$" % re.escape(n), plan[i:])
    return m.group(0) if m else None


def c12_plan_decisions(t: Tree) -> str:
    """Toda decisao D-N que as condicoes citam esta na tabela de decisoes do Owner do plano
    commitado; a D-4 diz o que a condicao 5 diz dela (rota 1 so, rota 2 recusa nomeada), e a
    D-10 o que a condicao 8 diz dela (o adapter da lane ANT-02 fora da release)."""
    plan = t.show(t.head, PLAN_FILE_REL)
    cond = t.show(t.head, CONDITIONS_REL)
    if plan is None or cond is None:
        raise AssertionError("%s ou %s ausente em %s" % (PLAN_FILE_REL, CONDITIONS_REL, t.head[:12]))
    cited = sorted(set(re.findall(r"\bD-(\d+)\b", cond)), key=int)
    if not cited:
        raise AssertionError("as condicoes nao citam decisao D-N nenhuma (a sonda seria vacua)")
    miss = [("D-%s" % n) for n in cited if _plan_decision(plan, n) is None]
    if miss:
        raise AssertionError("as condicoes citam %s, que a tabela de decisoes do plano commitado (%s) nao traz"
                             % (", ".join(miss), PLAN_FILE_REL))
    d4 = _norm(_plan_decision(plan, "4") or "")
    if "4" in cited and not ("rota 1" in d4 and "recusa nomeada" in d4):
        raise AssertionError("a D-4 do plano commitado nao diz «rota 1» e «recusa nomeada» (a condicao 5 diz)")
    d10 = _norm(_plan_decision(plan, "10") or "")
    if "10" in cited and not ("ANT-02" in d10 and "fora da 1.4.3" in d10):
        raise AssertionError("a D-10 do plano commitado nao diz «ANT-02» e «fora da 1.4.3» (a condicao 8 diz)")
    return "as condicoes citam %s; todas na tabela de decisoes do plano commitado" % (
        ", ".join("D-%s" % n for n in cited))


def c11_scope(t: Tree) -> str:
    gov = set(t.changed(".claude/governance/"))
    if not gov <= GOV_ALLOWED:
        raise AssertionError("muda em .claude/governance/ fora do declarado: %s" % ", ".join(sorted(gov - GOV_ALLOWED)))
    # a condicao 10 diz que do publicador confiavel do npm muda so o COMENTARIO
    ntp = ".claude/governance/npm-trusted-publisher.txt"
    if ntp in gov:
        body = [ln for ln in t.git("diff", "-U0", "--no-renames", t.base, t.head, "--", ntp).splitlines()
                if ln[:1] in "+-" and not ln.startswith(("+++", "---"))]
        data = [ln for ln in body if not ln[1:].lstrip().startswith("#") and ln[1:].strip()]
        if data:
            raise AssertionError("%s muda fora do comentario (a condicao 10 diz: so o comentario): %r"
                                 % (ntp, data[0][:80]))
    loc = set(t.changed(".claude/scripts/local/"))
    if not loc <= LOCAL_ALLOWED:
        raise AssertionError("em .claude/scripts/local/ muda %s (a condicao 10 diz: no maximo o release.sh)"
                             % ", ".join(sorted(loc - LOCAL_ALLOWED)))
    parts, out = runner_sets(t)
    every = set(t.changed())
    seen: Dict[str, str] = {}
    for n, s in parts.items():
        for p in s:
            if p in seen:
                raise AssertionError("%s esta nas partes %s e %s" % (p, seen[p], n))
            seen[p] = str(n)
    both = sorted(set(seen) & out)
    if both:
        raise AssertionError("caminho numa parte E fora do escopo: %s" % ", ".join(both[:5]))
    orphan = sorted(every - set(seen) - out)
    if orphan:
        raise AssertionError("caminho da faixa fora de toda parte e do escopo declarado: %s" % ", ".join(orphan[:8]))
    return "%d caminhos: %s dentro das partes, %d fora (declarado); governance e local no declarado" % (
        len(every), "+".join(str(len(parts[k])) for k in sorted(parts)), len(out & every))


def _claude_stub(d: Path, ver: str) -> str:
    b = d / ("claude-stub-" + ver)
    b.mkdir()
    (b / "claude").write_text("#!/bin/sh\necho '%s (Claude Code)'\n" % ver)
    os.chmod(str(b / "claude"), 0o755)
    return str(b)


def _upgrade(t: Tree, target: Path, flags: List[str], path_head: Optional[str], home: str,
             bare_path: Optional[str] = None) -> subprocess.CompletedProcess:
    path = bare_path if bare_path is not None else (path_head + os.pathsep + os.environ.get("PATH", ""))
    return run(["bash", str(t.path("scripts/upgrade.sh")), str(target)] + flags
               + ["--no-replay", "--no-deprecation-warn"], cwd=t.root,
               env=_env({"HOME": home, "PATH": path}), stdin=b"", timeout=300)


def _tree_state(d: Path) -> List[Tuple[str, str]]:
    out = []
    for dp, dn, fn in os.walk(str(d)):
        dn[:] = [x for x in dn if x != ".git"]
        for f in fn:
            fp = Path(dp) / f
            out.append((str(fp.relative_to(d)), hashlib.sha256(fp.read_bytes()).hexdigest()))
        for x in dn:
            out.append((str((Path(dp) / x).relative_to(d)) + "/", ""))
    return sorted(out)


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


def _section(text: str, version: str) -> str:
    at = re.search(r"(?m)^## \[%s\]" % re.escape(version), text)
    if not at:
        return ""
    rest = text[at.start():]
    nxt = re.search(r"(?m)^## \[", rest[4:])
    return rest[: nxt.start() + 4] if nxt else rest


def _cure67_compute_inside(src: str) -> List[str]:
    """Alem do verificador da relmeta-143: o HMAC (compute_entry_hmac) e calculado so dentro
    do bloco da trava que le o elo, grava a linha e atualiza o sidecar (src ja passou por
    cond67_ast, que exige esse bloco)."""
    fn = [n for n in ast.walk(ast.parse(src))
          if isinstance(n, ast.FunctionDef) and n.name == "append_entry"][0]
    locks = [w for w in ast.walk(fn) if isinstance(w, ast.With)
             and any(_is_filelock_lock(i) for i in w.items)]
    held = _calls_named(fn, "read_prev_hmac") + _calls_named(fn, "write_last_hmac")
    writes = _calls_named(fn, "write")
    calls = _calls_named(fn, "compute_entry_hmac")
    if not calls:
        return ["append_entry sem chamada a compute_entry_hmac"]
    inside = set()
    for w in locks:
        ids = set(id(n) for stmt in w.body for n in ast.walk(stmt))
        if all(id(c) in ids for c in held) and any(id(c) in ids for c in writes):
            inside |= ids
    out = [c.lineno for c in calls if id(c) not in inside]
    if out:
        return ["append_entry calcula o HMAC (compute_entry_hmac) FORA do bloco da trava que le o elo "
                "(linha(s) %s)" % ", ".join(str(x) for x in out)]
    return []


def c14_cure67(t: Tree) -> str:
    """Condicoes 1 e 3: o CASO da condicao 67 da v1.4.0-rc.1, declarado curado. A FORMA do
    codigo pela AST (cond67_ast, VERBATIM do script assinado da relmeta-143, mais o HMAC no
    mesmo bloco), o texto da secao da release no CHANGELOG do candidato e os DOIS envelopes da
    v1.4.0 numerando a 67. Nao executa o gravador."""
    src = t.show(t.head, AUDIT_LOG)
    if src is None:
        raise AssertionError("%s ausente" % AUDIT_LOG)
    bad = cond67_ast(src)
    if not bad:
        bad = _cure67_compute_inside(src)
    if bad:
        raise AssertionError("; ".join(bad))
    sec = _norm(_section(t.show(t.head, CHANGELOG) or "", RELEASE_VERSION))
    miss = [p for p in CURE67_PHRASES if _norm(p) not in sec]
    if miss:
        raise AssertionError("a secao [%s] do CHANGELOG nao diz %r" % (RELEASE_VERSION, miss[0]))
    for rel in V140_ENVELOPES:
        if COND67_DECL not in _norm(t.show(t.head, rel) or ""):
            raise AssertionError("%s nao numera a condicao 67 (%r)" % (rel, COND67_DECL[:40]))
    return ("append_entry le o elo, calcula o HMAC, grava a linha e atualiza o sidecar num mesmo with "
            "FileLock(paths[\"lock\"]) (AST); o CHANGELOG [%s] declara a cura e os limites; os dois "
            "envelopes da v1.4.0 numeram a 67" % RELEASE_VERSION)


def _drift_scenario(t: Tree) -> Dict:
    """O cenario do P2 da parte 3 do re-pass do GA v1.4.2, sem rede e sem executar o codex: um
    ledger JSON valido com `last_seen` em texto e um codex instalado FORA do pin (o package.json
    de um lancador no layout do npm: a ferramenta le a versao sem executa-lo), contra o
    check-substrate-drift.py do candidato com --strict."""
    tmp = tempfile.mkdtemp(prefix="rc1probe-drift.")
    try:
        pkg = Path(tmp) / "codex-pkg"
        (pkg / "bin").mkdir(parents=True)
        (pkg / "package.json").write_text('{"name": "@openai/codex", "version": "0.155.0"}\n',
                                          encoding="utf-8")
        launcher = pkg / "bin" / "codex.js"
        launcher.write_text("#!/bin/sh\nexit 97\n", encoding="utf-8")
        os.chmod(str(launcher), 0o755)
        stub = _claude_stub(Path(tmp), "2.1.999")
        ledger = Path(tmp) / "substrate-watch.json"
        ledger.write_text('{"components": [{"key": "claude_code", "last_seen": "2.1.280"}]}\n',
                          encoding="utf-8")
        cache = Path(tmp) / "cache"
        cache.mkdir()
        p = run([sys.executable, str(t.path(DRIFT_REL)), "--repo-root", t.root, "--json", "--strict",
                 "--skip-catalog", "--codex-bin", str(launcher), "--claude-bin",
                 os.path.join(stub, "claude"), "--ledger", str(ledger), "--cache-dir", str(cache)],
                cwd=tmp, env=_env(), timeout=120)
        try:
            rep = json.loads(p.stdout.decode("utf-8", "replace"))
        except ValueError:
            raise Infra("%s --json nao imprimiu JSON (rc %d): %s"
                        % (DRIFT_REL, p.returncode, p.stderr.decode("utf-8", "replace")[-200:]))
        kinds = [(f.get("component"), f.get("kind"), f.get("severity"))
                 for f in (rep.get("findings") or []) if isinstance(f, dict)]
        return {"rc": p.returncode, "kinds": kinds}
    finally:
        shutil.rmtree(tmp, ignore_errors=True)


def c15_cure_ga_p2(t: Tree) -> str:
    """Condicoes 2 e 4: o P2 da parte 3 do re-pass do GA v1.4.2 (um ledger de substrato com a
    forma errada substituia o relatorio inteiro), declarado curado. O texto da secao da release
    no CHANGELOG, os achados nomeados no codigo, o P2 no veredito pinado e o cenario do P2
    REPRODUZIDO: rc 1 com --strict, CC_LEDGER_UNREADABLE e a deriva do Codex preservada."""
    sec = _norm(_section(t.show(t.head, CHANGELOG) or "", RELEASE_VERSION))
    miss = [p for p in GA_P2_PHRASES if _norm(p) not in sec]
    if miss:
        raise AssertionError("a secao [%s] do CHANGELOG nao diz %r" % (RELEASE_VERSION, miss[0]))
    drift = t.show(t.head, DRIFT_REL) or ""
    for name in ("CC_LEDGER_UNREADABLE", "COMPONENT_CHECK_ERROR"):
        if name not in drift:
            raise AssertionError("%s sem o achado nomeado %s" % (DRIFT_REL, name))
    if GA_P2_TITLE not in (t.show(t.head, GA_P2_VERDICT) or ""):
        raise AssertionError("%s sem o P2 %r" % (GA_P2_VERDICT, GA_P2_TITLE))
    r = _drift_scenario(t)
    kept = [k for c, k, s in r["kinds"] if c == "codex" and s == "drift"]
    if r["rc"] != 1 or ("claude_code", "CC_LEDGER_UNREADABLE", "unknown") not in r["kinds"] or not kept \
            or any(k == "DETECTOR_ERROR" for _c, k, _s in r["kinds"]):
        raise AssertionError("o cenario do P2 (ledger com last_seen em texto, codex 0.155.0 fora do pin, "
                             "--strict) deu rc %d e %s; esperado rc 1, CC_LEDGER_UNREADABLE e a deriva do "
                             "Codex preservada" % (r["rc"], sorted(set(k for _c, k, _s in r["kinds"]))))
    return ("o CHANGELOG [%s] declara a cura; %s nomeia CC_LEDGER_UNREADABLE e COMPONENT_CHECK_ERROR; o "
            "cenario do P2 reproduzido: rc 1 (--strict), CC_LEDGER_UNREADABLE e a deriva do Codex (%s) "
            "preservada" % (RELEASE_VERSION, DRIFT_REL, ", ".join(kept)))


def _pin_without_tag(t: Tree, ref: str) -> Tuple[int, str]:
    """`upgrade.sh <alvo vazio> --pin <ref> --dry-run` rodado de um clone do candidato SEM
    tag nenhuma (o estado do hold: a tag do GA ainda nao existe); o alvo nao muda."""
    tmp = tempfile.mkdtemp(prefix="rc1probe-pin.")
    try:
        src = Path(tmp) / "src"
        if run(["git", "clone", "-q", "--shared", "--no-tags", "--no-checkout", t.root, str(src)],
               timeout=300).returncode != 0 \
                or run(["git", "-C", str(src), "checkout", "-q", "--detach", t.head],
                       timeout=300).returncode != 0:
            raise Infra("clone sem tags do candidato para o --pin")
        if run(["git", "-C", str(src), "rev-parse", "-q", "--verify", "refs/tags/" + ref]).returncode == 0:
            raise Infra("o clone sem tags ainda resolve a tag %s" % ref)
        stub = _claude_stub(Path(tmp), "2.1.999")
        home = os.path.join(tmp, "home")
        os.mkdir(home)
        target = Path(tmp) / "alvo"
        target.mkdir()
        if run(["git", "init", "-q", str(target)]).returncode != 0:
            raise Infra("git init do alvo do --pin")
        before = _tree_state(target)
        p = _upgrade(Tree(str(src), t.base, t.head), target, ["--pin", ref, "--dry-run"], stub, home)
        if _tree_state(target) != before:
            raise AssertionError("upgrade.sh --pin %s --dry-run alterou o alvo" % ref)
        return p.returncode, (p.stderr + p.stdout).decode("utf-8", "replace")
    finally:
        shutil.rmtree(tmp, ignore_errors=True)


def c16_adopter_notes(t: Tree) -> str:
    """Condicoes 7 e 8: durante o hold, o exemplo de upgrade do INSTALL.md pina a versao do
    VERSION do candidato (a que o bump escreve), e o upgrade.sh sem a tag sai com rc 2 e
    «unknown --pin ref»; o adapter Claude da lane live nao muda na faixa (D-10)."""
    inst = t.show(t.head, "INSTALL.md") or ""
    ver = (t.show(t.head, "VERSION") or "").strip()
    ex = re.findall(INSTALL_PIN_RE, inst)
    if len(ex) != 1:
        raise AssertionError("o INSTALL.md tem %d exemplo(s) --pin v<semver> (exigido: 1)" % len(ex))
    if ex[0][1]:
        raise AssertionError("o exemplo --pin do INSTALL.md e uma pre-release (v%s%s): o bump escreve a "
                             "versao GA" % ex[0])
    if ex[0][0] != ver:
        raise AssertionError("o exemplo --pin do INSTALL.md pina v%s e o VERSION do candidato e %r"
                             % (ex[0][0], ver))
    sites = t.show(t.head, BUMP_SITES_REL) or ""
    if BUMP_SITE_INSTALL not in sites:
        raise AssertionError("%s sem o sitio %r: o bump nao reescreve o exemplo do INSTALL.md"
                             % (BUMP_SITES_REL, BUMP_SITE_INSTALL))
    ref = "v" + ver
    rc, out = _pin_without_tag(t, ref)
    if rc != 2 or ("ERROR: unknown --pin ref: %s" % ref) not in out:
        raise AssertionError("upgrade.sh --pin %s --dry-run sem a tag: rc %d (esperado 2 e «ERROR: unknown "
                             "--pin ref: %s»): %s" % (ref, rc, ref, out[-200:]))
    if t.show(t.head, ADAPTER_REL) is None:
        raise AssertionError("%s ausente" % ADAPTER_REL)
    if t.changed(ADAPTER_REL):
        raise AssertionError("%s muda na faixa (a condicao 8 diz que nao)" % ADAPTER_REL)
    return ("o INSTALL.md pina %s (== VERSION; o bump reescreve o exemplo); sem a tag, upgrade.sh --pin %s "
            "--dry-run sai rc 2 com «unknown --pin ref»; %s sem mudanca na faixa" % (ref, ref, ADAPTER_REL))




def _runner_fn(runner: str, name: str) -> str:
    m = re.search(r"(?ms)^%s\(\) \{\n.*?^\}\n" % re.escape(name), runner)
    if not m:
        raise Infra("runner sem a funcao %s" % name)
    return m.group(0)


def _bash_fn(runner: str, fn: str, call: str, env: Optional[Dict[str, str]] = None) -> str:
    p = run(["bash", "-c", _runner_fn(runner, fn) + "\n" + call], env=_env(env), timeout=60)
    if p.returncode != 0:
        raise Infra("bash %s: rc %d" % (fn, p.returncode))
    return p.stdout.decode("utf-8", "surrogateescape")


def runner_sets(t: Tree) -> Tuple[Dict[int, set], set]:
    runner = t.show(t.head, RUNNER_REL)
    if runner is None:
        raise Infra("runner ausente em %s" % t.head)
    m = re.search(r'(?m)^PARTS="([0-9 ]+)"$', runner)
    if not m:
        raise Infra("runner sem PARTS")
    parts: Dict[int, set] = {}
    for n in [int(x) for x in m.group(1).split()]:
        spec = [ln for ln in _bash_fn(runner, "part_pathspec", "part_pathspec %d" % n).splitlines() if ln]
        parts[n] = set(t.changed(*spec))
    spec = [ln for ln in _bash_fn(runner, "out_of_scope_pathspec", "out_of_scope_pathspec").splitlines() if ln]
    return parts, set(t.changed(*spec))


def sizes(t: Tree) -> List[Tuple[bool, str]]:
    runner = t.show(t.head, RUNNER_REL)
    cond = t.show(t.head, CONDITIONS_REL)
    if runner is None or cond is None:
        raise Infra("runner/condicoes ausentes em %s" % t.head)
    parts, _out = runner_sets(t)
    res = []
    tmp = tempfile.mkdtemp(prefix="rc1probe-size.")
    try:
        cf = Path(tmp) / "cond.md"
        cf.write_text(cond, encoding="utf-8")
        for n in sorted(parts):
            files = sorted(parts[n])
            if not files:
                res.append((False, "SIZE parte %d: nenhum arquivo da pathspec mudou" % n))
                continue
            diff = run(["git", "-C", t.root, "diff", "-U1", "--no-renames", t.base, t.head, "--"] + files).stdout
            label = _bash_fn(runner, "part_label", "part_label %d" % n).rstrip("\n")
            cover = _bash_fn(runner, "part_coverage", "part_coverage %d" % n).rstrip("\n")
            head = _bash_fn(runner, "prompt_header", 'prompt_header %d "$PL" "$PC"' % n,
                            {"NPARTS": str(len(parts)), "BASE_TAG": "v1.4.2", "CANDIDATE_SHA": t.head,
                             "CONDITIONS_SNAPSHOT": str(cf), "CONDITIONS_SHA": "0" * 64,
                             "PL": label, "PC": cover})
            total = len(head.encode("utf-8")) + 1 + len(diff)
            lines = diff.count(b"\n")
            limit = MAX_RAW_BYTES - SIZE_MARGIN
            ok = total < limit and lines >= MIN_DIFF_LINES
            res.append((ok, "SIZE parte %d: ~%d B (teto %d = MAX_RAW_BYTES - %d), %d arquivo(s), %d linhas de diff"
                        % (n, total, limit, SIZE_MARGIN, len(files), lines)))
    finally:
        shutil.rmtree(tmp, ignore_errors=True)
    return res


CHECKS: List[Tuple[str, Callable[[Tree], str], Tuple[str, ...]]] = [
    ("C0-tree", c0_tree, ("cabecalho",)), ("C0-npm", c0_npm_rc, ("cabecalho", "6")),
    ("C0-rc-proof", c0_rc_proof, ("6",)), ("C17-final-text", c17_final_text, ("cabecalho",)),
    ("C1-annex-v1.4.0", c1_annex, ("1",)), ("C2-carried-1.4.2", c2_carried, ("2",)),
    ("C14-cure-67", c14_cure67, ("1", "3")), ("C15-cure-ga-p2", c15_cure_ga_p2, ("2", "4")),
    ("C9-codex-pin", c9_codex, ("5",)), ("C13-route1", c13_route1, ("5",)),
    ("C12-plan-decisions", c12_plan_decisions, ("5", "8")),
    ("C16-adopter-notes", c16_adopter_notes, ("7", "8")),
    ("C11-scope", c11_scope, ("9", "10")),
]
# A condicao que a projecao de tamanho (--sizes) confere: o derivador a le daqui (pela AST) e
# exige que toda condicao numerada do texto tenha ao menos um id (ou seja declarada so-texto).
SIZE_CONDITION = "9"


def condition_map() -> str:
    """A linha MAPA: que ids conferem cada condicao (SIZE = --sizes, na SIZE_CONDITION)."""
    by: Dict[str, List[str]] = {}
    for cid, _fn, conds in CHECKS:
        for c in conds:
            by.setdefault(c, []).append(cid)
    by.setdefault(SIZE_CONDITION, []).append("SIZE")
    keys = sorted(by, key=lambda k: (-1 if k == "cabecalho" else int(k)))
    return "MAPA condicao -> ids: " + "; ".join("%s: %s" % (k, " ".join(by[k])) for k in keys)


def main(argv: Optional[Sequence[str]] = None) -> int:
    ap = argparse.ArgumentParser()
    ap.add_argument("--root", required=True)
    ap.add_argument("--base", required=True)
    ap.add_argument("--head", required=True)
    ap.add_argument("--sizes", action="store_true")
    ap.add_argument("--only", default="")
    a = ap.parse_args(argv)
    try:
        t = Tree(a.root, "", "")
        t.base = t.git("rev-parse", "--verify", a.base + "^{commit}").strip()
        t.head = t.git("rev-parse", "--verify", a.head + "^{commit}").strip()
    except Infra as exc:
        print("INFRA sonda: %s" % exc)
        return 2
    only = set(x for x in a.only.split(",") if x)
    unknown = sorted(only - set(cid for cid, _fn, _conds in CHECKS))
    if unknown:
        # um id desconhecido rodaria NADA e sairia rc 0: nunca verde vacuo.
        print("INFRA sonda: id(s) de --only desconhecido(s): %s (ids: %s)"
              % (", ".join(unknown), " ".join(cid for cid, _fn, _conds in CHECKS)))
        return 2
    fails = infra = 0
    for cid, fn, _conds in CHECKS:
        if only and cid not in only:
            continue
        try:
            print("OK   %s: %s" % (cid, fn(t)))
        except AssertionError as exc:
            fails += 1
            print("FAIL %s: %s" % (cid, exc))
        except Infra as exc:
            infra += 1
            print("INFRA %s: %s" % (cid, exc))
        except Exception as exc:  # noqa: BLE001 — uma afirmacao que nao mede nunca vira OK
            infra += 1
            print("INFRA %s: %s: %s" % (cid, type(exc).__name__, str(exc)[:200]))
    if a.sizes:
        try:
            for ok, msg in sizes(t):
                print("%s %s" % ("OK  " if ok else "FAIL", msg))
                fails += 0 if ok else 1
        except Infra as exc:
            infra += 1
            print("INFRA SIZE: %s" % exc)
    print(condition_map())
    print("SONDA: %d FALSA(S), %d sem medida" % (fails, infra))
    if infra:
        return 2
    return 1 if fails else 0


if __name__ == "__main__":
    sys.exit(main())
