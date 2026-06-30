#!/usr/bin/env python3
"""statusline-ceo.py — Claude Code statusLine renderer + telemetry sidecar (PLAN-135 W5 O4).

Reads the Claude Code statusLine stdin JSON contract, renders ONE status
line on stdout, and tees a JSON snapshot ("sidecar") to the project state
dir (ADR-001 convention) for fail-soft consumption by:

  * ``measure_multiplier`` (PLAN-128 §7) — live /usage-equivalent quota
    snapshot next to the post-hoc transcript math;
  * ``check_budget``       (hook)        — advisory quota warning line.

## stdin contract (tolerant — absent/unknown fields degrade, never crash)

Claude Code pipes a JSON object on every refresh. Known fields consumed:

    model.display_name / model.id
    workspace.project_dir / cwd
    session_id, version
    cost.total_cost_usd / total_lines_added / total_lines_removed
    exceeds_200k_tokens                                  (bool)
    context_window | context  (used/max tokens OR used_percentage)
    rate_limits   — the /usage-equivalent buckets. Verified against the
                    Claude Code statusLine contract (code.claude.com/docs,
                    fetched 2026-06-13): nested
                    ``rate_limits.{five_hour,seven_day}.{used_percentage,
                    resets_at}`` where ``used_percentage`` is 0-100 and
                    ``resets_at`` is UNIX EPOCH SECONDS (int). Present only
                    for Claude.ai Pro/Max subscribers after the first API
                    response; each window may be independently absent. The
                    Agent-SDK credit bucket (post-2026-06-15) is NOT a field
                    on this contract — recorded as a forward-looking bucket
                    alias only; if Claude Code adds it under rate_limits the
                    generic parser picks it up untruncated. A flat
                    ``{used_percentage, resets_at}`` is also tolerated.

PROBE (pending-owner, $0 — the status line runs LOCALLY and consumes NO
API tokens, per the Claude Code docs): set ``CEO_STATUSLINE_DEBUG=1`` and
run a live session — the raw stdin JSON is teed to ``<sidecar>.debug.json``
so the live field shapes can be pinned against a real harness, in particular
that ``rate_limits`` is present (it appears only for Claude.ai Pro/Max after
the first API response) and whether the Agent-SDK credit bucket surfaces
there post-2026-06-15 (Doctrine 3: verify the knob routes). The field
contract itself is already verified from code.claude.com/docs (2026-06-13).

## Sidecar (schema ``statusline-sidecar/v1``)

Path resolution (mirror of ``_lib/audit_emit._audit_dir()``, ADR-001):

    $CEO_STATUSLINE_SIDECAR                              (full-path override)
    else <audit-dir>/state/statusline-snapshot.json
    where <audit-dir> = $CEO_AUDIT_LOG_DIR
                        or ~/.claude/projects/ceo-orchestration

Atomic write: tmp file in the same dir + ``os.replace``. Content is
numbers / enum-ish ids only — free text from stdin is never echoed.

TRUST TIER (residual, recorded verbatim in PLAN-135 §W5): "the sidecar is
an unauthenticated local JSON read as governance input — same trust tier
as other local state; integrity posture = follow-up if it ever gates a
decision." Consumers MUST stay advisory-only on this input.

## Closed-enum audit action

``statusline_sidecar_write`` — declared in PLAN-135
``staged/w5/actions-added.md`` (folded into ``_KNOWN_ACTIONS`` + SPEC at
arc consolidation). Emitted fail-soft via ``_lib.audit_emit.emit_generic``
and DEBOUNCED: only when the material digest changes AND at least
``CEO_STATUSLINE_EMIT_INTERVAL_S`` (default 300) elapsed since the last
emit. Pre-ceremony, ``emit_generic`` drops the unknown action with a
breadcrumb — bounded by the same debounce, so no flood either way.

## Env surface

    CEO_STATUSLINE_SIDECAR           full sidecar path override
    CEO_STATUSLINE_DISABLE=1         render-only (no sidecar, no emit)
    CEO_STATUSLINE_EMIT=0            sidecar write but no audit emit
    CEO_STATUSLINE_EMIT_INTERVAL_S   emit debounce floor seconds (default 300)
    CEO_STATUSLINE_DEBUG=1           tee raw stdin JSON to <sidecar>.debug.json
    CEO_AUDIT_LOG_DIR                state-dir base (matches audit_log.py)

## Fail-soft contract

ANY internal error → minimal one-line render + exit 0. A status line must
never break the session (same posture as hook fail-open, ADR-005).

Stdlib only. Python >= 3.9.
"""
from __future__ import annotations

import hashlib
import json
import os
import re
import sys
import time
from datetime import datetime, timezone
from pathlib import Path
from typing import Any, Dict, Optional

SCHEMA = "statusline-sidecar/v1"
SOURCE = "statusline-ceo/v1"
_EMIT_ACTION = "statusline_sidecar_write"
_DEFAULT_EMIT_INTERVAL_S = 300
_MAX_PLAN_FILES = 200
_PLAN_HEAD_BYTES = 4096

# Known bucket-name → short render label. Unknown buckets fall through to
# a sanitized 4-char prefix so a post-2026-06-15 Agent-SDK bucket (exact
# key unknown today) still renders + lands in the sidecar untruncated.
_BUCKET_LABELS = (
    (("five_hour", "5h", "session", "five_hour_limit"), "5h"),
    (("seven_day", "weekly", "week", "7d", "seven_day_limit"), "wk"),
    (("agent_sdk", "agentsdk", "sdk", "agent_sdk_credit"), "sdk"),
)


# ---------------------------------------------------------------------------
# Path resolution (ADR-001; byte-mirrors _lib/audit_emit._audit_dir())
# ---------------------------------------------------------------------------


def _audit_dir() -> Path:
    env_dir = os.environ.get("CEO_AUDIT_LOG_DIR")
    if env_dir:
        return Path(env_dir)
    home = os.environ.get("HOME") or str(Path.home())
    return Path(home) / ".claude" / "projects" / "ceo-orchestration"


def _default_sidecar_path() -> Path:
    return _audit_dir() / "state" / "statusline-snapshot.json"


def _sidecar_override_safe(raw: str, target: Path) -> bool:
    """True iff the CEO_STATUSLINE_SIDECAR override is NOT a symlink target, has
    no symlinked immediate parent, and contains no '..' traversal segment.

    PLAN-135-FOLLOWUP (Codex R5 P1-3, a-symlink DiD). The override is a documented
    full-path escape, so we do NOT constrain it under the audit dir (that would
    break the override's purpose + the test fixture). We only reject the
    symlink/traversal sub-vector: a tampered settings `env` block could point the
    always-on writer at an attacker-controlled symlink so an os.replace overwrites
    an out-of-tree file. Best-effort os.path.islink (one lstat each; NO
    os.path.realpath — it stats every path component); OSError → fail-closed
    (reject → default). RESIDUAL (intentionally not closed here): a plain absolute
    path to an attacker-writable dir on the same host, or a symlinked deep
    ancestor, still passes — the real control for the settings-injection vector is
    effective_config's settings-layer tamper detection (Codex R5 P1-3, option b)."""
    try:
        # Inspect the RAW segments — os.path.normpath would RESOLVE a '..' away
        # before we could see it, so a literal traversal segment must be caught
        # pre-normalization.
        if ".." in raw.replace("\\", os.sep).split(os.sep):
            return False
        if os.path.islink(str(target)):
            return False
        parent = target.parent
        if parent.exists() and os.path.islink(str(parent)):
            return False
    except OSError:
        return False
    return True


def _sidecar_path() -> Path:
    env = os.environ.get("CEO_STATUSLINE_SIDECAR")
    if env:
        target = Path(os.path.expanduser(env))
        if not _sidecar_override_safe(env, target):
            sys.stderr.write(
                "# statusline-ceo: CEO_STATUSLINE_SIDECAR rejected "
                "(symlink/traversal target) — using default sidecar path\n"
            )
            return _default_sidecar_path()
        return target
    return _default_sidecar_path()


# ---------------------------------------------------------------------------
# stdin parsing (tolerant)
# ---------------------------------------------------------------------------


def _read_stdin_json() -> Optional[Dict[str, Any]]:
    try:
        raw = sys.stdin.read()
    except Exception:
        return None
    if not raw or not raw.strip():
        return None
    try:
        data = json.loads(raw)
    except ValueError:
        return None
    return data if isinstance(data, dict) else None


def _num(v: Any) -> Optional[float]:
    """Coerce to float; bool/None/str-garbage → None (numbers only)."""
    if isinstance(v, bool) or v is None:
        return None
    if isinstance(v, (int, float)):
        return float(v)
    if isinstance(v, str):
        try:
            return float(v.strip())
        except ValueError:
            return None
    return None


def _safe_slug(name: Any, max_len: int = 32) -> str:
    return re.sub(r"[^a-z0-9_]", "_", str(name).lower())[:max_len]


def normalize_rate_limits(raw: Any) -> Dict[str, Dict[str, Any]]:
    """Normalize the (unverified-shape) rate_limits field.

    Accepts EITHER a flat ``{used_percentage, resets_at}`` object (one
    primary bucket) OR ``{bucket_name: {used_percentage, resets_at}}``.
    Output: ``{safe_bucket: {"used_pct": float|None, "resets_at": str|None}}``.
    Unknown extra fields are dropped (numbers/ids only — no free text).
    """
    out: Dict[str, Dict[str, Any]] = {}
    if not isinstance(raw, dict):
        return out

    def _bucket(name: Any, d: Any) -> None:
        if not isinstance(d, dict):
            return
        pct = _num(d.get("used_percentage", d.get("utilization", d.get("used_pct"))))
        if pct is not None:
            pct = round(min(max(pct, 0.0), 999.0), 1)
        # Verified contract: resets_at is UNIX EPOCH SECONDS (int). We also
        # tolerate an ISO-8601 string in case a future build changes it.
        # Stored faithfully (digits + ISO punctuation kept); the renderer
        # parses both forms.
        resets = d.get("resets_at", d.get("reset_at", d.get("resets")))
        resets_s: Optional[str] = None
        if isinstance(resets, (str, int, float)) and not isinstance(resets, bool):
            resets_s = re.sub(r"[^0-9TZz:+.-]", "", str(resets))[:40] or None
        if pct is None and resets_s is None:
            return
        key = _safe_slug(name) or "bucket"
        out[key] = {"used_pct": pct, "resets_at": resets_s}

    if any(isinstance(v, dict) for v in raw.values()):
        for k, v in raw.items():
            if isinstance(v, dict):
                _bucket(k, v)
    else:
        _bucket("primary", raw)
    return out


def context_pct(data: Dict[str, Any]) -> Optional[float]:
    """Best-effort context-usage %. Tries several candidate shapes; None when absent."""
    for key in ("context_window", "context", "context_usage"):
        cw = data.get(key)
        if not isinstance(cw, dict):
            continue
        pct = _num(cw.get("used_percentage", cw.get("used_pct", cw.get("percent_used"))))
        if pct is not None:
            return round(min(max(pct, 0.0), 100.0), 1)
        used = _num(cw.get("used_tokens", cw.get("input_tokens", cw.get("total_input_tokens"))))
        size = _num(cw.get("context_window_size", cw.get("max_tokens", cw.get("size"))))
        if used is not None and size is not None and size > 0:
            return round(min(max(used / size * 100.0, 0.0), 100.0), 1)
    return None


# ---------------------------------------------------------------------------
# Repo-derived fields (plan id + worktree) — read-only, capped, fail-soft
# ---------------------------------------------------------------------------


def active_plan_id(project_dir: Path) -> Optional[str]:
    """Single ``status: executing`` plan id from ``.claude/plans/`` (capped scan).

    Exactly one executing plan → its ``PLAN-NNN``. More than one → first
    (sorted) + ``+N`` marker. Zero → None. Mirrors the /status convention,
    deliberately simpler than check_budget's active-set logic.
    """
    plans_dir = project_dir / ".claude" / "plans"
    try:
        names = sorted(p for p in plans_dir.iterdir() if p.is_file()
                       and p.name.startswith("PLAN-") and p.name.endswith(".md"))
    except OSError:
        return None
    ids = []
    for p in names[:_MAX_PLAN_FILES]:
        try:
            with open(p, "r", encoding="utf-8", errors="replace") as fh:
                head = fh.read(_PLAN_HEAD_BYTES)
        except OSError:
            continue
        if re.search(r"^status:\s*['\"]?executing\b", head, re.M):
            m = re.match(r"(PLAN-\d{3})", p.name)
            if m:
                ids.append(m.group(1))
    if not ids:
        return None
    if len(ids) == 1:
        return ids[0]
    return "%s+%d" % (ids[0], len(ids) - 1)


def worktree_info(project_dir: Path) -> Dict[str, Optional[str]]:
    """Worktree dir basename + branch, read from .git/HEAD (no subprocess)."""
    branch: Optional[str] = None
    git = project_dir / ".git"
    try:
        head_path: Optional[Path] = None
        if git.is_file():  # linked worktree: ".git" is a pointer file
            m = re.search(r"gitdir:\s*(.+)", git.read_text(encoding="utf-8", errors="replace"))
            if m:
                gd = Path(m.group(1).strip())
                if not gd.is_absolute():
                    gd = (project_dir / gd).resolve()
                head_path = gd / "HEAD"
        elif git.is_dir():
            head_path = git / "HEAD"
        if head_path is not None and head_path.is_file():
            ht = head_path.read_text(encoding="utf-8", errors="replace").strip()
            m = re.match(r"ref:\s*refs/heads/(.+)", ht)
            branch = m.group(1)[:64] if m else (ht[:8] or None)  # detached → short sha
    except OSError:
        pass
    return {"dir": project_dir.name[:64] or None, "branch": branch}


# ---------------------------------------------------------------------------
# Render
# ---------------------------------------------------------------------------


def _bucket_label(key: str) -> str:
    for aliases, label in _BUCKET_LABELS:
        if key in aliases:
            return label
    return key[:4]


def _fmt_resets(resets_at: Optional[str]) -> str:
    """Render a reset time as ``(rHH:MM)`` local. Accepts the verified
    UNIX-epoch-seconds form (e.g. ``"1738425600"``) OR an ISO-8601 string.
    A pure integer string is treated as epoch; anything else is tried as
    ISO. Out-of-range / unparseable → empty (fail-soft, never raises)."""
    if not resets_at:
        return ""
    s = str(resets_at)
    # Epoch seconds: an all-digit token (optionally fractional). Reject the
    # absurd (negative/zero handled by the digit check; cap to ~year 3000).
    if re.fullmatch(r"\d{6,12}(\.\d+)?", s):
        try:
            ts = datetime.fromtimestamp(float(s), tz=timezone.utc)
            return "(r%s)" % ts.astimezone().strftime("%H:%M")
        except (ValueError, OverflowError, OSError):
            return ""
    try:
        ts = datetime.fromisoformat(s.replace("Z", "+00:00"))
        return "(r%s)" % ts.astimezone().strftime("%H:%M")
    except ValueError:
        return ""


def render_line(snapshot: Dict[str, Any]) -> str:
    parts = []
    model = snapshot.get("model_display") or snapshot.get("model_id")
    if model:
        parts.append(str(model)[:24])
    parts.append(snapshot.get("plan_id") or "-")
    pct = snapshot.get("context_pct")
    if pct is not None:
        parts.append("ctx:%d%%" % round(pct))
    elif snapshot.get("exceeds_200k_tokens"):
        parts.append("ctx:>200k")
    rl = snapshot.get("rate_limits") or {}
    bucket_bits = []
    for key in sorted(rl):
        b = rl[key]
        if b.get("used_pct") is None:
            continue
        bucket_bits.append("%s:%d%%%s" % (_bucket_label(key), round(b["used_pct"]),
                                          _fmt_resets(b.get("resets_at"))))
    if bucket_bits:
        parts.append(" ".join(bucket_bits))
    cost = (snapshot.get("cost") or {}).get("total_cost_usd")
    if cost is not None:
        parts.append("$%.2f" % cost)
    wt = snapshot.get("worktree") or {}
    if wt.get("branch"):
        parts.append("%s@%s" % (wt.get("dir") or "?", wt["branch"]))
    elif wt.get("dir"):
        parts.append(wt["dir"])
    return " | ".join(parts) if parts else "ceo"


# ---------------------------------------------------------------------------
# Snapshot build + atomic sidecar write
# ---------------------------------------------------------------------------


def build_snapshot(data: Dict[str, Any]) -> Dict[str, Any]:
    model = data.get("model") if isinstance(data.get("model"), dict) else {}
    ws = data.get("workspace") if isinstance(data.get("workspace"), dict) else {}
    project_dir_s = ws.get("project_dir") or data.get("cwd") or os.getcwd()
    project_dir = Path(str(project_dir_s))
    cost_in = data.get("cost") if isinstance(data.get("cost"), dict) else {}
    cost = {}
    for k in ("total_cost_usd", "total_lines_added", "total_lines_removed"):
        v = _num(cost_in.get(k))
        if v is not None:
            cost[k] = v
    exceeds = data.get("exceeds_200k_tokens")
    rl = normalize_rate_limits(data.get("rate_limits"))
    return {
        "schema": SCHEMA,
        "source": SOURCE,
        "captured_at": datetime.now(timezone.utc).strftime("%Y-%m-%dT%H:%M:%SZ"),
        "session_id": str(data.get("session_id") or "")[:64],
        "cc_version": str(data.get("version") or "")[:32],
        "model_id": str(model.get("id") or "")[:64] or None,
        "model_display": str(model.get("display_name") or "")[:32] or None,
        "project_dir": str(project_dir)[:256],
        "plan_id": active_plan_id(project_dir),
        "worktree": worktree_info(project_dir),
        "context_pct": context_pct(data),
        "exceeds_200k_tokens": exceeds if isinstance(exceeds, bool) else None,
        "rate_limits": rl,
        "rate_limits_available": bool(rl),
        "cost": cost,
    }


def snapshot_digest(snapshot: Dict[str, Any]) -> str:
    """Material digest — excludes captured_at/cost so a pure clock tick never re-emits."""
    material = {k: snapshot.get(k) for k in
                ("plan_id", "worktree", "rate_limits", "model_id", "session_id")}
    pct = snapshot.get("context_pct")
    material["context_decile"] = (int(pct // 10)
                                  if isinstance(pct, (int, float)) and not isinstance(pct, bool)
                                  else None)
    return hashlib.sha256(
        json.dumps(material, sort_keys=True, default=str).encode("utf-8")).hexdigest()


def write_sidecar_atomic(path: Path, snapshot: Dict[str, Any]) -> bool:
    tmp = path.with_name(path.name + ".tmp.%d" % os.getpid())
    try:
        path.parent.mkdir(parents=True, exist_ok=True)
        with open(tmp, "w", encoding="utf-8") as fh:
            json.dump(snapshot, fh, sort_keys=True)
            fh.write("\n")
        os.replace(tmp, path)
        return True
    except OSError:
        try:
            if tmp.exists():  # best-effort tmp cleanup
                tmp.unlink()
        except OSError:
            pass
        return False


# ---------------------------------------------------------------------------
# Debounced closed-enum emit (fail-soft; heavy import only inside the branch)
# ---------------------------------------------------------------------------


def _emit_interval_s() -> int:
    try:
        return max(0, int(os.environ.get("CEO_STATUSLINE_EMIT_INTERVAL_S",
                                         str(_DEFAULT_EMIT_INTERVAL_S))))
    except ValueError:
        return _DEFAULT_EMIT_INTERVAL_S


def should_emit(marker_path: Path, digest: str, now_epoch: float,
                interval_s: int) -> bool:
    """True when the material digest changed AND the debounce floor elapsed."""
    try:
        with open(marker_path, "r", encoding="utf-8") as fh:
            mark = json.load(fh)
        last_digest = mark.get("digest")
        last_ts = float(mark.get("emitted_at", 0))
    except (OSError, ValueError, TypeError):
        return True  # no/corrupt marker → first emit
    if digest == last_digest:
        return False
    return (now_epoch - last_ts) >= interval_s


def _write_marker(marker_path: Path, digest: str, now_epoch: float) -> None:
    try:
        tmp = marker_path.with_name(marker_path.name + ".tmp.%d" % os.getpid())
        with open(tmp, "w", encoding="utf-8") as fh:
            json.dump({"digest": digest, "emitted_at": now_epoch}, fh)
        os.replace(tmp, marker_path)
    except OSError:
        pass


def _pct_to_bps(pct: Optional[float], cap_bps: int = 10000) -> Optional[int]:
    """Percentage (0..N) -> integer basis-points (0..cap_bps) for the
    HMAC-covered statusline AUDIT breadcrumb only. None passes through.
    PLAN-135-FOLLOWUP-2 (S234): the canonical encoder forbids float in a
    signed payload (S181); the prior float form was written with hmac=null on
    every emit since v2.44. context_pct is 0..100% (cap 10000);
    buckets_used_pct_max is capped at 999% upstream (cap 99900 — no 100%
    ceiling, so an over-quota burst is preserved, not floored). This does NOT
    touch context_pct() or the on-disk sidecar JSON, which stay float."""
    if pct is None:
        return None
    try:
        return max(0, min(cap_bps, int(round(float(pct) * 100))))
    except (TypeError, ValueError, OverflowError):
        return None


def maybe_emit(sidecar: Path, snapshot: Dict[str, Any]) -> None:
    if os.environ.get("CEO_STATUSLINE_EMIT", "1").strip().lower() in ("0", "false", "no", "off"):
        return
    digest = snapshot_digest(snapshot)
    marker = sidecar.with_name(sidecar.name + ".emit-state.json")
    now_epoch = time.time()
    if not should_emit(marker, digest, now_epoch, _emit_interval_s()):
        return
    _write_marker(marker, digest, now_epoch)  # marker first — a crashed emit must not retry-flood
    try:
        hooks_dir = None
        pd = snapshot.get("project_dir")
        if pd and (Path(pd) / ".claude" / "hooks" / "_lib").is_dir():
            hooks_dir = Path(pd) / ".claude" / "hooks"
        else:
            cand = Path(__file__).resolve().parents[1] / "hooks"
            if (cand / "_lib").is_dir():
                hooks_dir = cand
        if hooks_dir is None:
            return
        if str(hooks_dir) not in sys.path:
            sys.path.insert(0, str(hooks_dir))
        from _lib import audit_emit  # noqa: E402  (deferred heavy import)
        rl = snapshot.get("rate_limits") or {}
        pcts = [b.get("used_pct") for b in rl.values() if b.get("used_pct") is not None]
        audit_emit.emit_generic(
            _EMIT_ACTION,
            sidecar_path=str(sidecar),
            plan_id=snapshot.get("plan_id"),
            # PLAN-135-FOLLOWUP-2: percentages are HMAC-covered -> integer
            # basis-points (pct * 100), never float (S181). Different caps:
            # context 0..100% (10000); buckets up to 999% (99900).
            context_pct_bps=_pct_to_bps(snapshot.get("context_pct")),
            bucket_count=len(rl),
            buckets_used_pct_max_bps=_pct_to_bps(
                max(pcts) if pcts else None, cap_bps=99900
            ),
            session_id=snapshot.get("session_id") or "",
            digest=digest[:12],
        )
    except Exception:
        # Fail-soft: observability must never break the status line.
        pass


# ---------------------------------------------------------------------------
# Main
# ---------------------------------------------------------------------------


def main() -> int:
    try:
        data = _read_stdin_json()
        if data is None:
            print("ceo | (no statusline payload)")
            return 0
        snapshot = build_snapshot(data)
        print(render_line(snapshot))
        if os.environ.get("CEO_STATUSLINE_DISABLE", "").strip().lower() in ("1", "true", "yes", "on"):
            return 0
        sidecar = _sidecar_path()
        if os.environ.get("CEO_STATUSLINE_DEBUG", "").strip().lower() in ("1", "true", "yes", "on"):
            write_sidecar_atomic(sidecar.with_name(sidecar.name + ".debug.json"), data)
        if write_sidecar_atomic(sidecar, snapshot):
            maybe_emit(sidecar, snapshot)
        return 0
    except Exception:
        # Last-ditch fail-soft: still render SOMETHING, always exit 0.
        try:
            print("ceo")
        except Exception:
            pass
        return 0


if __name__ == "__main__":
    sys.exit(main())
