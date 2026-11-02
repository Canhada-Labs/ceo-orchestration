"""inventory context-budget declarations."""

from __future__ import annotations

import argparse
import json
import os
import re
import sys
from pathlib import Path
from typing import Any, Dict, List, Optional, Tuple

# Static note initialization only; bound functions use the facade value.
CHARS_PER_TOKEN = 4
REDACTED = "[REDACTED-INJECTION-PATTERN]"

__all__ = ('_scan_matched', 'fence_token', 'POINTER_OVERHEAD_TOKENS', 'DESIGNATED_PILOTS', 'HONESTY_NOTES', 'estimate_tokens', '_read_text', '_line_count', '_BLOCK_SCALAR_INDICATORS', '_key_indent', 'parse_frontmatter', '_file_entry', 'discover_mcp_servers', '_collect_files', '_flag_file', 'compute_savings', '_savings_entry', 'build_inventory')

def _scan_matched(s: str) -> Optional[bool]:
    """Run the injection scan. True=hit, False=clean, None=scanner down."""
    if _injection_patterns is None:
        return None
    try:
        scan_fn = getattr(_injection_patterns, "scan_harness_mimicry", None)
        if not callable(scan_fn):
            return None
        result = scan_fn(s)
        matched = getattr(result, "matched", None)
        if matched is None:
            matched = bool(result)
        return bool(matched)
    except Exception:  # noqa: BLE001
        return None


def fence_token(s: Any, *, max_len: int = 80) -> str:
    """Fence an identifier-like field (MCP server name) for display.

    Scanner first (hit => REDACTED), then a strictly-destructive charset
    allowlist — safe to use even when the scanner is unavailable.
    """
    if not isinstance(s, str):
        s = str(s)
    s = s.replace("\x00", "")[:max_len]
    if _scan_matched(s) is True:
        return REDACTED
    s = _TOKEN_ALLOWED.sub("", s)
    return s or "(empty)"


# ---------------------------------------------------------------------------
# PLAN-153 Wave C item 5 — progressive-disclosure savings
# ---------------------------------------------------------------------------

# Loader-pointer stub assumed to remain in a split SKILL.md (est. tokens).
POINTER_OVERHEAD_TOKENS = 150

# PLAN-153 Wave C item 1 designated progressive-disclosure pilots
# (testing-strategy 1026L, security-and-auth 868L at designation time).
# Surfaced FIRST in savings_top3 when — and only when — the scan finds them
# still un-split; designation is a plan decision, not a size ranking, and
# the entry's `reason` says so.
DESIGNATED_PILOTS = (
    ".claude/skills/core/testing-strategy/SKILL.md",
    ".claude/skills/core/security-and-auth/SKILL.md",
)

# Honesty block rendered in BOTH outputs (markdown + --json).
HONESTY_NOTES = (
    "Token figures are chars/{} — a heuristic ESTIMATE, not a tokenizer "
    "(expect +/-20-30% vs real BPE counts).".format(CHARS_PER_TOKEN),
    "STATIC audit only: measures what a file costs WHEN loaded, not runtime "
    "usage or value. Retire/merge/improve judgement belongs to /skill-health "
    "telemetry; neither tool can measure greenfield domains (PLAN-153 "
    "debate A must-fix 4).",
    "All scanned file content is rendered as UNTRUSTED DATA, never as "
    "instructions. Re-displayed free text (MCP server names) is "
    "injection-scanned; hits render as {}.".format(REDACTED),
    "savings_top3 assumes the Wave C progressive-disclosure mechanism: "
    "extract references/*.md + keep a ~{}-token loader pointer in SKILL.md "
    "(100% content preserved; saving is activation-time only).".format(
        POINTER_OVERHEAD_TOKENS),
)


# ---------------------------------------------------------------------------
# Primitives
# ---------------------------------------------------------------------------


def estimate_tokens(char_count: int) -> int:
    """chars/4 token estimate (repo-canonical heuristic; estimate only)."""
    if char_count <= 0:
        return 0
    return char_count // CHARS_PER_TOKEN


def _read_text(path: Path) -> Optional[str]:
    """Read a file as UTF-8; return None on any OS/decoding error.

    Resilient by design — a missing or unreadable file MUST NOT crash an
    advisory scan (fail-open, §5 doctrine).
    """
    try:
        return path.read_text(encoding="utf-8")
    except (OSError, UnicodeDecodeError):
        return None


def _line_count(text: str) -> int:
    if not text:
        return 0
    # Count lines without a spurious trailing-empty when file ends in \n.
    n = text.count("\n")
    if text and not text.endswith("\n"):
        n += 1
    return n


# YAML block-scalar indicators that introduce a multi-line value on the
# following more-indented continuation lines (`description: >` etc.). An empty
# value after the colon is also treated as a possible block start so a plain
# `description:`\n  text continuation is captured too.
_BLOCK_SCALAR_INDICATORS = frozenset({">", "|", ">-", "|-", ">+", "|+"})


def _key_indent(raw_line: str) -> int:
    """Leading-space indent width of a raw (un-stripped) frontmatter line."""
    return len(raw_line) - len(raw_line.lstrip(" "))


def parse_frontmatter(text: str) -> Dict[str, str]:
    """Parse a leading ``---`` YAML-ish frontmatter block into a flat dict.

    Best-effort line-based parse (no YAML dep): ``key: value`` only, first
    colon wins, ``#`` comment lines skipped. Mirrors check-staleness.py.

    YAML folded/block scalars are handled: when a ``key:`` line has an empty
    value OR a block indicator (``>``, ``|``, ``>-``, ``|-``, ``>+``, ``|+``),
    the subsequent MORE-INDENTED continuation lines are consumed and
    space-joined as the value. This is what lets ``bloated_description`` fire
    on the ~49 real SKILL.md files that write ``description: >`` with the body
    on following indented lines (otherwise the value reads as ``>``, len 1).
    """
    if not text:
        return {}
    m = _FRONTMATTER_RE.match(text)
    if not m:
        return {}
    result: Dict[str, str] = {}
    raw_lines = m.group(1).splitlines()
    i = 0
    n = len(raw_lines)
    while i < n:
        raw = raw_lines[i]
        s = raw.strip()
        if not s or s.startswith("#"):
            i += 1
            continue
        if ":" not in s:
            i += 1
            continue
        k, _, v = s.partition(":")
        key = k.strip()
        value = v.strip()
        key_indent = _key_indent(raw)
        i += 1
        if value == "" or value in _BLOCK_SCALAR_INDICATORS:
            # Consume the following MORE-INDENTED (non-blank, non-comment)
            # continuation lines as the block/folded scalar body.
            parts: List[str] = []
            while i < n:
                cont_raw = raw_lines[i]
                cont_stripped = cont_raw.strip()
                if cont_stripped == "":
                    # Blank line: part of a block scalar — keep scanning, but
                    # contributes no token to a space-joined value.
                    i += 1
                    continue
                if _key_indent(cont_raw) <= key_indent:
                    break  # dedent back to (or above) the key → block ended
                parts.append(cont_stripped)
                i += 1
            joined = " ".join(parts).strip()
            # If the scalar had an explicit indicator but no body, fall back to
            # the indicator text only if nothing was captured (len stays small).
            if joined:
                value = joined
        result[key] = value
    return result


def _file_entry(path: Path, repo: Path, category: str) -> Optional[Dict[str, Any]]:
    """Build a per-file inventory entry, or None if unreadable.

    Carries the line count, byte/char size, token estimate, and (when a
    frontmatter ``description:`` exists) its length for bloat-flagging.
    """
    text = _read_text(path)
    if text is None:
        return None
    chars = len(text)
    lines = _line_count(text)
    fm = parse_frontmatter(text)
    description = fm.get("description", "")
    try:
        rel = str(path.relative_to(repo))
    except ValueError:
        rel = str(path)
    # Progressive-disclosure state (Wave C): a skill self-retires from
    # savings_top3 only when its live SKILL.md actually POINTS at the
    # references/ dir. Dir existence alone is not enough: during a
    # parallel-shadow soak the references land beside a still-unsplit
    # live SKILL.md, and that skill must keep appearing in the report.
    has_references = (
        category in (CAT_SKILLS, CAT_CORE_SKILL)
        and (path.parent / "references").is_dir()
        and "references/" in text
    )
    return {
        "category": category,
        "path": rel,
        "lines": lines,
        "chars": chars,
        "est_tokens": estimate_tokens(chars),
        "description_chars": len(description),
        "has_references": has_references,
    }


# ---------------------------------------------------------------------------
# MCP discovery
# ---------------------------------------------------------------------------


def discover_mcp_servers(repo: Path) -> Tuple[List[str], List[str]]:
    """Best-effort discovery of the MCP subscription surface.

    Looks for an ``mcpServers`` object in (in order) ``.mcp.json``,
    ``.claude/.mcp.json``, ``.claude/settings.json``, and
    ``.claude/settings.local.json``. Returns ``(server_names, source_files)``.
    Read-only; tolerant of malformed JSON / missing files (advisory).
    """
    candidates = [
        repo / ".mcp.json",
        repo / ".claude" / ".mcp.json",
        repo / ".claude" / "settings.json",
        repo / ".claude" / "settings.local.json",
    ]
    names: List[str] = []
    sources: List[str] = []
    for cand in candidates:
        if not cand.is_file():
            continue
        text = _read_text(cand)
        if text is None:
            continue
        try:
            data = json.loads(text)
        except (json.JSONDecodeError, ValueError):
            continue
        if not isinstance(data, dict):
            continue
        servers = data.get("mcpServers")
        if isinstance(servers, dict) and servers:
            try:
                rel = str(cand.relative_to(repo))
            except ValueError:
                rel = str(cand)
            sources.append(rel)
            for key in servers.keys():
                # Untrusted-data fence: server names come from file content
                # and are re-displayed — scan + charset-allowlist first.
                fenced = fence_token(str(key))
                if fenced not in names:
                    names.append(fenced)
    return names, sources


# ---------------------------------------------------------------------------
# Inventory
# ---------------------------------------------------------------------------


def _collect_files(repo: Path) -> Dict[str, List[Dict[str, Any]]]:
    """Walk the Gate-1 + skill surface and build per-category file entries."""
    out: Dict[str, List[Dict[str, Any]]] = {
        CAT_CLAUDE_MD: [],
        CAT_PROTOCOL: [],
        CAT_TEAM: [],
        CAT_CORE_SKILL: [],
        CAT_AGENTS: [],
        CAT_SKILLS: [],
        CAT_COMMANDS: [],
    }

    def _add(category: str, path: Path) -> None:
        if path.is_file():
            entry = _file_entry(path, repo, category)
            if entry is not None:
                out[category].append(entry)

    _add(CAT_CLAUDE_MD, repo / "CLAUDE.md")
    _add(CAT_PROTOCOL, repo / "PROTOCOL.md")
    _add(CAT_TEAM, repo / ".claude" / "team.md")
    _add(CAT_TEAM, repo / ".claude" / "frontend-team.md")

    core_skill = repo / ".claude" / "skills" / "core" / "ceo-orchestration" / "SKILL.md"
    _add(CAT_CORE_SKILL, core_skill)

    agents_dir = repo / ".claude" / "agents"
    if agents_dir.is_dir():
        for p in sorted(agents_dir.glob("*.md")):
            _add(CAT_AGENTS, p)

    skills_dir = repo / ".claude" / "skills"
    if skills_dir.is_dir():
        for p in sorted(skills_dir.rglob("SKILL.md")):
            # The core ceo-orchestration SKILL.md is its own category — don't
            # double-count it under the generic skills bucket.
            if p.resolve() == core_skill.resolve():
                continue
            _add(CAT_SKILLS, p)

    commands_dir = repo / ".claude" / "commands"
    if commands_dir.is_dir():
        for p in sorted(commands_dir.glob("*.md")):
            _add(CAT_COMMANDS, p)

    return out


def _flag_file(entry: Dict[str, Any]) -> List[Dict[str, Any]]:
    """Return reduction-candidate flags for a single file entry.

    Heavy-file (line) flags use the per-category threshold; a bloated
    frontmatter ``description:`` is a separate flag.
    """
    flags: List[Dict[str, Any]] = []
    category = entry["category"]
    lines = entry["lines"]

    if category == CAT_AGENTS:
        threshold = THRESHOLD_AGENT_LINES
    elif category in (CAT_SKILLS, CAT_CORE_SKILL):
        threshold = THRESHOLD_SKILL_LINES
    elif category == CAT_COMMANDS:
        threshold = THRESHOLD_RULE_LINES
    else:
        threshold = None  # claude_md / protocol / team have no line threshold

    if threshold is not None and lines > threshold:
        flags.append({
            "kind": "heavy_file",
            "category": category,
            "path": entry["path"],
            "lines": lines,
            "threshold_lines": threshold,
            "est_tokens": entry["est_tokens"],
            "message": (
                "{cat} file is {lines} lines (> {thr}); consider splitting or "
                "trimming to reduce always-loaded context".format(
                    cat=category, lines=lines, thr=threshold,
                )
            ),
        })

    if entry["description_chars"] > THRESHOLD_DESCRIPTION_CHARS:
        flags.append({
            "kind": "bloated_description",
            "category": category,
            "path": entry["path"],
            "description_chars": entry["description_chars"],
            "threshold_chars": THRESHOLD_DESCRIPTION_CHARS,
            "est_tokens": entry["est_tokens"],
            "message": (
                "frontmatter description is {n} chars (> {thr}); trim to keep "
                "the skill/agent index lean".format(
                    n=entry["description_chars"], thr=THRESHOLD_DESCRIPTION_CHARS,
                )
            ),
        })

    return flags


def compute_savings(
    files_by_cat: Dict[str, List[Dict[str, Any]]],
    limit: int = 3,
) -> List[Dict[str, Any]]:
    """Top-N progressive-disclosure savings opportunities (Wave C item 5).

    Candidate = a SKILL.md entry (skills or core_skill category) with
    ``lines > THRESHOLD_SKILL_LINES`` and NO existing ``references/`` dir.
    PLAN-153-designated pilots rank first WHEN FOUND as candidates; remaining
    slots go to the largest candidates by estimated tokens (path tie-break).
    Every entry carries an honest ``reason`` naming which rule ranked it.
    """
    candidates = [
        e
        for cat in (CAT_SKILLS, CAT_CORE_SKILL)
        for e in files_by_cat.get(cat, [])
        if e["lines"] > THRESHOLD_SKILL_LINES and not e.get("has_references")
    ]
    by_path = {e["path"]: e for e in candidates}
    picked: List[Dict[str, Any]] = []
    picked_paths = set()

    for pilot in DESIGNATED_PILOTS:
        if len(picked) >= limit:
            break
        entry = by_path.get(pilot)
        if entry is None:
            continue
        picked.append(_savings_entry(
            entry,
            reason="PLAN-153 Wave C item 1 designated pilot (plan decision, "
                   "not size rank alone — larger files may exist below)",
        ))
        picked_paths.add(entry["path"])

    rest = sorted(
        (e for e in candidates if e["path"] not in picked_paths),
        key=lambda e: (-e["est_tokens"], e["path"]),
    )
    for entry in rest:
        if len(picked) >= limit:
            break
        picked.append(_savings_entry(
            entry, reason="largest un-split SKILL.md by estimated tokens"))
        picked_paths.add(entry["path"])

    for rank, item in enumerate(picked, start=1):
        item["rank"] = rank
    return picked


def _savings_entry(entry: Dict[str, Any], reason: str) -> Dict[str, Any]:
    """One savings_top3 row. Numbers are estimates (chars/4 heuristic)."""
    item = {
        "rank": 0,
        "path": entry["path"],
        "category": entry["category"],
        "lines": entry["lines"],
        "est_tokens": entry["est_tokens"],
        "est_saving_tokens": max(
            0, entry["est_tokens"] - POINTER_OVERHEAD_TOKENS),
        "reason": reason,
        "mechanism": (
            "extract references/*.md + loader pointer in SKILL.md "
            "(100% content preserved; saving = activation-time only)"
        ),
    }
    if entry["category"] == CAT_CORE_SKILL:
        item["caveat"] = (
            "always-on at Gate 2 — highest raw saving, but restructuring the "
            "core CEO skill needs its own ceremony/debate, not a Wave C pilot"
        )
    return item


def build_inventory(repo: Path, top: int = 10) -> Dict[str, Any]:
    """Produce the full context-budget report dict.

    Categories table + flat file list + flagged reduction candidates + a
    top-N ranking by estimated tokens (heaviest first).
    """
    files_by_cat = _collect_files(repo)
    mcp_names, mcp_sources = discover_mcp_servers(repo)

    categories: List[Dict[str, Any]] = []
    all_files: List[Dict[str, Any]] = []
    flags: List[Dict[str, Any]] = []
    grand_tokens = 0

    cat_order = [
        CAT_CLAUDE_MD, CAT_PROTOCOL, CAT_TEAM, CAT_CORE_SKILL,
        CAT_AGENTS, CAT_SKILLS, CAT_COMMANDS,
    ]
    for cat in cat_order:
        entries = files_by_cat.get(cat, [])
        cat_tokens = sum(e["est_tokens"] for e in entries)
        cat_lines = sum(e["lines"] for e in entries)
        grand_tokens += cat_tokens
        categories.append({
            "category": cat,
            "file_count": len(entries),
            "total_lines": cat_lines,
            "est_tokens": cat_tokens,
        })
        for e in entries:
            all_files.append(e)
            flags.extend(_flag_file(e))

    # MCP category — count-based, not file-token-based.
    mcp_over = len(mcp_names) > THRESHOLD_MCP_SERVERS
    categories.append({
        "category": CAT_MCP,
        "file_count": len(mcp_sources),
        "server_count": len(mcp_names),
        "servers": mcp_names,
        "sources": mcp_sources,
        "over_subscribed": mcp_over,
        "threshold_servers": THRESHOLD_MCP_SERVERS,
    })
    if mcp_over:
        flags.append({
            "kind": "mcp_over_subscription",
            "category": CAT_MCP,
            "server_count": len(mcp_names),
            "threshold_servers": THRESHOLD_MCP_SERVERS,
            "servers": mcp_names,
            "message": (
                "{n} MCP servers configured (> {thr}); each adds tool-schema "
                "context — unsubscribe unused ones".format(
                    n=len(mcp_names), thr=THRESHOLD_MCP_SERVERS,
                )
            ),
        })

    # Top-N reduction candidates: heaviest files by estimated tokens, desc.
    # Stable tie-break on path so ordering is deterministic across runs.
    ranked = sorted(
        all_files,
        key=lambda e: (-e["est_tokens"], e["path"]),
    )
    if top is not None and top >= 0:
        ranked = ranked[:top]

    return {
        "schema": "context-budget.v1",
        "repo_root": str(repo),
        "heuristic": "1 token ~= {} chars (ESTIMATE, not the Anthropic "
                     "tokenizer)".format(CHARS_PER_TOKEN),
        "grand_total_est_tokens": grand_tokens,
        "categories": categories,
        "top_candidates": ranked,
        # PLAN-153 Wave C item 5 (additive to v1): top-3 progressive-
        # disclosure savings + the honesty block. See module docstring.
        "savings_top3": compute_savings(files_by_cat),
        # PLAN-179 W3 US11 (additive to v1): declared orphan-probe status for
        # the D1/D2/D5 decision probes. Descriptive; gates nothing.
        "probe_status": probe_status(),
        "notes": list(HONESTY_NOTES) + [PROBE_STATUS_NOTE],
        "scanner_available": _injection_patterns is not None,
        "flags": flags,
        "flag_count": len(flags),
        "files": all_files,
    }


