# stdlib Exceptions — opt-in third-party imports

**Status:** living document
**Last updated:** 2026-05-07 (PLAN-078 Wave 3 — release-dry-run.py)
**Related ADR:** [ADR-002 — Python hooks package layout](../.claude/adr/ADR-002-hooks-package-layout.md)

## Invariant

Per **ADR-002 §Decision drivers / "Stdlib only"**:

> Every external dep is a cross-platform support matrix expansion.
> stdlib gives us `json`, `re`, `hashlib`, `fcntl`, `unittest`,
> `multiprocessing`, `pathlib` — everything we need.

This invariant is **absolute for `.claude/hooks/**`** — runtime hooks
MUST NOT import any third-party package. Breaking the invariant breaks
first-run on minimal containers, airgapped installations, and the
`install.sh` zero-install contract.

## Relaxation clause (scripts only)

ADR-002's stdlib-only invariant is scoped to the hook runtime path
(`.claude/hooks/**`). **Offline utilities under `.claude/scripts/**`**
that are not invoked by `settings.json` and do not run in the hook
hot-path MAY opt into third-party packages **iff**:

1. The import is **lazy** (inside a function, not at module import).
2. A `try: import X; except ImportError` guard emits a clear install
   hint to stderr and exits with a non-zero code (typically `2`).
3. The runtime fallback is documented here.
4. CI paths-filter prevents the script from being required on every
   PR (benchmark / contract validators are advisory or path-gated).
5. The target project's `install.sh` does NOT require the dependency.

This relaxation is **explicit and enumerated** — adding a new
opt-in script requires updating this file in the same PR.

## Enumerated opt-in scripts

The table below lists every `.claude/scripts/*.py` that imports
something outside Python 3.9+ stdlib. As of 2026-05-07 there are
**exactly three**.

| Script | Opt-in package | Invocation site | Runtime if missing | Install command |
|--------|----------------|-----------------|--------------------|-----------------|
| `.claude/scripts/run-skill-benchmark.py` | `pyyaml` (lazy, line 122) + `anthropic` (lazy, line 896) | CI `benchmarks.yml` (paths-filtered to `.claude/skills/**`) or manual `python3 .claude/scripts/run-skill-benchmark.py <bench.yaml>` | `SystemExit(2)` with install hint on stderr | `python3 -m pip install pyyaml anthropic` |
| `.claude/scripts/validate-squad-contract.py` | `pyyaml` (top-level try/except, line 39) | CI `validate.yml` squad-gate step (only when `.claude/skills/domains/**` changed) or manual `python3 .claude/scripts/validate-squad-contract.py --squad <path>` | `SystemExit(2)` with install hint on stderr | `python3 -m pip install pyyaml` |
| `.claude/scripts/local/release-dry-run.py` | `pyyaml` (lazy via `_load_waivers`, top-level guard via `_ensure_pyyaml`) | Owner-machine local pre-tag validation: `python3 .claude/scripts/local/release-dry-run.py --target-version 1.x.y` | `SystemExit(2)` with install hint on stderr | `python3 -m pip install pyyaml` |

### `.claude/scripts/run-skill-benchmark.py`

- **Purpose:** async runner for skill benchmarks (e.g.
  `owasp-basics.yaml`). Executes scenarios against the Anthropic API
  at `temperature=0`, median-of-3, with pre-flight cost cap.
- **Why pyyaml:** benchmark YAML fixtures are declarative + already in
  the project; rewriting a minimal YAML parser for these files would
  invite silent parser drift. Opted into the upstream parser instead.
- **Why anthropic SDK:** the benchmark sends real API calls; stdlib
  `urllib` would force us to maintain our own retry / streaming
  plumbing. Lazy-imported after the cost gate passes so CI runs that
  hit `--skip-if-no-key` never need the SDK installed.
- **Fallback behaviour:** if either package is missing, the script
  prints a single-line install hint and exits `2` (usage/infra error).
  The hook runtime is unaffected; this script is never called from
  `settings.json`.

### `.claude/scripts/validate-squad-contract.py`

- **Purpose:** contract validator for squad bundles (per ADR-009 §
  Validation rules). Verifies `team-personas.md`, `pitfalls.yaml`
  (≥12), `task-chains.yaml` (≥2), and ≥3 skill dirs.
- **Why pyyaml:** squad contracts are user-authored YAML (`pitfalls.yaml`,
  `task-chains.yaml`); upstream parser matches user expectations
  (aliases, anchors, multiline). Writing a stricter subset parser would
  diverge from how authors read their own files.
- **Fallback behaviour:** prints `validate-squad-contract: PyYAML is
  required (python3 -m pip install pyyaml)` and exits `2`. This is a
  contract-validation gate, not a user-facing hook; absence only
  affects CI when squad files change.

## What is NOT allowed

- **Hooks (`.claude/hooks/**/*.py`)** — MUST stay stdlib-only.
  `check_agent_spawn.py`, `audit_log.py`, `check_bash_safety.py`,
  `check_plan_edit.py`, `check_read_injection.py`,
  `check_canonical_edit.py`, every file under `_lib/`, and every
  adapter under `_lib/adapters/` are stdlib-only. This is enforced by
  reviewer discipline (no CI regex yet — see DYN backlog for a
  future `check-stdlib-invariant.py`).
- **install.sh** — MUST NOT depend on any third-party package.
  Target-project installation must work on a vanilla Python 3.9+.
- **Transitive imports** — an opt-in script MAY NOT import a `_lib/`
  module that itself imports a third-party package. Runtime-optional
  imports must happen inside the script file, not leak through `_lib`.

## Adding a new exception

1. Open a plan item referencing this doc.
2. Add a row to the table above.
3. Ensure the import is lazy + guarded + emits a clear hint.
4. Verify `install.sh` is not touched.
5. Reference this doc in the plan's acceptance criteria so the review
   catches silent regressions.

## Auditing current state

```bash
# Every Python import of a non-stdlib package under .claude/
grep -rnE '^(import |from ) ?(yaml|anthropic|requests|httpx|pydantic|click|rich|typer)' .claude/ | grep -v __pycache__

# Expected output as of 2026-04-16 (4 lines, exactly):
#   .claude/scripts/run-skill-benchmark.py:122:        import yaml  # type: ignore
#   .claude/scripts/run-skill-benchmark.py:894:    # Lazy-import anthropic
#   .claude/scripts/run-skill-benchmark.py:896:        from anthropic import Anthropic  # type: ignore
#   .claude/scripts/validate-squad-contract.py:39:    import yaml  # type: ignore
```

If the audit returns anything under `.claude/hooks/**`, **that is a
bug** — open a P0 ticket immediately.

## References

- [ADR-002 — Python hooks package layout](../.claude/adr/ADR-002-hooks-package-layout.md) §Decision drivers (stdlib-only rationale)
- [ADR-002 §Option C rejection](../.claude/adr/ADR-002-hooks-package-layout.md) (why pip-install-e was turned down)
- PLAN-019 Phase 3 P2-001 (this exception doc was commissioned here)
