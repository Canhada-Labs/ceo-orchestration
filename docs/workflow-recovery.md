# Workflow recovery — launch ledger and resume guard (PLAN-190 W1)

> Audience: operators running autonomous Workflow pipelines in a consumer repository, and the
> recovery rite after a quota death, a process death or a reboot. Framework ≥ the release that
> ships `check_workflow_launch.py`; stdlib only.

## The loss this closes

A Workflow run's result cache is keyed by the exact `(prompt, opts)` of each `agent()` call. Anything
that changes the prompt text — an edited rule in the script, a rebuilt `args` object with one
field missing, a `continua` flag that was never there — changes the key and re-executes phases that
had already finished. The harness persists a run's `args` only when the run ENDS
(`<session>/workflows/wf_<id>.json`), never its script hash, the code revision, nor anything at
launch time; a run killed by a process death leaves nothing. Measured on one consumer
(2026-09-15→17): 15.5 % of phase starts never produced a result; 16 % of starts were
re-executions; one prompt edit in flight re-implemented 17 slices; args rebuilt from memory
regressed 11 slices; exact args resumed 12/12 in the right phase.

## What is recorded, and when

`check_workflow_launch.py` runs on **PreToolUse** and **PostToolUse** for the `Workflow` tool:

| moment | what | where |
|---|---|---|
| before dispatch | `launch_id`, instant, `session_id`, `tool_use_id`, `cwd`; script fingerprint (`sha256` + bytes) **and a snapshot of the script bytes** (inline text, or the `scriptPath` file as read at that instant); **`args` as literal canonical JSON, never truncated** — an absent `args` field is recorded as `<absent>`, distinct from `null`; `resumeFromRunId`; `name` / `description` | `<state-dir>/launches/<launch_id>.json` (atomic, 0600) + `<launch_id>.script` + index `launches.jsonl` |
| right after (same hook) | code revision of `cwd` (`git rev-parse HEAD`, dirty flag) inside a 1.2 s budget with `--no-optional-locks`; slow or absent git ⇒ `code.status: unknown` — the manifest is already on disk | same manifest (second atomic write) |
| after the tool returns | the `wf_<id>` run id found in the response is **bound**: by `tool_use_id` when the event carries one; otherwise only when EXACTLY ONE unbound launch exists in the session. An unknown `tool_use_id`, or zero or several candidates, becomes an `orphan` index line; a response with no run id, with two different labelled ids, or with two different unlabelled ids, records nothing and the launch stays unbound. Two cases are NOT treated as ambiguous (known-open, see Limitations): a top-level `runId` and `run_id` that differ (the first wins), and an id whose tail is too long (its prefix is bound). The harness-persisted script path, when visible in the response, is recorded with `persisted_matches_snapshot` | manifest (`run_id`, `bound_at`, `bind_method`) + a `bind` line |

`<state-dir>` is the project's runtime state dir (`python3 .claude/hooks/_lib/runtime_paths.py --state-dir`),
the same family as the audit log. Nothing from transcripts is stored; `args` are the operator's own inputs.

## The guard

A call with `resumeFromRunId` is compared with the manifest **currently bound to that run**:

| comparison | result | what the hook returns |
|---|---|---|
| same script hash, same `args` | `match` | `{}` |
| **`args` differ** (per top-level key, or the same keys in another order — the script sees the order) | `mismatch_blocked` | **block**, counts-only reason |
| script hash differs, `args` same | `mismatch_script_advisory` | `systemMessage` (allowed) — `CEO_WORKFLOW_SCRIPT_GUARD=enforce` turns it into a block (`mismatch_script_blocked`) when the bind is strong |
| `args` identical, but a script hash is unavailable (unreadable `scriptPath`, a `name`d workflow) | `inconclusive` | `{}` — never a block, never a match; different `args` still block |
| the recorded manifest fails its integrity check (below) | `inconclusive` (`integrity: <code>`) | `{}` — an inconsistent record is evidence of nothing |
| the guard itself raised | `inconclusive` (`error: <type>`) | `{}` — recorded, the call's manifest still written |
| no manifest bound to that run | `no_manifest` | `{}` |
| `resumeFromRunId` not shaped like a run id | `resume_id_unrecognised` | `{}` (recorded, not echoed) |

A manifest bound by heuristic (`by_single_unbound`, no `tool_use_id` in the event) never sustains
a block, args or script alike: an args mismatch against it is `mismatch_advisory_weak_bind`, a
script mismatch stays `mismatch_script_advisory` even under `CEO_WORKFLOW_SCRIPT_GUARD=enforce`
(the advisory names the route: `ceo-launches.py bind <launch_id> wf_<id>` makes it enforceable).
A launch the guard blocked never ran: it stays in the index (`blocked: true`) but is never a
candidate for the single-unbound binding of the corrected call.

A resume with DELIBERATELY changed `args` is legitimate — for example `args.resume` or `args.reverify`
naming the lanes to re-run, which only re-keys the phases whose prompt reads them. The guard cannot
tell deliberate from rebuilt-from-memory, so it asks the call to say which: declare it (below). Only
the phases whose prompt depends on what changed re-execute; the reason says exactly that.

Overrides — ONE path for every block (args, and script under enforce). It is carried by the call or
by the process, **never by stored state**, so there is nothing to read back, replay or race:
- **in the call** — re-issue the call with a `description` that starts with the exact prefix
  `CEO_WORKFLOW_RESUME_FORCE:` followed by a non-empty reason, for example
  `description: "CEO_WORKFLOW_RESUME_FORCE: slice A02 args fixed on purpose"`. If that call would be
  blocked it proceeds, is marked `mismatch_forced` with `force_source: call` and the reason, and is
  announced (`WORKFLOW-RESUME-FORCED`; the reason is recorded, never echoed). The declaration covers
  that one call and is never stored. Once that call is bound to the run, it becomes the run's recorded
  reference: a later resume with those same inputs is a `match`, and only a NEW divergence needs a new
  declaration. A declaration on a call that would not
  be blocked changes nothing (`force_declared: true` is recorded). The prefix is exact: leading text,
  another case or a missing reason is not a declaration. `description` is not part of the runner's
  cache key, so declaring it does not re-key the run.
- **process environment of the harness** (not a shell `export` inside the session):
  `CEO_WORKFLOW_RESUME_FORCE=1` (proceed over any block, `force_source: env`), `CEO_WORKFLOW_RESUME_GUARD=0`
  (advisory mode: the ledger keeps working, nothing blocks), `CEO_WORKFLOW_SCRIPT_GUARD=enforce`
  (block script changes too), `CEO_WORKFLOW_LEDGER=0` (hook off).

`report` prints the counts by guard result (`mismatch_forced`, `mismatch_blocked` and
`mismatch_script_blocked` among them); the stop rule's ratio, forced ÷ (forced + both blocked results),
is computed from those counts. Deliberate-change declarations count as forced, so read the ratio
together with the reasons recorded in the manifests.

**Who reads what.** A block returns `decision: block` with a counts-only `reason` the model reads. An
allowed call with something to say (forced, or an advisory) returns the same text twice:
`hookSpecificOutput.additionalContext` for the model, `systemMessage` for the user.

**Records are validated before they are evidence.** The manifest bound to a run is checked before any
comparison and before `relaunch`/`check` use it: schema; launch id, run id and bind method shapes;
`args` present/canonical/sha256 mutually consistent; the script sha256 equal to the hash of its
snapshot bytes. Any inconsistency is `inconclusive` for the guard, `rc 6` for `check`, and `rc 7`
(nothing printed or copied as exact) for `relaunch`. A missing script hash is not an
unavailable one: the `sha256` field must agree with the recorded source (inline or a path read at
launch ⇒ a hash that its snapshot bytes reproduce; a path unreadable at launch, a named workflow or no
script ⇒ `null`). If the construction of the record itself fails (for example `args` nested past the
interpreter's recursion limit), the call is still recorded with the error and the guard result is
`inconclusive`; a write failure leaves a stderr breadcrumb. Index lines that are not JSON objects with a
string `kind`, or that carry an ill-shaped launch id, are skipped. Records are written ASCII-escaped,
so no input (a lone surrogate included) can make a record unwritable; a failure to persist a call's
record does not undo a block the guard already computed. A `scriptPath` is read only when it is a
regular file of at most 8 MiB, opened non-blocking (a FIFO, a device, a directory, a larger file or a
path with a NUL byte is recorded `unreadable` with its reason — the script comparison is then
inconclusive, `args` are still compared). An index line torn by a crash never swallows the next
record: a writer that finds the file not ending in a newline starts a new line first. The lookup of
the manifest bound to a run takes the most recent binding not explicitly unbound; if that record is
unreadable, the answer is "no manifest", never an older launch's inputs. A binding LINE that is lost
from the index is a different case and is NOT detected (known-open, see Limitations): when an I/O
error stops the index read midway, or the newest binding line is torn, the lookup sees the previous
binding and the guard compares against that older launch.

**The block reason is counts-only.** It says how many keys changed / are only in the recorded call /
only in this call, whether the script hash differs, and the two routes — it never carries key names,
values or an unvalidated run id (that text reaches the model; the channel is closed by removal). The
detail is in the manifest: `ceo-launches.py show <launch_id>`.

Infrastructure failures (unreadable stdin, unwritable state dir, import error) fail **open** with a
stderr breadcrumb: this is a recovery instrument, not a security matcher.

## The recovery rite (replaces "reconstruct the call from memory")

```
# 1. what was launched, what is bound, what the guard saw
#    (from anywhere inside the project: without CLAUDE_PROJECT_DIR the CLI walks up from the
#     current directory to the project that holds .claude/, the ledger the hook writes)
python3 .claude/scripts/ceo-launches.py list
python3 .claude/scripts/ceo-launches.py show wf_<id>

# 2. the EXACT call to re-issue: the script SNAPSHOT (pass it as scriptPath) + literal args
#    args are printed in the ORIGINAL key order; rc 7 and nothing announced as exact when the record
#    fails its integrity check or its script was unreadable at launch; for a NAMED workflow it prints
#    the name and the args — the content saved under that name is not verified; --out creates a NEW
#    file only (never overwrites, never follows a symlink) and keeps writing until the last byte: a
#    HANDLED failure (I/O error, no progress, error at close) is rc 2 and the command TRIES to remove
#    the partial file (inode check, then unlink by name — two steps, not atomic: do not point --out at
#    a path another process writes to); if the removal itself fails, the partial file STAYS and the
#    message says so; a Ctrl-C or a signal in the middle of the write is not handled and can leave a
#    partial file. So never pass a copy from a run that did not print "snapshot copied to"
python3 .claude/scripts/ceo-launches.py relaunch wf_<id> [--out /path/to/copy.js]

# 3. before re-issuing from a rite that edits scripts: the guard's comparison, standalone
python3 .claude/scripts/ceo-launches.py check --run wf_<id> --script-file <path> --args-file <json>
#    rc 0 SAME · rc 3 ARGS-DIFFER (keys listed) · rc 5 SCRIPT-DIFFERS · rc 6 INCONCLUSIVE (hash unavailable
#    or record inconsistent) · rc 4 NO-MANIFEST

# 4. runs the PostToolUse half could not bind: `orphans` lists the orphan lines (unknown tool_use_id,
#    zero or several candidates); a launch whose response carried no or ambiguous run ids has no line
#    at all and shows in `list` with no run — bind either by hand
python3 .claude/scripts/ceo-launches.py orphans
python3 .claude/scripts/ceo-launches.py bind <launch_id> wf_<id>
```

Rules the ledger makes mechanical:
- **Never edit the script of a run in flight.** A new rule means a NEW script file; a per-run
  instruction goes through an `args` field the script already reads. Resuming over an edited script
  is allowed but announced (advisory): only the phases whose prompt changed re-execute.
- **Never rebuild `args` from memory.** `relaunch` prints them; `check` refuses a drift.
- **Absent is not null.** If the recorded call had no `args`, do not pass one.

## Measuring "quota per approved delivery" (W0.2 groundwork)

`ceo-launches.py report` counts launches, bindings by method, guard results and orphans. Joined with
the deduplicated token ledger (`ceo-cost-transcripts.py --by session` — the collector validated in
`docs/research/s354-token-consumption-study/03-collector-audit.md`) and with the merges on `main`,
it gives tokens per run and per approved delivery. "Approved delivery" is decided by code in
`approval_gate.py` (PLAN-190 W3, `docs/approval-gate.md`).

## Distribution (declared precondition)

The hook file travels with `.claude/hooks/`; its two registrations travel in
`templates/settings/settings.base.json` (the `user` profile is derived from it and keeps this hook).
`upgrade.sh` merges registrations **per recorded ceremony** (`.claude/.install-state.json`): a target
with no recorded ceremony and no `--ceremony` flag receives the shared settings only — no hooks.
The merge also needs `jq` on the machine running `upgrade.sh`; without it the merge is skipped with a
`settings-merge skipped (jq not found)` note and the hook file arrives unregistered. So "reaches
consumers without a manual step" holds for consumers whose ceremony is recorded and that have `jq`,
and it does not hold with `--no-settings-merge`. The plugin build ships `ceo-launches.py` in the
plugin's `scripts/` whenever it registers this guard.
This precondition is DECLARED here, not yet exercised by the smoke-install: adding one leg per case
is PLAN-190 W6.

## Limitations (declared)

- The guard sees the **`Workflow` tool call**; it cannot see `agent()` calls inside a run nor stop the
  harness from re-keying its cache. It stops the OPERATOR from resuming over changed inputs without
  knowing.
- There is no checkpoint inside a single `agent()`: a phase that dies at 400k tokens restarts. PLAN-190
  W2 adds a phase checkpoint file the phase prompt reads and writes; the runner itself is the limit.
- The run id is extracted from the tool response by shape (`wf_<hex8>[-<hex>]`, 98.5 % of 329 real
  responses in this repo's own transcripts); a harness version that changes the response leaves the
  launch recorded and `bind` closes it by hand.
- No audit event is emitted (registering a new action is the audit owner's ceremony); the manifests
  are the record. Manifests are never pruned (a `gc --keep-days` is a follow-up).
- **Retention and privacy.** The ledger keeps the literal `args` and a snapshot of every script
  indefinitely, under the per-project state dir (files 0600, dir 0700) — the same material the harness
  itself keeps for finished runs. `show` and `relaunch` print the `args` back, so whatever a caller put
  in them (issue text, a token) reaches the reader's context again. Backups of the state dir include
  the ledger.
- **One project context.** The ledger is per project dir: a launch recorded under one project dir and a
  resume issued from a session whose project dir is a different worktree of the same repo find no
  manifest (`no_manifest`, allowed and recorded).
- **Git in the session cwd.** The revision enrichment runs `git rev-parse` and `git status` in the call's
  `cwd` with `core.fsmonitor=false`; `git status` may still run filters that repository configures.
- **Worst-case hook time.** One locked index append (lock wait up to 2 s) plus the 1.2 s git budget stays
  under the 5 s registration timeout; the CI hook-latency gate does not profile this hook yet.
- **Resume response.** The harness prints `Run ID: wf_<id>` on launch and on resume, and a resume keeps
  the same id (probed on CLI 2.1.274 with a `.script` scriptPath, which the tool accepts); the id is
  taken from a top-level `runId`/`run_id` key, else from that label, else from the only distinct
  id-shaped token in the response.
- **Known-open, found by the cross-review rounds of the v1.4.1-rc.1 candidate (2026-09-18), not
  cured in v1.4.1:**
  - an incomplete read of the index (an I/O error midway, or a torn newest line) is not signalled;
    the guard then compares against the previous surviving binding and can BLOCK a legitimate
    resume — the exit is the `CEO_WORKFLOW_RESUME_FORCE` declaration;
  - `no_manifest` (another worktree, or a run launched before the hook existed) proceeds with no
    notice at all;
  - a top-level `runId` and `run_id` that differ are not treated as ambiguous (the first wins), and
    an id whose tail is too long (`wf_12345678-123456789`) is bound by its prefix (`wf_12345678`)
    instead of being rejected;
  - when a mismatch is NOT blocked (advisory mode, or a heuristic bind), the notice names the
    CURRENT call's manifest as "the recorded call"; once that call is bound, `relaunch wf_<id>`
    prints the changed inputs — read the original with `show <launch_id>` of the launch the notice
    was compared against (`guard.against` in the current manifest);
  - ledger writes follow a symlinked `launches/` directory or index file (deliberate same-user
    tampering is outside the threat model);
  - an INLINE script larger than 8 MiB is recorded, but its snapshot is read back through the 8 MiB
    reader: the record is then inconclusive for the guard (`script_snapshot_missing`);
  - `relaunch --out`: the partial-file cases named in the recovery rite above; the cleanup after a
    handled failure is an inode check followed by an unlink by name, so a concurrent writer that
    replaces the destination in between loses its file while the message says the partial file was
    removed; and when the second read of the snapshot fails, the command prints the "exact recorded
    call" heading, creates no file and exits rc 0. The structural cure (exclusive temporary file,
    publish by no-replace `link`, never unlink the destination) comes after v1.4.1.
