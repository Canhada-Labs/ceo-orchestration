"""Stable semantic-version policy for locally resolved CLI packages."""

from __future__ import annotations

import json
import re
from pathlib import Path
from typing import Iterable, Optional, Tuple


CODEX_VERSION_FLOOR = "0.160.0"
_SEMVER_RE = re.compile(r"^v?([0-9]+)\.([0-9]+)\.([0-9]+)$")


def parse_semver(value: object) -> Optional[Tuple[int, int, int]]:
    """Parse a stable ``major.minor.patch`` version; reject prereleases."""
    if not isinstance(value, str):
        return None
    match = _SEMVER_RE.fullmatch(value.strip())
    if match is None:
        return None
    return tuple(int(part) for part in match.groups())


def compare_semver(candidate: object, floor: object) -> Optional[int]:
    """Compare stable versions: positive when candidate is newer, else None."""
    parsed_candidate = parse_semver(candidate)
    parsed_floor = parse_semver(floor)
    if parsed_candidate is None or parsed_floor is None:
        return None
    return (parsed_candidate > parsed_floor) - (parsed_candidate < parsed_floor)


def compatible_package_version(
    payload: Path, launcher: Optional[Path], manifest_version: object = None,
    floor: str = CODEX_VERSION_FLOOR,
) -> Optional[str]:
    """Return a qualified stable version meeting floor and optional manifest.

    This is currency evidence only: callers must not describe it as a hash
    attestation of the executable bytes.
    """
    for package_file in _package_files((payload, launcher)):
        version = _qualified_package_version(package_file)
        comparison = compare_semver(version, floor)
        manifest_comparison = (
            1 if manifest_version is None else compare_semver(version, manifest_version)
        )
        if comparison is not None and comparison >= 0 and manifest_comparison is not None and manifest_comparison > 0:
            return version
    return None


def qualified_package_version(payload: Path, launcher: Optional[Path]) -> Optional[str]:
    """Return stable version from a nearby qualified package, if present."""
    for package_file in _package_files((payload, launcher)):
        version = _qualified_package_version(package_file)
        if version is not None:
            return version
    return None


def _package_files(paths: Iterable[Optional[Path]]) -> Iterable[Path]:
    seen = set()
    for path in paths:
        if path is None:
            continue
        try:
            path = path.resolve()
        except OSError:
            pass
        for parent in (path.parent, *path.parents):
            package_file = parent / "package.json"
            if package_file not in seen:
                seen.add(package_file)
                yield package_file


def _qualified_package_version(package_file: Path) -> Optional[str]:
    try:
        data = json.loads(package_file.read_text(encoding="utf-8"))
    except (OSError, ValueError, RecursionError):
        return None
    if not isinstance(data, dict) or data.get("name") != "@openai/codex":
        return None
    version = data.get("version")
    return version if parse_semver(version) is not None else None
