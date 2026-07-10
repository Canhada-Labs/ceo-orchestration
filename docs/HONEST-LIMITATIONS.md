# Honest limitations — ceo-orchestration

**Version:** 1.0.0
**Audience:** CTOs, VP Engineering, security reviewers evaluating adoption.
**Purpose:** disclose every structural limitation up front. If you read
this and decide ceo-orchestration is not a fit, we consider that a win —
a mismatch caught here is cheaper than one caught in week 6.

This document covers **structural** limitations (bus factor, platform,
design trade-offs). Bug-level issues go through PLAN-NNN remediation
plans; see §9 for current remediation status.

---

## 1. Bus factor = 1

**Reality:** one maintainer (the Owner) has write access to `main`.
Review, merge, tag, and release are all gated on that one human plus the
CEO protocol (Claude). There is no second human reviewer.

**Mitigations in place:**

- Every L3+ decision requires an ADR under `.claude/adr/` (171 shipped).
- Plan→Debate→Execute protocol forces 3-5 parallel critique agents before
  any L3+ merge.
- CODEOWNERS on `.github/` + `SPEC/` + `.claude/hooks/` force a review
  even if self-merged.
- Audit log captures every governance decision; drift is detectable.

**What this means for you:** if the Owner is unavailable for 30 days,
nobody merges to `main`. Forks work; patches stack locally. The framework
still runs — your hooks don't depend on upstream availability. But
upstream velocity = 1 person's calendar.

---

## 2. Adopter count = 0 (vibecoder-only by design)

**Reality:** at v1.0.0, **zero external projects** have installed this
framework and run it for 14 days under real workload. Internal dogfooding
only. This is **structural, not a milestone-in-progress**: per ADR-096
the framework is vibecoder-only by design and external-adopter
recruitment is OUT OF SCOPE.

**What signal exists:**

- All friction, false-positive, and cost numbers come from the
  framework's own dogfood repo (`adopter-metrics.py` on internal usage).
- The one external-style efficacy benchmark we ran (PLAN-077, N=17) was
  **indeterminate**: the framework beat raw Claude Code on 6/17 tasks
  (~35%). We publish that null result rather than hide it. A pre-registered
  3-arm benchmark (PLAN-122 WS-0b) is the next gate for an honest
  efficacy claim.

**What this means for you:** claims about "friction budget" and "hook
false-positive rate" are measured on the framework's own dogfood repo,
not on a third-party codebase. If you adopt, you adopt unvalidated —
your friction data is yours alone, with no upstream adopter cohort.

---

## 3. Platform matrix: macOS + Linux only

**Reality:** no Windows support. Not `cygwin`, not `WSL-tested`. The
install scripts use POSIX `/bin/bash`, `grep`, `find`, `sed`. Hook
runtime Python works anywhere CPython 3.9+ runs, but the install pipeline
was never exercised on `Windows PowerShell`.

**What works under WSL:** likely everything, but unvalidated. No CI
matrix entry. No test.

**What this means for you:** Windows-first shops should run WSL2 or
wait for a future Windows-native install path (not currently scoped).

---

## 4. Same-LLM limitation for debate and review

**Reality:** when the framework spawns "independent critique agents" via
`/debate` or `/spawn`, those agents are all Claude (same model family).
The phrase "independent review" is **semantic** — separate conversation
threads, separate prompts, separate skill contexts — not architectural.
A systemic model weakness (e.g. a specific prompt-injection pattern the
model is blind to) will evade every critique agent identically.

**Mitigations in place:**

- **The cross-vendor pair-rail, direction-neutral (ADR-145 / ADR-161).**
  No single model is both the author and the sole reviewer of a canonical
  edit. The pair-rail runs a *second, different-vendor* model over changes
  the first proposes. Under Claude Code the operating model is Anthropic
  and the cross-model reviewer is OpenAI Codex; under the Codex harness
  (PLAN-155) the direction inverts — the operating model is OpenAI Codex
  and the reviewer is Anthropic Claude (`claude -p`, Stop-time + push-time).
  The guarantee is symmetric: whichever vendor operates, the other reviews.
  **Caveat (unchanged in force, direction-neutral):** this reduces
  single-model blind spots; it does **not** eliminate shared-substrate
  failure modes. A defect both an OpenAI model and an Anthropic model make
  — a shared misconception, a class of prompt injection both fall for, an
  industry-wide training-data blind spot — is caught by neither seat. The
  pair-rail buys *cross-vendor diversity*, not *independence*. It is one
  layer; CODEOWNERS, branch protection, CI, and human review at merge are
  the others. (ADR-032 is the Interactive Debate Protocol, unrelated to
  adapters — prior editions of this doc mis-cited it; PLAN-045 F-05-06
  closure.)
- Human Owner intervention is mandatory for L3+ plan promotion (frontmatter
  `status: reviewed` can only be set post-Owner inspection).
- Formal verification (TLA+ + conformance harness) catches a class of
  model-invisible bugs that no LLM critique would find. 45 mutation
  fixtures, 100% kill rate as of v1.0.0.

**Advisor tool is NOT a mitigation (PLAN-135 W4 D7):** Anthropic's
server-side Advisor tool (`advisor_20260301`, beta header
`advisor-tool-2026-03-01`) lets a primary Claude model consult a
secondary model mid-conversation. When the advisor model is another
Claude, that is **same-vendor guidance by construction** — it inherits
every systemic blind spot described above. An Advisor consult **never
satisfies the ADR-145 cross-model VETO**: a `code-reviewer` /
security persona-demand is discharged only by the cross-vendor Codex
pair-rail (or an equivalent non-Anthropic reviewer). Treat Advisor
output as advisory input, never as a review verdict.

**Artifact Paradox (ultimate-guide audit BORROW-4):** polished AI
outputs trigger ~5.2 pp less scrutiny for missing context vs rough drafts
(Anthropic fluency research). Same-LLM debate inherits the bias — a
confident, well-formatted critique from a sub-agent can feel "done" even
when the review itself missed gaps. `PROTOCOL.md` §Artifact Paradox
documents the mitigation rubric (review as junior-engineer work, focus on
what's absent, verify confidence against code, use adversarial framing
per PLAN-034). Human Owner review on L3+ is the only reviewer not
susceptible to this bias.

**Reviewer-unavailable posture (ADR-161, direction-neutral):** if the
reviewer cannot be reached (binary absent, timeout, empty verdict), the
rail records the attempt as `UNAVAILABLE` and does **not** silently approve
and does **not** block forever: it allows with a loud RED-on-absence
breadcrumb, and the push-time gate + CI remain the backstops. A rail that
blocked indefinitely on a broken reviewer would be a denial-of-service on
the operator; a rail that silently approved would be a dead gate. The
honest middle is: record the gap, allow with noise, backstop downstream.

**What this means for you:** the debate protocol is not a substitute for
human senior-engineer review on load-bearing changes. It is a rigorous
preflight, not an approval. Treat fluent agent output with more skepticism,
not less. Which harness hosts the rail (Claude Code or Codex CLI) changes
*who reviews whom*, not this bottom line — see
[degradation-outside-claude-code.md](degradation-outside-claude-code.md)
for the per-rail Codex matrix.

---

## 5. Python ≥3.9 hard floor

**Reality:** `_lib/` modules declare `from __future__ import annotations`
and stick to `Optional[X]` / `Union[X, Y]` syntax. No PEP 604 `X | Y` at
runtime. No `match` statements. No `ExceptionGroup`. This caps feature
velocity at the Python 3.9 subset (ADR-002 invariant).

**Why:** adopter workstations vary. Some run system Python 3.9 (macOS
default on Intel). We refuse to ship a framework that breaks on a
still-supported interpreter.

**What this means for you:** if your team mandates Python 3.12 features
internally, you will need to mentally context-switch when reading
`.claude/hooks/_lib/`. The style is deliberately dated.

---

## 6. Skill-patch governance adds friction (ADR-031)

**Reality:** adopters cannot directly edit `SKILL.md` files under
`.claude/skills/core/` or `.claude/skills/frontend/`. Changes go through
the `SP-NNN` skill-patch proposal chain: fork → propose → `/skill-review`
→ merge. The sentinel `check_canonical_edit.py` hook enforces this.

**Trade-off:** this costs adopters ~30-60 minutes of process for each
skill customization but prevents silent drift. `domains/<profile>/`
skills are adopter-editable; only `core` + `frontend` are canonical.

**What this means for you:** if your team wants to fork, ignore the
sentinel, and iterate fast — do it on a fork or a custom profile under
`domains/`. The governance is opinionated, and the opinion comes from
watching teams drift their linter configs until nothing matches.

---

## 7. Audit log HMAC chain — detection only, not prevention

**Reality (PLAN-023 Phase B / ADR-055):** the audit log at
`~/.claude/projects/<slug>/audit-log.jsonl` ships a per-entry HMAC chain
keyed from `~/.claude/projects/<slug>/audit-key` (32 random bytes, 0600
perms). Chain formula:
`hmac = hmac_sha256(key, prev_hmac || canonical_json(entry_sans_hmac))`.

**What this defends:**

- **Forgery** — any bit flip in a covered field breaks the chain forward.
- **Reorder** — swapping entries produces a different HMAC.
- **Deletion of interior entries** — next-entry HMAC verification fails.
- **Transition-rule violation** — an hmac-bearing entry followed by an
  hmac-less one is surfaced as tamper (one-way rule).

**What this does NOT defend (documented residuals):**

- **Prevention** — HMAC is tamper-evident, not tamper-proof. An attacker
  with filesystem write-access can still tamper; the chain only makes
  it detectable.
- **Tail truncation** — attacker deletes the last N entries; the head
  remains internally consistent. **Mitigation path:**
  external anchor (OTEL shipping / remote append-only sink). Out of
  scope (deferred).
- **Key theft** — attacker with `$HOME` read-access reads `audit-key`
  and forges arbitrary history. Adopter hardening: FS-level ACLs,
  encrypted home, separate service account.
- **Rollback** — attacker restores an older (log, key) snapshot pair;
  the chain verifies clean against the old key. Mitigation out of scope
  (deferred — requires monotonic counter signed to an external store).
- **Log + key co-deletion** — deny-of-forensics. Mitigation requires an
  external sink.
- **Non-framework processes that acquire the key** — no OS-level
  enforcement.

**How to verify:**

```bash
python3 .claude/scripts/audit-verify-chain.py \
  --log-file ~/.claude/projects/<slug>/audit-log.jsonl
# exit 0 → intact; 1 → tamper; 2 → key missing; 3 → malformed; 4 → perm
```

Flags: `--key-file` / `--since N` / `--json` / `--verbose` / `--stdin`.

**Kill-switch:** `CEO_AUDIT_HMAC_DISABLE=1` skips the HMAC path (new
entries ship `hmac: null`). Useful if the chain path shows unacceptable
latency under unusual workloads.

**What this means for you:** the audit log is now forensic-grade for
forgery/reorder/deletion detection. For full tamper-proof forensics
(prevention, not just detection), pair it with a remote OTEL sink
(`docs/otel-integration.md`) or an append-only remote store. See
ADR-055 §Threat Model §Out-of-scope for the complete residual list.

---

## 8. Formal verification is scoped, not universal

**Reality:** TLA+ specs exist for the Circuit Breaker (ADR-044) and one
other component. The **vast majority** of framework logic — skill
loading, plan linting, hooks, adapters — is covered by conventional unit
tests (12000+ collected) + 45 mutation fixtures (100% kill), not by
mechanized proof.

**What formal verification covers today:**

- `_breaker.py` state machine (S1/S2/S3/L1 invariants).
- Hook governance invariants (canonical-edit sentinel non-removal).

**What it does NOT cover:**

- Policy-DSL correctness (grammar-level check only).
- Redact-on-ingest completeness (pattern-list tests only).
- OTEL export pipeline (smoke tests only).

**What this means for you:** do not read "formal verification shipped"
as "the framework is proved correct". It means "this one critical state
machine has machine-checked invariants, and the rest has 12000+ tests".

---

## 9. Remediation status (reference)

All 79 findings from the PLAN-018 audit (4 P0 / 26 P1 / 35 P2 / 14 P3)
are processed under PLAN-019. Closure status is live-tracked in
`.claude/plans/PLAN-019/progress.md`. Dynamic findings surfaced during
remediation live in `.claude/plans/PLAN-019/dynamic-findings.md`. At
publication of this document, P0 and P1 waves are closed; see the plan
tracker for current counts.

---

## 10. emit_<name> registry coverage — 41/92 by design

`_lib/audit_emit.py` ships ~53 typed `emit_<name>(…)` wrappers
(`emit_session_start`, `emit_skill_loaded`, `emit_veto_triggered`, …).
The remaining ~41 of ~92 registered audit-action names route through
`emit_generic(action_name, payload, …)` — a thin pass-through that
performs the same redaction / chain / HMAC pipeline as the typed
wrappers but does not validate per-action payload shape.

**This is intentional, not a defect.** Audit-v2 finding C-18-06
flagged the gap as a structural inconsistency. Per Session 74
disposition (close-cosmetic):

- **Typed wrappers exist** for actions where (a) the payload shape is
  load-bearing for downstream consumers (e.g. `emit_skill_loaded` is
  consumed by `audit-query.py spawn-stats` and must stay shape-stable);
  or (b) the action ships its own contract test in
  `test_audit_emit_<name>.py`.
- **`emit_generic` covers the rest** — actions whose payload is genuinely
  generic (key/value bag, no fixed shape) or whose downstream consumers
  do not assume a shape (e.g. one-off forensic breadcrumbs, ADR-driven
  experimental events that may shift before stabilizing).

Adding 41 typed wrappers would be ~120 LoC of mechanical pass-through
plus ~41 contract tests, with no observable adopter-side benefit:
`audit-query.py` and the OBSERVABILITY.md query patterns key off
`action_name` strings, not Python symbol presence. The audit chain,
HMAC, redaction, and rotation paths are identical between
`emit_<name>` and `emit_generic` (both go through
`_write_event(...)` under the same FileLock).

**Override:** if your adopter-side consumer needs a shape contract for
a currently-generic action, file an issue and we will promote it to
typed in a follow-up. The 41/92 split is not a freeze; it is the
default disposition for actions that have not yet earned a contract.

---

## 11. PLAN number gaps (bookkeeping disposition)

The plan registry has 4 numeric gaps where a `PLAN-NNN-*.md` file was
referenced in scoping but never materialized as a standalone plan. The
work was either superseded, shipped under a different artifact, or
honestly deferred. None of these represent functional gaps.

| Gap | Origin reference | Actual disposition |
|---|---|---|
| **PLAN-016** | "Sprint 16" — referenced in PLAN-017 frontmatter | **Superseded** by PLAN-044 (Full SOTA Audit). PLAN-017 frontmatter explicitly notes: *"PLAN-016 did not materialize; PLAN-044 audit gate replaces it"*. |
| **PLAN-053** | Sub-agent response scanner — drafted in PLAN-059 §4.3 + ADR-077 Phase B | **Functionally shipped** as `.claude/hooks/check_subagent_fabrication.py` (Session 67). Scanner detects 4 fabrication formats observed in PLAN-059 rail anomaly. No standalone PLAN file written; work landed via Session 67 close-everything ceremony. |
| **PLAN-054** | Bash carrier output scanner — drafted in PLAN-059 §4.4 + ADR-077 Phase B | **Functionally covered** by `.claude/hooks/check_output_secrets.py` (PostToolUse, `matcher: ""` — runs on Bash + Read + all tool outputs). Scanner uses `_lib/output_scan.py` LLM01_prompt_injection + LLM08_excessive_agency families which empirically detect the same harness-mimicry / directive-prose / synthetic-tool-call patterns the dedicated scanner would have caught (verified Session 75 closeout). Family-naming convention differs (`LLM01_*` vs `harness_mimicry`/`directive_prose`) but detection coverage is equivalent. |
| **PLAN-055** | Output compression rtk-inspired — drafted in ADR-077 Phase C | **Deferred** per ADR-077: "gated unless bottleneck observed". No bottleneck observed → trigger never fired → honest deferral. |

This list is the authoritative disposition for these 4 numeric gaps.
The framework registry (`scripts/check-plan-registry.py` if added in
future) MAY assert that every numeric gap has a corresponding entry
here.

---

## 12. CEO_SPAWN_SECRET_SCAN — opt-in secret detection on spawn prompts

**Default: OFF.** No spawn prompts are scanned for secrets unless you
explicitly opt in via `CEO_SPAWN_SECRET_SCAN=1`.

**Activation:** export the env var in the shell that launches Claude
Code:

```bash
export CEO_SPAWN_SECRET_SCAN=1
```

**Secret families covered (heuristic patterns):**

- **AWS Access Key** — `AKIA[0-9A-Z]{16}` and related AWS access-key
  identifier prefixes.
- **GitHub Personal Access Token** — `ghp_…`, `gho_…`, `ghu_…`,
  `ghs_…` (40-char body).
- **Google Service Account JSON** — presence of the literal field
  `"type": "service_account"` inside JSON-shaped content.
- **JWT** — `eyJ…` 3-part dot-separated tokens (header.payload.signature).
- **Generic 32+ char high-entropy strings** — Shannon entropy threshold
  triggers on random-looking strings of 32+ chars (catches generic API
  keys / tokens not covered by the named families above).
- **RSA Private Key block** — `-----BEGIN RSA PRIVATE KEY-----` (and
  related PEM private-key headers).

**You should turn this ON if** any of the following apply:

- You have local `.env` files containing API keys for development.
- You have dotfiles with credential snippets such as
  `~/.aws/credentials` or `~/.config/gh/hosts.yml`.
- You are working in a repo whose CI/CD secrets are visible in the
  workspace (e.g. `.envrc`, `secrets.yaml`).
- You routinely paste API responses, log excerpts, or fixture data
  into prompts.

**Threat model:** prevents secret material from being captured into
the spawn prompt → audit log → potential exfiltration channel.
Detection happens **before** the spawn lands; flagged spawns are
blocked and emit an `injection_flag` audit event for forensic review.

**Limitations:**

- Heuristic only — **false positives** are possible (e.g. legitimate
  base64-encoded payloads, fixture data, intentional high-entropy
  identifiers).
- **False negatives** are also possible — custom secret formats not
  covered by the 6 families above (e.g. proprietary tokens,
  vendor-specific key schemes) will not trip the scanner.

If your threat profile demands stronger guarantees, pair this with
filesystem-level controls (encrypted home, ACLs, separate service
account) and a remote OTEL sink for audit-log redundancy.

---

## 13. Audit emission — `emit_generic` literal-action requirement

Post-Session 76 fix B (Codex audit-v3 closure): the `_KNOWN_ACTIONS`
registry checker now requires every action emitted via
`emit_generic("name", …)` to be a **literal string**, not a variable
or computed expression. The registry checker uses AST resolution to
enforce this — it walks the source, extracts literal-string `name`
arguments to `emit_generic` calls (plus `getattr` aliases that
resolve to `emit_generic`), and verifies each appears in
`_KNOWN_ACTIONS`. Any unregistered action is **silently dropped at
the kernel boundary** when emitted at runtime.

**Limitation:** dynamic actions (action names computed at runtime —
e.g. `emit_generic(f"phase_{n}_done", …)` or
`emit_generic(action_var, …)`) are **not supported by design**.
Allowing them would break the orphan-detection invariant: the
registry checker could no longer prove every emitted action is
registered, so the `_KNOWN_ACTIONS` allowlist would degrade from a
static guarantee to a runtime-only check.

**What this means for you:** if you extend the framework with new
audit actions, you must (a) add the literal action name to
`_KNOWN_ACTIONS` in `_lib/audit_emit.py`, and (b) call
`emit_generic("your_literal_action_name", payload)` with the literal
string at the call-site. The CI registry checker will fail the build
if either step is missed.

---

## 14. Speed: the framework does not make sessions faster — fast mode included

**Reality (PLAN-135 W4 D7; kill ledger as stated — not re-litigated
here):** the "orchestration makes coding faster" thesis was
pre-registered and **killed 5-6 times** across the measurement arc —
from the PLAN-123 E2 $250 pilot through PLAN-134 W2 E5 parallel-read
(20/20 quality at ceiling, but p50 **51% slower** and **37% costlier**
than the solo baseline). The framework's honest value claims are
governance, catch-rate, and cost-routing — never wall-clock speed.
The death toll stands.

**Fast mode is not an escape hatch.** Anthropic's fast mode
(`speed: "fast"` model variants — Opus 4.6 only at this writing;
Opus 4.7/4.8 ship no fast variant) is an **API-billed premium lane**:
it bills at API rates above the standard rate card and does not draw
from subscription quota. The framework routes nothing through it
today. Any future fast-mode adoption is a **pilot lane ONLY**, gated
by a PLAN-134 W3-style pre-registration (frozen kill criteria +
falsifier + budget cap) *before* the first paid call — never a quiet
default flip. See `docs/provider-pricing.md` §Fast mode and
`docs/CEO-MODEL-ROUTING.md` §Routing one-liners.

---

## 15. What this document is NOT

- Not a complete threat model. See `docs/threat-model.md` for that.
- Not a SLA. See `docs/READINESS-STATUS.md` for the current verdict
  (`MAINTENANCE-MODE-VIBECODER` per ADR-096) — there is no upstream
  SLA cadence post-v1.11.0. ADR-095 retracted the 14-day CI green +
  30-day no-retag streaks; ADR-093 imposes a 60-day moratorium on
  new refusal ADRs.
- Not a commitment that these limitations will be fixed in version N+1.
  Bus factor 1 is structural per ADR-096 (vibecoder-only by design;
  co-maintainer recruitment OUT OF SCOPE). Adopter count grows
  linearly in time + Owner calendar availability.

If a limitation here would block your adoption and isn't on a fix path,
open an issue or reach the Owner directly. We'd rather know now.
