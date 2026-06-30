# SPEC/v1/tier-policy.schema.md

> **Normative source:** SELF (self-authoritative — see ADR-007
> §Self-authoritative pattern). Paired-ADR: ADR-064 (dynamic tier
> policy learned dispatch).
>
> **Status:** Self-authoritative SPEC for PLAN-043 tier-policy
> artifact (`.claude/tier-policy.json`) + sigchain contract.
> Promoted from STAGED → canonical 2026-04-19 via PLAN-043 Phase 5
> kernel batch. See ADR-064 for context and ADR-007 §Self-
> authoritative pattern for the pattern rule.

**Version:** 1.0.0
**Published by:** PLAN-043 / ADR-064
**Governs:** `.claude/tier-policy.json` +
`.claude/tier-policy.json.sigchain` artifact shapes consumed by the
`ceo-tier-policy` CLI and the `tier_policy_cli/` Python modules
(renamed from `tier_policy/` per PLAN-076 fork (f), S89; the
underscore form is Python-importable via
`from tier_policy_cli import ...`).

> **Namespace note (PLAN-076 fork (f)):** the symbol
> `VETO_HARDCODE` is referenced under TWO distinct namespaces with
> DIFFERENT shapes; do not conflate when reading this schema or
> downstream code:
>
> - `tier_policy_cli._constants.VETO_HARDCODE`
>   (`Final[Dict[str, str]]`, role → model_id binding floor; this
>   schema's consumer)
> - `_lib.tier_policy._constants.VETO_HARDCODE`
>   (`Mapping[str, FrozenSet[str]]`, role → task_types advisory
>   floor; consumed by PLAN-071 `task-route.py`, NOT by this schema)

## 1. Design goals

- **stdlib-only (ADR-002)** — consumer (loader.py) parses via
  `json.loads` + custom hooks, no `jsonschema` dependency.
- **Default-deny extra keys** — unknown top-level or assignment-level
  keys reject (schema_violation) rather than silently drop.
- **Forward-compatible migration** — bump `schema_version` + add
  migration recipe in `loader._migrate_schema`; old version readers
  reject-then-fallback with `schema_version_unknown` reason.
- **Fail-open on corruption** — loader returns baseline + status tag;
  dispatcher never breaks on policy bugs (ADR-005).

## 2. Canonical shape — `.claude/tier-policy.json`

```json
{
  "schema_version": "1.0",
  "generated_at": "<ISO-8601 UTC, Z-suffixed>",
  "baseline_from": "ADR-052",
  "assignments": {
    "code-reviewer":         {"tier": "claude-opus-4-8",          "locked_by": "VETO_FLOOR", "evidence": null},
    "security-engineer":     {"tier": "claude-opus-4-8",          "locked_by": "VETO_FLOOR", "evidence": null},
    "qa-architect":          {"tier": "claude-sonnet-4-6",        "locked_by": null,         "evidence": null|<Evidence>},
    "performance-engineer":  {"tier": "claude-sonnet-4-6",        "locked_by": null,         "evidence": null|<Evidence>},
    "devops":                {"tier": "claude-haiku-4-5-20251001","locked_by": null,         "evidence": null|<Evidence>}
  },
  "hmac_anchor": "<64-hex-char HMAC-SHA256>",
  "sigchain_tip_length": 1,
  "last_change_by_role": {}
}
```

### 2.1 Top-level required keys (strict)

| Key                     | Type    | Required | Notes |
|-------------------------|---------|----------|-------|
| `schema_version`        | string  | yes      | MUST start "1." for v1 contract |
| `generated_at`          | string  | yes      | ISO-8601, Z-suffixed, 256-char cap |
| `baseline_from`         | string  | yes      | Always "ADR-052" in v1 |
| `assignments`           | object  | yes      | Exactly the 5 canonical-5 agent slugs |
| `hmac_anchor`           | string  | yes      | Exactly 64 lowercase hex chars |

### 2.2 Top-level optional keys

| Key                     | Type    | Default  | Notes |
|-------------------------|---------|----------|-------|
| `sigchain_tip_length`   | int     | 1        | ≥1; covers genesis entry |
| `last_change_by_role`   | object  | `{}`     | `{role: ISO-8601 timestamp}`; O(1) cooldown lookup |

**Any other top-level key rejects with `extra_keys` reason.**

### 2.3 Assignment shape

Each entry in `assignments`:

```json
{
  "tier": "<MODEL_ID>",
  "locked_by": null | "VETO_FLOOR" | "<other string ≤256 chars>",
  "evidence": null | {
    "n": <int ≥ 0>,
    "gap_pp": <float>,
    "last_updated": null | "<ISO-8601>",
    "runs_considered": <int ≥ 0>,
    "tournament_report_hmacs": ["<64-hex string>", ...]
  }
}
```

**Required:** `tier`, `locked_by`, `evidence` (all three keys MUST be
present, even when null).
**Model IDs (Literal enum):** `claude-opus-4-8`, `claude-sonnet-4-6`,
`claude-haiku-4-5-20251001`.

### 2.4 Security / DoS defenses (F-SEC-P1-2)

- File size cap: 64 KiB (`MAX_POLICY_FILE_BYTES`).
- JSON nesting depth cap: 8 (`MAX_JSON_NESTING`).
- `object_pairs_hook` rejects `__proto__`, `constructor`, `prototype`
  keys at any level (prototype pollution defense).
- String cap: 256 chars on any value (`_STRING_CAP`).
- UTF-8 only; BOM stripped; non-UTF-8 → `non_utf8` reason.

## 3. Sigchain shape — `.claude/tier-policy.json.sigchain`

Append-only JSONL. One entry per policy change. Each entry is HMAC-
chained per ADR-055 pattern using a separate `tier-policy-key` (not
the audit-log key; principle of least blast-radius per F-SEC-P0-2).

```json
{
  "timestamp": "<ISO-8601 UTC>",
  "author": "<git user.email of Owner>",
  "sp_chain_id": "SP-NNN-<8-hex>",
  "action": "promote" | "demote" | "baseline" | "rotate",
  "agent_slug": "<one of CANONICAL_5>",
  "from_tier": "<MODEL_ID>",
  "to_tier": "<MODEL_ID>",
  "evidence_hmac": "<64-hex; tournament report anchor>",
  "prior_hash": "<64-hex; prior entry's hmac or genesis zeros>",
  "chain_length": <int, monotonic>,
  "prior_commit_sha": "<40-hex git HEAD at signing>",
  "hmac": "<64-hex HMAC-SHA256 of entry sans hmac field>"
}
```

### 3.1 C-P0-5 anti-truncation + anti-rollback

- `chain_length` monotonic counter — `verify` walks and rejects any
  non-increasing transition.
- `prior_commit_sha` — `verify` walks `git log` to confirm the
  referenced commit is ancestor of current HEAD (rollback attack:
  restoring an older (policy.json, sigchain) pair would reference a
  commit NOT in the current HEAD's ancestry).
- `sigchain_tip_length` in policy.json artifact, covered by the
  artifact's own `hmac_anchor` → truncating the sigchain breaks the
  anchor (the artifact signals "chain has N entries" but file has M,
  verify flags).

### 3.2 Statistical-power footer (NON-NORMATIVE)

Recommendations require:
- `n >= 30` per (role × task-type) cell
- `gap_pp >= 25` percentage points vs current tier's win-rate

At n=30 with p near 0.5, SE ≈ 0.091 → minimum detectable effect ≈
25pp at 80% power. A lower gap threshold (e.g., 15pp) is statistically
undersized at n=30 and produces false positives from sampling noise.

## 4. Reserved fields / extensions

Future schema versions (2.x+) MAY add:
- `cooldown_override: {role: <sp_chain_id>}` — Owner-signed cooldown
  bypass for model family releases.
- `governance_diff_hash` — structural invariant tracking.

`schema_version` MUST be bumped + migration recipe added to
`loader._migrate_schema` before any additive change ships.

## 5. Validation error taxonomy

Loader maps ValueErrors to stable reason tags (consumers key on
these):

| Reason | Trigger |
|--------|---------|
| `file_not_found` | Artifact absent → bootstrap short-circuit |
| `read_error` | OSError reading file |
| `oversized` | > 64 KiB |
| `non_utf8` | UTF-8 decode failure |
| `malformed_json` | json.JSONDecodeError |
| `prototype_pollution` | `__proto__` / `constructor` / `prototype` key |
| `nesting_exceeded` | > 8 levels of nesting |
| `root_not_object` | Top-level not a JSON object |
| `schema_version_missing` | `schema_version` key absent |
| `schema_version_unknown` | Known-current + unknown older |
| `schema_missing_keys` | One of `_REQUIRED_TOP_LEVEL` absent |
| `schema_extra_keys` | Unknown top-level key present |
| `string_too_long` | Any string > 256 chars |
| `invalid_model_id` | Tier not in `VALID_MODEL_IDS` |
| `hmac_anchor_malformed` | Not 64 lowercase hex chars |
| `assignments_slug_mismatch` | Assignments set != CANONICAL_5 |
| `schema_violation` | Catch-all |

## 6. Consumer contract (`tier_policy.loader.load_policy`)

Loader returns `LoadResult(status, policy_record, reason, baseline)`:

- `status="ok"` + `policy_record≠None` on full-valid.
- `status="migrated"` + `policy_record≠None` on forward-migration.
- `status="bootstrap"` + `policy_record=None` on file absent.
- `status="fallback"` + `policy_record=None` on any validation failure;
  `reason` carries the stable tag; `baseline` always carries the
  pre-computed ADR-052 static baseline for zero-I/O fallback
  (F-PERF-P1-2).

Dispatcher ALWAYS uses `baseline` on non-ok status.

## 7. Baseline artifact (shipped in `templates/`)

The framework ships a pre-signed genesis pair (per F-SEC-P0-8 / Q8
closure) in `templates/.claude/tier-policy.json` +
`templates/.claude/tier-policy.json.sigchain`. `install.sh --with-
tier-policy` copies both; adopter owns all post-first-derive state.

Baseline artifact content:

```json
{
  "schema_version": "1.0",
  "generated_at": "2026-04-19T00:00:00Z",
  "baseline_from": "ADR-052",
  "assignments": {
    "code-reviewer":         {"tier": "claude-opus-4-8",          "locked_by": "VETO_FLOOR", "evidence": null},
    "security-engineer":     {"tier": "claude-opus-4-8",          "locked_by": "VETO_FLOOR", "evidence": null},
    "qa-architect":          {"tier": "claude-sonnet-4-6",        "locked_by": null,         "evidence": null},
    "performance-engineer":  {"tier": "claude-sonnet-4-6",        "locked_by": null,         "evidence": null},
    "devops":                {"tier": "claude-haiku-4-5-20251001","locked_by": null,         "evidence": null}
  },
  "hmac_anchor": "<framework-signed on release>",
  "sigchain_tip_length": 1,
  "last_change_by_role": {}
}
```

Sigchain baseline genesis entry (framework-signed):

```json
{
  "timestamp": "2026-04-19T00:00:00Z",
  "author": "framework-genesis",
  "sp_chain_id": "SP-000-00000000",
  "action": "baseline",
  "agent_slug": "*",
  "from_tier": "*",
  "to_tier": "*",
  "evidence_hmac": "0000000000000000000000000000000000000000000000000000000000000000",
  "prior_hash": "0000000000000000000000000000000000000000000000000000000000000000",
  "chain_length": 1,
  "prior_commit_sha": "<release-tag-HEAD-sha>",
  "hmac": "<computed-at-release-build>"
}
```

## 8. Related

- **ADR-052** — static baseline this schema learns atop.
- **ADR-055** — HMAC chain pattern (policy artifact + sigchain).
- **ADR-063** — tournament report schema (input to learned policy).
- **ADR-064** — decision record for this artifact's semantics.
- **PLAN-043** — implementation plan.
