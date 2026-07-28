I'll review PLAN-163 and its debate consensus against the cited repo evidence, focusing on vacuous checks, path/line accuracy, gate ordering, and the two security-critical items.Verifying the plan's key file:line claims and security surfaces against the repo.Cross-checking one more install-oracle surface and the depth-fence advisory default before writing the verdict.VERDICT: REJECT

F1. **P1** — G4/T2 still scopes the 2.1.214 exit-2 hard-block class to three **unwired CLI scripts**, so the planned fix does not close the claimed session-block surface.  
**Claim:** accidental `argparse`/`SystemExit(2)` in `check_harness_config`, `emit_architect_outcome`, `policy_dispatch` is the new session hard-block surface (G4/T2.1–T2.3, CF-5).  
**Evidence:** zero of the 44 wired hooks import argparse; those three scripts are **NOT-WIRED** (`settings.json` hook graph; only `check_harness_config` appears as a comment + `validate.yml` CLI). On the Claude path the shim is plain `exec` (`.claude/hooks/_python-hook.sh:409-413`), so only **wired** hook exit codes reach the harness. Intentional blocks already use stdout JSON + Python `return 0` (e.g. `check_bash_safety.py:2832`).  
**Fix:** retarget the exit-code oracle at **derived wired hooks**; demote the three argparse scripts to CLI/CI hygiene only; assert that deny remains decision-JSON + shim-mapped, and that accidental non-zero/no-decision paths stay fail-open.

F2. **P1** — GATE-V2 is vacuous if implemented as “`pair_rail` row green.”  
**Claim:** `failopen_rail_liveness_7d` `pair_rail` must be healthy (≥1 risky healthy review) before W3 pack review (GATE-V2 / CF-8).  
**Evidence:** `ceo-boot.py:1902-1904` classifies **zero expected AND zero outcomes → GREEN (vacuous-but-true)**. A quiet 7d window greening the row satisfies “SAUDÁVEL” without any review.  
**Fix:** implement GATE-V2 as explicit predicates `healthy >= 1` AND `failopen == 0` (and no outstanding expected `review_id`), not overall green / “no signal.”

F3. **P1** — Success-criteria gate order contradicts GATE-PIN / CF-4.  
**Claim:** honor gates “liveness → pin ceremony → pack review under new pin” (Success criteria:286-287) while GATE-PIN requires pin **before** W3 review (Gates:77-79; CF-4).  
**Evidence:** pin file currently attests launcher `codex.js` (`codex-cli-binary-sha256.txt:32-36`); live payload differs (see F4). Liveness collected under the old pin is not evidence under the new attestation target.  
**Fix:** declare order **GATE-PIN → verify rail under new pin → re-establish ≥1 healthy review (GATE-V2) → W3 pack review → pack GPG**.

F4. **P1** — T5.2 correctly diagnoses launcher-vs-payload, but under-specifies enforcement: re-pin alone leaves V2 unattested at runtime.  
**Claim:** amend ADR-111 to pin resolved payload; sha-pin is the supply-chain gate; nice-to-have per-invoke probe (T5.2).  
**Evidence (fresh proof):** pin `134063e1…` == launcher `/…/@openai/codex/bin/codex.js`; native payload `/…/vendor/…/bin/codex` sha `80a3933d…` (version 0.144.6). `pair-rail-gate.sh:139-149` Gate 4 is still **STUB** (no sha compare). `check_pair_rail.py` resolves PATH / invokes codex but does **not** compare against `codex-cli-binary-sha256.txt`. Enforcement found only at release verdict step (`release.yml:633,694`).  
**Fix:** (1) pin the binary the launcher actually spawns, multi-arch; (2) implement real preflight compare in `pair-rail-gate.sh` (and/or mandatory invoke-time advisory→blocking path); (3) test `pin ≠ codex.js` and `pin == native`; (4) do not treat release metadata-only match as live attestation.

F5. **P1** — Hardcoded smoke-install “registrations = 48” will break adopter install CI.  
**Claim:** T3 46→48; T5.4 post-install/post-upgrade oracles require registration count **48**.  
**Evidence:** dogfood `.claude/settings.json` = **46** regs; `templates/settings/settings.base.json` = **45** (missing dogfood-only `PreToolUse/Bash/check_cost_envelope.py`). Install copies templates (`install.sh:1448-1499`). After +2 events: dogfood **48**, installed tree **47**.  
**Fix:** derive expected count from the artifact under test; or ship the missing registration into templates first; never hardcode a single 48 for both dogfood and install/upgrade oracles.

F6. **P1** — DirectoryAdded hardblock-floor design is sound for the blockable path, but the notification-only fallback is not implementable as written.  
**Claim:** if notification-only, enforcement migrates to PreToolUse write-guards denying Write/Edit under mid-session added roots (T3.1).  
**Evidence:** no current DirectoryAdded/add-dir handling in hooks; canonical guards are project-relative; plan never defines the session registry (where added roots are stored, schema, TTL, symlink/`realpath` policy, fail-closed on unparseable paths per CLAUDE.md §4 security matchers).  
**Fix:** before promising migration: (a) probe blockability; (b) specify session store + canonicalization + fail-closed parse; (c) unit fixtures with `TestEnvContext`; (d) keep hardblock-floor independent of env only if DirectoryAdded can block.

F7. **P2** — `STALE_RE += claude-opus-4-1` is born-green today.  
**Claim:** execute STALE_RE expansion for retirement 2026-08-05 (T1.8 / CF-11).  
**Evidence:** repo-wide search finds **zero** `claude-opus-4-1` hits; so the expanded scan cannot go red-first.  
**Fix:** plant a deliberate negative fixture outside allowlists for red-first, or mark the expansion as forward-looking and gate on an independent presence/routing oracle that is red now.

F8. **P2** — T6 closeout count list is incomplete and will leave count gates red.  
**Claim:** CLAUDE.md must update hooks on disk 55→57 and registrations 46→48 (T6.4).  
**Evidence:** CLAUDE.md:53 also states **44 wired**; README/npm-README/ARCHITECTURE use 44 wired / 46 regs. +2 hooks ⇒ **44→46 wired** as well.  
**Fix:** closeout must update the full triple (on-disk, wired unique scripts, registrations) across CLAUDE.md + badge surfaces, all derived from disk.

F9. **P2** — Missing adopter precondition for shipping `DirectoryAdded` (2.1.219+) into templates while ledger/adopters may be older.  
**Claim:** wire Notification + DirectoryAdded into settings **and templates** (T3.3 / CF-7).  
**Evidence:** substrate-watch last_seen CC is **2.1.198** (`.claude/scripts/substrate-watch.json`); DirectoryAdded attributed to 2.1.219 (G7). No plan probe that older harnesses ignore unknown hook event keys vs fail settings load.  
**Fix:** probe unknown-event tolerance on a floor version; document minimum CC for these registrations or feature-gate template emission until T5.1’s 2.1.220 pin is the supported floor.

F10. **P2** — T5.2 “payload” is ambiguous across multi-binary package contents.  
**Claim:** attest “payload resolvido (sha por-arch do binário nativo … ou manifest-hash npm)” (T5.2).  
**Evidence:** under `@openai/codex@0.144.6` there are multiple large binaries (`bin/codex`, `codex-code-mode-host`, `codex-path/rg`). Only one is the launcher’s spawn target.  
**Fix:** name the exact relative path the launcher spawns; pin that path per arch; optional secondary integrity for supporting binaries; prefer also recording npm package integrity as defense-in-depth.

F11. **P3** — T1.6 groups non-pricing surfaces under the presence-based pricing oracle with stale line semantics.  
**Claim:** presence fix includes `audit_log.py:890-917`, `ceo-cost.py:62-76`, `budget-summary.py:94-109` alongside `_PRICING_PER_MTOK` (T1.6).  
**Evidence:** `_PRICING_PER_MTOK` lacks opus-4-8/fable-5 (`audit-telemetry.py:39-45`) — oracle red is correct. But `ceo-cost.py:69-76` and `budget-summary.py:98-109` **already** contain `claude-opus-4-8`; `audit_log.py:890-917` is a **role→model** map, not pricing; `cost-table.yaml:65-71` already has fable-5/opus-4-8.  
**Fix:** split checks: (pricing presence red-now) vs (routing/role map updates gated on OQ1).

F12. **P3** — Hardblock-floor “project-dir ancestors” can break legitimate monorepo `/add-dir` without a residual note.  
**Claim:** floor includes ancestors of the project dir (T3.1 / CF-9).  
**Evidence:** for a nested package project, monorepo root is an ancestor; floor would deny that add even with hardblock env off.  
**Fix:** document residual + optional Owner allowlist for monorepo root, or narrow floor to `$HOME`, `~/.claude/`, and foreign `**/.claude/**` trees only.

---

**Security-critical assessment (fresh eyes)**

**T5.2 codex sha-pin (launcher vs payload):** Defect is real and live-proven (pin matches 7KB `codex.js`; native arm64 binary differs; 0.144.6 installed). Semver already admits 0.144.6. Plan correctly re-scopes away from semver bump theater. **Still REJECT-grade:** without unstubbing preflight/enforce-on-invoke, ADR-111 re-pin is a stronger **label**, not a stronger **control**. Multi-arch payload path must be named; release-only metadata compare is insufficient for the “V2 truth gate” claim.

**T3.1 DirectoryAdded hardblock-floor:** Threat model is right (`/add-dir` can expand write perimeter outside project HMAC/canonical rails). Floor for `$HOME` / `~/.claude/` / foreign `.claude` is the right fail-closed default **if** the event is blockable. **Still REJECT-grade until:** blockability probe is a hard gate; notification-only path has a concrete mid-session registry + fail-closed path canonicalization; template registration counts are not hardcoded to dogfood’s 48; unknown-event behavior on older CC is checked before template ship.
