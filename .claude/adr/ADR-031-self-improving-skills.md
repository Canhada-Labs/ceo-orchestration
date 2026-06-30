# ADR-031: Self-improving skills (Owner-gated, shadow-mode)

**Status:** ACCEPTED
**Date:** 2026-04-14
**Sprint:** 11 Phase 4
**Related:** ADR-010 (canonical-edit sentinel), ADR-011 (injection_flag
advisory), ADR-018 (claim grammar / confidence gate), ADR-019 (confidence
gate enforcement lifecycle), PLAN-011 debate round 1 **CR1** (CRITICAL)

## Context

PLAN-011 Phase 4 introduces a feedback loop: **agent-authored lessons →
candidate SKILL.md patch → Owner review → shadow apply → promote**.
Lessons accrete under `.claude/lessons/` whenever a benchmark fails or a
debate adjustment is captured. Over time the best-scoring lessons
represent compressed institutional memory. A manual CEO would fold that
institutional memory back into the relevant `SKILL.md` so every future
spawn benefits from the lesson — but a manual fold is slow, inconsistent,
and doesn't scale as the skill library grows past the current 48.

The naive pipeline is **CRITICAL-unsafe**. A compromised lesson — or a
crafted one planted by a prompt-injected Read — becomes a skill patch
proposal, which an Owner-on-autopilot visually approves, which then
mutates `SKILL.md`. Every subsequent spawn reads the compromised skill.
The amplification factor is the full spawn count for that skill across
the entire project lifetime. **This is the single highest blast radius
in the framework.**

The attack surface enumerated in debate round 1 CR1:

1. Unicode bidirectional override (U+202E) hiding hostile tokens
2. Zero-width joiners / spaces (U+200B–U+200F) hiding tokens
3. Homoglyph substitution (Cyrillic `а` for Latin `a` in `api_key`)
4. Long-line truncation — hostile payload past the 80/120 col visual cutoff
5. Injection patterns (scan-injection.py hits) embedded in rationale
6. Fenced executable code (```python) that looks like documentation but
   will be read/interpreted by future agents
7. Diff-size bloat — 10k-line diff that no human reviews exhaustively
8. Frontmatter approval spoofing — `approved_by:` is untrustworthy without
   cryptographic signature

Doing nothing is not an option — the Owner asked for auto-skills. Doing
it without the **10-point mitigation bundle** below would ship a backdoor.

## Decision drivers

- **Unacceptable worst case** — the cost of a single successful attack
  is "every spawn of compromised skill reads malicious content". Err on
  the side of false-negative rejection.
- **Fail-closed default** — no proposal applies unless every mitigation
  layer explicitly passes.
- **Stdlib-only** — GPG via subprocess; no new runtime dependency.
- **Shadow-first** — real `SKILL.md` is never written in the propose/apply
  flow. Promotion is a separate, delayed, explicit step.
- **Dogfood the sentinel** — the existing `check_canonical_edit.py`
  (ADR-010) already blocks `SKILL.md` edits without an Owner-signed
  sentinel. Skill-patch flow issues its OWN sentinel companion
  (`check_skill_patch_sentinel.py`) with a stricter contract.
- **Audit-first** — every stage (propose, apply, promote) emits an audit
  event. Silent mutations are forbidden.

## Decision

Ship **Owner-gated, 7-day shadow-mode** self-improving skills.

### Moving parts

1. **`.claude/scripts/skill-patch-propose.py`** — drafts an `SP-NNN.md`
   proposal from one or more lessons. Fail-closed on every attack
   vector in the CR1 table below.
2. **`.claude/scripts/skill-patch-apply.py`** — verifies GPG detached
   signature + Owner `--confirm` phrase. Default mode writes
   `<SKILL.md>.shadow.md` (never the real file). `--promote` mode is
   only valid after 7 days AND requires re-verification of the proposal
   + signature.
3. **`.claude/hooks/check_skill_patch_sentinel.py`** — PreToolUse
   `Edit|Write|MultiEdit` hook. If the target is a `SKILL.md` file,
   blocks unless a matching approved `SP-NNN` proposal exists AND the
   session env var `CEO_SKILL_PATCH_SHA` matches the diff hash recorded
   in the proposal. Fail-open on infra errors (ADR-005).
4. **`.claude/commands/skill-review.md`** — slash command for Owner
   review / approval / rejection.
5. **`.claude/proposals/`** — on-disk directory for SP-NNN proposals.
   Gitignored by default in target repos; present in this repo only via
   `.gitkeep` + `README.md` so the sentinel has something to scan.
6. **`SPEC/v1/skill-proposals.schema.md`** — normative contract for
   proposal frontmatter + status lifecycle + hash trailer format.

### 10-point CR1 mitigation bundle — evidence table

| # | Mitigation | Enforced by | Evidence (file:test) |
|---|---|---|---|
| 1 | `scan-injection.py` pre-draft | `skill-patch-propose.py::_scan_lesson` | `test_skill_patch_propose.py::test_rejects_injection_pattern` |
| 2 | Bidi / zero-width / control-char strip in preview | `skill-patch-propose.py::_normalize_preview` | `test_skill_patch_propose.py::test_rejects_bidi_override` + `test_rejects_zero_width` |
| 3 | AST-validate no fenced executable code without second-stage review | `skill-patch-propose.py::_detect_fenced_code` | `test_skill_patch_propose.py::test_rejects_fenced_python` + `test_allows_fenced_python_with_flag` |
| 4 | Diff size < 200 lines | `skill-patch-propose.py::_check_diff_size` | `test_skill_patch_propose.py::test_rejects_oversized_diff` |
| 5 | Re-run touched benchmarks in CI post-apply (shadow branch) | STUB in Sprint 11 — `skill-patch-apply.py` writes `.shadow.md` + `--skip-ci-rerun` sentinel log line (see §Open questions) | `test_skill_patch_apply.py::test_writes_shadow_on_apply` |
| 6 | `SP-NNN.md` requires Owner GPG detached signature | `skill-patch-apply.py::_verify_signature` | `test_skill_patch_apply.py::test_missing_signature_exits_2` + `test_invalid_signature_exits_2` |
| 7 | Hash of approved diff in commit trailer — verified by `check_canonical_edit.py` + `check_skill_patch_sentinel.py` | `check_skill_patch_sentinel.py::_verify_commit_trailer` via `CEO_SKILL_PATCH_SHA` env | `test_check_skill_patch_sentinel.py::test_allows_with_valid_trailer` + `test_blocks_on_trailer_mismatch` |
| 8 | 7-day shadow mode | `skill-patch-apply.py::_check_shadow_age` | `test_skill_patch_apply.py::test_promote_before_seven_days_exits_4` + `test_promote_after_seven_days_merges` |
| 9 | Confidence-gate extension (ADR-018 amendment) covers skill-patch proposals — declared as a rationale field, not a code change here | `skill-patch-propose.py` emits `claims_declared: bool` frontmatter field (Sprint 12 wires to confidence gate) | `test_skill_patch_propose.py::test_frontmatter_schema` |
| 10 | Owner approval phrase `--confirm "I have read SP-NNN"` literal | `skill-patch-apply.py::_verify_confirm_phrase` | `test_skill_patch_apply.py::test_wrong_confirm_phrase_exits_3` |

### 7-day shadow protocol

```
t=0   skill-patch-propose.py  → SP-042-core-security-2026-04-14.md (status: draft)
                                 diff committed to proposals/, no SKILL.md write
t=t0  Owner reviews, creates detached GPG signature SP-042.md.asc
t=t0  skill-patch-apply.py --proposal SP-042 --signature SP-042.md.asc \
        --confirm "I have read SP-042"
      → writes .claude/skills/core/security-and-auth/SKILL.md.shadow.md
        status: shadow, applied_at: 2026-04-14T12:00:00Z
        emits skill_patch_applied(shadow_mode=True)
t+7d  Owner runs benchmarks against the shadow file. No regression.
      skill-patch-apply.py --proposal SP-042 --signature ... \
        --confirm "I have read SP-042" --promote
      → verifies proposed_at >= 7d old
        merges SKILL.md.shadow.md → SKILL.md (printing commit message
        with `Skill-Patch-SHA: <hex>` trailer for CEO to commit)
        status: promoted, shadow_mode=False event emitted
t+8d  CEO commits with the trailer. check_canonical_edit.py verifies
      sentinel. check_skill_patch_sentinel.py verifies trailer hash
      matches proposal's recorded sha256_of_diff.
```

`CEO_SOTA_DISABLE=1` → `propose.py` and `apply.py` exit 0 no-op.
`check_skill_patch_sentinel.py` ignores `CEO_SOTA_DISABLE` — the sentinel
is a safety surface, not a feature flag.

## Non-goals (Sprint 11)

- **Auto-apply without Owner approval** — explicitly out of scope. The
  attack surface is too high.
- **Cross-skill proposals in one SP-NNN** — each proposal targets exactly
  one `SKILL.md`. Multi-skill refactors still need a hand-crafted plan.
- **Auto-revocation** — if a promoted skill turns out bad, the Owner
  reverts via normal `git revert` + new SP-NNN. No magic rollback.
- **Real shadow CI wiring** — Sprint 11 ships measure-only: the `.shadow.md`
  file exists, but the benchmarks re-run workflow is a separate ADR
  (Sprint 12 ADR-037 candidate per CR1 row #5).
- **Embedding-based lesson ranking for patch selection** — out of scope.
  The propose flow is CLI-driven: Owner picks the lessons.

## Blast radius: **L3**

Every `SKILL.md` consumer — every spawn across every squad — reads the
output of this flow (eventually). A misconfigured promote or bypassed
sentinel compromises the governance contract.

## Open questions (Sprint 12)

1. **Shadow CI orchestration.** Sprint 11 writes `.shadow.md` but does
   not automate benchmark re-runs against it. Sprint 12 ADR-037 wires
   `.github/workflows/skill-patch-shadow.yml` that runs the per-skill
   benchmark corpus against the shadow file and reports pass-rate delta.
2. **Signer fingerprint allowlist.** Sprint 11 accepts any valid GPG
   signature (GPG's WOT is used). Sprint 12 may add an explicit Owner
   fingerprint pin in `settings.json` — e.g. `skill_patch_signer_fpr:
   "ABCD 1234 ..."` — to defend against a compromised keyring.
3. **ADR-018 amendment wire-up.** CR1 row #9 says the confidence gate
   extension covers skill-patch proposals. Today this is declarative
   (frontmatter field). Sprint 12 actually invokes `check_confidence_gate.py`
   on the rationale section.
4. **Multi-signer policy.** Some orgs will want 2-of-N Owner signatures
   (e.g. CEO + Security). Deferred.

## Alternatives considered

- **Frontmatter `approved_by: @owner` + no GPG.** Rejected — one
  compromised YAML parse away from backdoor. Cryptographic signature is
  the defensible minimum.
- **Auto-apply with synchronous benchmark gate.** Rejected — benchmarks
  take minutes, and a benchmark suite crafted to avoid the injected
  content is trivially constructible by the attacker.
- **Skip shadow entirely.** Rejected — 7-day soak is the cheapest
  independent observation of the mutation before it amplifies.
- **Owner edits `SKILL.md` directly via canonical-edit sentinel (ADR-010).**
  Still available; the skill-patch flow is purely additive. If an Owner
  prefers the manual flow, ADR-010 still works.

## Back-compat

- `event_schema` remains `v2` (additive — `skill_patch_applied` is a new
  action, per the same additivity discipline as ADR-011 injection_flag).
- `check_canonical_edit.py` is unchanged. `check_skill_patch_sentinel.py`
  is a NEW hook registered alongside it; both fire on the same matcher
  (`Edit|Write|MultiEdit`).
- `CEO_SOTA_DISABLE` is the single kill-switch for the propose/apply
  feature. The sentinel remains active even when disabled.

## References

- PLAN-011 debate round 1 `consensus.md` §CR1 (this ADR addresses in full)
- ADR-010 (canonical-edit sentinel — the pattern we extend)
- ADR-011 (injection_flag advisory — observability pattern we dogfood)
- ADR-018 / ADR-019 (claim grammar / confidence gate — CR1 row #9)
- `SPEC/v1/skill-proposals.schema.md` (normative proposal format)

## Amendment 1 — Skill bootstrap bypass (ADR-059, 2026-04-19)

ADR-031 was designed for PATCHES over existing SKILL.md files via the
SP-NNN proposal + sha256 trailer + 7-day shadow-apply flow. It
inadvertently blocked NEW skill creation because the hook
`check_skill_patch_sentinel.py` applies the same gate to bootstrap
writes (target SKILL.md does not yet exist). Post-Sprint-11, every
attempt to create a new skill hit this wall; PLAN-031 (brainstorm
gate skill creation) surfaced the gap operationally.

**Bootstrap bypass mechanism:** two-factor env-var pattern
(`CEO_SKILL_BOOTSTRAP=<slug>` + `CEO_SKILL_BOOTSTRAP_ACK=I-ACCEPT`)
parallel to `CEO_KERNEL_OVERRIDE` / `_ACK` from `check_arbitration_kernel.py`.
Bootstrap-only (target must NOT already exist); existing SKILL.md
patches continue through the SP-NNN flow.

See `ADR-059-skill-bootstrap-env-knob.md` for the full rationale,
compensating controls, and revisit triggers.

## Enforcement commit

`78db946a3279` (retrofit — PLAN-050 Phase 2 / PLAN-045 F-06-03; this anchors the file's introduction commit, not a runtime-behavior commit. For ADRs whose decision was wired into hooks/scripts in a later commit, amend this line manually.)
