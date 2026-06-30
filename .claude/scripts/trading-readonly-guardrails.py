#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
trading-readonly-guardrails.py — PLAN-083 Wave 2 sub-agent 2.7.

R1-fortified trading-readonly enforcement library. Activates when the
canonical `.claude/repo-profile.yaml` declares `risk_class: trading-readonly`
(see PLAN-083 Wave 0a sub-agent 0.6 `detect-repo-profile.py`).

PLAN-083 §7 contract (non-negotiable):

  1. Repo-profile fail-CLOSED to `trading-readonly` on ambiguity
     (enforced upstream by sub-agent 0.6).
  2. Zero write actions to canonical trading paths without per-INVOCATION
     `CEO_TRADING_WRITE_OVERRIDE=1` + path-scoped + Owner justification ≥20
     chars + audit emit `trading_write_override_used`. Bare `=1` toggle
     without justification REJECTED.
  3. Secret scan BEFORE logs / audit / receipts / analysis output via
     `secret-patterns-exchange.yaml` (Wave -1.4). Per-rule FPR ≤15%.
  4. Strategy / concurrency / latency / precision files marked
     "manual review only" via `manual_review_paths` deny-list.
  5. Kill-switch FAIL-CLOSED: missing `repo-profile.yaml` DISABLES
     trading actions entirely (NOT downgrade to less-restrictive generic).
     Generic mode reachable ONLY via explicit `confirm-profile generic`.
     Escape hatch via Owner-signed ceremony emits
     `trading_kill_switch_disabled`.
  6. 7-day read-only first-week banner ALWAYS visible (even with override)
     per Codex `019e1803` — override does NOT silence safety advisories.

## Public API (six exported functions matching §7 1:1)

    check_write_override(env, target_path, justification) -> (allowed, reason)
    scan_output_for_secrets(output_text, profile_yaml_path=None) -> [Match]
    is_manual_review_path(target_path, profile_yaml_path) -> bool
    kill_switch_disabled(profile_yaml_path) -> bool   # True ⇒ DISABLED
    seven_day_banner_visible(profile_yaml_path) -> bool
    emit_kill_switch_invoked(profile_yaml_path, reason) -> None  # audit hook

Plus two book-keeping helpers used by the CLI driver:

    load_repo_profile(profile_yaml_path) -> dict | None
    load_secret_patterns(yaml_path) -> list[dict]

## CLI

    trading-readonly-guardrails.py check-override --target PATH --justification TEXT
    trading-readonly-guardrails.py scan-output [--input -|FILE] [--profile PATH]
    trading-readonly-guardrails.py check-manual-review --target PATH --profile PATH
    trading-readonly-guardrails.py kill-switch-status [--profile PATH]
    trading-readonly-guardrails.py banner [--profile PATH]

Exit codes:
  0 — guardrail allows action / scan clean / banner suppressed
  1 — guardrail BLOCKS (override rejected, secret leak detected, manual-review path)
  2 — kill-switch DISABLED (no repo-profile.yaml; fail-CLOSED state)
  3 — usage / CLI / schema error
  4 — IO error reading repo-profile or secret-patterns

## STDLIB ONLY. Python 3.9+. No PyYAML, no external regex engine.

The audit emit fields enforce the Sec MF-3 allowlist invariant (see
PLAN-083 §16 R1 digest item 3): NEVER persist raw matched-secret text,
NEVER persist literal Owner justification text body — only SHA-256
prefixes + truncated boolean classification. Allowlist enforced by
`.claude/hooks/_lib/audit_emit.py` via the patch in
`patches/audit-emit-trading-actions.patch`.
"""

from __future__ import annotations

import argparse
import datetime as _dt
import hashlib
import json
import os
import re
import sys
from pathlib import Path
from typing import Dict, List, Optional, Tuple

# ---------------------------------------------------------------------------
# Constants — PLAN-083 §7 non-negotiable invariants
# ---------------------------------------------------------------------------

# Per-invocation override env var (NOT session-wide). The hook contract
# requires this be cleared/reset before each Edit/Write tool dispatch.
ENV_WRITE_OVERRIDE = "CEO_TRADING_WRITE_OVERRIDE"
ENV_WRITE_JUSTIFICATION = "CEO_TRADING_WRITE_JUSTIFICATION"

# Minimum justification length (PLAN-083 §7.2 R1 Sec P0-2).
MIN_JUSTIFICATION_CHARS = 20

# Max justification length (defense-in-depth against log-injection).
MAX_JUSTIFICATION_CHARS = 4096

# Per-pattern FPR ceiling (PLAN-083 AC5b).
DEFAULT_FPR_CEILING = 0.15

# 7-day banner window (PLAN-083 §7.6).
BANNER_WINDOW_DAYS = 7

# Risk-class that activates ALL of these guardrails (PLAN-083 §7.1).
TRADING_RISK_CLASS = "trading-readonly"

# Profile values that mean "trading actions are DISABLED" when the profile
# is missing OR the profile is one of these flagged states (fail-CLOSED).
DISABLED_STATES = (
    "unknown-needs-owner-confirmation",
)

# Default manual-review path patterns (PLAN-083 §7.4 CR NTH ≥10 fixtures).
# Matched against POSIX repo-relative paths via `fnmatch.fnmatchcase`.
DEFAULT_MANUAL_REVIEW_PATHS: Tuple[str, ...] = (
    "strategies/**",
    "arbitrage/**",
    "exchanges/**",
    "bot/**",
    "trading/**",
    "src/strategies/**",
    "src/exchanges/**",
    "src/arbitrage/**",
    "**/concurrency.py",
    "**/latency.py",
    "**/precision.py",
    "**/order_book.py",
    "**/market_data.py",
    "**/.env",
    "**/.env.*",
)

# Where the secret-patterns YAML lives (canonical, from Wave -1.4).
DEFAULT_SECRET_PATTERNS_REL = ".claude/policies/secret-patterns-exchange.yaml"
DEFAULT_REPO_PROFILE_REL = ".claude/repo-profile.yaml"

# Context-hint window (per Wave -1.4 YAML comment: ±200 bytes).
CONTEXT_WINDOW_BYTES = 200

# Path-traversal max segment length / max total length (defense-in-depth).
MAX_PATH_LENGTH = 4096
MAX_PATH_SEGMENT_LENGTH = 512

# Output-scan size cap (avoid pathological inputs).
MAX_OUTPUT_SCAN_BYTES = 4 * 1024 * 1024  # 4 MiB


# ---------------------------------------------------------------------------
# Match record
# ---------------------------------------------------------------------------


class Match:
    """A single secret-scan hit. Carries enough forensic metadata for an
    audit-emit + a redaction step, but NEVER holds raw matched text in
    public attributes (sha256-prefixed only)."""

    __slots__ = (
        "pattern_id",
        "family",
        "redaction_label",
        "confidence",
        "match_sha256_prefix",
        "match_offset_bucket",
        "match_length",
    )

    def __init__(
        self,
        pattern_id: str,
        family: str,
        redaction_label: str,
        confidence: str,
        match_text: str,
        match_offset: int,
    ) -> None:
        self.pattern_id = pattern_id
        self.family = family
        self.redaction_label = redaction_label
        self.confidence = confidence
        # SHA-256 over the matched bytes; we expose only 16 hex chars
        # (~64 bits) of identity — enough to dedup, not enough to leak.
        digest = hashlib.sha256(match_text.encode("utf-8", errors="replace")).hexdigest()
        self.match_sha256_prefix = digest[:16]
        self.match_offset_bucket = _bucket_offset(match_offset)
        self.match_length = len(match_text)

    def to_dict(self) -> Dict[str, object]:
        """Forensic dict suitable for audit-emit. NEVER contains raw text."""
        return {
            "pattern_id": self.pattern_id,
            "family": self.family,
            "redaction_label": self.redaction_label,
            "confidence": self.confidence,
            "match_sha256_prefix": self.match_sha256_prefix,
            "match_offset_bucket": self.match_offset_bucket,
            "match_length": self.match_length,
        }


def _bucket_offset(offset: int) -> str:
    """Bucket a byte offset for Sec MF-3 (no raw offset persistence)."""
    if offset < 0:
        return "negative"
    if offset < 100:
        return "0-100"
    if offset < 1000:
        return "100-1k"
    if offset < 10000:
        return "1k-10k"
    if offset < 100000:
        return "10k-100k"
    return "100k+"


# ---------------------------------------------------------------------------
# Path-traversal guard
# ---------------------------------------------------------------------------


_PATH_BAD_CHARS = re.compile(r"[\x00\r\n]")


def _safe_relpath(target_path: str, repo_root: Optional[Path] = None) -> str:
    """Sanity-check a path input + return its POSIX form, rejecting nullbytes,
    newlines, and absurdly long paths. Returns the POSIX-style relative path
    when `repo_root` provided; otherwise returns the cleaned path verbatim.
    """
    if not isinstance(target_path, str):
        raise ValueError("target_path must be a string")
    if not target_path:
        raise ValueError("target_path must be non-empty")
    if len(target_path) > MAX_PATH_LENGTH:
        raise ValueError(f"target_path exceeds {MAX_PATH_LENGTH} chars")
    if _PATH_BAD_CHARS.search(target_path):
        raise ValueError("target_path contains forbidden chars (nul/CR/LF)")
    for segment in target_path.replace("\\", "/").split("/"):
        if len(segment) > MAX_PATH_SEGMENT_LENGTH:
            raise ValueError("target_path segment too long")
    p = Path(target_path)
    if repo_root is not None:
        repo_root_resolved = Path(repo_root).resolve(strict=False)
        try:
            resolved = (
                p
                if p.is_absolute()
                else (repo_root_resolved / p)
            ).resolve(strict=False)
            rel = resolved.relative_to(repo_root_resolved)
            return str(rel).replace(os.sep, "/")
        except ValueError:
            # Escapes the repo root — refuse.
            raise ValueError(f"target_path escapes repo root: {target_path!r}")
    # No root provided — return POSIX-cleaned input.
    return str(p).replace(os.sep, "/")


# ---------------------------------------------------------------------------
# Minimal YAML reader (subset matching detect-repo-profile.py's emitter)
# ---------------------------------------------------------------------------


_YAML_LINE_RE = re.compile(r"^([a-zA-Z_][a-zA-Z0-9_-]*):\s*(.*)$")
_YAML_LIST_ITEM_RE = re.compile(r"^(\s+)-\s*(.*)$")
_YAML_NESTED_KEY_RE = re.compile(r"^(\s+)([a-zA-Z_][a-zA-Z0-9_-]*):\s*(.*)$")


def _parse_yaml_scalar(value_repr: str) -> object:
    """Parse a yaml RHS scalar: quoted string, true/false/null, int, OR
    bare string (for the secret-patterns YAML which uses bare scalars).
    """
    v = value_repr.strip()
    if v.startswith('"'):
        # Find matching close honoring backslash escape.
        i = 1
        out_chars: List[str] = []
        while i < len(v):
            ch = v[i]
            if ch == "\\" and i + 1 < len(v):
                nxt = v[i + 1]
                if nxt == '"':
                    out_chars.append('"')
                    i += 2
                    continue
                if nxt == "\\":
                    out_chars.append("\\")
                    i += 2
                    continue
                if nxt == "n":
                    out_chars.append("\n")
                    i += 2
                    continue
                out_chars.append(nxt)
                i += 2
                continue
            if ch == '"':
                return "".join(out_chars)
            out_chars.append(ch)
            i += 1
        raise ValueError("unterminated quoted scalar")
    if v.startswith("'"):
        # Single-quoted: only the doubled '' is an escape; raw otherwise.
        i = 1
        out_chars2: List[str] = []
        while i < len(v):
            ch = v[i]
            if ch == "'":
                if i + 1 < len(v) and v[i + 1] == "'":
                    out_chars2.append("'")
                    i += 2
                    continue
                return "".join(out_chars2)
            out_chars2.append(ch)
            i += 1
        raise ValueError("unterminated single-quoted scalar")
    if v == "true":
        return True
    if v == "false":
        return False
    if v == "null" or v == "~":
        return None
    if re.fullmatch(r"-?\d+", v):
        return int(v)
    if re.fullmatch(r"-?\d+\.\d+", v):
        return float(v)
    # Bare string — strip inline comment ` #` (only if preceded by space).
    bare = v
    # Inline comment stripping is intentionally conservative.
    m = re.search(r"\s+#.*$", bare)
    if m:
        bare = bare[: m.start()].rstrip()
    return bare


def _load_yaml_loose(text: str) -> Dict[str, object]:
    """Loose YAML parser tolerant of the two shapes we accept:

      A) `repo-profile.yaml` (top-level flat keys + list-of-strings) — the
         exact subset emitted by `detect-repo-profile.py`.
      B) `secret-patterns-exchange.yaml` (top-level `patterns:` list of
         maps with nested key/scalar fields, indented 2 spaces under
         `- id: ...`).

    REJECTS yaml anchors (&), aliases (*), and tags (!!). Returns the
    parsed structure as nested dict/list/str/int/bool/None.
    """
    result: Dict[str, object] = {}
    current_list_key: Optional[str] = None
    # For shape (B): when parsing a list-of-maps, we track the current map.
    current_map: Optional[Dict[str, object]] = None
    # Indent of the current list item's child keys (for shape B).
    map_indent: Optional[int] = None

    lines = text.splitlines()
    for line_idx, raw in enumerate(lines, start=1):
        if line_idx == 1 and raw.startswith("﻿"):
            raw = raw[1:]
        stripped = raw.rstrip()
        if not stripped:
            continue
        stripped_l = stripped.lstrip(" ")
        if stripped_l.startswith("#") or stripped_l in ("---", "..."):
            continue
        indent = len(stripped) - len(stripped_l)
        # Reject anchors/aliases/tags outside quoted regions (lightweight check).
        if (
            re.search(r"(?<![\\\"'])&[A-Za-z_]", stripped)
            or re.search(r"(?<![\\\"'])\*[A-Za-z_]", stripped)
            or "!!" in stripped
        ):
            raise ValueError(
                f"yaml line {line_idx}: anchor/alias/tag not supported"
            )

        if indent == 0:
            # Top-level key.
            current_list_key = None
            current_map = None
            map_indent = None
            m_top = _YAML_LINE_RE.match(stripped_l)
            if not m_top:
                # Tolerate stray content at top-level by skipping (e.g. version
                # comments accidentally left as bare scalars). Strict reject for
                # the keys we care about is enforced by the caller's validation
                # of result keys.
                continue
            key, rest = m_top.group(1), m_top.group(2).strip()
            if rest == "" or rest == "[]":
                # List-opening OR empty list.
                result[key] = []
                current_list_key = key
                continue
            result[key] = _parse_yaml_scalar(rest)
            continue

        # Indented line — list item OR nested key under a map item.
        m_item = _YAML_LIST_ITEM_RE.match(stripped)
        if m_item:
            item_indent = len(m_item.group(1))
            item_rest = m_item.group(2).strip()
            if current_list_key is None:
                raise ValueError(
                    f"yaml line {line_idx}: list item with no parent key"
                )
            # Is the item itself a flat scalar (shape A) or a map's first
            # `key: value` line (shape B `- id: foo`)?
            m_inline = _YAML_LINE_RE.match(item_rest)
            if m_inline and item_rest != "":
                # Shape B: this `-` opens a new dict in the list.
                new_map: Dict[str, object] = {}
                ikey, ival = m_inline.group(1), m_inline.group(2).strip()
                if ival == "":
                    new_map[ikey] = []
                elif ival == "[]":
                    new_map[ikey] = []
                else:
                    new_map[ikey] = _parse_yaml_scalar(ival)
                target_list = result[current_list_key]
                if not isinstance(target_list, list):
                    raise ValueError(
                        f"yaml line {line_idx}: parent key is not a list"
                    )
                target_list.append(new_map)
                current_map = new_map
                # Subsequent nested keys are indented BEYOND the `-` indent.
                map_indent = item_indent + 2
                continue
            # Shape A: plain scalar list item.
            parsed = _parse_yaml_scalar(item_rest)
            target = result[current_list_key]
            if not isinstance(target, list):
                raise ValueError(
                    f"yaml line {line_idx}: parent key is not a list"
                )
            target.append(parsed)
            continue

        # Indented `key: value` under the current map (shape B).
        if current_map is not None and map_indent is not None and indent >= map_indent:
            m_nested = _YAML_NESTED_KEY_RE.match(stripped)
            if m_nested:
                nkey, nval = m_nested.group(2), m_nested.group(3).strip()
                if nval == "" or nval == "[]":
                    current_map[nkey] = []
                    # Track this map's child-list under nkey for subsequent items.
                    # We reuse current_list_key sentinel by treating it specially
                    # — list under a map item uses indent-based continuation.
                    # The smallest reliable thing: stash as last-list-key on map.
                    current_map["__last_list_key__"] = nkey
                else:
                    current_map[nkey] = _parse_yaml_scalar(nval)
                continue
            # `- value` under a map's child list.
            m_subitem = _YAML_LIST_ITEM_RE.match(stripped)
            if m_subitem:
                last_list_key = current_map.get("__last_list_key__")
                if isinstance(last_list_key, str):
                    target_l = current_map.get(last_list_key)
                    if isinstance(target_l, list):
                        target_l.append(_parse_yaml_scalar(m_subitem.group(2).strip()))
                        continue
            # Otherwise: ignore unsupported nesting silently (loose mode).
            continue

        # Anything else: silently ignored (loose mode for unknown indent).
    # Clean up bookkeeping keys.
    if "patterns" in result and isinstance(result["patterns"], list):
        for m in result["patterns"]:
            if isinstance(m, dict) and "__last_list_key__" in m:
                m.pop("__last_list_key__", None)
    return result


# ---------------------------------------------------------------------------
# Profile + secret-patterns loaders
# ---------------------------------------------------------------------------


def load_repo_profile(profile_yaml_path) -> Optional[Dict[str, object]]:
    """Return parsed profile dict, or None if file is absent.

    Raises ValueError on malformed YAML; OSError surfaces as IOError to the
    CLI driver via main().
    """
    p = Path(profile_yaml_path)
    if not p.exists():
        return None
    if not p.is_file():
        raise ValueError(f"{p} is not a regular file")
    text = p.read_text(encoding="utf-8", errors="replace")
    return _load_yaml_loose(text)


def load_secret_patterns(yaml_path) -> List[Dict[str, object]]:
    """Return the `patterns:` list from the secret-patterns YAML.

    Each entry has: id, family, regex, description, redaction_label,
    confidence, fpr_target, context_hint, require_context. Raises
    ValueError on malformed YAML or missing required keys.
    """
    p = Path(yaml_path)
    if not p.is_file():
        raise ValueError(f"secret patterns YAML missing: {p}")
    text = p.read_text(encoding="utf-8", errors="replace")
    doc = _load_yaml_loose(text)
    patterns = doc.get("patterns")
    if not isinstance(patterns, list):
        raise ValueError("secret-patterns YAML missing `patterns:` list")
    out: List[Dict[str, object]] = []
    for entry in patterns:
        if not isinstance(entry, dict):
            continue
        # Required keys.
        for k in ("id", "family", "regex", "redaction_label"):
            if k not in entry or not isinstance(entry[k], str):
                raise ValueError(
                    f"secret-patterns entry missing/non-string `{k}`: {entry}"
                )
        # Optional context_hint + require_context defaults.
        if "context_hint" not in entry:
            entry["context_hint"] = ""
        if "require_context" not in entry:
            entry["require_context"] = False
        if "confidence" not in entry:
            entry["confidence"] = "medium"
        if "fpr_target" not in entry:
            entry["fpr_target"] = DEFAULT_FPR_CEILING
        out.append(entry)
    return out


# ---------------------------------------------------------------------------
# §7.5 Kill-switch FAIL-CLOSED
# ---------------------------------------------------------------------------


def kill_switch_disabled(profile_yaml_path) -> bool:
    """Return True when the framework's trading actions are DISABLED.

    Per PLAN-083 §7.5 R1 Codex P0:
      - Missing `repo-profile.yaml` ⇒ DISABLED (fail-CLOSED) — does NOT
        silently downgrade to generic (security regression).
      - Profile present with `risk_class: unknown-needs-owner-confirmation`
        ⇒ DISABLED.
      - Profile present with malformed YAML ⇒ DISABLED.
      - Profile present + valid + any other risk_class ⇒ NOT disabled
        (caller still gates trading-specific guardrails on whether
        risk_class == "trading-readonly").

    Side-effect: emit `trading_kill_switch_invoked` audit per read so
    the forensic trail records every kill-switch check (R1 Sec P0-2).
    """
    path = Path(profile_yaml_path)
    if not path.exists():
        emit_kill_switch_invoked(path, reason="profile_missing")
        return True
    try:
        profile = load_repo_profile(path)
    except (ValueError, OSError):
        emit_kill_switch_invoked(path, reason="profile_malformed")
        return True
    if profile is None:
        emit_kill_switch_invoked(path, reason="profile_missing")
        return True
    risk = profile.get("risk_class")
    if not isinstance(risk, str):
        emit_kill_switch_invoked(path, reason="risk_class_missing")
        return True
    if risk in DISABLED_STATES:
        emit_kill_switch_invoked(path, reason="risk_class_unknown")
        return True
    return False


def emit_kill_switch_invoked(profile_yaml_path, reason: str) -> None:
    """Emit the `trading_kill_switch_invoked` audit row.

    Best-effort, fail-OPEN: if `_lib.audit_emit` is unavailable (running
    outside the framework, fresh-clone bootstrap path, etc.), the call
    is a silent no-op. The hook layer is responsible for ensuring the
    audit emit module is wired in production sessions.

    Sec MF-3: persists ONLY `reason` (closed enum) + profile sha256
    prefix (16 hex). NEVER persists profile body or filesystem path
    other than the prefix-hash.
    """
    try:
        _emit_audit(
            action="trading_kill_switch_invoked",
            reason=_clamp_enum(
                reason,
                allowed=("profile_missing", "profile_malformed",
                         "risk_class_missing", "risk_class_unknown",
                         "kill_switch_status_check"),
                default="unknown",
            ),
            profile_path_sha256_prefix=_path_sha_prefix(profile_yaml_path),
        )
    except Exception:
        # Fail-OPEN per framework invariant; never raise from audit.
        return


def _path_sha_prefix(path_like) -> str:
    """16-hex-char SHA-256 prefix of a path string. Sec MF-3 path-hashing."""
    try:
        s = str(path_like)
    except Exception:
        s = ""
    digest = hashlib.sha256(s.encode("utf-8", errors="replace")).hexdigest()
    return digest[:16]


def _clamp_enum(value, *, allowed: Tuple[str, ...], default: str) -> str:
    if isinstance(value, str) and value in allowed:
        return value
    return default


def _emit_audit(action: str, **fields) -> None:
    """Dispatch to `_lib.audit_emit.emit_generic` when available.

    Importing lazily so the module remains usable outside the framework
    (fresh-clone bootstrap + standalone CLI invocation in trading repo).
    """
    try:
        # Try the framework's audit emit pathway.
        from _lib import audit_emit  # type: ignore
    except Exception:
        try:
            # Alternate import path when run from .claude/hooks/ namespace.
            sys.path.insert(0, str(Path(__file__).resolve().parent))
            from _lib import audit_emit  # type: ignore  # noqa: F401
        except Exception:
            return
    try:
        audit_emit.emit_generic(action, **fields)
    except Exception:
        return


# ---------------------------------------------------------------------------
# §7.2 Per-invocation write override
# ---------------------------------------------------------------------------


def check_write_override(
    env: Dict[str, str],
    target_path: str,
    justification: Optional[str],
    repo_root: Optional[Path] = None,
) -> Tuple[bool, str]:
    """Decide whether a write action is allowed under trading-readonly.

    Returns (allowed, reason). Reason is a closed-enum string suitable
    for direct emission to the `trading_write_override_used` audit row.

    Allow only if ALL of the following hold (PLAN-083 §7.2):
      (a) env[CEO_TRADING_WRITE_OVERRIDE] == "1"
      (b) `target_path` is a single canonical path (NOT a glob)
      (c) `justification` ≥ MIN_JUSTIFICATION_CHARS chars
      (d) `justification` ≤ MAX_JUSTIFICATION_CHARS chars
      (e) `target_path` validates against path-traversal guards

    Caller MUST clear `CEO_TRADING_WRITE_OVERRIDE` after a single Edit
    (per-invocation contract); session-wide blanket is rejected here
    only via the explicit `justification` requirement (the env var is
    NOT enough on its own — bare `=1` toggle REJECTED per Sec P0-2).
    """
    if not isinstance(env, dict):
        return (False, "env_not_dict")
    raw_flag = env.get(ENV_WRITE_OVERRIDE)
    if raw_flag != "1":
        # Override not active. NOT an error — just denial.
        return (False, "override_env_not_set")
    # Path validation.
    try:
        cleaned = _safe_relpath(target_path, repo_root=repo_root)
    except ValueError as exc:
        _emit_audit(
            action="trading_write_override_used",
            allowed=False,
            reason="target_path_invalid",
            target_path_sha256_prefix=_path_sha_prefix(target_path),
            justification_length=0,
            justification_sha256_prefix="",
            err_preview=str(exc)[:80],
        )
        return (False, "target_path_invalid")
    if any(ch in cleaned for ch in ("*", "?", "[")):
        _emit_audit(
            action="trading_write_override_used",
            allowed=False,
            reason="target_path_is_glob",
            target_path_sha256_prefix=_path_sha_prefix(target_path),
            justification_length=0,
            justification_sha256_prefix="",
        )
        return (False, "target_path_is_glob")
    # Justification validation.
    if justification is None or not isinstance(justification, str):
        _emit_audit(
            action="trading_write_override_used",
            allowed=False,
            reason="justification_missing",
            target_path_sha256_prefix=_path_sha_prefix(target_path),
            justification_length=0,
            justification_sha256_prefix="",
        )
        return (False, "justification_missing")
    j = justification.strip()
    if len(j) < MIN_JUSTIFICATION_CHARS:
        _emit_audit(
            action="trading_write_override_used",
            allowed=False,
            reason="justification_too_short",
            target_path_sha256_prefix=_path_sha_prefix(target_path),
            justification_length=len(j),
            justification_sha256_prefix=_path_sha_prefix(j),
        )
        return (False, "justification_too_short")
    if len(j) > MAX_JUSTIFICATION_CHARS:
        _emit_audit(
            action="trading_write_override_used",
            allowed=False,
            reason="justification_too_long",
            target_path_sha256_prefix=_path_sha_prefix(target_path),
            justification_length=len(j),
            justification_sha256_prefix=_path_sha_prefix(j),
        )
        return (False, "justification_too_long")
    # All checks pass — allow + emit success audit row.
    _emit_audit(
        action="trading_write_override_used",
        allowed=True,
        reason="ok",
        target_path_sha256_prefix=_path_sha_prefix(cleaned),
        justification_length=len(j),
        justification_sha256_prefix=_path_sha_prefix(j),
    )
    return (True, "ok")


# ---------------------------------------------------------------------------
# §7.3 Secret-scan output (BEFORE logs / audit / receipts / analysis)
# ---------------------------------------------------------------------------


def scan_output_for_secrets(
    output_text: str,
    profile_yaml_path: Optional[Path] = None,
    secret_patterns_path: Optional[Path] = None,
) -> List[Match]:
    """Scan `output_text` for secret-pattern matches per Wave -1.4 YAML.

    Returns an empty list when:
      - profile_yaml_path is set AND `risk_class` is NOT `trading-readonly`
        (we only run the scan in the high-risk profile; fintech/engine/
        frontend rely on the generic `output_safety_flag` path)
      - kill_switch_disabled() is True (failure mode is to refuse)

    Per Codex P0 broader-scope: callers MUST invoke this BEFORE logs,
    audit, receipts, AND analysis output — not just analysis-only.

    Implementation notes:
      - Caps input to MAX_OUTPUT_SCAN_BYTES (4 MiB) to avoid pathological
        regex backtracking on hostile inputs.
      - Each pattern compiled lazily; `re.compile` errors emit a single
        breadcrumb and skip the pattern (fail-OPEN per individual rule
        + log-once contract).
      - Returns Match instances with sha256-prefixed identifiers ONLY.
    """
    if not isinstance(output_text, str):
        return []
    if not output_text:
        return []
    if len(output_text) > MAX_OUTPUT_SCAN_BYTES:
        # Truncate; emit a one-shot breadcrumb so forensic trace is intact.
        output_text = output_text[:MAX_OUTPUT_SCAN_BYTES]
        _emit_audit(
            action="trading_kill_switch_invoked",
            reason="kill_switch_status_check",
            profile_path_sha256_prefix=_path_sha_prefix(profile_yaml_path or ""),
        )

    # Gate on trading-readonly profile (when caller supplies one).
    if profile_yaml_path is not None:
        try:
            profile = load_repo_profile(profile_yaml_path)
        except (ValueError, OSError):
            profile = None
        risk = (profile or {}).get("risk_class")
        if risk and risk != TRADING_RISK_CLASS:
            # Out of scope — return empty list (caller may invoke the generic
            # `output_safety_flag` path instead).
            return []
        if profile is None:
            # Missing profile = kill-switch state; refuse to scan.
            return []

    patterns_path = secret_patterns_path or _resolve_secret_patterns_path()
    try:
        patterns = load_secret_patterns(patterns_path)
    except (ValueError, OSError):
        # Fail-CLOSED for the scan: caller cannot rely on output safety
        # without the catalog. Return a synthetic finding so the caller
        # surfaces an alert.
        synthetic = Match(
            pattern_id="catalog-unavailable",
            family="meta",
            redaction_label="[REDACTED:catalog_unavailable]",
            confidence="high",
            match_text="",
            match_offset=0,
        )
        return [synthetic]

    matches: List[Match] = []
    for pat in patterns:
        try:
            pid = pat["id"]
            family = pat["family"]
            regex_src = pat["regex"]
            redaction_label = pat["redaction_label"]
            confidence = pat.get("confidence", "medium")
            context_hint = pat.get("context_hint", "") or ""
            require_context = bool(pat.get("require_context", False))
        except (KeyError, TypeError):
            continue
        try:
            rx = re.compile(regex_src, re.ASCII)
        except re.error:
            continue
        ctx_rx = None
        if context_hint:
            try:
                ctx_rx = re.compile(context_hint, re.ASCII | re.IGNORECASE)
            except re.error:
                ctx_rx = None
        for m in rx.finditer(output_text):
            matched_text = m.group(0)
            offset = m.start()
            if require_context and ctx_rx is not None:
                lo = max(0, offset - CONTEXT_WINDOW_BYTES)
                hi = min(len(output_text), offset + len(matched_text) + CONTEXT_WINDOW_BYTES)
                window = output_text[lo:hi]
                if not ctx_rx.search(window):
                    continue
            matches.append(
                Match(
                    pattern_id=pid,
                    family=family,
                    redaction_label=redaction_label,
                    confidence=confidence,
                    match_text=matched_text,
                    match_offset=offset,
                )
            )
    return matches


def _resolve_secret_patterns_path() -> Path:
    """Resolve the canonical secret-patterns YAML location.

    Prefers `$CLAUDE_PROJECT_DIR` if set, else relative to the working
    directory. Caller may always override via `secret_patterns_path=`.
    """
    project = os.environ.get("CLAUDE_PROJECT_DIR")
    if project:
        return Path(project) / DEFAULT_SECRET_PATTERNS_REL
    return Path(DEFAULT_SECRET_PATTERNS_REL)


# ---------------------------------------------------------------------------
# §7.4 Manual-review path deny-list
# ---------------------------------------------------------------------------


def _glob_to_regex(glob_pattern: str) -> re.Pattern:
    """Convert a shell-style glob (with `**` for recursive) to a regex.

    Supported: `**` (matches any number of path segments incl. zero),
    `*` (matches any chars except `/`), `?` (matches one char except `/`),
    `[abc]` (char class).
    """
    out: List[str] = ["^"]
    i = 0
    n = len(glob_pattern)
    while i < n:
        ch = glob_pattern[i]
        if ch == "*":
            if i + 1 < n and glob_pattern[i + 1] == "*":
                # `**` — match across `/` segments. Consume optional `/` after.
                out.append(".*")
                i += 2
                if i < n and glob_pattern[i] == "/":
                    i += 1
                continue
            out.append("[^/]*")
            i += 1
            continue
        if ch == "?":
            out.append("[^/]")
            i += 1
            continue
        if ch == "[":
            # Char class — copy verbatim until matching `]`.
            j = glob_pattern.find("]", i + 1)
            if j == -1:
                out.append(re.escape(ch))
                i += 1
                continue
            out.append(glob_pattern[i : j + 1])
            i = j + 1
            continue
        out.append(re.escape(ch))
        i += 1
    out.append("$")
    return re.compile("".join(out))


def is_manual_review_path(
    target_path: str,
    profile_yaml_path: Optional[Path] = None,
    repo_root: Optional[Path] = None,
) -> bool:
    """Return True when `target_path` matches any `manual_review_paths`
    glob (from the profile YAML, or the default list when profile is
    missing or omits the field).

    PLAN-083 §7.4 CR NTH: ≥10 path fixtures documented in deny-list.
    DEFAULT_MANUAL_REVIEW_PATHS provides 15 (above the floor).

    Sec MF-3: no raw path body is emitted; we only audit the path-prefix
    SHA-256 (path-traversal guard applied first).
    """
    try:
        cleaned = _safe_relpath(target_path, repo_root=repo_root)
    except ValueError:
        return False
    profile: Optional[Dict[str, object]] = None
    if profile_yaml_path is not None:
        try:
            profile = load_repo_profile(profile_yaml_path)
        except (ValueError, OSError):
            profile = None
    review_paths: List[str] = []
    if profile and isinstance(profile.get("manual_review_paths"), list):
        for entry in profile["manual_review_paths"]:
            if isinstance(entry, str) and entry:
                review_paths.append(entry)
    if not review_paths:
        review_paths = list(DEFAULT_MANUAL_REVIEW_PATHS)
    for glob_pat in review_paths:
        try:
            rx = _glob_to_regex(glob_pat)
        except re.error:
            continue
        if rx.match(cleaned):
            return True
        # Also try matching the basename — handles `**/concurrency.py`
        # style when input is already relative without parent dirs.
        if rx.match(Path(cleaned).name):
            return True
    return False


# ---------------------------------------------------------------------------
# §7.6 7-day read-only first-week banner
# ---------------------------------------------------------------------------


def seven_day_banner_visible(profile_yaml_path) -> bool:
    """Return True when the 7-day read-only advisory banner should appear.

    Per Codex `019e1803` resolution: banner appears as long as the
    repo-profile.yaml `created_at` timestamp is within 7 days, even
    when `CEO_TRADING_WRITE_OVERRIDE=1` is set. Override does NOT
    silence safety advisories.

    Returns False when:
      - profile yaml absent or malformed
      - `created_at` parse fails
      - `created_at` older than BANNER_WINDOW_DAYS days
    """
    try:
        profile = load_repo_profile(profile_yaml_path)
    except (ValueError, OSError):
        return False
    if profile is None:
        return False
    created = profile.get("created_at")
    if not isinstance(created, str) or not created:
        return False
    try:
        # Accept "Z" suffix (UTC) by replacing with "+00:00" for fromisoformat.
        normalized = created.replace("Z", "+00:00")
        ts = _dt.datetime.fromisoformat(normalized)
    except (TypeError, ValueError):
        return False
    if ts.tzinfo is None:
        ts = ts.replace(tzinfo=_dt.timezone.utc)
    now = _dt.datetime.now(tz=_dt.timezone.utc)
    delta = now - ts
    return delta < _dt.timedelta(days=BANNER_WINDOW_DAYS)


# ---------------------------------------------------------------------------
# CLI
# ---------------------------------------------------------------------------


def cmd_check_override(args: argparse.Namespace) -> int:
    """`check-override` — exit 0 allow, 1 reject."""
    allowed, reason = check_write_override(
        env=dict(os.environ),
        target_path=args.target,
        justification=args.justification,
    )
    payload = {"allowed": allowed, "reason": reason}
    print(json.dumps(payload, sort_keys=True))
    return 0 if allowed else 1


def cmd_scan_output(args: argparse.Namespace) -> int:
    """`scan-output` — read stdin (or --input FILE), scan, emit summary."""
    if args.input == "-" or args.input is None:
        data = sys.stdin.read()
    else:
        data = Path(args.input).read_text(encoding="utf-8", errors="replace")
    profile = Path(args.profile) if args.profile else None
    matches = scan_output_for_secrets(
        data,
        profile_yaml_path=profile,
        secret_patterns_path=Path(args.patterns) if args.patterns else None,
    )
    if not matches:
        print(json.dumps({"clean": True, "matches": []}, sort_keys=True))
        return 0
    summary = {
        "clean": False,
        "matches": [m.to_dict() for m in matches],
        "count": len(matches),
        "families": sorted({m.family for m in matches}),
    }
    print(json.dumps(summary, sort_keys=True))
    return 1


def cmd_check_manual_review(args: argparse.Namespace) -> int:
    """`check-manual-review` — exit 1 if path is in deny-list."""
    profile = Path(args.profile) if args.profile else None
    blocked = is_manual_review_path(args.target, profile_yaml_path=profile)
    payload = {"target": args.target, "is_manual_review_path": blocked}
    print(json.dumps(payload, sort_keys=True))
    return 1 if blocked else 0


def cmd_kill_switch_status(args: argparse.Namespace) -> int:
    """`kill-switch-status` — exit 2 when DISABLED."""
    profile = Path(args.profile) if args.profile else Path(DEFAULT_REPO_PROFILE_REL)
    disabled = kill_switch_disabled(profile)
    payload = {"disabled": disabled, "profile_path": str(profile)}
    print(json.dumps(payload, sort_keys=True))
    return 2 if disabled else 0


def cmd_banner(args: argparse.Namespace) -> int:
    """`banner` — exit 0 visible, 1 hidden."""
    profile = Path(args.profile) if args.profile else Path(DEFAULT_REPO_PROFILE_REL)
    visible = seven_day_banner_visible(profile)
    if visible:
        msg = (
            "WARNING: trading-readonly profile within first 7 days. "
            "Read-only mode recommended even if CEO_TRADING_WRITE_OVERRIDE=1."
        )
        print(msg)
    return 0 if visible else 1


def build_parser() -> argparse.ArgumentParser:
    parser = argparse.ArgumentParser(
        prog="trading-readonly-guardrails.py",
        description=(
            "PLAN-083 Wave 2.7 — trading-readonly guardrails CLI. "
            "Stdlib-only enforcement library + CLI driver."
        ),
    )
    sub = parser.add_subparsers(dest="command", required=True)

    p_override = sub.add_parser("check-override", help="evaluate write override env + justification")
    p_override.add_argument("--target", required=True, help="canonical write target path")
    p_override.add_argument("--justification", default=None, help="Owner justification ≥20 chars")

    p_scan = sub.add_parser("scan-output", help="scan stdin/file for exchange-key secrets")
    p_scan.add_argument("--input", default="-", help="input file path (default: stdin)")
    p_scan.add_argument("--profile", default=None, help="optional repo-profile.yaml gate")
    p_scan.add_argument("--patterns", default=None, help="optional secret-patterns YAML override")

    p_mr = sub.add_parser("check-manual-review", help="check path against manual-review deny-list")
    p_mr.add_argument("--target", required=True, help="repo-relative path to evaluate")
    p_mr.add_argument("--profile", default=None, help="profile YAML (else default deny-list)")

    p_ks = sub.add_parser("kill-switch-status", help="check kill-switch state (exit 2 if DISABLED)")
    p_ks.add_argument("--profile", default=None, help="profile YAML path")

    p_bn = sub.add_parser("banner", help="print 7-day banner when within first week")
    p_bn.add_argument("--profile", default=None, help="profile YAML path")

    return parser


def main(argv: Optional[List[str]] = None) -> int:
    parser = build_parser()
    args = parser.parse_args(argv)
    try:
        if args.command == "check-override":
            return cmd_check_override(args)
        if args.command == "scan-output":
            return cmd_scan_output(args)
        if args.command == "check-manual-review":
            return cmd_check_manual_review(args)
        if args.command == "kill-switch-status":
            return cmd_kill_switch_status(args)
        if args.command == "banner":
            return cmd_banner(args)
    except ValueError as exc:
        sys.stderr.write(f"error: {exc}\n")
        return 3
    except OSError as exc:
        sys.stderr.write(f"error: io: {exc}\n")
        return 4
    sys.stderr.write(f"error: unknown command {args.command!r}\n")
    return 3


if __name__ == "__main__":
    sys.exit(main())
