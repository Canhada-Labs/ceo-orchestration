"""Controle DURO do P1: com o nome do tmp TORNADO PREVISIVEL (urandom fixado),
plantar um symlink nesse path exato e provar que a escrita RECUSA em vez de
seguir. Isso separa 'o atacante nao adivinha' (probabilistico) de 'mesmo
sabendo o nome, nao funciona' (estrutural)."""
import os
import pathlib
import shutil
import subprocess
import sys
import tempfile

REPO = pathlib.Path.home() / "canhada-labs/ceo-orchestration"
PACK = REPO / ".claude/plans/PLAN-179/staged-w01"

mirror = pathlib.Path(tempfile.mkdtemp(prefix="w179-symhard-"))
shutil.copytree(REPO / ".claude/hooks", mirror / "hooks",
                ignore=shutil.ignore_patterns("__pycache__", "*.pyc", "*.pyc.*"))
shutil.copy(PACK / ".claude/hooks/_lib/audit_emit.py", mirror / "hooks/_lib/audit_emit.py")

state = mirror / "state"; state.mkdir(parents=True, exist_ok=True)
victim = mirror / "VICTIM.txt"
victim.write_text("conteudo canonico que NAO pode ser truncado\n")

code = r'''
import os, sys, pathlib
sys.path.insert(0, r"%s")
from _lib import audit_emit as ae
state = pathlib.Path(r"%s"); victim = pathlib.Path(r"%s")
sid = "sess-attack"

# TORNA O NOME PREVISIVEL: urandom fixo => sufixo conhecido pelo atacante.
FIXED = bytes(range(6))
ae.os.urandom = lambda n: FIXED[:n]
suffix = FIXED[:6].hex()

# 1a chamada cria o marker (transicao 40).
ae.should_emit_context_pressure(40, str(state), sid)
name = ae._context_pressure_marker_name(sid)
tmp = state / ("." + name + "." + str(os.getpid()) + "." + suffix + ".tmp")

# ATAQUE: o path EXATO que o codigo vai usar, plantado como symlink.
if tmp.exists() or tmp.is_symlink():
    tmp.unlink()
tmp.symlink_to(victim)
print("PLANTED_EXACT_PATH=%%s" %% tmp.is_symlink())

before = victim.stat().st_size
# transicao 60 => re-arma => tentaria escrever exatamente nesse tmp
ae.should_emit_context_pressure(60, str(state), sid)
after = victim.stat().st_size
print("VICTIM_SIZE_BEFORE=%%d AFTER=%%d" %% (before, after))
print("VICTIM_INTACT=%%s" %% (before == after and after > 0))
print("SYMLINK_STILL_THERE=%%s" %% tmp.is_symlink())
''' % (str(mirror / "hooks"), str(state), str(victim))

r = subprocess.run([sys.executable, "-B", "-c", code], capture_output=True, text=True,
                   env={**os.environ, "PYTHONDONTWRITEBYTECODE": "1"})
print(r.stdout)
if r.returncode != 0:
    print("STDERR:", r.stderr[-1200:])
print("rc=%d" % r.returncode)
print("CONTEUDO FINAL DA VITIMA:", repr(victim.read_text()[:60]))
