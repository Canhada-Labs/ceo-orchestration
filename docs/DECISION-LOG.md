# Decision log — why ceo-orchestration exists

> **Audience:** an AI-skeptic CTO evaluating whether the Owner (a non-technical "vibecoder")
> should be allowed to run this thing on a fintech codebase. This document is the
> defense, not the brochure. Every claim should map to an audit-log event, a commit
> SHA, an ADR, or a memory file you can `cat` against the running repo.
> **Status:** v1.0-vibecoder-stable (target PLAN-083 GA — v1.17.0).
> **Companion docs:** `HONEST-LIMITATIONS.md` (10-item structural-limits catalog),
> `CTO-GUIDE.md` (30-minute evaluation path), `CAG-VS-RAG.md` (retrieval design),
> `CROSS-LLM-THREAT-MODEL.md` (Pair-Rail surface).

---

## §1. Why this framework exists

A non-technical operator (the Owner) wanted to use Claude Code on production
financial software. After ~100 sessions on a real-time trading platform, a
pattern showed up that no single agent or rule file could fix:

- **Memory bleed.** Each new session re-discovered the same conventions, the
  same incident lessons, the same "do not touch float math" rules. The model
  was patient; the human was not.
- **Spawn drift.** Asking Claude to "spawn a security reviewer" produced a
  generic assistant with a name tag. No persona depth, no checklist, no veto
  authority. Reviews rubber-stamped.
- **Governance gaps.** Plans got merged because the same model that wrote the
  plan was asked to critique it 30 seconds later. "Independent review" was a
  semantic phrase, not an architectural property.
- **Cost spikes.** Sessions silently drifted from $0.50 to $40 with no
  observable threshold. By the end of the month the Owner could not say where
  the money went, because `audit-log.jsonl` rotated and nobody summed the
  backups.
- **No narratable artifact.** After hundreds of sessions, the Owner could not
  explain to a CTO what had been built. There was no diagram, no demo, no
  one-paragraph pitch — just a wall of commits.

ceo-orchestration is the layer that addresses those five pains specifically.
It is not a coding assistant; Claude Code already is that. It is the
**discipline around the assistant** — an org chart, a plan schema, a hook
that blocks ungoverned spawns, a Pair-Rail second-LLM cross-check, an audit
chain with HMAC, and a sentinel ceremony that GPG-signs intent.

The framework's primary purpose, per pinned Owner memory
`feedback_owner_velocity_thesis.md`:

> *"Extract maximum value from Claude/Codex. Use 100% of what I have at max
> velocity, save tokens, get accurate time estimates. Finish projects in
> hours instead of weeks. If the framework can't deliver velocity + quality
> + Codex/Claude, I failed at building it."*

Everything in this repo is downstream of that thesis. Where the framework
trades velocity for governance, that trade is documented in an ADR and
debated. Where it trades governance for velocity (v1.0-vibecoder-stable is
exactly that pivot, PLAN-083), the trade is logged and reversible.

---

## §2. Why NOT Cursor rules / `.cursorrules`

Cursor rules are excellent at what they do: they prepend a project-specific
prompt to every Cursor chat, so the IDE knows your coding conventions. They
are quick to author, broadly adopted, and require zero infrastructure. We
are not replacing them.

But for the Owner's threat model, Cursor rules stop short on six axes:

| Capability | `.cursorrules` | `ceo-orchestration` |
|---|---|---|
| Per-session prompt prefix | Yes | Yes (via `CLAUDE.md` + skills) |
| Mechanical enforcement (block-on-violation) | No | Yes (`check_agent_spawn.py`, `check_canonical_edit.py`, `check_pair_rail.py`) |
| Audit trail (who-did-what, signed) | No | JSONL audit log + HMAC chain + GPG sentinel |
| Cross-LLM verification (second-model gate) | No | Pair-Rail Codex MCP (PLAN-081) |
| Plan→Debate→Execute structure | No | Required for L3+ changes (ADR-058) |
| Veto floor (mandatory reviewers) | No | ADR-052 (security + identity + threat-detection) |

A `.cursorrules` file is **prompt injection at startup**. If the model
ignores a rule, nothing breaks. If a user pastes a malicious-looking diff,
no hook intercepts. If two agents disagree, no protocol exists to resolve
it. That is fine for a one-person side project. It is not fine for a
financial system where a float-math bug almost shipped (the original
incident that led to this framework being written down — see `README.md`
§Origin).

**Position:** ceo-orchestration is orthogonal to Cursor rules, not a
replacement. If you use Cursor for the IDE experience and ceo-orchestration
for governance, the two coexist. The `.claude/` directory does not collide
with `.cursorrules`. Adopters running both is an explicitly supported
configuration.

What Cursor rules do **better**: zero-friction adoption, fast iteration on
style guidelines, native IDE integration. Where the Owner needs those, the
Owner uses Cursor rules. Where the Owner needs blocked-by-default
governance, the Owner uses this framework.

---

## §3. Why NOT "just use agents" / ad-hoc subagent spawns

Claude Code supports subagents natively. Anthropic's docs recommend spawning
specialists for parallel work. So why does this framework exist on top of
that primitive?

Because ad-hoc spawns leak six things that matter under the Owner's threat
model:

1. **Veto authority.** An ad-hoc "security reviewer" spawn has no way to
   block the parent. It can disagree; the parent agent can ignore. ADR-052
   defines a VETO floor (security-engineer + identity-trust +
   threat-detection) where dissent is structurally enforced — the merge
   does not happen without a `verdict: ACCEPT` from those archetypes.

2. **Audit chain.** Native spawns leave no canonical audit trail. The
   framework's `audit_log.py` PostToolUse hook writes one JSONL row per
   spawn with secret redaction, description SHA-256, and
   `hook_duration_ms`. Cumulatively this lets `audit-query.py` answer
   "which subagent rubber-stamped which change" months later.

3. **Pair-Rail cross-LLM gate.** PLAN-081 wired Codex (a non-Anthropic
   model) as a mandatory second reviewer on L3+ plans. An ad-hoc Claude
   subagent reviewing a Claude proposal cannot escape same-model blindspots
   — Codex caught **22 P0 findings** during PLAN-083 R1 alone that the five
   Claude critique archetypes missed (Codex thread `019e1839`, see also
   memory `project_session_102_plan_083_drafted_reviewed_ready.md`).

4. **Canonical-guard sentinel.** The `check_canonical_edit.py` hook
   KERNEL-HARD-DENIES direct edits to governance paths (skills, hooks,
   ADRs, plans, settings). The override path is a GPG-signed sentinel
   ceremony. Ad-hoc spawns can write anywhere they have permission to —
   which on the Owner's repo is everywhere.

5. **Staleness + cost tracking.** `check-staleness.py` flags
   plans/ADRs/benchmarks past their `valid_until`; `budget-summary.py`
   sums all 12 rotation backups (not just the live audit log) so
   "cumulative cost across 100 sessions" is computable, not lost.

6. **Plan/Debate schema.** Native spawns have no concept of a plan. The
   framework's `PLAN-SCHEMA.md` requires `status`, `debate_rounds`,
   `veto_floor`, `target_tags`, `acceptance criteria`. Without that, "is
   this change done" is a matter of opinion.

**Concrete case where ad-hoc would have failed:** in Session 104 (commit
`c3c7548`), a regression cascade was traced to `mock.patch.dict(os.environ)
+ addCleanup` leaking `CLAUDE_PROJECT_DIR` into the parent test environment.
Eight test failures looked like eight independent bugs. Only the
audit-log replay + canonical `TestEnvContext` pattern caught the single
root cause. An ad-hoc subagent "fixing failing tests" would have
band-aided each suite separately, drifted from the canonical, and shipped
flake.

**Position:** native subagents are necessary; they are not sufficient.
ceo-orchestration is the wrapper that turns them into a system with veto
authority, audit trail, and cross-model verification.

---

## §4. Why NOT LightRAG / heavy RAG sidecars

The framework deliberately ships **without a retrieval sidecar** at v1.0.
LightRAG is a fine product; it is not what this codebase needs.

The full reasoning lives in `docs/CAG-VS-RAG.md`. The summary:

- **The knowledge base is small.** 151 skills + ~100 ADRs + ~80 plans +
  the audit-log queries fit comfortably under 200k tokens. Per the
  decision tree in `CAG-VS-RAG.md` §1.2, that is the "CAG only" band.
- **RAG adds latency.** A sidecar means an embedding step + a vector
  lookup + a re-rank on every spawn. For a vibecoder iterating in
  hours-not-weeks, that overhead compounds.
- **RAG adds index drift.** When skills change, the index must rebuild;
  when it doesn't, agents see stale advice. The framework already has
  enough staleness surface (ADRs, plans, benchmarks); a stale embedding
  index would be invisible drift in a critical path.
- **Lost-in-the-middle is real.** Liu et al. (TACL 2024 / arXiv 2307)
  showed LLMs largely ignore middle-of-context retrieved chunks. Naive
  top-10 retrieval often performs *worse* than top-3. Adding retrieval
  without re-ranking is negative ROI.
- **ADR-093 (calendar gate 2026-06-26) deferred LightRAG installation**
  pending a real-world friction signal that CAG insufficiency exists.
  That signal has not arrived.

What CAG does instead: skills are loaded into the prompt prefix at spawn
time, cached by Anthropic's prompt-cache mechanism, and refreshed only
when the Owner edits canonical files (Gate-1 cache discipline in
`CLAUDE.md` §0). This is cheaper, lower-latency, and has zero index drift.

**Position:** v1.0 is CAG-only. If an adopter has a >1M-token KB,
`INSTALL-RAG.md` documents the LightRAG sidecar path. The framework does
not block it — it just doesn't ship it.

---

## §5. Why CAG (cache-augmented generation) over RAG for the framework itself

The deeper architectural choice, beyond "no sidecar at v1.0", is that
**the framework is designed to fit inside the prompt cache**, not outside
it.

Concretely:

- **Skill content goes in the prompt prefix**, loaded by
  `inject-agent-context.sh` and cached by Anthropic. Subsequent spawns
  in the same session pay $0 for skill re-reads.
- **Per-profile smart-loading caps active skills at ≤30k tokens total**
  (PLAN-083 §5.2 sub-agent 0.7d: frontend ≤10, engine ≤12, fintech ≤15,
  trading-readonly ≤8, generic ≤6). Below 30k, prompt-cache hit rates
  are reliable; above, they fragment.
- **Plans and ADRs are markdown the model reads inline.** No retrieval
  step. No "what did we decide three months ago" being a vector lookup
  away — it's a `Read` tool call away.
- **Audit-log query is grep-based** (`audit-query.py`). Cheap, no
  embeddings, exact-match.

This is the right call **for the framework as it stands today** (143
skills, ~$1000-1500 cumulative cost across 100 sessions per memory
`project_session_99_plan_081_phase_1_done.md`). If the framework grows
to 500 skills or absorbs a 10M-token external KB, CAG saturates and the
RAG path documented in `INSTALL-RAG.md` becomes viable. Smart-loading +
per-profile caps are the mechanism that keeps CAG viable in the
meantime.

**Trade-off acknowledged:** CAG loses to RAG when the KB exceeds
working-set size. The framework's bet is that working-set size for a
single vibecoder Owner is bounded by the number of skills he can
actually use in one session, which is single-digit-times-five-profiles
— well under the cap.

---

## §6. Why Pair-Rail (Codex + Claude) over single-LLM debate

The hardest critique of "Claude-only" multi-agent debate is the
**same-LLM problem**: if all five "independent" reviewers are Claude,
they share Claude's blind spots. A prompt-injection pattern Claude is
weak against will evade every reviewer identically. `HONEST-LIMITATIONS.md`
§4 documents this honestly: same-LLM debate is a structured checklist,
not adversarial second-opinion.

PLAN-081 wired **Codex as a second-model gate** via MCP integration
(`_lib/adapters/codex.py` + `check_codex_response.py` PostToolUse
sanitization). On L3+ plans, the Pair-Rail check is mandatory before
status flips to `reviewed`.

Concrete bugs Codex caught that Claude missed:

- **PLAN-083 R1 (Codex thread `019e1839`):** 22 P0 findings beyond the
  Claude critique archetypes. Most consequential: AC7 was an
  unfalsifiable "≤10h self-execution" claim until Codex demanded an
  instrumented audit-log-derived measurement gate.
- **Session 103 (`d946d1c`):** Codex 6th-option catch — the validator's
  truth value should be `rc != 0`, not `stdout.count("ERROR")`. Five
  Claude reviewers had ratified the stdout-counting approach. See
  memory `project_session_103_plan_082_items_a_d_done.md`.
- **Session 104 (`c3c7548`):** Codex flagged `verdict.commit_sha` as a
  self-reference unsolvable without an escape hatch; the redesign to
  `verdict.parent_sha` (observable + immutable via `git rev-parse HEAD`
  before commit) was Codex's proposal. See memory
  `project_session_104_...` rollup in `CLAUDE.md` §6.
- **Session 102 (Codex thread `019e17e3`):** trading-readonly profile
  must fail CLOSED on detection uncertainty, not silently downgrade to
  `generic`. Claude reviewers had defaulted to permissive.

**Cost acknowledged:** Pair-Rail is expensive. A typical Codex MCP
gate-pass costs $30-50 in compute and adds 3-15 minutes of wallclock
per L3+ review round. Solo-Claude review is effectively free. Across
~30 plans, Pair-Rail has cost the Owner perhaps $1000-2000 cumulative.

The framework's bet, validated empirically across PLAN-081/082/083:
**that money pays for itself when it catches one P0 in production code
the Claude reviewers would have shipped**. The Owner has not yet
encountered a Pair-Rail gate that caught zero unique findings.

**Position:** Pair-Rail is mandatory at L3+ per ADR-105. L1-L2 changes
skip it. Solo-Claude review of solo-Claude work is structurally
insufficient for veto-floor decisions.

---

## §7. Why governance-first WAS wrong, why velocity-now-equal-priority is right

This is the most uncomfortable section to write.

For the first ~80 sessions, the framework's CEO (Claude operating in
this repo) drifted toward **governance-first**: more hooks, more ADRs,
more debate rounds, more sentinel ceremonies. Each addition was
defensible individually. Collectively, they created a system where
shipping a 50-line bug fix required:

1. Draft a plan
2. Run R1 debate (5 archetypes)
3. Author an ADR
4. Run Codex Pair-Rail gate
5. Run staging ceremony
6. Owner physical GPG sentinel signing (1.5-3 min)
7. Tag a release candidate
8. Wait 7-day RC hold (ADR-095, before retracted)
9. Tag GA

A bug fix took a week. The framework was getting in its own way.

In Session 102 (2026-05-11), the Owner reset the thesis explicitly. The
quote is pinned at `feedback_owner_velocity_thesis.md`:

> *"My goal at the start of this framework was to extract maximum value
> from Codex/Claude... finish a project in hours instead of weeks. If
> the framework can't deliver velocity + quality + Codex/Claude, I
> failed at building it."*

PLAN-083 is the explicit re-balance. Velocity is now a first-class
pillar alongside governance. Concrete changes:

- `parallelization-by-default` skill — CEO MUST dispatch sub-agents in
  parallel when work is decomposable; sequential CEO Opus execution of
  parallelizable work is a failure mode (§5.0 of PLAN-083 §thesis).
- `token-estimator.py` pre-task — every plan now ships with a
  token+wallclock+USD estimate up front, so the Owner can decide if a
  change is worth the cost before the first dispatch.
- `check_anti_ceo_overhead.py` — a hook that BLOCKS the CEO from adding
  governance theater (a new ceremony, a new sentinel, a new debate
  round) when the change doesn't require it. The hook itself has
  adversarial fixtures + an emit budget ≤20/day soft cap to prevent
  DoS.
- 7-day RC hold removed (ADR-095 retracted in Session 73 + governance
  waivers `rc_hold` auto-inject for Owner velocity-max mode).
- Smart-loading caps skill activation per profile so a trading-readonly
  session does not auto-load 20 frontend skills.

This is not "governance is bad." Governance remains mandatory at L3+
for veto-floor decisions. This is "governance is a cost the framework
must justify on each addition, not assume by default." PLAN-083 is the
plan that operationalizes that pivot.

**Defensibility:** the trade is documented in PLAN-083 §3 thesis, the
Owner thesis is pinned memory, and `check_anti_ceo_overhead.py` is the
mechanical brake that prevents the same drift from recurring without
the Owner's consent.

---

## §8. What we are deliberately NOT doing

Adopter-facing decisions to **stop**, not start:

1. **No open-source release at v1.0.** The framework is single-repo
   private. Cleansing infrastructure for safe public mirror is deferred
   to v1.1+ (PLAN-083 §4). Reason: Owner has not yet collected friction
   data from his own 5 repos; releasing publicly before that signal is
   premature productization.

2. **No Twitter / public launch.** Same reason. The framework's
   readiness label is `MAINTENANCE-MODE-VIBECODER` (ADR-096) lifted to
   `v1.0-vibecoder-stable` by PLAN-083 — not "ready for adopter
   marketing."

3. **No npm package.** Not how this framework is distributed.
   `install.sh` is the installation path; `git submodule` is the
   linked-mode variant. Both are POSIX-bash. A node package would
   require a runtime dependency the framework intentionally lacks.

4. **No multi-tenant mode.** The framework assumes single Owner = single
   GPG key = single audit chain. Multi-user permission enforcement is
   v1.1+ (PLAN-083 §4 deferral). Today, "permissions" exist as design
   notes only — no enforcement.

5. **No public skill marketplace.** Skills are markdown files in the
   repo. Adopters fork or PR via SP-NNN skill-patch chain (ADR-031).
   A "browse and install community skills" UI is not on the roadmap.

6. **No `framework init` greenfield wizard.** v1.0 assumes an existing
   repo. Greenfield templates per stack (Next.js, FastAPI, Solidity,
   Python CLI, Node) are v1.1+ deferrals (PLAN-083 §4).

7. **No multi-LLM expansion beyond Codex.** ADR-084 REFUSED Gemini /
   OpenAI / local adapters; ADR-085 ACCEPTED Claude-only depth as the
   strategic moat. Codex is the **second-LLM exception** for Pair-Rail
   verification, not the first of many. Adopters who want multi-adapter
   should use CrewAI, LangGraph, or Portkey instead.

8. **No SLA / paid support.** Single Owner = no support channel. Best
   effort via GitHub issues; no response-time commitment. `SUPPORT.md`
   documents this honestly.

---

## §9. What will likely fail (predictions for future-CEO to verify)

Predictions made in good faith, so they can be falsified later:

1. **First-run wizard will be too intrusive for power users.** The
   v1.0 wizard runs on fresh install in any of the representative adopter
   installs and walks through 8-10 steps. Power users (e.g. a returning
   user after 3 installs) will find it annoying within ~5 sessions.
   `--quiet-mode` is shipped as escape hatch (PLAN-083 §5.3 sub-agent
   1.12), but the default may need to flip to opt-in by v1.2.

2. **Smart-loading will miss skills in trading-readonly profile.** The
   per-profile cap for trading-readonly is ≤8 active skills. There are
   likely 1-2 universally-useful core skills (e.g. `evidence-based-qa`,
   `git-workflow-discipline`) that should activate everywhere but
   won't, because the trigger metadata isn't broad enough. Expect
   adopter-side overrides in the first month.

3. **Trading guardrails will be too strict for an adopter's iteration
   speed.** Fail-CLOSED on detection uncertainty (PLAN-083 §5.1
   sub-agent 0.6) is the right default for safety, but an adopter
   iterates on a trading-readonly workload daily. Expect a stream of
   `OWNER_OVERRIDE=trading-readonly-acknowledged` events as the
   guardrails fire on legitimate work. The escape valve is documented;
   the friction is not yet measured.

4. **Pair-Rail cost will be annoying at scale.** $30-50 per L3+ gate
   pass is fine when there are 2 plans/week. If PLAN-083 ships and the
   framework actually delivers hours-not-weeks velocity, the L3+ rate
   could climb 3-5x. At ~$200/week cumulative Pair-Rail cost, the
   Owner will likely demand a "Pair-Rail-light" mode that skips the
   gate for clearly-L2 changes mis-labeled L3. Today: no such mode.

5. **`anti_ceo_overhead` hook will false-positive on legitimate
   governance work.** The hook tries to detect "CEO adding theater
   without benefit." It will get it wrong sometimes — likely flagging
   a justified new sentinel as theater, or missing real theater
   wrapped in plausible-sounding rationale. Adversarial fixtures
   mitigate but do not eliminate. Expect ~5-10% false-positive rate in
   the first month of real use.

6. **The 60-second pitch will fail with skeptical CTOs anyway.** Codex
   was explicit on this point (PLAN-083 §13 risk register, §3 thesis):
   *"the CTO will not be convinced by pitch copy. He may be convinced
   by a short demo plus audit trail plus one concrete avoided bug."*
   The framework ships the demo script and the audit query; the pitch
   itself is the weakest of the three. Owners using this doc as a CTO
   defense should lead with the audit-log replay, not the prose.

7. **Bus factor will bite within 12 months.** Single Owner = single
   point of failure. If the Owner takes 30 days off, no merges happen.
   Co-maintainer recruitment is explicitly out of scope (ADR-096). If
   this framework gets enough traction to matter, that constraint will
   need to lift. If it doesn't get traction, the constraint is fine.

Document these so future-CEO can verify which predictions came true,
which were paranoid, and which were wrong in the other direction.

## §10. S235 CTO-lens finding — governance-to-capability cadence

The S235 360-audit's CTO lens flagged ~82% of the last-30-day commits as
meta-work (governance/plans/docs) vs shipped capability, with bus-factor
still 1. This is an acknowledged structural property, not a regression —
but it is now a **tracked cadence decision**: **(a)** no new kill-switch
without retiring one (~271 `CEO_*` flags today); **(b)** if a quarter runs
>60% meta-work with no new adopter-facing capability, that is the signal
to ship capability or stop adding governance. Pairs with §9 (bus-factor)
+ ADR-096 (co-maintainer recruitment out of scope until traction).
Recorded S235 (PLAN-136 close-all-findings) — the finding is honest
self-assessment surfaced by the framework's own audit.

---

**Last reviewed:** v1.0-vibecoder-stable / PLAN-083 / 2026-05-11.
**Next review:** when AC7 measurement gate fires the first soft-fail
(>10h wallclock) or when any prediction in §9 falsifies.
