---
name: devops-ci-cd
description: CI/CD pipeline design, Docker optimization, PaaS deployment, health
  check engineering, rollback strategies, monitoring infrastructure, and secret
  management for backend services. Use when working on GitHub Actions
  workflows, Dockerfile changes, deploy configuration, health check endpoints,
  deploy scripts, Prometheus/Grafana setup, alerting rules, zero-downtime deploys,
  or any infrastructure/operations task. Also use when the user mentions "deploy",
  "CI", "pipeline", "Docker", "health check", "rollback", "monitoring",
  "Prometheus", "Grafana", or "secrets".
owner: DevOps Lead
# --- smart-loading fields (PLAN-083 Wave 0a sub-agent 0.7a) ---
domain: core
priority: 4
risk_class: medium
stack: [github-actions]
context_budget_tokens: 900
inactive_but_retained: false
repo_profile_binding:
  frontend: {active: true, priority: 5}
  engine: {active: true, priority: 3}
  fintech: {active: true, priority: 4}
  trading-readonly: {active: true, priority: 6}
  generic: {active: true, priority: 4}
activation_triggers:
  - {event: file-edit, glob: ".github/workflows/**"}
  - {event: file-edit, glob: "**/Dockerfile"}
---

# DevOps & CI/CD

> This skill assumes a Node.js backend. For Python/Go/Rust, adapt the specifics
> but the patterns transfer (test-before-deploy, multi-stage Docker, liveness
> vs readiness, automated rollback, secrets hygiene). Example commands use
> Fly.io as one concrete PaaS, but the same workflow applies to Railway,
> Render, Heroku, AWS, GCP, or any container platform.

## Fail-Fast Rule

If any CI step fails, **stop the pipeline and do not deploy**. Never deploy
untested code. Never skip health check validation. Never push secrets to git.
A broken deploy to production with live traffic and stateful connections is
catastrophic.

## Cardinal Rule

**Every push to `main` must pass tests and type-checking before reaching
production.** A deploy workflow that runs `{{DEPLOY_COMMAND}}` with zero
validation is the single highest-risk gap in any infrastructure.

## Audit Baseline: Current State

### deploy.yml (minimal, no tests)

```yaml
# ANTI-PATTERN -- {{PROJECT_PATH}}/.github/workflows/deploy.yml
name: Deploy
on:
  push:
    branches: [main]
jobs:
  deploy:
    runs-on: ubuntu-latest
    steps:
      - uses: actions/checkout@v4
      - uses: superfly/flyctl-actions/setup-flyctl@master
      - run: flyctl deploy --remote-only
        env:
          FLY_API_TOKEN: ${{ secrets.FLY_API_TOKEN }}
```

**Problems:**
1. No `npm ci` -- dependencies not installed
2. No test run -- test suite never executes
3. No `npx tsc --noEmit` -- TypeScript errors not caught
4. No build validation before deploy
5. No rollback on failed health check
6. No deployment notification
7. Single step -- any failure is opaque

### Dockerfile (single-stage, no cache optimization)

```
FROM node:20-slim
RUN apt-get update && apt-get install -y libjemalloc2
COPY package.json package-lock.json* ./
RUN npm install --omit=dev
COPY src ./src
COPY tsconfig.json ./
RUN npx esbuild "$ENTRY_POINT" --bundle --outdir=dist  # e.g. main.ts, app.ts
CMD ["node", "--enable-source-maps", "dist/index.js"]
```

### Deploy config (basic, single health check)

- App: `{{APP_NAME}}`, region: primary
- VM: sized for workload
- Health check: `GET /healthz` every 15s, timeout 10s, grace 60s
- No readiness check, no liveness distinction

## Target CI/CD Pipeline

### GitHub Actions: Complete Pipeline

```yaml
# .github/workflows/deploy.yml
name: Test & Deploy

on:
  push:
    branches: [main]
  pull_request:
    branches: [main]

concurrency:
  group: deploy-${{ github.ref }}
  cancel-in-progress: true

jobs:
  test:
    runs-on: ubuntu-latest
    timeout-minutes: 15
    steps:
      - uses: actions/checkout@v4

      - uses: actions/setup-node@v4
        with:
          node-version: '20'
          cache: 'npm'

      - name: Install dependencies
        run: npm ci

      - name: TypeScript type check
        run: npx tsc --noEmit

      - name: Run tests
        run: npm test
        env:
          NODE_OPTIONS: '--max-old-space-size=4096'

      - name: Build validation
        run: npm run build

  deploy:
    needs: test
    if: github.ref == 'refs/heads/main' && github.event_name == 'push'
    runs-on: ubuntu-latest
    timeout-minutes: 10
    environment: production
    steps:
      - uses: actions/checkout@v4

      # Example: Fly.io. Swap for Railway/Render/Heroku/AWS/GCP equivalents.
      - uses: superfly/flyctl-actions/setup-flyctl@master

      - name: Deploy
        run: ${{ env.DEPLOY_COMMAND }}   # e.g. flyctl deploy --remote-only
        env:
          FLY_API_TOKEN: ${{ secrets.FLY_API_TOKEN }}
          DEPLOY_COMMAND: flyctl deploy --remote-only

      - name: Wait for health check
        run: |
          echo "Waiting 60s for startup grace period..."
          sleep 60
          for i in $(seq 1 10); do
            STATUS=$(curl -sf {{PRODUCTION_URL}}/healthz | jq -r '.status' 2>/dev/null || echo "unreachable")
            echo "Health check attempt $i: $STATUS"
            if [ "$STATUS" = "ok" ] || [ "$STATUS" = "healthy" ]; then
              echo "Health check passed"
              exit 0
            fi
            sleep 10
          done
          echo "Health check failed after 10 attempts"
          exit 1

      - name: Rollback on failure
        if: failure()
        run: |
          echo "Deploy failed -- rolling back to previous release"
          # Example (Fly.io): re-deploy the previous release image
          flyctl releases --json | jq -r '.[1].id' | xargs -I {} flyctl deploy --image registry.fly.io/{{APP_NAME}}:{}
          # Other platforms: use their equivalent rollback command
          # (Railway: railway rollback, Render: dashboard or API, Heroku: heroku releases:rollback, AWS: blue/green swap)
        env:
          FLY_API_TOKEN: ${{ secrets.FLY_API_TOKEN }}
```

### Key Pipeline Principles

1. **Test job is blocking**: `deploy` has `needs: test`. No tests = no deploy.
2. **PR validation**: Runs tests on PRs without deploying (the `if` guard).
3. **Concurrency control**: Only one deploy at a time, newer cancels older.
4. **Health verification**: Post-deploy curl check with 10 retries.
5. **Automatic rollback**: If health check fails, revert to previous release.
6. **Timeouts**: 15 min for tests, 10 min for deploy.

## Docker Multi-Stage Build Optimization

### Current Problem

A naive Dockerfile installs ALL dependencies (`npm install --omit=dev`), copies
source, and builds in a single stage. This means:
- Every source change invalidates the npm cache layer
- Dev dependencies needed for the build are installed then unused
- Final image includes npm, source files, and build artifacts

### Optimized Multi-Stage Dockerfile

```dockerfile
# Stage 1: Dependencies (cached unless package-lock changes)
FROM node:20-slim AS deps
WORKDIR /app
COPY package.json package-lock.json* ./
RUN npm ci

# Stage 2: Build (cached unless src changes)
FROM deps AS build
COPY src ./src
COPY tsconfig.json ./
RUN npm run build

# Stage 3: Production (minimal image)
FROM node:20-slim AS production
RUN apt-get update \
  && apt-get install -y --no-install-recommends libjemalloc2 curl \
  && rm -rf /var/lib/apt/lists/*
ENV LD_PRELOAD=/usr/lib/x86_64-linux-gnu/libjemalloc.so.2
WORKDIR /app
COPY --from=deps /app/node_modules ./node_modules
COPY --from=build /app/dist ./dist
COPY package.json ./

ENV GIT_SHA=docker
ENV BUILD_TIME=unknown
EXPOSE 3000

HEALTHCHECK --interval=15s --timeout=10s --start-period=60s --retries=3 \
  CMD curl -f http://localhost:3000/healthz || exit 1

CMD ["node", "--enable-source-maps", "--max-old-space-size=8192", \
     "--max-semi-space-size=128", "dist/index.js"]
```

### Benefits

- **Layer caching**: `npm ci` only re-runs when `package-lock.json` changes
- **Smaller image**: Production stage has no source files, no build tools
- **Explicit healthcheck**: Docker-level health monitoring
- **curl included**: For health check verification

## Platform Configuration

### Example: fly.toml (one PaaS among many)

The patterns below apply to any PaaS — just translate to the equivalent
config format (Railway `railway.toml`, Render `render.yaml`, Heroku
`app.json`, AWS ECS task def, GCP Cloud Run service YAML, etc.).

```toml
app = '{{APP_NAME}}'
primary_region = 'gru'

[env]
  PORT = "3000"

[http_service]
  internal_port = 3000
  force_https = true
  auto_stop_machines = 'off'
  auto_start_machines = true
  min_machines_running = 1
  processes = ['app']

[[vm]]
  memory = '2gb'
  cpu_kind = 'shared'
  cpus = 2

# Liveness: is the process alive and responsive?
[checks.liveness]
  type = "http"
  port = 3000
  path = "/healthz"
  interval = "15s"
  timeout = "10s"
  grace_period = "120s"

# Readiness: is the system warmed up and serving accurate data?
[checks.readiness]
  type = "http"
  port = 3000
  path = "/readyz"
  interval = "30s"
  timeout = "10s"
  grace_period = "300s"
```

### Health Check Design

#### `/healthz` -- Liveness (should the process be restarted?)

Returns 200 if the Node.js process is alive and the event loop is responsive.
Returns 503 if the event loop is stalled or critical subsystems are down.

```typescript
// CORRECT: Checks real health
app.get('/healthz', (c) => {
  const elStall = getEventLoopStallMs();
  const memUsage = process.memoryUsage();
  const heapPct = memUsage.heapUsed / memUsage.heapTotal;

  if (elStall > 5000) {
    return c.json({
      status: 'unhealthy',
      reason: 'event_loop_stall',
      el_stall_ms: elStall,
    }, 503);
  }

  if (heapPct > 0.95) {
    return c.json({
      status: 'unhealthy',
      reason: 'heap_exhaustion',
      heap_pct: heapPct,
    }, 503);
  }

  return c.json({ status: 'ok', uptime: process.uptime() });
});

// WRONG: Always returns 200
app.get('/healthz', (c) => c.json({ status: 'ok' }));
```

#### `/readyz` -- Readiness (should traffic be routed here?)

Returns 200 only when the system is warmed up with sufficient data/state.
Returns 503 during the WARMING phase immediately after deploy.

```typescript
app.get('/readyz', (c) => {
  const warmState = engine.getWarmStateMetrics();
  const readyPct = warmState.loaded / warmState.expected;

  if (readyPct < 0.5) {
    return c.json({
      status: 'warming',
      ready_pct: readyPct,
      loaded: warmState.loaded,
      expected: warmState.expected,
    }, 503);
  }

  return c.json({
    status: 'ready',
    loaded: warmState.loaded,
  });
});
```

**Key distinction**: A degraded system (some upstream dependencies down) is LIVE
but should log warnings. A system that has not finished warming up is NOT READY
and should not serve traffic.

Project-specific status/metrics endpoints (beyond `/healthz` and `/readyz`)
can expose detailed internal state for operators, but keep them behind
admin auth.

## Rollback Strategies

### Strategy 1: Platform Release Rollback (Fastest)

```bash
# Example: Fly.io
fly releases -a {{APP_NAME}}
fly releases rollback -a {{APP_NAME}}
fly deploy --image registry.fly.io/{{APP_NAME}}:<sha>

# Other platforms:
# Railway: railway rollback
# Render:  use dashboard or API to redeploy previous image
# Heroku:  heroku releases:rollback v<N> -a {{APP_NAME}}
# AWS ECS: update service to previous task definition
# GCP Cloud Run: gcloud run services update-traffic --to-revisions=<prev>=100
```

**When to use**: Bad deploy, immediate rollback needed.
**Risk**: Low. Reverts to known-good image.

### Strategy 2: Canary Deploy (Safest for Risky Changes)

```bash
# Example on Fly.io (translate to your PaaS):
fly scale count 2 -a {{APP_NAME}}
fly deploy --strategy rolling -a {{APP_NAME}}

# Monitor health of new machine
fly status -a {{APP_NAME}}
curl {{PRODUCTION_URL}}/healthz

# If healthy: scale back down
# If unhealthy: rollback immediately
```

**When to use**: Architecture changes, IPC changes, worker thread changes.
**Risk**: Requires careful monitoring during rollout.

### Strategy 3: Manual Revert (Git-Based)

```bash
# Revert the problematic commit
cd {{PROJECT_PATH}}
git revert HEAD
git push origin main
# CI/CD pipeline redeploys automatically
```

**When to use**: Code bug identified, clean revert possible.
**Risk**: Revert may not be clean if commit has dependencies.

### Stateful-System Rollback Concerns

- **Stateful WebSocket / long-lived connections**: All client connections
  reconnect on deploy. A 5-10 minute warm-up can be normal depending on
  workload. Do not rollback just because state counters are at 0 immediately
  after deploy.
- **Worker threads / child processes**: All worker threads and child
  processes restart. Expect 30-60s to stabilize.
- **SharedArrayBuffer / in-memory caches**: Reset on restart. Consumers
  must handle stale/zero values during warm-up.
- **Grace period**: The PaaS `grace_period` value MUST be longer than the
  expected warm-up time for basic health, or the platform will kill the
  machine before it reports healthy.

## Secret Management

### Runtime Secrets (PaaS-managed)

```bash
# Example: Fly.io (translate to your PaaS — Railway variables,
# Render env groups, Heroku config vars, AWS Secrets Manager / SSM,
# GCP Secret Manager, etc.)
fly secrets set DB_PASSWORD=<value> -a {{APP_NAME}}
fly secrets set AUTH_SECRET=<value> -a {{APP_NAME}}
fly secrets set THIRD_PARTY_API_KEY=<value> -a {{APP_NAME}}
# ...

# List secrets (names only, never values)
fly secrets list -a {{APP_NAME}}
```

### GitHub Secrets (CI Pipeline)

| Secret | Purpose | Used In |
|--------|---------|---------|
| `FLY_API_TOKEN` (or equivalent) | Deploy authentication | deploy.yml |

**Rule**: ONLY the deploy-auth token should be in GitHub Secrets. All other
secrets live in the PaaS and are injected at runtime. Never duplicate
database credentials, third-party keys, or provider API keys in GitHub.

### Secrets Checklist

- [ ] No secrets in PaaS config (`fly.toml` `[env]`, `render.yaml` envVars,
      etc.) — only non-sensitive config belongs there
- [ ] No secrets in `.env` committed to git (`.gitignore` must include `.env*`)
- [ ] No secrets in Dockerfile `ENV` or `ARG`
- [ ] No secrets in GitHub Actions workflow files
- [ ] Third-party API keys stored encrypted at rest in your DB if user-scoped
- [ ] Key rotation procedure documented

## Monitoring Infrastructure

### Prometheus + Grafana

Expose metrics from the backend for scraping:

```typescript
// Expose /metrics endpoint for Prometheus
app.get('/metrics', adminAuthMiddleware, async (c) => {
  const metrics = collectMetrics(); // existing internal metrics
  return c.text(formatPrometheusExposition(metrics), 200, {
    'Content-Type': 'text/plain; version=0.0.4',
  });
});
```

### Example Key Metrics

| Metric | Type | Alert Threshold |
|--------|------|-----------------|
| `el_stall_p99_ms` | Gauge | > 500ms = WARN, > 2000ms = CRITICAL |
| `heap_used_bytes` | Gauge | > 80% of max = WARN |
| `rss_bytes` | Gauge | > 85% of VM memory = CRITICAL |
| `ipc_messages_per_sec` | Counter | backpressure risk threshold = WARN |
| `ws_connections_active` | Gauge | too low = CRITICAL (adapters down) |
| `worker_queue_depth` | Gauge | too high = WARN (processing lag) |
| `http_request_duration_ms` | Histogram | p99 > 1000ms = WARN |
| `upstream_reconnects` | Counter | > N/min per upstream = WARN |

### Alert Rules (PagerDuty/Slack)

```yaml
# Critical: Page immediately
- alert: CoreWorkloadZero
  expr: core_workload_counter == 0
  for: 5m
  annotations:
    summary: "Core workload counter at zero for 5 minutes"
    action: "Check worker/adapter processes, verify upstream connections"

- alert: EventLoopStall
  expr: el_stall_p99_ms > 2000
  for: 2m
  annotations:
    summary: "Event loop stalled >2s"
    action: "Check IPC message volume, heap usage, GC pauses"

- alert: HeapExhaustion
  expr: heap_used_bytes / heap_max_bytes > 0.95
  for: 1m
  annotations:
    summary: "Heap at 95%, OOM imminent"
    action: "Check for memory leaks, restart if necessary"

# Warning: Slack notification
- alert: UpstreamDisconnected
  expr: upstream_connected == 0
  for: 2m
  labels:
    severity: warning
  annotations:
    summary: "Upstream {{ $labels.upstream }} disconnected"
    action: "Check adapter logs, may self-recover via reconnect"

- alert: HighWorkerLag
  expr: worker_queue_depth > 500
  for: 5m
  labels:
    severity: warning
  annotations:
    summary: "Worker queue depth >500, processing lagging"
    action: "Check throughput thresholds, consider scaling workers"
```

## Deploy Checklist (Automated via CI)

Before every deploy, the pipeline must verify:

```
[ ] npm ci -- dependencies installed cleanly
[ ] npx tsc --noEmit -- zero TypeScript errors
[ ] npm test -- full test suite passes
[ ] Build step -- all entrypoints compile without errors
[ ] No secrets in committed files -- git-secrets scan
[ ] Health check responds 200 post-deploy
[ ] Readiness reports warm within expected window
```

### Manual Deploy Checklist

When deploying manually (bypassing CI):

```bash
cd {{PROJECT_PATH}}

# 1. Run tests locally
npm test

# 2. Type check
npx tsc --noEmit

# 3. Commit and push
git add <specific files>
git commit -m "<message>"
git push origin main

# 4. Deploy (example on Fly.io; use your platform's equivalent)
{{DEPLOY_COMMAND}}   # e.g. fly deploy

# 5. Verify (wait 60s for warm-up)
sleep 60
curl {{PRODUCTION_URL}}/healthz
curl {{PRODUCTION_URL}}/readyz

# 6. Check status/metrics endpoint (behind admin auth)
curl -H "Authorization: Bearer <token>" \
  {{PRODUCTION_URL}}/admin/runtime
```

## Zero-Downtime Deploy with WebSocket Connections

### Challenge

A backend that maintains long-lived connections (WebSockets, SSE, gRPC
streams) loses all of them on deploy unless handled carefully.

### Mitigation Strategy

1. **Rolling deploy**: With 2+ machines, the PaaS drains connections
   from the old machine before stopping it. Clients reconnect to new machine.
   (Fly.io: `--strategy rolling`. Kubernetes: rolling update strategy.
   AWS ECS: minimum healthy percent + maximum percent.)

2. **Client-side reconnect**: Frontend/client must implement automatic
   reconnect with exponential backoff.

3. **Grace period**: A sufficient `grace_period` (e.g. 120s) gives the
   old machine time to drain existing connections before being killed.

4. **SLO during deploy**: Accept a short window of degraded data
   (WARMING status) as normal. The `/readyz` endpoint correctly reports this.

5. **Upstream reconnection**: Adapter processes restart all upstream
   connections. Expected warm-up depends on upstream count and priority
   ordering.

### What NOT to Do

- Do not try to "hot swap" worker threads. Kill and restart is the correct
  approach for Node.js workers.
- Do not maintain two adapter processes simultaneously when upstream
  connections are unique per IP — two processes would cause conflicts.
- Do not rush the warm-up. Allow enough grace for the slowest upstream
  to come online before declaring the deploy bad.

## Anti-Patterns to Reject

| Anti-Pattern | Why It's Wrong | Correct Approach |
|---|---|---|
| Deploy without running tests | Broken code reaches production | `needs: test` in deploy job |
| `/healthz` always returns 200 | Hides real failures, PaaS cannot auto-restart | Return 503 when degraded |
| Secrets in PaaS config or git | Exposed in repo history forever | PaaS secrets + GitHub secrets only |
| Single-stage Dockerfile | Slow builds, large images, poor caching | Multi-stage: deps, build, production |
| No rollback plan | Stuck with broken deploy | Automated rollback on health check failure |
| Deploying from local machine | Bypasses all CI checks | Always deploy via CI pipeline |
| Monitoring added after incident | Reactive, not proactive | Instrument from day one |
| Same health check for liveness and readiness | Different failure modes need different checks | `/healthz` (alive) vs `/readyz` (ready) |
| Ignoring warm-up period | False alerts on every deploy | Grace period in health checks + readiness check |
| Force-killing during deploy | Drops active connections ungracefully | Drain period + client reconnect logic |

## Hard-won lessons

- **Dockerfile build entrypoint list drifts from `package.json` build script.**
  When adding new worker files, ALWAYS update BOTH. A worker will crash
  with `code:1` if the `.js` output is missing from `dist/`.
- **`fly logs --no-tail` (and equivalent non-streaming log commands) return
  only a small tail buffer** — use streaming logs or narrow with grep for
  debugging.
- **TDZ in const declarations:** JavaScript hoists `const`/`let` but they
  are NOT initialized until the declaration line. tsx/esbuild does NOT
  catch these at build time — they explode at runtime.
- **V8 `--max-old-space-size` tuning matters:** Undersized heaps can
  dramatically regress p50 latency due to GC pressure. Profile under
  realistic load and pick a size that gives headroom without oversubscribing
  the VM.
