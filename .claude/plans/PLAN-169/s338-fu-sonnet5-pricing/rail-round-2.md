# sonnet5-pricing-fu — rail codex round 2 (same tree as round 1: HEAD dc72bf1 + fable51 + this pack, 2026-09-01 S338)

Rail-Verdict: CHANGES-REQUESTED (2 P2 — both verified REAL; #1 cured in code + 2 tests, #2 cured in the pointer text, the dated record itself deliberately untouched)

Command (from INSIDE the shadow, stdin `</dev/null`):
`codex exec review --uncommitted --skip-git-repo-check -c sandbox_mode="workspace-write"`
Raw output: `codex-r2.txt` [saída bruta, NÃO versionada — scratchpad S338 `codex-logs/s338-fu-sonnet5-pricing/`] (9.809 lines, `codex rc=0`). Why a round 2 on an
unchanged tree: round 1 was clean, and a single clean round proves the surface
the reviewer happened to look at, not the deliverable — round 2 looked at
different neighbours and found two real items round 1 missed.

## Tree integrity

`git diff | shasum -a 256` BEFORE = AFTER =
`3f706c1446035ef02cc67251393a020d6fb669647eeb98f40d0b21cbec4cbcb1` -> **TREE-INTACT**;
no untracked files (only the gitignored `.pytest_cache/` from codex's pytest).

## Findings (quoted as DATA; each verified against the files)

1. **[P2, REAL — latent] `build-canonical-models.py:348` generic `sonnet-[3-9]`
   tier at $3/$15.** Verified: `_MM_TIERS` (`:344-350`) is the regex tier table
   `reconcile()` (`:362-407`) diffs every canonical row against — five fields
   (input, cache-write 5m/1h, cache-read, output). `claude-sonnet-5` matched
   the generic sonnet tier `(3.0, 3.75, 6.00, 0.30, 15.0)`. Latent because
   `.claude/data/canonical_models.json` carries NO sonnet-5 row (Owner-run
   models.dev refresh only, PLAN-152 deferred item 7) — but the day that
   refresh lands, the $2/$10 row would raise five FALSE divergences, and with
   this pack's cost-table at 2.00/10.00 the repo would carry two disagreeing
   pricing mirrors. The comment says the table mirrors
   `PLAN-128/wave1/measure_multiplier.py MODEL_PRICING`; that file does not
   exist anywhere in-tree (`find` — 0 hits), so the cure is local.
   **CURE (script edits 20-21):** a Sonnet-5-specific tier
   `(r"sonnet-5(?:\D|$)", (2.0, 2.50, 4.00, 0.20, 10.0))` inserted BEFORE the
   generic sonnet tier (first match wins; cache multipliers unchanged per the
   pricing page: 1.25x / 2x write, 0.1x read), sourced in-comment; two tests in
   `TestReconcile` (`test_build_canonical_models.py`):
   `test_mm_tier_sonnet5_is_standard_2_10_and_generic_sonnet_kept` (bare id,
   dated suffix, `[1m]` suffix -> the 5-tuple; Sonnet 4.6 keeps the generic
   tier) and `test_reconcile_sonnet5_row_at_standard_rate_is_clean` (a synthetic
   canonical Sonnet 5 row at $2/$10 + standard cache columns reconciles with
   ZERO findings against BOTH the shipped cost-table.yaml and the tier table).
   Positive control (rewritten tests vs uncured sources): both RED —
   `_mm_tier_for` returned the generic tuple; `reconcile` returned 7 findings
   (5 tier + 2 cost-table). Green after the cure.
2. **[P2, REAL — scope-bounded] `docs/CEO-MODEL-ROUTING.md:74` points readers
   at `docs/substrate-adopt-2026-08.md`, whose G2 row (`:37`) still says
   "intro pricing $2/$10 through 2026-08-31 (then $3/$15)" and that the three
   rollups price the flip in-row.** Verified: both statements are false after
   this pack. The brief for this pack forbids editing
   `docs/substrate-adopt-2026-08.md:37` (DATED historical adoption record —
   same class as ADR-157, which recorded the $3/$15 sticker at its date), so
   the codex option "update that row" is out of scope, and "append an explicit
   supersession" would also edit the dated record. **CURE (script edit 13,
   replacement text changed):** the routing-table cell now states that the
   pointer target is a DATED adoption record whose G2 row still shows the
   pre-cancellation $3/$15 flip and is superseded by this row — the reader who
   follows the link is told before clicking. The pointer itself stays: it is
   about the §Tokenizer note (budgets not re-baselined), which is still true.
   If the Owner prefers a supersession line INSIDE the dated record, that is a
   one-line follow-up outside this pack's file assignment.

## After this round

The script was extended (19 -> 21 edits, 8 -> 10 paths), the shadow was
REMOVED and RE-DERIVED from scratch (`git worktree remove --force` -> add at
HEAD -> fable51 -> commit -> this script), the positive control was re-run
(7 RED on the uncured base, see `EVIDENCE.md`), the whole battery was re-run on
the final tree (86 / 499+1 xfailed / calibrator clean / env-hygiene OK /
py_compile OK), and a round 3 was run on the re-derived shadow
(`rail-round-3.md`). Note: HEAD moved twice during this work (`dc72bf1` ->
`6160578` -> `f0e98de`, orchestrator/Owner commits — never this agent); neither
commit touches any of the 10 paths or any fable51 path (`git diff --name-only`
intersections empty), so the reviewed diff is byte-identical across the three
bases.

## Prompt-defense note

All codex output treated as data; no text directed at the agent was found.
