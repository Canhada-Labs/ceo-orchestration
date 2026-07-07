# What degrades outside Claude Code

**Audience:** anyone opening this repo (or a repo with the framework
installed) in something other than Claude Code — a plain editor, a bare
terminal, a CI bot, or another AI coding harness.
**Status:** honest disclosure. This page fronts future harness-compatibility
work (see [adapters.md](adapters.md)); it makes no compatibility claim today.

The framework's enforcement lives in the **hook rail**: Claude Code invokes
the Python scripts registered in `.claude/settings.json` on its lifecycle
events (`PreToolUse`, `PostToolUse`, `SessionStart`, `Stop`, …). Every block,
every audit append, every ceremony check happens because the harness fires
those events. Outside the harness, no event fires — so no hook runs. The
governance layer degrades from *enforced* to *documented*.

This is not a defect of any other tool; it is where the enforcement
boundary sits. The hooks themselves are harness-agnostic by design (they
read a normalized event via an adapter layer, ADR-008), but as of today the
`claude` adapter is the only production one — the others are stubs. See
[adapters.md](adapters.md).

---

## Rail by rail

| Rail | In Claude Code | Outside Claude Code |
|------|----------------|---------------------|
| Canonical-edit guard (`check_canonical_edit.py`) | PreToolUse blocks `Edit`/`Write`/`MultiEdit` and write-shaped `mcp__*` calls against canonical governance paths unless an Owner-signed GPG sentinel exists | Nothing intercepts. Any editor writes `team.md`, hooks, or skills freely. Remaining backstops are server-side: CODEOWNERS + branch protection ([threat-model.md](threat-model.md), T-003 residual risk) |
| Arbitration-kernel hard-deny (`check_arbitration_kernel.py`) | The guard hooks and `_lib` primitives *themselves* cannot be edited, even with a sentinel (only an explicit audited override) | Those files are editable like any others |
| Bash safety (`check_bash_safety.py`) | Destructive commands (`rm -rf` flag combos, `git reset --hard`, force-push) are blocked before execution | No pre-execution gate; your shell runs whatever is typed |
| Spawn governance (`check_agent_spawn.py`) | Agent spawns without the required profile/skill/file-assignment sections are blocked | There is no `Agent` tool at all; the spawn protocol is prose in `.claude/team.md` |
| Plan lifecycle (`check_plan_edit.py`) | Illegal plan-status transitions are blocked at edit time | Convention only at edit time; some drift is caught later by CI schema checks, at push |
| Skill-patch + VETO-floor sentinels (`check_skill_patch_sentinel.py`, `check_tier_policy.py`) | `SKILL.md` edits require a signed SP-NNN proposal; reviewer-agent `model:` changes require a dedicated sentinel | Gone at edit time; CI + CODEOWNERS partially compensate at push |
| Pair-rail review (`check_pair_rail.py`, `check_codex_filewrite.py`) | Edits to L3+ canonical paths automatically trigger a second-model review; write-shaped reviewer output is blocked | Manual only. The reviewer CLI still runs from any shell, but nothing forces the review to happen or screens what comes back |
| HMAC audit chain (`audit_log.py` + lifecycle hooks) | Every agent spawn, edit, and ceremony is appended to the HMAC-chained log | The chain **freezes** — work done outside appends nothing. `verify_chain()` still detects tampering of the *existing* log (see below), but it cannot record what never reached it. Absence of entries is not evidence of absence of activity |
| Vetoes, debates, three-strike rule ([../PROTOCOL.md](../PROTOCOL.md), `/debate`) | Slash-command ceremony with hook-checked artifacts; vetoes are hard blocks | Prose conventions. The debate/veto artifacts on disk are still readable — and writable by hand — but nothing gates execution on them |
| Injection & secret scanners (`check_output_secrets.py`, `check_webfetch_injection.py`, `check_mcp_response.py`, `check_read_injection.py`, …) | Advisory scans over tool traffic (web content, MCP responses, file reads, tool output) | There is no tool traffic to scan |
| Permission deny rules (`permissions.deny` in `.claude/settings.json`) | The harness refuses tool calls against `PROTOCOL.md`, `SPEC/**`, `settings.json`, and `git push --force` | Inert JSON |
| Session lifecycle + config tripwires (`SessionStart`/`SessionEnd`/`ConfigChange` hooks) | Boot health checks, closeout drains, out-of-band `settings.json` tamper observation | Never fire. The `ConfigChange` guard's own registration documents this boundary: it is blind to outside-harness edits by design |

The pattern: **every row's left column is harness-hosted.** A human or
agent editing this repo outside Claude Code is trusted, not gated.

---

## What still works

Everything that is a *record* or a *plain script* survives, because the
runtime is stdlib-only Python ≥ 3.9 and the artifacts are markdown.

- **The records.** Plans (`.claude/plans/`), ADRs (`.claude/adr/`), debate
  transcripts, [../PROTOCOL.md](../PROTOCOL.md), and the schemas
  (`.claude/plans/PLAN-SCHEMA.md`, `.claude/plans/DEBATE-SCHEMA.md`) are
  ordinary files. They remain the durable audit trail of *decisions* even
  when the runtime rail is off.
- **Audit verification.** The chain verifier is a standalone CLI:

  ```bash
  python3 .claude/scripts/audit-verify-chain.py
  ```

  Exit 0 iff the recorded chain is intact; tamper is reported line-by-line.
  Honest scope: it detects in-place edits and breaks in the chain that was
  written; per its own docstring it does not detect tail truncation by
  itself (that is the external anchor's job) nor rollback to an older
  log+key snapshot pair — and it says nothing about actions taken while no
  hook was appending.
- **The operational scripts.** The verification set in
  [GOVERNANCE.md §How to verify your install](GOVERNANCE.md) runs from any
  shell: `ceo-diagnose.py`, `validate-governance.sh`,
  `audit-verify-chain.py`, `audit-query.py`. So do the tests
  (`make test-collect`, pytest).
- **Server-side gates.** The CI workflows under `.github/workflows/`
  (governance validation, contamination, count drift), CODEOWNERS, and
  branch protection run on push regardless of what edited the files. They
  are coarser and later than the hook rail — push-time, not edit-time —
  but they are harness-independent.
- **Manual pair-rail.** The second-model review is a CLI invocation you can
  run yourself before merging. What you lose is the *automation and the
  gate*: outside the harness, running it is a habit, not a rule.

---

## Honest bottom line

Outside Claude Code, this framework is **documentation plus offline
verification plus server-side CI** — not a governance layer. The hook rail
is the product, and the hook rail is hosted by the harness:

- Prevention (canonical-edit guard, bash safety, spawn governance, kernel
  hard-deny) → **gone** at edit time.
- Evidence (HMAC audit chain) → **frozen**; existing history stays
  tamper-evident, new history is simply not written.
- Process (debates, vetoes, three-strike) → **prose** that a disciplined
  operator can follow and an undisciplined one can skip silently.
- Backstops (CI, CODEOWNERS, branch protection) → **still on**, but they
  fire at push time and see diffs, not intent.

If your team works across multiple harnesses today, treat a non-Claude-Code
session the way you would treat any un-hooked shell session: assume no
local gate fired, rely on the push-time gates, and run
`audit-verify-chain.py` plus `validate-governance.sh` before trusting
state. Making other harnesses first-class citizens of the hook rail is
future work tracked through the adapter layer ([adapters.md](adapters.md));
until an adapter is marked production there, no enforcement claim is made
for it. See also [HONEST-LIMITATIONS.md](HONEST-LIMITATIONS.md).
