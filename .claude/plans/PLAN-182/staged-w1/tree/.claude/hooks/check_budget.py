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
   for files whose frontmatter ``status`` is one of the "active"
   states (``executing``, ``reviewed``, ``draft``). Zero matches →
   skip check (normal maintenance mode). One match → that plan.
   Two or more (PLAN-178 Lote B cure — the old "indeterminate → skip"
   made the cap INERT for any multi-plan cycle, which is the NORMAL
   state of an OQ-6-style scope): deterministic tie-break — highest
   status tier (``executing`` > ``reviewed`` > ``draft``), then the
   HIGHEST plan number within the tier (the most recently authored
   plan is the one being burned against). The selection is surfaced
   in a forensic breadcrumb, never hidden.
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
| ``CEO_STATUSLINE_SIDECAR``       | unset     | PLAN-135 W5 O4: full-path override of the statusLine sidecar read for the quota hint (else ``<CEO_AUDIT_LOG_DIR or ~/.claude/projects/<native-slug>>/state/statusline-snapshot.json``). |

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
try:
    from _lib import runtime_paths as _rp  # noqa: E402  # PLAN-182 W1 single resolver
except Exception:  # pragma: no cover — partial upgrade: hook stays FAIL-OPEN (rail r1 P1-4)
    _rp = None  # type: ignore[assignment]


def _rp_state_dir():
    """Resolver com fallback de partial-upgrade (arquivo novo ausente).

    Fail-open: o hook NUNCA crasha por falta do resolvedor; degrada ao
    comportamento legado com aviso em stderr.
    """
    if _rp is not None:
        return _rp.runtime_state_dir()
    import sys as _s
    _s.stderr.write("# hook: _lib/runtime_paths ausente — fallback legado (partial upgrade)\n")
    from pathlib import Path as _P
    import os as _o
    _h = _o.environ.get("HOME") or str(_P.home())
    return _P(_h) / ".claude" / "projects" / "ceo-orchestration"  # rp-allow: partial-upgrade-fallback


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
    return _rp_state_dir() / "state" / "statusline-snapshot.json"


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


# PLAN-178 Lote B — tie-break tiers for the multi-active-plan cure. Lower
# rank wins. ``executing`` outranks ``reviewed`` outranks ``draft``: a plan
# actually being executed is the one whose budget the session burns.
_STATUS_TIER_RANK = {"executing": 0, "reviewed": 1, "draft": 2}


def _plan_seq(path: Path) -> int:
    """Numeric NNN from ``PLAN-NNN-<slug>.md``. 0 when unparseable (never
    raises; unparseable names lose every tie-break, deterministically)."""
    m = _PLAN_FILENAME_RE.match(path.name)
    if not m:
        return 0
    digits = ""
    for ch in path.name[len("PLAN-"):]:
        if ch.isdigit():
            digits += ch
        else:
            break
    try:
        return int(digits) if digits else 0
    except ValueError:
        return 0


def _resolve_active_plan(project_dir: Path) -> Tuple[Optional[Path], int]:
    """Return ``(selected_active_plan_path_or_None, active_match_count)``.

    Scans ``.claude/plans/PLAN-NNN-<slug>.md`` for files whose
    frontmatter ``status`` is in ``_ACTIVE_PLAN_STATUSES``. Zero matches
    returns ``(None, 0)`` — the *normal* maintenance-mode state (all
    plans terminal). One match returns ``(path, 1)``.

    Two or more matches (PLAN-178 Lote B cure): the OLD behavior
    returned ``(None, N)`` — "genuinely ambiguous", skip the check.
    That made the budget cap INERT in exactly the state where burn is
    highest (a multi-plan cycle: the S307 census found 12 active plans
    and therefore ZERO budget checks since the cycle opened). The cure
    is a DETERMINISTIC tie-break, not a guess: highest status tier
    (``executing`` > ``reviewed`` > ``draft``), then highest plan
    number NNN within the tier (the most recently authored plan is the
    one being burned against). Filename NNN — never mtime — so the
    selection is stable across filesystems and reinstalls. The count
    N is still returned so the caller surfaces the multi-plan state in
    a forensic breadcrumb (selection is visible, never silent).

    Missing dir / OSError → ``(None, 0)``.
    """
    pdir = _plans_dir(project_dir)
    if not pdir.is_dir():
        return None, 0

    matches: List[Tuple[int, int, Path]] = []
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
            status_norm = status.strip().lower()
            if status_norm not in _ACTIVE_PLAN_STATUSES:
                continue
            plan_id = fm.get("id")
            if isinstance(plan_id, str) and plan_id.startswith("PLAN-"):
                matches.append((
                    _STATUS_TIER_RANK.get(status_norm, 99),
                    -_plan_seq(candidate),
                    candidate.name,
                    candidate,
                ))
    except OSError:
        return None, 0

    if not matches:
        return None, 0
    # sort key: (tier rank ASC, -NNN ASC, filename ASC). The filename
    # tertiary key (codex r24 P2) covers same-tier same-NNN pairs like
    # PLAN-156 + PLAN-156-FOLLOWUP — without it the winner depended on
    # filesystem iterdir() order and varied between checkouts.
    matches.sort(key=lambda t: (t[0], t[1], t[2]))
    return matches[0][3], len(matches)


def _active_plan_path(project_dir: Path) -> Optional[Path]:
    """Return the selected active plan FILE PATH, or None when no plan
    is active (multi-plan states now tie-break deterministically —
    PLAN-178 Lote B — instead of collapsing to None).

    Mirrors ``_active_plan_id`` but returns the on-disk path so callers
    that need to read frontmatter (``max_tokens``) skip a second scan.
    Thin wrapper over :func:`_resolve_active_plan` (drops the count).
    """
    return _resolve_active_plan(project_dir)[0]


def _active_plan_id(project_dir: Path) -> Optional[str]:
    """Return the selected active plan_id, or None when no plan is
    active. >=2 active plans tie-break deterministically (PLAN-178
    Lote B) — the check RUNS against the selected plan instead of
    silently skipping (the old "indeterminate" behavior that left the
    cap inert across every multi-plan cycle).
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
    strict_attribution: bool = False,
) -> Tuple[int, int]:
    """Return ``(total_tokens, spawn_event_count)`` for the plan.

    Scans audit-log ``agent_spawn`` events. ``tokens_total`` is summed
    across events whose ``project`` matches ``project_dir``. Null /
    missing ``tokens_total`` is treated as 0 (ADR-016). Events that do
    not carry a plan_id field (pre-Sprint-11 shape) are included when
    ``project`` matches — a slight over-count in exchange for not
    silently skipping legacy data.

    ``strict_attribution=True`` (PLAN-178 Lote B, codex r9 P2 — the
    multi-plan companion of the tie-break cure): ONLY events carrying
    an explicit matching ``plan_id`` count; the legacy project-wide
    fallback is OFF. With >=2 active plans the fallback would charge
    the SELECTED plan for every other plan's spend plus prior history —
    a false budget_exceeded machine. Under-count is the honest
    direction for an advisory warning.

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
                elif strict_attribution:
                    # Multi-plan mode: unattributed rows never charge the
                    # selected plan (see docstring).
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
    spend_basis: str = "plan",
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
    if bypass_requested and spend_basis != "plan":
        # Codex r13 P2: with >=2 active plans the tie-break plan_id is an
        # arbitrary attribution target — a plan-scoped budget_bypass_used
        # event AND its per-plan 24h quota would both be misattributed
        # (spawn rows carry no plan_id yet). Advisory State 0: allow with
        # a declared-basis message + forensic breadcrumb; the per-plan
        # quota is NOT consumed (it belongs to no provable plan).
        return (
            _contract.allow(
                system_message=(
                    f"BUDGET BYPASS (multi-plan state) noted for selected "
                    f"plan {plan_id}. Spend basis: PROJECT-WIDE — no "
                    "plan-scope bypass event emitted; per-plan quota not "
                    "consumed (attribution pending the producer cure)."
                )
            ),
            {
                "emit": "breadcrumb_only",
                "message": (
                    f"multi-plan budget bypass: CEO_BUDGET_BYPASS=1 with "
                    f">=2 active plans (tie-break selection {plan_id}); "
                    "no plan-scope budget_bypass_used event emitted"
                ),
            },
        )
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
    basis_note = (
        " Spend basis: PROJECT-WIDE (multi-plan state; agent_spawn rows "
        "carry no plan_id yet — per-plan attribution lands with the "
        "producer cure, PLAN-178 record)." if spend_basis == "project-wide"
        else ""
    )
    warning = (
        f"BUDGET WARNING: plan {plan_id} at {tokens_used}/{max_plan_tokens} tokens "
        f"({pct}%).{basis_note} Advisory-only (Sprint 11). Set "
        f"CEO_BUDGET_BYPASS=1 to suppress this warning for urgent work. "
        f"See ADR-033.{quota_hint}"
    )
    if spend_basis != "plan":
        # Codex r11+r12 P2 (closed together): the multi-plan rollup is
        # PROJECT-wide spend vs ONE plan's cap. Emitting budget_exceeded
        # with scope="plan" would corrupt calibration telemetry, and
        # scope="project" is OUTSIDE the published audit-log schema enum
        # (spawn|plan; SPEC is deny-Edit here). So: the operator KEEPS the
        # systemMessage warning (with the declared basis), and the audit
        # trail gets a forensic BREADCRUMB instead of an off-contract
        # event — calibration telemetry stays clean plan-scope only.
        return (
            _contract.allow(system_message=warning),
            {
                "emit": "breadcrumb_only",
                "message": (
                    f"multi-plan budget advisory: project-wide spend "
                    f"{tokens_used} exceeds selected plan {plan_id} cap "
                    f"{max_plan_tokens} (cap_source={cap_source}); no "
                    "plan-scope budget_exceeded event emitted (schema enum "
                    "spawn|plan; per-plan attribution pending the producer "
                    "cure)"
                ),
            },
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
    if kind == "breadcrumb_only":
        # Multi-plan advisory (codex r12 P2): forensic trail without an
        # off-schema audit event.
        _breadcrumb(str(effect.get("message") or "breadcrumb_only"))
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
        # plan_id can only be None here with zero active plans (normal
        # maintenance mode — stay silent; breadcrumbing it floods
        # audit-log.errors on every plan-less tool call) or when the
        # SELECTED plan file failed to yield a frontmatter id (already
        # breadcrumbed above). The old ">=2 → indeterminate → skip"
        # branch is gone (PLAN-178 Lote B): multi-plan states tie-break
        # deterministically in _resolve_active_plan and the check RUNS.
        _claude_adapter.emit_decision(_contract.allow())
        return 0

    if active_plan_count >= 2:
        # Forensic visibility of the tie-break (never silent, never a
        # skip): file counts + the selected id only — no untrusted echo.
        _breadcrumb(
            f"{active_plan_count} active plans; budget check runs against "
            f"tie-break selection {plan_id} (tier executing>reviewed>draft, "
            "then highest NNN)"
        )

    try:
        # Design decision (closes the codex r9<->r10 oscillation): the live
        # agent_spawn producer (audit_log.py) emits NO plan_id, so strict
        # per-plan attribution today matches ZERO rows and re-inerts the
        # cap (r10 P1) — while the project-wide fallback over-counts the
        # selected plan (r9 P2). For an ADVISORY warning (State 0, never
        # blocks) over-counting with a DECLARED basis is the honest side:
        # the warning below names spend_basis=project-wide in multi-plan
        # states. strict_attribution stays available + tested as the
        # contract for the producer cure (plan_id on agent_spawn rows —
        # registered destination: v1.4.0 train, PLAN-178 record).
        tokens_used, _ = _plan_tokens_total(
            plan_id, project_dir=str(project_dir)
        )
    except Exception as e:
        _breadcrumb(f"token rollup failed: {type(e).__name__}: {e}")
        tokens_used = 0
    spend_basis = "project-wide" if active_plan_count >= 2 else "plan"

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
        spend_basis=spend_basis,
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
