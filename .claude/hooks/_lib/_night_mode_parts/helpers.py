"""Extracted night-mode helpers declarations."""
from __future__ import annotations

__all__ = ('settings_local_path', 'marker_path', 'lock_path', '_import_filelock', '_load_json_fail_closed', '_fsync_dir', '_atomic_write_json', '_read_back_matches', '_refuse_if_ci', '_hostname', '_utc_now_iso', '_marker_age_str', '_bounded_repr', '_LINE_BREAKS', '_ONE_LINE_TABLE', '_one_line', '_invalid_bounded_string', '_validate_marker', '_SUMMARY_TOKEN_SAFE', '_summary_token', '_summary', '_emit_audit', '_seam_widens_to', '_self_path_diagnostic', '_check_self_path', '_validate_root')

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
    OPERATOR-facing record; its forensic sibling is `_emit_audit` below,
    and the two are written as a PAIR on every terminating path (the `ast`
    oracle in the test suite pins the pair — NF-04/NF-07).

    Every value is passed through `_summary_token` — the record must stay
    one parseable line even when a value came from the untrusted marker.
    """
    print(
        "night-mode-event mode={0} previous_mode={1} result={2}".format(
            _summary_token(mode), _summary_token(previous_mode),
            _summary_token(result),
        )
    )


# --------------------------------------------------------------------------- #
# Audit — NF-07: the forensic `night_mode_toggled` row, one per terminating
# path, written as the sibling of every `_summary` call.
# --------------------------------------------------------------------------- #
def _emit_audit(mode: str, previous_mode: str, result: str) -> None:
    """Best-effort night_mode_toggled emit (P2, NM-05). NEVER raises,
    NEVER blocks the toggle.

    Only the P2-allowlisted fields travel: mode, previous_mode, result,
    hostname_hash (= sha256(hostname)[:12]). Never a file path, never
    file content, never the raw hostname. Pass "other" explicitly when a
    value is unknown at the terminating path — the typed wrapper coerces
    any off-enum value to "other" anyway (never echoed).

    Why this exists (NF-07, round-3 review): the overlay is written by a
    PROCESS, not by a tool, so no PostToolUse observer covers it. Without
    this row the highest-forensic-value event PLAN-165 produces — a
    posture flip that outlives the session — leaves nothing on the
    HMAC-chained log, and AC-7 is falsifiable. The action is registered
    (`_KNOWN_ACTIONS`, typed wrapper, scrub branch, SPEC row) by the
    `610d9ec` sentinel ceremony; this call is the other half of that
    ceremony's atomicity contract (registration commit, then this emit in
    the W1-land commit — never an unregistered emit at any HEAD).

    Fail-open by construction: `_lib.audit_emit` is imported INSIDE the
    try, so a missing/broken hooks tree degrades to "no forensic row",
    never to a failed toggle. Repo doctrine is fail-closed on INPUT and
    fail-open on INFRASTRUCTURE — an audit sink is infrastructure.
    """
    try:
        hooks_dir = str(REPO_ROOT / ".claude" / "hooks")
        if hooks_dir not in sys.path:
            sys.path.insert(0, hooks_dir)
        from _lib import audit_emit  # noqa: E402

        audit_emit.emit_night_mode_toggled(
            mode=mode,
            previous_mode=previous_mode,
            result=result,
            hostname_hash=hashlib.sha256(
                _hostname().encode("utf-8")
            ).hexdigest()[:12],
        )
    except Exception:  # noqa: BLE001 — observability must never block
        pass


def _seam_widens_to(root: Path) -> bool:
    """NM-04 hardening (S290 review, the S284 'TEST_MODE-is-a-bypass'
    class): the test seam is NO LONGER a general confinement bypass.

    Even with `CEO_NIGHT_MODE_TEST_SEAM` set, the widened target must
    resolve UNDER the system temp directory — which is all the test
    suite ever needs (every test root is an isolated tmp tree). A seam
    that reopened arbitrary-path writes ("arm acceptEdits in ANY repo on
    the machine") was the exact primitive NM-04 exists to remove; a
    tmp-tree write escalates nothing (a tmp repo's sessions belong to
    whoever created it).
    """
    if not os.environ.get(_TEST_SEAM_ENV):
        return False
    try:
        tmp = Path(tempfile.gettempdir()).resolve()
        resolved = root.resolve()
    except OSError:
        return False
    return resolved == tmp or tmp in resolved.parents


def _self_path_diagnostic(anchored: Path, real: Path) -> Optional[str]:
    """NF-08b — refuse to run as anything but the canonical toggle.

    PURE (no filesystem access): both paths arrive already resolved, so the
    comparison is testable without a real installation — the S285 shape, a
    fail-closed validator must be drivable outside the thing it validates.

    ``real``     the file that will actually execute, symlinks resolved.
    ``anchored`` the path it was INVOKED as, with ancestors resolved but the
                 FINAL component left alone.

    Two refusals, one per member of the class the S292 r2 review opened:

    1. ``real`` is not at ``<its repo>/.claude/scripts/night-mode.py`` — a
       RENAMED or RELOCATED copy. Measured: `cp night-mode.py
       .claude/scripts/nm2.py && python3 .claude/scripts/nm2.py on` armed the
       posture, because `REPO_ROOT` is derived positionally (`parents[2]`)
       and a copy two levels deep lands on the real repo root. No rule about
       `ln` would have caught this one.

    2. ``anchored != real`` — the final component is a LINK, i.e. an ALIAS.
       Measured: `ln -s <repo>/.claude/scripts/night-mode.py /tmp/nm &&
       python3 /tmp/nm on` printed `result=applied` and wrote the overlay,
       because `Path(__file__).resolve()` follows the link back home while
       the command line names nothing a matcher can recognise.

    Why the ancestors are resolved SEPARATELY: `/tmp` is a symlink to
    `/private/tmp` on this platform, and plenty of operators keep repos under
    a symlinked directory. Comparing raw `__file__` against the resolved form
    would lock every one of them out of their own toggle — a fail-closed gate
    landing on the useless side. Only the FINAL component being a link is an
    alias; an ancestor link is just a path spelling.
    """
    try:
        expected = real.parents[2].joinpath(*_CANONICAL_SELF_PARTS)
    except IndexError:
        # Fewer than three ancestors — cannot be an installed layout at all.
        return (
            f"this script is running from {real} , which is too shallow to be "
            "an installed project layout; refusing (NF-08b)."
        )
    canonical = "/".join(_CANONICAL_SELF_PARTS)
    if real != expected:
        return (
            f"this script is running as {real} , which is not "
            f"{canonical} of the repository it resolves into ({expected}); "
            "refusing (NF-08b). A renamed or relocated copy of the posture "
            "toggle still writes the REAL repository's overlay, so it is a "
            "second entry point around the OQ1-redo boundary. Run the "
            f"canonical file instead: `! python3 {canonical} on|off|status`."
        )
    if anchored != real:
        return (
            f"this script was invoked as {anchored} , an ALIAS of "
            f"{real} ; refusing (NF-08b). Arming or disarming the autonomy "
            "posture is a HUMAN action (PLAN-165 OQ1-redo, Owner-ratified "
            "2026-08-03), and a link is a second entry point that arms it "
            "without ever naming the guarded path. Run the canonical file "
            f"instead: `! python3 {canonical} on|off|status`."
        )
    return None


def _check_self_path() -> Optional[str]:
    """Resolve THIS script's own paths, then apply `_self_path_diagnostic`.

    Fail-CLOSED on a resolution error: a symlink loop raises `RuntimeError`
    on some platforms and `OSError` on others, and a guard that cannot
    determine what it is running as must refuse, not shrug. (The S277 pair
    rail found exactly this class — an uncaught symlink-loop `RuntimeError`
    — fail-OPEN in an earlier draft of a different guard in this repo.)
    """
    try:
        real = _INVOKED_SELF.resolve()
        anchored = _INVOKED_SELF.parent.resolve() / _INVOKED_SELF.name
    except (OSError, RuntimeError) as exc:
        return (
            "cannot resolve this script's own path "
            f"({exc.__class__.__name__}: {exc}); refusing (NF-08b)."
        )
    return _self_path_diagnostic(anchored, real)


def _validate_root(root: Path) -> Optional[str]:
    """NM-04 — confine --project-root; returns a diagnostic or None.

    Unconfined, `--project-root` is an arbitrary-path posture-write
    primitive: any Bash-capable agent could arm `acceptEdits` in ANY repo
    on the machine, including targets without the P1 deny rule. Reject
    (fail-closed) any target that is not this repository's root or under
    it. The test seam (`CEO_NIGHT_MODE_TEST_SEAM`) widens the confinement
    ONLY to targets under the system temp directory (`_seam_widens_to`)
    — never to arbitrary paths. In ALL cases the target must already look
    like an installed project (`.claude/settings.json` present) —
    night-mode never bootstraps a posture into a bare tree.
    """
    if root != REPO_ROOT and REPO_ROOT not in root.parents:
        if not _seam_widens_to(root):
            return (
                f"--project-root {root} is outside this repository "
                f"({REPO_ROOT}); refusing (NM-04 confinement — the toggle "
                f"only manages THIS repo's overlay). {_TEST_SEAM_ENV} widens "
                "confinement only to isolated trees under the system temp "
                "directory, never to arbitrary paths."
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
