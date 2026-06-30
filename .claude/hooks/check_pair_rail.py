#!/usr/bin/env python3
"""PLAN-075 Phase 0A → PRODUCTION (PLAN-091 A.6 status promotion) — `check_pair_rail.py` PreToolUse hook.

Cross-LLM gate enforcement: when Claude is about to perform an L3+
tool call against a high-blast-radius governance path, this hook
invokes Codex MCP (`mcp__codex__codex`) in **read-only review mode**.
Codex returns a textual review. The hook validates that the review
contains NO write-shaped patches (any `*** Update File:`, unified
diff, or JSON Patch RFC 6902 envelope is rejected — Codex is
read-only by contract here, NOT a coder).

## Hook contract

- **Trigger:** PreToolUse with tool_name in {Edit, Write, MultiEdit,
  NotebookEdit} AND target path classified as L3+ (see
  `_is_l3_plus_path` heuristic).
- **Codex unavailable** (binary missing / connect timeout / spawn
  error) → fail-OPEN with `{decision: allow}` + audit
  `pair_rail_codex_unavailable` (advisory).
- **Codex returns clean review** (no write-shaped patch detected) →
  audit `pair_rail_review_passed` + `{decision: allow}`.
- **Codex returns write-shaped patch** → audit
  `pair_rail_codex_violation` + `{decision: block, reason: ...}`.
- **Sentinel override** (Owner-signed sentinel grants the path) →
  short-circuit allow + audit `pair_rail_sentinel_bypass`.
- **Tool not in scope** (non-write tool, or path not L3+) → silent
  allow.

## L3+ path heuristic (production heuristic — to be replaced by formal
classifier in Phase 1)

A target path is L3+ iff its repo-relative form matches any of:
  - `.claude/hooks/_lib/*.py`
  - `.claude/hooks/check_*.py`
  - `.claude/scripts/local/*`
  - `.claude/policies/*`
  - `SPEC/v1/*`
  - `.github/workflows/*`

Documented in `routing-matrix.md` §L3-classifier.

## Environment

- `CEO_PAIR_RAIL_TIMEOUT_S` (default 30) — Codex invoke wall-clock
  cap. On timeout: fail-OPEN.
- `CEO_PAIR_RAIL_DISABLE` — kill-switch: when set to `1`, hook is a
  no-op (allow). For incident response.
- `CEO_PAIR_RAIL_CODEX_BIN` (test-only) — override path to Codex
  binary; defaults to `codex` on `$PATH`.
- `CEO_PAIR_RAIL_FIXTURE_RESPONSE` (test-only) — preset Codex
  stdout (bypasses subprocess invoke). Test-fixture injection point.

## Fail-open contract

Any unexpected exception → allow. Hook NEVER blocks the user on its
own bug — same invariant as `check_canonical_edit.py`. The L3+
canonical path is still gated downstream by the canonical-edit
hook (sentinel ceremony) so the cross-LLM rail is purely additive
defense-in-depth.

stdlib-only. Python ≥3.9. `from __future__ import annotations`.
"""

from __future__ import annotations

import json
import os
import re
import subprocess
import sys
from pathlib import Path
from typing import Any, Dict, List, Optional, Tuple

# Promoted from staging on 2026-05-09 (S96-cont-2 v1.13.x patch ceremony,
# enforcement_commit __FILLED_AT_COMMIT__).

# PLAN-091 Wave A.6 (W4.1) status promotion: this hook is now formally
# PRODUCTION (not "spike"). The PURE decision module
# `_lib/pair_rail_decide.py` (PLAN-088 W4.1) is the canonical decision
# kernel; this script is the PreToolUse harness shim that bridges hook-IO
# (stdin JSON envelope) to the kernel.
#
# DEFERRED to PLAN-092 (per R1 code-reviewer escalation clause):
#   The R2 P1 SHADOW-invariant "grep -nE 'decision.*block|return.*deny'
#   returns ZERO" requires stripping the current procedural block path
#   (line ~630 where Codex returning a write-shaped patch yields
#   `{decision: block}`). That is a behavior change with adopter-facing
#   blast radius (regression of the v1.13.x enforcement that has been
#   live in production since S96-cont-2). Per ADR-115 anti-churn +
#   PLAN-091 §3 hotfix discipline, behavior changes are out-of-scope.
#   PLAN-092 owns the SHADOW-strip + its ADR. PLAN-091 ships only the
#   docstring promotion + this `_PRODUCTION_PROMOTED_BY_PLAN_091`
#   constant.
#
# See `.claude/plans/PLAN-091/wave-a-pair-rail-defer.md` for the full
# escalation rationale + PLAN-092 handoff contract.
_PRODUCTION_PROMOTED_BY_PLAN_091: bool = True

# ---------------------------------------------------------------------
# L3+ path classifier — spike heuristic (Phase 0A only)
# ---------------------------------------------------------------------

# Glob patterns mirroring `check_canonical_edit._CANONICAL_GUARDS`
# subset. Conservative: matches the smallest blast-radius surface that
# justifies cross-LLM review. Phase 1 replaces this with the formal
# tier-policy classifier (PLAN-071).
_L3_PLUS_GLOB_PATTERNS: Tuple[str, ...] = (
    ".claude/hooks/_lib/*.py",
    ".claude/hooks/_lib/**/*.py",
    ".claude/hooks/check_*.py",
    ".claude/hooks/audit_*.py",
    ".claude/scripts/local/*",
    ".claude/policies/*.yaml",
    ".claude/policies/*.yml",
    "SPEC/v1/*.md",
    ".github/workflows/*.yml",
    ".github/workflows/*.yaml",
    "PROTOCOL.md",
)


def _fnmatch_segments(path: str, pattern: str) -> bool:
    """Segment-wise glob matcher with `*` (one segment) and `**` (zero+).

    Stripped-down port of `check_canonical_edit._fnmatch_segments`.
    """
    import fnmatch as _fn

    p_parts = path.split("/")
    pat_parts = pattern.split("/")

    def _match(p: List[str], pat: List[str]) -> bool:
        if not pat:
            return not p
        head, rest = pat[0], pat[1:]
        if head == "**":
            for i in range(len(p) + 1):
                if _match(p[i:], rest):
                    return True
            return False
        if not p:
            return False
        if head == "*" or _fn.fnmatchcase(p[0], head):
            return _match(p[1:], rest)
        return False

    return _match(p_parts, pat_parts)


def _is_l3_plus_path(path_str: str, repo_root: Path) -> bool:
    """True if path classifies as L3+ per the production heuristic."""
    if not path_str:
        return False
    p = Path(path_str)
    try:
        rel_path = (
            p.resolve().relative_to(repo_root.resolve())
            if p.is_absolute()
            else Path(path_str)
        )
    except (ValueError, OSError):
        # Path outside repo or non-resolvable — not L3+.
        return False
    rel_str = str(rel_path).replace(os.sep, "/")
    for pattern in _L3_PLUS_GLOB_PATTERNS:
        if _fnmatch_segments(rel_str, pattern):
            return True
    return False


# ---------------------------------------------------------------------
# Codex response — write-shaped patch detection (REUSE detectors from
# `_lib/mcp/canonical_guard.py`). Phase 0A spike: inline copies the
# regexes for staging-isolation. Phase 1 will import the canonical
# helpers directly. The regex constants below are intentionally a
# byte-identical subset of the canonical_guard.py originals.
# ---------------------------------------------------------------------

# Codex apply_patch envelope: `*** {Update,Add,Delete} File[:?] <path>`
_CODEX_PATCH_RE = re.compile(
    r"^\*\*\*\s+(Update|Add|Delete|Move|Rename)\s+File:?\s+(.+?)\s*$",
    re.MULTILINE,
)

# Codex `*** Move to:?` directive (R3-01 / R4-01 from PLAN-070).
_CODEX_MOVE_RE = re.compile(
    r"^\*\*\*\s+(?:Move|Rename)\s+to:?\s+(.+?)\s*$",
    re.MULTILINE,
)

# Unified diff: `--- a/foo` / `+++ b/foo`.
_UNIFIED_DIFF_RE = re.compile(
    r"^(?:---|\+\+\+)\s+(?:[ab]/)?(.+?)\s*$", re.MULTILINE,
)

# JSON Patch (RFC 6902) — legacy regex fallback for non-JSON-shape
# bodies that embed JSON-looking substrings. The primary parser uses
# json.loads on bodies that lstrip-start with `[` or `{`.
_JSON_PATCH_PATH_RE = re.compile(
    r'"path"\s*:\s*"(/[^"\\]*(?:\\.[^"\\]*)*)"'
)

# ReDoS defense: cap response size before regex invocation.
_MAX_RESPONSE_BYTES = 4 * 1024 * 1024  # 4 MiB
_MAX_RESPONSE_LINES = 200_000

# PLAN-142: hard cap on bytes read back from the helper-built last-message
# output file (the untrusted binary is the WRITER — TOCTOU). The redactor
# independently truncates at 256 KB; this is a defense-in-depth read-time cap
# so an oversize / disk-filling file cannot be slurped whole before redaction.
# Oversize (file larger than this) → ADVISORY degradation, never raise.
_MAX_OUTPUT_FILE_BYTES: int = 1 * 1024 * 1024  # 1 MiB


def _detect_write_shaped_patch(response_text: str) -> Optional[str]:
    """Detect any write-shaped patch in a Codex review response.

    Returns the matched grammar tag (`codex_apply_patch`, `unified_diff`,
    `codex_move`, `json_patch`) on first detection, or None if response
    is clean. Order is: Codex envelope → unified diff → JSON patch.

    Defense:
    - Length cap (4 MiB) — pathological responses skipped (treated as
      clean by production heuristic; future revision should fail-CLOSED).
    - Line cap (200k) — bound regex iteration.
    - All regexes anchored with `^...$` (multiline) — no nested
      quantifiers susceptible to ReDoS.
    """
    if not isinstance(response_text, str) or not response_text:
        return None
    if len(response_text) > _MAX_RESPONSE_BYTES:
        # Spike: treat oversize as clean (advisory). Production note:
        # ADR-110 PROPOSED Phase 1 should fail-CLOSED here.
        return None
    # Cap line count via early exit on findall-like inspection.
    line_count = response_text.count("\n")
    if line_count > _MAX_RESPONSE_LINES:
        return None

    # Grammar 1a: Codex apply_patch envelope.
    if _CODEX_PATCH_RE.search(response_text) is not None:
        return "codex_apply_patch"

    # Grammar 1b: Codex move directive.
    if _CODEX_MOVE_RE.search(response_text) is not None:
        return "codex_move"

    # Grammar 2: Unified diff. Filter false positives from prose by
    # requiring the second-half marker to also exist (`---` AND `+++`).
    has_minus = re.search(r"^---\s+", response_text, re.MULTILINE) is not None
    has_plus = re.search(r"^\+\+\+\s+", response_text, re.MULTILINE) is not None
    if has_minus and has_plus:
        return "unified_diff"

    # Grammar 3: JSON Patch (RFC 6902). Two-pass:
    # (a) JSON-shape body — try strict json.loads.
    stripped = response_text.lstrip()
    if stripped.startswith(("[", "{")):
        try:
            parsed = json.loads(response_text)
        except (ValueError, TypeError):
            parsed = None
        if isinstance(parsed, list):
            for op in parsed:
                if (
                    isinstance(op, dict)
                    and isinstance(op.get("op"), str)
                    and isinstance(op.get("path"), str)
                    and op["path"].startswith("/")
                    and op["op"] in {"add", "remove", "replace", "move", "copy"}
                ):
                    return "json_patch"
        elif isinstance(parsed, dict):
            # Single op object (uncommon but valid).
            if (
                isinstance(parsed.get("op"), str)
                and isinstance(parsed.get("path"), str)
                and parsed["path"].startswith("/")
                and parsed["op"] in {"add", "remove", "replace", "move", "copy"}
            ):
                return "json_patch"
    # (b) Legacy regex fallback for embedded JSON-Patch fragments in
    # mixed prose.
    if (
        '"op"' in response_text
        and '"path"' in response_text
        and _JSON_PATCH_PATH_RE.search(response_text) is not None
    ):
        return "json_patch"

    return None


# ---------------------------------------------------------------------
# Codex MCP invoke — subprocess wrapper. Spike-only; Phase 1 replaces
# with the typed `_lib/adapters/codex.py` adapter.
# ---------------------------------------------------------------------


class CodexUnavailable(Exception):
    """Raised when Codex binary is missing or invoke fails non-recoverably."""


class CodexTimeout(Exception):
    """Raised when Codex exceeds the wall-clock cap (CEO_PAIR_RAIL_TIMEOUT_S)."""


class CodexMalformed(Exception):
    """Raised when Codex stdout cannot be parsed as a valid review envelope."""


def _resolve_codex_bin() -> Optional[str]:
    """Return path to Codex binary, or None if not on PATH.

    Test-friendly: env `CEO_PAIR_RAIL_CODEX_BIN` overrides discovery.
    """
    override = os.environ.get("CEO_PAIR_RAIL_CODEX_BIN")
    if override:
        return override if Path(override).exists() else None
    # Lightweight PATH discovery — `which` semantics without subprocess.
    for entry in os.environ.get("PATH", "").split(os.pathsep):
        candidate = Path(entry) / "codex"
        if candidate.exists() and os.access(candidate, os.X_OK):
            return str(candidate)
    return None


def _build_codex_prompt(
    tool_name: str, file_path: str, proposed_content: str
) -> str:
    """Build the read-only review prompt sent to Codex.

    Production contract: prompt asks Codex to review for governance issues
    + return REVIEW-ONLY. ANY `*** Update File:` / unified diff /
    JSON-Patch in the response → automatic violation (regardless of
    intent — the hook contract is purely structural).
    """
    # Truncate proposed_content for prompt size sanity. Phase 1 will
    # use chunked streaming; spike caps at 32 KiB.
    capped = proposed_content[:32 * 1024] if proposed_content else ""
    return (
        f"PAIR-RAIL READ-ONLY REVIEW (PLAN-075 Phase 0A spike)\n\n"
        f"Tool: {tool_name}\n"
        f"Target path: {file_path}\n\n"
        "You are a READ-ONLY reviewer. Do NOT emit any patch, diff, "
        "apply_patch envelope, or JSON-Patch op.\n"
        "If you would change the file, describe the change in PROSE "
        "ONLY (no code-fenced patches, no `*** Update File:` lines, "
        "no `--- a/...` / `+++ b/...` markers).\n\n"
        f"Proposed content (truncated to 32 KiB):\n```\n{capped}\n```"
    )


def _resolve_codex_cli_shape():  # type: ignore[no-untyped-def]
    """Resolve the NEW non-kernel `_lib.codex_cli_shape` module.

    Mirrors the canonical-layout resolution used elsewhere: the
    `.claude/hooks/` dir that houses this file also houses `_lib/`. Returns
    the module or None (fail-OPEN — the caller treats None as
    CodexUnavailable, the ADR-106 fail-open path). NEVER raises.
    """
    try:
        hooks_dir = Path(__file__).resolve().parent
        if str(hooks_dir) not in sys.path:
            sys.path.insert(0, str(hooks_dir))
        from _lib import codex_cli_shape as _shape  # type: ignore
        return _shape
    except Exception:
        return None


def _invoke_codex_review(
    tool_name: str,
    file_path: str,
    proposed_content: str,
    timeout_s: float,
) -> str:
    """Invoke Codex review on codex-cli 0.139.0; return the REDACTED
    last-message file content (one structured JSON object) as a str.

    PLAN-142: the verdict is obtained by having the CLI write ONLY the final
    agent message to a private output file (verified on 0.139: a one-line
    JSON object). ALL flag-shape lives in the NON-kernel
    ``_lib.codex_cli_shape`` helper (D2); this kernel function constructs NO
    argv literals.

    Signature contract UNCHANGED for the consumer: returns a single str.
    But it is now the isolated last agent message (one structured object),
    ALREADY single-pass redacted (R-SEC-1 — redaction at the lowest-trust
    file-read site, before any json.loads in the consumer).

    Test-fixture path: env `CEO_PAIR_RAIL_FIXTURE_RESPONSE` short-circuits
    the subprocess invoke and is treated as the already-isolated
    last-message string; it is STILL single-pass redacted so fixture tests
    exercise the same ingress trust boundary as a real file read.

    tmpfile TOCTOU hygiene (R-SEC-4 / R-VP-E): a private `mkdtemp(0o700)`
    dir per call; the output file is pre-created O_CREAT|O_EXCL|0o600 at an
    absolute path; after the run we REFUSE to read if it is a symlink / not
    a regular file / not owned by us; `finally:` unlink (output + schema) +
    rmdir on EVERY exit path (success, read error, timeout, exception).

    Degradation matrix → CodexUnavailable / CodexTimeout / CodexMalformed
    (all map to ADVISORY in `_decide`), NEVER raise past the typed wall:
      helper/binary missing, spawn error, non-zero exit → CodexUnavailable;
      timeout → CodexTimeout; output file missing-after-exit-0 / symlink /
      non-regular / not-owned / empty / oversize → CodexMalformed.

    Raises:
        CodexUnavailable, CodexTimeout, CodexMalformed (all consumed as
        ADVISORY fail-open by `_decide`).
    """
    import os as _os  # local alias to avoid any chance of shadowing
    import stat as _stat
    import tempfile as _tempfile

    fixture = _os.environ.get("CEO_PAIR_RAIL_FIXTURE_RESPONSE")
    if fixture is not None:
        # Fixture is the already-isolated last-message string. STILL
        # single-pass redact it so the fixture path exercises the same
        # ingress trust boundary as a real file read (R-SEC-6).
        try:
            from _lib import codex_egress_redact as _redact
            return _redact.redact(fixture)
        except Exception:
            # Un-redactable ingress fixture → malformed so the consumer
            # degrades to ADVISORY rather than parsing un-redacted text.
            # (This is the INGRESS fail-open-to-ADVISORY path, distinct from
            # the ADR-114 fail-CLOSED egress contract below.)
            raise CodexMalformed(
                "codex_egress_redact unavailable on ingress (fixture)"
            )

    codex_bin = _resolve_codex_bin()
    if codex_bin is None:
        raise CodexUnavailable("codex binary not on PATH")

    shape = _resolve_codex_cli_shape()
    if shape is None:
        # The single argv builder is gone/unimportable. Fail-OPEN to
        # ADVISORY rather than hand-roll a (possibly rejected) argv.
        raise CodexUnavailable("codex_cli_shape helper unavailable")

    prompt = _build_codex_prompt(tool_name, file_path, proposed_content)
    # PLAN-084 Wave 0.5 (ADR-114 + AC9 — Codex egress redaction symmetry).
    # proposed_content is raw FILE CONTENT being reviewed (potentially
    # secret-laden source). Redact the OUTGOING prompt BEFORE it leaves the
    # framework. This stays fail-CLOSED per ADR-114: a redactor-import
    # failure REFUSES to ship the prompt.
    try:
        from _lib import codex_egress_redact as _redact
        _egress_bytes = len(prompt.encode("utf-8", "replace")) if isinstance(prompt, str) else 0
        prompt, _egress_findings = _redact.redact_outgoing_with_findings(prompt)
    except ImportError:
        # Fail-CLOSED per ADR-114: refuse to ship unredacted prompt to Codex.
        raise CodexUnavailable("codex_egress_redact unavailable — fail-CLOSED per ADR-114")
    # PLAN-112-FOLLOWUP-codex-egress-proof-telemetry (F-7.9): positive-proof
    # emit on EVERY outbound redaction (empty allowed). Fail-OPEN — wraps ONLY
    # the emit; the redact above stays fail-CLOSED per ADR-114.
    try:
        from _lib import audit_emit as _ae
        _ae.emit_pair_rail_outgoing_redaction_applied(
            signal="outbound",
            match_count=len(_egress_findings),
            bytes_scanned=_egress_bytes,
            callsite="check_pair_rail.py:_invoke_codex_review",
            session_id=os.environ.get("CLAUDE_SESSION_ID", ""),
            project=os.environ.get("CLAUDE_PROJECT_DIR", ""),
        )
    except Exception:
        pass

    # -----------------------------------------------------------------
    # tmpfile setup — we own the dir (0o700) and pre-create the output
    # file with O_EXCL|0o600 to win the symlink race; the CLI writes to it
    # by absolute path. A sibling schema file (written by US, not the
    # untrusted binary) carries the CLI-enforced verdict shape.
    # -----------------------------------------------------------------
    tmp_dir = _tempfile.mkdtemp(prefix="ceo_pairrail_")
    try:
        _os.chmod(tmp_dir, 0o700)
    except OSError:
        pass  # mkdtemp already creates 0o700 on POSIX
    out_path = _os.path.join(tmp_dir, "codex_last_message.json")
    schema_path = _os.path.join(tmp_dir, "codex_verdict_schema.json")

    def _cleanup() -> None:
        """Unlink both tmpfiles + rmdir the dir; never raises."""
        for _p in (out_path, schema_path):
            try:
                _os.unlink(_p)
            except OSError:
                pass
        try:
            _os.rmdir(tmp_dir)
        except OSError:
            pass

    try:
        # Pre-create O_CREAT|O_EXCL|0o600 — if a symlink/file already sits
        # at out_path, O_EXCL fails and we treat it as unavailable.
        try:
            fd = _os.open(out_path, _os.O_CREAT | _os.O_EXCL | _os.O_WRONLY, 0o600)
            _os.close(fd)
        except FileNotFoundError:
            raise CodexUnavailable("tmpdir vanished before pre-create")
        except FileExistsError:
            raise CodexUnavailable("tmpfile pre-create lost O_EXCL race")
        except OSError as e:
            raise CodexUnavailable(f"tmpfile pre-create failed: {type(e).__name__}")

        # Write the CLI-enforced verdict schema to our schema tmpfile
        # (PLAN-142 §3 [P1], R-SEC-2). Best-effort: if the helper cannot
        # serialize it, proceed WITHOUT enforcement (parser-side
        # parse_verdict_strict still validates the shape).
        schema_arg: Optional[str] = None
        try:
            schema_json = shape.verdict_output_schema_json()
            sfd = _os.open(schema_path, _os.O_CREAT | _os.O_EXCL | _os.O_WRONLY, 0o600)
            try:
                _os.write(sfd, schema_json.encode("utf-8"))
            finally:
                _os.close(sfd)
            schema_arg = schema_path
        except Exception:
            schema_arg = None

        # Build argv via the NON-kernel helper. The live-rail shape writes
        # the verdict to our output file and drops usage telemetry (R-SEC-5);
        # we pass only semantic intent — the helper owns flag names, the
        # model id, and the dead-flag migration.
        try:
            cli_args = shape.build_verdict_argv(
                prompt,
                output_file=out_path,
                schema_file=schema_arg,
            )
        except Exception as e:
            raise CodexUnavailable(
                f"codex_cli_shape.build_verdict_argv failed: {type(e).__name__}"
            )
        if not isinstance(cli_args, (list, tuple)) or not cli_args:
            raise CodexUnavailable("codex_cli_shape returned empty argv")

        cmd = [codex_bin] + list(cli_args)

        # Invoke. The prompt is the trailing positional built by the helper;
        # close stdin via input="" so the child never blocks on a pipe.
        try:
            proc = subprocess.run(
                cmd,
                input="",
                capture_output=True,
                text=True,
                timeout=timeout_s,
                check=False,
            )
        except subprocess.TimeoutExpired:
            raise CodexTimeout(f"codex invoke exceeded {timeout_s}s")
        except (FileNotFoundError, PermissionError, OSError, ConnectionError) as e:
            raise CodexUnavailable(f"codex invoke failed: {type(e).__name__}: {e}")
        except ValueError as e:
            # UnicodeDecodeError IS-A ValueError; map to malformed so
            # `_decide` degrades to ADVISORY (preserve concrete name).
            raise CodexMalformed(f"codex invoke {type(e).__name__}: {e}")

        # Post-subprocess audit breadcrumb (UNCHANGED behavior).
        try:
            from _lib import audit_emit as _ae  # type: ignore  # noqa: F811
            if hasattr(_ae, "emit_generic"):
                _ae.emit_generic("codex_invoke_dispatched", exit_code=int(proc.returncode))
        except Exception:
            pass

        if proc.returncode != 0:
            # Non-zero exit → unavailable (fail-OPEN). A present output file
            # after a non-zero exit is IGNORED (not read) and cleaned up.
            raise CodexUnavailable(
                f"codex returned exit={proc.returncode}; stderr_head="
                f"{(proc.stderr or '')[:240]!r}"
            )

        # -------------------------------------------------------------
        # Read back the output file with TOCTOU re-validation. Re-stat via
        # os.lstat (NOT following symlinks) and refuse anything that is not
        # a regular file we own.
        # -------------------------------------------------------------
        try:
            st = _os.lstat(out_path)
        except FileNotFoundError:
            raise CodexMalformed("codex last-message file missing after exit-0")
        except OSError as e:
            raise CodexMalformed(f"codex last-message lstat failed: {type(e).__name__}")

        if _stat.S_ISLNK(st.st_mode):
            raise CodexMalformed("codex last-message path is a symlink; refusing to read")
        if not _stat.S_ISREG(st.st_mode):
            raise CodexMalformed("codex last-message path is not a regular file; refusing")
        try:
            if st.st_uid != _os.getuid():
                raise CodexMalformed("codex last-message file not owned by us; refusing")
        except AttributeError:
            # os.getuid absent (non-POSIX) — the 0o700 mkdtemp + O_EXCL
            # pre-create are the primary controls; skip the uid check.
            pass
        if st.st_size == 0:
            raise CodexMalformed("codex last-message file is empty")
        if st.st_size > _MAX_OUTPUT_FILE_BYTES:
            raise CodexMalformed(
                f"codex last-message oversize ({st.st_size} > {_MAX_OUTPUT_FILE_BYTES})"
            )

        # Open refusing to follow a symlink swapped in post-lstat.
        try:
            open_flags = _os.O_RDONLY
            if hasattr(_os, "O_NOFOLLOW"):
                open_flags |= _os.O_NOFOLLOW
            rfd = _os.open(out_path, open_flags)
        except OSError as e:
            raise CodexMalformed(f"codex last-message open failed: {type(e).__name__}")
        try:
            raw_bytes = _os.read(rfd, _MAX_OUTPUT_FILE_BYTES + 1)
        finally:
            try:
                _os.close(rfd)
            except OSError:
                pass
        if len(raw_bytes) > _MAX_OUTPUT_FILE_BYTES:
            raise CodexMalformed("codex last-message grew past cap during read")

        content = raw_bytes.decode("utf-8", errors="replace")

        # -------------------------------------------------------------
        # SINGLE-PASS redact the FULL byte-string BEFORE returning (and
        # thus before any json.loads in the consumer). R-SEC-1. Ingress
        # redaction is fail-OPEN to ADVISORY (distinct from the ADR-114
        # fail-CLOSED *egress* contract above): if the redactor is
        # unavailable we refuse to hand un-redacted text to the parser and
        # degrade to ADVISORY via CodexMalformed.
        # -------------------------------------------------------------
        try:
            from _lib import codex_egress_redact as _redact  # noqa: F811
            redacted = _redact.redact(content)
        except Exception:
            raise CodexMalformed(
                "codex_egress_redact unavailable on ingress; refusing raw parse"
            )
        return redacted
    finally:
        _cleanup()


# ---------------------------------------------------------------------
# Sentinel bypass — share the same sentinel discovery as
# check_canonical_edit. A path that is canonical-edit-approved via
# sentinel is implicitly Pair-Rail-approved (Codex review still
# advisory, not gating). Phase 0A simplification.
# ---------------------------------------------------------------------


def _sentinel_grants_pair_rail_bypass(
    file_path: str, repo_root: Path
) -> bool:
    """True if any Architect sentinel covers `file_path` in its scope.

    Production: piggybacks on `check_canonical_edit._sentinel_grants_path`
    if that helper is importable. Otherwise returns False (no bypass).
    """
    try:
        # Best-effort import; staging file should not depend on
        # production import path. Fail soft.
        hooks_dir = repo_root / ".claude" / "hooks"
        if str(hooks_dir) not in sys.path:
            sys.path.insert(0, str(hooks_dir))
        try:
            import check_canonical_edit as _cce  # type: ignore
        except Exception:
            return False
        try:
            rel = (
                Path(file_path).resolve().relative_to(repo_root.resolve())
            )
        except (ValueError, OSError):
            return False
        rel_str = str(rel).replace(os.sep, "/")
        sentinels = _cce._find_sentinels(repo_root)  # type: ignore[attr-defined]
        for sentinel in sentinels:
            try:
                if _cce._sentinel_grants_path(sentinel, rel_str):  # type: ignore[attr-defined]
                    return True
            except Exception:
                continue
        return False
    except Exception:
        return False


# ---------------------------------------------------------------------
# Audit emit — best-effort; never raises.
# ---------------------------------------------------------------------

# Audit action labels. Post Phase 0B/1 ceremony:
#   - REGISTERED in audit_emit._KNOWN_ACTIONS (lines 338-341 of audit_emit.py):
#       pair_rail_review_passed, pair_rail_codex_unavailable,
#       pair_rail_codex_violation, pair_rail_sentinel_bypass
#   - PENDING registration (still breadcrumb-only to stderr; future
#     Owner-signed sentinel ceremony will promote them):
#       pair_rail_out_of_scope, pair_rail_kill_switch_used,
#       pair_rail_fatal_failopen
# The registered labels are durable audit records; the pending ones
# still surface via stderr for forensic sampling until promoted.
_AUDIT_REVIEW_PASSED = "pair_rail_review_passed"
_AUDIT_CODEX_VIOLATION = "pair_rail_codex_violation"
_AUDIT_CODEX_UNAVAILABLE = "pair_rail_codex_unavailable"
_AUDIT_SENTINEL_BYPASS = "pair_rail_sentinel_bypass"
_AUDIT_OUT_OF_SCOPE = "pair_rail_out_of_scope"
_AUDIT_KILL_SWITCH = "pair_rail_kill_switch_used"
# U10 NEW — uniform breadcrumb when main()'s catch-all swallows an
# unexpected exception. Without this, a hidden bug fails open silently
# with only a stderr line; with this, the audit sink keeps a single
# structured record that SPIKE-VERDICT.md can sample for U10 evidence.
_AUDIT_FATAL_FAILOPEN = "pair_rail_fatal_failopen"


def _emit_audit(action: str, **fields: Any) -> None:
    """Best-effort audit. Production fallback: stderr breadcrumb when no audit sink configured.

    Phase 1 wires through `_lib/audit_emit.emit_generic` after
    register-ceremony lands the action labels in `_KNOWN_ACTIONS`.
    """
    # Test capture hook: env-controlled file sink for unit tests.
    sink = os.environ.get("CEO_PAIR_RAIL_AUDIT_SINK")
    if sink:
        try:
            event = {"action": action, **fields}
            with open(sink, "a", encoding="utf-8") as f:
                f.write(json.dumps(event, ensure_ascii=False) + "\n")
        except Exception:
            pass  # advisory; never blocks
    # Stderr breadcrumb (spike — visible in test output).
    try:
        preview = ", ".join(
            f"{k}={v!r}" for k, v in list(fields.items())[:5]
        )
        sys.stderr.write(
            f"[check_pair_rail SPIKE] {action} {preview}\n"
        )
    except Exception:
        pass


# PLAN-122 WS3 — per-phase Codex-review audit event. ONE emit-site: fired once
# when a Codex review actually COMPLETES (any verdict). The kill-switch /
# unavailable / timeout / malformed paths represent NO completed invocation and
# do NOT emit here (consistent with WS3-SPEC: codex_review_disabled covers the
# kill-switch path; an unavailable Codex never ran). Trust boundary: the raw
# review text crosses a LOWER-trust boundary and is folded into the audit channel
# ONLY as the redacted PhaseReview (enum / bounded int / stable hash / fixed
# slug). FAIL-CLOSED: any import / mapping failure emits nothing. Never raises.
def _emit_codex_review_invoked(review_text: str, grammar: "Optional[str]") -> None:
    """Emit codex_review_invoked for a completed Codex review (best-effort).

    ``grammar`` is the write-shaped-patch verdict from ``_detect_write_shaped_patch``
    (``None`` == clean/passed; non-``None`` == a flagged violation/failed). We feed
    the review through the WS-3 driver (the single redaction source) so the raw
    text is hashed, never echoed, then route the redacted PhaseReview fields
    through ``optimizer._skeleton.safe_emit`` (silent until the action registers).
    """
    try:
        repo_root = Path(__file__).resolve().parents[2]
        scripts_dir = str((repo_root / ".claude" / "scripts").resolve())
        if scripts_dir not in sys.path:
            sys.path.insert(0, scripts_dir)
        from optimizer import codex_phase_gate as _pg  # type: ignore[import]
        from optimizer import _skeleton as _sk  # type: ignore[import]

        # Map the already-obtained review into a driver result. We INJECT a
        # closure returning that result so review_phase does the verdict
        # classification + redaction (status, violation-count normalisation,
        # thread/summary hashing) — we never re-implement that boundary here.
        # The kill-switch is intentionally bypassed: we only reach this site
        # AFTER a real invocation completed, so we drive review_phase with
        # CEO_CODEX_REVIEW unset semantics via a direct injected result.
        verdict = "block" if grammar is not None else "accept"
        injected = {
            "status": verdict,
            "summary": review_text if isinstance(review_text, str) else "",
        }
        review = _pg.review_phase(
            0, "", codex_invoke=lambda _p, _m: injected,
        )
        # review_disabled_signal is NOT forwarded — it routes the disabled
        # sibling instead; forwarding a bool would break canonical-json/HMAC.
        _sk.safe_emit(
            "codex_review_invoked",
            repo_root=repo_root,
            session_id=os.environ.get("CLAUDE_SESSION_ID", ""),
            phase_number=review.phase_number,
            review_status=review.review_status,
            summary_hash=review.summary_hash,
            thread_id_redacted=review.thread_id_redacted,
            codex_model=review.codex_model,
            duration_ms=review.duration_ms,
            violations_found_count=review.violations_found_count,
        )
    except Exception:
        # FAIL-CLOSED on the emit only — an audit-emit failure must NEVER block
        # or crash the Pair-Rail hook (ADR-005 never-blocks), and must NEVER
        # launder unredacted text (we simply emit nothing on any error).
        return


# ---------------------------------------------------------------------
# Consume side (PLAN-142) — structured-verdict primary signal (D3).
# ---------------------------------------------------------------------


def _load_codex_adapter():  # type: ignore[no-untyped-def]
    """Resolve `_lib.adapters.codex` (the structured-verdict parser).

    Same canonical-layout resolution as the other `_lib` loaders. Returns
    the module or None (fail-OPEN — caller degrades to ADVISORY). NEVER
    raises.
    """
    try:
        hooks_dir = Path(__file__).resolve().parent
        if str(hooks_dir) not in sys.path:
            sys.path.insert(0, str(hooks_dir))
        from _lib.adapters import codex as _codex  # type: ignore
        return _codex
    except Exception:
        return None


# Mirror of `_lib.adapters.codex._VALID_VERDICTS` so the kernel can validate
# without re-importing a private name. These are verdict LABELS (the
# trust-boundary vocabulary the §3 grep gate KEEPS in the kernel), not CLI
# literals.
_VALID_VERDICTS_LOCAL: Tuple[str, ...] = ("PASS", "ADVISORY", "BLOCK")


def _consume_codex_review(redacted_review: str) -> Tuple[str, Optional[str]]:
    """Derive (verdict, secondary_patch_grammar) from a REDACTED review.

    PRIMARY signal (D3): `parse_verdict_strict` — the verdict is accepted
    ONLY from a structured, schema-validated object (verdict ∈
    `_VALID_VERDICTS_LOCAL`). A forged free-text 'PASS' with no structured
    object → ADVISORY (fail-CLOSED-to-ADVISORY per R-SEC-2 / ADR-106).

    SECONDARY signal (D3): `_detect_write_shaped_patch` runs on the SAME
    redacted text as defense-in-depth annotation ONLY — it never upgrades a
    verdict to a hard block; the structured verdict is authoritative.

    Returns (verdict, patch_grammar) where verdict ∈ {"PASS","ADVISORY",
    "BLOCK"} and patch_grammar is the `_detect_write_shaped_patch` tag (or
    None). NEVER raises.
    """
    # Secondary defense-in-depth scan (advisory annotation only).
    try:
        patch_grammar = _detect_write_shaped_patch(redacted_review)
    except Exception:
        patch_grammar = None

    codex = _load_codex_adapter()
    if codex is None:
        # Adapter unimportable — fail-CLOSED-to-ADVISORY (cannot validate a
        # structured verdict, so we do not trust one).
        return "ADVISORY", patch_grammar

    # parse_verdict_strict is fail-CLOSED-to-ADVISORY and never raises, but
    # wrap defensively anyway and coerce any surprise to ADVISORY. We do NOT
    # fall back to the free-text patch scan as the verdict — it stays SECONDARY.
    try:
        envelope = codex.parse_verdict_strict(redacted_review)
        verdict = envelope.get("verdict")
        if verdict not in _VALID_VERDICTS_LOCAL:
            return "ADVISORY", patch_grammar
        return str(verdict), patch_grammar
    except Exception:
        return "ADVISORY", patch_grammar


# ---------------------------------------------------------------------
# Decision logic — pure function, easy to test.
# ---------------------------------------------------------------------


def _decide(
    *,
    tool_name: str,
    file_path: str,
    proposed_content: str,
    repo_root: Path,
    timeout_s: float,
) -> Dict[str, Any]:
    """Pure decision returning a JSON-shape dict.

    Returns:
        Dict with keys `decision` (allow|block) and optionally
        `reason` (block) or `systemMessage` (allow with note).
    """
    # Kill-switch.
    if os.environ.get("CEO_PAIR_RAIL_DISABLE", "").strip() == "1":
        _emit_audit(
            _AUDIT_KILL_SWITCH,
            tool_name=tool_name, file_path=file_path,
        )
        return {}  # schema-compliant allow (Claude Code hook schema rejects top-level "allow")

    # Out-of-scope: tool not in write set.
    write_tools = {"Edit", "Write", "MultiEdit", "NotebookEdit"}
    if tool_name not in write_tools:
        _emit_audit(
            _AUDIT_OUT_OF_SCOPE,
            tool_name=tool_name, reason="non_write_tool",
        )
        return {}  # schema-compliant allow (Claude Code hook schema rejects top-level "allow")

    # Out-of-scope: path not L3+.
    if not _is_l3_plus_path(file_path, repo_root):
        _emit_audit(
            _AUDIT_OUT_OF_SCOPE,
            tool_name=tool_name, file_path=file_path,
            reason="not_l3_plus",
        )
        return {}  # schema-compliant allow (Claude Code hook schema rejects top-level "allow")

    # Sentinel bypass — Owner-signed approval covers this path.
    if _sentinel_grants_pair_rail_bypass(file_path, repo_root):
        _emit_audit(
            _AUDIT_SENTINEL_BYPASS,
            tool_name=tool_name, file_path=file_path,
        )
        return {
            "systemMessage": (
                f"PAIR-RAIL: bypass via Architect sentinel "
                f"({file_path})"
            ),
        }

    # Invoke Codex review. `_invoke_codex_review` now returns the REDACTED
    # last-message content (one structured JSON object).
    try:
        redacted_review = _invoke_codex_review(
            tool_name=tool_name,
            file_path=file_path,
            proposed_content=proposed_content,
            timeout_s=timeout_s,
        )
    except CodexUnavailable as e:
        _emit_audit(
            _AUDIT_CODEX_UNAVAILABLE,
            tool_name=tool_name, file_path=file_path,
            error=str(e),
        )
        # Substring "Codex unavailable" PRESERVED for _base_to_verdicts.
        return {
            "systemMessage": (
                f"PAIR-RAIL: Codex unavailable ({e}); fail-OPEN "
                "advisory mode."
            ),
        }
    except CodexTimeout as e:
        _emit_audit(
            _AUDIT_CODEX_UNAVAILABLE,
            tool_name=tool_name, file_path=file_path,
            error=f"timeout:{e}",
        )
        # Substring "Codex timeout" PRESERVED for _base_to_verdicts.
        return {
            "systemMessage": (
                f"PAIR-RAIL: Codex timeout ({e}); fail-OPEN."
            ),
        }
    except CodexMalformed as e:
        _emit_audit(
            _AUDIT_CODEX_UNAVAILABLE,
            tool_name=tool_name, file_path=file_path,
            error=f"malformed:{e}",
        )
        # Substring "Codex malformed" PRESERVED for _base_to_verdicts.
        return {
            "systemMessage": (
                f"PAIR-RAIL: Codex malformed response ({e}); "
                "fail-OPEN."
            ),
        }

    # PRIMARY: structured verdict (parse_verdict_strict, fail-CLOSED-to-
    # ADVISORY). SECONDARY: _detect_write_shaped_patch annotation (D3).
    verdict, patch_grammar = _consume_codex_review(redacted_review)

    # PLAN-122 WS3 — record the completed Codex review (any verdict) as
    # codex_review_invoked (advisory; redacted PhaseReview; never blocks).
    # `grammar` keeps its historical meaning (write-shape tag). PLAN-142 V2
    # cross-model fold: a structured BLOCK with prose-only findings (no
    # write-shaped patch) has patch_grammar=None, which the WS3 driver would
    # otherwise map to 'accept' — under-reporting BLOCKs. Pass a synthetic
    # block tag so the telemetry agrees with the PRIMARY structured verdict.
    _emit_codex_review_invoked(
        redacted_review,
        patch_grammar or ("structured_block" if verdict == "BLOCK" else None),
    )

    if verdict == "BLOCK":
        # Structured BLOCK from a schema-validated object. Per PLAN-092 /
        # ADR-127 SHADOW-strip the rail stays ADVISORY-ONLY at the
        # user-facing surface (no top-level block); the matrix wrapper owns
        # any block promotion via Case-B preconditions. The "PAIR-RAIL-
        # ADVISORY" + "write-shaped" substrings are PRESERVED so
        # _base_to_verdicts classifies this as Case B (codex_verdict=BLOCK).
        _emit_audit(
            _AUDIT_CODEX_VIOLATION,
            tool_name=tool_name, file_path=file_path,
            verdict="BLOCK",
            grammar=(patch_grammar or ""),
            response_len=len(redacted_review),
        )
        return {
            "systemMessage": (
                "PAIR-RAIL-ADVISORY: Codex returned a structured BLOCK "
                "verdict (advisory-only per ADR-127). A write-shaped "
                f"secondary signal ({patch_grammar or 'none'}) was "
                f"{'also ' if patch_grammar else 'not '}detected. See "
                "routing-matrix.md §threat-model."
            ),
        }

    if patch_grammar is not None and verdict != "BLOCK":
        # Defense-in-depth ONLY: a write-shaped patch under a non-BLOCK
        # structured verdict. The structured verdict is authoritative (D3),
        # so we do NOT block; surface an advisory note + emit the violation
        # audit for forensic continuity. "PAIR-RAIL-ADVISORY" + "write-shaped"
        # keep the matrix Case-B classification stable.
        _emit_audit(
            _AUDIT_CODEX_VIOLATION,
            tool_name=tool_name, file_path=file_path,
            verdict=verdict,
            grammar=patch_grammar,
            response_len=len(redacted_review),
            note="secondary_writeshape_under_nonblock_verdict",
        )
        return {
            "systemMessage": (
                "PAIR-RAIL-ADVISORY: secondary defense-in-depth detected a "
                f"write-shaped patch ({patch_grammar}) under a non-BLOCK "
                f"structured verdict ({verdict}); advisory-only per ADR-127 "
                "+ D3 (structured verdict is authoritative)."
            ),
        }

    if verdict == "ADVISORY":
        # Parse miss / forged free-text / oversize / adapter-missing →
        # ADVISORY (fail-open). No "review clean" substring (NOT a clean
        # pass); no matrix Case-A.
        _emit_audit(
            _AUDIT_REVIEW_PASSED,
            tool_name=tool_name, file_path=file_path,
            verdict="ADVISORY",
            response_len=len(redacted_review),
        )
        return {
            "systemMessage": (
                "PAIR-RAIL: Codex verdict ADVISORY (no structured PASS/BLOCK "
                "parsed); fail-OPEN advisory mode."
            ),
        }

    # verdict == "PASS" — structured clean review. "review clean" substring
    # PRESERVED for _base_to_verdicts Case-A classification.
    _emit_audit(
        _AUDIT_REVIEW_PASSED,
        tool_name=tool_name, file_path=file_path,
        verdict="PASS",
        response_len=len(redacted_review),
    )
    return {
        "systemMessage": "PAIR-RAIL: Codex review clean (structured PASS verdict).",
    }


# ---------------------------------------------------------------------
# Hook entry point. Reads PreToolUse JSON envelope from stdin per
# SPEC/v1/hook-io.schema.md L14.
# ---------------------------------------------------------------------


def _read_event_from_stdin() -> Optional[Dict[str, Any]]:
    """Parse PreToolUse JSON envelope. Returns None on parse failure."""
    try:
        raw = sys.stdin.read()
    except Exception:
        return None
    if not raw:
        return None
    try:
        return json.loads(raw)
    except (ValueError, TypeError):
        return None


def _extract_proposed_content(tool_input: Dict[str, Any]) -> str:
    """Pull the proposed-write content from tool_input.

    Edit       → `new_string`
    Write      → `content`
    MultiEdit  → concatenation of all `new_string` values
    NotebookEdit → `new_source`
    Fallback   → empty string (Codex review still proceeds with path-only context).
    """
    if not isinstance(tool_input, dict):
        return ""
    if "content" in tool_input and isinstance(tool_input["content"], str):
        return tool_input["content"]
    if "new_string" in tool_input and isinstance(tool_input["new_string"], str):
        return tool_input["new_string"]
    if "new_source" in tool_input and isinstance(tool_input["new_source"], str):
        return tool_input["new_source"]
    edits = tool_input.get("edits")
    if isinstance(edits, list):
        chunks: List[str] = []
        for e in edits:
            if isinstance(e, dict) and isinstance(e.get("new_string"), str):
                chunks.append(e["new_string"])
        if chunks:
            return "\n".join(chunks)
    return ""


def main() -> int:
    """Hook entry point — fail-OPEN on any uncaught exception."""
    try:
        event = _read_event_from_stdin()
        if event is None:
            sys.stdout.write(json.dumps({}) + "\n")  # schema-compliant allow
            return 0
        tool_name = str(event.get("tool_name") or "")
        tool_input = event.get("tool_input") or {}
        if not isinstance(tool_input, dict):
            tool_input = {}
        file_path = str(tool_input.get("file_path") or "")
        proposed = _extract_proposed_content(tool_input)
        repo_root = Path(
            os.environ.get("CLAUDE_PROJECT_DIR") or os.getcwd()
        )
        try:
            timeout_s = float(
                os.environ.get("CEO_PAIR_RAIL_TIMEOUT_S", "30")
            )
        except (TypeError, ValueError):
            timeout_s = 30.0
        if timeout_s <= 0 or timeout_s > 600:
            timeout_s = 30.0

        # PLAN-081 Phase 3: route through the asymmetric VETO matrix
        # wrapper instead of the spike _decide() directly. The matrix
        # wrapper invokes _decide() internally + applies Cases A-F per
        # spec.md §11 + emits pair_rail_case per evaluation.
        decision = _decide_with_matrix(
            tool_name=tool_name,
            file_path=file_path,
            proposed_content=proposed,
            repo_root=repo_root,
            timeout_s=timeout_s,
        )
        sys.stdout.write(json.dumps(decision, ensure_ascii=False) + "\n")
        return 0
    except Exception as e:
        # Fail-OPEN — never block the user on hook bug. U10 contract:
        # emit a structured breadcrumb so SPIKE-VERDICT.md can audit the
        # rate of catch-all firings (a high rate = a real bug masked by
        # fail-open, not a healthy contract). The stderr write is kept
        # for human visibility during the spike.
        try:
            # Codex MCP review F3 — keep the 240-char preview AND emit
            # stable `error_type` + `error_len` fields so SPIKE-VERDICT.md
            # sampling can group by exception class without parsing the
            # truncated preview.
            err_type = type(e).__name__
            err_str = str(e)
            _emit_audit(
                _AUDIT_FATAL_FAILOPEN,
                error_type=err_type,
                error_len=len(err_str),
                error=f"{err_type}: {err_str}"[:240],
            )
        except Exception:
            pass
        try:
            sys.stderr.write(
                f"[check_pair_rail SPIKE] FATAL: {type(e).__name__}: {e}\n"
            )
        except Exception:
            pass
        sys.stdout.write(json.dumps({}) + "\n")  # schema-compliant allow
        return 0


# Codex iter 1 P0-1 fix: original `if __name__ == "__main__"` block moved
# to the END of this file (line ~1180) so the Phase 3 helper functions
# defined below are available when ``main()`` runs. Runtime import order:
# Python parses + defines all module-level symbols top-to-bottom, then
# the `if __name__` guard at the bottom triggers `main()` — which
# references `_decide_with_matrix` (defined further down). Without this
# move, `main()` would NameError at runtime since the helper was not
# yet defined when the original guard fired.


# =====================================================================
# PLAN-081 Phase 3 — Asymmetric VETO matrix Cases A-F + rubric catalogue
# + Case-B precondition validation + audit emit.
#
# Layered onto the spike _decide() (which handles review-only Phase 1
# semantics: write-shape detection + fail-OPEN). The Phase 3 wrapper
# `_decide_with_matrix()` invokes the spike _decide() to get an initial
# verdict, then applies the asymmetric matrix per spec.md §11:
#
#   Case A: claude=PASS + codex=PASS → dispatch
#   Case B: claude=PASS + codex=BLOCK with preconditions met → block
#           (preconditions: file:line + rubric_violation_id catalogue
#            + severity ∈ {P0, P1})
#   Case B': claude=PASS + codex=BLOCK without preconditions → fail-OPEN
#            advisory (per ADR-106 + R1 spec.md auto-Round-2 path)
#   Case C: claude=BLOCK + codex=PASS → not reachable at PreToolUse
#           (Claude already passed to invoke this hook); recorded for
#           Phase 4 corpus-replay parity.
#   Case D: claude=BLOCK + codex=BLOCK → not reachable at PreToolUse;
#           recorded for Phase 4 corpus-replay parity.
#   Case E: divergent (Jaccard similarity ≤ 0.3) → flag for human
#           review; allow with systemMessage warning.
#   Case F: timeout / outage / malformed → fail-OPEN per ADR-106.
#
# 24h human-triage grace per R1 S-TDE-4: severity P1 with grace remaining
# closes-as-advisory after T+24h (env CEO_PAIR_RAIL_HUMAN_TRIAGE_HOURS).
# =====================================================================


_RUBRIC_CATALOGUE_CACHE: Optional[Dict[str, Dict[str, Any]]] = None


def _load_rubric_catalogue(repo_root: Path) -> Dict[str, Dict[str, Any]]:
    """Load + cache the rubric violation catalogue.

    Returns an empty dict if the catalogue cannot be loaded (fail-OPEN —
    Phase 3 hook MUST NOT block on missing catalogue; it just downgrades
    Case-B to advisory because the rubric_violation_id can never be
    validated against an empty catalogue).
    """
    global _RUBRIC_CATALOGUE_CACHE
    if _RUBRIC_CATALOGUE_CACHE is not None:
        return _RUBRIC_CATALOGUE_CACHE
    catalogue_path = (
        repo_root / ".claude" / "policies" / "rubric-violation-catalogue.yaml"
    )
    if not catalogue_path.exists():
        _RUBRIC_CATALOGUE_CACHE = {}
        return _RUBRIC_CATALOGUE_CACHE
    try:
        text = catalogue_path.read_text(encoding="utf-8")
        # Inline minimal YAML parse for the `violations:` section.
        # Matches the routing-matrix-loader pattern (stdlib only).
        catalogue: Dict[str, Dict[str, Any]] = {}
        in_violations = False
        current: Optional[Dict[str, Any]] = None
        for raw_line in text.splitlines():
            line = raw_line.split("#", 1)[0].rstrip() if "#" in raw_line else raw_line.rstrip()
            if not line.strip():
                continue
            if line.startswith("violations:"):
                in_violations = True
                continue
            if not in_violations:
                continue
            # Detect new entry: '  - id: <slug>' at 2-space indent
            stripped = line.lstrip()
            indent = len(line) - len(stripped)
            if indent == 2 and stripped.startswith("- id:"):
                if current is not None and "id" in current:
                    catalogue[current["id"]] = current
                current = {}
                _, _, val = stripped.partition(":")
                current["id"] = val.strip()
            elif indent == 4 and current is not None and ":" in stripped:
                key, _, val = stripped.partition(":")
                current[key.strip()] = val.strip()
            elif indent < 2 and current is not None and "id" in current:
                # Section ended
                catalogue[current["id"]] = current
                current = None
                in_violations = False
        if current is not None and "id" in current:
            catalogue[current["id"]] = current
        _RUBRIC_CATALOGUE_CACHE = catalogue
        return catalogue
    except Exception:
        _RUBRIC_CATALOGUE_CACHE = {}
        return _RUBRIC_CATALOGUE_CACHE


def _validate_provider_pair(
    *,
    codex_verdict: str,
    rubric_violation_id: str,
    severity: str,
    file_line_cited: bool,
    repo_root: Path,
) -> Tuple[bool, str]:
    """Validate Case-B preconditions per spec.md §11.

    A Case-B verdict from Codex (BLOCK with PASS from Claude) must carry:
      - reproducible evidence (file:line OR command cited)
      - rubric_violation_id ∈ rubric-violation-catalogue.yaml
      - severity ∈ {P0, P1}

    R1 S-CR-1 codifies: this function is a greenfield helper (NOT
    preserving any prior provider-pair grandfather entry). ADR-097 was
    "Function-length advisory-permanent + 344-function grandfather list"
    — NO LLM/dispatcher/pair-rail content per `head -1` audit.

    Returns:
        (preconditions_met: bool, reason: str). Reason is "ok" when met;
        otherwise a slug naming the specific precondition that failed
        (downstream audit emit + reason_code).
    """
    if codex_verdict != "BLOCK":
        # Not a Case-B candidate — vacuously "met" for the dispatcher
        return True, "not_case_b"
    if not file_line_cited:
        return False, "missing_file_line"
    if not rubric_violation_id or len(rubric_violation_id) > 64:
        return False, "missing_or_invalid_rubric_id"
    catalogue = _load_rubric_catalogue(repo_root)
    if not catalogue:
        return False, "catalogue_not_loaded"
    if rubric_violation_id not in catalogue:
        return False, "rubric_id_not_in_catalogue"
    if severity not in ("P0", "P1"):
        return False, "invalid_severity"
    return True, "ok"


def _compute_jaccard_bucket(claude_findings: List[str], codex_findings: List[str]) -> str:
    """Bucket the Jaccard similarity for Case-E divergence detection.

    Phase 3 uses bucketed similarity (NEVER raw float) per Sec MF-3
    `_PAIR_RAIL_CASE_EMIT_ALLOWLIST` (raw float would leak prompt
    content / response content via correlated audit-log readout).

    Buckets per spec.md §11 R1.5-4 fix:
      - "<=0.3" → low similarity = high divergence → Case-E flag
      - "0.3-0.5"
      - "0.5-0.8"
      - ">0.8" → high similarity = aligned reviews
    """
    if not claude_findings and not codex_findings:
        return ">0.8"  # both empty = perfectly aligned
    set_c = {f.strip().lower() for f in claude_findings if f.strip()}
    set_x = {f.strip().lower() for f in codex_findings if f.strip()}
    if not set_c and not set_x:
        return ">0.8"
    inter = len(set_c & set_x)
    union = len(set_c | set_x)
    if union == 0:
        return ">0.8"
    sim = inter / union
    if sim <= 0.3:
        return "<=0.3"
    if sim <= 0.5:
        return "0.3-0.5"
    if sim <= 0.8:
        return "0.5-0.8"
    return ">0.8"


def _hash_file_path_prefix(file_path: str) -> str:
    """Compute 16-hex SHA-256 prefix of file path (LLM06 side-channel guard)."""
    import hashlib
    if not file_path:
        return ""
    return hashlib.sha256(file_path.encode("utf-8")).hexdigest()[:16]


def _resolve_human_triage_grace_h(severity: str) -> int:
    """Return human-triage grace hours per R1 S-TDE-4.

    P1 violations get a 24h grace window (env-overridable via
    CEO_PAIR_RAIL_HUMAN_TRIAGE_HOURS, clamped to [0, 24] per ADR-108
    + Codex iter 1 P1-2). P0 = 0h (immediate block).
    Outside-of-grace P1 closes-as-advisory.

    Codex iter 1 P1-2 fix: env override is clamped to ``min(value, 24)``
    so an Owner setting `CEO_PAIR_RAIL_HUMAN_TRIAGE_HOURS=1000` cannot
    extend the grace beyond the ADR-108-mandated 24h ceiling. Lower
    bound stays 0 (allows mechanical-immediate-close override).
    """
    if severity != "P1":
        return 0
    raw = os.environ.get("CEO_PAIR_RAIL_HUMAN_TRIAGE_HOURS", "24")
    try:
        h = int(raw)
        # Clamp to [0, 24] per ADR-108 §Operational labeling protocol.
        return max(0, min(h, 24))
    except (TypeError, ValueError):
        return 24


def _emit_pair_rail_case(
    *,
    case: str,
    claude_verdict: str,
    codex_verdict: str,
    tool_name: str,
    file_path: str,
    precondition_met: bool = False,
    rubric_violation_id: str = "",
    severity: str = "",
    jaccard_bucket: str = "",
    repo_root: Optional[Path] = None,
) -> None:
    """Best-effort audit emit of pair_rail_case. Fail-OPEN.

    Import resolution order (first hit wins):

    1. Test-only env override ``CEO_PAIR_RAIL_STAGED_AUDIT_EMIT_DIR``
       points at a directory containing ``_lib/audit_emit.py``. Used by
       the Phase 3 staging tests to load the staged audit_emit before
       the ceremony cp lands it canonical. Removed post-ceremony.
    2. Canonical layout: ``Path(__file__).resolve().parent`` (the
       canonical ``.claude/hooks/`` dir) contains ``_lib/audit_emit.py``.
       Standard production path post-ceremony.
    3. PYTHONPATH-discovered ``_lib.audit_emit`` (rare adopter
       scenario where the canonical hooks dir isn't this file's parent).

    Any failure → return silently (fail-OPEN per ADR-106).
    """
    _ae = None
    try:
        # Resolution 1: test-only staged-dir override.
        staged_dir = os.environ.get("CEO_PAIR_RAIL_STAGED_AUDIT_EMIT_DIR")
        if staged_dir:
            staged_path = Path(staged_dir)
            if staged_path.is_dir() and (staged_path / "_lib" / "audit_emit.py").exists():
                if str(staged_path) not in sys.path:
                    sys.path.insert(0, str(staged_path))
                try:
                    from _lib import audit_emit as _ae  # type: ignore
                except Exception:
                    _ae = None
        # Resolution 2: canonical layout.
        if _ae is None:
            hooks_dir = Path(__file__).resolve().parent
            if str(hooks_dir) not in sys.path:
                sys.path.insert(0, str(hooks_dir))
            try:
                from _lib import audit_emit as _ae  # type: ignore  # noqa: F811
            except Exception:
                _ae = None
        # Resolution 3: PYTHONPATH already configured.
        if _ae is None:
            try:
                from _lib import audit_emit as _ae  # type: ignore  # noqa: F811
            except Exception:
                _ae = None
        # Defense-in-depth: ALSO breadcrumb to CEO_PAIR_RAIL_AUDIT_SINK
        # (the spike's per-test file sink). Used by Phase 3 matrix tests
        # to capture matrix decisions in the same JSONL surface as the
        # spike's `_emit_audit`. Production deployment relies on
        # audit_emit.emit_pair_rail_case being reachable; the sink
        # breadcrumb is a forensic continuity bridge for tests + adopters
        # without canonical audit-log writability.
        sink = os.environ.get("CEO_PAIR_RAIL_AUDIT_SINK")
        if sink:
            try:
                with open(sink, "a", encoding="utf-8") as f:
                    f.write(json.dumps({
                        "action": "pair_rail_case",
                        "case": case,
                        "claude_verdict": claude_verdict,
                        "codex_verdict": codex_verdict,
                        "tool_name": tool_name,
                        "file_path_hash_prefix": _hash_file_path_prefix(file_path),
                        "precondition_met": precondition_met,
                        "rubric_violation_id": rubric_violation_id,
                        "severity": severity,
                        "jaccard_similarity_bucket": jaccard_bucket,
                        "human_triage_grace_h": _resolve_human_triage_grace_h(severity),
                    }, ensure_ascii=False) + "\n")
            except Exception:
                pass

        if _ae is None or not hasattr(_ae, "emit_pair_rail_case"):
            return
        _ae.emit_pair_rail_case(
            case=case,
            claude_verdict=claude_verdict,
            codex_verdict=codex_verdict,
            tool_name=tool_name,
            file_path_hash_prefix=_hash_file_path_prefix(file_path),
            precondition_met=precondition_met,
            rubric_violation_id=rubric_violation_id,
            severity=severity,
            jaccard_similarity_bucket=jaccard_bucket,
            human_triage_grace_h=_resolve_human_triage_grace_h(severity),
        )
    except Exception:
        pass  # fail-OPEN — never block on audit


def _load_pair_rail_decide():  # type: ignore[no-untyped-def]
    """Resolve the canonical pure decision module `_lib.pair_rail_decide`.

    Mirrors `_emit_pair_rail_case`'s Resolution-2 (canonical layout):
    the `.claude/hooks/` dir that houses this file also houses `_lib/`.
    Returns the module or None (fail-OPEN — caller must tolerate None).
    """
    try:
        hooks_dir = Path(__file__).resolve().parent
        if str(hooks_dir) not in sys.path:
            sys.path.insert(0, str(hooks_dir))
        from _lib import pair_rail_decide as _prd  # type: ignore
        return _prd
    except Exception:
        return None


def _base_to_verdicts(base: Dict[str, Any]) -> Tuple[str, str, str]:
    """Translate the procedural `base` decision dict into the verdict
    triple `_lib.pair_rail_decide.detect_case()` consumes.

    PLAN-112-FOLLOWUP-pair-rail-decide-canonical (W1). PURE + fail-OPEN:
    any malformed input yields the no-case tuple `("", "", "")` (which
    `detect_case()` maps to None → no matrix emit), never raises.

    The substring contract is byte-identical to the LEGACY inline
    classification in `_decide_with_matrix` (verified against
    `_decide()` returns, source lines 595-679). Precedence MUST match
    the inline arm order: F (Codex fail) → B (write-shape/block) →
    A (review clean) → None (sentinel / kill-switch / out-of-scope).

    Returns:
        (claude_verdict, codex_verdict, jaccard_bucket).
        claude_verdict is "PASS" for every reachable matrix case
        (Claude already passed to reach a PreToolUse write). Sentinel
        bypass + non-matrix short-circuits return ("", "", "").
    """
    try:
        sysmsg = base.get("systemMessage", "")
        if not isinstance(sysmsg, str):
            sysmsg = ""
        decision = base.get("decision", "allow")
        # Arm 1 — Case F (Codex unavailable / timeout / malformed).
        if (
            "Codex unavailable" in sysmsg
            or "Codex timeout" in sysmsg
            or "Codex malformed" in sysmsg
        ):
            sysmsg_lower = sysmsg.lower()
            if "malformed" in sysmsg_lower:
                return "PASS", "MALFORMED", ""
            # timeout AND unavailable both coerce to TIMEOUT (schema-
            # compatible; precise reason stays in base[systemMessage]).
            return "PASS", "TIMEOUT", ""
        # Arm 2 — sentinel bypass is NOT a matrix case (no verdicts).
        if "bypass via Architect sentinel" in sysmsg:
            return "", "", ""
        # Arm 3 — Case B (write-shape advisory OR legacy block path).
        is_advisory_writeshape = (
            "PAIR-RAIL-ADVISORY" in sysmsg and "write-shaped" in sysmsg
        )
        if decision == "block" or is_advisory_writeshape:
            return "PASS", "BLOCK", ""
        # Arm 4 — Case A (clean review).
        if "review clean" in sysmsg:
            return "PASS", "PASS", ""
        # Arm 5 — non-matrix short-circuit (kill-switch / out-of-scope).
        return "", "", ""
    except Exception:
        # Fail-OPEN: derivation error → no-case tuple (detect_case → None).
        return "", "", ""


def _decide_with_matrix(
    *,
    tool_name: str,
    file_path: str,
    proposed_content: str,
    repo_root: Path,
    timeout_s: float,
) -> Dict[str, Any]:
    """Phase 3 asymmetric VETO matrix wrapper around `_decide()`.

    Calls the canonical `_decide()` codepath to get the Phase 1 verdict
    (review-only semantics), then applies the Cases A-F matrix:

      - canonical path returns ALLOW with no matrix-relevant signal → Case A
      - canonical path returns advisory write-shape (PLAN-092 Wave B
        SHADOW-strip per ADR-127) → validate Case-B preconditions:
          + preconditions met → Case B (advisory + audit)
          + preconditions NOT met → Case B' fail-OPEN (advisory)
      - canonical path returns ALLOW with `systemMessage` containing
        "Codex unavailable" / "timeout" / "malformed" → Case F (allow)
      - canonical path returns ALLOW with sentinel bypass → not a matrix case
        (already authorized by Owner sentinel)

    Each matrix arm emits `pair_rail_case` with case + verdicts +
    preconditions + rubric metadata.

    R1 S-Perf-3: matrix lookup uses O(1) dict (NOT linear scan); the
    ``_MATRIX_DECISIONS`` table below dispatches in constant time.
    """
    # Compute base decision via spike _decide()
    base = _decide(
        tool_name=tool_name,
        file_path=file_path,
        proposed_content=proposed_content,
        repo_root=repo_root,
        timeout_s=timeout_s,
    )

    sysmsg = base.get("systemMessage", "")

    # PLAN-112-FOLLOWUP-pair-rail-decide-canonical (W2): delegate the
    # verdict→case CLASSIFICATION to the canonical pure module
    # `_lib.pair_rail_decide.detect_case()`. The procedural shell
    # (Codex invoke, patch detect — both inside `_decide()` above), the
    # B'/precondition resolution, and every audit emit STAY INLINE.
    # `evaluate()` is DELIBERATELY NOT called: it would convert a
    # precondition-unmet Case B into B' (pair_rail_decide.py:197-204),
    # diverging from production's byte-identical `case="B"` emit.
    #
    # Fail-OPEN: any error in verdict-derivation / classification / lib
    # import returns `base` (implicit allow), never raises.
    try:
        cv, xv, jb = _base_to_verdicts(base)
        _prd = _load_pair_rail_decide()
        matrix_case = (
            _prd.detect_case(claude_verdict=cv, codex_verdict=xv, jaccard_bucket=jb)
            if _prd is not None
            else None
        )
    except Exception:
        return base  # fail-OPEN — never block the user on a classifier bug

    if matrix_case is None:
        # Sentinel bypass / kill-switch / out-of-scope / non-matrix →
        # no case emit (byte-identical to the legacy fall-through arms).
        return base

    case_value = getattr(matrix_case, "value", matrix_case)

    if case_value == "F":
        # Case F — fail-OPEN. The codex_verdict sub-discrimination
        # (MALFORMED vs TIMEOUT, with UNAVAILABLE coercing to TIMEOUT)
        # is carried by `_base_to_verdicts()` in `xv`; emit it verbatim.
        _emit_pair_rail_case(
            case="F", claude_verdict="PASS", codex_verdict=xv,
            tool_name=tool_name, file_path=file_path,
        )
        return base

    if case_value == "B":
        # Procedural Case-B audit emit (advisory-only per ADR-127).
        # B'/precondition resolution stays INLINE (NOT via evaluate()).
        # precondition_met reflects whether substantive rubric evidence
        # was attached (False at Phase 3; True at Phase 4 corpus-replay).
        preconditions_met, reason_slug = _validate_provider_pair(
            codex_verdict="BLOCK",
            rubric_violation_id="",  # not extracted from procedural grammar
            severity="",
            file_line_cited=False,
            repo_root=repo_root,
        )
        _emit_pair_rail_case(
            case="B", claude_verdict="PASS", codex_verdict="BLOCK",
            tool_name=tool_name, file_path=file_path,
            precondition_met=preconditions_met,
            rubric_violation_id="",
            severity="P0",  # write-shape violation defaulted P0 procedural
        )
        # Advisory-only return — `base` already carries the advisory
        # systemMessage (Site 1). No `decision` key — schema treats
        # absence as implicit allow.
        return base

    if case_value == "A":
        _emit_pair_rail_case(
            case="A", claude_verdict="PASS", codex_verdict="PASS",
            tool_name=tool_name, file_path=file_path,
        )
        return base

    # Defensive: any other detected case (C/D/E — confirmed unreachable
    # from the procedural `base`, plan §2a.2) → no emit, fail-OPEN allow.
    return base


# Codex iter 1 P0-1 fix: __main__ guard moved to end-of-file so the
# Phase 3 matrix helpers above are bound before main() executes.
if __name__ == "__main__":
    sys.exit(main())
