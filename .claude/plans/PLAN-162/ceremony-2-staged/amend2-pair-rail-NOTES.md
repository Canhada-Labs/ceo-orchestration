# ADR-110-AMEND-2 — code patch NOTES

Artifact: `.claude/plans/PLAN-162/ceremony-2-staged/amend2-pair-rail.patch`
Base: `9c63750` (apply-check verified in a third clean clone)
Built in: overlay `scratchpad/amend2-overlay/` — the live tree was never edited.

---

## 0. The one deviation from the amendment text — READ FIRST

**§1.6 and §4(i) specify a float `timeout_s`. That field is not
implementable, and shipping it would have made the pair-rail invisible.**
The patch emits **`timeout_ms` (int, milliseconds)** instead.

`_lib/canonical_json.py:96` rejects floats in HMAC-covered fields. The
rejection is not benign — measured, not inferred:

```
$ emit_generic("pair_rail_case", ..., timeout_s=180.0)   # field allowlisted
$ wc -l audit-log.jsonl
1        # only the int row landed; the float row VANISHED
$ cat audit-log.errors
... spool_writer: sha compute failed: CanonicalJsonError:
    float at '$.timeout_s' forbidden in HMAC-covered JSON (value=180.0);
    encode as integer basis-points or fixed-precision string
```

So a float `timeout_s` does not merely fail validation: the spool writer
**drops the entire event**, leaving only an `audit-log.errors` breadcrumb.
On these two actions specifically, a dropped row is the worst possible
outcome — every `pair_rail_case` disappears and every
`pair_rail_review_expected` stays outstanding, manufacturing exactly the
/ceo-boot S254 liveness deficit that the r5 F2 `review_id` correlation
was built to disprove. The field meant to instrument the rail would have
blinded it.

**Precedent, exact and in the same hook family:** `dispatcher_route`
carries `wall_clock_ms` (int ms) with the SPEC note *"integer
milliseconds, NOT float seconds; canonical_json no-float invariant"*
(PLAN-081 Phase 2, Codex iter 1 P0-1). `timeout_ms` mirrors it verbatim:
bound `[0, 6_000_000]` ms (= 6000 s = 10x the hook's 600 s clamp
ceiling), divide by 1000 to recover seconds.

The hook keeps `timeout_s` (float seconds) as its INTERNAL variable and at
the `_emit_*` call sites — seconds is the natural unit there and it is
what `subprocess` consumes. Conversion happens once per wrapper, at the
audit boundary (`_timeout_ms()`).

**ACTION REQUIRED on the ADR text:** §1.6 and §4(i) should read
`timeout_ms` (integer milliseconds), not `timeout_s` (float). Two words
in the amendment; the code cannot be changed to match the prose.

---

## 1. Site-by-site: before → after

### 1a. `.claude/hooks/check_pair_rail.py` — timeout literals (ADR §1.1)

| site | before | after |
|---|---|---|
| module docstring (`:51`) | `` `CEO_PAIR_RAIL_TIMEOUT_S` (default 120) `` | `(default 180)` |
| env-read default (`:1717`) | `os.environ.get("CEO_PAIR_RAIL_TIMEOUT_S", "120")` | `"180"` |
| parse-error fallback (`:1720`) | `timeout_s = 120.0` | `180.0` |
| clamp-reset (`:1722`) | `timeout_s = 120.0` | `180.0` |
| clamp bound | `if timeout_s <= 0 or timeout_s > 600` | **UNCHANGED** (§5(c)) |

### 1b. `.claude/settings.json` + `templates/settings/settings.base.json` (§1.2, §1.3)

Identical 3-field edit in both (parity is a tested invariant):

| field | before | after |
|---|---|---|
| `timeout` | `150` | `210` |
| `statusMessage` | `"Pair-rail cross-model review (may take 1-2 min)"` | `"... (may take up to ~3 min)"` |
| `_comment` tail | `default 120s; registration cap 150s — invariant guarded by ...` | `default 180s; registration cap 210s — ADR-110-AMEND-2 recalibration, invariant guarded by ...` |

### 1c. `CHANGELOG.md:43` (§1.3)

The amend-2 debate's staff-code-reviewer argued this line is the v1.2.0
GA historical record and must NOT be edited; the ACCEPTED ADR §1.3 says
to update it. Resolved without falsifying history — the quoted string now
matches the live surface AND the shipped value is preserved:

```
- ... shows "may take up to ~3 min" instead of appearing frozen.
  (Shipped in 1.2.0 as "may take 1-2 min"; the wording tracks the budget
  and was retuned by ADR-110-AMEND-2 when it moved to 180/210 s.)
```

Note for the record: I checked whether a gate forces this.
`check-canonical-doc-freshness.py` enforces `last-reviewed:` stamps only —
it never scans for this string. The edit is ADR-driven, not gate-driven.

### 1d. `.claude/hooks/tests/test_pair_rail_timeout_invariant.py` (§1.4)

`_RATIFIED_INTERNAL_S` 120 → **180**; `_RATIFIED_REGISTRATION_S` 150 →
**210**. `_MARGIN_S` unchanged at 30; the invariant holds at equality
(210 == 180 + 30). Prose updated in 4 places (module docstring intro,
numbered item 4, the retired-trigger description, and the "120s+ stall"
assertion message). The three absolute asserts in
`test_ratified_absolute_values` read the constants, so they needed no
literal edits — the `_FALLBACK_RE` oracle now expects `["180", "180"]`
automatically.

### 1e. `timeout_ms` plumbing (§1.6)

`check_pair_rail.py`:
- new `_TIMEOUT_MS_MAX = 6_000_000` + `_timeout_ms(value_s) -> int`
  (bounded; non-numeric/NaN/inf → 0, catching `OverflowError` which
  `int(float('inf'))` raises and `(TypeError, ValueError)` does not).
- `_emit_pair_rail_review_expected(..., timeout_s: float = 0.0)` and
  `_emit_pair_rail_case(..., timeout_s: float = 0.0)`; each forwards
  `timeout_ms=_timeout_ms(timeout_s)` under the **same `__kwdefaults__`
  skew guard** as `review_id` (a pre-ceremony `audit_emit` degrades to a
  budget-less emit instead of raising `TypeError` into the fail-open
  catch, which would drop the whole event).
- `CEO_PAIR_RAIL_AUDIT_SINK` breadcrumb also carries `timeout_ms` — the
  sink BYPASSES `audit_emit`, so it applies the bound itself.
- **All 5 terminal call sites threaded** (derived by grep, not memory):
  `_decide` `:1469` (denominator) and, in `_decide_with_matrix`, the
  matrix-None case-F/ADVISORY arm, the case-F arm, the case-B arm and the
  case-A arm. The outage/timeout/malformed arms in `_decide` return
  `systemMessage`s that are classified by `_decide_with_matrix`, so they
  all funnel through those four emits — no terminal path is unthreaded
  (proved behaviorally, §3).

`_lib/audit_emit.py`:
- `timeout_ms` added to `_PAIR_RAIL_CASE_EMIT_ALLOWLIST` and
  `_PAIR_RAIL_REVIEW_EXPECTED_ALLOWLIST`.
- shared `_PAIR_RAIL_TIMEOUT_MS_MAX = 6_000_000` +
  `_coerce_pair_rail_timeout_ms(value)`. **`bool` is rejected explicitly**
  — `isinstance(True, int)` would otherwise sign `1` as a budget.
- both typed wrappers gained `timeout_ms: int = 0` and coerce before
  emitting.
- **both `emit_generic` dispatch branches** coerce `timeout_ms` (never
  `_EMIT_GENERIC_PASSTHROUGH`), so a direct caller writing the float the
  ADR prose names is coerced rather than dropping the row.

### 1f. `SPEC/v1/audit-log.schema.md` (§1.6)

`timeout_ms` documented on both rows (`pair_rail_case` `:321`,
`pair_rail_review_expected` `:488`) + one new `v2.55` history line. The
v2.55 entry states explicitly that no action is added (324 unchanged) and
that the integer encoding is **normative, not stylistic**, with the
drop-the-whole-event failure mode named.

---

## 2. The sixth surface the brief did not list — a real adopter defect

`grep -rl "_PAIR_RAIL_REVIEW_EXPECTED_ALLOWLIST\|pair_rail_case"` (the
brief's derivation) does NOT reach `scripts/upgrade.sh`. The suite found
it: `test_upgrade_settings_migration.py` went red on a pinned `150`.

Reading that migration surfaced a genuine defect of this amendment:

- `upgrade.sh` DERIVES the new cap from the template (auto-tracks to 210
  — good), but only migrates adopters whose current value `== 60`.
- **Every v1.2.0 adopter sits at exactly 150** — the AMEND-1 shipped
  default. Under the old code that value falls into the `else` arm and is
  PRESERVED with a `WARNING: ... ADOPTER-CUSTOMIZED` — mislabelling a
  shipped default as a deliberate choice.
- Result: registration 150 with internal default 180. `150 < 180 + 30`,
  so **the harness kills the hook before its own codex cap fires, and a
  killed hook emits NO `pair_rail_case` at all** — precisely the ADR §6
  failure mode described as *"strictly worse than today's case F:
  fail-open with no event, invisible to the instrument in both numerator
  and denominator."* The repo's own invariant test cannot catch it: it
  only reads the two in-repo settings files.

Fix: `OLD_PAIR_RAIL_CAP = 60` → `OLD_PAIR_RAIL_CAPS = (60, 150)`, a frozen
set of SUPERSEDED SHIPPED defaults; `cur == OLD` → `cur in OLD`. Any value
outside the set is still a genuine adopter choice, PRESERVED + WARNED.
Narrative comments in three places updated to match.

**Landmine worth recording.** That whole Python block lives inside a bash
**single-quoted `python3 -I -c '...'` string**. My first comment contained
apostrophes (`the hook's own cap`), which terminated the bash string. The
symptom was not a syntax error at the failing line — it was **29 tests
failing with the migration silently doing nothing** (the seeded value read
back unchanged), which reads as a logic bug, not a quoting bug. `bash -n`
is the diagnostic. I left an explicit in-block warning so the next editor
does not repeat it.

---

## 3. Tests updated / added, and why

| file | change | why |
|---|---|---|
| `test_pair_rail_timeout_invariant.py` | 120/150 → 180/210 + prose | §1.4 — the contract requires editing it in the same change |
| `test_upgrade_settings_migration.py` | pin 150 → **210** (renamed `..._cap_210`); `SUPERSEDED_SHIPPED_CAPS = (60, 150)`; **2 NEW** tests | the 150 pin went red; the new tests cover §2 above |
| `test_audit_emit_coverage.py` | `_truncate_log()` helper + **3 NEW** tests | prove the field reaches the SIGNED chain, coerces off-shape, and closes the direct-`emit_generic` path |
| `test_check_pair_rail_matrix.py` | **3 NEW** tests | prove the HOOK threads the budget — `audit_emit` accepting the kwarg proves nothing about the caller |

New tests (8 total):

- `test_every_superseded_shipped_cap_is_migrated` — RED-first, see below.
- `test_superseded_caps_all_below_new_cap` — guards the frozen set from
  silently acquiring a live value.
- `test_pair_rail_timeout_ms_lands_signed_on_both_actions` — asserts
  `hmac_error is None` and `hmac` truthy, i.e. the row was actually
  signed, not merely written.
- `test_pair_rail_timeout_ms_off_shape_coerces_never_drops` — 9 subtests
  (float seconds, float ms, str, None, **bool**, NaN, inf, negative,
  over-bound). `_read_one()` fails loudly if a row was DROPPED, which is
  the failure mode under test.
- `test_pair_rail_timeout_ms_direct_emit_generic_is_coerced` — passes
  `timeout_s=180.0` **and** `timeout_ms=180000.0` exactly as a caller
  following the ADR prose would; asserts `timeout_s` is scrubbed and the
  float ms is coerced.
- `test_effective_budget_threaded_to_case_and_expected` — captures the
  denominator kwargs AND reads the sink.
- `test_case_f_outage_arm_carries_effective_budget` — the §4(i) arm
  specifically: it returns from an exception handler, the terminal path
  most likely to be missed when threading a new field.
- `test_effective_budget_is_int_ms_never_float` — 0.25 s → `250`, asserts
  `int` and not `bool`.

### Positive controls — every new test was proved able to FAIL

A clean run is a claim, not proof. Each was reverted and re-run:

| control | result |
|---|---|
| `upgrade.sh`: `cur in OLD_PAIR_RAIL_CAPS` → `cur == OLD_PAIR_RAIL_CAPS[0]` | **RED**: `AssertionError: 150 != 210` |
| `audit_emit`: remove `"timeout_ms"` from the case allowlist | **RED** ×3: `KeyError: 'timeout_ms'` |
| `check_pair_rail`: drop `timeout_s=timeout_s` from the case-F emit | **RED** ×2: `AssertionError: 0 != 250` |

Each file was restored and re-verified byte-exact
(`upgrade.sh` sha256 `677360037ba66e6f1f543a17a0456a9f553fc40b131e531c5fd1d01494077ac3`
before and after).

### Live-fire through the real hook (not a fixture)

`check_pair_rail.main()` driven end-to-end with a mocked Codex outage and
a 5 s sub-floor budget, writing to a real isolated audit log:

```
pair_rail_review_expected    timeout_ms=5000  hmac_err=None  rid=26ac5a5b
pair_rail_case               timeout_ms=5000  hmac_err=None  rid=26ac5a5b
```

Both rows signed, paired by the same `review_id`, both carrying the
effective budget. This is §4(i) closed: a case F under a 5 s knob is now
tellable apart from a genuine Codex outage.

---

## 4. Golden / registry — unchanged, verified explicitly

No new action was added, as required.

| check | value |
|---|---|
| `.claude/data/audit-registry.golden.txt` sha256 | `3e32ce52c7674e015edd4e059a3d98569c7d760859e1dc5fa4f82e223420f022` (identical before and after; `git status` on the file is empty in the patched clean clone) |
| `len(_KNOWN_ACTIONS)` | **324** |
| `sha256(json.dumps(sorted(_KNOWN_ACTIONS)))` | `35696184ea595e36de5fbfba555264183fb593cfc73eb5f6b35d4c37187c60ba` — matches the pin in `test_audit_emit_api_contract.py` |
| `check-audit-registry-coverage.py` | `OK: audit registry in sync` |

---

## 5. Validation counts (measured, with the invocation)

In the overlay:

| command | result |
|---|---|
| `pytest .claude/hooks/tests/test_pair_rail_timeout_invariant.py -q` | **4 passed** |
| `pytest .claude/hooks/tests/ -k pair_rail -q` | **231 passed, 1 skipped** |
| `pytest test_audit_emit{,_api_contract,_coverage}.py test_w5_scrub_enforcement.py test_audit_emit_callsite_coverage_matrix.py test_audit_log_schema_consistency.py -q` | **268 passed, 1 xfailed** |
| `pytest .claude/scripts/tests/test_upgrade_settings_migration.py -q` | **40 passed** |
| `python3 -m json.tool` on both settings files | OK |
| `bash -n scripts/upgrade.sh` | OK |
| `bash .claude/scripts/local/verify-counts.sh` | rc=0, *no drift detected* |
| `python3 .claude/scripts/check-claude-md-claims.py` | rc=0 |

In the **third clean clone** (`amend2-verify`, `git checkout 9c63750` +
`git apply`):

| command | result |
|---|---|
| `git apply --check` | rc=0, all 11 files |
| `pytest` over the 7 directly-affected test files | **306 passed, 1 xfailed** |

`git diff --stat`: **11 files, +526 / −57**. No untracked files.

---

## 6. Concerns / open items for the CEO

1. **[BLOCKING on the ADR text]** §1.6 and §4(i) say `timeout_s` (float).
   The patch implements `timeout_ms` (int ms) because the float form drops
   the event. The amendment prose needs the two-word correction before it
   lands, or the ADR and the code disagree on the record. §0 above has the
   evidence.

2. **[NOT in this patch — belongs to the §1.5 instrument lane]**
   `.claude/plans/PLAN-162/ceremony-2-staged/pair-rail-latency.py:141`
   reads `float(os.environ.get("CEO_PAIR_RAIL_TIMEOUT_S", "120") or 120)`.
   After this amendment the default is 180, so an operator running the §3
   instrument without exporting the var will compute
   `at_or_over_budget_pct` against a **stale 120 budget** — the
   measurement-with-wrong-inputs class the ADR §3 exists to retire. One
   line, but it is another agent's staged artifact and outside my
   assignment, so I did not touch it. It should be fixed in the same
   ceremony.

3. **[ADVISORY]** The §6 harness-ceiling probe is still outstanding and is
   BLOCKING per the ADR: a hook registered at 210 s that blocks ~185 s
   must still return and still emit `pair_rail_case`. This patch cannot
   satisfy it — it needs a live harness run. Nothing here presumes the
   probe passed.

4. **[CLOSED — measured, not assumed]** `env-inventory-check.py` reports
   `ENV-DRIFT: 24` (rc=0, advisory) on the patched clone. It reports the
   **same 24** on a pristine clone at `9c63750`, so the drift is
   pre-existing and this patch neither adds to it nor fixes it. The
   `CEO_PAIR_RAIL_TIMEOUT_S` entry (`"sites": 4`) is unaffected — the
   patch adds no new mention of that env-var name.

5. **[ADVISORY]** `scripts/doctor.sh`'s pair-rail coherence check derives
   the internal default from the hook source with the same regex the
   invariant test uses, so it auto-tracks to 180/210. No edit needed —
   verified by reading, not assumed.

6. **[ADVISORY]** `ceremony-s291.sh:14` documents a `p5` step for the
   SPEC `v2.54` entry (PLAN-165). This patch adds `v2.55`; the ceremony-2
   script needs its own step for these 11 files.
