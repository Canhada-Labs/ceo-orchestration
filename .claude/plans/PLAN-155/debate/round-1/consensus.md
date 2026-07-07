---
plan: PLAN-155
round: 1
artifact: consensus
verdict: ADJUST_PROCEED
tally: "3x ADJUST_PROCEED / 0 VETO / 0 PROCEED"
created_at: 2026-07-07
positions:
  - devops-dx.md
  - qa-architect.md
  - security-engineer.md
---

# PLAN-155 — Round 1 Consensus

## Tally

| Position | Archetype | Verdict (as written) | Normalized |
|---|---|---|---|
| P1 | security-engineer | ADJUST | ADJUST_PROCEED |
| P2 | qa-architect | ADJUST_PROCEED | ADJUST_PROCEED |
| P3 | devops-dx | ADJUST_PROCEED | ADJUST_PROCEED |

**3× ADJUST_PROCEED, 0 VETO, 0 PROCEED.**
(P1's bare "ADJUST" is normalized to ADJUST_PROCEED under the house
PROCEED / ADJUST_PROCEED / VETO vocabulary; the position body contains no
veto language and closes with must-fixes + advisories, the ADJUST_PROCEED
shape.)

## Consensus verdict

**ADJUST_PROCEED.** No veto. All three seats endorse the plan's core
thesis — adapter-first, one enforcement kernel with two registrations, no
hook forks, behavioral positive-control as the certifying artifact, the
honesty matrix with residuals named inside each claim, consent-first OQ1
default, and the hard install.sh sequencing rule vs PLAN-153. All three
independently converged on the same top failure class: the **S254
silent-disarm pattern recurring cross-vendor** — (a) `CEO_HOOK_ADAPTER`
has zero consumers in the enforcement hooks today (R-QA-01: all four
ENFORCED hooks hard-import the claude adapter), (b) `resolve_adapter()`
silent fallback composes with fail-open-on-infrastructure into
every-rail-ABSENT with zero signal (R-SEC-01 / R-DX-04), and (c) nothing
distinguishes "installed" from "armed" post-install (R-SEC-05 / R-DX-03).
The three positions attack the same class at three layers (wiring, runtime
coherence, operator liveness); all three layers are binding.

## Merged adjustment index

Binding adjustments must ALL be applied into the plan text by the amender
before the draft→reviewed flip (S259/S261 precedent, Owner delegation).
Advisory adjustments are recorded for execution-time discretion.

### Binding (A1–A15)

| ID | Adjustment (one line) | Source(s) | Lands in |
|---|---|---|---|
| A1 | Wave 0 dispatch-surface inventory (every `from _lib.adapters import claude` site in `.claude/hooks/`) + Owner-ratified seam design (per-entrypoint `load_adapter()` migration OR single shared ingress seam); sentinel scope (SENT-CX-A or new SENT-CX-A2) enumerates the touched hook files explicitly — no execution-time widening. | R-QA-01 (CRITICAL) | Wave 0 + sentinel scope |
| A2 | Host/adapter coherence gate: explicitly-set-but-unresolvable `CEO_HOOK_ADAPTER`, or a recognizably cross-harness envelope under the resolved adapter, is an INPUT/mis-configuration failure per the PLAN-152 C4 taxonomy → fail-CLOSED + audit breadcrumb + SessionStart boot check RED; Wave 6 breadcrumb/chain assertions defined RED-on-absence (vacuous green is the failure mode); contract.py-vs-adapter-side scope decided at SENT-CX-A signing, not mid-wave. | R-SEC-01 + R-DX-04 | Wave 1/6 exit criteria + SENT-CX-A |
| A3 | Positive controls run as SUBPROCESSES on the byte-identical command line shipped in `templates/codex/hooks.json` (shim + argv + env), stdin = recorded envelope, assert `permissionDecision` AND deny-reason class; add per violation class a negative control (benign→allow) and a malformed-envelope control (C4 split); the T1/T2/T3 hermetic posture is recorded as normative in ADR-161, including the sentence "CI certifies fixture-replay against a recorded wire; only local live-fire certifies the real binary, per pinned version." | R-QA-02 (CRITICAL) | Wave 1 + ADR-161 + validate.yml same-commit |
| A4 | Kill the vacuous green: parameterize the golden round-trip over ALL `KNOWN_ADAPTERS`; minimum-fixture-count assertion per adapter (`.gitkeep`-only dir must FAIL); codex `out/` goldens (allow, deny-with-reason, additionalContext passthrough); extend the drift detector to scan codex host-mode `NormalizedEvent` call-sites. | R-QA-03 (CRITICAL) | Wave 1, same commit as host-mode code |
| A5 | Empirical Codex failure-semantics matrix recorded in Wave 1 BEFORE ADR-161 normativity: hook timeout / non-zero exit / malformed-or-foreign JSON / `{}` output, PLUS a live Stop-block enforcement transcript; pair-rail matrix row marked "PARTIAL, pending Stop-block verification" until the transcript exists; archive the SubagentStart non-enforcement transcript under `PLAN-155/artifacts/`, cite it from ADR-161, and add it to the substrate-watch per-bump re-test list. | R-SEC-02 + R-QA-08(a) | Wave 1 + ADR-161 |
| A6 | Trust-hash keying empirically pinned on 0.139 (edit shim → re-prompt? edit a hook `.py` → re-prompt?) during Wave 1/2; ADR-161 gets a normative "what /hooks trust does and does not attest" paragraph; OQ1 is ratified only AFTER this fact is in front of the Owner — the friction estimate and the consent-security meaning both invert on the answer. | R-SEC-04 + R-DX-03(b) | Wave 1/2 + ADR-161 + OQ1 |
| A7 | Post-install liveness/arming verification: a one-command doctor/`ceo-info`-class check (SessionStart audit-breadcrumb assert + benign behavioral probe) reporting ARMED / NOT-ARMED-(untrusted) / BROKEN, printed as the installer's final instruction; installer output states loudly that NOTHING is enforced until `/hooks` trust is granted; added to Wave 5 exit criteria and plan Success criteria. | R-SEC-05 + R-DX-03(a) | Wave 5/6 + Success criteria |
| A8 | The rail's own kill switch enters the guarded surface: `.codex/hooks.json`, `config.toml [hooks]`, `rules/ceo.rules`, `requirements.toml`, and the operator `AGENTS.md` added to the PreToolUse deny/canonical matcher AND the boot-time hash tripwire; ADR-161 conditions the "managed = non-disableable" claim on requirements.toml placement (admin/org scope, not agent-writable). | R-SEC-03 | Wave 2/3 + ADR-161 |
| A9 | Lifecycle symmetry: manifest + uninstall + backup + restore coverage for EVERY emitted path — `.codex/**`, root operator `AGENTS.md`, and the Wave 6 git pre-push hook (named in plan text as a third install surface under `.git/`, which no manifest walk reaches naturally) — specified against the LANDED PLAN-153 Wave B interface; uninstall that leaves enforcement residue is not symmetric. | R-DX-01 | Wave 5/6 exit criteria |
| A10 | Collision policy for pre-existing adopter files: refuse/merge/backup semantics per emitted file (refuse-and-print-diff default; `--force`/merge documented; never clobber), plus a scratch-repo regression where `AGENTS.md`, `.codex/config.toml`, and a foreign `hooks.json` already exist (folds in as an added case of the A11 matrix). | R-DX-02 | Wave 5 |
| A11 | Enumerated installer test matrix wired into validate.yml same-commit: (1) no-flag byte-identical via `diff -r` vs pre-plan golden; (2) `--harness codex` with every registered command path resolving/executable at real runtime resolution; (3) `--dry-run` zero writes; (4) unknown harness → usage error, no partial writes; (5) idempotent re-run; (6) `--harness` round-trips through the LANDED manifest into upgrade replay; (7) RENDERED operator `AGENTS.md` ≤ 32768 bytes (post-substitution, not template-only); (8) Wave 8 skills in manifest/doctor/uninstall if landed; (9) the A10 collision case. | R-QA-05 + devops NTH-5 | Wave 5 + validate.yml |
| A12 | Fixture↔pin mechanical coupling: every recorded fixture carries `_meta.codex_cli_version`; a unit test asserts it ∈ pin range (pin bump goes RED until re-record or explicit waiver); fixtures follow the PIN — bump the pin first via the ADR-111 ceremony, then re-record; the Wave 0 watch-item covers the codex-cli release feed AND the hooks/config/rules doc pages; ADR-161 carries the named per-bump re-verification checklist (exact artifact list + time-box) so each Codex release is a checklist run, and docs state CI-green ≠ current-Codex. | R-QA-04 + R-DX-06 | Wave 0/1 + ADR-161 |
| A13 | Audit-chain replay test runs under `TestEnvContext` with a test-scoped HMAC key (never real `$HOME`); the Wave 4-B distinct turn-ended backstop action name is asserted by pytest, with per-tool and turn-level appends countable separately from the same log slice. | R-QA-06 | Wave 4 |
| A14 | Characterization tests lock the pair-rail reviewer-egress surface (`parse_verdict*`, `make_invoke_command*`, `parse_usage_from_codex_stdout`) with golden in/out pairs BEFORE the Wave 1 host-mode edit; they must pass unchanged on both sides of that commit. | R-QA-07 | pre-Wave-1 |
| A15 | Docs promotion staged per-rail, each matrix row tied to the wave that made it true (installer-path "PRODUCTION" waits for Wave 5 exit criteria); every Codex row carries "verified against codex-cli 0.139.0"; installer probes `codex --version`, warns outside the verified range, and records the detected version in the install manifest. | R-DX-05 + R-SEC-11 | Wave 5/7 |

### Advisory (A16–A26)

| ID | Adjustment (one line) | Source(s) |
|---|---|---|
| A16 | Spawn-rail matrix row names the inherited `^Bash$` interception residual — the ADVISORY rail must not borrow an ENFORCED label it doesn't own. | R-SEC-06 |
| A17 | AGENTS.md hygiene: binding governance summary at TOP of template; boot-time warn on size ≥ cap and on a non-root AGENTS.md shadowing the operator file (nearest-wins); template comments state the shadowing rule; `additionalContext` payloads static or redacted (ingress-scan precedent). | R-SEC-07 |
| A18 | Wave 4-C names the wrapper-bypass residual (direct `codex exec` skips the bracketing); the wrapper ships as a first-class documented command (discoverable name, `--help`, INSTALL docs). | R-SEC-08 + devops NTH-4 |
| A19 | Canonical-edit matrix row names the MCP arg-shape residual (foreign arg names invisible to the normalizer) alongside the shell-escape class. | R-SEC-09 |
| A20 | ADR-161 paragraph on reviewer-unavailable posture: missing/broken `claude` CLI → Stop gate opens per SPEC §4 fail-open-on-infrastructure; pre-push/CI record check is the guaranteed floor; verdict-PARSE failures stay fail-closed-to-Owner (V2 doctrine). | R-SEC-10 |
| A21 | Citation hygiene in one sweep: reconcile the phantom `test_adapters_parity.py` pointer and the gemini/openai/local registry drift in Wave 7; reword Wave 1's check to distinguish the parity gate (golden + drift) from the ADR-040 live-adapter regression suite (different subsystem). | devops NTH-2 + R-QA-08(b) |
| A22 | Wave 7 docs carry a commit-posture paragraph: what teammates see on first run when `.codex/hooks.json` is committed (per-user trust re-prompt is Codex's intended team model — pre-empt the surprise reports). | devops NTH-1 |
| A23 | OQ3 ratification includes operator-visible latency/cost expectations for the Stop-hook review wait (seconds vs minutes, token ceiling) so operators don't kill the session. | devops NTH-3 |
| A24 | Conditional on Wave 8: `.codex/skills/` copy gets an upgrade story — manifest extension, upgrade re-sync or a doctor "codex-skills stale" drift class, and `--with-codex-skills` round-trips through the recorded install request. | R-DX-07 |
| A25 | ADR-161 defines parity for the asymmetric adapter: strict normalized-INPUT equality across adapters (same `normalized/<scenario>.json`), per-harness OUTPUT wire contracts — following the golden suite's existing docstring split. | R-QA-09 |
| A26 | Adopt the versioned-fixture mechanism now (`_meta` field as the single mechanism, or versioned dirs) so the first pin bump doesn't invent layout under pressure. | R-QA-04 (advisory tail) |

## Cross-position convergences (for the record)

- **S254-class silent disarm, three layers, three seats:** R-QA-01 (wiring:
  env var has no consumers) + R-SEC-01/R-DX-04 (runtime: silent fallback ×
  fail-open) + R-SEC-05/R-DX-03 (operator: installed ≠ armed). A1, A2, A7
  together close the class; any one alone leaves a silent-ABSENT path open.
- **Trust-hash keying** flagged independently by P1 (security meaning of
  consent) and P3 (friction/consent-fatigue) — same empirical question,
  merged as A6, and both agree OQ1 waits for the answer.
- **Version pin/drift** flagged by all three (R-QA-04, R-DX-05/06,
  R-SEC-11) — merged as A12 (mechanics) + A15 (operator-visible surface).
- **Unanimous do-not-change list:** adapter-first sequencing / no hook
  forks; consent-first OQ1 default; behavioral positive-control as the
  certifying artifact; ENFORCED/ADVISORY/ABSENT vocabulary with residuals
  in-claim; ADVISORY rails stay ADVISORY (no promotion-by-debate); the
  install.sh sequencing rule vs PLAN-153; C4 fail-open-infrastructure /
  fail-closed-input carried over unchanged.

## Anonymization map note

Positions were authored to disk under archetype filenames
(`security-engineer.md`, `qa-architect.md`, `devops-dx.md`) — no
pseudonymous stage was used this round, so the P1/P2/P3 labels in the
tally are a disclosed, order-arbitrary map (P1=security-engineer,
P2=qa-architect, P3=devops-dx), not a blinding layer. Each position was
drafted independently from its archetype lens with file:line evidence;
overlap noted above is convergent finding, not cross-copying.

## Disposition

ADJUST_PROCEED with A1–A15 binding. Next step per house doctrine: the
amender applies ALL fifteen binding adjustments into the PLAN-155 text
(waves, exit criteria, sentinel scopes, OQ gating, Success criteria),
records A16–A26 as advisory in the plan's debate section, then flips the
plan `draft` → `reviewed`. Sentinel-scope consequences (A1, A2, A8) must
be reflected in Wave 0 sentinel allocation BEFORE signing — no
execution-time scope widening.
