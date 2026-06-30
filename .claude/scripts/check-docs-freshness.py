#!/usr/bin/env python3
"""
check-docs-freshness.py — scan markdown docs for broken relative links.

PLAN-010 Phase 3 (DevOps & Platform Engineer). Stdlib-only, Python >= 3.9.

Strategy (pragmatic, not a full CommonMark parser):

    1. Strip YAML frontmatter (first `---`...`---` block at file head).
    2. Walk lines with a state machine that tracks:
         - fenced code blocks (``` or ~~~ with optional language tag)
         - multi-line HTML comments (<!-- ... -->)
       Content inside those regions is skipped.
    3. On active lines, find inline code spans by pairing backtick runs
       (` vs `` vs ```). Content inside spans is skipped.
    4. Remaining text is scanned for markdown link syntax
       `[text](target)` with a tolerant regex. Each target is classified:
         - scheme URL (http/https/ftp/mailto/javascript)  → ignore
         - anchor-only (#...)                             → ignore
         - allowlisted                                    → ignore
         - otherwise: resolve target relative to the file, URL-decode,
           strip `#fragment` and `?query`, and check existence.

Exit codes:
    0 — clean
    1 — broken refs found (advisory in CI today; blocking per ADR-023)
    2 — usage / arg error

Output modes:
    text (default, human)
    json (machine — {"broken":[{"file","line","col","target","resolved"}],
                     "scanned_files": N, "broken_count": N})

Lifecycle: see ADR-023.
"""

from __future__ import annotations

import argparse
import json
import os
import re
import sys
import urllib.parse
from pathlib import Path
from typing import Iterable, List, Optional, Sequence, Tuple

# ---------- link extraction ------------------------------------------------

# Tolerant: [text](target "title"?). Allow nested brackets one level in text.
# We do NOT attempt full CommonMark; that's deliberate (stdlib-only + docs
# freshness is a smell detector, not a spec conformance test).
_LINK_RE = re.compile(
    r"""
    \[                              # opening bracket
    (?P<text>(?:[^\[\]\\]|\\.)*)    # text (no brackets / escaped)
    \]
    \(
    \s*
    (?P<target><[^>]*>|[^\s)]+)     # target (angle form or bare)
    (?:\s+"[^"]*")?                 # optional title
    (?:\s+'[^']*')?                 # optional title (single-quote)
    \s*
    \)
    """,
    re.VERBOSE,
)

_SCHEME_RE = re.compile(r"^[a-zA-Z][a-zA-Z0-9+.\-]*:")

# Default scan globs relative to repo root.
DEFAULT_GLOBS: Tuple[str, ...] = (
    "CLAUDE.md",
    "CLAUDE_FULL.md",
    "README.md",
    "docs/**/*.md",
    ".claude/adr/*.md",
    ".claude/plans/PLAN-*.md",
    ".claude/skills/**/*.md",
)


# ---------- fixture scope helper ------------------------------------------


def _is_fixture_path(path: Path) -> bool:
    """Fixtures under tests/fixtures/ are intentionally broken; skip them
    when running the default repo scan. Explicit --root still scans them."""
    parts = path.parts
    for i in range(len(parts) - 1):
        if parts[i] == "tests" and parts[i + 1] == "fixtures":
            return True
    return False


# ---------- preprocessing --------------------------------------------------


def strip_frontmatter(text: str) -> Tuple[str, int]:
    """Return (body, leading_blank_lines) so line numbers stay in sync.

    We replace the frontmatter region with blank lines to preserve line
    numbering for downstream errors.
    """
    lines = text.splitlines(keepends=False)
    if not lines or lines[0].strip() != "---":
        return text, 0
    # find closing ---
    for i in range(1, len(lines)):
        if lines[i].strip() == "---":
            # blank out lines 0..i inclusive
            blanked = [""] * (i + 1) + lines[i + 1 :]
            return "\n".join(blanked), i + 1
    return text, 0  # unterminated frontmatter → treat as plain


# ---------- state machine --------------------------------------------------


_FENCE_RE = re.compile(r"^(?P<indent>\s{0,3})(?P<marker>`{3,}|~{3,})\s*(?P<info>[^`]*)$")


def iter_scannable_spans(text: str) -> Iterable[Tuple[int, str]]:
    """
    Yield (line_number_1based, scannable_line_content) for each line that
    is OUTSIDE fenced code + outside HTML comments. Inside-code lines are
    skipped entirely (not yielded). Inside-comment lines are yielded with
    the commented portion masked to spaces so line numbers / columns stay
    aligned.
    """
    lines = text.splitlines(keepends=False)
    in_fence = False
    fence_marker: Optional[str] = None
    in_html_comment = False

    for idx, raw in enumerate(lines, start=1):
        # --- fence handling ---
        stripped = raw.lstrip()
        m = _FENCE_RE.match(raw)
        if not in_fence and m:
            in_fence = True
            fence_marker = m.group("marker")[0] * 3  # normalize to 3-char kind
            # the fence open line itself is not scannable
            continue
        if in_fence:
            if m and m.group("marker")[0] * 3 == fence_marker and not m.group("info").strip():
                # closing fence
                in_fence = False
                fence_marker = None
            # still skip this line either way
            continue

        # --- HTML comment handling (can span lines) ---
        line = raw
        if in_html_comment:
            end = line.find("-->")
            if end == -1:
                # whole line is inside comment
                continue
            # mask everything up to and including -->
            line = " " * (end + 3) + line[end + 3 :]
            in_html_comment = False

        # find further comment starts on this line (possibly multiple)
        masked = []
        i = 0
        while i < len(line):
            start = line.find("<!--", i)
            if start == -1:
                masked.append(line[i:])
                break
            masked.append(line[i:start])
            end = line.find("-->", start + 4)
            if end == -1:
                masked.append(" " * (len(line) - start))
                in_html_comment = True
                i = len(line)
                break
            masked.append(" " * (end + 3 - start))
            i = end + 3
        line = "".join(masked)

        yield idx, line


# ---------- inline code span masking --------------------------------------


def mask_inline_code(line: str) -> str:
    """
    Pair up backtick runs on a single line. Content inside matching runs is
    replaced with spaces (to preserve column numbers).

    CommonMark rule (simplified): a backtick run of length N is closed by
    the next run of exactly length N. Unmatched runs stay literal.
    """
    out = list(line)
    i = 0
    n = len(line)
    while i < n:
        if out[i] == "`":
            # count run length
            j = i
            while j < n and out[j] == "`":
                j += 1
            run_len = j - i
            # find matching close run of same length
            k = j
            while k < n:
                if out[k] == "`":
                    m = k
                    while m < n and out[m] == "`":
                        m += 1
                    if m - k == run_len:
                        # mask content between [j..k) (exclusive of backticks
                        # themselves — but we also mask the backticks so the
                        # link regex can't see inside)
                        for p in range(i, m):
                            out[p] = " "
                        i = m
                        break
                    else:
                        k = m
                else:
                    k += 1
            else:
                # no closing run; leave as-is
                i = j
        else:
            i += 1
    return "".join(out)


# ---------- resolution ----------------------------------------------------


def classify_target(target: str) -> str:
    """
    Return one of: 'external', 'anchor', 'empty', 'local'.
    """
    t = target.strip()
    if t.startswith("<") and t.endswith(">"):
        t = t[1:-1]
    if not t:
        return "empty"
    if t.startswith("#"):
        return "anchor"
    if _SCHEME_RE.match(t):
        return "external"
    if t.startswith("~"):
        # Home-relative pointer (e.g. ~/.claude/projects/.../memory/foo.md):
        # an external, out-of-tree reference (the Owner's native-memory dir),
        # never an in-repo doc link. Treat like a scheme URL — ignore.
        return "external"
    return "local"


def resolve_local(file_path: Path, target: str, root: Path) -> Path:
    """
    Resolve a local link target relative to the containing file. Strip
    #fragment and ?query. Returns the URL-decoded candidate path.
    Existence check is done by the caller via `resolve_local_exists`,
    which tries both decoded and raw forms (some repos have literal `%20`
    filenames).
    """
    t = _normalize_target(target)
    t = urllib.parse.unquote(t)
    if t.startswith("/"):
        return (root / t.lstrip("/")).resolve()
    return (file_path.parent / t).resolve()


def _normalize_target(target: str) -> str:
    t = target.strip()
    if t.startswith("<") and t.endswith(">"):
        t = t[1:-1]
    for sep in ("#", "?"):
        pos = t.find(sep)
        if pos != -1:
            t = t[:pos]
    return t


def resolve_local_candidates(file_path: Path, target: str, root: Path) -> List[Path]:
    """Return list of candidate paths to probe (decoded + raw)."""
    decoded = resolve_local(file_path, target, root)
    raw_t = _normalize_target(target)
    if raw_t.startswith("/"):
        raw = (root / raw_t.lstrip("/")).resolve()
    else:
        raw = (file_path.parent / raw_t).resolve()
    # dedupe preserving order
    out = [decoded]
    if raw != decoded:
        out.append(raw)
    return out


# ---------- allowlist -----------------------------------------------------


def load_allowlist(path: Optional[Path]) -> List[str]:
    if path is None or not path.exists():
        return []
    out: List[str] = []
    for raw in path.read_text(encoding="utf-8").splitlines():
        line = raw.strip()
        if not line or line.startswith("#"):
            continue
        out.append(line)
    return out


def is_allowlisted(target: str, allowlist: Sequence[str]) -> bool:
    t = target.strip()
    if t.startswith("<") and t.endswith(">"):
        t = t[1:-1]
    for sep in ("#", "?"):
        pos = t.find(sep)
        if pos != -1:
            t = t[:pos]
    return t in allowlist


# ---------- scan ----------------------------------------------------------


def scan_file(
    file_path: Path,
    root: Path,
    allowlist: Sequence[str],
) -> List[dict]:
    """Return list of broken-ref dicts for this file."""
    try:
        text = file_path.read_text(encoding="utf-8")
    except (OSError, UnicodeDecodeError):
        return []

    body, _ = strip_frontmatter(text)
    broken: List[dict] = []

    for lineno, raw_line in iter_scannable_spans(body):
        line = mask_inline_code(raw_line)
        for m in _LINK_RE.finditer(line):
            target = m.group("target")
            col = m.start("target") + 1
            kind = classify_target(target)
            if kind in ("external", "anchor", "empty"):
                continue
            if is_allowlisted(target, allowlist):
                continue
            candidates = resolve_local_candidates(file_path, target, root)
            if any(c.exists() for c in candidates):
                continue
            resolved = candidates[0]
            try:
                rel_file = str(file_path.relative_to(root))
            except ValueError:
                rel_file = str(file_path)
            try:
                rel_resolved = str(resolved.relative_to(root))
            except ValueError:
                rel_resolved = str(resolved)
            broken.append(
                {
                    "file": rel_file,
                    "line": lineno,
                    "col": col,
                    "target": target,
                    "resolved": rel_resolved,
                }
            )
    return broken


def collect_files(root: Path, globs: Sequence[str]) -> List[Path]:
    seen: dict = {}
    for pattern in globs:
        for p in root.glob(pattern):
            if p.is_file() and p.suffix == ".md":
                if _is_fixture_path(p.relative_to(root) if p.is_absolute() else p):
                    continue
                seen[p.resolve()] = p
    return sorted(seen.values())


# ---------- main ----------------------------------------------------------


def main(argv: Optional[Sequence[str]] = None) -> int:
    """CLI entrypoint — flag docs stale relative to their cited source paths."""
    parser = argparse.ArgumentParser(
        description="Scan markdown docs for broken relative links (PLAN-010 Phase 3).",
    )
    parser.add_argument(
        "--root",
        type=Path,
        default=None,
        help="Repo root (default: nearest ancestor with a .git dir; else cwd).",
    )
    parser.add_argument(
        "--allowlist",
        type=Path,
        default=None,
        help="Path to allowlist file (default: <root>/docs/docs-freshness-allowlist.txt).",
    )
    parser.add_argument(
        "--format",
        choices=("text", "json"),
        default="text",
    )
    parser.add_argument(
        "--glob",
        action="append",
        default=None,
        help="Override default glob patterns (repeatable). "
        "If omitted, uses the standard doc surface.",
    )
    parser.add_argument(
        "--files",
        nargs="*",
        default=None,
        help="Scan exactly these files (relative to --root). Overrides --glob.",
    )
    try:
        args = parser.parse_args(argv)
    except SystemExit as e:
        return int(e.code) if isinstance(e.code, int) else 2

    root = (args.root or _find_repo_root(Path.cwd())).resolve()
    if not root.is_dir():
        print(f"error: --root is not a directory: {root}", file=sys.stderr)
        return 2

    allowlist_path = args.allowlist or (root / "docs" / "docs-freshness-allowlist.txt")
    allowlist = load_allowlist(allowlist_path if allowlist_path.exists() else None)

    if args.files:
        files = [(root / f).resolve() for f in args.files]
        files = [f for f in files if f.is_file()]
    else:
        globs = tuple(args.glob) if args.glob else DEFAULT_GLOBS
        files = collect_files(root, globs)

    all_broken: List[dict] = []
    for f in files:
        all_broken.extend(scan_file(f, root, allowlist))

    if args.format == "json":
        payload = {
            "scanned_files": len(files),
            "broken_count": len(all_broken),
            "broken": all_broken,
        }
        print(json.dumps(payload, indent=2, sort_keys=True))
    else:
        if not all_broken:
            print(f"OK: scanned {len(files)} file(s), 0 broken refs.")
        else:
            print(
                f"FOUND {len(all_broken)} broken ref(s) across "
                f"{len(files)} scanned file(s):"
            )
            for b in all_broken:
                print(
                    f"  {b['file']}:{b['line']}:{b['col']}  "
                    f"target={b['target']!r}  resolved={b['resolved']}"
                )
            print("")
            print("Hint: if a ref is intentional (future file, archival),")
            print("add it to docs/docs-freshness-allowlist.txt.")

    return 1 if all_broken else 0


def _find_repo_root(start: Path) -> Path:
    cur = start.resolve()
    while True:
        if (cur / ".git").exists():
            return cur
        if cur.parent == cur:
            return start.resolve()
        cur = cur.parent


if __name__ == "__main__":
    sys.exit(main())
