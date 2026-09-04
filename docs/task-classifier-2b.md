# The «specified task» classifier — decision procedure for PLAN-186 §2b

> **Authority.** `PLAN-186 §2b` is the norm: it decides *model* and *effort* per
> artefact class, and it decides from W1 onward. This document **REFINES** that
> rule and never suspends it — it fixes the ORDER in which §2b's discriminants
> are applied, names the tie-breaks, and makes the result falsifiable. Where a
> §2b cell and this procedure disagree, **the §2b cell wins** and the
> disagreement is a defect *in this document*, to be filed as a case.
> **Machine check:** `.claude/plans/PLAN-186/w5/classifier-cases.json` +
> `.claude/plans/PLAN-186/w5/check-classifier-cases.py` (AC-14).

## 0. Why a procedure and not a table

§2b is a TOTAL partition over seven artefact classes, but a partition is only
auditable if two people who read it land on the same row for the same task.
The failure mode this repo pays for is not a wrong table — it is a plausible
classification nobody can re-derive later. So the classifier is an **ordered
list of yes/no questions**, each with a mechanical test, and each terminal
answer lands in exactly one §2b row. The order is load-bearing: `assento CEO`
and `VETO` are *who runs*, not *what is produced*, so they must be answered
before any artefact question or every task double-classifies.

## 1. The rows (frozen copy of §2b)

Row ids are the §2b table order. This copy is checked byte-for-byte (after
whitespace normalization) against the plan by the fixture checker: if §2b
changes, the check goes RED and this document must be re-derived.

| id | classe de artefato (§2b) | modelo | effort |
|---|---|---|---|
| R1 | **DEFINE uma pergunta**: gate, oráculo, instrumento, critério de aceite, refutação, **DESENHO do predicado de um censo** | `claude-opus-5` | `xhigh` |
| R2 | **EXECUTA uma derivação DE TEXTO** com pergunta já fixada: relatório, doc, anchor-exact em prosa/Markdown | `claude-sonnet-5` | `high` |
| R3 | **EXECUTA uma derivação DE CÓDIGO/CONFIG** (`.py`/`.sh`/`.js`/`.yml`/`.json`) com pergunta já fixada, inclusive **censo MECÂNICO** que edita esses formatos (OQ-3) | `claude-opus-5` | `high` |
| R4 | **PESQUISA/LEITURA sob pergunta FIXADA pelo CEO**: ler fontes e devolver claim com citação verificável, sem escolher a pergunta | `claude-sonnet-5` | `high` |
| R5 | VETO (5 arquétipos) | camada T, decisão de capacidade — ver W1 | `max` |
| R6 | síntese / REDUCE | `claude-fable-5-1` | `max` |
| R7 | assento CEO | `claude-fable-5-1` fixo (OQ-1, sem A/B) | `high` |

## 2. The decision procedure

Answer in order. The first YES that is a terminal answer ends the walk. Every
question has a mechanical test — if you cannot run the test, the task is not
specified enough to dispatch, which is itself the answer (go back to the CEO).

### Q0 — Is the task the ORCHESTRATION itself?
R7 is a ROLE, not an execution mechanism. The seat's own work is deciding what
happens next: the Gate-1/Gate-2 reads, choosing the wave and the next execution
unit, classifying and dispatching, arbitrating a debate, ratifying a verdict.
*Test:* name the artefact this task hands back. If the answer is "a decision
about what to do next" and not a file, a claim or a report, it is the
orchestration.
**YES → R7.** NO → Q1.

> **The row is not the executor** (this is where an earlier draft of this
> document contradicted T5). A task keeps its row whoever runs it: an R3
> deriver classified `claude-opus-5`/`high` is still R3 when the seat writes it
> inline as a tool call instead of spawning — the classification is about the
> artefact, and T5 is about whether spawning is worth its fixed context cost.
> Q0 must therefore never be answered "yes" merely because no `agent()`
> dispatch occurred.

### Q1 — Does the task carry VETO authority?
*Test (DERIVED on disk, never recalled):* run
`grep -l '^veto_floor: true' .claude/agents/*.md` — the five files it prints ARE
the roster (`code-reviewer`, `security-engineer`, `incident-commander`,
`identity-trust-architect`, `threat-detection-engineer`). The code authority is
`VETO_FLOOR_ROLES` (`.claude/hooks/_lib/agent_frontmatter.py`), a 5-member
frozenset, and the two are kept identical by
`.claude/hooks/tests/test_veto_floor_bijection.py` — so the grep and the
constant cannot silently disagree.
**Do NOT source the roster from `VETO_HARDCODE`**
(`.claude/scripts/tier_policy_cli/_constants.py`): measured on this HEAD it
carries **2 of the 5 keys** (`code-reviewer`, `security-engineer`) — it is the
module-load SHA256 tripwire for the two hottest pins, not the roster. Reading
it as the roster is a silent 3-archetype false negative. (`ADR-142` names
the same five in prose; prose is corroboration, not the derivation.)
**YES → R5** (the model is the camada-T decision, not this document's; effort
`max`). NO → Q2.

### Q2 — Is the input EXCLUSIVELY other agents' returns, with no new claim of its own?
*Test:* the agent runs with no tools and writes no files, and every sentence
of its output is traceable to a fenced return it was given. A "synthesis" that
re-checks evidence against disk is NOT this row — re-checking is refutação,
which is R1.
**YES → R6.** NO → Q3.

### Q3 — Does the task DECIDE A PREDICATE?
Any one of these is a YES:
- **(a)** it writes or changes a gate, check, oracle, assertion or lint whose
  verdict future runs depend on;
- **(b)** it chooses the acceptance criterion, the death criterion, or the
  measurement's unit;
- **(c)** it decides what a census COUNTS AS a site (the predicate), as opposed
  to running a census whose predicate is given;
- **(d)** it re-verifies somebody else's claim against evidence (refutação).

*Test:* after this task lands, is there a future run whose PASS/FAIL depends on
a rule chosen HERE? If yes, the question was defined here.
**YES → R1.** NO → Q4.

### Q4 — Does the task WRITE bytes into the repo?
*Test:* the ADR-191 `## FILE ASSIGNMENT` of the spawn. A concrete path list is
a writing task. `CAN edit: NONE-READ-ONLY` is read-only **only when the
deliverable is a claim**: a task that hands back a program, a config or a
patch bound for a repo destination is Q4=YES even though it writes nothing
itself — the FILE ASSIGNMENT says where bytes may LAND, never what the task
PRODUCES. Without that clause a read-only agent asked to return a deriver
terminates at R4, whose row is «ler fontes e devolver claim com citação
verificável» — a shape that row does not cover, while §2b assigns code/config
derivation to R3 (rail r1 [P1]). The terminals are unchanged: this sharpens
Q4's TEST, it does not move a branch.
**NO (reads only, returns claims) → R4.** YES → Q5.

### Q5 — Is the artefact it PRODUCES a program or a config?
*Test:* the thing the agent hands back. A deriver script is a program even when
every byte it writes is prose. The extension list of §2b
(`.py`/`.sh`/`.js`/`.yml`/`.json`, plus `.yaml`/`.tsv`) is EVIDENCE, not the
definition: the question is "does a program CONSUME this artefact as input to
decide something" — a gate reads it, a build loads it, a router keys off it. Being
rendered, linted or link-checked is NOT consuming: human-facing prose stays R2
even though a linter reads it, which is why C2 records `Q5=no` for a doc that a
CI job link-checks (rail r2 [P2]). The default for an unlisted format a program
CONSUMES is R3, never R2.
**YES → R3.** **NO (prose bytes only, and no script is written) → R2.**

```procedure-map
Q0=yes -> R7
Q1=yes -> R5
Q2=yes -> R6
Q3=yes -> R1
Q4=no -> R4
Q5=yes -> R3
Q5=no -> R2
```

The map above is the machine-readable form of §2 and is parsed by the checker,
which proves three properties of the procedure itself: every question before
the last has exactly one terminal branch, the last question has two, and the
seven terminals are exactly the seven §2b rows — each reachable, none twice.
That is the partition being TOTAL, checked rather than asserted.

## 3. Tie-breaks (the part that was previously unwritten)

- **T1 — a mixed pack is ONE task and routes to the STRICTEST row present.** A
  pack that edits prose and code/config in the same anchor-exact deriver is R3.
  See boundary B1.
- **T2 — writing the oracle is never the same task as running the derivation.**
  Same model, different effort (R1 `xhigh` vs R3 `high`). See boundary B2.
- **T3 — R2 vs R4 is decided by Q4 alone** (writes vs reads). Both rows are
  `claude-sonnet-5`/`high`, so this boundary is cost-neutral today; it still
  matters for the `## FILE ASSIGNMENT` the spawn must carry.
- **T4 — the §2b prose calls the research row "linha 2"**; in the published
  seven-row table the research class is row **R4**. The ordinal in the prose is
  stale relative to the table's final shape, and it is cost-neutral (both rows
  are `claude-sonnet-5`/`high`). Recorded so nobody "restores" the older
  numbering from the prose.
- **T5 — the classifier decides the ROW, never whether to spawn at all.** The
  fixed per-spawn context cost (W5-US1, §W5) can make a correctly classified R3
  cheaper as a tool call in the seat.

## 4. Worked cases — every row covered, every citation real

Full text, question paths and citations live in the fixture; this table is the
index the checker binds against. Every §2b row has at least one non-boundary
worked case; R3 has two — C3 and C8 — because R3's cell is the only one that
enumerates a LIST of destination formats, and one case exercises only part of
it.

| id | row | terminal | task (short) |
|---|---|---|---|
| C1 | R1 | Q3=yes | design the discovery predicate of the installer write-safety census |
| C2 | R2 | Q5=no | render the ownership decision-table doc from the TSV that is the truth |
| C3 | R3 | Q5=yes | write the deriver that puts explicit `model:` on the workflow `agent()` sites |
| C4 | R4 | Q4=no | run one `nightly-hygiene` dimension and return findings with evidence pointers |
| C5 | R5 | Q1=yes | `code-reviewer`'s own merge-gate pass on a canonical patch (dispatching it is R7) |
| C6 | R6 | Q2=yes | merge the nine dimension returns into one report, no tools, no files |
| C7 | R7 | Q0=yes | the CEO turn itself — Gate-1/2, routing, wave decision |
| C8 | R3 | Q5=yes | the `adopt-fable-5.1` deriver: 30 destinations, `.py`/`.json`/`.yaml`/`.sh`/`.txt`/`.md` |
| B1 | R3 | Q5=yes | the mixed `sonnet5-pricing-fu` pack: 2 prose paths + 8 code/config paths |
| B2 | R1 | Q3=yes | write the oracle that checks `_ownership_verdict()` against the TSV |

### C1 — R1, DEFINE (`claude-opus-5`/`xhigh`)
Task: decide what the installer write-safety census COUNTS AS a site — the 5th
pass inverted discovery to fail-closed, so a command is a site unless its name
is proven read-only. Path: `Q0=no → Q1=no → Q2=no → Q3=yes(a,c)`. Citation:
`.claude/scripts/check-installer-write-safety.py`
(`PROVEN_READONLY = frozenset("""`). The file's own docstring records why the
first four passes were fail-open — the predicate IS the deliverable.
*Observed gap:* the refuter dispatch at `.claude/workflows/audit-fanout.js`
is also R1 work (refutação, Q3=d) and carries **no `model:` at all** today,
which is exactly the AC-3a defect the W1 ceremony closes.

### C2 — R2, TEXT derivation (`claude-sonnet-5`/`high`)
Task: render the human-readable ownership decision table from the TSV that
holds the truth; the verdicts are already decided, the artefact is prose.
Path: `Q0=no → Q1=no → Q2=no → Q3=no → Q4=yes → Q5=no`. Citations:
`docs/ownership-decision-table.md` (the doc naming
`scripts/tests/ownership_table.tsv` as "the truth") and
`scripts/tests/ownership_table.tsv`. Q3 is NO precisely because the doc
decides nothing: two oracles read the TSV, not the prose.

### C3 — R3, CODE/CONFIG derivation (`claude-opus-5`/`high`)
Task: write the deriver that adds an explicit `model:` to the real `agent()`
sites of the four Workflow scripts, given the per-site classification table.
Path: `Q0=no → Q1=no → Q2=no → Q3=no → Q4=yes → Q5=yes`. Citations:
`.claude/plans/PLAN-186/w1/apply-w1-explicit-model.py` (`SITES = [`) and one
destination, `.claude/workflows/nightly-hygiene.js`. Q3 is NO **only
because the table is given**: choosing which model each site gets is R1 work,
and §W1 says the wave re-derives that table under OQ-3 before the ceremony.
Split the two and each half is classifiable; merge them and the router is
choosing `xhigh` or `high` by coin flip.

### C4 — R4, RESEARCH under a fixed question (`claude-sonnet-5`/`high`)
Task: one of the nine `nightly-hygiene` dimensions — run the NAMED script for
the dimension and return findings, each with an evidence pointer, writing
nothing. Path: `Q0=no → Q1=no → Q2=no → Q3=no → Q4=no`. Citation:
`.claude/workflows/nightly-hygiene.js` — the dimension dispatch, anchored on
the `agent()` options object that carries `phase: 'Sweep'`. S343 v2 narrowed
that anchor to the half W1 does not rewrite: the W1 routing patch inserts
`model:` and `effort:` into the SAME object, which deleted the wider anchor
v1 used. Q3 is NO because the dimension's predicate was written elsewhere;
adding a NEW dimension is R1.

### C5 — R5, VETO (camada T/`max`)
Task: the `code-reviewer` archetype's OWN merge-gate pass on a canonical patch
— read the diff and exercise, or withhold, the VETO. S343 v2 corrected this
case: it used to read «DISPATCH the merge gate to the `code-reviewer`
archetype», and Q0 sends deciding-and-dispatching to R7, so the case's own
`Q0=no` contradicted the procedure and R5 had no valid worked case while the
oracle reported full coverage (rail r5 [P1]). Routing the review is the seat's
work; performing it is R5. Path: `Q0=no → Q1=yes`. Citations:
`.claude/agents/code-reviewer.md`
(`veto_floor: true` — the frontmatter flag the grep in Q1 selects on) and
`.claude/hooks/_lib/agent_frontmatter.py` (`VETO_FLOOR_ROLES`, the 5-member
frozenset the bijection test binds to that flag). The model is NOT this
document's decision: the floor is camada T, and the pin is Owner-signed. Note the governance limit measured in W0-US4
(AC-10): the hook validates the FILE, never the model SERVED — this row is a
capability claim about the archetype, not runtime enforcement.

### C6 — R6, síntese/REDUCE (`claude-fable-5-1`/`max`)
Task: merge the nine dimension returns into one markdown report, no tools, no
files. Path: `Q0=no → Q1=no → Q2=yes`. Citation:
`.claude/workflows/nightly-hygiene.js` — the dispatch text says
"read-only — use NO tools, write NO files", which is Q2's test verbatim on
disk. The neighbouring synthesizer in `.claude/workflows/audit-fanout.js` is the
same row; its REFUTERS are not (they are R1).

### C7 — R7, seat (`claude-fable-5-1` fixed/`high`)
Task: the CEO turn — Gate-1/2 reads, routing, wave decision. Path: `Q0=yes`.
Citations: two sentences of `PROTOCOL.md` — the seat drafting the plan («who
does what, in what order, with which skill loaded») and the seat deciding on a
lone dissenting risk. What the seat hands back is a DECISION about what happens
next, which is exactly what Q0 tests. §2b fixes the seat's model at
`claude-fable-5-1` (OQ-1, no A/B); that pin is Owner-signed camada T and is not
this document's decision.
*Why not the settings pin.* v1 of this document cited the session pin in
`.claude/settings.json` and called the STALE it would return at the W1 flip «a
deliberate ratchet». It is not a ratchet, it is a CI failure: this fixture is
verified by a pytest case that `pytest.ini` collects, so landing W1 would turn
`main` RED on a case whose argument never changed. Measured on a worktree with
the W1 routing patch applied, v1's fixture returns 2 ANCHOR-STALE + 1
ANCHOR-DRIFT. The seat now cites governance text W1 does not touch.

### C8 — R3, CODE/CONFIG derivation, CONFIG destinations (`claude-opus-5`/`high`)
Task: write the anchor-exact deriver of the `adopt-fable-5.1` ceremony — one
`.py` program carrying every edit of the wave over **30 destinations**
(`--list-paths`: 19 `.py`, 4 `.md`, 3 `.sh`, 2 `.json`, 1 `.txt`, 1 `.yaml`),
each with its exact anchor and expected count, refusing by name on an anchor
that is missing, ambiguous or already applied. Path:
`Q0=no → Q1=no → Q2=no → Q3=no → Q4=yes → Q5=yes`. Citations:
`.claude/plans/PLAN-169/s338-ceremony-fable51/apply-fable51-edits.py`
(`NEW_ID = "claude-fable-5-1"` — the single subject of the derivation) and one
CONFIG destination it wrote, `.claude/scripts/cost-table.yaml`
(`claude-fable-5-1:`). Q3 is NO because the question was settled BEFORE the
task: the Owner ratified rota (c) — the new id enters the ADR-149 working set
ONLY, floor/fallback/pin untouched — so «which ids move» is not this task's to
decide. Q5 is YES on the CONFIG half of the cell.
*Why R3 gets a second worked case:* R3's cell is the only one that enumerates a
LIST of destination formats (`.py`/`.sh`/`.js`/`.yml`/`.json`). C3's cited
destination is `.js`; C8's is `.yaml`, and its 30 destinations span six
extensions — so the two together exercise more of the list than either alone.
This is a claim about the DESTINATIONS the cases exercise, and it does not
re-open the discriminant: B1 decided the row is chosen by the artefact
PRODUCED, and both C3 and C8 produce a `.py` deriver (rail r1 [P2]).
`ROW-UNCOVERED` is blind to this either way — coverage counts CASES.

## 5. Boundary cases, decided

### B1 — mixed pack: R2 or R3? **R3 wins.**
The real task: the `sonnet5-pricing-fu` pack. Mechanically derived path set
(`--list-paths` plus an extension count over the same list): **21 edits over 10
paths — 8 code/config** (`.py` ×7, two of them test modules; `.yaml` ×1) **and 2
prose** (`.md` ×2: `docs/CEO-MODEL-ROUTING.md`, `docs/cost-of-operation.md`). It
plausibly sits between R2 and R3: the prose destinations carry the claim a
reader sees.

**Decision: R3 (`claude-opus-5`/`high`), as ONE task.** Three reasons:
1. **The artefact is the deriver, not the destination bytes.** Under OQ-3 the
   discriminant is the type of artefact PRODUCED, and what this task produces is
   `apply-sonnet5-pricing-fu.py` — a program. Prose destinations do not make a
   program a document.
2. **The invariant is whole-script.** "21 edits in 10 paths", the per-anchor
   expected count and the double-application refusal are properties of the
   script's plan step; split the pack in two and neither half can verify the
   count the other half owns.
3. **Evidence crosses the split.** The rail's r2 finding was in
   `build-canonical-models.py` `_MM_TIERS` — a code surface reached FROM the
   prose claim. A prose-only lane would have needed the code lane's evidence to
   know its own claim was incomplete.

Citation: `.claude/plans/PLAN-169/s338-fu-sonnet5-pricing/apply-sonnet5-pricing-fu.py`
(`EDITS: List[Tuple[str, str, str, int]] = [` — the single edit list) and
`docs/CEO-MODEL-ROUTING.md` as a prose destination inside it.

*Consequence, stated so it is not discovered later:* a task whose destinations
are prose-only AND that writes no script is still R2 — B1 does not swallow the
row, it only refuses to split a single deriver.

### B2 — the oracle vs the derivation: R1 or R3? **The oracle is R1.**
The real pair: `scripts/tests/test-ownership-verdict-unit.sh` (reads
`ownership_table.tsv` and decides whether `_ownership_verdict()` is right)
versus adding a row to that TSV and making `_ownership_verdict()`
(`scripts/_framework_manifest_set.sh`) satisfy it. Both are `claude-opus-5`
— so a hand-router feels no friction here and the boundary is invisible unless
it is written down. What differs is EFFORT.

**Decision: writing or extending the oracle is R1 (`xhigh`)** by Q3(a): after
it lands, a future run's PASS/FAIL depends on a rule the oracle chose. Making
the function satisfy a given row is R3 (`high`). The pair is the canonical shape
of this repo's dominant defect class — a green instrument whose question went
stale — and the whole reason R1 carries the higher effort tier.

Citations: `scripts/tests/test-ownership-verdict-unit.sh`
(`TSV="$SCRIPT_DIR/ownership_table.tsv"`) and
`scripts/_framework_manifest_set.sh` (`_ownership_verdict() {`).

## 6. What this classifier does NOT decide — declared false-negative surface

1. **No CI step invokes the checker directly** — that would edit
   `.github/**`, a signed ceremony surface. It is enforced INDIRECTLY, and
   S343 v2's pair-rail caught this document claiming otherwise: case 1 of
   `.claude/scripts/tests/test_ac14_classifier_check_rc.py` runs the oracle
   against the checked-out tree, and that directory is run by
   `.github/workflows/validate.yml` (the "script unit tests" steps) and by
   `.github/workflows/release.yml` (the tag gate). So a citation whose
   anchored TEXT dies turns CI red, on `main` and at a tag. What stays a real
   false negative is narrower and still worth stating: nobody runs the oracle
   on a tree that is not being tested — a stale fixture in a branch nobody
   pushes stays stale, and no step names the oracle, so a reader of the
   workflows will not find it.
2. **A live citation is not a live argument.** The checker proves the cited
   anchor still occurs, exactly once, in the cited file; it cannot prove the
   reasoning in the case still holds.
3. **Q5's extension list is an enumeration** and is therefore born blind to the
   next format — the r22 lesson of PLAN-179 (a channel closes by removal, not by
   enumeration). The mitigation is the DEFAULT stated in Q5, not a longer list.
4. **R2 vs R4 misclassification is invisible in dollars** (same model, same
   effort), so no cost signal will ever surface it. Only the FILE ASSIGNMENT of
   the spawn will.
5. **R5's model is out of scope by construction.** The camada-T pin decides it,
   and W0-US4 measured that the spawn hook validates the FILE, never the model
   SERVED.
6. **A citation dies when its anchored TEXT dies — and that RED is wanted.**
   Citations carry no line number (S343 v2: a line pin reddened on any edit
   ABOVE it, and the PLAN-186 W1 routing patch did exactly that to three of
   them without touching a single argument). What is left is the narrower
   failure this gate is FOR: a pack that DELETES a cited fact makes it RED,
   and the repair is `grep -n` on the anchor. A pack that merely MOVES the
   fact is now invisible here, which is the trade this cure buys.
7. **`VETO_HARDCODE` is not the VETO roster** and this classifier does not make
   it one. It freezes 2 of the 5 archetypes (measured, see Q1); the remaining
   three are protected by the frontmatter flag and the bijection test, not by
   the module-load SHA256 assertion. A reader who derives the roster from the
   constant gets three false negatives, and nothing in this fixture would go
   RED — the checker binds citations, not the reader's inference.
8. **The checker binds the FIXTURE's citations, never the doc's prose.** Rail
   round 1 [P2] found the prose in §4 naming the wrong line of
   `.claude/agents/code-reviewer.md` while the fixture recorded the anchor
   correctly — and the check stayed green throughout. S343 v2 removed every
   line number from this document's prose, and the fixture has none either, so
   the two can no longer disagree about a NUMBER. They can still disagree
   about a PATH, and only the fixture is verified.
9. **The domain is ARTEFACT-PRODUCING agent work, and that is a limit, not an
   oversight.** A specified OPERATIONAL task with side effects outside the tree
   — publish a release, push a pre-approved tag, run a ceremony's LAND — answers
   NO through Q0–Q3 and writes no repository bytes, so Q4=no would land it in R4,
   whose row is «ler fontes e devolver claim». It does not belong there and this
   procedure does not classify it: in this repo those acts are Owner-signed
   ceremony, not a routed spawn (`PROTOCOL.md`, the GPG land scripts). Adding a
   terminal would change the partition §2b freezes, which this document may not
   do — so the gap is DECLARED here and belongs to a §2b amendment if the Owner
   ever routes such a task to an agent (rail r2 [P2]).
