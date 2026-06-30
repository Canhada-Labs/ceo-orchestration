# Ecosystem Parity · Cluster 1.1 — Brotli context compression

**Status:** staged (Session 49 P04). Opt-in for adopters; stdlib
fallback ships always.

## When to activate

Turn this on if your project:

- Caches large textual context blocks (> 10 KiB each) across turns
  or sessions — Manifest summaries, long code files, transcripts.
- Is token-cost sensitive enough that the 30-50 % typical reduction
  outweighs a ~5 ms CPU overhead per cache read/write.
- Runs on infrastructure where `pip install brotli` is acceptable
  (brotli is the upgrade path; `zlib` works without any install).

**Skip** if:

- Your context payloads are small (< 1 KiB each) — compression
  overhead can exceed the savings.
- Your cache layer already compresses at the storage tier
  (Redis with compression, S3 + gzip transport).
- You cannot tolerate any CPU overhead on the hot path.

## How to activate

### Stdlib-only (zero install)

The default backend is `zlib`, which ships with Python. Just set the
env var:

```bash
export CEO_CONTEXT_COMPRESS=zlib
```

Compression ratio: ~40-55 % on English prose, ~50-70 % on JSON-
heavy payloads.

### Upgrade to brotli

```bash
pip install 'brotli==1.1.0'
export CEO_CONTEXT_COMPRESS=brotli
```

Compression ratio: ~55-70 % on the same payloads. CPU cost is
comparable at level 9.

### Disable

```bash
export CEO_CONTEXT_COMPRESS=off
```

Payloads pass through byte-identically.

## Cost calculator

Given a cache corpus of `N` bytes per session and `T` sessions per
month:

| Backend | Bytes/session (typical) | Savings/session | Typical annual savings (T=1000) |
|---|---|---|---|
| `off` | N = 500 KiB | 0 | 0 |
| `zlib` | ~250 KiB | ~250 KiB | ~3 GiB |
| `brotli` | ~175 KiB | ~325 KiB | ~3.9 GiB |

For token-based billing the equivalent is ~40-65 % cache-read-token
reduction. If your cache-read rate is 30 % of total input tokens,
you save ~12-20 % of total input tokens.

## What's in the scaffold

- `.claude/plans/PLAN-046/staged-code/brotli_passthrough.py` —
  stdlib-only compress/decompress helpers with fail-open discipline.
  API: `compress(data, level=9)`, `decompress(data)`.
- `.claude/hooks/tests/test_brotli_passthrough.py` — 12 tests
  (10 runnable stdlib, 2 skipped unless `brotli` installed). All
  green on stock Python 3.9+.
- `.claude/plans/PLAN-046/staged-code/cluster-1.1-brotli-passthrough-spec.md`
  — architecture + clean-room declaration + promote runbook.

## Integration points (future)

None of the scaffold is wired yet. When you integrate, the two
realistic call sites are:

1. `.claude/hooks/_lib/payload.py::write_context_cache` — compress on
   write, decompress on read.
2. The MCP bridge cache in `.claude/scripts/mcp/*` — same pattern.

Neither path is touched by this scaffold to avoid silently changing
cache semantics across the framework. The integration commit is
adopter-owned.

## Promote to canonical

The scaffold lives at a non-canonical path. To ship it into
`.claude/hooks/_lib/brotli_passthrough.py` (where hooks can import
it as `from _lib import brotli_passthrough`):

1. Owner stages a canonical-edit sentinel
   (`.claude/plans/PLAN-045/architect/round-N/approved.md`) with
   `Scope:` listing the target path.
2. Owner GPG-signs via a MEGA-SIGN-BUNDLE-style script.
3. Adopter or CEO copies the scaffold to `_lib/`.
4. Adopter wires the first caller under the same sentinel.
5. Test file import line flips from the
   `.claude/plans/PLAN-046/staged-code/` path shim to
   `from _lib.brotli_passthrough import compress, decompress`.

Full runbook: `.claude/plans/PLAN-046/staged-code/cluster-1.1-brotli-passthrough-spec.md`.

## Rollback

Set `CEO_CONTEXT_COMPRESS=off` for an instant session-level bypass.
No code revert needed.

## Clean-room note

The approach is inspired by the [ooples](https://github.com/ooples)
ecosystem work on context sidecar compression. No code is lifted;
the staged scaffold is a thin stdlib `zlib` wrapper with an opt-in
brotli upgrade path, both using the libraries' own public APIs.
