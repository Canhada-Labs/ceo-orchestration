# Cross-LLM Pair-Rail Threat Model

**Status:** v1.1 — Phase 6-bis final consolidation (PLAN-081 Phase 6-bis, S101-cont, 2026-05-11) + §9-bis containment-layer placement (PLAN-135 W4 D5+D8, 2026-06-12)
**Authors:** CEO Session 99 (Phase 1-full) · Session 100 (Phase 2 dispatcher + Phase 3 VETO matrix) · Session 101-cont (Phase 6-bis v1.0 consolidation)
**Authoritative:** Canonical threat-model doc for the Pair-Rail Multi-LLM architecture (Claude + Codex). This v1.0 supersedes all prior versions (v0.1 / v0.2 / v0.3). GA reference for v1.16.0.

---

## v1.0 Changelog (Phase 6-bis consolidation)

| Increment | What changed |
|---|---|
| v0.1 → Phase 1-full | T-1 (ingress injection), T-2 (egress secret leak), T-3 (PostToolUse blind spot) |
| v0.2 → Phase 2 | T-4 (archetype-spoofing via routing-matrix.yaml); §1 Scope expanded to Phase 2 surface |
| v0.3 → Phase 3 | T-5 (Case-B precondition bypass), T-6 (Case-F fail-open exploitation) |
| **v1.0 → Phase 6-bis** | **Full §1 Scope (Phases 1-6); T-7 (Codex codando deny-list bypass — Phase 5 surface); T-8 (Codex CLI binary swap / supply-chain — Phase 6 surface); T-9 (MITM on local stdio transport — Phase 6 surface); §3 State machine (ASCII); §4 Sandbox modes risk profile; §5 Asymmetric coverage disclosure (full); §6 MITRE ATT&CK coverage matrix; §7 OWASP Top 10 + LLM Top 10 coverage matrix; §8 Three hunting playbooks (T-1, T-7, R-NEW-1); §9 Open questions** |
| v1.1 → PLAN-135 W4 (D5+D8) | §9-bis containment-layer placement: T-1..T-9 mitigations mapped to the environment / model-policy / content taxonomy + harness-native vs hook ownership; honest position (the entire pair-rail is model/policy + content layer; §4 "sandbox modes" are MCP-server config declarations, not OS enforcement); egress-substitution named as the gold tier above T-2 redaction; MCP-connector-bypasses-rail rule (API-side `mcp_servers` emits NO PreToolUse — the whole rail is structurally bypassed) |

---

## §1. Scope (v1.0 — Phases 1-6 complete)

This version covers the full Phase 1-6 attack surface of the Pair-Rail Multi-LLM architecture. All prior per-version "out of scope" deferred items are now in scope.

**Phase 1-full surface:**

- `.claude/hooks/_lib/adapters/codex.py` — Codex MCP hook adapter (502 LoC).
- `.claude/hooks/_lib/adapters/_constants.py` — SHA-pinned adapter constants.
- `.claude/hooks/_lib/codex_egress_redact.py` — single-pass egress redactor.
- `.claude/hooks/check_codex_response.py` — PostToolUse ingress sanitizer (3 pattern families).
- `.claude/hooks/_lib/audit_emit.py:emit_pair_rail_codex_injection_detected` — audit emitter.
- `.claude/scripts/codex_invoke.py` — subprocess invocation wrapper.
- `.claude/scripts/local/pair-rail-gate.sh` — Phase 1 pre-flight checks.

**Phase 2 surface:**

- `.claude/dispatcher/routing-matrix.yaml` — 8-archetype Pair-Rail capability matrix.
- `.claude/dispatcher/routing-matrix-loader.py` — schema-validating YAML loader + SHA-pin assertion.
- `.claude/dispatcher/disable_predicate_eval.py` — typed-state-machine predicate evaluator (bounded tail-scan).
- `.claude/scripts/inject-agent-context.sh` — extended with `--pair-mode --coder= --reviewer=` flags.
- `.claude/hooks/_lib/audit_emit.py:emit_dispatcher_route` — Phase 2 audit emitter.

**Phase 3 surface:**

- `.claude/hooks/check_pair_rail.py` — PreToolUse asymmetric VETO evaluator (Cases A-F).
- `.claude/policies/rubric-violation-catalogue.yaml` — 19-entry catalogue of P0/P1 rubric violations.
- `.claude/hooks/_lib/audit_emit.py:emit_pair_rail_case` — Case audit emitter.

**Phase 4 surface (locked-corpus governance):**

- `.claude/governance/locked-corpus/` — N=15 SHA-pinned corpus fixtures.
- `.claude/governance/inputs-hash-manifest.json` — per-fixture SHA-256 manifest for corpus immutability.
- `.claude/hooks/check_pair_rail.py:_assert_corpus_sha()` — corpus-pin assertion gate.
- ADR-111 — locked-corpus governance (ACCEPTED).

**Phase 5 surface (Codex codando deny-list):**

- `.claude/hooks/check_codex_filewrite.py` — PreToolUse deny-list (DRY_RUN advisory, Phase 5).
- `.claude/policies/codex-filewrite-denylist.yaml` — glob patterns for canonical-path protection.
- `.claude/hooks/_lib/audit_emit.py:emit_pair_rail_codex_denylist_hit` — deny-list audit emitter.

**Phase 6 surface (verdict artifact + binary pin + supply-chain):**

- `.claude/governance/codex-cli-binary-sha256.txt` — Codex CLI binary SHA-256 pin.
- `.claude/governance/rubric-catalogue-pin.txt` — rubric catalogue SHA-256 pin (⏳ Phase 7 follow-up — NOT YET SHIPPED; placeholder reference).
- `.claude/scripts/local/pair-rail-gate.sh` — Phase 1 pre-flight checks (current); binary-pin + catalogue-pin pre-flight extension is ⏳ Phase 7 follow-up (NOT YET IMPLEMENTED).
- `.claude/governance/pair-rail-verdict-template.md` — structured verdict artifact template.
- `.github/scripts/validate-pair-rail-verdict.py` — verdict artifact schema validator.
- `docs/PAIR-RAIL-VERDICT-MATRIX.md` — asymmetric coverage reference (Phase 6 deliverable).

---

## §2. Threat catalogue (v1.0 — T-1 through T-9)

### T-1 — Codex output prompt-injection (ingress vector)

**Asset:** Claude session integrity. The next Claude turn after a Codex MCP review consumes Codex's stdout as part of its context.

**Adversary:** The Codex stdout can contain attacker-controlled content sourced from:
- A malicious file in the workspace that Codex read during review.
- A poisoned dependency README / docstring quoted by Codex.
- A compromised Codex CLI binary upstream (covered by T-8).
- MITM on the Codex MCP local stdio transport (covered by T-9).

**Vulnerability:** Claude's system-prompt parser may interpret framework-specific tokens (`[SYSTEM:`, `<system>`, `<tool_use>`) as in-band system messages and act on them. The Codex output is **provider-controlled** but contains **attacker-influenced** text.

**Impact:** **HIGH.** Successful T-1 exploitation can:
- Cause Claude to dispatch unintended sub-agents.
- Suppress safety-critical context from the next turn.
- Forge tool-use intent that Claude executes.

**Mitigation (Phase 1-full):**

`check_codex_response.py` — PostToolUse mcp__codex__* matcher — scans Codex stdout for the three injection pattern families:

| Family | Pattern | Examples |
|---|---|---|
| `harness_mimicry` | `\[\s*SYSTEM\s*:` (case-insensitive) | `[SYSTEM: ignore]`, `[ system :` |
| `xml_system_tag` | `<\s*system\b` | `<system>`, `<system attr=>` |
| `tool_use_forgery` | `<\s*tool_use\b` | `<tool_use>`, `<tool_use name=>` |

On any match, the hook emits `pair_rail_codex_injection_detected` to the audit log with:

- `tool_name` (str — `mcp__codex__codex` or `mcp__codex__codex-reply`)
- `family_ids` (sorted unique list)
- `match_count` (int)
- `first_offset_bucket` (`"0-100"` / `"100-1k"` / `"1k-10k"` / `"10k-100k"` / `"100k+"`)

**Per ADR-106, this is ADVISORY-ONLY:** PostToolUse hooks cannot block the tool that already ran. The Owner / on-call surveys via `audit-query.py codex-injection-summary` and the local SSE dashboard. For HARD enforcement (block downstream dispatch on detection), see Phase 3 `check_pair_rail.py` PreToolUse extensions (v0.3 amends T-1 mitigation).

**Residual risk:** A novel injection pattern not in the three families bypasses ingress sanitization. Mitigation: Phase 4 locked-corpus N=15 includes 2 VETO-floor-discriminative fixtures (`prompt-injection-payload-in-comment` + `secret-in-source-string`) measuring `check_codex_response.py` discriminative behavior. If 14/15 → AUTO-FLIP gate retry triggers; <14/15 → manual triage forensic artifact.

**Detection:** SOC alerting via SIEM forward of audit-log `pair_rail_codex_injection_detected` events. Threshold: ≥1 event/24h surfaces; ≥3 events/1h pages. See Hunting Playbook 1 (§8).

**Test coverage:** `test_check_codex_response.py:5` fixture Codex outputs with embedded patterns assert sanitized output contains no `[SYSTEM:` / `<system>` / `<tool_use>` tokens. Phase 4 mutation fixtures harden coverage.

---

### T-2 — Codex output secret/PII leak (egress vector)

**Asset:** Audit log integrity (LLM06 side-channel guard). The audit log is forensic-only; it MUST NOT persist secrets that could be exfiltrated via log tap, dashboard export, or CI artifact.

**Adversary:** A user prompt to Codex may contain a credential (e.g. pasted API key in a code review prompt). Codex may quote that credential back in its rationale text or a synthetic example.

**Vulnerability:** If Codex stdout flows directly into `audit_emit.pair_rail_*` events without redaction, the credential persists in the JSONL audit log. Subsequent `audit-query.py` consumers, dashboard renderings, or CI artifact uploads expose the credential.

**Impact:** **HIGH** for OpenAI / OpenRouter / Anthropic / GitHub PAT keys. Key exposure → unauthorized API access, billing fraud, or supply-chain pivot.

**Mitigation (Phase 1-full):**

`_lib/codex_egress_redact.py:redact()` — single-pass invariant per R1 S-Sec-1:

```python
redacted, _findings = secret_patterns.scan_and_redact(text)
```

The single-pass guarantee is **load-bearing**. R1 S-Sec-1 evidence: chained two-pass redaction (e.g. SECRETS first, PII second) leaks partial-overlap matches like PEM-with-embedded-CPF — the PEM pattern matches the outer block and masks the surrounding bytes; the inner CPF is then partially exposed at the byte boundary. `secret_patterns.scan_and_redact()`'s budget-bounded longest-match-wins resolution handles overlap correctly.

ABI conformance test pins this:

- `test_codex_egress_redact.py:TestSinglePassInvariant::test_redact_calls_scan_and_redact_once` — AST-walks the source of `redact()` and asserts exactly one `_patterns.scan_and_redact` call.
- `test_codex_egress_redact.py:TestPemWithEmbeddedCpf::test_pem_with_embedded_cpf_overlap` — adversarial fixture `"-----BEGIN PRIVATE KEY-----\n123.456.789-09\n-----END PRIVATE KEY-----"` MUST redact both the PEM and the embedded CPF.

**Residual risk:** A novel secret family not in `secret_patterns.ALL_PATTERNS`. Phase 6 amends with `sk-proj-` + `sk-` OpenAI patterns per R1 S-Sec NTH-Sec-1 (mapped to `owasp_class: LLM06`).

**Detection:** Pre-write canary — adopters can run `audit-query.py secrets-leak-scan` periodically to retroactively re-scan the audit log for unredacted patterns (Phase 6).

---

### T-3 — PostToolUse semantic blind spot

**Asset:** Defense-in-depth invariant. Pair-Rail's hook surface is supposed to be the cross-LLM enforcement boundary; a semantic blind spot in PostToolUse hooks weakens that boundary.

**Adversary:** Per Claude Code's hook contract:
- **PreToolUse hooks CAN block** the tool from running (`{"decision":"block"}`).
- **PostToolUse hooks CANNOT block** the tool that already ran (decision is informational only — host emits whatever; the tool already committed its side effects).

This is the **structural** semantic of PostToolUse, not a Claude Code bug. PLAN-081 Phase 1-full uses PostToolUse for ingress sanitization because we cannot intercept the Codex tool call BEFORE it returns (PreToolUse fires before the tool runs; no Codex output to scan yet).

**Vulnerability:** A user / sub-agent / dispatcher relying on `check_codex_response.py` to "block" malicious Codex output will be silently disappointed — the hook only emits `allow` and an audit event.

**Impact:** **MEDIUM.** Misunderstanding of the semantic could lead to false-confidence operational posture ("Pair-Rail blocks bad Codex output") that doesn't match reality.

**Mitigation (Phase 1-full):**

- **Documentation discipline:** `check_codex_response.py` module docstring explicitly labels ADVISORY-ONLY. ADR-106 codifies this. `docs/PAIR-RAIL-VERDICT-MATRIX.md` (Phase 6 v1.0) consolidates the asymmetric coverage matrix.
- **Layered enforcement:** Phase 3 PreToolUse `check_pair_rail.py` extension implements the asymmetric VETO matrix Cases A-F. Cases B (Claude PASS / Codex BLOCK) and D (both BLOCK) actually short-circuit the dispatched tool BEFORE it runs. PostToolUse remains advisory; PreToolUse gives the hard enforcement.
- **Audit-trail forensic:** detection without enforcement is still forensic-valuable. SOC alerts on `pair_rail_codex_injection_detected` surface the issue for human review in 1-24h windows.

**Residual risk:** A user may accept the advisory-only semantic but still want hard enforcement per-archetype. Phase 5 codando deny-list (`check_codex_filewrite.py` PreToolUse mcp__codex__*) closes the file-write surface; Phase 3 PreToolUse `check_pair_rail.py` extension closes the dispatch surface. v0.4 amends T-3 once Phases 3+5 land.

**Detection:** N/A (this is a documentation / training threat, not a runtime threat).

---

### T-4 — Archetype-spoofing via routing-matrix.yaml manipulation

**Asset:** Pair-Rail routing decisions. The dispatcher reads `.claude/dispatcher/routing-matrix.yaml` to resolve, per archetype, which provider acts as `coder` vs `reviewer`, which sandbox mode applies to the reviewer, which fallback provider engages when the pair-rail is disabled, and which `disable_predicates` gate the rail. A successful T-4 exploit corrupts these decisions silently — Pair-Rail still appears "enabled" while in fact routing all dispatches to a single LLM (negating cross-LLM defense) or to an attacker-favored sandbox mode.

**Adversary:** A sub-agent or compromised contributor with edit access to the canonical surface attempts one of:

- **Swap coder/reviewer** — set `coder: codex` for a VETO-floor archetype (`code-reviewer`, `security-engineer`, `threat-detection-engineer`) BEFORE Phase 4 promotion gate passes 15/15 strict (ADR-052 floor breach + ADR-108 violation).
- **Downgrade reviewer sandbox** — change `reviewer_sandbox: read-only` to `workspace-write` to grant the reviewer file-write capabilities Phase 5 hasn't gated yet.
- **Drop disable_predicates** — remove the `codex_outage_5min` / `fp_rate_30d_above_30pct` / `latency_p95_above_60s` predicates so the pair-rail stays "enabled" during a real Codex outage / quality regression / performance regression (preserves the appearance of cross-LLM defense while the second rail is actually inert).
- **Add a phantom archetype** — inject a `phantom-coder` entry that bypasses the 8-archetype mandatory L2+ contract, routing real dispatches to single-LLM under a misleading name.
- **Lower coder_model floor** — change `coder_model: opus` to `coder_model: haiku` for a VETO-floor archetype (ADR-052 + ADR-064 violation).

**Vulnerability:** The matrix is plain YAML on disk. Without canonical-guard sentinel enforcement + SHA-pin verification + archetype enumeration completeness check, any of the above mutations would silently take effect on the next dispatch cycle.

**Impact:** **HIGH.** Successful T-4 exploitation can:

- Disable cross-LLM review for VETO-floor archetypes (ADR-052 / ADR-108 floor breach).
- Mask Codex outages or quality regressions (no failover to fallback_provider).
- Grant the reviewer write capability before Phase 5 deny-list gates write attempts (privilege escalation).
- Mis-route dispatches to single-LLM under cover of legitimate-looking archetype names.

**Mitigation (Phase 2):**

1. **Canonical-guard registration** — `routing-matrix.yaml` + `routing-matrix-loader.py` + `disable_predicate_eval.py` all under `.claude/dispatcher/*.{py,yaml,yml}` and `.claude/dispatcher/**/*.py` glob in `_CANONICAL_GUARDS` (`check_canonical_edit.py`). Edits require Owner-signed `approved.md` sentinel. The dispatcher dir guards are added in Phase 2 as a KERNEL-HARD-DENY extension (sentinel + `CEO_KERNEL_OVERRIDE=PLAN-081-PHASE-2-DISPATCHER-GUARD-EXTENSION` + `CEO_KERNEL_OVERRIDE_ACK=I-ACCEPT` env vars).
2. **SHA-pin assertion** — `routing-matrix-loader.load_routing_matrix()` honors `CEO_PAIR_RAIL_MATRIX_SHA256` env var. When set, the loader computes the SHA-256 of the YAML bytes and compares against the pinned digest. Mismatch + `CEO_PAIR_RAIL_FAILCLOSED=1` → raises `RoutingMatrixError`. The pre-flight `pair-rail-gate.sh` (Phase 6 extension) sets the pin so adopters can detect drift between corpus runs.
3. **Schema validation at load time** — `_KNOWN_ARCHETYPES` enforces exactly 8 archetype names. Unknown name → `RoutingMatrixError`. Missing archetype (e.g. only 7 of 8 present) → `RoutingMatrixError`. Unknown coder/reviewer provider → `RoutingMatrixError`. Unknown predicate type / operator → `RoutingMatrixError`. Tabs in indent / flow-style mappings / anchors / aliases → `RoutingMatrixError`. This closes phantom-archetype injection, mismatched count, and YAML-injection escapes.
4. **Audit emit on dispatch decision** — every `--pair-mode` dispatch emits `dispatcher_route_emit` carrying `matrix_sha256_prefix` (16 hex) + `matrix_sha256_match` (bool against pin). Forensic-trail surface for `audit-query.py search 'dispatcher_route' (advisory rollup; dedicated dispatcher-routes-summary sub-command is ⏳ Phase 7 follow-up)` (Phase 6 deliverable). Sec MF-3 allowlist enforces no archetype-profile or task-description leak.
5. **`validate-governance.sh` REQUIRED_FILES** — the three dispatcher artifacts are listed in section 3 (Required governance files). A missing file → ERROR (gate fails). This catches accidental delete / move attempts that bypass the canonical-guard (which only catches edits, not deletions).
6. **Defense-in-depth: VETO-floor archetypes pinned** — for `code-reviewer`, `security-engineer`, `threat-detection-engineer`, the matrix declares `coder: claude` + `coder_model: opus` (ADR-052 floor). Phase 5 codando deny-list (`check_codex_filewrite.py`) further blocks Codex from writing canonical paths regardless of matrix state — so even a successful T-4 on these archetypes cannot escalate to file-write breach (defense-in-depth).

**Residual risk:** A simultaneous compromise of (a) the canonical-guard sentinel mechanism, (b) the kernel-override env vars, AND (c) the audit-log integrity (HMAC chain) would defeat all 6 mitigations. This is the same residual-risk class as direct edits to `_lib/audit_emit.py` itself; out-of-scope for T-4 specifically. Owner physical-time + GPG-key + HMAC-chain compromise is the threshold class assumed beyond Pair-Rail's defense surface.

**Detection:**

- `audit-query.py search 'dispatcher_route' (advisory rollup; dedicated dispatcher-routes-summary sub-command is ⏳ Phase 7 follow-up)` (Phase 6 v1.0 deliverable) reports archetype distribution + matrix_sha256_match rate + reason_code breakdown. Spike in `reason_code: matrix_sha_mismatch` → investigate matrix integrity. Drop of any archetype to 0 dispatches in active session → archetype-omission attack candidate.
- `validate-governance.sh` REQUIRED_FILES block prints `MISSING:` line + increments `ERRORS` counter for any of the 3 dispatcher artifacts.
- `routing-matrix-loader._main()` smoke-test prints the loaded matrix; CI dry-run can compare against last-known-good output.
- HMAC chain on `dispatcher_route_emit` records (via `_lib/audit_hmac`) detects post-hoc tampering of dispatch decisions in audit-log.

---

### T-5 — Case-B precondition bypass

**Asset:** Pair-Rail mechanical block surface for VETO-floor archetypes (CR + Sec + TDE) at L3+. Per ADR-107 + ADR-108, a Case-B verdict (Claude PASS + Codex BLOCK) mechanically blocks dispatch IFF preconditions are met: file:line cited + rubric_violation_id ∈ catalogue + severity ∈ {P0, P1}. Without preconditions, the case downgrades to Case-B' fail-OPEN advisory per ADR-106. T-5 attempts to bypass the mechanical block by exploiting precondition validation gaps.

**Adversary:** A compromised Codex CLI binary, a malicious response interceptor, or an adopter-mutated rubric catalogue attempting one of:

- **Free-form rubric ID injection** — Codex returns a Case-B verdict with a non-catalogue `rubric_violation_id` (e.g. typo `sec-injection-prompt-x`); `_validate_provider_pair()` rejects it via the catalogue check; case downgrades to Case-B' (advisory, NOT blocking). Attacker uses this to mask a real P0 finding behind a deliberately mistyped ID.
- **Catalogue truncation** — `.claude/policies/rubric-violation-catalogue.yaml` mutated to remove P0 entries (e.g. `sec-injection-sql`); ANY Case-B verdict citing a removed ID downgrades to Case-B' (the catalogue lookup returns missing); mechanical block surface shrinks silently.
- **Severity downgrade** — Codex returns Case-B with `severity=P2` (not in {P0, P1}); precondition validation rejects; case downgrades to advisory; the actual P0 finding is masked.
- **File:line omission** — Codex returns Case-B with no `file:line` evidence; precondition validation rejects; advisory-only path engaged. Combined with severity downgrade, attacker can systematically engineer Case-B' verdicts that look BLOCKing but never bind.
- **Race against grace window** — for severity P1, Codex returns Case-B at T+0; Owner has 24h to label `tp` (true-positive) per `audit-query.py label`. Attacker times the Case-B emit during a known Owner-offline window so the 24h grace expires unlabeled, closing-as-advisory automatically.

**Vulnerability:** Case-B preconditions are loose by design (R1 spec.md §11 R1.5-3) — they exist to prevent Codex from forcing arbitrary blocks on Claude. The looseness is the attack surface: any precondition failure path closes-as-advisory rather than fail-CLOSED.

**Impact:** **HIGH.** Successful T-5 exploitation can:

- Suppress P0-class findings (real injection, broken auth, alg=none) behind catalogue mutations or severity downgrades.
- Train SOC + Owner to ignore advisory-only Case-B' channel (over time it becomes noise).
- Combine with T-4 archetype-spoofing to mis-route VETO-floor archetypes AND suppress their findings simultaneously.

**Mitigation (Phase 3):**

1. **Catalogue sentinel-gating** — `.claude/policies/rubric-violation-catalogue.yaml` is canonical-guarded under `.claude/policies/*.yaml` glob in `_CANONICAL_GUARDS`. Edits require Owner-signed sentinel. Truncating an entry leaves a forensic record (git history + sentinel scope mismatch detection).
2. **Catalogue ID enumeration** — `_validate_provider_pair()` cross-checks `rubric_violation_id` against the live catalogue at decision time. The catalogue MUST be loaded for Case-B preconditions to validate — if missing, every Case-B downgrades to advisory (defense-in-depth: no catalogue → no mechanical block, fail-OPEN to advisory rather than fail-OPEN to no-trace).
3. **Audit emit per case** — every Case-B (precondition met OR not) emits `pair_rail_case_emit` with `precondition_met: bool` + `rubric_violation_id` + `severity` fields. Forensic audit-query at `audit-query.py search 'pair_rail_case'` reports the precondition-met rate per archetype. Spike in precondition-NOT-met rate → investigate catalogue + Codex behavior.
4. **Severity P0 mechanical bind** — P0 violations have `human_triage_grace_h=0` (no grace window). The grace-window race exists only for P1; P0 binds immediately. Plus catalogue authoring discipline: P0 = mechanically-blocking categories; P1 = human-triage-required; the catalogue PR review enforces this distinction.
5. **24h grace bounded by audit-query.py** — Phase 6 `audit-query.py fp-rate --window-days 30` reports the rate of grace-expired-unlabeled P1 events. If `>5%` of P1 events expire unlabeled in 30d, ADR-108 reopen criterion triggers (pair-rail demoted to advisory-only).
6. **Catalogue version pinning** — Phase 3 ships catalogue under sentinel governance only. The `pair-rail-gate.sh` pre-flight catalogue SHA-256 check against `.claude/governance/rubric-catalogue-pin.txt` is **Phase 7 follow-up — NOT YET IMPLEMENTED**. release.yml step 15 (Validate pair-rail verdict, shipped Phase 6-bis) is the LAST current step; step 16 catalogue-pin check is scoped to Phase 7.

**Residual risk:** A catalogue mutation that ADDS a fake-looking P1 entry whose ID matches a planned future Codex misfire could be used to engineer false-positive Case-B at scale. Mitigated by ADR-111 catalogue immutability + reopen criteria (Phase 4) + Owner labeling protocol (Phase 6).

**Detection:**

- `audit-query.py search 'pair_rail_case'` (Phase 6 v1.0 deliverable) reports per-case distribution + precondition_met rate + severity distribution. Spike in `precondition_met=false` for VETO-floor archetypes → investigate Codex/catalogue.
- `audit-query.py fp-rate --window-days 30` reports labeled-FP rate; `>30%` triggers `fp_rate_30d_above_30pct` predicate firing per archetype, disabling pair-rail.
- HMAC chain on `pair_rail_case_emit` detects post-hoc field tampering (e.g. `precondition_met: false` flipped to `true` after-the-fact).

---

### T-6 — Case-F fail-open exploitation

**Note:** Earlier prose called this "Case-D fail-open"; the canonical asymmetric matrix labeling is Case F = timeout/outage/malformed (per spec.md §11 + ADR-107 ACCEPTED labels). Case D = both-BLOCK (hard-block, not relevant to fail-open). T-6 specifically targets Case F.

**Asset:** Pair-Rail fail-OPEN semantics per ADR-106. When Codex is unreachable / times out / returns malformed output, `_decide()` returns `{decision: allow}` with `systemMessage` describing the failure. Case F is the audit label for these events.

**Adversary:** An attacker with read access to the audit-log can correlate `pair_rail_case_emit case=F` events with their own injection attempts to engineer windows of guaranteed fail-OPEN behavior:

- **Codex DoS** — flood the local Codex MCP server with pathological prompts to induce timeouts. While timeouts persist, all Pair-Rail evaluations enter Case F (fail-OPEN). Attacker times malicious commits to hit the timeout window.
- **Sandbox-mode escalation** — when the routing matrix declares `reviewer_sandbox=read-only` for an archetype but adopter-side runtime grants write access (e.g. via misconfigured MCP server settings), Codex could write to disk during review; combined with Case F masking, the writes are forensic-invisible.
- **Catalogue-load failure** — induce permission errors or corrupt YAML on `rubric-violation-catalogue.yaml`; loader's fail-OPEN-on-load-error returns empty catalogue; ALL Case-B verdicts downgrade to Case-B' (advisory); attacker engineers a known-injection commit to slip through.

**Vulnerability:** ADR-106 codifies fail-OPEN as the correct posture for hook bugs (a blocking hook that depends on a flaky upstream is worse than no hook). T-6 weaponizes the fail-OPEN policy.

**Impact:** **MEDIUM-HIGH.** Successful T-6 exploitation can:

- Time malicious commits to coincide with Codex outages (engineered or organic).
- Mask disposable-permission writes during review.
- Combined with T-1 (ingress prompt-injection from Codex output), inject a malicious payload during a known fail-OPEN window.

**Mitigation (Phase 3):**

1. **Fail-OPEN audit emit (DOES emit)** — every Case F emits `pair_rail_case_emit case=F codex_verdict=TIMEOUT|MALFORMED`. The fail-OPEN path is NOT silent; SOC alerting on `case=F` rate spike >5% over 1h surfaces the DoS pattern.
2. **Codex outage predicate disables routing** — `disable_predicates.codex_outage_5min` evaluates the trailing 60min window of `pair_rail_codex_unavailable` events; if >5min of outage, the pair-rail is disabled per archetype + dispatcher routes single-LLM via fallback. This narrows the "guaranteed fail-OPEN" window to <5min.
3. **Case-F + matrix_sha_mismatch correlation** — if both Case F rate AND `matrix_sha_mismatch` rate spike simultaneously, that's a strong T-4+T-6 combined attack signal. SOC playbook detects.
4. **Catalogue fail-CLOSED on parse error (Phase 4 escalation)** — current Phase 3 implementation fails-OPEN on catalogue load failure; Phase 4 promotion gate adds catalogue SHA-pin assertion that fails-CLOSED on mismatch (gated behind explicit Owner override). Phase 3 carries forward the audit + matrix_sha_mismatch detection.
5. **Bounded retry budget** — `codex.py:_resolve_timeout_s()` caps retry to 1 attempt at audit-class timeout (240s); does NOT retry-loop indefinitely. Attacker cannot engineer infinite Case F by sustained DoS — after 1 retry, the dispatch returns Case F audit emit + caller falls through.

**Residual risk:** A coordinated DoS + injection at the exact 5min outage threshold could engineer a brief window where the predicate is about to fire (disabling pair-rail) while Case F is still emitting. Mitigated by SOC alerting + 60min trailing window aggregation (predicates evaluate over a longer window than the 5min outage threshold, smoothing transient attack windows).

**Detection:**

- `audit-query.py search 'pair_rail_case'` rate of `case=F` events. Spike >5% over baseline → DoS / outage incident.
- `audit-query.py search 'pair_rail_case' --where "case=F AND codex_verdict=MALFORMED"` rate. MALFORMED rate >0.5% → likely Codex CLI corruption or upstream provider mutation.
- Correlation: `pair_rail_codex_unavailable` events + `pair_rail_case_emit case=F` + `dispatcher_route_emit reason_code=predicate_codex_outage_5min_fired` should monotonically follow each other on a real outage. Out-of-order = attack signal.

---

### T-7 — Codex codando deny-list bypass (NEW — Phase 5 surface)

**Asset:** Framework canonical-path integrity. When Codex acts as `coder` (Phase 5 flipped role — Codex-as-coder, Claude-as-reviewer), Codex MCP has write-capable tool calls that could target canonical-guarded paths (e.g. `_lib/audit_emit.py`, `check_canonical_edit.py`, `SPEC/v1/`). A successful T-7 bypass allows Codex to overwrite governance-critical files without sentinel authorization.

**Adversary:** A Codex response (or a prompt that steers Codex) requesting a write to a canonical-guarded path:

- **Direct canonical write** — Codex issues a write-to-file tool call targeting `.claude/hooks/_lib/audit_emit.py` directly, knowing the deny-list must enumerate this exact path.
- **Glob escape** — Codex targets a path that evaluates to a canonical file but is not enumerated in the deny-list globs (e.g. `../.claude/hooks/_lib/../_lib/audit_emit.py` — path traversal variant).
- **Deny-list parser crash** — Codex output triggers a YAML/Python parsing edge case in `check_codex_filewrite.py` or `codex-filewrite-denylist.yaml`; hook fails-OPEN, allowing the write.
- **DRY_RUN mode leakage** — Phase 5 ships `check_codex_filewrite.py` in `CEO_CODEX_DRYRUN=1` advisory mode. Attacker exploits the DRY_RUN default to write canonical paths during the advisory window (before Phase 4 promotion gate flips to enforcing mode).
- **Novel canonical path** — a new canonical file is added to `_CANONICAL_GUARDS` in `check_canonical_edit.py` but the corresponding glob is NOT added to `codex-filewrite-denylist.yaml`. Gap persists until the next ceremony.

**Vulnerability:** The deny-list is a glob enumeration against a dynamic canonical surface. Any new canonical path or glob escape creates a silent bypass window.

**Impact:** **HIGH.** Successful T-7 exploitation can:

- Overwrite `_lib/audit_emit.py` to suppress audit events (removes forensic visibility).
- Modify `check_canonical_edit.py` to self-remove its own canonical-guard (removes the governance layer entirely).
- Write to `SPEC/v1/` to forge compliance claims.
- Modify `check_codex_filewrite.py` itself to disable the deny-list check.

**Mitigation (Phase 5):**

1. **`check_codex_filewrite.py` PreToolUse deny-list** — fires on `mcp__codex__*` write-capable tool calls. Resolves the target path to absolute form, normalizes `..` traversal components, then matches against deny-list globs. Any match → `{"decision":"block", "reason":"deny-list"}` + emits `pair_rail_codex_denylist_hit` audit event. Fail-CLOSED on parser crash (exception handler returns block, not allow).
2. **Glob-coverage contract test** — `test_deny_list_coverage_vs_canonical_guards()` (R1 C1) enumerates every path in `_CANONICAL_GUARDS` and asserts at least one deny-list glob matches it. CI gate ensures new canonical paths automatically fail coverage contract until deny-list is updated.
3. **Mutation kill-rate gate** — `run-skill-benchmark.py --scenario codex-filewrite-denylist` executes 3-5 mutation fixtures (R1 C2): path-traversal bypass, glob-escape via symlink, YAML-injection in deny-list file, parser-crash payload. Minimum kill-rate ≥80% required for Phase 5 enforcing flip. Fixtures at `.claude/governance/locked-corpus/deny-list-mutations/`.
4. **Canonical-guard on deny-list itself** — `codex-filewrite-denylist.yaml` is under `.claude/policies/*.yaml` glob in `_CANONICAL_GUARDS`. Codex cannot edit its own deny-list without Owner-signed sentinel.
5. **DRY_RUN advisory logging** — in DRY_RUN mode, every would-be block emits `pair_rail_codex_denylist_hit` with `dry_run: true`. SOC monitoring surfaces the deny-list hit rate in advisory mode before flip. If hit rate >0 before flip, Owner reviews before Phase 5 enforcing activation.
6. **Phase 4 promotion gate dependency** — Phase 5 enforcing flip is gated on Phase 4 N=15 corpus passing ≥14/15 strict. Until then, `CEO_CODEX_DRYRUN=1` is the default. The gate enforces temporal ordering: no enforcing deny-list until corpus coverage is empirically validated.

**Residual risk:** A novel canonical path added between corpus runs creates a gap window. Mitigation: `test_deny_list_coverage_vs_canonical_guards()` runs in CI on every commit; any canonical-path addition that skips deny-list update fails the test gate (blocks merge).

---

### T-8 — Codex CLI binary swap / supply-chain (NEW — Phase 6 surface)

**Asset:** Codex CLI binary integrity at invocation time. The Pair-Rail architecture shells out to the Codex CLI binary via `subprocess.run(["codex", ...])`. If the binary resolved at invocation time is not the vetted version, the entire cross-LLM review surface is compromised.

**Adversary:** A supply-chain or host-level attacker targeting the Codex binary:

- **Malicious package upgrade** — `npm upgrade -g @openai/codex` or equivalent installs a compromised version during normal operations. The new binary silently differs from the pinned SHA-256.
- **PATH-prepended decoy** — attacker prepends a directory to `$PATH` containing a `codex` binary that proxies legitimate calls but injects content into the Codex response channel.
- **tmpfs-injected binary** — a transient `/tmp/codex` or `/tmp/foo/codex` binary is PATH-injected for the duration of a single session; removed after use; no persistent artifact.
- **Symlink pivot** — the binary path is a symlink that is atomically redirected between the SHA pin assertion and the actual subprocess call (TOCTOU).

**Vulnerability:** `subprocess.run(["codex", ...])` resolves `$PATH` at invocation time with no SHA assertion at the call site. The SHA-pin in `.claude/governance/codex-cli-binary-sha256.txt` is only checked by `pair-rail-gate.sh` at session pre-flight — not at every Codex invocation.

**Impact:** **CRITICAL.** A successful T-8 compromise of the Codex binary defeats the entire cross-LLM review surface:

- All Case-A through Case-E verdicts are generated by the attacker-controlled binary.
- `check_codex_response.py` PostToolUse sanitization runs against the compromised output (which may be crafted to evade pattern matching).
- The HMAC chain and audit events are all generated by the Claude harness trusting the compromised binary's output as legitimate Codex review.

**Mitigation status — partial implementation; runtime checks scheduled Phase 7 follow-up:**

1. **`.claude/governance/codex-cli-binary-sha256.txt`** ✅ **SHIPPED Phase 6-bis** — SHA-256 pin of the vetted Codex CLI binary (R-NEW-4 from PLAN-081 §6). Currently pinned to Owner's local 0.130.0 binary. Updated via ceremony: Owner runs `shasum -a 256 $(which codex) > .claude/governance/codex-cli-binary-sha256.txt` + GPG-signs the resulting sentinel update. Canonical-guarded under `.claude/governance/*.txt` post-Phase-6-bis (sentinel + KERNEL HARD-DENY for the guard list).
2. **`.github/scripts/validate-pair-rail-verdict.py --codex-cli-binary-sha256-file`** ✅ **SHIPPED Phase 6-bis** — release.yml step 15 asserts `verdict.tool_versions.codex_cli_binary_sha256` matches the pin file. Defeats supply-chain swap between rc.1 verdict generation and GA tag time. (Missing pin file → ADVISORY skip per Codex iter-1 P1 fix; semver pin still enforced.)
3. **`pair-rail-gate.sh` binary-pin assertion at session pre-flight** ⏳ **Phase 7 follow-up (documented intent — NOT YET IMPLEMENTED)** — the planned design: resolves `which codex` → computes SHA-256 of the resolved binary path → asserts against the pin file. Failure → exits non-zero → session pre-flight aborts. Emits `pair_rail_codex_binary_verified` audit event on PASS (`sha256_prefix` 16 hex + `binary_path` + `pin_match: true`). Currently the gate.sh script does NOT include this check; tracked as Phase 7 deliverable.
4. **`codex.py` invocation-time TOCTOU heuristic** ⏳ **Phase 7 follow-up (documented intent — NOT YET IMPLEMENTED)** — planned: `_lib/adapters/codex.py` records `resolved_path = shutil.which("codex")` at module import time. If `resolved_path` changes between import and subprocess call, a WARN breadcrumb is emitted to audit log (TOCTOU heuristic — does not block but surfaces the condition).
5. **Ceremony discipline** ✅ **SHIPPED Phase 6-bis (codex-cli-binary-sha256.txt now canonical-guarded; future pin updates require sentinel + ADR amendment if Phase 4 corpus re-run shows >5pp kill-rate regression).**
6. **CI smoke-test** — `validate-governance.sh` enhancement to check `codex-cli-binary-sha256.txt` exists + non-empty (REQUIRED_FILES gate) is also Phase 7 follow-up; pin file itself is shipped in Phase 6-bis but validate-governance.sh is not yet asserting on it.

**Residual risk:** SHA pin not updated after a legitimate upgrade. Per Phase 6-bis ship: release.yml step 15 (validate-pair-rail-verdict.py with `--codex-cli-binary-sha256-file`) hard-blocks tag time on mismatch when verdict carries `tool_versions.codex_cli_binary_sha256`. The Phase 7 follow-up adds runtime pre-flight via `pair-rail-gate.sh` to catch the same drift at session start (currently only release-time check is enforced). Adopters can set `CEO_PAIR_RAIL_SKIP_BINARY_PIN=1` to override at runtime once the Phase 7 check ships (currently a no-op env var — documented intent).

---

### T-9 — MITM on Codex MCP local stdio transport (NEW — Phase 6 surface)

**Asset:** Codex MCP request/response integrity. The Claude harness communicates with the Codex MCP server via a local stdio pipe (subprocess spawned by the MCP host). The stdio transport is the trust boundary between the Claude harness and the Codex process.

**Adversary:** A process running as the same UID as the Claude harness on the local host attempting to intercept or tamper with the stdio stream:

- **ptrace/gdb attach** — a malicious process attaches to the Codex subprocess PID and reads or modifies the stdio buffer in-flight.
- **LD_PRELOAD injection** — a malicious shared library preloaded into the Codex process intercepts `read()`/`write()` syscalls on file descriptors 0/1.
- **Shared file descriptor pivot** — if the MCP host shares file descriptors with the Claude process (e.g. via `fork()` before `exec()`), a malicious sibling can inherit and read the pipe.

**Vulnerability:** stdio is a plaintext local pipe with no integrity MAC or encryption. Any process running as the same UID can use `ptrace` (if not restricted by OS-level `ptrace_scope`) or `LD_PRELOAD` to intercept the stream. There is no in-band integrity check on the stdio bytes.

**Impact:** **LOW-MEDIUM** (local-only attack surface). Exploitation requires:
- Code execution as the same UID as the Claude harness process.
- Either `ptrace_scope=0` (permissive, non-default on modern Linux) OR `SIP` disabled (macOS).
- An active pair-rail session window to intercept.

Given these prerequisites, the practical likelihood for a framework user on a personal development workstation is low. However, the theoretical impact is HIGH (equivalent to T-8 if the attacker can modify the Codex response before `check_codex_response.py` sees it).

**Mitigation (Phase 6 — acknowledged, partially out-of-scope):**

1. **Process-isolation via `subprocess.PIPE`** — `codex.py` spawns the Codex subprocess with `stdout=subprocess.PIPE, stderr=subprocess.PIPE`. No intermediate file. The pipe is direct-parented — no third-party process is in the stdio chain by construction.
2. **Short-lived session window** — the Codex subprocess is spawned per-call and terminated immediately after output is consumed. No persistent stdio channel that can be pre-attached.
3. **OS-level `ptrace_scope`** — framework documentation (Phase 6 hardening guide) recommends `echo 1 > /proc/sys/kernel/yama/ptrace_scope` (Linux) or SIP enabled (macOS) as baseline. This is a host-level requirement, not in-scope for the framework to enforce.
4. **`check_codex_response.py` defense-in-depth** — even if T-9 succeeds in injecting bytes, the PostToolUse ingress sanitizer still runs over the final output visible to Claude. A T-9 attacker must craft output that both (a) looks like legitimate Codex review to the human analyst AND (b) passes the three injection pattern families. This raises the bar.

**Residual risk:** Any code running as the same UID can attach `ptrace` / `gdb` on Linux systems with `ptrace_scope=0`. This is treated as out-of-scope for the framework — host-level UID isolation and OS hardening are the Owner's responsibility. The framework documents this residual explicitly in the `docs/PAIR-RAIL-SECURITY-BASELINE.md` (Phase 6 deliverable).

---

## §3. State machine — dispatcher → pair-rail → verdict transitions

The following ASCII diagram shows the flow of a single pair-rail dispatch from archetype selection through final verdict audit. Events emitted at each transition node are shown in brackets.

```
  ┌─────────────────────────────────────────────────────────────────────┐
  │  CALLER (CEO / /spawn)                                              │
  │  Selects archetype + task description                               │
  └───────────────────────────────┬─────────────────────────────────────┘
                                  │
                                  ▼
  ┌─────────────────────────────────────────────────────────────────────┐
  │  inject-agent-context.sh --pair-mode --coder=X --reviewer=Y        │
  │  Loads routing-matrix.yaml [audit: dispatcher_route]               │
  │                                                                     │
  │  SHA-pin check (CEO_PAIR_RAIL_MATRIX_SHA256)                        │
  │    ├─ PASS → proceed                                                │
  │    └─ FAIL + CEO_PAIR_RAIL_FAILCLOSED=1 → abort [audit: matrix_sha_mismatch] │
  │                                                                     │
  │  disable_predicate_eval.py                                          │
  │    ├─ predicate fires (outage/fp-rate/latency) → single-LLM route  │
  │    └─ predicate clear → pair-rail route                            │
  └───────────────────────────────┬─────────────────────────────────────┘
                                  │ pair-rail route
                                  ▼
  ┌─────────────────────────────────────────────────────────────────────┐
  │  check_pair_rail.py [PreToolUse — fires BEFORE Codex MCP tool]     │
  │  Phase 3: Reads pending Claude verdict from context                │
  │                                                                     │
  │  Binary pin check (pair-rail-gate.sh pre-flight)                   │
  │    ├─ PASS → continue [audit: pair_rail_codex_binary_verified (⏳ Phase 7)] │
  │    └─ FAIL → abort (CEO_PAIR_RAIL_SKIP_BINARY_PIN overrides)       │
  └───────────────────────────────┬─────────────────────────────────────┘
                                  │
                                  ▼
  ┌─────────────────────────────────────────────────────────────────────┐
  │  Codex MCP subprocess (mcp__codex__codex / mcp__codex__codex-reply)│
  │  Runs as reviewer (sandbox=read-only default)                       │
  │                                                                     │
  │  check_codex_filewrite.py [PreToolUse — fires BEFORE Codex writes] │
  │    ├─ path NOT in deny-list → allow                                 │
  │    └─ path IN deny-list → block [audit: pair_rail_codex_denylist_hit] │
  └───────────────────────────────┬─────────────────────────────────────┘
                                  │ Codex stdout
                                  ▼
  ┌─────────────────────────────────────────────────────────────────────┐
  │  check_codex_response.py [PostToolUse — ADVISORY only]             │
  │  codex_egress_redact.py (single-pass secret scrub)                 │
  │                                                                     │
  │  Injection pattern scan (3 families)                               │
  │    ├─ no match → allow                                              │
  │    └─ match → allow + [audit: pair_rail_codex_injection_detected]  │
  └───────────────────────────────┬─────────────────────────────────────┘
                                  │ Codex verdict in next Claude turn
                                  ▼
  ┌─────────────────────────────────────────────────────────────────────┐
  │  check_pair_rail.py [PreToolUse — Phase 3 VETO evaluator]          │
  │  Cases A-F asymmetric VETO matrix                                  │
  │                                                                     │
  │  Case A: both PASS → allow                  [audit: pair_rail_case A] │
  │  Case B: Claude PASS + Codex BLOCK          │
  │    preconditions met → BLOCK  [audit: pair_rail_case B prec=true]  │
  │    preconditions NOT met → allow (advisory) [audit: pair_rail_case B' prec=false] │
  │  Case C: Claude BLOCK + Codex PASS → BLOCK  [audit: pair_rail_case C] │
  │       (Claude Opus VETO authority preserved per ADR-052)         │
  │  Case D: both BLOCK → BLOCK   [audit: pair_rail_case D]            │
  │  Case E: Jaccard ≤ 0.3 advisory divergence → allow w/ systemMessage [audit: pair_rail_case E] │
  │  Case F: Codex timeout/malformed → allow    [audit: pair_rail_case F] │
  └───────────────────────────────┬─────────────────────────────────────┘
                                  │
                                  ▼
  ┌─────────────────────────────────────────────────────────────────────┐
  │  VERDICT ARTIFACT                                                   │
  │  validate-pair-rail-verdict.py schema check                                  │
  │  Saved to .claude/governance/verdicts/<session>/<ts>.verdict.md    │
  │  [audit: pair_rail_promotion on Phase 4 gate]                      │
  └─────────────────────────────────────────────────────────────────────┘
```

---

## §4. Sandbox modes — Codex reviewer risk profile

The routing-matrix.yaml `reviewer_sandbox` field controls the file-system access granted to the Codex reviewer process. Three modes are defined; their risk profiles differ significantly.

### Mode 1: `read-only` (default for all 8 archetypes)

**What it means:** The Codex MCP server is configured to allow only read-capable tool calls (file reads, directory listings, grep). Write-capable calls (file writes, bash execution) are blocked at the MCP server level.

**Risk profile:**

- T-7 (deny-list bypass) is **not applicable** — no write-capable calls reach the deny-list check.
- T-1 (ingress injection) remains applicable — Codex can still output attacker-influenced text even in read-only mode.
- T-9 (MITM stdio) remains applicable — read-only mode does not affect the stdio transport.

**Residual risk:** A misconfigured MCP server that ignores the `read-only` sandbox declaration (e.g. adopter deploys Codex MCP with `--allow-write`) silently upgrades to workspace-write risk. The framework cannot enforce sandbox mode at the OS level — adopter's MCP server configuration is the trust boundary.

### Mode 2: `workspace-write` (requires Phase 4 corpus gate PASS ≥14/15)

**What it means:** Codex reviewer has write access to non-canonical workspace paths (e.g. `tests/`, `docs/`, staging dirs). Canonical paths are still protected by the deny-list (`check_codex_filewrite.py`).

**Risk profile:**

- T-7 (deny-list bypass) is **fully applicable**. Require deny-list coverage contract test green before enabling.
- T-8 (binary swap) risk is elevated — a compromised binary with workspace-write can exfiltrate code via staged files.
- Recommend explicit `audit-query.py codex-writeguard-summary --window-days 1` daily review while in workspace-write mode.

### Mode 3: `danger-full-access` (requires ADR amendment + Owner ceremony)

**What it means:** No file-system restrictions on Codex reviewer. Deny-list still applies but is the only line of defense.

**Risk profile:**

- **CRITICAL exposure.** All 9 threats have elevated impact in this mode.
- T-7 bypass impact is highest — `check_codex_filewrite.py` is the sole enforcement point.
- Phase 5 mutation kill-rate ≥80% requirement becomes a hard prerequisite for this mode (not just for Phase 5 flip).
- ADR-108 reopen criterion: any deny-list bypass finding in `danger-full-access` mode triggers immediate pair-rail demotion to advisory + Owner incident response.
- **Not recommended for production use.** Documented only for local development spike use cases.

---

## §5. Asymmetric coverage disclosure

The Pair-Rail architecture provides cross-LLM defense but has known blind spots that adopters must understand.

### What Pair-Rail catches

| Scenario | Detection mechanism | Audit event |
|---|---|---|
| Same-LLM blind spots — patterns Claude misses that Codex catches | Case-B BLOCK (Codex catches what Claude passed) | `pair_rail_case prec=true` |
| Coder-only code injection (Claude-as-coder, Codex-as-reviewer) | `check_codex_response.py` T-1 pattern families | `pair_rail_codex_injection_detected` |
| Secret/PII in Codex rationale | `codex_egress_redact.py` single-pass redaction | (redacted before emit) |
| Routing-matrix tampering | SHA-pin + schema validation + canonical-guard | `matrix_sha_mismatch` |
| Canonical file writes by Codex | `check_codex_filewrite.py` deny-list | `pair_rail_codex_denylist_hit` |
| Compromised Codex binary | release.yml step 15 `--codex-cli-binary-sha256-file` (shipped Phase 6-bis); `pair-rail-gate.sh` runtime SHA-pin pre-flight ⏳ Phase 7 | `pair_rail_codex_binary_verified` ⏳ Phase 7 |

### What Pair-Rail misses (known blind spots)

| Scenario | Reason | Mitigation status |
|---|---|---|
| Both-LLM blind spots — a vulnerability both Claude AND Codex miss | Cross-LLM review only catches differential findings | Phase 4 locked corpus validates discriminative coverage; not a complete substitute |
| Novel injection patterns (not in 3 families) | T-1 family enumeration is static | Phase 4 N=15 includes adversarial fixtures; open item for future Phase |
| Coder-only false positives (Codex BLOCK on legitimate code) | Case-B precondition gate (rubric_violation_id required) — without rubric ID, Codex BLOCK downgrades to advisory; Owner labels post-hoc as `fp` via `audit-query.py label` | fp-rate Wilson 95% lower bound > 0.30 → `fp_rate_30d_above_30pct` predicate auto-disables pair-rail for affected archetypes per ADR-108 §FP-rate |
| Semantic bugs (logic errors, not pattern-detectable) | Pattern-based detection only | Out-of-scope for pair-rail; human review responsibility |
| Supply-chain compromise of the Claude harness itself | If Claude harness is compromised, all hooks are also compromised | Out-of-scope; host-level trust boundary |
| MITM on stdio transport (same-UID attacker) | No in-band integrity MAC (T-9) | Host-level UID isolation; OS ptrace_scope hardening |

### Asymmetric VETO rationale (R1 S-TDE-Bonus)

The matrix is intentionally asymmetric: Codex-alone BLOCK (Case B) requires preconditions; Claude-alone BLOCK (Case C) is hard-block (Claude Opus VETO authority preserved per ADR-052); both-BLOCK (Case D) is hard-block; Case E (Jaccard ≤ 0.3 semantic divergence) allows with systemMessage warning. This reflects:

- **Claude is the orchestrator**: Claude's BLOCK is operationally trusted for VETO-floor archetypes.
- **Codex is the reviewer**: Codex's BLOCK is trusted only when it cites specific, catalogued evidence.
- **False-positive cost asymmetry**: A false Codex BLOCK on a legitimate commit is more disruptive than a missed finding (recoverable via re-review); a false Claude BLOCK on security-critical code is the correct conservative posture.

---

## §6. MITRE ATT&CK coverage matrix

| Threat | ATT&CK Technique | Technique Name | Notes |
|---|---|---|---|
| T-1 | T1059.006 | Command and Scripting: Python | Prompt-injection via Codex output influencing Claude's next action |
| T-1 | T1566.001 | Phishing: Spearphishing Attachment | Malicious content embedded in reviewed file (conceptual analogy) |
| T-2 | T1567 | Exfiltration Over Web Service | Secret/PII persisted to audit log → downstream exfil via log export |
| T-3 | T1562.001 | Impair Defenses: Disable or Modify Tools | PostToolUse semantic blind spot → false confidence in defense posture |
| T-4 | T1574.006 | Hijack Execution Flow: Dynamic Linker Hijacking | Routing-matrix manipulation redirects dispatch flow |
| T-4 | T1565.001 | Data Manipulation: Stored Data Manipulation | routing-matrix.yaml on-disk mutation |
| T-5 | T1059.006 | Command and Scripting: Python | Precondition bypass via engineered Codex responses |
| T-5 | T1565.001 | Data Manipulation: Stored Data Manipulation | Catalogue truncation mutates decision logic |
| T-6 | T1499.004 | Endpoint Denial of Service: Application Exhaustion | Codex DoS to force Case-F fail-OPEN window |
| T-7 | T1565.001 | Data Manipulation: Stored Data Manipulation | Deny-list bypass → canonical file overwrite |
| T-7 | T1059.006 | Command and Scripting: Python | Codex-as-coder writes governance-critical Python |
| T-8 | T1574.004 | Hijack Execution Flow: Dylib Hijacking | Binary swap / PATH-prepended decoy |
| T-8 | T1195.002 | Supply Chain Compromise: Compromise Software Supply Chain | Malicious Codex CLI package version |
| T-9 | T1055 | Process Injection | ptrace/LD_PRELOAD injection into Codex subprocess |
| T-9 | T1040 | Network Sniffing (analogy) | In-process stdio interception (local pipe analogy) |

---

## §7. OWASP coverage matrix

### OWASP Top 10 (Web, 2021)

| Threat | OWASP Category | Mapping rationale |
|---|---|---|
| T-1 | A03: Injection | Prompt-injection via Codex output into Claude context |
| T-2 | A02: Cryptographic Failures | Secrets/PII persisted in plaintext audit log |
| T-3 | A05: Security Misconfiguration | PostToolUse advisory-only misunderstood as enforcement |
| T-4 | A08: Software and Data Integrity Failures | routing-matrix.yaml manipulation without integrity check |
| T-5 | A03: Injection | Crafted Codex responses bypass precondition validation |
| T-6 | A05: Security Misconfiguration | Fail-OPEN policy weaponized via DoS |
| T-7 | A03: Injection | Codex-as-coder writes to canonical paths (file injection) |
| T-7 | A08: Software and Data Integrity Failures | Deny-list bypass → governance file modification |
| T-8 | A08: Software and Data Integrity Failures | Codex CLI binary supply-chain compromise |
| T-9 | A02: Cryptographic Failures | Plaintext stdio transport with no integrity MAC |

### OWASP LLM Top 10 (2025)

| Threat | LLM Category | Mapping rationale |
|---|---|---|
| T-1 | LLM01: Prompt Injection | Classic indirect prompt-injection via Codex output |
| T-2 | LLM06: Sensitive Information Disclosure | Secret/PII leak via audit log channel |
| T-3 | LLM08: Excessive Agency | Over-trust of PostToolUse enforcement posture → excessive LLM agency |
| T-4 | LLM02: Insecure Output Handling | Routing-matrix manipulation → unvalidated dispatch decision |
| T-5 | LLM01: Prompt Injection | Engineered Codex responses masquerade as valid verdicts |
| T-6 | LLM07: System Prompt Leakage (DoS variant) | Fail-OPEN policy exposure via engineered outage |
| T-7 | LLM02: Insecure Output Handling | Codex output requesting writes to canonical paths |
| T-8 | LLM04: Model Denial of Service (supply-chain variant) | Compromised binary defeats all model-level defenses |
| T-9 | LLM02: Insecure Output Handling | In-process interception of Codex output before sanitizer |

---

## §8. Hunting playbooks

> **⏳ Phase 7 follow-up disclaimer:** the playbooks below reference
> several specialized `audit-query.py` sub-commands (`codex-injection-summary`,
> `secrets-leak-scan`, `dispatcher-routes-summary`) and search flags
> (`--where`, `--session`, `--after`, `--action`, `--verbose`,
> `--format jsonl`, `--window 30d`) that are scoped to Phase 7. As of
> v1.16.0 (Phase 6-bis ship), the available audit-query sub-commands
> per `audit-query.py --help`: `summary`, `by-skill`, `compliance`,
> `by-day`, `search` (positional regex only), `since` (positional
> ISO-date), `stats`, `export`, `errors`, `debate`, `plans`, `vetoes`,
> `benchmarks`, `lessons`, `metrics`, `health`, `tokens`, `claims`,
> `prune-restore-ratio`, `architect-outcomes`, `lessons-effectiveness`,
> `weekly-summary`, `spawn-stats`, `by-domain`, plus PLAN-081 Phase 6-bis
> additions: `label`, `fp-rate`, `case-summary`, `codex-writeguard-summary`.
> Phase 7 will materialize the remaining specialized sub-commands; the
> playbook procedures below describe the analytical INTENT and operator
> workflow — concrete commands MAY need adjustment until Phase 7 lands.

### Playbook 1 — Hunt for T-1 (ingress injection escapes)

**Goal:** Identify sessions where Codex output contained injection patterns that were detected but not yet correlated with follow-on anomalous dispatches.

**Steps:**

1. Extract all `pair_rail_codex_injection_detected` events in the target window:
   ```sh
   python3 .claude/scripts/audit-query.py codex-injection-summary \
     --window 7d --format jsonl > /tmp/injection-events.jsonl
   ```

2. For each injection event, extract `session_id` + `timestamp` + `family_ids`:
   ```sh
   jq -r '[.session_id, .timestamp, (.family_ids | join(","))] | @tsv' \
     /tmp/injection-events.jsonl > /tmp/injection-sessions.tsv
   ```

3. For each `session_id` from step 2, look for `pair_rail_case` events occurring AFTER the injection timestamp:
   ```sh
   python3 .claude/scripts/audit-query.py search 'pair_rail_case' \
     --session <SESSION_ID> --after <TIMESTAMP> --format jsonl
   ```

4. Decision criteria:
   - **Case A** following injection: advisory — note for trend tracking.
   - **Case B precondition=false** following injection: **escalate** — Codex attempted to BLOCK but missed preconditions. Possible masking of real finding.
   - **Case F** (fail-OPEN) following injection: **escalate** — injection event + fail-OPEN window = compound risk.
   - No case event within 60s of injection: investigate if dispatcher was bypassed.

5. Escalation threshold: ≥2 injection events in 1h OR ≥1 event with `family_ids` containing `harness_mimicry` → open incident.

6. Verify audit HMAC chain integrity over the flagged records:
   ```sh
   python3 .claude/scripts/audit-query.py search 'audit_hmac_verify_chain' \
     --session <SESSION_ID> --verbose
   ```

---

### Playbook 2 — Hunt for T-7 (codando deny-list bypass attempts)

**Goal:** Identify Codex write attempts targeting canonical-guarded paths, including DRY_RUN mode hits that reveal intent before enforcing flip.

**Steps:**

1. Extract all `pair_rail_codex_denylist_hit` events (both enforcing and dry-run):
   ```sh
   python3 .claude/scripts/audit-query.py search \
     --action pair_rail_codex_denylist_hit \
     --window 30d --format jsonl > /tmp/denylist-hits.jsonl
   ```

2. Separate dry-run hits from enforcing hits:
   ```sh
   jq 'select(.dry_run == true)' /tmp/denylist-hits.jsonl > /tmp/dryrun-hits.jsonl
   jq 'select(.dry_run == false or .dry_run == null)' \
     /tmp/denylist-hits.jsonl > /tmp/enforcing-hits.jsonl
   ```

3. For each enforcing hit, inspect the `target_path` field:
   ```sh
   jq -r '.target_path' /tmp/enforcing-hits.jsonl | sort | uniq -c | sort -rn
   ```
   Any path containing `_lib/`, `hooks/`, `policies/`, `SPEC/`, or `dispatcher/` → **high-severity finding**.

4. Check for path-traversal patterns in `target_path`:
   ```sh
   jq -r '.target_path' /tmp/denylist-hits.jsonl | grep '\.\.' | head -20
   ```
   Any `..` component in `target_path` → **critical — possible glob escape attempt**.

5. Run deny-list coverage contract test to ensure current canonical surface is fully covered:
   ```sh
   python3 -m pytest .claude/hooks/tests/test_deny_list_coverage.py -v
   ```
   FAIL → open P0 incident: canonical path exists without deny-list coverage.

6. Decision criteria:
   - 0 enforcing hits in 30d: nominal.
   - ≥1 enforcing hit on a canonical path: **P0 incident** — open forensic review.
   - ≥3 dry-run hits on canonical paths before enforcing flip: review Phase 5 flip readiness; do NOT flip until root cause identified.
   - Path-traversal attempt: **P0 incident regardless of DRY_RUN mode** — possible active bypass attempt.

---

### Playbook 3 — Hunt for R-NEW-1 (verdict replay)

**Goal:** Identify cases where a previously issued verdict artifact is being replayed against a different session or task context (verdict timestamp mismatch, session reuse, or out-of-order verdict sequence).

**Context:** R-NEW-1 is the risk of a legitimate verdict from session A being replayed as the verdict for session B (e.g. an attacker re-uses a PASS verdict artifact from a benign task to approve a malicious one). Phase 6 verdict artifacts include `session_id` + `task_hash` + `timestamp` + schema-validated structure.

**Steps:**

1. Extract all `pair_rail_promotion` events (Phase 4 gate events) in the target window:
   ```sh
   python3 .claude/scripts/audit-query.py search \
     --action pair_rail_promotion \
     --window 30d --format jsonl > /tmp/promotion-events.jsonl
   ```

2. For each promotion event, cross-reference the `verdict_artifact_hash` against the verdict archive:
   ```sh
   jq -r '.verdict_artifact_hash' /tmp/promotion-events.jsonl | while read hash; do
     find .claude/governance/verdicts/ -name "*.verdict.md" \
       -exec sha256sum {} \; | grep "^${hash}"
   done
   ```
   Any hash that does NOT match an archived verdict file → **P0 — possible forged or replayed verdict**.

3. Check for duplicate `verdict_artifact_hash` values across different sessions:
   ```sh
   jq -r '.verdict_artifact_hash' /tmp/promotion-events.jsonl \
     | sort | uniq -d
   ```
   Any duplicate hash → **escalate** — same verdict used in two promotion events.

4. Validate the `session_id` field in each promotion event matches the `session_id` embedded in the verdict artifact:
   ```sh
   jq -r '[.session_id, .verdict_artifact_hash] | @tsv' \
     /tmp/promotion-events.jsonl | while IFS=$'\t' read sid hash; do
     artifact=$(find .claude/governance/verdicts/ \
       -name "*.verdict.md" -exec grep -l "session_id: ${sid}" {} \;)
     [ -z "$artifact" ] && echo "MISMATCH: session=${sid} hash=${hash}"
   done
   ```
   Any `MISMATCH` line → **P0 incident — session_id in promotion event does not match verdict artifact**.

5. Run `validate-pair-rail-verdict.py` schema check against all verdict artifacts in the archive:
   ```sh
   find .claude/governance/verdicts/ -name "*.verdict.md" \
     -exec python3 .github/scripts/validate-pair-rail-verdict.py {} \;
   ```
   Any FAIL → corrupt or tampered verdict artifact.

6. Decision criteria:
   - All hashes match, no duplicates, all session_ids match: nominal.
   - Duplicate hash: **P0 incident** — open forensic review of both sessions.
   - session_id mismatch: **P0 incident** — possible verdict replay.
   - Schema validation fail: **P1 incident** — verdict artifact corrupted; trace back to emitting session.

---

## §9. Open questions / future iterations

| ID | Question | Owner | Target version |
|---|---|---|---|
| OQ-1 | Should `check_codex_filewrite.py` fail-CLOSED on deny-list YAML parse error? Phase 5 ships fail-CLOSED; validate this holds under fuzzing. | Security | v1.13.1 patch |
| OQ-2 | Phase 5 mutation kill-rate target (≥80%) — is this sufficient for `danger-full-access` mode? Consider ≥95% requirement for that mode specifically. | TDE | v1.17.0 |
| OQ-3 | T-9 (MITM stdio): should the framework emit a startup advisory if `ptrace_scope > 0` is NOT set on Linux? Low-cost runtime check, high-value disclosure. | Security | v1.13.1 patch |
| OQ-4 | Verdict replay (R-NEW-1) hunting playbook (§8 Playbook 3) assumes `verdict_artifact_hash` is in the `pair_rail_promotion` audit event. Confirm this field is emitted by `emit_pair_rail_promotion()` in `_lib/audit_emit.py`. | Engineering | v1.16.0 GA ceremony |
| OQ-5 | T-8 SHA pin: `CEO_PAIR_RAIL_SKIP_BINARY_PIN=1` override is advisory-only. Consider requiring a GPG-signed override declaration (similar to kernel-override env-var pattern) to prevent silent bypass of binary pin in CI environments. | Security | v1.17.0 |
| OQ-6 | MITRE ATT&CK mapping: T-6 (Case-F fail-OPEN DoS) maps to T1499.004 (Application Exhaustion). Verify this is the most specific ATT&CK sub-technique; T1499.002 (Reflection Amplification) may be more applicable for engineered Codex DoS. | TDE | v1.0 errata |
| OQ-7 | Locked-corpus N=15 (Phase 4): 2 fixtures cover T-1 discriminative behavior. Add ≥1 fixture specifically covering T-7 deny-list evasion patterns before Phase 5 enforcing flip. | Engineering | Phase 4-bis ceremony |

---

## §9-bis. Containment-layer placement + MCP-connector boundary (PLAN-135 W4 — D5 + D8)

> Companion: the full harness-vs-hook containment map (per-vector table,
> three-layer framing, native-floor caveats, honest position statement) lives
> in `docs/threat-model.md` §Harness-vs-hook containment map. This section
> places the **pair-rail specifically** in that taxonomy. It is descriptive —
> no pair-rail check is retired on the basis of this mapping (H4 retirement
> mapping is DEFERRED per the PLAN-135 disposition ledger).

### Layer placement of the T-1..T-9 mitigations

Official taxonomy: **rail = model/policy layer; sandbox = environment
layer; redaction/sanitization = content layer.** OS primitives rank above
the custom rail for containment.

| Threat | Primary mitigation | Layer | Owner |
|---|---|---|---|
| T-1 ingress injection | `check_codex_response.py` 3-family scan (PostToolUse, ADVISORY) | content | hook |
| T-2 egress secret leak | `codex_egress_redact.py` single-pass redaction | content | hook |
| T-3 PostToolUse blind spot | documentation discipline + Phase 3 PreToolUse layering | model/policy | hook (structural semantics) |
| T-4 routing-matrix tamper | canonical guard + SHA-pin + schema validation | model/policy | hook |
| T-5 Case-B precondition bypass | catalogue sentinel + precondition validation | model/policy | hook |
| T-6 Case-F fail-open exploitation | audit emit + outage predicate | model/policy | hook |
| T-7 codando deny-list bypass | `check_codex_filewrite.py` PreToolUse deny-list (fail-CLOSED) | model/policy | hook |
| T-8 binary swap / supply-chain | release-time SHA-pin (runtime pre-flight ⏳ Phase 7) | environment (supply-chain) | hook/CI — OS-level package pinning + FS perms rank above |
| T-9 stdio MITM | `ptrace_scope` / SIP host hardening | environment | **OS/Owner-owned, explicitly NOT the framework's** |

**Honest position:** the entire pair-rail is model/policy- plus
content-layer. The §4 "sandbox modes" (`read-only` / `workspace-write` /
`danger-full-access`) are **MCP-server configuration declarations, not OS
enforcement** — §4 already states the framework cannot enforce sandbox mode
at the OS level; a misconfigured MCP server silently upgrades its own
privileges. The first true environment-layer primitive in the framework is
the S4 sandbox fragment (PLAN-135 W2 — **PENDING, opt-in, not default-on**).
Until it lands — and even after, given opt-in — containment of a compromised
reviewer process is the host's job, not the rail's.

**Egress-substitution above redaction (T-2 amendment):** T-2's single-pass
redaction is content-layer — it scrubs secrets that already reached the
text. The gold tier above it is **egress-substitution (agent-blind
secrets)**: the model only ever sees an opaque placeholder and the real
credential is substituted into the outbound request at egress (the Anthropic
vault `environment_variable` mechanism). Substitution makes the leak
structurally impossible rather than pattern-detected. Not shipped in the
framework — named target for the credential surfaces the rail touches.

### MCP-connector boundary (D8 — the rail presupposes the harness path)

Every T-1..T-9 mitigation presupposes that Codex MCP traffic traverses the
**local harness** stdio path (§3 state machine): that is what makes
`check_pair_rail.py`, `check_codex_filewrite.py` and
`check_codex_response.py` fire at all.

**API-side `mcp_servers` in a raw Messages request emits NO PreToolUse.**
A script, instrument, or live adapter that calls the Messages API directly
with an `mcp_servers` connector executes MCP tool calls on the provider side
of the API boundary — the entire pair-rail (ingress scan, egress redaction,
deny-list, Cases A-F, audit emit) is structurally bypassed, and nothing
lands in `audit-log.jsonl`.

Decision rule (normative — full text in `docs/threat-model.md` §D8):
route MCP through the harness when governance matters; when the connector is
unavoidable, mirror the PLAN-133 egress allowlist into the request (server
URLs + minimal tool surface) and declare the call rail-ungoverned in the
plan/review artifact. **A connector-side Codex call never satisfies the
ADR-145 cross-model VETO** — cross-model review counts only on the governed
rail.

---

## §10. References

- ADR-052 — VETO floor invariant.
- ADR-082 — mitigated rail (Sub-agent dispatch via general-purpose).
- ADR-106 — Codex MCP adapter contract (PostToolUse advisory-only).
- ADR-107 — Pair-Rail mandatory L2+ + asymmetric VETO (ACCEPTED Phase 3).
- ADR-108 — cross-LLM VETO floor (ACCEPTED Phase 3).
- ADR-110 — Codex PreToolUse enforcement.
- ADR-111 — locked-corpus governance (ACCEPTED Phase 4).
- PLAN-075 — Pair-Rail Multi-LLM v5 (DONE 2026-05-09).
- PLAN-081 — Pair-rail phases 2-6 + full Phase 1 (this plan; v1.16.0 GA target).
- SPEC/v1/adapters.schema.md — Hook adapter ABI contract.
- SPEC/v1/audit-log.schema.md — audit-log schema (v2.23 registers `pair_rail_codex_injection_detected` + `dispatcher_route` + `pair_rail_case` + `pair_rail_promotion`).
- docs/PAIR-RAIL-VERDICT-MATRIX.md — Asymmetric coverage reference (Phase 6 deliverable).

---

*Generated by CEO (PLAN-081 Phase 6-bis, 2026-05-11). v0.1 Phase 1-full (Session 99 2026-05-09) · v0.2 Phase 2 dispatcher (Session 100 2026-05-10) · v0.3 Phase 3 asymmetric VETO (Session 100 2026-05-10) · v1.0 Phase 6-bis final consolidation (Session 101-cont 2026-05-11). Supersedes all prior versions. GA reference for v1.16.0.*
