"""
check-creative-rewrite.py — Mechanical drop policy enforcement (ADJ-B2)

Rules:
  3a — flag if >=N consecutive whitespace-tokenized words match between
       target SKILL.md and any upstream agency-agents .md file.
  3b — flag if any H2 section's content SHA matches an upstream H2 SHA
       (structural fingerprint).

Scan modes:
  DEFAULT (full-corpus): checks target against ALL .md files in the upstream
    corpus.  This is the safe default — it catches copies even when the
    inspired_by: frontmatter cites a different file than the one actually
    copied from.

  --narrow-to-inspired (advisory): restricts the scan to the upstream files
    listed in the target's inspired_by: frontmatter.  Faster but UNSAFE:
    a skill that cites one benign upstream file while copying prose from a
    DIFFERENT upstream file will evade detection.  Use only for advisory /
    diagnostic purposes; never as a gate.

Exit codes:
  0 — no findings (drop policy not triggered)
  1 — one or more findings (drop policy triggered)
  2 — usage / environment error (missing archive/dir, bad inputs)
"""
from __future__ import annotations

import argparse
import hashlib
import io
import os
import re
import subprocess
import sys
import tarfile
from pathlib import Path
from typing import Optional

# ---------------------------------------------------------------------------
# Frontmatter helpers
# ---------------------------------------------------------------------------

_FRONTMATTER_RE = re.compile(r"\A---\s*\n(.*?)\n---\s*\n", re.DOTALL)
_INSPIRED_BY_SOURCE_RE = re.compile(
    r"^\s*-?\s*source:\s*(.+)$", re.MULTILINE
)


def extract_frontmatter(text: str) -> tuple[str, str]:
    """Return (frontmatter_block, body_without_frontmatter)."""
    m = _FRONTMATTER_RE.match(text)
    if m:
        return m.group(1), text[m.end():]
    return "", text


def parse_inspired_by_sources(frontmatter: str) -> list[str]:
    """
    Extract all `source:` values from the inspired_by YAML block.

    Handles both scalar and list forms:
      inspired_by:
        source: owner/repo/path@sha   # scalar
      inspired_by:
        - source: owner/repo/path@sha # list entry
    """
    return [m.group(1).strip() for m in _INSPIRED_BY_SOURCE_RE.finditer(frontmatter)]


def source_to_upstream_path(source: str) -> Optional[str]:
    """
    Convert `owner/repo/path@sha` (or `owner/repo/path`) to a relative path
    within the upstream archive/dir.

    Examples
    --------
    msitarzewski/agency-agents/engineering/backend.md@783f6a72
      -> engineering/backend.md
    msitarzewski/agency-agents/strategy/nexus.md
      -> strategy/nexus.md
    """
    # Strip @sha suffix
    source = source.split("@")[0].strip()
    parts = source.split("/")
    # Convention: first two segments are owner/repo; remainder is the path
    if len(parts) > 2:
        return "/".join(parts[2:])
    return None


# ---------------------------------------------------------------------------
# Text normalisation
# ---------------------------------------------------------------------------

_CODE_BLOCK_RE = re.compile(r"```.*?```", re.DOTALL)
_INLINE_CODE_RE = re.compile(r"`[^`\n]+`")
_URL_RE = re.compile(r"https?://\S+")
_H2_SPLIT_RE = re.compile(r"(?m)^## ")


def strip_noise(text: str) -> str:
    """Remove fenced code blocks, inline code, and URLs to reduce false positives."""
    text = _CODE_BLOCK_RE.sub(" ", text)
    text = _INLINE_CODE_RE.sub(" ", text)
    text = _URL_RE.sub(" ", text)
    return text


def tokenize(text: str) -> list[str]:
    """Lowercase, whitespace-split, filter empty tokens."""
    return [t.lower() for t in text.split() if t]


def split_h2_sections(body: str) -> dict[str, str]:
    """
    Return a dict mapping H2 header text → section body (content after the
    header line, before the next H2 or EOF).

    Sections that start with `### ` are not split here; only `## ` splits.
    """
    parts = _H2_SPLIT_RE.split(body)
    result: dict[str, str] = {}
    for part in parts[1:]:  # first element is pre-first-H2 content
        lines = part.split("\n", 1)
        header = lines[0].strip()
        content = lines[1] if len(lines) > 1 else ""
        result[header] = content
    return result


def h2_section_sha(content: str) -> str:
    """SHA-256 of the section content (stripped + lowercased)."""
    normalised = content.strip().lower()
    return hashlib.sha256(normalised.encode()).hexdigest()


# ---------------------------------------------------------------------------
# N-gram set building (hash-based for O(1) lookup)
# ---------------------------------------------------------------------------

def build_ngram_set(tokens: list[str], n: int) -> set[tuple[str, ...]]:
    """Return the set of all n-grams (as tuples) from a token list."""
    if len(tokens) < n:
        return set()
    return {tuple(tokens[i : i + n]) for i in range(len(tokens) - n + 1)}


def build_ngram_list(tokens: list[str], n: int) -> list[tuple[int, tuple[str, ...]]]:
    """
    Return a list of (start_index, ngram_tuple) for each position.
    Used when we need the position of a match in the target.
    """
    return [
        (i, tuple(tokens[i : i + n]))
        for i in range(max(0, len(tokens) - n + 1))
    ]


# ---------------------------------------------------------------------------
# Upstream corpus loading
# ---------------------------------------------------------------------------

def load_upstream_from_dir(upstream_dir: Path) -> dict[str, str]:
    """Return {relative_path: text} for all .md files under upstream_dir."""
    corpus: dict[str, str] = {}
    for root, _dirs, files in os.walk(upstream_dir):
        for fname in files:
            if fname.endswith(".md"):
                full = Path(root) / fname
                rel = str(full.relative_to(upstream_dir))
                try:
                    corpus[rel] = full.read_text(encoding="utf-8", errors="replace")
                except OSError:
                    pass
    return corpus


def load_upstream_from_archive(archive_path: Path) -> dict[str, str]:
    """
    Return {relative_path: text} for all .md files in a .tar.zst archive.

    stdlib tarfile does NOT support zstd before Python 3.14, so we decompress
    via the `zstd` CLI tool and pipe to tarfile.open(fileobj=...).
    """
    zstd_bin = _find_zstd()
    if zstd_bin is None:
        print(
            "ERROR: 'zstd' binary not found in PATH. "
            "Install zstd (e.g. `brew install zstd` or `apt install zstd`) "
            "to read .tar.zst archives.",
            file=sys.stderr,
        )
        sys.exit(2)

    try:
        result = subprocess.run(
            [zstd_bin, "-d", "-c", str(archive_path)],
            capture_output=True,
            timeout=60,
        )
    except subprocess.TimeoutExpired:
        print("ERROR: zstd decompression timed out (>60s).", file=sys.stderr)
        sys.exit(2)

    if result.returncode != 0:
        print(
            f"ERROR: zstd failed (exit {result.returncode}): "
            f"{result.stderr.decode(errors='replace')[:500]}",
            file=sys.stderr,
        )
        sys.exit(2)

    corpus: dict[str, str] = {}
    with tarfile.open(fileobj=io.BytesIO(result.stdout), mode="r:") as tf:
        for member in tf.getmembers():
            if member.name.endswith(".md") and member.isfile():
                f = tf.extractfile(member)
                if f is not None:
                    # Strip leading component (top-level archive dir, if any)
                    rel = _strip_archive_prefix(member.name)
                    corpus[rel] = f.read().decode("utf-8", errors="replace")
    return corpus


def _find_zstd() -> Optional[str]:
    """Locate the zstd binary in PATH."""
    import shutil
    return shutil.which("zstd")


def _strip_archive_prefix(path: str) -> str:
    """
    Remove the first path component from an archive member path so that
    `agency-agents-783f6a72/engineering/foo.md` → `engineering/foo.md`.
    """
    parts = path.split("/", 1)
    return parts[1] if len(parts) == 2 else path


# ---------------------------------------------------------------------------
# Core matching logic (pure functions — testable independently)
# ---------------------------------------------------------------------------

def check_rule_3a(
    target_tokens: list[str],
    upstream_ngram_sets: dict[str, set[tuple[str, ...]]],
    n: int,
) -> list[tuple[str, int, str]]:
    """
    Rule 3a: sliding window of N words.

    Returns list of (upstream_path, target_start_index, matched_phrase).
    """
    findings: list[tuple[str, int, str]] = []
    target_ngrams = build_ngram_list(target_tokens, n)
    if not target_ngrams:
        return findings

    for up_path, up_ngram_set in upstream_ngram_sets.items():
        for start_idx, ngram in target_ngrams:
            if ngram in up_ngram_set:
                findings.append((up_path, start_idx, " ".join(ngram)))
    return findings


def check_rule_3b(
    target_sections: dict[str, str],
    upstream_h2_sha_index: dict[str, list[str]],
) -> list[tuple[str, str, str]]:
    """
    Rule 3b: H2 section content SHA fingerprint.

    upstream_h2_sha_index maps sha256 → list[upstream_path:header] for lookup.

    Returns list of (target_header, upstream_path, upstream_header).
    """
    findings: list[tuple[str, str, str]] = []
    for header, content in target_sections.items():
        sha = h2_section_sha(content)
        if sha in upstream_h2_sha_index:
            for location in upstream_h2_sha_index[sha]:
                findings.append((header, location, sha[:16]))
    return findings


# ---------------------------------------------------------------------------
# Index builders
# ---------------------------------------------------------------------------

def build_upstream_ngram_sets(
    corpus: dict[str, str],
    n: int,
    narrow_paths: Optional[set[str]] = None,
) -> dict[str, set[tuple[str, ...]]]:
    """
    Build per-upstream-file ngram sets.

    If narrow_paths is given (a set of relative paths), only index those
    upstream files (advisory/narrow mode).  When None, ALL files in the
    corpus are indexed (full-corpus mode — the safe default).

    Returns {upstream_relative_path: ngram_set}.
    """
    result: dict[str, set[tuple[str, ...]]] = {}
    for rel_path, text in corpus.items():
        if narrow_paths is not None and rel_path not in narrow_paths:
            continue
        _, body = extract_frontmatter(text)
        body_clean = strip_noise(body)
        tokens = tokenize(body_clean)
        ngrams = build_ngram_set(tokens, n)
        if ngrams:
            result[rel_path] = ngrams
    return result


def build_upstream_h2_sha_index(
    corpus: dict[str, str],
    narrow_paths: Optional[set[str]] = None,
) -> dict[str, list[str]]:
    """
    Build SHA → list[upstream_path:header] lookup across corpus.

    If narrow_paths is given, only index those upstream files.
    When None, ALL files are indexed (full-corpus mode — the safe default).
    """
    index: dict[str, list[str]] = {}
    for rel_path, text in corpus.items():
        if narrow_paths is not None and rel_path not in narrow_paths:
            continue
        _, body = extract_frontmatter(text)
        sections = split_h2_sections(body)
        for header, content in sections.items():
            if not content.strip():
                continue
            sha = h2_section_sha(content)
            entry = f"{rel_path}:{header}"
            index.setdefault(sha, []).append(entry)
    return index


# ---------------------------------------------------------------------------
# Deduplication: collapse overlapping 3a windows
# ---------------------------------------------------------------------------

def deduplicate_3a_findings(
    findings: list[tuple[str, int, str]],
    n: int,
) -> list[tuple[str, int, str]]:
    """
    Many overlapping windows will fire for a single long match. Deduplicate
    by grouping by upstream path and merging start indices that are within
    n tokens of each other, keeping only the earliest occurrence per group.
    """
    # Group by upstream path
    by_path: dict[str, list[tuple[int, str]]] = {}
    for up_path, start, phrase in findings:
        by_path.setdefault(up_path, []).append((start, phrase))

    deduped: list[tuple[str, int, str]] = []
    for up_path, positions in by_path.items():
        positions_sorted = sorted(positions, key=lambda x: x[0])
        last_end = -1
        for start, phrase in positions_sorted:
            if start >= last_end:
                deduped.append((up_path, start, phrase))
                last_end = start + n
    return deduped


# ---------------------------------------------------------------------------
# Output formatting
# ---------------------------------------------------------------------------

def format_3a_finding(
    target_path: str,
    start_idx: int,
    up_path: str,
    phrase: str,
) -> str:
    return (
        f"DROP-3A-WORD-MATCH: {target_path}:token[{start_idx}]: "
        f"{up_path}: "
        f"{len(phrase.split())}-word match: «{phrase[:80]}{'...' if len(phrase) > 80 else ''}»"
    )


def format_3b_finding(
    target_path: str,
    target_header: str,
    upstream_location: str,
    sha_prefix: str,
) -> str:
    return (
        f"DROP-3B-H2-SHA-MATCH: {target_path}:## {target_header}: "
        f"{upstream_location}: "
        f"content sha256={sha_prefix}..."
    )


# ---------------------------------------------------------------------------
# Main entrypoint
# ---------------------------------------------------------------------------

def parse_args() -> argparse.Namespace:
    p = argparse.ArgumentParser(
        description=(
            "Mechanical drop policy check (ADJ-B2): "
            "detect near-verbatim copy from upstream agency-agents.\n\n"
            "DEFAULT mode scans target against ALL upstream .md files "
            "(full-corpus, safe for gate use).  Use --narrow-to-inspired "
            "for a faster advisory scan restricted to inspired_by: citations "
            "only — UNSAFE as a gate (see --narrow-to-inspired help)."
        )
    )
    p.add_argument("--target", required=True, help="SKILL.md file to check")
    p.add_argument(
        "--upstream-archive",
        default=None,
        help="Path to agency-agents-archive-783f6a72.tar.zst",
    )
    p.add_argument(
        "--upstream-dir",
        default=None,
        help="Path to upstream repo directory tree (preferred for dev/testing)",
    )
    p.add_argument(
        "--threshold-words",
        type=int,
        default=12,
        help="Rule 3a: consecutive-word match threshold (default: 12)",
    )
    p.add_argument(
        "--narrow-to-inspired",
        action="store_true",
        default=False,
        help=(
            "ADVISORY MODE — restrict scan to upstream files listed in the "
            "target's inspired_by: frontmatter.  Faster but UNSAFE as a gate: "
            "a skill that cites one benign upstream file while copying prose "
            "from a DIFFERENT upstream file will evade detection in this mode. "
            "When this flag is absent (default), all upstream files are scanned."
        ),
    )
    p.add_argument(
        "--quiet",
        action="store_true",
        help="Suppress summary line; only print findings",
    )
    p.add_argument(
        "--summary",
        action="store_true",
        help="Print only the summary line, suppress per-finding output",
    )
    return p.parse_args()


def main() -> int:  # noqa: C901
    args = parse_args()
    target_path = Path(args.target)

    # --- Validate target ---
    if not target_path.exists():
        print(f"ERROR: target not found: {target_path}", file=sys.stderr)
        return 2

    target_text = target_path.read_text(encoding="utf-8", errors="replace")
    frontmatter, body = extract_frontmatter(target_text)

    # --- Resolve upstream corpus ---
    upstream_dir = Path(args.upstream_dir) if args.upstream_dir else None
    upstream_archive = Path(args.upstream_archive) if args.upstream_archive else None

    corpus: dict[str, str]
    if upstream_dir is not None and upstream_dir.is_dir():
        corpus = load_upstream_from_dir(upstream_dir)
    elif upstream_archive is not None and upstream_archive.exists():
        corpus = load_upstream_from_archive(upstream_archive)
    else:
        msg_parts = []
        if upstream_dir is not None:
            msg_parts.append(
                f"--upstream-dir '{upstream_dir}' does not exist or is not a directory"
            )
        if upstream_archive is not None:
            msg_parts.append(
                f"--upstream-archive '{upstream_archive}' does not exist"
            )
        if not msg_parts:
            msg_parts.append(
                "No upstream source provided. "
                "Supply --upstream-dir <path> or --upstream-archive <path>."
            )
        print("ERROR: " + "; ".join(msg_parts), file=sys.stderr)
        return 2

    if not corpus:
        print(
            "WARNING: upstream corpus is empty — no .md files found. "
            "Proceeding with zero upstream content (no findings possible).",
            file=sys.stderr,
        )

    # --- Determine narrow_paths set (only used when --narrow-to-inspired) ---
    sources = parse_inspired_by_sources(frontmatter)
    narrow_paths: Optional[set[str]] = None

    if args.narrow_to_inspired:
        # Advisory narrow mode: scan only the inspired_by: cited upstream files.
        # All cited sources are resolved; missing ones are warned but not fatal.
        if not sources:
            print(
                "NOTE: --narrow-to-inspired set but target has no inspired_by: sources. "
                "Falling back to full-corpus scan.",
                file=sys.stderr,
            )
        else:
            resolved: set[str] = set()
            for src in sources:
                candidate = source_to_upstream_path(src)
                if candidate and candidate in corpus:
                    resolved.add(candidate)
                elif candidate:
                    print(
                        f"NOTE: inspired_by source '{src}' resolved to '{candidate}' "
                        "but not found in upstream corpus — skipped.",
                        file=sys.stderr,
                    )
                else:
                    print(
                        f"NOTE: inspired_by source '{src}' could not be resolved "
                        "to an upstream path — skipped.",
                        file=sys.stderr,
                    )
            if resolved:
                narrow_paths = resolved
            else:
                print(
                    "NOTE: no inspired_by: sources could be resolved in corpus. "
                    "Falling back to full-corpus scan.",
                    file=sys.stderr,
                )
        # Emit advisory bypass warning so callers understand the risk.
        print(
            "NOTE: running in advisory narrow mode (--narrow-to-inspired). "
            "This mode only scans cited upstream files and WILL MISS copies "
            "from un-cited upstream files. Do not use as a gate.",
            file=sys.stderr,
        )
    # When --narrow-to-inspired is absent: narrow_paths stays None → full-corpus scan.

    # --- Build upstream indexes ---
    n = args.threshold_words
    upstream_ngram_sets = build_upstream_ngram_sets(corpus, n, narrow_paths)
    upstream_h2_sha_index = build_upstream_h2_sha_index(corpus, narrow_paths)

    # --- Prepare target content ---
    body_clean = strip_noise(body)
    target_tokens = tokenize(body_clean)
    target_sections = split_h2_sections(body)

    # --- Rule 3a ---
    raw_3a = check_rule_3a(target_tokens, upstream_ngram_sets, n)
    deduped_3a = deduplicate_3a_findings(raw_3a, n)

    # --- Rule 3b ---
    raw_3b = check_rule_3b(target_sections, upstream_h2_sha_index)

    # --- Output ---
    total_findings = len(deduped_3a) + len(raw_3b)

    if not args.summary:
        for up_path, start_idx, phrase in deduped_3a:
            print(format_3a_finding(str(target_path), start_idx, up_path, phrase))
        for tgt_header, up_location, sha_prefix in raw_3b:
            print(format_3b_finding(str(target_path), tgt_header, up_location, sha_prefix))

    if not args.quiet:
        scan_mode = "narrow-to-inspired (advisory)" if args.narrow_to_inspired else "full-corpus"
        print(
            f"SUMMARY: scan_mode={scan_mode} "
            f"target_tokens={len(target_tokens)} "
            f"target_h2_sections={len(target_sections)} "
            f"upstream_files_indexed={len(upstream_ngram_sets)} "
            f"matched_windows_3a={len(deduped_3a)} "
            f"matched_h2s_3b={len(raw_3b)} "
            f"total_findings={total_findings} "
            f"drop_policy_triggered={'YES' if total_findings > 0 else 'NO'}"
        )

    return 1 if total_findings > 0 else 0


if __name__ == "__main__":
    sys.exit(main())
