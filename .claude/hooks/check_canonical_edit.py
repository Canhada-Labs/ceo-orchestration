#!/usr/bin/env python3
"""PreToolUse hook: gate canonical-path edits on Owner-signed sentinel.

Sprint 5 Phase 7 (ADR-010). Blocks Edit / Write / MultiEdit calls
against canonical governance paths unless an Owner-signed sentinel
file (`approved.md`) exists in the same Architect bundle directory
with a valid `Approved-By:` line and the target path declared in its
`Scope:` block.

## Wire-up

Registered in `.claude/settings.json` PreToolUse Edit/Write/MultiEdit:

    {
      "matcher": "Edit|Write|MultiEdit",
      "hooks": [
        {
          "type": "command",
          "command": "bash \"$CLAUDE_PROJECT_DIR/.claude/hooks/_python-hook.sh\" check_canonical_edit.py",
          "timeout": 5,
          "statusMessage": "Checking canonical-path sentinel..."
        }
      ]
    }

## Decision logic

1. Parse `tool_input.file_path` from the payload.
2. If path is NOT in the canonical guard list → allow silently.
3. If path IS canonical:
   a. Look for any sibling `.claude/plans/PLAN-NNN/architect/round-N/approved.md`
      that lists this path under its `Scope:` block.
   b. If sentinel exists + `Approved-By:` line valid → allow.
   c. Otherwise → block with a clear reason.

## Fail-open contract

Any internal exception → allow. The hook never blocks the user on its
own bug. (The canonical edit is allowed; the canonical path is still
governed by CODEOWNERS / branch protection on the merge side.)
"""

from __future__ import annotations

import fnmatch
import json
import os
import hashlib  # PLAN-094 Wave C — sha256 in cache key
import re
import sys
from pathlib import Path
from typing import Dict, List, Optional, Set, Tuple  # PLAN-094 Wave C

# Make the local _lib importable
_HOOKS_DIR = Path(__file__).resolve().parent
if str(_HOOKS_DIR) not in sys.path:
    sys.path.insert(0, str(_HOOKS_DIR))

# PLAN-045 Wave 1 P0-01 — GPG sentinel verification.
try:
    from _lib import gpg_verify as _gpg_verify
except Exception:  # pragma: no cover
    _gpg_verify = None  # type: ignore[assignment]

# PLAN-089 Wave C.4 — sentinel signer registry (ADR-121).
# Behavior-preserving migration: if YAML registry resolves the signer
# via _lib.sentinel_signers, that result wins; otherwise the legacy
# `.claude/sentinel-signers.txt` allowlist is consulted (existing
# PLAN-045 path). Both wires fail-CLOSED on import failure.
try:
    from _lib import sentinel_signers as _sentinel_signers  # type: ignore[import]
except Exception:  # pragma: no cover
    _sentinel_signers = None  # type: ignore[assignment]

_SENTINEL_SIGNERS_REGISTRY_YAML = (
    Path(__file__).resolve().parent.parent.parent
    / ".claude" / "security" / "sentinel-signers-registry.yaml"
)

# PLAN-089 Wave C.4 — R2 Codex iter-1 Q5+Q7 fold: _BOOTSTRAP_REGISTRY_SHA256
# pin per ADR-121 §5. Pre-GENESIS this is None and registry parse failure
# falls back to legacy `.txt` (avoids Wave C.6 transition brick).
# Post-GENESIS the Wave C.6 ceremony rotates this constant via KERNEL
# HARD-DENY ceremony (CEO_KERNEL_OVERRIDE=PLAN-089-WAVE-C-SENTINEL-
# ROTATION-GENESIS) to the SHA256 of the finalized YAML. When set:
#   - Registry hash mismatch → fail-CLOSED (tamper-detect)
#   - Registry parse failure → fail-CLOSED (post-GENESIS no-fallback)
_BOOTSTRAP_REGISTRY_SHA256: Optional[str] = None  # placeholder pre-GENESIS

# PLAN-045 Wave 1 P0-01 — signer allowlist for sentinel .asc signatures.
_SENTINEL_SIGNERS_FILE = (
    Path(__file__).resolve().parent.parent.parent
    / ".claude" / "sentinel-signers.txt"
)


# Canonical paths (relative to repo root) — ADR-010 v1.1 (Sprint 9
# amendment adds conftest.py + new-hook + lessons-related scripts).
# fnmatch.fnmatch is used; `*` is treated as a single segment matcher
# below by walking the path components manually. `**` matches zero or
# more segments (used for the Sprint 9 conftest entry).
#
# PLAN-019 Phase 2 Wave 2A (P1-SEC-A) expansion: full governance surface.
# Every path listed here is sentinel-gated (editable via Owner-signed
# sentinel). The arbitration-kernel subset (hook source files enforcing
# THIS guard, _lib/policy.py, _lib/redact.py, _lib/audit_emit.py, and
# .claude/policies/*.yaml) is ALSO covered by the stricter HARD-DENY
# hook `check_arbitration_kernel.py` — that hook has no sentinel escape
# and requires `CEO_KERNEL_OVERRIDE` with an audit-logged reason. The
# overlap is intentional defense-in-depth: if the arbitration hook is
# disabled by misconfiguration, this sentinel guard still blocks the
# edits (and vice versa).
_CANONICAL_GUARDS = [
    ".claude/team.md",
    ".claude/frontend-team.md",
    ".claude/pitfalls-catalog.yaml",
    # SKILL.md under any tier
    ".claude/skills/core/*/SKILL.md",
    ".claude/skills/frontend/*/SKILL.md",
    # PLAN-074 Wave 0 ADJ-A5: replace fixed 4-segment glob with
    # recursive ** to cover sub-namespaces (e.g. game-development/<engine>).
    ".claude/skills/domains/**/SKILL.md",
    # Domain-level governance files
    ".claude/skills/domains/*/team-personas.md",
    ".claude/skills/domains/*/pitfalls.yaml",
    # Sprint 9 (PLAN-009 A22 / A14) — defense-in-depth for confidence gate
    ".claude/**/conftest.py",
    ".claude/hooks/check_confidence_gate.py",
    ".claude/scripts/lessons.py",
    ".claude/scripts/prune-lessons.py",
    ".claude/scripts/lesson-restore.py",
    ".claude/scripts/lesson_ranker.py",
    # ---- PLAN-019 P1-SEC-A expansion: full governance surface ----
    # Hook source files (all PreToolUse / PostToolUse Python hooks).
    # An agent that can edit these can disable governance. Sentinel-gated
    # so Owner-signed ADRs can still land architectural changes.
    ".claude/hooks/*.py",
    ".claude/hooks/_python-hook.sh",
    # Hook shared library (_lib/*) — governance utilities.
    ".claude/hooks/_lib/*.py",
    ".claude/hooks/_lib/adapters/*.py",
    ".claude/hooks/_lib/**/*.py",
    # Policy-as-code (ADR-045) — policies + fixtures.
    ".claude/policies/*.yaml",
    ".claude/policies/*.yml",
    ".claude/policies/fixtures/*.jsonl",
    # PLAN-080 Phase 0b — JSON Schema for squad-bundle frontmatter validation
    # (M2-CDX-4 closure). Guarded so squad-bundle authoring contract cannot
    # be silently weakened. KERNEL-HARD-DENY since check_canonical_edit.py
    # itself is in _KERNEL_PATHS — extending its guard list requires both
    # CEO_KERNEL_OVERRIDE=PLAN-080-PHASE-0B-SCHEMA-GUARD-EXTENSION AND
    # CEO_KERNEL_OVERRIDE_ACK=I-ACCEPT in addition to the sentinel.
    ".claude/policies/schemas/*.json",
    # PLAN-081 Phase 2 — Pair-Rail dispatcher canonical surface. The
    # routing-matrix.yaml carries the per-archetype coder/reviewer
    # decisions consumed by inject-agent-context.sh --pair-mode and
    # check_pair_rail.py (Phase 3 asymmetric VETO matrix arms). Mutation
    # of this YAML or the loader/predicate-eval would mis-route Pair-Rail
    # dispatches (T-4 archetype-spoofing in CROSS-LLM-THREAT-MODEL.md).
    # Sentinel-gated edits only — KERNEL-HARD-DENY since this guard list
    # itself is in _KERNEL_PATHS — extending requires
    # CEO_KERNEL_OVERRIDE=PLAN-081-PHASE-2-DISPATCHER-GUARD-EXTENSION
    # AND CEO_KERNEL_OVERRIDE_ACK=I-ACCEPT.
    ".claude/dispatcher/*.py",
    ".claude/dispatcher/*.yaml",
    ".claude/dispatcher/*.yml",
    ".claude/dispatcher/**/*.py",
    # Settings file — matcher/hook registration.
    ".claude/settings.json",
    # PLAN-074 Wave 0 ADJ-A3 BLOCKER 2: sub-agent definitions ship the
    # ROUTING TABLE personas + model: floor declarations. Editable only
    # via Owner-signed sentinel; CR/Sec/etc. archetype files cannot be
    # silently mutated by a sub-agent.
    ".claude/agents/*.md",
    # ADRs — architectural record, supersede/immutability discipline.
    ".claude/adr/ADR-*.md",
    ".claude/adr/README.md",
    # SPEC/v1 — published compliance contract.
    "SPEC/v1/*.md",
    "SPEC/**/*.md",
    # CI workflows — release / branch-protection / validation gates.
    ".github/workflows/*.yml",
    ".github/workflows/*.yaml",
    # CODEOWNERS — merge-side branch-protection gate.
    ".github/CODEOWNERS",
    # Installer + upgrader scripts — framework distribution surface.
    "scripts/install.sh",
    "scripts/install-npm.sh",
    "scripts/upgrade.sh",
    # PLAN-138 Wave C (ADR-155) — sourced helpers backing the install/upgrade
    # baseline-manifest engine. They are `source`d by the GPG-gated
    # install.sh/upgrade.sh, so mutating them silently changes the integrity
    # classification (FRAMEWORK-CHANGED vs ADOPTER-CUSTOMIZED) that protects
    # adopter customizations + the root PROTOCOL.md. Guarded so they are not a
    # soft underbelly relative to the scripts that source them.
    "scripts/_hash_lib.sh",
    "scripts/_framework_manifest_set.sh",
    # Root governance docs. PROTOCOL.md is rarely-changed governance;
    # CLAUDE.md is intentionally NOT guarded because it is edited every
    # session during closeout (see DYN-SEC1 dynamic finding). Protecting
    # CLAUDE.md needs a separate "session-closeout" ceremony convention
    # (tracked in dynamic-findings.md).
    "PROTOCOL.md",
    # PLAN-042 ITEM 6 (FINDING-14): spec.md is injected
    # verbatim into sub-agent prompts via `## SPEC CONTEXT`
    # (ADR-058). Guard prevents unauthorized spec edits from
    # becoming a prompt-injection vector across sub-agents.
    ".claude/plans/PLAN-*/spec.md",
    # PLAN-043 / ADR-064 — tier-policy artifacts
    ".claude/tier-policy.json",
    ".claude/tier-policy.json.sigchain",
    # PLAN-081 Phase 4-bis — Pair-Rail locked corpus governance per ADR-111.
    # The MANIFEST + each fixture file are SHA-pinned; mutation defeats the
    # cross-LLM disagreement signal (corpus immutability is a structural
    # defense per ADR-108 §Operational). Sentinel-gated edits only — KERNEL
    # HARD-DENY since this guard list itself is in _KERNEL_PATHS — extending
    # requires CEO_KERNEL_OVERRIDE=PLAN-081-PHASE-4-BIS-CORPUS-GUARD-EXTENSION
    # AND CEO_KERNEL_OVERRIDE_ACK=I-ACCEPT.
    ".claude/plans/PLAN-*/corpus/locked/MANIFEST.md",
    ".claude/plans/PLAN-*/corpus/locked/**/*.py",
    ".claude/plans/PLAN-*/corpus/locked/**/*.js",
    # PLAN-081 Phase 6-bis — Pair-Rail governance pin files (codex-cli-pin,
    # codex-cli-binary-sha256, inputs-hash-manifest, verdict-template,
    # function-length-grandfather, governance-waivers, audit_tokens_allowlist).
    # Mutation of any of these silently changes release-gate behavior or
    # pair-rail trust-chain validation. Sentinel-gated edits only — KERNEL
    # HARD-DENY since this guard list itself is in _KERNEL_PATHS — extending
    # requires CEO_KERNEL_OVERRIDE=PLAN-081-PHASE-6-BIS-GOVERNANCE-GUARD-EXTENSION
    # AND CEO_KERNEL_OVERRIDE_ACK=I-ACCEPT.
    ".claude/governance/*.txt",
    ".claude/governance/*.md",
    ".claude/governance/*.yaml",
    ".claude/governance/*.json",
    # PLAN-084 Wave 0.5 — SOTA-finalization audit canonical artifacts.
    # 3 outputs: findings-master.jsonl, capability-gap-report.md,
    # evolution-roadmap.md. KERNEL HARD-DENY extension per ADR-113;
    # CEO_KERNEL_OVERRIDE=PLAN-084-WAVE-0-CANONICAL-GUARD-EXTENSION +
    # CEO_KERNEL_OVERRIDE_ACK=I-ACCEPT required to extend this list.
    ".claude/plans/PLAN-*/canonical/*",
    # ---- PLAN-155 Wave 3b (SENT-CX-E) — Codex kill-switch surface ----
    # debate A8: the .codex registration/rules/managed surface + the
    # operator AGENTS.md are the rail's OWN disarm surface under the Codex
    # harness. Waves 2/3 EMIT these as unguarded L2 templates; without this
    # guard an agent running under Codex could rewrite `.codex/hooks.json`
    # (or the rest of the surface) and disarm every ENFORCED rail while the
    # boot tripwire that should detect it stays silent — the circular-disarm
    # gap. Sentinel-gated edits only. KERNEL HARD-DENY since this guard list
    # itself is in `_KERNEL_PATHS` — extending it requires
    # CEO_KERNEL_OVERRIDE=PLAN-155-CODEX-KILLSWITCH-GUARD-EXTENSION AND
    # CEO_KERNEL_OVERRIDE_ACK=I-ACCEPT in addition to the SENT-CX-E sentinel
    # (same double-gate as PLAN-080-PHASE-0B / PLAN-081-PHASE-2). NOTE: in
    # THIS framework repo the root `AGENTS.md` is the reviewer contract
    # (S261) — a trusted prompt surface injected into reviewer prompts — so
    # guarding it here is a deliberate, defensible protection, not only the
    # installed-target operator file. Path patterns are repo-relative and
    # apply to BOTH this repo and an installed target's tree.
    ".codex/hooks.json",
    ".codex/config.toml",
    ".codex/rules/ceo.rules",
    "requirements.toml",
    "AGENTS.md",
]


# PLAN-065 Layer A (S81-tris gap closure, 2026-05-04):
# Write-shape parameter keys observed in MCP tool input payloads.
# When tool_name starts with `mcp__`, the hook scans tool_input for
# values under any of these keys and treats each as a candidate
# canonical-edit target. Conservative list: matches common MCP server
# implementations (codex, supabase, claude_ai_*) without false-positive
# on read-only tools. Tools like mcp__codex__apply_patch encode the
# target inside a `patch` blob (unified diff); v1 of Layer A does NOT
# parse those blobs — Layer B (PLAN-070 R3, server-side middleware)
# closes that surface. Layer A relies on the hook gate at PreToolUse
# matcher to surface mcp__* events; the hook itself blocks any direct
# path match against canonical guards.
_MCP_WRITE_PATH_KEYS = (
    "path",
    "file_path",
    "target_path",
    "file",
    "filename",
    "dest",
    "destination",
    "target",
    "uri",
)


def _extract_mcp_target_paths(tool_input: dict) -> List[str]:
    """Best-effort extraction of canonical-edit candidate paths from MCP
    tool input. Returns a list of string paths whose canonical status
    will be checked. Non-string / non-path-shaped values are ignored.

    PLAN-065 Layer A — closes S81-tris gap. Custom MCP tools previously
    bypassed `check_canonical_edit.py` because their tool_name does not
    match the legacy `Edit|Write|MultiEdit` matcher. Settings.json now
    routes `mcp__.*` here too; this function maps the heterogeneous
    MCP tool input shapes to a flat list of candidate paths.
    """
    if not isinstance(tool_input, dict):
        return []
    paths: List[str] = []
    for key in _MCP_WRITE_PATH_KEYS:
        value = tool_input.get(key)
        if isinstance(value, str) and value:
            # Length cap defense (Sec MF-7 mirror): reject pathological
            # input early. Real MCP paths are <4 KiB; absurdly long
            # values are likely adversarial.
            if len(value) <= 4096:
                paths.append(value)
        elif isinstance(value, list):
            for item in value:
                if isinstance(item, str) and item and len(item) <= 4096:
                    paths.append(item)
    return paths


_APPROVED_BY_RE = re.compile(
    r"^\s*Approved-By:\s*@[\w\-]+\s+\S+", flags=re.MULTILINE
)

# PLAN-085 Wave E.5 — amendment file frontmatter pattern. Amendment
# files (e.g. `approved-amendment-2026-05-12.md`) reference the
# original sentinel they extend via an `Amends:` line and inherit its
# Scope: declarations transitively. The discovery path resolves the
# chain in `_find_sentinels` filtering above; the byte-identity of the
# original sentinel is preserved (no mutation, only amendment).
_AMENDS_RE = re.compile(
    r"^\s*Amends:\s*\.claude/plans/PLAN-\d{3}/[^\n]+", flags=re.MULTILINE
)

# PLAN-044 audit-v2 C6-P0-04 — Scope: block parser regex constants.
# Supports both the PLAN-050 round-17 plain `Scope:` format AND the
# Session 67 mega-sentinel `Scope (24 canonical paths):` format with
# categorized sub-sections and blank lines between bullet groups.
_SCOPE_HEADER_RE = re.compile(
    r"^Scope(?:\s*\([^)\n]*\))?:\s*$",
    flags=re.MULTILINE,
)
# Top-level continuation headers that mark the end of the Scope block.
# Sub-section headers WITHIN Scope (e.g. "Hook code (PLAN-052):") are
# NOT in this set and are silently skipped during bullet collection.
_SCOPE_TERMINATOR_RE = re.compile(
    r"^(?:Effective|Plans|Rationale(?:\s+by\s+path)?|"
    r"Authorization(?:\s+source)?|Anchor\s+commit|Approved-By)"
    r"\s*[:.]",
    flags=re.IGNORECASE,
)
# Markdown horizontal rule — also terminates Scope block.
_SCOPE_HR_RE = re.compile(r"^(?:-{3,}|\*{3,}|_{3,})\s*$")

# PLAN-064 Option D — Lexical scope markers (DIM-13 closure, 2026-05-04).
#
# Tier-1 sentinel format: scope is delimited by HTML-comment markers,
# unambiguously separating signed scope from lifecycle annotations.
#
#     <!-- BEGIN SIGNED SCOPE -->
#     Approved-By: @user <commit-sha>
#     Plans: PLAN-NNN
#     Scope:
#       - .claude/path/one.md
#     <!-- END SIGNED SCOPE -->
#
#     Status: ... (lifecycle text outside markers, ignored by parser)
#
# Parser tier-prioritizes: if markers present, parse Scope: ONLY from
# inside the marker region; if markers absent (legacy 44 sentinels at
# 2026-05-04), fall back to existing _SCOPE_HEADER_RE parser. No env
# flag — auto-detected by marker presence. Backward-compatible by
# construction.
#
# The GPG `.asc` continues to cover the whole file. Any tamper of any
# byte (markers, scope, lifecycle, anywhere) breaks the signature; the
# markers add only parser-side disambiguation, not new crypto authority.
#
# ReDoS-safety: anchored regex; non-greedy `.*?` bounded by END marker;
# 64KiB length cap on text before regex invocation (matches existing
# 4096-byte MCP path cap pattern at line ~205).
_SCOPE_MARKER_RE = re.compile(
    r"<!--\s*BEGIN\s+SIGNED\s+SCOPE\s*-->\s*\n(.*?)\n\s*<!--\s*END\s+SIGNED\s+SCOPE\s*-->",
    flags=re.DOTALL,
)
_SCOPE_MARKER_CAP_BYTES = 64 * 1024


def _parse_scope_paths_from_text(scope_text: str) -> "Set[str]":
    """Extract declared canonical paths from a Scope block.

    PLAN-064 Option D — extracted helper used by both Tier-1 (marker
    region) and Tier-2 (legacy `_SCOPE_HEADER_RE`) parser paths.

    The Scope block extends from the `Scope` header line to the first
    top-level continuation header (Effective:, Plans:, Rationale,
    Authorization source:, Anchor commit:, a re-encountered
    `Approved-By:`) or markdown horizontal rule (---, ***, ___) or
    end-of-text. Sub-headers within Scope (lines ending with `:` that
    are NOT in the terminator set) are silently skipped.
    """
    import os as _os
    declared_paths: Set[str] = set()
    scope_header = _SCOPE_HEADER_RE.search(scope_text)
    if not scope_header:
        return declared_paths
    post = scope_text[scope_header.end():]
    for line in post.splitlines():
        if _SCOPE_TERMINATOR_RE.match(line) or _SCOPE_HR_RE.match(line):
            break
        m = re.match(r"\s*-\s*(\S+)", line)
        if not m:
            # Blank line or sub-header (e.g. "Hook code (PLAN-052):") —
            # keep collecting; only the explicit terminators stop us.
            continue
        raw = m.group(1)
        # PLAN-024 F-sec-003 P1 fix: reject any control-char in scope
        # entries (bidi, null, ANSI escape, etc.) before normalization.
        if any(ord(c) < 0x20 for c in raw):
            continue
        # Normalize `./foo/bar` -> `foo/bar` and strip any ending
        # separator so sentinel-declared paths match target_rel
        # resolution consistently.
        normalized = _os.path.normpath(raw).replace(_os.sep, "/")
        if normalized == ".":
            continue
        declared_paths.add(normalized)
    return declared_paths


def _emit_allow(system_message: Optional[str] = None) -> str:
    # Claude Code hook schema: top-level "allow" is NOT valid.
    # Emit empty {} or {"systemMessage": ...}.
    out: dict = {}
    if system_message:
        out["systemMessage"] = system_message
    return json.dumps(out, ensure_ascii=False)


def _emit_persona_coverage_synthesized(rel_path: str) -> None:
    """PLAN-106 Wave C — emit persona_coverage_synthesized at sentinel-approved
    canonical-edit allow path.

    Attribution policy:
      archetype = env CEO_ACTIVE_ARCHETYPE if in closed-enum, else
                  "code-reviewer" (canonical-edit sentinel chain is
                  the code-review surface per ADR-010).
      task_type = "review" (sentinel approval is a review act).
      cell_id   = sha256[:8](archetype + ":" + task_type)
      source    = "canonical_edit"

    Best-effort; fail-open on any exception. Bypass via
    ``CEO_PERSONA_COVERAGE_EMIT=0``.
    """
    env = os.environ
    if (env.get("CEO_PERSONA_COVERAGE_EMIT") or "").strip() == "0":
        return
    try:
        import hashlib as _hl
        import unicodedata as _uc
        from _lib import audit_emit as _audit_emit_pc  # noqa: E402

        # Closed enum check (mirrors audit_emit:_PERSONA_COVERAGE_ARCHETYPES).
        archetypes_ok = {
            "code-reviewer", "security-engineer", "qa-architect",
            "threat-detection-engineer",
        }
        raw = (env.get("CEO_ACTIVE_ARCHETYPE") or "").strip().lower()
        # NFKC fold to defeat full-width injection in env var
        raw = _uc.normalize("NFKC", raw)
        archetype = raw if raw in archetypes_ok else "code-reviewer"
        task_type = "review"
        cell_input = f"{archetype}:{task_type}".encode("utf-8")
        cell_id = _hl.sha256(cell_input).hexdigest()[:8]

        _audit_emit_pc.emit_generic(
            "persona_coverage_synthesized",
            archetype=archetype,
            task_type=task_type,
            cell_id=cell_id,
            source="canonical_edit",
        )
    except Exception:  # noqa: BLE001 — fail-open, never block edit
        return


def _emit_block(reason: str) -> str:
    return json.dumps(
        {"decision": "block", "reason": reason}, ensure_ascii=False
    )


def _scan_skill_content_unicode(content: str, *, surface: str, env=None):
    """PLAN-133 A2 — pure invisible-unicode guard for SKILL.md content.

    ``surface`` is the closed-enum origin ("skill_write" | "skill_read"). Default-OFF;
    emits invisible_unicode_blocked on both advisory + enforced paths. Returns a
    block-reason string when enforced AND a detection fires, else None. Fail-open.
    """
    try:
        from _lib import spec_context_sanitizer as _scs  # noqa: E402
    except Exception:  # pragma: no cover - fail-open
        return None
    try:
        if not content:
            return None
        src_env = env if env is not None else os.environ
        if (src_env.get("CEO_SOTA_DISABLE") or "").strip() == "1":
            enforce = False
        else:
            enforce = (src_env.get("CEO_UNICODE_HARDBLOCK") or "").strip() == "1"
            # Prefer the trusted_env snapshot when available (mirror A1/§5b).
            try:
                from _lib import trusted_env as _te  # noqa: E402
                _snap = _te.get_trusted("CEO_UNICODE_HARDBLOCK")
                if _snap is not None:
                    enforce = (_snap or "").strip() == "1"
            except Exception:  # pragma: no cover
                pass

        result = _scs.sanitize(content)
        count = _scs.invisible_unicode_count(result)
        if count <= 0:
            return None
        unicode_class = _scs.classify_invisible_unicode(result)

        try:
            from _lib import audit_emit as _ae  # noqa: E402
            _ae.emit_generic(
                "invisible_unicode_blocked",
                surface=surface,
                unicode_class=unicode_class,
                char_count=int(count),
                enforced=1 if enforce else 0,
            )
        except Exception:  # pragma: no cover - fail-open
            pass

        if not enforce:
            return None
        return (
            "CANONICAL-EDIT-BLOCKED: invisible_unicode_blocked: this SKILL.md "
            f"content contains {count} invisible/smuggling character(s) "
            f"(class={unicode_class}). Skill content is loaded into the model as "
            "trusted instructions; hidden control/bidi/Tag-block characters are "
            "rejected fail-CLOSED. Remove them. To run advisory-only, unset "
            "CEO_UNICODE_HARDBLOCK."
        )
    except Exception:  # pragma: no cover - fail-open invariant
        return None


def _staged_content(event) -> Optional[str]:
    """PLAN-133 A2 — best-effort extraction of the NEW SKILL.md content from a
    staged Edit/Write/MultiEdit ``tool_input``.

    At PreToolUse the new content is in the tool_input, NOT yet on disk. Reads the
    standard adapter keys (Write ``content``; Edit ``new_string``; MultiEdit
    ``edits[].new_string`` concatenated). Returns None when nothing can be extracted
    (fail-OPEN — the caller then never blocks). Never raises.
    """
    try:
        tool_input = getattr(event, "tool_input", None) or {}
        if not isinstance(tool_input, dict):
            return None
        # Write tool — full file content.
        content = tool_input.get("content")
        if isinstance(content, str) and content:
            return content
        # Edit tool — single replacement string.
        new_string = tool_input.get("new_string")
        if isinstance(new_string, str) and new_string:
            return new_string
        # MultiEdit tool — concatenate per-edit new strings.
        edits = tool_input.get("edits")
        if isinstance(edits, list):
            parts: List[str] = []
            for ed in edits:
                if isinstance(ed, dict):
                    ns = ed.get("new_string")
                    if isinstance(ns, str) and ns:
                        parts.append(ns)
            if parts:
                return "\n".join(parts)
    except Exception:  # pragma: no cover - fail-open
        return None
    return None


# PLAN-025 F-perf-004 fast-path — precomputed set of top-level path
# segments that every _CANONICAL_GUARDS entry starts with. Any path NOT
# starting with one of these prefixes is non-canonical in O(1) without
# running fnmatch 30+ times. Preserves semantics — every guard pattern
# starts with one of these prefixes by construction.
_CANONICAL_PREFIXES = frozenset({
    ".claude", ".github", "scripts", "SPEC", "PROTOCOL.md",
    # PLAN-155 Wave 3b (SENT-CX-E) — first-segment prefixes for the Codex
    # kill-switch surface. Without these three the fast-path bail-out in
    # `_is_canonical` returns False BEFORE the new `_CANONICAL_GUARDS`
    # entries are ever consulted (the guard would be dead — the S254
    # dead-gate class). Every kill-switch guard pattern starts with one of
    # these by construction (`.codex/*`, `requirements.toml`, `AGENTS.md`).
    ".codex", "requirements.toml", "AGENTS.md",
})


def _is_canonical(path_str: str, repo_root: Path) -> bool:
    """True if path_str matches one of the canonical guard patterns.

    PLAN-025 F-perf-004: fast-path prefix check bails out on the vast
    majority of non-canonical paths without invoking fnmatch.
    """
    p = Path(path_str)
    try:
        rel = p.resolve().relative_to(repo_root.resolve())
    except (ValueError, OSError):
        # Path is outside repo root → not canonical.
        return False
    rel_str = str(rel).replace(os.sep, "/")
    # Fast path: check the first path segment against known prefixes.
    first_seg = rel_str.split("/", 1)[0]
    if first_seg not in _CANONICAL_PREFIXES:
        return False
    for pattern in _CANONICAL_GUARDS:
        if _fnmatch_segments(rel_str, pattern):
            return True
    return False


def _fnmatch_segments(path: str, pattern: str) -> bool:
    """Segment-wise glob matcher.

    - ``*`` matches exactly one path segment (any non-slash content).
    - ``**`` matches zero or more path segments (Sprint 9 amendment).
    - Literal segments must match exactly.
    """
    p_parts = path.split("/")
    pat_parts = pattern.split("/")
    return _match_segments(p_parts, pat_parts)


def _match_segments(p_parts: List[str], pat_parts: List[str]) -> bool:
    """Recursive glob with ``**`` zero-or-more support.

    Per-segment patterns support full fnmatch semantics (so
    patterns like *.py, *.yaml, or ADR-*.md match one
    segment with a wildcard stem). ** still means zero-or-more
    segments.
    """
    if not pat_parts:
        return not p_parts
    head, rest = pat_parts[0], pat_parts[1:]
    if head == "**":
        # Zero-or-more: try consuming 0..len(p_parts) segments
        for i in range(len(p_parts) + 1):
            if _match_segments(p_parts[i:], rest):
                return True
        return False
    if not p_parts:
        return False
    # Bare-* is equivalent to fnmatch "*", but we keep the explicit
    # branch for readability. fnmatch.fnmatchcase does case-sensitive
    # glob on a single segment (no "/" traversal).
    if head == "*" or fnmatch.fnmatchcase(p_parts[0], head):
        return _match_segments(p_parts[1:], rest)
    return False


def _find_sentinels(repo_root: Path) -> List[Path]:
    """Find all valid Architect sentinel files in the repo.

    PLAN-045 Wave 1 F-01-04: reject any sentinel that is a symlink or
    whose immediate parent directory is a symlink. Mirrors the
    ``_validate_skill_reference`` hardening pattern (ADR-051 sub-check
    5). Silently drops symlinked entries — an attacker who plants
    ``PLAN-EVIL/architect/round-1/approved.md -> /tmp/evil`` no longer
    gets their sentinel considered.
    """
    base = repo_root / ".claude" / "plans"
    if not base.is_dir():
        return []
    # PLAN-085 Wave E.1 — explicit pattern union + grandfather allowlist
    # (R1 Sec-3). NO catch-all wildcard. Novel architect/* subdirs not
    # listed below are treated as ORPHAN, NOT TRUSTED.
    _PATTERNS = (
        "PLAN-*/architect/round-*/approved.md",
        "PLAN-*/architect/wave-0a/approved.md",      # PLAN-083 grandfather
        "PLAN-*/architect/wave-0b/approved.md",      # PLAN-083 grandfather
        "PLAN-*/architect/wave-1-2/approved.md",     # PLAN-083 grandfather
        "PLAN-*/architect/wave-minus-1/approved.md", # PLAN-083 grandfather
        "PLAN-*/staging/review/approved.md",         # PLAN-083 grandfather
        "PLAN-*/approved.md",                        # plan-root sentinels
        "PLAN-*/wave-*-approved.md",                 # S109 wave-N-approved.md
        "PLAN-*/approved-amendment-*.md",            # E.5 amendment files
        "PLAN-*/audit-v2/architect/round-*/approved.md",  # PLAN-044 audit-v2 historical
    )
    seen: set = set()
    candidates: list = []
    for pat in _PATTERNS:
        for c in sorted(base.glob(pat)):
            if c not in seen:
                seen.add(c)
                candidates.append(c)
    safe: List[Path] = []
    for p in candidates:
        try:
            if p.is_symlink():
                continue
            if p.parent.is_symlink():
                continue
            if p.parent.parent.is_symlink():
                continue
        except OSError:
            continue
        safe.append(p)
    return safe


# ---------------------------------------------------------------------------
# PLAN-094 Wave C — sentinel verification session cache (R-041)
# ---------------------------------------------------------------------------
# Module-scope ONLY (NEVER file-backed; PLAN-094 §3 Wave C C.1).
# Process death = cache loss (eliminates R5 stale-cache-survives-crash).
# Composite key — Codex iter-1 P0 fold: target_rel included so cache value
# (grant decision dependent on target_rel) is correct on hit; sha256_full
# transitively covers signer changes via .asc bytes (signer rotation
# window risk acknowledged + accepted trade-off per design draft §8).

_SENTINEL_CACHE_FORMAT_VERSION = 2  # bumped at iter-1 P0 fix (target_rel added)
_SENTINEL_VERIFY_CACHE: Dict[
    Tuple[str, int, int, int, str, str, int], bool
] = {}
_SENTINEL_CACHE_HITS = 0
_SENTINEL_CACHE_MISSES = 0


def _sentinel_cache_disabled() -> bool:
    """Kill-switch CEO_SENTINEL_SESSION_CACHE_DISABLED=1 bypasses cache."""
    return os.environ.get("CEO_SENTINEL_SESSION_CACHE_DISABLED", "") == "1"


def _compute_sentinel_cache_key(
    sentinel_path: Path,
    target_rel: str = "",
) -> Optional[Tuple[str, int, int, int, str, str, int]]:
    """Return composite key or None on stat/read failure (don't cache errors).

    iter-1 P0 fix: target_rel included so cache value (grant decision
    dependent on target_rel) is correct on hit.
    """
    try:
        st = sentinel_path.stat()
        content = sentinel_path.read_bytes()
    except OSError:
        return None
    return (
        str(sentinel_path),
        st.st_ino,
        st.st_mtime_ns,
        st.st_size,
        hashlib.sha256(content).hexdigest(),
        target_rel,
        _SENTINEL_CACHE_FORMAT_VERSION,
    )


def sentinel_cache_stats() -> Dict[str, int]:
    """Return session-scoped cache counters (skill_cache_stats sibling)."""
    return {
        "hit_count": _SENTINEL_CACHE_HITS,
        "miss_count": _SENTINEL_CACHE_MISSES,
        "size": len(_SENTINEL_VERIFY_CACHE),
    }


def _sentinel_grants_path(sentinel_path: Path, target_rel: str) -> bool:
    """Check whether a sentinel file grants the given target path.

    PLAN-045 Wave 1 P0-01: verification is now two-tiered:

    1. **Plaintext ``Approved-By:`` line** — existing fast check (visual
       Owner signoff marker).
    2. **Detached GPG signature** at ``<sentinel>.asc`` — verified
       against ``.claude/sentinel-signers.txt`` allowlist via
       ``_lib.gpg_verify.verify_detached``. Fail-CLOSED on: missing
       .asc, bad signature, signer fpr not in allowlist, empty
       allowlist.

    **Environment bypass (interim, per ADR-010 amendment)**: setting
    ``CEO_SENTINEL_UNLOCK=<plan-id>`` + ``CEO_SENTINEL_UNLOCK_ACK=I-ACCEPT``
    in the parent shell short-circuits the .asc requirement. This is a
    dual-auth mechanism mirroring the arbitration-kernel escape hatch;
    a sub-agent cannot forge the env vars. The override is logged via
    ``veto_triggered(reason_code=sentinel_unlock_used)``.

    The sentinel must contain:
    1. A valid ``Approved-By: @<handle> <commit-sha>`` line
    2. A ``Scope:`` block listing the target path (one bullet per line)
    3. A sibling ``<sentinel>.asc`` detached GPG signature (unless env
       override is set)
    """
    # PLAN-094 Wave C — session cache fast-path before expensive GPG verify.
    # Cache key (iter-1 P0 fix): (path, inode, mtime_ns, file_size, sha256_full,
    # target_rel, fmt_version). Cache value: granted (bool). env_override path
    # bypasses cache (CEO_SENTINEL_UNLOCK semantic: must re-verify).
    global _SENTINEL_CACHE_HITS, _SENTINEL_CACHE_MISSES
    _cache_key = None
    _unlock_reason_pre = (os.environ.get("CEO_SENTINEL_UNLOCK") or "").strip()
    _unlock_ack_pre = (os.environ.get("CEO_SENTINEL_UNLOCK_ACK") or "").strip()
    _env_override_pre = bool(
        _unlock_reason_pre
        and _unlock_ack_pre == "I-ACCEPT"
        and re.match(r'^(ADR-\d{3,4}|PLAN-\d{3})-[a-z0-9-]{3,100}$', _unlock_reason_pre)
    )
    if not _sentinel_cache_disabled() and not _env_override_pre:
        _cache_key = _compute_sentinel_cache_key(sentinel_path, target_rel)
        if _cache_key is not None:
            _cached = _SENTINEL_VERIFY_CACHE.get(_cache_key)
            if _cached is not None:
                _SENTINEL_CACHE_HITS += 1
                return _cached
            _SENTINEL_CACHE_MISSES += 1

    try:
        text = sentinel_path.read_text(encoding="utf-8")
    except OSError:
        return False

    # Check plaintext signature marker first (cheap).
    if not _APPROVED_BY_RE.search(text):
        return False

    # PLAN-045 Wave 1 P0-01: verify detached GPG signature.
    env = os.environ
    unlock_reason = (env.get("CEO_SENTINEL_UNLOCK") or "").strip()
    unlock_ack = (env.get("CEO_SENTINEL_UNLOCK_ACK") or "").strip()
    env_override = bool(
        unlock_reason
        and unlock_ack == "I-ACCEPT"
        and re.match(r'^(ADR-\d{3,4}|PLAN-\d{3})-[a-z0-9-]{3,100}$', unlock_reason)  # PLAN-086 Wave I.1 — ADR-119 tightening
    )
    if not env_override:
        if _gpg_verify is None:
            # _lib.gpg_verify is unavailable — fail-CLOSED. No sentinel
            # can grant canonical edits without the verification helper.
            return False
        sig_path = sentinel_path.with_name(sentinel_path.name + ".asc")
        # PLAN-089 Wave C.4 — dual-rail signer verification (ADR-121).
        # First-class path: legacy `.claude/sentinel-signers.txt` (existing).
        # Defense-in-depth: if YAML registry exists, re-check fingerprint via
        # _lib.sentinel_signers + bootstrap-SHA pin. Either rail rejecting
        # → fail-CLOSED. Post-GENESIS (_BOOTSTRAP_REGISTRY_SHA256 set),
        # parse/hash failure → fail-CLOSED (R2 Codex iter-1 Q5+Q7 fold);
        # pre-GENESIS (None), parse failure → legacy-only fallback.
        ok, _fpr, _reason = _gpg_verify.verify_detached(
            sentinel_path,
            sig_path,
            allowlist_path=_SENTINEL_SIGNERS_FILE,
            timeout=15.0,
        )
        if not ok:
            return False
        if (
            _sentinel_signers is not None
            and _SENTINEL_SIGNERS_REGISTRY_YAML.exists()
            and _fpr
        ):
            _post_genesis = _BOOTSTRAP_REGISTRY_SHA256 is not None
            try:
                # Bootstrap SHA pin verification (post-GENESIS only).
                if _post_genesis:
                    import hashlib as _hashlib
                    _yaml_bytes = _SENTINEL_SIGNERS_REGISTRY_YAML.read_bytes()
                    _computed_sha = _hashlib.sha256(_yaml_bytes).hexdigest()
                    if _computed_sha != _BOOTSTRAP_REGISTRY_SHA256:
                        try:
                            from _lib import audit_emit as _audit_emit
                            if hasattr(_audit_emit, "emit_sentinel_signer_quorum_failed"):
                                _audit_emit.emit_sentinel_signer_quorum_failed(
                                    key_id=_fpr,
                                    reason="bootstrap_sha_mismatch",
                                    source="canonical_edit_bootstrap_pin",
                                )
                        except Exception:  # pragma: no cover
                            pass
                        return False
                _registry = _sentinel_signers.load_registry(
                    _SENTINEL_SIGNERS_REGISTRY_YAML
                )
                _valid, _why = _sentinel_signers.is_valid_signer(
                    _fpr, registry=_registry
                )
                # PLAN-113 WIRE-AUDIT: emit quorum_attempted on EVERY
                # signer verification attempt (success + failure).
                try:
                    from _lib import audit_emit as _audit_emit_qa
                    if hasattr(_audit_emit_qa, "emit_sentinel_signer_quorum_attempted"):
                        _audit_emit_qa.emit_sentinel_signer_quorum_attempted(
                            distinct_signers=1,
                            threshold_required=1,
                            outcome="valid" if _valid else "failed",
                            source="canonical_edit_sentinel_verify",
                        )
                except Exception:  # pragma: no cover
                    pass
                if not _valid:
                    try:
                        from _lib import audit_emit as _audit_emit
                        if hasattr(_audit_emit, "emit_sentinel_signer_quorum_failed"):
                            _audit_emit.emit_sentinel_signer_quorum_failed(
                                key_id=_fpr,
                                reason=_why,
                                source="canonical_edit_sentinel_verify",
                            )
                    except Exception:  # pragma: no cover
                        pass
                    return False
            except Exception:  # pragma: no cover
                # Pre-GENESIS (constant None) — degrade to legacy-only.
                # Post-GENESIS — fail-CLOSED (R2 Codex Q7 fold).
                if _BOOTSTRAP_REGISTRY_SHA256 is not None:
                    return False

    # Parse Scope: block.
    #
    # PLAN-064 Option D (DIM-13 closure, 2026-05-04) — tier-prioritized
    # parser:
    #   Tier 1: if HTML-comment markers <!-- BEGIN SIGNED SCOPE --> /
    #           <!-- END SIGNED SCOPE --> are present, parse Scope: ONLY
    #           from text between those markers. Lifecycle text outside
    #           the markers is ignored for grant decisions; it is
    #           documentation. The GPG `.asc` continues to cover the
    #           whole file (any tamper breaks the signature).
    #   Tier 2: if markers absent (legacy 44 sentinels at 2026-05-04),
    #           fall back to existing _SCOPE_HEADER_RE parser path
    #           below. No env flag — auto-detected.
    #
    # PLAN-044 audit-v2 C6-P0-04 (Tier 2 fallback) — supports two
    # on-disk formats:
    #
    # Format A (PLAN-050 round-17 era — single contiguous bullet list):
    #
    #     Scope:
    #       - .claude/path/one.md
    #       - .claude/path/two.md
    #
    # Format B (Session 67 mega-sentinel — categorized with sub-headers
    # and blank lines between groups):
    #
    #     Scope (24 canonical paths):
    #
    #     ADR canonical promotions (9 files, all from staging):
    #     - .claude/adr/ADR-083-...
    #     - .claude/adr/ADR-084-...
    #
    #     Hook code (PLAN-052):
    #     - .claude/hooks/_lib/foo.py (new)
    #     - .claude/hooks/check_bar.py (new)
    #
    # The Scope block extends from the `Scope` header line to the first
    # top-level continuation header (`Effective:`, `Plans:`, `Rationale`,
    # `Authorization source:`, `Anchor commit:`, a re-encountered
    # `Approved-By:`) or markdown horizontal rule (`---`, `***`, `___`)
    # or end-of-file. Sub-headers within Scope (lines ending with `:`
    # that are NOT in the terminator set) are silently skipped.

    # Tier 1 — lexical scope markers (PLAN-064 Option D).
    # Length cap before regex invocation (ReDoS defense).
    declared_paths: Set[str] = set()
    if len(text) <= _SCOPE_MARKER_CAP_BYTES:
        marker_match = _SCOPE_MARKER_RE.search(text)
        if marker_match:
            scope_region = marker_match.group(1)
            declared_paths = _parse_scope_paths_from_text(scope_region)
            # If markers present but no scope paths extracted (malformed
            # interior), fail-CLOSED rather than silently fall through
            # to Tier 2 — markers are an explicit Owner intent signal.
            if not declared_paths:
                return False
            granted = target_rel in declared_paths
            if granted and env_override:
                _emit_unlock_audit(target_rel, unlock_reason)
            # PLAN-094-FOLLOWUP Wave C-tier1 — store Tier-1 grant decision
            # in cache (parity with Tier-2 store path below). env_override
            # path is NOT cached (mirrors Tier-2 invariant).
            if (
                _cache_key is not None
                and not env_override
                and not _sentinel_cache_disabled()
            ):
                _SENTINEL_VERIFY_CACHE[_cache_key] = granted
            return granted

    # Tier 2 — legacy _SCOPE_HEADER_RE parser (no markers in file).
    declared_paths = _parse_scope_paths_from_text(text)
    if not declared_paths:
        return False

    granted = target_rel in declared_paths
    if granted and env_override:
        _emit_unlock_audit(target_rel, unlock_reason)

    # PLAN-094 Wave C — store result into module-scope cache (NEVER file-backed).
    # env_override path is NOT cached (semantic: unlock env must always re-verify
    # to honor freshly-regenerated .asc files even when bytes are unchanged).
    if (
        _cache_key is not None
        and not env_override
        and not _sentinel_cache_disabled()
    ):
        _SENTINEL_VERIFY_CACHE[_cache_key] = granted

    return granted


def _emit_unlock_audit(target_rel: str, unlock_reason: str) -> None:
    """Best-effort audit emission for sentinel env-override grants.

    Session 75 Codex Finding 8 closure (extracted helper for PLAN-064
    Option D Tier-1/Tier-2 DRY): docstring promised
    `veto_triggered(reason_code=sentinel_unlock_used)` event when the
    env-var override path grants a canonical edit. Emission failures
    never block (advisory).
    """
    try:
        from _lib import audit_emit as _audit_emit_unlock
        _audit_emit_unlock.emit_veto_triggered(
            hook="check_canonical_edit",
            reason_code="sentinel_unlock_used",
            reason_preview=(
                f"sentinel env-override granted edit to {target_rel}; "
                f"reason={unlock_reason!r}"
            ),
            blocked_tool="Edit|Write|MultiEdit",
            caller=os.environ.get("CLAUDE_AGENT_NAME", "ceo"),
            session_id=os.environ.get("CLAUDE_SESSION_ID", ""),
            project=os.environ.get("CLAUDE_PROJECT_DIR", ""),
        )
    except Exception:
        pass  # advisory; emission failure never blocks


def decide(
    *,
    file_path: str,
    repo_root: Path,
) -> str:
    """Pure decision function.

    Returns the JSON payload to write to stdout.
    """
    if not file_path:
        return _emit_allow()

    if not _is_canonical(file_path, repo_root):
        return _emit_allow()

    # Resolve to repo-relative form for sentinel matching
    p = Path(file_path)
    try:
        rel = str(p.resolve().relative_to(repo_root.resolve())).replace(os.sep, "/")
    except (ValueError, OSError):
        return _emit_allow()

    sentinels = _find_sentinels(repo_root)
    for sentinel in sentinels:
        if _sentinel_grants_path(sentinel, rel):
            # PLAN-106 Wave C — persona coverage emit at canonical-edit
            # sentinel-approved allow path.
            _emit_persona_coverage_synthesized(rel_path=rel)
            return _emit_allow(
                system_message=(
                    f"CANONICAL-EDIT: allowed via sentinel "
                    f"{sentinel.relative_to(repo_root)}"
                )
            )

    return _emit_block(
        reason=(
            f"CANONICAL-EDIT-BLOCKED: '{rel}' is a canonical governance "
            "path. Edits require an Owner-signed sentinel at "
            ".claude/plans/PLAN-NNN/architect/round-N/approved.md with "
            f"this path declared in the Scope: block. See ADR-010."
        )
    )


def _audit_block(rel: str, sentinels_count: int) -> None:
    """Best-effort emit of veto_triggered event. Never raises."""
    try:
        from _lib import audit_emit
        audit_emit.emit_veto_triggered(
            hook="check_canonical_edit",
            reason_code="canonical_edit_unsigned",
            reason_preview=(
                f"blocked edit to {rel}; {sentinels_count} sentinel(s) checked, "
                "none grant this path"
            ),
            blocked_tool="Edit|Write|MultiEdit",
            project=os.environ.get("CLAUDE_PROJECT_DIR") or "",
        )
    except Exception:
        return


def _emit_legacy_decision_json(out: str, adapter, event=None) -> None:
    """Emit a pre-built legacy (Claude-shaped) decision JSON string through
    the resolved host adapter (PLAN-155 Wave 1 dispatch seam, debate A1).

    ``decide()`` returns pre-built JSON strings for the legacy contract.
    Under the default/claude adapter the string is written RAW + newline —
    byte-identical to the pre-seam hook. Under any other host adapter the
    string is parsed back into a neutral ``Decision`` and re-emitted via
    the adapter's ``emit_decision`` WITH the parsed NormalizedEvent
    (host egress shape is EXPLICIT-only: a host-wire event stamps
    ``raw_payload['ceo_host_wire']`` and the codex adapter emits
    ``hookSpecificOutput.permissionDecision``), so a deny reaches the
    host in the shape its wire enforces (a raw Claude-shaped line is
    foreign JSON on the codex wire → silent fail-open → the S254
    dead-gate class).
    """
    adapter_basename = (getattr(adapter, "__name__", "") or "").rsplit(".", 1)[-1]
    if adapter_basename == "claude":
        sys.stdout.write(out + "\n")
        return
    from _lib import contract as _contract  # noqa: PLC0415
    parsed = json.loads(out)
    adapter.emit_decision(
        _contract.Decision(
            allow=(parsed.get("decision") != "block"),
            reason=parsed.get("reason"),
            system_message=parsed.get("systemMessage"),
            message=parsed.get("message"),
        ),
        event=event,
    )


def _adapter_emit(adapter, decision, event=None) -> None:
    """Emit a neutral ``Decision`` through the resolved host adapter.

    Claude path: the historical two-arg call — byte-identical output
    (``claude.py:emit_decision`` does not take ``event=``). Any other
    resolved adapter (codex host mode, ``_FailClosedAdapter``) receives
    the parsed NormalizedEvent so the egress shape follows the wire that
    produced it and the debate-A2 coherence override can fire.
    """
    adapter_basename = (getattr(adapter, "__name__", "") or "").rsplit(".", 1)[-1]
    if adapter_basename == "claude":
        adapter.emit_decision(decision)
        return
    adapter.emit_decision(decision, event=event)


def main() -> int:
    """Hook entry point.

    PLAN-006 Phase 1 migration (ADR-014): uses Adapter Layer
    `read_event()` / `emit_decision()`. Byte-identical output.

    PLAN-155 Wave 1 (debate A1, ratified seam option b): the adapter is
    resolved ONCE per invocation through the shared seam
    ``_lib.adapters.resolve()``. Under ``CEO_HOOK_ADAPTER`` unset/"claude"
    the seam returns the claude adapter module and every downstream byte
    is identical to the pre-seam hook (the regression bar). The debate-A2
    coherence gate (explicitly-set-but-unresolvable ``CEO_HOOK_ADAPTER``
    → INPUT class per PLAN-152 C4) lives INSIDE ``resolve()``, which
    fails CLOSED by returning a ``_FailClosedAdapter`` whose egress
    ALWAYS denies in BOTH harness vocabularies (top-level
    ``decision: block`` + ``hookSpecificOutput.permissionDecision:
    deny``) with a stderr + audit breadcrumb — never a silent fallback
    to the claude adapter. Non-claude adapters additionally receive the
    parsed event at egress (``_adapter_emit``) so the host wire shape
    and the coherence override are event-driven, never latched.
    """
    from _lib import adapters as _adapters  # noqa: E402
    from _lib import contract as _contract  # noqa: E402

    _adapter = _adapters.resolve()

    try:
        event = _adapter.read_event(phase="PreToolUse")
    except Exception:
        _adapter.emit_decision(_contract.allow())
        return 0

    if event.parse_error:
        _adapter.emit_decision(_contract.allow())
        return 0

    # PLAN-065 Layer A (S81-tris gap closure, 2026-05-04):
    # When tool_name is mcp__*, the adapter's `event.file_path` field
    # may be empty (custom MCP tools don't use the standard
    # Edit/Write/MultiEdit `file_path` key). Inspect tool_input directly
    # for write-shape parameters and resolve all candidate paths.
    # Each candidate is gated independently; if ANY candidate is
    # canonical without sentinel coverage, block.
    tool_name = (event.tool_name or "").strip()
    candidate_paths: List[str] = []
    if event.file_path:
        candidate_paths.append(event.file_path)
    if tool_name.startswith("mcp__"):
        candidate_paths.extend(
            _extract_mcp_target_paths(event.tool_input or {})
        )
    # PLAN-155 Wave 1 (S265 pair-rail P1#3): a codex apply_patch can touch
    # MULTIPLE files; the host adapter surfaces every path (incl. rename
    # targets) as tool_input['apply_patch_paths']. Gate them ALL — a
    # benign first op must not smuggle a later op into a guarded path.
    # Absent under Claude Code (key never present → byte-identical).
    if isinstance(event.tool_input, dict):
        for _pp in event.tool_input.get("apply_patch_paths") or []:
            if isinstance(_pp, str) and _pp and _pp not in candidate_paths:
                candidate_paths.append(_pp)

    if not candidate_paths:
        _adapter_emit(_adapter, _contract.allow(), event)
        return 0

    # Use the first canonical path for legacy file_path-keyed downstream
    # logic, but iterate all candidates for canonical detection.
    file_path = candidate_paths[0]

    repo_root = Path(os.environ.get("CLAUDE_PROJECT_DIR") or os.getcwd())

    # Layer A: if ANY candidate is canonical, gate using that canonical
    # path (most restrictive policy). Historically mcp__*-only; PLAN-155
    # extends the scan to any multi-candidate event (apply_patch multi-
    # file, S265 P1#3). Single-candidate events (every Claude Code
    # Edit/Write) skip the loop body outcome-identically.
    if tool_name.startswith("mcp__") or len(candidate_paths) > 1:
        for candidate in candidate_paths:
            try:
                if _is_canonical(candidate, repo_root):
                    file_path = candidate
                    break
            except Exception:
                continue

    try:
        out = decide(file_path=file_path, repo_root=repo_root)
    except Exception as e:
        # PLAN-045 Wave 1 F-01-07: fail-CLOSED for canonical paths.
        # Previously any exception fell through to allow; now an edit
        # targeting a confirmed canonical path blocks with
        # ``canonical_edit_hook_fault``. Non-canonical edits keep the
        # fail-open contract so a hook bug doesn't brick the session
        # on benign writes.
        print(
            f"[check_canonical_edit] FATAL: {type(e).__name__}: {e}",
            file=sys.stderr,
        )
        try:
            is_canonical = _is_canonical(file_path, repo_root)
        except Exception:
            is_canonical = False
        if is_canonical:
            _emit_legacy_decision_json(
                _emit_block(
                    reason=(
                        "CANONICAL-EDIT-BLOCKED: hook fault on canonical "
                        f"path; {type(e).__name__}: {e}. PLAN-045 F-01-07."
                    )
                ),
                _adapter,
                event,
            )
            return 0
        _adapter_emit(_adapter, _contract.allow(), event)
        return 0

    # On block, emit veto event (best-effort)
    parsed = json.loads(out)
    if parsed.get("decision") == "block":
        try:
            rel = str(Path(file_path).resolve().relative_to(repo_root.resolve())).replace(os.sep, "/")
        except Exception:
            rel = file_path
        _audit_block(rel, len(_find_sentinels(repo_root)))

    # PLAN-133 A2 — invisible-unicode guard at SKILL.md authoring. Only on a
    # would-allow canonical SKILL.md edit (so we never relax the sentinel gate;
    # we can only ADD a fail-CLOSED block). Reads the staged tool_input content,
    # not disk. Default-OFF (CEO_UNICODE_HARDBLOCK=1). Fail-open.
    if parsed.get("decision") != "block" and (
        file_path.endswith("/SKILL.md") or file_path.endswith("SKILL.md")
    ):
        try:
            new_content = getattr(event, "new_content", None) or _staged_content(event)
        except Exception:  # pragma: no cover - fail-open
            new_content = None
        if new_content:
            _uni = _scan_skill_content_unicode(
                new_content, surface="skill_write"
            )
            if _uni is not None:
                _adapter_emit(_adapter, _contract.block(_uni), event)
                return 0

    # `decide()` returns pre-built JSON strings for the legacy contract;
    # under the default/claude adapter the seam helper writes it directly
    # + newline (byte identity preserved); other host adapters re-shape it
    # on the parsed event's wire.
    _emit_legacy_decision_json(out, _adapter, event)
    return 0


if __name__ == "__main__":
    sys.exit(main())
