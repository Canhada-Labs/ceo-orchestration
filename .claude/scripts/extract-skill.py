#!/usr/bin/env python3
"""extract-skill.py — PLAN-065 Phase 1 standalone skill-name extractor.

3-path SKILL extraction matrix (Format-A inline / Format-B reference /
Format-C `## SKILL CONTENT` block fallback) callable as CLI + importable
library. Built as a stand-alone module so the canonical wiring of
`audit_log.py` (which currently uses a single inline regex
`_SKILL_LINE_RE` and returns `unknown` 24/24 times in the live audit-log)
can land via Owner GPG ceremony without coupling the extraction logic
to that file's edit. Tests live at
``.claude/scripts/tests/test_extract_skill.py``.

Acceptance per PLAN-065 §4.1 + R1 adjustments:

- 3-path matrix: per-path fixture deterministically returns the exact
  expected skill string (or ``"unknown"`` for malformed cases).
- Sec MF-7 hardening: NFKC normalize, NUL-strip, length cap 256,
  path-traversal denied, Unicode homoglyph denied, ReDoS-safe.
- ThreadPoolExecutor parallelism via ``extract_many`` for batch use.
- ``--cached`` mode: identity-cached extract result keyed on input SHA-256
  (avoids re-running regex on the same prompt ≥1 time per process).
- Stdlib only. Python 3.9+.

Run as CLI:

    python3 .claude/scripts/extract-skill.py < prompt.txt
    python3 .claude/scripts/extract-skill.py --json < prompt.txt
    python3 .claude/scripts/extract-skill.py --batch prompts.jsonl
    python3 .claude/scripts/extract-skill.py --cached < prompt.txt

Library use::

    from extract_skill import extract_skill, extract_many, Result
    result = extract_skill(prompt_text)
    # result.skill in {"<name>", "unknown"}; result.path in {"a","b","c","none"}
"""
from __future__ import annotations

import argparse
import hashlib
import json
import re
import sys
import time
import unicodedata
from concurrent.futures import ThreadPoolExecutor, TimeoutError as FuturesTimeout
from dataclasses import dataclass
from typing import Dict, Iterable, List, Optional, Tuple

# ---------------------------------------------------------------------------
# Defensive bounds (Sec MF-7 + ReDoS hardening)
# ---------------------------------------------------------------------------

# Cap input at 1 MiB. Plans / prompts beyond this size are extreme outliers;
# rejecting them is preferred over feeding pathological input to the regex
# engine (CPython `re` is NFA but can still spend wall-clock on extreme
# alternation).
MAX_INPUT_BYTES = 1024 * 1024  # 1 MiB hard cap
MAX_INPUT_CHARS = MAX_INPUT_BYTES  # str-len equivalent for code-points

# Skill-name max length. PLAN-065 §4.1 fixture spec calls 256-char cap.
MAX_SKILL_NAME_CHARS = 256

# Per-extraction wall-clock budget. ReDoS defense — if any path takes
# longer than this in a single thread, we abort + return unknown. Bounded
# by ThreadPoolExecutor + future.result(timeout=...) in extract_many.
PER_EXTRACT_TIMEOUT_S = 0.1  # 100 ms (matches PLAN-065 §4.1 spec)

# Allowed skill-name character class (mirror current audit_log.py grammar):
# ``[a-z0-9][a-z0-9\-]*``. Anchored test on the captured group post-extract.
_SKILL_NAME_CHARSET = re.compile(r"^[a-z0-9][a-z0-9\-]*$")

# Path A — Format-A inline (matches current audit_log.py:103-106 grammar
# but line-anchored to avoid matching inside narrative paragraphs).
# Pre-compiled module-load time. Possessive-style alternation kept linear:
# the literal "SKILL: " prefix is anchored to start-of-line (re.MULTILINE),
# the captured group has no nested quantifier, and the upper-bound `{1,256}`
# fully bounds backtracking depth.
_PATH_A_RE = re.compile(
    r"(?m)^SKILL:[ \t]+([a-z0-9][a-z0-9\-]{0,255})\s*$",
)

# Path B — Format-B reference. Mitigated dispatch (ADR-082) + Format-B
# default flip emit:
#   @.claude/skills/core/<name>/SKILL.md sha256=<64-hex>
#   @.claude/skills/frontend/<name>/SKILL.md sha256=<64-hex>
#   @.claude/skills/domains/<domain>/skills/<name>/SKILL.md sha256=<64-hex>
# The captured group is the skill <name> path-segment, not the domain.
_PATH_B_RE = re.compile(
    r"(?m)^@\.claude/skills/"
    r"(?:core|frontend|domains/[a-z0-9][a-z0-9\-]{0,63}/skills)"
    r"/([a-z0-9][a-z0-9\-]{0,255})/SKILL\.md"
    r"\s+sha256=[0-9a-f]{64}\s*$",
)

# Path C — `## SKILL CONTENT` block fallback. Used when neither Format-A
# nor Format-B was emitted (legacy or third-party adapter surface). The
# block heading has a sibling `SKILL LOADED: <name>` annotation that the
# CEO orchestration emits at spawn time.
_PATH_C_RE = re.compile(
    r"(?m)^##[ \t]+SKILL[ \t]+CONTENT\b",
)
_SKILL_LOADED_RE = re.compile(
    r"(?m)^SKILL[ \t]+LOADED:[ \t]+([a-z0-9][a-z0-9\-]{0,255})\s*$",
)

# ---------------------------------------------------------------------------
# Result dataclass
# ---------------------------------------------------------------------------


@dataclass(frozen=True)
class Result:
    """Extraction result.

    - ``skill``: the canonical skill name (e.g. ``"code-review"``) or
      ``"unknown"`` when no path matched / input was rejected.
    - ``path``: which extraction path matched: ``"a"`` / ``"b"`` / ``"c"`` /
      ``"none"``.
    - ``rejected_reason``: short slug if input was rejected pre-regex
      (``"oversize"`` / ``"nul_byte"`` / ``"empty"`` / ``"non_string"``);
      empty string otherwise.
    - ``duration_ms``: wall-clock the extraction took (per-path; advisory
      only — caller may use to spot-check ReDoS attempts).
    """

    skill: str
    path: str
    rejected_reason: str = ""
    duration_ms: float = 0.0


# ---------------------------------------------------------------------------
# Sanitization helpers
# ---------------------------------------------------------------------------


def _sanitize(text: object) -> Tuple[Optional[str], str]:
    """Return ``(safe_text, rejected_reason)``.

    Returns ``(None, "...")`` when input must be rejected. Otherwise
    returns ``(NFKC-normalized + NUL-stripped + length-capped text, "")``.

    Rejections (Sec MF-7):
    - non-string inputs (defense-in-depth on caller)
    - empty / whitespace-only
    - over MAX_INPUT_BYTES UTF-8 / MAX_INPUT_CHARS code-points
    """
    if not isinstance(text, str):
        return None, "non_string"
    if not text or not text.strip():
        return None, "empty"
    # Length pre-check on raw chars (cheaper than NFKC on huge string)
    if len(text) > MAX_INPUT_CHARS:
        return None, "oversize"
    # NFKC normalize first — homoglyph defense (Cyrillic 'о' / 'о' → ASCII 'o').
    # NFKC also folds compat characters; NUL bytes survive NFKC, so strip after.
    normalized = unicodedata.normalize("NFKC", text)
    if "\x00" in normalized:
        # NUL injection denied (per Sec MF-7 fixture spec).
        return None, "nul_byte"
    # Re-check post-NFKC byte length (compat chars may expand).
    if len(normalized.encode("utf-8", errors="replace")) > MAX_INPUT_BYTES:
        return None, "oversize"
    return normalized, ""


def _validate_skill_name(name: str) -> bool:
    """Defense-in-depth: re-validate the captured group anchor + length.

    Even though each path regex bounds the captured group, we re-validate
    here so a future refactor or ReDoS attempt cannot smuggle a
    pathological name out via group-replacement edge case.

    Path-traversal patterns are denied here because the captured group
    grammar already excludes ``/`` and ``..`` — but we add an explicit
    anchor in case the grammar drifts.
    """
    if not name or len(name) > MAX_SKILL_NAME_CHARS:
        return False
    if "/" in name or ".." in name or "\\" in name:
        return False
    if not _SKILL_NAME_CHARSET.match(name):
        return False
    return True


# ---------------------------------------------------------------------------
# Per-path extractors (pure functions, deterministic)
# ---------------------------------------------------------------------------


def _try_path_a(text: str) -> Optional[str]:
    """Format-A inline ``^SKILL: <name>$``."""
    m = _PATH_A_RE.search(text)
    if m and _validate_skill_name(m.group(1)):
        return m.group(1)
    return None


def _try_path_b(text: str) -> Optional[str]:
    """Format-B reference ``^@.claude/skills/.../<name>/SKILL.md sha256=...$``."""
    m = _PATH_B_RE.search(text)
    if m and _validate_skill_name(m.group(1)):
        return m.group(1)
    return None


def _try_path_c(text: str) -> Optional[str]:
    """Format-C ``## SKILL CONTENT`` block + sibling ``SKILL LOADED: <name>``."""
    if not _PATH_C_RE.search(text):
        return None
    m = _SKILL_LOADED_RE.search(text)
    if m and _validate_skill_name(m.group(1)):
        return m.group(1)
    return None


# ---------------------------------------------------------------------------
# Public API
# ---------------------------------------------------------------------------


def extract_skill(text: object) -> Result:
    """Extract the skill name from a single prompt string.

    Order of precedence: A (inline) → B (reference) → C (block fallback).
    Returns ``Result(skill="unknown", path="none", rejected_reason=<slug>)``
    when no path matched.

    Pure function — no I/O, no side effects. Safe to call from any thread.
    Internal regex compilation is module-load time. Per-extraction cost is
    bounded by MAX_INPUT_CHARS (sanitize) + 3 anchored linear-time scans
    (one per path).
    """
    t0 = time.perf_counter()
    safe, reason = _sanitize(text)
    if safe is None:
        return Result(
            skill="unknown",
            path="none",
            rejected_reason=reason,
            duration_ms=(time.perf_counter() - t0) * 1000.0,
        )
    # Try paths in declared order. First-match wins.
    name_a = _try_path_a(safe)
    if name_a is not None:
        return Result(
            skill=name_a,
            path="a",
            duration_ms=(time.perf_counter() - t0) * 1000.0,
        )
    name_b = _try_path_b(safe)
    if name_b is not None:
        return Result(
            skill=name_b,
            path="b",
            duration_ms=(time.perf_counter() - t0) * 1000.0,
        )
    name_c = _try_path_c(safe)
    if name_c is not None:
        return Result(
            skill=name_c,
            path="c",
            duration_ms=(time.perf_counter() - t0) * 1000.0,
        )
    return Result(
        skill="unknown",
        path="none",
        duration_ms=(time.perf_counter() - t0) * 1000.0,
    )


# ---------------------------------------------------------------------------
# Identity cache (process-local; opt-in via --cached / use_cache=True)
# ---------------------------------------------------------------------------

_CACHE_MAX_ENTRIES = 1024  # bounded — never grows unbounded
_cache: Dict[str, Result] = {}
_cache_order: List[str] = []  # FIFO eviction key list


def _cache_key(text: str) -> str:
    """Stable cache key — SHA-256 over UTF-8 bytes."""
    return hashlib.sha256(text.encode("utf-8", errors="replace")).hexdigest()


def extract_skill_cached(text: object) -> Result:
    """Identity-cached extract. Cache TTL = process lifetime; bounded size."""
    if not isinstance(text, str):
        return extract_skill(text)
    key = _cache_key(text)
    if key in _cache:
        return _cache[key]
    result = extract_skill(text)
    if len(_cache) >= _CACHE_MAX_ENTRIES:
        evict = _cache_order.pop(0)
        _cache.pop(evict, None)
    _cache[key] = result
    _cache_order.append(key)
    return result


def cache_clear() -> None:
    """Drop the process-local identity cache. For tests + long-running CLIs."""
    _cache.clear()
    _cache_order.clear()


# ---------------------------------------------------------------------------
# Batch extractor (ThreadPoolExecutor, fail-soft)
# ---------------------------------------------------------------------------


def extract_many(
    texts: Iterable[object],
    *,
    max_workers: int = 4,
    timeout_per_extract_s: float = PER_EXTRACT_TIMEOUT_S,
) -> List[Result]:
    """Extract many prompts in parallel. Per-extract timeout enforced.

    Fail-soft: a timeout returns ``Result(unknown, "none", "timeout")`` for
    that input slot but DOES NOT abort other extractions. Order of inputs
    is preserved in output.

    For pure CPU-bound regex work the GIL serializes; the parallelism is
    advisory but useful in practice when callers chain disk I/O around
    extraction or run on PyPy. We keep ``max_workers`` small (default 4)
    to avoid thread-pool thrash on adopter machines.
    """
    items = list(texts)
    results: List[Optional[Result]] = [None] * len(items)
    with ThreadPoolExecutor(max_workers=max(1, max_workers)) as pool:
        future_to_index = {
            pool.submit(extract_skill, item): idx
            for idx, item in enumerate(items)
        }
        for fut, idx in future_to_index.items():
            try:
                results[idx] = fut.result(timeout=timeout_per_extract_s)
            except FuturesTimeout:
                results[idx] = Result(
                    skill="unknown",
                    path="none",
                    rejected_reason="timeout",
                    duration_ms=timeout_per_extract_s * 1000.0,
                )
            except Exception as e:  # pragma: no cover — fail-soft
                results[idx] = Result(
                    skill="unknown",
                    path="none",
                    rejected_reason=f"error_{type(e).__name__}",
                    duration_ms=0.0,
                )
    # Type-narrow: every slot has been filled.
    return [r if r is not None else Result("unknown", "none", "internal") for r in results]


# ---------------------------------------------------------------------------
# CLI entrypoint
# ---------------------------------------------------------------------------


def _read_stdin_bounded() -> str:
    """Read stdin once, capped at MAX_INPUT_BYTES. Defensive."""
    data = sys.stdin.buffer.read(MAX_INPUT_BYTES + 1)
    if len(data) > MAX_INPUT_BYTES:
        # Truncate cleanly — _sanitize will re-reject as oversize, but
        # the caller may want a graceful ``unknown`` instead of OOM.
        data = data[:MAX_INPUT_BYTES]
    try:
        return data.decode("utf-8", errors="replace")
    except Exception:
        return ""


def _main(argv: List[str]) -> int:
    parser = argparse.ArgumentParser(
        description="Extract a skill name from a CEO orchestration spawn prompt "
        "(stdin OR --batch jsonl).",
    )
    parser.add_argument(
        "--json",
        action="store_true",
        help="Emit result as JSON (action / path / rejected_reason / duration_ms).",
    )
    parser.add_argument(
        "--cached",
        action="store_true",
        help="Use process-local identity cache (CLI: useful only with --batch).",
    )
    parser.add_argument(
        "--batch",
        metavar="PATH",
        help="Read JSONL of {\"prompt\": <text>} entries and emit one result line each.",
    )
    parser.add_argument(
        "--max-workers",
        type=int,
        default=4,
        help="Parallel workers for --batch mode (default 4).",
    )
    args = parser.parse_args(argv)

    extractor = extract_skill_cached if args.cached else extract_skill

    if args.batch:
        try:
            with open(args.batch, "r", encoding="utf-8") as f:
                lines = [ln for ln in f if ln.strip()]
        except OSError as e:
            sys.stderr.write(f"extract-skill: cannot read --batch: {e}\n")
            return 2
        prompts: List[str] = []
        for ln in lines:
            try:
                obj = json.loads(ln)
                prompts.append(obj.get("prompt", "") if isinstance(obj, dict) else "")
            except json.JSONDecodeError:
                prompts.append("")
        # extract_many handles parallelism + per-extract timeout. Cached mode
        # short-circuits inside extract_skill_cached, so we keep the worker
        # parallelism path consistent regardless.
        results = (
            [extractor(p) for p in prompts] if args.cached
            else extract_many(prompts, max_workers=args.max_workers)
        )
        for r in results:
            if args.json:
                sys.stdout.write(json.dumps({
                    "skill": r.skill,
                    "path": r.path,
                    "rejected_reason": r.rejected_reason,
                    "duration_ms": round(r.duration_ms, 3),
                }) + "\n")
            else:
                sys.stdout.write(f"{r.skill}\t{r.path}\n")
        return 0

    text = _read_stdin_bounded()
    result = extractor(text)
    if args.json:
        sys.stdout.write(json.dumps({
            "skill": result.skill,
            "path": result.path,
            "rejected_reason": result.rejected_reason,
            "duration_ms": round(result.duration_ms, 3),
        }) + "\n")
    else:
        sys.stdout.write(result.skill + "\n")
    return 0


if __name__ == "__main__":
    sys.exit(_main(sys.argv[1:]))
