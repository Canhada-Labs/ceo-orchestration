---
plan: PLAN-154
round: 1
archetype: security-engineer
verdict: ADJUST_PROCEED
created_at: 2026-07-06
---

## Verdict

ADJUST_PROCEED — no VETO. My PLAN-153 VETO-floor condition (metadata-only v1)
is already a binding constraint of this plan (§Binding constraints #1), and
the plan's red lines (zero self-activation, mechanical-scan-not-human as the
injection defense, blocking-guard legibility untouchable) are the correct
ones. What remains under-specified is exactly the layer where those red lines
get implemented: the plan says *metadata-only* without defining metadata, says
*injection-scanned* while the file it extends ships an **advisory fail-open**
scanner today, says *fenced one-liners* while the existing lesson→prompt path
renders **unfenced imperatives**, and anchors approval in a data store that
lives **outside every guard this repo has** (`$HOME`, not the repo). The
adjustments below are additive and must land in the ADR draft (note: the
reserved number is **ADR-160**, not the ADR-174 the stub cites — R-SEC-10)
before any item executes.

## Summary (≤ 3 bullets)

- The trust chain of this plan is: unguarded `$HOME` lesson store → cheap-model
  distiller → human review → text injected into `/ceo-boot`, the single
  highest-trust context. Every mechanical control therefore has to bind to
  the **HMAC chain** (content-hash-pinned approvals) and to **closed schemas**
  (capture-time field allowlist, bounded lesson vocabulary), because file-level
  canonical guards cannot protect data under `$HOME` and `redact.py` is
  secret-only by contract.
- The repo already contains both the safe precedent and the unsafe precedent
  side by side: `_lib/guardrail_validator` is the fail-CLOSED boot-channel
  validator (`check_read_injection.py:40-49`), while
  `lessons.py:_scan_lesson_for_injection` is "PURE advisory — it never blocks
  a lesson write" (`lessons.py:174-177`) and `format_for_injection` renders
  `**Remember:** <text>` unfenced (`lessons.py:632-637`). PLAN-154 must
  route through the former and retrofit the latter — both are in SENT-F scope
  anyway.
- The deny-once fact-forcing gate (item 6) and the TTL machinery (constraint 5)
  each have one silent fail-open path the stub does not name: citation
  verification on the release decision (must be fail-CLOSED per the C4 / `_e3`
  precedent, `check_bash_safety.py:429-431` class) and TTL expiry semantics
  (must be terminal EXPIRED, with `created_at` verified against the chain,
  because the store file is attacker-refreshable).

## Risks

- **R-SEC-01 — "Metadata" is undefined; the boundary erodes at capture, and
  the HMAC chain makes any leak permanent.** Severity: **HIGH**.
  Description: Constraint #1 says the observe rail "extends the content-free
  PLAN-125 WS-1 rail". That rail is safe because its fields are a CLOSED
  schema: tool-name enum (raw `mcp__*` string "MUST NEVER reach the wire",
  MF-SEC-1), coarse `DURATION_BUCKETS` (raw ms forbidden, MF-SEC-3), two
  booleans (`tool_lifecycle.py:6-16, 90-97`). A learning loop will want
  trigger context — file paths, error strings, guard names, block reasons.
  None of those are content-free: paths embed usernames/`.env` filenames,
  error strings embed payload fragments, and `redact.py` strips only 9 secret
  classes (its own "What gets redacted" list) — zero PII coverage. Worse,
  anything emitted into the HMAC chain is **undeletable without tamper
  evidence**: a PII field that leaks into an audit event cannot be scrubbed
  later. Enforcing redaction "at read" is therefore the wrong end.
  Mitigation: define metadata normatively in ADR-160 as a **deny-by-default
  field allowlist enforced at CAPTURE** — closed enums, booleans, bounded
  opaque IDs, and hashes only; no free-text field may be added to the rail
  without an ADR amendment. Ship a schema-validator unit that reddens on any
  emitted field outside the allowlist (mirror of the MF-SEC-1 mapper test
  shape).

- **R-SEC-02 — The distiller's read surface is unnamed; the full audit log is
  a textual injection source, the lifecycle rail is not.** Severity: **HIGH**.
  Description: Item 2 says "offline distiller … proposing PENDING candidates"
  without naming what it reads. Constraint #2 correctly marks audit-log
  content as untrusted (it may carry verbatim attacker-influenced citations
  per the PLAN-153 E4 mechanism). But there is a structurally better option
  for v1: if the distiller consumes ONLY the closed-enum lifecycle rail plus
  the closed action-name vocabulary, its **input is injection-inert by
  construction** — there is no attacker-controllable string in a closed enum.
  Every widening of the read surface (free-text block reasons, cited
  instructions, tool payloads) converts the distiller into an
  untrusted-content consumer and drags in the full ADR-175 posture.
  Mitigation: ADR-160 names the v1 read surface = metadata rail + closed
  vocabularies ONLY; any later widening is its own reviewed change. The
  distiller spawn is read-only, no Bash/network, writes only to the pending
  store, and carries the Prompt Defense Baseline regardless (defense in depth
  — its output is still treated as untrusted, R-SEC-05).

- **R-SEC-03 — Boot one-liners: fence-escape is trivial, and the EXISTING
  lesson→prompt path is already unfenced.** Severity: **HIGH**.
  Description: Constraint #3 fences boot one-liners as untrusted data. Two
  gaps: (a) a markdown fence is escapable by content containing backticks or
  newlines — an approved lesson whose advisory text contains ``` breaks out
  of the fence and lands as live prose in the boot prompt; a naive ~1k-char
  truncation can itself split a fence open. (b) The plan fences the NEW boot
  path but the OLD path already exists: `format_for_injection`
  (`lessons.py:620-644`) renders `## PAST LESSONS` + `**Remember:**
  {lesson.remember_this}` — an unfenced imperative injected into every
  ranked-retrieval spawn today. Fencing boot while leaving the spawn path
  imperative leaves the wider sink open.
  Mitigation: (a) bounded lesson vocabulary excludes backticks and newlines
  outright; render-side asserts single-line + strips fence markers; the char
  cap applies to content BEFORE fencing so truncation can never bisect the
  fence. (b) Retrofit `format_for_injection` to the same fenced,
  data-not-imperative framing in the same SENT-F edit (the function is inside
  the guarded file — zero extra ceremony). (c) Route boot-channel lesson
  content through `_lib.guardrail_validator` — the fail-CLOSED MOIM validator
  already consumed at session boot (`check_read_injection.py:40-49`) — NOT
  through the advisory `check_read_injection` path, which by its own
  docstring never blocks.

- **R-SEC-04 — The lesson store is outside every guard: post-approval
  mutation is a TOCTOU into `/ceo-boot`.** Severity: **HIGH**.
  Description: Lessons live at `$HOME/.claude/projects/<slug>/lessons/*.json`
  (`lessons.py:12-13`) — plain JSON, not in the repo, not canonical-guarded
  (only the *scripts* are guarded, `check_canonical_edit.py:129-132`), not
  git-versioned. `/lesson-review` approval therefore approves a snapshot of a
  file that any process (or any later injected write) can rewrite before
  `/ceo-boot` renders it. Human gate + mechanical scan both run at approval
  time; render time trusts the file. That is a classic TOCTOU on the
  highest-trust surface.
  Mitigation: the approval event written to the HMAC chain carries
  `sha256(trigger + advisory_text)` of the approved candidate. `/ceo-boot`
  recomputes the hash at render and renders ONLY on match; mismatch → drop
  the lesson + surface a yellow/RED integrity flag. Same check in the top-3
  spawn path. This makes the chain — not the mutable file — the integrity
  anchor, which is the only anchor available for `$HOME` data.

- **R-SEC-05 — The pipeline scan the plan requires is fail-OPEN in the file it
  extends; promotion is INPUT, so the promotion scan must be fail-CLOSED.**
  Severity: **MEDIUM-HIGH**.
  Description: `_scan_lesson_for_injection` swallows every import/scan error
  and "never blocks a lesson write" (`lessons.py:164-216`). Acceptable for a
  raw benchmark-failure note; NOT acceptable as the constraint-#2 gate on
  candidate promotion. Per the C4 doctrine codified in CLAUDE.md §4 and the
  `_e3` precedent (`check_bash_safety.py` whole-command gate): content a
  security matcher cannot parse/scan is INPUT and is blocked, not waved
  through. If the injection corpus fails to load at promotion time, the
  candidate must not become PENDING-reviewable.
  Mitigation: two scan points, two postures. Raw observe-write may stay
  advisory (it is telemetry). The **promotion boundary** (distiller output →
  PENDING candidate) is fail-CLOSED: scanner unavailable or scan hit →
  candidate quarantined (terminal state, visible in `/lesson-review` as
  QUARANTINED, never rendered anywhere). Ship the fixture: scanner import
  mocked-broken + promotion attempt → assert refusal.

- **R-SEC-06 — Deny-once gate: three unnamed edges (the flip, the retry
  match, the verification failure).** Severity: **MEDIUM-HIGH**.
  Description: Item 6's "ADVISORY→enforce path with fail-CLOSED citation
  verification" is the right headline, but: (a) the ADVISORY→enforce **flip
  itself** is a guard-behavior change — if it is a bare env/config flag it
  becomes a silent guard-disable/enable surface; (b) "deny-once" implies
  state: if the retry is matched loosely ("similar command"), an attacker
  mutates the command between deny and cited retry and the citation releases
  a different op than the one denied; (c) the fail-CLOSED clause must be
  scoped exactly as PLAN-153 must-fix 2 was: verification failure on the
  RELEASE decision blocks; fail-open is permitted only on the audit-emit
  side.
  Mitigation: (a) the flip is a governed event — settings-backed, sentinel-
  scoped, and audit-emitted on every activation change; (b) deny-once state
  binds to `sha256(normalized command)` + session, expires with the session,
  and a retry releases ONLY an exact-hash match; (c) ADR-160 restates the
  release/emit split normatively and ships the transcript-read-failure →
  BLOCK fixture.

- **R-SEC-07 — TTL semantics: expiry must be terminal, warnings must be
  count-only, and the clock lives in an attacker-writable file.**
  Severity: **MEDIUM**.
  Description: Constraint #5 gives TTL 30d + 7d warning. Three edges: (a) the
  stub never states what expiry DOES — the only safe answer is terminal
  EXPIRED (archive), never any default disposition that touches activation;
  (b) if the 7d warning renders the pending lesson's TEXT in `/ceo-boot`,
  pre-approval untrusted text reaches the boot prompt through the warning
  side door, bypassing the whole approval pipeline; (c) TTL computed from the
  JSON file's `created_at` is refreshable by anything that can write `$HOME`
  — a pending kept alive forever awaiting a tired-reviewer approve.
  Mitigation: expiry → terminal EXPIRED with an audit event; boot warning is
  count-only metadata ("N pendings expire in <7d"), zero candidate text;
  `/lesson-review` verifies `created_at` against the chain's `lesson_write`
  event rather than trusting the file (converges with R-SEC-04's
  hash-pinning).

- **R-SEC-08 — One kill-switch is two kill-switches, and a killed rail is the
  S254 dead-rail class again.** Severity: **MEDIUM**.
  Description: Item 1's "kill-switch env" is fine for the observe rail
  (telemetry, fail-open infrastructure). But this plan also grows an
  ENFORCING surface (item 6 post-flip). A single shared switch — or a naming
  scheme that invites setting both — lets "turn off telemetry" quietly turn
  off enforcement. Separately, an env-disabled rail is silent-by-default:
  indistinguishable from healthy, which is precisely the S254 failure shape
  PLAN-153 Wave E's liveness machinery exists to catch.
  Mitigation: two distinct env vars, documented separately; disabling observe
  never touches the deny-once gate; each rail audit-emits a
  disabled-this-session breadcrumb once so Wave E liveness can show
  RED/yellow for a rail that has been off across a window.

- **R-SEC-09 — E↔F allowlist marker: hook-side self-annotation is a
  self-exemption primitive.** Severity: **MEDIUM**.
  Description: Constraint #6 requires opt-in no-op hooks to "carry the Wave-E
  annotation/allowlist marker so `check_harness_config.py` does not flag
  them". If the marker is a string INSIDE the hook file, then any
  future/injected hook that carries the string exempts itself from the very
  gate built to catch dead or misconfigured hooks — the marker becomes a
  bypass, and Wave E's positive-control guarantee silently excludes exactly
  the files an attacker would want excluded.
  Mitigation: the allowlist lives GATE-SIDE — an explicit path list inside
  Wave E's config/fixture surface (canonical-guarded, sentinel-scoped), keyed
  by hook path, not by in-file annotation. An in-file marker may exist for
  human readability but must not be sufficient. Fixture proves both
  directions per constraint #6: allowlisted no-op passes; NON-allowlisted
  no-op carrying a copied marker still reddens.

- **R-SEC-10 — SENT-F scope under-enumeration + ADR-number drift in the
  stub.** Severity: **LOW-MEDIUM** (but cheap to fix and expensive to hit).
  Description: (a) The stub scopes SENT-F as "`lessons.py` plus any
  `.claude/hooks/**` additions" (PLAN-154:30-32). The guarded family is wider:
  `prune-lessons.py` (where TTL will live), `lesson-restore.py`,
  `lesson_ranker.py`, and `check_confidence_gate.py` are ALL canonical-guarded
  (`check_canonical_edit.py:127-132`), and item 3 (confidence decay) plausibly
  touches the ranker + trips `check-confidence-gate-drift.py`. Per the S258
  lesson, `touched − SIGNED SCOPE = ∅` is checked pre-commit — an
  under-scoped sentinel means a mid-ceremony stall or, worse, pressure to
  land a guard-surface file outside scope. (b) The stub's gate (3) names
  **ADR-174**; the reserved learning-loop number is **ADR-160** (S261 index
  correction). A plan/sentinel/ADR number mismatch breaks the audit
  cross-reference trail and may collide with whoever now owns 174.
  Mitigation: fix the stub to ADR-160 before consensus; SENT-F pre-enumerates
  the full lesson-family guarded set + new hook paths; run the S258
  pre-commit scope assertion on every SENT-F commit.

- **R-SEC-11 — Dampening must be channel-enumerated: some "advisory" output
  is machine-consumed.** Severity: **LOW-MEDIUM**.
  Description: Constraint #4 protects blocking-reason legibility (correct).
  But "advisory output" is not one channel: `check_read_injection` emits BOTH
  a human-facing `systemMessage` AND a structured `injection_flag` audit
  event that downstream tooling consumes (`check_read_injection.py:2-6,
  232-236`). Condensing/dampening a structured field breaks or starves a
  machine consumer — a suppressed `injection_flag` is a suppressed signal,
  not reduced noise.
  Mitigation: ADR-160 enumerates the dampenable channel as human-facing
  advisory PROSE only (systemMessage text, boot advisory lines, with
  ordinal); structured events, audit emissions, `additionalContext` consumed
  by other hooks, and all block reasons are exempt by name.

## Must-fix (blocking)

All must land in ADR-160 (and the plan file) before `status` leaves `draft`;
items 1–4 are conditions on any code execution.

1. **Closed metadata schema, enforced at capture (R-SEC-01).** Deny-by-default
   field allowlist (enums/booleans/bounded IDs/hashes only) with a reddening
   schema test; no free-text field without an ADR amendment. "Redact at read"
   is rejected as a posture — the HMAC chain makes capture-time leaks
   permanent.
2. **Distiller v1 read surface = metadata rail + closed vocabularies only
   (R-SEC-02), and the promotion boundary is fail-CLOSED (R-SEC-05).**
   Scanner unavailable or scan hit → QUARANTINED terminal state, never
   PENDING. Fixture: broken scanner + promotion attempt → refusal.
3. **Boot channel goes through the fail-CLOSED validator with hash-pinned
   approvals (R-SEC-03, R-SEC-04).** Bounded vocabulary excludes
   backtick/newline; cap-then-fence rendering; `_lib.guardrail_validator` on
   the boot path; approval events carry `sha256(trigger+advisory_text)` and
   `/ceo-boot` + the spawn path verify-before-render. Retrofit
   `format_for_injection` in the same SENT-F edit.
4. **Deny-once gate edges named (R-SEC-06).** Governed + audited
   ADVISORY→enforce flip; exact-command-hash retry matching, session-scoped
   expiring state; release-side verification failure = BLOCK (C4/`_e3`),
   fail-open only for audit-emit; transcript-read-failure fixture asserts
   BLOCK.
5. **TTL is terminal and chain-verified (R-SEC-07).** Expiry → EXPIRED
   (+audit event); boot warnings count-only; `created_at` validated against
   the chain's `lesson_write` event at review time.
6. **Gate-side allowlist for E↔F markers (R-SEC-09)** with the
   copied-marker-still-reddens fixture.
7. **Stub hygiene before ceremony (R-SEC-10):** ADR-174 → ADR-160 in the plan
   file; SENT-F scope pre-enumerates `lessons.py`, `prune-lessons.py`,
   `lesson-restore.py`, `lesson_ranker.py`, any `check_confidence_gate.py`
   interaction, and all new `.claude/hooks/**` paths; S258 scope assertion on
   every SENT-F commit.

## Nice-to-have (advisory)

1. Split kill-switch env vars + disabled-this-session audit breadcrumb wired
   into Wave E liveness (R-SEC-08) — cheap, and it closes the "disabled
   forever = looks healthy" residual.
2. Channel enumeration for dampening (R-SEC-11) — one paragraph in ADR-160
   plus a test that a dampened advisory never mutates a structured field.
3. `/lesson-review`'s imperative-detector should reuse the existing corpus
   families (`scan-injection.py`) rather than a new heuristic — one corpus,
   two consumers, no drift.
4. Quarantined/expired lesson files should be pruned by `prune-lessons.py` on
   a schedule so the `$HOME` store does not accumulate flagged content that a
   future tool might naively re-read.

## Unseen by the original plan

1. **The integrity anchor problem.** Every governance control in this repo
   protects files in the REPO (canonical guards, sentinels, git history). The
   learning loop's operative data lives under `$HOME`, where none of that
   exists. The plan inherits six binding constraints but no constraint says
   what makes an approved lesson *stay* approved. Hash-pinned approval events
   in the HMAC chain (R-SEC-04) are, as far as I can find, the only mechanism
   available — this deserves to be a named design principle in ADR-160, not
   an implementation detail.
2. **The old spawn-injection path is in scope whether the plan says so or
   not.** `format_for_injection` + `get_top_k` already inject lesson text
   into spawns today. Any hardening that applies only to the new boot path
   creates a two-tier trust story where the WIDER, older sink is the weaker
   one. Since the file is being opened under SENT-F anyway, the retrofit is
   nearly free.
3. **Injection-inertness as a design lever.** Metadata-only v1 is framed as a
   privacy control (my PLAN-153 VETO-floor). It is ALSO the injection
   control: a distiller whose entire input is closed enums cannot be
   prompt-injected via its input. Naming this in ADR-160 creates the right
   pressure on every future proposal to widen the rail — the proposer must
   account for losing BOTH properties, not just the privacy one.

## What I would NOT change

1. **The six binding constraints as a package.** They correctly encode both
   critics' PLAN-153 requirements as constraints-not-suggestions, and
   constraint #3's "the human filters for usefulness, the machine for
   injection" is the single most important sentence in the plan. Keep it
   verbatim in ADR-160.
2. **Zero self-activation with SP-NNN/soak for instinct→skill.** Unchanged
   red line, correctly restated. This is what separates a learning loop from
   a self-modifying attack surface.
3. **The execution gate ordering in the stub** — Wave E ships (merged +
   positive-control fixtures green, not merely authored/staged), THEN debate,
   THEN ADR, THEN SENT-F, THEN code. The plan's hooks must be born under the
   liveness/positive-control regime, not grandfathered into it.
4. **Denial dampening scoped to advisory output with blocking reasons
   untouchable.** The redesign from PLAN-153 (condensation, not suppression)
   is right; R-SEC-11 only asks it to name its channels.
5. **The stub's success criterion** — "zero writes outside pending stores
   without an approval event in the HMAC chain" — is exactly the right shape:
   falsifiable and fixture-testable. Keep it, and add the R-SEC-04 hash
   verification to the same fixture family.
