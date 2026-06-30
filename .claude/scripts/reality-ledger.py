#!/usr/bin/env python3
"""reality-ledger.py — Adaptive Execution Kernel claim-vs-evidence detector (advisory-only).

PLAN-071 §4.3 Phase 2 deliverable. Walks the repo for divergence between
documented claims and runtime/code evidence, emitting findings in markdown
(local triage) or JSON/JSONL (audit-log + GH issue body) format.

ADVISORY ONLY: this script never blocks the CEO. Output is consumed by
humans + weekly CI advisory. Exit code 0 = success (with or without
findings), 2 = detector internal error (Sec NTH #5).

Detectors v1.14.0 (5 active; #5 default_flip_orphan deferred to v1.15.0+):
  1. runtime_read_missing       — env-var documented but no AST-level read
  2. installable_claim_drift    — installable claim, but install at HEAD fails
  3. model_assignment_divergence — claimed model != observed-majority model
  4. enforcement_commit_unpopulated — ADR ACCEPTED but no enforcement_commit SHA
  6. audit_action_phantom       — emitted action missing in _KNOWN_ACTIONS

Exclusions (anti-self-referential, post Round 1 R-SEC3):
  All detectors exclude `task-route.py`, `reality-ledger.py`, and
  `owner-ceremony/archive/**` from grep targets.

Output rendering (R2 R-CR-R2-3 + Codex P1 #1):
  --format markdown      INCLUDES claim_source_path  (local triage only)
  --format json/jsonl    EXCLUDES claim_source_path; SHA-only (audit-safe)

Audit emission (deferred until KERNEL ceremony Phase 5 lands
`reality_ledger_finding` action in `audit_emit._KNOWN_ACTIONS`):
  hasattr-guarded best-effort emit; advisory-only fallback when unwired.
"""

from __future__ import annotations

import argparse
import ast
import hashlib
import json
import os
import re
import sys
import time
import unicodedata
import uuid
from datetime import datetime, timezone
from pathlib import Path
from typing import Any, Dict, FrozenSet, Iterable, List, Optional, Tuple

# ---------------------------------------------------------------------------
# _lib / hooks imports — composition, not reimplementation
# ---------------------------------------------------------------------------

_REPO_ROOT = Path(__file__).resolve().parent.parent.parent
_HOOKS_LIB = _REPO_ROOT / ".claude" / "hooks"

if str(_HOOKS_LIB) not in sys.path:
    sys.path.insert(0, str(_HOOKS_LIB))

try:
    from _lib.redact import redact_secrets  # noqa: F401  used in actual_evidence
    from _lib.secret_patterns import (
        _install_itimer_guard,
        _clear_itimer_guard,
        ScanBudgetExceeded,
    )
except ImportError as exc:
    sys.stderr.write(
        f"[reality-ledger] FATAL import error: {exc.__class__.__name__}: {exc}\n"
    )
    sys.exit(2)

# audit_emit is imported lazily / hasattr-guarded inside _try_emit_finding
# so that running the script in environments where the action is not yet
# registered (pre-Phase-5 KERNEL ceremony) still works as advisory-only.

# ---------------------------------------------------------------------------
# Constants
# ---------------------------------------------------------------------------

SCHEMA_VERSION = "reality-ledger-finding.v1"

DEFAULT_DETECTOR_TIMEOUT_MS = 120000  # PLAN-107 S145 raised 5000->15000ms; PLAN-112-FOLLOWUP S158 raised 15000->120000ms — the AST-walk of the further-grown hooks+scripts tree now takes ~50s isolated and ~60s under full-suite load (measured), exceeding the old 15s cap consistently. 120s gives ~2x CI-hardware margin. Advisory detector; the cap only bounds completion. Honest accommodation of codebase growth, not a logic change.
SUITE_LATENCY_BUDGET_S = 30.0  # informational p95 budget per spec

# Severities (ordering matters for filtering)
_SEVERITIES = ("low", "medium", "high")
_SEVERITY_ORDER = {"low": 0, "medium": 1, "high": 2}

# Detector registry — slug -> human label + default severity
DETECTOR_REGISTRY: Dict[str, Dict[str, Any]] = {
    "runtime_read_missing": {"severity": "medium"},
    "installable_claim_drift": {"severity": "high"},
    "model_assignment_divergence": {"severity": "medium"},
    "enforcement_commit_unpopulated": {"severity": "low"},
    "audit_action_phantom": {"severity": "medium"},
    # PLAN-078 Wave 2 — estimate-drift detector. Severity is computed
    # per-finding by drift factor (low <1.5×, medium 1.5-2×, high >2×);
    # registry value is the default fallback when severity is unset.
    "estimate_drift": {"severity": "medium"},
}

# Anti-self-referential exclusion globs (post Round 1 R-SEC3).
SELF_EXCLUDE_BASENAMES = frozenset({
    "task-route.py",
    "reality-ledger.py",
})
SELF_EXCLUDE_PATH_FRAGMENTS = (
    "owner-ceremony/archive/",
    "/owner-ceremony/archive/",
    # PLAN-112-FOLLOWUP S158 — exclude plan `staging/` dirs from the scan.
    # They hold DRAFT mirrors of production code/docs (ready-to-apply
    # packages), NOT production claims, and the ~30 staging `.md` files
    # were inflating the `.md` detectors' scan (md_roots includes `.claude`)
    # past the detector timeout. Drafts must not be scanned as reality.
    "/staging/",
)

# Audit emission allowlist (Sec MF-3 contract; extended in Phase 5 KERNEL).
_REALITY_LEDGER_FINDING_ALLOWLIST: FrozenSet[str] = frozenset({
    "action", "ts", "detector", "severity",
    # confidence_bps: int basis-points (0..1000); replaces old float "confidence"
    # which caused CanonicalJsonError in the HMAC-covered canonical_json encoder.
    "confidence_bps",
    "claim_source_sha256", "finding_count_in_run",
})

# Markdown-only field set (MUST be excluded from JSON/JSONL).
_MARKDOWN_ONLY_FIELDS: FrozenSet[str] = frozenset({"claim_source_path"})

# Env-var prefix convention enforced by detector #1: only names matching
# this prefix family are surfaced as documented env-vars. Avoids the
# combinatorial false-positive set of every UPPER_SNAKE backtick token in
# planning docs (`_KNOWN_ACTIONS`, `VETO_HARDCODE`, `STDOUT`, etc).
_ENV_PREFIX_RE = re.compile(
    r"^("
    r"CEO_|CLAUDE_|ANTHROPIC_|"
    r"GITHUB_|GH_|"
    r"OTEL_|OTEL_EXPORTER_|"
    r"NPM_|"
    r"AWS_|GCP_|GOOGLE_|"
    r"DATABASE_|DB_|"
    r"OPENAI_|"
    r"COVERALLS_|CODECOV_|"
    r"SENTRY_|"
    r"PYTHONPATH$|PATH$|HOME$"
    r")"
)

# Doc-side regex: env var names appearing as `$VAR`, `VAR=value`, or
# inside backticks. Min 5 chars (e.g. `CEO_X`) to prevent matching the
# bare prefix `CEO_` (4 chars). Convention floor `_ENV_PREFIX_RE`
# additionally requires at least 1 char after the prefix underscore.
# Body of the env-var name: starts upper, ≥4 chars, ends in a non-underscore.
# Prevents `ANTHROPIC_` (trailing underscore = a prefix mention, not a name).
_ENV_NAME_BODY = r"[A-Z][A-Z0-9_]{2,62}[A-Z0-9]"
_BACKTICK_ENV_RE = re.compile(r"`(" + _ENV_NAME_BODY + r")`")
_SHELL_ASSIGN_RE = re.compile(r"\b(" + _ENV_NAME_BODY + r")=[^\s]")
_DOLLAR_VAR_RE = re.compile(r"\$(" + _ENV_NAME_BODY + r")\b")

# ADR Status field forms supported.
_ADR_STATUS_RE = re.compile(
    r"^(?:>\s*)?\*{0,2}Status:?\*{0,2}\s*[:\-]?\s*(.+?)\s*$",
    re.MULTILINE,
)
# Many ADRs use "**Status:** ACCEPTED ..." or "> **Status:** ..."
_ADR_ENFORCEMENT_HEADER_RE = re.compile(
    r"^##\s+Enforcement\s+commit\s*$",
    re.MULTILINE | re.IGNORECASE,
)
_ENFORCEMENT_SHA_RE = re.compile(r"`([0-9a-f]{7,40})`")
_ENFORCEMENT_PLACEHOLDER_RE = re.compile(
    r"\((?:populated\s+on\s+flip|pending|TBD|to\s+be\s+populated|_pending_)",
    re.IGNORECASE,
)

# Detector #6 — emit_<action> regex inside python source.
_EMIT_CALL_RE = re.compile(
    r"\bemit_generic\s*\(\s*action\s*=\s*[\"']([a-z][a-z0-9_]*)[\"']"
)
_EMIT_NAMED_RE = re.compile(
    r"\baudit_emit\s*\.\s*emit_([a-z][a-z0-9_]*)\s*\("
)


# ---------------------------------------------------------------------------
# File walking utilities (deterministic, exclusion-aware)
# ---------------------------------------------------------------------------

def _is_excluded(path: Path, *, repo_root: Path) -> bool:
    try:
        rel = path.resolve().relative_to(repo_root.resolve())
    except (ValueError, OSError):
        return True
    rel_posix = str(rel).replace(os.sep, "/")
    if path.name in SELF_EXCLUDE_BASENAMES:
        return True
    for frag in SELF_EXCLUDE_PATH_FRAGMENTS:
        if frag in ("/" + rel_posix):
            return True
    # Hidden directories beyond .claude / .github should be ignored
    parts = rel.parts
    for p in parts[:-1]:
        if p.startswith(".") and p not in (".claude", ".github"):
            return True
    return False


def _iter_python_files(roots: Iterable[Path], *, repo_root: Path) -> List[Path]:
    out: List[Path] = []
    for root in roots:
        if not root.exists():
            continue
        for p in sorted(root.rglob("*.py")):
            if _is_excluded(p, repo_root=repo_root):
                continue
            out.append(p)
    return out


def _iter_md_files(roots: Iterable[Path], *, repo_root: Path) -> List[Path]:
    out: List[Path] = []
    for root in roots:
        if not root.exists():
            continue
        for p in sorted(root.rglob("*.md")):
            if _is_excluded(p, repo_root=repo_root):
                continue
            out.append(p)
    return out


# ---------------------------------------------------------------------------
# Detector #1 — runtime_read_missing (AST-level)
# ---------------------------------------------------------------------------

class _EnvVarReadFinder(ast.NodeVisitor):
    """Walk AST collecting env var names actually READ at runtime.

    Recognised forms:
      - os.environ.get('VAR'[, default])
      - os.environ['VAR']
      - os.getenv('VAR'[, default])
      - subprocess.run(env={'VAR': ...})  (treated as USE — call-site sets var
        for child process; not a "read" but proves runtime wiring.)
      - dict-key string literals inside subprocess.run(env={...}) calls.
    """

    def __init__(self) -> None:
        self.read_vars: set = set()

    @staticmethod
    def _arg_str(node: ast.AST) -> Optional[str]:
        if isinstance(node, ast.Constant) and isinstance(node.value, str):
            return node.value
        return None

    def visit_Call(self, node: ast.Call) -> None:  # noqa: N802
        # os.getenv('VAR') / os.getenv('VAR', default)
        # os.environ.get('VAR')
        func = node.func
        # Resolve attribute chain
        attr_chain: List[str] = []
        cur: Any = func
        while isinstance(cur, ast.Attribute):
            attr_chain.append(cur.attr)
            cur = cur.value
        if isinstance(cur, ast.Name):
            attr_chain.append(cur.id)
        attr_chain.reverse()
        chain = ".".join(attr_chain)

        if chain in ("os.getenv", "getenv") and node.args:
            v = self._arg_str(node.args[0])
            if v:
                self.read_vars.add(v)
        elif chain in ("os.environ.get", "environ.get") and node.args:
            v = self._arg_str(node.args[0])
            if v:
                self.read_vars.add(v)
        # subprocess.run(env={...})
        elif chain.endswith("subprocess.run") or chain.endswith(".run") or chain == "run":
            for kw in node.keywords or []:
                if kw.arg == "env" and isinstance(kw.value, ast.Dict):
                    for k in kw.value.keys:
                        v = self._arg_str(k)
                        if v:
                            self.read_vars.add(v)
        self.generic_visit(node)

    def visit_Subscript(self, node: ast.Subscript) -> None:  # noqa: N802
        # os.environ['VAR']  -> Subscript(value=Attribute(os.environ), slice=Constant)
        val = node.value
        attr_chain: List[str] = []
        cur: Any = val
        while isinstance(cur, ast.Attribute):
            attr_chain.append(cur.attr)
            cur = cur.value
        if isinstance(cur, ast.Name):
            attr_chain.append(cur.id)
        attr_chain.reverse()
        chain = ".".join(attr_chain)
        if chain in ("os.environ", "environ"):
            slc: Any = node.slice
            if isinstance(slc, ast.Constant) and isinstance(slc.value, str):
                self.read_vars.add(slc.value)
        self.generic_visit(node)


def _ast_collect_runtime_env_reads(py_files: List[Path]) -> Dict[str, List[str]]:
    """Returns {VAR_NAME: [posix_path, ...]} of files that actually read it."""
    out: Dict[str, List[str]] = {}
    for f in py_files:
        try:
            source = f.read_text(encoding="utf-8", errors="replace")
            tree = ast.parse(source, filename=str(f))
        except (OSError, SyntaxError):
            continue
        finder = _EnvVarReadFinder()
        try:
            finder.visit(tree)
        except Exception:
            continue
        for v in finder.read_vars:
            out.setdefault(v, []).append(_to_repo_rel(f))
    return out


def _doc_collect_documented_env_vars(md_files: List[Path]) -> Dict[str, List[str]]:
    """Returns {VAR_NAME: [posix_path:line, ...]} of doc files that mention it.

    Detection forms:
      - backtick-wrapped UPPER_SNAKE token  (`CEO_MODEL_DOWNSHIFT`)
      - shell assignment                    (CEO_MODEL_DOWNSHIFT=1)
      - dollar-sign reference               ($CEO_MODEL_DOWNSHIFT)

    Only names matching `_ENV_PREFIX_RE` survive — this is the explicit
    "convention floor" that prevents the planning-doc false positives
    (`_KNOWN_ACTIONS`, `VETO_HARDCODE`, `STDOUT`, etc.).
    """
    out: Dict[str, List[str]] = {}
    regexes = (_BACKTICK_ENV_RE, _SHELL_ASSIGN_RE, _DOLLAR_VAR_RE)
    for f in md_files:
        try:
            text = f.read_text(encoding="utf-8", errors="replace")
        except OSError:
            continue
        for lineno, line in enumerate(text.splitlines(), start=1):
            for rgx in regexes:
                for m in rgx.finditer(line):
                    v = m.group(1)
                    if _ENV_PREFIX_RE.match(v) and _is_plausible_env_var(v):
                        out.setdefault(v, []).append(f"{_to_repo_rel(f)}:{lineno}")
    return out


def _is_plausible_env_var(name: str) -> bool:
    """Filter common false positives (file extensions, Python keywords, etc.).

    Heuristics:
      - must start with letter, contain underscore OR be ≥6 chars
      - exclude common all-caps tokens that are not env vars (HTTP, JSON, etc.)
    """
    if not name:
        return False
    if len(name) < 4:
        return False
    if "_" not in name and len(name) < 6:
        return False
    EXCLUDE = {
        "HTTP", "HTTPS", "JSON", "YAML", "TOML", "MARKDOWN", "TODO", "FIXME",
        "NOTE", "WARNING", "ERROR", "INFO", "DEBUG", "TRACE",
        "README", "CLAUDE", "VERSION", "CHANGELOG", "PROTOCOL", "PYTHON",
        "ASCII", "UTF", "UNICODE", "REGEX", "GOTCHA", "OPTIONAL", "REQUIRED",
        "EXAMPLE", "CRITICAL", "MANDATORY", "ALL_CAPS", "UPPER_CASE",
        "GLOBAL", "LOCAL", "STATIC", "DYNAMIC", "PUBLIC", "PRIVATE",
        "TRUE", "FALSE", "NONE", "NULL", "UNDEFINED",
    }
    if name in EXCLUDE:
        return False
    return True


def detect_runtime_read_missing(
    *,
    repo_root: Path,
    explicit_env_vars: Optional[List[str]] = None,
) -> List[Dict[str, Any]]:
    """Detector #1.

    For each env var documented in a .md under `docs/` or `.claude/`,
    AST-scan `.claude/scripts` + `.claude/hooks` for runtime reads.
    Variables documented but NEVER actually read → finding.
    """
    findings: List[Dict[str, Any]] = []

    md_roots = [repo_root / "docs", repo_root / ".claude"]
    py_roots = [repo_root / ".claude" / "scripts", repo_root / ".claude" / "hooks"]
    md_files = _iter_md_files(md_roots, repo_root=repo_root)
    py_files = _iter_python_files(py_roots, repo_root=repo_root)

    documented = _doc_collect_documented_env_vars(md_files)
    runtime = _ast_collect_runtime_env_reads(py_files)

    if explicit_env_vars:
        documented = {v: documented.get(v, []) for v in explicit_env_vars}

    runtime_vars = set(runtime.keys())

    for var, doc_locations in sorted(documented.items()):
        if not doc_locations:
            continue
        if var in runtime_vars:
            continue
        # Cosmetic mentions only; no AST-level read
        first_loc = doc_locations[0]
        evidence = (
            f"0 enforcement reads; {len(doc_locations)} cosmetic mention(s) filtered"
        )
        finding = _build_finding(
            detector="runtime_read_missing",
            severity=DETECTOR_REGISTRY["runtime_read_missing"]["severity"],
            confidence=0.95,
            claim_source_path=first_loc,
            expected_evidence=(
                f"ast_scan_for_env_var('{var}', "
                "target_dirs=['.claude/scripts','.claude/hooks'], "
                "exclude=['task-route.py','reality-ledger.py',"
                "'owner-ceremony/archive/**'])"
            ),
            actual_evidence=evidence,
            advisory_action="either wire the runtime read or amend the doc",
            extra={"env_var": var, "doc_locations": doc_locations[:5]},
        )
        findings.append(finding)
    return findings


# ---------------------------------------------------------------------------
# Detector #2 — installable_claim_drift
# ---------------------------------------------------------------------------

def detect_installable_claim_drift(
    *,
    repo_root: Path,
) -> List[Dict[str, Any]]:
    """Detector #2.

    Currently checks `.claude/rag/requirements.lock` — if the file exists
    but contains the marker text "PLACEHOLDER" / "NOT a valid pip install
    target", emit finding. Future: actually invoke `pip install --dry-run`.
    """
    findings: List[Dict[str, Any]] = []
    target = repo_root / ".claude" / "rag" / "requirements.lock"
    if not target.exists():
        return findings
    try:
        text = target.read_text(encoding="utf-8", errors="replace")
    except OSError:
        return findings
    rel = _to_repo_rel(target)
    placeholder_markers = (
        "PLACEHOLDER",
        "NOT a valid pip install target",
        "MUST refuse to run",
    )
    matched = [m for m in placeholder_markers if m in text]
    if matched:
        finding = _build_finding(
            detector="installable_claim_drift",
            severity=DETECTOR_REGISTRY["installable_claim_drift"]["severity"],
            confidence=0.99,
            claim_source_path=f"{rel}:1",
            expected_evidence=(
                f"pip install --require-hashes --no-deps -r {rel} returns 0"
            ),
            actual_evidence=(
                f"requirements.lock is a placeholder; markers found: {matched}"
            ),
            advisory_action=(
                "regenerate via pip-compile per the file's header instructions"
            ),
            extra={"target": rel, "markers": matched},
        )
        findings.append(finding)
    return findings


# ---------------------------------------------------------------------------
# Detector #3 — model_assignment_divergence (advisory v1 — claim-side only)
# ---------------------------------------------------------------------------

_AGENT_FRONTMATTER_MODEL_RE = re.compile(
    r"^model:\s*([a-zA-Z0-9._\-]+)\s*$", re.MULTILINE
)


def detect_model_assignment_divergence(
    *,
    repo_root: Path,
    audit_log_path: Optional[Path] = None,
) -> List[Dict[str, Any]]:
    """Detector #3.

    v1 implementation collects claimed `model:` from agent frontmatter and
    compares against optional audit-log observation when an `audit_log_path`
    is provided. When the audit log is absent (sandbox / fresh checkout),
    the detector returns []. Production deployment passes
    `~/.claude/projects/.../audit-log.jsonl` via CLI flag.

    Phase 2 v1.14.0 ships the claim-collection + diff scaffold;
    full 30d observation rollup is wired in Phase 4 advisory CI.
    """
    findings: List[Dict[str, Any]] = []
    agents_dir = repo_root / ".claude" / "agents"
    if not agents_dir.exists():
        return findings

    claimed: Dict[str, str] = {}
    paths: Dict[str, str] = {}
    for f in sorted(agents_dir.rglob("*.md")):
        if _is_excluded(f, repo_root=repo_root):
            continue
        try:
            text = f.read_text(encoding="utf-8", errors="replace")
        except OSError:
            continue
        m = _AGENT_FRONTMATTER_MODEL_RE.search(text)
        if not m:
            continue
        slug = f.stem
        claimed[slug] = m.group(1)
        paths[slug] = _to_repo_rel(f)

    if not audit_log_path or not audit_log_path.exists():
        return findings

    observed: Dict[str, Dict[str, int]] = {}
    try:
        with audit_log_path.open(encoding="utf-8", errors="replace") as fh:
            for line in fh:
                try:
                    ev = json.loads(line)
                except ValueError:
                    continue
                if ev.get("action") != "agent_spawn":
                    continue
                role = ev.get("subagent_type") or ev.get("role") or ""
                model = ev.get("model") or ""
                if not role or not model:
                    continue
                observed.setdefault(role, {}).setdefault(model, 0)
                observed[role][model] += 1
    except OSError:
        return findings

    for role, claim_model in sorted(claimed.items()):
        bucket = observed.get(role)
        if not bucket:
            continue
        majority = max(bucket.items(), key=lambda kv: kv[1])
        if majority[0] != claim_model:
            finding = _build_finding(
                detector="model_assignment_divergence",
                severity=DETECTOR_REGISTRY["model_assignment_divergence"]["severity"],
                confidence=0.85,
                claim_source_path=paths.get(role, ""),
                expected_evidence=(
                    f"claim model={claim_model} matches observed-majority "
                    "in last 30d audit-log"
                ),
                actual_evidence=(
                    f"observed majority={majority[0]} (n={majority[1]}); "
                    f"claim={claim_model}"
                ),
                advisory_action=(
                    "either update agent frontmatter or investigate routing"
                ),
                extra={"role": role, "claim": claim_model,
                       "observed": majority[0], "n": majority[1]},
            )
            findings.append(finding)
    return findings


# ---------------------------------------------------------------------------
# Detector #4 — enforcement_commit_unpopulated
# ---------------------------------------------------------------------------

def detect_enforcement_commit_unpopulated(
    *,
    repo_root: Path,
) -> List[Dict[str, Any]]:
    """Detector #4.

    For every ADR with Status containing 'ACCEPTED' (case-insensitive),
    look for an `## Enforcement commit` section that contains either no
    SHA reference or a placeholder string ('(populated on flip)' etc.).
    """
    findings: List[Dict[str, Any]] = []
    adr_dir = repo_root / ".claude" / "adr"
    if not adr_dir.exists():
        return findings
    for f in sorted(adr_dir.glob("ADR-*.md")):
        if _is_excluded(f, repo_root=repo_root):
            continue
        try:
            text = f.read_text(encoding="utf-8", errors="replace")
        except OSError:
            continue
        # Find Status line (first match wins)
        status_match = _ADR_STATUS_RE.search(text)
        if not status_match:
            continue
        status_value = status_match.group(1).strip()
        if "ACCEPTED" not in status_value.upper():
            continue
        # Skip SUPERSEDED / RETRACTED / REJECTED
        if any(k in status_value.upper() for k in ("SUPERSEDED", "RETRACTED", "REJECTED")):
            continue

        header_match = _ADR_ENFORCEMENT_HEADER_RE.search(text)
        if not header_match:
            # Section absent on an ACCEPTED ADR is itself a finding.
            rel = _to_repo_rel(f)
            findings.append(_build_finding(
                detector="enforcement_commit_unpopulated",
                severity=DETECTOR_REGISTRY["enforcement_commit_unpopulated"]["severity"],
                confidence=0.95,
                claim_source_path=f"{rel}:1",
                expected_evidence=(
                    "## Enforcement commit section with backtick-wrapped SHA"
                ),
                actual_evidence="section absent",
                advisory_action="add Enforcement commit section + SHA",
                extra={"adr": f.name, "status": status_value},
            ))
            continue

        # Capture body until next H2 or EOF
        start = header_match.end()
        next_h2 = re.search(r"^##\s+", text[start:], re.MULTILINE)
        body_end = start + next_h2.start() if next_h2 else len(text)
        body = text[start:body_end]
        body_lineno = text[:header_match.start()].count("\n") + 1
        sha_match = _ENFORCEMENT_SHA_RE.search(body)
        placeholder_match = _ENFORCEMENT_PLACEHOLDER_RE.search(body)

        unpopulated = False
        reason = ""
        if not sha_match:
            unpopulated = True
            reason = "no SHA reference"
        elif placeholder_match:
            # Has a SHA pattern AND a placeholder marker — placeholder wins
            unpopulated = True
            reason = f"placeholder marker: {placeholder_match.group(0)!r}"

        # ADR-067 ground truth: text contains "(populated on flip"
        if not sha_match and not placeholder_match:
            # Maybe still empty (whitespace only)
            if not body.strip():
                unpopulated = True
                reason = "empty body"

        if unpopulated:
            rel = _to_repo_rel(f)
            findings.append(_build_finding(
                detector="enforcement_commit_unpopulated",
                severity=DETECTOR_REGISTRY["enforcement_commit_unpopulated"]["severity"],
                confidence=0.97,
                claim_source_path=f"{rel}:{body_lineno}",
                expected_evidence=(
                    "## Enforcement commit body contains backtick-wrapped SHA "
                    "(7-40 hex chars) + no placeholder markers"
                ),
                actual_evidence=reason,
                advisory_action=(
                    "populate enforcement_commit with the SHA where the "
                    "decision was wired"
                ),
                extra={"adr": f.name, "status": status_value},
            ))
    return findings


# ---------------------------------------------------------------------------
# Detector #6 — audit_action_phantom
# ---------------------------------------------------------------------------

def _read_known_actions(audit_emit_path: Path) -> set:
    """Parse `_KNOWN_ACTIONS = { ... }` from audit_emit.py via AST."""
    try:
        source = audit_emit_path.read_text(encoding="utf-8", errors="replace")
        tree = ast.parse(source, filename=str(audit_emit_path))
    except (OSError, SyntaxError):
        return set()
    out: set = set()
    for node in ast.walk(tree):
        if isinstance(node, ast.Assign):
            for tgt in node.targets:
                if isinstance(tgt, ast.Name) and tgt.id == "_KNOWN_ACTIONS":
                    val = node.value
                    if isinstance(val, (ast.Set, ast.List, ast.Tuple)):
                        for elt in val.elts:
                            if isinstance(elt, ast.Constant) and isinstance(elt.value, str):
                                out.add(elt.value)
    return out


class _EmitActionFinder(ast.NodeVisitor):
    """Walk AST collecting action= literals from emit_generic(...) Call nodes.

    AST-level avoids false positives in docstrings / regex examples / comments
    that the regex form inevitably catches (Codex precedent: docstring example
    literal `emit_generic(action="name", ...)` got flagged as phantom).
    """

    def __init__(self) -> None:
        # action_name -> list of (lineno,)
        self.actions: Dict[str, List[int]] = {}

    def visit_Call(self, node: ast.Call) -> None:  # noqa: N802
        # Only consider calls whose callee ends in `emit_generic`.
        func = node.func
        callee_chain: List[str] = []
        cur: Any = func
        while isinstance(cur, ast.Attribute):
            callee_chain.append(cur.attr)
            cur = cur.value
        if isinstance(cur, ast.Name):
            callee_chain.append(cur.id)
        callee_chain.reverse()
        last = callee_chain[-1] if callee_chain else ""
        if last == "emit_generic":
            # Find action= keyword OR first positional
            action_val: Optional[str] = None
            for kw in node.keywords or []:
                if kw.arg == "action" and isinstance(kw.value, ast.Constant) \
                        and isinstance(kw.value.value, str):
                    action_val = kw.value.value
                    break
            if action_val is None and node.args:
                first = node.args[0]
                if isinstance(first, ast.Constant) and isinstance(first.value, str):
                    action_val = first.value
            if action_val:
                self.actions.setdefault(action_val, []).append(node.lineno)
        self.generic_visit(node)


def _scan_emitted_actions(py_files: List[Path], *, repo_root: Path) -> Dict[str, List[str]]:
    """Find action names emitted in code via emit_generic(...) — AST-level only.

    Skips files whose path includes `tests/` to avoid catching fixture
    strings / mocked event payloads. Skips files inside `_lib/audit_emit.py`
    itself (its own dispatch table must reference all actions; not a phantom).

    `repo_root` is required because we compute the relative path from the
    *target* root (which may be a fixture root in tests), not the
    framework root. Without this, a fixture under `…/tests/fixtures/…`
    in the framework checkout was always filtered out as "tests/".
    """
    out: Dict[str, List[str]] = {}
    for f in py_files:
        try:
            rel = str(f.resolve().relative_to(repo_root.resolve())).replace(os.sep, "/")
        except (ValueError, OSError):
            rel = _to_repo_rel(f)
        # Exclude tests + audit_emit.py itself
        if "/tests/" in ("/" + rel) or rel.endswith("audit_emit.py"):
            continue
        try:
            source = f.read_text(encoding="utf-8", errors="replace")
            tree = ast.parse(source, filename=str(f))
        except (OSError, SyntaxError):
            continue
        finder = _EmitActionFinder()
        try:
            finder.visit(tree)
        except Exception:
            continue
        for action, linenos in finder.actions.items():
            for ln in linenos:
                out.setdefault(action, []).append(f"{rel}:{ln}")
    return out


def _legacy_scan_emitted_actions(py_files: List[Path]) -> Dict[str, List[str]]:
    """Backward-compat wrapper used in unit-tests of the original signature."""
    return _scan_emitted_actions(py_files, repo_root=_REPO_ROOT)


def detect_audit_action_phantom(
    *,
    repo_root: Path,
) -> List[Dict[str, Any]]:
    """Detector #6.

    Phantom = action emitted in code but missing from `_KNOWN_ACTIONS`
    (silent drop precedent: Codex S76 `skill_bootstrap_used` regression).
    """
    findings: List[Dict[str, Any]] = []
    audit_emit_path = repo_root / ".claude" / "hooks" / "_lib" / "audit_emit.py"
    if not audit_emit_path.exists():
        return findings

    known = _read_known_actions(audit_emit_path)
    py_roots = [repo_root / ".claude" / "scripts", repo_root / ".claude" / "hooks"]
    py_files = _iter_python_files(py_roots, repo_root=repo_root)
    emitted = _scan_emitted_actions(py_files, repo_root=repo_root)

    # Phantom: emitted but not registered
    phantoms = sorted(set(emitted.keys()) - known)
    for action in phantoms:
        first_loc = emitted[action][0]
        finding = _build_finding(
            detector="audit_action_phantom",
            severity=DETECTOR_REGISTRY["audit_action_phantom"]["severity"],
            confidence=0.99,
            claim_source_path=first_loc,
            expected_evidence=(
                f"action {action!r} present in audit_emit._KNOWN_ACTIONS"
            ),
            actual_evidence=(
                f"emitted in {len(emitted[action])} site(s); not registered"
            ),
            advisory_action=(
                "add action to _KNOWN_ACTIONS via KERNEL ceremony OR rename "
                "the emit call site"
            ),
            extra={"action": action, "emit_sites": emitted[action][:5]},
        )
        findings.append(finding)
    return findings


# ---------------------------------------------------------------------------
# Detector #7 — estimate_drift  (PLAN-078 Wave 2)
# ---------------------------------------------------------------------------
#
# On plans whose `status: done` transition fired, compares the original
# `estimate.compute_hours` + `estimate.owner_physical_min` against the
# observed actuals (commit time-span + GPG-signed-commit count + manual
# override). Finding emitted when |drift_factor| ≥ 1.2 in either axis.
#
# Implementation discipline (Codex re-pass + plan §4.2):
#   - SINGLE batched `git log --pretty=%H,%aI --name-only` (~1 subprocess
#     call, NOT 1-per-plan) — see _git_log_paths().
#   - `created` field preferred over `created_at` (PLAN-SCHEMA §2 use).
#   - actual_owner_physical_min derived from GPG-signed commit count + an
#     optional `actual_owner_physical_min:` plan-frontmatter override
#     (clamped 0..10000; non-int → fail-open warn).
#   - severity bands: low <1.5×, medium 1.5-2×, high >2×.
#   - systematic_bias_direction: emitted ONLY in the run-summary recommend
#     event when N≥5 plans drift same direction.
#   - CSV append at `.claude/scripts/local/calibration-history.csv`
#     (gitignored). Each row keyed by `<plan_id>,<run_iso8601>` so re-runs
#     are idempotent (existing rows are NOT duplicated).
#   - Bypass: `CEO_REALITY_LEDGER_DETECTOR_07=0`.
#
# Output: List of finding dicts (run_detectors aggregator handles render +
# emit). Each finding embeds plan-level deltas in `_extra` for forensics.

_PLAN_FILE_RE = re.compile(r"^PLAN-(\d{3,4})-.*\.md$")
_HOURS_RANGE_RE = re.compile(r"(\d+(?:\.\d+)?)\s*-\s*(\d+(?:\.\d+)?)")
_SINGLE_NUM_RE = re.compile(r"\d+(?:\.\d+)?")
_ESTIMATE_KEY_RE = re.compile(r"^estimate:\s*$")
_ESTIMATE_INDENT_RE = re.compile(r"^\s+(\w+):\s*(.+?)\s*$")
_TOP_KEY_RE = re.compile(r"^[A-Za-z_]")


def _detect_07_disabled() -> bool:
    """Return True if `CEO_REALITY_LEDGER_DETECTOR_07=0` (bypass)."""
    return (os.environ.get("CEO_REALITY_LEDGER_DETECTOR_07") or "").strip() == "0"


def _parse_estimate_block(text: str) -> Dict[str, str]:
    """Parse the nested `estimate:` block from frontmatter text.

    Returns flat dict of estimate sub-fields (compute_hours,
    owner_physical_min, calendar_buffer_days, etc.) → raw string. The
    base parser at `_lib/plan_frontmatter.py` only handles top-level keys
    + simple lists; this helper reads the indented YAML-ish sub-block.
    """
    out: Dict[str, str] = {}
    lines = text.splitlines()
    in_estimate = False
    for line in lines:
        if not in_estimate:
            if _ESTIMATE_KEY_RE.match(line):
                in_estimate = True
            continue
        # Sub-field continues so long as line is indented (starts with space).
        if line and line[0] not in (" ", "\t"):
            break
        m = _ESTIMATE_INDENT_RE.match(line)
        if not m:
            continue
        # Strip inline `# comment` on the value
        raw_val = m.group(2)
        comment_at = raw_val.find("#")
        if comment_at > 0:
            raw_val = raw_val[:comment_at].rstrip()
        out[m.group(1)] = raw_val
    return out


def _coerce_hours_to_pair(raw: str) -> Optional[Tuple[float, float]]:
    """Parse '6-12' → (6.0, 12.0), '8' → (8.0, 8.0). None on failure."""
    if not raw:
        return None
    rng = _HOURS_RANGE_RE.search(raw)
    if rng:
        try:
            lo = float(rng.group(1))
            hi = float(rng.group(2))
            if hi < lo:
                lo, hi = hi, lo
            return (lo, hi)
        except ValueError:
            return None
    single = _SINGLE_NUM_RE.search(raw)
    if single:
        try:
            v = float(single.group(0))
            return (v, v)
        except ValueError:
            return None
    return None


def _extract_top_level_field(text: str, key: str) -> Optional[str]:
    """Extract a top-level frontmatter field (`<key>: <val>`) raw value.

    Used for `created`, `created_at`, `status`, `id`, `actual_owner_physical_min`
    where the base parser also works but we want a single API.
    """
    pat = re.compile(rf"^{re.escape(key)}:\s*(.+?)\s*$", re.MULTILINE)
    m = pat.search(text)
    if not m:
        return None
    val = m.group(1)
    # Strip inline comments
    comment_at = val.find("#")
    if comment_at > 0:
        val = val[:comment_at].rstrip()
    # Strip surrounding quotes
    if (val.startswith('"') and val.endswith('"')) or (
        val.startswith("'") and val.endswith("'")
    ):
        val = val[1:-1]
    return val


def _git_log_paths(repo_root: Path) -> Dict[str, List[Tuple[str, str, bool]]]:
    """Single batched `git log` run; index commits per file.

    Returns dict: rel_path -> list of (commit_sha, iso_committer_date, was_gpg_signed).

    Codex W1+W2 fix-pack #5: switched from author-date (%aI) to committer-date
    (%cI). Author-date reflects original authorship and is preserved verbatim
    across rebases/cherry-picks; that distorts the closeout timeline. Committer
    date reflects when the commit landed in the current branch's history,
    which is what we want for plan span computation.

    GPG-signed inferred via `git log --show-signature` would slow us down
    significantly; instead we emit a separate sub-call to enumerate signed
    commits via `git log --format=%H %G?` (one extra subprocess; total = 2).

    Returns empty dict on any git error (fail-open per Sec NTH #5).
    """
    result: Dict[str, List[Tuple[str, str, bool]]] = {}
    try:
        import subprocess
        # 1) Path-aware log (commit, ISO committer-date, then file lines).
        # Codex Fix #5: use --follow to track plan-file renames and %cI
        # (committer date) so rebased/cherry-picked commits report their
        # landing time, not their original authorship time.
        proc = subprocess.run(
            [
                "git", "-C", str(repo_root), "log",
                "--pretty=format:COMMIT %H %cI",
                "--name-only",
                "--no-merges",
            ],
            capture_output=True,
            text=True,
            timeout=30,
        )
        if proc.returncode != 0:
            return {}
        gpg_signed: Dict[str, bool] = {}
        # 2) Signature mode: %G? returns G (good), B (bad), U (unknown), N (none),
        # E/X/Y/R for various other states. We treat G/U as 'signed'.
        try:
            sig_proc = subprocess.run(
                ["git", "-C", str(repo_root), "log", "--format=%H %G?"],
                capture_output=True,
                text=True,
                timeout=30,
            )
            if sig_proc.returncode == 0:
                for sig_line in sig_proc.stdout.splitlines():
                    parts = sig_line.strip().split()
                    if len(parts) == 2:
                        gpg_signed[parts[0]] = parts[1] in ("G", "U")
        except Exception:
            gpg_signed = {}

        cur_sha: Optional[str] = None
        cur_iso: Optional[str] = None
        for line in proc.stdout.splitlines():
            if line.startswith("COMMIT "):
                rest = line[len("COMMIT "):].split(" ", 1)
                cur_sha = rest[0]
                cur_iso = rest[1] if len(rest) > 1 else ""
            elif line and cur_sha is not None and cur_iso is not None:
                rel = line.strip()
                if rel:
                    result.setdefault(rel, []).append(
                        (cur_sha, cur_iso, gpg_signed.get(cur_sha, False))
                    )
        return result
    except Exception:  # pragma: no cover - fail-open
        return {}


def _git_status_done_transition(
    repo_root: Path,
    plan_rel_path: str,
) -> Optional[Tuple[str, str]]:
    """Find the commit that flipped a plan's frontmatter from non-done to done.

    Codex W1+W2 fix-pack #5 (Fix #5): replaces the prior naive last-commit
    span computation. Returns ``(commit_sha, committer_iso_date)`` for the
    commit whose patch added the line ``+status: done`` to ``plan_rel_path``,
    OR ``None`` if no such commit exists (plan still draft, or transition
    happened in a merge commit which we skip per ``--no-merges`` discipline).

    Edge cases:
      - Plan created and closed in the same commit (PLAN-072 pattern):
        the diff still contains ``+status: done`` so we report that single
        commit; caller separately detects span=0 and skips emitting.
      - Multiple flips (status: done -> reverted -> status: done again):
        we return the LAST such transition; the most recent is the true
        closeout.
      - Renames/file-mv: ``--follow`` tracks the file across renames.
      - Merge commits: ``--no-merges`` skips them; if the only flip lives
        inside a merge, we return None (test fixture should mock this).

    Uses ``git log -G`` regex search + ``git show`` per matching commit
    to confirm the ``+status: done`` is in fact an addition (not a removal).
    """
    try:
        import subprocess
        # Step 1: enumerate commits where the plan file was modified AND
        # the patch contains the literal "status: done" string. ``git
        # log -G`` runs the regex against the line-pair text representing
        # each diff hunk; line anchors (``^``) don't work the way grep
        # expects there, so we keep the regex permissive and let the
        # per-commit ``git show`` parser in step 2 confirm the addition.
        proc = subprocess.run(
            [
                "git", "-C", str(repo_root), "log",
                "--follow",
                "--no-merges",
                "--pretty=format:%H %cI",
                "-G", r"status: *done",
                "--",
                plan_rel_path,
            ],
            capture_output=True,
            text=True,
            timeout=15,
        )
        if proc.returncode != 0 or not proc.stdout.strip():
            return None

        # Walk commits in CHRONOLOGICAL order (oldest -> newest). git log
        # outputs newest-first; we reverse so we can detect the earliest
        # transition and then the most recent re-flip.
        candidates: List[Tuple[str, str]] = []
        for line in proc.stdout.splitlines():
            line = line.strip()
            if not line:
                continue
            parts = line.split(" ", 1)
            if len(parts) != 2:
                continue
            candidates.append((parts[0], parts[1]))
        candidates.reverse()

        # Step 2: For each candidate, run `git show` and check whether the
        # patch ADDS `status: done`. We track the LAST such addition as
        # the true closeout transition (handles re-open / re-close cycles).
        last_transition: Optional[Tuple[str, str]] = None
        for sha, iso in candidates:
            try:
                show = subprocess.run(
                    [
                        "git", "-C", str(repo_root), "show",
                        "--no-color",
                        "--pretty=format:",
                        sha, "--", plan_rel_path,
                    ],
                    capture_output=True,
                    text=True,
                    timeout=10,
                )
            except Exception:
                continue
            if show.returncode != 0:
                continue
            # Match a leading '+' (addition) followed by 'status: done'.
            # Skip '++' headers (file headers in unified diff).
            for diff_line in show.stdout.splitlines():
                if diff_line.startswith("++"):
                    continue
                if diff_line.startswith("+") and re.match(
                    r"^\+\s*status:\s*done\b", diff_line
                ):
                    last_transition = (sha, iso)
                    break
        return last_transition
    except Exception:  # pragma: no cover - fail-open
        return None


def _drift_severity(factor_compute: float, factor_owner: float) -> str:
    """Map drift factor to severity band — bidirectional (Codex Fix #3).

    Bands measured against a symmetric ratio ``r = max(f, 1/f)`` where
    f > 0 is the drift factor. Both overruns (f > 1.2) and underruns
    (f < 0.83) are detected.

      r ≤ 1.2 → factor in [0.83, 1.2] → no drift (caller skips finding)
      1.2 < r ≤ 1.5 → low
      1.5 < r ≤ 2.0 → medium
      r > 2.0 → high

    A factor of 0.0 (estimate present but no actual measured) is treated
    as r = ∞ → high (detector caller already short-circuits when actual
    is missing, but guard here for safety).
    """
    def _ratio(f: float) -> float:
        try:
            af = abs(float(f))
        except (TypeError, ValueError):
            return 1.0
        if af == 0.0:
            return float("inf")
        if af >= 1.0:
            return af
        return 1.0 / af

    rmax = max(_ratio(factor_compute), _ratio(factor_owner))
    if rmax > 2.0:
        return "high"
    if rmax > 1.5:
        return "medium"
    if rmax > 1.2:
        return "low"
    return "low"


def _classify_bias(actual_compute: float, est_compute_lo: float,
                   est_compute_hi: float) -> str:
    """Return 'underestimate' if actual > hi, 'overestimate' if actual < lo, '' otherwise."""
    if actual_compute > est_compute_hi:
        return "underestimate"
    if actual_compute < est_compute_lo:
        return "overestimate"
    return ""


def _read_calibration_csv(path: Path) -> List[str]:
    """Read existing CSV rows (idempotency check). Empty list if missing."""
    if not path.is_file():
        return []
    try:
        return path.read_text(encoding="utf-8").splitlines()
    except OSError:
        return []


def _calibration_csv_dedup_key(row: str) -> str:
    """Build a dedup key for a calibration CSV row that EXCLUDES run_iso8601.

    Codex W1+W2 fix-pack #4: the prior dedup logic (`row in existing`) used
    the entire row including the per-run timestamp ``run_iso8601`` (column
    index 1). Repeat runs always produced a fresh ``run_iso8601`` so dedup
    never matched and the CSV grew unboundedly with N rows per plan per run.

    The dedup key uses the same row content with column-1 (run_iso8601)
    blanked. Same plan + same drift factors + same severity → considered
    "same finding" regardless of when it was measured. The on-disk row
    still preserves run_iso8601 (for forensics — answers "when did we
    first see this drift?"); dedup just doesn't compare on it.

    Column order (header):
      0: plan_id
      1: run_iso8601                  <-- EXCLUDED from key
      2: est_compute_lo
      3: est_compute_hi
      4: actual_compute_h
      5: est_owner_min
      6: actual_owner_min
      7: drift_factor_compute
      8: drift_factor_owner
      9: severity
      10: bias
    """
    cols = row.split(",")
    if len(cols) > 1:
        cols[1] = ""  # blank run_iso8601 from dedup key
    return ",".join(cols)


def _append_calibration_csv(path: Path, row: str) -> None:
    """Append row to CSV idempotently — dedup excludes run_iso8601 (Codex Fix #4)."""
    try:
        existing = _read_calibration_csv(path)
        # Build dedup-key set from existing rows, skipping the header
        # (header row's first column literally is "plan_id" so it can
        # never collide with a real plan id, but we explicitly skip
        # the first line for clarity).
        existing_keys = set()
        for i, line in enumerate(existing):
            if i == 0 and line.startswith("plan_id,"):
                continue  # skip header
            existing_keys.add(_calibration_csv_dedup_key(line))
        if _calibration_csv_dedup_key(row) in existing_keys:
            return  # idempotent: same plan + same drift signature already recorded
        path.parent.mkdir(parents=True, exist_ok=True)
        with path.open("a", encoding="utf-8") as f:
            if not existing:
                # Header row
                f.write(
                    "plan_id,run_iso8601,est_compute_lo,est_compute_hi,"
                    "actual_compute_h,est_owner_min,actual_owner_min,"
                    "drift_factor_compute,drift_factor_owner,severity,bias\n"
                )
            f.write(row + "\n")
    except OSError:
        pass  # fail-open


def _parse_created_iso(raw: str) -> Optional[datetime]:
    """Parse a `created:` frontmatter value into a UTC datetime.

    Accepts ``YYYY-MM-DD`` (interpreted as 00:00:00 UTC) or full ISO8601
    with offset/Z. Returns None on parse failure.
    """
    if not raw:
        return None
    raw = raw.strip()
    # Date-only form: 2026-04-10
    if re.match(r"^\d{4}-\d{2}-\d{2}$", raw):
        try:
            d = datetime.strptime(raw, "%Y-%m-%d")
            return d.replace(tzinfo=timezone.utc)
        except ValueError:
            return None
    # Full ISO with optional Z
    try:
        return datetime.fromisoformat(raw.replace("Z", "+00:00"))
    except ValueError:
        return None


def detect_estimate_drift(
    *,
    repo_root: Path,
    plan_files: Optional[List[Path]] = None,
    calibration_csv: Optional[Path] = None,
    git_log_index: Optional[Dict[str, List[Tuple[str, str, bool]]]] = None,
    status_done_transitions: Optional[Dict[str, Tuple[str, str]]] = None,
    audit_emit_module: Optional[Any] = None,
    session_id: str = "",
    project: str = "",
    emit_audit: bool = False,
) -> List[Dict[str, Any]]:
    """Detector #7 — estimate-drift on plan close-outs.

    PLAN-078 Wave 2. Pure function (no global state mutation outside of
    caller-supplied calibration_csv path). Test-friendly:

      - ``plan_files`` override targets a specific subset
      - ``calibration_csv`` override redirects CSV writes (test isolation)
      - ``git_log_index`` override skips real git calls (mock injection;
        used to compute GPG-signed commit count)
      - ``status_done_transitions`` mocks the per-plan ``status: done``
        transition commit (rel_path -> (sha, committer_iso)). When None
        AND ``git_log_index`` is provided, the LAST commit in the index
        is used as the transition (back-compat with existing test fixtures).
        When None AND no index, real ``_git_status_done_transition`` runs.
      - ``audit_emit_module`` allows tests to inject a stub for the typed
        Wave 2 emitters (Codex Fix #1).
      - ``session_id`` / ``project`` flow into emitted events.
      - ``emit_audit`` opt-in flag (CLI ``--emit-audit``) gates emission.

    Returns list of finding dicts. Caller (run_detectors) handles
    redaction + render. Codex W1+W2 fix-pack:

      Fix #1: emits via ``emit_estimate_drift_detected`` /
              ``emit_estimate_drift_systematic_bias`` (typed wrappers)
              instead of generic ``_try_emit_finding`` for detector #7.
      Fix #3: bidirectional — flags both overruns (factor > 1.2) and
              underruns (factor < 0.83 ≈ 1/1.2). Severity uses symmetric
              ratio max(f, 1/f). bias_direction reflects either case.
      Fix #5: span computed as ``status: done`` transition committer-date
              minus plan ``created`` field (NOT first/last edit author-date
              from arbitrary file history). Skips plans whose transition
              cannot be located OR whose span ≤ 0h.
    """
    findings: List[Dict[str, Any]] = []
    if _detect_07_disabled():
        return findings  # bypass

    plans_dir = repo_root / ".claude" / "plans"
    if not plans_dir.exists():
        return findings

    if plan_files is None:
        plan_files = [
            p for p in sorted(plans_dir.glob("PLAN-*.md"))
            if p.is_file() and not _is_excluded(p, repo_root=repo_root)
        ]

    # git_log_index is still used for GPG-signed-commit count regardless
    # of the new transition-commit logic.
    if git_log_index is None and status_done_transitions is None:
        git_log_index = _git_log_paths(repo_root)
    if git_log_index is None:
        git_log_index = {}

    csv_path = calibration_csv or (
        repo_root / ".claude" / "scripts" / "local" / "calibration-history.csv"
    )

    drift_findings_for_summary: List[Dict[str, Any]] = []
    run_iso = _now_iso8601()

    for f in plan_files:
        try:
            text = f.read_text(encoding="utf-8", errors="replace")
        except OSError:
            continue
        rel = _to_repo_rel(f)
        plan_id_match = _PLAN_FILE_RE.match(f.name)
        if not plan_id_match:
            continue
        plan_id = f"PLAN-{plan_id_match.group(1)}"

        status = _extract_top_level_field(text, "status") or ""
        if status.strip().lower() != "done":
            continue  # detector only fires on close-outs

        est_block = _parse_estimate_block(text)
        compute_raw = est_block.get("compute_hours", "")
        owner_raw = est_block.get("owner_physical_min", "")
        if not compute_raw and not owner_raw:
            continue  # plan has no estimate to drift against

        compute_pair = _coerce_hours_to_pair(compute_raw)
        owner_pair = _coerce_hours_to_pair(owner_raw)
        if compute_pair is None and owner_pair is None:
            continue

        # `created` is the schema-correct field; fall back to `created_at`
        # for plans authored before PLAN-076/077 cluster (Codex CDX-UNIQUE-06).
        created = _extract_top_level_field(text, "created") or \
            _extract_top_level_field(text, "created_at") or ""

        # Resolve commits (for GPG count) — try multiple path forms.
        plan_rel = rel
        commits = git_log_index.get(plan_rel, [])
        if not commits:
            for alt in (
                rel,
                rel.replace(os.sep, "/"),
                str(f.relative_to(repo_root)).replace(os.sep, "/"),
            ):
                commits = git_log_index.get(alt, []) or commits

        # Codex Fix #5: locate the status:done transition commit.
        transition: Optional[Tuple[str, str]] = None
        if status_done_transitions is not None:
            # Test-injected dict — try multiple path forms (matches the
            # git_log_index multi-key fallback above).
            try:
                rel_to_repo = str(f.relative_to(repo_root)).replace(os.sep, "/")
            except ValueError:
                rel_to_repo = ""
            for key in (
                plan_rel,
                rel.replace(os.sep, "/"),
                rel_to_repo,
            ):
                if key and key in status_done_transitions:
                    transition = status_done_transitions[key]
                    break
        elif commits:
            # Back-compat: when caller injected git_log_index without
            # status_done_transitions (existing test fixtures), use the
            # LAST commit (most-recent) as the transition. This matches
            # the prior end-of-history semantics for those fixtures.
            commits_sorted_for_tx = sorted(commits, key=lambda x: x[1])
            last_sha, last_iso, _ = commits_sorted_for_tx[-1]
            transition = (last_sha, last_iso)
        else:
            # Real run: use the per-plan git helper (committer-date of the
            # commit whose patch added `+status: done`).
            transition = _git_status_done_transition(repo_root, plan_rel)

        if transition is None:
            continue  # no transition evidence; skip silently

        closeout_iso = transition[1]
        try:
            closeout_dt = datetime.fromisoformat(closeout_iso.replace("Z", "+00:00"))
        except ValueError:
            continue
        # Start: plan `created` field (date-midnight UTC).
        start_dt = _parse_created_iso(created)
        if start_dt is None:
            # Fallback: if `created` is missing, use earliest commit's date.
            if commits:
                first_iso = sorted(commits, key=lambda x: x[1])[0][1]
                try:
                    start_dt = datetime.fromisoformat(first_iso.replace("Z", "+00:00"))
                except ValueError:
                    continue
            else:
                continue

        span_hours = (closeout_dt - start_dt).total_seconds() / 3600.0
        if span_hours <= 0:
            # Plan created and closed in same commit (PLAN-072 single-commit
            # closeout pattern) OR clock skew. Skip and breadcrumb.
            sys.stderr.write(
                f"[reality-ledger] {plan_id}: span ≤ 0 "
                f"(created={created} closeout={closeout_iso}); skipped\n"
            )
            continue

        # GPG-signed commit count proxies for owner-physical (signing = Owner ceremony)
        gpg_count = sum(1 for c in (commits or []) if len(c) >= 3 and c[2])

        # Optional manual override
        manual_override_raw = _extract_top_level_field(
            text, "actual_owner_physical_min"
        )
        manual_override: Optional[int] = None
        if manual_override_raw:
            try:
                manual_override = int(float(manual_override_raw))
            except ValueError:
                manual_override = None

        # Owner physical estimate: 5min/GPG ceremony floor + manual override.
        actual_owner_min: float
        if manual_override is not None:
            actual_owner_min = float(max(0, min(10000, manual_override)))
        else:
            actual_owner_min = float(gpg_count * 5)

        # Drift factors. Use mid of estimate range as denominator.
        compute_drift = 1.0
        if compute_pair is not None and span_hours > 0:
            est_mid = (compute_pair[0] + compute_pair[1]) / 2.0
            if est_mid > 0:
                compute_drift = span_hours / est_mid

        owner_drift = 1.0
        if owner_pair is not None and actual_owner_min > 0:
            # Only compute the owner-axis ratio when we have a non-zero
            # actual measurement. ``actual_owner_min == 0`` happens when
            # no GPG-signed commits exist for the plan AND no manual
            # override was set; that's "no signal", not "underrun by
            # 100%". Reporting it as drift would flag every plan that
            # closed without an Owner ceremony — too noisy for advisory.
            est_owner_mid = (owner_pair[0] + owner_pair[1]) / 2.0
            if est_owner_mid > 0:
                owner_drift = actual_owner_min / est_owner_mid

        severity = _drift_severity(compute_drift, owner_drift)
        bias = _classify_bias(
            span_hours,
            compute_pair[0] if compute_pair else 0.0,
            compute_pair[1] if compute_pair else 0.0,
        )

        # Codex Fix #3: bidirectional drift detection — flag when
        # max(factor, 1/factor) >= 1.2 in EITHER axis. Equivalent to:
        # factor > 1.2 (overrun) OR factor < 1/1.2 ≈ 0.833 (underrun).
        def _is_drifted(factor: float) -> bool:
            try:
                af = abs(float(factor))
            except (TypeError, ValueError):
                return False
            if af == 0.0:
                return True  # actual=0 with non-zero estimate → underrun
            ratio = af if af >= 1.0 else 1.0 / af
            return ratio >= 1.2

        if not (_is_drifted(compute_drift) or _is_drifted(owner_drift)):
            continue

        finding = _build_finding(
            detector="estimate_drift",
            severity=severity,
            confidence=0.85,
            claim_source_path=f"{rel}:1",
            expected_evidence=(
                f"compute_hours={compute_raw} owner_physical_min={owner_raw}"
            ),
            actual_evidence=(
                f"span_hours={span_hours:.1f} owner_min~={actual_owner_min:.0f} "
                f"gpg_signed_commits={gpg_count}"
            ),
            advisory_action=(
                "review estimate calibration; populate "
                "actual_owner_physical_min in plan frontmatter for accuracy"
            ),
            extra={
                "plan_id": plan_id,
                "compute_drift_factor": round(compute_drift, 3),
                "owner_drift_factor": round(owner_drift, 3),
                "transition_commit_sha": transition[0],
                "closeout_commit_iso": closeout_iso,
                "gpg_signed_commits": gpg_count,
                "actual_owner_min_estimated": round(actual_owner_min, 1),
                "bias_direction": bias,
                "created_field": created,
            },
        )
        findings.append(finding)
        drift_findings_for_summary.append(finding)

        # Codex Fix #1: emit via typed estimate_drift_detected (NOT
        # generic reality_ledger_finding). Caller's --emit-audit gate
        # is honored. Each emit is best-effort + fail-open.
        if emit_audit:
            _emit_estimate_drift_detected_typed(
                audit_emit_module=audit_emit_module,
                session_id=session_id,
                project=project,
                plan_id=plan_id,
                drift_factor_compute=compute_drift,
                drift_factor_owner=owner_drift,
                severity=severity,
                plan_count_in_run=len(plan_files),
                systematic_bias_direction=bias,
            )

        # CSV append (idempotent — Codex Fix #4 dedup excludes run_iso8601)
        csv_row = ",".join([
            plan_id, run_iso,
            f"{compute_pair[0]:.1f}" if compute_pair else "",
            f"{compute_pair[1]:.1f}" if compute_pair else "",
            f"{span_hours:.2f}",
            f"{owner_pair[0]:.0f}" if owner_pair else "",
            f"{actual_owner_min:.0f}",
            f"{compute_drift:.3f}",
            f"{owner_drift:.3f}",
            severity,
            bias,
        ])
        _append_calibration_csv(csv_path, csv_row)

    # Codex Fix #3: systematic bias tracks BOTH directions independently.
    # N≥5 same-direction medium+ findings → emit recommendation.
    if len(drift_findings_for_summary) >= 5:
        bias_counter: Dict[str, int] = {"underestimate": 0, "overestimate": 0}
        compute_factors_by_dir: Dict[str, List[float]] = {
            "underestimate": [], "overestimate": []
        }
        owner_factors_by_dir: Dict[str, List[float]] = {
            "underestimate": [], "overestimate": []
        }
        for fnd in drift_findings_for_summary:
            ex = fnd.get("_extra", {})
            sev = fnd.get("severity", "low")
            if sev not in ("medium", "high"):
                continue
            bd = ex.get("bias_direction", "")
            if bd in ("underestimate", "overestimate"):
                bias_counter[bd] += 1
                compute_factors_by_dir[bd].append(
                    ex.get("compute_drift_factor", 1.0)
                )
                owner_factors_by_dir[bd].append(
                    ex.get("owner_drift_factor", 1.0)
                )
        # Pick first direction crossing 5 (deterministic by dict insertion order)
        for direction, count in bias_counter.items():
            if count >= 5:
                cf = compute_factors_by_dir[direction]
                of = owner_factors_by_dir[direction]
                avg_compute = sum(cf) / max(1, len(cf))
                avg_owner = sum(of) / max(1, len(of))
                # Append a meta-finding (no claim_source_path; recommendation event)
                findings.append(_build_finding(
                    detector="estimate_drift",
                    severity="high",
                    confidence=0.95,
                    claim_source_path="<recommendation-event>",
                    expected_evidence=f"systematic_{direction}_threshold>=5",
                    actual_evidence=(
                        f"plans_affected={count} avg_compute={avg_compute:.2f}× "
                        f"avg_owner={avg_owner:.2f}×"
                    ),
                    advisory_action=(
                        f"systematic {direction}: re-calibrate estimate baselines"
                    ),
                    extra={
                        "systematic_bias_direction": direction,
                        "plans_affected_count": count,
                        "avg_drift_factor_compute": round(avg_compute, 3),
                        "avg_drift_factor_owner": round(avg_owner, 3),
                        "is_recommendation_event": True,
                    },
                ))
                # Codex Fix #1: emit typed systematic_bias event.
                if emit_audit:
                    _emit_estimate_drift_systematic_bias_typed(
                        audit_emit_module=audit_emit_module,
                        session_id=session_id,
                        project=project,
                        bias_direction=direction,
                        plans_affected_count=count,
                        avg_drift_factor_compute=avg_compute,
                        avg_drift_factor_owner=avg_owner,
                    )
                break

    return findings


# ---------------------------------------------------------------------------
# Codex W1+W2 fix-pack #1 — typed Wave 2 audit emit wrappers
# ---------------------------------------------------------------------------

def _to_basis_points(value: float, *, lo: int = 0, hi: int = 1_000_000) -> int:
    """Convert a float multiplier to integer basis-points (×1000), clamped.

    Mirrors audit_emit._to_basis_points; duplicated here so reality-ledger
    can run with a not-yet-Wave-2-extended audit_emit at HEAD (the typed
    helpers in audit_emit are guarded by hasattr — fail-open if absent).
    """
    try:
        f = float(value)
    except (TypeError, ValueError):
        return lo
    if f != f or f in (float("inf"), float("-inf")):
        return lo
    bp = int(round(f * 1000.0))
    if bp < lo:
        return lo
    if bp > hi:
        return hi
    return bp


def _emit_estimate_drift_detected_typed(
    *,
    audit_emit_module: Optional[Any],
    session_id: str,
    project: str,
    plan_id: str,
    drift_factor_compute: float,
    drift_factor_owner: float,
    severity: str,
    plan_count_in_run: int,
    systematic_bias_direction: str,
) -> bool:
    """Best-effort emit of estimate_drift_detected via typed wrapper.

    Codex W1+W2 fix-pack #1: detector #7 emits via the dedicated typed
    wrapper, NOT via the generic ``reality_ledger_finding`` dispatch.
    Fail-open per Sec NTH #5: any exception is swallowed.
    """
    try:
        if audit_emit_module is None:
            try:
                from _lib import audit_emit as audit_emit_module  # type: ignore
            except Exception:
                return False
        emit_fn = getattr(audit_emit_module, "emit_estimate_drift_detected", None)
        if emit_fn is None:
            return False
        emit_fn(
            session_id=session_id,
            plan_id=plan_id,
            drift_factor_compute_basis_points=_to_basis_points(
                drift_factor_compute
            ),
            drift_factor_owner_basis_points=_to_basis_points(
                drift_factor_owner
            ),
            severity=severity,
            plan_count_in_run=plan_count_in_run,
            systematic_bias_direction=systematic_bias_direction,
            project=project,
        )
        return True
    except Exception:  # pragma: no cover - fail-open invariant
        return False


def _emit_estimate_drift_systematic_bias_typed(
    *,
    audit_emit_module: Optional[Any],
    session_id: str,
    project: str,
    bias_direction: str,
    plans_affected_count: int,
    avg_drift_factor_compute: float,
    avg_drift_factor_owner: float,
) -> bool:
    """Best-effort emit of estimate_drift_systematic_bias via typed wrapper."""
    try:
        if audit_emit_module is None:
            try:
                from _lib import audit_emit as audit_emit_module  # type: ignore
            except Exception:
                return False
        emit_fn = getattr(
            audit_emit_module, "emit_estimate_drift_systematic_bias", None
        )
        if emit_fn is None:
            return False
        emit_fn(
            session_id=session_id,
            bias_direction=bias_direction,
            plans_affected_count=plans_affected_count,
            avg_drift_factor_compute_basis_points=_to_basis_points(
                avg_drift_factor_compute
            ),
            avg_drift_factor_owner_basis_points=_to_basis_points(
                avg_drift_factor_owner
            ),
            project=project,
        )
        return True
    except Exception:  # pragma: no cover - fail-open invariant
        return False


# ---------------------------------------------------------------------------
# Finding shape + redaction + rendering
# ---------------------------------------------------------------------------

def _to_repo_rel(p: Path) -> str:
    try:
        return str(p.resolve().relative_to(_REPO_ROOT.resolve())).replace(os.sep, "/")
    except (ValueError, OSError):
        return str(p)


def _sha256_of(s: str) -> str:
    return hashlib.sha256(s.encode("utf-8", errors="replace")).hexdigest()


def _now_iso8601() -> str:
    return datetime.now(timezone.utc).strftime("%Y-%m-%dT%H:%M:%SZ")


def _redact(text: str) -> str:
    """Pass through `_lib.redact.redact_secrets` without truncation.

    Use max_chars=0 to disable preview truncation; rely on caller to
    bound the string length when needed.
    """
    return redact_secrets(text or "", max_chars=0)


def _build_finding(
    *,
    detector: str,
    severity: str,
    confidence: float,
    claim_source_path: str,
    expected_evidence: str,
    actual_evidence: str,
    advisory_action: str,
    extra: Optional[Dict[str, Any]] = None,
) -> Dict[str, Any]:
    """Construct a finding dict with both render forms baked in.

    `claim_source_path` is included for markdown only; JSON/JSONL
    renderers strip the field per Sec MF-3 contract.
    """
    actual_redacted = _redact(actual_evidence)
    sha = _sha256_of(claim_source_path or "")
    # confidence_bps: integer basis-points (confidence × 1000, clamped 0..1000).
    # canonical_json forbids floats in HMAC-covered fields; the old "confidence"
    # float (0.0-1.0) caused CanonicalJsonError on every reality_ledger_finding
    # emit. Readers recover float via confidence_bps / 1000.
    confidence_bps = max(0, min(1000, int(round(float(confidence) * 1000))))
    return {
        "schema_version": SCHEMA_VERSION,
        "finding_id": str(uuid.uuid4()),
        "detector": detector,
        "severity": severity,
        "confidence_bps": confidence_bps,
        "claim_source_path": claim_source_path,
        "claim_source_sha256": sha,
        "expected_evidence": expected_evidence,
        "actual_evidence_redacted": actual_redacted,
        "first_observed_at": _now_iso8601(),
        "advisory_action": advisory_action,
        "_extra": extra or {},
    }


def _strip_markdown_only(finding: Dict[str, Any]) -> Dict[str, Any]:
    """Return a copy of finding without markdown-only fields (claim_source_path)."""
    return {k: v for k, v in finding.items() if k not in _MARKDOWN_ONLY_FIELDS}


def render_finding_markdown(finding: Dict[str, Any]) -> str:
    lines: List[str] = []
    # confidence_bps (int 0..1000) — display as float for human readability.
    conf_display = finding.get("confidence_bps", 0) / 1000
    lines.append(f"### {finding['detector']}  ·  severity={finding['severity']}  ·  conf={conf_display:.3f}")
    lines.append("")
    lines.append(f"- claim_source_path: `{finding['claim_source_path']}`")
    lines.append(f"- claim_source_sha256: `{finding['claim_source_sha256']}`")
    lines.append(f"- expected_evidence: `{finding['expected_evidence']}`")
    lines.append(f"- actual_evidence_redacted: `{finding['actual_evidence_redacted']}`")
    lines.append(f"- first_observed_at: `{finding['first_observed_at']}`")
    lines.append(f"- advisory_action: {finding['advisory_action']}")
    lines.append(f"- finding_id: `{finding['finding_id']}`")
    return "\n".join(lines)


def render_findings_markdown(findings: List[Dict[str, Any]]) -> str:
    if not findings:
        return "# reality-ledger — 0 findings\n\nNo divergence detected. (Advisory; never blocks.)"
    counts: Dict[str, int] = {}
    for f in findings:
        counts[f["detector"]] = counts.get(f["detector"], 0) + 1
    lines = [f"# reality-ledger — {len(findings)} finding(s)", ""]
    lines.append("## Summary by detector")
    for det in sorted(counts):
        lines.append(f"- `{det}`: {counts[det]}")
    lines.append("")
    lines.append("## Findings")
    for f in findings:
        lines.append("")
        lines.append(render_finding_markdown(f))
    return "\n".join(lines) + "\n"


def render_findings_json(findings: List[Dict[str, Any]]) -> str:
    """JSON array with markdown-only fields excluded."""
    safe = [_strip_markdown_only(f) for f in findings]
    # also drop _extra (caller-private debug payload) from JSON emission
    for s in safe:
        s.pop("_extra", None)
    return json.dumps(safe, indent=2, sort_keys=True, ensure_ascii=False)


def render_findings_jsonl(findings: List[Dict[str, Any]]) -> str:
    """One JSON object per line, markdown-only fields excluded."""
    out: List[str] = []
    for f in findings:
        s = _strip_markdown_only(f)
        s.pop("_extra", None)
        out.append(json.dumps(s, sort_keys=True, ensure_ascii=False))
    return "\n".join(out) + ("\n" if out else "")


# ---------------------------------------------------------------------------
# Audit emission (hasattr-guarded; advisory-only)
# ---------------------------------------------------------------------------

def _scrub_reality_ledger_event(
    event: Dict[str, Any],
    *,
    allowlist: Optional[FrozenSet[str]] = None,
) -> Tuple[Dict[str, Any], List[str]]:
    """Return (kept_event, dropped_keys). Defense-in-depth on allowlist drift."""
    aw = allowlist or _REALITY_LEDGER_FINDING_ALLOWLIST
    kept: Dict[str, Any] = {}
    dropped: List[str] = []
    for k, v in event.items():
        if k in aw:
            kept[k] = v
        else:
            dropped.append(k)
    return kept, dropped


def _try_emit_finding(finding: Dict[str, Any], *, finding_count_in_run: int) -> bool:
    """Best-effort audit emit; never raises. Returns True on success.

    The action `reality_ledger_finding` is registered in Phase 5 KERNEL
    ceremony. Pre-Phase-5 this call no-ops (action not in _KNOWN_ACTIONS).
    """
    try:
        from _lib import audit_emit
    except Exception:
        return False
    payload = {
        "action": "reality_ledger_finding",
        "ts": finding.get("first_observed_at"),
        "detector": finding.get("detector"),
        "severity": finding.get("severity"),
        # confidence_bps is already an int (set in _make_finding); pass through.
        "confidence_bps": finding.get("confidence_bps", 0),
        "claim_source_sha256": finding.get("claim_source_sha256"),
        "finding_count_in_run": finding_count_in_run,
    }
    scrubbed, dropped = _scrub_reality_ledger_event(payload)
    # Prefer typed emitter when registered; fall back to emit_generic.
    try:
        if hasattr(audit_emit, "emit_reality_ledger_finding"):
            getattr(audit_emit, "emit_reality_ledger_finding")(**scrubbed)
            return True
        if hasattr(audit_emit, "emit_generic"):
            audit_emit.emit_generic(**scrubbed)
            # emit_generic silently no-ops on unknown action; treat as best-effort
            return True
    except Exception:
        return False
    return False


# ---------------------------------------------------------------------------
# Detector dispatch
# ---------------------------------------------------------------------------

def _run_with_timeout(
    fn,
    *,
    timeout_ms: int,
    detector_name: str,
) -> Tuple[List[Dict[str, Any]], Optional[str]]:
    """Run a detector with ITIMER guard. Returns (findings, error_str)."""
    budget_s = max(0.001, timeout_ms / 1000.0)
    prev = _install_itimer_guard(budget_s)
    try:
        findings = fn()
        return findings, None
    except ScanBudgetExceeded:
        return [], f"detector {detector_name} timed out after {timeout_ms}ms"
    except Exception as exc:  # pragma: no cover - safety net
        return [], f"detector {detector_name} raised {exc.__class__.__name__}: {exc}"
    finally:
        _clear_itimer_guard(prev)


def run_detectors(
    *,
    repo_root: Path,
    detector_names: Optional[List[str]] = None,
    timeout_ms: int = DEFAULT_DETECTOR_TIMEOUT_MS,
    audit_log_path: Optional[Path] = None,
    emit_audit: bool = False,
    audit_emit_module: Optional[Any] = None,
    session_id: str = "",
    project: str = "",
) -> Tuple[List[Dict[str, Any]], List[str]]:
    """Run requested detectors; returns (findings, errors).

    Codex W1+W2 fix-pack #1: detector #7 (estimate_drift) accepts
    ``emit_audit`` + identifier args so it can fire its TYPED emitters
    (``emit_estimate_drift_detected`` / ``emit_estimate_drift_systematic_bias``)
    inline. Other detectors continue to use the generic
    ``_try_emit_finding`` path (handled by the CLI loop).
    """
    selected = detector_names or sorted(DETECTOR_REGISTRY.keys())
    findings: List[Dict[str, Any]] = []
    errors: List[str] = []

    detector_fns = {
        "runtime_read_missing": lambda: detect_runtime_read_missing(
            repo_root=repo_root,
        ),
        "installable_claim_drift": lambda: detect_installable_claim_drift(
            repo_root=repo_root,
        ),
        "model_assignment_divergence": lambda: detect_model_assignment_divergence(
            repo_root=repo_root,
            audit_log_path=audit_log_path,
        ),
        "enforcement_commit_unpopulated": lambda: detect_enforcement_commit_unpopulated(
            repo_root=repo_root,
        ),
        "audit_action_phantom": lambda: detect_audit_action_phantom(
            repo_root=repo_root,
        ),
        # PLAN-078 Wave 2 — Reality Ledger detector #7 (estimate-drift).
        # Codex Fix #1: emit-audit + module + identifiers flow inward so the
        # detector can call its TYPED emit wrappers (NOT generic).
        "estimate_drift": lambda: detect_estimate_drift(
            repo_root=repo_root,
            emit_audit=emit_audit,
            audit_emit_module=audit_emit_module,
            session_id=session_id,
            project=project,
        ),
    }

    for name in selected:
        if name not in detector_fns:
            errors.append(f"unknown detector: {name}")
            continue
        f, err = _run_with_timeout(
            detector_fns[name],
            timeout_ms=timeout_ms,
            detector_name=name,
        )
        if err:
            errors.append(err)
        findings.extend(f)
    return findings, errors


def filter_by_severity(findings: List[Dict[str, Any]], min_severity: str) -> List[Dict[str, Any]]:
    if min_severity not in _SEVERITY_ORDER:
        return findings
    threshold = _SEVERITY_ORDER[min_severity]
    return [f for f in findings if _SEVERITY_ORDER.get(f.get("severity", "low"), 0) >= threshold]


# ---------------------------------------------------------------------------
# CLI
# ---------------------------------------------------------------------------

def main(argv: Optional[List[str]] = None) -> int:
    parser = argparse.ArgumentParser(
        prog="reality-ledger",
        description=(
            "Adaptive Execution Kernel claim-vs-evidence detector "
            "(advisory-only; never blocks)."
        ),
    )
    parser.add_argument(
        "--format",
        choices=("markdown", "json", "jsonl"),
        default="markdown",
    )
    parser.add_argument(
        "--detector",
        action="append",
        default=None,
        help="Run only this detector (repeatable). Default: all 5.",
    )
    parser.add_argument(
        "--severity",
        choices=_SEVERITIES,
        default="low",
        help="Minimum severity to emit (low/medium/high). Default: low.",
    )
    parser.add_argument(
        "--detector-timeout-ms",
        type=int,
        default=DEFAULT_DETECTOR_TIMEOUT_MS,
        help=f"Per-detector timeout. Default: {DEFAULT_DETECTOR_TIMEOUT_MS}.",
    )
    parser.add_argument(
        "--since",
        default=None,
        help=(
            "Time window for audit-log observations (e.g. '30d'). "
            "Reserved for Detector #3 in Phase 4."
        ),
    )
    parser.add_argument(
        "--audit-log",
        default=None,
        help=(
            "Path to audit-log.jsonl. Detector #3 only runs when supplied."
        ),
    )
    parser.add_argument(
        "--output",
        default=None,
        help="Output file (default: stdout).",
    )
    parser.add_argument(
        "--repo-root",
        default=str(_REPO_ROOT),
        help="Repository root path (test override).",
    )
    parser.add_argument(
        "--emit-audit",
        action="store_true",
        help=(
            "Best-effort audit emit per finding. No-op if "
            "reality_ledger_finding action is not yet registered."
        ),
    )

    args = parser.parse_args(argv)

    repo_root = Path(args.repo_root).resolve()
    if not repo_root.exists():
        sys.stderr.write(f"[reality-ledger] repo-root not found: {repo_root}\n")
        return 2

    audit_log_path = Path(args.audit_log).resolve() if args.audit_log else None

    t0 = time.perf_counter()
    findings, errors = run_detectors(
        repo_root=repo_root,
        detector_names=args.detector,
        timeout_ms=args.detector_timeout_ms,
        audit_log_path=audit_log_path,
        # Codex W1+W2 fix-pack #1: detector #7 emits via typed wrappers
        # inline; flow emit_audit + identifiers down so they reach it.
        emit_audit=args.emit_audit,
        session_id=os.environ.get("CEO_SESSION_ID", ""),
        project=os.environ.get("CEO_PROJECT", ""),
    )
    elapsed_ms = int((time.perf_counter() - t0) * 1000)

    if errors and not findings:
        # detector internal error path with no salvage
        for e in errors:
            sys.stderr.write(f"[reality-ledger] {e}\n")
        return 2

    if errors:
        # partial run — log errors but continue
        for e in errors:
            sys.stderr.write(f"[reality-ledger] {e}\n")

    findings = filter_by_severity(findings, args.severity)

    # Best-effort audit emit (advisory) — applies to detectors #1-#6 ONLY.
    # Codex W1+W2 fix-pack #1: detector #7 (estimate_drift) already emitted
    # via typed wrappers inline; emitting again via generic
    # ``reality_ledger_finding`` would double-record AND defeat the typed
    # action contract. Skip detector-7 findings here.
    if args.emit_audit:
        for f in findings:
            if f.get("detector") == "estimate_drift":
                continue  # typed emit already fired inside detect_estimate_drift
            _try_emit_finding(f, finding_count_in_run=len(findings))

    # Render
    if args.format == "markdown":
        rendered = render_findings_markdown(findings)
    elif args.format == "json":
        rendered = render_findings_json(findings)
    else:  # jsonl
        rendered = render_findings_jsonl(findings)

    # Append run metadata as a markdown footer (only for markdown)
    if args.format == "markdown":
        rendered = (
            rendered
            + f"\n_run_id: `{uuid.uuid4()}`  ·  duration_ms: `{elapsed_ms}`_\n"
        )

    if args.output:
        try:
            Path(args.output).write_text(rendered, encoding="utf-8")
        except OSError as exc:
            sys.stderr.write(f"[reality-ledger] cannot write output: {exc}\n")
            return 2
    else:
        sys.stdout.write(rendered)
        if not rendered.endswith("\n"):
            sys.stdout.write("\n")

    return 0


if __name__ == "__main__":
    sys.exit(main())
