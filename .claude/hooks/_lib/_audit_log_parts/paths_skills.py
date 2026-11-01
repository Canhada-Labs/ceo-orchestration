"""Path resolution and skill extraction declarations."""
from __future__ import annotations

def audit_paths() -> Dict[str, Path]:
    """Resolve the audit log paths from env vars with sensible defaults."""
    home = Path(os.environ.get("HOME") or str(Path.home()))
    default_dir = _rp_state_dir()

    audit_dir = Path(os.environ.get("CEO_AUDIT_LOG_DIR") or str(default_dir))
    env_log = os.environ.get("CEO_AUDIT_LOG_PATH")
    audit_log = Path(env_log) if env_log else audit_dir / "audit-log.jsonl"
    # PLAN-182 W1 rail r1 P1-2: family-follows-log — when the LOG moved via
    # CEO_AUDIT_LOG_PATH, lock + errors follow its resolved parent (same
    # derivation as audit_emit._log_family_dir / audit_hmac), never the
    # default dir. One log, one lock, for every writer.
    family_dir = Path(env_log).resolve().parent if env_log else audit_dir
    audit_err = Path(
        os.environ.get("CEO_AUDIT_LOG_ERR") or str(family_dir / "audit-log.errors")
    )
    audit_lock = Path(
        os.environ.get("CEO_AUDIT_LOG_LOCK")
        or str(family_dir / "audit-log.lock")
    )
    return {
        "dir": audit_dir,
        "log": audit_log,
        "err": audit_err,
        "lock": audit_lock,
    }


def rotate_threshold() -> int:
    """Rotation threshold in bytes, overridable via env for tests."""
    raw = os.environ.get("CEO_AUDIT_LOG_ROTATE_BYTES")
    if raw:
        try:
            return int(raw)
        except ValueError:
            pass
    return DEFAULT_ROTATE_AT_BYTES


# -----------------------------------------------------------------------------
# Field extraction
# -----------------------------------------------------------------------------


def bucket_prompt_length(n: int) -> str:
    """Bucket a prompt length into the fixed histogram buckets."""
    if n < 256:
        return "<256"
    if n < 1024:
        return "<1024"
    if n < 4096:
        return "<4096"
    if n < 16384:
        return "<16384"
    if n < 65536:
        return "<65536"
    return ">=65536"


def _sanitize_prompt(prompt: str) -> Optional[str]:
    """PLAN-065 Phase 1 / Sec MF-7 — NFKC normalize + NUL-strip + length cap.

    Returns the safe text for regex scanning, or None if rejected. Never
    raises. Mirrors ``extract-skill.py._sanitize`` pre-regex hardening.

    Rejections:
    - non-string inputs (defense-in-depth)
    - empty / whitespace-only
    - over ``_MAX_INPUT_CHARS`` code points or ``_MAX_INPUT_BYTES`` UTF-8
    - NUL byte present (post-NFKC)
    """
    if not isinstance(prompt, str):
        return None
    if not prompt or not prompt.strip():
        return None
    if len(prompt) > _MAX_INPUT_CHARS:
        return None
    # NFKC normalize first — homoglyph defense (Cyrillic 'о' U+043E → 'o' folds
    # under NFKC so Cyrillic-only homoglyphs that LOOK like 'o' survive as
    # distinct code-points, then the validator's strict ASCII charset rejects).
    normalized = unicodedata.normalize("NFKC", prompt)
    if "\x00" in normalized:
        return None
    if len(normalized.encode("utf-8", errors="replace")) > _MAX_INPUT_BYTES:
        return None
    return normalized


def _validate_skill_name(name: str) -> bool:
    """Defense-in-depth: re-validate captured skill name post-extract.

    Even though each path's regex already bounds the captured group, we
    re-validate here so a future grammar drift cannot smuggle a
    pathological name out via a regex edge case.

    Path-traversal patterns are denied here: the captured-group grammars
    exclude ``/`` ``..`` ``\\`` already, but we add an explicit anchor.
    """
    if not name or len(name) > _MAX_SKILL_NAME_CHARS:
        return False
    if "/" in name or ".." in name or "\\" in name:
        return False
    if not _SKILL_NAME_CHARSET_RE.match(name):
        return False
    return True


def _path_d_lookup(subagent_type: str) -> str:
    """PLAN-079 Path D — resolve subagent_type to canonical skill name.

    Returns the mapped skill if subagent_type is one of the 5 canonical
    archetypes (``code-reviewer``, ``security-engineer``, ``qa-architect``,
    ``performance-engineer``, ``devops``); otherwise returns ``"unknown"``.

    Normalization: ``strip().lower()`` is applied to mirror the
    archetype-routing precedent in ``check_agent_spawn.py:204``
    (``_extract_archetype_from_payload``). Case-fold is intentional —
    Agent-tool emitters may pass mixed case for the same archetype.

    Defense-in-depth (Sec MF-7):
    - Non-string input rejected (``isinstance(subagent_type, str)``)
    - Raw input length capped at 80 chars BEFORE normalize to bound
      strip/lower allocation cost on the hot audit-hook path (Codex
      G23-04)
    - Post-normalize charset enforced via ``_ARCHETYPE_NAME_RE.fullmatch``
      (anchored both ends) — slash, dot-traversal, NUL, unicode rejected

    Never raises.
    """
    if not isinstance(subagent_type, str):
        return "unknown"
    # G23-04: bound raw length before allocating strip/lower copy.
    # 80 leaves headroom for whitespace + 64-char post-normalize cap.
    if len(subagent_type) > 80:
        return "unknown"
    name = subagent_type.strip().lower()
    if not _ARCHETYPE_NAME_RE.fullmatch(name):
        return "unknown"
    return _ARCHETYPE_TO_SKILL.get(name, "unknown")


def extract_skill(prompt: str, subagent_type: str = "") -> str:
    """Return the skill name extracted from a spawn prompt, or 'unknown'.

    PLAN-065 Phase 1 — 3-path matrix; PLAN-079 — +Path D archetype map.

    Order of precedence:

      A. Format-A inline ``^SKILL: <name>$`` (line-anchored)
      B. Format-B reference
         ``^@.claude/skills/<scope>/<name>/SKILL.md sha256=<64hex>$``
      C. Format-C ``## SKILL CONTENT`` block + ``SKILL LOADED: <name>`` line
      D. Path D (PLAN-079) — ``subagent_type`` ∈ canonical-5 archetypes
         maps to the skill loaded via ``.claude/agents/<name>.md`` per
         ADR-051. Tail fallback only — never overrides an explicit
         Path A/B/C envelope.

    Multi-format prompts: Path A wins (line-order preference per
    PLAN-065 spec). Path D fires only if Paths A/B/C miss AND
    ``subagent_type`` is provided + valid.

    Path D edge case (Codex gate #23 hardened):
    - Fires on TRULY EMPTY ``prompt`` (legitimate empty-body case)
    - Does NOT fire on ``_sanitize_prompt``-rejected prompt (G23-03)
      — rejected prompts may have contained a conflicting `SKILL:`
      envelope we failed to parse; preserving "unknown" surfaces the
      rejection signal in forensic logs
    - Does NOT fire on non-string ``prompt`` (G23-09) — None, False,
      0, list, dict all return "unknown" before reaching Path D

    Sanitization (Sec MF-7) runs once before any path regex on the
    prompt. The ``subagent_type`` input is independently validated
    against ``_ARCHETYPE_NAME_RE`` inside ``_path_d_lookup`` (post-
    `strip().lower()` normalize, with raw-length pre-bound). Never
    raises — returns ``"unknown"`` on any rejection.

    The legacy single-arg signature (``str -> str``) remains supported
    via the default ``subagent_type=""`` arg — pre-PLAN-079 callers
    continue to work unchanged.

    Path D firing rules (Codex gate #23 hardened):

    | prompt              | subagent_type    | result                  |
    |---------------------|------------------|-------------------------|
    | non-string          | any              | "unknown" (G23-09)      |
    | "" (empty)          | canonical-5      | mapped skill (Path D)   |
    | "" (empty)          | other / ""       | "unknown"               |
    | str, sanitize=None  | any              | "unknown" (G23-03)      |
    | str, Path A match   | any              | Path A name (precedence)|
    | str, Path B match   | any              | Path B name (precedence)|
    | str, Path C match   | any              | Path C name (precedence)|
    | str, A/B/C miss     | canonical-5      | mapped skill (Path D)   |
    | str, A/B/C miss     | other / ""       | "unknown"               |
    """
    # Codex G23-09: type-check prompt BEFORE the falsy-short-circuit
    # so non-string prompts (None, False, 0, [], {}) don't silently fall
    # through to Path D fallback via the `if not prompt` branch.
    if not isinstance(prompt, str):
        return "unknown"
    if not prompt:
        # Empty prompt is a legitimate case (archetype dispatch with no
        # user-visible body). Path D may resolve from subagent_type alone.
        if subagent_type:
            return _path_d_lookup(subagent_type)
        return "unknown"
    safe = _sanitize_prompt(prompt)
    if safe is None:
        # Codex G23-03: prompt was REJECTED by Sec MF-7 hardening
        # (oversize, NUL byte, whitespace-only). Do NOT fall back to
        # Path D — the rejected prompt may have contained a different
        # SKILL envelope we failed to parse. Returning the mapped
        # archetype skill here would silently override a conflicting
        # (but malformed) explicit claim. Returning "unknown" preserves
        # the rejection signal so downstream forensics see the parse
        # failure, not a synthesized skill identity.
        return "unknown"

    # Path A — Format-A inline (precedence wins on multi-format).
    m = _SKILL_PATH_A_RE.search(safe)
    if m:
        name = m.group(1)
        if _validate_skill_name(name):
            return name

    # Path B — Format-B reference.
    m = _SKILL_PATH_B_RE.search(safe)
    if m:
        name = m.group(1)
        if _validate_skill_name(name):
            return name

    # Path C — `## SKILL CONTENT` block fallback (legacy).
    if _SKILL_PATH_C_HEADER_RE.search(safe):
        m = _SKILL_PATH_C_LOADED_RE.search(safe)
        if m:
            name = m.group(1)
            if _validate_skill_name(name):
                return name

    # Path D — PLAN-079 canonical archetype → skill mapping (last resort).
    if subagent_type:
        return _path_d_lookup(subagent_type)

    return "unknown"


def has_profile(prompt: str) -> bool:
    """True if the spawn prompt contains an `## AGENT PROFILE` section (spawn discipline marker)."""
    if not prompt:
        return False
    return bool(_PROFILE_RE.search(prompt))


def has_file_assignment(prompt: str) -> bool:
    """True if the spawn prompt contains a `## FILE ASSIGNMENT` section (anti-collision marker)."""
    if not prompt:
        return False
    return bool(_FILE_ASSIGNMENT_RE.search(prompt))


def now_iso_utc() -> str:
    """ISO 8601 UTC timestamp with second precision (e.g. 2026-04-11T13:15:47Z)."""
    return datetime.now(timezone.utc).strftime("%Y-%m-%dT%H:%M:%SZ")


def now_month_slug() -> str:
    """YYYY-MM for the current UTC month — used for rotated filenames."""
    return datetime.now(timezone.utc).strftime("%Y-%m")


# -----------------------------------------------------------------------------
# Entry builder
# -----------------------------------------------------------------------------


