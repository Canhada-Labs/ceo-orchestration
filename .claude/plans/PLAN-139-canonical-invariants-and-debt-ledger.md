---
id: PLAN-139
title: Canonical Phrase-Deletion Guard + Inline Debt Ledger
status: done
created: 2026-06-18
reviewed_at: 2026-06-18
completed_at: 2026-06-19
related_commits: ["b1fb6f44155f81d1557604cf191ce5dc5743a3bd"]
created_by: "CEO (S243 — ponytail harvest wf_1fd8cce3-293 + premise validation + 6-persona debate wf_87527b04-38d [VETO->resolved] + Codex pair-rail 019edaeb [R1/R2 BLOCK->R3 ACCEPT])"
completed_by: "CEO (S245 — Workflow wf_6d083ec3-6d4 Wave A/B gen + wiring + 3-pass Codex pair-rail [ACCEPT, 5 P2 applied]; landed b1fb6f4)"
owner: CEO
depends_on: []
related_plans:
  - PLAN-110                      # spec-kit adoption sweep — check-docs-drift.py is the count-only sibling this complements
  - PLAN-133                      # G2 foreign-context discovery — WHY AGENTS.md is out of scope (scripts/discover_foreign_context.py)
  - PLAN-134                      # nightly-hygiene SAVED WORKFLOW (.claude/workflows/nightly-hygiene.js) — Wave B is its 8th dimension
  - PLAN-136                      # W3 injection-channel validation — anti-goal grounding (NOT ADR-153)
related_adrs:
  - ADR-107                       # pair-rail mandatory L2+ — gates Wave V
  - ADR-139                       # coverage tiering — new script lands with its own tests
  - ADR-136-AMEND-1               # read-only fan-out confinement — Wave B nightly dimension returns a shard, writes nothing
risk_tier: B                      # Wave A is fail-closed into validate-governance.sh (slow profile); scope reduced post-debate (no canonical-guard, no kernel override, no new ADR)
target_tag: v1.47.0               # tentative — confirm at execution
budget_tokens: 90-170k            # EXECUTION only. Wave A ≈50k (S) · Wave B ≈70k (M) · Wave V Codex ≈40k. Rite (harvest+debate+validation) already spent S243.
budget_sessions: 1
context_risk: low
provenance:
  source_repo: "github.com/DietrichGebert/ponytail (UNTRUSTED, MIT, 34.5k★) — read-only clone analyzed S243; nothing executed, ideas only"
  harvest_verdict: "0 ADOPT / 19 ADAPT (5 distinct) / 21 SKIP — this PLAN folds the 2 highest value/effort ADAPT items, reshaped"
  debate_verdict: "wf_87527b04-38d — 1 VETO (false AGENTS.md-mirror premise) + 12 consolidated fixes, ALL applied below"
---

# PLAN-139 — Canonical Phrase-Deletion Guard + Inline Debt Ledger

> **One-line goal:** two small stdlib scripts that close two verified gaps —
> (A) a **fail-closed deletion/parity detector** that load-bearing security
> phrases are not silently dropped from the *tracked* canonical docs during a
> closeout compaction, and (B) a **derived, advisory** inline-debt ledger
> surfaced by the nightly-hygiene workflow. No new ADR, no new canonical
> path, no kernel ceremony (see §1.5 debate disposition).

## 0. Provenance & honest framing

This PLAN is the only material harvested from an adversarial read of the
**untrusted** repo `ponytail` (S243 Workflow `wf_1fd8cce3-293`). Harvest
returned **zero ADOPT-as-is**. We take **two ideas, reshaped** for our
stdlib-Python governance model, and explicitly reject ponytail's
LOC-reduction claims, ruleset-content injection, and free-text kill-switch
(§6). Nothing from ponytail was executed.

**What Wave A is and is NOT (corrected after debate):** it is a phrase
**deletion / parity detector** for first-party *tracked* docs — it catches a
load-bearing phrase being silently removed (e.g. a careless CLAUDE.md
compaction dropping a Critical Rule). It is **NOT a tamper/security control**:
substring-presence cannot verify surrounding semantics, so a present-but-
neutered phrase passes. Parity tooling, not a guard against a hostile editor
(that actor can edit the checker itself; the real defense is the existing
validate gate + review).

## 1. Validated premise (read-only checks, S243 — corrected post-debate)

| Claim | Evidence | Verdict |
|---|---|---|
| There is exactly ONE tracked canonical agent-context file | `CLAUDE.md` tracked; `AGENTS.md` is **gitignored** (`git check-ignore` ✅) + **never committed** (`git ls-files` → no match) + **CI-absent** | ✅ corrected |
| `AGENTS.md` must NOT be read by a guard | `scripts/discover_foreign_context.py:4,9` — it is a FOREIGN agent-instruction file the framework "honors but NEVER reads contents of" (PLAN-133 G2) | ✅ out of scope |
| Load-bearing phrases live verbatim in CLAUDE.md spine | `Fail-open on infra` (CLAUDE.md:169), `NEVER block the user session`, `## AGENT PROFILE`, `Plan→Debate→Execute`, `stdlib only` — each 1 hit in the stable spine (§0/§5), NOT in §6/CHANGELOG | ✅ |
| ≥1 SPINE phrase lives verbatim in BOTH tracked files (parity has substance) | `3-strike` — CLAUDE.md:27 (§0 GATE-1 spine) + PROTOCOL.md (2 hits). (`Owner-signed` REJECTED — Codex C2: its only CLAUDE.md hit is CHANGELOG:241, volatile) | ✅ demonstrated |
| Nothing guards phrase deletion | `check-docs-drift.py` asserts numeric **counts** only (no AGENTS.md, no phrases); `check_protocol_semver_cascade.py` covers PROTOCOL.md semver only; `translations-pairs.yaml` is PT↔EN only | ✅ gap |
| `fail-open` (lowercase) is the WRONG phrase to pin | appears in CLAUDE.md ONLY at CHANGELOG:288 (volatile); spine phrase is `Fail-open on infra` (:169). Pinning the lowercase form would brick on a changelog reword | ✅ use spine form |
| No structured inline-debt grammar exists | `# ceo-debt:` = **0 hits**; scattered `DEFERRED to PLAN/ADR` + `TODO/FIXME` exist ad-hoc (counts re-measured at execution; do not cite stale numbers) | ✅ gap (future-facing) |

## 1.5 Debate disposition (wf_87527b04-38d — VETO + 12 fixes, ALL applied)

The 6-persona debate issued a **real VETO**: Wave A originally rested on the
false premise that gitignored/CI-absent `AGENTS.md` was a governed mirror.
Resolution applied throughout this revision:

- **F1/F2 (P0)** drop `AGENTS.md` entirely (gitignored + foreign per PLAN-133 G2); re-scope to tracked `{CLAUDE.md, PROTOCOL.md}`. → §1, §2, §3.
- **F3 (P0)** adopter-install would brick: guard must SKIP in adopter context. → US-A4.
- **F4 (P0)** wrong-phrase brick + neuter-substring: use spine `Fail-open on infra`, ban §6/CHANGELOG phrases, reframe as deletion/parity detector. → §0, §3, §2.
- **F5 (P1)** governance-cost claims were false (validate-governance.sh is NOT canonical-guarded; adding to `_CANONICAL_GUARDS` would be a KERNEL-HARD-DENY): **avoided** by choosing in-script phrase constant, no registry file, no `_CANONICAL_GUARDS` change, no ADR. → §3, §5.
- **F6 (P1)** nightly-hygiene is `.claude/workflows/nightly-hygiene.js`, not a SKILL.md. → US-B3.
- **F7 (P1)** no PyYAML (stdlib-only): phrases are an in-`.py` constant; no YAML registry. → §3.
- **F8 (P1)** Wave B per-validate scan = ~1.3s over 14k files (npm mirror not excluded) vs 20s CI timeout: **drop the per-validate step**; nightly dimension is the sole live surface; pin scan scope. → §4.
- **F9 (P1)** add `--repo` override; wire into the SLOW validate-governance.sh (validate_governance_fast runs no bash steps). → US-A1, US-A3.
- **F10 (P2)** NFKC-normalize BOTH phrase and content + collapse whitespace; ≥6 grep-verified phrases. → §3, US-A2.
- **F11 (P2)** run `npm-rebuild.sh` ship-step; fix anti-goal cite to S228/PLAN-136-W3; "same output style" not "shared module". → §5, §6.
- **F12 (P2)** ReDoS hardening: non-backtracking line-anchored regex, inert data, no eval/shell-out. → §4.

Open questions §7 resolved: **Q1 no new ADR**; **Q2 no templates pin (→ Non-goal)**; **Q3 token `# CEO-DEBT:`** (uppercase, line-anchored).

## 1.6 Codex pair-rail disposition (thread 019edaeb — R1 BLOCK + 3 fixes, ALL applied)

Cross-model review (ADR-107) of the post-debate revision returned **BLOCK**
with 3 findings — all empirically re-verified by the CEO and applied:

- **C1 (P0)** adopter-skip via absence of `.claude/adr/` is WRONG —
  `install.sh:1064` ships `.claude/adr/README.md` to every adopter, so the
  guard would NOT skip and would brick adopter installs. → use framework-only
  marker `.claude/adr/ADR-001-runtime-state-directory.md` (§3, US-A4).
- **C2 (P1)** `Owner-signed` violates the spine-only rule — its only CLAUDE.md
  hit is `CHANGELOG:241` (volatile). → removed from the set; `3-strike`
  (CLAUDE.md:27 §0 spine + PROTOCOL.md) remains the cross-file invariant (§1, §3).
- **C3 (P2)** the prune-set is a superset, not the literal `pytest.ini`
  `norecursedirs`. → reworded (§4).

Codex verified OK: `AGENTS.md` gitignored/untracked, the spine phrases present
where claimed, `fail-open` lowercase only in volatile history, `nightly-hygiene`
is the JS saved Workflow, `validate_governance_fast.py` runs no bash steps.

## 2. Non-goals / scope guard

- **Not** byte-equality of whole files; we pin **substrings** of the stable spine only.
- **Wave A operates ONLY on first-party tracked docs** (`CLAUDE.md`, `PROTOCOL.md`). It does **NOT** read `AGENTS.md` (gitignored foreign context per PLAN-133 G2 / `discover_foreign_context.py`).
- Phrases pinned come **only from the stable spine** (GATE protocol / Critical Rules / Spawn protocol), **never** from §6 Current Work or the CHANGELOG.
- **Detects phrase DELETION/parity-loss; cannot verify surrounding semantics** — a present-but-neutered phrase passes. Parity tooling, not a tamper guard.
- **No phrase-pinning into `templates/CLAUDE.md`** — the adopter stub carries only a subset of the spine (verified: 0/5 for several phrases); pinning would red every adopter gate. Guard SKIPs in adopter context (US-A4). Adopter mirroring, if ever wanted, is its own ADR.
- **No new audit-log action / HMAC field / SPEC bump.** No new `_CANONICAL_GUARDS` entry, no new ADR.

## 3. Wave A — Phrase-Deletion Guard (effort S, **fail-closed**)

**Deliverable:** `.claude/scripts/check-rule-invariants.py` (stdlib, py3.9+,
`from __future__ import annotations`) + tests + one fail-closed step in the
**slow** `validate-governance.sh`.

**Design:**
- Phrase list is an **in-script Python constant** — a list of
  `(id, phrase, files, rationale)` tuples. **No YAML, no PyYAML** (stdlib-only,
  ADR-002). ~6 invariants from §1: CLAUDE.md-only (`Fail-open on infra`,
  `NEVER block the user session`, `## AGENT PROFILE`, `Plan→Debate→Execute`,
  `stdlib only`) + cross-file parity (`3-strike` — present in both CLAUDE.md
  §0 spine and PROTOCOL.md). (`Owner-signed` rejected — Codex C2: its only
  CLAUDE.md hit is the volatile CHANGELOG, not the spine.)
- For each invariant: NFKC-normalize **both** the phrase and each file's
  content (single pass) + collapse internal whitespace/newlines, then assert
  the phrase is a substring of every listed file. Collect all misses; **exit 1**
  naming `id + file + phrase`. `--json` for machine output; `--list` to print
  the constant.
- **`--repo <path>`** override (mirror `check-staleness.py`) so tests run
  hermetically against a synthetic tmp tree (do NOT hardcode REPO_ROOT — that
  is the `check-docs-drift.py` anti-pattern).
- **Adopter SKIP:** if run outside the framework repo, exit 0 with an advisory
  note. Detect framework context via a **framework-only marker adopters never
  receive** — `.claude/adr/ADR-001-runtime-state-directory.md` (and/or
  `scripts/install.sh`). **NOT** `.claude/adr/` itself (install.sh:1064 ships
  `.claude/adr/README.md` to every adopter — Codex C1) and **NOT** presence of
  CLAUDE.md. Keeps adopter `validate-governance.sh` + `smoke-install.yml` green.
- Pure read-only: no eval, no shell-out on file content, no PyYAML.

**Acceptance criteria:**
- `[P0][US-A1][.claude/scripts/check-rule-invariants.py]` stdlib-only (passes `check-stdlib-only.py`, **no new allowlist entry**); accepts `--repo`; exit 1 when any pinned phrase missing from any listed file, exit 0 when all present; self-test asserts no loaded phrase is empty/whitespace after normalize.
- `[P0][US-A2][.claude/scripts/check-rule-invariants.py]` ≥6 invariants, each **grep-verified 1/1 in every listed tracked file before being added**; each phrase asserted `== NFKC(phrase)` in a registry self-test; ≥1 cross-file (CLAUDE.md+PROTOCOL.md) invariant present.
- `[P0][US-A3][.claude/scripts/validate-governance.sh]` guard wired as a fail-closed step modeled on the `check-docs-drift.py` invocation (~line 934); the **full (slow)** `validate-governance.sh` exits 0 on the current clean tree; deleting a pinned phrase makes the full gate exit non-zero. (Note: `validate_governance_fast` runs no bash steps — it is unaffected by design.)
- `[P0][US-A4][.claude/scripts/check-rule-invariants.py]` SKIPs (exit 0 + advisory) when the framework-only marker `.claude/adr/ADR-001-runtime-state-directory.md` (and/or `scripts/install.sh`) is absent — **NOT** merely `.claude/adr/`; add `[P1][scripts/tests/smoke-install.sh]` (or smoke-install.yml assertion) that `validate-governance.sh` exits 0 inside a fresh `install.sh --ceremony user` target.
- `[P1][US-A5][.claude/scripts/tests/test_check_rule_invariants.py]` positive (all present → 0), negative (delete one phrase → 1 naming id+file+phrase), adopter-skip (fixture with `.claude/adr/README.md` PRESENT but `ADR-001-runtime-state-directory.md` ABSENT → exit 0 — simulates a real adopter per C1), unicode/whitespace-reword case; coverage per ADR-139 tier.

## 4. Wave B — Inline Debt Ledger (effort M, **advisory, nightly-only**)

**Deliverable:** `.claude/scripts/check-debt-ledger.py` (stdlib) + grammar doc
+ an 8th dimension in the `nightly-hygiene` **saved Workflow**. **No
per-validate step** (dropped per debate F8 — redundant + latency risk).

**Design:**
- Grammar: `# CEO-DEBT: <ceiling>, <upgrade-trigger>` — **uppercase,
  line-anchored** sentinel (bare `# ceo-debt:` collides with ordinary
  comments). Matched at line-start or inside a code fence; a **non-backtracking
  line-anchored regex** treats marker content as inert data (ReDoS-safe, S180/S190).
- Script greps first-party roots only, **pruning** `{.git, npm, dist,
  node_modules, venv, .codex, staged, .plan138-bak, _lib_archived, __pycache__,
  archive, worktrees}` (a scanner-specific superset inspired by
  `pytest.ini:72 norecursedirs` — Codex C3) and its own fixtures/examples. Emits a **derived ledger** (stdout / `--json`) — never a
  stored file that can drift. Flags markers missing an upgrade-trigger =
  ungoverned debt. Footer mirrors the `check-staleness.py` output **style**
  (not a shared module): `N markers, M ungoverned`.
- **Honest note:** 0 `# CEO-DEBT:` markers exist today; Wave B is forward-
  facing infrastructure governing future in-code shortcuts below the ADR/PLAN
  bar. Existing `DEFERRED to PLAN/ADR` already point at governed artifacts —
  left as-is, not migrated.

**Acceptance criteria:**
- `[P0][US-B1][.claude/scripts/check-debt-ledger.py]` parses the grammar with a non-backtracking regex, emits derived ledger + `--json`, flags trigger-less markers; accepts `--repo`; excludes `npm/`, `dist/` and its own fixtures (assert self-non-match); advisory exit 0.
- `[P1][US-B3][.claude/workflows/nightly-hygiene.js]` add an 8th **read-only** dimension that invokes `python3 .claude/scripts/check-debt-ledger.py --json` and returns an ADR-141 8-field shard (writes nothing, no network; ADR-136-AMEND-1 confinement); re-validate with `validate-saved-workflows.js`.
- `[P2][US-B4][.claude/scripts/tests/test_check_debt_ledger.py]` grammar parse, trigger-less detection, empty-tree (0 markers), and prose-mentioning-`ceo-debt`-is-NOT-counted regression.
- `[P2][US-B5][docs/]` one-page grammar reference; linked from CONTRIBUTING or GOVERNANCE.

## 5. Wave V — Verify / rite (gates execution)

- **Debate**: DONE — `wf_87527b04-38d`, VETO resolved, 12 fixes applied (§1.5).
- **Pair-rail (ADR-107, L2+)**: DONE — Codex `019edaeb` R1/R2 BLOCK → R3 ACCEPT
  (3 design fixes applied, §1.6). Note: this reviewed the DESIGN doc; the
  implementation DIFF gets its own Codex pass at execution.
- **No ADR-157** (debate Q1): once `AGENTS.md` is dropped, Wave A is a small
  in-script substring guard following `check_protocol_semver_cascade` /
  `check-docs-drift` precedent — not an architectural decision. Revisit only if
  the Owner later wants a standalone canonical-guarded registry (a KERNEL-HARD-
  DENY change that WOULD need an ADR).
- **Ship**: materialize-bundle → `finish-plan139.sh` (dry-run + apply, auto-
  rollback). `validate-governance.sh` is **NOT** canonical-guarded (debate F5),
  so finish can run inline — but follow the established native-terminal pattern
  for consistency. **After landing**, run `scripts/npm-rebuild.sh` and commit
  the regenerated `npm/.claude` tree so `verify-npm-bundle-sync` (validate.yml)
  stays green. Owner-GPG the commit per normal ceremony.

## 6. Anti-goals — explicitly NOT imported from ponytail

- ❌ **LOC-reduction / "Without-arm vs With-arm" claims** — manufactures a terseness/speed thesis we deliberately do not make (`docs/3-arm-protocol.md`).
- ❌ **Injecting ruleset *content* into `additionalContext`** — regresses our pointers-only posture (**S228 / PLAN-136-W3**, not ADR-153).
- ❌ **Free-text kill-switch ("stop ponytail" / "normal mode")** — a prompt-injection vector; any future mode toggle is exact-prefix slash, user-origin.
- ❌ **Broadening to more agent hosts** — each ponytail host advertises "governance" while enforcing none; misrepresentation risk, not a win.
- ❌ **Auto-setup nudges with agent-directed imperatives** — exactly what `_validate_injection_channels` (PLAN-136-W3) neutralizes.

## 7. Status

**DONE — implemented, verified, and landed Owner-GPG-signed in `b1fb6f4`
(S245).**

Executed S245 via Workflow `wf_6d083ec3-6d4` (parallel Wave A/B generation,
each self-validated) + main-loop wiring + adversarial re-verification.

Delivered:
- **Wave A** — `.claude/scripts/check-rule-invariants.py` (9 invariants, 1
  cross-file `Plan → Debate → Execute`; NFKC+whitespace-collapse substring
  detector; `--repo/--json/--list`; adopter-SKIP keyed on the ADR-001 marker;
  registry self-test fails CLOSED even under `python -O`) + 16 tests + a
  **fail-closed** step in the slow `validate-governance.sh`
  (§5quinquies). Negative proof: deleting a pinned phrase makes the full gate
  exit 1 naming `id+file+phrase`.
- **Wave B** — `.claude/scripts/check-debt-ledger.py` (advisory, always exit 0;
  `# CEO-DEBT:` single-`#` line-anchored ReDoS-safe grammar; prune + triple
  self-exclude; derived ledger, never stored) + 9 tests + `docs/ceo-debt-grammar.md`
  + an 8th read-only dimension in `.claude/workflows/nightly-hygiene.js`
  (ADR-141 8-field shard; `validate-saved-workflows.js` green).

Verification: `check-stdlib-only` 411 OK (no new allowlist); **26 tests pass**;
full `validate-governance.sh` exit 0 (0 errors). **Codex pair-rail (ADR-107) on
the implementation diff: 3 cross-model passes, VERDICT ACCEPT throughout, 5 P2
findings applied + re-verified** — each with a regression test:
(1) single-`#` regex so `## CEO-DEBT:` headings don't count;
(2) robust self-non-match test (no hard-coded total);
(3) `assert`→`ValueError` so the registry self-test fails closed under `python -O`;
(4) adopter-skip keyed on the ADR-001 marker ONLY (dropped the `scripts/install.sh`
secondary marker — an adopter ships its own installer, which would wrongly defeat
the skip);
(5) debt-ledger excludes the target repo's own copy of the scanner under `--repo`
(not just `__file__`).
Note: the legacy `codex_invoke.py` wrapper is stale against codex-cli 0.139.0
(substrate drift) — the canonical pass was run via `codex exec review --uncommitted`.

Shipped: `npm-rebuild.sh` confirmed the `npm/.claude` mirror clean (gitignored;
`npm/package.json` already in sync at 1.46.1) → Owner-GPG-signed commit `b1fb6f4`
(Good signature, EDDSA D7227…E279). This status transition lands in a trivial
follow-up commit carrying `related_commits=[b1fb6f4]`. Read-only clone of ponytail
at `/tmp/ponytail-1781786581` (inert); safe to delete.
