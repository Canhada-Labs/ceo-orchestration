"""Prova da cobertura GARANTIDA do GC v4 (sharding por nome).

O rail rejeitou quatro versoes seguidas porque a fatia do turno vinha da
POSICAO na iteracao — e toda fatia por posicao deixa cauda inalcancavel.
Este controle cria uma cauda propositalmente (muitos arquivos, o expirado
no fim da ordem de leitura) e mostra que ele E recuperado dentro de K turnos.
"""
import os
import pathlib
import shutil
import subprocess
import sys
import tempfile

REPO = pathlib.Path.home() / "canhada-labs/ceo-orchestration"
PACK = REPO / ".claude/plans/PLAN-179/staged-w01"

mirror = pathlib.Path(tempfile.mkdtemp(prefix="w179-gc-"))
shutil.copytree(REPO / ".claude/hooks", mirror / "hooks",
                ignore=shutil.ignore_patterns("__pycache__", "*.pyc", "*.pyc.*"))
for rel in ("_lib/audit_emit.py", "_lib/scratchpad_lib.py"):
    shutil.copy(PACK / ".claude/hooks" / rel, mirror / "hooks" / rel)

code = r'''
import os, sys, time, pathlib
sys.path.insert(0, r"%s")
from _lib import scratchpad_lib as sl

root = pathlib.Path(r"%s")
store = root / sl.SESSION_SCRATCHPAD_STORE_NAME
store.mkdir(parents=True, exist_ok=True)

# 600 stores FRESCOS + 12 EXPIRADOS espalhados, inclusive no fim da leitura.
old = time.time() - sl.SESSION_SCOPE_TTL_SECONDS - 3600
expired = []
for i in range(600):
    sid = "session-%%08x-0000-0000-0000-00000000%%04x" %% (i, i)
    p = store / (sid + ".sqlite")
    p.write_text("x")
    if i %% 50 == 0:            # 12 expirados, espalhados por toda a ordem
        os.utime(p, (old, old))
        expired.append(p)

print("expirados plantados: %%d" %% len(expired))
alive_before = sum(1 for p in expired if p.exists())

# K turnos (o shard avanca a cada 60s => simulamos avancando o relogio logico)
real_time = time.time
turns = sl._GC_SHARDS
# ROUND 6: pior caso apontado pelo rail — TODAS as varreduras no MESMO
# minuto (rotina diaria). Com shard por relogio, so uma fatia seria vista.
fixed = real_time()
for t in range(turns):
    sl.time.time = (lambda v: (lambda: v))(fixed)
    sl.gc_orphan_session_stores(now=fixed)
sl.time.time = real_time

alive_after = sum(1 for p in expired if p.exists())
print("expirados vivos ANTES=%%d DEPOIS=%%d (em %%d sweeps, TODOS no mesmo minuto)" %% (alive_before, alive_after, turns))
print("COBERTURA_TOTAL=%%s" %% (alive_after == 0))
fresh_left = len(list(store.glob("*.sqlite")))
print("frescos preservados=%%d (esperado 588)" %% fresh_left)
''' % (str(mirror / "hooks"), str(mirror / "state"))

r = subprocess.run([sys.executable, "-B", "-c", code], capture_output=True, text=True,
                   env={**os.environ, "CEO_STATE_ROOT": str(mirror / "state"),
                        "PYTHONDONTWRITEBYTECODE": "1"})
print(r.stdout)
if r.returncode != 0:
    print("STDERR:", r.stderr[-1200:])
print("rc=%d" % r.returncode)
