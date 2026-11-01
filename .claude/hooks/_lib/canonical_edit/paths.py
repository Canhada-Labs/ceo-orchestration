"""Canonical target normalization, matching and sentinel discovery.

Functions are bound to the owning hook namespace by ``bind``. This keeps
its injectable dependencies and per-import state on the public hook.
"""
from __future__ import annotations

__all__ = ('_normalize_candidate_value', '_extract_mcp_target_paths', '_repo_rels', '_matches_canonical_guard', '_canonical_rel', '_is_canonical', '_fnmatch_segments', '_match_segments', '_find_sentinels')


def _normalize_candidate_value(value: str) -> str:
    """PLAN162_FIX_7 (finding #7) — turn a ``file://`` URI into a path.

    ``uri`` is one of ``_MCP_WRITE_PATH_KEYS``, but HEAD handed the value
    to ``Path()`` verbatim: ``file:///repo/.claude/settings.json`` became
    a RELATIVE path whose first segment is ``file:``, resolved against the
    process CWD, landed outside the repo root and classified
    NON-canonical — so the edit sailed through ungated even though the
    MCP server would write the guarded file.

    Normalizing in ONE place (the single function that builds candidates)
    was the form both debate lanes accepted; the alternative — treating an
    un-interpretable value as fail-CLOSED — is left to the callers, which
    already fail-CLOSE on a candidate they cannot classify.

    Only LOCAL file URIs are rewritten (empty or ``localhost`` authority).
    A ``file://remote-host/...`` URI is NOT a local path and is returned
    untouched, as is any value with a different scheme. A percent-escape
    that decodes to an embedded NUL is likewise returned untouched — a
    path the OS cannot open is not made more gate-able by decoding it.
    """
    if len(value) < 7 or value[:7].lower() != "file://":
        return value
    try:
        from urllib.parse import unquote, urlsplit  # noqa: PLC0415
        parts = urlsplit(value)
        if parts.scheme.lower() != "file":
            return value
        if (parts.netloc or "").lower() not in ("", "localhost"):
            return value  # remote authority: not a local filesystem path
        decoded = unquote(parts.path)
        if not decoded or "\x00" in decoded:
            return value
        return decoded
    except Exception:
        return value



def _extract_mcp_target_paths(tool_input: dict) -> List[str]:
    """Best-effort extraction of canonical-edit candidate paths from MCP
    tool input. Returns a list of string paths whose canonical status
    will be checked. Non-string / non-path-shaped values are ignored.

    PLAN-065 Layer A — closes S81-tris gap. Custom MCP tools previously
    bypassed `check_canonical_edit.py` because their tool_name does not
    match the legacy `Edit|Write|MultiEdit` matcher. Settings.json now
    routes `mcp__.*` here too; this function maps the heterogeneous
    MCP tool input shapes to a flat list of candidate paths.
    """
    if not isinstance(tool_input, dict):
        return []
    paths: List[str] = []
    for key in _MCP_WRITE_PATH_KEYS:
        value = tool_input.get(key)
        if isinstance(value, str) and value:
            # Length cap defense (Sec MF-7 mirror): reject pathological
            # input early. Real MCP paths are <4 KiB; absurdly long
            # values are likely adversarial. The cap is applied to the
            # RAW value (PLAN162_FIX_7 normalization can only shorten it).
            if len(value) <= 4096:
                paths.append(_normalize_candidate_value(value))
        elif isinstance(value, list):
            for item in value:
                if isinstance(item, str) and item and len(item) <= 4096:
                    paths.append(_normalize_candidate_value(item))
    return paths



def _repo_rels(path_str: str, repo_root: Path) -> List[str]:
    """All repo-relative POSIX forms of ``path_str`` (0, 1, or 2 entries).

    PLAN160_FIX_D (finding D — relative-path classification bypass,
    most-restrictive-wins): a RELATIVE path is resolved against BOTH the
    process CWD (historical anchoring) AND ``repo_root``. A canonical file
    addressed by a relative ``path_str`` from a CWD outside the repo
    previously resolved outside ``repo_root`` → ``relative_to`` raised →
    treated non-canonical → the unsigned edit sailed through ungated.
    Yielding the repo_root-anchored form too closes that bypass. Absolute
    paths yield ONLY the CWD-form (``repo_root / p`` discards ``repo_root``
    when ``p`` is absolute), so classification AND per-call resolve cost
    stay byte-identical on the Edit/Write hot path. Returned in anchoring
    order (CWD-form first) so callers pick the historical rel when both
    land inside the repo (the CWD==repo_root common case → one entry).

    TOTAL by construction (PLAN-160 finding-A blocker, codex + security
    pair-rail): every resolve is caught with a BROAD ``except Exception``.
    ``Path.resolve()`` raises ``RuntimeError`` — NOT ``ValueError``/``OSError``
    — on a symlink loop; if that propagated, ``_is_canonical`` would raise,
    and a raising candidate in the multi-candidate scan would route through
    ``decide()`` and the outer handler would fail-OPEN (allow) the whole
    event — a gate-bypass strictly worse than HEAD. An unresolvable path is
    simply non-canonical here (its write fails at the OS anyway); the other
    candidates in a multi-candidate event are still scanned and gated.
    """
    p = Path(path_str)
    try:
        root_resolved = repo_root.resolve()
    except Exception:
        return []
    anchorings = [p]
    if not p.is_absolute():
        anchorings.append(repo_root / p)
    rels: List[str] = []
    for cand in anchorings:
        try:
            rels.append(
                str(cand.resolve().relative_to(root_resolved)).replace(os.sep, "/")
            )
        except Exception:
            continue
    return rels



def _matches_canonical_guard(rel_str: str) -> bool:
    """True if a repo-relative POSIX path matches a canonical guard pattern.

    Split out of ``_is_canonical`` (PLAN160_FIX_D) so the identical
    fast-path prefix check + glob loop runs against each candidate path
    anchoring without duplication. PLAN-025 F-perf-004 fast-path preserved.

    PLAN162_FIX_CASEFOLD: the rel and the patterns are compared
    case-INSENSITIVELY (see the module note above) — on APFS the case
    variant addresses the very same inode.
    """
    rel_folded = rel_str.lower()
    # Fast path: check the first path segment against known prefixes.
    first_seg = rel_folded.split("/", 1)[0]
    if first_seg not in _CANONICAL_PREFIXES_FOLDED:
        return False
    for pattern in _CANONICAL_GUARDS_FOLDED:
        if _fnmatch_segments(rel_folded, pattern):
            return True
    return False



def _canonical_rel(path_str: str, repo_root: Path) -> Optional[str]:
    """The repo-relative form of ``path_str`` that matches a canonical
    guard, or ``None`` if no anchoring is canonical.

    PLAN160_FIX_D: single source of truth for canonicality AND the
    repo-relative form used downstream (decide() sentinel matching,
    ``_candidate_is_granted``), so a canonical path is ALWAYS paired with
    the exact rel that classified it — the CWD-anchored ``decide()`` resolve
    could otherwise raise on a repo_root-anchored canonical path and route a
    clean sentinel-block through finding C's fault branch instead.
    """
    for rel_str in _repo_rels(path_str, repo_root):
        if _matches_canonical_guard(rel_str):
            return rel_str
    return None



def _is_canonical(path_str: str, repo_root: Path) -> bool:
    """True if path_str matches one of the canonical guard patterns.

    Thin wrapper over ``_canonical_rel`` (PLAN160_FIX_D). NOTE: this is a
    SHARED predicate (hook Layer-A, the ``--is-canonical`` CLI oracle, and
    ``_candidate_is_granted``); the finding-D change WIDENS classification
    (relative paths from a foreign CWD now classify canonical → more
    blocks), never narrows it — see the ADR.
    """
    return _canonical_rel(path_str, repo_root) is not None



def _fnmatch_segments(path: str, pattern: str) -> bool:
    """Segment-wise glob matcher.

    - ``*`` matches exactly one path segment (any non-slash content).
    - ``**`` matches zero or more path segments (Sprint 9 amendment).
    - Literal segments must match exactly.
    """
    p_parts = path.split("/")
    pat_parts = pattern.split("/")
    return _match_segments(p_parts, pat_parts)



def _match_segments(p_parts: List[str], pat_parts: List[str]) -> bool:
    """Recursive glob with ``**`` zero-or-more support.

    Per-segment patterns support full fnmatch semantics (so
    patterns like *.py, *.yaml, or ADR-*.md match one
    segment with a wildcard stem). ** still means zero-or-more
    segments.
    """
    if not pat_parts:
        return not p_parts
    head, rest = pat_parts[0], pat_parts[1:]
    if head == "**":
        # Zero-or-more: try consuming 0..len(p_parts) segments
        for i in range(len(p_parts) + 1):
            if _match_segments(p_parts[i:], rest):
                return True
        return False
    if not p_parts:
        return False
    # Bare-* is equivalent to fnmatch "*", but we keep the explicit
    # branch for readability. fnmatch.fnmatchcase does case-sensitive
    # glob on a single segment (no "/" traversal).
    if head == "*" or fnmatch.fnmatchcase(p_parts[0], head):
        return _match_segments(p_parts[1:], rest)
    return False



def _find_sentinels(repo_root: Path) -> List[Path]:
    """Find all valid Architect sentinel files in the repo.

    PLAN-045 Wave 1 F-01-04: reject any sentinel that is a symlink or
    whose immediate parent directory is a symlink. Mirrors the
    ``_validate_skill_reference`` hardening pattern (ADR-051 sub-check
    5). Silently drops symlinked entries — an attacker who plants
    ``PLAN-EVIL/architect/round-1/approved.md -> /tmp/evil`` no longer
    gets their sentinel considered.
    """
    base = repo_root / ".claude" / "plans"
    if not base.is_dir():
        return []
    # PLAN-085 Wave E.1 — explicit pattern union + grandfather allowlist
    # (R1 Sec-3). NO catch-all wildcard. Novel architect/* subdirs not
    # listed below are treated as ORPHAN, NOT TRUSTED.
    _PATTERNS = (
        "PLAN-*/architect/round-*/approved.md",
        "PLAN-*/architect/wave-0a/approved.md",      # PLAN-083 grandfather
        "PLAN-*/architect/wave-0b/approved.md",      # PLAN-083 grandfather
        "PLAN-*/architect/wave-1-2/approved.md",     # PLAN-083 grandfather
        "PLAN-*/architect/wave-minus-1/approved.md", # PLAN-083 grandfather
        "PLAN-*/staging/review/approved.md",         # PLAN-083 grandfather
        "PLAN-*/approved.md",                        # plan-root sentinels
        "PLAN-*/wave-*-approved.md",                 # S109 wave-N-approved.md
        "PLAN-*/approved-amendment-*.md",            # E.5 amendment files
        "PLAN-*/audit-v2/architect/round-*/approved.md",  # PLAN-044 audit-v2 historical
    )
    seen: set = set()
    candidates: list = []
    for pat in _PATTERNS:
        for c in sorted(base.glob(pat)):
            if c not in seen:
                seen.add(c)
                candidates.append(c)
    # PLAN162_FIX_2 (PLAN-162 finding #2, consensus C9) — the symlink
    # rejection must be DEPTH-INDEPENDENT.
    #
    # HEAD checked exactly three levels (``p``, ``p.parent``,
    # ``p.parent.parent``), hard-coded to the depth of
    # ``PLAN-*/architect/round-*/approved.md``. The ``PLAN-*`` segment one
    # level further up was never checked, so
    # ``.claude/plans/PLAN-EVIL -> /tmp/evil`` smuggled a foreign
    # ``architect/round-1/approved.md`` into the TRUSTED sentinel set —
    # every intermediate directory is a real directory INSIDE the link
    # target, so all three checks passed.
    #
    # "Cover the real depth of the patterns" was rejected in debate: it
    # re-couples the guard to the pattern list, and the next 6-segment
    # pattern silently reopens the hole (the dead-gate class this file has
    # already suffered twice). Instead we do both depth-free checks:
    #
    #   (a) walk EVERY segment from ``p`` up to (excluding) ``base``,
    #       rejecting any symlinked component; and
    #   (b) assert ``realpath(p)`` stays under ``realpath(base)``, which
    #       also catches a symlink that resolves out of the tree without a
    #       symlinked component we happen to walk.
    #
    # RESIDUAL, deliberately not closed here: a symlink at ``base`` itself
    # (``.claude/plans``) satisfies both forms — (a) excludes base and (b)
    # resolves base through the same link. Named in the W1 instrument;
    # pinning today's behaviour there would pin a bypass.
    try:
        base_rp = os.path.realpath(str(base))
    except Exception:
        return []
    safe: List[Path] = []
    for p in candidates:
        try:
            # (a) depth-free ancestor walk: p, then every directory above
            # it, up to but not including `base`. A bound of 64 hops is a
            # runaway guard, never a semantic limit (real sentinels sit 2-4
            # levels under base).
            node = p
            contained = False
            for _hop in range(64):
                if node.is_symlink():
                    break
                parent = node.parent
                if parent == node:  # walked past the filesystem root
                    break
                if parent == base:
                    contained = True
                    break
                node = parent
            if not contained:
                continue
            # (b) realpath containment — independent of how many segments
            # the pattern happens to have.
            p_rp = os.path.realpath(str(p))
            if not p_rp.startswith(base_rp + os.sep):
                continue
        except OSError:
            continue
        safe.append(p)
    return safe
