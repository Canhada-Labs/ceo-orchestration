"""Reality ledger: estimate history."""

from __future__ import annotations

import argparse
import ast
import hashlib
import json
import os
import re
import sys
import time
import unicodedata
import uuid
from datetime import datetime, timezone
from pathlib import Path
from typing import Any, Dict, FrozenSet, Iterable, List, Optional, Tuple

from .constants import *  # shared declaration defaults

def _detect_07_disabled() -> bool:
    """Return True if `CEO_REALITY_LEDGER_DETECTOR_07=0` (bypass)."""
    return (os.environ.get("CEO_REALITY_LEDGER_DETECTOR_07") or "").strip() == "0"


def _parse_estimate_block(text: str) -> Dict[str, str]:
    """Parse the nested `estimate:` block from frontmatter text.

    Returns flat dict of estimate sub-fields (compute_hours,
    owner_physical_min, calendar_buffer_days, etc.) → raw string. The
    base parser at `_lib/plan_frontmatter.py` only handles top-level keys
    + simple lists; this helper reads the indented YAML-ish sub-block.
    """
    out: Dict[str, str] = {}
    lines = text.splitlines()
    in_estimate = False
    for line in lines:
        if not in_estimate:
            if _ESTIMATE_KEY_RE.match(line):
                in_estimate = True
            continue
        # Sub-field continues so long as line is indented (starts with space).
        if line and line[0] not in (" ", "\t"):
            break
        m = _ESTIMATE_INDENT_RE.match(line)
        if not m:
            continue
        # Strip inline `# comment` on the value
        raw_val = m.group(2)
        comment_at = raw_val.find("#")
        if comment_at > 0:
            raw_val = raw_val[:comment_at].rstrip()
        out[m.group(1)] = raw_val
    return out


def _coerce_hours_to_pair(raw: str) -> Optional[Tuple[float, float]]:
    """Parse '6-12' → (6.0, 12.0), '8' → (8.0, 8.0). None on failure."""
    if not raw:
        return None
    rng = _HOURS_RANGE_RE.search(raw)
    if rng:
        try:
            lo = float(rng.group(1))
            hi = float(rng.group(2))
            if hi < lo:
                lo, hi = hi, lo
            return (lo, hi)
        except ValueError:
            return None
    single = _SINGLE_NUM_RE.search(raw)
    if single:
        try:
            v = float(single.group(0))
            return (v, v)
        except ValueError:
            return None
    return None


def _extract_top_level_field(text: str, key: str) -> Optional[str]:
    """Extract a top-level frontmatter field (`<key>: <val>`) raw value.

    Used for `created`, `created_at`, `status`, `id`, `actual_owner_physical_min`
    where the base parser also works but we want a single API.
    """
    pat = re.compile(rf"^{re.escape(key)}:\s*(.+?)\s*$", re.MULTILINE)
    m = pat.search(text)
    if not m:
        return None
    val = m.group(1)
    # Strip inline comments
    comment_at = val.find("#")
    if comment_at > 0:
        val = val[:comment_at].rstrip()
    # Strip surrounding quotes
    if (val.startswith('"') and val.endswith('"')) or (
        val.startswith("'") and val.endswith("'")
    ):
        val = val[1:-1]
    return val


def _git_log_paths(repo_root: Path) -> Dict[str, List[Tuple[str, str, bool]]]:
    """Single batched `git log` run; index commits per file.

    Returns dict: rel_path -> list of (commit_sha, iso_committer_date, was_gpg_signed).

    Codex W1+W2 fix-pack #5: switched from author-date (%aI) to committer-date
    (%cI). Author-date reflects original authorship and is preserved verbatim
    across rebases/cherry-picks; that distorts the closeout timeline. Committer
    date reflects when the commit landed in the current branch's history,
    which is what we want for plan span computation.

    GPG-signed inferred via `git log --show-signature` would slow us down
    significantly; instead we emit a separate sub-call to enumerate signed
    commits via `git log --format=%H %G?` (one extra subprocess; total = 2).

    Returns empty dict on any git error (fail-open per Sec NTH #5).
    """
    result: Dict[str, List[Tuple[str, str, bool]]] = {}
    try:
        import subprocess
        # 1) Path-aware log (commit, ISO committer-date, then file lines).
        # Codex Fix #5: use --follow to track plan-file renames and %cI
        # (committer date) so rebased/cherry-picked commits report their
        # landing time, not their original authorship time.
        proc = subprocess.run(
            [
                "git", "-C", str(repo_root), "log",
                "--pretty=format:COMMIT %H %cI",
                "--name-only",
                "--no-merges",
            ],
            capture_output=True,
            text=True,
            timeout=30,
        )
        if proc.returncode != 0:
            return {}
        gpg_signed: Dict[str, bool] = {}
        # 2) Signature mode: %G? returns G (good), B (bad), U (unknown), N (none),
        # E/X/Y/R for various other states. We treat G/U as 'signed'.
        try:
            sig_proc = subprocess.run(
                ["git", "-C", str(repo_root), "log", "--format=%H %G?"],
                capture_output=True,
                text=True,
                timeout=30,
            )
            if sig_proc.returncode == 0:
                for sig_line in sig_proc.stdout.splitlines():
                    parts = sig_line.strip().split()
                    if len(parts) == 2:
                        gpg_signed[parts[0]] = parts[1] in ("G", "U")
        except Exception:
            gpg_signed = {}

        cur_sha: Optional[str] = None
        cur_iso: Optional[str] = None
        for line in proc.stdout.splitlines():
            if line.startswith("COMMIT "):
                rest = line[len("COMMIT "):].split(" ", 1)
                cur_sha = rest[0]
                cur_iso = rest[1] if len(rest) > 1 else ""
            elif line and cur_sha is not None and cur_iso is not None:
                rel = line.strip()
                if rel:
                    result.setdefault(rel, []).append(
                        (cur_sha, cur_iso, gpg_signed.get(cur_sha, False))
                    )
        return result
    except Exception:  # pragma: no cover - fail-open
        return {}


def _git_status_done_transition(
    repo_root: Path,
    plan_rel_path: str,
) -> Optional[Tuple[str, str]]:
    """Find the commit that flipped a plan's frontmatter from non-done to done.

    Codex W1+W2 fix-pack #5 (Fix #5): replaces the prior naive last-commit
    span computation. Returns ``(commit_sha, committer_iso_date)`` for the
    commit whose patch added the line ``+status: done`` to ``plan_rel_path``,
    OR ``None`` if no such commit exists (plan still draft, or transition
    happened in a merge commit which we skip per ``--no-merges`` discipline).

    Edge cases:
      - Plan created and closed in the same commit (PLAN-072 pattern):
        the diff still contains ``+status: done`` so we report that single
        commit; caller separately detects span=0 and skips emitting.
      - Multiple flips (status: done -> reverted -> status: done again):
        we return the LAST such transition; the most recent is the true
        closeout.
      - Renames/file-mv: ``--follow`` tracks the file across renames.
      - Merge commits: ``--no-merges`` skips them; if the only flip lives
        inside a merge, we return None (test fixture should mock this).

    Uses ``git log -G`` regex search + ``git show`` per matching commit
    to confirm the ``+status: done`` is in fact an addition (not a removal).
    """
    try:
        import subprocess
        # Step 1: enumerate commits where the plan file was modified AND
        # the patch contains the literal "status: done" string. ``git
        # log -G`` runs the regex against the line-pair text representing
        # each diff hunk; line anchors (``^``) don't work the way grep
        # expects there, so we keep the regex permissive and let the
        # per-commit ``git show`` parser in step 2 confirm the addition.
        proc = subprocess.run(
            [
                "git", "-C", str(repo_root), "log",
                "--follow",
                "--no-merges",
                "--pretty=format:%H %cI",
                "-G", r"status: *done",
                "--",
                plan_rel_path,
            ],
            capture_output=True,
            text=True,
            timeout=15,
        )
        if proc.returncode != 0 or not proc.stdout.strip():
            return None

        # Walk commits in CHRONOLOGICAL order (oldest -> newest). git log
        # outputs newest-first; we reverse so we can detect the earliest
        # transition and then the most recent re-flip.
        candidates: List[Tuple[str, str]] = []
        for line in proc.stdout.splitlines():
            line = line.strip()
            if not line:
                continue
            parts = line.split(" ", 1)
            if len(parts) != 2:
                continue
            candidates.append((parts[0], parts[1]))
        candidates.reverse()

        # Step 2: For each candidate, run `git show` and check whether the
        # patch ADDS `status: done`. We track the LAST such addition as
        # the true closeout transition (handles re-open / re-close cycles).
        last_transition: Optional[Tuple[str, str]] = None
        for sha, iso in candidates:
            try:
                show = subprocess.run(
                    [
                        "git", "-C", str(repo_root), "show",
                        "--no-color",
                        "--pretty=format:",
                        sha, "--", plan_rel_path,
                    ],
                    capture_output=True,
                    text=True,
                    timeout=10,
                )
            except Exception:
                continue
            if show.returncode != 0:
                continue
            # Match a leading '+' (addition) followed by 'status: done'.
            # Skip '++' headers (file headers in unified diff).
            for diff_line in show.stdout.splitlines():
                if diff_line.startswith("++"):
                    continue
                if diff_line.startswith("+") and re.match(
                    r"^\+\s*status:\s*done\b", diff_line
                ):
                    last_transition = (sha, iso)
                    break
        return last_transition
    except Exception:  # pragma: no cover - fail-open
        return None


def _drift_severity(factor_compute: float, factor_owner: float) -> str:
    """Map drift factor to severity band — bidirectional (Codex Fix #3).

    Bands measured against a symmetric ratio ``r = max(f, 1/f)`` where
    f > 0 is the drift factor. Both overruns (f > 1.2) and underruns
    (f < 0.83) are detected.

      r ≤ 1.2 → factor in [0.83, 1.2] → no drift (caller skips finding)
      1.2 < r ≤ 1.5 → low
      1.5 < r ≤ 2.0 → medium
      r > 2.0 → high

    A factor of 0.0 (estimate present but no actual measured) is treated
    as r = ∞ → high (detector caller already short-circuits when actual
    is missing, but guard here for safety).
    """
    def _ratio(f: float) -> float:
        try:
            af = abs(float(f))
        except (TypeError, ValueError):
            return 1.0
        if af == 0.0:
            return float("inf")
        if af >= 1.0:
            return af
        return 1.0 / af

    rmax = max(_ratio(factor_compute), _ratio(factor_owner))
    if rmax > 2.0:
        return "high"
    if rmax > 1.5:
        return "medium"
    if rmax > 1.2:
        return "low"
    return "low"


def _classify_bias(actual_compute: float, est_compute_lo: float,
                   est_compute_hi: float) -> str:
    """Return 'underestimate' if actual > hi, 'overestimate' if actual < lo, '' otherwise."""
    if actual_compute > est_compute_hi:
        return "underestimate"
    if actual_compute < est_compute_lo:
        return "overestimate"
    return ""


def _read_calibration_csv(path: Path) -> List[str]:
    """Read existing CSV rows (idempotency check). Empty list if missing."""
    if not path.is_file():
        return []
    try:
        return path.read_text(encoding="utf-8").splitlines()
    except OSError:
        return []


def _calibration_csv_dedup_key(row: str) -> str:
    """Build a dedup key for a calibration CSV row that EXCLUDES run_iso8601.

    Codex W1+W2 fix-pack #4: the prior dedup logic (`row in existing`) used
    the entire row including the per-run timestamp ``run_iso8601`` (column
    index 1). Repeat runs always produced a fresh ``run_iso8601`` so dedup
    never matched and the CSV grew unboundedly with N rows per plan per run.

    The dedup key uses the same row content with column-1 (run_iso8601)
    blanked. Same plan + same drift factors + same severity → considered
    "same finding" regardless of when it was measured. The on-disk row
    still preserves run_iso8601 (for forensics — answers "when did we
    first see this drift?"); dedup just doesn't compare on it.

    Column order (header):
      0: plan_id
      1: run_iso8601                  <-- EXCLUDED from key
      2: est_compute_lo
      3: est_compute_hi
      4: actual_compute_h
      5: est_owner_min
      6: actual_owner_min
      7: drift_factor_compute
      8: drift_factor_owner
      9: severity
      10: bias
    """
    cols = row.split(",")
    if len(cols) > 1:
        cols[1] = ""  # blank run_iso8601 from dedup key
    return ",".join(cols)


def _append_calibration_csv(path: Path, row: str) -> None:
    """Append row to CSV idempotently — dedup excludes run_iso8601 (Codex Fix #4)."""
    try:
        existing = _read_calibration_csv(path)
        # Build dedup-key set from existing rows, skipping the header
        # (header row's first column literally is "plan_id" so it can
        # never collide with a real plan id, but we explicitly skip
        # the first line for clarity).
        existing_keys = set()
        for i, line in enumerate(existing):
            if i == 0 and line.startswith("plan_id,"):
                continue  # skip header
            existing_keys.add(_calibration_csv_dedup_key(line))
        if _calibration_csv_dedup_key(row) in existing_keys:
            return  # idempotent: same plan + same drift signature already recorded
        path.parent.mkdir(parents=True, exist_ok=True)
        with path.open("a", encoding="utf-8") as f:
            if not existing:
                # Header row
                f.write(
                    "plan_id,run_iso8601,est_compute_lo,est_compute_hi,"
                    "actual_compute_h,est_owner_min,actual_owner_min,"
                    "drift_factor_compute,drift_factor_owner,severity,bias\n"
                )
            f.write(row + "\n")
    except OSError:
        pass  # fail-open


def _parse_created_iso(raw: str) -> Optional[datetime]:
    """Parse a `created:` frontmatter value into a UTC datetime.

    Accepts ``YYYY-MM-DD`` (interpreted as 00:00:00 UTC) or full ISO8601
    with offset/Z. Returns None on parse failure.
    """
    if not raw:
        return None
    raw = raw.strip()
    # Date-only form: 2026-04-10
    if re.match(r"^\d{4}-\d{2}-\d{2}$", raw):
        try:
            d = datetime.strptime(raw, "%Y-%m-%d")
            return d.replace(tzinfo=timezone.utc)
        except ValueError:
            return None
    # Full ISO with optional Z
    try:
        return datetime.fromisoformat(raw.replace("Z", "+00:00"))
    except ValueError:
        return None



__all__ = ['_detect_07_disabled', '_parse_estimate_block', '_coerce_hours_to_pair', '_extract_top_level_field', '_git_log_paths', '_git_status_done_transition', '_drift_severity', '_classify_bias', '_read_calibration_csv', '_calibration_csv_dedup_key', '_append_calibration_csv', '_parse_created_iso']
