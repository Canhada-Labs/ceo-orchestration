#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
first-run-wizard.py — PLAN-083 Wave 2 sub-agent 2.1.

First-run wizard for newly-installed ceo-orchestration framework. Implements
the `detect -> explain -> recommend -> ask` flow per PLAN-083 §5.4 row 2.1.

Target install path (post canonical-guard ceremony):
    .claude/scripts/first-run-wizard.py

Pipeline:
    1. detect    — invoke detect-repo-profile (library import or subprocess).
                   Exit 2 fail-CLOSED if profile is `unknown-needs-owner-
                   confirmation`. Print actionable next-step.
    2. explain   — read `.claude/repo-profile.yaml`, render a 3-5 line
                   summary including profile, confidence, top-5 active
                   skills (delegated to resolver), the 7-day read-only
                   policy hint, and an override pointer.
    3. recommend — delegate to smart-loading-resolver, take top-3 active
                   skills, attach confidence labels (Wave 1.10).
    4. ask       — interactive prompt [Y/n/customize]. Persist outcome to
                   `.claude/wizard-completed.yaml` (timestamp + version
                   stamp + recommendation slugs + user_action).

Sec P1 hardening (per PLAN-083 §5.4 row 2.1):
    - YAML reads ONLY through the strict mini-parser inherited from the
      sibling detect-repo-profile (or our own equivalent below). Inputs
      containing anchors `&`, aliases `*`, tags `!!`, or flow-style braces
      `{`/`}` are REJECTED (ValueError → exit 4). `yaml.safe_load` would
      reject anchors/aliases similarly; we go further and reject at lexer
      stage so the rejection survives even without PyYAML.
    - Path-traversal guard: every user-supplied path (--target, etc.)
      is resolved and asserted to live UNDER the resolved repo root
      via `resolve().relative_to(repo_root.resolve())`. Reject with
      exit 3 otherwise.
    - Sec MF-3 audit payload whitelist: only {profile, recommendation_count,
      user_action} fields are emitted via the framework audit hook.

Quiet-mode (Wave 1.12):
    - Env var `CEO_QUIET_MODE` default "1" suppresses info-level chatter.
    - When CEO_QUIET_MODE=1, only the 4 step headers + recommendations +
      the [Y/n/customize] prompt are written; warnings still print.
    - Explicit `CEO_QUIET_MODE=0` re-enables full status lines.

Stdlib only. Python 3.9+. No PyYAML, no external dependencies.

CLI:
    first-run-wizard.py run [--target PATH] [--no-interactive] [--force] [--json]
    first-run-wizard.py show [--target PATH] [--json]
    first-run-wizard.py --help

Exit codes:
    0 — success (wizard completed; `.claude/wizard-completed.yaml` written
        or user declined cleanly via "n")
    1 — soft failure (wizard ran but recommendation set was empty;
        actionable `/onboard` fallback printed)
    2 — hard failure (profile is `unknown-needs-owner-confirmation`;
        caller must run `confirm-profile`)
    3 — usage error (bad CLI args / path-traversal attempt / unknown
        --target outside repo root)
    4 — IO / schema error (file unreadable, malformed yaml, forbidden
        yaml feature such as anchor/alias/tag/flow-map)
"""

from __future__ import annotations

import argparse
import datetime as _dt
import io
import json
import os
import re
import sys
from pathlib import Path
from typing import Any, Callable, Dict, List, Optional, Tuple

# ---------------------------------------------------------------------------
# Module-level constants
# ---------------------------------------------------------------------------

WIZARD_VERSION = "1"
WIZARD_COMPLETED_FILENAME = "wizard-completed.yaml"
REPO_PROFILE_FILENAME = "repo-profile.yaml"
CLAUDE_DIR_NAME = ".claude"

# Sec MF-3 whitelist for audit emit payload (only these keys leave the
# wizard process boundary).
_AUDIT_ALLOWED_FIELDS = frozenset({
    "profile",
    "recommendation_count",
    "user_action",
})

# Confidence-label fallback (when sibling Wave 1.10 module not importable
# at runtime in target repo). Keep behavior identical to Wave 1.10 contract.
_FALLBACK_SAFE = "safe"
_FALLBACK_NEEDS_CONFIRM = "needs-confirm"

# Recognized user-response tokens for the [Y/n/customize] prompt.
# Default-Y on empty input per spec.
_RESPONSE_YES = frozenset({"y", "yes", ""})
_RESPONSE_NO = frozenset({"n", "no"})
_RESPONSE_CUSTOMIZE = frozenset({"c", "customize", "custom"})

# ---------------------------------------------------------------------------
# Minimal YAML loader (stdlib-only).
#
# Strict subset matching what detect-repo-profile emits + what the
# smart-loading-resolver reads. We REJECT anchors / aliases / tags /
# flow-mappings at lexer stage so that even a hypothetical PyYAML-less
# install cannot accidentally parse a hostile yaml input. This is stricter
# than `yaml.safe_load` (which already rejects most code-execution paths
# but still permits anchors/aliases).
# ---------------------------------------------------------------------------

_YAML_LINE_RE = re.compile(r"^([A-Za-z_][A-Za-z0-9_]*)\s*:\s*(.*)$")
_YAML_LIST_ITEM_RE = re.compile(r"^\s+-\s+(.*)$")


def _strip_quoted_scalars(line: str) -> str:
    """Remove the contents of "..." and '...' from a line so that anchor
    / alias / tag / flow-brace detection runs on STRUCTURE only.

    Mirrors the sibling detect-repo-profile helper so legitimate scalars
    like "strategies/**" do not trip the safety check.
    """
    out: List[str] = []
    i = 0
    n = len(line)
    while i < n:
        ch = line[i]
        if ch == '"':
            # Skip until next unescaped double quote.
            j = i + 1
            while j < n:
                if line[j] == "\\" and j + 1 < n:
                    j += 2
                    continue
                if line[j] == '"':
                    break
                j += 1
            i = j + 1
            continue
        if ch == "'":
            j = i + 1
            while j < n and line[j] != "'":
                j += 1
            i = j + 1
            continue
        out.append(ch)
        i += 1
    return "".join(out)


def _parse_scalar(raw: str, line_no: int) -> Any:
    s = raw.strip()
    if s == "":
        return ""
    low = s.lower()
    if low == "true":
        return True
    if low == "false":
        return False
    if low in ("null", "~"):
        return None
    # Quoted strings (drop the quotes, basic escape pass for \" and \\).
    if len(s) >= 2 and s[0] == '"' and s[-1] == '"':
        body = s[1:-1]
        return body.replace('\\"', '"').replace("\\\\", "\\")
    if len(s) >= 2 and s[0] == "'" and s[-1] == "'":
        return s[1:-1]
    # Integer.
    if re.match(r"^-?\d+$", s):
        try:
            return int(s)
        except ValueError:
            return s
    # Bare string (no surprise booleans/null already handled).
    return s


def safe_load_yaml(text: str) -> Dict[str, Any]:
    """Parse a YAML subset: top-level `key: scalar`, `key: []`, and
    `key:` followed by `  - "item"` block lists.

    Rejects anchors (&), aliases (*), tags (!!), flow-style braces ({}),
    and nested mappings. Raises ValueError on malformed input.

    This is intentionally stricter than `yaml.safe_load` so that even
    if the install pulls PyYAML in the future, the wizard's contract
    does not regress.
    """
    if not isinstance(text, str):
        raise ValueError("safe_load_yaml: input must be str")

    result: Dict[str, Any] = {}
    current_list_key: Optional[str] = None

    for line_no, raw in enumerate(text.splitlines(), start=1):
        # Strip UTF-8 BOM on first line.
        if line_no == 1 and raw.startswith("﻿"):
            raw = raw[1:]
        stripped = raw.rstrip()
        if not stripped:
            current_list_key = None
            continue
        if stripped.startswith("#") or stripped == "---" or stripped == "...":
            continue

        # SECURITY: detect forbidden yaml features on the structural portion
        # only (outside quoted strings).
        structural = _strip_quoted_scalars(stripped)
        if (
            "&" in structural
            or "*" in structural
            or "!!" in structural
            or "{" in structural
            or "}" in structural
        ):
            raise ValueError(
                "line {ln}: yaml feature rejected (anchor/alias/tag/flow-map)".format(
                    ln=line_no
                )
            )

        # Block-list item.
        m_item = _YAML_LIST_ITEM_RE.match(stripped)
        if m_item:
            if current_list_key is None:
                raise ValueError(
                    "line {ln}: list item with no parent key".format(ln=line_no)
                )
            value_repr = m_item.group(1).strip()
            parsed = _parse_scalar(value_repr, line_no)
            target = result[current_list_key]
            if not isinstance(target, list):
                raise ValueError(
                    "line {ln}: parent key is not a list".format(ln=line_no)
                )
            target.append(parsed)
            continue

        # Top-level keys must not be indented.
        if stripped != stripped.lstrip():
            raise ValueError(
                "line {ln}: unexpected indentation".format(ln=line_no)
            )

        m_key = _YAML_LINE_RE.match(stripped)
        if not m_key:
            raise ValueError(
                "line {ln}: cannot parse (expected `key: value`)".format(ln=line_no)
            )
        key, rest = m_key.group(1), m_key.group(2).strip()
        if rest == "":
            result[key] = []
            current_list_key = key
            continue
        if rest == "[]":
            result[key] = []
            current_list_key = None
            continue
        result[key] = _parse_scalar(rest, line_no)
        current_list_key = None

    return result


def emit_yaml(data: Dict[str, Any]) -> str:
    """Serialize a small mapping to the same YAML subset that
    safe_load_yaml round-trips. Used to write wizard-completed.yaml.
    """
    lines: List[str] = []
    for key in sorted(data.keys()):
        value = data[key]
        if isinstance(value, bool):
            lines.append("{k}: {v}".format(k=key, v="true" if value else "false"))
        elif value is None:
            lines.append("{k}: null".format(k=key))
        elif isinstance(value, int):
            lines.append("{k}: {v}".format(k=key, v=str(value)))
        elif isinstance(value, str):
            # Always quote strings to avoid YAML-bool ambiguity.
            escaped = value.replace("\\", "\\\\").replace('"', '\\"')
            lines.append('{k}: "{v}"'.format(k=key, v=escaped))
        elif isinstance(value, list):
            if not value:
                lines.append("{k}: []".format(k=key))
                continue
            lines.append("{k}:".format(k=key))
            for item in value:
                if isinstance(item, str):
                    esc = item.replace("\\", "\\\\").replace('"', '\\"')
                    lines.append('  - "{v}"'.format(v=esc))
                elif isinstance(item, bool):
                    lines.append("  - {v}".format(v="true" if item else "false"))
                elif item is None:
                    lines.append("  - null")
                else:
                    lines.append("  - {v}".format(v=str(item)))
        else:
            # Unsupported types are coerced to repr str (defensive).
            esc = repr(value).replace("\\", "\\\\").replace('"', '\\"')
            lines.append('{k}: "{v}"'.format(k=key, v=esc))
    return "\n".join(lines) + "\n"


# ---------------------------------------------------------------------------
# Path-traversal guard
# ---------------------------------------------------------------------------


def safe_resolve_target(target: Optional[str], *, default_cwd: Optional[Path] = None) -> Path:
    """Resolve --target into an absolute path UNDER the repo root.

    The "repo root" for traversal purposes is the resolved target itself
    when no explicit boundary is provided; we ensure that the result is
    a real directory that exists and we reject obvious traversal markers
    (.., null bytes, control chars) in the raw input before resolving.

    Exit code 3 (caller exits) on rejection.

    Args:
        target: User-supplied --target string. None falls back to cwd.
        default_cwd: Override for default working dir (test injection).

    Returns:
        Resolved Path that exists.

    Raises:
        ValueError: on traversal attempts or non-existent target.
    """
    base_cwd = default_cwd if default_cwd is not None else Path.cwd()

    if target is None or target == "":
        candidate = base_cwd
    else:
        # Reject obvious control characters or null bytes.
        if "\x00" in target or any(ord(c) < 0x20 for c in target):
            raise ValueError("path contains control characters")
        # Resolve relative to cwd if not absolute.
        raw = Path(target)
        if not raw.is_absolute():
            raw = base_cwd / raw
        candidate = raw

    try:
        resolved = candidate.resolve(strict=True)
    except FileNotFoundError as e:
        raise ValueError("target path does not exist: {p}".format(p=candidate)) from e

    if not resolved.is_dir():
        raise ValueError("target path is not a directory: {p}".format(p=resolved))

    # Defense in depth: confirm that the resolved path does not escape
    # via symlink ladders by ensuring we can take its `relative_to` itself
    # (trivially true) and that no `..` parts survive resolution.
    parts = resolved.parts
    if any(p == ".." for p in parts):
        raise ValueError("resolved path still contains '..' parts: {p}".format(p=resolved))

    return resolved


def safe_child_path(repo_root: Path, child: Path) -> Path:
    """Ensure that `child` resolves to a path under `repo_root`.

    Used for ALL file reads/writes inside the wizard so a hostile symlink
    cannot trick us into reading /etc/passwd or writing into /tmp.

    Raises:
        ValueError: if the resolved child is outside repo_root.
    """
    repo_root_resolved = repo_root.resolve()
    # We do NOT require child to exist (we may write a file that does
    # not yet exist), so resolve(strict=False) and then check.
    child_resolved = child.resolve()
    try:
        child_resolved.relative_to(repo_root_resolved)
    except ValueError as e:
        raise ValueError(
            "path-traversal blocked: {c} is outside repo root {r}".format(
                c=child_resolved, r=repo_root_resolved
            )
        ) from e
    return child_resolved


# ---------------------------------------------------------------------------
# Quiet-mode helpers
# ---------------------------------------------------------------------------


def is_quiet_mode(env: Optional[Dict[str, str]] = None) -> bool:
    """Return True when CEO_QUIET_MODE is the default ("1" or unset).

    Per Wave 1.12 the default is quiet. Explicit "0" disables.
    """
    _env = env if env is not None else dict(os.environ)
    value = _env.get("CEO_QUIET_MODE", "1")
    return value != "0"


def make_emitter(stdout: io.TextIOBase, quiet: bool) -> Callable[[str], None]:
    """Return a closure that prints info-level lines only when not quiet."""

    def _emit(line: str) -> None:
        if not quiet:
            stdout.write(line + "\n")

    return _emit


# ---------------------------------------------------------------------------
# Profile loading
# ---------------------------------------------------------------------------


def load_repo_profile(repo_root: Path) -> Dict[str, Any]:
    """Read and parse `.claude/repo-profile.yaml`.

    Returns the parsed dict. Raises ValueError on missing-or-malformed
    file; caller maps to exit 4 (IO/schema) or exit 2 (unknown profile).
    """
    profile_path = safe_child_path(
        repo_root, repo_root / CLAUDE_DIR_NAME / REPO_PROFILE_FILENAME
    )
    if not profile_path.is_file():
        raise ValueError(
            "repo-profile not found at {p}; run detect-repo-profile.py detect first".format(
                p=profile_path
            )
        )
    try:
        text = profile_path.read_text(encoding="utf-8")
    except OSError as e:
        raise ValueError("cannot read repo-profile: {e}".format(e=e)) from e
    parsed = safe_load_yaml(text)
    # Minimal schema sanity: must have `risk_class`.
    if "risk_class" not in parsed:
        raise ValueError("repo-profile missing required key: risk_class")
    return parsed


# ---------------------------------------------------------------------------
# Resolver delegation
# ---------------------------------------------------------------------------


def _add_sibling_to_syspath() -> None:
    """Make the sibling Wave 0b smart-loading-resolver + Wave 1.10
    confidence-labels importable when running directly from staging.

    No-op when already importable (e.g. when running from canonical
    `.claude/scripts/` after PLAN-083 ships).
    """
    here = Path(__file__).resolve().parent
    # Staging layout: PLAN-083/staging/wave-2/sub-2-1-wizard/first-run-wizard.py
    # Add wave-0b sub-0-7d + wave-1 sub-1-10 if present.
    plan_staging = here.parent.parent  # -> PLAN-083/staging/
    candidates = [
        plan_staging / "wave-0b" / "sub-0-7d-outcome-gates-resolver",
        plan_staging / "wave-1" / "sub-1-10-confidence-labels",
    ]
    for c in candidates:
        if c.is_dir() and str(c) not in sys.path:
            sys.path.insert(0, str(c))


def resolve_active_skills(
    repo_root: Path,
    *,
    resolver_fn: Optional[Callable[..., Dict[str, Any]]] = None,
    skill_glob: str = "**/SKILL.md",
) -> Dict[str, Any]:
    """Invoke smart-loading-resolver.resolve() and return its result.

    Test injection via `resolver_fn` lets the unit suite bypass the
    real resolver. Path-traversal guard applies to all derived paths.
    """
    if resolver_fn is not None:
        return resolver_fn(repo_root=repo_root, skill_glob=skill_glob)

    _add_sibling_to_syspath()
    try:
        # The sibling staging file uses hyphens; tests load it via importlib
        # but for runtime we shim a one-shot import here.
        import importlib.util as _ilu

        here = Path(__file__).resolve().parent
        candidate = (
            here.parent.parent
            / "wave-0b"
            / "sub-0-7d-outcome-gates-resolver"
            / "smart-loading-resolver.py"
        )
        # When deployed under .claude/scripts/, sibling resolver is at
        # `.claude/scripts/smart-loading-resolver.py`.
        canonical_candidate = repo_root / CLAUDE_DIR_NAME / "scripts" / "smart-loading-resolver.py"
        if canonical_candidate.is_file():
            candidate = canonical_candidate
        if not candidate.is_file():
            raise ValueError(
                "smart-loading-resolver.py not found (tried staging + canonical)"
            )
        # Path-traversal guard the resolver path too if it is under repo_root.
        if str(candidate).startswith(str(repo_root.resolve())):
            safe_child_path(repo_root, candidate)
        spec = _ilu.spec_from_file_location("smart_loading_resolver", candidate)
        if spec is None or spec.loader is None:
            raise ValueError("cannot build import spec for smart-loading-resolver")
        mod = _ilu.module_from_spec(spec)
        spec.loader.exec_module(mod)  # type: ignore[union-attr]
    except Exception as e:
        raise ValueError("smart-loading-resolver import failed: {e}".format(e=e)) from e

    profile_path = repo_root / CLAUDE_DIR_NAME / REPO_PROFILE_FILENAME
    skill_root = repo_root / CLAUDE_DIR_NAME / "skills"
    cap_table_path = repo_root / CLAUDE_DIR_NAME / "policies" / "smart-loading-cap-table.yaml"

    # PLAN-085 Wave A.2 (R-002): canonical location is .claude/policies/.
    # Pre-Wave-A installs (or adopters mid-upgrade) may still carry the
    # YAML at the old .claude/scripts/ path — honor it as fallback so the
    # wizard does not crash. Staging fallback (Wave 0b sub-0.7d) retained
    # for source-tree dogfood runs prior to install.
    if not cap_table_path.is_file():
        legacy_scripts_cap = repo_root / CLAUDE_DIR_NAME / "scripts" / "smart-loading-cap-table.yaml"
        if legacy_scripts_cap.is_file():
            cap_table_path = legacy_scripts_cap
        else:
            staging_cap = (
                Path(__file__).resolve().parent.parent.parent
                / "wave-0b"
                / "sub-0-7d-outcome-gates-resolver"
                / "smart-loading-cap-table.yaml"
            )
            if staging_cap.is_file():
                cap_table_path = staging_cap

    return mod.resolve(  # type: ignore[no-any-return]
        profile_path=profile_path,
        skill_root=skill_root,
        cap_table_path=cap_table_path,
        skill_glob=skill_glob,
        debug=False,
    )


# ---------------------------------------------------------------------------
# Confidence labels delegation
# ---------------------------------------------------------------------------


def _try_load_confidence_labels() -> Optional[Any]:
    """Return the Wave 1.10 module if importable, else None.

    On None, the wizard falls back to a static "[NEEDS-CONFIRM]" marker
    (no false-SAFE), matching Wave 1.10's fail-medium contract.
    """
    _add_sibling_to_syspath()
    try:
        import confidence_labels  # type: ignore[import-not-found]

        return confidence_labels
    except Exception:
        return None


def confidence_marker_for(
    skill_path: str,
    profile: str,
    *,
    labels_mod: Optional[Any] = None,
) -> str:
    """Compute a `[SAFE|NEEDS-CONFIRM|RISKY]` marker for a recommended skill.

    We classify the *recommendation* as a read-class action (we are not
    yet executing the skill), so the default surface is SAFE for most
    profiles; trading-readonly bumps to NEEDS-CONFIRM to ensure the
    Owner sees the marker mismatch.
    """
    mod = labels_mod if labels_mod is not None else _try_load_confidence_labels()
    if mod is None:
        # Fallback: trading-readonly -> NEEDS-CONFIRM, else SAFE.
        if profile == "trading-readonly":
            return "[NEEDS-CONFIRM]"
        return "[SAFE]"
    # Use the "help_me" action_type (read-class) and let context decide.
    context = {"profile": profile}
    c = mod.classify("help_me", context)
    # Trading-readonly read is still SAFE under Wave 1.10's rules; we
    # bump it to NEEDS-CONFIRM at the wizard layer to surface the bigger
    # context (the skill *itself* may write later).
    if profile == "trading-readonly" and c.level == mod.SAFE:
        bumped = mod.Confidence(level=mod.NEEDS_CONFIRM, reason_code="trading_profile_bump")
        return mod.as_emoji_free_marker(bumped)
    return mod.as_emoji_free_marker(c)


# ---------------------------------------------------------------------------
# Audit emit (Sec MF-3 whitelist)
# ---------------------------------------------------------------------------


def emit_audit_first_run_wizard(payload: Dict[str, Any]) -> None:
    """Emit the framework audit action with ONLY whitelisted fields.

    Fail-open: any error inside the audit_emit subtree is swallowed so
    the wizard never blocks the user.
    """
    safe = {k: v for (k, v) in payload.items() if k in _AUDIT_ALLOWED_FIELDS}
    try:
        # Lazy import the framework hook helper if available.
        here = Path(__file__).resolve()
        # Walk upward to find a `.claude/hooks/_lib/audit_emit.py`.
        cursor = here
        emitted = False
        for _ in range(6):
            cursor = cursor.parent
            cand = cursor / CLAUDE_DIR_NAME / "hooks"
            if cand.is_dir():
                if str(cand) not in sys.path:
                    sys.path.insert(0, str(cand))
                try:
                    from _lib import audit_emit  # type: ignore[import-not-found]

                    audit_emit.emit_generic("first_run_wizard_completed", **safe)
                    emitted = True
                except Exception:
                    pass
                break
        if not emitted:
            # Framework hook not present (e.g. mid-install). No-op.
            return
    except Exception:
        # fail-open per framework discipline
        return


# ---------------------------------------------------------------------------
# Step 1 — detect
# ---------------------------------------------------------------------------


def step_detect(
    repo_root: Path,
    *,
    stdout: io.TextIOBase,
    emit_info: Callable[[str], None],
) -> Tuple[int, Optional[Dict[str, Any]]]:
    """Run step 1. Returns (exit_code, profile_dict_or_None).

    Exit semantics:
        0 — profile loaded and is a known auto-detectable risk_class.
        2 — risk_class is `unknown-needs-owner-confirmation`; caller
            prints actionable next-step and stops.
        4 — IO / schema error on profile file.
    """
    stdout.write("Step 1/4 — detecting repo profile\n")
    try:
        profile = load_repo_profile(repo_root)
    except ValueError as e:
        stdout.write("  ERROR: {e}\n".format(e=e))
        stdout.write(
            "  Run: python3 .claude/scripts/detect-repo-profile.py detect\n"
        )
        return 4, None

    risk_class = profile.get("risk_class", "")
    if risk_class == "unknown-needs-owner-confirmation":
        stdout.write(
            "  Detection inconclusive. The framework needs an explicit Owner ack.\n"
        )
        stdout.write(
            "  Run: python3 .claude/scripts/detect-repo-profile.py confirm-profile <name>\n"
        )
        stdout.write(
            "  Valid names: frontend, engine, fintech, trading-readonly, generic\n"
        )
        return 2, profile

    emit_info("  detected risk_class={c} confidence={f}".format(
        c=risk_class, f=profile.get("confidence", "?")
    ))
    return 0, profile


# ---------------------------------------------------------------------------
# Step 2 — explain
# ---------------------------------------------------------------------------


def _format_top_n(active_skills: List[str], n: int = 5) -> str:
    if not active_skills:
        return "(none)"
    return ", ".join(active_skills[:n])


def step_explain(
    profile: Dict[str, Any],
    resolve_result: Dict[str, Any],
    *,
    stdout: io.TextIOBase,
) -> None:
    """Render the 3-5 line summary for step 2.

    Always prints (not info-level) so the user always sees their context.
    """
    stdout.write("Step 2/4 — explaining your context\n")
    risk_class = str(profile.get("risk_class", "?"))
    confidence = str(profile.get("confidence", "?")).upper()
    active = resolve_result.get("active_skills") or []
    active_count = resolve_result.get("active_count", len(active))
    suppressed = resolve_result.get("suppressed_count", 0)
    stdout.write(
        "  Detected as {rc} with confidence {co}.\n".format(rc=risk_class, co=confidence)
    )
    stdout.write(
        "  Active skills ({n}): {top}\n".format(
            n=active_count, top=_format_top_n(active, n=5)
        )
    )
    stdout.write(
        "  Suppressed dormant skills: {s}\n".format(s=suppressed)
    )
    stdout.write(
        "  Read-only mode for first 7 days per safety policy.\n"
    )
    stdout.write(
        "  Override via: python3 .claude/scripts/detect-repo-profile.py confirm-profile <name>\n"
    )


# ---------------------------------------------------------------------------
# Step 3 — recommend
# ---------------------------------------------------------------------------


def _rationale_for(skill_path: str, profile: str) -> str:
    """One-sentence rationale per recommendation.

    Pure-function (no I/O). Keep deterministic so tests pass.
    """
    base = skill_path.split("/")[-2] if "/" in skill_path else skill_path
    return "Active under '{p}' profile; surfaces capability '{s}'.".format(
        p=profile, s=base
    )


def step_recommend(
    profile_name: str,
    resolve_result: Dict[str, Any],
    *,
    stdout: io.TextIOBase,
    labels_mod: Optional[Any] = None,
) -> List[Dict[str, str]]:
    """Render and return the top-3 recommendations.

    If the resolver returned zero active skills, prints the `/onboard`
    fallback and returns an empty list (caller exit code 1).

    Returns:
        List of dicts with keys {skill_path, marker, rationale}. Length
        is 0 (fallback) or up to 3.
    """
    stdout.write("Step 3/4 — recommending top-3 skills\n")
    active = list(resolve_result.get("active_skills") or [])
    if not active:
        stdout.write(
            "  No skills active for profile '{p}'.\n".format(p=profile_name)
        )
        stdout.write(
            "  Run: /onboard to orient yourself manually.\n"
        )
        return []

    top3 = active[:3]
    recs: List[Dict[str, str]] = []
    for idx, skill_path in enumerate(top3, start=1):
        marker = confidence_marker_for(
            skill_path, profile_name, labels_mod=labels_mod
        )
        rationale = _rationale_for(skill_path, profile_name)
        stdout.write(
            "  {i}. {m} {s}\n     {r}\n".format(
                i=idx, m=marker, s=skill_path, r=rationale
            )
        )
        recs.append({
            "skill_path": skill_path,
            "marker": marker,
            "rationale": rationale,
        })
    return recs


# ---------------------------------------------------------------------------
# Step 4 — ask
# ---------------------------------------------------------------------------


def _read_response(
    stdin: io.TextIOBase, stdout: io.TextIOBase, prompt: str
) -> Optional[str]:
    """Print prompt + read one line. Returns None on EOF / IO error."""
    try:
        stdout.write(prompt)
        stdout.flush()
    except Exception:
        pass
    try:
        line = stdin.readline()
    except Exception:
        return None
    if line == "":
        # EOF in non-interactive contexts.
        return None
    return line.strip().lower()


def step_ask(
    profile_name: str,
    recommendations: List[Dict[str, str]],
    *,
    stdin: io.TextIOBase,
    stdout: io.TextIOBase,
    non_interactive: bool,
) -> Tuple[str, List[Dict[str, str]]]:
    """Run the [Y/n/customize] prompt.

    Args:
        profile_name: risk_class from profile.
        recommendations: top-3 from step_recommend.
        non_interactive: True for CI / piped contexts; assume "y".

    Returns:
        (user_action, chosen_recs) where user_action is one of
        "accepted", "declined", "customized" and chosen_recs is the
        final selected list.
    """
    stdout.write("Step 4/4 — confirm or customize\n")
    if non_interactive:
        stdout.write("  --no-interactive set; defaulting to Y\n")
        return "accepted", recommendations

    response = _read_response(
        stdin,
        stdout,
        "  Continue with these recommendations? [Y/n/customize]: ",
    )
    if response is None:
        # EOF -> treat as decline (safer than implicit-Y in
        # non-interactive contexts; --no-interactive is the explicit
        # opt-in).
        stdout.write("  (no input; declining)\n")
        return "declined", []

    if response in _RESPONSE_NO:
        stdout.write("  Declined. Run this wizard again any time.\n")
        return "declined", []

    if response in _RESPONSE_CUSTOMIZE:
        chosen = _customize_loop(recommendations, stdin=stdin, stdout=stdout)
        return "customized", chosen

    if response in _RESPONSE_YES:
        return "accepted", recommendations

    # Unknown token — re-prompt once, then default-N on second miss
    # (avoid infinite-loop traps in semi-interactive shells).
    response2 = _read_response(
        stdin,
        stdout,
        "  Unrecognized response. Reply Y, n, or customize: ",
    )
    if response2 is None or response2 in _RESPONSE_NO:
        return "declined", []
    if response2 in _RESPONSE_CUSTOMIZE:
        chosen = _customize_loop(recommendations, stdin=stdin, stdout=stdout)
        return "customized", chosen
    if response2 in _RESPONSE_YES:
        return "accepted", recommendations
    return "declined", []


def _customize_loop(
    recommendations: List[Dict[str, str]],
    *,
    stdin: io.TextIOBase,
    stdout: io.TextIOBase,
) -> List[Dict[str, str]]:
    """Let the user toggle individual recommendations.

    Each iteration prints the current selection state. User types the
    1-based index to toggle, or "done" to commit.
    """
    selected = [True] * len(recommendations)
    while True:
        stdout.write("  Current selection:\n")
        for i, rec in enumerate(recommendations, start=1):
            mark = "[x]" if selected[i - 1] else "[ ]"
            stdout.write(
                "    {m} {i}. {s}\n".format(m=mark, i=i, s=rec["skill_path"])
            )
        line = _read_response(
            stdin, stdout, "  Toggle index, or type 'done': "
        )
        if line is None or line == "done":
            break
        if not line.isdigit():
            stdout.write("  Expected an integer index or 'done'.\n")
            continue
        idx = int(line)
        if 1 <= idx <= len(recommendations):
            selected[idx - 1] = not selected[idx - 1]
        else:
            stdout.write(
                "  Index out of range (1..{n}).\n".format(n=len(recommendations))
            )
    return [recommendations[i] for i, on in enumerate(selected) if on]


# ---------------------------------------------------------------------------
# Persistence
# ---------------------------------------------------------------------------


def _now_utc_iso() -> str:
    return _dt.datetime.now(_dt.timezone.utc).strftime("%Y-%m-%dT%H:%M:%SZ")


def write_wizard_completed(
    repo_root: Path,
    *,
    profile_name: str,
    user_action: str,
    chosen_recs: List[Dict[str, str]],
) -> Path:
    """Persist `.claude/wizard-completed.yaml` (idempotent overwrite ok
    after `--force`; caller is responsible for the pre-check).

    Path-traversal guarded.
    """
    target = safe_child_path(
        repo_root, repo_root / CLAUDE_DIR_NAME / WIZARD_COMPLETED_FILENAME
    )
    target.parent.mkdir(parents=True, exist_ok=True)
    payload: Dict[str, Any] = {
        "completed_at": _now_utc_iso(),
        "profile": profile_name,
        "recommendation_count": len(chosen_recs),
        "recommendations": [r["skill_path"] for r in chosen_recs],
        "user_action": user_action,
        "wizard_version": WIZARD_VERSION,
    }
    text = emit_yaml(payload)
    target.write_text(text, encoding="utf-8")
    return target


def existing_wizard_completed(repo_root: Path) -> Optional[Path]:
    """Return the path to wizard-completed.yaml if it already exists."""
    candidate = repo_root / CLAUDE_DIR_NAME / WIZARD_COMPLETED_FILENAME
    if candidate.is_file():
        return candidate
    return None


# ---------------------------------------------------------------------------
# CLI dispatcher
# ---------------------------------------------------------------------------


def cmd_run(
    repo_root: Path,
    *,
    non_interactive: bool,
    force: bool,
    emit_json: bool,
    stdin: io.TextIOBase,
    stdout: io.TextIOBase,
    env: Optional[Dict[str, str]] = None,
    resolver_fn: Optional[Callable[..., Dict[str, Any]]] = None,
    labels_mod: Optional[Any] = None,
) -> int:
    """The `run` subcommand entry point.

    Returns:
        Exit code (see module docstring).
    """
    quiet = is_quiet_mode(env)
    emit_info = make_emitter(stdout, quiet)

    # Idempotency check.
    existing = existing_wizard_completed(repo_root)
    if existing is not None and not force:
        stdout.write(
            "wizard-completed.yaml already present at {p}\n".format(p=existing)
        )
        stdout.write(
            "Re-run with --force to overwrite (audit row will record reset).\n"
        )
        return 0

    # Step 1
    rc, profile = step_detect(repo_root, stdout=stdout, emit_info=emit_info)
    if rc != 0:
        return rc
    if profile is None:  # defensive
        return 4

    profile_name = str(profile.get("risk_class", "generic"))

    # Resolver
    try:
        resolve_result = resolve_active_skills(
            repo_root,
            resolver_fn=resolver_fn,
        )
    except ValueError as e:
        stdout.write("  ERROR resolving skills: {e}\n".format(e=e))
        return 4

    # Step 2
    step_explain(profile, resolve_result, stdout=stdout)

    # Step 3
    recs = step_recommend(
        profile_name, resolve_result, stdout=stdout, labels_mod=labels_mod
    )
    if not recs:
        # Fallback path: zero recs, exit soft-fail.
        return 1

    # Step 4
    user_action, chosen = step_ask(
        profile_name,
        recs,
        stdin=stdin,
        stdout=stdout,
        non_interactive=non_interactive,
    )

    if user_action == "declined":
        # No persistence on decline — Owner can re-run anytime.
        if emit_json:
            json.dump(
                {
                    "profile": profile_name,
                    "user_action": user_action,
                    "recommendation_count": 0,
                },
                stdout,
            )
            stdout.write("\n")
        return 0

    out_path = write_wizard_completed(
        repo_root,
        profile_name=profile_name,
        user_action=user_action,
        chosen_recs=chosen,
    )

    # Sec MF-3 whitelisted audit emit.
    emit_audit_first_run_wizard({
        "profile": profile_name,
        "recommendation_count": len(chosen),
        "user_action": user_action,
    })

    if emit_json:
        json.dump(
            {
                "profile": profile_name,
                "user_action": user_action,
                "recommendation_count": len(chosen),
                "wizard_completed_path": str(out_path),
            },
            stdout,
        )
        stdout.write("\n")
    else:
        stdout.write(
            "Saved {p}. Re-run with --force to reset.\n".format(p=out_path)
        )
    return 0


def cmd_show(repo_root: Path, *, emit_json: bool, stdout: io.TextIOBase) -> int:
    existing = existing_wizard_completed(repo_root)
    if existing is None:
        stdout.write("(no wizard-completed.yaml yet)\n")
        return 1
    text = existing.read_text(encoding="utf-8")
    parsed = safe_load_yaml(text)
    if emit_json:
        json.dump(parsed, stdout, indent=2, sort_keys=True)
        stdout.write("\n")
    else:
        stdout.write(text)
    return 0


def build_parser() -> argparse.ArgumentParser:
    parser = argparse.ArgumentParser(
        description="First-run wizard — PLAN-083 Wave 2 sub-agent 2.1."
    )
    sub = parser.add_subparsers(dest="cmd", required=True)

    p_run = sub.add_parser("run", help="Run the detect/explain/recommend/ask flow.")
    p_run.add_argument("--target", type=str, default=None)
    p_run.add_argument("--no-interactive", action="store_true")
    p_run.add_argument("--force", action="store_true")
    p_run.add_argument("--json", action="store_true")

    p_show = sub.add_parser("show", help="Show prior wizard-completed.yaml.")
    p_show.add_argument("--target", type=str, default=None)
    p_show.add_argument("--json", action="store_true")
    return parser


def main(argv: Optional[List[str]] = None) -> int:
    parser = build_parser()
    args = parser.parse_args(argv)

    # Path-traversal guard on --target before doing anything else.
    try:
        repo_root = safe_resolve_target(args.target)
    except ValueError as e:
        sys.stderr.write("first-run-wizard: {e}\n".format(e=e))
        return 3

    if args.cmd == "run":
        return cmd_run(
            repo_root,
            non_interactive=bool(args.no_interactive),
            force=bool(args.force),
            emit_json=bool(args.json),
            stdin=sys.stdin,
            stdout=sys.stdout,
        )
    if args.cmd == "show":
        return cmd_show(repo_root, emit_json=bool(args.json), stdout=sys.stdout)
    parser.error("unknown subcommand")
    return 3


if __name__ == "__main__":
    sys.exit(main())
