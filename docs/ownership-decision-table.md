# Ownership decision table — install/upgrade conditional surfaces

> **Status:** W0 product of PLAN-167. The enum in §3 is a *draft* until the
> PLAN-167 W1 debate ratifies or amends it. The open questions in §6 are
> deliberately unresolved here — they are the debate's agenda.
>
> **Two known inconsistencies are committed on purpose.** Writing the decision
> function against this table (the W2 proposal) exposed them, and resolving
> them unilaterally would pre-decide exactly what the debate exists to settle:
>
> 1. **The table is not self-consistent about `OMIT_RECORD`.** Some rows with a
>    prior record expect `OMIT_RECORD`, others with a prior record expect
>    `PRESERVE_UNOWNED`. Sixty-one hand-written rows never had to agree with
>    each other; a function has to. See OQ-9.
> 2. **`OWN-0018` and `OWN-0020` have identical dimensions and opposite
>    outcomes**, separated only by a prose directive in `note`. A decision
>    function cannot read prose, so the distinction has to become a *value* —
>    the proposal is a `live_content` of `legacy_pristine_partial`, meaning a
>    tree carrying an entry the fingerprint cannot hash. See OQ-7.
>
> The baseline map was measured against the table in this state, so the map and
> the table agree with each other. Reconciling either one is W2 work, after
> ratification.

## 1. What this document is, and why it exists

`ADR-155-AMEND-1` decided that framework ownership of the three
**conditional** surfaces — root `PROTOCOL.md`, the `SPEC/v1` contract tree,
and the `.claude/.framework-version` marker — derives from the **registered
delivery record**, never from the ceremony alone and never from file
presence.

The decision was right. Its *realization* was a cascade of `if` branches
spread across `scripts/install.sh`, `scripts/upgrade.sh` and
`scripts/_framework_manifest_set.sh`. That shape has a measured failure
mode: over eleven consecutive cross-model review rounds on the same code,
**35 distinct defects** were reported, and roughly half of the later ones
were regressions introduced by the fix for the round immediately before.
The 45-check end-to-end suite stayed green throughout — it exercises eight
scenarios, and the decision space is a nine-dimensional product.

The cause is not carelessness. It is that **"correct" was being decided one
branch at a time**, so two branches could encode contradictory answers to
the same question and nothing would notice. This document makes the space
explicit so that contradictions surface *before* they become defects.

Division of labour, strictly observed:

| Artifact | Role |
|---|---|
| this document | defines the dimensions, the legality rules, and the reasoning |
| `scripts/tests/ownership_table.tsv` | **the truth** — one row per legal cell, with its expected verdict |
| `scripts/tests/test-ownership-table.sh` | executes every row against the **real** scripts |

**No value is duplicated between this document and the TSV.** If you want to
know what a given cell decides, read the TSV. If you want to know *why the
cell exists at all*, read this.

## 2. The nine dimensions

A "cell" is one assignment of all nine. The subject under test is one
surface's outcome on one run.

### 2.1 `surface`

| Value | Path | Shape |
|---|---|---|
| `spec` | `SPEC/v1` | a **tree** |
| `protocol` | root `PROTOCOL.md` | a **generated pointer** — no source file; the body is a heredoc built from `$SOURCE_DIR`/`$TARGET`/`$PROFILE`/`$STACK` |
| `marker` | `.claude/.framework-version` | a tracked single-line file |

The three differ in more than their path, and every difference has produced
at least one defect. `spec` is the only tree (so it is the only surface with
descendants, per-file records, and a "partially populated" state);
`protocol` is the only surface with no bytes in the source (so `source_has`
is meaningless for it, and its baseline digest comes from a *computed*
canonical hash); `marker` is the only surface inside `.claude/`, so it is
the only one both ceremonies receive.

### 2.2 `prior_record` — what the PRE-run baseline manifest says

| Value | Meaning |
|---|---|
| `none` | no record line for this relpath |
| `hash` | a `<64-hex>  <relpath>` record |
| `link_match` | a `LINK  <relpath>  <target>` record whose target equals the live `readlink` |
| `link_retargeted` | a `LINK` record whose target does **not** equal the live `readlink` |

This dimension describes the **previous** run's testimony, read before
anything is written this run. It is the operative meaning of "registered
delivery" in ADR-155-AMEND-1 §3.

### 2.3 `live_type` — `lstat` of the destination, never following

`absent` · `dir` · `dir_empty` · `regular` · `symlink` · `special`
(FIFO, socket, device) · `ancestor_symlink`.

`ancestor_symlink` is a value of this dimension rather than a tenth
dimension because the decision function short-circuits on it *before* it
ever looks at the leaf — exactly as it does for `special`. It answers the
same question ("what kind of destination is this?") with "one reachable only
by writing through a symlink out of the target tree".

`dir_empty` is split from `dir` because for `spec` it changes the *manifest*
outcome without changing the *filesystem* outcome — the enumeration walks
the target and emits a record per regular file, so an empty tree yields no
records at all even when every other signal says "owned".

`special` exists because two separate defects were `cp` invoked on a FIFO,
which blocks forever waiting for a writer and hangs the run **mid-upgrade**,
after earlier surfaces have already been modified.

### 2.4 `live_content` — only defined when `live_type ∈ {dir, dir_empty, regular}`

| Value | Meaning |
|---|---|
| `pristine` | byte-identical to what **this** source would deliver |
| `legacy_pristine` | matches a `SPEC/v1` fingerprint the framework shipped at v1.2.0 or earlier |
| `edited` | neither |

`legacy_pristine` exists because v1.2-and-earlier installs never enumerated
`SPEC/v1`, so no record can distinguish a framework-installed tree from an
adopter-authored one; the ambiguity is resolved by content against three
pinned fingerprints.

### 2.5 `source_has` — does `$SOURCE_DIR` carry this surface?

`yes` · `no`. The reachable `no` case is the documented `--pin` downgrade to
a pre-v1.3.0 tag, whose checkout has no marker. A `SPEC/v1` absent from
source means a broken or partial checkout.

### 2.6 `mode` — the delivery mode of **this** run

`copy` · `link`. On `install.sh` this is `--mode`. On `upgrade.sh` there is
no `--mode` flag: the value is *inferred* for the baseline rewrite, from a
prior `LINK` record first and a symlink probe second.

> **This dimension is about the current run, not the recorded one.** See
> pruning rule R-09 for why conflating them would delete a real defect.

### 2.7 `ceremony`

`user` · `maintainer` — the *effective* ceremony, read replay-independently
from `.claude/.install-state.json`, failing open to `maintainer` when the
state is absent (every pre-Wave-B install).

### 2.8 `operation`

`install_fresh` · `install_rerun` · `upgrade`. "Fresh" is defined
structurally: **no pre-existing baseline manifest at the target**.

### 2.9 `skip_requested`

`none` · `self` (`--skip SPEC/v1`) · `descendant`
(`--skip SPEC/v1/local.md`).

### 2.10 `fault` — the tenth dimension (ratified in round 1)

`none` · `backup_unwritable`.

An injected environmental failure. It is not a property of the target, which
is why it is not `live_type`; it is a genuine tenth axis, and it rode inside
the `note` column as a prose directive until the round-1 debate ruled that a
**dimension the harness parses out of prose is a dimension nothing
validates**.

Dropping those rows was the lower-friction alternative and was rejected:
they are the backup-failure *safety* cells, and a failed backup followed by a
delete is the data-loss path the whole backup-before-replace contract exists
to prevent. A column is cheap; a hole is not.

Consequently `note` now carries **prose only**. `indistinguishable=` and
`open=` survive as annotations because neither changes what the fixture does
or what the decision function returns.

## 3. The verdict enum (draft — W1 ratifies)

The outcome of a cell is a **pair**. Every defect found in the eleven review
rounds was a cell whose pair was wrong — which is the evidence that the pair
is the right shape for the answer.

### 3.1 First field — what happens to the target

| Verdict | Meaning |
|---|---|
| `DELIVER` | write the framework's version; the target had nothing |
| `REFRESH` | replace existing content, **backup first** |
| `PRESERVE_OWNED` | do not touch the target; **keep** the delivery record |
| `PRESERVE_UNOWNED` | do not touch the target; do **not** record (the adopter owns it) |
| `OMIT_RECORD` | target stays; its record leaves the manifest |
| `ABORT_SURFACE` | refuse this surface, rc 0, named warning; the run continues |

`ABORT_SURFACE` is distinct from `PRESERVE_UNOWNED`: it is the outcome when
the framework *wanted* to act and could not do so safely — a failed backup,
an unsupported special file — and the distinction matters because the
operator must be told.

### 3.2 Second field — where the manifest's digest comes from

| `hash_source` | Meaning |
|---|---|
| `HASH_TARGET` | hash the bytes now on disk at the target |
| `HASH_SOURCE` | hash the framework's copy in `$SOURCE_DIR` |
| `HASH_PRIOR_RECORD` | carry the digest the previous manifest recorded |
| `HASH_CANONICAL_POINTER` | the computed hash of what the pointer heredoc *would* generate |
| `HASH_NONE` | emit no record |
| `LINK_RECORD` | emit `LINK  <relpath>  <target>` instead of a digest |

The two fields are **orthogonal**. `PRESERVE_OWNED` with `HASH_TARGET`
records the adopter's edited bytes as the framework baseline — which is how
a later upgrade comes to overwrite them and `uninstall.sh` comes to delete
them. `PRESERVE_OWNED` with `HASH_PRIOR_RECORD` is the safe reading of the
same intent. Nothing in the branch structure made that choice visible; a
column does.

### 3.3 What this replaces

`FMS_HASH_ROOT_PATHS` and `FMS_LINK_PATHS` are per-path override lists added
during the eleven rounds to narrow two global switches that turned out to be
too wide. They are **special cases of an explicit `hash_source`**, and the
implementation replaces them — it does not keep them alongside it. Adding a
third override list is the failure mode this table exists to prevent.

`FMS_PROTOCOL_HASH` carries **two different meanings** today: the canonical
pointer hash on the upgrade path, and a *prior record digest* on the install
continuity path. Under this model those are `HASH_CANONICAL_POINTER` and
`HASH_PRIOR_RECORD` — distinct values that must not share a channel. See
OQ-4.

### 3.4 `HASH_TARGET` is the default, and it is never distinctly correct

Filling the table surfaced something no single branch could show: across all
61 rows, **`HASH_TARGET` is never the right answer.** It appears only as an
`indistinguishable=` annotation on rows where the target was just written
from the framework's own bytes, so the two candidates are equal by
construction and the distinction is unobservable.

Yet `HASH_TARGET` is precisely what the generator falls back to when no
override is supplied. So the default is right only by coincidence — whenever
target and source agree — and wrong in exactly the situation the override
exists to handle: a preserved adopter edit. Three separate P1 defects are
instances of that one sentence.

This is an argument for making `hash_source` an explicit, required parameter
of the verdict rather than a set of opt-in overrides on a permissive default.
Recorded as evidence for the W1 debate, not decided here.

## 4. Legality rules (pruning)

A cell is **illegal** when the combination cannot occur against a real
target. Every rule below removes cells; **each is named with its reason, and
silent pruning is forbidden** — an unexplained absence from the TSV is
indistinguishable from an oversight, which is how a defect class hides.

| Rule | Statement | Reason |
|---|---|---|
| **R-01** | `operation=install_fresh` ⇒ `prior_record=none` | The manifest is written at the *end* of install. "Fresh" is defined as "no pre-existing manifest", so there is no prior testimony to read. |
| **R-02** | `operation ∈ {install_fresh, install_rerun}` ⇒ `skip_requested=none` | `--skip` is an `upgrade.sh` flag. `install.sh` has no equivalent (verified: zero occurrences). |
| **R-03** | `surface=protocol` ⇒ `source_has=yes` | The pointer is generated from a heredoc, never copied. There is no source file whose absence could be observed. |
| **R-04** | `live_content=legacy_pristine` ⇒ `surface=spec` | The pristine fingerprints are a `SPEC/v1`-tree construct. No equivalent exists, or is needed, for a one-line marker or a generated pointer. |
| **R-05** | `live_type=absent` ⇒ `live_content` undefined | Nothing to hash. |
| **R-06** | `skip_requested=descendant` ⇒ `surface=spec` | Only `SPEC/v1` is a tree. A path *under* a single file cannot exist. |
| **R-07** | `live_type=dir_empty` ⇒ `surface=spec` | For the single-file surfaces, an empty directory and a non-empty one behave identically (both yield no record and both are refused as non-regular). The distinction is only load-bearing where per-file records are emitted. |
| **R-08** | `ceremony=user` ⇒ `surface ∈ {spec, protocol}` cannot yield `DELIVER` or `REFRESH` | WS4 guards forbid root surfaces under a user ceremony. **This prunes verdicts, not cells:** those surfaces still legally *appear* under `ceremony=user` as residue of a prior maintainer install, and those residue cells are exactly where two defects lived. |
| **R-09** | `prior_record ∈ {link_match, link_retargeted}` ∧ `live_type ≠ symlink` ⇒ collapse to `link_retargeted` | `readlink` on a non-symlink yields empty, which never equals a recorded non-empty target. Keeping both would be two names for one observable state. |
| **R-10** | Rows are **equivalence classes**, not raw tuples; a dimension the row's outcome does not depend on is written `*` | Forced, not preferred. The raw product is ~24,000 tuples; at the mandated per-cell timeout the suite could not run in a day, so it would not be run — and an unrun suite is worse than a smaller honest one. `*` is the harness's instruction to instantiate the canonical representative, and any dimension that turns out to matter must be split into explicit rows. |
| **R-11** | `live_type=ancestor_symlink` ⇒ `surface ∈ {spec, marker}` | `PROTOCOL.md` sits at the target root, so between `$TARGET` and the leaf there is **no intermediate component** that could be a symlink. The guard is vacuous there, not missing. |

### 4.2 Conventions carried in the TSV

- `*` — don't-care, per R-10.
- `-` — not applicable under a rule above (e.g. `live_content` when the
  target is absent).
- `note` may carry structured directives alongside prose:
  `fault=<enum>` (an injected environmental failure),
  `indistinguishable=<enum>` (two `hash_source` candidates that are equal by
  construction on this row — the harness reports `AMBIG`, never a lucky
  green), `invariant=<id>`, `open=<round-id>` (a defect this row asserts and
  the current tree does not yet satisfy).

### 4.1 Three draft rules, REJECTED with reason

PLAN-167 §W0.1 offered five pruning rules as "already known". Three of them
are wrong, and adopting them would have deleted cells that hold real
defects. Recording the rejections here so they are not re-proposed.

- **REJECTED: `operation=install_fresh ⇒ live_type=absent`.**
  A maintainer install onto a target that already carries its own `SPEC/v1`
  is precisely the case ADR-155-AMEND-1 §3 cites for why ceremony-conditional
  enumeration is insufficient. `install_one` EXISTS-skips it, and the
  question of whether the adopter's tree gets inventoried as framework-owned
  is the whole point. The cell is legal and important.

- **REJECTED: `prior_record=link_* ⇒ mode=link`.**
  `prior_record` describes the previous run; `mode` describes this one. They
  are independent. `mode=link ∧ prior_record=hash` is an open, unfixed defect
  — a `--link` rerun over a copy-installed surface that has since been
  replaced by a symlink, where the absence of a `LINK` row is read as "no
  mismatch" and an arbitrary live symlink is recorded as a trusted delivery.
  `mode=copy ∧ prior_record=link` is a legal re-run after a mode change.
  Pruning either would delete the finding the table exists to hold.

- **REJECTED: `surface=protocol ⇒ live_type ∈ {absent, regular, symlink}`.**
  Nothing in `_refresh_protocol_pointer` prevents a directory or a FIFO at
  `$TARGET/PROTOCOL.md`. It has neither the non-regular-destination guard nor
  the leaf-symlink guard that `spec` and `marker` both acquired during the
  review rounds — see §5.1. The cell is not illegal; it is **unguarded**, and
  those are opposite things. Pruning it would have converted a live defect
  into an invisible one.

## 5. Cells whose pair is not obvious

Only the reasoning lives here; the pairs themselves are in the TSV.

### 5.1 The `protocol` surface is the family's late sibling

`spec` and `marker` each acquired, over the review rounds, three guards: a
symlinked-ancestor refusal, a leaf-symlink check validated against the prior
`LINK` record, and a refusal of any destination that exists but is not a
regular file. `protocol` acquired **none of them** — and it is the one
surface written with `cat >`, which follows a leaf symlink out of the target
tree, fails hard on a directory (aborting the whole run under
`set -euo pipefail`, mid-upgrade, after other surfaces have changed), and
blocks forever on a FIFO.

Two of those three are real gaps. The third is not: R-11 shows the
ancestor guard is **vacuous** for a root-level leaf, so its absence is
correct rather than missing. That correction is itself the point — the same
sweep that found the gaps also stopped a plausible-looking third "gap" from
being patched into existence.

None of this came from the eleven rounds. It came from asking the question
the table forces: *the same cell, on each surface, must have a declared
answer.* Per PLAN-167 §6 rule 2 it is recorded as rows, not patched
branch-locally.

### 5.4b The instrument was blind to the damage it was built to detect

The first version of this harness compared only the target tree. For the
rows where a surface is a symlink, that is not enough: a write that follows
the link lands **outside** the target, on adopter or system data, and the
target itself is unchanged. Such a row could report GREEN while the run
destroyed a file the test never looked at.

The fixture's foreign file is now a **tripwire**, digested before and after
every run. Any change to it produces status `ESCAPE`, which outranks the
verdict comparison entirely — a row whose pair matches while the run wrote
out of tree has not passed.

Arming it immediately converted a suspicion into evidence. `OWN-0034` — the
`protocol` surface as a leaf symlink — reports `ESCAPE`: `cat >` follows
the link and writes outside the target. `OWN-0044` (a `spec` symlink, which
is correctly preserved) does not, so the tripwire is not simply firing on
every symlink row.

That promotes the §5.1 finding. The missing leaf-symlink guard on the
pointer is not a hypothetical hardening gap; **it is a demonstrated
out-of-tree write**, which is the S238 class the whole baseline-manifest
design exists to close.

### 5.4c `prior_record` is ambiguous, and it matters exactly where it hurts

Running the decision function in shadow mode against the real callers — it
observes and records, it does not act — produced 17 agreements, 2
divergences and 10 rows the caller never reached. One divergence is a model
defect, not an implementation defect.

`prior_record` is defined as "what the pre-run baseline manifest says". There
are **two** such manifests and the definition does not choose between them:

- the **raw** file on disk, and
- the **sanitized** one the loader produces, which drops every record whose
  relpath traverses a symlinked component.

They agree everywhere except on the symlink-traversal rows — which are the
security-critical ones, and the same rows §5.8 is about. An observer reading
the sanitized manifest sees `none` and concludes `PRESERVE_UNOWNED`; an
observer reading the raw file sees `hash` and concludes `OMIT_RECORD`. Both
are defensible readings of a dimension that never said which it meant.

The resolution is not to pick the more convenient one. The **sanitized**
manifest is the authority, because honouring a record whose path crosses a
symlink is precisely what the ADR-155 decision-(v) provenance fence exists
to prevent — but the definition in §2.2 has to say so, and the harness has
to observe the same thing the caller does, or the two instruments will keep
disagreeing about cells neither of them is wrong about.

This is the kind of defect that survives eleven rounds of code review: every
branch reads *a* manifest, each reads a defensible one, and no branch is
individually wrong.

### 5.4d The missing cell was the most important one

The table had nine `protocol` rows and none for the combination that matters
most: an **adopter-customised pointer on a normal (maintainer) upgrade**.
`OWN-0072` covers the same content under `ceremony=user`; the ordinary path
was simply absent.

Deriving its expected pair exposed a **data-loss defect in the proposed
decision function**. For that cell the function returned `REFRESH` — it would
have overwritten a customised root `PROTOCOL.md`. That is the verified S238
loss that ADR-155 decision (iii) exists to close, and the live code has
preserved it correctly all along.

The asymmetry the function was missing is deliberate and is now stated in it:

| Surface | An adopter edit is… | Because |
|---|---|---|
| `SPEC/v1` | a **fork of the contract** → forced refresh | it is the published compliance contract (ADR-155-AMEND-1 §4) |
| `PROTOCOL.md` | **adopter content** → preserved | overwriting it is the verified S238 loss (ADR-155 (iii)) |

Both record a **canonical** digest regardless, because recording the
customised bytes would make the *next* upgrade read `H_dst == H_base` and
clobber them — the C.5 idempotency trap.

Two things are worth separating here. The defect was in the **new** code, not
the old: a refactor that had been driven only by "keep the map green" would
have shipped it, because **no existing row covered the cell**. What found it
was asking the completeness question — *which combinations does this surface
have, and is each one present?* — which is the one question a per-branch
review never asks.

### 5.5 Two findings are invariants, not cells

Two defects were about the **blast radius** of a fix rather than about any
one surface, and encoding them as rows would understate them. The harness
asserts them across every applicable row instead:

- **INV-1** — when ownership continuity fires on an install rerun, no
  enumerated path *outside* the continuity set may change its recorded
  digest. The original defect switched the whole tree's baseline to the
  unrendered source, which reads downstream as repo-wide adopter drift and
  silently stops those files from ever being refreshed again. One row could
  not have caught it; the damage was to the paths the row was not about.
- **INV-2** — `LINK` serialization may cover only paths that were already
  `LINK` records before the run. Otherwise an adopter's own symlink,
  preserved inside an enumerated directory, is promoted into a framework
  delivery record.
- **INV-3** — **an execution failure never advances the record.** A caller
  that was handed `DELIVER` or `REFRESH` and could not complete it must
  leave the manifest describing the world as it actually is. This is the
  correction to the C2 proposal below: "the failure inherits the verdict's
  `hash_source`" would record a delivery that did not happen — the framework
  claiming bytes it never wrote, which is precisely the over-claiming
  direction ADR-155-AMEND-1 §3 forbids. The failure path keeps the record
  the surface had *before* the attempt.

Both are the same shape: a switch that was correct in intent and too wide in
scope. That is the single most common defect class in this space, and it is
invisible to per-cell assertions by construction.

### 5.2 Ownership continuity and the digest it carries

Carrying ownership forward across a run that did not write anything is
correct — dropping the record strands a delivered tree as unowned forever.
But the flag and the digest are separate decisions, and four separate
defects came from moving one without the other. A `PRESERVE_OWNED` verdict
therefore always has an explicitly declared `hash_source`, and
`HASH_TARGET` is never its default.

### 5.3 Deliberate asymmetry: the marker under `--pin`

Where a pinned pre-v1.3.0 source has no marker, the record is **dropped**
rather than carried forward, so that readers fall back to `VERSION` — which
the pin did update. This is the one place where `OMIT_RECORD` is chosen over
`PRESERVE_OWNED` on purpose, and it is recorded here so it is not "fixed"
into consistency with the other surfaces.

Its residual is real and is open as OQ-3: `VERSION` in an *external* target
is adopter-owned and never written by the upgrade, so the fallback can still
report a version newer than the content.

### 5.4 The root `VERSION` file is not a surface

It is out of the enumeration and out of the upgrade, permanently and
deliberately (ADR-155-AMEND-1 §2). It is named here only so that its absence
from the table is not read as an omission.

### 5.6 One amendment to the plan's observation contract, and why

PLAN-167 §W0.3 drafted the observation contract so that `ABORT_SURFACE` was
recognised by *"target unchanged + named warning + rc 0, and **no record**"*.
Implementing it showed that clause is unsound: it makes the verdict field
depend on the `hash_source` field, and §3.2 requires the two to be
orthogonal. Under the draft rule, an `ABORT_SURFACE` that legitimately keeps
a prior record would be observed as `PRESERVE_OWNED` — which is precisely
the distinction OQ-2 exists to settle, silently pre-decided by the
instrument that was supposed to measure it.

The harness therefore recognises `ABORT_SURFACE` by the **refusal being
emitted at all** — the framework attempted and declined — and reads the
record independently. A refusal leaves no filesystem trace by construction,
so this is matched against a small declared set of operator-visible markers.
That coupling is deliberate and is the reason it is written down: if the
wording changes, these rows fail, and they *should* — the operator-visible
contract is part of what `ABORT_SURFACE` promises.

The harness also emits `HASH_UNCLASSIFIED` when a recorded digest matches
none of the four candidates. That is never an expected value: it means the
manifest recorded something the model has no name for, which is a gap in the
enum rather than a failing row.

**`REFRESH` versus `PRESERVE` has no single sound signal.** When the incoming
content equals what is already on disk, a refresh changes no bytes, and three
candidate observables each fail somewhere:

| Signal | Fails because |
|---|---|
| content digest | an identical-content refresh is invisible to it |
| backup presence | the ADOPTER-FORK *preserve* path also snapshots — a backup proves the framework **looked**, not that it wrote |
| modification time | `install.sh` re-runs placeholder substitution every invocation, rewriting the pointer with identical bytes and a fresh mtime — a write with no semantic content |

The harness uses mtime, and **only on the upgrade path**, where the forced
route is the one thing that rewrites these surfaces. The boundary is stated
rather than assumed, because each of these signals looked universal until a
row proved otherwise — and two of them were adopted, and withdrawn, during
this work.

The general lesson is worth more than the mechanism: in a space this shape,
**the instrument needs the same adversarial scrutiny as the subject.** Five
separate fixture defects were found while building this baseline, four of
which produced a confident green or red that meant nothing.

### 5.7 A guard placed on the right route, reached too late

The `special`-file rows do not fail where they were expected to. The upgrade
never reaches the SPEC or marker route at all: an earlier stage —
`_emit_deprecation_warnings`, which shells out to a scanner that walks the
whole target tree — opens the FIFO and blocks forever. The run dies before
any surface is refreshed.

Verified in isolation with both controls: the scanner alone, given a target
whose only anomaly is a FIFO at the marker path, hangs indefinitely; the same
scanner on the same tree with a regular file there exits 0.

Two consequences, and the second is the more important one:

1. It is a **new defect of a class the eleven rounds did not reach**. The
   special-file guards were placed on the three routes that *own* the
   surfaces. A tree-walking reader that runs earlier needs the same guard,
   and does not have it.
2. It means the existing guards are **masked**: no end-to-end run can
   demonstrate that the FIFO branch of `_refresh_spec_contract` works,
   because control never arrives there. A green suite would have proven
   nothing about them. The table found this by asserting an outcome the
   route was believed to produce and observing that the process died first.

Per PLAN-167 §6 rule 2 this is recorded, not patched branch-locally. Per
rule 5 the family sweep it implies is broader than the three surfaces: every
tree-walking reader invoked during an upgrade is in scope.

### 5.8 A continuity branch that cannot fire

The symlinked-ancestor guard on `spec` and `marker` ends with a line that
carries ownership forward when the pre-upgrade baseline holds a record. That
line is **unreachable**.

The relpath sanitizer rejects any record whose path traverses a symlinked
component, and it runs when the manifest is *loaded* — before
`_baseline_has_spec_record` is ever consulted. In the one situation the
continuity line was written for, the record it looks for has already been
removed from the sanitized manifest. The observable outcome is
`OMIT_RECORD`, never the intended `PRESERVE_OWNED`.

The table therefore expects `OMIT_RECORD` here — but the fix is **not** to
make the branch fire. Making it fire would mean honouring a record whose
path crosses a symlink, which is exactly the provenance fence ADR-155
decision (v) exists to enforce. Under-claiming ownership is the recoverable
direction (ADR-155-AMEND-1 §3). The branch should be **deleted as dead
code**, because a line that promises something it cannot deliver is worse
than no line: it reads, to the next maintainer, like a guarantee.

## 6. Open questions — the W1 debate agenda

These are the points where the three input authorities — the eleven review
verdicts, the live branch, and ADR-155/AMEND-1 — do **not** agree. PLAN-167
§W0.1 requires that they be recorded rather than resolved unilaterally.

- **OQ-1 — Is `ABORT_SURFACE` one verdict or two?**
  A failed backup and an unsupported special file both leave the target
  untouched with a named warning, but they differ in whether the framework
  *could* have proceeded. If the manifest outcome is identical, the enum
  should merge them; if the operator's next action differs, it should not.

- **OQ-2 — What is the `hash_source` of `ABORT_SURFACE` when a prior record
  exists?** Refusing to touch a surface is not evidence about ownership. The
  live code answers this differently on different branches.

- **OQ-3 — Version reporting under an external-target `--pin` downgrade.**
  Dropping the marker record makes readers fall back to a `VERSION` the
  upgrade never writes on an external target. A truthful signal requires
  deriving from the pinned source; that is a new mechanism, not a cell.

- **OQ-4 — Splitting `FMS_PROTOCOL_HASH`.** It carries
  `HASH_CANONICAL_POINTER` on one path and `HASH_PRIOR_RECORD` on another.
  Splitting is the model-faithful move; it also changes a canonical-guarded
  signature.

- **OQ-5 — Where does `_ownership_verdict()` live?**
  A new library file is a new canonical path, which requires a
  `_CANONICAL_GUARDS` entry and therefore a kernel ceremony. PLAN-167 §4
  states a preference for the already-guarded
  `scripts/_framework_manifest_set.sh` absent a reasoned veto. A veto
  escalates to the Owner — it does not become an overnight kernel ceremony.

- **OQ-6 — Does `install_rerun` need `--skip`?** R-02 prunes the whole
  column for install today. If the answer is "install should honour skips
  too", that is a feature decision, and the pruned cells become legal.

- **OQ-7 — RESOLVED in round 1.** `fault` is now a real column (§2.10) and
  `legacy_pristine_partial` a real `live_content` value. Both were prose
  directives; both are now dimensions. The text below is kept as the record
  of the question.

  ~~**`fault` is a tenth axis the column contract does not have.**~~
  Three defects are reachable only under an injected environmental failure
  (an unwritable backup directory). That is not a property of the target, so
  it is not `live_type`; it is a genuine tenth dimension. PLAN-167 §W0.2
  froze the TSV at fourteen columns, so it currently rides in `note` as
  `fault=<enum>`. This is **declared, not smuggled**: the debate should
  either bless a fifteenth column or rule those rows out of scope. Leaving
  it in free text is the one option that should not survive — a dimension
  the harness parses out of prose is a dimension nothing validates.

- **OQ-9 — Is `OMIT_RECORD` an independent verdict at all?**
  *New evidence from the shadow run:* the `OWN-0030` divergence exists ONLY
  because the two instruments answer different questions — the suite asks
  "did a record disappear?" and the function asks "was there a trustworthy
  prior record?". Both end with no record on disk. **If the two verdicts
  collapse into one, that divergence stops existing**, which is a second,
  independent argument for the collapse: a distinction that generates
  disagreement while having no observable consequence is not carrying its
  weight.
  Filling the table, every `OMIT_RECORD` row turned out to be a row that would
  read `PRESERVE_UNOWNED` if no prior record had existed. The two are not
  separate outcomes: they are the same outcome observed at different values of
  `prior_record`, which is already a column. If that holds under scrutiny, the
  enum has five verdicts, not six — and a redundant enum member is a place for
  two branches to disagree about which one applies.

- **OQ-10 — `--on-conflict` is an eleventh dimension.**
  Surfacing §5.4d's cell also surfaced its modifier: the live code branches on
  `--on-conflict={refuse|theirs|backup}` for exactly that cell, and `theirs`
  or `backup` invert the outcome from preserve to overwrite. The nine
  dimensions cannot express it, so the table currently describes the default
  (`refuse`) only. Either it becomes a dimension or the table states in one
  line that it is default-scoped — silence is the option §4 forbids.

- **OQ-8 — Does the table cover readers, or only writers?**
  One defect was a *reader* trusting a delivered-then-edited marker and
  therefore suppressing a real update. Its cure follows from the same pair,
  but the observation contract in `test-ownership-table.sh` derives the
  verdict from (target state, manifest) — the reader is a third observable.
  Either the contract grows a third channel, or reader rules live in a
  sibling table.

## 7. How to change this table

1. A new defect becomes **a row**, never a branch-local patch.
2. A finding that does not fit as a row is a **gap in the model**: record it
   and escalate. Do not reshape the finding to fit.
3. Removing a combination requires a **named rule in §4 with its reason**.
4. Changing a pair in the TSV without changing the reasoning here — or the
   reverse — means the two artifacts have drifted. The TSV wins on values;
   this document wins on why.

## 8. Origin ledger — where the 35 review findings went

PLAN-167 AC-5 requires a **literal enumeration**, not a count. Reading all
eleven verdicts end to end yields **35** distinct findings, not the 24 the
session summary recorded — so the count itself was wrong, which is why the
acceptance criterion demands enumeration. Every one is dispositioned:

| Disposition | Count | Findings |
|---|---:|---|
| Became one or more TSV rows | 29 | r1-F1..F3, r2-F1..F3, r3-F1..F2, r4-F2..F5, r5-F1..F3, r6-F1, r7-F1..F3, r8-F2, r9-F1..F4, r10-F1, r10-F3, r11-F1..F3 |
| Became a cross-surface invariant (§5.5) | 2 | r8-F1 → INV-1, r10-F2 → INV-2 |
| **Not a cell of this space** | 4 | r4-F1, r8-F3 (landing-script / CI-ledger hygiene), r10-F4 (CI path filter), r11-F4 (`INSTALL.md` forensic guidance) |

The four non-cells are **not dismissed** — they are real, and three of them
already landed. They are recorded here so that "absent from the TSV" can
never be confused with "forgotten". They do not belong to the ownership
decision space: they concern whether CI *runs* the tests and whether the
documented procedures match the code, which no per-cell assertion can
express.

Rows also exist that no finding produced — the `derived` origin. Those come
from the family sweep in §5.1. That a systematic pass over a nine-column
space found defects eleven sequential review rounds did not is the argument
for the table, stated as evidence rather than as a claim.
