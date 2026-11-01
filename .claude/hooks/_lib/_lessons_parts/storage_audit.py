# Implementation section: globals belong to the lessons facade.

from __future__ import annotations

__all__ = ['_lessons_dir', '_generate_id', '_now_utc', '_parse_iso_ts', '_emit_lesson_event', '_lesson_breadcrumb', '_audit_log_paths', '_chain_latest_events', '_scan_lesson_for_injection']

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
    # PLAN-182 W3 (S321): este modulo JA importava runtime_paths (:95) e
    # mesmo assim re-derivava o slug aqui, sem o traco inicial — as lessons
    # do adopter caiam num diretorio IRMAO da raiz da familia. Migracao
    # meio-feita que passava em todos os gates. O dir da grafia antiga nao
    # existe neste repositorio (medido), entao nao ha dado a migrar.
    if project_dir:
        slug = _rp.project_slug(project_dir)
    else:
        slug = "default"
    return home / ".claude" / "projects" / slug / "lessons"


def _generate_id(scenario_id: str, created_at: str) -> str:
    """SHA-256 hash of scenario_id + created_at, truncated to 16 hex chars."""
    raw = f"{scenario_id}:{created_at}"
    return hashlib.sha256(raw.encode("utf-8")).hexdigest()[:16]


# ---------------------------------------------------------------------------
# PLAN-154 — injectable clock seam (A9)
# ---------------------------------------------------------------------------


def _now_utc(now_fn: Optional[Callable[[], Any]] = None) -> datetime:
    """Resolve "now" through the injectable clock seam (A9).

    Every PLAN-154 time function routes through this helper. The wall
    clock is ONLY the default; tests inject ``now_fn`` for golden-value
    boundary + twice-run-identical determinism. ``now_fn`` may return a
    timezone-aware ``datetime`` or an epoch float (``time.time`` style).
    """
    if now_fn is None:
        return datetime.now(timezone.utc)
    value = now_fn()
    if isinstance(value, (int, float)):
        return datetime.fromtimestamp(float(value), tz=timezone.utc)
    if isinstance(value, datetime):
        if value.tzinfo is None:
            return value.replace(tzinfo=timezone.utc)
        return value.astimezone(timezone.utc)
    raise TypeError(
        "now_fn must return a timezone-aware datetime or an epoch float"
    )


def _parse_iso_ts(value: Any) -> Optional[datetime]:
    """Parse an ISO-8601 timestamp (chain ``ts`` or file ``created_at``).

    Returns a UTC-normalized datetime, or None on any parse failure —
    callers decide the failure posture per boundary.
    """
    if not isinstance(value, str) or not value:
        return None
    raw = value.strip()
    if raw.endswith("Z"):
        raw = raw[:-1] + "+00:00"
    try:
        dt = datetime.fromisoformat(raw)
    except ValueError:
        return None
    if dt.tzinfo is None:
        dt = dt.replace(tzinfo=timezone.utc)
    return dt.astimezone(timezone.utc)


# ---------------------------------------------------------------------------
# PLAN-154 — audit plumbing (emit + breadcrumb + bounded chain reads)
# ---------------------------------------------------------------------------


def _emit_lesson_event(action: str, fields: Dict[str, Any]) -> None:
    """Emit a lesson-lifecycle audit event via audit_emit (fail-open).

    Routes EXCLUSIVELY through ``audit_emit.emit_generic`` — never a
    bespoke write path. Pre-registration (action not yet in
    ``_KNOWN_ACTIONS``) this is a breadcrumbed no-op by audit_emit's own
    contract; the integrator lands the 4-file action registration.
    Fields are metadata-only: closed enums, bounded IDs, hashes (A2).
    """
    try:
        from _lib import audit_emit  # noqa: WPS433
        emit = getattr(audit_emit, "emit_generic", None)
        if callable(emit):
            emit(action, **fields)
    except Exception:
        pass


def _lesson_breadcrumb(message: str) -> None:
    """Append a metadata-only breadcrumb to the audit errors sidecar.

    Mirrors ``audit_emit._errors_path`` resolution (env-overridable).
    The sidecar is the ``/ceo-boot`` ``audit_log_freshness`` yellow
    channel, so integrity drops surface to the operator (A6). Never
    raises; never carries candidate text — lesson_id + reason codes only.
    """
    try:
        env = os.environ.get("CEO_AUDIT_LOG_ERR")
        if env:
            err = Path(env)
        else:
            env_dir = os.environ.get("CEO_AUDIT_LOG_DIR")
            if env_dir:
                base = Path(env_dir)
            else:
                home = os.environ.get("HOME") or str(Path.home())
                base = _rp.runtime_state_dir()
            err = base / "audit-log.errors"
        err.parent.mkdir(parents=True, exist_ok=True, mode=0o700)
        ts = datetime.now(timezone.utc).strftime("%Y-%m-%dT%H:%M:%SZ")
        with err.open("a", encoding="utf-8") as f:
            f.write(f"{ts} lessons: {message}\n")
    except Exception:
        pass


def _audit_log_paths() -> List[Path]:
    """Resolve chain files to scan, NEWEST FIRST (bounded count).

    Mirrors ``audit_emit._log_path`` env resolution
    (``CEO_AUDIT_LOG_PATH`` > ``CEO_AUDIT_LOG_DIR`` > ``$HOME`` default),
    then appends rotated monthly siblings (``<stem>-YYYY-MM[...].jsonl``,
    audit_rotation.py naming) sorted newest-first.
    """
    env_path = os.environ.get("CEO_AUDIT_LOG_PATH")
    if env_path:
        current = Path(env_path)
    else:
        env_dir = os.environ.get("CEO_AUDIT_LOG_DIR")
        if env_dir:
            base = Path(env_dir)
        else:
            home = os.environ.get("HOME") or str(Path.home())
            base = _rp.runtime_state_dir()
        current = base / "audit-log.jsonl"

    paths: List[Path] = []
    try:
        if current.is_file():
            paths.append(current)
        rotated = sorted(
            (
                p
                for p in current.parent.glob(current.stem + "-*.jsonl")
                if p != current and p.is_file()
            ),
            reverse=True,
        )
        paths.extend(rotated[: max(0, _CHAIN_SCAN_MAX_FILES - len(paths))])
    except OSError:
        pass
    return paths


def _chain_latest_events(
    actions: Set[str],
    lesson_ids: Optional[Set[str]] = None,
) -> Dict[Tuple[str, str], Dict[str, Any]]:
    """Return the newest chain event per (lesson_id, action) key.

    Bounded read of the HMAC audit chain (A6): files newest-first, total
    byte budget capped. Chain content is UNTRUSTED DATA (ADR-175 — it may
    contain attacker-influenced citations); only closed fields (``ts``,
    ``action``, ``lesson_id``, ``content_sha256``) are consumed, and
    nothing read here is ever rendered. Tamper-evidence of the chain
    itself is ``verify_chain()``'s job, not this reader's.
    """
    found: Dict[Tuple[str, str], Dict[str, Any]] = {}
    budget = _CHAIN_SCAN_MAX_BYTES
    for path in _audit_log_paths():
        if budget <= 0:
            break
        per_file: Dict[Tuple[str, str], Dict[str, Any]] = {}
        try:
            with path.open("r", encoding="utf-8", errors="replace") as f:
                for line in f:
                    budget -= len(line)
                    if budget <= 0:
                        break
                    stripped = line.strip()
                    if not stripped or '"action"' not in stripped:
                        continue
                    try:
                        ev = json.loads(stripped)
                    except (json.JSONDecodeError, ValueError):
                        continue
                    if not isinstance(ev, dict):
                        continue
                    action = ev.get("action")
                    if action not in actions:
                        continue
                    lid = str(ev.get("lesson_id") or "")
                    if lesson_ids is not None and lid not in lesson_ids:
                        continue
                    # Later lines win within one file (append-ordered).
                    per_file[(lid, str(action))] = ev
        except OSError:
            continue
        for key, ev in per_file.items():
            # Files are scanned newest-first: keep the first hit per key.
            found.setdefault(key, ev)
    return found


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
        # scan-injection.py lives in .claude/scripts/ (sibling). Shared
        # loader with the PLAN-154 fail-closed path: the previous inline
        # spec-load skipped sys.modules registration, which on Python 3.9
        # made dataclass processing raise inside exec_module — silently
        # swallowed here (fail-open), i.e. the advisory scan never ran.
        mod = _load_injection_scanner()
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
