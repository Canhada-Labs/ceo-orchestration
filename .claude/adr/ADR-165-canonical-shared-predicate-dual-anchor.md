# ADR-165 — `_is_canonical` dual-anchor: shared-predicate path resolution (finding D)

- **Status:** accepted
- **Date:** 2026-07-17
- **Plan:** PLAN-160 (finding D)
- **Blast radius:** L3 (kernel security gate + shared classification predicate consumed by the `--is-canonical` CLI oracle; `.claude/hooks/check_canonical_edit.py`)
- **Debate:** PLAN-160 round-1 (3 critics, 3× ADJUST → PROCEED; SK1/SK6 unseen-consumer + most-restrictive anchoring) — `.claude/plans/PLAN-160/debate/round-1/consensus.md`
- **Council origin:** S276 Wave-4 live-fire (`wf_cd40731f-205`), finding D, CEO-verified

## Context

**Finding D — relative-path classification bypass (MED).** `_is_canonical`
resolved the target path against the **process CWD**:

```python
rel = p.resolve().relative_to(repo_root.resolve())   # p.resolve() anchors to CWD
```

where `repo_root = CLAUDE_PROJECT_DIR or os.getcwd()`. When a hook event
carries a **relative** `file_path` for a canonical file and the process CWD
is **not** `CLAUDE_PROJECT_DIR`, `p.resolve()` lands outside `repo_root`,
`relative_to` raises, `_is_canonical` returns **False**, and the unsigned
edit to a governance path is **allowed**. The Wave-1 repro invokes the hook
via a subprocess with `cwd` outside `CLAUDE_PROJECT_DIR` (never `os.chdir` —
xdist-flake) and asserts HEAD allows the relative canonical edit; the
absolute-path twin control confirms absolute classification is unchanged.

`_is_canonical` is **not** a local helper — it is a **shared predicate** with
three consumers (round-1 debate SK1, previously unseen):

1. the Layer-A / `decide()` edit-time guard (this hook);
2. `_candidate_is_granted` (the finding-A most-restrictive scan, ADR-164);
3. the **`--is-canonical` CLI oracle** (`_cli_is_canonical`, PLAN-156-FOLLOWUP
   F5) — the single source of truth the grok/codex pre-push review gates
   shell out to, so they never re-implement the guard glob list in bash.

Any change to `_is_canonical` therefore changes the oracle's classification,
which the pre-push gates depend on. This is why finding D gets its **own**
ADR (debate SK1).

## Decision

**Dual-anchor, most-restrictive-wins, via a single source of truth.** A
relative path is resolved against **both** the process CWD (historical) and
`repo_root`; it classifies canonical if **either** anchoring lands inside the
repo and matches a guard. Implemented as one resolution helper reused by all
consumers so they can never disagree:

- `_repo_rels(path_str, repo_root)` returns all repo-relative POSIX forms
  (0, 1, or 2 entries). For an **absolute** path it yields only the CWD-form
  (`repo_root / p` discards `repo_root` when `p` is absolute), so absolute
  classification **and** per-call resolve cost stay **byte-identical** on the
  Edit/Write hot path. Relative paths additionally yield the `repo_root`-
  anchored form.
- `_canonical_rel(path_str, repo_root)` returns the first `_repo_rels` entry
  that matches a canonical guard, or `None`. This is the single source of
  truth for BOTH canonicality (`_is_canonical` = `_canonical_rel is not None`)
  AND the repo-relative form used for sentinel matching in `decide()` and the
  grant check — so a canonical path is always paired with the exact rel that
  classified it (a `repo_root`-anchored canonical path would otherwise fault
  the CWD-anchored `decide()` resolve and route a clean sentinel-block through
  finding C's fault branch).

The change **widens** classification (relative paths from a foreign CWD now
classify canonical → **more** blocks), and **never narrows** it. That
direction is correct for a guard AND for the oracle: over-triggering review
is the oracle's own documented safe direction (`_cli_is_canonical` fails a
per-path classification fault to `1`/canonical by design).

## Oracle-contract impact (the reason D is its own ADR)

- The oracle's `repo_root` resolution is **unchanged** (`CLAUDE_PROJECT_DIR`
  or cwd) — the dual-anchor changes how the **candidate path** is anchored,
  not `repo_root`. The oracle docstring's "repo root resolves exactly like
  the hook" invariant stays true.
- The pre-push gates invoke the oracle from the **repo root**
  (`cwd == repo_root`), where CWD-anchoring already lands inside the repo, so
  the second anchoring is redundant and the oracle's output is **unchanged
  for its designed invocation**. The dual-anchor only alters classification
  in the anomalous `cwd != repo_root` relative case — and there it moves in
  the **fail-CLOSED / over-trigger** direction the oracle already commits to.
- **Wave-3 preflight exercises the CLI oracle path**, not just the hook, so a
  regression in the oracle's contract is caught before the sentinel signs.

## Alternatives considered

- **Anchor only against `repo_root` (drop CWD-anchoring).** Rejected — would
  change absolute-path and normal-CWD classification (not byte-identical) and
  risk narrowing some existing-canonical classification; most-restrictive
  union is strictly safer.
- **Fix only the hook's `decide()`, leave `_is_canonical` alone.** Rejected —
  the bypass is in the shared classifier; fixing only `decide()` would leave
  the oracle (and thus the pre-push gates) blind to the same relative path.
- **`_candidate_is_granted` also dual-anchors the grant check.** Rejected —
  for a GRANT decision, most-restrictive means *harder to grant*: a candidate
  that does not cleanly resolve repo-relative is treated as ungranted
  (→ offender → block), never granted. Grant uses `_canonical_rel` (the rel
  that classified it canonical), so grant and classification agree without
  widening what counts as granted.

## Residual risk (pair-rail, accepted)

- **Theoretical over-block (security review nit).** A relative `path_str`
  from a foreign CWD whose `repo_root`-anchored form matches a canonical
  guard is classified canonical and gated, even though the write's real
  filesystem target (resolved against the tool's CWD) is a non-repo file
  (`/tmp/elsewhere/.claude/team.md`). This is the **fail-CLOSED** direction
  (block a possibly-benign write), which CLAUDE.md §4 tolerates far more than
  the inverse (allowing an unsigned canonical edit). Classification only
  **widens** (`_repo_rels` = CWD-form ∪ repo_root-form, a superset of HEAD),
  so it can never open a bypass. Confined to relative paths with
  `cwd != repo_root`; Claude Code Edit/Write pass absolute paths, and MCP /
  apply_patch relative paths under the normal `cwd == repo_root` are
  unaffected. Accepted as fail-closed-safe.
- **`_repo_rels` totality (`except Exception`).** Broadening the per-anchoring
  catch from `(ValueError, OSError)` to `Exception` (so a symlink-loop
  `RuntimeError` cannot make `_is_canonical` raise — see ADR-164's finding-A
  blocker) means a genuinely-canonical path whose resolve *transiently* faults
  is classified non-canonical → allowed. This matches HEAD's behavior for a
  raising path (HEAD's `except: continue` had the same effect), and the write
  itself fails at the OS layer; the multi-candidate scan still gates every
  OTHER candidate. Accepted.

## Consequences

- Relative canonical edits from a foreign CWD are now gated (hook) and
  reported canonical (oracle) — closes the bypass on both surfaces.
- Absolute-path and normal-CWD classification is byte-identical (regression:
  the absolute-twin control + the byte-identity fuzzer).
- `_repo_rels`/`_canonical_rel` are the single anchoring source; future
  consumers must route through them, never re-derive a CWD-only resolve.
- Regression coverage: the finding-D repro + absolute twin + the behavioral
  C-property (which now exercises the widened canonical set) in
  `.claude/hooks/tests/test_canonical_edit_council_findings.py`, plus the
  Wave-3 oracle-probe preflight.

## References

- PLAN-156-FOLLOWUP F5 (`--is-canonical` oracle, `_cli_is_canonical`).
- Findings A + C (multi-candidate policy + fail-closed resolve) — see
  **ADR-164**.
