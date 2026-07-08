# ADR-158: Harness-config gate — behavioral positive-controls certify, static scans complement

**Status:** ACCEPTED (S261, 2026-07-07 — PLAN-153 Wave E items 1/2/3;
acceptance flips at landing: the gate + tests are authored and staged under
SENT-E at `PLAN-153/staged/wave-E/`, the `/ceo-boot` checks are already
landed direct; the Owner's wake-up ceremony — sentinel signature →
scope==touched assert → overlay apply → CI-equivalent gates — flips this
line to ACCEPTED)
**Date:** 2026-07-07
**Decision drivers:** the S254 audit fan-out (run `wf_071ef6c5`) proved the
v1.0.0 pair-rail PreToolUse gate had been DEAD since ship — a relative shim
path in `settings.json` resolved to nothing at runtime and the shim
fail-opened with `{}` — while every static repo-root check stayed green;
PLAN-153 debate round-1 consensus #2 ratified the doctrine "behavioral
positive-control certifies; static scan complements"; debate B unseen-1
added that silence from a fail-open rail is not health.
**Related decisions:** ADR-159 (sibling Wave E — citation gate + prompt
defense), **ADR-160 is RESERVED for the PLAN-154 learning-loop doctrine —
do not allocate it elsewhere** (Wave 0 correction, PLAN-153 §Wave 0 log
item 3: this trio was drafted as "ADR-173/175/174" on a count-vs-index
confusion; artifacts citing those numbers read as 158/159/160), ADR-146
(adversary-review hook — prior art for a guard-of-the-guards), ADR-121
(dual signer rails governing the SENT-E landing ceremony).

> Alias note: Wave-E code markers and author reports cite this record as
> "ADR-173". Same decision, corrected index.

## Context

A hook registered in `.claude/settings.json` is only a security rail if it
**resolves and fires at runtime**. The framework's prior assurance was
static: `.claude/scripts/check-active-hooks-executable.py` parses the two
settings files, extracts hook commands, and asserts each script exists and
is executable — resolved against `REPO_ROOT` (its own `Path(__file__)`
anchor). That check is necessary and stays; but S254 proved it structurally
blind to the class that actually shipped:

- The harness guarantees `$CLAUDE_PROJECT_DIR`; it does **not** guarantee
  the shell's cwd is the repo root. A command reaching into `.claude/...`
  without anchoring on `$CLAUDE_PROJECT_DIR` (or an absolute path) works in
  dev and is a dead rail in production. That was the v1.0.0 pair-rail bug
  (today `settings.json:201` is correctly anchored).
- The `_python-hook.sh` shim resolves its script *argument* against its own
  directory (`_python-hook.sh:274` — `HOOKS_DIR` from
  `dirname "${BASH_SOURCE[0]}"`), so bare `check_x.py` arguments are fine —
  but only if the shim path itself resolves. When the target script is
  missing at the runtime-resolved path, the shim prints `{}` and exits 0
  (`_python-hook.sh:284-288`): a silent fail-open, invisible to a
  repo-root existence scan.
- A rail that is *designed* to fail open on infrastructure (the house
  rule) has a second failure mode: fail-opening on **every** invocation
  over a window. `check_pair_rail.py` fail-opens by design when Codex is
  absent — exactly the S254 root cause — and nothing surfaced it.

## Decision

1. **Behavioral positive-control per blocking hook** (the centerpiece).
   Every security-critical hook ships a red-team fixture — a known-bad
   input it MUST block, stored as clearly-marked inert JSON data under
   `.claude/hooks/tests/fixtures/harness-config/replay/` — and CI replays
   it against the real hook in a scrubbed hermetic env (temp
   HOME/GNUPGHOME/audit dir; no session `CEO_*` overrides leak in),
   asserting a block-shaped decision. A fixture that is missing,
   unparseable, tampered (`expect != block`), or that stops firing
   **reddens the build**. v1 replay set (`REQUIRED_REPLAY_CONTROLS`):
   `check_canonical_edit.py` (unauthorized canonical edit),
   `check_bash_safety.py` (destructive command),
   `check_agent_spawn.py` (named spawn missing `## SKILL CONTENT`).
   The already-frozen `check_postcompact_reinject.py` pointers-only
   positive-control (`hooks/tests/test_postcompact_reinject_no_exec_payload.py`,
   Wave E item 6) is the endorsed model this generalizes.
2. **Static side: `.claude/hooks/check_harness_config.py` as an EXTENSION
   of `check-active-hooks-executable.py`, not a duplicate.** The new gate
   *delegates* the exists+exec-bit sweep to the existing script
   (`run_exec_bit_gate`) and adds only what a repo-root scan cannot see:
   **runtime-resolution modeling** (`$CLAUDE_PROJECT_DIR` + the shim's
   dirname/cwd logic, never `REPO_ROOT`; cwd-dependent commands and
   runtime-unresolvable shims go RED — a planted runtime-unresolvable
   fixture proves the detector), an **inline-secret scan** over settings
   string values (family id + JSON path only; matched content never
   echoed), **missing-deny detection** (`DENY_BASELINE` floor must be a
   subset of `permissions.deny`), and **intentional no-op annotation**
   (constant-emitter hook commands are RED unless opted in via the
   `[harness-noop-ok]` marker, `harness-noop-allowlist.txt`, or the
   shipped defaults — fixtures prove both directions, debate A R-VP6).
3. **Failure doctrine.** This is a CI/preflight gate, not a registered
   session hook: it fails LOUD (exit != 0), never silently green. Input the
   matcher cannot parse is a finding, not a skip — fail-CLOSED per the
   `check_bash_safety.py` `_e3` precedent (`check_bash_safety.py:429-431`,
   PLAN-152 debate C4). `CEO_SOTA_DISABLE=1` skips only the optional
   replay machinery; static checks still run.
4. **Liveness for fail-open rails in `/ceo-boot`** (debate B unseen-1).
   Tier-S check `failopen_rail_liveness_7d` (`ceo-boot.py:1735`; classifier
   registry `:1726`, v1 ships `pair_rail`; window
   `CEO_FAILOPEN_LIVENESS_WINDOW_H` clamped [1, 2160]h, default 168h)
   streams the audit-log window once: all classified invocations
   fail-opened → **RED**; mixed → yellow; healthy reviews → green; and —
   the doctrinal point — **zero events → YELLOW "no signal", never green**.
   Silence from a fail-open rail is not health. Sibling Tier-S check
   `harness_config_gate` (`ceo-boot.py:1824` onward) runs the static gate
   at boot, green-if-missing until E1 lands (no landing-order constraint
   from boot).
5. **Deny baseline, framed honestly** (debate B expansion). Shipped
   `settings.json` + `install.sh` injection (`DENY_BASELINE_ENTRIES`, 20
   entries: `~/.ssh/**`, `~/.aws/**`, `**/.env` minus
   `.example/.sample/.template`, `Bash(curl * | bash)`, etc.) is a
   **coarse harness backstop** complementary to `check_bash_safety.py`'s
   parse gate (which owns the pipe-to-shell class) — never sold as
   coverage. `docs/deny-baseline.md` records the five explicit non-claims.
   The gate's `DENY_BASELINE` floor (7 entries) is deliberately narrower
   than the installer's 20 until the template-parity decision lands (Wave-E
   MANIFEST, cross-report finding 1).
6. **CI wiring, same commit** (consensus #5). `validate.yml` gains a
   "Harness-config gate" step (exit != 0 red) landing in the same series as
   the hook + staged tests (MANIFEST blocker 3: the step hard-fails on a
   missing gate file, so hook-first or one commit).

## Consequences

- The S254 class — a registered rail that silently resolves to nothing —
  can no longer ship green: runtime-resolution modeling catches it
  statically, the replayed positive-control catches it behaviorally, and
  the liveness check catches the fail-open-by-design variant at boot.
- Hook count on disk goes 53 → 54 at landing; `verify-counts.sh` and the
  CLAUDE.md claims check exact-pin the old number and must move in the same
  landing series (Wave-E MANIFEST blocker 2). "Registered hooks" stays
  44/45 — the gate is CI+boot, not a runtime hook.
- Every future security-critical hook owes a replay fixture; adding a
  blocking hook without one is a gate finding, not a style nit.
- Intentional no-op hooks are now an *annotated* state, never an ambient
  one.

## Alternatives considered

- **Static-only extension** — rejected by debate consensus #2: S254 is the
  existence proof that the dead-rail class is invisible to static scans;
  a scan alone re-certifies the same blindness.
- **A second standalone static gate** — rejected: duplicate parsing of
  settings drifts; extension-by-delegation keeps one owner for the
  exists+exec sweep.
- **Registering the gate as a runtime PreToolUse hook** — rejected: adds
  hot-path cost on every tool call and would itself be subject to the
  dead-rail class it polices; CI + `/ceo-boot` are the right surfaces.
- **Treating zero liveness events as green** — rejected (debate B
  unseen-1): that is precisely the S254 silence; "no signal" is yellow by
  doctrine.
- **Selling the deny baseline as command-coverage** — rejected: glob-level
  deny is trivially bypassable in ways the parse gate is not; honesty-first
  framing is a plan invariant.
