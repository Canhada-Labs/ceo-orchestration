"""PLAN-122 WS-1/WS-2 optimizer — the RECOMMENDER-only orchestration engine.

This package is the non-canonical (directly authorable) half of the PLAN-122
"Brutal Optimizer". It is wired as a **RECOMMENDER**: it never auto-dispatches a
``Workflow`` / ``Task`` from a hook (barred at HEAD — a PreToolUse decision has no
``updatedInput``/``additionalContext`` mutation channel and
``check_agent_spawn`` never mutates ``tool_input``). Instead the (canonical,
sentinel-gated) ``UserPromptSubmit`` hook calls :func:`optimizer.recommender.
recommend_for_prompt` and rides the returned advisory string into the session via
``hookSpecificOutput.additionalContext``. The top-level CEO agent reads that
advisory at the top of the turn and decides — in-turn — whether to dispatch a
native harness ``Workflow``, which model to pick per sub-task, and how wide to
fan out.

Layout (every leaf imports ONLY from ``_skeleton`` + ``types`` so the leaves never
import each other — parallel-author-safe; ``fanout`` additionally imports
``model_choice``; ``recommender`` is the façade importing all):

    _skeleton.py        shared stdlib foundation (kill-switches, defensive audit
                        emit, token estimator, env knobs) — NO leaf imports
    types.py            frozen dataclasses + string constants — pure data
    model_normalize.py  PLAN-133 B2 model-name canonicalization (alias/case ONLY,
                        preserves major.minor) — pure data, NO leaf imports
    complexity_gate.py  WS-1 parallelizability/complexity gate (p99 < 5ms)
    model_choice.py     WS-2(a) per-sub-task model-choice brain
    fanout.py           WS-2(b)(c) fan-out plan + budget + token-rate governor
    rag_recommender.py  WS-2(d) optional RAG context-trim hint (CEO_RAG=0 killable)
    recommender.py      WS-1/WS-2 façade — the single hook entry point

Resolves once ``.claude/scripts`` is on ``sys.path`` (seeded by the repo root
``conftest.py`` for pytest; seeded by the hook wiring patch for runtime). Pure
stdlib, Python >= 3.9, ``from __future__ import annotations`` throughout.
"""

from __future__ import annotations

__all__ = [
    "_skeleton",
    "types",
    "model_normalize",
    "complexity_gate",
    "model_choice",
    "fanout",
    "rag_recommender",
    "recommender",
]
