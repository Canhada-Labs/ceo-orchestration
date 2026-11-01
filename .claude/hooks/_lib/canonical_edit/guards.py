"""Mechanically extracted canonical-edit declarations."""
from __future__ import annotations
import re

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

__all__ = ['_CANONICAL_GUARDS', '_MCP_WRITE_PATH_KEYS', '_APPROVED_BY_RE', '_AMENDS_RE', '_SCOPE_HEADER_RE', '_SCOPE_TERMINATOR_RE', '_SCOPE_HR_RE', '_SCOPE_MARKER_RE', '_SCOPE_MARKER_CAP_BYTES', '_BEGIN_MARKER_RE', '_EDIT_CLASS_TOOLS', '_MCP_TOOL_NAME_RE', '_BLOCKED_TOOL_UNKNOWN']
