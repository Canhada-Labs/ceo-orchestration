#!/usr/bin/env python3
"""confidence-gate — verify CLAIM tokens in spawn output against the repo.

PLAN-008 Phase 2. Advisory-only in Sprint 8 — never blocks a spawn.
Collects FPR baseline for Sprint 9 enforcement decision.

## Grammar (ADR-018)

Inline tokens in agent output:

    CLAIM:<kind>:<args>

Where `<kind>` is one of:

    path_exists | function_exists | sha_exists | test_passes | line_range

And `<args>` is either raw (no whitespace, backtick, or `:`) or
backtick-quoted (to allow `:`-containing args like pytest selectors).

Tokens inside fenced code blocks (triple-backtick delimited, at
start-of-line) are IGNORED.

## Exit codes (debate consensus C4)

    0 — at least one claim passed, zero failed (or: 0 passed, 0 failed but claims found equivocally)
    1 — at least one claim failed verification (advisory signal)
    2 — usage / argument error
    3 — zero claims found in input (distinct signal for Sprint 9)

## Sprint 9 pre-work (PLAN-009 Phase 1 C1.0)

- `_scoped_resolve` rejects `..` escape, absolute-outside-repo, and
  symlinks crossing the repo boundary (PLAN-009 A2 / R-SEC2).
- `verify_test_passes` locks argv prefix + enforces strict selector
  regex (PLAN-009 A3 / R-SEC3).
- `extract_claims` bounded by `CEO_CONFIDENCE_MAX_CLAIMS` (default 200)
  and emits `truncated=true` + `claim_count_raw` via the Report
  (PLAN-009 A12).

## Usage

    confidence_gate.py --input FILE
    confidence_gate.py --stdin < FILE
    confidence_gate.py --json [--input FILE | --stdin]
    confidence_gate.py --agent-name NAME [...]

Emits `confidence_gate` audit event (schema v2) with reserved fields:
claim_count, pass_count, fail_count, verifier_kind_counts, agent_name,
source.

Stdlib-only. Python >= 3.9.
"""

from __future__ import annotations

import argparse
import ast
import json
import os
import re
import subprocess
import sys
from dataclasses import dataclass, field
from pathlib import Path
from typing import Any, Dict, List, Optional, Tuple

# Make _lib importable — confidence_gate.py lives in .claude/scripts/,
# _lib lives in .claude/hooks/_lib/
_HOOKS_DIR = Path(__file__).resolve().parent.parent / "hooks"
if str(_HOOKS_DIR) not in sys.path:
    sys.path.insert(0, str(_HOOKS_DIR))

try:
    from _lib.audit_emit import emit_confidence_gate as _emit_confidence_gate
    _AUDIT_EMIT_AVAILABLE = True
except ImportError:
    _AUDIT_EMIT_AVAILABLE = False


# ---------------------------------------------------------------------------
# Grammar
# ---------------------------------------------------------------------------

# kind must be snake_case letters + underscores only (ADR-018 forward-compat)
# args: either quoted in backticks OR a raw sequence of non-space,
# non-backtick, non-colon chars. Raw args cannot contain ":" (use quoting).
CLAIM_RE = re.compile(
    r"CLAIM:(?P<kind>[a-z_]+):"
    r"(?:`(?P<quoted>[^`]+)`|(?P<raw>[^\s:`]+))"
)

KNOWN_KINDS = {
    "path_exists",
    "function_exists",
    "sha_exists",
    "test_passes",
    "line_range",
    "import_resolves",  # ADR-018 v1.1 (Sprint 9 C1.2) — syntactic-only
}

# ADR-018 v1.1 — import_resolves grammar
# Matches: dotted identifiers like ``foo``, ``foo.bar``, ``pkg.sub.mod``
# Rejects anything starting with ``.``, containing ``/``, or containing
# non-identifier characters. The kind is **syntactic + file-existence
# only**; NO importlib.util.find_spec calls. See PLAN-009 Security R-SEC1
# for the RCE sink this explicitly avoids.
_IMPORT_DOTTED_RE = re.compile(r"^[A-Za-z_]\w*(?:\.[A-Za-z_]\w*)*$")

# Normative block-list of forbidden import prefixes (ADR-018 v1.1). Agents
# have no legitimate reason to CLAIM that `os`, `subprocess`, `sys`, or
# any dunder module "resolves" — those are always-available in CPython and
# CLAIMing them is either noise or an attempt to confuse the verifier.
_IMPORT_BLOCKED_TOPLEVEL = frozenset({
    "os",
    "subprocess",
    "sys",
    "importlib",
    "builtins",
    "__builtins__",
    "__main__",
})

# PLAN-009 A12: bound claim extraction to prevent DoS via pathological output.
# Default 200; env override `CEO_CONFIDENCE_MAX_CLAIMS`.
_DEFAULT_MAX_CLAIMS = 200

# PLAN-009 A3: strict pytest selector regex. Allows only:
#   <dotted/slash/dash/dot/underscore path>.py
#   optionally followed by up to 2 `::selector` segments
#   where each selector is [A-Za-z0-9_[]-]+
_PYTEST_SELECTOR_RE = re.compile(
    # File part: dotted/slash/dash/underscore then .py
    # Each `::name` segment must NOT start with '-' (blocks pytest flags
    # like `::--help` that would otherwise pass the char-class check).
    r"^[A-Za-z0-9_./-]+\.py(?:::[A-Za-z0-9_\[\]][A-Za-z0-9_\[\]\-]*){0,2}$"
)


def _get_max_claims() -> int:
    """Read `CEO_CONFIDENCE_MAX_CLAIMS` env var with fallback."""
    raw = os.environ.get("CEO_CONFIDENCE_MAX_CLAIMS", "")
    if not raw:
        return _DEFAULT_MAX_CLAIMS
    try:
        val = int(raw)
        if val < 1:
            return _DEFAULT_MAX_CLAIMS
        return val
    except ValueError:
        return _DEFAULT_MAX_CLAIMS


def _scoped_resolve(user_arg: str, repo_root: Path) -> Path:
    """Resolve a user-supplied path under ``repo_root``.

    PLAN-009 A2 / R-SEC2: verifier inputs come from untrusted agent output.
    We must NOT let a claim point at a path outside the repo (e.g.
    ``/etc/passwd``, ``../../.ssh/id_rsa``, or a symlink that resolves
    outside the tree).

    Contract:
    - ``user_arg`` may be relative (anchored to ``repo_root``) or absolute.
    - After ``Path.resolve()``, the final path MUST be inside
      ``repo_root.resolve()`` (or equal to it).
    - ``..`` traversal that escapes the root is rejected.
    - Absolute paths outside the root are rejected.
    - Symlinks whose resolved target escapes the root are rejected (resolve
      is strict=False so nonexistent suffixes do not raise; the early
      ancestor is what determines containment).

    Raises ``ValueError`` on rejection. The caller converts this into a
    verifier ``(False, detail)`` result.
    """
    if not user_arg:
        raise ValueError("empty path")
    # Reject NUL bytes and other control chars up front
    if "\x00" in user_arg:
        raise ValueError("null byte in path")
    candidate = Path(user_arg)
    if not candidate.is_absolute():
        candidate = repo_root / candidate
    try:
        resolved = candidate.resolve(strict=False)
        root_resolved = repo_root.resolve(strict=False)
    except (OSError, RuntimeError) as e:
        raise ValueError(f"resolve failed: {type(e).__name__}: {e}")
    # Containment check: resolved must be root_resolved or a descendant
    try:
        resolved.relative_to(root_resolved)
    except ValueError:
        raise ValueError(f"path escapes repo root: {user_arg!r}")
    return resolved


@dataclass
class Claim:
    """A parsed CLAIM token with its context."""

    kind: str
    args: str  # unquoted value
    raw_token: str  # full matched token text (for reporting)
    line_num: int  # 1-based line number where token was found


@dataclass
class VerificationResult:
    """Result of verifying a single claim."""

    claim: Claim
    passed: bool
    detail: str = ""  # short explanation (path not found, function not in AST, etc.)
    kind_supported: bool = True  # False if kind is not in KNOWN_KINDS


# ---------------------------------------------------------------------------
# Extraction — skips fenced code blocks (ADR-018)
# ---------------------------------------------------------------------------


def extract_claims(
    text: str, max_claims: Optional[int] = None
) -> Tuple[List[Claim], int, bool]:
    """Extract CLAIM tokens from text, ignoring fenced code blocks.

    Fenced code blocks are lines that start (after stripping) with
    triple-backtick. State toggles on each fence line. The fence line
    itself is never scanned.

    PLAN-009 A12: extraction is bounded by ``max_claims`` (default from
    env var ``CEO_CONFIDENCE_MAX_CLAIMS`` or 200). When the input contains
    more CLAIM tokens than the cap, we return only the first ``max_claims``
    and report ``raw_count > len(claims)`` + ``truncated=True``. The caller
    surfaces this via the audit event (mirrors ``injection_flag`` truncated
    precedent, ADR-011).

    Returns ``(claims, raw_count, truncated)``.
    """
    if max_claims is None:
        max_claims = _get_max_claims()
    claims: List[Claim] = []
    raw_count = 0
    in_code_block = False
    for lineno, line in enumerate(text.splitlines(), start=1):
        stripped = line.lstrip()
        if stripped.startswith("```"):
            in_code_block = not in_code_block
            continue
        if in_code_block:
            continue
        for match in CLAIM_RE.finditer(line):
            kind = match.group("kind")
            args = match.group("quoted") or match.group("raw") or ""
            if not args:
                continue
            raw_count += 1
            if len(claims) < max_claims:
                claims.append(
                    Claim(
                        kind=kind,
                        args=args,
                        raw_token=match.group(0),
                        line_num=lineno,
                    )
                )
    truncated = raw_count > len(claims)
    return claims, raw_count, truncated


# ---------------------------------------------------------------------------
# Verifiers — one per kind
# ---------------------------------------------------------------------------


def verify_path_exists(args: str, repo_root: Path) -> Tuple[bool, str]:
    """Return (passed, detail). Path resolved under repo_root (PLAN-009 A2)."""
    try:
        p = _scoped_resolve(args, repo_root)
    except ValueError as e:
        return False, f"path rejected: {e}"
    if p.exists():
        return True, f"path exists: {p}"
    return False, f"path not found: {p}"


def verify_function_exists(args: str, repo_root: Path) -> Tuple[bool, str]:
    """Args format: 'module-path:function-name'.

    Parses the file with `ast`, walks all FunctionDef and AsyncFunctionDef
    nodes (at module level OR as class methods), matches by name.
    """
    if ":" not in args:
        return False, f"function_exists args missing ':' separator: {args!r}"
    module_path, fn_name = args.rsplit(":", 1)
    try:
        p = _scoped_resolve(module_path, repo_root)
    except ValueError as e:
        return False, f"path rejected: {e}"
    if not p.is_file():
        return False, f"module file not found: {p}"
    try:
        source = p.read_text(encoding="utf-8", errors="replace")
        tree = ast.parse(source, filename=str(p))
    except (SyntaxError, OSError) as e:
        return False, f"parse failed: {type(e).__name__}: {e}"
    for node in ast.walk(tree):
        if isinstance(node, (ast.FunctionDef, ast.AsyncFunctionDef)):
            if node.name == fn_name:
                return True, f"function {fn_name!r} found at {p}:{node.lineno}"
    return False, f"function {fn_name!r} not found in {p}"


def verify_sha_exists(args: str, repo_root: Path) -> Tuple[bool, str]:
    """Use `git cat-file -e <sha>` to test existence."""
    sha = args.strip()
    if not re.fullmatch(r"[0-9a-f]{7,40}", sha):
        return False, f"not a valid SHA format: {sha!r}"
    try:
        result = subprocess.run(
            ["git", "-C", str(repo_root), "cat-file", "-e", sha],
            capture_output=True,
            text=True,
            timeout=5,
        )
    except (OSError, subprocess.TimeoutExpired) as e:
        return False, f"git invocation failed: {type(e).__name__}: {e}"
    if result.returncode == 0:
        return True, f"sha {sha} exists"
    return False, f"sha {sha} not found (git exit {result.returncode})"


def verify_test_passes(args: str, repo_root: Path) -> Tuple[bool, str]:
    """Use `pytest --collect-only -q <selector>`; collection success ≈ test exists.

    PLAN-009 A3 / R-SEC3: the selector is untrusted input. We enforce:
    1. Strict regex allowing only ``<path>.py[::name[::name]]`` where the
       file part is dotted/slash/dash/underscore and each ``::name`` is
       a bracket/alnum/underscore identifier. No spaces, no ``--``,
       no leading ``-``, no ``=``.
    2. File portion must resolve under repo_root (scoped).
    3. Argv prefix is locked: ``--rootdir=<repo>``, ``-p no:cacheprovider``,
       ``--no-header``.

    Note: advisory mode does NOT run the tests; we only verify the
    selector is discoverable.
    """
    selector = args.strip()
    if not _PYTEST_SELECTOR_RE.fullmatch(selector):
        return False, f"pytest selector rejected (malformed): {selector!r}"
    # Sanity check: the file portion of the selector must exist under the root
    file_part = selector.split("::", 1)[0]
    try:
        fp = _scoped_resolve(file_part, repo_root)
    except ValueError as e:
        return False, f"test file rejected: {e}"
    if not fp.is_file():
        return False, f"test file not found: {fp}"
    # Locked argv prefix — `--` not used because our regex forbids ``-``-leading
    # tokens, but we still pin rootdir and disable cache plugin.
    argv = [
        sys.executable,
        "-m",
        "pytest",
        "--collect-only",
        "-q",
        f"--rootdir={repo_root}",
        "-p",
        "no:cacheprovider",
        "--no-header",
        selector,
    ]
    try:
        result = subprocess.run(
            argv,
            cwd=str(repo_root),
            capture_output=True,
            text=True,
            timeout=15,
        )
    except (OSError, subprocess.TimeoutExpired) as e:
        return False, f"pytest invocation failed: {type(e).__name__}: {e}"
    if result.returncode == 0:
        return True, f"pytest collected {selector}"
    # Fallback: pytest may not be installed / configured. We treat that
    # as UNVERIFIABLE, not fail — return False with a specific detail so
    # the Sprint 9 FPR analysis can distinguish.
    return False, f"pytest could not collect (rc={result.returncode})"


def verify_line_range(args: str, repo_root: Path) -> Tuple[bool, str]:
    """Args format: 'path:start-end'. Checks that file has ≥ `end` lines."""
    if ":" not in args:
        return False, f"line_range args missing ':' separator: {args!r}"
    path_part, range_part = args.rsplit(":", 1)
    m = re.fullmatch(r"(\d+)-(\d+)", range_part)
    if not m:
        return False, f"line_range args malformed range: {range_part!r}"
    start = int(m.group(1))
    end = int(m.group(2))
    if start < 1 or end < start:
        return False, f"line_range invalid start/end: {start}-{end}"
    try:
        p = _scoped_resolve(path_part, repo_root)
    except ValueError as e:
        return False, f"path rejected: {e}"
    if not p.is_file():
        return False, f"file not found: {p}"
    try:
        # count lines without loading entire file (bounded reader)
        with p.open("rb") as f:
            line_count = sum(1 for _ in f)
    except OSError as e:
        return False, f"read failed: {type(e).__name__}: {e}"
    if line_count >= end:
        return True, f"file has {line_count} lines (>= {end})"
    return False, f"file has only {line_count} lines, need {end}"


def verify_import_resolves(args: str, repo_root: Path) -> Tuple[bool, str]:
    """Args: dotted import path like ``foo.bar.baz``.

    ADR-018 v1.1 (Sprint 9 C1.2). **Syntactic + file-existence only** —
    no ``importlib.util.find_spec`` calls (that API triggers parent
    package ``__init__.py`` execution, which is an RCE sink under
    untrusted-agent-output threat model; Security R-SEC1).

    Verification:
    1. Dotted path matches ``^[A-Za-z_]\\w*(\\.[A-Za-z_]\\w*)*$``
    2. Top-level component not in the block-list (``os``, ``subprocess``,
       ``sys``, ``importlib``, ``builtins``, dunder modules)
    3. Either ``<root>/<part0>.py`` exists OR
       ``<root>/<part0>/__init__.py`` exists

    Relative paths (``./path.py``) and filesystem paths containing ``/``
    are NOT in this kind — route those claims through ``path_exists``.
    """
    if not args or not isinstance(args, str):
        return False, f"import_resolves args empty/invalid: {args!r}"
    if args.startswith("."):
        return False, f"import_resolves rejects relative import: {args!r}"
    if "/" in args:
        return False, f"import_resolves rejects filesystem path: {args!r}"
    if not _IMPORT_DOTTED_RE.fullmatch(args):
        return False, f"import_resolves syntax invalid: {args!r}"

    parts = args.split(".")
    top = parts[0]
    if top in _IMPORT_BLOCKED_TOPLEVEL:
        return False, f"import_resolves rejects block-listed module: {top!r}"

    # File-existence check only. `_scoped_resolve` guards against escape
    # via the top-level name (which is a bare identifier, so it can't
    # contain `..` or absolute paths — but we route through it anyway
    # for uniform failure semantics).
    try:
        candidate_module = _scoped_resolve(f"{top}.py", repo_root)
        candidate_pkg_init = _scoped_resolve(
            os.path.join(top, "__init__.py"), repo_root
        )
    except ValueError as e:
        return False, f"import_resolves path scope failed: {e}"

    if candidate_module.is_file():
        return True, f"import {args!r} resolves: {candidate_module} (module)"
    if candidate_pkg_init.is_file():
        return True, f"import {args!r} resolves: {candidate_pkg_init} (package)"
    return False, f"import {args!r} not found ({top}.py or {top}/__init__.py)"


VERIFIERS = {
    "path_exists": verify_path_exists,
    "function_exists": verify_function_exists,
    "sha_exists": verify_sha_exists,
    "test_passes": verify_test_passes,
    "line_range": verify_line_range,
    "import_resolves": verify_import_resolves,  # ADR-018 v1.1
}


def verify_claim(claim: Claim, repo_root: Path) -> VerificationResult:
    """Dispatch to the appropriate verifier."""
    if claim.kind not in KNOWN_KINDS:
        return VerificationResult(
            claim=claim,
            passed=False,
            detail=f"unknown kind: {claim.kind!r}",
            kind_supported=False,
        )
    verifier = VERIFIERS[claim.kind]
    passed, detail = verifier(claim.args, repo_root)
    return VerificationResult(claim=claim, passed=passed, detail=detail)


# ---------------------------------------------------------------------------
# Aggregation
# ---------------------------------------------------------------------------


@dataclass
class Report:
    """Aggregate verification results.

    Sprint 9 (A12) adds ``raw_claim_count`` + ``truncated`` to reflect
    pre-cap claim volume when ``extract_claims`` hit the bound.
    """

    results: List[VerificationResult] = field(default_factory=list)
    raw_claim_count: int = 0  # pre-cap CLAIM tokens in input
    truncated: bool = False  # True when raw_claim_count > len(results)

    @property
    def claim_count(self) -> int:
        """Number of claims actually verified (post-cap)."""
        return len(self.results)

    @property
    def pass_count(self) -> int:
        """Number of verified claims whose verifier returned passed=True."""
        return sum(1 for r in self.results if r.passed)

    @property
    def fail_count(self) -> int:
        """Number of verified claims whose verifier returned passed=False."""
        return sum(1 for r in self.results if not r.passed)

    @property
    def verifier_kind_counts(self) -> Dict[str, int]:
        """Histogram of verifier kinds invoked (e.g. ``{'import': 4, 'file': 2}``)."""
        counts: Dict[str, int] = {}
        for r in self.results:
            counts[r.claim.kind] = counts.get(r.claim.kind, 0) + 1
        return counts

    def exit_code(self) -> int:
        """4-exit-code scheme per debate consensus C4."""
        if self.claim_count == 0:
            return 3
        if self.fail_count > 0:
            return 1
        return 0


def verify_text(text: str, repo_root: Path) -> Report:
    """Full pipeline: extract → verify → aggregate.

    PLAN-009 A12: extraction is bounded; ``Report`` carries ``raw_claim_count``
    and ``truncated`` so the CLI + audit emitter can surface the delta.
    """
    claims, raw_count, truncated = extract_claims(text)
    results = [verify_claim(c, repo_root) for c in claims]
    if raw_count == 0:
        raw_count = len(results)
    return Report(results=results, raw_claim_count=raw_count, truncated=truncated)


# ---------------------------------------------------------------------------
# CLI
# ---------------------------------------------------------------------------


# PLAN-090-FOLLOWUP Wave B.1 — claim severity mapping (ADR-018 closed enum).
# Pinned against KNOWN_KINDS at confidence_gate.py:92-99.
_SEVERITY_BY_KIND = {
    "path_exists":     "info",      # cheap existence assertion
    "function_exists": "warn",      # AST-level claim; high-frequency
    "sha_exists":      "critical",  # git-state claim; if wrong -> forensic gap
    "test_passes":     "critical",  # green-bar claim; gating impact
    "line_range":      "info",      # narrow scope; low blast
    "import_resolves": "warn",      # ADR-018 v1.1 — syntactic+file-existence
}


def _claim_severity(kind: str) -> str:
    """Return ADR-018 severity for a Claim.kind.

    Defaults to "info" on unknown kind (covers KNOWN_KINDS evolution
    without forcing a synchronous _SEVERITY_BY_KIND update).
    """
    return _SEVERITY_BY_KIND.get(kind, "info")


def _format_human(report: Report) -> str:
    """Human-readable report."""
    lines = []
    lines.append(f"Claims found: {report.claim_count}")
    lines.append(f"Passed: {report.pass_count}")
    lines.append(f"Failed: {report.fail_count}")
    if report.verifier_kind_counts:
        lines.append("By kind:")
        for kind, count in sorted(report.verifier_kind_counts.items()):
            lines.append(f"  {kind}: {count}")
    if report.results:
        lines.append("")
        lines.append("Details:")
        for r in report.results:
            status = "PASS" if r.passed else "FAIL"
            lines.append(
                f"  [{status}] line {r.claim.line_num}: "
                f"{r.claim.raw_token}  ->  {r.detail}"
            )
    return "\n".join(lines) + "\n"


def _format_json(report: Report, agent_name: str, source: str) -> str:
    """Machine-readable JSON output.

    PLAN-090-FOLLOWUP Wave B.1 — additionally emits `claims` list with
    per-claim payload the PostToolUse hook consumes (claim_id, severity,
    payload_hash, verdict, was_false_positive, kind_supported,
    verifier_outcome_raw transient, claim_args_for_overlap_check
    transient). Transients are consumed inside the hook (passed to
    _safe_verifier_outcome with both inputs in scope) and DROPPED before
    audit-log persist via emit_generic allowlist scrub.
    """
    import hashlib
    import unicodedata
    claims_payload = []
    for r in report.results:
        body_norm = unicodedata.normalize("NFKC", (r.claim.args or "").strip())
        payload_hash = hashlib.sha256(
            body_norm.encode("utf-8", errors="replace")
        ).hexdigest()[:12]
        claim_id = f"{r.claim.kind}:{payload_hash}"
        verdict = "pass" if r.passed else "fail"
        kind_supported = bool(r.kind_supported)
        # P0-1 fold — extraction-level FP signal from kind_supported.
        # When the verifier could not even attempt verification because
        # the kind is unknown to KNOWN_KINDS, the original claim is an
        # extraction false-positive. Produces non-zero FP rates per
        # class from day 1 of soak.
        was_false_positive = not kind_supported
        claims_payload.append({
            "claim_id": claim_id,
            "claim_type": r.claim.kind,
            "severity": _claim_severity(r.claim.kind),
            "verifier_kind": r.claim.kind,
            "verdict": verdict,
            "was_false_positive": was_false_positive,
            "kind_supported": kind_supported,
            "payload_hash": payload_hash,
            "line_num": r.claim.line_num,
            # Transient — consumed in-hook, NOT persisted
            "verifier_outcome_raw": r.detail,
            "claim_args_for_overlap_check": r.claim.args,
        })
    out = {
        "claim_count": report.claim_count,
        "raw_claim_count": report.raw_claim_count,
        "truncated": report.truncated,
        "pass_count": report.pass_count,
        "fail_count": report.fail_count,
        "verifier_kind_counts": report.verifier_kind_counts,
        "agent_name": agent_name,
        "source": source,
        "exit_code": report.exit_code(),
        "results": [
            {
                "kind": r.claim.kind,
                "args": r.claim.args,
                "line_num": r.claim.line_num,
                "passed": r.passed,
                "detail": r.detail,
                "kind_supported": r.kind_supported,
            }
            for r in report.results
        ],
        "claims": claims_payload,
    }
    return json.dumps(out, indent=2, ensure_ascii=False) + "\n"


def _read_input(args: argparse.Namespace) -> Tuple[str, str]:
    """Return (text, source_label)."""
    if args.stdin:
        return sys.stdin.read(), "stdin"
    if args.input:
        return Path(args.input).read_text(encoding="utf-8", errors="replace"), args.input
    raise SystemExit(2)


def main(argv: Optional[List[str]] = None) -> int:
    """CLI entrypoint — evaluate confidence-gate state for a plan transition."""
    parser = argparse.ArgumentParser(
        description="Verify CLAIM tokens in agent output (advisory, Sprint 8).",
    )
    source_group = parser.add_mutually_exclusive_group(required=True)
    source_group.add_argument("--input", help="Path to file to scan")
    source_group.add_argument("--stdin", action="store_true", help="Read from stdin")

    parser.add_argument("--json", action="store_true", help="JSON output instead of human-readable")
    parser.add_argument("--agent-name", default="", help="Agent name to attach to audit event")
    parser.add_argument("--repo-root", default=None, help="Override repo root (default: cwd)")
    parser.add_argument(
        "--no-emit",
        action="store_true",
        help="Skip writing the confidence_gate audit event (useful for tests)",
    )
    args = parser.parse_args(argv)

    try:
        text, source = _read_input(args)
    except FileNotFoundError as e:
        print(f"ERROR: input file not found: {e}", file=sys.stderr)
        return 2
    except OSError as e:
        print(f"ERROR: cannot read input: {e}", file=sys.stderr)
        return 2

    repo_root = Path(args.repo_root).resolve() if args.repo_root else Path.cwd()
    report = verify_text(text, repo_root)

    if args.json:
        sys.stdout.write(_format_json(report, args.agent_name, source))
    else:
        sys.stdout.write(_format_human(report))

    if not args.no_emit and _AUDIT_EMIT_AVAILABLE:
        try:
            _emit_confidence_gate(
                claim_count=report.claim_count,
                pass_count=report.pass_count,
                fail_count=report.fail_count,
                verifier_kind_counts=report.verifier_kind_counts,
                agent_name=args.agent_name,
                source=source,
                raw_claim_count=report.raw_claim_count,
                truncated=report.truncated,
            )
        except Exception:
            # fail-open observability per ADR-005 pattern
            pass

    return report.exit_code()


if __name__ == "__main__":
    sys.exit(main())
