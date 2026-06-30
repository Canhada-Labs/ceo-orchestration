# OTLP Dashboard Samples — `ceo-cost.py --stream`

> **PLAN-040 Wave C companion doc.** The streaming mode of `ceo-cost.py`
> emits one OTLP metric per spawn cost event. This document shows how
> adopters can pipe those metrics into three common observability
> stacks. All examples assume the adopter owns the target stack — the
> `ceo-orchestration` framework ships no dashboards of its own.

---

## 1. What ceo-cost.py emits

When you run:

```bash
python3 .claude/scripts/ceo-cost.py \
  --stream \
  --otlp-endpoint https://your-collector.example.com:4318/v1/metrics
```

…with `CEO_COST_OTLP_BEARER=<token>` set (optional), each cost-bearing
audit-log entry produces:

1. **stdout event** (JSON line): `spawn.cost` with full local context
   — tokens_in/out, model, session_id, plan_id, skill, running
   session + day totals.
2. **OTLP POST** (if endpoint configured): a minimal-shape OTLP/HTTP
   metric payload with the metric `ceo.cost.usd` (unit `USD`, gauge
   data point), labeled by model / session / plan / skill.

Kill-switch: `CEO_COST_STREAMING=0` disables the streaming path
entirely (batch mode unchanged).

Fallback on endpoint failure: events spill to
`cost-stream-fallback.jsonl` next to the audit log (or to
`--fallback-log <path>` if you override it). The spill happens on
non-2xx responses, network / DNS / TLS failures, and queue overflow.
A `cost.stream.post_failure` breadcrumb lands on stdout each failure
(endpoint + bearer token redacted).

---

## 2. Grafana (Prometheus-backed, via OTLP collector)

Adopters with an existing Grafana + Prometheus stack typically run an
OTLP collector in between. Collector config (minimal):

```yaml
# otelcol-config.yaml
receivers:
  otlp:
    protocols:
      http:
        endpoint: 0.0.0.0:4318

exporters:
  prometheus:
    endpoint: "0.0.0.0:9464"

service:
  pipelines:
    metrics:
      receivers: [otlp]
      exporters: [prometheus]
```

Point `ceo-cost.py --stream` at the collector:

```bash
python3 .claude/scripts/ceo-cost.py --stream \
  --otlp-endpoint http://otelcol.example.com:4318/v1/metrics
```

Grafana query (PromQL) for per-session running cost:

```promql
sum by (session_id) (ceo_cost_usd)
```

Per-day running cost:

```promql
sum by (exported_instance) (
  rate(ceo_cost_usd[24h])
) * 86400
```

Sample panel: **Cost by model, last 1h** (stacked area):

```promql
sum by (model) (rate(ceo_cost_usd_total[5m]))
```

> Note: Prometheus remaps the metric name from `ceo.cost.usd` →
> `ceo_cost_usd` (dots → underscores). Plan your dashboard queries
> accordingly.

---

## 3. Datadog (via OTLP HTTP endpoint)

Datadog accepts OTLP/HTTP at `https://otlp.datadoghq.com/v1/metrics` (or
the regional endpoint; check your Datadog site). Auth via API key
header.

```bash
CEO_COST_OTLP_BEARER="$DD_API_KEY" \
python3 .claude/scripts/ceo-cost.py --stream \
  --otlp-endpoint https://otlp.datadoghq.com/v1/metrics
```

Datadog metric-explorer query:

```
avg:ceo.cost.usd{*} by {model}
```

Alert monitor: **Daily cost spike**:

```
sum(last_1d):sum:ceo.cost.usd{*} by {session_id} > 50
```

(Adjust `50` to your `--alert-daily-usd` budget.)

---

## 4. Prometheus scrape (bypass collector)

If you prefer to avoid running a collector, you can scrape the OTLP
receiver directly via an OpenTelemetry SDK's Prometheus exporter.
Alternatively, run `ceo-cost.py` in `--stream` mode without
`--otlp-endpoint` and post-process the JSONL output with your own
scraper:

```bash
# Terminal 1: stream cost events to a rolling log
python3 .claude/scripts/ceo-cost.py --stream > /var/log/ceo-cost.jsonl

# Terminal 2: tail + reshape into Prometheus textfile format
tail -F /var/log/ceo-cost.jsonl | python3 -c '
import json, sys
for line in sys.stdin:
    e = json.loads(line)
    if e.get("event") == "spawn.cost":
        print(
            f"ceo_cost_usd{{model=\"{e[\"model\"]}\","
            f"session_id=\"{e[\"session_id\"]}\"}} {e[\"cost_usd\"]}"
        )
' >> /var/lib/node_exporter/textfile/ceo-cost.prom
```

Then let `node_exporter --collector.textfile.directory=/var/lib/node_exporter/textfile`
expose it.

---

## 5. Local-only dashboards (no external stack)

For a laptop-only or air-gapped environment:

```bash
# Stream to stdout + tee to JSONL; use jq + any lightweight viewer.
python3 .claude/scripts/ceo-cost.py --stream | tee ~/cost-live.jsonl

# In another terminal:
tail -f ~/cost-live.jsonl \
  | jq -r 'select(.event == "spawn.cost") | [.ts_iso, .model, .cost_usd, .running_session_usd] | @tsv'
```

For a minimal live TUI:

```bash
watch -n 2 'python3 .claude/scripts/ceo-cost.py --since 1h --by-session'
```

---

## 6. Operational notes

- **Heartbeat events** (`cost.stream.heartbeat`) fire every
  `--heartbeat-secs` (default 60s). External monitors can alert on
  "no heartbeat for 5 min" — zombie-process detection (DevOps P0-3
  closure from PLAN-040 Round-1 debate).
- **Alert events** (`cost.alert.session_threshold`,
  `cost.alert.daily_threshold`) fire once per boundary crossing. The
  state is in-process; restarts lose the "already alerted" flag and
  will re-fire once the running total is re-built.
- **Log rotation** is handled by inode tracking (DevOps P0-1 closure):
  when `audit-log.jsonl` is rotated (inode changes), the streamer
  closes the old file descriptor and re-opens at offset 0 of the new
  file.
- **Auth-token redaction:** the `cost.stream.post_failure`
  breadcrumb emits only `scheme://host[:port]`; the URL path, query
  string, and `Authorization` header never appear in stdout or the
  fallback JSONL.
- **Fallback JSONL** is append-only; rotate it with logrotate /
  external tooling if long-running streams produce too much content.

---

## 7. Cross-references

- `.claude/adr/ADR-061-runtime-cost-streaming.md` — threat model +
  decision rationale.
- `.claude/plans/PLAN-040-runtime-cost-streaming.md` — plan + debate
  Round-1 findings.
- `.claude/scripts/ceo-cost.py` — the streaming implementation.
- `.claude/scripts/tests/test_ceo_cost_stream.py` — 56+ tests
  covering the debate-convergent closures.
- `docs/MECHANISM-SELECTION.md` — why this is a script + optional
  MCP sidecar, not a hook (the observability workload is adopter-
  owned + runs on the operator's workstation, not at every tool call).

---

*Last updated: 2026-04-19. Closes PLAN-040 Phase 3. Maintainer: CEO
(Claude). Adopter dashboards are adopter-owned; this doc is a
starting-point map, not a turnkey deployment.*
