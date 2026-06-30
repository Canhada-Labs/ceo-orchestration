#!/usr/bin/env python3
"""morning_ledger.py — PLAN-134 W4 proposal-queue bundle format v0.

Ratification Futures v0 (novel mechanism #3, PLAN-134 §Novel mechanisms):
a *bundle* packages one night's mechanical evidence (artifacts produced by
scripts that already exist) together with its *futures* — the checks the
bundle DECLARED at creation time and ran BEFORE presentation, exit codes
recorded — and a Merkle root binding artifacts + futures + recommendation.
What the Owner ratifies in the morning is exactly the bytes that were
verified at production time: the verify→ratify TOCTOU gap is closed by the
hash commitment, not by trust in the renderer.

Layout (ADR-001: runtime state lives OUTSIDE the repo):

    ~/.claude/ceo-runtime/
      proposal-queue/<bundle_id>/manifest.json
      proposal-queue/<bundle_id>/artifacts/<files>
      ratified/<YYYYMMDD>/<bundle_id>/...
      ratifications/ratification-<YYYYMMDD>.json[.asc]

Env overrides: CEO_RUNTIME_DIR (tests / adopters).

Stdlib-only, Python >= 3.9. Library + CLI (verify / render).
"""
from __future__ import annotations

import argparse
import hashlib
import json
import os
import re
import sys
import unicodedata
from dataclasses import dataclass, field
from datetime import datetime, timezone
from pathlib import Path
from typing import Any, Dict, List, Optional, Tuple

FORMAT_V0 = "ceo-proposal-bundle/v0"
VERDICTS = ("sign", "dont-sign", "info")
_BUNDLE_ID_RE = re.compile(r"^[A-Za-z0-9][A-Za-z0-9._-]{0,127}$")
_MAX_WHY_CHARS = 200
_MAX_ARTIFACT_BYTES = 5 * 1024 * 1024  # bound per-file hashing work


class FalseTrustError(Exception):
    """Raised when recorded hashes do not match recomputed reality.

    This is the W4 kill-criterion event ("any false-trust event") — callers
    MUST surface it loudly, never swallow it.
    """


def runtime_dir() -> Path:
    env = os.environ.get("CEO_RUNTIME_DIR")
    if env:
        return Path(env)
    return Path.home() / ".claude" / "ceo-runtime"


def queue_dir() -> Path:
    return runtime_dir() / "proposal-queue"


def ratified_dir() -> Path:
    return runtime_dir() / "ratified"


def ratifications_dir() -> Path:
    return runtime_dir() / "ratifications"


def _utcnow_iso() -> str:
    return datetime.now(timezone.utc).strftime("%Y-%m-%dT%H:%M:%SZ")


def _sha256_bytes(data: bytes) -> str:
    return hashlib.sha256(data).hexdigest()


def _sha256_file(path: Path) -> str:
    h = hashlib.sha256()
    with open(path, "rb") as fh:
        read = 0
        while True:
            chunk = fh.read(65536)
            if not chunk:
                break
            read += len(chunk)
            if read > _MAX_ARTIFACT_BYTES:
                raise ValueError(f"artifact exceeds {_MAX_ARTIFACT_BYTES} bytes: {path}")
            h.update(chunk)
    return h.hexdigest()


def _canonical_json(obj: Any) -> bytes:
    return json.dumps(obj, sort_keys=True, separators=(",", ":"), ensure_ascii=True).encode("ascii")


def merkle_root(leaves: List[str]) -> str:
    """Deterministic Merkle root over hex-digest leaves.

    Pairwise sha256 over the ascii hex concatenation; odd node promotes.
    Empty leaf list is a structural error (a bundle always has >= 1 leaf).
    """
    if not leaves:
        raise ValueError("merkle_root: empty leaf list")
    level = list(leaves)
    while len(level) > 1:
        nxt: List[str] = []
        for i in range(0, len(level) - 1, 2):
            nxt.append(_sha256_bytes((level[i] + level[i + 1]).encode("ascii")))
        if len(level) % 2 == 1:
            nxt.append(level[-1])
        level = nxt
    return level[0]


def compute_bundle_root(manifest: Dict[str, Any]) -> str:
    """Merkle root binding the WHOLE manifest (Codex R1 P1 fix).

    Leaves: one per artifact row (path AND sha256, canonical-json — a
    re-pathed artifact trips the root), + metadata leaf (format/bundle_id/
    title/producer/created_at — a retitled bundle trips the root), +
    futures leaf + recommendation leaf.
    """
    artifacts = sorted(manifest.get("artifacts", []), key=lambda a: a["path"])
    leaves = [_sha256_bytes(_canonical_json(row)) for row in artifacts]
    metadata = {
        k: manifest.get(k)
        for k in ("format", "bundle_id", "title", "producer", "created_at")
    }
    leaves.append(_sha256_bytes(_canonical_json(metadata)))
    leaves.append(_sha256_bytes(_canonical_json(manifest.get("futures", []))))
    leaves.append(_sha256_bytes(_canonical_json(manifest.get("recommendation", {}))))
    return merkle_root(leaves)


def sanitize_text(s: str, limit: int = _MAX_WHY_CHARS) -> str:
    """NFKC + control-char strip + length bound (ceo-boot Sec MF-4 discipline)."""
    s = unicodedata.normalize("NFKC", str(s))
    s = "".join(ch for ch in s if ch == " " or (ch.isprintable() and ch not in "\r\n\t"))
    return s[:limit]


@dataclass
class Future:
    """A declared mechanical check, run BEFORE presentation (G2 → exit code)."""

    name: str
    cmd: str
    exit_code: int
    ran_at: str
    duration_ms: int
    output_sha256: str

    def to_dict(self) -> Dict[str, Any]:
        return {
            "name": self.name,
            "cmd": self.cmd,
            "exit_code": int(self.exit_code),
            "ran_at": self.ran_at,
            "duration_ms": int(self.duration_ms),
            "output_sha256": self.output_sha256,
        }


@dataclass
class BundleSpec:
    bundle_id: str
    title: str
    producer: str
    artifacts: List[Tuple[str, bytes]] = field(default_factory=list)  # (relname, content)
    futures: List[Future] = field(default_factory=list)
    verdict: str = "info"
    why: str = ""


def create_bundle(spec: BundleSpec, root: Optional[Path] = None) -> Path:
    """Materialize a bundle into the proposal queue. Returns the bundle dir.

    Crash-safe (Codex R1 P2 fix): the bundle is assembled in a `.tmp-` dir
    and atomically renamed into place only AFTER manifest.json is fully
    written — a crash never leaves a manifest-less bundle dir at the final
    path, and `pending_bundles()` ignores `.tmp-*` by construction (it
    requires manifest.json AND the final name).
    """
    if not _BUNDLE_ID_RE.match(spec.bundle_id):
        raise ValueError(f"invalid bundle_id: {spec.bundle_id!r}")
    if spec.verdict not in VERDICTS:
        raise ValueError(f"invalid verdict: {spec.verdict!r}")
    qdir = (root or queue_dir())
    final_dir = qdir / spec.bundle_id
    if final_dir.exists():
        raise FileExistsError(f"bundle already exists: {final_dir}")
    bdir = qdir / f".tmp-{spec.bundle_id}-{os.getpid()}"
    art_dir = bdir / "artifacts"
    art_dir.mkdir(parents=True)

    artifact_rows: List[Dict[str, str]] = []
    for relname, content in spec.artifacts:
        rel = Path(relname)
        if rel.is_absolute() or ".." in rel.parts:
            raise ValueError(f"artifact path escapes bundle: {relname!r}")
        target = art_dir / rel
        target.parent.mkdir(parents=True, exist_ok=True)
        target.write_bytes(content)
        artifact_rows.append({"path": f"artifacts/{rel.as_posix()}", "sha256": _sha256_bytes(content)})

    manifest: Dict[str, Any] = {
        "format": FORMAT_V0,
        "bundle_id": spec.bundle_id,
        "title": sanitize_text(spec.title, 120),
        "producer": sanitize_text(spec.producer, 120),
        "created_at": _utcnow_iso(),
        "artifacts": sorted(artifact_rows, key=lambda a: a["path"]),
        "futures": [f.to_dict() for f in spec.futures],
        "recommendation": {
            "verdict": spec.verdict,
            "why": sanitize_text(spec.why),
        },
    }
    manifest["merkle_root"] = compute_bundle_root(manifest)
    mpath = bdir / "manifest.json"
    with open(mpath, "w", encoding="utf-8") as fh:
        fh.write(json.dumps(manifest, indent=2, sort_keys=True) + "\n")
        fh.flush()
        os.fsync(fh.fileno())
    try:
        os.rename(bdir, final_dir)
    except OSError as exc:
        raise FileExistsError(f"bundle landed concurrently: {final_dir} ({exc})")
    return final_dir


def load_manifest(bundle_dir: Path) -> Dict[str, Any]:
    mpath = bundle_dir / "manifest.json"
    data = json.loads(mpath.read_text(encoding="utf-8"))
    if data.get("format") != FORMAT_V0:
        raise ValueError(f"unknown bundle format: {data.get('format')!r}")
    return data


def verify_bundle(bundle_dir: Path, deep: bool = True) -> Dict[str, Any]:
    """Verify a bundle. deep=True re-hashes artifact bytes (ceremony mode);
    deep=False re-derives the Merkle root from recorded leaves only (fast
    ledger-render mode — full byte verification is the ceremony's job).

    Raises FalseTrustError on ANY mismatch (W4 kill-criterion event).
    """
    manifest = load_manifest(bundle_dir)
    if deep:
        art_root = (bundle_dir / "artifacts").resolve()
        for row in manifest.get("artifacts", []):
            rel = Path(row["path"])
            if rel.is_absolute() or ".." in rel.parts or rel.parts[:1] != ("artifacts",):
                raise FalseTrustError(f"{manifest['bundle_id']}: artifact path escapes bundle: {row['path']!r}")
            fpath = bundle_dir / rel
            # Codex R1 P1 fix — symlink escape: reject symlinks anywhere in
            # the artifact path and require the RESOLVED path to stay under
            # the resolved artifacts root (py3.9-compatible commonpath check).
            probe = bundle_dir
            for part in rel.parts:
                probe = probe / part
                if probe.is_symlink():
                    raise FalseTrustError(f"{manifest['bundle_id']}: symlink in artifact path: {row['path']!r}")
            resolved = fpath.resolve()
            if os.path.commonpath([str(art_root), str(resolved)]) != str(art_root):
                raise FalseTrustError(f"{manifest['bundle_id']}: artifact resolves outside bundle: {row['path']!r}")
            if not fpath.is_file():
                raise FalseTrustError(f"{manifest['bundle_id']}: missing artifact {row['path']}")
            actual = _sha256_file(fpath)
            if actual != row["sha256"]:
                raise FalseTrustError(
                    f"{manifest['bundle_id']}: artifact hash mismatch {row['path']} "
                    f"(recorded {row['sha256'][:12]}.., actual {actual[:12]}..)"
                )
    recomputed = compute_bundle_root(manifest)
    if recomputed != manifest.get("merkle_root"):
        raise FalseTrustError(
            f"{manifest['bundle_id']}: merkle root mismatch "
            f"(recorded {str(manifest.get('merkle_root'))[:12]}.., recomputed {recomputed[:12]}..)"
        )
    return manifest


def pending_bundles(root: Optional[Path] = None) -> List[Path]:
    qdir = root or queue_dir()
    if not qdir.is_dir():
        return []
    out = [
        p for p in sorted(qdir.iterdir())
        if not p.name.startswith(".") and (p / "manifest.json").is_file()
    ]
    return out


class runtime_lock:
    """Exclusive advisory flock over the runtime dir (Codex R1 P2 fix).

    Producer and ceremony both take this lock so a nightly run can never
    mutate the queue while a ceremony is mid-flight (and vice versa).
    Context manager; blocks until acquired. POSIX-only (darwin/linux),
    which matches the framework's supported platforms.
    """

    def __init__(self, root: Optional[Path] = None, blocking: bool = True):
        self._dir = root or runtime_dir()
        self._blocking = blocking
        self._fh = None

    def __enter__(self) -> "runtime_lock":
        import fcntl
        self._dir.mkdir(parents=True, exist_ok=True)
        self._fh = open(self._dir / ".lock", "a+")
        flags = fcntl.LOCK_EX if self._blocking else (fcntl.LOCK_EX | fcntl.LOCK_NB)
        try:
            fcntl.flock(self._fh.fileno(), flags)
        except OSError:
            self._fh.close()
            self._fh = None
            raise RuntimeError(
                "runtime em uso (cerimônia ou produtor em andamento) — tente de novo em instantes"
            )
        return self

    def __exit__(self, *exc) -> None:
        import fcntl
        if self._fh is not None:
            fcntl.flock(self._fh.fileno(), fcntl.LOCK_UN)
            self._fh.close()
            self._fh = None


_VERDICT_FOUNDER = {
    "sign": "ASSINAR",
    "dont-sign": "NAO ASSINAR",
    "info": "informativo",
}


def render_verified_ledger(manifests: List[Dict[str, Any]]) -> str:
    """Render the ceremony ledger from ALREADY-VERIFIED in-memory manifests.

    Codex R1 P1 fix: the ceremony must never re-read mutable disk between
    deep-verification and the Owner's decision — the decision surface IS
    the verified object set.
    """
    if not manifests:
        return "## Morning Ledger\n\nFila vazia — nada aguardando ratificação.\n"
    lines = [
        "## Morning Ledger — propostas aguardando sua ratificação",
        "",
        "| Proposta | Recomendação | Por quê | Checks |",
        "|---|---|---|---|",
    ]
    for m in manifests:
        checks = m.get("futures", [])
        ok = sum(1 for f in checks if f.get("exit_code") == 0)
        rec = m.get("recommendation", {})
        verdict = _VERDICT_FOUNDER.get(rec.get("verdict", "info"), "informativo")
        why = sanitize_text(rec.get("why", ""))
        title = sanitize_text(m.get("title", m.get("bundle_id", "?")), 60)
        lines.append(f"| {title} | **{verdict}** | {why} | {ok}/{len(checks)} ok |")
    lines.append("")
    lines.append("_verificação byte-a-byte concluída sobre exatamente estes conteúdos._")
    return "\n".join(lines) + "\n"


def render_ledger(root: Optional[Path] = None, deep: bool = False, max_bundles: int = 10) -> str:
    """Founder-language Morning Ledger: sign / don't sign / why, per bundle."""
    bundles = pending_bundles(root)
    if not bundles:
        return "## Morning Ledger\n\nFila vazia — nada aguardando ratificação.\n"
    lines = [
        "## Morning Ledger — propostas aguardando sua ratificação",
        "",
        "| Proposta | Recomendação | Por quê | Checks |",
        "|---|---|---|---|",
    ]
    shown = 0
    for bdir in bundles:
        if shown >= max_bundles:
            lines.append(f"| … +{len(bundles) - shown} proposta(s) | | fila truncada em {max_bundles} | |")
            break
        try:
            m = verify_bundle(bdir, deep=deep)
            checks = m.get("futures", [])
            ok = sum(1 for f in checks if f.get("exit_code") == 0)
            rec = m.get("recommendation", {})
            verdict = _VERDICT_FOUNDER.get(rec.get("verdict", "info"), "informativo")
            why = sanitize_text(rec.get("why", ""))
            title = sanitize_text(m.get("title", bdir.name), 60)
            lines.append(f"| {title} | **{verdict}** | {why} | {ok}/{len(checks)} ok |")
        except FalseTrustError as exc:
            lines.append(
                f"| {sanitize_text(bdir.name, 60)} | **NAO ASSINAR** | "
                f"FALSE-TRUST: {sanitize_text(str(exc), 120)} | — |"
            )
        except Exception as exc:  # noqa: BLE001 — render must not crash the caller
            lines.append(
                f"| {sanitize_text(bdir.name, 60)} | **NAO ASSINAR** | "
                f"manifest ilegível: {sanitize_text(str(exc), 100)} | — |"
            )
        shown += 1
    mode = "verificação completa (bytes)" if deep else "verificação rápida (manifest); bytes na cerimônia"
    lines.append("")
    lines.append(f"_{mode}. Ratificar: `python3 .claude/scripts/morning-ceremony.py`_")
    return "\n".join(lines) + "\n"


def main(argv: List[str]) -> int:
    ap = argparse.ArgumentParser(description="proposal-queue bundle format v0 (PLAN-134 W4)")
    sub = ap.add_subparsers(dest="cmd")
    p_verify = sub.add_parser("verify", help="deep-verify one bundle or the whole queue")
    p_verify.add_argument("bundle", nargs="?", help="bundle id (default: all pending)")
    sub.add_parser("render", help="render the Morning Ledger (fast mode)")
    args = ap.parse_args(argv)
    if not args.cmd:
        ap.print_help()
        return 1

    if args.cmd == "render":
        sys.stdout.write(render_ledger())
        return 0
    # verify
    targets = [queue_dir() / args.bundle] if args.bundle else pending_bundles()
    if not targets:
        print("queue empty")
        return 0
    rc = 0
    for bdir in targets:
        try:
            m = verify_bundle(bdir, deep=True)
            print(f"OK   {m['bundle_id']}  root={m['merkle_root'][:16]}..")
        except FalseTrustError as exc:
            print(f"FALSE-TRUST  {bdir.name}: {exc}")
            rc = 2
        except Exception as exc:  # noqa: BLE001
            print(f"ERROR  {bdir.name}: {exc}")
            rc = max(rc, 1)
    return rc


if __name__ == "__main__":
    raise SystemExit(main(sys.argv[1:]))
