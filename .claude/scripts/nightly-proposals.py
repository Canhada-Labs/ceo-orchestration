#!/usr/bin/env python3
"""nightly-proposals.py — PLAN-134 W4 zero-LLM nightly proposal producer.

Runs scripts that ALREADY exist (judge.md W4 validation recipe: staleness
checker, verify-counts, orphan-worktree scan), captures their outputs as
bundle artifacts, records each run as a *future* (declared check + exit
code, executed BEFORE presentation), and enqueues one proposal bundle per
producer into ~/.claude/ceo-runtime/proposal-queue/ for the morning
ceremony. $0, no LLM call anywhere.

Recommendation semantics v0 (founder language): "sign" = every declared
check exited 0 and the evidence is hash-bound — ratifying costs one glance;
"dont-sign" = at least one check failed — look before you sign.

Idempotent per night: bundle ids carry the UTC date; an existing bundle id
is skipped (re-runs don't duplicate).

Stdlib-only, Python >= 3.9.
"""
from __future__ import annotations

import argparse
import json
import subprocess
import sys
import time
from datetime import datetime, timezone
from pathlib import Path
from typing import List, Optional, Tuple

SCRIPT_DIR = Path(__file__).resolve().parent
REPO_ROOT = SCRIPT_DIR.parents[1]

sys.path.insert(0, str(SCRIPT_DIR))
import morning_ledger as ml  # noqa: E402

_TIMEOUT_S = 120
_MAX_CAPTURE = 200_000  # bytes of combined output kept as artifact


def _utc_date() -> str:
    return datetime.now(timezone.utc).strftime("%Y%m%d")


def _run(cmd: List[str], cwd: Path) -> Tuple[int, bytes, int]:
    """Run a producer command. Returns (exit_code, combined_output, duration_ms)."""
    t0 = time.perf_counter()
    try:
        proc = subprocess.run(
            cmd,
            cwd=str(cwd),
            stdout=subprocess.PIPE,
            stderr=subprocess.STDOUT,
            timeout=_TIMEOUT_S,
        )
        out = proc.stdout or b""
        code = proc.returncode
    except subprocess.TimeoutExpired as exc:
        out = (exc.stdout or b"") + b"\n[TIMEOUT]"
        code = 124
    except OSError as exc:
        out = str(exc).encode("utf-8")
        code = 127
    dur = int((time.perf_counter() - t0) * 1000)
    if len(out) > _MAX_CAPTURE:
        out = out[:_MAX_CAPTURE] + b"\n[TRUNCATED]"
    return code, out, dur


def _orphan_worktree_scan(cwd: Path) -> Tuple[int, bytes, int]:
    """git worktree list + count of non-primary worktrees (read-only)."""
    code, out, dur = _run(["git", "worktree", "list", "--porcelain"], cwd)
    if code == 0:
        n_extra = max(0, out.count(b"worktree ") - 1)
        out += f"\n# non-primary worktrees: {n_extra}\n".encode("ascii")
    return code, out, dur


def _staleness_why(exit_code: int, output: bytes) -> Tuple[str, str]:
    """Honest verdict/why for the staleness producer (PREREG-W4 Amendment #1).

    check-staleness.py exits 0 even when status=degraded (advisory). The
    ledger must NEVER say "rodou limpa" when the artifact says otherwise —
    parse findings_count and surface it in founder language.
    """
    if exit_code != 0:
        return "dont-sign", "O check de staleness FALHOU ou achou itens parados — olhe o artefato antes de assinar."
    try:
        data = json.loads(output.decode("utf-8", errors="replace"))
        n = int(data.get("findings_count", 0))
        status = str(data.get("status", "ok"))
    except (ValueError, AttributeError):
        return "dont-sign", "Artefato de staleness ilegível — olhe antes de assinar."
    if n > 0:
        return (
            "sign",
            f"Check rodou; status {status} com {n} achado(s) advisory no artefato — vale uma olhada, nada bloqueante.",
        )
    return "sign", "Checagem mecânica de planos/ADRs parados rodou limpa; evidência selada por hash."


PRODUCERS = [
    # (slug, title, cmd-or-callable, artifact name, why-on-pass, why-on-fail)
    (
        "staleness",
        "Relatório de staleness (planos/ADRs parados)",
        [sys.executable, str(SCRIPT_DIR / "check-staleness.py"), "--json"],
        "staleness.json",
        _staleness_why,  # callable: honest verdict from artifact content
        None,
    ),
    (
        "verify-counts",
        "Contagens da documentação vs código real",
        ["bash", str(SCRIPT_DIR / "local" / "verify-counts.sh")],
        "verify-counts.txt",
        "Todas as contagens documentadas batem com o código real; sem drift.",
        "Drift de contagem detectado entre docs e código — olhe antes de assinar.",
    ),
    (
        "orphan-worktrees",
        "Varredura de worktrees órfãos",
        _orphan_worktree_scan,
        "worktrees.txt",
        "Varredura de worktrees rodou limpa; lista selada por hash.",
        "A varredura de worktrees FALHOU — olhe antes de assinar.",
    ),
]


def build_night(root: Optional[Path] = None, date: Optional[str] = None) -> List[str]:
    """Produce tonight's bundles. Returns list of '<bundle_id>: <status>' lines.

    Holds the runtime flock so production can never interleave with a
    mid-flight morning ceremony (Codex R1 P2 fix).
    """
    lock_root = root.parent if root is not None else None
    with ml.runtime_lock(lock_root, blocking=False):
        return _build_night_locked(root, date)


def _build_night_locked(root: Optional[Path], date: Optional[str]) -> List[str]:
    date = date or _utc_date()
    results: List[str] = []
    qdir = root or ml.queue_dir()
    for stale_tmp in (sorted(qdir.glob(".tmp-*")) if qdir.is_dir() else []):
        results.append(f"{stale_tmp.name}: INCOMPLETE residue from a crashed run — inspect/remove manually")
    for slug, title, runner, artifact_name, why_pass, why_fail in PRODUCERS:
        bundle_id = f"{date}-{slug}"
        target = qdir / bundle_id
        if (target / "manifest.json").is_file():
            results.append(f"{bundle_id}: SKIP (already queued)")
            continue
        if target.exists():
            results.append(f"{bundle_id}: INCOMPLETE (dir without manifest) — inspect/remove manually")
            continue
        if callable(runner):
            code, out, dur = runner(REPO_ROOT)
            cmd_str = f"<builtin:{slug}>"
        else:
            code, out, dur = _run(runner, REPO_ROOT)
            cmd_str = " ".join(Path(c).name if "/" in str(c) else str(c) for c in runner)
        future = ml.Future(
            name=slug,
            cmd=cmd_str,
            exit_code=code,
            ran_at=datetime.now(timezone.utc).strftime("%Y-%m-%dT%H:%M:%SZ"),
            duration_ms=dur,
            output_sha256=ml._sha256_bytes(out),
        )
        if callable(why_pass):
            verdict, why = why_pass(code, out)
        else:
            verdict = "sign" if code == 0 else "dont-sign"
            why = why_pass if code == 0 else why_fail
        spec = ml.BundleSpec(
            bundle_id=bundle_id,
            title=title,
            producer="nightly-proposals.py",
            artifacts=[(artifact_name, out)],
            futures=[future],
            verdict=verdict,
            why=why,
        )
        ml.create_bundle(spec, root=root)
        results.append(f"{bundle_id}: queued (exit={code}, {dur} ms)")
    return results


def main(argv: List[str]) -> int:
    ap = argparse.ArgumentParser(description="zero-LLM nightly proposal producer (PLAN-134 W4)")
    ap.add_argument("--date", help="override UTC date stamp YYYYMMDD (tests)")
    ap.add_argument("--json", action="store_true", help="machine-readable output")
    args = ap.parse_args(argv)
    try:
        lines = build_night(date=args.date)
    except RuntimeError as exc:
        # lock held by a mid-flight ceremony — friendly exit, no traceback
        print(str(exc), file=sys.stderr)
        return 75  # EX_TEMPFAIL
    if args.json:
        print(json.dumps({"results": lines}, indent=2))
    else:
        for ln in lines:
            print(ln)
    return 0


if __name__ == "__main__":
    raise SystemExit(main(sys.argv[1:]))
