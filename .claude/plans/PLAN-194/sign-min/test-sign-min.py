#!/usr/bin/env python3
"""Harness do molde «SIGN mínimo» (sign-min) — PLAN-194, S363.

Fora dos ``testpaths`` (o hífen no nome impede a coleta). Python stdlib.
Monta, num diretório descartável, um origin sintético (``.claude/hooks``
real do HEAD sob teste, o molde, stubs dos 13 gates, pytest.ini mínimo e o
pacote ``PLAN-900/pk1``), clona-o com os comandos do roteiro e roda o SIGN
sob ``env -i`` em cada caso (E, R, H, F, K), com retrato da recusa,
mutantes do próprio SIGN e plantios conferidos; depois os censos C1–C5 e
um ensaio ``--dry-run`` real com os materiais do W5b.

Uso:
  python3 test-sign-min.py --base <dir descartável> --w5b <sombra mat-w5b> [--so A,B] [--manter]

rc 0 só com a linha ``EVIDÊNCIA:`` (corrida completa, sem ``--so``).
"""
from __future__ import annotations

import argparse
import ast
import fcntl
import glob
import hashlib
import io
import json
import os
import pty
import re
import resource
import shutil
import signal
import subprocess
import sys
import tarfile
import tempfile
import termios
import threading
import time
import traceback
import unicodedata
from typing import Callable, Dict, List, Optional, Set, Tuple

AQUI = os.path.dirname(os.path.abspath(__file__))
REPO = os.path.realpath(os.path.join(AQUI, "..", "..", "..", ".."))
MOLDE = ".claude/plans/PLAN-194/sign-min"
ENTRADA = MOLDE + "/OWNER-SIGN.sh"
NUCLEO = MOLDE + "/sign_min.py"
BLOCO = MOLDE + "/bloco-comum.md"
HARNESS = MOLDE + "/test-sign-min.py"
ARQS_MOLDE = [ENTRADA, NUCLEO, BLOCO, HARNESS]
PLAN = "PLAN-900"
PACOTE = "pk1"
DADOS = ".claude/plans/PLAN-900/pk1/sign.tsv"
PATCH = ".claude/plans/PLAN-900/pk1/pk1.patch"
SENT = ".claude/plans/PLAN-900/pk1-approved.md"
ASC = SENT + ".asc"
RAIL = ".claude/plans/PLAN-900/pk1/rail-round-1.md"
NOME = "Fixture Signer"
EMAIL = "signer@example.invalid"
SIS_PATH = "/usr/bin:/bin:/usr/sbin:/sbin"


class Falha(Exception):
    pass


def afirma(cond: bool, msg: str) -> None:
    if not cond:
        raise Falha(msg)


def sha256b(dados: bytes) -> str:
    return hashlib.sha256(dados).hexdigest()


def sha256f(caminho: str) -> str:
    with open(caminho, "rb") as fh:
        return sha256b(fh.read())


def sha1_blob(dados: bytes) -> str:
    return hashlib.sha1(b"blob %d\0" % len(dados) + dados).hexdigest()


def ident(caminho: str) -> str:
    return hashlib.sha256(caminho.encode()).hexdigest()[:12]


def le(caminho: str) -> bytes:
    with open(caminho, "rb") as fh:
        return fh.read()


def grava(caminho: str, dados: bytes, modo: Optional[int] = None) -> None:
    os.makedirs(os.path.dirname(caminho), exist_ok=True)
    with open(caminho, "wb") as fh:
        fh.write(dados)
    if modo is not None:
        os.chmod(caminho, modo)


# ---------------------------------------------------------------------------
# contexto global da corrida
# ---------------------------------------------------------------------------

class G:
    h = ""
    atual = ""
    home_h = ""
    gnupg = ""
    fpr1 = ""
    fpr2 = ""
    git_real = ""
    gpg_real = ""
    py = ""
    pyub = ""
    base_git = ""
    b0 = ""
    b0_tree = ""
    cat: Dict[str, object] = {}
    saidas: List[Tuple[str, str]] = []
    executados: List[str] = []
    mutantes_vermelhos: List[str] = []
    tmp_antes: Set[str] = set()
    manter = False
    inicio = 0.0
    marca_func = ""
    ensaio = ""
    verboso = False
    sem_ensaio = False


def env_h(extra: Optional[Dict[str, str]] = None) -> Dict[str, str]:
    env = {
        "PATH": SIS_PATH, "HOME": G.home_h, "LANG": "C", "GIT_CONFIG_NOSYSTEM": "1",
        "GIT_AUTHOR_NAME": NOME, "GIT_AUTHOR_EMAIL": EMAIL,
        "GIT_COMMITTER_NAME": NOME, "GIT_COMMITTER_EMAIL": EMAIL,
    }
    if G.gnupg:
        env["GNUPGHOME"] = G.gnupg
    if extra:
        env.update(extra)
    return env


def sh(argv: List[str], cwd: Optional[str] = None, env: Optional[Dict[str, str]] = None,
       entrada: Optional[bytes] = None, ok: bool = True) -> Tuple[int, bytes, bytes]:
    p = subprocess.run(argv, cwd=cwd, env=env if env is not None else env_h(),
                       input=entrada, stdout=subprocess.PIPE, stderr=subprocess.PIPE)
    if ok and p.returncode != 0:
        raise Falha("comando do harness saiu rc %d: %s — %s" % (
            p.returncode, " ".join(argv[:6]), p.stderr.decode("utf-8", "replace")[-400:]))
    return p.returncode, p.stdout, p.stderr


def git(args: List[str], cwd: Optional[str] = None, entrada: Optional[bytes] = None,
        ok: bool = True, env: Optional[Dict[str, str]] = None) -> bytes:
    return sh([G.git_real] + args, cwd=cwd, entrada=entrada, ok=ok, env=env)[1]


def gitb(gitdir: str, args: List[str], entrada: Optional[bytes] = None,
         env: Optional[Dict[str, str]] = None) -> bytes:
    return git(["--git-dir=" + gitdir] + args, entrada=entrada, env=env)


# ---------------------------------------------------------------------------
# catálogo do núcleo (importado sem rodar o main)
# ---------------------------------------------------------------------------

CODIGO_CAT = (
    "import importlib.util, json, sys\n"
    "spec = importlib.util.spec_from_file_location('sign_min_cat', sys.argv[1])\n"
    "m = importlib.util.module_from_spec(spec)\n"
    "spec.loader.exec_module(m)\n"
    "print(json.dumps({'MENSAGENS': m.MENSAGENS, 'rotulo': sorted(m.ROTULOS), 'motivo': sorted(m.MOTIVOS),\n"
    "  'regra': sorted(m.REGRAS), 'campo': sorted(m.CAMPOS), 'nome': sorted(m.NOMES),\n"
    "  'var': sorted(m.VARS), 'p': sorted(m.PASSADAS)}))\n"
)


def carrega_catalogo() -> None:
    _rc, out, _err = sh([G.py, "-I", "-B", "-c", CODIGO_CAT, os.path.join(REPO, NUCLEO)],
                        env={"PATH": SIS_PATH})
    G.cat = json.loads(out.decode())


def msg(chave: str, **valores: object) -> str:
    modelo = G.cat["MENSAGENS"][chave]  # type: ignore[index]
    return modelo.format(**{k: str(v) for k, v in valores.items()})


def regex_modelo(modelo: str) -> str:
    partes = re.split(r"(\{[a-z]+\})", modelo)
    saida = []
    for parte in partes:
        m = re.match(r"^\{([a-z]+)\}$", parte)
        if m is None:
            saida.append(re.escape(parte))
        elif m.group(1) in G.cat:
            valores = G.cat[m.group(1)]  # type: ignore[index]
            saida.append("(?:" + "|".join(re.escape(v) for v in valores) + ")")  # type: ignore[union-attr]
        else:
            saida.append(r"[A-Za-z0-9._/@:+=,?-]{0,200}")
    return "^" + "".join(saida) + "$"


# ---------------------------------------------------------------------------
# censo de palavras (§9)
# ---------------------------------------------------------------------------

CONFUSAVEIS = {
    "\u0430": "a", "\u0432": "b", "\u0435": "e", "\u0451": "e", "\u043a": "k", "\u043c": "m",
    "\u043d": "h", "\u043e": "o", "\u0440": "p", "\u0441": "c", "\u0442": "t", "\u0443": "y",
    "\u0445": "x", "\u0455": "s", "\u0456": "i", "\u0457": "i", "\u0458": "j", "\u0501": "d",
    "\u04bb": "h", "\u04cf": "l", "\u04af": "y",
    "\u03b1": "a", "\u03b2": "b", "\u03b5": "e", "\u03b7": "n", "\u03b9": "i", "\u03ba": "k",
    "\u03bd": "v", "\u03bf": "o", "\u03c1": "p", "\u03c4": "t", "\u03c5": "u", "\u03c7": "x",
    "\u03c9": "w",
    "\u0131": "i", "\u0237": "j", "\u0142": "l", "\u00f8": "o", "\u0111": "d",
    "\u2010": "-", "\u2011": "-", "\u2012": "-", "\u2013": "-", "\u2014": "-", "\u2015": "-",
    "\u2212": "-", "\ufe63": "-", "\uff0d": "-",
}
RADICAIS = ("landou landad jaland interromp recuper receita recipe abort desfe desfaz revert restaur "
            "rollback publicad publicou publish preexist instavel flaky recovered interrupted lote "
            "nadapublic").split()
TOKENS_PROIBIDOS = set((
    "undo rm run rerun retry remove delete reset checkout prune push please try execute executar rode "
    "rodar remova remover apague apagar restaure refaca tente digite confira corrija edite cole sudo "
    "manually manualmente").split())


def normaliza(texto: str) -> str:
    t = unicodedata.normalize("NFKC", texto).casefold()
    t = "".join(c for c in unicodedata.normalize("NFD", t) if unicodedata.category(c) != "Mn")
    t = "".join(c for c in t if unicodedata.category(c) != "Cf")
    t = "".join(CONFUSAVEIS.get(c, c) for c in t)
    t = "".join(CONFUSAVEIS.get(c, c) for c in unicodedata.normalize("NFD", t)
                if unicodedata.category(c) != "Mn")
    return t


def palavras_proibidas(texto: str) -> List[str]:
    t = normaliza(texto)
    s1 = re.sub(r"[^a-z0-9]", "", t)
    s2 = re.findall(r"[a-z0-9]+", t)
    achados = [r for r in RADICAIS if r in s1]
    achados += sorted(set(s2) & TOKENS_PROIBIDOS)
    return achados


# ---------------------------------------------------------------------------
# fixture
# ---------------------------------------------------------------------------

MARCA_FUNC_MODELO = '''
import os as _os
import tempfile as _tf
def marca(nome):
    d = @ATUAL@
    with open(_os.path.join(d, "ordem.log"), "a") as fh:
        fh.write("%s %d %d\\n" % (nome, _os.getpid(), _os.getpgid(0)))
    with open(_os.path.join(d, "env-" + nome + ".txt"), "w") as fh:
        for k in sorted(_os.environ):
            if k in ("GNUPGHOME", "GPG_TTY", "PYTHONUNBUFFERED", "TMPDIR"):
                fh.write(k + "=" + _os.environ[k] + "\\n")
            else:
                fh.write(k + "\\n")
        fh.write("@tempdir=" + _tf.gettempdir() + "\\n")
'''

GATES = [
    ".claude/scripts/check-test-env-hygiene.py", ".claude/scripts/env-inventory-check.py",
    ".claude/scripts/check-active-hooks-executable.py", ".claude/scripts/check-contamination.sh",
    "scripts/build-plugin.py", ".claude/scripts/gen-command-skill-hook-map.py",
    ".claude/scripts/check-docs-freshness.py", ".claude/scripts/check-docs-drift.py",
    ".claude/scripts/local/verify-counts.sh", ".claude/scripts/check-claude-md-claims.py",
    ".claude/scripts/check-ceremony-script.py", ".claude/scripts/check-staleness.py",
    ".claude/scripts/validate-governance.sh",
]


def py_marca(nome: str, corpo: str = "") -> bytes:
    return ("#!/usr/bin/env python3\n" + G.marca_func + "\nmarca(%r)\n" % nome + corpo).encode()


def sh_marca(nome: str, corpo: str = "") -> bytes:
    return ("#!/bin/bash\npython3 -B tools/marca.py %s\n" % nome + corpo).encode()


def arquivos_base() -> Dict[str, Tuple[str, bytes]]:
    a: Dict[str, Tuple[str, bytes]] = {}
    a["README.md"] = ("100644", b"fixture sign-min\n")
    a["pytest.ini"] = ("100644", b"[pytest]\ntestpaths = tests\nmarkers =\n    serial: serial\n")
    a["tools/marca.py"] = ("100644", ("import sys\n" + G.marca_func + "\nmarca(sys.argv[1])\n").encode())
    a["tools/hard_ok.py"] = ("100644", py_marca("hard-ok"))
    a["tests/test_base.py"] = ("100644", (
        "import pytest\n" + G.marca_func +
        "\n\ndef test_a():\n    marca('teste-a')\n\n\n@pytest.mark.serial\ndef test_b():\n    marca('teste-b')\n"
    ).encode())
    a["hardtests/test_hard.py"] = ("100644", (
        G.marca_func + "\n\ndef test_unbuf():\n    marca('hard-unbuf')\n\n\ndef test_form4():\n"
        "    marca('hard-form4')\n").encode())
    a["scripts/install.sh"] = ("100755", b"#!/bin/bash\necho instalar\n")
    a["docs/a.md"] = ("100644", b"linha 1\nlinha 2\n")
    a["docs/velho.md"] = ("100644", b"velho\n")
    for caminho in GATES:
        nome = "gate-" + os.path.basename(caminho)
        if caminho.endswith(".sh"):
            a[caminho] = ("100644", sh_marca(nome))
        else:
            a[caminho] = ("100644", py_marca(nome))
    a[".claude/sentinel-signers.txt"] = ("100644", ("# allowlist do harness\n%s\n" % G.fpr1).encode())
    a[".claude/plans/PLAN-900/pk1/hard-unbuf.sh"] = ("100644", (
        "#!/bin/bash\nexport PYTHONUNBUFFERED=1\n"
        "python3 -m pytest -p no:cacheprovider -q hardtests/test_hard.py::test_unbuf\n").encode())
    return a


def monta_base() -> None:
    src = os.path.join(G.h, "base-src")
    os.makedirs(src)
    _rc, tar, _e = sh([G.git_real, "-C", REPO, "archive", "HEAD", ".claude/hooks"])
    with tarfile.open(fileobj=io.BytesIO(tar)) as tf:
        tf.extractall(src)
    for caminho in (ENTRADA, NUCLEO, BLOCO):
        grava(os.path.join(src, caminho), le(os.path.join(REPO, caminho)), 0o644)
    for caminho, (modo, dados) in arquivos_base().items():
        grava(os.path.join(src, caminho), dados, 0o755 if modo == "100755" else 0o644)
    G.base_git = os.path.join(G.h, "base.git")
    git(["init", "-q", "--bare", G.base_git])
    idx = os.path.join(G.h, "base.idx")
    env = env_h({"GIT_INDEX_FILE": idx})
    git(["--git-dir=" + G.base_git, "--work-tree=" + src, "add", "-A"], env=env)
    G.b0_tree = git(["--git-dir=" + G.base_git, "write-tree"], env=env).decode().strip()
    G.b0 = gitb(G.base_git, ["commit-tree", G.b0_tree, "-m", "base da fixture"]).decode().strip()
    os.remove(idx)
    shutil.rmtree(src)


class Arvore:
    """Árvore derivada de outra por mudanças (índice temporário)."""

    def __init__(self, base_tree: str) -> None:
        self.base = base_tree
        self.mudancas: Dict[str, Optional[Tuple[str, bytes]]] = {}

    def aplica(self, mudancas: Dict[str, Optional[Tuple[str, bytes]]]) -> str:
        idx = os.path.join(G.h, "t.idx")
        env = env_h({"GIT_INDEX_FILE": idx})
        gitb(G.base_git, ["read-tree", self.base], env=env)
        linhas = []
        for caminho, valor in mudancas.items():
            if valor is None:
                linhas.append("0 %s\t%s" % ("0" * 40, caminho))
                continue
            modo, dados = valor
            if modo == "120000":
                sha = gitb(G.base_git, ["hash-object", "-w", "--stdin"], entrada=dados).decode().strip()
            else:
                sha = gitb(G.base_git, ["hash-object", "-w", "--no-filters", "--stdin"],
                           entrada=dados).decode().strip()
            linhas.append("%s %s\t%s" % (modo, sha, caminho))
        if linhas:
            gitb(G.base_git, ["update-index", "--add", "--index-info"],
                 entrada=("\n".join(linhas) + "\n").encode(), env=env)
        arvore = gitb(G.base_git, ["write-tree"], env=env).decode().strip()
        os.remove(idx)
        return arvore


# ---------------------------------------------------------------------------
# pacote sintético
# ---------------------------------------------------------------------------

class Pacote:
    def __init__(self) -> None:
        self.pre: Dict[str, Optional[Tuple[str, bytes]]] = {}
        self.pos: Dict[str, Optional[Tuple[str, bytes]]] = {
            "scripts/install.sh": ("100755", b"#!/bin/bash\necho instalar\necho fim\n"),
            "docs/a.md": ("100644", b"linha 1\nlinha dois\n"),
            "docs/novo.md": ("100644", b"novo\n"),
            "docs/velho.md": None,
        }
        self.hard: List[List[str]] = [
            ["bash", "-n", "scripts/install.sh"],
            ["python3", "tools/hard_ok.py"],
            ["bash", ".claude/plans/PLAN-900/pk1/hard-unbuf.sh"],
            ["python3", "-m", "pytest", "-p", "no:cacheprovider", "-q", "-rfE", "--tb=no",
             "hardtests/test_hard.py::test_form4"],
        ]
        self.canonical: List[str] = ["scripts/install.sh"]
        self.rail_p = RAIL
        self.dados_txt: Optional[bytes] = None
        self.dados_p = DADOS
        self.patch_fn: Optional[Callable[[bytes], bytes]] = None
        self.sent_fn: Optional[Callable[[str], str]] = None
        self.rail_fn: Optional[Callable[[str], str]] = None
        self.sent_extra = ""
        self.extra_a: Dict[str, Optional[Tuple[str, bytes]]] = {}
        self.escopo: Optional[List[str]] = None
        self.sem_dados = False

    def dados(self) -> bytes:
        if self.dados_txt is not None:
            return self.dados_txt
        linhas = ["format\tsign-min-1", "rail\t" + self.rail_p]
        linhas += ["canonical\t" + c for c in self.canonical]
        linhas += ["hard\t" + "\t".join(h) for h in self.hard]
        return ("\n".join(linhas) + "\n").encode()


def caminhos_patch(patch: bytes) -> List[str]:
    achados = []
    for linha in patch.decode("utf-8", "replace").split("\n"):
        if linha.startswith("diff --git a/") and " b/" in linha:
            achados.append(linha[len("diff --git a/"):].split(" b/", 1)[0])
    return achados


def bloco_txt() -> str:
    return le(os.path.join(REPO, BLOCO)).decode()


def texto_sentinel(escopo: List[str], extra: str = "", dados_p: str = DADOS) -> str:
    return (
        "# pk1-approved — sentinel sintético do harness sign-min\n\n"
        "Plan: PLAN-900\nWave: pk1\n"
        "Dados: " + dados_p + "\n"
        "Molde: .claude/plans/PLAN-194/sign-min/OWNER-SIGN.sh\n"
        "Patch-sha256: TO-FILL-BY-SIGN\nRail-Record-sha256: TO-FILL-BY-SIGN\n"
        "Anchor-SHA: TO-FILL-BY-SIGN\nData: TO-FILL-BY-SIGN\n\n"
        "## Ratificação (Owner)\n\n- sintético.\n" + extra + "\n"
        "<!-- bloco-comum sign-min v1 -->\n" + bloco_txt() + "<!-- fim do bloco-comum -->\n\n"
        "## Controle vermelho (registro)\n\n- sintético.\n\n"
        "## Scope\n\n" + "".join("- `%s`\n" % c for c in escopo)
    )


def texto_rail(patch: bytes, sent: bytes, dados: bytes, veredito: str = "APPROVE") -> str:
    return (
        "# registro sintético do rail\n\n"
        "Rail-Subject-sha256: %s\nRail-Sentinel-sha256: %s\nRail-Data-sha256: %s\nRail-Verdict: %s\n"
        % (sha256b(patch), sha256b(sent), sha256b(dados), veredito)
    )


class Construido:
    def __init__(self) -> None:
        self.a = ""
        self.patch = b""
        self.sent = b""
        self.rail = b""
        self.dados = b""
        self.origin = ""
        self.caminhos: List[str] = []
        self.blocos: List[Tuple[str, str, str, str, str, str]] = []


def constroi(pk: Pacote, sobrepor: Optional[Dict[str, Optional[Tuple[str, bytes]]]] = None,
             dir_caso: str = "") -> Construido:
    """Origin do caso: B0 + pacote (+ sobreposições do molde para mutantes)."""
    c = Construido()
    t_pre = Arvore(G.b0_tree).aplica(dict(pk.pre))
    pos_completo = dict(pk.pre)
    pos_completo.update(pk.pos)
    t_pos = Arvore(G.b0_tree).aplica(pos_completo)
    patch = gitb(G.base_git, ["diff-tree", "-p", "--full-index", "--no-renames", "--no-color", t_pre, t_pos])
    if pk.patch_fn is not None:
        patch = pk.patch_fn(patch)
    c.patch = patch
    c.caminhos = caminhos_patch(patch)
    escopo = pk.escopo if pk.escopo is not None else c.caminhos
    sent_txt = texto_sentinel(escopo, pk.sent_extra, pk.dados_p)
    if pk.sent_fn is not None:
        sent_txt = pk.sent_fn(sent_txt)
    c.sent = sent_txt.encode()
    c.dados = pk.dados()
    rail_txt = texto_rail(c.patch, c.sent, c.dados)
    if pk.rail_fn is not None:
        rail_txt = pk.rail_fn(rail_txt)
    c.rail = rail_txt.encode()
    mats: Dict[str, Optional[Tuple[str, bytes]]] = dict(pk.pre)
    mats[PATCH] = ("100644", c.patch)
    mats[SENT] = ("100644", c.sent)
    if pk.rail_p == RAIL:
        mats[RAIL] = ("100644", c.rail)
    if not pk.sem_dados:
        mats[pk.dados_p] = ("100644", c.dados)
    mats.update(pk.extra_a)
    if sobrepor:
        mats.update(sobrepor)
    t_a = Arvore(G.b0_tree).aplica(mats)
    c.a = gitb(G.base_git, ["commit-tree", t_a, "-p", G.b0, "-m", "pacote sintético"]).decode().strip()
    c.origin = os.path.join(dir_caso, "origin.git")
    git(["init", "-q", "--bare", c.origin])
    grava(os.path.join(c.origin, "objects", "info", "alternates"),
          (os.path.join(G.base_git, "objects") + "\n").encode())
    gitb(c.origin, ["update-ref", "refs/heads/main", c.a])
    gitb(c.origin, ["symbolic-ref", "HEAD", "refs/heads/main"])
    return c


def clona(origin: str, destino: str, home: str) -> None:
    """Os MESMOS comandos do roteiro (clone sem template, config local, checkout)."""
    env = env_h({"HOME": home})
    git(["clone", "-q", "--template=", "--no-checkout", "--single-branch", origin, destino], env=env)
    for chave, valor in (("core.hooksPath", "/dev/null"), ("core.fsmonitor", "false"),
                         ("core.untrackedCache", "false"), ("user.name", NOME), ("user.email", EMAIL)):
        git(["-C", destino, "config", chave, valor], env=env)
    git(["-C", destino, "checkout", "-q", "main"], env=env)


# ---------------------------------------------------------------------------
# fachadas
# ---------------------------------------------------------------------------

FACHADA_GIT = r'''#!/bin/bash
REAL=@REAL@
MODO=@MODO@
sub=''
pula=0
for a in "$@"; do
  if [ "$pula" = 1 ]; then pula=0; continue; fi
  case "$a" in -c) pula=1 ;; -*) ;; *) sub="$a"; break ;; esac
done
case "$MODO" in
  f7) printf '%s\n' 'Run git config --global user.email you@example.com' 'remove the file manually' >&2
      if [ "$sub" = apply ]; then case " $* " in *" --index "*) exit 128 ;; esac; fi ;;
  k6) if [ "$sub" = apply ]; then case " $* " in *" --check "*) exit 1 ;; esac; fi ;;
  f9) if [ "$sub" = commit ]; then exit 128; fi ;;
  hashobj) if [ "$sub" = hash-object ]; then cat > /dev/null; printf '%s\n' 0000000000000000000000000000000000000000; exit 0; fi ;;
  fcommit) if [ "$sub" = commit ]; then "$REAL" "$@"; r=$?; "$REAL" update-ref refs/heads/main HEAD~1; exit $r; fi ;;
  k4) if [ "$sub" = commit ]; then "$REAL" "$@"; kill -9 $PPID; kill -9 $$; fi ;;
esac
exec "$REAL" "$@"
'''

FACHADA_GPG = r'''#!/bin/bash
REAL=@REAL@
LOG=@LOG@
MODO=@MODO@
s=outro
case " $* " in *" --detach-sign "*) s=--detach-sign ;; *" --verify "*) s=--verify ;; *" --list-secret-keys "*) s=--list-secret-keys ;; esac
printf 'GPG %s\n' "$s" >> "$LOG"
if [ "$s" = --detach-sign ]; then
  case "$MODO" in
    f6) exit 2 ;;
    fver) args=(); prox=0
          for a in "$@"; do
            if [ "$prox" = 1 ]; then args+=(@KEY2@); prox=0; continue; fi
            [ "$a" = --local-user ] && prox=1
            args+=("$a")
          done
          exec "$REAL" "${args[@]}" ;;
  esac
fi
exec "$REAL" "$@"
'''


def q(texto: str) -> str:
    return "'" + texto.replace("'", "'\\''") + "'"


def monta_fachadas(dir_caso: str, modo_git: str, modo_gpg: str, com_gpg: bool = True) -> str:
    d = os.path.join(dir_caso, "fachada")
    os.makedirs(d)
    grava(os.path.join(d, "git"), FACHADA_GIT.replace("@REAL@", q(G.git_real)).replace(
        "@MODO@", q(modo_git)).encode(), 0o755)
    if com_gpg:
        grava(os.path.join(d, "gpg"), FACHADA_GPG.replace("@REAL@", q(G.gpg_real)).replace(
            "@LOG@", q(os.path.join(G.atual, "ordem.log"))).replace("@MODO@", q(modo_gpg)).replace(
            "@KEY2@", q(G.fpr2)).encode(), 0o755)
    return d


# ---------------------------------------------------------------------------
# casos
# ---------------------------------------------------------------------------

class Caso:
    def __init__(self, nome: str, tipo: str, real: bool = False) -> None:
        self.nome = nome
        self.tipo = tipo
        self.real = real
        self.pk = Pacote()
        self.marcador = ""
        self.esperado: Optional[Tuple[str, Dict[str, object]]] = None
        self.esperado_fn: Optional[Callable[["Exec"], Tuple[str, Dict[str, object]]]] = None
        self.plantio: Optional[Callable[["Exec"], None]] = None
        self.env_fn: Optional[Callable[["Exec", Dict[str, str]], None]] = None
        self.argv_fn: Optional[Callable[["Exec", List[str]], List[str]]] = None
        self.cwd_rel = ""
        self.modo_git = "normal"
        self.modo_gpg = "normal"
        self.com_gpg = True
        self.pty = real
        self.fsize = 0
        self.confere: Optional[Callable[["Exec"], None]] = None
        self.ao_ler: Optional[Callable[["Exec", str], None]] = None
        self.timeout = 300.0
        self.extra_dirs: List[str] = []


class Exec:
    def __init__(self, caso: Caso, dir_caso: str, c: Construido, clone: str, home: str,
                 fachada: str, plantio: str) -> None:
        self.caso = caso
        self.dir = dir_caso
        self.c = c
        self.clone = clone
        self.home = home
        self.fachada = fachada
        self.plantio = plantio
        self.rc: Optional[int] = None
        self.out: List[str] = []
        self.err = b""
        self.proc: Optional[subprocess.Popen] = None
        self.mestre: Optional[int] = None
        self.notas: List[str] = []
        self.sha_nucleo = sha256f(os.path.join(clone, NUCLEO)) if os.path.exists(
            os.path.join(clone, NUCLEO)) else ""
        self.t = ""
        self.extra: Dict[str, object] = {}

    def gitc(self, args: List[str], ok: bool = True) -> bytes:
        return git(["-C", self.clone] + args, ok=ok, env=env_h({"HOME": self.home}))

    def ordem(self) -> List[str]:
        p = os.path.join(G.atual, "ordem.log")
        return le(p).decode().splitlines() if os.path.exists(p) else []


def env_sign(ex: Exec) -> Dict[str, str]:
    env = {
        "PATH": ex.plantio + ":" + ex.fachada + ":" + SIS_PATH,
        "HOME": ex.home, "USER": os.environ.get("USER", "fixture"),
        "LOGNAME": os.environ.get("LOGNAME", os.environ.get("USER", "fixture")),
        "SHELL": "/bin/bash", "TERM": "xterm-256color", "LANG": "en_US.UTF-8", "PAGER": "cat",
        "GNUPGHOME": G.gnupg, "PYTHONUSERBASE": G.pyub,
    }
    return env


def roda(ex: Exec) -> None:
    caso = ex.caso
    env = env_sign(ex)
    escravo = None
    if caso.pty:
        ex.mestre, escravo = pty.openpty()
        env["GPG_TTY"] = os.ttyname(escravo)
    if caso.env_fn is not None:
        caso.env_fn(ex, env)
    argv = ["/bin/bash", ENTRADA, "--nucleo-sha256=" + ex.sha_nucleo]
    if not caso.real:
        argv.append("--dry-run")
    argv.append(caso.pk.dados_p)
    if caso.argv_fn is not None:
        argv = caso.argv_fn(ex, argv)
    cwd = os.path.join(ex.clone, caso.cwd_rel) if caso.cwd_rel else ex.clone
    fsize = caso.fsize
    usa_pty = caso.pty

    def preexec() -> None:
        os.setsid()
        if usa_pty:
            fcntl.ioctl(0, termios.TIOCSCTTY, 0)
        if fsize:
            resource.setrlimit(resource.RLIMIT_FSIZE, (fsize, fsize))

    proc = subprocess.Popen(
        ["/usr/bin/env", "-i"] + ["%s=%s" % kv for kv in env.items()] + argv,
        stdin=escravo if escravo is not None else subprocess.DEVNULL,
        stdout=subprocess.PIPE, stderr=subprocess.PIPE, cwd=cwd, preexec_fn=preexec)
    ex.proc = proc
    if escravo is not None:
        os.close(escravo)
    erros: List[bytes] = []

    def le_err() -> None:
        erros.append(proc.stderr.read())  # type: ignore[union-attr]

    te = threading.Thread(target=le_err)
    te.start()
    if ex.mestre is not None:
        mestre = ex.mestre

        def drena() -> None:
            try:
                while os.read(mestre, 4096):
                    pass
            except OSError:
                pass
        threading.Thread(target=drena, daemon=True).start()
    limite = time.monotonic() + caso.timeout
    estouro = []

    def vigia() -> None:
        while proc.poll() is None:
            if time.monotonic() > limite:
                estouro.append(1)
                try:
                    os.killpg(proc.pid, signal.SIGKILL)
                except OSError:
                    pass
                return
            time.sleep(0.2)
    threading.Thread(target=vigia, daemon=True).start()
    try:
        for bruta in proc.stdout:  # type: ignore[union-attr]
            linha = bruta.decode("utf-8", "replace").rstrip("\n")
            ex.out.append(linha)
            if linha.startswith("SIGN-FATO: logs em "):
                ex.t = linha[len("SIGN-FATO: logs em "):]
            if caso.ao_ler is not None:
                caso.ao_ler(ex, linha)
            if proc.stdout.closed:  # type: ignore[union-attr]
                break
    except ValueError:
        pass
    proc.wait()
    te.join()
    ex.rc = proc.returncode
    ex.err = b"".join(erros)
    if ex.mestre is not None:
        try:
            os.close(ex.mestre)
        except OSError:
            pass
    afirma(not estouro, "o SIGN passou do tempo limite do caso (%ss)" % caso.timeout)


def retrato(ex: Exec) -> Dict[str, object]:
    clone = ex.clone
    gitdir = os.path.join(clone, ".git")
    if os.path.isfile(gitdir) and not os.path.islink(gitdir):
        gitdir = le(gitdir).decode().split("gitdir: ", 1)[1].strip()
    gitdir = os.path.realpath(gitdir)
    nobj = sum(len(f) for _d, _s, f in os.walk(os.path.join(gitdir, "objects")))
    refs = git(["--git-dir=" + gitdir, "for-each-ref"], env=env_h({"HOME": ex.home}))
    return {
        "index": sha256f(os.path.join(gitdir, "index")) if os.path.exists(os.path.join(gitdir, "index")) else "",
        "fetch": os.path.exists(os.path.join(gitdir, "FETCH_HEAD")),
        "refs": refs, "nobj": nobj, "tmp": set(glob.glob("/tmp/sign-min.*")), "gitdir": gitdir,
    }


def novos_desde(raizes: List[str], marca: float) -> List[str]:
    achados = []
    for raiz in raizes:
        for base, dirs, arquivos in os.walk(raiz):
            for nome in arquivos + dirs:
                p = os.path.join(base, nome)
                try:
                    st = os.lstat(p)
                except OSError:
                    continue
                if st.st_mtime > marca or st.st_ctime > marca:
                    achados.append(p)
    return achados


def contagem_commits(ex: Exec) -> int:
    out = ex.gitc(["cat-file", "--batch-all-objects", "--batch-check"])
    return sum(1 for ln in out.decode().splitlines() if ln.split(" ")[1:2] == ["commit"])


def prepara(caso: Caso, sobrepor: Optional[Dict[str, Optional[Tuple[str, bytes]]]] = None) -> Exec:
    if os.path.exists(G.atual):
        shutil.rmtree(G.atual)
    os.makedirs(G.atual)
    dir_caso = tempfile.mkdtemp(prefix="c.", dir=G.h)
    c = constroi(caso.pk, sobrepor, dir_caso)
    clone = os.path.join(dir_caso, "clone")
    home = os.path.join(dir_caso, "home")
    os.makedirs(home)
    plantio = os.path.join(dir_caso, "plantio")
    os.makedirs(plantio)
    clona(c.origin, clone, home)
    fachada = monta_fachadas(dir_caso, caso.modo_git, caso.modo_gpg, caso.com_gpg)
    ex = Exec(caso, dir_caso, c, clone, home, fachada, plantio)
    if caso.plantio is not None:
        caso.plantio(ex)
    return ex


def mata_restos() -> None:
    """Encerra os grupos de processos que a fixture registrou (só esses)."""
    p = os.path.join(G.atual, "ordem.log")
    if not os.path.exists(p):
        return
    for linha in le(p).decode().splitlines():
        partes = linha.split(" ")
        if len(partes) == 3 and partes[1].isdigit() and partes[2].isdigit():
            for alvo in (int(partes[2]),):
                try:
                    os.killpg(alvo, signal.SIGKILL)
                except OSError:
                    pass


def limpa_caso(ex: Exec) -> None:
    mata_restos()
    if not G.manter and ex.dir.startswith(G.h + "/c."):
        shutil.rmtree(ex.dir, ignore_errors=True)


def confere_recusa(ex: Exec, antes: Dict[str, object], marca: float, chave: str,
                   valores: Dict[str, object]) -> None:
    depois = retrato(ex)
    raizes = [ex.clone] + ([antes["gitdir"]] if not str(antes["gitdir"]).startswith(ex.clone) else [])  # type: ignore[list-item]
    novos = novos_desde(raizes, marca)  # type: ignore[arg-type]
    afirma(not novos, "a recusa escreveu no clone: %s" % novos[:3])
    for k in ("index", "fetch", "refs", "nobj", "tmp"):
        afirma(antes[k] == depois[k], "retrato mudou em %s" % k)
    esperado = [msg(chave, **valores), msg("FIXA")]
    afirma(ex.rc == 1, "rc %s (esperado 1)" % ex.rc)
    afirma(ex.out == esperado, "saída %r (esperado %r)" % (ex.out, esperado))
    afirma(ex.err == b"", "stderr não vazio: %r" % ex.err[:200])


def executa_recusa(caso: Caso, sobrepor: Optional[Dict[str, Optional[Tuple[str, bytes]]]] = None) -> Exec:
    ex = prepara(caso, sobrepor)
    try:
        time.sleep(0.05)
        antes = retrato(ex)
        marca = time.time()
        time.sleep(0.05)
        roda(ex)
        if caso.esperado_fn is not None:
            chave, valores = caso.esperado_fn(ex)
        else:
            assert caso.esperado is not None
            chave, valores = caso.esperado
        confere_recusa(ex, antes, marca, chave, valores)
        if caso.confere is not None:
            caso.confere(ex)
    finally:
        if sobrepor is None:
            G.saidas.append((caso.nome, "\n".join(ex.out) + ("\n" + ex.err.decode("utf-8", "replace") if ex.err else "")))
        limpa_caso(ex)
    return ex


def mutante_texto(texto: str, marcador: str) -> str:
    linhas = texto.split("\n")
    alvo = [i for i, ln in enumerate(linhas) if ln.rstrip().endswith("# " + marcador)]
    afirma(len(alvo) == 1 and texto.count("# " + marcador + "\n") == 1,
           "marcador %s não é único" % marcador)
    i = alvo[0]
    recuo = linhas[i][:len(linhas[i]) - len(linhas[i].lstrip())]
    if marcador.startswith(("P0:", "B:")):
        linhas[i] = recuo + "pass  # " + marcador
    else:
        linhas[i] = recuo + ":  # " + marcador
    novo = "\n".join(linhas)
    afirma(novo != texto, "mutante igual ao original")
    return novo


# mutante cujo vermelho só conta com este texto na falha (o caso confere outras coisas antes)
MOTIVO_MUTANTE = {"B:tmp": "TMPDIR"}


def roda_mutante(caso: Caso, marcador: str, checa: Callable[[Caso, Optional[Dict[str, Optional[Tuple[str, bytes]]]]], None]) -> None:
    caminho = NUCLEO if marcador.startswith(("P0:", "B:")) else ENTRADA
    original = le(os.path.join(REPO, caminho)).decode()
    novo = mutante_texto(original, marcador)
    sobrepor = {caminho: ("100644", novo.encode())}
    try:
        checa(caso, sobrepor)
    except Falha as exc:
        motivo = MOTIVO_MUTANTE.get(marcador)
        afirma(motivo is None or motivo in str(exc),
               "o mutante %s reprovou o caso %s por outro motivo: %s" % (marcador, caso.nome, exc))
        G.mutantes_vermelhos.append(marcador)
        return
    raise Falha("o mutante %s passou no caso %s (devia reprovar)" % (marcador, caso.nome))


# ---------------------------------------------------------------------------
# definições dos casos
# ---------------------------------------------------------------------------

CASOS: List[Caso] = []
MUTANTE_DE: Dict[str, str] = {}


def caso(nome: str, tipo: str, real: bool = False) -> Caso:
    c = Caso(nome, tipo, real)
    CASOS.append(c)
    return c


def plant_git(args: List[str]) -> Callable[[Exec], None]:
    def f(ex: Exec) -> None:
        ex.gitc(args)
    return f


def def_e() -> None:
    c = caso("E-src", "E")
    c.marcador = "E:src"
    c.cwd_rel = MOLDE
    c.argv_fn = lambda ex, a: [a[0], "OWNER-SIGN.sh"] + a[2:]
    c.esperado = ("E-SRC", {})
    c = caso("E-path-relativo", "E")
    c.marcador = "E:path"
    c.env_fn = lambda ex, env: env.__setitem__("PATH", ".:" + env["PATH"])
    c.esperado = ("E-PATH", {})
    c = caso("E-path-vazio", "E")
    c.env_fn = lambda ex, env: env.__setitem__("PATH", env["PATH"].replace(":/usr/bin:", "::/usr/bin:"))
    c.esperado = ("E-PATH", {})
    c = caso("E-py", "E")
    c.marcador = "E:py"
    c.env_fn = lambda ex, env: env.__setitem__("PATH", ex.fachada + ":/bin")
    c.esperado = ("E-PY", {})
    c = caso("E-args", "E")
    c.marcador = "E:args"
    c.argv_fn = lambda ex, a: [a[0], a[1]] + a[3:]
    c.esperado = ("E-ARGS", {})
    c = caso("E-args-63", "E")
    c.argv_fn = lambda ex, a: [a[0], a[1], "--nucleo-sha256=" + ex.sha_nucleo[:63]] + a[3:]
    c.esperado = ("E-ARGS", {})
    c = caso("E-sha", "E")
    c.marcador = "E:sha"
    c.argv_fn = lambda ex, a: [a[0], a[1], "--nucleo-sha256=" + "0" * 64] + a[3:]
    c.esperado = ("E-SHA", {})
    c = caso("E-sha-ausente", "E")

    def apaga_nucleo(ex: Exec) -> None:
        os.remove(os.path.join(ex.clone, NUCLEO))
        afirma(not os.path.exists(os.path.join(ex.clone, NUCLEO)), "plantio sem efeito")
    c.plantio = apaga_nucleo
    c.argv_fn = lambda ex, a: [a[0], a[1], "--nucleo-sha256=" + sha256f(os.path.join(REPO, NUCLEO))] + a[3:]
    c.esperado = ("E-SHA", {})


def env_mais(**extra: str) -> Callable[[Exec, Dict[str, str]], None]:
    def f(ex: Exec, env: Dict[str, str]) -> None:
        env.update(extra)
    return f


def def_r_p0a() -> None:
    c = caso("R-args", "R")
    c.marcador = "P0:args"
    c.argv_fn = lambda ex, a: a[:-1] + ["x/sign.tsv"]
    c.esperado = ("P-ARGS", {"n": 2})
    for nome, extra, n, marc in (
            ("R-env-func", {"BASH_FUNC_f%%": "() { :; }"}, 1, "P0:env"),
            ("R-env-compgen", {"BASH_FUNC_compgen%%": "() { :; }", "GIT_DIR": "/tmp/x"}, 2, ""),
            ("R-env-gitdir-vazio", {"GIT_DIR": ""}, 1, ""),
            ("R-env-ceo-kernel-override-vazio", {"CEO_KERNEL_OVERRIDE": ""}, 1, ""),
            ("R-env-tmpdir", {"TMPDIR": "/tmp"}, 1, "")):
        c = caso(nome, "R")
        c.marcador = marc
        c.env_fn = env_mais(**extra)
        c.esperado = ("P-ENV", {"n": n})
    c = caso("R-cwd", "R")
    c.marcador = "P0:root"
    c.cwd_rel = "docs"
    c.argv_fn = lambda ex, a: [a[0], "../" + ENTRADA] + a[2:]
    c.esperado = ("P-CWD", {})
    c = caso("R-gitdir", "R")

    def gitfile(ex: Exec) -> None:
        real = os.path.join(ex.dir, "gitdir-real")
        os.rename(os.path.join(ex.clone, ".git"), real)
        grava(os.path.join(ex.clone, ".git"), ("gitdir: " + real + "\n").encode())
        out = ex.gitc(["rev-parse", "--git-dir"]).decode().strip()
        afirma(out == real, "plantio sem efeito (git-dir %s)" % out)
    c.plantio = gitfile
    c.esperado = ("P-GITDIR", {})
    c = caso("R-gitdir-symlink", "R")

    def gitlink(ex: Exec) -> None:
        real = os.path.join(ex.dir, "gitdir-real")
        os.rename(os.path.join(ex.clone, ".git"), real)
        os.symlink(real, os.path.join(ex.clone, ".git"))
        afirma(os.path.islink(os.path.join(ex.clone, ".git")), "plantio sem efeito")
    c.plantio = gitlink
    c.esperado = ("P-GITDIR", {})
    c = caso("R-tty", "R", real=True)
    c.marcador = "P0:tty"
    c.pty = False
    c.env_fn = env_mais(GPG_TTY="/dev/ttys000")
    c.esperado = ("P-TTY", {})
    c = caso("R-gpgtty", "R", real=True)
    c.env_fn = env_mais(GPG_TTY="/dev/ttys999")
    c.esperado = ("P-GPGTTY", {})
    c = caso("R-tool", "R")
    c.marcador = "P0:tools"
    c.com_gpg = False
    c.esperado = ("P-TOOL", {"nome": "gpg"})


def def_r_cfg() -> None:
    c = caso("R-hooks-ausente", "R")
    c.marcador = "P0:hooks"

    def sem_hooks(ex: Exec) -> None:
        ex.gitc(["config", "--unset", "core.hooksPath"])
        afirma(ex.gitc(["config", "--get-all", "core.hooksPath"], ok=False) == b"", "plantio sem efeito")
    c.plantio = sem_hooks
    c.esperado = ("P-HOOKS", {"r": 1, "n": 0})
    c = caso("R-hooks-dois-valores", "R")

    def dois(ex: Exec) -> None:
        ex.gitc(["config", "--add", "core.hooksPath", "/dev/null"])
        afirma(ex.gitc(["config", "--get-all", "core.hooksPath"]).count(b"\n") == 2, "plantio sem efeito")
    c.plantio = dois
    c.esperado = ("P-HOOKS", {"r": 0, "n": 2})
    c = caso("R-hooks-por-include", "R")

    def inc(ex: Exec) -> None:
        arq = os.path.join(ex.dir, "inc.cfg")
        grava(arq, b"[core]\n\thooksPath = /dev/null\n")
        ex.gitc(["config", "--unset", "core.hooksPath"])
        ex.gitc(["config", "include.path", arq])
        out = ex.gitc(["config", "--show-origin", "--get-all", "core.hooksPath"])
        afirma(out.startswith(b"file:" + arq.encode()), "plantio sem efeito: %r" % out)
    c.plantio = inc
    c.esperado = ("P-HOOKS", {"r": 0, "n": 1})
    c = caso("R-fsm-sem-valor", "R")
    c.marcador = "P0:fsm"

    def sem_valor(ex: Exec) -> None:
        p = os.path.join(ex.clone, ".git", "config")
        txt = le(p).decode()
        afirma("\tfsmonitor = false\n" in txt, "config inesperada")
        grava(p, txt.replace("\tfsmonitor = false\n", "\tfsmonitor\n").encode())
        out = ex.gitc(["config", "--show-origin", "--type=bool", "--get-all", "core.fsmonitor"])
        afirma(out == b"file:.git/config\ttrue\n", "plantio sem efeito: %r" % out)
    c.plantio = sem_valor
    c.esperado = ("P-FSM", {"r": 0, "n": 1})
    c = caso("R-fsm-true", "R")
    c.plantio = plant_git(["config", "core.fsmonitor", "true"])
    c.esperado = ("P-FSM", {"r": 0, "n": 1})
    c = caso("R-fsm-ausente", "R")
    c.plantio = plant_git(["config", "--unset", "core.fsmonitor"])
    c.esperado = ("P-FSM", {"r": 1, "n": 0})
    c = caso("R-ident", "R")
    c.marcador = "P0:ident"

    def sem_email(ex: Exec) -> None:
        ex.gitc(["config", "--unset", "user.email"])
        rc, _o, _e = sh([G.git_real, "-C", ex.clone, "-c", "user.useConfigOnly=true", "var", "GIT_AUTHOR_IDENT"],
                        env={"PATH": SIS_PATH, "HOME": ex.home}, ok=False)
        afirma(rc != 0, "plantio sem efeito")
    c.plantio = sem_email

    def sem_run(ex: Exec) -> None:
        afirma("Run" not in "\n".join(ex.out) and b"Run" not in ex.err, "«Run» na saída")
    c.confere = sem_run
    c.esperado = ("P-IDENT", {"var": "GIT_AUTHOR_IDENT", "r": 128})
    for nome, rel, marc in (("R-lock-index", ".git/index.lock", "P0:lock"),
                            ("R-lock-ref", ".git/refs/heads/main.lock", "")):
        c = caso(nome, "R")
        c.marcador = marc

        def trava(ex: Exec, rel: str = rel) -> None:
            grava(os.path.join(ex.clone, rel), b"")
            afirma(os.path.exists(os.path.join(ex.clone, rel)), "plantio sem efeito")
        c.plantio = trava
        c.esperado = ("P-LOCK", {"n": 1, "h": ident(rel)})
    c = caso("R-head-destacado", "R")
    c.marcador = "P0:head"
    c.plantio = plant_git(["checkout", "-q", "--detach"])
    c.esperado = ("P-HEAD", {})
    c = caso("R-origin-difere", "R")
    c.plantio = lambda ex: ex.gitc(["update-ref", "refs/remotes/origin/main", G.b0]) and None
    c.esperado_fn = lambda ex: ("P-ORIGIN", {"a": ex.c.a, "x": G.b0})
    c = caso("R-head-sem-commit", "R")

    def orfao(ex: Exec) -> None:
        ex.gitc(["update-ref", "-d", "refs/heads/main"])
        afirma(ex.gitc(["symbolic-ref", "HEAD"]) == b"refs/heads/main\n", "HEAD deixou de ser simbólico")
        afirma(ex.gitc(["rev-parse", "--verify", "--quiet", "HEAD"], ok=False) == b"", "plantio sem efeito")
    c.plantio = orfao
    c.esperado = ("P-RC", {"rotulo": "git rev-parse", "r": 1})
    c = caso("R-filter", "R")
    c.marcador = "P0:filter"

    def filtro(ex: Exec) -> None:
        grava(os.path.join(ex.clone, ".git", "info", "attributes"), b"docs/a.md filter=nada\n")
        out = ex.gitc(["check-attr", "filter", "--", "docs/a.md"])
        afirma(out == b"docs/a.md: filter: nada\n", "plantio sem efeito")
    c.plantio = filtro
    c.esperado = ("P-FILTER", {"n": 1, "h": ident("docs/a.md")})


def status_vazio(ex: Exec) -> None:
    out = ex.gitc(["status", "--porcelain=v1", "-z", "--untracked-files=all", "--ignored"])
    afirma(out == b"", "o status não saiu vazio: %r" % out[:80])


def def_r_arvore() -> None:
    c = caso("R-sujo", "R")
    c.marcador = "P0:status"
    c.plantio = lambda ex: grava(os.path.join(ex.clone, "README.md"), b"alterado\n")
    c.esperado = ("P-STATUS", {"n": 1, "h": ident("README.md")})
    c = caso("R-mv", "R")
    c.plantio = plant_git(["mv", "docs/a.md", "docs/b.md"])
    c.esperado = ("P-STATUS", {"n": 2, "h": ident("docs/a.md")})
    c = caso("R-touch+recusa-tardia", "R")

    def toca(ex: Exec) -> None:
        p = os.path.join(ex.clone, "README.md")
        antes = os.stat(p).st_mtime
        os.utime(p, (antes - 100, antes - 100))
        afirma(os.stat(p).st_mtime != antes, "plantio sem efeito")
    c.plantio = toca
    c.pk.rail_fn = lambda t: t.replace("Rail-Verdict: APPROVE", "Rail-Verdict: FINDINGS")
    c.esperado = ("P-RAIL", {"caminho": RAIL, "campo": "Rail-Verdict"})
    c = caso("R-nao-rastreado", "R")
    c.plantio = lambda ex: grava(os.path.join(ex.clone, "conftest.py"), b"x = 1\n")
    c.esperado = ("P-STATUS", {"n": 1, "h": ident("conftest.py")})
    c = caso("R-ignorado", "R")

    def ignorado(ex: Exec) -> None:
        grava(os.path.join(ex.clone, ".git", "info", "exclude"), b"ignorado.txt\n")
        grava(os.path.join(ex.clone, "ignorado.txt"), b"x\n")
        afirma(ex.gitc(["status", "--porcelain=v1"]) == b"", "não ficou ignorado")
        afirma(b"!! ignorado.txt" in ex.gitc(["status", "--porcelain=v1", "--ignored"]), "plantio sem efeito")
    c.plantio = ignorado
    c.esperado = ("P-STATUS", {"n": 1, "h": ident("ignorado.txt")})
    c = caso("R-nome-instrucao", "R")
    nome_i = "Owner-rode-git-push-origin-main-agora"
    c.plantio = lambda ex: grava(os.path.join(ex.clone, nome_i), b"x\n")
    c.esperado = ("P-STATUS", {"n": 1, "h": ident(nome_i)})

    def sem_nome(ex: Exec) -> None:
        afirma(nome_i not in "\n".join(ex.out), "o nome do arquivo apareceu na saída")
    c.confere = sem_nome
    c = caso("R-bytes-assume-unchanged", "R")
    c.marcador = "P0:bytes"

    def assume(ex: Exec) -> None:
        ex.gitc(["update-index", "--assume-unchanged", "docs/a.md"])
        grava(os.path.join(ex.clone, "docs/a.md"), b"outro\n")
        status_vazio(ex)
        afirma(b"h docs/a.md" in ex.gitc(["ls-files", "-v"]), "bit ausente")
    c.plantio = assume
    c.esperado = ("P-BYTES", {"n": 1, "h": ident("docs/a.md")})
    c = caso("R-bytes-skip-worktree", "R")

    def skip(ex: Exec) -> None:
        ex.gitc(["update-index", "--skip-worktree", "README.md"])
        grava(os.path.join(ex.clone, "README.md"), b"outro\n")
        status_vazio(ex)
        afirma(b"S README.md" in ex.gitc(["ls-files", "-v"]), "bit ausente")
    c.plantio = skip
    c.esperado = ("P-BYTES", {"n": 1, "h": ident("README.md")})
    c = caso("R-bytes-eol", "R")

    def eol(ex: Exec) -> None:
        grava(os.path.join(ex.clone, ".git", "info", "attributes"), b"*.sh eol=crlf\n")
        os.remove(os.path.join(ex.clone, "scripts/install.sh"))
        ex.gitc(["checkout", "--", "scripts/install.sh"])
        afirma(b"\r\n" in le(os.path.join(ex.clone, "scripts/install.sh")), "plantio sem efeito")
        status_vazio(ex)
    c.plantio = eol
    c.esperado = ("P-BYTES", {"n": 1, "h": ident("scripts/install.sh")})
    c = caso("R-bytes-xbit", "R")

    def xbit(ex: Exec) -> None:
        ex.gitc(["config", "core.fileMode", "false"])
        os.chmod(os.path.join(ex.clone, "docs/a.md"), 0o755)
        status_vazio(ex)
    c.plantio = xbit
    c.esperado = ("P-BYTES", {"n": 1, "h": ident("docs/a.md")})
    c = caso("R-bytes-modo", "R")
    c.pk.pre["docs/link"] = ("120000", b"a.md")

    def link(ex: Exec) -> None:
        afirma(os.path.islink(os.path.join(ex.clone, "docs/link")), "plantio sem efeito")
        status_vazio(ex)
    c.plantio = link
    c.esperado = ("P-BYTES", {"n": 1, "h": ident("docs/link")})


DADOS_BASE_N = 7


def dados_com(linha_extra: bytes, posicao: Optional[int] = None) -> Callable[[Pacote], int]:
    def f(pk: Pacote) -> int:
        linhas = pk.dados().split(b"\n")[:-1]
        if posicao is None:
            linhas.append(linha_extra)
            n = len(linhas)
        else:
            linhas.insert(posicao - 1, linha_extra)
            n = posicao
        pk.dados_txt = b"\n".join(linhas) + b"\n"
        return n
    return f


def def_r_dados() -> None:
    def novo(nome: str, extra: bytes, motivo: str, posicao: Optional[int] = None, marc: str = "") -> None:
        c = caso(nome, "R")
        c.marcador = marc
        n = dados_com(extra, posicao)(c.pk)
        c.esperado = ("P-DATA", {"arg": DADOS, "n": n, "motivo": motivo})
    novo("R-dados-byte", "# \u0441".encode(), "byte fora do conjunto", 2, "P0:data")
    novo("R-dados-cr", b"# x\r", "byte fora do conjunto", 2)
    novo("R-dados-chave", b"foo\tbar", "chave fora da lista")
    novo("R-dados-tool", b"tool\tjq", "chave fora da lista")
    novo("R-dados-py-module", b"py-module\tyaml", "chave fora da lista")
    novo("R-dados-cardinalidade", b"rail\t" + RAIL.encode(), "cardinalidade")
    novo("R-dados-repetido", b"canonical\tscripts/install.sh", "valor repetido")
    novo("R-dados-campo-vazio", b"hard\tbash\t\tscripts/install.sh", "valor fora da gramática")
    for nome, argv in (
            ("R-argv-basetemp", "python3\t-m\tpytest\t--basetemp=/abs\thardtests/test_hard.py"),
            ("R-argv-junit", "python3\t-m\tpytest\t--junit-xml=/abs\thardtests/test_hard.py"),
            ("R-argv-x-ponto-ponto", "python3\ttools/hard_ok.py\t--x=.."),
            ("R-argv-k", "python3\t-m\tpytest\t-k\tx\thardtests/test_hard.py"),
            ("R-argv-c", "python3\t-m\tpytest\t-c\tpytest.ini\thardtests/test_hard.py"),
            ("R-argv-git", "git\tstatus"),
            ("R-argv-env", "env\tPYTHONUNBUFFERED=1\tpython3\t-m\tpytest\thardtests/test_hard.py"),
            ("R-argv-py-compile", "python3\t-m\tpy_compile\ttools/hard_ok.py"),
            ("R-argv-alvo-colchete", "python3\t-m\tpytest\thardtests/test_hard.py::test_a[1]")):
        novo(nome, b"hard\t" + argv.encode(), "valor fora da gramática")
    c = caso("R-dados-tamanho", "R")
    c.pk.dados_txt = c.pk.dados() + b"#\n" * 200
    c.esperado = ("P-DATA", {"arg": DADOS, "n": 201, "motivo": "tamanho"})
    c = caso("R-dados-sem-lf", "R")
    c.pk.dados_txt = c.pk.dados()[:-1]
    c.esperado = ("P-DATA", {"arg": DADOS, "n": DADOS_BASE_N, "motivo": "sem LF final"})
    c = caso("R-dados-ausente", "R")
    c.pk.sem_dados = True
    c.esperado_fn = lambda ex: ("P-DATA-AUS", {"arg": DADOS, "a": ex.c.a})


def bloco_falso(caminho: str, cab: str) -> Callable[[bytes], bytes]:
    def f(patch: bytes) -> bytes:
        return patch + cab.replace("@P@", caminho).encode()
    return f


def def_r_patch() -> None:
    c = caso("R-mat-rail", "R")
    c.marcador = "P0:mat"
    c.pk.rail_p = ".claude/plans/PLAN-900/pk1/rail-inexistente.md"
    c.esperado_fn = lambda ex: ("P-MAT", {"caminho": ".claude/plans/PLAN-900/pk1/rail-inexistente.md", "a": ex.c.a})
    c = caso("R-mat-hard-removido", "R")
    c.pk.pos["tools/hard_ok.py"] = None
    c.esperado_fn = lambda ex: ("P-MAT", {"caminho": "tools/hard_ok.py", "a": ex.c.a})
    z = "0" * 40
    um = "1" * 40
    casos_patch = [
        ("R-patch-rename", "diff --git a/docs/velho.md b/docs/velho2.md\nsimilarity index 100%\n"
         "rename from docs/velho.md\nrename to docs/velho2.md\n", "cabeçalho diff --git",
         "a/docs/velho.md?b/docs/velho2.md", "P0:patch"),
        ("R-patch-mode", "diff --git a/README.md b/README.md\nold mode 100644\nnew mode 100755\n",
         "linha de cabeçalho fora das formas", "README.md", ""),
        ("R-patch-aspas", 'diff --git "a/docs/x y.md" "b/docs/x y.md"\nnew file mode 100644\n',
         "cabeçalho diff --git", '?a/docs/x?y.md???b/docs/x?y.md?', ""),
        ("R-patch-a-existente", "diff --git a/README.md b/README.md\nnew file mode 100644\nindex " + z +
         ".." + um + "\n--- /dev/null\n+++ b/README.md\n@@ -0,0 +1 @@\n+x\n",
         "criação sobre caminho existente", "README.md", ""),
        ("R-patch-sentinel", "diff --git a/@P@ b/@P@\nindex " + um + ".." + um + " 100644\n--- a/@P@\n"
         "+++ b/@P@\n@@ -1 +1 @@\n-x\n+y\n", "caminho proibido", SENT, ""),
        ("R-patch-gitattributes", "diff --git a/.gitattributes b/.gitattributes\nnew file mode 100644\nindex "
         + z + ".." + um + "\n--- /dev/null\n+++ b/.gitattributes\n@@ -0,0 +1 @@\n+* text\n",
         "caminho proibido", ".gitattributes", ""),
        ("R-patch-molde", "diff --git a/@P@ b/@P@\nindex " + um + ".." + um + " 100644\n--- a/@P@\n"
         "+++ b/@P@\n@@ -1 +1 @@\n-x\n+y\n", "caminho proibido", BLOCO, ""),
    ]
    for nome, cab, regra, caminho, marc in casos_patch:
        c = caso(nome, "R")
        c.marcador = marc
        alvo = SENT if nome == "R-patch-sentinel" else BLOCO
        c.pk.patch_fn = bloco_falso(alvo, cab)
        c.esperado = ("P-PATCH", {"regra": regra, "caminho": caminho})
    c = caso("R-patch-binario", "R")

    def binario(patch: bytes) -> bytes:
        sha = sha1_blob(b"fixture sign-min\n")
        return patch + ("diff --git a/README.md b/README.md\nindex %s..%s 100644\nGIT binary patch\n"
                        "literal 0\nHcmV?d00001\n\n" % (sha, um)).encode()
    c.pk.patch_fn = binario
    c.esperado = ("P-PATCH", {"regra": "linha de cabeçalho fora das formas", "caminho": "README.md"})
    c = caso("R-patch-preimagem", "R")

    def preimagem(patch: bytes) -> bytes:
        sha = sha1_blob(b"linha 1\nlinha 2\n")
        afirma(sha.encode() in patch, "pré-imagem não encontrada no patch")
        return patch.replace(sha.encode(), um.encode())
    c.pk.patch_fn = preimagem
    c.esperado = ("P-PATCH", {"regra": "pré-imagem diferente do commit", "caminho": "docs/a.md"})
    c = caso("R-apply-check", "R")
    c.marcador = "P0:apply"

    def contexto(patch: bytes) -> bytes:
        afirma(b" linha 1\n" in patch, "contexto não encontrado")
        return patch.replace(b" linha 1\n", b" linha X\n")
    c.pk.patch_fn = contexto
    c.esperado = ("P-APPLY", {"r": 1})


def def_r_sent() -> None:
    c = caso("R-sentinel-3-tofill", "R")
    c.marcador = "P0:sent"
    c.pk.sent_fn = lambda t: t.replace("Anchor-SHA: TO-FILL-BY-SIGN\n", "")
    c.esperado = ("P-SENT", {"regra": "linha Anchor-SHA"})
    c = caso("R-sentinel-data-preenchida", "R")
    c.pk.sent_fn = lambda t: t.replace("Data: TO-FILL-BY-SIGN", "Data: 2026-10-11")
    c.esperado = ("P-SENT", {"regra": "linha Data"})
    c = caso("R-sentinel-bloco", "R")
    c.pk.sent_fn = lambda t: t.replace("bloco comum a todos", "bloco comum a quase todos")
    c.esperado = ("P-SENT", {"regra": "bloco comum diferente do molde"})
    c = caso("R-sentinel-scope", "R")
    c.pk.escopo = ["docs/a.md", "docs/novo.md", "docs/velho.md"]
    c.esperado = ("P-SCOPE", {"n": 1})
    c = caso("R-asc-head", "R")
    c.marcador = "P0:asc"
    c.pk.extra_a[ASC] = ("100644", b"-----BEGIN PGP SIGNATURE-----\n")
    c.esperado_fn = lambda ex: ("P-ASC", {"a": ex.c.a, "caminho": ASC})
    for nome, campo, troca, marc in (
            ("R-rail-subject", "Rail-Subject-sha256", "Rail-Subject-sha256: ", "P0:rail"),
            ("R-rail-sentinel", "Rail-Sentinel-sha256", "Rail-Sentinel-sha256: ", ""),
            ("R-rail-dados", "Rail-Data-sha256", "Rail-Data-sha256: ", "")):
        c = caso(nome, "R")
        c.marcador = marc
        c.pk.rail_fn = (lambda tr: lambda t: re.sub(re.escape(tr) + "[0-9a-f]{64}", tr + "f" * 64, t))(troca)
        c.esperado = ("P-RAIL", {"caminho": RAIL, "campo": campo})
    c = caso("R-rail-veredito", "R")
    c.pk.rail_fn = lambda t: t.replace("Rail-Verdict: APPROVE", "Rail-Verdict: FINDINGS")
    c.esperado = ("P-RAIL", {"caminho": RAIL, "campo": "Rail-Verdict"})
    c = caso("R-canon", "R")
    c.marcador = "P0:canon"
    c.pk.canonical = []
    c.esperado = ("P-CANON", {"n": 1})
    c = caso("R-kernel", "R")
    c.marcador = "P0:kernel"
    kp = ".claude/hooks/_lib/redact.py"
    c.pk.pos[kp] = ("100644", le(os.path.join(REPO, kp)) + b"# toque do caso R-kernel\n")
    c.pk.canonical = ["scripts/install.sh", kp]
    c.esperado = ("P-KERN", {"caminho": kp})
    c = caso("R-oraculo", "R")
    c.pk.extra_a[".claude/hooks/check_canonical_edit.py"] = ("100644", b"import sys\nsys.exit(3)\n")
    c.esperado = ("P-ORACLE", {"r": 3})
    c = caso("R-kernel-rc", "R")
    c.pk.extra_a[".claude/hooks/check_arbitration_kernel.py"] = ("100644", b"raise SystemExit(4)\n")
    c.esperado = ("P-KERN-RC", {"r": 4})
    c = caso("R-pymod", "R")
    c.marcador = "P0:pymod"

    def ub_vazio(ex: Exec, env: Dict[str, str]) -> None:
        d = os.path.join(ex.dir, "ub-vazio")
        os.makedirs(d, exist_ok=True)
        env["PYTHONUSERBASE"] = d
    c.env_fn = ub_vazio
    c.esperado = ("P-PYMOD", {"r": 1})
    c = caso("R-chave", "R")
    c.marcador = "P0:key"
    c.pk.extra_a[".claude/sentinel-signers.txt"] = ("100644", b"# outro\n" + b"AB" * 20 + b"\n")
    c.esperado_fn = lambda ex: ("P-KEY", {"a": ex.c.a})
    c = caso("R-allowlist-vazio", "R")
    c.pk.extra_a[".claude/sentinel-signers.txt"] = ("100644", b"# so comentarios\n# nada\n")
    c.esperado_fn = lambda ex: ("P-ALLOW", {"a": ex.c.a})


# ---------------------------------------------------------------------------
# casos de execução (H, F, K)
# ---------------------------------------------------------------------------

def executa(caso_: Caso, sobrepor: Optional[Dict[str, Optional[Tuple[str, bytes]]]] = None) -> Exec:
    ex = prepara(caso_, sobrepor)
    try:
        ex.extra["commits_antes"] = contagem_commits(ex)
        roda(ex)
        afirma(caso_.confere is not None, "caso sem conferência")
        caso_.confere(ex)  # type: ignore[misc]
    finally:
        if sobrepor is None:
            G.saidas.append((caso_.nome, "\n".join(ex.out) + ("\n" + ex.err.decode("utf-8", "replace") if ex.err else "")))
        limpa_caso(ex)
    return ex


def ultima_linhas(ex: Exec, chave: str, **valores: object) -> None:
    afirma(ex.rc == 1, "rc %s (esperado 1); saída %r" % (ex.rc, ex.out[-4:]))
    afirma(ex.out[-2:] == [msg(chave, **valores), msg("FIXA")],
           "fim da saída %r (esperado %r)" % (ex.out[-2:], [msg(chave, **valores), msg("FIXA")]))
    afirma(ex.err == b"", "stderr não vazio: %r" % ex.err[:200])


def sem_assinatura(ex: Exec) -> None:
    afirma(not any(ln.startswith("GPG --detach-sign") for ln in ex.ordem()), "houve assinatura")
    afirma(contagem_commits(ex) == ex.extra["commits_antes"], "houve commit novo")


def falha_antes(chave: str, **valores: object) -> Callable[[Exec], None]:
    def f(ex: Exec) -> None:
        vals = dict(valores)
        for k, v in list(vals.items()):
            if callable(v):
                vals[k] = v(ex)
        ultima_linhas(ex, chave, **vals)
        sem_assinatura(ex)
    return f


def t_arq(nome: str) -> Callable[[Exec], str]:
    return lambda ex: os.path.join(ex.t, nome)


def le_env(nome: str) -> Dict[str, str]:
    p = os.path.join(G.atual, "env-" + nome + ".txt")
    afirma(os.path.exists(p), "arquivo de ambiente ausente: %s" % nome)
    saida: Dict[str, str] = {}
    for linha in le(p).decode().splitlines():
        k, _s, v = linha.partition("=")
        saida[k] = v
    return saida


MARCADORES_FIXTURE = ("hard-", "teste-", "gate-")


def mensagem_esperada(ex: Exec, fpr: str) -> bytes:
    return (
        "ceremony(PLAN-900 pk1): patch e sentinel assinado pelo molde sign-min\n\n"
        "Dados: %s\nPatch: %s (sha256 %s)\nSentinel: %s\nAnchor-SHA: %s\nRail-Record-sha256: %s\n"
        "Signer: %s\n\nCo-Authored-By: Claude Opus 5.5 <noreply@anthropic.com>\n"
        % (DADOS, PATCH, sha256b(ex.c.patch), SENT, ex.c.a, sha256b(ex.c.rail), fpr)).encode()


def gpg_verifica(ex: Exec, sent: bytes, asc: bytes) -> str:
    d = os.path.join(ex.dir, "verif")
    os.makedirs(d, exist_ok=True)
    grava(os.path.join(d, "s"), sent)
    grava(os.path.join(d, "a"), asc)
    _rc, out, _e = sh([G.gpg_real, "--batch", "--status-fd", "1", "--verify", os.path.join(d, "a"),
                       os.path.join(d, "s")], env=env_h())
    fprs = [ln.split()[2] for ln in out.decode().splitlines() if ln.startswith("[GNUPG:] VALIDSIG")]
    afirma(b"[GNUPG:] GOODSIG" in out and len(fprs) == 1, "a .asc não verifica")
    return fprs[0]


def confere_h1(ex: Exec) -> None:
    afirma(ex.rc == 0, "rc %s; saída %r; err %r" % (ex.rc, ex.out[-3:], ex.err[:300]))
    afirma(ex.err == b"", "stderr não vazio")
    c_sha = ex.gitc(["rev-parse", "refs/heads/main"]).decode().strip()
    afirma(ex.out[-1] == msg("OK", c=c_sha, a=ex.c.a, n=len(ex.c.caminhos), fpr=G.fpr1),
           "linha final %r" % ex.out[-1])
    corpo = ex.gitc(["cat-file", "commit", c_sha])
    cab, _s, mensagem = corpo.partition(b"\n\n")
    pais = [ln for ln in cab.decode().split("\n") if ln.startswith("parent ")]
    afirma(pais == ["parent " + ex.c.a], "pais %r" % pais)
    for papel in ("author", "committer"):
        linha = [ln for ln in cab.decode().split("\n") if ln.startswith(papel + " ")][0]
        afirma(linha.startswith("%s %s <%s> " % (papel, NOME, EMAIL)), "identidade %r" % linha)
    afirma(mensagem == mensagem_esperada(ex, G.fpr1), "mensagem difere: %r" % mensagem[:200])
    raw = ex.gitc(["diff-tree", "-r", "-z", "--no-renames", ex.c.a, c_sha]).split(b"\0")
    obtido = set()
    for i in range(0, len(raw) - 1, 2):
        if raw[i]:
            m = raw[i].decode().lstrip(":").split(" ")
            obtido.add((m[4], m[0], m[1], m[2], m[3], raw[i + 1].decode()))
    s_c = ex.gitc(["cat-file", "blob", c_sha + ":" + SENT])
    g_c = ex.gitc(["cat-file", "blob", c_sha + ":" + ASC])
    s_a = ex.gitc(["cat-file", "blob", ex.c.a + ":" + SENT])
    esperado = {
        ("M", "100755", "100755", sha1_blob(b"#!/bin/bash\necho instalar\n"),
         sha1_blob(b"#!/bin/bash\necho instalar\necho fim\n"), "scripts/install.sh"),
        ("M", "100644", "100644", sha1_blob(b"linha 1\nlinha 2\n"), sha1_blob(b"linha 1\nlinha dois\n"), "docs/a.md"),
        ("A", "000000", "100644", "0" * 40, sha1_blob(b"novo\n"), "docs/novo.md"),
        ("D", "100644", "000000", sha1_blob(b"velho\n"), "0" * 40, "docs/velho.md"),
        ("M", "100644", "100644", sha1_blob(s_a), sha1_blob(s_c), SENT),
        ("A", "000000", "100644", "0" * 40, sha1_blob(g_c), ASC),
    }
    afirma(obtido == esperado, "diff-tree difere: %r" % (obtido ^ esperado))
    assinado = le(os.path.join(ex.t, "assinado", "sentinel"))
    afirma(sha1_blob(assinado) == sha1_blob(s_c), "o blob do sentinel no commit não é o dos bytes assinados")
    la, lc = s_a.decode().split("\n"), s_c.decode().split("\n")
    afirma(len(la) == len(lc), "o sentinel mudou de tamanho em linhas")
    mudadas = [(x, y) for x, y in zip(la, lc) if x != y]
    hoje = time.strftime("%Y-%m-%d", time.gmtime())
    afirma(mudadas == [
        ("Patch-sha256: TO-FILL-BY-SIGN", "Patch-sha256: " + sha256b(ex.c.patch)),
        ("Rail-Record-sha256: TO-FILL-BY-SIGN", "Rail-Record-sha256: " + sha256b(ex.c.rail)),
        ("Anchor-SHA: TO-FILL-BY-SIGN", "Anchor-SHA: " + ex.c.a),
        ("Data: TO-FILL-BY-SIGN", "Data: " + hoje)], "linhas mudadas %r" % mudadas)
    afirma(gpg_verifica(ex, s_c, g_c) == G.fpr1, "a .asc verifica com outra chave")
    afirma(le_env("hard-unbuf").get("PYTHONUNBUFFERED") == "1", "o envoltório não exportou PYTHONUNBUFFERED")
    afirma("PYTHONUNBUFFERED" not in le_env("hard-form4"), "a forma 4 recebeu PYTHONUNBUFFERED")
    afirma(not any(ln.startswith("MARCADOR") for ln in ex.ordem()), "um marcador plantado executou")
    afirma(c_sha == ex.gitc(["rev-parse", "HEAD"]).decode().strip(), "HEAD não acompanha main")
    ex.extra["c"] = c_sha


def confere_h1_ordem(ex: Exec) -> None:
    ordem = ex.ordem()
    afirma(any(ln.startswith("GPG --detach-sign") for ln in ordem), "nenhuma assinatura em ordem.log")
    i = [k for k, ln in enumerate(ordem) if ln.startswith("GPG --detach-sign")][0]
    antes = [ln for ln in ordem[:i] if ln.startswith(MARCADORES_FIXTURE)]
    depois = [ln for ln in ordem[i:] if ln.startswith(MARCADORES_FIXTURE)]
    afirma(len(antes) >= 3 + 2 + 13, "marcadores insuficientes antes da assinatura: %d" % len(antes))
    afirma(not depois, "marcador da fixture depois da assinatura: %r" % depois)


def confere_env_filhos(ex: Exec) -> None:
    """Todo hard, teste e gate da fixture: GNUPGHOME de T, sem GPG_TTY e TMPDIR = <T>/tmp-filhos real."""
    arquivos = glob.glob(os.path.join(G.atual, "env-*.txt"))
    nomes = [os.path.basename(a)[4:-4] for a in arquivos if os.path.basename(a)[4:].startswith(MARCADORES_FIXTURE)]
    afirma(len(nomes) >= 3 + 2 + 13, "arquivos de ambiente insuficientes: %d" % len(nomes))
    tmp = os.path.join(ex.t, "tmp-filhos")
    afirma(os.path.realpath(tmp) == tmp, "o TMPDIR esperado %r não é o caminho real" % tmp)
    parcial = "/"
    for parte in tmp.split("/")[1:]:
        parcial = os.path.join(parcial, parte)
        afirma(not os.path.islink(parcial), "componente do TMPDIR esperado é link simbólico: %r" % parcial)
    afirma(os.path.isdir(tmp) and (os.lstat(tmp).st_mode & 0o7777) == 0o700, "o TMPDIR esperado não é diretório 0700")
    for nome in nomes:
        env = le_env(nome)
        afirma(env.get("GNUPGHOME") == os.path.join(ex.t, "gnupg-vazio"), "%s: GNUPGHOME %r" % (nome, env.get("GNUPGHOME")))
        afirma("GPG_TTY" not in env, "%s recebeu GPG_TTY" % nome)
        afirma(env.get("TMPDIR") == tmp, "%s: TMPDIR %r (esperado %r)" % (nome, env.get("TMPDIR"), tmp))
        afirma(env.get("@tempdir") == tmp, "%s: tempfile.gettempdir() %r com TMPDIR %r" % (
            nome, env.get("@tempdir"), env.get("TMPDIR")))


def confere_h1_env(ex: Exec) -> None:
    confere_env_filhos(ex)


def plantios_h1(ex: Exec) -> None:
    marcador = os.path.join(ex.dir, "marcador.sh")
    grava(marcador, ("#!/bin/bash\nprintf 'MARCADOR %%s\\n' \"$0 $*\" >> %s\nexit 1\n"
                     % q(os.path.join(G.atual, "ordem.log"))).encode(), 0o755)
    modelo = os.path.join(ex.dir, "modelo.txt")
    grava(modelo, b"texto do commit.template plantado\n")
    # sentinel sem entrada «racy»: mtime antigo + refresh do índice antes do atributo ident
    agora = time.time() - 30
    for base, dirs, arquivos in os.walk(ex.clone):
        if ".git" in base.split(os.sep):
            continue
        for nome in arquivos:
            os.utime(os.path.join(base, nome), (agora, agora), follow_symlinks=False)
        if ".git" in dirs:
            dirs.remove(".git")
    ex.gitc(["update-index", "--refresh", "-q"])
    for chave, valor in (("commit.gpgsign", "true"), ("gpg.program", marcador), ("core.editor", marcador),
                         ("commit.template", modelo), ("gc.auto", "1"), ("alias.ci", "!" + marcador)):
        ex.gitc(["config", chave, valor])
        out = ex.gitc(["config", "--show-origin", "--get", chave])
        afirma(out == ("file:.git/config\t" + valor + "\n").encode(), "plantio %s sem efeito" % chave)
    grava(os.path.join(ex.clone, ".git", "info", "attributes"), b"*.md ident\n")
    afirma(ex.gitc(["check-attr", "ident", "--", SENT]) == (SENT + ": ident: set\n").encode(), "ident sem efeito")
    com = ex.gitc(["hash-object", SENT]).strip()
    sem = ex.gitc(["hash-object", "--no-filters", SENT]).strip()
    afirma(com != sem, "o atributo ident não muda o blob do sentinel")
    status_vazio(ex)


def def_h() -> None:
    c = caso("H1", "H", real=True)
    c.pk.sent_extra = "\nMarca: $Id: deadbeef $\n"
    c.plantio = plantios_h1
    c.confere = confere_h1
    caso("H1-ordem", "H")
    caso("H1-env", "H")
    c = caso("H2", "H")

    def confere_h2(ex: Exec) -> None:
        afirma(ex.rc == 0 and ex.out[-1] == msg("ENSAIO"), "rc %s; fim %r; err %r" % (ex.rc, ex.out[-2:], ex.err[:200]))
        afirma(ex.err == b"", "stderr não vazio")
        afirma(ex.t.startswith("/private/tmp/sign-min.") and os.path.isdir(ex.t), "T fora de /tmp: %r" % ex.t)
        afirma(contagem_commits(ex) == ex.extra["commits_antes"], "houve commit novo")
        afirma(ex.gitc(["rev-parse", "refs/heads/main"]).decode().strip() == ex.c.a, "main mudou")
        afirma(not os.path.exists(os.path.join(ex.clone, ASC)), "há .asc")
        afirma(le(os.path.join(ex.clone, SENT)) == ex.c.sent, "o sentinel difere do blob de A")
        afirma(not any(ln.startswith("GPG --detach-sign") for ln in ex.ordem()), "houve assinatura")
        confere_env_filhos(ex)
    c.confere = confere_h2


def def_f() -> None:
    def com_hard(c: Caso, nome_arq: str, corpo: bytes, forma: str = "bash") -> int:
        caminho = "tools/" + nome_arq
        c.pk.pre[caminho] = ("100644", corpo)
        c.pk.hard.append([forma, caminho])
        return len(c.pk.hard)

    c = caso("F1", "F")
    k = com_hard(c, "falha.sh", b"#!/bin/bash\nexit 1\n")
    c.confere = falha_antes("X-RC", rotulo="hard %d" % k, rc=1, arq=t_arq("hard-%d.log" % k))
    c = caso("F1b", "F")
    c.pk.pre["hardtests/test_skip.py"] = ("100644", b"import pytest\n\ndef test_ok():\n    pass\n\n\n"
                                          b"@pytest.mark.skip(reason='x')\ndef test_pula():\n    pass\n")
    c.pk.hard.append(["python3", "-m", "pytest", "-p", "no:cacheprovider", "-q", "hardtests/test_skip.py"])
    c.confere = falha_antes("X-PYT", rotulo="hard 5", arq=t_arq("hard-5.log"))
    c = caso("F2", "F")
    c.pk.pre["tests/test_vermelho.py"] = ("100644", b"def test_vermelho():\n    assert False\n")

    def confere_f2(ex: Exec) -> None:
        falha_antes("X-SUITE", p="paralela", k=1, arq=t_arq("sobram-paralela.txt"))(ex)
        logs = sorted(os.path.basename(x) for x in glob.glob(os.path.join(ex.t, "rerun-paralela-*")))
        afirma(logs == ["rerun-paralela-1-1.log", "rerun-paralela-1-2.log", "rerun-paralela-1-3.log"],
               "repetições isoladas: %r" % logs)
    c.confere = confere_f2
    c = caso("F3", "F")
    c.pk.pre["tests/test_flaky.py"] = ("100644", (
        "import os\n\ndef test_flaky():\n    p = %r\n    if not os.path.exists(p):\n"
        "        open(p, 'w').close()\n        assert False\n" % os.path.join(G.atual, "flaky.flag")).encode())

    def confere_f3(ex: Exec) -> None:
        afirma(ex.rc == 0 and ex.out[-1] == msg("ENSAIO"), "rc %s; fim %r" % (ex.rc, ex.out[-2:]))
        afirma(any(re.match(r"^SIGN-FATO: passada paralela: 1 id\(s\) falharam; 1 passaram numa repetição "
                            r"isolada \([0-9.]+ s\)$", ln) for ln in ex.out), "fato da passada ausente")
        afirma("test_flaky" not in "\n".join(ex.out), "o id apareceu na saída")
    c.confere = confere_f3
    c = caso("F3b", "F")
    c.pk.pre["tests/test_skip_isolado.py"] = ("100644", (
        "import os\nimport pytest\n\n@pytest.mark.skipif('PYTEST_XDIST_WORKER' not in os.environ, reason='x')\n"
        "def test_so_paralelo():\n    assert False\n").encode())
    c.confere = falha_antes("X-SUITE", p="paralela", k=1, arq=t_arq("sobram-paralela.txt"))
    c = caso("F-coleta", "F")
    c.pk.pre["tests/test_quebrado.py"] = ("100644", b"def test_x(:\n    pass\n")

    def confere_coleta(ex: Exec) -> None:
        falha_antes("X-COLETA", p="paralela", k=1, arq=t_arq("coleta-paralela.txt"))(ex)
        afirma(not glob.glob(os.path.join(ex.t, "rerun-paralela-*")), "houve repetição depois de erro de coleta")
    c.confere = confere_coleta
    c = caso("F4", "F")
    c.pk.pre["tests/test_escreve.py"] = ("100644", b"def test_escreve():\n    open('docs/a.md', 'a').write('x')\n")
    c.confere = falha_antes("X-IDX", n=1, arq=t_arq("indice-2.txt"))
    c = caso("F4b", "F")
    k = com_hard(c, "assume.sh", b"#!/bin/bash\ngit update-index --assume-unchanged docs/a.md && echo x >> docs/a.md\n")
    c.confere = falha_antes("X-IDX", n=1, arq=t_arq("indice-2.txt"))
    c = caso("F5", "F")
    c.pk.pre[".claude/scripts/check-docs-drift.py"] = ("100644", py_marca("gate-check-docs-drift.py", "raise SystemExit(1)\n"))
    c.confere = falha_antes("X-RC", rotulo="check-docs-drift.py", rc=1, arq=t_arq("gate-8.log"))
    c = caso("F-config", "F")
    com_hard(c, "config.sh", b"#!/bin/bash\ngit config commit.gpgsign true\n")
    c.confere = falha_antes("X-CFG")
    c = caso("F-config-global", "F")
    com_hard(c, "global.sh", b"#!/bin/bash\nprintf '[alias]\\n\\tx = status\\n' > \"$HOME/.gitconfig\"\n")
    c.confere = falha_antes("X-CFG")
    c = caso("F-ref", "F")
    com_hard(c, "ref.sh", b"#!/bin/bash\ngit update-ref refs/heads/main HEAD~1\n")
    c.confere = falha_antes("X-REF")
    c = caso("F-attr", "F")
    com_hard(c, "attr.sh", b"#!/bin/bash\nmkdir -p .git/info\nprintf '* filter=x\\n' >> .git/info/attributes\n")

    def confere_attr(ex: Exec) -> None:
        n = len(ex.gitc(["ls-files", "-z"]).split(b"\0")) - 1
        falha_antes("X-FILTER", n=n, arq=t_arq("filtro.txt"))(ex)
    c.confere = confere_attr
    c = caso("F6", "F", real=True)
    c.modo_gpg = "f6"
    c.confere = falha_antes("X-RC", rotulo="gpg", rc=2, arq=t_arq("gpg-sign.log"))

    def depois_9(chave: str, **valores: object) -> Callable[[Exec], None]:
        def f(ex: Exec) -> None:
            vals = {k: (v(ex) if callable(v) else v) for k, v in valores.items()}
            ultima_linhas(ex, chave, **vals)
            afirma(contagem_commits(ex) == ex.extra["commits_antes"], "houve commit novo")
        return f
    c.confere = depois_9("X-RC", rotulo="gpg", rc=2, arq=t_arq("gpg-sign.log"))
    c = caso("F-ver", "F", real=True)
    c.modo_gpg = "fver"
    c.confere = depois_9("X-VER", arq=t_arq("verify.txt"))
    c = caso("F7", "F")
    c.modo_git = "f7"

    def confere_f7(ex: Exec) -> None:
        ultima_linhas(ex, "X-RC", rotulo="git apply", rc=128, arq=os.path.join(ex.t, "apply.err"))
        texto = "\n".join(ex.out) + ex.err.decode("utf-8", "replace")
        afirma("Run" not in texto and "manually" not in texto, "texto do git chegou à saída")
        afirma(b"manually" in le(os.path.join(ex.t, "apply.err")), "a fachada não emitiu o ruído (plantio sem efeito)")
    c.confere = confere_f7
    c = caso("F8", "F")
    c.pk.pos["docs/grande.md"] = ("100644", b"".join(b"linha %06d do arquivo grande\n" % i for i in range(4000)))
    c.fsize = 65536
    c.plantio = lambda ex: ex.extra.__setitem__("marca_gpg", time.time())

    def confere_f8(ex: Exec) -> None:
        falha_antes("X-OS", rotulo="aplica", errno="EFBIG")(ex)
        grandes = []
        for base, _d, arqs in os.walk(G.gnupg):
            for nome in arqs:
                st = os.lstat(os.path.join(base, nome))
                if st.st_mtime > ex.extra["marca_gpg"] and st.st_size >= 65536:
                    grandes.append(nome)
        afirma(not grandes, "o gpg gravou no GNUPGHOME arquivo de 64 KiB ou mais: %r" % grandes)
        ex.notas.append("F8: o gpg não gravou no GNUPGHOME arquivo ≥ 64 KiB durante o P0")
    c.confere = confere_f8
    c = caso("F-bg", "F")
    k = com_hard(c, "bg.sh", ("#!/bin/bash\npython3 -B tools/marca.py hard-bg\n"
                              "( sleep 15; printf 'bg-tardio\\n' >> %s ) &\nexit 0\n"
                              % q(os.path.join(G.atual, "ordem.log"))).encode())
    c.timeout = 120
    c.confere = falha_antes("X-BG", rotulo="hard %d" % k, arq=t_arq("hard-%d.log" % k))
    c = caso("F-setsid", "F", real=True)
    c.pk.pre["tools/setsid_filho.py"] = ("100644", (
        "import os\nimport time\nos.setsid()\nlog = %r\nfim = time.time() + 120\n"
        "while time.time() < fim:\n    if 'GPG --detach-sign' in open(log).read():\n        break\n"
        "    time.sleep(0.1)\nwith open(log, 'a') as fh:\n"
        "    fh.write('hard-setsid-tardio %%d %%d\\n' %% (os.getpid(), os.getpgid(0)))\n"
        % os.path.join(G.atual, "ordem.log")).encode())
    c.pk.pre["tools/setsid.py"] = ("100644", (
        "import subprocess\nimport sys\n"
        "subprocess.Popen([sys.executable, '-B', 'tools/setsid_filho.py'], stdin=subprocess.DEVNULL,"
        " stdout=subprocess.DEVNULL, stderr=subprocess.DEVNULL)\n").encode())
    c.pk.hard.append(["python3", "tools/setsid.py"])

    def confere_setsid(ex: Exec) -> None:
        afirma(ex.rc == 0 and ex.out[-1].startswith("SIGN-OK:"), "rc %s; fim %r" % (ex.rc, ex.out[-2:]))
        fim_t = time.monotonic() + 30
        while time.monotonic() < fim_t and not any(ln.startswith("hard-setsid-tardio") for ln in ex.ordem()):
            time.sleep(0.2)
        ordem = ex.ordem()
        i = [k for k, ln in enumerate(ordem) if ln.startswith("GPG --detach-sign")]
        j = [k for k, ln in enumerate(ordem) if ln.startswith("hard-setsid-tardio")]
        afirma(i and j and j[0] > i[0], "o descendente com setsid não escreveu depois da assinatura")
        ex.notas.append("descendente com setsid escreveu depois da assinatura (resíduo declarado)")
    c.confere = confere_setsid
    c = caso("F-plant", "F")
    plantado = ("#!/bin/bash\nprintf 'PLANTADO %%s\\n' \"$(ps -o command= -p $PPID)\" >> %s\n"
                % q(os.path.join(G.atual, "ordem.log")))
    com_hard(c, "planta.sh", ("#!/bin/bash\nd=\"${PATH%%%%:*}\"\nfor f in git gpg; do printf '%%s' %s > \"$d/$f\"; "
                              "chmod +x \"$d/$f\"; done\ngit --version\n" % q(plantado)).encode())

    def confere_plant(ex: Exec) -> None:
        falha_antes("X-TOOL", nome="git")(ex)
        linhas = [ln for ln in ex.ordem() if ln.startswith("PLANTADO")]
        afirma(linhas, "o plantio não executou (plantio sem efeito)")
        afirma(not any("sign_min.py" in ln for ln in linhas), "o núcleo executou o plantado")
    c.confere = confere_plant
    c = caso("F-troca", "F")
    com_hard(c, "troca.sh", b"#!/bin/bash\nf=\"$(command -v gpg)\"\nprintf '# troca\\n' >> \"$f\"\n")
    c.confere = falha_antes("X-TOOL", nome="gpg")
    c = caso("F9", "F", real=True)
    c.modo_git = "f9"
    c.confere = depois_9("X-RC", rotulo="git commit", rc=128, arq=t_arq("git.log"))
    c = caso("F-exc", "F", real=True)
    c.modo_git = "hashobj"
    c.confere = depois_9("X-EXC", rotulo="índice do sentinel", tipo="ValueError")
    c = caso("F-commit", "F", real=True)
    c.modo_git = "fcommit"

    def confere_fcommit(ex: Exec) -> None:
        ultima_linhas(ex, "X-COMMIT", c=ex.c.a, arq=os.path.join(ex.t, "commit-detalhe.txt"))
    c.confere = confere_fcommit


def def_k() -> None:
    lento = ("100644", ("import time\n" + G.marca_func + "\n\ndef test_lento():\n    marca('teste-lento')\n"
                        "    time.sleep(6)\n").encode())
    for nome, sinal, rc in (("K1", signal.SIGKILL, -9), ("K2", signal.SIGTERM, -15)):
        c = caso(nome, "K")
        c.pk.pre["tests/test_lento.py"] = lento

        def ao_ler(ex: Exec, linha: str, sinal: int = sinal) -> None:
            if linha.startswith("SIGN-PASSO: 5 de 7"):
                time.sleep(1.5)
                ex.extra["n_morte"] = len(ex.out)
                os.kill(ex.proc.pid, sinal)  # type: ignore[union-attr]
        c.ao_ler = ao_ler

        def confere(ex: Exec, rc: int = rc) -> None:
            afirma(ex.rc == rc, "rc %s (esperado %s)" % (ex.rc, rc))
            afirma(len(ex.out) == ex.extra.get("n_morte"), "linha depois da morte: %r" % ex.out[-2:])
            afirma(ex.err == b"", "stderr não vazio")
            ex.notas.append("filhos da suíte encerrados pelo harness (grupo registrado)")
        c.confere = confere
    c = caso("K3", "K", real=True)
    c.pk.pre["tools/dorme.sh"] = ("100644", ("#!/bin/bash\nprintf '%%s\\n' $$ > %s\nsleep 6\n"
                                             % q(os.path.join(G.atual, "dorme.pid"))).encode())
    c.pk.hard.insert(0, ["bash", "tools/dorme.sh"])

    def ao_ler3(ex: Exec, linha: str) -> None:
        if linha.startswith("SIGN-PASSO: 4 de 12"):
            time.sleep(1.5)
            os.write(ex.mestre, b"\x03")  # type: ignore[arg-type]
    c.ao_ler = ao_ler3

    def confere3(ex: Exec) -> None:
        afirma(ex.rc == -signal.SIGINT, "rc %s (esperado -2 = 130 no shell)" % ex.rc)
        afirma(ex.err == b"", "stderr não vazio: %r" % ex.err[:200])
        afirma(not any("Traceback" in ln for ln in ex.out), "traceback")
        pid = int(le(os.path.join(G.atual, "dorme.pid")).decode().strip())
        vivo = True
        try:
            os.kill(pid, 0)
        except ProcessLookupError:
            vivo = False
        afirma(vivo, "o filho em sessão própria morreu com o INT")
        os.killpg(pid, signal.SIGKILL)
        ex.notas.append("filho da bateria vivo após o INT; encerrado pelo harness pelo pgid %d" % pid)
    c.confere = confere3
    c = caso("K4", "K", real=True)
    c.modo_git = "k4"

    def confere4(ex: Exec) -> None:
        afirma(ex.rc == -9, "rc %s (esperado -9)" % ex.rc)
        afirma(ex.out[-1] == msg("PASSO", k=11, n=12, rotulo="commit"), "linha depois do commit: %r" % ex.out[-1])
        # bloco (f) LAND-OK do roteiro, copiado literalmente
        land = ('[ "$(HOME="$LH" git diff-tree -r --no-renames --name-status "${ANCORA}" refs/heads/main | LC_ALL=C sort)" = '
                '"$( { HOME="$LH" git show "${ANCORA}:${P}" | awk \'/^diff --git a\\//{if(p!="")print s"\\t"p; p=$3; '
                'sub(/^a\\//,"",p); s="M"} /^new file mode/{s="A"} /^deleted file mode/{s="D"} END{if(p!="")print s"\\t"p}\'; '
                'printf \'M\\t%s\\nA\\t%s.asc\\n\' "${SE}" "${SE}"; } | LC_ALL=C sort)" ]')
        env = {"PATH": SIS_PATH, "LH": ex.home, "ANCORA": ex.c.a, "P": PATCH, "SE": SENT, "HOME": ex.home}
        rc, _o, _e = sh(["/bin/bash", "-c", land], cwd=ex.clone, env=env, ok=False)
        c_sha = ex.gitc(["rev-parse", "refs/heads/main"]).decode().strip()
        pais = [ln for ln in ex.gitc(["cat-file", "commit", c_sha]).decode().split("\n") if ln.startswith("parent ")]
        s_c = ex.gitc(["cat-file", "blob", c_sha + ":" + SENT])
        g_c = ex.gitc(["cat-file", "blob", c_sha + ":" + ASC])
        ancora_ok = ("Anchor-SHA: " + ex.c.a) in s_c.decode()
        fpr = gpg_verifica(ex, s_c, g_c)
        afirma(rc == 0 and pais == ["parent " + ex.c.a] and ancora_ok and fpr == G.fpr1,
               "LAND-OK rc %s, pais %r, âncora %s, fpr %s" % (rc, pais, ancora_ok, fpr))
        ex.notas.append("K4 medido pela ref: LAND-OK rc 0; pai único = âncora; a .asc verifica com a chave do allowlist")
    c.confere = confere4
    c = caso("K5", "K")
    c.pk.pre["tools/dorme2.sh"] = ("100644", b"#!/bin/bash\nsleep 2\n")
    c.pk.hard.insert(0, ["bash", "tools/dorme2.sh"])

    def ao_ler5(ex: Exec, linha: str) -> None:
        if len(ex.out) == 1:
            ex.proc.stdout.close()  # type: ignore[union-attr]
    c.ao_ler = ao_ler5

    def confere5(ex: Exec) -> None:
        afirma(ex.rc == -signal.SIGPIPE, "rc %s (esperado -13 = 141 no shell)" % ex.rc)
        afirma(ex.err == b"", "stderr não vazio: %r" % ex.err[:200])
    c.confere = confere5
    c = caso("K6", "K")
    c.modo_git = "k6"
    c.pk.pos["docs/enorme.md"] = ("100644", b"".join(b"linha %07d do arquivo enorme\n" % i for i in range(45000)))

    def confere6(ex: Exec) -> None:
        afirma(len(ex.c.patch) > 1024 * 1024, "o patch não passa de 1 MiB")
        afirma(ex.rc == -signal.SIGPIPE, "rc %s (esperado -13 = 141 no shell)" % ex.rc)
        afirma(ex.out == [], "saída %r" % ex.out)
        afirma(ex.err == b"", "stderr não vazio")
    c.confere = confere6


# ---------------------------------------------------------------------------
# censos
# ---------------------------------------------------------------------------

def censo_ast(fonte: str) -> List[str]:
    arvore = ast.parse(fonte)
    erros: List[str] = []
    mensagens: Dict[str, str] = {}
    for no in arvore.body:
        if isinstance(no, (ast.Assign, ast.AnnAssign)):
            alvo = no.targets[0] if isinstance(no, ast.Assign) else no.target
            if isinstance(alvo, ast.Name) and alvo.id == "MENSAGENS" and isinstance(no.value, ast.Dict):
                for k, v in zip(no.value.keys, no.value.values):
                    if not (isinstance(k, ast.Constant) and isinstance(v, ast.Constant) and isinstance(v.value, str)):
                        erros.append("MENSAGENS com entrada não literal")
                    else:
                        mensagens[str(k.value)] = v.value
    if not mensagens:
        erros.append("MENSAGENS ausente")
    funcoes: Dict[ast.AST, str] = {}
    for no in ast.walk(arvore):
        if isinstance(no, ast.FunctionDef):
            for filho in ast.walk(no):
                funcoes.setdefault(filho, no.name)

    def dentro(no: ast.AST) -> str:
        return funcoes.get(no, "")
    sub_ok = set("rev-parse symbolic-ref config var ls-files check-attr status cat-file ls-tree apply "
                 "hash-object update-index diff-index diff-tree commit".split())
    sub_proibidos = set("add push fetch update-ref reset checkout restore clean stash worktree rm gc prune".split())
    for no in ast.walk(arvore):
        if isinstance(no, ast.Name) and no.id == "print":
            erros.append("print fora de say")
        if isinstance(no, ast.Attribute) and isinstance(no.value, ast.Name):
            par = (no.value.id, no.attr)
            if par in (("sys", "stdout"), ("sys", "stderr"), ("os", "write")) and dentro(no) != "say":
                erros.append("%s.%s fora de say" % par)
            if no.value.id == "subprocess" and dentro(no) != "run":
                erros.append("subprocess fora de run")
            if par in (("os", "system"), ("os", "popen"), ("os", "remove"), ("os", "unlink"), ("shutil", "rmtree"),
                       ("Path", "home"), ("os", "getenv")):
                erros.append("%s.%s proibido" % par)
        if isinstance(no, ast.Attribute) and no.attr == "expanduser":
            erros.append("expanduser proibido")
        if isinstance(no, ast.Name) and no.id in ("eval", "exec", "compile", "__import__"):
            erros.append("%s proibido" % no.id)
        if isinstance(no, ast.Subscript) and isinstance(no.slice, ast.Constant) and no.slice.value == "HOME":
            erros.append("leitura de HOME")
        if (isinstance(no, ast.Call) and isinstance(no.func, ast.Attribute) and no.func.attr in ("get", "getenv")
                and no.args and isinstance(no.args[0], ast.Constant) and no.args[0].value == "HOME"):
            erros.append("leitura de HOME")
        if isinstance(no, ast.keyword) and no.arg == "shell":
            erros.append("shell= presente")
        if isinstance(no, ast.List):
            for e in no.elts:
                if isinstance(e, ast.Constant) and e.value in sub_proibidos:
                    erros.append("subcomando proibido %s" % e.value)
        if isinstance(no, ast.Call):
            nome = no.func.id if isinstance(no.func, ast.Name) else (no.func.attr if isinstance(no.func, ast.Attribute) else "")
            if nome == "say":
                if not no.args or not isinstance(no.args[0], ast.Constant) or no.args[0].value not in mensagens:
                    erros.append("say sem chave literal do catálogo (linha %d)" % no.lineno)
                for kw in no.keywords:
                    if not isinstance(kw.value, (ast.Name, ast.Attribute, ast.Subscript)):
                        erros.append("say com valor %s (linha %d)" % (type(kw.value).__name__, no.lineno))
            if nome == "run":
                a0 = no.args[0] if no.args else None
                lista0 = a0 if isinstance(a0, ast.List) else (a0.left if isinstance(a0, ast.BinOp) else None)
                if not isinstance(lista0, ast.List):
                    erros.append("run sem lista (linha %d)" % no.lineno)
                elif lista0.elts and isinstance(lista0.elts[0], ast.Constant) and lista0.elts[0].value in ("git", "gpg"):
                    erros.append("argv começa com o literal %s (linha %d)" % (lista0.elts[0].value, no.lineno))
            if nome in ("git", "git_ok") and dentro(no) not in ("git", "git_ok"):
                a0 = no.args[0] if no.args else None
                lista = a0 if isinstance(a0, ast.List) else (a0.left if isinstance(a0, ast.BinOp) else None)
                if not isinstance(lista, ast.List):
                    erros.append("git sem lista (linha %d)" % no.lineno)
                else:
                    sub = None
                    pula = False
                    for e in lista.elts:
                        if pula:
                            pula = False
                            continue
                        if isinstance(e, ast.Constant) and e.value == "-c":
                            pula = True
                            continue
                        if isinstance(e, ast.Constant) and isinstance(e.value, str) and not e.value.startswith("-"):
                            sub = e.value
                            break
                    if sub not in sub_ok:
                        erros.append("subcomando git %r (linha %d)" % (sub, no.lineno))
            if nome == "verify_detached":
                kws = {kw.arg: kw.value for kw in no.keywords}
                v = kws.get("gpg_bin")
                if not (isinstance(v, ast.Attribute) and v.attr == "gpg_abs"):
                    erros.append("verify_detached sem gpg_bin=GPG_ABS")
    # run do núcleo com st.git_abs: subcomando na lista literal
    for no in ast.walk(arvore):
        if isinstance(no, ast.Call) and isinstance(no.func, ast.Name) and no.func.id == "run" and no.args:
            a0 = no.args[0]
            if isinstance(a0, ast.List) and a0.elts and isinstance(a0.elts[0], ast.Attribute) and a0.elts[0].attr == "git_abs":
                subs = [e.value for e in a0.elts[1:] if isinstance(e, ast.Constant) and isinstance(e.value, str)
                        and not e.value.startswith("-") and "=" not in e.value]
                if not subs or subs[0] not in sub_ok:
                    erros.append("run de git com subcomando %r" % (subs[:1],))
    # sinais: exatamente 2, ambos SIG_DFL, antes de qualquer outra chamada
    chamadas = []
    for no in arvore.body:
        for filho in ast.walk(no):
            if isinstance(filho, ast.Call):
                chamadas.append(filho)
        if len(chamadas) >= 2:
            break
    sinais = [n for n in ast.walk(arvore) if isinstance(n, ast.Call) and isinstance(n.func, ast.Attribute)
              and n.func.attr == "signal" and isinstance(n.func.value, ast.Name) and n.func.value.id == "signal"]
    if len(sinais) != 2 or chamadas[:2] != sinais or not all(
            isinstance(s.args[1], ast.Attribute) and s.args[1].attr == "SIG_DFL" for s in sinais):
        erros.append("signal.signal fora da forma (2 × SIG_DFL antes de qualquer chamada)")
    for chave, valor in mensagens.items():
        if chave == "FIXA":
            continue
        ruins = palavras_proibidas(valor)
        if ruins:
            erros.append("MENSAGENS[%s] com %s" % (chave, ruins))
    return erros


def tokens_bash(linha: str) -> List[Tuple[str, str]]:
    """(tipo, valor): tipo ∈ {w, op}; aspas resolvidas; comentário removido."""
    saida: List[Tuple[str, str]] = []
    i = 0
    atual = ""
    tem = False
    n = len(linha)

    def fecha() -> None:
        nonlocal atual, tem
        if tem:
            saida.append(("w", atual))
        atual = ""
        tem = False
    while i < n:
        ch = linha[i]
        if ch == "'":
            j = linha.index("'", i + 1)
            atual += linha[i + 1:j]
            tem = True
            i = j + 1
            continue
        if ch == '"':
            j = i + 1
            while linha[j] != '"':
                j += 2 if linha[j] == "\\" else 1
            atual += linha[i + 1:j]
            tem = True
            i = j + 1
            continue
        if ch == "#" and not tem:
            break
        if linha.startswith("$(", i):
            fecha()
            saida.append(("op", "$("))
            i += 2
            continue
        if linha.startswith("<<", i):
            fecha()
            saida.append(("op", "<<"))
            i += 2
            continue
        if ch == "&" and atual and atual[-1] in "<>":
            atual += ch
            i += 1
            continue
        for op in (";;", "&&", "||", ";", "|", "&", "(", ")"):
            if linha.startswith(op, i):
                fecha()
                saida.append(("op", op))
                i += len(op)
                break
        else:
            if ch in " \t":
                fecha()
            else:
                atual += ch
                tem = True
            i += 1
    fecha()
    return saida


def censo_bash(texto: str, cat: Dict[str, str]) -> List[str]:
    erros: List[str] = []
    inv: List[Tuple[str, List[str]]] = []
    for linha in texto.split("\n"):
        toks = tokens_bash(linha)
        pos_cmd = True
        for k, (tipo, valor) in enumerate(toks):
            if tipo == "op":
                if valor == "<<":
                    erros.append("heredoc")
                pos_cmd = valor in (";;", "&&", "||", ";", "|", "&", "(", ")", "$(")
                continue
            if pos_cmd:
                if re.match(r"^[A-Za-z_][A-Za-z0-9_]*=", valor):
                    continue
                if valor in ("{", "}"):
                    continue
                args = []
                for t2, v2 in toks[k + 1:]:
                    if t2 == "op":
                        break
                    args.append(v2)
                inv.append((valor, args))
                pos_cmd = valor in ("then", "do", "else", "exec", "!")
            else:
                pos_cmd = valor in ("then", "do", "else") and False
    nomes = [n for n, _a in inv]
    for proibido in ("echo", "eval", "source", ".", "trap", "rm", "git", "gpg", "export"):
        if proibido in nomes:
            erros.append("invocação de %s" % proibido)
    printfs = [a for n, a in inv if n == "printf"]
    e_msgs = set(v for k, v in cat.items() if k.startswith("E-"))
    if len(printfs) != 5:
        erros.append("%d invocações de printf (esperado 5)" % len(printfs))
    for a in printfs:
        if len(a) != 3 or a[0] != "%s\\n" or a[1] not in e_msgs or a[2] != cat["FIXA"]:
            erros.append("printf fora da forma: %r" % a[:3])
    if nomes.count("python3") != 2:
        erros.append("%d invocações de python3 (esperado 2)" % nomes.count("python3"))
    if [a[:2] for n, a in inv if n == "command"] != [["-v", "python3"]]:
        erros.append("command -v python3 fora da forma")
    for m in ("# E:src", "# E:path", "# E:py", "# E:args", "# E:sha"):
        if texto.count(m) != 1:
            erros.append("marcador %s" % m)
    return erros


def caso_c1() -> None:
    erros = censo_ast(le(os.path.join(REPO, NUCLEO)).decode())
    afirma(not erros, "C1: %s" % erros)
    fonte = le(os.path.join(REPO, NUCLEO)).decode()
    controles = {
        "print": fonte.replace("def fim() -> None:\n", "def fim() -> None:\n    print('x')\n", 1),
        "say-literal": fonte.replace('say("P-CWD")', 'say("P-CWD", x="lit")', 1),
        "git-push": fonte.replace('["status", "--porcelain=v1"', '["push", "--porcelain=v1"', 1),
        "argv-git": fonte.replace("[st.git_abs] + args", '["git"] + args', 1),
        "home": fonte.replace("def fim() -> None:\n", "def fim() -> None:\n    os.environ['HOME']\n", 1),
        "sinal": fonte.replace("signal.signal(signal.SIGPIPE, signal.SIG_DFL)\n", "", 1),
        "gpg_bin": fonte.replace("gpg_bin=st.gpg_abs)", "gpg_bin=None)", 1),
    }
    for nome, mutado in controles.items():
        afirma(mutado != fonte, "controle C1 %s não mudou a fonte" % nome)
        afirma(censo_ast(mutado), "controle C1 %s não foi pego" % nome)


def caso_c2() -> None:
    cat = G.cat["MENSAGENS"]  # type: ignore[assignment]
    texto = le(os.path.join(REPO, ENTRADA)).decode()
    afirma(not censo_bash(texto, cat), "C2: %s" % censo_bash(texto, cat))  # type: ignore[arg-type]
    for nome, extra in (("python3 a mais", "python3 -c 1\n"), ("rm", "rm -f x\n"), ("ponto", ". ./x\n"),
                        ("git depois de &&", "true && git status\n")):
        afirma(censo_bash(texto + extra, cat), "controle C2 %s não foi pego" % nome)  # type: ignore[arg-type]


def caso_c3() -> None:
    modelos = [re.compile(regex_modelo(m)) for m in G.cat["MENSAGENS"].values()]  # type: ignore[union-attr]
    fixa = G.cat["MENSAGENS"]["FIXA"]  # type: ignore[index]
    total = 0
    for nome, saida in G.saidas:
        for linha in saida.split("\n"):
            if linha == "":
                continue
            total += 1
            afirma(any(m.match(linha) for m in modelos), "C3 forma: %s: %r" % (nome, linha))
            if linha != fixa:
                afirma(not palavras_proibidas(linha), "C3 palavras: %s: %r %s" % (nome, linha, palavras_proibidas(linha)))
    afirma(total > 100, "C3 viu poucas linhas: %d" % total)
    ruim = "SIGN-PASSO: 1 de 12: rótulo inventado"
    afirma(not any(m.match(ruim) for m in modelos), "controle C3 (rótulo fora de ROTULOS) não foi pego")
    afirma(not any(m.match("fatal: not a git repository") for m in modelos), "controle C3 (stderr) não foi pego")
    fonte = le(os.path.join(REPO, NUCLEO)).decode()
    for nome, entrada in (("ja landou", '"Z1": "SIGN-FATO: ja landou",\n'),
                          ("concatenação", '"Z1": "SIGN-FATO: INTER" "ROMPIDA",\n'),
                          ("cirílico", '"Z1": "SIGN-FATO: r\u0435cuperado",\n'),
                          ("espaçado", '"Z1": "SIGN-FATO: L O T E",\n'),
                          ("largura total", '"Z1": "SIGN-FATO: \uff4c\uff4f\uff54\uff45",\n')):
        mutado = fonte.replace('    "FIXA": "Pare e chame o CEO.",\n', '    "FIXA": "Pare e chame o CEO.",\n    ' + entrada, 1)
        afirma(mutado != fonte, "controle C3 %s não mudou a fonte" % nome)
        afirma(any("MENSAGENS[Z1]" in e for e in censo_ast(mutado)), "controle C3 %s não foi pego" % nome)


def caso_c4() -> None:
    t = le(os.path.join(REPO, BLOCO)).decode()
    afirma("TO-FILL" not in t and "<!--" not in t and "## Scope" not in t, "C4: token, marcador ou Scope no bloco")
    afirma(not re.search(r"(?i)lote", t), "C4: «lote» no bloco")
    afirma(t.endswith("\n") and not t.endswith("\n\n"), "C4: fim do bloco")


def caso_c5() -> None:
    env = env_h({"HOME": G.home_h})
    out = git(["-C", REPO, "ls-files", "-s", "--"] + ARQS_MOLDE, env=env).decode()
    modos = {ln.split("\t")[1]: ln.split(" ")[0] for ln in out.splitlines()}
    for caminho in ARQS_MOLDE:
        afirma(modos.get(caminho) == "100644", "C5: modo no índice de %s = %s" % (caminho, modos.get(caminho)))
        afirma(not (os.stat(os.path.join(REPO, caminho)).st_mode & 0o111), "C5: bit de execução no FS: %s" % caminho)
    py_env = {"PATH": SIS_PATH, "HOME": G.home_h}
    _rc, lista, _e = sh([G.py, "-B", os.path.join(REPO, ".claude/scripts/check-ceremony-script.py"), "--list"],
                        cwd=REPO, env=py_env)
    afirma(ENTRADA in lista.decode(), "C5: a entrada não é candidata do ceremony-lint")
    rc, saida, _e = sh([G.py, "-B", os.path.join(REPO, ".claude/scripts/check-ceremony-script.py")],
                       cwd=REPO, env=py_env, ok=False)
    afirma(rc == 0, "C5: ceremony-lint rc %d" % rc)
    blocking = [ln for ln in saida.decode().splitlines() if "BLOCKING" in ln and ENTRADA in ln]
    afirma(rc == 0 and not blocking, "C5: BLOCKING na entrada: %r" % blocking)


# ---------------------------------------------------------------------------
# ensaio real (W5b) em --dry-run
# ---------------------------------------------------------------------------

W5B_HARD = [
    ["bash", "-n", "scripts/install.sh"],
    ["python3", ".claude/scripts/check-installer-write-safety.py"],
    ["bash", "scripts/tests/test-install-deny-baseline.sh"],
    ["python3", "-m", "pytest", "-p", "no:cacheprovider", "-q", "-rfE", "--tb=no",
     ".claude/scripts/tests/test_install_sh_placeholders.py"],
    ["python3", ".claude/scripts/check-time-unit.py", "docs/deny-baseline.md"],
    ["python3", ".claude/scripts/check-install-profiles.py"],
    ["python3", ".claude/scripts/gen-settings-user-template.py", "--check"],
    ["bash", "scripts/tests/test-manifest-delivery-route.sh"],
    ["python3", ".claude/scripts/validate_governance_fast.py"],
]


def diagnostico_ensaio(t: str) -> str:
    """Listas que o próprio SIGN gravou em T (ids e erros de coleta), para o relatório da falha."""
    partes = []
    for nome in sorted(os.listdir(t)) if t and os.path.isdir(t) else []:
        if nome.startswith(("sobram-", "coleta-", "ids-")) and nome.endswith(".txt"):
            partes.append("%s: %s" % (nome, le(os.path.join(t, nome)).decode("utf-8", "replace")[:4000].strip()))
    return "; ".join(partes)


def caso_ensaio_w5b(w5b: str) -> None:
    d = tempfile.mkdtemp(prefix="w5b.", dir=G.h)
    try:
        origin = os.path.join(d, "origin.git")
        env = env_h({"HOME": G.home_h})
        git(["clone", "-q", "--bare", "--single-branch", REPO, origin], env=env)
        head = gitb(origin, ["rev-parse", "HEAD"], env=env).decode().strip()
        afirma(head == git(["-C", REPO, "rev-parse", "HEAD"], env=env).decode().strip(), "HEAD do origin difere")
        patch = le(os.path.join(w5b, ".claude/plans/PLAN-194/w5b/w5b.patch"))
        sent_orig = le(os.path.join(w5b, ".claude/plans/PLAN-194/w5b-approved.md")).decode()
        dados_p = ".claude/plans/PLAN-194/w5b/sign.tsv"
        rail_p = ".claude/plans/PLAN-194/w5b/rail-ensaio-sign-min.md"
        linhas = sent_orig.split("\n")
        i_wave = [k for k, ln in enumerate(linhas) if ln.startswith("Wave:")][0]
        linhas[i_wave + 1:i_wave + 1] = ["Dados: " + dados_p, "Molde: " + ENTRADA]
        i_scope = linhas.index("## Scope")
        linhas[i_scope:i_scope] = ["<!-- bloco-comum sign-min v1 -->"] + bloco_txt().split("\n")[:-1] + [
            "<!-- fim do bloco-comum -->", ""]
        sent = "\n".join(linhas).encode()
        dados = ("format\tsign-min-1\nrail\t" + rail_p + "\ncanonical\tscripts/install.sh\n" +
                 "".join("hard\t" + "\t".join(h) + "\n" for h in W5B_HARD)).encode()
        rail = texto_rail(patch, sent, dados).encode()
        signers = le(os.path.join(REPO, ".claude/sentinel-signers.txt")) + (
            "# chave descartável do ensaio do harness sign-min\n%s\n" % G.fpr1).encode()
        idx = os.path.join(d, "idx")
        envi = env_h({"HOME": G.home_h, "GIT_INDEX_FILE": idx})
        gitb(origin, ["read-tree", head], env=envi)
        for caminho, dados_b in ((".claude/plans/PLAN-194/w5b/w5b.patch", patch),
                                 (".claude/plans/PLAN-194/w5b-approved.md", sent), (dados_p, dados),
                                 (rail_p, rail), (".claude/sentinel-signers.txt", signers),
                                 (ENTRADA, le(os.path.join(REPO, ENTRADA))), (NUCLEO, le(os.path.join(REPO, NUCLEO))),
                                 (BLOCO, le(os.path.join(REPO, BLOCO)))):
            sha = gitb(origin, ["hash-object", "-w", "--no-filters", "--stdin"], entrada=dados_b, env=envi).decode().strip()
            gitb(origin, ["update-index", "--add", "--cacheinfo", "100644,%s,%s" % (sha, caminho)], env=envi)
        arvore = gitb(origin, ["write-tree"], env=envi).decode().strip()
        a = gitb(origin, ["commit-tree", arvore, "-p", head, "-m", "ensaio W5b (materiais de teste)"], env=envi).decode().strip()
        gitb(origin, ["update-ref", "refs/heads/main", a], env=envi)
        gitb(origin, ["symbolic-ref", "HEAD", "refs/heads/main"], env=envi)
        clone = os.path.join(d, "clone")
        home = os.path.join(d, "home")
        os.makedirs(home)
        clona(origin, clone, home)
        sha_nucleo = sha256f(os.path.join(clone, NUCLEO))
        caminho_env = ":".join(p for p in os.environ.get("PATH", SIS_PATH).split(":") if p.startswith("/") and os.path.isdir(p))
        env_sign_ = {"PATH": caminho_env, "HOME": home, "USER": os.environ.get("USER", "fixture"),
                     "LOGNAME": os.environ.get("LOGNAME", os.environ.get("USER", "fixture")), "SHELL": "/bin/bash",
                     "TERM": "xterm-256color", "LANG": "en_US.UTF-8", "PAGER": "cat", "GPG_TTY": "not a tty",
                     "GNUPGHOME": G.gnupg, "PYTHONUSERBASE": G.pyub}
        commits_antes = len(git(["-C", clone, "rev-list", "--all"], env=env).splitlines())
        inicio = time.monotonic()
        p = subprocess.run(["/usr/bin/env", "-i"] + ["%s=%s" % kv for kv in env_sign_.items()] +
                           ["bash", ENTRADA, "--nucleo-sha256=" + sha_nucleo, "--dry-run", dados_p],
                           cwd=clone, stdin=subprocess.DEVNULL, stdout=subprocess.PIPE, stderr=subprocess.PIPE,
                           start_new_session=True, timeout=5400)
        dur = time.monotonic() - inicio
        out = p.stdout.decode("utf-8", "replace")
        G.saidas.append(("ENSAIO-W5B", out + p.stderr.decode("utf-8", "replace")))
        linhas_out = out.splitlines()
        grava(os.path.join(G.h, "ensaio-w5b.out"), p.stdout + b"\n--stderr--\n" + p.stderr)
        tl = [ln[len("SIGN-FATO: logs em "):] for ln in linhas_out if ln.startswith("SIGN-FATO: logs em ")]
        t = tl[0] if tl else ""
        # o ensaio só passa com SIGN-ENSAIO e rc 0: nenhum desfecho de falha é aceito
        afirma(p.returncode == 0 and linhas_out[-1:] == [msg("ENSAIO")] and p.stderr == b"",
               "ensaio W5b: SIGN-RC=%d; fim %r; stderr %r; %s" % (
                   p.returncode, linhas_out[-3:], p.stderr[:300], diagnostico_ensaio(t)))
        for k in range(1, len(W5B_HARD) + 1):
            afirma(any(re.match(r"^SIGN-FATO: hard %d saiu rc 0 \([0-9.]+ s\)$" % k, ln) for ln in linhas_out),
                   "ensaio W5b: hard %d sem rc 0" % k)
        passadas = [ln for ln in linhas_out if re.match(r"^SIGN-FATO: passada (paralela|serial): ", ln)]
        afirma([ln.split(":")[1].strip() for ln in passadas] == ["passada paralela", "passada serial"],
               "ensaio W5b: passadas %r" % passadas)
        n_rc0 = sum(1 for ln in linhas_out if re.match(r"^SIGN-FATO: .+ saiu rc 0 \([0-9.]+ s\)$", ln))
        afirma(n_rc0 == len(W5B_HARD) + len(GATES), "ensaio W5b: %d linhas «saiu rc 0» (esperado %d)" % (
            n_rc0, len(W5B_HARD) + len(GATES)))
        afirma(len(git(["-C", clone, "rev-list", "--all"], env=env).splitlines()) == commits_antes, "ensaio: commit novo")
        afirma(not os.path.exists(os.path.join(clone, ".claude/plans/PLAN-194/w5b-approved.md.asc")), "ensaio: .asc")
        afirma(le(os.path.join(clone, ".claude/plans/PLAN-194/w5b-approved.md")) == sent, "ensaio: sentinel mudou")
        G.ensaio = "W5b --dry-run: SIGN-RC=0 (SIGN-ENSAIO); %d hard e %d gates rc 0; %s; %.0f s; %d linhas" % (
            len(W5B_HARD), len(GATES), "; ".join(ln[len("SIGN-FATO: "):].rsplit(" (", 1)[0] for ln in passadas),
            dur, len(linhas_out))
    finally:
        if not G.manter:
            shutil.rmtree(d, ignore_errors=True)


# ---------------------------------------------------------------------------
# orquestração
# ---------------------------------------------------------------------------

def prepara_gnupg() -> None:
    G.gnupg = tempfile.mkdtemp(prefix="smg.", dir="/tmp")
    afirma(len(G.gnupg) + 13 <= 100, "GNUPGHOME longo demais")
    os.chmod(G.gnupg, 0o700)
    for nome in ("Fixture Signer <signer@example.invalid>", "Fixture Outra <outra@example.invalid>"):
        sh([G.gpg_real, "--batch", "--pinentry-mode", "loopback", "--passphrase", "", "--quick-gen-key",
            nome, "ed25519", "sign", "never"])
    _rc, out, _e = sh([G.gpg_real, "--batch", "--with-colons", "--list-secret-keys"])
    fprs = []
    em_sec = False
    for linha in out.decode().splitlines():
        campos = linha.split(":")
        if campos[0] == "sec":
            em_sec = True
        elif campos[0] == "fpr" and em_sec:
            fprs.append(campos[9])
            em_sec = False
    afirma(len(fprs) == 2, "chaves descartáveis: %r" % fprs)
    G.fpr1, G.fpr2 = fprs


def declarados() -> List[str]:
    return [c.nome for c in CASOS] + ["C1", "C2", "C3", "C4", "C5", "ENSAIO-W5B"]


def roda_casos(so: Optional[Set[str]], w5b: str) -> None:
    por_nome = {c.nome: c for c in CASOS}
    h1_ex: List[Exec] = []
    for c in CASOS:
        if so and c.nome not in so and not (c.nome == "H1" and so & {"H1-ordem", "H1-env"}):
            continue
        if c.nome in ("H1-ordem", "H1-env"):
            continue
        inicio = time.monotonic()
        try:
            if c.tipo in ("E", "R"):
                executa_recusa(c)
            elif c.nome == "H1":
                ex = prepara(c)
                try:
                    ex.extra["commits_antes"] = contagem_commits(ex)
                    roda(ex)
                    confere_h1(ex)
                    G.saidas.append(("H1", "\n".join(ex.out) + ("\n" + ex.err.decode() if ex.err else "")))
                    G.executados.append("H1")
                    print("ok   H1 (%.1f s)" % (time.monotonic() - inicio), flush=True)
                    confere_h1_ordem(ex)
                    G.executados.append("H1-ordem")
                    print("ok   H1-ordem", flush=True)
                    confere_h1_env(ex)
                    G.executados.append("H1-env")
                    print("ok   H1-env", flush=True)
                    h1_ex.append(ex)
                finally:
                    limpa_caso(ex)
                continue
            else:
                afirma(c.nome not in ("F4", "F4b") or "H1" in G.executados, "F4/F4b antes do H1 verde")
                executa(c)
        except Falha as exc:
            raise Falha("%s: %s" % (c.nome, exc))
        G.executados.append(c.nome)
        print("ok   %s (%.1f s)" % (c.nome, time.monotonic() - inicio), flush=True)
        if G.verboso and G.saidas:
            print("     | " + G.saidas[-1][1].replace("\n", "\n     | "), flush=True)
    # mutantes
    for marcador, nome in MUTANTE_DE.items():
        if so and nome not in so:
            continue
        c = por_nome[nome]
        inicio = time.monotonic()
        if c.tipo in ("E", "R"):
            roda_mutante(c, marcador, lambda cc, sob: executa_recusa(cc, sob) and None)
        else:
            roda_mutante(c, marcador, lambda cc, sob: executa(cc, sob) and None)
        print("ok   mutante %s vermelho em %s (%.1f s)" % (marcador, nome, time.monotonic() - inicio), flush=True)
    for nome, fn in (("C1", caso_c1), ("C2", caso_c2), ("C3", caso_c3), ("C4", caso_c4), ("C5", caso_c5)):
        if so and nome not in so:
            continue
        try:
            fn()
        except Falha as exc:
            raise Falha("%s: %s" % (nome, exc))
        G.executados.append(nome)
        print("ok   %s" % nome, flush=True)
    if (not so or "ENSAIO-W5B" in so) and not G.sem_ensaio:
        caso_ensaio_w5b(w5b)
        G.executados.append("ENSAIO-W5B")
        print("ok   ENSAIO-W5B: %s" % G.ensaio, flush=True)  # type: ignore[attr-defined]


def limpa_tudo(h: str) -> None:
    for t in set(glob.glob("/tmp/sign-min.*")) - G.tmp_antes:
        real = os.path.realpath(t)
        if os.path.basename(real).startswith("sign-min.") and os.path.dirname(real) in ("/tmp", "/private/tmp"):
            gv = os.path.join(real, "gnupg-vazio")
            if os.path.isdir(gv):
                subprocess.run([os.path.join(os.path.dirname(G.gpg_real), "gpgconf"), "--homedir", gv, "--kill", "gpg-agent"], env=env_h(),
                               stdout=subprocess.DEVNULL, stderr=subprocess.DEVNULL)
            shutil.rmtree(real, ignore_errors=True)
    if G.gnupg and os.path.basename(G.gnupg).startswith("smg."):
        subprocess.run([os.path.join(os.path.dirname(G.gpg_real), "gpgconf"), "--homedir", G.gnupg, "--kill", "gpg-agent"], env=env_h(),
                       stdout=subprocess.DEVNULL, stderr=subprocess.DEVNULL)
        shutil.rmtree(G.gnupg, ignore_errors=True)
    if not G.manter and os.path.basename(h).startswith("sign-min-h."):
        shutil.rmtree(h, ignore_errors=True)


def main() -> int:
    ap = argparse.ArgumentParser()
    ap.add_argument("--base", default="/tmp")
    ap.add_argument("--w5b", default="")
    ap.add_argument("--so", default="")
    ap.add_argument("--manter", action="store_true")
    ap.add_argument("--verboso", action="store_true")
    ap.add_argument("--sem-ensaio", action="store_true")
    args = ap.parse_args()
    so = set(x for x in args.so.split(",") if x) or None
    G.sem_ensaio = args.sem_ensaio
    G.manter = args.manter
    G.verboso = args.verboso
    G.inicio = time.monotonic()
    G.tmp_antes = set(glob.glob("/tmp/sign-min.*"))
    G.h = os.path.realpath(tempfile.mkdtemp(prefix="sign-min-h.", dir=args.base))
    G.atual = os.path.join(G.h, "atual")
    G.home_h = os.path.join(G.h, "home-h")
    os.makedirs(G.home_h)
    G.marca_func = MARCA_FUNC_MODELO.replace("@ATUAL@", repr(G.atual))
    G.git_real = os.path.realpath(shutil.which("git", path=SIS_PATH) or "/usr/bin/git")
    gpg = shutil.which("gpg", path=os.environ.get("PATH", "")) or "/opt/homebrew/bin/gpg"
    G.gpg_real = os.path.realpath(gpg)
    G.py = shutil.which("python3", path=SIS_PATH) or "/usr/bin/python3"
    G.pyub = sh([G.py, "-I", "-c", "import site;print(site.getuserbase())"], env={"PATH": SIS_PATH,
                "HOME": os.environ.get("HOME", "/")})[1].decode().strip()
    try:
        if not so and not G.sem_ensaio:
            afirma(bool(args.w5b), "a corrida completa exige --w5b")
            st = git(["-C", REPO, "status", "--porcelain", "--", MOLDE], env=env_h({"HOME": G.home_h}))
            afirma(st == b"", "os arquivos do molde diferem do HEAD; a corrida completa roda sobre o HEAD")
        carrega_catalogo()
        prepara_gnupg()
        monta_base()
        def_e()
        def_r_p0a()
        def_r_cfg()
        def_r_arvore()
        def_r_dados()
        def_r_patch()
        def_r_sent()
        def_h()
        def_f()
        def_k()
        for c in CASOS:
            if c.marcador:
                afirma(c.marcador not in MUTANTE_DE, "marcador repetido %s" % c.marcador)
                MUTANTE_DE[c.marcador] = c.nome
        MUTANTE_DE["P0:cfg"] = "H2"
        MUTANTE_DE["B:tmp"] = "H2"
        nucleo = le(os.path.join(REPO, NUCLEO)).decode()
        entrada = le(os.path.join(REPO, ENTRADA)).decode()
        todos = sorted(set(re.findall(r"# (P0:[a-z]+)\n", nucleo)) | set(re.findall(r"# (B:[a-z]+)\n", nucleo)) |
                       set(re.findall(r"# (E:[a-z]+)\n", entrada)))
        afirma(todos == sorted(MUTANTE_DE), "marcadores sem caso: %s" % (set(todos) ^ set(MUTANTE_DE)))
        roda_casos(so, args.w5b)
        if so or G.sem_ensaio:
            print("corrida parcial (--so/--sem-ensaio): %d itens, %d mutantes vermelhos; sem EVIDÊNCIA" % (
                len(G.executados), len(G.mutantes_vermelhos)))
            return 2
        afirma(G.executados == [n for n in declarados() if n in G.executados] and
               sorted(G.executados) == sorted(declarados()), "casos executados ≠ declarados")
        afirma(sorted(G.mutantes_vermelhos) == sorted(MUTANTE_DE), "mutantes vermelhos ≠ marcadores")
        print("EVIDÊNCIA: %d casos, %d mutantes vermelhos; sha256 OWNER-SIGN.sh=%s sign_min.py=%s bloco-comum.md=%s" % (
            len(G.executados), len(G.mutantes_vermelhos), sha256f(os.path.join(REPO, ENTRADA)),
            sha256f(os.path.join(REPO, NUCLEO)), sha256f(os.path.join(REPO, BLOCO))), flush=True)
        return 0
    except Falha as exc:
        print("FALHA: %s" % exc, flush=True)
        return 1
    except Exception:  # noqa: BLE001
        traceback.print_exc()
        return 1
    finally:
        limpa_tudo(G.h)


if __name__ == "__main__":
    sys.exit(main())
