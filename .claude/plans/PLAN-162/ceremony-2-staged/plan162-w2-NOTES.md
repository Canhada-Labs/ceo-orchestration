# PLAN-162 W2 — implementation notes for `plan162-w2-fixes.patch`

> **Artifact:** `.claude/plans/PLAN-162/ceremony-2-staged/plan162-w2-fixes.patch`
> **Base:** `9c63750` (main at implementation time). `git apply --check`
> verified in a SECOND pristine `git clone --local` of the repo, then
> applied there for real and the PLAN-162 suite re-run — same result as
> in the working overlay (49 passed / 1 skipped).
> **Overlay:** `<scratchpad>/plan162-overlay/`. No canonical file in the
> live tree was touched.
>
> **Revision (S292):** the artifact was REGENERATED to fold the Codex
> pair-rail P1 finding (gpg bounded by the remaining wall allowance). All
> "After" counts below are the post-fold measurements; the column moved
> by exactly the 7 tests the fold adds. See
> [§ Codex P1 fold](#codex-p1-fold-s292-gpg-bounded-by-remaining-budget).

## Headline counts (exact, measured — not recalled)

| Run | Command | Before (HEAD `9c63750`) | After (patch, post-fold) |
|---|---|---|---|
| PLAN-162 instrument | `pytest .claude/hooks/tests/test_canonical_edit_plan162_findings.py -q` | **19 passed, 1 skipped, 23 xfailed** | **49 passed, 1 skipped** |
| Neighborhood (14 files: `test_canonical_edit*`, `test_check_canonical_edit*`, `test_check_arbitration_kernel*`, `test_sentinel_session_cache*`, `test_kernel_subsumes*`, `test_session_75_kernel_findings`) | `pytest <14 files> -q` | n/a | **340 passed, 12 skipped, 0 failed** |
| Every test file referencing the two hooks (41 files) | `pytest $(grep -rln 'check_canonical_edit\|check_arbitration_kernel\|_is_canonical\|_KERNEL_PATHS\|_CANONICAL_GUARDS\|_find_sentinels\|_sentinel_grants_path' .claude/hooks/tests/*.py) -q -p no:randomly` | n/a | **1111 passed, 14 skipped, 4 xfailed, 0 failed** |
| Whole hooks suite | `pytest .claude/hooks/tests -q -n auto` | (control, see below) | **6495 passed, 36 skipped, 8 xfailed, 2 xpassed, 1 failed** |

**All 23 strict xfails flipped to passed. 0 failed, 0 unexpected xpass in
the PLAN-162 instrument.** 19 + 23 = 42 pre-fold, + 7 added by the Codex
P1 fold = 49 — the arithmetic closes, no test vanished.

### The one residual failure, and the control that exonerates it

`test_check_pair_rail_matrix.py::TestDecideWithMatrixPerformance::test_case_a_p99_under_5ms`
fails only under `-n auto` load. It was NOT waved through on plausibility —
a **side-by-side control on a second, UNMODIFIED `git clone --local` of
`9c63750`** was run with the byte-identical command:

```
pytest .claude/hooks/tests/test_check_pair_rail_matrix.py \
       .claude/hooks/tests/test_a*.py .claude/hooks/tests/test_c*.py -q -n auto

control (HEAD, no patch): 2 failed, 3040 passed, 17 skipped, 29 xfailed  -> SAME test fails
overlay (patched):        2 failed, 3063 passed, 17 skipped,  6 xfailed  -> SAME test fails

# re-measured after the Codex P1 fold (patched side only — the control
# clone is unmodified, so it does not contain the 7 new tests):
overlay (post-fold):      2 failed, 3070 passed, 17 skipped,  6 xfailed  -> SAME test fails
```

The unmodified tree fails it identically, so the patch is not the cause.
Solo, 3 consecutive runs in EACH clone: 3/3 pass in both. This is the
documented perf-gate-under-load flake class
(`[[feedback-perf-gate-n20-load-flake]]`).

That control doubles as an independent check of the flip count: **29 xfailed
(control) − 6 xfailed (patched) = 23**, exactly the PLAN-162 strict xfails
that flipped, derived from a run that knows nothing about my arithmetic.

Worth stating because it was the real risk here, not a hand-wave: this test
*does* reach the changed code — `check_pair_rail._sentinel_grants_pair_rail_bypass`
lazily imports `check_canonical_edit` and calls `_find_sentinels` +
`_sentinel_grants_path` per iteration, and this patch adds work to both
(a realpath + ancestor walk per candidate; signing-material digests per
sentinel). The control is what rules that out, not the fact that
`check_pair_rail.py` is absent from the diff.

The 2 `xpassed` are the pre-existing non-strict advisory perf budgets in
`test_hook_latency.py` (`strict=False` by PLAN-113 W8 decision — reported,
never fails CI). Not caused by, and not affected by, this patch.

### Gates run on the patched overlay (all clean)

```
python3 .claude/scripts/check-claude-md-claims.py          -> (silent) OK
bash .claude/scripts/local/verify-counts.sh --no-tests --quiet -> (silent) OK
python3 .claude/scripts/check-test-env-hygiene.py         -> OK (337 flagged, all allowlisted)
bash .claude/scripts/check-contamination.sh               -> No contamination outside allowed zones
python3 -m py_compile <both hooks>                        -> OK
grep for PEP-604 runtime unions / match statements        -> zero hits (py3.9 clean)
```

---

## Fix units

### S1 — case-insensitive filesystem bypass (P0) — `PLAN162_FIX_CASEFOLD`

**Both rails**, as the instrument's `_in_both_rails()` demands: a half fix
leaves the flag False, the fixed half XPASSes, and strict-xfail fails the
gate.

* `check_canonical_edit.py`: added `_CANONICAL_GUARDS_FOLDED` +
  `_CANONICAL_PREFIXES_FOLDED` (both precomputed at import) and
  `_matches_canonical_guard` now lowers the rel once before the O(1)
  prefix bail-out and the glob loop.
* `check_arbitration_kernel.py`: added `_KERNEL_PATHS_FOLDED`;
  `_is_kernel_path` lowers the rel before matching.

**Both halves were required.** The prefix fast-path bails out *before* any
glob runs, so folding only the matcher would have left `.CLAUDE/settings.json`
inert — the guard would LOOK fixed. The instrument fences this explicitly
with a third `BOTH_RAIL_VARIANTS` row that varies the FIRST segment.

`str.lower()`, not `str.casefold()`, and the choice is documented in the
code: casefold expands `ß`→`ss`, changing segment LENGTH and therefore
what a glob matches. `lower()` covers the exploited ASCII class exactly,
and since identical inputs fold identically the normalization can only
ADD matches (over-classify = the safe direction), never remove one.

*Proved by:* `S1CaseFoldBypassTest` — 3 repros (predicate-level on both
rails, end-to-end canonical block, end-to-end kernel block) plus the
anti-OVER-block control (`.claude/NOTES.MD`, `docs/README.MD`,
`src/Main.PY` must stay unguarded) and the exploitability control that
writes through a case twin and asserts the overwrite.

### #1 + #10 — cache partition + wall-clock deadline — `PLAN162_FIX_1`

One marker, per the instrument's explicit warning that flag detection is a
SUBSTRING test (`PLAN162_FIX_1<digit>` would alias). Both halves ship in
the same patch (consensus C3: a deadline without the partition fires on
the 4.16 s the debate measured and denies the ceremony itself).

**Cache partition.** Added `_SIG_VERIFY_CACHE` (target-FREE) keyed by
`_compute_sig_cache_key()` over the sentinel's identity/bytes *plus*
digests of the three signing-material inputs — the `.asc`, the legacy
allowlist, and the ADR-121 registry — *plus the PATHS* of the latter two
(they are module-level seams; a different file is a different decision).
The GPG + dual-signer body was extracted verbatim into
`_verify_signature_rail()`, wrapped by `_signature_rail_ok()`.

`_GRANT_CACHE` is an **alias for the same dict object** as
`_SENTINEL_VERIFY_CACHE` — not a copy. `_compute_sentinel_cache_key`, the
7-field key shape, the `target_rel` position, and the
`_SENTINEL_CACHE_HITS/MISSES` counters are all pinned by
`test_sentinel_session_cache.py`; keeping the object identical is what
keeps those 15 tests green.

**Ordering is the #10 fix, not a style choice.** The signature rail now runs
BEFORE the grant fast-path. Had it stayed after, a mutated `.asc` would
still have hit a grant key computed only over `approved.md` bytes and
ridden a stale `True`. Running the material-keyed rail first makes a
revocation in any of the three files land immediately — closing the
"signer rotation window" PLAN-094 §8 had consciously accepted.

**Deadline.** `_HOOK_WALL_BUDGET_S = 4.0` (module constant, C3 — never
read from `settings.json` at runtime: the budget lives in the file this
hook guards, and JSON-parsing on the hot path worsens the very path being
optimized). Registered timeout measured from the live `settings.json`:
**exactly one** `check_canonical_edit` registration, `timeout: 5` — so
4.0 s leaves ~1 s to emit. Clock exposed as the module seam `_now`
(default `time.monotonic`) per S8, so the red-first test never sleeps.
Armed by `_start_wall_budget()` and cleared by `_reset_wall_budget()` in
`main()`'s `finally`; `main()` is now a thin wrapper over `_main_guarded()`
for exactly that reason — a module-scope deadline armed by one in-process
invocation would otherwise leak into the next caller in the same process
and fail it closed for no reason. Checked at the top of BOTH sentinel
loops (`decide()` and the multi-candidate scan in `main()`), fail-CLOSED
with `canonical_edit_hook_fault`. **No sentinel cap** — C2 removed it as a
regression (`_find_sentinels` returns sorted, so a cap drops the
highest-numbered pack, i.e. the ceremony the Owner just signed).

*Proved by:* `Finding1And10CachePartitionTest` (4 repros: M calls for
M sentinels x N targets, plus `.asc` / allowlist / registry byte-change
invalidation — all IN-PROCESS per consensus S5) and
`Finding1WallDeadlineTest` (registration-drift static check).
`test_1_control_grant_decisions_stay_target_specific` fences that the
partition did not let a grant for one target replay for another.

**Deliberately untouched:** the deadline-expiry BEHAVIOUR test
(`test_1_repro_expired_deadline_fails_closed_via_injected_clock`, lines
~875-925) stays `@pytest.mark.skip`. It is an unresolved contract conflict
(C2 fail-closed vs AGENTS.md §1 / CLAUDE.md §4 "timeout → breadcrumb +
allow") that needs an ADR. **The implementation picks fail-CLOSED**, which
is the side C2 ratified and the side this file already behaves on in three
other places — but the ADR still has to be written before the test is
re-enabled, and the CEO should treat "the code now takes a side the test
refuses to take" as a ceremony input, not a settled matter.

### #2 — depth-independent symlink rejection — `PLAN162_FIX_2`

`_find_sentinels` now does two depth-FREE checks instead of three
hard-coded levels: (a) walks every segment from `p` up to (excluding)
`base` rejecting any symlinked component, bounded at 64 hops as a runaway
guard; (b) asserts `realpath(p)` stays under `realpath(base)`.
Pattern-depth coupling is gone, so the next 6-segment pattern cannot
silently reopen the hole.

*Proved by:* `test_2_repro_symlinked_plan_segment_is_rejected`, with the
positive control (`p.parent` symlink, which HEAD already caught) proving
the probe is alive and the anti-over-block control proving an ordinary
sentinel is still discovered.

**Residual carried forward, not closed:** a symlink at `base` itself
(`.claude/plans`) defeats both forms — (a) excludes base, (b) resolves
base through the same link. The instrument names it; pinning today's
behaviour there would pin a bypass. Documented in the code comment.

### #3 + #8 — guard the guard-files — `PLAN162_FIX_3`

Added to **both** `_CANONICAL_GUARDS` and `_KERNEL_PATHS`:

* `.claude/security/sentinel-signers-registry.yaml`
* `.claude/policies/.drift-manifest.json`

Kernel tier because a sentinel that could grant an edit to the signer
registry would be bootstrapping its own successor. Per C10 the `.exists()`
gate was **not** inverted into "absence ⇒ fail-closed" — that needs a
definition of "expected" which is itself editable, and would make
DELETING a file the way to choose the posture.

*Proved by:* `Finding3And8GuardTheGuardfilesTest` — predicate-level on
both rails plus end-to-end blocks on both hooks, with the
guarded-neighbour control (`.claude/policies/guarded.yaml`) fencing that a
False was about the pattern list, not a broken repo_root.

Count assertions elsewhere are all `>=` (`test_check_canonical_edit_kernel_v2.py`
`>= 58` / `>= 30`, `test_kernel_subsumes_security_critical_lib.py` `>= 27`)
— checked before editing; adding entries is safe.

### #4 — scope containment — `PLAN162_FIX_4`

Three narrow rules (the original "parse only inside the markers" was
rejected in debate: it bricks 5 of 16 live sentinels).

1. New `_BEGIN_MARKER_RE` detects marker PRESENCE separately from a
   well-formed PAIR. A BEGIN with no valid pair now returns False instead
   of silently falling to the Tier-2 whole-file parser.
2. Oversize (> `_SCOPE_MARKER_CAP_BYTES`) REJECTS fail-closed, parsed by
   neither tier.
3. `_SCOPE_TERMINATOR_RE` gained the END marker as its first (cheapest)
   alternative, so a bullet after an END in a marker-less file is no
   longer collected.

**Chars-vs-bytes, decided explicitly** (C5 required a decision): the cap is
named in BYTES so it is now measured in BYTES
(`len(text.encode("utf-8", "surrogatepass"))`). HEAD compared `len(text)`
in CHARACTERS, which understated a non-ASCII sentinel's real size. Since
oversize is now a REJECT rather than a silent downgrade, the stricter
reading is also the safer one. `_SCOPE_MARKER_CAP_BYTES == 64*1024` is
unchanged and still pinned by `test_check_canonical_edit_markers.py:438`.

*Proved by:* three repros in `Finding4ScopeContainmentTest`, with the
twin control (`..._marker_region_without_scope_fails_closed`) proving the
oversize repro differs from its passing twin ONLY by size.

### #5b — `parse_error` fails CLOSED — `PLAN162_FIX_5B`

`main()`'s `event.parse_error` branch now emits a block with
`canonical_edit_payload_parse_error`. 5a (an EXCEPTION out of
`read_event`) is untouched and stays fail-OPEN — genuine infrastructure,
and the kernel sibling is fail-open identically there.

The code comment records that the council's "ADR-010 mandates fail-open"
justification was verified FALSE (zero occurrences of any failure-posture
text in that ADR; the only such text is this hook's own docstring, so
citing it is circular).

*Proved by:* `test_5b_repro_parse_error_must_block`, with
`test_5a_pin_read_event_exception_still_allows` fencing the over-correction
and `test_5b_control_wellformed_payload_is_unaffected` fencing over-block.

### #7 — `file://` URI candidates — `PLAN162_FIX_7`

New `_normalize_candidate_value()`, applied in the one function that
builds candidates. Rewrites LOCAL file URIs only (empty or `localhost`
authority); a `file://remote-host/...` URI, a different scheme, or a
percent-escape decoding to an embedded NUL is returned untouched. The
4 KiB length cap is still applied to the RAW value (normalization can only
shorten).

*Proved by:* `test_7_repro_file_uri_target_is_gated`, with
`test_7_control_plain_path_under_uri_key_is_gated` (the `uri` key IS
wired) and `test_7_control_non_canonical_file_uri_stays_allowed`
(anti-over-block).

### #9 — `blocked_tool` forensics — `PLAN162_FIX_9`

All **four** sites (`_emit_unlock_audit`, `_audit_block`,
`_audit_registry_unreadable` which carried `""`, and
`_audit_session_root_block`) now call `_blocked_tool_field()`. The value
is the event's tool name VALIDATED against a closed enum plus
`^mcp__[a-z0-9_]+$`; anything else becomes the literal `unknown`, never
truncated (truncation would let two distinct hostile names alias).
Plumbed via `_CURRENT_TOOL_NAME`, set once in `_main_guarded()` and
cleared in `main()`'s `finally` — `_emit_unlock_audit` sits deep in the
call graph with no event in scope.

*Proved by:* the behavioral repro, the SOURCE-level fence covering all
four sites at once (two are not economically reachable behaviorally), and
`test_9_pin_hostile_tool_name_never_lands_verbatim` — the half that turns
a forensics fix into a log-injection vector if it ships unvalidated.

The kernel hook's own `blocked_tool` literal is out of scope: C6 named
four sites in `check_canonical_edit`, and `FIXED_9` is an `_in_hook` flag.

### S2 — sentinel trust anchor under `env_override` — `PLAN162_FIX_S2`

Under `CEO_SENTINEL_UNLOCK` the GPG rail is skipped entirely, so the only
thing separating an Owner-signed sentinel from one the AGENT just wrote is
WHEN it appeared. `_sentinel_predates_session()` requires the sentinel to
exist in the tree at the commit named by `CEO_SESSION_ANCHOR_SHA`
(validated `^[0-9a-fA-F]{7,64}$`, proved via `git cat-file -e <sha>:<rel>`
with a 5 s timeout, memoized per process).

The pair-rail R2 correction is honored: git *tracked-ness* is never
consulted, because it is a statement about the index, not about who
authorized the file. Requiring an ENV var adds no new trust assumption —
it is the same primitive the unlock itself already rests on (a sub-agent
cannot set env in the parent shell).

*Proved by:* three negatives (untracked / staged / committed) plus the
anti-self-DoS control that takes the anchor AFTER the commit.

> ## ⚠️ TWO THINGS THE OWNER MUST RATIFY BEFORE THIS SHIPS
>
> **1. A real, named residual.** The rail arms only when the project is a
> git work tree (`.git` present); otherwise no proof mechanism exists and
> the legacy accept stands. **Consequence: `rm -rf .git` disarms this
> fix.** That is a genuine hole. It is what keeps the neighborhood green
> without a mass fixture rewrite (every existing unlock fixture builds a
> non-git tmp project), and it is stated in the code comment rather than
> buried — but it is a weaker fix than S2 describes, and calling it
> "closed" would be dishonest. Closing it needs an anchor form that does
> not depend on git, which is a separate decision.
>
> **2. It changes a documented OPERATOR contract.** ADR-119 and
> `SPEC/v1/sentinel-format.schema.md` document `CEO_SENTINEL_UNLOCK` +
> `_ACK` as sufficient. After this patch, inside a git work tree they are
> not: every ceremony script that exports `CEO_SENTINEL_UNLOCK` must also
> export `CEO_SESSION_ANCHOR_SHA`. **The ceremony scripts were NOT updated
> by this patch** (out of the assigned file scope) — landing the hook
> without updating them will make the next unlock-based ceremony fail
> closed. The instrument's own docstring flags `CEO_SESSION_ANCHOR_SHA` as
> "a proposed interface name, not an existing one"; renaming is allowed,
> dropping the requirement is not.

### S6 — interaction pass

`InteractionPassTest` passes: the #2 fix does not invert the #1 fixtures
(a legitimate sentinel beside a rejected symlinked one is still discovered
AND still grants), and #7 x #9 on the same event records the repo-relative
canonical path plus the validated tool name, never the raw URI.

---

## Neighborhood contract-pins REWRITTEN in this patch (the C7 precedent)

Four tests pinned exactly the postures PLAN-162 reverses. Per consensus C7
(`test_indeterminate_plan_skips`) they are rewritten in the SAME patch —
leaving them would have made the fix un-landable, and rewriting them later
would have left the closeout red. Each rewrite states in its docstring
what changed and why, so the diff is not a silent contract flip:

| File | Test | Was | Now |
|---|---|---|---|
| `test_check_canonical_edit.py` | `test_malformed_payload_allows` → `test_malformed_payload_blocks` | allow | block + `canonical_edit_payload_parse_error` |
| `test_check_canonical_edit_markers.py` | `..._only_begin_marker_falls_to_tier2` → `..._only_begin_marker_fails_closed` | allow | block |
| `test_fail_open_contract.py` | `test_check_canonical_edit_fail_open` | blanket "never block on any malformed stdin" | **narrowed for this hook only** — infra payloads still allow; the parse-error payload blocks. Other five hooks untouched. |
| `probes/test_canonical_edit_probe.py` | `test_hook_fails_open_on_malformed_stdin` → `..._fails_closed_...` | allow | block |

The `test_fail_open_contract.py` narrowing is worth flagging on its own:
that file's docstring cites "CLAUDE.md §5", a stale section reference, and
its blanket rule predates the PLAN-152 C4 doctrine correction now codified
in CLAUDE.md §4 (fail-open on INFRASTRUCTURE, fail-CLOSED on INPUT). The
split was **measured, not assumed** — probed all four payloads against the
patched hook:

```
empty               rc=0  {}                                    (parses, no target -> allow)
garbage             rc=0  {"decision":"block", ...parse_error}  (INPUT failure -> block)
json_missing_fields rc=0  {}                                    (parses -> allow)
null_tool_input     rc=0  {}                                    (parses -> allow)
```

Only the true parse-error payload blocks; the exit-0 / never-zero-emit
guarantee is asserted for all four.

## What is NOT in this patch

* **`ADR-164-AMEND-1`** (consensus S3) — a required ceremony deliverable,
  but a doc, not a fix unit; out of the assigned file scope.
* **`ADR-110-AMEND-2`**, the SHA-pin, the ADR count bump — separate
  ceremony inputs.
* **The R1 `check_budget` redesign** (C7) and its
  `test_indeterminate_plan_skips` rewrite — a rider, not a
  `check_canonical_edit` fix; the consensus keeps it separable (S7).
* **#6, #11 (DOC-GAP), #12 (ACCEPT with a named reopen trigger)** — no
  behavior change by disposition, so no code and no test.
* **The ADR settling the deadline-posture conflict** — see the #1 section.
* **Ceremony-script updates for `CEO_SESSION_ANCHOR_SHA`** — see the S2
  warning box.

## Scope note for the sentinel (consensus S7)

The Scope must keep the fail-closed hook fixes SEPARABLE from the riders,
so a pair-rail REJECT on a rider cannot trap them. This patch touches
exactly seven files and no rider:

```
.claude/hooks/check_arbitration_kernel.py
.claude/hooks/check_canonical_edit.py            <- canonical + KERNEL tier
.claude/hooks/tests/probes/test_canonical_edit_probe.py
.claude/hooks/tests/test_canonical_edit_plan162_findings.py   <- + Codex P1 fold
.claude/hooks/tests/test_check_canonical_edit.py
.claude/hooks/tests/test_check_canonical_edit_markers.py
.claude/hooks/tests/test_fail_open_contract.py
```

Both hooks are in `_KERNEL_PATHS`, so landing needs
`CEO_KERNEL_OVERRIDE` + `_ACK` in addition to the sentinel. The five test
files are not canonical-guarded (`hooks/tests/` is not; `_lib/tests/` is)
and need no Scope entry — but listing them in the ceremony record is
worthwhile precisely because they carry contract REVERSALS.

**Scope delta vs. the pre-fold artifact:** six files → seven. The added
file is the PLAN-162 instrument itself, which the pre-fold patch left
untouched (W1 landed it; W2 only flipped its xfails). It is a test file,
so the sentinel Scope block is UNCHANGED — no canonical path was added.

## Codex P1 fold (S292): gpg bounded by remaining budget

The staged artifact was regenerated to fold one pair-rail P1 raised by
Codex against the patch itself:

> **Bound GPG verification by the remaining hook budget** —
> `plan162-w2-fixes.patch:590-594`. When gpg or gpg-agent stalls, this
> call can block for 15 seconds although the hook is registered for 5
> seconds and the new internal deadline is 4 seconds. Because the
> deadline is checked only between sentinel iterations, the harness can
> kill the process before it emits the intended fail-closed decision,
> recreating the silent fail-open that ADR-164-AMEND-1 §3 explicitly says
> the patch prevents; pass a timeout derived from the remaining wall
> budget.

**The finding is correct, and it lands on a claim this ceremony already
makes.** ADR-164-AMEND-1 §3 D2 states, in the artifact staged next to
this one: *"The patch passes a timeout derived from the remaining wall
budget so a single hung `gpg` cannot ride past the deadline into the
harness kill."* The pre-fold code passed the `_lib.gpg_verify` default,
`timeout=15.0`. The ADR was describing the intent; the code had the
literal. This fold makes the text true rather than amending it down.

Why the polled deadline could not cover it on its own: `_wall_budget_
expired()` is read at the TOP of the sentinel loops, so it bounds only
what happens BETWEEN iterations. One stalled subprocess inside an
iteration is unobserved by construction — and a hook killed mid-verify
emits nothing, which the harness cannot distinguish from an allow.

### Before / after

| | Before (staged pre-fold) | After (this artifact) |
|---|---|---|
| ceiling per spawn | constant `15.0` (library default; 3x the 5 s registration) | `min(15.0, remaining − margin)`, floor `_GPG_MIN_SPAWN_S` |
| allowance too short to verify **and** emit | spawns anyway | does NOT spawn; latches, blocks fail-closed with the deadline reason + recovery route |
| stalled gpg, simulated wall for the event | **45.0 s** (3 sentinels x 15 s) | **3.5 s**, under the 4 s internal deadline and the 5 s registration |
| refusal in `_SIG_VERIFY_CACHE` | n/a | never memoized (a refusal is not a verdict) |
| budget fault on the LAST sentinel | generic "declare this path in Scope" block | `canonical_edit_hook_fault` + recovery route |

```python
# .claude/hooks/check_canonical_edit.py
_GPG_VERIFY_TIMEOUT_CAP_S = 15.0   # pinned to the _lib.gpg_verify default
_GPG_EMIT_MARGIN_S = 0.5           # wall reserved so the decision still EMITS
_GPG_MIN_SPAWN_S = 0.5             # floor: below this, do not fork at all

def _gpg_verify_timeout() -> Optional[float]:
    if _WALL_DEADLINE_AT is None:          # disarmed => historical behaviour
        return _GPG_VERIFY_TIMEOUT_CAP_S
    usable = (_WALL_DEADLINE_AT - _now()) - _GPG_EMIT_MARGIN_S
    if usable < _GPG_MIN_SPAWN_S:
        return None                        # DO NOT SPAWN
    return min(_GPG_VERIFY_TIMEOUT_CAP_S, usable)
```

Four coupled changes, all under the existing `PLAN162_FIX_1` marker (the
fold adds no new marker, so the file's feature-detect contract and the
23-xfail arithmetic are untouched):

1. `_verify_signature_rail` derives the ceiling from the remaining
   allowance; `None` => refuse the spawn and latch.
2. `_WALL_BUDGET_EXHAUSTED` latch (cleared by `_start_wall_budget` /
   `_reset_wall_budget`) makes `_wall_budget_expired()` report a spent
   allowance, so the refusal routes through the SAME fail-closed
   `_WALL_DEADLINE_BLOCK_REASON` — with its recovery route — instead of
   the generic "declare this path in Scope" block, which would
   misdiagnose a wall fault as a missing sentinel.
3. `_signature_rail_ok` does NOT memoize a refusal. Caching it would
   leave a `False` no gpg ever produced riding `_SIG_VERIFY_CACHE` for
   the rest of the process — finding #10 re-created inside its own fix.
   This was the one self-inflicted bug the fold could have introduced;
   it has its own red-first test.
4. `decide()` re-polls AFTER the sentinel loop: the allowance can run out
   DURING the last sentinel's verification, past the final top-of-loop
   poll.

**Unarmed callers are unaffected by construction.** With
`_WALL_DEADLINE_AT is None` — direct `decide()` callers, and importers
such as `check_pair_rail`, which lazily imports this module and calls
`_sentinel_grants_path` — the cap is returned unchanged. The fold narrows
the hook-invocation path only.

### Red-first proof (measured, not asserted)

The new tests were run against a **pre-fold hook** built independently:
pristine `git clone --local` at `9c63750` + the PRE-FOLD staged patch
(which `git apply --check` accepted clean), pointed at via the file's own
`PLAN162_HOOK_PATH` seam. The `PLAN162_FIX_1` marker is present in that
build, so `_XFAIL_1` is inert and the repros FAIL rather than xfail:

```
PLAN162_HOOK_PATH=<pre-fold clone>/.claude/hooks/check_canonical_edit.py \
  pytest .claude/hooks/tests/test_canonical_edit_plan162_findings.py \
         -k GpgSpawnBounded -q

5 failed, 2 passed        <- the 2 passing are the anti-vacuity CONTROLS
```

The headline failure is the finding, quantified:

```
AssertionError: 45.0 not less than or equal to 5.0 : a stalled gpg
consumed 45.0s of a 5.0s registration — the harness kills the hook
before it emits, which is the silent fail-open ADR-164-AMEND-1 §3 D2
claims to prevent (ceilings=[15.0, 15.0, 15.0])
```

Post-fold, the same 7 tests pass (`7 passed`). The two controls pass on
BOTH sides, which is what makes the 5 reds attributable to the ceiling
logic rather than to a fixture that never reaches gpg.

`Finding1GpgSpawnBoundedTest` (7 tests, `.claude/hooks/tests/test_canonical_edit_plan162_findings.py`):

| test | proves |
|---|---|
| `test_control_healthy_rail_still_verifies_and_allows` | anti-vacuity: the fixture DOES reach the signature rail and is allowed |
| `test_control_registration_is_discoverable` | anti-vacuity for the wall assertion: the settings.json walk matches exactly one registration (the S287 vacuous-gate class) |
| `test_repro_spawn_constants_leave_room_for_a_first_verify` | margin + floor < `_HOOK_WALL_BUDGET_S` (else the FIRST sentinel could never be verified — C3 self-DoS); cap pinned to the live `_lib.gpg_verify` default via `inspect.signature` |
| `test_repro_spawn_ceiling_never_exceeds_the_wall_allowance` | every ceiling handed to `verify_detached` fits the allowance |
| `test_repro_near_dead_deadline_refuses_to_spawn_gpg` | `calls == 0` and a fail-closed `canonical_edit_hook_fault` block |
| `test_repro_stalled_gpg_leaves_room_to_emit_the_decision` | total simulated wall ≤ (LIVE registered ceiling − emit margin) |
| `test_repro_spawn_refusal_is_not_memoized` | `_SIG_VERIFY_CACHE` stays empty after a refusal, and the sentinel verifies once the allowance is restored |

Two properties of the instrument worth recording:

* **No test sleeps.** A `_FakeClock` (injected through the `_now` seam the
  S8 addendum required) and a stub that advances it by exactly the
  ceiling it was handed simulate the stall. Real multi-second sleeps
  against a wall budget are the documented flake class
  (`[[feedback-perf-gate-n20-load-flake]]`).
* **Names dodge the serial auto-mark.** The root `conftest.py` marks any
  test whose NODE ID matches `budget|timeout|perf|latency|elapsed|…` as
  `serial`. These are deterministic, so "allowance" / "ceiling" /
  "deadline" are used throughout to keep them in the parallel lane — the
  trap `Finding1WallDeadlineTest` documented for W2.

### Regenerated artifact — verification

```
git diff 9c63750 -- <the 7 files>  > plan162-w2-fixes.patch   (1887 lines)
sha256: 01a57d7b3c9df46cc70f96e91f65e9438cf8e898a9a0d95949ae91b68ba0f21a

pristine `git clone --local` @ 9c63750:
  git apply --check plan162-w2-fixes.patch        -> clean
  git apply         plan162-w2-fixes.patch        -> 7 files modified
  pytest test_canonical_edit_plan162_findings.py  -> 49 passed, 1 skipped
  pytest <neighborhood + probes + fail_open>      -> 361 passed, 12 skipped
  python3 .claude/scripts/check-test-env-hygiene.py
                                                  -> OK (337 flagged, all allowlisted)
```

⚠️ **`MANIFEST.sha256` is now STALE** for two entries — both this NOTES
file and `plan162-w2-fixes.patch` were rewritten. Regenerate it before
the preflight `shasum -c` runs, or the fail-closed manifest gate will
(correctly) reject the pack.

---

## Codex r2 fold — three P1s IN the S2 trust anchor

Round 2 of the pair-rail read the *staged patch* (not HEAD) and found
three P1s in the sentinel trust-anchor control the W2 patch itself
introduced. All three are folded here under the marker
`PLAN162_FIX_S2R2` (a superstring of `PLAN162_FIX_S2`, so the W1
feature-detect flag `FIXED_S2` is unaffected).

Red-first was run against a *pre-fold* reference tree — a pristine
`git clone --local` @ `9c63750` with the previous `plan162-w2-fixes.patch`
applied — through the `PLAN162_HOOK_PATH` seam:

```
pytest test_canonical_edit_plan162_findings.py -k RoundTwo
  PLAN162_HOOK_PATH=<pre-fold hook>   -> 10 failed, 4 passed   (the 4 are
                                          the anti-vacuity controls)
  PLAN162_HOOK_PATH unset (folded)    -> 14 passed
```

Re-running that first line NOW yields **9 failed, 5 passed**, and the
difference is not drift: `test_p1_3_contract_surfaces_document_the_new_requirement`
deliberately reads the LIVE tree rather than `PLAN162_HOOK_PATH`, so once
the doc half of P1-3 landed it passes against either hook. The 10/4 line
is the measurement taken before the doc edits — i.e. the doc half was red
first too, and this is the only test in the class that a redirected hook
cannot make red again.

### P1-1 — anchored PATH is not anchored CONTENT

> *"`git cat-file -e` proves only that the path EXISTED at the anchor;
> the hook then parses the CURRENT attacker-modified bytes while skipping
> GPG."*

Confirmed and real. The attack needs no new capability: inside a
legitimate window, open any pre-existing unguarded `approved.md`, keep
its `Approved-By:` line, append one bullet to `Scope:`.

**Before:** `_sentinel_predates_session()` -> `git cat-file -e <sha>:<rel>`
-> bool; `_sentinel_grants_path` then parsed `sentinel_path.read_text()`.

**After:** `_unlock_trusted_text()` -> `(authorized, text)`, where `text`
comes from `git cat-file **blob** <sha>:<rel>`. The parser consumes the
anchored bytes; disk bytes are never consulted on that path.

Codex offered two remedies — compare-blob-and-reject-divergence, or
parse-the-anchored-content. **Chosen: parse the anchored content**, and
`test_p1_1_the_anchored_scope_is_what_governs` pins that choice so a
future swap is deliberate. Reason: SPEC section 4.1 explicitly permits
lifecycle text *outside* the signed markers to change (`Status:`,
`Verified-At:`), so reject-on-divergence would brick an unlock window
over a hand-edited `Status:` line — a false-reject in exactly the
recovery path P1-3 is about. Anchored-parse ignores that text, as the
grant logic already does.

### P1-2 — the git probe now fits the wall budget

Same class as the round-1 gpg fold, same two constants. New
`_git_anchor_timeout()`: `None` (= do not spawn) when
`remaining - _GPG_EMIT_MARGIN_S < _GPG_MIN_SPAWN_S`, else
`min(_GIT_ANCHOR_TIMEOUT_CAP_S, remaining - margin)`. On refusal it calls
`_mark_wall_budget_exhausted()` so the caller's next poll emits the
*wall-deadline* block rather than the generic one. The `timeout=5`
literal is gone. Budget refusals are **not** memoized
(`_ANCHOR_BLOB_CACHE` stores verdicts only) — the same contract the
round-1 fold gave `_SIG_VERIFY_CACHE`.

### P1-3 — DECISION: (ii) plus a second proof form, not (i)

**Option (i) — derive the anchor from HEAD — is REFUTED, and the W1
instrument already proves it.** `test_s2_repro_committed_in_session_sentinel_does_not_grant`
requires that a sentinel the agent *committed* inside the window does not
grant. A `HEAD` sampled at hook time contains exactly that commit.
Auto-deriving would re-open S2 while looking fixed.

Taken instead: **(ii) update every contract surface in this landing —
plus a second, git-free proof form so the documented recovery route
actually survives.**

The anchor alone does more than "require one more env var": it bricks the
*only* use ADR-119's own Context names for the unlock — *"ceremony
authoring where the .asc is being signed in parallel"*. A freshly
authored sentinel predates nothing, so **no value of
`CEO_SESSION_ANCHOR_SHA` exists that would let it through**. That is not
a documentation gap, it is the removal of a route. And it is load-bearing
elsewhere in this same pack: `Finding1WallDeadlineTest` justifies
fail-CLOSED on deadline expiry by pointing at *"the existing recovery
route (CEO_SENTINEL_UNLOCK + _ACK)"*. Silently removing it would knock a
leg out from under a decision made two findings away.

So the Owner may instead pin the sentinel's **content**:

```bash
export CEO_SENTINEL_UNLOCK_SHA256=$(shasum -a 256 approved.md | cut -d' ' -f1)
# space/comma-separate several for a multi-sentinel pack
```

Why this is not a weakening:

* it rests on the *same* trust primitive as the unlock itself — parent-shell
  env a sub-agent cannot set;
* it binds CONTENT, so it is strictly stronger than the anchor (which
  binds a path). Reading the value gains an attacker nothing (sha256
  preimage);
* it works in a non-git tree, where the anchor cannot arm — i.e. it *is*
  the git-free proof form the first draft deferred as "a separate
  decision";
* a pin that misses a given sentinel **falls through** to the anchor rail
  rather than terminating it, so pinning one file never self-DoSes a pack
  (`test_p1_3_control_pinning_one_sentinel_keeps_anchored_ones_working`);
* a **malformed** pin fails CLOSED for the whole window, anchor present or
  not — unparseable security input is never waved through (CLAUDE.md
  section 4).

Surfaces updated in this same patch (derived from
`grep -rln CEO_SENTINEL_UNLOCK`):

| file | change |
|---|---|
| `.claude/adr/ADR-119-sentinel-unlock-contract.md` | new **Invariant 5** — both forms, worked examples, the "capture the anchor BEFORE the session" warning, the named residual |
| `SPEC/v1/sentinel-format.schema.md` | section 3 override paragraph gains the provenance requirement plus both snippets |
| `docs/FAQ.md` | escalation step 3 gains the one-line rule plus pointer |
| `README.md`, `README.pt-BR.md`, `npm/README.md` | one-clause qualifier on the escape-hatch bullet (kept identical across the three copies) |

And the gate now **teaches** the value it requires: `_unlock_trust_hint()`
appends the rail name, the refusal code, and both `export` lines to the
block reason — but only when an unlock window was actually armed
(`test_p1_3_hint_is_absent_when_no_unlock_window_is_armed`). Without it,
an operator following the documented recipe reads *"declare this path in
the Scope: block"* about a path that already is.

`test_p1_3_contract_surfaces_document_the_new_requirement` reads ADR-119
and the SPEC from the LIVE tree and fails if either stops naming both env
vars — the doc update is a gate, not a promise in this file.

### NOT fixed here — for the Owner / lead

* `CEREMONY-2-RUNBOOK.md:210` ("`CEO_SENTINEL_UNLOCK` relanca a sessao se
  o guard reclamar de sentinel") is now incomplete in the same way. It is
  outside this agent's file assignment; the fix is one clause.
* `.claude/security/README.md:142` records the historical GENESIS
  ceremony's env line. Left alone deliberately — it is a record of what
  was run, not live guidance.
* `.claude/plans/PLAN-160/land-plan160.sh:209,357` sets the unlock in a
  **non-git** tmp tree, so the residual keeps it working; verified it is
  not broken by this fold.

### Residual, restated (Owner ratification: ADR-164-AMEND-1)

The anchor rail arms only in a git work tree; `rm -rf .git` disarms that
half (the digest pin is unaffected). And in a non-git tree a pin does not
tighten the *other* sentinels — a pin-miss falls through to the legacy
accept there, exactly as it falls through to the anchor rail in a git
tree. That is a decision, not an oversight, and it is written into the
module comment: the alternative is "pin one file, reject the whole rest
of the pack" in the one tree shape that has no second proof form.

### Regenerated artifact — verification

```
git diff 9c63750  > plan162-w2-fixes.patch     (2630 lines, 13 files)
sha256: be7c18792aca906413bcfbfa65fe38affa372ca68b6bc88728100c6c1da571ee

pristine `git clone --local` @ 9c63750:
  git apply --check plan162-w2-fixes.patch       -> clean
  git apply         plan162-w2-fixes.patch       -> 13 files, mode 755 kept
  pytest test_canonical_edit_plan162_findings.py -> 63 passed, 1 skipped
  pytest -k "canonical_edit or arbitration_kernel"
                                                 -> 337 passed, 13 skipped

overlay (the tree the patch is cut from):
  pytest .claude/hooks/tests/ -n auto -m 'not serial'
                                     -> 6051 passed, 35 skipped, 4 xfailed
  pytest .claude/hooks/tests/ -m 'serial'
                                     -> 459 passed, 2 skipped, 2 xfailed,
                                        4 xpassed  (the 4 xpasses are
                                        PRE-EXISTING — identical count on
                                        the pre-fold reference tree)
  check-test-env-hygiene.py          -> OK (337 flagged, all allowlisted)
  verify-counts.sh                   -> no drift
  check-docs-drift.py                -> 70 WARN, identical to the pre-fold
                                        baseline (advisory, rc=0)
```

WARNING: **`MANIFEST.sha256` is STALE again** — both this NOTES file and
`plan162-w2-fixes.patch` were rewritten by this fold. Regenerate before
the preflight `shasum -c`.
