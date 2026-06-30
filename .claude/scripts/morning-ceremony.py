#!/usr/bin/env python3
"""morning-ceremony.py — PLAN-134 W4 Merkle-root single-GPG morning ceremony v0.

Flow: deep-verify every pending bundle (bytes re-hashed against the
manifests sealed at production time) → render the Morning Ledger → ONE
Owner decision (y/N) → write ratification-<date>.json carrying every bundle
root + a combined Merkle root → ONE `gpg --detach-sign` over that file →
archive ratified bundles. The Owner signs once; the signature covers the
whole night because every byte chains up to the combined root.

Kill-criterion instrumentation (PLAN-134 novel mechanism #3): the elapsed
wall-clock from ledger-presentation to decision is appended to
~/.claude/ceo-runtime/dryrun-log.jsonl. `--baseline` measures the
status-quo instead (raw artifact outputs, no ledger/Merkle) for the same
prompt — the 3-morning dry-run compares the two. Any FalseTrustError is
recorded as a false_trust event (instant kill evidence) and aborts.

Modes:
  (default)    verify + ledger + prompt + GPG sign + archive
  --dry-run    same, but skips GPG and does NOT archive (queue untouched)
  --baseline   status-quo arm: dump raw artifacts, prompt, record timing
  --yes        non-interactive approve (timing recorded as automated)

Stdlib-only, Python >= 3.9.
"""
from __future__ import annotations

import argparse
import json
import os
import subprocess
import sys
import time
from datetime import datetime, timezone
from pathlib import Path
from typing import Any, Dict, List, Optional

SCRIPT_DIR = Path(__file__).resolve().parent
sys.path.insert(0, str(SCRIPT_DIR))
import morning_ledger as ml  # noqa: E402


def _utcnow_iso() -> str:
    return datetime.now(timezone.utc).strftime("%Y-%m-%dT%H:%M:%SZ")


def _utc_date() -> str:
    return datetime.now(timezone.utc).strftime("%Y%m%d")


def _log_timing(row: Dict[str, Any]) -> None:
    ml.runtime_dir().mkdir(parents=True, exist_ok=True)
    path = ml.runtime_dir() / "dryrun-log.jsonl"
    with open(path, "a", encoding="utf-8") as fh:
        fh.write(json.dumps(row, sort_keys=True) + "\n")


def _prompt_decision(auto_yes: bool) -> bool:
    if auto_yes:
        return True
    try:
        ans = input("\nRatificar TODAS as propostas acima com UMA assinatura? [y/N] ")
    except EOFError:
        return False
    return ans.strip().lower() in ("y", "yes", "s", "sim")


def run_baseline(auto_yes: bool) -> int:
    """Status-quo arm: present the RAW artifact outputs (no ledger, no Merkle)."""
    with ml.runtime_lock():
        return _run_baseline_locked(auto_yes)


def _run_baseline_locked(auto_yes: bool) -> int:
    bundles = ml.pending_bundles()
    if not bundles:
        print("Fila vazia — nada para revisar.")
        return 0
    print(f"== STATUS-QUO (baseline): saída crua de {len(bundles)} produção(ões) ==\n")
    t0 = time.perf_counter()
    for bdir in bundles:
        for f in sorted((bdir / "artifacts").rglob("*")):
            # symlink artifacts are never followed (Codex R1 P1 fix)
            if f.is_file() and not f.is_symlink():
                print(f"---- {bdir.name}/{f.name} ----")
                try:
                    print(f.read_text(encoding="utf-8", errors="replace"))
                except OSError as exc:
                    print(f"[unreadable: {exc}]")
    approved = _prompt_decision(auto_yes)
    elapsed = time.perf_counter() - t0
    _log_timing({
        "ts": _utcnow_iso(), "arm": "baseline", "bundles": len(bundles),
        "elapsed_s": round(elapsed, 2), "approved": approved,
        "automated": auto_yes,
    })
    print(f"\nbaseline: {elapsed:.1f}s ({'aprovado' if approved else 'não aprovado'}) — timing registrado.")
    return 0


def _abort_false_trust(bundle: str, exc: Exception) -> int:
    _log_timing({
        "ts": _utcnow_iso(), "arm": "ceremony", "event": "false_trust",
        "bundle": bundle, "detail": ml.sanitize_text(str(exc), 200),
    })
    print(f"\n*** FALSE-TRUST EVENT — cerimônia ABORTADA ***\n{exc}")
    print("Evento registrado em dryrun-log.jsonl (evidência de kill W4).")
    return 2


def run_ceremony(dry_run: bool, auto_yes: bool) -> int:
    # The flock spans verify → decision → sign → archive: the producer (or a
    # second ceremony) can never mutate the queue mid-ceremony (Codex R1 P2).
    with ml.runtime_lock():
        return _run_ceremony_locked(dry_run, auto_yes)


def _run_ceremony_locked(dry_run: bool, auto_yes: bool) -> int:
    bundles = ml.pending_bundles()
    if not bundles:
        print("Fila vazia — nada para ratificar.")
        return 0

    # Phase 1 — deep verification BEFORE presentation (futures already ran
    # at production time; here we prove the bytes are still those bytes).
    verified: List[Dict[str, Any]] = []
    t0 = time.perf_counter()
    for bdir in bundles:
        try:
            verified.append(ml.verify_bundle(bdir, deep=True))
        except ml.FalseTrustError as exc:
            return _abort_false_trust(bdir.name, exc)
    verify_s = time.perf_counter() - t0

    # Phase 2 — present the ledger from the VERIFIED in-memory manifests
    # (never re-read mutable disk between verify and decision; Codex R1 P1).
    print(ml.render_verified_ledger(verified))
    print(f"(verificação byte-a-byte: OK em {verify_s:.1f}s — {len(verified)} bundle(s))")
    t1 = time.perf_counter()
    approved = _prompt_decision(auto_yes)
    decision_s = time.perf_counter() - t1
    total_s = time.perf_counter() - t0

    if not approved:
        _log_timing({
            "ts": _utcnow_iso(), "arm": "ceremony", "bundles": len(verified),
            "elapsed_s": round(total_s, 2), "approved": False, "automated": auto_yes,
            "dry_run": dry_run,
        })
        print("Nada ratificado; fila intacta.")
        return 0

    # Phase 2b — RE-verify after approval (Codex R1 P0 #2: the Owner may sit
    # at the prompt for minutes; bytes must be re-proven IDENTICAL — same
    # Merkle roots — immediately before anything is signed).
    for bdir, first in zip(bundles, verified):
        try:
            again = ml.verify_bundle(bdir, deep=True)
        except ml.FalseTrustError as exc:
            return _abort_false_trust(bdir.name, exc)
        if again["merkle_root"] != first["merkle_root"]:
            return _abort_false_trust(
                bdir.name,
                ml.FalseTrustError(
                    f"{bdir.name}: bundle mudou entre a apresentação e a assinatura "
                    f"(root {first['merkle_root'][:12]}.. → {again['merkle_root'][:12]}..)"
                ),
            )

    # Phase 3 — ratification record: one combined Merkle root over bundle
    # roots. Written atomically (tmp + os.replace) and re-read after GPG to
    # prove the signed bytes are these bytes (Codex R1 P0 #1).
    date = _utc_date()
    record = {
        "format": "ceo-ratification/v0",
        "date": date,
        "decided_at": _utcnow_iso(),
        "bundles": [
            {"bundle_id": m["bundle_id"], "merkle_root": m["merkle_root"]}
            for m in sorted(verified, key=lambda m: m["bundle_id"])
        ],
        "dry_run": dry_run,
    }
    record["combined_root"] = ml.merkle_root([b["merkle_root"] for b in record["bundles"]])
    expected_bytes = (json.dumps(record, indent=2, sort_keys=True) + "\n").encode("utf-8")
    ml.ratifications_dir().mkdir(parents=True, exist_ok=True)
    rec_path = ml.ratifications_dir() / f"ratification-{date}.json"
    suffix = 1
    while rec_path.exists():
        rec_path = ml.ratifications_dir() / f"ratification-{date}.{suffix}.json"
        suffix += 1
    tmp_path = rec_path.with_suffix(".json.tmp")
    with open(tmp_path, "wb") as fh:
        fh.write(expected_bytes)
        fh.flush()
        os.fsync(fh.fileno())
    os.replace(tmp_path, rec_path)

    gpg_ok: Optional[bool] = None
    if not dry_run:
        # Phase 4 — the ONE GPG touch of the morning.
        proc = subprocess.run(
            ["gpg", "--armor", "--detach-sign", str(rec_path)],
            stdout=subprocess.PIPE, stderr=subprocess.STDOUT,
        )
        gpg_ok = proc.returncode == 0
        if gpg_ok:
            # Signed-bytes equality + signature validity BEFORE archiving:
            # a record mutated between write and sign (or a signature that
            # does not verify against the bytes on disk) is a false-trust
            # event, not a success path.
            sig_path = Path(str(rec_path) + ".asc")
            if rec_path.read_bytes() != expected_bytes:
                return _abort_false_trust(
                    rec_path.name,
                    ml.FalseTrustError("registro de ratificação mudou entre escrita e assinatura"),
                )
            vproc = subprocess.run(
                ["gpg", "--verify", str(sig_path), str(rec_path)],
                stdout=subprocess.PIPE, stderr=subprocess.STDOUT,
            )
            if vproc.returncode != 0:
                return _abort_false_trust(
                    rec_path.name,
                    ml.FalseTrustError("assinatura GPG não verifica contra o registro em disco"),
                )
        else:
            print(f"gpg falhou (exit {proc.returncode}); registro mantido SEM assinatura:\n{rec_path}")
        # Phase 5 — archive ratified bundles out of the queue (collision-safe).
        if gpg_ok:
            dest_root = ml.ratified_dir() / date
            dest_root.mkdir(parents=True, exist_ok=True)
            for bdir in bundles:
                dest = dest_root / bdir.name
                n = 1
                while dest.exists():
                    dest = dest_root / f"{bdir.name}.{n}"
                    n += 1
                bdir.rename(dest)

    total_s = time.perf_counter() - t0
    _log_timing({
        "ts": _utcnow_iso(), "arm": "ceremony", "bundles": len(verified),
        "elapsed_s": round(total_s, 2), "decision_s": round(decision_s, 2),
        "approved": True, "automated": auto_yes, "dry_run": dry_run,
        "gpg_ok": gpg_ok, "combined_root": record["combined_root"],
    })
    label = "DRY-RUN (sem GPG, fila intacta)" if dry_run else "assinatura única concluída"
    print(f"\nRatificação {label}: {len(verified)} bundle(s), root {record['combined_root'][:16]}.., {total_s:.1f}s")
    print(f"Registro: {rec_path}")
    return 0


def main(argv: List[str]) -> int:
    ap = argparse.ArgumentParser(description="Merkle-root single-GPG morning ceremony v0 (PLAN-134 W4)")
    ap.add_argument("--dry-run", action="store_true", help="skip GPG + keep queue (3-morning dry-run)")
    ap.add_argument("--baseline", action="store_true", help="status-quo arm: raw outputs, timed")
    ap.add_argument("--yes", action="store_true", help="non-interactive approve (timing marked automated)")
    args = ap.parse_args(argv)
    if args.baseline:
        return run_baseline(args.yes)
    return run_ceremony(args.dry_run, args.yes)


if __name__ == "__main__":
    raise SystemExit(main(sys.argv[1:]))
