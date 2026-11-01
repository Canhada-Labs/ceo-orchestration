#!/usr/bin/env python3
"""night-mode — Owner-invoked autonomy posture toggle (PLAN-165 W1 T1.1).

`/night-mode on|off|status` flips the per-machine autonomy posture by
merge-writing `permissions.defaultMode: "acceptEdits"` into the gitignored
`<project>/.claude/settings.local.json` overlay. The tracked
`.claude/settings.json` (fail-closed default: `defaultMode: "manual"` +
`disableAutoMode: "disable"`) is NEVER touched — settings are read at
session start, so the toggle takes effect on the NEXT session
("arm before sleep, disarm in the morning" semantics, PLAN-165 fact #5).

## Design decisions carried in from the PLAN-165 v2 review

- **D1 — no `bypassPermissions`, anywhere.** The only mode `on` ever
  writes is `acceptEdits`, and `off` restores only values from the
  closed set `_RESTORABLE_MODES` — which NEVER includes
  `bypassPermissions` (NM-01). `bypassPermissions` in ANY settings layer
  trips `TAMPER_PERMISSION_BYPASS` (`_lib/effective_config.py`) and turns
  `/ceo-boot` red by design; the honest escape valve is an explicit,
  ephemeral `claude --permission-mode bypassPermissions` session.
- **D2 — single-writer via ceremony prerequisite P1.** A deny rule for
  Edit/Write on `.claude/settings.local.json` (sentinel ceremony, blocks
  W1 landing) makes this script — a process write, not a tool write —
  the only writer of the overlay. This script does not and cannot
  enforce P1 itself; it relies on it for the escalation-ladder closure.
- **D3 — the boot banner derives from the resolver, not the marker.**
  The marker/snapshot file is decoration + restore-state only. `status`
  reconciles marker vs `_lib.effective_config.resolve_settings()` and
  REPORTS disagreement instead of picking a side.

## State model (W0 decisions — fixed, do not revisit)

Marker AND snapshot live in ONE file, `<project>/.claude/state/night-mode.json`
(gitignored via the `.claude/state/` entry), same filesystem as the
settings overlay (atomicity; kills the slug-convention ambiguity, W0 T0.7):

    {"version": 1, "mode_written": "acceptEdits", "prev_present": bool,
     "prev_value": null | <mode in _RESTORABLE_MODES>,
     "created_file": bool, "ts": "...Z", "hostname": "..."}

The file is gitignored, unguarded and agent-writable, so on the way IN
(`off`) it is UNTRUSTED input: `_validate_marker` checks the whole
document against that schema — including the consistency rule
`created_file=True implies prev_present=False` — before any field is
acted on (NF-03).

The snapshot is CREATE-ONLY (contract item 4): if the marker exists, `on`
is a no-op (exit 0). Without this, a second `on` would snapshot the value
night-mode itself wrote and `off` would "restore" `acceptEdits` — a
permanently weakened posture.

## Write contract (PLAN-165 §Contrato de escrita — all items mandatory)

1. `_lib.filelock.FileLock` around every whole mutation sequence.
2. Atomic writes only: tempfile in the SAME directory, flush + fsync,
   `os.replace`. Never a truncating in-place write — a torn/truncated
   settings file makes the harness skip the WHOLE file (S286 class).
3. Read-back after replace: reopen + re-parse; mismatch exits non-zero
   WITHOUT touching the marker.
4. Snapshot is create-only (above).
5. Defined ordering: `on` writes settings THEN marker; `off` restores
   settings THEN removes the marker. `status` reconciles and reports.
6. Malformed existing input is fail-CLOSED (exit 2, no write, clear
   diagnostic) — repo doctrine: fail-open on infra, fail-closed on input.
7. Double-`on` / double-`off` are no-ops that exit 0.

## Non-goals with enforcement

No autonomy in CI: `on`/`off` REFUSE (exit 2) whenever the `CI` env var
is present (even empty — fail-closed on presence). `status` stays
available read-only. No tty gate (W0 T0.6: the Bash rail has no tty;
Owner presence is guaranteed by P1 + the CI refusal).

## Audit (NM-05 / NF-07 — two records, one per terminating path)

Every `on`/`off` invocation leaves TWO records on EVERY terminating
path, written as a pair, never one without the other:

1. ONE machine-readable summary line on stdout (stable key=value shape) —
   the operator-facing record, unsigned and terminal-scoped:

       night-mode-event mode=... previous_mode=... result=applied|noop|refused|failed

2. ONE `night_mode_toggled` row on the HMAC-chained audit log, via
   `_emit_audit` -> `_lib.audit_emit.emit_night_mode_toggled` — the
   FORENSIC record PLAN-165 AC-7 requires. The overlay is written by a
   PROCESS, not by a tool, so no PostToolUse observer covers it: without
   this row a posture flip between sessions leaves no signed trace.

The action is REGISTERED (`_KNOWN_ACTIONS`, typed wrapper, deny-by-default
scrub branch, SPEC row — sentinel ceremony `610d9ec`), so the emit is
live. Only the four allowlisted fields travel (`mode`, `previous_mode`,
`result`, `hostname_hash`); never a path, never file content, never the
raw hostname. The emit is best-effort and NEVER raises: observability
must not be able to block or fail the toggle.

`status` emits NEITHER record — it is read-only, not a toggle.

## Round-2 security hardening (see PLAN-165/architect/round-2/)

- NM-01/NM-10 — `off` restores `prev_value` only if it is a string in
  the closed set `_RESTORABLE_MODES`; anything else (wrong type, unknown
  string, `bypassPermissions`) is fail-CLOSED exit 2 with the marker
  left in place. A tampered marker can no longer launder a value into
  the overlay through the Owner's own `off`.
- NM-02 — `on` never snapshots night-mode's own value: if the overlay
  already carries `acceptEdits` with no marker (crash/desync end-state),
  the snapshot is normalized to "no prior override" so `off` restores
  the project posture instead of freezing the weak one.
- NM-04 — `--project-root` is confined to this repository unless the
  test-only `CEO_NIGHT_MODE_TEST_SEAM` env var is set; the target must
  already contain `.claude/settings.json`.
- NM-09 — best-effort parent-directory fsync after `os.replace` and
  after overlay/marker unlink.

## Round-3 security hardening (findings NF-01..NF-04)

- NF-01 — `_RESTORABLE_MODES` excludes `NIGHT_MODE` itself. `cmd_on`'s
  desync normalization guarantees a healthy marker never carries
  night-mode's own value, so admitting it could only ever admit a
  TAMPERED value — and honoring it re-armed `acceptEdits` while REMOVING
  the marker, leaving the posture armed with every later `off` a forever
  no-op. `cmd_off` applies the same normalization symmetrically as a
  second layer.
- NF-02 — the restorable set is DERIVED from
  `_HARNESS_PERMISSION_MODES`, the CLI's real `--permission-mode` enum,
  instead of hand-listed: the hand-listed set carried a mode the harness
  does not have (`default`) and omitted one it does (`dontAsk`), so a
  legitimate `dontAsk` overlay was snapshotted by `on` and then refused
  by `off` FOREVER with `acceptEdits` left armed — fail-closed landing on
  the permissive side. `off --discard-snapshot` is the documented,
  non-restoring recovery from every fail-closed refusal, referenced in
  every refusal diagnostic.
- NF-03 — `_validate_marker` validates the marker as a WHOLE DOCUMENT
  before ANY field is acted on (version, mode_written, both booleans,
  prev_value, and the `created_file=True implies prev_present=False`
  consistency rule). Validating `prev_value` alone left the overlay
  `os.unlink` branch reachable from a planted `created_file` — silent
  data loss on an exit-0 `result=applied` path.
- NF-04 — the one-summary-per-terminating-path requirement (and the P2
  audit emit that lands beside it) is asserted STRUCTURALLY by an `ast`
  oracle in `tests/test_night_mode.py`, not just described in prose.

## Round-4 security hardening (findings NF-05..NF-06)

One class, two surfaces: values from the two gitignored documents
(`settings.local.json`, `.claude/state/night-mode.json`) were echoed into
LINE-ORIENTED records without collapsing line breaks, so whoever can write
either file forges whole extra lines in records the Owner and parsers
trust.

- NF-05 — `cmd_on`'s success line interpolated `previous` (the overlay's
  RAW `permissions.defaultMode`) with neither `_bounded_repr` nor
  `_summary_token`, the only untrusted echo in the file that did. A `\n`
  in that value made ONE `on` emit TWO `night-mode-event ` rows, the
  forged one claiming `result=applied`; a 200k-char value emitted 200k
  bytes. It now goes through `_bounded_repr` like every sibling.
- NF-06 — `cmd_status` never ran `_validate_marker` and printed
  `host=` / `ts=` raw, and `_validate_marker` never checked those two
  fields at all. So a planted `hostname` injected arbitrary status lines
  (a forged `reconciliation:` verdict landing BEFORE the true one), and
  `status` reported "AGREE — night-mode ON" for the very marker `off`
  refuses with exit 2 — the reporter blessing what the writer rejects.
  Now: `ts`/`hostname` are type-, length- and control-char-checked as part
  of the whole document (`_invalid_bounded_string`), `status` RUNS the
  validator and renders "PRESENT but INVALID (<field>)" with a DISAGREE
  verdict for a rejected marker, every untrusted echo is bounded, and the
  report is emitted through `_one_line` so no future field can forge a
  record.

## Round-3 RE-REVIEW hardening (findings NF-07, NF-09)

- NF-07 — the `night_mode_toggled` action was registered, SPEC'd and
  documented in signed surfaces, with ZERO production callers: a
  registered-and-empty action, and three published claims that were
  false. `_emit_audit` is now the sibling of every `_summary` call (see
  `## Audit` above), so the signed claim "emitted on EVERY terminating
  path of on/off" is true of this build. The `ast` oracle pins the PAIR,
  not just the summary — a later refactor that drops one of the two is a
  test failure, not a silent regression.
- NF-09 — `off` on the route where the overlay had ALREADY been removed
  by hand wrote nothing, then reported `restored to '<snapshot>'` with
  `result=applied` on both records. It now reports `absent` / `noop` and
  says plainly that nothing was restored. The bug was harmless while the
  record was only a stdout line; with NF-07 wired it would have put a
  false restore into the HMAC chain, which is why the two fixes belong in
  one commit.

- NF-08b — the script refuses to run unless the file it was invoked as IS
  `<repo>/.claude/scripts/night-mode.py`. Round 2 of the cross-vendor
  review found that the Bash matcher guarding this toggle recognises
  SPELLINGS, and an alias exists to have a different one: `ln -s
  <repo>/.claude/scripts/night-mode.py /tmp/nm && python3 /tmp/nm on`
  armed the posture (measured, `result=applied`), because
  `Path(__file__).resolve()` follows the link back into the repository.
  Re-probing widened the class — a renamed copy inside the repo
  (`.claude/scripts/nm2.py`) armed it too, and no rule about `ln` would
  have caught that. The guard is here rather than in the hook because it
  holds however the alias was created and even if the hook never runs;
  the hook keeps the cheap half (denying `ln` on the toggle) as the
  earlier signal. An ancestor directory being a symlink is NOT an alias
  (`/tmp` -> `/private/tmp`), so ancestors are resolved separately.

Exit codes:
    0 — success or idempotent no-op
    1 — read-back mismatch / post-write verification failure
    2 — usage error, CI refusal, alias/relocated invocation (NF-08b),
        root confinement (NM-04), tampered or malformed marker (NM-01 /
        NF-01..NF-03 / NF-06), or malformed input (all fail-closed).
        Recover an armed posture from any of these with
        `off --discard-snapshot`.

Stdlib-only; Python >= 3.9.
"""

from __future__ import annotations

import argparse
import copy
import hashlib
import json
import os
import socket
import stat
import sys
import tempfile
from datetime import datetime, timezone
from pathlib import Path
from typing import Any, Dict, List, Optional, Tuple

REPO_ROOT = Path(__file__).resolve().parents[2]

# NF-08b — the path this script was INVOKED as, before any symlink is
# followed. Captured at import so it cannot depend on a later `os.chdir`;
# `absolute()` deliberately does NOT resolve links (that is the whole point —
# `REPO_ROOT` above already has the resolved form).
_INVOKED_SELF = Path(__file__).absolute()

# The one relative location this script may legitimately be executed from.
_CANONICAL_SELF_PARTS = (".claude", "scripts", "night-mode.py")

# The ONLY mode `on` ever writes (PLAN-165 D1 — bypassPermissions was cut
# in review; do not add a mode flag).
NIGHT_MODE = "acceptEdits"

# The harness's REAL `--permission-mode` enum — verified against
# `claude --help` on the pinned CLI (2026-08-03). NF-02 (round-3 review):
# the restorable set below is DERIVED from this enum instead of being
# hand-listed, because a hand-listed set drifted BOTH ways at once — it
# carried `default` (never a harness mode) and OMITTED `dontAsk` (a legal
# one). The omission was the dangerous half: an Owner whose overlay
# legitimately carried `dontAsk` had it snapshotted by `on`, and then every
# `off` refused forever with `acceptEdits` left armed — a fail-closed gate
# landing on the PERMISSIVE side. If the CLI gains a mode, update THIS
# constant; the derivation and the diagnostics follow automatically.
_HARNESS_PERMISSION_MODES = frozenset(
    {"acceptEdits", "auto", "bypassPermissions", "manual", "dontAsk", "plan"}
)

# NM-01 / NF-01 / NF-02 — closed set of modes `off` may restore. Derived,
# with exactly two exclusions, both load-bearing:
#
# - `bypassPermissions` (D1): present in ANY settings layer it trips
#   `TAMPER_PERMISSION_BYPASS` (`_lib/effective_config.py`) and turns
#   `/ceo-boot` red by design. night-mode must never be the thing that
#   writes it back — not even under the name "restoring".
# - `NIGHT_MODE` (`acceptEdits`, NF-01): cmd_on's desync normalization
#   guarantees that a HEALTHY marker never carries night-mode's own value
#   as `prev_value`. Admitting it to the set could therefore only ever
#   admit a TAMPERED value — and honoring it produces the worst end-state
#   this script has: `off` re-writes `acceptEdits` into the overlay,
#   REMOVES the marker, and exits 0, leaving the posture armed with no
#   marker, so every later `off` is a forever no-op.
#
# The marker is gitignored, unguarded, agent-writable state; a `prev_value`
# outside this set is evidence of tampering (or of a mode enum this build
# does not know), so restore fails CLOSED — with `off --discard-snapshot`
# as the documented, non-restoring way out (NF-02).
_RESTORABLE_MODES = _HARNESS_PERMISSION_MODES - {"bypassPermissions", NIGHT_MODE}

# NF-02 — the sanctioned exit from EVERY fail-closed refusal in `off`. A
# refusal must never strand the operator with the posture armed and no way
# to disarm it short of hand-editing two gitignored files.
_DISCARD_HINT = (
    "Recovery: 'night-mode off --discard-snapshot' removes the local "
    "defaultMode override AND the marker WITHOUT honoring prev_value, and "
    "prints exactly what it discarded."
)

# NM-04 — test-only escape hatch for the --project-root confinement.
# Set ONLY by the test suite (isolated tmp trees under TestEnvContext).
_TEST_SEAM_ENV = "CEO_NIGHT_MODE_TEST_SEAM"

MARKER_VERSION = 1

_EPILOG = (
    "Audit (NM-05/NF-07): every on/off invocation leaves TWO records on "
    "EVERY terminating path — one machine-readable summary line on stdout "
    "('night-mode-event mode=... previous_mode=... "
    "result=applied|noop|refused|failed') and one forensic "
    "'night_mode_toggled' row on the HMAC-chained audit log (registered "
    "action + typed wrapper, sentinel ceremony 610d9ec). Only mode, "
    "previous_mode, result and a hashed hostname travel — never a path, "
    "never file content, never the raw hostname; the emit is best-effort "
    "and never blocks the toggle. 'status' emits neither (read-only). "
    "Refuses on/off when the CI env var is set (PLAN-165 AC-11). "
    "Recovery (NF-02): 'off --discard-snapshot' is the sanctioned exit from "
    "every fail-closed refusal — it removes the local defaultMode override "
    "AND the marker WITHOUT honoring the snapshot's prev_value, printing "
    "exactly what it discarded, and it also disarms the "
    "armed-without-marker state where plain 'off' is a no-op. A refusal "
    "must never leave the posture armed with no way to disarm it. "
    "--project-root is a TEST-ONLY seam confined to this repository "
    "(NM-04); the test-only CEO_NIGHT_MODE_TEST_SEAM env var lifts the "
    "confinement for isolated test trees, and the target must already "
    "contain .claude/settings.json."
)


# --------------------------------------------------------------------------- #
# Path resolution — anchored in FUNCTIONS, not module-level literals, so a
# test's --project-root (or a patched env) cannot be defeated by an
# import-time constant (PLAN-165 T1.3 note).
# --------------------------------------------------------------------------- #

# Bind extracted implementation to this module global namespace.
_hooks_dir = str(REPO_ROOT / ".claude" / "hooks")
if _hooks_dir not in sys.path:
    sys.path.insert(0, _hooks_dir)
from _lib._night_mode_parts import install as _install_parts
_install_parts(globals(), ("helpers", "toggles"))

def _local_layer(resolved: Dict[str, Any]) -> Dict[str, Any]:
    for layer in resolved.get("layers", []):
        if isinstance(layer, dict) and layer.get("name") == "local":
            return layer
    return {}


def cmd_status(root: Path) -> int:
    """Reconcile marker vs resolver and REPORT disagreement (D3 + contract 5).

    Read-only; always exits 0. The posture line derives from
    `_lib.effective_config.resolve_settings()` — the same resolver the
    tamper tripwires use — never from the marker alone.

    NF-06 (round-4): this command RUNS `_validate_marker` and renders its
    verdict. It used to print `host=` / `ts=` raw and reconcile a marker it
    never validated, so it reported "AGREE — night-mode ON" for the very
    document `off` refuses with exit 2 — status blessed what the writer
    rejects, and a planted `hostname` forged extra lines (a fake
    `reconciliation:` verdict landing BEFORE the true one). Now: every
    untrusted echo goes through `_bounded_repr`, an invalid marker reads
    "PRESENT but INVALID (<field>)" and can never reach an AGREE verdict,
    and every rendered line is collapsed with `_one_line` so no future echo
    can forge a record either.
    """
    hooks_dir = str(REPO_ROOT / ".claude" / "hooks")
    if hooks_dir not in sys.path:
        sys.path.insert(0, hooks_dir)
    from _lib import effective_config  # noqa: E402

    resolved = effective_config.resolve_settings(str(root))
    effective = resolved.get("effective") or {}
    permissions = effective.get("permissions")
    eff_mode = permissions.get("defaultMode") if isinstance(permissions, dict) else None
    eff_layer = (resolved.get("sources") or {}).get("permissions", "(none)")

    lines: List[str] = ["## night-mode status"]
    lines.append(
        "effective permissions.defaultMode: {0} "
        "(layer: {1}; resolver: _lib.effective_config)".format(
            # NF-06: bounded — the winning value can come from the overlay.
            _bounded_repr(eff_mode), eff_layer,
        )
    )
    if not resolved.get("ok", True):
        lines.append(f"resolver errors: {_bounded_repr(resolved.get('errors'))}")

    # What the LOCAL overlay itself says (the layer night-mode writes).
    local = _local_layer(resolved)
    local_data = local.get("data") if isinstance(local.get("data"), dict) else {}
    local_perms = local_data.get("permissions")
    local_mode = local_perms.get("defaultMode") if isinstance(local_perms, dict) else None
    lines.append(
        "local overlay defaultMode: {0} (exists={1}, parse_ok={2})".format(
            _bounded_repr(local_mode),
            bool(local.get("exists")),
            bool(local.get("ok")),
        )
    )

    marker_file = marker_path(root)
    marker: Optional[Dict[str, Any]] = None
    marker_diag: Optional[str] = None
    marker_invalid: Optional[str] = None
    if marker_file.exists():
        marker, marker_diag = _load_json_fail_closed(marker_file, "night-mode marker")

    if marker is not None:
        # NF-06: the SAME whole-document gate `off` applies. A marker status
        # blesses must be a marker the writer would accept.
        marker_invalid = _validate_marker(marker)
        lines.append(
            "marker: {0} (age {1}, mode_written={2}, host={3}, ts={4})".format(
                "PRESENT" if marker_invalid is None else "PRESENT but INVALID",
                _marker_age_str(str(marker.get("ts"))),
                _bounded_repr(marker.get("mode_written")),
                _bounded_repr(marker.get("hostname")),
                _bounded_repr(marker.get("ts")),
            )
        )
        if marker_invalid is not None:
            lines.append(f"marker validation: {marker_invalid}")
    elif marker_diag is not None:
        lines.append(f"marker: PRESENT but unreadable — {marker_diag}")
    else:
        lines.append("marker: absent (night-mode OFF)")

    # Reconciliation — report, never repair (contract item 5).
    if marker is not None and marker_invalid is not None:
        # NF-06: an INVALID marker reconciles nothing. Reporting AGREE here
        # (round-3 behavior) told the Owner "night-mode ON" about a document
        # `off` refuses with exit 2 — and the posture the overlay carries is
        # then unexplained by any trustworthy record.
        verdict = (
            "DISAGREE — the marker is PRESENT but INVALID ({0}); it is not a "
            "document night-mode wrote, so night-mode state cannot be "
            "reconciled from it. 'off' refuses this marker (exit 2); recover "
            "with 'off --discard-snapshot'.".format(marker_invalid)
        )
    elif marker is not None:
        if local_mode == marker.get("mode_written"):
            verdict = "AGREE — marker and local overlay match (night-mode ON)"
        else:
            verdict = (
                "DISAGREE — marker says night-mode wrote "
                "{0} but the local overlay has {1} (crash between writes, or "
                "hand edit). Reconcile by hand, then 'off' or 'on'.".format(
                    _bounded_repr(marker.get("mode_written")),
                    _bounded_repr(local_mode),
                )
            )
    elif marker_diag is not None:
        verdict = (
            "DISAGREE — marker exists but cannot be parsed; treat night-mode "
            "state as unknown and reconcile by hand."
        )
    else:
        if local_mode is None:
            verdict = "AGREE — no marker and the local overlay sets no defaultMode (night-mode OFF)"
        elif local_mode == NIGHT_MODE:
            # AC-5 crash class: settings armed but the marker never landed
            # (crash between the two writes) — or a hand-arm. Either way
            # night-mode did not record it; report, never repair.
            verdict = (
                f"DISAGREE — no marker, but the local overlay is armed with "
                f"defaultMode={NIGHT_MODE!r} (crash between settings and "
                "marker writes, or a hand edit). night-mode did not record "
                "this; reconcile by hand."
            )
        else:
            verdict = (
                "AGREE — night-mode OFF; note: the local overlay hand-sets "
                "defaultMode={0} outside night-mode's management (posture "
                "visibility is the /ceo-boot banner's job).".format(
                    _bounded_repr(local_mode)
                )
            )
    lines.append(f"reconciliation: {verdict}")

    # NF-06: one rendered line per record, enforced at the single point where
    # the report is emitted. Every untrusted value above is already bounded +
    # repr-escaped; this is the structural backstop, so a future field echoed
    # without `_bounded_repr` still cannot forge a second `reconciliation:`
    # (or `marker:`) line.
    print("\n".join(_one_line(line) for line in lines))
    return 0


# --------------------------------------------------------------------------- #
# CLI
# --------------------------------------------------------------------------- #
def main(argv: Optional[List[str]] = None) -> int:
    parser = argparse.ArgumentParser(
        prog="night-mode",
        description=(
            "Toggle the per-machine autonomy posture "
            "(permissions.defaultMode=acceptEdits in .claude/settings.local.json) "
            "for the NEXT session. PLAN-165."
        ),
        epilog=_EPILOG,
    )
    parser.add_argument(
        "command",
        choices=("on", "off", "status"),
        help="on: arm acceptEdits for the next session; off: restore the "
             "snapshot; status: reconcile marker vs resolved settings",
    )
    parser.add_argument(
        "--discard-snapshot",
        dest="discard_snapshot",
        action="store_true",
        help="with 'off' ONLY — recovery from a fail-closed refusal: remove "
             "the local defaultMode override AND the marker WITHOUT honoring "
             "the snapshot's prev_value, printing exactly what was "
             "discarded. Also disarms the armed-without-marker state, where "
             "plain 'off' is a no-op (NF-02).",
    )
    parser.add_argument(
        "--project-root",
        dest="project_root",
        default=None,
        help=argparse.SUPPRESS,  # test seam only
    )
    args = parser.parse_args(argv)

    self_diag = _check_self_path()
    if self_diag is not None:
        # NF-08b: BEFORE any other dispatch, including the root confinement —
        # a script running from an alias has no business resolving a target.
        # `status` is refused too, matching `_e4`'s scope decision: the SCRIPT
        # is the surface, and a read-only carve-out would key a PERMISSIVE
        # branch off argv parsing.
        sys.stderr.write(f"night-mode: {self_diag}\n")
        if args.command in ("on", "off"):
            # A refusal is a terminating path of on/off (NM-05/NF-07), so it
            # leaves BOTH records. The audit emit resolves through REPO_ROOT,
            # i.e. the REAL repository the alias points into — which is
            # exactly where the attempt should be recorded.
            _summary(mode="none", previous_mode="none", result="refused")
            _emit_audit("other", "other", "refused")
        return 2

    if args.discard_snapshot and args.command != "off":
        sys.stderr.write(
            "night-mode: --discard-snapshot is only valid with 'off' (got "
            f"{args.command!r}); it is the recovery path for a refused "
            "restore, not a mode of arming or reporting.\n"
        )
        if args.command == "on":
            # Pre-dispatch refusals are terminating paths of on/off too —
            # the SPEC row says EVERY one leaves a `night_mode_toggled`
            # record, so the pair travels here as well (NF-07).
            _summary(mode="none", previous_mode="none", result="refused")
            _emit_audit("other", "other", "refused")
        return 2

    root = Path(args.project_root).resolve() if args.project_root else REPO_ROOT

    diag = _validate_root(root)
    if diag is not None:
        # NM-04: fail-closed on an unconfined target, BEFORE any dispatch.
        sys.stderr.write(f"night-mode: {diag}\n")
        if args.command in ("on", "off"):
            _summary(mode="none", previous_mode="none", result="refused")
            _emit_audit("other", "other", "refused")
        return 2

    try:
        if args.command == "on":
            return cmd_on(root)
        if args.command == "off":
            if args.discard_snapshot:
                return cmd_off_discard_snapshot(root)
            return cmd_off(root)
        return cmd_status(root)
    except Exception as exc:  # noqa: BLE001 — CLI must exit, not traceback
        sys.stderr.write(
            f"night-mode: internal error ({exc.__class__.__name__}: {exc})\n"
        )
        if args.command in ("on", "off"):
            # NM-05/NF-07: even the catch-all leaves BOTH records.
            #
            # Lock contention is a REFUSAL, not a failure: nothing was
            # attempted, another holder owns the mutation sequence, and this
            # path exits 2 — which the ceremony's result table maps to
            # `refused` (`failed` is reserved for exit 1, "a write was
            # attempted and lost"). NF-11(b) flagged the old blanket
            # `failed` as diverging from that table. ONE `result` feeds BOTH
            # records, so the operator-facing line and the signed row can
            # never disagree about the same invocation (the NF-09 lesson).
            #
            # Classifying must not itself be able to raise: the import sits
            # in its own try, and an unimportable `_lib` degrades to
            # `failed` — the conservative value, since a build that cannot
            # import its own lock is not refusing, it is broken.
            result = "failed"
            try:
                hooks_dir = str(REPO_ROOT / ".claude" / "hooks")
                if hooks_dir not in sys.path:
                    sys.path.insert(0, hooks_dir)
                from _lib.filelock import FileLockTimeout  # noqa: E402

                if isinstance(exc, FileLockTimeout):
                    result = "refused"
            except Exception:  # noqa: BLE001 — classification is best-effort
                pass
            _summary(mode="none", previous_mode="none", result=result)
            _emit_audit("other", "other", result)
        return 2


if __name__ == "__main__":
    sys.exit(main())
