from __future__ import annotations

import argparse
import os
import re
import sys
from dataclasses import dataclass, field
from pathlib import Path
from typing import Iterator, List, Optional, Tuple

try:
    import yaml as _yaml  # best-effort; dev/CI dep, NOT shipped (stdlib-only contract)
except Exception:  # pragma: no cover - PyYAML absent in bare adopter env
    _yaml = None

_NAME_PATTERN_RE = re.compile(r"^[a-z][a-z0-9-]*$")

SKILLS_ROOT = Path(__file__).parent.parent / "skills"

SEVERITY_ERROR = "ERROR"
SEVERITY_WARN = "WARN"
SEVERITY_INFO = "INFO"

GENERIC_DESCRIPTION_PATTERNS = [
    re.compile(r"^\s*expert\s+in\b", re.IGNORECASE),
    re.compile(r"^\s*specialist\s+in\b", re.IGNORECASE),
]

ISO_DATE_RE = re.compile(r"^\d{4}-\d{2}-\d{2}$")
SHA40_RE = re.compile(r"^[0-9a-f]{40}$", re.IGNORECASE)
SOURCE_RE = re.compile(r"^.+@[0-9a-f]{40}$", re.IGNORECASE)

VALID_RELATIONSHIPS = {
    "structural_inspiration",
    "partial_reuse",
    "topic_only",
    "deliverable_template",
    "severity_scale",
    "convention",
    "pattern_reference",
}
VALID_PII_HANDLING = {"required", "optional", "none"}
VALID_DROP_CATEGORIES = {"voice", "quality", "security", "governance", "license"}
VALID_INHERITS_PREFIXES = ("core/", "frontend/", "domains/")
# PLAN-135 W3 K1: context: execution-context enum. `fork` = run the skill in a
# forked (isolated) context — used for heavy analytic skills so they do not
# pollute the main window; `main` = explicit default (inline in the invoking
# context). Absence of the field == `main`.
VALID_CONTEXT_VALUES = {"fork", "main"}

CANONICAL_H2_WARN_SET = {
    "quando aplicar",
    "when to apply",
    "anti-patterns",
    "examples",
    "correct vs wrong",
}


@dataclass
class Finding:
    severity: str
    path: str
    line: int
    rule_id: str
    message: str

    def format(self) -> str:
        return f"{self.severity}: {self.path}:{self.line}: {self.rule_id} {self.message}"


def _parse_frontmatter(lines: List[str]) -> Tuple[Optional[dict], int, List[Tuple[int, str]]]:
    """Return (kv_dict, body_start_line, parse_errors).

    body_start_line is the 1-based line number of the first body line.
    kv_dict contains only scalar/multi-line string values from YAML-like
    frontmatter (single-level keys only — sufficient for our rules).
    parse_errors is a list of (line_no, message) for structural anomalies.
    """
    errors: List[Tuple[int, str]] = []
    if not lines or lines[0].rstrip() != "---":
        return None, 1, [("missing frontmatter opening ---")]

    end = None
    for i, ln in enumerate(lines[1:], start=1):
        if ln.rstrip() == "---":
            end = i
            break
    if end is None:
        return None, 1, [(1, "unclosed frontmatter (no closing ---)")]

    kv: dict = {}
    current_key: Optional[str] = None
    current_val_lines: List[str] = []
    in_multiline = False

    for i in range(1, end):
        raw = lines[i]
        stripped = raw.strip()
        if not stripped or stripped.startswith("#"):
            continue

        indent = len(raw) - len(raw.lstrip())

        if indent == 0:
            if in_multiline and current_key is not None:
                kv[current_key] = " ".join(current_val_lines).strip()
                current_val_lines = []
                in_multiline = False
                current_key = None

            if ":" in stripped:
                key, _, rest = stripped.partition(":")
                key = key.strip()
                rest = rest.strip()
                if rest == "" or rest == "|" or rest == ">":
                    current_key = key
                    in_multiline = True
                    current_val_lines = []
                elif rest.startswith("["):
                    kv[key] = rest
                else:
                    kv[key] = rest
                    current_key = None
        else:
            if in_multiline and current_key is not None:
                current_val_lines.append(stripped)

    if in_multiline and current_key is not None:
        kv[current_key] = " ".join(current_val_lines).strip()

    body_start = end + 2  # 1-based
    return kv, body_start, errors


def _extract_inspired_by_entries(lines: List[str], fm_end_line: int) -> List[Tuple[int, dict]]:
    """Parse all inspired_by list entries from raw frontmatter lines."""
    entries: List[Tuple[int, dict]] = []
    in_inspired = False
    current: Optional[dict] = None
    current_line = 0

    for i, raw in enumerate(lines[1:fm_end_line], start=2):
        stripped = raw.strip()
        if stripped.startswith("inspired_by:"):
            in_inspired = True
            continue
        if in_inspired:
            indent = len(raw) - len(raw.lstrip())
            if indent == 0 and stripped and not stripped.startswith("-"):
                break
            if stripped.startswith("-"):
                if current is not None:
                    entries.append((current_line, current))
                current = {}
                current_line = i
                rest = stripped[1:].strip()
                if rest and ":" in rest:
                    k, _, v = rest.partition(":")
                    current[k.strip()] = v.strip()
            elif current is not None and ":" in stripped:
                k, _, v = stripped.partition(":")
                current[k.strip()] = v.strip()

    if current is not None:
        entries.append((current_line, current))
    return entries


def _strip_quotes(s: str) -> str:
    s = s.strip()
    if len(s) >= 2 and s[0] == s[-1] and s[0] in ("'", '"'):
        return s[1:-1]
    return s


def _extract_list_field(
    lines: List[str], fm_end_line: int, key: str
) -> Tuple[bool, int, List[Tuple[int, Optional[str]]], Optional[str]]:
    """Locate a top-level `<key>:` inside the raw frontmatter lines.

    Returns (present, key_line, items, scalar_value):
      present      — True if the key appears at indent 0 inside frontmatter
      key_line     — 1-based line number of the key (0 if absent)
      items        — [(line_no, raw_entry_or_None), ...] from an inline
                     `[a, b]` list or an indented `- item` block sequence;
                     None marks a structurally non-scalar entry
      scalar_value — raw scalar text when the value is neither list form

    Stdlib-only fallback parser (PLAN-135 W3 K1). When PyYAML is available the
    strict parse is the validation oracle; this supplies line numbers and the
    bare-adopter-env fallback (same best-effort posture as LINT-FM-04/05).
    """
    present = False
    key_line = 0
    items: List[Tuple[int, Optional[str]]] = []
    scalar_value: Optional[str] = None

    i = 1
    while i < fm_end_line:
        raw = lines[i]
        stripped = raw.strip()
        line_no = i + 1
        if stripped and not stripped.startswith("#") and (len(raw) - len(raw.lstrip())) == 0:
            k, sep, rest = stripped.partition(":")
            if sep and k.strip() == key:
                present = True
                key_line = line_no
                rest = rest.strip()
                if rest.startswith("["):
                    if rest.endswith("]"):
                        inner = rest[1:-1].strip()
                        if inner:
                            for part in inner.split(","):
                                items.append((line_no, part.strip()))
                    else:
                        scalar_value = rest  # malformed inline list -> scalar
                elif rest in ("", "|", ">"):
                    j = i + 1
                    while j < fm_end_line:
                        nraw = lines[j]
                        nstripped = nraw.strip()
                        if not nstripped or nstripped.startswith("#"):
                            j += 1
                            continue
                        nindent = len(nraw) - len(nraw.lstrip())
                        if nindent == 0:
                            break
                        if nstripped == "-":
                            items.append((j + 1, None))
                        elif nstripped.startswith("- "):
                            items.append((j + 1, nstripped[2:].strip()))
                        elif not items:
                            # indented non-list content: block scalar value
                            scalar_value = ((scalar_value + " ") if scalar_value else "") + nstripped
                        else:
                            # nested content under a list entry -> non-scalar
                            items[-1] = (items[-1][0], None)
                        j += 1
                else:
                    scalar_value = rest
                break
        i += 1
    return present, key_line, items, scalar_value


def lint_file(path: Path, quiet: bool = False, max_description: int = 1024,
              strict_yaml: bool = False,
              only_rules: Optional[frozenset] = None) -> List[Finding]:
    findings: List[Finding] = []

    def add(severity: str, line: int, rule_id: str, message: str) -> None:
        if only_rules is not None and rule_id not in only_rules:
            return
        if quiet and severity != SEVERITY_ERROR:
            return
        findings.append(Finding(severity, str(path), line, rule_id, message))

    try:
        text = path.read_text(encoding="utf-8", errors="replace")
    except OSError as exc:
        findings.append(Finding(SEVERITY_ERROR, str(path), 0, "LINT-IO-01", str(exc)))
        return findings

    lines = text.splitlines(keepends=True)
    lines_stripped = [ln.rstrip("\n") for ln in lines]

    fm, body_start, fm_errors = _parse_frontmatter(lines_stripped)

    for err in fm_errors:
        if isinstance(err, tuple):
            add(SEVERITY_ERROR, err[0], "LINT-FM-00", err[1])
        else:
            add(SEVERITY_ERROR, 1, "LINT-FM-00", str(err))

    if fm is None:
        return findings

    fm_end_line = body_start - 2  # index of closing ---

    # PLAN-117 WS-C: authoritative strict-YAML parse (best-effort PyYAML — dev/CI
    # dep, NOT shipped; no-ops in bare stdlib-only adopter envs). When available it
    # is the oracle for BOTH frontmatter validity (LINT-FM-05) and description
    # length (LINT-FM-04): the lenient kv-parser under-measures plain multi-line
    # scalars (captures only the first line).
    fm_text = "\n".join(lines_stripped[1:fm_end_line])
    yaml_err = None
    parsed_description: Optional[str] = None
    parsed_fm: Optional[dict] = None  # PLAN-135 W3 K1: strict-parse oracle for FM-40/41
    if _yaml is not None:
        try:
            parsed = _yaml.safe_load(fm_text)
            if isinstance(parsed, dict):
                parsed_fm = parsed
                if isinstance(parsed.get("description"), str):
                    parsed_description = parsed["description"]
        except _yaml.YAMLError as exc:  # type: ignore[union-attr]
            yaml_err = exc

    if strict_yaml and yaml_err is not None:
        _first = str(yaml_err).splitlines()[0] if str(yaml_err) else yaml_err.__class__.__name__
        add(SEVERITY_ERROR, 1, "LINT-FM-05",
            f"frontmatter is not valid YAML under a strict loader: {_first}")

    description = fm.get("description", "")
    if not description:
        add(SEVERITY_ERROR, 1, "LINT-FM-01", "frontmatter missing 'description:' key")
    else:
        if len(description) < 50:
            add(SEVERITY_ERROR, 1, "LINT-FM-02",
                f"description too short ({len(description)} chars, min 50)")
        _desc_len = len(parsed_description) if parsed_description is not None else len(description)
        if _desc_len > max_description:
            add(SEVERITY_ERROR, 1, "LINT-FM-04",
                f"description too long ({_desc_len} chars, max {max_description})")
        for pat in GENERIC_DESCRIPTION_PATTERNS:
            if pat.match(description):
                add(SEVERITY_ERROR, 1, "LINT-FM-03",
                    "description is generic ('expert in X' / 'specialist in Y')")
                break

    # LINT-FM-00b: name: field — required, non-empty, should be lowercase-hyphen
    skill_name = fm.get("name", "")
    if not skill_name:
        add(SEVERITY_ERROR, 1, "LINT-FM-00b",
            "frontmatter missing required 'name:' key (must be a non-empty string)")
    elif not _NAME_PATTERN_RE.match(skill_name):
        add(SEVERITY_WARN, 1, "LINT-FM-00b",
            f"name {skill_name!r} should match [a-z][a-z0-9-]* (lowercase, hyphens only)")

    if "inspired_by" in fm:
        entries = _extract_inspired_by_entries(lines_stripped, fm_end_line)
        if not entries:
            add(SEVERITY_ERROR, 1, "LINT-FM-10",
                "inspired_by: present but no list entries found")
        for entry_line, entry in entries:
            source = entry.get("source", "")
            if not source:
                add(SEVERITY_ERROR, entry_line, "LINT-FM-11",
                    "inspired_by entry missing 'source:'")
            elif not SOURCE_RE.match(source):
                add(SEVERITY_ERROR, entry_line, "LINT-FM-12",
                    f"inspired_by source must end with '@<40-hex-sha>': {source!r}")

            if not entry.get("license", ""):
                add(SEVERITY_ERROR, entry_line, "LINT-FM-13",
                    "inspired_by entry missing 'license:'")

            relationship = entry.get("relationship", "")
            if not relationship:
                add(SEVERITY_ERROR, entry_line, "LINT-FM-14",
                    "inspired_by entry missing 'relationship:'")
            elif relationship not in VALID_RELATIONSHIPS:
                add(SEVERITY_ERROR, entry_line, "LINT-FM-15",
                    f"inspired_by relationship {relationship!r} not in "
                    f"{sorted(VALID_RELATIONSHIPS)}")

            if not entry.get("authored_by", ""):
                add(SEVERITY_ERROR, entry_line, "LINT-FM-16",
                    "inspired_by entry missing 'authored_by:'")

            authored_at = entry.get("authored_at", "")
            if not authored_at:
                add(SEVERITY_ERROR, entry_line, "LINT-FM-17",
                    "inspired_by entry missing 'authored_at:'")
            elif not ISO_DATE_RE.match(authored_at):
                add(SEVERITY_ERROR, entry_line, "LINT-FM-18",
                    f"authored_at must be ISO YYYY-MM-DD, got: {authored_at!r}")

    inherits = fm.get("inherits", "")
    if inherits:
        vals = [v.strip().lstrip("-").strip() for v in inherits.replace("[", "").replace("]", "").split(",")]
        for val in vals:
            if val and not any(val.startswith(p) for p in VALID_INHERITS_PREFIXES):
                add(SEVERITY_ERROR, 1, "LINT-FM-20",
                    f"inherits value {val!r} must start with core/, frontend/, or domains/")

    pii_handling = fm.get("pii_handling", "")
    if pii_handling and pii_handling not in VALID_PII_HANDLING:
        add(SEVERITY_ERROR, 1, "LINT-FM-21",
            f"pii_handling {pii_handling!r} not in {sorted(VALID_PII_HANDLING)}")

    rewritten_at = fm.get("rewritten_at", "")
    if rewritten_at and not ISO_DATE_RE.match(rewritten_at):
        add(SEVERITY_ERROR, 1, "LINT-FM-22",
            f"rewritten_at must be ISO YYYY-MM-DD, got: {rewritten_at!r}")

    dropped_at = fm.get("dropped_at", "")
    if dropped_at:
        drop_category = fm.get("drop_category", "")
        if not drop_category:
            add(SEVERITY_ERROR, 1, "LINT-FM-30",
                "dropped_at present but drop_category: missing")
        elif drop_category not in VALID_DROP_CATEGORIES:
            add(SEVERITY_ERROR, 1, "LINT-FM-31",
                f"drop_category {drop_category!r} not in {sorted(VALID_DROP_CATEGORIES)}")

    # ------------------------------------------------------------------
    # PLAN-135 W3 K1 — optional auto-activation fields.
    # LINT-FM-40: paths: must be a NON-EMPTY YAML list of non-empty glob
    #             strings (auto-activation: the skill announces when a touched
    #             file matches one of the globs via fnmatch).
    # LINT-FM-41: context: must be one of VALID_CONTEXT_VALUES (fork|main).
    # Strict-YAML discipline (PLAN-117 WS-C posture): when PyYAML is available
    # the strict safe_load parse is the validation oracle; the raw extractor
    # is the stdlib fallback for bare adopter envs + supplies line numbers.
    # Both fields are OPTIONAL — absence produces no finding.
    # ------------------------------------------------------------------
    paths_present, paths_line, paths_items, paths_scalar = _extract_list_field(
        lines_stripped, fm_end_line, "paths")
    if parsed_fm is not None and "paths" in parsed_fm:
        _pline = paths_line or 1
        _pval = parsed_fm["paths"]
        if not isinstance(_pval, list):
            add(SEVERITY_ERROR, _pline, "LINT-FM-40",
                f"paths: must be a YAML list of glob strings, got {type(_pval).__name__}")
        elif not _pval:
            add(SEVERITY_ERROR, _pline, "LINT-FM-40",
                "paths: must be a NON-EMPTY list of glob strings")
        else:
            for entry in _pval:
                if not isinstance(entry, str) or not entry.strip():
                    add(SEVERITY_ERROR, _pline, "LINT-FM-40",
                        f"paths: entries must be non-empty glob strings, got {entry!r}")
    elif paths_present:
        if paths_scalar is not None:
            add(SEVERITY_ERROR, paths_line, "LINT-FM-40",
                f"paths: must be a YAML list of glob strings, got scalar {paths_scalar!r}")
        elif not paths_items:
            add(SEVERITY_ERROR, paths_line, "LINT-FM-40",
                "paths: must be a NON-EMPTY list of glob strings")
        else:
            for entry_line, entry in paths_items:
                val = _strip_quotes(entry) if entry is not None else ""
                if entry is None or not val or val.startswith("{") or val.endswith(":"):
                    add(SEVERITY_ERROR, entry_line, "LINT-FM-40",
                        f"paths: entries must be non-empty glob strings, got {entry!r}")

    ctx_present, ctx_line, ctx_items, ctx_scalar = _extract_list_field(
        lines_stripped, fm_end_line, "context")
    ctx_val = None  # type: object
    have_ctx = False
    if parsed_fm is not None and "context" in parsed_fm:
        have_ctx = True
        ctx_val = parsed_fm["context"]
    elif ctx_present:
        have_ctx = True
        if ctx_items:
            ctx_val = [entry for _, entry in ctx_items]  # list form = invalid type
        elif ctx_scalar is not None:
            ctx_val = _strip_quotes(ctx_scalar)
    if have_ctx:
        if not isinstance(ctx_val, str) or ctx_val not in VALID_CONTEXT_VALUES:
            add(SEVERITY_ERROR, ctx_line or 1, "LINT-FM-41",
                f"context {ctx_val!r} not in {sorted(VALID_CONTEXT_VALUES)}")

    body_lines = lines_stripped[body_start - 1:]
    body_text = "\n".join(body_lines)
    body_stripped = body_text.strip()

    if len(body_stripped.encode("utf-8")) < 1024:
        add(SEVERITY_ERROR, body_start, "LINT-STRUCT-01",
            f"body too short ({len(body_stripped.encode('utf-8'))} bytes, min 1024)")

    h2_lines: List[Tuple[int, str]] = []
    for rel_i, ln in enumerate(body_lines):
        if re.match(r"^## ", ln):
            abs_line = body_start + rel_i
            h2_lines.append((abs_line, ln))

    if len(h2_lines) < 2:
        add(SEVERITY_ERROR, body_start, "LINT-STRUCT-02",
            f"body has {len(h2_lines)} H2 section(s), need ≥ 2")

    h2_titles_lower = {re.sub(r"^## ", "", t).strip().lower() for _, t in h2_lines}
    missing_canonical = CANONICAL_H2_WARN_SET - h2_titles_lower
    if missing_canonical:
        add(SEVERITY_WARN, body_start, "LINT-STRUCT-03",
            f"missing recommended H2 section(s): {sorted(missing_canonical)}")

    if not re.search(r"^```", body_text, re.MULTILINE):
        add(SEVERITY_WARN, body_start, "LINT-STRUCT-04",
            "body contains no fenced code block (``` ...)")

    return findings


def collect_skill_files(paths: List[str]) -> Iterator[Path]:
    expanded: List[Path] = []
    if not paths:
        expanded.append(SKILLS_ROOT)
    else:
        expanded = [Path(p) for p in paths]

    for p in expanded:
        if p.is_file():
            yield p
        elif p.is_dir():
            for root, dirs, files in os.walk(p):
                dirs.sort()
                for fname in sorted(files):
                    if fname == "SKILL.md":
                        yield Path(root) / fname
        else:
            print(f"WARN: path not found: {p}", file=sys.stderr)


def main() -> int:
    parser = argparse.ArgumentParser(
        description="Lint SKILL.md files in the ceo-orchestration framework"
    )
    parser.add_argument("paths", nargs="*", help="Files or directories to lint (default: .claude/skills/)")
    parser.add_argument("--quiet", action="store_true", help="Only show ERROR findings")
    parser.add_argument("--summary", action="store_true", help="Print counts at end")
    parser.add_argument("--max-description", type=int, default=1024,
                        help="Max allowed description length in chars (default 1024)")
    parser.add_argument("--strict-yaml", action="store_true",
                        help="Reject frontmatter that fails a strict YAML parse (best-effort PyYAML)")
    parser.add_argument("--only-rules", default=None,
                        help="Comma-separated rule IDs to enforce exclusively (others suppressed)")
    args = parser.parse_args()

    _only_rules = (frozenset(r.strip() for r in args.only_rules.split(",") if r.strip())
                   if args.only_rules else None)
    counts = {SEVERITY_ERROR: 0, SEVERITY_WARN: 0, SEVERITY_INFO: 0}
    has_error = False
    files_checked = 0

    for skill_path in collect_skill_files(args.paths):
        files_checked += 1
        findings = lint_file(skill_path, quiet=args.quiet,
                             max_description=args.max_description,
                             strict_yaml=args.strict_yaml,
                             only_rules=_only_rules)
        for f in findings:
            print(f.format())
            counts[f.severity] = counts.get(f.severity, 0) + 1
            if f.severity == SEVERITY_ERROR:
                has_error = True

    if args.summary:
        total = sum(counts.values())
        print(
            f"\nSummary: {files_checked} file(s) checked — "
            f"{counts[SEVERITY_ERROR]} error(s), "
            f"{counts[SEVERITY_WARN]} warning(s), "
            f"{counts[SEVERITY_INFO]} info — "
            f"{total} finding(s) total"
        )

    return 1 if has_error else 0


if __name__ == "__main__":
    sys.exit(main())
