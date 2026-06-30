#!/usr/bin/env python3
"""import-skill — attribution + SP-NNN wrapper for curated skill imports.

PLAN-033 Phase 2. Takes a source SKILL.md (from an external curated
corpus, e.g. `antigravity-awesome-skills`) and produces a framework-
compatible SKILL.md under `.claude/skills/domains/<domain>/skills/<slug>/`
with provenance frontmatter injected.

Plan spec named this script `.sh`; we use Python instead for harness
parity with `skill-import-rubric.py` and deterministic cross-platform
behavior. Functionally identical to a bash wrapper around the same steps.

Usage::

    import-skill.py \\
        --source path/to/upstream/SKILL.md \\
        --domain community \\
        --slug my-skill \\
        --upstream nextlevelbuilder/antigravity-awesome-skills@v10.3.0 \\
        --license "CC BY 4.0" \\
        --sp-nnn SP-042 \\
        [--owner-sha256 <64-hex>]

Behavior::

  1. Validate the source passes `skill-import-rubric.py` (unless
     --skip-rubric is set — rare, Owner override).
  2. Compute a deterministic "import provenance" frontmatter block
     (`source:`, `license:`, `sp_chain:`, `owner_sha256:`,
     `imported_at:`).
  3. Merge the provenance fields INTO the source's existing frontmatter.
  4. Write the result to
     `.claude/skills/domains/<domain>/skills/<slug>/SKILL.md`.
  5. Refuse to overwrite an existing target unless `--force` is passed.
  6. If `--notice` is provided, append an attribution row to the target
     domain's `NOTICE.md`.

Exit codes::

  0 — success
  1 — rubric failure, IO error, or target exists without --force
  2 — CLI error
"""
from __future__ import annotations

import argparse
import importlib.util
import json
import re
import sys
from datetime import datetime, timezone
from pathlib import Path
from typing import Any, Dict, List, Optional


REPO_ROOT = Path(__file__).resolve().parents[2]
SKILLS_DOMAIN_ROOT = REPO_ROOT / ".claude" / "skills" / "domains"
_FRONTMATTER_RE = re.compile(r"^---\s*\n(.*?)\n---\s*\n", re.DOTALL)

# PLAN-045 Wave 1 F-01-08 — shared signer allowlist (same file used by
# SP-NNN skill-patch-apply.py). ``--skip-rubric`` now requires a real
# Owner GPG signature on the source, verified against this allowlist.
_SIGNER_ALLOWLIST = REPO_ROOT / ".claude" / "skill-patch-signers.txt"

# PLAN-045 Wave 3 F-14-03 / F-11-01 — SPDX license allowlist.
#
# Previously --license accepted any string. Now only SPDX identifiers
# matching a permissive / copyleft-compatible shortlist are accepted.
# AGPL, proprietary, or unknown strings fail-CLOSED with a clear error.
#
# Curated permissive + weak-copyleft list. Add entries via
# --license-extra kwarg in CI when a new license is reviewed.
_ALLOWED_SPDX_LICENSES = frozenset({
    "Apache-2.0",
    "MIT",
    "BSD-2-Clause",
    "BSD-3-Clause",
    "BSD-4-Clause",
    "ISC",
    "CC0-1.0",
    "CC-BY-4.0",
    "CC-BY-SA-4.0",
    "MPL-2.0",
    "Zlib",
    "Unlicense",
})

# PLAN-045 Wave 3 F-14-03 alias — `_ALLOWED_LICENSES` is the name used
# in PLAN-044 triage spec and downstream security audits. Same frozenset.
_ALLOWED_LICENSES = _ALLOWED_SPDX_LICENSES


# PLAN-045 Wave 3 F-11-03 hardening — strict 40-hex SHA matcher.
# Short SHAs (7-12 hex) are collision-prone (2**28 space for 7-hex is
# computationally trivial; Linux kernel has observed natural 7-hex
# collisions). Supply-chain pins MUST use full 40-hex (2**160).
_COMMIT_SHA_RE = re.compile(r"^(?P<repo>[\w\-._/]+)@(?P<ref>[a-f0-9]{40})$")

# Strict 40-hex matcher for extracting the SHA into `imported_sha:`
# provenance field. Lowercase-normalised at validation time.
_STRICT_40HEX_RE = re.compile(r"^[a-f0-9]{40}$")


def _extract_commit_sha_40hex(upstream: str) -> Optional[str]:
    """Return the 40-hex commit SHA after '@' if present, else None.

    Used to populate the ``imported_sha:`` provenance field. Tags
    (e.g. ``v1.2.3``) return None; only full 40-hex refs yield a
    value. Callers must have already normalised upstream via
    ``_validate_upstream_ref`` which lowercases hex refs.
    """
    if "@" not in upstream:
        return None
    _repo, _, ref = upstream.rpartition("@")
    ref = ref.strip().lower()
    if _STRICT_40HEX_RE.match(ref):
        return ref
    return None

# Known mutable branch refs — deny-list. Any other ref string after
# ``@`` (tags, release branches with explicit version prefixes) is
# accepted as immutable-by-convention.
_FORBIDDEN_BRANCH_REFS = frozenset({
    "main", "master", "trunk", "HEAD", "develop", "dev",
    "staging", "stable", "next", "latest", "edge",
})


def _validate_upstream_ref(upstream: str) -> str:
    """PLAN-045 Wave 3 F-11-03 closure: reject @main / @HEAD / branch refs.

    Valid upstream is ``<repo>@<ref>`` where <ref> is EITHER:

    - A commit SHA (7-40 hex chars), OR
    - Any string NOT in the forbidden-branch-ref deny-list
      (``main``, ``master``, ``trunk``, ``HEAD``, ``develop``, ``dev``,
      ``staging``, ``stable``, ``next``, ``latest``, ``edge``).

    Tags — whether ``v1.2.3``, ``valpha``, ``release-2026-04`` — are
    accepted because tags are conventionally immutable in OSS
    workflows (reassignment requires force-push, an intentional
    maintainer act). The deny-list approach is more forgiving than
    a strict "must start with v<digit>" allow-list.

    Returns the upstream string on success. Raises ValueError on
    reject.
    """
    if "@" not in upstream:
        raise ValueError(
            f"--upstream {upstream!r} must be 'org/repo@<ref>' "
            f"(commit SHA or immutable tag). PLAN-045 F-11-03."
        )
    # Full 40-hex commit SHA passes. Normalise to lowercase hex so
    # downstream ``imported_sha:`` comparisons are canonical (PLAN-045 F-11-03).
    m = _COMMIT_SHA_RE.match(upstream)
    if m:
        repo = m.group("repo")
        ref = m.group("ref").lower()
        return f"{repo}@{ref}"
    # Split and check the ref against the branch deny-list.
    _repo, _, ref = upstream.rpartition("@")
    ref = ref.strip()
    if ref in _FORBIDDEN_BRANCH_REFS:
        raise ValueError(
            f"--upstream {upstream!r} uses a mutable branch ref "
            f"({ref!r}). Use a commit SHA (e.g. 'org/repo@<40-hex>') "
            f"or a tag (e.g. 'org/repo@v1.0.0'). Mutable refs are "
            f"rejected for forensic traceability. PLAN-045 F-11-03."
        )
    # PLAN-045 F-11-03: reject short-SHA-looking refs (7-39 hex lowercase).
    # Short SHAs collide (git observed 7-hex collisions in Linux kernel);
    # supply-chain pins MUST be full 40-hex OR a non-hex-looking tag.
    if re.match(r"^[a-f0-9]{7,39}$", ref.lower()):
        raise ValueError(
            f"--upstream {upstream!r} ref {ref!r} looks like a short "
            f"SHA ({len(ref)} hex chars). Supply-chain pins require "
            f"full 40-hex SHAs (2**160 collision space) or a non-hex "
            f"tag. PLAN-045 F-11-03."
        )
    if not ref:
        raise ValueError(
            f"--upstream {upstream!r} has empty ref after '@'. "
            f"PLAN-045 F-11-03."
        )
    return upstream


def _validate_license_spdx(
    license_str: str,
    extra_allowed: Optional[List[str]] = None,
) -> str:
    """PLAN-045 F-14-03 / F-11-01 closure: reject unknown licenses.

    Returns the canonicalised license string (SPDX preferred form).
    Raises ValueError on rejection. ``extra_allowed`` augments the
    built-in allowlist for operators who have reviewed and accepted
    a new license.
    """
    if not license_str:
        raise ValueError("--license cannot be empty")
    normalised = license_str.strip()
    # Also accept the common verbose form "CC BY 4.0" -> "CC-BY-4.0".
    verbose_map = {
        "CC BY 4.0": "CC-BY-4.0",
        "CC BY-SA 4.0": "CC-BY-SA-4.0",
        "CC BY SA 4.0": "CC-BY-SA-4.0",
        "CC0 1.0": "CC0-1.0",
        "Apache 2.0": "Apache-2.0",
        "Apache License 2.0": "Apache-2.0",
        "MPL 2.0": "MPL-2.0",
    }
    if normalised in verbose_map:
        normalised = verbose_map[normalised]
    allowed = set(_ALLOWED_SPDX_LICENSES)
    if extra_allowed:
        allowed.update(s.strip() for s in extra_allowed if s.strip())
    if normalised not in allowed:
        raise ValueError(
            f"--license {license_str!r} is not in the SPDX allowlist. "
            f"Allowed: {sorted(allowed)}. Known-bad (AGPL / proprietary) "
            f"are rejected; if this is a new permissive license, pass "
            f"--license-extra <SPDX-id> after Owner review."
        )
    return normalised

# Provenance keys written by this tool (injected / updated on import).
_PROVENANCE_KEYS = [
    "source",
    "imported_sha",
    "license",
    "sp_chain",
    "owner_sha256",
    "imported_at",
    "imported_by",
    "skip_rubric_signer_fpr",
]


def _load_rubric_module() -> Any:
    """Load the rubric validator so we can call it in-process."""
    src = REPO_ROOT / ".claude" / "scripts" / "skill-import-rubric.py"
    spec = importlib.util.spec_from_file_location("rubric_runtime", src)
    mod = importlib.util.module_from_spec(spec)
    sys.modules["rubric_runtime"] = mod
    assert spec.loader is not None
    spec.loader.exec_module(mod)
    return mod


def _split_frontmatter(content: str) -> (str, str):
    """Return (frontmatter_body_without_fences, body_after_frontmatter)."""
    m = _FRONTMATTER_RE.match(content)
    if not m:
        return "", content
    return m.group(1), content[m.end():]


def _merge_frontmatter(original: str, injected: Dict[str, str]) -> str:
    """Emit a frontmatter body containing original lines, with provenance
    keys from `injected` overriding any matching key already present.

    We preserve the original frontmatter order for all non-provenance
    keys, then append any provenance keys not already present at the
    end of the block.
    """
    lines = original.splitlines()
    out_lines: List[str] = []
    seen: set = set()
    # Pass 1: copy original, substituting provenance keys if they appear.
    for line in lines:
        m = re.match(r"^(\s*)([a-zA-Z_][a-zA-Z0-9_-]*)\s*:", line)
        if m:
            key = m.group(2)
            if key in injected:
                out_lines.append(f"{key}: {injected[key]}")
                seen.add(key)
                continue
        out_lines.append(line)
    # Pass 2: append injected keys not present in original.
    for key in _PROVENANCE_KEYS:
        if key in injected and key not in seen:
            out_lines.append(f"{key}: {injected[key]}")
    return "\n".join(out_lines)


def _utc_iso_now() -> str:
    return datetime.now(timezone.utc).strftime("%Y-%m-%dT%H:%M:%SZ")


def build_provenance(
    upstream: str,
    license_spdx: str,
    sp_nnn: str,
    owner_sha256: Optional[str] = None,
    imported_by: str = "CEO-orchestration/plan-033",
) -> Dict[str, str]:
    """Build the provenance frontmatter block (source / license / sp_chain / sha)."""
    prov = {
        "source": f'"{upstream}"',
        "license": f'"{license_spdx}"',
        "sp_chain": sp_nnn,
        "imported_at": _utc_iso_now(),
        "imported_by": f'"{imported_by}"',
    }
    # PLAN-045 F-11-03 — dedicated 40-hex audit-trail field. Only
    # emitted when upstream pins a full SHA (tags skip by design;
    # SBOM tooling falls back to parsing ``source:``).
    sha40 = _extract_commit_sha_40hex(upstream)
    if sha40:
        prov["imported_sha"] = sha40
    if owner_sha256:
        prov["owner_sha256"] = owner_sha256
    return prov


def target_path(domain: str, slug: str) -> Path:
    return SKILLS_DOMAIN_ROOT / domain / "skills" / slug / "SKILL.md"


def _verify_skip_rubric_authorization(
    source: Path,
    owner_sha256: Optional[str],
    signature_path: Optional[Path],
    signer_allowlist: Path,
) -> str:
    """PLAN-045 Wave 1 F-01-08: validate Owner authorization for --skip-rubric.

    Closes the supply-chain backdoor documented in PLAN-044 F-01-08.
    Previously ``--skip-rubric`` was a plain flag with no binding to
    actual Owner authentication; any agent with CLI access could
    import unvalidated SKILL.md. Three skills shipped this way under
    PLAN-033 Phase 3 with no retrospective proof of per-skill Owner
    authorization.

    Now ``--skip-rubric`` requires all three:

    1. ``--owner-sha256 <64-hex>`` — Owner-declared SHA-256 of a Owner-
       signed sentinel (matching the canonical-edit sentinel pattern).
       Callers typically compute this as
       ``sha256sum .claude/plans/PLAN-NNN/architect/round-N/approved.md``.
    2. ``source.asc`` (or ``<source>.asc``) — a detached GPG signature
       OVER the source SKILL.md file.
    3. Signer fingerprint in ``.claude/skill-patch-signers.txt``.

    Returns the signer fingerprint on success; raises ValueError on any
    failure mode with a stable reason prefix for log scraping.

    The returned fpr is injected into the target skill's provenance
    frontmatter as ``skip_rubric_signer_fpr:`` for forensic traceability
    — an auditor can diff the allowlist at import time vs today and
    detect retroactive allowlist expansion.
    """
    if not owner_sha256:
        raise ValueError(
            "--skip-rubric requires --owner-sha256 (Owner-signed sentinel hash)"
        )
    if not re.match(r"^[0-9a-fA-F]{64}$", owner_sha256):
        raise ValueError(
            f"--owner-sha256 must be 64-hex; got {owner_sha256!r}"
        )
    sig_path = signature_path if signature_path is not None else source.with_suffix(
        source.suffix + ".asc"
    )
    if not sig_path.is_file():
        raise ValueError(
            f"--skip-rubric requires a detached GPG signature at {sig_path} "
            f"(missing). See docs/SP-NNN-OWNER-WORKFLOW.md §skip-rubric."
        )
    # Delegate to the shared GPG verification helper.
    sys.path.insert(0, str(REPO_ROOT / ".claude" / "hooks"))
    try:
        from _lib import gpg_verify  # type: ignore
    except ImportError as e:
        raise ValueError(
            f"cannot import _lib.gpg_verify (hook lib missing?): {e}"
        )
    ok, fpr, reason = gpg_verify.verify_detached(
        source,
        sig_path,
        allowlist_path=signer_allowlist,
        timeout=15.0,
    )
    if not ok:
        raise ValueError(
            f"--skip-rubric signature verification failed: {reason}"
        )
    return fpr


def run_import(
    source: Path,
    domain: str,
    slug: str,
    upstream: str,
    license_spdx: str,
    sp_nnn: str,
    *,
    owner_sha256: Optional[str] = None,
    force: bool = False,
    skip_rubric: bool = False,
    notice_path: Optional[Path] = None,
    signature_path: Optional[Path] = None,
    signer_allowlist: Optional[Path] = None,
    license_extra: Optional[List[str]] = None,
) -> Path:
    """Do the import. Returns the written target path."""
    if not source.is_file():
        raise FileNotFoundError(f"source not found: {source}")

    # PLAN-045 F-14-03 closure: reject unknown licenses before any
    # I/O against the target tree.
    license_spdx = _validate_license_spdx(license_spdx, license_extra)

    # PLAN-045 F-11-03 closure: reject @main / @master / branch refs.
    # Upstream MUST be a commit SHA or signed tag for forensic
    # traceability.
    upstream = _validate_upstream_ref(upstream)

    skip_rubric_fpr: Optional[str] = None

    # Rubric gate (or Owner-authorized bypass).
    if skip_rubric:
        # PLAN-045 Wave 1 F-01-08: require real Owner signature.
        skip_rubric_fpr = _verify_skip_rubric_authorization(
            source,
            owner_sha256,
            signature_path,
            signer_allowlist if signer_allowlist is not None else _SIGNER_ALLOWLIST,
        )
    else:
        rubric = _load_rubric_module()
        result = rubric.evaluate(source)
        if not result.passed:
            fails = [
                f"{f.rule}: {f.detail}" for f in result.findings if not f.ok
            ]
            raise ValueError(
                f"source fails rubric: {'; '.join(fails)}"
            )

    tgt = target_path(domain, slug)
    if tgt.exists() and not force:
        raise FileExistsError(f"target exists (use --force): {tgt}")

    content = source.read_text(encoding="utf-8")
    fm_body, rest = _split_frontmatter(content)
    if not fm_body:
        raise ValueError("source has no frontmatter; rubric must have caught this")

    provenance = build_provenance(upstream, license_spdx, sp_nnn, owner_sha256)
    if skip_rubric_fpr:
        # Forensic provenance: who bypassed the rubric for this import.
        provenance["skip_rubric_signer_fpr"] = skip_rubric_fpr
    new_fm = _merge_frontmatter(fm_body, provenance)
    merged = f"---\n{new_fm}\n---\n{rest}"

    tgt.parent.mkdir(parents=True, exist_ok=True)
    tgt.write_text(merged, encoding="utf-8")

    if notice_path is not None:
        notice_path.parent.mkdir(parents=True, exist_ok=True)
        with notice_path.open("a", encoding="utf-8") as f:
            f.write(
                f"- `{domain}/skills/{slug}/SKILL.md` — "
                f"imported from `{upstream}` under `{license_spdx}` via "
                f"`{sp_nnn}` on {provenance['imported_at']}\n"
            )

    return tgt


# ---------------------------------------------------------------------------
# CLI
# ---------------------------------------------------------------------------


def build_parser() -> argparse.ArgumentParser:
    """Build the argparse parser for the community-skill importer CLI."""
    p = argparse.ArgumentParser(
        prog="import-skill",
        description="Import a curated SKILL.md with attribution + SP-NNN chain.",
    )
    p.add_argument("--source", required=True, type=Path)
    p.add_argument("--domain", required=True)
    p.add_argument("--slug", required=True)
    p.add_argument("--upstream", required=True, help="Upstream provenance tag (e.g. org/repo@tag)")
    p.add_argument("--license", dest="license_spdx", required=True, help="SPDX license id, e.g. CC-BY-4.0")
    p.add_argument("--sp-nnn", required=True, dest="sp_nnn", help="SP-NNN chain identifier (Owner signed)")
    p.add_argument("--owner-sha256", default=None, help="Optional SHA-256 of the Owner-signed sentinel")
    p.add_argument("--force", action="store_true", help="Overwrite existing target")
    p.add_argument(
        "--skip-rubric",
        action="store_true",
        help=(
            "Skip the rubric gate (rare — Owner override only). REQUIRES "
            "--owner-sha256 AND a sibling <source>.asc detached GPG "
            "signature, with signer fingerprint in "
            ".claude/skill-patch-signers.txt. See docs/SP-NNN-OWNER-WORKFLOW.md "
            "§skip-rubric. PLAN-045 Wave 1 F-01-08."
        ),
    )
    p.add_argument(
        "--signature",
        type=Path,
        default=None,
        help=(
            "Path to <source>.asc detached GPG signature (only used "
            "with --skip-rubric). Default: <source>.asc sibling."
        ),
    )
    p.add_argument(
        "--signer-allowlist",
        type=Path,
        default=None,
        help=(
            "Override path to signer-fpr allowlist (testing only). "
            "Default: .claude/skill-patch-signers.txt"
        ),
    )
    p.add_argument(
        "--license-extra",
        action="append",
        default=None,
        help=(
            "Extra SPDX license ids to accept beyond the built-in "
            "allowlist. Repeat for multiple entries. PLAN-045 F-14-03."
        ),
    )
    p.add_argument(
        "--notice",
        type=Path,
        default=None,
        help="Append an attribution row to this NOTICE.md",
    )
    return p


def main(argv: Optional[List[str]] = None) -> int:
    """CLI entrypoint — import one curated community skill through the rubric gate."""
    parser = build_parser()
    args = parser.parse_args(argv)
    try:
        tgt = run_import(
            source=args.source,
            domain=args.domain,
            slug=args.slug,
            upstream=args.upstream,
            license_spdx=args.license_spdx,
            sp_nnn=args.sp_nnn,
            owner_sha256=args.owner_sha256,
            force=args.force,
            skip_rubric=args.skip_rubric,
            notice_path=args.notice,
            signature_path=args.signature,
            signer_allowlist=args.signer_allowlist,
            license_extra=args.license_extra,
        )
    except (FileNotFoundError, FileExistsError, ValueError) as exc:
        print(f"error: {exc}", file=sys.stderr)
        return 1
    except Exception as exc:
        print(f"unexpected error: {exc}", file=sys.stderr)
        return 2
    print(f"OK: wrote {tgt}")
    return 0


if __name__ == "__main__":
    sys.exit(main())
