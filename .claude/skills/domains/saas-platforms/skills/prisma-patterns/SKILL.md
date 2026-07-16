---
name: prisma-patterns
description: >
  Production patterns and footgun avoidance for the Prisma ORM in TypeScript
  backends: schema and index design, ID strategy, include-vs-select and DTO
  mapping, transaction form selection, the PrismaClient singleton, cursor
  pagination, soft delete, typed error translation, and serverless connection
  pooling. Emphasises the non-obvious traps that silently corrupt data or
  exhaust connections — updateMany/deleteMany returning a count instead of
  rows, the interactive $transaction 5-second timeout, `migrate dev` resetting
  the database, @updatedAt skipping bulk writes, edited migration files
  breaking checksums, and where soft delete leaks through *OrThrow reads. Use
  when designing Prisma schema, writing queries or transactions, running
  migrations, or deploying to serverless runtimes.
version: 1.0.0
metadata:
  activation_triggers:
    - "prisma"
    - "schema\\.prisma"
    - "PrismaClient"
    - "\\$transaction"
    - "updateMany|deleteMany|findUniqueOrThrow|findFirstOrThrow"
    - "migrate (dev|deploy|diff)"
    - "prisma/migrations"
    - "P2002|P2025|P2003|P3006"
    - "connection_limit|pgbouncer"
  paths:
    - "**/schema.prisma"
    - "**/prisma/**"
    - "**/prisma.config.ts"
  risk_class: low
  domain: saas-platforms
source: affaan-m/ecc@81af4076 skills/prisma-patterns/
license: MIT
---

# Prisma Patterns

Idiomatic patterns and the sharp edges of the Prisma ORM in TypeScript
backends. Prisma is ergonomic on the happy path; most production incidents
come from a handful of methods that behave differently than their names
suggest. This skill front-loads those.

## When to Activate

- Designing or changing Prisma schema models, relations, or indexes.
- Writing queries, transactions, or pagination.
- Reaching for any bulk operation (`updateMany`, `deleteMany`, `createMany`).
- Planning or running a migration against anything other than a solo local DB.
- Deploying to a serverless or edge runtime (functions, Lambda, workers).
- Implementing soft delete or per-tenant row filtering.

## Version First

The Prisma surface has shifted across majors — check before applying any
snippet here.

```bash
npx prisma --version
```

Things that move between versions, and how to stay portable:

- **Relation loading.** Newer clients can resolve relations with a single
  SQL `JOIN` instead of separate round trips. This is usually faster, but on
  wide 1:N relations or deep `include` it can inflate the result set (row
  fan-out). Benchmark both strategies on your real cardinality; do not assume.
- **Client shape.** Recent installs may expose the client as `prisma` rather
  than `@prisma/client`, may require a driver adapter in the constructor
  (e.g. a Postgres adapter), and may read the datasource URL from a config
  file rather than `schema.prisma`. Let the type checker tell you which shape
  you have instead of hardcoding one.
- **Stable surface.** The migration CLI verbs (`migrate dev`,
  `migrate deploy`, `generate`) are consistent across versions — the traps
  below apply regardless.

## Schema & Indexing

### Choosing an ID

| Strategy | Reach for it when | Avoid when |
|---|---|---|
| collision-resistant string id (cuid-style) | Default. URL-safe, roughly sortable, no coordination needed | An external system demands strictly sequential ids |
| UUID | You must interoperate with non-Prisma systems that expect UUIDs | Very high write volume — random UUIDs fragment B-tree indexes and hurt insert locality |
| auto-increment integer | Internal join tables, append-only audit rows | Public-facing ids — a monotonic integer leaks your row count |

### Sensible defaults

```prisma
model User {
  id        String    @id @default(cuid())
  email     String    @unique          // @unique already builds an index
  name      String
  role      Role      @default(USER)
  posts     Post[]
  createdAt DateTime  @default(now())
  updatedAt DateTime  @updatedAt
  deletedAt DateTime?

  @@index([createdAt])
  @@index([deletedAt, createdAt])      // composite: soft-delete filter + sort
}
```

Guidance that pays off later:

- Put an index on every foreign key and on every column that appears in a
  `WHERE` or `ORDER BY`. Missing FK indexes are the most common cause of a
  query that was fast in dev and crawls in prod.
- Do **not** add a second `@@index` on a field that already has `@unique` —
  the unique constraint is an index.
- If soft delete is even plausibly coming, declare `deletedAt DateTime?` on
  day one. Adding a nullable column later is cheap; retrofitting it onto a
  large live table under load is not.
- `@updatedAt` is maintained by the Prisma Client, not the database: raw
  SQL and any non-Prisma writer bypass it, and older client versions also
  skipped it on `updateMany` — see Traps.

## Reading Data

### `include` vs `select`

| | `include` | `select` |
|---|---|---|
| Returns | Every scalar column plus the listed relations | Only the fields you name |
| Reach for | You genuinely need most columns plus a relation | Hot paths, wide tables, anything user-facing |
| Cost | Can over-fetch on wide rows | Minimal payload |

```ts
// include: all columns of user + a trimmed relation
const withPosts = await prisma.user.findUnique({
  where: { id },
  include: { posts: { select: { id: true, title: true } } },
});

// select: an explicit allowlist, nothing else crosses the wire
const lean = await prisma.user.findUnique({
  where: { id },
  select: { id: true, email: true, name: true },
});
```

### Never hand a raw entity to a caller

A Prisma model is your storage shape, not your API contract. Returning it
directly leaks whatever columns exist today — password hashes, internal
flags, `deletedAt` — and re-leaks anything you add tomorrow.

```ts
// Leaks every column, including ones added after this line was written
return await prisma.user.findUniqueOrThrow({ where: { id } });

// Map to an explicit response shape — the allowlist is the contract
const u = await prisma.user.findUniqueOrThrow({ where: { id } });
return { id: u.id, name: u.name, email: u.email };
```

### The N+1 trap

Loading a relation inside a loop fires one query per parent row.

```ts
// One query, then one MORE query per user
const users = await prisma.user.findMany();
for (const u of users) {
  const posts = await prisma.post.findMany({ where: { authorId: u.id } });
}

// Fetch the relation in the same call
const users = await prisma.user.findMany({ include: { posts: true } });
```

On newer clients the `include` form may collapse to a single JOIN. Watch the
result-set size when each parent can own many children — the fix for N+1 can
trade query count for payload size.

## Cursor Pagination

Prefer cursor (keyset) pagination for feeds and any large or frequently
mutated dataset. Offset pagination (`skip`/`take`) is fine only when a user
must jump to an arbitrary page number, e.g. an admin table.

```ts
async function getPosts(cursor?: string, limit = 20) {
  const rows = await prisma.post.findMany({
    where: { published: true },
    orderBy: [
      { createdAt: "desc" },
      { id: "desc" },            // tiebreaker: stable order on equal timestamps
    ],
    take: limit + 1,             // one extra row is the "is there more?" probe
    ...(cursor && { cursor: { id: cursor }, skip: 1 }),
  });

  const hasNextPage = rows.length > limit;
  if (hasNextPage) rows.pop();   // drop the probe row before returning

  return {
    items: rows,
    nextCursor: hasNextPage ? rows[rows.length - 1].id : null,
  };
}
```

Two things make this correct: fetching `limit + 1` lets you detect a next
page without a second `count` query, and a unique secondary sort key (`id`)
keeps pagination stable when many rows share the same timestamp — without it,
rows can be skipped or repeated across pages.

## Transactions

Pick the form by the shape of the work, not by habit.

| Situation | Form |
|---|---|
| Independent writes with no data dependency between them | Array form — one round trip |
| A later step needs the result of an earlier one | Interactive callback |
| Any external call (email, HTTP, queue) is involved | No transaction — do it outside |

```ts
// Array form: batched atomically in a single round trip
const [user, post] = await prisma.$transaction([
  prisma.user.update({ where: { id }, data: { name } }),
  prisma.post.create({ data: { title, authorId: id } }),
]);

// Interactive form: use ONLY the tx client inside — never the outer prisma
const post = await prisma.$transaction(async (tx) => {
  const user = await tx.user.findUniqueOrThrow({ where: { id } });
  if (user.role !== "ADMIN") throw new Error("forbidden");
  return tx.post.create({ data: { title, authorId: user.id } });
});
```

Inside an interactive transaction, reaching for the outer `prisma` client
instead of `tx` runs that statement on a *different* connection, outside the
transaction — it will not roll back with the rest.

## The Client Is a Singleton

Every `PrismaClient` opens its own connection pool. Construct it once per
process and reuse it. Under a hot-reloading dev server (framework dev mode,
`nodemon`, `ts-node-dev`) module re-evaluation will spawn a new client on
every reload and exhaust the database's connection slots — pin it on
`globalThis`.

```ts
// lib/prisma.ts
import { PrismaClient } from "@prisma/client"; // or your generated client path

function createClient() {
  return new PrismaClient({
    log: process.env.NODE_ENV === "development" ? ["query", "error"] : ["error"],
    // If your install requires a driver adapter, pass `adapter: <pgAdapter>` here.
  });
}

const g = globalThis as unknown as { prisma?: PrismaClient };
export const prisma = g.prisma ?? createClient();
if (process.env.NODE_ENV !== "production") g.prisma = prisma;
```

If `new PrismaClient()` errors demanding an adapter, construct the adapter
from `DATABASE_URL` and pass it in; if it works bare, keep it bare. The
compiler is the source of truth for which your version needs.

## Serverless Connection Pooling

Each concurrent function invocation is its own process with its own pool. A
few hundred simultaneous invocations, each opening a default-sized pool, will
blow past the database's connection limit. Cap each instance to one
connection and route through an external pooler.

Put the parameters *inside* the URL — building the connection string by
concatenation breaks when it already carries query params like `?schema=`.

```bash
# One connection per instance, bounded wait for it
DATABASE_URL="postgresql://user:pass@host/db?connection_limit=1&pool_timeout=20"

# Through an external pooler (transaction-mode poolers need pgbouncer=true)
DATABASE_URL="postgresql://user:pass@host/db?pgbouncer=true&connection_limit=1"
```

## Error Handling

Catch Prisma's typed errors at the service boundary and translate them into
your own domain errors. Never surface a raw Prisma message to an API
consumer — it exposes schema internals and constraint names.

```ts
import { Prisma } from "@prisma/client"; // or your generated client path

try {
  await prisma.user.create({ data: { email } });
} catch (e) {
  if (e instanceof Prisma.PrismaClientKnownRequestError) {
    if (e.code === "P2002") throw new ConflictError("email already exists");
    if (e.code === "P2025") throw new NotFoundError("record not found");
    if (e.code === "P2003") throw new BadRequestError("referenced record missing");
  }
  throw e;
}
```

The codes worth memorising: `P2002` unique-constraint violation, `P2025`
record not found, `P2003` foreign-key violation, `P3006` migration failed
to apply cleanly to the shadow database.

## Traps (each has bitten someone in production)

### `updateMany` / `deleteMany` return a count, not rows

```ts
// result is { count: 2 } — result[0] is undefined, not a user
const result = await prisma.user.updateMany({
  where: { role: "GUEST" },
  data: { role: "USER" },
});

// If you need the affected rows: capture ids, mutate, then re-read
const ids = (
  await prisma.user.findMany({ where: { role: "GUEST" }, select: { id: true } })
).map((u) => u.id);
await prisma.user.updateMany({ where: { id: { in: ids } }, data: { role: "USER" } });
const updated = await prisma.user.findMany({ where: { id: { in: ids } } });
```

### The interactive transaction times out at ~5 seconds

The interactive `$transaction` callback holds a connection and has a default
timeout (about 5s). Put a network call inside it and it will throw
"Transaction already closed" while also pinning a connection the whole time.

```ts
// External call inside the transaction — blows the timeout
await prisma.$transaction(async (tx) => {
  const user = await tx.user.findUniqueOrThrow({ where: { id } });
  await sendWelcomeEmail(user.email);           // don't
  await tx.user.update({ where: { id }, data: { emailSent: true } });
});

// Keep external work outside the transaction boundary
const user = await prisma.user.findUniqueOrThrow({ where: { id } });
await sendWelcomeEmail(user.email);
await prisma.user.update({ where: { id }, data: { emailSent: true } });

// Raise the timeout only for genuine long-running bulk work
await prisma.$transaction(async (tx) => { /* ... */ }, { timeout: 30_000 });
```

### `migrate dev` can reset the database

On detecting schema drift, `migrate dev` may offer to reset the DB — which
drops every row. It is a *local, solo-developer* command.

```bash
npx prisma migrate dev --name add_column   # LOCAL only — can drop data on drift
npx prisma migrate deploy                   # CI/CD, staging, prod — never resets

# Inspect drift without touching anything
npx prisma migrate diff \
  --from-migrations ./prisma/migrations \
  --to-schema-datamodel ./prisma/schema.prisma \
  --shadow-database-url "$SHADOW_DATABASE_URL"
```

### Editing an applied migration breaks every downstream environment

Prisma checksums each migration file. Change one after it has been applied
anywhere and every environment that already ran the original fails with
`P3006` checksum mismatch. To change already-shipped SQL, add a *new*
migration.

### Breaking column changes need expand-and-contract

Adding `NOT NULL` to an existing column, or renaming one, in a single
migration will lock the table or drop data. Split it across deploys:

```bash
# 1. add the new nullable column
npx prisma migrate dev --name add_new_column      # author locally
npx prisma migrate deploy                          # ship
```
```ts
// 2. backfill in a job/script (not an ad-hoc shell one-liner)
await prisma.user.updateMany({ data: { newColumn: derivedValue } });
```
```bash
# 3. only now tighten the constraint
npx prisma migrate dev --name make_new_column_required
npx prisma migrate deploy
```

### `@updatedAt` depends on the writer

`@updatedAt` is client-side: raw SQL (`$executeRaw`) and any non-Prisma
writer always bypass it, and older client versions skipped it on
`updateMany` (verify against your pinned version). When in doubt, set it
explicitly — redundant on new clients, harmless everywhere.

```ts
await prisma.post.updateMany({ where: { authorId }, data: { published: true } }); // updatedAt frozen
await prisma.post.updateMany({
  where: { authorId },
  data: { published: true, updatedAt: new Date() },
});
```

### Soft delete leaks through `findUniqueOrThrow`

`findUniqueOrThrow` throws `P2025` only when the row is absent from the
database. A soft-deleted row still exists, so it comes back with no error.
On Prisma < 5.0 you also cannot simply add `deletedAt: null` to the `where` —
`findUnique*` required a genuinely unique key (5.0's extendedWhereUnique GA
lifted that restriction, so the second line below compiles there). Either
way, `findFirstOrThrow` accepts arbitrary filters and works everywhere.

```ts
const user = await prisma.user.findUniqueOrThrow({ where: { id } });               // returns deleted rows
const user2 = await prisma.user.findUniqueOrThrow({ where: { id, deletedAt: null } }); // type error < 5.0
const user3 = await prisma.user.findFirstOrThrow({ where: { id, deletedAt: null } });  // correct
```

Filter soft deletes explicitly at each call site. Client middleware/extensions
*can* inject the filter globally, but hiding it makes "where did this row go?"
debugging much harder — prefer the explicit `where: { deletedAt: null }`.

### `deleteMany` with no `where` empties the table

```ts
await prisma.post.deleteMany();                          // wipes every post, silently
await prisma.post.deleteMany({ where: { authorId } });   // scoped
```

## Best Practices

| Rule | Why |
|---|---|
| `migrate deploy` in CI/CD; `migrate dev` local only | `migrate dev` can reset on drift |
| Map entities to explicit response shapes | Storage shape is not an API contract |
| Translate `PrismaClientKnownRequestError` at the boundary | Hide constraint internals; return domain errors |
| Prefer `*OrThrow`, and `findFirstOrThrow` when filtering non-unique fields | Automatic `P2025`; survives soft-delete filters |
| `connection_limit=1` + external pooler in serverless | Prevents connection exhaustion |
| Always pass `where` to `deleteMany`/`updateMany` | Prevents whole-table mutations |
| Set `updatedAt: new Date()` in bulk writes | `@updatedAt` skips them |
| Index every FK and every `WHERE`/`ORDER BY` column | The prod-slowness class of bug |

## Related Skills

- `postgres-patterns` — index internals, `EXPLAIN`, connection tuning at the DB layer.
- `database-migrations` — sequencing zero-downtime schema changes.
- `backend-patterns` — service-layer and API design around the ORM.

## Changelog

- 1.0.0 — Initial clean-room authoring. Covers schema/index design, ID
  strategy, read patterns and DTO mapping, cursor pagination, transaction
  form selection, the client singleton, serverless pooling, typed error
  translation, and the eight production traps (bulk-write count returns,
  interactive-transaction timeout, `migrate dev` reset, migration checksum,
  expand-and-contract, `@updatedAt` on bulk writes, soft-delete leakage
  through `*OrThrow`, unscoped `deleteMany`).
Skill-Import-Attestation: reviewed-by=AE9B236FDAF0462874060C6BCFCFACF00335DC74; sha256=8849c85ad2dd728af1dc69dcd7bfb0905252608382bca5c2aa959ceeaee80018
