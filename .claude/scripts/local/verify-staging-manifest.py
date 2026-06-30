#!/usr/bin/env python3
"""PLAN-084 Wave 0.10 — verify-staging-manifest.

R2-iter-2 CODEX-P0-2 strict enforcement:
(a) sha256 every artifact; mismatch with manifest = HALT
(b) cross-reference manifest entries against wave_artifact_written audit
    events for same (wave_id, archetype, path) tuple
(c) verify manifest GPG .asc signature against Owner key fingerprint

Stdlib only (uses gpg binary subprocess for signature verify).

Usage:
  python3 .claude/scripts/local/verify-staging-manifest.py \
    --manifests .claude/plans/PLAN-084/manifests/ \
    --staging .claude/plans/PLAN-084/ \
    --audit-log ~/.claude/projects/ceo-orchestration/audit-log.jsonl \
    --owner-fingerprint 0000000000000000000000000000000000000000
"""

from __future__ import annotations

import argparse
import hashlib
import json
import re
import subprocess
import sys
from pathlib import Path
from typing import Dict, List, Optional, Set, Tuple


def sha256_file(path: Path) -> str:
    h = hashlib.sha256()
    with path.open("rb") as f:
        for chunk in iter(lambda: f.read(65536), b""):
            h.update(chunk)
    return h.hexdigest()


def parse_manifest_yaml(path: Path) -> Tuple[List[Dict], List[str], int]:
    """Return (artifacts, raw_finding_ids_universe, pre_cap_total)."""
    artifacts: List[Dict] = []
    universe: List[str] = []
    pre_cap_total: int = 0
    current_artifact: Optional[Dict] = None
    in_artifacts = False
    in_universe = False
    for line in path.read_text(encoding="utf-8").splitlines():
        s = line.rstrip()
        if s.startswith("artifacts:"):
            in_artifacts = True
            in_universe = False
            continue
        if s.startswith("raw_finding_ids_universe:"):
            in_artifacts = False
            in_universe = True
            continue
        if s.startswith("pre_cap_total:"):
            in_universe = False
            try:
                pre_cap_total = int(s.split(":", 1)[1].strip())
            except ValueError:
                pass
            continue
        if in_artifacts:
            if re.match(r"\s*-\s*path:", s):
                if current_artifact:
                    artifacts.append(current_artifact)
                current_artifact = {"path": s.split("path:", 1)[1].strip().strip('"').strip("'")}
            elif current_artifact and re.match(r"\s+sha256:", s):
                current_artifact["sha256"] = s.split("sha256:", 1)[1].strip().strip('"').strip("'")
            elif current_artifact and re.match(r"\s+owner_archetype:", s):
                current_artifact["owner_archetype"] = s.split("owner_archetype:", 1)[1].strip().strip('"').strip("'")
            elif current_artifact and re.match(r"\s+write_session_id:", s):
                current_artifact["write_session_id"] = s.split("write_session_id:", 1)[1].strip().strip('"').strip("'")
            elif current_artifact and re.match(r"\s+write_ts:", s):
                current_artifact["write_ts"] = s.split("write_ts:", 1)[1].strip().strip('"').strip("'")
        if in_universe:
            m = re.match(r"\s*-\s+(.+)", s)
            if m:
                universe.append(m.group(1).strip().strip('"').strip("'"))
    if current_artifact:
        artifacts.append(current_artifact)
    return artifacts, universe, pre_cap_total


def verify_gpg_signature(file_path: Path, asc_path: Path, fingerprint: str) -> Tuple[bool, str]:
    """Verify detached GPG signature against expected fingerprint."""
    if not asc_path.exists():
        return False, f"missing .asc: {asc_path}"
    try:
        result = subprocess.run(
            ["gpg", "--status-fd", "1", "--verify", str(asc_path), str(file_path)],
            capture_output=True,
            text=True,
            timeout=10,
        )
    except (FileNotFoundError, subprocess.TimeoutExpired) as e:
        return False, f"gpg invocation failed: {e}"
    output = result.stdout + result.stderr
    if f"GOODSIG" in output and fingerprint.upper() in output.upper():
        return True, "verified"
    return False, f"signature verification failed: {output[:200]}"


def find_audit_events(audit_log: Path, action: str, wave_id: str, path: str) -> List[Dict]:
    if not audit_log.exists():
        return []
    matches: List[Dict] = []
    for line in audit_log.read_text(encoding="utf-8", errors="replace").splitlines():
        line = line.strip()
        if not line:
            continue
        try:
            ev = json.loads(line)
        except json.JSONDecodeError:
            continue
        if ev.get("action") == action and ev.get("wave_id") == wave_id and ev.get("path") == path:
            matches.append(ev)
    return matches


def main() -> int:
    p = argparse.ArgumentParser()
    p.add_argument("--manifests", type=Path, default=Path(".claude/plans/PLAN-084/manifests/"))
    p.add_argument("--staging", type=Path, default=Path(".claude/plans/PLAN-084/"))
    p.add_argument("--audit-log", type=Path, default=Path("~/.claude/projects/ceo-orchestration/audit-log.jsonl").expanduser())
    p.add_argument("--owner-fingerprint", default="0000000000000000000000000000000000000000")
    p.add_argument("--require-gpg", action="store_true", help="Require .asc per manifest (post-Owner-ceremony)")
    p.add_argument("--require-audit-event", action="store_true", help="Require wave_artifact_written audit cross-reference (post-Wave-0.5)")
    p.add_argument("--json", action="store_true")
    args = p.parse_args()

    if not args.manifests.exists():
        print(json.dumps({"error": f"manifests dir not found: {args.manifests}"}))
        return 3

    sha_mismatches: List[str] = []
    audit_event_missing: List[str] = []
    gpg_failures: List[str] = []
    all_hashes_match = True
    total_artifacts = 0

    for manifest_file in args.manifests.glob("*-manifest.sha256"):
        artifacts, universe, pre_cap_total = parse_manifest_yaml(manifest_file)
        wave_id = manifest_file.stem.replace("-manifest.sha256", "").split("/")[-1]
        for art in artifacts:
            total_artifacts += 1
            art_path = args.staging.parent.parent / art["path"] if art["path"].startswith(".claude") else args.staging / art["path"]
            if not art_path.exists():
                sha_mismatches.append(f"{art['path']}: file not found")
                all_hashes_match = False
                continue
            actual = sha256_file(art_path)
            expected = art.get("sha256", "")
            if actual != expected:
                sha_mismatches.append(f"{art['path']}: expected {expected[:12]} got {actual[:12]}")
                all_hashes_match = False
            if args.require_audit_event:
                events = find_audit_events(args.audit_log, "wave_artifact_written", wave_id, art["path"])
                if not events:
                    audit_event_missing.append(f"{wave_id}/{art['path']}: no wave_artifact_written event")
        # GPG verify
        if args.require_gpg:
            asc = manifest_file.with_suffix(".sha256.asc")
            if asc.exists():
                ok, reason = verify_gpg_signature(manifest_file, asc, args.owner_fingerprint)
                if not ok:
                    gpg_failures.append(f"{manifest_file.name}: {reason}")
            else:
                gpg_failures.append(f"{manifest_file.name}: missing .asc")

    result = {
        "manifests_count": len(list(args.manifests.glob("*-manifest.sha256"))),
        "total_artifacts": total_artifacts,
        "all_hashes_match": all_hashes_match,
        "sha_mismatches": sha_mismatches,
        "unauthorized_writes": audit_event_missing if args.require_audit_event else [],
        "gpg_failures": gpg_failures if args.require_gpg else [],
    }

    print(json.dumps(result, indent=2))
    halt = not all_hashes_match or bool(gpg_failures) or (args.require_audit_event and audit_event_missing)
    return 0 if not halt else 1


if __name__ == "__main__":
    sys.exit(main())
