"""Skill-reference parsing, path validation and content integrity.

Bound to the public hook namespace by this package at import time.
"""
from __future__ import annotations

__all__ = (
    '_is_enabled',
    '_has_valid_frontmatter_with_name',
    '_skill_ref_parse_sentinel',
    '_skill_ref_resolve_path',
    '_skill_ref_validate_unicode',
    '_skill_ref_read_bounded',
    '_skill_ref_validate_frontmatter',
    '_skill_ref_validate_hash_and_redact',
    '_validate_skill_reference',
    '_has_skill_reference',
)


def _is_enabled(env_var: str, default: bool, env: Optional[dict] = None) -> bool:
    """Live read of an env-var toggle with a module default fallback.

    Allows runtime opt-out via env (`CEO_SKILL_REFERENCE_MODE=0`,
    `CEO_NATIVE_SUBAGENTS=0`) without restarting Claude Code.
    `CEO_SOTA_DISABLE=1` is the master kill — overrides everything.
    """
    src_env = env if env is not None else os.environ
    if (src_env.get("CEO_SOTA_DISABLE") or "").strip() == "1":
        return False
    raw = (src_env.get(env_var) or "").strip()
    if raw == "":
        return default
    return raw not in ("0", "false", "FALSE", "False", "no", "off")



def _has_valid_frontmatter_with_name(text: str) -> bool:
    """Stdlib-only frontmatter parser (no PyYAML).

    Returns True iff the file starts with `---` on first line, has a
    closing `---` line, and has at least one `name: <value>` line.
    """
    if not text.startswith("---\n") and not text.startswith("---\r\n"):
        return False
    body_start = 4 if text.startswith("---\n") else 5
    closing = text.find("\n---", body_start)
    if closing == -1:
        return False
    fm_block = text[body_start:closing]
    return bool(re.search(r"^name:\s*\S+", fm_block, flags=re.MULTILINE))



def _skill_ref_parse_sentinel(
    sanitized: str,
) -> Tuple[Optional[Tuple[bool, Optional[str], Optional[str]]], Optional[str], Optional[str]]:
    """Sub-checks 1-2: locate `## SKILL REFERENCE` header + body.

    Returns ``(error_tuple, raw_path, expected_hash)``. On failure,
    ``error_tuple`` is populated and the other fields are None.
    """
    if not _SKILL_REFERENCE_HEADER_RE.search(sanitized):
        return (
            (False, REASON_REFERENCE_MISSING, "no `## SKILL REFERENCE` header"),
            None,
            None,
        )
    body_match = _SKILL_REFERENCE_LINE_RE.search(sanitized)
    if not body_match:
        return (
            (
                False,
                REASON_REFERENCE_MISSING,
                "header found but no `@<path> sha256=<hex>` body",
            ),
            None,
            None,
        )
    return None, body_match.group("path"), body_match.group("hash").lower()



def _skill_ref_resolve_path(
    raw_path: str,
    repo_root: Path,
) -> Tuple[Optional[Tuple[bool, Optional[str], Optional[str]]], Optional[Path], Optional[Path]]:
    """Sub-checks 3-5: resolve path, confirm under skills root, filename = SKILL.md, not symlink.

    Returns ``(error_tuple, candidate, resolved)``. On failure, the
    latter two are None.
    """
    skills_root = (repo_root / ".claude" / "skills").resolve()
    candidate = Path(raw_path)
    if not candidate.is_absolute():
        candidate = repo_root / raw_path
    try:
        resolved = candidate.resolve(strict=True)
    except (FileNotFoundError, OSError) as exc:
        return (
            (False, REASON_REFERENCE_MISSING, f"resolve failed: {exc}"),
            None,
            None,
        )
    try:
        resolved.relative_to(skills_root)
    except ValueError:
        return (
            (
                False,
                REASON_REFERENCE_OUTSIDE_SKILLS_ROOT,
                f"{resolved} not under {skills_root}",
            ),
            None,
            None,
        )
    if resolved.name != "SKILL.md":
        return (
            (
                False,
                REASON_REFERENCE_WRONG_FILENAME,
                f"filename is {resolved.name!r}, expected 'SKILL.md'",
            ),
            None,
            None,
        )
    if candidate.is_symlink():
        return (
            (
                False,
                REASON_REFERENCE_SYMLINK_REFUSED,
                f"{candidate} is a symlink",
            ),
            None,
            None,
        )
    return None, candidate, resolved



def _skill_ref_validate_unicode(
    candidate: Path,
) -> Optional[Tuple[bool, Optional[str], Optional[str]]]:
    """Sub-check 6: NFC unicode normalization. Returns error_tuple or None."""
    raw_str = str(candidate)
    nfc_str = unicodedata.normalize("NFC", raw_str)
    if nfc_str != raw_str:
        return (
            False,
            REASON_REFERENCE_UNICODE_NORMALIZATION_MISMATCH,
            "path not NFC-normalized",
        )
    return None



def _skill_ref_read_bounded(
    resolved: Path,
) -> Tuple[Optional[Tuple[bool, Optional[str], Optional[str]]], Optional[bytes], Optional[str]]:
    """Sub-checks 7-8: size cap + body floor on non-ws bytes.

    Returns ``(error_tuple, content_bytes, decoded_text)``.
    """
    try:
        size = resolved.stat().st_size
    except OSError as exc:
        return (
            (False, REASON_REFERENCE_MISSING, f"stat failed: {exc}"),
            None,
            None,
        )
    if size > _SKILL_REFERENCE_MAX_BYTES:
        return (
            (
                False,
                REASON_REFERENCE_TOO_LARGE,
                f"{size} bytes > {_SKILL_REFERENCE_MAX_BYTES} cap",
            ),
            None,
            None,
        )
    try:
        content_bytes = resolved.read_bytes()
    except OSError as exc:
        return (
            (False, REASON_REFERENCE_MISSING, f"read failed: {exc}"),
            None,
            None,
        )
    try:
        text = content_bytes.decode("utf-8")
    except UnicodeDecodeError as exc:
        return (
            (False, REASON_REFERENCE_MISSING_FRONTMATTER, f"decode: {exc}"),
            None,
            None,
        )
    non_ws = sum(1 for c in text if not c.isspace())
    if non_ws < _SKILL_REFERENCE_MIN_BODY_BYTES:
        return (
            (
                False,
                REASON_REFERENCE_BYTE_FLOOR_UNDERFLOW,
                f"{non_ws} non-ws bytes < {_SKILL_REFERENCE_MIN_BODY_BYTES} floor",
            ),
            None,
            None,
        )
    return None, content_bytes, text



def _skill_ref_validate_frontmatter(
    text: str,
) -> Optional[Tuple[bool, Optional[str], Optional[str]]]:
    """Sub-check 9: YAML frontmatter parseable + has `name:` key."""
    if not _has_valid_frontmatter_with_name(text):
        return (
            False,
            REASON_REFERENCE_MISSING_FRONTMATTER,
            "missing or malformed YAML frontmatter / no `name:` key",
        )
    return None



def _skill_ref_validate_hash_and_redact(
    content_bytes: bytes,
    text: str,
    expected_hash: str,
) -> Optional[Tuple[bool, Optional[str], Optional[str]]]:
    """Sub-checks 10-11: SHA-256 match + redaction scan.

    Per PLAN-025 F-perf-006: SHA-256 on reference-mode skill content
    costs ~1ms for a 5KB skill per invocation. Acceptable at current
    spawn volumes.

    Per Session 32 bugfix: `_redact.redact_secrets` whitespace-collapses
    output, so direct string compare would always mismatch. Instead
    we check for the specific secret-indicator tokens that only appear
    when a pattern matched.
    """
    actual_hash = hashlib.sha256(content_bytes).hexdigest()
    if actual_hash != expected_hash:
        return (
            False,
            REASON_REFERENCE_HASH_MISMATCH,
            f"expected {expected_hash[:8]}..., got {actual_hash[:8]}...",
        )
    redacted = _redact.redact_secrets(text)
    if any(tok in redacted for tok in _SECRET_TOKENS_IN_OUTPUT):
        return (
            False,
            REASON_REFERENCE_REDACTION_HIT,
            "secret pattern detected in skill content",
        )
    return None



def _validate_skill_reference(
    prompt: str,
    repo_root: Optional[Path] = None,
) -> Tuple[bool, Optional[str], Optional[str]]:
    """Validate `## SKILL REFERENCE` sentinel via 11 synchronous sub-checks.

    Refactored (PLAN-050 Phase 1b F-02-03-e) into 6 named helpers for
    readability + per-check test coverage. Same contract: fail-CLOSED
    on any failure, sub-check order preserved from ADR-051 §Synchronous
    validation (sub-check 11 = redaction scan added Session 32;
    PLAN-024 F-hooks-003 doc drift close).
    """
    if not prompt or not isinstance(prompt, str):
        return False, REASON_REFERENCE_MISSING, "empty prompt"

    sanitized = _strip_fenced_and_comments(prompt)

    err, raw_path, expected_hash = _skill_ref_parse_sentinel(sanitized)
    if err:
        return err

    if repo_root is None:
        repo_root = Path(
            os.environ.get("CLAUDE_PROJECT_DIR") or os.getcwd()
        )

    err, candidate, resolved = _skill_ref_resolve_path(raw_path, repo_root)
    if err:
        return err

    err = _skill_ref_validate_unicode(candidate)
    if err:
        return err

    err, content_bytes, text = _skill_ref_read_bounded(resolved)
    if err:
        return err

    err = _skill_ref_validate_frontmatter(text)
    if err:
        return err

    err = _skill_ref_validate_hash_and_redact(
        content_bytes, text, expected_hash
    )
    if err:
        return err

    return True, None, None



def _has_skill_reference(
    prompt: str,
    repo_root: Optional[Path] = None,
) -> bool:
    """Backward-compat wrapper: True iff reference passes all sub-checks."""
    ok, _, _ = _validate_skill_reference(prompt, repo_root=repo_root)
    return ok
