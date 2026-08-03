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

## Observability (NM-05 — interim record until P2 lands)

Every `on`/`off` invocation prints ONE machine-readable summary line on
EVERY terminating path (stdout, stable key=value shape):

    night-mode-event mode=... previous_mode=... result=applied|noop|refused|failed

This script deliberately does NOT emit a `night_mode_toggled` audit
event: the action is unregistered until the P2 sentinel ceremony lands
(`_KNOWN_ACTIONS` entry + typed wrapper + schema bump), and emitting an
unregistered action is exactly what the reality-ledger (detector 6) and
audit-registry-coverage guards red on — those guards are correct. The
forensic audit trail arrives WITH the P2 ceremony; the one-line summary
is the interim record.

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

Exit codes:
    0 — success or idempotent no-op
    1 — read-back mismatch / post-write verification failure
    2 — usage error, CI refusal, root confinement (NM-04), tampered or
        malformed marker (NM-01 / NF-01..NF-03 / NF-06), or malformed
        input (all fail-closed). Recover an armed posture from any of
        these with `off --discard-snapshot`.

Stdlib-only; Python >= 3.9.
"""

from __future__ import annotations

import argparse
import copy
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
    "Observability (NM-05): every on/off invocation prints one "
    "machine-readable summary line on EVERY terminating path — "
    "'night-mode-event mode=... previous_mode=... "
    "result=applied|noop|refused|failed'. This is the interim record: the "
    "forensic 'night_mode_toggled' audit event ships WITH the P2 sentinel "
    "ceremony (registered action + typed wrapper); this script deliberately "
    "does not emit it before P2 (an unregistered emit reds the "
    "reality-ledger and audit-registry guards, and those guards are "
    "correct). Refuses on/off when the CI env var is set (PLAN-165 AC-11). "
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
def settings_local_path(root: Path) -> Path:
    """The per-machine, gitignored settings overlay."""
    return root / ".claude" / "settings.local.json"


def marker_path(root: Path) -> Path:
    """Single marker+snapshot file (W0 T0.7: same tree as the settings)."""
    return root / ".claude" / "state" / "night-mode.json"


def lock_path(root: Path) -> Path:
    """Sibling lock file guarding the whole mutation sequence."""
    return root / ".claude" / "state" / "night-mode.lock"


def _import_filelock() -> Any:
    """Import `_lib.filelock` from THIS script's repo (not --project-root)."""
    hooks_dir = str(REPO_ROOT / ".claude" / "hooks")
    if hooks_dir not in sys.path:
        sys.path.insert(0, hooks_dir)
    from _lib.filelock import FileLock  # noqa: E402

    return FileLock


# --------------------------------------------------------------------------- #
# JSON IO — fail-closed reads, atomic verified writes.
# --------------------------------------------------------------------------- #
def _load_json_fail_closed(path: Path, what: str) -> Tuple[Optional[Dict[str, Any]], Optional[str]]:
    """Load *path* as a JSON object.

    Returns (doc, None) on success, (None, None) when the file is absent,
    and (None, diagnostic) when the file exists but cannot be parsed as a
    JSON object — the caller MUST treat that as fail-closed (exit 2, no
    write). Contract item 6.
    """
    if not path.exists():
        return None, None
    try:
        raw = path.read_text(encoding="utf-8")
    except (OSError, UnicodeDecodeError) as exc:
        return None, f"{what} at {path} is unreadable ({exc.__class__.__name__}: {exc})"
    try:
        doc = json.loads(raw)
    except ValueError as exc:
        return None, (
            f"{what} at {path} is not valid JSON ({exc}). "
            f"Refusing to rewrite or 'fix' it (fail-closed on input) — "
            f"repair it by hand, then re-run."
        )
    if not isinstance(doc, dict):
        return None, (
            f"{what} at {path} parses but is not a JSON object "
            f"(top-level {type(doc).__name__}). Refusing to merge (fail-closed)."
        )
    return doc, None


def _fsync_dir(path: Path) -> None:
    """NM-09 — best-effort parent-directory fsync.

    `os.replace`/`os.unlink` mutate the DIRECTORY; fsyncing only the file
    fd leaves the rename itself lose-able on power loss (the torn-state
    class contract item 2 cites, S286). Durability here is best-effort:
    any failure is swallowed — it must never break the operation.
    """
    fd = -1
    try:
        fd = os.open(str(path), os.O_RDONLY)
        os.fsync(fd)
    except OSError:
        pass
    finally:
        if fd >= 0:
            try:
                os.close(fd)
            except OSError:
                pass


def _atomic_write_json(target: Path, doc: Dict[str, Any]) -> None:
    """Write *doc* atomically: tempfile in the SAME dir, fsync, os.replace.

    Never truncates in place (contract item 2 — a torn settings file makes
    the harness skip the whole file, the S286 failure class). Preserves the
    permission bits of a pre-existing target; new files keep mkstemp's 0600.
    Raises OSError to the caller on failure (nothing partially replaced).
    """
    target.parent.mkdir(parents=True, exist_ok=True)
    payload = json.dumps(doc, indent=2, ensure_ascii=False, sort_keys=False) + "\n"
    prev_mode: Optional[int] = None
    if target.exists():
        try:
            prev_mode = stat.S_IMODE(target.stat().st_mode)
        except OSError:
            prev_mode = None
    fd, tmp_name = tempfile.mkstemp(
        prefix=target.name + ".", suffix=".tmp", dir=str(target.parent)
    )
    try:
        with os.fdopen(fd, "w", encoding="utf-8") as fh:
            fh.write(payload)
            fh.flush()
            os.fsync(fh.fileno())
        if prev_mode is not None:
            os.chmod(tmp_name, prev_mode)
        os.replace(tmp_name, target)
        _fsync_dir(target.parent)  # NM-09: make the rename durable
    except BaseException:
        try:
            os.unlink(tmp_name)
        except OSError:
            pass
        raise


def _read_back_matches(target: Path, expected: Dict[str, Any]) -> bool:
    """Contract item 3: reopen + re-parse *target*; True iff it equals
    *expected* structurally. Any read/parse failure counts as mismatch."""
    try:
        got = json.loads(target.read_text(encoding="utf-8"))
    except (OSError, ValueError, UnicodeDecodeError):
        return False
    return got == expected


# --------------------------------------------------------------------------- #
# Guards
# --------------------------------------------------------------------------- #
def _refuse_if_ci() -> Optional[int]:
    """PLAN-165 AC-11 — no autonomy toggling in CI / headless runners.

    Fail-closed on PRESENCE of the `CI` env var (even empty): a runner that
    sets `CI=` is still a runner. Returns exit code 2 when refusing.
    """
    if "CI" in os.environ:
        sys.stderr.write(
            "night-mode: refusing to toggle autonomy posture — the CI "
            "environment variable is set (PLAN-165 non-goal: no autonomy "
            "on CI/headless runners; AC-11).\n"
        )
        return 2
    return None


def _hostname() -> str:
    try:
        return socket.gethostname()
    except OSError:
        return "unknown-host"


def _utc_now_iso() -> str:
    return datetime.now(timezone.utc).strftime("%Y-%m-%dT%H:%M:%SZ")


def _marker_age_str(ts: str) -> str:
    """Human age of the marker timestamp; degrades to 'unknown age'."""
    try:
        then = datetime.strptime(ts, "%Y-%m-%dT%H:%M:%SZ").replace(tzinfo=timezone.utc)
    except (ValueError, TypeError):
        return "unknown age"
    seconds = (datetime.now(timezone.utc) - then).total_seconds()
    if seconds < 0:
        return "clock skew (marker in the future)"
    if seconds < 90:
        return f"{int(seconds)}s"
    if seconds < 5400:
        return f"{seconds / 60.0:.0f}m"
    return f"{seconds / 3600.0:.1f}h"


def _bounded_repr(value: Any, limit: int = 200) -> str:
    """`repr(value)`, truncated to *limit* characters.

    Every echo of a marker field goes through here: the marker is
    UNTRUSTED input (gitignored, unguarded, agent-writable), so a planted
    document may carry a megabyte-long string. Diagnostics must be loud
    about what they rejected AND bounded.
    """
    try:
        text = repr(value)
    except Exception:  # noqa: BLE001 — a diagnostic must never raise
        return "<unrepresentable>"
    if len(text) > limit:
        return "{0}...<truncated {1} chars>".format(text[:limit], len(text) - limit)
    return text


# Every character Python's own `str.splitlines()` treats as a line boundary,
# plus TAB. NF-05/NF-06 (round-4): `status` renders a LINE-ORIENTED record
# (`marker:`, `reconciliation:` …) that the Owner and log parsers read one
# line at a time, and the marker + overlay it echoes are gitignored,
# agent-writable documents. A single planted line break forges a whole extra
# record — including a fake `reconciliation:` verdict that lands BEFORE the
# true one. The exotic members (VT, FF, FS, GS, RS, NEL, LS, PS) are here
# because `str.splitlines()` splits on them too: a consumer that splits
# would see two records even where a raw terminal shows one. Written as
# ESCAPES on purpose — a literal U+2028 in the source is invisible.
_LINE_BREAKS = "\n\r\v\f\x1c\x1d\x1e\x85\u2028\u2029\t"
_ONE_LINE_TABLE = {ord(ch): " " for ch in _LINE_BREAKS}


def _one_line(text: Any) -> str:
    """Collapse every line-boundary character (and TAB) to a single space.

    Applied to whole rendered lines, so no field a future edit echoes into
    `status` can forge an extra record even if that echo forgets
    `_bounded_repr` (NF-06 defense in depth — the class, not the instance).
    """
    if not isinstance(text, str):
        text = str(text)
    return text.translate(_ONE_LINE_TABLE)


def _invalid_bounded_string(value: Any, field: str, limit: int) -> Optional[str]:
    """Diagnostic if *value* is not a bounded, control-char-free string.

    NF-06 (round-4): `ts` and `hostname` were the two marker fields
    `_validate_marker` never looked at, and `status` printed both RAW. A
    planted `hostname` therefore injected arbitrary lines into the status
    report — including a forged `reconciliation:` verdict rendered ABOVE the
    real one. Both fields are Owner-facing decoration; a control character
    in either is evidence of tampering, so it fails CLOSED like every other
    field of the document.
    """
    if not isinstance(value, str):
        return "field {0!r} is {1}, expected a JSON string".format(
            field, _bounded_repr(value)
        )
    if not value:
        return "field {0!r} is an empty string".format(field)
    if len(value) > limit:
        return "field {0!r} is {1} chars long, over the {2}-char bound".format(
            field, len(value), limit
        )
    bad = [ch for ch in value if ch in _LINE_BREAKS or ord(ch) < 0x20 or ord(ch) == 0x7F]
    if bad:
        return (
            "field {0!r} contains control character(s) {1} — a marker field "
            "night-mode wrote can never carry one, and this field is echoed "
            "on a line-oriented surface (NF-06)".format(
                field, _bounded_repr("".join(sorted(set(bad))))
            )
        )
    return None


# --------------------------------------------------------------------------- #
# NF-03 — whole-document marker validation (fail-CLOSED on input).
# --------------------------------------------------------------------------- #
def _validate_marker(doc: Any) -> Optional[str]:
    """Validate the marker as a WHOLE DOCUMENT; None means healthy.

    Returns a diagnostic naming the offending field otherwise. The caller
    MUST treat any diagnostic as fail-CLOSED (exit 2, marker left in place,
    nothing acted on) — contract item 6.

    Round-2 validated `prev_value` ALONE. Every other field
    (`prev_present`, `created_file`, `mode_written`, `version`) was still
    trusted from the same untrusted document, and that was exploitable
    (NF-03): a planted `created_file=true` + `prev_present=false` made
    `off` `os.unlink` an overlay night-mode did NOT create — silent data
    loss on an exit-0 `result=applied` path. Per-field validation alone is
    still not enough: the CONSISTENCY rule (`created_file=True` implies
    `prev_present=False` — night-mode creates the overlay only when there
    was no overlay, hence no prior value) is what makes the unlink branch
    safe to reach at all.
    """
    if not isinstance(doc, dict):
        return "marker is not a JSON object (top-level {0})".format(
            type(doc).__name__
        )

    version = doc.get("version")
    # `isinstance(version, bool)` first: in Python `True == 1`, so a planted
    # `"version": true` would otherwise pass an `== MARKER_VERSION` check.
    if isinstance(version, bool) or version != MARKER_VERSION:
        return (
            "field 'version' is {0}, expected {1!r} — this marker was not "
            "written by this build of night-mode".format(
                _bounded_repr(version), MARKER_VERSION
            )
        )

    mode_written = doc.get("mode_written")
    if mode_written != NIGHT_MODE:
        return (
            "field 'mode_written' is {0}, expected {1!r} — night-mode only "
            "ever writes {1!r}".format(_bounded_repr(mode_written), NIGHT_MODE)
        )

    for field in ("prev_present", "created_file"):
        if field not in doc:
            return "field {0!r} is missing".format(field)
        if not isinstance(doc[field], bool):
            return "field {0!r} is {1}, expected a JSON boolean".format(
                field, _bounded_repr(doc[field])
            )

    prev_present = doc["prev_present"]
    prev_value = doc.get("prev_value")
    if prev_present:
        if not (isinstance(prev_value, str) and prev_value in _RESTORABLE_MODES):
            return (
                "field 'prev_value' is {0}, which is not a string in the "
                "closed set of restorable modes {1} (derived from the harness "
                "--permission-mode enum minus 'bypassPermissions' and {2!r}; "
                "NM-01 / NF-01 / NF-02)".format(
                    _bounded_repr(prev_value),
                    sorted(_RESTORABLE_MODES),
                    NIGHT_MODE,
                )
            )
    elif prev_value is not None:
        return (
            "field 'prev_value' is {0} while 'prev_present' is false — a "
            "healthy marker records prev_value=null when there was no prior "
            "override".format(_bounded_repr(prev_value))
        )

    if doc["created_file"] and prev_present:
        return (
            "fields 'created_file'=true and 'prev_present'=true are mutually "
            "inconsistent — night-mode creates the overlay only when there "
            "was no overlay, hence no prior value. Honoring this pair would "
            "unlink a file night-mode did not create (NF-03)"
        )

    # NF-06 (round-4): `ts` and `hostname` completed the WHOLE-document
    # promise this helper's name makes. Round-3 checked neither — they are
    # "only decoration", but decoration is exactly what `status` PRINTS, and
    # `status` renders a line-oriented report. A planted `hostname` forged
    # arbitrary lines there, including a fake `reconciliation:` verdict
    # rendered ABOVE the true one. Bounds: `ts` is night-mode's own
    # `%Y-%m-%dT%H:%M:%SZ` (20 chars; 32 leaves room for a future
    # fractional-seconds format), `hostname` the DNS maximum of 253.
    for field, limit in (("ts", 32), ("hostname", 253)):
        if field not in doc:
            return "field {0!r} is missing".format(field)
        bad = _invalid_bounded_string(doc[field], field, limit)
        if bad is not None:
            return bad
    return None


# --------------------------------------------------------------------------- #
# Observability — NM-05: one machine-readable line on EVERY terminating path.
# --------------------------------------------------------------------------- #
_SUMMARY_TOKEN_SAFE = frozenset(
    "abcdefghijklmnopqrstuvwxyzABCDEFGHIJKLMNOPQRSTUVWXYZ0123456789_.:-"
)


def _summary_token(value: Any, limit: int = 32) -> str:
    """Coerce *value* into ONE safe token for the key=value summary line.

    Some summary values originate in the untrusted marker. A planted
    `prev_value` carrying a space would forge an extra field in the
    machine-readable record, and one carrying a newline would forge an
    extra LINE. Unsafe characters collapse to '_'; the result is bounded
    and never empty.
    """
    text = value if isinstance(value, str) else str(value)
    text = "".join(ch if ch in _SUMMARY_TOKEN_SAFE else "_" for ch in text)
    if not text:
        return "none"
    return text[:limit]


def _summary(mode: str, previous_mode: str, result: str) -> None:
    """Print the NM-05 one-line summary (stdout, stable key=value shape).

    `result` is one of: applied | noop | refused | failed. Use 'none' for
    a value that is unknown or not applicable on that path. This is the
    INTERIM record — the forensic `night_mode_toggled` audit event ships
    with the P2 sentinel ceremony (see module docstring); nothing here
    touches `_lib.audit_emit` on purpose (an unregistered emit reds the
    reality-ledger + audit-registry guards, correctly).

    Every value is passed through `_summary_token` — the record must stay
    one parseable line even when a value came from the untrusted marker.
    """
    print(
        "night-mode-event mode={0} previous_mode={1} result={2}".format(
            _summary_token(mode), _summary_token(previous_mode),
            _summary_token(result),
        )
    )


def _validate_root(root: Path) -> Optional[str]:
    """NM-04 — confine --project-root; returns a diagnostic or None.

    Unconfined, `--project-root` is an arbitrary-path posture-write
    primitive: any Bash-capable agent could arm `acceptEdits` in ANY repo
    on the machine, including targets without the P1 deny rule. Reject
    (fail-closed) any target that is not this repository's root or under
    it, unless the test-only `CEO_NIGHT_MODE_TEST_SEAM` env var is set
    (isolated tmp trees in the test suite). In BOTH cases the target must
    already look like an installed project (`.claude/settings.json`
    present) — night-mode never bootstraps a posture into a bare tree.
    """
    if not os.environ.get(_TEST_SEAM_ENV):
        if root != REPO_ROOT and REPO_ROOT not in root.parents:
            return (
                f"--project-root {root} is outside this repository "
                f"({REPO_ROOT}); refusing (NM-04 confinement — the toggle "
                f"only manages THIS repo's overlay). {_TEST_SEAM_ENV} is a "
                "test-only escape hatch for isolated test trees."
            )
    if not (root / ".claude" / "settings.json").is_file():
        return (
            f"target {root} does not contain .claude/settings.json — not an "
            "installed project; refusing to write a posture overlay there "
            "(NM-04)."
        )
    return None


# --------------------------------------------------------------------------- #
# on
# --------------------------------------------------------------------------- #
def cmd_on(root: Path) -> int:
    refused = _refuse_if_ci()
    if refused is not None:
        _summary(mode=NIGHT_MODE, previous_mode="none", result="refused")
        return refused

    FileLock = _import_filelock()
    with FileLock(str(lock_path(root))):
        marker_file = marker_path(root)
        if marker_file.exists():
            # Contract items 4 + 7: marker is CREATE-ONLY; a second `on`
            # must not re-snapshot the value night-mode itself wrote.
            print(
                "night-mode: already ON (marker present at "
                f"{marker_file}) — no-op. Run 'status' to reconcile."
            )
            _summary(mode=NIGHT_MODE, previous_mode="none", result="noop")
            return 0

        settings_file = settings_local_path(root)
        doc, diag = _load_json_fail_closed(settings_file, "settings.local.json")
        if diag is not None:
            sys.stderr.write(f"night-mode: {diag}\n")
            _summary(mode=NIGHT_MODE, previous_mode="none", result="refused")
            return 2
        created_file = doc is None
        if doc is None:
            doc = {}

        permissions = doc.get("permissions")
        if permissions is not None and not isinstance(permissions, dict):
            sys.stderr.write(
                f"night-mode: 'permissions' in {settings_file} is not an "
                f"object (got {type(permissions).__name__}); refusing to "
                "merge (fail-closed on input).\n"
            )
            _summary(mode=NIGHT_MODE, previous_mode="none", result="refused")
            return 2

        prev_present = isinstance(permissions, dict) and "defaultMode" in permissions
        prev_value = permissions["defaultMode"] if prev_present else None
        if prev_present and prev_value == NIGHT_MODE:
            # NM-02 (round-2 security review): the overlay already carries
            # night-mode's OWN value while no marker exists — the AC-5
            # crash/desync end-state (settings armed, marker lost) or a
            # hand-arm. Snapshotting it would make the weak posture
            # permanent: `off` would "restore" acceptEdits forever.
            # night-mode NEVER snapshots its own value — normalize to
            # "no prior override" so `off` falls back to the project
            # layer's ratified posture.
            sys.stderr.write(
                "night-mode: note — desync detected and normalized: the "
                f"local overlay already had defaultMode={NIGHT_MODE!r} with "
                "no marker (crash between writes, or a hand edit). "
                "Recording 'no prior override' so 'off' restores the "
                "project posture instead of re-freezing acceptEdits.\n"
            )
            prev_present = False
            prev_value = None

        # NF-02 note: `on` records the overlay's REAL prior value, including
        # one that `off` will later refuse to restore (a hand-set
        # `bypassPermissions`, or a mode outside this build's enum).
        # Snapshotting the truth is correct; deciding RESTORABILITY is
        # `off`'s closed-set gate, and `off --discard-snapshot` is the
        # documented exit when that gate refuses. `on` never silently
        # rewrites what it found.

        # Deep-merge ONLY permissions.defaultMode — every unrelated
        # top-level key and every unrelated permissions subkey survives.
        new_doc = copy.deepcopy(doc)
        new_permissions = dict(new_doc.get("permissions") or {})
        new_permissions["defaultMode"] = NIGHT_MODE
        new_doc["permissions"] = new_permissions

        # Ordering (contract item 5): settings FIRST, marker second.
        try:
            _atomic_write_json(settings_file, new_doc)
        except OSError as exc:
            sys.stderr.write(
                f"night-mode: failed to write {settings_file} "
                f"({exc.__class__.__name__}: {exc}); nothing changed.\n"
            )
            _summary(mode=NIGHT_MODE, previous_mode="none", result="failed")
            return 1
        if not _read_back_matches(settings_file, new_doc):
            # Contract item 3: verified-write failure — do NOT write the
            # marker; the operator sees a hard failure, not a torn state.
            sys.stderr.write(
                f"night-mode: read-back of {settings_file} does not match "
                "what was written — settings may be torn; marker NOT "
                "created. Inspect the file before retrying.\n"
            )
            _summary(mode=NIGHT_MODE, previous_mode="none", result="failed")
            return 1

        marker = {
            "version": MARKER_VERSION,
            "mode_written": NIGHT_MODE,
            "prev_present": prev_present,
            "prev_value": prev_value,
            "created_file": created_file,
            "ts": _utc_now_iso(),
            "hostname": _hostname(),
        }
        previous = prev_value if prev_present else "absent"
        try:
            _atomic_write_json(marker_file, marker)
        except OSError as exc:
            sys.stderr.write(
                f"night-mode: settings written but marker write failed "
                f"({exc.__class__.__name__}: {exc}). Run 'status' — it will "
                "report the disagreement; re-run 'on' after fixing.\n"
            )
            _summary(mode=NIGHT_MODE, previous_mode=str(previous), result="failed")
            return 1
        if not _read_back_matches(marker_file, marker):
            sys.stderr.write(
                f"night-mode: read-back of {marker_file} does not match; "
                "marker may be torn. Run 'status' to reconcile.\n"
            )
            _summary(mode=NIGHT_MODE, previous_mode=str(previous), result="failed")
            return 1

        print(
            "night-mode: ON — next session starts with "
            "permissions.defaultMode={0!r} (local overlay). Previous local "
            "value: {1}. Disarm with: night-mode off".format(
                NIGHT_MODE,
                # NF-05 (round-4): `previous` is the overlay's RAW
                # defaultMode — untrusted input from a gitignored,
                # agent-writable document, echoed here on a LINE-ORIENTED
                # surface. Interpolated bare, a value carrying '\n' made
                # ONE `on` invocation emit TWO 'night-mode-event ' rows (the
                # forged one claiming result=applied), and a 200k-char value
                # emitted 200k bytes of stdout. `_bounded_repr` escapes the
                # newline (repr) AND bounds the length — the same treatment
                # every other untrusted echo in this file already got.
                _bounded_repr(previous),
            )
        )
        # Summary LAST on every terminating path of on/off (structural rule,
        # asserted by the AST oracle in the test suite — NF-04): the P2
        # ceremony inserts the forensic `_emit_audit` call right here, and a
        # path that returns without it leaves no record.
        _summary(mode=NIGHT_MODE, previous_mode=str(previous), result="applied")
        return 0


# --------------------------------------------------------------------------- #
# off
# --------------------------------------------------------------------------- #
def cmd_off(root: Path) -> int:
    refused = _refuse_if_ci()
    if refused is not None:
        _summary(mode="none", previous_mode="none", result="refused")
        return refused

    FileLock = _import_filelock()
    with FileLock(str(lock_path(root))):
        marker_file = marker_path(root)
        if not marker_file.exists():
            # Contract item 7: idempotent no-op.
            print("night-mode: already OFF (no marker) — no-op.")
            _summary(mode="none", previous_mode="none", result="noop")
            return 0

        marker, diag = _load_json_fail_closed(marker_file, "night-mode marker")
        if diag is not None or marker is None:
            sys.stderr.write(
                f"night-mode: {diag or 'marker unreadable'}\n"
                "night-mode: refusing to guess restore state (fail-closed). "
                f"Inspect the marker and the settings overlay by hand. "
                f"{_DISCARD_HINT}\n"
            )
            _summary(mode="none", previous_mode="none", result="refused")
            return 2

        # NF-03: validate the WHOLE document BEFORE any field is acted on.
        # Round-2 gated only `prev_value`; `prev_present`, `created_file`,
        # `mode_written` and `version` were still trusted from the same
        # untrusted document, and the unlink branch below is reachable from
        # `created_file` alone. One helper, all fields, plus the
        # created_file/prev_present consistency rule. Fail-CLOSED: the
        # marker stays in place as evidence and NOTHING is written.
        invalid = _validate_marker(marker)
        if invalid is not None:
            sys.stderr.write(
                "night-mode: REFUSING to restore — the marker at "
                f"{marker_file} is not a healthy night-mode marker: "
                f"{invalid}. Whole-document validation is fail-CLOSED "
                "(NM-01 / NF-01 / NF-02 / NF-03): no field of a rejected "
                "marker is acted on, the settings overlay is untouched, and "
                f"the marker is left in place as evidence. {_DISCARD_HINT}\n"
            )
            # The marker is rejected, so NOTHING in it — mode_written
            # included — is echoed into the machine-readable record.
            _summary(mode="none", previous_mode="none", result="refused")
            return 2

        # Every field below is now schema-validated: `mode_written` is
        # NIGHT_MODE, both booleans are real booleans, `prev_value` is
        # either None or a string in _RESTORABLE_MODES, and
        # created_file=True implies prev_present=False.
        prev_present = marker["prev_present"]
        prev_value = marker.get("prev_value")
        created_file = marker["created_file"]
        mode_written = marker.get("mode_written")

        if prev_present and prev_value == NIGHT_MODE:
            # NF-01, belt and braces. `_RESTORABLE_MODES` already excludes
            # NIGHT_MODE, so `_validate_marker` rejects this marker above and
            # this branch is unreachable TODAY. It stays because the failure
            # it prevents is the worst one in the script: restoring
            # night-mode's own value re-arms `acceptEdits` in the overlay AND
            # removes the marker, leaving the posture armed with nothing to
            # disarm it. If a future change ever loosens the set, the
            # symmetric normalization — same rule cmd_on applies on the way
            # in — still turns a self-referential snapshot into "remove the
            # override" instead of "re-arm forever". Exercised directly by
            # the test suite with a loosened set.
            sys.stderr.write(
                "night-mode: note — the snapshot's prev_value is night-mode's "
                f"own {NIGHT_MODE!r}, which a healthy marker can never carry "
                "(cmd_on normalizes it away). Treating it as 'no prior "
                "override' and REMOVING the local override instead of "
                "re-arming the weak posture (NF-01).\n"
            )
            prev_present = False
            prev_value = None

        settings_file = settings_local_path(root)
        doc, diag = _load_json_fail_closed(settings_file, "settings.local.json")
        if diag is not None:
            sys.stderr.write(
                f"night-mode: {diag}\n"
                "night-mode: marker left in place (restore not performed). "
                "Repair the overlay JSON by hand first — "
                "'off --discard-snapshot' also refuses to rewrite an overlay "
                "it cannot parse.\n"
            )
            _summary(mode="none", previous_mode=str(mode_written), result="refused")
            return 2

        if doc is None:
            # Overlay vanished since `on` (hand cleanup). Nothing to restore;
            # removing the marker completes the off.
            sys.stderr.write(
                f"night-mode: warning — {settings_file} is gone; nothing to "
                "restore. Removing marker.\n"
            )
        else:
            permissions = doc.get("permissions")
            if permissions is not None and not isinstance(permissions, dict):
                sys.stderr.write(
                    f"night-mode: 'permissions' in {settings_file} is not an "
                    "object; refusing to restore (fail-closed). Marker left "
                    "in place. Repair the overlay by hand first — "
                    "'off --discard-snapshot' also refuses a 'permissions' "
                    "value it cannot merge.\n"
                )
                _summary(
                    mode="none", previous_mode=str(mode_written), result="refused"
                )
                return 2

            current = (permissions or {}).get("defaultMode")
            if current != mode_written:
                sys.stderr.write(
                    "night-mode: warning — current local defaultMode "
                    f"({current!r}) differs from what night-mode wrote "
                    f"({mode_written!r}); restoring the snapshot anyway.\n"
                )

            new_doc = copy.deepcopy(doc)
            new_permissions = dict(new_doc.get("permissions") or {})
            if prev_present:
                new_permissions["defaultMode"] = prev_value
            else:
                new_permissions.pop("defaultMode", None)
            if new_permissions:
                new_doc["permissions"] = new_permissions
            else:
                # Drop an empty permissions {} rather than leaving litter.
                new_doc.pop("permissions", None)

            # Ordering (contract item 5, inverse): settings FIRST,
            # marker removal second.
            night_mode_own_doc = {"permissions": {"defaultMode": mode_written}}
            if created_file and not new_doc and doc == night_mode_own_doc:
                # `on` created the file and nothing else ever landed in it:
                # restoring means removing it entirely. Reachable ONLY after
                # `_validate_marker` proved created_file is a real boolean
                # AND that created_file=True implies prev_present=False
                # (NF-03) — an unvalidated `created_file` made this branch
                # unlink an overlay night-mode never created.
                #
                # NF-03 residual, bounded here: no marker field can prove
                # the file did not pre-exist (that fact lives ONLY in the
                # marker), so the destructive branch additionally requires
                # the overlay's CURRENT content to be, in full, exactly what
                # `on` writes when it creates the file. A forged
                # `created_file` can therefore only ever delete a document
                # night-mode itself would have written byte-for-byte;
                # anything the Owner actually put in the overlay takes the
                # non-destructive rewrite branch below instead.
                try:
                    os.unlink(settings_file)
                except OSError as exc:
                    sys.stderr.write(
                        f"night-mode: failed to remove {settings_file} "
                        f"({exc.__class__.__name__}: {exc}); marker left in "
                        "place.\n"
                    )
                    _summary(
                        mode="none",
                        previous_mode=str(mode_written),
                        result="failed",
                    )
                    return 1
                _fsync_dir(settings_file.parent)  # NM-09: durable unlink
            else:
                try:
                    _atomic_write_json(settings_file, new_doc)
                except OSError as exc:
                    sys.stderr.write(
                        f"night-mode: failed to write {settings_file} "
                        f"({exc.__class__.__name__}: {exc}); marker left in "
                        "place.\n"
                    )
                    _summary(
                        mode="none",
                        previous_mode=str(mode_written),
                        result="failed",
                    )
                    return 1
                if not _read_back_matches(settings_file, new_doc):
                    sys.stderr.write(
                        f"night-mode: read-back of {settings_file} does not "
                        "match the restored document — marker left in place "
                        "so 'status' keeps reporting the disagreement.\n"
                    )
                    _summary(
                        mode="none",
                        previous_mode=str(mode_written),
                        result="failed",
                    )
                    return 1

        restored = prev_value if prev_present else "absent"
        try:
            os.unlink(marker_file)
        except OSError as exc:
            sys.stderr.write(
                f"night-mode: settings restored but marker removal failed "
                f"({exc.__class__.__name__}: {exc}); re-run 'off'.\n"
            )
            _summary(
                mode=str(restored), previous_mode=str(mode_written), result="failed"
            )
            return 1
        _fsync_dir(marker_file.parent)  # NM-09: durable unlink

        if prev_present:
            # NM-11: name the restored value's relation to the project
            # layer — a restored local value still OVERRIDES the project
            # posture; do not claim ratification that did not happen.
            print(
                f"night-mode: OFF — local overlay defaultMode restored to "
                f"{restored!r} (snapshot). Note: that local value still "
                "overrides the project layer's posture for the next session."
            )
        else:
            print(
                "night-mode: OFF — local overlay defaultMode override "
                f"removed (snapshot: {restored}). Next session resolves the "
                "project layer's ratified posture."
            )
        # Summary LAST (NF-04 structural rule — see cmd_on).
        _summary(
            mode=str(restored), previous_mode=str(mode_written), result="applied"
        )
        return 0


# --------------------------------------------------------------------------- #
# off --discard-snapshot  (NF-02 recovery)
# --------------------------------------------------------------------------- #
def cmd_off_discard_snapshot(root: Path) -> int:
    """NF-02 — the sanctioned exit from EVERY fail-closed `off` refusal.

    Removes the local `permissions.defaultMode` override AND the marker
    WITHOUT honoring `prev_value` (or any other marker field), printing
    exactly what it discarded. Every refusal diagnostic points here: a
    fail-closed gate must never strand the operator with the posture armed
    and no way to disarm it short of hand-editing two gitignored files —
    which is precisely how the round-3 review found the old closed set
    landing on the PERMISSIVE side (NF-02).

    Deliberate asymmetries with plain `off`:

    - a MISSING marker is NOT a no-op here. The armed-without-marker
      end-state (crash between the two writes, hand edit, or the NF-01
      tamper) is exactly what needs recovering, so the override is stripped
      anyway.
    - the overlay file is NEVER unlinked, whatever `created_file` claims:
      discard removes ONE KEY, never a file. It refuses to act on any
      marker field, so it cannot inherit the NF-03 data-loss path.
    - a malformed overlay is still fail-CLOSED. Discard rewrites the
      overlay, and rewriting JSON it cannot parse would destroy the
      Owner's other settings (contract item 6).
    """
    refused = _refuse_if_ci()
    if refused is not None:
        _summary(mode="none", previous_mode="none", result="refused")
        return refused

    FileLock = _import_filelock()
    with FileLock(str(lock_path(root))):
        marker_file = marker_path(root)
        marker, marker_diag = _load_json_fail_closed(
            marker_file, "night-mode marker"
        )
        # Loud, BOUNDED forensic echo — throwing the snapshot away is the
        # whole point of the flag, so the operator must see what was thrown.
        if marker is not None:
            print(
                "night-mode: DISCARDING the snapshot at {0} — version={1} "
                "mode_written={2} prev_present={3} prev_value={4} "
                "created_file={5} ts={6} hostname={7}".format(
                    marker_file,
                    _bounded_repr(marker.get("version")),
                    _bounded_repr(marker.get("mode_written")),
                    _bounded_repr(marker.get("prev_present")),
                    _bounded_repr(marker.get("prev_value")),
                    _bounded_repr(marker.get("created_file")),
                    _bounded_repr(marker.get("ts")),
                    _bounded_repr(marker.get("hostname")),
                )
            )
            print(
                "night-mode: that prev_value is NOT being restored — the "
                "local defaultMode override is being REMOVED instead."
            )
        elif marker_diag is not None:
            print(
                f"night-mode: DISCARDING an UNPARSEABLE marker at "
                f"{marker_file} — {marker_diag}"
            )
        else:
            print(
                f"night-mode: no marker at {marker_file} — discarding the "
                "local defaultMode override anyway (armed-without-marker "
                "recovery; plain 'off' is a no-op in this state)."
            )

        settings_file = settings_local_path(root)
        doc, diag = _load_json_fail_closed(settings_file, "settings.local.json")
        if diag is not None:
            sys.stderr.write(
                f"night-mode: {diag}\n"
                "night-mode: --discard-snapshot still refuses to rewrite an "
                "overlay it cannot parse (fail-closed on input) — repair the "
                "JSON by hand, then re-run. Marker left in place.\n"
            )
            _summary(mode="none", previous_mode="none", result="refused")
            return 2

        removed: Any = "absent"
        if doc is None:
            sys.stderr.write(
                f"night-mode: warning — {settings_file} is absent; there is "
                "no override to strip.\n"
            )
        else:
            permissions = doc.get("permissions")
            if permissions is not None and not isinstance(permissions, dict):
                sys.stderr.write(
                    f"night-mode: 'permissions' in {settings_file} is not an "
                    f"object (got {type(permissions).__name__}); refusing to "
                    "rewrite it (fail-closed). Repair it by hand, then "
                    "re-run. Marker left in place.\n"
                )
                _summary(mode="none", previous_mode="none", result="refused")
                return 2
            removed = (permissions or {}).get("defaultMode", "absent")

            new_doc = copy.deepcopy(doc)
            new_permissions = dict(new_doc.get("permissions") or {})
            new_permissions.pop("defaultMode", None)
            if new_permissions:
                new_doc["permissions"] = new_permissions
            else:
                new_doc.pop("permissions", None)

            # Ordering (contract item 5): settings FIRST, marker second.
            try:
                _atomic_write_json(settings_file, new_doc)
            except OSError as exc:
                sys.stderr.write(
                    f"night-mode: failed to write {settings_file} "
                    f"({exc.__class__.__name__}: {exc}); marker left in "
                    "place.\n"
                )
                _summary(mode="none", previous_mode="none", result="failed")
                return 1
            if not _read_back_matches(settings_file, new_doc):
                sys.stderr.write(
                    f"night-mode: read-back of {settings_file} does not match "
                    "the stripped document — marker left in place so 'status' "
                    "keeps reporting the disagreement.\n"
                )
                _summary(mode="none", previous_mode="none", result="failed")
                return 1

        if marker_file.exists():
            try:
                os.unlink(marker_file)
            except OSError as exc:
                sys.stderr.write(
                    f"night-mode: override stripped but marker removal failed "
                    f"({exc.__class__.__name__}: {exc}); re-run "
                    "'off --discard-snapshot'.\n"
                )
                _summary(mode="none", previous_mode="none", result="failed")
                return 1
            _fsync_dir(marker_file.parent)  # NM-09: durable unlink

        print(
            "night-mode: OFF (snapshot DISCARDED) — local overlay "
            f"defaultMode override removed (it was "
            f"{_bounded_repr(removed)}), marker deleted, prev_value NOT "
            "restored. The next session resolves the project layer's "
            "ratified posture."
        )
        # Summary LAST (NF-04 structural rule — see cmd_on).
        _summary(mode="none", previous_mode="none", result="applied")
        return 0


# --------------------------------------------------------------------------- #
# status
# --------------------------------------------------------------------------- #
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

    if args.discard_snapshot and args.command != "off":
        sys.stderr.write(
            "night-mode: --discard-snapshot is only valid with 'off' (got "
            f"{args.command!r}); it is the recovery path for a refused "
            "restore, not a mode of arming or reporting.\n"
        )
        if args.command == "on":
            _summary(mode="none", previous_mode="none", result="refused")
        return 2

    root = Path(args.project_root).resolve() if args.project_root else REPO_ROOT

    diag = _validate_root(root)
    if diag is not None:
        # NM-04: fail-closed on an unconfined target, BEFORE any dispatch.
        sys.stderr.write(f"night-mode: {diag}\n")
        if args.command in ("on", "off"):
            _summary(mode="none", previous_mode="none", result="refused")
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
            # NM-05: even the catch-all leaves a machine-readable record.
            _summary(mode="none", previous_mode="none", result="failed")
        return 2


if __name__ == "__main__":
    sys.exit(main())
