"""Núcleo do molde «SIGN mínimo» (sign-min) — PLAN-194, S363.

Chamado só pela entrada ``OWNER-SIGN.sh`` (``python3 -I -B``), com
``[--dry-run] <caminho do sign.tsv>``. Especificação: SPEC-v2 do molde
(S363, 2026-10-11). Regras de forma que o harness ``test-sign-min.py``
confere pela AST (caso C1):

- toda linha impressa passa por ``say()`` com uma chave de ``MENSAGENS``;
- todo subprocesso passa por ``run()``, com lista de argumentos e sem shell;
- ``git`` e ``gpg`` do próprio núcleo saem dos caminhos absolutos fixados
  em P0:tools;
- cada conferência do P0 é chamada por uma linha com o marcador único
  ``# P0:<id>`` (os mutantes do harness trocam essa linha por ``pass``).
"""
from __future__ import annotations

import signal

signal.signal(signal.SIGINT, signal.SIG_DFL)
signal.signal(signal.SIGPIPE, signal.SIG_DFL)

import errno  # noqa: E402
import hashlib  # noqa: E402
import importlib.util  # noqa: E402
import os  # noqa: E402
import re  # noqa: E402
import shutil  # noqa: E402
import stat  # noqa: E402
import subprocess  # noqa: E402
import sys  # noqa: E402
import tempfile  # noqa: E402
import time  # noqa: E402
from pathlib import Path  # noqa: E402
from typing import Dict, List, Optional, Set, Tuple  # noqa: E402

MENSAGENS: Dict[str, str] = {
    "FIXA": "Pare e chame o CEO.",
    "E-SRC": "SIGN-RECUSA: a entrada não foi chamada por um caminho com «/»",
    "E-PATH": "SIGN-RECUSA: o PATH tem entrada vazia ou que não começa com «/»",
    "E-PY": "SIGN-RECUSA: python3 ausente no PATH",
    "E-ARGS": "SIGN-RECUSA: o 1.º argumento não é --nucleo-sha256= com 64 hex minúsculos",
    "E-SHA": "SIGN-RECUSA: o núcleo ao lado da entrada não tem o sha256 informado",
    "P-ARGS": "SIGN-RECUSA: argumentos fora da gramática ({n} recebido(s))",
    "P-ENV": "SIGN-RECUSA: o ambiente recebido pelo núcleo tem {n} nome(s) fora da lista do molde",
    "P-CWD": "SIGN-RECUSA: o diretório atual não é a raiz do clone que contém o molde",
    "P-GITDIR": "SIGN-RECUSA: o .git deste diretório não é um diretório comum com git-dir e common-dir iguais a ele",
    "P-TTY": "SIGN-RECUSA: a entrada padrão não é um terminal",
    "P-GPGTTY": "SIGN-RECUSA: GPG_TTY difere do terminal da entrada padrão",
    "P-TOOL": "SIGN-RECUSA: ferramenta ausente no PATH: {nome}",
    "P-RC": "SIGN-RECUSA: {rotulo} saiu rc {r} numa leitura do P0",
    "P-HOOKS": "SIGN-RECUSA: core.hooksPath não é um valor único /dev/null vindo de .git/config (rc {r}, {n} linha(s))",
    "P-FSM": "SIGN-RECUSA: core.fsmonitor não é um valor único falso vindo de .git/config (rc {r}, {n} linha(s))",
    "P-IDENT": "SIGN-RECUSA: git var {var} saiu rc {r} com user.useConfigOnly=true",
    "P-LOCK": "SIGN-RECUSA: {n} arquivo(s) *.lock sob .git; o primeiro tem id {h}",
    "P-HEAD": "SIGN-RECUSA: HEAD não é refs/heads/main",
    "P-ORIGIN": "SIGN-RECUSA: HEAD ({a}) difere de refs/remotes/origin/main ({x})",
    "P-FILTER": "SIGN-RECUSA: {n} caminho(s) rastreado(s) com atributo filter; o primeiro tem id {h}",
    "P-STATUS": "SIGN-RECUSA: git status lista {n} entrada(s); a primeira tem id {h}",
    "P-BYTES": "SIGN-RECUSA: {n} caminho(s) rastreado(s) com modo fora de 100644/100755, ou com bytes ou bit de execução diferentes do índice; o primeiro tem id {h}",
    "P-DATA-AUS": "SIGN-RECUSA: dados {arg} ausentes no commit {a} como arquivo 100644",
    "P-DATA": "SIGN-RECUSA: dados {arg}, linha {n}: {motivo}",
    "P-MAT": "SIGN-RECUSA: {caminho} falta como arquivo no commit {a} ou na árvore com o patch",
    "P-PATCH": "SIGN-RECUSA: patch, {regra}: {caminho}",
    "P-APPLY": "SIGN-RECUSA: git apply --check saiu rc {r}",
    "P-SENT": "SIGN-RECUSA: sentinel, {regra}",
    "P-SCOPE": "SIGN-RECUSA: Scope do sentinel difere dos caminhos do patch ({n} diferença(s))",
    "P-ASC": "SIGN-RECUSA: o commit {a} contém {caminho}",
    "P-RAIL": "SIGN-RECUSA: registro do rail {caminho}, campo {campo}: ausente, repetido ou diferente",
    "P-ORACLE": "SIGN-RECUSA: o oráculo de canônicos saiu rc {r} ou fora do formato",
    "P-CANON": "SIGN-RECUSA: canônicos pelo oráculo diferem dos declarados ({n} diferença(s))",
    "P-KERN-RC": "SIGN-RECUSA: o predicado do kernel saiu rc {r} ou fora do formato",
    "P-KERN": "SIGN-RECUSA: {caminho} é caminho do kernel",
    "P-PYMOD": "SIGN-RECUSA: python3 não importa pytest e xdist (rc {r})",
    "P-ALLOW": "SIGN-RECUSA: o allowlist .claude/sentinel-signers.txt do commit {a} não carregou ou está vazio",
    "P-KEY": "SIGN-RECUSA: nenhuma chave secreta acessível ao gpg está no allowlist do commit {a}",
    "PASSO": "SIGN-PASSO: {k} de {n}: {rotulo}",
    "F-TMP": "SIGN-FATO: logs em {t}",
    "F-RC0": "SIGN-FATO: {rotulo} saiu rc 0 ({s} s)",
    "F-SUITE": "SIGN-FATO: passada {p}: {f} id(s) falharam; {r} passaram numa repetição isolada ({s} s)",
    "X-RC": "SIGN-FALHA: {rotulo} saiu rc {rc}; log em {arq}",
    "X-PYT": "SIGN-FALHA: {rotulo} saiu rc 0 sem resumo só de aprovados; log em {arq}",
    "X-COLETA": "SIGN-FALHA: passada {p}: {k} erro(s) de coleta; lista em {arq}",
    "X-SUITE": "SIGN-FALHA: passada {p}: {k} id(s) falharam também nas 3 repetições isoladas; lista em {arq}",
    "X-IDX": "SIGN-FALHA: o índice ou a árvore difere do esperado em {n} caminho(s); lista em {arq}",
    "X-CFG": "SIGN-FALHA: a configuração efetiva do git difere da lida no início",
    "X-REF": "SIGN-FALHA: HEAD, refs/heads/main ou refs/remotes/origin/main difere do lido no início",
    "X-TOOL": "SIGN-FALHA: {nome} resolve no PATH para outro caminho, ou o arquivo fixado no início tem outro sha256",
    "X-BG": "SIGN-FALHA: o grupo de processos de {rotulo} ainda tinha processo vivo 10 s depois de ele terminar; log em {arq}",
    "X-FILTER": "SIGN-FALHA: {n} caminho(s) rastreado(s) com atributo filter depois da bateria; lista em {arq}",
    "X-VER": "SIGN-FALHA: a assinatura não verificou; motivo em {arq}",
    "X-OS": "SIGN-FALHA: {rotulo}: erro do sistema {errno}",
    "X-EXC": "SIGN-FALHA: {rotulo}: exceção {tipo}",
    "X-COMMIT": "SIGN-FALHA: o commit {c} difere do esperado; detalhe em {arq}",
    "ENSAIO": "SIGN-ENSAIO: bateria e gates aprovados sobre a árvore com o patch; nesta execução não houve assinatura nem git commit; o patch fica aplicado neste clone",
    "OK": "SIGN-OK: commit {c} em refs/heads/main deste clone; pai único {a}; os {n} caminho(s) do patch com os blobs e modos das linhas index, o sentinel e a .asc com os bytes assinados; a .asc verifica com a chave {fpr}; autor e committer = a identidade conferida",
}

# --- conjuntos fixos dos placeholders «fixos» -------------------------------

PASSOS: List[str] = [
    "temporário", "aplica", "índice", "bateria hard", "suítes", "gates",
    "reconfere", "sentinel", "assinatura", "índice do sentinel", "commit",
    "conferência do commit",
]
GATES: List[Tuple[str, List[str]]] = [
    ("check-test-env-hygiene.py", ["python3", ".claude/scripts/check-test-env-hygiene.py"]),
    ("env-inventory-check.py", ["python3", ".claude/scripts/env-inventory-check.py", "--check"]),
    ("check-active-hooks-executable.py", ["python3", ".claude/scripts/check-active-hooks-executable.py"]),
    ("check-contamination.sh", ["bash", ".claude/scripts/check-contamination.sh"]),
    ("build-plugin.py", ["python3", "scripts/build-plugin.py", "--check"]),
    ("gen-command-skill-hook-map.py", ["python3", ".claude/scripts/gen-command-skill-hook-map.py", "--check"]),
    ("check-docs-freshness.py", ["python3", ".claude/scripts/check-docs-freshness.py", "--format=text"]),
    ("check-docs-drift.py", ["python3", ".claude/scripts/check-docs-drift.py"]),
    ("verify-counts.sh", ["bash", ".claude/scripts/local/verify-counts.sh", "--quiet", "--no-tests"]),
    ("check-claude-md-claims.py", ["python3", ".claude/scripts/check-claude-md-claims.py"]),
    ("check-ceremony-script.py", ["python3", ".claude/scripts/check-ceremony-script.py"]),
    ("check-staleness.py", ["python3", ".claude/scripts/check-staleness.py"]),
    ("validate-governance.sh", ["bash", ".claude/scripts/validate-governance.sh"]),
]
SUBCOMANDOS_GIT: List[str] = [
    "rev-parse", "symbolic-ref", "config", "var", "ls-files", "check-attr",
    "status", "cat-file", "ls-tree", "apply", "hash-object", "update-index",
    "diff-index", "diff-tree", "commit",
]
P0_IDS: List[str] = [
    "args", "env", "tools", "root", "tty", "cfg", "hooks", "fsm", "ident",
    "lock", "head", "filter", "status", "bytes", "data", "mat", "patch",
    "apply", "sent", "asc", "rail", "canon", "kernel", "pymod", "key",
]
PASSADAS = frozenset(["paralela", "serial"])
ROTULOS = frozenset(
    PASSOS
    + [nome for nome, _argv in GATES]
    + ["hard %d" % k for k in range(1, 41)]
    + ["git " + sub for sub in SUBCOMANDOS_GIT]
    + ["gpg", "verify_detached", "passada paralela", "passada serial"]
    + ["P0:" + i for i in P0_IDS]
)
MOTIVOS = frozenset([
    "byte fora do conjunto", "tamanho", "sem LF final", "chave fora da lista",
    "cardinalidade", "valor fora da gramática", "valor repetido",
])
REGRAS = frozenset([
    # regras do P0:patch
    "patch vazio", "linha fora de bloco", "cabeçalho diff --git",
    "caminho fora da gramática", "caminho repetido", "caminho proibido",
    "linha de cabeçalho fora das formas", "criação sobre caminho existente",
    "caminho ausente no commit", "pré-imagem diferente do commit",
    "modo diferente do commit", "criação de arquivo vazio",
    "linhas --- e +++", "linha de hunk fora da forma",
    # regras do P0:sent
    "não é UTF-8, ou tem CR ou NUL", "linha Dados", "linha Molde",
    "linha Patch-sha256", "linha Rail-Record-sha256", "linha Anchor-SHA",
    "linha Data", "token TO-FILL-BY-SIGN", "marcadores do bloco comum",
    "bloco comum diferente do molde", "seção Scope",
])
CAMPOS = frozenset([
    "Rail-Subject-sha256", "Rail-Sentinel-sha256", "Rail-Data-sha256", "Rail-Verdict",
])
NOMES = frozenset(["git", "gpg", "bash"])
VARS = frozenset(["GIT_AUTHOR_IDENT", "GIT_COMMITTER_IDENT"])
FIXOS: Dict[str, frozenset] = {
    "rotulo": ROTULOS, "motivo": MOTIVOS, "regra": REGRAS, "campo": CAMPOS,
    "nome": NOMES, "var": VARS, "p": PASSADAS,
}
MEDIDO = re.compile(r"^[A-Za-z0-9._/@:+=,?-]{0,200}$")
RE_PLACEHOLDER = re.compile(r"\{([a-z]+)\}")

# --- constantes do molde ----------------------------------------------------

L_ENV = frozenset([
    "PATH", "HOME", "USER", "LOGNAME", "SHELL", "TERM", "LANG", "PAGER",
    "GPG_TTY", "GNUPGHOME", "PYTHONUSERBASE", "PWD", "OLDPWD", "SHLVL",
])
SHIM_ENV = frozenset([
    "CPATH", "LIBRARY_PATH", "MANPATH", "SDKROOT", "LC_CTYPE",
    "__CF_USER_TEXT_ENCODING",
])
RE_ARG_DADOS = re.compile(r"^\.claude/plans/PLAN-[0-9]{3}/[a-z0-9][a-z0-9-]{0,31}/sign\.tsv$")
RE_CAMINHO = re.compile(r"^[A-Za-z0-9_.-]+(/[A-Za-z0-9_.-]+)*$")
RE_ARG = re.compile(r"^[A-Za-z0-9_.,:=+@%-]{1,255}$")
RE_NOME_PY = re.compile(r"^[A-Za-z_][A-Za-z0-9_]*$")
RE_HEX40 = re.compile(r"^[0-9a-f]{40}$")
RE_HEX64 = re.compile(r"^[0-9a-f]{64}$")
RE_RESUMO = re.compile(r"^[0-9]+ [a-z]+(, [0-9]+ [a-z]+)* in [0-9.]+s( \([0-9:]+\))?$")
MOLDE_DIR = ".claude/plans/PLAN-194/sign-min/"
MOLDE_ENTRADA = ".claude/plans/PLAN-194/sign-min/OWNER-SIGN.sh"
BLOCO = ".claude/plans/PLAN-194/sign-min/bloco-comum.md"
SIGNERS = ".claude/sentinel-signers.txt"
GPGV = ".claude/hooks/_lib/gpg_verify.py"
ORACULO = ".claude/hooks/check_canonical_edit.py"
KERNEL = ".claude/hooks/check_arbitration_kernel.py"
TOKEN = "TO-FILL-BY-SIGN"
ZERO40 = "0" * 40
ZERO_MODO = "000000"
MODOS = ("100644", "100755")
OPCOES_PYTEST = frozenset(["-q", "-rfE", "--tb=no", "--tb=short", "--strict-markers"])
VEREDITOS = frozenset(["APPROVE", "DECLARED-P2"])
MARCA_INICIO = "<!-- bloco-comum sign-min v1 -->"
MARCA_FIM = "<!-- fim do bloco-comum -->"
AUSENTE = "ausente"
ESPERA_GRUPO = 10.0
CODIGO_KERNEL = (
    "import importlib.util, os, sys\n"
    "from pathlib import Path\n"
    "spec = importlib.util.spec_from_file_location('sign_min_kernel', sys.argv[1])\n"
    "mod = importlib.util.module_from_spec(spec)\n"
    "spec.loader.exec_module(mod)\n"
    "raiz = Path(os.getcwd())\n"
    "for linha in sys.stdin.read().splitlines():\n"
    "    sys.stdout.write('%s\\t%d\\n' % (linha, 1 if mod._is_kernel_path(linha, raiz) else 0))\n"
)


class Estado:
    """Valores medidos no P0 e usados depois (tudo em memória)."""

    def __init__(self) -> None:
        self.rotulo = "P0:args"
        self.real = True
        self.arg = ""
        self.plan = ""
        self.pacote = ""
        self.patch_p = ""
        self.sent_p = ""
        self.asc_p = ""
        self.raiz = ""
        self.which: Dict[str, Optional[str]] = {}
        self.git_abs = ""
        self.gpg_abs = ""
        self.sha_git = ""
        self.sha_gpg = ""
        self.cfg_sha = ""
        self.ident = ""
        self.a = ""
        self.dados: Optional[Dict[str, object]] = None
        self.dados_blob = b""
        self.patch_blob = b""
        self.sent_blob = b""
        self.rail_blob = b""
        self.bloco_blob = b""
        self.arvore_a: Dict[str, Tuple[str, str, str]] = {}
        self.blocos: List[Dict[str, str]] = []
        self.caminhos: List[str] = []
        self.gpgv = None
        self.allow: Set[str] = set()
        self.fpr = ""
        self.t = ""
        self.git_log = ""
        self.env_filhos: Dict[str, str] = {}
        self.esperado: Set[Tuple[str, str, str, str, str, str]] = set()
        self.n_indice = 0


st = Estado()


# --- saída ------------------------------------------------------------------

def say(chave: str, **valores: object) -> None:
    """Única saída do núcleo: modelo do catálogo + valores conferidos."""
    modelo = MENSAGENS[chave]
    nomes = set(RE_PLACEHOLDER.findall(modelo))
    if nomes != set(valores):
        raise ValueError(chave)
    prontos: Dict[str, str] = {}
    for nome, valor in valores.items():
        texto = str(valor)
        conjunto = FIXOS.get(nome)
        if conjunto is not None:
            if texto not in conjunto:
                raise ValueError(nome)
        elif not MEDIDO.match(texto):
            raise ValueError(nome)
        prontos[nome] = texto
    linha = modelo.format(**prontos) + "\n"
    sys.stdout.buffer.write(linha.encode("utf-8"))
    sys.stdout.buffer.flush()


def fim() -> None:
    say("FIXA")
    sys.exit(1)


def limpa(texto: str) -> str:
    return re.sub(r"[^A-Za-z0-9._/@:+=,-]", "?", texto)[:200]


def ident_opaco(caminho: bytes) -> str:
    return hashlib.sha256(caminho).hexdigest()[:12]


def sha1_blob(dados: bytes) -> str:
    return hashlib.sha1(b"blob %d\0" % len(dados) + dados).hexdigest()


def sha256_arquivo(caminho: str) -> str:
    with open(caminho, "rb") as fh:
        return hashlib.sha256(fh.read()).hexdigest()


def rotulo(valor: str) -> None:
    st.rotulo = valor


# --- subprocessos -----------------------------------------------------------

def run(argv: List[str], entrada: Optional[bytes] = None, cwd: Optional[str] = None,
        env: Optional[Dict[str, str]] = None, log: Optional[str] = None,
        erro: Optional[str] = None, grupo: bool = False) -> Tuple[int, bytes, bool]:
    """Único ponto de subprocesso: lista de argumentos, sem shell.

    stdout: capturado (log None) ou gravado no arquivo ``log`` (com o
    stderr junto). stderr sem log: /dev/null ou o arquivo ``erro`` (append).
    Com ``grupo``, o filho roda em sessão própria e o retorno diz se o
    grupo dele ainda tinha processo vivo 10 s depois do fim.
    """
    fh_saida = None
    fh_erro = None
    try:
        if log is not None:
            fh_saida = open(log, "wb")
            saida_destino = fh_saida
            erro_destino = subprocess.STDOUT
        else:
            saida_destino = subprocess.PIPE
            if erro is not None:
                fh_erro = open(erro, "ab")
                erro_destino = fh_erro
            else:
                erro_destino = subprocess.DEVNULL
        proc = subprocess.Popen(
            argv,
            stdin=subprocess.DEVNULL if entrada is None else subprocess.PIPE,
            stdout=saida_destino,
            stderr=erro_destino,
            cwd=cwd if cwd is not None else st.raiz or None,
            env=env,
            start_new_session=grupo,
        )
        out, _err = proc.communicate(entrada)
        rc = proc.returncode
        vivo = False
        if grupo:
            vivo = grupo_vivo(proc.pid)
    finally:
        if fh_saida is not None:
            fh_saida.close()
        if fh_erro is not None:
            fh_erro.close()
    return rc, out or b"", vivo


def grupo_vivo(pgid: int) -> bool:
    limite = time.monotonic() + ESPERA_GRUPO
    while True:
        try:
            os.killpg(pgid, 0)
        except ProcessLookupError:
            return False
        except PermissionError:
            return True
        if time.monotonic() >= limite:
            return True
        time.sleep(0.1)


def env_git() -> Dict[str, str]:
    env = dict(os.environ)
    env["GIT_OPTIONAL_LOCKS"] = "0"
    env["GIT_NO_REPLACE_OBJECTS"] = "1"
    return env


def git(args: List[str], entrada: Optional[bytes] = None) -> Tuple[int, bytes]:
    erro = st.git_log or None
    rc, out, _vivo = run([st.git_abs] + args, entrada=entrada, env=env_git(), erro=erro)
    return rc, out


def git_ok(args: List[str], sub: str, entrada: Optional[bytes] = None) -> bytes:
    """git que tem de sair rc 0; no P0 recusa (P-RC), depois falha (X-RC)."""
    rc, out = git(args, entrada=entrada)
    if rc != 0:
        rot = "git " + sub
        if st.git_log:
            arq = st.git_log
            say("X-RC", rotulo=rot, rc=rc, arq=arq)
        else:
            say("P-RC", rotulo=rot, r=rc)
        fim()
    return out


# --- P0 ---------------------------------------------------------------------

def p0_args(argv: List[str]) -> None:
    rotulo("P0:args")
    n = len(argv)
    ok = (n == 1 and RE_ARG_DADOS.match(argv[0]) is not None) or (
        n == 2 and argv[0] == "--dry-run" and RE_ARG_DADOS.match(argv[1]) is not None)
    if not ok:
        say("P-ARGS", n=n)
        fim()


def le_args(argv: List[str]) -> None:
    st.real = argv[0] != "--dry-run"
    st.arg = argv[-1]
    partes = st.arg.split("/")
    st.plan = partes[2]
    st.pacote = partes[3]
    st.patch_p = "/".join(partes[:4]) + "/" + st.pacote + ".patch"
    st.sent_p = ".claude/plans/" + st.plan + "/" + st.pacote + "-approved.md"
    st.asc_p = st.sent_p + ".asc"


def p0_env() -> None:
    rotulo("P0:env")
    fora = [k for k in os.environ if k not in L_ENV and k not in SHIM_ENV]
    n = len(fora)
    if n:
        say("P-ENV", n=n)
        fim()


def le_tools() -> None:
    for nome in ("git", "gpg", "bash"):
        st.which[nome] = shutil.which(nome)


def p0_tools() -> None:
    rotulo("P0:tools")
    for nome in ("git", "gpg", "bash"):
        if not st.which.get(nome):
            say("P-TOOL", nome=nome)
            fim()
    st.git_abs = os.path.realpath(str(st.which["git"]))
    st.gpg_abs = os.path.realpath(str(st.which["gpg"]))
    st.sha_git = sha256_arquivo(st.git_abs)
    st.sha_gpg = sha256_arquivo(st.gpg_abs)


def p0_root() -> None:
    rotulo("P0:root")
    if os.path.realpath(os.getcwd()) != st.raiz:
        say("P-CWD")
        fim()
    top = git_ok(["rev-parse", "--show-toplevel"], "rev-parse").rstrip(b"\n")
    if os.path.realpath(os.fsdecode(top)) != st.raiz:
        say("P-CWD")
        fim()
    gd = git_ok(["rev-parse", "--git-dir"], "rev-parse")
    gc = git_ok(["rev-parse", "--git-common-dir"], "rev-parse")
    if gd != b".git\n" or gc != b".git\n" or os.path.islink(".git") or not os.path.isdir(".git"):
        say("P-GITDIR")
        fim()


def p0_tty() -> None:
    rotulo("P0:tty")
    if not st.real:
        return
    if not os.isatty(0):
        say("P-TTY")
        fim()
    if os.environ.get("GPG_TTY") != os.ttyname(0):
        say("P-GPGTTY")
        fim()


def retrato_cfg() -> str:
    out = git_ok(["config", "--list", "--show-origin", "--show-scope", "-z"], "config")
    return hashlib.sha256(out).hexdigest()


def p0_cfg() -> None:
    rotulo("P0:cfg")
    st.cfg_sha = retrato_cfg()


def p0_hooks() -> None:
    rotulo("P0:hooks")
    rc, out = git(["config", "--show-origin", "--get-all", "core.hooksPath"])
    if rc != 0 or out != b"file:.git/config\t/dev/null\n":
        n = out.count(b"\n")
        say("P-HOOKS", r=rc, n=n)
        fim()


def p0_fsm() -> None:
    rotulo("P0:fsm")
    rc, out = git(["config", "--show-origin", "--type=bool", "--get-all", "core.fsmonitor"])
    if rc != 0 or out != b"file:.git/config\tfalse\n":
        n = out.count(b"\n")
        say("P-FSM", r=rc, n=n)
        fim()


def p0_ident() -> None:
    rotulo("P0:ident")
    lidos = []
    for var in ("GIT_AUTHOR_IDENT", "GIT_COMMITTER_IDENT"):
        rc, out = git(["-c", "user.useConfigOnly=true", "var", var])
        if rc != 0:
            say("P-IDENT", var=var, r=rc)
            fim()
        lidos.append(out.decode("utf-8", "replace").rstrip("\n").rsplit(" ", 2)[0])
    st.ident = lidos[0]


def p0_lock() -> None:
    rotulo("P0:lock")
    achados: List[str] = []
    for base, _dirs, arquivos in os.walk(".git", followlinks=False):
        for nome in arquivos:
            if nome.endswith(".lock"):
                achados.append(os.path.join(base, nome))
    if achados:
        achados.sort()
        n = len(achados)
        h = ident_opaco(os.fsencode(achados[0]))
        say("P-LOCK", n=n, h=h)
        fim()


def p0_head() -> None:
    rotulo("P0:head")
    rc, out = git(["symbolic-ref", "--quiet", "HEAD"])
    if rc != 0 or out != b"refs/heads/main\n":
        say("P-HEAD")
        fim()
    a = git_ok(["rev-parse", "--verify", "--quiet", "HEAD^{commit}"], "rev-parse").decode().strip()
    rc, out = git(["rev-parse", "--verify", "--quiet", "refs/remotes/origin/main^{commit}"])
    x = out.decode("ascii", "replace").strip() if rc == 0 else AUSENTE
    if not RE_HEX40.match(a) or x != a:
        x = limpa(x)
        say("P-ORIGIN", a=a, x=x)
        fim()
    st.a = a


def caminhos_com_filtro() -> List[bytes]:
    lista = git_ok(["ls-files", "-z"], "ls-files")
    if not lista:
        return []
    out = git_ok(["check-attr", "-z", "--stdin", "filter"], "check-attr", entrada=lista)
    campos = out.split(b"\0")
    achados: List[bytes] = []
    for i in range(0, len(campos) - 2, 3):
        if campos[i + 2] != b"unspecified":
            achados.append(campos[i])
    return achados


def p0_filter() -> None:
    rotulo("P0:filter")
    achados = caminhos_com_filtro()
    if achados:
        n = len(achados)
        h = ident_opaco(achados[0])
        say("P-FILTER", n=n, h=h)
        fim()


def p0_status() -> None:
    rotulo("P0:status")
    out = git_ok(["status", "--porcelain=v1", "-z", "--no-renames",
                  "--untracked-files=all", "--ignored"], "status")
    entradas = [e for e in out.split(b"\0") if e]
    if entradas:
        n = len(entradas)
        h = ident_opaco(entradas[0][3:])
        say("P-STATUS", n=n, h=h)
        fim()


def confere_bytes() -> List[bytes]:
    """Árvore = índice por bytes; devolve os caminhos que divergem."""
    out = git_ok(["ls-files", "-s", "-z"], "ls-files")
    ruins: List[bytes] = []
    for entrada in out.split(b"\0"):
        if not entrada:
            continue
        meta, _tab, caminho = entrada.partition(b"\t")
        partes = meta.split(b" ")
        if len(partes) != 3 or partes[2] != b"0" or partes[0].decode() not in MODOS:
            ruins.append(caminho)
            continue
        try:
            info = os.lstat(caminho)
        except OSError:
            ruins.append(caminho)
            continue
        if not stat.S_ISREG(info.st_mode):
            ruins.append(caminho)
            continue
        if bool(info.st_mode & stat.S_IXUSR) != (partes[0] == b"100755"):
            ruins.append(caminho)
            continue
        with open(caminho, "rb") as fh:
            dados = fh.read()
        if sha1_blob(dados) != partes[1].decode():
            ruins.append(caminho)
    return ruins


def p0_bytes() -> None:
    rotulo("P0:bytes")
    ruins = confere_bytes()
    if ruins:
        n = len(ruins)
        h = ident_opaco(ruins[0])
        say("P-BYTES", n=n, h=h)
        fim()


def ls_tree(caminhos: List[str]) -> Dict[str, Tuple[str, str, str]]:
    if not caminhos:
        return {}
    out = git_ok(["ls-tree", "-z", st.a, "--"] + caminhos, "ls-tree")
    achados: Dict[str, Tuple[str, str, str]] = {}
    for entrada in out.split(b"\0"):
        if not entrada:
            continue
        meta, _tab, caminho = entrada.partition(b"\t")
        partes = meta.decode().split(" ")
        if len(partes) == 3:
            achados[os.fsdecode(caminho)] = (partes[0], partes[1], partes[2])
    return achados


def cat_blob(caminho: str) -> bytes:
    return git_ok(["cat-file", "blob", st.a + ":" + caminho], "cat-file")


def caminho_ok(valor: str) -> bool:
    if len(valor) > 255 or valor.startswith("-") or RE_CAMINHO.match(valor) is None:
        return False
    return all(c not in (".", "..", ".git") for c in valor.split("/"))


def argv_ok(campos: List[str]) -> bool:
    if len(campos) < 2:
        return False
    if campos[0] == "bash":
        if len(campos) == 3 and campos[1] == "-n":
            return caminho_ok(campos[2])
        return caminho_ok(campos[1]) and campos[1].endswith(".sh") and all(arg_ok(a) for a in campos[2:])
    if campos[0] != "python3":
        return False
    if campos[1:3] == ["-m", "pytest"]:
        resto = campos[3:]
        i = 0
        while i < len(resto):
            if resto[i] in OPCOES_PYTEST:
                i += 1
            elif resto[i] == "-p" and i + 1 < len(resto) and resto[i + 1] == "no:cacheprovider":
                i += 2
            else:
                break
        alvos = resto[i:]
        return bool(alvos) and all(alvo_ok(a) for a in alvos)
    return caminho_ok(campos[1]) and campos[1].endswith(".py") and all(arg_ok(a) for a in campos[2:])


def arg_ok(valor: str) -> bool:
    if caminho_ok(valor):
        return True
    return RE_ARG.match(valor) is not None and ".." not in valor


def alvo_ok(valor: str) -> bool:
    partes = valor.split("::")
    return caminho_ok(partes[0]) and all(RE_NOME_PY.match(p) for p in partes[1:])


def scripts_do_hard(campos: List[str]) -> List[str]:
    if campos[0] == "bash" and campos[1] == "-n":
        return [campos[2]]
    if campos[1:3] == ["-m", "pytest"]:
        return [a.split("::")[0] for a in campos[3:] if alvo_ok(a)]
    return [campos[1]]


def analisa_dados(blob: bytes) -> Tuple[int, str, Dict[str, object]]:
    """(0, "", dados) ou (linha, motivo, {})."""
    linhas = blob.split(b"\n")
    total = blob.count(b"\n") + (0 if blob.endswith(b"\n") else 1)
    permitido = set([9, 10]) | set(range(0x20, 0x7F))
    for n, linha in enumerate(linhas, 1):
        if any(b not in permitido for b in linha):
            return n, "byte fora do conjunto", {}
    if total > 200:
        return 201, "tamanho", {}
    if len(blob) > 8192:
        return blob[:8193].count(b"\n") + 1, "tamanho", {}
    if not blob.endswith(b"\n"):
        return total, "sem LF final", {}
    formato = False
    rail = ""
    canonical: List[str] = []
    hard: List[List[str]] = []
    for n, bruta in enumerate(linhas[:-1], 1):
        linha = bruta.decode("ascii")
        if linha == "" or linha.startswith("#"):
            continue
        campos = linha.split("\t")
        chave, valores = campos[0], campos[1:]
        if chave not in ("format", "rail", "canonical", "hard"):
            return n, "chave fora da lista", {}
        if not formato and chave != "format":
            return n, "cardinalidade", {}
        if formato and chave == "format":
            return n, "cardinalidade", {}
        if not valores or any(v == "" for v in valores):
            return n, "valor fora da gramática", {}
        if chave == "format":
            if valores != ["sign-min-1"]:
                return n, "valor fora da gramática", {}
            formato = True
        elif chave == "rail":
            if rail:
                return n, "cardinalidade", {}
            if len(valores) != 1 or not caminho_ok(valores[0]):
                return n, "valor fora da gramática", {}
            rail = valores[0]
        elif chave == "canonical":
            if len(valores) != 1 or not caminho_ok(valores[0]):
                return n, "valor fora da gramática", {}
            if valores[0] in canonical:
                return n, "valor repetido", {}
            canonical.append(valores[0])
        else:
            if len(hard) == 40:
                return n, "cardinalidade", {}
            if not argv_ok(valores):
                return n, "valor fora da gramática", {}
            hard.append(valores)
    if not formato or not rail or not hard:
        return total, "cardinalidade", {}
    return 0, "", {"rail": rail, "canonical": canonical, "hard": hard}


def p0_data() -> None:
    rotulo("P0:data")
    a = st.a
    arg = st.arg
    arv = ls_tree([st.arg])
    if arv.get(st.arg, ("", "", ""))[:2] != ("100644", "blob"):
        say("P-DATA-AUS", arg=arg, a=a)
        fim()
    st.dados_blob = cat_blob(st.arg)
    n, motivo, dados = analisa_dados(st.dados_blob)
    if n:
        say("P-DATA", arg=arg, n=n, motivo=motivo)
        fim()
    st.dados = dados


def resumo_patch(blob: bytes) -> Tuple[Set[str], Set[str]]:
    """Leitura tolerante: (criados, removidos) pelos cabeçalhos do patch."""
    criados: Set[str] = set()
    removidos: Set[str] = set()
    atual = ""
    for bruta in blob.split(b"\n"):
        linha = bruta.decode("utf-8", "replace")
        if linha.startswith("diff --git a/"):
            atual = linha[len("diff --git a/"):].split(" b/", 1)[0]
        elif linha.startswith("new file mode "):
            criados.add(atual)
        elif linha.startswith("deleted file mode "):
            removidos.add(atual)
    return criados, removidos


def p0_mat() -> None:
    rotulo("P0:mat")
    a = st.a
    dados = st.dados or {}
    fixos = [st.patch_p, st.sent_p, str(dados["rail"]), BLOCO, SIGNERS, GPGV, ORACULO, KERNEL]
    scripts: List[str] = []
    for campos in dados["hard"]:  # type: ignore[union-attr]
        scripts.extend(scripts_do_hard(campos))
    arv = ls_tree(sorted(set(fixos + scripts)))
    st.arvore_a.update(arv)
    for caminho in fixos:
        modo, tipo, _sha = arv.get(caminho, ("", "", ""))
        precisa = ("100644",) if caminho in (st.patch_p, st.sent_p) else MODOS
        if tipo != "blob" or modo not in precisa:
            caminho = limpa(caminho)
            say("P-MAT", caminho=caminho, a=a)
            fim()
    st.patch_blob = cat_blob(st.patch_p)
    criados, removidos = resumo_patch(st.patch_blob)
    for caminho in scripts:
        modo, tipo, _sha = arv.get(caminho, ("", "", ""))
        no_a = tipo == "blob" and modo in MODOS
        if (no_a and caminho in removidos) or (not no_a and caminho not in criados):
            caminho = limpa(caminho)
            say("P-MAT", caminho=caminho, a=a)
            fim()


def recusa_patch(regra: str, caminho_bruto: str) -> None:
    caminho = limpa(caminho_bruto)
    say("P-PATCH", regra=regra, caminho=caminho)
    fim()


def analisa_patch(blob: bytes) -> List[Dict[str, str]]:
    patch_p = st.patch_p
    if not blob or not blob.endswith(b"\n"):
        recusa_patch("patch vazio", patch_p)
    linhas = blob.decode("utf-8", "replace").split("\n")[:-1]
    blocos: List[List[str]] = []
    for linha in linhas:
        if linha.startswith("diff --git "):
            blocos.append([linha])
        elif not blocos:
            recusa_patch("linha fora de bloco", patch_p)
        else:
            blocos[-1].append(linha)
    if not blocos:
        recusa_patch("patch vazio", patch_p)
    vistos: List[str] = []
    resultado: List[Dict[str, str]] = []
    for bloco in blocos:
        resultado.append(analisa_bloco(bloco, vistos))
    return resultado


def analisa_bloco(bloco: List[str], vistos: List[str]) -> Dict[str, str]:
    cab = bloco[0]
    resto = cab[len("diff --git "):]
    if not resto.startswith("a/") or " b/" not in resto:
        recusa_patch("cabeçalho diff --git", resto)
    x, _sep, y = resto[2:].partition(" b/")
    if x != y:
        recusa_patch("cabeçalho diff --git", resto)
    if not caminho_ok(x):
        recusa_patch("caminho fora da gramática", x)
    if x in vistos:
        recusa_patch("caminho repetido", x)
    vistos.append(x)
    ultimo = x.split("/")[-1]
    if (x in (st.sent_p, st.asc_p, st.arg, str((st.dados or {}).get("rail")))
            or ultimo == ".gitattributes" or x.startswith(MOLDE_DIR)):
        recusa_patch("caminho proibido", x)
    i = 1
    status = "M"
    modo_novo = ""
    if i < len(bloco) and bloco[i].startswith("new file mode "):
        status = "A"
        modo_novo = bloco[i][len("new file mode "):]
        i += 1
    elif i < len(bloco) and bloco[i].startswith("deleted file mode "):
        status = "D"
        modo_novo = bloco[i][len("deleted file mode "):]
        i += 1
    if i >= len(bloco) or not bloco[i].startswith("index "):
        recusa_patch("linha de cabeçalho fora das formas", x)
    m = re.match(r"^index ([0-9a-f]{40})\.\.([0-9a-f]{40})( ([0-9]{6}))?$", bloco[i])
    if m is None:
        recusa_patch("linha de cabeçalho fora das formas", x)
    pre, pos, modo_idx = m.group(1), m.group(2), m.group(4) or ""
    i += 1
    no_a = st.arvore_a.get(x)
    if status == "A":
        if modo_novo not in MODOS or pre != ZERO40 or pos == ZERO40 or modo_idx:
            recusa_patch("linha de cabeçalho fora das formas", x)
        if no_a is not None:
            recusa_patch("criação sobre caminho existente", x)
        modo_pre, modo_pos = ZERO_MODO, modo_novo
        esperado = ("--- /dev/null", "+++ b/" + x)
    else:
        if no_a is None or no_a[1] != "blob":
            recusa_patch("caminho ausente no commit", x)
        if pre != no_a[2]:
            recusa_patch("pré-imagem diferente do commit", x)
        if status == "D":
            if pos != ZERO40 or modo_idx:
                recusa_patch("linha de cabeçalho fora das formas", x)
            if modo_novo != no_a[0]:
                recusa_patch("modo diferente do commit", x)
            modo_pre, modo_pos = no_a[0], ZERO_MODO
            esperado = ("--- a/" + x, "+++ /dev/null")
        else:
            if pos == ZERO40 or not modo_idx:
                recusa_patch("linha de cabeçalho fora das formas", x)
            if modo_idx != no_a[0]:
                recusa_patch("modo diferente do commit", x)
            modo_pre, modo_pos = no_a[0], no_a[0]
            esperado = ("--- a/" + x, "+++ b/" + x)
    if i >= len(bloco):
        recusa_patch("criação de arquivo vazio", x)
    if tuple(bloco[i:i + 2]) != esperado:
        if bloco[i].startswith("--- "):
            recusa_patch("linhas --- e +++", x)
        recusa_patch("linha de cabeçalho fora das formas", x)
    i += 2
    if i >= len(bloco) or not bloco[i].startswith("@@ "):
        recusa_patch("linha de hunk fora da forma", x)
    for linha in bloco[i:]:
        if not (linha.startswith("@@ ") or linha[:1] in (" ", "+", "-", "\\")):
            recusa_patch("linha de hunk fora da forma", x)
    return {"status": status, "modo_pre": modo_pre, "modo_pos": modo_pos,
            "pre": pre, "pos": pos, "caminho": x}


def p0_patch() -> None:
    rotulo("P0:patch")
    arv = ls_tree(sorted(set(resumo_caminhos(st.patch_blob))))
    st.arvore_a.update(arv)
    st.blocos = analisa_patch(st.patch_blob)
    st.caminhos = [b["caminho"] for b in st.blocos]
    st.esperado = set(
        (b["status"], b["modo_pre"], b["modo_pos"], b["pre"], b["pos"], b["caminho"])
        for b in st.blocos)


def resumo_caminhos(blob: bytes) -> List[str]:
    achados: List[str] = []
    for bruta in blob.split(b"\n"):
        linha = bruta.decode("utf-8", "replace")
        if linha.startswith("diff --git a/") and " b/" in linha:
            candidato = linha[len("diff --git a/"):].split(" b/", 1)[0]
            if caminho_ok(candidato):
                achados.append(candidato)
    return achados


def p0_apply() -> None:
    rotulo("P0:apply")
    rc, _out = git(["apply", "--check", "-"], entrada=st.patch_blob)
    if rc != 0:
        say("P-APPLY", r=rc)
        fim()


def recusa_sent(regra: str) -> None:
    say("P-SENT", regra=regra)
    fim()


def p0_sent() -> None:
    rotulo("P0:sent")
    blob = cat_blob(st.sent_p)
    st.sent_blob = blob
    st.bloco_blob = cat_blob(BLOCO)
    try:
        texto = blob.decode("utf-8")
    except UnicodeDecodeError:
        texto = "\r"
    if "\r" in texto or "\0" in texto:
        recusa_sent("não é UTF-8, ou tem CR ou NUL")
    linhas = texto.split("\n")
    for prefixo, valor, regra in (
            ("Dados:", "Dados: " + st.arg, "linha Dados"),
            ("Molde:", "Molde: " + MOLDE_ENTRADA, "linha Molde"),
            ("Patch-sha256:", "Patch-sha256: " + TOKEN, "linha Patch-sha256"),
            ("Rail-Record-sha256:", "Rail-Record-sha256: " + TOKEN, "linha Rail-Record-sha256"),
            ("Anchor-SHA:", "Anchor-SHA: " + TOKEN, "linha Anchor-SHA"),
            ("Data:", "Data: " + TOKEN, "linha Data")):
        achadas = [ln for ln in linhas if ln.startswith(prefixo)]
        if achadas != [valor]:
            recusa_sent(regra)
    if texto.count(TOKEN) != 4:
        recusa_sent("token TO-FILL-BY-SIGN")
    if linhas.count(MARCA_INICIO) != 1 or linhas.count(MARCA_FIM) != 1:
        recusa_sent("marcadores do bloco comum")
    ini = linhas.index(MARCA_INICIO)
    fim_i = linhas.index(MARCA_FIM)
    if fim_i < ini:
        recusa_sent("marcadores do bloco comum")
    miolo = "".join(ln + "\n" for ln in linhas[ini + 1:fim_i])
    if miolo.encode("utf-8") != st.bloco_blob:
        recusa_sent("bloco comum diferente do molde")
    if linhas.count("## Scope") != 1:
        recusa_sent("seção Scope")
    escopo: List[str] = []
    for ln in linhas[linhas.index("## Scope") + 1:]:
        if ln.startswith("## "):
            break
        if ln == "":
            continue
        m = re.match(r"^- `([^`]+)`$", ln)
        if m is None or not caminho_ok(m.group(1)) or m.group(1) in escopo:
            recusa_sent("seção Scope")
        escopo.append(m.group(1))
    n = len(set(escopo) ^ set(st.caminhos))
    if n:
        say("P-SCOPE", n=n)
        fim()


def p0_asc() -> None:
    rotulo("P0:asc")
    rc, _out = git(["cat-file", "-e", st.a + ":" + st.asc_p])
    if rc == 0:
        a = st.a
        caminho = st.asc_p
        say("P-ASC", a=a, caminho=caminho)
        fim()


def p0_rail() -> None:
    rotulo("P0:rail")
    dados = st.dados or {}
    rail_p = str(dados["rail"])
    st.rail_blob = cat_blob(rail_p)
    linhas = st.rail_blob.decode("utf-8", "replace").split("\n")
    esperados = {
        "Rail-Subject-sha256": hashlib.sha256(st.patch_blob).hexdigest(),
        "Rail-Sentinel-sha256": hashlib.sha256(st.sent_blob).hexdigest(),
        "Rail-Data-sha256": hashlib.sha256(st.dados_blob).hexdigest(),
    }
    for campo in ("Rail-Subject-sha256", "Rail-Sentinel-sha256", "Rail-Data-sha256", "Rail-Verdict"):
        achadas = [ln for ln in linhas if ln.startswith(campo + ":")]
        if campo == "Rail-Verdict":
            ok = len(achadas) == 1 and achadas[0][len(campo) + 2:] in VEREDITOS and \
                achadas[0][len(campo):len(campo) + 2] == ": "
        else:
            ok = achadas == [campo + ": " + esperados[campo]]
        if not ok:
            caminho = limpa(rail_p)
            say("P-RAIL", caminho=caminho, campo=campo)
            fim()


def le_flags(out: bytes, caminhos: List[str]) -> Optional[List[str]]:
    linhas = out.decode("utf-8", "replace").split("\n")
    if len(linhas) != len(caminhos) + 1 or linhas[-1] != "":
        return None
    marcados: List[str] = []
    for caminho, linha in zip(caminhos, linhas):
        if linha == caminho + "\t1":
            marcados.append(caminho)
        elif linha != caminho + "\t0":
            return None
    return marcados


def p0_canon() -> None:
    rotulo("P0:canon")
    entrada = "".join(c + "\n" for c in st.caminhos).encode()
    rc, out, _vivo = run(["python3", "-I", "-B", ORACULO, "--is-canonical", "-"], entrada=entrada)
    marcados = le_flags(out, st.caminhos) if rc == 0 else None
    if marcados is None:
        say("P-ORACLE", r=rc)
        fim()
    declarados = set((st.dados or {})["canonical"])  # type: ignore[arg-type]
    n = len(set(marcados or []) ^ declarados)
    if n:
        say("P-CANON", n=n)
        fim()


def p0_kernel() -> None:
    rotulo("P0:kernel")
    entrada = "".join(c + "\n" for c in st.caminhos).encode()
    rc, out, _vivo = run(["python3", "-I", "-B", "-c", CODIGO_KERNEL, KERNEL], entrada=entrada)
    marcados = le_flags(out, st.caminhos) if rc == 0 else None
    if marcados is None:
        say("P-KERN-RC", r=rc)
        fim()
    if marcados:
        caminho = limpa((marcados or [""])[0])
        say("P-KERN", caminho=caminho)
        fim()


def p0_pymod() -> None:
    rotulo("P0:pymod")
    rc, _out, _vivo = run(["python3", "-B", "-c", "import pytest, xdist"], cwd="/")
    if rc != 0:
        say("P-PYMOD", r=rc)
        fim()


def carrega_gpgv() -> None:
    sys.dont_write_bytecode = True
    spec = importlib.util.spec_from_file_location("sign_min_gpg_verify", os.path.join(st.raiz, GPGV))
    if spec is None or spec.loader is None:
        raise ImportError(GPGV)
    modulo = importlib.util.module_from_spec(spec)
    spec.loader.exec_module(modulo)
    st.gpgv = modulo


def p0_key() -> None:
    rotulo("P0:key")
    a = st.a
    carrega_gpgv()
    allow, err = st.gpgv.load_allowlist(Path(os.path.join(st.raiz, SIGNERS)))  # type: ignore[union-attr]
    if err is not None or not allow:
        say("P-ALLOW", a=a)
        fim()
    st.allow = set(allow)
    rc, out, _vivo = run([st.gpg_abs, "--batch", "--with-colons", "--list-secret-keys"],
                         erro=st.git_log or None)
    escolhida = ""
    em_sec = False
    for linha in out.decode("utf-8", "replace").split("\n"):
        campos = linha.split(":")
        if campos[0] == "sec":
            em_sec = True
        elif campos[0] == "fpr" and em_sec and len(campos) > 9:
            em_sec = False
            fpr = st.gpgv.normalise_fpr(campos[9])  # type: ignore[union-attr]
            if fpr and fpr in st.allow and not escolhida:
                escolhida = fpr
        elif campos[0] in ("pub", "ssb", "sub"):
            em_sec = False
    if rc != 0 or not escolhida:
        say("P-KEY", a=a)
        fim()
    st.fpr = escolhida


# --- passos -----------------------------------------------------------------

def passo(k: int) -> None:
    n = 12 if st.real else 7
    rot = PASSOS[k - 1]
    rotulo(rot)
    say("PASSO", k=k, n=n, rotulo=rot)


def arquivo_t(nome: str) -> str:
    return os.path.join(st.t, nome)


def grava_t(nome: str, dados: bytes) -> str:
    caminho = arquivo_t(nome)
    with open(caminho, "xb") as fh:
        fh.write(dados)
    return caminho


def le_diff_index() -> Set[Tuple[str, str, str, str, str, str]]:
    out = git_ok(["diff-index", "--cached", "-z", "--no-renames", st.a], "diff-index")
    return le_raw(out)


def le_raw(out: bytes) -> Set[Tuple[str, str, str, str, str, str]]:
    campos = out.split(b"\0")
    achados: Set[Tuple[str, str, str, str, str, str]] = set()
    i = 0
    while i + 1 < len(campos) and campos[i]:
        meta = campos[i].decode().lstrip(":").split(" ")
        caminho = os.fsdecode(campos[i + 1])
        if len(meta) == 5:
            achados.add((meta[4], meta[0], meta[1], meta[2], meta[3], caminho))
        else:
            achados.add(("?", "", "", "", "", caminho))
        i += 2
    return achados


def confere_indice(esperado: Set[Tuple[str, str, str, str, str, str]]) -> None:
    obtido = le_diff_index()
    difs = sorted(set(t[5] for t in (obtido ^ esperado)))
    difs += sorted(os.fsdecode(c) for c in confere_bytes())
    st.n_indice += 1
    if difs:
        n = len(difs)
        arq = grava_t("indice-%d.txt" % st.n_indice, "".join(d + "\n" for d in difs).encode("utf-8", "replace"))
        say("X-IDX", n=n, arq=arq)
        fim()


def roda_bateria(rot: str, argv: List[str], log: str) -> Tuple[int, float]:
    rotulo(rot)
    inicio = time.monotonic()
    rc, _out, vivo = run([*argv], env=st.env_filhos, log=log, grupo=True)
    if vivo:
        arq = log
        say("X-BG", rotulo=rot, arq=arq)
        fim()
    return rc, time.monotonic() - inicio


def so_aprovados(dados: bytes) -> bool:
    linhas = [ln for ln in dados.decode("utf-8", "replace").splitlines() if ln.strip()]
    if not linhas:
        return False
    ultima = linhas[-1].strip("= ")
    if RE_RESUMO.match(ultima) is None:
        return False
    palavras = re.findall(r"[0-9]+ ([a-z]+)", ultima.rsplit(" in ", 1)[0])
    return "passed" in palavras and all(p in ("passed", "warning", "warnings") for p in palavras)


def le_log(caminho: str) -> bytes:
    with open(caminho, "rb") as fh:
        return fh.read()


def passo_hard() -> None:
    hard = (st.dados or {})["hard"]
    for k, campos in enumerate(hard, 1):  # type: ignore[arg-type]
        rot = "hard %d" % k
        log = arquivo_t("hard-%d.log" % k)
        rc, dur = roda_bateria(rot, campos, log)
        arq = log
        if rc != 0:
            say("X-RC", rotulo=rot, rc=rc, arq=arq)
            fim()
        if campos[1:3] == ["-m", "pytest"] and not so_aprovados(le_log(log)):
            say("X-PYT", rotulo=rot, arq=arq)
            fim()
        s = "%.1f" % dur
        say("F-RC0", rotulo=rot, s=s)


def ids_de_falha(dados: bytes) -> Tuple[List[str], List[str]]:
    """(ids que falharam, erros de coleta), pela lógica do W4."""
    ids: List[str] = []
    coleta: List[str] = []
    for linha in dados.decode("utf-8", "replace").splitlines():
        if not (linha.startswith("FAILED ") or linha.startswith("ERROR ")):
            continue
        resto = linha.split(" ", 1)[1]
        cabeca = resto.split(" - ", 1)[0]
        if "::" not in cabeca:
            if linha.startswith("ERROR "):
                coleta.append(cabeca)
            continue
        ident = ""
        c = resto.find("::")
        b = resto.find("[", c)
        if b >= 0:
            for i in range(b, len(resto)):
                if resto[i] == "]" and (i == len(resto) - 1 or resto[i + 1:i + 4] == " - "):
                    ident = resto[:i + 1]
                    break
        if not ident:
            ident = cabeca
        if ident not in ids:
            ids.append(ident)
    return ids, coleta


def passada(nome: str, args: List[str]) -> None:
    rot = "passada " + nome
    log = arquivo_t("suite-%s.log" % nome)
    rc, dur = roda_bateria(rot, ["python3", "-m", "pytest"] + args, log)
    p = nome
    arq = log
    if rc not in (0, 1):
        say("X-RC", rotulo=rot, rc=rc, arq=arq)
        fim()
    ids, coleta = ids_de_falha(le_log(log))
    if coleta:
        k = len(coleta)
        arq = grava_t("coleta-%s.txt" % nome, "".join(c + "\n" for c in coleta).encode("utf-8", "replace"))
        say("X-COLETA", p=p, k=k, arq=arq)
        fim()
    if rc == 1 and not ids:
        say("X-RC", rotulo=rot, rc=rc, arq=arq)
        fim()
    grava_t("ids-%s.txt" % nome, "".join(i + "\n" for i in ids).encode("utf-8", "replace"))
    sobram: List[str] = []
    inicio = time.monotonic()
    for k, ident in enumerate(ids, 1):
        passou = False
        for t in range(1, 4):
            relog = arquivo_t("rerun-%s-%d-%d.log" % (nome, k, t))
            rrc, _d = roda_bateria(rot, ["python3", "-m", "pytest", ident, "-q", "-p", "no:cacheprovider",
                                         "--tb=short", "--strict-markers"], relog)
            if rrc == 0 and so_aprovados(le_log(relog)):
                passou = True
                break
        if not passou:
            sobram.append(ident)
    f = len(ids)
    r = f - len(sobram)
    s = "%.1f" % (dur + time.monotonic() - inicio)
    say("F-SUITE", p=p, f=f, r=r, s=s)
    if sobram:
        k = len(sobram)
        arq = grava_t("sobram-%s.txt" % nome, "".join(i + "\n" for i in sobram).encode("utf-8", "replace"))
        say("X-SUITE", p=p, k=k, arq=arq)
        fim()


def passo_gates() -> None:
    for k, (rot, argv) in enumerate(GATES, 1):
        log = arquivo_t("gate-%d.log" % k)
        rc, dur = roda_bateria(rot, argv, log)
        if rc != 0:
            arq = log
            say("X-RC", rotulo=rot, rc=rc, arq=arq)
            fim()
        s = "%.1f" % dur
        say("F-RC0", rotulo=rot, s=s)


def passo_reconfere() -> None:
    if retrato_cfg() != st.cfg_sha:
        say("X-CFG")
        fim()
    rc, out = git(["symbolic-ref", "--quiet", "HEAD"])
    ref_ok = rc == 0 and out == b"refs/heads/main\n"
    for ref in ("refs/heads/main", "refs/remotes/origin/main"):
        rc, out = git(["rev-parse", "--verify", "--quiet", ref + "^{commit}"])
        ref_ok = ref_ok and rc == 0 and out.decode("ascii", "replace").strip() == st.a
    if not ref_ok:
        say("X-REF")
        fim()
    achados = caminhos_com_filtro()
    if achados:
        n = len(achados)
        arq = grava_t("filtro.txt", b"".join(c + b"\n" for c in achados))
        say("X-FILTER", n=n, arq=arq)
        fim()
    confere_indice(st.esperado)
    for nome in ("git", "gpg"):
        fixado = st.git_abs if nome == "git" else st.gpg_abs
        sha = st.sha_git if nome == "git" else st.sha_gpg
        if shutil.which(nome) != st.which[nome] or sha256_arquivo(fixado) != sha:
            say("X-TOOL", nome=nome)
            fim()


def preenche_sentinel() -> bytes:
    valores = {
        "Patch-sha256": hashlib.sha256(st.patch_blob).hexdigest(),
        "Rail-Record-sha256": hashlib.sha256(st.rail_blob).hexdigest(),
        "Anchor-SHA": st.a,
        "Data": time.strftime("%Y-%m-%d", time.gmtime()),
    }
    saida: List[bytes] = []
    for linha in st.sent_blob.split(b"\n"):
        for campo, valor in valores.items():
            if linha == (campo + ": " + TOKEN).encode():
                linha = (campo + ": " + valor).encode()
        saida.append(linha)
    return b"\n".join(saida)


def grava_arvore(caminho: str, dados: bytes) -> None:
    fd = os.open(caminho, os.O_WRONLY | os.O_TRUNC | os.O_NOFOLLOW)
    with os.fdopen(fd, "wb") as fh:
        fh.write(dados)


def verifica(sent: str, asc: str, nome: str) -> Tuple[bool, str]:
    rotulo("verify_detached")
    ok, fpr, motivo = st.gpgv.verify_detached(  # type: ignore[union-attr]
        Path(sent), Path(asc), allowlist_fprs=st.allow, gpg_bin=st.gpg_abs)
    grava_t(nome, ("ok=%s fpr=%s motivo=%s\n" % (ok, fpr, motivo)).encode("utf-8", "replace"))
    return bool(ok), str(fpr)


def hash_object(dados: bytes) -> str:
    out = git_ok(["hash-object", "-w", "--no-filters", "--stdin"], "hash-object", entrada=dados)
    calculado = sha1_blob(dados)
    if out.decode("ascii", "replace").strip() != calculado:
        raise ValueError("hash-object")
    return calculado


def mensagem() -> bytes:
    sha_patch = hashlib.sha256(st.patch_blob).hexdigest()
    sha_rail = hashlib.sha256(st.rail_blob).hexdigest()
    return (
        "ceremony(%s %s): patch e sentinel assinado pelo molde sign-min\n"
        "\n"
        "Dados: %s\n"
        "Patch: %s (sha256 %s)\n"
        "Sentinel: %s\n"
        "Anchor-SHA: %s\n"
        "Rail-Record-sha256: %s\n"
        "Signer: %s\n"
        "\n"
        "Co-Authored-By: Claude Opus 5.5 <noreply@anthropic.com>\n"
        % (st.plan, st.pacote, st.arg, st.patch_p, sha_patch, st.sent_p, st.a, sha_rail, st.fpr)
    ).encode("utf-8")


def confere_commit(esperado: Set[Tuple[str, str, str, str, str, str]]) -> None:
    rc, out = git(["rev-parse", "--verify", "--quiet", "refs/heads/main^{commit}"])
    c = out.decode("ascii", "replace").strip() if rc == 0 else ""
    problemas: List[str] = []
    if not RE_HEX40.match(c):
        problemas.append("refs/heads/main ilegível")
        c = AUSENTE
    rc, out = git(["symbolic-ref", "--quiet", "HEAD"])
    if rc != 0 or out != b"refs/heads/main\n":
        problemas.append("HEAD não é refs/heads/main")
    if not problemas:
        rc, corpo = git(["cat-file", "commit", c])
        cab = corpo.split(b"\n\n", 1)[0].decode("utf-8", "replace").split("\n")
        pais = [ln[len("parent "):] for ln in cab if ln.startswith("parent ")]
        if rc != 0 or pais != [st.a]:
            problemas.append("pais diferentes de [Anchor-SHA]")
        for papel in ("author", "committer"):
            linhas = [ln[len(papel) + 1:].rsplit(" ", 2)[0] for ln in cab if ln.startswith(papel + " ")]
            if linhas != [st.ident]:
                problemas.append(papel + " diferente da identidade conferida")
        rc, out = git(["diff-tree", "-r", "-z", "--no-renames", st.a, c])
        if rc != 0 or le_raw(out) != esperado:
            problemas.append("diff-tree diferente do esperado")
        dirc = arquivo_t("commit")
        os.mkdir(dirc)
        rc1, s_c = git(["cat-file", "blob", c + ":" + st.sent_p])
        rc2, g_c = git(["cat-file", "blob", c + ":" + st.asc_p])
        if rc1 != 0 or rc2 != 0:
            problemas.append("sentinel ou .asc ilegível no commit")
        else:
            grava_t("commit/sentinel", s_c)
            grava_t("commit/asc", g_c)
            ok, fpr = verifica(arquivo_t("commit/sentinel"), arquivo_t("commit/asc"), "verify-commit.txt")
            if not ok or fpr != st.fpr:
                problemas.append("a .asc do commit não verifica com a mesma chave")
    if problemas:
        arq = grava_t("commit-detalhe.txt", "".join(p + "\n" for p in problemas).encode("utf-8"))
        say("X-COMMIT", c=c, arq=arq)
        fim()
    a = st.a
    n = len(st.caminhos)
    fpr = st.fpr
    say("OK", c=c, a=a, n=n, fpr=fpr)


def main() -> int:
    argv = sys.argv[1:]
    st.raiz = os.path.realpath(os.path.join(os.path.dirname(os.path.abspath(__file__)), "..", "..", "..", ".."))
    p0_args(argv)  # P0:args
    le_args(argv)
    p0_env()  # P0:env
    le_tools()
    p0_tools()  # P0:tools
    p0_root()  # P0:root
    p0_tty()  # P0:tty
    p0_cfg()  # P0:cfg
    p0_hooks()  # P0:hooks
    p0_fsm()  # P0:fsm
    p0_ident()  # P0:ident
    p0_lock()  # P0:lock
    p0_head()  # P0:head
    p0_filter()  # P0:filter
    p0_status()  # P0:status
    p0_bytes()  # P0:bytes
    p0_data()  # P0:data
    p0_mat()  # P0:mat
    p0_patch()  # P0:patch
    p0_apply()  # P0:apply
    p0_sent()  # P0:sent
    p0_asc()  # P0:asc
    p0_rail()  # P0:rail
    p0_canon()  # P0:canon
    p0_kernel()  # P0:kernel
    p0_pymod()  # P0:pymod
    p0_key()  # P0:key

    passo(1)
    st.t = os.path.realpath(tempfile.mkdtemp(prefix="sign-min.", dir="/tmp"))
    os.mkdir(arquivo_t("gnupg-vazio"), 0o700)
    st.git_log = arquivo_t("git.log")
    t = st.t
    say("F-TMP", t=t)
    st.env_filhos = {k: v for k, v in os.environ.items() if k != "GPG_TTY"}
    st.env_filhos["GNUPGHOME"] = arquivo_t("gnupg-vazio")

    passo(2)
    patch_t = grava_t("patch", st.patch_blob)
    rc, _out, _vivo = run([st.git_abs, "-c", "core.hooksPath=/dev/null", "-c", "core.fsmonitor=false",
                           "apply", "--index", "--", patch_t], env=env_git(), erro=arquivo_t("apply.err"))
    if rc != 0:
        arq = arquivo_t("apply.err")
        rot = "git apply"
        say("X-RC", rotulo=rot, rc=rc, arq=arq)
        fim()

    passo(3)
    confere_indice(st.esperado)

    passo(4)
    passo_hard()

    passo(5)
    passada("paralela", ["-n", "auto", "-m", "not serial", "--strict-markers", "-q", "-rfE",
                         "--tb=no", "-p", "no:cacheprovider"])
    passada("serial", ["-m", "serial", "--strict-markers", "-q", "-rfE", "--tb=no", "-p",
                       "no:cacheprovider"])

    passo(6)
    passo_gates()

    passo(7)
    passo_reconfere()
    if not st.real:
        say("ENSAIO")
        return 0

    passo(8)
    s_bytes = preenche_sentinel()
    grava_t("sentinel.filled", s_bytes)
    grava_arvore(st.sent_p, s_bytes)

    passo(9)
    rotulo("gpg")
    log_gpg = arquivo_t("gpg-sign.log")
    rc, _out, _vivo = run([st.gpg_abs, "--armor", "--detach-sign", "--local-user", st.fpr,
                           "--output", st.asc_p, "--", st.sent_p], log=log_gpg)
    if rc != 0:
        arq = log_gpg
        rot = "gpg"
        say("X-RC", rotulo=rot, rc=rc, arq=arq)
        fim()
    with open(st.sent_p, "rb") as fh:
        lido = fh.read()
    with open(st.asc_p, "rb") as fh:
        g_bytes = fh.read()
    os.mkdir(arquivo_t("assinado"))
    sent_t = grava_t("assinado/sentinel", s_bytes)
    asc_t = grava_t("assinado/asc", g_bytes)
    ok, fpr = verifica(sent_t, asc_t, "verify.txt")
    if not ok or fpr != st.fpr:
        arq = arquivo_t("verify.txt")
        say("X-VER", arq=arq)
        fim()
    if lido != s_bytes:
        n = 1
        arq = grava_t("indice-sentinel.txt", (st.sent_p + "\n").encode())
        say("X-IDX", n=n, arq=arq)
        fim()

    passo(10)
    blob_s = hash_object(s_bytes)
    blob_g = hash_object(g_bytes)
    git_ok(["-c", "core.hooksPath=/dev/null", "-c", "core.fsmonitor=false", "update-index",
            "--cacheinfo", "100644," + blob_s + "," + st.sent_p], "update-index")
    git_ok(["-c", "core.hooksPath=/dev/null", "-c", "core.fsmonitor=false", "update-index",
            "--add", "--cacheinfo", "100644," + blob_g + "," + st.asc_p], "update-index")
    pre_sent = st.arvore_a[st.sent_p][2]
    esperado2 = set(st.esperado)
    esperado2.add(("M", "100644", "100644", pre_sent, blob_s, st.sent_p))
    esperado2.add(("A", ZERO_MODO, "100644", ZERO40, blob_g, st.asc_p))
    confere_indice(esperado2)

    passo(11)
    msg = grava_t("mensagem.txt", mensagem())
    git_ok(["-c", "core.hooksPath=/dev/null", "-c", "core.fsmonitor=false", "-c", "commit.gpgsign=false",
            "-c", "core.attributesFile=/dev/null", "-c", "gc.auto=0", "-c", "maintenance.auto=false",
            "-c", "user.useConfigOnly=true", "commit", "--quiet", "--no-verify", "--no-gpg-sign",
            "--cleanup=verbatim", "-F", msg], "commit")

    passo(12)
    confere_commit(esperado2)
    return 0


def principal() -> int:
    try:
        return main()
    except OSError as exc:
        rot = st.rotulo
        nome = errno.errorcode.get(exc.errno or 0, "ESEMCODIGO")
        say("X-OS", rotulo=rot, errno=nome)
    except Exception as exc:  # noqa: BLE001 — nunca traceback (mostraria a fonte)
        rot = st.rotulo
        tipo = type(exc).__name__
        try:
            say("X-EXC", rotulo=rot, tipo=tipo)
        except Exception:  # noqa: BLE001
            pass
    say("FIXA")
    return 1


if __name__ == "__main__":
    sys.exit(principal())
