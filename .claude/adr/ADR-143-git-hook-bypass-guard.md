---
id: ADR-143
title: Git hook-bypass guard — new audit action + dual-auth escape hatch + fail-closed parse mode
status: ACCEPTED
decision_date: 2026-06-02
proposing_session: S20x
accepted_at: 2026-06-17
accepting_session: S242
enforcement_commit: bf11d3a0
authorization: "PLAN-124 WS-1 (ECC value-harvest) — debate R1 PROCEED (MF-A..MF-L folded) + Codex pair-rail R1 BLOCK->R2 EXECUTE-READY. Owner GPG ceremony pending; this ADR is the not-silent authorization for the SPEC/kernel contract change (a NEW closed-enum audit action) per VERSIONING.md."
owner: security-engineer
plan: PLAN-124-ecc-value-harvest
amends: none
related: [ADR-040, ADR-055, ADR-056, ADR-139, ADR-124, ADR-125, ADR-126]
---

# ADR-143 — Git hook-bypass guard

**Status:** ACCEPTED (S242, 2026-06-17 — git-bypass guard live in the Tier-1
`check_bash_safety.py`, registered in `.claude/settings.json`, 85 tests, SPEC v2.38;
Codex pair-rail R1 BLOCK→R2 EXECUTE-READY at PLAN-124 WS-1 + Codex R-sweep ACCEPT
thread `019ed788`)
**Enforcement commit:** `bf11d3a0` (PLAN-124 WS-1 — `_lib/git_bypass.py` wired into
`check_bash_safety.py` + the `git_hook_bypass_blocked` closed-enum action; later fix `97ed70cb`)
**Blast radius:** L3 (a NEW closed-enum audit action = SPEC/kernel contract
change; a new PreToolUse Bash decision branch on the Tier-1 `check_bash_safety.py`)
**Supersedes:** none
**Superseded by:** none
**Depends on:** ADR-040-AMEND-2 §Layer-1 (import-time `trusted_env` snapshot as
the trust root for `CEO_*` escape-hatch reads); ADR-055/ADR-056 (audit-emit
closed-enum + per-action field allowlist contract); ADR-139 (Tier-1 86%
enforcing coverage floor for `check_bash_safety.py`)

## Context

PLAN-124 harvests governance/correctness mechanisms from `affaan-m/ECC`
("Everything Claude Code", MIT). WS-1 ports the *idea* of ECC's
`scripts/hooks/block-no-verify.js` — a tokenizer that blocks git hook-bypass
flags — as a clean-room stdlib-Python re-implementation.

**Honest framing (debate K2 / MF-A — the "crown jewel" framing is RETRACTED):**
this is **defense-in-depth + adopter protection + git hygiene**, NOT a fix for
a structural hole in *this* repo's moat. Our pre-commit governance is a Claude
Code **PreToolUse** hook (`settings.stack.node.json`) that fires regardless of
`--no-verify` / `core.hooksPath`, and our `.git/hooks/` holds only `.sample`
files. The real beneficiary is an **adopter** repo that relies on git-native
hooks. WS-1 ships at the corrected (lower) priority debate K2 assigned it.

ECC covers **6** subcommands (`commit`/`push`/`merge`/`cherry-pick`/`rebase`/
`am` — Codex falsified an earlier debate "no `am`" claim, MF-C), treats `-n` as
`--no-verify` for `commit` only, and blocks the inline `-c core.hooksPath=…`
global. ECC does **not** cover the `GIT_CONFIG_COUNT`/`GIT_CONFIG_KEY_<n>`/
`GIT_CONFIG_VALUE_<n>` env channel, `git config` *writes* to `core.hooksPath`
(the split attack), or `--git-dir`/`-C`/alias smuggling. Our guard must
therefore **exceed** ECC, not match it (MF-D).

## Decision

Add a pure stdlib tokenizer + decision function in a NEW module
`.claude/hooks/_lib/git_bypass.py` (`scan_command(command) -> Optional[GitBypassMatch]`),
consumed by the Tier-1 PreToolUse `check_bash_safety.py` hook, that blocks the
git hook-bypass vectors below, and a NEW closed-enum audit action
`git_hook_bypass_blocked` (the SPEC/kernel contract change this ADR authorizes).

### Blocked vectors (exceeds ECC, MF-C / MF-D)

1. `--no-verify` on the **6** subcommands `commit`/`push`/`merge`/
   `cherry-pick`/`rebase`/`am`.
2. `-n` (and combined short bundles `-nm` / `-nFm`) counts as `--no-verify`
   **only for `commit`** (MF-B). For `push`, `-n` is `--dry-run` and **passes**.
3. Inline `-c core.hooksPath=…` (case-insensitive key), incl. the glued
   `-ccore.hooksPath=…` short form.
4. `git config` **writes** to `core.hooksPath` — the split attack (a `--get`
   read passes; a value, `--unset`/`--add`/`--replace-all` is a write).
5. The `GIT_CONFIG_COUNT` + `GIT_CONFIG_KEY_<n>`=`core.hooksPath` env channel,
   set via inline `VAR=value git …`, `env VAR=value git …`, or `export VAR=…`.
6. `--git-dir=` / `-C <dir>` repo redirection **paired with** a hook-bearing
   write subcommand (a plain `git -C ../other status` read passes — MF-F).
7. `-c alias.X=<body>` whose body smuggles `--no-verify` / `core.hooksPath`.

### Closed-enum audit action `git_hook_bypass_blocked` (MF-G)

A NEW kernel-allowlisted action (`_KNOWN_ACTIONS`, 270 → 271) with a
**dedicated** `emit_git_hook_bypass_blocked(...)` emitter routing through a
**dedicated scrub branch + per-action field allowlist**
(`_GIT_HOOK_BYPASS_BLOCKED_ALLOWLIST`). It **never** routes through
`emit_generic`'s verbatim-passthrough set
([[feedback-closed-enum-breadcrumb-must-not-echo-rejected-value]]). The ONLY
caller-supplied field is `flag_class`, a member of a CLOSED set:

```
no_verify_commit · no_verify_other_subcmd · hookspath_inline ·
hookspath_config_write · git_config_env_channel · git_dir_redirect ·
alias_abuse · parse_failure · escape_hatch_used
```

The matched **command bytes are NEVER persisted** — a flag value such as
`-c http.extraHeader="Bearer <secret>"` is a secret (MF-G). An unrecognized
`flag_class` is **coerced to `parse_failure`** at the typed emitter AND again in
the `emit_generic` dispatch branch (defense-in-depth — a direct `emit_generic`
caller smuggling a raw command substring into `flag_class` cannot reach the
signed HMAC chain). A test asserts no ≥8-char substring of a malicious command
leaks into the emitted event. The closed set is mirrored as a literal frozenset
in `audit_emit.py` (zero import-time dependency on the hook-side tokenizer); a
test asserts the two frozensets are equal.

### Dual-auth escape hatch (MF-E)

The bypass is allowed only via the proven dual-auth pattern
(`check_canonical_edit.py`, ADR-040-AMEND-2 §Layer-1) on a NEW dedicated env
pair: `CEO_GIT_BYPASS_ALLOW` (a reason/ticket matching
`^(ADR-\d{3,4}|PLAN-\d{3})-[a-z0-9-]{3,100}$`) **+** `CEO_GIT_BYPASS_ALLOW_ACK`
== `I-ACCEPT`. **Both are read from the import-time `trusted_env` snapshot, NOT
live `os.environ`** — a late-set value injected by a sub-agent / subprocess
cannot grant the bypass. When the hatch is used the hook ALLOWs and emits
`flag_class=escape_hatch_used`. Tested on-path (valid dual-auth allows) AND
off-path (missing/invalid ACK or bad ticket still blocks; a live `os.environ`
value absent from the snapshot does NOT grant).

### Fail-closed parse mode (MF-L)

An unparseable command that **clearly invokes git** is treated as a potential
bypass → **fail-CLOSED BLOCK** (`flag_class=parse_failure`). The fail-closed is
**bounded** so a tokenizer/infra bug cannot brick the whole session: a command
that does NOT clearly invoke git (e.g. an `awk` one-liner with an unbalanced
quote) passes through untouched. A tokenizer exception inside the hook fails
**OPEN** per the §5 hook contract — only the deliberate `parse_failure` path of
the pure detector is fail-closed.

## Consequences

- A new SPEC row (`audit-log.schema.md`, schema note **v2.38**) documents
  `git_hook_bypass_blocked` and its closed `flag_class` enum; the version note
  is bumped consistently with the S202 PLAN-125 `tool_call_lifecycle_recorded`
  precedent (v2.37 → v2.38).
- `check_bash_safety.py` (Tier-1, ADR-139:63) gains a new decision branch that
  runs BEFORE the destructive matchers; the new branches in `git_bypass.py` +
  `check_bash_safety.py` are branch-complete tested to meet the **86%** Tier-1
  enforcing floor.
- No new always-loaded context surface and no new hot-path subprocess: the
  tokenizer is pure stdlib invoked inline in the existing PreToolUse hook.
- The dual-auth hatch makes a legitimate, audited bypass possible without
  weakening the default-block posture.

## MIT attribution (MF / open question 5)

The `--no-verify` tokenizer **idea** is credited to `affaan-m/ECC`
`scripts/hooks/block-no-verify.js` (MIT, v2.0.0-rc.1). This is a clean-room
stdlib-Python re-implementation — no vendored JavaScript — that **exceeds** the
original (env channel, `git config` split-attack write, `--git-dir`/`-C`/alias
coverage, the dual-auth escape hatch, the closed-enum tamper-evident audit
action, and the bounded fail-closed parse mode). The MIT license of ECC permits
this re-implementation with attribution.

## Alternatives considered

- **Match ECC 1:1 (the 6 subcommands + inline `-c` only):** rejected — leaves
  the env channel + split-attack write + redirect/alias smuggle open, which
  would re-create the exact ECC overclaim anti-pattern PLAN-124 rejects.
- **Block ALL `git config` edits / ALL `-C` redirects:** rejected — too much
  friction; a `git config --get core.hooksPath` read and a `git -C ../x status`
  read are legitimate and MUST pass (MF-F regression corpus).
- **A single-env-var (no-ACK) escape hatch:** rejected — the proven dual-auth
  (reason/ticket + `_ACK=I-ACCEPT` + import-time snapshot) is the established
  trust-root contract (ADR-040-AMEND-2); a weaker hatch would be the new
  weakest link.
