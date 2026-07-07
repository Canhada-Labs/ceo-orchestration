---
plan: PLAN-155
round: 1
archetype: devops-dx
verdict: ADJUST_PROCEED
created_at: 2026-07-07
---

## Verdict

ADJUST_PROCEED — the adapter-first thesis, the no-hook-forks posture, and the
matrix-vocabulary honesty discipline are the right platform calls, and the
OQ1 recommendation (consent-first `/hooks` default, `--managed-hooks` opt-in)
is the correct DX default. But the plan ships a second install surface
(`.codex/**`, root `AGENTS.md`, and a Wave 6 git pre-push hook) into a
lifecycle machinery that is `.claude/`-scoped by construction, has no
collision policy for files Codex adopters already have, and has no way for an
operator to tell that the rails are actually FIRING (trust not granted, or
adapter silently fell back) versus merely installed. Those are the failure
modes that generate "installed it, nothing happened" adoption reports —
which, for a framework whose entire pitch is enforcement, is the
reputation-fatal class. Five must-fixes; everything else advisory.

## Summary (≤ 3 bullets)

- Strong: adapter linchpin first; one enforcement kernel, two registrations;
  behavioral positive-control as the certifying artifact; hard install.sh
  sequencing vs PLAN-153; Wave 8 scope guard keeping counts tolerance=0
  untouched. The honesty matrix with named residuals is exactly the house
  ethos applied to a new harness.
- Weak (blocking): install/uninstall asymmetry — the entire `.codex` surface
  is invisible to the manifest, uninstall, backup AND restore machinery on
  disk today; no clobber policy for pre-existing `AGENTS.md` /
  `.codex/config.toml`; no post-install liveness signal for trust or adapter
  resolution (two independent silent-ABSENT paths).
- Blind spot: `resolve_adapter()` silent-fallback (`_lib/contract.py:225-240`)
  was designed for a claude-default world. With a second production harness,
  an explicitly-set-but-unresolvable `CEO_HOOK_ADAPTER=codex` composes with
  fail-open-on-infrastructure into "every rail ABSENT, zero signal".

## Risks

- **R-DX-01 — the `.codex` surface is outside every lifecycle rail we ship.
  Severity: HIGH.**
  Wave 5 emits `.codex/hooks.json`, `.codex/rules/ceo.rules`, an operator
  `AGENTS.md` (repo root), and optionally 151 skills under `.codex/skills/`;
  Wave 6 additionally installs a **git pre-push hook** (a third surface,
  under `.git/hooks/` or `core.hooksPath` — named nowhere in any
  install/uninstall line). The machinery on disk cannot see any of it: the
  baseline-manifest generator enumerates a closed root-set of `PROTOCOL.md` +
  `.claude/**` paths (`scripts/_framework_manifest_set.sh:71-96`);
  `scripts/uninstall.sh` backups tar **only `.claude/`** (`uninstall.sh:174-178`),
  the post-removal sweep walks only `.claude/` (`uninstall.sh:264-273`), and
  `--restore` moves only `.claude/` aside (`uninstall.sh:140-144`). The plan
  mentions uninstall symmetry ONLY inside optional Wave 8, and only for
  skills. Result: uninstall reports clean while the target still has live
  Codex hooks registered and a pre-push gate installed — a leftover
  *enforcement* residue, worse than leftover files. Mitigation: Wave 5 exit
  criteria must include manifest recording + uninstall/backup/restore
  coverage for EVERY emitted path (`.codex/**`, root `AGENTS.md`, the Wave 6
  pre-push hook), decided against the **landed** PLAN-153 Wave B interface,
  not the staged one.

- **R-DX-02 — installer clobber risk on files Codex adopters already have.
  Severity: HIGH.**
  The target audience for `--harness codex` is, by definition, people already
  using Codex — who therefore very plausibly already have a root `AGENTS.md`
  (Codex's standard operator file, the plan's own ground-truth section says
  discovery is git-root→cwd), a `.codex/config.toml`, possibly their own
  hooks registration. Wave 5 says "operator `AGENTS.md` from template" and
  "(or documented config.toml merge)" — no refuse/merge/backup semantics
  anywhere. The `.claude` path has an established non-destructive posture
  (move-aside + `.claude.bak`); the `.codex` path specifies none. Silently
  overwriting an adopter's AGENTS.md on first contact with the framework is
  the single fastest way to lose them. Mitigation: explicit collision policy
  per file (refuse-and-print-diff by default; `--force`/merge documented),
  plus a regression test installing onto a scratch repo that ALREADY has
  `AGENTS.md` + `.codex/config.toml` + a foreign `hooks.json`.

- **R-DX-03 — no liveness signal: "installed" ≠ "firing". Severity: HIGH.**
  Two facts compose badly: (1) non-managed hooks need per-user `/hooks` trust
  keyed to file hash — until granted (and again after EVERY upgrade that
  changes the hashed file), the hooks presumably simply don't run; (2)
  nothing in the plan verifies post-install that events actually fire. The
  CI positive-control replay proves adapter+hook logic against recorded
  envelopes; the Wave 2 live-fire proves it once, on the maintainer's
  machine. Neither proves anything about an adopter's session. So the most
  common adopter state after `install.sh --harness codex` will be: green
  install output, zero enforcement, no signal — the S254 fail-open-shim
  lesson recurring at the trust layer. Mitigation: a liveness probe as a
  Wave 5/6 deliverable — e.g. SessionStart boot breadcrumb asserted by a
  doctor/`ceo-info`-style check ("no SessionStart audit event in this
  session ⇒ hooks not trusted/not firing ⇒ print the exact `/hooks` steps"),
  and the installer's final output telling the operator to run that one
  command. Additionally: the plan asserts trust is "keyed to the hook file's
  hash" but never pins WHICH file (hooks.json entry? the `_python-hook.sh`
  shim? each `.py`?). The whole friction estimate diverges on the answer —
  if it keys on the shim only, upgrades of the 53 hook `.py` files re-prompt
  never (low friction, thin consent); if per-file, a typical upgrade
  re-prompts many times (consent fatigue → operators blind-click trust →
  the consent ceremony becomes noise). Determine it empirically in Wave 1
  fixtures work and record it in ADR-161; docs and the upgrade flow both
  depend on it.

- **R-DX-04 — silent adapter fallback composes with fail-open into silent
  ABSENT. Severity: HIGH.**
  `resolve_adapter()` returns `DEFAULT_ADAPTER` ("claude") on any unknown or
  empty `CEO_HOOK_ADAPTER`, deliberately silent (`_lib/contract.py:225-240`).
  In the codex-host world the template sets the env var explicitly — a typo
  in a hand-edited hooks.json, an env not propagated by Codex's hook exec, or
  a version-skewed installed `_lib` (target upgraded hooks but not the
  adapter) yields the CLAUDE adapter parsing a CODEX envelope →
  `NormalizedEvent(parse_error)` → fail-open allow → every rail ABSENT with
  zero operator signal. Silent fallback was a defensible policy when
  "unknown" meant "someone experimenting"; with a second production harness,
  explicitly-set-but-unresolvable must be LOUD. Mitigation: when the env var
  is set and the resolved adapter ≠ the requested one, emit an audit
  breadcrumb + have the SessionStart boot check go red (this pairs naturally
  with the R-DX-03 liveness probe); alternatively the host-mode `read_event`
  detects a cross-harness envelope shape and breadcrumbs it. Note
  `contract.py` is kernel-HARD-DENY surface — this lands only if
  `contract.py` is already in SENT-CX-A scope ("only if registry constants
  move"); decide at signing, do not widen silently.

- **R-DX-05 — docs promotion wording can outrun shipped capability, and no
  operator-facing version pin. Severity: MEDIUM.**
  Wave 7 promotes the codex row to "PRODUCTION gated on Wave 1-4 exit
  criteria" — but Wave 5 (installer) and Wave 6 (inverted pair-rail) land
  AFTER. If the docs sweep runs on schedule, an adopter reads "production on
  Codex" while there is no `--harness codex` path and no pair-rail teeth.
  Today's page honestly says "makes no compatibility claim today"
  (`docs/degradation-outside-claude-code.md:6-7`) — the upgrade must not
  overshoot in the other direction. Separately: everything is verified
  against codex-cli **0.139.0** while upstream ships 0.142.5; the §Risks
  section knows this, but no operator-facing surface is required to carry
  the pin. Mitigation: (a) stage the promotion per-rail — each matrix row
  states which wave made it true, and "PRODUCTION" for the installer path
  waits for Wave 5's exit criteria; (b) every Codex row carries "verified
  against codex-cli 0.139.0"; (c) the installer probes `codex --version` and
  prints a warning outside the verified range (the substrate watch-item is
  maintainer-side and nightly — adopters never see it; this is the
  adopter-side mirror, and it is cheap).

- **R-DX-06 — second-harness re-verification burden is detected but unowned.
  Severity: MEDIUM.**
  The Wave 0 watch-item is the right move and cheap to build —
  `check-substrate-watch.py` has a closed `_PROBE_ARGV` registry + ledger
  pattern that takes a `codex --version` probe naturally
  (`.claude/scripts/check-substrate-watch.py`, probe registry is
  code-defined by design). But the watch detects VERSION drift only. The
  actual per-release cost — re-record Wave 1 fixtures, re-run the Wave 2/6
  live-fires, re-test the interception surface, re-check trust-keying
  semantics — is manual Owner work on a bus-factor-1 project, against a CLI
  that moved 0.139→0.142 in weeks. And because CI replays FROZEN fixtures,
  CI stays green forever regardless of upstream drift: CI-green must never
  be read as "current Codex still speaks this shape". Mitigation: ADR-161
  carries a named per-bump re-verification checklist (exact artifact list +
  expected time-box), so each Codex release is a checklist run, not a
  research session; docs state the CI-green-≠-current-Codex boundary
  explicitly.

- **R-DX-07 — skills copy (OQ2-b) drifts on upgrade. Severity: MEDIUM.**
  Opt-in copy is the right call (symlinks: Windows, git-checkout, and
  unverified codex-cli link-following — correctly flagged). But copy creates
  a second tree that `upgrade.sh` replay will NOT touch: the target's
  `.claude/skills/` gets upgraded, `.codex/skills/` silently stays stale,
  and the Codex-side operator runs old skill content with no signal. Also,
  "recorded in the install manifest" (OQ2 rec) is currently impossible — the
  manifest generator's root-set is `.claude`-only (R-DX-01's same evidence).
  Mitigation: Wave 8 exit criteria add (a) manifest extension covering
  `.codex/skills/`, (b) upgrade re-sync (or an explicit doctor drift class
  "codex-skills stale"), (c) the `--with-codex-skills` value round-trips
  through the recorded install request like `--harness` does.

## Must-fix (blocking)

1. **Wave 5 lifecycle symmetry (R-DX-01):** manifest + uninstall + backup +
   restore coverage for every emitted `.codex/**` path, the root operator
   `AGENTS.md`, AND the Wave 6 git pre-push hook, specified against the
   landed PLAN-153 Wave B interface. Uninstall that leaves enforcement
   residue (live hooks, push gates) is not symmetric.
2. **Collision policy for pre-existing adopter files (R-DX-02):**
   refuse/merge/backup semantics per emitted file, plus a scratch-repo
   regression test where `AGENTS.md`, `.codex/config.toml`, and a foreign
   `hooks.json` already exist. Never clobber by default.
3. **Post-install liveness probe (R-DX-03):** a one-command check (doctor or
   `ceo-info`-class) that proves hooks are firing in a real Codex session
   (SessionStart breadcrumb assert), printed as the installer's final
   instruction; plus empirically pin WHICH file the `/hooks` trust hash keys
   on and record it in ADR-161 — the upgrade-UX and the consent-fatigue
   posture both depend on the answer.
4. **Loud failure for explicitly-set adapter (R-DX-04):** when
   `CEO_HOOK_ADAPTER` is set and does not resolve to the requested adapter
   (or the host adapter receives a cross-harness envelope), emit an audit
   breadcrumb and fail the SessionStart boot check red. Scope decision
   (contract.py vs adapter-side detection) made at SENT-CX-A signing, not
   discovered mid-wave.
5. **Docs promotion gating + operator-visible version pin (R-DX-05):**
   per-rail promotion tied to the wave that made each claim true; every
   Codex matrix row carries "verified against codex-cli 0.139.0"; installer
   warns when `codex --version` is outside the verified range.

## Nice-to-have (advisory)

1. **Commit-posture doc for the `.codex` bundle in target repos.** If
   `hooks.json` is committed, every teammate's clone re-prompts for trust on
   first session — that is Codex's intended team model, but adopters will
   hit it as a surprise. One paragraph in the Wave 7 docs ("what your
   teammates will see on first run") pre-empts the issue reports.
2. **Fold the phantom-test pointer into the Wave 7 adapters.md fix:** the
   gemini row cites `test_adapters_parity.py`, which does not exist under
   that name (the plan itself corrects the research pointer at its line
   66-70) — reconcile the doc's test citations to the real files in the same
   sweep that fixes the gemini/openai/local registry drift.
3. **OQ3 should also state operator-visible latency/cost expectations.** A
   Stop-hook that `decision:block`-loops until a `claude -p` review lands is
   a synchronous wait the operator experiences on every L3 session close;
   docs should say what "normal" looks like (seconds vs minutes, token
   ceiling) so people don't kill the session — which is exactly the
   abandonment path the PARTIAL rail already worries about.
4. **Name and document the Wave 4-C `codex exec` wrapper as a first-class
   command** (discoverable name, `--help`, mentioned in INSTALL docs), not a
   loose script — headless CI usage on the adopter side will find it only if
   it is documented where `codex exec` users look.
5. **AGENTS.md size test must assert POST-substitution size.** The Wave 2
   check tests the template at ≤32768 bytes; placeholder substitution at
   install time can only grow it. Assert the rendered artifact on the
   scratch-repo install, not (only) the template.

## Unseen by the original plan

1. **The Wave 6 git pre-push hook is a third install surface with no
   lifecycle story at all** — not in Wave 5's emitted-file list, not in any
   uninstall/manifest line, and it survives an uninstall as active
   enforcement on a repo that no longer has the framework (folded into
   R-DX-01, but it deserves its own named line in the plan text because it
   lives under `.git/`, which no manifest walk will ever reach naturally).
2. **Trust-hash keying ambiguity** (which file the `/hooks` trust actually
   hashes) — the plan treats "re-trust on every hook edit" as understood,
   but the operational cost ranges from ~zero to ~per-file-per-upgrade
   depending on the answer, and the security meaning of "trusted" inverts
   (trusting a shim whose Python payload changes freely is consent theater).
   This is a Wave 1 empirical question, not a docs question.
3. **Version-skew between an installed target's `_lib` and its hooks.json**
   after partial upgrades — the R-DX-04 fallback path is reachable not just
   by typo but by any upgrade flow that updates one side first; the
   `upgrade.sh` replay ordering for the codex surface should update adapter
   + registration atomically or tolerate one-sided states loudly.

## What I would NOT change

- **Adapter-first sequencing and the no-hook-forks rule.** One enforcement
  kernel, two registrations is the only maintainable shape for a
  bus-factor-1 project; a Codex-side fork of 53 hooks would be the real
  maintenance catastrophe, and this plan correctly refuses it.
- **OQ1's recommended default** — `/hooks` guided consent as default,
  `--managed-hooks` as explicit enterprise opt-in. Consent-first matches the
  human-gated ethos; an installer that silently writes non-disableable
  policy would betray it. Keep it, with the R-DX-03 liveness probe as the
  companion that makes consent-first survivable.
- **Behavioral positive-control as the certifying artifact** (planted
  violation → assert deny, in CI). Config-file existence proves nothing;
  this repo has paid for that lesson twice.
- **The hard install.sh sequencing rule vs PLAN-153** and SENT-CX-C
  anchor-sha on post-PLAN-153 main — two sentinels racing one guarded file
  is exactly what the S258 scope assert exists to prevent.
- **Wave 8's zero-new-files-in-this-repo scope guard.** Install-time
  copy only, counts tolerance=0 untouched, no content fork. Correct — a
  forked skill tree would double contamination review per file.
- **The honesty vocabulary discipline** — ENFORCED/ADVISORY/ABSENT with
  residuals in the same breath, no speed claims, and the direction-neutral
  same-vendor caveat. This is the product; the Codex port must not dilute it.
