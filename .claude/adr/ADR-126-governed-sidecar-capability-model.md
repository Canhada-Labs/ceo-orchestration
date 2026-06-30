---
id: ADR-126
title: Governed sidecar capability model (option D) — refines ADR-002 stdlib-only invariant
status: ACCEPTED
proposed_at: 2026-05-13
accepted_at: 2026-05-13
proposed_by: CEO (Session 117 FASE 0 doctrine cleanup; Codex thread 019e21fe option-D locked S115-cont)
related_plans: [PLAN-093, PLAN-097, PLAN-099, PLAN-101, PLAN-103]
related_adrs: [ADR-002, ADR-051, ADR-064, ADR-115, ADR-116, ADR-124, ADR-125]
supersedes: []
refines: [ADR-002]
authorization: PLAN-103 sentinel `.claude/plans/PLAN-103/architect/round-1/approved.md` + `.asc` (Owner GPG 0000000000000000000000000000000000000000)
---

# ADR-126 — Governed sidecar capability model (option D)

## Status

ACCEPTED — Session 117 FASE 0 doctrine cleanup 2026-05-13 — Codex R2 iter-4 ACCEPT thread `019e2254-b8af-7bb3-a2a3-d45fba537544` (extended from 3-iter pattern by 1 small-fix iter) — Owner GPG 0000000000000000000000000000000000000000 via PLAN-103 sentinel `.asc`.

## Date

2026-05-13

## Context

ADR-002 (Sprint 2 A.1-A.5) declared **stdlib-only** as the invariant
for the framework's hook code:

> Stdlib only. Every external dep is a cross-platform support matrix
> expansion. stdlib gives us `json`, `re`, `hashlib`, `fcntl`,
> `unittest`, `multiprocessing`, `pathlib` — everything we need.

This invariant has held for **6+ months across 90+ plans** (PLAN-001
through PLAN-091). The FASE 4 evolution-roadmap from PLAN-084
introduces four capabilities whose minimal viable implementation
exceeds stdlib:

| Plan | Capability | Why stdlib insufficient |
|---|---|---|
| PLAN-097 | RAG installability | chroma vector store + sentence-transformers embeddings |
| PLAN-099 | Federation stdlib SSL MVP | stdlib `ssl` covers MVP; advanced X.509 + key rotation needs `cryptography` sidecar |
| PLAN-101 | AEK Calibration C2-C4 | calibration sample storage feasible in stdlib but vector similarity benefits from sidecar |
| PLAN-093 | Tier-5 hypothesis dev-extras | property-based testing requires `hypothesis` library |

Three solution shapes considered S115-cont (Codex thread
`019e21fe-f2d2-76b2-895d-03c7a7e5633c`):

- **Option A**: Hold stdlib-only forever. Plans drop or stay degraded.
- **Option B**: Relax ADR-002 — allow non-stdlib in core hooks.
- **Option D (CHOSEN)**: Governed sidecars — core stays stdlib;
  capability-class sidecars opt-in, isolated, manifest-governed.

Codex locked Option D 2026-05-13 (thread `019e21fe`, iter-3 ACCEPT).
This ADR institutionalizes that decision.

## Decision drivers

- **Preserve ADR-002 invariant for core.** Hooks are governance-
  critical; stdlib-only eliminates supply chain blast radius for
  the kernel. Any non-stdlib in core is rejected.
- **Permit roadmap capabilities to ship.** PLAN-097/099/101/093
  cannot be implemented in stdlib alone; doctrine must permit them
  somewhere.
- **Isolation boundary mechanical, not aspirational.** Sidecars
  must be import-walled from core; core code never imports sidecar
  code; sidecar manifest declares capabilities + tests enforce
  boundary.
- **Capability classes, not individual sidecars.** Avoid
  per-sidecar ADR explosion. A small fixed set of capability
  classes (5 initial) carries doctrine; individual sidecars within
  a class share governance.
- **Opt-in by adopter class.** Tier-A (read-only, observable)
  sidecars can default-ON conditional on detection (ADR-125).
  Tier-C (model-exec, spendy) sidecars default-OFF.
- **Manifest-governed**: each sidecar ships a JSON manifest at
  `.claude/sidecars/<capability-class>/<name>/manifest.json` with
  declared capabilities + isolation contract + governance hooks.

## Options considered

### Option A — Stay stdlib-only forever (no sidecars)

Hold ADR-002 invariant rigid. PLAN-097/099/101/093 deferred
indefinitely or rescoped to stdlib-only degenerate forms.

**Rejected** — discards 4 evolution-roadmap items. Codex P2 REVISIT
verdict (S115-cont) explicitly noted "stdlib-core + sidecars is the
path; insisting stdlib-only blocks roadmap." PLAN-084 evolution
investment is wasted under this option.

### Option B — Relax ADR-002 (allow non-stdlib in core hooks)

Add `requirements.txt` to `.claude/hooks/`. Allow hook code to
`import chromadb` etc.

**Rejected** —
- Breaks zero-install-cost promise (ADR-002 §decision drivers #1).
- Expands supply chain attack surface to every adopter.
- Removes the cross-platform support matrix simplification.
- Kernel hardening (ADR-116 KERNEL HARD-DENY) was justified
  partially by "stdlib-only kernel is auditable". This option
  invalidates that justification.

### Option C — Per-sidecar individual ADR + ad-hoc isolation

Each sidecar gets its own ADR, ad-hoc isolation pattern, per-plan
governance. Roughly the pre-this-ADR status quo.

**Rejected** — produces ADR explosion (4 sidecars × 3 supporting
ADRs each = ~12 ADRs). Inconsistent isolation patterns. Codex
explicitly preferred capability-class consolidation.

### Option D — Governed sidecars + 5 capability classes (CHOSEN)

Stdlib core sacred + 5 capability classes carry doctrine + each
sidecar within a class shares governance + manifest schema enforced
mechanically.

**CHOSEN.**

## Decision

**Option D.** Eight-part rule:

### Part 1 — Core stays stdlib-only

`.claude/hooks/` + `.claude/hooks/_lib/` + `.claude/scripts/` +
`SPEC/` + `.claude/policies/` + `.github/workflows/*.yml` may import
ONLY:

- Python stdlib (per ADR-002).
- Other modules within `.claude/hooks/_lib/` (relative absolute).

Imports of non-stdlib packages from core are BLOCKED via canonical-
guard extension. (Enforcement script: `.claude/scripts/check-stdlib-only.py`
proposed as Part 6 below.)

ADR-002 §decision and §choice remain in force for core. ADR-116
KERNEL HARD-DENY paths remain stdlib-only.

### Part 2 — Capability-class sidecars permitted

Non-stdlib code permitted ONLY under:

```
.claude/sidecars/<capability-class>/<sidecar-name>/
├── manifest.json          # capability declaration + isolation contract (stdlib `json`-enforceable; NOT YAML)
├── README.md              # adopter install instructions
├── install.sh             # standalone installer (idempotent)
├── boundary_test.py       # enforces "core never imports this"
├── sidecar_code/          # the actual non-stdlib code lives here
│   ├── __init__.py
│   └── <impl>.py
└── tests/                 # sidecar-internal tests
```

### Part 3 — Five initial capability classes

| Class | Name | First plan | Domain | Default tier (ADR-125) |
|---|---|---|---|---|
| C1 | crypto | PLAN-099 | X.509, key rotation, advanced TLS | A (read-only peer view) for MVP; C for any signing |
| C2 | vector-memory | PLAN-097 | embeddings, vector store, similarity search | B (conditional on HW class) |
| C3 | model-exec | RESERVED | local model inference (ollama, llama.cpp, mlx) | C (token spend) |
| C4 | browser | RESERVED (authorizing ADR-134) | headless browser automation | C (network spend, sandbox needed) |
| C5 | dev-tools | PLAN-093 | property-based testing, fuzzing, mutation testing | A (dev-only; never adopter runtime) |

**ADR number RESERVATIONS**: C3 = ADR-130, C4 = ADR-134. These
slots are RESERVED in the ADR ledger pending first sidecar arrival
in their respective class. Sidecar manifests declaring
`capability_class: C3` or `C4` reference these reserved ADR
numbers; manifests are INVALID (fail-CLOSED in CI per §Part 6
validator) until the corresponding authorizing ADR is drafted +
Codex R2 ACCEPTED + Owner GPG.

### Part 4 — Manifest schema (manifest.json, JSON not YAML)

**Format decision**: `manifest.json` chosen over YAML because
Python stdlib ships `json` but NOT a YAML parser. The validator
script (§Part 6) must remain stdlib-only to fit ADR-002 invariant
for core. JSON5 / comments are NOT permitted; strict RFC 8259 only.

Each sidecar `manifest.json`:

```json
{
  "sidecar": {
    "name": "<kebab-case>",
    "capability_class": "C1|C2|C3|C4|C5",
    "version": "<semver>",
    "default_tier": "A|B|C"
  },
  "isolation": {
    "core_paths_blocked": [
      ".claude/hooks/",
      ".claude/scripts/",
      "SPEC/",
      ".claude/policies/",
      ".github/workflows/"
    ],
    "core_paths_allowlisted_workflow_invokers": [
      ".github/workflows/validate.yml"
    ],
    "import_roots": [
      "<unique-top-level-python-package-name-this-sidecar-owns>"
    ],
    "allowed_workflow_invocation_patterns": [
      "^python3? \\.claude/sidecars/[^/]+/[^/]+/boundary_test\\.py($| )"
    ],
    "boundary_test": "boundary_test.py"
  },
  "dependencies": {
    "python": [
      "<pkg>==<pinned-version>"
    ],
    "system": []
  },
  "governance": {
    "kill_switch_env": "CEO_SIDECAR_<NAME>_ENABLED",
    "default_state": "on|off|conditional",
    "activation_predicate": "<expression evaluated at init: hw-class | calibration-gate | always-true>",
    "enable_value": "1",
    "disable_value": "0",
    "explicit_opt_in_required": true,
    "authorizing_adr": "ADR-NNN",
    "cost_envelope": {
      "per_invocation_tokens": 0,
      "daily_burn_cap": 0,
      "enforcement": "adapter|adapter+settings|disabled"
    }
  },
  "install": {
    "script": "install.sh",
    "hw_class_check": "none|gpu_optional|gpu_required|disk_2gb"
  }
}
```

**Field semantics** (§Part 4 details):

- `isolation.import_roots`: unique top-level Python package
  name(s) this sidecar owns. Used by `boundary_test.py` for AST
  Import/ImportFrom checks. Example: C2 vector-memory sidecar's
  `import_roots` = `["chromadb", "sentence_transformers"]`.
- `isolation.core_paths_blocked`: paths under which NO `.py` file
  may import any entry in `import_roots`. Includes
  `.github/workflows/` to prevent workflow scripts from pulling
  sidecar imports.
- `isolation.core_paths_allowlisted_workflow_invokers`: narrow
  allowlist for CI files that legitimately invoke
  `boundary_test.py` (the test harness MAY reference the sidecar
  path; the workflow itself MUST NOT import sidecar code).
- `isolation.allowed_workflow_invocation_patterns`: list of regex
  strings declaring the EXACT subprocess invocation patterns
  workflows MAY use to call `boundary_test.py`. Required by §Part 5
  workflow scan (step 2b condition (a)). Example canonical pattern:
  `"^python3? \\.claude/sidecars/[^/]+/[^/]+/boundary_test\\.py($| )"`
  — matches `python3 .claude/sidecars/c2-vector-memory/chroma-mvp/boundary_test.py`
  but rejects any extra arguments importing sidecar modules.
  Validator (§Part 6 `check-sidecar-manifest.py`) MUST enforce
  presence of this field for every sidecar manifest.
- `governance.default_state`:
  - `"on"`: capability activates by default (Tier A — kill switch
    `enable_value` is default).
  - `"off"`: capability disabled by default (Tier C — kill
    switch unset OR `disable_value` is default).
  - `"conditional"`: capability evaluates `activation_predicate`
    at init (Tier B — e.g., `hw-class=gpu_optional`).
- `governance.explicit_opt_in_required`: MANDATORY `true` for
  Tier C (`default_tier == "C"`). Tier A MAY set `false` (default
  ON). Tier B SHOULD set `false` (conditional logic governs).
  Validator (§Part 6) enforces this.
- `governance.cost_envelope`: Tier C ONLY — populated with
  per-invocation token estimate + daily burn cap + enforcement
  mechanism (per ADR-064 LLM-FinOps).

### Part 5 — Boundary test contract (mechanically enforceable)

Each sidecar `boundary_test.py` MUST:

1. Parse the sidecar's `manifest.json` via stdlib `json` to load
   `isolation.import_roots`, `isolation.core_paths_blocked`,
   `isolation.core_paths_allowlisted_workflow_invokers`, and
   `isolation.allowed_workflow_invocation_patterns` (regex strings
   declaring the exact subprocess invocation patterns workflows MAY
   use to call `boundary_test.py`, e.g. `^python3? \\.claude/sidecars/[^/]+/[^/]+/boundary_test\\.py($| )`).
2. Scan every `.py` file under each path in `core_paths_blocked`
   via stdlib `ast.parse` + `ast.walk`.
2b. **YAML / workflow scan** (mandatory for `.github/workflows/`):
    parse every `.yml`/`.yaml` under `.github/workflows/` via stdlib
    line-level `re` (no YAML parser in stdlib). For each line:
    (a) If the line contains a `run:` shell step body OR a
        `python3?` invocation: assert one of —
        - the line matches a pattern in
          `isolation.allowed_workflow_invocation_patterns`
          (e.g., the canonical boundary-test invocation), OR
        - the line contains NO substring matching any
          `isolation.import_roots` entry (exact OR dotted prefix),
          OR
        - the workflow file path is in
          `isolation.core_paths_allowlisted_workflow_invokers`
          AND the line is a `pip install` / `uv pip install` /
          dependency-bootstrap line (NOT a `python -c "import X"`
          execution).
    (b) `python -c "import <import_root>"` and equivalents are
        BANNED in every workflow regardless of allowlist.
3. For each `ast.Import` node, assert no `alias.name` matches any
   entry in `import_roots` (exact match OR dotted-prefix match —
   `chromadb.client` matches `chromadb`).
4. For each `ast.ImportFrom` node, assert `node.module` does NOT
   match any entry in `import_roots` (exact OR dotted-prefix).
5. Additionally scan for banned dynamic import patterns via AST +
   string-literal inspection:
   - `importlib.import_module("<import_root>")`
   - `__import__("<import_root>")`
   - `exec("import <import_root>")` / `eval("...")` containing
     import_root string literal
   - Bare string literals matching `^(from|import) <import_root>($|[. ])`
     OUTSIDE comment / docstring tokens (use `tokenize` module
     to distinguish code strings from comments).
6. Run as part of `.github/workflows/validate.yml` CI gate.
7. Fail-CLOSED — boundary violation blocks merge with exit
   code ≠ 0 + structured error output naming the offending file +
   line number + matched pattern.
8. Test fails-OPEN ONLY if `manifest.json` is missing or malformed
   (treated as install incomplete; surfaces in `validate.yml` as
   `sidecar_manifest_missing_or_malformed` lint error → blocks
   merge anyway, but distinct error class from boundary violation).

### Part 6 — Stdlib-only enforcement for core

New script `.claude/scripts/check-stdlib-only.py`:

1. AST-parses every `.py` file under
   `.claude/hooks/` + `.claude/scripts/` + `SPEC/python/` (if any).
2. Asserts every `import X` resolves to:
   - Python stdlib (per `sys.stdlib_module_names` Python 3.10+, or
     hardcoded list for 3.9 fallback), OR
   - Relative path within `.claude/hooks/_lib/` or `.claude/scripts/_lib/`.
3. Fail-CLOSED in CI; emit `stdlib_violation` audit event.

Additionally a companion script
`.claude/scripts/check-sidecar-manifest.py`:

1. Parses every `.claude/sidecars/*/*/manifest.json` via stdlib
   `json`.
2. Validates required fields per §Part 4 schema (sidecar /
   isolation / governance / install).
3. Enforces `default_tier`-consistent `explicit_opt_in_required`:
   Tier C MUST be `true`; Tier A MAY be `false`; Tier B SHOULD be
   `false` (warned if `true` without justification comment in
   plan §Default).
4. Asserts `governance.authorizing_adr` references an ADR file
   with status ACCEPTED (not PROPOSED, RESERVED, or non-existent).
   RESERVED-class sidecars (per §Part 8) emit
   `sidecar_manifest_violation` audit event and fail-CLOSED.
5. Asserts `cost_envelope` is populated for `default_tier == "C"`
   (per ADR-064 LLM-FinOps gate).
6. Fail-CLOSED in CI; emit `sidecar_manifest_violation` audit
   event on any rule failure.

Both scripts (`check-stdlib-only.py` + `check-sidecar-manifest.py`)
ship together in this ADR's enforcement commit (PLAN-103 Wave 3)
OR within first sidecar plan (PLAN-093/097), whichever lands first.
PLAN-104 reserved for these enforcement scripts if neither sidecar
plan lands within 30 days of this ADR's ACCEPTED date.

### Part 7 — Per-capability-class authorizing ADR

Each capability class has its own authorizing ADR governing that
class's sidecars:

| Class | Authorizing ADR | First plan |
|---|---|---|
| C1 crypto | ADR-129 (proposed PLAN-099) | PLAN-099 |
| C2 vector-memory | ADR-128 (proposed PLAN-097) | PLAN-097 |
| C3 model-exec | ADR-130 (RESERVED first sidecar arrival) | TBD |
| C4 browser | ADR-134 (RESERVED first browser sidecar; concrete number assignable when drafted) | TBD |
| C5 dev-tools | ADR-131 (proposed PLAN-093) | PLAN-093 |

Class ADRs may add class-specific constraints (e.g., C3 model-exec
ADR-130 must enforce ADR-064 cost-envelope manifest).

### Part 8 — Sunset / class addition

- **Adding a new capability class** (C6+) requires its own
  doctrinal ADR + Codex R2 ACCEPT + Owner GPG. Not arbitrary.
- **Class with RESERVED authorizing ADR** (currently C3 ADR-130
  and C4 ADR-134): sidecar manifests declaring this class are
  INVALID until the concrete authorizing ADR is drafted + Codex
  R2 ACCEPTED + Owner GPG. The `check-sidecar-manifest.py`
  validator (§Part 6) fails-CLOSED on any manifest referencing a
  non-ACCEPTED `authorizing_adr`. Canonical-guard additionally
  blocks any merge containing a sidecar dir under a RESERVED
  class path until the class ADR exists.
- **Retiring a capability class** requires its authorizing ADR's
  SUPERSEDED-BY path + dependent sidecars rescoped or deprecated.
- **This ADR retires** when ADR-002 is itself superseded OR when
  capability-class count exceeds 10 (signal to revisit doctrine
  scalability).

## Consequences

**Positive (+):**

- Preserves ADR-002 invariant for core kernel/governance.
- Unblocks PLAN-093/097/099/101 evolution-roadmap items.
- Boundary tests prevent slippery-slope erosion ("just one more
  import in core").
- Capability-class consolidation prevents ADR explosion.
- Manifest schema gives mechanical auditability per sidecar.
- Tier-A/B/C alignment with ADR-125 routes sidecar defaults
  consistently.

**Negative (-):**

- Adds `.claude/sidecars/` tree (new top-level governance directory).
- Adds canonical-guard extension for stdlib-only enforcement.
- Adds per-sidecar `manifest.json` + `boundary_test.py` overhead.
- Adopter install complexity grows: optional sidecar installers
  must be discoverable.
- 5 capability classes is an opinionated taxonomy — may need C6+
  expansion sooner than expected (ADR amendment path).

**Neutral (~):**

- ADR-064 LLM-FinOps cost-envelope governs Tier-C sidecar token
  spend (already in scope).
- ADR-051 non-delegation governs architect-class operations (sidecar
  authoring is CEO work; sidecar invocation by sub-agents OK).
- ADR-115 §Detection-decay monitor extends to per-sidecar telemetry
  (each sidecar should emit `sidecar_invoked` audit event).

## Blast radius

**L3+** — affects core/sidecar boundary across the framework.
Touches:

- This ADR (new).
- `.claude/adr/ADR-002-hooks-package-layout.md` — append §Refined-by
  block linking to ADR-126.
- `.claude/sidecars/` — new top-level directory (created by first
  C1/C2/C5 plan; NOT in PLAN-103 scope).
- `.claude/scripts/check-stdlib-only.py` — new enforcement script
  (Part 6; deferred to first sidecar plan or PLAN-104).
- `.claude/scripts/check-sidecar-manifest.py` — new manifest
  validator script (Part 6; deferred to first sidecar plan or
  PLAN-104; ships paired with `check-stdlib-only.py`).
- `.github/workflows/validate.yml` — add `check-stdlib-only` +
  `check-sidecar-manifest.py` CI steps (deferred with Part 6;
  both ship paired and gate merges together).
- `.claude/scripts/canonical_guard.py` — add `.claude/sidecars/**`
  to canonical-path coverage (sentinel-required for sidecar adds;
  deferred to first sidecar plan).
- `templates/CLAUDE.md` — adopter-install template references
  optional sidecar surface (deferred).
- `INSTALL.md` — sidecar discovery section (deferred).

No `SPEC/` schema changes in this ADR; per-class ADRs may add
sidecar-specific schemas.

## Compliance checklist

| Item | Verification |
|---|---|
| ADR file present | `test -f .claude/adr/ADR-126-governed-sidecar-capability-model.md` |
| Codex R2 3-iter ACCEPT logged | thread ref in §Codex MCP gate trail |
| ADR-002 §Refined-by block present | `grep 'ADR-126' .claude/adr/ADR-002-*.md` |
| `.claude/sidecars/` directory permitted by canonical-guard | dry-run mkdir + sentinel-required path test |
| Manifest schema documented in this ADR §Part 4 | grep `manifest.json` |
| `check-sidecar-manifest.py` validator shipped (in PLAN-103 commit OR within 30d) | `test -f .claude/scripts/check-sidecar-manifest.py` OR PLAN-104 tracking |
| 5 capability classes enumerated | grep `C1\|C2\|C3\|C4\|C5` in §Part 3 |
| Per-class authorizing ADR mapping documented | §Part 7 table |
| `check-stdlib-only.py` shipped (in this ADR commit OR within 30d) | `test -f .claude/scripts/check-stdlib-only.py` OR PLAN-104 tracking |
| boundary_test.py contract documented | §Part 5 |
| Class addition / retirement governance documented | §Part 8 |

## Related decisions

- ADR-002 — Hooks package layout + stdlib-only invariant — **refined by** this ADR
- ADR-051 — Non-delegation (architect-class) — applies to sidecar authoring
- ADR-064 — LLM-FinOps cost-envelope — governs Tier-C sidecar spend
- ADR-115 — Post-SOTA maintenance mode + Detection-decay monitor
- ADR-116 — KERNEL HARD-DENY Tier-0 — kernel stays stdlib-only
- ADR-124 — Post-audit-SOTA-execution-mode — operational scope for sidecar rollout
- ADR-125 — Risk-tiered defaulting doctrine — sidecar default tier classification
- PLAN-084 evolution-roadmap.md — sidecar-requiring items source
- PLAN-097 (RAG) — first C2 vector-memory sidecar
- PLAN-099 (Federation) — first C1 crypto sidecar (stdlib MVP first; sidecar reserved)
- PLAN-093 (Tier-5 hypothesis) — first C5 dev-tools sidecar
- ADR-128 — C2 vector-memory authorizing ADR (proposed PLAN-097)
- ADR-129 — C1 crypto authorizing ADR (proposed PLAN-099)
- ADR-130 — C3 model-exec authorizing ADR (RESERVED; draftable at first model-exec sidecar arrival)
- ADR-131 — C5 dev-tools authorizing ADR (proposed PLAN-093)
- ADR-134 — C4 browser authorizing ADR (RESERVED; draftable at first browser sidecar arrival)

## Codex MCP gate trail

- Doctrine option-D selection: thread `019e21fe-f2d2-76b2-895d-03c7a7e5633c` (S115-cont) — ACCEPT iter-3.
- Cross-LLM revalidation P2 REVISIT (stdlib-core+sidecars): thread `019e215c-cff5-7ed3-a7f1-87e4b8f94439` (S115-cont).
- This ADR R2 iter-1 NEEDS-FIXES (5 findings: 3 P1 + 2 P2): thread `019e2254-b8af-7bb3-a2a3-d45fba537544` (Session 117 Wave 1) — all 5 folded inline 2026-05-13 (boundary test AST + workflows in core_paths_blocked + manifest.yaml→manifest.json + governance schema fields + C4 ADR-134 reservation).
- This ADR R2 iter-2 NEEDS-FIXES (4 findings: 1 P1 + 3 P2): thread continuation `019e2254-b8af-7bb3-a2a3-d45fba537544` — all 4 folded inline 2026-05-13 (workflow-boundary AST + 4 stale `manifest.yaml` refs + §Part 7 C4 ADR-XXX → ADR-134 + `check-sidecar-manifest.py` in §Blast radius/Compliance).
- This ADR R2 iter-3 NEEDS-FIXES (3 findings: 1 P1 + 2 P2): thread continuation `019e2254-b8af-7bb3-a2a3-d45fba537544` — all 3 folded inline 2026-05-13 (`allowed_workflow_invocation_patterns` field added to §Part 4 schema + §Field semantics + 1 stale "YAML manifest" + `validate.yml` blast-radius bullet expansion).
- This ADR R2 iter-4 final **ACCEPT**: thread continuation `019e2254-b8af-7bb3-a2a3-d45fba537544` — verdict 2026-05-13: "ACCEPT. Iter-1/2/3 boundary, manifest, reserved-class, and CI-enforcement gaps are now folded into enforceable doctrine without violating ADR-002 stdlib-core constraints."

## Authorization

PLAN-103 sentinel `.claude/plans/PLAN-103/architect/round-1/approved.md` +
detached `.asc` signature (Owner GPG 00000000).
