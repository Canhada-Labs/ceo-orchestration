# PLAN-179 W2 US8 — `SessionEnd.py` memory-delta observation (spec, not a patch)

> **Why this is a note and not a staged file.** `.claude/hooks/*.py` is
> canonical-guarded (`_CANONICAL_GUARDS` in `check_canonical_edit.py`), so
> `SessionEnd.py` lands only through the Owner's signed ceremony. This
> document is the implementable diff description that ceremony consumes:
> function signatures, the event contract, closed field sets, ordering,
> budget, kill-switch, and the test surface. Nothing here is applied to the
> live tree.

---

## 1. What `SessionEnd.py` does today (read, not inferred)

Four responsibilities per its own docstring; the one that matters for US8 is
#2, **memory persistence verify**. Its entire implementation is:

- `_memory_dir_state(repo_root) -> Dict[str, object]` — derives
  `slug = str(repo_root).replace("/", "-").lstrip("-")`, builds
  `Path.home() / ".claude" / "projects" / f"-{slug}" / "memory"`, and returns
  `{"writable": os.access(dir, os.W_OK), "memory_md_present": (dir /
  "MEMORY.md").is_file(), "slug": slug}`.
- `_emit_session_end(...)` puts exactly two of those on the wire:
  `memory_writable` (bool) and `memory_index_present` (bool), inside the
  `session_end` event.
- `decide()` echoes `memory_writable` into the `systemMessage`.

**The gap, stated precisely:** the hook answers *"could this session have
written memory?"* and never *"did it?"*. Both fields are green in the exact
failure this plan exists to close — CLAUDE.md §5 records that **nothing
writes memory**; `SessionEnd.py` only verifies writability. A permanently
green writability bit is an instrument whose question has aged out
([[feedback-instrument-green-with-stale-question]]): it cannot distinguish a
session that wrote three memory topics from a session that wrote none, and
the second case is the E3 abandonment mode.

**Non-goal, load-bearing.** US8 does **not** make the hook write memory.
Memory writing stays a decision of the model or the Owner. The hook's job is
to make the **omission visible** — nothing more. Any implementation that
opens a file under the memory dir for write is out of contract; this rail is
**stat-only**.

---

## 2. The delta the hook can honestly observe

The hook cannot know what the model *intended* to record. It can observe
three facts, all by `stat`, no file bodies read:

| Fact | How | Cost |
|---|---|---|
| Memory dir file count | `iterdir()` + `is_file()` | one dirent pass |
| Which entries changed during **this session** | `st_mtime >= session_start_ts` | one `stat` per entry |
| Whether the `MEMORY.md` index itself changed | same predicate on that one path | one `stat` |

`session_start_ts` has a resolution order, and an explicit "I do not know"
terminal — never a guess:

1. **Primary — the HMAC chain.** Bounded reverse scan of the audit log for
   this `session_id`'s `session_start` event. Caps: ≤200 lines **and**
   ≤256 KiB read **and** ≤100 ms wall. The chain is the anchor, never a
   mutable side file (the ADR-160 §3 / A6 principle applied here).
2. **Fallback — the per-session state file.** `tool_lifecycle.py`'s
   per-session 0600 record file, whose creation `mtime` bounds the session
   from below. `SessionEnd` already touches this module
   (`_cleanup_tool_lifecycle`), so read the mtime **before**
   `cleanup_session()` deletes it — see §5 ordering.
3. **Terminal — unknown.** Any failure of both ⇒ outcome
   `start_unknown`. The hook reports that it could not bound the window; it
   does **not** substitute "since midnight", "last hour", or process start.
   A wrong window produces a false "you wrote memory" — worse than absent
   (the plan's own §8 rule: a degraded entry is worse than a missing one).

---

## 3. New functions (signatures + contracts)

All additions are module-private, `from __future__ import annotations`,
`typing.Optional`/`Dict`/`Tuple` only, no PEP 604 at runtime, no `match`,
stdlib only, Python ≥ 3.9. Every one is best-effort and **never raises** —
SessionEnd is observational and fail-OPEN on infrastructure (CLAUDE.md §5).
There is no security matcher here, so there is no fail-CLOSED arm.

```
_MEMORY_DELTA_ENV = "CEO_SESSION_MEMORY_DELTA"
_MEMORY_DELTA_SCAN_BUDGET_MS = 50       # stat pass over the memory dir
_MEMORY_DELTA_ANCHOR_BUDGET_MS = 100    # chain reverse-scan for session_start
_MEMORY_DELTA_ANCHOR_MAX_LINES = 200
_MEMORY_DELTA_ANCHOR_MAX_BYTES = 262144
_MEMORY_DELTA_MAX_NAMES = 5             # names rendered to the operator
_MEMORY_DELTA_NAME_MAX_CHARS = 64       # per name, post-NFKC, asserted
```

### `_memory_delta_rail_state() -> str`

Resolves the kill-switch into a **closed** three-value string:
`"full"` (default — emit event + render the operator line), `"quiet"`
(emit event, no `systemMessage` line), `"off"` (no-op, nothing emitted).
Mapping: `CEO_SESSION_MEMORY_DELTA` in `{"0","false","off","no"}` → `"off"`;
in `{"quiet","1q"}` → `"quiet"`; unset / anything else → `"full"`.
Rationale for default-ON: this rail *is* the visibility PLAN-179 W2 depends
on; an opt-in rail nobody enables reproduces the very omission it measures.

> **Harness no-op detector.** Under `"off"` this rail legitimately produces
> no output, so `check_harness_config.py`'s no-op detector needs the
> **gate-side, canonical-guarded** allowlist entry
> (`harness-noop-allowlist.txt`) per ADR-160 §7. An in-file marker string
> does **not** suffice and must not be used.

### `_session_start_ts(session_id: str, repo_root: Path) -> Optional[float]`

Implements §2's resolution order. Returns a POSIX timestamp (float, used
only for the in-process comparison — it never reaches the wire) or `None`
for the terminal-unknown case. Honours both budgets; on budget exhaustion
returns `None` rather than a partial answer.

### `_memory_delta_observed(repo_root: Path, session_id: str) -> Dict[str, object]`

The observation. Returns a dict with exactly:

```
{
  "outcome": <closed enum, see §4>,
  "files_count": int,             # entries in the memory dir
  "modified_count": int,          # entries with st_mtime >= session_start
  "index_modified": bool,         # MEMORY.md specifically
  "names": List[str],             # basenames only — OPERATOR channel only
}
```

`names` holds at most `_MEMORY_DELTA_MAX_NAMES` **basenames** of modified
entries, sorted, each already passed through the sanitiser of §6. It is
consumed only by the `systemMessage` renderer and is **never** passed to
`audit_emit` — see the §4 denial list.

Budget: the whole function is wall-capped at
`_MEMORY_DELTA_SCAN_BUDGET_MS`; on exhaustion it returns the partial counts
with `outcome="error"` rather than an optimistic outcome. A slow filesystem
must never be reported as "memory written".

### `_emit_session_memory_delta(...) -> None`

Best-effort emit; wraps the whole body in `try/except Exception: return`, and
an emit failure never changes any decision (there is no decision here to
change). Field list in §4.

### `_render_memory_delta_line(delta: Dict[str, object]) -> str`

Builds the one-line operator ratification string appended to the existing
`systemMessage`. Shapes:

- omission — `SessionEnd: memory delta ABSENT (0 of N topics touched this session) — ratify or record before closing`
- written — `SessionEnd: memory delta = 3 topic(s) + index (a.md, b.md, c.md)`
- unknown — `SessionEnd: memory delta UNKNOWN (session start not resolvable) — treat as unverified`

The **omission** phrasing is the point of the whole item: it is the line that
makes E3 visible at the moment the operator can still act on it.

---

## 4. Audit event contract

**Action:** `session_memory_delta_observed`

A **new action**, deliberately not extra fields on `session_end`. Overloading
`session_end` would conflate "the hook ran" with "a delta was observed", and
would change the meaning of an event that already has a landed SPEC row
(v2.7). One emit per session, immediately before the `session_end` emit.

**Fields on the wire (closed set):**

| Field | Type | Contract |
|---|---|---|
| `action` | str | `session_memory_delta_observed` |
| `outcome` | str | CLOSED enum: `written` · `absent` · `index_only` · `start_unknown` · `dir_missing` · `not_writable` · `error` · `other`. Off-enum COERCED to `other` — **never** to `written` (an unparseable observation must never be laundered into a healthy-class value). |
| `files_count` | int | clamped 0..99999; entries in the memory dir |
| `modified_count` | int | clamped 0..99999; entries modified inside the session window |
| `index_modified` | bool | `MEMORY.md` specifically |
| `anchor_source` | str | CLOSED enum: `chain` · `state_file` · `none`; which resolution step of §2 answered |
| `session_id` | str | threaded from the harness event, no silent default |
| `project` | str | `str(repo_root)` — the same field every event on this rail already carries |
| `event_schema`, `ts` | — | baseline |
| `tokens_*`, `hmac`, `hmac_error` | — | baseline |

**DENIED on the wire, by name:**

- the memory **file names / basenames** (`names`) — a topic slug is
  model-authored free text and a path fragment; both are forbidden by the
  LLM06 side-channel guard, and the precedent rows (`directory_added_recorded`,
  `notification_lifecycle`, `pair_rail_review_expected`) all carry a
  `*_hash_prefix` instead of a path;
- the memory **file bodies** or any excerpt;
- the resolved **absolute memory dir path** and the `$HOME`-derived `slug`
  (the slug is literally the operator's home-relative repo path);
- the raw `session_start` timestamp source line from the chain;
- any environment **value**.

> **Reconciliation note — "counts and paths" from the plan text.** The W2 AC
> says the delta is "contagem + paths, nunca corpo". Paths cannot ride the
> signed chain: that would violate the repo's own schema doctrine and the
> no-path rule this file assignment restates. The split that satisfies both:
> **counts + closed enums go to the audit event; the (sanitised, capped)
> basenames go only to the `systemMessage`**, which is the operator
> ratification channel and is not the signed chain. If a future consumer
> genuinely needs path identity in the chain, add a
> `memory_dir_hash_prefix` (EXACT 12-lowercase-hex sha256 prefix of the
> absolute dir, or exactly `""`; off-shape DROPPED to `""`, never
> truncated) — a hash, never the path.

**Emit routing:** typed emitter `emit_session_memory_delta_observed` in
`_lib/audit_emit.py` with a dedicated deny-by-default
`_SESSION_MEMORY_DELTA_OBSERVED_ALLOWLIST` scrub branch **plus** closed-enum
VALUE re-coercion in the `emit_generic` dispatch branch — **never**
`_EMIT_GENERIC_PASSTHROUGH`. All counts are `int` with the unit implied by
the name; **no floats anywhere** (a float in an HMAC-covered field drops the
whole event — [[feedback-float-in-hmac-field-drops-whole-event]]). Note that
`_MEMORY_DELTA_*_BUDGET_MS` are already integer milliseconds for this reason;
if a budget value is ever put on the wire it goes as `int` ms, never seconds.

**SPEC row.** `SPEC/v1/audit-log.schema.md` needs one new row in the landed
style. The `event_schema` minor is allocated **at the moment of writing the
ceremony**, not reserved in this draft (latest landed is v2.54; do not
hardcode v2.55 here — the same discipline as ADR numbering, PLAN-179 §8.2).
`SPEC/**` carries an `Edit` deny and lands only in the signed ceremony.

**ATLAS:** none. This is a governance/omission-visibility breadcrumb, not a
detection signal.

**Completeness residual (name it in the row):** an absent
`session_memory_delta_observed` row is not evidence of an absent session —
`CEO_EXTENDED_LIFECYCLE=0`, `disableAllHooks`, or a killed process all
suppress it. Same honest boundary as ADR-153 §H2.

---

## 5. Ordering inside `decide()` (exact)

The current body is `memory_state → _cleanup_tool_lifecycle →
_flush_audit_log_filelock → _invoke_audit_tokens_stub →
_invoke_value_dashboard_summarize → _emit_session_end → return`.

Two ordering constraints, both load-bearing:

1. **Observe before cleanup.** `_memory_delta_observed` must run **before**
   `_cleanup_tool_lifecycle`, because the fallback anchor (§2 step 2) reads
   the per-session record file that `cleanup_session()` deletes. Inverting
   these silently degrades every session to `anchor_source="none"` —
   a green-looking rail answering nothing.
2. **Emit before `session_end`.** So the delta lands in the same session
   window as the closing event, and a reader scanning backwards from
   `session_end` finds it adjacent (the same rationale the audit-tokens stub
   already uses).

Resulting body:

```
memory_state = _memory_dir_state(repo_root)
rail = _memory_delta_rail_state()
delta = None
if rail != "off":
    delta = _memory_delta_observed(repo_root, session_id)   # BEFORE cleanup
_cleanup_tool_lifecycle(session_id)
_flush_audit_log_filelock(repo_root)
_invoke_audit_tokens_stub(...)
_invoke_value_dashboard_summarize(...)
if delta is not None:
    _emit_session_memory_delta(session_id=session_id, repo_root=repo_root, delta=delta)
_emit_session_end(...)                                       # unchanged
```

`_emit_session_end` and its two existing fields are **not** modified. The
`systemMessage` gains the §3 line only when `rail == "full"`.

---

## 6. Untrusted-content handling for the rendered names

Memory basenames were written by a previous session's model. They enter the
current model's context through `systemMessage`, so they are untrusted
content on an ingress path and get the treatment the boot lessons render gate
already uses (`ceo-boot.py::_validate_boot_lesson` is the reference
implementation to mirror, not to import — it is a `/ceo-boot` private):

- reject any name containing a backtick, `\n`, `\r`, or `\x00` (fence-escape
  and line-smuggling primitives);
- NFKC-normalise **before** the length check, then **assert** the
  `_MEMORY_DELTA_NAME_MAX_CHARS` bound — drop, never truncate;
- drop `<`/`>` and markdown-link syntax;
- a name failing any check is **omitted from the rendered list** while still
  counting in `modified_count`. Counts stay truthful; only the display
  degrades. Never render a redaction placeholder as a file name.

---

## 7. Test surface

New file `.claude/hooks/tests/test_session_end_memory_delta.py`
(`hooks/tests/` is **not** canonical-guarded — [[feedback-test-canonicality-and-env-hygiene-for-new-tests]]),
using `TestEnvContext` from `_lib/testing.py` plus `mock.patch.dict` for env;
never touching the real `$HOME` or `$CLAUDE_PROJECT_DIR`.

1. `test_absent_delta_reports_absent` — memory dir exists, nothing modified
   inside the window ⇒ `outcome="absent"`, `modified_count == 0`, and the
   operator line contains `ABSENT`. **This is the positive control for the
   whole item**: it is the case the current hook cannot express.
2. `test_written_delta_counts_only` — two files touched inside the window ⇒
   `outcome="written"`, `modified_count == 2`.
3. `test_index_only` — only `MEMORY.md` touched ⇒ `outcome="index_only"`,
   `index_modified is True`.
4. `test_unresolvable_anchor_is_start_unknown` — chain unreadable and state
   file absent ⇒ `outcome="start_unknown"`, `anchor_source="none"`, and
   **no** `written`-class outcome under any input.
5. `test_no_paths_on_the_wire` — assert the emitted kwargs set is exactly the
   §4 field list; assert the memory dir string, the slug, and every basename
   are absent from the serialised event. Positive control: plant a distinctive
   basename and grep the emitted payload for it.
6. `test_no_floats_on_the_wire` — every numeric kwarg `isinstance(..., int)`
   and not `bool` where an int is required.
7. `test_ordering_observes_before_cleanup` — patch `tool_lifecycle` and assert
   the observation call precedes `cleanup_session`. Negative control: swap the
   order in the test double and assert the anchor degrades to `none`.
8. `test_kill_switch_off_is_silent` — `CEO_SESSION_MEMORY_DELTA=0` ⇒ zero
   emits, no `systemMessage` delta line, and `{"continue": true}` still on
   stdout.
9. `test_hostile_basename_dropped_from_render_not_from_count` — a basename
   carrying a backtick + newline is excluded from the rendered list while
   `modified_count` still includes it.
10. `test_fail_open_on_stat_error` — `os.stat` raising ⇒ `outcome="error"`,
    hook still returns `{"continue": true}` exit 0.
11. `test_budget_exhaustion_is_not_written` — a stat pass forced past
    `_MEMORY_DELTA_SCAN_BUDGET_MS` ⇒ `outcome="error"`, never `written`.

---

## 8. Dependencies and honest boundaries

- **No dependency on the staged W0/W1 pack.** US8 uses no symbol from
  `.claude/plans/PLAN-179/staged-w01/` (no scratchpad session-scope fallback,
  no `written_session_scope` outcome, no `context_pressure_observed`). If a
  later revision grows one, it must probe with `getattr` **and emit a LOUD
  breadcrumb naming the missing symbol** — a silent `getattr` degradation is
  exactly the false-green integration recorded as process defect #1 in
  `.claude/plans/PLAN-179/LEDGER.md` (a hook probed a sibling's symbol under
  the wrong name, degraded quietly, and the cure did not exist while the
  tests were green).
- **This rail measures its own subject.** It counts memory writes, and the
  thing it is measuring is whether anybody writes memory. A permanently
  `absent` outcome is the honest signal, not a broken hook — the cure for it
  is a behaviour change by the model/Owner, not a code change here.
- **A count is not a ratification.** The hook renders a line; it cannot force
  anyone to read it. If the omission line proves as ignorable as the
  writability bit it replaces, US8 has failed and should be **removed**, not
  kept as debt — the same death criterion the W2 ledger checkpoint carries
  (PLAN-179 §8 emendas r1-A1/A3/B6). Pre-register the check: if
  `outcome="absent"` dominates over the measurement window with no
  corresponding behaviour change, the rail is deleted.
- **Sessions that never reach SessionEnd emit nothing.** A killed process, a
  crashed harness, or `CEO_EXTENDED_LIFECYCLE=0` all produce no row — the
  censored universe must be declared alongside any rate computed from this
  event ([[feedback-measurement-must-list-its-inputs]]).
- **Ceremony scope.** Landing US8 touches `SessionEnd.py`,
  `_lib/audit_emit.py` (typed emitter + allowlist branch),
  `SPEC/v1/audit-log.schema.md` (one row + version bump), and
  `harness-noop-allowlist.txt` if the `off` state is shipped — all canonical
  or deny-protected. One sentinel, scope = that exact path set; `touched −
  scope = ∅` asserted before commit
  ([[feedback-sentinel-scope-and-plan-lifecycle-gotchas]]).
