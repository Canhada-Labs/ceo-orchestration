#!/usr/bin/env python3
"""UserPromptSubmit lifecycle hook (PLAN-028 / ADR-056).

Fires when the user submits a prompt to Claude, BEFORE the model sees
it. Three responsibilities:

1. **Sensitive-pattern redaction** — scan the prompt via `_lib/redact`
   for API keys / JWTs / bearer tokens / URL-with-creds and emit a
   redaction breadcrumb (does NOT modify the prompt itself;
   framework-level redaction would violate harness opacity).
2. **Prompt-injection smell-test** — advisory scan via
   `_lib/scan_injection` for known vectors (system-reminder forging,
   role-confusion, instruction-nesting, context-escape). Flags are
   audit-emitted; does NOT block.
3. **Emit `prompt_submitted` event** — session_id + prompt_len_bucket
   (not raw prompt) + hash (sha256[:16]) for forensic correlation +
   injection_family_counts.

## Fail-open contract (ADR-005)

Any internal exception → `{"decision":"allow"}`. UserPromptSubmit
never blocks the session — advisory-only at State 0, per-family
FPR data will inform Sprint 29+ decision on promoting any family
to blocking.

## Privacy

The prompt content is NEVER persisted raw. Only:
- `prompt_len_bucket` (≤100 / ≤500 / ≤2000 / ≤8000 / >8000)
- `prompt_sha256[:16]` — per-installation **salted** SHA-256 prefix
  (PLAN-058 Round-23 / ADR-079). Salt loaded from
  `_lib.injection_salt.get_instance_salt()`. An external observer
  with audit-log read access cannot enumerate plausible prompts and
  precompute hashes to identify which prompt was issued. Single-
  instance correlation across time is preserved (salt is stable per
  installation). Cross-instance correlation is impossible by design.
  Fail-open: if salt module fails, hash falls back to unsalted form
  (availability invariant).
- `redact_hits_count` (per-family count, not content)
- `injection_family_counts` (dict of family → hit count)

## Kill-switch

`CEO_EXTENDED_LIFECYCLE=0` disables this hook.
`CEO_PROMPT_INJECTION_SCAN=0` disables only the injection scan
(redaction breadcrumb still emitted).
"""

from __future__ import annotations

import hashlib
import json
import os
import re
import sys
from datetime import datetime, timezone
from pathlib import Path
from typing import Dict, Optional, Tuple

_HOOKS_DIR = Path(__file__).resolve().parent
if str(_HOOKS_DIR) not in sys.path:
    sys.path.insert(0, str(_HOOKS_DIR))

_KILL_SWITCH_ENV = "CEO_EXTENDED_LIFECYCLE"
_SCAN_KILL_SWITCH_ENV = "CEO_PROMPT_INJECTION_SCAN"
_HOOK_VERSION = "1.0.0"


def _emit_observe(system_message: Optional[str] = None) -> str:
    """Schema-compliant lifecycle hook output.

    Per Claude Code hook schema, UserPromptSubmit accepts top-level
    fields: continue, systemMessage, suppressOutput, stopReason,
    decision ("approve"|"block"), and optional hookSpecificOutput
    with {hookEventName, additionalContext}. The `"allow"` value is
    NOT in the enum. Observational hook emits minimal
    {"continue": true, "systemMessage": ...}.
    """
    out: Dict[str, object] = {"continue": True}
    if system_message:
        out["systemMessage"] = system_message
    return json.dumps(out, ensure_ascii=False)


def _emit_with_context(additional_context: str, system_message: Optional[str] = None) -> str:
    """PLAN-122 WS12 — emit with an optimizer recommendation as additionalContext.

    Rides the recommendation into the model/CEO-agent context via the documented
    hookSpecificOutput.additionalContext channel (systemMessage is a user-only
    banner). Schema-compliant; preserves continue=True (never blocks).
    """
    out: Dict[str, object] = {"continue": True}
    if additional_context:
        out["hookSpecificOutput"] = {
            "hookEventName": "UserPromptSubmit",
            "additionalContext": additional_context,
        }
    if system_message:
        out["systemMessage"] = system_message
    return json.dumps(out, ensure_ascii=False)


def _optimizer_recommendation(prompt: str, repo_root: str, session_id: str) -> str:
    """PLAN-122 WS12 — call the non-canonical optimizer recommender (fail-open).

    Lazily puts .claude/scripts on sys.path and imports the recommender. Any
    failure returns '' so the hook's ADR-005 never-blocks contract holds. Passes
    in_hook=True so the recommender skips synchronous RAG sidecar IO.
    """
    try:
        import sys as _sys
        from pathlib import Path as _Path
        scripts_dir = str((_Path(repo_root) / ".claude" / "scripts").resolve())
        if scripts_dir not in _sys.path:
            _sys.path.insert(0, scripts_dir)
        from optimizer import recommender as _rec  # type: ignore[import]
        return _rec.recommend_for_prompt(prompt, _Path(repo_root), session_id=session_id, in_hook=True)
    except Exception:
        return ""


def _kill_switch_active(var: str) -> bool:
    val = os.environ.get(var, "").strip().lower()
    return val in {"0", "false", "off", "no"}


def _prompt_len_bucket(n: int) -> str:
    for cap in (100, 500, 2000, 8000):
        if n <= cap:
            return f"<={cap}"
    return ">8000"


def _count_redact_hits(prompt: str) -> int:
    """Count tokens redacted by `_lib.redact.redact_secrets`, advisory."""
    try:
        from _lib import redact  # type: ignore
        redacted = redact.redact_secrets(prompt)
        # Each redaction inserts a `[redacted-*]` token; count via regex.
        return len(re.findall(r"\[redacted-[a-z0-9_]+\]", redacted))
    except Exception:
        return 0


# PLAN-042 ITEM 2 + ITEM 3 (FINDING-5 retrospective — code-reviewer +
# security-engineer + performance-engineer convergence):
# - context_escape used unbounded `.*` with DOTALL → catastrophic
#   backtracking on 50kB-class adversarial input (`\`\`\`` + "END"
#   repeated without closing fence). Bounded char class `[^`]{0,500}`
#   eliminates the nested-quantifier ambiguity.
# - Pre-compiled via `re.compile()` at module load — consistent with
#   `_lib/output_scan.py` style; eliminates dependency on re's 512-entry
#   LRU cache and makes the cost of _scan_injection deterministic.
_INJECTION_FAMILIES: Dict[str, "re.Pattern[str]"] = {
    "system_reminder_forge": re.compile(r"(?is)<\s*system[-_ ]reminder\b"),
    "role_confusion": re.compile(
        r"(?is)\b(you are (now|actually|really)|pretend (you|to) (are|be))\b"
    ),
    "instruction_nesting": re.compile(
        r"(?is)```[a-z]*\s*\n\s*(ignore|disregard|forget)"
    ),
    "context_escape": re.compile(
        r"(?is)```[^`]{0,500}END[^`]{0,500}```\s*\n\s*\[new instructions\]"
    ),
    "direct_override": re.compile(
        r"(?is)\b(ignore (previous|all|the above)|disregard (previous|all|the above))\b"
    ),
}


def _scan_injection(prompt: str) -> Dict[str, int]:
    """Count matches per family. Returns {family: count}.

    Each pattern is pre-compiled at module load (ITEM 3); we call
    `pattern.findall(prompt)` directly instead of `re.findall(str, prompt)`
    so the call cost does not depend on the re LRU cache size.
    """
    result: Dict[str, int] = {}
    for family, pattern in _INJECTION_FAMILIES.items():
        try:
            result[family] = len(pattern.findall(prompt))
        except Exception:
            result[family] = 0
    return result


def _emit_prompt_submitted(
    *,
    session_id: str,
    prompt_len: int,
    prompt_sha: str,
    redact_hits: int,
    injection_counts: Dict[str, int],
    repo_root: Path,
) -> None:
    """Best-effort audit event. Never raises."""
    try:
        from _lib import audit_emit  # type: ignore
        emitter = getattr(audit_emit, "emit_generic", None)
        if emitter is not None:
            emitter(
                action="prompt_submitted",
                session_id=session_id,
                hook_version=_HOOK_VERSION,
                prompt_len_bucket=_prompt_len_bucket(prompt_len),
                prompt_sha256=prompt_sha,
                redact_hits_count=redact_hits,
                injection_family_counts=injection_counts,
                project=str(repo_root),
            )
    except Exception:
        return


def decide(*, prompt: str, repo_root: Path, session_id: str) -> str:
    """Pure decision function.

    Returns `allow` unconditionally. Side effects: audit emit.
    """
    if _kill_switch_active(_KILL_SWITCH_ENV):
        return _emit_observe(
            system_message="UserPromptSubmit: kill-switch active, no-op"
        )

    try:
        prompt_len = len(prompt)
        # PLAN-058 Round-23 / ADR-079: salt the prompt hash with the
        # per-installation salt to defeat the correlation oracle (any
        # party with audit-log read access could otherwise enumerate
        # plausible prompts and precompute hashes). Fail-open: if the
        # salt module errors, we fall back to the unsalted form so a
        # filesystem failure never breaks UserPromptSubmit emission
        # (availability is invariant; identifier confidentiality is
        # best-effort per ADR-005).
        try:
            from _lib import injection_salt as _salt_mod  # type: ignore
            _salt = _salt_mod.get_instance_salt()
        except Exception:
            _salt = b""
        prompt_sha = hashlib.sha256(
            _salt + prompt.encode("utf-8", errors="replace")
        ).hexdigest()[:16]
        redact_hits = _count_redact_hits(prompt)
        if _kill_switch_active(_SCAN_KILL_SWITCH_ENV):
            injection_counts: Dict[str, int] = {}
        else:
            injection_counts = _scan_injection(prompt)
        total_injection_hits = sum(injection_counts.values())
        _emit_prompt_submitted(
            session_id=session_id,
            prompt_len=prompt_len,
            prompt_sha=prompt_sha,
            redact_hits=redact_hits,
            injection_counts=injection_counts,
            repo_root=repo_root,
        )
        # Advisory banner on redact/injection detection
        banner = None
        if redact_hits > 0 or total_injection_hits > 0:
            banner = (
                f"UserPromptSubmit: advisory — redact_hits={redact_hits}, "
                f"injection_hits={total_injection_hits} (see audit-log)"
            )
        # PLAN-122 WS12 — optimizer recommender (advisory; never blocks). Gated
        # on CEO_OPTIMIZER so a kill-switch OFF skips the import entirely.
        # FAIL-CLOSED: do NOT ride a recommendation into the higher-trust
        # additionalContext channel when the prompt tripped the redact/injection
        # smell-test — that would launder attacker-controlled text past the
        # existing detect-and-advise control (multi-lens review P1).
        rec = ""
        if (redact_hits == 0 and total_injection_hits == 0
                and not _kill_switch_active("CEO_OPTIMIZER")):
            rec = _optimizer_recommendation(prompt, repo_root, session_id)
        if rec:
            return _emit_with_context(additional_context=rec, system_message=banner)
        return _emit_observe(system_message=banner)
    except Exception as e:
        sys.stderr.write(f"[UserPromptSubmit] FATAL: {type(e).__name__}: {e}\n")
        return _emit_observe()


def main() -> int:
    """Hook entry point. Emits schema-compliant UserPromptSubmit output.

    Output shape: `{"continue": true, "systemMessage": "..."}` — no
    `decision` field (UserPromptSubmit schema does NOT accept "allow").
    """
    try:
        from _lib.adapters import claude as _claude_adapter  # noqa: E402
    except Exception:
        sys.stdout.write(_emit_observe() + "\n")
        return 0

    try:
        event = _claude_adapter.read_event(phase="UserPromptSubmit")
    except Exception:
        sys.stdout.write(_emit_observe() + "\n")
        return 0

    # NormalizedEvent exposes the user prompt via `prompt` (populated from
    # tool_input) and the full payload via `raw_payload`. Legacy attempt to
    # read event.user_prompt / event.raw returned empty on NormalizedEvent —
    # fix for retrospective FINDING-2 (code-reviewer + security-engineer P0).
    raw_payload = getattr(event, "raw_payload", {}) or {}
    prompt = (
        getattr(event, "prompt", "")
        or raw_payload.get("prompt", "")
        or raw_payload.get("user_prompt", "")
    ) or ""

    session_id = (
        os.environ.get("CLAUDE_SESSION_ID", "")
        or getattr(event, "session_id", "") or ""
    ) or datetime.now(timezone.utc).strftime("%Y%m%dT%H%M%S")
    repo_root = Path(os.environ.get("CLAUDE_PROJECT_DIR") or os.getcwd())

    try:
        out = decide(prompt=prompt, repo_root=repo_root, session_id=session_id)
    except Exception as e:
        sys.stderr.write(f"[UserPromptSubmit] FATAL: {type(e).__name__}: {e}\n")
        sys.stdout.write(_emit_observe() + "\n")
        return 0

    sys.stdout.write(out + "\n")
    return 0


if __name__ == "__main__":
    sys.exit(main())
