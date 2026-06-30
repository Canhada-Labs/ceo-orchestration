"""PLAN-133 C3 — real-task reward benchmark task suite.

Each task module in this package defines a single ``TASK`` dict describing a
small, real software-engineering task with a **deterministic verifier** that
emits a scalar ``reward`` in ``[0.0, 1.0]``. The runner (``..runner``) sets up
an isolated working directory per task, drives the CEO orchestration to attempt
the instruction (real subscription quota — NOT free), then runs the verifier
against the resulting tree.

A task module MUST expose a module-level ``TASK`` dict with the schema in
``TASK_SCHEMA`` below. The contract is intentionally tiny and stdlib-only so a
task is trivially unit-testable in isolation (the verifier is a pure function of
the on-disk tree).

## TASK schema (all keys required)

| key | type | meaning |
|---|---|---|
| ``id`` | str | unique, stable task id (e.g. ``"py-fix-off-by-one"``). |
| ``title`` | str | one-line human label. |
| ``category`` | str | grouping bucket (``bugfix`` / ``feature`` / ``refactor`` / ``test`` / ``docs``). |
| ``difficulty`` | str | ``easy`` / ``medium`` / ``hard`` (advisory; affects nothing). |
| ``setup`` | callable | ``setup(workdir: Path) -> None`` writes the starting files into ``workdir``. |
| ``instruction`` | str | the natural-language task handed to the orchestration. |
| ``verify`` | callable | ``verify(workdir: Path) -> float`` returns a reward in ``[0, 1]``. |

The verifier MUST be:
- **deterministic** — same tree in, same reward out (no clocks, no network);
- **fail-safe** — never raises; a missing/empty file yields a low reward, not a
  crash (the runner clamps to ``[0, 1]`` defensively regardless);
- **partial-credit aware** — return intermediate rewards (e.g. ``0.5``) when the
  attempt is partially correct, so the reporter can surface ``partial``.

## Discovery

``load_all_tasks()`` imports every ``*.py`` module in this package (except
dunder files), reads its ``TASK``, validates the schema, and returns the list
sorted by ``id``. Discovery is import-time safe: a task module must not do any
work at import (no network, no filesystem writes) beyond defining functions.
"""

from __future__ import annotations

import importlib
import pkgutil
from pathlib import Path
from typing import Any, Callable, Dict, List

# Required keys + their expected python types. Callables are checked separately.
_REQUIRED_STR_KEYS = ("id", "title", "category", "difficulty", "instruction")
_REQUIRED_CALLABLE_KEYS = ("setup", "verify")

VALID_CATEGORIES = ("bugfix", "feature", "refactor", "test", "docs")
VALID_DIFFICULTIES = ("easy", "medium", "hard")


def validate_task(task: Dict[str, Any], *, source: str = "<task>") -> List[str]:
    """Return a list of human-readable validation errors (empty == valid).

    Pure + total: never raises, so the runner can surface a bad task as a
    skipped row rather than crashing the whole benchmark.
    """
    errors: List[str] = []
    if not isinstance(task, dict):
        return [f"{source}: TASK must be a dict, got {type(task).__name__}"]
    for key in _REQUIRED_STR_KEYS:
        val = task.get(key)
        if not isinstance(val, str) or not val.strip():
            errors.append(f"{source}: TASK[{key!r}] must be a non-empty str")
    for key in _REQUIRED_CALLABLE_KEYS:
        if not callable(task.get(key)):
            errors.append(f"{source}: TASK[{key!r}] must be callable")
    cat = task.get("category")
    if isinstance(cat, str) and cat not in VALID_CATEGORIES:
        errors.append(
            f"{source}: TASK['category']={cat!r} not in {VALID_CATEGORIES}"
        )
    diff = task.get("difficulty")
    if isinstance(diff, str) and diff not in VALID_DIFFICULTIES:
        errors.append(
            f"{source}: TASK['difficulty']={diff!r} not in {VALID_DIFFICULTIES}"
        )
    return errors


def load_all_tasks() -> List[Dict[str, Any]]:
    """Import every task module in this package and return validated TASK dicts.

    Skips modules that fail validation (logs nothing — the runner reports the
    skip). Returns the list sorted by ``id`` for deterministic ordering (a
    benchmark must run tasks in a stable order to be comparable run-to-run).
    """
    tasks: List[Dict[str, Any]] = []
    seen_ids = set()
    pkg_path = [str(Path(__file__).resolve().parent)]
    for mod_info in pkgutil.iter_modules(pkg_path):
        name = mod_info.name
        if name.startswith("_"):
            continue
        try:
            module = importlib.import_module(f"{__name__}.{name}")
        except Exception:  # pragma: no cover — a broken task module is skipped
            continue
        task = getattr(module, "TASK", None)
        if task is None:
            continue
        if validate_task(task, source=name):
            continue
        tid = task["id"]
        if tid in seen_ids:
            continue
        seen_ids.add(tid)
        tasks.append(task)
    tasks.sort(key=lambda t: t["id"])
    return tasks


# ---------------------------------------------------------------------------
# Verifier helpers shared by the task modules (stdlib-only, pure).
# ---------------------------------------------------------------------------


def read_text(workdir: Path, rel: str) -> str:
    """Read a file under ``workdir`` returning '' on any error (fail-safe)."""
    try:
        return (workdir / rel).read_text(encoding="utf-8")
    except Exception:
        return ""


def run_python(workdir: Path, rel: str, *, func: str, args: tuple) -> Any:
    """Exec a python file under ``workdir`` in a fresh namespace and call ``func``.

    Returns the call result, or the sentinel ``_VERIFY_ERROR`` on ANY failure
    (syntax error, missing func, raised exception). The verifier turns that
    sentinel into a low reward — it never propagates.

    Hermetic: the exec namespace gets a copy of builtins only; the file is read
    from the sandbox ``workdir``. No import of the file as a package (so a task's
    solution file name can be anything).
    """
    src = read_text(workdir, rel)
    if not src.strip():
        return _VERIFY_ERROR
    ns: Dict[str, Any] = {"__name__": "__candidate__", "__file__": str(workdir / rel)}
    try:
        compiled = compile(src, str(workdir / rel), "exec")
        exec(compiled, ns)  # noqa: S102 — sandbox eval of candidate solution by design
        fn = ns.get(func)
        if not callable(fn):
            return _VERIFY_ERROR
        return fn(*args)
    except Exception:
        return _VERIFY_ERROR


class _VerifyError:
    """Sentinel returned by ``run_python`` on any candidate failure."""

    __slots__ = ()

    def __repr__(self) -> str:  # pragma: no cover — debug aid only
        return "<VERIFY_ERROR>"


_VERIFY_ERROR = _VerifyError()


def clamp_reward(value: Any) -> float:
    """Coerce any verifier output to a float reward in ``[0.0, 1.0]``.

    Non-numeric / NaN / inf → 0.0. The runner calls this on every verifier
    result so a misbehaving verifier can never poison the aggregate.
    """
    try:
        f = float(value)
    except (TypeError, ValueError):
        return 0.0
    if f != f or f in (float("inf"), float("-inf")):  # NaN / inf
        return 0.0
    if f < 0.0:
        return 0.0
    if f > 1.0:
        return 1.0
    return f
