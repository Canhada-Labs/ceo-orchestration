#!/usr/bin/env python3
"""Sonda das condicoes da v1.4.2-rc.1 (PLAN-193): cada afirmacao sobre CODIGO do
CONDITIONS-rc1.md e conferida aqui contra um commit, ANTES do re-pass.

  python3 probe-conditions-rc1.py --root DIR --base REV --head REV [--sizes] [--only ID,..]

--root  checkout onde os comportamentos rodam (o worktree do candidato no runner;
        a arvore viva no G0 do OWNER-RC1-CUT.sh). Os arquivos RASTREADOS da arvore
        tem de ser os de --head (conferido; a sonda recusa uma arvore que difere).
--base  a tag base resolvida (v1.4.1^{commit}); --head o commit sob revisao.
--sizes projeta o payload de cada parte com as funcoes do PROPRIO runner (pathspec,
        rotulo, cobertura, cabecalho do prompt) e recusa uma parte acima de
        MAX_RAW_BYTES - 16 KiB, sem arquivo, ou com menos de 50 linhas de diff.

Saida: uma linha `OK|FAIL <id>: <o que>` por afirmacao; rc 0 = todas OK, rc 1 = alguma
FALSA (o re-pass NAO pode rodar com este texto: corrija o codigo ou as condicoes), rc 2 =
a sonda nao conseguiu medir (infraestrutura; nunca vira OK). Nenhuma escrita fora de um
diretorio temporario do sistema, removido na saida; nenhum .pyc (PYTHONDONTWRITEBYTECODE).
DERIVADO por .claude/plans/PLAN-193/derive-kit-142.py — NAO edite a mao. stdlib, >= 3.9.
"""
from __future__ import annotations

import argparse
import ast
import hashlib
import importlib.util
import json
import os
import re
import shlex
import shutil
import subprocess
import sys
import tempfile
from pathlib import Path
from typing import Callable, Dict, List, Optional, Sequence, Tuple

sys.dont_write_bytecode = True

NEW_ID = "claude-opus-5-5"
OLD_ID = "claude-opus-5"
CC_FLOOR = "2.1.280"
CODEX_PIN = "0.156.1"
MAX_RAW_BYTES = 262000
SIZE_MARGIN = 16384
MIN_DIFF_LINES = 50
EV_REL = ".claude/plans/PLAN-193/repass-rc1"
RUNNER_REL = EV_REL + "/run-rc1-repass.sh"
CONDITIONS_REL = EV_REL + "/CONDITIONS-rc1.md"
PLAN_FILE_REL = ".claude/plans/PLAN-193-release-v1-4-2-opus55-fasttrack.md"
GA_ENVELOPE = ".claude/governance/pair-rail-verdict-v1.4.1.md"
RC_ENVELOPE = ".claude/governance/pair-rail-verdict-v1.4.1-rc.1.md"
GA_CONDITIONS = ".claude/plans/PLAN-192/repass-ga/CONDITIONS-ga.md"
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
V140_HOOKS_RE = re.compile(r"^\.claude/hooks/(?!tests/).+\.py$")
V140_TESTS_RE = re.compile(r"(?:^|/)tests/")
FN04_SENTINEL = ".claude/plans/PLAN-193/wave-fn04-approved.md"
CC_BLOCK_RE = re.compile(r"(?ms)^# >>> claude-code-floor\b.*?^# <<< claude-code-floor <<<$")
HARNESS_STUB_MARK = "# >>> harness-claude-stub"
TOOLS = (".claude/scripts/re-pin-codex.py", ".claude/scripts/check-substrate-drift.py",
         ".claude/scripts/derive-settings-baselines.py")
GOV_ALLOWED = frozenset([".claude/governance/codex-cli-pin.txt",
                         ".claude/governance/codex-cli-pin-manifest.json",
                         ".claude/governance/gate-scripts-manifest.txt"])
LOCAL_ALLOWED = frozenset([".claude/scripts/local/release.sh"])


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
    if "if: \"!contains(github.ref, '-rc.')\"" not in wf:
        raise AssertionError("npm-publish.yml nao pula mais as tags -rc.")
    return "a rc nao publica no npm (npm-publish.yml pula -rc.)"


def c1_annex(t: Tree) -> str:
    plan = t.show(t.head, PLAN_FILE_REL) or ""
    if "OQ-3" not in plan or "RE-DECLARA que a cura do anexo da v1.4.0" not in _norm(plan):
        raise AssertionError("%s sem a decisao OQ-3 (RE-DECLARA a cura do anexo da v1.4.0)" % PLAN_FILE_REL)
    env = _norm(t.show(t.head, GA_ENVELOPE) or "")
    for need in ("release_tag: v1.4.1 ", "release expressa que NÃO leva essa cura",
                 "nenhuma versão está prometida para ela"):
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
                                     or V140_HOOKS_RE.match(p) or V140_TESTS_RE.search(p)
                                     or p == "CLAUDE.md")]
    if stray:
        raise AssertionError("arquivo citado pelos vereditos da v1.4.0 muda fora das classes "
                             "declaradas: %s" % ", ".join(stray))
    if not hits:
        raise AssertionError("nenhum arquivo citado pelos vereditos da v1.4.0 muda na faixa — "
                             "a condicao 1 diz que mudam")
    return "anexo da v1.4.0 re-declarado (OQ-3 + envelope do GA); %d citado(s) mudam, todos nas classes" % len(hits)


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
    rc_cond = envelope_verdict_pins(t, RC_ENVELOPE)[1]
    if not rc_cond:
        raise AssertionError("%s nao pina veredito nenhum por condicao (as rodadas 1 e 2)" % RC_ENVELOPE)
    gc = t.show(t.head, GA_CONDITIONS) or ""
    if "\n14. `relaunch --out`" not in gc or "\n23. **O hook copia os bytes" not in gc:
        raise AssertionError("%s nao numera mais 14 (relaunch --out) e 23 (bytes do scriptPath)" % GA_CONDITIONS)
    return "%d veredito(s) pinado(s), todos presentes com o sha256 pinado (%s); GA: 14 e 23" % (
        len(seen), "; ".join(counts))


def c3_fn04(t: Tree) -> str:
    found = canary_pre(t.root)
    if found:
        raise AssertionError("o PreToolUse gravou os bytes do scriptPath em: %s" % ", ".join(found[:3]))
    rec = canary_record(t.root)
    for rel in (FN04_SENTINEL, FN04_SENTINEL + ".asc"):
        if t.show(t.head, rel) is None:
            raise AssertionError("o canario passa, mas %s esta ausente (a cerimonia do FN-04 nao landou)" % rel)
    # A condicao 3 cita o residual do sentinel: a classe NAO se esgota neste hook.
    sent = _norm(t.show(t.head, FN04_SENTINEL) or "")
    for need in ("e nenhum outro hook da classe", "A classe não se esgota neste hook"):
        if need not in sent:
            raise AssertionError("o sentinel do FN-04 (%s) nao declara mais %r" % (FN04_SENTINEL, need))
    return ("canario: o PreToolUse nao grava os bytes do scriptPath e registra caminho, sha256 e tamanho; "
            "%s; o sentinel do FN-04 declara a classe nao esgotada (cerimonia landada)" % rec)


def _ledger_files(home: Path) -> Tuple[List[Path], List[Path], List[Path]]:
    mans, idx, snaps = [], [], []
    for dp, _dn, fn in os.walk(str(home)):
        if Path(dp).name != "launches":
            continue
        for f in fn:
            if f.endswith(".json"):
                mans.append(Path(dp) / f)
            elif f == "launches.jsonl":
                idx.append(Path(dp) / f)
            elif f.endswith(".script"):
                snaps.append(Path(dp) / f)
    return mans, idx, snaps


def canary_record(root: str) -> str:
    """PreToolUse + PostToolUse do hook REAL de `root` com um `scriptPath` canario, em
    quatro vinculos: por tool_use_id com o id rotulado (o snapshot e gravado, com os bytes
    do sha256 gravado antes do despacho), sem tool_use_id (heuristico), com o id sem
    rotulo, e com o arquivo trocado entre as duas leituras (nenhum snapshot nos tres)."""
    hook = Path(root) / ".claude/hooks/check_workflow_launch.py"
    if not hook.is_file():
        raise Infra("hook ausente: %s" % hook)
    tmp = tempfile.mkdtemp(prefix="rc1probe-ledger.")
    try:
        why = []
        for case in ("bound", "heuristic", "unlabelled", "changed"):
            base = Path(tmp) / case
            home, proj = base / "home", base / "proj"
            (proj / ".claude").mkdir(parents=True)
            home.mkdir()
            script = base / "denied" / "workflow.js"
            script.parent.mkdir()
            data = (b"// RC1-PROBE-LEDGER-" + os.urandom(8).hex().encode()
                    + b"\nexport default async function () {}\n")
            script.write_bytes(data)
            sha = hashlib.sha256(data).hexdigest()
            env = _env({"HOME": str(home), "CLAUDE_PROJECT_DIR": str(proj)})
            pre = {"hook_event_name": "PreToolUse", "tool_name": "Workflow", "session_id": "probe-ledger",
                   "tool_use_id": "toolu_probe_" + case, "cwd": str(proj),
                   "tool_input": {"scriptPath": str(script), "args": {"k": "v"}}}
            for ev in ("pre", "post"):
                if ev == "post":
                    rid = "wf_" + os.urandom(4).hex()
                    resp = ("Workflow started (%s).\n" % rid) if case == "unlabelled" else ("Workflow launched.\nRun ID: %s\n" % rid)
                    event = dict(pre, hook_event_name="PostToolUse", tool_response=resp)
                    if case == "heuristic":
                        event.pop("tool_use_id")
                    if case == "changed":
                        script.write_bytes(data + b"// trocado depois do despacho\n")
                else:
                    event = pre
                p = run([sys.executable, str(hook)], cwd=str(proj), env=env,
                        stdin=json.dumps(event).encode(), timeout=60)
                if p.returncode != 0:
                    raise Infra("hook (%s/%s) rc %d: %s" % (case, ev, p.returncode,
                                                            p.stderr.decode("utf-8", "replace")[:200]))
                mans, idx, snaps = _ledger_files(home)
                if len(mans) != 1 or len(idx) != 1:
                    raise Infra("ledger do ensaio (%s/%s): %d manifesto(s), %d indice(s)" % (case, ev, len(mans), len(idx)))
                m = json.loads(mans[0].read_text(encoding="utf-8"))
                s = m.get("script") or {}
                if (s.get("source"), s.get("path"), s.get("sha256"), s.get("bytes")) != ("path", str(script), sha, len(data)):
                    raise AssertionError("%s/%s: o manifesto nao registra caminho, sha256 e tamanho do scriptPath (%r)" % (case, ev, s))
                if ev == "pre":
                    if snaps or m.get("script_snapshot") is not None \
                            or m.get("script_snapshot_why") != "awaiting_post_tool_use":
                        raise AssertionError("%s/pre: snapshot antes do despacho (%r, %r, %d arquivo(s))"
                                             % (case, m.get("script_snapshot"), m.get("script_snapshot_why"), len(snaps)))
                    if ('"script_sha256": "%s"' % sha) not in idx[0].read_text(encoding="utf-8"):
                        raise AssertionError("%s/pre: a linha do indice nao carrega o sha256 do scriptPath" % case)
                elif case == "bound":
                    if len(snaps) != 1 or snaps[0].read_bytes() != data or m.get("script_snapshot") != snaps[0].name:
                        raise AssertionError("bound/post: o PostToolUse vinculado por tool_use_id nao gravou o snapshot com os bytes do sha256 gravado")
                else:
                    if snaps or m.get("script_snapshot") is not None:
                        raise AssertionError("%s/post: gravou snapshot (%r)" % (case, m.get("script_snapshot_why")))
                    why.append("%s=%s" % (case, m.get("script_snapshot_why")))
        return "PostToolUse por tool_use_id grava o snapshot; sem snapshot: %s" % ", ".join(why)
    finally:
        shutil.rmtree(tmp, ignore_errors=True)


def canary_pre(root: str) -> List[str]:
    """Roda o hook REAL de `root` num PreToolUse com scriptPath para um arquivo canario e
    devolve os arquivos (fora do canario) que contem os bytes dele. Usado tambem pelo
    harness contra o hook da v1.4.1 (controle positivo: la a lista NAO e vazia)."""
    hook = Path(root) / ".claude/hooks/check_workflow_launch.py"
    if not hook.is_file():
        raise Infra("hook ausente: %s" % hook)
    tmp = tempfile.mkdtemp(prefix="rc1probe-canary.")
    try:
        home = Path(tmp) / "home"
        proj = Path(tmp) / "proj"
        (proj / ".claude").mkdir(parents=True)
        home.mkdir()
        secret = Path(tmp) / "denied" / "workflow.js"
        secret.parent.mkdir()
        mark = b"RC1-PROBE-CANARY-7f3a9c2e-" + os.urandom(8).hex().encode()
        secret.write_bytes(b"// " + mark + b"\nexport default async function () {}\n")
        ev = {"hook_event_name": "PreToolUse", "tool_name": "Workflow", "session_id": "probe-session",
              "tool_use_id": "toolu_probe_canary", "cwd": str(proj),
              "tool_input": {"scriptPath": str(secret), "args": {"k": "v"}}}
        p = run([sys.executable, str(hook)], cwd=str(proj),
                env=_env({"HOME": str(home), "CLAUDE_PROJECT_DIR": str(proj)}),
                stdin=json.dumps(ev).encode(), timeout=60)
        if p.returncode != 0:
            raise Infra("hook rc %d: %s" % (p.returncode, p.stderr.decode("utf-8", "replace")[:200]))
        hits = []
        for base in (home, proj):
            for dp, _dn, fn in os.walk(str(base)):
                for f in fn:
                    fp = Path(dp) / f
                    try:
                        if mark in fp.read_bytes():
                            hits.append(str(fp.relative_to(tmp)))
                    except OSError:
                        continue
        # o hook escreveu ALGO? Sem nenhum arquivo sob o estado, o canario seria vacuo.
        wrote = any(files for _d, _n, files in os.walk(str(home)))
        if not wrote:
            raise Infra("o hook nao escreveu nada sob o HOME do ensaio — o canario seria vacuo")
        return sorted(hits)
    finally:
        shutil.rmtree(tmp, ignore_errors=True)


def _load_ceo_launches(root: str):
    path = Path(root) / ".claude/scripts/ceo-launches.py"
    spec = importlib.util.spec_from_file_location("ceo_launches_probe", str(path))
    if spec is None or spec.loader is None:
        raise Infra("ceo-launches.py nao carrega")
    mod = importlib.util.module_from_spec(spec)
    old = list(sys.path)
    try:
        spec.loader.exec_module(mod)
    finally:
        sys.path[:] = old
    return mod


def c4_relaunch_out(t: Tree) -> str:
    src = t.show(t.head, ".claude/scripts/ceo-launches.py") or ""
    for lit in ("os.link(", '_TMP_PREFIX = ".ceo-launches-out-"', "could not be read back", "os.fsync(fd)"):
        if lit not in src:
            raise AssertionError("ceo-launches.py sem %r" % lit)
    i_d = src.find("could not be read back")
    i_x = src.find("# exact recorded call for run")
    if i_x < 0 or i_d > i_x:
        raise AssertionError("o caso (d) nao recusa antes do cabecalho de chamada exata")
    if "return 7" not in src[i_d:i_d + 400]:
        raise AssertionError("o caso (d) nao sai rc 7")
    if src.find("os.fsync(fd)") > src.find("os.link("):
        raise AssertionError("o fsync nao vem antes do link")
    doc = t.show(t.head, "docs/workflow-recovery.md") or ""
    if "**`relaunch --out` (declared).**" not in doc:
        raise AssertionError("docs/workflow-recovery.md sem o item «relaunch --out (declared)»")
    tree = ast.parse(src)
    bad = []
    for node in ast.walk(tree):
        if isinstance(node, ast.Call) and isinstance(node.func, ast.Attribute) \
                and isinstance(node.func.value, ast.Name) and node.func.value.id == "os" \
                and node.func.attr in ("unlink", "remove", "rmdir", "rename", "replace", "renames"):
            a0 = node.args[0] if node.args else None
            if not (isinstance(a0, ast.Name) and a0.id in ("_TMP_NAME", "priv")):
                bad.append("os.%s(%s) na linha %d" % (node.func.attr, ast.unparse(a0) if a0 is not None else "", node.lineno))
    if bad:
        raise AssertionError("remocao/renomeacao com nome que nao e o temporario nem o diretorio privado: %s" % "; ".join(bad))
    mod = _load_ceo_launches(t.root)
    wr = getattr(mod, "_write_new_file", None)
    if wr is None:
        raise AssertionError("ceo-launches.py sem _write_new_file")
    tmp = tempfile.mkdtemp(prefix="rc1probe-out.")
    try:
        d = Path(tmp)
        data = b"x" * 70000 + b"\nFIM\n"
        err = wr(str(d / "novo.js"), data)
        left = [p.name for p in d.iterdir() if p.name.startswith(".ceo-launches-out-")]
        if err is not None or (d / "novo.js").read_bytes() != data or left:
            raise AssertionError("destino ausente: err=%r, sobras=%r" % (err, left))
        (d / "existe.js").write_bytes(b"do adopter\n")
        err = wr(str(d / "existe.js"), data)
        if err is None or (d / "existe.js").read_bytes() != b"do adopter\n":
            raise AssertionError("destino existente foi aceito ou alterado")
        (d / "alvo.txt").write_bytes(b"alvo\n")
        os.symlink(str(d / "alvo.txt"), str(d / "link.js"))
        err = wr(str(d / "link.js"), data)
        if err is None or (d / "alvo.txt").read_bytes() != b"alvo\n" or not os.path.islink(str(d / "link.js")):
            raise AssertionError("symlink no destino foi seguido ou substituido")
        (d / "dir.js").mkdir()
        err = wr(str(d / "dir.js"), data)
        if err is None or not (d / "dir.js").is_dir():
            raise AssertionError("diretorio no destino foi aceito")
        left = [p.name for p in d.iterdir() if p.name.startswith(".ceo-launches-out-")]
        if left:
            raise AssertionError("sobrou diretorio privado depois das recusas: %s" % left)
    finally:
        shutil.rmtree(tmp, ignore_errors=True)
    return "relaunch --out: link sem substituir; nome do destino nunca removido; 4 casos de comportamento"


def _settings(t: Tree, rel: str) -> Dict:
    raw = t.show(t.head, rel)
    if raw is None:
        raise AssertionError("%s ausente" % rel)
    return json.loads(raw)


def _fb(v) -> List[str]:
    return v if isinstance(v, list) else ([v] if isinstance(v, str) else [])


def c5_pin(t: Tree) -> str:
    for rel in ("templates/settings/settings.base.json", "templates/settings/settings.user.json",
                ".claude/settings.json"):
        s = _settings(t, rel)
        if s.get("model") != NEW_ID:
            raise AssertionError("%s: model=%r (esperado %s)" % (rel, s.get("model"), NEW_ID))
        if "ultracode" in s:
            raise AssertionError("%s carrega ultracode" % rel)
        if rel.endswith("settings.user.json"):
            # o perfil user e advisory por desenho: fixa o pin sem restringir a lista
            if "availableModels" in s or "fallbackModel" in s:
                raise AssertionError("%s carrega availableModels/fallbackModel" % rel)
            continue
        am = s.get("availableModels") or []
        if NEW_ID not in am or OLD_ID not in am:
            raise AssertionError("%s: availableModels sem %s e %s" % (rel, NEW_ID, OLD_ID))
        if OLD_ID not in _fb(s.get("fallbackModel")):
            raise AssertionError("%s: fallbackModel sem %s" % (rel, OLD_ID))
    af = t.show(t.head, ".claude/hooks/_lib/agent_frontmatter.py") or ""
    m = re.search(r"(?ms)^VETO_FLOOR_ALLOWED\b[^=]*=\s*frozenset\(\{(.*?)\}\)", af)
    if not m or ('"%s"' % NEW_ID) not in m.group(1):
        raise AssertionError("VETO_FLOOR_ALLOWED sem %s" % NEW_ID)
    agents = t.changed(".claude/agents/")
    if agents:
        raise AssertionError("arquivo de agente muda na faixa: %s" % ", ".join(agents))
    return "pin %s nos 3 settings, %s em availableModels/fallback, sem ultracode; piso VETO; agentes intactos" % (NEW_ID, OLD_ID)


def _claude_stub(d: Path, ver: str) -> str:
    b = d / ("claude-stub-" + ver)
    b.mkdir()
    (b / "claude").write_text("#!/bin/sh\necho '%s (Claude Code)'\n" % ver)
    os.chmod(str(b / "claude"), 0o755)
    return str(b)


def c6_effort(t: Tree) -> str:
    for rel in ("templates/settings/settings.base.json", "templates/settings/settings.user.json"):
        if _settings(t, rel).get("effortLevel") != "xhigh":
            raise AssertionError("%s: effortLevel != xhigh" % rel)
    shipped = t.show(t.base, "templates/settings/settings.base.json")
    if shipped is None:
        raise Infra("template base da tag base ilegivel")
    tmp = tempfile.mkdtemp(prefix="rc1probe-upg.")
    try:
        stub = _claude_stub(Path(tmp), "2.1.999")
        home = str(Path(tmp) / "home")
        os.mkdir(home)
        out = []
        for label, extra in (("sem effortLevel", {}), ("effortLevel do adopter", {"effortLevel": "low"})):
            target = Path(tmp) / label.replace(" ", "-")
            (target / ".claude").mkdir(parents=True)
            seed = json.loads(shipped)
            seed.update(extra)
            (target / ".claude/settings.json").write_text(json.dumps(seed, indent=2) + "\n")
            p = run(["bash", str(t.path("scripts/upgrade.sh")), str(target), "--settings-migrate-only",
                     "--no-replay", "--no-deprecation-warn"], cwd=t.root,
                    env=_env({"HOME": home, "PATH": stub + os.pathsep + os.environ.get("PATH", "")}),
                    timeout=180)
            if p.returncode != 0:
                raise AssertionError("upgrade.sh --settings-migrate-only (%s) rc %d: %s"
                                     % (label, p.returncode, (p.stderr or p.stdout).decode("utf-8", "replace")[-300:]))
            after = json.loads((target / ".claude/settings.json").read_text())
            want = extra.get("effortLevel", "high")
            if after.get("model") != NEW_ID or after.get("effortLevel") != want:
                raise AssertionError("adopter %s: model=%r effortLevel=%r (esperado %s / %s)"
                                     % (label, after.get("model"), after.get("effortLevel"), NEW_ID, want))
            out.append(label)
        # o opt-in: `--adopt-setting effortLevel` grava xhigh; um valor do adopter fica.
        for label, extra, want in (("opt-in", {}, "xhigh"), ("opt-in sobre valor do adopter", {"effortLevel": "low"}, "low")):
            target = Path(tmp) / label.replace(" ", "-")
            (target / ".claude").mkdir(parents=True)
            seed = json.loads(shipped)
            seed.update(extra)
            (target / ".claude/settings.json").write_text(json.dumps(seed, indent=2) + "\n")
            p = _upgrade(t, target, ["--settings-migrate-only", "--adopt-setting", "effortLevel"], stub, home)
            after = json.loads((target / ".claude/settings.json").read_text())
            if p.returncode != 0 or after.get("model") != NEW_ID or after.get("effortLevel") != want:
                raise AssertionError("adopter %s: rc %d model=%r effortLevel=%r (esperado 0 / %s / %s)"
                                     % (label, p.returncode, after.get("model"), after.get("effortLevel"), NEW_ID, want))
        # a re-execucao: um settings.json ilegivel sai sem migrar e imprime o comando com o
        # alvo (citado para o shell) e as flags do operador.
        target = Path(tmp) / "alvo com espaco $e aspas'"
        (target / ".claude").mkdir(parents=True)
        (target / ".claude/settings.json").write_text("{ nao e json\n")
        for flags in (["--adopt-setting", "effortLevel", "--allow-old-claude-code"],
                      ["--adopt-setting", "effortLevel", "--dry-run"]):
            p = _upgrade(t, target, ["--settings-migrate-only"] + flags, stub, home)
            err = p.stderr.decode("utf-8", "replace")
            cmds = [shlex.split(ln.strip()) for ln in err.splitlines() if "--settings-migrate-only" in ln]
            want_cmd = ["scripts/upgrade.sh", str(target), "--settings-migrate-only"] + flags
            if (target / ".claude/settings.json").read_text() != "{ nao e json\n":
                raise AssertionError("o settings.json ilegivel foi alterado (%s)" % " ".join(flags))
            if cmds != [want_cmd]:
                raise AssertionError("a saida do helper que falha nao da o comando de re-execucao com o alvo e "
                                     "as flags do operador (%s): %r" % (" ".join(flags), cmds))
    finally:
        shutil.rmtree(tmp, ignore_errors=True)
    dog = _settings(t, ".claude/settings.json")
    if dog.get("effortLevel") != "xhigh":
        raise AssertionError(".claude/settings.json: effortLevel=%r (esperado xhigh)" % dog.get("effortLevel"))
    # Cada saida de falha da migracao que deixa o settings.json sem migrar imprime o
    # comando que a rotina UNICA monta: toda linha «migration alone» o carrega (na mesma
    # ou na seguinte), e nenhuma outra linha monta um `upgrade.sh ... --settings-migrate-only`.
    up = [ln for ln in (t.show(t.head, "scripts/upgrade.sh") or "").splitlines()]
    body = [ln for ln in up if not ln.lstrip().startswith("#")]
    sites = [i for i, ln in enumerate(up) if "migration alone" in ln and not ln.lstrip().startswith("#")]
    if len(sites) < 3 or any("$(_t54_rerun_cmd)" not in (up[i] + (up[i + 1] if i + 1 < len(up) else ""))
                             for i in sites):
        raise AssertionError("upgrade.sh: uma saida «migration alone» sem o comando da rotina _t54_rerun_cmd (%d saida(s))" % len(sites))
    built = [ln for ln in body if "upgrade.sh" in ln and "--settings-migrate-only" in ln]
    rr = re.search(r"(?ms)^_t54_rerun_cmd\(\) \{\n.*?^\}\n", "\n".join(up) + "\n")
    if len(built) != 1 or not rr or any(f not in rr.group(0) for f in
                                        ("--adopt-setting", "--allow-old-claude-code", "--pin", "--dry-run", "%q")):
        raise AssertionError("upgrade.sh: o comando de re-execucao nao e montado por UMA rotina com as 4 flags citadas")
    return ("templates e .claude/settings.json xhigh; upgrade dos settings da v1.4.1: pin -> %s e high quando "
            "ausente, xhigh so com --adopt-setting, valor do adopter mantido; re-execucao com o alvo e as flags "
            "(%d saidas pela rotina unica)" % (NEW_ID, len(sites)))


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


def c7_cc_floor(t: Tree) -> str:
    blocks = []
    for rel in ("scripts/install.sh", "scripts/upgrade.sh"):
        m = CC_BLOCK_RE.search(t.show(t.head, rel) or "")
        if not m:
            raise AssertionError("%s sem o bloco claude-code-floor" % rel)
        blocks.append(m.group(0))
    if blocks[0] != blocks[1]:
        raise AssertionError("o bloco claude-code-floor difere entre install.sh e upgrade.sh")
    if ('CC_FLOOR_VERSION="%s"' % CC_FLOOR) not in blocks[0] or "CC_FLOOR_PROBE_SECONDS=10\n" not in blocks[0]:
        raise AssertionError("o bloco claude-code-floor sem o piso %s ou sem a sonda de 10 s" % CC_FLOOR)
    shipped = t.show(t.base, "templates/settings/settings.base.json")
    if shipped is None:
        raise Infra("template base da tag base ilegivel")
    bare = os.pathsep.join(["/usr/bin", "/bin", "/usr/sbin", "/sbin"])
    if shutil.which("claude", path=bare) is not None or any(
            shutil.which(x, path=bare) is None for x in ("bash", "git", "python3")):
        raise Infra("o PATH minimo %s tem um claude, ou nao tem bash/git/python3: o caso sem claude nao mede" % bare)
    tmp = tempfile.mkdtemp(prefix="rc1probe-floor.")
    seen = []
    try:
        home = str(Path(tmp) / "home")
        os.mkdir(home)
        stubs = {}
        for name, body in (("old", "echo '2.1.279 (Claude Code)'"), ("beta", "echo '2.1.280-beta.1 (Claude Code)'"),
                           ("other-first", "echo '9.9.9 (Other Tool)'; echo '2.1.279 (Claude Code)'"),
                           ("floor", "echo '2.1.280 (Claude Code)'"), ("unreadable", "echo 'sem versao'")):
            d = Path(tmp) / ("stub-" + name)
            d.mkdir()
            (d / "claude").write_text("#!/bin/sh\n%s\n" % body)
            os.chmod(str(d / "claude"), 0o755)
            stubs[name] = str(d)
        # (stub, flags, rc esperado, o alvo muda?, trecho esperado no stderr)
        cases = (
            ("old", ["--settings-migrate-only"], 6, False, "is below %s" % CC_FLOOR),
            ("old", [], 6, False, "nothing was written"),
            ("beta", ["--settings-migrate-only"], 6, False, "anything after its three numbers"),
            ("other-first", ["--settings-migrate-only"], 6, False, "2.1.279 is below"),
            ("old", ["--settings-migrate-only", "--allow-old-claude-code"], 0, True, "continuing because --allow-old-claude-code"),
            ("old", ["--settings-migrate-only", "--dry-run"], 0, False, "(dry-run) would REFUSE"),
            ("floor", ["--settings-migrate-only"], 0, True, ""),
            ("unreadable", ["--settings-migrate-only"], 0, True, "version unreadable"),
            (None, ["--settings-migrate-only"], 0, True, "not found on PATH"),
        )
        for i, (stub, flags, want_rc, changes, needle) in enumerate(cases):
            target = Path(tmp) / ("upg-%d" % i)
            (target / ".claude").mkdir(parents=True)
            if run(["git", "init", "-q", str(target)]).returncode != 0:
                raise Infra("git init do alvo do upgrade.sh")
            (target / ".claude/settings.json").write_text(shipped)
            before = _tree_state(target)
            if stub is None:
                p = _upgrade(t, target, flags, None, home, bare_path=bare)
            else:
                p = _upgrade(t, target, flags, stubs[stub], home)
            err = p.stderr.decode("utf-8", "replace")
            label = "%s %s" % (stub or "sem claude", " ".join(flags) or "(upgrade completo)")
            if p.returncode != want_rc or (needle and needle not in err):
                raise AssertionError("upgrade.sh (%s): rc %d (esperado %d); stderr sem %r: %s"
                                     % (label, p.returncode, want_rc, needle, err[-240:]))
            if (_tree_state(target) != before) != changes:
                raise AssertionError("upgrade.sh (%s): o alvo %s" % (label, "nao migrou" if changes else "mudou"))
            seen.append(label)
        # install.sh num alvo novo, abaixo do piso: sai 6 e o alvo fica como estava.
        target = Path(tmp) / "inst"
        target.mkdir()
        if run(["git", "init", "-q", str(target)]).returncode != 0:
            raise Infra("git init do alvo do install.sh")
        before = _tree_state(target)
        p = run(["bash", str(t.path("scripts/install.sh")), str(target)], cwd=t.root,
                env=_env({"HOME": home, "PATH": stubs["old"] + os.pathsep + os.environ.get("PATH", "")}),
                stdin=b"", timeout=300)
        if p.returncode != 6 or _tree_state(target) != before \
                or ("is below %s" % CC_FLOOR) not in p.stderr.decode("utf-8", "replace"):
            raise AssertionError("install.sh abaixo do piso: rc %d (esperado 6), alvo %s"
                                 % (p.returncode, "intacto" if _tree_state(target) == before else "ALTERADO"))
        seen.append("install.sh old")
    finally:
        shutil.rmtree(tmp, ignore_errors=True)
    return "bloco igual nos dois scripts; %d casos do piso %s: %s" % (len(seen), CC_FLOOR, "; ".join(seen))


def _plan_oq(plan: str, n: str) -> Optional[str]:
    """O item `- OQ-<n> ...` do plano, ate o proximo item de lista de topo."""
    m = re.search(r"(?ms)^- OQ-%s\b.*?(?=^- |^#|\Z)" % re.escape(n), plan)
    return m.group(0) if m else None


def c12_plan_decisions(t: Tree) -> str:
    """Toda decisao OQ-N que as condicoes citam esta no plano commitado, RESOLVIDA; e a
    OQ-7 do plano nao contradiz a condicao 6 (a migracao do pin grava `high`)."""
    plan = t.show(t.head, PLAN_FILE_REL)
    cond = t.show(t.head, CONDITIONS_REL)
    if plan is None or cond is None:
        raise AssertionError("%s ou %s ausente em %s" % (PLAN_FILE_REL, CONDITIONS_REL, t.head[:12]))
    cited = sorted(set(re.findall(r"\bOQ-(\d+)\b", cond)), key=int)
    if not cited:
        raise AssertionError("as condicoes nao citam decisao OQ-N nenhuma (a sonda seria vacua)")
    miss = []
    for n in cited:
        item = _plan_oq(plan, n)
        if item is None or "RESOLVIDA" not in item:
            miss.append("OQ-%s" % n)
    if miss:
        raise AssertionError("as condicoes citam %s, que o plano commitado (%s) nao traz RESOLVIDA(S)"
                             % (", ".join(miss), PLAN_FILE_REL))
    oq7 = _norm(_plan_oq(plan, "7") or "")
    if "não muda o esforço" in oq7:
        raise AssertionError("a OQ-7 do plano commitado diz que o upgrade «não muda o esforço», e a "
                             "condicao 6 diz que a migracao do pin grava high (OQ-8)")
    return "as condicoes citam %s; todas RESOLVIDAS no plano commitado; a OQ-7 nao contradiz a condicao 6" % (
        ", ".join("OQ-%s" % n for n in cited))


def c8_adapter(t: Tree) -> str:
    code = (
        "import sys\nsys.dont_write_bytecode=True\nsys.path.insert(0, sys.argv[1])\n"
        "import os\n"
        "from _lib.adapters.live import claude as c\n"
        "from _lib.adapters.live import claude_batch as cb\n"
        # novos, futuros e um id da lista com OUTRO segmento: adaptive-only
        "ids = ['claude-opus-5-5','claude-opus-5','claude-sonnet-5','claude-zeta-9','claude-sonnet-4-5-fast']\n"
        # legados: por id, datado, Vertex, Bedrock, a data da geracao 4.0, e a familia Claude 3
        "leg = ['claude-sonnet-4-5','claude-sonnet-4-5-20250929','claude-sonnet-4-5@20250929',"
        "'anthropic.claude-sonnet-4-5-20250929-v1:0','claude-opus-4-20250514','claude-3-7-sonnet-20250219',"
        "'claude-3-5-haiku-latest']\n"
        "bad = [i for i in ids if not c._is_adaptive_only(i)] + [i for i in leg if c._is_adaptive_only(i)]\n"
        "os.environ['CEO_EFFORT_OVERRIDE'] = 'high'\n"
        "a = c._resolve_effort_config('claude-opus-5-5')\n"
        "l = c._resolve_effort_config('claude-sonnet-4-5')\n"
        "if a[0] != {'type': 'adaptive'} or 'budget_tokens' in str(a):\n"
        "    bad.append('effort-novo:%r' % (a,))\n"
        "if not (isinstance(l[0], dict) and l[0].get('type') == 'enabled' and l[0].get('budget_tokens')):\n"
        "    bad.append('effort-legado:%r' % (l,))\n"
        "th = {'type': 'enabled', 'budget_tokens': 2048}\n"
        "pl = cb.BatchClaudeLiveAdapter().build_batch_request_payload([{'model': 'claude-opus-5-5', 'thinking': dict(th), 'messages': []}])\n"
        "if pl['requests'][0]['params'].get('thinking') != th:\n"
        "    bad.append('batch-nativo:%r' % (pl,))\n"
        "print('BAD:' + ','.join(bad) if bad else 'OK')\n")
    p = run([sys.executable, "-c", code, str(t.path(".claude/hooks"))], cwd=t.root, env=_env(), timeout=60)
    out = p.stdout.decode("utf-8", "replace").strip()
    if p.returncode != 0:
        raise AssertionError("adapter nao carrega/_is_adaptive_only ausente: %s" % p.stderr.decode("utf-8", "replace")[-200:])
    if out != "OK":
        raise AssertionError("adapter: classificacao errada: %s" % out)
    # call(): a normalizacao de um thinking de quem chama num id adaptive-only, antes do envio.
    src = t.show(t.head, ".claude/hooks/_lib/adapters/live/claude.py") or ""
    g = re.search(r'(?ms)^ +if isinstance\(body\.get\("thinking"\), dict\) and _is_adaptive_only\(model\):\n(.*?)\n\n', src)
    if not g or 'body["thinking"] = {"type": "adaptive"}' not in g.group(1) \
            or '_t_norm.pop("budget_tokens", None)' not in g.group(1):
        raise AssertionError("claude.py: call() sem a normalizacao do thinking de quem chama nos ids adaptive-only")
    bsrc = t.show(t.head, ".claude/hooks/_lib/adapters/live/claude_batch.py") or ""
    nb = re.search(r"(?ms)^    def _run_native_batch_lifecycle\(.*?(?=^    def )", bsrc)
    if not nb or "self.build_batch_request_payload(" not in nb.group(0):
        raise AssertionError("claude_batch.py: o batch nativo nao monta o pedido por build_batch_request_payload")
    return ("adapter: ids novos, futuros e com outro segmento adaptativos; legados (id, datado, Vertex, Bedrock, "
            "Claude 3) com budget no /effort; call() normaliza; o batch nativo leva o thinking como veio")


def c9_codex(t: Tree) -> str:
    man = json.loads(t.show(t.head, ".claude/governance/codex-cli-pin-manifest.json") or "{}")
    if man.get("package_version") != CODEX_PIN:
        raise AssertionError("o manifesto ADR-182 pina %r (esperado %s: o re-pin landou?)"
                             % (man.get("package_version"), CODEX_PIN))
    for rel in (".claude/plans/PLAN-193/codex-pin-0156/pin-0156-approved.md",
                ".claude/plans/PLAN-193/codex-pin-0156/pin-0156-approved.md.asc"):
        if t.show(t.head, rel) is None:
            raise AssertionError("%s ausente (a cerimonia do re-pin nao landou)" % rel)
    return "manifesto ADR-182 pina %s; cerimonia do re-pin landada" % CODEX_PIN


def c10_tools(t: Tree) -> str:
    names = [Path(x).name for x in TOOLS]
    for rel in TOOLS:
        if t.show(t.head, rel) is None:
            raise AssertionError("%s ausente" % rel)
        test = ".claude/scripts/tests/test_%s" % Path(rel).name.replace("-", "_")
        if t.show(t.head, test) is None:
            raise AssertionError("%s sem teste (%s)" % (rel, test))
    surfaces = ["templates/settings/settings.base.json", "templates/settings/settings.user.json",
                ".claude/settings.json"]
    surfaces += [p for p in t.git("ls-tree", "-r", "--name-only", t.head, ".claude/hooks/").splitlines()
                 if p.endswith(".py") and "/tests/" not in p]
    for rel in surfaces:
        s = t.show(t.head, rel) or ""
        for n in names:
            if n in s:
                raise AssertionError("%s cita %s" % (rel, n))
    return "as 3 ferramentas existem; nenhum settings entregue nem hook as chama"


def c11_scope(t: Tree) -> str:
    gov = set(t.changed(".claude/governance/"))
    if not gov <= GOV_ALLOWED:
        raise AssertionError("muda em .claude/governance/ fora do declarado: %s" % ", ".join(sorted(gov - GOV_ALLOWED)))
    loc = set(t.changed(".claude/scripts/local/"))
    if loc != LOCAL_ALLOWED:
        raise AssertionError("em .claude/scripts/local/ muda %s (a condicao 12 diz: so o release.sh)"
                             % (", ".join(sorted(loc)) or "nada"))
    gam = t.show(t.head, ".claude/scripts/generate-available-models.py") or ""
    if "--check" not in gam or "ADR-149" not in gam:
        raise AssertionError("generate-available-models.py sem --check ou sem a ADR-149 como fonte")
    adr = t.changed(".claude/adr/")
    a149 = ".claude/adr/ADR-149-model-id-allowlist.md"
    if a149 not in adr or "## Amendment 3" not in (t.show(t.head, a149) or ""):
        raise AssertionError("a ADR-149 nao muda na faixa com a Amendment 3")
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
    # A condicao 12: o bloco harness-claude-stub nos harnesses de teste e no unico
    # scripts/local/ que muda; a camada de isolamento (Eixo 4) na parte 2, nao fora.
    sl = set(t.changed("scripts/local/"))
    if sl != {"scripts/local/smoke-install-parity.sh"} \
            or HARNESS_STUB_MARK not in (t.show(t.head, "scripts/local/smoke-install-parity.sh") or ""):
        raise AssertionError("em scripts/local/ muda %s (a condicao 12 diz: so o smoke-install-parity.sh, com o bloco harness-claude-stub)"
                             % (", ".join(sorted(sl)) or "nada"))
    stubbed = [p for p in every if V140_TESTS_RE.search(p) and p.endswith(".sh")
               and HARNESS_STUB_MARK in (t.show(t.head, p) or "")]
    if not stubbed:
        raise AssertionError("nenhum harness shell de teste da faixa traz o bloco harness-claude-stub (a condicao 12 diz que sim)")
    ti = ".claude/hooks/_lib/test_isolation.py"
    tis = t.show(t.head, ti) or ""
    if ti not in parts.get(2, set()) or "## Axis 4 — the host Claude Code CLI" not in tis \
            or 'CC_STUB_DIRNAME = "claude-code-stub"' not in tis:
        raise AssertionError("%s nao muda na parte 2 com o Eixo 4 (a condicao 12 diz que esta la)" % ti)
    # O release.sh muda no bloco por-release E no probe de assinatura do preflight (`--yes`),
    # e o envelope do GA declara, na condicao 15, que ele e entregue so pelo upgrade.sh.
    rel_head = t.show(t.head, ".claude/scripts/local/release.sh") or ""
    rel_base = t.show(t.base, ".claude/scripts/local/release.sh") or ""
    if not re.search(r"gpg --yes\b[^\n]*--detach-sign", rel_head) or re.search(r"gpg --yes\b", rel_base):
        raise AssertionError("o probe de assinatura do preflight do release.sh nao passa a chamar o gpg com --yes na faixa")
    gae = t.show(t.head, GA_ENVELOPE) or ""
    m15 = re.search(r"(?m)^[ \t]*(?:- )?15\. ", gae)
    m16 = re.search(r"(?m)^[ \t]*(?:- )?16\. ", gae[m15.end():]) if m15 else None
    if not m15 or not m16 or "É entregue, e só pelo `upgrade.sh`" not in gae[m15.end():m15.end() + m16.start()]:
        raise AssertionError("a condicao 15 do envelope do GA (%s) nao declara o release.sh entregue so pelo upgrade.sh" % GA_ENVELOPE)
    return "%d caminhos: %s dentro das partes, %d fora (declarado); governance e local no declarado" % (
        len(every), "+".join(str(len(parts[k])) for k in sorted(parts)), len(out & every))


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
                            {"NPARTS": str(len(parts)), "BASE_TAG": "v1.4.1", "CANDIDATE_SHA": t.head,
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


CHECKS: List[Tuple[str, Callable[[Tree], str]]] = [
    ("C0-tree", c0_tree), ("C0-npm", c0_npm_rc), ("C1-annex-v1.4.0", c1_annex),
    ("C2-carried-1.4.1", c2_carried), ("C3-fn04", c3_fn04), ("C4-relaunch-out", c4_relaunch_out),
    ("C5-pin", c5_pin), ("C6-effort", c6_effort), ("C7-cc-floor", c7_cc_floor),
    ("C8-adapter", c8_adapter), ("C9-codex-pin", c9_codex), ("C10-tools", c10_tools),
    ("C11-scope", c11_scope), ("C12-plan-decisions", c12_plan_decisions),
]


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
    fails = infra = 0
    for cid, fn in CHECKS:
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
    print("SONDA: %d FALSA(S), %d sem medida" % (fails, infra))
    if infra:
        return 2
    return 1 if fails else 0


if __name__ == "__main__":
    sys.exit(main())
