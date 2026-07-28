I'll re-read the current PLAN-163 plan and the round-2 reject reports, then verify F1–F3 and residual findings are closed.Next I'll pull the T5.2 / T3 / ADR sections from the plan and cross-check them against the live pin and rail code.I'll verify the plan claims against the live code surfaces and scan for any remaining defects.Cross-checking a few final residual nits, then issuing the round-3 verdict.VERDICT: APPROVE

Round-3 re-read of `.claude/plans/PLAN-163-substrate-uplift.md` (v4) against `grok-r2.md` F1–F3 and `codex-r2.md` #1–#7. Prior REJECT gates are closed in plan text; residual items below are non-blocking P3 nits.

### Required closures (r2 → v4)

| Gate | Status | Evidence |
|---|---|---|
| **F1 T5.2 control** | Closed | Platform optional package path + measured darwin-arm64 example (`@openai/codex-darwin-arm64/vendor/aarch64-apple-darwin/bin/codex`); launcher-mirroring `findCodexExecutable` helper; launcher/`$(which codex)` hash = ceremony **failure** class; per-arch versioned pin manifest; consumers enumerated (`validate-pair-rail-verdict.py:323-380`, release.yml envelope, Gate 4, tests, **`check_pair_rail.py`**); **mandatory blocking** native-payload sha compare on live rail before subprocess; pin==`codex.js` fails / pin==native passes; release metadata ≠ invoke attestation (`:276-307`, Success `:384-386`). |
| **F2 ADR identity** | Closed | Explicit: ADR-120 = PII; false 111→120 is ledger inconsistency; **NEW ADR** owns payload-pin + runtime enforcement + supersedes locked-corpus pin sections; repair ADR-111 frontmatter/index; **never** amend ADR-120-pii (`:297-304`, Success `:385-386`). |
| **F3 T3 notification-only** | Closed | DirectoryAdded still wired as **observer-WRITER** → `.claude/state/session-roots.json`; named PreToolUse consumers (Edit\|Write\|MultiEdit write-guards); absolute-path + `realpath` matching; fail-closed unparseable paths; state non-commit/gitignore policy; red-first write under registered root (`:215-227`, Check `:241-245`). |

### Codex r2 residual trace

| # | Status |
|---|---|
| 1 speed/throughput claims | Closed (compliance note `:61-66`; no framework speedup benefit language) |
| 2 `FALLBACK_MODEL_CHAIN` + generator split | Closed in T1 (`:128-138`); see P3-1 for OQ typo |
| 3 shim = pure `exec` | Closed in T2 body (`:180-192`); see P3-2 for stale Check wording |
| 4 per-arch pin + live rail | Closed (T5.2 a–c) |
| 5 baseline-aware upgrade | Closed (`:311-320`) |
| 6 ADR NEW + ledger repair | Closed (T5.2 d) |
| 7 independent ADR-149 mirrors | Closed (`:139-143`) |

Grok r1 table items previously open (F4/F10) are absorbed into the F1 closure above.

---

### Residual P3 nits (non-blocking)

1. **OQ1 stale identifier** (`:353`): still says ``FALLBACK_CHAIN``; authoritative block is ``FALLBACK_MODEL_CHAIN`` (T1 `:129-130`, ADR-149:89-93). Prefer exact id in the soak option so (b-soak) cannot invent a second symbol.

2. **Stale “shim-mapping” summary** (`:204`, `:375`): T2 correctly states pure `exec` with no exit remapping; Check/Success still say `schema+exit+shim-mapping`. Drop “shim-mapping” so oracle authors do not reintroduce the r2#3 false contract.

3. **Preflight path typo** (`:293`): writes `scripts/local/pair-rail-gate.sh`; on-disk path is `.claude/scripts/local/pair-rail-gate.sh`.

4. **Per-arch schema example optional but useful** (`:284-289`): migration + consumers are mandated; a one-block example (arch key = launcher `targetTriple`, field layout, how scalar `tool_versions.codex_cli_binary_sha256` selects a map entry) would reduce implementer variance inside the NEW pin ADR—not required to re-open F1.

5. **ADR-181 number jump** (`:169`): max on-disk ADR is **165**. Unless 166–180 are reserved, prefer next free monotonic id for the Claude-5 refresh ADR (pin ADR remains “ADR NOVO” without a premature number—fine).

6. **T5 Check vs Success** (`:326-329` vs `:384-386`): Check bullets stress Gate 4 sha unstub; Success already requires live-rail blocking compare. Adding the live-rail oracle to the T5 Check line avoids a “Gate-4-only” local definition of done.

7. **State gitignore precision** (`:219-220`): plan declares `.claude/state/` non-commit; repo currently ignores path-scoped entries (e.g. `.claude/state/turbo/`). Prefer an explicit ignore for `session-roots.json` (or a dedicated subdir) rather than assuming a blanket `.claude/state/` rule already exists.

---

**Bottom line:** v4 is plan-complete for the r2 REJECT bar. F1 control end-to-end, F2 pin ADR routing, and F3 observer-writer path are specified tightly enough to execute under GATE-PIN → GATE-V2 → pack review → GPG. P3 nits can land as drive-by cleanups in the same execution pack; they do not justify another REJECT cycle.
