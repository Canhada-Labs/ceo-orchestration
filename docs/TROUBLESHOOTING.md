# TROUBLESHOOTING — Common problems and fixes

> **PT-BR:** [TROUBLESHOOTING.pt-BR.md](TROUBLESHOOTING.pt-BR.md) (mirror).

## "The hook blocked my command"

### Destructive bash blocked

**Message:** `BLOCKED: 'rm' with -r and -f is destructive`

**Fix:** don't use `rm -rf`. Options:
```bash
# Em vez de: rm -rf foo/
mv foo/ /tmp/foo.trash-$(date +%s)

# Se precisa APAGAR mesmo:
# Roda no seu terminal (fora do Claude Code), não via CEO.
```

Full list of blocked commands in
`.claude/hooks/check_bash_safety.py`.

### Edit on a canonical file blocked

**Message:** `CANONICAL-EDIT-BLOCKED: '<path>' is a canonical
governance path`

**Fix:** use `/architect`:
```
/architect "atualiza o skill security-and-auth pra incluir X"
```

Or, if it's a structural framework change, work via PLAN-NNN with a
sentinel signed by the Owner.

### Agent spawn blocked

**Message:** `spawn missing ## SKILL CONTENT section`

**Cause:** you (or the CEO) tried to invoke the Agent tool without
loading a skill. This is the most important hook — it prevents the
"cosmetic agent" (just a name, no manual).

**Fix:**
- Use `/spawn` instead of the Agent tool manually
- Or use `bash .claude/scripts/inject-agent-context.sh "<nome>" "<task>"`

### Plan-lifecycle transition blocked

**Message:** `PLAN-LIFECYCLE: ...` (e.g. missing `reviewed_at`, missing
`completed_at`, or an abandonment without a reason).

**Cause:** `check_plan_edit.py` enforces the plan state machine
(draft → reviewed → executing → done, plus `abandoned`). A status flip
that skips a required timestamp or jumps a state is blocked.

**Fix:** add the required field for the transition you want:
- `draft → reviewed` needs a `reviewed_at:` stamp
- `executing → done` needs a `completed_at:` stamp
- `→ abandoned` needs an abandonment reason
Then re-apply the edit. Full state machine: `.claude/plans/PLAN-SCHEMA.md` §1.

### Anti-CEO-overhead pattern blocked

**Message:** `GOVERNANCE: anti-CEO-overhead ...`

**Cause:** `check_anti_ceo_overhead.py` fires when the CEO does work
itself that should be delegated (one of the P1-P5 predicates — e.g.
writing bulk code inline instead of spawning a specialist).

**Fix:** delegate via `/spawn`. If the action is genuinely correct and
you accept the overhead, set `CEO_OVERHEAD_ACK=1` for that action (the
override is itself audited).

### Kernel-path edit hard-denied

**Message:** `GOVERNANCE: ... arbitration kernel ...` (hard-deny).

**Cause:** `check_arbitration_kernel.py` hard-denies edits to the
governance kernel paths (the hooks, the arbitration logic itself).
This is the strongest guard and is not relaxed by the canonical
sentinel alone.

**Fix:** kernel changes go through a PLAN-NNN with an Owner-issued
kernel override: `CEO_KERNEL_OVERRIDE=<plan-id>` +
`CEO_KERNEL_OVERRIDE_ACK=I-ACCEPT`, scoped to that plan. Never carry a
stale override across sessions — `unset` it when it is not your current
plan (a leftover override silently widens what canonical edits pass).

### Cross-plan scratchpad access blocked

**Message:** `scratchpad --plan ...`

**Cause:** `check_scratchpad_access.py` blocks a plan from reading or
writing another plan's scratchpad memory.

**Fix:** use the scratchpad scoped to your own plan id. If you need a
handoff, write to the shared memory namespace via `/memory-scratchpad`
for your current plan, not another plan's path.

### Swarm cost cap blocked

**Message:** `GOVERNANCE: cost_envelope_capped_at_<window>: ...`

**Cause:** `check_cost_envelope.py` blocks a swarm/agent dispatch whose
estimated spend would exceed the per-window cost cap.

**Fix:** lower the fan-out (fewer parallel spawns), or run in batches.
The estimate comes from `CEO_SWARM_ESTIMATE_CENTS` /
`CEO_SWARM_ESTIMATED_SPAWN_CENTS`; if the estimate is wrong, correct it
before re-dispatching. The cap is a budget guardrail, not a bug.

### MCP response injection blocked

**Message:** `{"decision":"block", ...}` from an MCP tool result.

**Cause:** `check_mcp_response.py` (STRICT) blocks when an MCP tool's
response contains a prompt-injection / instruction-override pattern.

**Fix:** this is protecting you — an external MCP server tried to inject
instructions. Do not work around it. Inspect the offending MCP server;
if it is a false positive on benign content, file an issue tagged
`area/hooks`.

### Skill-patch sentinel blocked

**Message:** `{"decision":"block", ...}` on a skill-patch apply.

**Cause:** `check_skill_patch_sentinel.py` blocks applying a skill patch
without a valid Owner-signed sentinel.

**Fix:** route skill changes through `/architect` or `/skill-review`; the
Owner signs the sentinel that authorizes the apply.

### Tier-policy routing blocked

**Message:** `{"decision":"block", ...}` referencing tier policy.

**Cause:** `check_tier_policy.py` blocks a dispatch that violates the
model-tier routing policy (`.claude/tier-policy.json`).

**Fix:** route the task to the tier the policy allows for that task
class. If the routing itself is wrong, the fix is a tier-policy change
(canonical — via PLAN-NNN + sentinel), not a per-call bypass.

### Codex file-write blocked

**Message:** `{"decision":"block", ...}` on a Codex (pair-rail) write.

**Cause:** `check_codex_filewrite.py` blocks the Codex MCP pair-rail from
writing to paths outside its allowed scope.

**Fix:** have Codex propose the diff and let the CEO apply it through the
normal Edit/Write path (which the canonical guards then evaluate). Codex
is a reviewer/proposer, not a direct writer to guarded paths.

### Confidence gate blocked

**Message:** `decision: block` with a confidence reason.

**Cause:** `check_confidence_gate.py` blocks a low-confidence claim
(ADR-019-AMEND-1 per-class block-mode) — e.g. an agent asserting a fact
it cannot ground.

**Fix:** ground the claim (cite the file/line) and retry. As a last
resort the bypass hatch is `CEO_CONFIDENCE_BYPASS=1`, but prefer fixing
the claim over bypassing — a blocked claim is usually a real signal.

### Which hooks can block vs. only warn

Not every hook blocks. These are **advisory-only** (they emit findings
but never return `decision: block`), so if work stops it is *not* one of
these: `check_read_injection.py`, `check_webfetch_injection.py`,
`check_output_secrets.py` / `check_output_safety.py`,
`check_pair_rail.py` (block path demoted to advisory per ADR-127),
`check_skill_bootstrap_post.py`, and `audit_log.py` (silent observer).
The blocking set is the 13 hooks documented above
(bash-safety, canonical-edit, agent-spawn, plan-edit,
anti-ceo-overhead, arbitration-kernel, scratchpad-access,
cost-envelope, mcp-response, skill-patch-sentinel, tier-policy,
codex-filewrite, confidence-gate). Verify the current set yourself with:
```bash
grep -l '"decision": "block"' .claude/hooks/check_*.py
```

## "I don't know which command or skill to use"

**Symptom:** you have a task but don't know what to invoke.

**Fix:** use the discovery primitive — type `/help me <your situation>`
(note the space after `help`):
```
/help me I need to add a payment endpoint that takes card data
```
It is context-aware: give it your *current* situation, not a generic
question. It routes you to the right skill or command.

## "/first-run command not found"

**Symptom:** the onboarding docs mention `/first-run` and you get
command-not-found.

**Fix:** `/first-run` is wired by `.claude/commands/first-run.md`. If your
install predates it, run the wizard directly:
```bash
python3 .claude/scripts/first-run-wizard.py run
```
This detects your repo profile, explains it, and recommends the top
skills to activate.

## "CEO didn't activate"

**Symptom:** you type "Activate the CEO protocol" and Claude answers
as a generic assistant.

**Checklist:**
1. Are you inside the project directory? (`pwd` should show the
   project, not your home)
2. Does `CLAUDE.md` exist at the root?
3. Does `PROTOCOL.md` exist at the root?
4. Does `.claude/skills/core/ceo-orchestration/SKILL.md` exist?

If any is missing, run the installer:
```bash
bash /caminho/ceo-orchestration/scripts/install.sh
```

## "CEO spawned an agent and it failed"

**Symptom:** CEO spawns "VP Engineering" and gets useless or
fabricated output.

**Cause 1: persona wasn't loaded.** Check the audit log:
```bash
python3 .claude/scripts/audit-query.py search --q "VP Engineering"
```

If `has_profile: false` appears, the spawn ran without persona. The
CEO needs to use `/spawn` correctly.

**Cause 2: skill doesn't exist.** List installed skills:
```bash
python3 .claude/scripts/registry.py skills
```

If the skill invoked isn't listed, fix the SKILL MAP in
`.claude/team.md`.

**Cause 3: agent hallucinated a file.** Sprint 7 will ship a
confidence gate. Until then, verify yourself:
```bash
grep -r "<caminho que o agente citou>" .
```

If it doesn't exist, the agent lied. That's a strike (3 strikes =
persona rewrite).

## "Coverage CI failed"

**Symptom:** push to main, Coverage CI red, message
`FAILED under 86`.

**Fix:**
1. Run it locally first:
   ```bash
   python3 -m coverage run --source=.claude/hooks -m unittest discover -s .claude/hooks/tests
   python3 -m coverage run --append --source=.claude/scripts -m unittest discover -s .claude/scripts/tests
   python3 -m coverage report
   ```
2. Identify the file with the gap
3. Add tests to cover it

Or, if it's a temporary regression (large refactor), open a PR
relaxing the threshold in `.github/workflows/coverage.yml` (Owner
approves).

## "/debate stuck on 'waiting for agent N'"

**Cause:** one of the parallel spawns silently failed.

**Fix:**
```bash
ls -la .claude/plans/PLAN-NNN/debate/round-1/
```

If an `<archetype>.md` file is missing, re-spawn that agent:
```
/spawn "<archetype>" "finish your round 1 critique on PLAN-NNN and write .claude/plans/PLAN-NNN/debate/round-1/<archetype-slug>.md"
```

## "Audit log grew too large"

**Symptom:** `audit-log.jsonl` exceeded 10 MB.

**Fix:** automatic rotation already exists. If it didn't rotate:
```bash
ls -la ~/.claude/projects/<slug>/
# Procura audit-log-2026-04.jsonl, -2026-05.jsonl, etc
```

If no rotated files exist and the file is huge, force a rotation:
```bash
mv ~/.claude/projects/<slug>/audit-log.jsonl \
   ~/.claude/projects/<slug>/audit-log-$(date +%Y-%m-manual).jsonl
```

## "Memory 'auto-loaded' wrong"

**Symptom:** CEO remembers something you didn't say, or forgets
what you did say.

**Fix:** memory lives in:
```bash
ls ~/.claude/projects/<slug>/memory/
```

Edit directly OR:
```
Esquece X.
```

CEO will search for the entry in memory and remove it.

## "I want to disable everything temporarily"

```bash
cd /caminho/do/seu/projeto
mv .claude .claude.disabled
mv CLAUDE.md CLAUDE.md.disabled
```

Claude Code reverts to generic mode.

To re-enable:
```bash
mv .claude.disabled .claude
mv CLAUDE.md.disabled CLAUDE.md
```

## "How do I wipe audit log and lessons to start from scratch?"

```bash
SLUG=$(pwd | sed 's|/|-|g' | sed 's|^-||')
rm -f ~/.claude/projects/$SLUG/audit-log.jsonl
rm -f ~/.claude/projects/$SLUG/audit-log.errors
rm -rf ~/.claude/projects/$SLUG/lessons/
```

Warning: audit trail is lost. Back up first if it matters.

## "CEO_HOOK_ADAPTER: what is it?"

Env var that picks which IDE adapter to use. **V1.0 supports only
`claude`**. Leave it empty or default:

```bash
# Não precisa exportar nada — o default é claude
```

A Gemini stub exists but is for Sprint 8+. Don't use it in
production.

## "Tests pass locally, CI fails"

**Common causes:**
1. **Different environment.** CI runs Python 3.11 on Linux. Your
   local setup is probably macOS + Python 3.9.
2. **Missing secrets.** Some tests require env vars you have
   locally but CI doesn't.
3. **Dependency not installed on CI.** Check `.github/workflows/*.yml`
   — any `pip install` listed, add it to your environment.

## Common requests the CEO refuses

- "Write it straight, skip the plan" → refused on protocol grounds
- "Ignore hook X" → refused, hooks are mechanical
- "Merge without code review" → Staff Code Reviewer vetoes
- "Commit without me asking" → anti-pattern #7

If you think the refusal is wrong, escalate to the Owner.

## When to file a GitHub issue

- Inconsistent hook behavior (blocks in a scenario where it should
  allow)
- Skill with outdated information
- Doc with an error

Tag with `area/hooks`, `area/skills`, `area/docs` respectively.

## Last resort: reinstall from scratch

```bash
cd /caminho/do/seu/projeto
rm -rf .claude/
rm CLAUDE.md PROTOCOL.md
bash /caminho/ceo-orchestration/scripts/install.sh
```

You lose customizations. Back up first.
