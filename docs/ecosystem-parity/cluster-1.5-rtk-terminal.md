# Ecosystem Parity · Cluster 1.5 — Terminal-output compression

**Status:** staged (Session 49 P04). Opt-in but zero install.
Inspiration: rtk repo (clean-room).

## When to activate

Turn this on if your sub-agents or hooks regularly feed large
terminal outputs back to the LLM as tool results:

- Long `grep -r` / `ripgrep` outputs
- `ls -l`, `find`, `ps aux`, `netstat -anp` traces
- `cat` of large fixture files with trailing whitespace
- ANSI-colored output from linters, test runners

Typical savings: **70-90 %** of output tokens on these shapes.

**Skip** if:

- Your tool-result payloads are small (< 200 bytes).
- You rely on exact byte-for-byte preservation of ANSI colors in
  downstream processing (rare for LLM-fed context).

## How to activate

Zero install. Just flip the env var:

```bash
export CEO_TERMINAL_COMPRESS=on   # default — you may not need to set it
```

If you want ANSI strip + whitespace normalization but **not** the
prefix-collapse pass (which is the most aggressive):

```bash
export CEO_TERMINAL_COMPRESS=on
export CEO_TERMINAL_COMPRESS_COLLAPSE=off
```

To disable entirely:

```bash
export CEO_TERMINAL_COMPRESS=off
```

## What each pass does

| Pass | Removes | Preserves |
|---|---|---|
| ANSI strip | `\x1b[…]` control codes, box-drawing chars | colored text content |
| Whitespace normalize | trailing spaces, 3+ blank-line runs | blank lines (capped at 2 consecutive) |
| Prefix collapse | middle lines in runs of 4+ lines sharing a 6+ char prefix | first + last line of each run |

## Cost calculator

Given `N` bytes of terminal capture per tool-call and `C` tool-calls
per session:

| Input shape | Typical input | Typical compressed | Savings |
|---|---|---|---|
| `ls -l` 200 files | 12 KiB | 1.5 KiB | 87 % |
| `grep -n foo src/*` hit in 30 files | 4 KiB | 1 KiB | 75 % |
| colored linter output 100 lines | 8 KiB | 2 KiB | 75 % |
| `cat fixture.json` dense | 3 KiB | 2.6 KiB | 13 % |
| single-line `echo hi` | 3 B | 3 B | 0 % |

## What's in the scaffold

- `.claude/plans/PLAN-046/staged-code/terminal_compress.py` —
  3-pass compressor + `ratio()` telemetry helper.
- `.claude/hooks/tests/test_terminal_compress.py` — 15 tests.
- `.claude/plans/PLAN-046/staged-code/cluster-1.5-rtk-passthrough-spec.md`
  — architecture + promote runbook.

## Integration points (future)

The realistic call site is `_lib/payload.py::sanitize_tool_result`
(or wherever your framework packs a Bash tool-result into the next
turn's context). The integration commit is adopter-owned so the
first adopter can validate corpus-specific behavior before promoting
the path into the canonical hook graph.

## Promote to canonical

Same pattern as Cluster 1.1:

1. Owner-signed sentinel listing
   `.claude/hooks/_lib/terminal_compress.py` in `Scope:`.
2. Copy scaffold → `_lib/terminal_compress.py`.
3. Wire first caller.
4. Flip test import.

Full runbook: `.claude/plans/PLAN-046/staged-code/cluster-1.5-rtk-passthrough-spec.md`.

## Rollback

`CEO_TERMINAL_COMPRESS=off` — instant. No revert required.

## Clean-room note

The ANSI-strip regex (`\x1b\[…]`) is standard ECMA-48. The
prefix-collapse algorithm is a simple longest-common-prefix walk,
no proprietary technique. No code is lifted from rtk.
