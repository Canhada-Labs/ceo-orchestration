#!/usr/bin/env python3
"""squad-export.py — Package a squad bundle into a signed tarball.

PLAN-011 Phase 12 (Agent Architect + Staff Security Engineer). Creates a
publishable ``squad-<slug>-v<version>.tar.gz`` from an existing squad
under ``.claude/skills/domains/<slug>/`` and, if ``--sign-with`` is given,
produces a detached ASCII-armored signature at ``<out>.sig``.

## Contract (per ADR-039 / SPEC/v1/squad-manifest.schema)

Tarball layout::

    <slug>/
        manifest.json            # machine-readable manifest (stdlib-only JSON)
        manifest.yaml            # human-readable mirror (optional, best-effort)
        team-personas.md
        pitfalls.yaml
        task-chains.yaml
        skills/<skill-id>/SKILL.md
        examples/PLAN-EXAMPLE.md   # if present

``manifest.json`` fields::

    {
        "squad_name": <slug>,
        "version": "1.0.0",
        "created_at": <ISO8601 UTC>,
        "squad_contract": "v1",
        "files": [<relative paths>],
        "files_sha256": {<rel>: <hex>}
    }

## Security rationale

Consensus CR2 demands signature verification BEFORE any parse on import.
Export writes the tarball deterministically, computes per-file SHA-256,
and offers detached-signature production so the publisher can sign the
archive bytes (not the manifest, which is inside the tarball).

Exit codes:
    0 — success, or ``CEO_SOTA_DISABLE=1`` no-op.
    2 — usage error (missing squad, write failure).
"""

from __future__ import annotations

import argparse
import hashlib
import io
import json
import os
import subprocess
import sys
import tarfile
from datetime import datetime, timezone
from pathlib import Path
from typing import Dict, List, Optional, Tuple


DEFAULT_VERSION = "1.0.0"
SQUAD_CONTRACT_VERSION = "v1"

# Files that constitute a squad bundle per ADR-009.
_CORE_FILES = (
    "team-personas.md",
    "pitfalls.yaml",
    "task-chains.yaml",
)
# Optional top-level extras.
_OPTIONAL_TOP = (
    "frontend-team-personas.md",
    "ORG_CHART.md",
)


def _utc_now_iso() -> str:
    """Return current UTC time in ISO 8601 second-precision (Z suffix)."""
    return datetime.now(timezone.utc).strftime("%Y-%m-%dT%H:%M:%SZ")


def _sha256_file(path: Path) -> str:
    """Return lowercase hex SHA-256 digest of file contents."""
    h = hashlib.sha256()
    with path.open("rb") as f:
        for chunk in iter(lambda: f.read(65536), b""):
            h.update(chunk)
    return h.hexdigest()


def _sha256_bytes(data: bytes) -> str:
    return hashlib.sha256(data).hexdigest()


def _default_repo_root() -> Path:
    """Resolve the ceo-orchestration repo root (parents[2] from this file)."""
    return Path(__file__).resolve().parents[2]


def _discover_squad_files(squad_dir: Path) -> List[Path]:
    """Return the list of files that belong in the tarball (sorted)."""
    out: List[Path] = []

    # Core files (mandatory to be discoverable; we don't hard-require all
    # here — validate-squad-contract.py is the authority for minimums).
    for name in _CORE_FILES:
        p = squad_dir / name
        if p.is_file():
            out.append(p)

    # Optional top-level extras.
    for name in _OPTIONAL_TOP:
        p = squad_dir / name
        if p.is_file():
            out.append(p)

    # skills/<skill-id>/SKILL.md (+ any other files under skills/<id>/ —
    # future-proof for supplemental per-skill docs).
    skills_dir = squad_dir / "skills"
    if skills_dir.is_dir():
        for skill_sub in sorted(skills_dir.iterdir()):
            if not skill_sub.is_dir():
                continue
            for fp in sorted(skill_sub.rglob("*")):
                if fp.is_file():
                    out.append(fp)

    # examples/ (optional)
    examples_dir = squad_dir / "examples"
    if examples_dir.is_dir():
        for fp in sorted(examples_dir.rglob("*")):
            if fp.is_file():
                out.append(fp)

    return out


def _build_manifest(
    squad_dir: Path,
    version: str,
    files: List[Path],
) -> Tuple[Dict, Dict[str, str]]:
    """Produce (manifest_dict, files_sha256_map).

    Relative paths are rooted at ``<slug>/`` (the arcname prefix used
    during tarball packing).
    """
    slug = squad_dir.name
    rels: List[str] = []
    hashes: Dict[str, str] = {}
    for fp in files:
        rel = fp.relative_to(squad_dir).as_posix()
        arcname = f"{slug}/{rel}"
        rels.append(arcname)
        hashes[arcname] = _sha256_file(fp)

    manifest = {
        "squad_name": slug,
        "version": version,
        "created_at": _utc_now_iso(),
        "squad_contract": SQUAD_CONTRACT_VERSION,
        "files": sorted(rels),
        "files_sha256": dict(sorted(hashes.items())),
    }
    return manifest, hashes


def _render_manifest_yaml(manifest: Dict) -> str:
    """Render a minimal YAML representation of the manifest.

    We do NOT depend on PyYAML (stdlib-only). This is a human mirror; the
    machine-readable authority is ``manifest.json``.
    """
    lines: List[str] = []
    lines.append(f"squad_name: {manifest['squad_name']}")
    lines.append(f"version: {manifest['version']}")
    lines.append(f'created_at: "{manifest["created_at"]}"')
    lines.append(f"squad_contract: {manifest['squad_contract']}")
    lines.append("files:")
    for rel in manifest["files"]:
        lines.append(f"  - {rel}")
    lines.append("files_sha256:")
    for rel, digest in manifest["files_sha256"].items():
        lines.append(f'  "{rel}": {digest}')
    return "\n".join(lines) + "\n"


def _add_bytes_to_tar(tar: tarfile.TarFile, arcname: str, data: bytes) -> None:
    """Add in-memory bytes as a regular file entry."""
    info = tarfile.TarInfo(name=arcname)
    info.size = len(data)
    info.mtime = 0  # deterministic
    info.mode = 0o600
    info.type = tarfile.REGTYPE
    info.uid = 0
    info.gid = 0
    info.uname = ""
    info.gname = ""
    tar.addfile(info, io.BytesIO(data))


def _add_file_to_tar(
    tar: tarfile.TarFile,
    squad_dir: Path,
    file_path: Path,
    slug: str,
) -> None:
    """Add a real filesystem file to the tarball, stripped of identifying metadata."""
    rel = file_path.relative_to(squad_dir).as_posix()
    arcname = f"{slug}/{rel}"
    info = tar.gettarinfo(str(file_path), arcname=arcname)
    if info is None:
        return
    # Strip metadata for determinism / privacy.
    info.mtime = 0
    info.mode = 0o600 if info.isfile() else 0o700
    info.uid = 0
    info.gid = 0
    info.uname = ""
    info.gname = ""
    if info.isfile():
        with file_path.open("rb") as f:
            tar.addfile(info, f)
    else:
        # Skip non-regular entries in export.
        return


def _sign_detached(
    tarball_path: Path,
    fingerprint: str,
    *,
    gnupg_home: Optional[Path] = None,
    passphrase: str = "",
) -> Path:
    """Invoke gpg to produce an armored detached signature.

    Returns the .sig path. Raises RuntimeError on failure.
    """
    sig_path = Path(str(tarball_path) + ".sig")
    if sig_path.exists():
        sig_path.unlink()

    env = dict(os.environ)
    cmd: List[str] = ["gpg"]
    if gnupg_home is not None:
        cmd.extend(["--homedir", str(gnupg_home)])
        env["GNUPGHOME"] = str(gnupg_home)
    cmd.extend([
        "--batch", "--no-tty",
        "--pinentry-mode", "loopback",
        "--passphrase", passphrase,
        "--local-user", fingerprint,
        "--armor",
        "--detach-sign",
        "--output", str(sig_path),
        str(tarball_path),
    ])
    proc = subprocess.run(
        cmd, capture_output=True, text=True, timeout=30, env=env,
    )
    if proc.returncode != 0 or not sig_path.is_file():
        raise RuntimeError(
            f"gpg --detach-sign failed: rc={proc.returncode} stderr={proc.stderr[:400]}"
        )
    return sig_path


def export_squad(
    squad_dir: Path,
    output: Path,
    *,
    version: str = DEFAULT_VERSION,
    sign_with: Optional[str] = None,
    gnupg_home: Optional[Path] = None,
    passphrase: str = "",
) -> Tuple[Path, Optional[Path], str]:
    """Package a squad directory into a tarball.

    Returns (tarball_path, sig_path_or_None, manifest_sha256).

    Raises:
        FileNotFoundError if ``squad_dir`` is not a directory.
        RuntimeError if tarball write or signing fails.
    """
    if not squad_dir.is_dir():
        raise FileNotFoundError(f"squad directory not found: {squad_dir}")

    slug = squad_dir.name
    files = _discover_squad_files(squad_dir)
    if not files:
        raise RuntimeError(
            f"squad {slug} contains no files under {squad_dir} — nothing to export"
        )

    manifest, _hashes = _build_manifest(squad_dir, version, files)
    manifest_json_bytes = (
        json.dumps(manifest, indent=2, sort_keys=True, ensure_ascii=False) + "\n"
    ).encode("utf-8")
    manifest_yaml_bytes = _render_manifest_yaml(manifest).encode("utf-8")
    manifest_sha256 = _sha256_bytes(manifest_json_bytes)

    output.parent.mkdir(parents=True, exist_ok=True)

    # Write tarball deterministically via gzip with mtime=0.
    # tarfile.open mode "w:gz" compresses with a timestamp in the gzip
    # header. We open with explicit gzip fileobj to pin mtime=0.
    import gzip

    with open(output, "wb") as raw:
        with gzip.GzipFile(
            filename="", mode="wb", fileobj=raw, mtime=0, compresslevel=9
        ) as gz:
            with tarfile.open(mode="w", fileobj=gz) as tar:
                # 1. manifest.json at <slug>/manifest.json
                _add_bytes_to_tar(tar, f"{slug}/manifest.json", manifest_json_bytes)
                # 2. manifest.yaml mirror
                _add_bytes_to_tar(tar, f"{slug}/manifest.yaml", manifest_yaml_bytes)
                # 3. real files
                for fp in files:
                    _add_file_to_tar(tar, squad_dir, fp, slug)

    sig_path: Optional[Path] = None
    if sign_with:
        sig_path = _sign_detached(
            output,
            sign_with,
            gnupg_home=gnupg_home,
            passphrase=passphrase,
        )

    return output, sig_path, manifest_sha256


def _default_output_path(squad_dir: Path, version: str) -> Path:
    slug = squad_dir.name
    return Path.cwd() / f"squad-{slug}-v{version}.tar.gz"


def main(argv: Optional[List[str]] = None) -> int:
    """CLI entrypoint — export a signed squad bundle tarball."""
    # Kill-switch per debate S4.
    if os.environ.get("CEO_SOTA_DISABLE") == "1":
        sys.stdout.write(
            "squad-export: CEO_SOTA_DISABLE=1 — marketplace disabled (noop)\n"
        )
        return 0

    parser = argparse.ArgumentParser(
        prog="squad-export",
        description="Package a squad into a signed tarball for the marketplace.",
    )
    parser.add_argument(
        "--squad",
        required=True,
        help="Squad slug (looked up under .claude/skills/domains/<slug>/) "
        "OR an absolute path to the squad directory.",
    )
    parser.add_argument(
        "--output",
        default=None,
        help="Output tarball path. Default: ./squad-<slug>-v<version>.tar.gz",
    )
    parser.add_argument(
        "--version",
        default=DEFAULT_VERSION,
        help=f"Version string embedded in manifest. Default: {DEFAULT_VERSION}",
    )
    parser.add_argument(
        "--sign-with",
        default=None,
        help="GPG fingerprint / key-id to sign the tarball with. Optional.",
    )
    parser.add_argument(
        "--gnupg-home",
        default=None,
        help="Override GNUPGHOME (points gpg at a specific keyring). "
        "Used by tests with ephemeral keyring fixture.",
    )
    parser.add_argument(
        "--repo-root",
        default=None,
        help="Override repo root (used by tests).",
    )

    try:
        args = parser.parse_args(argv)
    except SystemExit as exc:
        return 2 if exc.code else 0

    repo_root = Path(args.repo_root).expanduser() if args.repo_root else _default_repo_root()

    # Resolve squad directory — accept slug or absolute path.
    squad_arg = Path(args.squad).expanduser()
    if squad_arg.is_absolute() and squad_arg.is_dir():
        squad_dir = squad_arg
    else:
        squad_dir = repo_root / ".claude" / "skills" / "domains" / args.squad
        if not squad_dir.is_dir():
            sys.stderr.write(
                f"error: squad not found: tried {squad_dir}\n"
                f"       (also not a directory: {squad_arg})\n"
            )
            return 2

    output = (
        Path(args.output).expanduser()
        if args.output
        else _default_output_path(squad_dir, args.version)
    )

    gnupg_home = Path(args.gnupg_home).expanduser() if args.gnupg_home else None

    try:
        tar_path, sig_path, manifest_sha256 = export_squad(
            squad_dir,
            output,
            version=args.version,
            sign_with=args.sign_with,
            gnupg_home=gnupg_home,
        )
    except (FileNotFoundError, RuntimeError) as exc:
        sys.stderr.write(f"error: {exc}\n")
        return 2

    sys.stdout.write(f"tarball: {tar_path}\n")
    if sig_path:
        sys.stdout.write(f"signature: {sig_path}\n")
    else:
        sys.stdout.write("signature: (unsigned — pass --sign-with <fpr> for marketplace)\n")
    sys.stdout.write(f"manifest_sha256: {manifest_sha256}\n")
    sys.stdout.write(f"squad_name: {squad_dir.name}\n")
    sys.stdout.write(f"version: {args.version}\n")
    return 0


if __name__ == "__main__":  # pragma: no cover
    sys.exit(main())
