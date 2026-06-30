#!/usr/bin/env python3
"""Generate CycloneDX v1.5 JSON SBOM for ceo-orchestration.

PLAN-045 F-14 — supply-chain release hardening.

Walks the repo to enumerate:
  - Python stdlib imports declared across .claude/hooks + .claude/scripts
  - Documented third-party exceptions (`docs/stdlib-exceptions.md` — yaml, anthropic)
  - GitHub Actions workflow dependencies (SHA-pinned actions)

Stdlib-only. Python 3.9+. Deterministic output (sorted keys, fixed
timestamp unless --now).

Usage:
  python3 .claude/scripts/generate-sbom.py --output sbom.cyclonedx.json
  python3 .claude/scripts/generate-sbom.py --print   # stdout, no write

Exit codes:
  0 — SBOM emitted successfully
  2 — expected directory structure missing (not a ceo-orchestration repo root)
"""
from __future__ import annotations

import argparse
import ast
import json
import os
import re
import subprocess
import sys
import uuid
from datetime import datetime, timezone
from pathlib import Path
from typing import Any, Dict, List, Optional, Set, Tuple


REPO_ROOT = Path(__file__).resolve().parent.parent.parent

# Documented third-party exceptions (ADR-002). Update when
# `docs/stdlib-exceptions.md` amends the allow-list.
THIRD_PARTY_ALLOWLIST = {
    "yaml": {
        "name": "pyyaml",
        "purl_prefix": "pkg:pypi/pyyaml",
        "scope": "required",
        "reason": "ADR-002 exception — skill frontmatter parsing",
    },
    "anthropic": {
        "name": "anthropic",
        "purl_prefix": "pkg:pypi/anthropic",
        "scope": "optional",
        "reason": "ADR-002 exception — benchmark dispatcher (lazy-loaded)",
    },
    "pytest": {
        "name": "pytest",
        "purl_prefix": "pkg:pypi/pytest",
        "scope": "excluded",
        "reason": "dev/test tooling — not runtime",
    },
}


def _detect_third_party_imports() -> Set[str]:
    """Grep for third-party imports in hooks + scripts; return allowed set."""
    hits: Set[str] = set()
    for root in [REPO_ROOT / ".claude" / "hooks",
                 REPO_ROOT / ".claude" / "scripts"]:
        if not root.is_dir():
            continue
        for py in root.rglob("*.py"):
            if "/tests/" in str(py) or "/mutations/" in str(py):
                continue
            try:
                tree = ast.parse(py.read_text(encoding="utf-8"))
            except (SyntaxError, UnicodeDecodeError):
                continue
            for node in ast.walk(tree):
                if isinstance(node, ast.Import):
                    for alias in node.names:
                        mod = alias.name.split(".")[0]
                        if mod in THIRD_PARTY_ALLOWLIST:
                            hits.add(mod)
                elif isinstance(node, ast.ImportFrom):
                    if node.module:
                        mod = node.module.split(".")[0]
                        if mod in THIRD_PARTY_ALLOWLIST:
                            hits.add(mod)
    return hits


def _detect_workflow_actions() -> List[Dict[str, str]]:
    """Parse .github/workflows/*.yml for `uses: owner/repo@sha` lines."""
    workflows_dir = REPO_ROOT / ".github" / "workflows"
    if not workflows_dir.is_dir():
        return []
    actions: Dict[str, str] = {}
    uses_re = re.compile(
        r"^\s*-?\s*uses:\s*([a-zA-Z0-9_.-]+/[a-zA-Z0-9_.-]+)@([a-f0-9]{40}|v?[\d.]+)",
        re.MULTILINE,
    )
    for wf in workflows_dir.glob("*.yml"):
        try:
            text = wf.read_text(encoding="utf-8")
        except OSError:
            continue
        for match in uses_re.finditer(text):
            name, ref = match.group(1), match.group(2)
            actions.setdefault(name, ref)
    out = []
    for name, ref in sorted(actions.items()):
        out.append({
            "name": name,
            "version": ref,
            "purl": "pkg:github/{name}@{ref}".format(name=name, ref=ref),
            "scope": "required",
        })
    return out


def _git_commit_sha() -> str:
    """Return HEAD commit SHA via subprocess, or 'unknown' on failure."""
    try:
        result = subprocess.run(
            ["git", "rev-parse", "HEAD"],
            capture_output=True,
            text=True,
            timeout=5,
            cwd=str(REPO_ROOT),
        )
        if result.returncode == 0:
            return result.stdout.strip()
    except (OSError, subprocess.TimeoutExpired):
        pass
    return "unknown"


def _read_version() -> str:
    """Read top-level VERSION file; return 'unknown' on failure."""
    v = REPO_ROOT / "VERSION"
    if v.exists():
        try:
            return v.read_text(encoding="utf-8").strip()
        except OSError:
            pass
    return "unknown"


def generate_sbom(
    include_python: bool = True,
    include_workflows: bool = True,
    use_current_time: bool = False,
) -> Dict[str, Any]:
    """Build the CycloneDX v1.5 document dictionary.

    Deterministic output when ``use_current_time=False``: timestamp
    defaults to the epoch-0 UTC value so byte-identity holds across
    runs. Set ``use_current_time=True`` to embed real release time.
    """
    ts = datetime.now(timezone.utc) if use_current_time else datetime(
        2026, 1, 1, tzinfo=timezone.utc
    )

    components: List[Dict[str, Any]] = []

    if include_python:
        detected = sorted(_detect_third_party_imports())
        for mod in detected:
            entry = THIRD_PARTY_ALLOWLIST[mod]
            if entry["scope"] == "excluded":
                continue
            components.append({
                "type": "library",
                "name": entry["name"],
                "purl": entry["purl_prefix"],
                "scope": entry["scope"],
                "description": entry["reason"],
            })

    if include_workflows:
        for action in _detect_workflow_actions():
            components.append({
                "type": "application",
                "name": action["name"],
                "version": action["version"],
                "purl": action["purl"],
                "scope": action["scope"],
                "description": "GitHub Actions workflow dependency",
            })

    # Deterministic serial number from git HEAD — same tree → same SBOM.
    sha = _git_commit_sha()
    if sha != "unknown":
        # Derive a UUID from the SHA for determinism.
        serial = str(uuid.UUID(bytes=sha.encode("ascii", errors="replace").ljust(16, b"0")[:16]))
    else:
        serial = str(uuid.uuid4())

    return {
        "bomFormat": "CycloneDX",
        "specVersion": "1.5",
        "serialNumber": "urn:uuid:{s}".format(s=serial),
        "version": 1,
        "metadata": {
            "timestamp": ts.strftime("%Y-%m-%dT%H:%M:%SZ"),
            "tools": [{
                "vendor": "ceo-orchestration",
                "name": "generate-sbom.py",
                "version": _read_version(),
            }],
            "component": {
                "type": "application",
                "name": "ceo-orchestration",
                "version": _read_version(),
                "description": "Portable framework for operating Claude Code as a governed team of specialist agents.",
                "licenses": [{"license": {"id": "MIT"}}],
                "externalReferences": [{
                    "type": "vcs",
                    "url": os.environ.get(
                        "CEO_FRAMEWORK_UPSTREAM",
                        "https://github.com/Canhada-Labs/ceo-orchestration",
                    ),
                    "comment": "HEAD SHA: {sha}".format(sha=sha),
                }],
            },
        },
        "components": components,
    }


def main() -> int:
    """CLI entrypoint — emit a CycloneDX v1.5 SBOM to stdout or file."""
    parser = argparse.ArgumentParser(
        prog="generate-sbom",
        description="Generate CycloneDX v1.5 JSON SBOM for ceo-orchestration.",
    )
    parser.add_argument(
        "--output", type=Path, default=None,
        help="Write SBOM to this path (default stdout).",
    )
    parser.add_argument(
        "--print", action="store_true",
        help="Print SBOM to stdout (forced when --output omitted).",
    )
    parser.add_argument(
        "--include-python", action="store_true", default=True,
        help="Include Python third-party imports (default on).",
    )
    parser.add_argument(
        "--include-workflows", action="store_true", default=True,
        help="Include GitHub Actions workflow deps (default on).",
    )
    parser.add_argument(
        "--now", action="store_true",
        help="Embed current UTC time (default: deterministic epoch).",
    )
    args = parser.parse_args()

    if not (REPO_ROOT / "CLAUDE.md").exists():
        print(
            "ERROR: expected repo root at {r}".format(r=REPO_ROOT),
            file=sys.stderr,
        )
        return 2

    sbom = generate_sbom(
        include_python=args.include_python,
        include_workflows=args.include_workflows,
        use_current_time=args.now,
    )
    text = json.dumps(sbom, indent=2, sort_keys=True)

    if args.output is None or args.print:
        print(text)
    if args.output is not None:
        args.output.parent.mkdir(parents=True, exist_ok=True)
        args.output.write_text(text + "\n", encoding="utf-8")
        print(
            "SBOM written to {p} ({n} components)".format(
                p=args.output, n=len(sbom["components"])
            ),
            file=sys.stderr,
        )
    return 0


if __name__ == "__main__":
    sys.exit(main())
