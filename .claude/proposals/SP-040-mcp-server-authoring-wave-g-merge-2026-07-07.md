---
id: SP-040
skill_slug: mcp-server-authoring
archetype: mcp-builder
proposed_at: 2026-07-07T07:30:00Z
source_lessons:
  - plan-153-wave-g-adapt-merge
scan_injection_pass: true
diff_size_added: 115
diff_size_removed: 0
sha256_of_diff: null
sha256_of_staged: c459a7a29c8e44b8ef6ba272a83db3f36503670175a2b458f96b8657b4e1ec4b
claims_declared: false
status: shadow
approved_by: AE9B236FDAF0462874060C6BCFCFACF00335DC74
applied_at: 2026-07-09T11:33:31Z
promoted_at: null
shadow_mode: true
proposal_type: adapt-merge-enrichment
after_wave_c: false
upstream_sources:
  - affaan-m/ecc@81af4076 skills/agent-harness-construction/
patch_source: .claude/plans/PLAN-153/staged/wave-G/.claude/skills/core/mcp-server-authoring/
---

# SP-040 — skill patch proposal (Wave G ADAPT merge)

**Target:** `.claude/skills/core/mcp-server-authoring/SKILL.md`
**Archetype:** mcp-builder
**Kind:** PLAN-153 Wave G ADAPT-merge enrichment (1 upstream skill folded into
an existing catalog skill; no new skill file; catalog count unchanged)

## Rationale

Wave G materialized-merge **row 21** (`wave-g-materialized-list.md`): fold the
agent-harness-construction ruleset from `affaan-m/ecc@81af4076`
`skills/agent-harness-construction/` into our existing `mcp-server-authoring`
skill. The live skill is thorough on making a server *safe* (12 Hard Rules,
security boundaries, three test layers) but silent on whether the LLM harness on
the other end of the pipe can actually *use* the tool surface it exposes. The
upstream contributes exactly that missing axis — action-space design, tool
granularity, actionable observation shape, an error-recovery contract, and
surface-level benchmark signals. The merge is **additive**: one net-new
`## Designing the Tool Surface for the Calling Agent` section (inserted after
`## Tool Schema Design`, before `## Security Boundaries`) plus a `## Changelog`
entry; no pre-existing content rewritten. Staged file is 800 lines vs. the
685-line live skill (net +115 lines of merged material, 0 removed).

## Provenance note

Clean-room ADAPT: the upstream skill informed scope and axis (usability of the
tool surface for the calling agent); the prose, examples, and every rule are
original work in this framework's voice, cross-referenced back into our own Hard
Rules (stable output shape ↔ wire framing Rule 5, narrow schema ↔ fuzz surface,
retry guidance ↔ idempotency markers Rule 8). Zero upstream/ECC strings in the
merged body. Provenance is recorded two ways, per the Wave G contract: (1) a row
in the root `NOTICE` "PENDING CEREMONY LANDING — PLAN-153 Wave G" section naming
`affaan-m/ecc@81af4076 skills/agent-harness-construction/` + MIT license; (2) an
`inspired_by:` frontmatter entry (`relationship: content_adaptation`) in the
merged SKILL.md.

Because the merge carries upstream-derived content, it rides the **import gate**
(`check-imported-skill.py`) IN ADDITION to `/skill-review` (plan §Wave G: "All
merges ride SP-NNN + `/skill-review` + import gate"). `scan-injection.py` was run
over the staged file (2026-07-07) with **exit 0, no injection patterns detected**;
the enforcing injection-corpus + provenance + attestation checks are the ceremony
precondition (Landing mechanics step 1), not an author-time attestation.

Rollback-safe: promote replaces exactly one file (SKILL.md); reverting restores
the prior SKILL.md. No references directory is added by this row.

## Patch source (staged tree, sha256-pinned)

Source of truth = the staged tree at
`.claude/plans/PLAN-153/staged/wave-G/.claude/skills/core/mcp-server-authoring/`:

| sha256 | file |
|---|---|
| `a53d2b95398fa56f83d51a21a69dfad965358b5063489fb3875f614187357f97` | `SKILL.md` (merged, 800L) |

## Proposed diff (summary — the full diff is NOT embedded)

The merge is additive (verified: `git diff --no-index` shows +115, 0 removals);
regenerate and review the unified diff against the live skill with:

```
git diff --no-index .claude/skills/core/mcp-server-authoring/SKILL.md \
  .claude/plans/PLAN-153/staged/wave-G/.claude/skills/core/mcp-server-authoring/SKILL.md
```

Not embedded as a ```diff fence: `skill-patch-apply.py` refuses any diff with
removal lines by contract, and landing is a whole-file replacement (`mv
SKILL.md.shadow.md SKILL.md`), not an append-only patch. Landing is the Owner
ceremony below.

## Landing mechanics (wake-up ceremony — /skill-review + import gate)

1. **Import gate + /skill-review.** Run
   `check-imported-skill.py --skill <staged SKILL.md> --notice NOTICE` (expect the
   provenance check to resolve against the Wave G NOTICE row) and the human
   `/skill-review` line-by-line pass ON TOP of the mechanical gate. Verify the
   sha256 pin above before anything else.
2. **Approve (shadow apply).** After review + detached GPG signature on this file
   (`.claude/skill-patch-signers.txt`), copy the staged SKILL.md to
   `.claude/skills/core/mcp-server-authoring/SKILL.md.shadow.md`. Update
   frontmatter `status: shadow`, `applied_at`, `approved_by`.
3. **Soak — parallel-shadow, NOT skip (OQ3=c).** The live SKILL.md keeps serving
   activations for the soak window while the shadow sits beside it;
   `skill-health.py` telemetry (invocations + failure-proxy for
   `mcp-server-authoring`) is the regression signal.
4. **Promote.** After the soak window, `mv SKILL.md.shadow.md SKILL.md` under the
   SKILL.md sentinel gate (`check_skill_patch_sentinel.py` requires this SP on
   disk), replace the `SP-040` placeholder in the merged changelog if needed, and
   set `status: promoted`, `promoted_at`.

## Honest residuals

- `diff_size_added: 113 / diff_size_removed: 0` are the verified insertion/removal
  counts vs. the live skill; `sha256_of_diff` stays null (no standalone diff
  artifact is pinned — the reproduction command above is the review instrument).
- `scan_injection_pass: true` records an exit-0 run of the advisory scanner, not
  a full adversarial injection audit — the import gate at ceremony is enforcing.
- Activation-time cost rises with the merged content; `mcp-server-authoring` is
  not a Wave C progressive-disclosure pilot, so the +115 lines are paid per
  activation. Acceptable for a first-class usability axis on an authoring skill;
  revisit if it becomes a context-budget top-3.


> **Contagens finais S262 (pós-review, autoritativas):** staged = 800 linhas; diff vs live = +115/−0; frontmatter diff_size_added/removed sincronizados. Rail de integridade = pin sha256_of_staged, re-pinado após cada fix.
