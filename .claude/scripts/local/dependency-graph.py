#!/usr/bin/env python3
"""Dependency graph viz for PLAN-*.md files.

PLAN-078 Wave 4 spike (non-canonical, no GPG required).

Reads frontmatter from .claude/plans/PLAN-*.md, builds a directed graph from
depends_on / external_wait / related_plans / parent_plan, and renders an
offline-safe HTML file with inline SVG.

Security posture (per PLAN-078 §Wave 4 SEC-P1-03):
  - All dynamic content rendered via SVG <text> nodes; never innerHTML.
  - Plan markdown body is NEVER rendered — only whitelisted frontmatter fields.
  - Output is pure HTML+SVG, no JavaScript, no network calls.

Field whitelist (PLAN-SCHEMA §2-3 + extension precedent):
  id, title, status, created, owner, depends_on, sprint, tags,
  external_wait, related_plans, parent_plan, level

Output: .claude/scripts/local/dependency-graph.html (gitignored target).
Default location is OUTSIDE .claude/plans/ to avoid PLAN-SCHEMA §1 filename
validation (validate-governance.sh requires .claude/plans/ files match
PLAN-NNN-*.md pattern).
"""

from __future__ import annotations

import argparse
import html
import re
import sys
from dataclasses import dataclass, field
from pathlib import Path
from typing import Dict, List, Optional, Set, Tuple

# --- Field whitelist (per PLAN-078 §Wave 4 + Codex CDX-UNIQUE-05) ---

WHITELIST = frozenset({
    "id", "title", "status", "created", "owner", "depends_on",
    "sprint", "tags", "external_wait", "related_plans",
    "parent_plan", "level",
})

# --- Status → color (per PLAN-078 §Wave 4) ---

STATUS_COLORS = {
    "done": "#2ecc71",       # green
    "executing": "#f1c40f",  # yellow
    "reviewed": "#3498db",   # blue
    "draft": "#95a5a6",      # gray
    "abandoned": "#e74c3c",  # red
    "refused": "#c0392b",    # darker red (matches magenta intent — adjusted)
}

# Edge styles
EDGE_STYLES = {
    "depends_on": "stroke-dasharray:none",
    "external_wait": "stroke-dasharray:6,4",
    "related_plans": "stroke-dasharray:2,3",
    "parent_plan": "stroke-dasharray:8,2,2,2",
}

EDGE_LABELS = {
    "depends_on": "depends",
    "external_wait": "wait",
    "related_plans": "related",
    "parent_plan": "parent",
}

# Layout constants
NODE_WIDTH = 180
NODE_HEIGHT = 50
LEVEL_GAP_X = 240
NODE_GAP_Y = 70
SVG_PADDING = 40

# Output cap (PLAN-078 §Wave 4 PERF-P1-04: <500KB at 200 plans)
MAX_HTML_BYTES = 500 * 1024


# ---------- YAML frontmatter parser (stdlib-only, minimal) ----------


@dataclass
class FrontmatterParseError(Exception):
    path: Path
    reason: str

    def __str__(self) -> str:
        return f"FrontmatterParseError: {self.path}: {self.reason}"


def _strip_inline_comment(value: str) -> str:
    """Strip ' # comment' suffix from a YAML scalar value (common in PLAN files).

    Preserves '#' inside quoted strings.
    """
    in_single = False
    in_double = False
    for i, ch in enumerate(value):
        if ch == "'" and not in_double:
            in_single = not in_single
        elif ch == '"' and not in_single:
            in_double = not in_double
        elif ch == "#" and not in_single and not in_double:
            # Comment marker, but only if preceded by whitespace
            if i == 0 or value[i - 1] in (" ", "\t"):
                return value[:i].rstrip()
    return value.rstrip()


def _parse_scalar(raw: str) -> object:
    """Parse a YAML scalar (string/int/null/bool). No coercion of dates."""
    s = _strip_inline_comment(raw).strip()
    if not s:
        return None
    if s.lower() in ("null", "~"):
        return None
    if s.lower() == "true":
        return True
    if s.lower() == "false":
        return False
    # Quoted string
    if (s.startswith("'") and s.endswith("'")) or (s.startswith('"') and s.endswith('"')):
        return s[1:-1]
    # Int
    if re.match(r"^-?\d+$", s):
        try:
            return int(s)
        except ValueError:
            pass
    return s


def _parse_inline_list(raw: str) -> List[object]:
    """Parse [a, b, c] inline YAML list. Items are scalars."""
    inner = raw.strip()
    if not (inner.startswith("[") and inner.endswith("]")):
        return []
    inner = inner[1:-1].strip()
    if not inner:
        return []
    items: List[object] = []
    # Simple split by comma at depth 0 (no nested lists in our schema)
    depth = 0
    in_quote: Optional[str] = None
    buf: List[str] = []
    for ch in inner:
        if in_quote:
            buf.append(ch)
            if ch == in_quote:
                in_quote = None
        elif ch in ("'", '"'):
            buf.append(ch)
            in_quote = ch
        elif ch == "[" or ch == "{":
            depth += 1
            buf.append(ch)
        elif ch == "]" or ch == "}":
            depth -= 1
            buf.append(ch)
        elif ch == "," and depth == 0:
            items.append(_parse_scalar("".join(buf)))
            buf = []
        else:
            buf.append(ch)
    if buf:
        items.append(_parse_scalar("".join(buf)))
    return items


def _extract_frontmatter_block(text: str) -> Optional[str]:
    """Return the YAML frontmatter block (between leading --- ... ---) or None.

    Frontmatter must start at offset 0.
    """
    if not text.startswith("---"):
        return None
    # Find closing ---
    rest = text[3:]
    # The closing must be on its own line
    m = re.search(r"\n---\s*(?:\n|$)", rest)
    if not m:
        return None
    return rest[: m.start()]


def parse_frontmatter(path: Path) -> Dict[str, object]:
    """Parse YAML frontmatter from a plan file.

    Returns a dict with whitelisted keys only. Unknown keys are dropped silently
    (whitelist enforcement). Raises FrontmatterParseError on structural issues.
    """
    try:
        text = path.read_text(encoding="utf-8", errors="replace")
    except OSError as exc:
        raise FrontmatterParseError(path=path, reason=f"read error: {exc}")

    block = _extract_frontmatter_block(text)
    if block is None:
        raise FrontmatterParseError(path=path, reason="no frontmatter block")

    data: Dict[str, object] = {}
    current_key: Optional[str] = None
    current_list: Optional[List[object]] = None

    for raw_line in block.splitlines():
        line = raw_line.rstrip()
        if not line.strip():
            current_key = None
            current_list = None
            continue
        # Sub-list item under a multi-line list: leading whitespace + '-'
        m_item = re.match(r"^\s+-\s*(.*)$", line)
        if m_item and current_key is not None and current_list is not None:
            item = _parse_scalar(m_item.group(1))
            if item is not None:
                current_list.append(item)
            continue
        # Indented "key: value" inside a nested mapping — drop (we only read top-level)
        if line.startswith(" ") or line.startswith("\t"):
            continue
        # Top-level key
        m_kv = re.match(r"^([A-Za-z_][A-Za-z0-9_]*):\s*(.*)$", line)
        if not m_kv:
            current_key = None
            current_list = None
            continue
        key, val = m_kv.group(1), m_kv.group(2)
        if key not in WHITELIST:
            current_key = None
            current_list = None
            continue
        # Inline list
        stripped = val.strip()
        if stripped.startswith("["):
            data[key] = _parse_inline_list(stripped)
            current_key = None
            current_list = None
            continue
        # Multi-line list start (empty value on key line)
        if not stripped:
            data[key] = []
            current_key = key
            current_list = data[key]  # type: ignore[assignment]
            continue
        # Scalar (or block scalar | / >)
        if stripped in ("|", ">"):
            data[key] = ""  # don't capture multi-line scalars
            current_key = None
            current_list = None
            continue
        data[key] = _parse_scalar(stripped)
        current_key = None
        current_list = None

    return data


# ---------- Graph data model ----------


@dataclass
class PlanNode:
    plan_id: str
    title: str
    status: str
    sprint: Optional[str]
    edges: Dict[str, List[str]] = field(default_factory=dict)
    # Layout assignments (filled later)
    level: int = 0
    column: int = 0


@dataclass
class GraphBuildResult:
    nodes: Dict[str, PlanNode]
    warnings: List[str]
    errors: List[str]


def _normalize_plan_id(value: object) -> Optional[str]:
    """Coerce a frontmatter id-like value to string. Return None if not extractable."""
    if value is None:
        return None
    if isinstance(value, str):
        s = value.strip()
        return s or None
    if isinstance(value, int):
        return f"PLAN-{value:03d}"
    return None


def _extract_id_from_filename(path: Path) -> Optional[str]:
    m = re.match(r"^(PLAN-\d{3})", path.name)
    return m.group(1) if m else None


def build_graph(plans_dir: Path) -> GraphBuildResult:
    """Walk plans_dir for PLAN-*.md, parse frontmatter, build node + edge map."""
    nodes: Dict[str, PlanNode] = {}
    warnings: List[str] = []
    errors: List[str] = []

    plan_paths = sorted(plans_dir.glob("PLAN-*.md"))
    if not plan_paths:
        warnings.append(f"no PLAN-*.md files in {plans_dir}")

    for path in plan_paths:
        try:
            fm = parse_frontmatter(path)
        except FrontmatterParseError as exc:
            errors.append(str(exc))
            continue
        plan_id = _normalize_plan_id(fm.get("id")) or _extract_id_from_filename(path)
        if not plan_id:
            warnings.append(f"{path.name}: no id; skipping")
            continue
        title = str(fm.get("title", "")) or path.stem
        status = str(fm.get("status", "draft")).lower().strip() or "draft"
        sprint_val = fm.get("sprint")
        sprint = str(sprint_val) if sprint_val is not None else None

        edges: Dict[str, List[str]] = {}
        for edge_kind in ("depends_on", "external_wait", "related_plans", "parent_plan"):
            raw = fm.get(edge_kind)
            ids: List[str] = []
            if isinstance(raw, list):
                for item in raw:
                    pid = _normalize_plan_id(item)
                    if pid and re.match(r"^PLAN-\d{3}$", pid):
                        ids.append(pid)
            elif isinstance(raw, str):
                # Single value (parent_plan or external_wait scalar form)
                # external_wait often holds free-form text; only retain PLAN-NNN
                m = re.search(r"PLAN-\d{3}", raw)
                if m:
                    ids.append(m.group(0))
            if ids:
                edges[edge_kind] = ids
        nodes[plan_id] = PlanNode(
            plan_id=plan_id,
            title=title,
            status=status,
            sprint=sprint,
            edges=edges,
        )

    # Validate edges: warn on unknowns
    known_ids = set(nodes.keys())
    for plan_id, node in nodes.items():
        for kind, refs in list(node.edges.items()):
            unknowns = [r for r in refs if r not in known_ids]
            if unknowns:
                warnings.append(
                    f"{plan_id}: {kind} references unknown plan(s): {', '.join(unknowns)}"
                )
                # Drop unknowns from edge list to keep graph valid
                node.edges[kind] = [r for r in refs if r in known_ids]
                if not node.edges[kind]:
                    del node.edges[kind]

    return GraphBuildResult(nodes=nodes, warnings=warnings, errors=errors)


# ---------- Cycle detection ----------


def detect_cycles(nodes: Dict[str, PlanNode]) -> List[List[str]]:
    """Detect cycles via DFS. Considers depends_on edges only (the structural ones).

    Returns list of cycle-paths. Empty list if acyclic.
    """
    cycles: List[List[str]] = []
    WHITE, GRAY, BLACK = 0, 1, 2
    color = {pid: WHITE for pid in nodes}
    stack: List[str] = []

    def visit(pid: str) -> None:
        color[pid] = GRAY
        stack.append(pid)
        node = nodes.get(pid)
        if node is not None:
            for nxt in node.edges.get("depends_on", []):
                if nxt not in color:
                    continue
                if color[nxt] == GRAY:
                    if nxt in stack:
                        idx = stack.index(nxt)
                        cycles.append(stack[idx:] + [nxt])
                elif color[nxt] == WHITE:
                    visit(nxt)
        color[pid] = BLACK
        stack.pop()

    for pid in sorted(nodes.keys()):
        if color[pid] == WHITE:
            visit(pid)
    return cycles


# ---------- Layout ----------


def _topological_levels(nodes: Dict[str, PlanNode]) -> Dict[str, int]:
    """Assign each node a level = longest path from a root in depends_on DAG.

    Falls back to 0 for nodes participating in a cycle.
    """
    cycle_members: Set[str] = set()
    for cycle in detect_cycles(nodes):
        cycle_members.update(cycle)

    levels: Dict[str, int] = {}
    visiting: Set[str] = set()

    def lvl(pid: str) -> int:
        if pid in cycle_members:
            return 0
        if pid in levels:
            return levels[pid]
        if pid in visiting:
            return 0
        visiting.add(pid)
        node = nodes.get(pid)
        deps = node.edges.get("depends_on", []) if node else []
        depth = 0
        for d in deps:
            if d in nodes:
                depth = max(depth, lvl(d) + 1)
        visiting.discard(pid)
        levels[pid] = depth
        return depth

    for pid in nodes:
        lvl(pid)
    return levels


def assign_layout(nodes: Dict[str, PlanNode]) -> Tuple[int, int]:
    """Assign each node a (level, column) and return svg (width, height)."""
    levels = _topological_levels(nodes)
    by_level: Dict[int, List[str]] = {}
    for pid, level in levels.items():
        by_level.setdefault(level, []).append(pid)
    # Sort within level for determinism
    for level, ids in by_level.items():
        ids.sort()
    max_level = max(by_level.keys()) if by_level else 0
    max_column = max((len(ids) for ids in by_level.values()), default=0)
    for level, ids in by_level.items():
        for column, pid in enumerate(ids):
            node = nodes[pid]
            node.level = level
            node.column = column
    width = SVG_PADDING * 2 + (max_level + 1) * LEVEL_GAP_X + NODE_WIDTH
    height = SVG_PADDING * 2 + max_column * NODE_GAP_Y + NODE_HEIGHT
    return width, height


def node_position(node: PlanNode) -> Tuple[int, int]:
    x = SVG_PADDING + node.level * LEVEL_GAP_X
    y = SVG_PADDING + node.column * NODE_GAP_Y
    return x, y


# ---------- SVG rendering ----------


def _esc(text: str) -> str:
    """HTML-escape text content for safe embedding inside SVG <text> nodes."""
    return html.escape(text, quote=True)


def _truncate_title(title: str, max_chars: int = 30) -> str:
    if len(title) <= max_chars:
        return title
    return title[: max_chars - 1] + "…"


def render_svg(nodes: Dict[str, PlanNode]) -> Tuple[str, int, int]:
    """Render nodes + edges to a self-contained SVG string. Returns (svg, w, h)."""
    width, height = assign_layout(nodes)

    svg_parts: List[str] = []
    svg_parts.append(
        f'<svg xmlns="http://www.w3.org/2000/svg" '
        f'viewBox="0 0 {width} {height}" '
        f'width="{width}" height="{height}" '
        f'role="img" aria-label="Plan dependency graph">'
    )
    # Marker for arrowheads
    svg_parts.append(
        '<defs>'
        '<marker id="arrow" viewBox="0 0 10 10" refX="9" refY="5" '
        'markerWidth="6" markerHeight="6" orient="auto-start-reverse">'
        '<path d="M 0 0 L 10 5 L 0 10 z" fill="#34495e" />'
        '</marker>'
        '</defs>'
    )
    # Edges first (so nodes overlap them)
    for plan_id, node in sorted(nodes.items()):
        sx, sy = node_position(node)
        for kind in ("depends_on", "external_wait", "related_plans", "parent_plan"):
            for target_id in node.edges.get(kind, []):
                target = nodes.get(target_id)
                if target is None:
                    continue
                tx, ty = node_position(target)
                # Source: right-edge of source. Target: left-edge of target.
                x1 = sx + NODE_WIDTH
                y1 = sy + NODE_HEIGHT // 2
                x2 = tx
                y2 = ty + NODE_HEIGHT // 2
                style = EDGE_STYLES[kind]
                svg_parts.append(
                    f'<line x1="{x1}" y1="{y1}" x2="{x2}" y2="{y2}" '
                    f'stroke="#34495e" stroke-width="1.5" '
                    f'style="{style}" marker-end="url(#arrow)" />'
                )
    # Nodes
    for plan_id, node in sorted(nodes.items()):
        x, y = node_position(node)
        color = STATUS_COLORS.get(node.status, "#bdc3c7")
        svg_parts.append(
            f'<g transform="translate({x},{y})">'
            f'<rect width="{NODE_WIDTH}" height="{NODE_HEIGHT}" rx="6" ry="6" '
            f'fill="{color}" stroke="#2c3e50" stroke-width="1" />'
            f'<text x="10" y="18" font-family="monospace" font-size="12" '
            f'font-weight="bold" fill="#2c3e50">{_esc(plan_id)}</text>'
            f'<text x="10" y="36" font-family="sans-serif" font-size="10" '
            f'fill="#2c3e50">{_esc(_truncate_title(node.title))}</text>'
            f'</g>'
        )
    svg_parts.append('</svg>')
    return "".join(svg_parts), width, height


# ---------- HTML wrapper ----------


HTML_TEMPLATE = """<!DOCTYPE html>
<html lang="en">
<head>
<meta charset="utf-8">
<title>PLAN dependency graph</title>
<style>
  body {{ font-family: -apple-system, BlinkMacSystemFont, sans-serif; margin: 0; padding: 16px; background: #ecf0f1; color: #2c3e50; }}
  h1 {{ font-size: 18px; margin: 0 0 8px 0; }}
  .meta {{ font-size: 12px; color: #7f8c8d; margin-bottom: 12px; }}
  .legend {{ display: flex; flex-wrap: wrap; gap: 12px; margin-bottom: 12px; font-size: 12px; }}
  .legend span.swatch {{ display: inline-block; width: 14px; height: 14px; border-radius: 3px; vertical-align: middle; margin-right: 4px; border: 1px solid #2c3e50; }}
  .edge-legend {{ display: inline-block; margin-right: 12px; }}
  .edge-legend svg {{ vertical-align: middle; }}
  .container {{ overflow: auto; background: white; padding: 8px; border: 1px solid #bdc3c7; border-radius: 4px; }}
  .warnings {{ font-size: 11px; color: #c0392b; margin-top: 12px; max-height: 200px; overflow: auto; background: #fdedec; padding: 8px; border-radius: 4px; }}
</style>
</head>
<body>
<h1>PLAN dependency graph</h1>
<div class="meta">{plan_count} plans · generated {generated_at} · offline-safe (no JS, no network)</div>
<div class="legend">
  <span><span class="swatch" style="background:#2ecc71"></span>done</span>
  <span><span class="swatch" style="background:#f1c40f"></span>executing</span>
  <span><span class="swatch" style="background:#3498db"></span>reviewed</span>
  <span><span class="swatch" style="background:#95a5a6"></span>draft</span>
  <span><span class="swatch" style="background:#e74c3c"></span>abandoned</span>
  <span><span class="swatch" style="background:#c0392b"></span>refused</span>
</div>
<div class="legend">
  <span class="edge-legend"><svg width="40" height="6"><line x1="0" y1="3" x2="40" y2="3" stroke="#34495e" stroke-width="1.5"/></svg> depends_on</span>
  <span class="edge-legend"><svg width="40" height="6"><line x1="0" y1="3" x2="40" y2="3" stroke="#34495e" stroke-width="1.5" stroke-dasharray="6,4"/></svg> external_wait</span>
  <span class="edge-legend"><svg width="40" height="6"><line x1="0" y1="3" x2="40" y2="3" stroke="#34495e" stroke-width="1.5" stroke-dasharray="2,3"/></svg> related_plans</span>
  <span class="edge-legend"><svg width="40" height="6"><line x1="0" y1="3" x2="40" y2="3" stroke="#34495e" stroke-width="1.5" stroke-dasharray="8,2,2,2"/></svg> parent_plan</span>
</div>
<div class="container">
{svg}
</div>
{warnings_block}
</body>
</html>
"""


def render_html(
    svg: str,
    plan_count: int,
    warnings: List[str],
    generated_at: str,
) -> str:
    warnings_block = ""
    if warnings:
        items = "".join(f"<li>{_esc(w)}</li>" for w in warnings)
        warnings_block = (
            f'<div class="warnings"><strong>{len(warnings)} warning(s):</strong>'
            f'<ul>{items}</ul></div>'
        )
    return HTML_TEMPLATE.format(
        plan_count=plan_count,
        generated_at=_esc(generated_at),
        svg=svg,
        warnings_block=warnings_block,
    )


# ---------- CLI ----------


def main(argv: Optional[List[str]] = None) -> int:
    parser = argparse.ArgumentParser(
        description="Render PLAN-*.md dependency graph to standalone HTML."
    )
    parser.add_argument(
        "--plans-dir",
        type=Path,
        default=Path(".claude/plans"),
        help="Directory holding PLAN-*.md files (default: .claude/plans)",
    )
    parser.add_argument(
        "--output",
        type=Path,
        default=Path(".claude/scripts/local/dependency-graph.html"),
        help="Output HTML path (default: .claude/scripts/local/dependency-graph.html)",
    )
    parser.add_argument(
        "--strict-cycles",
        action="store_true",
        help="Exit non-zero if cycles are detected (default: warn only)",
    )
    parser.add_argument(
        "--max-bytes",
        type=int,
        default=MAX_HTML_BYTES,
        help=f"Cap output size in bytes (default: {MAX_HTML_BYTES})",
    )
    args = parser.parse_args(argv)

    plans_dir: Path = args.plans_dir
    if not plans_dir.is_dir():
        print(f"error: plans dir not found: {plans_dir}", file=sys.stderr)
        return 2

    result = build_graph(plans_dir)
    for err in result.errors:
        print(f"ERROR: {err}", file=sys.stderr)

    cycles = detect_cycles(result.nodes)
    if cycles:
        for cycle in cycles:
            msg = f"cycle detected: {' -> '.join(cycle)}"
            result.warnings.append(msg)
            print(f"WARN: {msg}", file=sys.stderr)
        if args.strict_cycles:
            return 3

    svg, _, _ = render_svg(result.nodes)
    from datetime import datetime, timezone

    generated_at = datetime.now(timezone.utc).strftime("%Y-%m-%d %H:%M:%SZ")
    html_str = render_html(
        svg=svg,
        plan_count=len(result.nodes),
        warnings=result.warnings,
        generated_at=generated_at,
    )

    out_bytes = html_str.encode("utf-8")
    if len(out_bytes) > args.max_bytes:
        print(
            f"error: output {len(out_bytes)} bytes exceeds cap {args.max_bytes}",
            file=sys.stderr,
        )
        return 4

    args.output.parent.mkdir(parents=True, exist_ok=True)
    args.output.write_bytes(out_bytes)
    print(
        f"wrote {args.output} ({len(out_bytes)} bytes, "
        f"{len(result.nodes)} plans, {len(result.warnings)} warnings)"
    )
    return 0


if __name__ == "__main__":
    sys.exit(main())
