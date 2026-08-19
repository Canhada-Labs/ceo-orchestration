"""Controle do achado [P2] do round 4: o guard tem de disparar com a entrada
REAL do PreCompact (so `trigger` + `custom_instructions` + envelope), lendo o
sidecar do statusline — e NAO so com a forma injetada que producao nunca manda.

Braco A (controle NEGATIVO): entrada real, SEM sidecar  -> nenhum evento.
Braco B (a cura):            entrada real, COM sidecar  -> evento emitido.
"""
import json
import os
import pathlib
import shutil
import subprocess
import sys
import tempfile

REPO = pathlib.Path.home() / "canhada-labs/ceo-orchestration"
PACK = REPO / ".claude/plans/PLAN-179/staged-w01"

mirror = pathlib.Path(tempfile.mkdtemp(prefix="w179-prodshape-"))
shutil.copytree(REPO / ".claude/hooks", mirror / "hooks",
                ignore=shutil.ignore_patterns("__pycache__", "*.pyc", "*.pyc.*"))
for rel in ("_lib/audit_emit.py", "_lib/scratchpad_lib.py",
            "check_precompact_continuity.py"):
    shutil.copy(PACK / ".claude/hooks" / rel, mirror / "hooks" / rel)

def run(tag, write_sidecar):
    home = pathlib.Path(tempfile.mkdtemp(prefix="home-"))
    audit = home / ".claude" / "projects" / "t"
    audit.mkdir(parents=True, exist_ok=True)
    proj = pathlib.Path(tempfile.mkdtemp(prefix="proj-"))
    (proj / ".claude").mkdir(parents=True, exist_ok=True)
    if write_sidecar:
        (audit / "state").mkdir(parents=True, exist_ok=True)
        (audit / "state" / "statusline-snapshot.json").write_text(
            json.dumps({"context_pct": 84.0, "schema": "x"}))
    # ENTRADA REAL do PreCompact: so o que o schema documenta.
    payload = json.dumps({
        "hook_event_name": "PreCompact",
        "session_id": "11111111-2222-3333-4444-555555555555",
        "transcript_path": str(home / "t.jsonl"),
        "cwd": str(proj),
        "trigger": "auto",
        "custom_instructions": None,
    })
    env = {
        **os.environ,
        "HOME": str(home),
        "CLAUDE_PROJECT_DIR": str(proj),
        "CEO_AUDIT_LOG_DIR": str(audit),
        "CEO_AUDIT_SYNC_MODE": "1",
        "CEO_CONTEXT_PROGRESS_FLOOR_TOKENS": "1000",
        "PYTHONDONTWRITEBYTECODE": "1",
    }
    r = subprocess.run(
        [sys.executable, "-B", str(mirror / "hooks" / "check_precompact_continuity.py")],
        input=payload, capture_output=True, text=True, env=env)
    log = audit / "audit-log.jsonl"
    n = 0
    if log.exists():
        for line in log.read_text(errors="replace").splitlines():
            if '"context_pressure_observed"' in line:
                n += 1
                row = json.loads(line)
                print("   evento: used_bucket=%r event_source=%r project=%s session_id=%s"
                      % (row.get("used_bucket"), row.get("event_source"),
                         "sim" if row.get("project") else "NAO",
                         "sim" if row.get("session_id") else "NAO"))
    print("%s: rc=%d  context_pressure_observed=%d" % (tag, r.returncode, n))
    if r.stderr.strip():
        for l in r.stderr.strip().splitlines()[:2]:
            print("   stderr:", l[:110])
    return n

a = run("A (sem sidecar, controle NEGATIVO)", False)
b = run("B (com sidecar, a CURA)          ", True)
print()
print("VEREDITO:", "OK — o guard so dispara quando ha medicao real"
      if (a == 0 and b == 1) else "FALHOU (esperado A=0, B=1; obtido A=%d, B=%d)" % (a, b))
