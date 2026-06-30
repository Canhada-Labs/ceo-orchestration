#!/usr/bin/env python3
"""debate-orchestrate.py — multi-round debate orchestrator.

PLAN-011 Phase 5. Generates per-round agent prompts under
`.claude/plans/PLAN-NNN/debate/round-N/*.md`, runs Jaccard convergence
checks between rounds, triggers a Red Team archetype when convergence
hits at round <= 2 (M1 anti-groupthink gate), and applies secret
redaction on consolidated critiques before they're fed forward into the
next round.

## Scope — Sprint 11

This script produces the **orchestration scaffolding + prompt files**.
It does NOT actually spawn live Claude Code Agent invocations —
spawning is a Sprint 12+ wiring step (see ADR-032 §Non-goals). What
ships today:

1. Round-1 proposal.md + one `<archetype>.md` **prompt** per archetype
2. Jaccard convergence detection between consecutive rounds
3. Red Team prompt file generation when M1 gate fires
4. Redaction of the consolidated round-N output before it feeds
   round N+1 agents
5. `debate_event` audit events per round phase
6. `CEO_SOTA_DISABLE=1` fallback to single-round mode

## Usage

    debate-orchestrate.py
        --plan PLAN-NNN
        --proposal "<free-text proposal blurb>"
        [--max-rounds 5]           # default 5, HARD cap 10
        [--archetypes VPE,Security,QA,DevOps,Backend,AI]
        [--plans-root <path>]
        [--threshold 0.7]
        [--round N]                # advance to round N (default 1)
        [--dry-run]                # skip audit emission

## Exit codes

    0 — round N files generated successfully
    1 — arg error / plan file missing / max-rounds exceeded
    2 — consensus reached + red-team written; caller should proceed
    3 — MAX_ROUNDS hit without convergence (terminal; see
        debate-converge.py MAX_ROUNDS constant + PLAN-012 chaos
        CRITICAL-2 "Cost runaway via adversarial injection")
"""

from __future__ import annotations

import argparse
import os
import re
import subprocess
import sys
from datetime import datetime, timezone
from pathlib import Path
from typing import Any, Callable, Dict, List, Optional, Tuple

# HARD cap — refuse to operate past 10 rounds no matter what flags say.
MAX_ROUNDS_HARD_CAP = 10

# Exit code for terminal max-rounds-reached. Distinct from:
#   0 = round generated OK / converged; 1 = arg/plan error;
#   2 = red-team triggered and written. CI + /debate slash command
#   branch on 3 specifically to log escalation to Owner.
EXIT_MAX_ROUNDS_REACHED = 3

# Default archetypes for round 1 — matches the CEO's typical triad
# expanded into the six-archetype debate lineup used by PLAN-011 itself.
DEFAULT_ARCHETYPES: List[str] = [
    "VPE",
    "Security",
    "QA",
    "DevOps",
    "Backend",
    "AI",
]

# Archetype short-name → (full name, kebab slug for filename, primary skill)
_ARCHETYPE_TABLE: Dict[str, Tuple[str, str, str]] = {
    "VPE": ("VP Engineering", "vp-engineering", "architecture-decisions"),
    "Security": ("Staff Security Engineer", "security-engineer", "security-and-auth"),
    "QA": ("Principal QA Architect", "qa-architect", "testing-strategy"),
    "DevOps": ("DevOps & Platform Engineer", "devops-engineer", "devops-ci-cd"),
    "Backend": ("Staff Backend Engineer", "staff-backend", "public-api-design"),
    "AI": ("AI/LLM Lead", "ai-llm-lead", "ai-llm-orchestration"),
    # Red Team is a contingent archetype activated by the M1 gate.
    "RedTeam": ("Red Team", "red-team", "chaos-and-resilience"),
}


def _script_dir() -> Path:
    return Path(__file__).resolve().parent


def _hooks_dir() -> Path:
    return _script_dir().parent / "hooks"


def _load_redact_secrets() -> "Callable[..., str]":
    """Import redact_secrets from _lib, fail-open with identity fallback."""
    hooks = _hooks_dir()
    if str(hooks) not in sys.path:
        sys.path.insert(0, str(hooks))
    try:
        from _lib.redact import redact_secrets  # type: ignore
        return redact_secrets
    except Exception:
        def _identity(text, **kwargs) -> str:  # pragma: no cover
            return text
        return _identity


def _now_iso() -> str:
    return datetime.now(timezone.utc).strftime("%Y-%m-%dT%H:%M:%SZ")


def _plans_root_default() -> Path:
    return _script_dir().parent / "plans"


def _round_dir(plans_root: Path, plan_id: str, round_num: int) -> Path:
    return plans_root / plan_id / "debate" / f"round-{round_num}"


def _parse_archetypes(csv: str) -> List[str]:
    names: List[str] = []
    seen = set()
    for raw in csv.split(","):
        name = raw.strip()
        if not name:
            continue
        if name not in _ARCHETYPE_TABLE:
            raise ValueError(f"unknown archetype: {name!r}")
        if name in seen:
            continue
        seen.add(name)
        names.append(name)
    if not names:
        raise ValueError("--archetypes yielded an empty list")
    return names


def _archetype_slug(name: str) -> str:
    return _ARCHETYPE_TABLE[name][1]


def _archetype_full_name(name: str) -> str:
    return _ARCHETYPE_TABLE[name][0]


def _archetype_skill(name: str) -> str:
    return _ARCHETYPE_TABLE[name][2]


def _emit_max_rounds_event(plan_id: str, round_num: int, *, dry_run: bool = False) -> None:
    """Emit ``debate_event`` phase ``terminated_max_rounds`` (direct
    import — debate-emit.py CLI restricts round 1..3). Fail-open."""
    if dry_run:
        return
    hooks = _hooks_dir()
    if str(hooks) not in sys.path:
        sys.path.insert(0, str(hooks))
    try:
        from _lib.audit_emit import emit_debate_event  # type: ignore
        emit_debate_event(plan_id=plan_id, round_num=round_num,
                          phase="terminated_max_rounds", agent="orchestrator")
    except Exception:
        return


def _emit_audit_event(
    phase: str,
    plan_id: str,
    round_num: int,
    *,
    agent: str = "",
    artifact_path: Optional[str] = None,
    consensus_adjustments: Optional[int] = None,
    dry_run: bool = False,
) -> None:
    """Invoke debate-emit.py as a subprocess. Fail-open: never raise."""
    if dry_run:
        return
    emit_script = _script_dir() / "debate-emit.py"
    if not emit_script.is_file():
        return
    args = [
        sys.executable,
        str(emit_script),
        phase,
        plan_id,
        str(round_num),
    ]
    if agent:
        args += ["--agent", agent]
    if artifact_path is not None:
        args += ["--artifact", artifact_path]
    if consensus_adjustments is not None:
        args += ["--consensus-adjustments", str(consensus_adjustments)]
    try:
        subprocess.run(
            args,
            check=False,
            timeout=5.0,
            stdout=subprocess.DEVNULL,
            stderr=subprocess.DEVNULL,
        )
    except Exception:
        return


# -------------------------------------------------------------------------
# Prompt generation
# -------------------------------------------------------------------------


_PROPOSAL_TEMPLATE = """---
plan: {plan_id}
round: 1
created_at: {ts}
---

# Proposal — {plan_id} round 1

{proposal_body}

## Scope for debate

Each archetype agent critiques this proposal from their skill perspective.
Produce the 7-section critique format from `.claude/plans/DEBATE-SCHEMA.md`
§4 (Verdict, Summary, Risks, Must-fix, Nice-to-have, Unseen,
What I would NOT change).

## Risks

- (propose risks here; this proposal seed itself has no risks yet)
"""


def _render_proposal(plan_id: str, proposal: str) -> str:
    return _PROPOSAL_TEMPLATE.format(
        plan_id=plan_id,
        ts=_now_iso(),
        proposal_body=proposal.strip(),
    )


_AGENT_PROMPT_TEMPLATE = """---
round: {round_num}
archetype: {full_name}
skill: {skill}
agent_persona: (fill-in at spawn time if team.md has a persona)
generated_at: {ts}
---

## Verdict

ADJUST | REJECT | ACCEPT — one-word overall position.

## Summary

- What's the plan trying to do
- Where I think it's strong
- Where I think it's weak

## Risks

- R-{slug_upper}1 — <severity> — <description> — <mitigation>
- R-{slug_upper}2 — <severity> — <description> — <mitigation>

## Must-fix

1. ...

## Nice-to-have

1. ...

## Unseen by the original plan

1. ...

## What I would NOT change

1. ...

---

# Context for {full_name}

You are the {full_name}. Primary skill: `{skill}`.

{previous_round_block}

## Task

Critique the proposal + plan file. Produce the 7-section critique
above. File assignment: write ONLY this file. You MAY read the plan
file, the proposal, any peer critique, your own SKILL.md.
"""


def _render_agent_prompt(
    archetype: str,
    round_num: int,
    previous_round_block: str,
) -> str:
    full_name = _archetype_full_name(archetype)
    slug = _archetype_slug(archetype)
    skill = _archetype_skill(archetype)
    return _AGENT_PROMPT_TEMPLATE.format(
        round_num=round_num,
        full_name=full_name,
        skill=skill,
        slug_upper=re.sub(r"[^A-Z0-9]", "", slug.upper())[:3] or "AGT",
        ts=_now_iso(),
        previous_round_block=previous_round_block,
    )


_RED_TEAM_TEMPLATE = """---
round: {round_num}
archetype: Red Team
skill: chaos-and-resilience
secondary_skill: security-and-auth
generated_at: {ts}
contingent: true
trigger: jaccard>={threshold} at round <= 2 (M1 anti-groupthink gate)
---

## Verdict

RED TEAM FINDINGS — list risks the consensus-forming group missed.

## Mission

You are the Red Team. The prior round showed high-Jaccard convergence
between {prev_round} and {round_num} (score {jaccard:.3f}). Convergence
at round <= 2 is a groupthink risk per PLAN-011 consensus M1.

Your job: find risks the consensus group missed. Do NOT validate their
agreement — attack it.

## Inputs (redacted consolidated critiques)

{consolidated_redacted}

## Risks

- R-RED1 — <severity> — <risk the consensus missed> — <mitigation>
- R-RED2 — <severity> — <risk the consensus missed> — <mitigation>

## Must-fix

1. ...

## What the consensus got wrong

Numbered list. Each with (a) the agreed finding, (b) why it is
incomplete / wrong, (c) what the real risk is.

## Unseen

Risks that no archetype mentioned — single failure modes, rare edge
cases, cross-archetype blind spots.
"""


def _render_red_team_prompt(
    round_num: int,
    jaccard: float,
    threshold: float,
    consolidated_redacted: str,
) -> str:
    return _RED_TEAM_TEMPLATE.format(
        round_num=round_num,
        ts=_now_iso(),
        threshold=threshold,
        jaccard=jaccard,
        prev_round=round_num - 1,
        consolidated_redacted=consolidated_redacted.strip() or "(none)",
    )


# -------------------------------------------------------------------------
# Redaction of consolidated critiques (M6)
# -------------------------------------------------------------------------


def _anon_label(idx: int) -> str:
    return "Critic-%s" % chr(ord("A") + idx) if idx < 26 else "Critic-%d" % (idx + 1)


def consolidate_round(round_dir: Path) -> str:
    """Concatenate all agent critique files from a round, ANONYMIZED.

    DEBATE-SCHEMA §13.2 (PLAN-134 W1, Codex S228 finding #4): the
    consolidated text that feeds round N+1 / red-team / synthesis carries
    `Critic-A/B/C` labels instead of archetype filenames; persona-identifying
    frontmatter keys (archetype/agent_persona/skill) are stripped and
    archetype-name strings scrubbed from bodies. The label↔file mapping is
    written to `round_dir/anonymization-map.md` for audit (best-effort —
    consolidation never fails on a map-write error). Non-critique files
    (consensus/proposal/synthesis/red-team/anonymization-map) excluded.
    On-disk critique files keep their names (§13.2 item 4).
    """
    if not round_dir.is_dir():
        return ""
    excluded = {
        "proposal.md",
        "consensus.md",
        "synthesis.md",
        "red-team.md",
        "anonymization-map.md",
    }
    critique_files = [
        p for p in sorted(round_dir.iterdir())
        if p.suffix == ".md" and p.name not in excluded
    ]
    labels: Dict[str, str] = {
        p.name: _anon_label(i) for i, p in enumerate(critique_files)
    }
    # Name fragments to scrub from bodies (anti-halo): file stems and their
    # space variants, longest first so 'security-engineer' wins over 'security'.
    frags: List[str] = []
    for p in critique_files:
        frags.extend((p.stem, p.stem.replace("-", " ")))
    frags = sorted({f for f in frags if len(f) >= 4}, key=len, reverse=True)
    parts: List[str] = []
    for p in critique_files:
        try:
            text = p.read_text(encoding="utf-8")
        except OSError:
            continue
        label = labels[p.name]
        kept: List[str] = []
        in_fm = False
        first = True
        for line in text.splitlines():
            s = line.strip()
            if first:
                first = False
                if s == "---":
                    in_fm = True
                    kept.append(line)
                    continue
            if in_fm:
                if s == "---":
                    in_fm = False
                    kept.append(line)
                    continue
                if s.startswith(("archetype:", "agent_persona:", "skill:")):
                    continue  # identifying frontmatter stripped (§13.2 item 2)
            kept.append(line)
        body = "\n".join(kept)
        for frag in frags:
            body = re.sub(re.escape(frag), label, body, flags=re.IGNORECASE)
        parts.append(f"### {label}\n\n{body}")
    if critique_files:
        round_m = re.match(r"round-(\d+)$", round_dir.name)
        plan = next(
            (a.name for a in round_dir.parents if a.name.startswith("PLAN-")),
            "unknown",
        )
        map_text = "\n".join(
            ["---", f"plan: {plan}",
             "round: %s" % (round_m.group(1) if round_m else round_dir.name),
             "labels:"]
            + ["  %s: %s" % (labels[p.name], p.stem) for p in critique_files]
            + ["---", ""]
        )
        try:
            (round_dir / "anonymization-map.md").write_text(
                map_text, encoding="utf-8"
            )
        except OSError:
            pass
    return "\n\n".join(parts)


def redact_consolidated(text: str) -> str:
    """Apply `_lib.redact.redact_secrets` to consolidated text.

    max_chars=0 → no truncation. The bounded-growth invariant from
    redact.py still caps output at 2x input.
    """
    redact = _load_redact_secrets()
    try:
        return redact(text, max_chars=0)
    except TypeError:
        # Fallback if redact signature differs (fail-open)
        return redact(text)


# -------------------------------------------------------------------------
# Convergence wiring
# -------------------------------------------------------------------------


def _load_debate_converge() -> Any:
    """Dynamic-import debate-converge.py (hyphen); sys.modules-cached
    so @dataclass annotation resolution on Python 3.9 succeeds."""
    import importlib.util
    key = "debate_converge_module"
    cached = sys.modules.get(key)
    if cached is not None:
        return cached
    spec = importlib.util.spec_from_file_location(key, _script_dir() / "debate-converge.py")
    if spec is None or spec.loader is None:
        raise RuntimeError("failed to load debate-converge module")
    mod = importlib.util.module_from_spec(spec)
    sys.modules[key] = mod  # register BEFORE exec_module
    spec.loader.exec_module(mod)
    return mod


def check_convergence(
    plans_root: Path,
    plan_id: str,
    round_num: int,
    threshold: float,
) -> Dict[str, object]:
    """Import and call debate-converge's compute_convergence.

    Returns the result dict. Raises FileNotFoundError if prior round
    data is missing (orchestrator must ensure round N-1 exists before
    calling check_convergence for round N).
    """
    return _load_debate_converge().compute_convergence(
        plans_root, plan_id, round_num, threshold=threshold
    )


# -------------------------------------------------------------------------
# Orchestrator — per-round work
# -------------------------------------------------------------------------


def generate_round_1(
    plans_root: Path,
    plan_id: str,
    proposal: str,
    archetypes: List[str],
    *,
    dry_run: bool = False,
) -> List[Path]:
    """Write proposal.md + one prompt file per archetype under round-1/.

    Returns the list of files written.
    """
    round_dir = _round_dir(plans_root, plan_id, 1)
    round_dir.mkdir(parents=True, exist_ok=True)

    written: List[Path] = []

    # Emit 'start' audit event for this round
    _emit_audit_event("start", plan_id, 1, dry_run=dry_run)

    proposal_path = round_dir / "proposal.md"
    proposal_path.write_text(
        _render_proposal(plan_id, proposal), encoding="utf-8"
    )
    written.append(proposal_path)
    _emit_audit_event(
        "start",
        plan_id,
        1,
        artifact_path=str(proposal_path),
        dry_run=dry_run,
    )

    # Previous round block is empty at round 1
    previous_block = "## Previous round consolidated critiques\n\n(none — this is round 1)"

    for archetype in archetypes:
        slug = _archetype_slug(archetype)
        path = round_dir / f"{slug}.md"
        path.write_text(
            _render_agent_prompt(archetype, 1, previous_block),
            encoding="utf-8",
        )
        written.append(path)
        _emit_audit_event(
            "agent-done",
            plan_id,
            1,
            agent=slug,
            artifact_path=str(path),
            dry_run=dry_run,
        )
    return written


def generate_round_n(
    plans_root: Path,
    plan_id: str,
    round_num: int,
    archetypes: List[str],
    *,
    dry_run: bool = False,
) -> List[Path]:
    """Generate round-N/ prompts; consume round N-1 consolidated+redacted."""
    if round_num < 2:
        raise ValueError(f"round_num must be >= 2 for generate_round_n (got {round_num})")

    prev_dir = _round_dir(plans_root, plan_id, round_num - 1)
    if not prev_dir.is_dir():
        raise FileNotFoundError(f"prior round missing: {prev_dir}")

    round_dir = _round_dir(plans_root, plan_id, round_num)
    round_dir.mkdir(parents=True, exist_ok=True)

    _emit_audit_event("start", plan_id, round_num, dry_run=dry_run)

    # M6 — redact before feed-forward
    raw = consolidate_round(prev_dir)
    redacted = redact_consolidated(raw)

    previous_block = (
        f"## Previous round consolidated critiques (redacted)\n\n"
        f"```\n{redacted.strip()}\n```"
    )

    written: List[Path] = []
    for archetype in archetypes:
        slug = _archetype_slug(archetype)
        path = round_dir / f"{slug}.md"
        path.write_text(
            _render_agent_prompt(archetype, round_num, previous_block),
            encoding="utf-8",
        )
        written.append(path)
        _emit_audit_event(
            "agent-done",
            plan_id,
            round_num,
            agent=slug,
            artifact_path=str(path),
            dry_run=dry_run,
        )
    return written


def maybe_trigger_red_team(
    plans_root: Path,
    plan_id: str,
    round_num: int,
    threshold: float,
    *,
    dry_run: bool = False,
) -> Optional[Path]:
    """Compute convergence; if red_team_needed, write round-(N+1)/red-team.md.

    Returns the red-team path (or None). The next-round directory is
    created as a side effect if the gate fires.
    """
    result = check_convergence(plans_root, plan_id, round_num, threshold)
    if not result.get("red_team_needed"):
        return None

    target_round = round_num + 1
    target_dir = _round_dir(plans_root, plan_id, target_round)
    target_dir.mkdir(parents=True, exist_ok=True)

    # Pull the consolidated+redacted text from round N for the prompt
    raw = consolidate_round(_round_dir(plans_root, plan_id, round_num))
    redacted = redact_consolidated(raw)

    path = target_dir / "red-team.md"
    path.write_text(
        _render_red_team_prompt(
            target_round,
            float(result["jaccard"]),
            float(threshold),
            redacted,
        ),
        encoding="utf-8",
    )
    _emit_audit_event(
        "agent-done",
        plan_id,
        target_round,
        agent="red-team",
        artifact_path=str(path),
        dry_run=dry_run,
    )
    return path


def write_unresolved_consensus(
    plans_root: Path,
    plan_id: str,
    round_num: int,
    max_rounds: int,
    jaccard_score: float,
    *,
    dry_run: bool = False,
) -> Path:
    """Write consensus.md with status: unresolved when max-rounds exhausted."""
    round_dir = _round_dir(plans_root, plan_id, round_num)
    round_dir.mkdir(parents=True, exist_ok=True)
    path = round_dir / "consensus.md"
    body = (
        f"---\n"
        f"plan: {plan_id}\n"
        f"round: {round_num}\n"
        f"status: unresolved\n"
        f"max_rounds: {max_rounds}\n"
        f"final_jaccard: {jaccard_score:.6f}\n"
        f"synthesized_at: {_now_iso()}\n"
        f"synthesized_by: debate-orchestrate\n"
        f"---\n\n"
        f"## Escalation required\n\n"
        f"Max rounds ({max_rounds}) exhausted without convergence. "
        f"Final Jaccard score: {jaccard_score:.3f} (threshold 0.7).\n\n"
        f"Escalate to Owner — something is wrong with the plan or the "
        f"archetype mix.\n"
    )
    path.write_text(body, encoding="utf-8")
    _emit_audit_event(
        "consensus",
        plan_id,
        round_num,
        artifact_path=str(path),
        consensus_adjustments=0,
        dry_run=dry_run,
    )
    return path


# -------------------------------------------------------------------------
# CLI
# -------------------------------------------------------------------------


def _parse(argv: List[str]) -> argparse.Namespace:
    p = argparse.ArgumentParser(
        description="Orchestrate a multi-round debate with convergence + Red Team gate"
    )
    p.add_argument("--plan", required=True, help="Plan ID (PLAN-NNN)")
    p.add_argument(
        "--proposal",
        default="",
        help="Proposal blurb (required for --round 1)",
    )
    p.add_argument(
        "--max-rounds",
        type=int,
        default=5,
        help="Max rounds (default 5; HARD cap 10)",
    )
    p.add_argument(
        "--archetypes",
        default=",".join(DEFAULT_ARCHETYPES),
        help="CSV of archetype short names",
    )
    p.add_argument(
        "--round",
        type=int,
        default=1,
        dest="round_num",
        help="Round to generate (default 1)",
    )
    p.add_argument(
        "--plans-root",
        type=str,
        default=None,
        help="Override plans root",
    )
    p.add_argument(
        "--threshold",
        type=float,
        default=0.7,
        help="Jaccard threshold for convergence (default 0.7)",
    )
    p.add_argument(
        "--dry-run",
        action="store_true",
        help="Skip audit emission",
    )
    return p.parse_args(argv)


def _validate_args(
    args,
) -> "Tuple[Optional[List[str]], Optional[Path], int]":
    """Validate CLI args, parse archetypes, resolve plans_root.

    Returns ``(archetypes, plans_root, 0)`` on success;
    ``(None, None, 1)`` on validation error (with stderr already
    printed).
    """
    if not re.match(r"^PLAN-[0-9]{3}$", args.plan):
        print(
            f"ERROR: --plan must match PLAN-NNN (got {args.plan!r})",
            file=sys.stderr,
        )
        return None, None, 1
    if args.max_rounds < 1 or args.max_rounds > MAX_ROUNDS_HARD_CAP:
        print(
            f"ERROR: --max-rounds must be in [1, {MAX_ROUNDS_HARD_CAP}] "
            f"(got {args.max_rounds})",
            file=sys.stderr,
        )
        return None, None, 1
    if args.round_num < 1 or args.round_num > args.max_rounds:
        print(
            f"ERROR: --round must be in [1, {args.max_rounds}] "
            f"(got {args.round_num})",
            file=sys.stderr,
        )
        return None, None, 1
    try:
        archetypes = _parse_archetypes(args.archetypes)
    except ValueError as e:
        print(f"ERROR: {e}", file=sys.stderr)
        return None, None, 1
    plans_root = (
        Path(args.plans_root).resolve() if args.plans_root else _plans_root_default()
    )
    return archetypes, plans_root, 0


def _run_sota_disabled(args, plans_root, archetypes) -> int:
    """CEO_SOTA_DISABLE=1 single-round fallback path."""
    if args.round_num != 1:
        print(
            "CEO_SOTA_DISABLE=1: only round 1 is generated in fallback mode",
            file=sys.stderr,
        )
        return 1
    if not args.proposal:
        print("ERROR: --proposal required for round 1", file=sys.stderr)
        return 1
    written = generate_round_1(
        plans_root,
        args.plan,
        args.proposal,
        archetypes,
        dry_run=args.dry_run,
    )
    print(f"SOTA disabled — single-round mode; wrote {len(written)} files")
    for w in written:
        print(f"  {w}")
    return 0


def _handle_convergence(conv, args, plans_root) -> "Optional[int]":
    """Dispatch on convergence result after round-N write.

    Returns an exit code if the caller should return immediately, or
    ``None`` to fall through to ``return 0``.
    """
    print(
        f"  jaccard={conv['jaccard']:.3f} "
        f"converged={conv['converged']} "
        f"red_team_needed={conv['red_team_needed']} "
        f"outcome={conv.get('outcome', '')}"
    )
    if conv.get("max_rounds_reached"):
        _emit_max_rounds_event(args.plan, args.round_num, dry_run=args.dry_run)
        unresolved_path = write_unresolved_consensus(
            plans_root, args.plan, args.round_num, args.max_rounds,
            float(conv.get("jaccard", 0.0)), dry_run=args.dry_run,
        )
        max_rounds_const = getattr(_load_debate_converge(), "MAX_ROUNDS", 5)
        print(
            f"[ORCHESTRATOR] MAX_ROUNDS={max_rounds_const} reached "
            f"without convergence. Terminating.",
            file=sys.stderr,
        )
        print(f"  Max rounds exhausted; unresolved consensus at {unresolved_path}")
        return EXIT_MAX_ROUNDS_REACHED
    if conv.get("red_team_needed"):
        rt_path = maybe_trigger_red_team(
            plans_root,
            args.plan,
            args.round_num,
            args.threshold,
            dry_run=args.dry_run,
        )
        if rt_path:
            print(f"  Red Team prompt written: {rt_path}")
            return 2
    elif conv["converged"] and args.round_num > 2:
        _emit_audit_event(
            "consensus",
            args.plan,
            args.round_num,
            artifact_path=str(
                _round_dir(plans_root, args.plan, args.round_num)
                / "consensus.md"
            ),
            consensus_adjustments=0,
            dry_run=args.dry_run,
        )
        print("  Consensus reached (round > 2); caller should write consensus.md")
    elif args.round_num >= args.max_rounds:
        final_jaccard = float(conv.get("jaccard", 0.0))
        unresolved_path = write_unresolved_consensus(
            plans_root,
            args.plan,
            args.round_num,
            args.max_rounds,
            final_jaccard,
            dry_run=args.dry_run,
        )
        print(
            f"  Max rounds exhausted; unresolved consensus at {unresolved_path}"
        )
    return None


def main(argv: Optional[List[str]] = None) -> int:
    """CLI orchestrator (PLAN-023 Phase E decomposition).

    Thin 40-line shell over ``_validate_args`` + ``_run_sota_disabled``
    + ``_handle_convergence`` helpers; behavior byte-identical to the
    pre-decomposition 162-LoC monolith.
    """
    args = _parse(argv if argv is not None else sys.argv[1:])

    archetypes, plans_root, err = _validate_args(args)
    if err:
        return err

    if os.environ.get("CEO_SOTA_DISABLE") == "1":
        return _run_sota_disabled(args, plans_root, archetypes)

    # Normal multi-round flow — round 1
    if args.round_num == 1:
        if not args.proposal:
            print("ERROR: --proposal required for round 1", file=sys.stderr)
            return 1
        written = generate_round_1(
            plans_root, args.plan, args.proposal, archetypes, dry_run=args.dry_run
        )
        print(f"Round 1 generated; wrote {len(written)} files")
        for w in written:
            print(f"  {w}")
        return 0

    # Round N (N>=2)
    written = generate_round_n(
        plans_root,
        args.plan,
        args.round_num,
        archetypes,
        dry_run=args.dry_run,
    )
    print(f"Round {args.round_num} generated; wrote {len(written)} files")
    for w in written:
        print(f"  {w}")

    try:
        conv = check_convergence(
            plans_root, args.plan, args.round_num, args.threshold
        )
    except FileNotFoundError as e:
        print(f"  convergence skipped: {e}", file=sys.stderr)
        conv = None

    if conv is not None:
        exit_code = _handle_convergence(conv, args, plans_root)
        if exit_code is not None:
            return exit_code
    return 0


if __name__ == "__main__":
    sys.exit(main())
