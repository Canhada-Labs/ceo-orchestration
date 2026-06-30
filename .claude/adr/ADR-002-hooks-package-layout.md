# ADR-002: Python hooks package layout + version shim

## Refined-by (PLAN-103 FASE 0, 2026-05-13)

**Stdlib-only invariant** declared in this ADR is **REFINED** (not
relaxed, not superseded) by
[ADR-126](ADR-126-governed-sidecar-capability-model.md) as of
2026-05-13. ADR-126 establishes the governed-sidecar capability
model (option D):

- **Core stays stdlib-only.** `.claude/hooks/`, `.claude/hooks/_lib/`,
  `.claude/scripts/`, `SPEC/`, `.claude/policies/`, and
  `.github/workflows/*.yml` remain bound by this ADR's invariant.
  Non-stdlib imports in these paths are BLOCKED by canonical-guard
  extension + `.claude/scripts/check-stdlib-only.py` validator.
- **Sidecars permitted under** `.claude/sidecars/<C1-C5>/<name>/`,
  governed by ADR-126's manifest schema + boundary-test contract.
  Sidecars MAY import non-stdlib packages declared in their
  `manifest.json` dependencies. Core code NEVER imports sidecar
  modules (enforced via `boundary_test.py` AST + workflow scan).

This refinement does NOT relax this ADR's invariant for core; it
allows non-stdlib code only in a quarantined, manifest-governed,
boundary-tested sub-tree. ADR-116 KERNEL HARD-DENY paths remain
stdlib-only without exception.

See ADR-126 §Part 1 (core stays stdlib-only) + §Part 2-8 for the
full sidecar contract.

**Status:** ACCEPTED (refined by ADR-126 — see refinement notice above)
**Date:** 2026-04-11 (Sprint 2 A.1–A.5)
**Decision drivers:** stdlib-only (zero install cost), testable with `python3 -m unittest discover`, reproducible across macOS + Linux, no `pip install`, no `PYTHONPATH` gymnastics at the point of use.

## Context

Sprint 2 migrates the two bash hooks (`check-agent-spawn.sh`,
`audit-log.sh`) to Python. The motivation is in PLAN-002 §1 thesis:
Sprint 1 shipped 4 real bugs tied to bash+jq+sed+POSIX quirks
(heredoc stealing stdin, POSIX nested-set warnings, PostToolUse hook
collision, CI YAML block-scalar indentation). Python's stdlib
eliminates every one of these hazards with boring, testable code.

The decision this ADR records is **not** whether to migrate (that's
PLAN-002 Item A); it's **how the Python code should be laid out**
so that:

1. The hooks can `import` shared helpers without pip, venv, or
   `PYTHONPATH` manipulation at invocation time.
2. `python3 -m unittest discover` finds all tests without magic.
3. Target projects that install the framework get a working hook
   system the instant `install.sh` finishes — no extra steps.
4. Python version resolution is explicit, not "whatever python3
   happens to point at".

## Decision drivers

- **Zero install cost.** `install.sh` already exists; adding a
  `pip install -e .` step is a meaningful regression in first-run
  friction, especially on minimal containers.
- **Stdlib only.** Every external dep is a cross-platform support
  matrix expansion. stdlib gives us `json`, `re`, `hashlib`, `fcntl`,
  `unittest`, `multiprocessing`, `pathlib` — everything we need.
- **Testable with discovery.** Tests must work with
  `python3 -m unittest discover -s .claude/hooks/tests -p 'test_*.py'`
  without a `pyproject.toml`, `conftest.py`, or pytest plugin.
- **Version resolution must be explicit.** `python3` on a user's
  PATH is not hermetic (asdf, pyenv, system vs brew, minimal containers).
  A mis-resolved interpreter silently running 3.7 would fail at runtime.
- **Cross-platform.** Must work on macOS (Big Sur+) and Linux
  (Ubuntu 22.04+, Fedora 38+). Windows is out of scope (ADR-002 scope
  limit; `fcntl` makes it infeasible anyway).

## Options considered

### Option A: Flat files + `.sh` wrappers

All hooks are standalone `.py` files with no shared helpers. Any
duplicated logic (redaction regex, payload parsing, lock primitive)
is copy-pasted.

- (+) Zero import magic; each file is self-contained
- (+) `python3 hook.py` just works
- (-) Duplication of ~200 lines across two hooks, and the duplication
  grows with Sprint 3 hooks
- (-) Property-based redaction tests can't cover a shared module
- (-) Bug fixes have to be applied in every file

**Rejected** — duplication is worse than the import gymnastics.

### Option B: `.claude/hooks/` as a proper Python package (CHOSEN)

```
.claude/hooks/
├── _lib/                    # shared stdlib-only package
│   ├── __init__.py
│   ├── payload.py
│   ├── redact.py
│   ├── filelock.py
│   ├── team.py
│   └── testing.py
├── _python-hook.sh          # version resolver + invoker
├── check_agent_spawn.py     # entry point
├── audit_log.py             # entry point
├── tests/
│   ├── test_*.py
│   └── fixtures/
└── legacy/
    ├── check-agent-spawn.sh
    └── audit-log.sh
```

Each hook inserts its parent directory on `sys.path` before importing
from `_lib`:

```python
import sys
from pathlib import Path
sys.path.insert(0, str(Path(__file__).resolve().parent))
from _lib import payload, redact, filelock, team
```

Test files do the same (pointing one level up) and then use absolute
imports. No `__init__.py` under `tests/` — it's a flat directory that
`unittest discover` scans.

- (+) Shared code lives in exactly one place
- (+) Tests run with stock `unittest discover` — no pytest, no conftest
- (+) Zero pip/install steps
- (+) `TestEnvContext` base class centralizes env isolation
- (-) `sys.path.insert(0, ...)` at the top of each file is ugly but
  idiomatic for single-file script packages
- (-) Third-party import systems (mypy, pyright, some IDEs) may need
  a `# type: ignore` on the `from _lib import ...` line — acceptable

**CHOSEN.**

### Option C: `pip install -e .claude/hooks/` with a pyproject.toml

- (+) Cleanest imports
- (+) Standard Python packaging
- (-) Requires pip at install time
- (-) Target projects need to add a bootstrap step to `install.sh`
- (-) Installed package pollutes the user's site-packages
- (-) Airgapped installations fail

**Rejected** — breaks the zero-install property.

## Decision

**Option B.** Layout as specified above. Hooks use
`sys.path.insert(0, str(Path(__file__).parent))` then absolute
imports from `_lib`.

Python version resolution is handled by `_python-hook.sh`, a shim that:

1. Tries in order: `python3.13` → `python3.12` → `python3.11` →
   `python3.10` → `python3.9` → `python3`.
2. Reads `sys.version_info` from each candidate.
3. Accepts the first one that reports `major >= 3, minor >= 9`.
4. Refuses anything `< 3.9` with install instructions written to stderr.
5. Is **fail-open**: if NO compatible Python is found, emits
   `{"decision":"allow"}` on stdout so the session is never bricked.
6. `exec`s the chosen interpreter against the hook script, passing
   through stdin and any trailing args.

The shim is invoked by `settings.json` as:

```
"command": "bash \"$CLAUDE_PROJECT_DIR/.claude/hooks/_python-hook.sh\" check_agent_spawn.py"
```

**Python minimum: 3.9.** This is a concession to the macOS system
Python on older machines (documented in PLAN-002 §11-bis Q1 correction).
All hook code is written with `from __future__ import annotations`,
`typing.Optional/Union` type hints, and avoids `match` statements,
PEP 604 `X | Y` runtime, `tomllib`, and `asyncio.TaskGroup`.

## Consequences

- (+) **Shared code, zero duplication** — `_lib/` holds every helper;
  `payload`, `redact`, `filelock`, `team`, `testing` are imported from
  both hooks and from tests.
- (+) **Property-based tests** — `_lib/redact.py` is exercised by
  seeded-corpora invariant tests (no leak, idempotent, bounded growth)
  in one place.
- (+) **Test isolation** — `TestEnvContext` in `_lib/testing.py` is
  the shared base for every hook test, so env leakage is impossible.
- (+) **Explicit Python resolution** — no silent downgrade to 3.7; the
  shim refuses with a clear error and fail-open.
- (+) **Rollback path** — reverting A.4 restores `settings.json` to
  bash paths; the Python files become orphaned inert code until
  Sprint 3's first commit removes them.
- (-) **`sys.path.insert` boilerplate** — every entry point file has
  4 lines of import bootstrap. Ugly but confined.
- (-) **No `__init__.py` under `tests/`** — means test modules can't
  use relative imports (`from . import x`). We use absolute
  `sys.path.insert` + absolute imports instead. `unittest discover`
  works; relative imports don't.
- (~) **Python 3.9 constraint** — we give up `match`, runtime PEP 604,
  `tomllib`, and `asyncio.TaskGroup`. None are on the hook hot path.
  Sprint 4+ may revisit if we want to raise the minimum.

## Blast radius

**L3** — directory layout, `settings.json` command field, CI workflow
shellcheck scope, two new test framework files (`test_e2e_hook_chain`,
`test_hook_latency`), governance validator required-files list, and
7 documentation files that reference the hook paths. Touched in the
A.4 commit.

## Related commits

- `be0684a` (A.1) — `_lib/` package + 52 tests
- `c1c426e` (A.2) — `check_agent_spawn.py` + 14 tests
- `22144c4` (A.3) — `audit_log.py` + 16 tests + rotation
- `17718df` (A.4) — shim + settings.json switch + legacy move
- `dcaa94e` (A.5) — E2E + latency tests

## Rollback

Revert `17718df` → `settings.json` points at the bash paths again; the
legacy bash files are still in place (they were `git mv`'d, not
deleted). Zero downtime. The Python files become orphaned inert code
that Sprint 3's first commit removes.

## Enforcement commit

`b7aef7ede65d` (retrofit — PLAN-050 Phase 2 / PLAN-045 F-06-03; this anchors the file's introduction commit, not a runtime-behavior commit. For ADRs whose decision was wired into hooks/scripts in a later commit, amend this line manually.)
