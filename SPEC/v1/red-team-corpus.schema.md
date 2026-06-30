---
status: accepted
spec_version: 1.0.0
created: 2026-04-15
plan: PLAN-014
phase: D.2
supersedes: none
---

# SPEC/v1/red-team-corpus.schema.md -- Frozen Red-Team Corpus Contract

**Version:** 1.0.0 (PLAN-014 Phase D.2, Sprint 14)
**Status:** accepted
**Authoritative source:** `.claude/scripts/red-team-corpus/v1/fixtures.jsonl`

## 0. Purpose

This SPEC defines the frozen red-team adversarial corpus format, versioning
policy, FPR measurement binding, and refresh procedure. The frozen corpus
is the ONLY input against which False Positive Rate (FPR) is measured.
Ad-hoc fixture additions do NOT affect the FPR baseline until a new frozen
version is cut.

Companion documents:
- ADR-037 -- Chaos + load testing methodology (State 0 to 1 transition)
- `.claude/scripts/red-team-eval.py` -- corpus runner
- `.claude/scripts/red-team-corpus/provenance.md` -- per-fixture provenance
- `.github/workflows/red-team.yml` -- CI workflow (State 1 enforcing)

---

## 1. Version + Status

| Field | Value |
|---|---|
| Schema version | `1.0.0` |
| Schema status | `accepted` |
| Spec lifetime | v1.x.y -- additive only per section 10 |
| Authoritative source | `.claude/scripts/red-team-corpus/v1/fixtures.jsonl` |

## 2. Corpus Layout

```
.claude/scripts/red-team-corpus/
  v1/
    fixtures.jsonl          # frozen corpus (one fixture per line)
    fixtures.jsonl.sha256   # adjacent SHA-256 checksum
  synthetic/                # source: hand-crafted adversarial fixtures
  external/                 # source: governance-bypass + public dataset fixtures
  regression/               # source: regression-from-past-incidents fixtures
  provenance.md             # per-fixture SHA + license + rationale
  .byte-identity-check.txt  # per-file SHA-256 ledger
  flake-budget.yaml         # quarantine policy
  README.md                 # corpus documentation
```

## 3. Fixture Format (JSONL)

Each line in `fixtures.jsonl` is a self-contained JSON object:

```json
{
  "id": "SYN-001",
  "target": "<target_id>",
  "category": "<kebab-case-taxonomy>",
  "input": "<adversarial payload string>",
  "expected_behavior": "<behavior_code>",
  "reference": "<ADR/CVE/paper citation>",
  "severity": "<LOW|MEDIUM|HIGH|CRITICAL>",
  "notes": "<optional reviewer guidance>"
}
```

### 3.1 Required Fields

| Field | Type | Constraint |
|---|---|---|
| `id` | string | Unique. Pattern: `SYN-NNN`, `EXT-NNN`, or `REG-NNN` |
| `target` | string | Closed enum (section 4) |
| `category` | string | Free-form kebab-case taxonomy slug |
| `input` | string | Adversarial payload (JSON-escaped) |
| `expected_behavior` | string | Closed enum (section 5) |
| `reference` | string | ADR/CVE/paper citation |

### 3.2 Optional Fields

| Field | Type | Default |
|---|---|---|
| `severity` | string | `MEDIUM` |
| `notes` | string | empty |

## 4. Target Enum (closed)

| Target ID | Defense Under Test |
|---|---|
| `skill_patch_sentinel` | check_skill_patch_sentinel.py |
| `audit_log_tamper` | _lib/audit_emit.py filelock + append-only |
| `plan_id_spoof` | _lib/plan_frontmatter.py + state_store ACL |
| `sandbox_escape` | check_bash_safety.py + egress allowlist |
| `mcp_handler` | MCP server ACL + governance passthrough |
| `adapter_exfil` | _lib/adapters/live/ credential hygiene |
| `output_safety_evasion` | check_output_safety.py pipeline |
| `npm_tamper` | npm/ shim SHA-256 + SLSA |

Adding a new target requires a SPEC amendment (section 10).

## 5. Expected Behavior Enum (closed)

| Code | Meaning |
|---|---|
| `MUST_BLOCK` | Defense must reject/block the input |
| `MUST_SANITIZE` | Defense must sanitize/redact sensitive content |
| `MUST_EMIT_AUDIT` | Defense must emit an audit trail event |
| `MUST_REJECT` | Defense must reject with explicit denial |
| `MUST_QUARANTINE` | Defense must quarantine the fixture |

## 6. Fixture ID Namespaces

| Prefix | Source | Range |
|---|---|---|
| `SYN-` | Hand-crafted synthetic | SYN-001 through SYN-999 |
| `EXT-` | External dataset / governance-bypass | EXT-001 through EXT-999 |
| `REG-` | Regression from past incidents | REG-001 through REG-999 |

IDs are monotonic within each namespace. Gaps are permitted (deleted
fixtures are NOT renumbered).

## 7. Frozen Corpus Versioning

| Property | Value |
|---|---|
| Current version | v1 |
| Location | `.claude/scripts/red-team-corpus/v1/fixtures.jsonl` |
| Checksum | `.claude/scripts/red-team-corpus/v1/fixtures.jsonl.sha256` |
| Fixture count | 67 (v1 baseline) |

### 7.1 Version Lifecycle

1. **Frozen:** Once a version is published, its `fixtures.jsonl` is
   immutable. The SHA-256 checksum is the identity proof.
2. **FPR binding:** FPR measurements reference exactly one frozen version.
   Comparing FPR across versions requires the v(N)-vs-v(N+1) diff report.
3. **Refresh:** Creating v2 requires:
   - ADR-037 amendment documenting the reason
   - v1-vs-v2 FPR diff (same runner, both corpora, side-by-side)
   - New `v2/fixtures.jsonl` + `v2/fixtures.jsonl.sha256`
   - Provenance.md update for all new fixtures

### 7.2 SHA-256 Pre-check

The runner (`red-team-eval.py`) MUST verify the frozen corpus SHA-256
before evaluating any fixture. If the checksum does not match, the
runner exits with code 2 (invalid fixture).

## 8. FPR Measurement Contract

- FPR = (false positives) / (total fixtures evaluated)
- Measured ONLY against the frozen corpus version
- Target: FPR < 5% across 50+ spawn evaluations (ADR-037 State 0 to 1)
- Baseline established at corpus freeze time
- Regression = FPR increase beyond baseline + tolerance (1%)

## 9. Security Constraints

- Fixtures contain SIMULATED payloads only
- No live malware, no weaponized exploits
- Stub strings used for dangerous patterns (e.g., GPG keys)
- External dataset binaries NEVER committed
- Provenance documented per ADJ-023

## 10. Versioning (additive-only)

New fields MAY be added to the fixture format. Existing fields MUST NOT
be removed or have their semantics changed. New target or behavior enum
values require a minor version bump (1.x.0).

Breaking changes (field removal, semantic change) require a major version
bump and a new SPEC document.

## 11. References

- PLAN-014 Phase D.1-D.2 (corpus expansion + FPR gate)
- ADR-037 (chaos testing methodology + State transitions)
- PLAN-013 consensus C9/S16/S17 (corpus requirements)
- `.claude/scripts/red-team-eval.py` (runner)
- `.claude/scripts/red-team-corpus/provenance.md` (per-fixture provenance)
