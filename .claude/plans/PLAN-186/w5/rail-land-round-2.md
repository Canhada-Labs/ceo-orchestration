Rail-Verdict: CHANGES-REQUESTED (1 P2 — REAL, reproduced on disk by the lander, cured in the pack derivator with a frozen case)

# Pair-rail round 2 — land of `ac14-classifier-v2` (S343, autonomous night run)

* **Instrument:** `codex exec review --uncommitted --skip-git-repo-check`
  (`gpt-5.6-sol`), run from the repository root against the tree carrying the
  round-1 cure, applied and staged.
* Round 1's finding does not reappear.

## Finding — [P2] a valid but deeply nested fixture broke the checker's own rc contract

The checker's docstring publishes three exit codes: 0 consistent, 1 a NAMED
inconsistency, 2 input the gate cannot read. The reviewer observed that
`json.loads` raises `RecursionError` — which is **not** a `ValueError` — on a
document that is syntactically valid but nested deeper than the decoder's
recursion limit, so it walked straight out of `run()` as an uncaught traceback
at rc 1: the code reserved for a real finding.

**Positive control, run by the lander before the cure** (`control_recursion.py`,
a real subprocess, 2000 nested arrays written into the scratchpad, never into
the repo):

```
rc=1
last-line: RecursionError: maximum recursion depth exceeded while decoding a JSON array from a unicode string
traceback-present: True
```

This is the same class the pack itself cured in its own round 4 (the symlink
loop raising `RuntimeError` past an `except (ValueError, OSError)`): a
non-obvious exception type escaping a guard whose contract promises rc 2.

**Cure (in the derivator):** two anchored edits, each expected exactly once —
the checker's `json.loads` guard becomes `except (ValueError, RecursionError)`
and names the exception class in the refusal, and the shipped rc-contract test
gains a permanent **case 14** that asserts the PROCESS exit status and the
ABSENCE of a traceback for the same 2000-deep input.

**Verification after the cure — the same control, same command:**

```
rc=2
last-line: check-classifier-cases: fixture is not decodable as JSON (RecursionError): maximum recursion depth exceeded while decoding a JSON array from a unicode string
traceback-present: False
```

plus oracle rc 0 CONSISTENT (7 rows, 7 terminals, 10 cases, 20 citations) and
the shipped test at **14 passed** (was 13).
