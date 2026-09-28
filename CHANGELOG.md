# Changelog

All notable changes to **ceo-orchestration** are documented in this file.

The format is based on [Keep a Changelog](https://keepachangelog.com/en/1.1.0/),
and this project adheres to [Semantic Versioning](https://semver.org/spec/v2.0.0.html).

> **Scope.** This log records *user-visible* changes — new skills, hooks, slash
> commands, schema/contract changes, and behavior an adopter would notice after
> installing or upgrading the framework. Internal refactors, test-only churn, and
> release-engineering bookkeeping are omitted. Counts cited below (as of
> v1.4.1: 166 skills, 27 slash commands, 198 ADRs, 72 `_lib` modules) are
> reproducible from the repository via
> `bash .claude/scripts/local/verify-counts.sh`.

---

## [1.4.2] - 2026-09-25

Express release (PLAN-193). Claude Opus 5.5 (`claude-opus-5-5`) becomes the
session-default model the settings templates ship, and joins the model
allowlist and the VETO floor. New installs ship at `xhigh` effort; an
upgraded install whose shipped Opus 5 pin moves to Opus 5.5, and whose
`.claude/settings.json` sets no `effortLevel`, gets `high`, the Opus 5
default, instead of medium, the Opus 5.5 one. **Claude Code 2.1.280 or later
is required**: the installer and the upgrader refuse an older `claude` on
`PATH` unless you pass `--allow-old-claude-code` (below). The pair-rail
reviewer is pinned to Codex CLI 0.156.1. The Workflow launch ledger stops
persisting the bytes of a `scriptPath` file before the harness has decided
whether the call may run: that is the case v1.4.1 GA condition 23 declared
known-open, with its cure targeted to this release. The class that
condition names by shape is declared here, not cured, and the copies v1.4.1
wrote are not removed (below). `relaunch --out` gets the structural cure
that v1.4.1 deferred. The honest part: the `[1.4.1]` entry and the v1.4.1
tag annotation re-targeted the cure of the v1.4.0 annex to this version.
**This release does not carry it**, and no release is assigned to it
(Known-open below). No speed claim.

### Changed — Claude Opus 5.5 is the session default and joins the VETO floor (PLAN-193, ADR-149 Amendment 3)

- `claude-opus-5-5` is appended at the END of the ADR-149 working set, and so
  of `availableModels` in the base (maintainer) settings template. It
  becomes the top-level `model` pin in both settings templates (`base`, and
  the `user` profile derived from it). `fallbackModel` stays `claude-opus-5`
  in the base template (the `user` template sets none), and `claude-opus-5`
  stays allowlisted: the change is additive. No shipped settings file sets
  `ultracode`.
- **VETO floor.** `claude-opus-5-5` joins the ids an agent file with
  `veto_floor: true` may declare (the ADR-149 block and
  `agent_frontmatter.VETO_FLOOR_ALLOWED`, kept equal by test). That makes it
  ELIGIBLE; it moves no agent: every shipped VETO-bearing agent file keeps
  its `claude-fable-5` pin. The amendment declares by shape where a pin does
  not hold — among them a per-call `model`, which outranks the agent file
  with no gate observing it; mitigated and Workflow spawns passed no model,
  which run on whatever model the session runs at that moment; and subagent
  effort, which is inherited from the session, not pinned.
- **Prices.** $4 / $20 per MTok input/output, with cache reads at **0.05×**
  the input price ($0.20/MTok), not the usual 0.1×. The cost table and the
  cost rollups bound to the working set carry that row; a rollup that looks
  a model up by its exact spelling does not price the `claude-opus-5-5[1m]`
  spelling.
- **The live Claude adapter sent a thinking shape current models reject.** It
  kept a hand-maintained list of adaptive-only ids and sent the legacy
  `budget_tokens` shape to every other id; `claude-opus-5` and
  `claude-sonnet-5` were never added, so an effort override
  (`CEO_EFFORT_OVERRIDE`, set by `/effort`) on them was an HTTP 400. The
  default is inverted: the adapter now keeps the CLOSED list of pre-4.6 ids
  whose only thinking mode is the legacy shape, and sends adaptive thinking
  to ids outside it, so a newly released model gets the adaptive shape with
  no edit there. An entry of that list matches its exact id, optionally
  followed by one date segment (`-YYYYMMDD`, or the Vertex `@YYYYMMDD`) and
  a Bedrock version suffix; an id that adds any other segment is another id
  and gets the adaptive default (one entry is a family, every `claude-3-`
  id, and the bare 4.0 ids match only with their date). The list of
  always-on models stays hand-maintained and matches the same way: a
  caller's `{"type": "disabled"}` is dropped only on the models it names
  (where it is an HTTP 400) and is sent as given elsewhere, so an always-on
  model it does not name still answers that request with an HTTP 400
  (Known-open below). On a model whose thinking is on by default, an effort
  of `off` does not turn thinking off.
- The env-channel tamper check (`effective_config`) reads a model-remap value
  of `claude-opus-5-5[1m]` as the allowlisted `claude-opus-5-5`: one trailing
  `[1m]` tag is folded before the membership test, and any other suffix is
  compared as written.

### Changed — effort: `xhigh` on new installs; `high` when an upgrade moves the Opus 5 pin (PLAN-193 OQ-1, OQ-7, OQ-8, OQ-10)

- **New installs** ship a top-level `effortLevel: "xhigh"` in both settings
  templates. In project settings that key applies to every model of the
  session and outranks a level a developer saved with `/effort` (Claude Code
  keeps those per model, in user settings); a level in
  `.claude/settings.local.json` outranks the project file. `xhigh` typically
  spends more tokens — cost and latency — than the default: lower or delete
  the key to trade depth for cost. The key takes `low`, `medium`, `high` or
  `xhigh`; `max` is not one of its values.
- **Existing installs** (`upgrade.sh`, unless `--no-settings-migrate`):
  `availableModels` is written with the list that has `claude-opus-5-5`
  (appended last) when the file has none or has a list an earlier release
  shipped; a list you customized is preserved with a named warning. The
  `model` pin moves to `claude-opus-5-5` when it is absent or is the
  `claude-opus-5` an earlier release shipped, and only when your effective
  `availableModels` names `claude-opus-5-5` exactly (Claude Code admits an
  id by segment prefix; the upgrade is stricter) — otherwise it stays as it
  is, with a named warning; a pin you chose is preserved with a named
  warning. Opus 5.5 runs at MEDIUM effort when nothing sets a level, where
  Opus 5 ran at high; so when the upgrade moves the pin from `claude-opus-5`
  and `.claude/settings.json` carries no `effortLevel`, it writes
  `"effortLevel": "high"` — the Opus 5 default, not the new-install
  `xhigh`. Like any top-level `effortLevel` in project settings, that value
  then outranks a level saved with `/effort`, and a top-level `effortLevel`
  in user settings, which applied to Opus 5, does not apply to Opus 5.5. A
  settings file with no pin receives the pin and no `effortLevel`: where
  nothing else sets a level, Opus 5.5 then runs at its default, medium. An
  `effortLevel` you set is never overwritten, with or without the flag
  below. `xhigh` reaches an existing install only through `--adopt-setting
  effortLevel`, on an upgrade that finds no `effortLevel` in the file (on
  the upgrade that moves the pin, the flag writes `xhigh` instead of
  `high`); once the file has one — the `high` above included — `xhigh` is an
  edit by hand. Every MIGRATE line, in a dry run too, is followed by a
  REVERT line (for the pin, the `.claude/settings.local.json` entry that
  keeps the previous value; for the written `high`, deleting the key), and
  the migration does not write without its pre-migration backup.
- **Every exit that leaves the file unmigrated names the re-run with your
  flags.** The backup that cannot be written, `python3` not found and a
  failed migration helper (an unparseable file, a failed write) each print
  one command, built in one place, that re-runs only the migration
  (`--settings-migrate-only`) with the `--adopt-setting`,
  `--allow-old-claude-code`, `--pin` and `--dry-run` you passed, the target
  and the `--pin` value quoted for the shell. In v1.4.1 the one hint (after
  a failed helper) carried no flag, and a missing `python3` gave none.

### Changed — Claude Code 2.1.280 or later is required (PLAN-193 OQ-9)

- Claude Code added Claude Opus 5.5 in 2.1.280, and 2.1.280 is the minimum
  CLI documented for it. `SUPPORT.md` carries the row, and what to edit on
  an older CLI.
- The shipped `effortLevel: "xhigh"` is the second reason. Claude Code added
  the `xhigh` level in 2.1.111, and its changelog records under 2.1.121 a fix
  for "invalid legacy enum values in `settings.json` invalidating the entire
  settings file": a settings value a CLI does not accept can make it skip
  the WHOLE project settings file — the framework's hooks and permission
  rules in it included — with no framework-side signal. Whether a CLI
  before 2.1.111 does so with `xhigh` was not measured.
- `install.sh` and `upgrade.sh` read `claude --version` before an install or
  an upgrade writes anything. Below 2.1.280 they refuse by name and exit 6,
  unless you pass `--allow-old-claude-code`, which continues with a named
  warning; a dry run names the refusal and goes on previewing. With no
  `claude` on `PATH` (CI, a headless runner), or a version they cannot read
  — no output line that names `(Claude Code)` with a version, or no answer
  within 10 seconds — they warn by name and continue. A version with
  anything after its three numbers (a pre-release such as `2.1.280-beta.1`)
  counts as below the floor. The modes that deliver no framework file exit
  before the check — `--help`, `--print-settings-baselines` (`upgrade.sh`),
  and `--arming-check` and `--uninstall` (`install.sh`). Some argument and
  target refusals run before the check and some after it (for example an
  unknown `--pin` ref in `upgrade.sh`), so a run can stop on the floor
  before it reports an argument error.
- Claude Code's npm `stable` dist-tag is behind 2.1.280 (2.1.274, measured
  2026-09-25): move to a version, not to a channel.
- In the framework repository, the test suite and the installer harnesses
  do not read the host's `claude`: under pytest, `_lib/test_isolation.py`
  puts first on `PATH` a stand-in `claude` that answers `--version` with
  the floor, and every shell harness under a `tests` directory or
  `scripts/local/` that names `install.sh` or `upgrade.sh` exports a
  `claude` function with the same answer. Limits, by shape: a test that
  builds its own `PATH` decides which `claude` it brings, a suite run with
  `python -m unittest` directly skips the isolation layer, and a child
  started with `env -i` loses the function.

### Changed — pair-rail reviewer pinned to Codex CLI 0.156.1 (PLAN-193, ADR-182)

- The payload manifest (`.claude/governance/codex-cli-pin-manifest.json`)
  pins the 0.156.1 binary by sha256 for one platform, `aarch64-apple-darwin`
  (Apple Silicon macOS), and the accepted range
  (`.claude/governance/codex-cli-pin.txt`) becomes `>=0.128.0,<0.157.0`. In
  the framework checkout, `check_pair_rail.py --verify-codex-pin` fails
  CLOSED on any other binary and on any other platform: run the rail from a
  1.4.2 checkout on that platform, with Codex 0.156.1 installed. Rail
  measurements taken before and after the re-pin are not comparable — the
  instrument changed.
- Installs do not receive `.claude/governance/`. There the gate finds no
  manifest, and a missing or mismatched Codex fails open, recorded as
  `pair_rail_codex_unavailable` — unchanged by this release.
- With `--harness codex`, the installer's version-skew warning reads the same
  range from the checkout you install from, so a Codex 0.156.x counts as in
  range for Codex as a hook host while the Codex hook fixtures are still the
  0.139.0 recordings (declared in the pin file itself).

### Fixed — the Workflow ledger persisted a `scriptPath` file before the permission decision (PLAN-193 W4b; v1.4.1 GA condition 23)

- In v1.4.1, on PreToolUse of the `Workflow` tool, `check_workflow_launch.py`
  read the regular file (up to 8 MiB) that `tool_input.scriptPath` names —
  when the call carries no inline `script` —, by absolute path or relative
  to the call's `cwd`, inside or outside the project, and wrote a copy
  (`<launch_id>.script`, mode 0600) into `launches/` in the project's state
  directory, BEFORE the harness decided whether the call may run. The copy
  was written even when a read-deny rule covered that path, and the rule did
  not cover the copy, which sits at another path; `ceo-launches.py relaunch`
  printed where the copy was, and `relaunch --out` copied it to a new file.
  The class, by shape: a hook that runs before the permission decision and
  persists the bytes of a path the harness can deny. In v1.4.1 the declared
  exit was `CEO_WORKFLOW_LEDGER=0`, which turns the whole hook off.
- **This release cures that case — the Workflow launch ledger — and no other
  hook of the class** (Known-open below). From this release the PreToolUse
  half persists no bytes of that file: it records the path, the sha256 and
  the size. A copy is taken, if at all, by the PostToolUse half of the same
  call — bound by the call's `tool_use_id`, with a run id its response
  reports — and only when the file still hashes to the sha256 recorded
  before dispatch. A script passed inline in `script` is recorded before
  dispatch, as before.
- **Exit code changed.** `ceo-launches.py relaunch` of a `scriptPath` launch
  that has a recorded sha256 and no copy — for example one bound by the
  heuristic or by hand instead of by its own call, or one whose file changed
  between the two reads — exits rc 7: it prints the exact `args`, the
  recorded sha256 and whether the original file still hashes to it, and
  nothing as the exact script; `relaunch --out` refuses, rc 7, and creates
  no file. In v1.4.1 every readable `scriptPath` launch had a copy.
- **Resume guard.** For a `scriptPath` launch recorded without a copy, the
  sha256 recorded before dispatch was not corroborated after it, so the
  guard's script comparison is inconclusive, as for an unreadable script:
  never a match, never a script advisory or block, whatever
  `CEO_WORKFLOW_SCRIPT_GUARD` says. `args` are compared, and a difference
  under a strong bind is blocked, as before.
- The limits of this cure, the class it leaves open, and the copies v1.4.1
  left behind are declared below (Known-open).

### Changed — `relaunch --out` publishes the whole copy or no copy (PLAN-190-FOLLOWUP, option B)

- v1.4.1 wrote the destination in place (an exclusive create and a write
  loop; on a handled failure, an `lstat` and then an `unlink` of the
  destination — two steps, not one atomic operation) and declared the
  partial-file and cleanup cases known-open. `ceo-launches.py relaunch --out
  FILE` now writes the copy to an exclusive temporary inside a private
  directory (`.ceo-launches-out-<hex>`, requested mode 0700) that it creates
  in FILE's directory, `fsync`s the temporary, and publishes it with a hard
  link that never replaces an existing entry. The name FILE is never passed
  to unlink, rmdir, rename or replace; the cleanup removes, by name, only
  the two names the call created — the temporary and the private directory
  — so it acts on whatever those names hold at that moment. A FILE present
  at the start, or one that appears during the write, is refused (rc 2) and
  left as it is.
- **"The whole file or no file" holds while the machine stays up and while,
  during the call, nothing else writes FILE's directory as the command
  opened it, changes what a directory on the path to FILE resolves to (a
  rename, a re-pointed symlink, a mount), or writes what the command
  creates.** After a power loss nothing is claimed: no directory is
  `fsync`ed and `F_FULLFSYNC` is not used. Use a copy only from a run that
  printed "snapshot copied to".
- A run that ends without its cleanup — a signal still at its default
  action (SIGTERM, SIGHUP, SIGQUIT and SIGKILL among them), a power loss, a
  failed removal — can leave a `.ceo-launches-out-<hex>` directory, possibly
  holding the temporary, never a partial file under FILE. It is never the
  copy: delete it, never edit it (after the link, a temporary left there is a
  second name of FILE).
- **Exit codes changed** — the class "an `--out` that creates no file never
  exits 0": `--out` for a NAMED workflow was ignored with rc 0 and is now
  refused, rc 2; `--out ""` was taken as omitted and is now refused, rc 2; a
  second read of the snapshot that failed (rc 0, no file) or that differed
  from the recorded sha256 (printed and copied, rc 0) now exits rc 7 with
  nothing printed as exact. For a record whose script was not recorded at
  launch, an `--out` refusal is rc 7.
- **Environments where v1.4.1 published the copy and this release refuses**,
  rc 2 (rc 7 for a record whose script was not recorded at launch), by shape:
  wherever a plain exclusive create of FILE would succeed but an operation
  of the new shape is refused or fails — examples, not the list: a
  directory-relative call, creating or opening the private directory, a
  second inode, `fsync`, the hard link. Measured on macOS: a FAT (msdos)
  volume (`link` answers `ENOTSUP`), an ACL entry denying
  `add_subdirectory`, and a process umask that clears the owner's write or
  search bit of the requested 0700 (0177, for example — the umask case was
  measured on Linux too). The full list of limits, and the tampering that
  stays outside the threat model, is in `docs/workflow-recovery.md`
  (framework repository; not delivered to installs).

### Added — tools for the next model or Codex release (PLAN-193 W5; maintainer tooling)

- `.claude/scripts/re-pin-codex.py <version>` resolves the `@openai/codex`
  package and its platform artifact on the public npm registry, checks the
  platform tarball's sha512 against the registry integrity, hashes the
  payload member in memory (one tar header shape is accepted; any other is
  refused by name), and EMITS a new re-pin pack: the pin and manifest as
  `.new` files, the ceremony script, and a sentinel draft whose human
  sections are `TODO(owner)`. It never applies a pack, installs a CLI, signs
  or commits.
- `.claude/scripts/check-substrate-drift.py`, offline unless `--fetch`,
  reports whether the installed Codex is the version the payload manifest
  pins (a version comparison, not the payload hash:
  `check_pair_rail.py --verify-codex-pin` stays the gate), whether npm
  `latest` moved past the pin (only from a cache an explicit `--fetch` left),
  whether `claude --version` differs from the substrate ledger, and which
  model ids the installed Claude Code knows that ADR-149 does not cover (read
  from the binary; a format it cannot read is a named `unknown`). Report mode
  exits 0; `--strict` exits 1 on drift.
- `.claude/scripts/derive-settings-baselines.py` derives the per-key part of
  `upgrade.sh`'s settings-migration table (old, new and superseded values)
  from the templates the GA tags shipped. `--check scripts/upgrade.sh`
  compares it with the table in `upgrade.sh`: rc 0 on a match, rc 1 with
  every difference named, rc 2 when it cannot derive (no GA tags, as in a
  shallow clone) or meets a shape it does not model.
- No hook or shipped settings file runs the three tools, and no CI workflow
  step invokes them directly: their tests do. The tests live in
  `.claude/scripts/tests/`, which the CI test jobs, `release.sh preflight`
  and the release workflow run. One of them runs
  `derive-settings-baselines.py --check scripts/upgrade.sh` against the GA
  tags of the checkout it runs in and fails unless that answers rc 0; a
  checkout without the GA tags (a shallow clone) skips it, visibly.
  `release.sh preflight` runs in the maintainer's checkout and the release
  workflow clones the full history, so both run that check on the tree they
  release. `install.sh` copies every top-level `.claude/scripts/*.py`, so
  the tools reach installs, where they answer only "not applicable" or
  refuse (exit 2): they need the framework checkout.
- New framework-repository document (not delivered to installs):
  `docs/adopter-new-model-fast-access.md`, the per-machine route
  (`.claude/settings.local.json`) to use a newly released Claude model before
  a framework release adopts it.

### Fixed — maintenance sweep (S357)

- **`templates/.mcp.json` registered a Codex MCP server that can no longer
  start.** It ran `codex mcp-server`, a subcommand codex-cli 0.154.0 removed;
  measured on codex-cli 0.155.0, the entry can never complete an MCP
  handshake. The template now ships an empty `mcpServers`. The pair-rail
  gate does not use it (it runs `codex exec`); the hooks on the
  `mcp__codex__*` tools (`check_codex_filewrite.py`, `check_codex_response.py`
  and its `codex_review_invoked` event) stay idle while no server named
  `codex` is registered. `install.sh` never overwrites an existing
  `.mcp.json` and `upgrade.sh` does not touch it, so an install made from an
  earlier release keeps the dead entry until you remove it:
  `claude mcp remove codex -s project`, or delete the `codex` key under
  `mcpServers` by hand (on Claude Code 2.1.280 `claude mcp remove` also
  dropped the file's `_comment` key).
- **`/ceo-boot` assumed task tools that current models do not get.** Claude
  Code offers the task-tracking tools (`TaskCreate`, `TaskList` and the rest)
  by default only on older models: by default a session on Opus 4.8,
  Opus 5 / 5.5, Sonnet 5 or Fable 5.x has none of them
  (`.claude/commands/ceo-boot.md` lists what still turns them on).
  `/ceo-boot` now checks what the session offers and, without them, renders
  its follow-up candidates inline instead of creating tasks. `/ceo-boot` and
  `/debate` no longer list task tools in `allowed-tools`.
- **`CLAUDE_CODE_SUBAGENT_MODEL_FORCE` flattens the model tiering.** Since
  Claude Code 2.1.257, when it is on, every subagent runs on the subagent
  model (or the main model) and `model:` frontmatter and per-spawn models are
  ignored — a VETO rite can fall below its floor tier. A test now asserts
  that neither the framework's own settings nor any settings template nor
  the `SETTINGS_DELTA` documented in `.claude/hooks/route.py` sets it, and
  `scripts/install-accelerators.sh` warns — never writes — when it is on in
  the shell, in user settings, or in the app's project or local settings.
  The same script now says that `CLAUDE_CODE_SUBAGENT_MODEL` is only the
  default subagent model since Claude Code 2.1.251.
- **The audit-retention claim was false.** `docs/soc2-audit-mapping.md` said
  the audit log stays "90 days live on disk". By default the framework keeps
  its audit log in `~/.claude/projects/<slug>/`, and size-based rotation
  renames it to archives in the same directory. Claude Code's own cleanup
  sweep (read in the 2.1.280 binary) walks every project directory under
  the `projects/` directory of its config home and unlinks each top-level
  `*.jsonl` older than the `cleanupPeriodDays` of the session that runs the
  sweep (default 30), with no name filter — so the live `audit-log.jsonl`
  and its rotated `audit-log-YYYY-MM[-N].jsonl` archives are deleted like
  aged transcripts.
  The retention you can count on is the smallest `cleanupPeriodDays` any
  sweeping session on the machine resolves. The document now says so, and
  `INSTALL.md` §Audit-log retention gives the mitigation: a large
  `cleanupPeriodDays` at user scope (for example 3650 in
  `~/.claude/settings.json`), scheduled backups with
  `.claude/scripts/ceo-backup.sh`, and never `touch` an audit file (it
  rewrites the times forensic review relies on).
- **Settings guard loadability, pinned by test.** Claude Code drops a WHOLE
  settings file — every hook and every deny rule in it — when a `PreToolUse`
  or `PermissionRequest` hook entry in it cannot be loaded. A new test
  replicates that rule (read in the Claude Code 2.1.277, 2.1.278 and 2.1.280
  binaries) and asserts that no shipped settings surface trips it; it turns
  red when the substrate ledger moves to a newer Claude Code, until the rule
  is re-derived. It does not replicate the full settings schema, which is
  where the `effortLevel` reason above lives.
- `.claude/scripts/run-skill-benchmark.py` sent `temperature=0` and
  `top_p=1`, which the anthropic Python SDK 1.x does not accept and current
  Claude models reject; it now sends no sampling parameters, and its
  documentation now says model output is not deterministic.
- **Codex as a hook host.** A Codex upgrade can re-key every hook's trust
  while `.codex/hooks.json` stays byte-identical (measured on nine of the
  twelve shipped entries: trust hashes recorded under codex-cli 0.139.0
  list as `modified` under 0.155.0), and
  the arming check's `ARMED` reads project trust only: after upgrading Codex,
  re-check `/hooks` (`INSTALL.md`, the Codex templates,
  `docs/degradation-outside-claude-code.md`). Under Codex, leave
  `CEO_BASH_FORCE_PUSH_REWRITE` unset: with it set, the Codex adapter answers
  a force-push with a plain `allow`.
- The substrate ledger (`.claude/scripts/substrate-watch.json`) records Claude
  Code 2.1.280 as the version it was reconciled against; the components it
  holds back, and why, are in `docs/substrate-adopt-2026-09.md`.

### Known-open (declared by this release)

- **Audit files can be deleted by Claude Code** (above). No plan carries a
  structural cure; `verify_chain()` checks only what is still on disk.
- **Model pins.** The limits the amendment declares by shape (above) stay.
  The pin (`claude-opus-5-5`) and `fallbackModel` (`claude-opus-5`) are now
  different models: an availability fallback changes the serving model for
  the turn in which it fires, pays cache writes on the fallback model for
  the context it holds no live cache for (and on the pin, on the return,
  for what its cache lost meanwhile), runs without the Opus 5.5 thinking
  blocks, and no hook records it. Going back to an older release does not
  move the pin back: restore the pre-migration backup, revert the committed
  upgrade, or override the value in `.claude/settings.local.json` as the
  REVERT line shows.
- **Thinking on always-on models.** The adapter's list of always-on models is
  kept by hand: an always-on model it does not list answers a caller's
  `{"type": "disabled"}` with an HTTP 400.
- **The Claude Code version check reads one CLI**: the `claude` found on
  `PATH` when the script runs. The CLI that later opens the project can be
  another one, and with no `claude` on `PATH` the scripts only warn.
  `SPEC/v1/install-cli.md` lists neither `--allow-old-claude-code`,
  `--adopt-setting` nor exit 6 (its exit-code table already stopped at 3).
- **The class of v1.4.1 GA condition 23 is declared, not cured.** This
  release cures the case that condition describes, the Workflow launch
  ledger. It does not establish that no other hook has the shape of the
  class: a hook that runs before the permission decision and writes into
  the project's state directory bytes of a file the call names — for
  example, an excerpt of its content in an audit event — is not touched by
  this release and stays as it is.
- **The `scriptPath` cure (above) has declared limits.** Before the
  permission decision the PreToolUse half still opens and reads the file,
  and records its sha256 and size whether or not the call is then allowed:
  whoever can read the state directory can test a guess of the content
  against that hash. The copy the PostToolUse half takes re-reads the PATH,
  so it is not a copy of what the harness ran — only bytes that hash to the
  value recorded before dispatch — and, like any copy in `launches/`, it is
  not covered by a read-deny rule on the original path. The cure relies on
  the harness firing PostToolUse, with the call's `tool_use_id` and a run id
  in its response, only for a call it allowed and ran. The PostToolUse half
  does not serialize its re-read, its copy and its manifest rewrite: two
  PostToolUse events of one call, with the file changing between them, can
  leave the record naming no copy (rc 7), and a failed manifest rewrite
  after the copy leaves the run unbound and the copy named by no record. The
  `_comment` of the hook's registration in the settings files still says the
  snapshot is recorded before dispatch.
- **The copies earlier releases wrote before the permission decision stay
  in `launches/`**: this release removes none. While one exists,
  `relaunch` of the record that names it still prints it as the exact
  script and `relaunch --out` still copies it; deleting one makes that
  record fail its integrity check (inconclusive for the guard, rc 7 for
  `relaunch`).
- **`relaunch --out`**: the leftover private directory and the trust in the
  destination's directory described above.
- **The three fast-lane tools** run when someone runs them. The one
  automatic check is the test that runs the `--check` of
  `derive-settings-baselines.py` in a checkout with the GA tags (above); a
  checkout without them skips it.
- **Codex as a hook host**: the range admits 0.156.x while the hook fixtures
  stay at 0.139.0 (above).

### Known-open (carried — NOT cured by this release)

- **The v1.4.0 annex.** The signed v1.4.0 verdict carries an annex of P1
  findings and declared conditions marked "cure in 1.4.1"; the `[1.4.1]`
  entry and the v1.4.1 tag annotation re-targeted that cure to 1.4.2. **This
  release does not cure them, and no release is assigned to their cure**
  (Owner decision, 2026-09-22, PLAN-193 OQ-3). The list is the
  `NEW FINDINGS (annex)` sections of the verdicts under
  `.claude/plans/PLAN-169/repass-rc1/` and `.claude/plans/PLAN-169/repass-ga/`,
  plus the `conditions:` of `.claude/governance/pair-rail-verdict-v1.4.0.md`.
- **What v1.4.1 left open**, with two exceptions cured above: the
  `relaunch --out` item of the `[1.4.1]` entry's Known-open (within the
  limits stated above) and the case of v1.4.1 GA condition 23, the Workflow
  launch ledger (within its declared limits; the class that condition names
  stays open, above). Everything else stays open, by source: the Known-open
  of the `[1.4.1]` entry; the open findings the conditions of the v1.4.1 GA
  declare (`.claude/plans/PLAN-192/repass-ga/CONDITIONS-ga.md`); and the
  `NEW FINDINGS (annex)` and P2 findings of the v1.4.1 cross-review
  verdicts — the rc.1 rounds under `.claude/plans/PLAN-192/repass-rc1*/` and
  the GA re-pass under `.claude/plans/PLAN-192/repass-ga/`, bound by the
  signed `.claude/governance/pair-rail-verdict-v1.4.1-rc.1.md` and
  `.claude/governance/pair-rail-verdict-v1.4.1.md`. Among them are findings
  in the Workflow guard and ledger, in `approval_gate.py` and the other
  PLAN-190 recovery tools, and in delivery (`upgrade.sh` delivers
  `.claude/scripts/local/` while a fresh install does not). No release is
  assigned to their cure.

### What an adopter should know before installing or upgrading

- Update Claude Code to 2.1.280 or later first: the installer and the
  upgrader refuse an older `claude` they find on `PATH` (exit 6).
  `--allow-old-claude-code` continues past that refusal, and `SUPPORT.md`
  says what to edit in `.claude/settings.json` for an older CLI.
- After `upgrade.sh`, a pin the framework shipped moves to `claude-opus-5-5`
  when your `availableModels` lists it, and a file with no `effortLevel`
  gets `high` with it; read the MIGRATE and REVERT lines. For `xhigh`, pass
  `--adopt-setting effortLevel` on that upgrade; once the file has an
  `effortLevel`, the flag keeps it, and `xhigh` is an edit by hand.
- Scripts that call `ceo-launches.py relaunch --out FILE` must use FILE as
  the copy only after a run that printed "snapshot copied to" — never after
  rc 2 or rc 7 — and never use a `.ceo-launches-out-<hex>` directory. A
  `relaunch` of a `scriptPath` launch recorded without a copy exits rc 7
  (above).
- The `<launch_id>.script` copies v1.4.1 wrote before the permission
  decision stay in `launches/`, in the project's state directory, after the
  upgrade. Deleting one removes those bytes and makes the record that names
  it inconclusive (rc 7 for `relaunch`).
- Remove the dead `codex` entry from `.mcp.json` if your install has one.
- Raise `cleanupPeriodDays` at user scope and back up the audit files if you
  rely on the audit trail for longer than 30 days.

## [1.4.1] - 2026-09-18

Patch release for adopters who run long autonomous `Workflow` pipelines
(PLAN-190). Every `Workflow` launch is now recorded BEFORE dispatch, a resume
whose `args` differ from the recorded launch is blocked instead of going
through, and the exact recorded call can be read back from the ledger rather
than rebuilt from memory. Both kill-switches are named below. No speed claim.

### Added
- **Workflow launch ledger + resume guard** (PLAN-190 W1). A new hook,
  `check_workflow_launch.py`, registered on PreToolUse and PostToolUse for the
  `Workflow` tool in the dogfood settings and in the base template (the `user`
  profile keeps it), records every launch BEFORE dispatch — script sha256 plus a
  snapshot of the script bytes, the literal `args` (absent ≠ null), the
  `resumeFromRunId`, the code revision of the working directory — and binds the
  run id the runner returns. A resume over DIFFERENT args is blocked with a
  counts-only reason (the detail stays in the manifest); a resume over a
  different script with the same args is advisory by default
  (`CEO_WORKFLOW_SCRIPT_GUARD=enforce` to block). A block needs a strong bind
  (by `tool_use_id` or manual): a heuristic bind never sustains one, args or
  script alike; a blocked attempt is never a candidate for heuristic binding.
  The recorded manifest is validated before it is evidence (args
  canonical/hash consistency, script hash against its snapshot bytes, id
  shapes): an inconsistent record is inconclusive for the guard and refused
  as "exact" by `relaunch`. ONE override path for every block, carried by the
  call or the process and never by stored state: a `description` starting
  with `CEO_WORKFLOW_RESUME_FORCE: <why>` on the call itself, or
  `CEO_WORKFLOW_RESUME_FORCE=1` in the harness environment — recorded as
  `mismatch_forced` with its source and reason, announced. A `scriptPath`
  is read only as a regular file of at most 8 MiB (FIFO, device, larger
  file or NUL byte ⇒ recorded unreadable, args still compared); a torn
  index line never swallows the next record; the CLI finds the hook's
  ledger from any subdirectory of the project; the plugin build ships the
  recovery CLI with the guard. `args` are recorded in their original key
  order too (`relaunch` prints that order; a reordered resume counts as a
  difference); notices for allowed calls reach the model as
  `additionalContext`; the block reason names the deliberate-change route
  (`args.resume` style resumes declare themselves); the run id is taken from
  a top-level `runId`/`run_id` key of the response, else from the harness
  `Run ID:` label, else from the only id-shaped token (two different
  labelled ids, or two different unlabelled ones, bind nothing); a record
  whose construction or write fails is still inconclusive-recorded or
  breadcrumbed; `relaunch --out` never overwrites.
  `CEO_WORKFLOW_RESUME_GUARD=0` (advisory mode, ledger kept),
  `CEO_WORKFLOW_LEDGER=0` (off). Fail-open on infrastructure, with the gaps
  listed under Known-open below. CLI
  `ceo-launches.py` (`list · show · relaunch · check · bind · orphans ·
  report`) and operator doc `docs/workflow-recovery.md`. Inventory:
  60 hook scripts, 49 wired, 52 event registrations, 72 `_lib` modules.
- **Recovery and approval tools for autonomous pipelines** (PLAN-190 W2/W3).
  Five stdlib-only CLIs under `.claude/scripts/`, called by a workflow phase,
  a recovery rite or a human — NO hook enforces any of them yet (the
  single-writer hook and quota admission are future ceremonies).
  `approval_gate.py` decides APPROVED/REJECTED by code from a policy file
  (minimum score, a closed severity enum, blocking severities, a cap per
  severity, reviewed revision == final revision, green gate): under the
  source repository's default policy
  (`tests/fixtures/approval/policy-default.json`) a missing score, findings
  list, reviewed revision or gate list, a prose score, an out-of-enum
  severity and a wrong scale are REJECTED with the rule named (doc:
  `docs/approval-gate.md`); the inputs that still come out APPROVED are
  listed under Known-open below.
  `test_refs.py`
  normalises test references — file path, node id, bare function,
  `Class.method` — to pytest node ids by static `ast` (tests are never
  executed); an ambiguous BARE name is an error that lists the candidates.
  `mutant_sandbox.py` runs a mutant inside a disposable detached
  worktree of an identified revision, records the outcome per (revision,
  mutant, command) so a valid verification can be reused, removes the copy in
  `finally`, and reports an ERROR outcome if `git status` of the
  implementation tree differs before and after. `worktree_lock.py` gives one
  writer per worktree among callers that use it (`O_EXCL` lock file,
  heartbeat, `steal` when the holder's heartbeat is older than the
  `--stale-minutes` the CALLER passes — the holder's own TTL is not
  consulted — and `release` by the owner or with `--force`).
  `phase_checkpoint.py` keeps an append-only ledger of steps
  completed inside a phase, bound to the code revision: steps recorded under
  another revision are listed as stale and never count.

### Fixed
- **`ceo-launches.py relaunch --out` could leave a truncated copy and report
  success** (PLAN-190 W1.1). The snapshot copy was written with a single
  `os.write`, which may write fewer bytes than asked — and the truncated file
  is exactly what the recovery rite passes back as `scriptPath`. The write
  now continues until every byte is down; on a HANDLED failure (an I/O error,
  a write that makes no progress, an error surfacing at `close`) the command
  returns rc 2 naming the incomplete write and TRIES to remove the partial
  file: it compares the destination's inode with the one it created (`lstat`)
  and then unlinks by name. Those are two steps, not one atomic operation: a
  concurrent writer that replaces the destination in between loses ITS file,
  and the message still says the partial file was removed. If the `lstat` or
  the `unlink` fails, the partial file STAYS and the message says so. Not
  handled at all: an interruption that is not an `OSError` (Ctrl-C, a signal)
  in the middle of the write can leave a partial file, with no message. So
  this is NOT yet "the whole file or no file", and the cleanup is NOT
  guaranteed to touch only this call's file (known-open below; the structural
  cure — exclusive temporary file, publish by no-replace `link`, never unlink
  the destination — comes after this release).

### Known-open (found by this release's cross-review)
Cross-review round 1 of the rc.1 candidate (2026-09-18) returned NO-GO on
five declared conditions that were false against the code; no P0. Round 2,
over the same code with the text corrected, returned GO-WITH-CONDITIONS on
two parts and NO-GO on one sentence (the cleanup promise of `relaunch
--out`, above); no P0. Round 3 is again over the same code. Every CODE
finding of rounds 1 and 2 is still open in this release; the verdicts are
under `.claude/plans/PLAN-192/repass-rc1-20260918-NOGO-r1/` and `-r2/`. By
class:
- **Workflow guard** (`launch_ledger.py`). An incomplete read of the index
  (an I/O error midway, or a torn newest line) is not signalled: the guard
  then compares against the previous surviving binding and can BLOCK a
  legitimate resume (exit: the `CEO_WORKFLOW_RESUME_FORCE` declaration). A
  resume from another worktree, or of a run launched before the hook
  existed, finds no manifest and proceeds with NO notice. When both `runId`
  and `run_id` are present and differ, the first wins; an id whose tail is
  too long is bound by its prefix instead of being rejected. When a
  mismatch is NOT blocked (advisory mode, or a heuristic bind) the notice
  names the CURRENT call's manifest as "the recorded call", and once that
  call is bound `relaunch <run-id>` prints the changed inputs. Ledger writes
  follow a symlinked `launches/` directory or
  index file (same-user tampering is outside the threat model). An INLINE
  script larger than 8 MiB is recorded, but its snapshot is read back through
  the 8 MiB reader, so the record is inconclusive for the guard.
- **`relaunch --out`**: the partial-file cases and the non-atomic cleanup
  named under Fixed above; and when the second read of the snapshot fails the
  command prints the "exact recorded call" heading, creates no file and exits
  rc 0 — the copy exists only when the output says "snapshot copied to".
- **`approval_gate.py`** still APPROVES a non-finite score (`"NaN"`,
  `"nan/10"`), a gate entry with no `failed` count or no `cmd` (or a negative
  `failed`), and a policy whose restriction key is misspelled (unknown keys
  are ignored, so the restriction silently disappears). A DUPLICATE JSON key
  in the evidence keeps the last value (`"findings":[…P0…],"findings":[]`
  approves). No default policy file is delivered to adopters: the one the doc
  names is a fixture under `tests/` in the source repository.
- **`test_refs.py`**: a node id whose class does not exist resolves to the
  only test with that function name in the file; parametrised ids
  (`test_x[case]`) are not normalised and come back `node-not-found`; a test
  file that cannot be read or parsed is treated as having no tests, so a name
  that is really ambiguous can resolve.
- **`worktree_lock.py`**: `steal` trusts the caller's `--stale-minutes`, not
  the holder's TTL; two concurrent `steal` calls can both succeed; the fixed
  `writer.lock.tmp` name follows a symlink; `release --force` on an
  unreadable lock is not logged.
- **`mutant_sandbox.py`**: the patch is hashed and then re-read by path
  (another producer can swap it in between); `gc` removes a sandbox that is
  still running (its state stays `creating` until the end); every non-zero
  exit code is recorded as `killed`, including a runner or collection error;
  a command that times out has its direct child killed, but descendants it
  started keep running while the sandbox is removed under them.
- **`phase_checkpoint.py`**: `--rev HEAD` is stored literally; an append
  after a torn line loses both records.
- **Delivery**: `upgrade.sh` delivers `.claude/scripts/local/` (maintainer
  tooling, the release driver `release.sh` included) to adopters, while a
  fresh install does not; no delivered hook, command, settings file,
  template, skill or top-level script references `release.sh`.

### Known-open (carried from v1.4.0 — NOT cured by this release)
- The signed v1.4.0 verdict carries an annex of P1 findings and declared
  conditions marked "cure in 1.4.1". **This release does not cure them.**
  1.4.1 is an out-of-order patch that ships the Workflow guard to adopters
  now, by Owner decision (2026-09-18); none of those findings is addressed by
  the changes in this release. The annex stays known-open, unchanged, and
  its cure is re-targeted to 1.4.2. The list is the `NEW FINDINGS (annex)`
  sections of the rc.1 and GA verdicts under
  `.claude/plans/PLAN-169/repass-rc1/` and `.claude/plans/PLAN-169/repass-ga/`,
  plus the `conditions:` of `.claude/governance/pair-rail-verdict-v1.4.0.md`.
- What an adopter should know before upgrading: the new guard CAN BLOCK (a
  resume over different `args`) and the `user` profile keeps it — this
  extends condition 63 of the v1.4.0 verdict (the `user` profile is not
  advisory-only). On an adopter it takes effect only after an `upgrade.sh`
  to a version that contains it, with the install ceremony recorded in the
  install-state or passed to the upgrade, `jq` available, and without
  `--no-settings-merge`; otherwise the hook file arrives unregistered and
  nothing changes. Exit routes: `CEO_WORKFLOW_RESUME_GUARD=0` (advisory,
  ledger kept), `CEO_WORKFLOW_LEDGER=0` (off), or the per-call
  `CEO_WORKFLOW_RESUME_FORCE: <why>` declaration.

## [1.4.0] - 2026-09-07

Continuity, delivery and installer-safety train (PLAN-179 compaction
continuity and work-boundary persistence; PLAN-182 per-project audit
isolation; PLAN-183 delivery routes and an upgrade that finally
delivers `docs/` and `.github/`; PLAN-185 installer write
confinement; PLAN-169 a `user` profile derived from the base instead
of hand-maintained). The headline for an adopter is that
`upgrade.sh` now delivers the two trees it silently skipped for four
releases, and that every delivered-template destination is now confined
to the directory you hand it (the seams that are not — backups, the
schema-doc refresh, `.gitignore` appends, the dispatcher copies, the
`state/` seed — are signed conditions of this rc, with the pre-upgrade
checks in `docs/UPGRADE-PROCEDURE.md`; the cross-model re-pass verdicts committed
with the release evidence are an annex of this pre-release — every P1 they list
is a mandatory cure before the GA). Two security fixes in the install path, one
audit-log scope change adopters share a machine over, and the honest
part: the compaction-continuity feature this train is named after
shipped only after its first design was measured and found to deliver
nothing. As always: governance and auditability — no speed claim.

### Fixed — `upgrade.sh` silently skipped `docs/` and `.github/` (PLAN-183, ADR-194)

The most consequential adopter-visible defect closed in this release.
From v1.0.0 through v1.3.0, `scripts/upgrade.sh` never delivered the
`docs/` and `.github/` trees that `install.sh` delivers — an adopter
who installed once and upgraded thereafter kept the *original*
`docs/BRANCH-PROTECTION.md`, `docs/rotation-log.md`, `.github/CODEOWNERS`
and the two CI workflow templates forever, with no warning.

- **Upgrade now delivers both trees**, hash-gated against the git
  generations of the SOURCE file: a byte-pristine copy of a known prior
  framework generation is replaced, anything you edited is PRESERVED
  loudly. A pre-existing copy of yours that is byte-identical to ANY
  generation, the current one included, counts as the framework's own
  copy too — replaced or mode-normalised, and registered as
  framework-owned — even if the framework never delivered it (signed
  condition of rc.1: edit or move such a file before upgrading).
  Backups go to `.claude.bak/<timestamp>` without the destination
  confinement the deliveries get: keep that path absent or empty, never
  a symlink (signed condition of rc.1). Delivery is registered
  only after it actually happened, when a prior registration's digest
  still matches, or — the third route — when a pre-existing file's bytes
  equal the current or a historical generation of the source (naked byte
  equality; signed conditions 5 and 42). A delivery that
  fails its PRECONDITION (route table, a table row whose source or
  destination relpath is not confined, transform) exits 3 and
  persists `upgrade_succeeded: false` in the install-state rather than
  recording a full upgrade that did not happen (`6304f66`); a failure of
  the WRITER or the RENDERER after a route was selected (a read-only
  `docs/`, a failed tempfile or rename, a failed CODEOWNERS render) is
  still reported PRESERVED with exit 0 — signed condition of rc.1: read
  the delivery summary, a PRESERVED route you never edited is a failed
  delivery. A sensitive path already TRACKED by git
  (`.claude/settings.local.json`, `.claude/state`,
  `state/mcp_client_secrets`) aborts the upgrade AFTER hooks, scripts and
  settings were rewritten (signed condition of rc.1: `git ls-files` over
  those paths must print nothing before upgrading).
  A route whose SOURCE file is missing (or not a regular file) in the
  executing checkout is counted SKIPPED, not failed — the run still exits
  0 (signed condition of rc.1: upgrade from a complete checkout and read
  the delivery summary; any SKIPPED route without `--pin` means an
  incomplete upgrade).
  A route whose transform has no renderer in the running version is
  a failed delivery too: named, `upgrade_succeeded: false`, exit 3
  (`5518888`, all four sites of the class).
- **One route table, three readers.** `scripts/delivery-routes.tsv` is
  now the single answer to "which source file produces this
  destination?", read by the manifest generator, `doctor.sh` and the
  parity classifier — no reader carries a private copy. Four separate
  defects (`upgrade.sh` not delivering, the parity classifier and the
  manifest generator resolving the wrong source, and `doctor.sh`
  REPAIRING with the wrong file) all had the same shape: no single
  owner for that question. Contract: ADR-194 (`b6de7cf`, `aaf32c7`,
  `6304f66`, `3bc3638`).
- **`doctor.sh` repaired deliveries from the wrong source** before this
  release; the positive control reproduced a leak of the maintainer's
  live `.github/CODEOWNERS` into an adopter repo. `doctor.sh` now reads
  the same route table (`6304f66`).
- **Shallow-clone caveat, named:** in CI with `actions/checkout` at
  depth 1 the hash gate cannot see older generations, so files are
  PRESERVED (safe) and reported `STALE`. Deepen the history before
  upgrading in CI if you want the refresh.

### Security — delivered-template destinations are confined to the target (PLAN-185, ADR-196)

- **`install.sh` wrote outside `$TARGET`** when a destination path was a
  pending symlink or hardlink. One destination-confinement predicate now
  lives in `scripts/_framework_manifest_set.sh`; `install.sh` pre-flies
  every delivered-template destination before the first write and
  refuses by name, `upgrade.sh` consumes the same predicate. E2E in
  bytes: 105/0 after the cure against 22/33 before it (`cc00235`).
  Several seams stay outside that preflight in this release candidate
  and are signed conditions of rc.1: the `state/mcp_client_secrets`
  seed (a symlinked `TARGET/state` is followed by `mkdir -p`/`chmod`);
  a refused SOURCE template (symlink outside the checkout) that install
  reports as `SKIP` and upgrade as `PRESERVED` while still exiting 0; a
  source MISSING from the executing checkout (`SKIP`, exit 0, on both
  install and upgrade); the `.gitignore`/`.claude/.gitignore` appends,
  which test `-L` only, so a hard link there is written through; the
  `.claude/dispatcher/` copies, which run no check at all (a symlink or a
  hard link there is written through); and `install_dispatcher`, which
  re-copies unconditionally on a rerun (edited dispatcher files are
  overwritten — back them up first); and the deny-baseline merge of
  `install.sh`, which writes a PID-named sibling of `.claude/settings.json`
  outside the preflight (a pre-placed symlink there is written through —
  the `find` check over `.claude/` in `docs/UPGRADE-PROCEDURE.md` catches
  it; run it before a fresh install too).
- **`--github-owner` with a `/` in it left `.github/CODEOWNERS` at zero
  bytes, permanently.** The handle grammar is now shared by producer and
  consumer, the file is rendered through a pipe and written atomically,
  and a truncated CODEOWNERS is recovered from delivery EVIDENCE
  (`cc00235`) — evidence meaning a manifest line that NAMES the path;
  the line's digest grammar is not validated, so keep the manifest
  intact; a CODEOWNERS you switched off survives only a re-run WITHOUT
  `--github-owner` — deleting the file makes the installer render it
  again, and an emptied file with a manifest record is re-rendered too
  (signed condition 61 of rc.1).
- **`uninstall.sh` followed a crafted manifest out of the target.** The
  install manifest is a plain file in your repo and is NOT
  integrity-checked before the removal walk; pre-cure, a record naming
  `../outside/victim.txt` was REMOVED, and with a symlinked `docs`
  component the walk deleted an outside file and the backup archived
  bytes read through the link. Every removal, every backup entry and
  every restore member OUTSIDE `.claude/` is now tested lexically
  (absolute paths, `..` segments, control characters, whitespace and glob
  metacharacters, option-like `-` leaders) and physically (a symlinked
  ancestor under the target) (`6160578`); the `.claude` subtree of a
  restore archive is still extracted whole after a name-only check
  (signed condition 57 of rc.1: restore only unmodified archives this
  uninstaller produced).
- **`doctor.sh` stopped discarding unsafe manifest records in silence** —
  traversal, absolute path, any control byte, symlinked ancestor,
  malformed digest and duplicate relpath are each a NAMED discard, capped
  at 20 and folded into `UNRESOLVED` (rc 1); a manifest containing a NUL
  is refused before the parse (`ba15c71`).
- A fail-closed census of installer write sites
  (`check-installer-write-safety.py`) ships as a RATCHET in `validate.yml`
  with its blind spots declared in the plan, not papered over.

### Changed — audit log resolves per PROJECT, not per `$HOME` (PLAN-182, ADR-001)

**Adopter-visible if you run the framework in more than one repository
under the same `$HOME`.** Runtime state — the HMAC audit log, its key,
lock, errors, salt and sidecars — now resolves through one family
resolver (`.claude/hooks/_lib/runtime_paths.py`) using Claude Code's own
path-based project slug, instead of a literal `ceo-orchestration`
directory shared by every project (`9de4efc`, `965fb13`, `3d16070`).

- For repositories with DISTINCT resolved runtime directories, this separates
  their chains and keys and provides correct
  `project` attribution for the emitters that carry the field (a handful
  of newly specified actions still omit `project` or `session_id` and
  cannot be attributed in a shared `CEO_AUDIT_LOG_PATH` — rc.1 condition
  23), a `verify_chain()` that means something per project — for stretches
  written by one writer at a time: the previous HMAC is still read before
  the log lock is taken, so two parallel writers can chain to the same
  predecessor and a break is then reported that nobody caused (signed
  condition 67 of rc.1; same order as v1.3.0) — and a per-project HMAC key
  and salt, preventing correlation by `prompt_sha256` between those
  repositories. The path-derived slug can collide: `/srv/a-b/c` and
  `/srv/a/b-c` both yield `-srv-a-b-c`. Verify distinct resolved directories
  before using multiple repositories (rc.1 condition 30); a collision shares
  the log, key and salt. The per-project key is minted on first use and that first
  mint is not exclusive: create it with a single writer before the first
  session (signed condition 68 of rc.1; `docs/UPGRADE-PROCEDURE.md`,
  check 11).
- **The old location is not migrated for you.** The pre-v1.4.0 chain
  under `$HOME/.claude/projects/ceo-orchestration/` stays where it is;
  `SPEC/v1/audit-log.schema.md` records the change as v2.58 and names the
  legacy path.
- **Plan state and scratchpads move too, and are not migrated either.**
  `state_store.py` resolves through the same family resolver, so a
  repository with an ACTIVE plan on v1.3.0 opens a NEW, empty state
  store after the upgrade — inter-agent handoffs report missing state,
  `/resume` finds no cached graph, while the old SQLite files stay on disk under the
  legacy directory. Two documented routes: set `CEO_PROJECT_NAME` to
  the legacy slug (the explicit escape hatch in `state_store.py`) until
  the plan closes, or copy ONLY `scratchpad/`, `skill_proposals/`,
  `skill_index/` and `session_graph/` from `<legacy>/state/` into
  `<new-runtime-root>/state/`, plus the root-level `session-graphs/` (the
  cached `/resume` graphs; `/resume` otherwise rebuilds from the audit log,
  git and the plan markdown and never reads the stores — sessions recorded
  before the upgrade stay in the legacy chain). The CLI
  `python3 .claude/hooks/_lib/runtime_paths.py --state-dir` prints
  `<new-runtime-root>`; append `/state` for the store destination.
  NEVER copy the whole legacy `state/` directory or its flat files:
  its audit recovery spools can contaminate the new project's chain.
  First drain or quarantine those spools in the legacy context; follow
  `docs/UPGRADE-PROCEDURE.md` and rc.1 condition 27. Automatic migration
  remains a pre-GA follow-up.
- **The limit that does NOT go away:** under the same UID one project's
  process can still read another's `0700` directory and `0600` key. A
  real boundary needs a separate UID; that is out of scope by decision,
  and said here rather than implied away.
- The resolver ships with a CLI
  (`python3 .claude/hooks/_lib/runtime_paths.py --state-dir|--slug|--project-dir
  [--project PATH]`) used by the pre-push templates and by
  `ceo-backup`/`ceo-restore` (`3d16070`).

### Changed — upgrade withholds hook registration when the ceremony is unknown (PLAN-169, `5930974`)

- `upgrade.sh` now DERIVES which hooks to register from the settings
  template of the ceremony you actually installed, instead of a
  hardcoded roster that would have silently promoted a `--ceremony user`
  install to the maintainer profile.
- **New behavior you may see:** with no readable install-state, no
  `--ceremony` flag and no `CEO_UPGRADE_CEREMONY`, the upgrade reports
  `PARTIAL (ceremony unknown)` and registers NO hooks — only the settings
  both profiles declare identically. Pass `--ceremony maintainer` or
  `--ceremony user` to register the profile you installed. The previous
  behavior (inferring, and getting it wrong) could turn an advisory hook
  into a blocking one.

### Changed — the `user` ceremony profile is now DERIVED, not hand-maintained (PLAN-169, ADR-197)

- `templates/settings/settings.user.json` is generated from
  `settings.base.json` by a declared subtraction recorded in its own
  `_derivation` key, applied by `.claude/scripts/gen-settings-user-template.py`,
  with a byte-for-byte `--check` mode wired into `validate.yml` (`303ae55`).
- The prose it replaces had rotted: it claimed the profile removed
  "exactly 10" hooks while a census measured 26 removed basenames, a
  hand-narrowed matcher, a silently dropped second registration and four
  hand-edited annotations. **The `user` profile therefore registers more
  hooks than in v1.3.0** (20 → 29 registrations, 28 basenames); every
  newly included hook that can still block is named in
  `_derivation.blocking_inclusions` together with its escape route.

### Added — compaction continuity and work-boundary persistence (PLAN-179, ADR-195)

Two new hooks, both **advisory, both fail-open, neither blocks a tool
call today**:

- **`check_compact_pinning.py`** (`SessionStart`, matcher `compact`):
  after a context compaction, re-states the pinned governance
  constraints from a CODE constant (`_lib/pinned_constraints.py`) via
  `additionalContext`, so the summarizer cannot evict them. Kill switch:
  `CEO_CONSTRAINT_PINNING=0`.
- **`check_ledger_checkpoint.py`** (`PreToolUse`, matcher `Bash`): on the
  FIRST `git commit` of a Bash call (staging done in earlier tool calls)
  that lands plan-scoped work, reports whether that plan's `LEDGER.md` is
  in the same commit. Scope is derived MECHANICALLY from the paths staged
  (and, under `-a`, the tracked modifications present) at the moment the
  hook fires, BEFORE the command runs: `git add x && git commit` on a
  clean index is `skipped`, a mutation made earlier in the same call is
  not seen, and a second commit in the same call is not inspected (signed
  condition 77 of rc.1). No branch in the module returns a decision —
  there is no deny arm to disarm. Kill switches:
  `CEO_LEDGER_CHECKPOINT=0`, `CEO_SOTA_DISABLE=1` (`b07be9b`, `bc82651`).
- **`session_memory_delta_observed`** at `SessionEnd` records whether the
  project's memory directory saw activity inside this session's time window
  (stat-only: no memory content is read or logged). The directory is shared
  by every session of the project and a stat carries no author, so a
  concurrent session's write counts too: `written` is window activity, never
  proof that THIS session wrote memory. The window opens at the whole second
  after the recorded session start, so a write inside that first second is
  not counted (signed condition 20 of rc.1).
- **Audit-log SPEC v2.55 → v2.60**, additive as always
  (`SPEC/v1/audit-log.schema.md`); the known-action set is 331 entries.
- **The honest part.** ADR-153's original continuity design shipped in an
  earlier train and delivered NOTHING: the real autocompact fired both
  hooks and produced `snapshot_outcome=scratchpad_unavailable`,
  `plan_id=unknown`, because plan resolution required an event from the
  session's own history — 2 such events in 12,515 log lines. The rebuilt
  version falls back to a SESSION-scoped snapshot when no plan resolves
  (the plan id itself still comes from the audit history) and carries a
  separate ledger INDEX derived from the last commit's paths — a pointer,
  not a copy. Related
  measurement that corrects a number this project published: the context
  floor re-paid after a compaction was measured at **97,292 tokens** at a
  real compaction boundary (independent cold control: 97,097), roughly
  twice the ~45-55k this repository previously claimed, and it is not a
  constant — a 41-sample series spreads 51.7% around its mean.

### Added — the CI template we deliver is now actually EXECUTED in the smoke test (PLAN-183, `6160578`)

- `scripts/tests/smoke-install.sh` activates the delivered
  `validate.yml.template` in a throwaway target and runs its steps in
  order, one `bash -eo pipefail` per step, stopping at the first red. Any
  workflow shape outside the frozen subset is a parse FAILURE, never a
  vacuous green. Runs on Linux with `CI=true` or
  `CEO_SMOKE_EXECUTE_CI=1`; elsewhere it lists the steps with a note.
- **The delivered template changed accordingly:** it is SHA-pinned
  (`actions/checkout`), honors a `CEO_SOTA_DISABLE=1` repository variable
  as a kill switch, raises its own timeout 5 → 15 minutes, installs PyYAML
  in CI when it is absent and FAILS the YAML catalog syntax check if no
  parser can be had (a syntax gate that skips silently is a gate that
  fails open; a slim offline runner therefore goes red, by design), and
  verifies the SHA-256 of the actionlint release asset before running it.
  It ships INERT with a `.template` suffix; activation is still an
  explicit `mv -n` you perform.

### Added — `claude-fable-5-1` in the model allowlist (`ab56e76`)

- `claude-fable-5-1` joins `availableModels` in `.claude/settings.json`
  and in the maintainer/base settings template (the advisory `user`
  profile deliberately carries no `availableModels`). Adopting a new model is
  deliberately never automatic: the VETO floor, the pins and the agent
  definitions stay Owner-signed by design (ADR-149 remains the single
  source for the model catalog).

### Fixed — seven VETO-bearing skills were demoted to name-only (`b7dad83`)

- `kill-switches`, `latency-budgets`, `equity-research`,
  `financial-correctness-and-math`, `financial-display`,
  `prediction-markets` and `trading-execution` were listed under
  `skillOverrides` as `name-only`, which withholds their body from the
  agent — including from the veto paths that are supposed to read them.
  All seven are undemoted in BOTH settings profiles on a FRESH install.
  An existing v1.3.0 installation keeps its own `skillOverrides` on
  upgrade (the upgrader preserves settings outside the enumerated
  additive migrations), so the undemotion reaches upgraded adopters
  only through a baseline-aware migration — a signed condition of rc.1
  (lands before GA). Four skills with no
  veto role (`cpp-testing`, `frontend-slides`, `prisma-patterns`,
  `ui-demo`) were added to the name-only list in their place — in the
  framework checkout's own live settings only: the delivered templates
  (`templates/settings/`) do not carry the four names. The undemotion
  itself DOES reach a fresh install (the seven names are absent from
  `skillOverrides` in both files); only an upgraded adopter keeps the old
  list until the baseline-aware migration.

### Fixed — the test suite was writing into the live HMAC chain (`2ae16d2`, `7a618c9`, `3d16070`)

- Measured: 2,356 `policy_*` events over 7 days — 19 processes × exactly
  124 — all with an empty `session_id`, 79% of the live segment. The
  emitter was `python3 -m pytest --collect-only`, run before every
  commit: the isolation layer popped the environment carrier at import
  time but redirected the log in a session FIXTURE, and `--collect-only`
  runs the first without the second. Cured in two layers, with a positive
  control and an anti-rot guard. Adopter-relevant only if you run this
  repository's own suite; recorded here because it corrupted the
  integrity signal this project sells.

### Fixed — `git log --since=<N>h` was a silent misparse (`9af6114`)

- Two instruments passed an hour-suffixed window to `git log --since`,
  which git's approxidate parser DISCARDS — collapsing the window
  silently rather than erroring. Both sites cured, twelve regression
  tests added.

### Changed — documentation

- `docs/UPGRADE-PROCEDURE.md` said `--pin` was "durable; subsequent
  `upgrade.sh` calls honor the pinned version". **It is not, and never
  was.** The pin checks the source tree out at the ref, runs the upgrade,
  and restores the original branch on exit; `--profile`, `--stack` and the
  recorded harness are replayed from the install-state (signed condition
  82). The document is
  corrected to match `VERSIONING.md`, which was right all along.
- New: `docs/CONTEXT-CONTINUITY-GUIDE.md`, `docs/task-classifier-2b.md`,
  an expanded `docs/threat-model.md`, and
  `docs/BUG-REPORT-adopter-harness-config-replay-fixtures.pt-BR.md`. These are
  framework-repo documents; `install.sh` delivers only the two `docs/`
  files named in `scripts/delivery-routes.tsv`.

### Governance

- ADRs 191 → **197** by NUMBER; 198 ADR files on disk (amendments are
  separate files counted by `verify-counts.sh`): ADR-192 gate-scripts
  checksum manifest, ADR-193 break-glass repo kill switches, ADR-194
  delivery-route resolution, ADR-195 work-boundary persistence, ADR-196
  installer write confinement, ADR-197 user-profile derivation.
- Counts moved: hook scripts on disk 57 → **59**; wired in
  `settings.json` 46 → **48** (48 → **50** event registrations); shared
  `_lib` modules 68 → **71**; ADR files 192 → **198**; collected test
  cases ~14,000 → **~15,400**. Unchanged since v1.3.0: **166 skills**
  (42 core + 8 frontend + 116 domain), **27 slash commands**, **32
  `SPEC/v1` files** (28 `*.schema.md`), **4 TLA+ specifications**.
- Commit count since v1.3.0: `git rev-list --count v1.3.0..<tag>` at the
  tagged commit (a number written here ages with every candidate).
  Canonical changes landed as Owner-GPG-signed ceremonies with per-phase
  sentinels and closed scopes.

### Known issues

Carried into 1.4.0 deliberately, each with its state named:

- **The `PROTOCOL.md` pointer delivered to an adopter is absolute**, not
  relative — it embeds the maintainer's framework path. Found in field
  testing at S315, still OPEN; the cure is PLAN-183 W1 and did not make
  this release.
- **The CI hook-latency gate is sensitive to a slow runner.** The probe
  measures spawn cost and cannot see runner contention: the same hooks at
  the same SHA measured 77 ms locally and 209-435 ms in CI, failing three
  afternoon runs and passing at night. A RELATIVE gate
  (`hook_p50 ≤ K × ref_p50`) is landed in phase 1 ADVISORY only
  (`4bd7def`); making it the enforcing gate is decided but not shipped.
- **The pair-rail is inert until you install Codex separately**, and it
  is a same-class reviewer — unchanged from v1.3.0, restated because it
  is the most misread property of this framework.
- **The ownership e2e ends 62 green / 3 red by design**
  (`OWN-0016`/`0024`/`0027`, causes in ADR-190). An all-green run means
  the decision table changed — stop and find out why.
- **Fence-shadow variant 5 in the release verdict gate** stays outside
  the threat model (the signer is the Owner); the fixed-format envelope
  that closes it is named for a future release.
- **The formal model is still not in CI.** The TLA+ specifications under
  `docs/formal-verification/` are specifications, not a verified claim.
- **`upgrade.sh` under `--pin <ref>` where `<ref>` predates `aaf32c7`**
  finds no route table in the pinned tree; the running upgrader now
  copies the table's bytes out of its own checkout first, so the pinned
  upgrade still delivers.

## [1.3.0] - 2026-08-04

Night-mode + doctrine + release-engineering train (PLAN-162/165
ceremony 2; PLAN-166/167/168 release-hold closure and install/upgrade
ownership; PLAN-177 GA re-pass cures; PLAN-178 spawn acceptance
contract v2, native cost cross-check and vacuity lint). The headline
feature is night-mode; one cross-rail security P0
closed, one published-contract conflict settled by ADR instead of by
silence, and the install/upgrade ownership decision collapsed into a
single audited function. As always: governance and auditability — no
speed claim.

### Added — night-mode: Owner-invoked autonomy posture toggle (PLAN-165, ADR-185)

- **`/night-mode` command + `.claude/scripts/night-mode.py`**: the Owner
  flips the per-machine autonomy posture (`permissions.defaultMode`
  overlay in the gitignored `.claude/settings.local.json`) with
  next-session semantics — "arm before sleep, autonomous overnight
  session, disarm in the morning". The tracked `settings.json` posture is
  never touched; templates and adopter defaults are unchanged.
- **Arming autonomy is a HUMAN action** (Owner-ratified OQ1-redo): the
  toggle refuses under CI; the writer script carries a self-path guard
  and the Bash rail carries a best-effort invocation matcher (defense in
  depth — the real boundary is the script's own guard plus the session
  deny surface, and the docs say exactly that, not more).
- **Audited**: every `on`/`off`/refusal emits `night_mode_toggled` into
  the HMAC chain (schema row in `SPEC/v1/audit-log.schema.md`); live-fire
  proven — toggle events and a negative-control `refused` line verified
  on-chain before this release.
- `bypassPermissions` was deliberately CUT from the design: it would trip
  the `settings_tamper_tripwires` boot check by construction. The honest
  escape valve stays `claude --permission-mode bypassPermissions` (one
  session, explicit, ephemeral).

### Security — sentinel unlock now requires provenance inside git worktrees (ADR-119 Invariant 5)

- **Adopter-visible tightening of the recovery contract** (SPEC/v1
  `sentinel-format.schema.md` §unlock): inside a git work tree, the
  `CEO_SENTINEL_UNLOCK` + `CEO_SENTINEL_UNLOCK_ACK` pair alone no longer
  grants — you must also provide provenance via
  `CEO_SESSION_ANCHOR_SHA=$(git rev-parse HEAD)` (captured BEFORE the
  session) **or** `CEO_SENTINEL_UNLOCK_SHA256=<sha256 of approved.md>`.
  The block message teaches both forms when a window is armed. This
  closes a real escalation: during an unlock window the agent could
  author its own `approved.md` (a path guarded by neither rail) and
  self-grant. Classified MINOR under this repo's published policy
  (`VERSIONING.md` §MINOR: "a new trust boundary adopters must
  understand"); MAJOR is reserved for schema-consumer breakage
  (removed/renamed fields, dropped event types), which this is not.
  **Action needed only if you scripted the 2-var unlock inside a git
  worktree** — add one of the two exports above.

### Fixed — case-fold bypass on canonical AND kernel rails (PLAN-162 W2, P0)

- On case-insensitive filesystems (APFS default), `fnmatch.fnmatchcase`
  let `.claude/settings.JSON` / `.claude/hooks/_lib/audit_emit.PY` slip
  past BOTH guard rails while the write lands on the real file. Both
  rails now case-fold before matching. Found first-hand during the
  PLAN-162 debate; verified by red-first tests on both rails.

### Changed — hook-deadline doctrine settled by ADR-186 (fail-CLOSED)

- The canonical-edit matcher now enforces a **per-invocation wall
  deadline that fails CLOSED** (`_HOOK_WALL_BUDGET_S`, injectable clock),
  replacing the unbounded sentinel sweep — and the published
  fail-open-on-infrastructure contract in `CLAUDE.md` §4 / `AGENTS.md` §1
  now names this exception explicitly: a timeout *inside the matcher* is
  an incomplete verification, not infrastructure. Recovery route:
  provenance-pinned unlock (`CEO_SENTINEL_UNLOCK` +
  `CEO_SESSION_ANCHOR_SHA` or `CEO_SENTINEL_UNLOCK_SHA256`).
- Sentinel-verification **cache partitioned** (signature validity no
  longer keyed per-target). This closes the measured saturation window —
  4.16 s consumed of a 5 s budget at 20 candidate paths — that made the
  old fail-open deadline attacker-reachable by planting sentinels
  (ADR-164-AMEND-1). A correctness/security fix; no throughput claim.
- Deadline blocks are **countable in the chain**: the veto breadcrumb
  carries `reason_code=canonical_edit_hook_fault` instead of
  masquerading as a missing-sentinel block.

### Changed — pair-rail recalibrated 120/150 → 180/210 (ADR-110-AMEND-2)

- Internal cap 180 s under a 210 s registration, ratified only after a
  live substrate probe proved the harness honors a 210 s hook
  registration (evidence committed:
  `.claude/plans/PLAN-162/probe-210s-GO-EVIDENCE.md`).
- `pair_rail_case` events now carry `timeout_ms` (int — a float in an
  HMAC-covered field silently drops the whole event), and the §3
  escalation trigger is the **censoring rate**, not p95 (the p95 of a
  censored sample is inestimable).

### Fixed — scheduled workflows that were red without surfacing in push CI

- **mutation-gate**: kill-rate now parsed from mutmut's junitxml (the old
  regex parser NEVER reported a rate — historical "96.7%" came from an
  inflated formula), artifact redaction inlined and fail-closed, and the
  `actions/checkout` SHA re-pinned (which also cures the
  supply-chain-watch drift red present since 2026-07-20).
- **tournament**: stderr banner no longer merged into the cost-projection
  JSON (`2>&1` unmerge).
- **reality-ledger**: required labels created idempotently
  (`gh label create --force`) so fresh installs cannot red on a missing
  label.
- **ceo-boot**: 24th Tier-S check `scheduled_workflows_red` closes the
  "scheduled gate red for weeks, invisible" class — with cure-detection
  (a red scheduled lane whose newest completed run across ALL trigger
  events is green reports `cured_pending_cron`, not red).

### Changed — install/upgrade semantics (PLAN-166/167/168)

Adopter-visible behavior of `scripts/install.sh` / `scripts/upgrade.sh`
changed in this release — what a v1.2.0 adopter notices when upgrading:

- **Ownership is ONE decision, not a cascade (ADR-190).** On upgrade,
  whether the framework owns `PROTOCOL.md`, `SPEC/v1` or
  `.claude/.framework-version` is answered by a single pure decision
  function (`_ownership_verdict()` in
  `scripts/_framework_manifest_set.sh`) over the observed ownership
  dimensions — execution-state faults (e.g. a failed backup) stay
  caller-side by design; `upgrade.sh` observes → calls → executes
  instead of deciding locally. Fresh installs sit BEFORE the decision:
  they record the registered delivery (the ADR-155 baseline manifest)
  that upgrade's observations later read. Contract:
  `docs/ownership-decision-table.md`.
- **`SPEC/v1` is a forced route on upgrade.** A framework-owned
  `SPEC/v1` is backed up to `.claude.bak/<timestamp>/SPEC/v1` and
  replaced wholesale — a local edit is a fork of the published
  compliance contract, not a customization. A pre-existing `SPEC/v1`
  with no delivery record is byte-compared against the pristine SPECs
  shipped at v1.2.0 and earlier: a match refreshes it, anything else is
  preserved in place with a named WARNING (ADR-155-AMEND-1). Skipped on
  `--ceremony user` installs.
- **`.claude/.framework-version` is the version marker.** Written on
  install and refreshed on framework-owned, unskipped upgrades;
  `check-framework-updates.sh` and forensic triage read it MARKER-FIRST
  — a well-formed marker validated against its delivery record is the
  signal; an absent, unrecorded, malformed or integrity-failed marker
  falls back to root `VERSION`. The adopter repo's root `VERSION` file
  is deliberately never touched by upgrade — after a framework-owned
  upgrade, the validated marker (not root `VERSION`) is what carries
  the installed framework version.
- **`PROTOCOL.md` pointer has ONE generator.** Install and upgrade
  render the pointer through the same shared generator (byte-identical
  output on both paths); a degraded pointer body is cured with a backup
  and adopter edits are preserved. Skipped on `--ceremony user`
  installs, which never create root files.

### Fixed — release-verdict readers share ONE fail-closed grammar (PLAN-177)

The GA re-pass over rc.3 ended NO-GO; the cures landed inside this
train (rc.4) instead of being deferred:

- **Both release decision gates** — the server-side
  `validate-pair-rail-verdict.py` (step 15) and the local
  `_release_tag_guard.py` (all-modes enforcement) — now parse the
  signed verdict with the same strict ASCII/YAML grammar: indented
  continuations of a scalar, comments glued to the value, Unicode
  whitespace stuck to the token (`GO<U+00A0>` is NOT `GO`) and
  separator-less keys (`verdict:GO`) are each a NAMED rejection, never
  a silent normalization into the authorizing token. Proven by
  cross-reader probe fixtures that run the two rails on every key
  shape and require identical answers.
- **Gitignore delivery is symlink-safe**: the three writers refuse to
  follow a symlinked `.gitignore`/`.claude/.gitignore`, dry-run
  previews print what WOULD be appended (never "asserted clean" over
  debris), and the root-gitignore symlink guard is part of the
  baseline enumeration.
- **plans/ schema docs refresh is hash-gated on upgrade**: only a
  byte-pristine copy of a KNOWN prior framework generation of
  `PLAN-SCHEMA.md`/`DEBATE-SCHEMA.md` is replaced (with backup);
  an adopter-modified schema is PRESERVED loudly. Closes the F3 STALE
  signature the parity e2e flagged. The refresh writes over the
  existing inode (`cp`, not an atomic rename), so a hard link to that
  file outside the target changes with it — signed condition of rc.1:
  no hard links or symlinks anywhere under `.claude/`, `docs/`, `.github/`
  and `SPEC/` before upgrading (two `find` commands in
  `docs/UPGRADE-PROCEDURE.md`; the hook, script, command, skill and
  agent deliveries copy through a link the same way). A `--ceremony
  user` repository upgrades with `--no-settings-migrate` (signed
  condition of rc.1: the leaf migration adds three maintainer-profile
  keys to the advisory profile otherwise).
- **Pre-state ceremony migration fails safe to `user`** and only an
  EXPLICIT `--ceremony` flag / env / recorded state persists into the
  synthesized install-state — the fail-safe inference itself is never
  persisted.
- **npm honesty**: `npm/INTEGRITY.md` names the packlist exceptions
  that actually ship; `SBOM.md`, `install-npm.sh` and `INSTALL.md`
  claims re-verified against behavior.

### Added — spawn acceptance contract v2 (PLAN-178 Lote B, ADR-191)

- **FILE ASSIGNMENT grammar with taint semantics** in
  `check_agent_spawn.py`: every named spawn declares `- CAN edit:
  <concrete paths>` or `- CAN edit: NONE-READ-ONLY`; globs, Unicode
  whitespace, control characters or non-whitelisted list lines taint
  the whole declaration. Advisory-first: omission is VISIBLE
  (`spawn_file_assignment_recorded`, `path_count=0`) and the enforce
  flip stays a future ceremony gated on the measure-first window.
- **Fenced + capped inter-agent ingest** in the four shipped Workflow
  skills (byte-identical COMMON block): PROMPT DEFENSE ≥6, explicit
  FILE ASSIGNMENT, anti-spoof fencing with a 24000-char cap whose
  truncation poisons the owning dimension — plus a pre-dispatch
  validator of the reduced ADR-191 grammar in the workflow scripts
  themselves (the Workflow rail does not pass through the spawn hook;
  honest limitation recorded in ADR-191 §4).
- **Shared-memory `query()` returns are fenced**
  (`_lib/memory_shared.py`, ADR-089-AMEND-1) with a derivable
  SEC-P0-02 reopen trigger.
- **Multi-plan budget cap cure** (`check_budget.py`): the previously
  INERT cap (early-allow with ≥2 active plans) now resolves the
  active plan by an explicit tie-break and emits a breadcrumb instead
  of silently allowing.
- **Native cost cross-check in `/agent-budget`** (PLAN-178 W1.2):
  a read-only, fail-soft, zero-network puller reads Claude Code's own
  per-subagent usage records and `budget-summary.py` joins them
  against the audit-log estimate (exact match on session + description
  hash, ordinal fallback; unmatched residue VISIBLE on both sides;
  cache-billable split priced correctly). Opt-in via `--native` /
  `CEO_BUDGET_NATIVE=1` — the default output stays byte-identical —
  with a `CEO_NATIVE_COST_DISABLE` kill-switch. Doctrine recorded in
  the command doc: a cross-check, never an authority swap.
- **Vacuous-check lint + a live cure** (PLAN-178 Lote A):
  `check-vacuous-checks.py` fails any boot check whose reachable local
  returns can never go red (structured head-only waiver:
  `# CEO-INFORMATIONAL-ONLY: <reason>`), with positive controls on the
  lint itself. The known-vacuous `check_tier_a_spec_version_drift` is
  CURED for real: framework-vs-SPEC major comparison with a reachable
  red, ownership-aware source and ADR-155-AMEND-1 §5 provenance
  (no provenance ⇒ yellow "suspected", never red).

### Governance

- ADRs 184 → **191** by NUMBER; 192 ADR files on disk — amendments
  (e.g. ADR-089-AMEND-1) are separate files counted by
  verify-counts.sh (ADR-185 night-mode; ADR-186 hook-deadline policy;
  ADR-110-AMEND-2; ADR-164-AMEND-1; ADR-155-AMEND-1 delivery-record
  ownership; ADR-190 ownership-decision-table contract; ADR-191 spawn
  acceptance contract v2; ADR-089-AMEND-1 shared-memory fence). Slash
  commands 26 → **27**
  (`/night-mode`). All ceremony phases landed as separable
  Owner-GPG-signed commits with per-phase sentinels and closed scopes —
  PLAN-178 Lote B under its own sentinel (SENT-PLAN178-LOTEB) and a
  44-round cross-model rail.

## [1.2.0] - 2026-07-30

Substrate + rail release (PLAN-160/161/163/164). The headline is not a new
feature: it is that the cross-model pair-rail **completed a live in-hook
review for the first time in the audit log's history**. Everything else is
the substrate work that made that possible. As always: governance and
auditability — no speed claim.

### Fixed — the pair-rail was 100% fail-open (PLAN-164, ADR-110-AMEND-1)

- **`CEO_PAIR_RAIL_TIMEOUT_S` internal default 30 → 120 s**, and the
  `check_pair_rail.py` PreToolUse **registration timeout 60 → 150 s** in both
  kernel `.claude/settings.json` and `templates/settings/settings.base.json`
  (parity enforced). The 30 s value was an implementation literal, never a
  decided one, and it sat structurally *below* the latency of a real Codex
  verdict: **every one of the 12 `pair_rail_case` events in the entire life of
  the audit log was case F / TIMEOUT.** The rail had never once completed a
  live review. Measured calibration (N=9, same machine): p95 ≈ 75 s, which
  crosses the measurement protocol's own 70 s escalation threshold and selects
  120/150 rather than the 100/120 first draft.
- **The layering invariant is now tested, not assumed**
  (`test_pair_rail_timeout_invariant.py`): kernel registration == template
  registration, and `registration >= internal + 30`. A unilateral flip of any
  of the three literals now goes red in the suite and in the pack preflight.
- **`statusMessage` on the registration** — a session held by a synchronous
  cross-model review shows "may take up to ~3 min" instead of appearing
  frozen. (Shipped in 1.2.0 as "may take 1-2 min"; the wording tracks the
  budget and was retuned by ADR-110-AMEND-2 when it moved to 180/210 s.)
- **From zero completed reviews to ten.** The log now holds 10 healthy cases
  (7 × case A, 3 × case B) alongside 14 case F. Median verdict latency 70.5 s;
  observed maximum 120.0 s.
- **The §3 recalibration trigger (≥10 healthy cases) is met, and it points
  upward — with the caveat it deserves.** No sample actually exceeded 120 s;
  the p95 figure of 122.2 s is an *interpolation above the observed maximum*
  on exactly ten points, not a measured latency. What is solid: the three
  slowest healthy reviews (115 / 115 / 120 s) leave 0–5 s of headroom, and the
  trigger's own query is **right-censored by construction** — any review slower
  than the budget becomes a case F and never enters the healthy set, so this
  p95 can only ever under-report the true distribution. An upward
  `ADR-110-AMEND-2` is therefore indicated, but the new pair is deliberately
  **not** chosen here: §3 requires a new amendment via ceremony, and the number
  belongs to the C5 measurement protocol plus a debate, not to a changelog
  line.

### Changed — substrate uplift to Claude Code 2.1.220 + Claude 5 (PLAN-163, ADR-181)

- Model registry refreshed to the **Claude 5 family**. Adopter installs are
  migrated in place by the landed `scripts/upgrade.sh` — including the
  pair-rail **registration-timeout cap 60 → 150 s** (the settings half of
  ADR-110-AMEND-1; applied only when the adopter's value is still the old
  default, so an operator-chosen value is never clobbered).
- **Dated pricing is now event-date-aware** rather than resolved against wall
  clock, so a historical audit event prices at the rate in force when it
  happened.
- `opus-4-8-fast` recognized; stale-model scan updated.

### Added — Codex payload pin enforcement (PLAN-163, ADR-182)

- **Verify-then-invoke.** The previous SHA pin attested the *launcher*, not the
  payload it executed — a pin that proved the wrong artifact. The pin now
  verifies the payload before invocation and fails closed.

### Changed — canonical-edit gate hardening (PLAN-160/161, ADR-164, ADR-165)

- Multi-candidate sentinel resolution is **fail-closed**, with a shared
  predicate and dual-anchor validation; `resolve_anchor` is suffix-newest and
  revert-aware. Three redundant `Write()` deny twins removed.

### Added — upgrade + liveness instrumentation (PLAN-161)

- Red-first **upgrade oracles** (dry-run identity, exclusion predicate, opt-in
  purge) wired into the `smoke-install` CI job — an adopter upgrade that
  silently changes behavior now fails a gate instead of shipping.
- **Pair-rail liveness telemetry**: two typed audit actions, so "the rail is
  fail-open" is a queryable fact rather than an inference.
- Perf-gate backoff with a probe-gated third attempt (runner-load flake).
- `ADR-183` — directory-added notification events.

### Fixed — `disableAutoMode` silently disabled every hook

- The value was a boolean; Claude Code 2.1.220's settings schema rejects it and
  **skips the entire `settings.json`** — a session would boot with none of the
  48 hook registrations, governance fully absent, and no error surfaced. Now
  the string `"disable"`. Found by live-fire on the first boot after the
  substrate pack, not by any fixture.

### Counts (reproducible via `verify-counts.sh`)

166 skills (42 core / 8 frontend / 116 domain) · 26 slash commands · **184
ADRs** (178 → 184) · 57 hook scripts on disk, 46 wired into `settings.json`
across 48 event registrations · 68 `_lib` modules.

---

## [1.1.0] - 2026-07-13

Feature release (PLAN-153/154/155/156): two new host harnesses (Codex CLI
and Grok Build run the same enforcement hooks), a cross-vendor audit
council, a gated learning loop, and a skill-catalog uplift 151 → 166. As
always: governance and auditability — no speed claim.

### Added — multi-harness (PLAN-155, PLAN-156)
- **`--harness codex`** (PLAN-155, ADR-161): the installer emits a Codex
  bundle (`.codex/hooks.json`, `.codex/rules/ceo.rules`, operator
  `AGENTS.md`) that runs the **same** hooks under `CEO_HOOK_ADAPTER=codex`.
  Per-rail truth (verified against codex-cli 0.139.0): canonical-edit,
  bash-safety, plan-lifecycle, kernel-deny, config, and kill-switch are
  ENFORCED at edit time; audit chain ENFORCED but completeness-bounded;
  pair-rail inverted (Codex operates, `claude -p` reviews) and PARTIAL;
  spawn governance ADVISORY. Installer ends with an
  `ARMED / NOT-ARMED-(untrusted) / BROKEN` arming check.
- **`--harness grok`** (PLAN-156, ADR-162): single-surface install — Grok
  Build reads the shipped `.claude/settings.json` directly (no second
  bundle; arming both surfaces would double-fire every hook). Prevention
  rails ENFORCED via grok's `pre_tool_use`; pair-rail is Stop-passive, so
  a **git pre-push review gate is the teeth**. Verified against grok
  0.2.93 (exact pin). Emits `AGENTS.md` + `.grok/*.example` config.
- New docs: [`docs/adapters.md`](docs/adapters.md) +
  [`docs/provider_capability_matrix.md`](docs/provider_capability_matrix.md)
  (per-rail, per-harness enforcement matrix — what is actually enforced
  vs advisory under each harness).
- Audit-chain action registry extended for both harnesses (314 → 319
  registered actions, tamper-mirror coverage included).
- codex-cli version pin bumped to `<0.145.0` (GPT-5.6 line) in
  `codex-cli-pin.txt`; release gate hard-blocks verdicts from unpinned
  codex binaries.

### Added — cross-vendor audit council (PLAN-156)
- **`/council <scope>`** — read-only, three-vendor audit (Claude in-harness
  agents + Codex `exec --sandbox read-only` + Grok `-p --sandbox council`)
  with vendor-attributed verdicts, adversarial re-verification, and
  explicit fail-loud quorum degradation (an unavailable lane reports
  STATUS: unavailable, never a silent substitution). Every external-lane
  prompt passes the ADR-114 egress redactor; ADVISORY evidence only;
  operator/local only — never CI.

### Added — gated learning loop (PLAN-154)
- Hooks accrue **lesson candidates** from live sessions; nothing renders
  or persists as advice until explicitly approved: **`/lesson-review`**
  (approve / reject / undo, HMAC-recorded), **`/lesson-evolve`** (cluster
  approved lessons into SP-NNN skill-patch drafts for the existing
  /skill-review ceremony), and an opt-in boot surface
  (`CEO_LEARNING_BOOT_LESSONS=1`) that renders ≤3 verified one-liners as
  fenced untrusted data — verify-before-render against the HMAC chain,
  fail-closed drops, count-only integrity notes. Default OFF
  (`CEO_SOTA_DISABLE=1` master kill precedence).

### Added — skill catalog + commands (PLAN-153)
- Skill catalog **151 → 166**: 15 imported domain skills land through a
  new import gate with a NOTICE provenance ledger; 20+ SP-NNN adaptation
  patches promoted shadow → live through the new **`/skill-review`**
  ceremony (staged shadow-soak, Owner-waivable).
- New commands: **`/skill-health`** (per-skill telemetry from the HMAC
  audit log — invocations, failure-proxy clusters, dead-skill flagging)
  and **`/context-budget`** (static context-overhead audit of the skill
  catalog + governance surface).
- `COMMAND→SKILL→HOOK` map (`docs/COMMAND-SKILL-HOOK-MAP.md`) with a
  validate.yml drift gate — regenerate via
  `.claude/scripts/gen-command-skill-hook-map.py --write`.

### Added — security gates (PLAN-153 Wave E)
- Harness-config gate (tamper tripwires over `settings.json` hook
  registrations), citation gate, spawn prompt-defense template, deny
  baseline, and supply-chain watch — all wired into `/ceo-boot` +
  validate.yml.

### Added — installer / release lifecycle (PLAN-153 Wave B)
- `doctor.sh` + repair mode, install-state manifest + replay,
  install-profiles manifest, deterministic plugin-manifest regeneration
  (`build-plugin.py --check` CI drift gate), release idempotency +
  release-notes template. Fixes the two latent v1.0.x release.yml bugs
  (RC-version-mismatch; hardcoded release notes).

### Changed
- `/ceo-boot` extended with liveness checks (fail-open rail silence is
  now surfaced, not mistaken for health) and the harness-config gate.
- README / plugin description / manifests: counts reconciled to disk
  truth (166 skills, 55 hook scripts, 68 `_lib` modules, 26 commands,
  178 ADRs).

## [1.0.1] - 2026-07-02

v1.0.1 hardening sweep (PLAN-152) — remediation of the 2026-07-01 post-release
audit fan-out (run `wf_071ef6c5`: 41 confirmed findings) + v1.0.1 backlog.
No new features; security fixes, CI truth, tarball hygiene, model modernization.

### Security (P0 — shipped-broken in v1.0.0)
- **check_pair_rail PreToolUse gate was FAIL-OPEN since v1.0.0** — the
  settings.json registration passed a relative path the shim could not
  resolve (`hook not found` + `{}` allow). Fixed to the basename +
  `"$CLAUDE_PROJECT_DIR"` form used by the other 43 registrations
  (governance-01).
- **bash-safety destructive-command guard fail-opened on quoted metachars**
  (`rm -rf ~ ";"` passed). Fixed with a quote-aware subcommand splitter
  (char-walk honoring quotes/escapes/adjacent operators); 16-case
  adversarial battery; kill-switch `CEO_BASH_RAWSCAN=0` (error-handling-01).
- **_python-hook.sh interpreter-cache TOCTOU/symlink hardening** — cache dir
  must be owner-held, non-symlink, not group/world-writable; symlink
  rejected before chmod (security-01).
- Match.snippet in `_lib/pii_patterns.py` now honors its "redacted /
  preview-safe" contract: matched span masked AND surrounding context
  re-swept by the module's own family+entropy redaction (adjacent-secret
  leak found by the Codex pair-rail) (error-handling-02).
- **`CEO_UNICODE_HARDBLOCK=1` Read scan streams the whole file** — the
  economics-02 capped re-read silently fail-opened the opt-in fail-closed
  guard for invisible-unicode payloads past 1 MiB. Found by the Codex
  release re-pass (RC window, R1 REJECT); the armed path now scans in
  cap-sized chunks (per-code-point detection — chunking exact); flag-off
  hot path unchanged (PLAN-152 round-2).

### CI / tests
- **~1,600 formerly CI-dark tests wired into validate.yml** as explicit
  paths (tests/unit + 8 roots: _lib/tests, swarm, replay, federation,
  mcp-server, detectors, predict-budget, forensic, synthetic), two-pass
  serial split preserved (tests-01/02/07). 13 root test files (incl. 3
  SECURITY suites) relocated to tests/unit/. Stale tests exposed by the
  wiring fixed (codex token telemetry ×2, predict-budget spool-write race).
- env-hygiene burndown: 55 violations (swarm 43 + mcp-server 12) refactored
  to TestEnvContext; the 3 cleaned roots added to the enforcing scan tuple
  (tests-03).
- coverage.yml: stale "78%" floor claims reconciled with the real enforcing
  `--fail-under=67` (tests-04); dead doc refs corrected (tests-05: ADR-042
  now cites mcp-smoke.yml).
- validate-governance.sh: new orphan PLAN-<NNN>/ dir guard (PLAN-SCHEMA §1
  matching-plan-file rule now enforced + seed test) (governance-05).

### npm tarball (backlog #2)
- **Selective staging replaces blanket `cp -r .claude npm/`** in
  npm-publish.yml + install-npm.sh (rsync excludes: **/tests/, **/fixtures/,
  red-team-corpus, eval, numbered plan trees, _lib/testing.py +
  test_isolation.py; keeps plans schemas/examples + policies/fixtures).
  v1.0.0 shipped 2373 files incl. 1029 test files; v1.0.1 ships 1158 with
  zero FORBIDDEN framework-internal artifacts (the two deliberate
  carve-outs — `.claude/policies/fixtures/` and the adopter-facing
  `templates/oidc-proxy/tests/` — keep shipping by contract) (tarball-01).
- **Packlist gate** (`npm pack --dry-run --json` + forbidden-pattern assert)
  added to validate.yml (PR/push) and npm-publish.yml (pre-publish)
  (tarball-02). npm/.npmignore comments corrected (entries are INERT under
  the package.json `files` whitelist — staging excludes are the rail).
- npm-publish.yml false "OIDC trusted publisher" header corrected (auth is
  a granular token + Sigstore --provenance; Trusted Publishing tracked for
  v1.0.2; NPM_TOKEN expires ~2026-09-28).

### Hot-path economics
- check_output_secrets: deprecated aggregate sidecar emit removed (halves
  HMAC appends + filelocks per scan hit) (economics-01).
- check_read_injection: A2 unicode guard now gated on CEO_UNICODE_HARDBLOCK
  BEFORE any work + re-read capped at 1 MiB (was: unconditional 2nd
  uncapped full-file read on EVERY Read) (economics-02).
- anti-CEO-overhead 5-min window now per-SESSION (parallel sanctioned
  fan-outs no longer pool one budget) + stale-window GC (economics-03).

### Workflow robustness (backlog #4)
- audit-fanout / nightly-hygiene / eval-baseline-n20 null-guarded against
  agent() resolving null on terminal API error (the wf_071ef6c5 crash
  class); audit-fanout gains a deterministic mechanical verdict — CLEAN is
  inadmissible over unaudited dimensions (error-handling-03).

### Model / substrate (backlog #3)
- **ADR-157**: Sonnet 5 (`claude-sonnet-5`) added to the closed MODEL_ID
  enum — member only; M-tier routing default UNCHANGED and pinned by
  regression tests (routing flip = own future plan per OQ1).
- model-deprecations ledger: fast-mode fuses added (claude-opus-4-6-fast
  retired 2026-06-29 silent fallback; claude-opus-4-7-fast retires
  2026-07-24 hard error).

### Docs / dead code
- Dead refs + stale counts fixed across GUIA-COMPLETO (EN/pt-BR), INSTALL,
  CTO-GUIDE, RELEASE, QUICKSTART, SBOM, TROUBLESHOOTING (EN/pt-BR),
  release-checklist, .coveragerc, performance-budgets (docs-01..08,
  dependencies-01, economics-04).
- PLAN-128 orphan dir resolved with a restored provenance plan file
  (dead-code-03); 7 shipped ceremony scripts moved to
  scripts/local/historical/ (dead-code-04); null-valued benchmark JSONL
  removed (dead-code-06); check-version-drift docstring corrected
  (dead-code-01); install-accelerators stale note fixed (dead-code-02).

### Deferred to v1.0.2 (on-disk pointers in PLAN-152)
- `_lib/tests` 128-site env-hygiene burndown; npm Trusted Publishing (OIDC);
  kernel-matcher expansion (governance-04/07); nested-subagent red-team
  corpus; PLAN-128 wave1 measurement tooling restore.

## [1.0.0] — 2026-06-29

First public release — the clean public baseline of **ceo-orchestration**.

Prior versions were private internal iterations and are intentionally not part of
this repository's history; v1.0.0 is the zero-history genesis of the public
project.

### Included
- **Plan → Debate → Execute** governance gating for L3+ changes, with vetoes and
  a three-strike rule (`PROTOCOL.md`).
- A **tamper-evident, HMAC-chained audit log** with chain verification.
- A **cross-LLM pair-rail**: a second model reviews canonical edits before they land.
- A **skill library** (151 skills: 42 core + 8 frontend + 101 domain).
- **Governance hooks** (Python, stdlib-only) wired through `.claude/settings.json`.
- **171 ADRs** and **22 slash commands**.

> **No speed claim.** Internal experiments found no general speedup over an
> optimized solo workflow — the value here is governance and auditability, not
> throughput.

---

[1.0.0]: https://github.com/Canhada-Labs/ceo-orchestration/releases/tag/v1.0.0
