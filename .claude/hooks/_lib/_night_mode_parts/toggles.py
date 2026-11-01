"""Extracted night-mode toggles declarations."""
from __future__ import annotations

__all__ = ('cmd_on', 'cmd_off', 'cmd_off_discard_snapshot')

def cmd_on(root: Path) -> int:
    refused = _refuse_if_ci()
    if refused is not None:
        _summary(mode=NIGHT_MODE, previous_mode="none", result="refused")
        _emit_audit(NIGHT_MODE, "other", "refused")
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
            _emit_audit(NIGHT_MODE, "other", "noop")
            return 0

        settings_file = settings_local_path(root)
        doc, diag = _load_json_fail_closed(settings_file, "settings.local.json")
        if diag is not None:
            sys.stderr.write(f"night-mode: {diag}\n")
            _summary(mode=NIGHT_MODE, previous_mode="none", result="refused")
            _emit_audit(NIGHT_MODE, "other", "refused")
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
            _emit_audit(NIGHT_MODE, "other", "refused")
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
            _emit_audit(NIGHT_MODE, "other", "failed")
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
            _emit_audit(NIGHT_MODE, "other", "failed")
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
            _emit_audit(NIGHT_MODE, str(previous), "failed")
            return 1
        if not _read_back_matches(marker_file, marker):
            sys.stderr.write(
                f"night-mode: read-back of {marker_file} does not match; "
                "marker may be torn. Run 'status' to reconcile.\n"
            )
            _summary(mode=NIGHT_MODE, previous_mode=str(previous), result="failed")
            _emit_audit(NIGHT_MODE, str(previous), "failed")
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
        # The two records LAST, as a pair, on every terminating path of
        # on/off (structural rule, asserted by the `ast` oracle in the test
        # suite — NF-04/NF-07): operator-facing summary, then the forensic
        # `night_mode_toggled` row. A path that returns without both leaves
        # a posture flip only half-witnessed.
        _summary(mode=NIGHT_MODE, previous_mode=str(previous), result="applied")
        _emit_audit(NIGHT_MODE, str(previous), "applied")
        return 0


# --------------------------------------------------------------------------- #
# off
# --------------------------------------------------------------------------- #
def cmd_off(root: Path) -> int:
    refused = _refuse_if_ci()
    if refused is not None:
        _summary(mode="none", previous_mode="none", result="refused")
        _emit_audit("other", "other", "refused")
        return refused

    FileLock = _import_filelock()
    with FileLock(str(lock_path(root))):
        marker_file = marker_path(root)
        if not marker_file.exists():
            # Contract item 7: idempotent no-op.
            print("night-mode: already OFF (no marker) — no-op.")
            _summary(mode="none", previous_mode="none", result="noop")
            _emit_audit("other", "other", "noop")
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
            _emit_audit("other", "other", "refused")
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
            _emit_audit("other", "other", "refused")
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
            _emit_audit("other", str(mode_written), "refused")
            return 2

        overlay_absent = doc is None
        if overlay_absent:
            # Overlay vanished since `on` (hand cleanup). Nothing to restore;
            # removing the marker completes the off.
            #
            # NF-09 (round-3 review): this route writes NOTHING, so it must
            # not claim it did. It used to fall through to the shared tail
            # and report "restored to 'plan' (snapshot)" with
            # `result=applied` — a restore that never happened, on both
            # records. The truth is that the local layer carries no
            # defaultMode at all and the next session resolves the PROJECT
            # layer, so `restored` is "absent" and the outcome is `noop`.
            # The stderr warning corrected an attentive human; the
            # structured record — the thing a parser reads, and after NF-07
            # the thing that gets HMAC-signed — stayed wrong.
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
                _emit_audit("other", str(mode_written), "refused")
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
                    _emit_audit("other", str(mode_written), "failed")
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
                    _emit_audit("other", str(mode_written), "failed")
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
                    _emit_audit("other", str(mode_written), "failed")
                    return 1

        if overlay_absent or not prev_present:
            # NF-09: "absent" on BOTH routes that leave the local layer
            # without a defaultMode — the snapshot said there was no prior
            # override, or the overlay holding it had already been removed
            # by hand. Neither restored a value, so neither may name one.
            restored = "absent"
        else:
            restored = prev_value
        # NF-09: the overlay-gone route writes no settings file at all, so
        # its outcome is a no-op, not an `applied`. The marker removal that
        # still happens below is state cleanup, not a posture write.
        outcome = "noop" if overlay_absent else "applied"
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
            _emit_audit(str(restored), str(mode_written), "failed")
            return 1
        _fsync_dir(marker_file.parent)  # NM-09: durable unlink

        if overlay_absent:
            # NF-09: nothing was written on this route. Say that, and say
            # what governs the next session instead of naming a snapshot
            # value that was never put anywhere.
            print(
                "night-mode: OFF — nothing to restore: the local overlay "
                "was already gone, so no file was written; the marker is "
                "removed. Next session resolves the project layer's "
                "ratified posture."
            )
        elif prev_present:
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
        # Both records LAST, as a pair (NF-04/NF-07 — see cmd_on).
        _summary(
            mode=str(restored), previous_mode=str(mode_written), result=outcome
        )
        _emit_audit(str(restored), str(mode_written), outcome)
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
        _emit_audit("other", "other", "refused")
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
            _emit_audit("other", "other", "refused")
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
                _emit_audit("other", "other", "refused")
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
                _emit_audit("other", "other", "failed")
                return 1
            if not _read_back_matches(settings_file, new_doc):
                sys.stderr.write(
                    f"night-mode: read-back of {settings_file} does not match "
                    "the stripped document — marker left in place so 'status' "
                    "keeps reporting the disagreement.\n"
                )
                _summary(mode="none", previous_mode="none", result="failed")
                _emit_audit("other", "other", "failed")
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
                _emit_audit("other", "other", "failed")
                return 1
            _fsync_dir(marker_file.parent)  # NM-09: durable unlink

        print(
            "night-mode: OFF (snapshot DISCARDED) — local overlay "
            f"defaultMode override removed (it was "
            f"{_bounded_repr(removed)}), marker deleted, prev_value NOT "
            "restored. The next session resolves the project layer's "
            "ratified posture."
        )
        # Both records LAST, as a pair (NF-04/NF-07 — see cmd_on).
        _summary(mode="none", previous_mode="none", result="applied")
        _emit_audit("other", "other", "applied")
        return 0


# --------------------------------------------------------------------------- #
# status
# --------------------------------------------------------------------------- #
