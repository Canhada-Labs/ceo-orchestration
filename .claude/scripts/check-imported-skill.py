#!/usr/bin/env python3
"""check-imported-skill.py — mechanical import gate for ported skills.

PLAN-153 Wave D (debate consensus #4). This is the MECHANICAL gate wired
into ``/skill-review`` that blocks catalog entry for a ported (externally
sourced) skill unless four conditions hold. Human line-by-line review
happens **on top** of this gate, never instead of it.

## Checks (all must pass)

(a) **Injection-corpus scan** — the imported ``SKILL.md`` is scanned with
    the existing prompt-injection corpus (``scan-injection.py``'s six
    families). Any match blocks. Content the security scan cannot read or
    decode is fail-CLOSED (blocked), per the house rule "fail-closed on
    input a security matcher cannot parse" (CLAUDE.md §4).

(b) **Well-formed provenance** — a ``NOTICE`` entry must exist for the
    skill's catalog path (the attribution ledger row written by
    ``import-skill.py --notice``), and the ``SKILL.md`` frontmatter must
    declare ``source:`` + ``license:``.

(c) **Review-attestation trailer** — the ``SKILL.md`` must carry a
    ``Skill-Import-Attestation:`` trailer that is well-formed AND binds to
    the reviewed bytes (its ``sha256`` must equal the digest of the
    ``SKILL.md`` with the trailer line removed). This makes the attestation
    non-theater: editing the skill after review invalidates it. Produce a
    valid trailer with the ``--attest`` mode below.

(d) **Ported-script safety** — sibling scripts shipped in the skill
    directory must not fetch upstream infrastructure (network calls) or
    execute upstream-supplied content (eval/exec/shell). Static heuristic
    scan; an unreadable script is fail-CLOSED (blocked).

## Quarantine (post-merge finding → disable)

Imports are reversible. When a post-merge finding lands, ``--quarantine``
moves the offending skill directory out of the catalog into
``<skills-root>/.quarantine/`` and records an audit breadcrumb. A typed
``skill_import_quarantined`` audit event is not yet registered (that is a
canonical kernel edit / separate SP chain); until then the breadcrumb +
the printed manual step are the durable trail.

## CLI

    check-imported-skill.py --skill <SKILL.md> --notice <NOTICE.md>
        exit 0 = pass, 1 = finding(s), 2 = usage error

    check-imported-skill.py --attest --skill <SKILL.md> --reviewed-by <id>
        print a content-bound attestation trailer to stdout (exit 0/2)

    check-imported-skill.py --quarantine <skill-dir-or-SKILL.md> [--dry-run]
        disable a merged skill (exit 0 = done/planned, 2 = bad path)

    Add --json to the check mode for machine-readable findings.

## Constraints (CLAUDE.md §4)

- stdlib only, Python >= 3.9; ``from __future__ import annotations``; no
  PEP 604 unions, no ``match``.
- Reuses ``scan-injection.py`` (loaded by path — its filename is
  hyphenated) rather than re-implementing the corpus.
"""

from __future__ import annotations

import argparse
import datetime as _dt
import hashlib
import importlib.util
import json
import os
import re
import sys
from dataclasses import dataclass
from pathlib import Path
from typing import Any, List, Optional, Tuple

_THIS_DIR = Path(__file__).resolve().parent           # .claude/scripts
_HOOKS_DIR = _THIS_DIR.parent / "hooks"               # .claude/hooks
if str(_HOOKS_DIR) not in sys.path:
    sys.path.insert(0, str(_HOOKS_DIR))


# ---- Result type ------------------------------------------------------------


@dataclass
class Finding:
    """One reason a ported skill is blocked from catalog entry."""

    check: str      # one of: injection, provenance, attestation, ported-script
    detail: str


# ---- (a) injection-corpus scan ---------------------------------------------


def _load_scan_injection() -> Optional[Any]:
    """Load the hyphen-named ``scan-injection.py`` module by path.

    Returns the module, or ``None`` if it cannot be loaded (caller treats
    a missing scanner as fail-closed — an admission gate must not admit
    unscanned content).
    """
    src = _THIS_DIR / "scan-injection.py"
    cached = sys.modules.get("scan_injection")
    if cached is not None and hasattr(cached, "scan_text"):
        return cached
    try:
        spec = importlib.util.spec_from_file_location("scan_injection", src)
        if spec is None or spec.loader is None:
            return None
        mod = importlib.util.module_from_spec(spec)
        # Register BEFORE exec: scan-injection.py uses @dataclass with
        # `from __future__ import annotations`, and the dataclass machinery
        # resolves `sys.modules[cls.__module__]` at class-creation time.
        sys.modules["scan_injection"] = mod
        spec.loader.exec_module(mod)
        return mod
    except Exception:
        sys.modules.pop("scan_injection", None)
        return None


def check_injection(skill_path: Path) -> List[Finding]:
    """Scan the SKILL.md with the injection corpus. Fail-closed on input.

    Blocks on any corpus match. Also blocks if the file cannot be read or
    decoded (input a security scan cannot parse) or if the scanner module
    is unavailable (cannot vouch for the content).
    """
    try:
        raw = skill_path.read_bytes()
    except OSError as exc:
        return [Finding("injection", f"SKILL.md unreadable (fail-closed): {exc}")]
    try:
        text = raw.decode("utf-8")
    except UnicodeDecodeError as exc:
        return [Finding("injection", f"SKILL.md is not valid UTF-8 (fail-closed): {exc}")]

    scanner = _load_scan_injection()
    if scanner is None:
        return [Finding("injection", "injection scanner unavailable (fail-closed)")]
    result = scanner.scan_text(text)
    if not getattr(result, "matched", False):
        return []
    fams = ", ".join(sorted(getattr(result, "family_counts", {}) or {})) or "unknown"
    return [Finding("injection", f"prompt-injection corpus matched families: {fams}")]


# ---- (b) provenance / NOTICE entry -----------------------------------------


_FRONTMATTER_RE = re.compile(r"^---\s*\n(.*?)\n---\s*\n", re.DOTALL)


def _frontmatter_keys(text: str) -> set:
    """Return the set of top-level frontmatter keys present in SKILL.md."""
    m = _FRONTMATTER_RE.match(text)
    if not m:
        return set()
    keys = set()
    for line in m.group(1).splitlines():
        km = re.match(r"^([a-zA-Z_][a-zA-Z0-9_-]*)\s*:", line)
        if km:
            keys.add(km.group(1))
    return keys


def _skill_relpaths(skill_path: Path) -> List[str]:
    """Candidate catalog-relative path tokens to search for in NOTICE.

    A NOTICE row may cite the skills-root-relative path
    (``domains/community/skills/foo/SKILL.md``), the domains-stripped form
    (``community/skills/foo/SKILL.md``), or just ``foo/SKILL.md``.
    """
    parts = skill_path.resolve().parts
    tokens: List[str] = []
    if "skills" in parts:
        idx = len(parts) - 1 - parts[::-1].index("skills")
        tokens.append("/".join(parts[idx:]))                    # skills/foo/... (rare)
    # domains/<d>/skills/<slug>/SKILL.md and the domains-stripped form.
    if "domains" in parts:
        didx = parts.index("domains")
        tokens.append("/".join(parts[didx:]))                   # domains/community/skills/foo/SKILL.md
        tokens.append("/".join(parts[didx + 1:]))               # community/skills/foo/SKILL.md (NOTICE row style)
    tokens.append("/".join(parts[-2:]))                         # foo/SKILL.md
    # de-dup preserving order
    seen: set = set()
    return [t for t in tokens if not (t in seen or seen.add(t))]


def check_provenance(skill_path: Path, notice_path: Path) -> List[Finding]:
    """Require a well-formed NOTICE row + source/license frontmatter."""
    findings: List[Finding] = []
    try:
        skill_text = skill_path.read_text(encoding="utf-8", errors="replace")
    except OSError as exc:
        return [Finding("provenance", f"SKILL.md unreadable: {exc}")]

    keys = _frontmatter_keys(skill_text)
    missing = [k for k in ("source", "license") if k not in keys]
    if missing:
        findings.append(Finding(
            "provenance", "SKILL.md frontmatter missing provenance key(s): "
            + ", ".join(missing)))

    try:
        notice = notice_path.read_text(encoding="utf-8")
    except OSError as exc:
        findings.append(Finding("provenance", f"NOTICE unreadable (fail-closed): {exc}"))
        return findings

    row = _matching_notice_row(notice, _skill_relpaths(skill_path))
    if row is None:
        findings.append(Finding(
            "provenance", "no NOTICE entry for this skill path "
            f"(searched: {', '.join(_skill_relpaths(skill_path))})"))
    elif not _notice_row_well_formed(row):
        findings.append(Finding(
            "provenance", "NOTICE row present but malformed "
            "(needs upstream 'from' + a license/SP reference): " + row.strip()[:120]))
    return findings


def _matching_notice_row(notice: str, tokens: List[str]) -> Optional[str]:
    """Return the first NOTICE line referencing any candidate path token."""
    for line in notice.splitlines():
        for tok in tokens:
            if tok and tok in line:
                return line
    return None


def _notice_row_well_formed(row: str) -> bool:
    """A provenance row must name an upstream AND a license/SP reference."""
    low = row.lower()
    has_upstream = ("imported from" in low) or ("from `" in low) or ("source" in low)
    has_license = bool(re.search(r"\bunder\b|licen[sc]e|spdx|\bsp-\d", low))
    return has_upstream and has_license


# ---- (c) review-attestation trailer ----------------------------------------

# Format: `Skill-Import-Attestation: reviewed-by=<id>; sha256=<64-hex>`
_ATTEST_RE = re.compile(
    r"^Skill-Import-Attestation:\s*reviewed-by=(?P<who>[^;]+?)\s*;\s*"
    r"sha256=(?P<sha>[0-9a-fA-F]{64})\s*$",
    re.MULTILINE,
)


def _strip_attestation_line(text: str) -> str:
    """Return ``text`` with the attestation trailer line removed.

    The declared sha256 binds to this stripped content, so the reviewer
    cannot attest one version and ship another.
    """
    out = []
    for line in text.splitlines(keepends=True):
        if _ATTEST_RE.match(line.rstrip("\n").rstrip("\r")):
            continue
        out.append(line)
    return "".join(out)


def compute_attestation(text: str, reviewed_by: str) -> str:
    """Build a content-bound attestation trailer for ``text``.

    Public helper so ``--attest`` and tests share one implementation.
    ``text`` should be the SKILL.md content WITHOUT an existing trailer.
    """
    who = reviewed_by.strip()
    if not who:
        raise ValueError("reviewed_by must be non-empty")
    digest = hashlib.sha256(_strip_attestation_line(text).encode("utf-8")).hexdigest()
    return "Skill-Import-Attestation: reviewed-by={0}; sha256={1}".format(who, digest)


def check_attestation(skill_path: Path) -> List[Finding]:
    """Require a present, well-formed, content-bound attestation trailer."""
    try:
        text = skill_path.read_text(encoding="utf-8")
    except (OSError, UnicodeDecodeError) as exc:
        return [Finding("attestation", f"SKILL.md unreadable (fail-closed): {exc}")]

    m = _ATTEST_RE.search(text)
    if m is None:
        return [Finding("attestation", "missing Skill-Import-Attestation trailer")]
    if not m.group("who").strip():
        return [Finding("attestation", "attestation trailer has empty reviewed-by")]
    expected = hashlib.sha256(
        _strip_attestation_line(text).encode("utf-8")).hexdigest()
    if m.group("sha").lower() != expected:
        return [Finding(
            "attestation", "attestation sha256 does not bind to SKILL.md content "
            "(skill edited after review, or hash forged)")]
    return []


# ---- (d) ported-script safety ----------------------------------------------

_SCRIPT_SUFFIXES = {
    ".py", ".sh", ".bash", ".zsh", ".js", ".mjs", ".cjs", ".ts",
    ".rb", ".pl", ".php", ".ps1", ".lua",
}

_NETWORK_RE = re.compile(
    r"https?://|wss?://|\burllib\b|urlopen|requests\.(?:get|post|put|delete|patch|head|request|Session)"
    r"|http\.client|httplib|aiohttp|httpx|\bsocket\.(?:socket|create_connection)"
    r"|\bftplib\b|\bsmtplib\b|\bcurl\b|\bwget\b|fetch\s*\(|XMLHttpRequest|axios"
    r"|net/http|Net::HTTP|LWP::|urllib\.request",
    re.IGNORECASE,
)

_EXEC_RE = re.compile(
    r"\beval\s*\(|\bexec\s*\(|os\.system\s*\(|subprocess\.(?:run|call|check_output|check_call|Popen)\s*\("
    r"|\bpopen\s*\(|pty\.spawn|commands\.getoutput|__import__\s*\(|compile\s*\("
    r"|child_process|Function\s*\(|\|\s*(?:bash|sh|zsh|python[0-9.]*)\b|\bsource\s+\S",
    re.IGNORECASE,
)


def _iter_ported_scripts(skill_dir: Path) -> List[Path]:
    """Yield candidate ported-script files under the skill directory."""
    scripts: List[Path] = []
    for root, _dirs, files in os.walk(skill_dir):
        for name in files:
            p = Path(root) / name
            if p.suffix.lower() in _SCRIPT_SUFFIXES:
                scripts.append(p)
            elif p.suffix == "" and _has_shebang(p):
                scripts.append(p)
    return sorted(scripts)


def _has_shebang(p: Path) -> bool:
    try:
        with p.open("rb") as fh:
            return fh.read(2) == b"#!"
    except OSError:
        return False


def check_ported_scripts(skill_dir: Path) -> List[Finding]:
    """Static-scan sibling scripts for network calls / exec of content."""
    findings: List[Finding] = []
    for script in _iter_ported_scripts(skill_dir):
        rel = script.name
        try:
            body = script.read_text(encoding="utf-8")
        except (OSError, UnicodeDecodeError) as exc:
            findings.append(Finding(
                "ported-script", f"{rel}: unreadable (fail-closed): {exc}"))
            continue
        net = _NETWORK_RE.search(body)
        if net:
            findings.append(Finding(
                "ported-script", f"{rel}: network call ({net.group(0).strip()!r})"))
        ex = _EXEC_RE.search(body)
        if ex:
            findings.append(Finding(
                "ported-script", f"{rel}: exec of external content ({ex.group(0).strip()!r})"))
    return findings


# ---- orchestration ----------------------------------------------------------


def run_checks(skill_path: Path, notice_path: Path) -> List[Finding]:
    """Run all four checks and return the aggregated findings list."""
    findings: List[Finding] = []
    findings.extend(check_injection(skill_path))
    findings.extend(check_provenance(skill_path, notice_path))
    findings.extend(check_attestation(skill_path))
    findings.extend(check_ported_scripts(skill_path.parent))
    return findings


# ---- quarantine -------------------------------------------------------------


def _resolve_skill_dir(target: Path) -> Optional[Path]:
    """Return the skill directory for ``target`` (a dir or its SKILL.md)."""
    t = target.resolve()
    if t.is_file() and t.name == "SKILL.md":
        return t.parent
    if t.is_dir():
        return t
    return None


def _skills_root_of(skill_dir: Path) -> Optional[Path]:
    """Return the OUTERMOST ``skills`` root above ``skill_dir``, if any.

    Uses the first ``skills`` path segment so quarantine lands under the
    top-level catalog root (``.claude/skills/.quarantine/``), clearly out
    of every tier's ``skills/*/SKILL.md`` catalog glob.
    """
    parts = skill_dir.resolve().parts
    if "skills" not in parts:
        return None
    idx = parts.index("skills")
    return Path(*parts[: idx + 1])


def quarantine_skill(
    target: Path,
    *,
    dry_run: bool = False,
    errors_log: Optional[Path] = None,
) -> Tuple[int, dict]:
    """Disable a merged skill by moving it out of the catalog.

    Returns ``(exit_code, plan)``. ``exit_code`` is 0 on success/plan, 2
    on a bad path (not a skill dir, or outside a ``.claude/skills`` root).
    """
    skill_dir = _resolve_skill_dir(target)
    if skill_dir is None:
        return 2, {"error": f"not a skill directory or SKILL.md: {target}"}
    skills_root = _skills_root_of(skill_dir)
    # Must be STRICTLY inside a skills root (root itself is never quarantined).
    if skills_root is None or skills_root not in skill_dir.resolve().parents:
        return 2, {"error": f"skill dir is not under a skills root: {skill_dir}"}

    ts = _dt.datetime.now(_dt.timezone.utc).strftime("%Y%m%dT%H%M%SZ")
    dest = skills_root / ".quarantine" / f"{skill_dir.name}-{ts}"
    plan = {
        "action": "skill_import_quarantined",
        "skill_dir": str(skill_dir),
        "dest": str(dest),
        "dry_run": dry_run,
    }
    if dry_run:
        return 0, plan

    dest.parent.mkdir(parents=True, exist_ok=True)
    skill_dir.replace(dest)
    _write_quarantine_breadcrumb(plan, errors_log)
    return 0, plan


def _write_quarantine_breadcrumb(plan: dict, errors_log: Optional[Path]) -> None:
    """Best-effort audit breadcrumb into the audit-log.errors sidecar.

    A typed ``skill_import_quarantined`` emitter is not registered yet
    (kernel edit); this sidecar line + the printed manual step are the
    durable trail. Never raises (fail-open on the breadcrumb only).
    """
    path = errors_log or _default_errors_log()
    try:
        path.parent.mkdir(parents=True, exist_ok=True)
        ts = _dt.datetime.now(_dt.timezone.utc).strftime("%Y-%m-%dT%H:%M:%SZ")
        line = (f"{ts} check-imported-skill: skill_import_quarantined "
                f"skill_dir={plan['skill_dir']} dest={plan['dest']}\n")
        with path.open("a", encoding="utf-8") as fh:
            fh.write(line)
    except Exception:
        pass


def _default_errors_log() -> Path:
    override = os.environ.get("CEO_AUDIT_LOG_ERR")
    if override:
        return Path(override)
    home = Path(os.environ.get("HOME") or str(Path.home()))
    return home / ".claude" / "projects" / "ceo-orchestration" / "audit-log.errors"


# ---- CLI --------------------------------------------------------------------


def _build_parser() -> argparse.ArgumentParser:
    p = argparse.ArgumentParser(
        description="Mechanical import gate for ported skills (PLAN-153 Wave D).")
    p.add_argument("--skill", type=Path, help="Path to the imported SKILL.md")
    p.add_argument("--notice", type=Path, help="Path to the NOTICE attribution ledger")
    p.add_argument("--attest", action="store_true",
                   help="Print a content-bound attestation trailer for --skill")
    p.add_argument("--reviewed-by", default="",
                   help="Reviewer identity for --attest")
    p.add_argument("--quarantine", type=Path, default=None,
                   help="Disable a merged skill (dir or SKILL.md); move out of catalog")
    p.add_argument("--dry-run", action="store_true",
                   help="With --quarantine, print the plan without moving")
    p.add_argument("--json", action="store_true", dest="as_json",
                   help="Machine-readable output for check mode")
    return p


def _run_attest(args: argparse.Namespace) -> int:
    if args.skill is None or not args.skill.is_file():
        sys.stderr.write("[check-imported-skill] --attest requires --skill <SKILL.md>\n")
        return 2
    if not args.reviewed_by.strip():
        sys.stderr.write("[check-imported-skill] --attest requires --reviewed-by <id>\n")
        return 2
    text = _strip_attestation_line(args.skill.read_text(encoding="utf-8"))
    print(compute_attestation(text, args.reviewed_by))
    return 0


def _run_check(args: argparse.Namespace) -> int:
    if args.skill is None or args.notice is None:
        sys.stderr.write(
            "[check-imported-skill] check mode requires --skill and --notice\n")
        return 2
    if not args.skill.is_file():
        sys.stderr.write(f"[check-imported-skill] SKILL.md not found: {args.skill}\n")
        return 2
    findings = run_checks(args.skill, args.notice)
    if args.as_json:
        print(json.dumps(
            {"passed": not findings,
             "findings": [{"check": f.check, "detail": f.detail} for f in findings]},
            indent=2))
    else:
        _print_findings_human(args.skill, findings)
    return 1 if findings else 0


def _print_findings_human(skill: Path, findings: List[Finding]) -> None:
    if not findings:
        sys.stdout.write(f"PASS {skill}: import gate clean (4/4 checks)\n")
        return
    sys.stdout.write(f"BLOCK {skill}: {len(findings)} finding(s)\n")
    for f in findings:
        sys.stdout.write(f"  [{f.check}] {f.detail}\n")


def _run_quarantine(args: argparse.Namespace) -> int:
    rc, plan = quarantine_skill(args.quarantine, dry_run=args.dry_run)
    if rc != 0:
        sys.stderr.write(f"[check-imported-skill] {plan.get('error', 'quarantine failed')}\n")
        return rc
    verb = "PLAN" if args.dry_run else "QUARANTINED"
    sys.stdout.write(f"{verb} {plan['skill_dir']} -> {plan['dest']}\n")
    if not args.dry_run:
        sys.stdout.write(
            "Manual step: append a `skill_import_quarantined` note to the "
            "domain NOTICE + open a follow-up so the typed audit event lands.\n")
    return 0


def main(argv: Optional[List[str]] = None) -> int:
    """Dispatch between attest, quarantine, and check modes."""
    args = _build_parser().parse_args(argv)
    if args.attest:
        return _run_attest(args)
    if args.quarantine is not None:
        return _run_quarantine(args)
    return _run_check(args)


if __name__ == "__main__":
    sys.exit(main())
