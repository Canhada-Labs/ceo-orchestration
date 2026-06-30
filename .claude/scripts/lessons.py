#!/usr/bin/env python3
"""Reflexion lessons — CRUD + relevance ranking.

Sprint 3 Item A. Implements Shinn et al. 2023 "Reflexion" pattern for
the ceo-orchestration framework. When a benchmark scenario fails, the
runner writes a lesson file. When an agent is spawned, the top-3 most
relevant lessons are injected into the prompt.

## Lesson storage

Each lesson is a JSON file under:

    $HOME/.claude/projects/<slug>/lessons/<lesson_id>.json

Lesson IDs are SHA-256 hashes of (scenario_id + created_at). Files are
human-readable JSON, one per lesson.

## Relevance ranking

    score = archetype_match × scope_overlap × recency_decay

- archetype_match: 1.0 if exact match, 0.3 if related, 0.0 otherwise
- scope_overlap: Jaccard similarity of lesson scope_tags vs task keywords
- recency_decay: exp(-days_since_lesson / 90) — 90-day half-life

Top 3 by score, capped at 2K total tokens of injected content.

## CLI

    python3 lessons.py write --scenario-id X --archetype Y --remember "..." --scope "tag1,tag2" --agent-response "..." --expected "..."
    python3 lessons.py top3 --archetype Y --keywords "tag1,tag2"
    python3 lessons.py list
    python3 lessons.py prune --older-than-days 180

## Constraints

- stdlib-only, Python >= 3.9
- Directory scan capped at 1000 files (debate consensus R-DEV3)
- All agent_response content passes through _lib.redact before storage
"""

from __future__ import annotations

import hashlib
import json
import math
import os
import sys
import time
from dataclasses import asdict, dataclass, field
from datetime import datetime, timezone
from pathlib import Path
from typing import Any, Dict, List, Optional, Set

# Make _lib importable — lessons.py lives in .claude/scripts/,
# _lib lives in .claude/hooks/_lib/
_HOOKS_DIR = Path(__file__).resolve().parent.parent / "hooks"
if str(_HOOKS_DIR) not in sys.path:
    sys.path.insert(0, str(_HOOKS_DIR))

try:
    from _lib.redact import redact_secrets
except ImportError:
    # Graceful degradation — if _lib isn't available, no-op redaction
    def redact_secrets(text: str) -> str:  # type: ignore[misc]
        return text

try:
    from _lib.filelock import FileLock, FileLockTimeout
    _FILELOCK_AVAILABLE = True
except ImportError:
    _FILELOCK_AVAILABLE = False

try:
    from _lib.audit_emit import emit_lesson_write as _emit_lesson_write
    from _lib.audit_emit import emit_lesson_read as _emit_lesson_read
    _AUDIT_EMIT_AVAILABLE = True
except ImportError:
    _AUDIT_EMIT_AVAILABLE = False


# Maximum lesson files to scan per query (debate consensus R-DEV3)
_MAX_SCAN = 1000

# Maximum total tokens of injected lesson content
_MAX_INJECT_TOKENS = 2000

# Approximate chars per token for budget estimation
_CHARS_PER_TOKEN = 4


@dataclass
class Lesson:
    """A single reflexion lesson.

    PLAN-006 Phase 4 (ADR-015): extended with `hit_count` / `miss_count`
    for outcome tracking. Absence (or zero) = untested; populated via
    `record_outcome()` when a benchmark run applies this lesson.
    """

    lesson_id: str = ""
    created_at: str = ""  # ISO 8601
    scenario_id: str = ""
    archetype: str = ""
    remember_this: str = ""  # ≤ 200 chars
    scope_tags: List[str] = field(default_factory=list)
    agent_response: str = ""  # redacted before storage
    expected_response: str = ""
    # Outcome loop (ADR-015)
    hit_count: int = 0
    miss_count: int = 0
    last_outcome_at: str = ""  # ISO 8601 of most recent hit/miss

    def hit_rate(self) -> Optional[float]:
        """Ratio hits / (hits + misses). None when n < 3 (low signal)."""
        n = self.hit_count + self.miss_count
        if n < 3:
            return None
        return self.hit_count / n


def _lessons_dir(base_dir: Optional[str] = None) -> Path:
    """Resolve the lessons directory.

    Priority:
    1. base_dir argument (for testing)
    2. CEO_LESSONS_DIR env var
    3. $HOME/.claude/projects/<slug>/lessons/
       where <slug> is derived from CLAUDE_PROJECT_DIR
    """
    if base_dir:
        return Path(base_dir)

    env = os.environ.get("CEO_LESSONS_DIR")
    if env:
        return Path(env)

    # PLAN-025 Batch E F-scripts-003: fail-loud on missing HOME.
    # Silent fallback to /tmp was leaking lessons into a world-writable
    # location when the shell had no HOME set (e.g. launchd processes).
    # Now raises so the operator notices and sets HOME or CEO_LESSONS_DIR.
    home_env = os.environ.get("HOME")
    if not home_env:
        raise RuntimeError(
            "CEO_LESSONS_DIR is unset AND $HOME is empty; refusing to "
            "silently fall back to /tmp. Set CEO_LESSONS_DIR=<path> or "
            "ensure $HOME is exported before calling lessons.py."
        )
    home = Path(home_env)
    project_dir = os.environ.get("CLAUDE_PROJECT_DIR", "")
    if project_dir:
        slug = project_dir.replace("/", "-").lstrip("-")
    else:
        slug = "default"
    return home / ".claude" / "projects" / slug / "lessons"


def _generate_id(scenario_id: str, created_at: str) -> str:
    """SHA-256 hash of scenario_id + created_at, truncated to 16 hex chars."""
    raw = f"{scenario_id}:{created_at}"
    return hashlib.sha256(raw.encode("utf-8")).hexdigest()[:16]


def _scan_lesson_for_injection(
    text_blob: str,
    lesson_id: str,
    archetype: str,
) -> None:
    """PLAN-009 P3.6 — advisory injection scan at lesson-write time.

    Uses the Sprint 5 `scan-injection.py` library. Any match triggers an
    `injection_flag` audit event tagged with the lesson_id + archetype so
    future triage can isolate compromised lessons.

    Fail-open: any import / scan error is swallowed silently. The scan
    is PURE advisory — it never blocks a lesson write.
    """
    if not text_blob:
        return
    try:
        # scan-injection.py lives in .claude/scripts/ (sibling). Using
        # dynamic import because the filename uses a hyphen.
        import importlib.util as _iutil
        spec = _iutil.spec_from_file_location(
            "scan_injection_for_lessons",
            Path(__file__).resolve().parent / "scan-injection.py",
        )
        if spec is None or spec.loader is None:
            return
        mod = _iutil.module_from_spec(spec)
        spec.loader.exec_module(mod)
        result = mod.scan_text(text_blob)
    except Exception:
        return

    if not getattr(result, "matches", None):
        return

    # Emit injection_flag event tagged with lesson context
    try:
        from _lib import audit_emit  # noqa: WPS433
        family_counts: Dict[str, int] = {}
        for m in result.matches:
            fam = getattr(m, "family", "unknown")
            family_counts[fam] = family_counts.get(fam, 0) + 1
        audit_emit.emit_injection_flag(
            source="lesson_write",
            family_counts=family_counts,
            match_count=len(result.matches),
            bytes_scanned=len(text_blob),
            truncated=False,
            triggered_by_tool=f"lesson:{lesson_id}:{archetype}",
        )
    except Exception:
        pass


def write_lesson(
    scenario_id: str,
    archetype: str,
    remember_this: str,
    scope_tags: List[str],
    agent_response: str = "",
    expected_response: str = "",
    base_dir: Optional[str] = None,
    trigger: str = "benchmark_fail",
) -> Path:
    """Write a lesson file to disk. Returns the file path.

    Uses a directory-scoped FileLock to serialize writes across processes
    so that concurrent runners (e.g. parallel benchmark workers) don't
    corrupt lesson files or emit interleaved audit events.
    """
    now = datetime.now(timezone.utc).isoformat()
    lesson_id = _generate_id(scenario_id, now)

    # PLAN-009 P3.6 (K5/A21): scan the lesson body for prompt-injection
    # patterns BEFORE persisting. Attacker-written lessons become fuel for
    # the next Architect spawn (they are injected via top-K retrieval).
    # Advisory: we don't refuse to write, but we emit a breadcrumb +
    # `injection_flag` audit event so future triage can find compromised
    # lessons. Fail-open: scanner errors never block lesson writes.
    try:
        _scan_lesson_for_injection(
            text_blob="\n".join([remember_this, agent_response, expected_response]),
            lesson_id=lesson_id,
            archetype=archetype,
        )
    except Exception:
        pass

    lesson = Lesson(
        lesson_id=lesson_id,
        created_at=now,
        scenario_id=scenario_id,
        archetype=archetype,
        remember_this=remember_this[:200],
        scope_tags=scope_tags,
        agent_response=redact_secrets(agent_response),
        expected_response=redact_secrets(expected_response),
    )

    d = _lessons_dir(base_dir)
    d.mkdir(parents=True, exist_ok=True)
    path = d / f"{lesson_id}.json"
    payload = json.dumps(asdict(lesson), indent=2, ensure_ascii=False) + "\n"

    if _FILELOCK_AVAILABLE:
        lock_path = str(d / ".lessons.lock")
        try:
            with FileLock(lock_path, timeout=2.5):
                path.write_text(payload, encoding="utf-8")
        except FileLockTimeout:
            # Fail-open: lock contention is not fatal. Write anyway.
            path.write_text(payload, encoding="utf-8")
    else:
        path.write_text(payload, encoding="utf-8")

    # Emit audit event (fail-open: wrapped in its own try/except)
    if _AUDIT_EMIT_AVAILABLE:
        try:
            _emit_lesson_write(
                lesson_id=lesson_id,
                archetype=archetype,
                scope_tags=scope_tags,
                trigger=trigger,
                source_event_id=scenario_id,
            )
        except Exception:
            pass

    return path


def list_lessons(base_dir: Optional[str] = None) -> List[Lesson]:
    """List all lessons, capped at _MAX_SCAN files."""
    d = _lessons_dir(base_dir)
    if not d.is_dir():
        return []

    lessons = []
    count = 0
    for f in sorted(d.iterdir()):
        if count >= _MAX_SCAN:
            break
        if not f.suffix == ".json":
            continue
        count += 1
        try:
            data = json.loads(f.read_text(encoding="utf-8"))
            lessons.append(Lesson(**{
                k: data.get(k, v)
                for k, v in Lesson().__dict__.items()
            }))
        except (json.JSONDecodeError, TypeError, KeyError):
            continue
    return lessons


def _archetype_match(lesson_archetype: str, query_archetype: str) -> float:
    """1.0 exact, 0.3 related (same word overlap), 0.0 otherwise."""
    if not lesson_archetype or not query_archetype:
        return 0.0
    la = set(lesson_archetype.lower().split())
    qa = set(query_archetype.lower().split())
    if la == qa:
        return 1.0
    if la & qa:
        return 0.3
    return 0.0


def _scope_overlap(lesson_tags: List[str], query_keywords: List[str]) -> float:
    """Jaccard similarity of tag sets."""
    if not lesson_tags or not query_keywords:
        return 0.0
    a = set(t.lower() for t in lesson_tags)
    b = set(k.lower() for k in query_keywords)
    intersection = len(a & b)
    union = len(a | b)
    if union == 0:
        return 0.0
    return intersection / union


def _recency_decay(created_at: str) -> float:
    """exp(-days/90) — 90-day half-life."""
    try:
        # Parse ISO 8601
        if created_at.endswith("Z"):
            created_at = created_at[:-1] + "+00:00"
        dt = datetime.fromisoformat(created_at)
        now = datetime.now(timezone.utc)
        days = (now - dt).total_seconds() / 86400
        return math.exp(-days / 90)
    except (ValueError, TypeError):
        return 0.5  # neutral if unparseable


def rank_lessons(
    archetype: str,
    keywords: List[str],
    base_dir: Optional[str] = None,
) -> List[Lesson]:
    """Return top-3 lessons by relevance score (injection-sized)."""
    return get_top_k(archetype, keywords, k=3, base_dir=base_dir)


def get_top_k(
    archetype: str,
    keywords: List[str],
    k: int = 50,
    base_dir: Optional[str] = None,
) -> List[Lesson]:
    """Return top-K lessons by relevance score, capped by K.

    PLAN-006 Phase 4 (ADR-015, R-VP4 10x scale): hard cap prevents O(n)
    cross-archetype scoring on every spawn from degrading at scale.
    Relevance weighted by `archetype_match × scope_overlap ×
    recency_decay × hit_rate_weight`.

    Default K=50 (ADR-015 scaling envelope). Injection path uses K=3.
    """
    if k < 1:
        k = 1
    if k > 50:
        k = 50  # hard ceiling per ADR-015

    lessons = list_lessons(base_dir)
    if not lessons:
        return []

    scored = []
    for lesson in lessons:
        am = _archetype_match(lesson.archetype, archetype)
        so = _scope_overlap(lesson.scope_tags, keywords)
        rd = _recency_decay(lesson.created_at)
        # Hit-rate weight: untested lessons (n<3) get neutral 1.0;
        # proven lessons in [0.5, 1.5] range so confirmed winners
        # (hr=1.0 → hw=1.5) outrank untested ones, while confirmed
        # losers (hr=0.0 → hw=0.5) are down-weighted but not zeroed
        # (pruning policy in ADR-017 handles deletion separately).
        hr = lesson.hit_rate()
        hw = 1.0 if hr is None else max(0.1, 0.5 + hr)
        score = am * so * rd * hw
        if score > 0:
            scored.append((score, lesson))

    scored.sort(key=lambda x: x[0], reverse=True)
    return [lesson for _, lesson in scored[:k]]


# PLAN-009 P3.2 (C10/A10) — consumer enum is closed; new values require
# SPEC amendment (SPEC/v1/audit-log.schema.md).
VALID_CONSUMERS = frozenset({"benchmark", "architect"})


def record_outcome(
    lesson_id: str,
    hit: bool,
    base_dir: Optional[str] = None,
    consumer: str = "benchmark",
) -> Optional[Lesson]:
    """Increment hit_count or miss_count on a lesson; update last_outcome_at.

    PLAN-006 Phase 4 (ADR-015); PLAN-009 P3.2 adds ``consumer``
    parameter. Fail-open — returns None if lesson not found or write
    fails.

    Args:
        lesson_id: lesson ID (SHA-256 prefix of scenario_id + created_at)
        hit: True → increment hit_count; False → miss_count
        base_dir: optional override for lessons directory (testing)
        consumer: ``"benchmark"`` (default, back-compat) or
            ``"architect"``. New values require SPEC amendment — see
            ``VALID_CONSUMERS``.

    Raises:
        ValueError: when ``consumer`` is not in ``VALID_CONSUMERS``.
            Strict validation at entry prevents silent mis-attribution
            of Architect outcomes to benchmark aggregates.
    """
    if consumer not in VALID_CONSUMERS:
        raise ValueError(
            f"record_outcome: unknown consumer={consumer!r}. "
            f"Valid values: {sorted(VALID_CONSUMERS)}. "
            "Adding a new consumer requires SPEC v1 amendment."
        )

    d = _lessons_dir(base_dir)
    path = d / f"{lesson_id}.json"
    if not path.is_file():
        return None

    now = datetime.now(timezone.utc).isoformat()
    try:
        data = json.loads(path.read_text(encoding="utf-8"))
    except (OSError, json.JSONDecodeError):
        return None

    if hit:
        data["hit_count"] = int(data.get("hit_count") or 0) + 1
    else:
        data["miss_count"] = int(data.get("miss_count") or 0) + 1
    data["last_outcome_at"] = now

    # Preserve field order; write under lock
    payload = json.dumps(data, indent=2, ensure_ascii=False) + "\n"
    if _FILELOCK_AVAILABLE:
        lock_path = str(d / ".lessons.lock")
        try:
            with FileLock(lock_path, timeout=2.5):
                path.write_text(payload, encoding="utf-8")
        except FileLockTimeout:
            path.write_text(payload, encoding="utf-8")
    else:
        path.write_text(payload, encoding="utf-8")

    # Audit event (fail-open)
    try:
        from _lib import audit_emit  # noqa: WPS433
        audit_emit.emit_lesson_outcome(
            lesson_id=lesson_id,
            archetype=str(data.get("archetype") or ""),
            hit=hit,
            hit_count=int(data.get("hit_count") or 0),
            miss_count=int(data.get("miss_count") or 0),
            consumer=consumer,
        )
    except Exception:
        pass

    return Lesson(**{k: v for k, v in data.items() if k in Lesson.__dataclass_fields__})


def undo_outcome(
    lesson_id: str,
    consumer: str,
    base_dir: Optional[str] = None,
) -> Optional[Lesson]:
    """Reverse a single hit/miss increment on a lesson (PLAN-009 P3.3).

    Escape hatch when the Architect inference rule proves bad. Decrements
    the larger of (hit_count, miss_count) by 1 if > 0. Emits a
    `lesson_outcome_undone` audit event (schema v2.3).

    Best-effort: returns None on not-found / parse error / both counts
    already zero. Consumer is validated per ``VALID_CONSUMERS``.
    """
    if consumer not in VALID_CONSUMERS:
        raise ValueError(
            f"undo_outcome: unknown consumer={consumer!r}. "
            f"Valid values: {sorted(VALID_CONSUMERS)}."
        )

    d = _lessons_dir(base_dir)
    path = d / f"{lesson_id}.json"
    if not path.is_file():
        return None

    try:
        data = json.loads(path.read_text(encoding="utf-8"))
    except (OSError, json.JSONDecodeError):
        return None

    hit_count = int(data.get("hit_count") or 0)
    miss_count = int(data.get("miss_count") or 0)

    if hit_count == 0 and miss_count == 0:
        return None  # nothing to undo

    # Decrement the larger counter (most recent outcome is ambiguous without
    # a per-event log, but the larger bucket is the safer guess for undo).
    if hit_count >= miss_count and hit_count > 0:
        data["hit_count"] = hit_count - 1
        undone_kind = "hit"
    elif miss_count > 0:
        data["miss_count"] = miss_count - 1
        undone_kind = "miss"
    else:
        return None

    payload = json.dumps(data, indent=2, ensure_ascii=False) + "\n"
    if _FILELOCK_AVAILABLE:
        lock_path = str(d / ".lessons.lock")
        try:
            with FileLock(lock_path, timeout=2.5):
                path.write_text(payload, encoding="utf-8")
        except FileLockTimeout:
            path.write_text(payload, encoding="utf-8")
    else:
        path.write_text(payload, encoding="utf-8")

    # Audit event — emit best-effort (fail-open)
    try:
        from _lib import audit_emit  # noqa: WPS433
        audit_emit.emit_lesson_outcome_undone(
            lesson_id=lesson_id,
            archetype=str(data.get("archetype") or ""),
            consumer=consumer,
            undone_kind=undone_kind,
            hit_count=int(data.get("hit_count") or 0),
            miss_count=int(data.get("miss_count") or 0),
        )
    except Exception:
        pass

    return Lesson(**{k: v for k, v in data.items() if k in Lesson.__dataclass_fields__})


def build_index(base_dir: Optional[str] = None) -> Path:
    """Regenerate lessons/index.json — lesson metadata for fast top-K.

    PLAN-006 Phase 4 (ADR-015). Writes a compact index so consumers
    (inject-agent-context) can avoid O(n) file reads on every spawn.
    Index structure:

        {
          "generated_at": "ISO8601",
          "lesson_count": N,
          "lessons": [
            {"id": "...", "archetype": "...", "scope_tags": [...],
             "hit_count": X, "miss_count": Y, "created_at": "..."}
          ]
        }
    """
    d = _lessons_dir(base_dir)
    d.mkdir(parents=True, exist_ok=True)
    lessons = list_lessons(base_dir)
    index = {
        "generated_at": datetime.now(timezone.utc).isoformat(),
        "lesson_count": len(lessons),
        "lessons": [
            {
                "id": l.lesson_id,
                "archetype": l.archetype,
                "scope_tags": l.scope_tags,
                "hit_count": l.hit_count,
                "miss_count": l.miss_count,
                "created_at": l.created_at,
            }
            for l in lessons
        ],
    }
    index_path = d / "index.json"
    payload = json.dumps(index, indent=2, ensure_ascii=False) + "\n"

    if _FILELOCK_AVAILABLE:
        lock_path = str(d / ".lessons.lock")
        try:
            with FileLock(lock_path, timeout=2.5):
                index_path.write_text(payload, encoding="utf-8")
        except FileLockTimeout:
            index_path.write_text(payload, encoding="utf-8")
    else:
        index_path.write_text(payload, encoding="utf-8")
    return index_path


def format_for_injection(lessons: List[Lesson]) -> str:
    """Format top lessons as markdown for prompt injection.

    Respects _MAX_INJECT_TOKENS budget (~2K tokens ≈ 8000 chars).
    """
    if not lessons:
        return ""

    lines = ["## PAST LESSONS", ""]
    budget = _MAX_INJECT_TOKENS * _CHARS_PER_TOKEN
    used = 0

    for i, lesson in enumerate(lessons, 1):
        block = (
            f"### Lesson {i} (scenario: {lesson.scenario_id})\n"
            f"**Remember:** {lesson.remember_this}\n"
            f"**Tags:** {', '.join(lesson.scope_tags)}\n"
            f"**Archetype:** {lesson.archetype}\n"
        )
        if used + len(block) > budget:
            break
        lines.append(block)
        used += len(block)

    return "\n".join(lines)


def _build_arg_parser() -> Any:
    """Build the lessons CLI argparse tree (PLAN-023 Phase E split)."""
    import argparse

    parser = argparse.ArgumentParser(description="Reflexion lessons CRUD + ranking")
    sub = parser.add_subparsers(dest="command")

    # write
    w = sub.add_parser("write", help="Write a new lesson")
    w.add_argument("--scenario-id", required=True)
    w.add_argument("--archetype", required=True)
    w.add_argument("--remember", required=True, help="≤200 char summary")
    w.add_argument("--scope", required=True, help="Comma-separated tags")
    w.add_argument("--agent-response", default="")
    w.add_argument("--expected", default="")
    w.add_argument("--dir", default=None, help="Override lessons directory")

    # top3
    t = sub.add_parser("top3", help="Get top 3 relevant lessons")
    t.add_argument("--archetype", required=True)
    t.add_argument("--keywords", required=True, help="Comma-separated keywords")
    t.add_argument("--dir", default=None)
    t.add_argument(
        "--emit-consumer",
        default="",
        help="If set, emit a lesson_read audit event naming this consumer "
             "(e.g. 'architect', 'spawn'). PLAN-008 Phase 3.",
    )
    t.add_argument(
        "--k", type=int, default=3, help="Number of lessons to return (default 3)",
    )
    t.add_argument(
        "--task-desc", default="",
        help="Optional task description; ≥4-char words merged into keywords "
             "for ranking (PLAN-008 Phase 3 keyword extraction).",
    )
    t.add_argument(
        "--ranking-mode",
        default="recency",
        choices=["recency", "effectiveness", "hybrid"],
        help=(
            "Ranking strategy for top-K lessons (PLAN-009 P5.2). "
            "Default `recency` preserves Sprint 8 behavior. "
            "`effectiveness` delegates to `lesson_ranker.rank_by_effectiveness`; "
            "`hybrid` alternates (not implemented in Sprint 9 — maps to "
            "recency with a breadcrumb). Sprint 10 decides default flip."
        ),
    )

    # list
    l_sub = sub.add_parser("list", help="List all lessons")
    l_sub.add_argument("--dir", default=None)

    # undo (PLAN-136 W3 F1) — reverse one hit/miss increment on a lesson.
    # Backs the `/lesson-review --undo <id>` command (lesson-review.md Step 3),
    # delegating to undo_outcome() which lives in this module.
    u_sub = sub.add_parser(
        "undo", help="Undo (decrement) the most recent outcome on a lesson",
    )
    u_sub.add_argument("lesson_id", help="Lesson ID whose outcome to undo")
    u_sub.add_argument(
        "--consumer", default="architect", choices=sorted(VALID_CONSUMERS),
        help="Consumer tag for the lesson_outcome_undone audit event "
             "(default 'architect').",
    )
    u_sub.add_argument("--dir", default=None, help="Override lessons directory")

    return parser


def _handle_write(args) -> int:
    """Execute the ``write`` sub-command."""
    path = write_lesson(
        scenario_id=args.scenario_id,
        archetype=args.archetype,
        remember_this=args.remember,
        scope_tags=[t.strip() for t in args.scope.split(",")],
        agent_response=args.agent_response,
        expected_response=args.expected,
        base_dir=args.dir,
    )
    print(f"Lesson written: {path}")
    return 0


def _merge_task_desc_keywords(keywords, task_desc: str) -> List[str]:
    """Extract ≥4-char words from task_desc; dedupe into keywords list."""
    if not task_desc:
        return keywords
    import re as _re
    extra = [
        w.lower() for w in _re.findall(r"[A-Za-z][A-Za-z0-9_]*", task_desc)
        if len(w) >= 4
    ]
    seen = set(keywords)
    for w in extra:
        if w not in seen:
            keywords.append(w)
            seen.add(w)
    return keywords


def _apply_ranking(lessons, ranking_mode: str, k: int) -> List[Lesson]:
    """PLAN-009 P5.2 optional re-ranking via lesson_ranker module."""
    if ranking_mode == "effectiveness":
        try:
            import lesson_ranker as _lr  # noqa: WPS433
            ranked = _lr.rank_by_effectiveness(lessons)
            return [t[0] for t in ranked][:k]
        except Exception:
            return lessons  # fail-open: stay with recency order
    elif ranking_mode == "hybrid":
        import sys as _sys
        print("[lessons.top3] ranking-mode=hybrid not implemented; "
              "falling back to recency", file=_sys.stderr)
    return lessons


def _emit_read_if_requested(lesson_ids, archetype, keywords, k, consumer) -> None:
    """Emit lesson_read audit event if --emit-consumer is set."""
    if consumer and _AUDIT_EMIT_AVAILABLE:
        try:
            _emit_lesson_read(
                lesson_ids=lesson_ids,
                archetype=archetype,
                keywords=keywords,
                k=k,
                consumer=consumer,
            )
        except Exception:
            pass


def _handle_top3(args) -> int:
    """Execute the ``top3`` sub-command."""
    keywords = [k.strip() for k in args.keywords.split(",") if k.strip()]
    task_desc = getattr(args, "task_desc", "") or ""
    keywords = _merge_task_desc_keywords(keywords, task_desc)

    k = int(getattr(args, "k", 3) or 3)
    ranking_mode = getattr(args, "ranking_mode", "recency") or "recency"
    lessons = get_top_k(
        archetype=args.archetype,
        keywords=keywords,
        k=k,
        base_dir=args.dir,
    )
    lessons = _apply_ranking(lessons, ranking_mode, k)

    consumer = getattr(args, "emit_consumer", "") or ""

    if not lessons:
        print("No relevant lessons found.")
        _emit_read_if_requested([], args.archetype, keywords, k, consumer)
        return 0

    print(format_for_injection(lessons))
    _emit_read_if_requested(
        [lsn.lesson_id for lsn in lessons],
        args.archetype, keywords, k, consumer,
    )
    return 0


def _handle_list(args) -> int:
    """Execute the ``list`` sub-command."""
    lessons = list_lessons(args.dir)
    if not lessons:
        print("No lessons found.")
        return 0
    for lesson in lessons:
        print(f"  {lesson.lesson_id}  {lesson.scenario_id:30s}  {lesson.remember_this[:60]}")
    print(f"\nTotal: {len(lessons)} lesson(s)")
    return 0


def _handle_undo(args) -> int:
    """Execute the ``undo`` sub-command (PLAN-136 W3 F1).

    Thin CLI over :func:`undo_outcome`. Honors the documented
    ``/lesson-review --undo`` contract (lesson-review.md Step 3):

    - not found   → exit 3, message on stderr (caller suggests re-listing)
    - already-undone / nothing to undo → exit 0, ``already_undone`` no-op
    - undone      → exit 0, confirmation with lesson id + undone kind

    Idempotent: a second invocation after the counters reach zero is a
    no-op (exit 0), never an error.
    """
    lesson_id = args.lesson_id
    path = _lessons_dir(args.dir) / f"{lesson_id}.json"
    if not path.is_file():
        print(f"not found: no live lesson with id {lesson_id!r}", file=sys.stderr)
        return 3

    result = undo_outcome(lesson_id, consumer=args.consumer, base_dir=args.dir)
    if result is None:
        # File exists but both counts were already zero → idempotent no-op.
        print(f"already_undone: lesson {lesson_id!r} has no outcome to undo (no-op)")
        return 0

    hit_count = int(getattr(result, "hit_count", 0) or 0)
    miss_count = int(getattr(result, "miss_count", 0) or 0)
    print(
        f"undone: lesson {lesson_id!r} "
        f"(hit_count={hit_count}, miss_count={miss_count})"
    )
    return 0


def main() -> int:
    """CLI entrypoint (PLAN-023 Phase E decomposition).

    Thin orchestrator over :func:`_build_arg_parser`, :func:`_handle_write`,
    :func:`_handle_top3`, :func:`_handle_list`, and :func:`_handle_undo`.
    The ``write``/``top3``/``list`` paths remain behavior byte-identical to
    the pre-decomposition 157-LoC monolith; ``undo`` is the PLAN-136 W3 F1
    addition.
    """
    parser = _build_arg_parser()
    args = parser.parse_args()

    if args.command == "write":
        return _handle_write(args)
    elif args.command == "top3":
        return _handle_top3(args)
    elif args.command == "list":
        return _handle_list(args)
    elif args.command == "undo":
        return _handle_undo(args)
    else:
        parser.print_help()
        return 1


if __name__ == "__main__":
    sys.exit(main())
