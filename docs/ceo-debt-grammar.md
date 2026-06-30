# `# CEO-DEBT:` grammar — the inline-debt ledger

> **Advisory. Nightly-only. Derived.** This marker grammar lets you
> annotate a deliberate in-code shortcut that lives *below* the ADR/PLAN
> bar — too small for an architecture decision record, but worth a paper
> trail. A nightly read-only sweep harvests every marker into a derived
> ledger and flags the ones that are *ungoverned*.
>
> Scanner: [`.claude/scripts/check-debt-ledger.py`](../.claude/scripts/check-debt-ledger.py).

## Why this exists

Most technical debt in this framework is already governed: it points at a
PLAN or an ADR (`DEFERRED to PLAN-NNN`, `REFUSED — see ADR-NNN`). Those
artifacts carry their own review and exit criteria.

But some shortcuts are genuinely smaller than that — a hardcoded ceiling,
a temporary cap, a "good enough for now" path — that still deserve to be
*visible* and to carry an explicit condition under which they must be
revisited. The `# CEO-DEBT:` marker is for exactly those. It is **not** a
replacement for a PLAN or ADR; it is the rung below them.

**Honest note:** there are **0** `# CEO-DEBT:` markers in the tree today,
and that is the intended steady state. This is forward-facing
infrastructure, not a backlog report. An empty ledger
(`0 markers, 0 ungoverned`) is success, not a gap.

## The grammar

```
# CEO-DEBT: <ceiling>, <upgrade-trigger>
```

| Part | Meaning |
|---|---|
| `# CEO-DEBT:` | The **UPPERCASE**, line-anchored sentinel. Required exactly. |
| `<ceiling>` | The shortcut / cap / compromise being taken. |
| `, <upgrade-trigger>` | The condition under which this debt **must** be revisited. |

Rules the scanner enforces:

- **UPPERCASE only.** A bare lowercase `# ceo-debt:` does **not** match —
  it would collide with ordinary comments. Only the uppercase token is a
  marker.
- **Line-anchored.** The marker must be at the start of a line, optionally
  preceded by whitespace and/or a Markdown code-fence indent. A
  `# CEO-DEBT:` appearing mid-line (after code) is **not** a marker.
- **Inert payload.** Everything after the token is treated as data. It is
  never evaluated, executed, or shelled out. Matching uses a single
  non-backtracking, line-anchored regex (ReDoS-safe).

## Governed vs ungoverned

The payload is split on its **first comma**:

- **Governed** — there is a non-empty upgrade-trigger after the comma. The
  author named the condition that retires this shortcut.

  ```python
  # CEO-DEBT: cap retries at 3, when the upstream adds idempotency keys
  ```

- **Ungoverned** — there is **no comma**, or the second field is empty.
  The debt has a ceiling but no exit condition, so the ledger **flags**
  it.

  ```python
  # CEO-DEBT: cap retries at 3
  ```

The footer of the ledger reports both totals in the
`check-staleness.py` output style:

```
N markers, M ungoverned
```

## What does NOT count

- **Prose mentions.** Writing the words "ceo-debt" or "CEO-DEBT" in a
  sentence, a heading, or documentation is never counted. Only a real
  line-anchored marker comment is.
- **Lowercase token.** `# ceo-debt:` is ignored by design.
- **Vendored / generated / fixture trees.** The walk prunes
  `{.git, npm, dist, node_modules, venv, .codex, staged, .plan138-bak,
  _lib_archived, __pycache__, archive, worktrees}` plus the scanner's own
  `tests/` fixtures dir and its own source file — so grammar examples
  (including the ones on this page) never inflate the count.

## Running it

```bash
# Human-readable ledger (advisory; always exits 0)
python3 .claude/scripts/check-debt-ledger.py

# Machine-readable
python3 .claude/scripts/check-debt-ledger.py --json

# Scan a different tree
python3 .claude/scripts/check-debt-ledger.py --repo /path/to/repo
```

It is wired as a read-only dimension of the `nightly-hygiene` saved
Workflow. There is deliberately **no per-validate step**: the ledger is
derived on demand and never written to a stored file (a stored ledger
would drift from the source of truth).
