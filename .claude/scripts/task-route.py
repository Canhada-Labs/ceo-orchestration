#!/usr/bin/env python3
"""task-route.py — Adaptive Execution Kernel pre-task classifier (advisory-only).

PLAN-071 §4.2 Phase 1 deliverable. Reads task description + file hints,
emits a Task Execution Contract v1 covering classification (S/M/L/XL),
ceremony mode, recommended agents, context strategy, and review gates.

ADVISORY ONLY: this script never blocks the CEO. Output is consumed
by humans + dispatch logic at CEO discretion. Exit code 0 = success,
2 = internal error (Sec NTH #5).

Composition (read-only — paths corrected per Round 1 R-CR1):
- ``.claude/team.md`` ROUTING TABLE — work-type → archetype lookup
- ``_lib/tier_policy/_constants.py::VETO_HARDCODE`` — 2-role hardcode floor
- ``_lib/tier_policy/_constants.py::EXPECTED_VETO_FLOOR_UNION`` — 6-role spec floor
- ``_lib/tier_policy/_types.py::ROLE_TO_TASK_TYPES`` — reverse routing index
- ``_lib/agent_frontmatter.py::VETO_FLOOR_ROLES`` — runtime 6-role canonical
- ``.claude/settings.json::ceo_quality_profile`` — `balanced`/`fast`/`careful`

Robustness:
- 8 KiB input cap on task description
- NFKC normalize BOTH task_description AND file_hints (defeats ZWJ + homoglyph)
- 200ms ITIMER budget across full classify() call (NOT per-pattern)
- 8-step `--files` path validator (no traversal, no symlink escape, no NUL)
- Stdlib only; Python 3.9+

Audit emission (deferred until KERNEL ceremony Phase 5 lands
``task_route_advised`` action in ``audit_emit._KNOWN_ACTIONS``):
- hasattr-guarded best-effort emit; advisory-only fallback when unwired

S87 Phase 1 skeleton scope (delivered):
  decision tree §3.3 + NFKC + VETO union assertion + ReDoS guard +
  8-step --files validator + --format markdown + --format json
  Task Execution Contract v1 + deterministic JSON output

S87 Phase 1 acceptance gaps (next session):
  - ≥30 mutation fixtures (5 bypass classes × 6 roles)
  - 8 adversarial + ZWJ + homoglyph + pathological-backtrack fixtures
  - p95 < 200ms cold-start benchmark
  - audit_emit task_route_advised wiring (depends on Phase 5 KERNEL)
"""

from __future__ import annotations

import argparse
import hashlib
import hmac
import json
import os
import re
import sys
import time
import unicodedata
import uuid
from datetime import datetime, timezone
from pathlib import Path
from typing import Any, Dict, FrozenSet, List, Optional, Tuple

# ---------------------------------------------------------------------------
# _lib / tier_policy imports — composition, not reimplementation
# ---------------------------------------------------------------------------

_REPO_ROOT = Path(__file__).resolve().parent.parent.parent
_HOOKS_LIB = _REPO_ROOT / ".claude" / "hooks"

if str(_HOOKS_LIB) not in sys.path:
    sys.path.insert(0, str(_HOOKS_LIB))

try:
    from _lib.tier_policy._constants import (
        VETO_HARDCODE,
        EXPECTED_VETO_FLOOR_UNION,
        CLASSIFICATION_MODES,
    )
    from _lib.tier_policy._types import ROLE_TO_TASK_TYPES
    from _lib.agent_frontmatter import VETO_FLOOR_ROLES
    from _lib.injection_salt import get_instance_salt
    from _lib.secret_patterns import (
        _install_itimer_guard,
        _clear_itimer_guard,
        ScanBudgetExceeded,
    )
except ImportError as exc:
    sys.stderr.write(
        f"[task-route] FATAL import error: {exc.__class__.__name__}: {exc}\n"
    )
    sys.exit(2)


# ---------------------------------------------------------------------------
# Constants — closed enums + invariants
# ---------------------------------------------------------------------------

SCHEMA_VERSION = "task-execution-contract.v1"

MAX_TASK_DESCRIPTION_BYTES = 8 * 1024  # 8 KiB cap (R-PERF U2)
MAX_FILE_HINTS = 50  # R2 advisory A4
ITIMER_BUDGET_SECONDS = 0.2  # 200ms total across classify()

CEREMONY_MODES = frozenset({
    "direct",  # S — no /spawn, CEO operates directly
    "1-agent-with-veto",  # M — single agent + VETO floor
    "multi-agent",  # L — multiple agents in parallel
    "debate",  # XL — full Plan→Debate→Execute
})

# Veto-domain keywords (regex, NFKC-normalized input)
_VETO_KEYWORDS = re.compile(
    r"\b("
    r"auth|authentication|authorisation|authorization|"
    r"token|jwt|oauth|sso|"
    r"crypto|cipher|encrypt|decrypt|signing|"
    r"password|passcode|"
    r"secret|credential|"
    r"financial|payment|billing|invoice|"
    r"phi|hipaa|"
    r"decimal|monetary|"
    r"injection|xss|csrf|sqli|"
    r"timing.oracle|side.channel|constant.time"
    r")\b",
    re.IGNORECASE,
)

# Schema/migration signals
_SCHEMA_SIGNALS = re.compile(
    r"\b(schema|migrat\w+|spec/v\d+|column|alter\s+table|drop\s+table)\b",
    re.IGNORECASE,
)

# Workflow-class signals (filename-based)
_WORKFLOW_RELEASE = re.compile(r"\.github/workflows/(release|deploy|publish)")
_WORKFLOW_CI = re.compile(r"\.github/workflows/(validate|coverage|tournament|mcp-smoke|tier-policy|reality-ledger|benchmarks)")
_WORKFLOW_RAG = re.compile(r"\.claude/rag/")
_WORKFLOW_TEST_INFRA = re.compile(r"(^|/)(tests?/conftest\.py|pytest\.ini|tox\.ini|setup\.cfg|pyproject\.toml)$|^Makefile$")

# Canonical guards subset (mirrors check_canonical_edit.py _CANONICAL_GUARDS;
# kept inline as a regex to avoid importing the hook module — a parser-bug
# fix in that hook should NOT silently shift task-route.py's behavior).
_CANONICAL_REGEXES = [
    re.compile(r"^\.claude/team\.md$"),
    re.compile(r"^\.claude/frontend-team\.md$"),
    re.compile(r"^\.claude/skills/(core|frontend)/[^/]+/SKILL\.md$"),
    re.compile(r"^\.claude/skills/domains/.+/SKILL\.md$"),
    re.compile(r"^\.claude/hooks/.*\.py$"),
    re.compile(r"^\.claude/policies/.*\.yaml$"),
    re.compile(r"^\.claude/adr/ADR-\d{3,}-.*\.md$"),
    re.compile(r"^\.claude/adr/README\.md$"),
    re.compile(r"^\.claude/plans/PLAN-\d{3,}/spec\.md$"),
    re.compile(r"^\.claude/scripts/lessons\.py$"),
    re.compile(r"^\.claude/scripts/prune-lessons\.py$"),
    re.compile(r"^\.claude/scripts/lesson-restore\.py$"),
    re.compile(r"^\.claude/scripts/lesson_ranker\.py$"),
    re.compile(r"^\.claude/.*conftest\.py$"),
    re.compile(r"^\.claude/hooks/check_confidence_gate\.py$"),
    re.compile(r"^\.github/CODEOWNERS$"),
    re.compile(r"^\.github/workflows/release\.yml$"),
    re.compile(r"^SPEC/v\d+/.*\.md$"),
    re.compile(r"^PROTOCOL\.md$"),
]


# ---------------------------------------------------------------------------
# VETO floor union — invariant assertion at module load
# ---------------------------------------------------------------------------

def _compute_veto_floor() -> FrozenSet[str]:
    """Union of VETO_HARDCODE keys + agent_frontmatter.VETO_FLOOR_ROLES.

    Per PLAN-071 §3.1 #6 / §4.2 line 388. Returns the computed union.

    Pre-PLAN-071-Phase-2 / Pre-PLAN-074-Wave-1c tolerance:
    `_lib/tier_policy/_constants.py::EXPECTED_VETO_FLOOR_UNION` documents
    a 6-role spec contract whose 4 forward-looking roles
    (incident-commander, identity-trust-architect, threat-detection-engineer,
    llm-finops-architect) only land in `_lib/agent_frontmatter.VETO_FLOOR_ROLES`
    AFTER the next sentinel ceremony adds them atomically alongside their
    `.claude/agents/<role>.md` files (S90 P0-01 atomic-add invariant). Until
    that ceremony lands, the computed union is a strict subset of the spec
    union — this is the **documented-tolerance** state per the constants.py
    docstring ("may NOT yet have agent definition files... declares the spec
    contract independent of on-disk presence").

    Module load MUST stay tolerant of this gap: raising on a documented-
    tolerance state would break dispatch advisory in every fresh-install
    or partial-deployment scenario. A breach IS reportable telemetry — but
    via stderr breadcrumb + audit-log, NOT via RuntimeError on import.

    A future PLAN-074-Wave-1c ceremony lands the 3 VETO-floor agent files
    + frozenset additions atomically; once that ceremony ships, the
    computed union becomes a full superset of the spec union and this
    function's breach detection drops to zero unless someone deletes a
    deployed entry. Spec drift detection remains the responsibility of
    `validate-governance.sh` + the `test_veto_floor_roles_bijection_with_deployed_agents`
    test contract (Wave 1c-staged in `_artifacts/adr-052-amendment.patch`).
    """
    union = frozenset(VETO_HARDCODE.keys()) | VETO_FLOOR_ROLES
    if not (union >= EXPECTED_VETO_FLOOR_UNION):
        # Documented-tolerance state — emit advisory breadcrumb + return
        # the computed subset. Do NOT raise on import; that breaks every
        # downstream consumer (advisory dispatcher, /ceo-boot, hook chain).
        try:
            sys.stderr.write(
                "task-route: VETO floor union pre-Phase-2 (computed=%s, "
                "spec=%s, diff=%s) — advisory mode; "
                "see PLAN-074-Wave-1c-veto-floor-matrix for the atomic-add "
                "contract.\n" % (
                    sorted(union),
                    sorted(EXPECTED_VETO_FLOOR_UNION),
                    sorted(EXPECTED_VETO_FLOOR_UNION - union),
                )
            )
        except Exception:  # pragma: no cover — stderr write never fatal
            pass
    return union


COMPUTED_VETO_FLOOR: FrozenSet[str] = _compute_veto_floor()


# ---------------------------------------------------------------------------
# --files 8-step path validator (PLAN-071 R-SEC6)
# ---------------------------------------------------------------------------

class FileHintError(ValueError):
    """Raised when --files argument fails 8-step validator."""


def _validate_file_hint(path_str: str, repo_root: Path) -> str:
    """8-step validator per PLAN-071 §4.2 R-SEC6.

    Returns the repo-relative posix path on success; raises FileHintError
    on any rejection condition.

    Codex audit fix #2: backslash check repeats AFTER NFKC (defeats
    fullwidth backslash U+FF3C → ASCII `\\` normalize bypass); pre-resolve
    lstat scan catches symlinks at any path component (resolve() collapses
    the chain, making post-resolve symlink test mostly dead).
    """
    # 1. NUL byte
    if "\x00" in path_str:
        raise FileHintError(f"NUL byte in path: {path_str!r}")
    # 2a. Backslash (literal — Windows traversal vector)
    if "\\" in path_str:
        raise FileHintError(f"Backslash in path: {path_str!r}")
    # 3. NFKC normalize
    normalized = unicodedata.normalize("NFKC", path_str)
    # 2b. Re-check backslash AFTER NFKC (Codex audit fix #2:
    # fullwidth backslash U+FF3C normalizes to ASCII `\\`)
    if "\\" in normalized:
        raise FileHintError(f"Backslash in normalized path: {normalized!r}")
    # 4. Reject absolute paths
    if normalized.startswith("/") or normalized.startswith("~"):
        raise FileHintError(f"Absolute path rejected: {normalized!r}")
    # 5. Pre-resolve symlink scan (Codex audit fix #2):
    # lstat each path component to catch symlink-escape attempts BEFORE
    # resolve() collapses them. resolve() returns the symlink target,
    # so a post-resolve `is_symlink()` check is mostly unreachable.
    candidate = repo_root / normalized
    cur = repo_root
    try:
        for part in Path(normalized).parts:
            cur = cur / part
            if cur.is_symlink():
                target = cur.readlink()
                # Resolve relative to symlink's parent (POSIX semantics)
                if not target.is_absolute():
                    target = (cur.parent / target).resolve(strict=False)
                else:
                    target = target.resolve(strict=False)
                try:
                    target.relative_to(repo_root.resolve())
                except ValueError as exc:
                    raise FileHintError(
                        f"Symlink component escapes repo: {normalized!r} "
                        f"({cur} -> {target})"
                    ) from exc
    except OSError:
        # lstat() failure on non-existent path is fine — only resolved
        # paths matter; broken-symlink detection at step 5/6 below.
        pass
    # 6+7. Resolve + relative_to (raises ValueError if outside repo)
    try:
        resolved = candidate.resolve(strict=False)
        rel = resolved.relative_to(repo_root.resolve())
    except (ValueError, OSError) as exc:
        raise FileHintError(f"Path escapes repo root: {normalized!r}") from exc
    rel_posix = str(rel).replace(os.sep, "/")
    # 8. Reject any `..` component in the resolved-relative path
    if any(part == ".." for part in rel.parts):
        raise FileHintError(f"`..` component: {rel_posix!r}")
    return rel_posix


# ---------------------------------------------------------------------------
# Classification — decision tree §3.3
# ---------------------------------------------------------------------------

def _match_canonical(file_hints_rel: List[str]) -> List[str]:
    """Return file_hints that match canonical guard regexes."""
    matches: List[str] = []
    for hint in file_hints_rel:
        for regex in _CANONICAL_REGEXES:
            if regex.search(hint):
                matches.append(hint)
                break
    return matches


def _detect_veto_keywords(task_description: str) -> Optional[str]:
    """Returns matched veto-domain keyword (or None). Single-shot regex."""
    m = _VETO_KEYWORDS.search(task_description)
    return m.group(1).lower() if m else None


def _count_modules(file_hints_rel: List[str]) -> int:
    """Distinct top-level directory roots."""
    if not file_hints_rel:
        return 0
    roots = set()
    for hint in file_hints_rel:
        parts = hint.split("/", 2)
        # Use first 2 segments as "module root" (e.g., src/auth or .claude/hooks)
        if len(parts) >= 2:
            roots.add(f"{parts[0]}/{parts[1]}")
        else:
            roots.add(parts[0])
    return len(roots)


def _detect_schema_signals(task_description: str, file_hints_rel: List[str]) -> bool:
    if _SCHEMA_SIGNALS.search(task_description):
        return True
    for hint in file_hints_rel:
        if hint.startswith("SPEC/v") or "migration" in hint.lower() or hint.endswith(".sql"):
            return True
    return False


def _detect_workflow_signal(file_hints_rel: List[str]) -> Optional[str]:
    """Returns 'release' / 'ci' / 'rag' / 'test-infra' or None."""
    for hint in file_hints_rel:
        if _WORKFLOW_RELEASE.search(hint):
            return "release"
        if _WORKFLOW_CI.search(hint):
            return "ci"
        if _WORKFLOW_RAG.search(hint):
            return "rag"
        if _WORKFLOW_TEST_INFRA.search(hint):
            return "test-infra"
    return None


def _strip_invisible_format_chars(s: str) -> str:
    """Strip Unicode Cf (format) category — defeats ZWJ / ZWNJ / RTL override.

    NFKC does NOT strip Cf. Per PLAN-071 §3.3 the goal is "defeat ZWJ,
    RTL override, fullwidth homoglyph"; NFKC handles compatibility
    homoglyphs (fullwidth, etc.) but invisible separators need explicit
    Cf removal. Applied BEFORE NFKC so word boundaries reform cleanly.
    """
    return "".join(c for c in s if unicodedata.category(c) != "Cf")


def classify(task_description: str, file_hints_rel: List[str]) -> Dict[str, Any]:
    """Pure classification — no I/O, no clock except for itimer guard.

    Returns dict with 'classification', 'rationale' list, and signal map.
    Bounded by ITIMER_BUDGET_SECONDS via _install_itimer_guard.
    """
    # Strip Cf (invisible format chars) FIRST, then NFKC (R-SEC5 + R-SEC6)
    sanitized_task = _strip_invisible_format_chars(task_description)
    sanitized_hints = [_strip_invisible_format_chars(h) for h in file_hints_rel]
    nfkc_task = unicodedata.normalize("NFKC", sanitized_task)
    nfkc_hints = [unicodedata.normalize("NFKC", h) for h in sanitized_hints]

    prev_handler = _install_itimer_guard(ITIMER_BUDGET_SECONDS)
    try:
        canonical_paths = _match_canonical(nfkc_hints)
        veto_domain = _detect_veto_keywords(nfkc_task)
        n_modules = _count_modules(nfkc_hints)
        multi_module = n_modules >= 3
        schema_change = _detect_schema_signals(nfkc_task, nfkc_hints)
        workflow_change = _detect_workflow_signal(nfkc_hints)
    except ScanBudgetExceeded:
        return {
            "classification": "M",
            "rationale": ["ITIMER budget exceeded — fail-safe to M"],
            "signals": {"itimer_exceeded": True},
        }
    finally:
        _clear_itimer_guard(prev_handler)

    rationale: List[str] = []
    signals: Dict[str, Any] = {
        "canonical_paths": canonical_paths,
        "veto_domain": veto_domain,
        "n_modules": n_modules,
        "multi_module": multi_module,
        "schema_change": schema_change,
        "workflow_change": workflow_change,
        "n_files": len(nfkc_hints),
    }

    # XL conditions (Codex audit fix #1: add multi_module+test_infra → XL per §3.3)
    if canonical_paths:
        rationale.append(f"Canonical-guarded path(s): {canonical_paths[:3]}")
        return {"classification": "XL", "rationale": rationale, "signals": signals}
    if veto_domain in ("auth", "authentication", "authorisation", "authorization", "financial", "phi", "hipaa", "payment"):
        if multi_module:
            rationale.append(f"Auth/financial/PHI veto domain ({veto_domain}) + multi-module → XL")
            return {"classification": "XL", "rationale": rationale, "signals": signals}
    if schema_change:
        rationale.append("Schema/migration/SPEC change → XL")
        return {"classification": "XL", "rationale": rationale, "signals": signals}
    if workflow_change in ("release", "ci", "rag"):
        rationale.append(f"Workflow class '{workflow_change}' → XL")
        return {"classification": "XL", "rationale": rationale, "signals": signals}
    # NEW (Codex audit): multi_module AND test-infra → XL per §3.3 line 259
    if multi_module and workflow_change == "test-infra":
        rationale.append("Multi-module + test-infra workflow → XL")
        return {"classification": "XL", "rationale": rationale, "signals": signals}

    # L conditions
    if multi_module:
        rationale.append(f"{n_modules} distinct module roots → L")
        return {"classification": "L", "rationale": rationale, "signals": signals}
    if workflow_change == "test-infra":
        rationale.append("Test-infra workflow change → L")
        return {"classification": "L", "rationale": rationale, "signals": signals}

    # M-veto: any veto domain immediately → M
    if veto_domain:
        rationale.append(f"VETO-protected domain ({veto_domain}) → M")
        return {"classification": "M", "rationale": rationale, "signals": signals}

    # S — strict gate (Codex audit fix #1: 0 < len() to reject empty file list).
    # Empty --files MUST fall to safe-default M, not S; an Owner-task with no
    # file hints is too ambiguous for advisory-S classification.
    if (
        0 < len(nfkc_hints) <= 2
        and not veto_domain
        and not canonical_paths
        and not schema_change
        and workflow_change is None
    ):
        rationale.append("≤2 files, no veto, no canonical, no schema/workflow → S")
        return {"classification": "S", "rationale": rationale, "signals": signals}

    # M-default: 3-4 files OR empty hints OR boundary cases
    if len(nfkc_hints) <= 4:
        rationale.append(f"{len(nfkc_hints)} files, no decisive S signal → M default")
        return {"classification": "M", "rationale": rationale, "signals": signals}

    # Safe default
    rationale.append("Safe default — no decisive signal")
    return {"classification": "M", "rationale": rationale, "signals": signals}


# ---------------------------------------------------------------------------
# Contract assembly
# ---------------------------------------------------------------------------

def _hmac_task(task_description: str) -> Optional[str]:
    """HMAC-SHA256 of task description with instance salt.

    Returns None when salt is unavailable (per R-SEC N3 — never falls back
    to constant; preserves ADR-079 invariant).
    """
    salt = get_instance_salt()
    if not salt:
        return None
    return hmac.new(salt, task_description.encode("utf-8"), hashlib.sha256).hexdigest()


def _ceremony_for(classification: str, veto_domain: Optional[str]) -> Tuple[str, bool]:
    """Returns (ceremony_mode, debate_required)."""
    if classification == "S":
        return "direct", False
    if classification == "M":
        return "1-agent-with-veto", False
    if classification == "L":
        return "multi-agent", False
    if classification == "XL":
        return "debate", True
    return "1-agent-with-veto", False  # safe default


def _agents_for(
    classification: str,
    veto_domain: Optional[str],
    workflow_change: Optional[str],
    schema_change: bool,
) -> List[Dict[str, Any]]:
    """Recommended agents per classification + signal map.

    Per PLAN-071 §3.1 #6: VETO floor union (6 roles) is reachable via
    COMPUTED_VETO_FLOOR. CR + Sec are always Opus per ADR-052.
    """
    agents: List[Dict[str, Any]] = []

    if classification == "S":
        return agents  # CEO operates directly

    # M+: VETO floor minimum (CR + Sec when veto domain detected)
    if veto_domain or classification in ("M", "L", "XL"):
        if classification == "M" and not veto_domain:
            agents.append({
                "archetype": "Staff Code Reviewer",
                "role": "code-reviewer",
                "skill": "code-review-checklist",
                "model": "claude-opus-4-8",
                "veto_floor": True,
                "consumption_class": "advisory-actionable",
            })
        else:
            agents.append({
                "archetype": "Principal Security Engineer",
                "role": "security-engineer",
                "skill": "security-and-auth",
                "model": "claude-opus-4-8",
                "veto_floor": True,
                "consumption_class": "advisory-actionable",
            })
            agents.append({
                "archetype": "Staff Code Reviewer",
                "role": "code-reviewer",
                "skill": "code-review-checklist",
                "model": "claude-opus-4-8",
                "veto_floor": True,
                "consumption_class": "advisory-actionable",
            })

    # Add specialty roles per signal
    if workflow_change == "release" or workflow_change == "ci":
        agents.append({
            "archetype": "DevOps & Platform Engineer",
            "role": "devops",
            "skill": "devops-ci-cd",
            "model": "claude-opus-4-8",
            "veto_floor": False,
            "consumption_class": "advisory-actionable",
        })

    if schema_change or classification == "L" or classification == "XL":
        # qa-architect for L+
        if classification in ("L", "XL"):
            agents.append({
                "archetype": "Principal QA Architect",
                "role": "qa-architect",
                "skill": "testing-strategy",
                "model": "claude-sonnet-4-6",
                "veto_floor": False,
                "consumption_class": "advisory-actionable",
            })

    return agents


def _context_strategy(classification: str, n_files: int) -> Dict[str, Any]:
    """Per §1.2 row 4: defer rerank/RAG/HyDE to L+ + tier-1 repos."""
    if classification == "S":
        return {
            "primary": "grep+read",
            "rerank": False,
            "rag_sidecar": False,
            "hyde": False,
            "skill_index": False,
            "rationale": "Tier 0 — single-symbol target, NFKC grep sufficient",
            "consumption_class": "advisory-readonly",
        }
    if classification == "M":
        return {
            "primary": "grep+read",
            "rerank": False,
            "rag_sidecar": False,
            "hyde": False,
            "skill_index": True,
            "rationale": "Tier 0/1 — symbol-known + skill-aware",
            "consumption_class": "advisory-readonly",
        }
    if classification == "L":
        return {
            "primary": "grep+read+rerank",
            "rerank": True,
            "rag_sidecar": False,
            "hyde": False,
            "skill_index": True,
            "rationale": "Tier 1 — multi-module benefits from rerank",
            "consumption_class": "advisory-readonly",
        }
    # XL
    return {
        "primary": "grep+read+rerank+rag",
        "rerank": True,
        "rag_sidecar": True,
        "hyde": True,
        "skill_index": True,
        "rationale": "Tier 2 — canonical/schema/workflow change, full pipeline",
        "consumption_class": "advisory-readonly",
    }


def build_contract(
    task_description: str,
    file_hints_rel: List[str],
) -> Dict[str, Any]:
    """Assemble Task Execution Contract v1 — deterministic JSON output."""
    cls = classify(task_description, file_hints_rel)
    classification = cls["classification"]
    rationale = cls["rationale"]
    signals = cls["signals"]

    ceremony_mode, debate = _ceremony_for(classification, signals.get("veto_domain"))
    agents = _agents_for(
        classification,
        signals.get("veto_domain"),
        signals.get("workflow_change"),
        bool(signals.get("schema_change")),
    )
    ctx = _context_strategy(classification, signals.get("n_files", 0))

    review_gates = sorted({
        f"{a['role']} VETO" for a in agents if a.get("veto_floor")
    })

    contract: Dict[str, Any] = {
        "schema_version": SCHEMA_VERSION,
        "contract_id": str(uuid.uuid4()),
        "issued_at": datetime.now(timezone.utc).strftime("%Y-%m-%dT%H:%M:%SZ"),
        "task_description_hmac": _hmac_task(task_description),
        "classification": classification,
        "classification_rationale": rationale,
        "ceremony": {
            "mode": ceremony_mode,
            "debate": debate,
            "brainstorm": classification == "XL",
            "veto_holders": sorted([a["role"] for a in agents if a.get("veto_floor")]),
        },
        "agents": agents,
        "context_strategy": ctx,
        "file_assignment": {
            "may_edit": sorted(file_hints_rel),
            "forbidden": ["everything else"],
            "parallelism": "single-agent-sequential" if len(agents) <= 1 else "multi-agent-parallel",
            "consumption_class": "advisory-actionable",
        },
        "tests": {
            "minimum": ["existing tests still pass"],
            "additional": [],
            "escalation_if_fails": f"{classification} → escalate one tier (add qa-architect if absent)",
            "consumption_class": "advisory-readonly",
        },
        "review_gates": review_gates,
        "execution_receipt_required": classification in ("L", "XL"),
        "residual_risks": [],
        "auto_escalate_triggers": [
            {"signal": "edit touches >1 file beyond contract", "promote_to": "L"},
            {"signal": "test diff > 50 LoC", "promote_to": "L"},
            {"signal": "any auth pattern change", "promote_to": "L + debate"},
        ],
    }

    # Deterministic JSON: sort lists where ordering doesn't carry meaning
    contract["agents"].sort(key=lambda a: a.get("role", ""))

    return contract


# ---------------------------------------------------------------------------
# Output rendering
# ---------------------------------------------------------------------------

def render_markdown(contract: Dict[str, Any]) -> str:
    """Human-readable digest (≤30 lines per CEO eyeball spec)."""
    lines: List[str] = []
    lines.append(f"# Task Execution Contract — classification: **{contract['classification']}**")
    lines.append("")
    lines.append("## Rationale")
    for r in contract["classification_rationale"]:
        lines.append(f"- {r}")
    lines.append("")
    lines.append(f"## Ceremony: {contract['ceremony']['mode']}")
    lines.append(f"- debate: {contract['ceremony']['debate']}")
    lines.append(f"- brainstorm: {contract['ceremony']['brainstorm']}")
    lines.append(f"- veto holders: {', '.join(contract['ceremony']['veto_holders']) or '—'}")
    lines.append("")
    if contract["agents"]:
        lines.append("## Recommended agents")
        for a in contract["agents"]:
            floor = " [VETO]" if a.get("veto_floor") else ""
            lines.append(f"- {a['archetype']} ({a['role']}, {a['model']}){floor}")
        lines.append("")
    lines.append("## Context strategy")
    lines.append(f"- {contract['context_strategy']['rationale']}")
    lines.append("")
    if contract["review_gates"]:
        lines.append("## Review gates")
        for g in contract["review_gates"]:
            lines.append(f"- {g}")
    lines.append("")
    lines.append(f"_contract_id: `{contract['contract_id']}`_")
    return "\n".join(lines)


def render_json(contract: Dict[str, Any]) -> str:
    """Deterministic JSON (sorted keys + sorted inner lists)."""
    return json.dumps(contract, indent=2, sort_keys=True, ensure_ascii=False)


# ---------------------------------------------------------------------------
# CLI
# ---------------------------------------------------------------------------

def _parse_files_arg(arg: Optional[str], repo_root: Path) -> List[str]:
    """Parse --files comma-separated arg through 8-step validator."""
    if not arg:
        return []
    raw = [p.strip() for p in arg.split(",") if p.strip()]
    if len(raw) > MAX_FILE_HINTS:
        raise FileHintError(
            f"Too many --files entries ({len(raw)} > {MAX_FILE_HINTS} cap)"
        )
    validated: List[str] = []
    for p in raw:
        validated.append(_validate_file_hint(p, repo_root))
    return validated


def main(argv: Optional[List[str]] = None) -> int:
    parser = argparse.ArgumentParser(
        prog="task-route",
        description="Adaptive Execution Kernel pre-task classifier (advisory-only).",
    )
    parser.add_argument("--task", required=True, help="Task description (≤8 KiB)")
    parser.add_argument("--files", default="", help="Comma-separated file hints (≤50)")
    parser.add_argument("--format", choices=("markdown", "json"), default="markdown")
    parser.add_argument("--explain", action="store_true", help="Verbose rationale")
    parser.add_argument("--repo-root", default=str(_REPO_ROOT))

    args = parser.parse_args(argv)

    # Input cap
    task_bytes = args.task.encode("utf-8")
    if len(task_bytes) > MAX_TASK_DESCRIPTION_BYTES:
        sys.stderr.write(
            f"[task-route] task description {len(task_bytes)} bytes > "
            f"{MAX_TASK_DESCRIPTION_BYTES} cap\n"
        )
        return 2

    repo_root = Path(args.repo_root).resolve()
    if not repo_root.exists():
        sys.stderr.write(f"[task-route] repo-root not found: {repo_root}\n")
        return 2

    try:
        file_hints = _parse_files_arg(args.files, repo_root)
    except FileHintError as exc:
        sys.stderr.write(f"[task-route] --files validation failed: {exc}\n")
        return 2

    t0 = time.perf_counter()
    contract = build_contract(args.task, file_hints)
    elapsed_ms = int((time.perf_counter() - t0) * 1000)

    contract["duration_ms"] = elapsed_ms

    if args.format == "markdown":
        print(render_markdown(contract))
        if args.explain:
            print("")
            print("## Signals")
            print("```json")
            print(json.dumps(
                {"signals": classify(args.task, file_hints).get("signals")},
                indent=2, sort_keys=True,
            ))
            print("```")
    else:  # json
        print(render_json(contract))

    # PLAN-071 / ADR-104 — emit task_route_advised audit event.
    # hasattr-guarded best-effort: action lands in _KNOWN_ACTIONS via
    # the v1.14.0 KERNEL ceremony. Pre-ceremony, emit_generic returns
    # silently for unknown actions (no crash). Sec MF-3 allowlist
    # enforced inside audit_emit; only whitelisted fields persist.
    try:
        from _lib import audit_emit as _audit_emit
        if hasattr(_audit_emit, "emit_generic"):
            _audit_emit.emit_generic(
                "task_route_advised",
                contract_id=contract["contract_id"],
                classification=contract["classification"],
                task_description_hmac=contract["task_description_hmac"],
                duration_ms=elapsed_ms,
                project=os.environ.get("CLAUDE_PROJECT_DIR", ""),
                session_id=os.environ.get("CLAUDE_SESSION_ID", ""),
            )
    except Exception:
        # Advisory-only: emission failure NEVER blocks the user.
        pass

    return 0


if __name__ == "__main__":
    sys.exit(main())
