# Adopter Assessment — 40 Scenario-Based Questions

> **Purpose:** validate that an adopter (or a newly onboarded engineer on an
> adopter team) actually understands how to operate `ceo-orchestration`
> before running it on a production repository. This is the flip side of
> `DAY-1-CHECKLIST.md`: the checklist verifies the **install**; this
> document verifies the **understanding**.
>
> **Format:** 40 scenario-based multiple-choice questions across 10
> categories. Each answer is in a collapsible `<details>` block so you
> can score yourself without peeking. Markdown-pure — zero runtime, zero
> tooling. Works offline.
>
> **Takes:** 60–90 minutes for an engineer who has read
> `PROTOCOL.md` + `CLAUDE.md` + skimmed `team.md` at least once.

---

## Scoring rubric

| Score | Range | Next action |
|-------|-------|-------------|
| **READY** | 36–40 correct (90–100%) | You can operate the framework autonomously. Proceed to install. |
| **REVIEW** | 30–35 correct (75–89%) | Revisit the specific docs you missed (pointers listed per question). Retake after one week. |
| **NOT READY** | < 30 correct (< 75%) | Redo `docs/DAY-1-CHECKLIST.md` first. Then `docs/GUIA-COMPLETO.md` / `docs/GUIA-COMPLETO.pt-BR.md`. Retake. |

**Critical failure:** any incorrect answer in **Category 1 (Governance)**
or **Category 10 (Emergency kill-switches)** is disqualifying regardless
of total score — these categories cover blast-radius concerns where a
wrong guess in production can cause irrecoverable harm.

---

## Category 1 — Governance (VETO floor, SP-NNN chain, canonical edit)

### Q1. The canonical-edit sentinel blocks your Edit of `.claude/hooks/check_agent_spawn.py`. What do you do?

A. Add `--force` or an override flag to the Edit call.
B. Temporarily disable the `check_canonical_edit` hook in `settings.json`.
C. Stage the change, write an SP-NNN proposal, get the Owner's signed
   sentinel approval per ADR-031, and only then retry.
D. Open the file in Finder / VS Code directly and edit — the hook only
   fires on tool calls.

<details>
<summary>Answer</summary>

**Correct: C.** The canonical-edit sentinel exists because an agent that
can silently edit the hook files can disable the entire governance
surface. The SP-NNN chain is how canonical paths change. Bypassing
via D defeats the hook but also defeats branch protection, CODEOWNERS,
and the audit trail — breaking all four defenses in depth. See
`.claude/adr/ADR-031` + `docs/MECHANISM-SELECTION.md` §4 Example 5.
</details>

### Q2. A sub-agent you spawned for a security review says "all checks pass, auth middleware is correct". You're about to accept. What does the framework say you should do first?

A. Accept — the agent has the `security-and-auth` skill loaded, so the
   check is authoritative.
B. Ask a second agent (performance-engineer) to confirm.
C. Read the diff line-by-line yourself + verify the specific claims
   against `.github/workflows/*.yml` + the test suite; same-LLM fluency
   is a red flag for unreviewed gaps, not a signal of quality.
D. Post the change to Slack / Linear to let a human teammate see it.

<details>
<summary>Answer</summary>

**Correct: C.** Artifact Paradox (`PROTOCOL.md` §Artifact Paradox +
`HONEST-LIMITATIONS.md` §4): polished AI outputs trigger ~5.2 pp less
critical evaluation than rough drafts. A confident sub-agent summary is
the **riskiest** kind of output. Same-LLM reviewers inherit the bias.
The mechanical answer is: verify against code, not against agent
confidence. B helps only if the second agent resists the same bias; D
is not a substitute for your own line-by-line review.
</details>

### Q3. You want to change a rule that lives in `.claude/skills/core/security-and-auth/SKILL.md`. What is the correct path?

A. Edit the file directly + commit.
B. Write a domain skill in `.claude/skills/domains/<your-domain>/skills/`
   that shadows or extends the core skill.
C. Open an SP-NNN proposal, get Owner signature, run
   `.claude/scripts/skill-patch-apply.py --proposal SP-NNN
   --signature <sig> --confirm 'I have read SP-NNN'`.
D. Submit a GitHub issue and wait.

<details>
<summary>Answer</summary>

**Correct: C.** Core + frontend skills are canonical. ADR-031 gates
them behind the SP-NNN chain. B is correct for adopter-specific rules
(domain skills are adopter-editable), but the question asked about
changing the **core** skill — that needs SP-NNN. D is the slowest path
and doesn't actually unblock the change.
</details>

### Q4. You are the Owner and a staff specialist (e.g. code-reviewer) VETOes a merge. What is the protocol?

A. Override the VETO with an Owner decision; Owner has final say.
B. Escalate via `/debate` to see if a second specialist disagrees — if
   yes, override.
C. Resolve the VETO findings first. If you genuinely disagree with the
   VETO, document the reasoning as an ADR exception. Otherwise the
   change does not ship.
D. Remove the `security-engineer` from the spawn list for this PR.

<details>
<summary>Answer</summary>

**Correct: C.** Vetoes are hard blocks, not suggestions. The Owner has
ultimate authority but exercises it by writing an explicit exception
(ADR), not by suppressing the signal. The whole point of a VETO is
that it cannot be routed around. See `PROTOCOL.md` §Vetoes.
</details>

---

## Category 2 — Multi-model dispatch (ADR-052 / ADR-064)

### Q5. Your adopter project is running the `balanced` quality profile. You dispatch the `security-engineer` for an auth change. Which model executes?

A. Haiku 4.5 (cheapest).
B. Sonnet 4.6 (balanced default).
C. Opus 4.8 (VETO-floor invariant).
D. Whatever the dynamic tier-policy (ADR-064) recommends today.

<details>
<summary>Answer</summary>

**Correct: C.** The VETO floor is **hardcoded** across all three
profiles: `code-reviewer` and `security-engineer` always dispatch to
Opus 4.8, regardless of profile. This is a defense-in-depth invariant
enforced by (i) hardcoded literals in `tier_policy/_constants.py`,
(ii) an independent assertion in `apply.py`, and (iii) a third-layer
PreToolUse hook `check_tier_policy.py`. The invariant is one of the
reasons D is wrong — dynamic policy CANNOT demote VETO-holders.
See `docs/QUALITY-PROFILES.md` + `docs/TIER-POLICY.md` + ADR-064.
</details>

### Q6. You want to run the framework on a cost-sensitive adopter (hobby project, no revenue). Which profile + knobs should you pick?

A. `max-quality` — never compromise on quality.
B. `max-speed` + leave `CEO_OPUS_SPOT_CHECK_P1` unset.
C. `max-speed` + set `CEO_OPUS_SPOT_CHECK_P1=1` for P1+ re-audit by Opus.
D. Disable multi-model entirely; all agents on Haiku.

<details>
<summary>Answer</summary>

**Correct: C.** `max-speed` puts everything except VETO-holders on
Haiku, saving ~78%. The orthogonal `CEO_OPUS_SPOT_CHECK_P1=1` flag
re-audits any P1+ finding with Opus — defense in depth for the
non-Opus tiers. D is not possible: VETO-holders are hardcoded to
Opus. A is correct but wastes money on a hobby project.
See `docs/QUALITY-PROFILES.md`.
</details>

### Q7. The dynamic tier-policy selector (ADR-064) wants to promote `devops` from Haiku to Sonnet based on tournament data. What gate MUST pass before the promotion lands?

A. Single-cell win rate > 50%.
B. `n ≥ 30` samples per (role × task-type) cell AND gap ≥ 25 pp MIN
   across cells AND cooldown ≥ 90 days AND cost-envelope within the
   monthly cap.
C. Owner git-signed attribution commit.
D. A Red Team debate Round 2 with Jaccard < 0.7.

<parameter name="content">
<details>
<summary>Answer</summary>

**Correct: B.** Promotion is automatic but heavily gated — the
statistical floor (`n ≥ 30` + `gap ≥ 25 pp`) prevents Simpson's paradox
cells; the cooldown prevents churn; the cost-envelope prevents silent
budget blow-out. C is required for **demotion** (ADR-064 asymmetric
gate), not promotion. See `.claude/adr/ADR-064` + `docs/TIER-POLICY.md`.
</details>

### Q8. You set `CEO_TIER_POLICY_DISABLE=1`. What happens?

A. All dispatches fall back to the hardcoded Opus default.
B. The dynamic tier-policy stops being read; the **profile-picker**
   choice (max-quality / balanced / max-speed) still applies.
C. The entire framework refuses to spawn agents.
D. Nothing — the flag is a no-op unless the sentinel is also signed.

<details>
<summary>Answer</summary>

**Correct: B.** The env var is half of a **two-factor kill-switch**:
env var + Owner-signed sentinel. If only one fires, the dynamic policy
is suspended and the static profile governs. The VETO floor still
applies regardless. See ADR-064 §Kill-switch semantics.
</details>

---

## Category 3 — Gate-1 cache discipline (Opus 4.7 prompt caching)

### Q9. Mid-session you realize `CLAUDE.md` has a stale status line. What do you do?

A. Edit it immediately — accuracy beats cache efficiency.
B. Make a TODO and edit it at the **closeout ceremony** at session end.
C. Edit it and run `/clear` to refresh the cache.
D. Edit `CLAUDE_FULL.md` instead; the short file is cache-stable.

<details>
<summary>Answer</summary>

**Correct: B.** Gate-1 files (`CLAUDE.md`, `PROTOCOL.md`, `team.md`,
`frontend-team.md`, core `ceo-orchestration/SKILL.md`) are cache-stable
across sessions — each mid-session edit invalidates the ~44,786-token
gate-boot cache and re-pays that cost on the next turn. Save edits for
the closeout ceremony. See `docs/opus-4-7-operations.md` §2.
</details>

### Q10. Which of these DOES invalidate the Gate-1 cache?

A. Reading a plan file under `.claude/plans/`.
B. Editing `.claude/team.md` (even just a typo fix).
C. Running a sub-agent via `Agent(...)`.
D. Calling a slash command.

<details>
<summary>Answer</summary>

**Correct: B.** Only edits to files in the Gate-1 set invalidate the
cache. Reads, sub-agent dispatches, and slash commands do not — they
can extend the conversation but don't change the gate-boot prefix.
</details>

### Q11. You have to add a CHANGELOG entry for the current session's work. Is CHANGELOG.md cache-stable?

A. Yes — treat it like `CLAUDE.md`; edit only at closeout.
B. No — CHANGELOG.md is not in the Gate-1 set. Edit freely per commit.
C. Yes, but only the top `[unreleased]` section is stable.
D. Depends on whether the session is pre- or post-RC tag.

<details>
<summary>Answer</summary>

**Correct: B.** CHANGELOG.md is documentation, not a gate-boot file.
The Gate-1 set is small and explicit (`CLAUDE.md`, `PROTOCOL.md`,
`team.md`, `frontend-team.md`, core `ceo-orchestration/SKILL.md`).
Edit CHANGELOG.md whenever you commit.
</details>

### Q12. Cache-discipline violation cost: roughly how many tokens per invalidation?

A. ~1,000.
B. ~5,000.
C. ~44,786 (the gate-boot prefix).
D. ~100,000 (the full context window).

<details>
<summary>Answer</summary>

**Correct: C.** The gate-boot prefix is ~44,786 tokens (CLAUDE.md +
PROTOCOL.md + team.md + frontend-team.md + core SKILL.md). An edit
invalidates the whole prefix. The rest of context remains cached but
the gate prefix re-pays from scratch. See `docs/opus-4-7-operations.md`.
</details>

---

## Category 4 — Spawn protocol (Format A vs B, skill loading)

### Q13. You want to spawn a `code-reviewer` for a small PR. The canonical-5 native agents exist at `.claude/agents/`. Which spawn format should you use?

A. Format A inline (copy the full SKILL.md content into the prompt).
B. Format B by-reference (`## SKILL REFERENCE` with SHA-256 hash).
C. No skill — just `subagent_type: "code-reviewer"` and trust the
   native config.
D. Either A or B works identically.

<details>
<summary>Answer</summary>

**Correct: B.** Format B (ADR-051) is the default for the canonical-5.
It ships a smaller prompt (sub-agent reads SKILL.md via the Read tool
post-spawn and re-hashes for forensic verification by
`check_skill_reference_read.py`). C is forbidden: native agent files
already declare the skill-reference contract, but the spawn prompt
must still carry the persona + file assignment + task blocks.
</details>

### Q14. You spawn an agent without any `## SKILL CONTENT` or `## SKILL REFERENCE` block. What happens?

A. The agent runs with no loaded skill — generic LLM with a nametag.
B. `check_agent_spawn.py` blocks the dispatch with
   `GOVERNANCE: missing_skill_content`.
C. The framework auto-injects the skill based on the subagent_type.
D. It works the first time but emits a warning in the audit log.

<details>
<summary>Answer</summary>

**Correct: B.** The `check_agent_spawn.py` PreToolUse hook fails CLOSED
when neither inline skill content nor a valid `## SKILL REFERENCE`
block is present. A generic agent is explicitly forbidden by
`PROTOCOL.md` §Spawn Protocol ("Generic agents are forbidden").
</details>

### Q15. You are writing an `/effort` clause into your sub-agent spawn prompt to bump its thinking budget. The hook blocks. Why?

A. `/effort` tokens are CEO-only (the outer turn). Sub-agents inherit
   Anthropic's default thinking budget. See ADR-050 §7 and
   `check_agent_spawn.py::_has_effort_token`.
B. `/effort` is deprecated; you should use `/thinking` instead.
C. The tokens must be enclosed in `<effort>…</effort>` tags.
D. Owner must sign the effort override for canonical-5 archetypes.

<details>
<summary>Answer</summary>

**Correct: A.** Sub-agents budget is Anthropic-default; the CEO uses
`/effort` on the outer turn when the orchestration is cognitively
heavy. Leaking the token into a spawn prompt is blocked mechanically.
</details>

### Q16. Two agents in a parallel dispatch both claim the same file in their `## FILE ASSIGNMENT`. What should happen?

A. Both edit — Git handles merges.
B. The CEO must declare zero-overlap before spawning; if files collide,
   run them sequentially instead.
C. Run with `isolation: "worktree"` for both and merge after.
D. The hook auto-serializes collisions.

<details>
<summary>Answer</summary>

**Correct: B.** Anti-collision is a CEO responsibility declared at
Spawn Protocol Step 0. If 1–3 files overlap → sequential; 4+ overlap
→ probably one task. Worktrees (C) are a fallback when collisions are
necessary but the CEO must still understand the overlap. A is just
wrong (no merge tool helps when two agents are deleting each other's
edits live).
</details>

---

## Category 5 — Plan → Debate → Execute (when L1-L2 vs L3+)

### Q17. Your task: rename an internal function in one file. Debate required?

A. Yes — every merge needs at least a Round-1 debate.
B. No — L1 / narrow / one file. Go straight to execute.
C. Yes — any rename is L3 because it breaks all callers.
D. Only if the file is in `.claude/hooks/`.

<details>
<summary>Answer</summary>

**Correct: B.** L1–L2 tasks (1–2 files, contained blast radius) skip
the debate. `PROTOCOL.md` §When to skip debate. A rename is L3 only
if it's an exported symbol touching 3+ modules.
</details>

### Q18. You are about to propose a new ADR that changes the hook lifecycle semantics. Which Plan → Debate step runs?

A. Draft the plan; execute; write the ADR post-merge.
B. `pre-plan-brainstorm` skill (spec.md) → draft the plan → 5-agent
   Round-1 debate → convergence gate → (Red Team if Jaccard ≥ 0.7) →
   Owner review (`reviewed` status) → execute → ADR accepted.
C. Run `/spawn code-reviewer` to evaluate the proposal.
D. Submit the ADR as draft and skip the debate since you are the CEO.

<details>
<summary>Answer</summary>

**Correct: B.** L3+ with ambiguous requirements — brainstorm + full
debate. ADR-058 (brainstorm) can be skipped only for well-precedented
L3+ with unambiguous requirements. Red Team archetype (ADR-032) is
contingent on M1 convergence gate. See `PROTOCOL.md` §Session protocol
Gate 3 step 8.
</details>

### Q19. Debate Round-1 converges with two archetypes flagging the SAME risk. What is the CEO required to do?

A. Note the disagreement and pick the majority recommendation.
B. Adjust the plan to mitigate that risk before proceeding.
C. Spawn a third agent as tiebreaker.
D. Defer the decision to the Owner.

<details>
<summary>Answer</summary>

**Correct: B.** If 2+ agents agree on a specific risk the CEO MUST
adjust the plan. That's consensus — the CEO does not get to overrule.
See `PROTOCOL.md` §Debate Rules, item 2.
</details>

### Q20. You're executing and discover your `FILE ASSIGNMENT` is wrong (you need to edit a file assigned to another agent). What do you do?

A. Edit it anyway; the CEO will notice post-merge.
B. STOP and report to the CEO. The CEO re-plans the file assignment.
C. Open an SP-NNN proposal.
D. Create a branch to isolate the edit.

<details>
<summary>Answer</summary>

**Correct: B.** Anti-collision is mechanical. If the assignment is
wrong the CEO re-slices the work. Silent deviation (A) is exactly the
failure mode the assignment is designed to prevent.
</details>

---

## Category 6 — 3-Strike policy (what counts, what doesn't)

### Q21. An agent's output includes "done" but key files are missing. Strike?

A. Yes — incomplete output is a strike.
B. No — it's a communication lapse, not a technical error.
C. Yes, but only for the second occurrence.
D. No — verifiable against code means only factual errors count.

<details>
<summary>Answer</summary>

**Correct: A.** Incomplete output (says "done" but files are missing)
is a named strike type. See `PROTOCOL.md` §3-Strike Policy "What counts
as a strike".
</details>

### Q22. An agent uses a different approach than the CEO expected, but the approach works and passes tests. Strike?

A. Yes — failing to follow the plan is a strike.
B. No — a different-but-valid approach is taste, not a strike.
C. Yes, but downgraded to a warning.
D. Only if the CEO's plan was explicitly marked as non-negotiable.

<details>
<summary>Answer</summary>

**Correct: B.** A different approach that works is a judgment call,
not a factual error. See `PROTOCOL.md` §"What does NOT count as a
strike".
</details>

### Q23. An agent's fix breaks two existing tests. Strike?

A. Yes — regression is a strike.
B. No — tests can be brittle.
C. Only if the agent is at 2/3 already.
D. Only the originally failing test matters.

<details>
<summary>Answer</summary>

**Correct: A.** A fix that breaks existing tests is a named strike
type (regression). See `PROTOCOL.md` §3-Strike Policy.
</details>

### Q24. An agent hits 3/3 strikes. What happens?

A. Warning in the next session start.
B. Supervised mode — another agent reviews every output before the CEO
   accepts.
C. **Fired** — the persona is rewritten with a new name and background;
   the score resets.
D. Fired and the archetype is removed from `team.md`.

<details>
<summary>Answer</summary>

**Correct: C.** 3/3 is termination. The archetype stays in `team.md`
(the role is still needed) but the persona gets a new name + background.
Score tracked in `.claude/agent-metrics.md`. Score tracking is per
persona, not per archetype.
</details>

---

## Category 7 — Memory discipline (user / feedback / project / reference)

### Q25. The Owner tells you "we don't use Slack for incident reporting — we use Linear". Which memory type?

A. `user` memory — Owner preference.
B. `feedback` memory — this is a correction to future behavior.
C. `reference` memory — pointer to an external system.
D. `project` memory — current incident state.

<details>
<summary>Answer</summary>

**Correct: C.** Reference memories point to external systems ("Linear
is where incidents live"). A user memory is about Owner's role /
preferences / goals; feedback is a correction to how you approach
work; project is about current ongoing work. See the `auto memory`
§Types of memory rubric in the system prompt.
</details>

### Q26. The Owner says "stop summarizing what you just did at the end of every response, I can read the diff". Which memory type?

A. `feedback` — correction to future behavior. Include the why.
B. `user` — it's about the Owner's preference for reading diffs.
C. Both A and B — write two entries.
D. None — ephemeral session state.

<details>
<summary>Answer</summary>

**Correct: A.** Feedback memories capture corrections that should
shape future sessions. The body includes **Why:** and **How to
apply:** fields. B would duplicate it; the right place is feedback.
</details>

### Q27. Which of these should NOT be saved to memory?

A. Current framework state snapshot (test count, commit SHA, plan
   statuses).
B. Code patterns already documented in `CLAUDE.md`.
C. An Owner decision that affects future sessions.
D. A recurring preference that emerged from correcting you twice.

<details>
<summary>Answer</summary>

**Correct: B.** Code patterns + conventions + architecture are derivable
from the project state; memory should not duplicate them. A is a
project memory (valid). C is user or feedback depending on content.
D is feedback.
</details>

### Q28. You recall a memory that names a helper function `foo_util()`. Before recommending it, what do you do?

A. Trust the memory — memories are forensic-grade.
B. Grep for `foo_util` to confirm it still exists. Memory is a claim
   about the past, not a guarantee about today.
C. Ask the Owner.
D. Update the memory with today's date and continue.

<details>
<summary>Answer</summary>

**Correct: B.** Memories are snapshots — names rot. "Before recommending
from memory" is a named rule in the `auto memory` instructions. Verify
first.
</details>

---

## Category 8 — Audit log (what's captured, what's redacted)

### Q29. An agent spawn carries a prompt that includes `OPENAI_API_KEY=sk-...`. What ends up in the audit log?

A. The full prompt with the key — for forensics.
B. The prompt with the key redacted; the audit log's `redact_secrets`
   module handles ~70 secret patterns.
C. Nothing — spawns aren't audited.
D. A hash of the prompt only.

<details>
<summary>Answer</summary>

**Correct: B.** The redaction layer (see `_lib/redact.py` + its
pattern list) runs before any write to `audit-log.jsonl`. High-entropy
patterns, API keys, JWTs, PII, tokens — all redacted. See
`docs/admin-tooling.md` + the `redact_preview` helper for ingest-path
previewing.
</details>

### Q30. How do you verify the audit log hasn't been tampered with?

A. Compare file modification time with `git log`.
B. Run `python3 .claude/scripts/audit-verify-chain.py
   --log-file ~/.claude/projects/<slug>/audit-log.jsonl`.
C. Recompute SHA-256 of the file and compare to a backup.
D. Check that `hmac: null` is absent from every entry.

<details>
<summary>Answer</summary>

**Correct: B.** The HMAC chain (ADR-055) makes tamper **detectable**
(forgery, reorder, interior deletion, transition-rule violation). Exit
codes: 0 intact, 1 tamper, 2 key missing, 3 malformed, 4 perm. See
`docs/HONEST-LIMITATIONS.md` §7 for what it does NOT defend (tail
truncation, key theft, rollback, co-deletion).
</details>

### Q31. Your CI deploys the framework but `audit-log.jsonl` is missing at `$HOME/.claude/projects/<slug>/`. What does the framework do?

A. Blocks all tool calls until the log is restored.
B. Creates it on the first write (fail-open on infra, ADR-005).
C. Raises an exception.
D. Falls back to stdout logging.

<details>
<summary>Answer</summary>

**Correct: B.** Fail-open on infra (ADR-005). Hooks never block the
user session on infrastructure bugs — parse errors, missing files,
timeouts all log a breadcrumb and emit `{"decision":"allow"}`. The
log is self-healing on first write.
</details>

### Q32. You want an external sink for audit logs (for tamper prevention, not just detection). What does the framework provide out of the box?

A. A built-in S3 uploader.
B. An OTEL sink (`docs/otel-integration.md`) that adopters can wire.
C. Nothing — tamper prevention is out of scope for v1.6.
D. An HTTP POST hook on every write.

<details>
<summary>Answer</summary>

**Correct: B.** OTEL is the recommended path for append-only remote
sink. See `docs/HONEST-LIMITATIONS.md` §7 "What this does NOT defend
(tail truncation, key theft, rollback)" + `docs/otel-integration.md`.
Prevention is adopter-wired, not framework-default.
</details>

---

## Category 9 — Quality profiles (max-quality / balanced / max-speed)

### Q33. `.claude/scripts/set-quality-profile.sh max-speed` runs successfully. What changed?

A. `code-reviewer` and `security-engineer` moved to Haiku 4.5.
B. All non-VETO archetypes (qa-architect, performance-engineer, devops)
   moved to Haiku 4.5; VETO-holders stayed on Opus 4.8.
C. The debate protocol is disabled.
D. Audit-log writes are skipped.

<details>
<summary>Answer</summary>

**Correct: B.** Profiles trade velocity vs quality on non-VETO archetypes
only. The VETO floor is an invariant across all three profiles. See
`docs/QUALITY-PROFILES.md`.
</details>

### Q34. `bash .claude/scripts/set-quality-profile.sh --show` outputs what?

A. A dry-run of the next profile change.
B. The currently active profile and per-archetype model assignment.
C. The full skill inventory.
D. The audit-log tail.

<details>
<summary>Answer</summary>

**Correct: B.** `--show` prints the active profile + each archetype's
model. Useful to sanity-check before an expensive dispatch.
</details>

### Q35. You run the framework in `balanced` mode on a security-sensitive PR. You want extra rigor without escalating to `max-quality`. What do you do?

A. Set `CEO_OPUS_SPOT_CHECK_P1=1` — non-Opus tiers re-audit any P1+
   finding with Opus.
B. Run the PR on `max-quality` for this one change.
C. Manually dispatch a second `security-engineer` for a Round-2 review.
D. Any of A / B / C works; pick the cheapest.

<details>
<summary>Answer</summary>

**Correct: A.** The spot-check flag is orthogonal to the profile and
adds defense-in-depth on P1+ findings from non-Opus tiers. It's the
cheapest and most targeted escalation. B works but is less precise; C
is correct in other contexts but not the orthogonal knob.
</details>

### Q36. A new archetype joins `team.md`. What happens to the profile assignment?

A. The archetype auto-inherits Haiku until mapped.
B. The profile file (`.claude/tier-policy.json`) must be updated to
   explicitly declare the new archetype's model per profile; until then
   dispatch falls back to the hardcoded default (usually Opus).
C. The archetype cannot be dispatched until profiles are updated.
D. The profile file is auto-regenerated by `generate-skill-inventory.sh`.

<details>
<summary>Answer</summary>

**Correct: B.** Explicit beats implicit — new archetypes need a profile
mapping. Until added, the fallback is the safest model (Opus), not the
cheapest. See `docs/TIER-POLICY.md` + `set-quality-profile.sh`.
</details>

---

## Category 10 — Emergency kill-switches (master + per-feature)

### Q37. Everything has gone wrong and you need to disable all non-essential hooks immediately. What do you do?

A. Edit `.claude/settings.json` to remove hooks — persists across
   sessions.
B. Set `CEO_HOOKS_DISABLE=1` in the shell env — master kill-switch for
   advisory hooks. Required hooks (canonical-edit, arbitration-kernel,
   governance floor) stay on.
C. Delete `.claude/hooks/` — nuclear option.
D. `git revert` the commit that added the hook.

<details>
<summary>Answer</summary>

**Correct: B.** Kill-switches are env-flagged precisely so they're
reversible in a shell. A persists the change across sessions (not
ideal for an emergency). C is irreversible and unnecessary. D takes
longer than flipping the flag. The master kill-switch respects the
required-hook floor.
</details>

### Q38. The dynamic tier-policy selector (ADR-064) misbehaves. How many kill-switch mechanisms must you trigger?

A. One — the env var.
B. Two — the env var AND the Owner-signed sentinel file (two-factor
   kill).
C. Three — env var + sentinel + manual git revert.
D. None — the policy auto-reverts on first misbehavior.

<details>
<summary>Answer</summary>

**Correct: B.** Two-factor kill-switch is a supply-chain-hardening
decision (ADR-064 §Kill-switch semantics + C-P0-12 closure). Either
factor alone does not disable the policy — this prevents a single
compromised env from killing VETO governance silently.
</details>

### Q39. You want to disable LightRAG sidecar integration (MCP) for a single session without uninstalling. What's the fastest path?

A. Kill the sidecar process.
B. Remove the entry from `.mcp.json` and restart Claude Code.
C. Set `CEO_RAG_DISABLE=1` for the session (documented kill-switch in
   ADR-062).
D. `git revert` the install.

<details>
<summary>Answer</summary>

**Correct: C.** Per-feature kill-switches exist for every opt-in feature.
Set the flag → retry → re-enable by unsetting. See ADR-062 + the
per-ADR kill-switch table in `docs/ROADMAP.md` / emergency-runbooks.
</details>

### Q40. A hook kill-switch is set but the framework still blocks an edit. Why?

A. The specific hook is in the **required** set (canonical-edit,
   arbitration-kernel, governance-floor) — the master switch doesn't
   disable those. You need a scoped override like a signed sentinel
   (ADR-031) or `CEO_KERNEL_OVERRIDE=<scope> CEO_KERNEL_OVERRIDE_ACK=I-ACCEPT`
   for a single kernel batch.
B. You typo'd the env var.
C. The audit log is corrupted.
D. The cache is stale.

<details>
<summary>Answer</summary>

**Correct: A.** Kill-switches are NOT the same as an override. The
governance floor (canonical-edit sentinel, arbitration-kernel) requires
a scoped Owner authorization, not a bulk disable. This is the defense
that prevents an attacker with shell access from disabling governance
by flipping one env var.
</details>

---

## Interpreting your score

- **36–40 (READY):** proceed to `DAY-1-CHECKLIST.md` and install the
  framework in your target project.
- **30–35 (REVIEW):** revisit `PROTOCOL.md` + the docs cited in the
  answers you missed. Retake after one week.
- **< 30 (NOT READY):** start with `docs/GUIA-COMPLETO.md` (or
  `GUIA-COMPLETO.pt-BR.md`) end-to-end before retaking.
- **Wrong in Category 1 (Governance) or Category 10 (Emergency
  kill-switches):** disqualifying regardless of total score — these
  categories cover blast-radius concerns where a wrong guess in
  production can cause irrecoverable harm. Study those categories in
  depth.

## Cross-references

- `docs/DAY-1-CHECKLIST.md` — install verification (complements this
  understanding verification).
- `docs/CHEAT-SHEET.md` — daily operator commands.
- `docs/GUIA-COMPLETO.md` / `GUIA-COMPLETO.pt-BR.md` — comprehensive
  onboarding guide for non-dev + dev adopters.
- `PROTOCOL.md` — governance contract (the source of truth for most
  answers).
- `docs/HONEST-LIMITATIONS.md` — structural limits (bus factor,
  same-LLM, platform matrix).
- `docs/MECHANISM-SELECTION.md` — decision matrix for picking the right
  framework mechanism (adjacent to governance understanding).
- `docs/QUALITY-PROFILES.md` + `docs/TIER-POLICY.md` — multi-model
  dispatch governance.

---

*Last updated: 2026-04-19. Closes PLAN-037 (ultimate-guide audit
BORROW-3). Maintainer: CEO (Claude). Answers validated against
framework state at HEAD of Session 38; review quarterly or after any
L3+ ADR lands to keep questions + answers in sync.*
