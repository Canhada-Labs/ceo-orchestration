---
id: SP-023
skill_slug: security-and-auth
archetype: security-engineer
proposed_at: 2026-07-07T05:31:00Z
source_lessons:
  - plan-153-wave-c-progressive-disclosure-pilot
scan_injection_pass: true
diff_size_added: 43
diff_size_removed: 771
sha256_of_diff: 0b53f19e79c32e817fce377d30f66709ebbcfd09b7bc26ce353612746ed202e7
claims_declared: false
status: promoted
approved_by: AE9B236FDAF0462874060C6BCFCFACF00335DC74
applied_at: 2026-07-09T00:11:21Z
promoted_at: 2026-07-09T15:49:44Z
shadow_mode: false
proposal_type: progressive-disclosure-restructure
patch_source: .claude/plans/PLAN-153/staged/wave-C/.claude/skills/core/security-and-auth/
---

# SP-023 — skill patch proposal

**Target:** `.claude/skills/core/security-and-auth/SKILL.md`
**Archetype:** security-engineer
**Kind:** PLAN-153 Wave C progressive-disclosure pilot #2 (staged-tree
restructure — slim loader SKILL.md + `references/*.md`, 100% content
preserved)

## Rationale

PLAN-153 Wave C item 1 designated `security-and-auth` as progressive-
disclosure pilot #2. `context-budget.py` (Wave C telemetry tool) ranks it
savings opportunity #2: 868 lines, ~10202 est tokens always paid per
activation; the staged loader is 134 lines (~1070 est tokens) — potential
saving ~10052 est tokens per activation. The restructure extracts the
eight topic bodies into `references/*.md` and leaves a loader SKILL.md
whose frontmatter (`name`, `description`, `activation_triggers`,
smart-loading fields) is UNCHANGED, so catalog discovery, `/debate`
veto-floor participation, and machine triggers are unaffected; each
section is replaced by a pointer table entry telling the agent which
reference file to Read on demand.

**Content preservation proof (mechanical, run 2026-07-07):** all 69
`##`/`###` headings of the live SKILL.md appear verbatim in the staged
tree; all 567 normalized non-heading content lines of the live SKILL.md
appear verbatim in the staged tree (0 lost). Zero content loss — the
saving is activation-time only.

Extra care taken for this pilot: `security-and-auth` is a VETO-floor
reviewer skill (it is wired into `/debate` per
`docs/COMMAND-SKILL-HOOK-MAP.md`). The loader keeps the veto-relevant
decision rules inline and pushes only the long worked material (OWASP
walkthroughs, threat-model worksheet, detection-as-code recipes) into
references, so a reviewer that fails to Read a reference still has the
floor rules in context.

## Provenance note

Hand-authored under PLAN-153 Wave C (ratified debate; staging discipline
per plan §Wave C). `skill-patch-propose.py` was NOT usable as generator:
its conservative appender only emits append-only diffs (cap 200 lines,
`.claude/scripts/skill-patch-propose.py:82` `_DIFF_SIZE_CAP`), and this
restructure is 39+/769− plus 8 NEW `references/*.md` files. The moved
content contains fenced code blocks inherited VERBATIM from the live
SKILL.md (the `CEO_SKILL_PATCH_ALLOW_CODE=1` human-review route applies —
no new executable content is introduced; every fence already exists in
the promoted live skill). All 9 staged files pass `scan-injection.py`
(clean, 2026-07-07) and the propose-time Unicode/bidi/homoglyph checks.

Rollback-safe: promote replaces exactly one file (SKILL.md) and adds
inert `references/*.md`; reverting restores the prior SKILL.md and
removes the references directory. The live skill's `benchmarks/`
directory is untouched. No other file is touched.

## Patch source (staged tree, sha256-pinned)

Source of truth = the staged tree at
`.claude/plans/PLAN-153/staged/wave-C/.claude/skills/core/security-and-auth/`:

| sha256 | file |
|---|---|
| `01136ae3d537cedff7ce5cb97a66a864b570ab33e7aa7033ada53159d39a4296` | `SKILL.md` (loader, 134L) |
| `cc08012c4a2fd5f739df37c3319617e2c09f982069723cae40c372338a3f274c` | `references/auth-and-credentials.md` |
| `fc080d5e49465d7002332531abd98b1b8cf7aa092b542a0183a1e14adb84de27` | `references/data-access-and-validation.md` |
| `d4f0d121c15fb9709fbfad4626903ccf27e8b637b62c7f275d9cfa4b7b9d13ff` | `references/detection-as-code.md` |
| `d0c8a839f5cdbdb7c034ee73bd5bb234887204c01b68554f018177e3b3c7adef` | `references/known-vulnerabilities.md` |
| `3e7c84132c8a73590b27bdd6231538af642053f8e1b24405f1b2f883f794015b` | `references/owasp.md` |
| `c7a70fec8e2f215d1d20fcee55a56c259230cad40ebbdf21b66c2129726f95f2` | `references/perimeter-and-transport.md` |
| `24182a00131b8eb00641fcace8e2f38e5ae790c320970227805af66afba8416b` | `references/proof-of-exploitability.md` |
| `6224cedb58c509245dd1db473acbb61e17475eb042a7c6262c3bc87261e0fc29` | `references/threat-model-worksheet.md` |

## Proposed diff (summary — the full diff is NOT embedded)

The SKILL.md unified diff is 43 added / 771 removed lines; regenerate and
verify against `sha256_of_diff` in the frontmatter with:

```
git diff --no-index .claude/skills/core/security-and-auth/SKILL.md \
  .claude/plans/PLAN-153/staged/wave-C/.claude/skills/core/security-and-auth/SKILL.md \
  > /tmp/sp-023.patch && shasum -a 256 /tmp/sp-023.patch
```

It is deliberately not embedded as a ```diff fence: `skill-patch-apply.py`
refuses any diff containing removal lines by contract
(`.claude/scripts/skill-patch-apply.py:461-464` returns None on a `-`
line), so an embedded fence would invite an apply path that structurally
cannot succeed. See Landing mechanics.

## Landing mechanics (wake-up ceremony — /skill-review governance)

This proposal rides `/skill-review` for governance (GPG-signed approval
against `.claude/skill-patch-signers.txt`, 7-day soak semantics, audit
events) but the mechanical apply is an Owner ceremony because the
automated apply path cannot express a restructure:

1. **Approve (shadow apply):** after `/skill-review` review + detached
   GPG signature on this file, the Owner copies the staged loader to
   `.claude/skills/core/security-and-auth/SKILL.md.shadow.md`
   (overwriting the stale shadow currently on disk) and lands the 8
   `references/*.md` files directly (they are NOT canonical-guarded —
   `check_canonical_edit.py:117-122` guards only `SKILL.md` — and are
   inert until the loader points at them). Verify every sha256 pin above
   before copying. Update frontmatter `status: shadow`, `applied_at`,
   `approved_by`.
2. **Soak — parallel-shadow, NOT skip (OQ3=c):** these pilots restructure
   EXISTING promoted skills, so the ratified soak posture is
   parallel-shadow: live SKILL.md keeps serving activations for the soak
   window while the shadow file exists side by side; `skill-health.py`
   telemetry over the window is the regression signal (invocations +
   failure-proxy for `security-and-auth` must not degrade — pay extra
   attention to `/debate` VETO-floor sessions in the window).
3. **Promote:** after the soak window, `mv SKILL.md.shadow.md SKILL.md`
   under the SKILL.md sentinel gate (`check_skill_patch_sentinel.py`
   requires this SP on disk) and update frontmatter `status: promoted`,
   `promoted_at`.

## Honest residuals

- The content-preservation proof is normalized-line containment (headings
  + stripped non-heading lines), not byte identity; ordering inside
  reference files was reviewed by the Wave C author, not machine-proven.
- Est-token figures are the 4-chars-per-token heuristic of
  `context-budget.py`, not the Anthropic tokenizer.
- Activation-time saving is realized only if agents actually Read
  references on demand; for a VETO-floor reviewer skill this is a
  behavioral risk, not just an efficiency one — the parallel-shadow soak
  plus `skill-health.py` discovery telemetry is the explicit guard, and a
  degraded soak window is grounds to reject promote.

## ⚠ Fix-before-apply (CEO note, S261)

The staged `SKILL.md` changelog line (`## Changelog` → `**1.0.0** …`) cites
**SP-022**; it must read **SP-023** (this proposal). The one-word fix could
not be applied by the night-run CEO because the SKILL.md canonical guard
(ADR-031) correctly refuses SKILL.md edits outside the `CEO_SKILL_PATCH_SHA`
ceremony — which is exactly this `/skill-review` step. Fix the line during
review, then re-pin `sha256_of_diff`/loader sha (the reproduction command is
in the Patch-source section above) before promote. Nothing else in the
staged tree references the wrong number.

> **Soak waiver S263 (2026-07-09):** 7-day parallel-shadow window waived by explicit Owner decision (single-user dogfood; pre-authorized skip semantics of --promote --force-recover). SP-026/SP-034 (AFTER-C) excluded — they keep the full soak.
