# PLAN-156 W0a/W3 — double-fire INVOCATION-COUNT positive control (S269)

> Debate C6 / Sec R-SEC5 acceptance: the double-fire resolution must be
> proven by an invocation-COUNT control (total == 1: chosen surface == 1,
> non-chosen == 0), NOT a deny-observed test — a deny-only test cannot
> distinguish fired-twice / fired-once / never-fired (the C3 dead-gate
> class). This is a LOCAL T2 artifact (needs the grok binary); the CI
> tier is hermetic and covers the exit-2 chokepoint, not the live
> double-fire (no grok binary on any runner — acceptance criterion).

## Method

A recorder hook appends one line per invocation, tagged by which surface
registered it (`surface-native` = `.grok/hooks/`, `surface-legacy` =
`.claude/settings.json`). One tool call is driven; the lines are counted
per `toolUseId`. All runs: `grok -p … --trust --yolo --sandbox workspace
--no-leader --max-turns 3` on grok 0.2.93.

## Results (counts per single tool call)

| Config | surface-legacy | surface-native | total | verdict |
|---|---|---|---|---|
| BOTH surfaces armed | 1 | 1 | **2** | double-fire CONFIRMED (same toolUseId) |
| BOTH + `[compat.claude] hooks=false` (project `.grok/config.toml`) | 1 | 1 | **2** | kill switch INERT (project config not read) |
| BOTH + `GROK_CLAUDE_HOOKS_ENABLED=0` | 1 | 1 | **2** | `[disabled]` in `grok inspect`, runtime STILL fires |
| BOTH + env + `--no-leader` | 1 | 1 | **2** | not a stale-leader artifact |
| **legacy-only** (`.claude/settings.json`; no `.grok/hooks/`) | **1** | **0** | **1** | ✅ the shipped configuration |

The chosen configuration (legacy-only) is the ONLY one that yields
total == 1. Every attempt to keep both surfaces and disable one at
runtime failed on 0.2.93 — both compat kill switches are inspect-only.

## Why this forces the OQ1 inversion

The plan drafted OQ1 as "ship native `.grok/hooks/` (recommended)". The
count control inverts it: with native present you cannot avoid the
legacy surface firing too (grok reads `.claude/settings.json`
unconditionally as compat, and the toggle that should suppress it is a
runtime no-op). A double-fired `audit_log.py` append is an HMAC
double-count + filelock race — a correctness defect, not cosmetic. So
the sound resolution is single-surface, and the surface grok reads
natively-without-us-shipping-a-file is the legacy one. The framework
therefore ships NO `.grok/hooks/` and guards `.grok/hooks/**` so nothing
re-arms it (SENT-GK-E). Re-test this table on every grok pin bump
(substrate-watch item): if a future release honors the kill switch, the
native surface becomes available again.

## Raw fixtures

`grok-wire-fixtures-0.2.93.ndjson` (this directory) — the envelopes that
each surface received; note the LEGACY surface received a GROK-shaped
camelCase envelope (native `toolName`), not a Claude-shaped one, so a
legacy-surface hook still needs `CEO_HOOK_ADAPTER=grok` to parse it.
