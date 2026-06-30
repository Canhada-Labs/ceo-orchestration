---
id: ADR-078
title: Sentinel co-sign vs. ADR forensic co-sign — semantic distinction (PLAN-064 amendment — lexical scope markers)
status: ACCEPTED
created: 2026-04-24
accepted_at: 2026-04-24
amended_at: 2026-05-04
amended_via: PLAN-064 architect/round-1 sentinel (Path B / Option D pivot)
accepted_via: Round-23 sentinel (PLAN-058 Phase B closure batch)
proposed_by: CEO (Session 60 PLAN-058 Round-23, addressing Phase B audit C-P0-08 / F-SEC-05)
amended_by: CEO (Session 84 — Round 1 consensus pivot to Option D; closes Codex audit-v3 DIM-13)
co_signers: [VP Engineering (architecture clarity), Principal Security Engineer (forensic-record integrity), DevOps Engineer (PLAN-064 ceremony cost analysis)]
related_plans: [PLAN-058, PLAN-063, PLAN-064]
related_adrs: [ADR-031, ADR-077]
blast_radius: L2 (parser-side disambiguation; cryptographic trust-chain unchanged)
supersedes: none
superseded_by: none
closes_finding: PLAN-058 Phase B C-P0-08 (Security F-SEC-05) + PLAN-063 Codex audit-v3 DIM-13 (parser ambiguity)
staged_at: bb0da49
enforcement_commit: bb0da49
amendment_enforcement_commit: <PLAN-064 ceremony commit, TBD>
---

# ADR-078 — Sentinel co-sign vs. ADR forensic co-sign + lexical scope markers

## Context

### Original (Round-23, 2026-04-24)

Phase B audit (Session 59 cont³) flagged a semantic conflation
inside the Round-21 sentinel for ADR-077. Two distinct co-sign
layers were collapsed into one signer list:

1. **Sentinel scope co-signers** — the GPG signers of
   `architect/round-N/approved.md.asc` who authorize the canonical
   promote of the listed paths. Their authority is **operational**
   (they grant the CEO permission to write the canonical-guarded
   files). This is the layer enforced by `check_canonical_edit.py`.

2. **ADR forensic co-signers** — names recorded inside an ADR's
   `co_signers:` frontmatter field, attesting that those archetypes
   reviewed the architectural / security correctness of the decision
   itself. Their authority is **substantive** (they validate the
   design). This layer is documentary; it does not pass through
   `check_canonical_edit.py`.

Round-21 listed 8 GPG signers for the ADR-077 remediation scope and
ADR-077 internally listed `co_signers: [VP Engineering, Principal
Security Engineer]`. A reader interpreting Round-21 as "ADR-077 has
8 forensic reviewers" is mistaken — those 8 are the operational
authorizers of the canonical write, not the architectural reviewers.

### PLAN-064 amendment (Session 84, 2026-05-04)

Codex audit-v3 DIM-13 (P2) flagged a parser-ambiguity finding:
`check_canonical_edit.py:_sentinel_grants_path` could not distinguish
"scope was signed at time T1" from "lifecycle text was added at time
T2 outside the signed payload" because the parser used heuristic
`_SCOPE_HEADER_RE` to find the scope block. Lifecycle annotations
(status fields, verify timestamps, notes) inside the same `approved.md`
body could collide with the heuristic and either suppress legitimate
scope or — theoretically — mislead the parser.

PLAN-063 Round 1 debate consensus C1 lifted DIM-13 to a separate plan
(PLAN-064) for trust-chain redesign. PLAN-064 Round 1 debate (3
archetypes, 2026-05-04) evaluated three candidates:

- **Option A:** SHA-256 binding two-file format (`approved.md` +
  `verification.json`). Cleanest cryptographic contract but introduces
  4× under-counted migration scope (44 sentinels, not 10), 7 of 15
  named threats unmitigated, and ~60-90 min Owner-physical ceremony.
  Security verdict SOFT-REJECT.

- **Option D (VP Engineering surface):** Lexical scope markers via
  HTML comments. Closes the literal DIM-13 finding (parser ambiguity)
  with ~15-25 LoC parser change, no migration, ~5 min Owner-physical
  ceremony, HIGH reversibility.

- **Option G (Security Engineer surface):** Drop PLAN-064 entirely
  (DIM-13 is P2 *theoretical*, no empirical attack observed).

Round 1 consensus selected **Option D**. Owner directive Session 84
('faz o que da agora quando eu chegar em casa termino') authorized
execution.

## Decision

### Original — naming convention + clarifying header (unchanged)

| Layer | Field name | Stored at | Authority |
|---|---|---|---|
| Sentinel scope | `Approved-By:` (header) + GPG signers (`.asc`) | `architect/round-N/approved.md` | Operational — authorize canonical write |
| ADR forensic | `co_signers:` (frontmatter list) | `.claude/adr/ADR-NNN-*.md` | Substantive — validate design |

Every `architect/round-N/approved.md` file from Round-23 onward MUST
include the clarifying header before the `## Scope — paths covered`
section (text unchanged from original ADR-078; quoted in §References).

### PLAN-064 amendment — Lexical Scope Markers (2026-05-04)

In addition to the existing two-layer co-sign convention, sentinel
files MAY (and SHOULD for new sentinels) delimit the signed scope
manifest with explicit HTML-comment markers:

```markdown
<!-- BEGIN SIGNED SCOPE -->
Approved-By: @Canhada-Labs <commit-sha>
Plans: PLAN-NNN
Scope:
  - .claude/path/one.md
  - .claude/path/two.md
<!-- END SIGNED SCOPE -->

<!-- The lifecycle markers below are NOT part of the signed scope.
     They are documentation/state annotations only. The GPG signature
     covers the whole file (any tamper breaks .asc); these markers
     clarify parser priority per ADR-078 PLAN-064 amendment. -->

Status: PENDING_OWNER_GPG (or APPROVED, REVOKED, etc.)
Verified-At: <timestamp>
Notes: ...
```

`check_canonical_edit.py:_sentinel_grants_path` tier-prioritizes:

| Tier | Condition | Behavior |
|---|---|---|
| 1 | Markers present (both `<!-- BEGIN SIGNED SCOPE -->` AND `<!-- END SIGNED SCOPE -->` regex match) | Parse `Scope:` block ONLY from text inside the markers. Lifecycle text outside is ignored for grant decisions. |
| 2 | Markers absent (legacy 44 sentinels at 2026-05-04) | Fall back to existing `_SCOPE_HEADER_RE` parser. No env flag — auto-detected by marker presence. |

Implementation:
- `_SCOPE_MARKER_RE = re.compile(r"<!--\s*BEGIN\s+SIGNED\s+SCOPE\s*-->\s*\n(.*?)\n\s*<!--\s*END\s+SIGNED\s+SCOPE\s*-->", flags=re.DOTALL)`
- Length cap `_SCOPE_MARKER_CAP_BYTES = 64 * 1024` enforced before regex invocation (ReDoS defense; matches existing 4096-byte MCP path cap pattern).
- Helper `_parse_scope_paths_from_text(scope_text)` extracts paths via `_SCOPE_HEADER_RE` against either the marker region (Tier 1) or the full file text (Tier 2).
- Test surface: ≥15 unit tests in `test_check_canonical_edit_markers.py` covering Tier 1 happy path, Tier 2 fallback, mixed format isolation, malformed markers (BEGIN-only, END-only, repeated, homoglyph), ReDoS bench (≤100ms wall-clock on 64KiB input), GPG coverage invariant.

## Rationale

### Original (unchanged)

- **No enforcement change at the GPG layer.** Modifying
  `check_canonical_edit.py` to cross-verify ADR `co_signers:` against
  sentinel signers would entangle two orthogonal layers and increase
  blast radius without solving a real attack. Forensic co-signers are
  documentary; sentinel signers are gatekeepers.

### PLAN-064 amendment — why Option D over Option A

- **Closes DIM-13 literally.** DIM-13 was a *parser-ambiguity*
  finding — Codex flagged that the parser could not distinguish scope
  from lifecycle text. Lexical markers resolve that ambiguity at the
  parser layer: scope is what's between the markers, period. Anything
  else in the file is lifecycle annotation.

- **No new attack surface.** Option D adds ~5 LoC of regex constants
  + 1 helper function + tier-priority dispatch. No JSON/YAML parser
  (eliminates Security T6/T7/T8/T9), no `runtime.json` (eliminates
  T13 social-engineering vector), no `CEO_SENTINEL_LEGACY_FALLBACK`
  env flag (eliminates T12 `CEO_SENTINEL_UNLOCK` repeat anti-pattern),
  no atomic-write contract / TOCTOU window (eliminates T15), no
  parser-as-write-surface (P0-SEC-8 stays N/A — parser remains
  read-only).

- **Backward compatible by construction.** Existing 44 sentinels lack
  markers → Tier 2 fallback kicks in silently. Zero migration. Zero
  re-sign. Zero Owner physical for legacy sentinels. Future plans
  naturally drift to v2 marker format as new sentinels are signed.

- **Cryptographic guarantees preserved.** GPG `.asc` still covers the
  full file (`approved.md`). Any tamper of either signed scope OR
  lifecycle annotations OR markers themselves breaks the signature.
  Option D adds a parser-side disambiguation only; it does not weaken
  or replace the existing crypto layer.

- **Honors ADR-096 vibecoder-only + ADR-103 calendar-gate purge.**
  DIM-13 was P2 *theoretical*; no empirical attack observed in
  S67-S83. The single-Owner / no-external-pressure context does not
  justify the 60-90 min Owner-physical ceremony Option A would
  require. Option D fits the empirical-ROI envelope.

### PLAN-064 amendment — why not Option A or Option G

- **Option A rejected (Round 1 SOFT-REJECT × 2):** Security R1 critique
  enumerated 8 P0 + 7 P1 + 6 P2 = 21 unconditional adjustments. Migration
  scope under-counted 4.4× (44 sentinels not 10). 7 of 15 named threats
  unmitigated as drafted. HARD VETO conditional on D6 (lifecycle
  revocation power). Migration cost vs. *theoretical* P2 finding =
  empirical-ROI negative.

- **Option G considered, declined:** Owner directive Session 84
  ('quero 100% do plan64 feito') overrides empirical-ROI argument per
  CEO protocol authority hierarchy. Option D threads the needle:
  respects directive (PLAN-064 ships, DIM-13 closes), respects
  empirical-ROI (cost minimal), respects security (no new attack
  surface).

## Consequences

### Original (unchanged)

- All `architect/round-N/approved.md` files created from Round-23
  onward MUST include the clarifying header.
- The `inject-agent-context.sh` helper (and any future sentinel
  scaffolding) updates its template to emit the header by default.
- No code change to `check_canonical_edit.py` from this layer. No
  enforcement delta. No baseline regression.
- Adopters reading the audit trail understand the two-layer co-sign
  model without re-deriving it from the codebase.

### PLAN-064 amendment

- **`check_canonical_edit.py:_sentinel_grants_path`** updated with
  Tier 1 / Tier 2 dispatch (~15-25 LoC delta + 1 helper extraction).
- **`SPEC/v1/sentinel-format.schema.md`** NEW — published spec for
  marker convention, parser tier resolution, backward compat policy.
- **Future sentinels (this PLAN-064 round-1 forward) SHOULD use markers**;
  the convention is template-emit-by-default once `inject-agent-context.sh`
  or equivalent scaffolding is updated (deferred to PLAN-067 v1.13.0
  if not bundled here).
- **Existing 44 sentinels (legacy format) parse via Tier 2 indefinitely.**
  No migration burden. Plan IDs covered: PLAN-044, PLAN-045, PLAN-050,
  PLAN-051, PLAN-052, PLAN-058, PLAN-059, PLAN-060, PLAN-061, PLAN-063,
  PLAN-065, PLAN-066, PLAN-068, PLAN-069, PLAN-073, PLAN-074, PLAN-075
  (18 plans, 44 sentinels enumerated in PLAN-064 §10.1).
- **DIM-13 closes** at Codex audit-v3 backlog. PLAN-063 §4 Phase 5
  finding marked CLOSED with PLAN-064 cross-reference.
- **No `CEO_SENTINEL_LEGACY_FALLBACK` env flag** introduced — auto-
  detection by marker presence is the contract.

## Acceptance

### Original (unchanged)

- This ADR ships canonical at `.claude/adr/ADR-078-*.md` with
  status `ACCEPTED` after Round-23 sentinel co-signs.
- Round-23 `approved.md` itself includes the clarifying header
  (self-demonstrating).
- Future sentinels (Round-24+) include the header — verified at
  ceremony time by reading the staged sentinel before signing.

### PLAN-064 amendment

- ADR-078 amendment ACCEPTED via PLAN-064 architect/round-1 sentinel
  GPG ceremony (Owner physical ~5 min, single sentinel covers ADR
  amendment + parser patch + SPEC NEW).
- Round-1 debate artifacts preserved at
  `.claude/plans/PLAN-064/debate/round-1/` (proposal.md +
  vp-engineering.md + security-engineer.md + devops.md +
  consensus.md).
- `test_check_canonical_edit_markers.py` GREEN (15/15 tests at
  ceremony time). Existing `test_check_canonical_edit.py` GREEN
  unchanged (50/50 tests, Tier-2 fallback covers existing 44
  sentinels).
- `validate-governance.sh` GREEN. `release.yml` 14-step gate GREEN.
- Tag `v1.12.2` ships with the parser update + ADR amendment + SPEC
  NEW.

## References

### Original

- PLAN-058 Phase B audit `audit/findings/security-engineer.md`
  F-SEC-05 (the conflation finding)
- ADR-031 (canonical-edit sentinel chain — operational layer)
- ADR-077 (the ADR that triggered the finding)
- `check_canonical_edit.py` (the operational enforcement)

Original clarifying header text (preserved verbatim):

> **Co-sign scope clarification (ADR-078):** The signers of this
> sentinel authorize the *canonical promote* of the listed paths.
> They are NOT making an architectural-review claim about the ADRs
> referenced inside. ADR architectural reviewers are recorded
> separately in each ADR's `co_signers:` frontmatter field.

### PLAN-064 amendment

- PLAN-064 plan: `.claude/plans/PLAN-064-signed-sentinel-content-separation.md`
- Round 1 debate artifacts: `.claude/plans/PLAN-064/debate/round-1/`
  - `proposal.md` (CEO input)
  - `vp-engineering.md` (VP Engineering critique — SOFT-REJECT, surfaced Option D)
  - `security-engineer.md` (Security critique — SOFT-REJECT, HARD VETO conditional on D6)
  - `devops.md` (DevOps critique — ADJUST, ceremony cost analysis)
  - `consensus.md` (CEO synthesis — Path B / Option D pivot)
- DIM-13 origin: PLAN-063 §4 Phase 5 (Codex audit-v3)
- Staged patches at PLAN-064/staged-patches/:
  - `check_canonical_edit.py.modified` (full file post-patch, ~28KB)
  - `check_canonical_edit.py.patch` (unified diff for review, ~10KB)
  - `ADR-078-amended.full.md` (this file)
  - `SPEC-sentinel-format-schema.full.md` (NEW SPEC v2.18 file)
- Test surface: `.claude/hooks/tests/test_check_canonical_edit_markers.py`
  (15 tests, GREEN against modified parser).
- ADR-096 vibecoder-only thesis (single-Owner empirical baseline).
- ADR-103 calendar-gate purge (estimates must be empirically anchored).
- ADR-058 round-1 debate convention (3 archetypes, convergence rule).
