# Audit Dashboard

Local, read-only, stdlib-only dashboard for the `audit-log.jsonl` event
stream v2. Serves a live SSE tail plus four aggregation panels.

Shipped by PLAN-004 Phase 5 (SSE base) and extended by PLAN-010 Phase 4
(tokens / reflexion / pruning / architect-outcomes panels).

## Running the dashboard

```bash
python3 .claude/scripts/audit-dashboard.py
# → prints a URL like http://127.0.0.1:54321/?t=<token>
# → open in a browser; the overview tails events live
```

Options:

| Flag | Default | Meaning |
|---|---|---|
| `--port N` | 0 (random) | TCP port to bind |
| `--bind ADDR` | 127.0.0.1 | Must be loopback (127.0.0.1, ::1, or localhost) |
| `--tail N` | 500 | Events replayed on SSE connect |
| `--max-connections N` | 4 | Concurrent SSE streams allowed |
| `--token-file PATH` | — | Write token to file (mode 0600) instead of stdout |

Ctrl-C stops the server. Each restart rotates the token.

## Auth flow

Every request must carry `?t=<token>`. The token is a 32-char
`secrets.token_urlsafe` string printed to stdout on startup (or written
to `--token-file` if specified). Missing or wrong token → **HTTP 401**.

Token comparison uses `secrets.compare_digest` (constant time). Loopback
binding is enforced (`--bind 0.0.0.0` is rejected at startup). No TLS —
the dashboard is localhost-only by design.

## Panels

The overview page (`/`) includes a nav bar linking to four aggregation
panels. Each panel reads the JSONL once per request, renders static HTML,
and returns (no long-lived connection).

### `/panel/tokens` — token usage

Aggregates token consumption from `agent_spawn` events per archetype per
day. Supports both shapes:

- PLAN-006 flat: `tokens_in` + `tokens_out` at the event root
- Adapter shape: `usage.total_tokens`

Shows per-archetype totals and an archetype × day breakdown. Records
missing both shapes are counted under "records without tokens" so
adapter coverage gaps are visible.

_Placeholder: `docs/img/panel-tokens.png`_

### `/panel/reflexion` — lesson hit/miss/ratio

Aggregates `lesson_outcome` events (excluding `inference_mode =
window-only` by default, same gate as
`audit-query lessons-effectiveness`). Shows global hit/miss totals, the
aggregate hit-ratio, and a top-10 ranking by effectiveness
(hit / (hit + miss)).

Injection counts come from `lesson_read.lesson_ids`. Treat as
informational only — per PLAN-009 Phase 5, ranking by injection count
is a gameable axis.

_Placeholder: `docs/img/panel-reflexion.png`_

### `/panel/pruning` — restore ratio

Computes restore ratio (unique lessons restored / total archived) across
three rolling windows: 24h, 7d, 30d. Counts safety-guard triggers
(events where `force_dangerous_threshold: true` or `safety_guard_triggered:
true`), which correspond to ADR-020 `--force-dangerous-threshold`
invocations in `prune-lessons.py`.

Ratio color-coding: `>10%` red, `>5%` amber, otherwise default.

_Placeholder: `docs/img/panel-pruning.png`_

### `/panel/architect-outcomes` — session vs window inference

Breaks down `lesson_outcome` events by:

- **inference_mode** — session-correlated (trusted) vs window-only
  (attribution-only heuristic from PLAN-009 ADR-015 amendment)
- **consumer** — `architect`, `benchmark`, or any other value seen

Per-consumer rows include hits, misses, and effectiveness.

_Placeholder: `docs/img/panel-architect-outcomes.png`_

## Limits and safety

- **Concurrent clients:** max 5 panel requests in-flight at once (6th
  gets HTTP 503). SSE uses its own cap (`--max-connections`, default 4).
- **Per-connection timeout:** server-side socket timeout of 30 seconds
  via `BaseHTTPRequestHandler.setup()`. SSE heartbeats every 15s keep
  connections alive; any stall longer than 30s drops the socket.
- **Fail-open:** malformed JSONL lines are skipped with a stderr
  breadcrumb (never abort the read). Panel aggregation errors render
  an empty-state card rather than returning HTTP 500.
- **Concurrent reader safety:** panels open+read+close the log in one
  call. Writers hold `fcntl.flock` via `_lib/filelock.py` when
  appending; readers are never locked. A rotation (file truncated +
  rewritten) mid-read yields either the pre- or post-rotation bytes —
  both are valid snapshots. Tested under `test_concurrent_reader_during_rotation`.
- **Read-only:** POST / PUT / DELETE return HTTP 405. The dashboard
  never gates hook/plan/spawn behavior.

## Environment

| Variable | Purpose |
|---|---|
| `CEO_AUDIT_LOG_PATH` | Override default log path. Used by tests. |
| `HOME` | Falls back to `Path.home()` if unset. |

Default log path: `~/.claude/projects/ceo-orchestration/audit-log.jsonl`.

## Troubleshooting

- **401 on every request.** The URL token changed on server restart —
  copy the new one from the launch terminal.
- **503 on panels.** More than 5 concurrent panel requests. Usually a
  script hitting the dashboard in a loop; add a delay.
- **Empty-state everywhere.** No events in the log yet. Spawn an agent
  (`/spawn "Name" task`) or run a benchmark to seed data.
- **Browser hangs on SSE.** Some proxies buffer SSE. Always open via
  `127.0.0.1:<port>` directly — no proxy in front of localhost.

## Tests

```bash
python3 -m pytest .claude/scripts/tests/test_audit_dashboard.py -v
```

30 tests cover: auth (8), HTTP methods (3), SSE (3), panel happy path
(4), panel auth fail (4), edge cases (5 — empty log, malformed JSONL,
concurrent rotation, 503 cap, timeout constant), state (2), aggregation
units (4), loopback enforcement (1).
