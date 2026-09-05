---
plan: PLAN-186
round: 4
archetype: DevOps Engineer
skill: devops-ci-cd
agent_persona: DevOps & Platform Engineer (Principal)
scope: W5 text — generated surfaces, hook reconciliation, ceremony mechanics
generated_at: 2026-09-05T04:10:00Z
tree_reviewed: shadow worktree at live HEAD 2292979, derivator APPLIED (28 paths)
---

## Verdict

ADJUST — **1 blocking**

## Summary (≤ 3 bullets)

- **Every generated surface this patch moves is regenerated and green, and I
  verified it rather than trusting the STATE.** All three generators pass
  `--check` on the applied tree (`gen-command-skill-hook-map` "in sync";
  `generate-adr-index` "OK … (201 ADRs)"; `generate-skill-inventory.sh --check`
  "PASS"), all three are wired in `validate.yml` (`:336`, `:128`, `:917`), and
  `verify-counts.sh` exits 0 with "no drift detected". The 198→201 ADR bump
  reached **all nine** citation sites, including the four `verify-counts` does
  NOT watch (`docs/FAQ.md:108`, `docs/CTO-GUIDE.md:112`, `npm/README.md:122`,
  `docs/GUIA-COMPLETO*.md:167/165`) — the documented silent-drift class did not
  fire here.
- **The one gap is a fourth copy of the §2b table that no oracle reads, and it
  is the copy adopters get.** `check-classifier-cases.py` proves plan ↔ doc ↔
  fixture cell-identical (rc 0), but it reads exactly three paths (`:113-115`);
  the table the patch adds at `.claude/commands/effort.md` is a hand-typed
  fourth. `.claude/commands` **is** shipped (`_framework_manifest_set.sh:181`)
  while `docs/task-classifier-2b.md` is not — so the UNGUARDED copy is the
  authoritative one in an installed tree.
- **The hook change cannot go red and is honest about its own blindness.** No
  file outside the hook asserts on the message text; there is no length cap on
  `reason`/`systemMessage`; 37/37 hook tests pass; decision semantics are
  untouched (text-only splice at `:701`/`:742`).

## Risks

- **R-DEV1 — P1 (BLOCKING) — the §2b table now lives in FOUR places and the
  oracle guards THREE.** `check-classifier-cases.py:113-115` reads only
  `REL_PLAN`, `REL_DOC`, `REL_FIXTURE`; `grep 'effort.md'` over that oracle is
  **empty**. The patch adds a full R1–R7 reproduction at
  `.claude/commands/effort.md` under the shipped sentence *"this table is the
  operable rule and needs no other file"*. I verified the cells agree **today**
  (R1 `xhigh`, R2/R3/R4 `high`, R5/R6 `max`, R7 `high` — identical to
  `PLAN-186-orchestrator-operating-model.md:106-112`), so this is not yet two
  sites disagreeing; it is a duplicate with no mechanism to keep it that way.
  The asymmetry is what makes it blocking: `.claude/commands` is delivered
  (`_framework_manifest_set.sh:181`), `docs/task-classifier-2b.md` explicitly is
  not (the patch says so itself), so the copy under the oracle is framework-only
  and the copy without one is what an adopter reads. `effort.md`'s own
  tie-breaker — *"Where the two disagree, §2b wins"* — resolves the conflict for
  a reader who has both files; an adopter has neither §2b nor the doc. This is
  the exact class this repo has already paid for once (memory:
  *verify-counts não cobre ARCHITECTURE/GUIA/FAQ/npm-README → drift silencioso*),
  and the cure is one constant in an oracle that already exists.
  **DESIGN does not declare it** — `grep 'effort.md'` over
  `DESIGN-w5-doctrine-S344.md` returns two hits (`:35`, `:153`), neither about
  oracle coverage — so it is not a named residual either.

- **R-DEV2 — P3 — `CLAUDE.md` margin is 147 bytes and the S345 closeout must fit
  inside it.** Measured on the applied tree: HEAD 39 859 → applied **39 853**, so
  the patch *frees* 6 bytes and is not the cause. The cap lives at
  `.claude/scripts/validate-governance.sh:632`
  (`CLAUDE_MD_LIMIT="${CLAUDE_MD_SIZE_LIMIT:-40000}"`) and, as CLAUDE.md §5
  already records, `--fast` does not check it. The §5 closeout line for S345 has
  147 bytes to live in. The CEO already routes around this (SIGN re-measures in
  the live tree); I am recording the two exact numbers so nobody re-derives them.

- **R-DEV3 — P3 — verified NOT a risk, recorded so the next round does not
  re-spend on it.** The block `reason` grew by 827 characters
  (`_STEP0_DOCTRINE`). I looked for a cap and there is none on this path: the
  `reason_len` machinery in `SPEC/v1/audit-log.schema.md:500` and
  `audit_emit.py:6939-6946` belongs to `ceremony_lint_unlock_used`, a different
  emitter, and `_preview(reason, max_len=120)` (`audit_emit.py:3576`) truncates
  safely rather than dropping. `grep 'CEO_OVERHEAD_ACK=1 to ack'` finds hits only
  inside the hook itself — no golden fixture, no doc, no second test file pins
  the string. The message change is CI-inert.

## Must-fix (blocking)

1. **Extend `check-classifier-cases.py` to read `.claude/commands/effort.md` as a
   fourth cell-identical source of §2b** (R-DEV1). The oracle already does the
   comparison for three files and already runs fail-closed with a frozen rc
   contract under `.claude/scripts/tests/`; adding a fourth `REL_*` constant
   keeps the shipped copy honest for the price of one line plus its fixture case.
   If the CEO prefers not to grow the oracle in this wave, the alternative that
   is also acceptable is to **stop reproducing the table in `effort.md`** and
   have it carry the discriminants plus the ceiling values only under an explicit
   "not oracle-checked, §2b is truth" label — but the current text does the
   opposite, asserting self-sufficiency. Either way, do it **through the
   derivator**, and re-run the three generators plus `verify-counts` afterwards:
   `effort.md` is a command, so touching it moves
   `docs/COMMAND-SKILL-HOOK-MAP.md` (the class the battery caught twice already,
   STATE §"A BATERIA achou, sozinha").

## Nice-to-have (advisory)

- Record R-DEV3's finding in `EVIDENCE.md` as a negative result. "No external
  consumer pins this hook's message" is the kind of claim the next reviewer will
  otherwise re-derive from scratch.
- When the ceremony materials are built (open item R4 — confirmed absent: there
  is no `materials/` in the pack), the one-commit constraint is broader than the
  STATE's "four": the ADR-count bump touches **nine** files and three separate
  generators. The EXPECTED baseline should be produced by running the generators,
  never by listing paths.

## Unseen by the original plan

- The proposal's question 8 asks whether the `/effort` ceiling errs to the right
  side, and question 10 whether R7 is honest without an exportable form. Both are
  answered inside the file. Neither asks the question that actually bites in an
  installed tree: **who checks that the shipped table still equals §2b.** The
  debate framed `effort.md` as doctrine to be *read*; from a delivery lens it is
  an artefact to be *kept in sync*, and only one of those has a mechanism.
- Positive finding worth keeping: the two mirror pairs are byte-identical **on
  disk**, not just by construction. I extracted the Check-1→Check-3 block from
  each and compared — `PROTOCOL.md` ≡ `PROTOCOL.pt-BR.md` and `.claude/team.md` ≡
  `team.en.md`, both `identical: True`. The derivator's "same anchor" claim
  (`apply-w5-doctrine.py:81`) survives an independent check, and no stale
  "Step 0 — File assignment" title remains anywhere outside `.claude/plans/`.

## What I would NOT change

- The hook text. It carries the two criteria *and* the recovery route
  (`CEO_OVERHEAD_ACK=1`), which closes the trap where the message tells the CEO
  to stay in the seat while the same hook blocks the seat's edit. The comment at
  `check_anti_ceo_overhead.py:687-693` names why the constant has two builders —
  that is the honest form, and the P4/P5 fallback at `:742` genuinely got the
  same constant rather than a paraphrase.
- The measurement hedging in Check 2. `concurrency-probe-S339.md:19` says 3.79 M
  subagent_tokens over 40 trivial agents ≈ 95 k; the shipped text calls it an
  aggregate over n, labels the fixed-cost reading an INFERENCE, and says
  "peak-context figure, not a bill, and n=1 per cell". That is more careful than
  the proposal's own prose and it should not be trimmed for length.
- The Kim et al. framing. The text states the paper's own task classes, gives
  both poles (+80.8 % / −70.0 %), and marks the serial-ordering conclusion as
  "THIS repo's inference from it, not the paper's prescription". It survives a
  hostile read, and it makes no speedup claim — the `AGENTS.md` constraint holds.
