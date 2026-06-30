---
id: ADR-131
title: C5 dev-tools capability class — first C-class authorizing ADR per ADR-126 §Part 7
status: ACCEPTED
proposed_at: 2026-05-14
accepted_at: 2026-05-14
proposed_by: CEO (Session 120 PLAN-093 Wave B pre-execute gate; iter-3 ACCEPT thread 019e25fb on gpt-5.5)
related_plans: [PLAN-093]
related_adrs: [ADR-002, ADR-064, ADR-115, ADR-124, ADR-125, ADR-126]
supersedes: []
refines: [ADR-126]
amends: []
authorization: PLAN-093 architect sentinel `.claude/plans/PLAN-093/architect/round-1/approved.md` + `.asc` (Owner GPG 0000000000000000000000000000000000000000)
tags: [capability-class, c5-dev-tools, sidecar, hypothesis, property-based-testing, ADR-126-part-7-first-c-class]
---

# ADR-131 — C5 dev-tools capability class (first C-class authorizing ADR per ADR-126 §Part 7)

## Status

ACCEPTED — Session 120 2026-05-14 — Codex R2 iter-3 ACCEPT on `model: gpt-5.5` thread `019e25fb-e4f9-7533-9a59-e9db7b06f933` (3-iter convergence: iter-1 NEEDS-FIXES 2 P0 + 4 P1 + 4 P2 → iter-2 NEEDS-FIXES 0 P0 + 2 P1 + 2 P2 → iter-3 ACCEPT clean). Owner GPG 0000000000000000000000000000000000000000 via PLAN-093 architect/round-1 sentinel.

Full editorial body source: `.claude/plans/PLAN-093/ADR-131-draft.md` (~590 LoC). This canonical file condenses the editorial draft to ~280 LoC while preserving all doctrinal content; field-by-field equivalence verified at promotion ceremony.

## Date

2026-05-14

## Deciders

CEO (Owner) + Codex R2 cross-LLM verdict (gpt-5.5, thread `019e25fb`)

## Tags

capability-class / c5-dev-tools / sidecar / hypothesis / property-based-testing / ADR-126-part-7-first-c-class

## Refines

- ADR-126 (Governed sidecar capability model — refines §Part 3 generic C5 row + §Part 4 generic manifest schema + §Part 5 generic boundary test contract by specializing for the C5 dev-tools class)

## Related

- ADR-002 (Stdlib-only invariant for core — preserved; C5 sidecar lives outside core import surface)
- ADR-064 `dynamic-tier-policy-learned-dispatch` — contains cost-envelope rules cross-referenced; N/A for C5 dev-tools per `cost_envelope.enforcement="disabled"`
- ADR-115 §exception #1 (P0 ship-before-perf precedent — analogue authority)
- ADR-124 §Part 2 (post-audit-SOTA-execution-mode mechanical scope test — PLAN-093 satisfies via R-035 + R-036)
- ADR-125 §Tier A criteria (read-only / no token spend / single env kill-switch / byte-identical reversible)
- CLAUDE.md §6 — ADR-131 reserved per S117 PLAN-103 doctrine cleanup (ADR-126 §Part 7 reservation table)

## Context

ADR-126 (Session 117) introduced governed sidecar capability model with 5 initial classes. ADR-131 is the **first C-class authorizing ADR to materialize** (ahead of ADR-128/129 because PLAN-093 reached Wave B pre-execute gate first). PLAN-093 Wave B (`R-036 property-based testing`) requires `hypothesis` + `jsonschema` (non-stdlib). Per ADR-002 + ADR-126 §Part 2, sidecar isolation is the admissible path. This ADR establishes the C5 class contract authorizing `hypothesis` AND any future C5 sidecar (`mutmut`, `atheris`, etc.) under same governance.

## Decision

### Scope inclusions — admissible under C5

C5 admits sidecars whose primary purpose is **development-time testing/analysis infrastructure**:

- **Property-based testing**: `hypothesis`, `hypothesis-jsonschema`
- **Mutation testing**: `mutmut`, `cosmic-ray`
- **Fuzzing**: `atheris`, `python-afl`
- **Coverage analysis** (PyPI dev dependency NOT stdlib): `coverage[toml]` extras, `pytest-cov` plugins
- **Property generation helpers**: `faker`, `factory-boy`

All C5 admissions share three invariants:

1. Imported ONLY by `tests/`, `.claude/sidecars/c5-dev-tools/*/`, and CI-allowlisted workflow invokers
2. NEVER imported by production code paths (`.claude/hooks/`, `.claude/scripts/`, `SPEC/`, `.claude/policies/`, `.github/workflows/` except explicit invoker allowlist)
3. Dev-extras install path via `pyproject.toml` `[project.optional-dependencies] dev = [...]` (NOT base `dependencies`)

### Scope exclusions — NOT admissible under C5

- Cryptography libraries (X.509, JOSE) → **C1** (ADR-129)
- Vector embeddings / similarity search → **C2** (ADR-128)
- Local model inference (ollama, llama-cpp, mlx) → **C3** (ADR-130 RESERVED)
- Headless browser automation (playwright, selenium) → **C4** (ADR-134 RESERVED)
- HTTP clients / API wrappers used in production code → NOT a sidecar class; production code stays stdlib-only or uses blessed adapter
- Linters/formatters (`ruff`, `black`, `mypy`) → NOT C5; ship via `pre-commit` or developer-machine install

### C5-specific manifest schema delta vs ADR-126 §Part 4

ADR-126 §Part 4 specifies the generic 5-block manifest schema. C5 sidecars use the **canonical schema unchanged**. Only C5-specific *values*:

- `sidecar.capability_class`: `"C5"`
- `sidecar.default_tier`: `"A"`
- `governance.kill_switch_env`: `"CEO_SIDECAR_<NAME>_ENABLED"` (uppercase kebab-to-underscore of `sidecar.name`)
- `governance.default_state`: `"on"` (Tier A; `CEO_SIDECAR_<NAME>_ENABLED=0` disables; unset means default state "on")
- `governance.activation_predicate`: `"always-true"`
- `governance.explicit_opt_in_required`: `false`
- `governance.authorizing_adr`: `"ADR-131"`
- `governance.cost_envelope.enforcement`: `"disabled"` (zero per-invocation token cost; no LLM-FinOps enforcement)
- `install.hw_class_check`: `"none"`

### Tier-A justification (per ADR-125 + ADR-126 §Part 3)

All four ADR-125 §Tier A criteria hold for C5:

1. **Read-only**: dev-tools sidecars exercise test infrastructure; no production state writes (no audit-log mutation, no `_KNOWN_ACTIONS` rebase, no `.claude/state/*` mutation). Mutation testing mutates **test subjects** in isolated workspaces — not committed code.
2. **No token spend**: local Python execution; zero LLM API calls. `cost_envelope.per_invocation_tokens` is `0` structurally.
3. **Single env kill-switch — narrowly scoped**: `CEO_SIDECAR_<NAME>_ENABLED=0` disables sidecar **functional/property test execution only**. Boundary enforcement (`check-sidecar-manifest.py --strict` + `boundary_test.py` import/workflow scan per ADR-126 §Part 5/6) **ALWAYS RUNS** in CI regardless of kill-switch state. ADR-126 fail-closed invariant preserved.
4. **Reversal byte-identical via git revert**: removing a C5 sidecar requires removing **all seven surfaces atomically** — (a) sidecar dir, (b) `pyproject.toml` `[dev]` pin lines, (c) workflow boundary check step + grep belt-and-braces, (d) workflow allowlist entry, (e) `check-sidecar-manifest.py` if no other sidecars remain (validator is class-generic for C1/C2/C3/C4/C5), (f) `check-stdlib-only.py` sidecar-aware extension (same scope), (g) sidecar-internal `tests/` files. Single `git revert <sidecar-introduction-commit-sha>` restores all seven surfaces atomically. Commit-atomic introduction + commit-atomic removal, NOT piecemeal `rm -rf` operations.

### Boundary test contract (specialization of ADR-126 §Part 5)

ADR-126 §Part 5 specifies the generic boundary_test.py contract (parse manifest → AST-scan `core_paths_blocked` → assert zero Import/ImportFrom of `import_roots` → workflow YAML scan with allowed-pattern allowlist). C5 adds two assertions:

- **C5.1**: property tests using `hypothesis` MUST live under sidecar-internal tests at `.claude/sidecars/c5-dev-tools/<name>/tests/`. Framework-internal test paths (`.claude/hooks/tests/`, `.claude/scripts/tests/`) remain stdlib-only and MUST NOT import `hypothesis` / `jsonschema` directly. Adopter install unaffected — sidecar-internal tests run only when dev-extras installed.

  **PLAN-093 §3 Wave B.6 amendment required BEFORE Wave B executes**: PLAN-093 lines 292-307 still reference 4 property test paths at `tests/property/test_*.py` (non-canonical). Before Wave B `reviewed → executing` flip, PLAN-093 §B.6 MUST be amended via plan-amendment sentinel to relocate paths to `.claude/sidecars/c5-dev-tools/hypothesis/tests/test_*.py`. Plan-amendment dependency, NOT ADR-131 acceptance gate — ADR-131 ACCEPTED lands first; PLAN-093 §B.6 amends second as PLAN-093 Wave B pre-execute ceremony.

- **C5.2**: `pyproject.toml` `[project.optional-dependencies] dev` declarations MUST pin EXACT version (no `>=`/`^`/`~=`) AND match `manifest.json` `dependencies.python` byte-for-byte. Prevents dependency drift between manifest and install path.

### CI invocation contract (specialization of ADR-126 §Part 6)

C5 CI workflow MUST invoke:

```yaml
- name: C5 dev-tools sidecar boundary check
  run: |
    python3 .claude/scripts/check-sidecar-manifest.py --strict
    python3 .claude/sidecars/c5-dev-tools/<name>/boundary_test.py
    # Belt-and-braces: non-Python path grep for sidecar imports
    if grep -rn "<import_root_1>\|<import_root_2>" SPEC/ .claude/policies/; then
      echo "FAIL: C5 dev-tools leaked to non-Python production path" && exit 1
    fi
```

Grep step intentionally redundant with boundary_test.py Part 5 §2 AST scan — defense-in-depth against ast.parse failure modes.

### Promotion path (C5 → not-C5)

If a future C5 sidecar needs to be imported from production code: (1) new ADR drafted, (2) Codex R2 3-iter ACCEPT, (3) migration plan to either reimplement in stdlib OR promote to different capability class with appropriate tier, (4) original C5 sidecar manifest deprecated. NOT in scope for ADR-131 — escape valve documented for future authors. PLAN-093 Wave B ships C5 hypothesis under canonical Tier-A semantics with no promotion in v1.x arc.

## Options considered

- **A (rejected)**: Inline `hypothesis` into core via stdlib-only workaround — substantial reinvention; no `hypothesis-jsonschema` analog; dev-velocity cost unjustified
- **B (CHOSEN)**: Class C5 sidecar — `hypothesis` ships with manifest + boundary; ADR-002 preserved; adopter install unaffected; ~5MB (estimated) dev-extras install; pattern reusable for future C5 sidecars
- **C (rejected)**: Vendor `hypothesis` directly into repo — MPL-2.0 license burden + maintenance + bloat (~10k LoC); `pyproject.toml` `[dev]` extras is canonical
- **D (rejected)**: Skip property-based testing entirely — leaves coverage SOTA gap; canonical roadmap lists R-036 as Tier-5 deliverable

## Acceptance trail (bijective to PLAN-093 §4 ACs)

- **A1 → PLAN-093 AC5**: this ADR ACCEPTED via Codex R2 3-iter ACCEPT BEFORE Wave B executes — **CLOSED 2026-05-14 iter-3**
- **A2 → PLAN-093 AC3**: full ADR-126 §Part 4 + §Part 5 boundary enforcement per C5 manifest schema + boundary_test + workflow scan spec
- **A3 → PLAN-093 AC13**: CI gate in `.github/workflows/coverage.yml` invokes BOTH `check-sidecar-manifest.py --strict` AND `boundary_test.py`
- **A4 → PLAN-093 AC4**: 4 property tests GREEN with `@settings(max_examples=200, database=None)` floor per C5 invariant #1
- **A5 → PLAN-093 AC15**: mutation kill-rate ≥80% on `audit_emit.py` newly-wired `emit_*` (enabled by future C5 admission of `mutmut`-class sidecars)
- **A6 → PLAN-093 AC17**: `pyproject.toml` CREATED at repo root with `[project.optional-dependencies] dev = ["hypothesis==X.Y.Z", "jsonschema==X.Y.Z"]` (Wave B.2 prerequisite per C5.2)
- **A7 → PLAN-093 AC18**: `TestEnvContext` wrapping on all `@given` property tests (env isolation per SKILL.md rule 5; C5 invariant #1)

**PLAN-093 deliverables (NOT this ADR's gates)**: `.claude/sidecars/c5-dev-tools/hypothesis/manifest.json`, `.claude/sidecars/c5-dev-tools/hypothesis/boundary_test.py`, `.claude/scripts/check-sidecar-manifest.py` — these ship as part of PLAN-093 Wave B execution.

## Anti-churn compliance

This ADR materializes one of ADR-126 §Part 7 reserved slots (C5 = ADR-131). The reservation is explicit in ADR-126 §Part 7 table (lines 373-379); this ADR consumes the slot without expanding the slot count. No new ADR-N created beyond reserved ADR-131. ADR-115 §exception #1 invariant preserved — not a security/perf regression. ADR-002 stdlib-only preserved via boundary enforcement (AST + YAML scan + grep).

## Cross-ADR refinement specifics

### ADR-126 §Part 3 C5 row specialization

- **Original** (ADR-126 lines 158-166): "C5 | dev-tools | PLAN-093 | property-based testing, fuzzing, mutation testing | A (dev-only; never adopter runtime)"
- **Specialized-by-ADR-131**: scope inclusions list (5 admissible domains) + 5 explicit exclusions; manifest schema delta documented (no schema change vs §Part 4; canonical values only); boundary test C5.1 + C5.2 assertions added; promotion path C5 → not-C5 documented
- **Compatibility**: ADR-126 §Part 3 row preserved unchanged; specialization lives in ADR-131 as C-class authoritative contract

### ADR-126 §Part 7 reservation table consumption

- **Original** (ADR-126 §Part 7 table at lines 373-379): C5 dev-tools | ADR-131 (proposed PLAN-093) | PLAN-093
- **Consumed-by-ADR-131**: ADR-131 = C5 authorizing ADR. Row realizes the ADR-131 slot. ADR-128/129 remain "proposed PLAN-097/099" pending; ADR-130/134 remain "RESERVED first sidecar arrival"
- **Compatibility**: ADR-126 §Part 7 table needs no edit on ADR-131 ACCEPT — table row already names ADR-131 as C5 authorizing ADR

## Operator-facing changes

End-users see:

1. **No adopter runtime change** — sidecar lives under `.claude/sidecars/c5-dev-tools/<name>/`, import-walled from production paths; adopter `pip install ceo-orchestration` does NOT install `hypothesis`
2. **Framework CI installs sidecars via `pip install -e ".[dev]"`** — developer machines + framework's own CI workflow only; never adopter CI
3. **Kill-switch via env var**: `CEO_SIDECAR_HYPOTHESIS_ENABLED=0` disables sidecar; boundary_test still runs (validates manifest structure); sidecar tests skipped
4. **New sidecar dirs visible** at `.claude/sidecars/c5-dev-tools/<name>/` per future C5 admissions

## Observability + telemetry

C5 boundary enforcement is **CI-only** (not runtime-observable in operator terminal). CI workflow logs: `check-sidecar-manifest.py --strict` exit code + per-manifest validation; `boundary_test.py` exit code + per-sidecar isolation; belt-and-braces grep result. No audit_emit events fire (C5 is dev-time only).

## Anti-pattern callout

This ADR deliberately rejects four anti-patterns:

1. **"Just install hypothesis in core"** — violates ADR-002 + adopter install burden. Sidecar isolation mandatory.
2. **"Vendor hypothesis into repo"** — license burden + maintenance + bloat. PyPI install via dev-extras is canonical.
3. **"C5 admits anything dev-related"** — scope-creep risk. C5 has explicit 5-domain inclusion list + 5-domain exclusion list. Linters/formatters NOT C5 — ship via `pre-commit` or developer-machine install.
4. **"Skip boundary_test for first sidecar"** — every C5 sidecar MUST ship `boundary_test.py` AND framework MUST run `check-sidecar-manifest.py --strict`. No grandfathering; first C-class ADR sets discipline for subsequent C-classes.

## Consequences

### Positive

- Property-based testing admissible in framework CI without violating ADR-002 stdlib-only invariant
- First C-class ADR sets §template structure for ADR-128/129/130/134
- Adopter runtime unaffected — sidecar isolation mechanically enforced
- Future C5 sidecars (mutmut, atheris) inherit contract without new authorizing ADRs (only manifest + boundary test per ADR-126)
- Belt-and-braces enforcement (AST + YAML + grep) catches import leaks from multiple angles

### Negative

- Framework dev/CI environments must `pip install -e ".[dev]"` to access C5 sidecars
- New disk surface under `.claude/sidecars/c5-dev-tools/<name>/` (~5MB per sidecar — estimated; will be measured post-install)
- CI workflow gains `boundary_test.py` invocation step (~1-3s estimated; not measured) to `coverage.yml` runtime

### Neutral

- ADR-002 stdlib-only core invariant — preserved unchanged
- ADR-115 maintenance-mode + ADR-124 post-audit-SOTA-execution-mode — preserved unchanged
- ADR-125 Tier A criteria — C5 maps cleanly per §Tier-A justification
- ADR-064 cost-envelope — N/A for C5 (no token spend); cited for completeness
