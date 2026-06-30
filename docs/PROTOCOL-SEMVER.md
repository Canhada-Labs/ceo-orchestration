# PROTOCOL.md semver discipline

> **Doctrine port**: github/spec-kit `templates/commands/constitution.md:L302-L305`.
> **PLAN-110 Wave D deliverable.** Operator-facing.

PROTOCOL.md is the governance contract. Edits to it MUST follow semver:

| Bump  | Trigger                                                         |
|-------|-----------------------------------------------------------------|
| MAJOR | Breaking change to Plan->Debate->Execute flow, veto semantics, 3-strike. |
| MINOR | Additive doctrine (new gate, new tier, new archetype role).      |
| PATCH | Typo, formatting, link-fix, non-doctrinal clarification.         |

## Sync Impact Report cascade

Every MAJOR + MINOR PROTOCOL.md edit MUST ship paired with:

1. **ADR-NNN-AMEND-M** — the formal record of WHY the protocol changed.
2. **Sync Impact Report section in the PR/commit body** — lists every
   downstream artifact updated to reflect the new protocol:
   - CLAUDE.md §Critical Rules
   - .claude/team.md / frontend-team.md (if archetype-affecting)
   - .claude/skills/core/ceo-orchestration/SKILL.md (if Gate-N affecting)
   - PLAN-SCHEMA.md / DEBATE-SCHEMA.md (if schema-affecting)
3. **Advisory hook** `check_protocol_semver_cascade.py` — PreToolUse
   warning when PROTOCOL.md is edited without an ADR-AMEND in the same
   session. Fail-OPEN (non-blocking).

### Machine-emitted Sync Impact Report (PLAN-138 Wave D, ADR-156)

Since PLAN-138 the Sync Impact Report is **partly machine-emitted**. The
hook `check_protocol_semver_cascade.py` re-verifies a **small, explicit
dependent-set** on ANY PROTOCOL.md edit and ships a Sync Impact Report
through `additionalContext` on **both** the well-behaved paired-amend
path **and** the no-amend path (the no-amend path additionally carries
the legacy missing-amend WARN as an extra line). The author still writes
the prose Sync Impact Report in the PR/commit body (item 2 above); the
machine report is an advisory cross-check, never a substitute.

The dependent-set (keyed on **structural anchors** — section headings /
frontmatter markers, not byte/line counts — so renumbers and additive
edits like Wave A's PLAN-SCHEMA §14 do not cry wolf):

| # | Dependent artifact | Structural anchor probed |
|---|---|---|
| 1 | `CLAUDE.md` §Critical Rules | heading text `Critical Rules` present |
| 2 | `PLAN-SCHEMA.md` §5 | H2 heading `## 5. Required body sections` present |
| 3 | `ceo-orchestration` `SKILL.md` | YAML frontmatter `name:`+`description:` valid (LINT-FM-04/05) |
| 4 | `DEBATE-SCHEMA.md` | file present + non-empty |
| 5 | `validate-governance.sh` | still references `PLAN-SCHEMA` |

Properties of the machine report (ADR-156) — the **dependent-set is
advisory / fail-open / booleans-only**:

- **Advisory + fail-OPEN ALWAYS** — the dependent-set probe NEVER emits
  `permissionDecision`, never increments `ERRORS`, never blocks the
  Owner GPG ceremony. A missing/binary/unreadable dependent file is
  reported `INDETERMINATE`, not an error.
- **Booleans/counts only** — each item is reported `PRESENT` /
  `MISSING/DRIFT` / `INDETERMINATE`; matched file text is **never**
  echoed. Every rendered fragment is clamped to printable ASCII +
  bounded length (Codex S228 injection defense) so a dependent file
  carrying control chars cannot forge an extra report line.
- **Kill-switch** `CEO_PROTOCOL_SYNC_CASCADE=0` suppresses the machine
  report entirely (the legacy missing-amend WARN still ships). The hook
  exits 0 regardless.
- **Sub-2s deadline** (`TIME_BUDGET_S`, checked in every probe loop) +
  per-file read cap; a non-PROTOCOL edit short-circuits with **zero**
  dependent-set file reads.

## PATCH-only allowance (advisory exception)

PATCH bumps may ship WITHOUT an ADR-AMEND iff:

- The edit changes ZERO doctrinal text (verbs like SHALL/MUST/MAY remain
  byte-identical).
- The diff is whitespace-only, link-fix, typo-only, or markdown formatting.

The advisory hook will still emit a warning event; Owner may dismiss.

## Audit action

New audit action: `protocol_edit_missing_amend_paired` (PLAN-110 Wave D
kernel-override `CEO_KERNEL_OVERRIDE=PLAN-110-WAVE-D-AUDIT-EMIT-EXTENSION`
+ `CEO_KERNEL_OVERRIDE_ACK=I-ACCEPT`).

Caller fields: `protocol_path`, `amend_present`, `hook_origin`,
`session_id` (if available), `timestamp_iso`.

## Reversion

Wave D revert path: REVERT PROTOCOL.md §semver doctrine + DELETE
`check_protocol_semver_cascade.py` + REVERT `_KNOWN_ACTIONS` allowlist
extension (kernel-override required per S136 lesson).
