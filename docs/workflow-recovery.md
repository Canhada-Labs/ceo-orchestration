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
| before dispatch | `launch_id`, instant, `session_id`, `tool_use_id`, `cwd`; script fingerprint (`sha256` + size); **a snapshot of an INLINE script's text**; for a `scriptPath`, the path, `sha256` and size only — the file is read to hash it and its bytes are NOT written (`script_snapshot_why: awaiting_post_tool_use`): this half runs before the harness's permission decision (FN-04, below); **`args` as literal canonical JSON, never truncated** — an absent `args` field is recorded as `<absent>`, distinct from `null`; `resumeFromRunId`; `name` / `description` | `<state-dir>/launches/<launch_id>.json` (atomic, 0600) + `<launch_id>.script` (inline scripts) + index `launches.jsonl` |
| right after (same hook) | code revision of `cwd` (`git rev-parse HEAD`, dirty flag) inside a 1.2 s budget with `--no-optional-locks`; slow or absent git ⇒ `code.status: unknown` — the manifest is already on disk | same manifest (second atomic write) |
| after the tool returns | the `wf_<id>` run id found in the response is **bound**: by `tool_use_id` when the event carries one; otherwise only when EXACTLY ONE unbound launch exists in the session. An unknown `tool_use_id`, or zero or several candidates, becomes an `orphan` index line; a response with no run id, with two different labelled ids, or with two different unlabelled ids, records nothing and the launch stays unbound. Two cases are NOT treated as ambiguous (known-open, see Limitations): a top-level `runId` and `run_id` that differ (the first wins), and an id whose tail is too long (its prefix is bound). The harness-persisted script path, when visible in the response, is recorded with `persisted_matches_snapshot`. **The `scriptPath` snapshot is taken here, and only by the bind by `tool_use_id`** — the PostToolUse of that same call, which the harness fires after it allowed and ran the call — and only when the response reports the id as the run it launched (the `Run ID:` label or a top-level `runId`/`run_id` key; a bare id token is `run_id_not_labelled`): the file is read again (same bounded reader, relative to the `cwd` recorded before dispatch) and written as `<launch_id>.script` only when its bytes hash to the `sha256` recorded before dispatch; otherwise nothing is written and `script_snapshot_why` says why (`changed_after_dispatch`, `unreadable_after_dispatch:<why>`, `write_failed:<type>`, `error:<type>`). The heuristic bind (that PostToolUse may belong to another call) and a manual `bind` never take a snapshot (`not_bound_by_tool_use`) and read no file outside the ledger's own index and manifests; only the bind by `tool_use_id` reads — the `scriptPath` file to take the snapshot, and the harness copy named in the response only to compare it with a snapshot the record holds. A `scriptPath` unreadable before dispatch has no hash and is never read afterwards | manifest (`run_id`, `bound_at`, `bind_method`, `script_snapshot`) + `<launch_id>.script` (`scriptPath`) + a `bind` line |

`<state-dir>` is the project's runtime state dir (`python3 .claude/hooks/_lib/runtime_paths.py --state-dir`),
the same family as the audit log. Nothing from transcripts is stored; `args` are the operator's own inputs.

## The guard

A call with `resumeFromRunId` is compared with the manifest **currently bound to that run**:

| comparison | result | what the hook returns |
|---|---|---|
| same script hash, same `args` | `match` | `{}` |
| **`args` differ** (per top-level key, or the same keys in another order — the script sees the order) | `mismatch_blocked` | **block**, counts-only reason |
| script hash differs, `args` same | `mismatch_script_advisory` | `systemMessage` (allowed) — `CEO_WORKFLOW_SCRIPT_GUARD=enforce` turns it into a block (`mismatch_script_blocked`) when the bind is strong |
| `args` identical, but a script hash is unavailable (unreadable `scriptPath`, a `name`d workflow, or a `scriptPath` record without a snapshot — its hash was never corroborated after dispatch) | `inconclusive` | `{}` — never a block, never a match; different `args` still block |
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
snapshot bytes whenever the record names a snapshot (an inline record must name one; a `scriptPath`
record without one is valid, but its hash — never corroborated after dispatch — makes the script
comparison inconclusive, while `args` are still compared). Any inconsistency is
`inconclusive` for the guard, `rc 6` for `check`, and `rc 7`
(nothing printed or copied as exact) for `relaunch`. `relaunch` holds the snapshot bytes it is about
to print and copy — a second read — to the same recorded hash: bytes that cannot be read back, or
that no longer hash to the record, are `rc 7` too. A missing script hash is not an
unavailable one: the `sha256` field must agree with the recorded source (inline ⇒ a hash that its
snapshot bytes reproduce; a path read at launch ⇒ a hash, reproduced by its snapshot bytes when there
is a snapshot; a path unreadable at launch, a named workflow or no script ⇒ `null`). If the construction of the record itself fails (for example `args` nested past the
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
#    fails its integrity check, when the snapshot about to be printed cannot be read back unchanged,
#    or when its script was unreadable at launch; for a NAMED workflow it prints the name and the
#    args — the content saved under that name is not verified. A scriptPath launch has a snapshot
#    only when the PostToolUse half of the same call took it (see "What is recorded"); without one,
#    relaunch is rc 7: the args are exact, the recorded sha256 and size are printed, and the
#    original file is reported against that sha256 (unchanged / CHANGED / unreadable) — nothing
#    is printed or copied as the exact script, and --out refuses, naming why (rc 7).
#    --out FILE publishes a copy of the snapshot as a NEW file. The command creates a private
#    directory (.ceo-launches-out-<hex>, mode 0700 requested) inside FILE's directory, so on the
#    same filesystem, and writes the bytes to an exclusive temporary inside it (created
#    O_EXCL|O_NOFOLLOW, mode 0600 requested), to the last byte, then fsync'ed. The umask applies
#    to both requested modes, and mode bits are not the only access control (ACL entries: see
#    the limitations below). Only then does FILE receive them, through link(2), which never
#    replaces an entry: anything at FILE that the command did not create (a file, a symlink, a
#    directory), whether there from the start or appearing meanwhile, is a refusal (rc 2) and is
#    left as it is. The command itself only ever writes partial bytes inside the private
#    directory, so FILE never names a file holding part of the copy while the machine stays up and,
#    during the call, nothing else writes FILE's directory as the command opened it, changes what a
#    directory on the path to FILE resolves to (a rename, a re-pointed symlink, a mount), or writes
#    what the command creates (the limitations below). That includes a FILE that the filesystem
#    treats as the same name as the private directory (for example a spelling that differs only
#    by case): FILE then names that directory while the command runs, and the command refuses,
#    rc 2 (it tells this case from a FILE that appeared meanwhile by comparing identities, not
#    spellings). The cleanup removes, by name, only the two names the command created: the
#    temporary (only once the command has recorded that its exclusive create succeeded), then the
#    private directory. FILE is
#    never passed to unlink, rmdir, rename or replace (removal BY NAME has a declared limit when
#    someone else writes FILE's directory: see the limitations below). A failure before the link
#    (the private directory cannot be created or opened, the temporary cannot be created, an I/O
#    error, no progress, fsync,
#    fstat, close) is rc 2 with nothing published at FILE. After link, whatever it answered, what
#    FILE then names decides, by identity (device, inode) against the identity fstat took from
#    the temporary's descriptor: the temporary itself is a publication, rc 0 — also when link
#    answered an error after creating the name (a retransmitted LINK on NFS can answer EEXIST).
#    When link answered an error, anything else that can be read is rc 2 with nothing published at
#    FILE by the command. When link succeeded, anything else (for example another object put under
#    the
#    temporary's name before link ran, or FILE replaced right after it) is rc 2 saying FILE is
#    not the temporary the command wrote; what FILE names is left as it is — do not use it. In
#    both cases, when what FILE names cannot be read, rc 2 says it cannot tell whether FILE holds
#    the copy. When link fails for a reason other than an existing entry, the message names the
#    errno the error carries and adds that the filesystem may lack hard links when it is EPERM,
#    ENOTSUP/EOPNOTSUPP, EXDEV or EMLINK. A failure to remove the temporary or
#    the private directory AFTER a link whose identity check passed is not a failure of the
#    copy: FILE is whole, "snapshot copied to" is printed, the exit code is unchanged and stderr
#    names the leftover directory. A FILE whose last component names no file (empty, ".", "..",
#    or a path ending in /) is refused, rc 2.
#    --out with nothing to copy (a named workflow, also with --out ""; a script not recorded at
#    launch, for a record the hook wrote; a scriptPath launch without a snapshot) creates no file
#    and never exits 0: rc 2 for a named workflow, rc 7 for the other two, the reason on stderr. Every rc 2 of --out above is
#    rc 7 instead when the record's script was not recorded at launch: the hook never writes a
#    snapshot for such a record, so only a hand-edited manifest that carries one reaches the copy,
#    and a refusal of that copy stays rc 7 (v1.4.1 answered 2). Use a copy only from a run that
#    printed "snapshot copied to FILE": after a refusal, do not use a file at FILE as this
#    command's copy, and a leftover .ceo-launches-out-<hex> directory is never the copy to use.
#    That line is only as good as the trust the limitations below place in FILE's directory and
#    the path to it: anyone who, during the call, writes that directory, changes what a directory
#    on the path to FILE resolves to, or writes the objects the command creates can make it print
#    that line while FILE names bytes that are not the snapshot.
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
- **Retention and privacy.** The ledger keeps the literal `args` indefinitely, and the snapshot of
  every inline script and of every `scriptPath` file that the PostToolUse half of its own call found
  unchanged, under the per-project state dir (files 0600, dir 0700) — the same material the harness
  itself keeps for finished runs. `show` and `relaunch` print the `args` back, so whatever a caller put
  in them (issue text, a token) reaches the reader's context again. Backups of the state dir include
  the ledger.
- **Before the permission decision (FN-04).** The PreToolUse half runs before the harness decides
  the call. It writes no byte of the file a `scriptPath` names — but it still OPENS and READS that
  file (the same bounded reader) to compute its `sha256` and size, and records both in the manifest
  (the `sha256` also in the index line), whether or not the harness then allows the call: whoever can read the state
  dir can test a guess of that file's content against the hash, and on a resume the guard's result
  depends on those bytes. The snapshot after dispatch re-reads the PATH; it is not a copy of what
  the harness ran: if what that path resolves to changes between the PreToolUse read, the harness's
  own check and the PostToolUse read, the snapshot can hold bytes other than the ones the harness
  checked — never bytes that fail to hash to the value recorded before dispatch. The cure relies on
  the harness firing PostToolUse only for a call it allowed and ran. Snapshots that earlier versions
  of this hook wrote at PreToolUse stay in `launches/`: this version removes none, and deleting one
  makes its record fail the integrity check (`inconclusive` for the guard, rc 7 for `relaunch`).
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
    reader: the record is then inconclusive for the guard (`script_snapshot_missing`).
- **`relaunch --out` (declared).** The v1.4.1 cases declared for it (a partial file left under the
  destination name, a cleanup that was an `lstat` of the destination followed by an `unlink` of it,
  rc 0 when the second read of the snapshot failed), and cases it did not declare (`--out` ignored
  for a named workflow; `--out ""` taken as omitted; a second read of the snapshot that changed,
  printed and copied — all rc 0), are replaced by the publication described in the recovery rite
  (PLAN-190-FOLLOWUP). What that publication does not cover:
  - a process that ends without running its cleanup (a signal still at its default action when
    that action ends the process — SIGTERM, SIGHUP, SIGQUIT and SIGKILL among them; the command
    installs no signal handler — or a power loss), an interruption that lands before the command
    has recorded what it just created (between a creation — the private directory, the
    temporary — and the moment the command records it) or inside the cleanup itself, or a failed
    removal leaves a `.ceo-launches-out-<hex>` directory in the destination's directory, possibly
    holding the temporary. Signals whose disposition
    Python itself sets at startup are not in that class: SIGINT (Ctrl-C) becomes an exception,
    unless the parent process left it ignored, so the cleanup runs (the unhandled-exception case
    below); SIGPIPE and SIGXFSZ are ignored, so a write past the file-size limit fails with an
    error instead (measured: `EFBIG`, rc 2, nothing left) and SIGPIPE never ends the copy. When the
    removal fails on a path the command handles (a refusal, a
    handled write failure, or after the link) the message names the directory; when an exception
    the command does not handle (Ctrl-C included) propagates out of it, a failed removal is
    reported by nothing — look for the directory by its prefix. While the machine stays up, and
    within the trust the next bullets declare, it never leaves a file holding part of the copy
    under the destination name (after a power loss nothing is claimed: see the "whole file or no
    file" bullet below). A leftover directory is never the copy to use: delete
    it, never edit what it holds — a temporary left there after the link is a second name of FILE
    (the same inode), so editing it changes FILE;
  - the destination's directory is trusted like the ledger directory. Anyone who can write it —
    another process of the same user, or another user where that directory is writable to others
    without the sticky bit — can rename entries in it while `--out` runs: put something else under
    the private directory's name between its creation and its opening (a symlink there is refused,
    never followed; a directory there that the command can open receives the temporary, and
    whoever can write that directory can then put another object under the temporary's name —
    refused after the link, rc 2, what FILE names left as it is — or alter the temporary in
    place, which no check sees), put an EMPTY directory under that name before the cleanup, which
    then removes that one (the cleanup goes by name, for the temporary as for the directory, and
    `rmdir` removes only an empty directory; the command's own directory is then left under
    whatever name they gave it, and nothing reports it), or replace FILE after its identity check.
    Mode bits do not bound who else can act: anyone the permissions of the private directory and
    the temporary admit — the same user, and on macOS whoever an inheritable ACL entry on FILE's
    directory grants the rights to — can alter the temporary in place, and write FILE after it is
    published. Such an entry is inherited by the private directory, the temporary and FILE (seen
    with `ls -le`, also for an entry that does not apply to FILE's directory itself,
    `only_inherit`), and an ACL allow entry grants what it names over the mode bits (measured:
    mode 000 plus an allow entry admits the create and the open for writing it names). In those
    cases the command can print "snapshot copied to" over bytes that are not the snapshot. That
    tampering is outside the threat model;
  - only the last component of FILE is never followed; the directory part is resolved as given (a
    symlinked directory is followed) and once, when the command opens it: every later step acts on
    that open directory, while the printed path is resolved again by whoever uses it, so a
    directory on the path to FILE renamed or re-pointed during the call makes that path name an
    entry of another directory;
  - where the v1.4.1 shape (a plain exclusive create of FILE, written and closed) would succeed
    but any operation this shape performs beyond it is refused or fails — examples, not the
    list: a directory-relative call, creating or opening the private directory, creating the
    temporary inside it, a second inode, `fsync`, `fstat`, the hard link, reading what FILE names
    after it — `--out` refuses, rc 2 (rc 7 for a record whose script was not recorded at launch),
    instead of falling back to writing FILE in place (the v1.4.1 shape, which could leave part of
    the copy under FILE). What refuses can be FILE's directory, its filesystem or platform, or
    the process's umask. Measured on macOS, where a plain exclusive create of FILE in the same
    directory succeeds: an ACL entry denying `add_subdirectory`; a umask that clears the owner's
    write or search bit of the private directory's requested 0700 (0177, 0100, 0200 — a umask
    that clears only the owner's read bit, such as 0400, still publishes, there and wherever
    `O_PATH` or `O_SEARCH` exists; where neither exists it refuses too — pinned by a test that
    forces that fallback open flag, no such platform measured); and a FAT (msdos)
    volume, where `link` answers `ENOTSUP` while the v1.4.1 shape published. Which call names
    the umask refusal depends on the platform: on macOS (`O_SEARCH`) opening the private
    directory refuses when the search bit is cleared; on Linux (`O_PATH`, measured in a
    container) that open checks no permission on the directory itself and creating the
    temporary refuses. A platform without
    the directory-relative calls refuses the same way. The destination's directory and the
    private directory are opened for search only where Python exposes `O_PATH` (Linux) or
    `O_SEARCH` (macOS), so a directory you
    can write and search but not read (a drop directory, mode 0300) is accepted there; where
    neither flag exists it is opened for reading and such a directory is refused, rc 2. A
    filesystem that reported one file's identity differently through FILE than through the
    temporary's descriptor would refuse every copy, rc 2 (the command compares identities; no such
    filesystem was measured);
  - "the whole file or no file" holds while the machine stays up and while, during the call,
    nothing else writes FILE's directory as the command opened it, changes what a directory on the
    path to FILE resolves to (a rename, a re-pointed symlink, a mount), or writes what the command
    creates (previous bullets); every other statement of it in this document and in the command
    carries these same limits. The
    bytes are fsync'ed before the name exists, but no directory is fsync'ed and `fsync(2)` on macOS
    does not flush the drive's cache (`F_FULLFSYNC` is not used): after a power loss nothing is
    claimed about FILE, neither the name nor the bytes under it;
  - a FILE present when the command starts is refused by a check made before anything is created;
    one that appears after that check is refused by `link` itself (`EEXIST`) — the check alone would
    not hold under a race.
