---
description: Live preflight — resolve framework paths + writability, print effective settings, optional cheap model round-trip with latency; exits non-zero for CI — /ceo-info
allowed-tools: Bash
---

# /ceo-info — live preflight & effective config

PLAN-133 item [G4] (Wave G). A Goose-harvest port of `goose info --check`:
one command that resolves the framework's runtime paths (audit-log, native
memory dir, plans dir), checks each is **present + writable**, prints the
**effective settings** (which `settings.json` won + active `CEO_*`/`CLAUDE_*`
env overrides), and — opt-in only — performs ONE cheap model round-trip and
reports its latency. Designed to **exit non-zero for CI** when a required path
is missing or non-writable so a misconfigured adopter fails fast.

The backing script is stdlib-only and **fail-open on infra** — a probe that
cannot resolve degrades to a descriptive status, never a traceback.

## Arguments received

`/ceo-info $ARGUMENTS`

| Flag | Effect |
|------|--------|
| `--check` | exit **non-zero** if any required path is missing/non-writable (CI gate). Without it the command is advisory and always exits 0, like `/status`. |
| `--json` | emit machine-readable JSON instead of the human block. |
| `--live` | opt into the live model round-trip (default-OFF). Equivalent to `CEO_INFO_LIVE_PROBE=1`. |

## Procedure

Run the backing script with the received arguments:

```bash
python3 .claude/scripts/ceo-info.py $ARGUMENTS
```

Then summarize the output for the Owner in 2-3 lines: the **overall** verdict,
any **RED** path (the actionable blocker), and — if `--live`/`--json` was
passed — the round-trip latency.

## Default-OFF live round-trip (doctrine §3.1)

The live model round-trip is a **behavioral / network change**, so it is
default-OFF behind the `CEO_INFO_LIVE_PROBE` env flag (or the explicit `--live`
flag). It targets the token-counting endpoint (`/v1/messages/count_tokens`),
which **bills zero tokens**, and uses the cheapest model
(`claude-haiku-4-5`, overridable via `CEO_INFO_PROBE_MODEL`). It runs only when
opted in AND a credential is present; it never echoes the credential and
**fail-opens** to a `yellow` status on any network/auth error.

*Promotion-measure:* once an adopter A/B confirms the round-trip is cheap and
stable, the flag can flip default-ON; publish p50/p95 latency from
`--json` `live_probe.detail.latency_ms` before any flip.

## Path / settings resolution order

- **audit-log** — `$CEO_AUDIT_LOG_PATH` → `$CEO_AUDIT_LOG_DIR/audit-log.jsonl`
  → `$CLAUDE_PROJECT_DIR`-derived slug → legacy
  `~/.claude/projects/ceo-orchestration/audit-log.jsonl`.
- **memory dir** — `$CEO_MEMORY_DIR` → `$CLAUDE_PROJECT_DIR`-derived
  `…/<slug>/memory`.
- **plans dir** — always repo-relative `.claude/plans/` (never adopter-home).
- **settings** — `.claude/settings.json` then `.claude/settings.local.json`
  (last valid file wins as the effective override).

## Fail-open

Every probe degrades to a descriptive status instead of raising. The only
non-zero exits are: `1` (a required path is RED **under `--check`**) and `2`
(a usage / internal error). A plain `/ceo-info` with no `--check` is purely
advisory and always exits 0.
