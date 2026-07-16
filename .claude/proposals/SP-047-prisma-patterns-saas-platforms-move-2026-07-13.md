---
id: SP-047
skill_slug: prisma-patterns
archetype: none   # squad-drain move, CEO-proposed — SP-018/SP-042 precedent (no owning archetype)
proposed_at: 2026-07-13T23:09:00Z
source_lessons:
  - plan-157-oq5-prisma-home-saas-platforms
scan_injection_pass: true
diff_size_added: 1
diff_size_removed: 1
sha256_of_diff: 52548b5856574b25b915d142f2188f30af63437a9f1db54e2106d26c5968f7cb
sha256_of_staged: 0c5fa36e13c4f8de03c51e764d0b39464475477e0e27d7a047605ebd18c6aa2d
claims_declared: false
status: proposed
shadow_mode: false
soak_waiver: owner-ratified-at-signing   # PLAN-157 OQ4 (Owner tie-break S270) via SP-042/S264-OQ4 precedent
proposal_type: squad-drain-move
patch_source: inline diff fence (below)
---

# SP-047 — MOVE `prisma-patterns` → `domains/saas-platforms` (PLAN-157, **applied at W3 per OQ5**)

> **APPLY WINDOW: Wave 3, not Wave 1.** OQ5 must resolve before the
> data-ml graduation go/no-go; this move IS that resolution and lands
> in the W3 sentinel ceremony, ahead of the data-ml go/no-go decision.

**Move:** `.claude/skills/domains/data-ml/skills/prisma-patterns/` →
`.claude/skills/domains/saas-platforms/skills/prisma-patterns/`
**Kind:** NOT a distill — the skill body relocates VERBATIM as its own
skill dir; the only content edit is the frontmatter
`metadata.domain: data-ml` → `saas-platforms`. The data-ml source dir
is deleted by the move itself (`git mv`).
**Source pin:** pre-move SKILL.md sha256
`0eaa69c7a77f9f91927c1c5dacc3d7b3149c61e7f4396b3a7d483aa9772695bd`;
post-move content pinned by `sha256_of_staged` (18,290 B → 18,297 B —
the one-line domain edit is the entire content delta).

## Rationale — Owner OQ5 ratification (S270)

Owner selected "data-ml vira ML-only + prisma move": `prisma-patterns`
(a TypeScript ORM skill) does not belong beside `pytorch-patterns` in
an ML bundle; it moves via SP to a web/backend-adjacent domain and
data-ml graduates ML-only with +1 authored ML skill. `saas-platforms`
is that domain (multi-tenant TS/backend platform squad).

**Its Related Skills entries refer to skills by name, not path** — no
tier-boundary exposure; domains→domains references are outside
`check-tier-boundaries.py`'s scan set anyway (it walks core/ +
frontend/ only).

## Gate evidence — saas-platforms absorbs +1 (ADR-009 minimums)

Measured against the `validate-governance.sh` §5 bundle gate (minimums,
not exact counts): personas **5** (gate ≥5); skills **3 → 4** after the
move (gate ≥3); pitfalls **13** (gate ≥10); task-chains **2** top-level
(gate ≥2); examples **1** (gate ≥1). Every minimum holds post-move.
Additionally `saas-platforms` sits on `SQUAD_GRANDFATHER`, so a bundle
failure would be WARN-only regardless — and the grandfather cap counts
SQUADS, not skills: this move does not touch `current`/`cap`.

## Count surfaces + W3 go/no-go flag

Net-zero on the 166-skill catalog (one dir moves), but the move commit
MUST still run the full PLAN-157 reconcile checklist — claims,
verify-counts, COMMAND-SKILL-HOOK-MAP regen, the guarded skill-inventory
block, and the install-profiles bijection (`profiles.json` references
data-ml today; `check-install-profiles.py` runs BOTH ways).

**FLAG for the W3 data-ml go/no-go:** post-move data-ml =
`pytorch-patterns` only; the plan's "+1 authored ML skill" yields 2
skills — below the ≥3 ADR-009 graduation minimum. data-ml graduation
needs +2 authored ML skills, or the disposition needs a revisit at the
go/no-go.

## Soak waiver

WAIVED per the Owner's OQ4 ratification (S270 structured tie-break,
SP-042/S264-OQ4 precedent): the skill body is relocated verbatim —
in-tree and import-attested since 2026-07-08; zero doctrine delta
beyond one frontmatter key. Owner ratifies by detach-signing this
proposal. `sha256_of_staged` pins the exact post-move file.

## Apply route

A directory MOVE is not expressible by the append-only pipeline
`_apply_unified_diff` (SP-042 constraint). Applied Owner-shell inside
the **W3** sentinel ceremony: `git mv` of the skill dir + the one-line
frontmatter edit, then the staged-file hash asserted before commit.
Reconcile checklist items ride the same commit.

## Diff

```diff
diff --git a/.claude/skills/domains/data-ml/skills/prisma-patterns/SKILL.md b/.claude/skills/domains/saas-platforms/skills/prisma-patterns/SKILL.md
similarity index 99%
rename from .claude/skills/domains/data-ml/skills/prisma-patterns/SKILL.md
rename to .claude/skills/domains/saas-platforms/skills/prisma-patterns/SKILL.md
--- a/.claude/skills/domains/data-ml/skills/prisma-patterns/SKILL.md
+++ b/.claude/skills/domains/saas-platforms/skills/prisma-patterns/SKILL.md
@@ -29,7 +29,7 @@
     - "**/prisma/**"
     - "**/prisma.config.ts"
   risk_class: low
-  domain: data-ml
+  domain: saas-platforms
 source: affaan-m/ecc@81af4076 skills/prisma-patterns/
 license: MIT
 ---
```

## Verification

- `sha256(saas-platforms/skills/prisma-patterns/SKILL.md post-move) ==
  sha256_of_staged` (asserted by the W3 landing script before commit);
  data-ml source dir absent.
- `bash .claude/scripts/validate-governance.sh` → saas-platforms bundle
  minimums hold (personas ≥5, skills ≥3, pitfalls ≥10, task-chains ≥2,
  examples ≥1).
- `python3 .claude/scripts/check-install-profiles.py` → bijection green
  after the profiles.json data-ml reference is reconciled.
- `python3 .claude/scripts/check-claude-md-claims.py` &&
  `bash .claude/scripts/local/verify-counts.sh --no-tests` &&
  `python3 .claude/scripts/gen-command-skill-hook-map.py --check` →
  net-zero catalog confirmed (166 skills).
- `python3 .claude/scripts/lint-skills.py` → zero ERROR lines.
- Full PLAN-157 per-wave Check set rides the W3 ceremony commit.
