# Implementation section: globals belong to the lessons facade.

from __future__ import annotations

__all__ = ['write_lesson', 'list_lessons', '_archetype_match', '_scope_overlap', '_recency_decay', 'rank_lessons', 'get_top_k', 'record_outcome', 'undo_outcome', 'build_index', 'VALID_CONSUMERS']

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
            # PLAN-154 belt: a candidate record misplaced in the live
            # top-level dir must NEVER load as a live lesson — candidates
            # surface only via the verified boot path (A6). Their own
            # namespace is candidates/ (skipped here as a directory).
            if isinstance(data, dict) and str(
                data.get("status") or ""
            ) in CANDIDATE_STATUSES:
                continue
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


def _recency_decay(
    created_at: str,
    now_fn: Optional[Callable[[], Any]] = None,
) -> float:
    """exp(-days/90) exponential decay — 90-day e-folding time.

    PLAN-154 A14 docstring fix: the old wording claimed a "90-day
    half-life"; the actual half-life of exp(-days/90) is 90·ln(2) ≈
    62.4 days (90 days is the e-folding constant, decay ≈ 0.368).

    PLAN-154 A9: injectable ``now_fn`` (wall clock only as default) so
    decay is deterministic under test — golden-value boundaries,
    monotonicity, and twice-run-identical are pinned in
    ``test_lessons_candidates.py``.
    """
    try:
        # Parse ISO 8601
        if created_at.endswith("Z"):
            created_at = created_at[:-1] + "+00:00"
        dt = datetime.fromisoformat(created_at)
        if dt.tzinfo is None:
            dt = dt.replace(tzinfo=timezone.utc)
        now = _now_utc(now_fn)
        days = (now - dt).total_seconds() / 86400
        return math.exp(-days / 90)
    except (ValueError, TypeError, AttributeError):
        return 0.5  # neutral if unparseable


def rank_lessons(
    archetype: str,
    keywords: List[str],
    base_dir: Optional[str] = None,
    now_fn: Optional[Callable[[], Any]] = None,
) -> List[Lesson]:
    """Return top-3 lessons by relevance score (injection-sized)."""
    return get_top_k(archetype, keywords, k=3, base_dir=base_dir, now_fn=now_fn)


def get_top_k(
    archetype: str,
    keywords: List[str],
    k: int = 50,
    base_dir: Optional[str] = None,
    now_fn: Optional[Callable[[], Any]] = None,
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
        rd = _recency_decay(lesson.created_at, now_fn=now_fn)
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


# ---------------------------------------------------------------------------
# PLAN-154 — candidate store (separate namespace: <lessons_dir>/candidates/)
# ---------------------------------------------------------------------------
