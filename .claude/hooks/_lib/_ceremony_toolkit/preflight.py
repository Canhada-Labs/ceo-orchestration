"""Read-only canonical scope and GPG gates for a future ceremony packet."""

from __future__ import annotations

import ast
import fnmatch
import hashlib
import re
import shutil
import subprocess
from pathlib import Path, PurePosixPath
from typing import Iterable, Mapping, Optional

_FPR = re.compile(r"^[A-F0-9]{40}$")
_SCOPE_LINE = re.compile(r"^\s{2,}-\s+(.+?)\s*$")
_APPROVAL = re.compile(r"^Approved-By:\s+@\S+\s+[a-fA-F0-9]{40}\s*$", re.M)


def _safe_rel(path: str) -> str:
    """Reject all ambiguous paths instead of normalising them into scope."""
    if not isinstance(path, str) or not path or "\\" in path or "\x00" in path:
        raise ValueError("unsafe_path")
    p = PurePosixPath(path)
    if p.is_absolute() or any(part in (".", "..") for part in path.split("/")):
        raise ValueError("unsafe_path")
    if p.as_posix() != path or path.startswith("~"):
        raise ValueError("unsafe_path")
    return path


def _fnmatch_segments(path: str, pattern: str) -> bool:
    """Mirror canonical_edit.paths._fnmatch_segments without its hook-bound globals."""
    parts, patterns = path.split("/"), pattern.split("/")
    if not patterns:
        return not parts
    head, rest = patterns[0], patterns[1:]
    if head == "**":
        return any(_match_parts(parts[i:], rest) for i in range(len(parts) + 1))
    return _match_parts(parts, patterns)


def _match_parts(parts: list, patterns: list) -> bool:
    if not patterns:
        return not parts
    if patterns[0] == "**":
        return any(_match_parts(parts[i:], patterns[1:]) for i in range(len(parts) + 1))
    return bool(parts) and fnmatch.fnmatchcase(parts[0], patterns[0]) and _match_parts(parts[1:], patterns[1:])


def _canonical_patterns(repo_root: Path) -> tuple[str, ...]:
    """Read the actual guard policy as AST literals; never execute hook code."""
    policy = repo_root / ".claude/hooks/check_canonical_edit.py"
    source = ast.parse(policy.read_text(encoding="utf-8"))
    for node in source.body:
        if isinstance(node, ast.Assign) and any(
            isinstance(t, ast.Name) and t.id == "_CANONICAL_GUARDS" for t in node.targets
        ):
            patterns = ast.literal_eval(node.value)
            if not isinstance(patterns, list) or not all(isinstance(x, str) for x in patterns):
                break
            return tuple(patterns)
    raise ValueError("canonical_guard_policy_unavailable")


def collect_modified_canonical_paths(
    repo_root: Path, modified_paths: Iterable[str], *, canonical_patterns: Optional[Iterable[str]] = None
) -> tuple[str, ...]:
    """Collect guarded paths using the hook's segment-matching semantics.

    Caller supplies modified paths from a trusted diff; this helper never
    invents a diff or assumes a cached list. Unsafe paths fail the packet.
    """
    patterns = tuple(canonical_patterns) if canonical_patterns is not None else _canonical_patterns(Path(repo_root))
    if not patterns or not all(isinstance(p, str) and p for p in patterns):
        raise ValueError("empty_or_invalid_canonical_policy")
    paths = (_safe_rel(p) for p in modified_paths)
    return tuple(sorted({p for p in paths if any(_fnmatch_segments(p.lower(), pat.lower()) for pat in patterns)}))


def _parse_scope(text: str) -> tuple[str, ...]:
    in_scope = False
    seen_scope = False
    scope = []
    for line in text.splitlines():
        if line.strip() == "Scope:":
            if seen_scope:
                raise ValueError("duplicate_scope")
            seen_scope = True
            in_scope = True
            continue
        if in_scope:
            match = _SCOPE_LINE.fullmatch(line)
            if match:
                scope.append(_safe_rel(match.group(1)))
            elif line.strip():
                in_scope = False
    if not scope or len(set(scope)) != len(scope):
        raise ValueError("missing_or_duplicate_scope")
    return tuple(sorted(scope))


def validate_sentinel_pack(
    repo_root: Path,
    sentinel_file: Path,
    modified_paths: Iterable[str],
    *,
    expected_sha256: Optional[Mapping[str, str]] = None,
    canonical_patterns: Optional[Iterable[str]] = None,
) -> dict:
    """Check exact scope and optional *fresh* SHA-256 pins; never approve.

    ``expected_sha256`` pins must cover every modified canonical path, or
    are omitted altogether. Content pins are remeasured from disk on each
    call. Syntactic validity does not imply that the Owner signed anything.
    """
    result = {"valid": False, "reason": "", "canonical_paths": (), "sha256": {}}
    try:
        root = Path(repo_root).resolve(strict=True)
        sentinel = Path(sentinel_file)
        if sentinel.is_symlink() or not sentinel.is_file():
            raise ValueError("sentinel_missing_or_symlink")
        text = sentinel.read_text(encoding="utf-8")
        if len(_APPROVAL.findall(text)) != 1:
            raise ValueError("approved_by_missing_or_ambiguous")
        actual = collect_modified_canonical_paths(root, modified_paths, canonical_patterns=canonical_patterns)
        result["canonical_paths"] = actual
        if _parse_scope(text) != actual:
            raise ValueError("scope_diff_mismatch")
        if expected_sha256 is not None:
            if set(expected_sha256) != set(actual):
                raise ValueError("sha256_pin_scope_mismatch")
            for rel in actual:
                target = root / rel
                if target.is_symlink() or not target.is_file() or not target.resolve().is_relative_to(root):
                    raise ValueError("canonical_file_missing_or_symlink")
                digest = hashlib.sha256(target.read_bytes()).hexdigest()
                result["sha256"][rel] = digest
                if not isinstance(expected_sha256[rel], str) or digest != expected_sha256[rel].lower():
                    raise ValueError("sha256_pin_mismatch")
        result.update(valid=True, reason="")
    except (ValueError, OSError, UnicodeError, SyntaxError) as exc:
        result["reason"] = str(exc) if isinstance(exc, ValueError) else type(exc).__name__
    return result


def verify_detached_signatures(
    signed_file: Path,
    signature_file: Path,
    *,
    keyring_home: Path,
    allowed_fingerprints: Iterable[str],
    timeout: float = 15.0,
) -> dict:
    """Verify detached bytes with GPG and an explicit isolated keyring.

    Reject unknown signers even when GPG reports ``GOODSIG``. No trust on
    first use, personal GNUPGHOME, network retrieval or signing commands.
    """
    result = {"valid": False, "fingerprint": "", "reason": ""}
    try:
        home = Path(keyring_home)
        signed = Path(signed_file)
        sig = Path(signature_file)
        if not home.is_absolute() or home.is_symlink() or not home.is_dir():
            raise ValueError("explicit_keyring_required")
        if any(p.is_symlink() or not p.is_file() for p in (signed, sig)):
            raise ValueError("signed_file_or_signature_missing")
        permitted = {str(fp).replace(" ", "").upper() for fp in allowed_fingerprints}
        if not permitted or not all(_FPR.fullmatch(fp) for fp in permitted):
            raise ValueError("invalid_or_empty_fingerprint_allowlist")
        binary = shutil.which("gpg") or shutil.which("gpg2")
        if binary is None:
            raise ValueError("gpg_missing")
        command = [binary, "--no-options", "--no-autostart", "--homedir", str(home), "--batch", "--no-tty", "--no-auto-key-retrieve", "--status-fd", "1", "--verify", str(sig), str(signed)]
        process = subprocess.run(command, capture_output=True, text=True, timeout=timeout, check=False)
        if process.returncode:
            raise ValueError("gpg_invalid_signature")
        good = False
        candidates = set()
        for line in process.stdout.splitlines():
            if line.startswith("[GNUPG:] GOODSIG "):
                good = True
            elif line.startswith("[GNUPG:] VALIDSIG "):
                fields = line.split()
                if len(fields) >= 3:
                    candidates.add(fields[2].upper())
                    if len(fields) >= 12:
                        candidates.add(fields[-1].upper())  # primary key, if signing subkey
        if not good or not candidates:
            raise ValueError("gpg_signature_status_incomplete")
        matches = sorted(fp for fp in candidates if _FPR.fullmatch(fp) and fp in permitted)
        if not matches:
            raise ValueError("signer_not_allowlisted")
        result.update(valid=True, fingerprint=matches[0], reason="")
    except (ValueError, OSError, subprocess.TimeoutExpired) as exc:
        result["reason"] = str(exc) if isinstance(exc, ValueError) else type(exc).__name__
    return result
