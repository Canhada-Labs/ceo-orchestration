<!-- last-reviewed: 2026-06-12 (PLAN-135 W4 D4 session-continuity section; prior 2026-05-27) -->

# Triage REDUCE protocol — evidence-bound adversarial verification for swarm fan-out

> **Status:** reference doctrine (PLAN-115 WS-E). Backed by **ADR-141** (ACCEPTED).
> Cross-linked from `core/ai-llm-orchestration`. This is the **REDUCE-side**
> companion to the **MAP-side** worker return-status contract in
> `.claude/team.md` §AGENT SPAWN PROTOCOL (PLAN-115 WS-C).

## Why this exists

When the CEO fans a task out across many shards (PLAN-112/113 ran 8–31), the
risk is not the MAP step (each shard does bounded work) — it is the **REDUCE**
step, where shard outputs are merged into a verdict. A summary-merge that
accepts or drops findings without re-checking evidence is a **laundering point**:
PLAN-113's Codex anti-laundering pass reopened 4 "laundered" drops, and PLAN-114
found ~57% of a 307-finding backlog was already stale on re-verification. The
lesson is **scale the proof surface, not the agent count**: verification effort
should grow with risk and drop-rate, not linearly with fan-out.

This protocol formalizes REDUCE as an **evidence-bound adversarial verification**
step, not a summary merge.

## Mandatory shard-output schema (8 fields)

Every shard returns a list of findings; each finding MUST carry all 8 fields:

| Field | Type | Notes |
|-------|------|-------|
| `finding_id` | string | stable id within the run |
| `map_key` | string | which shard / axis produced it |
| `disposition` | enum | `fix` / `accept` / `fixed-confirmed` / `dup` / `moot` / `defer` |
| `evidence_kind` | enum | `file_line` / `grep` / `test_run` / `audit_event` / `none` |
| `evidence_pointer` | string (redacted) | e.g. `path:line`, a test id, an audit `finding_id` — NOT prose |
| `confidence` | integer **basis-points** (0–10000) | **never a raw float** |
| `risk_tags` | list (redacted) | e.g. `security`, `canonical`, `cosmetic` |
| `author` | string (redacted) | shard model / rail id |

**Sanitization (Sec-C7).** The free-text fields that re-enter the reducer prompt
OR an HMAC-covered audit emit — `evidence_pointer`, `risk_tags`, `author` — MUST
be redacted/length-bounded exactly as `audit_emit.py` already treats
`desc_preview` / `reason_preview`. `confidence` MUST be an **integer
basis-point** (0–10000), never a raw float: a float in an HMAC-covered emit
raises `CanonicalJsonError`, which `audit_emit._write_event` catches by writing
the event with `hmac=null` + `hmac_error` and breadcrumbing to
`audit-log.errors` — i.e. the event persists but loses HMAC coverage, weakening
tamper detection (and flooding the errors sidecar). That is the S164
float-in-HMAC class — see [[feedback-float-in-hmac-is-a-class-scan-the-live-errors]].
Encode any rate as `_bps`, any money as `_cents`.

## Reducer rule

1. **No accept and no drop of a finding without evidence.** A disposition with
   `evidence_kind: none` is not reducible — it is re-opened or escalated, never
   silently merged.
2. **Security and canonical findings require an INDEPENDENT adversarial review**
   — ideally on a *different model / rail* (e.g. the Codex pair-rail), because
   same-model shards share correlated blind spots (PROTOCOL.md §Honest
   limitation: same-LLM).
3. The reducer consumes **typed evidence pointers, not shard free-prose.**
4. **Hard anti-pattern:** _an evidence-free summary merge is a governance
   failure._ "All 30 shards agreed, shipping" is not a verdict; "each drop
   traced to `path:line` or a test id" is.

The precise import is **critical-path orchestration with typed evidence
contracts**, not "MapReduce" (which undersells the verification half).
Verification scales by **risk + drop-rate**, NOT linearly with fan-out: 100% of
`security` / `canonical` / `defer` / `fixed-confirmed` drops are verified;
cosmetic `P3` is sampled; escalate automatically when shards disagree or
drop-density spikes (see Failure mode (c)).

## Metrics — two observability tiers (avoid false-green)

**Tier-1 — derivable NOW from audit-log timestamps** (no new wiring):

- `critical_steps` — the **longest dependency branch per stage** (critical-path
  / Amdahl), NOT the total step count. Total steps overstate parallelism.
- `parallel_width` — peak concurrent shards.

**Tier-2 — requires the 8-field schema wired as typed `audit_emit` events**
(until then these are hand-calculated from prose = false-green, do NOT report
them as measured):

- `drop_reopen_rate` — fraction of drops the adversarial review re-opens.
- `evidence_missing_rate` — fraction of findings with `evidence_kind: none`.
- `reducer_disagreement_rate` — fraction where reducer ≠ shard disposition.

## Failure modes (each with a CONCRETE mitigation — no slogans)

**(a) Straggler economics.** The slowest shard owns wall-clock, so *better
sharding beats more shards*. Concrete sub-rules:
- shard-size target: **≤ N findings per shard**, with N calibrated from history
  (S167 ran ~124 survivors over 7 shards ≈ ≤20/shard as a starting N);
- straggler-detection: a shard taking **> 2× the median peer latency** is a
  straggler;
- split-or-not: split a straggler only if its work is independently
  partitionable (no shared write target); otherwise let it run and narrow N next
  time.

**(b) Correlated hallucination.** Same-model shards share blind spots → route the
`security` / `canonical` verifier to a **different model / rail** (Codex
pair-rail). A unanimous same-model verdict is not independent evidence.

**(c) Reducer capture.** The reducer is a single laundering point → it must
PROVE each drop from raw evidence, not shard prose. **Serialization guard
(Perf-R2):** proving *every* drop serializes the reducer into the new
bottleneck when drop-density is high (PLAN-114 hit 57% stale). When
**drop-density ≥ 40%**, switch to a **two-pass reducer**: pass-1 triages by
`risk_tags` + `evidence_kind` (cheap), pass-2 adversarially verifies only the
security/canonical/defer subset + a sample of the rest.

**(d) Prompt-injection propagation.** A malicious source seen by one shard can
enter the reducer bundle. **Bound to the EXISTING scanner (Sec-C6):** every
shard-output field that re-enters the reducer prompt MUST pass
`_lib/injection_patterns.scan_harness_mimicry()` (families: `harness_mimicry` /
`provider_tokens` / `role_preamble` / `directive_prose`). A hit **quarantines
that shard → escalate; never silent-drop.** The reducer consumes typed evidence
pointers, not shard free-prose.

## PARL import = INSTRUMENTATION, not training (non-goals)

The S163 analysis (Codex-validated convergence; external sources unverified —
see Provenance) characterized the Kimi swarm's advantage as **PARL, a train-time
policy** baked into the weights, which prompt orchestration (this framework,
CrewAI, AutoGen) can imitate at the interface/metrics level but not reach without
training. Treat that as the analysis's framing, not an independently verified
fact about Kimi. The actionable, internally-grounded takeaway either way: the
cheap import is **instrumentation** — critical-path accounting (`critical_steps`)
+ serial-collapse / fake-parallelism detection.

**Explicit non-goals:**
- NOT a bigger swarm (write-path parallelism is dependency-graph-bound, not
  agent-count-bound — integration, canonical files, tests, GPG sentinels,
  audit-chain integrity, and release tags stay on the critical path).
- NOT training a decomposition policy.
- NOT reframing this framework as "adopt swarm" — that is cargo-culting/overhead
  for our coupled, high-error-cost workload.

## Provenance + attribution (AC-E4)

This protocol's load-bearing claims trace to **internal precedent** — the
PLAN-112/113 fan-out (author/reviewer split + Codex anti-laundering that
reopened 4 laundered drops) and the S164/S167 burndown experience — **not** to
the external analysis. The Moonshot "Kimi Agent Swarm" (K2.6 / PARL) is cited as
**inspiration only** (ADR-058 attribution style). External Kimi URLs and a
plan-filename-with-line-numbers cited during the S163 analysis were **NOT
independently verified** and are deliberately **not referenced as fact** here.
Do not add any unverified external citation to this doc.

PLAN-113 is the living experiment — this doc **forward-specifies** the REDUCE
contract; it does not reopen or retro-audit PLAN-113.

## Session continuity across waves (PLAN-135 W4 D4)

Re-briefing is the **dominant cost driver of multi-wave fan-out plans**:
every cold re-spawn re-pays the gate-boot + plan-context brief before the
shard does any new work. Doctrine for MAP/REDUCE arcs that span waves:

- **persona→agentId ledger.** When a wave spawns named shards, record
  `persona → agentId` (the native resume handle) in the plan scratchpad
  (`/memory-scratchpad`). A later wave that needs the SAME shard's
  accumulated context resumes it — `SendMessage` to the named spawn /
  respawn by recorded id — instead of cold re-spawning + re-briefing.
- **`/fork` for context-rich side investigations.** An escalated
  straggler or a disputed drop that needs the reducer's accumulated
  evidence context is a `/fork` of the live session, NOT a cold spawn —
  the fork inherits the evidence trail for free. **Exception that stays
  cold:** the independent adversarial verifier (Reducer rule 2) MUST be
  a cold, different-model/rail start — forking it from the reducer would
  inherit the very correlated blind spots failure mode (b) exists to
  break. Continuity is a cost optimization for SAME-context work only;
  it never substitutes for independence.
- **`--fork-session` for A/B arms.** When comparing shard or reducer
  variants, fork both arms from one session so the briefing is
  byte-identical — the canonical briefing-variance killer (instrument
  shape per the PLAN-134 W3 pilot instruments).
- **Post-crash:** `claude --continue` restores the **CONVERSATION**;
  `/resume PLAN-NNN` restores the **PLAN** (derived graph + scratchpad).
  Run both before re-spawning anything — the on-disk shard outputs +
  audit log remain the ground truth for what each wave already proved.

## See also

- MAP-side worker return-status contract: `.claude/team.md` §AGENT SPAWN PROTOCOL.
- ADR-141 (REDUCE protocol decision + attribution).
- `core/ai-llm-orchestration` §Independent LLM Output Audit (the same-rail-audit discipline).
- Internal precedent: PLAN-112 / PLAN-113 triage ledgers + anti-laundering.
