#!/usr/bin/env python3
"""PLAN-045 F-14-07 / PLAN-050 Phase 6 (C12) — Actions SHA-pin compliance + drift.

Walks `.github/workflows/*.yml` + `.github/workflows/*.yaml`, finds lines
like:

    uses: actions/checkout@<40-hex-sha>  # <tag-claim>

...and verifies two axes:

1. **Format compliance (hard — PLAN-050 C12).** Every `uses: X@Y` line
   MUST have `Y` as a 40-character hex SHA (not a tag or branch). Failure
   → exit 1. Bypasses: local `./path` references + `docker://` images.

2. **Tag-comment drift (advisory — PLAN-045 F-14-07).** When a pin carries
   a trailing `# tag` comment, query the GitHub API for the tag's actual
   dereferenced SHA. Mismatch → advisory WARN line (exit 2 under
   ``--strict``, else exit 0).

Stdlib-only (urllib). Python 3.9+.

Exit codes:
- **0** — format OK, no drift (or network check skipped)
- **1** — FORMAT VIOLATION (non-SHA pin) — CI hard-fail
- **2** — network/rate-limit failure OR tag-comment drift — CI soft-warning

Security (PLAN-050 C12):
- `ssl.CERT_REQUIRED` + `check_hostname=True` on every TLS connection.
- `timeout=10` per HTTP request.
- `GITHUB_TOKEN` env honored for authenticated rate limits (5000 req/hr
  vs. 60 req/hr unauthenticated).
"""
from __future__ import annotations

import argparse
import json
import os
import re
import ssl
import sys
import urllib.error
import urllib.request
from pathlib import Path
from typing import Iterator, List, Optional, Tuple


_REPO_ROOT = Path(__file__).resolve().parent.parent.parent

# PLAN-050 C12 — strict format regex. `uses: owner/repo[/path]@<40-hex>`
# optionally followed by a `# comment` (tag claim) or end-of-line. Allows
# leading YAML list indicator (`-`) since `uses:` typically lives under
# a `steps:` list item.
_STRICT_USES_RE = re.compile(
    r"^\s*(?:-\s+)?uses:\s*([A-Za-z0-9_./\-]+)@([A-Fa-f0-9]{40})"
    r"\s*(?:#\s*(\S+))?\s*$"
)
# Any `uses: ...` line at column-start (optionally under a list item).
# Used to surface format violations (tags, branches, partial SHAs).
_ANY_USES_RE = re.compile(r"^\s*(?:-\s+)?uses:\s*(\S+)")
# Exemptions: composite/local actions and docker:// images.
_EXEMPT_PREFIXES = ("./", "docker://")

_REQUEST_TIMEOUT_S = 10.0


def _build_ssl_context() -> ssl.SSLContext:
    """Strict TLS per PLAN-050 C12."""
    ctx = ssl.create_default_context()
    ctx.check_hostname = True
    ctx.verify_mode = ssl.CERT_REQUIRED
    return ctx


def _github_headers() -> dict:
    headers = {
        "User-Agent": "ceo-orchestration-sha-drift-check",
        "Accept": "application/vnd.github+json",
    }
    token = os.environ.get("GITHUB_TOKEN", "").strip()
    if token:
        headers["Authorization"] = f"Bearer {token}"
    return headers


def _iter_pins(
    workflows_dir: Path,
) -> Iterator[Tuple[Path, int, str, str, Optional[str], bool]]:
    """Yield ``(path, line_num, owner_repo, ref, tag_claim, is_strict)``.

    ``is_strict`` is True when the line matched the 40-hex SHA form; False
    when it matched the fallback (potential format violation).
    """
    if not workflows_dir.is_dir():
        return
    candidates = sorted(
        list(workflows_dir.glob("*.yml")) + list(workflows_dir.glob("*.yaml"))
    )
    for wf in candidates:
        try:
            lines = wf.read_text(encoding="utf-8").splitlines()
        except (OSError, UnicodeDecodeError):
            continue
        for i, line in enumerate(lines, start=1):
            # Skip commented-out `uses:` lines
            stripped = line.lstrip()
            if stripped.startswith("#"):
                continue
            m_strict = _STRICT_USES_RE.match(line)
            if m_strict:
                yield (
                    wf, i,
                    m_strict.group(1), m_strict.group(2),
                    m_strict.group(3), True,
                )
                continue
            m_any = _ANY_USES_RE.match(line)
            if m_any:
                target = m_any.group(1)
                if target.startswith(_EXEMPT_PREFIXES):
                    continue
                # Split owner/repo@ref for reporting
                if "@" in target:
                    repo, ref = target.split("@", 1)
                    yield wf, i, repo, ref, None, False
                else:
                    yield wf, i, target, "", None, False


def _fetch_tag_sha(
    owner_repo: str, tag: str, ctx: ssl.SSLContext
) -> str:
    """Query GitHub for the tag's dereferenced target SHA.

    Returns 40-hex SHA, or ``'unknown'`` on any network / parse / rate
    / TLS error (fail-open — caller treats unknown as soft-warning).
    """
    # Strip any path suffix: `owner/repo/sub/dir` → `owner/repo`
    parts = owner_repo.split("/")
    if len(parts) < 2:
        return "unknown"
    short_repo = f"{parts[0]}/{parts[1]}"
    url = f"https://api.github.com/repos/{short_repo}/git/refs/tags/{tag}"
    try:
        req = urllib.request.Request(url, headers=_github_headers())
        with urllib.request.urlopen(
            req, timeout=_REQUEST_TIMEOUT_S, context=ctx
        ) as r:
            if r.status != 200:
                return "unknown"
            body = r.read()
            if len(body) > 1_000_000:
                return "unknown"
            data = json.loads(body.decode("utf-8"))
            obj = data.get("object") or {}
            target_sha = obj.get("sha", "")
            obj_type = obj.get("type")
            # Annotated tags require a second dereference to get the commit SHA.
            if obj_type == "tag" and target_sha:
                url2 = (
                    f"https://api.github.com/repos/{short_repo}"
                    f"/git/tags/{target_sha}"
                )
                req2 = urllib.request.Request(url2, headers=_github_headers())
                with urllib.request.urlopen(
                    req2, timeout=_REQUEST_TIMEOUT_S, context=ctx
                ) as r2:
                    if r2.status != 200:
                        return target_sha
                    body2 = r2.read()
                    if len(body2) > 1_000_000:
                        return target_sha
                    data2 = json.loads(body2.decode("utf-8"))
                    return (data2.get("object") or {}).get("sha", target_sha)
            if isinstance(target_sha, str) and len(target_sha) == 40:
                return target_sha.lower()
            return "unknown"
    except (urllib.error.URLError, urllib.error.HTTPError,
            TimeoutError, json.JSONDecodeError, OSError, ssl.SSLError):
        return "unknown"


def main(argv: Optional[List[str]] = None) -> int:
    """CLI entrypoint — scan workflow SHA-pins + verify format + drift."""
    parser = argparse.ArgumentParser(
        prog="check-action-sha-drift",
        description=(
            "Verify .github/workflows/*.yml pins are 40-hex SHAs + "
            "advise on tag-comment drift vs upstream."
        ),
    )
    parser.add_argument(
        "--workflows-dir",
        type=Path,
        default=_REPO_ROOT / ".github" / "workflows",
        help="Directory to scan (default: <repo>/.github/workflows).",
    )
    parser.add_argument(
        "--strict", action="store_true",
        help="Exit 2 on tag-comment drift (default: exit 0 / advisory).",
    )
    parser.add_argument(
        "--offline", "--format-only",
        dest="offline", action="store_true",
        help="Skip GitHub API drift check; format-compliance only.",
    )
    args = parser.parse_args(argv)

    # Pass 1 — collect + classify pins
    violations: List[str] = []
    compliant: List[Tuple[Path, int, str, str, Optional[str]]] = []
    for path, line_no, repo, ref, tag_claim, is_strict in _iter_pins(
        args.workflows_dir
    ):
        if not is_strict:
            violations.append(
                f"  {path.name}:{line_no}  non-compliant pin: "
                f"uses: {repo}@{ref or '<missing>'}"
            )
            continue
        compliant.append((path, line_no, repo, ref, tag_claim))

    # Format violations → hard fail
    if violations:
        print("FORMAT VIOLATIONS (PLAN-050 C12 hard-fail):", file=sys.stderr)
        for v in violations:
            print(v, file=sys.stderr)
        print(
            f"\ninventory: {len(compliant)} compliant, "
            f"{len(violations)} violation(s)",
            file=sys.stderr,
        )
        return 1

    if args.offline or not compliant:
        print(
            f"format OK: {len(compliant)} compliant SHA pin(s); "
            "network drift check skipped.",
            file=sys.stderr,
        )
        return 0

    # Pass 2 — advisory tag-comment drift check
    ctx = _build_ssl_context()
    drifts = 0
    skipped = 0
    for path, line_no, repo, sha, tag_claim in compliant:
        if not tag_claim:
            continue  # no tag comment → no drift axis
        upstream = _fetch_tag_sha(repo, tag_claim, ctx)
        if upstream == "unknown":
            skipped += 1
            continue
        if sha.lower() != upstream.lower():
            print(
                f"  DRIFT {path.name}:{line_no} {repo}@{sha[:12]}... "
                f"claims tag {tag_claim}; upstream {tag_claim} → "
                f"{upstream[:12]}...",
                file=sys.stderr,
            )
            drifts += 1

    print(
        f"\ninventory: {len(compliant)} compliant, "
        f"{drifts} drift(s), {skipped} skipped (network/unknown)",
        file=sys.stderr,
    )
    if skipped and not drifts:
        return 2  # network failure (CI soft-warning per C12)
    if drifts and args.strict:
        return 2
    return 0


if __name__ == "__main__":
    sys.exit(main())
