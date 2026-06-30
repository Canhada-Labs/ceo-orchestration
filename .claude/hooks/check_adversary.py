#!/usr/bin/env python3
"""PreToolUse hook (Bash): adversary local-rules deny/ask gate (PLAN-133 E1).

LOCAL-RULES-ONLY — NO model call on the hot path (the rite rejected sync Codex
here: a measured 40×-600× p99 regression vs the ~5ms warm floor; real adversarial
depth lives in the canonical/L3 Codex pair-rail). This hook:

  1. Reads ``.claude/adversary.md`` from INSIDE ``CLAUDE_PROJECT_DIR`` ONLY (never
     env-text), with a hard size cap. A missing/oversize/unreadable ruleset →
     fail-OPEN (allow), no emit beyond a breadcrumb.
  2. Runs ``_lib.adversary_rules.AdversaryEngine`` (deterministic, budgeted).
  3. SECRET FAIL-CLOSED (E1 §4, INDEPENDENT of the .md rules): if a live-credential
     pattern (``_lib.secret_patterns``) matches inside the proposed command, the
     gate DENIES (enforce) / flags (advisory). The command is NEVER transmitted
     anywhere (E1 sends nothing — local-only — so "never transmit" is structural).
  4. Default-OFF: ``CEO_ADVERSARY`` (read from the import-time trusted_env
     snapshot) gates ENFORCEMENT. Unset/≠"1" → advisory (emit, ALLOW). "1" → a
     ``deny`` rule BLOCKS; an ``ask`` rule BLOCKS with an ask-style reason.
  5. Hard per-session call cap (``CEO_ADVERSARY_MAX_PER_SESSION``, default 500):
     beyond the cap the hook short-circuits to allow (bounds the latency tax).
  6. Emits ``adversary_review_flagged`` (closed-enum decision + rule_id +
     rule_class ONLY — no command/value echo) on ANY hit, enforced or advisory.
  7. Infra failure fails OPEN (advisory); a returned deny IS honored.

Promotion-measure (doctrine #1): publish p50/p95/p99 latency + per-session hit
count + the advisory deny/ask mix at /ceo-boot before any default-on flip.
"""

from __future__ import annotations

import os
import sys
from pathlib import Path
from typing import Optional, Tuple

_HOOKS_DIR = Path(__file__).resolve().parent
if str(_HOOKS_DIR) not in sys.path:
    sys.path.insert(0, str(_HOOKS_DIR))

try:
    from _lib.adapters import claude as _claude_adapter
    from _lib import contract as _contract
except Exception:  # pragma: no cover — fail-open if the adapter is unavailable
    _claude_adapter = None  # type: ignore
    _contract = None  # type: ignore

try:
    from _lib import adversary_rules as _rules
except Exception:  # pragma: no cover
    _rules = None  # type: ignore

try:
    from _lib import trusted_env as _trusted_env
except Exception:  # pragma: no cover
    _trusted_env = None  # type: ignore

try:
    from _lib import secret_patterns as _secret_patterns
except Exception:  # pragma: no cover
    _secret_patterns = None  # type: ignore

try:
    from _lib import audit_emit as _audit_emit
except Exception:  # pragma: no cover
    _audit_emit = None  # type: ignore

# Hard size cap on the ruleset file (mirrors adversary_rules.MAX_RULESET_BYTES).
_MAX_RULESET_BYTES = 64 * 1024
_DEFAULT_MAX_PER_SESSION = 500


def _enforce_enabled() -> bool:
    """True iff CEO_ADVERSARY=='1' in the import-time trusted_env snapshot.

    Default-OFF: read from the snapshot (NOT live os.environ) so a late-set value
    can't toggle enforcement mid-op. Pure; never raises.
    """
    if _trusted_env is None or _rules is None:  # pragma: no cover
        return False
    try:
        return (
            _trusted_env.get_trusted(_rules.ADVERSARY_ENFORCE_FLAG) or ""
        ).strip() == "1"
    except Exception:  # pragma: no cover
        return False


def _ruleset_path() -> Optional[Path]:
    """Resolve .claude/adversary.md INSIDE CLAUDE_PROJECT_DIR only (never env-text).

    Returns None (→ fail-OPEN) if the project dir is unset, the resolved path
    escapes the project dir, the file is missing, or it exceeds the size cap.
    """
    proj = os.environ.get("CLAUDE_PROJECT_DIR") or ""
    if not proj:
        return None
    try:
        root = Path(proj).resolve()
        candidate = (root / ".claude" / "adversary.md").resolve()
        # Containment: the resolved path must stay under the project root.
        candidate.relative_to(root)
    except Exception:
        return None
    if not candidate.is_file():
        return None
    try:
        if candidate.stat().st_size > _MAX_RULESET_BYTES:
            return None
    except OSError:
        return None
    return candidate


def _command_carries_secret(command: str) -> bool:
    """True iff a live-credential pattern matches inside the command (E1 §4).

    Fail-OPEN on infra (a scan exception → False, no false block). The canonical
    secret_patterns bank is the source of truth.
    """
    if _secret_patterns is None or not command:
        return False
    try:
        return bool(_secret_patterns.scan(command))
    except Exception:  # pragma: no cover — fail-OPEN
        return False


def _evaluate(command: str) -> Tuple[Optional[str], Optional[str], Optional[str]]:
    """Return (decision, rule_id, rule_class) or (None, None, None).

    decision ∈ {deny, ask, advisory}. Secret-in-command short-circuits to a
    secret-class hit BEFORE the .md rules (highest-credential surface). Pure-ish
    (reads the ruleset file); never raises.
    """
    if _rules is None:
        return (None, None, None)
    enforce = _enforce_enabled()

    # (E1 §4) Secret fail-CLOSED — independent of the .md rules AND independent of
    # CEO_ADVERSARY. A live credential in the command is the highest-severity exfil
    # surface, so it ALWAYS denies (enforce) or asks (advisory-off) — it is NEVER
    # downgraded to a non-blocking "advisory" pass. Only the .md-rule hits below
    # stay gated by CEO_ADVERSARY.
    if _command_carries_secret(command):
        decision = "deny" if enforce else "ask"
        return (decision, "secret_in_command", "exfiltration")

    path = _ruleset_path()
    if path is None:
        return (None, None, None)  # fail-OPEN (no ruleset)
    try:
        text = path.read_text(encoding="utf-8", errors="replace")
    except Exception:
        return (None, None, None)
    try:
        rules = _rules.parse_ruleset(text)
        engine = _rules.AdversaryEngine(rules, enforce=enforce)
        hit = engine.evaluate(command)
    except Exception:  # pragma: no cover — fail-OPEN on engine infra
        return (None, None, None)
    if hit is None:
        return (None, None, None)
    return (hit.decision, hit.rule_id, hit.rule_class)


def _emit(decision: str, rule_class: str, rule_id: str = "") -> None:
    """Emit adversary_review_flagged. Fail-open. Closed-enum decision + class +
    the author-controlled ``rule_id`` MARKER ONLY.

    NEVER the command text, the matched substring, the rule's `match`/`regex`
    source, or any env value. ``rule_id`` is the only free-ish field — for an
    .md-rule hit it is the author-chosen config id; for the secret path it is the
    fixed literal ``"secret_in_command"`` — neither carries command/credential
    bytes. ``rule_id`` is in the audit allowlist, so recording it lets the
    breadcrumb distinguish WHICH rule fired (e.g. a secret_in_command hit vs a
    generic .md deny) without echoing any value.
    """
    if _audit_emit is None:
        return
    try:
        _audit_emit.emit_adversary_review_flagged(
            decision=decision,
            rule_class=rule_class,
            rule_id=rule_id or "",
            session_id=os.environ.get("CLAUDE_SESSION_ID", ""),
            project=os.environ.get("CLAUDE_PROJECT_DIR", ""),
        )
    except Exception:  # pragma: no cover
        pass


def _over_session_cap() -> bool:
    """Best-effort per-session call cap to bound the latency tax. Fail-open."""
    try:
        cap = int(os.environ.get("CEO_ADVERSARY_MAX_PER_SESSION", "") or _DEFAULT_MAX_PER_SESSION)
    except ValueError:
        cap = _DEFAULT_MAX_PER_SESSION
    # The cap is advisory; a process-local counter keeps it cheap. A fresh hook
    # subprocess per op means this is a soft ceiling on the *measured* path only —
    # the real bound is the in-process counter the accel_dispatch host would hold
    # if E1 is later folded there. Here: always under the soft cap (no state file
    # → no I/O on the hot path). Kept as a seam for the measured rollout.
    return False if cap > 0 else True


def main() -> int:
    """PreToolUse(Bash). Fail-open on ANY infra error."""
    if _claude_adapter is None or _contract is None:
        return 0
    try:
        event = _claude_adapter.read_event(phase="PreToolUse")
        if event.parse_error:
            _claude_adapter.emit_decision(_contract.allow())
            return 0
        command = event.command or ""
        if not command and isinstance(event.tool_input, dict):
            command = str(event.tool_input.get("command") or "")
        if not command:
            _claude_adapter.emit_decision(_contract.allow())
            return 0

        # ALWAYS evaluate (the secret-in-command scan is NEVER rate-limited — a
        # live credential must fail-CLOSED even at/over the per-session cap). Only
        # the markdown-RULE path is bounded by the cap below.
        decision, _rule_id, rule_class = _evaluate(command)
        if decision is None:
            _claude_adapter.emit_decision(_contract.allow())
            return 0

        # Per-session cap downgrades ONLY a non-secret (markdown-rule) hit to allow
        # (bounds the latency tax). A secret hit (rule_id == "secret_in_command",
        # the marker _evaluate emits for the credential path) is NEVER downgraded.
        if _rule_id != "secret_in_command" and _over_session_cap():
            _claude_adapter.emit_decision(_contract.allow())
            return 0

        # Emit on ANY hit (enforced OR advisory). Pass the rule_id MARKER so the
        # breadcrumb can distinguish a secret_in_command hit from an .md rule
        # (rule_id is an allowlisted, author-controlled token — never command bytes).
        _emit(decision, rule_class or "other", _rule_id or "")

        if decision == "deny":
            _claude_adapter.emit_decision(_contract.block(
                reason=(
                    "GOVERNANCE (adversary local-rules): this Bash command matched "
                    "a deny rule (or carries a live credential). Review and rewrite; "
                    "if intentional, run it outside Claude Code. "
                    "(Set CEO_ADVERSARY=0 disables enforcement — measure-first.)"
                ),
            ))
            return 0
        if decision == "ask":
            _claude_adapter.emit_decision(_contract.block(
                reason=(
                    "GOVERNANCE (adversary local-rules): this Bash command matched "
                    "an ASK rule and needs explicit confirmation. Re-issue it "
                    "deliberately if you intend to proceed."
                ),
            ))
            return 0
        # advisory (default-OFF) → allow (the emit already fired).
        _claude_adapter.emit_decision(_contract.allow())
        return 0
    except Exception:  # pragma: no cover — fail-OPEN on any infra error
        try:
            _claude_adapter.emit_decision(_contract.allow())
        except Exception:
            pass
        return 0


if __name__ == "__main__":
    sys.exit(main())
