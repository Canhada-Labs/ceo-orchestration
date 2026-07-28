I'll re-read the revised PLAN-163 and both round-1 review reports, then verify each of my F1–F12 resolutions and re-check T5.2/T3.Checking residual T5.2/T3 surfaces and a few plan claims against the repo so the re-review is evidence-based.VERDICT: REJECT

Round-2 cross-check: **F1, F2, F3, F5, F6 (design skeleton), F7, F8, F9, F11, F12** are genuinely applied in the revised text. **F4 / F10 remain only partially closed**, and the codex-F12 absorb introduced one **new** decision-record defect. Fresh adversarial focus on T5.2 / T3 below.

---

### F1. **P1** — T5.2 still under-specifies the *control*: wrong payload path + wrong resolution algorithm + preflight-only enforcement site
**Claim:** T5.2 / G13 / GATE-PIN will attest the resolved native payload, unstub Gate 4, and turn V2 supply-chain into a **control** (not a label).  
**Evidence:**
1. **Wrong path.** Plan names `node_modules/@openai/codex/vendor/<arch>/…/codex`. Live 0.144.6 launcher resolves via the **platform optional package**, not a vendor tree under the main package:
   - launcher: `/opt/homebrew/lib/node_modules/@openai/codex/bin/codex.js` sha `134063e1…` (matches pin)
   - native: `…/@openai/codex/node_modules/@openai/codex-darwin-arm64/vendor/aarch64-apple-darwin/bin/codex` sha `80a3933d…`
   - main package `…/@openai/codex/vendor` **does not exist**
2. **Resolution algorithm omitted.** Pin file + threat-model ceremony still document `shasum -a 256 $(which codex)` (hashes launcher content via symlink). Unstubbing Gate 4 without mandating launcher→`findCodexExecutable`-equivalent resolution either (a) re-pins the launcher or (b) always fails once the pin holds the native sha. Multi-arch pin **format** is still unspecified (file is currently a single 64-hex line).
3. **Enforcement site is not the live rail.** `pair-rail-gate.sh` is a **manual/local** preflight (`scripts/local/…`); it is **not** registered in `.claude/settings.json`. Live reviews go through `check_pair_rail.py:_resolve_codex_bin` / `_invoke_codex_review`, which still has **zero** pin compare. Plan language is only “`pair-rail-gate.sh` Gate 4 … e caminho invoke-time **advisory→blocking definido**” — no hard requirement that the **call site** fail-closed on pin mismatch before `subprocess` (threat model T-8 residual remains: mid-session PATH/binary swap after optional preflight).  
**Fix:** (a) name the spawn target as the platform package path the launcher actually uses (`@openai/codex-<platform>/vendor/<targetTriple>/bin/codex[.exe]`), with a resolution helper that mirrors the launcher; (b) redefine pin schema (per-arch map or multi-line) + ceremony text so `which codex`/launcher hash is an explicit **failure** class; (c) unstub **and** mandate blocking compare on the live rail path (`check_pair_rail` and/or adapter) of the resolved native payload (preflight alone is insufficient for the “control” claim); (d) keep the test that pin==`codex.js` fails and pin==native passes; (e) treat release metadata-only match as non-attestation of live invoke.

### F2. **P2** — Pin ADR chain points at the wrong successor identity (new defect from absorbing codex r1 F12)
**Claim:** T5.2(c) / Success criteria: “`ADR-111` está SUPERSEDED por ADR-120 — emendar o registro autoritativo … ou ADR novo.”  
**Evidence:** On disk, `ADR-120-pii-core-promotion.md` is **PII core promotion** (rename of the *other* ADR-111), not locked-corpus / pin governance. `ADR-117` + `adr/README.md` document that **locked-corpus kept id 111** and PII moved to 120. `ADR-111-locked-corpus-governance.md` frontmatter says SUPERSEDED→120, but that is a **ledger inconsistency**, not proof that ADR-120 owns the pin stack. An implementer following the plan literally can amend the **PII** ADR for a codex-binary ceremony.  
**Fix:** Do not treat “ADR-111 → ADR-120” as the pin authority. Either (i) repair ADR-111 status vs actual successor if one exists, (ii) land a **new** ADR that owns payload-pin + runtime enforcement and supersedes the locked-corpus pin sections, or (iii) explicitly amend `ADR-111-locked-corpus-governance.md` after reconciling its SUPERSEDED label — never route pin substance into ADR-120-pii.

### F3. **P2** — T3 notification-only path: registry store specified, writer path still vacuous
**Claim:** If `DirectoryAdded` is notification-only, enforcement migrates to PreToolUse write-guards using `.claude/state/session-roots.json` (schema, `session_id`, TTL, `realpath` fail-closed).  
**Evidence:** Plan specifies store shape well (r1 F6 largely met) and keeps blockability as a hard gate. But it never names a **must-wire** DirectoryAdded **observer** that *writes* the registry when the event cannot block. Without that writer, PreToolUse deny-under-registered-roots is born-green. Also unspecified: gitignore / non-commit policy for `.claude/state/`, which write-guards are extended, and absolute-path matching for roots outside the project (current canonical guards are project-relative).  
**Fix:** If notification-only: (1) still register DirectoryAdded → `check_directory_added.py` (or sibling) as **observer-writer** of session-roots; (2) name PreToolUse surfaces that consume the registry; (3) absolute-path / realpath matching rules; (4) state path under existing project-state conventions + gitignore. Blockable path can keep the floor as written.

---

### F1–F12 resolution table (grok r1)

| ID | Status | Notes |
|---|---|---|
| F1 argparse/wired | **Resolved** | T2 oracle = derived wired set; CLI trio out of scope; harness-config exit≠0 preserved |
| F2 GATE-V2 vacuous | **Resolved** | Explicit `expected≥1`, terminal outcome, `healthy≥1`, `failopen==0` under **new** pin |
| F3 gate order | **Resolved** | GATE-PIN → GATE-V2 → pack review → GPG |
| F4 T5.2 control | **Open (P1)** | See F1 above |
| F5 reg count 48 | **Resolved** | 48 dogfood / 47 template; oracles derive from artifact |
| F6 DirectoryAdded registry | **Mostly resolved** | Blockability hard-gate + schema; residual writer vacuity → F3 |
| F7 STALE_RE born-green | **Resolved** | Planted negative fixture + allowlist deltas first |
| F8 count triple | **Resolved** | on-disk 55→57, **wired 44→46**, regs 46→48 |
| F9 version floor | **Resolved** | Probe / raise floor; template emission feature-gated |
| F10 payload ambiguity | **Open (P1)** | Path named but incorrect; multi-binary still not schema’d → F1 |
| F11 pricing vs routing | **Resolved** | Presence red scoped; routing map OQ1; no false reds |
| F12 monorepo ancestors | **Resolved** | Ancestors removed from floor; residual + Owner allowlist |

Codex-lane absorbs (ADR-149 regen, upgrade migration, no speed claims, mirror tests, etc.) look correctly applied; **except** the ADR-111/120 identity error (F2).

---

### Fresh adversarial: T3 (prior REJECT-grade)
**Mostly closed for plan-grade.** Blockability is a hard gate; floor narrowed (`$HOME`, `~/.claude/`, foreign `**/.claude/**`); monorepo ancestors out; counts 47/48; version-floor before template ship; fail-closed parse. Remaining gaps are **P2** (F3 writer path / state hygiene), not a new REJECT-grade perimeter hole **if** the blockable branch is proven first.

### Fresh adversarial: T5.2 (prior REJECT-grade)
**Still REJECT-grade.** The plan correctly diagnoses launcher≠payload and STUB Gate 4, but an implementer can still ship a stronger **label**: re-pin a wrong path, unstub a **manual** preflight with the old `which codex` hash algorithm, leave live `check_pair_rail` unattested, and call the supply-chain gate “closed.” Until resolution algorithm + pin schema + **mandatory live-rail** (or equivalently automatic) native-sha compare are unambiguous, the V2 truth-gate claim is not met.

---

**Required for APPROVE:** close F1 (T5.2 control end-to-end) at minimum; F2/F3 as P2 should not re-open the prior T3 REJECT if F1 is solid, but F2 should be fixed before any pin ADR ceremony language lands.
