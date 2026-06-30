#!/usr/bin/env python3
"""Blocking persistent-instructions validator (PLAN-133 G1 + G3 / Goose-harvest).

G1 = single trusted MOIM channel (``.claude/instructions.md`` at the project root).
G3 = the SAME blocking engine, applied to HIERARCHICAL per-directory
``.claude/hints.md`` files discovered repo-root-and-below (no parent traversal,
skip vendored/third_party). Both share this one ``_lib/`` module (per PLAN-133
§3.1 they serialize on it).
"""

from __future__ import annotations

import os
import re
import unicodedata
from dataclasses import dataclass
from pathlib import Path
from typing import Dict, List, Optional, Tuple

# ------------------------------------------------------------------ G1 base ---
MAX_INSTRUCTIONS_BYTES = 64 * 1024

VERDICT_REASONS = frozenset(
    {"ok", "injection_pattern", "oversize", "outside_project_dir", "other"}
)
VERDICT_DECISIONS = frozenset({"allow", "block"})

_BLOCK_PATTERNS = (
    re.compile(
        r"\bignore\s+(?:all\s+)?(?:the\s+)?(?:above|previous|prior|earlier|preceding)"
        r"\s+(?:instructions?|prompts?|rules?)\b",
        re.IGNORECASE,
    ),
    re.compile(
        r"\bdisregard\s+(?:all\s+)?(?:the\s+)?(?:above|previous|prior|system)\b",
        re.IGNORECASE,
    ),
    re.compile(
        r"\bforget\s+(?:everything|all|your)\s+(?:above|before|prior|instructions?)\b",
        re.IGNORECASE,
    ),
    re.compile(
        r"\boverride\s+(?:the\s+)?(?:system|previous|safety|default)\s+"
        r"(?:prompt|instructions?|rules?)\b",
        re.IGNORECASE,
    ),
    re.compile(
        r"\b(?:reveal|print|dump|leak|export)\s+(?:me\s+)?(?:your|the)\s+"
        r"(?:system\s+)?(?:prompt|instructions?|context)\b",
        re.IGNORECASE,
    ),
    re.compile(
        r"\bas\s+(?:the\s+)?(?:owner|admin|root|ceo)[,.]?\s+I\s+(?:hereby\s+)?"
        r"(?:authorize|authorise|allow|permit)\b",
        re.IGNORECASE,
    ),
    re.compile(r"\byou\s+are\s+now\b", re.IGNORECASE),
    re.compile(r"<\s*system[-_ ]?reminder\s*>", re.IGNORECASE),
    re.compile(r"<\s*user[-_ ]?prompt[-_ ]?submit[-_ ]?hook\s*>", re.IGNORECASE),
    re.compile(r"<\|im_start\|>"),
    re.compile(r"<\|im_end\|>"),
    re.compile(r"\[INST\]"),
    re.compile(r"<<SYS>>"),
)

_BIDI_ZW_RE = re.compile(
    "[​-‏‪-‮⁠-⁯﻿"
    "\U000e0000-\U000e007f]"
)


@dataclass(frozen=True)
class Verdict:
    decision: str
    reason: str
    family_hits: int
    bytes_scanned: int

    def to_audit_fields(self) -> Dict[str, object]:
        decision = self.decision if self.decision in VERDICT_DECISIONS else "block"
        reason = self.reason if self.reason in VERDICT_REASONS else "other"
        return {
            "decision": decision,
            "reason": reason,
            "family_hits": int(self.family_hits),
            "bytes_scanned": int(self.bytes_scanned),
        }


def _allow() -> Verdict:
    return Verdict(decision="allow", reason="ok", family_hits=0, bytes_scanned=0)


def resolve_trusted_path(
    filename: str,
    *,
    project_dir: Optional[str],
) -> Optional[Path]:
    if not project_dir or not filename:
        return None
    try:
        if Path(filename).is_absolute():
            return None
        root = Path(project_dir).resolve()
        candidate = (root / filename).resolve()
        candidate.relative_to(root)
    except (ValueError, OSError, RuntimeError):
        return None
    return candidate


def validate_text(text: str) -> Verdict:
    try:
        if text is None:
            return _allow()
        if not isinstance(text, str):
            try:
                text = str(text)
            except Exception:
                return _allow()
        encoded = text.encode("utf-8", errors="replace")
        nbytes = len(encoded)
        if nbytes > MAX_INSTRUCTIONS_BYTES:
            return Verdict(
                decision="block", reason="oversize", family_hits=0, bytes_scanned=nbytes
            )
        normalized = unicodedata.normalize("NFKC", text)
        if _BIDI_ZW_RE.search(text):
            return Verdict(
                decision="block", reason="injection_pattern", family_hits=1,
                bytes_scanned=nbytes,
            )
        hits = 0
        for pat in _BLOCK_PATTERNS:
            try:
                if pat.search(normalized):
                    hits += 1
            except Exception:
                continue
        if hits > 0:
            return Verdict(
                decision="block", reason="injection_pattern", family_hits=hits,
                bytes_scanned=nbytes,
            )
        return Verdict(
            decision="allow", reason="ok", family_hits=0, bytes_scanned=nbytes
        )
    except Exception:  # pragma: no cover
        return _allow()


def validate_trusted_file(
    filename: str,
    *,
    project_dir: Optional[str],
) -> Verdict:
    try:
        path = resolve_trusted_path(filename, project_dir=project_dir)
        if path is None:
            return Verdict(
                decision="allow", reason="outside_project_dir", family_hits=0,
                bytes_scanned=0,
            )
        # SECURITY (PLAN-133 G1): reject a symlinked MOIM file. resolve_trusted_path
        # already resolves + containment-checks (an escaping symlink → None above),
        # but a symlinked file that resolves to a sibling INSIDE the root would still
        # pass; reject it outright so the single trusted MOIM channel is a real file.
        try:
            if project_dir and (Path(project_dir) / filename).is_symlink():
                return Verdict(
                    decision="allow", reason="outside_project_dir", family_hits=0,
                    bytes_scanned=0,
                )
        except (OSError, RuntimeError, ValueError):
            return _allow()
        if not path.is_file():
            return _allow()
        try:
            size = path.stat().st_size
        except OSError:
            return _allow()
        if size > MAX_INSTRUCTIONS_BYTES:
            return Verdict(
                decision="block", reason="oversize", family_hits=0,
                bytes_scanned=int(size),
            )
        try:
            with path.open("rb") as fh:
                raw = fh.read(MAX_INSTRUCTIONS_BYTES + 1)
        except OSError:
            return _allow()
        if len(raw) > MAX_INSTRUCTIONS_BYTES:
            return Verdict(
                decision="block", reason="oversize", family_hits=0,
                bytes_scanned=len(raw),
            )
        text = raw.decode("utf-8", errors="replace")
        return validate_text(text)
    except Exception:  # pragma: no cover
        return _allow()


# ----------------------------------------------- G3 hierarchical discovery ---

# Per-directory hint filename (the G3 channel). Distinct from the single G1
# MOIM file (.claude/instructions.md): G3 hints live in EACH directory's
# .claude/ subdir and are merged in shallow-to-deep order at boot.
HINT_FILENAME = ".claude/hints.md"

# Vendored / third-party / build dirs whose nested .claude/hints.md must NOT be
# honored (an attacker who lands a hints.md inside a pulled npm package /
# vendored module must not reprogram the agent). Mirrors the framework's
# existing _LOC_SKIP_DIRS convention (detect-repo-profile.py) + adds the
# explicit "third_party"/"third-party" forms.
HINT_SKIP_DIRS = frozenset(
    {
        "node_modules",
        "vendor",
        "vendored",
        "third_party",
        "third-party",
        ".venv",
        "venv",
        "site-packages",
        "__pycache__",
        ".git",
        ".pytest_cache",
        "dist",
        "build",
        "target",
        ".next",
        ".nuxt",
        ".cache",
        ".tox",
        "coverage",
        ".gradle",
        ".idea",
        ".mypy_cache",
    }
)

# Bound the descent so a pathological tree (deep monorepo / symlink fan-out)
# can never make boot O(huge). Repo-root-and-below only.
MAX_HINT_DIR_DEPTH = 25
MAX_HINT_FILES = 64

# Closed-enum provenance reason per loaded hint (mirrors VERDICT_REASONS plus
# the discovery-specific "skipped_vendored" / "depth_capped" states). audit_emit
# keeps a literal copy; drift is caught by the parity test.
HINT_PROVENANCE_REASONS = frozenset(
    {"loaded", "blocked_injection", "blocked_oversize", "read_error", "other"}
)


@dataclass(frozen=True)
class HintResult:
    """Closed-enum provenance for ONE discovered hint file.

    ``rel_dir_depth`` is the integer directory depth below the repo root (an
    INTEGER, never the path text). ``reason`` is a closed enum. The file body,
    the matched line, and the absolute path are NEVER carried — only the
    repo-relative directory depth + closed enum + integer counts. This is the
    ONLY thing the G3 emitter persists (no-value-echo).
    """

    reason: str            # closed enum: HINT_PROVENANCE_REASONS
    rel_dir_depth: int     # integer depth below repo root (NOT the path text)
    family_hits: int
    bytes_scanned: int

    def to_audit_fields(self) -> Dict[str, object]:
        reason = self.reason if self.reason in HINT_PROVENANCE_REASONS else "other"
        return {
            "reason": reason,
            "rel_dir_depth": int(self.rel_dir_depth),
            "family_hits": int(self.family_hits),
            "bytes_scanned": int(self.bytes_scanned),
        }


def _is_under_skip_dir(rel: Path) -> bool:
    """True if ANY segment of the repo-relative dir is a vendored/skip dir."""
    for part in rel.parts:
        if part in HINT_SKIP_DIRS:
            return True
    return False


def discover_hint_dirs(project_dir: Optional[str]) -> List[Path]:
    """Walk the repo root-and-below for directories that hold ``.claude/hints.md``.

    SECURITY (PLAN-133 §2 / G3 must-fix):
      - root is the resolved CLAUDE_PROJECT_DIR — never env-text path; the walk
        is strictly **repo-root-and-below** (no parent traversal — os.walk only
        descends, and every yielded dir is re-checked for root containment).
      - vendored / third_party / build dirs are pruned (HINT_SKIP_DIRS) so a
        hints.md inside a pulled package can never reprogram the agent.
      - bounded depth (MAX_HINT_DIR_DEPTH) + file count (MAX_HINT_FILES) so a
        pathological tree can't make boot O(huge).
      - symlinked dirs are NOT followed (followlinks=False) — a symlink that
        escapes the root is ignored.

    Returns the list of directories (each containing ``.claude/hints.md``),
    ordered SHALLOW-first (root -> deep) so a deeper hint is applied AFTER (and
    can refine) a shallower one. Never raises; returns [] on any infra error.
    """
    out: List[Path] = []
    if not project_dir:
        return out
    try:
        root = Path(project_dir).resolve()
        if not root.is_dir():
            return out
    except (OSError, RuntimeError, ValueError):
        return out

    try:
        for dirpath, dirnames, _filenames in os.walk(
            str(root), topdown=True, followlinks=False
        ):
            try:
                here = Path(dirpath).resolve()
            except (OSError, RuntimeError, ValueError):
                dirnames[:] = []
                continue
            # Containment re-check: never honor a dir outside the root.
            try:
                rel = here.relative_to(root)
            except ValueError:
                dirnames[:] = []
                continue
            depth = len(rel.parts)
            # Prune vendored/skip dirs IN PLACE so os.walk never descends them.
            dirnames[:] = [
                d for d in dirnames
                if d not in HINT_SKIP_DIRS
            ]
            # Depth cap — stop descending past the limit.
            if depth >= MAX_HINT_DIR_DEPTH:
                dirnames[:] = []
            if _is_under_skip_dir(rel):
                continue
            hint = here / HINT_FILENAME
            try:
                if hint.is_file():
                    out.append(here)
                    if len(out) >= MAX_HINT_FILES:
                        break
            except OSError:
                continue
    except Exception:  # pragma: no cover — fail-open on walk infra
        return out

    # Shallow-first deterministic order.
    out.sort(key=lambda p: (len(p.relative_to(root).parts), str(p)))
    return out


def validate_hint_dir(dir_path: Path, *, project_dir: Optional[str]) -> HintResult:
    """Validate the ``.claude/hints.md`` inside ONE discovered directory.

    Re-runs the SAME blocking engine (size cap + injection/bidi/Tag-block scan)
    as G1, but returns a :class:`HintResult` carrying the repo-relative dir
    DEPTH (integer) for provenance — never the path text or the body.

    Fail-OPEN on read/stat infra (a per-file scanner error -> that file is
    skipped, reason ``read_error``, the OTHER hints still load) but fail-CLOSED
    on a positive injection/oversize signal (that hint is BLOCKED, never loaded
    into context). Never raises.
    """
    try:
        root = Path(project_dir).resolve() if project_dir else None
        try:
            rel_depth = (
                len(dir_path.resolve().relative_to(root).parts)
                if root is not None
                else 0
            )
        except (ValueError, OSError, RuntimeError):
            rel_depth = 0
        hint = dir_path / HINT_FILENAME
        # SECURITY (PLAN-133 G3): a symlinked hints.md (or a symlinked path
        # component) can escape CLAUDE_PROJECT_DIR and read an arbitrary file
        # into the agent's context. Before any read: (a) reject a symlinked
        # hint file outright, and (b) resolve the real path and require it to
        # stay contained under the resolved project root (fail-CLOSED on any
        # error or escape). discover_hint_dirs already prunes symlinked DIRS,
        # but validate_hint_dir is also a public entrypoint, so it must guard
        # the file independently.
        try:
            if hint.is_symlink():
                return HintResult(
                    reason="read_error", rel_dir_depth=rel_depth,
                    family_hits=0, bytes_scanned=0,
                )
            if root is not None:
                resolved_hint = hint.resolve()
                resolved_hint.relative_to(root)
        except (OSError, RuntimeError, ValueError):
            return HintResult(
                reason="read_error", rel_dir_depth=rel_depth,
                family_hits=0, bytes_scanned=0,
            )
        try:
            if not hint.is_file():
                return HintResult(
                    reason="read_error", rel_dir_depth=rel_depth,
                    family_hits=0, bytes_scanned=0,
                )
            size = hint.stat().st_size
        except OSError:
            return HintResult(
                reason="read_error", rel_dir_depth=rel_depth,
                family_hits=0, bytes_scanned=0,
            )
        if size > MAX_INSTRUCTIONS_BYTES:
            return HintResult(
                reason="blocked_oversize", rel_dir_depth=rel_depth,
                family_hits=0, bytes_scanned=int(size),
            )
        try:
            with hint.open("rb") as fh:
                raw = fh.read(MAX_INSTRUCTIONS_BYTES + 1)
        except OSError:
            return HintResult(
                reason="read_error", rel_dir_depth=rel_depth,
                family_hits=0, bytes_scanned=0,
            )
        if len(raw) > MAX_INSTRUCTIONS_BYTES:
            return HintResult(
                reason="blocked_oversize", rel_dir_depth=rel_depth,
                family_hits=0, bytes_scanned=len(raw),
            )
        verdict = validate_text(raw.decode("utf-8", errors="replace"))
        if verdict.decision == "block":
            reason = (
                "blocked_oversize" if verdict.reason == "oversize"
                else "blocked_injection"
            )
            return HintResult(
                reason=reason, rel_dir_depth=rel_depth,
                family_hits=int(verdict.family_hits),
                bytes_scanned=int(verdict.bytes_scanned),
            )
        return HintResult(
            reason="loaded", rel_dir_depth=rel_depth, family_hits=0,
            bytes_scanned=int(verdict.bytes_scanned),
        )
    except Exception:  # pragma: no cover — fail-open on infra
        return HintResult(
            reason="read_error", rel_dir_depth=0, family_hits=0, bytes_scanned=0
        )


def validate_hierarchical_hints(
    project_dir: Optional[str],
) -> Tuple[List[HintResult], List[HintResult]]:
    """Discover + validate EVERY nested ``.claude/hints.md`` repo-root-and-below.

    Returns ``(loaded, blocked)`` — both lists of :class:`HintResult`. ``loaded``
    are clean hints (shallow-first) the caller may safely merge into context;
    ``blocked`` are the ones a fail-CLOSED signal rejected (injection/oversize)
    and must NEVER be loaded. ``read_error`` results are dropped from both lists
    (fail-open: a per-file infra error skips just that file). Never raises.
    """
    loaded: List[HintResult] = []
    blocked: List[HintResult] = []
    try:
        for d in discover_hint_dirs(project_dir):
            res = validate_hint_dir(d, project_dir=project_dir)
            if res.reason == "loaded":
                loaded.append(res)
            elif res.reason in ("blocked_injection", "blocked_oversize"):
                blocked.append(res)
            # read_error -> fail-open skip
    except Exception:  # pragma: no cover — fail-open on infra
        return loaded, blocked
    return loaded, blocked
