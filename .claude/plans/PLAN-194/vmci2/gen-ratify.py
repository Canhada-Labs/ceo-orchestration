#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""gen-ratify.py — preenche o sentinel ``vmci2-approved.md`` a partir de um Anchor-SHA.

PLAN-194, VM-CI 2: ratificação pós-fato dos bytes canônicos que os merges dos
PRs #4 e #5 puseram no ``main``. Este script NÃO assina, NÃO faz fetch, NÃO
escreve no git. Ele só lê objetos do git (``git show-ref``/``cat-file``/
``ls-tree``/``diff``/``archive``) e, no modo de escrita, grava 2 arquivos do
próprio PLAN-194: o registro do diff (``Record``) e o sentinel preenchido a
partir do rascunho.

Uso, da raiz do repositório, depois de ``git fetch origin``:

    python3 -I -B .claude/plans/PLAN-194/vmci2/gen-ratify.py --anchor <sha>
        escreve .claude/plans/PLAN-194/vmci2/pr4-pr5.patch e
        .claude/plans/PLAN-194/vmci2-approved.md (a partir do .draft)
    python3 -I -B .claude/plans/PLAN-194/vmci2/gen-ratify.py --anchor <sha> --check
        recalcula tudo e compara, byte a byte, com os 2 arquivos já gravados;
        não escreve nada

A Base é constante (BASE abaixo): não há opção para trocá-la.

Recusas (código 3), cada uma com mensagem «RECUSA R-x: ...»:
  R-a  o Anchor não é um SHA de 40 hexadecimais de um commit, é igual à Base,
       não descende da Base, ou não é alcançável a partir de --main-ref; ou
       --main-ref não é um nome COMPLETO sob ``refs/remotes/`` que exista
       exatamente com esse nome (padrão: refs/remotes/origin/main, como estava
       no último fetch). Nome curto não é aceito: uma tag ou um ramo com o
       mesmo nome curto sombrearia a ref remota;
  R-b  algum caminho que mudou entre a Base e o Anchor não é UTF-8 válido ou
       tem caractere de controle; ou algum caminho CANÔNICO fora do Scope
       mudou; ou algum caminho do KERNEL de arbitragem fora do Scope mudou;
       ou o conjunto dos caminhos que mudaram não é exatamente o medido
       (EXPECTED_CHANGED); ou os caminhos que mudaram e que o classificador
       do kernel dá como kernel não são exatamente os medidos
       (EXPECTED_KERNEL: o controle positivo do classificador — um
       classificador que respondesse 0 para tudo cai aqui). O oráculo
       canônico é o ``check_canonical_edit.py
       --is-canonical`` e o do kernel é o ``_is_kernel_path`` do
       ``check_arbitration_kernel.py``, os dois extraídos da BASE
       (``git archive``) e rodados num diretório vazio, sem depender da
       árvore de trabalho. Os do Anchor NÃO são executados: é código ainda
       não ratificado;
  R-c  algum caminho do Scope não é canônico, não mudou, não existe no Anchor,
       aparece mais de uma vez na árvore, ou não é arquivo comum;
  R-d  os bytes ou o modo de algum caminho do Scope no Anchor diferem dos
       REVISTOS (EXPECTED_BYTES abaixo, os mesmos do REVIEW-pr4-pr5.md), ou
       o Record difere byte a byte do revisto (EXPECTED_RECORD_SHA256): a
       assinatura ratifica só o que foi revisto;
  R-e  algum caminho do Scope mudou entre o Anchor e --main-ref: os bytes do
       main já não são os ratificados;
  R-f  (--check) o Record ou o sentinel gravados diferem do que o gerador
       produz agora; ou (escrita) o destino já existe com outro conteúdo, é
       link simbólico, ou o sentinel já tem ``.asc`` ao lado;
  R-g  algum dos 4 materiais (rascunho, revisão, controles, este gerador) na
       árvore de trabalho difere do blob dele em --main-ref, ou não está lá
       como arquivo comum: o que se assina é o que está publicado.
Código 2 = uso ou infraestrutura (git ausente, material ausente, oráculo que
não responde, erro inesperado). Código 0 = tudo conferido.

Determinismo: mesma entrada (repositório, Anchor, materiais) ⇒ mesmos bytes de
saída. O git roda com configuração global e de sistema desligadas, objetos de
substituição (``refs/replace``) e enxertos desligados, árvore de trabalho e
índice VAZIOS (nenhum .gitattributes interfere) e opções de diff explícitas;
o que ainda puder mudar a forma do diff (a configuração local do repositório,
outra versão do git) muda o Record e cai na R-d. Python ≥ 3.9, só biblioteca
padrão.
"""
from __future__ import annotations

import argparse
import hashlib
import io
import os
import re
import shutil
import subprocess
import sys
import tarfile
import tempfile
from pathlib import Path
from typing import Dict, List, Optional, Sequence, Tuple

# ---------------------------------------------------------------------------
# Constantes da ratificação
# ---------------------------------------------------------------------------

BASE = "3ecb388a72eb848b524b4619b19aac11b29fb1f2"
MAIN_REF_DEFAULT = "refs/remotes/origin/main"

SCOPE: Tuple[str, ...] = (
    ".claude/hooks/_lib/spool_writer.py",
    ".claude/hooks/_lib/tests/test_goap_planner.py",
    ".github/workflows/coverage.yml",
    ".github/workflows/formal-verify.yml",
    ".github/workflows/ownership-nightly.yml",
    ".github/workflows/smoke-install.yml",
    ".github/workflows/validate.yml",
)

# Bytes REVISTOS (REVIEW-pr4-pr5.md §1): caminho -> (sha256, tamanho, blob,
# modo). Mudar uma linha aqui é mudar o que foi revisto: exige revisão nova.
EXPECTED_BYTES: Dict[str, Tuple[str, int, str, str]] = {
    ".claude/hooks/_lib/spool_writer.py": (
        "1f0104a9f0794b9f025ae6f7614aa356be5308c8d75ad3e0636a765c4217cd88",
        115572, "2fbae393b895200045e75d8f9baf0721fce1431d", "100644"),
    ".claude/hooks/_lib/tests/test_goap_planner.py": (
        "658d77d176d70994f08424d7814e2ad78956ed67c082de3d48278eb4928e4b6c",
        17223, "8789326d6553537fbf9a50cffa6c72a7ed3b0fc6", "100644"),
    ".github/workflows/coverage.yml": (
        "e41dc4047068122eb06e1f6208897ea2a25e8e4707e960218765ae1aafcd27f2",
        14124, "2c5210b2bba3b2b2072f67b857af4a9d17c5c7d1", "100644"),
    ".github/workflows/formal-verify.yml": (
        "7fe9ee54f2e55e6f403914527dfad77e26d5afe8a1860a04472bdc7d747e8463",
        4156, "dc471e97e8e78d3379d4c6cbe4f4aaa2884bb44d", "100644"),
    ".github/workflows/ownership-nightly.yml": (
        "92342b8ce69f4269a1f4eb905ac9e14eec3cbc4194076d603fa1f130815e4d87",
        14976, "3547f97cb06f6cfcbdf84913d278dd43cc29a7fe", "100644"),
    ".github/workflows/smoke-install.yml": (
        "431ca942a9e60fbf2f5d49c1df133a68628e8b78acd04d8401450a056ba6a5b4",
        63294, "d562d0407194d24be1bf546dc7ab4037ec375910", "100644"),
    ".github/workflows/validate.yml": (
        "ada86947fc4404a2a66a81c1126d332f8ea040818515915fcc3a67b9a59845ef",
        97043, "7dbbf634432b6fb06bc918499f589f1329b5496f", "100644"),
}
# O Record revisto, byte a byte (REVIEW-pr4-pr5.md §1). Outro valor é recusa.
EXPECTED_RECORD_SHA256 = (
    "4817e9cdde0eef6c633a3b68ec0afcff51f85c435c98cb2148c25fddfc4f3ddd")

# O conjunto EXATO de caminhos que mudam entre a Base e o Anchor (medido;
# REVIEW-pr4-pr5.md §1). Qualquer caminho a mais ou a menos é recusa.
EXPECTED_CHANGED: Tuple[str, ...] = (
    ".claude/hooks/_lib/spool_writer.py",
    ".claude/hooks/_lib/tests/test_goap_planner.py",
    ".claude/hooks/tests/test_spool_first_append_durability.py",
    ".claude/scripts/derive-settings-baselines.py",
    ".claude/scripts/diagnose-output-hook.py",
    ".claude/scripts/goap-planner.py",
    ".github/workflows/coverage.yml",
    ".github/workflows/formal-verify.yml",
    ".github/workflows/ownership-nightly.yml",
    ".github/workflows/smoke-install.yml",
    ".github/workflows/validate.yml",
    "docs/formal-verification/breaker.cfg",
    "docs/formal-verification/breaker.pcal",
    "docs/formal-verification/breaker.tla",
    "docs/formal-verification/check-breaker-model.py",
    "docs/formal-verification/debate-convergence.cfg",
    "docs/formal-verification/plan-lifecycle.cfg",
    "docs/formal-verification/properties-proved.md",
    "docs/formal-verification/run-tlc.sh",
    "scripts/tests/historical-parallel.py",
    "scripts/tests/ownership-parallel.py",
    "scripts/tests/replay-parallel.py",
    "scripts/tests/test-upgrade-historical-adopter.sh",
    "scripts/tests/test_historical_parallel.py",
    "scripts/tests/test_install_state_replay.sh",
    "scripts/tests/test_ownership_parallel.py",
    "scripts/tests/test_replay_parallel.py",
    "tests/formal_verification/test_breaker_conformance.py",
)

# Os caminhos do KERNEL de arbitragem entre os que mudam entre a Base e o
# Anchor (medido; REVIEW-pr4-pr5.md §1). É o controle positivo embutido do
# classificador do kernel: outro conjunto é recusa.
EXPECTED_KERNEL: Tuple[str, ...] = (
    ".github/workflows/coverage.yml",
    ".github/workflows/validate.yml",
)

PLAN_DIR = ".claude/plans/PLAN-194"
MAT_DIR = PLAN_DIR + "/vmci2"
SENTINEL_REL = PLAN_DIR + "/vmci2-approved.md"
DRAFT_REL = SENTINEL_REL + ".draft"
RECORD_REL = MAT_DIR + "/pr4-pr5.patch"
REVIEW_REL = MAT_DIR + "/REVIEW-pr4-pr5.md"
CONTROL_REL = MAT_DIR + "/red-control.txt"
GENERATOR_REL = MAT_DIR + "/gen-ratify.py"
MATERIALS: Tuple[str, ...] = (DRAFT_REL, REVIEW_REL, CONTROL_REL,
                              GENERATOR_REL)
ORACLE_REL = ".claude/hooks/check_canonical_edit.py"
KERNEL_REL = ".claude/hooks/check_arbitration_kernel.py"

TOKEN_RE = re.compile(r"<<GERADOR:([A-Z0-9_]+)>>")
HEX40_RE = re.compile(r"^[0-9a-f]{40}$")
REMOTE_REF_RE = re.compile(r"^refs/remotes/[A-Za-z0-9._-]+(/[A-Za-z0-9._-]+)+$")
CONTROL_CHAR_RE = re.compile(r"[\x00-\x1f\x7f]")

# Classificador do kernel: roda num processo isolado, importa o módulo da
# Base extraída (argv[1] = diretório .claude/hooks extraído, argv[2] = raiz
# vazia) e responde «caminho<TAB>0|1» por linha do stdin.
KERNEL_PROBE = (
    "import sys\n"
    "from pathlib import Path\n"
    "sys.path.insert(0, sys.argv[1])\n"
    "import check_arbitration_kernel as k\n"
    "root = Path(sys.argv[2])\n"
    "for ln in sys.stdin.read().split('\\n'):\n"
    "    if ln:\n"
    "        print('%s\\t%d' % (ln, 1 if k._is_kernel_path(str(root / ln),"
    " root) else 0))\n"
)

EXIT_OK = 0
EXIT_INFRA = 2
EXIT_REFUSE = 3


class Refusal(Exception):
    def __init__(self, code: str, msg: str) -> None:
        super().__init__("RECUSA %s: %s" % (code, msg))


class Infra(Exception):
    pass


# ---------------------------------------------------------------------------
# git em ambiente neutro
# ---------------------------------------------------------------------------

def _neutral_env(extra: Optional[Dict[str, str]] = None) -> Dict[str, str]:
    env = {k: v for k, v in os.environ.items() if not k.startswith("GIT_")}
    env.update({
        "GIT_CONFIG_GLOBAL": os.devnull,
        "GIT_CONFIG_NOSYSTEM": "1",
        "GIT_ATTR_NOSYSTEM": "1",
        "GIT_NO_REPLACE_OBJECTS": "1",
        "GIT_GRAFT_FILE": os.devnull,
        "GIT_PAGER": "cat",
        "GIT_TERMINAL_PROMPT": "0",
        "GIT_OPTIONAL_LOCKS": "0",
        "LC_ALL": "C",
        "LANG": "C",
    })
    if extra:
        env.update(extra)
    return env


class Git:
    """Leitor de objetos do git. Roda num diretório vazio, com --git-dir."""

    def __init__(self, repo: Path, scratch: Path) -> None:
        self.repo = repo
        self.empty = scratch / "arvore-vazia"
        self.empty.mkdir()
        try:
            out = subprocess.run(
                ["git", "-C", str(repo), "rev-parse", "--absolute-git-dir",
                 "--git-common-dir"],
                capture_output=True, env=_neutral_env(), timeout=60)
        except (OSError, subprocess.TimeoutExpired) as e:
            raise Infra("git indisponível: %s" % e)
        if out.returncode != 0:
            raise Infra("não é um repositório git: %s" % repo)
        dirs = out.stdout.decode("utf-8", "replace").splitlines()
        if len(dirs) != 2:
            raise Infra("rev-parse inesperado: %r" % dirs)
        self.git_dir = dirs[0].strip()
        common = Path(dirs[1].strip())
        if not common.is_absolute():
            common = (repo / common).resolve()
        for d in (Path(self.git_dir), common):
            info_attr = d / "info" / "attributes"
            if info_attr.exists() and info_attr.stat().st_size > 0:
                raise Infra("%s existe e não está vazio: o diff deixaria de "
                            "ser determinístico; esvazie-o e rode de novo"
                            % info_attr)
        self.env = _neutral_env({
            "GIT_INDEX_FILE": str(scratch / "indice-inexistente"),
        })

    def run(self, args: Sequence[str], ok_codes: Sequence[int] = (0,),
            stdin: Optional[bytes] = None) -> Tuple[int, bytes]:
        cmd = ["git", "--no-replace-objects",
               "--git-dir=" + self.git_dir,
               "--work-tree=" + str(self.empty),
               "-c", "core.quotePath=true",
               "-c", "core.attributesFile=" + os.devnull,
               "-c", "attr.tree=",
               "-c", "advice.graftFileDeprecated=false",
               "-c", "diff.noprefix=false",
               "-c", "diff.mnemonicPrefix=false",
               "-c", "diff.relative=false",
               "-c", "diff.suppressBlankEmpty=false"] + list(args)
        try:
            p = subprocess.run(cmd, cwd=str(self.empty), env=self.env,
                               input=stdin, capture_output=True, timeout=600)
        except (OSError, subprocess.TimeoutExpired) as e:
            raise Infra("git falhou (%s): %s" % (" ".join(args[:3]), e))
        if p.returncode not in ok_codes:
            raise Infra("git %s saiu %d: %s" % (
                " ".join(args[:3]), p.returncode,
                p.stderr.decode("utf-8", "replace").strip()[:400]))
        return p.returncode, p.stdout

    def commit_sha(self, sha: str) -> Optional[str]:
        """O SHA, se for um commit deste repositório; None se não for."""
        rc, out = self.run(["cat-file", "-t", sha], ok_codes=(0, 1, 128))
        if rc != 0 or out.decode("ascii", "replace").strip() != "commit":
            return None
        return sha

    def remote_ref(self, ref: str) -> Optional[str]:
        """SHA do commit apontado EXATAMENTE por ``ref`` (show-ref --verify)."""
        rc, out = self.run(["show-ref", "--verify", "--", ref],
                           ok_codes=(0, 1, 128))
        if rc != 0:
            return None
        lines = out.decode("utf-8", "replace").splitlines()
        if len(lines) != 1:
            return None
        sha, _, name = lines[0].partition(" ")
        if name != ref or not HEX40_RE.match(sha):
            return None
        rc, out = self.run(["rev-parse", "--verify", "--quiet",
                            sha + "^{commit}"], ok_codes=(0, 1))
        peeled = out.decode("ascii", "replace").strip()
        return peeled if rc == 0 and HEX40_RE.match(peeled) else None

    def is_ancestor(self, a: str, b: str) -> bool:
        rc, _ = self.run(["merge-base", "--is-ancestor", a, b],
                         ok_codes=(0, 1))
        return rc == 0

    def changed(self, a: str, b: str, paths: Sequence[str] = ()) -> List[str]:
        args = ["diff", "--name-only", "-z", "--no-renames", "--no-ext-diff",
                a, b]
        if paths:
            args += ["--"] + list(paths)
        _, out = self.run(args)
        names = [n.decode("utf-8", "surrogateescape")
                 for n in out.split(b"\0") if n]
        return sorted(set(names))

    def entries(self, rev: str, path: str) -> List[Tuple[str, str, str]]:
        """Todos os registros (modo, tipo, objeto) do caminho no commit."""
        _, out = self.run(["ls-tree", "-z", "--full-tree", rev, "--", path])
        found: List[Tuple[str, str, str]] = []
        for r in out.split(b"\0"):
            if not r:
                continue
            meta, _, name = r.partition(b"\t")
            if name.decode("utf-8", "surrogateescape") == path:
                parts = meta.decode("ascii", "replace").split(" ")
                if len(parts) != 3:
                    raise Infra("ls-tree fora do formato: %r" % r[:200])
                found.append((parts[0], parts[1], parts[2]))
        return found

    def blob(self, obj: str) -> bytes:
        _, out = self.run(["cat-file", "blob", obj])
        return out

    def record(self, base: str, anchor: str, paths: Sequence[str]) -> bytes:
        _, out = self.run([
            "diff", "--full-index", "--no-ext-diff", "--no-textconv",
            "--no-color", "--no-renames", "--text", "-U3",
            "--inter-hunk-context=0", "--indent-heuristic",
            "--diff-algorithm=myers", "--src-prefix=a/", "--dst-prefix=b/",
            "-O" + os.devnull, base, anchor, "--"] + list(paths))
        return out

    def hooks_tree(self, rev: str, dest: Path) -> Path:
        """Extrai .claude/hooks do commit para dest (só arquivos e diretórios)."""
        _, data = self.run(["archive", "--format=tar", rev, "--",
                            ".claude/hooks"])
        dest.mkdir(parents=True)
        with tarfile.open(fileobj=io.BytesIO(data), mode="r:") as tf:
            for m in tf.getmembers():
                name = m.name.rstrip("/")
                parts = name.split("/")
                parent_dir = m.isdir() and name in (".claude", ".claude/hooks")
                if (name.startswith("/") or ".." in parts or "" in parts
                        or not (parent_dir
                                or name.startswith(".claude/hooks/"))):
                    raise Infra("membro inesperado no git archive: %r" % name)
                target = dest.joinpath(*parts)
                if m.isdir():
                    target.mkdir(parents=True, exist_ok=True)
                elif m.isreg():
                    target.parent.mkdir(parents=True, exist_ok=True)
                    fh = tf.extractfile(m)
                    if fh is None:
                        raise Infra("membro ilegível: %r" % name)
                    target.write_bytes(fh.read())
                else:
                    raise Infra("membro que não é arquivo comum: %r" % name)
        for rel in (ORACLE_REL, KERNEL_REL):
            if not (dest / rel).is_file():
                raise Infra("%s ausente em %s" % (rel, rev))
        return dest


# ---------------------------------------------------------------------------
# Oráculos da Base (canônico e kernel), em processo isolado
# ---------------------------------------------------------------------------

def _probe(argv: Sequence[str], paths: Sequence[str], cwd: Path, home: Path,
           what: str) -> Dict[str, int]:
    if not paths:
        return {}
    env = {
        "PATH": os.environ.get("PATH", "/usr/bin:/bin"),
        "HOME": str(home),
        "LC_ALL": "C",
        "LANG": "C",
        "CLAUDE_PROJECT_DIR": str(cwd),
    }
    try:
        p = subprocess.run(
            list(argv), cwd=str(cwd), env=env,
            input=("\n".join(paths) + "\n").encode("utf-8"),
            capture_output=True, timeout=300)
    except (OSError, subprocess.TimeoutExpired) as e:
        raise Infra("%s não respondeu: %s" % (what, e))
    if p.returncode != 0:
        raise Infra("%s saiu %d: %s" % (
            what, p.returncode, p.stderr.decode("utf-8", "replace")[:400]))
    lines = p.stdout.decode("utf-8", "replace").splitlines()
    if len(lines) != len(paths):
        raise Infra("%s devolveu %d linhas para %d caminhos" % (
            what, len(lines), len(paths)))
    result: Dict[str, int] = {}
    for want, line in zip(paths, lines):
        got, sep, flag = line.rpartition("\t")
        if sep != "\t" or got != want or flag not in ("0", "1"):
            raise Infra("resposta do %s fora do formato: %r" % (what, line))
        result[want] = int(flag)
    return result


def run_oracle(hooks: Path, paths: Sequence[str], cwd: Path,
               home: Path) -> Dict[str, int]:
    return _probe([sys.executable, "-I", "-B", str(hooks / ORACLE_REL),
                   "--is-canonical", "-"], paths, cwd, home,
                  "oráculo canônico")


def run_kernel(hooks: Path, paths: Sequence[str], cwd: Path,
               home: Path) -> Dict[str, int]:
    kdir = (hooks / KERNEL_REL).parent
    return _probe([sys.executable, "-I", "-B", "-c", KERNEL_PROBE,
                   str(kdir), str(cwd)], paths, cwd, home,
                  "classificador do kernel")


# ---------------------------------------------------------------------------
# Utilidades
# ---------------------------------------------------------------------------

def sha256(data: bytes) -> str:
    return hashlib.sha256(data).hexdigest()


def fmt_int(n: int) -> str:
    """Milhar com ponto (pt-BR): 115572 -> 115.572."""
    s = str(n)
    out = []
    while len(s) > 3:
        out.insert(0, s[-3:])
        s = s[:-3]
    out.insert(0, s)
    return ".".join(out)


def record_stats(rec: bytes) -> str:
    adds = dels = files = 0
    in_hunk = False
    for ln in rec.split(b"\n"):
        if ln.startswith(b"diff --git "):
            files += 1
            in_hunk = False
        elif ln.startswith(b"@@ "):
            in_hunk = True
        elif in_hunk and ln.startswith(b"+"):
            adds += 1
        elif in_hunk and ln.startswith(b"-"):
            dels += 1
    nlines = rec.count(b"\n")
    return "%d arquivos, +%s −%s; %s linhas, %s bytes" % (
        files, fmt_int(adds), fmt_int(dels), fmt_int(nlines),
        fmt_int(len(rec)))


def read_material(repo: Path, rel: str) -> bytes:
    p = repo / rel
    if p.is_symlink() or not p.is_file():
        raise Infra("material ausente ou não é arquivo comum: %s" % rel)
    return p.read_bytes()


def _check_path_text(path: str) -> None:
    try:
        path.encode("utf-8")
    except UnicodeEncodeError:
        raise Refusal("R-b", "caminho mudado que não é UTF-8 válido: %r"
                      % path)
    if CONTROL_CHAR_RE.search(path):
        raise Refusal("R-b", "caminho mudado com caractere de controle: %r"
                      % path)


# ---------------------------------------------------------------------------
# Núcleo
# ---------------------------------------------------------------------------

def compute(repo: Path, anchor_in: str, main_ref: str,
            scratch: Path) -> Dict[str, object]:
    g = Git(repo, scratch)

    # R-a — Anchor e --main-ref; Base ≤ Anchor ≤ main-ref.
    if not HEX40_RE.match(anchor_in):
        raise Refusal("R-a", "o Anchor tem de ser um SHA de 40 hexadecimais "
                      "minúsculos, não um nome de ref nem um SHA curto: %r"
                      % anchor_in)
    if not REMOTE_REF_RE.match(main_ref) or ".." in main_ref:
        raise Refusal("R-a", "--main-ref tem de ser um nome completo sob "
                      "refs/remotes/ (por exemplo refs/remotes/origin/main), "
                      "não um nome curto: %r" % main_ref)
    anchor = g.commit_sha(anchor_in)
    if anchor is None:
        raise Refusal("R-a", "Anchor %r não é um commit deste repositório "
                      "(faltou git fetch?)" % anchor_in)
    base = g.commit_sha(BASE)
    if base is None:
        raise Infra("a Base %s não é um commit deste repositório" % BASE)
    main = g.remote_ref(main_ref)
    if main is None:
        raise Refusal("R-a", "--main-ref %r não existe exatamente com esse "
                      "nome, ou não aponta para um commit" % main_ref)
    if anchor == base:
        raise Refusal("R-a", "Anchor igual à Base: não há bytes novos")
    if not g.is_ancestor(base, anchor):
        raise Refusal("R-a", "a Base %s não é ancestral do Anchor %s"
                      % (base[:12], anchor[:12]))
    if not g.is_ancestor(anchor, main):
        raise Refusal("R-a", "o Anchor %s não é alcançável de %s (%s)"
                      % (anchor[:12], main_ref, main[:12]))

    # R-b / R-c — o que mudou entre a Base e o Anchor.
    changed = g.changed(base, anchor)
    for p in changed:
        _check_path_text(p)
    to_classify = sorted(set(changed) | set(SCOPE))
    home = scratch / "home"
    home.mkdir()
    hooks = g.hooks_tree(base, scratch / "hooks-base")
    flags = run_oracle(hooks, to_classify, g.empty, home)
    canonical = {p for p in to_classify if flags[p] == 1}
    outside = sorted((canonical & set(changed)) - set(SCOPE))
    if outside:
        raise Refusal("R-b", "caminho(s) canônico(s) fora do Scope mudaram "
                      "entre Base e Anchor: %s" % ", ".join(outside))
    kflags = run_kernel(hooks, to_classify, g.empty, home)
    kernel = {p for p in to_classify if kflags[p] == 1}
    k_outside = sorted((kernel & set(changed)) - set(SCOPE))
    if k_outside:
        raise Refusal("R-b", "caminho(s) do kernel de arbitragem fora do "
                      "Scope mudaram entre Base e Anchor: %s"
                      % ", ".join(k_outside))
    not_canon = sorted(set(SCOPE) - canonical)
    if not_canon:
        raise Refusal("R-c", "caminho(s) do Scope que o oráculo não dá "
                      "como canônicos: %s" % ", ".join(not_canon))
    unchanged = sorted(set(SCOPE) - set(changed))
    if unchanged:
        raise Refusal("R-c", "caminho(s) do Scope que não mudaram entre Base "
                      "e Anchor (Anchor errado?): %s" % ", ".join(unchanged))
    extra = sorted(set(changed) - set(EXPECTED_CHANGED))
    missing = sorted(set(EXPECTED_CHANGED) - set(changed))
    if extra or missing:
        raise Refusal("R-b", "o conjunto de caminhos que mudam entre Base e "
                      "Anchor não é o medido — a mais: %s; a menos: %s" % (
                          ", ".join(extra) or "nenhum",
                          ", ".join(missing) or "nenhum"))
    k_changed = sorted(kernel & set(changed))
    if k_changed != sorted(EXPECTED_KERNEL):
        raise Refusal("R-b", "os caminhos do kernel de arbitragem que mudam "
                      "entre Base e Anchor não são os medidos — o "
                      "classificador da Base deu: %s; o medido: %s" % (
                          ", ".join(k_changed) or "nenhum",
                          ", ".join(sorted(EXPECTED_KERNEL))))

    # R-c / R-d — bytes e modo no Anchor.
    files: List[Tuple[str, str, int, str]] = []
    for path in SCOPE:
        ents = g.entries(anchor, path)
        if not ents:
            raise Refusal("R-c", "%s não existe no Anchor" % path)
        if len(ents) != 1:
            raise Refusal("R-c", "%s aparece %d vezes na árvore do Anchor"
                          % (path, len(ents)))
        mode, typ, obj = ents[0]
        if typ != "blob" or mode not in ("100644", "100755"):
            raise Refusal("R-c", "%s não é arquivo comum no Anchor (modo %s)"
                          % (path, mode))
        data = g.blob(obj)
        digest = sha256(data)
        exp = EXPECTED_BYTES[path]
        if (digest, len(data), obj, mode) != exp:
            raise Refusal("R-d", "%s no Anchor tem sha256 %s (%d bytes, blob "
                          "%s, modo %s); o revisto é %s (%d bytes, blob %s, "
                          "modo %s)" % (
                              path, digest, len(data), obj[:12], mode,
                              exp[0], exp[1], exp[2][:12], exp[3]))
        files.append((path, digest, len(data), obj))

    # R-e — o main não mudou esses caminhos depois do Anchor.
    later = g.changed(anchor, main, SCOPE)
    if later:
        raise Refusal("R-e", "caminho(s) do Scope mudaram entre o Anchor e "
                      "%s: %s" % (main_ref, ", ".join(later)))

    # R-g — os materiais da árvore de trabalho são os publicados em main-ref.
    for rel in MATERIALS:
        ents = g.entries(main, rel)
        if len(ents) != 1 or ents[0][1] != "blob" or ents[0][0] != "100644":
            raise Refusal("R-g", "%s não está em %s como 1 arquivo comum "
                          "(modo 100644)" % (rel, main_ref))
        if read_material(repo, rel) != g.blob(ents[0][2]):
            raise Refusal("R-g", "%s na árvore de trabalho difere do blob "
                          "em %s" % (rel, main_ref))

    # R-d — o Record é o revisto, byte a byte.
    rec = g.record(base, anchor, SCOPE)
    rec_paths = sorted({ln.split(b" b/", 1)[1].decode("utf-8", "replace")
                        for ln in rec.split(b"\n")
                        if ln.startswith(b"diff --git a/")})
    if rec_paths != sorted(SCOPE):
        raise Infra("o Record não cobre exatamente o Scope: %s" % rec_paths)
    if sha256(rec) != EXPECTED_RECORD_SHA256:
        raise Refusal("R-d", "o Record tem sha256 %s (%s); o revisto é %s — "
                      "a forma do diff mudou (configuração local do "
                      "repositório? outra versão do git?)" % (
                          sha256(rec), record_stats(rec),
                          EXPECTED_RECORD_SHA256))

    return {"anchor": anchor, "base": base, "main": main, "files": files,
            "record": rec, "changed": changed, "canonical": sorted(canonical),
            "kernel": sorted(kernel)}


def fill(draft: str, values: Dict[str, str]) -> str:
    unknown = sorted(set(TOKEN_RE.findall(draft)) - set(values))
    if unknown:
        raise Infra("rascunho com marcador desconhecido: %s" % unknown)
    missing = sorted(set(values) - set(TOKEN_RE.findall(draft)))
    if missing:
        raise Infra("rascunho sem o marcador: %s" % missing)
    out = TOKEN_RE.sub(lambda m: values[m.group(1)], draft)
    if "<<GERADOR:" in out:
        raise Infra("marcador restante depois do preenchimento")
    return out


def build(repo: Path, res: Dict[str, object]) -> Tuple[bytes, bytes]:
    anchor = str(res["anchor"])
    files = res["files"]  # type: ignore[assignment]
    rec = res["record"]  # type: ignore[assignment]
    assert isinstance(rec, bytes)
    draft = read_material(repo, DRAFT_REL).decode("utf-8")
    review = read_material(repo, REVIEW_REL)
    control = read_material(repo, CONTROL_REL)
    generator = read_material(repo, GENERATOR_REL)
    me = Path(__file__).resolve().read_bytes()
    if me != generator:
        raise Infra("este gerador não é byte a byte o %s do repositório: "
                    "rode a cópia do repositório" % GENERATOR_REL)
    sha_lines = "\n".join("File-sha256: %s %s" % (p, d)
                          for p, d, _, _ in files)  # type: ignore[misc]
    table = "\n".join("  - `%s`: %s bytes, blob `%s…`" % (p, fmt_int(n), o[:12])
                      for p, _, n, o in files)  # type: ignore[misc]
    values = {
        "ANCHOR_SHA": anchor,
        "BASE_SHA": str(res["base"]),
        "FILE_SHA256_LINES": sha_lines,
        "FILE_TABLE": table,
        "RECORD_SHA256": sha256(rec),
        "RECORD_STATS": record_stats(rec),
        "REVIEW_SHA256": sha256(review),
        "CONTROL_SHA256": sha256(control),
        "GENERATOR_SHA256": sha256(generator),
    }
    sentinel = fill(draft, values).encode("utf-8")
    return rec, sentinel


def write_atomic(path: Path, data: bytes, rel: str) -> str:
    if path.is_symlink():
        raise Refusal("R-f", "%s é link simbólico" % rel)
    if path.exists():
        if path.read_bytes() == data:
            return "igual (nada a fazer)"
        raise Refusal("R-f", "%s já existe com outro conteúdo: apague-o à mão "
                      "se for mesmo para regerar" % rel)
    tmp = path.with_name("." + path.name + ".tmp-gen")
    try:
        fh = open(tmp, "xb")
    except FileExistsError:
        raise Infra("temporário sobrando de uma execução anterior: %s — "
                    "apague-o à mão" % tmp)
    with fh:
        fh.write(data)
        fh.flush()
        os.fsync(fh.fileno())
    os.replace(tmp, path)
    return "gravado"


def run(a: argparse.Namespace) -> int:
    repo = Path(a.repo).resolve()
    scratch = Path(tempfile.mkdtemp(prefix="gen-ratify-"))
    try:
        res = compute(repo, a.anchor.strip(), a.main_ref, scratch)
        rec, sentinel = build(repo, res)
        print("Anchor-SHA: %s" % res["anchor"])
        print("Base-SHA:   %s" % res["base"])
        print("main-ref:   %s = %s" % (a.main_ref, res["main"]))
        changed = res["changed"]  # type: ignore[assignment]
        print("caminhos que mudaram entre Base e Anchor: %d; canônicos: %s; "
              "do kernel: %s" % (
                  len(changed),  # type: ignore[arg-type]
                  ", ".join(p for p in res["canonical"]  # type: ignore
                            if p in changed),  # type: ignore[operator]
                  ", ".join(p for p in res["kernel"]  # type: ignore
                            if p in changed)))  # type: ignore[operator]
        for p, d, n, o in res["files"]:  # type: ignore[misc]
            print("File-sha256: %s %s (%d bytes, blob %s)" % (p, d, n, o[:12]))
        print("Record-sha256: %s (%s)" % (sha256(rec), record_stats(rec)))
        rec_p = repo / RECORD_REL
        sen_p = repo / SENTINEL_REL
        asc_p = repo / (SENTINEL_REL + ".asc")
        if a.check:
            for p, data in ((rec_p, rec), (sen_p, sentinel)):
                if p.is_symlink() or not p.is_file():
                    raise Refusal("R-f", "%s ausente" % p.relative_to(repo))
                if p.read_bytes() != data:
                    raise Refusal("R-f", "%s difere do que o gerador produz "
                                  "agora" % p.relative_to(repo))
            print("OK: Record e sentinel conferem byte a byte (sha256 do "
                  "sentinel %s)" % sha256(sentinel))
            return EXIT_OK
        if asc_p.exists() or asc_p.is_symlink():
            if not (sen_p.is_file() and sen_p.read_bytes() == sentinel
                    and rec_p.is_file() and rec_p.read_bytes() == rec):
                raise Refusal("R-f", "o sentinel já tem .asc ao lado e o "
                              "conteúdo mudaria: não regravo um arquivo "
                              "assinado")
        print("%s: %s" % (RECORD_REL, write_atomic(rec_p, rec, RECORD_REL)))
        print("%s: %s" % (SENTINEL_REL,
                          write_atomic(sen_p, sentinel, SENTINEL_REL)))
        print("OK: sha256 do sentinel %s" % sha256(sentinel))
        return EXIT_OK
    finally:
        shutil.rmtree(scratch, ignore_errors=True)


def main(argv: Optional[Sequence[str]] = None) -> int:
    for stream in (sys.stdout, sys.stderr):
        try:
            stream.reconfigure(errors="backslashreplace")  # type: ignore
        except (AttributeError, ValueError):
            pass
    ap = argparse.ArgumentParser(description=__doc__.split("\n\n")[0])
    ap.add_argument("--anchor", required=True,
                    help="SHA de 40 hexadecimais do commit do main que "
                    "carrega os bytes")
    ap.add_argument("--main-ref", default=MAIN_REF_DEFAULT,
                    help="nome completo sob refs/remotes/ (padrão %s)"
                    % MAIN_REF_DEFAULT)
    ap.add_argument("--repo", default=".")
    ap.add_argument("--check", action="store_true",
                    help="só confere; não escreve nada")
    a = ap.parse_args(argv)
    try:
        return run(a)
    except Refusal as e:
        sys.stdout.flush()
        print(str(e), file=sys.stderr)
        return EXIT_REFUSE
    except Infra as e:
        sys.stdout.flush()
        print("INFRA: %s" % e, file=sys.stderr)
        return EXIT_INFRA
    except Exception as e:  # noqa: BLE001 — fora do contrato vira INFRA
        sys.stdout.flush()
        print("INFRA: erro inesperado (%s: %s)" % (type(e).__name__, e),
              file=sys.stderr)
        return EXIT_INFRA


if __name__ == "__main__":
    sys.exit(main())
