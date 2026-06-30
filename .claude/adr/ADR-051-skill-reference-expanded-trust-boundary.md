# ADR-051: Skill-by-reference expanded trust boundary

**Status:** ACCEPTED (flipped PLAN-025 Batch C — live per PLAN-020 Phase 2 commit c53c4dd (check_skill_reference_read.py + 10 sub-checks + 34 tests))
**Date:** 2026-04-17 (pre-authored during PLAN-020 Phase 0a per Q5 Owner default)
**Deciders:** CEO, Principal Security, VP Engineering, Principal QA Architect
**Blast radius:** L3 (spawn dispatcher trust boundary + new PostToolUse hook + redaction contract)
**Supersedes:** none
**Superseded by:** none

## Context

PLAN-020 Phase 2 introduces a new spawn-prompt format that replaces
inline skill content with a hash-pinned file reference:

```markdown
## SKILL REFERENCE

@.claude/skills/core/code-review-checklist/SKILL.md sha256=<64-hex>

(optional human-readable 256+ byte summary)
```

This trades **inline byte cost** for **file system trust boundary**:
the sub-agent must Read the referenced SKILL.md, and that read must
match the pinned SHA-256 hash. If the file was modified between hash
computation and read, the contract is violated.

Today's `_has_skill_content` checks the inline body byte count
(≥256 non-ws after fence/comment masking). Phase 2 ADDS
`_has_skill_reference` as a parallel accept path — it does NOT
relax the inline path. Adopters can use either.

The new trust boundary is the file system. An attacker who can write
to `.claude/skills/` could:
- Inject prompt-injection payloads into a SKILL.md
- Replace a legitimate SKILL.md with a malicious one
- Race the hash check (TOCTOU between hash computation and Read)
- Trigger DoS via a 100MB SKILL.md
- Symlink-traverse outside the skills root

ADR-051 specifies the defenses against each.

## Decision

Add `_has_skill_reference()` as an **additive** accept-path in
`check_agent_spawn.py::decide()`. Does NOT replace `_has_skill_content`.
8 existing `TestSkillContentMarkerRobustness` cases continue to pass
unchanged (A5 byte-fidelity acceptance).

### Sentinel format (new)

```markdown
## SKILL REFERENCE

@<absolute-or-relative-path-to-SKILL.md> sha256=<64-hex>

(optional human-readable 256+ byte summary of the skill's key rules,
to help the sub-agent reason before it Reads the referenced file)
```

The `@path sha256=hex` line is the sentinel. The optional summary
helps the sub-agent reason without paying for the full Read tool call
upfront, and serves as fallback context if the Read tool call fails.

### Synchronous validation (10 sub-checks, fail-CLOSED)

`_has_skill_reference()` validates the sentinel in this exact order
(short-circuit on first failure):

1. **Sentinel present.** Regex match `^## SKILL REFERENCE\s*$\n+@(\S+)
   sha256=([0-9a-f]{64})\b` (anchored, case-sensitive). Returns
   `(path, hash)` or False.

2. **Path resolves.** `Path(path).resolve(strict=True)` succeeds.
   Reason code on fail: `reference_missing`.

3. **Path under skills root.** Resolved path is under
   `<project_dir>/.claude/skills/` via `.resolve().relative_to(skills_root)`
   (real path, not substring prefix). Reason: `reference_outside_skills_root`.

4. **Filename is SKILL.md.** `Path.name == "SKILL.md"` exactly. Reason:
   `reference_wrong_filename`.

5. **Not a symlink.** `Path.is_symlink() → False`. Reason:
   `reference_symlink_refused`.

6. **NFC unicode normalization.** `unicodedata.normalize("NFC", str(path))
   == str(path)`. Reason: `reference_unicode_normalization_mismatch`.

7. **Size cap.** `Path.stat().st_size <= 1_048_576` (1 MiB). Reason:
   `reference_too_large`.

8. **Body byte floor.** Non-whitespace byte count of file content ≥ 512
   (distinct from inline `_has_skill_content` 256 floor). Reason:
   `reference_byte_floor_underflow`.

9. **YAML frontmatter parses + has `name:` key (lowercase).** Stdlib-
   only frontmatter reader. Reason: `reference_missing_frontmatter`.

10. **SHA-256 hash matches.** `hashlib.sha256(content).hexdigest() == hash`.
    Reason: `reference_hash_mismatch`.

11. **Redaction scan.** `_lib.redact.redact_secrets(content)` applied;
    block if any secret family triggers. Reason: `reference_redaction_hit`.

(Counted as 10 sub-checks because the sentinel-present check is the
match precondition, not a sub-check.)

**Fail-CLOSED on every step.** Emits:
```json
{"decision":"block","reason":"GOVERNANCE: <reason_code>: <detail>"}
```

The `_has_skill_content` inline path retains fail-OPEN on infrastructure
exceptions per ADR-005 compatibility. The reference path is stricter.

### Telemetry reason codes (12 enum)

Added to audit-log v2.7 schema:

- `missing_skill_content` (existing — inline path)
- `reference_missing`
- `reference_unsafe_path`
- `reference_hash_mismatch`
- `reference_symlink_refused`
- `reference_too_large`
- `reference_redaction_hit`
- `reference_wrong_filename`
- `reference_missing_frontmatter`
- `reference_byte_floor_underflow`
- `reference_unicode_normalization_mismatch`
- `reference_outside_skills_root`

Each reason emitted via `_lib.audit_emit.emit_veto_triggered`.

### Sub-agent obligation

Inline system reminder in spawn prompt:

> "MUST re-hash the referenced SKILL.md after Read; on mismatch, abort
> task and report to CEO."

PostToolUse observer hook `check_skill_reference_read.py` verifies
the first Read tool call of the sub-agent against the pinned hash.
Emits `veto_triggered` with reason `reference_postread_mismatch` if
the file changed between sentinel hash computation and sub-agent
Read. This does NOT undo the damage (the spawn is in-flight) but
produces audit-log breadcrumb for forensic.

### `inject-agent-context.sh --mode=reference`

New flag emits prompt with `## SKILL REFERENCE` sentinel + hash
pre-computed at build time. CEO invokes:

```bash
.claude/scripts/inject-agent-context.sh <Agent> "<task>" --mode=reference
```

Output sentinel format matches the synchronous validation regex.

### `validate-governance.sh` extension

New step: `grep -rE "^@\\.?/?\\.claude/skills/.*SKILL\\.md sha256=" templates/`
finds reference sentinels in spawn templates. Verifies (a) referenced
file exists, (b) parseable frontmatter, (c) `name:` key. Catches
broken references in CI, not at spawn time. Budget ≤2s.

### `ENABLE_SKILL_REFERENCE_MODE` module-level constant

In `check_agent_spawn.py` toggled via `CEO_SKILL_REFERENCE_MODE`.
- `=1` (default): both inline + reference paths accept.
- `=0`: rewrites `--mode=reference` invocations to inline (forward-
  compatible degradation; sub-agent still gets skill content, just
  via inline rather than reference).
- Phase 2 commit revert = single-line flip to `False`.
- Independent of `ENABLE_NATIVE_SUBAGENTS` (Phase 1) and
  `CEO_SOTA_DISABLE` (master).

## Consequences

**Positive:**

- ~25.2% projected reduction in spawn-prompt tokens for canonical
  archetypes (Phase 0 baseline measurement; security-engineer skill
  saves more due to larger SKILL.md size).
- Sub-agent Read of SKILL.md happens in subagent's cache lane, not
  CEO's — better cache amortization across multiple spawns of same
  archetype within a session.
- Hash-pin contract gives forensic trail: `reference_hash_mismatch`
  in audit log proves SKILL.md was modified mid-session (or
  attacker swap detected).
- 12 telemetry reason codes provide observability into reference-mode
  failure modes (vs single `missing_skill_content` reason today).
- Symlink + NFC + size-cap defenses block 4 specific classes of
  attacks identified in Security debate critique §M3.

**Negative:**

- Trust boundary expanded to file system. Mitigated by 10 synchronous
  sub-checks + sub-agent re-hash obligation + PostToolUse observer
  hook.
- Adopter-authored `.claude/skills/**/SKILL.md` files become an
  attack surface IF the adopter accepts an untrusted SKILL.md PR.
  Mitigated by `_lib.redact` ingestion (Security Nice-to-have #3
  prompt-injection scan) and `validate-governance.sh` extension.
- Sub-agent must perform 1 Read tool call to obtain skill content.
  Cost: ~10ms wall-clock + ~50 tool-call protocol tokens. Net token
  saving still strongly positive (~6,900 → ~5,165 + 50 = 5,215
  tokens; -24% net).
- Hash-pin computed at build time is racy if SKILL.md modified
  between build and spawn. Mitigated by sub-agent re-hash + PostToolUse
  observer.

**Trade-offs explicitly accepted:**

- We do NOT remove the inline `_has_skill_content` path. Both paths
  parallel; adopters opt into reference mode at injection time.
- We do NOT relax the inline 256-byte floor. P1-SEC-B hardening
  byte-identical preserved (A5 acceptance).
- We do NOT verify the YAML frontmatter beyond presence of `name:`
  key. Schema validation deferred (could grow in Sprint 21+).
- We do NOT cache the hash computation or the Read result. Every
  spawn re-hashes; every sub-agent re-Reads. Correctness > cost.

## Threat model

| Threat | Defense | Reason code |
|--------|---------|------------|
| Path traversal `../../../../etc/passwd` | Sub-check 3 (resolve.relative_to skills_root) | `reference_outside_skills_root` |
| Symlink escape | Sub-check 5 (`is_symlink → False`) | `reference_symlink_refused` |
| TOCTOU hash race | Sub-check 10 (resync hash post-Read) + PostToolUse re-hash | `reference_hash_mismatch` |
| DoS via 100MB SKILL.md | Sub-check 7 (1 MiB size cap) | `reference_too_large` |
| Unicode confusable swap | Sub-check 6 (NFC normalization) | `reference_unicode_normalization_mismatch` |
| Wrong file type (e.g., `team.md`) | Sub-check 4 (filename == SKILL.md) | `reference_wrong_filename` |
| Empty / under-sized stub | Sub-check 8 (512-byte floor) | `reference_byte_floor_underflow` |
| Missing YAML frontmatter | Sub-check 9 (frontmatter parse + `name:` key) | `reference_missing_frontmatter` |
| Secret leak in SKILL.md | Sub-check 11 (redact ingestion scan) | `reference_redaction_hit` |
| Generic bypass attempt | Sub-check 1 (regex match strict) | `reference_missing` |

## Acceptance for ADR-051 closure

(Tracked in PLAN-020 §10 Success criteria — A1, A3, A5 + benchmark
sub-target on spawn-prompt token reduction.)

- [ ] `_has_skill_reference()` lands in `check_agent_spawn.py` as
      additive accept-path.
- [ ] All 10 synchronous sub-checks implemented + each has ≥1
      negative test case.
- [ ] 12 telemetry reason codes wired through `_lib.audit_emit`.
- [ ] PostToolUse hook `check_skill_reference_read.py` lands +
      registered in `.claude/settings.json`.
- [ ] `inject-agent-context.sh --mode=reference` functional.
- [ ] `validate-governance.sh` extension lints reference sentinels.
- [ ] `tests/formal_verification/mutation_fixtures/skill_content/`
      ≥8 mutation fixtures with 100% kill rate.
- [ ] `test_check_agent_spawn_reference_bypass.py` ≥30 bypass vectors
      across 14 attack classes — all blocked.
- [ ] PLAN-019 `TestSkillContentMarkerRobustness` (8 cases) all pass
      unchanged (A5 byte-fidelity).
- [ ] Spawn-prompt token reduction on reference rail ≥20% measured
      vs Phase 0 inline baseline (Phase 6 acceptance §6 sub-target).

## References

- PLAN-020 §4 Phase 2 (skill-by-reference design)
- PLAN-020 §6.1 Q1 Owner answer (hash-pin inline = YES)
- PLAN-020 §6a Kill-switch matrix
- ADR-050 (native subagents; reference sentinel is the format used by
  native rail)
- Principal Security debate critique §S1 must-fix #3 (14 bypass classes)
- Performance debate critique §S1 must-fix #5 (decomposition: spawn-
  prompt tokens delta sub-target)
- QA debate critique §S1 must-fix #1 (deterministic acceptance over
  LLM judge)
- ADR-005 (fail-open contract for inline path; reference path is
  stricter exception)
- P1-SEC-B (PLAN-019 inline byte floor + fence/comment mask hardening
  preserved)

## Enforcement commit

`3917fec1bfd9` (retrofit — PLAN-050 Phase 2 / PLAN-045 F-06-03; this anchors the file's introduction commit, not a runtime-behavior commit. For ADRs whose decision was wired into hooks/scripts in a later commit, amend this line manually.)
