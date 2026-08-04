# NF-08 — option (a): posture-toggle INVOCATION guard

Staged artifacts for the Owner. **Nothing was committed, pushed, or applied
to the live tree.** All work happened in a throwaway clone
(`scratchpad/nf08-overlay`, base `9c63750`); the two `.patch` files and this
note are the only things written outside it.

> **This implements OPTION (a) of NF-08. The (a)-vs-(b) choice is the
> Owner's.** Option (b) — keep model-rail invocation and rewrite the three
> signed comments to say what is actually true — is *not* implemented here,
> and it also requires re-ratifying OQ1-redo, because (b) changes what was
> ratified. If the Owner picks (b), discard both patches; the only reusable
> piece is the wording in §6 below.

---

## 1. Artifacts

| File | Base tree | Lands in |
|---|---|---|
| `nf08-invocation-guard.patch` | `main` @ `9c63750` | **ceremony 2** (edits the canonical hook `check_bash_safety.py`) |
| `nf08-night-mode-command-doc.patch` | `.claude/commands/night-mode.md` as it exists on `origin/plan-165-draft` | **W1-land** (`.claude/commands/*.md` is not canonical-guarded — a plain edit) |

`sha256`:

```
695ff471fec4ef6e9633309569eb284121bac6c1008015464eb2e6536452f1e0  nf08-invocation-guard.patch
a729518563f8b43bf032868ed185045d92d01e9e1d3de81b9f60b362b163378b  nf08-night-mode-command-doc.patch
```

> **SUPERSEDED ONCE.** `nf08-invocation-guard.patch` was regenerated after
> the cross-vendor review found two P1 bypasses in it — see the **APPENDIX**
> at the end of this file. The hash above is the CURRENT one; the earlier
> `c2fb0f7d…` appears further down in historical narrative and no longer
> matches any file on disk. `MANIFEST.sha256` still carries the old value
> for this patch and for this note, and must be regenerated before the
> ceremony preflight runs `shasum -c`.

**Deliberate deviation from the brief.** The brief asked for ONE patch
carrying hook + tests + command doc. That patch would apply to no tree that
exists: `.claude/commands/night-mode.md` is not in `main`, and the hook is
not in the W1-land diff. Worse, they are different *commits* — the hook edit
needs a sentinel, the doc edit does not. Splitting is the correct shape, not
a workaround. Both halves are verified below.

Order of application does not matter; they touch disjoint files.

## 2. What the matcher does

New in `check_bash_safety.py` (~233 lines incl. comments):

- `_E4_POSTURE_TOGGLE_SCRIPTS` — the guarded surface, one entry today
  (`.claude/scripts/night-mode.py`). A frozenset so a future posture writer
  is a one-line change.
- `_e4_check_posture_toggle_invocation(command)` — the matcher.
- Wired into `decide_command` immediately after `_e3`, as
  `Decision(allow=False, reason=…)` with **`destructive=False`**: this is a
  governance boundary, not a destructive-command class, so the ADR-175
  citation gate and the PLAN-154 fact gate can never release it.

The matcher walks tokens (same `shlex` configuration as `_e3`:
`punctuation_chars="();<>|&\`"`) tracking *command-word position* — index 0
and every token after a terminator — and denies when the toggle appears as
something a command would **execute**.

### 2.1 Design decision: the SCRIPT is the surface, not the subcommand

`status` is denied too, even though it is read-only. A carve-out for
`status` would key a **permissive** branch off argv parsing — the exact
shape the repo's fail-closed doctrine rejects (and `argparse` positional
handling is not a boundary I want the guard to depend on). The lockout risk
that normally argues against a blanket deny does not apply: the recovery
route is the ratified one (`!` prefix), always available, and Claude still
has a model-rail read of the posture via `/ceo-boot`'s advisory banner,
which is resolver-derived and needs no subprocess.

### 2.2 Division of labour with `_e3` (documented, and asserted by tests)

`_e3` matches WRITE shapes. It *incidentally* already denied the indirect
bodies — `bash -c '…'`, `eval`, `xargs`, `find -exec` — because the toggle
path is a literal `_CANONICAL_GUARDS` entry and `_scan_blob` substring-scans
those bodies. The round-3 review called that coverage "por acaso"; it is
now load-bearing and documented rather than accidental:

- **`_e3` blob-scan** → indirect bodies (keep the older canonical message).
- **`_e4`** → direct argv forms.

`test_bash_posture_toggle_invocation.py` pins both sides: the three
blob-scan vectors are in the BLOCK matrix (so a change to `_e3` that drops
them fails here), and `test_invocation_block_names_the_human_rail` excludes
exactly those three, so the split is asserted rather than assumed. A
coherence test also fails if `.claude/scripts/night-mode.py` is ever removed
from `_CANONICAL_GUARDS` while staying invocation-guarded (split-brain).

## 3. Forms COVERED

| Class | Example | Mechanism |
|---|---|---|
| interpreter + path | `python3 .claude/scripts/night-mode.py on` | script-operand extraction |
| direct exec | `./.claude/scripts/night-mode.py on` | command word is the path |
| bare relative | `.claude/scripts/night-mode.py on` | idem |
| absolute | `/abs/repo/.claude/scripts/night-mode.py on` | suffix match after `normpath` |
| `..`/`//` spellings | `.claude/scripts/../scripts/night-mode.py` | `normpath` (string-only, no FS hit) |
| quoting | `python3 ".../night-mode.py"`, `'…'`, `.claude/scripts/"night-mode.py"` | posix `shlex` |
| python variants | `python`, `python3`, `python3.11`, `/usr/bin/python3` | `_E4_PYTHON_RE` + `_e3_cmd_name` |
| interpreter flags | `python3 -u …`, `python3 -X importtime …`, `python3 -- …` | flag/value consumption |
| `-m runpy` | `python3 -m runpy .../night-mode.py` | `_E4_MODULE_PATH_RUNNERS` |
| shells | `bash .../night-mode.py`, `sh …` | shell family |
| shell heredoc | `bash <<EOF\npython3 .../night-mode.py on\nEOF` | shell family scans ALL segment positionals (`_e3_segment_positionals` skips the redirect clause and keeps collecting the body) |
| prefix runners | `exec`, `command`, `nohup`, `env`, `sudo`, `doas`, `setsid`, `stdbuf`, `xargs`, `time`, `nice -n 10`, `timeout 5` | prefix strip + flag/duration skip |
| env assignments | `FOO=1 python3 …`, `env FOO=1 python3 …` | `_ENV_ASSIGNMENT_RE` |
| stacked prefixes | `nohup env FOO=1 python3 …` | fixed-point strip |
| chaining / subshell | `echo hi && python3 …`, `; `, `\|\|`, `(…)`, `\| xargs python3 …` | terminator tracking |
| **post-`cd` basename** | `cd .claude/scripts && python3 night-mode.py on` | basename match **in execution position only** |
| **variable indirection** | `S=.claude/scripts/night-mode.py; python3 $S on` | conjunctive: assignment names the toggle **AND** a `$`-token sits in execution position |
| unparseable + names it | `python3 '.claude/scripts/night-mode.py on` | fail-CLOSED, order-independent of `_e3`'s parse gate |

Two of these deserve their rationale spelled out.

**Basename match.** `_e4_is_toggle_path` also matches the bare basename
`night-mode.py`. This is an over-approximation: `python3 /elsewhere/night-mode.py`
is denied too. It is confined to execution position (the function is only
ever called on a command word or a script operand), and it closes
`cd .claude/scripts && python3 night-mode.py on`, which no path-prefix rule
can see and which is the first thing anyone would type. A file named
`night-mode.py` in another project, *executed from this repo's session*, is
the whole false-positive surface.

**Variable indirection.** `shlex` does not expand `$S`, so the path is only
visible in the assignment. The rule is deliberately **conjunctive** —
assignment naming the toggle AND a `$`-token in execution position — so that
`S=.claude/scripts/night-mode.py; cat $S` stays ALLOWED. Blocking that read
would have been the easy version and the wrong one; there is an explicit
ALLOW twin for it in the test matrix.

## 4. Forms NOT covered — and why

These are honest residual gaps, not oversights. Each was considered and
left open because closing it costs a false-positive class worth more than
the gap:

1. **`python3 -` (stdin script) with a heredoc** —
   `python3 - <<EOF … EOF`. The python family takes the *script operand*
   only; `-` is consumed as a flag. Widening python to "all positionals"
   (as the shell family does) would block
   `python3 tool.py .claude/scripts/night-mode.py`, i.e. any tool that takes
   the writer's path as an argument — a read.
2. **Base64 / encoded bodies, `printf | sh`, and other re-encodings.** Out
   of scope for a governance rail. `_e3`'s blob-scan catches the literal
   forms; nothing catches an encoded one, here or anywhere else in the hook.
3. **A shell variable set in an EARLIER Bash call and exported.** The hook
   sees one command at a time; there is no cross-invocation state.
4. **`python3 -mpytest .claude/scripts/night-mode.py`** (attached `-m`) is
   BLOCKED, while the spaced `python3 -m pytest …` is ALLOWED. The attached
   spelling falls through the generic flag skip. Inconsistent, in the safe
   direction, on a spelling nobody types.

**Consequence for the ceremony-2 wording — read §6.** After this patch the
control is real but not absolute; the three signed comments should say what
it does, not "cannot".

## 5. Command-doc rewrite (`nf08-night-mode-command-doc.patch`)

`.claude/commands/night-mode.md` stops being a model driver:

- `allowed-tools: Bash, Read` → **`allowed-tools: Read`**.
- New section *"⛔ This command does NOT run the toggle — you do"* with a
  four-step instruction to Claude: parse the subcommand, print the `!`-prefixed
  line, print the reminder, **stop** (explicitly: do not call Bash, do not
  "verify" by running it).
- Every ```` ```bash ```` block that used to be an instruction to execute is
  now a plain block showing the operator's line, e.g.
  `! python3 .claude/scripts/night-mode.py on`.
- `status` keeps its full documentation, plus a paragraph explaining why it
  is denied to the model rail anyway and pointing at `/ceo-boot`'s
  resolver-derived banner as the model-visible read.
- Troubleshooting gains the entry operators will actually hit: *"Claude
  refused to run it for me"* → by design, run the `!` line.
- **Also fixes NF-11(a) in this file only**: the obsolete
  `+ disableAutoMode: "disable"` claim (removed by `9f53628`) is gone from
  the posture description. NF-11(a) still owns the other two sites
  (`night-mode.py:8`, `ADR-185:25`) — **dedupe with whoever takes NF-11.**

## 6. Wording the ceremony-2 comments should use

The three claims NF-08 falsifies are canonical and are not touched by these
patches. With option (a) applied they become *nearly* true; the honest
version, which survives a round-4 re-probe:

> Model-rail **invocation** of the toggle is denied by
> `check_bash_safety._e4_check_posture_toggle_invocation` (PLAN-165 NF-08):
> the writer as a command word or as an interpreter's script operand, plus
> the prefix-runner, heredoc and variable-indirection spellings. Encoded or
> cross-invocation indirection is out of scope. `on`/`off` are HUMAN actions
> — the `!` prefix or a terminal.

Avoid "removes model-rail invocation" and "only a human at the keyboard
can": those are the phrasings the round-3 probe falsified, and §4 keeps them
falsifiable.

## 7. Validation (exact counts, all reproducible)

Baseline = pristine `git clone --local` at `9c63750`.

**RED-first**, new test file against the UNPATCHED hook:

```
77 failed, 34 passed
  test_invocation_is_blocked ................ 38 failed,  3 passed
      (the 3 passing = the _e3 blob-scan vectors: bash -c / sh -c / eval)
  test_write_forms_still_blocked ............  8 passed   <- control
  test_benign_commands_still_allowed ........ 22 passed   <- control
```

The 30 regression/negative controls being GREEN before the fix is the point:
any red there after the fix is my regression, not a pre-existing condition.

**GREEN**, after the patch:

| Selector | Baseline | Patched | Delta |
|---|---|---|---|
| `test_bash_posture_toggle_invocation.py` | (n/a) | **120 passed** | +120 new |
| `.claude/hooks/tests/ -k bash_safety` | 211 passed, 1 skipped, 3 xfailed | **211 passed, 1 skipped, 3 xfailed** | **0** (the new file's name does not match this selector — this is the pure regression signal) |
| `.claude/hooks/tests/ -k bash` | 382 passed, 1 skipped, 3 xfailed | **502 passed, 1 skipped, 3 xfailed** | +120, exactly the new tests |

Other gates, run on the clean clone with the patch applied:

- `check-test-env-hygiene.py` → `OK: test-env hygiene clean (337 flagged files, all allowlisted)`. The new test touches no env var.
- perf microbench (PLAN-089 §4 AC8, 50 ms budget) → `n=300 p50=0.124ms p95=0.173ms p99=0.186ms`. The matcher's pre-filter (basename substring) short-circuits every command that does not name the toggle.
- `gen-command-skill-hook-map.py --check` → exit 0; `check-claude-md-claims.py` → exit 0. **My patch causes zero derived-surface drift.**

**Patch application**, on a fresh `git clone --local` (`9c63750`):

```
git apply --check nf08-invocation-guard.patch          -> clean
git apply        nf08-invocation-guard.patch           -> applied
git checkout origin/plan-165-draft -- .claude/commands/night-mode.md
git apply --check nf08-night-mode-command-doc.patch    -> clean
pytest .claude/hooks/tests/test_bash_posture_toggle_invocation.py -q
  -> 120 passed
```

### 7.1 Smoke — real stdin through the hook (same shape as the review's probe)

Run against the freshly-cloned + patched tree, `CLAUDE_PROJECT_DIR=$PWD`:

```
=== INVOCACAO ===
python3 .claude/scripts/night-mode.py on        -> BLOCK: ... INVOKES the night-mode posture toggle ('.c…
./.claude/scripts/night-mode.py on              -> BLOCK: ... INVOKES the night-mode posture toggle ('./…
bash -c "python3 .claude/scripts/night-mode.py on" -> BLOCK: bash 'bash' -c body references canonical p…
nohup python3 .claude/scripts/night-mode.py off &  -> BLOCK: ... INVOKES the night-mode posture toggle
cd .claude/scripts && python3 night-mode.py on  -> BLOCK: ... INVOKES the night-mode posture toggle ('ni…
S=.claude/scripts/night-mode.py ; python3 $S on -> BLOCK: ... INVOKES the night-mode posture toggle ('$S…

=== CONTROLES POSITIVOS (o probe esta vivo) ===
echo x > .claude/scripts/night-mode.py          -> BLOCK: writes to canonical path
echo x > .claude/settings.local.json            -> BLOCK: writes to canonical path
echo x > .claude/state/night-mode.json          -> BLOCK: writes to canonical path

=== CONTROLES NEGATIVOS ===
cat .claude/scripts/night-mode.py               -> ALLOW {}
grep -n RESTORABLE .claude/scripts/night-mode.py-> ALLOW {}
python3 -m pytest .../tests/test_night_mode.py  -> ALLOW {}
git add .claude/commands/night-mode.md          -> ALLOW {}
S=.claude/scripts/night-mode.py ; cat $S        -> ALLOW {}
python3 .claude/scripts/ceo-boot.py             -> ALLOW {}
echo hello                                      -> ALLOW {}
```

The three write controls are the review's own liveness proof, reproduced
unchanged: the probe is alive, so the ALLOWs are real ALLOWs.

### 7.2 Full hooks suite — GREEN

Complete `pytest .claude/hooks/tests/` on the clean clone with
`nf08-invocation-guard.patch` applied (the working diff hashed
byte-identical to the staged patch, `c2fb0f7d…`, before the run):

```
6586 passed, 36 skipped, 28 xfailed, 5 xpassed, 25 warnings in 409.36s
```

Zero failures.

Two earlier attempts at this run — one on the patched tree, one on the
**pristine baseline** — each died on a *different* test
(`test_adequacy_gate.py::test_no_sandbox_leak`, a global assertion over the
shared system tempdir, and
`test_lifecycle_edge_cases.py::TestOutputScanPerfRigorous::test_p99_1kb`,
perf under load). Both were the known "full suite under concurrent load
exposes flake classes" pattern, caused by several agents running suites at
once; the fact that the *unpatched* tree also failed is what identified them
as load flakes rather than regressions. The 6 586-passed run above was taken
once the machine was quiet, and supersedes them.

### 7.3 Fuzz — the matcher never raises

20 000 random commands built from an alphabet seeded with the toggle path,
shell metacharacters, quotes, backslashes, `$S`, `<<EOF`, `-c`, `-m`, `--`:

```
fuzz: 20000 commands, exceptions=0
```

Plus purity (same input → same output) and empty-input checks. This matters
because an exception here would reach `main()`'s catch-all, which fail-opens
to ALLOW — a raising matcher is a silently disabled matcher.

## 8. Finding for W1-land (outside NF-08, found while validating)

Importing `.claude/commands/night-mode.md` moves the command catalog
**26 → 27**, which puts `docs/COMMAND-SKILL-HOOK-MAP.md` in drift:

```
[gen-command-skill-hook-map] DRIFT: docs/COMMAND-SKILL-HOOK-MAP.md differs
+ | `/night-mode` | — | `.claude/scripts/night-mode.py` |
- Commands: 26
+ Commands: 27
```

`check-claude-md-claims.py` still exits 0 (it does not carry a command
count). Reproduced on a clone with only the W1-land doc imported, so it is
**not** caused by these patches — but W1-land must run
`gen-command-skill-hook-map.py --write` and commit, or CI goes red on a
tolerance-0 gate.

## 9. Concerns for the Owner

1. **(a) vs (b) is unmade.** Option (a) costs the slash command its ability
   to run anything, including `status`. If that UX loss is not worth it,
   (b) + re-ratification is the coherent alternative — but (b) must not be
   chosen by *default*, which is what landing W1-land unchanged would do.
2. **The comment wording is not fixed by these patches** (§6). Landing (a)
   without correcting "removes model-rail invocation" leaves a weaker
   version of the same overstatement NF-08 is about.
3. **Sentinel scope.** `nf08-invocation-guard.patch` touches the canonical
   `check_bash_safety.py`; `.claude/hooks/tests/` is not canonical-guarded
   (only `_lib/tests/` is), so the sentinel scope is the hook file alone.
4. **NF-11(a) overlap** — §5, last bullet.
5. **No audit event is emitted** on an `_e4` block, matching `_e3`'s
   behaviour. Deliberate: a new action would need registration in
   `_KNOWN_ACTIONS`, a SPEC row and a golden regen — i.e. it would grow this
   into the NF-07 ceremony. If the Owner wants the denial recorded, it
   belongs in the same pass as `night_mode_toggled`, not here.

---

# APPENDIX — Codex P1 fold (S292 review of this patch)

The cross-vendor pair rail read `nf08-invocation-guard.patch` and returned
**two P1 bypasses of the matcher this patch adds**. Both are real, both were
reproduced before any fix, and both are now closed. The patch was
regenerated; scope is unchanged (`check_bash_safety.py` +
`tests/test_bash_posture_toggle_invocation.py`).

## A1. The findings, verbatim in substance

* **P1-A (patch:162-166)** — "Tokenize before applying the basename fast
  path: shell concatenation can name the guarded script without the raw
  command containing the literal basename … a case variant such as
  `NIGHT-MODE.PY` does likewise on default APFS. This pre-filter returns
  before shlex normalizes either form → ALLOW."
* **P1-B (patch:209-216)** — "Consume value-bearing prefix-runner flags:
  `env -u FOO python3 …` / `sudo -u root python3 …` — skips only `-u`,
  treats `FOO`/`root` as the final command word, stops examining subsequent
  tokens → ALLOW."

## A2. Reproduction BEFORE the fix (red-first)

Against a clean clone at `9c63750` with the **previous** version of this
patch applied — i.e. exactly what the ceremony would have landed:

```
python3 .claude/scripts/night"-"mode.py on              ALLOW   <-- P1-A
python3 .claude/scripts/night''-mode.py on              ALLOW   <-- P1-A
python3 .claude/scripts/night\-mode.py on               ALLOW   <-- P1-A (backslash)
python3 .claude/scripts/NIGHT-MODE.PY on                ALLOW   <-- P1-A (APFS)
./.claude/scripts/Night-Mode.py on                      ALLOW   <-- P1-A
python3 .claude/scripts/night-mod?.py on                ALLOW   <-- glob (folded in)
env -u FOO python3 .claude/scripts/night-mode.py on     ALLOW   <-- P1-B
sudo -u root python3 .claude/scripts/night-mode.py on   ALLOW   <-- P1-B
timeout -s KILL 5 python3 …/night-mode.py on            ALLOW   <-- P1-B
env -u FOO ./.claude/scripts/night-mode.py on           ALLOW   <-- P1-B (direct exec)
```

Codex named two forms; the same two defects reach **27 distinct vectors**,
now all pinned. Running the new test file against the pre-fix matcher in
that clean clone: **57 failed, 137 passed**.

Two of the 29 new BLOCK vectors already passed pre-fix and are kept as
boundary pins: `--user=root` (attached long-form value) and a quote that
splits the *directory* half (`".claude/scr"ipts/…`, which leaves the literal
basename in the raw string).

## A3. Fix A — no pre-filter, fold case, cover globs

The `basename in command` pre-filter is **deleted**. It cannot be repaired:
any pre-filter over the raw string is defeated by whatever the shell
normalises away (quotes, empty quotes, backslashes, and — with globs — by
characters that are not in the name at all). The matcher now always
tokenizes.

* **Case**: comparisons run on `str.lower()` forms, the same spelling and
  the same rationale as the write rail's `PLAN162_FIX_CASEFOLD` (`lower`
  not `casefold`: casefold expands `ß`→`ss` and changes token length, hence
  what a glob matches). On a case-sensitive filesystem this over-blocks;
  that is the safe direction.
* **Globs** (`night-mod?.py`, `night-*.py`) are **not** in the codex
  finding. Folded in because they are the same class — a token that
  resolves to the guarded file without spelling it — and would have been
  the obvious next probe. Bounded by a literal-character floor of 4, so
  `python3 *.py` (3 literals) stays ALLOWED.
* **Documented residual**: `python3 .claude/scripts/*.py` stays ALLOWED. A
  dir-qualified glob rule would need to compare path tails, and its false
  positives (any directory named `scripts`) buy less than they cost.
* The **parse-failure** branch keeps its fail-closed deny, but now gates on
  the quote/backslash-stripped, case-folded raw string, so an unparseable
  command that has nothing to do with the toggle keeps `_e3`'s own
  fail-closed message instead of a confusing night-mode one.

### Cost of always tokenizing (the pre-filter's only justification)

Measured on this machine (CPython 3.9.6, darwin — the same interpreter the
whole verification below ran under, so the floor of the supported range is
what was measured), `decide_command` over a 6-command corpus, 3000
iterations each:

```
BEFORE (pre-codex-fix)  mean 119.6us      AFTER  mean 153.7us
delta +34.1us (+28.5%) = 0.068% of the governing budget
governing budget: p95 < 50ms per command (PLAN-089 §4 AC8,
                  test_perf_p95_under_50ms_advisory)
that gate, measured: p95 0.173ms -> 0.199ms   (advisory warn at 25ms)
```

`_e3` already tokenizes unconditionally with the identical shlex
configuration, so sharing one memoized tokenizer would drive the marginal
cost to ~zero. **Deliberately not done**: it would put `_e3`'s entire
matcher inside this patch's blast radius to buy 25us the budget does not
need. Recorded here so the choice is visible rather than rediscovered.

## A4. Fix B — resolve the whole runner chain

The walk no longer stops at the first non-flag token after a prefix runner.
It carries a **per-runner flag table** (`_E4_PREFIX_RUNNER_FLAGS`) with both
the value-bearing and the boolean flags, because the two error directions
have different costs:

* a value flag missing from the table → the value is examined as a command
  word **and** the scan continues one token further (`ambiguous`) → still
  denied, no bypass;
* a boolean flag wrongly recorded as value-bearing → the real command word
  is skipped and the script lands at command-word position → still denied,
  but `sudo -E cat <toggle>` would false-positive. Hence the boolean rows.

An **unknown** flag is therefore fail-closed-ambiguous, never silently
boolean; one unknown flag buys exactly one extra candidate position, which
is enough for `env --frobnicate VAL python3 <toggle>` without walking into
a settled command's own arguments (the shape that would false-positive on
`sudo -u root cat <toggle>`).

**Derivation of the table** (S291 lesson — a closed set written from memory
errs in both directions, so each row names its authority):

| runner | source |
|---|---|
| `env`, `xargs`, `stdbuf`, `nice` | this machine's `man 1 <cmd>` |
| `sudo` | this machine's `man 8 sudo` option list |
| `timeout`, `ionice`, `setsid` | GNU coreutils / util-linux documented synopsis |
| `doas`, `time` | documented synopsis only — **the binaries are absent on darwin, so the man page could not be read.** Weakest rows; both fail-closed if wrong in the value direction. |

`test_every_prefix_runner_has_a_flag_table_entry` derives its assertion from
`_E4_PREFIX_RUNNERS` (no runner without a row, no row without a runner, no
flag classified as both).

## A5. Verification

| check | result |
|---|---|
| new tests vs **pre-fix** matcher (clean clone @`9c63750` + old patch) | **57 failed, 137 passed** (red-first) |
| `test_bash_posture_toggle_invocation.py` after fix | **194 passed** (was 191 collected / 137P+54F) |
| `-k "bash_safety or bash_canonical or bash_posture or bash_citation or git_bypass"` | **541 passed**, 1 skipped, 3 xfailed — baseline with the old patch was **467 passed**, 1 skipped, 3 xfailed; delta **+74 = exactly the tests added** (58 BLOCK + 13 ALLOW + 3 structural) |
| perf gate `test_perf_p95_under_50ms_advisory` | passes, p95 0.199ms |
| stdin smoke through the real hook (`PreToolUse` JSON on the hook's stdin) | **24/24**: 10 new BLOCK, 3 original review forms BLOCK, 11 negative controls ALLOW |
| `git apply --check` of the regenerated patch, clean clone @`9c63750` | applies cleanly; 194 tests pass there |

New negative controls (all ALLOW, all were ALLOW pre-fix too — they are the
false-positive twins of Fix B and the glob rule):
`sudo -u root cat <toggle>`, `sudo -u root grep -n MODES <toggle>`,
`env -u FOO cat <toggle>`, `env -C /tmp head -20 <toggle>`,
`sudo -E cat <toggle>`, `sudo -En cat <toggle>`,
`echo x | xargs -I {} cat <toggle>`, `nohup cat <toggle>`,
`sudo -u root git log --oneline -- <toggle>`,
`timeout -s KILL 60 python3 -m pytest <toggle>`, `python3 *.py`,
`python3 .claude/scripts/*.py`, `python3 tools/*.py --check`.

## A6. NEW concern for the Owner — the BASH WRITE rail is still case-blind

Found while validating the case fold; **outside this patch's scope, not
fixed here.** With the full ceremony-2 pack applied to a clean clone
(`plan162-w2-fixes.patch` + `deny-write-twins.patch` at `9c63750`):

```
Edit/Write KERNEL rail     _is_kernel_path('.claude/settings.JSON')      = True   (fixed by W2)
Edit/Write CANONICAL rail  _is_canonical('.claude/settings.JSON')        = True   (fixed by W2)
BASH write rail            echo x > .claude/settings.JSON                = ALLOW  <-- still open
                           cp /tmp/evil .claude/Settings.json            = ALLOW
                           cp /tmp/evil .claude/hooks/CHECK_BASH_SAFETY.PY = ALLOW
```

`PLAN162_FIX_CASEFOLD` folds `_KERNEL_PATHS` and `_CANONICAL_GUARDS` inside
`check_canonical_edit.py` / `check_arbitration_kernel.py`. But
`check_bash_safety._e3_check_canonical_path_write` carries its **own local**
`_is_canonical()` which imports the UNFOLDED `_CANONICAL_GUARDS` and calls
`_fnmatch_segments` directly — a **third site** of S1 that "BOTH rails" does
not reach. On APFS a case variant still overwrites the real file through
Bash. This matters directly for PLAN-165 p1-corrected, whose stated purpose
is closing the Bash rail.

It belongs in the W2/S1 patch (same marker, same rationale, same test file),
not here — folding it into this patch would expand an NF-08 sentinel scope
into PLAN-162's, and the two would collide on the same function.

## A7. Second concern — patch base of the DOC patch

`nf08-invocation-guard.patch` applies standalone at `9c63750` (verified).
`nf08-night-mode-command-doc.patch` does **not**: `.claude/commands/night-mode.md`
does not exist at `9c63750` — it arrives with the PLAN-165 W1 merge, as does
`.claude/scripts/night-mode.py` itself. So the ceremony must land W1 first,
or apply the two nf08 patches at the post-merge base. (The guard is
token-based and does not need the script to exist; its coherence test passes
at `9c63750` because `_CANONICAL_GUARDS` already lists the path — guard
ahead of file, the correct direction.)

## A8. Self-review round on the codex fix — NINE more bypasses, all verified executing

Re-probing the fix on this repo's own platform found that folding the PATH
without folding the COMMAND NAME closes only half of P1-A, and that the
matcher never covered command substitution at all. **Every one below was
confirmed to actually execute before being pinned** (a `print()` probe run
through each form), so these are bypasses, not theory:

```
PYTHON3 .claude/scripts/night-mode.py on              ALLOW  -> now BLOCK
Python3 ...                                           ALLOW  -> now BLOCK
/usr/bin/PYTHON3 ...                                  ALLOW  -> now BLOCK
BASH .claude/scripts/night-mode.py on                 ALLOW  -> now BLOCK
SUDO -u root python3 ...                              ALLOW  -> now BLOCK
ENV  -u FOO  python3 ...                              ALLOW  -> now BLOCK
python3 $(echo .claude/scripts/night-mode.py) on      ALLOW  -> now BLOCK
python3 <backtick>echo .../night-mode.py<backtick> on ALLOW  -> now BLOCK
$(echo ./.claude/scripts/night-mode.py) off           ALLOW  -> now BLOCK
```

Proof that the interpreter-name case class is real on this filesystem,
rather than inferred from "APFS is case-insensitive":

```
$ PYTHON3 /tmp/nf08probe.py            -> EXECUTED-via-/tmp/nf08probe.py
$ /usr/bin/PYTHON3 /tmp/nf08probe.py   -> EXECUTED-via-/tmp/nf08probe.py
$ ENV -u FOO python3 /tmp/nf08probe.py -> EXECUTED-via-/tmp/nf08probe.py
$ python3 $(echo /tmp/nf08probe.py)    -> EXECUTED-via-/tmp/nf08probe.py
```

**Fix**: `_e3_cmd_name(tok).lower()` before interpreter / prefix-runner
classification (one line, the same ratified over-block direction as the path
fold), plus `_e4_substitution_body_names_toggle` — which keeps the matcher's
existing CONJUNCTIVE shape for indirection: the substitution must sit in an
EXECUTION position (a command word, or an interpreter's script operand) AND
the toggle must appear inside it. Reads are untouched, pinned by five new
negative controls — `X=$(cat <toggle>)`, `echo $(cat <toggle>)`,
`N=$(wc -l < <toggle>)`, `echo $(grep -c ... <toggle>)` and
`python3 $(echo tool.py) --check` — all ALLOW.

**Scope note for the Owner.** The command-NAME fold is not separable from
the codex P1-A fix: shipping the path fold alone would close
`NIGHT-MODE.PY` while leaving `PYTHON3 night-mode.py` open — i.e. it would
restate the exact failure NF-08 exists to correct, a signed claim that a
rail is closed when it is not. The SUBSTITUTION rule IS separable (one
helper plus two branches, ~45 lines) and can be dropped without touching
either P1 fix, if the ceremony prefers the minimal patch.

### Final counts

| check | result |
|---|---|
| `test_bash_posture_toggle_invocation.py` | **219 passed** (194 after the P1 fixes alone; 137P/54F pre-fix) |
| `-k "bash_safety or bash_canonical or bash_posture or bash_citation or git_bypass"` | **566 passed**, 1 skipped, 3 xfailed — baseline with the OLD patch was **467 passed**; delta **+99 = exactly the tests added** |
| full `.claude/hooks/tests/` | **6660 passed**, 36 skipped, 28 xfailed, 5 xpassed, 0 failed |
| perf gate `test_perf_p95_under_50ms_advisory` | p95 **0.196ms** against a 50ms budget |
| stdin smoke through the real hook | **30/30** — 17 BLOCK (incl. the 3 original review forms), 13 ALLOW |
| interpreter | CPython **3.9.6**, the repo's supported floor; stdlib-only (`fnmatch` added — stdlib) |

### MANIFEST.sha256 — action required before the ceremony

Both staged files were rewritten, so `MANIFEST.sha256` lines 14-15 are STALE
and the preflight `shasum -c` will fail closed. The manifest is outside this
agent's file assignment and was deliberately NOT edited — regenerate the two
rows with:

```
cd .claude/plans/PLAN-162/ceremony-2-staged/
shasum -a 256 nf08-invocation-guard.patch nf08-invocation-guard-NOTES.md
```

---

# APPENDIX 2 — Codex r2 fold: executable ALIASES (P1)

Round 2 of the cross-vendor review, against the patch APPENDIX 1 produced.

> "The matcher recognizes only tokens whose SPELLING resembles the protected
> path, so `ln -s .claude/scripts/night-mode.py /tmp/nm && python3 /tmp/nm on`
> remains allowed […] Python then follows the symlink, and night-mode.py
> resolves `__file__` back into this repository and changes the posture,
> defeating the OQ1-redo boundary."

## 1. The finding is real — measured before anything was written

Not reasoned about; run. A symlink under the scratchpad pointed at the
merged clone's `night-mode.py`:

```
$ python3 <scratchpad>/alias-probe/nm on
night-mode: ON — next session starts with permissions.defaultMode='acceptEdits' …
night-mode-event mode=acceptEdits previous_mode=absent result=applied
$ cat <clone>/.claude/settings.local.json
{ "permissions": { "defaultMode": "acceptEdits" } }
```

The mechanism is `REPO_ROOT = Path(__file__).resolve().parents[2]`:
`resolve()` follows the link, so the script re-anchors itself in the REAL
repository while the command line names nothing recognisable.

## 2. Re-probing widened the class — a second member codex did not report

The same probe run against `cp`, `install` and hard links found that only
ONE of them re-anchors, and found one bypass the finding does not mention:

| vector | result | why |
|---|---|---|
| `ln -s <toggle> /tmp/nm` then run it | **ARMED THE POSTURE** | `resolve()` follows the link home |
| `cp <toggle> .claude/scripts/nm2.py` then run it | **ARMED THE POSTURE** | `parents[2]` of a copy two levels deep IS the real repo root |
| `cp <toggle> /tmp/nm.py` | refused | NM-04: `/tmp` is not an installed project |
| `cp <toggle> /tmp/fake/.claude/scripts/nm.py --project-root <repo>` | refused | NM-04 confinement |
| `ln <toggle> /tmp/nm` (HARD link) | refused | a hard link is a real dirent; `resolve()` does not redirect it |

The renamed-copy row matters for the FIX CHOICE: no rule about `ln` would
have caught it, which is the clearest available evidence that a matcher over
command spellings is the wrong place to put this boundary.

## 3. Layer decision — (iii) BOTH, weighted on (ii)

Asked for as an (i)/(ii)/(iii) choice with a justification. It is (iii),
but the two halves are not equal partners.

**Why the matcher cannot own this (the (i)-only case fails).**

1. It matches SPELLINGS; an alias exists to have a different one.
2. Deciding at EXECUTION time whether `/tmp/nm` is the toggle requires
   resolving an attacker-supplied path on EVERY Bash command. That means an
   FS syscall inside the hook's latency budget, a `RuntimeError` on a symlink
   loop — the exact fail-OPEN class the S277 pair rail found in this repo's
   own draft of `check_canonical_edit.py` — and a TOCTOU window in which the
   alias is created after the check. `_e4` is deliberately string-only
   (`normpath`, no FS hit); this patch does not change that.
3. The alias need not be created by a command the matcher ever sees: a
   previous session, `git checkout` of a branch carrying a symlink,
   `os.symlink`, `tar -x`, `rsync -l`, or the operator's own hand.

**Why the script-level guard is the boundary (the (ii) case).** It holds
however the alias came to exist, covers BOTH members of the class, and holds
even if the hook rail never runs. It is also cheap: two path comparisons.

**Why the matcher prong is still worth having.** Blocking the CREATION of a
link naming the toggle is the earliest and clearest signal, costs ~20 lines,
and needs no FS access. An agent staging an alias is already outside the
ratified path; telling it so at that moment is better than at execution.

**Scope of the matcher prong: LINKS ONLY. `cp` is deliberately allowed.**
A copy is a SNAPSHOT, not a second live entry point — the self-path guard
refuses to run it, so it is inert. Blocking `cp` would cost two workflows
that are real, not hypothetical:

- backing the file up before editing it (done in THIS ceremony —
  `scratchpad/night-mode.pre-insert.py`);
- `install.sh` copying the toggle into an ADOPTER repo's own
  `.claude/scripts/night-mode.py`, where it is legitimately that repo's
  toggle (verified: `install.sh` copies per-file at lines 917/1096/1349/1386).

The decision is pinned by `test_copy_is_deliberately_not_an_alias`, which
fails if someone later adds `cp` to `_E4_LINK_RUNNERS` without deleting the
test and saying why.

## 4. THIRD ARTIFACT — `nf08-self-path-guard.patch`

The (ii) half edits `night-mode.py`, which does not exist on `main`. It is a
separate patch against the MERGED tree.

| file | base | lands in |
|---|---|---|
| `nf08-invocation-guard.patch` | `main` @ `9c63750` | **ceremony 2** (canonical hook — needs a sentinel) |
| `nf08-self-path-guard.patch` | merged tree, **after** `w1-land-fixes.patch` | **W1-land** (`.claude/scripts/night-mode.py` is not canonical-guarded on the branch) |
| `nf08-night-mode-command-doc.patch` | `.claude/commands/night-mode.md` from `plan-165-draft` | **W1-land** |

**Order of application (load-bearing for the self-path patch only):**

```
1. merge plan-165-draft into main
2. git apply w1-land-fixes.patch          # NF-07 + NF-09
3. git apply nf08-self-path-guard.patch   # NF-08b   <- requires step 2
4. git apply nf08-night-mode-command-doc.patch
```

Step 3 touches `night-mode.py` and `tests/test_night_mode.py`, both of which
`w1-land-fixes.patch` also edits; applying it first will conflict. The other
two patches are order-independent (disjoint files). Verified against the
rehearsal clone at `4cdf754` ("REHEARSAL: W1-land fixes NF-07+NF-09"):
`git apply --check` OK there, and correctly REFUSED against plain `main`
("No such file or directory") — a negative control that the patch really is
merged-tree-only.

## 5. What the self-path guard does

`_self_path_diagnostic(anchored, real)` — PURE, no filesystem access, so it
is drivable from tests without a real installation (the S285 shape: a
fail-closed validator must be testable outside the thing it validates).
`_check_self_path()` is the thin resolver that feeds it, catching `OSError`
and `RuntimeError` (symlink loop) and refusing on either.

Two refusals:

1. `real != <its repo>/.claude/scripts/night-mode.py` → renamed/relocated copy.
2. `anchored != real` → the FINAL path component is a link, i.e. an alias.

`anchored` is `invoked.parent.resolve() / invoked.name` — ancestors resolved,
final component left alone. **This is the false-positive fix, and it is not
optional:** `/tmp` is a symlink to `/private/tmp` on this platform, and an
operator whose repo path traverses any symlinked directory would otherwise be
locked out of their own toggle by a fail-closed gate landing on the useless
side. Pinned by `test_diagnostic_tolerates_a_symlinked_ANCESTOR`.

Wired as the FIRST pre-dispatch check in `main()`, before the NM-04 root
confinement, and emitting the NM-05/NF-07 record pair on `on`/`off` — the
audit row lands in the REAL repository the alias points into, which is
exactly where the attempt belongs. `status` is refused too, matching `_e4`'s
scope decision (the SCRIPT is the surface).

The structural pin `_MAIN_RECORD_PATHS` moved 3 → 4. That bump is the
INTENDED cost of adding a refusal path — the pin exists so a new terminating
path cannot be wired to one record helper and not the other.

## 6. Verification (run FROM the patches, not from the overlays)

Both patches were applied to fresh `git clone --local` trees and everything
below was re-run there (C4, S284: verify claims, not reports).

| check | result |
|---|---|
| red-first, matcher | **26 failed** / 227 passed before the fix (13 alias vectors x 2 tests) |
| red-first, script guard | **10 failed** / 1 passed before the fix — the 1 pass is the positive control `test_canonical_invocation_is_the_positive_control`, which proves the fixture works |
| `test_bash_posture_toggle_invocation.py` (from the applied clone) | **255 passed** (219 -> 255; +36 = 14 alias vectors x 2 + 6 FP twins + 2 structural tests, minus the 1 excluded from the human-rail test) |
| full `.claude/hooks/tests/` (nf08 overlay) | **6721 passed**, 36 skipped, 28 xfailed, **5 xpassed**, 0 failed |
| the 5 XPASS | pre-existing ADVISORY perf budgets, all `strict=False` (PLAN-113 W8 / PLAN-125 / PLAN-154) — never fail CI, unrelated to this patch |
| `test_night_mode.py` (from the applied merged clone) | **110 passed** |
| full `.claude/scripts/tests/` (merged tree) | **4882 passed**, 24 skipped, 0 failed |
| live-fire, symlink alias, FROM the patched clone | `result=refused`, **no overlay written** |
| live-fire, renamed copy inside the repo | `result=refused`, **no overlay written** |
| live-fire control, canonical `on`/`status`/`off` | round-trip clean, overlay written and removed |
| `git apply --check` in clean clones | all three OK; self-path patch correctly REFUSED on plain `main` |

## 7. Concerns for the Owner

1. **`nf08-night-mode-command-doc.patch` is now slightly incomplete.** It
   documents the `!` rail but says nothing about the alias refusal, so an
   operator who hits `NF-08b` will not find it in the command doc. That file
   is outside this agent's assignment and was NOT edited. One paragraph.
2. **`MANIFEST.sha256` is stale for three rows now** (two rewritten patches
   plus one new file) and the preflight `shasum -c` fails closed. Current
   hashes:
   ```
   3497de1da1a95cf4fd0eb394324768b692e622e31ed1ddc2b18663db5ad9a47e  nf08-invocation-guard.patch
   f131bdebed768aae29c1501b5c645ea631a7feb65e23809e854f767de7ccce36  nf08-self-path-guard.patch
   7622b620742ddec667876a7674b5a64d50ececfa0e8600078325de56ee699440  workflows-fixes.patch
   ```
   (`nf08-invocation-guard-NOTES.md` and `workflows-fixes-NOTES.md` changed
   too — rehash after this file.)
3. **Residual, accepted:** an alias created OUTSIDE a Bash command the hook
   sees (a prior session, `git checkout`, the Owner's hand) is not prevented
   — it is REFUSED AT EXECUTION by the self-path guard. That is the design,
   not a gap: prevention lives where it can be complete.
4. **Residual, accepted:** the guard compares paths, so a bind mount or a
   copy-on-write clone of the whole repository presents as its own
   installation and manages its own overlay. That is correct behaviour (it
   IS a different installation), and NM-04 confinement already prevents it
   from reaching across.

---

# APPENDIX 3 — Codex r3 fold: newline separators + expansion-built paths (2 x P1)

Round 3 of the cross-vendor review, both findings against THIS patch. Both
are real, both were measured as ALLOW before anything was written, and both
land on the matcher two previous rounds had already hardened — which is the
argument for the rail, not against it.

## 1. The findings, verbatim in substance

**P1-A — "Treat newlines as Bash command separators"** (`patch:536-538`):

> "`shlex` treats a newline as whitespace here, while the walker resets
> `at_cmd_word` only for `_E3_TERMINATORS`. Thus `echo ok\npython3
> .claude/scripts/night-mode.py on` is ALLOWED even though Bash executes the
> second line and invokes the protected toggle; newline boundaries must be
> preserved or handled before tokenization."

**P1-B — "Reject expansion-built toggle paths"** (`patch:618-621`):

> "The execution-position check only recognizes literal paths or variables
> whose assigned value is ALREADY the complete toggle path. For example,
> `X=; python3 .claude/scripts/night${X}-mode.py on` returns allow, after
> which Bash expands the canonical filename and the script's self-path guard
> accepts it."

## 2. Red-first: 26 vectors proven ALLOW before the fix

Added to `test_bash_posture_toggle_invocation.py` as `NEWLINE_SEPARATOR_VECTORS`
(15) and `EXPANSION_BUILT_PATH_VECTORS` (16), plus 4 structural tests and 25
new ALLOW twins. Baseline 255 passed -> 345 passed.

Of the **31** new deny vectors, **26 were genuine bypasses** (returned ALLOW
against the pre-r3 overlay) and 5 were already covered — pinned anyway so a
refactor cannot narrow them:

```
ansi_c_quoting_as_cmd_word              locale_translation_quoting
ansi_c_quoting_builds_the_dash          newline_crlf_line_ending
ansi_c_quoting_whole_basename           newline_second_line_direct_exec
expansion_after_newline                 newline_second_line_interpreter
expansion_backtick_in_basename          newline_then_alias_creation
expansion_bare_var_in_basename          newline_then_case_folded
expansion_braced_var_mid_stem           newline_then_prefix_runner
expansion_dollar_paren_in_basename      newline_then_substitution
expansion_empty_var_in_basename         newline_third_line
expansion_in_alias_creation             line_continuation_before_direct_exec
expansion_plus_case_variance            line_continuation_before_script
expansion_plus_glob                     line_continuation_in_prefix_chain
expansion_under_prefix_runner           expansion_var_in_basename_as_cmd_word
```

Already-green pins: `newline_first_line`, `newline_after_and_operator`,
`newline_after_semicolon`, `newline_then_var_indirection`,
`expansion_in_directory_half`.

**All 74 ALLOW vectors — the 49 pre-existing plus the 25 added here — pass
against the PRE-r3 overlay too.** That is the check that matters for a
widening fix: the negative controls were already green, so every one of them
is a guard against THIS fold over-blocking, not a pre-existing pass being
re-counted as a win.

## 3. Fix A — quote-aware newline normalisation, BEFORE tokenizing

`_e4_normalise_command()` runs first and rewrites the two Bash line
constructs shlex does not model:

* an UNQUOTED newline becomes `_E4_NEWLINE_SEPARATOR` (`" ; "`);
* `\<newline>` — a LINE CONTINUATION — is REMOVED, as Bash removes it.

**The separator is SPACE-PADDED, and that is load-bearing.** shlex returns a
RUN of punctuation characters as ONE token, so a bare `;` appended to `&&`
tokenizes as `'&&;'` — a token in no terminator set. A "fix" that inserted a
bare `;` would have LOST the boundary it meant to add, at `foo &&<newline>bar`.

**Rejected first: `punctuation_chars`.** The obvious fix is to hand shlex the
newline as punctuation. Measured — it has NO EFFECT: shlex checks
`self.whitespace` before `punctuation_chars`, and `\n` is in whitespace by
default. Removing it from `whitespace` instead makes `ok\npython3` a single
WORD, which is worse. The token dump is in the session scratchpad
(`tok_probe.py`); the pre-tokenize rewrite is the only sound route.

**The continuation half was NOT in the finding.** It surfaced while probing:
shlex's escape handling turns `\<newline>` into a literal-newline WORD, which
settled as a bogus command word and pushed the real script operand into a
non-command position. `python3 \<NL> <toggle> on` was ALLOWED for a different
reason than the finding's vector, through the same blind spot.

**Quote-awareness is the whole reason this is a scanner and not a
`str.replace`.** A newline inside quotes is literal DATA in Bash
(`git commit -m "subject\n\nbody"`), and turning it into a separator would
manufacture command words out of prose — operator DoS on a hook that runs on
EVERY Bash command. Three ALLOW twins pin it: `newline_inside_single_quotes`,
`newline_inside_double_quotes`, `newline_in_commit_message`. An escaped
BACKSLASH is consumed as a pair, so `echo 'a\\'` followed by a newline keeps
its boundary instead of having it eaten.

## 4. Fix B — a second pass over the EXPANSION SKELETON

`_e4_check_posture_toggle_invocation` is now an orchestrator over two passes
of the same walk (`_e4_scan`):

1. **LITERAL pass**, on the normalised command. Owns every rule that reads
   the text as written — including the `$(...)`-in-execution-position rule,
   whose whole point is that the substitution IS visible.
2. **EXPANSION-SKELETON pass**, only if pass 1 allowed AND the command
   carries a `$` or a backtick. `_e4_globify_expansions` replaces every
   `${X}` / `$(...)` / `` `...` `` / `$NAME` with `*`, and the SAME walk asks
   whether the shell could still land on the toggle there.

`*` is the right stand-in because it is exactly the claim being made — "the
shell may put ANY text here" — and it lands the question in the glob
machinery the matcher already had (`_e4_glob_names_toggle`), LITERAL FLOOR
included. **That floor is load-bearing in the other direction**: `python3
$SCRIPT` skeletonises to `python3 *`, which names every script in the tree
and therefore names none of them, and stays ALLOWED. Without it this rule
would deny most variable-driven interpreter calls in the repo — a fail-closed
gate turned into a lockout.

Reusing the walk (rather than adding a parallel string rule) is what keeps
READS allowed for free: `cat .claude/scripts/night${X}-mode.py` skeletonises
to `cat .claude/scripts/night*-mode.py`, `cat` is not a runner, the path is
never an execution-position operand. Eight ALLOW twins pin that half.

**Pass ORDER is load-bearing in both directions**, and
`test_expansion_skeleton_does_not_shadow_the_literal_pass` pins it with a
positive control: pass 1 must run first so `python3 $(echo <toggle>) on`
keeps its precise message (its skeleton, `python3 *`, is deliberately
allow-shaped — the test asserts the skeleton ALONE does not deny it), and
pass 2 must run at all so `night${X}-mode.py` is refused.

The unparseable-input branch is SUPPRESSED on pass 2: pass 1 saw the
operator's real text and already adjudicated parseability. A skeleton that
fails to parse where the original did is an artefact of `*` substitution, and
denying on it would report a shape the operator never wrote.

Deny messages raised on the skeleton carry `_E4_EXPANSION_NOTE`. Without it
the message quotes a token (`night*-mode.py`) that appears nowhere in the
operator's command — an accurate deny that reads like a bug. The `!` rail and
the `night-mode` name stay in the base message, so the recovery route
survives the suffix (asserted by `test_invocation_block_names_the_human_rail`,
which now covers all 27 new vectors).

## 4b. Fix C — ANSI-C quoting, found by attacking my own fix

Not in the finding. After A and B were green, the fix was probed
adversarially (20 vectors, "would BASH actually run the toggle here?"), and
one came back ALLOW:

```
python3 .claude/scripts/night$'\x2d'mode.py on     -> ALLOW
```

Verified by EXECUTION before being treated as real — in a scratch tree it
printed `RAN: sc/night-mode.py`. Bash decodes `\x2d` to `-`, so the token IS
the canonical path; `shlex` does not implement ANSI-C quoting and handed the
walk a literal `night$-mode.py`, which matches nothing. Same class as P1-B —
text the SHELL assembles — so it belongs in the same regex, and `$"..."`
(locale translation) with it.

**Decoded, not wildcarded.** The first attempt mapped `$'...'` to `*` like
every other expansion, and left a second bypass standing:
`python3 .claude/scripts/$'night-mode.py' on` skeletonises to
`.claude/scripts/*`, which is below the glob literal floor and therefore
ALLOWED — while bash runs the toggle. The asymmetry is the point: an ANSI-C
string is not a run-time value, it is static text sitting in the command, so
`*` throws away information the matcher HAS. `_e4_expansion_replacement`
therefore decodes `$'...'` (via `unicode_escape`: `\xNN`, `\NNN` octal, `\\`,
`\n`, `\t`) and strips `$"..."` to its content, and falls back to `*` only
when decoding raises — the widening direction.

**Precision check (the other half).** `night$'\x2d\'x'mode.py` decodes to
`night-'xmode.py` — a DIFFERENT file, confirmed by asking bash for the
filename and testing that it does not exist. `_e4` correctly ALLOWS it.
`decide_command` still blocks that command, but through `_e3`'s whole-command
parse gate (the unbalanced quote makes it unparseable, and Wave E.3 fails
closed on that) — a different, pre-existing rail that fires identically on
`python3 tools/build$'\x2d\'x'fast.py`, which never mentions the toggle.
`test_ansi_c_decoding_does_not_over_match` pins both halves, with `_e3` as
the positive control so the attribution cannot rot.

## 5. Verification (exact counts)

| gate | result |
|---|---|
| `test_bash_posture_toggle_invocation.py` (overlay) | 255 -> **345 passed**, 0 failed |
| same file, clean clone @`9c63750` + patch applied | **345 passed** |
| adversarial self-probe, 20 vectors (1 red -> 0) | **FAILS=0 / 20** |
| bash-safety siblings (4 files), applied clone | **205 passed, 3 xfailed** |
| FULL `.claude/hooks/tests/` (overlay, final state) | **6811 passed**, 36 skipped, 28 xfailed, 5 xpassed, **0 failed** |
| standalone probe, 22 vectors (7 red -> 0) | **FAILS=0 / 22** |
| stdin smoke through the hook (JSON in/JSON out), 23 vectors | **FAILS=0 / 23** |
| `git apply --check`, pristine clone @`9c63750` | CLEAN |
| exec bit after apply | `-rwxr-xr-x` preserved |

The stdin smoke includes all 15 pre-r3 deny shapes (plain, direct-exec,
concat, case, env-flag, substitution, alias, `bash -c`) and 8 negative
controls; `bash -c` still carries `_e3`'s canonical message, so the division
of labour is intact.

**Perf (PLAN-089 §4 AC8, p95 < 50 ms):** measured n=2000 per shape, this fix
vs the r2 overlay. Non-expansion commands are flat within noise; the worst
case is a command carrying expansions, which pays for the second shlex pass:

```
                                        r2 overlay      this fold
git status --porcelain                   p95  98.0us     p95  99.0us
python3 -m pytest .claude/hooks/tests/   p95 140.3us     p95 144.9us
echo ok\npython3 tools/build.py ...      p95 157.5us     p95 166.2us
X=1; python3 ${SCRIPT_DIR}/build.py ...  p95 235.4us     p95 270.7us
```

Worst case +35us, which is **0.07% of the 50 ms budget**.

## 6. Concerns for the Owner

1. **The claim in §5 of the base NOTES is now wrong and was corrected.** The
   r1 notes recorded "The matcher's pre-filter (basename substring)
   short-circuits every command that does not name the toggle" as the perf
   argument. That pre-filter was REMOVED by the r1 codex fold (it was P1-A);
   the perf table above replaces that claim with a measurement of what
   actually ships.

2. **Residual, accepted — expansion state from a PREVIOUS command.** `X` set
   in an earlier Bash call is invisible to this hook: `python3 $X on` where
   `$X` already holds the toggle skeletonises to `python3 *` and is ALLOWED
   by the literal floor. Closing it would require denying `python3 $VAR`
   universally. It is refused at execution by the self-path guard
   (`nf08-self-path-guard.patch`) — the same layer that owns the alias class,
   for the same reason: prevention lives where it can be complete.

3. **Residual, accepted — `_e3` is still newline-blind in principle.** The
   normalisation added here is `_e4`'s own; `_e3` keeps its single flat
   tokenization. Probed rather than assumed: `echo ok\ncp evil
   .claude/hooks/check_bash_safety.py` and `ls\n> .claude/hooks/...` both
   still DENY, because `_e3`'s write matchers do not depend on `at_cmd_word`
   the way `_e4` did. So there is no open bypass — but the two matchers now
   disagree about what a newline is, and a future `_e3` rule that DOES key
   off command position would inherit the bug this appendix fixes. Sharing
   one normaliser is the obvious cleanup and was deliberately not done here:
   it would put `_e3`'s whole matcher inside this patch's blast radius on the
   eve of a ceremony.

4. **Non-conforming glob spellings remain a documented residual**, unchanged
   from r1: `python3 .claude/scripts/*.py` stays ALLOWED (3 literals, below
   `_E4_GLOB_MIN_LITERALS`). The skeleton pass does not change that line — it
   reuses it.

5. **Three rounds, and every round found something in MY draft.** r1 found
   the raw-substring pre-filter, r2 the alias class, r3 the newline and the
   expansion. Round 3's two findings are both in code that r1 and r2 had
   already reviewed. I do not read that as the matcher being unusually bad —
   I read it as the shell surface being larger than any single reviewer's
   model of it, which is the argument for the rail. The honest status of
   this patch is "no bypass known to four rounds of adversarial probing",
   not "no bypass". The self-path guard in `nf08-self-path-guard.patch`
   remains the layer that does not depend on getting the string matcher
   right, and it is the one that should carry the Owner's confidence.

---

# Appendix 3 — Codex S292 round 4 fold (BRACE EXPANSION, P1)

Round 4 returned one P1 against this patch: the matcher does not cover brace
expansion, so a token the shell rewrites into the guarded path is never
compared against it.

## 1. Red-first — the bypass, executed before it was fixed

Sandbox repo, GNU bash 3.2.57 (arm64-apple-darwin25), toggle replaced by a
script that appends its `argv` to a marker FILE. A stdout marker was tried
first and **lied**: `cat`-ing the source prints the marker string, so a read
scored as an execution. The side-effect file is the sound instrument.

| form | expands to | ran the toggle | guard (pre-r4) |
|---|---|---|---|
| `python3 .claude/scripts/night-mode.p{y..y} on` | **1 word** — the canonical path | yes | **ALLOW** |
| `python3 .claude/scripts/{night-mode,other}.py on` | 2 words | yes | **ALLOW** |
| `python3 .claude/scripts/night-mode{,}.py on` | 2 identical words | yes | **ALLOW** |
| `python3 .claude/scripts/night{-,x}mode.py on` | toggle + decoy | yes | **ALLOW** |
| `./.claude/scripts/night-mode{,}.py on` | 2 words, direct exec | yes | **ALLOW** |

The **first row was not in the finding** and is the sharpest of the set. A
sequence expression whose endpoints are equal expands to a SINGLE word, so the
command bash executes is byte-identical to the plain literal deny case —
measured argv from BOTH spellings:

```
argv via brace range : ['.claude/scripts/night-mode.py', 'on']
argv via literal     : ['.claude/scripts/night-mode.py', 'on']
identical            : True
```

Nothing about the bypass survives to run time. There is no residue a later
layer could notice.

## 2. The fix — expand, do not wildcard

The `$`-expansion rounds answered with a WILDCARD skeleton. That answer does
not work here, and the reason is worth recording because it is the trap:
`{night-mode,other}.py` skeletonises to `*.py`, which carries 3 literal
characters, lands under `_E4_GLOB_MIN_LITERALS`, and is **ALLOWED**.
Wildcarding would have shipped a fix that changes nothing for the finding's
own vector.

Brace expansion is STATIC text — the shell derives it from the command alone,
with no run-time value involved — so it is expanded, exactly as the ANSI-C
quoting branch DECODES rather than wildcards. `_e4_brace_words()` is an
iterative (explicit-stack) expander: recursion depth here would be the
attacker-controlled group count, and a `RecursionError` inside a security
matcher is a crash, which is a fail-OPEN, not a deny.

Two budgets, both fail-CLOSED on overflow (`_E4_BRACE_MAX_WORDS = 4096`,
`_E4_BRACE_MAX_TOKEN = 4096` chars). The deny message distinguishes the two
cases, because claiming "one of those words IS the guarded path" about a token
nobody enumerated would be a false statement in operator-facing text.

## 3. Verification

```
pre-r4 guard + r4 tests   ->  35 failed, 361 passed   (red-first)
r4 guard    + r4 tests    ->   0 failed, 396 passed
baseline (pre-r4 both)    ->   0 failed, 345 passed
whole bash/canonical set  ->  1310 passed, 14 skipped, 26 xfailed
live-fire, 18 forms       ->  bypasses: 0
mean per-command latency  ->  41.7us   (PLAN-089 section 4 AC8 budget: p95 < 50ms)
```

`git apply --check` passes against a clean `--local` clone of `main`.

One r4 vector — `brace_in_directory_half` — already denied pre-r4 (its basename
is spelled literally), and is pinned anyway so a refactor cannot narrow it.

## 4. Deliberate over-classification, stated plainly

`python3 .claude/scripts/{other,night-mode}.py on` does **not** run the toggle
(python executes the first expanded word, `other.py`; the toggle lands in
`argv[2]`) — and the guard denies it anyway. Deciding otherwise would mean
modelling which expanded word becomes the script operand for every runner and
flag combination, and being wrong there in the permissive direction is the
unsafe one. Two vectors are pinned in this shape, labelled as conservative.

## 5. Residuals

1. **A brace bomb past the budget is denied, not decided.** A token expanding
   to more than 4096 words is refused. Real fan-out (`bash deploy.sh
   {srv001..srv300}` — 300 words) expands exactly and stays ALLOWED; the
   negative control for that is pinned.
2. **Zero-padded integer ranges** (`{01..03}`) are generated unpadded. It
   under-approximates a shape no spelling of this toggle can use — the guarded
   basename carries no digits — and is recorded so the next reader does not
   read it as an oversight.
3. **`{A..B..STEP}`**: the step is parsed and ignored, yielding a SUPERSET of
   what bash produces. A matcher that considered FEWER words than the shell is
   the direction this must not fail in.
4. **`_e3` is not brace-aware.** This appendix widens `_e4` only. Not folded in
   for the same reason the r3 newline normaliser was not shared: it would put
   `_e3`'s whole matcher inside this patch's blast radius on the eve of a
   ceremony. Recorded as a follow-up, not as a closed gap.

## 6. Four rounds, four findings in my own draft

r1 the raw-substring pre-filter, r2 the alias class, r3 the newline and the
`$`-expansion, r4 the braces — each in code the previous rounds had already
reviewed and signed off. The honest status is unchanged and should stay
unchanged in the sentinel: **"no bypass known to five rounds of adversarial
probing"**, not "no bypass". The self-path guard in `nf08-self-path-guard.patch`
is still the layer that does not depend on getting a string matcher right.

---

# Appendix 4 — Codex S292 round 5 fold (UNKNOWN LAUNCHERS, P1)

> Finding, verbatim in substance (`nf08-invocation-guard.patch:175-178`):
> *"Treat `xcrun` as a command-launching prefix"* — `xcrun python3
> .claude/scripts/night-mode.py on` is not blocked, because `xcrun` is not in
> the matcher's prefix-runner list.

## 1. Red-first — 22 vectors ALLOWED, then 31 through the real hook

Probe (`scratchpad/probe_r5_xcrun.py`) against the pre-r5 overlay, before a
line was changed:

```
allowed-but-should-block: 22 / 22
```

Widened into the permanent vector list and re-measured through the REAL hook
on stdin — a subprocess with a `PreToolUse` payload, not an imported
`decide_command` (S291: a fixture is not the harness):

| | MUST-BLOCK | MUST-ALLOW |
|---|---|---|
| pre-r5 hook | 184 vectors → **153 blocked, 31 LEAKED** | 101 → 101 allowed |
| post-r5 hook | 184 → **184 blocked, 0 leaked** | 101 → 101 allowed |

Command: `python3 scratchpad/smoke_r5.py <overlay-root>` (drives the vector
lists straight out of the test module, so the smoke cannot drift from the
suite).

## 2. The vectors are real on this platform, not theory

Which of the named launchers actually EXIST here, and whether they execute
their operand — measured with a dummy script, never the toggle:

```
PRESENT xcrun, arch, caffeinate, script, sandbox-exec, nice, stdbuf
absent  unbuffer, proxychains4, taskset, firejail, watch, parallel,
        flock, gdb, strace, ionice

xcrun python3 dummy.py            -> RAN-THE-DUMMY
xcrun --sdk macosx python3 …      -> RAN-THE-DUMMY
xcrun -sdk macosx python3 …       -> RAN-THE-DUMMY   (single-dash long option)
xcrun ./dummy.py                  -> RAN-THE-DUMMY   (DIRECT EXEC, no interpreter)
arch -x86_64 python3 dummy.py     -> RAN-THE-DUMMY
caffeinate -t 5 python3 dummy.py  -> RAN-THE-DUMMY
script -q /dev/null python3 …     -> RAN-THE-DUMMY
sandbox-exec -p … python3 …       -> RAN-THE-DUMMY
```

The direct-exec spelling is live because the toggle ships executable:

```
$ git ls-tree plan-165-draft .claude/scripts/night-mode.py
100755 blob eff92e71…  .claude/scripts/night-mode.py
```

**And the script rail does NOT cover this class.** A faithful replica of the
NF-08b `_self_path_diagnostic` was run under each shape, with a positive
control that must pass:

```
direct run (positive control)          -> ARMED (guard passed)
xcrun python3 …/night-mode.py          -> ARMED (guard passed)   <-- matcher is the ONLY rail
python3 < …/night-mode.py              -> REFUSED (real=…/<stdin>)
cat …/night-mode.py | python3          -> REFUSED (real=…/<stdin>)
```

So for `xcrun`, defense-in-depth is one layer deep, and that layer was the
one that was open.

## 3. Decision: (b) structurally, with (a) kept for the one shape (b) cannot see

The brief offered (a) enumerate the launcher family, or (b) invert the logic.
**Both were implemented, for a reason worth stating.**

**(b) is the primary rail — `_e4_scan`, INTERPRETER HOP.** After an
unrecognised command word, the walk no longer stops: it keeps testing every
remaining token in the segment for INTERPRETER family. The launcher's NAME
stops mattering, so `<anything> python3 <toggle>` is denied. This is what
makes the next round of this class a non-event; it is pinned as a PROPERTY,
not a vector list, by `test_guard_does_not_depend_on_knowing_the_launcher_name`
(an invented launcher name that exists in no table).

**(b) alone is not sufficient, and this is the honest limit.** `xcrun
./<toggle> on` names no interpreter. To a string matcher it is the same shape
as `cat <toggle>`: the shell executes the FIRST word in both, and only the
command's own semantics decide whether the second word is launched or read.
That is structurally undecidable, so the hop deliberately re-opens ONLY the
interpreter rule — never the direct-exec rule — and the direct-exec position
is covered by naming launchers instead.

**(a) is therefore the secondary rail, and only for launchers that could be
MEASURED here**: `xcrun`, `arch`, `caffeinate`, `script`, `sandbox-exec`.
Absent binaries (`unbuffer`, `taskset`, `firejail`, `proxychains`, `torify`,
`systemd-run`, …) are **deliberately not added from memory** — see §5, an
invented flag table false-positives on readers. Their interpreter form is
covered by (b) regardless, which is exactly the point of having (b).

**No "reader" allow-list was added** to soften §4's cost, and the reason is a
vector, not an opinion: `git` READS in `git add` and LAUNCHES in `git bisect
run`. The split is a property of command+flags, not of the name, so an
allow-list keyed on the name would have handed back the very bypass this
round closes. Pinned by the `git_bisect_run` vector.

## 4. The cost, accepted and bounded

The hop makes three shapes DENY that previously allowed:

```
grep -n python3 .claude/scripts/night-mode.py
grep -rn sh     .claude/scripts/night-mode.py
echo python3    .claude/scripts/night-mode.py
```

An interpreter word used as DATA in a command that also names the toggle.
Accepted, and pinned as a decision by
`test_interpreter_word_used_as_data_is_a_known_false_positive`:

* it only fires on a command that ALREADY names the toggle — the blast radius
  is one file, not the operator's shell. `grep -n python3 .claude/scripts/ceo-boot.py`
  and `grep -rn python3 .claude/` are unaffected (asserted);
* the deny message names the `!` route, and the rewrite is one pipe
  (`cat <toggle> | grep python3`);
* the other direction is a silent bypass of a boundary three signed comments
  claim is closed — CLAUDE.md §4, fail-CLOSED on the input of a security
  matcher.

**Zero regression on the accumulated ALLOW matrix**: all 101 negative controls
from rounds 1-5 still allow, through the real hook.

## 5. Two sub-findings from attacking the fix

**r5-A — the flag tables are load-bearing, not decoration.** With an empty
table every flag classifies as `unknown`, the fail-closed `ambiguous` step
holds the command-word position open one token too long, and the READER
behind the flag is skipped so its operand reads as a command word:
`caffeinate -t 60 cat <toggle>` DENIED. Measured before the tables were
added. Each row is read off THIS machine's man page (`man 1 xcrun`,
`man 1 arch`, `man 8 caffeinate`, `man 1 script`, `man 1 sandbox-exec`) and
then confirmed by running the form. `_e4_classify_prefix_flag` also had to
learn single-dash LONG names — macOS spells them with one dash, and `-sdk`
was being tested as the cluster `-s -d -k`.

**r5-B — the expansion skeleton was inventing a word boundary.** Found by
running the new hop against the EXISTING negative controls:
`echo ok$'\n'python3 <toggle> on` started denying. Bash makes that ONE
argument to `echo`; no command starts at `python3`. The skeleton pass decoded
the ANSI-C escape to a literal newline, `shlex` split there, and `python3`
appeared as a free-standing token. The old walk ignored everything after
`echo`, so the defect was invisible — a pre-existing modelling bug that the
hop surfaced. Fix (`_e4_skeleton_safe`): decoded whitespace becomes `?`, one
glob character per character, so length is preserved and the word stays
whole. Recorded consequence: `python3 .claude/scripts/night$'\n'mode.py`
now skeletonises to `night?mode.py` and DENIES, though bash would name a
file with a newline in it. A fail-closed over-block on a shape no workflow
writes, versus a word boundary the shell never makes.

## 6. Verification — exact counts, with the commands that produced them

```
# unit, pre-r5 baseline (clean clone @9c63750 + previous patch)
python3 -m pytest .claude/hooks/tests/test_bash_posture_toggle_invocation.py -q
  -> 396 passed

# RED PROOF: the NEW tests against the PRE-r5 hook
  -> 66 failed, 409 passed        (31 vectors x 2 test fns + 4 property tests)

# unit, post-fix
  -> 475 passed

# whole hook suite, post-fix (the CI invocation, not `unittest discover`)
python3 -m pytest .claude/hooks/tests/ -q
  -> 6941 passed, 36 skipped, 28 xfailed, 5 xpassed in 418.69s
     baseline pre-r5, same command, same clone shape:
     6862 passed, 36 skipped, 28 xfailed, 5 xpassed in 424.03s
     DELTA = +79 passed, and NOTHING else moved. 79 = 475 - 396, i.e. exactly
     the tests this round adds; the xfail/xpass/skip profile is byte-identical,
     so no pre-existing xfail was silently flipped by the widened matcher.

# canonical matrix + perf gate
python3 -m pytest .claude/hooks/tests/test_check_bash_safety_canonical_matrix.py -q
  -> 39 passed, 3 xfailed

# smoke through the REAL hook over the FULL rounds-1-5 matrix
python3 scratchpad/smoke_r5.py <overlay>
  -> MUST-BLOCK 184 (184 blocked / 0 leaked)
     MUST-ALLOW 101 (101 allowed / 0 blocked)   TOTAL 285   RESULT: PASS

# latency (the hop adds per-TOKEN work; PLAN-089 §4 AC8 budget p95 < 50ms)
python3 scratchpad/perf_r5.py <hooks-dir> <label>   # 10 commands x 300 reps
  pre-r5  worst p95 = 3.440 ms
  post-r5 worst p95 = 3.435 ms      (worst case: a 200-word `echo`, unchanged)

# the patch itself, applied to a CLEAN clone at the base commit
git clone --local … && git checkout 9c63750 && git apply --check <patch>
  -> CLEAN; applied; hook and test byte-identical to the overlay; exec bit 755
  -> 514 passed, 3 xfailed in the clean clone; smoke 285/285 PASS
```

Patch: `nf08-invocation-guard.patch`, 2691 lines / 139073 bytes, regenerated
as `git diff 9c63750 -- .claude/hooks/check_bash_safety.py
.claude/hooks/tests/test_bash_posture_toggle_invocation.py`.

## 6b. Attacking the r5 fix (every previous round found a bug in the previous fix)

23 shapes aimed at the hop itself (`scratchpad/probe_r5_selfattack.py`):
**15/15 denied, 8/8 allowed, 0 unexpected.** The ones worth naming:

* denied — case-folded (`PYTHON3`), path-qualified (`/usr/bin/python3`),
  backslash-escaped (`\python3`), versioned (`python3.12`) interpreters after
  an unknown launcher; hop across a redirect clause, across two stacked
  unknowns, into the second segment of a `|` / `&&` chain; the hop combined
  with each earlier round's spelling (brace, case-folded path, `$S`
  variable); `xcrun --toolchain python3 <toggle>`, where the value-bearing
  flag eats the interpreter and the toggle lands at a command word instead;
* allowed — readers behind one and two unknown launchers, `python3 -m pytest
  <toggle>` behind an unknown launcher, another script in the same directory,
  the generic `*.py` glob, a TAB inside `$'…'` in an argument (the r5-B
  twin), a commit message quoting the whole command, and a redirect whose
  TARGET happens to be named `python3`.

The one thing this round did not survive is recorded as residual (5) below —
found by this same self-attack, not by the reviewer.

## 7. Residuals and one action the Owner must take

**Action — `MANIFEST.sha256` is now stale.** This round rewrote two files it
covers; regenerating the manifest is outside this agent's file assignment, so
the preflight `shasum -c` will FAIL until lines 13-14 are updated:

```
nf08-invocation-guard.patch      cc9385aae4b0cf0df59fac32dfcaa6cc03072eb1a3627bac231f8a901ddccbcd
nf08-invocation-guard-NOTES.md   (regenerate after this append)
```

**Residuals, stated rather than hidden:**

1. **Direct exec through a launcher that is not enumerated** —
   `firejail ./<toggle> on`. Structurally indistinguishable from `cat
   <toggle>` (§3). Only the enumerated five are covered in that position.
2. **`script out.txt ./<toggle> on`** — `script`'s FIRST positional is the
   typescript FILE, so the filename settles as the command word and the
   direct-exec rule never sees the toggle. Its interpreter form is caught.
3. **`$(which python3) <toggle> on` — measured, and it BLOCKS.** Recorded
   because the reasoning said otherwise: `(` and `)` are terminators for this
   walk, so the toggle lands at a command word after `)` and the direct-exec
   rule fires. Written here from the probe output, not from the argument that
   predicted a leak.
4. **stdin/pipe-fed interpreters** (`python3 < <toggle>`, `cat <toggle> |
   python3`) still ALLOW at the matcher, and are **neutralised by the script
   rail** — `__file__` becomes `<stdin>`, so `_self_path_diagnostic` refuses
   (measured in §2, with a positive control that passes). Left to the layer
   that already covers it rather than widened here on the eve of a ceremony.
5. **A RENAMED INTERPRETER defeats the whole matcher — the honest limit of
   this round.** Measured on this platform:

   ```
   ln -sf /Library/Developer/CommandLineTools/usr/bin/python3 ./zz-interp
   ./zz-interp dummy.py                 -> RAN-THE-DUMMY
   ./zz-interp …/night-mode.py          -> ARMED (self-path guard PASSES)
   decide_command("./zz-interp .claude/scripts/night-mode.py on") -> allow
   ```

   r5 moved the name dependency from "know every LAUNCHER" to "know every
   INTERPRETER" — a much smaller and far more stable set (`python*`, `bash`,
   `sh`, `zsh`, `ksh`, `dash`), but not zero. Closing it means treating any
   unknown command with the toggle as an operand as an invocation, which
   denies `cat <toggle>`; see §3. **This is why the sentinel line must not
   say "cannot be invoked".** The claim the evidence supports is: *every
   spelling found by five rounds of adversarial probing is denied, and the
   layer that does not depend on spelling is the self-path guard.*

   (Related, and NOT a residual: a glob-spelled interpreter name is a
   non-issue — bash does not glob a command word against `PATH`. Measured:
   `bash -c 'pyth?n3 dummy.py'` → `bash: pyth?n3: command not found`. It only
   works with a local file, which is case (5) by another route.)

## 8. Five rounds, five findings in my own draft

r1 raw-substring, r2 aliases, r3 newline + `$`-expansion, r4 braces, r5 the
launcher list — plus r5-B, which the fix itself exposed in code four rounds
had already signed off. The closed set has now failed in three of five
rounds; r5 is the first fold that removes the dependency on the set being
complete rather than adding to it. The sentinel line stays honest and stays
the same: **"no bypass known to five rounds of adversarial probing"**, not
"no bypass".
