"""Implementation pieces for the budget summary facade."""

from __future__ import annotations

def parse_since(expr: str) -> timedelta:
    """Parse ``Nm`` / ``Nh`` / ``Nd`` into a timedelta. Raises ValueError."""
    m = _SINCE_RE.match(expr.strip().lower())
    if not m:
        raise ValueError(
            f"bad --since value: {expr!r} (expected Nm / Nh / Nd, e.g. 30d)"
        )
    n = int(m.group(1))
    unit = m.group(2)
    if n < 0:
        raise ValueError(f"--since must be non-negative: {expr!r}")
    if unit == "m":
        return timedelta(minutes=n)
    if unit == "h":
        return timedelta(hours=n)
    if unit == "d":
        return timedelta(days=n)
    raise ValueError(f"unknown unit: {unit!r}")  # pragma: no cover


def _parse_ts(ts: Any) -> Optional[datetime]:
    """Parse ISO8601 audit-log timestamp; returns None on miss."""
    if not isinstance(ts, str):
        return None
    normalized = ts.replace("Z", "+0000")
    try:
        return datetime.strptime(normalized, "%Y-%m-%dT%H:%M:%S%z")
    except ValueError:
        return None


def _parse_ts_any(ts: Any) -> Optional[datetime]:
    """``_parse_ts`` that also accepts fractional-second ISO stamps."""
    if not isinstance(ts, str):
        return None
    return _parse_ts(_TS_FRACTION_RE.sub("", ts))


def default_audit_dir() -> Path:
    """Return the canonical audit-log directory.

    Honors ``CEO_AUDIT_LOG_DIR`` env override (used by tests). Otherwise
    defaults to ``~/.claude/projects/<native-slug>/``.
    """
    env_dir = os.environ.get("CEO_AUDIT_LOG_DIR")
    if env_dir:
        return Path(env_dir)
    home = os.environ.get("HOME") or str(Path.home())
    return _rp.runtime_state_dir()


def discover_logs(audit_dir: Optional[Path] = None) -> List[Path]:
    """Return all ``audit-log*.jsonl`` files in the audit dir, sorted.

    Ordering: ``audit-log.jsonl`` (the active log) is read LAST so that
    when an event is duplicated across rotation boundary the *backup*
    version wins (it's the immutable, GPG-friendly historical record).
    Backups are sorted lexicographically (which equals chronological
    for the ``audit-log-YYYY-MM-N.jsonl`` rotation convention).
    """
    if audit_dir is None:
        audit_dir = default_audit_dir()
    if not audit_dir.is_dir():
        return []
    pattern = str(audit_dir / AUDIT_LOG_GLOB)
    paths = sorted(Path(p) for p in glob.glob(pattern))
    active: List[Path] = []
    backups: List[Path] = []
    for p in paths:
        if p.name == "audit-log.jsonl":
            active.append(p)
        else:
            backups.append(p)
    return backups + active


def canonical_event_sha256(event: Dict[str, Any]) -> str:
    """Compute sha256 over the canonical form of an event.

    Strips ``_DEDUP_STRIP_FIELDS`` (hmac/hmac_error/hook_duration_ms)
    so that the *same logical event* mirrored across a rotation
    boundary canonicalizes identically.

    Returns a 64-char hex digest.
    """
    canonical = {k: v for k, v in event.items() if k not in _DEDUP_STRIP_FIELDS}
    blob = json.dumps(canonical, sort_keys=True, ensure_ascii=False, separators=(",", ":"))
    return hashlib.sha256(blob.encode("utf-8")).hexdigest()


def iter_unique_events(
    log_paths: Iterable[Path],
    seen: Optional[Set[str]] = None,
) -> Iterator[Dict[str, Any]]:
    """Yield deduplicated events across multiple log files.

    Tolerates malformed JSON lines (silently skipped — matches
    ``audit_emit.iter_events`` behavior for forward compatibility).
    """
    if seen is None:
        seen = set()
    for path in log_paths:
        try:
            with path.open("r", encoding="utf-8") as f:
                for raw in f:
                    raw = raw.strip()
                    if not raw:
                        continue
                    try:
                        event = json.loads(raw)
                    except json.JSONDecodeError:
                        continue
                    if not isinstance(event, dict):
                        continue
                    digest = canonical_event_sha256(event)
                    if digest in seen:
                        continue
                    seen.add(digest)
                    yield event
        except OSError:
            continue


def _safe_plan_id(value: Any) -> Optional[str]:
    """Return value if it matches PLAN-NNN, else None (Sec MF-3 boundary)."""
    if not isinstance(value, str):
        return None
    if _PLAN_ID_RE.match(value):
        return value
    return None



