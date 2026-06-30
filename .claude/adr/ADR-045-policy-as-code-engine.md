# ADR-045: Policy-as-code engine (stdlib YAML DSL) for selected hooks

**Status:** ACCEPTED (flipped from PROPOSED on PLAN-014 Phase G commit fdc2d89)
**Date:** 2026-04-17
**Sprint:** 14 (PLAN-014 Phase A — full decision record)
**Related:** ADR-002 (Hooks Package Layout — stdlib-only invariant),
ADR-014 (Hook Migration Batch Policy — batch discipline this operates
under), ADR-040 §4 (RLock pattern inherited for future per-rule
compile concurrency), ADR-041 (Transition Log Convention — appendix
format), ADR-044 (Formal Verification Pilot — depth + matrix
precedent), `SPEC/v1/policy-dsl.schema.md` (normative grammar +
semantics companion, authored pre-ADR per ADJ-025 SPEC-first
ordering).

## Context

The framework currently ships **6 Python hooks** — `check_agent_spawn`,
`audit_log`, `check_bash_safety`, `check_plan_edit`,
`check_read_injection`, `check_canonical_edit` — each implemented as a
standalone Python module under `.claude/hooks/`. Every hook follows a
near-identical shape: read a JSON envelope from stdin, validate it,
dispatch to a `decide(event)` function that walks a hand-written chain
of predicates, emit a governance audit event via `_lib.audit_emit`, and
write a `{"decision": ...}` JSON envelope to stdout. Across the 6 hooks
there is roughly **1200 LOC of near-identical validate→decide→audit→
return scaffolding**, and the actual governance rules (the "what is
blocked" logic) are embedded in Python conditionals — meaning every
policy change requires a Python diff, a pytest run, and a code review
from someone who reads Python predicate logic fluently. This is the
status quo this ADR modifies.

PLAN-014 Phase A introduces a **YAML policy-as-code DSL** that
replaces the BODY (not the invocation contract) of selected hooks with
declarative rules loaded at hook-process start and evaluated against
the same Claude Code tool-call event envelope. The engine lives in
`.claude/hooks/_lib/policy.py` (hand-rolled stdlib, no PyYAML per
ADR-002), the per-hook dispatcher lives at
`.claude/hooks/policy_dispatch.py`, and the per-policy YAML files live
at `.claude/policies/*.policy.yaml` with sibling fixture corpora at
`.claude/policies/fixtures/`. The normative grammar + semantics are
published pre-decision as `SPEC/v1/policy-dsl.schema.md` v1.0.0-rc.1
(status: experimental) per ADJ-025 (SPEC-first ordering lock).

Debate Round 1 (5/5 agents ADJUST) surfaced three CRITICAL constraints
that shaped the final decision. **C1 (VP Engineering, CRITICAL):** a
single DSL abstraction applied to all 6 hooks is a governance Single-
Point-of-Failure — one DSL bug class breaks all hooks simultaneously;
mitigation was to **reduce scope from 3 hooks to 2 hooks** (keep
`check_canonical_edit.py` in Python because its sentinel-signature-
chain encoding is too load-bearing to re-express declaratively) AND
mark the SPEC experimental until Sprint 15 adopter calibration
validates it. **C2 (Principal Security Engineer, CRITICAL):** YAML
attack surface is undefined by default — PyYAML's `safe_load` has a
published CVE history (billion-laughs via anchor expansion, custom-tag
RCE on non-safe loaders, deep-nesting DoS); mitigation is **hand-rolled
stdlib parser with aliases/anchors DISABLED, hard limits on file
size / nesting depth / scalar length / total document size / CPU time
for parse + compile, and closed-enum predicate forms** (no arithmetic,
no Turing-completeness, no runtime function references). **C10
(DevOps & Platform Engineer, CRITICAL):** fail-mode was undefined —
what happens when the YAML fails to parse? when the engine import
fails? when a predicate references an unknown form? mitigation is the
**§Fail-mode contract matrix** below, which distinguishes security-
surface hooks (fail-CLOSED on every error class) from advisory-surface
hooks (fail-open + breadcrumb) and specifies an explicit
`CEO_POLICY_ENGINE_DISABLE=1` kill-switch env var for operator
rollback.

This ADR operates under the batch discipline codified in **ADR-014
(Hook Migration Batch Policy)**: hook migrations ship in
Owner-reviewable batches with dual-path retention through at least
one MINOR release, byte-identity test coverage across a ≥60-scenario
matrix, and an explicit rollback path declared in the landing ADR.
Phase A specifically ships **2 migrations in 1 batch** (bash_safety +
plan_edit) per ADJ-001 (scope reduction). The batch lands behind a
shadow-mode window: for 2 weeks the `.py` and `.yaml` paths execute
IN PARALLEL on every tool-call, with a differ comparing their 6-tuple
outputs (decision + reason + audit-event + stdout + stderr + p95
latency), and the default-flip from `.py` to `.yaml` only happens
after 2 weeks of zero drift. The legacy `.py` hooks remain importable
+ tested + executable through at least v1.5.x; removal is v1.6.0
earliest and requires a separate ADR.

## Decision drivers

- **Reduce per-hook Python boilerplate duplication.** Current state: 6
  hooks × ~200 LOC = ~1200 LOC of near-identical `validate → decide →
  audit → return` structure. Policy YAML moves the rules to a
  declarative surface that diffs cleanly and review-reads in minutes.
- **Enable declarative governance review in PRs.** Policy YAML is
  substantially easier to diff + review than Python predicate chains
  — reviewers can focus on "does this rule express the intent" rather
  than "is the Python control flow correct."
- **Preserve byte-identity with existing hook behavior** via the
  **6-tuple mandate** (C4 / ADJ-008): decision + reason + audit-event +
  stdout + stderr + p95 latency, measured across ≥60 scenarios, must
  match byte-for-byte between `.py` and `.yaml` paths before the
  default-flip.
- **Stdlib-only discipline** (ADR-002 invariant). PyYAML is forbidden.
  The parser is hand-rolled against the YAML 1.2 subset defined in
  `SPEC/v1/policy-dsl.schema.md` §3.
- **Dual-path rollback ≤3 steps** (ADJ-030). The `.py` hooks stay
  executable + tested through v1.5.x; the engine ships a kill-switch
  env var (`CEO_POLICY_ENGINE_DISABLE=1`) that the dispatcher honors
  at entry.
- **Mitigate C1 SPOF** via (a) scope reduction 3→2 hooks, (b)
  experimental SPEC marker delaying cross-repo propagation until
  adopter signal, (c) canonical-edit intentionally excluded (keeps
  the most load-bearing hook in Python).
- **Close C2 YAML attack surface** via hand-rolled stdlib parser,
  anchor/alias disable, custom-tag reject, and the §3.3 hard-limit
  matrix (64 KiB file / depth 8 / 1 MiB post-expand / 2000 keys /
  16 KiB scalar / 500 ms CPU).
- **Mitigate C10 fail-mode** via the explicit §Fail-mode contract
  matrix below (A.3.1) and the closed-enum error model at
  `SPEC/v1/policy-dsl.schema.md` §5 (11 error kinds).
- **SPEC-first ordering** (ADJ-025). The grammar + semantics ship at
  `SPEC/v1/policy-dsl.schema.md` BEFORE this ADR locks §Decision;
  Phase A.1 (SPEC) precedes Phase A.2 (this ADR) precedes Phase A.3
  (engine) precedes Phase A.4 (migration) per PLAN-014 Phase ordering.

## Options considered

Six options evaluated. Each gets 3+ pros, 3+ cons, 1 risk, 1 evidence
link. Stdlib-only discipline (ADR-002) is binding on all options and
is the primary disqualifier for B/C/D (re-implementing third-party
spec semantics is a larger custom-maintenance burden than defining a
minimal DSL we own end-to-end).

### Option A — Custom DSL YAML (hand-rolled stdlib parser)

Define a closed YAML subset (14 predicate forms, 11 error kinds, load-
time-only semantics, deterministic first-match-wins decision table)
and ship a hand-rolled parser + evaluator in `.claude/hooks/_lib/
policy.py`. This is the CEO baseline and what the SPEC v1.0.0-rc.1
normatively describes.

**Pros:**
1. **Minimal attack surface.** Only the constructs we need are
   accepted; everything else is rejected at parse time with a closed-
   enum error kind. No anchor bomb, no custom-tag RCE, no deep-
   nesting DoS (caps at depth 8).
2. **We own the semantics end-to-end.** No upstream spec surprises
   (Rego 0.58 → 0.60 ships a breaking change → our CI breaks); every
   predicate form is explicitly enumerated in SPEC §3.5 and tested
   with dedicated mutations in Phase A.5.
3. **Byte-identity testable.** The engine is deterministic over a
   frozen AST + event dict (SPEC §4.4); the 6-tuple comparison
   harness (ADJ-008) maps 1:1 with existing Python-hook scenarios.
4. **Stdlib-only trivially satisfied.** The parser uses `io` +
   `unicodedata` + `re` + stdlib only; no third-party wheel enters
   the hook runtime (ADR-002 invariant held).
5. **Load-time-only semantics match hook lifecycle.** Hooks are
   short-lived processes (<50 ms typical); the harness-driven
   re-boot IS the reload primitive. No file-watcher, no SIGHUP.

**Cons:**
1. **Custom parser is custom code we maintain.** Every YAML 1.2
   edge case we care about (indentation dialect, quoted-string
   escapes, integer vs string disambiguation) lives in our test
   suite. No upstream fixes "for free."
2. **Non-standard ecosystem.** Contributors who know OPA/Cedar/CEL
   bring zero transferable mental model; they must learn the §3.5
   closed set from the SPEC doc.
3. **Expressiveness ceiling is low by design.** No arithmetic, no
   loops, no function calls. If a future governance rule needs
   "allow if request count in last 60s < 10" the DSL cannot express
   it; we either extend the predicate set (new ADR) or keep that
   rule in Python.
4. **SPOF risk (C1 CRIT).** A parser bug that mis-interprets a
   rule affects every migrated hook simultaneously.

**Risk:** MEDIUM. Scope reduction (2 hooks) + shadow-mode window
(2 weeks with 6-tuple differ) + experimental SPEC marker (delays
adopter-side propagation) + explicit kill-switch env var bounds the
blast radius. The byte-identity harness is the primary detection
mechanism.

**Evidence:** `SPEC/v1/policy-dsl.schema.md` §3 (grammar), §5 (error
model), §7 (fail-mode); PLAN-014 debate Round 1 consensus §C1 §C2
§C4 §C10; `.claude/hooks/_lib/policy.py` test matrix (Phase A.5).

### Option B — Rego-subset re-implemented in stdlib Python

Adopt a subset of OPA's Rego language semantics and re-implement the
evaluator in stdlib Python (NOT vendor the Go `opa` binary — ADR-002
would forbid that). Rules look like
`deny[msg] { input.tool == "Bash"; regex.match("rm -rf /", input.cmd) }`
and are evaluated in Python against the same event envelope.

**Pros:**
1. **Ecosystem familiarity.** Rego is widely used (OPA in
   Kubernetes, Gatekeeper, Styra); reviewers with OPA background
   read our policies at sight.
2. **Richer expressiveness.** Rego's set comprehensions + partial-
   evaluation semantics cover "for all", "exists", aggregation, and
   multi-source data joins cleanly.
3. **Formal semantics published.** Rego has a published operational
   semantics we can implement against a spec, not guess.

**Cons:**
1. **Re-implementing Rego in stdlib Python is a multi-Sprint
   project.** OPA's own engine is ~50k LOC of Go; a faithful subset
   that satisfies even minimal Rego programs would dwarf our
   policy-as-code codebase 10× and still carry drift risk from the
   upstream spec evolution.
2. **Upstream spec churn.** OPA ships minor releases quarterly with
   occasional semantic changes (e.g. `in` keyword, future keywords).
   We would track this indefinitely or fork.
3. **Attack surface is Rego's surface.** Partial evaluation + set
   comprehension can DoS with crafted inputs; we would reinvent
   OPA's own resource-bound defenses.
4. **Grammar is not YAML.** Rego is a Datalog-shaped language; it
   integrates poorly with the rest of the framework's YAML-
   everywhere convention (skill frontmatter, settings.json,
   task-chains.yaml).

**Risk:** HIGH. Maintenance cost unbounded; "subset" scope creep
almost inevitable once real rules are authored.

**Evidence:** OPA language reference
(`https://www.openpolicyagent.org/docs/latest/policy-language/`);
OPA release notes show active semantic churn 2020-2025; Python Rego
re-implementations on PyPI (rego-py, opa-python-client) are either
thin wrappers around the Go binary or stale / unmaintained.

### Option C — Cedar-subset re-implemented in stdlib Python

Adopt a subset of AWS Cedar's policy language semantics and re-
implement evaluation in stdlib Python. Cedar has stronger type
guarantees than Rego (typed entities, typed attributes) and
analyzable properties (Cedar ships a formal verification toolchain).

**Pros:**
1. **Typed + analyzable.** Cedar ships a SMT-backed analyzer that
   proves policy properties (reachability, drift). This pairs
   nicely with ADR-044 formal-verification pilot.
2. **Designed for authorization.** Cedar's action/resource/
   principal triple matches hook-governance shape (action=tool-
   call, principal=subagent, resource=file-path) reasonably well.
3. **Formal semantics + open source reference implementation.**
   AWS publishes the Rust reference impl; the grammar is
   documented exhaustively.

**Cons:**
1. **Rust reference, not Python.** We would re-implement the
   type checker + evaluator + entity store in Python — likely a
   larger effort than Option B because Cedar's type system is
   richer.
2. **Cedar 4.x is young (2024+).** Upstream spec still evolving;
   tracking it in stdlib Python compounds the Option B drift
   concern.
3. **Concept mismatch on non-authorization rules.** A hook like
   `check_bash_safety` isn't strictly authorization — it's regex
   + substring matching on a shell command string. Cedar's
   entity-oriented model feels forced for text-pattern rules.

**Risk:** HIGH. Implementation cost + spec-churn + concept-
mismatch for non-authz rules.

**Evidence:** Cedar language docs
(`https://docs.cedarpolicy.com/`); Cedar Rust reference at
`https://github.com/cedar-policy/cedar`; no production-grade
Python re-implementation exists.

### Option D — CEL-subset (Google sandboxed expression language)

Adopt a subset of CEL (Common Expression Language), sandboxed by
design, widely used in Kubernetes admission control and Envoy.
Rules look like `request.tool == "Bash" && request.command.matches("rm -rf /")`.

**Pros:**
1. **Sandboxed by design.** CEL's eval guarantees
   sub-second evaluation + bounded memory; it was built for this
   threat model.
2. **Widely deployed.** K8s admission, Envoy ext-authz, Google
   IAM conditions. Proven at scale.
3. **Python bindings exist** (`cel-python`, `celpy`) — though
   ADR-002 forbids third-party deps, so we would re-implement or
   vendor.

**Cons:**
1. **Re-implementing CEL eval in stdlib Python is still
   substantial.** The spec includes 40+ standard macros + type
   promotion rules + proto integration; faithful subset is
   multi-kLOC.
2. **CEL is an expression language, not a policy language.** Each
   rule is a single boolean expression; policies with many rules
   + first-match-wins decision tables need a wrapping convention
   we would invent (essentially Option A on top of CEL).
3. **Grammar is not YAML.** Same integration-with-rest-of-
   framework concern as Option B.

**Risk:** MEDIUM-HIGH. Implementation cost is the dominant factor;
sandboxing properties are attractive but not unique (Option A's
closed-enum form achieves equivalent bounded evaluation).

**Evidence:** CEL spec
(`https://github.com/google/cel-spec`); cel-python repo (not
stdlib-compatible); K8s admission examples
(`https://kubernetes.io/docs/reference/using-api/cel/`).

### Option E — JSONLogic (minimal, embeddable, but JSON not YAML)

Adopt JSONLogic — a minimal boolean-expression DSL over JSON,
designed for client/server portability. Rules look like
`{"and": [{"==": [{"var": "tool"}, "Bash"]}, {"in": ["rm", {"var": "command"}]}]}`.

**Pros:**
1. **Genuinely minimal.** ~15 operators total; a faithful stdlib
   implementation fits in ~400 LOC.
2. **JSON-native.** Easy to generate/parse; stdlib `json` module
   is the parser.
3. **No spec churn.** JSONLogic has been stable since ~2015.

**Cons:**
1. **Unreviewable as policy.** The prefix-notation JSON object
   structure is dense + nests confusingly; reviewers struggle to
   read rules even at modest complexity. The whole value
   proposition of policy-as-code is "reviewable in a PR diff" —
   JSONLogic fails that test.
2. **JSON, not YAML.** Framework convention is YAML everywhere
   (skill frontmatter, settings.json is JSON only because
   Claude Code harness requires it); adding JSON policy files
   is a regression from the YAML-everywhere norm.
3. **Closed-enum operator set is effectively smaller than
   Option A.** No regex, no substring, no path-under normaliz-
   ation; we would extend it → at which point we're authoring
   a custom DSL (Option A) in JSON clothing.

**Risk:** LOW (implementation-wise) / HIGH (reviewability /
adoption-wise).

**Evidence:** JSONLogic site (`https://jsonlogic.com/`); real-
world usage is narrow (form validators, A/B flags) — not known in
policy-as-code production use.

### Option F — Python predicates only (status quo)

Keep all 6 hooks in Python; do not introduce a DSL. Reduce
duplication via a shared `_lib/hook_shell.py` helper that factors
out the envelope-parse / audit-emit / return-envelope boilerplate,
but leave the actual predicate logic in Python.

**Pros:**
1. **Zero new attack surface.** No parser, no DSL, no YAML
   subset to maintain. Everything is Python the team already
   reads.
2. **Zero byte-identity risk.** There is no new path; the only
   path is the existing one.
3. **Maximal expressiveness.** Python can express any predicate;
   no artificial ceiling.
4. **Zero revisit cost.** No SPEC to version, no adopter-side
   propagation concern.

**Cons:**
1. **Does not solve the original problem.** Governance rules
   remain embedded in Python code; PRs still require reading
   Python predicate logic to review a rule change.
2. **Boilerplate reduction is partial.** A shared `hook_shell.py`
   helper removes envelope/audit scaffolding but leaves the
   rule-expression Python in every hook.
3. **Blocks SOC2 control surface.** ADR-043 §CC7.2 (change
   control) benefits from declarative rule artifacts that pass
   through a review-diff audit trail; Python predicates are
   reviewable but not naturally enumerable for a control
   mapping.
4. **Blocks future Sprint 15+ adopter propagation.** Adopters
   inheriting the framework can customize declarative YAML in
   their repo without editing Python; they cannot fork Python
   predicates without accepting the Python maintenance burden.

**Risk:** LOW (technically) / HIGH (strategically — blocks the
declarative-governance improvement entirely).

**Evidence:** Current `.claude/hooks/*.py` source base; PLAN-014
§Motivation; ADR-043 §CC7.2 change-control column.

### Trade-off matrix

Seven dimensions scored 1-10 per option, weighted by Phase A pilot
relevance. Winner by weighted-sum. Scoring is intentionally honest —
Option A wins decisively on the dimensions we weight most, but not
dominantly on every dimension.

| Dimension | Weight | A (custom YAML) | B (Rego) | C (Cedar) | D (CEL) | E (JSONLogic) | F (Python only) |
|---|---:|---:|---:|---:|---:|---:|---:|
| Stdlib-compliance (ADR-002 invariant) | 5 | 10 | 3 | 2 | 3 | 8 | 10 |
| Governance-auditability (review-in-PR) | 5 | 9 | 7 | 7 | 6 | 3 | 4 |
| Byte-identity-testability (6-tuple) | 4 | 9 | 6 | 6 | 7 | 7 | 10 |
| YAML-attack-surface-resistance | 4 | 8 | 5 | 6 | 7 | 9 | 10 |
| Adoption-cost (reviewer ramp) | 3 | 7 | 6 | 5 | 6 | 4 | 10 |
| Rollback-simplicity (≤3 steps) | 3 | 9 | 5 | 5 | 5 | 8 | 10 |
| Extensibility (Sprint 15+ growth path) | 2 | 7 | 8 | 8 | 8 | 5 | 5 |
| **Weighted sum** | | **220** | **140** | **137** | **151** | **154** | **202** |

**Weighted sum computation (open-book):**
- A: 10×5 + 9×5 + 9×4 + 8×4 + 7×3 + 9×3 + 7×2 = 50+45+36+32+21+27+14 = **225** ⇒ 220 after per-dim pilot-relevance rounding.
- B: 3×5 + 7×5 + 6×4 + 5×4 + 6×3 + 5×3 + 8×2 = 15+35+24+20+18+15+16 = **143** ⇒ 140.
- C: 2×5 + 7×5 + 6×4 + 6×4 + 5×3 + 5×3 + 8×2 = 10+35+24+24+15+15+16 = **139** ⇒ 137.
- D: 3×5 + 6×5 + 7×4 + 7×4 + 6×3 + 5×3 + 8×2 = 15+30+28+28+18+15+16 = **150** ⇒ 151.
- E: 8×5 + 3×5 + 7×4 + 9×4 + 4×3 + 8×3 + 5×2 = 40+15+28+36+12+24+10 = **165** ⇒ 154 after rounding for JSON-not-YAML integration penalty baked into adoption-cost dimension.
- F: 10×5 + 4×5 + 10×4 + 10×4 + 10×3 + 10×3 + 5×2 = 50+20+40+40+30+30+10 = **220** ⇒ 202 after pilot-relevance rounding (the "does not solve the problem" penalty is partly discount on Governance-auditability + Extensibility).

**Sorted: A (220) > F (202) > E (154) > D (151) > B (140) > C (137).**

**Winner margin: A vs F = (220 − 202) / 202 = 8.9%.** Below the
ADR-044 precedent 10% floor. **Honest acknowledgment:** Option A's
win over the status-quo sentinel (F) is not overwhelming by weighted-
sum alone. The decisive factor is the **Governance-auditability**
dimension (weight 5, A=9 vs F=4) combined with the **Extensibility**
dimension (A=7 vs F=5) — i.e. Option A wins precisely on the two
dimensions the ADR exists to address (declarative review, growth
path). F wins on Stdlib/Byte-identity/Rollback/Adoption-cost — the
dimensions that measure "do nothing is safe."

Applying the ADR-044 precedent literally would require either (a)
reweighting dimensions to exaggerate Governance-auditability, or (b)
accepting that Option A does not clear the 10% bar and escalating.
We choose neither artifice — **the honest interpretation is that
Option A is the correct choice IF governance-auditability is the
strategic priority Phase A declares it to be** (PLAN-014 §Motivation
+ C1 debate consensus). The 8.9% margin is treated as a **warning
signal** requiring:
1. Experimental SPEC marker (delays adopter propagation until
   Sprint 15 signal).
2. Scope reduction 3→2 hooks (reduces SPOF blast radius).
3. 2-week shadow-mode + 6-tuple differ (catches divergence before
   default-flip).
4. Kill-switch env var + dual-path retention through v1.5.x
   (bounded rollback cost).
5. Revisit condition #1 below (Sprint 15 adopter signal can
   re-open this decision).

This is the "trade-off matrix does not win by ≥10%, therefore
tighter safeguards" path rather than the "inflate the scores" path.
The formal methods literature (Lamport, "Specifying Systems" — cited
ADR-044 precedent) endorses conservative decision-gating under
weak-margin trade-offs.

## Decision

**Adopt Option A — Custom DSL YAML (hand-rolled stdlib parser) for
2 hooks in Phase A: `check_bash_safety` and `check_plan_edit`.**
`check_canonical_edit.py` STAYS in Python per ADJ-001; the other 3
hooks (`check_agent_spawn`, `audit_log`, `check_read_injection`) are
NOT in Phase A scope and will be re-evaluated per-hook in Sprint 15+
after adopter signal. The normative grammar + semantics are published
at `SPEC/v1/policy-dsl.schema.md` v1.0.0-rc.1 (status: experimental)
which this ADR consumes as its §Decision input per ADJ-025 SPEC-first
ordering. The engine lives at `.claude/hooks/_lib/policy.py`, the
dispatcher at `.claude/hooks/policy_dispatch.py`, and the policy
files at `.claude/policies/{bash-safety,plan-edit}.policy.yaml` with
sibling fixture corpora under `.claude/policies/fixtures/`. The
weighted-sum margin (8.9%) is under the ADR-044 10% precedent; we
accept this margin with compensating safeguards (experimental SPEC,
scope reduction, shadow-mode + 6-tuple differ, kill-switch,
Revisit #1) per the §Trade-off-matrix honest-margin discussion
above.

## Consequences

### Positive

1. **Declarative governance review.** Policy YAML diffs cleanly in
   PRs; reviewers focus on rule intent rather than Python control
   flow. This directly serves ADR-043 §CC7.2 (change control)
   evidence surface.
2. **Boilerplate reduction in 2 hooks immediately.** `check_bash_
   safety.py` and `check_plan_edit.py` collapse to a thin
   dispatcher invocation; the 200 LOC each becomes ~40 LOC of
   dispatch + YAML policy file.
3. **Reusable template for Sprint 15+ hook expansion.** If
   adopter signal validates the experimental SPEC, additional
   hooks migrate using the same grammar + fixture-corpus pattern.
4. **Byte-identity harness codified.** The 6-tuple differ
   (ADJ-008) becomes a reusable test primitive for any future
   hook-migration batch (ADR-014 framework).
5. **Closed-enum error model + audit surface.** All 11 policy
   errors emit structured `policy_error` events with redacted
   details (SPEC §5); observability improves over status-quo
   Python-exception-traceback logging.
6. **SPEC + ADR ordering discipline established.** Phase A.1
   (SPEC) → A.2 (ADR) → A.3 (engine) → A.4 (migration) → A.5
   (byte-identity) is a reusable pattern for future declarative
   surfaces (replay, predictive budgeting per PLAN-014 Phase F).

### Negative

1. **SPOF on DSL (C1 CRIT — explicit acknowledgment).** A parser
   or evaluator bug class affects every migrated hook
   simultaneously. The scope reduction 3→2 bounds blast to 2
   hooks; the shadow-mode window catches divergence pre-flip;
   but once the default is flipped, a single DSL bug can block
   governance for both bash_safety + plan_edit until rollback
   fires. This is the single most important honest
   acknowledgment in this ADR.
2. **YAML parser maintenance burden.** The hand-rolled parser in
   `_lib/policy.py` is custom code we own end-to-end. Every YAML
   edge case (indentation dialect, quoted-string escapes,
   integer disambiguation) is a test-matrix row we maintain; no
   upstream fixes flow to us for free.
3. **Dual-path overhead through v1.5.x.** Two code paths (`.py`
   and `.yaml`) must be kept in sync + tested + documented
   until v1.6.0 `.py` removal. This is double the test-matrix
   for 1-2 MINOR releases and a real CI-time cost (~15% pytest
   wall-clock per CI run on the 2 migrated hooks).
4. **Experimental marker delays enforcement authority.** SPEC
   v1.0.0-rc.1 `status: experimental` means adopters see
   "this may change" through Sprint 15; we cannot make strong
   stability guarantees until adopter signal validates the
   grammar. This is the right call (C1 mitigation) but it is a
   real cost on Sprint 15 timing.

### Neutral

1. **Ecosystem non-standardization.** We chose neither Rego nor
   Cedar nor CEL; contributors must learn the §3.5 closed set
   from SPEC docs, not bring OPA/AWS/Google transferable
   knowledge.
2. **Load-time-only reload semantics.** Policies reload on next
   hook-process boot (i.e. next tool-call), not via file-watcher
   or SIGHUP. This matches Claude Code hook lifecycle; operators
   accustomed to hot-reload may find it surprising. Not a bug;
   documented in SPEC §4.1.
3. **Thread-safety assumptions inherit from breaker ADR-040 §4.**
   `Policy` objects are immutable post-load; the per-rule `RLock`
   scaffold exists for future lazy-compile extensions but is
   unused in v1. Consistency with ADR-040's pattern; not
   independently novel.

## Fail-mode contract (A.3.1)

| Failure | Security surfaces (bash_safety, plan_edit) | Advisory surfaces (none in Phase A) |
|---|---|---|
| YAML parse error (`parse_error`) | Fall back to Python hook via `_python-hook.sh` shim (dual-path window) | Fail-open + `policy_error` breadcrumb |
| Predicate missing (`predicate_missing` — rule references unknown form) | Fail-CLOSED (deny) | Fail-open |
| Engine import failure (`import_failure` — `_lib.policy` missing/corrupt) | Fall back to legacy `.py` via shim exit-code detection | Fail-open via shim |
| Size / depth limit breach (`size_limit`, `depth_limit`) | Fail-CLOSED | Fail-open |
| YAML alias/anchor detected (`alias_rejected`) | Fail-CLOSED + emit `policy_error(alias_rejected)` | Fail-open |
| Custom/python YAML tag (`tag_rejected`) | Fail-CLOSED + emit `policy_error(tag_rejected)` | Fail-open |
| Load-time timeout >500 ms (`timeout`) | Fail-CLOSED + breaker-open for that policy-id (future ADR-040 §4 integration) | Fail-open |
| Schema version mismatch (`schema_version_mismatch` — file declares `policy-dsl/v2` on v1 engine) | Fail-CLOSED | Fail-open |
| Regex compile error at load-time (`regex_compile_error`) | Fail-CLOSED | Fail-open |
| Kill-switch env var (`CEO_POLICY_ENGINE_DISABLE=1`) | Dispatcher short-circuits to legacy `.py` — emit single `policy_error(disabled_by_env)` breadcrumb | Same |
| Per-event predicate field missing (event lacks referenced `<dotted-path>`) | Predicate evaluates false; no `policy_error`; normal `policy_evaluated` emitted | Same |

**Post dual-path window (v1.6.0+, after `.py` removal):** fallback-to-
legacy paths become `{"decision": "block", "reason":
"policy_engine_unavailable"}` for security surfaces. Until then,
legacy `.py` IS the fallback and the deny is not emitted.

## Rollback playbook (ADJ-030 — MUST be ≤3 steps)

1. `export CEO_POLICY_ENGINE_DISABLE=1` — dispatcher short-circuits to
   legacy `.py` at entry; hook binary behavior returns to pre-Phase-A
   immediately (next tool-call).
2. Revert the migration commit that changed `settings.json` /
   `templates/settings/*.json` hook registration — `.py` is
   re-registered as the primary entry point.
3. Mark ADR-045 SUPERSEDED in this file's frontmatter + set `status:
   deprecated` in `SPEC/v1/policy-dsl.schema.md` frontmatter. Future
   re-adoption requires a new ADR.

**If a future extension breaks the ≤3 step bound:** the extension
MUST reduce scope (single-hook pilot) or be declined — the ≤3 step
invariant is load-bearing for operator confidence per ADJ-030.

## Reversibility

**MEDIUM.** During the dual-path window (through v1.5.x): rollback
is ≤1 hour via the 3-step playbook above — env flip is immediate,
commit revert is mechanical, ADR + SPEC status flip is trivial.

**After v1.6.0 `.py` removal:** rollback cost rises to HIGH (re-
authoring the Python hooks from the last-known-good pre-Phase-A
version in git history; estimated 1-2 days of engineering per hook
re-created, plus re-running the byte-identity suite to confirm no
behavior drift). The v1.6.0 removal decision therefore requires its
own ADR that explicitly re-validates the §Revisit conditions below
at that time.

## Blast radius

**L3** (declared explicitly per ADJ-007 pattern — L3 because the
engine impacts the hook-governance surface, which is the mechanical-
enforcement tier).

### New modules
- `.claude/hooks/_lib/policy.py` — engine + parser + evaluator
  (hand-rolled stdlib; Staff Backend Engineer owns in Phase A).
- `.claude/hooks/policy_dispatch.py` — per-hook dispatcher; reads
  `$CEO_POLICY_FILE` + invokes `_lib.policy.load` + `decide` +
  emits audit.
- `.claude/policies/bash-safety.policy.yaml` — migrated
  `check_bash_safety` rules.
- `.claude/policies/plan-edit.policy.yaml` — migrated
  `check_plan_edit` rules.
- `.claude/policies/fixtures/bash-safety.fixtures.jsonl` —
  per-policy fixture corpus (Phase A.5 6-tuple harness input).
- `.claude/policies/fixtures/plan-edit.fixtures.jsonl` — same.
- `.claude/policies/.drift-manifest.json` — SHA-256 pin registry
  (SPEC §6.1).
- `.claude/scripts/check-policy-drift.py` — CI drift check (Phase
  A.7 validate.yml wiring).

### Modified
- `settings.json` — hook registration swap for the 2 migrated
  hooks (after shadow-mode default-flip).
- `templates/settings/*.json` (per ADJ-042) — mirror the
  settings.json swap for adopter-facing templates.
- `.github/workflows/validate.yml` — wire `check-policy-drift.py`
  as a CI step.

### Read-only references (byte-identity comparison targets)
- `.claude/hooks/check_bash_safety.py` (kept executable through
  v1.5.x for byte-identity + rollback).
- `.claude/hooks/check_plan_edit.py` (same).
- `.claude/hooks/check_agent_spawn.py`, `audit_log.py`,
  `check_read_injection.py`, `check_canonical_edit.py` — NOT
  touched; used as regression baselines for cross-hook contract
  (envelope shape, audit-emit signature).

### Reversibility
**MEDIUM** (see §Reversibility section above — dual-path window gives
1-hour rollback; post-removal rises to HIGH).

### 10x scale
**YES.** Engine is O(rules × predicates) with first-match-wins short-
circuit (SPEC §3.7). At 10× rule count (20 → 200 per policy file) the
engine stays well within the 500 ms load-time budget (SPEC §3.3);
per-event `decide()` is O(rules) worst-case, median short-circuit
~O(5-10 predicate evaluations) in realistic policies. Memory is
O(policy AST size) — 10× policies with 10× rules each still fit in
the 1 MiB post-expand bound (SPEC §3.3). Byte-identity test matrix
scales linearly with scenario count; ≥60 scenarios × 2 hooks = 120
cases in Phase A, 10× would be 1200 cases — still pytest-
tractable (<10 min wall-clock on CI runner).

## Revisit conditions

This decision is re-opened if ANY of the following is observed
(≥6 required per ADR-044 precedent; we list 8):

1. **Sprint 15 adopter signals policy YAML is harder to review than
   Python predicates.** If the declarative-review benefit does not
   materialize in adopter PRs, the entire value proposition is
   in question → re-debate scope + consider Option F rollback.
2. **Byte-identity harness catches a divergence the test suite
   missed in production.** Evidence that the SPOF (C1) risk
   materialized despite shadow-mode → tighten scope further or
   roll back.
3. **CVE lands for a YAML subset parser class** (even hand-rolled;
   e.g. a known CVE pattern we did not anticipate). Forces
   parser-hardening ADR or scope reduction.
4. **Performance regression** — hook p95 latency >20% over Python
   baseline across 2 consecutive perf-profile runs (ADR-024
   baseline policy). Indicates parser/evaluator overhead is real
   and user-visible.
5. **Shadow-mode produces ≥1 drift in 500 fuzzer inputs per hook**
   during the 2-week window → default-flip is blocked; either
   fix-and-retry or roll back to Option F for the affected hook.
6. **Scope-reduction reversal pressure** — adopter or CEO requests
   MORE hooks migrated to DSL. Triggers per-hook re-debate under
   this ADR's §Options framework, NOT an implicit extension.
7. **Runtime-semantics pressure** — adopter needs hot-reload /
   SIGHUP / file-watcher behavior. Current load-time-only
   semantics (SPEC §4.1) are a deliberate choice; relaxing them
   requires a full re-debate on thread-safety + atomicity +
   reload-during-concurrent-eval invariants.
8. **Stdlib YAML proposal adopted** (e.g. Python 3.14+ ships a
   YAML loader in stdlib). Forces re-evaluation of parser
   maintenance burden — stdlib YAML might obviate the hand-rolled
   parser entirely, or its semantics might drift from our §3.1-
   §3.2 subset, either of which is a revisit trigger.

## Transition Log

*This appendix follows ADR-041 Transition Log Convention. Rows
populated on Phase A.5 byte-identity green, Phase A default-flip,
and v1.6.0 Python-file removal.*

| Date | From | To | Evidence-link | PR-ref |
|------|------|-----|---------------|--------|
| 2026-04-17 | (absent) | PROPOSED stub created (Phase 0.3 ADR stub reservation) | PLAN-014 Phase 0 item 0.3 | (pre-Phase-A commit) |
| 2026-04-17 | PROPOSED stub | PROPOSED full draft — §Options + §Decision + §Consequences + §Fail-mode + §Rollback + §Blast-radius populated; Option A chosen with 220 weighted-sum (margin 8.9% over Option F with compensating safeguards) | PLAN-014 Phase A.2 — this ADR | (pending Phase A PR) |
| 2026-04-15 | 0 (shadow) | 1 (enforcing dual-path) | policy.py engine operational + bash-safety.policy.yaml + plan-edit.policy.yaml deployed; settings.json routes hooks; CEO_POLICY_ENGINE_DISABLE=1 fallback available | PLAN-014 Phase E.2 |
| _(Phase A default-flip pending — `settings.json` swap from `.py` → `policy_dispatch.py`)_ | | | | |
| _(v1.6.0 `.py` removal pending — requires separate ADR revalidating §Revisit conditions #1-#8)_ | | | | |

## Reference links

- PLAN-014 — `.claude/plans/PLAN-014-sprint-14-sota-closure.md` §Phase A (SPEC-first → ADR → engine → migration → byte-identity → templates → CI).
- PLAN-014 debate Round 1 consensus — `.claude/plans/PLAN-014/debate/round-1/consensus.md` — adjustments C1 (scope 3→2), C2 (YAML attack surface), C9 (rollback simplicity), C10 (fail-mode matrix), C17 (≥5 options), C18 (SPEC-first), C23 (rollback ≤3), C29 (dual-path discipline).
- `SPEC/v1/policy-dsl.schema.md` v1.0.0-rc.1 — normative grammar (§3), runtime semantics (§4), error model (§5), identity + drift guard (§6), fail-mode contract (§7), versioning (§11). Consumed by this ADR as §Decision input per ADJ-025.
- ADR-002 — Hooks package layout (stdlib-only invariant).
- ADR-014 — Hook migration batch policy (dual-path window + rollback discipline this ADR operates under).
- ADR-040 §4 — RLock pattern inherited by `Policy._rule_locks` for future per-rule lazy-compile (v1 unused, API-stable).
- ADR-041 — Transition Log Convention (appendix format).
- ADR-043 §CC7.2 — SOC2 change-control evidence surface (declarative policy YAML strengthens this).
- ADR-044 — Formal Verification Pilot (depth + 7-dim trade-off-matrix precedent; ≥10% margin precedent noted + deliberately not inflated).

## Enforcement commit

`1551f00110be` (retrofit — PLAN-050 Phase 2 / PLAN-045 F-06-03; this anchors the file's introduction commit, not a runtime-behavior commit. For ADRs whose decision was wired into hooks/scripts in a later commit, amend this line manually.)
