---
status: experimental
spec_version: 1.0.0-rc.1
created: 2026-04-17
plan: PLAN-014
phase: A.1
supersedes: none
---

# SPEC/v1/policy-dsl.schema.md — Policy-as-code DSL Contract

**Version:** 1.0.0-rc.1 (PLAN-014 Phase A.1, Sprint 14)
**Status:** experimental (per ADJ-003 until Sprint 15 adopter signal)
**Authoritative source:** `.claude/hooks/_lib/policy.py` + `.claude/policies/*.yaml` — this SPEC is the grep-able grammar + behavior inventory the engine is tested against.

## 0. Purpose

ADR-045 §Decision (post Phase A.2 lock) establishes WHY a policy-as-code engine exists. This document is the normative companion: YAML subset grammar, predicate semantics, closed-enum error model, identity + canonical-form contract, runtime lifecycle, and security boundary declarations.

**Scope:** 2 hooks migrate to this DSL in Sprint 14 (`check_bash_safety.py` + `check_plan_edit.py`). `check_canonical_edit.py` STAYS Python per ADJ-001 (sentinel-signature-chain encoding too load-bearing). Additional hooks may migrate in Sprint 15.5+ post adopter calibration per ADR-045 §Rollback reversal path.

**Non-scope:** runtime-dynamic rule injection (§4 explicit), external-network predicate evaluation (§9 explicit), non-YAML DSL surfaces (JSON / TOML rejected — see ADR-045 §Options for rationale).

Companion documents:
- `audit-log.schema.md` v2.6 — 3 events registered (`policy_evaluated`, `policy_denied`, `policy_error`)
- `adapters.schema.md` — hook adapter ABI (envelope types policies emit)
- ADR-045 — Policy-as-code engine decision record (full options + trade-off matrix + §Fail-mode + §Rollback)
- ADR-014 — hook-migration-batch-policy (cited in Phase A context)
- ADR-002 — hooks package layout (stdlib-only invariant enforced here)

---

## 1. Version + Status

| Field | Value |
|---|---|
| Schema version | `1.0.0-rc.1` |
| Schema status | `experimental` (frontmatter) |
| Spec lifetime | v1.x.y — additive only per §11 Versioning |
| Authoritative source | `.claude/hooks/_lib/policy.py` |
| Policy file naming | `.claude/policies/<slug>.policy.yaml` |
| Fixture naming | `.claude/policies/fixtures/<slug>.fixtures.jsonl` |
| Migration bundle entry point | `settings.json` `PreToolUse` / `PostToolUse` hook command |

SemVer-shaped. Within v1 every grammar addition is MINOR-bump additive only. Grammar removal or semantic change to an existing predicate is MAJOR bump (forbidden in v1 without new SPEC file).

---

## 2. Surface

The DSL is **load-time only**. A hook process boot:

1. Reads `$CEO_POLICY_FILE` env (or default `<hook-name>.policy.yaml`)
2. Parses via `_lib.policy.load(path)` returning a frozen `Policy` object
3. Evaluates `Policy.decide(event)` per Claude Code tool-call entry
4. Emits 0–1 `policy_evaluated` + 0–1 `policy_denied` + 0–1 `policy_error` audit events
5. Returns `{"decision": "allow" | "block", "reason"?: "<enum>", "message"?: "<human>"}`

Hook binary shim (`_python-hook.sh`) remains unchanged. The DSL is a replacement for the **body** of the Python hook, not its invocation contract (which lives in `adapters.schema.md`).

### Dual-path window

Every migrated hook retains its `.py` file executable + tested through v1.5.x (per ADJ-014). The `settings.json` entry points to a thin shim:

```
.claude/hooks/_python-hook.sh .claude/hooks/check_bash_safety.py
```

post-migration becomes:

```
.claude/hooks/_python-hook.sh .claude/hooks/policy_dispatch.py --policy bash-safety
```

Legacy `.py` remains importable for byte-identity testing (§6) + emergency rollback via `CEO_POLICY_ENGINE_DISABLE=1` (see §7 + ADR-045 §Rollback).

---

## 3. Grammar (YAML subset — normative)

The parser is **hand-rolled stdlib** (ADR-002 invariant; ADJ-004). **PyYAML is forbidden.** The accepted subset is a strict sub-language of YAML 1.2 with the following normative constraints:

### 3.1 Accepted constructs

- Block mappings (`key: value`)
- Block sequences (`- item`)
- Plain scalars (unquoted strings, integers, booleans `true`/`false`, `null`)
- Double-quoted strings with standard escapes (`\n`, `\t`, `\"`, `\\`, `\uXXXX`)
- Single-quoted strings with `''` escape
- Nested mappings + sequences up to depth 8
- UTF-8 encoding only (explicit `encoding: utf-8` on file read)

### 3.2 Rejected constructs (MUST fail with `alias_rejected` / `tag_rejected` / `parse_error`)

- `&anchor` / `*alias` — **DISABLED** at parse time (ADJ-004)
- `!!python/name:` / `!!python/object:` / any custom Python tag
- Multi-document streams (`---` separators between docs)
- **Multi-line** flow-style mappings (`{k: v,\n k2: v2}`) and multi-line flow sequences
- **Nested** flow-style (flow inside flow, e.g. `{k: {k2: v}}`) — only 1-level inline flow permitted
- Block scalar indicators `|` and `>` (ambiguous whitespace semantics)
- Directives (`%YAML`, `%TAG`)
- Binary data (`!!binary`)

**Rationale:** each rejection closes a known YAML security CVE class or ambiguity. Block scalars add a trailing-whitespace dialect; custom tags permit code execution in PyYAML; anchors permit billion-laughs DoS.

**Inline single-line flow-mapping EXCEPTION (v1.0.0-rc.1 clarification):** Single-line inline flow-mapping `{field: <path>, value: <scalar>}` and flow-sequence `[a, b, c]` values are ACCEPTED ONLY as predicate-argument sugar within a block-mapping rule (e.g. `eq: {field: tool, value: "Bash"}` per §3.5). This is load-bearing for §3.5 predicate syntax and Appendix A examples. Parser MUST reject: (a) any flow spanning multiple source lines; (b) flow nested inside flow (depth > 1 within a flow context); (c) flow at the top-level document position. This exception is narrowly scoped — predicate-body sugar only.

### 3.3 Hard limits (enforced before parse commits)

| Limit | Value | Enforcement point | Audit event on breach |
|---|---|---|---|
| File size (raw bytes) | 64 KiB | Pre-parse, on file read | `policy_error(size_limit)` |
| Nesting depth | 8 | Parse-time counter | `policy_error(depth_limit)` |
| Total post-expand document size | 1 MiB | Post-parse memory audit (stdlib `sys.getsizeof` walk) | `policy_error(size_limit)` |
| Total key count | 2000 | Parse-time counter | `policy_error(size_limit)` |
| Single scalar length | 16 KiB | Parse-time token bound | `policy_error(size_limit)` |
| CPU time for parse + compile | 500 ms | Wall-clock via `time.monotonic()` at entry/exit | `policy_error(timeout)` — breaker opens |

Exceeding ANY limit → fail-CLOSED for security-surface hooks (bash_safety, plan_edit); fail-open for pure-advisory hooks (none in Phase A). See §7 fail-mode matrix.

### 3.4 Document structure (top-level)

```yaml
# Normative top-level schema (abstract)
schema: "policy-dsl/v1"       # REQUIRED; closed-enum literal
id: <slug>                    # REQUIRED; matches filename base
description: <free text>      # REQUIRED; ≤200 chars; shown in audit
kind: allow_list | deny_list | mixed  # REQUIRED; closed enum
defaults:                     # REQUIRED
  decision: allow | block     # fail-safe default when no rule matches
  reason: <closed-enum-key>   # default reason for non-match
rules:                        # REQUIRED; list of rule-objects
  - id: <slug>                # REQUIRED; unique within file
    description: <free text>  # OPTIONAL; ≤200 chars
    decision: allow | block   # REQUIRED
    reason: <closed-enum-key> # REQUIRED if decision=block
    predicate:                # REQUIRED; single predicate root
      <predicate-form>
error_model:                  # REQUIRED
  reasons:                    # closed enum of allowable reason keys
    <key>: <human-message>
    ...
```

### 3.5 Predicate forms (closed set)

Exactly one of these shapes is allowed at every predicate root + sub-node:

| Form | Shape | Semantics |
|---|---|---|
| `all` | `all: [<pred>, <pred>, ...]` | Conjunction (short-circuit on first false) |
| `any` | `any: [<pred>, <pred>, ...]` | Disjunction (short-circuit on first true) |
| `not` | `not: <pred>` | Negation |
| `eq` | `eq: {field: <dotted-path>, value: <scalar>}` | Equality on event field |
| `neq` | `neq: {field: <dotted-path>, value: <scalar>}` | Inequality |
| `in` | `in: {field: <dotted-path>, values: [<scalar>, ...]}` | Set membership (values closed at load-time) |
| `not_in` | `not_in: {field: <dotted-path>, values: [...]}` | Negated membership |
| `regex` | `regex: {field: <dotted-path>, pattern: "<python-re>"}` | Python `re` dialect (pinned; ADJ-004) |
| `starts_with` | `starts_with: {field: <dotted-path>, prefix: "<str>"}` | Literal prefix match |
| `ends_with` | `ends_with: {field: <dotted-path>, suffix: "<str>"}` | Literal suffix match |
| `contains` | `contains: {field: <dotted-path>, substring: "<str>"}` | Literal substring match |
| `length_le` | `length_le: {field: <dotted-path>, value: <int>}` | String length ≤ N |
| `length_ge` | `length_ge: {field: <dotted-path>, value: <int>}` | String length ≥ N |
| `path_under` | `path_under: {field: <dotted-path>, root: "<prefix>"}` | Normalized path containment (prevents `..` escape via `os.path.realpath`) |

**`<dotted-path>`** refers to fields on the event envelope (adapter ABI). Examples: `tool`, `tool_input.command`, `tool_input.file_path`, `subagent_type`.

**No arithmetic predicates** (deliberate — prevents Turing completeness + bounded evaluation time).

### 3.6 Regex dialect

- Python `re` module (pinned — no RE2, no PCRE, no ECMA).
- Flags encoded inline via `(?iLmsux)` prefix (no separate `flags:` field).
- Pre-compiled at load-time with `re.compile(pattern)`; compile errors → `policy_error(parse_error)`.
- Pattern string length hard-cap 512 chars.
- No backreferences in the pattern quantifier (e.g. `\1+` rejected at compile-time).

### 3.7 Decision table

When `decide(event)` runs:

1. Iterate `rules` in declared order
2. For each rule, evaluate `predicate`; if true → return `{decision: rule.decision, reason: rule.reason?}`
3. If no rule matches → return `{decision: defaults.decision, reason: defaults.reason}`

**First-match-wins.** Deterministic. No rule-priority field (explicit ordering via YAML sequence preserves intent).

---

## 4. Runtime semantics

### 4.1 Load-time only

Policies are loaded **ONCE at hook-process start**. Claude Code harness spawns a fresh hook process per tool-call boundary; reload is implicit on next process boot. **Mid-session policy edits DO NOT take effect until the next tool-call** (ADJ-036).

This is a deliberate simplification: no file-watcher, no SIGHUP handler, no shared-memory cache. The hook-process lifecycle is short (<50 ms typical), and harness-driven re-boot IS the reload primitive.

### 4.2 Thread-safety

The `_lib.policy.Policy` object is immutable post-load. `decide(event)` is a pure function over the frozen AST + event dict. Per-rule `RLock` is provided by `_lib.policy.Policy._rule_locks` for future lazy-compile extensions (breaker ADR-040 §4 precedent); current v1 semantics are fully eager so locks are unused but API-stable.

### 4.3 Eager compile

- YAML parse → AST construction → regex compile → rule-form validation ALL happen inside `load(path)`.
- `decide()` never compiles, never parses, never reads files.
- Separation prevents per-event latency spikes + enables load-time validation of all predicates before any tool-call runs against the policy.

### 4.4 Determinism

- `decide(event)` is deterministic: same event dict + same policy file → same decision + same audit event payloads.
- Audit event `duration_ms` is NOT part of the decision fingerprint (timing info only).
- Regex matches use `re.search` (not `re.match`) to support middle-of-string patterns consistently.

---

## 5. Error model (closed enum)

All policy-engine errors emit `policy_error(error_kind=<key>, detail=<redacted>)` via `audit_emit.emit_policy_error`. Closed enum:

| `error_kind` | Trigger | Fail-mode (security surface) | Fail-mode (advisory surface) |
|---|---|---|---|
| `parse_error` | YAML syntax / grammar violation | fail-CLOSED (deny) | fail-open (allow + breadcrumb) |
| `predicate_missing` | Rule references `predicate` form not in §3.5 closed set | fail-CLOSED | fail-open |
| `import_failure` | `_lib.policy` import fails (corrupt install) | fail-CLOSED via shim fallback to `.py` | fail-open via shim fallback |
| `depth_limit` | Nesting > 8 | fail-CLOSED | fail-open |
| `size_limit` | Any §3.3 size bound exceeded | fail-CLOSED | fail-open |
| `alias_rejected` | YAML anchor/alias detected | fail-CLOSED | fail-open |
| `tag_rejected` | Custom/python YAML tag detected | fail-CLOSED | fail-open |
| `timeout` | Parse + compile > 500 ms (§3.3) | fail-CLOSED + breaker-opens for that policy-id | fail-open |
| `field_missing` | Event lacks `<dotted-path>` referenced in predicate | depends on rule — counted as predicate-false per §3.7 | same |
| `regex_compile_error` | Pattern rejected by Python `re.compile` at load-time | fail-CLOSED | fail-open |
| `schema_version_mismatch` | Top-level `schema:` != `policy-dsl/v1` | fail-CLOSED | fail-open |

**Decision reason enum** (emitted when `policy_denied` fires) is file-local — authored in `error_model.reasons` per policy and registered in `audit-log.schema.md` v2.6 via the `policy_denied.reason` field.

**Redaction:** `detail` field passes through `_lib.redact.redact_secrets` in `audit_emit.emit_policy_error` before write. Tokens, paths with credentials, and known provider-API patterns (`sk-ant-*`, `AIza*`, `sk-proj-*`) are masked.

---

## 6. Policy identity + drift guard

Per ADJ-005, policy identity is a **2-layer check**:

### 6.1 Canonical-form hash

Serialize the parsed `Policy` AST (post-load, before regex compile) with:

```python
json.dumps(policy.to_canonical_dict(), sort_keys=True,
           separators=(',', ':'), ensure_ascii=False).encode('utf-8')
```

SHA-256 digest is the **policy identity**. Semantically-equivalent rewrites (whitespace changes, comment relocation, key reordering) produce identical identity. Any semantic change produces a different identity.

Each policy file ships with a pinned identity in `.claude/policies/.drift-manifest.json`:

```json
{
  "policies": {
    "bash-safety": {
      "sha256": "abc123...",
      "updated": "2026-04-17",
      "pr": "#NNN",
      "reviewers": ["@Canhada-Labs", "@security-lead"]
    }
  }
}
```

### 6.2 Fixture-corpus semantic check

Every policy MUST have a sibling `<slug>.fixtures.jsonl` under `.claude/policies/fixtures/` enumerating:

```jsonl
{"input": {<event-dict>}, "expected_decision": "allow|block", "expected_reason": "<enum>"}
```

The drift check runs each fixture through the engine and asserts exact match on `expected_decision` + `expected_reason`. **Fixture mismatch fails with exit 1 regardless of canonical-hash stability** — a semantically-equivalent rewrite MAY change the hash but MUST preserve all fixture outcomes.

### 6.3 CI check

`.claude/scripts/check-policy-drift.py` (stub Phase 0.4 → full Phase A) runs:

1. For each policy file: compute canonical hash; compare to manifest pin
2. For each fixture: execute via engine; diff decision + reason
3. Exit 0 clean, 1 drift, 2 parse error

Wired into `validate.yml` (Phase A.7).

---

## 7. Fail-mode contract

Three categories of failure, each with a deterministic outcome:

### 7.1 Parse / compile failure (load-time)

- Hook process boots → `_lib.policy.load(path)` raises
- Dispatcher catches → emits `policy_error(error_kind=<key>)`
- **Security-surface hooks** (bash_safety, plan_edit): the dispatcher invokes the **original `.py` hook as fallback** during the dual-path window (v1.5.x). Decision is what the `.py` hook returns.
- **Post dual-path window** (v1.6.0+): fail-CLOSED returning `{"decision": "block", "reason": "policy_engine_unavailable"}`.

### 7.2 Engine import failure

- `_python-hook.sh` invokes `policy_dispatch.py`; dispatcher fails to import `_lib.policy`
- Shim detects via exit code + stderr grep, invokes legacy `check_bash_safety.py` / `check_plan_edit.py` directly
- Transparent to Claude Code harness

### 7.3 Predicate field missing (per-event)

- `decide(event)` encounters `field: tool_input.command` but event has no `tool_input.command`
- Rule predicate evaluates to **false** (not an error)
- No `policy_error` emitted; normal `policy_evaluated(decision=<defaults>)` path

### 7.4 Kill-switch escape hatch

`CEO_POLICY_ENGINE_DISABLE=1` env var → dispatcher short-circuits at entry + invokes legacy `.py` hook directly. Emits `policy_error(error_kind=disabled_by_env)` once per hook process for observability.

---

## 8. Revocation + deprecation

### 8.1 Policy revocation

A policy becomes ineffective by either:
- Removing its `settings.json` registration (harness no longer invokes the hook)
- Removing the YAML file (`settings.json` still references → `policy_error(parse_error)` → fail-mode §7.1)

Manifest pin MUST be removed in the same PR to keep drift check clean.

### 8.2 Rule deprecation

Rules accumulate. A rule is deprecated by:
1. Adding `status: deprecated` at rule level (optional field, no runtime effect)
2. Setting `decision: allow` + blank predicate (always-match) + `description: "DEPRECATED — remove by <date>"`
3. Removing in a follow-up PR

The `status` field is advisory metadata; it does not affect evaluation. Deprecation is a doc/PR hygiene pattern, not a runtime behavior.

### 8.3 Schema deprecation window

Per §11 Versioning, a grammar form (§3.5) is deprecated by:
1. Landing its replacement in v1.N.0 with backward-compat overlap
2. Marking the old form `status: deprecated` in this SPEC §3.5 table
3. Emitting `policy_error(error_kind=deprecated_form)` advisory-only for 2 MINOR releases
4. Removing in the NEXT MAJOR (v2.0.0)

Deprecation window: minimum 2 MINOR releases. No shortening without new SPEC file.

---

## 9. Security considerations

### 9.1 DSL is load-time only (§4.1 re-stated)

No runtime-dynamic rule injection. Policies are files under `.claude/policies/**` — CODEOWNERS-gated (Phase 0.5 ADJ-031). A PR is the only surface for policy change.

### 9.2 Thread-safety

Per §4.2, `Policy` is immutable post-load. No shared mutable state across `decide()` calls.

### 9.3 Attack surface enumeration

| Vector | Mitigation |
|---|---|
| YAML billion-laughs (alias bomb) | Aliases DISABLED at parse time (§3.2) |
| YAML custom-tag RCE | Custom tags rejected (§3.2); PyYAML not used (ADR-002) |
| Deep-nesting DoS | Depth cap 8 (§3.3) |
| Large-file DoS | Size caps (§3.3) |
| ReDoS via crafted pattern | Pre-compile at load-time + pattern-length cap 512 (§3.6); load-time CPU bound 500 ms (§3.3) |
| Path-traversal in `path_under` | `os.path.realpath` normalization before comparison (§3.5) |
| Credential leak in `detail` | `redact_secrets` on emit (§5) |
| Policy-file tamper | CODEOWNERS gate + drift-manifest SHA pin (§6) |
| Fixture drift | `check-policy-drift.py` CI enforcement (§6.3) |

### 9.4 Tier classification

Policy files are **Tier 2 governance surface** (same as hooks). Changes require CODEOWNERS review per §0.5 ADJ-031.

### 9.5 No external network

The evaluator NEVER makes network calls. `_lib.policy.decide()` is a pure function over event dict + compiled AST. Any future extension requiring network lookups MUST ship as a separate predicate kind with explicit ADR amendment.

---

## 10. Backward compatibility

Within v1 (v1.0.0-rc.1 through v1.x.y):

- **Grammar additions** are MINOR bump, additive only. New predicate forms (§3.5) land with new v1.N.0 tag.
- **Grammar removals** are MAJOR (forbidden in v1).
- **Semantic changes to existing predicates** are MAJOR (forbidden in v1).
- **Error-enum additions** are MINOR (new `error_kind` values MUST be documented in §5 + registered in `audit-log.schema.md` if event payload changes).
- **Default policy-dispatch behavior** is frozen: fail-CLOSED for security surfaces, fail-open for advisory (none Phase A).

Consumer contract: **unknown predicate form** → `policy_error(predicate_missing)` + fail-CLOSED. Upgrade path: pin `schema:` literal per-file; load-time compatibility check rejects `policy-dsl/v2` on a v1 engine.

---

## 11. Versioning + history

### Spec-level versioning

| Version | Released | Summary |
|---|---|---|
| 1.0.0-rc.1 | 2026-04-17 | Initial experimental release. 14 predicate forms, 11 error enums, 2 migrated hooks (bash_safety + plan_edit). Status: experimental pending Sprint 15 adopter signal. |

### Deprecation window

2 MINOR releases minimum for any grammar form (§8.3). No deprecation window for advisory fields (may drop on MINOR).

### Schema-version pinning

Every `.policy.yaml` MUST declare `schema: "policy-dsl/v1"` at top level. Missing → `policy_error(schema_version_mismatch)`. Future v2 files will declare `schema: "policy-dsl/v2"`; a v1 engine MUST reject them with the same error.

---

## 12. References

- ADR-045 — Policy-as-code engine (options + decision + fail-mode + rollback)
- ADR-002 — Hooks package layout (stdlib-only invariant)
- ADR-014 — Hook-migration-batch-policy (cited in Phase A context)
- ADR-040 §4 — RLock pattern for per-item compile concurrency
- PLAN-014 §Phase A + §Debate Round 1 (ADJ-001 scope reduction; ADJ-003 experimental marker; ADJ-004 stdlib parser + alias disable; ADJ-005 canonical hash + fixture corpus; ADJ-008 6-tuple byte-identity; ADJ-014 dual-path; ADJ-015 fail-mode matrix; ADJ-024 ≥5 options; ADJ-025 SPEC-first; ADJ-030 rollback ≤3; ADJ-036 runtime-semantics load-time only)
- `audit-log.schema.md` v2.6 — 3 registered events (`policy_evaluated`, `policy_denied`, `policy_error`)
- `adapters.schema.md` — hook adapter ABI

---

## Appendix A — Minimal example

```yaml
# .claude/policies/example-safety.policy.yaml
schema: "policy-dsl/v1"
id: example-safety
description: "Trivial deny on rm -rf / wildcard"
kind: deny_list
defaults:
  decision: allow
rules:
  - id: deny_rm_rf_slash
    description: "Block rm -rf / and variants"
    decision: block
    reason: dangerous_rm
    predicate:
      all:
        - eq: {field: tool, value: "Bash"}
        - regex:
            field: tool_input.command
            pattern: "(?i)\\brm\\s+-[a-z]*r[a-z]*f[a-z]*\\s+/(?:\\s|$)"
error_model:
  reasons:
    dangerous_rm: "Refusing to execute rm -rf on filesystem root"
```

Corresponding fixture:

```jsonl
{"input": {"tool": "Bash", "tool_input": {"command": "rm -rf /"}}, "expected_decision": "block", "expected_reason": "dangerous_rm"}
{"input": {"tool": "Bash", "tool_input": {"command": "rm -rf ./build"}}, "expected_decision": "allow", "expected_reason": null}
{"input": {"tool": "Read", "tool_input": {"file_path": "/etc/passwd"}}, "expected_decision": "allow", "expected_reason": null}
```

---

**End of SPEC/v1/policy-dsl.schema.md v1.0.0-rc.1 (experimental).**
