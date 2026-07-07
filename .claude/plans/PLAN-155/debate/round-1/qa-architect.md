---
plan: PLAN-155
round: 1
archetype: qa-architect
skill: testing-strategy
verdict: ADJUST_PROCEED
created_at: 2026-07-07
---

## Verdict

ADJUST_PROCEED — the plan's certification doctrine is the right one
(behavioral positive-control over static existence, PLAN-153 consensus #2),
and the hermetic question the QA seat was asked — *can CI replay Codex-side
hooks without a Codex binary?* — has a clean YES, because the entire hook
surface is stdin/stdout JSON: the binary is needed only to RECORD fixtures
and for local live smoke, never to REPLAY them. But two findings are
critical. First, the plan's central mechanism has **no consumer today**:
`CEO_HOOK_ADAPTER` is dispatched by `contract.resolve_adapter()`
(`_lib/contract.py:222`) which **zero hook entrypoints call** — all four
ENFORCED hooks hard-import the claude adapter
(`check_canonical_edit.py:1081`, `check_bash_safety.py:169`,
`check_plan_edit.py:92`, `check_arbitration_kernel.py:448`:
`from _lib.adapters import claude as _claude_adapter`). Setting the env var
in `.codex/hooks.json` as Wave 2 specifies would change nothing; under
Codex the claude parser would mis-read the envelope and the rails would
fail open to ALLOW — the exact S254 dead-gate class (gate wired, tests
green, enforcement dead) this framework already paid a P0 for. Second, the
Wave 1 exit gate as literally written is **satisfiable vacuously today**:
the codex fixture dirs contain only `.gitkeep`
(`hooks/tests/fixtures/adapters/codex/{in,out}/.gitkeep`) and
`test_adapter_golden.py`'s only codex assertions are directory-existence
(`test_adapter_golden.py:69-85`); the round-trip and write-decision tests
are claude-only (`:99`, `:135-158`). Both are fixable in plan text and
Wave-0 scope before execution; neither invalidates the thesis. Fix the
binding adjustments below and this moves to `reviewed` from the QA seat.

## Summary (≤ 3 bullets)

- **What it does:** teaches `_lib/adapters/codex.py` host mode (parse Codex
  hook envelopes, emit `hookSpecificOutput.permissionDecision`), ships
  `.codex/` registration templates + execpolicy backstop, extends the audit
  chain and installer (`--harness codex`), inverts the pair-rail, and
  rewrites the docs to an honest per-rail matrix.
- **Strong:** the capability matrix names residuals as part of each claim;
  live-fire evidence is explicitly archived, not asserted; the
  staged-vs-landed sequencing rule vs PLAN-153 is exactly the discipline
  the S258 scope assert exists to enforce.
- **Weak:** the plan certifies the *adapter* and the *hook logic* but, as
  drafted, not the *wiring between them* — and wiring is where this
  framework's only confirmed dead-gate P0 lived (S254: `settings.json:201`
  relative path → shim fail-open `{}` with every unit test green). The
  positive-control design must cross the process boundary or it proves the
  wrong thing.

## The hermetic test posture (direct answer to the QA charge)

Three tiers, each honestly labeled — this should land in the plan and in
ADR-161 as normative:

- **T1 — hermetic CI (every push, no codex binary, no license).** Recorded
  Codex-wire envelopes (captured once per pinned CLI version from the live
  local binary) replayed two ways: (a) adapter-unit round-trip via the
  golden suite (parse → NormalizedEvent → emit); (b) **subprocess**
  positive/negative controls — spawn the hook exactly as the shipped
  `.codex/hooks.json` command line does (`_python-hook.sh` shim, real argv,
  `CEO_HOOK_ADAPTER=codex` in env), pipe the recorded envelope to stdin,
  assert the stdout JSON's `permissionDecision`. CI already runs the whole
  `hooks/tests/` tree (`validate.yml:298-299`) and installs only
  pytest/PyYAML/xdist (`validate.yml:286-289`); no workflow installs codex
  (grep: only `mcp-smoke.yml` tool-name strings and `release.yml:556-618`
  pin-file assertions). This tier needs nothing added to CI images.
- **T2 — local live smoke (per pinned version, transcript archived).** Real
  0.139 session live-fire (Wave 2 denied-edit, Wave 6 Stop-block), gated by
  `shutil.which("codex")` + pin-range check, `pytest.mark`-skipped in CI
  **with a reason string that names the local runbook** — the skip must be
  visible, never silent, or T2 becomes a CI-dark surface.
- **T3 — release gate.** `release.yml` step-15 already asserts the codex
  pin (`codex-cli-pin.txt`, `codex-cli-binary-sha256.txt`); extend the
  verdict envelope to record which fixture-set version the release was
  certified against.

The honesty sentence that must survive into Wave 7 docs: **CI certifies
fixture-replay against a recorded wire; only local live-fire certifies the
real binary, per pinned version.** "Positive-control replay in CI" must
never be readable as "CI tested against real Codex."

## Risks

- **R-QA-01 — `CEO_HOOK_ADAPTER` has zero consumers in the enforcement
  hooks; SENT-CX-A scope cannot deliver the plan's own Approach**
  Severity: **CRITICAL** · Binding
  Description: Approach says "the Codex-side registration calls the SAME
  Python hooks with `CEO_HOOK_ADAPTER=codex`" — but no hook calls
  `contract.load_adapter()`/`resolve_adapter()` (grep over
  `.claude/hooks/*.py`: zero hits); every wire-speaking hook hard-imports
  claude (`check_canonical_edit.py:1081`, `check_bash_safety.py:169`,
  `check_plan_edit.py:92`, `check_arbitration_kernel.py:448`, plus ~20
  more). Under Codex the claude parser receives a Codex envelope: at best
  `parse_error` → fail-open allow, at worst partial mis-parse — every
  ENFORCED row in the matrix silently becomes ABSENT. SENT-CX-A's scope
  (`codex.py`, `adapters/__init__.py`, `contract.py`) does not include the
  hook entrypoints that must move to dynamic dispatch; discovering that at
  execution time is the exact sentinel-widening anti-pattern Wave 0 exists
  to prevent.
  Mitigation: Wave 0 adds a **dispatch-surface inventory** task (enumerate
  every `from _lib.adapters import claude` site in `.claude/hooks/`), and
  the Owner ratifies ONE of two designs at signing: (a) migrate each
  entrypoint to `contract.load_adapter()` — SENT-CX-A (or a new SENT-CX-A2)
  scope enumerates those hook files explicitly; or (b) a single-seam
  design — one shared ingress/egress helper the hooks already route
  through, so only that module changes. Either way the R-QA-02 subprocess
  controls are what prove the chosen seam actually dispatches.

- **R-QA-02 — positive-control replay must cross the process boundary on
  the real registered command line**
  Severity: **CRITICAL** · Binding
  Description: Wave 1's "replayed through the adapter into the real hooks
  in CI" permits an in-process reading (import module, call function) that
  would have stayed green through S254's dead gate. In-process replay
  cannot catch: shim path resolution bugs, env-var loss between
  registration and process, import failure → fail-open `{}`, wrong argv in
  the template. House precedent is explicit: same-process evidence doesn't
  prove cross-process behavior (the flock lesson), and a harness that
  accepts any green as GREEN masks vacuous passes.
  Mitigation: each of the 3 planted violations runs as a **subprocess**
  using the byte-identical command string shipped in
  `templates/codex/hooks.json` (shim + hook + env), stdin = recorded
  envelope, assert `hookSpecificOutput.permissionDecision == "deny"` AND
  the deny-reason class. Add per violation class: one **negative control**
  (benign envelope → `allow`, catching fail-closed regressions) and one
  **malformed-envelope control** asserting the PLAN-152 C4 split under the
  new parser — infrastructure failure fails open, unparseable *input* at
  the security matchers fails closed. Wire into `validate.yml` same-commit
  (plan already commits to this — hold it).

- **R-QA-03 — vacuous-green: the existing golden suite passes today with
  empty codex fixtures**
  Severity: **CRITICAL** · Binding
  Description: `fixtures/adapters/codex/in/` and `out/` hold only
  `.gitkeep`; `test_known_adapters_have_{in,out}_fixtures` assert only that
  the directories exist (`test_adapter_golden.py:69-85`), and the only
  round-trip + write-decision tests are claude-specific (`:99`, `:135`,
  `:145`). The Wave 1 check "golden suite green under
  `CEO_HOOK_ADAPTER=codex`" is therefore already true with zero codex
  behavior tested — the exit gate cannot distinguish done from not-started.
  Mitigation: same commit as host-mode code: (a) parameterize the
  round-trip test over ALL `KNOWN_ADAPTERS` (`contract.py:216`); (b) add a
  **minimum-scenario-count assertion** per adapter (≥ the 6 events Wave 1
  names; a `.gitkeep`-only dir must FAIL); (c) codex `out/` goldens for
  allow, deny-with-reason, and `additionalContext` passthrough; (d) extend
  the drift detector — today hardwired to claude
  (`test_adapter_drift_detector.py:40`, class at `:232`) — to statically
  scan `codex.py` host-mode `NormalizedEvent(...)` call-sites for
  non-canonical fields.

- **R-QA-04 — version-drift (0.139 pinned vs 0.142.5 upstream): fixtures
  and the pin must be mechanically coupled**
  Severity: **MAJOR** · Binding
  Description: `.claude/governance/codex-cli-pin.txt` pins
  `>=0.128.0,<0.140.0`, asserted at release step-15 and
  `pair-rail-gate.sh` preflight. PLAN-155 adds a second artifact class
  coupled to that pin (host-adapter wire fixtures) but no mechanism binds
  them — a future pin bump to 0.142.x with stale 0.139 fixtures is
  precisely the PLAN-142 drift class (`codex_invoke.py` vs 0.139
  empty-stdout), now on the enforcement path instead of the review path.
  `check-substrate-watch.py` has zero codex coverage today (grep confirms),
  so nothing alerts.
  Mitigation: (a) every recorded fixture carries a
  `_meta.codex_cli_version`; a unit test asserts every codex fixture's
  recorded version is inside the pin range — a pin bump goes RED until
  fixtures are re-recorded or explicitly waived; (b) fixtures follow the
  PIN, not upstream: do not record on 0.142.5 while the pin says <0.140.0
  — if the Owner wants 0.142.x, bump the pin first via the ADR-111
  ceremony, then re-record (the plan's How-to-continue already gestures at
  this; make it a test, not a memo); (c) the Wave 0 watch-item must cover
  BOTH the codex-cli release feed and the hooks/config/rules doc pages,
  and its alert text must name the re-record runbook. Advisory: adopt a
  versioned fixture layout (`codex/in/v0139/` or the `_meta` field as the
  single mechanism) now, so the first bump doesn't invent layout under
  pressure.

- **R-QA-05 — `install.sh --harness codex` needs an explicit test matrix;
  current installer tests are shell scripts and are not in validate.yml**
  Severity: **MAJOR** · Binding
  Description: on-disk installer test infra is
  `scripts/tests/{smoke-install.sh,test-doctor.sh,test-install-sandbox-merge.sh,test_install_baseline_manifest.sh}`
  — plain bash, not the "bats/pytest suite" Wave 5 prose implies, and no
  installer test job exists in `validate.yml` today. "Default path
  byte-identical" and "dry-run previews" are claims that rot instantly
  without an enumerated matrix.
  Mitigation — the matrix, each case a scratch repo: (1) no-flag run:
  `diff -r` the produced tree against a pre-plan golden — byte-identical is
  asserted, not eyeballed; (2) `--harness codex`: bundle exists AND every
  command path registered in the emitted `hooks.json` resolves and is
  executable at the harness's real runtime resolution (the PLAN-153 Wave E
  dirname/cwd lesson as an assertion); (3) `--dry-run` writes nothing
  (empty `git status --porcelain` after); (4) unknown harness
  (`--harness gemini`) → usage error, non-zero exit, zero partial writes;
  (5) idempotent re-run; (6) `--harness` value round-trips through the
  PLAN-153 Wave B manifest into `upgrade.sh` replay — tested against the
  LANDED interface only, per the plan's own staged-vs-landed rule; (7)
  operator `AGENTS.md` ≤ 32768 bytes asserted in the installer test as
  well as the template unit test (installers concatenate); (8) if Wave 8
  lands: skills recorded in manifest, visible to doctor, removed by
  uninstall. All wired into `validate.yml` same-commit. Advisory: the
  interactive `/hooks` trust flow is untestable hermetically — golden-test
  the *printed guidance text* and mark the interactive path T2/local-only.

- **R-QA-06 — audit-chain replay determinism + the Wave 4-B distinct
  action must be asserted, not narrated**
  Severity: **MAJOR** · Binding
  Description: Wave 4's CI replay (recorded session →
  `audit-verify-chain.py` exit 0) verifies an HMAC chain — under a real
  `$HOME` key this is non-hermetic and flaky-by-environment; and the
  "distinct action name" for turn-ended backstop appends (Wave 4-B, echoed
  in §Risks) is exit-criteria prose with no named assertion, so
  completeness analysis can silently lie exactly as the risk section
  fears.
  Mitigation: the replay test runs under `TestEnvContext` (house rule:
  never the real `$HOME`/`$CLAUDE_PROJECT_DIR`) with a test-scoped HMAC
  key; a pytest assertion checks the backstop events carry the distinct
  action string AND that per-tool and turn-level appends are countable
  separately from the same log slice (the completeness-analysis query is
  itself the test).

- **R-QA-07 — dual-role `codex.py`: pin the untouched half with tests
  before touching the module**
  Severity: **MAJOR** · Binding
  Description: `check_pair_rail.py:829,:874` consumes
  `codex.parse_verdict_strict` from the same module Wave 1 rewrites;
  `write_decision` currently emits the Claude shape by documented contract
  (`codex.py:247-263`). "Helpers untouched by contract" is a promise, not
  a gate.
  Mitigation: BEFORE the host-mode edit lands, a characterization test
  locks the reviewer-egress surface (`parse_verdict*`,
  `make_invoke_command*`, `parse_usage_from_codex_stdout`) with golden
  in/out pairs; it must pass unchanged on both sides of the Wave 1 commit.
  Cheap, and it converts the §Risks mitigation into something CI can veto.

- **R-QA-08 — the ADVISORY labels need pinned negative evidence, and the
  live-adapter suite citation is a different subsystem**
  Severity: **MINOR** · Advisory
  Description: (a) "SubagentStart `continue:false` parsed but does NOT
  stop the subagent (verified 0.139)" is a session claim; the matrix row
  and the §Deferred promotion trigger both hang off it. (b) The Wave 1
  check cites `.claude/hooks/tests/adapters/` — but
  `adapters/live/test_adapters.py` is the ADR-040 LLM-API live-adapter
  suite (mock `http.server` for Claude/Gemini/OpenAI/Local), not
  hook-envelope parity; fine to keep green, misleading as a parity gate.
  Mitigation: (a) archive the SubagentStart non-enforcement transcript
  under `PLAN-155/artifacts/` and cite it from ADR-161; add it to the
  substrate-watch re-test list so the ADVISORY→ENFORCED promotion trigger
  in §Deferred is re-checked per CLI bump from evidence, not memory.
  (b) One-line rewording in Wave 1's check distinguishing the parity gate
  (golden + drift) from the regression gate (live-adapter suite).

- **R-QA-09 — parity-test extension scope: name what "parity" means for a
  deliberately asymmetric adapter**
  Severity: **MINOR** · Advisory
  Description: host-mode codex output (`hookSpecificOutput.*`) is
  intentionally NOT byte-equal to claude output, so "parity" can no longer
  mean identical `out/` fixtures across adapters — but the normalized side
  MUST stay identical. Left implicit, the next contributor either
  force-equalizes outputs (wrong) or drops normalized equality (worse).
  Mitigation: state the invariant in ADR-161 and encode it: for every
  shared scenario, `read_event` output round-trips to the SAME
  `normalized/<scenario>.json` across adapters (input parity = strict);
  `out/` fixtures are per-adapter wire shapes validated per-adapter
  (output parity = per-harness contract). The golden suite's docstring
  contract (`test_adapter_golden.py:22-29`) already anticipates exactly
  this split — make the codex extension follow it explicitly.

## Adjustments requested (for consensus merge)

| ID | Binding? | One-line ask |
|---|---|---|
| R-QA-01 | **Binding** | Wave 0: dispatch-surface inventory + Owner-ratified seam design; sentinel scope covers the hook entrypoints (or the single seam) that make `CEO_HOOK_ADAPTER` actually dispatch. |
| R-QA-02 | **Binding** | Positive controls run as subprocesses on the shipped `hooks.json` command line; add negative + malformed-envelope controls asserting the C4 fail-open/fail-closed split. |
| R-QA-03 | **Binding** | Kill the vacuous green: parameterized round-trip over KNOWN_ADAPTERS + minimum-fixture-count assertion + codex out-goldens + drift-detector extension. |
| R-QA-04 | **Binding** | Fixture `_meta.codex_cli_version` asserted ∈ pin range; fixtures follow the pin; watch-item covers release feed + doc pages with a named re-record runbook. |
| R-QA-05 | **Binding** | Enumerated 8-case installer matrix (incl. byte-identical via `diff -r`, dry-run zero-writes, unknown-harness error, upgrade round-trip vs LANDED interface), CI-wired same-commit. |
| R-QA-06 | **Binding** | Audit replay under `TestEnvContext` with test HMAC key; distinct backstop action asserted by pytest, not prose. |
| R-QA-07 | **Binding** | Characterization tests lock the pair-rail reviewer-egress helpers before the Wave 1 edit. |
| R-QA-08 | Advisory | Archive SubagentStart non-enforcement transcript + cite from ADR-161; reword the live-suite citation in Wave 1's check. |
| R-QA-09 | Advisory | ADR-161 defines parity = strict normalized-input equality, per-harness output contracts. |

## Evidence index

- Hard-wired adapter imports: `check_canonical_edit.py:1081`,
  `check_bash_safety.py:169`, `check_plan_edit.py:92`,
  `check_arbitration_kernel.py:448`; zero `load_adapter` call-sites in
  `.claude/hooks/*.py`.
- Dispatch machinery unused by hooks: `_lib/contract.py:216-222`
  (`KNOWN_ADAPTERS`, `ADAPTER_ENV_VAR`), `resolve_adapter` at `:226`.
- Vacuous green: `hooks/tests/fixtures/adapters/codex/{in,out}/.gitkeep`
  only; `test_adapter_golden.py:69-85` (dir-existence),
  `:99` / `:135` / `:145` (claude-only behavior tests).
- Drift detector claude-only: `test_adapter_drift_detector.py:40`, `:232`.
- CI has no codex binary: `validate.yml:286-299` (deps + hooks-test lanes);
  codex appears in workflows only as `mcp-smoke.yml:267,281` tool-name
  strings and `release.yml:556-618` pin assertions.
- Pin reality: `.claude/governance/codex-cli-pin.txt` →
  `>=0.128.0,<0.140.0`; local binary `codex-cli 0.139.0`.
- Substrate watch: `grep -n codex .claude/scripts/check-substrate-watch.py`
  → no matches.
- Dual-role consumer: `check_pair_rail.py:829,:874`
  (`parse_verdict_strict`); Claude-shaped egress at `codex.py:247-263`.
- Installer test infra: `scripts/tests/{smoke-install.sh,test-doctor.sh,test-install-sandbox-merge.sh,test_install_baseline_manifest.sh}`;
  no installer job in `validate.yml`.
- Wrong-subsystem citation: `hooks/tests/adapters/live/test_adapters.py`
  docstring ("four ADR-040 live adapters", mock `http.server`).
