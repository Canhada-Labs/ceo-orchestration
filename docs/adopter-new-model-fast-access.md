# Using a new Claude model before a framework release

> A per-machine route for adopters who want a newly released Claude model
> **today**, without waiting for the framework to adopt it in a release. It
> changes one per-machine file, `.claude/settings.local.json`. It does not
> change what the framework ships or what it enforces.

**Evidence and substrate.** The harness behaviour described here was checked
on **2026-09-22 and 2026-09-23 against Claude Code 2.1.280** (the darwin-arm64
build), on the **Anthropic API** (first-party login, no third-party provider
configured), from the 2.1.280 binary, the Claude Code docs as published on
2026-09-22 (the model-configuration, subagents, hooks and workflows pages
and the changelog re-read on 2026-09-23), and three sets of `claude -p`
probes run in throwaway directories around Claude Opus 5.5
(`claude-opus-5-5`, the newest model those days):

- **R1–R4** (model selection, 2026-09-22) read the model actually served from
  `modelUsage`. All four set `"enforceAvailableModels": true`: R2 and R3
  with the maintainer allowlist (the seven ids the maintainer template ships
  in v1.4.0 and v1.4.1-rc.1), R1 and R4 with a one-model allowlist. They ran
  without `--setting-sources`, so the operator's own user settings were in
  scope too (an `availableModels` list there would have been concatenated).
  No shipped template sets `enforceAvailableModels`. Per the Claude Code docs the
  key decides what the default resolves to wherever the default is reached:
  session startup, Default in `/model`, the `default` keyword in fallback
  chains, and the replacement for a selection the allowlist excludes. The
  admit function read in the 2.1.280 binary checks `availableModels` without
  consulting it.
- **E1–E8** (effort and `ultracode`) ran `claude -p --input-format
  stream-json --model claude-opus-5-5` and read the applied model, effort
  and `ultracode` from a `get_settings` control request; E6–E8 also read the
  effort level of every tool call (main session, subagent, workflow agents)
  from a PreToolUse hook. They excluded user settings (`--setting-sources project`).
- **2026-09-23 re-runs**, with user settings excluded (`--setting-sources
  project,local`): the recipe end to end, R4's merge, and the ConfigChange
  behaviour described [below](#use-the-model-key-not-anthropic_model).
- **2026-10-09 binary reads, Claude Code 2.1.295** (no probe re-run): the
  default effort per model in the embedded model catalog, the `effortLevel`
  schema and the `ultracode` key's description. Statements that rest on
  them name 2.1.295.

Where a statement rests on the docs alone, or on one probe, it says so. The
raw probe outputs are not kept in this repository. These are harness
semantics, not framework semantics, and they can change in any Claude Code
release: re-check them when you update Claude Code.

The framework-side statements (which guard reads what, what a template
ships) were checked against this repository's code, its GA tags v1.0.0 to
v1.4.0 and v1.4.1-rc.1, the newest tag on 2026-09-23; each names the file,
and the release it holds from where that differs. A later release can change them, for example
by adopting the model this page uses as its example: re-check them against
the release you run. The recipe writes the model as `claude-<new-model-id>`.

**Provider scope.** The recipe uses Anthropic API model ids. Per the docs, on
Amazon Bedrock the `model` value is an inference profile ARN, on Google
Cloud's Agent Platform a version name and on Microsoft Foundry a deployment
name: use your provider's own id form there. Nothing below was measured on a
third-party provider; the allowlist matching, the substitution and the probe
results are Anthropic API measurements.

## Why this route exists

The framework adopts a model explicitly, in a release. An Owner-signed
ADR-149 amendment adds the id to the working set, and the maintainer
template's `availableModels`, the price rows and the upgrade baselines follow
it. That path is slow by design. Claude Fable 5.1 launched on 2026-09-01. The
adoption commit (`ab56e76`, 2026-09-02) added `claude-fable-5-1` to the working
set, the maintainer template and the price table, and left the VETO floor, the
fallback chain and the session-default pin unchanged. Adopters received it
with v1.4.0 on 2026-09-15, 14 days after launch.

Those 14 days measure the framework's explicit adoption. On Claude Code
2.1.280, under the segment-prefix matching described
[below](#why-availablemodels-usually-needs-no-change), the `claude-fable-5`
entry that the maintainer template has shipped in every GA release since
v1.0.0 admits `claude-fable-5-1`. Whether the Claude Code versions in use
between 2026-09-01 and 2026-09-15 did the same was not measured. ADR-149
itself is not installed in adopter repositories.

Your own sessions do not have to wait for a release. Claude Code reads a
per-machine settings file that outranks the project's settings, and that
file is enough to run the main session on the new model. Measured on
2026-09-23 with user settings excluded: with the v1.4.0 maintainer template's
`model`, `availableModels` and `fallbackModel` in `.claude/settings.json` and
only `{"model": "claude-opus-5-5"}` in `.claude/settings.local.json`, a
session started without `--model` served `claude-opus-5-5`; without the
local file it served `claude-opus-5`.

Two Claude Enterprise organization controls can overrule the local file on
the Anthropic API (docs, model configuration): an organization default model
that the admin has set to override user selection takes precedence over the
`model` value in user, project and local settings, and a model the
organization restricts is replaced at startup by an allowed one, whatever
`availableModels` says. The [Verify](#verify-the-substitution-risk) step
shows which model you got.

## The recipe

1. **Update Claude Code** to a version that knows the model. Claude Opus 5.5,
   for example, needs Claude Code 2.1.280 or later (docs). The framework's
   v1.4.2 release (planned; not tagged on 2026-09-24) makes 2.1.280 its
   minimum Claude Code, both for that model and for the
   `effortLevel: "xhigh"` its fresh-install settings carry
   ([Effort](#effort)). Check with `claude --version`. If your framework
   release already PINS the model (`jq .model .claude/settings.json` shows
   it), you do not need this route. A model the release only lists in
   `availableModels` is not the session model: a `/model` choice loses to
   the project pin at the next launch
   ([below](#use-the-model-key-not-anthropic_model)), so it still needs the
   local `model` key.

2. **Edit `.claude/settings.local.json` yourself**, from your own editor or
   terminal. Do not ask the agent to do it. What stops an agent write
   depends on the install profile and on the release you installed. Since
   v1.3.0:

   - **maintainer** profile: both write rails
     (`.claude/hooks/check_canonical_edit.py` and
     `.claude/hooks/check_arbitration_kernel.py`) and the
     `Edit(.claude/settings.local.json)` deny rule of the maintainer template
     (`templates/settings/settings.base.json`, rendered into your
     `.claude/settings.json`) refuse it;
   - **user** profile (`--ceremony user`): neither rail is registered and the
     template carries no `permissions` block, so nothing in the framework
     refuses an Edit/Write of this file. Only a Bash write of a shape
     `.claude/hooks/check_bash_safety.py` recognises (a redirect, `tee`,
     `sed -i`, ...) is refused; that hook reuses the canonical path list.

   Before v1.3.0 the file is on neither rail's list (so not on the list
   `check_bash_safety.py` reuses either) and in no deny rule, so none of
   these refuses an agent write of it under either profile.

   If the file already exists (for example `/night-mode on` wrote
   `permissions.defaultMode` into it), add the keys; do not replace the file,
   and keep it valid JSON.

   ```json
   {
     "model": "claude-<new-model-id>"
   }
   ```

   Prefer the explicit model id to an alias. Aliases are resolved by the
   harness and differ per provider. Measured on the Anthropic API (probe R3),
   `opus[1m]` served `claude-opus-5-5[1m]`. On the Anthropic API the `[1m]`
   suffix does not change the window of Opus 4.7 and later, which run with
   the 1M context window anyway (docs): probe R2, with the plain
   `claude-opus-5-5`, reported a 1,000,000-token `contextWindow` as R3 did,
   so there the suffix changes only the id `modelUsage` reports. On Amazon
   Bedrock, Google Cloud's Agent Platform and Microsoft Foundry, per the
   docs, Opus 4.8 and later run with a 200K context window unless the model
   id carries `[1m]`, which selects the 1M window there (append it only when
   the model supports 1M context). Nothing here was measured on those
   providers. Per the docs, `opus` resolves to Opus 5.5 on the Anthropic API,
   Claude Platform on AWS, Amazon Bedrock and Google Cloud's Agent Platform,
   and to Opus 4.6 on Microsoft Foundry.

3. **Optional: `ultracode`.** To get dynamic workflow orchestration by
   default, add `"ultracode": true` next to `model`. On Claude Code 2.1.280
   it also made `xhigh` the default effort. The 2.1.284 changelog says it no
   longer forces `xhigh`, and the 2.1.295 binary describes it as
   orchestration "at any effort level"; the effort it yields on 2.1.295 was
   not probed. The settings reference gives the key the scope "Any file",
   and a probe on 2026-09-22 (Claude Code 2.1.280) with user settings
   excluded read it applied from the local file alone (`get_settings`:
   `ultracode` true, effort `xhigh`, source `localSettings`); so there it
   applies to every session of this project on this machine. It changes
   more than orchestration and effort. Per the Claude Code docs, while
   `ultracode` is active the session is not held to the Agent tool's
   concurrent-subagent limit (20 by default,
   `CLAUDE_CODE_MAX_CONCURRENT_SUBAGENTS`; Claude Code 2.1.217 or later; the
   2.1.280 binary's limit check reads the same flag), and in **Auto**
   permission mode the first-launch Workflow consent prompt is skipped. In
   manual and accept-edits modes each workflow run still asks for approval,
   unless you chose **Yes, and don't ask again** for that workflow in this
   project, an option Claude Code offers only when a bundled, saved or
   plugin workflow is run by name (docs, the workflows page and its
   permission-mode table); the maintainer template
   ships `permissions.defaultMode` `"manual"` from v1.2.0 on. Read [Effort](#effort) and
   [What the local override reaches](#what-the-local-override-reaches)
   before turning it on.

4. **Start a new session.** The model is resolved when a session starts. A
   resumed session (`claude --resume`, `--continue` or the `/resume`
   picker) keeps the model it was using when its transcript was saved,
   whatever the `model` setting says (docs; on Amazon Bedrock, Google
   Cloud's Agent Platform and Microsoft Foundry the saved model is not
   restored), so resuming a session saved before this change does not pick
   up the new model.

5. **Verify what is served** (next section). Do not skip this step.

To roll back, delete the keys you added and start a new session. A session
started under the override and resumed after the rollback stays on the new
model; start a new one instead.

## Verify: the substitution risk

Claude Code treats a model outside the allowlist differently depending on how
you asked for it:

- `/model` in an interactive session **refuses** it with an error (docs);
- a model named with `--model` is **replaced at startup**: probe R1 asked for
  `claude-opus-5-5` under a one-model allowlist and was served
  `claude-haiku-4-5`, the replacement that `enforceAvailableModels: true`
  selected (the first allowed entry). No shipped template sets that key;
  without it the docs say the session starts on the default model instead,
  which these probes did not measure. Per the docs, the `ANTHROPIC_MODEL` environment
  variable and the `model` settings key are replaced the same way (the
  probes did not exercise those two), and an interactive session shows a
  warning naming both the requested and the substituted model. In
  `claude -p --output-format json` probe R1 saw no warning at all: stderr
  stayed empty.

So never infer the model from what you asked for. Check what was served:

- interactively, `/status` (or the status line, if you configured one) shows
  the model the session is running;
- in scripts and CI, run `claude -p --output-format json "reply ok"` and read
  the keys of `modelUsage` in the result. That is the served model id.

## Why `availableModels` usually needs no change

Claude Code 2.1.280 matches `availableModels` entries **by segment prefix**
(binary, and probe R2: the maintainer allowlist admitted `claude-opus-5-5`):
an entry admits every id that starts with it and continues with `-` or ends
there. The maintainer profile's allowlist includes `claude-opus-5` from
v1.2.0 on (checked at every GA tag through v1.4.0 and at v1.4.1-rc.1), so it
already admits `claude-opus-5-5` and `claude-opus-5-5[1m]`. A new
**sub-version** of a listed family needs no
allowlist change. The releases before v1.2.0 (v1.0.0 to v1.1.0) do not list
`claude-opus-5`, so there `claude-opus-5-5` counts as a new family (below).
Check what your install lists, for example with
`jq .availableModels .claude/settings.json`.

A new **family** (an id no entry is a prefix of) does need a change. Add it in
the same local file:

```json
{
  "model": "claude-<new-family-id>",
  "availableModels": ["claude-<new-family-id>"]
}
```

`availableModels` arrays from user, project, local and `--settings` sources
are **concatenated**, so this adds to the project's list instead of replacing
it (binary; probe R4 merged a `--settings` list with a local-file list). Two
exceptions, per the binary and the docs: a list in a **managed** policy
replaces all others, and `fallbackModel` never merges (the highest-precedence
file supplies the whole chain).

The `user` install profile (`templates/settings/settings.user.json`) ships no
`availableModels` at all, on purpose. There, nothing in the project filters
the id; a list in your user settings or in a managed policy still would, and
so would an organization model restriction (above). With no list in effect,
do not add the new-family entry there: a list that holds only the new id
blocks every id that entry is not a prefix of, the VETO agents' own included
([below](#what-the-local-override-reaches)).

## Use the `model` key, not `ANTHROPIC_MODEL`

Model selection, highest first (docs): `/model` in the session, `--model`,
`ANTHROPIC_MODEL`, the `model` settings key, then `ANTHROPIC_DEFAULT_MODEL`.
The `model` key itself resolves by file precedence, highest first: managed
policy, `--settings`, `.claude/settings.local.json`, `.claude/settings.json`,
`~/.claude/settings.json` (an Enterprise organization default with override
on sits above the last three; see above). Since v1.2.0 both install profiles pin a
top-level `model` in `.claude/settings.json`, so a model saved with `/model`
into your user settings loses to that pin at the next launch; that is why the
recipe uses the local file. On an older install there is no project pin.

In the framework's own repository there is a second reason. Two readers
apply the same classifier (`.claude/hooks/_lib/effective_config.py`) to
`ANTHROPIC_MODEL`, `ANTHROPIC_SMALL_FAST_MODEL` and `ANTHROPIC_DEFAULT_*`
(so `ANTHROPIC_DEFAULT_MODEL` too). Up to v1.4.1-rc.1 it flags the value
whenever it is not an **exact** member of the first `frozenset` in ADR-149.
That is the VETO-floor list (`VETO_FLOOR_ALLOWED`), not the working set, so
even some working-set ids are flagged there. The two readers see different
things:

- the `/ceo-boot` tamper tripwire, at the next boot, checks those keys in
  the process environment and in every settings file's `env` block;
- the ConfigChange hook (`.claude/hooks/check_config_change.py`) checks the
  settings layers, their `env` blocks included; it filters
  process-environment findings out. On Claude Code 2.1.280 the ConfigChange
  event also fires for a settings-file change made outside the harness
  during a running session (measured 2026-09-23 in a headless
  `claude -p --input-format stream-json` session: a
  `.claude/settings.local.json` rewritten in place by another process
  mid-session fired it with `source` `local_settings`; no edit, no event).
  An interactive session, and a save that replaces the file by rename, as
  some editors do, were not measured.
  When ANY settings layer carries a finding, not only the file you edited,
  the hook returns a block decision, and Claude Code enforces it silently:
  the edited settings do not reach the running session and no message says
  so (measured the same day, in the same kind of headless session: a deny
  rule added mid-session applied without the block and did not apply with
  it; the docs describe the silence in general). So make the edit between
  sessions, or start a new session after it, as step 4 of the recipe
  requires; a new session reads the file at startup.

The top-level `model` key is not one of the keys the classifier inspects.
Adopter installs do not receive ADR-149, so in an adopter repository the
tripwire does not check the model value at all: it writes a stderr
breadcrumb and emits no finding.

The silent block itself is not limited to the framework's own repository.
The ConfigChange hook is registered in the maintainer template at every GA
release and in the user template from v1.4.0, and most of the classifier's
finding classes do not depend on ADR-149: a hook disarm, a credential or
endpoint re-routing, a permission bypass, a redirect of the status-line
sidecar. In an adopter install where any settings layer carries one of
those (for example a non-default `ANTHROPIC_BASE_URL` for an LLM gateway,
or an `apiKeyHelper`, in your user settings), every settings change made
during a session is dropped with no message, and so is a skill-file change
(a managed-policy change cannot be blocked; docs). The cure is the same:
start a new session after the edit.

## Effort

Levels and defaults depend on the model: see the effort table in the Claude
Code model-configuration docs (some models have no `xhigh`, and a model
missing from that table does not support effort at all).

- **Claude Opus 5.5 defaults to `medium`**; the other models that support
  effort default to `high`, except Opus 4.7 (`xhigh`) and, for your
  organization's default model, the effort level your organization sets
  (docs, read 2026-09-22). Probe E5, with no effort set anywhere, read
  `medium` applied to `claude-opus-5-5`. If you relied on the old default,
  set it explicitly. The model catalog in the Claude Code 2.1.295 binary
  (read 2026-10-09) also gives `medium` to Sonnet 5.5 and Haiku 5.5, and
  `high` to Fable 5.1.
- The `effortLevel` settings key (top level, or per model under
  `modelSettings.<model>.effortLevel`) accepts only `low` to `xhigh`; a `max`
  value there is dropped. In the 2.1.295 binary both schemas still list
  `low` to `xhigh` and drop any other value (read 2026-10-09).
- **An `xhigh` in a settings file needs a Claude Code that accepts it.** The
  changelog (read 2026-09-23) adds the `xhigh` level in 2.1.111. Two later
  entries show one failure shape, a single value a build does not accept
  costing the whole file: 2.1.121 fixes "invalid legacy enum values in
  `settings.json` invalidating the entire settings file", and 2.1.281 notes
  that older CLI versions skip a settings file holding
  `"attribution": false`. A skipped `.claude/settings.json` takes every
  hook it registers with it, the framework's governance hooks included.
  Neither entry names `effortLevel` and no older build was run for this
  page, so which builds skip a file for `effortLevel: "xhigh"` is not
  measured; builds before 2.1.111 do not have the level at all. The framework's
  v1.4.2 release (planned; not tagged on 2026-09-24) ships
  `effortLevel: "xhigh"` in a fresh install's settings and names Claude
  Code 2.1.280, the Opus 5.5 floor, as its minimum. Run `claude --version`
  before you set `xhigh` in any settings file yourself.
- A top-level `effortLevel` in your **user** settings is ignored for Opus 5.5
  and models released after it.
  In project, local or `--settings` sources it applies to every model.
- `max` persists only through the `CLAUDE_CODE_EFFORT_LEVEL` environment
  variable, which takes precedence over `--effort`, `/effort` and the effort
  settings, `ultracode` included; a `maxEffortLevel` cap still applies
  (docs). Probe E7 (Claude Code 2.1.280;
  `CLAUDE_CODE_EFFORT_LEVEL=max` plus `ultracode: true`) saw every tool call
  run at `max`, including one from a workflow agent started with
  `{effort: 'low'}`.

**On Claude Code 2.1.280, `ultracode` and `max` did not combine.** There,
`ultracode: true` made the default effort `xhigh` and enabled dynamic
workflow orchestration. The Claude Code
docs (model configuration, read 2026-09-22) name three conditions under which
it is not available: workflows are turned off, the model does not support
`xhigh`, or an effort cap below `xhigh` applies to the model. That cap is an
organization limit or a `maxEffortLevel` in any settings file; when several
set one, the lowest applies (settings reference). The 2.1.280 binary's own
description of the key calls it session-scoped, "typically provided via
--settings or the apply_flag_settings control request"; the published
settings reference gives it the scope "Any file", and the local-file probe in
step 3 applied it. When the resolved effort is not `xhigh`, the flag stays
set but has no effect. Probes E3, E4, E7 and E8 (`ultracode: true` through
`--settings`, with `CLAUDE_CODE_EFFORT_LEVEL=max` or `--effort max`) read
`ultracode` set in the settings but not applied (`get_settings`
`applied.ultracode` false), while E1 and E6 (without `max`) read it applied.
`/effort max` was not probed. The lifted subagent limit and the Auto-mode
consent skip belong to an applied `ultracode` (docs); neither was probed on
its own.

The 2.1.284 changelog says Ultracode "no longer forces xhigh effort and stays
on at any effort level". The 2.1.295 binary's description of the key (read
2026-10-09) keeps the session-scoped text, says that interactive toggles
never persist it, and names two requirements: workflows enabled and a model
that supports ultracode. It names no effort condition. None of the probes
above was re-run on 2.1.295, so whether `ultracode` and `max` combine there
is not measured.

The combination recommended here is `ultracode: true` for the main session,
with `max` requested per agent inside workflow scripts
(`agent(prompt, {effort: 'max'})`). Probe E6 (Claude Code 2.1.280) measured
it with `ultracode` passed through `--settings`: `ultracode` applied, the
main session and a subagent ran at `xhigh`, and a workflow agent started
with `{effort: 'max'}` ran at `max` (one started with `{effort: 'low'}` ran
at `low`). A local-file `ultracode` was probed only for the applied setting
(step 3), not for per-agent effort.

## What the local override reaches

It reaches:

- **Subagents that have no model of their own.** Per the docs (*Create custom
  subagents*, "Choose a model", read 2026-09-22), Claude Code 2.1.280 resolves
  a subagent's model in this order: the model Claude passes for that
  invocation, the definition's `model:` frontmatter (where `inherit` means the
  main session's model), `CLAUDE_CODE_SUBAGENT_MODEL`, then the main
  session's model. Setting that variable to `inherit` is the same as leaving
  it unset. Both hold from a floor (same docs page): this order from Claude
  Code 2.1.251 (before it, `CLAUDE_CODE_SUBAGENT_MODEL` came first and
  overrode the invocation's model and the frontmatter), and `inherit` as
  unset from 2.1.196 (before it, `inherit` forced every subagent onto the
  main session's model). The shipped settings set it to `inherit` (the maintainer
  profile in every GA release, the user profile since v1.4.0). So a
  general-purpose spawn that is not assigned a model runs on the new model;
  per the docs' environment-variable reference the same default covers
  workflow agents that are not assigned a model. The built-in Explore agent
  inherits it too (capped at Opus on the Claude API), from Claude Code
  2.1.198; before it Explore always ran on Haiku (same docs page). A
  definition whose frontmatter pins an exact id runs on that id only when
  resolution reaches the frontmatter and admits the id. A model Claude
  passes for that invocation, `CLAUDE_CODE_SUBAGENT_MODEL_FORCE`, and an
  allowlist that blocks the id are examples of what moves it off, not a
  complete list; the VETO floor item below states the class. The
  per-invocation model comes first in the order above; the Agent
  tool takes `sonnet`, `opus`, `haiku` or `fable` there, and the 2.1.280
  binary describes the parameter as taking precedence over the definition's
  frontmatter (the changelog records it restored in 2.1.72). A family alias
  passed there resolves to the main session's exact model when that model
  is of the same family (docs). `CLAUDE_CODE_SUBAGENT_MODEL_FORCE` is a
  variable of Claude Code 2.1.257 or later: per the same docs page, while it
  is on Claude Code ignores the `model` field of every subagent definition
  and Claude cannot pass a model. List your pinned definitions with
  `grep -l '^model:' .claude/agents/*.md`.
- **Workflow orchestration, with `ultracode`.** Agents that a Workflow script
  starts do not pass through the spawn gate
  (`.claude/hooks/check_agent_spawn.py`), with or without `ultracode`: a
  Claude Code limit recorded in the framework repository (`CLAUDE.md`, probe
  `wf_d7af49d9`, PLAN-178) and seen again on 2.1.280 in probe E6, where a
  PreToolUse hook matching every tool recorded no Agent event for the three
  `agent()` starts of a workflow while the main session's own Agent call did
  fire one. The workflow agents' own tool calls do fire PreToolUse (measured
  for Bash in E6–E8), so the framework's PreToolUse guards on those tools
  still see them. `ultracode` turns on dynamic workflow orchestration (the
  harness's own description) and, in Auto mode, skips the first-launch
  Workflow consent prompt; the agents those workflows start are agents the
  spawn gate does not see.

It does not change:

- **The VETO floor check, though not the model of every VETO spawn.** The
  spawn gate (`.claude/hooks/check_agent_spawn.py`) checks the VETO-role
  agent files' own `model:` frontmatter against `VETO_FLOOR_ALLOWED`
  (`.claude/hooks/_lib/agent_frontmatter.py`, exact membership). It does not
  read the session model, so the override neither trips that check nor
  satisfies it. It does not read the model Claude passes for the invocation
  either, although the PreToolUse input of an Agent call carries it as
  `tool_input.model` (docs, hooks reference), and it does not see the model
  Claude Code finally serves. The check vouches for the frontmatter only,
  and the frontmatter decides a VETO agent's model only when resolution
  reaches it and admits it. Anything that settles the model before the
  frontmatter is consulted, or that rejects the frontmatter's id once it
  is, runs a VETO agent on another model while the check still passes.
  Those mechanisms belong to Claude Code and change between its releases:
  the *Create custom subagents* docs page, sections "Choose a model" and
  "Run every subagent on one model" (read 2026-09-23), describes them for
  the current release. The three below are examples from that reading, not
  a complete list:

  - **A per-invocation model.** It outranks the frontmatter (the
    resolution order above). An alias that resolves outside
    `VETO_FLOOR_ALLOWED` (`sonnet` or `haiku`, for example) runs the VETO
    agent off the floor with or without this override. `opus` resolves to
    the main session's exact model when that model is an Opus: without the
    override that is the shipped pin `claude-opus-5`, which the floor lists;
    under the override it is the new model, and `claude-opus-5-5`, this
    page's example, is not in `VETO_FLOOR_ALLOWED` as of v1.4.1-rc.1. When
    the main session's model is not an Opus, `opus` resolves to the version
    the alias points to, which on the Anthropic API is Opus 5.5 from Claude
    Code 2.1.280 unless `ANTHROPIC_DEFAULT_OPUS_MODEL` is set (docs, model
    configuration): outside the floor as well.
  - **A variable that comes before the frontmatter or replaces it.** On
    Claude Code older than 2.1.196 the shipped
    `CLAUDE_CODE_SUBAGENT_MODEL=inherit` forced every subagent onto the main
    session's model, so there the override changes the model every VETO
    agent is served; from 2.1.196 `inherit` counts as unset. Before 2.1.251
    a model set in `CLAUDE_CODE_SUBAGENT_MODEL` came first in the order and
    overrode the frontmatter. On 2.1.257 or later (that variable's floor),
    while `CLAUDE_CODE_SUBAGENT_MODEL_FORCE` is on, Claude Code ignores the
    `model` field of every definition. No shipped template sets that
    variable; leave it unset, or the VETO floor model is lost.
  - **An allowlist that blocks the frontmatter's id.** Claude Code checks
    the frontmatter value against the `availableModels` list in effect. For
    a blocked full id it runs the subagent on the inherited model instead,
    trying `CLAUDE_CODE_SUBAGENT_MODEL` first when that names a model; under
    this override the inherited model is the new model. At every GA tag
    from v1.0.0 through v1.4.1-rc.1 the VETO-role files (`VETO_FLOOR_ROLES`
    in the same module) pin `claude-fable-5`, and the maintainer
    template's list admits that id. Lists from user, project and local
    settings are concatenated, so in a maintainer install a list you add
    there cannot remove it. A list in a managed policy replaces all the
    others (docs, model configuration, "Merge behavior"), so under either
    profile it blocks the id unless it admits it. A `user` profile install
    ships no list, so there any list in effect blocks the id unless it
    admits `claude-fable-5`: one in your user or local settings, for
    example, the new-family entry
    [above](#why-availablemodels-usually-needs-no-change) included. Check
    with `grep '^model:' .claude/agents/*.md` which ids your definitions
    pin, and keep each one in any list you add.
- **The prices.** `python3 .claude/scripts/ceo-cost.py` (no slash command
  ships for it) has printed two blocks by default (`--source both`) since
  v1.4.0. The transcripts block (primary,
  `.claude/scripts/ceo-cost-transcripts.py`) reads the model recorded on each
  transcript turn, so the new id does appear there, but until a release adds
  its price row it is named in a warning and priced at $0, never guessed; its
  prices come from `.claude/scripts/cost-table.yaml`, or from a table
  embedded in that script when the file does not parse. The
  audit block (secondary) prices each spawn by the model id
  `.claude/hooks/audit_log.py` records for it. In the PLAN-044 audit the
  spawn's tool response carried no model on 199 of 199 spawns (an older
  Claude Code; not re-measured on 2.1.280), so that id is the ADR-052 policy
  id for the agent's role (for `general-purpose`, `claude-opus-5` from
  v1.2.0 through v1.4.1-rc.1 and `claude-opus-4-8` from v1.0.0 through
  v1.1.0), or nothing, which the audit block reports as `unknown_model` at
  $0. The `CEO_COST_PRICING_JSON` override **replaces**
  the audit block's price table rather than extending it: a custom file must
  carry every row you want priced.
- **Your teammates.** The file is per machine and must stay out of git.
  Since v1.3.0, `scripts/install.sh` and `scripts/upgrade.sh` put
  `/settings.local.json` in `.claude/.gitignore` under **every** install
  profile (creating the file, or appending the entry when it is missing).
  They also add `.claude/settings.local.json` to the repository's root
  `.gitignore` unless the profile is `user`. `install.sh` defaults to
  `maintainer`, so it writes the root entry unless run with
  `--ceremony user`. `upgrade.sh` takes the profile from the recorded
  `.claude/.install-state.json` first, then `--ceremony`, then the
  `CEO_UPGRADE_CEREMONY` environment variable; with none of these it treats
  the install as `user` and skips the root file. On an older
  install, or if you edited those ignore files, check with
  `git check-ignore .claude/settings.local.json`: if it prints nothing, add
  the path to `.gitignore` yourself before committing anything.

When the framework release that adopts the model arrives, upgrade as usual
([UPGRADE-PROCEDURE.md](UPGRADE-PROCEDURE.md)). If the release pins the same model, you can
remove the keys from the local file; if it pins another one, the local file
keeps winning on your machine until you remove them.
