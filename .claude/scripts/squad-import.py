#!/usr/bin/env python3
"""squad-import.py — Verify + install a signed squad tarball.

PLAN-011 Phase 12 (Agent Architect + Staff Security Engineer). Honors
consensus CR2: sig-before-parse, filesystem-safe extraction, allowlist,
revocation.

## Validation order (STRICT — must not change without ADR amendment)

    1. **Signature verification** — gpg --verify on (tarball bytes, detached sig).
       NOTHING is parsed from the tarball until this passes. Exit 2 on failure.
    2. **Size cap** — reject archives > CEO_SQUAD_MAX_BYTES (default 5 MiB).
       Exit 2 on failure.
    3. **Allowlist** — ``--source`` URI must appear in
       ``.claude/settings.json`` ``squad_allowlist`` list. Empty default =
       import refused. Exit 2.
    4. **Revocation** — compare manifest SHA-256 against
       ``.claude/squad-revocations.jsonl``. Exit 2 on match.
    5. **Path-traversal refusal** — iterate tarfile members BEFORE
       extraction; refuse symlinks, hardlinks, absolute paths, or any
       name containing ``..``. Exit 2 on first bad entry.
    6. **Extract** — write to a tmpdir, then atomic rename into
       ``.claude/skills/domains/<slug>/``. Collision requires ``--force``.
    7. **Contract check** — subprocess-invoke
       ``validate-squad-contract.py``. On failure, rollback + exit 3.
    8. **Audit** — emit ``squad_imported`` event with manifest_sha256 +
       signer_fingerprint + source.

## Exit codes

    0 — imported cleanly (or CEO_SOTA_DISABLE=1 noop).
    1 — usage / IO error.
    2 — validation failure (signature / size / allowlist / revocation /
        path-traversal). Distinguishable via stderr prefix.
    3 — validate-squad-contract.py rejected the extracted squad.
"""

from __future__ import annotations

import argparse
import hashlib
import json
import os
import shutil
import subprocess
import sys
import tarfile
import tempfile
from pathlib import Path
from typing import List, Optional, Tuple

# Resolve _lib import for audit_emit.
_HERE = Path(__file__).resolve()
REPO_ROOT = _HERE.parents[2]
HOOKS_DIR = REPO_ROOT / ".claude" / "hooks"
if str(HOOKS_DIR) not in sys.path:
    sys.path.insert(0, str(HOOKS_DIR))

try:
    from _lib.audit_emit import emit_squad_imported  # type: ignore
except Exception:  # pragma: no cover — fail-open for audit, not for security
    emit_squad_imported = None  # type: ignore


DEFAULT_MAX_BYTES = 5 * 1024 * 1024  # 5 MiB (CR2)
SQUAD_CONTRACT_VERSION = "v1"


# --- validation errors ------------------------------------------------------


class ValidationError(Exception):
    """Stage-2 validation error (signature / size / allowlist / revocation /
    path-traversal). Stringifies to a short machine-readable reason code."""

    def __init__(self, reason_code: str, message: str = "") -> None:
        self.reason_code = reason_code
        super().__init__(message or reason_code)


class ContractError(Exception):
    """Raised when validate-squad-contract.py rejects the extracted squad."""

    def __init__(self, stderr: str) -> None:
        self.stderr = stderr
        super().__init__(stderr)


# --- step helpers -----------------------------------------------------------


def _read_bytes(path: Path, max_bytes: int) -> bytes:
    """Read a file fully into memory, refusing oversize up-front.

    We stat() first so an oversized input is rejected before any read.
    """
    if not path.is_file():
        raise ValidationError("io_error", f"file not found: {path}")
    size = path.stat().st_size
    if size > max_bytes:
        raise ValidationError(
            "oversized",
            f"tarball size {size} exceeds cap {max_bytes}",
        )
    return path.read_bytes()


def _sha256_bytes(data: bytes) -> str:
    return hashlib.sha256(data).hexdigest()


def _gpg_verify(
    tarball_path: Path,
    signature_path: Path,
    *,
    keyring_home: Optional[Path] = None,
) -> Tuple[bool, str, str]:
    """Invoke ``gpg --verify`` on the DETACHED signature and the tarball.

    Critical: we pass the TARBALL PATH, not an opened tarfile. This is
    the sig-before-parse guarantee.

    Fingerprint extraction (F9 — parity with ``_lib/gpg_verify.py``):
    the ``VALIDSIG`` status line carries two distinct fingerprints —

      * 3rd field (``parts[2]``)  = the key that MADE the signature
        (the signing **subkey** for a best-practice primary+subkey
        setup; the sole key for a single-key setup).
      * last field (``parts[-1]``) = the **primary**-key fingerprint.

    The returned ``signer_fingerprint`` is the **primary** fpr (the last
    VALIDSIG field) when present, falling back to the signing-(sub)key
    fpr only when the line is too short to carry a primary. Keying on
    ``parts[2]`` alone (the pre-F9 behaviour) reported the signing-subkey
    fpr, which diverges from the primary that an allowlist/keyring would
    typically hold — the same primary-vs-subkey blind spot fixed in
    ``_lib/gpg_verify.py`` (F1). For a single-key setup the two fields are
    identical, so behaviour is unchanged there.

    GOODSIG and VALIDSIG are bound (mirrors F1/M7): a fingerprint is only
    surfaced when a GOODSIG line was also seen on the same status stream.

    Returns (ok, signer_fingerprint, stderr_snippet).
    """
    gpg_bin = shutil_which_gpg()
    if not gpg_bin:
        return False, "", "gpg binary not found on PATH"

    env = dict(os.environ)
    if keyring_home is not None:
        env["GNUPGHOME"] = str(keyring_home)

    cmd = [
        gpg_bin,
        "--batch", "--no-tty",
        "--status-fd", "1",
        "--verify",
        str(signature_path),
        str(tarball_path),
    ]
    proc = subprocess.run(
        cmd, capture_output=True, text=True, timeout=30, env=env,
    )
    fpr = ""
    good = False
    for line in proc.stdout.splitlines():
        if line.startswith("[GNUPG:] GOODSIG"):
            good = True
        elif line.startswith("[GNUPG:] VALIDSIG"):
            parts = line.split()
            if len(parts) >= 3:
                # parts[-1] = primary fpr; parts[2] = signing-(sub)key fpr.
                # Prefer the primary; fall back to the signing key only if
                # the line is too short to carry a separate primary field.
                fpr = parts[-1] if len(parts) > 3 else parts[2]
    # Bind GOODSIG <-> VALIDSIG: never surface a fpr without a GOODSIG.
    if not good:
        fpr = ""
    if proc.returncode != 0:
        return False, fpr, proc.stderr[:300]
    return (good and bool(fpr)), fpr, ""


def shutil_which_gpg() -> Optional[str]:
    """Resolve gpg (or gpg2) from PATH."""
    import shutil as _shutil

    return _shutil.which("gpg") or _shutil.which("gpg2")


def _load_allowlist(settings_path: Path) -> List[str]:
    """Read ``squad_allowlist`` from ``.claude/settings.json``.

    Missing file / missing key / wrong type = empty list (secure default).
    """
    if not settings_path.is_file():
        return []
    try:
        # settings.json contains comments (``_comment`` keys) but is
        # otherwise valid JSON.
        data = json.loads(settings_path.read_text(encoding="utf-8"))
    except Exception:
        return []
    val = data.get("squad_allowlist") if isinstance(data, dict) else None
    if not isinstance(val, list):
        return []
    return [str(v) for v in val]


def _load_revocations(ledger_path: Path) -> List[dict]:
    """Read revocation ledger; one JSON object per line. Lines starting with
    ``#`` are comments. Malformed lines skipped silently (fail-open on
    observability but NOT on security — revocation match is still checked
    against every valid entry)."""
    if not ledger_path.is_file():
        return []
    out: List[dict] = []
    try:
        for raw in ledger_path.read_text(encoding="utf-8").splitlines():
            line = raw.strip()
            if not line or line.startswith("#"):
                continue
            try:
                obj = json.loads(line)
            except Exception:
                continue
            if isinstance(obj, dict):
                out.append(obj)
    except OSError:
        return []
    return out


def _check_allowlist(source: str, allowlist: List[str]) -> None:
    """Raise ValidationError("not_in_allowlist") if source not listed."""
    if source not in allowlist:
        raise ValidationError(
            "not_in_allowlist",
            f"source {source!r} not in allowlist (size={len(allowlist)})",
        )


def _check_revocation(manifest_sha256: str, revocations: List[dict]) -> None:
    """Raise ValidationError("revoked") if manifest SHA appears in ledger."""
    for entry in revocations:
        if str(entry.get("manifest_sha256", "")).lower() == manifest_sha256.lower():
            raise ValidationError(
                "revoked",
                f"manifest_sha256 {manifest_sha256[:12]}... is in revocation ledger",
            )


def _iter_member_paths(member_name: str) -> List[str]:
    """Split a tar member name into path components for traversal checks."""
    # Tar names use "/" regardless of host OS. Also split on OS separator
    # as defense-in-depth (CR2).
    parts: List[str] = []
    for chunk in member_name.split("/"):
        for sub in chunk.split(os.sep):
            if sub != "":
                parts.append(sub)
    return parts


def _refuse_bad_members(tar: tarfile.TarFile) -> None:
    """Walk every member once BEFORE extraction; refuse unsafe entries.

    Per CR2: no symlinks, no hardlinks, no absolute paths, no ``..``.
    First bad entry triggers ValidationError with reason_code
    "symlink_refused" / "path_traversal".
    """
    for member in tar.getmembers():
        if member.issym():
            raise ValidationError(
                "symlink_refused",
                f"member {member.name!r} is a symlink",
            )
        if member.islnk():
            raise ValidationError(
                "symlink_refused",
                f"member {member.name!r} is a hardlink",
            )
        if member.isdev() or member.ischr() or member.isblk() or member.isfifo():
            raise ValidationError(
                "symlink_refused",
                f"member {member.name!r} is a special device/fifo",
            )
        name = member.name
        if not name:
            raise ValidationError("path_traversal", "empty member name")
        if name.startswith("/") or (os.sep != "/" and name.startswith(os.sep)):
            raise ValidationError(
                "path_traversal",
                f"member {name!r} uses an absolute path",
            )
        parts = _iter_member_paths(name)
        if any(p == ".." for p in parts):
            raise ValidationError(
                "path_traversal",
                f"member {name!r} contains ``..``",
            )


def _find_manifest_in_tar(tar: tarfile.TarFile) -> Tuple[Optional[str], Optional[bytes]]:
    """Locate ``<slug>/manifest.json`` inside the tar. Returns (slug, bytes) or (None, None)."""
    for member in tar.getmembers():
        if not member.isfile():
            continue
        name = member.name
        if name.endswith("/manifest.json"):
            # First component is the slug.
            parts = name.split("/")
            if len(parts) == 2:
                slug = parts[0]
                f = tar.extractfile(member)
                if f is None:
                    return None, None
                return slug, f.read()
    return None, None


def _extract_to(tar: tarfile.TarFile, dest_root: Path) -> None:
    """Extract every regular file to ``dest_root`` (which already passed
    traversal checks). We do NOT use tar.extractall to avoid its historic
    CVE surface; we hand-extract each regular file."""
    for member in tar.getmembers():
        if not member.isfile() and not member.isdir():
            # Should have been blocked by _refuse_bad_members; defense-in-depth.
            continue
        target = dest_root / member.name
        # Belt-and-suspenders: ensure the resolved path is still inside dest_root.
        try:
            target_resolved = target.resolve()
            dest_resolved = dest_root.resolve()
            target_resolved.relative_to(dest_resolved)
        except (ValueError, OSError):
            raise ValidationError(
                "path_traversal",
                f"resolved path escapes dest: {member.name!r}",
            )
        if member.isdir():
            target.mkdir(parents=True, exist_ok=True)
            continue
        target.parent.mkdir(parents=True, exist_ok=True)
        src = tar.extractfile(member)
        if src is None:
            continue
        with target.open("wb") as dst:
            shutil.copyfileobj(src, dst)
        try:
            os.chmod(target, 0o600)
        except OSError:
            pass


def _invoke_contract_validator(
    squad_dir: Path,
    *,
    validator_path: Optional[Path] = None,
    core_skills_dir: Optional[Path] = None,
) -> Tuple[bool, str]:
    """Run ``validate-squad-contract.py --squad <path>``.

    Returns (ok, stderr_snippet).
    """
    if validator_path is None:
        validator_path = (
            REPO_ROOT / ".claude" / "scripts" / "validate-squad-contract.py"
        )
    if not validator_path.is_file():
        return False, f"validator not found: {validator_path}"
    cmd = [
        sys.executable,
        str(validator_path),
        "--squad",
        str(squad_dir),
    ]
    if core_skills_dir is not None:
        cmd.extend(["--core-skills", str(core_skills_dir)])
    # Pass env explicitly so the validator's Python sees the same
    # site-packages / PYTHONPATH the caller has (PyYAML dependency).
    proc = subprocess.run(
        cmd, capture_output=True, text=True, timeout=30, env=dict(os.environ),
    )
    return (proc.returncode == 0), (proc.stderr or "")[:600]


# --- public API -------------------------------------------------------------


def _verify_signature_and_size(
    tarball_path: Path,
    signature_path: Path,
    max_bytes: int,
    keyring_home: Optional[Path],
) -> Tuple[bytes, str]:
    """Step 1-2: GPG signature verification + size cap. Returns (bytes, fpr)."""
    tarball_bytes = _read_bytes(tarball_path, max_bytes)

    if not signature_path.is_file():
        raise ValidationError(
            "signature_invalid",
            f"detached signature not found: {signature_path}",
        )
    sig_ok, signer_fpr, gpg_stderr = _gpg_verify(
        tarball_path, signature_path, keyring_home=keyring_home
    )
    if not sig_ok:
        raise ValidationError(
            "signature_invalid",
            f"gpg --verify failed: {gpg_stderr[:200]}",
        )

    if len(tarball_bytes) > max_bytes:
        raise ValidationError(
            "oversized",
            f"tarball size {len(tarball_bytes)} exceeds cap {max_bytes}",
        )
    return tarball_bytes, signer_fpr


def _parse_and_check_manifest(
    tar: tarfile.TarFile,
    revocations_path: Path,
) -> Tuple[str, str]:
    """Step 4-5 inner: find manifest, parse, revocation-check. Returns (slug, sha)."""
    slug, manifest_bytes = _find_manifest_in_tar(tar)
    if not slug or not manifest_bytes:
        raise ValidationError(
            "malformed_manifest",
            "tarball does not contain <slug>/manifest.json",
        )
    try:
        manifest = json.loads(manifest_bytes)
    except Exception as e:
        raise ValidationError(
            "malformed_manifest",
            f"manifest.json is not valid JSON: {e}",
        )
    if not isinstance(manifest, dict):
        raise ValidationError(
            "malformed_manifest",
            "manifest.json is not a JSON object",
        )
    if manifest.get("squad_contract") != SQUAD_CONTRACT_VERSION:
        raise ValidationError(
            "malformed_manifest",
            f"unsupported squad_contract: {manifest.get('squad_contract')!r}",
        )

    manifest_sha256 = _sha256_bytes(manifest_bytes)
    revocations = _load_revocations(revocations_path)
    _check_revocation(manifest_sha256, revocations)

    if manifest.get("squad_name") and manifest["squad_name"] != slug:
        raise ValidationError(
            "malformed_manifest",
            f"squad_name {manifest['squad_name']!r} != tar slug {slug!r}",
        )
    return slug, manifest_sha256


def _install_staged_squad(
    staging: Path,
    slug: str,
    dest_root: Path,
    force: bool,
) -> Tuple[Path, Optional[Path]]:
    """Move staged squad → final dest_root; return (final_path, backup_path)."""
    staged_squad = staging / slug
    if not staged_squad.is_dir():
        raise ValidationError(
            "malformed_manifest",
            f"extracted tree does not contain expected directory: {slug}",
        )

    final_squad = dest_root / slug
    backup: Optional[Path] = None
    if final_squad.exists():
        if not force:
            raise FileExistsError(
                f"squad already installed: {final_squad}. "
                "Re-run with --force to overwrite (audit-logged)."
            )
        backup_dir = Path(tempfile.mkdtemp(prefix=f"squad-backup-{slug}-"))
        shutil.move(str(final_squad), str(backup_dir / slug))
        backup = backup_dir

    dest_root.mkdir(parents=True, exist_ok=True)
    shutil.move(str(staged_squad), str(final_squad))
    return final_squad, backup


def _validate_or_rollback(
    final_squad: Path,
    slug: str,
    backup: Optional[Path],
    validator_path: Optional[Path],
    core_skills_dir: Optional[Path],
) -> None:
    """Step 7: run contract validator; rollback + raise ContractError on fail."""
    ok, stderr_snip = _invoke_contract_validator(
        final_squad,
        validator_path=validator_path,
        core_skills_dir=core_skills_dir,
    )
    if not ok:
        try:
            shutil.rmtree(final_squad)
        except OSError:
            pass
        if backup is not None and (backup / slug).exists():
            shutil.move(str(backup / slug), str(final_squad))
        raise ContractError(stderr_snip)

    if backup is not None:
        try:
            shutil.rmtree(backup)
        except OSError:
            pass


def import_squad(
    tarball_path: Path,
    signature_path: Path,
    source: str,
    *,
    dest_root: Path,
    settings_path: Path,
    revocations_path: Path,
    max_bytes: int = DEFAULT_MAX_BYTES,
    keyring_home: Optional[Path] = None,
    force: bool = False,
    validator_path: Optional[Path] = None,
    core_skills_dir: Optional[Path] = None,
) -> Tuple[str, str, str]:
    """Run the full import pipeline.

    Orchestrator over (1) :func:`_verify_signature_and_size` — step 1-2,
    (2) allowlist check, (3) :func:`_parse_and_check_manifest` — step
    4-5, (4) extract + :func:`_install_staged_squad` — step 6, and
    (5) :func:`_validate_or_rollback` — step 7. PLAN-023 Phase E
    decomposition preserves the sig-before-parse ORDER invariant and
    all existing test behavior byte-identical.

    Returns (slug, manifest_sha256, signer_fingerprint) on success.

    Raises:
        ValidationError on any stage 1-5 failure.
        ContractError on stage 7 failure (post-extraction rollback applied).
        FileExistsError on collision without force=True.
    """
    # STEP 1-2: signature + size
    _tarball_bytes, signer_fpr = _verify_signature_and_size(
        tarball_path, signature_path, max_bytes, keyring_home,
    )

    # STEP 3: allowlist
    allowlist = _load_allowlist(settings_path)
    _check_allowlist(source, allowlist)

    # STEP 4-6: extract to staging + parse manifest + revocation check
    with tempfile.TemporaryDirectory(prefix="squad-import-") as td:
        staging = Path(td) / "staging"
        staging.mkdir()
        try:
            with tarfile.open(str(tarball_path), mode="r:gz") as tar:
                # STEP 5a — path-traversal refusal (pre-extraction walk)
                _refuse_bad_members(tar)
                # STEP 4-5b — manifest parse + revocation
                slug, manifest_sha256 = _parse_and_check_manifest(
                    tar, revocations_path
                )
                # STEP 6 — extract
                _extract_to(tar, staging)
        except tarfile.TarError as e:
            raise ValidationError("corrupt_tar", f"tarfile error: {e}")

        # Move staged → final + capture backup for rollback.
        final_squad, backup = _install_staged_squad(
            staging, slug, dest_root, force,
        )

        # STEP 7: contract validator + rollback path.
        _validate_or_rollback(
            final_squad, slug, backup, validator_path, core_skills_dir,
        )

    return slug, manifest_sha256, signer_fpr


# --- CLI --------------------------------------------------------------------


def main(argv: Optional[List[str]] = None) -> int:
    """CLI entrypoint — import a squad tarball into .claude/skills/domains/."""
    # Kill-switch per debate S4.
    if os.environ.get("CEO_SOTA_DISABLE") == "1":
        sys.stdout.write(
            "squad-import: CEO_SOTA_DISABLE=1 — marketplace disabled (noop)\n"
        )
        return 0

    parser = argparse.ArgumentParser(
        prog="squad-import",
        description="Verify and install a signed squad tarball.",
    )
    parser.add_argument(
        "--tarball",
        required=True,
        help="Path to the .tar.gz archive.",
    )
    parser.add_argument(
        "--signature",
        required=True,
        help="Path to the detached GPG signature (typically <tarball>.sig).",
    )
    parser.add_argument(
        "--source",
        required=True,
        help="Pin-allowlist URI, e.g. github.com/acme/squad-edtech@v1",
    )
    parser.add_argument(
        "--dest-root",
        default=None,
        help="Override destination under .claude/skills/domains/ (used by tests).",
    )
    parser.add_argument(
        "--settings",
        default=None,
        help="Override path to .claude/settings.json (used by tests).",
    )
    parser.add_argument(
        "--revocations",
        default=None,
        help="Override path to revocation ledger (default "
        ".claude/squad-revocations.jsonl).",
    )
    parser.add_argument(
        "--max-bytes",
        type=int,
        default=DEFAULT_MAX_BYTES,
        help=f"Maximum tarball size in bytes. Default: {DEFAULT_MAX_BYTES}",
    )
    parser.add_argument(
        "--gnupg-home",
        default=None,
        help="Override GNUPGHOME (points gpg at a specific keyring). "
        "Used by tests with ephemeral keyring fixture.",
    )
    parser.add_argument(
        "--force",
        action="store_true",
        help="Overwrite an existing squad with the same slug.",
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

    tarball = Path(args.tarball).expanduser()
    signature = Path(args.signature).expanduser()

    repo_root = Path(args.repo_root).expanduser() if args.repo_root else REPO_ROOT
    dest_root = (
        Path(args.dest_root).expanduser()
        if args.dest_root
        else repo_root / ".claude" / "skills" / "domains"
    )
    settings_path = (
        Path(args.settings).expanduser()
        if args.settings
        else repo_root / ".claude" / "settings.json"
    )
    revocations_path = (
        Path(args.revocations).expanduser()
        if args.revocations
        else repo_root / ".claude" / "squad-revocations.jsonl"
    )
    keyring_home = Path(args.gnupg_home).expanduser() if args.gnupg_home else None

    try:
        slug, manifest_sha256, signer_fpr = import_squad(
            tarball,
            signature,
            args.source,
            dest_root=dest_root,
            settings_path=settings_path,
            revocations_path=revocations_path,
            max_bytes=args.max_bytes,
            keyring_home=keyring_home,
            force=args.force,
        )
    except ValidationError as exc:
        sys.stderr.write(
            f"error: validation failure — {exc.reason_code}: {exc}\n"
        )
        return 2
    except FileExistsError as exc:
        sys.stderr.write(f"error: {exc}\n")
        return 1
    except ContractError as exc:
        sys.stderr.write(
            "error: contract validator rejected the extracted squad; rollback applied.\n"
        )
        if exc.stderr:
            sys.stderr.write(f"validator stderr: {exc.stderr}\n")
        return 3
    except OSError as exc:
        sys.stderr.write(f"error: io: {exc}\n")
        return 1

    # Success — audit + stdout report.
    if emit_squad_imported is not None:
        try:
            emit_squad_imported(
                squad_name=slug,
                manifest_sha256=manifest_sha256,
                signer_fingerprint=signer_fpr,
                source=args.source,
            )
        except Exception:
            # Fail-open on audit (CLAUDE.md §Critical Rules).
            pass

    sys.stdout.write(f"imported: {slug}\n")
    sys.stdout.write(f"manifest_sha256: {manifest_sha256}\n")
    sys.stdout.write(f"signer_fingerprint: {signer_fpr}\n")
    sys.stdout.write(f"source: {args.source}\n")
    sys.stdout.write(f"installed_at: {dest_root / slug}\n")
    return 0


if __name__ == "__main__":  # pragma: no cover
    sys.exit(main())
