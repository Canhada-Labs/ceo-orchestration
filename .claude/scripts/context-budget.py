#!/usr/bin/env python3
"""context-budget.py — static context-inventory audit (advisory, never blocks).

PLAN-124 WS-4. Stdlib-only, loopback / read-only — like
``check-staleness.py`` and our other advisory scanners. This tool inventories
the **always-loaded / Gate-1 + skill surface** that we re-pay every session
(CLAUDE.md §0 cache discipline, ~44,786-token gate-boot cost) and produces:

  * a per-category estimated-token table, and
  * a top-N ranked list of reduction candidates (heaviest files / bloated
    frontmatter / MCP over-subscription).

It harvests the **mechanism** from ECC's ``skills/context-budget/SKILL.md``
(token inventory + heavy-file flagging + top optimizations) re-implemented in
stdlib Python under our patterns. ECC is MIT; this is a re-implementation, not
a vendored copy.

## What is inventoried (categories)

| Category    | Surface                                                  |
|-------------|----------------------------------------------------------|
| claude_md   | ``CLAUDE.md``                                            |
| protocol    | ``PROTOCOL.md``                                          |
| team        | ``.claude/team.md`` + ``.claude/frontend-team.md``       |
| core_skill  | ``.claude/skills/core/ceo-orchestration/SKILL.md``       |
| agents      | ``.claude/agents/*.md``                                  |
| skills      | ``.claude/skills/**/SKILL.md``                           |
| commands    | ``.claude/commands/*.md``                                |
| mcp         | MCP subscription surface (``.mcp.json`` / settings)      |

## Heavy-file thresholds (from the ECC reference)

  * agents          > 200 lines
  * skills          > 400 lines
  * rules/commands  > 100 lines
  * frontmatter ``description:`` > 200 chars  (bloated description)
  * MCP servers     > 5 configured            (over-subscription)

## Token estimate

Reuses the repo's documented chars/4 heuristic (see
``profile-opus-4-7.py:estimate_gate_boot_token_cost`` — "1 token ≈ 4 chars").
This is an **estimate** for monotonic diff tracking, NOT the Anthropic
tokenizer. Every report labels it as such.

## Usage

    python3 .claude/scripts/context-budget.py
    python3 .claude/scripts/context-budget.py --json
    python3 .claude/scripts/context-budget.py --top 5
    python3 .claude/scripts/context-budget.py --repo-root <path>
    python3 .claude/scripts/context-budget.py --tool-loop-scan <audit-log.jsonl>
    python3 .claude/scripts/context-budget.py --compact-decision \
        --used-tokens 170000 --window-tokens 200000   # D1 auto-compaction probe
    python3 .claude/scripts/context-budget.py --summarize-decision \
        --output-sizes '[12000,800,30000,500]'        # D2 summarize-oldest probe
    python3 .claude/scripts/context-budget.py --middle-out-decision \
        --message-sizes '[50000,800,50000,500]' \
        --budget-tokens 60000                          # D5 middle-out ladder probe

Exit code: always 0 (advisory) — never blocks a session, never writes outside
stdout. Use ``--strict`` to exit 1 when any heavy-file / over-subscription
flag fires (for an opt-in advisory CI lint).

## PLAN-153 Wave C item 5 — /context-budget command surface

The ``/context-budget`` slash command (``.claude/commands/context-budget.md``)
fronts this CLI. Wave C additions on top of the PLAN-124 inventory:

  * ``savings_top3`` — top-3 progressive-disclosure savings opportunities.
    Candidate = a SKILL.md over the heavy-skill line threshold with NO
    ``references/`` dir yet (already-split skills self-retire from the list).
    The PLAN-153 Wave C item 1 **designated pilots**
    (``core/testing-strategy``, ``core/security-and-auth``) rank first WHEN
    the scan finds them still un-split — that ordering is a plan decision,
    not a pure size rank, and each entry says which rule ranked it.
  * ``notes`` — honesty block rendered in both outputs: chars/4 is an
    ESTIMATE (not a tokenizer); this is a STATIC audit (activation-time cost,
    not runtime usage — retire/merge/improve judgement is /skill-health's
    scope, and neither tool can measure greenfield domains; PLAN-153 debate A
    must-fix 4).
  * Untrusted-data fence (debate B unseen-2): scanned file content is DATA,
    never instructions. The only free text this report re-displays (MCP
    server names from config files) passes ``_lib/injection_patterns`` +
    a conservative charset allowlist; hits render as
    ``[REDACTED-INJECTION-PATTERN]``. Frontmatter descriptions are only
    MEASURED (length), never displayed.
  * ``--scheduled`` — any scheduled wrapper must pass it so
    ``CEO_SOTA_DISABLE`` is honored.

## Stdlib-only

Filesystem walks + ``json`` for MCP config + a regex frontmatter parse. No
deps; never reads outside the given repo-root; never mutates anything.
"""

from __future__ import annotations

import argparse
import json
import os
import re
import sys
from pathlib import Path
from typing import Any, Dict, List, Optional, Tuple

# ---------------------------------------------------------------------------
# Heuristic + thresholds
# ---------------------------------------------------------------------------

# Repo-canonical token estimate: 1 token ≈ 4 chars (English-Portuguese mix).
# Mirrors profile-opus-4-7.py. Estimate only; not the Anthropic tokenizer.
CHARS_PER_TOKEN = 4

# Heavy-file line thresholds (from the ECC context-budget reference).
THRESHOLD_AGENT_LINES = 200
THRESHOLD_SKILL_LINES = 400
THRESHOLD_RULE_LINES = 100  # commands / rules
# Bloated frontmatter `description:` length (chars).
THRESHOLD_DESCRIPTION_CHARS = 200
# MCP over-subscription: more than this many configured servers.
THRESHOLD_MCP_SERVERS = 5

# Category labels (stable keys for --json consumers).
CAT_CLAUDE_MD = "claude_md"
CAT_PROTOCOL = "protocol"
CAT_TEAM = "team"
CAT_CORE_SKILL = "core_skill"
CAT_AGENTS = "agents"
CAT_SKILLS = "skills"
CAT_COMMANDS = "commands"
CAT_MCP = "mcp"

_FRONTMATTER_RE = re.compile(r"^---\s*\n(.*?)\n---\s*\n", re.DOTALL)


# ---------------------------------------------------------------------------
# PLAN-153 Wave C — untrusted-data fence (debate B unseen-2)
# ---------------------------------------------------------------------------
#
# Everything this tool reads is repo file content — rendered as DATA, never
# as instructions. The only free-text field re-displayed verbatim-ish is the
# MCP server name (a key in a JSON config); it passes the harness-mimicry
# injection scan + a conservative charset allowlist before display (mirrors
# skill-health.py `fence_token`). Frontmatter descriptions are only MEASURED
# (length), never displayed, so they need no display fence.

_HOOKS_DIR = str(Path(__file__).resolve().parent.parent / "hooks")
if _HOOKS_DIR not in sys.path:
    sys.path.insert(0, _HOOKS_DIR)

try:
    from _lib import injection_patterns as _injection_patterns  # type: ignore
except Exception:  # pragma: no cover - exercised via monkeypatch in tests
    _injection_patterns = None  # type: ignore[assignment]

REDACTED = "[REDACTED-INJECTION-PATTERN]"

# Conservative charset for identifier-like fields (MCP server names). No
# whitespace / angle brackets / pipes survive, so no catalogued injection
# pattern can survive either; the scanner still runs first when available.
_TOKEN_ALLOWED = re.compile(r"[^A-Za-z0-9._:/@#+()-]")


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
        "notes": list(HONESTY_NOTES),
        "scanner_available": _injection_patterns is not None,
        "flags": flags,
        "flag_count": len(flags),
        "files": all_files,
    }


# ---------------------------------------------------------------------------
# PLAN-133 D1 — proactive auto-compaction policy (hysteresis state machine)
# ---------------------------------------------------------------------------
#
# Default-OFF behavioral change. The *decision* (this module) is non-canonical
# and lives here in `scripts/`; the actual `context_auto_compacted` /
# `context_auto_compact_suppressed` closed-enum audit emit is CANONICAL
# (`.claude/hooks/_lib/audit_emit.py`) and is staged for Owner-GPG under
# `.claude/plans/PLAN-133/staged/D1.proposal.md` — this file never edits it.
#
# Doctrine compliance:
#   * Default-OFF: the feature is INACTIVE unless `CEO_AUTO_COMPACT_THRESHOLD`
#     is set to a sane int in (0, 100]. With the env unset, `decide_compaction`
#     always returns a "disabled" decision (compact=False, suppressed=False).
#     The default constant below (80) is the value used WHEN enabled; it is NOT
#     a default-on flip.
#   * Measure-first: every decision carries the numeric reason + ratios so the
#     compaction-rate can be tabulated from logs before any default-on flip.
#   * Hysteresis (perf must-fix): trigger at a HIGH-water mark, re-arm only
#     after dropping below a LOW-water mark, plus a minimum-turns cooldown and
#     a minimum-bytes-reclaimed floor. When the floor (or a still-disarmed
#     re-arm gate, or cooldown) blocks a would-be compaction, the decision is
#     `suppressed=True` so the caller emits `context_auto_compact_suppressed`.
#   * Fail-open-on-infra: any malformed input / read error yields a "disabled"
#     decision (never raises), so a buggy snapshot never blocks a session.
#
# This is a pure, side-effect-free decision function: it does NOT compact, does
# NOT emit, and does NOT write anything. The host wires the side effects.

# Env flags (default-OFF). `CEO_AUTO_COMPACT_THRESHOLD` is the high-water % of
# the model context window at which compaction is proposed. Unset/invalid ⇒ OFF.
ENV_AUTO_COMPACT_THRESHOLD = "CEO_AUTO_COMPACT_THRESHOLD"
ENV_AUTO_COMPACT_LOW_WATER = "CEO_AUTO_COMPACT_LOW_WATER"
ENV_AUTO_COMPACT_COOLDOWN_TURNS = "CEO_AUTO_COMPACT_COOLDOWN_TURNS"
ENV_AUTO_COMPACT_MIN_RECLAIM_PCT = "CEO_AUTO_COMPACT_MIN_RECLAIM_PCT"

# Defaults used ONLY when the feature is enabled (threshold env present + valid).
DEFAULT_AUTO_COMPACT_THRESHOLD_PCT = 80   # high-water trigger (% of window)
DEFAULT_AUTO_COMPACT_LOW_WATER_PCT = 60   # re-arm only after dropping below this
DEFAULT_AUTO_COMPACT_COOLDOWN_TURNS = 5   # min turns between compactions
DEFAULT_AUTO_COMPACT_MIN_RECLAIM_PCT = 10  # skip if < this % of bytes would be freed

# Decision reason codes (stable strings for log tabulation; closed set).
REASON_DISABLED = "disabled"                  # feature OFF (env unset/invalid)
REASON_BELOW_HIGH_WATER = "below_high_water"   # usage under trigger
REASON_NOT_REARMED = "not_rearmed"             # above low-water since last compaction
REASON_COOLDOWN = "cooldown"                   # min-turns cooldown not elapsed
REASON_RECLAIM_FLOOR = "reclaim_floor"         # < min-bytes-reclaimed freed → skip
REASON_COMPACT = "compact"                     # all gates pass → compact now


def _env_int(name: str, env: Optional[Dict[str, str]]) -> Optional[int]:
    """Read an int from `env` (or os.environ) — None on absent/malformed.

    Fail-open: never raises. A non-integer, empty, or whitespace value reads as
    None (treated by callers as "not configured").
    """
    src = env if env is not None else os.environ
    raw = src.get(name)
    if raw is None:
        return None
    try:
        return int(str(raw).strip())
    except (TypeError, ValueError):
        return None


class CompactionPolicy:
    """Hysteresis config + re-arm state for the auto-compaction decision.

    Stateless across processes by design — the host owns persistence. The host
    passes the prior `armed` flag and `turns_since_last_compaction` from its own
    session state; this object only derives the next decision + next state.

    `armed` means "eligible to trigger again": it is set False right after a
    compaction and re-set True once usage has dropped below the low-water mark.
    """

    def __init__(
        self,
        high_water_pct: int,
        low_water_pct: int,
        cooldown_turns: int,
        min_reclaim_pct: int,
    ) -> None:
        # Clamp to a sane, monotone config (fail-open: never raise on bad nums).
        self.high_water_pct = _clamp_pct(high_water_pct, DEFAULT_AUTO_COMPACT_THRESHOLD_PCT)
        low = _clamp_pct(low_water_pct, DEFAULT_AUTO_COMPACT_LOW_WATER_PCT)
        # Low-water MUST sit strictly below high-water for hysteresis to exist;
        # if a caller inverts them, pin low to high-1 (degenerate but safe).
        if low >= self.high_water_pct:
            low = max(0, self.high_water_pct - 1)
        self.low_water_pct = low
        self.cooldown_turns = cooldown_turns if cooldown_turns is not None and cooldown_turns >= 0 else DEFAULT_AUTO_COMPACT_COOLDOWN_TURNS
        self.min_reclaim_pct = _clamp_pct(min_reclaim_pct, DEFAULT_AUTO_COMPACT_MIN_RECLAIM_PCT)


def _clamp_pct(value: Any, fallback: int) -> int:
    """Coerce `value` to an int in [0, 100]; `fallback` on any malformed input."""
    try:
        n = int(value)
    except (TypeError, ValueError):
        return fallback
    if n < 0:
        return 0
    if n > 100:
        return 100
    return n


def load_policy_from_env(env: Optional[Dict[str, str]] = None) -> Optional[CompactionPolicy]:
    """Build a CompactionPolicy from env, or None when the feature is OFF.

    The feature is OFF (returns None) unless `CEO_AUTO_COMPACT_THRESHOLD` is set
    to an int in (0, 100]. All other knobs fall back to their documented
    defaults when unset/invalid. Fail-open: never raises.
    """
    threshold = _env_int(ENV_AUTO_COMPACT_THRESHOLD, env)
    if threshold is None or threshold <= 0 or threshold > 100:
        return None  # default-OFF
    return CompactionPolicy(
        high_water_pct=threshold,
        low_water_pct=(
            _env_int(ENV_AUTO_COMPACT_LOW_WATER, env)
            if _env_int(ENV_AUTO_COMPACT_LOW_WATER, env) is not None
            else DEFAULT_AUTO_COMPACT_LOW_WATER_PCT
        ),
        cooldown_turns=(
            _env_int(ENV_AUTO_COMPACT_COOLDOWN_TURNS, env)
            if _env_int(ENV_AUTO_COMPACT_COOLDOWN_TURNS, env) is not None
            else DEFAULT_AUTO_COMPACT_COOLDOWN_TURNS
        ),
        min_reclaim_pct=(
            _env_int(ENV_AUTO_COMPACT_MIN_RECLAIM_PCT, env)
            if _env_int(ENV_AUTO_COMPACT_MIN_RECLAIM_PCT, env) is not None
            else DEFAULT_AUTO_COMPACT_MIN_RECLAIM_PCT
        ),
    )


def _safe_ratio_pct(numerator: Any, denominator: Any) -> Optional[float]:
    """numerator/denominator as a percent (0..100), or None if not derivable."""
    try:
        num = float(numerator)
        den = float(denominator)
    except (TypeError, ValueError):
        return None
    if den <= 0:
        return None
    pct = (num / den) * 100.0
    if pct < 0:
        return 0.0
    return pct


def decide_compaction(
    used_tokens: Any,
    window_tokens: Any,
    *,
    reclaimable_tokens: Any = None,
    armed: bool = True,
    turns_since_last_compaction: Any = None,
    policy: Optional[CompactionPolicy] = None,
    env: Optional[Dict[str, str]] = None,
) -> Dict[str, Any]:
    """Decide whether to auto-compact NOW. Pure + side-effect-free + fail-open.

    Parameters
    ----------
    used_tokens, window_tokens
        Current context usage and the model window size (tokens). The usage
        ratio drives the high/low-water hysteresis.
    reclaimable_tokens
        Estimated tokens a compaction would free. Drives the minimum-reclaim
        floor. When None, the floor is treated as PASSED (host could not
        estimate — do not block on a missing estimate; fail-open).
    armed
        Host-supplied re-arm flag (False right after a prior compaction until
        usage has dropped below the low-water mark).
    turns_since_last_compaction
        Host-supplied turn counter for the cooldown gate. None ⇒ cooldown
        treated as elapsed (no prior compaction this session).
    policy
        Explicit policy; when None, derived from `env` (default-OFF if the
        threshold env is unset/invalid).

    Returns a decision dict (never raises):
      {
        "compact": bool,            # caller should compact now
        "suppressed": bool,         # a would-be compaction was skipped by a gate
        "reason": <REASON_*>,       # stable reason code
        "enabled": bool,            # feature active
        "usage_pct": float|None,    # used/window * 100
        "reclaim_pct": float|None,  # reclaimable/used * 100 (estimate)
        "next_armed": bool,         # re-arm state the host should persist
        "high_water_pct": int|None,
        "low_water_pct": int|None,
        "cooldown_turns": int|None,
        "min_reclaim_pct": int|None,
      }

    NOTE — no payload echo: this dict carries ONLY numeric ratios + closed
    reason codes. It never includes any transcript text, command bytes, env
    values, or file paths. The canonical emit (staged proposal) scrubs to the
    same closed-field allowlist.
    """
    base = {
        "compact": False,
        "suppressed": False,
        "reason": REASON_DISABLED,
        "enabled": False,
        "usage_pct": None,
        "reclaim_pct": None,
        "next_armed": bool(armed),
        "high_water_pct": None,
        "low_water_pct": None,
        "cooldown_turns": None,
        "min_reclaim_pct": None,
    }

    if policy is None:
        policy = load_policy_from_env(env)
    if policy is None:
        return base  # default-OFF — disabled decision

    base["enabled"] = True
    base["high_water_pct"] = policy.high_water_pct
    base["low_water_pct"] = policy.low_water_pct
    base["cooldown_turns"] = policy.cooldown_turns
    base["min_reclaim_pct"] = policy.min_reclaim_pct

    usage_pct = _safe_ratio_pct(used_tokens, window_tokens)
    base["usage_pct"] = usage_pct
    if usage_pct is None:
        # Cannot derive usage (bad/zero window) → fail-open: do nothing.
        base["reason"] = REASON_BELOW_HIGH_WATER
        return base

    # Hysteresis re-arm: once usage drops below low-water, become eligible again.
    next_armed = bool(armed)
    if usage_pct < policy.low_water_pct:
        next_armed = True
    base["next_armed"] = next_armed

    # Below the high-water trigger: nothing to do (and we've already updated the
    # re-arm flag above for the drop-below-low case).
    if usage_pct < policy.high_water_pct:
        base["reason"] = REASON_BELOW_HIGH_WATER
        return base

    # At/above high-water but NOT re-armed (we are still riding the band above
    # low-water since the last compaction) → hold (not a suppression event; we
    # simply have not earned a fresh trigger).
    if not next_armed:
        base["reason"] = REASON_NOT_REARMED
        return base

    # Cooldown gate: a would-be compaction blocked by min-turns IS a suppression.
    turns = turns_since_last_compaction
    if turns is not None:
        try:
            turns_int = int(turns)
        except (TypeError, ValueError):
            turns_int = None
        if turns_int is not None and turns_int < policy.cooldown_turns:
            base["reason"] = REASON_COOLDOWN
            base["suppressed"] = True
            return base

    # Minimum-reclaim floor: skip a compaction that would free too little.
    reclaim_pct = _safe_ratio_pct(reclaimable_tokens, used_tokens)
    base["reclaim_pct"] = reclaim_pct
    if reclaim_pct is not None and reclaim_pct < policy.min_reclaim_pct:
        base["reason"] = REASON_RECLAIM_FLOOR
        base["suppressed"] = True
        return base

    # All gates pass → compact now; consume the re-arm (host disarms until the
    # next drop below low-water).
    base["compact"] = True
    base["reason"] = REASON_COMPACT
    base["next_armed"] = False
    return base


# ---------------------------------------------------------------------------
# PLAN-133 D2 (Wave D) — cheap-tier summarization of oldest verbose subagent
# outputs (protect last N)
# ---------------------------------------------------------------------------
#
# Default-OFF behavioral change. The *decision* (this module) is non-canonical
# and lives here in `scripts/`; the actual `subagent_output_summarized` /
# `subagent_output_summarize_skipped` closed-enum audit emit is CANONICAL
# (`.claude/hooks/_lib/audit_emit.py`) and is staged for Owner-GPG under
# `.claude/plans/PLAN-133/staged/D2.proposal.md` — this file never edits it.
#
# The IDEA (re-implemented from scratch, stdlib-only, NOT vendored): when the
# context window fills, the OLDEST + most-VERBOSE subagent tool-outputs are the
# best candidates to compress — they are the least likely to be needed verbatim
# again, and they carry the most tokens. We route those oldest verbose outputs
# to a CHEAP model tier for a short digest, while PROTECTING the last N outputs
# (the recent working set the orchestrator is actively reasoning over) so a
# just-produced result is never silently summarized out from under the loop.
#
# Doctrine compliance (§3):
#   * Default-OFF: INACTIVE unless `CEO_SUMMARIZE_OLDEST` is set to a truthy
#     int budget (the max number of outputs to summarize in one pass, > 0).
#     Unset/invalid ⇒ `decide_summarization` returns a "disabled" plan
#     (selected=[], enabled=False). The DEFAULT constants below are the values
#     used WHEN enabled; they are NOT a default-on flip.
#   * Measure-first: the plan carries the selected count + reclaimable-token
#     estimate + a closed reason so the summarization-rate (and the tokens it
#     would reclaim) can be tabulated from logs before any default-on flip.
#     Named promotion-measure: count(`subagent_output_summarized`) and the
#     summed `reclaim_tokens` per week at /ceo-boot.
#   * protect-last-N (the named AC): the `protect_last` most-recent outputs are
#     NEVER eligible, regardless of size, so the active working set is safe.
#   * verbosity floor: only outputs whose estimated size is >= a minimum-token
#     floor are eligible (summarizing a tiny output costs a cheap-tier call to
#     save nothing — `subagent_output_summarize_skipped` reason=below_floor).
#   * budget cap: at most `max_summaries` oldest-first eligible outputs are
#     selected in one pass (the rest are deferred, not lost).
#   * Fail-open-on-infra: any malformed input / read error yields a "disabled"
#     plan (never raises), so a buggy snapshot never blocks a session and a
#     recent output is never accidentally selected.
#   * No payload echo: the plan carries ONLY integer indices + token-size
#     buckets + closed reason codes. It NEVER includes any subagent output
#     text, agent name, file path, or command bytes. The canonical emit (staged
#     proposal) scrubs to the same closed-field allowlist.
#
# This is a pure, side-effect-free decision function: it does NOT summarize,
# does NOT call any model, does NOT emit, and does NOT write anything. The host
# wires the cheap-tier digest call + the audit emit + the context rewrite.

# Env flags (default-OFF). `CEO_SUMMARIZE_OLDEST` is the per-pass budget (max
# number of oldest verbose outputs to summarize). Unset/invalid/<=0 ⇒ OFF.
ENV_SUMMARIZE_OLDEST = "CEO_SUMMARIZE_OLDEST"
ENV_SUMMARIZE_PROTECT_LAST = "CEO_SUMMARIZE_PROTECT_LAST"
ENV_SUMMARIZE_MIN_TOKENS = "CEO_SUMMARIZE_MIN_TOKENS"

# Defaults used ONLY when the feature is enabled (the budget env is present and
# a valid positive int).
DEFAULT_SUMMARIZE_PROTECT_LAST = 3       # never summarize the last N outputs
DEFAULT_SUMMARIZE_MIN_TOKENS = 2000      # verbosity floor: skip small outputs
DEFAULT_SUMMARIZE_MAX_PER_PASS = 5       # cap per pass when budget is degenerate

# Summarization-plan reason codes (stable strings for log tabulation; closed
# set, mirrored by the canonical `_SUBAGENT_SUMMARIZE_REASON_ENUM`).
SUMM_REASON_DISABLED = "disabled"          # feature OFF (env unset/invalid)
SUMM_REASON_NO_CANDIDATES = "no_candidates"  # nothing past protect-N over floor
SUMM_REASON_SELECTED = "selected"          # >=1 output selected to summarize

# Per-output skip reason codes (why an individual output was NOT selected).
SUMM_SKIP_PROTECTED = "protected"          # within the last-N working set
SUMM_SKIP_BELOW_FLOOR = "below_floor"      # under the verbosity (min-tokens) floor
SUMM_SKIP_OVER_BUDGET = "over_budget"      # eligible but past the per-pass cap


class SummarizationPolicy:
    """Config for the oldest-verbose-output summarization decision.

    Stateless by design — the host owns the list of current subagent outputs
    and applies the resulting plan. This object only holds the three knobs.
    """

    def __init__(
        self,
        max_summaries: int,
        protect_last: int,
        min_tokens: int,
    ) -> None:
        # Clamp to sane, fail-open values (never raise on a bad number).
        self.max_summaries = _clamp_nonneg_int(
            max_summaries, DEFAULT_SUMMARIZE_MAX_PER_PASS)
        self.protect_last = _clamp_nonneg_int(
            protect_last, DEFAULT_SUMMARIZE_PROTECT_LAST)
        self.min_tokens = _clamp_nonneg_int(
            min_tokens, DEFAULT_SUMMARIZE_MIN_TOKENS)


def _clamp_nonneg_int(value: Any, fallback: int) -> int:
    """Coerce `value` to an int >= 0; `fallback` on any malformed input."""
    try:
        n = int(value)
    except (TypeError, ValueError):
        return fallback
    return 0 if n < 0 else n


def load_summarization_policy_from_env(
    env: Optional[Dict[str, str]] = None,
) -> Optional[SummarizationPolicy]:
    """Build a SummarizationPolicy from env, or None when the feature is OFF.

    OFF (returns None) unless `CEO_SUMMARIZE_OLDEST` is set to a positive int
    (the per-pass budget). Other knobs fall back to documented defaults when
    unset/invalid. Fail-open: never raises.
    """
    budget = _env_int(ENV_SUMMARIZE_OLDEST, env)
    if budget is None or budget <= 0:
        return None  # default-OFF
    protect = _env_int(ENV_SUMMARIZE_PROTECT_LAST, env)
    min_tokens = _env_int(ENV_SUMMARIZE_MIN_TOKENS, env)
    return SummarizationPolicy(
        max_summaries=budget,
        protect_last=protect if protect is not None else DEFAULT_SUMMARIZE_PROTECT_LAST,
        min_tokens=min_tokens if min_tokens is not None else DEFAULT_SUMMARIZE_MIN_TOKENS,
    )


def _output_token_size(record: Any) -> Optional[int]:
    """Best-effort estimated token size of one subagent-output record.

    Accepts either a mapping with an ``est_tokens`` (preferred) or ``tokens``
    or ``chars`` field, or a bare int (already a token count). Returns None when
    no size can be derived (the record is then treated as below-floor and never
    selected — fail-open: a record we cannot size is never summarized).
    """
    if isinstance(record, bool):
        # bool is an int subclass — reject it as a meaningless size.
        return None
    if isinstance(record, int):
        return record if record >= 0 else None
    if isinstance(record, dict):
        for key in ("est_tokens", "tokens"):
            if key in record:
                try:
                    n = int(record[key])
                except (TypeError, ValueError):
                    return None
                return n if n >= 0 else None
        if "chars" in record:
            try:
                c = int(record["chars"])
            except (TypeError, ValueError):
                return None
            return estimate_tokens(c) if c >= 0 else None
    return None


def decide_summarization(
    outputs: Any,
    *,
    policy: Optional[SummarizationPolicy] = None,
    env: Optional[Dict[str, str]] = None,
) -> Dict[str, Any]:
    """Decide which oldest verbose subagent outputs to digest on the cheap tier.

    Pure + side-effect-free + fail-open. PROTECTS the last N outputs.

    Parameters
    ----------
    outputs
        An ordered sequence of subagent-output records, OLDEST FIRST (index 0
        is the oldest, index ``len-1`` the most recent). Each record may be a
        mapping carrying an estimated size (``est_tokens`` / ``tokens`` /
        ``chars``) or a bare int token count. The order is the ONLY thing that
        determines age; the host supplies it.
    policy
        Explicit policy; when None, derived from `env` (default-OFF if the
        budget env is unset/invalid).

    Returns a plan dict (never raises):
      {
        "enabled": bool,            # feature active
        "reason": <SUMM_REASON_*>,  # stable plan-level reason code
        "selected": [int, ...],     # indices to summarize (oldest first)
        "selected_count": int,
        "reclaim_tokens": int,      # est tokens the selected digests would free
        "candidate_count": int,     # eligible-before-budget count
        "total_count": int,         # len(outputs)
        "protect_last": int|None,
        "min_tokens": int|None,
        "max_summaries": int|None,
        "skipped": [                # per-index skip provenance (closed reasons)
          {"index": int, "reason": <SUMM_SKIP_*>}, ...
        ],
      }

    NO payload echo: the plan carries ONLY integer indices + token-size buckets
    + closed reason codes. It NEVER includes any output text, agent name, file
    path, or command bytes. The canonical emit (staged proposal) scrubs to the
    same closed-field allowlist.
    """
    plan: Dict[str, Any] = {
        "enabled": False,
        "reason": SUMM_REASON_DISABLED,
        "selected": [],
        "selected_count": 0,
        "reclaim_tokens": 0,
        "candidate_count": 0,
        "total_count": 0,
        "protect_last": None,
        "min_tokens": None,
        "max_summaries": None,
        "skipped": [],
    }

    if policy is None:
        policy = load_summarization_policy_from_env(env)
    if policy is None:
        return plan  # default-OFF — disabled plan

    plan["enabled"] = True
    plan["protect_last"] = policy.protect_last
    plan["min_tokens"] = policy.min_tokens
    plan["max_summaries"] = policy.max_summaries

    # Normalize the outputs list (fail-open: a non-sequence ⇒ empty).
    try:
        items = list(outputs)
    except TypeError:
        items = []
    total = len(items)
    plan["total_count"] = total
    if total == 0:
        plan["reason"] = SUMM_REASON_NO_CANDIDATES
        return plan

    # The protected window is the last `protect_last` indices (the recent
    # working set). Everything strictly before it is age-eligible.
    protect_last = policy.protect_last
    protect_from = max(0, total - protect_last) if protect_last > 0 else total
    # `protect_from` is the first PROTECTED index; indices [0, protect_from) are
    # age-eligible candidates (oldest first).

    candidates: List[Tuple[int, int]] = []  # (index, est_tokens) oldest first
    for idx in range(total):
        if idx >= protect_from:
            # Within the protected last-N working set — never eligible.
            plan["skipped"].append(
                {"index": idx, "reason": SUMM_SKIP_PROTECTED})
            continue
        size = _output_token_size(items[idx])
        if size is None or size < policy.min_tokens:
            # Under the verbosity floor (or unsizeable) — not worth a cheap call.
            plan["skipped"].append(
                {"index": idx, "reason": SUMM_SKIP_BELOW_FLOOR})
            continue
        candidates.append((idx, size))

    plan["candidate_count"] = len(candidates)
    if not candidates:
        plan["reason"] = SUMM_REASON_NO_CANDIDATES
        return plan

    # Select the OLDEST-first candidates up to the per-pass budget. Candidates
    # are already in ascending-index (oldest-first) order; honoring that keeps
    # the selection deterministic and biased to the oldest outputs (the AC).
    budget = policy.max_summaries
    selected: List[int] = []
    reclaim = 0
    for pos, (idx, size) in enumerate(candidates):
        if budget > 0 and len(selected) >= budget:
            # Eligible but past the per-pass cap — deferred, not lost.
            plan["skipped"].append(
                {"index": idx, "reason": SUMM_SKIP_OVER_BUDGET})
            continue
        selected.append(idx)
        reclaim += size

    plan["selected"] = selected
    plan["selected_count"] = len(selected)
    plan["reclaim_tokens"] = reclaim
    plan["reason"] = SUMM_REASON_SELECTED if selected else SUMM_REASON_NO_CANDIDATES
    # Keep the skip provenance deterministically ordered by index.
    plan["skipped"].sort(key=lambda s: s["index"])
    return plan


# ---------------------------------------------------------------------------
# PLAN-133 D5 (Wave D) — middle-out degradation ladder on the context-overflow
# path (drop growing fractions of tool-response messages, middle-out, before
# failing)
# ---------------------------------------------------------------------------
#
# Default-OFF behavioral change. The *decision + transform* (this module) is
# non-canonical and lives here in `scripts/`; the actual
# `context_middle_out_degraded` / `context_middle_out_degrade_failed`
# closed-enum audit emit is CANONICAL (`.claude/hooks/_lib/audit_emit.py`) and is
# staged for Owner-GPG under `.claude/plans/PLAN-133/staged/D5.proposal.md` —
# this file never edits it.
#
# The IDEA (re-implemented from scratch, stdlib-only, NOT vendored): when the
# assembled context would OVERFLOW the model window, do NOT hard-fail. Instead,
# walk a **degradation ladder** — a sequence of growing fractions (e.g. 25% →
# 50% → 75% → 90%) — and at each RUNG drop that fraction from the MIDDLE of the
# largest tool-response messages, preserving a HEAD and a TAIL slice of each
# (the head carries the request/the first lines of output; the tail carries the
# conclusion/error/exit status — the two highest-signal regions). Keep climbing
# rungs (degrading more, on more messages) only while still over budget; stop
# the instant the projection fits (success) or the ladder is exhausted (the
# caller then decides to summarize/compact/fail — D1/D2 are the upstream knobs).
#
# Why MIDDLE-out and not head/tail truncation: a tool response's first lines
# (the command echoed + the start of stdout) and its last lines (the tail of
# stdout + the exit/error) are what the orchestrator actually reasons over; the
# bulk in the middle (repetitive log lines, large dumps) is the cheapest to drop
# with the least loss of meaning. This is the same rationale as a unified-diff
# context window: keep the edges, elide the center.
#
# Doctrine compliance (§3):
#   * Default-OFF: INACTIVE unless `CEO_MIDDLE_OUT_DEGRADE` is set to a truthy
#     int in (0, 100] — the per-message head+tail-preserved floor PERCENT (the
#     minimum fraction of each degraded message that MUST be kept; e.g. 40 ⇒ at
#     most 60% of any message is ever dropped). Unset/invalid ⇒
#     `decide_middle_out_degradation` returns a "disabled" plan (degraded=[],
#     enabled=False) and `apply_middle_out_degradation` returns the messages
#     UNCHANGED. The DEFAULT constants below are the values used WHEN enabled;
#     they are NOT a default-on flip.
#   * Measure-first: the plan carries the rung reached + reclaimed-token
#     estimate + a closed reason so the degradation-rate (and how often it
#     SAVED an overflow vs FAILED) can be tabulated from logs before any
#     default-on flip. Named promotion-measure: count(`context_middle_out_degraded`)
#     vs count(`context_middle_out_degrade_failed`) per week at /ceo-boot.
#   * protect-last-N + pinned: the `protect_last` most-recent messages and any
#     message marked `pinned`/`agent_visible`-True are NEVER degraded, so the
#     active working set and explicitly-pinned context are safe.
#   * growing-fraction ladder (the named AC): rungs are applied in ascending
#     aggressiveness; a rung is only entered if the prior projection still
#     overflows — never drop more than the overflow requires.
#   * head/tail floor: a degraded message ALWAYS keeps at least `min_keep_pct`
#     of its content (split head/tail), so a message is never reduced to a
#     meaningless stub. The floor is the env value.
#   * Fail-open-on-infra: any malformed input / read error yields a "disabled"
#     plan (never raises) and the apply function returns the input untouched, so
#     a buggy snapshot never blocks a session and a message is never corrupted.
#   * No payload echo: the plan carries ONLY integer indices + token-size
#     buckets + a rung integer + closed reason codes. It NEVER includes any
#     message text, tool name, agent name, file path, or command bytes. The
#     canonical emit (staged proposal) scrubs to the same closed-field allowlist.
#
# `decide_middle_out_degradation` is PURE + side-effect-free (does not mutate
# inputs, does not emit, does not write). `apply_middle_out_degradation` returns
# NEW message dicts (copies) with the middle elided — it likewise never emits,
# never writes, and never mutates the inputs in place.

# Env flag (default-OFF). `CEO_MIDDLE_OUT_DEGRADE` is the per-message keep-floor
# PERCENT (minimum % of each degraded message preserved, split head/tail).
# Unset/invalid/<=0/>100 ⇒ OFF.
ENV_MIDDLE_OUT_DEGRADE = "CEO_MIDDLE_OUT_DEGRADE"
ENV_MIDDLE_OUT_PROTECT_LAST = "CEO_MIDDLE_OUT_PROTECT_LAST"
ENV_MIDDLE_OUT_MIN_MSG_TOKENS = "CEO_MIDDLE_OUT_MIN_MSG_TOKENS"

# Defaults used ONLY when the feature is enabled (the keep-floor env is present
# and a valid int in (0, 100]).
DEFAULT_MIDDLE_OUT_KEEP_FLOOR_PCT = 40   # keep >= this % of any degraded message
DEFAULT_MIDDLE_OUT_PROTECT_LAST = 3      # never degrade the last N messages
DEFAULT_MIDDLE_OUT_MIN_MSG_TOKENS = 1000  # only degrade messages bigger than this

# The degradation ladder: ascending fractions of a message's content to TARGET
# for removal at each rung. The actual removal is clamped so the kept fraction
# never drops below the keep-floor (so a "90% drop" rung with a 40% keep-floor
# removes at most 60%). A closed, ordered tuple — the rungs are stable for log
# tabulation. Rung index 0 is the least aggressive.
MIDDLE_OUT_LADDER = (0.25, 0.50, 0.75, 0.90)

# Marker inserted where the middle was elided (token-cheap, signals truncation).
MIDDLE_OUT_ELISION_MARKER = "\n…[middle-out: {n} chars elided]…\n"

# Degradation-plan reason codes (stable strings for log tabulation; closed set,
# mirrored by the canonical `_MIDDLE_OUT_REASON_ENUM`).
MO_REASON_DISABLED = "disabled"        # feature OFF (env unset/invalid)
MO_REASON_NO_OVERFLOW = "no_overflow"   # already within budget — nothing to do
MO_REASON_DEGRADED = "degraded"         # ladder reclaimed enough → fits now
MO_REASON_FAILED = "failed"             # ladder exhausted, still over budget


class MiddleOutPolicy:
    """Config for the middle-out degradation ladder.

    Stateless by design — the host owns the message list and applies the plan.
    This object only holds the three knobs + the (constant) ladder.
    """

    def __init__(
        self,
        keep_floor_pct: int,
        protect_last: int,
        min_msg_tokens: int,
    ) -> None:
        # Clamp to sane, fail-open values (never raise on a bad number). The
        # keep-floor is a percent in [1, 100] (0 would allow dropping a whole
        # message — middle-out always keeps SOMETHING, so floor is >= 1).
        floor = _clamp_pct(keep_floor_pct, DEFAULT_MIDDLE_OUT_KEEP_FLOOR_PCT)
        self.keep_floor_pct = floor if floor >= 1 else 1
        self.protect_last = _clamp_nonneg_int(
            protect_last, DEFAULT_MIDDLE_OUT_PROTECT_LAST)
        self.min_msg_tokens = _clamp_nonneg_int(
            min_msg_tokens, DEFAULT_MIDDLE_OUT_MIN_MSG_TOKENS)


def load_middle_out_policy_from_env(
    env: Optional[Dict[str, str]] = None,
) -> Optional[MiddleOutPolicy]:
    """Build a MiddleOutPolicy from env, or None when the feature is OFF.

    OFF (returns None) unless `CEO_MIDDLE_OUT_DEGRADE` is set to an int in
    (0, 100] (the per-message keep-floor percent). Other knobs fall back to
    documented defaults when unset/invalid. Fail-open: never raises.
    """
    floor = _env_int(ENV_MIDDLE_OUT_DEGRADE, env)
    if floor is None or floor <= 0 or floor > 100:
        return None  # default-OFF
    protect = _env_int(ENV_MIDDLE_OUT_PROTECT_LAST, env)
    min_tokens = _env_int(ENV_MIDDLE_OUT_MIN_MSG_TOKENS, env)
    return MiddleOutPolicy(
        keep_floor_pct=floor,
        protect_last=protect if protect is not None else DEFAULT_MIDDLE_OUT_PROTECT_LAST,
        min_msg_tokens=min_tokens if min_tokens is not None else DEFAULT_MIDDLE_OUT_MIN_MSG_TOKENS,
    )


def _message_is_pinned(record: Any) -> bool:
    """True if a message record is explicitly pinned / kept-in-model.

    A mapping carrying ``pinned``-truthy or ``agent_visible`` is NEVER degraded
    (the dual-visibility D3 marker + an explicit pin both protect a message).
    Anything we cannot interpret is treated as NOT pinned (fail-open: we never
    refuse to consider a message just because it lacks a flag — but see the
    size/protect-window gates which independently protect it).
    """
    if isinstance(record, dict):
        if record.get("pinned"):
            return True
        if record.get("agent_visible") is True:
            return True
    return False


def _message_content(record: Any) -> Optional[str]:
    """Best-effort text content of one message record, or None.

    Accepts a mapping with a ``content`` (preferred) or ``text`` str field, or a
    bare str. Returns None when no text can be derived (the record is then never
    degraded — fail-open: we never elide content we cannot read).
    """
    if isinstance(record, str):
        return record
    if isinstance(record, dict):
        for key in ("content", "text"):
            v = record.get(key)
            if isinstance(v, str):
                return v
    return None


def _message_token_size(record: Any) -> Optional[int]:
    """Best-effort estimated token size of one message record.

    Prefers an explicit ``est_tokens`` / ``tokens`` field; else estimates from
    the text content length (chars/4). Returns None when no size can be derived
    (the record is then treated as below-floor and never degraded).
    """
    if isinstance(record, bool):
        return None
    if isinstance(record, int):
        return record if record >= 0 else None
    if isinstance(record, dict):
        for key in ("est_tokens", "tokens"):
            if key in record:
                try:
                    n = int(record[key])
                except (TypeError, ValueError):
                    return None
                return n if n >= 0 else None
        if "chars" in record:
            try:
                c = int(record["chars"])
            except (TypeError, ValueError):
                return None
            return estimate_tokens(c) if c >= 0 else None
    text = _message_content(record)
    if text is not None:
        return estimate_tokens(len(text))
    return None


def _elide_middle(text: str, drop_fraction: float, keep_floor_pct: int) -> Tuple[str, int]:
    """Drop the MIDDLE of `text`, keeping head+tail. Returns (new_text, chars_dropped).

    `drop_fraction` is the TARGET fraction (0..1) of chars to remove; the actual
    removal is clamped so the kept fraction never falls below `keep_floor_pct`%.
    The kept portion is split as evenly as possible head/tail (head gets the odd
    char on an odd split). A token-cheap elision marker replaces the gap.

    Fail-open: a non-str, empty, or degenerate input returns the text unchanged
    with 0 dropped (never raises).
    """
    if not isinstance(text, str) or not text:
        return text, 0
    total = len(text)
    try:
        frac = float(drop_fraction)
    except (TypeError, ValueError):
        return text, 0
    if frac <= 0:
        return text, 0
    if frac > 1:
        frac = 1.0
    # Clamp the drop so the kept fraction stays at/above the keep-floor.
    max_drop_frac = max(0.0, 1.0 - (keep_floor_pct / 100.0))
    eff_frac = min(frac, max_drop_frac)
    drop_chars = int(total * eff_frac)
    if drop_chars <= 0:
        return text, 0
    keep_chars = total - drop_chars
    if keep_chars <= 0:
        # Degenerate (keep-floor 0 path defended elsewhere) — keep 1 char head.
        keep_chars = 1
        drop_chars = total - 1
        if drop_chars <= 0:
            return text, 0
    head_len = (keep_chars + 1) // 2  # head gets the odd char
    tail_len = keep_chars - head_len
    head = text[:head_len]
    tail = text[total - tail_len:] if tail_len > 0 else ""
    marker = MIDDLE_OUT_ELISION_MARKER.format(n=drop_chars)
    new_text = head + marker + tail
    # Report the NET char delta actually removed (the marker adds a few back).
    net_dropped = total - len(new_text)
    if net_dropped <= 0:
        # The marker was longer than what we dropped (tiny message) — no-op.
        return text, 0
    return new_text, net_dropped


def decide_middle_out_degradation(
    messages: Any,
    budget_tokens: Any,
    *,
    policy: Optional[MiddleOutPolicy] = None,
    env: Optional[Dict[str, str]] = None,
) -> Dict[str, Any]:
    """Decide which messages to degrade middle-out, and at which ladder rung.

    Pure + side-effect-free + fail-open. PROTECTS the last N + pinned messages.
    Does NOT mutate `messages` and does NOT perform the elision — it returns a
    plan that `apply_middle_out_degradation` (or the host) executes.

    Parameters
    ----------
    messages
        An ordered sequence of message records, OLDEST FIRST (index 0 is the
        oldest, index ``len-1`` the most recent). Each record may be a mapping
        carrying ``content``/``text`` and/or a size (``est_tokens`` / ``tokens``
        / ``chars``), or a bare str. The order determines the protect-last-N
        window; the host supplies it.
    budget_tokens
        The token budget the assembled context must fit within (e.g. the model
        window minus a safety margin). Overflow = sum(sizes) > budget.
    policy
        Explicit policy; when None, derived from `env` (default-OFF if the
        keep-floor env is unset/invalid).

    Returns a plan dict (never raises):
      {
        "enabled": bool,            # feature active
        "reason": <MO_REASON_*>,    # stable plan-level reason code
        "rung": int,                # ladder rung reached (-1 if none entered)
        "degraded": [               # per-message degradation directives
          {"index": int, "drop_fraction": float}, ...
        ],
        "degraded_count": int,
        "reclaim_tokens": int,      # est tokens the plan would reclaim
        "total_tokens": int,        # sum of message sizes (pre-degrade)
        "budget_tokens": int,       # the budget projected against
        "fits_after": bool,         # projected to fit after degradation
        "protected_count": int,     # last-N + pinned + below-floor skips
        "protect_last": int|None,
        "min_msg_tokens": int|None,
        "keep_floor_pct": int|None,
        "ladder_len": int,
      }

    NO payload echo: the plan carries ONLY integer indices + token totals + a
    rung integer + a float fraction + closed reason codes. It NEVER includes any
    message text, tool name, agent name, file path, or command bytes. The
    canonical emit (staged proposal) scrubs to the same closed-field allowlist.
    """
    plan: Dict[str, Any] = {
        "enabled": False,
        "reason": MO_REASON_DISABLED,
        "rung": -1,
        "degraded": [],
        "degraded_count": 0,
        "reclaim_tokens": 0,
        "total_tokens": 0,
        "budget_tokens": 0,
        "fits_after": True,
        "protected_count": 0,
        "protect_last": None,
        "min_msg_tokens": None,
        "keep_floor_pct": None,
        "ladder_len": len(MIDDLE_OUT_LADDER),
    }

    if policy is None:
        policy = load_middle_out_policy_from_env(env)
    if policy is None:
        return plan  # default-OFF — disabled plan

    plan["enabled"] = True
    plan["protect_last"] = policy.protect_last
    plan["min_msg_tokens"] = policy.min_msg_tokens
    plan["keep_floor_pct"] = policy.keep_floor_pct

    # Normalize the budget (fail-open: a bad/<=0 budget ⇒ disabled-ish no-op).
    try:
        budget = int(budget_tokens)
    except (TypeError, ValueError):
        budget = 0
    if budget <= 0:
        plan["reason"] = MO_REASON_NO_OVERFLOW
        return plan
    plan["budget_tokens"] = budget

    # Normalize the messages list (fail-open: a non-sequence ⇒ empty).
    try:
        items = list(messages)
    except TypeError:
        items = []
    total_msgs = len(items)
    if total_msgs == 0:
        plan["reason"] = MO_REASON_NO_OVERFLOW
        return plan

    # Size every message; sum the total (None-sized rows count as 0 — they are
    # never degraded so they cannot help, but they DO occupy real budget the
    # host is responsible for; we conservatively count what we can size).
    sizes: List[Optional[int]] = [_message_token_size(m) for m in items]
    total_tokens = sum(s for s in sizes if isinstance(s, int))
    plan["total_tokens"] = total_tokens

    # No overflow → nothing to do (the common, cheap path).
    if total_tokens <= budget:
        plan["reason"] = MO_REASON_NO_OVERFLOW
        return plan

    overflow = total_tokens - budget

    # Determine the protected window: the last `protect_last` indices + any
    # pinned message + any below-floor (too-small to bother) message.
    protect_last = policy.protect_last
    protect_from = max(0, total_msgs - protect_last) if protect_last > 0 else total_msgs

    # Eligible = age-eligible (before protect window) AND not pinned AND big
    # enough to bother (>= min_msg_tokens AND sizeable). Build (index, size),
    # LARGEST FIRST so we degrade the heaviest messages first within a rung.
    eligible: List[Tuple[int, int]] = []
    protected = 0
    for idx in range(total_msgs):
        size = sizes[idx]
        if idx >= protect_from:
            protected += 1
            continue
        if _message_is_pinned(items[idx]):
            protected += 1
            continue
        if size is None or size < policy.min_msg_tokens:
            protected += 1
            continue
        eligible.append((idx, size))
    plan["protected_count"] = protected

    if not eligible:
        # Nothing we are allowed to degrade — the ladder cannot help. FAILED
        # (the caller must summarize/compact/fail upstream).
        plan["reason"] = MO_REASON_FAILED
        plan["fits_after"] = False
        return plan

    # Largest-first ordering within a rung.
    eligible.sort(key=lambda t: (-t[1], t[0]))

    keep_floor = policy.keep_floor_pct
    # The most a single message can ever reclaim (its size × max-drop-fraction).
    max_drop_frac = max(0.0, 1.0 - (keep_floor / 100.0))

    # Climb the ladder. At rung r, every eligible message is degraded at the
    # rung's TARGET fraction (clamped by the keep-floor). We stop the instant
    # the cumulative reclaim covers the overflow, recording the per-message
    # directive + the rung reached. Higher rungs subsume lower ones (we recompute
    # from scratch per rung so the directive is the FINAL fraction per message).
    best_plan: Optional[Tuple[int, List[Dict[str, Any]], int]] = None
    for rung, target_frac in enumerate(MIDDLE_OUT_LADDER):
        eff_frac = min(float(target_frac), max_drop_frac)
        if eff_frac <= 0:
            continue
        directives: List[Dict[str, Any]] = []
        reclaim = 0
        for idx, size in eligible:
            drop = int(size * eff_frac)
            if drop <= 0:
                continue
            directives.append({"index": idx, "drop_fraction": round(eff_frac, 4)})
            reclaim += drop
            if reclaim >= overflow:
                break
        if reclaim >= overflow:
            # This rung fits — record and STOP (do not climb further).
            best_plan = (rung, directives, reclaim)
            break
        # This rung did not fit; remember the most-aggressive attempt so far
        # (the last rung, fully applied) for the FAILED-but-best report.
        best_plan = (rung, directives, reclaim)

    if best_plan is None:
        # No applicable rung (Codex pair-rail #3): e.g. keep-floor=100% -> max_drop_frac=0
        # -> every rung is skipped. Fail-OPEN with an empty FAILED plan instead of
        # crashing on the unpack below.
        plan["rung"] = -1
        plan["degraded"] = []
        plan["degraded_count"] = 0
        plan["reclaim_tokens"] = 0
        plan["fits_after"] = False
        plan["reason"] = MO_REASON_FAILED
        return plan
    rung, directives, reclaim = best_plan  # type: ignore[misc]
    # Sort directives by index for a deterministic, log-friendly order.
    directives.sort(key=lambda d: d["index"])
    plan["rung"] = rung
    plan["degraded"] = directives
    plan["degraded_count"] = len(directives)
    plan["reclaim_tokens"] = reclaim
    fits = reclaim >= overflow
    plan["fits_after"] = fits
    plan["reason"] = MO_REASON_DEGRADED if fits else MO_REASON_FAILED
    return plan


def apply_middle_out_degradation(
    messages: Any,
    plan: Dict[str, Any],
    *,
    policy: Optional[MiddleOutPolicy] = None,
    env: Optional[Dict[str, str]] = None,
) -> List[Any]:
    """Apply a `decide_middle_out_degradation` plan, returning NEW messages.

    Does NOT mutate the input list or its records — it returns a new list whose
    degraded entries are shallow copies with the middle of their text elided.
    Non-degraded messages are passed through unchanged (same object). Fail-open:
    a disabled/empty plan, a malformed message list, or a record we cannot read
    text from returns the input messages (as a list) untouched; never raises.

    `policy`/`env` resolve the keep-floor used by the elision; when None they are
    derived from env (default-OFF ⇒ the input is returned unchanged).
    """
    try:
        items = list(messages)
    except TypeError:
        return []

    if not isinstance(plan, dict) or not plan.get("enabled"):
        return items
    directives = plan.get("degraded") or []
    if not directives:
        return items

    if policy is None:
        policy = load_middle_out_policy_from_env(env)
    if policy is None:
        return items  # feature OFF at apply time ⇒ no-op
    keep_floor = policy.keep_floor_pct

    # Map index → drop_fraction for O(1) lookup.
    drop_by_index: Dict[int, float] = {}
    for d in directives:
        if not isinstance(d, dict):
            continue
        try:
            i = int(d.get("index"))
            f = float(d.get("drop_fraction"))
        except (TypeError, ValueError):
            continue
        drop_by_index[i] = f

    out: List[Any] = []
    n = len(items)
    for idx in range(n):
        rec = items[idx]
        frac = drop_by_index.get(idx)
        if frac is None or frac <= 0:
            out.append(rec)
            continue
        text = _message_content(rec)
        if text is None:
            out.append(rec)  # cannot read text ⇒ pass through unchanged
            continue
        new_text, dropped = _elide_middle(text, frac, keep_floor)
        if dropped <= 0:
            out.append(rec)  # nothing actually dropped ⇒ pass through
            continue
        if isinstance(rec, str):
            out.append(new_text)
        elif isinstance(rec, dict):
            new_rec = dict(rec)  # shallow copy — never mutate the input
            if "content" in rec and isinstance(rec.get("content"), str):
                new_rec["content"] = new_text
            elif "text" in rec and isinstance(rec.get("text"), str):
                new_rec["text"] = new_text
            else:
                new_rec["content"] = new_text
            new_rec["middle_out_degraded"] = True
            out.append(new_rec)
        else:
            out.append(rec)
    return out


# ---------------------------------------------------------------------------
# Optional P3 fold-in: tool-loop scan (ECC ecc-context-monitor idea)
# ---------------------------------------------------------------------------


def scan_tool_loops(
    audit_log: Path, min_run: int = 3,
) -> Dict[str, Any]:
    """Flag runs of N identical *consecutive* tool-calls in an audit-log.

    Reads a JSONL audit-log read-only; for each line, derives a tool key from
    ``tool_name`` (fallback ``action``). A run of ``>= min_run`` identical
    consecutive keys is flagged (an agent stuck in a tool loop). Advisory:
    tolerant of malformed lines, never blocks, never echoes payload content.
    Returns ``{loops: [...], lines_scanned, error?}``.
    """
    text = _read_text(audit_log)
    if text is None:
        return {"loops": [], "lines_scanned": 0, "error": "unreadable"}

    keys: List[str] = []
    scanned = 0
    for line in text.splitlines():
        line = line.strip()
        if not line:
            continue
        scanned += 1
        try:
            obj = json.loads(line)
        except (json.JSONDecodeError, ValueError):
            # Malformed line breaks the consecutive run (use a sentinel).
            keys.append("\x00malformed")
            continue
        if not isinstance(obj, dict):
            keys.append("\x00malformed")
            continue
        key = obj.get("tool_name") or obj.get("action") or "\x00unknown"
        keys.append(str(key))

    loops: List[Dict[str, Any]] = []
    i = 0
    n = len(keys)
    while i < n:
        j = i
        while j < n and keys[j] == keys[i]:
            j += 1
        run_len = j - i
        key = keys[i]
        if run_len >= min_run and not key.startswith("\x00"):
            loops.append({
                "tool": key,
                "consecutive_count": run_len,
                "start_index": i,
                "message": (
                    "{n} consecutive '{tool}' calls (>= {m}) — possible tool "
                    "loop".format(n=run_len, tool=key, m=min_run)
                ),
            })
        i = j

    return {"loops": loops, "lines_scanned": scanned}


# ---------------------------------------------------------------------------
# Rendering
# ---------------------------------------------------------------------------


def _render_human(report: Dict[str, Any], top: int) -> str:
    lines: List[str] = []
    lines.append("# context-budget report")
    lines.append("# heuristic: {}".format(report["heuristic"]))
    lines.append(
        "# grand total: ~{} est tokens across the always-loaded surface".format(
            report["grand_total_est_tokens"],
        )
    )
    lines.append("")
    lines.append("## per-category")
    lines.append("  {:<12} {:>6} {:>8} {:>10}".format(
        "category", "files", "lines", "est_tok"))
    for c in report["categories"]:
        if c["category"] == CAT_MCP:
            extra = "servers={}".format(c.get("server_count", 0))
            if c.get("over_subscribed"):
                extra += " OVER-SUBSCRIBED"
            lines.append("  {:<12} {:>6} {:>8} {:>10}  {}".format(
                c["category"], c["file_count"], "-", "-", extra))
        else:
            lines.append("  {:<12} {:>6} {:>8} {:>10}".format(
                c["category"], c["file_count"], c["total_lines"], c["est_tokens"]))
    lines.append("")

    lines.append("## top {} reduction candidates (by est tokens)".format(top))
    if not report["top_candidates"]:
        lines.append("  (none — no files inventoried)")
    else:
        for e in report["top_candidates"]:
            lines.append("  ~{:>7} tok  {:>5}L  [{}]  {}".format(
                e["est_tokens"], e["lines"], e["category"], e["path"]))
    lines.append("")

    # PLAN-153 Wave C item 5 — top-3 savings opportunities.
    savings = report.get("savings_top3", [])
    lines.append("## top-3 savings opportunities (progressive disclosure)")
    if not savings:
        lines.append(
            "  (none — no un-split SKILL.md over {} lines)".format(
                THRESHOLD_SKILL_LINES))
    else:
        for s in savings:
            lines.append(
                "  {}. {} — {}L, ~{} est tok; potential saving ~{} est tok "
                "per activation".format(
                    s["rank"], s["path"], s["lines"], s["est_tokens"],
                    s["est_saving_tokens"]))
            lines.append("     why ranked: {}".format(s["reason"]))
            lines.append("     mechanism: {}".format(s["mechanism"]))
            if s.get("caveat"):
                lines.append("     caveat: {}".format(s["caveat"]))
    lines.append("")

    lines.append("## flags ({} total)".format(report["flag_count"]))
    if not report["flags"]:
        lines.append("  OK: no heavy-file / bloat / over-subscription flags.")
    else:
        for f in report["flags"]:
            lines.append("  [{}] {}".format(f["kind"], f.get("path", f["category"])))
            lines.append("      {}".format(f["message"]))
    lines.append("")

    lines.append("## honesty notes")
    for note in report.get("notes", []):
        lines.append("  - {}".format(note))
    if not report.get("scanner_available", True):
        lines.append(
            "  - DEGRADED: _lib/injection_patterns unavailable — displayed "
            "identifiers fell back to the charset allowlist only.")
    lines.append("")
    lines.append("# advisory only — this tool never blocks and never writes "
                 "outside stdout.")
    return "\n".join(lines)


def _render_loops_human(result: Dict[str, Any]) -> str:
    lines: List[str] = []
    lines.append("# tool-loop scan")
    lines.append("# lines scanned: {}".format(result.get("lines_scanned", 0)))
    if result.get("error"):
        lines.append("# error: {}".format(result["error"]))
    loops = result.get("loops", [])
    if not loops:
        lines.append("  OK: no tool loops detected.")
    else:
        for lp in loops:
            lines.append("  [tool_loop] {}".format(lp["message"]))
    lines.append("")
    lines.append("# advisory only.")
    return "\n".join(lines)


# ---------------------------------------------------------------------------
# CLI
# ---------------------------------------------------------------------------


def _cli(argv: List[str]) -> int:
    parser = argparse.ArgumentParser(
        description="ceo-orchestration context-budget audit (advisory, "
                    "read-only, never blocks)",
    )
    parser.add_argument(
        "--repo-root", default=".", help="project root (default: cwd)")
    parser.add_argument(
        "--json", action="store_true", help="machine-readable JSON output")
    parser.add_argument(
        "--top", type=int, default=10,
        help="how many top reduction candidates to rank (default: 10)")
    parser.add_argument(
        "--strict", action="store_true",
        help="exit 1 if any flag fires (opt-in advisory CI lint)")
    parser.add_argument(
        "--scheduled", action="store_true",
        help="mark this run as scheduled machinery (honors CEO_SOTA_DISABLE)")
    parser.add_argument(
        "--tool-loop-scan", metavar="AUDIT_LOG", default=None,
        help="(P3) flag N identical consecutive tool-calls in an audit-log "
             "JSONL file, then exit")
    parser.add_argument(
        "--loop-min", type=int, default=3,
        help="min consecutive identical tool-calls to flag a loop (default: 3)")
    # PLAN-133 D1 — auto-compaction decision probe (advisory; default-OFF unless
    # CEO_AUTO_COMPACT_THRESHOLD is set in the environment).
    parser.add_argument(
        "--compact-decision", action="store_true",
        help="(D1) print the proactive auto-compaction decision for a context "
             "snapshot, then exit. Default-OFF: requires CEO_AUTO_COMPACT_THRESHOLD.")
    parser.add_argument("--used-tokens", type=int, default=None,
                        help="(D1) current context usage in tokens")
    parser.add_argument("--window-tokens", type=int, default=None,
                        help="(D1) model context window in tokens")
    parser.add_argument("--reclaimable-tokens", type=int, default=None,
                        help="(D1) estimated tokens a compaction would free")
    parser.add_argument("--armed", dest="armed", action="store_true", default=True,
                        help="(D1) re-arm flag is set (default)")
    parser.add_argument("--disarmed", dest="armed", action="store_false",
                        help="(D1) re-arm flag is cleared (post-compaction)")
    parser.add_argument("--turns-since-compaction", type=int, default=None,
                        help="(D1) turns elapsed since the last compaction")
    # PLAN-133 D2 — oldest-verbose-output summarization decision probe
    # (advisory; default-OFF unless CEO_SUMMARIZE_OLDEST is set). Reads an
    # ordered list of per-output token sizes (oldest first) from a JSON file or
    # inline, and prints the summarization plan, then exits.
    parser.add_argument(
        "--summarize-decision", action="store_true",
        help="(D2) print the oldest-verbose-output summarization plan for a "
             "list of subagent output token-sizes, then exit. Default-OFF: "
             "requires CEO_SUMMARIZE_OLDEST.")
    parser.add_argument(
        "--output-sizes", metavar="JSON", default=None,
        help="(D2) JSON array of per-output est-token sizes (OLDEST FIRST), "
             "e.g. '[12000, 800, 30000, 500]'")
    parser.add_argument(
        "--output-sizes-file", metavar="PATH", default=None,
        help="(D2) path to a JSON file holding the per-output size array")
    # PLAN-133 D5 — middle-out degradation ladder decision probe (advisory;
    # default-OFF unless CEO_MIDDLE_OUT_DEGRADE is set). Reads an ordered list of
    # per-message token sizes (oldest first) + a budget, and prints the
    # degradation plan, then exits. Decision only — never elides anything.
    parser.add_argument(
        "--middle-out-decision", action="store_true",
        help="(D5) print the middle-out degradation plan for a list of message "
             "token-sizes + a token budget, then exit. Default-OFF: requires "
             "CEO_MIDDLE_OUT_DEGRADE.")
    parser.add_argument(
        "--message-sizes", metavar="JSON", default=None,
        help="(D5) JSON array of per-message est-token sizes (OLDEST FIRST), "
             "e.g. '[50000, 800, 50000, 500]'")
    parser.add_argument(
        "--message-sizes-file", metavar="PATH", default=None,
        help="(D5) path to a JSON file holding the per-message size array")
    parser.add_argument(
        "--budget-tokens", type=int, default=None,
        help="(D5) the token budget the assembled context must fit within")
    args = parser.parse_args(argv)

    # CEO_SOTA_DISABLE contract: any *scheduled* machinery must honor it.
    if args.scheduled and os.environ.get("CEO_SOTA_DISABLE"):
        print("[context-budget] skipped: CEO_SOTA_DISABLE is set "
              "(scheduled run)")
        return 0

    # Clamp a negative --top to 0 (least-surprising): a negative limit would
    # otherwise SKIP the slice and return ALL candidates plus print a
    # nonsensical "top -N" header. 0 cleanly means "rank nothing".
    if args.top is not None and args.top < 0:
        args.top = 0

    # D1 fold-in mode — independent of the inventory. Advisory + read-only:
    # prints the decision dict, never compacts, never emits, always exit 0.
    if args.compact_decision:
        decision = decide_compaction(
            args.used_tokens,
            args.window_tokens,
            reclaimable_tokens=args.reclaimable_tokens,
            armed=args.armed,
            turns_since_last_compaction=args.turns_since_compaction,
        )
        print(json.dumps(decision, indent=2))
        return 0

    # D2 fold-in mode — independent of the inventory. Advisory + read-only:
    # prints the summarization plan, never summarizes, never emits, exit 0.
    if args.summarize_decision:
        sizes: Any = []
        raw = None
        if args.output_sizes_file:
            raw = _read_text(Path(args.output_sizes_file))
        elif args.output_sizes is not None:
            raw = args.output_sizes
        if raw is not None:
            try:
                sizes = json.loads(raw)
            except (json.JSONDecodeError, ValueError):
                sizes = []  # fail-open: malformed input ⇒ empty (disabled-ish)
        plan = decide_summarization(sizes)
        print(json.dumps(plan, indent=2))
        return 0

    # D5 fold-in mode — independent of the inventory. Advisory + read-only:
    # prints the degradation plan, never elides, never emits, exit 0.
    if args.middle_out_decision:
        msg_sizes: Any = []
        raw = None
        if args.message_sizes_file:
            raw = _read_text(Path(args.message_sizes_file))
        elif args.message_sizes is not None:
            raw = args.message_sizes
        if raw is not None:
            try:
                msg_sizes = json.loads(raw)
            except (json.JSONDecodeError, ValueError):
                msg_sizes = []  # fail-open: malformed input ⇒ empty
        budget = args.budget_tokens if args.budget_tokens is not None else 0
        plan = decide_middle_out_degradation(msg_sizes, budget)
        print(json.dumps(plan, indent=2))
        return 0

    # P3 fold-in mode — independent of the inventory.
    if args.tool_loop_scan is not None:
        result = scan_tool_loops(Path(args.tool_loop_scan), min_run=args.loop_min)
        if args.json:
            print(json.dumps(result, indent=2))
        else:
            print(_render_loops_human(result))
        # Advisory: exit 0 unless --strict and loops were found.
        if args.strict and result.get("loops"):
            return 1
        return 0

    repo = Path(args.repo_root).resolve()
    report = build_inventory(repo, top=args.top)

    if args.json:
        print(json.dumps(report, indent=2))
    else:
        print(_render_human(report, args.top))

    if args.strict and report["flag_count"] > 0:
        return 1
    return 0


if __name__ == "__main__":
    sys.exit(_cli(sys.argv[1:]))
