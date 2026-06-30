# SPEC v1 — skill-index.schema

> **Spec version:** 1.0.0-rc.1
> **Status:** normative
> **Sprint:** 11 (PLAN-011 Phase 2)
> **Related ADR:** ADR-029 (lexical tf-idf retrieval)

This document is the **public contract** for the lexical skill-retrieval
index. A third-party tool can build a compatible index, or read an
index produced by this framework, by following this schema.

## Path convention

The index lives in a single sqlite file outside the repository, per
ADR-001 (runtime state directory):

```
${CEO_SKILL_INDEX_PATH:-$HOME/.claude/projects/${CEO_PROJECT_NAME:-ceo-orchestration}/skill-index.sqlite}
```

Unlike the plan-scoped state store (`_lib.state_store`), the skill
index is **global** — it indexes repo-level skills regardless of the
currently active plan. A separate sqlite file keeps the index
lifecycle independent from any specific plan.

## File permissions

The index file MUST be created with mode `0o600` (owner-read/write only).
Parent directory MUST exist with mode `0o700` or tighter.

## Sqlite schema

### Table `skills`

```sql
CREATE TABLE skills (
    slug        TEXT PRIMARY KEY,   -- collision-resolved id; "tier:name" when raw_slug collides
    raw_slug    TEXT NOT NULL,      -- the directory name as-is (may collide across tiers)
    tier        TEXT NOT NULL,      -- "core" | "frontend" | "domain:<name>"
    path        TEXT NOT NULL,      -- repo-relative path to SKILL.md
    mtime       REAL NOT NULL,      -- float epoch seconds, os.stat.st_mtime
    content_sha TEXT NOT NULL,      -- sha256 hex digest of the indexed text
    vector_json TEXT NOT NULL       -- JSON object: {term: weight, ...}
);
```

### Table `idf`

```sql
CREATE TABLE idf (
    term       TEXT PRIMARY KEY,
    idf_value  REAL NOT NULL
);
```

### Table `meta`

```sql
CREATE TABLE meta (
    k TEXT PRIMARY KEY,
    v TEXT NOT NULL
);
```

**Required keys:**

| Key | Value |
|---|---|
| `total_docs` | decimal string, N documents in the corpus |
| `built_at`   | decimal string, epoch seconds of build time |
| `spec_version` | string matching this SPEC version (`"1.0.0"` for v1.0.0-rc.1) |

Additional keys MAY be present; consumers MUST ignore unknown keys.

## Pragmas

The builder writes with `PRAGMA journal_mode=WAL`. Consumers MUST NOT
depend on a specific pragma configuration; query-only access with
default pragmas MUST succeed.

## Indexed text

For each `SKILL.md` under `.claude/skills/**/SKILL.md`, the indexed
text is the concatenation of:

1. The `name:` frontmatter field (if present).
2. The `description:` frontmatter field (if present).
3. The first `BODY_EXTRACT_CHARS = 2000` characters of the body
   (after the closing `---` of the frontmatter).

Joined with blank lines. Empty / missing frontmatter fields are omitted.

## Tokenization

- Unicode-aware: regex `[A-Za-z0-9]+` matches tokens.
- Lowercased.
- Minimum token length: 2 characters.
- Stopword filter: a small inline list of ≤50 common English stopwords
  (see `_lib/embeddings.py`). Compliant implementations MAY use a
  different stopword list, but they SHOULD document it; the reference
  implementation's list is authoritative for round-trip reproducibility.

## Term frequency (sublinear scaling)

```
sublinear_tf(tf) = 1 + ln(tf)       for tf >= 1
                 = (undefined)       for tf == 0 (omit term)
```

Natural log (`ln`, base e). Terms absent from a document contribute 0.

## Inverse document frequency (smoothed)

```
idf(t) = ln((N + 1) / (df(t) + 1)) + 1
```

Where N = total number of documents and df(t) = number of documents
containing term t. Smoothing matches the scikit-learn
`smooth_idf=True` convention. Terms unseen at index-build time MAY
be assigned the "unseen-term" smoothed idf at query time:

```
unseen_idf = ln((N + 1) / 1) + 1
```

## tf-idf vector

Per-document vector: `{term: sublinear_tf(tf_doc(term)) * idf(term)}`.
Stored as compact JSON in `skills.vector_json` (sorted keys, no
whitespace). Terms with zero weight MUST be omitted.

## Cosine similarity

```
cos(a, b) = dot(a, b) / (norm(a) * norm(b))
```

Where `dot(a, b) = sum(a[t] * b[t] for t in a & b)` and
`norm(v) = sqrt(sum(v[t]^2 for t in v))`. Return 0.0 when either
norm is 0.

Guaranteed range `[0.0, 1.0]` for non-negative weight vectors
(which lexical tf-idf always produces).

## Feature flag — `CEO_REAL_EMBEDDINGS`

When unset or not `"1"`: the reference implementation uses lexical
tf-idf per this schema.

When `"1"` AND a real embedding provider is reachable: the
implementation MAY substitute a different vector encoding. Sprint 11
does NOT ship a provider; the flag is reserved. Consumers MUST NOT
assume the index contents were produced by lexical tf-idf; they can
detect this via future `meta.embedder_kind` key (reserved, not shipped
in v1.0.0-rc.1).

## Feature flag — `CEO_SOTA_DISABLE`

When `"1"`: the index builder exits 0 as a no-op, and the retrieval
CLI falls back to a static SKILL-MAP keyword-match against `team.md`.
No sqlite read is performed. Compliant implementations SHOULD support
this flag or document their disable path.

## Staleness semantics

An index is **stale** for skill S if the live filesystem mtime of
`S/SKILL.md` exceeds `skills.mtime + 0.001` (1 ms slack). The CLI
emits a WARNING line per stale skill to stderr when `--check-stale`
is passed; exit code is 0 (advisory).

Compliant implementations SHOULD provide a stale-check path.

## Uncommitted-changes advisory

For reproducibility, the index builder scans `git status --porcelain
.claude/skills/`. When non-empty and `--strict` is passed, the builder
exits 3 without writing. Non-strict mode writes the index with a
WARNING to stderr. Consumers relying on commit-identity-level index
reproducibility MUST use `--strict` in CI.

## Version history

| SPEC version | Notes |
|---|---|
| 1.0.0-rc.1 | Initial formal contract for Sprint 11 Phase 2 (PLAN-011). Lexical tf-idf baseline with `CEO_REAL_EMBEDDINGS` reserved. |

## References

- ADR-029 — Lexical tf-idf retrieval (decision record)
- ADR-001 — Runtime state directory (path convention)
- ADR-027 — Unified agent state backend (why the skill index is NOT
  on state_store: index is repo-global, not plan-scoped)
- `.claude/benchmarks/retrieval-judgment-set.yaml` — held-out gold
  pairs for recall@5 gate
- `.claude/benchmarks/tests/test_retrieval_recall_gate.py` — the H4
  gate test
