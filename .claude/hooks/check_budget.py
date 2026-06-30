#!/usr/bin/env python3
"""PreToolUse Agent hook: Cost/Budget advisory (Sprint 11 Phase 6).

PLAN-011 Phase 6 (ADR-033). Ships as **Sprint 11 advisory-only**: when
the running token total for the active plan exceeds the configured cap,
the hook emits a ``budget_exceeded`` audit event and a systemMessage
warning but NEVER blocks the spawn. Sprint 12 may flip to enforcing
behavior IFF FPR baseline data supports it (see ADR-033 Flip Criteria
Table).

## Wire-up

Registered in ``.claude/settings.json`` PreToolUse Agent (appended
below the existing ``check_agent_spawn.py`` entry)::

    {
      "matcher": "Agent",
      "hooks": [
        {
          "type": "command",
          "command": "bash \"$CLAUDE_PROJECT_DIR/.claude/hooks/_python-hook.sh\" check_budget.py",
          "timeout": 5,
          "statusMessage": "Checking token budget..."
        }
      ]
    }

## Decision logic (Sprint 11 State 0 — advisory)

1. Resolve the active plan_id by scanning ``.claude/plans/PLAN-*.md``
   for exactly one file whose frontmatter ``status`` is one of the
   "active" states (``executing``, ``reviewed``, ``draft``). If zero
   or more than one match the plan_id is indeterminate → skip check.
2. Sum ``tokens_total`` across audit-log ``agent_spawn`` events whose
   ``project`` matches the current ``CLAUDE_PROJECT_DIR``. Null
   ``tokens_total`` values are treated as 0 (ADR-016 contract).
3. Compare against the resolved cap (precedence below).
4. If over cap: emit ``budget_exceeded`` event (with
   ``cap_source`` field), build a WARNING systemMessage, ALWAYS allow
   (State 0).
5. Bypass: ``CEO_BUDGET_BYPASS=1`` emits ``budget_bypass_used`` (H13
   audit requirement) and allows. Rate-limited to
   ``CEO_BUDGET_BYPASS_MAX_PER_DAY`` (default 10) per plan_id: when
   exhausted, we still allow (State 0 is advisory) but log a WARNING
   breadcrumb to ``audit-log.errors`` and SKIP the
   ``budget_bypass_used`` emit so the quota enforcement is honest.

## Cap precedence (PLAN-065 §4.5.D)

ADR-033 extension: a plan author may declare a per-plan cap in
frontmatter. Resolution order:

1. **Plan frontmatter** ``max_tokens: <int>`` (PLAN-065 §4.5.D). Must
   be a positive integer literal in the closed range
   ``[1, 10_000_000]``. Strings, scientific notation, negatives,
   booleans, lists, aliases (``&anchor``) are REJECTED with a
   breadcrumb + fall-through. The 10M ceiling is a defense-in-depth
   guard against accidental ``50000000`` typos that would silently
   uncap the budget.
2. **Env** ``CEO_MAX_PLAN_TOKENS`` (existing).
3. **Default** ``1_000_000``.

The resolved source is recorded in the ``budget_exceeded`` event's
``cap_source`` field as one of ``"plan_frontmatter"`` /
``"env"`` / ``"default"`` so audit-tokens can attribute caps.

## Env var surface

| Var                              | Default   | Meaning |
|----------------------------------|-----------|---------|
| ``CEO_MAX_SPAWN_TOKENS``         | 100_000   | Logged only in Sprint 11 (spawn-scope cap reserved for Sprint 12). |
| ``CEO_MAX_PLAN_TOKENS``          | 1_000_000 | Plan-scope cap; triggers ``budget_exceeded`` event when exceeded. Overridden by frontmatter ``max_tokens:`` when present + valid. |
| ``CEO_BUDGET_BYPASS``            | unset     | ``1`` → bypass mode (still allows in State 0). |
| ``CEO_BUDGET_BYPASS_MAX_PER_DAY``| 10        | Rate limit: at most N ``budget_bypass_used`` emits per plan / 24h. |
| ``CEO_BUDGET_ENFORCE``           | ``0``     | Sprint 11 default. Flip criterion in ADR-033. |
| ``CEO_BUDGET_QUOTA_HINT``        | ``1``     | PLAN-135 W5 O4: ``0`` disables reading the statusLine sidecar to append a live rate-limit line to the over-cap warning. Advisory text only — never gates the decision. |
| ``CEO_STATUSLINE_SIDECAR``       | unset     | PLAN-135 W5 O4: full-path override of the statusLine sidecar read for the quota hint (else ``<CEO_AUDIT_LOG_DIR or ~/.claude/projects/ceo-orchestration>/state/statusline-snapshot.json``). |

## Fail-open contract (ADR-005, CLAUDE.md §Critical Rules)

Any exception during plan resolution, audit-log scanning, frontmatter
parse, or filesystem error → breadcrumb + allow. The hook NEVER
blocks a user session on an infrastructure bug. Empty stdin is
tolerated (allow). Malformed JSON stdin → allow.

Stdlib only. Python >= 3.9.
"""

from __future__ import annotations

import json
import os
import re
import sys
from datetime import datetime, timezone
from pathlib import Path
from typing import Any, Dict, List, Optional, Tuple

# Make the local _lib importable
_HOOKS_DIR = Path(__file__).resolve().parent
if str(_HOOKS_DIR) not in sys.path:
    sys.path.insert(0, str(_HOOKS_DIR))

from _lib import contract as _contract  # noqa: E402
from _lib.adapters import claude as _claude_adapter  # noqa: E402
from _lib import plan_frontmatter as _plan_frontmatter  # noqa: E402


# ---------------------------------------------------------------------------
# Constants
# ---------------------------------------------------------------------------

# Defaults surfaced at module scope so tests can monkey-patch.
DEFAULT_MAX_SPAWN_TOKENS = 100_000
DEFAULT_MAX_PLAN_TOKENS = 1_000_000
DEFAULT_BYPASS_MAX_PER_DAY = 10

# Defense-in-depth ceiling for frontmatter ``max_tokens:``. Anything
# above this is rejected — protects against accidental extra zeroes
# that would silently uncap the budget. Matches PLAN-065 §4.5.D.
MAX_TOKENS_CEILING = 10_000_000

# Frontmatter ``status`` values treated as "the plan is live right now".
# Anything outside this set is ignored during plan_id derivation.
_ACTIVE_PLAN_STATUSES = frozenset({"executing", "reviewed", "draft"})

# Plan file name pattern — `.claude/plans/PLAN-NNN-slug.md` (no subdirs).
_PLAN_FILENAME_RE = re.compile(r"^PLAN-\d{3}-[a-z0-9-]+\.md$")

# ISO-8601 timestamp prefix for a 24h rolling bypass count.
# We use UTC everywhere to dodge DST edges.

# Strict integer literal: 1-8 digits, no leading zero, no sign, no
# scientific notation. Pre-screen the RAW frontmatter substring BEFORE
# Python int() coercion so attacks like ``1e500`` (valid float, would
# otherwise become a python int via int(float(...)) round-trip in some
# parsers) and ``00000100`` (octal-looking) are rejected up front.
# Range 1-99_999_999 covers any realistic cap; combined with the
# ``MAX_TOKENS_CEILING`` post-check this caps at 10M.
_STRICT_INT_RE = re.compile(r"^[1-9][0-9]{0,7}$")


# ---------------------------------------------------------------------------
# Live-quota hint from the statusLine sidecar (PLAN-135 W5 O4) — ADVISORY
# ---------------------------------------------------------------------------
#
# The token-budget cap above counts SUBAGENT-spawn tokens from the audit log.
# It is blind to the operator's real Claude.ai quota (the 5h / weekly rate
# limits) — that lives only in the LIVE statusLine `rate_limits`, captured by
# `.claude/scripts/statusline-ceo.py` into a local sidecar JSON.
#
# This reads that sidecar PURELY to enrich the existing over-cap WARNING with a
# live-quota line ("...and your 5h quota is at Y%"). It is advisory text only:
# it NEVER changes the allow/deny decision, NEVER becomes a cap, and is
# completely fail-soft (any error → empty string). Trust tier is unauthenticated
# local state (PLAN-135 §W5 residual: "same trust tier as other local state;
# integrity posture = follow-up if it ever gates a decision") — which is exactly
# why it only decorates a warning the user already sees, and gates nothing.
#
# Kill-switch: CEO_BUDGET_QUOTA_HINT=0 disables the read entirely.

_STATUSLINE_SIDECAR_SCHEMA = "statusline-sidecar/v1"


def _statusline_sidecar_path() -> Path:
    """Mirror of statusline-ceo._sidecar_path() / audit_emit._audit_dir()."""
    env = os.environ.get("CEO_STATUSLINE_SIDECAR")
    if env:
        return Path(os.path.expanduser(env))
    base = os.environ.get("CEO_AUDIT_LOG_DIR")
    if base:
        return Path(base) / "state" / "statusline-snapshot.json"
    home = os.environ.get("HOME") or str(Path.home())
    return Path(home) / ".claude" / "projects" / "ceo-orchestration" / "state" / "statusline-snapshot.json"


def _statusline_quota_hint() -> str:
    """Fail-soft one-liner summarizing the LIVE rate-limit buckets, or ``""``.

    Reads the statusLine sidecar (schema-checked). Returns e.g.
    ``" Live quota — 5h:24% wk:41%."`` to append to a warning, or ``""`` on
    ANY problem (kill-switch, missing/corrupt/wrong-schema sidecar, no buckets).
    Never raises (ADR-005 fail-open posture)."""
    if os.environ.get("CEO_BUDGET_QUOTA_HINT", "1").strip().lower() in ("0", "false", "no", "off"):
        return ""
    try:
        path = _statusline_sidecar_path()
        with open(path, "r", encoding="utf-8") as fh:
            snap = json.load(fh)
        if not isinstance(snap, dict) or snap.get("schema") != _STATUSLINE_SIDECAR_SCHEMA:
            return ""
        rl = snap.get("rate_limits")
        if not isinstance(rl, dict) or not rl:
            return ""
        bits: List[str] = []
        labels = {"five_hour": "5h", "seven_day": "wk", "agent_sdk": "sdk"}
        for name in sorted(rl):
            b = rl[name]
            if not isinstance(b, dict):
                continue
            pct = b.get("used_pct")
            if isinstance(pct, (int, float)) and not isinstance(pct, bool):
                bits.append("%s:%d%%" % (labels.get(name, str(name)[:4]), round(pct)))
        if not bits:
            return ""
        return " Live quota — %s (advisory, statusLine sidecar)." % " ".join(bits)
    except Exception:
        return ""


# ---------------------------------------------------------------------------
# Plan resolution
# ---------------------------------------------------------------------------


def _plans_dir(project_dir: Path) -> Path:
    return project_dir / ".claude" / "plans"


def _resolve_active_plan(project_dir: Path) -> Tuple[Optional[Path], int]:
    """Return ``(single_active_plan_path_or_None, active_match_count)``.

    Scans ``.claude/plans/PLAN-NNN-<slug>.md`` for files whose
    frontmatter ``status`` is in ``_ACTIVE_PLAN_STATUSES``. A single
    match returns ``(path, 1)``. Zero matches returns ``(None, 0)`` —
    the *normal* maintenance-mode state (all plans terminal). Two or
    more matches returns ``(None, N)`` — genuinely ambiguous.

    The count lets callers distinguish the routine no-active-plan case
    (which must stay silent) from an ambiguous one worth a forensic
    breadcrumb. Missing dir / OSError → ``(None, 0)``.
    """
    pdir = _plans_dir(project_dir)
    if not pdir.is_dir():
        return None, 0

    matches: List[Path] = []
    try:
        for candidate in pdir.iterdir():
            if not candidate.is_file():
                continue
            if not _PLAN_FILENAME_RE.match(candidate.name):
                continue
            try:
                text = candidate.read_text(encoding="utf-8", errors="replace")
            except OSError:
                continue
            fm = _plan_frontmatter.parse_frontmatter(text)
            status = fm.get("status")
            if not isinstance(status, str):
                continue
            if status.strip().lower() not in _ACTIVE_PLAN_STATUSES:
                continue
            plan_id = fm.get("id")
            if isinstance(plan_id, str) and plan_id.startswith("PLAN-"):
                matches.append(candidate)
    except OSError:
        return None, 0

    if len(matches) == 1:
        return matches[0], 1
    return None, len(matches)


def _active_plan_path(project_dir: Path) -> Optional[Path]:
    """Return the single active plan FILE PATH, or None if indeterminate.

    Mirrors ``_active_plan_id`` but returns the on-disk path so callers
    that need to read frontmatter (``max_tokens``) skip a second scan.
    Thin wrapper over :func:`_resolve_active_plan` (drops the count).
    """
    return _resolve_active_plan(project_dir)[0]


def _active_plan_id(project_dir: Path) -> Optional[str]:
    """Return the single active plan_id, or None if indeterminate.

    Scans ``.claude/plans/PLAN-NNN-<slug>.md`` files and reads the
    frontmatter ``id`` + ``status`` via the stdlib-only
    ``plan_frontmatter`` parser. Returns None when zero or >=2 files
    match — the hook then SKIPS the check (logs "indeterminate").
    """
    path = _active_plan_path(project_dir)
    if path is None:
        return None
    try:
        text = path.read_text(encoding="utf-8", errors="replace")
    except OSError:
        return None
    fm = _plan_frontmatter.parse_frontmatter(text)
    plan_id = fm.get("id")
    if isinstance(plan_id, str) and plan_id.startswith("PLAN-"):
        return plan_id.strip()
    return None


# ---------------------------------------------------------------------------
# Plan-frontmatter ``max_tokens`` parsing (PLAN-065 §4.5.D)
# ---------------------------------------------------------------------------


def _parse_plan_max_tokens(plan_path: Path) -> Optional[int]:
    """Return the plan-level ``max_tokens`` cap, or None when absent / invalid.

    Per PLAN-065 §4.5.D + Sec Unseen-5 (YAML safe-load discipline),
    enforced via stdlib-only int-only schema:

    * Accepts: positive integer literal in ``[1, 10_000_000]``
      (e.g. ``max_tokens: 500000``).
    * Rejects (each → breadcrumb + None, NEVER blocks):
        - Quoted strings: ``max_tokens: "500000"``
        - Scientific notation: ``max_tokens: 1e500`` (and ``1e6``)
        - Negative ints: ``max_tokens: -100``
        - Boolean-typed values: ``max_tokens: true``
        - List / dict / null values
        - YAML alias references: ``max_tokens: &anchor 100``
        - Values exceeding the 10M ceiling: ``max_tokens: 50000000``
        - Octal-looking / leading-zero literals: ``max_tokens: 00500000``
        - Whitespace-padded variants that pass int() but fail the
          strict regex (defense-in-depth).

    Implementation note: we parse the FRONTMATTER text twice. First via
    ``_plan_frontmatter.parse_frontmatter`` (existing stdlib-only
    extractor — but it returns raw strings for non-list values, which
    means we still need to int-validate). Then we re-pull the raw
    line for the ``max_tokens`` key so we can detect alias / quote /
    scientific-notation patterns BEFORE the value normalization the
    extractor performs.
    """
    try:
        text = plan_path.read_text(encoding="utf-8", errors="replace")
    except OSError as e:
        _breadcrumb(
            f"max_tokens read failed: {plan_path.name}: "
            f"{type(e).__name__}: {e}"
        )
        return None

    raw_block = _plan_frontmatter.extract_frontmatter_text(text)
    if not raw_block:
        return None

    # Look for the raw `max_tokens:` line BEFORE the extractor's
    # quote-stripping / list-flattening runs. This is where we catch
    # alias references, quoted strings, and scientific notation.
    raw_value = _extract_raw_max_tokens_line(raw_block)
    if raw_value is None:
        # Key absent — silently fall through to env / default.
        return None

    # Reject YAML alias / anchor markers immediately.
    if raw_value.startswith("&") or raw_value.startswith("*"):
        _breadcrumb(
            f"max_tokens: alias/anchor reference rejected in "
            f"{plan_path.name}: {raw_value!r}"
        )
        return None

    # Reject quoted forms (stdlib `int()` would coerce "500000" but
    # PLAN-065 §4.5.D requires int-only schema).
    if (raw_value.startswith('"') and raw_value.endswith('"')) or (
        raw_value.startswith("'") and raw_value.endswith("'")
    ):
        _breadcrumb(
            f"max_tokens: string-typed value rejected in "
            f"{plan_path.name}: {raw_value!r}"
        )
        return None

    # Reject inline-list / mapping shapes.
    if raw_value.startswith("[") or raw_value.startswith("{"):
        _breadcrumb(
            f"max_tokens: non-scalar value rejected in "
            f"{plan_path.name}: {raw_value!r}"
        )
        return None

    # Reject scientific notation, hex, octal, underscores, signs,
    # decimals, and any whitespace via the strict regex. The regex
    # bounds 1-99_999_999; the post-check enforces 10M.
    if not _STRICT_INT_RE.match(raw_value):
        _breadcrumb(
            f"max_tokens: invalid integer literal in "
            f"{plan_path.name}: {raw_value!r}"
        )
        return None

    try:
        value = int(raw_value)
    except (ValueError, TypeError):
        _breadcrumb(
            f"max_tokens: int() coercion failed in "
            f"{plan_path.name}: {raw_value!r}"
        )
        return None

    if value <= 0:
        _breadcrumb(
            f"max_tokens: non-positive rejected in {plan_path.name}: {value}"
        )
        return None

    if value > MAX_TOKENS_CEILING:
        _breadcrumb(
            f"max_tokens: exceeds ceiling ({value} > {MAX_TOKENS_CEILING}) "
            f"in {plan_path.name}"
        )
        return None

    return value


def _extract_raw_max_tokens_line(frontmatter_text: str) -> Optional[str]:
    """Pull the RAW ``max_tokens:`` value substring from the frontmatter.

    Returns the trimmed value as it appears on disk (no quote
    stripping, no type coercion). Returns ``None`` when the key is
    absent or the line does not match a key/value shape.

    We deliberately do NOT use ``_plan_frontmatter.parse_frontmatter``
    here — that helper strips surrounding quotes and flattens lists,
    which would mask the very attacks we want to detect.
    """
    for line in frontmatter_text.split("\n"):
        stripped = line.strip()
        if not stripped or stripped.startswith("#"):
            continue
        if not stripped.startswith("max_tokens"):
            continue
        # Match `max_tokens: <value>`, allowing optional whitespace.
        match = re.match(
            r"^max_tokens\s*:\s*(.*?)\s*$", line
        )
        if not match:
            continue
        return match.group(1)
    return None


# ---------------------------------------------------------------------------
# Cap resolution (PLAN-065 §4.5.D — frontmatter > env > default)
# ---------------------------------------------------------------------------


def _resolve_cap(
    plan_path: Optional[Path],
    *,
    env: Optional[Dict[str, str]] = None,
) -> Tuple[int, str]:
    """Resolve the effective ``max_plan_tokens`` cap with source attribution.

    Returns ``(cap, source)`` where ``source`` is one of:
        - ``"plan_frontmatter"`` — frontmatter ``max_tokens:`` honored.
        - ``"env"`` — ``CEO_MAX_PLAN_TOKENS`` honored.
        - ``"default"`` — fell through to ``DEFAULT_MAX_PLAN_TOKENS``.
    """
    # 1. Plan frontmatter (highest precedence).
    if plan_path is not None:
        try:
            plan_cap = _parse_plan_max_tokens(plan_path)
        except Exception as e:
            _breadcrumb(
                f"max_tokens parse raised: {type(e).__name__}: {e}"
            )
            plan_cap = None
        if plan_cap is not None:
            return (plan_cap, "plan_frontmatter")

    # 2. Env (existing behavior).
    src = env if env is not None else os.environ
    raw = (src.get("CEO_MAX_PLAN_TOKENS") or "").strip()
    if raw:
        try:
            value = int(raw)
            if value >= 0:
                return (value, "env")
        except ValueError:
            pass

    # 3. Default.
    return (DEFAULT_MAX_PLAN_TOKENS, "default")


# ---------------------------------------------------------------------------
# Audit-log rollup
# ---------------------------------------------------------------------------


def _plan_tokens_total(
    plan_id: str,
    *,
    project_dir: str,
) -> Tuple[int, int]:
    """Return ``(total_tokens, spawn_event_count)`` for the plan.

    Scans audit-log ``agent_spawn`` events. ``tokens_total`` is summed
    across events whose ``project`` matches ``project_dir``. Null /
    missing ``tokens_total`` is treated as 0 (ADR-016). Events that do
    not carry a plan_id field (pre-Sprint-11 shape) are included when
    ``project`` matches — a slight over-count in exchange for not
    silently skipping legacy data.

    Fail-open: any exception returns (0, 0).
    """
    try:
        from _lib import audit_emit  # noqa: WPS433 (local import to stay fail-open)
    except Exception:
        return (0, 0)

    total = 0
    count = 0
    try:
        for event in audit_emit.iter_events(action_filter="agent_spawn"):
            try:
                # Plan scoping: when the event carries an explicit plan_id,
                # require match. When it doesn't (legacy), fall back to
                # project match so the rollup still reflects real spend.
                ev_plan = event.get("plan_id")
                if isinstance(ev_plan, str) and ev_plan:
                    if ev_plan != plan_id:
                        continue
                else:
                    ev_project = event.get("project") or ""
                    if project_dir and ev_project != project_dir:
                        continue

                tokens = event.get("tokens_total")
                if tokens is None:
                    continue
                if isinstance(tokens, bool):
                    continue
                if isinstance(tokens, (int, float)) and tokens > 0:
                    total += int(tokens)
                    count += 1
            except Exception:
                # Per-event parse issue — skip, continue tally.
                continue
    except Exception:
        return (total, count)

    return (total, count)


# ---------------------------------------------------------------------------
# Bypass rate limiting
# ---------------------------------------------------------------------------


def _count_recent_bypasses(plan_id: str) -> int:
    """Count ``budget_bypass_used`` events for ``plan_id`` in the last 24h.

    Fail-open: any exception returns 0 (rate limit never blocks on infra).
    """
    try:
        from _lib import audit_emit
    except Exception:
        return 0

    now = datetime.now(timezone.utc)
    count = 0
    try:
        for event in audit_emit.iter_events(action_filter="budget_bypass_used"):
            try:
                if event.get("plan_id") != plan_id:
                    continue
                ts = event.get("ts")
                if not isinstance(ts, str):
                    continue
                # ``ts`` shape: ``YYYY-MM-DDTHH:MM:SSZ`` (see _utc_now_iso).
                # strptime in py3.9 accepts %z with offset; the trailing 'Z'
                # needs translation to '+0000' for portability.
                normalized = ts.replace("Z", "+0000")
                try:
                    parsed = datetime.strptime(
                        normalized, "%Y-%m-%dT%H:%M:%S%z"
                    )
                except ValueError:
                    continue
                delta = now - parsed
                if 0 <= delta.total_seconds() <= 24 * 3600:
                    count += 1
            except Exception:
                continue
    except Exception:
        return count

    return count


# ---------------------------------------------------------------------------
# Env var parsing
# ---------------------------------------------------------------------------


def _env_int(name: str, default: int, *, env: Optional[Dict[str, str]] = None) -> int:
    """Parse a non-negative integer env var with a fallback default."""
    src = env if env is not None else os.environ
    raw = (src.get(name) or "").strip()
    if not raw:
        return default
    try:
        value = int(raw)
        if value < 0:
            return default
        return value
    except ValueError:
        return default


def _is_truthy(name: str, *, env: Optional[Dict[str, str]] = None) -> bool:
    src = env if env is not None else os.environ
    raw = (src.get(name) or "").strip().lower()
    return raw in ("1", "true", "yes", "on")


# ---------------------------------------------------------------------------
# Breadcrumb (local — reuses audit_emit's errors file path)
# ---------------------------------------------------------------------------


def _breadcrumb(message: str) -> None:
    """Write a warning breadcrumb to ``audit-log.errors``. Fail-open."""
    try:
        from _lib import audit_emit  # noqa: WPS433
        # Reuse audit_emit's private helper via public resolution path.
        err = audit_emit._errors_path()  # type: ignore[attr-defined]
        err.parent.mkdir(parents=True, exist_ok=True, mode=0o700)
        ts = datetime.now(timezone.utc).strftime("%Y-%m-%dT%H:%M:%SZ")
        with err.open("a", encoding="utf-8") as f:
            f.write(f"{ts} check_budget: {message}\n")
    except Exception:
        pass


# ---------------------------------------------------------------------------
# Decision
# ---------------------------------------------------------------------------


def decide(
    *,
    plan_id: Optional[str],
    tokens_used: int,
    max_plan_tokens: int,
    bypass_requested: bool,
    recent_bypass_count: int,
    bypass_max_per_day: int,
    caller_pid: int,
    session_id: str,
    project: str,
    cap_source: str = "default",
) -> Tuple[_contract.Decision, Optional[Dict[str, Any]]]:
    """Pure decision function. Returns (decision, side-effect-spec).

    The side-effect-spec is either None (no emits) or a dict describing
    which audit event to write:

        {"emit": "budget_exceeded", "plan_id": ..., "tokens_used": ...,
         "cap": ..., "scope": "plan", "cap_source": ...}
        {"emit": "budget_bypass_used", "plan_id": ..., "caller_pid": ...}
        {"emit": "rate_limit_exceeded", ...}  (breadcrumb-only, no audit)

    In Sprint 11 (State 0) the Decision is ALWAYS allow regardless.
    This isolates the advisory vs. enforcing concern to a single line
    when Sprint 12 flips the contract.

    Args:
        cap_source: provenance of the resolved cap. Forwarded into the
            ``budget_exceeded`` effect dict so audit-tokens can attribute
            caps to plan / env / default per PLAN-065 §4.5.D.
    """
    # No active plan — skip the check entirely.
    if not plan_id:
        return (_contract.allow(), None)

    # Bypass short-circuit — still obeys rate limit.
    if bypass_requested:
        if recent_bypass_count >= bypass_max_per_day:
            # Rate-limit exhausted. State 0 still allows but writes a
            # breadcrumb instead of emitting a bypass_used event (H13:
            # honest accounting of over-quota attempts).
            return (
                _contract.allow(
                    system_message=(
                        f"BUDGET BYPASS RATE LIMIT EXCEEDED: {recent_bypass_count}"
                        f"/{bypass_max_per_day} in the last 24h for plan "
                        f"{plan_id}. Advisory-only (Sprint 11)."
                    )
                ),
                {"emit": "rate_limit_exceeded", "plan_id": plan_id},
            )
        return (
            _contract.allow(
                system_message=(
                    f"BUDGET BYPASS USED for plan {plan_id} "
                    f"({recent_bypass_count + 1}/{bypass_max_per_day} in 24h)."
                )
            ),
            {
                "emit": "budget_bypass_used",
                "plan_id": plan_id,
                "caller_pid": caller_pid,
                "session_id": session_id,
                "project": project,
            },
        )

    # Under cap — quiet allow.
    if tokens_used <= max_plan_tokens:
        return (_contract.allow(), None)

    # Over cap — emit event + WARNING systemMessage, always allow (State 0).
    pct = int((tokens_used / max_plan_tokens) * 100) if max_plan_tokens else 0
    # PLAN-135 W5 O4 — enrich (never gate) the warning with the LIVE rate-limit
    # buckets from the statusLine sidecar. Fail-soft: "" when unavailable.
    quota_hint = _statusline_quota_hint()
    warning = (
        f"BUDGET WARNING: plan {plan_id} at {tokens_used}/{max_plan_tokens} tokens "
        f"({pct}%). Advisory-only (Sprint 11). Set CEO_BUDGET_BYPASS=1 to "
        f"suppress this warning for urgent work. See ADR-033.{quota_hint}"
    )
    return (
        _contract.allow(system_message=warning),
        {
            "emit": "budget_exceeded",
            "plan_id": plan_id,
            "tokens_used": tokens_used,
            "cap": max_plan_tokens,
            "scope": "plan",
            "session_id": session_id,
            "project": project,
            "cap_source": cap_source,
        },
    )


# ---------------------------------------------------------------------------
# Effect emission
# ---------------------------------------------------------------------------


def _apply_effect(effect: Optional[Dict[str, Any]]) -> None:
    """Fire the audit-emit side effect described by ``decide()``. Fail-open."""
    if not effect:
        return
    kind = effect.get("emit")
    if not kind:
        return

    try:
        from _lib import audit_emit
    except Exception:
        _breadcrumb("audit_emit import failed — effect dropped")
        return

    try:
        if kind == "budget_exceeded":
            # Forward cap_source via kwargs when audit_emit accepts it;
            # gracefully degrade to the legacy signature if not (preserves
            # backward compat with un-bumped audit_emit deployments).
            try:
                audit_emit.emit_budget_exceeded(
                    plan_id=effect["plan_id"],
                    spawn_id="",  # plan-scope; spawn-scope reserved for Sprint 12
                    tokens_used=int(effect["tokens_used"]),
                    cap=int(effect["cap"]),
                    scope=str(effect.get("scope", "plan")),
                    session_id=str(effect.get("session_id", "")),
                    project=str(effect.get("project", "")),
                    cap_source=str(effect.get("cap_source", "default")),
                )
            except TypeError:
                # Older audit_emit without cap_source kwarg — fall back.
                audit_emit.emit_budget_exceeded(
                    plan_id=effect["plan_id"],
                    spawn_id="",
                    tokens_used=int(effect["tokens_used"]),
                    cap=int(effect["cap"]),
                    scope=str(effect.get("scope", "plan")),
                    session_id=str(effect.get("session_id", "")),
                    project=str(effect.get("project", "")),
                )
        elif kind == "budget_bypass_used":
            audit_emit.emit_budget_bypass_used(
                plan_id=effect["plan_id"],
                caller_pid=int(effect.get("caller_pid", 0)),
                reason="",  # free-text reason left empty in v1
                session_id=str(effect.get("session_id", "")),
                project=str(effect.get("project", "")),
            )
        elif kind == "rate_limit_exceeded":
            _breadcrumb(
                f"BYPASS RATE LIMIT EXCEEDED plan={effect.get('plan_id', '')}"
            )
    except Exception as e:
        _breadcrumb(f"emit {kind} failed: {type(e).__name__}: {e}")


# ---------------------------------------------------------------------------
# Main entrypoint
# ---------------------------------------------------------------------------


def main() -> int:
    """PreToolUse hook entry point. Fail-open contract.

    ALL paths emit ``allow`` in Sprint 11 (State 0). Returns exit 0.
    """
    try:
        event = _claude_adapter.read_event(phase="PreToolUse")
    except Exception as e:
        _breadcrumb(f"stdin: {type(e).__name__}: {e}")
        _claude_adapter.emit_decision(_contract.allow())
        return 0

    if event.parse_error:
        # Empty or malformed stdin — fail-open.
        _claude_adapter.emit_decision(_contract.allow())
        return 0

    # Apply only to Agent spawns. Unknown tool_name falls through (allow).
    if event.tool_name and event.tool_name not in ("Agent", "unknown"):
        _claude_adapter.emit_decision(_contract.allow())
        return 0

    project_dir_raw = os.environ.get("CLAUDE_PROJECT_DIR") or os.getcwd()
    try:
        project_dir = Path(project_dir_raw).resolve()
    except OSError:
        project_dir = Path(project_dir_raw)

    try:
        plan_path, active_plan_count = _resolve_active_plan(project_dir)
    except Exception as e:
        _breadcrumb(f"plan resolution failed: {type(e).__name__}: {e}")
        plan_path, active_plan_count = None, 0

    plan_id: Optional[str] = None
    if plan_path is not None:
        try:
            text = plan_path.read_text(encoding="utf-8", errors="replace")
            fm = _plan_frontmatter.parse_frontmatter(text)
            pid = fm.get("id")
            if isinstance(pid, str) and pid.startswith("PLAN-"):
                plan_id = pid.strip()
        except Exception as e:
            # This is the count==1 forensic counterpart to the count>=2
            # breadcrumb below: a single resolvable plan whose frontmatter
            # could not be read IS worth logging. Do NOT try to "unify"
            # this with the indeterminate breadcrumb — that would re-flood
            # audit-log.errors for the benign zero-active-plan case.
            _breadcrumb(f"plan_id read failed: {type(e).__name__}: {e}")

    if plan_id is None:
        # Only a genuinely ambiguous resolution (>=2 active plans) earns a
        # forensic breadcrumb. Zero active plans is the normal
        # maintenance-mode state (all plans terminal); breadcrumbing it
        # floods audit-log.errors on every plan-less tool call. Silencing
        # the zero case is the noise-burndown sibling of the
        # mcp_route_advised / tier_policy / output_scan_finding_suppressed
        # cleanups. active_plan_count is a file count (no untrusted echo).
        if active_plan_count >= 2:
            _breadcrumb(
                "indeterminate plan_id — "
                f"{active_plan_count} active plans; skipping budget check"
            )
        _claude_adapter.emit_decision(_contract.allow())
        return 0

    try:
        tokens_used, _ = _plan_tokens_total(
            plan_id, project_dir=str(project_dir)
        )
    except Exception as e:
        _breadcrumb(f"token rollup failed: {type(e).__name__}: {e}")
        tokens_used = 0

    try:
        max_plan_tokens, cap_source = _resolve_cap(plan_path)
    except Exception as e:
        _breadcrumb(f"cap resolution raised: {type(e).__name__}: {e}")
        max_plan_tokens = _env_int(
            "CEO_MAX_PLAN_TOKENS", DEFAULT_MAX_PLAN_TOKENS
        )
        cap_source = "env" if os.environ.get("CEO_MAX_PLAN_TOKENS") else "default"

    bypass_requested = _is_truthy("CEO_BUDGET_BYPASS")
    bypass_max_per_day = _env_int(
        "CEO_BUDGET_BYPASS_MAX_PER_DAY", DEFAULT_BYPASS_MAX_PER_DAY
    )

    try:
        recent_bypasses = _count_recent_bypasses(plan_id)
    except Exception:
        recent_bypasses = 0

    decision, effect = decide(
        plan_id=plan_id,
        tokens_used=tokens_used,
        max_plan_tokens=max_plan_tokens,
        bypass_requested=bypass_requested,
        recent_bypass_count=recent_bypasses,
        bypass_max_per_day=bypass_max_per_day,
        caller_pid=os.getpid(),
        session_id=event.session_id or "",
        project=str(project_dir),
        cap_source=cap_source,
    )

    _apply_effect(effect)
    _claude_adapter.emit_decision(decision)
    return 0


if __name__ == "__main__":
    sys.exit(main())
