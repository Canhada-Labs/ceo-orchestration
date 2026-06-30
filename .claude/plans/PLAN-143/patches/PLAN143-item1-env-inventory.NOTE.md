<!-- last-reviewed: 2026-06-20 -->
# PLAN-143 item-1 — env-inventory regen (DATA regen, Owner-run)

> **Why this is a NOTE, not a `.patch`.** Item-1 is a **data regeneration**,
> not a code change. The fix is to re-run the inventory generator in WRITE
> mode so `.claude/scripts/env-inventory.json` re-captures the current live
> `CEO_*` / `CLAUDE_*` / `ANTHROPIC_*` token census. That file lives under the
> GPG-guarded `.claude/scripts/` tree, so the regen must be run + committed by
> the Owner — there is no clean hand-authored unified diff to stage (the JSON
> body is mechanically derived). This note records the exact command, the live
> drift state, and the per-token classification the round-1 debate required
> **before** the regen runs.

## Live drift state (captured 2026-06-20)

`python3 .claude/scripts/env-inventory-check.py --check --json` → `status=drift`:
**25 NEW**, **0 stale**. The inventory body was last generated 2026-06-13; the
`TOKEN_RE` scanner is a documented SUPERSET (any `CEO_*`/`CLAUDE_*`/`ANTHROPIC_*`
token), so "NEW" means "appears in source but not yet in the census", NOT "new
unreviewed bypass surface."

## Classification of the 25 NEW tokens (round-1 §2 + AC `[P1][env-inventory]`)

Each NEW token is classified `{consumed | forbidden-family-mention | descriptor}`.
Evidence column = the file(s) the scanner found the token in.

### A. `forbidden-family-mention` — deny-list tokens, ZERO `getenv`/`environ` consumers (do NOT enrol as intended surfaces)

The five governance kill-switches appear ONLY inside
`.claude/hooks/_lib/env_persist_allowlist.py` — the deny-list whose job is to
EXCLUDE them from persistence. The bypass class is already governed by **ADR-143**.
Per round-1 CF-1/D3 these are census mentions, NOT blessed surfaces, and get **NO new ADR**.

| Token | Evidence |
|---|---|
| `CEO_TRUST_BYPASS` | `env_persist_allowlist.py` |
| `CEO_CANONICAL_GUARD_DISABLE` | `env_persist_allowlist.py` |
| `CEO_ALLOW_NO_VERIFY` | `env_persist_allowlist.py` |
| `CEO_HOOKS_DISABLE` | `env_persist_allowlist.py` |
| `CEO_SKIP_HOOKS` | `env_persist_allowlist.py` |

### B. `consumed` — genuinely live `getenv`/`environ` consumers (classify; the security-adjacent ones get the real review)

| Token | Evidence | Note |
|---|---|---|
| `CLAUDE_ENV_FILE` | `env_persist_allowlist.py`, `check_setup_verification.py`, `settings.json` | **Security-adjacent (file-path env surface) — give it the real review per AC.** |
| `ANTHROPIC_MODEL` | `effective_config.py`, `ceo-boot.py` | model-routing trio |
| `ANTHROPIC_SMALL_FAST_MODEL` | `effective_config.py`, `ceo-boot.py` | model-routing trio |
| `ANTHROPIC_DEFAULT_OPUS_MODEL` | `effective_config.py` | model-routing trio |
| `CEO_BASH_FORCE_PUSH_REWRITE` | `check_bash_safety.py` | bash-safety opt-in |
| `CEO_BUDGET_QUOTA_HINT` | `check_budget.py` | budget hint |
| `CEO_CACHE_CONTROL_AUTO_DISABLE` | `adapters/live/claude.py` | cache-control toggle |
| `CEO_COUNT_TOKENS_PREFLIGHT` | `adapters/live/claude.py` | preflight toggle |
| `CEO_CONFIG_CHANGE_GUARD` | `check_config_change.py`, `settings.json`, `upgrade.sh` | guard toggle |
| `CEO_PROTOCOL_SYNC_CASCADE` | `check_protocol_semver_cascade.py` | cascade toggle |
| `CEO_SETUP_VERIFICATION` | `check_setup_verification.py`, `settings.json`, `upgrade.sh` | setup-verify toggle |
| `CEO_STRUCTURED_OUTPUTS` | `benchmark-judge.py` | judge toggle |
| `CEO_VERIFY_AFTER_EDIT_NO_CONTINUE` | `accel_dispatch.py`, `verify_after_edit.py` | verify-after-edit toggle |
| `CLAUDE_BASH_MAINTAIN_PROJECT_WORKING_DIR` | `settings.json`, `templates/settings/settings.base.json` | harness env passthrough |
| `CLAUDE_CODE_SUBPROCESS_ENV_SCRUB` | `settings.json`, `templates/settings/settings.base.json` | harness env passthrough |

### C. `descriptor` — lifecycle/census descriptors (not bypasses, not security-adjacent)

| Token | Evidence |
|---|---|
| `CEO_COMPACTION_CONTINUITY` | `check_postcompact_reinject.py`, `check_precompact_continuity.py`, `settings.json` |
| `CEO_SUBAGENT_LIFECYCLE` | `check_fluency_nudge.py`, `check_subagent_start.py`, `settings.json` |
| `CEO_SUBAGENT_LIFECYCLE_STATE_DIR` | `check_fluency_nudge.py`, `check_subagent_start.py` |
| `CEO_SUBAGENT_TRANSCRIPT_ROOT` | `check_fluency_nudge.py` |
| `CEO_FINISH_CEREMONY` | `scripts/local/finish-plan135.sh` |

## Regen command (Owner-run; LAST step, after classification above is recorded)

```bash
cd /path/to/ceo-orchestration

# 0. (pre-flight) confirm the drift is still 25-NEW / 0-stale before regen
python3 .claude/scripts/env-inventory-check.py --check --json

# 1. WRITE mode — re-derive .claude/scripts/env-inventory.json from live source
python3 .claude/scripts/env-inventory-check.py --generate

# 2. Verify the regen cleared the drift
python3 .claude/scripts/env-inventory-check.py --check     # expect exit 0, status=current

# 3. Disjointness invariant (SK-1): the descriptive census is NOT a persist
#    allowlist — no kill-switch/escape-hatch name may land in any persist
#    allowlist. This test MUST still pass post-regen:
python3 -m pytest .claude/hooks/_lib/tests/test_env_persist_allowlist.py -q
```

## npm/ mirror (round-1 SK-4)

`.claude/scripts/env-inventory.json` has an `npm/.claude/` twin. After the regen,
either run the tree-sync step or re-run `--generate` against the `npm/` mirror so
the next `nightly-hygiene` sweep does not flag fresh `.claude/` ↔ `npm/.claude/`
drift.

## Acceptance check (AC `[P1][env-inventory]`)

- [ ] All 25 NEW tokens classified (done above; the five kill-switches recorded
      as `forbidden-family-mention`, NOT enrolled as intended surfaces).
- [ ] `CLAUDE_ENV_FILE` given the real security-adjacent review.
- [ ] `env-inventory-check.py --check` returns `status=current` (0 NEW, 0 stale).
- [ ] `test_env_persist_allowlist.py` still passes (disjointness preserved).
- [ ] npm/ mirror re-synced.
