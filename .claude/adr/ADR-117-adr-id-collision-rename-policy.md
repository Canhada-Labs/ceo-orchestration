---
id: ADR-117
title: ADR-ID collision rename policy — going-forward doctrine
status: ACCEPTED
accepted_at: 2026-05-12
accepted_by: "Owner (post-Codex-Pair-Rail-iter-5-ACCEPT 2026-05-12; threads 019e1d07..019e1d22)"
proposed_at: 2026-05-12
proposed_by: CEO (PLAN-085 Wave 0; PLAN-084 R-006 historical collision driver)
related_plans: [PLAN-080, PLAN-082, PLAN-084, PLAN-085]
related_adrs: [ADR-093, ADR-111, ADR-120]
supersedes: []
tags: [governance, adr-lifecycle, naming, collision-rename]
authorization: PLAN-085 Wave 0 atomic ADR ceremony (`OWNER-CEREMONY-PLAN-085-WAVE-0.sh`)
---

# ADR-117 — ADR-ID collision rename policy

## §1. Status

PROPOSED at draft time. Flips to ACCEPTED at the PLAN-085 Wave 0 atomic
ceremony commit that lands ADR-116/117/120 + ADR-040-AMEND-2 together
(`OWNER-CEREMONY-PLAN-085-WAVE-0.sh`). ADR-117 MUST be ACCEPTED before
the Wave B.1 ADR-111 → ADR-120 rename lands, since ADR-117 is the
doctrine that authorises the rename mechanic.

## §2. Context

The ADR ledger is monotonic and zero-padded 3-digit per the
`architecture-decisions` core skill. Two collisions have surfaced in
the framework's history:

1. **ADR-049 `a` suffix discipline (PLAN-061 precedent)** — `ADR-049-dual-path`
   and `ADR-049a-worktree` intentionally share the base-ID with an `a`
   suffix; this is a **documented non-collision** (Codex REFUTE on
   F-A-SEC-T-0002 in PLAN-084 Wave A; PLAN-085 B.2 documents the
   non-rename closure in `.claude/adr/README.md`).
2. **ADR-111 PII core promotion vs. ADR-111 locked-corpus governance
   (PLAN-082 historical)** — two ADRs ship with `id: ADR-111` in their
   frontmatter and on disk
   (`.claude/adr/ADR-111-pii-core-promotion.md` and
   `.claude/adr/ADR-111-locked-corpus-governance.md`).
   This is a **genuine collision** caught by PLAN-084 R-006
   (F-A-SEC-0001-7a82c1de, veto case C — audit-integrity).
   Both ADRs are ACCEPTED + ship in the same canonical posture; neither
   can be retracted without rewriting downstream `related_adrs:` graphs
   in 7+ plans + 3 skills + `CLAUDE.md` §6 archive.

The collision exists because:

- ADR drafting historically allocated the next-free integer at draft
  time, NOT at acceptance time;
- two concurrent plans (PLAN-080 PII core promotion + PLAN-082 locked
  corpus) each picked `111` independently and committed inside the
  same calendar week;
- no mechanical lint check warned on duplicate `^id: ADR-NNN` across
  the ADR directory.

Until ADR-117 lands, there is **no canonical doctrine** describing how
the framework resolves an existing ADR-ID collision. PLAN-082 R1
debates surfaced this gap but did not formalise; PLAN-084 audit promoted
it to TIER-1 roadmap item R-006. PLAN-085 Wave B.1 implements; ADR-117
documents the rule.

## §3. Decision drivers

- **Anti-churn (ADR-115 maintenance-mode):** rewriting both colliding
  ADRs to swap IDs causes cascade rename in every consumer; pick **one
  side to keep its original ID**, rename the other to a fresh
  monotonic-next slot.
- **Forensic preservation:** `git log --follow` MUST traverse the
  rename; commit message MUST cite the original ID for auditability;
  the renamed ADR retains its **content, status, and decided dates**
  unchanged (rename is mechanical only).
- **Cross-reference graceful migration:** ALL `related_adrs:` entries,
  `[[ADR-NNN]]` memory wiki-links, plan frontmatter references, skill
  body mentions, and CHANGELOG entries pointing at the renamed ADR MUST
  be updated in the same atomic commit as the rename.
- **Mechanical detection:** future collisions MUST be caught at lint
  time, NOT at audit time (`check-adr-id-uniqueness.py` script CI
  gate).
- **Doctrine reusability:** ADR-117 is reusable for any future ADR-ID
  collision; it is NOT specific to ADR-111.

## §4. Options considered

### Option A — Rename later-ACCEPTED ADR; keep earlier-ACCEPTED ID stable (CHOSEN)

The ADR whose `decided:` (or `proposed_at:` if pre-decision) timestamp
is later **keeps its content** but is **renamed to the next free
monotonic ID** at the next available slot. The earlier-ACCEPTED ADR
retains its ID unchanged. Rename ceremony:

1. New ID allocated from monotonic-next-free slot in the ADR ledger
   (verified via `check-adr-id-uniqueness.py --next-free`).
2. File renamed via `git mv` (preserves `--follow` history).
3. Frontmatter `id: ADR-NNN` updated to new ID; **all other
   frontmatter fields preserved**.
4. Title line `# ADR-NNN — <title>` updated to new ID.
5. A `## §X. Rename history` section appended to the renamed ADR's
   body recording the original ID + rename-driver finding ID + ceremony
   commit SHA.
6. Grep-and-update all cross-references in `.claude/`, `CLAUDE.md`,
   `MEMORY.md`, `.claude/plans/*.md`, `.claude/skills/**/SKILL.md`,
   `docs/**/*.md` — same atomic commit.
7. Ceremony commit message: `ceremony(ADR-OLD-rename): ADR-OLD →
   ADR-NEW per ADR-117 collision-rename`.

**Pros:** monotonic ID ledger preserved (no gaps); rename is
mechanically uniform; later-ACCEPTED ADR is by definition the one with
fewer downstream consumers (since it had less time to be referenced),
minimising cross-reference update surface.

**Cons:** if BOTH ADRs are decided in the same calendar day (tie),
tiebreaker required (see §5 — alphabetical sort by slug).

### Option B — Rename earlier-ACCEPTED ADR

Symmetric: rename the older one, keep the newer one's ID.

**Pros:** the newer ADR is by definition "fresher" in the author's
mind; less re-orientation cost on rename.

**Cons:** maximises downstream-consumer rename surface (older ADR has
had more time to accrue `related_adrs:` references). Breaks `git log
--follow` continuity for the longer-established ADR. **REJECTED**.

### Option C — Retract both, draft a new ADR-NNN consolidating

Withdraw both colliding ADRs; produce a new monotonic-next ADR
covering the union of both decisions.

**Pros:** single source of truth for the merged scope.

**Cons:** ADR-111 PII core promotion + ADR-111 locked-corpus
governance are **orthogonal scopes** (PII data-flow inheritance vs.
canonical corpus tamper-evidence); consolidation would create a
sprawling ADR that violates the "one decision per ADR" doctrine.
Retracting an ACCEPTED ADR requires retroactive `superseded_by:`
chains in 7+ plan files. **REJECTED** as scope-violating.

### Option D — Document both as collision; do not rename

Add a `## Note` block in `.claude/adr/README.md` flagging the
collision; leave both ADRs in place at `id: ADR-111`.

**Pros:** zero rename surface.

**Cons:** breaks the monotonic-ID invariant assumed by tooling
(`audit-query.py`, `check-skill-health.sh`, `validate-governance.sh`)
that uses `id:` as a unique key. Every future ADR-111 reference becomes
ambiguous. **REJECTED** as compounding the original defect.

## §5. Decision

**Adopt Option A** — rename the LATER-ACCEPTED ADR to a fresh
monotonic-next slot. Earlier-ACCEPTED ADR retains its ID unchanged.

### Tiebreaker (same-day acceptance)

If both ADRs are accepted on the same calendar day (UTC), the tiebreaker
is **lexicographic sort by slug** (post-ID portion of the filename):
the slug that sorts **EARLIER** keeps its ID; the LATER slug renames.

Example: `ADR-111-locked-corpus-governance.md` (decided 2026-05-09) vs.
`ADR-111-pii-core-promotion.md` (decided 2026-05-09). Slug
`locked-corpus-governance` sorts before `pii-core-promotion`
alphabetically — therefore **locked-corpus-governance keeps ID 111**,
and **pii-core-promotion renames to ADR-120** (next-free slot in
PLAN-085 ledger).

This tiebreaker is **mechanical** (no human judgement); both ADR
authors can independently compute the same rename outcome before
ceremony.

### Mechanical rename procedure (PLAN-085 B.1 implementation)

The rename is implemented in PLAN-085 Wave B.1 as a sequence of
atomic operations within a single ceremony commit:

1. `git mv .claude/adr/ADR-111-pii-core-promotion.md
   .claude/adr/ADR-120-pii-core-promotion.md`
2. Edit frontmatter: `id: ADR-111` → `id: ADR-120`.
3. Edit title line: `# ADR-111 — PII core promotion` →
   `# ADR-120 — PII core promotion`.
4. Append `## §X. Rename history` section (see ADR-120 body).
5. `grep -rln 'ADR-111-pii-core' .claude/ CLAUDE.md MEMORY.md
   docs/` → update each match to `ADR-120-pii-core` or
   `ADR-120` per context.
6. `grep -rln '\[\[ADR-111\]\]' ~/.claude/projects/*/memory/` →
   update wiki-links (memory files only; if context disambiguates,
   convert to `[[ADR-111]]` for locked-corpus or `[[ADR-120]]` for
   PII core promotion).
7. Atomic ceremony commit: `ceremony(ADR-111-rename): ADR-111 →
   ADR-120 per ADR-117 collision-rename` with body citing
   F-A-SEC-0001-7a82c1de as driver.

### Future-collision prevention

Ship `.claude/scripts/check-adr-id-uniqueness.py` (stdlib-only,
Python ≥3.9) as a CI gate in PLAN-085 Wave B.1:

- Glob `.claude/adr/ADR-*.md`, parse `^id:` frontmatter line.
- ERROR exit code if any ID appears in ≥2 files (with `a`-suffix
  whitelist per `ADR-049a` precedent — list pre-approved
  `<base>+<suffix>` pairs in script header).
- Wired into `validate-governance.sh` Tier-S list.

This script is the **mechanical floor** that ensures ADR-117 doctrine
is enforced going forward — no new collision can land without CI
failing.

## §6. Consequences

**Positive:**

- ADR-111 collision resolved with monotonic ID ledger preserved.
- Reusable doctrine: any future collision follows the same
  later-ACCEPTED-renames rule + lexicographic tiebreaker (no per-case
  debate).
- CI gate (`check-adr-id-uniqueness.py`) catches future collisions at
  pre-merge time, not at audit time.
- `git log --follow` history preserved on the renamed file via
  `git mv` (NOT `cp` + delete).
- All downstream consumers update in the same atomic commit (no
  intermediate broken-reference state).

**Negative:**

- The renamed ADR retains its original `decided:` date (NOT updated to
  the rename ceremony date) — a future reader could be confused
  why ADR-120 has `decided: 2026-05-09` but a rename history dated
  `2026-05-12`. Mitigated by the `## Rename history` section being a
  required body section (not an optional appendix).
- Cross-reference update surface is bounded by `grep -rln` matches at
  rename time; if a NEW reference is added to the original ID between
  draft and ceremony, it would survive as a stale reference. Mitigated
  by capturing the ceremony commit at start of Wave 0 + `git diff
  HEAD@{start}..HEAD` against PLAN-085 Wave 0 → B.1 timespan as a
  forensic check (delta should be zero new old-ID references).

**Neutral:**

- ADR ledger continues monotonic-numbering posture; no gaps introduced.
  PLAN-085 allocates ADR-116/117/120 + ADR-040-AMEND-2 — note ADR-118,
  119 already allocated to PLAN-088 (god-mode declaration) and PLAN-086
  (sentinel-unlock contract) respectively per the 4-plan handoff §1.

## §7. Authorization

ADR-117 itself is an ACCEPTED doctrine ADR (documentation-only — no
runtime hook artifact). Acceptance ceremony is the PLAN-085 Wave 0
atomic commit signed by Owner GPG via
`scripts/local/historical/OWNER-CEREMONY-PLAN-085-WAVE-0.sh`.

ADR-117 does NOT require `CEO_KERNEL_OVERRIDE` (no kernel scope
expansion; the new CI lint script `check-adr-id-uniqueness.py` is
shipped through Wave B.1, not Wave 0, and is itself NOT a kernel path).

## §8. Related work

- ADR-093 — canonical-guard moratorium retract + kernel-override
  discipline (this ADR follows the same atomic-ceremony pattern for
  the doctrine acceptance step).
- ADR-111 (locked-corpus governance, retains ID) — keeps its ID per
  ADR-117 §5 tiebreaker (earlier lexicographic slug).
- ADR-120 (PII core promotion, formerly ADR-111-pii-core-promotion) —
  the renamed ADR; documents its own rename history per §5.
- PLAN-082 — historical context where the collision was introduced
  (parallel-plan independent ID allocation).
- PLAN-084 R-006 (F-A-SEC-0001-7a82c1de) — audit-driver finding that
  promoted the collision-resolution to TIER-1 roadmap.
- PLAN-085 Wave B.1 — mechanical rename implementation.

## §9. Enforcement commit

n/a (documentation-only doctrine). The runtime enforcement artifact
(`check-adr-id-uniqueness.py`) ships with PLAN-085 Wave B.1 as a
separate commit gated by ADR-117 acceptance; that script's commit
SHA appears in PLAN-085 progress log §11.
