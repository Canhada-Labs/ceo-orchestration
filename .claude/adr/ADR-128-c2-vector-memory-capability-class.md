---
id: ADR-128
title: C2 vector-memory capability class authorizing ADR
status: ACCEPTED
accepted_at: 2026-05-17
date: 2026-05-17
proposed_at: 2026-05-17
proposed_by: CEO (PLAN-097 Wave 0 — S131 execution, post-PLAN-096 v1.29.0 ship)
related_plans: [PLAN-041, PLAN-062, PLAN-097]
related_adrs: [ADR-002, ADR-062, ADR-062-AMEND-1, ADR-064, ADR-125, ADR-126, ADR-131]
authorizing_for_capability_class: C2
refines: [ADR-126]
amends: []
blast_radius: moderate
authorization: PLAN-097 sentinel `.claude/plans/PLAN-097/approved.md` + `.asc` (Owner GPG 0000000000000000000000000000000000000000) — TO BE COLLECTED AT CEREMONY
---

# ADR-128 — C2 vector-memory capability class authorizing ADR

## Status

ACCEPTED. (Drafted PROPOSED Session 131 (2026-05-17) under PLAN-097
Wave 0 per PLAN-097 §3 Wave 0 + §5 ADRs-proposed + ADR-126 §Part 7
table; promoted PROPOSED → ACCEPTED at the Owner ceremony after the
Codex R2 3-iter ACCEPT cycle. Frontmatter `status:` is the source of
truth — PLAN-113 W2 reconciled this body marker to match.)

This is the FIRST sidecar plan authoring a C-class authorizing ADR
under PLAN-097 (post ADR-131 C5 already ACCEPTED for PLAN-093 Wave B).

## Date

2026-05-17

## Context

ADR-126 §Part 3 enumerates 5 initial capability classes; C2
(vector-memory) is the home for RAG sidecars, calibration sample
storage, and any future vector-similarity work. PLAN-097 ships the
first concrete C2 sidecar — `lightrag-mvp` — wrapping the existing
PLAN-041 LightRAG sidecar in the §Part 4 manifest schema +
§Part 5 boundary test contract.

ADR-126 §Part 7 table assigns ADR-128 as the authorizing ADR for C2.
This ADR institutionalizes that assignment with class-specific
constraints.

## Decision drivers

- **Default tier B per ADR-125**: RAG ROUTING is conditional
  default-ON when predicate (`repo_profile == LARGE AND
  sidecar_installed AND sidecar_running`) holds. ADR-126 §Part 3
  table column 4 records C2 default-tier as B. ADR-062-AMEND-1
  refines the predicate per LARGE-profile semantics. Class-wide
  default is `conditional` per ADR-126 §Part 4 `governance.default_state`.
- **Install remains Tier C**: sidecar bytes (chromadb +
  sentence-transformers + lightrag + transitive ~ 90 MiB models +
  500 MiB-1 GiB disk @ 500k LoC + 1-2 GiB RAM peak) cross the
  Tier-C cost-quality threshold per ADR-115 §exception #3 +
  ADR-064 LLM-FinOps. Install requires Owner interactive consent
  in `install.sh` per PLAN-097 Wave C.2.
- **stdlib-only core preserved**: per ADR-126 §Part 1, no
  `chromadb` / `sentence_transformers` / `lightrag` imports in
  `.claude/hooks/` / `.claude/scripts/` / `SPEC/` /
  `.claude/policies/` / `.github/workflows/`. Boundary enforced
  by `boundary_test.py` (AC8) + `check-sidecar-manifest.py` (AC9)
  + workflow scan (B.5).
- **Network access NONE at runtime**: sidecar reads local repo
  (already permitted via ADR-062 §Architecture) + writes own
  state-dir under `~/.ceo-orchestration/rag/`. NO outbound HTTP
  at query time. (Model download is one-time at install per
  PLAN-097 AC1 + AC15 cost-envelope.)
- **Audit mediation via brokered IPC**: sidecar emits via existing
  ADR-062 §Architecture MCP bridge — the bridge writes audit
  events to the canonical chain (HMAC-protected per ADR-055-AMEND-1);
  sidecar does NOT write the audit log directly. This preserves
  the kernel-protected audit chain invariant per ADR-055.
- **Failure semantics fail-degraded**: per ADR-062 §Invariants-preserved
  bullet 3 (fail-open) — sidecar unavailable returns None to the
  routing layer, which falls through to CAG retrieval. Framework
  never blocks on sidecar state. This ADR institutionalizes the
  fail-degraded contract.

## Decision

The C2 vector-memory capability class is governed by the following
mandatory contract for any sidecar declaring `capability_class: C2`
in its `manifest.json`:

### §1. Permitted operations

- **Read-only access to repo files** (already permitted to all
  sidecars via ADR-002 §Architecture — sidecar's `_index_core.py`
  walks `.gitignore`-respected repo and extracts symbol-level
  embeddings).
- **Write-own-state-dir** at `~/.ceo-orchestration/rag/<project-id>/`
  with mode `0700` parent + `0600` files (per ADR-062 §Storage layout
  §Authentication).
- **No outbound network** at runtime (post-install). Model download
  is one-time at `install.sh` execution, governed by AC15 cost-envelope
  check (ADR-064) + AC13 fail-mode 2 (no-net).
- **MCP-tool exposure via local Unix socket** at
  `~/.ceo-orchestration/rag/sidecar.sock` with mode `0600` (per
  ADR-062 §Auth). No TCP exposure unless explicit Windows/WSL config
  override (loopback-only, `SO_EXCLUSIVEADDRUSE` on Windows).

### §2. Forbidden operations

- **Direct audit-log writes**: sidecar MUST emit via brokered IPC
  to framework core; framework core writes the HMAC-protected chain.
  Sidecar process MUST NOT acquire write permissions on
  `~/.claude/projects/*/audit-log.jsonl`. Mechanically enforced
  via UID-distinct sidecar process (when feasible) + file-permission
  audit at CI gate (AC8 boundary test scans for
  `audit-log.jsonl` file-handle acquisition under sidecar dir).
- **Network egress at query time**: any HTTP/socket/DNS call from
  the running sidecar (post-install) is a contract violation.
  Mitigation: PLAN-097 Wave A.3 smoke test exercises a network-
  isolated Docker run (`--network=none`) to prove no egress
  dependency at query time.
- **Imports of `chromadb` / `sentence_transformers` / `lightrag`
  in core paths**: per ADR-126 §Part 1 + §Part 5 boundary test.
  AC8 enforces fail-CLOSED in CI.
- **Auto-start of daemon by framework core**: per ADR-062 §Sidecar
  lifecycle §Auto-start — explicitly NOT. ADR-062-AMEND-1
  preserves this invariant for the LARGE-profile auto-wire path
  (framework routes queries to an Owner-instantiated sidecar; it
  does NOT spawn the daemon process).

### §3. Manifest schema requirements (C2-specific)

Per ADR-126 §Part 4 base schema PLUS the following C2-specific
constraints:

- `sidecar.capability_class` MUST equal `"C2"`.
- `sidecar.default_tier` MUST equal `"B"` (conditional). Tier-A or
  Tier-C C2 sidecars are NOT permitted under this ADR; future
  amendment ADR-128-AMEND-1 may relax this.
- `isolation.import_roots` MUST include each top-level Python
  package the sidecar owns. For `lightrag-mvp`: `["chromadb",
  "sentence_transformers", "lightrag"]`. Validator (`check-sidecar-manifest.py`)
  asserts non-empty.
- `isolation.core_paths_blocked` MUST include the standard 5-tuple
  per ADR-126 §Part 4 (`.claude/hooks/`, `.claude/scripts/`,
  `SPEC/`, `.claude/policies/`, `.github/workflows/`).
- `governance.kill_switch_env` MUST equal
  `"CEO_SIDECAR_C2_VECTOR_MEMORY_ENABLED"` (the canonical class
  kill-switch — applies to ALL C2 sidecars uniformly).
- `governance.default_state` MUST equal `"conditional"`.
- `governance.activation_predicate` MUST reference a deterministic
  expression. For `lightrag-mvp`: `"repo_profile=LARGE AND
  sidecar_installed AND sidecar_running"`. The predicate is
  evaluated at routing decision time by `.claude/hooks/_lib/rag_router.py`;
  it MUST NOT trigger network I/O, MUST NOT spawn processes, and
  MUST short-circuit to false if any sub-clause evaluation raises.
- `governance.cost_envelope` is required when the sidecar performs
  install-time model download (per AC15). For `lightrag-mvp`:
  documented at `enforcement: adapter` with per-query token estimate
  declared in manifest `install.model_pin_sha256` cross-ref.
  Runtime-only C2 sidecars (no install-time spend) MAY set
  `cost_envelope: null` per ADR-126 §Part 4 `default_tier` semantics
  — but install-time spend ALWAYS requires populated envelope.
- `install.hw_class_check` MUST equal `"disk_2gb"` minimum for C2
  sidecars shipping vector indices.

**C2-specific install-block extensions** (per ADR-126 §Part 4 the
base `install` block declares `script` + `hw_class_check`; the
following fields EXTEND that base with C2-specific keys; validator
`check-sidecar-manifest.py` enforces them only when
`capability_class == "C2"`):

- `install.min_python` MUST equal `"3.10"` minimum (per ADR-062
  §Architecture sidecar venv requirement; framework core remains
  Python 3.9+).
- `install.model_pin_sha256` MUST be populated at install time
  with the SHA-256 of the downloaded embedding model. Pre-install
  the field is the literal string `"<hex-populated-at-install>"`.
- `install.offline_cache_path` (optional) MAY be populated with the
  filesystem path adopters use to pre-stage embedding model weights
  when behind a corporate proxy (per PLAN-097 §6 R-corporate-proxy
  mitigation). Format: `"~/.ceo-rag/models/"` or equivalent shell
  expansion. When absent, install-sidecar.sh fetches from HuggingFace
  directly — corporate-proxy adopters MUST populate this field before
  running the installer.

**C2-specific governance clarifications** (per ADR-126 §Part 4
`governance.explicit_opt_in_required` SHOULD-false for Tier-B —
made explicit here to prevent drift):

- `governance.explicit_opt_in_required` MUST equal `false` for C2
  (Tier-B routing). Owner consent for **install** is collected by
  `scripts/install.sh` interactive prompt (Tier-C) per
  ADR-062-AMEND-1; ROUTING activation (Tier-B) is governed by the
  activation_predicate alone.

**Cost-envelope shape for C2** (refines the §3 mention above):

- `governance.cost_envelope` MUST be a populated object — never
  literal JSON `null`. For runtime-only paths (no install-time
  spend) acceptable shape is `{per_invocation_tokens: 0,
  daily_burn_cap: 0, enforcement: "disabled"}`. Validator
  `_validate_cost_envelope_conditional` rejects `enforcement:
  disabled` ONLY when install-time download is present
  (`model_pin_sha256` field populated). The shipped lightrag-mvp
  manifest uses `enforcement: adapter` since model download occurs
  at install per AC15.

**§Workflow-scan additional invariant** (refines §4 below):

- `isolation.core_paths_blocked` MUST include `.github/workflows/`
  so that ADR-126 §Part 5 step 2b workflow scan triggers. The
  shipped lightrag-mvp manifest satisfies this at the standard
  5-tuple element (`.github/workflows/`).

### §4. Boundary test contract (C2-specific)

Per ADR-126 §Part 5 generic contract PLUS:

- AST scan MUST flag `chromadb.client`, `chromadb.config`,
  `sentence_transformers.SentenceTransformer`, `lightrag.LightRAG`,
  and any dotted submodule (prefix match per ADR-126 §Part 5).
- Workflow scan (per ADR-126 §Part 5 step 2b triad) MUST permit
  ONLY the canonical boundary-test invocation pattern
  `^python3? \.claude/sidecars/c2-vector-memory/lightrag-mvp/boundary_test\.py($| )`.
  Any other `python3 .claude/sidecars/c2-vector-memory/...`
  invocation in `.github/workflows/*.yml` is a violation regardless
  of whether the invoker workflow is in
  `core_paths_allowlisted_workflow_invokers`.
- `python -c "import chromadb"` / `python -c "import sentence_transformers"`
  / `python -c "import lightrag"` are BANNED in every workflow
  regardless of allowlist match (per ADR-126 §Part 5 step 2b(b)).

### §5. Failure semantics

- **Sidecar process crash mid-query** → routing layer times out
  per `CEO_RAG_QUERY_TIMEOUT_MS` (default 2s, ADR-062 §Kill-switches)
  → returns None → routing layer emits `rag_query_routed` with
  `result: timeout` → caller falls through to CAG retrieval per
  ADR-005 fail-open invariant.
- **Sidecar socket missing** at routing decision time → predicate
  evaluates false → routing skipped → `rag_auto_wire_skipped_sidecar_down`
  emit → CAG fallback.
- **Sidecar manifest violation** detected by `check-sidecar-manifest.py`
  in CI → fail-CLOSED merge block + `sidecar_manifest_violation`
  audit emit per ADR-126 §Part 6.
- **Boundary test violation** detected by `boundary_test.py` in CI
  → fail-CLOSED merge block + structured error per ADR-126 §Part 5
  step 7.

### §6. Telemetry contract

C2 sidecars MUST emit (via brokered IPC to framework core, which
writes the HMAC-protected chain):

- `rag_query_routed` per routed query — Sec MF-3 caller fields:
  `query_class` (semantic / timeline / get_observations), `result`
  (one of: `dispatched` — emitted by the routing layer when the
  predicate evaluates true and the query is handed off to the
  sidecar; `hit` / `miss` / `timeout` / `error` — emitted by the
  sidecar query handler post-dispatch reporting query outcome),
  `latency_ms_p50` (bucketed, optional). NO query text. NO result
  text. NO file paths. The routing-layer emit always sets
  `result="dispatched"`; downstream hit/miss/timeout/error emits
  come from the sidecar query handler in a separate code path.
- `rag_profile_recommended` once per session at routing-decision
  time — caller fields: `profile` (SMALL/MEDIUM/LARGE), `decision`
  (auto-wire / skip / kill-switched).
- `rag_auto_wire_skipped_sidecar_down` when LARGE predicate is
  true but sidecar socket missing/unresponsive — caller fields:
  `reason` (socket-missing / health-probe-failed / kill-switched).
- `rag_false_large_demoted` when AC10 7d-sustained >1% false-LARGE
  threshold fires — caller fields: `false_large_rate_x100` (integer
  basis-points), `window_days` (7).
- `rag_hit_rate_degraded` when AC11 7d-sustained <60% hit-rate
  threshold fires — caller fields: `hit_rate_x100`, `window_days`.

Field allowlist enforced by Sec MF-3 caller-field whitelist on each
emit_* function in `.claude/hooks/_lib/audit_emit.py`.

### §7. SBOM / supply-chain

Per ADR-062 §Architecture supply-chain rationale: every dependency
in `.claude/sidecars/c2-vector-memory/<name>/requirements.lock` MUST
be SHA-256 pinned via `pip-compile --generate-hashes`. The model
download (embedding weights) MUST be SHA-256 pinned in the manifest
`install.model_pin_sha256` field. PLAN-097 Wave A.2 closes this gate
by populating real hashes (currently PLACEHOLDER per
`.claude/rag/requirements.lock` §header instructions).

## Compliance checklist

| Item | Verification |
|---|---|
| `.claude/sidecars/c2-vector-memory/lightrag-mvp/manifest.json` present | `test -f .claude/sidecars/c2-vector-memory/lightrag-mvp/manifest.json` |
| Manifest `capability_class == "C2"` | `jq -r .sidecar.capability_class < <manifest>` |
| Manifest `default_tier == "B"` | `jq -r .sidecar.default_tier < <manifest>` |
| Manifest `governance.kill_switch_env` matches canonical | grep `CEO_SIDECAR_C2_VECTOR_MEMORY_ENABLED` |
| boundary_test.py at canonical path | `test -f .claude/sidecars/c2-vector-memory/lightrag-mvp/boundary_test.py` |
| boundary_test.py exits 0 on clean tree | `python3 .claude/sidecars/c2-vector-memory/lightrag-mvp/boundary_test.py; echo $?` |
| `check-sidecar-manifest.py` validates ADR-128 manifest | `python3 .claude/scripts/check-sidecar-manifest.py --strict` |
| All 5 audit actions registered + emit_* defined | `grep -cE 'rag_profile_recommended\|rag_auto_wire_skipped_sidecar_down\|rag_query_routed\|rag_false_large_demoted\|rag_hit_rate_degraded' .claude/hooks/_lib/audit_emit.py` returns ≥10 (5 in `_KNOWN_ACTIONS` + 5 `emit_*` function definitions) |
| ADR-062-AMEND-1 ACCEPTED in same ceremony | `.claude/adr/ADR-062-AMEND-1-*.md` status: ACCEPTED |
| `requirements.lock` has SHA-256 hashes (no PLACEHOLDER) | `grep -c "^\s*[a-z].*==.*\s*\\\\$" .claude/sidecars/c2-vector-memory/lightrag-mvp/requirements.lock` ≥ 3 |

## Consequences

**Positive (+):**

- C2 capability class becomes the canonical home for vector-memory
  sidecars (RAG today; calibration vector storage in PLAN-101 future).
- Manifest schema mechanically enforced by `check-sidecar-manifest.py`
  prevents drift across future C2 sidecars.
- Boundary test contract prevents `chromadb` / `sentence_transformers`
  / `lightrag` from leaking into core paths over time.
- Failure-degraded semantics inherit from ADR-005 + ADR-062 —
  framework never blocks on C2 sidecar state.
- Tier B (conditional default-ON for routing) + Tier C (Owner
  consent for install) split per ADR-125 + ADR-062-AMEND-1 keeps
  installability discrete from runtime activation.

**Negative (-):**

- Adds a fourth (post C5 ADR-131, C1 reserved ADR-129, C3 reserved
  ADR-130) capability-class authorizing ADR to the ledger. Per
  ADR-126 §Part 7 this is the planned expansion path; no governance
  surprise.
- Per-query brokered-IPC audit emit adds ~50µs vs direct audit-log
  write. Acceptable given AC2 sidecar-internal perf scope (per
  PLAN-097 §AC2 R1 P1-4 clarification: NOT subject to PLAN-094
  framework-wide spawn-hook budget).
- Sidecar binary footprint (~90 MiB model + ~500 MiB-1 GiB disk +
  1-2 GiB RAM peak) crosses cost-envelope threshold; AC15 gates
  this at install time. Adopters declining sidecar install retain
  CAG fallback unaffected.

**Neutral (~):**

- ADR-062 (RAG sidecar opt-in) remains in force for SMALL/MEDIUM
  profiles; only the §Opt-in default clause is amended by
  ADR-062-AMEND-1 for LARGE profile.
- ADR-064 (LLM-FinOps) gates install-time cost via AC15 — already
  in scope, no expansion.
- ADR-115 (post-SOTA maintenance) §exception #3 (TTV ≤5min) honored:
  SMALL/MEDIUM see zero new install steps; LARGE see interactive
  prompt with declinability.

## Related decisions

- **ADR-002** — stdlib-only invariant for core. Refined by ADR-126
  §Part 1. This ADR enforces the invariant for C2 sidecar boundary.
- **ADR-062** — RAG sidecar opt-in. Amended by ADR-062-AMEND-1
  for LARGE-profile auto-wire. This ADR institutionalizes the
  C2 class hosting the RAG sidecar.
- **ADR-062-AMEND-1** — PLAN-097 Wave 0 sibling amendment. Defines
  the conditional default-ON predicate that this ADR's
  `governance.activation_predicate` field references.
- **ADR-064** — LLM-FinOps cost-envelope. Gates install-time model
  download spend via AC15.
- **ADR-125** — risk-tiered defaulting. C2 default tier B (routing)
  + Tier C (install) split.
- **ADR-126** — governed sidecar capability model. §Part 7 table
  assigns ADR-128 as C2 authorizing ADR.
- **ADR-131** — C5 dev-tools authorizing ADR (already ACCEPTED
  S120 for PLAN-093). Precedent for C-class authorizing ADR
  structure.

## Codex MCP gate trail

Codex R2 3-iter ACCEPT trail (PLAN-097 promotion ceremony, S131):

- This ADR R2 iter-1: ACCEPT-WITH-FIXES at PLAN-097 Wave 0.3 execution (S131) — 4 findings folded inline pre-ship: C2 install-block extensions (`min_python`, `model_pin_sha256`) declared as ADR-126 §Part 4 extensions, cost_envelope populated-object-never-null, `.github/workflows/` core_paths_blocked invariant, §6 telemetry result enum (routing-layer `dispatched` + sidecar-handler `hit/miss/timeout/error`).
- This ADR R2 iter-2: ACCEPT-WITH-FIXES — 2 P2 findings folded into draft: `install.offline_cache_path` (manifest line 52) added as third C2 install extension; Compliance row "5 audit actions registered" expanded to full 5-action `grep -cE` returning ≥10.
- This ADR R2 iter-3 (final): **ACCEPT** — P2 folds verified clean against manifest + audit_emit.py; status flip PROPOSED → ACCEPTED authorized.

## Authorization

PLAN-097 sentinel `.claude/plans/PLAN-097/approved.md` + detached
`.asc` signature (Owner GPG
0000000000000000000000000000000000000000) collected at PLAN-097
Owner ceremony (v1.30.0 ship).
