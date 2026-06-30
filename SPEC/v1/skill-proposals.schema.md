# SPEC v1 — skill-proposals.schema

> **Normative source:** `.claude/adr/ADR-031-self-improving-skills.md`
> **Spec version:** 1.0.0-rc.1

## Summary (normative)

Skill-patch proposals are markdown files with YAML frontmatter living
under:

```
.claude/proposals/SP-<NNN>-<skill-slug>-<YYYY-MM-DD>.md
```

- `NNN` is a zero-padded 3-digit monotonic sequence scoped to the
  `proposals/` directory (nothing resets it — `SP-001` is permanent even
  after the proposal is retired).
- `skill-slug` matches the target SKILL.md's parent directory slug
  (e.g. `security-and-auth`). Kebab-case.
- `YYYY-MM-DD` is the UTC calendar date the proposal was drafted.

Rejected proposals (failed scan-injection, oversized diff, etc.) are
written to `SP-REJECTED-<YYYYMMDDThhmmss>.md` for forensic purposes and
do NOT consume a sequence number.

## Directory layout

```
.claude/proposals/
  README.md                                             # explains semantics
  .gitkeep                                              # ensures dir exists
  SP-001-security-and-auth-2026-04-14.md                # draft|shadow|promoted|retired
  SP-001-security-and-auth-2026-04-14.md.asc            # detached GPG signature (after approval)
  SP-REJECTED-20260414T101500.md                        # forensic-only, no signature
  ...
```

## Frontmatter schema (normative)

```yaml
---
id: SP-NNN                       # required, string, matches filename
skill_slug: <slug>               # required, matches target SKILL.md parent dir
archetype: <slug>                # required, archetype that surfaced the lessons
proposed_at: 2026-04-14T12:00:00Z # required, ISO-8601 UTC second-precision
source_lessons:                  # required, non-empty list of lesson IDs
  - <lesson_id_1>
  - <lesson_id_2>
scan_injection_pass: true        # required, bool — must be true to reach shadow
diff_size_added: <int>           # required, count of `+` lines in unified diff
diff_size_removed: <int>         # required, count of `-` lines in unified diff
sha256_of_diff: <64-char-hex>    # required, SHA-256 of the raw unified diff string
claims_declared: <bool>          # required, CR1 row #9 — confidence gate wire-up marker
status: draft                    # required, enum: draft|shadow|promoted|retired
approved_by: null                # null until apply; SHA256 fingerprint of signing GPG key afterward
applied_at: null                 # null until apply; ISO-8601 UTC when written to .shadow.md
promoted_at: null                # null until promote; ISO-8601 UTC when merged to real SKILL.md
shadow_mode: true                # true during draft+shadow; false after promote
---
```

### Status lifecycle (normative)

```
draft  ──(apply + Owner signature + confirm phrase)──▶ shadow
shadow ──(apply --promote, ≥7d since proposed_at, re-signed)──▶ promoted
shadow ──(explicit delete / Owner decision)──▶ retired
any    ──(manual Owner override)──▶ retired
```

- `draft → shadow` requires: detached GPG signature verifies, confirm
  phrase matches exactly, no other proposal already in shadow for same
  `skill_slug`.
- `shadow → promoted` requires: `proposed_at` is at least 7 days before
  apply time, re-verification of signature, confirm phrase matches.
- `retired` is terminal. Retired proposals stay on disk for audit but
  the sentinel will refuse to use them to gate any future SKILL.md
  write.

### Hash trailer format (normative)

After a successful promote, the Owner commits the modified SKILL.md
with a trailer line in the commit message body:

```
Skill-Patch-SHA: <64-char-hex>
```

The hex value MUST equal `sha256_of_diff` from the proposal frontmatter.
Both `check_canonical_edit.py` (via sentinel) and
`check_skill_patch_sentinel.py` (via `CEO_SKILL_PATCH_SHA` env var that
the Owner sets during the commit session) verify the trailer matches
the proposal hash.

## Rejection artifact schema

```yaml
---
kind: skill_patch_rejected
rejected_at: <ISO-8601>
reason_code: <enum>
---
```

`reason_code` is one of:

- `scan_injection_hit` — Sprint-5 scanner flagged the source lesson
- `bidi_or_zero_width` — Unicode attack characters in the rendered preview
- `homoglyph_hit` — mixed-script identifier detected (heuristic)
- `fenced_executable_code` — fenced code block in python|bash|sh|js|ts
  without `CEO_SKILL_PATCH_ALLOW_CODE=1`
- `diff_too_large` — added + removed lines exceeds 200
- `subprocess_error` — `scan-injection.py` returned non-zero
- `skill_target_missing` — the target SKILL.md doesn't exist
- `long_line_hidden_payload` — a single line exceeds 8000 chars in the
  source lesson (rejected as a truncation-attack vector)

## Audit events

Emitted at each stage (see `_lib/audit_emit.py`):

- `draft → shadow`: `skill_patch_applied(shadow_mode=True)`
- `shadow → promoted`: `skill_patch_applied(shadow_mode=False)`
- Rejections do NOT emit an audit event in Sprint 11 (they write a
  breadcrumb to `SP-REJECTED-*.md`). Sprint 12 may register
  `skill_patch_rejected`.

## CLI contracts

```
skill-patch-propose.py \
    --archetype <slug> \
    --skill <slug> \
    --lessons <dir-or-glob> \
    [--skill-md <path>]              # override default skill path resolution
```

Exit codes:
- 0 — proposal drafted (may be silently no-op if `CEO_SOTA_DISABLE=1`)
- 1 — rejection recorded in `SP-REJECTED-*.md`
- 2 — I/O or argument error

```
skill-patch-apply.py \
    --proposal SP-NNN \
    --signature <path> \
    --confirm "I have read SP-NNN" \
    [--promote]
```

Exit codes:
- 0 — apply succeeded (shadow write OR promote)
- 2 — signature missing or invalid
- 3 — confirm phrase wrong
- 4 — `--promote` requested too early (< 7 days since `proposed_at`)
- 5 — proposal not found or malformed frontmatter
- 6 — shadow file missing when `--promote` requested
- 7 — already promoted

## Feature flag

`CEO_SOTA_DISABLE=1`:
- `skill-patch-propose.py` exits 0 after printing a single-line
  no-op message to stderr. No file written.
- `skill-patch-apply.py` exits 0 after printing a single-line
  no-op message to stderr. No file written.
- `check_skill_patch_sentinel.py` is **NOT** disabled by this flag (it
  is a safety surface, not a feature).

## Related

- ADR-031 (self-improving skills — the decision)
- ADR-010 (canonical-edit sentinel — adjacent pattern)
- ADR-011 (injection_flag — observability pattern dogfooded here)
- `SPEC/v1/audit-log.schema.md` v2.4 (`skill_patch_applied` action)
