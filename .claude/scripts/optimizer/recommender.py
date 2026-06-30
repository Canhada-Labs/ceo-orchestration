"""WS-1/WS-2 FAÇADE — the single entry point the guarded ``UserPromptSubmit``
hook imports.

Orchestrates ``complexity_gate`` → ``fanout`` → ``rag_recommender``, assembles the
``additionalContext`` advisory string + the structured
:class:`optimizer.types.Recommendation`, emits the guarded audit telemetry via
:func:`optimizer._skeleton.safe_emit` (a silent no-op until the canonical bundle
registers the new actions), and returns ONLY a string to the hook. The RAG leg is
invoked here ONLY when ``in_hook=False`` (the hook passes ``in_hook=True`` to skip
synchronous sidecar IO per the <100 ms hook SLO). It **NEVER dispatches** a
``Workflow`` / ``Task``; the advisory carries no command the harness will
auto-execute. Fail-open: any exception yields ``''`` so the hook's ADR-005
never-blocks contract is preserved.
"""

from __future__ import annotations

import dataclasses
import json
import sys
from pathlib import Path
from typing import List, Optional

from . import complexity_gate, fanout, rag_recommender
from ._skeleton import optimizer_enabled, safe_emit
from .types import (
    FanoutPlan,
    GateResult,
    RagHint,
    Recommendation,
    ROUTE_PASSTHROUGH,
)

# Hard cap on the advisory string (additionalContext is bounded by contract).
_MAX_CONTEXT_CHARS = 4000
# Per-label cap inside the advisory render.
_MAX_LABEL_CHARS = 80


def _sanitize_label(label: str) -> str:
    """Neutralise a prompt-derived label before rendering it into the
    additionalContext advisory: collapse all whitespace (kills newline /
    control-char injection that could forge a system frame in the higher-trust
    channel) and hard-cap the length. Defense-in-depth alongside the hook-side
    fail-closed-on-injection gate (multi-lens review P1)."""
    try:
        collapsed = " ".join(str(label).split())
        return collapsed[:_MAX_LABEL_CHARS]
    except Exception:
        return ""


def _len_bucket(prompt: str) -> int:
    """Map prompt length to a small int bucket (audit-safe, no free text)."""
    n = len(prompt) if isinstance(prompt, str) else 0
    if n < 80:
        return 0
    if n < 240:
        return 1
    if n < 800:
        return 2
    return 3


def build_recommendation(
    gate: GateResult,
    fan: Optional[FanoutPlan],
    rag: Optional[RagHint],
) -> Recommendation:
    """Pure assembler — render the bounded agent-readable advisory. Never raises."""
    try:
        lines: List[str] = []
        lines.append("[CEO OPTIMIZER — advisory only; you remain the dispatcher]")
        lines.append(
            "Route: %s (complexity=%s, parallelizable=%s). Suggested width: %d."
            % (gate.route, gate.complexity, "yes" if gate.parallelizable else "no", gate.suggested_width)
        )
        if fan is not None and fan.subtasks:
            lines.append(
                "Recommended fan-out (dispatch a native Workflow in-turn — your call):"
            )
            for st in fan.subtasks:
                model = st.model or "(harness default)"
                lines.append("  %d. %s -> %s (~%d tok)" % (st.index + 1, _sanitize_label(st.label), model, st.est_tokens_in))
            lines.append(
                "Governors: width=%d, width_capped=%s, budget_governed=%s, rate_backoff=%s."
                % (
                    fan.suggested_width,
                    "yes" if fan.width_capped else "no",
                    "yes" if fan.budget_governed else "no",
                    "yes" if fan.rate_backoff_applied else "no",
                )
            )
        if rag is not None and rag.available and rag.context_block:
            lines.append("RAG context (trimmed, %d chunks):" % rag.chunks_returned)
            lines.append(rag.context_block)
        lines.append("Disable with CEO_OPTIMIZER=0. This is a recommendation, not a command.")

        block = "\n".join(lines)
        if len(block) > _MAX_CONTEXT_CHARS:
            block = block[: _MAX_CONTEXT_CHARS - 3] + "..."
        return Recommendation(gate=gate, fanout=fan, rag=rag, context_block=block)
    except Exception:
        return Recommendation(gate=gate, fanout=fan, rag=rag, context_block="")


def recommend_for_prompt(
    prompt: str,
    repo_root: Path,
    session_id: str = "",
    in_hook: bool = True,
) -> str:
    """Hook-facing call: return the advisory string (``''`` if nothing to add).

    Fail-open — the whole body is wrapped so any exception yields ``''`` and the
    hook falls back to its existing pass-through path.
    """
    try:
        if not optimizer_enabled():
            return ""
        gate = complexity_gate.classify(prompt)
        if gate.route == ROUTE_PASSTHROUGH:
            return ""

        fan = fanout.plan(prompt, gate)
        # Skip synchronous sidecar IO inside the latency-critical hook. The
        # out-of-hook path forwards in_hook=False so rag_recommender actually
        # runs the lever (route_query → health probe → rag_search).
        rag = None if in_hook else rag_recommender.recommend(prompt, repo_root, in_hook=False)

        rec = build_recommendation(gate, fan, rag)

        # --- guarded telemetry (silent no-op until the canonical bundle lands) -
        rr = Path(repo_root) if repo_root else None
        safe_emit(
            "optimizer_route_recommended",
            repo_root=rr,
            session_id=session_id,
            route=gate.route,
            complexity_bucket=gate.complexity,
            parallelizable=int(gate.parallelizable),
            suggested_width=gate.suggested_width,
            prompt_len_bucket=_len_bucket(prompt),
            kill_switch_state="on",
        )
        if fan is not None and fan.subtasks:
            safe_emit(
                "fanout_recommended",
                repo_root=rr,
                session_id=session_id,
                subtask_count=len(fan.subtasks),
                suggested_width=fan.suggested_width,
                width_capped=int(fan.width_capped),
                budget_governed=int(fan.budget_governed),
                rate_backoff_applied=int(fan.rate_backoff_applied),
                models_basis=",".join(sorted({st.model for st in fan.subtasks if st.model}))[:200],
            )
            for st in fan.subtasks:
                # SEC MF-3: never persist st.label — it is prompt-derived free
                # text (may contain file paths / secrets). Emit the index +
                # the REAL model-choice telemetry carried on the SubTask.
                safe_emit(
                    "model_choice_recommended",
                    repo_root=rr,
                    session_id=session_id,
                    subtask_index=st.index,
                    model_recommended=st.model or "default",
                    confidence_basis_points=st.confidence_basis_points,
                    cost_governed=int(st.cost_governed),
                    fell_back_to_static=int(st.fell_back_to_static),
                )
        if rag is not None and rag.available:
            safe_emit(
                "rag_context_recommended",
                repo_root=rr,
                session_id=session_id,
                router_decision=rag.router_decision,
                chunks_returned=rag.chunks_returned,
                kill_switch_state="on",
            )

        return rec.context_block
    except Exception:
        return ""


def _to_dict(rec: Recommendation) -> dict:
    """Structured Recommendation → JSON-able dict (debug/benchmark CLI)."""
    return dataclasses.asdict(rec)


def main(argv: Optional[List[str]] = None) -> int:
    """Optional debug CLI: ``--prompt TEXT`` or stdin → json.dumps the structured
    Recommendation. Not wired into any hook. Returns 0."""
    import argparse

    parser = argparse.ArgumentParser(description="PLAN-122 optimizer recommender (debug CLI)")
    parser.add_argument("--prompt", default=None, help="prompt text; reads stdin if omitted")
    parser.add_argument("--repo-root", default=".", help="repo root for the RAG leg")
    parser.add_argument("--in-hook", action="store_true", help="skip the RAG leg (hook mode)")
    args = parser.parse_args(argv)

    prompt = args.prompt if args.prompt is not None else sys.stdin.read()
    gate = complexity_gate.classify(prompt)
    fan = fanout.plan(prompt, gate)
    rag = None if args.in_hook else rag_recommender.recommend(prompt, Path(args.repo_root), in_hook=False)
    rec = build_recommendation(gate, fan, rag)
    print(json.dumps(_to_dict(rec), indent=2, sort_keys=True))
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
