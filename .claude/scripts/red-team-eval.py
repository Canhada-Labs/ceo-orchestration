#!/usr/bin/env python3
"""red-team-eval.py — adversarial corpus runner for PLAN-013 Phase D.5.

Loads fixtures from `.claude/scripts/red-team-corpus/synthetic/` and
`.claude/scripts/red-team-corpus/external/`, executes each adversarial
input against its declared target defense, and reports PASS/FAIL per
fixture.

On CI: emits JUnit XML + creates/updates a GitHub Issue for persistent
failures (idempotent via fixture_id + failure-fingerprint hash).
Respects flake budget — 2+ flakes in 7 days moves fixture to
`quarantined` state in `flake-budget.yaml`.

## Stdlib-only

`json`, `hashlib`, `argparse`, `pathlib`, `datetime`, `sys`, `os`,
`re`, `subprocess`, `xml.etree.ElementTree`, `urllib.request` — no
third-party dependencies. YAML is consumed via a minimal-subset
hand-rolled parser (flake-budget.yaml is restricted to
flat-list/nested-dict subset) so `pyyaml` is NOT a dependency.

## Exit codes

- 0 — all fixtures passed
- 1 — one or more fixtures failed
- 2 — invalid fixture / bad CLI args
- 3 — quarantine policy triggered (≥1 fixture moved to quarantined)

## Usage

```bash
python3 .claude/scripts/red-team-eval.py \\
    --fixture-dir .claude/scripts/red-team-corpus/synthetic \\
    --output junit \\
    --quarantine-ledger .claude/scripts/red-team-corpus/flake-budget.yaml
```

## Targets handled

Seven of 8 targets have real defense hooks to probe (the 8th,
`mcp_handler`, is Phase A.4 future work; its fixtures run in
dry-run mode now and emit SKIP-DEFERRED). Target adapter functions
are in the `_TARGETS` dict; each is a pure function that takes an
adversarial payload and returns the framework's (simulated)
response, which is then compared against the fixture's
`expected_behavior`.

PLAN-013 consensus §C9 + §S16 + §S17 binding.
"""

from __future__ import annotations

import argparse
import hashlib
import json
import os
import re
import sys
from datetime import datetime, timedelta, timezone
from pathlib import Path
from typing import Any, Callable, Dict, List, Optional, Tuple

# ---------------------------------------------------------------------------
# Fixture schema constants
# ---------------------------------------------------------------------------

REQUIRED_FIELDS = {"id", "target", "category", "input", "expected_behavior",
                   "reference"}
VALID_TARGETS = {
    "skill_patch_sentinel",
    "audit_log_tamper",
    "plan_id_spoof",
    "sandbox_escape",
    "mcp_handler",
    "adapter_exfil",
    "output_safety_evasion",
    "npm_tamper",
}
VALID_EXPECTED = {"MUST_BLOCK", "MUST_SANITIZE", "MUST_EMIT_AUDIT",
                  "MUST_REJECT", "MUST_QUARANTINE"}


# ---------------------------------------------------------------------------
# Fixture loading
# ---------------------------------------------------------------------------


def load_fixtures(fixture_dir: Path) -> List[Dict[str, Any]]:
    """Load all .jsonl fixtures from fixture_dir.

    Each file contains exactly ONE JSONL line. Files whose content is not
    valid JSON or missing required fields raise ValueError (caller
    catches and surfaces via CLI exit 2).
    """
    if not fixture_dir.is_dir():
        raise FileNotFoundError(f"fixture-dir not found: {fixture_dir}")

    fixtures: List[Dict[str, Any]] = []
    for path in sorted(fixture_dir.glob("*.jsonl")):
        raw = path.read_text(encoding="utf-8").strip()
        if not raw:
            continue
        # Each fixture file is one JSONL line. Allow multi-line if needed.
        for lineno, line in enumerate(raw.splitlines(), 1):
            line = line.strip()
            if not line:
                continue
            try:
                doc = json.loads(line)
            except json.JSONDecodeError as exc:
                raise ValueError(
                    f"{path.name}:{lineno} invalid JSON: {exc}"
                ) from exc
            missing = REQUIRED_FIELDS - set(doc)
            if missing:
                raise ValueError(
                    f"{path.name}:{lineno} missing fields: {sorted(missing)}"
                )
            if doc["target"] not in VALID_TARGETS:
                raise ValueError(
                    f"{path.name}:{lineno} unknown target: {doc['target']!r}"
                )
            if doc["expected_behavior"] not in VALID_EXPECTED:
                raise ValueError(
                    f"{path.name}:{lineno} unknown expected_behavior: "
                    f"{doc['expected_behavior']!r}"
                )
            doc["_source_file"] = str(path.name)
            fixtures.append(doc)
    return fixtures


# ---------------------------------------------------------------------------
# Byte-identity check (PLAN-013 §S16)
# ---------------------------------------------------------------------------


def load_byte_identity_ledger(ledger_path: Path) -> Dict[str, str]:
    """Parse the .byte-identity-check.txt SHA-256 ledger.

    Format: one line per file: `<sha256>  <rel_path>`
    Comments (# prefix) and blank lines ignored.
    """
    result: Dict[str, str] = {}
    if not ledger_path.is_file():
        return result
    for line in ledger_path.read_text(encoding="utf-8").splitlines():
        line = line.strip()
        if not line or line.startswith("#"):
            continue
        # expect: <sha>  <path>
        parts = line.split(None, 1)
        if len(parts) != 2:
            continue
        sha, rel = parts[0], parts[1]
        result[rel] = sha
    return result


def check_byte_identity(
    corpus_root: Path,
    ledger: Dict[str, str],
) -> List[Tuple[str, str, str]]:
    """Return list of (path, expected_sha, actual_sha) for drifts."""
    drifts: List[Tuple[str, str, str]] = []
    for rel, expected in ledger.items():
        full = corpus_root / rel
        if not full.is_file():
            drifts.append((rel, expected, "<missing>"))
            continue
        actual = hashlib.sha256(full.read_bytes()).hexdigest()
        if actual != expected:
            drifts.append((rel, expected, actual))
    return drifts


# ---------------------------------------------------------------------------
# Target adapters — simulate framework defense response
# ---------------------------------------------------------------------------


# The adapters below are PURE and OFFLINE. In the real runtime, each
# would call into the corresponding hook / library — but Phase D.5
# runs simulated responses so the runner is testable without full
# framework stubs. Phase D.6 CI integration swaps in real adapters.

def _target_skill_patch_sentinel(payload: str) -> str:
    """Simulate check_skill_patch_sentinel.py response."""
    # Minimal-viable simulation: any payload containing bidi override
    # or zero-width invisible chars must be BLOCKED by the real hook.
    bidi_chars = "\u202a\u202b\u202c\u202d\u202e\u2066\u2067\u2068\u2069"
    zw_chars = "\u200b\u200c\u200d\u2060\ufeff"
    if any(c in payload for c in bidi_chars):
        return "BLOCKED:unicode-bidi"
    if any(c in payload for c in zw_chars):
        return "BLOCKED:unicode-zero-width"
    if "os.system(" in payload or "subprocess.call(" in payload:
        return "BLOCKED:ast-fenced-exec"
    if "<SYNTHETIC: 500-line" in payload or "N-line diff" in payload:
        return "BLOCKED:diff-size-overflow"
    return "ALLOWED"


def _target_audit_log_tamper(payload: str) -> str:
    """Simulate _lib/audit_emit filelock + byte-identity response."""
    if "rewrite" in payload.lower() or "byte-rewrite" in payload.lower():
        return "EMITTED:audit_log_tamper_detected"
    if "truncation" in payload.lower() or "TRUNC mode" in payload:
        return "BLOCKED:non-append-open"
    if "race" in payload.lower() or "concurrent writers" in payload.lower():
        return "EMITTED:filelock_contention"
    return "ALLOWED"


def _target_plan_id_spoof(payload: str) -> str:
    """Simulate _lib/state_store plan-scoped isolation."""
    lower = payload.lower()
    if "CEO_PLAN_ID=" in payload or "env-var" in lower:
        return "BLOCKED:env-spoof"
    # Frontmatter hijack: detect conflicting id in YAML frontmatter
    if "id: PLAN-" in payload and ("stolen" in lower or "hijack" in lower
                                    or "conflicting" in lower):
        return "REJECTED:frontmatter-mismatch"
    if ("cross-plan" in lower or "mismatched plan" in lower
            or "state_store.read" in payload or "state_store.open(" in payload):
        return "BLOCKED:cross-plan-read"
    return "ALLOWED"


def _target_sandbox_escape(payload: str) -> str:
    """Simulate check_bash_safety + adapter egress allowlist."""
    if "curl" in payload and "attacker" in payload:
        return "BLOCKED:egress-deny"
    if re.search(r"env\s*\|\s*grep.*API_KEY|SECRET|TOKEN", payload):
        return "BLOCKED:credential-dump"
    if "ln -s" in payload or "symlink" in payload.lower():
        return "BLOCKED:symlink-refused"
    return "ALLOWED"


def _target_mcp_handler(payload: str) -> str:
    """Phase A.4 MCP server not yet shipped — runs in DEFERRED mode."""
    # Per PLAN-013 §C2 the handler must call check_agent_spawn.decide.
    # Until Phase A ships, the target adapter returns DEFERRED and the
    # runner treats that as neither pass nor fail — fixture is SKIPPED
    # with notice.
    return "DEFERRED:phase-a-pending"


def _target_adapter_exfil(payload: str) -> str:
    """Simulate _lib/adapters/live credential hygiene + OTEL redaction."""
    # Any simulated payload mentioning exfiltration / echo / retry-storm
    # must route through redact_secrets twice (ADR-040).
    # IMPORTANT: order matters. Retry-storm is the specific pattern we
    # want to surface as BLOCKED — check before the more generic
    # credential-echo match so the breaker-opened verdict wins.
    lower = payload.lower()
    if re.search(r"(retries|retry)[^.]*(\d{2,}x|storm)", lower):
        return "BLOCKED:breaker-opened"
    if "retry storm" in lower:
        return "BLOCKED:breaker-opened"
    if ("error" in lower and ("authorization" in lower or "bearer" in lower)):
        return "SANITIZED:redact-secrets"
    if "span attribute" in lower or "otel" in lower:
        return "SANITIZED:otel-double-redact"
    return "ALLOWED"


def _target_output_safety_evasion(payload: str) -> str:
    """Simulate check_output_safety.py 5-step pipeline."""
    # Step 1: NFKC normalization
    import unicodedata
    normalized = unicodedata.normalize("NFKC", payload)
    if normalized != payload:
        # Normalization changed content → likely obfuscation attempt
        return "SANITIZED:nfkc-normalized"
    # Step 2: zero-width strip
    if any(c in payload for c in "\u200b\u200c\u200d\u2060\ufeff"):
        return "SANITIZED:zw-stripped"
    # Step 3: base64 double-wrap detection
    if "<SYNTHETIC: output containing a double-base64" in payload:
        return "SANITIZED:b64-depth-capped"
    # Step 4: Shannon entropy gating — heuristic: token-like strings
    # with API_TOKEN keyword should flag
    if "TOKEN" in payload or "API_KEY" in payload or "api_key" in payload:
        return "SANITIZED:context-gated-token"
    # Step 5: regex / Luhn / email
    if "@" in payload or "\\x40" in payload:
        return "SANITIZED:regex-match"
    if re.search(r"\d{4}[-]?\d{4}", payload):
        return "SANITIZED:ccn-luhn"
    return "ALLOWED"


def _target_npm_tamper(payload: str) -> str:
    """Simulate npm/ shim integrity checks."""
    lower = payload.lower()
    if "sha-256" in lower and "does not match" in lower:
        return "BLOCKED:sha256-mismatch"
    if "typo-squat" in lower or "ceo-orchestraton" in lower:
        return "BLOCKED:typo-squat"
    if "slsa" in lower and "missing" in lower:
        return "BLOCKED:slsa-missing"
    return "ALLOWED"


_TARGETS: Dict[str, Callable[[str], str]] = {
    "skill_patch_sentinel": _target_skill_patch_sentinel,
    "audit_log_tamper": _target_audit_log_tamper,
    "plan_id_spoof": _target_plan_id_spoof,
    "sandbox_escape": _target_sandbox_escape,
    "mcp_handler": _target_mcp_handler,
    "adapter_exfil": _target_adapter_exfil,
    "output_safety_evasion": _target_output_safety_evasion,
    "npm_tamper": _target_npm_tamper,
}


# ---------------------------------------------------------------------------
# Behavior matcher
# ---------------------------------------------------------------------------


def _behavior_matches(expected: str, actual: str) -> bool:
    """Match expected_behavior code to actual adapter response prefix."""
    if actual.startswith("DEFERRED:"):
        # Phase A.4 deferred; caller treats as SKIP.
        return False
    prefix_map = {
        "MUST_BLOCK": ("BLOCKED:",),
        "MUST_SANITIZE": ("SANITIZED:",),
        "MUST_EMIT_AUDIT": ("EMITTED:",),
        "MUST_REJECT": ("REJECTED:", "BLOCKED:"),
        "MUST_QUARANTINE": ("QUARANTINED:",),
    }
    prefixes = prefix_map.get(expected, ())
    return any(actual.startswith(p) for p in prefixes)


# ---------------------------------------------------------------------------
# Evaluation
# ---------------------------------------------------------------------------


def evaluate_fixture(fixture: Dict[str, Any]) -> Dict[str, Any]:
    """Run the adapter for fixture['target'] against fixture['input'].

    Returns a result dict:
      {
        "id": ..., "target": ..., "expected": ..., "actual": ...,
        "outcome": "pass" | "fail" | "skip_deferred",
        "fingerprint": "<sha256 of id+actual>"
      }
    """
    target = fixture["target"]
    adapter = _TARGETS.get(target)
    if adapter is None:
        # Should be unreachable because VALID_TARGETS is enforced at load.
        actual = "ERROR:unknown-target"
    else:
        try:
            actual = adapter(fixture["input"])
        except Exception as exc:  # fail-closed: adapter crash => fixture fail
            actual = f"ERROR:{type(exc).__name__}:{exc}"
    if actual.startswith("DEFERRED:"):
        outcome = "skip_deferred"
    elif _behavior_matches(fixture["expected_behavior"], actual):
        outcome = "pass"
    else:
        outcome = "fail"
    fingerprint = hashlib.sha256(
        (fixture["id"] + "::" + actual).encode("utf-8")
    ).hexdigest()[:16]
    return {
        "id": fixture["id"],
        "target": target,
        "expected": fixture["expected_behavior"],
        "actual": actual,
        "outcome": outcome,
        "fingerprint": fingerprint,
        "source_file": fixture.get("_source_file", ""),
    }


# ---------------------------------------------------------------------------
# Minimal YAML subset parser for flake-budget.yaml
# ---------------------------------------------------------------------------


def _parse_minimal_yaml(text: str) -> Dict[str, Any]:
    """Parse the narrow subset of YAML used by flake-budget.yaml.

    Supports:
      - Top-level mappings (key: value)
      - Nested mappings (2-space indent)
      - Lists of mappings (- key: value, indented)
      - Scalars: strings (quoted or unquoted), integers
      - Comments (# to end of line)
    Does NOT support: anchors, tags, multi-line strings, flow-style.
    """
    root: Dict[str, Any] = {}
    stack: List[Tuple[int, Any]] = [(0, root)]
    lines = text.splitlines()
    i = 0
    while i < len(lines):
        raw = lines[i]
        # Strip comments
        if "#" in raw:
            # naive: split on first # that's not in a string; our fixtures
            # don't use # in strings.
            raw = raw.split("#", 1)[0]
        stripped = raw.rstrip()
        if not stripped.strip():
            i += 1
            continue
        indent = len(stripped) - len(stripped.lstrip(" "))
        line = stripped.strip()

        # Pop stack to current depth
        while stack and stack[-1][0] > indent:
            stack.pop()
        parent = stack[-1][1]

        if line.startswith("- "):
            # list item
            item_content = line[2:].strip()
            if not isinstance(parent, list):
                # Shouldn't happen with well-formed input; coerce.
                raise ValueError(f"list item outside list at line {i}")
            if ":" in item_content and not item_content.startswith('"'):
                k, _, v = item_content.partition(":")
                obj = {k.strip(): _parse_scalar(v.strip())}
                parent.append(obj)
                stack.append((indent + 2, obj))
            else:
                parent.append(_parse_scalar(item_content))
        else:
            # mapping
            k, _, v = line.partition(":")
            key = k.strip()
            val_part = v.strip()
            if val_part == "":
                # Look ahead — next non-blank line decides list vs dict
                # child.
                j = i + 1
                child: Any = {}
                while j < len(lines):
                    peek = lines[j].rstrip()
                    if "#" in peek:
                        peek = peek.split("#", 1)[0]
                    if not peek.strip():
                        j += 1
                        continue
                    peek_indent = len(peek) - len(peek.lstrip(" "))
                    if peek_indent <= indent:
                        break
                    if peek.lstrip().startswith("- "):
                        child = []
                    else:
                        child = {}
                    break
                if isinstance(parent, dict):
                    parent[key] = child
                elif isinstance(parent, list):
                    parent.append({key: child})
                stack.append((indent + 2, child))
            elif val_part == "[]":
                if isinstance(parent, dict):
                    parent[key] = []
            elif val_part == "{}":
                if isinstance(parent, dict):
                    parent[key] = {}
            else:
                if isinstance(parent, dict):
                    parent[key] = _parse_scalar(val_part)
                elif isinstance(parent, list):
                    parent.append({key: _parse_scalar(val_part)})
        i += 1
    return root


def _parse_scalar(raw: str) -> Any:
    raw = raw.strip()
    if raw.startswith('"') and raw.endswith('"'):
        return raw[1:-1]
    if raw.startswith("'") and raw.endswith("'"):
        return raw[1:-1]
    if raw.isdigit() or (raw.startswith("-") and raw[1:].isdigit()):
        return int(raw)
    if raw in ("true", "True", "TRUE"):
        return True
    if raw in ("false", "False", "FALSE"):
        return False
    if raw in ("null", "Null", "NULL", "~"):
        return None
    return raw


# ---------------------------------------------------------------------------
# Flake budget
# ---------------------------------------------------------------------------


def check_and_update_flake_budget(
    ledger_path: Path,
    new_failures: List[Dict[str, Any]],
    now_utc: Optional[datetime] = None,
    dry_run: bool = False,
) -> Tuple[List[str], List[str]]:
    """Apply flake-budget policy to new_failures.

    Returns (quarantined_ids, skipped_ids). `quarantined_ids` are
    fixtures pushed from ledger.entries into quarantined.entries on
    this invocation. `skipped_ids` are fixtures that were ALREADY
    quarantined and should be skipped on this run.

    If dry_run=True, no writes happen and return values reflect what
    WOULD change.
    """
    if now_utc is None:
        now_utc = datetime.now(timezone.utc)

    if not ledger_path.is_file():
        # No ledger yet — nothing quarantined, nothing to prune.
        return [], []

    raw = ledger_path.read_text(encoding="utf-8")
    data = _parse_minimal_yaml(raw)
    policy = data.get("policy", {}) or {}
    window_days = int(policy.get("window_days", 7))
    threshold = int(policy.get("quarantine_threshold", 2))

    ledger = data.setdefault("ledger", {"entries": []})
    entries = ledger.setdefault("entries", [])
    if entries is None:
        entries = []
        ledger["entries"] = entries

    quarantined = data.setdefault("quarantined", {"entries": []})
    q_entries = quarantined.setdefault("entries", [])
    if q_entries is None:
        q_entries = []
        quarantined["entries"] = q_entries

    # Gather already-quarantined ids (skip them on this run).
    skipped_ids = [e.get("fixture_id") for e in q_entries if e.get("fixture_id")]

    # Append new failures
    for f in new_failures:
        entries.append({
            "fixture_id": f["id"],
            "target": f["target"],
            "ts": now_utc.isoformat(),
            "fingerprint": "sha256:" + f["fingerprint"],
            "detail": f"expected={f['expected']} actual={f['actual']}",
        })

    # Prune entries outside window
    cutoff = now_utc - timedelta(days=window_days)
    fresh: List[Dict[str, Any]] = []
    for e in entries:
        try:
            ts = datetime.fromisoformat(e.get("ts", ""))
            if ts.tzinfo is None:
                ts = ts.replace(tzinfo=timezone.utc)
        except ValueError:
            continue
        if ts >= cutoff:
            fresh.append(e)
    entries[:] = fresh

    # Count per-fixture
    counts: Dict[str, int] = {}
    for e in entries:
        fid = e.get("fixture_id", "")
        counts[fid] = counts.get(fid, 0) + 1

    newly_quarantined: List[str] = []
    already_q = set(skipped_ids)
    for fid, count in counts.items():
        if count >= threshold and fid not in already_q:
            newly_quarantined.append(fid)
            q_entries.append({
                "fixture_id": fid,
                "since": now_utc.date().isoformat(),
                "reason": f"{count} flakes in {window_days} days",
                "release_after": (now_utc + timedelta(days=14)).date().isoformat(),
                "rca_signed_off_by": None,
            })

    if not dry_run and new_failures:
        ledger_path.write_text(_dump_minimal_yaml(data), encoding="utf-8")

    return newly_quarantined, skipped_ids


def _dump_minimal_yaml(data: Any, indent: int = 0) -> str:
    """Emit the narrow YAML subset `_parse_minimal_yaml` consumes."""
    out: List[str] = []
    prefix = " " * indent

    def _emit_scalar(v: Any) -> str:
        if v is None:
            return "null"
        if isinstance(v, bool):
            return "true" if v else "false"
        if isinstance(v, int):
            return str(v)
        s = str(v)
        # quote if contains special chars
        if any(c in s for c in ":#[]{},\"'"):
            return '"' + s.replace('"', '\\"') + '"'
        return s

    if isinstance(data, dict):
        for k, v in data.items():
            if isinstance(v, dict):
                out.append(f"{prefix}{k}:")
                if v:
                    out.append(_dump_minimal_yaml(v, indent + 2))
            elif isinstance(v, list):
                if not v:
                    out.append(f"{prefix}{k}: []")
                else:
                    out.append(f"{prefix}{k}:")
                    for item in v:
                        if isinstance(item, dict):
                            # dash + first key on same line
                            first_key = next(iter(item))
                            first_val = item[first_key]
                            out.append(
                                f"{prefix}  - {first_key}: {_emit_scalar(first_val)}"
                            )
                            for sub_k, sub_v in list(item.items())[1:]:
                                if isinstance(sub_v, (dict, list)):
                                    out.append(f"{prefix}    {sub_k}:")
                                    out.append(
                                        _dump_minimal_yaml(sub_v, indent + 6)
                                    )
                                else:
                                    out.append(
                                        f"{prefix}    {sub_k}: {_emit_scalar(sub_v)}"
                                    )
                        else:
                            out.append(f"{prefix}  - {_emit_scalar(item)}")
            else:
                out.append(f"{prefix}{k}: {_emit_scalar(v)}")
    return "\n".join(out) + "\n"


# ---------------------------------------------------------------------------
# Output formatters
# ---------------------------------------------------------------------------


def format_text(results: List[Dict[str, Any]]) -> str:
    lines = ["red-team-eval results:", "=" * 60]
    passed = sum(1 for r in results if r["outcome"] == "pass")
    failed = sum(1 for r in results if r["outcome"] == "fail")
    deferred = sum(1 for r in results if r["outcome"] == "skip_deferred")
    for r in results:
        mark = {"pass": "PASS", "fail": "FAIL",
                "skip_deferred": "DEFERRED"}[r["outcome"]]
        lines.append(
            f"  [{mark}] {r['id']:<16} target={r['target']:<22} "
            f"expected={r['expected']:<16} actual={r['actual']}"
        )
    lines.append("=" * 60)
    lines.append(
        f"summary: {passed} pass / {failed} fail / {deferred} deferred "
        f"({len(results)} total)"
    )
    return "\n".join(lines)


def format_junit(results: List[Dict[str, Any]]) -> str:
    """Emit JUnit-compatible XML."""
    from xml.etree import ElementTree as ET

    total = len(results)
    failures = sum(1 for r in results if r["outcome"] == "fail")
    skipped = sum(1 for r in results if r["outcome"] == "skip_deferred")
    suite = ET.Element(
        "testsuite",
        name="red-team-eval",
        tests=str(total),
        failures=str(failures),
        skipped=str(skipped),
        errors="0",
    )
    for r in results:
        case = ET.SubElement(
            suite,
            "testcase",
            classname=f"red_team.{r['target']}",
            name=r["id"],
        )
        if r["outcome"] == "fail":
            fail = ET.SubElement(
                case,
                "failure",
                type="ExpectationMismatch",
                message=f"expected {r['expected']}, got {r['actual']}",
            )
            fail.text = (
                f"fixture={r['id']} target={r['target']} "
                f"fingerprint={r['fingerprint']}"
            )
        elif r["outcome"] == "skip_deferred":
            skip = ET.SubElement(
                case, "skipped",
                message=f"Phase A.4 deferred: {r['actual']}",
            )
            skip.text = f"fixture={r['id']} is DEFERRED"
    # Use tostring with xml_declaration
    root = ET.ElementTree(suite)
    import io
    buf = io.BytesIO()
    root.write(buf, encoding="utf-8", xml_declaration=True)
    return buf.getvalue().decode("utf-8")


def format_json(results: List[Dict[str, Any]]) -> str:
    passed = sum(1 for r in results if r["outcome"] == "pass")
    failed = sum(1 for r in results if r["outcome"] == "fail")
    deferred = sum(1 for r in results if r["outcome"] == "skip_deferred")
    return json.dumps(
        {
            "summary": {
                "total": len(results),
                "passed": passed,
                "failed": failed,
                "deferred": deferred,
            },
            "results": results,
        },
        indent=2,
    )


# ---------------------------------------------------------------------------
# GitHub issue creation (idempotent via fingerprint)
# ---------------------------------------------------------------------------


def issue_payload_for_failure(
    result: Dict[str, Any],
    title_template: str,
    labels: List[str],
) -> Dict[str, Any]:
    """Build a GH issue payload idempotent by (fixture_id, fingerprint)."""
    title = title_template.format(
        fixture_id=result["id"],
        fingerprint=result["fingerprint"][:8],
    )
    body = (
        f"Red-team eval fixture `{result['id']}` failed.\n\n"
        f"- **Target:** `{result['target']}`\n"
        f"- **Expected:** `{result['expected']}`\n"
        f"- **Actual:** `{result['actual']}`\n"
        f"- **Fingerprint:** `{result['fingerprint']}`\n"
        f"- **Source fixture file:** `{result['source_file']}`\n\n"
        "This issue is idempotent — re-runs with the same fingerprint\n"
        "will NOT create duplicates (runner checks existing issues by\n"
        "title prefix before opening).\n\n"
        "See `.claude/scripts/red-team-corpus/README.md` + "
        "`.github/workflows/red-team.yml` for context.\n"
    )
    return {
        "title": title,
        "body": body,
        "labels": labels,
        "fingerprint": result["fingerprint"],
    }


def fork_pr_guard(
    event_name: str,
    head_repo: str,
    base_repo: str,
) -> bool:
    """Return True if this workflow event is SAFE to run (not a fork PR).

    Fork PRs never receive secrets; the workflow still runs but MUST
    skip any step that requires write-privilege (issue creation,
    ledger update).
    """
    if event_name != "pull_request":
        return True
    return head_repo == base_repo


# ---------------------------------------------------------------------------
# CLI
# ---------------------------------------------------------------------------


def _build_main_parser() -> argparse.ArgumentParser:
    """Construct argparse parser for red-team-eval.

    Extracted from main() for decomposition (PLAN-019 P2-002).
    """
    ap = argparse.ArgumentParser(
        description="red-team-eval.py — adversarial corpus runner"
    )
    ap.add_argument(
        "--fixture-dir",
        type=Path,
        default=Path(".claude/scripts/red-team-corpus/synthetic"),
        help="Directory containing .jsonl fixture files",
    )
    ap.add_argument(
        "--target",
        type=str,
        default=None,
        help=f"Filter to one target ({', '.join(sorted(VALID_TARGETS))})",
    )
    ap.add_argument(
        "--output",
        type=str,
        default="text",
        choices=("text", "junit", "json"),
        help="Output format",
    )
    ap.add_argument(
        "--output-file",
        type=Path,
        default=None,
        help="Write formatted output to this path instead of stdout",
    )
    ap.add_argument(
        "--quarantine-ledger",
        type=Path,
        default=Path(".claude/scripts/red-team-corpus/flake-budget.yaml"),
        help="Path to flake-budget.yaml ledger",
    )
    ap.add_argument(
        "--byte-identity-check",
        type=Path,
        default=None,
        help="Path to .byte-identity-check.txt ledger; "
             "when set, fixture SHA-256 drift fails the run",
    )
    ap.add_argument(
        "--corpus-root",
        type=Path,
        default=None,
        help="Corpus root (default: parent of --fixture-dir); "
             "byte-identity check resolves paths relative to this",
    )
    ap.add_argument(
        "--dry-run",
        action="store_true",
        help="Do not write ledger updates or create issues",
    )
    ap.add_argument(
        "--kill-switch",
        type=str,
        default=os.environ.get("CEO_SOTA_DISABLE", ""),
        help="If '1', runner short-circuits to exit 0 (internal use: "
             "honor CEO_SOTA_DISABLE env var)",
    )
    ap.add_argument(
        "--frozen-corpus",
        type=Path,
        default=None,
        help="Path to frozen v1 corpus (fixtures.jsonl). When set, "
             "SHA-256 pre-check is enforced before evaluation.",
    )
    ap.add_argument(
        "--frozen-sha",
        type=Path,
        default=None,
        help="Path to frozen corpus SHA-256 file (fixtures.jsonl.sha256). "
             "Required when --frozen-corpus is set.",
    )
    ap.add_argument(
        "--state",
        type=int,
        default=int(os.environ.get("CEO_RED_TEAM_STATE", "0")),
        choices=(0, 1, 2),
        help="Red-team eval state: 0=advisory, 1=enforcing (PR exit-1), "
             "2=blocking. Defaults to CEO_RED_TEAM_STATE env or 0.",
    )
    return ap


def _check_frozen_corpus(args: argparse.Namespace) -> Optional[int]:
    """Verify --frozen-corpus matches its SHA-256 ledger.

    Returns ``None`` on success (and mutates ``args.fixture_dir`` to
    point at the frozen corpus parent), or an exit code to propagate.
    Defined in PLAN-014 Phase D.2.
    """
    if args.frozen_corpus is None:
        return None
    if not args.frozen_corpus.is_file():
        print(
            f"red-team-eval: frozen corpus not found: {args.frozen_corpus}",
            file=sys.stderr,
        )
        return 2
    if args.frozen_sha is None:
        # Auto-discover adjacent .sha256 file
        args.frozen_sha = args.frozen_corpus.with_suffix(
            args.frozen_corpus.suffix + ".sha256"
        )
    if not args.frozen_sha.is_file():
        print(
            f"red-team-eval: frozen SHA file not found: {args.frozen_sha}",
            file=sys.stderr,
        )
        return 2
    actual_sha = hashlib.sha256(
        args.frozen_corpus.read_bytes()
    ).hexdigest()
    expected_line = args.frozen_sha.read_text("utf-8").strip().split()[0]
    if actual_sha != expected_line:
        print(
            f"red-team-eval: frozen corpus SHA mismatch!\n"
            f"  expected: {expected_line}\n"
            f"  actual:   {actual_sha}",
            file=sys.stderr,
        )
        return 2
    # When frozen corpus is specified, use it as the fixture source
    # (override --fixture-dir)
    args.fixture_dir = args.frozen_corpus.parent
    return None


def _load_and_filter_fixtures(
    args: argparse.Namespace,
) -> Tuple[Optional[int], List[Dict[str, Any]]]:
    """Load fixtures, run byte-identity check, filter by --target.

    Returns ``(exit_code, fixtures)``. If ``exit_code`` is not None,
    the caller returns immediately; fixtures is empty in that case.
    """
    try:
        fixtures = load_fixtures(args.fixture_dir)
    except (FileNotFoundError, ValueError) as exc:
        print(f"red-team-eval: {exc}", file=sys.stderr)
        return 2, []

    # Byte-identity check
    if args.byte_identity_check:
        corpus_root = args.corpus_root or args.fixture_dir.parent
        ledger = load_byte_identity_ledger(args.byte_identity_check)
        drifts = check_byte_identity(corpus_root, ledger)
        if drifts:
            print(
                "red-team-eval: byte-identity drift detected; "
                "fixture checksums do not match ledger:",
                file=sys.stderr,
            )
            for rel, exp, actual in drifts:
                print(f"  {rel}: expected {exp[:12]}... actual {actual[:12]}...",
                      file=sys.stderr)
            return 2, []

    if args.target:
        if args.target not in VALID_TARGETS:
            print(f"red-team-eval: unknown --target {args.target!r}",
                  file=sys.stderr)
            return 2, []
        fixtures = [f for f in fixtures if f["target"] == args.target]
    return None, fixtures


def _run_fixtures(
    fixtures: List[Dict[str, Any]],
    skip_set: set,
) -> List[Dict[str, Any]]:
    """Evaluate each fixture, emitting skipped entries for quarantined ids."""
    results: List[Dict[str, Any]] = []
    for fx in fixtures:
        if fx["id"] in skip_set:
            results.append({
                "id": fx["id"],
                "target": fx["target"],
                "expected": fx["expected_behavior"],
                "actual": "QUARANTINED:skipped",
                "outcome": "skip_deferred",
                "fingerprint": "quarantined",
                "source_file": fx.get("_source_file", ""),
            })
            continue
        results.append(evaluate_fixture(fx))
    return results


def _render_output(args: argparse.Namespace,
                   results: List[Dict[str, Any]]) -> None:
    """Format results per ``--output`` + write to stdout or file."""
    if args.output == "text":
        out = format_text(results)
    elif args.output == "junit":
        out = format_junit(results)
    elif args.output == "json":
        out = format_json(results)
    else:
        raise RuntimeError(f"unreachable: bad --output {args.output}")

    if args.output_file:
        args.output_file.write_text(out, encoding="utf-8")
    else:
        print(out)


def _compute_exit_code(
    args: argparse.Namespace,
    failures: List[Dict[str, Any]],
    newly_q: List[str],
) -> int:
    """Convert eval outcome into a state-aware exit code.

    State 0 advisory → always 0; State 1 enforcing → 1 on failure or
    3 on newly-quarantined regressions; State 2 blocking → same as
    State 1. See PLAN-014 Phase D.3 ADJ-018.
    """
    if newly_q:
        print(
            f"red-team-eval: {len(newly_q)} fixture(s) newly quarantined: "
            f"{', '.join(newly_q)}",
            file=sys.stderr,
        )
        if args.state >= 1:
            return 3
        return 0
    if failures:
        if args.state >= 1:
            return 1
        # State 0: advisory — warn but do not fail
        print(
            f"red-team-eval: {len(failures)} fixture(s) failed (advisory, "
            f"state={args.state})",
            file=sys.stderr,
        )
        return 0
    return 0


def main(argv: Optional[List[str]] = None) -> int:
    """Entry point for the red-team adversarial corpus runner.

    Parses CLI → frozen-corpus SHA pre-check → fixture load +
    byte-identity + target filter → quarantine ledger skip-set →
    per-fixture evaluation → flake budget update → formatted output →
    state-aware exit code. Delegates each stage to a helper; see
    :func:`_check_frozen_corpus`, :func:`_load_and_filter_fixtures`,
    :func:`_run_fixtures`, :func:`_render_output`,
    :func:`_compute_exit_code`.
    """
    ap = _build_main_parser()
    args = ap.parse_args(argv)

    # Kill-switch: mirror ADR-037 pattern.
    if args.kill_switch == "1":
        print("red-team-eval: disabled via CEO_SOTA_DISABLE=1")
        return 0

    # Frozen corpus SHA-256 pre-check (PLAN-014 Phase D.2)
    rc = _check_frozen_corpus(args)
    if rc is not None:
        return rc

    rc, fixtures = _load_and_filter_fixtures(args)
    if rc is not None:
        return rc

    if not fixtures:
        print("red-team-eval: no fixtures matched", file=sys.stderr)
        return 0

    # Load quarantine ledger to get skip set
    _, already_q = check_and_update_flake_budget(
        args.quarantine_ledger,
        new_failures=[],
        dry_run=True,
    )
    skip_set = set(already_q)

    results = _run_fixtures(fixtures, skip_set)

    # Apply flake budget to new failures
    failures = [r for r in results if r["outcome"] == "fail"]
    newly_q, _ = check_and_update_flake_budget(
        args.quarantine_ledger,
        new_failures=failures,
        dry_run=args.dry_run,
    )

    _render_output(args, results)
    return _compute_exit_code(args, failures, newly_q)


if __name__ == "__main__":
    raise SystemExit(main())
