#!/usr/bin/env python3
"""PreToolUse Edit/Write/MultiEdit hook: gate SKILL.md writes on an
Owner-signed skill-patch proposal (ADR-031, Sprint 11 Phase 4).

Scope
-----
Complements `check_canonical_edit.py` (ADR-010). ADR-010 requires a
plan-level sentinel (``approved.md``) to allow an edit to any canonical
governance path. This hook adds a STRICTER contract for the
``SKILL.md`` subset: a matching **SP-NNN proposal** must exist under
``.claude/proposals/`` with status ``shadow`` or ``promoted``, AND the
commit session MUST carry the proposal's diff SHA-256 in the env var
``CEO_SKILL_PATCH_SHA``. This defends against:

- Forged sentinel: Owner signed a plan-level approval.md once, then an
  agent later tries to slip a malicious SKILL.md edit.
- Hash mismatch: the proposal says "apply diff X" but the actual edit
  is "diff Y".

Fail-open contract (ADR-005)
----------------------------
Any internal exception → allow. The hook NEVER blocks the user on its
own bug. But this is a safety surface — ``CEO_SOTA_DISABLE=1`` is NOT
honored here (propose.py and apply.py honor it; the sentinel does not).

Decision logic
--------------
1. Read PreToolUse event. If tool is not Edit/Write/MultiEdit or
   ``file_path`` is empty → allow.
2. If the target path is not ``**/SKILL.md`` under ``.claude/skills/``
   → allow (this hook only cares about SKILL.md).
3. Compute the ``skill_slug`` = parent directory name.
4. Scan ``.claude/proposals/SP-*.md`` for a proposal with matching
   ``skill_slug`` and ``status`` in {``shadow``, ``promoted``}.
5. If none found → block with ``"SKILL.md edit requires signed SP-NNN
   proposal (ADR-031)"``.
6. If found but the env var ``CEO_SKILL_PATCH_SHA`` is missing OR does
   not match the proposal's ``sha256_of_diff`` → block with trailer
   mismatch reason.
7. Otherwise → allow.

Wire-up
-------
Registered in ``.claude/settings.json`` PreToolUse after
``check_canonical_edit.py`` — both fire on the ``Edit|Write|MultiEdit``
matcher; this one is SKILL.md-specific and more restrictive.
"""

from __future__ import annotations

import json
import os
import re
import sys
from pathlib import Path
from typing import Dict, List, Optional

_HOOKS_DIR = Path(__file__).resolve().parent
if str(_HOOKS_DIR) not in sys.path:
    sys.path.insert(0, str(_HOOKS_DIR))


# Matches `.claude/skills/<tier>/.../SKILL.md` anywhere in the tree.
_SKILL_MD_RE = re.compile(r"\.claude/skills/(?:[^/]+/)+SKILL\.md$")

# Accepted statuses that imply Owner approval occurred.
_APPROVED_STATUSES = frozenset({"shadow", "promoted"})


def _emit_allow(system_message: Optional[str] = None) -> str:
    # Claude Code hook schema: top-level "allow" is NOT valid (enum is
    # "approve"|"block"). Emit empty {} or {"systemMessage": ...}.
    out: Dict[str, str] = {}
    if system_message:
        out["systemMessage"] = system_message
    return json.dumps(out, ensure_ascii=False)


def _emit_block(reason: str) -> str:
    return json.dumps(
        {"decision": "block", "reason": reason}, ensure_ascii=False
    )


def _is_skill_md(path_str: str, repo_root: Path) -> bool:
    """True if path_str points to a `.claude/skills/.../SKILL.md` file."""
    if not path_str:
        return False
    try:
        p = Path(path_str)
        try:
            rel = str(p.resolve().relative_to(repo_root.resolve())).replace(os.sep, "/")
        except (ValueError, OSError):
            rel = str(path_str).replace(os.sep, "/")
        return bool(_SKILL_MD_RE.search(rel))
    except Exception:
        return False


def _skill_slug_for(path_str: str) -> str:
    """Return the parent directory slug for a SKILL.md path."""
    try:
        return Path(path_str).parent.name
    except Exception:
        return ""


def _parse_frontmatter(text: str) -> Dict[str, str]:
    """Extract a minimal flat string->string view of the YAML frontmatter.

    We parse only the subset of YAML we actually emit in proposals:
    ``key: value`` on its own line (possibly with surrounding quotes).
    Returns {} on parse error.
    """
    if not text.startswith("---"):
        return {}
    end = text.find("\n---", 3)
    if end < 0:
        return {}
    header = text[3:end]
    result: Dict[str, str] = {}
    for raw_line in header.splitlines():
        line = raw_line.strip()
        if not line or line.startswith("#"):
            continue
        if ":" not in line:
            continue
        # Skip list-item lines (they start with "-")
        if line.startswith("-"):
            continue
        key, _, value = line.partition(":")
        key = key.strip()
        value = value.strip()
        # Strip surrounding quotes
        if len(value) >= 2 and value[0] == value[-1] and value[0] in {'"', "'"}:
            value = value[1:-1]
        result[key] = value
    return result


def _find_proposals_for_skill(
    repo_root: Path, skill_slug: str
) -> List[Dict[str, str]]:
    """Scan .claude/proposals/ for matching SP-NNN proposals."""
    proposals_dir = repo_root / ".claude" / "proposals"
    if not proposals_dir.is_dir():
        return []
    matches: List[Dict[str, str]] = []
    # Only direct children ``SP-*.md`` — do not descend.
    for entry in sorted(proposals_dir.iterdir()):
        if not entry.is_file():
            continue
        if not entry.name.startswith("SP-"):
            continue
        if entry.name.startswith("SP-REJECTED-"):
            continue
        if not entry.name.endswith(".md"):
            continue
        try:
            text = entry.read_text(encoding="utf-8")
        except OSError:
            continue
        fm = _parse_frontmatter(text)
        if not fm:
            continue
        if fm.get("skill_slug") != skill_slug:
            continue
        if fm.get("status", "") not in _APPROVED_STATUSES:
            continue
        fm["_path"] = str(entry)
        matches.append(fm)
    return matches


# PLAN-042 ITEM 8 (FINDING-18): path-validation hardening. The
# bootstrap branch must not rely on upstream _is_skill_md filter —
# defense-in-depth requires local scope + slug regex + traversal reject.
_BOOTSTRAP_SLUG_RE = re.compile(r"[a-z][a-z0-9-]{1,63}")


def _bootstrap_bypass_allows(file_path: str, skill_slug: str) -> bool:
    """ADR-059 bootstrap bypass — two-factor env-var path for NEW skills.

    Returns True iff:
    1. CEO_SKILL_BOOTSTRAP env equals the skill_slug exactly.
    2. CEO_SKILL_BOOTSTRAP_ACK env equals "I-ACCEPT" exactly.
    3. Target SKILL.md does NOT already exist (bootstrap-only, not patch).
    4. PLAN-042 ITEM 8: target path, after resolve(), lives under
       <repo_root>/.claude/skills/ — rejects paths outside the
       governance subtree.
    5. PLAN-042 ITEM 8: skill_slug matches [a-z][a-z0-9-]{1,63} —
       rejects path-traversal tokens, empty slugs, overly long slugs.
    6. PLAN-042 ITEM 8: raw file_path contains no ".." segment —
       reject before any resolution can silently normalize it.

    Audit emit is best-effort via _lib.audit_emit if available; never
    raises.

    Design rationale: ADR-031 check_skill_patch_sentinel was designed
    for PATCHES over existing SKILL.md. NEW skill bootstrap has no
    SP-NNN proposal available. This bypass adds the two-factor
    env-var pattern (parallel to CEO_KERNEL_OVERRIDE + _ACK) for
    bootstrap-only — a target that already exists continues through
    the SP-NNN gate.
    """
    env_slug = os.environ.get("CEO_SKILL_BOOTSTRAP", "").strip()
    env_ack = os.environ.get("CEO_SKILL_BOOTSTRAP_ACK", "").strip()

    if env_slug != skill_slug:
        return False
    if env_ack != "I-ACCEPT":
        return False

    # ITEM 8 step 5: slug must match the whitelist regex. Empty or
    # path-traversal-laced slugs never match.
    if not _BOOTSTRAP_SLUG_RE.fullmatch(skill_slug or ""):
        return False

    # ITEM 8 step 6: raw file_path with "..": reject outright. Some
    # filesystems normalize ".." through symlinks; rejecting at the
    # raw string level eliminates that ambiguity.
    if ".." in (file_path or "").replace("\\", "/").split("/"):
        return False

    # Bootstrap-only: target must NOT already exist. Existing SKILL.md
    # edits continue to require the SP-NNN flow.
    try:
        target = Path(file_path)
        if target.exists():
            return False
    except Exception:
        return False

    # ITEM 8 step 4: scope check via resolve + relative_to. Any resolved
    # path outside <repo_root>/.claude/skills/ is rejected even if the
    # slug + env vars look legitimate.
    try:
        repo_root = Path(
            os.environ.get("CLAUDE_PROJECT_DIR") or os.getcwd()
        ).resolve()
        skills_root = repo_root / ".claude" / "skills"
        try:
            resolved_parent = target.resolve().parent
            resolved_parent.relative_to(skills_root)
        except (ValueError, OSError):
            return False
    except Exception:
        return False

    # Best-effort audit emit (never raises).
    try:
        from _lib import audit_emit
        audit_emit.emit_generic(
            action="skill_bootstrap_used",
            skill_slug=skill_slug,
            env_set=True,
            project=os.environ.get("CLAUDE_PROJECT_DIR") or "",
        )
    except Exception:
        pass

    return True




def decide(*, file_path: str, repo_root: Path) -> str:
    """Pure decision function.

    Returns the JSON payload (legacy contract — pre-built string) that
    the hook will write to stdout.
    """
    if not file_path:
        return _emit_allow()

    if not _is_skill_md(file_path, repo_root):
        # Non-SKILL.md paths (including sibling ``SKILL.md.shadow.md``
        # shadow files, which this hook deliberately does not gate —
        # skill-patch-apply.py is their only legitimate writer and it
        # has already verified the Owner signature) pass through.
        return _emit_allow()

    skill_slug = _skill_slug_for(file_path)
    if not skill_slug:
        # Unreachable under normal paths but fail-closed here is unsafe
        # per fail-open contract.
        return _emit_allow()

    # ADR-059 — bootstrap bypass check BEFORE SP-NNN proposal lookup.
    if _bootstrap_bypass_allows(file_path, skill_slug):
        return _emit_allow(
            system_message=(
                f"SKILL-BOOTSTRAP: allowed via ADR-059 two-factor env "
                f"(CEO_SKILL_BOOTSTRAP={skill_slug}, "
                f"CEO_SKILL_BOOTSTRAP_ACK=I-ACCEPT, target did not exist)"
            )
        )

    proposals = _find_proposals_for_skill(repo_root, skill_slug)
    if not proposals:
        return _emit_block(
            reason=(
                "SKILL.md edit requires signed SP-NNN proposal (ADR-031). "
                f"No approved proposal found for skill_slug='{skill_slug}'. "
                "Run: .claude/scripts/skill-patch-apply.py --proposal SP-NNN "
                "--signature <sig> --confirm 'I have read SP-NNN'"
            )
        )

    env_sha = os.environ.get("CEO_SKILL_PATCH_SHA", "").strip().lower()
    if not env_sha:
        return _emit_block(
            reason=(
                "SKILL.md edit requires CEO_SKILL_PATCH_SHA env var set to "
                "the proposal's sha256_of_diff (ADR-031). "
                f"Found {len(proposals)} approved proposal(s) for "
                f"skill_slug='{skill_slug}'."
            )
        )

    matching = [
        p for p in proposals if p.get("sha256_of_diff", "").lower() == env_sha
    ]
    if not matching:
        return _emit_block(
            reason=(
                "SKILL.md edit blocked: CEO_SKILL_PATCH_SHA does not match "
                "any approved proposal's sha256_of_diff (ADR-031 trailer "
                f"mismatch). skill_slug='{skill_slug}'."
            )
        )

    return _emit_allow(
        system_message=(
            f"SKILL-PATCH: allowed via {matching[0].get('id', '?')} "
            f"(sha trailer verified)"
        )
    )


def _audit_block(reason_preview: str, blocked_tool: str) -> None:
    """Best-effort emit of veto_triggered event. Never raises."""
    try:
        from _lib import audit_emit
        audit_emit.emit_veto_triggered(
            hook="check_skill_patch_sentinel",
            reason_code="skill_patch_sentinel_missing_or_mismatch",
            reason_preview=reason_preview,
            blocked_tool=blocked_tool,
            project=os.environ.get("CLAUDE_PROJECT_DIR") or "",
        )
    except Exception:
        return


def main() -> int:
    """Hook entry point.

    Uses Adapter Layer (ADR-014) — byte-identical legacy output.
    """
    try:
        from _lib.adapters import claude as _claude_adapter
        from _lib import contract as _contract
    except Exception:
        # Cannot even import adapters — emit bare allow JSON.
        sys.stdout.write(json.dumps({}) + "\n")  # schema-compliant allow
        return 0

    try:
        event = _claude_adapter.read_event(phase="PreToolUse")
    except Exception:
        _claude_adapter.emit_decision(_contract.allow())
        return 0

    if event.parse_error:
        _claude_adapter.emit_decision(_contract.allow())
        return 0

    if event.tool_name not in {"Edit", "Write", "MultiEdit"}:
        _claude_adapter.emit_decision(_contract.allow())
        return 0

    file_path = event.file_path or ""
    if not file_path:
        _claude_adapter.emit_decision(_contract.allow())
        return 0

    repo_root = Path(os.environ.get("CLAUDE_PROJECT_DIR") or os.getcwd())

    try:
        out = decide(file_path=file_path, repo_root=repo_root)
    except Exception as e:
        print(
            f"[check_skill_patch_sentinel] FATAL: {type(e).__name__}: {e}",
            file=sys.stderr,
        )
        _claude_adapter.emit_decision(_contract.allow())
        return 0

    try:
        parsed = json.loads(out)
    except Exception:
        parsed = {"decision": "allow"}

    if parsed.get("decision") == "block":
        _audit_block(parsed.get("reason", "")[:160], event.tool_name)

    sys.stdout.write(out + "\n")
    return 0


if __name__ == "__main__":
    sys.exit(main())
