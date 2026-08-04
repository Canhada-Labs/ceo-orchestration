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
import subprocess  # PLAN162_FIX_S2 — session-anchor proof via git
import sys
import time  # PLAN162_FIX_1 — per-invocation wall-clock budget
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
    # ---- PLAN-156 Wave 3 (SENT-GK-E) — Grok kill-switch surface ----
    # Same class as the .codex surface above: under the Grok harness these
    # files ARE the rail's own disarm surface. An agent running under grok
    # that can rewrite `.grok/config.toml` (compat cells, leader mode) or
    # `.grok/sandbox.toml` (the council lane's OS-level containment)
    # disarms governance while the boot tripwire stays silent — the
    # circular-disarm gap. `.grok/hooks/` is guarded even though PLAN-156
    # deliberately ships NO live hooks there: a file we choose not to ship
    # is exactly the file an attacker would CREATE, and creating it
    # re-opens the double-fire that the single-surface decision closes.
    #
    # Why single-surface (OQ1, INVERTED by evidence — S269 probe P8): with
    # BOTH `.grok/hooks/` and the legacy `.claude/settings.json` present,
    # grok 0.2.93 fires EVERY hook TWICE on the same toolUseId, and neither
    # documented kill switch turns the legacy surface off at runtime —
    # `[compat.claude] hooks = false` in the project config is not even
    # read, and `GROK_CLAUDE_HOOKS_ENABLED=0` marks the hook `[disabled]`
    # in `grok inspect` while the runtime STILL fires it (probes
    # P8b/P8c/P8d; product-bug class on a 0.x). A double-fired audit-chain
    # append is an HMAC double-count + a filelock race, so the only sound
    # resolution is to arm exactly ONE surface. We arm the one grok reads
    # natively as legacy compat — the `.claude/settings.json` this
    # framework already ships — and guard `.grok/**` so nothing re-arms the
    # second one behind our back.
    #
    # KERNEL HARD-DENY (this guard list lives in _KERNEL_PATHS): extending
    # it requires CEO_KERNEL_OVERRIDE=PLAN-156-GROK-KILLSWITCH-GUARD-EXTENSION
    # AND CEO_KERNEL_OVERRIDE_ACK=I-ACCEPT in addition to the SENT-GK-E
    # sentinel (same double-gate as PLAN-155-CODEX-KILLSWITCH).
    ".grok/hooks/*.json",
    ".grok/hooks/**/*.json",
    ".grok/config.toml",
    ".grok/sandbox.toml",
    ".grok/rules/*.md",
    # ---- PLAN-156 Wave 3 (SENT-GK-E) — install-template settings ----
    # pair-rail R13: `templates/settings/settings.base.json` is the hook
    # REGISTRATION surface every new install inherits, and it carried the
    # same non-shim `check_codex_filewrite.py` registration the live
    # settings.json did — so fixing only the dogfood file would have left
    # every adopter fail-open under grok (both halves: no exit-2 mapping,
    # no block->deny rewrite). It is a fail-open-BEARING distribution
    # surface and belongs under the same sentinel gate as
    # `.claude/settings.json`, not merely under a CI meta-test.
    "templates/settings/settings.base.json",
    "templates/settings/*.json",
    # ---- PLAN-156 Wave 6 (SENT-GK-F) — cross-vendor council egress surface ----
    # `council-audit.js` OWNS the live external-lane egress: it invokes the
    # ADR-114 redactor, enforces the per-lane budget hard-kill, and carries
    # the no-CI fence. A later ORDINARY edit that stripped the redactor call
    # or the fence would transmit repo content to xAI/OpenAI UNREDACTED — so
    # the workflow AND the /council command that triggers it are guarded.
    # NOTE (verified): `.claude/workflows/` was NOT previously canonical-
    # guarded (only `.github/workflows/*` is); this closes that gap for the
    # egress-bearing workflow. The `.claude/commands/council.md` trigger is
    # guarded for the same reason — it is the operator entry point to egress.
    # KERNEL HARD-DENY (this guard list is in _KERNEL_PATHS): extending it
    # requires CEO_KERNEL_OVERRIDE=PLAN-156-COUNCIL-GUARD-EXTENSION AND
    # CEO_KERNEL_OVERRIDE_ACK=I-ACCEPT in addition to SENT-GK-F.
    #
    # PLAN-156-FOLLOWUP F3 (S270 live-fire finding, OQ1 Owner-ratified):
    # the exact-path entry guarded the INSTANCE, not the CLASS. A sibling
    # (or nested) workflow could carry the same external-lane egress and be
    # ordinary-writable — "a file we choose not to ship is exactly the file
    # an attacker would CREATE". The glob covers subdirectories too; `**`
    # matches zero or more segments in _fnmatch_segments (Sprint 9).
    # Cost accepted at ratification: authoring ANY .claude/workflows/*.js
    # becomes a sentinel ceremony.
    ".claude/workflows/**/*.js",
    ".claude/commands/council.md",
    # PLAN-165 p1-corrected (CX-1, S290): the night-mode posture-write
    # surface. The per-tool deny entries in settings.json close the
    # Edit/Write rail; THESE entries are the load-bearing rail for Bash —
    # check_bash_safety keys write-shaped (and -c/-e-body) command
    # references off this list, so without them
    # `echo '{...}' > settings.local.json` passes under acceptEdits with
    # the deny applied (the codex CX-1 refutation of the original p1).
    # Listing the WRITER script here also removes model-rail invocation
    # of the toggle (OQ1-redo, Owner-ratified 2026-08-03: presence =
    # only a human at the keyboard runs on/off, via `!` or a terminal).
    ".claude/settings.local.json",
    ".claude/state/night-mode.json",
    ".claude/scripts/night-mode.py",
    # PLAN162_FIX_3 (PLAN-162 findings #3 + #8, consensus C10) — guard the
    # files the guard itself TRUSTS. Both were guarded by NEITHER rail on
    # HEAD (verified: canonical=False AND kernel=False), which is what
    # separates them from finding #12 (that one at least has the kernel
    # hard-deny underneath).
    #
    #   1. `.claude/security/sentinel-signers-registry.yaml` — the ADR-121
    #      identity root read below in `_sentinel_grants_path`. An ordinary
    #      Edit silently disarmed half the dual signer rail.
    #   2. `.claude/policies/.drift-manifest.json` — the policy hash-pin
    #      registry. Rewritable without the sentinel it pins; the parallel
    #      of #3 ("pin the pinner").
    #
    # BOTH are ALSO in `_KERNEL_PATHS` (same wave) — the sentinel rail
    # alone would let a sentinel authorize an edit to the registry that
    # decides which signers are valid, i.e. a sentinel bootstrapping its
    # own successor. C10 explicitly does NOT invert the `.exists()` gate
    # into "absence ⇒ fail-closed": that would make DELETING a file the
    # way to pick the posture.
    ".claude/security/sentinel-signers-registry.yaml",
    ".claude/policies/.drift-manifest.json",
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


def _normalize_candidate_value(value: str) -> str:
    """PLAN162_FIX_7 (finding #7) — turn a ``file://`` URI into a path.

    ``uri`` is one of ``_MCP_WRITE_PATH_KEYS``, but HEAD handed the value
    to ``Path()`` verbatim: ``file:///repo/.claude/settings.json`` became
    a RELATIVE path whose first segment is ``file:``, resolved against the
    process CWD, landed outside the repo root and classified
    NON-canonical — so the edit sailed through ungated even though the
    MCP server would write the guarded file.

    Normalizing in ONE place (the single function that builds candidates)
    was the form both debate lanes accepted; the alternative — treating an
    un-interpretable value as fail-CLOSED — is left to the callers, which
    already fail-CLOSE on a candidate they cannot classify.

    Only LOCAL file URIs are rewritten (empty or ``localhost`` authority).
    A ``file://remote-host/...`` URI is NOT a local path and is returned
    untouched, as is any value with a different scheme. A percent-escape
    that decodes to an embedded NUL is likewise returned untouched — a
    path the OS cannot open is not made more gate-able by decoding it.
    """
    if len(value) < 7 or value[:7].lower() != "file://":
        return value
    try:
        from urllib.parse import unquote, urlsplit  # noqa: PLC0415
        parts = urlsplit(value)
        if parts.scheme.lower() != "file":
            return value
        if (parts.netloc or "").lower() not in ("", "localhost"):
            return value  # remote authority: not a local filesystem path
        decoded = unquote(parts.path)
        if not decoded or "\x00" in decoded:
            return value
        return decoded
    except Exception:
        return value


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
            # values are likely adversarial. The cap is applied to the
            # RAW value (PLAN162_FIX_7 normalization can only shorten it).
            if len(value) <= 4096:
                paths.append(_normalize_candidate_value(value))
        elif isinstance(value, list):
            for item in value:
                if isinstance(item, str) and item and len(item) <= 4096:
                    paths.append(_normalize_candidate_value(item))
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
#
# PLAN162_FIX_4 rule 3 (finding #4, consensus C5): the END scope marker
# is now a terminator too. Without it a marker-LESS (Tier-2) sentinel
# could carry `Scope:` bullets, an `<!-- END SIGNED SCOPE -->` line, and
# then MORE bullets — the comment line is not bullet-shaped, so
# collection simply continued straight past it and the post-END bullets
# granted. Listed FIRST in the alternation so the cheap literal wins.
_SCOPE_TERMINATOR_RE = re.compile(
    r"^(?:\s*<!--\s*END\s+SIGNED\s+SCOPE\s*-->"
    r"|(?:Effective|Plans|Rationale(?:\s+by\s+path)?|"
    r"Authorization(?:\s+source)?|Anchor\s+commit|Approved-By)"
    r"\s*[:.])",
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
# PLAN162_FIX_4 rule 1 — BEGIN-marker PRESENCE, independent of whether a
# well-formed PAIR exists. Detecting the two separately is what lets a
# lone/malformed BEGIN fail-CLOSE instead of quietly falling to Tier-2.
_BEGIN_MARKER_RE = re.compile(r"<!--\s*BEGIN\s+SIGNED\s+SCOPE\s*-->")


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


# ---------------------------------------------------------------------------
# PLAN162_FIX_9 — blocked_tool must be forensic, not decorative (C6)
# ---------------------------------------------------------------------------
# FOUR sites write ``blocked_tool`` into the HMAC audit chain: three
# carried the literal "Edit|Write|MultiEdit" regardless of which tool
# actually fired, and one carried the empty string. This hook is
# registered for ``mcp__.*`` too, so a human reading the chain after an
# incident was told the wrong tool — the two newest sites (the
# session-roots deny and the registry-tamper emit) were born after the
# council that found this.
#
# The fix plumbs the EVENT's tool name through. It is VALIDATED first,
# against a closed enum plus the ``mcp__`` shape, because the value is
# attacker-influenced input landing in a log humans read: an unvalidated
# fix would turn a forensics repair into a log-injection vector. Anything
# unrecognized becomes the literal "unknown" — never truncated (a
# truncation would let two distinct hostile names alias to one string).
_EDIT_CLASS_TOOLS = frozenset({"Edit", "Write", "MultiEdit", "NotebookEdit"})
_MCP_TOOL_NAME_RE = re.compile(r"^mcp__[a-z0-9_]+$")
_BLOCKED_TOOL_UNKNOWN = "unknown"

# Set ONCE per invocation by ``main()`` from the parsed event, and reset
# in its ``finally`` so a value can never leak into a later in-process
# caller. Helpers deep in the call graph (``_emit_unlock_audit`` has no
# event in scope) read it through ``_blocked_tool_field()``.
_CURRENT_TOOL_NAME = ""


def _validated_tool_name(tool_name) -> str:
    """Closed-enum / shape validation for an event-derived tool name."""
    raw = tool_name.strip() if isinstance(tool_name, str) else ""
    if raw in _EDIT_CLASS_TOOLS:
        return raw
    if _MCP_TOOL_NAME_RE.match(raw):
        return raw
    return _BLOCKED_TOOL_UNKNOWN


def _blocked_tool_field() -> str:
    """The validated ``blocked_tool`` value for this invocation."""
    return _validated_tool_name(_CURRENT_TOOL_NAME)


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
    # PLAN-156 Wave 3 (SENT-GK-E) — the same dead-guard class as `.codex`
    # above, twice over (pair-rail R4 + R14). `_is_canonical()` bails out
    # BEFORE any glob matching unless the path's first segment is in this
    # set, so adding the `.grok/**` and `templates/settings/*` patterns to
    # _CANONICAL_GUARDS without adding their first segments HERE would
    # leave both guards INERT — unsentineled edits sailing straight through
    # a list that LOOKS like it protects them. The S254 dead-gate class,
    # and the reason this pair of edits can never be split across waves.
    ".grok", "templates",
})


# PLAN160_FIX_A — upper bound on candidates classified per multi-candidate
# event. Beyond this the event is fail-CLOSED (blocked) rather than risk an
# unexamined canonical candidate riding through past a truncated scan. Real
# apply_patch / MCP bulk events carry a handful of paths; this is a DoS-shape
# backstop, not a normal-path limit.
_PLAN160_MAX_CANDIDATES = 512


def _repo_rels(path_str: str, repo_root: Path) -> List[str]:
    """All repo-relative POSIX forms of ``path_str`` (0, 1, or 2 entries).

    PLAN160_FIX_D (finding D — relative-path classification bypass,
    most-restrictive-wins): a RELATIVE path is resolved against BOTH the
    process CWD (historical anchoring) AND ``repo_root``. A canonical file
    addressed by a relative ``path_str`` from a CWD outside the repo
    previously resolved outside ``repo_root`` → ``relative_to`` raised →
    treated non-canonical → the unsigned edit sailed through ungated.
    Yielding the repo_root-anchored form too closes that bypass. Absolute
    paths yield ONLY the CWD-form (``repo_root / p`` discards ``repo_root``
    when ``p`` is absolute), so classification AND per-call resolve cost
    stay byte-identical on the Edit/Write hot path. Returned in anchoring
    order (CWD-form first) so callers pick the historical rel when both
    land inside the repo (the CWD==repo_root common case → one entry).

    TOTAL by construction (PLAN-160 finding-A blocker, codex + security
    pair-rail): every resolve is caught with a BROAD ``except Exception``.
    ``Path.resolve()`` raises ``RuntimeError`` — NOT ``ValueError``/``OSError``
    — on a symlink loop; if that propagated, ``_is_canonical`` would raise,
    and a raising candidate in the multi-candidate scan would route through
    ``decide()`` and the outer handler would fail-OPEN (allow) the whole
    event — a gate-bypass strictly worse than HEAD. An unresolvable path is
    simply non-canonical here (its write fails at the OS anyway); the other
    candidates in a multi-candidate event are still scanned and gated.
    """
    p = Path(path_str)
    try:
        root_resolved = repo_root.resolve()
    except Exception:
        return []
    anchorings = [p]
    if not p.is_absolute():
        anchorings.append(repo_root / p)
    rels: List[str] = []
    for cand in anchorings:
        try:
            rels.append(
                str(cand.resolve().relative_to(root_resolved)).replace(os.sep, "/")
            )
        except Exception:
            continue
    return rels


# PLAN162_FIX_CASEFOLD (PLAN-162 consensus S1, P0 — BOTH rails).
#
# ``_match_segments`` matches with ``fnmatch.fnmatchcase`` (exact case)
# and ``_CANONICAL_PREFIXES`` is an exact-case frozenset. On a
# case-INSENSITIVE filesystem — APFS, the default on this repo's
# platform — ``.claude/settings.JSON`` IS ``.claude/settings.json``, and
# writing through the variant OVERWRITES the guarded file. Measured on
# HEAD: `.claude/settings.JSON`, `.claude/hooks/_lib/audit_emit.PY` and
# `.CLAUDE/settings.json` all classified NON-canonical AND non-kernel,
# reaching files the threat model assumes unreachable.
#
# Both halves must fold or the guard only LOOKS fixed: the prefix
# fast-path bails out in O(1) BEFORE any glob runs, so folding the glob
# matcher alone would leave `.CLAUDE/...` inert — the dead-gate class
# this file was already bitten by twice (the `.codex` and `.grok` prefix
# omissions).
#
# ``str.lower`` — not ``str.casefold`` — deliberately: casefold expands
# 'ß'→'ss', changing segment LENGTH and hence what a glob matches. The
# exploited class is ASCII case variance, which ``lower()`` covers
# exactly; identical inputs always fold identically, so the
# normalization can only ADD matches (over-classify = the safe
# direction), never remove one.
#
# Precomputed at import: the hot path pays one ``str.lower()`` per
# classification instead of one per (segment x pattern).
_CANONICAL_GUARDS_FOLDED = [pat.lower() for pat in _CANONICAL_GUARDS]
_CANONICAL_PREFIXES_FOLDED = frozenset(
    prefix.lower() for prefix in _CANONICAL_PREFIXES
)


def _matches_canonical_guard(rel_str: str) -> bool:
    """True if a repo-relative POSIX path matches a canonical guard pattern.

    Split out of ``_is_canonical`` (PLAN160_FIX_D) so the identical
    fast-path prefix check + glob loop runs against each candidate path
    anchoring without duplication. PLAN-025 F-perf-004 fast-path preserved.

    PLAN162_FIX_CASEFOLD: the rel and the patterns are compared
    case-INSENSITIVELY (see the module note above) — on APFS the case
    variant addresses the very same inode.
    """
    rel_folded = rel_str.lower()
    # Fast path: check the first path segment against known prefixes.
    first_seg = rel_folded.split("/", 1)[0]
    if first_seg not in _CANONICAL_PREFIXES_FOLDED:
        return False
    for pattern in _CANONICAL_GUARDS_FOLDED:
        if _fnmatch_segments(rel_folded, pattern):
            return True
    return False


def _canonical_rel(path_str: str, repo_root: Path) -> Optional[str]:
    """The repo-relative form of ``path_str`` that matches a canonical
    guard, or ``None`` if no anchoring is canonical.

    PLAN160_FIX_D: single source of truth for canonicality AND the
    repo-relative form used downstream (decide() sentinel matching,
    ``_candidate_is_granted``), so a canonical path is ALWAYS paired with
    the exact rel that classified it — the CWD-anchored ``decide()`` resolve
    could otherwise raise on a repo_root-anchored canonical path and route a
    clean sentinel-block through finding C's fault branch instead.
    """
    for rel_str in _repo_rels(path_str, repo_root):
        if _matches_canonical_guard(rel_str):
            return rel_str
    return None


def _is_canonical(path_str: str, repo_root: Path) -> bool:
    """True if path_str matches one of the canonical guard patterns.

    Thin wrapper over ``_canonical_rel`` (PLAN160_FIX_D). NOTE: this is a
    SHARED predicate (hook Layer-A, the ``--is-canonical`` CLI oracle, and
    ``_candidate_is_granted``); the finding-D change WIDENS classification
    (relative paths from a foreign CWD now classify canonical → more
    blocks), never narrows it — see the ADR.
    """
    return _canonical_rel(path_str, repo_root) is not None


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
    # PLAN162_FIX_2 (PLAN-162 finding #2, consensus C9) — the symlink
    # rejection must be DEPTH-INDEPENDENT.
    #
    # HEAD checked exactly three levels (``p``, ``p.parent``,
    # ``p.parent.parent``), hard-coded to the depth of
    # ``PLAN-*/architect/round-*/approved.md``. The ``PLAN-*`` segment one
    # level further up was never checked, so
    # ``.claude/plans/PLAN-EVIL -> /tmp/evil`` smuggled a foreign
    # ``architect/round-1/approved.md`` into the TRUSTED sentinel set —
    # every intermediate directory is a real directory INSIDE the link
    # target, so all three checks passed.
    #
    # "Cover the real depth of the patterns" was rejected in debate: it
    # re-couples the guard to the pattern list, and the next 6-segment
    # pattern silently reopens the hole (the dead-gate class this file has
    # already suffered twice). Instead we do both depth-free checks:
    #
    #   (a) walk EVERY segment from ``p`` up to (excluding) ``base``,
    #       rejecting any symlinked component; and
    #   (b) assert ``realpath(p)`` stays under ``realpath(base)``, which
    #       also catches a symlink that resolves out of the tree without a
    #       symlinked component we happen to walk.
    #
    # RESIDUAL, deliberately not closed here: a symlink at ``base`` itself
    # (``.claude/plans``) satisfies both forms — (a) excludes base and (b)
    # resolves base through the same link. Named in the W1 instrument;
    # pinning today's behaviour there would pin a bypass.
    try:
        base_rp = os.path.realpath(str(base))
    except Exception:
        return []
    safe: List[Path] = []
    for p in candidates:
        try:
            # (a) depth-free ancestor walk: p, then every directory above
            # it, up to but not including `base`. A bound of 64 hops is a
            # runaway guard, never a semantic limit (real sentinels sit 2-4
            # levels under base).
            node = p
            contained = False
            for _hop in range(64):
                if node.is_symlink():
                    break
                parent = node.parent
                if parent == node:  # walked past the filesystem root
                    break
                if parent == base:
                    contained = True
                    break
                node = parent
            if not contained:
                continue
            # (b) realpath containment — independent of how many segments
            # the pattern happens to have.
            p_rp = os.path.realpath(str(p))
            if not p_rp.startswith(base_rp + os.sep):
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

# PLAN162_FIX_1 (PLAN-162 findings #1 + #10, consensus C1 + C2 + C3 + S8).
#
# ## The defect (#1, re-diagnosed in debate: AMPLIFICATION, not latency)
#
# The cache above folds ``target_rel`` into its key, but
# ``_gpg_verify.verify_detached`` never RECEIVES a target — signature
# validity is target-INDEPENDENT. So the same sentinel was
# cryptographically re-verified once per distinct target: a subprocess
# count of O(candidates x sentinels). Measured in debate, gpg-agent
# healthy: 1 GPG ~ 17 ms, but a 20-path ceremony pack cost **4.16 s of a
# 5 s hook budget** with 0 cache hits and 320 misses (40 paths: 4.23 s).
#
# ## The fix — two caches, not one
#
#   * ``_SIG_VERIFY_CACHE`` — the SIGNATURE rail, keyed on the signing
#     MATERIAL and NOT on the target. 320 subprocesses collapse to 16.
#   * ``_GRANT_CACHE`` — the SCOPE rail, target-keyed and cheap. This is
#     the SAME object as ``_SENTINEL_VERIFY_CACHE`` (an alias, not a
#     copy): the PLAN-094 key shape and counters are pinned by
#     ``test_sentinel_session_cache.py`` and stay byte-compatible.
#
# ## Why the signature rail must run FIRST (this is finding #10)
#
# #10 observed that the grant key hashes only ``approved.md``'s bytes, so
# mutating the ``.asc`` / signer allowlist / ADR-121 registry left a
# stale ``True`` riding the cache in-process. Rather than smuggle a
# digest of three more files into a key shape other tests pin, the
# signature rail is consulted BEFORE the grant fast-path and keys on
# those bytes itself. A revocation in any of the three now invalidates
# the decision even when ``approved.md`` is byte-identical — closing the
# "signer rotation window" that PLAN-094 §8 had consciously accepted.
_SIG_CACHE_FORMAT_VERSION = 1
_SIG_VERIFY_CACHE: Dict[tuple, bool] = {}
_GRANT_CACHE = _SENTINEL_VERIFY_CACHE  # alias — same dict object

# ---------------------------------------------------------------------------
# PLAN162_FIX_1 — per-invocation wall-clock budget (consensus C2 + C3 + S8)
# ---------------------------------------------------------------------------
# C2 REMOVED the sentinel cap from the design: ``_find_sentinels`` returns
# SORTED, so the highest-numbered pack — the ceremony the Owner just
# signed — is exactly the sentinel a cap would drop. Self-DoS with the
# signature in hand, and it does not even fix a hung gpg (one hang costs
# the full timeout at cap=1). What replaces it is a global wall-clock
# deadline per INVOCATION, checked at the top of the sentinel loops.
#
# C3: the budget is a MODULE CONSTANT, never read from settings.json at
# runtime — the budget lives in the file this hook guards (circular), and
# parsing JSON on the hot path would worsen the very path being
# optimized. Drift against the registered timeout is a STATIC test
# instead (the shape verify-counts.sh already uses):
# ``test_1_repro_wall_deadline_constant_has_slack_under_registration``.
# 4.0 s under the registered 5 s leaves ~1 s to emit the decision.
#
# S8: the clock is an injectable module-level seam (``_now``). Without
# it the red-first test's only options were a multi-second real sleep
# (a documented flake class in this repo) or no deterministic coverage
# of the slow path at all. This is a requirement OF the fix.
#
# ORDER IS NOT NEGOTIABLE (C3): the deadline and the cache partition ship
# in the SAME patch under the SAME marker. A deadline without the
# partition fires on the 4.16 s measured above and denies the ceremony
# itself.
_HOOK_WALL_BUDGET_S = 4.0
_now = time.monotonic
_WALL_DEADLINE_AT = None  # type: Optional[float]
_WALL_BUDGET_EXHAUSTED = False


def _start_wall_budget() -> None:
    """Arm the per-invocation wall-clock deadline (called once by main)."""
    global _WALL_DEADLINE_AT, _WALL_BUDGET_EXHAUSTED
    _WALL_BUDGET_EXHAUSTED = False
    _WALL_DEADLINE_AT = _now() + _HOOK_WALL_BUDGET_S


def _reset_wall_budget() -> None:
    """Disarm the deadline.

    Called from ``main()``'s ``finally`` so a module-scope deadline can
    never leak into a LATER in-process caller (the test suite drives
    ``decide()`` directly in the same process; a stale expired deadline
    would fail those closed for no reason).
    """
    global _WALL_DEADLINE_AT, _WALL_BUDGET_EXHAUSTED
    _WALL_DEADLINE_AT = None
    _WALL_BUDGET_EXHAUSTED = False


def _mark_wall_budget_exhausted() -> None:
    """Latch the budget as spent (see ``_gpg_verify_timeout``).

    Set when a signature verification is REFUSED for want of budget. The
    clock has not necessarily elapsed yet, but the invocation can no
    longer reach a verdict, so every subsequent poll must report expiry —
    otherwise the loop runs to its end and the operator is handed the
    generic "declare this path in Scope" block, which misdiagnoses a
    budget fault as a missing sentinel and omits the recovery route.
    """
    global _WALL_BUDGET_EXHAUSTED
    _WALL_BUDGET_EXHAUSTED = True


def _wall_budget_expired() -> bool:
    """True once the armed invocation budget has elapsed (or is spent).

    Disarmed (``None``) => never expired, so direct ``decide()`` callers
    outside a hook invocation are unaffected.
    """
    if _WALL_DEADLINE_AT is None:
        return False
    if _WALL_BUDGET_EXHAUSTED:
        return True
    return _now() > _WALL_DEADLINE_AT


# ---------------------------------------------------------------------------
# PLAN162_FIX_1 — the gpg subprocess is bounded by the REMAINING budget
# ---------------------------------------------------------------------------
# Codex pair-rail P1 (S292) against this patch, staged:
#
#   "Bound GPG verification by the remaining hook budget. When gpg or
#   gpg-agent stalls, this call can block for 15 seconds although the
#   hook is registered for 5 seconds and the new internal deadline is 4
#   seconds. Because the deadline is checked only between sentinel
#   iterations, the harness can kill the process before it emits the
#   intended fail-closed decision, recreating the silent fail-open that
#   ADR-164-AMEND-1 §3 explicitly says the patch prevents."
#
# The deadline above is POLLED: read at the top of the sentinel loops, it
# can only bound work that happens BETWEEN iterations. One
# ``verify_detached`` at the library default (``timeout=15.0``,
# ``_lib/gpg_verify.py``) is 3x the entire registration — the poll never
# gets its turn, the harness kills a hook that has emitted NOTHING, and
# "no decision" is indistinguishable from allow. ADR-164-AMEND-1 §3 D2
# already states the intended behaviour ("per-verify subprocess timeout
# bounded by remaining budget"); this is the code that makes the text
# true.
#
# Two constants, both about EMITTING rather than about gpg:
#
#   * ``_GPG_EMIT_MARGIN_S`` — wall time reserved AFTER gpg returns so the
#     rest of the decision plus the JSON emit still fit inside the
#     internal deadline. A verification bounded to land exactly ON the
#     deadline would merely have moved the kill.
#   * ``_GPG_MIN_SPAWN_S`` — the floor below which spawning is pointless:
#     a fork we cannot afford to wait out cannot tell "bad signature"
#     from "slow agent", so it must not start at all.
#
# Their sum must stay well under ``_HOOK_WALL_BUDGET_S``, or the FIRST
# sentinel of a fresh invocation could never be verified — self-DoS with
# the Owner's signature in hand, the C3 class. Pinned by
# ``test_control_gpg_bound_constants_leave_room_for_a_first_verify``.
_GPG_VERIFY_TIMEOUT_CAP_S = 15.0  # the historical _lib.gpg_verify default
_GPG_EMIT_MARGIN_S = 0.5
_GPG_MIN_SPAWN_S = 0.5


def _gpg_verify_timeout() -> Optional[float]:
    """Subprocess timeout for ONE detached-signature verification.

    ``None`` means DO NOT SPAWN — what is left of the invocation budget
    cannot cover both a meaningful verification and the emit that has to
    follow it. Callers translate that into the fail-CLOSED wall-deadline
    block, never into an allow and never into a silent zero-emit.

    With the budget disarmed (direct ``decide()`` callers, importers such
    as ``check_pair_rail``) the historical cap is returned unchanged:
    this narrows the hook-invocation path only.
    """
    if _WALL_DEADLINE_AT is None:
        return _GPG_VERIFY_TIMEOUT_CAP_S
    usable = (_WALL_DEADLINE_AT - _now()) - _GPG_EMIT_MARGIN_S
    if usable < _GPG_MIN_SPAWN_S:
        return None
    return min(_GPG_VERIFY_TIMEOUT_CAP_S, usable)


_WALL_DEADLINE_BLOCK_REASON = (
    "CANONICAL-EDIT-BLOCKED: canonical_edit_hook_fault — the hook's "
    "per-invocation wall-clock budget ({0}s) elapsed before authorization "
    "for this canonical path could be established. A security matcher that "
    "cannot finish deciding does NOT allow (PLAN-045 F-01-07 posture; "
    "PLAN-162 consensus C2). Recovery: re-issue the edit, or use the "
    "documented CEO_SENTINEL_UNLOCK / CEO_KERNEL_OVERRIDE ceremony."
).format(_HOOK_WALL_BUDGET_S)


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


def _file_digest(path: Optional[Path]) -> str:
    """sha256 of a file's bytes, or a stable marker when unreadable.

    PLAN162_FIX_1 helper. ``"-"`` distinguishes "no such file" from any
    real digest, so a signer allowlist APPEARING (or vanishing) changes
    the signature cache key just like editing it does.
    """
    if path is None:
        return "-"
    try:
        return hashlib.sha256(path.read_bytes()).hexdigest()
    except OSError:
        return "-"


def _compute_sig_cache_key(sentinel_path: Path) -> Optional[tuple]:
    """Target-FREE key over everything the SIGNATURE decision depends on.

    PLAN162_FIX_1 (#1 partition + #10 staleness). Covers the sentinel's
    own identity/bytes AND the three signing-material inputs — the
    detached ``.asc``, the legacy signer allowlist, and the ADR-121 YAML
    registry — plus the PATH of the latter two (they are module-level
    seams; a different file is a different decision).

    Returns ``None`` on stat/read failure of the sentinel itself, which
    means "do not cache" — errors are never memoized.
    """
    try:
        st = sentinel_path.stat()
        content = sentinel_path.read_bytes()
    except OSError:
        return None
    sig_path = sentinel_path.with_name(sentinel_path.name + ".asc")
    return (
        str(sentinel_path),
        st.st_ino,
        st.st_mtime_ns,
        st.st_size,
        hashlib.sha256(content).hexdigest(),
        _file_digest(sig_path),
        str(_SENTINEL_SIGNERS_FILE),
        _file_digest(_SENTINEL_SIGNERS_FILE),
        str(_SENTINEL_SIGNERS_REGISTRY_YAML),
        _file_digest(_SENTINEL_SIGNERS_REGISTRY_YAML),
        _SIG_CACHE_FORMAT_VERSION,
    )


def sentinel_cache_stats() -> Dict[str, int]:
    """Return session-scoped cache counters (skill_cache_stats sibling)."""
    return {
        "hit_count": _SENTINEL_CACHE_HITS,
        "miss_count": _SENTINEL_CACHE_MISSES,
        "size": len(_SENTINEL_VERIFY_CACHE),
    }


def _verify_signature_rail(sentinel_path: Path) -> bool:
    """The full detached-GPG + dual signer-registry rail for ONE sentinel.

    Extracted verbatim from ``_sentinel_grants_path`` (PLAN162_FIX_1) so
    the decision it produces — which is INDEPENDENT of the edit target —
    can be cached target-free. Behaviour is unchanged: fail-CLOSED on a
    missing helper, bad signature, unlisted fingerprint, bootstrap-SHA
    mismatch, or (post-GENESIS) a registry parse failure.
    """
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
    # PLAN162_FIX_1 (Codex P1 fold) — the subprocess is bounded by what is
    # LEFT of the invocation budget, minus the margin needed to still emit
    # a decision. ``None`` => not enough budget to verify AND emit: refuse
    # the spawn and latch, so the caller's next deadline poll produces the
    # fail-closed wall-deadline block instead of a harness kill.
    _timeout = _gpg_verify_timeout()
    if _timeout is None:
        _mark_wall_budget_exhausted()
        return False
    ok, _fpr, _reason = _gpg_verify.verify_detached(
        sentinel_path,
        sig_path,
        allowlist_path=_SENTINEL_SIGNERS_FILE,
        timeout=_timeout,
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
    return True


def _signature_rail_ok(sentinel_path: Path) -> bool:
    """``_verify_signature_rail`` behind the target-FREE signature cache.

    PLAN162_FIX_1: this is the O(sentinels) rail. The caller's grant
    lookup stays O(sentinels x targets) but is pure string work.
    """
    if _sentinel_cache_disabled():
        return _verify_signature_rail(sentinel_path)
    sig_key = _compute_sig_cache_key(sentinel_path)
    if sig_key is None:
        return _verify_signature_rail(sentinel_path)
    cached = _SIG_VERIFY_CACHE.get(sig_key)
    if cached is not None:
        return cached
    result = _verify_signature_rail(sentinel_path)
    if _WALL_BUDGET_EXHAUSTED:
        # PLAN162_FIX_1 (Codex P1 fold): a budget REFUSAL is not a verdict
        # on this sentinel — memoizing it would poison the signature cache
        # for the rest of the process with a `False` no gpg ever produced.
        # Same contract as the `sig_key is None` path above: errors and
        # non-verdicts are never cached.
        return result
    _SIG_VERIFY_CACHE[sig_key] = result
    return result


# ---------------------------------------------------------------------------
# PLAN162_FIX_S2 — the sentinel SET is a trust anchor (consensus S2)
# ---------------------------------------------------------------------------
# ``.claude/plans/PLAN-*/**/approved.md`` is guarded by NEITHER rail, and
# under an Owner ``CEO_SENTINEL_UNLOCK`` window the GPG rail is skipped
# entirely — so an ``approved.md`` the AGENT writes mid-window GRANTS.
# That is a bypass of AUTHORIZATION, not merely a DoS on the gate's cost.
#
# The first mitigation drafted for this ("tracked in git OR pre-existing")
# was DEFEATED by the pair-rail in one command: inside the window the
# agent writes the file and runs an ordinary ``git add``; ``ls-files
# --error-unmatch`` then calls it TRACKED, and a HEAD-based check would
# accept an agent-authored COMMIT just the same. **Git state is a
# statement about the index, not about who authorized the file.**
#
# The trust anchor is therefore SESSION START: under ``env_override``,
# accept only a sentinel that already existed in the tree at the commit
# the Owner names in ``CEO_SESSION_ANCHOR_SHA``. The anchor is an ENV
# var, which is exactly the same trust primitive the unlock itself rests
# on (a sub-agent cannot set env in the parent shell) — so requiring it
# adds no new assumption. No anchor => no proof => no grant.
#
# ## PLAN162_FIX_S2R2 — what the codex round-2 pair-rail corrected
#
# The first draft of this rail proved only that the sentinel PATH existed
# at the anchor, then parsed the CURRENT bytes. Codex defeated it in one
# move (P1-1): inside a legitimate window, take any pre-existing
# unguarded ``approved.md``, keep its ``Approved-By:`` line, ADD a target
# to ``Scope:`` — path-existence still holds, GPG is skipped, and the
# hook authorizes off attacker-modified bytes. **A trust decision must be
# made on the ANCHORED bytes, not on bytes that merely live at an
# anchored path.** ``git cat-file blob`` now supplies the text that is
# parsed; what is on disk is never consulted on this path.
#
# Two more round-2 corrections ride the same fold:
#
#   * P1-2 — the git subprocess is bounded by the REMAINING wall budget
#     (``_git_anchor_timeout``), exactly as the gpg spawn already is. A
#     5 s probe inside a 4 s budget lets the harness kill the process
#     before it emits the intended BLOCK, which is the zero-emit
#     fail-open this whole patch exists to remove.
#   * P1-3 — a fail-closed gate with no recovery route is a brick. The
#     anchor alone bricks the ONE use ADR-119 names for the unlock
#     ("ceremony authoring where the .asc is being signed in parallel"):
#     a freshly authored sentinel predates nothing. So the Owner may
#     instead PIN the sentinel's content hash
#     (``CEO_SENTINEL_UNLOCK_SHA256``, space/comma-separated for several).
#     It rests on the same trust primitive as the unlock itself — env a
#     sub-agent cannot set in the parent shell — and it is strictly
#     stronger than the anchor: it binds CONTENT, not a path. Reading the
#     value gains an attacker nothing (sha256 preimage), and it works in
#     a non-git tree, where the anchor cannot.
#
# ## RESIDUAL — read before ratifying
#
# The ANCHOR rail arms only when the project is a git work tree (``.git``
# present); otherwise no anchor proof exists and the legacy accept
# stands. Consequence: ``rm -rf .git`` disarms the anchor half. Named
# here rather than buried. The digest-pin half is unaffected by it — it
# is the git-free proof form the first draft said "is a separate
# decision", and this is that decision.
#
# DECIDED, not overlooked: in a NON-git tree a digest pin does not make
# the unpinned sentinels stricter — a pin-miss falls through to the
# residual accept there, exactly as it falls through to the anchor rail
# in a git tree. Making the pin authoritative in a non-git tree would
# mean "pin one file, reject every other sentinel in the pack" in the
# one tree shape that has no second proof form: the C3 self-DoS class,
# traded for a tightening that only bites where the legacy accept
# already applies.
#
# Landing this CHANGES a documented operator contract (ADR-119,
# SPEC/v1/sentinel-format.schema.md, docs/FAQ.md, the READMEs): an
# unlock window now needs a THIRD value. Those surfaces are updated in
# this same patch, and ``_unlock_trust_hint`` teaches both forms in the
# block reason itself — a required value that only exists in the diff is
# the lockout P1-3 named. Owner ratification: ADR-164-AMEND-1.
_SESSION_ANCHOR_ENV = "CEO_SESSION_ANCHOR_SHA"
_UNLOCK_DIGEST_ENV = "CEO_SENTINEL_UNLOCK_SHA256"
_ANCHOR_SHA_RE = re.compile(r"^[0-9a-fA-F]{7,64}$")
_SHA256_RE = re.compile(r"^[0-9a-fA-F]{64}$")
_GIT_ANCHOR_TIMEOUT_CAP_S = 5.0
# (repo_root, anchor, rel) -> anchored text, or None for "proven absent".
# A key is absent from the map when no VERDICT was reached (budget
# refusal, git fault) — errors are never memoized, same contract as
# ``_SIG_VERIFY_CACHE``.
_ANCHOR_BLOB_CACHE = {}  # type: Dict[tuple, Optional[str]]

# Why the unlock rail refused, for the block reason. First refusal wins;
# reset per ``decide()`` call.
_UNLOCK_TRUST_DIAG = None  # type: Optional[str]


def _repo_root_for_sentinels() -> Path:
    """Repo root, resolved exactly as ``main()`` resolves it."""
    return Path(os.environ.get("CLAUDE_PROJECT_DIR") or os.getcwd())


def _reset_unlock_trust_diag() -> None:
    global _UNLOCK_TRUST_DIAG
    _UNLOCK_TRUST_DIAG = None


def _note_unlock_trust_diag(code: str) -> None:
    global _UNLOCK_TRUST_DIAG
    if _UNLOCK_TRUST_DIAG is None:
        _UNLOCK_TRUST_DIAG = code


def _git_anchor_timeout() -> Optional[float]:
    """Subprocess timeout for ONE ``git cat-file`` anchor probe.

    PLAN162_FIX_S2R2 (codex P1-2). Same shape and the same two constants
    as ``_gpg_verify_timeout``: the probe must finish AND leave room to
    emit. ``None`` means DO NOT SPAWN — callers translate that into
    fail-CLOSED plus a latched budget, never into an allow and never into
    a fork the harness kills mid-flight.
    """
    if _WALL_DEADLINE_AT is None:
        return _GIT_ANCHOR_TIMEOUT_CAP_S
    usable = (_WALL_DEADLINE_AT - _now()) - _GPG_EMIT_MARGIN_S
    if usable < _GPG_MIN_SPAWN_S:
        return None
    return min(_GIT_ANCHOR_TIMEOUT_CAP_S, usable)


def _anchored_blob_text(repo_root: Path, anchor: str, rel: str) -> Optional[str]:
    """Text of ``rel`` AS OF ``anchor``, or ``None`` when unprovable."""
    cache_key = (str(repo_root), anchor, rel)
    if cache_key in _ANCHOR_BLOB_CACHE:
        return _ANCHOR_BLOB_CACHE[cache_key]
    timeout = _git_anchor_timeout()
    if timeout is None:
        # P1-2: refuse the spawn and latch, so the caller's next deadline
        # poll produces the fail-closed wall-deadline block instead of a
        # harness kill. NOT memoized — a budget refusal is not a verdict.
        _mark_wall_budget_exhausted()
        return None
    try:
        proc = subprocess.run(
            ["git", "-C", str(repo_root), "cat-file", "blob",
             "{0}:{1}".format(anchor, rel)],
            stdout=subprocess.PIPE,
            stderr=subprocess.DEVNULL,
            timeout=timeout,
        )
    except Exception:
        # git missing / hung / unusable: the work tree says the proof
        # mechanism SHOULD exist, so an unusable one is fail-CLOSED.
        return None
    if proc.returncode != 0:
        _ANCHOR_BLOB_CACHE[cache_key] = None
        return None
    try:
        text = proc.stdout.decode("utf-8")
    except Exception:
        _ANCHOR_BLOB_CACHE[cache_key] = None
        return None
    _ANCHOR_BLOB_CACHE[cache_key] = text
    return text


def _pinned_sentinel_digests(src_env) -> Tuple[Set[str], bool]:
    """``(digests, malformed)`` from ``CEO_SENTINEL_UNLOCK_SHA256``.

    Empty + not-malformed means "the Owner pinned nothing" (rail B
    decides). ANY unparseable token makes the whole value malformed:
    a typo'd trust input is never silently narrowed to the tokens that
    happened to parse.
    """
    raw = (src_env.get(_UNLOCK_DIGEST_ENV) or "").strip()
    if not raw:
        return (set(), False)
    tokens = [t for t in re.split(r"[,\s]+", raw) if t]
    digests = set()  # type: Set[str]
    for token in tokens:
        if not _SHA256_RE.match(token):
            return (set(), True)
        digests.add(token.lower())
    return (digests, not digests)


def _unlock_trusted_text(sentinel_path: Path, env=None) -> Tuple[bool, Optional[str]]:
    """``(authorized, text_to_parse)`` for ONE sentinel under an unlock.

    PLAN162_FIX_S2 / PLAN162_FIX_S2R2. Consulted ONLY on the
    ``env_override`` path, where the GPG rail is skipped entirely and the
    only thing separating an Owner-signed sentinel from one the AGENT
    just wrote is provenance.

    ``text_to_parse`` is ``None`` for "parse what is on disk" — returned
    only by the two paths where disk bytes ARE the authorized bytes: an
    Owner-pinned digest (which covers exactly those bytes) and the
    non-git residual.
    """
    src_env = env if env is not None else os.environ
    repo_root = _repo_root_for_sentinels()

    # ---- Rail A: the Owner pinned this sentinel's CONTENT (P1-3) ----
    pinned, malformed = _pinned_sentinel_digests(src_env)
    if malformed:
        _note_unlock_trust_diag("digest_malformed")
        return (False, None)
    if pinned:
        try:
            raw = sentinel_path.read_bytes()
        except OSError:
            _note_unlock_trust_diag("sentinel_unreadable")
            return (False, None)
        if hashlib.sha256(raw).hexdigest() in pinned:
            try:
                return (True, raw.decode("utf-8"))
            except Exception:
                _note_unlock_trust_diag("sentinel_undecodable")
                return (False, None)
        # A pin that does not cover THIS sentinel is not a verdict on the
        # others: fall through to the anchor rail, or the pack's
        # pre-existing sentinels would be self-DoS'd by pinning one file.
        _note_unlock_trust_diag("digest_mismatch")

    # ---- Rail B: the sentinel predates the session (anchored bytes) ----
    try:
        is_git = (repo_root / ".git").exists()
    except OSError:
        is_git = False
    if not is_git:
        return (True, None)  # documented residual: no anchor mechanism
    anchor = (src_env.get(_SESSION_ANCHOR_ENV) or "").strip()
    if not _ANCHOR_SHA_RE.match(anchor):
        _note_unlock_trust_diag("anchor_missing" if not anchor else "anchor_malformed")
        return (False, None)
    try:
        rel = str(sentinel_path.relative_to(repo_root)).replace(os.sep, "/")
    except ValueError:
        # A sentinel outside the repo root can never be anchored.
        _note_unlock_trust_diag("sentinel_outside_repo")
        return (False, None)
    text = _anchored_blob_text(repo_root, anchor, rel)
    if text is None:
        _note_unlock_trust_diag("not_anchored")
        return (False, None)
    # P1-1: the ANCHORED bytes are the authorization, not the bytes an
    # in-window writer left at that path.
    return (True, text)


def _unlock_trust_hint() -> str:
    """Teaching suffix for a block an armed unlock window could not lift.

    PLAN162_FIX_S2R2 (codex P1-3). Without this, the operator whose
    recovery route just started failing closed reads "declare the path in
    the Scope: block" about a path that IS declared, and has no way to
    learn which value is missing. Empty string when the unlock rail was
    never the reason.
    """
    if _UNLOCK_TRUST_DIAG is None:
        return ""
    return (
        "\n\nUNLOCK WINDOW ARMED, NO TRUSTED SENTINEL ({diag}). Inside a "
        "CEO_SENTINEL_UNLOCK window the GPG rail is skipped, so a sentinel "
        "must prove it was not written by the agent, by ONE of:\n"
        "  (a) predating the session — export {anchor}=<sha of a commit "
        "taken BEFORE this agent session started>; capture it in your own "
        "shell (`git rev-parse HEAD`) before launching, never after;\n"
        "  (b) Owner-pinned content — export {digest}=<sha256 of the "
        "approved.md>, e.g. `shasum -a 256 <approved.md> | cut -d' ' -f1` "
        "(space- or comma-separate several).\n"
        "See ADR-119 Invariant 5."
    ).format(
        diag=_UNLOCK_TRUST_DIAG,
        anchor=_SESSION_ANCHOR_ENV,
        digest=_UNLOCK_DIGEST_ENV,
    )


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

    # PLAN-045 Wave 1 P0-01: env-override (CEO_SENTINEL_UNLOCK) detection.
    env = os.environ
    unlock_reason = (env.get("CEO_SENTINEL_UNLOCK") or "").strip()
    unlock_ack = (env.get("CEO_SENTINEL_UNLOCK_ACK") or "").strip()
    env_override = bool(
        unlock_reason
        and unlock_ack == "I-ACCEPT"
        and re.match(r'^(ADR-\d{3,4}|PLAN-\d{3})-[a-z0-9-]{3,100}$', unlock_reason)  # PLAN-086 Wave I.1 — ADR-119 tightening
    )

    # PLAN162_FIX_1 — SIGNATURE RAIL FIRST, and it is target-FREE.
    #
    # Two reasons the order changed (both are the fix):
    #   * #1 — verifying once per SENTINEL instead of once per
    #     (sentinel x target) is the whole amplification collapse; and
    #   * #10 — the target-keyed grant cache below hashes only
    #     approved.md, so a mutated .asc / allowlist / registry would ride
    #     a stale True if the grant fast-path ran first. Consulting the
    #     material-keyed rail up front makes a revocation land immediately.
    _trusted_text = None  # type: Optional[str]
    if not env_override:
        if not _signature_rail_ok(sentinel_path):
            return False
    else:
        # PLAN162_FIX_S2 — inside an unlock window the GPG rail is skipped
        # entirely, so the only thing separating an Owner-signed sentinel
        # from one the AGENT just wrote is provenance. See the module note
        # above for the two proof forms and the residual.
        _authorized, _trusted_text = _unlock_trusted_text(sentinel_path, env=env)
        if not _authorized:
            return False

    # PLAN-094 Wave C — session cache fast-path (now scope-only).
    # Cache key (iter-1 P0 fix): (path, inode, mtime_ns, file_size, sha256_full,
    # target_rel, fmt_version). Cache value: granted (bool). env_override path
    # bypasses cache (CEO_SENTINEL_UNLOCK semantic: must re-verify).
    _cache_key = None
    if not _sentinel_cache_disabled() and not env_override:
        _cache_key = _compute_sentinel_cache_key(sentinel_path, target_rel)
        if _cache_key is not None:
            _cached = _SENTINEL_VERIFY_CACHE.get(_cache_key)
            if _cached is not None:
                _SENTINEL_CACHE_HITS += 1
                return _cached
            _SENTINEL_CACHE_MISSES += 1

    # PLAN162_FIX_S2R2 (codex P1-1): under an unlock window the bytes that
    # decide are the ANCHORED bytes, never whatever an in-window writer
    # left at that path. ``None`` means "disk bytes ARE the authorized
    # bytes" (Owner-pinned digest, or the non-git residual).
    if _trusted_text is not None:
        text = _trusted_text
    else:
        try:
            text = sentinel_path.read_text(encoding="utf-8")
        except OSError:
            return False

    # Check plaintext signature marker first (cheap).
    if not _APPROVED_BY_RE.search(text):
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

    # ---- PLAN162_FIX_4 (finding #4, consensus C5 — narrowed) ----
    #
    # The original council proposal ("parse ONLY inside the markers")
    # would have bricked 31% of live sentinels: 5 of 16 carry no BEGIN
    # marker, including the two most recent ceremonies. What ships is
    # three narrow rules instead:
    #
    #   1. A BEGIN marker with no well-formed PAIR must NEVER silently
    #      downgrade to the Tier-2 whole-file parser. The code already
    #      fail-CLOSES on that exact principle for a marker region with an
    #      unparseable INTERIOR; a BEGIN with a missing/malformed END did
    #      the opposite, which is the containment loss #4 reported —
    #      Scope bullets OUTSIDE the Owner's intended region were honored.
    #   2. Oversize (> _SCOPE_MARKER_CAP_BYTES) REJECTS fail-closed
    #      rather than downgrading to Tier-2. Blast measured ~zero (the
    #      largest live sentinel is 6,801 B = 10.4% of the cap).
    #   3. The END marker terminates a Tier-2 Scope block (added to
    #      _SCOPE_TERMINATOR_RE), so a bullet placed AFTER an END in a
    #      marker-less file is no longer collected.
    #
    # CHARS-vs-BYTES, decided explicitly (C5 required a decision): the cap
    # is named in BYTES, so it is now measured in BYTES. HEAD compared
    # len(text) in CHARACTERS, which for a non-ASCII sentinel understated
    # the real size. Since oversize is now a REJECT (rule 2) rather than a
    # silent downgrade, the stricter of the two readings is also the
    # safer one.
    declared_paths: Set[str] = set()
    try:
        _text_bytes = len(text.encode("utf-8", "surrogatepass"))
    except Exception:  # pragma: no cover - defensive
        _text_bytes = len(text)
    if _text_bytes > _SCOPE_MARKER_CAP_BYTES:
        # Rule 2 — fail-CLOSED. An oversize sentinel is not parsed by
        # EITHER tier; it is rejected.
        return False
    if _BEGIN_MARKER_RE.search(text):
        marker_match = _SCOPE_MARKER_RE.search(text)
        if marker_match is None:
            # Rule 1 — a BEGIN marker is an explicit (if broken) Owner
            # intent signal. Never Tier-2 behind its back.
            return False
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
            blocked_tool=_blocked_tool_field(),  # PLAN162_FIX_9
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
    # PLAN162_FIX_S2R2 — per-decision state, so an in-process caller
    # (``check_pair_rail``, the tests) never inherits a previous event's
    # unlock diagnosis.
    _reset_unlock_trust_diag()

    if not file_path:
        return _emit_allow()

    if not _is_canonical(file_path, repo_root):
        return _emit_allow()

    # Confirmed canonical. Re-derive the repo-relative form for sentinel
    # matching via the SAME dual-anchor resolution as _is_canonical
    # (PLAN160_FIX_D), so the path is paired with the rel that classified
    # it (a repo_root-anchored canonical path would otherwise fault the
    # historical CWD-anchored resolve and route a clean sentinel-block
    # through the finding-C fault branch).
    rel = _canonical_rel(file_path, repo_root)
    if rel is None:
        # PLAN160_FIX_C (finding C): fail-CLOSED. ``_is_canonical`` (guard
        # above) returned True, yet no anchoring yields a canonical rel
        # HERE — only a same-process TOCTOU between those two resolves can
        # reach this. The historical code fail-OPENED via
        # ``return _emit_allow()`` on the resolve fault; a confirmed-canonical
        # path MUST block (PLAN-045 F-01-07). Dead in same-process terms;
        # defense-in-depth.
        return _emit_block(
            reason=(
                "CANONICAL-EDIT-BLOCKED: canonical_edit_hook_fault — a "
                "confirmed-canonical path could not be resolved repo-relative "
                "for sentinel matching (same-process TOCTOU). PLAN-045 "
                "F-01-07 / PLAN-160 finding C fail-closed."
            )
        )

    sentinels = _find_sentinels(repo_root)
    for sentinel in sentinels:
        # PLAN162_FIX_1 (C2) — wall-clock deadline, checked at the TOP of
        # the sentinel loop and fail-CLOSED. Never "allow because we ran
        # out of time", and never "stop checking sentinels" (a cap would
        # drop the highest-numbered pack, i.e. the ceremony the Owner just
        # signed — self-DoS with the signature in hand).
        if _wall_budget_expired():
            return _emit_block(reason=_WALL_DEADLINE_BLOCK_REASON)
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

    # PLAN162_FIX_1 (Codex P1 fold) — the budget can run out DURING the
    # last sentinel's verification, after the final top-of-loop poll. Both
    # outcomes block, but only this one names the cause and carries the
    # recovery route; the generic block below would tell the Owner to
    # declare a path that IS already declared.
    if _wall_budget_expired():
        return _emit_block(reason=_WALL_DEADLINE_BLOCK_REASON)

    return _emit_block(
        reason=(
            f"CANONICAL-EDIT-BLOCKED: '{rel}' is a canonical governance "
            "path. Edits require an Owner-signed sentinel at "
            ".claude/plans/PLAN-NNN/architect/round-N/approved.md with "
            f"this path declared in the Scope: block. See ADR-010."
            # PLAN162_FIX_S2R2 (P1-3): when an unlock window IS armed and
            # the trust rail is what refused, say so and name the value.
            + _unlock_trust_hint()
        )
    )


def _candidate_is_granted(path_str: str, repo_root: Path, sentinels) -> bool:
    """PLAN160_FIX_A helper — pure grant predicate for one candidate.

    True iff the (assumed-canonical) ``path_str`` resolves repo-relative
    AND some sentinel in ``sentinels`` grants that repo-relative path. A
    resolve fault on a canonical path is NOT a grant → returns False, so
    the caller treats the candidate as the offender and blocks
    (fail-CLOSED, mirroring finding C's decide() contract).

    Pure: NO side effects (does not emit persona coverage or audit) — those
    stay once-per-event concerns owned by ``decide()``. Uses the SAME
    ``_canonical_rel`` anchoring as ``_is_canonical`` and ``decide()``
    (PLAN160_FIX_D), so grant is checked against the exact rel that
    classified the candidate canonical; a candidate with no canonical rel
    is conservatively treated as ungranted (→ offender → block).
    """
    rel = _canonical_rel(path_str, repo_root)
    if rel is None:
        return False
    for sentinel in sentinels:
        if _sentinel_grants_path(sentinel, rel):
            return True
    return False


def _safe_sentinel_count(repo_root: Path) -> int:
    """Best-effort sentinel count for the veto-audit breadcrumb.

    PLAN160_FIX_A (codex pair-rail HIGH#2): the audit breadcrumb must never
    let a ``_find_sentinels`` fault (a malformed sentinel dir, an OSError
    walking the tree) propagate out of ``main()`` and produce a ZERO-emit
    hook on a governance event. Returns 0 on any fault — the count is
    forensic only; the block/allow decision is already made.
    """
    try:
        return len(_find_sentinels(repo_root))
    except Exception:
        return 0


def _block_reason_code(reason: str) -> str:
    """Which ``reason_code`` the CHAIN gets for a block decision.

    PLAN162_FIX_1B (r8 P2). ``_emit_block`` already names the class in the
    DECISION text, but the audit breadcrumb hard-coded
    ``canonical_edit_unsigned`` for every block — so the wall-deadline
    fail-CLOSED (and the pre-existing over-cap / scan-fault blocks) landed
    in the HMAC chain labelled as an unsigned edit: indistinguishable from
    a legitimate missing-sentinel block, and therefore UNCOUNTABLE for the
    ADR-110-AMEND-2 §3 censorship RATE. ``wave-readonly-monitor.py``
    already lists ``canonical_edit_hook_fault`` in
    ``_LAYER_3A_REASON_CODES``: a consumer with zero producers.

    Closed 2-value derivation, read off the decision this hook itself
    built — never off attacker-shaped input.
    """
    return (
        "canonical_edit_hook_fault"
        if "canonical_edit_hook_fault" in (reason or "")
        else "canonical_edit_unsigned"
    )


def _audit_block(
    rel: str,
    sentinels_count: int,
    reason_code: str = "canonical_edit_unsigned",
) -> None:
    """Best-effort emit of veto_triggered event. Never raises.

    ``reason_code`` defaults to the historical value, so every existing
    caller is byte-identical. NO new ACTION is invented — ``veto_triggered``
    stays the registered action, same precedent as
    ``_audit_registry_unreadable``'s ``session_roots_registry_unreadable``.
    """
    try:
        from _lib import audit_emit
        if reason_code == "canonical_edit_unsigned":
            _preview = (
                f"blocked edit to {rel}; {sentinels_count} sentinel(s) checked, "
                "none grant this path"
            )
        else:
            _preview = (
                f"blocked edit to {rel}; fail-CLOSED before the sentinel sweep "
                f"could complete ({sentinels_count} sentinel(s) on disk)"
            )
        audit_emit.emit_veto_triggered(
            hook="check_canonical_edit",
            reason_code=reason_code,
            reason_preview=_preview,
            blocked_tool=_blocked_tool_field(),  # PLAN162_FIX_9
            project=os.environ.get("CLAUDE_PROJECT_DIR") or "",
        )
    except Exception:
        return


# ---------------------------------------------------------------------------
# PLAN-163 T3.1 — session-roots write-guard (DirectoryAdded consumer)
# ---------------------------------------------------------------------------
# CC 2.1.220 ships `DirectoryAdded` as a NOTIFICATION-ONLY, POST-facto hook
# event: `decision: block` is structurally ignored, and by the time the
# event dispatches the permission/sandbox surface ALREADY includes the new
# directory (full reads+writes for the rest of the session). The observer
# half (`check_directory_added.py`, PLAN-163 T3.1 thread B1) records every
# added root into `.claude/state/session-roots.json`; THIS extension is the
# enforcement half: on the existing Edit|Write|MultiEdit PreToolUse guard,
# a write whose realpath resolves INSIDE a session-registered root that is
# not explicitly allowlisted is DENIED. Deliberately an EXTENSION of
# check_canonical_edit.py (the write-path guard already wired for this
# matcher family) — NOT a new hook file (ADR-183; hook-count contract
# T6.4: only the B1 observer + the Notification telemetry hook are new
# files).
#
# Registry schema (written by check_directory_added.py):
#     {"schema": 1,
#      "sessions": {<session_id>: {"roots": [
#          {"directory": <abs>, "source": <str>, "ts": <str>,
#           "unparseable": true?}, ...]}}}
#
# Failure contract (CLAUDE.md §4):
#   - Registry ABSENT → allow silently (the registry only exists if the
#     observer ran; absence is the normal no-DirectoryAdded state, not a
#     fault).
#   - Registry PRESENT but unparseable (corrupt JSON / unknown schema /
#     malformed `sessions`) → INPUT-parse failure of a security matcher,
#     NOT an ABSENT-file INFRA condition → fail-CLOSED for writes that
#     cannot be proven repo-internal (FXγ / C3, doctrine correction). The
#     deny is SCOPED to external writes — the new surface an added root
#     could have opened — while repo-internal writes stay governed by the
#     canonical stack above (unaffected). A stderr breadcrumb AND a
#     best-effort tamper audit event fire UNCONDITIONALLY (reason_code=
#     session_roots_registry_unreadable, on the already-registered
#     `veto_triggered` action) so corrupting/truncating the registry is both
#     BLOCKED (for the external write it opened) and HMAC-observable (H5).
#   - Root entry `unparseable: true` (or structurally malformed — a root
#     was recorded but its boundary is unknowable, INCLUDING a `directory`
#     that is not an ABSOLUTE path: a relative value would resolve against
#     the process CWD and silently mis-scope the boundary, M2) →
#     fail-CLOSED: every non-repo-internal write in that session is denied.
#   - Event carries NO session_id (absent/empty) while the registry holds
#     registered sessions → fail-CLOSED (M1): the write cannot be bound to
#     a session, yet roots exist, so the boundary is unknowable; external
#     writes are denied so that clearing CLAUDE_SESSION_ID cannot
#     neutralize the guard (CLAUDE.md §4).
#   - Tool-call path that cannot be canonicalized while the guard is
#     active → DENY (security-matcher input, fail-CLOSED).
#   - Candidates whose realpath resolves INSIDE the repo root are exempt:
#     they are governed by the canonical-guard stack above; this guard
#     scopes exclusively to the NEW write surface DirectoryAdded opened.
#     The realpath comparison makes the exemption symlink-safe (a repo
#     path symlinked out to a registered root still resolves external →
#     still gated).
#
# KNOWN RESIDUAL (documented, not closable here):
#   1. Roots granted via LAUNCH-time `--add-dir` never fire DirectoryAdded
#      (CC 2.1.220 registry blind spot), so they never reach the registry
#      and this guard cannot see them. Partial mitigation is the
#      SessionStart roots snapshot (T3.1 B1).
#   2. REGISTRY-REWRITE BYPASS (H5), NARROWED by FXγ. The registry
#      (.claude/state/session-roots.json) is repo-INTERNAL, so writes to it
#      are EXEMPT from this guard (repo-internal candidates are governed by
#      the canonical stack above, not here) AND it is agent-writable. FXγ
#      closes the CORRUPTION half of this bypass: corrupting/truncating the
#      registry no longer silently allows external writes — a
#      present-but-unparseable registry now fails CLOSED for them (above).
#      The residual that REMAINS is the EMPTY-but-VALID overwrite: writing
#      `{"schema":1,"sessions":{}}` parses cleanly and legitimately means
#      "no registered sessions" → allow, so an agent can still neutralize
#      the guard that way. (The corruption signal is deliberately reserved
#      for unparseable/unknown-schema; an empty valid registry is not
#      corruption.) This guard remains a BEST-EFFORT, confused/
#      non-adversarial-deputy control, NOT a hard security boundary: it
#      stops the accidental / notification-blind write that DirectoryAdded
#      opens (S283); it does not stop an adversary who rewrites the registry
#      to an empty-valid state. Even for that residual, mitigation is
#      OBSERVABILITY layered with prevention: the corrupt-registry path
#      emits a tamper audit event AND denies the external write, so a
#      corruption-based rewrite is both blocked and visible in the HMAC
#      audit chain. The read-path residual — read access under an added root
#      remains wholly undiscovered by this write-path guard — is unchanged.
#      Never sold as prevention. See ADR-183 §Residuals.

_SESSION_ROOTS_SCHEMA = 1
_SESSION_ROOTS_ALLOW_ENV = "CEO_SESSION_ROOTS_ALLOW"


def _session_roots_registry_path(repo_root: Path) -> Path:
    """Location of the session-roots registry written by the B1 observer."""
    return repo_root / ".claude" / "state" / "session-roots.json"


_SESSION_ROOTS_UNCANON_EMPTY = (
    "SESSION-ROOTS-WRITE-BLOCKED: session_root_path_uncanonicalizable "
    "— a write-target path in this event is empty, not a string, or "
    "carries an embedded NUL while session-registered workspace "
    "roots are active; a path the guard cannot canonicalize cannot "
    "be proven outside the registered roots. Security-matcher "
    "input → fail-closed (CLAUDE.md §4; PLAN-163 T3.1 / ADR-183)."
)


def _session_roots_partition_external(
    candidate_paths: List[str],
    repo_root: Path,
) -> Tuple[Optional[str], List[Tuple[str, str]]]:
    """Partition event write-targets into repo-internal vs external.

    Shared canonicalization core for ``_session_roots_guard``: used by BOTH
    the active-guard path (registry parsed, roots registered for this
    session) AND the corrupt-registry fail-CLOSED branch (FXγ / C3), so the
    two call sites agree byte-for-byte on what counts as an EXTERNAL write.
    A single source of truth here is a cross-state safeguard: it stops the
    corrupt-branch and the active-path external-detection from drifting apart
    and disagreeing on the same tool-input.

    Returns ``(uncanon_reason, external)``:
      * ``uncanon_reason`` is a fail-CLOSED block-reason string when ANY
        candidate cannot be canonicalized (not a str, empty, embedded NUL,
        or ``os.path.realpath`` raised). A path that cannot be proven
        repo-internal must not be waved through while a session-roots
        security condition is in force. ``external`` is ``[]`` in that case.
      * otherwise ``uncanon_reason`` is ``None`` and ``external`` lists the
        ``(original, realpath)`` pairs that resolve OUTSIDE ``repo_root``
        (repo-internal candidates are governed by the canonical stack above
        and are dropped here). If ``repo_root`` itself cannot be
        canonicalized, NO candidate can be proven internal → every candidate
        is treated as external (fail-CLOSED on an unknowable boundary).

    Pure: no emission, no raises out (realpath failures are caught and
    converted to the fail-CLOSED ``uncanon_reason`` return VALUE).
    """
    try:
        repo_rp = os.path.realpath(str(repo_root))  # type: Optional[str]
    except Exception:
        repo_rp = None

    external = []  # type: List[Tuple[str, str]]
    for cand in candidate_paths:
        # NUL/empty/non-str rejection is EXPLICIT (mirrors the control-char
        # rejection in _parse_scope_paths_from_text): since bpo-33721
        # (Py 3.8) os.path.realpath swallows the embedded-NUL ValueError and
        # returns the tainted string un-resolved, so the except branch below
        # never sees it — yet a NUL-bearing path is exactly the "cannot be
        # canonicalized" input class this matcher fail-CLOSES.
        if not isinstance(cand, str) or not cand or "\x00" in cand:
            return (_SESSION_ROOTS_UNCANON_EMPTY, [])
        try:
            rp = os.path.realpath(cand)
        except Exception:
            return (
                "SESSION-ROOTS-WRITE-BLOCKED: session_root_path_uncanonicalizable "
                f"— write-target path {cand!r} cannot be canonicalized "
                "(os.path.realpath raised) while session-registered workspace "
                "roots are active. Security-matcher input → fail-closed "
                "(CLAUDE.md §4; PLAN-163 T3.1 / ADR-183).",
                [],
            )
        if repo_rp is not None and (
            rp == repo_rp or rp.startswith(repo_rp + os.sep)
        ):
            continue  # repo-internal → governed by the canonical stack above
        external.append((cand, rp))
    return (None, external)


def _session_roots_guard(
    candidate_paths: List[str],
    repo_root: Path,
    session_id: str,
    env=None,
) -> Optional[str]:
    """Pure deny predicate for writes under session-registered roots.

    Returns a block-reason string (→ deny) or ``None`` (→ allow). The DENY
    path is PURE in the ``_candidate_is_granted`` sense: no emission side
    effects — the deny audit breadcrumb is a once-per-event concern owned
    by ``main()``. The ONE carve-out is the corrupt / unreadable /
    unknown-schema registry branch: a PRESENT-but-unparseable registry is a
    security-matcher INPUT-parse failure (FXγ / C3), so it fails CLOSED for
    external writes (deny) while allowing repo-internal writes, and it
    additionally fires a best-effort tamper audit event (H5 observability,
    see below) so a registry-rewrite attack is both blocked and visible.
    ``env`` defaults to ``os.environ`` (injectable for tests).

    Deny returns are VALUES, never raises: an unexpected raise out of this
    function is a hook bug (INFRA) and the ``main()`` call site fail-OPENs
    it with a breadcrumb, per the CLAUDE.md §4 split.
    """
    src_env = env if env is not None else os.environ

    # ---- Load registry (absent OR infra-read-error → silent allow;
    # ---- present-but-unparseable → fail-CLOSED for external writes) ----
    registry_path = _session_roots_registry_path(repo_root)
    try:
        if not registry_path.is_file():
            return None
    except OSError:
        return None
    # C3 (codex/grok R4+R5): read raw BYTES in a SEPARATE try — an OSError here
    # (PermissionError, IsADirectory, transient IO) is an INFRASTRUCTURE read
    # failure, NOT tampering, so it fails OPEN (allow), same as an ABSENT file.
    # Folding it into the parse `except Exception` below turned an infra read
    # error into a fail-CLOSED external-write DENY — a self-DoS. Reading BYTES
    # (not text) keeps the utf-8 DECODE inside the fail-closed parse block:
    # non-utf-8 bytes raise UnicodeDecodeError (IS-A ValueError, NOT OSError),
    # which is PRESENT-but-unparseable security-matcher input and MUST
    # fail-CLOSED — an earlier `read_text(encoding=...)` let that escape to the
    # caller's infra catch-all and wrongly ALLOW a binary registry overwrite
    # (R5). Only an OSError (bytes not readable at all) is INFRA -> allow.
    try:
        raw_bytes = registry_path.read_bytes()
    except OSError:
        return None
    try:
        data = json.loads(raw_bytes.decode("utf-8"))
        if not isinstance(data, dict):
            raise ValueError("registry root is not an object")
        if data.get("schema") != _SESSION_ROOTS_SCHEMA:
            raise ValueError("unknown registry schema")
        sessions = data.get("sessions")
        if not isinstance(sessions, dict):
            raise ValueError("registry 'sessions' is not an object")
    except Exception as exc:  # registry PRESENT + readable but unparseable
        print(
            "[check_canonical_edit] session-roots registry unreadable "
            f"({type(exc).__name__}); present-but-unparseable security-matcher "
            "input → fail-CLOSED for external writes; repo-internal writes stay "
            f"governed by the canonical stack. registry={registry_path}",
            file=sys.stderr,
        )
        # FXγ (C3) — DOCTRINE CORRECTION. A registry that EXISTS but cannot be
        # parsed (corrupt JSON, unknown schema-version, malformed `sessions`)
        # is PRESENT-but-unparseable security-matcher input, NOT an
        # ABSENT-file INFRA condition, so per CLAUDE.md §4 it fails CLOSED —
        # content the guard cannot parse is blocked, never waved through. The
        # deny is SCOPED to writes we cannot prove repo-internal (the new
        # surface an added root could have opened); repo-internal writes stay
        # governed by the canonical stack above (unaffected). Registry ABSENT
        # (handled earlier) remains an allow — the observer may simply not
        # have run.
        #
        # H5 observability is preserved and now UNCONDITIONAL: whether or not
        # this event carries an external write, the corruption is recorded in
        # the HMAC audit chain so a registry-rewrite attack leaves a forensic
        # trace. Emitted BEFORE the partition so even the allow (repo-internal
        # only) branch records the tamper. Best-effort; never raises.
        _audit_registry_unreadable(registry_path, type(exc).__name__)
        uncanon_reason, external = _session_roots_partition_external(
            candidate_paths, repo_root
        )
        if uncanon_reason is not None or external:
            # At least one write-target cannot be proven repo-internal while
            # the registry — the very state that tells us whether a root was
            # added — is unparseable. The write boundary is unknowable →
            # deny fail-CLOSED until the registry is repaired.
            return (
                "SESSION-ROOTS-WRITE-BLOCKED: session_roots_registry_unreadable "
                "— the session-roots registry "
                "(.claude/state/session-roots.json) is PRESENT but could not be "
                "parsed (corrupt JSON, unknown schema-version, or a malformed "
                "'sessions' object). A present-but-unparseable security-matcher "
                "input cannot prove this write stays inside the project root, "
                "so writes OUTSIDE the repo are denied fail-closed (CLAUDE.md "
                "§4) until the registry is repaired or removed. Repo-internal "
                "writes remain governed by the canonical stack; the corruption "
                "is recorded in the HMAC audit chain. PLAN-163 T3.1 / ADR-183; "
                "H5."
            )
        return None  # all writes provably repo-internal → canonical stack

    sid = (session_id or "").strip()
    # M1 (PLAN-163 T3.1 / ADR-183) — an ABSENT/empty session_id while the
    # registry holds registered sessions is a security-matcher input the
    # guard cannot bind to a session, yet roots DO exist → the write
    # boundary is unknowable → fail-CLOSED (CLAUDE.md §4). Denying here
    # means clearing CLAUDE_SESSION_ID cannot silently neutralize the
    # guard. Only EXTERNAL writes are denied (repo-internal writes stay
    # governed by the canonical stack above); the deny is emitted below,
    # after the fail-CLOSED input resolution, once ``external`` is known.
    sid_missing_with_registry = (not sid) and bool(sessions)
    if sid_missing_with_registry:
        roots = []  # boundary unknowable; external writes denied below
    else:
        sess = sessions.get(sid)
        if not isinstance(sess, dict):
            return None  # no roots registered for THIS session
        roots = sess.get("roots")
        if not isinstance(roots, list) or not roots:
            return None

    # ---- Guard is ACTIVE for this session. Resolve inputs fail-CLOSED ----
    # Allowlist: CEO_SESSION_ROOTS_ALLOW, os.pathsep-separated directory
    # list, compared by realpath.
    allow_rps: Set[str] = set()
    for tok in (src_env.get(_SESSION_ROOTS_ALLOW_ENV) or "").split(os.pathsep):
        tok = tok.strip()
        if not tok:
            continue
        try:
            allow_rps.add(os.path.realpath(tok))
        except (OSError, ValueError):
            continue  # a broken allowlist token allows nothing

    # Resolve inputs + partition repo-internal vs external through the SHARED
    # core (also used by the corrupt-registry FXγ branch above) so the two
    # sites cannot drift on what "external" means. Uncanonicalizable input →
    # fail-CLOSED; repo-internal candidates are governed by the canonical
    # stack above and are dropped.
    uncanon_reason, external = _session_roots_partition_external(
        candidate_paths, repo_root
    )
    if uncanon_reason is not None:
        return uncanon_reason
    if not external:
        return None

    if sid_missing_with_registry:
        # M1 fail-CLOSED: session identity is absent but the registry is
        # non-empty and this event has external write targets → deny.
        return (
            "SESSION-ROOTS-WRITE-BLOCKED: session_id_missing — this "
            "canonical-edit event carries no session_id (absent/empty) "
            "while the session-roots registry holds registered workspace "
            "roots, so the write cannot be bound to a session and the "
            "boundary is unknowable. Writes outside the project root are "
            "denied fail-closed so that clearing CLAUDE_SESSION_ID cannot "
            "neutralize the guard (CLAUDE.md §4; PLAN-163 T3.1 / ADR-183)."
        )

    for entry in roots:
        directory = entry.get("directory") if isinstance(entry, dict) else None
        if (
            not isinstance(entry, dict)
            or entry.get("unparseable")
            or not isinstance(directory, str)
            or not directory
            or "\x00" in directory
            or not os.path.isabs(directory)
        ):
            # A root WAS registered for this session but its boundary is
            # unknowable (observer marked it unparseable, the entry is
            # structurally malformed, or — M2 — its `directory` is not an
            # ABSOLUTE path: a relative value would be silently resolved
            # against the process CWD by os.path.realpath below and
            # mis-scope the boundary, so it is rejected in the same
            # fail-CLOSED class as unparseable). Like a corrupt whole-registry
            # (present-but-unparseable → fail-CLOSED for external writes), here
            # we positively know the session's write
            # surface grew and cannot bound it → every non-repo write is
            # denied until the entry is repaired (fail-CLOSED in the
            # consumer, PLAN-163 T3.1).
            return (
                "SESSION-ROOTS-WRITE-BLOCKED: session_root_unparseable — this "
                "session has a registered workspace root whose directory could "
                "not be parsed (entry marked unparseable or malformed in "
                ".claude/state/session-roots.json), so the session's write "
                "boundary is unknowable. Writes outside the project root are "
                "denied fail-closed until the registry entry is repaired "
                "(PLAN-163 T3.1 / ADR-183)."
            )
        try:
            root_rp = os.path.realpath(directory)
        except Exception:
            return (
                "SESSION-ROOTS-WRITE-BLOCKED: session_root_unparseable — a "
                "registered workspace root for this session cannot be "
                "canonicalized (os.path.realpath raised); the session's write "
                "boundary is unknowable. Writes outside the project root are "
                "denied fail-closed (PLAN-163 T3.1 / ADR-183)."
            )
        if root_rp in allow_rps:
            continue  # Owner explicitly allowlisted this root
        for cand, rp in external:
            if rp == root_rp or rp.startswith(root_rp + os.sep):
                return (
                    "SESSION-ROOTS-WRITE-BLOCKED: session_root_write_denied — "
                    f"write target '{cand}' resolves to '{rp}', inside the "
                    f"session-registered workspace root '{root_rp}' "
                    f"(source={entry.get('source') or 'unknown'}). "
                    "DirectoryAdded (CC 2.1.220) is notification-only and "
                    "post-facto, so added roots are writable-by-default at "
                    "the permission layer; this framework denies such writes "
                    "by default. To allow, add the root's realpath to "
                    f"{_SESSION_ROOTS_ALLOW_ENV} (os.pathsep-separated) and "
                    "retry. PLAN-163 T3.1 / ADR-183."
                )
    return None


def _audit_registry_unreadable(registry_path: Path, exc_name: str) -> None:
    """Best-effort tamper-observability emit for a corrupt / unreadable /
    unknown-schema session-roots registry (H5).

    The guard fails CLOSED for external writes on this condition (FXγ / C3:
    a present-but-unparseable registry is a security-matcher INPUT-parse
    failure, not an ABSENT-file INFRA allow) while allowing repo-internal
    writes. This emit runs UNCONDITIONALLY — before the external/internal
    partition — so that even the repo-internal allow path records the
    corruption: an adversary corrupting or truncating the repo-internal,
    agent-writable ``.claude/state/session-roots.json`` is both BLOCKED (for
    the external write it opened) and OBSERVABLE in the HMAC-chained audit
    log. Reuses the already-registered ``veto_triggered`` action (NO new
    action invented — see ADR-183 §Residuals) with a distinct ``reason_code``.
    hasattr-guarded; never raises; no-value-echo — the breadcrumb carries the
    registry PATH and the exception CLASS name only, never registry bytes or
    tool-input content.
    """
    try:
        from _lib import audit_emit
        if not hasattr(audit_emit, "emit_veto_triggered"):
            return
        audit_emit.emit_veto_triggered(
            hook="check_canonical_edit",
            reason_code="session_roots_registry_unreadable",
            reason_preview=(
                "session-roots registry unreadable/corrupt/unknown-schema; "
                "fail-CLOSED for external writes (FXγ) + tamper recorded; "
                f"exc={exc_name}; registry={registry_path}"
            ),
            blocked_tool=_blocked_tool_field(),  # PLAN162_FIX_9
            project=os.environ.get("CLAUDE_PROJECT_DIR") or "",
        )
    except Exception:
        return


def _audit_session_root_block(target: str) -> None:
    """Best-effort veto_triggered emit for a session-roots deny.

    Mirrors ``_audit_block``: never raises; no-value-echo (the breadcrumb
    carries the target PATH only, never tool-input content).
    """
    try:
        from _lib import audit_emit
        audit_emit.emit_veto_triggered(
            hook="check_canonical_edit",
            reason_code="session_root_write_denied",
            reason_preview=(
                f"blocked write under session-registered root; target={target}"
            ),
            blocked_tool=_blocked_tool_field(),  # PLAN162_FIX_9
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


def _cli_is_canonical(args: List[str]) -> int:
    """PLAN-156-FOLLOWUP F5 (debate C2(b)) — read-only canonical-path
    classification ORACLE.

    Single-source-of-truth CLI so shell consumers (the grok/codex pre-push
    review gates) classify paths with the SAME ``_is_canonical`` predicate
    the edit-time guard and the Stop-review recorder use — re-implementing
    the guard glob list in bash IS the drift class F5 fixes.

    Usage:
        python3 check_canonical_edit.py --is-canonical <path>...
        python3 check_canonical_edit.py --is-canonical -   # paths on stdin,
                                                           # one per line
                                                           # (ARG_MAX-safe)

    Output: one line per input path, ``<path>\\t<0|1>`` (1 = canonical),
    in input order. Exit 0 on successful classification of every path.
    Exit 2 when no path argument/stdin is supplied (consumers must treat
    ANY nonzero exit as oracle failure and fall back fail-CLOSED to their
    coarse over-triggering classifier).

    Contract notes:
    - Pure read-only classification. NO hook semantics run in this mode:
      no event parse, no adapter, no sentinel lookup, no emission on the
      hook wire. The hook entry (``main()``) is byte-identical when the
      script is invoked as a hook (argv empty — ``_python-hook.sh`` passes
      no arguments).
    - Repo root resolves exactly like the hook path does
      (``CLAUDE_PROJECT_DIR`` or cwd — see ``main()``), so oracle and hook
      can never disagree on anchoring.
    - Per-path classification fault → that path is reported ``1``
      (canonical). Over-triggering review on an unclassifiable path is the
      safe direction (fail-CLOSED); under-triggering would let an
      unreviewed L3 touch through. ``_is_canonical`` itself already
      returns False for paths outside the repo root — that is the
      oracle's own semantics, not a fault.
    """
    repo_root = Path(os.environ.get("CLAUDE_PROJECT_DIR") or os.getcwd())
    paths: List[str] = list(args)
    if paths == ["-"]:
        paths = [ln.rstrip("\n") for ln in sys.stdin.read().splitlines()]
        paths = [p for p in paths if p]
    if not paths:
        sys.stderr.write(
            "usage: check_canonical_edit.py --is-canonical <path>... | -\n"
        )
        return 2
    out_lines: List[str] = []
    for raw in paths:
        try:
            flag = 1 if _is_canonical(raw, repo_root) else 0
        except Exception:
            # Fail-CLOSED per path: unclassifiable → treat as canonical
            # (over-trigger review, never under-trigger).
            flag = 1
        out_lines.append("%s\t%d" % (raw, flag))
    sys.stdout.write("\n".join(out_lines) + "\n")
    return 0


def main() -> int:
    """Hook entry point.

    PLAN162_FIX_1 / PLAN162_FIX_9 wrapper: arms the per-invocation
    wall-clock deadline (consensus C2/C3/S8) around the real entry point
    and clears BOTH pieces of invocation-scoped module state in a
    ``finally``. Without the reset, a module-scope deadline (or a stale
    tool name) armed by one in-process invocation would leak into the
    next caller in the same process — the test suite drives ``decide()``
    and ``main()`` in-process, and an expired leftover deadline would
    fail those closed for no reason at all.
    """
    global _CURRENT_TOOL_NAME
    _start_wall_budget()
    try:
        return _main_guarded()
    finally:
        _reset_wall_budget()
        _CURRENT_TOOL_NAME = ""


def _main_guarded() -> int:
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
        # PLAN162_FIX_5B (finding #5b, consensus C4). HEAD emitted a bare
        # ALLOW here. ``parse_error`` is, by name and by construction, the
        # signal that the PAYLOAD did not parse — INPUT, not
        # infrastructure — and CLAUDE.md §4 is literal about that split:
        # fail-open on INFRASTRUCTURE, fail-CLOSED on INPUT. The sibling
        # kernel hook already implements this exact form; THIS hook was
        # the drift.
        #
        # The council justified the old posture by citing "the ADR-010
        # fail-open contract". That citation is FALSE: ADR-010 contains
        # zero occurrences of any failure-posture text. The only such text
        # is this hook's own module docstring, so citing it as the ADR
        # that authorizes it is circular.
        #
        # 5a (``read_event`` RAISING, above) stays fail-OPEN — that IS a
        # genuine infrastructure failure, and the kernel sibling is
        # fail-open identically there.
        _emit_legacy_decision_json(
            _emit_block(
                reason=(
                    "CANONICAL-EDIT-BLOCKED: canonical_edit_payload_parse_error "
                    "— the PreToolUse payload could not be parsed, so this "
                    "edit-class event cannot be proven non-canonical. "
                    "Security-matcher INPUT failure → fail-closed "
                    "(CLAUDE.md §4; PLAN-162 finding #5b). Re-issue the tool "
                    "call with a well-formed payload."
                )
            ),
            _adapter,
            event,
        )
        return 0

    # PLAN-065 Layer A (S81-tris gap closure, 2026-05-04):
    # When tool_name is mcp__*, the adapter's `event.file_path` field
    # may be empty (custom MCP tools don't use the standard
    # Edit/Write/MultiEdit `file_path` key). Inspect tool_input directly
    # for write-shape parameters and resolve all candidate paths.
    # Each candidate is gated independently; if ANY candidate is
    # canonical without sentinel coverage, block.
    tool_name = (event.tool_name or "").strip()
    # PLAN162_FIX_9 — publish the EVENT's tool name (validated at read
    # time, not here) for the four audit sites that record ``blocked_tool``.
    global _CURRENT_TOOL_NAME
    _CURRENT_TOOL_NAME = tool_name
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

    # Layer A: gate a multi-candidate event using the MOST RESTRICTIVE
    # canonical candidate. Historically mcp__*-only; PLAN-155 extends the
    # scan to any multi-candidate event (apply_patch multi-file, S265
    # P1#3). Single-candidate events (every Claude Code Edit/Write) skip
    # this block entirely — byte-identical fast path.
    #
    # PLAN160_FIX_A (finding A — multi-candidate gate bypass): the prior
    # loop ``break``-ed at the FIRST canonical candidate and gated ONLY
    # that path via decide(). A multi-file MCP event whose first canonical
    # candidate was sentinel-GRANTED let every LATER canonical candidate
    # ride through UNGATED. The fix scans ALL candidates and selects the
    # OFFENDING candidate (canonical + ungranted) if any —
    # most-restrictive-wins — so decide() is still invoked at most ONCE
    # (emit-once: decide() fires _emit_persona_coverage_synthesized on the
    # allow path; a per-candidate decide() would double-emit).
    #
    # ``_forced_out``: a pre-built decision that BYPASSES decide(). Set for
    # the two fail-CLOSED cases that must NOT be re-routed through decide()
    # — over-cap, and any scan fault (classification OR sentinel discovery).
    # Routing a classification-fault candidate through decide() would
    # re-raise inside decide(), and the outer handler below would then
    # fail-classify it as non-canonical and ALLOW (the V-A hole the codex
    # pair-rail REJECTed). ``_find_sentinels`` is loaded LAZILY, only once a
    # canonical candidate is seen, and the whole scan is wrapped so a
    # sentinel-discovery fault fail-CLOSES with an emit instead of
    # propagating out of main() (zero-emit hole).
    _multi = tool_name.startswith("mcp__") or len(candidate_paths) > 1
    _forced_out = None
    if _multi:
        try:
            if len(candidate_paths) > _PLAN160_MAX_CANDIDATES:
                # Fail-CLOSED: more candidates than we will classify —
                # cannot prove every canonical candidate is granted, so
                # block the whole event rather than truncate the scan and
                # risk an unexamined offender beyond the cap.
                _forced_out = _emit_block(
                    reason=(
                        "CANONICAL-EDIT-BLOCKED: canonical_edit_hook_fault — "
                        f"multi-candidate event carries {len(candidate_paths)} "
                        f"paths (> cap {_PLAN160_MAX_CANDIDATES}); cannot clear "
                        "all — fail-closed. PLAN-160 finding A."
                    )
                )
            else:
                sentinels = None  # lazy: only load once a canonical candidate exists
                first_canonical = None
                offender = None
                for candidate in candidate_paths:
                    # PLAN162_FIX_1 (C2) — the second sentinel-loop site.
                    # Fail-CLOSED on an elapsed budget: a multi-candidate
                    # event we could not finish clearing is exactly the
                    # event that must not ride through.
                    if _wall_budget_expired():
                        _forced_out = _emit_block(
                            reason=_WALL_DEADLINE_BLOCK_REASON
                        )
                        break
                    if not _is_canonical(candidate, repo_root):
                        continue
                    if first_canonical is None:
                        first_canonical = candidate
                    if sentinels is None:
                        sentinels = _find_sentinels(repo_root)
                    if not _candidate_is_granted(candidate, repo_root, sentinels):
                        offender = candidate
                        break
                # decide() runs ONCE: on the offender (→ block naming it) if
                # any, else the first canonical candidate (→ sentinel allow +
                # persona coverage), else candidate_paths[0] (non-canonical →
                # allow).
                file_path = offender or first_canonical or file_path
        except Exception as _scan_exc:
            # Classification OR sentinel-discovery fault on a MULTI-candidate
            # event → fail-CLOSED with an emit. We are on a multi-file event
            # we could not fully clear; a re-route through decide() would
            # re-raise on the unclassifiable path and the outer handler would
            # ALLOW it (V-A). Blocking here is the only safe outcome.
            print(
                f"[check_canonical_edit] SCAN FAULT: "
                f"{type(_scan_exc).__name__}: {_scan_exc}",
                file=sys.stderr,
            )
            _forced_out = _emit_block(
                reason=(
                    "CANONICAL-EDIT-BLOCKED: canonical_edit_hook_fault — "
                    f"multi-candidate scan fault ({type(_scan_exc).__name__}); "
                    "fail-closed. PLAN-160 finding A."
                )
            )

    if _forced_out is not None:
        # Pre-built fail-closed decision (over-cap or scan fault). Emit
        # through the same legacy seam + best-effort veto audit as a normal
        # block, BYPASSING decide() — routing a scan-fault path through
        # decide() would re-raise and the outer handler would fail-OPEN
        # (the V-A hole the codex pair-rail REJECTed).
        _fparsed = json.loads(_forced_out)
        if _fparsed.get("decision") == "block":
            # Forensic breadcrumb only. On over-cap / scan-fault the specific
            # offending candidate is unknown or unreachable, so we record the
            # event's FIRST candidate (not necessarily the offender); the
            # fail-CLOSED decision itself is correct regardless.
            _audit_block(
                candidate_paths[0] if candidate_paths else file_path,
                _safe_sentinel_count(repo_root),
                reason_code=_block_reason_code(_fparsed.get("reason", "")),
            )
        _emit_legacy_decision_json(_forced_out, _adapter, event)
        return 0

    # Single-candidate hot path (and the all-canonical-granted multi path)
    # reaches decide() here. SECURITY INVARIANT: this call is NOT wrapped by
    # the multi-candidate fail-CLOSED scan above, so its safety relies on
    # ``_is_canonical`` / ``_repo_rels`` being TOTAL (never raising on str
    # input — guaranteed by their broad ``except Exception``, PLAN160_FIX_D,
    # and fenced by the totality unit tests). If a future refactor
    # reintroduces a raise in classification, the outer handler below
    # re-classifies and could fail-OPEN a single-candidate canonical edit —
    # keep the totality tests as the regression fence.
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
        _audit_block(
            rel,
            _safe_sentinel_count(repo_root),
            reason_code=_block_reason_code(parsed.get("reason", "")),
        )

    # PLAN-163 T3.1 — session-roots write-guard (DirectoryAdded consumer).
    # Runs AFTER the existing project-relative checks and ONLY on a
    # would-allow event, so it never relaxes the sentinel gate — it can
    # only ADD a deny. Checks EVERY candidate path of the event (the
    # multi-candidate list built above), by absolute realpath, against the
    # session-registered roots in .claude/state/session-roots.json.
    if parsed.get("decision") != "block":
        try:
            _sr_sid = (
                (getattr(event, "session_id", "") or "").strip()
                or (os.environ.get("CLAUDE_SESSION_ID") or "").strip()
            )
            _sr_reason = _session_roots_guard(
                candidate_paths, repo_root, _sr_sid
            )
        except Exception as _sr_exc:
            # An unexpected raise here is a hook bug (INFRA) → fail-open
            # with a breadcrumb; every INPUT-shaped failure inside the
            # guard already returns a deny VALUE instead of raising.
            print(
                "[check_canonical_edit] session-roots guard fault: "
                f"{type(_sr_exc).__name__}: {_sr_exc}",
                file=sys.stderr,
            )
            _sr_reason = None
        if _sr_reason is not None:
            _audit_session_root_block(
                candidate_paths[0] if candidate_paths else file_path
            )
            _emit_legacy_decision_json(
                _emit_block(_sr_reason), _adapter, event
            )
            return 0

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
    # PLAN-156-FOLLOWUP F5 — oracle CLI mode is gated on an EXPLICIT argv
    # sentinel so hook invocations (argv always empty: `_python-hook.sh`
    # execs `$FOUND_PY $HOOK_SCRIPT "$@"` with no extra args from
    # settings.json) can never reach it. Any other argv shape falls
    # through to the unchanged hook entry.
    if len(sys.argv) >= 2 and sys.argv[1] == "--is-canonical":
        sys.exit(_cli_is_canonical(sys.argv[2:]))
    sys.exit(main())
