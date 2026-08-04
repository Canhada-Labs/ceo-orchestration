# W1-land fixes — NF-07 + NF-09 (rehearsal export)

Companion to `w1-land-fixes.patch`
(`sha256 668379886c1cb360c5f806bfc327f051923eed12dd4b4afd1142db4533de5ee7`,
1020 lines).

- **Produced in:** the S292 merge rehearsal tree
  `…/scratchpad/plan165-merge/`, commit `4cdf754`
  (`REHEARSAL: W1-land fixes NF-07+NF-09`) on top of `9e580e4`
  (the rehearsal merge of `plan-165-draft` into main).
- **Applies to:** the merged tree BEFORE these fixes. Verified with
  `git apply --check` against `HEAD~1` of the rehearsal: clean.
- **Touches exactly two files**, neither canonical-guarded:
  `.claude/scripts/night-mode.py` (+204/−36),
  `.claude/scripts/tests/test_night_mode.py` (+441/−20).
  No hook, no `_lib`, no SPEC, no settings — nothing requiring a sentinel.
- **Source of the requirement:** `PLAN-165/architect/round-3/security-review.md`
  §NF-07 (HIGH, blocking) and §NF-09 (MEDIUM, recommended); normative spec
  for NF-07 is `PLAN-165/ceremony-staged/README.md`
  §"P2 emit re-insertion (MANDATORY — same ceremony)".

---

## 1. NF-07 — the emit

### Helper

`_emit_audit(mode, previous_mode, result)` added verbatim from the README
snippet, in a new `# Audit` section immediately after `_summary`.
`import hashlib` had to be **added** — contrary to the README's note
("requires the script's existing `hashlib` … all present"), the merged
script imported `argparse, copy, json, os, socket, stat, sys, tempfile`
only. `sys`, `REPO_ROOT` and `_hostname` were present as stated.

Fail-open by construction: `_lib.audit_emit` is imported INSIDE the `try`,
so a missing or broken hooks tree costs a forensic row, never the toggle.

### Call sites — the structural rule as implemented

Every `_summary(...)` call in the module is immediately followed by exactly
one `_emit_audit(...)`, and every `_emit_audit(...)` is immediately preceded
by exactly one `_summary(...)`. Counts (from `ast`, not by eye):

| function | returns | `_summary` | `_emit_audit` |
|---|---|---|---|
| `cmd_on` | 9 | 9 | 9 |
| `cmd_off` | 11 | 11 | 11 |
| `cmd_off_discard_snapshot` | 7 | 7 | 7 |
| `main` | 7 | 3 | 3 |
| `cmd_status` | 1 | **0** | **0** |

`main`'s other four returns are DISPATCH returns (`return cmd_on(root)`),
where the record belongs to the callee. Its three record-bearing paths are
the two pre-dispatch fail-closed refusals and the catch-all.

**Deviation from the README's placement list, deliberate:** the README names
"`cmd_on`/`cmd_off` + `main`'s catch-all". The two PRE-dispatch refusals in
`main` (a `--discard-snapshot on`, and the NM-04 root-confinement refusal)
are also terminating paths of an `on`/`off` invocation, and they already
emit `_summary`. The signed SPEC row (`audit-log.schema.md:491`) claims the
emit on **EVERY** terminating path of `on`/`off` — leaving those two out
would have left the very claim NF-07 exists to make true still false. They
emit too.

### Result mapping (all 30 sites)

Mechanical rule with exactly one translation: the emit carries the SAME
semantics as its `_summary` sibling, with the summary's sentinel `"none"`
(unknown / not applicable) rendered as the audit enum's `"other"`, per the
README ("Pass `other` explicitly when a value is unknown at the terminating
path").

| terminating path class | exit | `mode` | `previous_mode` | `result` |
|---|---|---|---|---|
| `cmd_on` CI refusal / malformed overlay / non-object `permissions` | 2 | `NIGHT_MODE` | `other` | `refused` |
| `cmd_on` marker already present (double-`on`) | 0 | `NIGHT_MODE` | `other` | `noop` |
| `cmd_on` settings write OSError / read-back mismatch | 1 | `NIGHT_MODE` | `other` | `failed` |
| `cmd_on` marker write OSError / read-back mismatch | 1 | `NIGHT_MODE` | `str(previous)` | `failed` |
| `cmd_on` success | 0 | `NIGHT_MODE` | `str(previous)` | `applied` |
| `cmd_off` CI refusal / unreadable marker / invalid marker (NM-01) | 2 | `other` | `other` | `refused` |
| `cmd_off` no marker (double-`off`) | 0 | `other` | `other` | `noop` |
| `cmd_off` malformed overlay / non-object `permissions` | 2 | `other` | `str(mode_written)` | `refused` |
| `cmd_off` unlink / write / read-back failure | 1 | `other` | `str(mode_written)` | `failed` |
| `cmd_off` marker-removal failure | 1 | `str(restored)` | `str(mode_written)` | `failed` |
| `cmd_off` success | 0 | `str(restored)` | `str(mode_written)` | `applied` / **`noop`** (NF-09) |
| `off --discard-snapshot` refusals | 2 | `other` | `other` | `refused` |
| `off --discard-snapshot` write/read-back/unlink failures | 1 | `other` | `other` | `failed` |
| `off --discard-snapshot` success | 0 | `other` | `other` | `applied` |
| `main` pre-dispatch refusals (bad flag pairing, NM-04) | 2 | `other` | `other` | `refused` |
| `main` catch-all — `FileLockTimeout` | 2 | `other` | `other` | **`refused`** |
| `main` catch-all — any other exception, or unimportable `_lib` | 2 | `other` | `other` | `failed` |

### One decision inside the catch-all that goes slightly past NF-07 — flagged

The README maps exit 2 (lock contention included) to `refused` and reserves
`failed` for exit 1. The merged code emitted a blanket `_summary(...
result="failed")` there — the divergence NF-11(b) names, which the review
says to settle **before** the mapping becomes signed content.

Implemented: the catch-all computes `result` ONCE (`FileLockTimeout` →
`refused`, anything else → `failed`, unimportable `_lib` → `failed`) and
feeds it to BOTH records. So the one-line change also moves `_summary` on
that path from `failed` to `refused`.

Rationale: emitting `refused` on the signed row while the stdout line next
to it says `failed` would have reproduced, in a brand-new record, exactly
the NF-09 defect (two records about one invocation disagreeing). If the CEO
prefers to keep `_summary` untouched and defer NF-11(b), it is a one-token
revert — but then the two records disagree by construction on that path.

Covered behaviourally by
`NightModeAuditRowTest::test_lock_contention_records_refused_not_failed`,
which holds the lock in the TEST process and runs the toggle in a CHILD
(same-process `flock` re-acquire does not contend — S281).

### Claims repaired

- `night-mode.py` module docstring: the `## Observability (NM-05 — interim
  record until P2 lands)` section, which stated the script "deliberately
  does NOT emit", is replaced by `## Audit`, describing the two records.
- `_EPILOG`: same replacement (it carried the identical claim, so
  `night-mode --help` was publishing it).
- `_summary`'s own docstring: "nothing here touches `_lib.audit_emit` on
  purpose" removed.
- Three call-site comments that said "the P2 ceremony inserts the forensic
  `_emit_audit` call right here" now describe the pair as landed.
- **Verified, not edited:** `.claude/commands/night-mode.md:57` and
  `audit_emit.py:9215-9219` become TRUE by the emit landing — no edit
  needed. `SPEC/v1/audit-log.schema.md:491` ("emitted … on EVERY
  terminating path of `on`/`off` (applied/noop/refused/failed)") is now
  satisfied: all four result values are reachable and every terminating
  path of `on`/`off` emits.

---

## 2. NF-09 — the overlay-gone route

`cmd_off`, the branch where `settings.local.json` no longer exists (hand
cleanup between `on` and `off`). Before: it printed a stderr warning, then
fell through to the shared tail and announced `restored to '<snapshot>'`
with `mode=<snapshot> result=applied` — while writing nothing.

After: `overlay_absent` flag drives three things —
`restored = "absent"`, `outcome = "noop"`, and a dedicated human line
("nothing to restore: the local overlay was already gone, so no file was
written; the marker is removed. Next session resolves the project layer's
ratified posture.").

The marker removal still happens; that is state cleanup, not a posture
write, and the code says so in a comment. `result=noop` refers to the
POSTURE overlay — no settings file is created or modified on this route.

---

## 3. Test counts

| suite | before | after |
|---|---|---|
| `.claude/scripts/tests/test_night_mode.py` | **86 passed** | **99 passed** (+13) |
| `test_reality_ledger.py` + `test_check_audit_registry_coverage.py` | 139 passed, 2 skipped | **139 passed, 2 skipped** (unchanged — the atomicity oracle stays green with registration+emit) |
| `test_audit_emit_ghost_action_guard.py` + `_callsite_coverage_matrix` + `_coverage` | — | **175 passed, 1 xfailed** |
| `check-audit-registry-coverage.py` | OK | **OK: audit registry in sync** (exit 0) |
| `check-test-env-hygiene.py` | OK | **OK** (337 flagged files, all allowlisted) |
| `py_compile` both files | — | clean |

New tests (13): `NightModeMainRecordPairingTest` (3),
`NightModeAuditRowTest` (5), `NightModeAuditFailOpenTest` (2),
`NightModeOverlayGoneRouteTest` (3).

### Oracle extension

`_TERMINAL_HELPERS = ("_summary",)` → `("_summary", "_emit_audit")`, which
makes the three existing structural assertions require the PAIR before every
`return` in the three toggle commands. That alone does not reach `main()`
(most of its returns are dispatch returns), so `NightModeMainRecordPairingTest`
adds a MODULE-WIDE walk asserting adjacency in both directions, plus a pin on
`main`'s three record paths and on its catch-all.

### Positive controls — the new tests were proven to fail without the fix

Green on the first run is a claim, so each fix was reverted in turn:

| control | tests that failed |
|---|---|
| A — drop ONE `_emit_audit` call site (`cmd_off` no-op path) | `test_each_helper_is_called_exactly_once_per_terminating_path`, `test_every_return_is_immediately_preceded_by_the_terminal_helpers`, `test_summary_and_emit_are_always_adjacent_siblings` (3 failed) |
| B — make `_emit_audit` a dead call (the NF-07 bug verbatim: registered action, no live emitter) | 5 failed across `NightModeAuditRowTest` + `NightModeOverlayGoneRouteTest::test_the_audit_row_matches_the_no_write_reality`. `test_status_leaves_no_row` correctly stayed green (negative assertion). |
| C — restore the pre-NF-09 tail (`restored=prev_value`, `result=applied`) | `test_off_reports_noop_and_absent_and_writes_nothing`, `test_the_audit_row_matches_the_no_write_reality` (2 failed); `test_a_normal_off_still_reports_the_restore` stayed green — the fix cannot pass by breaking `off`. |

Tree restored and re-verified clean after each control (`grep CONTROL` → none;
99 passed).

---

## 4. Behavioural proof

Isolated tmp root under `tempfile.gettempdir()`, `CEO_NIGHT_MODE_TEST_SEAM=1`,
`CI` unset, and an **isolated audit sink** (`HOME` + `CEO_AUDIT_LOG_*`
redirected into the tmp tree, `CEO_AUDIT_SYNC_MODE=1`) — the live HMAC chain
in `~/.claude/projects/ceo-orchestration/` was not written to.

Initial overlay: `{"permissions":{"defaultMode":"plan"},"env":{"KEEP":"me"}}`.

```
############ SCENARIO 1: on -> off (normal restore)
night-mode-event mode=acceptEdits previous_mode=plan result=applied
night-mode-event mode=plan previous_mode=acceptEdits result=applied
-- overlay after off:
{ "permissions": { "defaultMode": "plan" }, "env": { "KEEP": "me" } }

############ SCENARIO 2: on -> rm overlay -> off (NF-09 route)
night-mode-event mode=acceptEdits previous_mode=plan result=applied
night-mode: warning — <root>/.claude/settings.local.json is gone; nothing to restore. Removing marker.
night-mode: OFF — nothing to restore: the local overlay was already gone, so no
            file was written; the marker is removed. Next session resolves the
            project layer's ratified posture.
night-mode-event mode=absent previous_mode=acceptEdits result=noop
-- overlay exists after off? NO
-- marker exists after off?  NO

############ AUDIT ROWS (isolated sink)
{'action':'night_mode_toggled','mode':'acceptEdits','previous_mode':'other','result':'applied','hostname_hash':'b8127dca551a'}
{'action':'night_mode_toggled','mode':'other',      'previous_mode':'acceptEdits','result':'applied','hostname_hash':'b8127dca551a'}
{'action':'night_mode_toggled','mode':'acceptEdits','previous_mode':'other','result':'applied','hostname_hash':'b8127dca551a'}
{'action':'night_mode_toggled','mode':'absent',     'previous_mode':'acceptEdits','result':'noop','hostname_hash':'b8127dca551a'}
```

AC-7 is satisfied: a row after `on` and a row after `off`, on both scenarios.

---

## 5. Concerns for the CEO

### C1 — NF-10 is no longer theoretical; the probe above IS the evidence (decide in ceremony 2)

Look at rows 1 and 2. The overlay's real prior value was `plan`; the stdout
line says `previous_mode=plan` and `mode=plan`; the **signed row says
`other`** — because `_NIGHT_MODE_MODE_ENUM` is `{acceptEdits, manual,
absent, other}` while `_RESTORABLE_MODES` is `{auto, dontAsk, manual,
plan}`. Intersection: `manual` only.

So **three of the five legitimate `off` outcomes** (`auto`, `dontAsk`,
`plan`) are recorded as `other` — the same token a tampered value produces.
The direction is fail-safe (nothing is echoed) and this is exactly what
NF-10 predicted, but the review said to decide *before* wiring the emit; the
emit is now wired, so the decision is due. Widening the enum touches
`audit_emit.py` (arbitration kernel, no sentinel escape) **and** the SPEC
row — i.e. a ceremony-2 item, not something this patch could do. The
alternative NF-10 offers (document in SPEC that off-enum modes collapse to
`other` by minimisation, so nobody reads `other` as tampering) is also a
SPEC edit.

I did **not** pre-empt that decision: no call site passes a value the enum
would have to grow to accept.

### C2 — NF-11(a) untouched, on purpose

The obsolete `disableAutoMode: "disable"` claim survives in
`night-mode.py:8`, `.claude/commands/night-mode.md:15` and
`ADR-185-night-mode-posture-toggle.md:25`. Two of those three are outside my
file assignment, and fixing one third of a finding is worse than leaving it
coherent for whoever lands the W1 docs. Three plain edits, no ceremony.

### C3 — NF-08 is untouched and still blocking the APPROVE

Out of scope here (it needs an Owner decision between "implement the
invocation block" and "correct the three signed comments", and either way a
ceremony). Flagging only so it is not assumed closed by this patch: this
patch is what puts the live toggle binary at HEAD, which is precisely the
event that makes NF-08 concrete.

### C4 — under-claiming on `off --discard-snapshot`

On a successful discard the code KNOWS the local key was removed, so
`mode="absent"` would be truthful; I emit `mode="other"` to stay exactly as
informative as the adjacent `_summary` line (which says `none`). This is a
deliberate under-claim, consistent with the NF-09 lesson, and it is the one
place where a reviewer could reasonably prefer more fidelity. Changing it is
one literal — but it is really the same question as C1, so it belongs to the
NF-10 decision.

### C5 — this is a REHEARSAL artifact

Nothing was committed to the live tree. The patch is exported for the real
W1-land commit; re-run the two mandated suites at that commit, since the
rehearsal merge base (`9e580e4`) may differ from the eventual one.
