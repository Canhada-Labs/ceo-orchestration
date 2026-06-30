# SPEC v1 — claude-sdk-compat (Claude Agent SDK / Claude Code CLI version pinning)

> **Source plan:** PLAN-056 Phase 2 (Claude Agent SDK compat matrix)
> **Companion ADR:** to be assigned at promotion (next available number)
> **Spec version:** 1.0.0-rc.1
> **Status:** STAGED — awaits Owner sentinel for promotion to canonical
> `SPEC/v1/claude-sdk-compat.md`.

## Purpose

Protect ceo-orchestration adopters from bit-rot when the Claude Agent
SDK (Anthropic upstream) ships a breaking change to:

- Hook lifecycle contract (PreToolUse / PostToolUse / SessionStart /
  SessionEnd / UserPromptSubmit invocation order or signature)
- MCP server contract (tool name namespacing, response shape, transport)
- `permission_mode` signature (env var, CLI flag, settings.json field)
- Tool universe (new tools added that change matcher patterns)
- Settings.json schema (top-level field renames)

Today the framework consumes Claude Code CLI as `claude` binary at
runtime. There is no version pin. A breaking-change release in
upstream Claude Agent SDK could silently break governance hooks
without our CI catching it.

## Tested-against matrix (GREEN — known-compatible)

| Claude Code CLI version | Tested in (commit) | Notes |
|---|---|---|
| `claude-code v1.0.x` | < 2026-04-01 baseline | hook lifecycle pre-ADR-056 expansion |
| `claude-code v1.1.x` | 2026-04-15 (PLAN-051 Phase 6) | ADR-056 lifecycle expansion (SessionStart + SessionEnd hooks added) |
| `claude-code v1.2.x` | 2026-04-22 (PLAN-050 Phase 7a) | ADR-058 brainstorm + spec-context support |
| `claude-code v1.3.x` | 2026-04-25 (PLAN-058) | ADR-077 WebFetch hook + injection patterns |
| `claude-code v1.4.x` | 2026-04-27 (PLAN-052) | ADR-083 MCP scanner + matcher `mcp__.*` |
| `claude-code v2.0.x` | 2026-04-27 (Session 67) | major rev; backward-compat verified by full-suite test green |
| `claude-code v2.1.x` | 2026-04-27 (Session 67 dev environment) | currently-running adopter version; full-suite test green at v2.1.119 |

## Known-incompatible matrix (RED — fail-closed)

| Version | Reason | Workaround |
|---|---|---|
| (none currently flagged) | — | — |

If Anthropic ships a breaking change that causes test-suite regressions
without code change on our side, the new version goes here with
remediation steps.

## Pin policy

- **Major.Minor** is the floor declared in this spec: `v1.4.x`.
- **Patch** is unpinned (1.4.0 == 1.4.99 for our purposes).
- **Major bump** triggers CI gate (advisory).
- **Minor bump** triggers smoke test (advisory; runs full pytest).

The framework does NOT install or vendor a specific CLI version.
Adopter projects bring their own Claude Code installation; the
compat matrix is informational + advisory CI gate.

## CI gate behavior

`.claude/scripts/check-sdk-compat.sh` (new in PLAN-056 Phase 2):

- Reads `claude --version` output (or `$CLAUDE_VERSION` env override
  for CI).
- Compares against the tested-against matrix.
- **Fail-open** on unlisted versions (warning, exit 0). Adopters may
  be on newer SDK; do not block their build.
- **Fail-closed** on known-incompatible versions (error, exit 1).
  Block until Owner amends matrix.
- **Skip silently** if `claude` binary not in PATH (developer
  environment without CLI).

## Breaking-change categories (informational)

When a category-X breaking change ships upstream, the framework's
response is documented per category:

| Category | Example | ceo-orchestration response |
|---|---|---|
| **Hook lifecycle** | New hook event (e.g. `PreSubAgentSpawn`) | Add registration in `settings.json`, no breaking-change for adopters |
| **Hook input shape** | Field rename (e.g. `tool_name` → `toolName`) | Update `_python-hook.sh` shim or hook-specific parsers; emit warning |
| **MCP contract** | Tool namespace change | Update `_lib/mcp_injection_scan.py:is_mcp_tool_name` regex |
| **`permission_mode` semantics** | New mode added | Update CLAUDE.md + spawn protocol docs |
| **Tool universe** | New tool requires hook coverage | New PostToolUse matcher entry |
| **Settings.json schema** | Top-level field rename | Migration script in `scripts/upgrade.sh` |

## Adoption guidance

For framework adopters:

1. Run `claude --version` in your CI before invoking framework hooks.
2. Add `bash .claude/scripts/check-sdk-compat.sh` as advisory step
   in your CI workflow.
3. If the script warns "version unlisted", file a brief issue —
   we update the matrix on confirmed-green.
4. If the script errors "known-incompatible", upgrade or downgrade
   to a green version; do not bypass.

## Maintenance

This spec is updated:

- **Every framework minor release** — bump tested-against floor.
- **On Anthropic breaking change** — add row to known-incompatible.
- **On adopter-reported regression** — investigate + add row if
  reproduced.

Updates are doc-only; no code change required for matrix edits
(but typically paired with `.claude/scripts/check-sdk-compat.sh`
adjustment).

## Version history

| SPEC version | Source commit | Notes |
|---|---|---|
| 1.0.0-rc.1 | PLAN-056 Phase 2 | Initial publication; floor v1.4.x; no known-incompatible. |

## References

- ADR-085 — Framework landscape Claude-only (parent)
- PLAN-056 Phase 2 — original proposal (this spec is the deliverable)
- `.claude/scripts/check-sdk-compat.sh` — companion CI gate
- `.claude/scripts/tests/test_check_sdk_compat.py` — companion tests
