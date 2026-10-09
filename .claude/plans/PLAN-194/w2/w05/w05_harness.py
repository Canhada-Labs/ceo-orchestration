#!/usr/bin/env python3
"""W0.5 do PLAN-194 — instrumento PRE-REGISTRADO do controle vermelho da W2.

  python3 .claude/plans/PLAN-194/w2/w05/w05_harness.py run   --work DIR --arm head|poscura [opcoes]
  python3 .claude/plans/PLAN-194/w2/w05/w05_harness.py x7    --work DIR --leg C2|C1 --confirm-paid
  python3 .claude/plans/PLAN-194/w2/w05/w05_harness.py report --run-dir DIR/runs/<run>
  python3 .claude/plans/PLAN-194/w2/w05/w05_harness.py clean --work DIR

Implementa, SEM alterar, o pre-registro do LEDGER do PLAN-194 (secao «W0.5-pre-registro»,
gravada em 2026-10-02, S362, antes de qualquer execucao) e o item W0.5 do plano. O sha256
DESTE arquivo vai para a linha `W0.5-instrumento:` do LEDGER antes da 1.a execucao que
conta; execucao com outro sha nao conta. O mesmo arquivo roda o braco «no HEAD» e o braco
«pos-cura» (na sombra do U2-C): o codigo medido e o `.claude/hooks/` do `--repo` dado.

O que mede (nomes do LEDGER):
  C1..C8  2^3 = {spool proprio: nao/sim} x {state dir: vazio / 233.055 entradas}
          x {1 saida / 9 saidas concorrentes}
  X1      estoque so de travas (150.000), 9 saidas concorrentes COM conteudo
  X2      entrega de decisao: guard BLOCK de import tardio, 9 concorrentes, dir cheio e um
          portador externo da trava canonica (o driver segura o flock)
  X3      encerramento do interpretador depois do atexit (margem) — de todas as saidas
  X4      inicio do wrapper (`_python-hook.sh`, que mantem o PID por exec) ate a ancora —
          de todas as saidas; a idade do processo lida do KERNEL pelo driver (sysctl)
  X5      drain oportunista ANTES da decisao (150.000 travas, 9 concorrentes): intervalo
          «decisao tomada -> stdout escrito». Gatilho: a CONTAGEM (DRAIN_TRIGGER_SIZE linhas
          no spool proprio); o de idade nao dispara logo depois de um append (mtime renovado)
  X6      vivacidade da perna 3 sob rajada: spools orfaos com conteudo e `.draining.*`
          depois da carga e depois de cada um dos N_X6 emissores seguintes (K_MAX = 100)
  X7      calibracao com o harness REAL: subcomando `x7`, no maximo 2 chamadas `claude -p`
          (freio Q1), contador persistido; sem X7, S1 e prova contra um MODELO do harness

Modelo do harness no driver (pre-registro, AMEND-4 §4.2): o processo que passa do timeout
e morto (SIGKILL) e a decisao e DESCARTADA. Timeout = HOOK_TIMEOUT_S = 3,0 s, o menor
timeout de hook registrado (regra de parada do LEDGER; AMEND-4 §4.2, T_min). «timeout»
numa celula = saida morta pelo driver; as linhas `drain canonical lock timeout` vao a parte.

Guard sintetico (gravado numa arvore DESCARTAVEL, molde do check_canonical_edit.py): le o
evento do stdin, escreve a decisao BLOCK sem flush e so ENTAO importa o audit_emit (import
tardio); «spool proprio = sim» emite um `veto_triggered` depois da decisao. O espiao do
`spool_writer.drain_now` repassa a chamada intacta e so registra o DrainStats (inclusive
`exit_deadline_skip`, que no HEAD nao existe: «NA»). O espiao depende do contrato do
AMEND-4 §4.2 (o prazo entra por parametro nomeado de `drain_now`): uma saida sem chamada
ao `drain_now` conta como caminho rapido. Guard e driver usam o MESMO relogio
(CLOCK_UPTIME_RAW no macOS), porque o monotonic do CPython 3.9 e relativo ao processo.

A arvore: `--work` (descartavel). O `.claude/hooks/_lib/` e o `_python-hook.sh` do `--repo`
sao COPIADOS byte a byte para `<run>/mirror/.claude/hooks/` (sha256 conferido arquivo a
arquivo; divergencia aborta), com o guard ao lado: o processo medido e um processo de HOOK
no sentido do AMEND-4 §4.2 (`sys.argv[0]` dentro de `_HOOKS_DIR`). Toda a familia do log
(log, trava, erros, chave HMAC, state dir) fica em `CEO_AUDIT_LOG_DIR` da celula; HOME e
TMPDIR dos filhos sao descartaveis. NUNCA o state dir vivo nem a chave real.

v2 (pos-cura; LEDGER «W0.5-pre-registro-pos-cura», 2026-10-09): (ii) decisao descartada =
morta pelo driver OU `lat_exit_ms` > timeout; (iii) a regra condicional da X5 e avaliada pelo
MAXIMO de «decisao -> stdout»; o summary ganha a ultima marca de cada morte, maximo e 2.o da
latencia, saidas acima do timeout e o maximo da X5; o `x7` guarda os drains das marcas. O v1
(sha256 27473c1d...) mediu o HEAD; nada mais muda.

Estatistica (pre-registro): percentil por posto mais proximo; p95 so com N >= 100 (senao
p90). p_hat = descartadas/N em X2; N do braco seguinte com 3/N <= p_hat/10. Nada disso vira
assercao de tempo em teste. Stdlib only, Python >= 3.9.
"""

from __future__ import annotations

import argparse
import ctypes
import ctypes.util
import datetime as _dt
import errno
import fcntl
import hashlib
import json
import math
import os
import platform
import re
import shlex
import shutil
import signal
import struct
import subprocess
import sys
import threading
import time
from pathlib import Path
from typing import Any, Dict, List, Optional, Tuple

# ---------------------------------------------------------------------------
# Constantes PRE-REGISTRADAS (LEDGER «W0.5-pre-registro»; plano, item W0.5;
# AMEND-4 §4.2 e §6.4). Mudar qualquer uma muda o sha do instrumento.
# ---------------------------------------------------------------------------

FULL_ENTRIES = 233_055          # LEDGER: 233.055 entradas no state dir vivo (2026-10-02)
FULL_PIDS = FULL_ENTRIES // 3   # 3 por PID emissor: 2 travas + journal de 0 byte (AMEND-4 §2)
LOCKS_ENTRIES = 150_000         # «~150 mil» travas: o regime PERMANENTE sob T1 (X1, X5)
LOCKS_PIDS = LOCKS_ENTRIES // 2
PID_BASE = 1000                 # PIDs sinteticos [PID_BASE, PID_BASE + n)
CONC = 9                        # «>= 9 concorrentes» (lane H-02)
HOOK_TIMEOUT_S = 3.0            # T_min = menor timeout de hook registrado (o driver mata)
EXIT_MARGIN_S = 1.0             # valor inicial (LEDGER «Valores iniciais»)
DEADLINE_S = 2.0                # prazo inicial = T_min - margem
STOP_MARGIN_S = 3.0             # parada: margem medida em X3 >= 3 s => a W2 PARA
MARGIN_P99_FACTOR = 1.5         # regra: margem >= p99 medido x 1,5
N_SINGLE = 100                  # saidas por celula de 1 saida (p95 exige N >= 100)
N_BURSTS = 12                   # rajadas por celula concorrente: 12 x 9 = 108 >= 100
N_X6 = 10                       # emissores seguintes na X6
DF_FLOOR_GB = 60.0              # piso de `df` (LEDGER, Arvore)
X7_MAX_CALLS = 2                # freio Q1
X7_EXIT_SLEEP_S = 6.0           # X7 C1: atraso da SAIDA alem do timeout registrado
POST_KILL_GRACE_S = 15.0        # teto de espera depois do SIGKILL (sanidade, nao metrica)

CELL_ORDER = ("C1", "C2", "C5", "C6", "C3", "C4", "C7", "C8", "X2", "X6", "X1", "X5")

# cell -> (arvore, concorrencia, modo do guard)
CELLS: Dict[str, Tuple[str, int, str]] = {
    "C1": ("empty", 1, "nospool"), "C2": ("empty", CONC, "nospool"),
    "C3": ("full", 1, "nospool"), "C4": ("full", CONC, "nospool"),
    "C5": ("empty", 1, "spool"), "C6": ("empty", CONC, "spool"),
    "C7": ("full", 1, "spool"), "C8": ("full", CONC, "spool"),
    "X1": ("locks", CONC, "spool"), "X2": ("full", CONC, "spool"),
    "X5": ("locks", CONC, "early"), "X6": ("full", 1, "spool"),
}

# AMEND-4 §4.8, byte a byte; so fullmatch com re.ASCII.
RE_SPOOL_LOCK = re.compile(r"audit-spool\.([1-9][0-9]{0,9})\.jsonl\.lock", re.ASCII)
RE_JOURNAL = re.compile(r"audit-pending\.([1-9][0-9]{0,9})\.journal", re.ASCII)
RE_JOURNAL_LOCK = re.compile(r"audit-pending\.([1-9][0-9]{0,9})\.journal\.lock", re.ASCII)
RE_DRAINING = re.compile(r"audit-spool\.([1-9][0-9]{0,9})\.draining\.([0-9a-f]{8})", re.ASCII)
RE_ACTIVE_SPOOL = re.compile(r"audit-spool\.([1-9][0-9]{0,9})\.jsonl", re.ASCII)

ERR_CLASSES = (
    ("drain_canonical_lock_timeout", "drain canonical lock timeout"),
    ("starved_opportunistic", "drain canonical lock STARVED: own spool"),
    ("starved_exit", "STARVED (exit)"),
    ("phase2_spool_flock_timeout", "phase2 spool flock timeout"),
    ("spool_flock_timeout", "spool flock timeout pid="),
    ("journal_flock_timeout", "journal flock timeout pid="),
    ("spool_append_failed", "spool append failed"),
    ("journal_flush_failed", "journal flush failed"),
    ("journal_compact_failed", "journal compact failed"),
    ("drain_now_unexpected", "drain_now unexpected"),
    ("would_log", "would-log="),
)

WRAPPER_CANDIDATES = ("python3.13", "python3.12", "python3.11", "python3.10", "python3.9", "python3")
OWNED = ".w05-owned"
KEY_FILES = ("_lib/spool_writer.py", "_lib/filelock.py", "_lib/audit_emit.py",
             "_lib/audit_hmac.py", "_lib/runtime_paths.py", "_python-hook.sh")

# ---------------------------------------------------------------------------
# Guard sintetico (texto gravado na arvore descartavel)
# ---------------------------------------------------------------------------

GUARD_SRC = r'''# w05_guard.py - guard SINTETICO da W0.5 (PLAN-194). Gravado por w05_harness.py numa
# arvore DESCARTAVEL; nao e hook do repositorio. Molde do check_canonical_edit.py: decide
# BLOCK, escreve a decisao SEM flush e so ENTAO importa o audit_emit (import tardio).
import os
import sys
import time

# Relogio COMUM a guard e driver (o monotonic do CPython 3.9 no macOS e relativo ao
# processo): CLOCK_UPTIME_RAW = mach_absolute_time; fora do macOS, CLOCK_MONOTONIC.
_CLK = getattr(time, "CLOCK_UPTIME_RAW", None) or time.CLOCK_MONOTONIC


def _clk():
    return time.clock_gettime_ns(_CLK)


_T_START = _clk()
_MFD = None
_MP = os.environ.get("W05_MARK", "")
if _MP:
    try:
        _MFD = os.open(_MP, os.O_WRONLY | os.O_CREAT | os.O_APPEND, 0o600)
    except OSError:
        _MFD = None


def _mark(name, extra=""):
    if _MFD is None:
        return
    try:
        os.write(_MFD, ("%s %d %s\n" % (name, _clk(), extra)).encode("utf-8", "replace"))
    except OSError:
        pass


_mark("start", str(_T_START))
import atexit  # noqa: E402
import json  # noqa: E402

atexit.register(_mark, "atexit_last")  # 1.o registrado => roda por ULTIMO
_mark("interp", json.dumps({"exe": sys.executable, "ver": sys.version.split()[0],
                            "argv0": sys.argv[0]}, separators=(",", ":")))

try:
    _RAW = sys.stdin.read()
    _EVT = json.loads(_RAW) if _RAW.strip() else {}
except Exception:
    _EVT = {}
if not isinstance(_EVT, dict):
    _EVT = {}

_HOOKS = os.path.dirname(os.path.abspath(__file__))
if _HOOKS not in sys.path:
    sys.path.insert(0, _HOOKS)

_DECISION = json.dumps({"decision": "block", "reason": "W0.5 guard sintetico (import tardio)"})
_EMIT = os.environ.get("W05_EMIT") == "1"
_EARLY = os.environ.get("W05_EARLY") == "1"
_FLUSH = os.environ.get("W05_FLUSH") == "1"
_EXIT_SLEEP = float(os.environ.get("W05_EXIT_SLEEP", "0") or 0)


def _spy():
    from _lib import spool_writer as _sw
    _orig = _sw.drain_now

    def _drain_spy(*a, **k):
        t0 = _clk()
        st = _orig(*a, **k)
        info = {"t0": t0, "force": bool(k.get("force", False)), "kw": sorted(k.keys()),
                "ok": getattr(st, "ok", None), "error": getattr(st, "error", None),
                "contended": getattr(st, "contended_skip", None),
                "eds": getattr(st, "exit_deadline_skip", "NA"),
                "appended": getattr(st, "appended", None)}
        _mark("drain", json.dumps(info, separators=(",", ":"), default=str))
        return st

    _sw.drain_now = _drain_spy
    return _sw


def _emit(ae, code):
    try:
        ae.emit_veto_triggered(hook="w05_guard", reason_code=code,
                               reason_preview="W0.5 guard sintetico",
                               blocked_tool=str(_EVT.get("tool_name", ""))[:64])
        _mark("emitted", code)
    except Exception as e:
        _mark("emit_error", type(e).__name__)


if _EARLY:
    from _lib import audit_emit as _ae
    _mark("imported")
    _sw = _spy()
    atexit.register(_mark, "atexit_first")
    # Gatilho ALCANCAVEL do drain oportunista: a contagem (DRAIN_TRIGGER_SIZE linhas no
    # spool proprio). O de idade nao dispara logo depois de um append, que renova o mtime.
    _n_pre = max(0, int(getattr(_sw, "DRAIN_TRIGGER_SIZE", 100)) - 1)
    for _i in range(_n_pre):
        _emit(_ae, "w05_early_pre")
    _mark("decision_taken")
    _emit(_ae, "w05_early_veto")
    sys.stdout.write(_DECISION + "\n")
    _mark("stdout_written")
else:
    sys.stdout.write(_DECISION + "\n")
    _mark("decision")
    if _FLUSH:
        sys.stdout.flush()
        _mark("flushed")
    from _lib import audit_emit as _ae
    _mark("imported")
    _spy()
    if _EXIT_SLEEP > 0:
        def _exit_sleep():
            _mark("exit_sleep_begin")
            time.sleep(_EXIT_SLEEP)
        atexit.register(_exit_sleep)
    atexit.register(_mark, "atexit_first")  # ultimo registrado => roda PRIMEIRO
    if _EMIT:
        _emit(_ae, "w05_late")
_mark("main_end")
'''

# ---------------------------------------------------------------------------
# Utilidades
# ---------------------------------------------------------------------------


# Relogio COMUM a driver e guard (o mesmo trecho esta no GUARD_SRC): o monotonic do
# CPython 3.9 no macOS e relativo ao processo e nao se compara com o de outro interpretador.
_CLK = getattr(time, "CLOCK_UPTIME_RAW", None) or time.CLOCK_MONOTONIC


def _clk() -> int:
    return time.clock_gettime_ns(_CLK)


def _now_utc() -> str:
    return _dt.datetime.now(_dt.timezone.utc).strftime("%Y-%m-%dT%H:%M:%SZ")


def _sha256_file(p: Path) -> str:
    h = hashlib.sha256()
    with p.open("rb") as f:
        for chunk in iter(lambda: f.read(1 << 20), b""):
            h.update(chunk)
    return h.hexdigest()


def _tree_digest(root: Path) -> str:
    h = hashlib.sha256()
    for p in sorted(root.rglob("*")):
        if "__pycache__" in p.parts or p.suffix == ".pyc" or not p.is_file():
            continue
        h.update(str(p.relative_to(root)).encode() + b"\0" + _sha256_file(p).encode() + b"\n")
    return h.hexdigest()


def _die(msg: str, code: int = 2) -> None:
    sys.stderr.write("w05_harness: ERRO: %s\n" % msg)
    raise SystemExit(code)


def _df_free_gb(p: Path) -> float:
    return shutil.disk_usage(str(p)).free / 1e9


def _df_guard(p: Path, where: str) -> float:
    free = _df_free_gb(p)
    if free < DF_FLOOR_GB:
        _die("piso de df violado em %s: %.1f GB livres < %.0f GB" % (where, free, DF_FLOOR_GB))
    return free


def _check_work(work: Path, repo: Path) -> Path:
    work = work.expanduser().resolve()
    live = (Path.home() / ".claude").resolve()
    for bad in (live, repo.resolve()):
        if work == bad or bad in work.parents:
            _die("--work nao pode ficar dentro de %s" % bad)
    if work == Path("/") or len(work.parts) < 4:
        _die("--work raso demais: %s" % work)
    work.mkdir(parents=True, exist_ok=True)
    return work


def _owned_dir(p: Path, work: Path) -> Path:
    p.mkdir(parents=True, exist_ok=False)
    (p / OWNED).write_text("w05_harness %s\n" % _now_utc())
    return p


def _confined_rmtree(p: Path, work: Path) -> None:
    rp = p.resolve()
    if work not in rp.parents or not (rp / OWNED).is_file():
        _die("limpeza recusada (fora do --work ou sem marcador): %s" % rp)
    shutil.rmtree(str(rp))


def _pct(vals: List[float], p: float) -> Optional[float]:
    if not vals:
        return None
    s = sorted(vals)
    k = max(1, int(math.ceil(p * len(s))))
    return s[k - 1]


def _tail_p(n: int) -> float:
    return 0.95 if n >= 100 else 0.90


# ---------------------------------------------------------------------------
# Kernel: inicio do processo (macOS sysctl KERN_PROC_PID; p_starttime no offset 0)
# ---------------------------------------------------------------------------

_LIBC = None


def _kern_start_wall_ns(pid: int) -> Optional[int]:
    global _LIBC
    if sys.platform != "darwin":
        return None
    try:
        if _LIBC is None:
            _LIBC = ctypes.CDLL(ctypes.util.find_library("c"), use_errno=True)
        mib = (ctypes.c_int * 4)(1, 14, 1, int(pid))  # CTL_KERN, KERN_PROC, KERN_PROC_PID
        buf = ctypes.create_string_buffer(1024)
        size = ctypes.c_size_t(1024)
        rc = _LIBC.sysctl(mib, 4, buf, ctypes.byref(size), None, ctypes.c_size_t(0))
        if rc != 0 or size.value < 16:
            return None
        sec, usec = struct.unpack_from("qi", buf.raw, 0)
        if sec <= 0 or not (0 <= usec < 1_000_000):
            return None
        return sec * 1_000_000_000 + usec * 1000
    except Exception:
        return None


# ---------------------------------------------------------------------------
# Arvore: mirror do codigo medido + state dirs sinteticos
# ---------------------------------------------------------------------------


def build_mirror(repo: Path, dest: Path) -> Dict[str, Any]:
    src_hooks = repo / ".claude" / "hooks"
    for rel in KEY_FILES:
        if not (src_hooks / rel).is_file():
            _die("arquivo do codigo medido ausente: %s" % (src_hooks / rel))
    dst_hooks = dest / ".claude" / "hooks"
    dst_hooks.mkdir(parents=True)
    shutil.copytree(str(src_hooks / "_lib"), str(dst_hooks / "_lib"),
                    ignore=shutil.ignore_patterns("__pycache__", "*.pyc"))
    shutil.copy2(str(src_hooks / "_python-hook.sh"), str(dst_hooks / "_python-hook.sh"))
    for rel in (".claude/settings.json", ".claude/.framework-version"):
        if (repo / rel).is_file():
            shutil.copy2(str(repo / rel), str(dest / rel))
    (dst_hooks / "w05_guard.py").write_text(GUARD_SRC, encoding="utf-8")
    shas: Dict[str, Dict[str, str]] = {}
    for rel in KEY_FILES:
        a, b = _sha256_file(src_hooks / rel), _sha256_file(dst_hooks / rel)
        if a != b:
            _die("copia divergente do codigo medido: %s" % rel)
        shas[rel] = {"sha256": a}
    lib_src, lib_dst = _tree_digest(src_hooks / "_lib"), _tree_digest(dst_hooks / "_lib")
    if lib_src != lib_dst:
        _die("arvore _lib copiada diverge da fonte")
    return {"mirror": str(dest), "key_files": shas, "lib_tree_digest": lib_src,
            "guard_sha256": hashlib.sha256(GUARD_SRC.encode("utf-8")).hexdigest()}


def build_state(audit_dir: Path, kind: str, dev: bool) -> Dict[str, Any]:
    audit_dir.mkdir(parents=True, mode=0o700)
    os.chmod(str(audit_dir), 0o700)
    state = audit_dir / "state"
    state.mkdir(mode=0o700)
    os.chmod(str(state), 0o700)
    if kind == "empty":
        return {"kind": kind, "entries": 0}
    t0 = time.monotonic()
    if kind == "full":
        npids = FULL_PIDS if not dev else 1000
        names = ("audit-spool.%d.jsonl.lock", "audit-pending.%d.journal", "audit-pending.%d.journal.lock")
    elif kind == "locks":
        npids = LOCKS_PIDS if not dev else 1000
        names = ("audit-spool.%d.jsonl.lock", "audit-pending.%d.journal.lock")
    else:
        _die("arvore desconhecida: %s" % kind)
    sd = str(state)
    flags = os.O_WRONLY | os.O_CREAT | os.O_EXCL
    for pid in range(PID_BASE, PID_BASE + npids):
        for fmt in names:
            os.close(os.open(os.path.join(sd, fmt % pid), flags, 0o600))
    n = len(os.listdir(sd))
    expect = npids * len(names)
    if n != expect:
        _die("arvore %s com %d entradas, esperado %d" % (kind, n, expect))
    return {"kind": kind, "entries": n, "build_s": round(time.monotonic() - t0, 2)}


def census(state: Path, with_orphans: bool) -> Dict[str, Any]:
    t0 = time.monotonic()
    names = os.listdir(str(state))
    c = {"entries": len(names), "spool_lock": 0, "journal": 0, "journal_lock": 0,
         "draining": 0, "active_spool": 0}
    now = time.time()
    orphan_n, orphan_age_max = 0, 0.0
    drain_age_max = 0.0
    for nm in names:
        if RE_SPOOL_LOCK.fullmatch(nm):
            c["spool_lock"] += 1
        elif RE_JOURNAL_LOCK.fullmatch(nm):
            c["journal_lock"] += 1
        elif RE_JOURNAL.fullmatch(nm):
            c["journal"] += 1
        elif RE_DRAINING.fullmatch(nm):
            c["draining"] += 1
            if with_orphans:
                try:
                    drain_age_max = max(drain_age_max, now - os.stat(os.path.join(str(state), nm)).st_mtime)
                except OSError:
                    pass
        else:
            m = RE_ACTIVE_SPOOL.fullmatch(nm)
            if m:
                c["active_spool"] += 1
                if with_orphans:
                    try:
                        st = os.stat(os.path.join(str(state), nm))
                    except OSError:
                        continue
                    if st.st_size > 0 and not _pid_alive(int(m.group(1))):
                        orphan_n += 1
                        orphan_age_max = max(orphan_age_max, now - st.st_mtime)
    if with_orphans:
        c["orphan_active_with_content"] = orphan_n
        c["orphan_active_age_max_s"] = round(orphan_age_max, 1)
        c["draining_age_max_s"] = round(drain_age_max, 1)
    c["census_s"] = round(time.monotonic() - t0, 3)
    return c


def _pid_alive(pid: int) -> bool:
    try:
        os.kill(pid, 0)
    except ProcessLookupError:
        return False
    except PermissionError:
        return True
    except OSError:
        return False
    return True


def errors_census(audit_dir: Path) -> Dict[str, int]:
    out = {k: 0 for k, _ in ERR_CLASSES}
    out["lines"] = 0
    p = audit_dir / "audit-log.errors"
    if not p.is_file():
        return out
    with p.open("r", encoding="utf-8", errors="replace") as f:
        for line in f:
            out["lines"] += 1
            for k, needle in ERR_CLASSES:  # 1.a classe que casa (a ordem importa)
                if needle in line:
                    out[k] += 1
                    break
    return out


def canonical_lines(audit_dir: Path) -> int:
    p = audit_dir / "audit-log.jsonl"
    if not p.is_file():
        return 0
    with p.open("rb") as f:
        return sum(1 for _ in f)


# ---------------------------------------------------------------------------
# Execucao de um processo de hook sob o modelo do harness
# ---------------------------------------------------------------------------


class Cfg:
    def __init__(self, run_dir: Path, mirror: Path, hook_path: str, bash: str,
                 timeout_s: float) -> None:
        self.run_dir = run_dir
        self.mirror = mirror
        self.wrapper = mirror / ".claude" / "hooks" / "_python-hook.sh"
        self.hook_path = hook_path
        self.bash = bash
        self.timeout_s = timeout_s
        self.home = run_dir / "home"
        self.tmp = run_dir / "tmp"


def _child_env(cfg: Cfg, audit_dir: Path, mark: Path, knobs: Dict[str, str]) -> Dict[str, str]:
    env = {
        "PATH": cfg.hook_path,
        "HOME": str(cfg.home),
        "TMPDIR": str(cfg.tmp) + "/",
        "LANG": os.environ.get("LANG", "en_US.UTF-8"),
        "USER": os.environ.get("USER", ""),
        "LOGNAME": os.environ.get("LOGNAME", ""),
        "CLAUDE_PROJECT_DIR": str(cfg.mirror),
        "CEO_AUDIT_LOG_DIR": str(audit_dir),
        "W05_MARK": str(mark),
    }
    env.update(knobs)
    return env


_STDIN_EVENT = json.dumps({"hook_event_name": "PreToolUse", "tool_name": "Edit",
                           "tool_input": {"file_path": "/w05/synthetic.txt"},
                           "session_id": "w05-synthetic"}).encode()


def _parse_marks(p: Path) -> Dict[str, Any]:
    marks: Dict[str, Any] = {"drains": []}
    try:
        raw = p.read_text(encoding="utf-8", errors="replace")
    except OSError:
        return marks
    for line in raw.splitlines():
        parts = line.split(" ", 2)
        if len(parts) < 2:
            continue
        name, extra = parts[0], (parts[2] if len(parts) > 2 else "")
        try:
            t = int(parts[1])
        except ValueError:
            continue
        if name == "drain":
            try:
                info = json.loads(extra)
            except ValueError:
                info = {}
            info["t_ret"] = t
            marks["drains"].append(info)
        elif name == "interp":
            try:
                marks["interp"] = json.loads(extra)
            except ValueError:
                marks["interp"] = {"raw": extra}
        elif name == "emitted":
            marks["emitted_n"] = marks.get("emitted_n", 0) + 1
            marks.setdefault("emitted", t)
        elif name not in marks:
            marks[name] = t
    return marks


class Supervised:
    """Um processo de hook: alimenta o stdin, le stdout/stderr, mata no timeout."""

    def __init__(self, cfg: Cfg, audit_dir: Path, mark: Path, knobs: Dict[str, str],
                 meta: Dict[str, Any]) -> None:
        self.rec: Dict[str, Any] = dict(meta)
        self.mark = mark
        env = _child_env(cfg, audit_dir, mark, knobs)
        self.rec["t0_wall"] = time.time_ns()
        self.rec["t0"] = _clk()
        self.p = subprocess.Popen([cfg.bash, str(cfg.wrapper), "w05_guard.py"],
                                  stdin=subprocess.PIPE, stdout=subprocess.PIPE,
                                  stderr=subprocess.PIPE, env=env, cwd=str(cfg.mirror),
                                  close_fds=True)
        self.rec["pid"] = self.p.pid
        self.rec["kstart_wall"] = _kern_start_wall_ns(self.p.pid)
        self._lock = threading.Lock()
        self._exited = False
        self._out = bytearray()
        self._err = bytearray()
        remaining = cfg.timeout_s - (_clk() - self.rec["t0"]) / 1e9
        self._timer = threading.Timer(max(0.0, remaining), self._kill)
        self._timer.daemon = True
        self._threads = [
            threading.Thread(target=self._feed, daemon=True),
            threading.Thread(target=self._read, args=(self.p.stdout, self._out, "out"), daemon=True),
            threading.Thread(target=self._read, args=(self.p.stderr, self._err, "err"), daemon=True),
            threading.Thread(target=self._wait, daemon=True),
        ]
        self._timer.start()
        for t in self._threads:
            t.start()

    def _kill(self) -> None:
        with self._lock:
            if self._exited:
                return
            try:
                os.kill(self.p.pid, signal.SIGKILL)
                self.rec["t_kill"] = _clk()
            except ProcessLookupError:
                pass

    def _feed(self) -> None:
        try:
            self.p.stdin.write(_STDIN_EVENT)
            self.p.stdin.close()
        except (BrokenPipeError, OSError, ValueError):
            pass

    def _read(self, stream, buf: bytearray, key: str) -> None:
        fd = stream.fileno()
        while True:
            try:
                chunk = os.read(fd, 65536)
            except OSError:
                break
            if not chunk:
                self.rec["t_%s_eof" % key] = _clk()
                break
            if not buf:
                self.rec["t_%s_first" % key] = _clk()
            buf.extend(chunk)
        try:
            stream.close()
        except OSError:
            pass

    def _wait(self) -> None:
        try:
            _, status = os.waitpid(self.p.pid, 0)
        except ChildProcessError:
            status = -1
        t = _clk()
        with self._lock:
            self._exited = True
        self._timer.cancel()
        self.rec["t_exit"] = t
        self.rec["status"] = status
        if status >= 0 and os.WIFSIGNALED(status):
            self.p.returncode = -os.WTERMSIG(status)
        elif status >= 0:
            self.p.returncode = os.WEXITSTATUS(status)
        else:
            self.p.returncode = -1

    def finish(self, grace_s: float) -> Dict[str, Any]:
        for t in self._threads:
            t.join(timeout=grace_s)
        r = self.rec
        r["hung_threads"] = sum(1 for t in self._threads if t.is_alive())
        st = r.get("status", -1)
        r["killed"] = bool(st >= 0 and os.WIFSIGNALED(st) and os.WTERMSIG(st) == signal.SIGKILL)
        r["signaled"] = bool(st >= 0 and os.WIFSIGNALED(st))
        r["rc"] = os.WEXITSTATUS(st) if st >= 0 and os.WIFEXITED(st) else None
        out = bytes(self._out).decode("utf-8", "replace")
        dec = None
        for line in out.splitlines():
            try:
                obj = json.loads(line)
            except ValueError:
                continue
            if isinstance(obj, dict) and obj.get("decision") == "block":
                dec = "block"
        r["decision_in_stdout"] = dec == "block"
        r["delivered"] = bool(dec == "block" and not r["signaled"] and r.get("t_exit") is not None)
        r["stderr_tail"] = bytes(self._err[-400:]).decode("utf-8", "replace")
        r["marks"] = _parse_marks(self.mark)
        _derive(r)
        return r


def _ms(a: Optional[int], b: Optional[int]) -> Optional[float]:
    if a is None or b is None:
        return None
    return round((b - a) / 1e6, 3)


def _derive(r: Dict[str, Any]) -> None:
    m = r["marks"]
    t0 = r["t0"]
    r["lat_exit_ms"] = _ms(t0, r.get("t_exit"))
    r["lat_first_byte_ms"] = _ms(t0, r.get("t_out_first"))
    af = m.get("atexit_first")
    exit_drains = [d for d in m["drains"] if af is not None and d.get("t0", 0) >= af]
    pre_drains = [d for d in m["drains"] if af is None or d.get("t0", 0) < af]
    r["exit_drains"] = exit_drains
    r["pre_drains"] = pre_drains
    r["exit_drain_ms"] = _ms(exit_drains[0]["t0"], exit_drains[-1]["t_ret"]) if exit_drains else None
    alive = not r.get("signaled")
    r["x3_final_ms"] = _ms(m.get("atexit_last"), r.get("t_exit")) if alive else None
    r["x3_after_drain_ms"] = (_ms(exit_drains[-1]["t_ret"], r.get("t_exit"))
                              if (alive and exit_drains) else None)
    r["x4_start_ms"] = _ms(t0, m.get("start"))
    r["x4_import_ms"] = _ms(t0, m.get("imported"))
    ks = r.get("kstart_wall")
    r["x4_kstart_ms"] = round((ks - r["t0_wall"]) / 1e6, 3) if ks else None
    r["x5_ms"] = _ms(m.get("decision_taken"), m.get("stdout_written"))
    r["interp"] = m.get("interp")


_MARK_COUNTERS = frozenset(("emitted_n",))  # contadores, nao instantes


def _last_mark(r: Dict[str, Any]) -> str:
    m = [(n, t) for n, t in r["marks"].items() if isinstance(t, int) and n not in _MARK_COUNTERS]
    m += [("drain", d["t_ret"]) for d in r["marks"].get("drains", []) if isinstance(d.get("t_ret"), int)]
    return max(m, key=lambda x: x[1])[0] if m else "none"


def run_unit(cfg: Cfg, cell: str, unit: int, conc: int, audit_dir: Path,
             knobs: Dict[str, str], raw_fh) -> List[Dict[str, Any]]:
    mdir = cfg.run_dir / "marks" / cell
    mdir.mkdir(parents=True, exist_ok=True)
    procs = []
    for slot in range(conc):
        mark = mdir / ("%03d-%d.mark" % (unit, slot))
        procs.append(Supervised(cfg, audit_dir, mark, knobs,
                                {"cell": cell, "unit": unit, "slot": slot, "conc": conc}))
    recs = [p.finish(cfg.timeout_s + POST_KILL_GRACE_S) for p in procs]
    for r in recs:
        raw_fh.write(json.dumps(r, sort_keys=True, default=str) + "\n")
    raw_fh.flush()
    return recs


class Holder:
    """Portador EXTERNO da trava canonica (X2): o driver segura o flock."""

    def __init__(self, lock_path: Path) -> None:
        self.lock_path = lock_path
        self.fd: Optional[int] = None

    def __enter__(self) -> "Holder":
        self.fd = os.open(str(self.lock_path), os.O_CREAT | os.O_RDWR, 0o600)
        fcntl.flock(self.fd, fcntl.LOCK_EX | fcntl.LOCK_NB)
        probe = os.open(str(self.lock_path), os.O_RDWR)
        try:
            fcntl.flock(probe, fcntl.LOCK_EX | fcntl.LOCK_NB)
            fcntl.flock(probe, fcntl.LOCK_UN)
            os.close(probe)
            _die("controle do portador falhou: 2.a descricao obteve o flock")
        except OSError as e:
            os.close(probe)
            if e.errno not in (errno.EAGAIN, errno.EWOULDBLOCK):
                raise
        return self

    def __exit__(self, *exc: Any) -> None:
        if self.fd is not None:
            fcntl.flock(self.fd, fcntl.LOCK_UN)
            os.close(self.fd)
            self.fd = None


# ---------------------------------------------------------------------------
# Resumo por celula e veredito
# ---------------------------------------------------------------------------


def summarize(cell: str, recs: List[Dict[str, Any]], timeout_s: float) -> Dict[str, Any]:
    n = len(recs)
    tp = _tail_p(n)
    tname = "p95" if tp == 0.95 else "p90"
    killed = sum(1 for r in recs if r["killed"])
    signaled = sum(1 for r in recs if r["signaled"])
    cens = timeout_s * 1000.0
    over = [r for r in recs if r["lat_exit_ms"] is not None and r["lat_exit_ms"] > cens]
    # v2 (ii): descartada = morta pelo driver OU saida depois do timeout.
    delivered = sum(1 for r in recs if r["delivered"] and not (r["lat_exit_ms"] is not None
                                                               and r["lat_exit_ms"] > cens))
    lat = [r["lat_exit_ms"] for r in recs if r["lat_exit_ms"] is not None]
    p50, ptl = _pct(lat, 0.5), _pct(lat, tp)
    lat_desc = sorted(lat, reverse=True)
    deaths = [{"unit": r["unit"], "slot": r["slot"], "last_mark": _last_mark(r),
               "lat_exit_ms": r["lat_exit_ms"]} for r in recs if r["killed"]]
    last_marks: Dict[str, int] = {}
    for d in deaths:
        last_marks[d["last_mark"]] = last_marks.get(d["last_mark"], 0) + 1
    exit_drains = [d for r in recs for d in r["exit_drains"]]
    eds_vals = [d.get("eds") for d in exit_drains]
    if any(v == "NA" for v in eds_vals) or not eds_vals:
        eds = "n/a (campo ausente no codigo medido)" if eds_vals else "n/a (nenhum drain de saida)"
    else:
        k = sum(1 for v in eds_vals if v is True)
        eds = "%d/%d" % (k, len(eds_vals))
    errs: Dict[str, int] = {}
    for d in exit_drains:
        key = str(d.get("error"))
        errs[key] = errs.get(key, 0) + 1
    no_exit_drain = sum(1 for r in recs if not r["exit_drains"] and not r["signaled"])
    pre = [d for r in recs for d in r["pre_drains"]]
    s: Dict[str, Any] = {
        "cell": cell, "N": n, "tail": tname,
        "timeouts_killed": killed, "signaled": signaled,
        "delivered": delivered, "discarded": n - delivered,
        "lat_exit_p50_ms": p50, "lat_exit_tail_ms": ptl,
        "lat_tail_censored": bool(ptl is not None and ptl >= cens),
        "lat_exit_max_ms": lat_desc[0] if lat_desc else None,
        "lat_exit_2nd_ms": lat_desc[1] if len(lat_desc) > 1 else None,
        "exits_over_T": len(over), "killed_last_marks": last_marks, "deaths": deaths,
        "exit_drain_p50_ms": _pct([r["exit_drain_ms"] for r in recs if r["exit_drain_ms"] is not None], 0.5),
        "exit_drain_tail_ms": _pct([r["exit_drain_ms"] for r in recs if r["exit_drain_ms"] is not None], tp),
        "exit_drain_errors": errs, "exit_drain_calls": len(exit_drains),
        "exit_without_drain_call": no_exit_drain,
        "exit_deadline_skip": eds,
        "pre_decision_drains": len(pre),
        "pre_decision_drain_contended": sum(1 for d in pre if d.get("contended")),
        "hung_threads": sum(r["hung_threads"] for r in recs),
        "emit_errors": sum(1 for r in recs if "emit_error" in r["marks"]),
    }
    x5 = [r["x5_ms"] for r in recs if r["x5_ms"] is not None]
    if x5:
        s["x5_p50_ms"], s["x5_tail_ms"], s["x5_N"] = _pct(x5, 0.5), _pct(x5, _tail_p(len(x5))), len(x5)
        s["x5_max_ms"] = max(x5)
    return s


def pooled(recs: List[Dict[str, Any]], key: str) -> Dict[str, Any]:
    v = [r[key] for r in recs if r.get(key) is not None]
    return {"N": len(v), "p50": _pct(v, 0.5), "p95": _pct(v, 0.95) if len(v) >= 100 else None,
            "p90": _pct(v, 0.90), "p99": _pct(v, 0.99) if len(v) >= 100 else None,
            "max": max(v) if v else None}


def verdict(summ: Dict[str, Dict[str, Any]], all_recs: List[Dict[str, Any]],
            arm: str, dev: bool) -> Dict[str, Any]:
    g = lambda c, k: summ.get(c, {}).get(k)  # noqa: E731
    out: Dict[str, Any] = {}
    x2 = summ.get("X2")
    if x2:
        n, d = x2["N"], x2["discarded"]
        p_hat = d / n if n else None
        out["p_hat_X2"] = p_hat
        out["N_next_arm_rule"] = (int(math.ceil(30.0 / p_hat)) if p_hat else None)
        tag = "HEAD" if arm == "head" else "pos-cura"
        line = "W0.5-veredito (%s): decisoes_descartadas=%d N=%d" % (tag, d, n)
        out["verdict_line"] = ("DEV-SMOKE (NAO CONTA) " + line) if dev else line
    if arm == "head":
        c4, c8 = g("C4", "timeouts_killed") or 0, g("C8", "timeouts_killed") or 0
        c2, c6 = g("C2", "timeouts_killed"), g("C6", "timeouts_killed")
        red = {
            ">=1 timeout em C4 ou C8": (c4 + c8) >= 1,
            "0 timeout em C2 e C6": (c2 == 0 and c6 == 0),
            "decisao perdida em X2": bool(x2 and x2["discarded"] >= 1),
        }
        out["red_criterion"] = red
        out["red_reproduced"] = all(red.values())
        out["H1"] = "fora deste instrumento (LEDGER, W2 — H1 vivo: F = 0,9947, |D| = 14.572)"
        # Leitura INFORMATIVA (nao decide): «timeout» lido como linha de breadcrumb.
        bc = lambda c: (summ.get(c, {}).get("errors_delta") or {}).get("drain_canonical_lock_timeout")  # noqa: E731
        out["red_criterion_breadcrumb_reading_info"] = {c: bc(c) for c in ("C2", "C4", "C6", "C8", "X2")}
    fin = pooled(all_recs, "x3_final_ms")
    aft = pooled(all_recs, "x3_after_drain_ms")
    out["X3_final"] = fin
    out["X3_after_exit_drain"] = aft
    stop = {}
    for name, pl in (("final", fin), ("after_exit_drain", aft)):
        p99 = pl.get("p99")
        if p99 is not None:
            req = MARGIN_P99_FACTOR * p99 / 1000.0
            stop[name] = {"p99_s": round(p99 / 1000.0, 4), "margin_required_s": round(req, 4),
                          "stop_rule_fires": bool(req >= STOP_MARGIN_S or p99 / 1000.0 >= STOP_MARGIN_S),
                          "fits_initial_margin": bool(req <= EXIT_MARGIN_S)}
    out["stop_rule"] = stop
    out["X4"] = {"wrapper_to_first_line": pooled(all_recs, "x4_start_ms"),
                 "wrapper_to_import_anchor": pooled(all_recs, "x4_import_ms"),
                 "wrapper_to_kernel_start": pooled(all_recs, "x4_kstart_ms")}
    x5 = summ.get("X5")
    if x5 and x5.get("x5_tail_ms") is not None:
        out["X5_rule_fires"] = bool(x5["x5_max_ms"] / 1000.0 > EXIT_MARGIN_S)  # v2 (iii): pelo MAXIMO
    x1 = summ.get("X1")
    if x1:
        out["T2_trigger_X1"] = {
            "exit_deadline_skip": x1["exit_deadline_skip"],
            "tail_vs_T_min": "%s=%s ms vs %s ms" % (x1["tail"], x1["lat_exit_tail_ms"], HOOK_TIMEOUT_S * 1000),
        }
    return out


# ---------------------------------------------------------------------------
# Substrato
# ---------------------------------------------------------------------------


def _wrapper_resolution(hook_path: str) -> Dict[str, Any]:
    for c in WRAPPER_CANDIDATES:
        w = shutil.which(c, path=hook_path)
        if not w:
            continue
        try:
            v = subprocess.run([w, "-c", "import sys;print(sys.version.split()[0])"],
                               capture_output=True, text=True, timeout=20).stdout.strip()
        except Exception:
            continue
        try:
            maj, mi = (int(x) for x in v.split(".")[:2])
        except ValueError:
            continue
        if (maj, mi) >= (3, 9):
            return {"candidate": c, "path": w, "realpath": os.path.realpath(w), "version": v}
    return {"candidate": None}


def substrate(repo: Path, cfg: Optional[Cfg], instrument: Path) -> Dict[str, Any]:
    def _cmd(args: List[str], timeout: float = 20.0) -> Optional[str]:
        try:
            return subprocess.run(args, capture_output=True, text=True, timeout=timeout).stdout.strip()
        except Exception:
            return None
    ps = _cmd(["ps", "-axo", "comm="]) or ""
    claude_procs = sum(1 for ln in ps.splitlines() if os.path.basename(ln.strip()) == "claude")
    all_procs = sum(1 for ln in ps.splitlines() if ln.strip())
    s: Dict[str, Any] = {
        "utc": _now_utc(),
        "instrument_path": str(instrument),
        "instrument_sha256": _sha256_file(instrument),
        "repo": str(repo),
        "claude_code_version": _cmd(["claude", "--version"]),
        "os": {"platform": platform.platform(), "mac_ver": platform.mac_ver()[0],
               "build": _cmd(["sw_vers", "-buildVersion"])},
        "driver_python": {"exe": sys.executable, "ver": sys.version.split()[0]},
        "load": {"loadavg": [round(x, 2) for x in os.getloadavg()],
                 "uptime": _cmd(["uptime"]), "claude_processes": claude_procs,
                 "processes": all_procs},
    }
    try:
        s["repo_head"] = subprocess.run(["git", "rev-parse", "HEAD"], cwd=str(repo),
                                        capture_output=True, text=True, timeout=20).stdout.strip()
    except Exception:
        s["repo_head"] = None
    if cfg is not None:
        s["hook_path"] = cfg.hook_path
        s["bash"] = cfg.bash
        s["wrapper_python_by_candidates"] = _wrapper_resolution(cfg.hook_path)
        s["hook_timeout_s"] = cfg.timeout_s
        s["df_free_gb"] = round(_df_free_gb(cfg.run_dir), 1)
    return s


# ---------------------------------------------------------------------------
# Subcomando run
# ---------------------------------------------------------------------------

KNOBS = {
    "nospool": {"W05_EMIT": "0"},
    "spool": {"W05_EMIT": "1"},
    "early": {"W05_EARLY": "1"},
}


def _print(fh, msg: str) -> None:
    sys.stdout.write(msg + "\n")
    sys.stdout.flush()
    fh.write(msg + "\n")
    fh.flush()


def cmd_run(a: argparse.Namespace) -> int:
    instrument = Path(__file__).resolve()
    repo = Path(a.repo).resolve() if a.repo else instrument.parents[5]
    work = _check_work(Path(a.work), repo)
    _df_guard(work, "inicio")
    stamp = _dt.datetime.now(_dt.timezone.utc).strftime("%Y%m%dT%H%M%SZ")
    runs = work / "runs"
    runs.mkdir(exist_ok=True)
    run_dir = _owned_dir(runs / ("%s-%s%s" % (a.arm, stamp, "-dev" if a.dev_smoke else "")), work)
    mirror_info = build_mirror(repo, run_dir / "mirror")
    hook_path = a.hook_path if a.hook_path else os.environ.get("PATH", "/usr/bin:/bin")
    bash = shutil.which("bash", path=hook_path) or "/bin/bash"
    cfg = Cfg(run_dir, run_dir / "mirror", hook_path, bash, a.hook_timeout)
    cfg.home.mkdir()
    cfg.tmp.mkdir()
    n_single = 2 if a.dev_smoke else N_SINGLE
    bursts = 1 if a.dev_smoke else N_BURSTS
    n_x6 = 2 if a.dev_smoke else N_X6
    overrides: Dict[str, int] = {}
    for item in a.units or []:
        k, _, v = item.partition("=")
        overrides[k.strip()] = int(v)
    cells = [c for c in CELL_ORDER if (not a.cells or c in a.cells.split(","))]
    log = (run_dir / "run.log").open("a", encoding="utf-8")
    raw = (run_dir / "raw.jsonl").open("a", encoding="utf-8")
    sub = substrate(repo, cfg, instrument)
    sub["mirror"] = mirror_info
    sub["arm"] = a.arm
    sub["dev_smoke"] = bool(a.dev_smoke)
    sub["load_note"] = a.load_note
    sub["constants"] = {k: globals()[k] for k in (
        "FULL_ENTRIES", "LOCKS_ENTRIES", "CONC", "HOOK_TIMEOUT_S", "EXIT_MARGIN_S", "DEADLINE_S",
        "STOP_MARGIN_S", "N_SINGLE", "N_BURSTS", "N_X6", "DF_FLOOR_GB")}
    (run_dir / "substrate-start.json").write_text(json.dumps(sub, indent=2, sort_keys=True))
    _print(log, "W0.5 %s run_dir=%s instrument_sha256=%s repo_head=%s" % (
        "DEV-SMOKE (NAO CONTA)" if a.dev_smoke else "", run_dir, sub["instrument_sha256"], sub["repo_head"]))
    _print(log, "substrato: CC=%s python(wrapper/candidatos)=%s os=%s load=%s claude_procs=%d" % (
        sub["claude_code_version"], sub["wrapper_python_by_candidates"], sub["os"]["mac_ver"],
        sub["load"]["loadavg"], sub["load"]["claude_processes"]))

    # Controles do instrumento (cada celula precisa poder ficar VERMELHA): o driver
    # entrega uma decisao rapida e DESCARTA uma saida que passa do timeout.
    ctrl_audit = run_dir / "ctrl" / "audit"
    build_state(ctrl_audit, "empty", a.dev_smoke)
    warm = run_unit(cfg, "WARMUP", 0, 1, ctrl_audit, KNOBS["spool"], raw)
    ok = run_unit(cfg, "CTRL-OK", 0, 1, ctrl_audit, KNOBS["spool"], raw)
    kill = run_unit(cfg, "CTRL-KILL", 0, 1, ctrl_audit,
                    dict(KNOBS["spool"], W05_EXIT_SLEEP=str(a.hook_timeout + 1.0)), raw)
    ctrl = {"warmup_delivered": warm[0]["delivered"], "ok_delivered": ok[0]["delivered"],
            "kill_discarded": (not kill[0]["delivered"]) and kill[0]["killed"],
            "interp": ok[0].get("interp")}
    _print(log, "controles: %s" % json.dumps(ctrl, sort_keys=True))
    if not (ctrl["ok_delivered"] and ctrl["kill_discarded"]):
        _print(log, "ABORT: controle do instrumento falhou (entrega ou descarte)")
        return 3
    want_ver = sub["wrapper_python_by_candidates"].get("version")
    got_ver = (ok[0].get("interp") or {}).get("ver")

    trees: Dict[str, Path] = {}
    tree_info: Dict[str, Any] = {}
    summ: Dict[str, Dict[str, Any]] = {}
    all_recs: List[Dict[str, Any]] = []
    cell_meta: Dict[str, Any] = {}
    for cell in cells:
        kind, conc, mode = CELLS[cell]
        _df_guard(work, cell)
        if kind == "empty":
            audit = run_dir / "cells" / cell / "audit"
            tree_info[cell] = build_state(audit, "empty", a.dev_smoke)
        else:
            if kind not in trees:
                audit = run_dir / "trees" / kind / "audit"
                tree_info[kind] = build_state(audit, kind, a.dev_smoke)
                trees[kind] = audit
                _print(log, "arvore %s: %s" % (kind, tree_info[kind]))
            audit = trees[kind]
        state = audit / "state"
        before = {"census": census(state, cell == "X6"), "errors": errors_census(audit),
                  "canonical_lines": canonical_lines(audit), "loadavg": list(os.getloadavg())}
        units = overrides.get(cell, n_single if conc == 1 else bursts)
        if cell == "X6":
            units = overrides.get(cell, n_x6)
        recs: List[Dict[str, Any]] = []
        trajectory = []
        t_cell = time.monotonic()
        if cell == "X2":
            with Holder(audit / "audit-log.lock"):
                for u in range(units):
                    recs.extend(run_unit(cfg, cell, u, conc, audit, KNOBS[mode], raw))
        else:
            for u in range(units):
                recs.extend(run_unit(cfg, cell, u, conc, audit, KNOBS[mode], raw))
                if cell == "X6":
                    trajectory.append(census(state, True))
        after = {"census": census(state, cell in ("X6", "X2", "C8")), "errors": errors_census(audit),
                 "canonical_lines": canonical_lines(audit), "loadavg": list(os.getloadavg()),
                 "cell_wall_s": round(time.monotonic() - t_cell, 1)}
        s = summarize(cell, recs, cfg.timeout_s)
        s["errors_delta"] = {k: after["errors"][k] - before["errors"][k] for k in after["errors"]}
        s["canonical_lines_delta"] = after["canonical_lines"] - before["canonical_lines"]
        s["entries_before"] = before["census"]["entries"]
        s["entries_after"] = after["census"]["entries"]
        s["loadavg_before"] = [round(x, 2) for x in before["loadavg"]]
        s["loadavg_after"] = [round(x, 2) for x in after["loadavg"]]
        cell_meta[cell] = {"before": before, "after": after, "x6_trajectory": trajectory}
        summ[cell] = s
        all_recs.extend(recs)
        _print(log, "%s %s" % (cell, json.dumps(s, sort_keys=True, default=str)))
        if cell == "X6":
            _print(log, "X6 trajetoria (orfaos com conteudo, draining) depois de cada emissor: %s" % (
                [(t.get("orphan_active_with_content"), t.get("draining")) for t in trajectory]))

    interps = sorted({json.dumps(r.get("interp"), sort_keys=True) for r in all_recs if r.get("interp")})
    res = verdict(summ, all_recs, a.arm, a.dev_smoke)
    res["interpreters_seen"] = [json.loads(x) for x in interps]
    res["interpreter_version_matches_wrapper_candidates"] = bool(got_ver and got_ver == want_ver)
    res["controls"] = ctrl
    end = substrate(repo, cfg, instrument)
    out = {"substrate_start": sub, "substrate_end": end, "trees": tree_info,
           "cells": summ, "cell_meta": cell_meta, "result": res}
    (run_dir / "summary.json").write_text(json.dumps(out, indent=2, sort_keys=True, default=str))
    _print(log, "RESULTADO %s" % json.dumps(res, sort_keys=True, default=str))
    if res.get("verdict_line"):
        _print(log, res["verdict_line"])
    raw.close()
    log.close()
    return 0


# ---------------------------------------------------------------------------
# Subcomando x7 — calibracao contra o harness REAL (no maximo 2 chamadas)
# ---------------------------------------------------------------------------


def cmd_x7(a: argparse.Namespace) -> int:
    instrument = Path(__file__).resolve()
    repo = Path(a.repo).resolve() if a.repo else instrument.parents[5]
    work = _check_work(Path(a.work), repo)
    if not a.confirm_paid:
        _die("x7 gasta uma chamada paga `claude -p`: exige --confirm-paid")
    x7 = work / "x7"
    if not x7.exists():
        _owned_dir(x7, work)
    ledger = x7 / "calls.json"
    calls = json.loads(ledger.read_text()) if ledger.is_file() else []
    if len(calls) >= X7_MAX_CALLS:
        _die("freio Q1: %d chamadas ja feitas (maximo %d)" % (len(calls), X7_MAX_CALLS))
    if any(c.get("leg") == a.leg for c in calls):
        _die("perna %s ja rodou" % a.leg)
    if a.leg == "C1" and not any(c.get("leg") == "C2" and c.get("hook_ran") and not c.get("marker_exists")
                                 for c in calls):
        _die("C1 so roda depois de C2 provar que o hook BLOQUEIA (controle)")
    _df_guard(work, "x7")
    mirror = x7 / "mirror"
    if not mirror.exists():
        build_mirror(repo, mirror)
    hook_path = a.hook_path if a.hook_path else os.environ.get("PATH", "/usr/bin:/bin")
    leg_dir = _owned_dir(x7 / ("leg-%s" % a.leg), work)
    proj = leg_dir / "proj"
    proj.mkdir()
    audit = leg_dir / "audit"
    build_state(audit, "empty", False)
    (leg_dir / "home").mkdir()
    (leg_dir / "tmp").mkdir()
    mark = leg_dir / "guard.mark"
    marker = proj / ("x7-marker-%s" % a.leg)
    env_parts = {
        "PATH": hook_path, "HOME": str(leg_dir / "home"), "TMPDIR": str(leg_dir / "tmp") + "/",
        "CEO_AUDIT_LOG_DIR": str(audit), "W05_MARK": str(mark), "W05_EMIT": "1", "W05_FLUSH": "1",
        "W05_EXIT_SLEEP": str(X7_EXIT_SLEEP_S if a.leg == "C1" else 0),
    }
    cmd = " ".join("%s=%s" % (k, shlex.quote(v)) for k, v in env_parts.items())
    cmd += " bash %s w05_guard.py" % shlex.quote(str(mirror / ".claude" / "hooks" / "_python-hook.sh"))
    settings = {"hooks": {"PreToolUse": [{"matcher": "", "hooks": [
        {"type": "command", "command": cmd, "timeout": int(HOOK_TIMEOUT_S)}]}]}}
    sfile = leg_dir / "settings.json"
    sfile.write_text(json.dumps(settings, indent=2))
    prompt = ("Use the Bash tool exactly once to run this command: touch %s . "
              "Do not use any other tool. If the tool call is blocked, reply BLOCKED and stop." % marker)
    argv = ["claude", "-p", prompt, "--model", a.model, "--settings", str(sfile),
            "--setting-sources", "local", "--no-session-persistence", "--strict-mcp-config",
            "--allowedTools", "Bash(touch:*)", "--output-format", "json"]
    env = {k: v for k, v in os.environ.items()
           if not (k.startswith("CEO_") or k.startswith("CLAUDE") or k.startswith("W05_"))}
    env["DISABLE_AUTOUPDATER"] = "1"
    calls.append({"leg": a.leg, "utc": _now_utc(), "status": "started"})
    ledger.write_text(json.dumps(calls, indent=2))
    sub = substrate(repo, None, instrument)
    t0 = time.monotonic()
    try:
        cp = subprocess.run(argv, cwd=str(proj), env=env, capture_output=True, text=True, timeout=300)
        rc, out, err = cp.returncode, cp.stdout, cp.stderr
    except subprocess.TimeoutExpired as e:
        rc, out, err = None, (e.stdout or ""), "TIMEOUT"
    wall = round(time.monotonic() - t0, 2)
    marks = _parse_marks(mark)
    hook_runs = 0
    try:
        hook_runs = sum(1 for ln in mark.read_text().splitlines() if ln.startswith("start "))
    except OSError:
        pass
    try:
        res = json.loads(out) if out.strip() else {}
    except ValueError:
        res = {"raw": out[-2000:]}
    rec = {
        "leg": a.leg, "utc": _now_utc(), "status": "done", "rc": rc, "wall_s": wall,
        "hook_ran": hook_runs > 0, "hook_runs": hook_runs, "marker_exists": marker.exists(),
        "exit_sleep_s": env_parts["W05_EXIT_SLEEP"], "hook_timeout_s": HOOK_TIMEOUT_S,
        "guard_marks": {k: v for k, v in marks.items() if k != "drains"},
        "guard_drains": marks.get("drains", []),
        "drain_after_start_s": ([(d["t0"] - marks["start"]) / 1e9 for d in marks.get("drains", [])]
                                if "start" in marks else []),
        "claude_result": {k: res.get(k) for k in ("is_error", "num_turns", "result", "total_cost_usd",
                                                   "permission_denials", "subtype")},
        "stderr_tail": (err or "")[-800:], "substrate": sub, "model": a.model,
    }
    if not rec["hook_ran"]:
        rec["reading"] = "INCONCLUSIVO: o hook nao rodou (o modelo nao chamou ferramenta)"
    elif a.leg == "C2":
        rec["reading"] = ("controle OK: o hook bloqueia" if not rec["marker_exists"]
                          else "controle FALHOU: hook rapido nao bloqueou — calibracao nula")
    else:
        rec["reading"] = ("BLOQUEOU: o harness consome a decisao antes da saida (o flush a protege)"
                          if not rec["marker_exists"] else
                          "PASSOU: o harness exige a saida dentro do timeout (modelo do driver calibrado)")
    calls[-1] = rec
    ledger.write_text(json.dumps(calls, indent=2, default=str))
    sys.stdout.write(json.dumps(rec, indent=2, default=str) + "\n")
    return 0


# ---------------------------------------------------------------------------
# Subcomando clean — limpeza CONFINADA ao --work
# ---------------------------------------------------------------------------


def cmd_clean(a: argparse.Namespace) -> int:
    instrument = Path(__file__).resolve()
    repo = Path(a.repo).resolve() if a.repo else instrument.parents[5]
    work = _check_work(Path(a.work), repo)
    targets: List[Path] = []
    runs = work / "runs"
    if runs.is_dir():
        targets += [p for p in sorted(runs.iterdir()) if p.is_dir() and (p / OWNED).is_file()
                    and (not a.run or p.name == a.run)]
    if a.x7 and (work / "x7" / OWNED).is_file():
        targets.append(work / "x7")
    for t in targets:
        _confined_rmtree(t, work)
        sys.stdout.write("removido: %s\n" % t)
    return 0


def cmd_report(a: argparse.Namespace) -> int:
    """Tabela compacta de um run (le summary.json; nada e re-medido)."""
    d = json.loads((Path(a.run_dir) / "summary.json").read_text())
    sub = d["substrate_start"]
    w = sys.stdout.write
    w("instrumento sha256=%s repo_head=%s arm=%s dev=%s\n" % (
        sub["instrument_sha256"], sub["repo_head"], sub["arm"], sub["dev_smoke"]))
    w("substrato: CC=%s hooks=%s %s SO=%s/%s load=%s->%s nota=%r\n" % (
        sub["claude_code_version"], sub["wrapper_python_by_candidates"].get("path"),
        sub["wrapper_python_by_candidates"].get("version"), sub["os"]["mac_ver"], sub["os"]["build"],
        sub["load"]["loadavg"], d["substrate_end"]["load"]["loadavg"], sub.get("load_note")))
    w("cel  N    mortos entreg descart  p50_ms   cauda_ms     drain_saida_p50  breadcrumb_timeout  eds\n")
    for c in CELL_ORDER:
        s = d["cells"].get(c)
        if not s:
            continue
        w("%-4s %-4d %-6d %-6d %-8d %-8s %-4s=%-8s%s %-16s %-19s %s\n" % (
            c, s["N"], s["timeouts_killed"], s["delivered"], s["discarded"], s["lat_exit_p50_ms"],
            s["tail"], s["lat_exit_tail_ms"], "*" if s["lat_tail_censored"] else " ",
            s["exit_drain_p50_ms"], s["errors_delta"].get("drain_canonical_lock_timeout"),
            s["exit_deadline_skip"]))
    w("RESULTADO %s\n" % json.dumps(d["result"], sort_keys=True, default=str))
    return 0


def main(argv: Optional[List[str]] = None) -> int:
    ap = argparse.ArgumentParser(description="W0.5 do PLAN-194 (instrumento pre-registrado)")
    sp = ap.add_subparsers(dest="cmd", required=True)
    r = sp.add_parser("run")
    r.add_argument("--work", required=True)
    r.add_argument("--repo", default=None)
    r.add_argument("--arm", required=True, choices=("head", "poscura"))
    r.add_argument("--hook-path", default=None, help="PATH dos hooks (o wrapper resolve o python por ele)")
    r.add_argument("--hook-timeout", type=float, default=HOOK_TIMEOUT_S)
    r.add_argument("--cells", default=None, help="subconjunto, ex.: C1,X2 (padrao: todas)")
    r.add_argument("--units", action="append", help="CELULA=n (N do braco pos-cura pela regra 3/N)")
    r.add_argument("--dev-smoke", action="store_true", help="arvores e N minimos; NAO CONTA")
    r.add_argument("--load-note", default="", help="carga declarada (ex.: agentes vivos)")
    rp = sp.add_parser("report")
    rp.add_argument("--run-dir", required=True)
    x = sp.add_parser("x7")
    x.add_argument("--work", required=True)
    x.add_argument("--repo", default=None)
    x.add_argument("--leg", required=True, choices=("C2", "C1"))
    x.add_argument("--confirm-paid", action="store_true")
    x.add_argument("--model", default="haiku")
    x.add_argument("--hook-path", default=None)
    c = sp.add_parser("clean")
    c.add_argument("--work", required=True)
    c.add_argument("--repo", default=None)
    c.add_argument("--run", default=None)
    c.add_argument("--x7", action="store_true")
    a = ap.parse_args(argv)
    if a.cmd == "run":
        return cmd_run(a)
    if a.cmd == "report":
        return cmd_report(a)
    if a.cmd == "x7":
        return cmd_x7(a)
    return cmd_clean(a)


if __name__ == "__main__":
    raise SystemExit(main())
