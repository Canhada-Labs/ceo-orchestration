"""Policy pre-processors — PLAN-014 Phase A.4.

Pure Python functions that enrich a raw Claude Code tool-call event dict
with ``_derived_*`` fields the declarative policy engine can evaluate.

This module is the "thin imperative shim" in front of the declarative
DSL. It does the work that is not expressible in the 14 predicate forms
of SPEC/v1/policy-dsl.schema.md §3.5:

- ``bash_safety_preprocess`` — shell tokenization via ``shlex``, credential
  scan via :mod:`_lib.credentials`, per-subcommand rule-match booleans.
- ``plan_edit_preprocess`` — plan-file scope check, frontmatter parse via
  :mod:`_lib.plan_frontmatter`, transition-graph legality, required-field
  presence checks.

Both preprocessors are **fail-safe**: any exception collapses derived
fields to "no match" defaults so the policy engine routes to its
``defaults.decision: allow`` path. The legacy .py hooks preserve their
own fail-open contract as a second line of defense (ADJ-014 dual-path).

Stdlib only per ADR-002. Byte-identity governance (ADJ-008) is enforced
via the paired ``.fixtures.jsonl`` files under ``.claude/policies/fixtures/``.
"""

from __future__ import annotations

import os
import re
import shlex
import sys
from pathlib import Path
from typing import Any, Dict, List

_HOOKS_DIR = Path(__file__).resolve().parent.parent
if str(_HOOKS_DIR) not in sys.path:
    sys.path.insert(0, str(_HOOKS_DIR))

from _lib import credentials as _credentials  # noqa: E402
from _lib import plan_frontmatter as _fm  # noqa: E402


# ---------------------------------------------------------------------------
# Bash-safety preprocessor
# ---------------------------------------------------------------------------

# Mirror of _SUBCOMMAND_SPLIT_RE in check_bash_safety.py (byte-identical).
_BASH_SUBCMD_SPLIT_RE = re.compile(r"\s*(?:&&|\|\||[;|])\s*")


def _split_subcommands(command: str) -> List[str]:
    if not command or not command.strip():
        return []
    parts = _BASH_SUBCMD_SPLIT_RE.split(command)
    return [p for p in (s.strip() for s in parts) if p]


def _tokenize(subcommand: str) -> List[str]:
    try:
        return shlex.split(subcommand)
    except ValueError:
        return []


# PLAN-019 P0-02 — privilege-escalation prefixes the matchers normalize
# away so that ``sudo rm -rf /`` / ``/bin/rm …`` / ``\rm …`` are not
# silently allowed. Mirrors check_bash_safety._PRIVILEGE_PREFIXES.
_PRIVILEGE_PREFIXES = frozenset({"sudo", "doas", "nocorrect"})


def _normalize_command_tokens(tokens: List[str]) -> List[str]:
    """Mirror of ``check_bash_safety._normalize_command_tokens`` (ADJ-014
    dual-path invariant): strip privilege prefixes + basename the first
    token. Kept byte-equivalent to the ``.py`` hook implementation.

    See that function's docstring for semantics + examples.
    """
    if not tokens:
        return tokens
    working = list(tokens)
    while working and working[0] in _PRIVILEGE_PREFIXES:
        working.pop(0)
        while working and working[0].startswith("-"):
            flag = working.pop(0)
            if (flag in ("-u", "--user")
                    and working
                    and not working[0].startswith("-")):
                working.pop(0)
    if not working:
        return working
    first = working[0]
    if first.startswith("\\"):
        first = first.lstrip("\\")
    basename = Path(first).name if first else first
    working[0] = basename or first
    return working


def _tokens_match_rm_rf(tokens: List[str]) -> bool:
    """PLAN-019 P0-01 + P0-02: long-option parsing + prefix normalization.

    Kept byte-equivalent to ``check_bash_safety._check_rm_rf``
    (ADJ-014 dual-path invariant).
    """
    tokens = _normalize_command_tokens(tokens)
    if not tokens or tokens[0] != "rm":
        return False
    has_r = False
    has_f = False
    for t in tokens[1:]:
        if not t.startswith("-"):
            continue
        if t.startswith("--"):
            # Defensive: ``--recursive=VALUE`` is non-standard rm syntax;
            # treat the equals-form on destructive flags as implying both
            # ``-r`` and ``-f`` (ADJ-014 dual-path mirror of .py hook).
            has_eq = "=" in t
            name = t[2:].split("=", 1)[0].lower()
            if name in ("recursive", "r"):
                has_r = True
                if has_eq:
                    has_f = True
            elif name == "force":
                has_f = True
                if has_eq:
                    has_r = True
            if has_r and has_f:
                return True
            continue
        body = t[1:]
        lowered = body.lower()
        if "r" in lowered:
            has_r = True
        if "f" in lowered:
            has_f = True
        if has_r and has_f:
            return True
    return has_r and has_f


def _tokens_match_git_reset_hard(tokens: List[str]) -> bool:
    """PLAN-019 P0-02: normalize before matching ``git reset --hard``."""
    tokens = _normalize_command_tokens(tokens)
    return (
        len(tokens) >= 3
        and tokens[0] == "git"
        and tokens[1] == "reset"
        and tokens[2] == "--hard"
    )


def _tokens_match_git_push_force(tokens: List[str]) -> bool:
    """PLAN-019 P0-02: normalize before matching ``git push --force`` / ``-f``."""
    tokens = _normalize_command_tokens(tokens)
    if len(tokens) < 3 or tokens[0] != "git" or tokens[1] != "push":
        return False
    for t in tokens[2:]:
        if t == "--force" or t == "-f":
            return True
    return False


def _bash_defaults() -> Dict[str, Any]:
    return {
        "command": "",
        "credential_leak_provider": "",
        "credential_leak_redacted": "",
        "subcommands": [],
        "tokens_per_subcommand": [],
        "matched_rm_rf": False,
        "matched_git_reset_hard": False,
        "matched_git_push_force": False,
    }


def bash_safety_preprocess(event: Dict[str, Any]) -> Dict[str, Any]:
    """Enrich ``event`` with ``_derived_bash`` fields.

    Fail-safe: any exception collapses derived fields to "no match"
    defaults so the policy engine falls through to ``defaults.decision``.
    """
    enriched = dict(event) if isinstance(event, dict) else {}
    derived = _bash_defaults()
    try:
        tool_input = event.get("tool_input") if isinstance(event, dict) else None
        command = ""
        if isinstance(tool_input, dict):
            command = str(tool_input.get("command") or "")
        derived["command"] = command

        # Credential scan (runs on raw command BEFORE tokenization).
        if command:
            try:
                for provider, match, _off in _credentials.detect_keys(command):
                    if _credentials.is_likely_real_key(match, command):
                        derived["credential_leak_provider"] = provider
                        derived["credential_leak_redacted"] = (
                            _credentials.redacted_display(provider, match)
                        )
                        break
            except Exception:
                # Fail-CLOSED on credential scan failure (match the .py hook).
                derived["credential_leak_provider"] = "unknown"
                derived["credential_leak_redacted"] = "unknown:****"

        subcommands = _split_subcommands(command)
        derived["subcommands"] = subcommands

        tokens_per: List[List[str]] = []
        matched_rm_rf = False
        matched_reset = False
        matched_push = False
        for sub in subcommands:
            tokens = _tokenize(sub)
            tokens_per.append(tokens)
            if not tokens:
                continue
            if _tokens_match_rm_rf(tokens):
                matched_rm_rf = True
            if _tokens_match_git_reset_hard(tokens):
                matched_reset = True
            if _tokens_match_git_push_force(tokens):
                matched_push = True
        derived["tokens_per_subcommand"] = tokens_per
        derived["matched_rm_rf"] = matched_rm_rf
        derived["matched_git_reset_hard"] = matched_reset
        derived["matched_git_push_force"] = matched_push
    except Exception:
        derived = _bash_defaults()
    enriched["_derived_bash"] = derived
    return enriched


# ---------------------------------------------------------------------------
# Plan-edit preprocessor
# ---------------------------------------------------------------------------

_PLAN_PATH_RE = re.compile(r"\.claude/plans/PLAN-\d{3}-[a-z0-9-]+\.md$")
_PLAN_ID_RE = re.compile(r"(PLAN-\d{3})-[a-z0-9-]+\.md$")

_LEGAL_STATUSES = frozenset({"draft", "reviewed", "executing", "done", "abandoned", "refused"})

_ALLOWED_TRANSITIONS: Dict[str, frozenset] = {
    "draft": frozenset({"draft", "reviewed", "abandoned", "refused"}),
    "reviewed": frozenset({"reviewed", "executing", "abandoned", "refused"}),
    "executing": frozenset({"executing", "done", "abandoned", "refused"}),
    # done is reopen-able when the plan body declares a `reopen_via:`
    # ADR reference (audit-v2 ADR-092 honest-deferral framework).
    "done": frozenset({"done", "executing"}),
    "abandoned": frozenset({"abandoned"}),  # terminal
    "refused": frozenset({"refused"}),  # terminal — must cite refused_adr
}


def _plan_defaults() -> Dict[str, Any]:
    return {
        "is_plan_file": False,
        "plan_id": "",
        "old_status": "",
        "new_status": "",
        "status_changed": False,
        "transition_legal": True,
        "new_status_legal": True,
        "reviewed_at_present": False,
        "completed_at_present": False,
        "related_commits_nonempty": False,
        "abandonment_reason_present": False,
        "refused_adr_present": False,
        "refused_adr_well_formed": False,
        # Session 76 audit-v3 (DIM-11) — ADR-092 enforcement fields.
        "refused_at_present": False,
        "reopen_via_present": False,
        "reopen_via_well_formed": False,
        "reopen_trigger_present": False,
        "reopen_criteria_section_present": False,
        "transition_reason_key": "",
    }


def _apply_edit(current: str, old_string: str, new_string: str,
                replace_all: bool) -> str:
    if not current or old_string not in current:
        return current
    if replace_all:
        return current.replace(old_string, new_string)
    return current.replace(old_string, new_string, 1)


def _read_plan_file(file_path: str) -> str:
    """Default file reader — empty string on any error (matches .py hook)."""
    try:
        return Path(file_path).read_text(encoding="utf-8")
    except (OSError, UnicodeDecodeError):
        return ""


def plan_edit_preprocess(event: Dict[str, Any],
                         *, read_current=None) -> Dict[str, Any]:
    """Enrich ``event`` with ``_derived_plan`` fields.

    Optional ``read_current`` param lets tests inject a fake file reader.
    When ``None``, reads the real filesystem (matches .py hook behavior).
    """
    enriched = dict(event) if isinstance(event, dict) else {}
    derived = _plan_defaults()
    reader = read_current if read_current is not None else _read_plan_file
    try:
        tool_input = event.get("tool_input") if isinstance(event, dict) else None
        if not isinstance(tool_input, dict):
            enriched["_derived_plan"] = derived
            return enriched
        file_path = str(tool_input.get("file_path") or "")
        old_string = str(tool_input.get("old_string") or "")
        new_string = str(tool_input.get("new_string") or "")
        replace_all = bool(tool_input.get("replace_all") or False)

        # Scope guard.
        if not file_path or not _PLAN_PATH_RE.search(file_path):
            enriched["_derived_plan"] = derived
            return enriched
        derived["is_plan_file"] = True
        m = _PLAN_ID_RE.search(file_path)
        derived["plan_id"] = m.group(1) if m else ""

        current = reader(file_path)
        if not current:
            enriched["_derived_plan"] = derived
            return enriched

        new_content = _apply_edit(current, old_string, new_string, replace_all)
        if new_content == current:
            enriched["_derived_plan"] = derived
            return enriched

        old_fm = _fm.parse_frontmatter(current)
        new_fm = _fm.parse_frontmatter(new_content)

        old_status = str(old_fm.get("status", "")).strip()
        new_status = str(new_fm.get("status", "")).strip()
        derived["old_status"] = old_status
        derived["new_status"] = new_status
        derived["status_changed"] = bool(
            old_status and new_status and old_status != new_status
        )

        # Legality checks
        new_status_legal = new_status in _LEGAL_STATUSES if new_status else True
        derived["new_status_legal"] = new_status_legal

        if old_status and old_status in _LEGAL_STATUSES and new_status_legal:
            allowed = _ALLOWED_TRANSITIONS.get(old_status, frozenset())
            derived["transition_legal"] = (new_status in allowed) or (
                old_status == new_status
            )
        else:
            # Corrupt existing status or new plan without old status → don't
            # block the transition graph (mirrors .py hook _check_transition).
            derived["transition_legal"] = True

        # Required-field detectors
        reviewed_at = new_fm.get("reviewed_at")
        derived["reviewed_at_present"] = bool(reviewed_at)
        completed_at = new_fm.get("completed_at")
        derived["completed_at_present"] = bool(completed_at)
        rc = new_fm.get("related_commits")
        derived["related_commits_nonempty"] = bool(
            rc and (not isinstance(rc, list) or len(rc) > 0)
        )
        derived["abandonment_reason_present"] = _fm.has_abandonment_reason(
            new_content
        )
        # Session 75 F7: refused_adr field required when status=refused.
        # Mirrors check_plan_edit.py _check_required_fields refused branch.
        import re as _re_refused
        refused_adr = new_fm.get("refused_adr")
        derived["refused_adr_present"] = bool(refused_adr)
        if refused_adr:
            ra = str(refused_adr).strip()
            derived["refused_adr_well_formed"] = bool(
                _re_refused.match(r"^ADR-\d{3,4}\b", ra)
            )
        else:
            derived["refused_adr_well_formed"] = False

        # Session 76 audit-v3 (DIM-11) — ADR-092 derived fields.
        derived["refused_at_present"] = bool(new_fm.get("refused_at"))
        reopen_via = new_fm.get("reopen_via")
        derived["reopen_via_present"] = bool(reopen_via)
        if reopen_via:
            rv = str(reopen_via).strip()
            import re as _re_reopen
            derived["reopen_via_well_formed"] = bool(
                _re_reopen.match(r"^ADR-\d{3,4}\b", rv)
            )
        else:
            derived["reopen_via_well_formed"] = False
        derived["reopen_trigger_present"] = bool(new_fm.get("reopen_trigger"))
        derived["reopen_criteria_section_present"] = (
            "## Reopen criteria" in new_content
        )

        # Resolve transition_reason_key (advisory — mirrors policy rule order).
        if derived["status_changed"]:
            if not new_status_legal:
                derived["transition_reason_key"] = "illegal_status_value"
            elif not derived["transition_legal"]:
                derived["transition_reason_key"] = "illegal_transition"
            elif new_status == "reviewed" and not derived["reviewed_at_present"]:
                derived["transition_reason_key"] = "missing_reviewed_at"
            elif new_status == "done" and not derived["completed_at_present"]:
                derived["transition_reason_key"] = "missing_completed_at"
            elif (new_status == "done"
                  and derived["completed_at_present"]
                  and not derived["related_commits_nonempty"]):
                derived["transition_reason_key"] = "missing_related_commits"
            elif (new_status == "abandoned"
                  and not derived["abandonment_reason_present"]):
                derived["transition_reason_key"] = "missing_abandonment_reason"
            elif (new_status == "refused"
                  and not derived["refused_adr_present"]):
                derived["transition_reason_key"] = "missing_refused_adr"
            elif (new_status == "refused"
                  and derived["refused_adr_present"]
                  and not derived["refused_adr_well_formed"]):
                derived["transition_reason_key"] = "malformed_refused_adr"
            # Session 76 audit-v3 (DIM-11) — ADR-092 reason chain extensions.
            elif (new_status == "refused"
                  and derived["refused_adr_present"]
                  and derived["refused_adr_well_formed"]
                  and not derived["refused_at_present"]):
                derived["transition_reason_key"] = "missing_refused_at"
            elif (new_status == "executing"
                  and old_status == "done"
                  and not derived["reopen_via_present"]):
                derived["transition_reason_key"] = "missing_reopen_via"
            elif (new_status == "executing"
                  and old_status == "done"
                  and derived["reopen_via_present"]
                  and not derived["reopen_via_well_formed"]):
                derived["transition_reason_key"] = "malformed_reopen_via"
            elif (new_status == "executing"
                  and old_status == "done"
                  and derived["reopen_via_present"]
                  and derived["reopen_via_well_formed"]
                  and not derived["reopen_trigger_present"]):
                derived["transition_reason_key"] = "missing_reopen_trigger"
            elif (new_status == "executing"
                  and old_status == "done"
                  and derived["reopen_via_present"]
                  and derived["reopen_via_well_formed"]
                  and derived["reopen_trigger_present"]
                  and not derived["reopen_criteria_section_present"]):
                derived["transition_reason_key"] = "missing_reopen_criteria"
    except Exception:
        derived = _plan_defaults()
    enriched["_derived_plan"] = derived
    return enriched


__all__ = [
    "bash_safety_preprocess",
    "plan_edit_preprocess",
]
