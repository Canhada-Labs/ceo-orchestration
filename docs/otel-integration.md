# OpenTelemetry integration guide

> **Status:** ADVISORY (Sprint 11, ADR-035 State 0). The exporter is
> Owner-invoked; the framework does NOT auto-export on its own. Sprint
> 12 may wire auto-export from `audit_log.py`, gated on stable drop
> rates.

This guide shows how to point the `ceo-orchestration` audit log at an
OpenTelemetry backend. Every recipe starts by setting
`CEO_OTEL_ALLOWED_HOSTS` — the empty default rejects every endpoint
(fail-closed per ADR-035 §CR3).

## Security model (TL;DR)

The exporter enforces six mitigations at the only code path
(`.claude/hooks/_lib/otel_emit.py`):

1. **HTTPS only.** `http://`, `file://`, `gopher://`, `ws://` are
   rejected with exit code 2.
2. **Host allowlist.** `CEO_OTEL_ALLOWED_HOSTS` must list the
   destination host explicitly. Empty ⇒ reject all.
3. **Double redaction.** Every span attribute value passes through
   `redact_secrets` twice. Your API keys, Bearer tokens, and
   `sk-...` values are stripped *before* the POST.
4. **`description_hash` dropped.** SHA-256 of plaintext is
   externally correlatable; never exported.
5. **`otel_export_dropped` audit events.** Every drop (redaction OR
   rejection) is logged to `audit-log.jsonl` with host-only
   metadata (no URL path, no query).
6. **Stdlib-only transport.** `urllib.request` for the POST; no
   `requests` / `httpx` / `opentelemetry-sdk`.

**You cannot override these at runtime.** The only disable is
`CEO_SOTA_DISABLE=1`, which short-circuits the exporter to a no-op
(matches the other Sprint 11 surfaces).

## Prerequisites

- `ceo-orchestration` installed (framework or via `install.sh`).
- Python 3.9+ already on your path.
- `audit-log.jsonl` present at
  `~/.claude/projects/<project>/audit-log.jsonl`.

## Quick start

```bash
# 1. Declare which host(s) you trust as OTEL destinations.
export CEO_OTEL_ALLOWED_HOSTS="tempo.example.com"

# 2. Dry-run first — see the payload, no network.
python3 .claude/scripts/otel-export.py \
  --endpoint https://tempo.example.com/v1/traces \
  --dry-run \
  --since 24h

# 3. Once the payload looks right, remove --dry-run.
python3 .claude/scripts/otel-export.py \
  --endpoint https://tempo.example.com/v1/traces \
  --since 24h \
  --headers "Authorization: Bearer $YOUR_TOKEN"
```

If step 2 shows fields you did NOT expect to export, file an issue
*before* you run step 3. The redaction pipeline is aggressive but
adversarial examples help us catch gaps.

## Recipe 1 — Grafana Tempo (self-hosted)

Tempo ships an OTLP/HTTP receiver on `/v1/traces`. With a default
deployment:

```bash
export CEO_OTEL_ALLOWED_HOSTS="tempo.example.com"

python3 .claude/scripts/otel-export.py \
  --endpoint https://tempo.example.com/v1/traces \
  --since 7d \
  --service-name ceo-orchestration
```

**Tempo auth via basic-auth proxy:** add `--headers` with the
bearer your reverse proxy issues. Values are double-redacted before
the POST logs the request locally.

```bash
python3 .claude/scripts/otel-export.py \
  --endpoint https://tempo.example.com/v1/traces \
  --since 7d \
  --headers "Authorization: Bearer $TEMPO_TOKEN"
```

**Warning:** never commit the endpoint URL — it's a pin for where
your traces live. Keep it in your shell's secret store or a CI
secret.

## Recipe 2 — Datadog APM

Datadog exposes OTLP/HTTP on intake hosts per region. For the US
region:

```bash
export CEO_OTEL_ALLOWED_HOSTS="trace-intake.datadoghq.com"

python3 .claude/scripts/otel-export.py \
  --endpoint https://trace-intake.datadoghq.com/api/v0.2/traces \
  --headers "DD-API-KEY: $DATADOG_API_KEY" \
  --since 24h
```

For EU: replace `.datadoghq.com` with `.datadoghq.eu` on BOTH the
endpoint and the allowlist entry. The host check is exact-match; a
wrong region host is rejected.

**Warning:** the `DD-API-KEY` header value is double-redacted by
the CLI before anything is logged. But Datadog's receiver requires
the plaintext key — ensure `$DATADOG_API_KEY` is set only in the
shell running the exporter, not checked into any file.

## Recipe 3 — Honeycomb

Honeycomb's OTLP endpoint is `api.honeycomb.io`. You use the
`x-honeycomb-team` header for auth:

```bash
export CEO_OTEL_ALLOWED_HOSTS="api.honeycomb.io"

python3 .claude/scripts/otel-export.py \
  --endpoint https://api.honeycomb.io/v1/traces \
  --headers "x-honeycomb-team: $HONEYCOMB_API_KEY" \
  --headers "x-honeycomb-dataset: ceo-orchestration" \
  --since 24h
```

Honeycomb recommends a dataset header; `--headers` is repeatable.

## Recipe 4 — Local Jaeger all-in-one (development)

Jaeger's `all-in-one` image exposes OTLP/HTTP on
`:4318/v1/traces`. For local development *on your workstation*
(not CI):

```bash
# Start Jaeger (once):
docker run -d --name jaeger -p 16686:16686 -p 4318:4318 \
  jaegertracing/all-in-one:latest

# Export (note the CEO_OTEL_SMOKE + --no-tls-verify combo;
# required because Jaeger all-in-one serves plaintext HTTP on
# 4318, and the scheme allowlist only accepts https).
#
# RECOMMENDED: put Jaeger behind an HTTPS reverse proxy (nginx,
# Caddy) for any use beyond a single-dev-laptop sanity check.
# The below is a workstation-only shortcut.

export CEO_OTEL_ALLOWED_HOSTS="jaeger.local"
export CEO_OTEL_SMOKE="1"

# Add `jaeger.local 127.0.0.1` to /etc/hosts so the allowlist
# matches AND HTTPS resolution stays on loopback.
python3 .claude/scripts/otel-export.py \
  --endpoint https://jaeger.local:4318/v1/traces \
  --no-tls-verify \
  --since 24h
```

**Warning:** `CEO_OTEL_SMOKE=1` disables TLS verification. Use it
**only** for loopback or CI-private destinations. Never on a
production endpoint. The CLI refuses `--no-tls-verify` unless
`CEO_OTEL_SMOKE=1` is set — this is intentional friction.

## Flags reference

| Flag | Purpose | Notes |
|---|---|---|
| `--endpoint URL` | Required. HTTPS URL of the OTLP receiver. | Scheme and host are validated before DNS. |
| `--dry-run` | Print payload to stdout; no POST. | Use this first for every new endpoint. |
| `--since DUR` | Filter events by `ts` (e.g. `24h`, `7d`, `2w`). | Units: `s m h d w`. |
| `--headers "K: V"` | Repeatable. Forwarded to POST; values are double-redacted in logs. | |
| `--audit-log PATH` | Override the default audit-log location. | Useful for tests / offline replays. |
| `--service-name NAME` | OTEL `service.name` resource attribute. | Default: `ceo-orchestration`. |
| `--timeout SEC` | POST timeout in seconds. | Default: 10. |
| `--no-tls-verify` | Only under `CEO_OTEL_SMOKE=1`. | Refused otherwise. |

## Environment variables

| Var | Effect |
|---|---|
| `CEO_OTEL_ALLOWED_HOSTS` | Comma-separated hostnames allowed as export targets. Empty ⇒ reject all. |
| `CEO_OTEL_SMOKE` | When `1`, `--no-tls-verify` is honored. CI-smoke only. |
| `CEO_SOTA_DISABLE` | When `1`, every Sprint-11 surface short-circuits, including the exporter. |

## Exit codes

| Code | Meaning |
|---|---|
| 0 | Success (or dry-run, or disabled) |
| 2 | Validation error (scheme, host, bad `--since`, missing `--endpoint`) |
| 3 | Transport error (POST failure, timeout) |

## Troubleshooting

**"scheme http not allowed (HTTPS only)"**
Your URL starts with `http://`. The exporter only accepts HTTPS.
If you need a loopback plaintext receiver for dev, see Recipe 4.

**"host X not in allowlist"**
Set `CEO_OTEL_ALLOWED_HOSTS` to include `X` exactly. Matching is
case-insensitive but does NOT support wildcards.

**"bad duration '...'"**
`--since` requires `<int><s|m|h|d|w>`. `24h`, `7d`, `2w` — not
`24hours` or `7 days`.

**No spans exported, no error**
Check `--since`: if the window is shorter than your oldest event,
nothing matches. Also check `audit-log.jsonl` exists and is
non-empty.

**Redaction dropped too much**
If you see `dropped_fields=N` where N is suspiciously large, your
events contain secret-shaped values in fields you didn't expect. Run
`--dry-run` and inspect the payload; adjust your hook emitters to
avoid putting secrets in attribute *values* in the first place.

**Audit events of action `otel_export_dropped`**
These are intentional — they prove the defense fired. Query them
via `audit-query.py metrics` (Sprint 12 may add a dedicated
sub-command).

## Security warnings

1. **The allowlist is the first and last line.** An empty
   `CEO_OTEL_ALLOWED_HOSTS` means nothing exports. Do not set it
   globally in your shell profile — export only in the scope that
   actually runs the CLI.
2. **Credentials go in `--headers` only.** Never embed tokens in
   the endpoint URL (`https://user:pass@host/...`). The redactor
   catches embedded credentials, but the URL itself is recorded
   host-only in audit — so credentials *would* pass through the
   network even if audit is clean. Use `--headers`.
3. **Never commit the endpoint URL.** It pins the location of your
   trace store. Keep it in a secrets manager or CI secret.
4. **Do not run `--no-tls-verify` against the public internet.**
   The `CEO_OTEL_SMOKE=1` gate makes this hard to do by accident;
   don't engineer around it.

## Further reading

- ADR-035 — normative decision record.
- `SPEC/v1/audit-log.schema.md` §`otel_export_dropped`.
- `.github/workflows/otel-smoke.yml` — working example end-to-end.
- `.claude/hooks/_lib/otel_emit.py` — library source.
