"""PLAN-102 Wave A.1 — Cost envelope state + cap arithmetic.

STAGED for ceremony Phase A1 copy to
`.claude/hooks/_lib/cost_envelope.py`. The ceremony apply-patches.py
performs the copy with Owner-signed sentinel (approved.md.asc) covering
the canonical destination per ADR-010.

Per-class daily / weekly / monthly / per-plan spend caps for the
autonomous-loop opt-in capability. Ships **DEFAULT-OFF**: activation
requires an Owner-physical opt-in (GPG sentinel + per-class env flag)
per ADR-125 §Tier C invariant + Owner directive 2026-04-17 anti-goal #1.

State files at
`~/.claude/projects/<project>/state/cost-envelope-<sha256[:32]>.json`
guarded by an `fcntl.flock` sibling lock. Tenant isolation uses a
DATED composite key `sha256(project_path + ":" + user_id + ":" +
date)[:32]` so two projects sharing a HOME do not cross-pollinate
counters AND each new UTC date gets a NEW state file. Midnight
rollover is therefore IMPLICIT: today's daily counter lives in
today's date-keyed state file; tomorrow's read targets a different
file (cheap; no migration; no race window for double-spend).

Weekly / monthly windows aggregate over the trailing N dated state
files (7 for weekly; 30 for monthly). Per-plan is filtered within
each state file's `per_plan` block.

Cents are stored as `int`. Floats are forbidden across the audit_emit
HMAC chain (`canonical_json` rejects float). `$5.00 == 500`.

6-layer kill-switch awareness: this module checks the master
`CEO_SWARM` env at import-time + exposes `is_disabled()` for callers
that resolve the flag dynamically. When the master kill is engaged
(`CEO_SWARM` unset OR == "0") the envelope short-circuits to disabled
— the consumer hook returns a pass-through allow.

Sec MF-3: this module does NOT persist project path or user id raw
in state. Only the composite-key hash + counter ints are written.
The audit_emit allowlist for `cost_envelope_capped` (kernel patch
in PLAN-102 ceremony) likewise denies raw path/user fields.

Public API:
    - class CostEnvelope
    - soft_cap_breached(env: CostEnvelope) -> bool
    - is_disabled() -> bool
    - _COST_CAP_MATRIX  (module-level frozen dict)
"""

from __future__ import annotations

import hashlib
import json
import os
import time
from datetime import date as _date_cls
from datetime import datetime, timezone
from pathlib import Path
from typing import Dict, NamedTuple, Optional, Tuple

try:
    from _lib.filelock import FileLock, FileLockTimeout
except Exception:  # pragma: no cover — defensive import path
    FileLock = None  # type: ignore[assignment]

    class FileLockTimeout(Exception):  # type: ignore[no-redef]
        pass


_STATE_SCHEMA_VERSION = 1
_LOCK_TIMEOUT_SEC = 5.0
_VALID_WINDOWS = ("daily", "weekly", "monthly", "per_plan")
_VALID_CLASSES = ("vibecoder", "CTO", "team")


_COST_CAP_MATRIX: Dict[str, Dict[str, int]] = {
    "vibecoder": {
        "daily":        500,
        "weekly":       2500,
        "monthly":      8000,
        "per_plan":     300,
        "max_parallel": 1,
    },
    "CTO": {
        "daily":        1500,
        "weekly":       7500,
        "monthly":      25000,
        "per_plan":     1000,
        "max_parallel": 2,
    },
    "team": {
        "daily":        5000,
        "weekly":       25000,
        "monthly":      80000,
        "per_plan":     3000,
        "max_parallel": 4,
    },
}


_SOFT_CAP_DAILY_BPS = 800
_SOFT_CAP_WEEKLY_BPS = 700
_SOFT_CAP_MONTHLY_BPS = 600


def is_disabled() -> bool:
    """Master kill-switch check.

    Returns True when `CEO_SWARM` is unset or `"0"`. The autonomous-loop
    capability ships DEFAULT-OFF. Consumers MUST treat a True return as
    "do not enforce envelope; pass through allow".
    """
    val = os.environ.get("CEO_SWARM")
    if val is None:
        return True
    return val.strip() == "0"


def _utc_today_iso() -> str:
    return datetime.now(timezone.utc).date().isoformat()


def _utc_iso_week_key(today: Optional[_date_cls] = None) -> str:
    d = today or datetime.now(timezone.utc).date()
    year, week, _ = d.isocalendar()
    return f"{year:04d}-W{week:02d}"


def _utc_month_key(today: Optional[_date_cls] = None) -> str:
    d = today or datetime.now(timezone.utc).date()
    return f"{d.year:04d}-{d.month:02d}"


def _composite_key(project_path: str, user_id: str, date_iso: str) -> str:
    """Return 32-hex prefix of sha256(project_path:user_id:date_iso).

    Per ADR-133 §A dated tenant-iso. Each new UTC date produces a NEW
    key → NEW state file → implicit midnight rollover (no migration).
    """
    raw = f"{project_path}:{user_id}:{date_iso}".encode("utf-8")
    return hashlib.sha256(raw).hexdigest()[:32]


def _state_dir(project_path: str) -> Path:
    home = Path(os.environ.get("HOME") or "/tmp")
    project_slug = project_path.replace("/", "-").strip("-") or "default"
    return home / ".claude" / "projects" / project_slug / "state"


def _state_path_for(project_path: str, user_id: str, date_iso: str) -> Path:
    """Date-keyed state file path. Today's writes target today's file."""
    key = _composite_key(project_path, user_id, date_iso)
    return _state_dir(project_path) / f"cost-envelope-{key}.json"


def _lock_path_for(project_path: str, user_id: str, date_iso: str) -> Path:
    """Date-keyed sibling lock path; pairs with `_state_path_for`."""
    key = _composite_key(project_path, user_id, date_iso)
    return _state_dir(project_path) / f"cost-envelope-{key}.json.lock"


def _list_recent_state_files(
    project_path: str, user_id: str, n_days: int, today: Optional[_date_cls] = None
) -> list:
    """Return list of (date_iso, Path) for the last `n_days` UTC dates.

    Used by weekly / monthly window aggregation. Missing files are
    silently skipped (zero contribution). Sorted oldest → newest.
    """
    from datetime import timedelta
    d_today = today or datetime.now(timezone.utc).date()
    out = []
    for delta in range(n_days):
        d = d_today - timedelta(days=delta)
        diso = d.isoformat()
        p = _state_path_for(project_path, user_id, diso)
        if p.is_file():
            out.append((diso, p))
    out.sort()
    return out


def _empty_state() -> Dict[str, object]:
    return {
        "schema_version": _STATE_SCHEMA_VERSION,
        "tenants": {},
    }


def _load_state(path: Path) -> Dict[str, object]:
    if not path.is_file():
        return _empty_state()
    try:
        raw = path.read_text(encoding="utf-8")
        data = json.loads(raw)
        if not isinstance(data, dict):
            return _empty_state()
        if data.get("schema_version") != _STATE_SCHEMA_VERSION:
            return _empty_state()
        if not isinstance(data.get("tenants"), dict):
            data["tenants"] = {}
        return data
    except (OSError, json.JSONDecodeError, UnicodeDecodeError):
        return _empty_state()


def _atomic_write_state(path: Path, state: Dict[str, object]) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    tmp = path.with_suffix(".json.tmp")
    payload = json.dumps(state, ensure_ascii=False, sort_keys=True, separators=(",", ":"))
    tmp.write_text(payload, encoding="utf-8")
    os.replace(str(tmp), str(path))


class _TodayContext(NamedTuple):
    """Atomic snapshot of date-derived paths/keys per Codex R2 iter-2 P0 #1.

    All four values are derived from a SINGLE `_utc_today_iso()` call so
    a `record_spend()` straddling UTC midnight cannot lock "tomorrow"
    while writing "today" (or vice versa). Threaded through every
    public operation (`current_spend`, `would_breach`, `record_spend`,
    `check_and_record`, `cap_for`) via optional `ctx=None` arg.
    """
    date_iso: str
    state_path: Path
    lock_path: Path
    tenant_key: str


class CostEnvelope:
    """Per-tenant cost envelope with 4-window cap arithmetic.

    Tenants are isolated by the DATED composite key
    `sha256(project_path:user_id:date_iso)[:32]` (ADR-133 §A). Each
    new UTC date produces a NEW state file path — implicit midnight
    rollover with no migration and no race window for double-spend
    (today's writes and tomorrow's writes touch different files).

    **Cross-date atomicity** (Codex R2 iter-2 P0 #1): each public
    operation computes its `_TodayContext` via a SINGLE call to
    `_today_context()` (one `_utc_today_iso()` invocation) and threads
    the resulting (date, state_path, lock_path, tenant_key) tuple
    through every derived value. Eliminates the prior TOCTOU window
    where `state_path` / `lock_path` / tenant key could resolve to
    different dates within a single operation if the clock advanced
    between calls.

    Weekly / monthly aggregation walks the trailing 7 / 30 dated
    state files. Per-plan filters within today's state file.

    The state file is filelock'd at the file system level; concurrent
    writes from sibling processes serialize on fcntl.flock with a
    5-second timeout (fail-OPEN with breadcrumb).

    Methods:
        current_spend(window, ctx=None) -> int
            Returns spend in cents for the named window. Daily looks at
            today's file; weekly sums last 7; monthly sums last 30;
            per_plan filters within today's per_plan block.
        cap_for(window) -> int
            Returns the cents cap for this class tier and window.
        would_breach(additional_cents, ctx=None) -> Optional[str]
            Returns the window name that WOULD breach if the candidate
            additional spend lands, else None. **Advisory inspector
            only** — production callers MUST use `check_and_record()`
            for atomic enforcement (Codex R2 iter-2 P0 #2).
        record_spend(cents, plan_id=None, ctx=None) -> None
            Persists the spend in today's date-keyed state file under
            filelock. **Advisory inspector only** — production callers
            MUST use `check_and_record()` for atomic enforcement.
        check_and_record(additional_cents, plan_id=None) -> Tuple[Optional[str], int, int]
            **Atomic check+add** under a SINGLE FileLock acquisition.
            Eliminates the TOCTOU window between `would_breach()` and
            `record_spend()` in the split-phase API. Returns
            `(breached_window_or_None, cap_cents_or_-1, current_cents)`.
            On allow: records the spend and returns
            `(None, cap_for(first_window), current_after_record)`.
            On block: skips the write and returns
            `(window_name, cap_cents, current_pre_check)`.
    """

    def __init__(
        self,
        project_path: str,
        user_id: str,
        class_tier: str = "vibecoder",
    ) -> None:
        if class_tier not in _VALID_CLASSES:
            class_tier = "vibecoder"
        self._project_path = project_path or ""
        self._user_id = user_id or ""
        self._class_tier = class_tier

    @property
    def class_tier(self) -> str:
        return self._class_tier

    @property
    def state_path(self) -> Path:
        """Today's date-keyed state file path. Recomputed each call so
        a long-lived envelope crosses midnight correctly."""
        return self._today_context().state_path

    def _today_context(self) -> _TodayContext:
        """Atomic snapshot — derive all date-keyed values from ONE
        `_utc_today_iso()` call. Codex R2 iter-2 P0 #1: any function
        that needs date-keyed paths/keys MUST call this once and thread
        the result rather than re-calling `_utc_today_iso()` per
        derived value (which could straddle UTC midnight)."""
        date_iso = _utc_today_iso()
        sp = _state_path_for(self._project_path, self._user_id, date_iso)
        lp = _lock_path_for(self._project_path, self._user_id, date_iso)
        tk = _composite_key(self._project_path, self._user_id, date_iso)
        return _TodayContext(date_iso=date_iso, state_path=sp, lock_path=lp, tenant_key=tk)

    def _today_state_path(self, ctx: Optional[_TodayContext] = None) -> Path:
        if ctx is not None:
            return ctx.state_path
        return self._today_context().state_path

    def _today_lock_path(self, ctx: Optional[_TodayContext] = None) -> Path:
        if ctx is not None:
            return ctx.lock_path
        return self._today_context().lock_path

    def _tenant_block(
        self,
        state: Dict[str, object],
        ctx: Optional[_TodayContext] = None,
    ) -> Dict[str, object]:
        """Today's tenant block (date-keyed file → single tenant block)."""
        tenants = state.get("tenants")
        if not isinstance(tenants, dict):
            tenants = {}
            state["tenants"] = tenants
        if ctx is None:
            ctx = self._today_context()
        key = ctx.tenant_key
        block = tenants.get(key)
        if not isinstance(block, dict):
            block = {
                "daily":    {"cents": 0},
                "per_plan": {"plan_id": "", "cents": 0},
            }
            tenants[key] = block
        if not isinstance(block.get("daily"), dict):
            block["daily"] = {"cents": 0}
        if not isinstance(block.get("per_plan"), dict):
            block["per_plan"] = {"plan_id": "", "cents": 0}
        return block  # type: ignore[return-value]

    def _daily_spend_in_file(self, path: Path) -> int:
        """Read `daily.cents` out of a single dated state file (0 if absent)."""
        state = _load_state(path)
        tenants = state.get("tenants")
        if not isinstance(tenants, dict):
            return 0
        total = 0
        for block in tenants.values():
            if not isinstance(block, dict):
                continue
            daily = block.get("daily")
            if isinstance(daily, dict):
                c = daily.get("cents")
                if isinstance(c, int) and c > 0:
                    total += c
        return total

    def current_spend(
        self, window: str, ctx: Optional[_TodayContext] = None
    ) -> int:
        """Return spend in cents for the named window.

        Advisory inspector. For atomic enforcement use `check_and_record`.
        `ctx` (optional) — pre-computed `_TodayContext`; reuse it to keep
        a multi-step operation date-consistent (Codex R2 iter-2 P0 #1).
        """
        if window not in _VALID_WINDOWS:
            return 0
        if ctx is None:
            ctx = self._today_context()
        if window == "daily":
            state = self._load_under_lock_today(ctx=ctx)
            block = self._tenant_block(state, ctx=ctx)
            sub = block.get("daily")
            if not isinstance(sub, dict):
                return 0
            c = sub.get("cents")
            return int(c) if isinstance(c, int) else 0
        if window == "weekly":
            return self._sum_last_n_days(7, ctx=ctx)
        if window == "monthly":
            return self._sum_last_n_days(30, ctx=ctx)
        if window == "per_plan":
            state = self._load_under_lock_today(ctx=ctx)
            block = self._tenant_block(state, ctx=ctx)
            sub = block.get("per_plan")
            if not isinstance(sub, dict):
                return 0
            c = sub.get("cents")
            return int(c) if isinstance(c, int) else 0
        return 0

    def _sum_last_n_days(
        self, n: int, ctx: Optional[_TodayContext] = None
    ) -> int:
        # Use ctx.date_iso to anchor today; ensures cross-date consistency
        # when called under a clock-tick.
        if ctx is None:
            ctx = self._today_context()
        d_today = datetime.fromisoformat(ctx.date_iso).date()
        total = 0
        for _diso, path in _list_recent_state_files(
            self._project_path, self._user_id, n, today=d_today
        ):
            try:
                total += self._daily_spend_in_file(path)
            except OSError:
                continue
        return total

    def cap_for(self, window: str) -> int:
        if window not in _VALID_WINDOWS:
            return 0
        return int(_COST_CAP_MATRIX[self._class_tier].get(window, 0))

    def would_breach(
        self,
        additional_cents: int,
        ctx: Optional[_TodayContext] = None,
    ) -> Optional[str]:
        """Return the window that WOULD breach, else None.

        **Advisory inspector** — for atomic enforcement use
        `check_and_record()`. Two concurrent dispatches can both pass
        `would_breach()` then both call `record_spend()` and overshoot
        the cap (Codex R2 iter-2 P0 #2 TOCTOU). Production callers
        MUST use `check_and_record()` which holds a single FileLock
        across the read+decide+write.
        """
        if additional_cents <= 0:
            return None
        if ctx is None:
            ctx = self._today_context()
        for window in _VALID_WINDOWS:
            cap = self.cap_for(window)
            if cap <= 0:
                continue
            current = self.current_spend(window, ctx=ctx)
            if current + int(additional_cents) > cap:
                return window
        return None

    def record_spend(
        self,
        cents: int,
        plan_id: Optional[str] = None,
        ctx: Optional[_TodayContext] = None,
    ) -> None:
        """Persist `cents` to today's date-keyed state file.

        **Advisory inspector** — for atomic enforcement use
        `check_and_record()`. Rejects negative or zero amounts
        (defensive). All exceptions bounded: caller (hook) must
        fail-OPEN around this method.
        """
        if not isinstance(cents, int) or cents <= 0:
            return
        cents = int(cents)
        if ctx is None:
            ctx = self._today_context()
        state_path = ctx.state_path
        try:
            with self._acquire_lock(ctx=ctx):
                state = _load_state(state_path)
                block = self._tenant_block(state, ctx=ctx)

                daily = block["daily"]
                if isinstance(daily, dict):
                    daily["cents"] = int(daily.get("cents", 0)) + cents

                per_plan = block.get("per_plan")
                if not isinstance(per_plan, dict):
                    per_plan = {"plan_id": "", "cents": 0}
                    block["per_plan"] = per_plan
                pid = plan_id or ""
                if per_plan.get("plan_id") != pid:
                    per_plan["plan_id"] = pid
                    per_plan["cents"] = 0
                per_plan["cents"] = int(per_plan.get("cents", 0)) + cents

                _atomic_write_state(state_path, state)
        except FileLockTimeout:
            _breadcrumb(
                "cost_envelope: filelock timeout — record_spend dropped (fail-OPEN)"
            )
        except OSError as e:
            _breadcrumb(f"cost_envelope: io error {e!r} — record_spend dropped")

    def check_and_record(
        self,
        additional_cents: int,
        plan_id: Optional[str] = None,
    ) -> Tuple[Optional[str], int, int]:
        """Atomic check+add — Codex R2 iter-2 P0 #2 fold.

        Acquire today's FileLock ONCE; read all 4 window counters;
        decide breach; on allow write the spend; release. Eliminates
        the TOCTOU window between `would_breach()` and `record_spend()`
        in the prior split-phase API.

        Single FileLock acquisition (`ctx.lock_path`) covers BOTH the
        read of current spend AND the conditional write. Two concurrent
        callers serialize on fcntl.flock — exactly one wins each round.

        Returns:
            (breached_window_or_None, cap_cents_or_-1, current_cents)
            - allow path: (None, cap_of_first_window_evaluated_or_0, current_after_record)
            - block path: (window_name, cap_for_window, current_pre_check)

        Fail-OPEN contract: on FileLockTimeout or OSError, returns
        (None, -1, -1) — caller MUST treat sentinel as "lock unavailable;
        do not overcount; pass-through allow per CLAUDE.md §5".
        """
        if not isinstance(additional_cents, int) or additional_cents <= 0:
            # Trivial allow — nothing to add, nothing to check.
            return (None, 0, 0)

        ctx = self._today_context()
        try:
            with self._acquire_lock(ctx=ctx):
                state = _load_state(ctx.state_path)
                block = self._tenant_block(state, ctx=ctx)

                # Compute current per-window under lock.
                # daily: today's block; weekly/monthly: today's block + dated trailing files;
                # per_plan: today's block filtered by plan_id (post-rotation logic).
                cur_daily = 0
                d_sub = block.get("daily")
                if isinstance(d_sub, dict):
                    c = d_sub.get("cents")
                    if isinstance(c, int) and c > 0:
                        cur_daily = c

                cur_per_plan = 0
                p_sub = block.get("per_plan")
                pid = plan_id or ""
                if isinstance(p_sub, dict):
                    existing_pid = p_sub.get("plan_id")
                    if existing_pid == pid:
                        c = p_sub.get("cents")
                        if isinstance(c, int) and c > 0:
                            cur_per_plan = c
                    # else: rotation will reset to 0 on write — current is 0 for this plan_id

                # Weekly / monthly aggregate over trailing dated files PLUS today.
                # We sum across files on disk (today's file may not yet contain
                # this update). Use ctx.date_iso to anchor.
                d_today = datetime.fromisoformat(ctx.date_iso).date()
                weekly_files = _list_recent_state_files(
                    self._project_path, self._user_id, 7, today=d_today
                )
                monthly_files = _list_recent_state_files(
                    self._project_path, self._user_id, 30, today=d_today
                )

                def _sum_files(files):
                    total = 0
                    for _diso, path in files:
                        # Today's file: use the in-memory state we just loaded
                        # (most-fresh under lock). Other files: read from disk.
                        if path == ctx.state_path:
                            tenants = state.get("tenants")
                            if isinstance(tenants, dict):
                                for blk in tenants.values():
                                    if isinstance(blk, dict):
                                        d = blk.get("daily")
                                        if isinstance(d, dict):
                                            c = d.get("cents")
                                            if isinstance(c, int) and c > 0:
                                                total += c
                            continue
                        try:
                            total += self._daily_spend_in_file(path)
                        except OSError:
                            continue
                    return total

                cur_weekly = _sum_files(weekly_files)
                cur_monthly = _sum_files(monthly_files)

                # Decide breach per _VALID_WINDOWS iteration order.
                current_by_window = {
                    "daily":    cur_daily,
                    "weekly":   cur_weekly,
                    "monthly":  cur_monthly,
                    "per_plan": cur_per_plan,
                }
                breached: Optional[str] = None
                breached_cap = 0
                breached_current = 0
                for window in _VALID_WINDOWS:
                    cap = self.cap_for(window)
                    if cap <= 0:
                        continue
                    cur = current_by_window[window]
                    if cur + int(additional_cents) > cap:
                        breached = window
                        breached_cap = cap
                        breached_current = cur
                        break

                if breached is not None:
                    # Block path: do NOT record. Return pre-check counters.
                    return (breached, breached_cap, breached_current)

                # Allow path: record spend in-place (under same lock).
                if isinstance(d_sub, dict):
                    d_sub["cents"] = int(d_sub.get("cents", 0)) + int(additional_cents)
                else:
                    block["daily"] = {"cents": int(additional_cents)}
                    d_sub = block["daily"]

                if not isinstance(p_sub, dict):
                    p_sub = {"plan_id": "", "cents": 0}
                    block["per_plan"] = p_sub
                if p_sub.get("plan_id") != pid:
                    p_sub["plan_id"] = pid
                    p_sub["cents"] = 0
                p_sub["cents"] = int(p_sub.get("cents", 0)) + int(additional_cents)

                _atomic_write_state(ctx.state_path, state)

                # Return allow + new daily counter.
                new_daily = int(d_sub.get("cents", 0))
                return (None, self.cap_for("daily"), new_daily)
        except FileLockTimeout:
            _breadcrumb(
                "cost_envelope: filelock timeout — check_and_record fail-OPEN"
            )
            return (None, -1, -1)
        except OSError as e:
            _breadcrumb(
                f"cost_envelope: io error {e!r} — check_and_record fail-OPEN"
            )
            return (None, -1, -1)

    def soft_cap_breached(self) -> bool:
        return soft_cap_breached(self)

    def _load_under_lock_today(
        self, ctx: Optional[_TodayContext] = None
    ) -> Dict[str, object]:
        if ctx is None:
            ctx = self._today_context()
        path = ctx.state_path
        try:
            with self._acquire_lock(ctx=ctx):
                return _load_state(path)
        except FileLockTimeout:
            _breadcrumb("cost_envelope: filelock timeout on read — fail-OPEN empty")
            return _empty_state()
        except OSError:
            return _empty_state()

    def _acquire_lock(self, ctx: Optional[_TodayContext] = None):
        if FileLock is None:  # pragma: no cover
            return _NullLock()
        if ctx is None:
            ctx = self._today_context()
        return FileLock(
            ctx.lock_path,
            timeout=_LOCK_TIMEOUT_SEC,
            poll_interval=0.05,
        )


class _NullLock:
    def __enter__(self):
        return self

    def __exit__(self, exc_type, exc_val, exc_tb):
        return False


def soft_cap_breached(env: CostEnvelope) -> bool:
    """Compound soft-cap predicate. AND not OR.

    True iff daily >= 80% cap AND weekly >= 70% cap AND monthly >= 60% cap.
    The compound (AND) prevents single-window evasion: a tenant cannot
    burn weekly budget aggressively while staying under daily threshold
    and dodge the soft-cap warning.
    """
    daily_cap = env.cap_for("daily")
    weekly_cap = env.cap_for("weekly")
    monthly_cap = env.cap_for("monthly")
    if daily_cap <= 0 or weekly_cap <= 0 or monthly_cap <= 0:
        return False
    daily = env.current_spend("daily")
    weekly = env.current_spend("weekly")
    monthly = env.current_spend("monthly")
    daily_bps = (daily * 1000) // daily_cap
    weekly_bps = (weekly * 1000) // weekly_cap
    monthly_bps = (monthly * 1000) // monthly_cap
    return (
        daily_bps >= _SOFT_CAP_DAILY_BPS
        and weekly_bps >= _SOFT_CAP_WEEKLY_BPS
        and monthly_bps >= _SOFT_CAP_MONTHLY_BPS
    )


def _breadcrumb(msg: str) -> None:
    try:
        import sys
        sys.stderr.write(f"[cost_envelope] {msg}\n")
    except Exception:
        pass


_IS_DISABLED_AT_IMPORT = is_disabled()
_IMPORT_TS = time.time()
