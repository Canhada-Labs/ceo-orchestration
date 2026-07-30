#!/usr/bin/env python3
"""check-hook-stdout-schema.py — hook stdout/exit-code contract oracle.

PLAN-163 T2.1/T2.2 (substrate uplift, CC 2.1.220). Destination:
``.claude/scripts/check-hook-stdout-schema.py`` (non-canonical scripts/ tier).

## Why this oracle exists (the REAL contract, do not invent another)

The shim ``.claude/hooks/_python-hook.sh`` (lines 409-413) is a pure
``exec`` on the Claude adapter path: whatever exit code a wired Python hook
produces reaches the harness UNALTERED. Under Claude Code >= 2.1.214 an
accidental ``exit 2`` on a blocking event BLOCKS the tool call. The
framework contract (CLAUDE.md §4) is therefore:

- INFRASTRUCTURE failure (missing file, import error, broken env) →
  fail-OPEN: emit ``{}`` (schema-compliant allow, or an allow-shaped JSON
  advisory) and **exit 0**. Never a nonzero exit, never a deny.
- INPUT-parse failure inside a SECURITY MATCHER (content the guard cannot
  parse — the ``check_bash_safety.py`` ``_e3`` whole-command parse gate
  precedent, codified by PLAN-152 debate C4) → fail-CLOSED: emit a
  block/deny decision-JSON and **exit 0**. Intentional denies are
  exit-0 + decision-JSON — the decision, not the exit code, carries them.

Three argparse CLIs under ``.claude/hooks/`` are OUT OF SCOPE by design:
``check_harness_config.py`` (KEEPS its exit!=0 contract — consumed by the
validate.yml harness-config gate, see validate.yml:960-984),
``emit_architect_outcome.py`` and ``policy_dispatch.py``. None of them is
wired in ``settings.json``; if one ever appears wired through the shim,
this oracle fails loudly (an argparse CLI's ``exit 2`` on bad argv is the
exact accidental-block class this gate exists to stop).

## What it does

(a) Derives the set of WIRED hooks by parsing ``.claude/settings.json`` at
    RUNTIME (zero hardcoded counts): every ``hooks.<Event>[].hooks[]``
    command routed through ``_python-hook.sh <script>.py``.
(b) INFRA fixture per registration: a valid, benign hook-input JSON for the
    registration's event/matcher (generated from the matcher itself; see
    ``_payload_for``) run with a CONTROLLED BROKEN env
    (``CLAUDE_PROJECT_DIR`` pointing at a nonexistent dir, fresh temp
    ``HOME``). Asserts: exit 0, stdout empty or schema-valid JSON, and NO
    deny/block decision (an infra failure must never manifest as a deny).
(c) SECURITY-MATCHER fixture: for each hook in ``_SECURITY_MATCHERS`` an
    INPUT-parse-failure payload run with a SANE isolated env (temp HOME +
    empty temp project). Asserts: exit 0 AND a block/deny decision-JSON.
(d) Validates the stdout schema on BOTH paths — built-in structural rules
    always; plus the versioned snapshot when available (below).
(e) STATIC check over every wired hook file: rejects ``import argparse``
    (and ``from argparse import ...``) and unhandled SystemExit-class
    exits with a constant nonzero status (``sys.exit(2)``,
    ``raise SystemExit(1)``, ``os._exit(3)``, builtin ``exit(2)``).
    ``sys.exit(main())`` (non-constant) is allowed — the behavioral
    checks own that path. Constant nonzero exits inside functions ONLY
    reachable via an argv-gated ``__main__`` branch (the ``--selftest``
    pattern; the shim passes no extra argv to wired hooks) are downgraded
    to warnings.

## Versioned schema snapshot (T2.2 / CF-5)

``--schema-snapshot <path>`` (default: ``.claude/data/hook-schema-2.1.220.json``)
points at the extracted CC 2.1.220 hook-output schema snapshot. The
snapshot is produced by the S284 schema-extract probe (extraction recipe
+ binary sha256 in the artifact's own ``_meta``; provenance:
``.claude/plans/PLAN-163/probes/hook-schema-2.1.220.json``, staged
verbatim to ``.claude/data/hook-schema-2.1.220.json`` — sha256
``acd9b05f8bf1d789c743f390a5218ababfe2c733ff13cdd49e78785c479abcee``).
This oracle does NOT extract the schema itself. Snapshot absent → the
snapshot half is SKIPPED with a warning (built-in structural validation
still runs); snapshot present but unrecognized shape → warning + skip.

**Fail-CLOSED in CI (M3/C7).** WARN-and-skip is a DEV-LOCAL convenience
only. In CI — detected via ``$GITHUB_ACTIONS`` or ``$CI``, or forced with
``--require-snapshot`` (the validate.yml gate passes it explicitly) — a
missing / unreadable / unrecognized snapshot is a fail-CLOSED VIOLATION
(nonzero exit), because a governance gate must not silently pass after
losing its versioned authority. The error carries the regeneration recipe
(restore the committed ``.claude/data/hook-schema-2.1.220.json`` byte-for-byte
from the S284 probe artifact, or re-extract from the CC binary per that
artifact's ``_meta.recipe``). This is ADDITIVE — every other oracle check
(static, behavioral, built-in structural) still runs regardless.

Recognized snapshot shapes (tolerant by design — the probe owns the
format): a JSON object carrying either
  {"events": {"<Event>": {"allowed_top_level_keys": [...]}, ...}}
or a global {"allowed_top_level_keys": [...]}
or a JSON-schema-ish {"properties": {...}} (its keys become the allowed
top-level key set)
or the S284 schema-extract probe shape {"common_output_schema": {<key>:
"<zod description>", ...}} — its keys become the allowed set (the
"async_variant" meta-entry expands to the ``async``/``asyncTimeout`` keys
of the documented async union). When a key set is resolved, any stdout
JSON top-level key outside the set is a VIOLATION.

## Isolation

TestEnvContext-style, subprocess edition: every hook subprocess runs with
an EXPLICIT env dict (fresh temp HOME, controlled CLAUDE_PROJECT_DIR,
CEO_HOOK_ADAPTER=claude, CEO_AUDIT_SYNC_MODE=1) — the real ``$HOME`` and
the operator's live env never leak in, and nothing is written outside the
temp tree.

## Usage

    python3 .claude/scripts/check-hook-stdout-schema.py \
        [--repo <path>] [--schema-snapshot <path>] [--require-snapshot] \
        [--only <script.py>] [--skip-behavioral] [--json] [--verbose]

Exit contract: 0 all-green / 1 one-or-more violations (INCLUDING a
required-but-unavailable schema snapshot under CI or ``--require-snapshot``)
/ 2 unusable input (settings.json missing or unparseable). NO-SPEED-CLAIM:
this gate is about governance and auditability of the hook rail, not
throughput.
"""

from __future__ import annotations

import ast
import json
import os
import re
import shutil
import subprocess
import sys
import tempfile
import uuid
from pathlib import Path
from typing import Any, Dict, List, Optional, Tuple

# ---------------------------------------------------------------------------
# Constants
# ---------------------------------------------------------------------------

_SHIM_RE = re.compile(r"_python-hook\.sh\"?\s+([A-Za-z0-9_.-]+\.py)\b")

# Argparse CLIs that live under .claude/hooks/ but are NOT hooks (they are
# operator/CI CLIs with a deliberate exit!=0 contract). They stay out of
# scope while UNWIRED; a wired appearance is a hard violation.
_ARGPARSE_CLI_ALLOWLIST = frozenset(
    {
        "check_harness_config.py",  # exit!=0 contract: validate.yml:960-984
        "emit_architect_outcome.py",
        "policy_dispatch.py",
    }
)

# Built-in structural knowledge of the CC hook-output surface. This is a
# WARN-tier reference (unknown key => warning); the versioned snapshot is
# the FAIL-tier authority when present. Derived from the Claude Code hooks
# output contract as of 2.1.220 plus the framework's own advisory keys.
_BUILTIN_KNOWN_TOP_LEVEL_KEYS = frozenset(
    {
        "decision",
        "reason",
        "continue",
        "stopReason",
        "suppressOutput",
        "systemMessage",
        "hookSpecificOutput",
        "additionalContext",
        "message",
        "permissionDecision",
        "permissionDecisionReason",
    }
)

_DENY_DECISIONS = frozenset({"block", "deny"})

# Security matchers: hooks whose INPUT-parse-failure path is fail-CLOSED by
# design (CLAUDE.md §4 input half; PLAN-152 debate C4). Each entry maps the
# hook script to an input payload the guard cannot parse and MUST block.
# check_bash_safety.py: the _e3 whole-command shlex parse gate — an
# unterminated quote fails shlex.split and must emit a block decision.
_SECURITY_MATCHERS: Dict[str, Dict[str, Any]] = {
    "check_bash_safety.py": {
        "hook_event_name": "PreToolUse",
        "session_id": "hook-stdout-schema-oracle",
        "tool_name": "Bash",
        "tool_input": {"command": 'echo "unterminated'},
    },
}

_DEFAULT_SNAPSHOT_REL = Path(".claude/data/hook-schema-2.1.220.json")

# Per-subprocess wall cap (seconds) on top of the registration's own
# settings.json timeout. Broken-env runs return in well under a second;
# the cap only exists so a hung hook turns into a reported violation
# instead of a hung CI job.
_TIMEOUT_FLOOR_S = 15
_TIMEOUT_CEIL_S = 150


# ---------------------------------------------------------------------------
# Small arg parser (deliberately NOT argparse — this oracle polices argparse
# in hooks; keeping the dependency out of its own process is cheap honesty).
# ---------------------------------------------------------------------------

def _parse_args(argv: List[str]) -> Dict[str, Any]:
    opts: Dict[str, Any] = {
        "repo": None,
        "schema_snapshot": None,
        "require_snapshot": False,
        "only": [],
        "skip_behavioral": False,
        "json": False,
        "verbose": False,
    }
    i = 0
    while i < len(argv):
        a = argv[i]
        if a == "--repo" and i + 1 < len(argv):
            opts["repo"] = argv[i + 1]
            i += 2
        elif a == "--schema-snapshot" and i + 1 < len(argv):
            opts["schema_snapshot"] = argv[i + 1]
            i += 2
        elif a == "--require-snapshot":
            opts["require_snapshot"] = True
            i += 1
        elif a == "--only" and i + 1 < len(argv):
            opts["only"].append(argv[i + 1])
            i += 2
        elif a == "--skip-behavioral":
            opts["skip_behavioral"] = True
            i += 1
        elif a == "--json":
            opts["json"] = True
            i += 1
        elif a in ("--verbose", "-v"):
            opts["verbose"] = True
            i += 1
        elif a in ("--help", "-h"):
            print(__doc__)
            raise SystemExit(0)
        else:
            print("check-hook-stdout-schema: unknown argument %r" % a, file=sys.stderr)
            raise SystemExit(2)
    return opts


def _env_truthy(val: Optional[str]) -> bool:
    """A CI-style boolean env var is truthy unless explicitly off/empty."""
    if val is None:
        return False
    return val.strip().lower() not in ("", "0", "false", "no", "off")


def _require_snapshot_active(opts: Dict[str, Any]) -> Tuple[bool, str]:
    """Is the versioned schema snapshot MANDATORY (fail-CLOSED) this run?

    Returns ``(required, source-label)``. Required when the operator/CI
    passes ``--require-snapshot`` OR a CI environment is detected: GitHub
    Actions always exports ``GITHUB_ACTIONS=true`` and generic CI systems
    export ``CI=true``. In any of those contexts a missing / unreadable /
    unrecognized snapshot is a fail-CLOSED violation (M3/C7): the gate must
    not pass after losing its versioned authority. Dev-local (no flag, no
    CI env) keeps the WARN-and-skip convenience.
    """
    if opts.get("require_snapshot"):
        return True, "--require-snapshot"
    if _env_truthy(os.environ.get("GITHUB_ACTIONS")):
        return True, "CI ($GITHUB_ACTIONS)"
    if _env_truthy(os.environ.get("CI")):
        return True, "CI ($CI)"
    return False, ""


def _find_repo_root(start: Path) -> Optional[Path]:
    """Walk up from ``start`` to the real repo root.

    Anchored on ``.git`` FIRST (the test_fingerprint_parity precedent):
    a staged pack under ``.claude/plans/PLAN-163/staged/main-pack/`` may
    itself carry a staged ``.claude/settings.json`` copy, so a
    settings.json-anchored walk would wrongly stop inside the pack. The
    real repo root is the first ancestor carrying ``.git``; the
    settings.json-anchored walk is only the fallback for non-git installs.
    """
    for cand in [start, *start.parents]:
        if (cand / ".git").exists() and (cand / ".claude" / "settings.json").is_file():
            return cand
    for cand in [start, *start.parents]:
        if (cand / ".claude" / "settings.json").is_file():
            return cand
    return None


# ---------------------------------------------------------------------------
# (a) Wired-hook derivation — RUNTIME parse of settings.json
# ---------------------------------------------------------------------------

def _load_registrations(settings_path: Path) -> Tuple[List[Dict[str, Any]], List[str]]:
    """Return ([registration...], [non-shim command notes]).

    Registration: {event, matcher, script, timeout}.
    """
    raw = json.loads(settings_path.read_text(encoding="utf-8"))
    regs: List[Dict[str, Any]] = []
    non_shim: List[str] = []
    hooks_obj = raw.get("hooks", {})
    if not isinstance(hooks_obj, dict):
        return regs, non_shim
    for event, groups in hooks_obj.items():
        if not isinstance(groups, list):
            continue
        for group in groups:
            if not isinstance(group, dict):
                continue
            matcher = group.get("matcher", "")
            for h in group.get("hooks", []) or []:
                if not isinstance(h, dict):
                    continue
                cmd = h.get("command", "")
                m = _SHIM_RE.search(cmd)
                if not m:
                    non_shim.append("%s [%s]: %s" % (event, matcher, cmd[:80]))
                    continue
                regs.append(
                    {
                        "event": event,
                        "matcher": matcher if isinstance(matcher, str) else "",
                        "script": m.group(1),
                        "timeout": h.get("timeout", 10),
                    }
                )
    return regs, non_shim


# ---------------------------------------------------------------------------
# (e) Static check
# ---------------------------------------------------------------------------

def _const_nonzero_int(node: ast.AST) -> bool:
    return (
        isinstance(node, ast.Constant)
        and isinstance(node.value, int)
        and not isinstance(node.value, bool)
        and node.value != 0
    )


def _refs_sys_argv(node: ast.AST) -> bool:
    for sub in ast.walk(node):
        if (
            isinstance(sub, ast.Attribute)
            and sub.attr == "argv"
            and isinstance(sub.value, ast.Name)
            and sub.value.id == "sys"
        ):
            return True
    return False


def _argv_gated_cli_functions(tree: ast.Module) -> set:
    """Names of functions ONLY reachable via an argv-gated CLI branch.

    The shim invokes wired hooks with NO extra argv, so a function called
    exclusively inside ``if __name__ == "__main__":`` under an ``if``
    testing ``sys.argv`` (the ``--selftest`` pattern, e.g.
    ``turbo_sessionstart.py``) is unreachable in hook mode. Constant
    nonzero exits inside such functions are downgraded to warnings.
    A name also called anywhere OUTSIDE those gated bodies loses the
    exemption.
    """
    gated: set = set()
    for node in tree.body:
        if not isinstance(node, ast.If):
            continue
        t = node.test
        is_main_guard = (
            isinstance(t, ast.Compare)
            and isinstance(t.left, ast.Name)
            and t.left.id == "__name__"
        )
        if not is_main_guard:
            continue
        for stmt in node.body:
            if isinstance(stmt, ast.If) and _refs_sys_argv(stmt.test):
                for sub in ast.walk(stmt):
                    if isinstance(sub, ast.Call) and isinstance(sub.func, ast.Name):
                        gated.add(sub.func.id)
        # Drop names also called outside the gated bodies (approximate:
        # any call in a FunctionDef or elsewhere at module level).
    if gated:
        gated_calls_elsewhere: set = set()
        for node in ast.walk(tree):
            if isinstance(node, ast.FunctionDef):
                for sub in ast.walk(node):
                    if (
                        isinstance(sub, ast.Call)
                        and isinstance(sub.func, ast.Name)
                        and sub.func.id in gated
                    ):
                        gated_calls_elsewhere.add(sub.func.id)
        gated -= gated_calls_elsewhere
    return gated


def _static_check(path: Path) -> Tuple[List[str], List[str]]:
    """Return (static violations, static warnings) for one hook file."""
    violations: List[str] = []
    warnings: List[str] = []
    try:
        tree = ast.parse(path.read_text(encoding="utf-8"))
    except Exception as exc:  # unparseable hook source is itself a finding
        return (
            ["static: source failed to parse (%s: %s)" % (type(exc).__name__, exc)],
            [],
        )

    cli_only = _argv_gated_cli_functions(tree)
    # Map line -> enclosing argv-gated CLI function (exempt region).
    exempt_ranges: List[Tuple[int, int, str]] = []
    for node in ast.walk(tree):
        if isinstance(node, ast.FunctionDef) and node.name in cli_only:
            end = getattr(node, "end_lineno", node.lineno)
            exempt_ranges.append((node.lineno, end, node.name))

    def _exempt(lineno: int) -> Optional[str]:
        for lo, hi, name in exempt_ranges:
            if lo <= lineno <= hi:
                return name
        return None

    for node in ast.walk(tree):
        if isinstance(node, ast.Import):
            for alias in node.names:
                if alias.name == "argparse" or alias.name.startswith("argparse."):
                    violations.append(
                        "static: `import argparse` at line %d — argparse exits 2 on "
                        "bad argv, which BLOCKS under CC >= 2.1.214" % node.lineno
                    )
        elif isinstance(node, ast.ImportFrom):
            if (node.module or "").split(".")[0] == "argparse":
                violations.append(
                    "static: `from argparse import ...` at line %d" % node.lineno
                )
        elif isinstance(node, ast.Call):
            fn = node.func
            target = None
            if isinstance(fn, ast.Attribute) and isinstance(fn.value, ast.Name):
                dotted = "%s.%s" % (fn.value.id, fn.attr)
                if dotted in ("sys.exit", "os._exit"):
                    target = dotted
            elif isinstance(fn, ast.Name) and fn.id in ("exit", "quit"):
                target = fn.id
            if target and node.args and _const_nonzero_int(node.args[0]):
                fn_name = _exempt(node.lineno)
                msg = (
                    "static: %s(%r) at line %d — constant nonzero exit reaches the "
                    "harness unaltered through the exec shim"
                    % (target, node.args[0].value, node.lineno)  # type: ignore[attr-defined]
                )
                if fn_name:
                    warnings.append(
                        msg
                        + " [EXEMPT: inside argv-gated CLI-only function %s()]" % fn_name
                    )
                else:
                    violations.append(msg)
        elif isinstance(node, ast.Raise):
            exc = node.exc
            if (
                isinstance(exc, ast.Call)
                and isinstance(exc.func, ast.Name)
                and exc.func.id == "SystemExit"
                and exc.args
                and _const_nonzero_int(exc.args[0])
            ):
                fn_name = _exempt(node.lineno)
                msg = "static: `raise SystemExit(%r)` at line %d" % (
                    exc.args[0].value,  # type: ignore[attr-defined]
                    node.lineno,
                )
                if fn_name:
                    warnings.append(
                        msg
                        + " [EXEMPT: inside argv-gated CLI-only function %s()]" % fn_name
                    )
                else:
                    violations.append(msg)
    return violations, warnings


# ---------------------------------------------------------------------------
# Fixture generation from the matcher (task item 2: no committed corpus for
# this shape exists under .claude/hooks/tests/fixtures/ — the harness-config
# replay fixtures are PLANTED VIOLATIONS, the opposite of the benign inputs
# needed here — so minimal per-event payloads are derived from settings.json
# matchers at runtime).
# ---------------------------------------------------------------------------

_LIFECYCLE_EVENTS = {
    "SessionStart",
    "SessionEnd",
    "Stop",
    "SubagentStop",
    "SubagentStart",
    "PreCompact",
    "PostCompact",
    "ConfigChange",
    "Setup",
}


def _first_tool_of(matcher: str) -> str:
    if not matcher:
        return "Bash"
    return matcher.split("|")[0].strip() or "Bash"


def _tool_payload(tool: str, project_dir: str) -> Tuple[str, Dict[str, Any]]:
    """Map a matcher tool token to (tool_name, benign tool_input)."""
    if tool == "Agent" or tool == "Task":
        # Deliberately UN-named spawn: check_agent_spawn only gates NAMED
        # agent spawns, so this payload is benign on the sane path too.
        return "Agent", {"prompt": "benign oracle fixture — no named agent"}
    if tool == "Bash":
        return "Bash", {"command": "true"}
    if tool in ("Edit", "Write", "MultiEdit"):
        return "Edit", {
            "file_path": os.path.join(project_dir, "ORACLE-BENIGN.md"),
            "old_string": "a",
            "new_string": "b",
        }
    if tool == "Read":
        return "Read", {"file_path": os.path.join(project_dir, "ORACLE-BENIGN.md")}
    if tool in ("WebFetch", "WebSearch"):
        return "WebFetch", {"url": "https://example.com/"}
    if tool.startswith("mcp__"):
        # A literal mcp matcher (mcp__codex__codex) is used verbatim; the
        # generic pattern mcp__.* gets a neutral placeholder name.
        name = tool if "*" not in tool and "." not in tool else "mcp__example__tool"
        return name, {"prompt": "benign oracle fixture"}
    # Glob-ish or unknown token: neutral Bash.
    return "Bash", {"command": "true"}


def _payload_for(event: str, matcher: str, project_dir: str) -> Dict[str, Any]:
    base: Dict[str, Any] = {
        "hook_event_name": event,
        "session_id": "hook-stdout-schema-oracle",
        "cwd": project_dir,
    }
    if event in _LIFECYCLE_EVENTS:
        if event == "Setup":
            base["trigger"] = matcher or "init"
        if event == "PreCompact":
            base["trigger"] = "manual"
        return base
    if event == "UserPromptSubmit":
        base["prompt"] = "hello from the hook-stdout-schema oracle"
        return base
    tool_name, tool_input = _tool_payload(_first_tool_of(matcher), project_dir)
    base["tool_name"] = tool_name
    base["tool_input"] = tool_input
    if event in ("PostToolUse", "PostToolUseFailure"):
        base["tool_response"] = {"stdout": "ok", "stderr": ""}
    if event == "PostToolUseFailure":
        base["error"] = "synthetic tool failure (oracle fixture)"
    return base


# ---------------------------------------------------------------------------
# Snapshot loading (T2.2 slot)
# ---------------------------------------------------------------------------

def _load_snapshot(path: Path) -> Tuple[Optional[Dict[str, Any]], Optional[str]]:
    """Return (snapshot-index, warning). snapshot-index:
    {"global": set|None, "events": {event: set}}."""
    if not path.is_file():
        return None, "schema snapshot absent at %s — snapshot validation SKIPPED (built-in structural rules still apply)" % path
    try:
        raw = json.loads(path.read_text(encoding="utf-8"))
    except Exception as exc:
        return None, "schema snapshot unreadable (%s: %s) — snapshot validation SKIPPED" % (type(exc).__name__, exc)
    if not isinstance(raw, dict):
        return None, "schema snapshot is not a JSON object — snapshot validation SKIPPED"
    idx: Dict[str, Any] = {"global": None, "events": {}}
    if isinstance(raw.get("allowed_top_level_keys"), list):
        idx["global"] = {k for k in raw["allowed_top_level_keys"] if isinstance(k, str)}
    if isinstance(raw.get("properties"), dict):
        idx["global"] = set(raw["properties"].keys()) | (idx["global"] or set())
    if isinstance(raw.get("common_output_schema"), dict):
        # S284 schema-extract probe shape (PLAN-163 T2.2 artifact): the
        # dict's keys ARE the allowed common-output top-level keys. The
        # "async_variant" entry is a meta-description of the async union
        # ({async: true, asyncTimeout?}) — expand it to those two keys.
        keys = set(raw["common_output_schema"].keys())
        if "async_variant" in keys:
            keys.discard("async_variant")
            keys.update({"async", "asyncTimeout"})
        idx["global"] = keys | (idx["global"] or set())
    events = raw.get("events")
    if isinstance(events, dict):
        for ev, spec in events.items():
            if isinstance(spec, dict) and isinstance(spec.get("allowed_top_level_keys"), list):
                idx["events"][ev] = {
                    k for k in spec["allowed_top_level_keys"] if isinstance(k, str)
                }
            elif isinstance(spec, dict) and isinstance(spec.get("properties"), dict):
                idx["events"][ev] = set(spec["properties"].keys())
    if idx["global"] is None and not idx["events"]:
        return None, "schema snapshot shape unrecognized — snapshot validation SKIPPED (see module docstring for accepted shapes)"
    # Recognized shape but ZERO real validation keys (empty
    # ``allowed_top_level_keys`` / empty ``properties`` / empty
    # ``common_output_schema`` / only-empty per-event key sets). At
    # validation time the ``if allowed:`` guard would treat the empty set as
    # falsy and SKIP every versioned check — a vacuous pass. A snapshot with
    # no keys carries no versioned authority, so it is UNUSABLE: return None
    # (like an absent/unrecognized snapshot) so ``--require-snapshot``/CI
    # fails CLOSED via ``snapshot is None`` below, while dev-local keeps the
    # WARN-and-skip convenience. The valid non-empty path is untouched.
    if not idx["global"] and not any(idx["events"].values()):
        return None, (
            "schema snapshot recognized but carries NO validation keys "
            "(empty allowed-key set) — a versioned snapshot must define at "
            "least one allowed top-level key; snapshot validation SKIPPED"
        )
    # FXζ (C7): MIXED snapshot — recognized per-event key set(s) that are
    # EMPTY alongside non-empty sibling(s) (or a non-empty global). The
    # non-empty siblings keep it OUT of the wholly-empty gate above, so it
    # LOADS; but at validation time each empty event resolves
    # ``snapshot["events"][ev] or snapshot["global"]`` to a falsy/None
    # ``allowed`` and the ``if allowed:`` guard SKIPS it — a VACUOUS pass for
    # that event alone. Record the offenders on the index (always, so main()
    # can read them uniformly) and, when present, warn naming them. main()
    # escalates to fail-CLOSED under --require-snapshot/CI — a versioned gate
    # that silently skips a DECLARED event has lost its authority there — but
    # does NOT discard the snapshot: dev-local keeps warn-and-validate (the
    # non-empty siblings still validate; only the empty event is skipped).
    empty_events = sorted(ev for ev, keys in idx["events"].items() if not keys)
    idx["empty_events"] = empty_events
    if empty_events:
        return idx, (
            "schema snapshot has recognized event(s) with an EMPTY "
            "allowed-key set: %s — each validates VACUOUSLY (its versioned "
            "check is SKIPPED); under --require-snapshot/CI this is "
            "fail-CLOSED" % ", ".join(empty_events)
        )
    return idx, None


# Provenance of the committed default snapshot (PLAN-163 T2.2 / CF-5 / M3-C7):
# staged verbatim from the S284 schema-extract probe artifact.
_SNAPSHOT_PROBE_PROVENANCE = ".claude/plans/PLAN-163/probes/hook-schema-2.1.220.json"
_SNAPSHOT_EXPECTED_SHA256 = (
    "acd9b05f8bf1d789c743f390a5218ababfe2c733ff13cdd49e78785c479abcee"
)


def _snapshot_fail_closed_message(
    snapshot_path: Path, source: str, reason: Optional[str]
) -> str:
    """Actionable fail-CLOSED message (M3/C7): why + how to regenerate.

    The regeneration recipe restores the committed 2.1.220 artifact
    byte-for-byte; if the caller pointed ``--schema-snapshot`` at a
    different version file, the ``_meta.recipe`` re-extraction path in the
    docstring is the general fallback.
    """
    detail = reason or ("schema snapshot unavailable at %s" % snapshot_path)
    return (
        "check-hook-stdout-schema: FAIL-CLOSED — the versioned Claude Code "
        "hook-output schema snapshot is REQUIRED here (%s) but is unavailable "
        "or unusable.\n"
        "  cause:    %s\n"
        "  expected: %s\n"
        "  regenerate (restore the committed artifact, byte-for-byte):\n"
        "      cp %s %s\n"
        "      # expected sha256: %s\n"
        "  or re-extract from the Claude Code binary per the recipe in that "
        "artifact's _meta.recipe (see this module's docstring).\n"
        "  (dev-local runs — no CI env, no --require-snapshot — downgrade this "
        "to a warning.)"
        % (
            source,
            detail,
            snapshot_path,
            _SNAPSHOT_PROBE_PROVENANCE,
            snapshot_path,
            _SNAPSHOT_EXPECTED_SHA256,
        )
    )


# ---------------------------------------------------------------------------
# (d) stdout schema validation
# ---------------------------------------------------------------------------

def _decision_of(obj: Dict[str, Any]) -> str:
    d = obj.get("decision")
    if isinstance(d, str):
        return d
    hso = obj.get("hookSpecificOutput")
    if isinstance(hso, dict):
        pd = hso.get("permissionDecision")
        if isinstance(pd, str):
            return pd
    pd2 = obj.get("permissionDecision")
    if isinstance(pd2, str):
        return pd2
    return ""


def _validate_stdout(
    stdout: str,
    event: str,
    snapshot: Optional[Dict[str, Any]],
) -> Tuple[Optional[Dict[str, Any]], List[str], List[str]]:
    """Return (parsed-or-None, violations, warnings)."""
    violations: List[str] = []
    warnings: List[str] = []
    text = stdout.strip()
    if not text:
        return None, violations, warnings
    try:
        obj = json.loads(text)
    except Exception:
        violations.append(
            "stdout is non-empty but not JSON (the argparse-usage-on-stdout "
            "class): %r" % text[:120]
        )
        return None, violations, warnings
    if not isinstance(obj, dict):
        violations.append("stdout JSON is not an object: %r" % text[:120])
        return None, violations, warnings
    d = obj.get("decision")
    if d is not None and not isinstance(d, str):
        violations.append("`decision` is present but not a string: %r" % (d,))
    unknown_builtin = sorted(set(obj.keys()) - _BUILTIN_KNOWN_TOP_LEVEL_KEYS)
    if unknown_builtin:
        warnings.append(
            "top-level key(s) outside the built-in known set: %s" % ", ".join(unknown_builtin)
        )
    if snapshot is not None:
        allowed = snapshot["events"].get(event) or snapshot["global"]
        if allowed:
            bad = sorted(set(obj.keys()) - allowed)
            if bad:
                violations.append(
                    "top-level key(s) outside the versioned schema snapshot for %s: %s"
                    % (event, ", ".join(bad))
                )
    return obj, violations, warnings


# ---------------------------------------------------------------------------
# Behavioral runners
# ---------------------------------------------------------------------------

def _run_hook(
    script_path: Path,
    payload: Dict[str, Any],
    env: Dict[str, str],
    timeout_s: int,
) -> Tuple[int, str, str, Optional[str]]:
    """Run one hook subprocess. Returns (rc, stdout, stderr, error)."""
    try:
        proc = subprocess.run(
            [sys.executable, str(script_path)],
            input=json.dumps(payload),
            capture_output=True,
            text=True,
            env=env,
            timeout=timeout_s,
        )
        return proc.returncode, proc.stdout, proc.stderr, None
    except subprocess.TimeoutExpired:
        return -1, "", "", "timed out after %ds" % timeout_s
    except Exception as exc:  # oracle infra — surfaced, never swallowed
        return -1, "", "", "%s: %s" % (type(exc).__name__, exc)


def _clean_env(home: Path, project_dir: str) -> Dict[str, str]:
    """TestEnvContext-style explicit env for a hook subprocess.

    Nothing from the operator's live env leaks in except PATH (interpreter
    + coreutils resolution). The real $HOME is never visible.
    """
    return {
        "PATH": os.environ.get("PATH", "/usr/bin:/bin"),
        "HOME": str(home),
        "TMPDIR": str(home / "tmp"),
        "CLAUDE_PROJECT_DIR": project_dir,
        "CEO_HOOK_ADAPTER": "claude",
        "CEO_AUDIT_SYNC_MODE": "1",
        "LC_ALL": "C",
    }


def _timeout_for(reg_timeout: Any) -> int:
    try:
        t = int(reg_timeout)
    except Exception:
        t = 10
    return max(_TIMEOUT_FLOOR_S, min(t + 10, _TIMEOUT_CEIL_S))


# ---------------------------------------------------------------------------
# Main
# ---------------------------------------------------------------------------

def main(argv: List[str]) -> int:
    opts = _parse_args(argv)

    script_dir = Path(__file__).resolve().parent
    repo = Path(opts["repo"]).resolve() if opts["repo"] else _find_repo_root(script_dir)
    if repo is None:
        print(
            "check-hook-stdout-schema: could not locate a repo root carrying "
            ".claude/settings.json (pass --repo)",
            file=sys.stderr,
        )
        return 2
    settings_path = repo / ".claude" / "settings.json"
    hooks_dir = repo / ".claude" / "hooks"
    if not settings_path.is_file():
        print("check-hook-stdout-schema: %s not found" % settings_path, file=sys.stderr)
        return 2

    try:
        regs, non_shim = _load_registrations(settings_path)
    except Exception as exc:
        print(
            "check-hook-stdout-schema: settings.json unparseable (%s: %s)"
            % (type(exc).__name__, exc),
            file=sys.stderr,
        )
        return 2

    if opts["only"]:
        only = set(opts["only"])
        regs = [r for r in regs if r["script"] in only]
        if not regs:
            print(
                "check-hook-stdout-schema: --only matched no wired registration",
                file=sys.stderr,
            )
            return 2

    snapshot_path = (
        Path(opts["schema_snapshot"]).resolve()
        if opts["schema_snapshot"]
        else repo / _DEFAULT_SNAPSHOT_REL
    )
    snapshot, snap_warn = _load_snapshot(snapshot_path)

    # M3/C7: in CI (or under --require-snapshot) a missing / unreadable /
    # unrecognized snapshot is fail-CLOSED, never a silent warn-and-skip.
    # FXζ (C7): additionally, a snapshot that LOADED but carries recognized
    # event(s) with an EMPTY allowed-key set (a MIXED snapshot) is
    # fail-CLOSED under the same trigger — each such event would validate
    # vacuously. This is ADDITIVE to the ``snapshot is None`` case and does
    # NOT discard the snapshot: the non-empty events still validate below.
    require_snapshot, require_source = _require_snapshot_active(opts)
    snapshot_empty_events: List[str] = (
        snapshot.get("empty_events", []) if snapshot is not None else []
    )
    snapshot_fail_closed = require_snapshot and (
        snapshot is None or bool(snapshot_empty_events)
    )

    report: Dict[str, Any] = {
        "repo": str(repo),
        "snapshot": str(snapshot_path),
        "snapshot_active": snapshot is not None,
        "snapshot_required": require_snapshot,
        "snapshot_require_source": require_source,
        "snapshot_empty_events": snapshot_empty_events,
        "snapshot_fail_closed": snapshot_fail_closed,
        "registrations": len(regs),
        "non_shim_commands": non_shim,
        "hooks": {},
        "violations": 0,
        "warnings": [],
    }
    if snap_warn:
        report["warnings"].append(snap_warn)

    fail_closed_msg: Optional[str] = None
    if snapshot_fail_closed:
        fail_closed_msg = _snapshot_fail_closed_message(
            snapshot_path, require_source, snap_warn
        )
        report["snapshot_fail_closed_detail"] = fail_closed_msg
        # Always surface on stderr so CI logs carry the recipe even in
        # --json mode (stdout is reserved for the report there). This does
        # NOT short-circuit: the static + behavioral checks below still run.
        print(fail_closed_msg, file=sys.stderr)

    # Unique wired scripts (a script may be wired on several events).
    scripts = sorted({r["script"] for r in regs})

    # --- (e) static + argparse-CLI-wired guard --------------------------
    per_hook: Dict[str, Dict[str, Any]] = {
        s: {"static": [], "behavioral": [], "warnings": []} for s in scripts
    }
    for s in scripts:
        path = hooks_dir / s
        if not path.is_file():
            per_hook[s]["static"].append("wired script missing on disk: %s" % path)
            continue
        if s in _ARGPARSE_CLI_ALLOWLIST:
            per_hook[s]["static"].append(
                "argparse CLI %s is WIRED as a hook — it belongs to the operator/CI "
                "tier (exit!=0 contract) and must never route through the shim" % s
            )
            continue
        s_viols, s_warns = _static_check(path)
        per_hook[s]["static"].extend(s_viols)
        per_hook[s]["warnings"].extend(s_warns)

    # --- (b)+(c) behavioral ---------------------------------------------
    if not opts["skip_behavioral"]:
        tmp_root = Path(tempfile.mkdtemp(prefix="hook-stdout-oracle-"))
        try:
            broken_project = "/nonexistent-hook-oracle-%s" % uuid.uuid4().hex[:12]
            sane_project = tmp_root / "sane-project"
            sane_project.mkdir(parents=True)
            seen_pairs = set()
            for reg in regs:
                s = reg["script"]
                path = hooks_dir / s
                if not path.is_file():
                    continue
                pair = (s, reg["event"], reg["matcher"])
                if pair in seen_pairs:
                    continue
                seen_pairs.add(pair)
                timeout_s = _timeout_for(reg["timeout"])
                label = "%s @ %s[%s]" % (s, reg["event"], reg["matcher"] or "*")

                # (b) INFRA fixture: benign payload + broken env.
                home_b = tmp_root / ("home-b-%d" % len(seen_pairs))
                (home_b / "tmp").mkdir(parents=True)
                payload = _payload_for(reg["event"], reg["matcher"], broken_project)
                rc, out, _err, err = _run_hook(
                    path, payload, _clean_env(home_b, broken_project), timeout_s
                )
                if err is not None:
                    per_hook[s]["behavioral"].append("[infra] %s: %s" % (label, err))
                else:
                    if rc != 0:
                        per_hook[s]["behavioral"].append(
                            "[infra] %s: exit %d under a broken env (must fail-OPEN "
                            "with exit 0 — an accidental exit 2 BLOCKS under CC >= 2.1.214)"
                            % (label, rc)
                        )
                    obj, viols, warns = _validate_stdout(out, reg["event"], snapshot)
                    per_hook[s]["behavioral"].extend("[infra] %s: %s" % (label, v) for v in viols)
                    per_hook[s]["warnings"].extend("[infra] %s: %s" % (label, w) for w in warns)
                    if obj is not None and _decision_of(obj) in _DENY_DECISIONS:
                        per_hook[s]["behavioral"].append(
                            "[infra] %s: emitted a deny/block on an INFRASTRUCTURE "
                            "failure with a benign payload (must fail-OPEN)" % label
                        )

                # (c) SECURITY-MATCHER fixture: parse-failure payload + sane env.
                if s in _SECURITY_MATCHERS and reg["event"] == "PreToolUse":
                    home_c = tmp_root / ("home-c-%d" % len(seen_pairs))
                    (home_c / "tmp").mkdir(parents=True)
                    rc, out, _err, err = _run_hook(
                        path,
                        _SECURITY_MATCHERS[s],
                        _clean_env(home_c, str(sane_project)),
                        timeout_s,
                    )
                    if err is not None:
                        per_hook[s]["behavioral"].append("[input] %s: %s" % (label, err))
                    else:
                        if rc != 0:
                            per_hook[s]["behavioral"].append(
                                "[input] %s: exit %d on an input-parse failure "
                                "(the deny travels in the decision-JSON at exit 0; "
                                "the exit code must stay 0)" % (label, rc)
                            )
                        obj, viols, warns = _validate_stdout(out, reg["event"], snapshot)
                        per_hook[s]["behavioral"].extend(
                            "[input] %s: %s" % (label, v) for v in viols
                        )
                        per_hook[s]["warnings"].extend(
                            "[input] %s: %s" % (label, w) for w in warns
                        )
                        if obj is None or _decision_of(obj) not in _DENY_DECISIONS:
                            per_hook[s]["behavioral"].append(
                                "[input] %s: security matcher did NOT emit a "
                                "block/deny decision-JSON on unparseable input "
                                "(fail-CLOSED contract, PLAN-152 C4)" % label
                            )
        finally:
            shutil.rmtree(tmp_root, ignore_errors=True)

    # --- Report ----------------------------------------------------------
    total_violations = 0
    for s in scripts:
        entry = per_hook[s]
        n = len(entry["static"]) + len(entry["behavioral"])
        total_violations += n
        report["hooks"][s] = entry
        status = "OK" if n == 0 else "VIOLATION(%d)" % n
        if not opts["json"]:
            print("%-42s %s" % (s, status))
            for v in entry["static"] + entry["behavioral"]:
                print("    ! %s" % v)
            if opts["verbose"]:
                for w in entry["warnings"]:
                    print("    ~ warn: %s" % w)
    report["violations"] = total_violations

    if not opts["json"]:
        for w in report["warnings"]:
            print("~ %s" % w)
        if non_shim and opts["verbose"]:
            for n_ in non_shim:
                print("~ non-shim registration (out of scope): %s" % n_)
        if snapshot_fail_closed:
            snap_suffix = (
                " [snapshot REQUIRED but unavailable/unusable — FAIL-CLOSED]"
            )
        elif snapshot is not None:
            snap_suffix = ""
        else:
            snap_suffix = " [snapshot inactive]"
        print(
            "hook-stdout-schema: %d wired script(s), %d registration(s), "
            "%d violation(s)%s"
            % (
                len(scripts),
                len(regs),
                total_violations,
                snap_suffix,
            )
        )
    else:
        print(json.dumps(report, indent=2, sort_keys=True))

    return 1 if (total_violations or snapshot_fail_closed) else 0


if __name__ == "__main__":
    sys.exit(main(sys.argv[1:]))
