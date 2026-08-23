#!/usr/bin/env python3
"""measure-right-censoring.py — PLAN-183 W0-US2 (S322).

Reproducible **method** behind the "taxa de censura à direita, por hook"
Check in ``PLAN-183-adopter-fitness.md`` (§ W0-US2). Read-only over the
audit chain and the session transcripts: this script never writes a
file, never emits an audit/HMAC event, and never re-derives the
per-project slug locally (M4 rule — the ONE resolver is
``_lib.runtime_paths.runtime_state_dir()``).

WHAT "right-censoring" means here: a hook invocation that never produced
an attributable audit-log line, either because (a) the process was
killed before the emit line ran, or (b) the hook's action is emitted
conditionally / has no verified single producer / the transcript itself
never records a ``hook_success`` for that event type. This script
measures what is MECHANICALLY computable today and refuses to print a
rate it cannot verify (silêncio > número falso).

Two independent data sources, cross-referenced:
  - DENOMINATOR ("invocations"): the session transcripts
    (``~/.claude/projects/<slug>/<session-uuid>.jsonl``), which record
    every hook run as an ``attachment`` of type ``hook_success`` or
    ``hook_cancelled``, keyed by ``attachment.command`` == the
    ``statusMessage`` string configured in ``.claude/settings.json``.
  - NUMERATOR ("emitted lines"): the live HMAC chain
    (``<state_dir>/audit-log.jsonl``), counted by ``action``, split by
    ``session_id`` empty/non-empty (empty == unattributable — the
    known suite-contamination class, PLAN-182).

Usage::

    python3 .claude/plans/PLAN-183/w0-us2/measure-right-censoring.py

Exit codes:
    0 — always, EXCEPT:
    2 — one of the two DENOMINATOR reconciliation assertions (§3: the
        per-(event,command) sum and the per-day sum of all-time
        ``hook_cancelled`` must both equal the directly-counted total)
        failed. Any other condition (e.g. a missing file) is reported
        to stderr but still exits 0 — this is an advisory instrument,
        not a gate.
"""

from __future__ import annotations

import glob
import json
import os
import re
import sys
from collections import Counter
from pathlib import Path
from typing import Dict, List, Optional, Tuple

# ---------------------------------------------------------------------------
# 0. Resolve <repo>/.claude/hooks for `_lib` import. Mirrors the precedent
#    in .claude/scripts/policy-shadow-runner.py (Path(__file__).resolve()
#    .parents[N]) — this file sits 4 levels under the repo root:
#    .claude/plans/PLAN-183/w0-us2/measure-right-censoring.py
# ---------------------------------------------------------------------------
_REPO_ROOT = Path(__file__).resolve().parents[4]
_HOOKS_DIR = _REPO_ROOT / ".claude" / "hooks"
if str(_HOOKS_DIR) not in sys.path:
    sys.path.insert(0, str(_HOOKS_DIR))

from _lib.runtime_paths import runtime_state_dir  # noqa: E402  (M4: the ONE resolver)

_SETTINGS_PATH = _REPO_ROOT / ".claude" / "settings.json"

# The only 1:1 pair verified today by source grep (unique emitter,
# unique registration): (script, statusMessage, action). Adding a pair
# here REQUIRES the same proof used for Stop.py: `grep -rln <action>
# .claude/hooks/*.py` returns exactly one hook file, AND that file is
# the one registered under the given statusMessage.
VERIFIED_PAIRS: List[Tuple[str, str, str]] = [
    ("Stop.py", "Session interrupt cleanup...", "session_stop"),
]

# Known multiplicity case: a real action, but with >1 producer, so
# lines/invocations measures conditionality/multiplicity, NEVER a
# censoring rate. Printed for transparency, explicitly labeled.
MULTIPLICITY_CASES: List[Tuple[str, str, str]] = [
    ("check_output_secrets.py", "Scanning tool output...", "tool_call_lifecycle_recorded"),
]

_TS_RE = re.compile(
    r"^(\d{4})-(\d{2})-(\d{2})T(\d{2}):(\d{2}):(\d{2})(?:\.(\d+))?Z$"
)


def _parse_ts_epoch(ts: str) -> Optional[float]:
    """Parse an ISO-8601 UTC 'Z' timestamp (ms optional) to a POSIX epoch.

    Python 3.9 stdlib has no ``datetime.fromisoformat`` support for the
    trailing 'Z' (added 3.11), and naive string comparison across mixed
    fractional-second precision is NOT chronologically monotonic
    (``"18.714Z" < "18Z"`` lexicographically despite being later) — so
    every timestamp is normalized through this parser before comparing.
    """
    m = _TS_RE.match(ts)
    if not m:
        return None
    y, mo, d, h, mi, se = (int(m.group(i)) for i in range(1, 7))
    frac = m.group(7)
    frac_val = float("0." + frac) if frac else 0.0
    import calendar
    import datetime

    try:
        dt = datetime.datetime(y, mo, d, h, mi, se)
    except ValueError:
        return None
    return calendar.timegm(dt.timetuple()) + frac_val


def _iter_jsonl(path: str):
    with open(path, encoding="utf-8", errors="replace") as f:
        for line in f:
            line = line.strip()
            if not line:
                continue
            try:
                yield json.loads(line)
            except json.JSONDecodeError:
                continue


def _extract_script(command: str) -> str:
    """Best-effort script basename from a settings.json hook command."""
    matches = re.findall(r"[A-Za-z0-9_.\-]+\.py", command)
    if matches:
        return matches[-1]
    return "inline:" + command.strip()[:40]


def _load_settings_registrations() -> List[Dict[str, str]]:
    """Flatten .claude/settings.json hooks[event][].hooks[] into rows."""
    with open(_SETTINGS_PATH, encoding="utf-8") as f:
        cfg = json.load(f)
    rows: List[Dict[str, str]] = []
    for event, entries in cfg.get("hooks", {}).items():
        for entry in entries:
            for h in entry.get("hooks", []):
                command = h.get("command", "")
                rows.append(
                    {
                        "event": event,
                        "status_message": h.get("statusMessage") or "",
                        "command": command,
                        "script": _extract_script(command),
                    }
                )
    return rows


def main() -> int:  # noqa: C901 — single linear report, deliberately not split
    state_dir = runtime_state_dir()
    print("=" * 78)
    print("PLAN-183 W0-US2 — taxa de censura à direita, por hook (método reproduzível)")
    print("=" * 78)
    print(f"state dir (via _lib.runtime_paths.runtime_state_dir()): {state_dir}")

    audit_log_path = state_dir / "audit-log.jsonl"
    if not audit_log_path.exists():
        print(f"FATAL: {audit_log_path} nao existe — nada a medir.", file=sys.stderr)
        return 0  # advisory instrument: exit 2 is reserved for the §3 assertion

    # -----------------------------------------------------------------
    # NUMERADOR — audit-log.jsonl (a cadeia viva). Também deriva a
    # JANELA (min/max ts) que delimita o DENOMINADOR abaixo, então por
    # construção toda linha do audit-log já está "dentro da janela".
    # -----------------------------------------------------------------
    total_log_lines = 0
    lines_with_ts = 0
    ts_epochs: List[float] = []
    ts_strings_by_epoch: Dict[float, str] = {}
    action_total = Counter()
    action_attributed = Counter()
    action_unattributed = Counter()

    for obj in _iter_jsonl(str(audit_log_path)):
        total_log_lines += 1
        action = obj.get("action", "<missing>")
        action_total[action] += 1
        sid = obj.get("session_id", "")
        if sid:
            action_attributed[action] += 1
        else:
            action_unattributed[action] += 1
        ts = obj.get("ts")
        if isinstance(ts, str) and ts:
            epoch = _parse_ts_epoch(ts)
            if epoch is not None:
                lines_with_ts += 1
                ts_epochs.append(epoch)
                ts_strings_by_epoch.setdefault(epoch, ts)

    if not ts_epochs:
        print(f"FATAL: nenhum 'ts' parseavel em {audit_log_path}.", file=sys.stderr)
        return 0

    window_start_epoch = min(ts_epochs)
    window_end_epoch = max(ts_epochs)
    window_start = ts_strings_by_epoch[window_start_epoch]
    window_end = ts_strings_by_epoch[window_end_epoch]

    total_unattributed = sum(action_unattributed.values())
    pct_unattributed = (100.0 * total_unattributed / total_log_lines) if total_log_lines else 0.0

    print()
    print("--- JANELA (min/max ts sobre linhas parseaveis de audit-log.jsonl) ---")
    print(f"linhas totais em audit-log.jsonl: {total_log_lines}")
    print(f"linhas com 'ts' parseavel: {lines_with_ts}")
    print(f"janela: {window_start} .. {window_end}")

    print()
    print("--- NUMERADOR (audit-log.jsonl, por action, session_id vazio vs nao-vazio) ---")
    print(f"nao-atribuiveis (session_id==''): {total_unattributed} / {total_log_lines} "
          f"({pct_unattributed:.1f}%)")
    top_unattrib = action_unattributed.most_common(5)
    if top_unattrib:
        print("  top actions nao-atribuiveis:")
        for act, n in top_unattrib:
            print(f"    {act}: {n}")

    # -----------------------------------------------------------------
    # MAPA — .claude/settings.json: statusMessage -> script, por
    # registro (event, statusMessage, command, script).
    # -----------------------------------------------------------------
    registrations = _load_settings_registrations()
    no_status = [r for r in registrations if not r["status_message"]]
    print()
    print("--- MAPA (.claude/settings.json: statusMessage -> script) ---")
    print(f"registros de hook: {len(registrations)}")
    print(f"sem statusMessage (nao-atribuivel por essa chave): {len(no_status)}")
    for r in no_status:
        print(f"    event={r['event']} script={r['script']}")

    # -----------------------------------------------------------------
    # DENOMINADOR — varrer *.jsonl do MESMO dir, excluindo basenames
    # com 'audit-log'. Uma única passada por arquivo:
    #   - contagem WINDOW (dentro da janela derivada acima), por command
    #   - contagem ALL-TIME de hook_cancelled, por (hookEvent, command)
    #     e por dia-calendario (para a reconciliacao do item 3)
    #   - quais hookEvent alguma vez produziram hook_success
    # -----------------------------------------------------------------
    transcript_paths = sorted(
        p for p in glob.glob(str(state_dir / "*.jsonl"))
        if "audit-log" not in os.path.basename(p)
    )

    window_command_total = Counter()   # hook_success + hook_cancelled, dentro da janela
    window_command_cancelled = Counter()  # so hook_cancelled, dentro da janela
    alltime_cancelled_total = 0
    alltime_cancelled_by_event_command: Counter = Counter()
    alltime_cancelled_by_day: Counter = Counter()
    alltime_cancelled_by_event: Counter = Counter()
    alltime_cancelled_by_command: Counter = Counter()
    events_with_hook_success: set = set()
    scanned_attachment_records = 0
    unparseable_timestamps = 0

    for path in transcript_paths:
        for obj in _iter_jsonl(path):
            if obj.get("type") != "attachment":
                continue
            att = obj.get("attachment")
            if not isinstance(att, dict):
                continue
            kind = att.get("type")
            if kind not in ("hook_success", "hook_cancelled"):
                continue
            scanned_attachment_records += 1
            command = att.get("command", "") or ""
            event = att.get("hookEvent", "") or ""
            if kind == "hook_success":
                events_with_hook_success.add(event)

            ts = obj.get("timestamp")
            epoch = _parse_ts_epoch(ts) if isinstance(ts, str) else None
            if epoch is None:
                unparseable_timestamps += 1
            elif window_start_epoch <= epoch <= window_end_epoch:
                window_command_total[command] += 1
                if kind == "hook_cancelled":
                    window_command_cancelled[command] += 1

            if kind == "hook_cancelled":
                alltime_cancelled_total += 1
                alltime_cancelled_by_event_command[(event, command)] += 1
                alltime_cancelled_by_event[event] += 1
                alltime_cancelled_by_command[command] += 1
                if isinstance(ts, str) and len(ts) >= 10:
                    alltime_cancelled_by_day[ts[:10]] += 1

    print()
    print("--- DENOMINADOR (transcripts: attachment.type in {hook_success,hook_cancelled}) ---")
    print(f"arquivos de transcript varridos (exclui *audit-log*): {len(transcript_paths)}")
    print(f"registros hook_success+hook_cancelled (all-time, todos os arquivos): "
          f"{scanned_attachment_records}")
    print(f"registros com 'timestamp' nao-parseavel: {unparseable_timestamps}")
    print(f"hook_cancelled all-time (todo o histórico de transcripts, TODAS as janelas): "
          f"{alltime_cancelled_total}")
    print("  por hookEvent:")
    for event, n in sorted(alltime_cancelled_by_event.items(), key=lambda kv: -kv[1]):
        print(f"    {event}: {n}")
    print("  por dia-calendario:")
    for day, n in sorted(alltime_cancelled_by_day.items()):
        print(f"    {day}: {n}")

    # ---- item 3: reconciliation assertions (the ONLY exit-2 path) ----
    sum_by_event_command = sum(alltime_cancelled_by_event_command.values())
    sum_by_day = sum(alltime_cancelled_by_day.values())
    try:
        assert sum_by_event_command == alltime_cancelled_total, (
            f"soma por (hookEvent,command) = {sum_by_event_command} != "
            f"total direto = {alltime_cancelled_total}"
        )
        assert sum_by_day == alltime_cancelled_total, (
            f"soma por dia-calendario = {sum_by_day} != "
            f"total direto = {alltime_cancelled_total}"
        )
    except AssertionError as exc:
        print(f"FATAL (reconciliacao aritmetica falhou): {exc}", file=sys.stderr)
        return 2
    print(f"reconciliacao OK: total direto == soma por (event,command) == soma por dia "
          f"== {alltime_cancelled_total}")

    events_never_hook_success = sorted(
        {r["event"] for r in registrations} - events_with_hook_success
    )
    print()
    print("--- eventos SEM nenhum hook_success all-time (denominador censurado no transcript) ---")
    for event in events_never_hook_success:
        print(f"    {event}")

    # -----------------------------------------------------------------
    # PARES 1:1 verificados — taxa de censura real.
    # -----------------------------------------------------------------
    print()
    print("--- TAXA DE CENSURA POR HOOK (pares 1:1 com produtor unico verificado) ---")
    for script, status_message, action in VERIFIED_PAIRS:
        inv = window_command_total.get(status_message, 0)
        cancelled = window_command_cancelled.get(status_message, 0)
        linhas = action_attributed.get(action, 0)
        if inv > 0:
            taxa = 1.0 - (linhas / inv)
            print(f"{script} (\"{status_message}\") -> {action}:")
            print(f"    invocacoes (janela) = {inv}, hook_cancelled (janela) = {cancelled}, "
                  f"linhas(session_id!='') = {linhas}")
            print(f"    taxa de censura = 1 - {linhas}/{inv} = {taxa*100:.1f}%")
        else:
            print(f"{script} (\"{status_message}\") -> {action}: "
                  f"invocacoes (janela) = 0 — sem base para taxa nesta janela")

    print()
    print("--- MULTIPLICIDADE CONHECIDA (NAO e taxa de censura — multiplos produtores) ---")
    for script, status_message, action in MULTIPLICITY_CASES:
        inv = window_command_total.get(status_message, 0)
        linhas = action_attributed.get(action, 0)
        if inv > 0:
            razao = linhas / inv
            print(f"{script} (\"{status_message}\") -> {action}: "
                  f"{inv} inv / {linhas} linhas = razao {razao:.2f} "
                  f"— NAO e taxa de censura (multiplos produtores)")
        else:
            print(f"{script} (\"{status_message}\") -> {action}: invocacoes (janela) = 0")

    # -----------------------------------------------------------------
    # INCOMPUTAVEIS — todo registro que nao esta nas duas listas acima,
    # com causa mecanicamente verificavel. Nunca imprime uma taxa.
    # -----------------------------------------------------------------
    verified_status_messages = {sm for _, sm, _ in VERIFIED_PAIRS} | {
        sm for _, sm, _ in MULTIPLICITY_CASES
    }
    print()
    print("--- INCOMPUTAVEIS (silencio > numero falso) ---")
    incomputable_count = 0
    for r in registrations:
        sm = r["status_message"]
        if sm in verified_status_messages:
            continue
        incomputable_count += 1
        if not sm:
            cause = "sem statusMessage no settings.json — denominador nao-atribuivel por essa chave"
        elif r["event"] in events_never_hook_success:
            cause = (f"evento '{r['event']}' nunca registra hook_success no transcript "
                     f"(so hook_cancelled quando cancela) — denominador ele mesmo censurado")
        elif r["script"] == "check_output_secrets.py":
            cause = ("mesmo script do caso de multiplicidade acima, mas statusMessage "
                     "diferente — produtor nao isolado para esta chave")
        else:
            cause = ("sem par 1:1 verificado: o log nao carrega identidade do hook emissor "
                     "(nao existe acao hook_invoked/hook_entered) e mapear esta statusMessage "
                     "a uma acao unica exigiria grep manual por hook, fora do escopo desta "
                     "medicao automatica")
        print(f"    [{r['event']}] {r['script']} (\"{sm or '<sem statusMessage>'}\"): {cause}")
    print(f"total incomputavel: {incomputable_count} / {len(registrations)} registros")

    print()
    print("=" * 78)
    print("FIM — reexecute este script apos a cadeia crescer; a janela anda, "
          "os numeros mudam, o METODO nao. Nunca ajuste este script para casar "
          "com um numero publicado antigo — republique o numero novo.")
    print("=" * 78)
    return 0


if __name__ == "__main__":
    sys.exit(main())
