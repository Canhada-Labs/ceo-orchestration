#!/usr/bin/env python3
"""PreToolUse hook: HARD-DENY edits to the arbitration kernel.

PLAN-019 P1-SEC-A (Phase 2 Wave 2A). Defense-in-depth on top of
`check_canonical_edit.py`. The canonical-edit sentinel is the first
line — it allows Owner-signed `approved.md` to unlock any canonical
governance path. But the arbiter of that sentinel (the hook source
itself, plus the _lib modules it imports, plus the policies YAML it
consumes) must NOT be sentinel-unlockable: an agent that can edit the
arbitration hook can remove itself from the guard list and then edit
anything.

## What's in the kernel (HARD-DENY list)

1. **The four governance hooks** — check_agent_spawn.py,
   check_canonical_edit.py, check_plan_edit.py, check_arbitration_kernel.py.
2. **Hook shared library primitives** — _lib/policy.py, _lib/redact.py,
   _lib/audit_emit.py, _lib/contract.py (neutral Event/Decision), the
   Claude adapter, and the PII pattern bank.
3. **Policy-as-code files** — .claude/policies/*.yaml + corresponding
   .jsonl fixtures (these drive policy_dispatch.py decisions).

Each is matched via a dedicated glob in `_KERNEL_PATHS` below.

## Escape hatch (Owner-only)

If the Owner must edit a kernel path (e.g. an ADR-approved refactor of
the policy engine), they set BOTH of these env vars in the same shell
session:

    export CEO_KERNEL_OVERRIDE="<reason-slug>"   # e.g. ADR-045-refactor
    export CEO_KERNEL_OVERRIDE_ACK="I-ACCEPT"

The hook then allows the edit and emits a `veto_triggered` audit event
with `reason_code=kernel_override_used` so the override is traceable.
Absent BOTH env vars, the edit is blocked regardless of any sentinel.

This is stricter than sentinel gating on purpose: a spawned sub-agent
cannot set env vars in the parent Claude process, so the ACK token
cannot be forged by an agent spawn.

## Fail-closed contract

UNLIKE the sentinel hook, this hook is **fail-closed** on any
observable internal error path (parse_error, unparseable payload):
if the hook cannot determine whether the path is a kernel file, it
treats it as potentially-kernel and blocks with a synthetic reason.
The only exception is a catastrophic Python exception (e.g. ImportError
on the adapter itself) — that still emits allow, because the sandbox
cannot function at all if the adapter is broken (you cannot recover
from a broken hook runtime via a blocking hook that depends on it).

Tests verify the fail-closed posture (block on missing file_path when
the tool is Edit|Write|MultiEdit).
"""

from __future__ import annotations

import fnmatch
import json
import os
import re
import sys
from pathlib import Path
from typing import List, Optional

_HOOKS_DIR = Path(__file__).resolve().parent
if str(_HOOKS_DIR) not in sys.path:
    sys.path.insert(0, str(_HOOKS_DIR))


# Arbitration kernel — full governance-enforcement surface.
# Each pattern uses the same segment-glob rules as _CANONICAL_GUARDS in
# check_canonical_edit.py: `*` matches a single segment, `**` matches
# zero or more segments. See _fnmatch_segments below.
_KERNEL_PATHS: List[str] = [
    # The four governance hooks (edit-gating surface).
    ".claude/hooks/check_agent_spawn.py",
    ".claude/hooks/check_canonical_edit.py",
    ".claude/hooks/check_plan_edit.py",
    ".claude/hooks/check_arbitration_kernel.py",
    # Skill-patch sentinel — same tier of power as the canonical guard.
    ".claude/hooks/check_skill_patch_sentinel.py",
    # Hook library primitives that back the above hooks.
    ".claude/hooks/_lib/contract.py",
    ".claude/hooks/_lib/policy.py",
    ".claude/hooks/_lib/policy_preprocessors.py",
    ".claude/hooks/_lib/redact.py",
    ".claude/hooks/_lib/pii_patterns.py",
    ".claude/hooks/_lib/audit_emit.py",
    ".claude/hooks/_lib/adapters/claude.py",
    # The policy-as-code declarative surface — drives policy_dispatch.py.
    ".claude/policies/*.yaml",
    ".claude/policies/*.yml",
    ".claude/policies/fixtures/*.jsonl",
    # The policy_dispatch dispatcher itself.
    ".claude/hooks/policy_dispatch.py",
    # PLAN-045 Wave 1 P0-03 — native-subagent frontmatter under kernel.
    # ``.claude/agents/*.md`` carries the ``model:`` field read by
    # Claude Code's native subagent dispatcher. F-01-03 documented the
    # demotion-via-frontmatter attack: an agent that edits
    # ``security-engineer.md`` can silently route the VETO role to
    # Haiku. Adding this glob to the kernel HARD-DENY list means
    # frontmatter mutations require ``CEO_KERNEL_OVERRIDE + ACK``
    # (which a sub-agent cannot forge).
    ".claude/agents/*.md",
    # PLAN-085 Wave E.2 — ADR-116 13-entry kernel-extension (S111).
    # Closes F-C2-008 single-edit catastrophic chain. Each entry maps to
    # >=1 of the 4 attack vectors per ADR-116 §2. PLAN-089 will revisit
    # the 22 deferred R-026 paths via a separate ADR.
    #
    # Attack-vector coverage per entry:
    # (1) settings.json     -> hook configuration disable (vector 1 + 2)
    # (2) _python-hook.sh   -> hook runtime swap (vector 1)
    # (3) gpg_verify.py     -> sentinel signature bypass (vector 2)
    # (4) audit_hmac.py     -> chain-integrity bypass (vector 3)
    # (5) secret_patterns   -> secret-scan bypass (vector 1)
    # (6) injection_patterns-> injection-scan bypass (vector 1)
    # (7) output_scan       -> egress-scan bypass (vector 4)
    # (8) codex_egress_redact-> Codex egress redactor (vector 4)
    # (9) dispatcher/**     -> Pair-Rail VETO matrix (vector 4)
    # (10-11) release.yml + validate.yml -> CI gate bypass (vector 2)
    # (12) sentinel-signers.txt -> allowlist injection (vector 2)
    # (13) trusted_env.py   -> ADR-040-AMEND-2 Layer 1 trust-root (vector 1)
    ".claude/settings.json",
    ".claude/hooks/_python-hook.sh",
    ".claude/hooks/_lib/gpg_verify.py",
    ".claude/hooks/_lib/audit_hmac.py",
    ".claude/hooks/_lib/secret_patterns.py",
    ".claude/hooks/_lib/injection_patterns.py",
    ".claude/hooks/_lib/output_scan.py",
    ".claude/hooks/_lib/codex_egress_redact.py",
    ".claude/dispatcher/**/*",
    ".github/workflows/release.yml",
    ".github/workflows/validate.yml",
    ".claude/sentinel-signers.txt",
    # M8 — sentinel_signers.py is the ADR-121 YAML signer-registry
    # loader consumed by check_canonical_edit.py's dual-rail signer check
    # (is_valid_signer / load_registry). It is identity-trust + KERNEL-HARD-DENY-
    # enforcer tier (same as sentinel-signers.txt and gpg_verify.py): an agent
    # that can edit it can forge the signer-validity decision and grant itself
    # canonical-edit authority. The canonical-edit sentinel guard already covers
    # it via `.claude/hooks/_lib/*.py`, but that rail is sentinel-UNLOCKABLE;
    # the kernel rail (no sentinel escape) must guard it too. Fail-CLOSED-only
    # gap closure.
    ".claude/hooks/_lib/sentinel_signers.py",
    ".claude/hooks/_lib/trusted_env.py",
    # PLAN-089 Wave A.4 — ADR-116-AMEND-1 kernel-extension-v2 START
    # ADR-116-AMEND-1 (PLAN-089) — extends ADR-116 §4 enumeration; each
    # entry scored against ADR-116 §4 criteria (>=2 of: tier-0-governance,
    # audit-integrity, identity-trust, kernel-overrider-self-reference,
    # KERNEL HARD-DENY enforcer). Rationale: PLAN-089/kernel-extension-
    # v2-enumeration.md. Honest deferrals (15%) documented in the same file.
    ".claude/hooks/_lib/mcp/canonical_guard.py",
    ".claude/hooks/_lib/mcp/bearer_replay.py",
    ".claude/hooks/_lib/credentials.py",
    ".claude/hooks/_lib/canonical_json.py",
    ".claude/hooks/_lib/audit_rotation.py",
    ".claude/hooks/_lib/replay_redact.py",
    ".claude/hooks/_lib/injection_salt.py",
    ".claude/hooks/_lib/mcp_injection_scan.py",
    ".claude/hooks/_lib/spec_context_sanitizer.py",
    ".claude/hooks/_lib/state_store.py",
    ".claude/hooks/_lib/filelock.py",
    ".claude/hooks/_lib/adapters/codex.py",
    ".claude/hooks/_lib/adapters/_constants.py",
    ".claude/hooks/_lib/__init__.py",
    ".claude/hooks/_lib/adapters/__init__.py",
    ".claude/hooks/_lib/mcp/__init__.py",
    ".claude/hooks/_lib/tier_policy/loader.py",
    ".claude/hooks/_lib/tier_policy/__init__.py",
    ".claude/hooks/_lib/tier_policy/_constants.py",
    ".claude/hooks/_lib/tier_policy/_agent_frontmatter.py",
    ".claude/hooks/_lib/tier_policy/_types.py",
    ".claude/hooks/_lib/agent_frontmatter.py",
    ".claude/hooks/_lib/model_routing.py",
    ".claude/hooks/_lib/mcp_routing.py",
    ".claude/hooks/_lib/pair_rail_decide.py",
    ".claude/hooks/_lib/escalation_signals.py",
    ".claude/hooks/check_pair_rail.py",
    ".claude/hooks/check_bash_safety.py",
    ".claude/hooks/check_bash_canonical_forensic.py",
    ".claude/hooks/check_codex_filewrite.py",
    ".claude/hooks/check_codex_response.py",
    ".claude/hooks/check_skill_bootstrap_post.py",
    ".claude/hooks/check_skill_reference_read.py",
    ".claude/hooks/check_read_injection.py",
    ".claude/hooks/check_webfetch_injection.py",
    ".claude/hooks/check_output_secrets.py",
    ".claude/hooks/check_output_safety.py",
    ".claude/hooks/check_mcp_response.py",
    ".claude/hooks/check_tier_policy.py",
    ".claude/hooks/check_tier_policy_misrouting_24h.py",
    ".claude/hooks/check_subagent_fabrication.py",
    ".claude/hooks/check_confidence_gate.py",
    ".claude/hooks/check_anti_ceo_overhead.py",
    ".claude/hooks/check_scratchpad_access.py",
    ".claude/hooks/check_budget.py",
    ".claude/hooks/check_fluency_nudge.py",
    ".claude/hooks/audit_log.py",
    ".claude/hooks/SessionStart.py",
    ".claude/hooks/SessionEnd.py",
    ".claude/hooks/Stop.py",
    ".claude/hooks/UserPromptSubmit.py",
    ".claude/hooks/emit_architect_outcome.py",
    ".claude/tier-policy.json",
    ".claude/tier-policy.json.sigchain",
    ".claude/governance/governance-waivers.yaml",
    ".claude/governance/codex-cli-pin.txt",
    ".claude/governance/codex-cli-binary-sha256.txt",
    ".claude/governance/pair-rail-inputs-hash-manifest.txt",
    ".claude/governance/pair-rail-verdict-template.md",
    ".claude/governance/function-length-grandfather.yaml",
    ".claude/governance/audit_tokens_allowlist.json",
    ".github/CODEOWNERS",
    ".github/workflows/mutation-gate.yml",
    ".github/workflows/coverage.yml",
    ".github/workflows/actionlint.yml",
    # PLAN-089 Wave A.4 — ADR-116-AMEND-1 kernel-extension-v2 END
    # PLAN-099 Wave E.1 — ADR-129 / ADR-135 federation paths (6 entries).
    # Federation enable + LAN sentinel pairs + peer registry must be
    # kernel-guarded so a sub-agent cannot forge an enable / bypass
    # the LAN gate by overwriting peers.yaml. The trailing glob covers
    # the dir-root semantic (plan §3 Wave E.1 entry #1) — any future
    # file added under .claude/data/federation/ inherits kernel-guard.
    ".claude/data/federation/peers.yaml",
    ".claude/data/federation/enabled.md",
    ".claude/data/federation/enabled.md.asc",
    ".claude/data/federation/lan-enabled.md",
    ".claude/data/federation/lan-enabled.md.asc",
    ".claude/data/federation/**/*",
]


def _emit_allow(system_message: Optional[str] = None) -> str:
    # Claude Code hook schema: top-level "allow" is NOT valid.
    # Emit empty {} or {"systemMessage": ...}.
    out: dict = {}
    if system_message:
        out["systemMessage"] = system_message
    return json.dumps(out, ensure_ascii=False)


def _emit_block(reason: str) -> str:
    return json.dumps(
        {"decision": "block", "reason": reason}, ensure_ascii=False
    )


def _fnmatch_segments(path: str, pattern: str) -> bool:
    """Segment-wise glob (copy of check_canonical_edit helper).

    - `*` matches exactly one segment.
    - `**` matches zero or more segments.
    """
    p_parts = path.split("/")
    pat_parts = pattern.split("/")
    return _match_segments(p_parts, pat_parts)


def _match_segments(p_parts: List[str], pat_parts: List[str]) -> bool:
    if not pat_parts:
        return not p_parts
    head, rest = pat_parts[0], pat_parts[1:]
    if head == "**":
        for i in range(len(p_parts) + 1):
            if _match_segments(p_parts[i:], rest):
                return True
        return False
    if not p_parts:
        return False
    if head == "*" or fnmatch.fnmatchcase(p_parts[0], head):
        return _match_segments(p_parts[1:], rest)
    return False


def _is_kernel_path(path_str: str, repo_root: Path) -> bool:
    """True if path_str resolves inside the kernel HARD-DENY list."""
    if not path_str:
        return False
    p = Path(path_str)
    try:
        rel = str(p.resolve().relative_to(repo_root.resolve())).replace(
            os.sep, "/"
        )
    except (ValueError, OSError):
        # Path outside repo root → cannot be a kernel path by definition.
        return False
    for pattern in _KERNEL_PATHS:
        if _fnmatch_segments(rel, pattern):
            return True
    return False


_ACK_TOKEN = "I-ACCEPT"
_REASON_RE = re.compile(r"^[A-Za-z0-9._\-]{1,120}$")


def _override_granted(env: dict) -> bool:
    """True only when BOTH env vars are set correctly.

    `CEO_KERNEL_OVERRIDE` must be a non-empty reason slug matching
    `[A-Za-z0-9._-]{1,120}`. `CEO_KERNEL_OVERRIDE_ACK` must equal the
    literal ACK token `I-ACCEPT`. Both must be present — the ACK alone
    (or a reason alone) does not grant override. This prevents
    accidental pastes from elsewhere from enabling the bypass.
    """
    reason = (env.get("CEO_KERNEL_OVERRIDE") or "").strip()
    ack = (env.get("CEO_KERNEL_OVERRIDE_ACK") or "").strip()
    if not reason or not ack:
        return False
    if ack != _ACK_TOKEN:
        return False
    if not _REASON_RE.match(reason):
        return False
    return True


def decide(
    *,
    tool_name: str,
    file_path: str,
    repo_root: Path,
    env: Optional[dict] = None,
) -> str:
    """Pure decision function. Returns JSON payload string."""
    # Out of scope: only act on edit-class tools.
    if tool_name not in {"Edit", "Write", "MultiEdit"}:
        return _emit_allow()

    src_env = env if env is not None else os.environ

    if not file_path:
        # Fail-closed: if the tool is edit-class but we have no file_path,
        # we cannot prove the target is non-kernel. Block.
        return _emit_block(
            reason=(
                "ARBITRATION-KERNEL-BLOCKED: edit-class tool invocation "
                "without a file_path — cannot verify target is non-kernel. "
                "Re-issue with a concrete file_path."
            )
        )

    if not _is_kernel_path(file_path, repo_root):
        return _emit_allow()

    if _override_granted(src_env):
        reason = src_env.get("CEO_KERNEL_OVERRIDE", "").strip()
        # PLAN-113 WIRE-AUDIT: emit kernel_extension_landed on override grant.
        # This is the canonical callsite — every kernel-guarded edit that
        # proceeds via CEO_KERNEL_OVERRIDE fires this event once per tool call.
        try:
            from _lib import audit_emit as _audit_emit_ke
            if hasattr(_audit_emit_ke, "emit_kernel_extension_landed"):
                _rel_path = ""
                try:
                    _rel_path = str(
                        Path(file_path).resolve()
                        .relative_to(repo_root.resolve())
                    ).replace(os.sep, "/")
                except Exception:
                    _rel_path = file_path[:128]
                _audit_emit_ke.emit_kernel_extension_landed(
                    plan_id=reason[:32],
                    wave="kernel-override",
                    entries_added=0,
                    cardinality_after=0,
                    ceremony_sha=_rel_path[:64],
                )
        except Exception:  # pragma: no cover — fail-open
            pass
        return _emit_allow(
            system_message=(
                f"ARBITRATION-KERNEL: override granted — reason='{reason}'. "
                "Edit audited; see event stream veto_triggered "
                "reason_code=kernel_override_used."
            )
        )

    try:
        rel = str(Path(file_path).resolve().relative_to(repo_root.resolve())).replace(
            os.sep, "/"
        )
    except Exception:
        rel = file_path

    return _emit_block(
        reason=(
            f"ARBITRATION-KERNEL-BLOCKED: '{rel}' is an arbitration-kernel "
            "file (the hooks and libraries that enforce governance). "
            "These paths have NO sentinel escape — they are only editable "
            "when both CEO_KERNEL_OVERRIDE=<reason-slug> and "
            f"CEO_KERNEL_OVERRIDE_ACK={_ACK_TOKEN} are set in the session "
            "shell. This is stricter than the canonical-edit sentinel by "
            "design: a sub-agent cannot forge these env vars. "
            "See PLAN-019 P1-SEC-A."
        )
    )


def _audit_block(rel: str, override_used: bool) -> None:
    """Best-effort emit of veto_triggered event. Never raises.

    Schema v2.14 (PLAN-044 audit-v2 P1 #6): resolves caller identity
    from CLAUDE_AGENT_NAME / CLAUDE_PARENT_AGENT / "ceo" and passes
    session_id from CLAUDE_SESSION_ID for forensic traceability.
    """
    try:
        from _lib import audit_emit
        # Caller resolution (P1 #6 / schema v2.14):
        # 1. CLAUDE_AGENT_NAME — set on sub-agent process tree
        # 2. CLAUDE_PARENT_AGENT — set on nested spawns
        # 3. "ceo" — top-of-session default (no spawner)
        caller = (
            os.environ.get("CLAUDE_AGENT_NAME")
            or os.environ.get("CLAUDE_PARENT_AGENT")
            or "ceo"
        ).strip()
        session_id = (os.environ.get("CLAUDE_SESSION_ID") or "").strip()
        audit_emit.emit_veto_triggered(
            hook="check_arbitration_kernel",
            reason_code=(
                "kernel_override_used" if override_used
                else "kernel_edit_blocked"
            ),
            reason_preview=(
                f"kernel override used on {rel}"
                if override_used
                else f"blocked kernel edit on {rel}"
            ),
            blocked_tool="Edit|Write|MultiEdit",
            project=os.environ.get("CLAUDE_PROJECT_DIR") or "",
            session_id=session_id,
            caller=caller,
        )
    except Exception:
        return


def main() -> int:
    """Hook entry point.

    Uses the Adapter Layer. On catastrophic (import/adapter) failure,
    fail-open so the runtime isn't bricked. On payload-parse failure,
    fail-closed for edit-class tools (blocks).
    """
    try:
        from _lib.adapters import claude as _claude_adapter  # noqa: E402
        from _lib import contract as _contract  # noqa: E402
    except Exception:
        # Cannot even load the adapter — don't brick the session.
        sys.stdout.write(_emit_allow() + "\n")
        return 0

    try:
        event = _claude_adapter.read_event(phase="PreToolUse")
    except Exception:
        _claude_adapter.emit_decision(_contract.allow())
        return 0

    tool_name = (event.tool_name or "").strip() or "Edit"

    if event.parse_error:
        # Fail-closed: if we cannot parse the stdin payload, we cannot
        # trust the routing. If the matcher fired, the tool was edit-class;
        # block to be safe.
        if tool_name in {"Edit", "Write", "MultiEdit"}:
            sys.stdout.write(
                _emit_block(
                    reason=(
                        "ARBITRATION-KERNEL-BLOCKED: PreToolUse payload "
                        "parse error on an edit-class invocation. Cannot "
                        "verify target path; fail-closed."
                    )
                )
                + "\n"
            )
            return 0
        _claude_adapter.emit_decision(_contract.allow())
        return 0

    repo_root = Path(os.environ.get("CLAUDE_PROJECT_DIR") or os.getcwd())
    file_path = event.file_path or ""

    try:
        out = decide(
            tool_name=tool_name,
            file_path=file_path,
            repo_root=repo_root,
        )
    except Exception as e:
        # PLAN-024 F-chaos-002 P0 fix: kernel guard MUST fail-CLOSED on
        # edit-class tool names when decide() raises — matches the
        # parse-error branch above (lines ~290-302) and chaos-and-
        # resilience skill rule "safety mechanisms MUST NOT be disabled
        # without a replacement". Non-edit tools (Bash, Read, etc.) keep
        # the fail-open contract since they aren't guarded by this hook.
        print(
            f"[check_arbitration_kernel] FATAL: {type(e).__name__}: {e}",
            file=sys.stderr,
        )
        if tool_name in {"Edit", "Write", "MultiEdit"}:
            sys.stdout.write(
                _emit_block(
                    reason=(
                        "ARBITRATION-KERNEL-BLOCKED: decide() raised "
                        f"{type(e).__name__}; fail-closed on edit-class "
                        "invocation per PLAN-024 F-chaos-002."
                    )
                )
                + "\n"
            )
            return 0
        _claude_adapter.emit_decision(_contract.allow())
        return 0

    parsed = json.loads(out)
    decision = parsed.get("decision")
    if decision == "block":
        try:
            rel = str(
                Path(file_path).resolve().relative_to(repo_root.resolve())
            ).replace(os.sep, "/")
        except Exception:
            rel = file_path
        _audit_block(rel, override_used=False)
    elif decision == "allow" and _override_granted(os.environ) and _is_kernel_path(
        file_path, repo_root
    ):
        # Allow path WITH override — still audit.
        try:
            rel = str(
                Path(file_path).resolve().relative_to(repo_root.resolve())
            ).replace(os.sep, "/")
        except Exception:
            rel = file_path
        _audit_block(rel, override_used=True)

    sys.stdout.write(out + "\n")
    return 0


if __name__ == "__main__":
    sys.exit(main())
