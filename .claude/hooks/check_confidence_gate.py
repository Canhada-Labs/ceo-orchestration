#!/usr/bin/env python3
"""PostToolUse hook: run confidence-gate over Agent spawn output (Sprint 9 C1.1).

PLAN-009 Phase 1. Ships as **advisory-only** scaffold: regardless of the
gate's exit code, this hook returns `decision: allow`. The enforcement
gate (`CEO_CONFIDENCE_ENFORCE=1`) is wired in C1.3 (ADR-019).

## Wire-up

Registered in `.claude/settings.json` PostToolUse Agent (added in C1.4):

    {
      "matcher": "Agent",
      "hooks": [
        {
          "type": "command",
          "command": "bash \"$CLAUDE_PROJECT_DIR/.claude/hooks/_python-hook.sh\" check_confidence_gate.py",
          "timeout": 10,
          "statusMessage": "Running confidence gate..."
        }
      ]
    }

## Decision logic

1. Read PostToolUse Agent payload.
2. Extract agent response text from `tool_response` (Claude adapter
   already normalizes this into `NormalizedEvent.tool_response`).
3. Invoke `confidence_gate.py --stdin --json --agent-name <name>`
   as a subprocess with a 5-second timeout (plan P1.1).
4. Always return `decision: allow` in Sprint 9 C1.1 (advisory).
5. C1.3 adds `CEO_CONFIDENCE_ENFORCE=1` → exit 1 (CLI fail) becomes
   `decision: block` with reason. Bypass hatch `CEO_CONFIDENCE_BYPASS=1`.

## Timeout handling

- Hard 5-second subprocess timeout.
- On timeout: emit `confidence_gate` event with `outcome: "timeout"`,
  record via audit-log, return allow. Fail-open contract (CLAUDE.md).
- Timeout is named at module scope as `_VERIFY_TIMEOUT_SEC=5`.

## Fail-open contract

Per CLAUDE.md §Critical Rules: hooks NEVER block on infrastructure bugs.
Parse errors, missing files, subprocess failures, unexpected exceptions
→ breadcrumb + allow. Enforcement (C1.3) only blocks on *verified* CLI
failure exit code 1 AND env gate on.

Stdlib-only. Python >= 3.9.
"""

from __future__ import annotations

import json
import os
import subprocess
import sys
import time
from pathlib import Path
from typing import Any, Dict, Optional

# Make the local _lib importable
_HOOKS_DIR = Path(__file__).resolve().parent
if str(_HOOKS_DIR) not in sys.path:
    sys.path.insert(0, str(_HOOKS_DIR))

from _lib import contract as _contract  # noqa: E402
from _lib.adapters import claude as _claude_adapter  # noqa: E402

_VERIFY_TIMEOUT_SEC = 5  # Named per plan P1.1

# CLI exit code meanings (confidence_gate.py):
#   0 = at least one claim passed, zero failed
#   1 = at least one claim failed (advisory signal)
#   2 = usage / argument error
#   3 = zero claims found in input
_CLI_EXIT_PASS = 0
_CLI_EXIT_FAIL = 1
_CLI_EXIT_USAGE = 2
_CLI_EXIT_ZERO = 3


def _extract_agent_text(tool_response: Dict[str, Any]) -> str:
    """Pull the Agent's textual response out of Claude Code's tool_response.

    Claude Code sends the Agent's final message text in `tool_response`.
    Shape varies between adapter versions, so we try a handful of common
    keys and fall back to the full JSON blob.
    """
    if not isinstance(tool_response, dict):
        return ""

    for key in ("text", "response", "output", "content"):
        val = tool_response.get(key)
        if isinstance(val, str) and val:
            return val

    content = tool_response.get("content")
    if isinstance(content, list):
        parts = []
        for block in content:
            if isinstance(block, dict):
                t = block.get("text") or block.get("content")
                if isinstance(t, str):
                    parts.append(t)
            elif isinstance(block, str):
                parts.append(block)
        if parts:
            return "\n".join(parts)

    # Empty/unknown shape — no meaningful text to scan
    if not tool_response:
        return ""
    try:
        return json.dumps(tool_response, ensure_ascii=False)
    except (TypeError, ValueError):
        return ""


def _run_gate_cli(
    text: str,
    *,
    agent_name: str,
    repo_root: Path,
    timeout_sec: int = _VERIFY_TIMEOUT_SEC,
) -> Optional[Dict[str, Any]]:
    """Invoke `confidence_gate.py --stdin --json` and return parsed output.

    Returns a dict with at least `outcome` and `exit_code`. `outcome` is
    one of `"verified"` (CLI ran to completion), `"timeout"` (subprocess
    hit timeout_sec), or infra error → returns None so caller can emit
    a timeout-ish breadcrumb event.
    """
    cli = repo_root / ".claude" / "scripts" / "confidence_gate.py"
    if not cli.is_file():
        return None

    # `--no-emit` here because the hook emits its own audit event with
    # more context (agent_name, session_id); avoid duplicate events.
    argv = [
        sys.executable,
        str(cli),
        "--stdin",
        "--json",
        "--no-emit",
        "--agent-name",
        agent_name,
        "--repo-root",
        str(repo_root),
    ]
    try:
        result = subprocess.run(
            argv,
            input=text,
            capture_output=True,
            text=True,
            timeout=timeout_sec,
        )
    except subprocess.TimeoutExpired:
        return {"outcome": "timeout", "exit_code": None}
    except (OSError, ValueError):
        return None

    try:
        payload = json.loads(result.stdout)
    except (json.JSONDecodeError, ValueError):
        return None

    payload["exit_code"] = result.returncode
    payload["outcome"] = "verified"
    return payload


def _emit_event(
    *,
    payload: Optional[Dict[str, Any]],
    agent_name: str,
    session_id: str,
    project: str,
    duration_ms: int,
    outcome: str,
) -> None:
    """Best-effort emit of confidence_gate audit event. Never raises."""
    try:
        from _lib import audit_emit
    except ImportError:
        return

    if payload is None:
        try:
            audit_emit.emit_confidence_gate(
                claim_count=0,
                pass_count=0,
                fail_count=0,
                verifier_kind_counts={},
                agent_name=agent_name,
                source="post_tool_use",
                session_id=session_id,
                project=project,
                raw_claim_count=0,
                truncated=False,
            )
        except Exception:
            pass
        return

    try:
        audit_emit.emit_confidence_gate(
            claim_count=int(payload.get("claim_count", 0)),
            pass_count=int(payload.get("pass_count", 0)),
            fail_count=int(payload.get("fail_count", 0)),
            verifier_kind_counts=dict(payload.get("verifier_kind_counts") or {}),
            agent_name=agent_name,
            source="post_tool_use",
            session_id=session_id,
            project=project,
            raw_claim_count=int(
                payload.get("raw_claim_count", payload.get("claim_count", 0))
            ),
            truncated=bool(payload.get("truncated", False)),
        )
    except Exception:
        pass

    # PLAN-090-FOLLOWUP Wave B.3 — per-claim event pair (advisory; gated by kill-switch).
    # Codex iter-1 P0-1 + P0-2 + code-reviewer P1 + security P1-C folds:
    #   - verdict default "fail" (NOT "refuted"; refuted is FP signal in backfill)
    #   - kind_supported passed to BOTH emit calls (Wave A signatures require it)
    #   - kill-switch CEO_CONFIDENCE_GATE_PRODUCER_PAIR_DISABLED reverts byte-identical
    #   - exception types specific (KeyError/TypeError/ValueError) + breadcrumb
    #   - agent_name/source clipped at the hook layer (defense-in-depth re-clip
    #     also happens in emit_generic per Wave A.6)
    if os.environ.get("CEO_CONFIDENCE_GATE_PRODUCER_PAIR_DISABLED", "0") == "1":
        return
    _agent_name_clipped = str(agent_name)[:64]
    _source_clipped = "post_tool_use"  # static; not caller-controlled
    for c in (payload.get("claims") or []):
        try:
            audit_emit.emit_claim_emitted(
                claim_id=str(c.get("claim_id", "")),
                claim_type=str(c.get("claim_type", "unknown")),
                severity=str(c.get("severity", "info")),
                verifier_kind=str(c.get("verifier_kind", "")),
                payload_hash=str(c.get("payload_hash", "")),
                kind_supported=bool(c.get("kind_supported", True)),
                line_num=int(c.get("line_num", 0)),
                agent_name=_agent_name_clipped,
                source=_source_clipped,
                session_id=session_id,
                project=project,
            )
            # Security iter-1 P1-B fold — use raw verifier_outcome +
            # claim_args overlap input via the audit_emit helper
            # (transient fields are NOT persisted).
            from _lib.audit_emit import _safe_verifier_outcome as _svo
            _outcome_redacted = _svo(
                str(c.get("verifier_outcome_raw", "")),
                str(c.get("claim_args_for_overlap_check", "")),
            )
            audit_emit.emit_confidence_gate_verdict(
                claim_id=str(c.get("claim_id", "")),
                verdict=str(c.get("verdict", "fail")),
                was_false_positive=bool(c.get("was_false_positive", False)),
                kind_supported=bool(c.get("kind_supported", True)),
                verifier_kind=str(c.get("verifier_kind", "")),
                verifier_outcome=_outcome_redacted,
                agent_name=_agent_name_clipped,
                source=_source_clipped,
                session_id=session_id,
                project=project,
            )
        except (KeyError, TypeError, ValueError) as e:
            # Specific catches per code-reviewer iter-1 P1 fold —
            # broad Exception swallowed real bugs. Breadcrumb on swallow
            # so the failure is forensic-visible without breaking the loop.
            try:
                from _lib import audit_emit as _ae
                _ae._breadcrumb(  # type: ignore[attr-defined]
                    f"claim-producer skip: {type(e).__name__}: {str(e)[:64]}"
                )
            except Exception:
                pass
            continue


def decide(
    *,
    payload: Optional[Dict[str, Any]],
    enforce: bool,
    bypass: bool,
    class_tiers: Optional[Dict[str, str]] = None,
) -> _contract.Decision:
    """Pure decision function — ADR-019-AMEND-1 per-class block-mode.

    Hook exit-code translation table (ADR-019, refined ADR-019-AMEND-1):

        CLI exit | ENFORCE | TIER CONFIG | HIGH_BLOCK class failed? | Hook decision
        ---------|---------|-------------|--------------------------|--------------
        0        | any     | any         | n/a                       | allow
        1        | 0       | any         | n/a                       | allow (advisory)
        1        | 1       | empty       | n/a                       | allow (fail-OPEN; pre-ADR-019-AMEND-1 broad semantic suspended)
        1        | 1       | present     | yes (+ no kill-switch)    | block + reason
        1        | 1       | present     | no                        | allow
        2 / 3    | any     | any         | n/a                       | allow

    Per-class kill-switch: `CEO_CONFIDENCE_BLOCK_<CLASS>=0` (EXACT match).
    Bypass-all hatch: `CEO_CONFIDENCE_BYPASS=1` (session-scoped).
    """
    if bypass:
        return _contract.allow()

    if payload is None:
        return _contract.allow()

    if payload.get("outcome") == "timeout":
        return _contract.allow()

    exit_code = payload.get("exit_code")

    if exit_code in (_CLI_EXIT_PASS, _CLI_EXIT_USAGE, _CLI_EXIT_ZERO):
        return _contract.allow()

    if exit_code == _CLI_EXIT_FAIL:
        if not enforce:
            return _contract.allow()

        # PLAN-100 ADR-019-AMEND-1 per-class block-mode.
        tiers = class_tiers or {}

        if not tiers:
            # Fail-OPEN per CLAUDE.md §Critical Rules. The legacy ADR-019
            # broad-enforcement path is INTENTIONALLY suspended when tier
            # config is missing: the safer default during a missing-config
            # window is advisory mode, not blocking sessions on the
            # last-known broad policy.
            return _contract.allow()

        blocking = _classify_blocking_claims(payload, tiers)
        if not blocking:
            return _contract.allow()

        return _contract.block(
            reason=(
                f"CONFIDENCE-GATE-BLOCKED [per-class]: HIGH_CONFIDENCE_BLOCK "
                f"claim(s) failed verification: {blocking}. "
                "Per ADR-019-AMEND-1. To unblock: set "
                "CEO_CONFIDENCE_BLOCK_<CLASS>=0 for the specific class, "
                "CEO_CONFIDENCE_ENFORCE=0 to revert to advisory mode, OR "
                "CEO_CONFIDENCE_BYPASS=1 for a single wedged session."
            )
        )

    return _contract.allow()


def _is_truthy_env(name: str) -> bool:
    """Env var is set to a truthy value (1 / true / yes / on)."""
    raw = os.environ.get(name, "").strip().lower()
    return raw in ("1", "true", "yes", "on")


# ---------------------------------------------------------------------------
# PLAN-100 Wave B — per-class block-mode (ADR-019-AMEND-1 PROPOSED).
# Tier name constants pinned against ADR-019-AMEND-1 §2 enum.
# ---------------------------------------------------------------------------

_TIER_HIGH_BLOCK = "HIGH_CONFIDENCE_BLOCK"
_TIER_MED_ADV = "MED_CONFIDENCE_ADVISORY"
_TIER_LOW_ADV = "LOW_CONFIDENCE_ADVISORY"
_VALID_TIERS = frozenset({_TIER_HIGH_BLOCK, _TIER_MED_ADV, _TIER_LOW_ADV})


def _load_class_tiers(repo_root: Path) -> Dict[str, str]:
    """Load per-class tier config. Fail-OPEN on missing/malformed.

    Returns dict mapping `claim_kind` -> tier string (one of _VALID_TIERS).
    Unknown classes are silently dropped (defense-in-depth).

    Per ADR-019-AMEND-1 §2 + CLAUDE.md §Critical Rules fail-open contract.
    """
    config_path = repo_root / ".claude" / "data" / "confidence-gate-class-tiers.json"
    try:
        if not config_path.is_file():
            return {}
        with open(config_path, "rb") as f:
            raw = f.read().decode("utf-8", errors="replace")
        data = json.loads(raw)
    except (OSError, json.JSONDecodeError, ValueError, UnicodeError):
        return {}
    tiers_raw = data.get("tiers") if isinstance(data, dict) else None
    if not isinstance(tiers_raw, dict):
        return {}
    out: Dict[str, str] = {}
    for k, v in tiers_raw.items():
        if not isinstance(k, str) or not isinstance(v, str):
            continue
        if v in _VALID_TIERS:
            out[k] = v
    return out


def _is_class_killed(class_name: str) -> bool:
    """EXACT-match per-class kill-switch lookup.

    `CEO_CONFIDENCE_BLOCK_<UPPERCASE_CLASS>=0` disables block for that class.
    `CEO_CONFIDENCE_BLOCK=0` (no `_<CLASS>` suffix) is IGNORED per
    ADR-019-AMEND-1 §3 partial-match non-interference.

    Truthy off-signals: "0", "false", "no", "off", "" (absent).
    """
    if not class_name:
        return False
    env_name = f"CEO_CONFIDENCE_BLOCK_{class_name.upper()}"
    raw = os.environ.get(env_name, "").strip().lower()
    return raw in ("0", "false", "no", "off")


def _classify_blocking_claims(
    payload: Dict[str, Any],
    class_tiers: Dict[str, str],
) -> List[str]:
    """Return list of claim_kinds that should trigger a block.

    A claim triggers block iff:
    - verdict == "fail"
    - verifier_kind (or claim_type fallback) is in HIGH_CONFIDENCE_BLOCK tier
    - per-class kill-switch is NOT set

    Returns the list of distinct blocking class names (sorted, deduped).
    Empty list = no block.
    """
    seen: List[str] = []
    for claim in (payload.get("claims") or []):
        if not isinstance(claim, dict):
            continue
        verdict = claim.get("verdict")
        if verdict != "fail":
            continue
        cls = claim.get("verifier_kind") or claim.get("claim_type") or ""
        if not isinstance(cls, str) or not cls:
            continue
        tier = class_tiers.get(cls, "")
        if tier != _TIER_HIGH_BLOCK:
            continue
        if _is_class_killed(cls):
            continue
        if cls not in seen:
            seen.append(cls)
    return sorted(seen)



def main() -> int:
    """PostToolUse hook entry point.

    Fail-open contract: the hook NEVER returns non-zero; decisions are
    serialized to stdout via the adapter. Exceptions are swallowed with
    a breadcrumb (stderr) and become `allow`.
    """
    t0 = time.monotonic()
    try:
        event = _claude_adapter.read_post_event()
    except Exception as e:
        sys.stderr.write(f"[check_confidence_gate] stdin: {type(e).__name__}: {e}\n")
        _claude_adapter.emit_decision(_contract.allow())
        return 0

    if event.parse_error:
        _claude_adapter.emit_decision(_contract.allow())
        return 0

    if event.tool_name and event.tool_name not in ("Agent", "unknown"):
        _claude_adapter.emit_decision(_contract.allow())
        return 0

    repo_root = Path(os.environ.get("CLAUDE_PROJECT_DIR") or os.getcwd())
    try:
        repo_root = repo_root.resolve()
    except OSError:
        pass

    agent_name = event.subagent_type or ""
    session_id = event.session_id or ""
    project = str(repo_root)

    agent_text = _extract_agent_text(event.tool_response or {})
    if not agent_text:
        _claude_adapter.emit_decision(_contract.allow())
        return 0

    gate_result = _run_gate_cli(
        agent_text,
        agent_name=agent_name,
        repo_root=repo_root,
    )

    duration_ms = int((time.monotonic() - t0) * 1000)
    outcome = (gate_result or {}).get("outcome", "error")
    _emit_event(
        payload=gate_result,
        agent_name=agent_name,
        session_id=session_id,
        project=project,
        duration_ms=duration_ms,
        outcome=outcome,
    )

    enforce = _is_truthy_env("CEO_CONFIDENCE_ENFORCE")
    bypass = _is_truthy_env("CEO_CONFIDENCE_BYPASS")

    # PLAN-100 Wave B — load per-class tiers (fail-OPEN on missing config).
    class_tiers = _load_class_tiers(repo_root)
    decision = decide(
        payload=gate_result,
        enforce=enforce,
        bypass=bypass,
        class_tiers=class_tiers,
    )

    # PLAN-100 Wave B — emit confidence_gate_blocked when block decision fires.
    # Specific exception catch (no broad swallow) + breadcrumb on swallow.
    if not getattr(decision, "allow", True):
        try:
            from _lib import audit_emit as _ae  # type: ignore[import]
            _blocking = _classify_blocking_claims(gate_result or {}, class_tiers)
            _ae.emit_confidence_gate_blocked(
                blocking_classes=_blocking,
                fail_count=int((gate_result or {}).get("fail_count", 0)),
                agent_name=agent_name,
                source="post_tool_use",
                session_id=session_id,
                project=project,
            )
        except (ImportError, AttributeError, KeyError, TypeError, ValueError) as _e:
            sys.stderr.write(
                f"[check_confidence_gate] emit_confidence_gate_blocked skipped: "
                f"{type(_e).__name__}: {str(_e)[:64]}\n"
            )

    _claude_adapter.emit_decision(decision)
    return 0


if __name__ == "__main__":
    sys.exit(main())
