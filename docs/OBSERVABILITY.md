# Observability — audit-log JSONL is canonical

> **PLAN-056 Phase 6 / ADR-087 deliverable.** Documents the framework's
> observability surface. No OpenTelemetry SDK; no vendor coupling.
> Audit-log JSONL + 3 stdlib CLI tools cover every observability use
> case ceo-orchestration ships for.

## TL;DR

| You want to know | Tool | Example |
|---|---|---|
| What's the framework doing right now? | `ceo-diagnose` | `python3 .claude/scripts/ceo-diagnose.py` |
| What ran in the last 24h? | `audit-query.py` | `python3 .claude/scripts/audit-query.py recent --limit 100` |
| Per-archetype dispatch counts + p95 latency? | `audit-telemetry.py` | `python3 .claude/scripts/audit-telemetry.py --window 7d` |
| Was the audit log tampered with? | `audit-verify-chain.py` | `python3 .claude/scripts/audit-verify-chain.py` |
| Governance health (errors / warnings)? | `validate-governance.sh` | `bash .claude/scripts/validate-governance.sh` |

## Why audit-log JSONL, not OpenTelemetry

Per ADR-087, the framework refuses to add OTel-native span emit. The
reason is a deliberate architectural choice:

1. **Audit-log is governance-load-bearing.** HMAC chain (ADR-055)
   provides tamper detection. Canonical-edit sentinels reference it.
   OTel does not have an equivalent governance contract.
2. **JSONL is universal.** Any observability backend (Jaeger, Datadog,
   Honeycomb, Phoenix, Tempo) ingests JSONL via tail-and-parse.
   No vendor coupling at our boundary.
3. **No new dependency surface.** OTel SDK adds dependency burden;
   stdlib OTLP-protocol implementation adds maintenance burden.
4. **Adopter teams already tool around JSONL.** `grep`, `jq`, `awk`
   are universal. OTel-native tooling requires more setup.

If your team runs Jaeger/Datadog/Honeycomb/Phoenix/etc, see
§"Bridging audit-log → OTel collector" below.

## The 4-tool observability stack

### 1. `ceo-diagnose` — single-glance health check

```bash
python3 .claude/scripts/ceo-diagnose.py            # human text
python3 .claude/scripts/ceo-diagnose.py --json     # machine output
python3 .claude/scripts/ceo-diagnose.py --quick    # skip pytest probe
```

Probes:
- **Open plans** — count of plans not in `done`
- **Governance** — `validate-governance.sh` exit + warnings
- **Audit log** — freshness + last-24h event count
- **Dispatch modes** — per-archetype mitigation breakdown
- **ADR-082** — current status (PROPOSED / ACCEPTED)
- **Install mode** — vibecoder vs cto (when ADR-086 lands)
- **Hook tests** — pytest pass/fail count

Exit code: `0` green / `1` yellow / `2` red.

### 2. `audit-telemetry.py` — aggregate analytics

```bash
python3 .claude/scripts/audit-telemetry.py                       # 24h default
python3 .claude/scripts/audit-telemetry.py --window 7d
python3 .claude/scripts/audit-telemetry.py --archetype qa-architect
python3 .claude/scripts/audit-telemetry.py --json
```

Reports:
- Total events + spawns + fabrication-rate within window
- Per-archetype dispatch counts + mode breakdown (mitigated / native / unknown)
- p50 / p95 latency per archetype (when `hook_duration_ms` field present)

Window grammar: `30m`, `24h`, `7d`, `90d` etc.

### 3. `audit-query.py` — flexible event grep

```bash
python3 .claude/scripts/audit-query.py recent --limit 50         # last N events
python3 .claude/scripts/audit-query.py grep --action agent_spawn # filter by action
python3 .claude/scripts/audit-query.py grep --since-hours 24
python3 .claude/scripts/audit-query.py count --action veto_triggered
```

9 sub-commands; see `--help` for full list.

### 4. `audit-verify-chain.py` — HMAC tamper check

```bash
python3 .claude/scripts/audit-verify-chain.py
```

Exit codes:
- `0` chain valid
- `1` forgery detected (HMAC mismatch)
- `2` reorder detected
- `3` interior deletion detected
- `4` transition violation (hmac-bearing → hmac-less = tamper)

Run before any forensic claim. ADR-055 §Threat Model documents
what this defends + what it does NOT defend.

## Schema reference

`SPEC/v1/audit-log.schema.md` is the authoritative event schema.
Each action declared in `_KNOWN_ACTIONS` (`.claude/hooks/_lib/audit_emit.py`)
has a corresponding row in the SPEC file with field-level contracts.

Key fields on every event:
- `action`: enum from `_KNOWN_ACTIONS` (33+ actions registered)
- `ts`: ISO-8601 UTC timestamp
- `event_schema`: `v2` (or absence = v1)
- `tokens_in / tokens_out / tokens_total`: nullable cost fields
- `hmac / hmac_error`: HMAC chain (ADR-055)
- `session_id / project`: provenance

## Integrating with external systems

### Bridging audit-log → OTel collector (no native; tail+parse pattern)

```bash
tail -F ~/.claude/projects/$(slugify $PWD)/audit-log.jsonl \
  | jq -c 'select(.action == "agent_spawn") | {
      "timestamp": .ts,
      "trace_id": .session_id,
      "operation": .action,
      "archetype": .archetype,
      "duration_ms": .hook_duration_ms
    }' \
  | curl -X POST -H 'Content-Type: application/json' \
         -d @- https://your-otel-collector/v1/traces
```

(Adapt the JSON transformation to your OTel collector's expected
schema. The framework does NOT include this script — it's a recipe
for adopter teams.)

### Splunk / ELK / Loki

JSONL ingests natively. Point your forwarder at the audit-log file:

```bash
# Filebeat example (Loki via Promtail equivalent)
filebeat.inputs:
  - type: log
    paths:
      - ~/.claude/projects/*/audit-log.jsonl
    json.keys_under_root: true
```

### Datadog Logs (free-tier)

```bash
DD_API_KEY=xxx datadog-agent \
  -c "logs:enabled = true" \
  -c "logs.path = ~/.claude/projects/*/audit-log.jsonl" \
  -c "logs.service = ceo-orchestration"
```

### Custom dashboards

`audit-telemetry.py --json` emits a stable v1 schema. Pipe to any
plotting tool:

```bash
while true; do
  python3 .claude/scripts/audit-telemetry.py --window 1h --json \
    | jq '.totals' >> /tmp/ceo-metrics.jsonl
  sleep 60
done
```

## Anti-patterns

### ❌ Don't treat audit-log as primary alerting

Audit-log is post-hoc forensic. Real-time alerting belongs in your
external SIEM/observability tool ingesting the JSONL.

### ❌ Don't grep audit-log for SECRETS

The audit-log emits redacted previews via `_lib/redact.redact_secrets`
(ADR-036). If you need to inspect the full plaintext of a tool input/
output, that's a hook responsibility (and probably wrong — see
ADR-077 + ADR-082 redaction discipline).

### ❌ Don't manually edit audit-log.jsonl

It's append-only with HMAC chain. Manual edit = `audit-verify-chain.py`
exit 1. Use `audit-rotate.py` if file grows too large (rotation resets
chain at genesis).

## When this doc fails you

If your observability use case isn't covered:

1. Check if `audit-query.py --help` has a sub-command for it.
2. Check if the event you need is in `_KNOWN_ACTIONS`. If not, the
   relevant hook isn't emitting it (file a finding).
3. If the gap is structural (i.e. JSONL doesn't capture what you
   need), reopen ADR-087 with the new evidence.

## References

- ADR-087 — OpenTelemetry emit REFUSED (this doc's parent)
- ADR-085 — Framework landscape Claude-only thesis
- ADR-055 — Audit-log HMAC chain
- ADR-077 — WebFetch injection (redaction precedent)
- ADR-036 — Output safety redaction
- `SPEC/v1/audit-log.schema.md` — authoritative schema
- `STATE-RECOVERY.md` — sister doc on audit-log as recovery surface
