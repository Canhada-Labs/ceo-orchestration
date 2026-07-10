# What degrades outside Claude Code

**Audience:** anyone opening this repo (or a repo with the framework
installed) in something other than Claude Code — a plain editor, a bare
terminal, a CI bot, or another AI coding harness.
**Status:** honest disclosure. Two harnesses now host the enforcement rail
— **Claude Code** (default) and **OpenAI Codex CLI** (per-rail, verified
against codex-cli 0.139.0; see [adapters.md](adapters.md) and
[provider_capability_matrix.md](provider_capability_matrix.md)). This page
covers what happens under Codex (a real per-rail matrix, not a blanket
claim) **and** the unchanged case of no harness at all (plain editor, CI,
an un-adaptered harness).

The framework's enforcement lives in the **hook rail**: a harness invokes
the Python scripts registered on its lifecycle events (`PreToolUse`,
`PostToolUse`, `SessionStart`, `Stop`, …). Every block, every audit
append, every ceremony check happens because the harness fires those
events. The hooks themselves are harness-agnostic (they read a normalized
event via an adapter layer, ADR-008); the two production adapters are
`claude` and `codex` (`KNOWN_ADAPTERS` in `_lib/contract.py`). Outside
**any** adaptered harness, no event fires — so no hook runs, and the
governance layer degrades from *enforced* to *documented*.

Two things bound the Codex column below, stated once here and carried into
every ENFORCED cell:

- **Nothing is enforced under Codex until `/hooks` trust is granted.** An
  installed-but-untrusted hook is a silent no-op, indistinguishable from
  healthy at runtime. The installer's post-install arming check
  (`ARMED / NOT-ARMED-(untrusted) / BROKEN`) is the only local detector.
- **Codex fail-open is the default failure mode.** A hook that times out,
  crashes, or emits malformed/foreign JSON waves the tool call through
  with no model-visible signal (`failure-semantics-matrix.md`). Our
  fail-closed-on-input invariant is implemented inside the hooks; the
  RED-on-absence breadcrumbs (Wave 6) + CODEOWNERS/CI are the backstops.

---

## Rail by rail

Three columns: Claude Code (default harness), Codex CLI (installed +
trusted, per-rail), and no harness (plain editor / bare terminal / CI bot
/ un-adaptered tool). Codex cells use the house vocabulary — ENFORCED /
ADVISORY / ABSENT — with the residual in the claim.

| Rail | In Claude Code | Under Codex CLI (installed + trusted) | No harness |
|------|----------------|----------------------------------------|------------|
| Canonical-edit guard (`check_canonical_edit.py`) | PreToolUse blocks `Edit`/`Write`/`MultiEdit` and write-shaped `mcp__*` against canonical paths unless an Owner-signed GPG sentinel exists | **ENFORCED** (edit-time) — PreToolUse `apply_patch\|Edit\|Write\|mcp__.*` → deny; every path in a multi-file patch gated. Residual: complex-shell smuggle + `apply_patch` Update-hunk content (path gate still fires); backstop `^Bash$` + CODEOWNERS | Nothing intercepts. Any editor writes `team.md`, hooks, or skills freely. Backstops are server-side: CODEOWNERS + branch protection |
| Arbitration-kernel hard-deny (`check_arbitration_kernel.py`) | The guard hooks and `_lib` primitives *themselves* cannot be edited even with a sentinel (only an explicit audited override) | **ENFORCED** (edit-time) — unconditional deny on kernel paths, any kernel path in a multi-file patch | Those files are editable like any others |
| Bash safety (`check_bash_safety.py`) | Destructive commands (`rm -rf` flag combos, `git reset --hard`, force-push) blocked before execution | **ENFORCED** — `^Bash$` runs our parser + `.codex/rules/ceo.rules` coarse `prefix_rule` backstop. Residual: Codex "doesn't intercept all shell calls yet, only the simple ones"; the hook applies our own parser on every event that fires | No pre-execution gate; your shell runs whatever is typed |
| Spawn governance (`check_agent_spawn.py`) | Agent spawns without the required profile/skill/file-assignment sections are blocked | **ADVISORY** — SubagentStart `continue:false` is parsed but does NOT stop the subagent (verified 0.139). `additionalContext` injects the requirement; Bash-routed spawns re-gain the ENFORCED gate; Wave 6 chain scan is the backstop. Never enforced | No `Agent` tool at all; the spawn protocol is prose in `.claude/team.md` |
| Plan lifecycle (`check_plan_edit.py`) | Illegal plan-status transitions blocked at edit time | **ENFORCED** (edit-time) — PreToolUse on `.claude/plans/**`; Add-op content reconstructed per-op. Residual: Update-hunk content gap (path gate fires); CI schema checks at push | Convention only at edit time; some drift caught later by CI schema checks, at push |
| Skill-patch + VETO-floor sentinels (`check_skill_patch_sentinel.py`, `check_tier_policy.py`) | `SKILL.md` edits require a signed SP-NNN proposal; reviewer-agent `model:` changes require a dedicated sentinel | **ENFORCED** (edit-time) via the same canonical/PreToolUse rail | Gone at edit time; CI + CODEOWNERS partially compensate at push |
| Pair-rail review (`check_pair_rail.py` / inverted `check_codex_stop_review.py`) | Edits to L3+ canonical paths trigger a second-model (Codex) review; write-shaped reviewer output is blocked | **PARTIAL, INVERTED** — Codex operates, reviewer = `claude -p`; Stop hook `decision:block` auto-continues until the review ran; git pre-push backstop. Residual: killing the session abandons the Stop gate (push gate holds); reviewer pin PROVISIONAL (OQ3) | Manual only. The reviewer CLI still runs from any shell, but nothing forces the review or screens what comes back |
| HMAC audit chain (`audit_log.py` + lifecycle hooks) | Every agent spawn, edit, and ceremony appended to the HMAC-chained log | **ENFORCED, completeness-bounded** — PostToolUse `*` per-tool append (`codex_tool_recorded`) + SessionStart boot + `codex_turn_ended` backstop; `verify_chain()` unchanged and green. Residual: per-edit completeness best-effort under partial shell interception — absence of an entry is not evidence of absence of activity | The chain **freezes** — work done outside appends nothing. `verify_chain()` still detects tampering of the *existing* log, but cannot record what never reached it |
| Config / kill-switch protection (`SessionStart` boot re-hash, `.codex/**` guard) | Boot health checks + out-of-band `settings.json` tamper observation (`ConfigChange`) | **ENFORCED at edit-time; ADVISORY between sessions** — `.codex` kill-switch surface is canonical-guarded + boot-re-hash tripwired (Wave 3b). Residual: Codex has **no ConfigChange event** → continuous observation degrades to boot-time-only; the tripwire baseline is agent-writable (edit-time guard is the real protection) | Never fire. Config tamper is invisible until push-time CI |
| Vetoes, debates, three-strike rule ([../PROTOCOL.md](../PROTOCOL.md), `/debate`) | Slash-command ceremony with hook-checked artifacts; vetoes are hard blocks | Prose conventions — the ceremony surface is Claude-Code-slash-command shaped; the on-disk artifacts stay readable/writable, but the debate flow is not Codex-hosted | Prose conventions. Debate/veto artifacts on disk are readable — and writable by hand — but nothing gates execution on them |
| Injection & secret scanners (`check_output_secrets.py`, `check_webfetch_injection.py`, …) | Advisory scans over tool traffic (web content, MCP responses, file reads, tool output) | Advisory scans fire on the PostToolUse `*` matcher for tools Codex intercepts; the partial-interception residual bounds coverage | There is no tool traffic to scan |
| Permission deny rules (`permissions.deny` in `.claude/settings.json`) | The harness refuses tool calls against `PROTOCOL.md`, `SPEC/**`, `settings.json`, `git push --force` | Codex has no `permissions.deny` equivalent; the same paths are covered by the PreToolUse canonical/kernel deny rail instead | Inert JSON |

The pattern: **every row's left column is harness-hosted.** Under Codex,
the enforcement rows are hosted too (once trusted); the process rows
(debates/vetoes) stay Claude-Code-shaped. With no harness at all, a human
or agent editing this repo is trusted, not gated.

---

## What still works (in every case)

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

Under **Claude Code**, the framework is a governance layer with the rails
in the left column above. Under **Codex CLI** (installed + trusted), it is
the per-rail matrix in the middle column — most prevention rails ENFORCED
at edit time, the spawn rail honestly ADVISORY, the pair-rail inverted and
PARTIAL, and audit ENFORCED-but-completeness-bounded — with the two
substrate caveats (trust-before-anything, fail-open-on-hook-death) stated
in every ENFORCED claim. With **no harness at all**, this framework is
**documentation plus offline verification plus server-side CI** — not a
governance layer:

- Prevention (canonical-edit guard, bash safety, kernel hard-deny) →
  **gone** at edit time with no harness; **ENFORCED** under Codex (once
  trusted).
- Evidence (HMAC audit chain) → **frozen** with no harness;
  **completeness-bounded** under Codex; existing history stays
  tamper-evident in both cases.
- Process (debates, vetoes, three-strike) → **prose** that a disciplined
  operator can follow and an undisciplined one can skip silently; the
  ceremony surface is Claude-Code-shaped even under Codex.
- Backstops (CI, CODEOWNERS, branch protection) → **always on**, but they
  fire at push time and see diffs, not intent.

If your team works across harnesses, treat a non-adaptered session the way
you would treat any un-hooked shell session: assume no local gate fired,
rely on the push-time gates, and run `audit-verify-chain.py` plus
`validate-governance.sh` before trusting state. For a Codex session,
additionally confirm the arming check reports **ARMED** — installed is not
armed, and armed is not trusted-forever (trust re-keys when a hook
registration string changes). CI certifies fixture-replay against a
recorded wire; only local live-fire certifies the real binary, per pinned
version. See also [HONEST-LIMITATIONS.md](HONEST-LIMITATIONS.md).
