---
description: In-process governance guard self-test — asserts the 3 core guards block crafted payloads, $0 hermetic — /self-test
allowed-tools: Bash, Read
---

# /self-test — Governance guard self-test (PLAN-133 C5)

Drives the three **core governance guard hooks IN-PROCESS** against crafted
(synthetic) payloads and asserts each one **BLOCKS**. It NEVER spawns a live
subagent and NEVER constructs an Anthropic client, so it is **$0 hermetic** —
it exercises only the pure decision functions of the hooks.

This is the framework's "are my guardrails still armed?" smoke test. Run it
after any change to `check_agent_spawn.py`, `check_canonical_edit.py`, or
`check_bash_safety.py`, and at `/ceo-boot` when you want a fast governance
liveness signal.

## Guards under test

| # | Guard | Crafted payload | Expected |
|---|-------|-----------------|----------|
| a | `check_agent_spawn` | persona header (`PERSONA:`) with **no** `## SKILL CONTENT` | **block** |
| b | `check_canonical_edit` | edit to `.claude/team.md` with **no** Owner-signed sentinel | **block** |
| c | `check_bash_safety` | `rm -rf /` | **block** |
| d | `effective_config.classify_tampering` (PLAN-135 W1 S3) | crafted tamper payloads — `disableAllHooks`, `apiKeyHelper`, `bypassPermissions`, `ANTHROPIC_BASE_URL` remap, `ANTHROPIC_AUTH_TOKEN`, dangerously-skip flag, ghost registered hook | **detect** (+ secrets redacted) |

Any guard that **ALLOWS** its payload is a **CRITICAL** governance regression
(the protective hook has been silently disabled or weakened). The harness also
fails the run if any `anthropic` client module is imported while the guards
run (the $0-hermetic invariant).

Section (d) is the tamper-tripwire assertion (PLAN-135 W1 S3): it drives the
same classifier the `/ceo-boot` `settings_tamper_tripwires` Tier-S check uses
and reports under a separate `tamper` section (the C5 3-scenario contract is
unchanged). While `_lib/effective_config` is not yet installed
(pre-W1-ceremony), the section is **SKIPPED** with an advisory note and the
run still passes; post-ceremony, a `missed` verdict is CRITICAL.

## Arguments received

`/self-test $ARGUMENTS`

- (no args) — run all scenarios, print a human-readable report.
- `--json` — emit a JSON result object instead.

## Procedure

### Step 1 — Run the harness

```bash
python3 .claude/scripts/self_test.py $ARGUMENTS
```

The runner:
1. Installs an Anthropic-import sentinel (reversible; snapshots `sys.modules`
   so a pre-loaded module is not counted against this run).
2. Drives each guard's pure `decide` / `decide_command` function against the
   crafted payload (no I/O beyond a hermetic temp dir for the canonical-edit
   case; no network; no model call).
3. Asserts each verdict is `block`.
4. Asserts no Anthropic client module was newly imported.

### Step 2 — Read the verdict

- Exit `0` → every guard blocked correctly (**PASS**) and the run was hermetic.
- Exit `1` → at least one guard **failed to block** (CRITICAL) **or** a strict
  infra error (a guard module could not be imported) **or** an Anthropic client
  was constructed (not hermetic).
- Exit `2` → usage / IO error.

On a CRITICAL result, treat it as a halt-trigger: a governance guard is no
longer protecting the session. Do NOT proceed with work until it is restored.

## Config

`CEO_SELF_TEST_STRICT` (default `1`): when `1`, an infra error (e.g. a guard
module that cannot be imported at all) is a hard FAIL; set to `0` to demote
infra errors to a non-fatal advisory SKIP. The guard **verdicts** themselves
are always strict regardless of this flag.

The declarative scenario manifest is `.claude/eval/self_test.yaml` (metadata
only — the guard-driving payloads live in `.claude/scripts/self_test.py`, the
source of truth, so a tampered manifest can never weaken a verdict).
