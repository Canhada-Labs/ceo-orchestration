---
name: data-schema-design
description: PostgreSQL schema design including migration strategy and cross-ORM
  migration tooling (Prisma, Drizzle, Kysely, Django, golang-migrate), retention
  policy design, index strategy, keyset pagination, queue-claim patterns, disaster
  recovery DDL, SECURITY DEFINER safety, RLS policy patterns and RLS performance,
  naming conventions, and cross-engine notes for MySQL/MariaDB. Use when creating or
  modifying database tables, writing SQL migrations, planning zero-downtime rollouts,
  designing RLS policies, planning data retention, adding indexes, reviewing schema
  security, or troubleshooting query performance. Also use when the user mentions
  "schema", "DDL", "migration", "RLS", "retention", "index", "table", "enum",
  "pagination", "MySQL", "MariaDB", or "database design".
owner: Data Engineer (archetype)
version: 1.1.0
inspired_by:
  - source: msitarzewski/agency-agents/engineering/engineering-database-optimizer.md@783f6a72bfd7f3135700ac273c619d92821b419a
    license: MIT
    relationship: pattern_reference
    authored_by: ceo-orchestration framework
    authored_at: 2026-05-06
  - source: msitarzewski/agency-agents/engineering/engineering-data-engineer.md@783f6a72bfd7f3135700ac273c619d92821b419a
    license: MIT
    relationship: pattern_reference
    authored_by: ceo-orchestration framework
    authored_at: 2026-05-06
  - source: affaan-m/ecc/skills/database-migrations/@81af40761939056ab3dc54732fd4f562a27309d0
    license: MIT
    relationship: pattern_reference
    authored_by: ceo-orchestration framework
    authored_at: 2026-07-07
  - source: affaan-m/ecc/skills/postgres-patterns/@81af40761939056ab3dc54732fd4f562a27309d0
    license: MIT
    relationship: pattern_reference
    authored_by: ceo-orchestration framework
    authored_at: 2026-07-07
  - source: affaan-m/ecc/skills/mysql-patterns/@81af40761939056ab3dc54732fd4f562a27309d0
    license: MIT
    relationship: pattern_reference
    authored_by: ceo-orchestration framework
    authored_at: 2026-07-07
# --- smart-loading fields (PLAN-083 Wave 0a sub-agent 0.7a) ---
domain: core
priority: 4
risk_class: medium
stack: [postgres, sql]
context_budget_tokens: 1000
inactive_but_retained: false
repo_profile_binding:
  frontend: {active: true, priority: 6}
  engine: {active: true, priority: 3}
  fintech: {active: true, priority: 3}
  trading-readonly: {active: true, priority: 6}
  generic: {active: true, priority: 4}
activation_triggers:
  - {event: file-edit, glob: "**/migrations/**"}
  - {event: help-me-invoked, regex: "(?i)schema|migration|ddl|mysql|mariadb|pagination"}
source: affaan-m/ecc@81af4076 skills/database-migrations/ + skills/postgres-patterns/ + skills/mysql-patterns/
license: MIT
---

# Data Schema Design

This skill assumes PostgreSQL (including Supabase's PostgreSQL). For other databases, adapt the specifics but the principles transfer.

## Fail-Fast Rule

If a migration could cause data loss, **stop and require explicit confirmation**.
Never drop columns or tables without a backup plan. Never alter enum types in
a way that invalidates existing rows. Never run destructive DDL in production
without testing on a branch first.

## Cardinal Rule

**Every table in production must have a DDL file in the `sql/` directory.**
If a table exists in the database but has no DDL, it is undocumented technical
debt. Schema-as-code is the only way to recover from disaster. Audit periodically
to catch drift between production and the `sql/` directory.

## Audit Baseline: Current State

### Existing DDL Files (sql/ directory)

| File | Tables Covered |
|------|---------------|
| `core_tables.sql` | Foundational domain tables for the project |
| `billing_tables.sql` | Billing / subscription / webhook audit tables |
| `external_data_tables.sql` | Tables for ingested third-party data |
| `retention_policies.sql` | `run_retention_cleanup()` function |
| `retention_summary_tables.sql` | Daily summary / rollup tables |
| `security_fixes.sql` | RLS/function fixes (no new tables) |
| `rls_fixes.sql` | RLS policy fixes (no new tables) |

### Tables WITHOUT DDL (missing — identified in audit)

Run the audit query (see *Disaster Recovery*) to list tables in production that
have no corresponding `sql/` file. Every such table is a recovery risk and
should have a DDL file created.

**Priority**: Create DDL files for every table discovered by the audit. Without
them, a database disaster (unlikely but possible) means rebuilding from memory.

## Numeric Precision Convention

### Rule

**For financial or high-precision values, prefer `TEXT` (or `NUMERIC` with a
well-defined scale) and handle arithmetic in your application layer using a
decimal arithmetic library.**

```typescript
// Example client configuration
const client = createClient(url, key, {
  db: { schema: 'public' },
  // Return numerics as strings to prevent JavaScript floating-point corruption
});
```

### Why

JavaScript `Number` has 64-bit IEEE 754 precision. A value like
`12345678901234567890.123456789` loses precision when parsed as a JS number.
Many JSON parsers coerce numeric columns to JS numbers, corrupting them before
your code even sees them.

Supabase-specific: if you're on Supabase, some PostgREST/Supabase configs return
numerics as strings — handle this in your DTO layer. Route all arithmetic
through your decimal arithmetic library rather than native JS math.

### Column Type Guidelines

| Data Type | PostgreSQL Type | Example |
|-----------|----------------|---------|
| Prices, rates, amounts | `TEXT` | `price TEXT`, `amount TEXT` |
| Percentages | `TEXT` | `rate_pct TEXT`, `avg_rate_pct TEXT` |
| Counts (small, exact) | `INTEGER` | `item_count INTEGER`, `attempts INTEGER` |
| Counts (large) | `BIGINT` | `sequence_id BIGINT` |
| Timestamps (epoch ms) | `BIGINT` | `timestamp BIGINT`, `event_time BIGINT` |
| Timestamps (human) | `TIMESTAMPTZ` | `created_at TIMESTAMPTZ` |
| Booleans | `BOOLEAN` | `is_active BOOLEAN` |
| Enums/status | `TEXT` | `status TEXT`, `tier TEXT` |
| Structured data | `JSONB` | `payload JSONB`, `metadata JSONB` |
| Arrays | `TEXT[]` | `tags TEXT[]` |

### Anti-Pattern

```sql
-- RISKY: NUMERIC/DECIMAL columns may return with trailing zeros or varying
-- string representation depending on client config.
CREATE TABLE prices (
  price NUMERIC(20, 8),  -- e.g. "123.45000000" (trailing zeros)
  amount DECIMAL(30, 8), -- inconsistent string representation
);

-- SAFER: TEXT for all high-precision values
CREATE TABLE prices (
  price TEXT,   -- "123.45" exactly as written
  amount TEXT,  -- "1000000.5" exactly as written
);
```

Exception: `NUMERIC` is acceptable for statistical values (e.g. z-scores) used
for comparison, not for values where exact representation matters.

## RLS Policy Patterns

Supabase-specific: if you're on Supabase, RLS is enforced on the PostgREST
path and `auth.uid()` is available. On plain Postgres, you implement these
patterns at the application layer or via your own auth context — the SQL shape
still applies.

### Pattern 1: Public Read-Only Data

Used for: publicly-visible tables where anyone can read but only the backend writes.

```sql
ALTER TABLE public.<table> ENABLE ROW LEVEL SECURITY;

-- Anyone (anon, authenticated, service_role) can read
CREATE POLICY "Anon read <table>"
  ON public.<table>
  FOR SELECT
  USING (true);

-- Only service_role can write (bypasses RLS anyway, but explicit is better)
CREATE POLICY "Service write <table>"
  ON public.<table>
  FOR ALL
  TO service_role
  USING (true)
  WITH CHECK (true);
```

**Why not skip the service_role policy?** service_role bypasses RLS, so the
write policy is technically redundant. However, it documents the intent: "only
the backend writes here." If RLS behavior changes or someone uses a non-service
role, the policy protects the table.

### Pattern 2: User-Scoped Data (user sees only their own)

Used for: user profiles, user-owned resources, per-user audit trails.

```sql
ALTER TABLE public.<table> ENABLE ROW LEVEL SECURITY;

-- Users can read only their own rows
CREATE POLICY "Users read own <table>"
  ON public.<table>
  FOR SELECT
  USING (auth.uid() = user_id);

-- Users can insert their own rows
CREATE POLICY "Users insert own <table>"
  ON public.<table>
  FOR INSERT
  WITH CHECK (auth.uid() = user_id);

-- Service role manages all (backend webhook handlers, jobs)
CREATE POLICY "Service manage <table>"
  ON public.<table>
  FOR ALL
  TO service_role
  USING (true)
  WITH CHECK (true);
```

### Pattern 3: Tier-Gated Data (free users get limited access)

Used for: historical analytics, deep data access, premium features.

```sql
-- Users with paid tiers get full history
-- Free users get last 24 hours only
CREATE POLICY "Tier-gated read analytics"
  ON public.events
  FOR SELECT
  USING (
    public.get_user_tier(auth.uid()) IN ('pro', 'enterprise')
    OR event_time > (EXTRACT(EPOCH FROM NOW() - INTERVAL '24 hours') * 1000)::BIGINT
  );
```

### Pattern 4: Service-Only Sensitive Data

Used for: webhook event logs, internal audit logs, system internals.

```sql
ALTER TABLE public.<table> ENABLE ROW LEVEL SECURITY;

-- No public read access at all
-- Only service_role can read and write
-- (service_role bypasses RLS, so no policy needed, but explicit deny is safer)
CREATE POLICY "Deny all public access"
  ON public.<table>
  FOR ALL
  USING (false);
```

### Common RLS Mistakes (Fixed)

| Table | Issue | Fix Applied |
|-------|-------|-------------|
| `public.events` | `FOR ALL` without `TO service_role` | Dropped, service_role bypasses |
| `public.audit_log` | `FOR ALL` without `TO service_role` | Dropped |
| `public.signals` | `FOR ALL` without `TO service_role` | Dropped |
| `public.metrics` | `FOR ALL` without `TO service_role` | Replaced with `TO service_role` |
| `public.snapshots` | `FOR ALL` without `TO service_role` | Replaced with `TO service_role` |
| `public.indicators` | Unscoped INSERT/UPDATE | Replaced with single `FOR ALL TO service_role` |

## Migration Strategy

### Principles

1. **Idempotent**: Every migration uses `CREATE TABLE IF NOT EXISTS`,
   `CREATE INDEX IF NOT EXISTS`, `DROP POLICY IF EXISTS` before `CREATE POLICY`.
2. **Additive only**: Never drop columns in a migration. Add new columns,
   backfill, then deprecate old ones in a future migration.
3. **No breaking changes**: Old code must work with new schema, new code must
   work with old schema (during rolling deploy).
4. **Tested on branch**: Database branching (e.g. Supabase branching) allows
   testing migrations before applying to production.

### ALTER TYPE for Enums

Prefer TEXT columns over PostgreSQL ENUM types for flexibility. If an ENUM
type is ever needed:

```sql
-- SAFE: Add a value to existing enum
ALTER TYPE billing_tier ADD VALUE IF NOT EXISTS 'enterprise';

-- UNSAFE: Remove or rename enum values (requires migration)
-- 1. Create new enum type
CREATE TYPE billing_tier_v2 AS ENUM ('free', 'pro', 'enterprise');
-- 2. Alter column to use new type
ALTER TABLE users ALTER COLUMN tier TYPE billing_tier_v2 USING tier::text::billing_tier_v2;
-- 3. Drop old type
DROP TYPE billing_tier;
-- 4. Rename new type
ALTER TYPE billing_tier_v2 RENAME TO billing_tier;
```

**Convention**: Use TEXT for all status/tier/type columns. Validate
in application code, not database constraints. This avoids enum migration pain.

### Tier Consistency (Audit Finding)

When a project defines multiple tiers, verify all tables that reference tiers
use consistent values. Check:
- `users.tier`
- `subscriptions.tier`
- `api_keys.tier` (if exists)
- Application code `TIER_LIMITS` object

A mismatch between schema values and application constants is a common source
of silent bugs.

### Migration File Convention

```
sql/
  core_tables.sql           -- foundational domain tables
  billing_tables.sql        -- user billing columns, subscriptions, webhook events
  external_data_tables.sql  -- ingested third-party data
  retention_policies.sql    -- cleanup function
  retention_summary_tables.sql -- daily summary tables
  security_fixes.sql        -- RLS/function security patches
  rls_fixes.sql             -- additional RLS fixes
```

### Running Migrations

```sql
-- In your SQL editor (e.g. Supabase SQL Editor, psql, or CI migration tool):
-- Paste the contents of the .sql file and run.
-- All statements are idempotent — safe to re-run.
```

## Retention Policy Design

### Current Coverage

A `run_retention_cleanup()` function covers the project's retention-eligible
tables and is scheduled via pg_cron (typically daily at 04:00 UTC).

### Tables Covered by Retention

| Table | Retention | Time Column | Type |
|-------|-----------|-------------|------|
| `public.events` | 90 days | fetched_at (TIMESTAMPTZ) | DELETE |
| `public.metrics` | 90 days | calculated_at (TIMESTAMPTZ) | DELETE |
| `public.quotes` | 90 days | fetched_at (TIMESTAMPTZ) | DELETE |
| `public.news` | 90 days | fetched_at (TIMESTAMPTZ) | DELETE |
| `public.reports` | 90 days | fetched_at (TIMESTAMPTZ) | DELETE |
| `public.snapshots` | 90 days | snapshot_time (BIGINT ms) | DELETE |

### Tables MISSING Retention (need cleanup)

| Table | Growth Rate | Suggested Retention | Strategy |
|-------|-------------|--------------------|---------|
| `public.trades` | High | 7 days raw, summarize daily | Aggregate then delete |
| `public.opportunities` | High | 30 days raw, summarize daily | Aggregate then delete |
| `public.history` | Medium | 30 days raw, summarize daily | Aggregate then delete |
| `public.events` | Low-medium | 90 days | Direct delete |
| `public.alerts` | Low | 180 days | Direct delete |
| `public.telemetry` | Medium | 7 days (PII) | Direct delete |
| `public.snapshots` | High | 7 days raw, summarize daily | Aggregate then delete |
| `public.reference` | Low | Keep indefinitely (small) | No cleanup needed |
| `public.cache` | Bounded (upsert) | Self-cleaning via upsert | No cleanup needed |
| `public.logs_1m` | High | 90 days | Direct delete |
| `public.webhook_events` | Low | 365 days (audit) | Direct delete |
| `public.order_executions` | Medium | 5 years (regulatory) | Archive to cold storage |
| `public.audit_log` | Medium | 5 years (regulatory) | Archive to cold storage |

### Retention with Summarization Pattern

For high-volume tables, summarize before deleting:

```sql
-- Step 1: Summarize opportunities into daily_summary
INSERT INTO public.daily_summary (day, type, key, total_count,
  positive_count, avg_value, max_value, min_value, avg_gross_value)
SELECT
  DATE(TO_TIMESTAMP(timestamp / 1000)) AS day,
  type,
  key,
  COUNT(*) AS total_count,
  COUNT(*) FILTER (WHERE net_value::NUMERIC > 0) AS positive_count,
  AVG(net_value::NUMERIC)::TEXT AS avg_value,
  MAX(net_value::NUMERIC)::TEXT AS max_value,
  MIN(net_value::NUMERIC)::TEXT AS min_value,
  AVG(gross_value::NUMERIC)::TEXT AS avg_gross_value
FROM public.opportunities
WHERE timestamp < (EXTRACT(EPOCH FROM NOW() - INTERVAL '30 days') * 1000)::BIGINT
GROUP BY day, type, key
ON CONFLICT (day, type, key) DO NOTHING;

-- Step 2: Delete raw data older than 30 days
DELETE FROM public.opportunities
WHERE timestamp < (EXTRACT(EPOCH FROM NOW() - INTERVAL '30 days') * 1000)::BIGINT;
```

### Batch Delete with Backpressure

For large tables, delete in batches to avoid locking:

```sql
-- Delete in batches of 10,000 to avoid long locks
CREATE OR REPLACE FUNCTION public.batch_delete_old_rows(
  retention_days INTEGER DEFAULT 7,
  batch_size INTEGER DEFAULT 10000
)
RETURNS BIGINT AS $$
DECLARE
  _deleted BIGINT := 0;
  _batch_deleted BIGINT;
  _cutoff BIGINT;
BEGIN
  _cutoff := (EXTRACT(EPOCH FROM NOW() - (retention_days || ' days')::INTERVAL) * 1000)::BIGINT;

  LOOP
    DELETE FROM public.events
    WHERE id IN (
      SELECT id FROM public.events
      WHERE timestamp < _cutoff
      LIMIT batch_size
    );
    GET DIAGNOSTICS _batch_deleted = ROW_COUNT;
    _deleted := _deleted + _batch_deleted;

    -- Exit when no more rows to delete
    EXIT WHEN _batch_deleted = 0;

    -- Brief pause to release locks and let other queries run
    PERFORM pg_sleep(0.1);
  END LOOP;

  RETURN _deleted;
END;
$$ LANGUAGE plpgsql SECURITY DEFINER SET search_path = public;
```

## Index Strategy

### Composite Indexes for Query-Hot Paths

```sql
-- Cache table: queried by (source, key) and (key, updated_at)
CREATE INDEX IF NOT EXISTS idx_cache_key ON public.cache(key);
CREATE INDEX IF NOT EXISTS idx_cache_source ON public.cache(source);
CREATE INDEX IF NOT EXISTS idx_cache_updated_at ON public.cache(updated_at);
CREATE INDEX IF NOT EXISTS idx_cache_status ON public.cache(status);

-- Time-series tables: always (key, timestamp DESC) for "latest N" queries
CREATE INDEX IF NOT EXISTS idx_logs_1m_key_time ON public.logs_1m(key, open_time DESC);
CREATE INDEX IF NOT EXISTS idx_events_key_ts ON public.events(key, timestamp DESC);
CREATE INDEX IF NOT EXISTS idx_opportunities_key_ts ON public.opportunities(key, timestamp DESC);
CREATE INDEX IF NOT EXISTS idx_history_key_time ON public.history(key, bucket_time DESC);
CREATE INDEX IF NOT EXISTS idx_snapshots_key_ts ON public.snapshots(key, timestamp DESC);
```

### Partial Indexes for Filtered Queries

```sql
-- Only index active rows (most queries filter by is_active)
CREATE INDEX IF NOT EXISTS idx_reference_active
  ON public.reference(is_active)
  WHERE is_active = TRUE;

-- Only index recent events (queries rarely go back > 7 days)
CREATE INDEX IF NOT EXISTS idx_events_recent
  ON public.events(timestamp DESC)
  WHERE timestamp > (EXTRACT(EPOCH FROM NOW() - INTERVAL '7 days') * 1000)::BIGINT;

-- Only index non-free tier users (tier checks in RLS)
CREATE INDEX IF NOT EXISTS idx_users_paid_tier
  ON public.users(tier)
  WHERE tier != 'free';
```

### Index Guidelines

1. **Every foreign key gets an index** (PostgreSQL does not auto-index FKs).
2. **Every `WHERE` clause column in a frequent query gets an index.**
3. **Composite indexes**: leftmost column = most selective filter.
   `(key, timestamp DESC)` not `(timestamp DESC, key)`.
4. **Avoid over-indexing**: Each index costs write performance. Write-heavy
   workloads pay extra per index. Measure before adding.
5. **Use CONCURRENTLY**: `CREATE INDEX CONCURRENTLY` for production tables
   to avoid locking.

## SECURITY DEFINER Function Safety

### The Problem

`SECURITY DEFINER` functions run with the privileges of the function owner
(typically the `postgres` superuser). If the function's `search_path` is
mutable, an attacker could create a function in a different schema that
shadows a built-in function.

### The Fix

Always set `search_path` explicitly:

```sql
-- CORRECT: search_path pinned
CREATE OR REPLACE FUNCTION public.get_user_tier(user_id uuid)
RETURNS text
LANGUAGE sql STABLE SECURITY DEFINER
SET search_path = public
AS $$
  SELECT COALESCE(
    (SELECT tier FROM public.users WHERE id = user_id),
    'free'
  );
$$;

-- WRONG: search_path not set (linter warning: function_search_path_mutable)
CREATE OR REPLACE FUNCTION public.get_user_tier(user_id uuid)
RETURNS text
LANGUAGE sql STABLE SECURITY DEFINER
AS $$
  SELECT COALESCE(
    (SELECT tier FROM users WHERE id = user_id),
    'free'
  );
$$;
```

### Functions That Need search_path

| Function | Status |
|----------|--------|
| `run_retention_cleanup()` | Has `SECURITY DEFINER`, needs `SET search_path = public` |
| `update_<table>_updated_at()` triggers | Fix in security_fixes.sql |
| `get_user_tier()` | Needs `SET search_path = public` |
| `batch_delete_old_rows()` | Template above includes it |

## Naming Conventions

### Tables

- Snake_case, plural: `order_executions`, `audit_log`
- Prefix for external/ingested data with its source: e.g. `vendor_`
- Suffix `_cache` for frequently-refreshed data: `cache`, `data_cache`
- Suffix `_summary` for aggregated data: `daily_summary`, `weekly_summary`
- Suffix `_1m` for time-bucketed data: `logs_1m`, `metrics_1m`

### Columns

- Snake_case: `created_at`, `rate_pct`, `user_id`
- Primary key: `id BIGSERIAL PRIMARY KEY` (not UUID for high-volume tables)
- Foreign key: `user_id uuid REFERENCES auth.users(id)`
- Timestamps: `created_at TIMESTAMPTZ DEFAULT NOW()`, `updated_at TIMESTAMPTZ DEFAULT NOW()`
- Epoch timestamps: `timestamp BIGINT` (milliseconds), `event_time BIGINT`
- Status fields: `TEXT` not ENUM

### Indexes

- Format: `idx_<table>_<column(s)>`
- Examples: `idx_cache_key`, `idx_logs_1m_key_time`

### RLS Policies

- Format: `"<Action> <scope> <table>"`
- Examples: `"Anon read cache"`, `"Users read own api_keys"`, `"Service write logs_1m"`

## DDL Template for New Tables

```sql
-- ============================================================
-- <Table Name> — <Brief description>
-- Writer: <which service writes to this table>
-- Schedule: <how often, e.g., "30s batch upsert", "on demand">
-- ============================================================

CREATE TABLE IF NOT EXISTS public.<table_name> (
  id              BIGSERIAL PRIMARY KEY,
  -- Business columns
  source          TEXT        NOT NULL,
  key             TEXT        NOT NULL,
  -- High-precision values as TEXT
  value           TEXT,
  amount          TEXT,
  -- Metadata
  created_at      TIMESTAMPTZ DEFAULT NOW(),
  updated_at      TIMESTAMPTZ DEFAULT NOW(),
  -- Uniqueness constraint (if upsert)
  UNIQUE(source, key)
);

-- Indexes
CREATE INDEX IF NOT EXISTS idx_<table>_<column> ON public.<table_name>(<column>);

-- RLS
ALTER TABLE public.<table_name> ENABLE ROW LEVEL SECURITY;
CREATE POLICY "Anon read <table_name>"
  ON public.<table_name>
  FOR SELECT
  USING (true);
CREATE POLICY "Service write <table_name>"
  ON public.<table_name>
  FOR ALL
  TO service_role
  USING (true)
  WITH CHECK (true);
```

## Disaster Recovery

### Recovery Procedure

1. **Schema recovery**: Run all `sql/*.sql` files in order:
   - `core_tables.sql` first (foundational)
   - Then all other table files
   - Then `retention_policies.sql` (depends on tables existing)
   - Then `security_fixes.sql` and `rls_fixes.sql` (patches)

2. **Data recovery**: Many managed Postgres providers (including Supabase Pro)
   offer point-in-time recovery (PITR). Append-heavy data with upserts can
   often be regenerated from upstream sources.

3. **Non-recoverable data**: User profiles, credentials, order history, and
   anything user-authored. These MUST be backed up or have PITR enabled.

### DDL Audit Checklist

Run periodically to verify schema-as-code matches production:

```sql
-- List all tables in public schema
SELECT tablename FROM pg_tables WHERE schemaname = 'public' ORDER BY tablename;

-- Compare with tables documented in sql/ files
-- Any table in production but not in sql/ = missing DDL (add it)
-- Any table in sql/ but not in production = stale DDL (remove or deploy)
```

## Anti-Patterns to Reject

| Anti-Pattern | Why It's Wrong | Correct Approach |
|---|---|---|
| NUMERIC/DECIMAL for high-precision values | String representation varies between clients, risks silent precision loss | TEXT for all high-precision values, arithmetic via decimal library |
| PostgreSQL ENUM types | Painful to alter, migration-heavy | TEXT columns with app-level validation |
| `FOR ALL USING (true)` without `TO service_role` | Grants write to anon/authenticated | Always scope write policies to service_role |
| Table without DDL file | Cannot recover from disaster | Every table has a sql/ file |
| Single retention period for all tables | Different data has different value | Per-table retention based on usage + regulation |
| Missing `SET search_path` on SECURITY DEFINER | Schema injection vulnerability | Always set search_path = public |
| `DROP TABLE` in migration | Data loss, no recovery | Use `ALTER TABLE`, additive changes only |
| UUID primary keys on high-volume tables | Slower inserts, larger indexes | BIGSERIAL for time-series, UUID for user-facing |
| Missing indexes on foreign keys | Slow joins, slow cascading deletes | Index every FK column |
| Unbounded `DELETE` in retention | Locks table for duration | Batch delete with LIMIT + pg_sleep |

## Query Optimization Discipline

Slow queries are a schema problem as much as a query problem. Run `EXPLAIN ANALYZE`
before deploying any query that touches a table with more than 10,000 rows or
runs on a hot path (invoked per request, per message, per event).

### EXPLAIN ANALYZE Workflow

```sql
-- Step 1: Run with EXPLAIN (ANALYZE, BUFFERS, FORMAT TEXT) to see real execution
EXPLAIN (ANALYZE, BUFFERS, FORMAT TEXT)
SELECT u.id, u.tier, COUNT(o.id) AS order_count
FROM public.users u
JOIN public.order_executions o ON o.user_id = u.id
WHERE u.tier != 'free'
  AND o.created_at > NOW() - INTERVAL '30 days'
GROUP BY u.id, u.tier;

-- Read the output: look for these signals
-- BAD:  Seq Scan on a large table (no index hit)
-- BAD:  rows estimated=10 actual=94823 (planner was 9000x wrong — stale stats)
-- BAD:  Hash Join with very high actual rows (may spill to disk)
-- OK:   Bitmap Heap Scan (partial index used — acceptable for medium selectivity)
-- GOOD: Index Scan or Index Only Scan
```

**NEVER ship a query that produces a Seq Scan on a table over 50,000 rows**
without an explicit decision recorded in a comment: `-- Seq Scan accepted: table
is 200 rows, index cost > benefit`.

### Plan Regression Detection

Capture the query plan hash for every query on a hot path. Alert when the plan
changes between deployments — a plan change is often a sign that an index was
dropped, statistics drifted, or a new data distribution broke the planner's
assumptions.

```sql
-- Capture plan hash for regression tracking via EXPLAIN.
-- pg_stat_statements does NOT expose query plans (only normalized SQL +
-- timing); to track plan stability you must run EXPLAIN in CI and hash
-- the structured output yourself.
EXPLAIN (FORMAT JSON)
  SELECT *
  FROM order_executions
  WHERE status = 'open'
    AND created_at > now() - interval '7 days'
  ORDER BY created_at DESC
  LIMIT 100;
```

Capture the JSON output and split it into TWO independent CI artifacts:

1. **Structural plan hash** — normalize cost ranges + node IDs (they
   fluctuate with stats) and hash the remaining structure: join order,
   scan types, index choices, filter conditions. Store as
   `plan_structure_hash`. A change here MUST trigger deliberate review
   before merge.
2. **Row-estimate snapshot** — DO NOT normalize estimates. Store
   per-node `Plan Rows` as a separate `plan_rows_snapshot` artifact.
   A 10× drift on any node signals stats staleness or a data-distribution
   shift — alert independently of the structure hash.

Hashing structure AND estimates together collapses the very stats-drift
signal you most want to catch; keep them separate.

### Index Design Rules for Hot-Path Queries

| Query Pattern | Index Type | Example |
|---|---|---|
| Equality + range on same column | B-tree composite | `(status, created_at DESC)` |
| Queries filtering a known subset | Partial index | `WHERE status = 'active'` |
| Expression in WHERE clause | Expression index | `lower(email)` |
| Full-text search on TEXT column | GIN index | `gin_trgm_ops` on `description` |
| Covering query (no heap fetch) | Include columns | `(user_id) INCLUDE (tier, email)` |

**Covering index rule**: if a query reads only two or three columns after filtering,
add those columns to `INCLUDE (...)` so the planner can answer the query from
the index leaf page without a heap fetch. This eliminates the most expensive
part of an `Index Scan` on wide tables.

```sql
-- CORRECT: covering index for tier-gated user lookup
CREATE INDEX IF NOT EXISTS idx_users_tier_covering
  ON public.users (tier)
  INCLUDE (email, created_at)
  WHERE tier != 'free';

-- WRONG: forces a heap fetch for each matching row
CREATE INDEX IF NOT EXISTS idx_users_tier ON public.users (tier);
```

### Eliminating N+1 Queries

An N+1 query is a loop that issues one query per row from a parent result.
It is the single most common cause of application-layer slow queries that look
fine in isolation.

```sql
-- WRONG: application loop issues one query per user
-- SELECT * FROM users LIMIT 20;
-- then for each user: SELECT * FROM orders WHERE user_id = $1;
-- = 1 + 20 = 21 round trips, scales with result size

-- CORRECT: single JOIN with aggregation
SELECT
  u.id,
  u.email,
  u.tier,
  COALESCE(
    json_agg(
      json_build_object('id', o.id, 'amount', o.amount, 'created_at', o.created_at)
      ORDER BY o.created_at DESC
    ) FILTER (WHERE o.id IS NOT NULL),
    '[]'
  ) AS recent_orders
FROM public.users u
LEFT JOIN public.order_executions o
  ON o.user_id = u.id
  AND o.created_at > NOW() - INTERVAL '30 days'
GROUP BY u.id, u.email, u.tier
LIMIT 20;
```

When a JOIN result set is too large to aggregate safely, use a lateral
subquery to cap the per-parent rows explicitly:

```sql
-- Lateral: fetch at most 5 recent orders per user without a full JOIN
SELECT u.id, u.email, recent.orders
FROM public.users u
CROSS JOIN LATERAL (
  SELECT json_agg(o ORDER BY o.created_at DESC) AS orders
  FROM (
    SELECT id, amount, created_at
    FROM public.order_executions
    WHERE user_id = u.id
    ORDER BY created_at DESC
    LIMIT 5
  ) o
) recent
WHERE u.tier != 'free'
LIMIT 20;
```

### Materialized View Refresh Strategy

Use materialized views for aggregations that are expensive to recompute per
request but do not require sub-minute freshness.

```sql
-- Create the materialized view
CREATE MATERIALIZED VIEW public.mv_daily_revenue AS
SELECT
  DATE(created_at) AS day,
  tier,
  COUNT(*) AS order_count,
  SUM(amount::NUMERIC)::TEXT AS total_revenue
FROM public.order_executions
WHERE status = 'completed'
GROUP BY DATE(created_at), tier
WITH DATA;

-- Index it like any other table
CREATE UNIQUE INDEX ON public.mv_daily_revenue (day, tier);

-- Refresh on a schedule via pg_cron (not CONCURRENTLY if small; CONCURRENTLY if large)
SELECT cron.schedule(
  'refresh-daily-revenue',
  '0 * * * *',   -- every hour
  'REFRESH MATERIALIZED VIEW CONCURRENTLY public.mv_daily_revenue'
);
```

**NEVER use `REFRESH MATERIALIZED VIEW` without `CONCURRENTLY` on a
production table that serves live reads.** The non-concurrent form takes
an exclusive lock for the entire refresh duration.

## ETL/ELT and Pipeline Schema Discipline

Tables that serve as pipeline landing zones or intermediate stages carry
additional constraints beyond regular application tables. Violating them
causes silent data corruption that only surfaces hours or days later.

### Batch vs. Streaming Choice Rubric

Choose the pipeline model before writing any DDL. The model determines the
table structure, index strategy, and schema evolution contract.

| Dimension | Choose Batch | Choose Streaming |
|---|---|---|
| Acceptable latency | Minutes to hours | Seconds |
| Source delivery | Files, database exports | Kafka, CDC, webhooks |
| Processing cost sensitivity | Low (burst OK) | High (sustained cost) |
| Replay safety / effectively-once | Idempotent upserts (replay-safe; not true exactly-once distributed-systems semantics) | Offset tracking + transactional sink (still effectively-once at consumer) |
| Schema change frequency | High (dbt handles it) | Low (hard to hot-swap) |

If latency tolerance is above 5 minutes, batch is almost always the right
choice. Streaming carries real operational cost (broker management, consumer
group lag monitoring, offset tracking + transactional sink + replay-safety
machinery for effectively-once delivery) that batch avoids entirely.

### Idempotency and Replay Safety

**Every pipeline landing table MUST support idempotent writes.** A replay
(re-running the pipeline for the same time window) MUST produce the same
final state, not duplicate rows or overwritten aggregates.

```sql
-- CORRECT: upsert with explicit conflict target
INSERT INTO public.external_prices (source, key, price, fetched_at)
VALUES ($1, $2, $3, $4)
ON CONFLICT (source, key) DO UPDATE
  SET price = EXCLUDED.price,
      fetched_at = EXCLUDED.fetched_at
WHERE EXCLUDED.fetched_at > external_prices.fetched_at;  -- only advance, never regress

-- WRONG: INSERT without conflict handling — duplicates on replay
INSERT INTO public.external_prices (source, key, price, fetched_at)
VALUES ($1, $2, $3, $4);
```

For append-only tables (event logs, audit trails), replay safety requires a
deduplication key:

```sql
-- Deduplication key on the append-only table
CREATE TABLE IF NOT EXISTS public.raw_events (
  id            BIGSERIAL PRIMARY KEY,
  event_id      TEXT        NOT NULL,  -- upstream idempotency key
  source        TEXT        NOT NULL,
  payload       JSONB       NOT NULL,
  ingested_at   TIMESTAMPTZ DEFAULT NOW(),
  UNIQUE(source, event_id)             -- replay safe: duplicate = conflict = skip
);
```

### Schema Evolution Contract for Downstream Consumers

When a pipeline table's schema changes, downstream consumers (dbt models,
materialized views, application queries) break silently unless a migration
discipline is enforced.

**Hard rules for pipeline schema changes:**

1. **Additive only in the same major version.** New nullable columns are
   safe to add. Dropping columns, renaming columns, or changing column types
   requires a versioned table or a coordinated cut-over.

2. **Announce breaking changes with lead time.** Add the new column, publish
   the change, give consumers one full pipeline cycle to adapt, then remove
   the old column. Never drop on the same day you add the replacement.

3. **Dual-write during cut-over.** When renaming a column, write both the
   old and new name for one full release cycle:

   ```sql
   -- Migration: dual-write period (both columns populated)
   ALTER TABLE public.external_data ADD COLUMN symbol TEXT;
   UPDATE public.external_data SET symbol = ticker WHERE symbol IS NULL;

   -- Application: write both until all consumers migrated
   -- INSERT INTO external_data (ticker, symbol, ...) VALUES ($1, $1, ...)

   -- After all consumers updated: drop old column in a separate migration
   ALTER TABLE public.external_data DROP COLUMN ticker;
   ```

4. **Document the schema contract at the table level.** Use a DDL comment
   that lists the consumer list and the freshness SLA:

   ```sql
   COMMENT ON TABLE public.external_data IS
     'Pipeline landing table for external market data.
      Consumers: mv_daily_summary, api/v1/prices, dbt model silver_prices.
      SLA: refreshed every 30 seconds. Schema changes require 24h notice to consumers.';
   ```

### Pipeline Observability Columns

Every pipeline table MUST include audit columns so failures and replays can
be traced without external logging:

```sql
CREATE TABLE IF NOT EXISTS public.pipeline_landing (
  id              BIGSERIAL PRIMARY KEY,
  -- Business payload
  source          TEXT        NOT NULL,
  key             TEXT        NOT NULL,
  payload         JSONB       NOT NULL,
  -- Pipeline audit columns (NEVER omit these)
  ingested_at     TIMESTAMPTZ NOT NULL DEFAULT NOW(),
  pipeline_run_id TEXT        NOT NULL,  -- identifies which run wrote this row
  source_file     TEXT,                  -- path or URL of the source file/batch
  row_checksum    TEXT,                  -- md5 or sha256 of payload for drift detection
  UNIQUE(source, key, pipeline_run_id)
);
```

`pipeline_run_id` lets you answer: "which pipeline run wrote these rows?"
without querying an external log system. `row_checksum` lets you detect
silent data mutation between pipeline stages.

## Migration Tooling and Rollout Safety

The *Migration Strategy* section above covers the idempotent, Postgres-first
DDL shape this project uses. This section covers the discipline that holds
regardless of which migration runner a target repo already uses, and the
zero-downtime rollout pattern for changes that would otherwise break a rolling
deploy.

### Migration Discipline (tool-independent)

1. **Every change is a migration file.** Never hand-run DDL against a production
   database. A manual change leaves no audit trail and cannot be replayed onto a
   fresh environment, so environments silently diverge.
2. **Migrations are immutable once they have run in production.** Editing a
   landed migration makes the version that ran in prod no longer match the one in
   the repo — the definition of drift. To change course, add a *new* forward
   migration; never rewrite history.
3. **Roll forward, not back.** In production a "rollback" is a new migration that
   undoes the change, not an in-place reversal. Keep a documented DOWN for
   local/dev iteration, but treat production recovery as forward-only.
4. **Separate schema (DDL) from data (DML).** A backfill that transforms millions
   of rows has a different risk and retry profile from an `ALTER TABLE`. Mixing
   them in one migration makes both harder to reason about, and a failed backfill
   can strand the schema change mid-flight. (This is the operational twin of the
   *Additive only* rule.)
5. **Rehearse against production-sized data.** A migration that returns instantly
   on 100 rows can hold a lock for minutes on 10M. Test on a branch or a restored
   snapshot before applying.

### Migration Safety Checklist

Before applying any migration:

- [ ] Reversible, **or** explicitly marked irreversible with a recovery note.
- [ ] No full-table lock on a large table (concurrent DDL, batched DML).
- [ ] New columns are nullable or carry a default. Never add `NOT NULL` **without
      a default** to a populated table — that rewrites every row under an
      exclusive lock. (On Postgres 11+, `ADD COLUMN ... NOT NULL DEFAULT <const>`
      is a metadata-only change and is safe; the hazard is the *no-default* case.)
- [ ] Indexes built `CONCURRENTLY`, outside a transaction block.
- [ ] Data backfill is its own migration, batched.
- [ ] Rehearsed on production-sized data; recovery path written down.

### Cross-Tool Quick Reference

Our default is raw Postgres DDL in `sql/`. When a target repo already drives
migrations through an ORM's runner, these are the commands you'll meet — the
safety rules above are tool-independent and still apply.

| Runner | Generate | Apply (prod) | Custom SQL / concurrent index |
|---|---|---|---|
| Prisma | `prisma migrate dev --name x` | `prisma migrate deploy` | `prisma migrate dev --create-only`, then hand-edit — Prisma does not emit `CONCURRENTLY` |
| Drizzle | `drizzle-kit generate` | `drizzle-kit migrate` | Edit the generated SQL by hand; `drizzle-kit push` is dev-only (no migration file) |
| Kysely | `kysely migrate:make x` | `kysely migrate:latest` | Write `up`/`down` in TS; type the DB as `Kysely<any>` so a frozen migration never depends on current schema types |
| Django | `makemigrations` | `migrate` | `makemigrations --empty` for a `RunPython` backfill; `SeparateDatabaseAndState` to drop a field from model state without touching the DB yet |
| golang-migrate | `migrate create -ext sql -seq x` | `migrate ... up` | Paired `.up.sql`/`.down.sql`; `migrate ... force VERSION` clears a dirty state |

One caveat that bites every runner: `CREATE INDEX CONCURRENTLY` cannot run inside
a transaction, and most runners wrap each migration in one. Isolate a concurrent
index in its own migration, or use the runner's explicit "no transaction" escape
hatch.

### Expand–Contract (Zero-Downtime) Rollout

Any change that a rolling deploy would break — renaming a column, tightening a
type, splitting a table — goes through three phases so that old and new code run
side by side without error. This is the same principle as the *Dual-write during
cut-over* rule in the pipeline section, generalized to all schema change.

```
Phase 1 — EXPAND
  Add the new column/table (nullable or defaulted).
  Deploy code that writes BOTH old and new.
  Backfill existing rows in batches.

Phase 2 — MIGRATE
  Deploy code that READS new, still WRITES both.
  Verify old and new agree.

Phase 3 — CONTRACT
  Deploy code that uses only new.
  Drop the old column/table in a SEPARATE, later migration.
```

Column rename is the canonical case: never `ALTER TABLE ... RENAME COLUMN` in
place on a live table. Add the new name, dual-write, cut reads over, then drop
the old name once no deployed code references it. A representative day-scale
timeline (compress or stretch to your deploy cadence):

```
Day 1  Migration adds new_status (nullable); deploy v2 writes status + new_status
Day 2  Backfill migration fills new_status for existing rows
Day 3  Deploy v3 reads new_status only (still writes both)
Day 7  Migration drops the old status column
```

### Batched Backfill with SKIP LOCKED

The *Batch Delete with Backpressure* function covers deletes; backfills need the
same backpressure. `FOR UPDATE SKIP LOCKED` lets several workers backfill
disjoint row sets without blocking each other, and the batch loop keeps any
single transaction short:

```sql
-- Backfill in bounded batches, releasing locks between batches.
CREATE OR REPLACE PROCEDURE public.backfill_normalized_email(batch_size INT DEFAULT 10000)
LANGUAGE plpgsql AS $$
DECLARE _n INT;
BEGIN
  LOOP
    UPDATE public.users
      SET normalized_email = lower(email)
    WHERE id IN (
      SELECT id FROM public.users
      WHERE normalized_email IS NULL
      LIMIT batch_size
      FOR UPDATE SKIP LOCKED
    );
    GET DIAGNOSTICS _n = ROW_COUNT;
    EXIT WHEN _n = 0;
    COMMIT;   -- release row locks + WAL pressure between batches
  END LOOP;
END $$;

CALL public.backfill_normalized_email();
```

Note the `PROCEDURE`/`CALL` shape: transaction-control statements (`COMMIT`)
are never legal inside an ordinary function, and inside a `DO $$ ... $$`
block only on PG11+ when invoked at top level (outside an explicit
transaction). The stored `PROCEDURE` + `CALL` shape works on every PG >= 11
and keeps the transaction boundaries explicit; an application-side loop is
the portable fallback.
If your migration runner wraps each migration in a single transaction, drive the
loop from application code instead so each batch commits independently.

## Access Patterns: Pagination, Queues, and RLS Performance

These are read/write shapes that keep hot paths fast as tables grow. They
complement the *Index Strategy* and *RLS Policy Patterns* sections above.

### Keyset (Cursor) Pagination

`OFFSET n` makes the database scan and discard `n` rows before returning the
page — O(n), and it gets slower the deeper a user pages. Keyset pagination
carries the last row's sort key as a cursor and is effectively O(1) per page:

```sql
-- First page
SELECT id, created_at
FROM public.events
ORDER BY created_at DESC, id DESC
LIMIT 20;

-- Next page: pass the last row's (created_at, id) back as the cursor
SELECT id, created_at
FROM public.events
WHERE (created_at, id) < ($last_created_at, $last_id)
ORDER BY created_at DESC, id DESC
LIMIT 20;
```

Back it with an index whose column order matches the `ORDER BY`:
`(created_at DESC, id DESC)`. Use the **row-value** comparison
`(created_at, id) < (...)`, not a bare `created_at <` — comparing only the
timestamp duplicates or skips rows at the page boundary whenever two rows share
a timestamp. The trailing unique key (`id`) breaks the tie deterministically.

### Queue Claim with SKIP LOCKED

To hand work to N concurrent workers without two of them grabbing the same job,
claim the next row under `FOR UPDATE SKIP LOCKED`:

```sql
UPDATE public.jobs
  SET status = 'processing', started_at = NOW()
WHERE id = (
  SELECT id FROM public.jobs
  WHERE status = 'pending'
  ORDER BY created_at
  LIMIT 1
  FOR UPDATE SKIP LOCKED
)
RETURNING *;
```

`SKIP LOCKED` is correct **only** for queue-style work where skipping a
row another worker already holds is the desired behavior. Never use it for
balance reads, accounting, or any integrity-sensitive query — it deliberately
returns an inconsistent snapshot (locked rows simply vanish from the result).

### RLS Predicate Performance

A policy predicate is evaluated per row. If it calls a stable function such as
`auth.uid()` directly, the planner may re-evaluate that call for every row. Wrap
the call in a scalar subquery so the planner hoists it to an init-plan evaluated
once per statement:

```sql
-- Slower: auth.uid() may run per row
CREATE POLICY "Users read own t" ON public.t
  FOR SELECT USING (auth.uid() = user_id);

-- Faster: evaluated once, then compared per row — identical meaning
CREATE POLICY "Users read own t" ON public.t
  FOR SELECT USING ((SELECT auth.uid()) = user_id);
```

Apply the same wrap to any `STABLE` helper used in a policy, e.g.
`(SELECT public.get_user_tier((SELECT auth.uid())))`. This changes nothing about
what the policy permits — only how many times the function runs — and is a
measurable win on large tables.

### BRIN for Append-Only Time-Series

The *Index Strategy* section uses B-tree composite and partial indexes. For very
large **append-only** tables whose rows land in roughly time order (event logs,
`snapshots` keyed by `timestamp`, ingest tables), a BRIN index on the time column
is a tiny fraction of the size of a B-tree and is enough to prune block ranges
for wide range scans:

```sql
CREATE INDEX IF NOT EXISTS brin_events_ts ON public.events USING brin (timestamp);
```

BRIN only helps when physical heap order correlates with the indexed column —
true for append-only ingest, false once heavy updates/deletes shuffle the heap.
Keep the B-tree `(key, timestamp DESC)` for "latest N per key" lookups; add BRIN
alongside it for historical range scans over the whole table.

### Drift-Detection Queries

Run these periodically; they complement the *DDL Audit Checklist*:

```sql
-- Foreign keys with no backing index (slow joins + slow cascading deletes)
SELECT conrelid::regclass AS tbl, a.attname AS col
FROM pg_constraint c
JOIN pg_attribute a ON a.attrelid = c.conrelid AND a.attnum = ANY (c.conkey)
WHERE c.contype = 'f'
  AND NOT EXISTS (
    SELECT 1 FROM pg_index i
    WHERE i.indrelid = c.conrelid AND a.attnum = ANY (i.indkey)
  );

-- Tables accumulating dead tuples (autovacuum falling behind)
SELECT relname, n_dead_tup, last_autovacuum
FROM pg_stat_user_tables
WHERE n_dead_tup > 1000
ORDER BY n_dead_tup DESC;

-- Slowest normalized statements (requires the pg_stat_statements extension)
SELECT query, calls, mean_exec_time
FROM pg_stat_statements
WHERE mean_exec_time > 100
ORDER BY mean_exec_time DESC
LIMIT 20;
```

### Server-Level Guards

Two settings stop a single runaway query or a forgotten open transaction from
taking the database down. Set them at the database or role level, not just per
session:

```sql
ALTER DATABASE app SET statement_timeout = '30s';
ALTER DATABASE app SET idle_in_transaction_session_timeout = '30s';
```

And revoke the default `public` schema grant so newly created objects are not
world-usable by accident, then grant explicitly:

```sql
REVOKE ALL ON SCHEMA public FROM PUBLIC;
```

This is defense-in-depth alongside RLS, not a replacement for it.

## Cross-Engine Notes: MySQL and MariaDB

This skill assumes Postgres, and the *principles* transfer directly:
schema-as-code, additive migrations, indexed foreign keys, exact-decimal money,
batched deletes, and least privilege all apply unchanged. When a target repo is
on MySQL or MariaDB, the items below are the concrete syntax and behavioral
differences that actually bite. The two engines have diverged, so identify which
one you are on before applying a version-specific pattern.

### Identify the Engine and Version First

```sql
SELECT VERSION();
SHOW VARIABLES LIKE 'version_comment';
```

### Schema Defaults

```sql
CREATE TABLE orders (
    id          BIGINT UNSIGNED NOT NULL AUTO_INCREMENT,
    account_id  BIGINT UNSIGNED NOT NULL,
    status      VARCHAR(32)     NOT NULL,
    total       DECIMAL(15, 2)  NOT NULL,
    created_at  DATETIME        NOT NULL DEFAULT CURRENT_TIMESTAMP,
    updated_at  DATETIME        NOT NULL DEFAULT CURRENT_TIMESTAMP ON UPDATE CURRENT_TIMESTAMP,
    deleted_at  DATETIME        NULL,
    PRIMARY KEY (id),
    KEY idx_orders_account_status_created (account_id, status, created_at),
    KEY idx_orders_active (account_id, deleted_at)
) ENGINE=InnoDB DEFAULT CHARSET=utf8mb4 COLLATE=utf8mb4_unicode_ci;
```

| Concern | Prefer | Avoid |
|---|---|---|
| Surrogate primary key | `BIGINT UNSIGNED AUTO_INCREMENT` | `INT` on anything that can pass ~2B rows |
| UUID lookup key | `BINARY(16)` with app-side conversion | `VARCHAR(36)` primary key on a hot table |
| Money / exact quantity | `DECIMAL(p, s)` | `FLOAT` / `DOUBLE` (same lesson as our Postgres money rule — exact type, never binary float) |
| User-facing text | `utf8mb4` tables and indexes | the legacy `utf8` / `utf8mb3` alias (3-byte; drops emoji and some CJK) |
| Application timestamps | `DATETIME`, UTC managed by the app | assuming any type stores a time zone |
| Soft delete | `deleted_at DATETIME NULL` + an index that scopes it | filtering soft-deletes with no supporting index |
| Changing status set | lookup table or constrained `VARCHAR` | `ENUM` when values churn (mirrors our "TEXT not ENUM" rule) |

### Upsert — Engine Divergence

This is the sharpest edge. MySQL now documents a **row-alias** form and
deprecates `VALUES(col)`; MariaDB still documents `VALUES(col)`. For a mixed or
unknown fleet, `VALUES(col)` is the portable choice:

```sql
-- Portable (MySQL + MariaDB)
INSERT INTO user_settings (user_id, setting_key, setting_value)
VALUES (?, ?, ?)
ON DUPLICATE KEY UPDATE
    setting_value = VALUES(setting_value),
    updated_at    = CURRENT_TIMESTAMP;

-- MySQL-only row alias (use only after confirming the engine is MySQL)
INSERT INTO user_settings (user_id, setting_key, setting_value)
VALUES (?, ?, ?) AS new
ON DUPLICATE KEY UPDATE
    setting_value = new.setting_value,
    updated_at    = CURRENT_TIMESTAMP;
```

### Keyset Pagination

Same shape as the Postgres pattern above, MySQL syntax:

```sql
SELECT id, name, created_at
FROM products
WHERE (created_at, id) < (?, ?)
ORDER BY created_at DESC, id DESC
LIMIT 50;
-- back it with:  CREATE INDEX idx_products_created_id ON products (created_at, id);
```

Deep `OFFSET` is O(n) here too — avoid it on large tables.

### JSON Columns

Store extension data in a `JSON` column, but keep ownership, tenancy, and
lifecycle fields relational. To index a hot JSON path, expose a **generated
column** and index that column, not the JSON directly:

```sql
CREATE TABLE events (
    id         BIGINT UNSIGNED AUTO_INCREMENT PRIMARY KEY,
    payload    JSON NOT NULL,
    event_type VARCHAR(64)
        GENERATED ALWAYS AS (JSON_UNQUOTE(JSON_EXTRACT(payload, '$.type'))) STORED,
    KEY idx_events_type (event_type)
) ENGINE=InnoDB DEFAULT CHARSET=utf8mb4;
```

### Reading EXPLAIN

| Field | Investigate when |
|---|---|
| `type` | `ALL` (full scan) on a large table |
| `key` | `NULL` despite a selective predicate existing |
| `rows` | very high estimate on an interactive path |
| `Extra` | `Using temporary`, `Using filesort`, or a broad `Using where` |

Use `EXPLAIN ANALYZE` only where it is safe to actually run the statement — it
executes the query and can be expensive on production-sized data.

### Transactions and Deadlocks

Keep transactions short and lock rows in a **deterministic order** across every
code path — two paths locking the same rows in opposite order is the number-one
deadlock cause.

```sql
START TRANSACTION;
SELECT id, balance FROM accounts
  WHERE id IN (?, ?) ORDER BY id FOR UPDATE;   -- deterministic lock order
UPDATE accounts SET balance = balance - ? WHERE id = ?;
UPDATE accounts SET balance = balance + ? WHERE id = ?;
COMMIT;
```

Deadlock / lock-wait checklist:

- Do external/API calls **before** opening the transaction, never inside it.
- Index every predicate used in `UPDATE`, `DELETE`, and locking reads.
- On deadlock, roll back and retry the whole transaction with a bounded budget.
- Capture `SHOW ENGINE INNODB STATUS\G` immediately — it is overwritten by the
  next event.
- For queue-style workers, claim with `FOR UPDATE SKIP LOCKED` (queue work only,
  same caveat as the Postgres queue pattern).

### Connection Pool Sizing

Keep the pool's recycle age **below** the server `wait_timeout`, or the server
drops idle connections the pool still believes are live. If `wait_timeout = 300`,
a `pool_recycle` around 240s plus a checkout-time pre-ping (SQLAlchemy
`pool_pre_ping`) is coherent and recovers cleanly from failover. Note for
`mysql2`: `enableKeepAlive` is TCP-level keepalive only — it does NOT
validate a connection at pool checkout; pair the recycle age with a
`connection.ping()`-on-checkout or retry-on-stale wrapper instead.

### Replication Read-After-Write

Read replicas lag. Never route read-your-own-write paths — checkout, permission
checks, idempotency-key reads — to a replica immediately after a write; pin those
to the primary. Monitor SQL-thread health, IO-thread health, and lag, not just
TCP liveness. The status command name differs by version — `SHOW REPLICA STATUS\G`
on newer builds, `SHOW SLAVE STATUS\G` on older fleets — so check before
standardizing on one.

### Least Privilege and TLS

Same posture as our Postgres `SECURITY DEFINER` / RLS discipline:

- The runtime application user is **not** the migration/admin user and never
  holds `ALL PRIVILEGES` or `*.*`.
- Require TLS for users whose traffic crosses hosts (`ALTER USER ... REQUIRE SSL`).
- Manage grants through `CREATE USER` / `ALTER USER` / `DROP USER`, never by DML
  against `mysql.user` (grant-table corruption risk).
- Remove anonymous users (`DROP USER IF EXISTS ''@'localhost'`).
- Store credentials in a secret manager, never in migration files or examples.

### Configuration Is a Prompt for Review, Not a Preset

Durability and sizing knobs (`innodb_buffer_pool_size`, `max_connections`,
`innodb_flush_log_at_trx_commit`, `sync_binlog`, `wait_timeout`, slow-log
settings, binlog retention) must be sized from the workload, hardware, backup
policy, and recovery objectives — not copied from a template. Treat any example
`my.cnf` as a starting point to review, not a universal default.

### MySQL/MariaDB Anti-Patterns

| Anti-Pattern | Risk | Better Pattern |
|---|---|---|
| `SELECT *` on hot paths | Over-fetching, brittle clients | Select explicit columns |
| Deep `OFFSET` pagination | Linear scans, slow pages | Keyset pagination |
| No index on FK joins | Slow joins, lock-heavy deletes | Index FK columns intentionally |
| Long transactions | Lock waits, large undo history | Commit small units of work |
| Direct DML against `mysql.user` | Grant-table corruption | `CREATE`/`ALTER`/`DROP USER` |
| App user with admin grants | Large blast radius | Least-privilege runtime user |
| `pool_recycle` above `wait_timeout` | Stale pooled connections | Recycle below timeout + pre-ping |
| Replica read after write | Stale user-facing state | Pin read-after-write flows to primary |

### When Reviewing a MySQL/MariaDB Change

State the engine/version assumption up front, call out the highest-risk
correctness, lock, security, and migration issues, give the exact safe SQL, and
attach a validation plan: `EXPLAIN`, a migration dry run on production-sized
data, a lock/deadlock check, and rollback criteria. Flag any MySQL-vs-MariaDB
syntax difference that changes the recommendation.

## Changelog

- **1.1.0** (2026-07-07, PLAN-153 Wave G, SP-027): clean-room ADAPT merge of three
  upstream skills into new sections — *Migration Tooling and Rollout Safety*
  (tool-independent migration discipline, safety checklist, cross-ORM runner
  reference, expand–contract rollout, SKIP-LOCKED batched backfill),
  *Access Patterns: Pagination, Queues, and RLS Performance* (keyset pagination,
  queue claim, RLS init-plan wrap, BRIN, drift-detection queries, server-level
  guards), and *Cross-Engine Notes: MySQL and MariaDB*. Also introduced the
  `version:` frontmatter and this changelog, extended `description` +
  `activation_triggers`, and recorded provenance in `inspired_by`. No existing
  section was altered; all additions are net-new.
Skill-Import-Attestation: reviewed-by=AE9B236FDAF0462874060C6BCFCFACF00335DC74; sha256=702045c2a1b730fe8184e11fa458fc726891b36379c513e9e55cac643187a2c6
