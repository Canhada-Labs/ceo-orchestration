---
id: PLAN-155
title: Codex Harness Compatibility
status: done
reviewed_at: 2026-07-07
executing_at: 2026-07-09
completed_at: 2026-07-10
created: 2026-07-07
owner: CEO
depends_on: [PLAN-153]
budget_tokens: 0.95-1.4M
budget_sessions: 4
context_risk: medium
external_wait: none
tags: [harness-compat, adapters, codex, installer, audit, pair-rail]
related_commits:
  - daca2ec   # feat(PLAN-155): land Wave-1 codex host adapter — resolve() seam (b), 4 enforced hooks, ADR
  - fdb1822   # feat(PLAN-155): land Wave-2 codex templates — hooks.json + config example + AGENTS.md + ru
  - c529caa   # feat(PLAN-155): land Wave-3b kill-switch teeth — guard-list extension incl. AGENTS.md [SEN
  - 0d13e11   # feat(PLAN-155): land Wave-4 codex audit chain — actions 314→316 + tamper mirror [SENT-CX-B
  - 8c032df   # feat(PLAN-155): land Wave-5 codex installer — _codex_harness + matrix tests [SENT-CX-C]
  - 9a74d51   # feat(PLAN-155): land Wave-6 inverted pair-rail teeth + validate.yml riders [SENT-CX-D]
  - c70adf1   # docs(PLAN-155): land Wave-7 docs — INSTALL/README/adapters/capability matrix
---

# PLAN-155 — Codex Harness Compatibility

## Context

Owner directive (S261/S262): make the framework **functional on OpenAI
Codex** — not a stub row, an installable, enforcing rail. The demand signal
that `docs/adapters.md:58-61` said was missing ("Add when a real Codex CLI
user appears") now exists by directive.

**Ground truth (S261 research, verified against local codex-cli 0.139.0 +
primary docs at `developers.openai.com/codex/{hooks,config-reference,rules,guides/agents-md}`):**

- Codex 0.139 ships a lifecycle-hooks system nearly identical to Claude
  Code's (feature `hooks=stable+true`, verified locally): `PreToolUse` /
  `PostToolUse` / `SessionStart` / `UserPromptSubmit` / `Stop` /
  `SubagentStart` / `SubagentStop` / `PermissionRequest`, speaking
  `hookEventName` / `permissionDecision` / `permissionDecisionReason` /
  `hookSpecificOutput` / `additionalContext` — the same vocabulary our
  hooks already emit through the adapter layer.
- `PreToolUse` intercepts Bash, file edits via `apply_patch` (matcher
  aliases `apply_patch|Edit|Write`), and MCP tools. Official caveat, quoted
  because it bounds every enforcement claim below: it "doesn't intercept
  all shell calls yet, only the simple ones".
- Codex skills use the **same `SKILL.md` + frontmatter** format
  (name/description/metadata) — our 151 skills port near-verbatim to
  `.codex/skills/` (see the optional Wave 8).
- Non-managed hooks require user `/hooks` trust, **keyed to the hook file's
  hash** (any edit ⇒ re-trust). `requirements.toml` MANAGED hooks are
  trusted-by-policy and non-disableable (enterprise posture).
- Operator context file: `AGENTS.md`, capped by `project_doc_max_bytes`
  (32 KiB), discovery git-root→cwd nearest-wins. Our current root
  `AGENTS.md` is the *reviewer contract* only (S261) — the operator-facing
  file for installed targets is a new template, it does not replace ours.

**Ground truth (this repo, verified on disk at authoring time, S262):**

- The adapter layer (ADR-008) is built for exactly this.
  `_lib/contract.py:216` already registers
  `KNOWN_ADAPTERS = ["claude", "codex"]`, and
  `.claude/hooks/_lib/adapters/codex.py` already exists — **but as the
  pair-rail reviewer-egress helper** (PLAN-081/PLAN-142 lineage): its
  `read_event` parses the *Claude Code* wire (Codex-as-MCP-tool responses)
  and its `write_decision` emits the *Claude* decision shape
  (`codex.py:247-263`, "Claude Code is the host IDE"). The Codex-as-HOST
  direction — parse Codex hook envelopes, emit
  `hookSpecificOutput.permissionDecision` — is the new work (Wave 1
  linchpin).
- `docs/adapters.md` is stale twice over: it still documents
  gemini/openai/local adapters that are no longer in the registry AND marks
  codex "NOT IMPLEMENTED / low demand". Wave 7 fixes both honestly.
- Adapter test reality: the parity/drift suites on disk are
  `.claude/hooks/tests/test_adapter_golden.py`,
  `.claude/hooks/tests/test_adapter_drift_detector.py`, and
  `.claude/hooks/tests/adapters/live/test_adapters.py` (the research
  pointer `test_adapters_parity.py` does not exist under that name — cite
  the real files).
- `scripts/install.sh` has no `--harness` flag today (flag surface at
  `install.sh:378-460`).
- `docs/degradation-outside-claude-code.md` (S261) is the honesty baseline
  this plan upgrades: from "no adapter is production → no enforcement
  claim" to a real per-rail matrix.
- Substrate versions: local codex-cli **0.139.0** pinned by PLAN-142;
  upstream already ships **0.142.5** — version-drift risk named in §Risks;
  `claude` CLI 2.1.202 present for the inverted rail.

## Goal

An operator can run `install.sh --harness codex` on a target repo and get
the governance rails **functional under OpenAI Codex** — canonical-edit,
bash-safety, plan-edit, and kernel-deny ENFORCED at edit time via Codex
PreToolUse; the HMAC audit chain appending and `verify_chain()`-green over
Codex sessions; the pair-rail inverted (Codex operates, Claude reviews) —
with every residual named in writing and the two honest ADVISORY rails
(spawn hard-block, continuous config tripwire) never oversold.

## Approach / Thesis

- **Adapter first (linchpin).** Everything else is templates and wiring;
  the one piece of kernel code is teaching
  `_lib/adapters/codex.py` to be a *host* adapter: `read_event` for the
  Codex hook envelope, `emit_decision` mapping our
  `{decision: block, reason}` to
  `{hookSpecificOutput: {hookEventName, permissionDecision: "deny",
  permissionDecisionReason}}`. Wire shape is ~identical to `claude.py`;
  same fail-open-on-infrastructure invariant (SPEC/v1 §4).
- **Same hooks, different registration.** No hook forks. The Codex-side
  registration (`.codex/hooks.json` or `[hooks]` in `.codex/config.toml`)
  calls the SAME Python hooks with `CEO_HOOK_ADAPTER=codex` + explicit
  timeout. One enforcement kernel, two harnesses.
- **Capability-matrix vocabulary is binding** (house ethos): every rail is
  labeled ENFORCED / ADVISORY / ABSENT, and every ENFORCED claim names its
  residual (shell-escape class, partial interception) and its backstop
  (CODEOWNERS, pre-push, CI). No speed claim anywhere.
- **Behavioral over static** (PLAN-153 debate consensus #2): what certifies
  a rail alive under Codex is the positive-control replay (planted
  violation → assert deny), not the existence of a config file.
- **Ceremony-derived L-levels.** Waves 1, 3b, 4, 6 touch `.claude/hooks/**`
  (canonical-guarded, `check_canonical_edit.py`); Wave 5 touches
  `scripts/install.sh`; Wave 6 may touch `.claude/dispatcher/**` and
  `.github/workflows/**`; ADR-161 lands under guarded `.claude/adr/`. All
  L3 — sentinels allocated in Wave 0, never discovered at execution time.
  Waves 2/3 land as NEW files under unguarded `templates/` — L2 — but they
  only **emit** the `.codex` registration/rules templates; the TEETH that
  protect the kill-switch surface (extending the canonical guard list + the
  boot-time hash tripwire) are the separate **L3 Wave 3b (SENT-CX-E)**,
  because extending `_CANONICAL_GUARDS` in `check_canonical_edit.py` is a
  KERNEL-class guard-list extension (that file is in `_KERNEL_PATHS`;
  `check_canonical_edit.py:149-152` + `check_arbitration_kernel.py:302-304`
  require a plan-specific `CEO_KERNEL_OVERRIDE=<slug> + CEO_KERNEL_OVERRIDE_ACK=I-ACCEPT`
  in addition to the sentinel).
- **Sequencing vs PLAN-153 (staged-not-landed reality).** PLAN-153 Wave B
  (installer lifecycle) and Wave E (deny baseline write) both touch
  `scripts/install.sh` and are STAGED, not landed, as of S261. This plan's
  Wave 5 executes only AFTER PLAN-153's install.sh waves are merged on
  main — otherwise two signed sentinels race on the same guarded file and
  the second scope-assert (`touched − SIGNED SCOPE = ∅`, S258 rule) fails
  on rebase. Waves 0-4 have no file overlap with PLAN-153 and may proceed.
- **Stdlib-only, py≥3.9**, `from __future__ import annotations`, fail-open
  on infrastructure / fail-closed on input (PLAN-152 C4) — unchanged.

## Capability matrix — Codex target state (normative for all docs/claims)

Vocabulary per the house capability-matrix doctrine. "Residual" is part of
the claim, not a footnote.

| Rail | Codex primitive | Status | Residual + backstop |
|---|---|---|---|
| Canonical-edit guard (`check_canonical_edit.py`) | PreToolUse matcher `apply_patch\|Edit\|Write\|mcp__.*` → deny | **ENFORCED** (edit-time) | Residual: writes smuggled through complex shell commands — the same shell-escape class already documented for Claude Code. Backstops: the `^Bash$` rail below sees the full command string; CODEOWNERS + branch protection at push. |
| Bash safety (`check_bash_safety.py`) | PreToolUse `^Bash$` running our exact hook logic + `.codex/rules/ceo.rules` execpolicy `prefix_rule(decision=forbidden)` backstop | **ENFORCED** | Residual: official caveat — Codex "doesn't intercept all shell calls yet, only the simple ones"; Codex splits `bash -lc` only on plain words + `&&`/`\|\|`/`;`/`\|`, opaque single commands otherwise. Our hook receives the full string on every event that fires and applies our own parser (`_e3` whole-command gate stays fail-closed on input). |
| Plan lifecycle (`check_plan_edit.py`) | PreToolUse on `.claude/plans/**` writes | **ENFORCED** (edit-time) | Same shell-escape residual as canonical-edit; CI plan-schema checks at push. |
| Arbitration kernel (`check_arbitration_kernel.py`) | PreToolUse unconditional deny on kernel paths | **ENFORCED** (edit-time) | Same residual class; kernel paths also in CODEOWNERS. |
| Spawn governance (`check_agent_spawn.py`) | SubagentStart hook | **ADVISORY** — real gap: `continue:false` is parsed but does NOT stop the subagent (verified 0.139) | Mitigations: `additionalContext` injects the profile/skill/file-assignment requirement into the subagent; spawns routed via Bash (`claude -p` / `codex exec`) re-gain the ENFORCED gate through the `^Bash$` matcher; pre-push/CI check over the audit chain's spawn records (Wave 6). Never documented as enforced. |
| Pair-rail review | **INVERTED**: Codex operates, reviewer = `claude -p` (verified non-interactive); Stop hook `decision:block` auto-continues the session until the review ran; git pre-push backstop | **PARTIAL, pending Stop-block verification** (stop-time + push-time, not per-edit; nothing recorded yet shows Stop `decision:block` IS enforced on 0.139 — the row is confirmed only when the Wave 1 live Stop-block enforcement transcript exists, debate A5) | Residual: nothing forces per-edit review mid-turn; the Stop gate can be abandoned by killing the session (push gate still holds). |
| Audit HMAC chain (`audit_log.py` + emit hooks) | PostToolUse matcher `*` per-tool-call append + SessionStart boot + `notify` turn-ended backstop | **ENFORCED, completeness-bounded** | Residual: per-edit completeness is best-effort while shell interception is partial — absence of an entry is not evidence of absence of activity (same honest line as the degradation page). `verify_chain()` unchanged and green over what was written. |
| Config protection (`.claude/settings.json`, hook sources) | Edit-time PreToolUse block ENFORCED + `requirements.toml` MANAGED hooks (trusted-by-policy, non-disableable) | **ENFORCED at edit time; ADVISORY between sessions** | Codex has **no ConfigChange event** — the continuous tamper tripwire degrades to boot-time-only re-check (SessionStart). Backstop: boot-time hash re-check + CI. |
| Kill-switch protection (`.codex/hooks.json`, `.codex/config.toml`, `.codex/rules/ceo.rules`, `requirements.toml`, operator `AGENTS.md`) | The rail's OWN registration surface entering the PreToolUse deny/canonical matcher + boot-time hash tripwire (deregistering the hooks must not silently kill the tripwire that detects it) | **ABSENT until Wave 3b (SENT-CX-E) lands** — Waves 2/3 EMIT these template files (L2) but ship **no teeth**; protection exists only after the L3 guard-list + tripwire extension | Residual: until Wave 3b lands, an agent under Codex can rewrite the kill-switch files and disarm every rail above — the circular-disarm gap (debate A8). Backstop until then: CODEOWNERS + branch protection at push; after Wave 3b: canonical-edit deny (KERNEL-override-gated guard extension) + SessionStart boot re-hash. |
| Skills | `.codex/skills/` — same `SKILL.md` + frontmatter format | Available (optional Wave 8) | Not a rail; contamination/counts implications scoped in Wave 8. |

**ABSENT on Codex today** (goes to §Deferred with a WATCH pointer): total
shell-call interception; a ConfigChange lifecycle event; a SubagentStart
that hard-blocks.

## Waves

Execution order: `0 → 1 → 2 → 3 → 3b → 4 → 5 → 6 → 7 (→ 8 optional)`. Waves
2+3 may run in parallel with Wave 1 review; Wave 3b (kill-switch guard
extension) gates on Waves 2/3 defining the `.codex` kill-switch paths and
MUST land before Wave 5 ships those paths via the installer; Wave 5 gates
on PLAN-153's install.sh waves landing (see Approach).

### Wave 0 — Ceremony allocation + Owner ratification (L3 allocation, session 1)

Check: sentinels drafted with exact `Scope:` paths + verified against both
signer rails; ADR-161 slug reserved; OQ answers logged verbatim in this
file.

- [ ] Ratify §Open questions OQ2 (skills-port posture) and OQ3
      (inverted-rail reviewer pin). **OQ1 is NOT ratified in Wave 0**
      (debate A6): the `/hooks` trust-hash keying semantics are pinned
      empirically in Wave 1/2 first (edit the shim → re-prompt? edit a
      hook `.py` → re-prompt?), and OQ1 is ratified only AFTER that fact
      is in front of the Owner — the friction estimate and the
      consent-security meaning both invert on the answer.
- [ ] **Dispatch-surface inventory + seam ratification (debate A1,
      CRITICAL):** `CEO_HOOK_ADAPTER` has ZERO consumers in the
      enforcement hooks today — all four ENFORCED hooks (and ~20 more)
      hard-import the claude adapter (`check_canonical_edit.py:1081`,
      `check_bash_safety.py:201`, `check_plan_edit.py:92`,
      `check_arbitration_kernel.py:448`); no hook entrypoint calls
      `contract.load_adapter()`/`resolve_adapter()`. Enumerate every
      `from _lib.adapters import claude` site in `.claude/hooks/`, then
      the Owner ratifies ONE seam design at signing: (a) migrate each
      entrypoint to `contract.load_adapter()`, or (b) a single shared
      ingress/egress seam the hooks already route through. The sentinel
      scope (SENT-CX-A, or a new SENT-CX-A2) enumerates the touched hook
      files explicitly — no execution-time widening.
- [ ] Draft + sign sentinels (dual rail per ADR-121, real anchor-sha, exact
      scope per the canonical guard's exact-path rule):
      **SENT-CX-A** (Wave 1): `.claude/hooks/_lib/adapters/codex.py`,
      `.claude/hooks/_lib/adapters/__init__.py`,
      `.claude/hooks/_lib/contract.py` (only if registry constants move
      or the debate-A2 coherence gate lands contract-side — decided at
      signing), PLUS the hook entrypoint files (or the single shared
      seam module) ratified under the debate-A1 dispatch-surface
      inventory — enumerated explicitly at signing, or split into a new
      **SENT-CX-A2**. **KERNEL-class (pair-rail S265 F1):** all three
      named files are in `_KERNEL_PATHS`
      (`check_arbitration_kernel.py:85,165,168` — the PLAN-153 landing's
      ADR-116-AMEND-1 kernel-extension-v2 added the adapter modules), so
      the Wave 1 ceremony additionally requires
      `CEO_KERNEL_OVERRIDE=PLAN-155-CODEX-HOST-ADAPTER` +
      `CEO_KERNEL_OVERRIDE_ACK=I-ACCEPT` (audited per ADR-031
      §kernel-override) on top of the sentinel; the SENT-E/S261
      Owner-shell apply route satisfies the same requirement with the
      signed sentinel as the authorization record;
      **SENT-CX-B** (Wave 4): registering a NEW audit action is a
      four-file coupling (the S261 PLAN-153 Wave E 302→303 precedent —
      exactly this shape; that precedent has since LANDED, so the current
      baseline is 303), so the scope enumerates ALL of:
      `.claude/hooks/audit_log.py` (guarded — if the per-tool-call append
      path is extended past the `agent_spawn`-only `build_entry`,
      `audit_log.py:566-567,:642`), `.claude/hooks/_lib/audit_emit.py`
      (guarded — register the new action in `_KNOWN_ACTIONS`
      (`audit_emit.py:153`) with its closed-enum field allowlist, since
      `_write_event` rejects any unregistered action at
      `audit_emit.py:2475-2477`), `SPEC/v1/audit-log.schema.md` (guarded
      under `SPEC/v1/*.md` — the action row gets an **Amends** version-bump
      clause), and the unguarded same-commit companion
      `.claude/hooks/tests/test_audit_emit_api_contract.py` (rebaseline the
      `_KNOWN_ACTIONS` count + SHA256 pin — CURRENT pin is 303 at
      `test_audit_emit_api_contract.py:656-658`; Wave 4's actions
      rebaseline 303→304/305, pair-rail S265 F4). The unguarded
      test rides along in the emitter's commit; it is named here only so
      the coupling is not discovered at execution time (`hooks/tests/` is
      NOT canonical-guarded, so it is not sentinel-blocked).
      **KERNEL-class (pair-rail S265 F3):** `audit_log.py` and
      `_lib/audit_emit.py` are in `_KERNEL_PATHS`
      (`check_arbitration_kernel.py:200,90`), so the Wave 4 ceremony
      additionally requires
      `CEO_KERNEL_OVERRIDE=PLAN-155-CODEX-AUDIT-ACTIONS` +
      `CEO_KERNEL_OVERRIDE_ACK=I-ACCEPT` on top of the sentinel (same
      Owner-shell-apply equivalence as SENT-CX-A);
      **SENT-CX-C** (Wave 5): `scripts/install.sh` (+ `scripts/upgrade.sh`
      if touched) — sign only AFTER PLAN-153 SENT-B lands, anchor-sha on
      the post-PLAN-153 main;
      **SENT-CX-D** (Wave 6): `.claude/hooks/check_pair_rail.py` (if
      touched), `.claude/dispatcher/**` (if routing matrix touched),
      `.github/workflows/validate.yml` (CI teeth for the advisory rails).
      **KERNEL-class (pair-rail S265 F5):** all three named surfaces are
      in `_KERNEL_PATHS` (`check_arbitration_kernel.py:180,133,135`), so
      if Wave 6 touches any of them the ceremony additionally requires
      `CEO_KERNEL_OVERRIDE=PLAN-155-CODEX-PAIRRAIL-TEETH` +
      `CEO_KERNEL_OVERRIDE_ACK=I-ACCEPT` on top of the sentinel (same
      Owner-shell-apply equivalence as SENT-CX-A);
      **SENT-CX-E** (Wave 3b — kill-switch guard extension, debate A8):
      `.claude/hooks/check_canonical_edit.py` (extend `_CANONICAL_GUARDS`
      to cover `.codex/hooks.json`, `.codex/config.toml`,
      `.codex/rules/ceo.rules`, `requirements.toml`, operator `AGENTS.md`
      — this file is in `_KERNEL_PATHS`, so the guard-list extension is
      KERNEL-class and additionally requires
      `CEO_KERNEL_OVERRIDE=PLAN-155-CODEX-KILLSWITCH-GUARD-EXTENSION` +
      `CEO_KERNEL_OVERRIDE_ACK=I-ACCEPT`, per `check_canonical_edit.py:149-152`
      and `check_arbitration_kernel.py:302-304`),
      `.claude/hooks/SessionStart.py` (extend the boot-time hash re-check
      beyond `_GATE_1_FILES` (`SessionStart.py:48-54,:79`) to cover the
      kill-switch surface), `.claude/hooks/_lib/effective_config.py`
      (extend the disk census beyond the registered `.claude/hooks/*.py`
      basenames, `effective_config.py:192-199`), plus the unguarded
      same-commit test companions that pin these contents
      (`.claude/hooks/tests/{test_check_canonical_edit.py,test_session_start.py,test_effective_config.py}`).
      Sentinel-scope consequences of debate A1 (dispatch seam), A2
      (coherence-gate home: contract.py vs adapter-side) and A8
      (kill-switch guarded surface) are reflected in this allocation
      BEFORE signing — never discovered at execution time. New tests land
      in `hooks/tests/` (not guarded); new templates land under
      `templates/` (not guarded).
- [ ] Reserve **ADR-161** — "Codex harness capability matrix + host-adapter
      doctrine" — carrying the §Capability matrix as normative text (the
      ENFORCED/ADVISORY/ABSENT labels + named residuals). Per the debate
      bindings, ADR-161 additionally carries: the empirical
      failure-semantics matrix + the SubagentStart non-enforcement
      transcript citation (A5); the normative "what /hooks trust does and
      does not attest" paragraph (A6); the T1/T2/T3 hermetic-posture text
      incl. the sentence "CI certifies fixture-replay against a recorded
      wire; only local live-fire certifies the real binary, per pinned
      version" (A3); the named per-bump re-verification checklist with
      exact artifact list + time-box (A12); and the placement condition
      on the managed-hooks "non-disableable" claim (A8). `.claude/adr/` is
      guarded (S261 confirmation: NEW files too) — the ADR file rides the
      SENT-CX-A ceremony batch.
- [ ] Add a **substrate watch-item** for the Codex hook schema:
      `check-substrate-watch.py` today sweeps Claude Code + Agent-SDK drift
      only — the Codex hooks/config/rules doc set and codex-cli release
      feed are not covered. Register the watch entry (unguarded
      `.claude/scripts/` surface) in this wave so drift detection exists
      BEFORE we ship code depending on the schema. (Debate A12) The watch
      entry covers BOTH the codex-cli release feed AND the
      hooks/config/rules doc pages, and its alert text names the fixture
      re-record runbook.

### Wave 1 — Host-adapter linchpin (L3, SENT-CX-A)

Check: `pytest .claude/hooks/tests/test_adapter_golden.py
.claude/hooks/tests/test_adapter_drift_detector.py
.claude/hooks/tests/adapters/ -q` green under BOTH
`CEO_HOOK_ADAPTER=claude` and `=codex` AND non-vacuously (the debate-A4
minimum-fixture-count assertions in force — a `.gitkeep`-only codex
fixture dir must FAIL); subprocess positive/negative/malformed controls
(below) green; full hook suite green; S258 `touched − SIGNED SCOPE = ∅`.

- [ ] **Characterization pre-gate (debate A14) — lands BEFORE the
      host-mode edit:** golden in/out characterization tests lock the
      pair-rail reviewer-egress surface (`parse_verdict*`,
      `make_invoke_command*`, `parse_usage_from_codex_stdout`); they must
      pass unchanged on BOTH sides of the Wave 1 commit
      (`check_pair_rail.py:829,:874` consumes this surface).
- [ ] Extend `_lib/adapters/codex.py` to host mode: `read_event` parses the
      Codex hook envelope (`hookEventName`, tool fields, `apply_patch`
      alias normalization → our `Edit`/`Write` semantics);
      `write_decision`/`emit_decision` emit
      `{hookSpecificOutput: {hookEventName, permissionDecision:
      "deny"|"allow", permissionDecisionReason}}` (+ `additionalContext`
      passthrough via `Decision.extra`). The existing reviewer-egress
      helpers (`parse_verdict*`, `make_invoke_command*`,
      `parse_usage_from_codex_stdout`) are UNTOUCHED — one module, two
      documented roles; the module docstring gains a role map. Fail-open on
      parse error preserved (`NormalizedEvent(parse_error=...)`, never
      raises).
- [ ] Capture real 0.139 hook payloads to
      `hooks/tests/fixtures/adapters/codex/in/*.json` (≥2 per event we
      consume: PreToolUse bash, PreToolUse apply_patch, PostToolUse,
      SessionStart, Stop, SubagentStart) + matching normalized
      expectations. Fixtures are recorded from the live local CLI, not
      hand-written from docs. (Debate A12) Every recorded fixture carries
      `_meta.codex_cli_version`; a unit test asserts that version ∈ the
      `codex-cli-pin.txt` range — a pin bump goes RED until fixtures are
      re-recorded or explicitly waived. Fixtures follow the PIN, never
      upstream: to record on 0.142.x, bump the pin FIRST via the ADR-111
      ceremony, then re-record.
- [ ] Golden/byte-fidelity coverage: the host-mode `write_decision` shape
      change is DELIBERATE — update `test_adapter_golden.py` goldens for
      the codex adapter in the same commit and note it in ADR-161 (the
      old Claude-shaped output was the "symbolic parity" era; no
      production caller consumed it host-side).
- [ ] **Dispatch seam implementation (debate A1):** implement the Wave-0
      ratified seam so `CEO_HOOK_ADAPTER=codex` ACTUALLY dispatches —
      today zero hook entrypoints call
      `contract.load_adapter()`/`resolve_adapter()` and all four ENFORCED
      hooks hard-import the claude adapter; without the seam, the Wave 2
      env wiring changes nothing and every ENFORCED row silently becomes
      ABSENT (the S254 dead-gate class). The subprocess controls below
      are what prove the chosen seam dispatches.
- [ ] **Host/adapter coherence gate (debate A2):** an
      explicitly-set-but-unresolvable `CEO_HOOK_ADAPTER`, or a
      recognizably cross-harness envelope under the resolved adapter, is
      an INPUT/mis-configuration failure per the PLAN-152 C4 taxonomy →
      fail-CLOSED (deny) + audit breadcrumb + SessionStart boot check
      RED — never a silent fallback to the claude adapter. Whether the
      gate lives in `contract.py` or adapter-side is decided at SENT-CX-A
      signing, not mid-wave.
- [ ] **Kill the vacuous green (debate A4, same commit as the host-mode
      code):** parameterize the golden round-trip over ALL
      `KNOWN_ADAPTERS`; minimum-fixture-count assertion per adapter (a
      `.gitkeep`-only dir must FAIL — today's suite passes with empty
      codex fixture dirs); codex `out/` goldens for allow,
      deny-with-reason, and `additionalContext` passthrough; extend the
      drift detector to scan codex host-mode `NormalizedEvent` call-sites.
- [ ] **Empirical failure-semantics matrix (debate A5), recorded BEFORE
      ADR-161 treats any matrix row as normative:** what codex-cli 0.139
      does on hook timeout / non-zero exit / malformed-or-foreign JSON /
      `{}` output — PLUS a live Stop-block enforcement transcript. The
      pair-rail matrix row stays "PARTIAL, pending Stop-block
      verification" until that transcript exists. Archive the
      SubagentStart non-enforcement transcript under
      `PLAN-155/artifacts/`, cite it from ADR-161, and add it to the
      substrate-watch per-bump re-test list.
- [ ] **Trust-hash keying empirically pinned (debate A6, Wave 1/2):**
      does editing the `_python-hook.sh` shim re-prompt trust? does
      editing a hook `.py` re-prompt? ADR-161 gets the normative "what
      /hooks trust does and does not attest" paragraph; OQ1 is ratified
      only AFTER this fact is in front of the Owner (see §Open
      questions).
- [ ] **Positive-control replay** (the certifying artifact, PLAN-153 Wave E
      doctrine; hardened per debate A3): the 3 planted violation classes
      — (a) unsentineled write to a canonical path, (b) destructive bash
      (`rm -rf` class), (c) illegal plan-status transition — recorded as
      Codex-wire PreToolUse envelopes and replayed as **SUBPROCESSES on
      the byte-identical command line shipped in
      `templates/codex/hooks.json`** (shim + argv + env,
      `CEO_HOOK_ADAPTER=codex`), stdin = recorded envelope; all three
      MUST come back `hookSpecificOutput.permissionDecision: deny` AND
      assert the deny-reason class. In-process import-and-call replay is
      insufficient — it would have stayed green through the S254 dead
      gate. Per violation class add one **negative control** (benign
      envelope → allow) and one **malformed-envelope control** asserting
      the PLAN-152 C4 split (infrastructure fails open; unparseable input
      at a security matcher fails closed). Wired into an explicit
      `validate.yml` pytest path same-commit (PLAN-153 consensus #5;
      validate.yml touch rides SENT-CX-D scope if needed, or the path is
      added in Wave 6's CI commit — decide at signing, do not widen
      SENT-CX-A silently).
- [ ] **Hermetic test posture normative in ADR-161 (debate A3):** three
      tiers, honestly labeled — T1 hermetic CI (recorded-wire replay:
      golden suite + the subprocess controls, no codex binary in CI); T2
      local live smoke per pinned version (gated on
      `shutil.which("codex")` + pin-range, `pytest.mark`-skipped in CI
      with a reason string naming the local runbook — visible, never
      silent); T3 release gate (the step-15 verdict envelope records the
      fixture-set version certified against). Normative sentence: "CI
      certifies fixture-replay against a recorded wire; only local
      live-fire certifies the real binary, per pinned version."

### Wave 2 — Registration template + operator AGENTS.md (L2, templates/)

Check: template JSON parses; a scratch `.codex/hooks.json` drives a live
0.139 session in which a planted canonical-edit is denied end-to-end
(manual live-fire, transcript kept under `PLAN-155/artifacts/`); operator
AGENTS.md ≤ 32768 bytes asserted by a unit test.

- [ ] `templates/codex/hooks.json` (+ documented `[hooks]`-in-`config.toml`
      variant): registers PreToolUse (`apply_patch|Edit|Write`, `^Bash$`,
      `mcp__.*`), PostToolUse `*`, SessionStart, UserPromptSubmit, Stop,
      SubagentStart, `notify` turn-ended — each command invoking the SAME
      `_python-hook.sh`-shimmed hooks with `CEO_HOOK_ADAPTER=codex` and an
      explicit per-hook timeout. Path resolution follows the harness's
      REAL runtime resolution (the PLAN-153 Wave E lesson: model
      dirname/cwd logic, not `REPO_ROOT`).
- [ ] `templates/codex/AGENTS.md` — operator contract for installed
      targets, ≤32 KiB (`project_doc_max_bytes`), placement doctrine
      documented (discovery git-root→cwd nearest-wins; in THIS repo the
      root `AGENTS.md` stays the reviewer contract — the template is for
      target repos and for a `.codex/`-scoped operator file here).
- [ ] SubagentStart `additionalContext` injection: the spawn-protocol
      requirement (`## AGENT PROFILE` / `## SKILL CONTENT` /
      `## FILE ASSIGNMENT`) injected as context — labeled ADVISORY in the
      template comments, per the matrix.
- [ ] **Kill-switch surface — EMISSION ONLY here; teeth in Wave 3b
      (debate A8):** this wave writes the rail's own registration surface
      as templates — `.codex/hooks.json`, `[hooks]` in
      `.codex/config.toml`, `.codex/rules/ceo.rules`, `requirements.toml`,
      and the operator `AGENTS.md`. **No protection ships in this L2 wave.**
      Making those files enter the PreToolUse deny/canonical matcher AND
      the boot-time hash tripwire (so deregistering the hooks cannot
      silently kill the tripwire that detects it — the circular-disarm
      gap) requires extending `_CANONICAL_GUARDS` and the SessionStart
      re-hash, which are canonical-guarded / KERNEL-class edits — that is
      the **L3 Wave 3b (SENT-CX-E)**, and the §capability-matrix
      config-protection row records this surface as ABSENT until Wave 3b
      lands. ADR-161 conditions the "managed = non-disableable" claim on
      `requirements.toml` placement (admin/org scope, not agent-writable).

### Wave 3 — Execpolicy rules backstop (L2, templates/)

Check: `codex execpolicy check` (0.139 syntax) accepts the shipped rules
file; a table in the file header maps each rule to the
`check_bash_safety.py` class it backstops; unit test asserts the rules
file parses and covers the destructive-command list used by the
positive-control corpus.

- [ ] `templates/codex/rules/ceo.rules`: `prefix_rule(decision=forbidden)`
      denylist for the destructive-command classes (`rm -rf` variants,
      `git reset --hard`, force-push, pipe-to-shell installers) — framed
      honestly as a COARSE prefix backstop under the hook rail, never as
      coverage (prefix rules see plain-word splits only; the hook owns the
      parser).
- [ ] `ceo.rules` is part of the debate-A8 kill-switch surface (see Wave
      2): this wave only EMITS the template. The PreToolUse deny/canonical
      matcher and boot-time hash tripwire that cover it are the L3 Wave 3b
      (SENT-CX-E) guard-list + tripwire extension — ABSENT until then.

### Wave 3b — Kill-switch guard extension (L3, SENT-CX-E; after Waves 2/3, before Wave 5)

This is the TEETH that Waves 2/3 deliberately deferred (debate A8). Waves
2/3 emit the `.codex` registration/rules/operator-doc templates as
unguarded L2 files; without this wave those files are an unguarded
underbelly — an agent under Codex could rewrite `.codex/hooks.json` (or
`requirements.toml`, or the operator `AGENTS.md`) and disarm every ENFORCED
rail while the tripwire that should detect it stays silent (circular
disarm). Extending the guard list AND the boot re-hash closes that gap.
Sequencing: runs after Waves 2/3 fix the kill-switch path set, and MUST
land before Wave 5 ships those paths via the installer, so the hooks the
installer copies already carry the protection.

Check: a planted edit to each kill-switch path (`.codex/hooks.json`,
`.codex/config.toml`, `.codex/rules/ceo.rules`, `requirements.toml`,
operator `AGENTS.md`) without a sentinel is DENIED end-to-end by
`check_canonical_edit.py` (behavioral positive-control, not a static list
diff); a mutated kill-switch file makes the SessionStart boot re-hash go
RED; full hook suite green under BOTH `CEO_HOOK_ADAPTER=claude` and
`=codex`; the signing env carried
`CEO_KERNEL_OVERRIDE=PLAN-155-CODEX-KILLSWITCH-GUARD-EXTENSION` +
`CEO_KERNEL_OVERRIDE_ACK=I-ACCEPT`; S258 `touched − SIGNED SCOPE = ∅`.

- [ ] **Guard-list extension (KERNEL-class):** add the kill-switch paths to
      `_CANONICAL_GUARDS` in `check_canonical_edit.py`
      (`check_canonical_edit.py:137-142` region). Because that file is in
      `_KERNEL_PATHS` (`check_arbitration_kernel.py:79`), the edit needs
      the plan-specific `CEO_KERNEL_OVERRIDE=PLAN-155-CODEX-KILLSWITCH-GUARD-EXTENSION`
      + `CEO_KERNEL_OVERRIDE_ACK=I-ACCEPT` in addition to the SENT-CX-E
      sentinel — the same double-gate PLAN-080-PHASE-0B and PLAN-081-PHASE-2
      used to extend the guard list (`check_canonical_edit.py:149-152`).
- [ ] **Boot-tripwire extension:** extend `SessionStart.py`'s boot-time
      hash re-check so the kill-switch surface is re-hashed on
      SessionStart (today `_GATE_1_FILES` / `_gate_1_hash` cover only the
      5 Gate-1 files, `SessionStart.py:48-54,:79`). **KERNEL-class
      (pair-rail S265 F2 — corrects this plan's earlier "sentinel-only"
      claim):** `SessionStart.py` IS in `_KERNEL_PATHS`
      (`check_arbitration_kernel.py:201`, added by the PLAN-153 landing's
      kernel-extension), so this edit is covered by the SAME
      `CEO_KERNEL_OVERRIDE=PLAN-155-CODEX-KILLSWITCH-GUARD-EXTENSION` +
      ACK that the guard-list extension already carries — SENT-CX-E's
      override covers BOTH kernel rows of this wave.
- [ ] **Census extension:** extend the `effective_config.py` disk census
      (today `registered-basename-missing-on-disk` over
      `.claude/hooks/*.py`, `effective_config.py:192-199`) so a
      deregistered/removed kill-switch registration is surfaced as a
      tamper class, not silently fail-open — canonical-guarded
      (sentinel-only).
- [ ] **Pin-tests updated same-commit (unguarded companions):**
      `.claude/hooks/tests/test_check_canonical_edit.py`,
      `.claude/hooks/tests/test_session_start.py`,
      `.claude/hooks/tests/test_effective_config.py` assert the extended
      guard list / tripwire set / census; they ride in the same commit
      (`hooks/tests/` is not canonical-guarded, so they are edited direct,
      not sentinel-blocked).
- [ ] **RED-on-absence (debate A2):** the boot re-hash is defined RED when
      a kill-switch file is missing or mutated — a silent fail-open here
      would recreate the S254 dead-gate class; vacuous green is the failure
      mode this wave exists to catch.
- [ ] **Matrix reconciliation:** flip the §capability-matrix
      config/kill-switch-protection row from "ABSENT until Wave 3b" to
      ENFORCED-at-edit-time + boot-time-ADVISORY, and record the KERNEL
      guard-extension override in ADR-161 alongside the PLAN-080/PLAN-081
      precedents.

### Wave 4 — Audit chain under Codex (L3, SENT-CX-B)

Check: recorded end-to-end Codex session (SessionStart → ≥5 tool calls →
Stop) yields an audit log where `python3
.claude/scripts/audit-verify-chain.py` exits 0; replay test in CI from the
recorded fixture; honesty assertion — the completeness residual sentence
appears in the degradation page diff (Wave 7).

- [ ] **A (preferred): hook-native appends** — PostToolUse `*` per-tool-call
      append via the codex adapter + SessionStart boot event, using the
      existing `audit_log.py` chain. **This IS a schema change** (drop any
      "no schema change" framing): `audit_log.py:566-567` returns `None`
      for non-Agent tools and `:642` hardcodes `action: "agent_spawn"`, so
      appending a per-tool-call event for the full `*` matcher requires a
      NEW registered action name (not `agent_spawn`) — see the registration
      coupling item below. The HMAC chain shape and `verify_chain()` stay
      untouched; the `_KNOWN_ACTIONS` enum grows.
- [ ] **B: `notify` turn-ended backstop** — turn-level append when
      per-tool-call events were missed (partial interception), marked with
      a distinct action so completeness analysis can tell rails apart.
- [ ] **Action registration is a four-file coupling, all in the SAME
      commit as the emitter (S261 PLAN-153 Wave E precedent, 302→303 —
      landed; current baseline 303):**
      each NEW action introduced by A (per-tool-call, non-`agent_spawn`)
      and B (turn-ended backstop) is (1) added to `_KNOWN_ACTIONS` in
      `_lib/audit_emit.py:153` WITH its closed-enum field allowlist
      (deny-by-default per-action allowlist per SPEC v2.41; `_write_event`
      rejects any unregistered action at `audit_emit.py:2475-2477`); (2)
      recorded in `SPEC/v1/audit-log.schema.md` as an **Amends**
      version-bump clause on the action row; (3) count+SHA rebaselined in
      `.claude/hooks/tests/test_audit_emit_api_contract.py` (the pin at
      `_EXPECTED_KNOWN_ACTIONS_SHA256`, count 303→304/305 from the
      current 303 baseline at `test_audit_emit_api_contract.py:656-658`);
      (4) emitted by the
      Wave 4 code — items 1-4 land in ONE commit so the api-contract test
      never goes RED against an unregistered emit. SENT-CX-B scope (Wave 0)
      names files 1-3; file 3's test is the unguarded companion.
- [ ] **C: wrapper for `codex exec`** — non-interactive runs get
      SessionStart/Stop bracketing via a thin wrapper script (unguarded
      `scripts/` or `templates/codex/`), so headless usage still lands in
      the chain.
- [ ] **Replay determinism + asserted backstop action (debate A13):** the
      CI replay test runs under `TestEnvContext` with a test-scoped HMAC
      key (never the real `$HOME`/`$CLAUDE_PROJECT_DIR`); a pytest
      assertion checks the Wave 4-B turn-ended backstop events carry the
      distinct action name AND that per-tool and turn-level appends are
      countable separately from the same log slice — the
      completeness-analysis query is itself the test, not prose.
- [ ] Honestly impossible, recorded in ADR-161 + §Deferred: TOTAL per-edit
      completeness (partial shell interception) and continuous
      config-tamper observation (no ConfigChange event).

### Wave 5 — Installer `--harness codex` (L3, SENT-CX-C; AFTER PLAN-153 install.sh waves land)

Check: `install.sh --harness codex --dry-run` on a scratch repo previews
the full delta; real run produces `.codex/hooks.json`, `.codex/rules/ceo.rules`,
operator `AGENTS.md` (≤32 KiB RENDERED, post-substitution), adapter env
wiring; the debate-A11 nine-case installer matrix green + CI-wired
same-commit; post-install arming check (debate A7) reports correctly on a
scratch install; lifecycle symmetry (debate A9) verified — uninstall
leaves zero `.codex`/pre-push enforcement residue; `shellcheck -S warning`
green; S258 scope assert green.

- [ ] `--harness <claude|codex>` flag (default `claude`, existing behavior
      byte-identical when absent — regression-tested).
- [ ] Codex path emits: (1) operator `AGENTS.md` from template; (2)
      `.codex/hooks.json` (or documented config.toml merge); (3)
      `.codex/rules/ceo.rules`; (4) trust-flow guidance — print the exact
      `/hooks` trust steps AND offer the `requirements.toml` managed
      option per OQ1's ratified default, including
      `projects."<path>".trust_level = "trusted"`; (5) optional skills
      copy/symlink → `.codex/skills/` per OQ2; (6) MCP reviewer
      registration INVERTED: register `claude` as the reviewer-side CLI
      (mirror of today's codex registration).
- [ ] Install-state recording composes with PLAN-153 Wave B's recorded
      original request (the `--harness` value must round-trip through
      `upgrade.sh` replay).
- [ ] **Post-install arming verification (debate A7):** a one-command
      doctor/`ceo-info`-class check (SessionStart audit-breadcrumb assert
      + benign behavioral probe) reporting ARMED /
      NOT-ARMED-(untrusted) / BROKEN, printed as the installer's FINAL
      instruction; installer output states loudly that NOTHING is
      enforced until `/hooks` trust is granted. Installed ≠ armed — the
      behavioral-over-static thesis must not stop at the installer's
      door.
- [ ] **Lifecycle symmetry (debate A9):** manifest + uninstall + backup +
      restore coverage for EVERY emitted path — `.codex/**`, the root
      operator `AGENTS.md`, and the Wave 6 git pre-push hook (a THIRD
      install surface under `.git/`, which no manifest walk reaches
      naturally) — specified against the LANDED PLAN-153 Wave B
      interface, not the staged one. An uninstall that leaves enforcement
      residue (live hooks, push gates) is not symmetric.
- [ ] **Collision policy (debate A10):** refuse/merge/backup semantics
      per emitted file — refuse-and-print-diff by default,
      `--force`/merge documented, never clobber a pre-existing
      `AGENTS.md` / `.codex/config.toml` / foreign `hooks.json` (that
      scenario is case 9 of the A11 matrix below).
- [ ] **Installer test matrix (debate A11), wired into `validate.yml`
      same-commit:** (1) no-flag run byte-identical via `diff -r` vs a
      pre-plan golden; (2) `--harness codex` with every registered
      command path resolving AND executable at the harness's real
      runtime resolution; (3) `--dry-run` zero writes; (4) unknown
      harness → usage error, no partial writes; (5) idempotent re-run;
      (6) `--harness` round-trips through the LANDED manifest into
      `upgrade.sh` replay; (7) RENDERED operator `AGENTS.md` ≤ 32768
      bytes (post-substitution on the scratch install, not
      template-only); (8) Wave 8 skills in manifest/doctor/uninstall if
      landed; (9) the A10 pre-existing-files collision case.
- [ ] **Version-skew surface (debate A15):** installer probes
      `codex --version`, warns outside the verified range, and records
      the detected version in the install manifest.

### Wave 6 — Inverted pair-rail + teeth for the advisory rails (L3, SENT-CX-D)

Check: live-fire transcript — a Codex session editing a canonical path
cannot Stop until the `claude -p` review ran (Stop hook `decision:block`
auto-continue), archived under `PLAN-155/artifacts/`; pre-push hook red on
missing review record + red on spawn-protocol violation in the chain;
validate.yml paths added same-commit as each new script.

- [ ] Stop-hook rail: on Stop, if the session touched L3+ paths without a
      recorded cross-model review, emit `decision:block` with the review
      instruction until the `claude -p` review verdict lands (verified
      non-interactive with claude 2.1.202). Reviewer contract = root
      `AGENTS.md` doctrine, direction-inverted; verdict vocabulary
      unchanged (APPROVE/REJECT with file:line).
- [ ] Git pre-push backstop: push blocked when canonical-path commits lack
      a review record — the PARTIAL rail's teeth when the Stop gate was
      abandoned. This hook is a THIRD install surface under `.git/`
      (debate A9): its manifest/uninstall/backup/restore coverage is
      bound by Wave 5's lifecycle-symmetry criteria.
- [ ] **RED-on-absence semantics (debate A2):** the pre-push/CI
      breadcrumb and chain assertions are defined RED on ABSENCE — no
      SessionStart breadcrumb / no session records despite new commits ⇒
      RED, not green. Vacuous green is the failure mode this class
      exists to catch; silence from a fail-open rail is not health.
- [ ] CI/pre-push teeth for the TWO honest ADVISORY rails: (a) spawn
      governance — chain scan proving every SubagentStart had the
      protocol-bearing `additionalContext` + flagging spawns that bypassed
      Bash-gated spawn paths; (b) config tripwire — boot-time settings-hash
      re-check breadcrumb asserted present per session window. Both
      documented as backstops, not as making the rails ENFORCED.
- [ ] Same-vendor caveat text INVERTED where applicable: under this rail
      the operating model is OpenAI and the reviewer is Anthropic — the
      "no single model is both author and sole reviewer" property holds in
      both directions; docs must state it direction-neutrally (Wave 7
      lands the wording, this wave supplies it).

### Wave 7 — Docs honesty sweep (L1-L2)

Check: `check-claude-md-claims.py` + `verify-counts.sh` +
`check-contamination.sh` + `check-agents-md.py` all green; no
"enforced" claim without a named residual (reviewed against the §matrix);
zero speed claims.

- [ ] `docs/degradation-outside-claude-code.md`: from blanket "no adapter
      is production → no enforcement claim" to the real per-rail Codex
      matrix (keep the generic outside-any-harness section for
      plain-editor/CI cases — that boundary is unchanged).
- [ ] `docs/adapters.md`: promote the codex row PER-RAIL (debate A15:
      each matrix row is tied to the wave that made it true —
      adapter/host-mode on Waves 1-4 exit criteria, installer path
      "PRODUCTION" only after Wave 5's exit criteria, inverted pair-rail
      after Wave 6; every Codex row carries "verified against codex-cli
      0.139.0") AND fix the pre-existing drift —
      gemini/openai/local rows describe modules absent from
      `KNOWN_ADAPTERS = ["claude", "codex"]` (`_lib/contract.py:216`);
      reconcile the doc to disk (re-verify module presence at execution
      time before deleting prose).
- [ ] `docs/provider_capability_matrix.md` + `docs/HONEST-LIMITATIONS.md`:
      Codex rows with the ENFORCED/ADVISORY/ABSENT labels + residuals;
      README/INSTALL `--harness codex` section; trust-flow +
      trust-rekeying friction documented where operators will actually
      read it.
- [ ] **CI-green ≠ current-Codex boundary (debate A12/A3):** docs state
      explicitly that CI replays FROZEN fixtures per pinned version —
      "CI certifies fixture-replay against a recorded wire; only local
      live-fire certifies the real binary, per pinned version."

### Wave 8 — OPTIONAL, Owner-gated: skills port to `.codex/skills/`

Check: install-time copy/symlink verified on a scratch repo; skill
frontmatter accepted by codex-cli 0.139 skill discovery for a 5-skill
sample; `check-claude-md-claims.py` + `verify-counts.sh` green (counts
MUST NOT drift); contamination grep green over the installed tree.

- [ ] Scope guard: this wave is an INSTALL-TIME copy/symlink of the
      existing 151 `SKILL.md` files into the target's `.codex/skills/` —
      it creates ZERO new skill files in THIS repo, so the hardcoded
      skill counts (CLAUDE.md tolerance=0) are untouched. Any
      Codex-specific skill content fork is out of scope (single source of
      truth stays `.claude/skills/`; a fork would double the maintenance
      surface and re-open contamination review per file).
- [ ] Symlink-vs-copy decision per OQ2; `--with-codex-skills` flag default
      per OQ2; uninstall symmetry (the PLAN-153 doctor/manifest machinery
      must see these files or explicitly exclude them — decide with the
      landed Wave B interface, not against the staged one).

## Open questions (Owner, Wave 0)

1. **OQ1 — adoption friction: `/hooks` trust vs `requirements.toml`
   managed.** Non-managed hooks require per-user `/hooks` trust keyed to
   file hash — every framework upgrade re-prompts (friction, but explicit
   consent). `requirements.toml` MANAGED hooks are trusted-by-policy and
   non-disableable (teeth, enterprise posture, but the installer would be
   writing policy the user can't toggle). Installer default: guide `/hooks`
   interactively and offer `requirements.toml` behind an explicit flag? Or
   invert? CEO recommends: **`/hooks` guided flow as default,
   `--managed-hooks` opt-in emitting requirements.toml** — consent-first
   matches the human-gated ethos; enterprises opt into teeth.
   **Ratification gate (debate A6):** OQ1 is ratified only AFTER the
   `/hooks` trust-hash keying semantics are empirically pinned (Wave 1/2:
   what does the hash attest — the registered shim only, or the
   transitive hook set?). The friction estimate and the consent-security
   meaning both invert on the answer; Wave 0 ratifies OQ2/OQ3 only.
2. **OQ2 — skills-port posture (Wave 8).** (a) skip Wave 8 entirely v1;
   (b) `--with-codex-skills` opt-in copy; (c) opt-in symlink (zero
   duplication, breaks if target tooling can't follow links). CEO
   recommends **(b) opt-in copy**, recorded in the install manifest for
   doctor/uninstall symmetry.
3. **OQ3 — inverted-rail reviewer pin.** Which `claude` model tier does the
   `claude -p` reviewer pin to, and what is the per-review token ceiling?
   (Mirror of the codex reviewer pin; needs a
   `docs/provider-pricing.md`-consistent row + named env override in the
   same commit that pins it.)

### Owner ratifications — 2026-07-10 (S265 wake-up ceremony, verbatim)

Presented via AskUserQuestion; selected options logged verbatim per the
CLAUDE.md AskUserQuestion doctrine.

- **A1 dispatch seam → OPTION (b) — single shared `resolve()` seam + only
  the 4 ENFORCED hooks migrated** (CEO recommendation, CONFIRMED). The
  Owner first selected (a) but, after the CEO corrected the record that
  (a) is a full re-implementation across +19 KERNEL hooks (not a text
  re-draft) with cascading Wave-3b/4 rebases — and that those 19 are
  Claude-only rails that never fire on Codex's wire shape, so (a) adds no
  Codex-matrix coverage, only kernel blast-radius — the Owner reverted to
  (b) on an informed re-choice (2026-07-10). Wave 1 overlay as-built
  already implements (b); SENT-CX-A scope stands as reconciled. Migrating
  the remaining advisory rails to the seam is available incrementally
  later if a Codex-side need for them appears.
- **AGENTS.md guard (SENT-CX-E) → KEEP (Recomendado).** Guarding the
  repo-root `AGENTS.md` (reviewer contract = trusted prompt surface)
  stands; SENT-CX-E unchanged on this point.
- **OQ1 → `/hooks` guided default + `--managed-hooks` opt-in** (Recomendado;
  ratified now — the empirical trust-hash keying fact is in
  `artifacts/trust-keying-A6.md`).
- **OQ2 → (b) opt-in `--with-codex-skills` copy** (Recomendado),
  manifest-recorded.
- **OQ3 → reviewer pin `claude-opus-4-8`, 100k-token ceiling, env override
  `CEO_PAIR_RAIL_REVIEWER_MODEL`** (Recomendado; ADR-052 VETO-floor parity).

## Success criteria

- [ ] Positive-control replay: the 3 planted violation classes
      (canonical-edit write, destructive bash, illegal plan transition)
      replayed as recorded Codex PreToolUse envelopes as SUBPROCESSES on
      the shipped `templates/codex/hooks.json` command line (debate A3)
      → all `permissionDecision: deny` + deny-reason class, with
      per-class negative + malformed-envelope controls, running in CI on
      every push (not just locally once).
- [ ] `audit-verify-chain.py` exit 0 over a real end-to-end Codex session
      (SessionStart → tool calls → Stop), with the recorded-session replay
      test in CI.
- [ ] `install.sh --harness codex` produces a working `.codex/` bundle on a
      scratch repo (hooks.json + rules + operator AGENTS.md ≤32 KiB
      rendered + trust-flow guidance); default `claude` path
      byte-identical to pre-plan behavior (`diff -r` asserted, debate
      A11).
- [ ] Post-install arming verification shipped (debate A7): a one-command
      doctor/`ceo-info`-class check reports ARMED / NOT-ARMED-(untrusted)
      / BROKEN, is printed as the installer's final instruction, and the
      installer states loudly that NOTHING is enforced until `/hooks`
      trust is granted. Lifecycle symmetry (debate A9): manifest +
      uninstall + backup + restore cover every emitted path incl. the
      `.git/` pre-push hook.
- [ ] Live-fire evidence archived: one real 0.139 session where a planted
      canonical edit is denied, and one where Stop is blocked until the
      `claude -p` review lands.
- [ ] `docs/degradation-outside-claude-code.md` + `docs/adapters.md` +
      `docs/provider_capability_matrix.md` updated to the real matrix; the
      spawn and config-tripwire rails documented as ADVISORY with named
      backstops — grep proves no "enforced" claim for them.
- [ ] Kill-switch protection has TEETH (Wave 3b, debate A8): a planted
      unsentineled edit to each `.codex` kill-switch path is DENIED by
      `check_canonical_edit.py` and a mutated kill-switch file turns the
      SessionStart boot re-hash RED; the guard-list extension landed under
      `CEO_KERNEL_OVERRIDE=PLAN-155-CODEX-KILLSWITCH-GUARD-EXTENSION` + ACK
      (SENT-CX-E) — the §capability-matrix row is no longer ABSENT.
- [ ] ADR-161 accepted; sentinels archived per retention policy; every
      SENT-CX commit passed the S258 scope assert.
- [ ] Zero CI-dark surfaces: every new script/test path added to
      validate.yml in the same commit; counts tolerance=0 respected;
      contamination gate green.

## How to continue (next session first message)

> Gate 1-3 per CLAUDE.md, then: read
> `.claude/plans/PLAN-155-codex-harness-compat.md` + the §Capability matrix
> + `docs/degradation-outside-claude-code.md` + `_lib/adapters/codex.py`
> (note its dual role: pair-rail reviewer-egress helpers stay untouched;
> host mode is the new surface). Debate round-1 is DONE (ADJUST_PROCEED,
> A1-A15 applied into this text — see §Debate). Codex pair-rail: R1
> REJECT → fixes → R2 APPROVE (S262) → S265 re-run REJECT on
> post-PLAN-153 disk drift (kernel-extension-v2 + 303 baseline) → fixes
> applied → **R3 APPROVE 2026-07-09 (S265)** — the execution gate is
> SATISFIED; status flipped `executing` S265.
> Next: execute Wave 0 with the Owner (ratify OQ2/OQ3 — OQ1 waits for
> the debate-A6 trust-keying answer; run the debate-A1 dispatch-surface
> inventory + seam ratification; sign SENT-CX-A/B/E with the A1/A2/A8
> scope consequences reflected — SENT-CX-E carries the KERNEL guard-list
> extension override; reserve ADR-161; SENT-CX-C only after
> PLAN-153's install.sh waves are MERGED on main — staged does not
> count). Waves in order 1→2→3→3b→4→5→6→7; Wave 8 only on Owner go.
> Re-verify the codex-cli version pin first (0.139.0 local vs 0.142.5
> upstream) — if the pin moves, bump the pin via the ADR-111 ceremony
> FIRST, then record the Wave 1 fixtures (debate A12).

## §Deferred (what Codex cannot give today)

- **Total shell-call interception.** Official caveat stands; per-edit
  enforcement completeness and audit completeness stay bounded. WATCH:
  Codex release notes / `developers.openai.com/codex/hooks` — re-test the
  interception surface at each CLI bump (0.142.5 already available vs our
  pinned 0.139.0; the substrate watch-item from Wave 0 owns the alert).
- **ConfigChange lifecycle event.** Continuous config-tamper observation
  stays ADVISORY (boot-time re-check only) until Codex ships an
  equivalent event. WATCH: same feed.
- **SubagentStart hard-block.** `continue:false` parsed-but-not-enforced is
  upstream behavior; if a future release enforces it, the spawn rail
  promotes ADVISORY→ENFORCED via a one-line matrix + docs change (and the
  Wave 6 teeth stay as defense-in-depth). WATCH: same feed.
- **Execpolicy expressiveness.** `prefix_rule` denylists only; anything
  richer (arg-aware policy) deferred to upstream capability.
- **Managed-hooks enterprise rollout guide** (requirements.toml at org
  scale) — deferred until a real enterprise adopter asks; OQ1 covers the
  single-repo posture only.

## Risks

- **Substrate drift, now on a second vendor.** The Codex hook schema is
  NOT covered by our substrate-watch today — Wave 0 adds the watch-item
  BEFORE code ships. Version skew is live (0.139.0 pinned vs 0.142.5
  upstream): fixtures are recorded per pinned version; a CLI bump without
  fixture re-record is the drift class PLAN-142 already paid for once
  (`codex_invoke.py` vs 0.139 empty-stdout).
- **Trust-rekeying friction.** `/hooks` trust is keyed to a hook file
  hash — WHICH file is empirically pinned in Wave 1/2 (debate A6): the
  re-prompt cost ranges from ~zero (shim-only keying — thin consent) to
  per-file-per-upgrade (consent fatigue) depending on the answer.
  Mitigation: pin it empirically before ratifying OQ1, document loudly
  (Wave 7), `requirements.toml` path offered (OQ1); do NOT "solve" this
  by discouraging hook updates.
- **Dual-role `codex.py` regression.** Host-mode `write_decision` changes
  the emitted shape; the pair-rail reviewer-egress helpers share the
  module. Mitigation: helpers untouched by contract, golden fixtures
  updated deliberately in the same commit, full hook suite + live adapter
  tests both adapters green before merge.
- **install.sh collision with PLAN-153.** Two plans, one guarded file.
  Hard sequencing rule in Approach + SENT-CX-C anchor-sha taken on
  post-PLAN-153 main; violating this trips the S258 scope assert by
  design.
- **Overclaim risk (the honesty failure mode).** "Runs on Codex" will be
  read as "same guarantees as Claude Code". Every outward sentence must
  carry the matrix vocabulary; the two ADVISORY rails and the audit
  completeness bound are named in the same breath as the ENFORCED rails.
  The pair-rail same-vendor caveat is direction-neutralized, not deleted.
- **Audit-log noise under partial interception.** Turn-ended backstop
  events (Wave 4 B) must be distinguishable from per-tool appends or
  completeness analysis silently lies; distinct action name is part of the
  wave's exit criteria.

## Reference links

- Research: S261 Codex-harness research (verified vs local codex-cli
  0.139.0 + `developers.openai.com/codex/{hooks,config-reference,rules,guides/agents-md}`)
- On-disk anchors verified at authoring (S262): `_lib/contract.py:216`
  (KNOWN_ADAPTERS), `_lib/adapters/codex.py` (dual-role reality),
  `docs/adapters.md:58-61` (stale codex row),
  `.claude/hooks/tests/{test_adapter_golden.py,test_adapter_drift_detector.py,adapters/live/test_adapters.py}`,
  `scripts/install.sh:378-460` (flag surface, no `--harness`)
- Doctrine: ADR-008 (adapter layer), ADR-107/ADR-145 (pair-rail + review
  modality), ADR-121 (dual signer rails), PLAN-142 (codex-cli substrate
  lesson), PLAN-152 C4 (fail-closed on input), PLAN-153 (Wave E
  positive-control doctrine + Wave B installer interface this plan
  composes with), `docs/degradation-outside-claude-code.md` (baseline)
- Successor context: PLAN-153 §Deferred / PLAN-154 preconditions —
  unrelated tracks; only the install.sh sequencing couples us.

## Debate

**Round 1 — 2026-07-07 — verdict: ADJUST_PROCEED.** Tally: 3×
ADJUST_PROCEED / 0 VETO / 0 PROCEED (seats: security-engineer,
qa-architect, devops-dx; P1's bare "ADJUST" normalized to ADJUST_PROCEED
per the house vocabulary). Full record:
`.claude/plans/PLAN-155/debate/round-1/consensus.md` + the three position
files alongside it.

- **Binding adjustments A1–A15: ALL applied into this plan text**
  (S259/S261 amender precedent, Owner delegation) — A1 Wave-0
  dispatch-surface inventory + seam ratification (CEO_HOOK_ADAPTER has
  zero consumers today); A2 host/adapter coherence gate fail-CLOSED per
  C4 + RED-on-absence assertions; A3 subprocess positive/negative/
  malformed controls on the shipped command line + T1/T2/T3 normative in
  ADR-161; A4 anti-vacuous-green golden suite (min-fixture-count, codex
  out-goldens, drift-detector extension); A5 empirical failure-semantics
  matrix + Stop-block transcript gating the pair-rail matrix row; A6
  trust-hash attestation empirically pinned BEFORE OQ1 ratification; A7
  post-install arming verification (ARMED/NOT-ARMED/BROKEN); A8
  kill-switch registration surface guarded (deny matcher + boot
  tripwire); A9 lifecycle symmetry incl. the `.git/` pre-push third
  surface; A10 collision policy (never clobber); A11 nine-case installer
  matrix in validate.yml; A12 fixture↔pin mechanical coupling + per-bump
  re-verification checklist; A13 audit replay under `TestEnvContext` +
  pytest-asserted backstop action; A14 reviewer-egress characterization
  pre-gate; A15 staged per-rail docs promotion + operator-visible
  version pin.
- **Advisory A16–A26 (execution-time discretion, recorded per
  consensus):** A16 spawn-row inherited `^Bash$` interception residual
  wording; A17 AGENTS.md hygiene (top-of-file governance summary,
  shadowing warn, static/redacted `additionalContext`); A18
  wrapper-bypass residual named + wrapper as a first-class documented
  command; A19 MCP arg-shape residual named in the canonical-edit row;
  A20 ADR-161 reviewer-unavailable-posture paragraph; A21 citation
  hygiene sweep (phantom `test_adapters_parity.py`; parity-gate vs
  ADR-040 live-suite wording); A22 commit-posture paragraph (teammate
  trust re-prompts); A23 OQ3 states operator-visible latency/cost
  expectations; A24 Wave-8 codex-skills upgrade/drift story; A25 ADR-161
  parity definition (strict normalized-input equality, per-harness
  output contracts); A26 versioned-fixture mechanism adopted now.
- **Cross-position convergence:** all three seats independently attacked
  the S254 silent-disarm class at three layers — wiring (A1), runtime
  coherence (A2), operator liveness (A7); all three binding, any one
  alone leaves a silent-ABSENT path open.
- **Unanimous do-not-change list honored:** adapter-first / no hook
  forks; consent-first OQ1 default; behavioral positive-control as the
  certifying artifact; ENFORCED/ADVISORY/ABSENT with residuals in-claim;
  ADVISORY rails stay ADVISORY (no promotion-by-debate); install.sh
  sequencing vs PLAN-153; C4 fail-open-infrastructure /
  fail-closed-input carried over unchanged.
- Sentinel-scope consequences (A1, A2, A8) are reflected in Wave 0
  allocation BEFORE signing — no execution-time scope widening.

Status flipped `draft → reviewed` 2026-07-07 by the debate amender under
Owner delegation, after applying all fifteen binding adjustments.

### Codex pair-rail (cross-LLM review of the plan text)

- **Round 1 — 2026-07-07 — verdict: REJECT (2 findings).** The pair-rail
  (Codex) reviewed the plan as authored and rejected it for two
  under-scoping errors, both since resolved in this text (2026-07-07,
  S261):
  - **P1 — ceremony misclassification (Waves 2/3 sold protection they
    could not deliver at L2).** The plan required the `.codex` kill-switch
    surface (`.codex/hooks.json`, `.codex/config.toml`,
    `.codex/rules/ceo.rules`, `requirements.toml`, operator `AGENTS.md`)
    to enter the deny matcher + boot tripwire, but those paths are not in
    `_CANONICAL_GUARDS` (`check_canonical_edit.py:137-142`), the boot
    tripwire hashes only Gate-1 files (`SessionStart.py:48-54,:79`), and
    the disk census covers only registered `.claude/hooks/*.py`
    (`effective_config.py:192-199`); extending the first is a KERNEL-class
    guard-list extension (that file is in `_KERNEL_PATHS`), the other two
    are canonical-guarded hook/_lib edits — none of which an L2
    templates-only wave can perform. **Fix:** carved the protection into a
    new **L3 Wave 3b (SENT-CX-E)** with the guard-list extension
    (KERNEL-override-gated: `CEO_KERNEL_OVERRIDE=PLAN-155-CODEX-KILLSWITCH-GUARD-EXTENSION`
    + ACK), the tripwire extension, and the census extension named
    explicitly in the sentinel scope; kept Waves 2/3 as L2 emission-only
    with the teeth deferral stated in-text; recorded the surface as ABSENT
    until Wave 3b in the §capability matrix and allocated SENT-CX-E in
    Wave 0.
  - **P2 — Wave 4 audit change under-scoped (a false "no schema change"
    claim).** `audit_log.py:566-567` ignores non-Agent tool events and
    `:642` hardcodes `action: "agent_spawn"`; `_lib/audit_emit.py` gates
    every write on a fixed `_KNOWN_ACTIONS` registry (`:153`) and rejects
    unknown actions (`:2455` at R1 time; now `:2475-2477`). A distinct
    per-tool/turn-ended action is
    therefore a four-file coupling, exactly the S261 PLAN-153 Wave E
    302→303 precedent. **Fix:** dropped the "no schema change" claim in
    Wave 4-A; added the same-commit four-file registration item
    (`audit_emit._KNOWN_ACTIONS` + closed-enum allowlist,
    `SPEC/v1/audit-log.schema.md` Amends clause,
    `test_audit_emit_api_contract.py` count+SHA rebaseline, emitter) and
    named files 1-3 in SENT-CX-B scope in Wave 0.
- **Round 2 — 2026-07-07 (S262) — APPROVE, no residuals** (recorded in
  commit `314891a`'s message; this paragraph previously said PENDING —
  stale). That verdict was rendered against PRE-PLAN-153-landing main.
- **Round 2 re-run — 2026-07-09 (S265) — REJECT (5 findings + 2 P3),
  all disk-drift:** the PLAN-153 landing (2026-07-08, `24d2a27` +
  series) extended `_KERNEL_PATHS` (ADR-116-AMEND-1 kernel-extension-v2)
  and landed the 302→303 action registration, invalidating this plan's
  ceremony scoping written against the older main. F1: SENT-CX-A files
  (`_lib/adapters/codex.py`, `adapters/__init__.py`, `contract.py`) are
  KERNEL (`check_arbitration_kernel.py:165,168,85`) → Wave 1 needs
  `CEO_KERNEL_OVERRIDE=PLAN-155-CODEX-HOST-ADAPTER` + ACK. F2:
  `SessionStart.py` IS KERNEL (`:201`) → Wave 3b boot-tripwire edit rides
  the SENT-CX-E override (the "sentinel-only" claim was wrong). F3:
  `audit_log.py`/`audit_emit.py` are KERNEL (`:200,90`) → Wave 4 needs
  `CEO_KERNEL_OVERRIDE=PLAN-155-CODEX-AUDIT-ACTIONS` + ACK. F4: action
  count baseline is 303 (pin at `test_audit_emit_api_contract.py:656-658`),
  not 302 → Wave 4 rebaselines 303→304/305. F5: SENT-CX-D surfaces
  (`check_pair_rail.py`, `dispatcher/**`, `validate.yml`) are KERNEL
  (`:180,133,135`) → `CEO_KERNEL_OVERRIDE=PLAN-155-CODEX-PAIRRAIL-TEETH`
  + ACK if touched. P3 anchor fixes: `audit_emit.py:2455`→`:2475-2477`;
  `check_bash_safety.py:169`→`:201`. **All 7 fixes applied into this
  text 2026-07-09 (S265).**
- **Round 3 — 2026-07-09 (S265) — APPROVE.** F1-F5 verified resolved
  against disk (kernel lines 85/165/168, 201, 90/200, count pin
  `test_audit_emit_api_contract.py:656-658`, 180/133/135); the two P3
  leftovers (stale `:2455` in the historical R1 paragraph — annotated;
  §How to continue R2-PENDING contradiction — fixed) applied same
  session. **Execution gate SATISFIED**; Owner signing of the SENT-CX
  sentinels (with the three kernel-override slugs) remains the morning
  ceremony.
