#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
detect-repo-profile.py — PLAN-083 Wave 0a sub-agent 0.6.

Fail-CLOSED detector for repo `risk_class` (one of frontend / engine /
fintech / trading-readonly / generic / unknown-needs-owner-confirmation).
Reads filesystem signals (package.json, pyproject.toml, Cargo.toml,
*.sol, compliance/, kyc/, strategies/, exchanges/, etc.) and writes
the canonical `.claude/repo-profile.yaml` consumed by:

  - sub-agent 2.1 first-run wizard
  - sub-agent 2.7 trading-readonly hooks + 7-day read-only banner
  - sub-agent 0.7d smart-loading-resolver (per-profile cap table)

Key invariants (per PLAN-083 §7.1, §7.5, §7.6 + R1 Codex P0):
  1. Unknown / mixed structure -> fail-CLOSED to `trading-readonly`
     (most restrictive), NOT silent `generic`.
  2. No signals at all -> `unknown-needs-owner-confirmation` + exit 2.
     Caller must run `confirm-profile <name>` to proceed.
  3. `generic` is reachable ONLY via explicit Owner `confirm-profile generic`
     (never via auto-detect).
  4. Existing `.claude/repo-profile.yaml` with `manual_override: true`
     is respected; `detect` re-runs heuristics but refuses to overwrite,
     printing the divergence (if any) and exiting non-zero.
  5. STDLIB ONLY. Python 3.9+. No PyYAML, no external deps.

CLI:
  detect-repo-profile.py detect [--target PATH] [--json]
  detect-repo-profile.py confirm-profile NAME [--target PATH] [--notes TEXT]
  detect-repo-profile.py show [--target PATH] [--json]

Exit codes:
  0 — success (auto-detected high/medium confidence OR confirmation applied)
  1 — soft failure (`trading-readonly` fail-CLOSED on ambiguous repo; file written)
  2 — hard failure (`unknown-needs-owner-confirmation`; caller must confirm)
  3 — usage error (bad CLI args / unknown profile name / refused overwrite)
  4 — IO / schema error (file unreadable, malformed existing yaml)
"""

from __future__ import annotations

import argparse
import datetime as _dt
import json
import os
import re
import sys
from pathlib import Path
from typing import Dict, List, Optional, Tuple

# ---------------------------------------------------------------------------
# Constants
# ---------------------------------------------------------------------------

SCHEMA_VERSION = "1"

# PLAN-097 Wave C.1 — size_class field (independent of risk_class).
# Boundaries per PLAN-097 §3 Wave C.1 (left-closed right-open):
#   SMALL  = [0, 50_000) LoC
#   MEDIUM = [50_000, 200_000) LoC
#   LARGE  = [200_000, ∞) LoC
SMALL_LOC_MAX = 50_000
MEDIUM_LOC_MAX = 200_000

VALID_SIZE_CLASSES = ("SMALL", "MEDIUM", "LARGE")

VALID_PROFILES = (
    "frontend",
    "engine",
    "fintech",
    "trading-readonly",
    "generic",
    "unknown-needs-owner-confirmation",
)

# Profiles reachable via auto-detect. `generic` and
# `unknown-needs-owner-confirmation` are excluded — `generic` requires
# explicit Owner confirmation, `unknown-needs-owner-confirmation` is the
# no-signals sentinel.
AUTO_DETECTABLE = ("frontend", "engine", "fintech", "trading-readonly")

# Default trading-readonly deny-list (>=10 path globs per PLAN-083 CR NTH).
# Each glob is matched against POSIX relative paths from repo root.
DEFAULT_TRADING_MANUAL_REVIEW_PATHS = (
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

# Strong file-presence signals -> (signal_slug, profile_vote).
# Order matters: later entries can override only when explicitly merged
# in the scoring step.
STRONG_FILE_SIGNALS = (
    ("Cargo.toml", "trading-readonly-or-engine"),  # ambiguous; refined below
)

# Frontmatter regexes for package.json + pyproject.toml content.
FRONTEND_DEP_REGEX = re.compile(
    r'"(?:next|react|vue|@angular/core|svelte|nuxt|remix|astro|gatsby|solid-js)"\s*:',
    re.IGNORECASE,
)
ENGINE_PY_DEP_REGEX = re.compile(
    r"(?:^|[\s'\"\[=,])"  # boundary
    r"(?:fastapi|django|flask|starlette|aiohttp|sanic|tornado|quart|litestar)"
    r"(?:[\s'\"\]=,<>~!^]|$)",
    re.IGNORECASE | re.MULTILINE,
)
ENGINE_NODE_DEP_REGEX = re.compile(
    r'"(?:express|fastify|koa|hapi|nestjs|@nestjs/core)"\s*:',
    re.IGNORECASE,
)
TRADING_KEY_REGEX = re.compile(
    r"(?:^|[\s'\"=:])"
    r"(?:BINANCE|COINBASE|KRAKEN|BITFINEX|BYBIT|OKX|KUCOIN|BITSTAMP)_API_KEY"
    r"(?:[\s'\"=:]|$)",
    re.IGNORECASE | re.MULTILINE,
)
COMPLIANCE_HINT_REGEX = re.compile(
    r"(?:^|[\s'\"=:,/])"
    r"(?:kyc|aml|pci-dss|sox|cvm|finra|mifid|lgpd|gdpr)"
    r"(?:[\s'\"=:,/]|$)",
    re.IGNORECASE | re.MULTILINE,
)
FINTECH_DEP_REGEX = re.compile(
    r'"(?:stripe|plaid|web3|ethers|@solana/web3\.js|braintree|adyen|dlt|big.js|decimal\.js)"\s*:',
    re.IGNORECASE,
)

# Directory-presence signals — substring match against repo-relative dirs.
TRADING_DIR_HINTS = (
    "strategies",
    "arbitrage",
    "exchanges",
    "bot",
    "trading",
    "orderbook",
    "market_data",
)
COMPLIANCE_DIR_HINTS = (
    "compliance",
    "kyc",
    "aml",
    "lgpd",
    "audit-trail",
    "regulatory",
)
FINTECH_DIR_HINTS = (
    "ledger",
    "ledgers",
    "balances",
    "transactions",
    "payments",
    "billing",
    "wallets",
)

# Path-traversal max-walk depth (defense in depth; we only need top-level
# + 2-3 levels deep for signal harvesting).
MAX_WALK_DEPTH = 4

# Files we never read (binary / huge / lock files we don't need).
SKIP_FILE_NAMES = frozenset(
    [
        "package-lock.json",
        "yarn.lock",
        "pnpm-lock.yaml",
        "poetry.lock",
        "uv.lock",
        "Pipfile.lock",
        "Cargo.lock",
        "go.sum",
    ]
)

# Files capped at this read size (bytes). package.json/pyproject.toml etc
# rarely exceed 200KB; we cap to keep detector fast + safe.
MAX_FILE_READ_BYTES = 256 * 1024


# ---------------------------------------------------------------------------
# Tiny YAML emitter + parser (stdlib only)
#
# We intentionally do NOT depend on PyYAML. The repo-profile.yaml schema is
# flat + well-controlled: keys are strings, values are scalars / lists of
# strings / booleans. We emit deterministic YAML with stable key ordering
# and reject yaml anchors/aliases when reading.
# ---------------------------------------------------------------------------

_YAML_KEY_ORDER = (
    "schema_version",
    "risk_class",
    "size_class",         # PLAN-097 Wave C.1 — SMALL/MEDIUM/LARGE (optional)
    "loc_count",          # PLAN-097 Wave C.1 — raw LoC count (optional)
    "detected_at",
    "confidence",
    "manual_override",
    "created_at",
    "signals",
    "manual_review_paths",
    "notes",
)


def _yaml_escape_scalar(value) -> str:
    """Render a scalar for inclusion on the RHS of `key: value`."""
    if isinstance(value, bool):
        return "true" if value else "false"
    if isinstance(value, int):
        return str(value)
    if value is None:
        return "null"
    s = str(value)
    # Always quote strings to avoid YAML's surprising bare-scalar rules
    # (e.g. "no" -> False, "2026-05-11" -> date object in PyYAML 1.1).
    # We use double-quotes and escape backslash + double-quote.
    escaped = s.replace("\\", "\\\\").replace('"', '\\"')
    # Reject embedded newlines in scalars — schema fields are all single-line.
    if "\n" in escaped or "\r" in escaped:
        raise ValueError("repo-profile scalar values must not contain newlines")
    return '"' + escaped + '"'


def emit_yaml(profile: Dict[str, object]) -> str:
    """Render `profile` dict as a deterministic YAML document.

    Keys follow `_YAML_KEY_ORDER`; unknown keys appended last in sorted
    order. Lists render block-style. No anchors, no aliases, no flow
    style. Returns a string ending with a single trailing newline.
    """
    lines: List[str] = ["# .claude/repo-profile.yaml"]
    lines.append("# Generated by detect-repo-profile.py (PLAN-083 Wave 0a sub-agent 0.6).")
    lines.append("# Do not hand-edit unless you understand the kill-switch fail-CLOSED")
    lines.append("# contract documented in PLAN-083 §7.5. Use `confirm-profile` to change.")
    lines.append("---")

    known = set(_YAML_KEY_ORDER)
    extra_keys = sorted(k for k in profile.keys() if k not in known)
    ordered_keys = [k for k in _YAML_KEY_ORDER if k in profile] + extra_keys

    for key in ordered_keys:
        value = profile[key]
        if isinstance(value, list):
            if not value:
                lines.append(f"{key}: []")
            else:
                lines.append(f"{key}:")
                for item in value:
                    lines.append(f"  - {_yaml_escape_scalar(item)}")
        else:
            lines.append(f"{key}: {_yaml_escape_scalar(value)}")
    return "\n".join(lines) + "\n"


_YAML_LINE_RE = re.compile(r"^([a-zA-Z_][a-zA-Z0-9_]*):\s*(.*)$")
_YAML_LIST_ITEM_RE = re.compile(r"^\s+-\s*(.*)$")


def _strip_quoted_scalars(line: str) -> str:
    """Return `line` with all double-quoted regions replaced by `""`.

    Used to safety-check structural tokens (`*`, `&`, `!!`, `{`) only
    OUTSIDE of legitimate string scalars like `"strategies/**"`. Honors
    backslash escaping of `"` inside quoted regions.
    """
    out_chars: List[str] = []
    i = 0
    in_quote = False
    while i < len(line):
        ch = line[i]
        if not in_quote:
            if ch == '"':
                in_quote = True
                out_chars.append('"')
                i += 1
                continue
            out_chars.append(ch)
            i += 1
            continue
        # Inside quoted region — consume until matching close.
        if ch == "\\" and i + 1 < len(line):
            i += 2
            continue
        if ch == '"':
            in_quote = False
            out_chars.append('"')
            i += 1
            continue
        i += 1
    return "".join(out_chars)


def parse_yaml(text: str) -> Dict[str, object]:
    """Minimal stdlib YAML parser for the exact subset we emit.

    Supports: top-level `key: scalar`, top-level `key: []`, top-level
    `key:` followed by `  - "item"` lines. Rejects anchors (&), aliases
    (*), tags (!!), flow style ([..], {..}) except empty `[]`, and any
    nested mapping. Strict by design — if a future schema extension
    needs nesting, parse_yaml will refuse and the caller exits with
    code 4. This is correct: better to fail-CLOSED than mis-parse.
    """
    result: Dict[str, object] = {}
    current_list_key: Optional[str] = None

    for raw_idx, raw in enumerate(text.splitlines(), start=1):
        # Strip a possible UTF-8 BOM only on the first line.
        if raw_idx == 1 and raw.startswith("﻿"):
            raw = raw[1:]
        stripped = raw.rstrip()
        if not stripped:
            current_list_key = None
            continue
        # Comment / document separator.
        if stripped.startswith("#") or stripped == "---" or stripped == "...":
            continue
        # Reject anchors / aliases / tags / flow-style braces upfront.
        # We only check the STRUCTURAL portion (outside quoted strings) for
        # these tokens, so that legitimate scalars like "strategies/**" or
        # "a*b" do NOT trip the safety check.
        _structural = _strip_quoted_scalars(stripped)
        if (
            "&" in _structural
            or "*" in _structural
            or "!!" in _structural
            or "{" in _structural
        ):
            raise ValueError(
                f"line {raw_idx}: yaml feature not supported (anchor/alias/tag/flow-map)"
            )
        # List item under current_list_key.
        m_item = _YAML_LIST_ITEM_RE.match(stripped)
        if m_item:
            if current_list_key is None:
                raise ValueError(f"line {raw_idx}: list item with no parent key")
            value_repr = m_item.group(1).strip()
            parsed = _parse_scalar(value_repr, raw_idx)
            target = result[current_list_key]
            if not isinstance(target, list):
                raise ValueError(f"line {raw_idx}: parent key is not a list")
            target.append(parsed)
            continue
        # Reject any leading whitespace at this point — we only allow
        # 0-indent keys + 2-indent list items.
        if stripped != stripped.lstrip():
            raise ValueError(f"line {raw_idx}: unexpected indentation")
        # `key: value` or `key:` (list-opening).
        m_key = _YAML_LINE_RE.match(stripped)
        if not m_key:
            raise ValueError(f"line {raw_idx}: cannot parse (expected `key: value`)")
        key, rest = m_key.group(1), m_key.group(2).strip()
        if rest == "":
            # `key:` opens a block list on subsequent lines.
            result[key] = []
            current_list_key = key
            continue
        if rest == "[]":
            result[key] = []
            current_list_key = None
            continue
        result[key] = _parse_scalar(rest, raw_idx)
        current_list_key = None

    return result


def _parse_scalar(value_repr: str, line_no: int) -> object:
    """Parse a single scalar from yaml RHS. Accepts double-quoted strings,
    bare true/false/null, and integers. Anything else is an error.
    """
    v = value_repr.strip()
    # Strip optional trailing inline comment (` #` form).
    # Only when not inside a quoted string.
    if v.startswith('"'):
        # Find matching closing quote honoring `\"` escape.
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
                # Unknown escape — preserve literally.
                out_chars.append(nxt)
                i += 2
                continue
            if ch == '"':
                # End of scalar.
                return "".join(out_chars)
            out_chars.append(ch)
            i += 1
        raise ValueError(f"line {line_no}: unterminated quoted scalar")
    # Bare values.
    if v == "true":
        return True
    if v == "false":
        return False
    if v == "null" or v == "~":
        return None
    # Integer literal.
    if re.fullmatch(r"-?\d+", v):
        return int(v)
    # Reject unquoted strings — schema requires quoted strings for safety
    # (avoids the no/yes/on/off + ISO-date YAML 1.1 surprises).
    raise ValueError(
        f"line {line_no}: bare scalar `{v[:40]}` rejected (quote string scalars)"
    )


# ---------------------------------------------------------------------------
# Filesystem signal harvesting
# ---------------------------------------------------------------------------


def _safe_resolve_target(target: str) -> Path:
    """Resolve and validate a --target path; refuse symlink escape."""
    p = Path(target).expanduser().resolve(strict=False)
    if not p.exists():
        raise FileNotFoundError(f"target does not exist: {p}")
    if not p.is_dir():
        raise NotADirectoryError(f"target is not a directory: {p}")
    return p


def _read_text_safe(path: Path) -> Optional[str]:
    """Read a text file with size cap + utf-8 + skip-on-error."""
    try:
        if not path.is_file():
            return None
        size = path.stat().st_size
        if size > MAX_FILE_READ_BYTES:
            with path.open("rb") as fh:
                raw = fh.read(MAX_FILE_READ_BYTES)
        else:
            with path.open("rb") as fh:
                raw = fh.read()
        return raw.decode("utf-8", errors="replace")
    except OSError:
        return None


def _walk_top_dirs(root: Path, max_depth: int = MAX_WALK_DEPTH) -> List[Path]:
    """Collect directory entries up to `max_depth` levels under root, while
    refusing to follow symlinks that escape root.
    """
    collected: List[Path] = []
    root_resolved = root.resolve(strict=False)
    stack: List[Tuple[Path, int]] = [(root_resolved, 0)]
    while stack:
        cur, depth = stack.pop()
        if depth > max_depth:
            continue
        try:
            entries = list(cur.iterdir())
        except OSError:
            continue
        for entry in entries:
            if entry.is_symlink():
                try:
                    resolved = entry.resolve(strict=False)
                    # Refuse to traverse symlinks escaping root.
                    resolved.relative_to(root_resolved)
                except (OSError, ValueError):
                    continue
            if entry.is_dir():
                name = entry.name
                if name in {".git", "node_modules", ".venv", "venv", "__pycache__", "dist", "build", "target"}:
                    continue
                collected.append(entry)
                stack.append((entry, depth + 1))
    return collected


def _collect_dir_names(root: Path) -> List[str]:
    """Return lowercased relative directory names under root."""
    names: List[str] = []
    for d in _walk_top_dirs(root):
        try:
            rel = d.resolve().relative_to(root.resolve())
        except ValueError:
            continue
        names.append(str(rel).lower())
    return names


def _has_dir_hint(dir_names: List[str], hints: Tuple[str, ...]) -> List[str]:
    """Return list of hits (signal slugs) for dir hints found."""
    hits: List[str] = []
    for hint in hints:
        for d in dir_names:
            parts = d.split(os.sep)
            if hint in parts:
                hits.append(f"dir:{hint}/")
                break
    return hits


def _has_file_pattern(root: Path, pattern: str, max_results: int = 5) -> List[str]:
    """Find up to `max_results` files matching glob pattern under root."""
    hits: List[str] = []
    try:
        for match in root.rglob(pattern):
            if match.is_file():
                try:
                    rel = match.resolve().relative_to(root.resolve())
                except ValueError:
                    continue
                hits.append(str(rel))
                if len(hits) >= max_results:
                    break
    except OSError:
        pass
    return hits


# ---------------------------------------------------------------------------
# PLAN-097 Wave C.1 — Size-class detection (LoC counting)
# ---------------------------------------------------------------------------

# Extensions counted as source LoC (per PLAN-097 §AC10 corpus methodology).
_SOURCE_EXTS = frozenset(
    [
        ".py", ".pyi",
        ".js", ".jsx", ".ts", ".tsx", ".mjs", ".cjs",
        ".rs",
        ".go",
        ".java", ".kt",
        ".rb",
        ".php",
        ".c", ".h", ".cc", ".cpp", ".hpp", ".cxx", ".hxx",
        ".cs",
        ".swift",
        ".scala",
        ".sol",
        ".sh", ".bash",
        ".sql",
        ".vue", ".svelte",
    ]
)

# Directories ALWAYS skipped during LoC count (per PLAN-097 §3 Wave C.1).
_LOC_SKIP_DIRS = frozenset(
    [
        "node_modules",
        "vendor",
        ".venv",
        "venv",
        "__pycache__",
        ".git",
        ".pytest_cache",
        "dist",
        "build",
        "target",
        ".next",
        ".nuxt",
        ".cache",
        "coverage",
        ".tox",
    ]
)


def _is_under_skip_dir(rel: Path) -> bool:
    """True if any path segment matches `_LOC_SKIP_DIRS`."""
    for part in rel.parts:
        if part in _LOC_SKIP_DIRS:
            return True
    return False


def _read_gitignore_patterns(root: Path) -> List[str]:
    """Read top-level `.gitignore` patterns (best-effort, stdlib-only)."""
    gi_path = root / ".gitignore"
    if not gi_path.is_file():
        return []
    text = _read_text_safe(gi_path) or ""
    patterns: List[str] = []
    for raw in text.splitlines():
        line = raw.strip()
        if not line or line.startswith("#"):
            continue
        patterns.append(line)
    return patterns


def _matches_gitignore_pattern(rel_posix: str, patterns: List[str]) -> bool:
    """Best-effort `.gitignore` match — supports simple `*`, `**`, dir prefixes.
    NOT a full gitignore parser; suffices for typical adopter patterns
    (`node_modules/`, `dist/**`, `*.lock`).
    """
    import fnmatch  # local import — stdlib
    for pat in patterns:
        # Strip leading slash + handle dir-suffix patterns.
        p = pat
        if p.startswith("/"):
            p = p[1:]
        # `dir/` pattern → match anything under that dir.
        if p.endswith("/"):
            if rel_posix.startswith(p) or f"/{p}" in rel_posix:
                return True
            continue
        # Use fnmatch (simple globs only — `**` collapsed to `*`).
        p_simple = p.replace("**", "*")
        if fnmatch.fnmatch(rel_posix, p_simple):
            return True
        # Match path SEGMENT (e.g., "node_modules" pattern matches any
        # `node_modules/` path component).
        parts = rel_posix.split("/")
        for part in parts:
            if fnmatch.fnmatch(part, p_simple):
                return True
    return False


def _count_loc(root: Path) -> int:
    """Count LoC across source files under root.

    Walking rules (per PLAN-097 §3 Wave C.1):
      - `.gitignore`-respecting walk (top-level .gitignore only)
      - skip `_LOC_SKIP_DIRS` segments
      - skip symlinks (NOT followed)
      - count only files with `_SOURCE_EXTS` suffix
      - line count = `\n` count (stdlib pathlib + io)

    Deterministic: file iteration uses sorted POSIX paths.
    """
    if not root.exists() or not root.is_dir():
        return 0
    gi_patterns = _read_gitignore_patterns(root)
    total = 0
    try:
        root_resolved = root.resolve(strict=False)
    except OSError:
        return 0
    for entry in sorted(root_resolved.rglob("*"), key=lambda p: p.as_posix()):
        try:
            if entry.is_symlink():
                continue
            if not entry.is_file():
                continue
        except OSError:
            continue
        suffix = entry.suffix.lower()
        if suffix not in _SOURCE_EXTS:
            continue
        try:
            rel = entry.relative_to(root_resolved)
        except ValueError:
            continue
        if _is_under_skip_dir(rel):
            continue
        rel_posix = rel.as_posix()
        if _matches_gitignore_pattern(rel_posix, gi_patterns):
            continue
        # Cheap line count: byte-level newline counter.
        try:
            with entry.open("rb") as fh:
                buf = fh.read()
        except OSError:
            continue
        total += buf.count(b"\n")
    return total


def _classify_size(loc: int) -> str:
    """Map LoC count to size_class per PLAN-097 §3 Wave C.1 boundaries.

    Left-closed right-open:
      SMALL  = [0, 50_000)
      MEDIUM = [50_000, 200_000)
      LARGE  = [200_000, ∞)
    """
    if loc < SMALL_LOC_MAX:
        return "SMALL"
    if loc < MEDIUM_LOC_MAX:
        return "MEDIUM"
    return "LARGE"


# ---------------------------------------------------------------------------
# Detection algorithm
# ---------------------------------------------------------------------------


def detect_profile(root: Path) -> Tuple[str, str, List[str]]:
    """Core detection: returns (risk_class, confidence, signals).

    Algorithm:
      1. Collect file + dir signals.
      2. Score each candidate profile.
      3. If `trading-readonly` signals present -> trading-readonly (most
         restrictive wins).
      4. Else if `fintech` signals present -> fintech.
      5. Else if `frontend` AND `engine` signals both present -> frontend
         (mixed-frontend-backend bias toward frontend per Codex fixture
         spec, with medium confidence; user can `confirm-profile engine`).
      6. Else single profile clear -> that profile.
      7. Else (no signals) -> unknown-needs-owner-confirmation.
      8. Ambiguous-but-some-signals -> trading-readonly (fail-CLOSED).

    Confidence:
      - high: >=3 distinct strong signals all agreeing on single profile.
      - medium: 1-2 strong signals OR mixed signals resolved by priority.
      - low: fail-CLOSED default or signals contradict.
    """
    signals: List[str] = []

    # File-content scans
    pkg_path = root / "package.json"
    pyproject_path = root / "pyproject.toml"
    req_path = root / "requirements.txt"
    cargo_path = root / "Cargo.toml"

    pkg_text = _read_text_safe(pkg_path)
    pyproject_text = _read_text_safe(pyproject_path)
    req_text = _read_text_safe(req_path)
    cargo_text = _read_text_safe(cargo_path)

    # Env files for trading API keys
    env_texts: List[str] = []
    for env_name in (".env", ".env.example", ".env.sample", ".env.local"):
        env_text = _read_text_safe(root / env_name)
        if env_text:
            env_texts.append(env_text)

    frontend_votes = 0
    engine_votes = 0
    fintech_votes = 0
    trading_votes = 0

    if pkg_text:
        if FRONTEND_DEP_REGEX.search(pkg_text):
            frontend_votes += 2
            signals.append("package.json:frontend-framework")
        if ENGINE_NODE_DEP_REGEX.search(pkg_text):
            engine_votes += 2
            signals.append("package.json:node-engine-framework")
        if FINTECH_DEP_REGEX.search(pkg_text):
            fintech_votes += 2
            signals.append("package.json:fintech-dep")

    if pyproject_text:
        if ENGINE_PY_DEP_REGEX.search(pyproject_text):
            engine_votes += 2
            signals.append("pyproject.toml:py-engine-framework")
        if COMPLIANCE_HINT_REGEX.search(pyproject_text):
            fintech_votes += 1
            signals.append("pyproject.toml:compliance-keyword")

    if req_text:
        if ENGINE_PY_DEP_REGEX.search(req_text):
            engine_votes += 2
            signals.append("requirements.txt:py-engine-framework")

    if cargo_text:
        # Cargo alone is ambiguous — could be trading bot OR generic engine.
        # Combined with trading dir hints, it's strong trading-readonly.
        signals.append("Cargo.toml:present")

    # Solidity contracts -> strong trading-readonly signal.
    sol_files = _has_file_pattern(root, "*.sol", max_results=3)
    if sol_files:
        trading_votes += 3
        signals.append(f"file:*.sol(x{len(sol_files)})")

    # Env file trading-key hint -> strong trading-readonly signal.
    for env_text in env_texts:
        if TRADING_KEY_REGEX.search(env_text):
            trading_votes += 3
            signals.append("env:exchange-api-key")
            break

    # Directory walk for trading + compliance + fintech hints.
    dir_names = _collect_dir_names(root)
    trading_dir_hits = _has_dir_hint(dir_names, TRADING_DIR_HINTS)
    compliance_dir_hits = _has_dir_hint(dir_names, COMPLIANCE_DIR_HINTS)
    fintech_dir_hits = _has_dir_hint(dir_names, FINTECH_DIR_HINTS)

    if trading_dir_hits:
        trading_votes += 2 * len(trading_dir_hits)
        signals.extend(trading_dir_hits)
    if compliance_dir_hits:
        fintech_votes += 2 * len(compliance_dir_hits)
        signals.extend(compliance_dir_hits)
    if fintech_dir_hits:
        fintech_votes += len(fintech_dir_hits)
        signals.extend(fintech_dir_hits)

    # Apps subdirs (Next.js / monorepo detection)
    has_apps = any(d == "apps" or d.startswith("apps" + os.sep) for d in dir_names)
    has_packages = any(d == "packages" or d.startswith("packages" + os.sep) for d in dir_names)
    if has_apps and has_packages:
        signals.append("dir:apps/+packages/")

    # ---------------------------------------------------------------
    # Priority resolution (per algorithm doc above)
    # ---------------------------------------------------------------

    total_signals = len(signals)

    # Trading wins always when any trading signal fires.
    if trading_votes > 0:
        confidence = "high" if trading_votes >= 5 else "medium"
        return ("trading-readonly", confidence, signals)

    # Fintech beats plain frontend/engine when fintech signals fire.
    if fintech_votes > 0:
        confidence = "high" if fintech_votes >= 4 else "medium"
        return ("fintech", confidence, signals)

    # Mixed-frontend-backend -> frontend at medium confidence (vibecoder
    # bias per Codex fixture spec). Owner can `confirm-profile engine`.
    if frontend_votes > 0 and engine_votes > 0:
        return ("frontend", "medium", signals + ["mixed:frontend+engine"])

    # Clear single signal.
    if frontend_votes > 0 and engine_votes == 0:
        confidence = "high" if frontend_votes >= 3 else "medium"
        return ("frontend", confidence, signals)
    if engine_votes > 0 and frontend_votes == 0:
        confidence = "high" if engine_votes >= 3 else "medium"
        return ("engine", confidence, signals)

    # No detectable signals at all -> unknown.
    if total_signals == 0:
        return (
            "unknown-needs-owner-confirmation",
            "low",
            signals + ["fallback:no-signals"],
        )

    # Some signals but none decisive (e.g. monorepo apps/+packages/ only
    # with no framework markers, or bare Cargo.toml without trading-readonly
    # signal) -> fail-CLOSED to trading-readonly.
    return (
        "trading-readonly",
        "low",
        signals + ["fallback:ambiguous-fail-closed"],
    )


# ---------------------------------------------------------------------------
# File-level I/O
# ---------------------------------------------------------------------------


def _now_utc_iso() -> str:
    """RFC 3339 / ISO 8601 timestamp in UTC ending in Z (no fractional)."""
    return _dt.datetime.now(tz=_dt.timezone.utc).replace(microsecond=0).isoformat().replace(
        "+00:00", "Z"
    )


def _repo_profile_path(target: Path) -> Path:
    return target / ".claude" / "repo-profile.yaml"


def load_existing_profile(target: Path) -> Optional[Dict[str, object]]:
    """Return existing profile dict, or None if file absent.

    Raises ValueError when file present but malformed (caller exits 4).
    """
    path = _repo_profile_path(target)
    if not path.is_file():
        return None
    text = _read_text_safe(path)
    if text is None:
        raise ValueError(f"cannot read {path}")
    return parse_yaml(text)


def _validate_against_schema(profile: Dict[str, object]) -> None:
    """Lightweight stdlib schema validation matching repo-profile.schema.json.

    We do NOT load the schema file at runtime (would need jsonschema dep);
    instead we hand-code the validation matching the schema 1:1. Tests
    cross-check against the on-disk schema for drift.
    """
    required = {"risk_class", "detected_at", "confidence", "signals", "manual_override", "created_at"}
    missing = required - set(profile.keys())
    if missing:
        raise ValueError(f"profile missing required keys: {sorted(missing)}")
    if profile["risk_class"] not in VALID_PROFILES:
        raise ValueError(f"invalid risk_class: {profile['risk_class']!r}")
    if profile["confidence"] not in ("high", "medium", "low"):
        raise ValueError(f"invalid confidence: {profile['confidence']!r}")
    if not isinstance(profile["signals"], list):
        raise ValueError("signals must be a list")
    for s in profile["signals"]:
        if not isinstance(s, str) or not s or len(s) > 200:
            raise ValueError(f"invalid signal entry: {s!r}")
        if not re.fullmatch(r"[a-zA-Z0-9._:/+-]+", s):
            raise ValueError(f"invalid signal slug chars: {s!r}")
    if not isinstance(profile["manual_override"], bool):
        raise ValueError("manual_override must be bool")
    for ts_key in ("detected_at", "created_at"):
        ts = profile[ts_key]
        if not isinstance(ts, str) or not re.fullmatch(
            r"\d{4}-\d{2}-\d{2}T\d{2}:\d{2}:\d{2}(?:\.\d+)?(?:Z|[+-]\d{2}:\d{2})", ts
        ):
            raise ValueError(f"{ts_key} must be RFC 3339 UTC string, got {ts!r}")
    if "manual_review_paths" in profile:
        if not isinstance(profile["manual_review_paths"], list):
            raise ValueError("manual_review_paths must be a list")
        for p in profile["manual_review_paths"]:
            if not isinstance(p, str) or not p or len(p) > 500:
                raise ValueError(f"invalid manual_review_paths entry: {p!r}")
    if "schema_version" in profile and profile["schema_version"] != SCHEMA_VERSION:
        raise ValueError(f"unsupported schema_version: {profile['schema_version']!r}")
    if "notes" in profile and not isinstance(profile["notes"], str):
        raise ValueError("notes must be a string")
    # PLAN-097 Wave C.1 — size_class + loc_count (both optional).
    if "size_class" in profile:
        if profile["size_class"] not in VALID_SIZE_CLASSES:
            raise ValueError(f"invalid size_class: {profile['size_class']!r}")
    if "loc_count" in profile:
        if not isinstance(profile["loc_count"], int) or profile["loc_count"] < 0:
            raise ValueError(f"loc_count must be non-negative integer, got {profile['loc_count']!r}")


def write_profile(target: Path, profile: Dict[str, object]) -> None:
    _validate_against_schema(profile)
    path = _repo_profile_path(target)
    path.parent.mkdir(parents=True, exist_ok=True)
    text = emit_yaml(profile)
    # Atomic-ish write: tmp + rename within same dir.
    tmp = path.with_suffix(path.suffix + ".tmp")
    with tmp.open("w", encoding="utf-8", newline="\n") as fh:
        fh.write(text)
    os.replace(tmp, path)


# ---------------------------------------------------------------------------
# CLI commands
# ---------------------------------------------------------------------------


def cmd_detect(target: Path, emit_json: bool) -> int:
    existing = load_existing_profile(target)
    risk_class, confidence, signals = detect_profile(target)
    # PLAN-097 Wave C.1 — size detection runs alongside risk-class detection.
    loc = _count_loc(target)
    size_class = _classify_size(loc)
    now = _now_utc_iso()

    if existing is not None and existing.get("manual_override") is True:
        # Owner has confirmed risk_class; do NOT overwrite. Report divergence.
        existing_class = existing.get("risk_class")
        diverged = existing_class != risk_class
        report = {
            "command": "detect",
            "result": "manual-override-respected",
            "manual_override_risk_class": existing_class,
            "would-have-detected": risk_class,
            "would-have-confidence": confidence,
            "size_class": size_class,
            "loc_count": loc,
            "signals": signals,
            "diverged": diverged,
        }
        if emit_json:
            print(json.dumps(report, sort_keys=True))
        else:
            print(f"detect: manual_override active (risk_class={existing_class})")
            print(f"  would-have-detected: {risk_class} ({confidence})")
            print(f"  size_class: {size_class} (loc={loc:,})")
            if diverged:
                print("  WARNING: detection diverges from manual override")
                print(f"  signals: {', '.join(signals)}")
        # Still emit rag_profile_recommended (size-class is independent).
        _emit_rag_profile_recommended(size_class, decision_for_size(size_class))
        return 0 if not diverged else 3

    profile = _build_profile_dict(
        risk_class=risk_class,
        confidence=confidence,
        signals=signals,
        manual_override=False,
        existing=existing,
        now=now,
        size_class=size_class,
        loc_count=loc,
    )

    # Add manual_review_paths default ONLY for trading-readonly.
    if risk_class == "trading-readonly":
        profile["manual_review_paths"] = list(DEFAULT_TRADING_MANUAL_REVIEW_PATHS)

    write_profile(target, profile)

    report = {
        "command": "detect",
        "risk_class": risk_class,
        "confidence": confidence,
        "size_class": size_class,
        "loc_count": loc,
        "signals": signals,
        "manual_override": False,
        "wrote": str(_repo_profile_path(target)),
    }
    if emit_json:
        print(json.dumps(report, sort_keys=True))
    else:
        print(f"detect: risk_class={risk_class} confidence={confidence}")
        print(f"  size_class: {size_class} (loc={loc:,})")
        print(f"  signals: {', '.join(signals) if signals else '(none)'}")
        print(f"  wrote: {_repo_profile_path(target)}")

    # PLAN-097 Wave C.5 — emit rag_profile_recommended audit event.
    _emit_rag_profile_recommended(size_class, decision_for_size(size_class))

    if risk_class == "unknown-needs-owner-confirmation":
        return 2
    if risk_class == "trading-readonly" and confidence == "low":
        # fail-CLOSED ambiguous default -> soft failure exit 1.
        return 1
    return 0


def decision_for_size(size_class: str) -> str:
    """Return the RAG routing decision implied by size_class alone.

    Note: actual routing decision at query time additionally checks
    kill-switches + sidecar health; this function gives the size-class
    contribution only (used in rag_profile_recommended audit emit).
    """
    if size_class == "LARGE":
        return "auto-wire"
    return "skip"


def _emit_rag_profile_recommended(size_class: str, decision: str) -> None:
    """Emit rag_profile_recommended audit event (PLAN-097 Wave C.5 / AC14).

    Fail-open per ADR-005 framework discipline; hasattr-guarded for pre-
    ceremony adopter compatibility per ADR-098.
    """
    try:
        repo_root = Path(__file__).resolve().parents[2]
        hooks_dir = repo_root / ".claude" / "hooks"
        if str(hooks_dir) not in sys.path:
            sys.path.insert(0, str(hooks_dir))
        from _lib import audit_emit  # type: ignore
        if hasattr(audit_emit, "emit_rag_profile_recommended"):
            audit_emit.emit_rag_profile_recommended(
                profile=size_class,
                decision=decision,
            )
        elif hasattr(audit_emit, "emit_generic"):
            audit_emit.emit_generic(
                "rag_profile_recommended",
                profile=size_class,
                decision=decision,
            )
    except Exception:
        pass  # fail-open per framework discipline


def cmd_confirm_profile(target: Path, name: str, notes: Optional[str]) -> int:
    if name not in VALID_PROFILES:
        sys.stderr.write(f"error: unknown profile name `{name}`\n")
        sys.stderr.write(f"  valid: {', '.join(VALID_PROFILES)}\n")
        return 3
    if name == "unknown-needs-owner-confirmation":
        sys.stderr.write(
            "error: cannot confirm `unknown-needs-owner-confirmation` (that is the no-signals sentinel)\n"
        )
        return 3

    existing = load_existing_profile(target)
    # Re-run detection to capture current signals (forensic record).
    auto_class, auto_confidence, auto_signals = detect_profile(target)
    now = _now_utc_iso()

    confidence = "high"  # explicit Owner ACK is always high confidence.
    signals = auto_signals + [f"manual:confirm-{name}"]

    profile = _build_profile_dict(
        risk_class=name,
        confidence=confidence,
        signals=signals,
        manual_override=True,
        existing=existing,
        now=now,
    )

    if name == "trading-readonly":
        # Preserve any existing manual_review_paths additions.
        existing_paths: List[str] = []
        if existing and isinstance(existing.get("manual_review_paths"), list):
            existing_paths = [p for p in existing["manual_review_paths"] if isinstance(p, str)]
        merged = list(DEFAULT_TRADING_MANUAL_REVIEW_PATHS) + [
            p for p in existing_paths if p not in DEFAULT_TRADING_MANUAL_REVIEW_PATHS
        ]
        profile["manual_review_paths"] = merged

    if notes:
        profile["notes"] = notes

    write_profile(target, profile)
    print(f"confirm-profile: risk_class={name} manual_override=true")
    print(f"  wrote: {_repo_profile_path(target)}")
    _emit_profile_confirmed(name, target)
    return 0


def _emit_profile_confirmed(name: str, target: Path) -> None:
    """Emit repo_profile_confirmed audit action (PLAN-086 Wave H.4).

    Fail-open: silently returns on any error. ``repo_profile_confirmed``
    is not yet in ``_KNOWN_ACTIONS`` at v1.19.0; ``emit_generic`` will
    breadcrumb + drop per ADR-098 hasattr-guard. Full registration
    deferred to closeout ceremony.
    """
    try:
        repo_root = Path(__file__).resolve().parents[2]
        hooks_dir = repo_root / ".claude" / "hooks"
        if str(hooks_dir) not in sys.path:
            sys.path.insert(0, str(hooks_dir))
        from _lib import audit_emit  # type: ignore
        if hasattr(audit_emit, "emit_generic"):
            audit_emit.emit_generic(
                "repo_profile_confirmed",
                risk_class=name,
                target=str(target),
            )
    except Exception:
        pass  # fail-open per framework discipline


def cmd_show(target: Path, emit_json: bool) -> int:
    existing = load_existing_profile(target)
    if existing is None:
        if emit_json:
            print(json.dumps({"command": "show", "result": "absent"}, sort_keys=True))
        else:
            print("show: no .claude/repo-profile.yaml present")
        return 2
    if emit_json:
        print(json.dumps({"command": "show", "profile": existing}, sort_keys=True, default=str))
    else:
        for k in _YAML_KEY_ORDER:
            if k in existing:
                print(f"{k}: {existing[k]}")
    return 0


def _build_profile_dict(
    risk_class: str,
    confidence: str,
    signals: List[str],
    manual_override: bool,
    existing: Optional[Dict[str, object]],
    now: str,
    size_class: Optional[str] = None,
    loc_count: Optional[int] = None,
) -> Dict[str, object]:
    """Construct a fresh profile dict, preserving `created_at` when present."""
    created_at: str
    if existing and isinstance(existing.get("created_at"), str):
        existing_created = existing["created_at"]
        if re.fullmatch(
            r"\d{4}-\d{2}-\d{2}T\d{2}:\d{2}:\d{2}(?:\.\d+)?(?:Z|[+-]\d{2}:\d{2})",
            existing_created,
        ):
            created_at = existing_created
        else:
            created_at = now
    else:
        created_at = now
    # De-duplicate signals while preserving order.
    seen = set()
    deduped: List[str] = []
    for s in signals:
        if s not in seen:
            seen.add(s)
            deduped.append(s)
    out: Dict[str, object] = {
        "schema_version": SCHEMA_VERSION,
        "risk_class": risk_class,
        "detected_at": now,
        "confidence": confidence,
        "manual_override": manual_override,
        "created_at": created_at,
        "signals": deduped,
    }
    if size_class is not None:
        out["size_class"] = size_class
    if loc_count is not None:
        out["loc_count"] = loc_count
    return out


# ---------------------------------------------------------------------------
# Argparse entry
# ---------------------------------------------------------------------------


def build_parser() -> argparse.ArgumentParser:
    parser = argparse.ArgumentParser(
        prog="detect-repo-profile.py",
        description=(
            "Fail-CLOSED repo profile detector (PLAN-083 Wave 0a sub-agent 0.6). "
            "Reads filesystem signals + writes `.claude/repo-profile.yaml`."
        ),
    )
    sub = parser.add_subparsers(dest="command", required=True)

    p_det = sub.add_parser("detect", help="run heuristics + write profile yaml")
    p_det.add_argument("--target", default=".", help="repo root path (default: cwd)")
    p_det.add_argument("--json", action="store_true", help="emit JSON report on stdout")

    p_conf = sub.add_parser(
        "confirm-profile",
        help="Owner ACK a specific profile (sets manual_override=true)",
    )
    p_conf.add_argument("name", help="profile name (frontend/engine/fintech/trading-readonly/generic)")
    p_conf.add_argument("--target", default=".", help="repo root path (default: cwd)")
    p_conf.add_argument("--notes", default=None, help="optional Owner annotation string")

    p_show = sub.add_parser("show", help="display current `.claude/repo-profile.yaml`")
    p_show.add_argument("--target", default=".", help="repo root path (default: cwd)")
    p_show.add_argument("--json", action="store_true", help="emit JSON on stdout")

    return parser


def main(argv: Optional[List[str]] = None) -> int:
    parser = build_parser()
    args = parser.parse_args(argv)

    try:
        target = _safe_resolve_target(args.target)
    except (FileNotFoundError, NotADirectoryError) as exc:
        sys.stderr.write(f"error: {exc}\n")
        return 3

    try:
        if args.command == "detect":
            return cmd_detect(target, emit_json=args.json)
        if args.command == "confirm-profile":
            return cmd_confirm_profile(target, name=args.name, notes=args.notes)
        if args.command == "show":
            return cmd_show(target, emit_json=args.json)
    except ValueError as exc:
        sys.stderr.write(f"error: {exc}\n")
        return 4
    except OSError as exc:
        sys.stderr.write(f"error: io: {exc}\n")
        return 4

    sys.stderr.write(f"error: unknown command {args.command!r}\n")
    return 3


if __name__ == "__main__":
    sys.exit(main())
