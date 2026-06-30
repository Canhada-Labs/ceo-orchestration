#!/usr/bin/env python3
"""skill-patch-apply.py — verify + apply a skill-patch proposal.

ADR-031, Sprint 11 Phase 4.

Flow
----
1. Parse --proposal / --signature / --confirm / --promote.
2. Verify the GPG detached signature over the proposal file (subprocess
   ``gpg --verify``). Missing or invalid → exit 2.
3. Verify the confirm phrase is EXACTLY ``I have read SP-NNN``
   (proposal ID substituted). Mismatch → exit 3.
4. **Default mode (no --promote):** write
   ``<SKILL.md>.shadow.md`` by reconstructing the new SKILL content
   from the proposal's unified diff. Update the proposal frontmatter
   to ``status: shadow`` + ``applied_at: <now>`` + ``approved_by:
   <signer-fpr>``. Emit ``skill_patch_applied(shadow_mode=True)``.
5. **--promote mode:** require ``proposed_at >= 7 days`` ago
   (else exit 4). Require the shadow file already exists from a prior
   apply (else exit 6). Copy shadow to real ``SKILL.md``. Print the
   commit message with a ``Skill-Patch-SHA: <hex>`` trailer. Update
   proposal frontmatter to ``status: promoted``. Emit
   ``skill_patch_applied(shadow_mode=False)``.

``CEO_SOTA_DISABLE=1`` → exit 0 no-op.

Stdlib-only. GPG invoked via subprocess.
"""

from __future__ import annotations

import argparse
import datetime as _dt
import difflib
import json
import os
import re
import shutil
import signal
import subprocess
import sys
from pathlib import Path
from typing import Any, Dict, List, Optional, Tuple


_REPO_ROOT = Path(os.environ.get("CLAUDE_PROJECT_DIR") or os.getcwd()).resolve()
_PROPOSALS_DIR = _REPO_ROOT / ".claude" / "proposals"

_SHADOW_SUFFIX = ".shadow.md"
_SEVEN_DAYS_SECS = 7 * 24 * 60 * 60
_LOCK_TIMEOUT_SECS = 30.0
_PARTIAL_SUFFIX = ".partial"
_QUARANTINE_SUFFIX = ".quarantine"

# Atomic-write state: the signal handler reads this to quarantine the
# in-flight `.partial` on SIGTERM/SIGINT. Set only while
# `_atomic_shadow_write` is executing.
_INFLIGHT_PARTIAL: Optional[Path] = None

# PLAN-012 Phase 3 D4 / debate chaos HIGH-3. Reuse `_lib/filelock.py`
# (ADR-001 amendment Sprint 10 Phase 6 — shared concurrency primitive).
_HOOKS_DIR = _REPO_ROOT / ".claude" / "hooks"
if str(_HOOKS_DIR) not in sys.path:
    sys.path.insert(0, str(_HOOKS_DIR))
try:
    from _lib.filelock import FileLock, FileLockTimeout  # type: ignore
except Exception:  # pragma: no cover
    FileLock = None  # type: ignore[assignment]

    class FileLockTimeout(Exception):  # type: ignore[no-redef]
        pass


def _emit_concurrent_blocked(*, skill_slug: str, shadow_path: Path, reason: str) -> None:
    """Best-effort breadcrumb for concurrent-apply blocking.

    Typed audit events live in ``audit_emit.py`` (out of scope here);
    we emit a human-readable line to stderr + ``audit-log.errors``.
    """
    msg = (f"shadow_concurrent_apply_blocked: skill={skill_slug} "
           f"shadow={shadow_path} reason={reason}")
    sys.stderr.write(f"[skill-patch-apply] {msg}\n")
    try:
        err_path = Path(
            os.environ.get("CEO_AUDIT_LOG_ERR") or (
                Path(os.environ.get("HOME") or str(Path.home()))
                / ".claude" / "projects" / "ceo-orchestration"
                / "audit-log.errors"
            )
        )
        err_path.parent.mkdir(parents=True, exist_ok=True, mode=0o700)
        with err_path.open("a", encoding="utf-8") as f:
            ts = _dt.datetime.now(_dt.timezone.utc).strftime("%Y-%m-%dT%H:%M:%SZ")
            f.write(f"{ts} skill-patch-apply: {msg}\n")
    except Exception:  # pragma: no cover
        pass


def _quarantine_path_for(shadow_path: Path) -> Path:
    return shadow_path.with_name(shadow_path.name + _QUARANTINE_SUFFIX)


def _partial_path_for(shadow_path: Path) -> Path:
    return shadow_path.with_name(shadow_path.name + _PARTIAL_SUFFIX)


def _lock_path_for(shadow_path: Path) -> Path:
    return shadow_path.with_name(shadow_path.name + ".lock")


def _install_signal_handlers() -> List[Tuple[int, Any]]:
    """Install SIGTERM/SIGINT handlers that quarantine in-flight partial."""
    def _handler(signum, frame) -> None:  # type: ignore[no-untyped-def]
        global _INFLIGHT_PARTIAL
        partial = _INFLIGHT_PARTIAL
        _INFLIGHT_PARTIAL = None
        if partial is not None and partial.is_file():
            qpath = _quarantine_path_for(
                partial.with_name(partial.name[: -len(_PARTIAL_SUFFIX)])
            )
            try:
                if not qpath.exists():
                    partial.replace(qpath)
            except Exception:  # pragma: no cover
                pass
            sys.stderr.write(
                f"[skill-patch-apply] signal {signum} mid-write; "
                f"quarantined partial to {qpath}\n"
            )
        raise SystemExit(128 + int(signum))

    prev: List[Tuple[int, Any]] = []
    for sig in (signal.SIGTERM, signal.SIGINT):
        try:
            prev.append((int(sig), signal.signal(sig, _handler)))
        except (ValueError, OSError):  # pragma: no cover
            pass
    return prev


def _restore_signal_handlers(prev: List[Tuple[int, Any]]) -> None:
    for sig, handler in prev:
        try:
            signal.signal(sig, handler)
        except (ValueError, OSError):  # pragma: no cover
            pass


def _atomic_shadow_write(shadow_path: Path, content: str) -> None:
    """Write `content` via `.partial` + atomic rename. SIGTERM-safe."""
    global _INFLIGHT_PARTIAL
    partial = _partial_path_for(shadow_path)
    _INFLIGHT_PARTIAL = partial
    try:
        with partial.open("w", encoding="utf-8") as f:
            f.write(content)
            try:
                f.flush(); os.fsync(f.fileno())
            except (OSError, AttributeError):  # pragma: no cover
                pass
        os.replace(partial, shadow_path)
    finally:
        _INFLIGHT_PARTIAL = None


def _refuse_if_quarantined(shadow_path: Path) -> Optional[str]:
    """Return error string if `.quarantine` sibling present; else None."""
    qpath = _quarantine_path_for(shadow_path)
    if qpath.is_file():
        return (
            f"quarantine file exists: {qpath}. A previous apply was "
            f"interrupted mid-write. Re-run with --force-recover to clear."
        )
    return None


# -----------------------------------------------------------------------------
# Audit + event emission helpers (best-effort, fail-open)
# -----------------------------------------------------------------------------


def _emit_audit(
    *,
    proposal_id: str,
    skill_slug: str,
    commit_sha: str,
    signer_fingerprint: str,
    shadow_mode: bool,
) -> None:
    """Best-effort skill_patch_applied event. Never raises."""
    try:
        sys.path.insert(0, str(_REPO_ROOT / ".claude" / "hooks"))
        from _lib import audit_emit  # type: ignore
        audit_emit.emit_skill_patch_applied(
            proposal_id=proposal_id,
            skill_slug=skill_slug,
            commit_sha=commit_sha,
            signer_fingerprint=signer_fingerprint,
            shadow_mode=shadow_mode,
            project=os.environ.get("CLAUDE_PROJECT_DIR") or "",
        )
    except Exception:
        return


# -----------------------------------------------------------------------------
# Frontmatter parsing / rewriting
# -----------------------------------------------------------------------------


def _parse_frontmatter(text: str) -> Tuple[Dict[str, str], str]:
    """Return ({key: value}, body) for a simple markdown+YAML frontmatter.

    Supports the subset emitted by propose.py: scalar strings, null,
    booleans, integers, hex; plus one list key ``source_lessons:`` with
    dash-indented entries.
    """
    if not text.startswith("---"):
        return {}, text
    end = text.find("\n---", 3)
    if end < 0:
        return {}, text
    header = text[3:end]
    body = text[end + 4 :].lstrip("\n")
    result: Dict[str, str] = {}
    cur_list_key: Optional[str] = None
    list_items: List[str] = []
    for raw in header.splitlines():
        stripped = raw.strip()
        if not stripped or stripped.startswith("#"):
            continue
        if stripped.startswith("-") and cur_list_key:
            list_items.append(stripped.lstrip("-").strip())
            continue
        # new key
        if cur_list_key and list_items:
            result[cur_list_key] = ",".join(list_items)
            list_items = []
            cur_list_key = None
        if ":" not in stripped:
            continue
        key, _, value = stripped.partition(":")
        key = key.strip()
        value = value.strip()
        if value == "":
            # possibly start of a list
            cur_list_key = key
            continue
        if len(value) >= 2 and value[0] == value[-1] and value[0] in {'"', "'"}:
            value = value[1:-1]
        result[key] = value
    if cur_list_key and list_items:
        result[cur_list_key] = ",".join(list_items)
    return result, body


def _rewrite_frontmatter(text: str, updates: Dict[str, str]) -> str:
    """Return ``text`` with frontmatter keys replaced per ``updates``.

    Only keys already present in the frontmatter are updated. Unknown
    keys are appended in a conservative order at the end of the block.
    List keys (source_lessons) are left untouched.
    """
    if not text.startswith("---"):
        return text
    end = text.find("\n---", 3)
    if end < 0:
        return text
    header = text[3:end]
    rest = text[end:]  # includes "\n---..."

    applied = set()
    new_lines: List[str] = []
    for raw in header.splitlines():
        stripped = raw.strip()
        if ":" in stripped and not stripped.startswith("-"):
            key = stripped.split(":", 1)[0].strip()
            if key in updates:
                new_lines.append(f"{key}: {updates[key]}")
                applied.add(key)
                continue
        new_lines.append(raw)
    for key, val in updates.items():
        if key not in applied:
            new_lines.append(f"{key}: {val}")
    return "---" + "\n".join(["", *new_lines, ""]) + rest[1:]


# -----------------------------------------------------------------------------
# Proposal discovery
# -----------------------------------------------------------------------------


def _find_proposal(proposal_id: str) -> Optional[Path]:
    if not _PROPOSALS_DIR.is_dir():
        return None
    matches = sorted(_PROPOSALS_DIR.glob(f"{proposal_id}-*.md"))
    # Exclude rejection artifacts + shadow files.
    matches = [
        m for m in matches
        if not m.name.startswith("SP-REJECTED-")
        and not m.name.endswith(_SHADOW_SUFFIX)
    ]
    if not matches:
        return None
    return matches[0]


# -----------------------------------------------------------------------------
# Signature verification
# -----------------------------------------------------------------------------


_SKILL_PATCH_SIGNERS_FILE = _REPO_ROOT / ".claude" / "skill-patch-signers.txt"


def _verify_gpg_signature(
    proposal_path: Path, signature_path: Path
) -> Tuple[bool, str]:
    """Verify detached GPG signature + signer-fpr allowlist.

    PLAN-045 Wave 1 P0-02: delegates to the shared
    ``_lib.gpg_verify.verify_detached`` helper and cross-checks the
    signer fingerprint against ``.claude/skill-patch-signers.txt``.

    Closes PLAN-044 F-01-02 TOFU anti-pattern: previously any valid
    GOODSIG was accepted, so a compromised mirror shipping a second
    signing key became a trusted writer. Now the fingerprint MUST
    match the allowlist; empty allowlist = fail-CLOSED.

    Returns ``(ok, fingerprint)`` for backwards compatibility with the
    existing call-site in ``_load_and_verify_proposal``. On failure
    the empty string is returned; a detailed reason is written to
    stderr so the Owner can diagnose bad signatures vs missing
    allowlist entries.
    """
    from _lib import gpg_verify  # type: ignore
    ok, fpr, reason = gpg_verify.verify_detached(
        proposal_path,
        signature_path,
        allowlist_path=_SKILL_PATCH_SIGNERS_FILE,
        timeout=15.0,
    )
    if not ok:
        sys.stderr.write(
            f"[skill-patch-apply] gpg verify failed: reason={reason}\n"
        )
        return False, ""
    return True, fpr


# -----------------------------------------------------------------------------
# Diff reconstruction
# -----------------------------------------------------------------------------


def _extract_diff_block(proposal_text: str) -> Optional[str]:
    """Pull the unified diff back out of the proposal's ```diff fence."""
    m = re.search(r"```diff\n(.*?)\n```", proposal_text, flags=re.DOTALL)
    if not m:
        return None
    return m.group(1)


# PLAN-047 P03 follow-up: whole-file NEW skill support. SP-019 et al
# ship with ``proposal_type: create-new-skill`` and a ```markdown fence
# containing the full body of the SKILL.md to create. The existing diff
# path assumed patch-over-existing; this extractor is its sibling.
_MARKDOWN_FENCE_RE = re.compile(r"```markdown\n(.*?)\n```", flags=re.DOTALL)
_CREATE_NEW_SKILL_MAX_BYTES = 256 * 1024  # 256 KiB cap on NEW SKILL body
_SKILL_SLUG_RE = re.compile(r"[a-z][a-z0-9-]{1,63}")
_PROPOSAL_TARGET_RE = re.compile(
    r"^\.claude/skills/(core|frontend|domains/[a-z][a-z0-9-]{0,63}/skills)"
    r"/([a-z][a-z0-9-]{1,63})/SKILL\.md$"
)


def _extract_markdown_block(proposal_text: str) -> Optional[str]:
    """Pull the NEW SKILL.md body out of the proposal's ```markdown fence.

    Mirror of ``_extract_diff_block`` for ``proposal_type:
    create-new-skill`` proposals. Returns None if no fence, multiple
    fences, or body exceeds the 256 KiB cap (defense against accidental
    giant bodies from copy-paste mishaps).
    """
    matches = _MARKDOWN_FENCE_RE.findall(proposal_text)
    if not matches or len(matches) > 1:
        return None
    body = matches[0]
    if len(body.encode("utf-8")) > _CREATE_NEW_SKILL_MAX_BYTES:
        return None
    return body


def _parse_proposal_target(target: str) -> Optional[Tuple[str, str]]:
    """Return (tier, slug) for a `.claude/skills/<tier>/<slug>/SKILL.md` path.

    Accepts:
    - ``.claude/skills/core/<slug>/SKILL.md``
    - ``.claude/skills/frontend/<slug>/SKILL.md``
    - ``.claude/skills/domains/<domain>/skills/<slug>/SKILL.md``

    Returns ``None`` on any shape mismatch (rejects ``..``, backslashes,
    absolute paths, empty slugs, overlong slugs). The caller treats
    ``None`` as a hard-block.
    """
    if not target:
        return None
    # Reject Windows-style separators, absolute paths, and traversal.
    if "\\" in target or target.startswith("/") or ".." in target.split("/"):
        return None
    m = _PROPOSAL_TARGET_RE.match(target)
    if not m:
        return None
    tier_raw, slug = m.group(1), m.group(2)
    return tier_raw, slug


def _resolve_create_new_skill_target(target: str) -> Optional[Path]:
    """Return absolute Path for a NEW SKILL.md, refusing anything outside
    ``<repo_root>/.claude/skills/``.

    Unlike ``_resolve_skill_md``, this accepts non-existent targets (the
    caller intends to create them). Returns ``None`` if the path shape
    is malformed OR if resolution escapes the skills subtree.
    """
    parsed = _parse_proposal_target(target)
    if parsed is None:
        return None
    skills_root = (_REPO_ROOT / ".claude" / "skills").resolve()
    candidate = (_REPO_ROOT / target).resolve()
    try:
        candidate.parent.relative_to(skills_root)
    except ValueError:
        return None
    return candidate


def _apply_unified_diff(original: str, diff: str) -> Optional[str]:
    """Apply a unified diff to ``original`` using difflib recompute.

    The propose.py diff is a simple append, so we prefer a
    pattern-stable recompute over a full diff parser: we extract the
    '+'-prefixed added lines (excluding ``+++`` header), append them to
    the trimmed original, and validate the result.
    """
    if not diff:
        return None
    added_lines: List[str] = []
    in_hunk = False
    for line in diff.splitlines():
        if line.startswith("+++") or line.startswith("---"):
            continue
        if line.startswith("@@"):
            in_hunk = True
            continue
        if not in_hunk:
            continue
        if line.startswith("+"):
            added_lines.append(line[1:])
        elif line.startswith("-"):
            # Conservative: propose.py never removes content in Sprint 11,
            # but we refuse to apply if we see removals (contract violation).
            return None
        # context lines ignored — we're appending

    if not added_lines:
        return None
    addition = "\n".join(added_lines)
    if original and not original.endswith("\n"):
        original += "\n"
    return original + addition + "\n"


# -----------------------------------------------------------------------------
# Main
# -----------------------------------------------------------------------------


def _resolve_skill_md(skill_slug: str) -> Optional[Path]:
    candidates = [
        _REPO_ROOT / ".claude" / "skills" / "core" / skill_slug / "SKILL.md",
        _REPO_ROOT / ".claude" / "skills" / "frontend" / skill_slug / "SKILL.md",
    ]
    for c in candidates:
        if c.is_file():
            return c.resolve()
    domains_dir = _REPO_ROOT / ".claude" / "skills" / "domains"
    if domains_dir.is_dir():
        for d in sorted(domains_dir.iterdir()):
            candidate = d / "skills" / skill_slug / "SKILL.md"
            if candidate.is_file():
                return candidate.resolve()
    return None


def _parse_iso8601(val: str) -> Optional[_dt.datetime]:
    if not val:
        return None
    try:
        return _dt.datetime.strptime(val, "%Y-%m-%dT%H:%M:%SZ").replace(
            tzinfo=_dt.timezone.utc
        )
    except ValueError:
        return None


def _build_main_parser() -> argparse.ArgumentParser:
    """Construct argparse parser for skill-patch-apply.

    Extracted from main() to isolate CLI surface; tests can instantiate
    without invoking main.
    """
    parser = argparse.ArgumentParser(
        description="Verify + apply a skill-patch proposal (ADR-031).",
    )
    parser.add_argument("--proposal", required=True, help="SP-NNN id")
    parser.add_argument("--signature", required=True, help="Path to detached GPG .asc")
    parser.add_argument(
        "--confirm", required=True, help='Exact phrase: "I have read SP-NNN"'
    )
    parser.add_argument(
        "--promote", action="store_true",
        help="Promote shadow file into real SKILL.md (requires 7-day soak).",
    )
    parser.add_argument(
        "--force-recover", action="store_true",
        help=(
            "Remove a lingering .quarantine file left by a SIGTERM/SIGKILL "
            "mid-write. Requires the same --proposal + --signature + "
            "--confirm as a normal apply so the Owner has signed off on "
            "recovery. Exits 0 on success, 6 if no quarantine present."
        ),
    )
    return parser


def _load_and_verify_proposal(
    args: argparse.Namespace,
) -> Tuple[Optional[int], Optional[Path], Optional[Dict[str, str]], str, str]:
    """Locate proposal, verify confirm phrase + GPG signature.

    Returns a 5-tuple ``(exit_code, proposal_path, fm, proposal_text,
    signer_fpr)``. If ``exit_code`` is not ``None``, the caller should
    return it immediately; otherwise the remaining fields are populated.
    """
    proposal_id = args.proposal
    # Validate ID shape.
    if not re.match(r"^SP-\d{3}$", proposal_id):
        sys.stderr.write(
            f"[skill-patch-apply] invalid proposal id: {proposal_id!r}\n"
        )
        return 5, None, None, "", ""

    proposal_path = _find_proposal(proposal_id)
    if proposal_path is None:
        sys.stderr.write(
            f"[skill-patch-apply] proposal {proposal_id} not found under "
            f"{_PROPOSALS_DIR}\n"
        )
        return 5, None, None, "", ""

    proposal_text = proposal_path.read_text(encoding="utf-8")
    fm, _body = _parse_frontmatter(proposal_text)
    if not fm:
        sys.stderr.write(
            f"[skill-patch-apply] malformed frontmatter in {proposal_path.name}\n"
        )
        return 5, None, None, "", ""

    # --- Verify confirm phrase --------------------------------------------
    expected_confirm = f"I have read {proposal_id}"
    if args.confirm != expected_confirm:
        sys.stderr.write(
            f"[skill-patch-apply] confirm phrase mismatch. "
            f"Expected: {expected_confirm!r}\n"
        )
        return 3, None, None, "", ""

    # --- Verify GPG signature ---------------------------------------------
    sig_path = Path(args.signature)
    if not sig_path.is_file():
        sys.stderr.write(
            f"[skill-patch-apply] signature file missing: {sig_path}\n"
        )
        return 2, None, None, "", ""
    ok, fpr = _verify_gpg_signature(proposal_path, sig_path)
    if not ok:
        sys.stderr.write(
            f"[skill-patch-apply] GPG signature verification FAILED for "
            f"{proposal_path.name}\n"
        )
        return 2, None, None, "", ""

    return None, proposal_path, fm, proposal_text, fpr


def _handle_force_recover(shadow_path: Path) -> int:
    """Clear a lingering quarantine/partial pair for ``shadow_path``.

    Returns 0 on successful removal, 5 on unlink failure, 6 if there
    was nothing to recover. Gated at the caller on the same sig +
    confirm phrase as a real apply so an attacker cannot clear a
    quarantine they induced.
    """
    qpath = _quarantine_path_for(shadow_path)
    partial = _partial_path_for(shadow_path)
    removed = False
    if qpath.is_file():
        try:
            qpath.unlink(); removed = True
        except OSError as e:
            sys.stderr.write(
                f"[skill-patch-apply] --force-recover unlink {qpath}: {e}\n"
            )
            return 5
    if partial.is_file():
        try:
            partial.unlink(); removed = True
        except OSError:
            pass
    if not removed:
        sys.stderr.write(
            f"[skill-patch-apply] --force-recover: no quarantine/partial "
            f"at {qpath}\n"
        )
        return 6
    print(
        f"[skill-patch-apply] --force-recover cleared "
        f"{shadow_path.relative_to(_REPO_ROOT)}"
    )
    return 0


def _handle_promote(
    proposal_id: str,
    proposal_path: Path,
    proposal_text: str,
    fm: Dict[str, str],
    skill_md: Path,
    shadow_path: Path,
    skill_slug: str,
    fpr: str,
    sha256: str,
    skip_soak: bool = False,
) -> int:
    """Promote the shadow file into the real SKILL.md.

    Enforces the 7-day soak window unless ``skip_soak`` is set (Owner
    ``--promote --force-recover`` combo, pre-authorized per WAR-ROOM
    01-OWNER-AUTHORIZATIONS.md §D1). Refuses to double-promote, requires
    the shadow file to exist. On success rewrites proposal frontmatter
    to ``status: promoted`` and emits an audit event.
    """
    proposed_at = _parse_iso8601(fm.get("proposed_at", ""))
    if proposed_at is None:
        sys.stderr.write(
            "[skill-patch-apply] proposed_at missing/invalid; refusing promote\n"
        )
        return 5
    age_secs = (
        _dt.datetime.now(_dt.timezone.utc) - proposed_at
    ).total_seconds()
    if age_secs < _SEVEN_DAYS_SECS and not skip_soak:
        sys.stderr.write(
            f"[skill-patch-apply] promote refused: proposal is "
            f"{age_secs/86400:.1f}d old; 7-day shadow soak required\n"
        )
        return 4
    if fm.get("status", "") == "promoted":
        sys.stderr.write(
            "[skill-patch-apply] proposal already promoted\n"
        )
        return 7
    if not shadow_path.is_file():
        sys.stderr.write(
            f"[skill-patch-apply] promote refused: shadow file "
            f"{shadow_path} missing — run apply (no --promote) first\n"
        )
        return 6

    # Merge: write shadow content → real SKILL.md
    new_content = shadow_path.read_text(encoding="utf-8")
    skill_md.write_text(new_content, encoding="utf-8")

    updates = {
        "status": "promoted",
        "promoted_at": _dt.datetime.now(_dt.timezone.utc).strftime(
            "%Y-%m-%dT%H:%M:%SZ"
        ),
        "shadow_mode": "false",
    }
    new_proposal_text = _rewrite_frontmatter(proposal_text, updates)
    proposal_path.write_text(new_proposal_text, encoding="utf-8")

    print(
        f"[skill-patch-apply] PROMOTED {proposal_id} → "
        f"{skill_md.relative_to(_REPO_ROOT)}"
    )
    print("")
    print("Suggested commit message:")
    print("")
    print(f"    skill: apply {proposal_id} to {skill_slug}")
    print("")
    print(f"    Skill-Patch-SHA: {sha256}")
    print("")
    print("Before committing, export:")
    print(f"    export CEO_SKILL_PATCH_SHA={sha256}")
    print("")
    _emit_audit(
        proposal_id=proposal_id,
        skill_slug=skill_slug,
        commit_sha="",
        signer_fingerprint=fpr,
        shadow_mode=False,
    )
    return 0


def _handle_create_new_skill_shadow(
    proposal_id: str,
    proposal_path: Path,
    proposal_text: str,
    skill_md: Path,
    shadow_path: Path,
    skill_slug: str,
    body: str,
    fpr: str,
) -> int:
    """Shadow-apply a `proposal_type: create-new-skill` SP-NNN.

    Parallel of ``_handle_default_apply`` but for NEW SKILL.md files:
    materializes the target directory, writes the whole-file body to
    the shadow sibling atomically under fcntl LOCK_EX. Same filelock +
    quarantine + SIGTERM discipline as the diff path.

    Refuses if the target SKILL.md already exists (create-new-skill
    is bootstrap-only; use the diff path for existing files).
    """
    if skill_md.is_file():
        sys.stderr.write(
            f"[skill-patch-apply] create-new-skill refused: target "
            f"{skill_md.relative_to(_REPO_ROOT)} already exists. "
            f"Use a diff-based SP-NNN to patch an existing skill.\n"
        )
        return 5

    # Materialize parent dir (idempotent). Permissions default per umask;
    # the skill dir is not secret.
    try:
        skill_md.parent.mkdir(parents=True, exist_ok=True)
    except OSError as e:
        sys.stderr.write(
            f"[skill-patch-apply] cannot create parent dir "
            f"{skill_md.parent}: {e}\n"
        )
        return 5

    # Ensure body ends with a single newline for POSIX sanity.
    new_content = body if body.endswith("\n") else body + "\n"

    if FileLock is None:  # pragma: no cover
        sys.stderr.write(
            "[skill-patch-apply] _lib.filelock unavailable; refusing write\n"
        )
        return 5
    try:
        lock = FileLock(str(_lock_path_for(shadow_path)),
                        timeout=_LOCK_TIMEOUT_SECS)
        lock.acquire()
    except FileLockTimeout:
        _emit_concurrent_blocked(
            skill_slug=skill_slug, shadow_path=shadow_path,
            reason=f"lock_timeout_after_{_LOCK_TIMEOUT_SECS:.0f}s",
        )
        return 1

    quarantine_err = _refuse_if_quarantined(shadow_path)
    if quarantine_err is not None:
        lock.release()
        sys.stderr.write(f"[skill-patch-apply] {quarantine_err}\n")
        return 6

    prev_sig = _install_signal_handlers()
    write_error: Optional[BaseException] = None
    try:
        _atomic_shadow_write(shadow_path, new_content)
    except Exception as e:
        write_error = e
    finally:
        _restore_signal_handlers(prev_sig)
        lock.release()
    if write_error is not None:
        sys.stderr.write(
            f"[skill-patch-apply] atomic_shadow_write failed: "
            f"{type(write_error).__name__}: {write_error}\n"
        )
        return 5

    updates = {
        "status": "shadow",
        "applied_at": _dt.datetime.now(_dt.timezone.utc).strftime(
            "%Y-%m-%dT%H:%M:%SZ"
        ),
        "approved_by": fpr or "unknown",
    }
    new_proposal_text = _rewrite_frontmatter(proposal_text, updates)
    proposal_path.write_text(new_proposal_text, encoding="utf-8")

    print(
        f"[skill-patch-apply] create-new-skill shadow "
        f"{shadow_path.relative_to(_REPO_ROOT)} "
        f"(signer fpr={fpr[:16]}…)"
    )
    _emit_audit(
        proposal_id=proposal_id,
        skill_slug=skill_slug,
        commit_sha="",
        signer_fingerprint=fpr,
        shadow_mode=True,
    )
    return 0


def _handle_default_apply(
    proposal_id: str,
    proposal_path: Path,
    proposal_text: str,
    skill_md: Path,
    shadow_path: Path,
    skill_slug: str,
    diff: str,
    fpr: str,
) -> int:
    """Apply the diff to a shadow file under fcntl LOCK_EX.

    PLAN-012 Phase 3 D4 / debate HIGH-3 — serialize writes so no two
    concurrent `skill-patch-apply` invocations can interleave partial
    writes into the shadow. Re-checks quarantine under the lock,
    installs signal handlers so SIGTERM mid-write quarantines the
    partial output.
    """
    current = skill_md.read_text(encoding="utf-8")
    new_content = _apply_unified_diff(current, diff)
    if new_content is None:
        sys.stderr.write(
            f"[skill-patch-apply] could not reconstruct shadow content "
            f"from diff (unsupported diff shape)\n"
        )
        return 5

    # --- Concurrent-safe write --------------------------------------------
    # PLAN-012 Phase 3 D4 / debate HIGH-3. Serialize via fcntl LOCK_EX to
    # prevent interleaved partial writes corrupting the shadow.
    if FileLock is None:  # pragma: no cover
        sys.stderr.write(
            "[skill-patch-apply] _lib.filelock unavailable; refusing write\n"
        )
        return 5
    try:
        lock = FileLock(str(_lock_path_for(shadow_path)),
                        timeout=_LOCK_TIMEOUT_SECS)
        lock.acquire()
    except FileLockTimeout:
        _emit_concurrent_blocked(
            skill_slug=skill_slug, shadow_path=shadow_path,
            reason=f"lock_timeout_after_{_LOCK_TIMEOUT_SECS:.0f}s",
        )
        return 1

    # Re-check quarantine under the lock (a SIGTERM'd peer may have just
    # created one between our pre-flight check and acquire).
    quarantine_err = _refuse_if_quarantined(shadow_path)
    if quarantine_err is not None:
        lock.release()
        sys.stderr.write(f"[skill-patch-apply] {quarantine_err}\n")
        return 6

    prev_sig = _install_signal_handlers()
    write_error: Optional[BaseException] = None
    try:
        _atomic_shadow_write(shadow_path, new_content)
    except Exception as e:
        write_error = e
    finally:
        _restore_signal_handlers(prev_sig)
        lock.release()
    if write_error is not None:
        sys.stderr.write(
            f"[skill-patch-apply] atomic_shadow_write failed: "
            f"{type(write_error).__name__}: {write_error}\n"
        )
        return 5

    updates = {
        "status": "shadow",
        "applied_at": _dt.datetime.now(_dt.timezone.utc).strftime(
            "%Y-%m-%dT%H:%M:%SZ"
        ),
        "approved_by": fpr or "unknown",
    }
    new_proposal_text = _rewrite_frontmatter(proposal_text, updates)
    proposal_path.write_text(new_proposal_text, encoding="utf-8")

    print(
        f"[skill-patch-apply] wrote shadow file "
        f"{shadow_path.relative_to(_REPO_ROOT)} "
        f"(signer fpr={fpr[:16]}…)"
    )
    _emit_audit(
        proposal_id=proposal_id,
        skill_slug=skill_slug,
        commit_sha="",
        signer_fingerprint=fpr,
        shadow_mode=True,
    )
    return 0


def main(argv: Optional[List[str]] = None) -> int:
    """Verify and apply a skill-patch proposal.

    Entry point for ``.claude/scripts/skill-patch-apply.py``. Dispatches
    between force-recover, promote, and default apply modes after
    verifying the GPG signature + confirm phrase. See helper functions
    ``_load_and_verify_proposal``, ``_handle_force_recover``,
    ``_handle_promote``, and ``_handle_default_apply`` for each mode's
    detailed preconditions and exit codes.
    """
    parser = _build_main_parser()
    args = parser.parse_args(argv)

    if os.environ.get("CEO_SOTA_DISABLE") == "1":
        sys.stderr.write("[skill-patch-apply] CEO_SOTA_DISABLE=1 — no-op\n")
        return 0

    rc, proposal_path, fm, proposal_text, fpr = _load_and_verify_proposal(args)
    if rc is not None:
        return rc
    assert proposal_path is not None and fm is not None  # narrow for mypy

    # PLAN-047 P03: branch on proposal_type. Default path (absence or
    # explicit ``skill-patch``) keeps the original diff flow. New value
    # ``create-new-skill`` ships a whole-file NEW SKILL.md body.
    proposal_type = (fm.get("proposal_type", "") or "skill-patch").strip()

    if proposal_type == "create-new-skill":
        # NEW skill flow: derive (tier, slug) from proposal_target,
        # locate shadow path under target dir, dispatch.
        proposal_target = fm.get("proposal_target", "").strip()
        parsed = _parse_proposal_target(proposal_target)
        if parsed is None:
            sys.stderr.write(
                f"[skill-patch-apply] create-new-skill: proposal_target "
                f"{proposal_target!r} has unsupported shape. Expected "
                f".claude/skills/{{core|frontend|domains/<d>/skills}}"
                f"/<slug>/SKILL.md\n"
            )
            return 5
        _, skill_slug = parsed
        if not _SKILL_SLUG_RE.fullmatch(skill_slug):
            sys.stderr.write(
                f"[skill-patch-apply] create-new-skill: skill_slug "
                f"{skill_slug!r} fails regex [a-z][a-z0-9-]{{1,63}}\n"
            )
            return 5
        skill_md = _resolve_create_new_skill_target(proposal_target)
        if skill_md is None:
            sys.stderr.write(
                f"[skill-patch-apply] create-new-skill: refusing to write "
                f"outside .claude/skills/ (target={proposal_target!r})\n"
            )
            return 5
        body = _extract_markdown_block(proposal_text)
        if body is None:
            sys.stderr.write(
                f"[skill-patch-apply] create-new-skill: proposal missing "
                f"single ```markdown fence OR body exceeds "
                f"{_CREATE_NEW_SKILL_MAX_BYTES} bytes\n"
            )
            return 5
        shadow_path = skill_md.parent / f"{skill_md.name}.shadow.md"

        # Force-recover sozinho: clear quarantine (existing semantic).
        # Force-recover + promote: skip 7-day soak (§D1 pre-authorized).
        if args.force_recover and not args.promote:
            return _handle_force_recover(shadow_path)

        quarantine_err = _refuse_if_quarantined(shadow_path)
        if quarantine_err is not None:
            sys.stderr.write(f"[skill-patch-apply] {quarantine_err}\n")
            return 6

        if args.promote:
            # For create-new-skill, sha256_of_diff may be absent in the
            # frontmatter (whole-file body, not a diff). Fall back to
            # empty string for the commit trailer.
            sha256 = fm.get("sha256_of_diff", "")
            return _handle_promote(
                proposal_id=args.proposal,
                proposal_path=proposal_path,
                proposal_text=proposal_text,
                fm=fm,
                skill_md=skill_md,
                shadow_path=shadow_path,
                skill_slug=skill_slug,
                fpr=fpr,
                sha256=sha256,
                skip_soak=args.force_recover,
            )

        return _handle_create_new_skill_shadow(
            proposal_id=args.proposal,
            proposal_path=proposal_path,
            proposal_text=proposal_text,
            skill_md=skill_md,
            shadow_path=shadow_path,
            skill_slug=skill_slug,
            body=body,
            fpr=fpr,
        )

    # --- Default (diff-over-existing) path ---------------------------------
    skill_slug = fm.get("skill_slug", "")
    skill_md = _resolve_skill_md(skill_slug) if skill_slug else None
    if skill_md is None:
        sys.stderr.write(
            f"[skill-patch-apply] cannot locate SKILL.md for "
            f"skill_slug={skill_slug!r}\n"
        )
        return 5

    diff = _extract_diff_block(proposal_text)
    if diff is None:
        sys.stderr.write(
            f"[skill-patch-apply] proposal missing ```diff block\n"
        )
        return 5

    sha256 = fm.get("sha256_of_diff", "")
    # Name it as <SKILL.md>.shadow.md — the task spec asks for this
    # sibling file rather than <SKILL.md>.shadow.
    shadow_path = skill_md.parent / f"{skill_md.name}.shadow.md"

    # --- FORCE-RECOVER MODE -----------------------------------------------
    # Sozinho: clear quarantine (legacy semantic).
    # Combinado com --promote: skip 7-day soak (§D1 pre-authorized).
    # Gated on the same Owner sign-off (sig + confirm) as apply, so an
    # attacker cannot clear a quarantine they induced.
    if args.force_recover and not args.promote:
        return _handle_force_recover(shadow_path)

    # --- Pre-flight: refuse on quarantine --------------------------------
    quarantine_err = _refuse_if_quarantined(shadow_path)
    if quarantine_err is not None:
        sys.stderr.write(f"[skill-patch-apply] {quarantine_err}\n")
        return 6

    # --- PROMOTE MODE ------------------------------------------------------
    if args.promote:
        return _handle_promote(
            proposal_id=args.proposal,
            proposal_path=proposal_path,
            proposal_text=proposal_text,
            fm=fm,
            skill_md=skill_md,
            shadow_path=shadow_path,
            skill_slug=skill_slug,
            fpr=fpr,
            sha256=sha256,
            skip_soak=args.force_recover,
        )

    # --- DEFAULT MODE (apply to shadow) ------------------------------------
    return _handle_default_apply(
        proposal_id=args.proposal,
        proposal_path=proposal_path,
        proposal_text=proposal_text,
        skill_md=skill_md,
        shadow_path=shadow_path,
        skill_slug=skill_slug,
        diff=diff,
        fpr=fpr,
    )


if __name__ == "__main__":
    sys.exit(main())
