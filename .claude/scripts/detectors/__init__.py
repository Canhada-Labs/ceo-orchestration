"""PLAN-047 Phase 1 — ghost-token detectors.

Stdlib-only detectors that scan the CEO audit-log for patterns
correlated with wasted tokens. Each detector is a standalone
module exposing `detect(log_path: Path, ...) -> List[Finding]`.

Detectors (clean-room, derived from AUDIT-LOG-SCHEMA.md semantics):

- retry_churn         — same (session, subagent, skill) repeat spawns
- tool_cascade        — long chains of short-response spawns
- looping             — same subagent repeat with similar desc_hash
- wasteful_thinking   — Opus on short non-VETO tasks
- weak_model          — Haiku on VETO roles (governance slip)
- overpowered         — Opus/Sonnet on short devops tasks

See `.claude/plans/PLAN-047/phase-0-baseline.md` for the baseline
snapshot + clean-room declaration.
"""
from __future__ import annotations
