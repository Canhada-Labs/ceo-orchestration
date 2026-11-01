# Implementation section: globals belong to the lessons facade.

from __future__ import annotations

__all__ = ['_build_arg_parser', '_handle_write', '_merge_task_desc_keywords', '_apply_ranking', '_emit_read_if_requested', '_handle_top3', '_handle_list', '_handle_undo', '_handle_add_candidate', '_handle_candidates', '_handle_approve', '_handle_expire_sweep', 'main']

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

    # ---- PLAN-154 candidate lifecycle (gated learning loop) ----------------

    # add-candidate — distiller promotion boundary (item 2/3, A4)
    ac = sub.add_parser(
        "add-candidate",
        help="Write a PENDING/QUARANTINED lesson candidate (PLAN-154)",
    )
    ac.add_argument("--trigger", required=True, help="Bounded trigger token")
    ac.add_argument(
        "--text", required=True,
        help="Advisory text (≤200 chars, no backticks/newlines)",
    )
    ac.add_argument("--scope", default="", help="Comma-separated bounded tags")
    ac.add_argument("--dir", default=None, help="Override lessons directory")

    # candidates — /lesson-review listing (all states visible)
    c_sub = sub.add_parser(
        "candidates", help="List lesson candidates (PLAN-154 review view)",
    )
    c_sub.add_argument(
        "--status", default=None,
        choices=sorted(CANDIDATE_STATUSES),
        help="Filter by candidate status",
    )
    c_sub.add_argument("--json", action="store_true", help="JSON output")
    c_sub.add_argument("--dir", default=None, help="Override lessons directory")

    # approve — the /lesson-review human gate backend (A6 hash-pinned)
    ap = sub.add_parser(
        "approve", help="Approve a PENDING candidate (PLAN-154 human gate)",
    )
    ap.add_argument("lesson_id", help="Candidate lesson ID to approve")
    ap.add_argument("--dir", default=None, help="Override lessons directory")

    # expire-sweep — TTL 30d PENDING → terminal EXPIRED (A9)
    es = sub.add_parser(
        "expire-sweep",
        help="Expire PENDING candidates past the 30d TTL (PLAN-154)",
    )
    es.add_argument("--dir", default=None, help="Override lessons directory")

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


def _handle_add_candidate(args) -> int:
    """Execute the ``add-candidate`` sub-command (PLAN-154).

    Exit codes: 0 = written (PENDING or QUARANTINED — status printed);
    2 = bounded-vocabulary reject (ValueError).
    """
    scope_tags = [t.strip() for t in (args.scope or "").split(",") if t.strip()]
    try:
        lesson_id, status = add_candidate(
            trigger=args.trigger,
            advisory_text=args.text,
            scope_tags=scope_tags,
            base_dir=args.dir,
        )
    except ValueError as exc:
        print(f"rejected: {exc}", file=sys.stderr)
        return 2
    print(f"candidate written: {lesson_id} status={status}")
    return 0


def _handle_candidates(args) -> int:
    """Execute the ``candidates`` sub-command (PLAN-154 review listing)."""
    records = list_candidates(base_dir=args.dir, status=args.status)
    if getattr(args, "json", False):
        print(json.dumps(records, indent=2, ensure_ascii=False, sort_keys=True))
        return 0
    if not records:
        print("No candidates found.")
        return 0
    for r in records:
        lid = str(r.get("lesson_id") or "")
        status = str(r.get("status") or "")
        trigger = str(r.get("trigger") or "")
        text = _sanitize_one_liner(r.get("advisory_text"), cap=60)
        print(f"  {lid}  {status:11s}  {trigger:24s}  {text}")
    print(f"\nTotal: {len(records)} candidate(s)")
    return 0


def _handle_approve(args) -> int:
    """Execute the ``approve`` sub-command (PLAN-154 human gate).

    Exit codes mirror the ``undo`` contract shape:
    - 0 approved / already_approved
    - 3 not found
    - 4 refused, no state change (chain_event_missing / scanner_unavailable)
    - 5 terminal transition or already-terminal (QUARANTINED / EXPIRED)
    """
    status, reason = approve_candidate(args.lesson_id, base_dir=args.dir)
    if status == "NOT_FOUND":
        print(f"not found: no candidate with id {args.lesson_id!r}", file=sys.stderr)
        return 3
    print(f"approve: lesson {args.lesson_id!r} status={status} reason={reason}")
    if status == STATUS_APPROVED:
        return 0
    if status == STATUS_PENDING:
        return 4
    return 5


def _handle_expire_sweep(args) -> int:
    """Execute the ``expire-sweep`` sub-command (PLAN-154 TTL, A9).

    Prints expired IDs plus the COUNT-ONLY 7d warning ("N pendings
    expire in <7d" — zero candidate text).
    """
    expired = expire_pending_candidates(base_dir=args.dir)
    for lid in expired:
        print(f"expired: {lid}")
    warn = pending_expiry_warning_count(base_dir=args.dir)
    print(f"expired_total={len(expired)} pendings_expiring_in_7d={warn}")
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
    elif args.command == "add-candidate":
        return _handle_add_candidate(args)
    elif args.command == "candidates":
        return _handle_candidates(args)
    elif args.command == "approve":
        return _handle_approve(args)
    elif args.command == "expire-sweep":
        return _handle_expire_sweep(args)
    else:
        parser.print_help()
        return 1
