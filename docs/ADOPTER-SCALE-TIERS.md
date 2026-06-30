# Adopter Scale Tiers

> **Audience:** anyone installing ceo-orchestration in a target
> repo. Determines which features to enable based on repo size +
> team shape.
> **Companion:** [`CAG-VS-RAG.md`](./CAG-VS-RAG.md), [`HYDE-RECIPE.md`](./HYDE-RECIPE.md), [`INSTALL-RAG.md`](./INSTALL-RAG.md).
> **PLAN:** PLAN-062 Phase 5.

## TL;DR

The framework has 3 adopter tiers based on **repo size**:

| Tier | Repo size | Sidecar | HyDE | Custom skills | Skill-index |
|---|---|---|---|---|---|
| **Tier 0 — Vibecoder solo** | < 50k LoC | skip | skip | 0-3 | skip |
| **Tier 1 — Lightweight enterprise** | 50k - 1M LoC | **install** | optional | 5-15 | optional |
| **Tier 2 — Heavy enterprise** | > 1M LoC | **install** | recommended | 15+ | recommended |

If you don't know your tier, run:

```bash
bash scripts/measure-repo-size.sh
```

(See §3 for the script source if you want to inspect first.)

---

## 1. Tier definitions

### 1.1 Tier 0 — Vibecoder solo

**Profile:** one developer, side project or early-stage startup,
repo under 50k LoC. Single technical voice. Queries are direct.
"How do I X" rarely; usually "rewrite X to do Y."

**Framework subset:**

- Core only (`bash scripts/install.sh` from upstream)
- No sidecar (overhead > benefit at this scale)
- No HyDE (queries already technical)
- 0-3 custom domain skills (typically zero — core skills cover it)
- No skill-index tf-idf (42 core skills + your 0-3 fit inline)

**Why this is the framework's primary design target:**

ADR-096 (vibecoder-only-by-design) ratified the framework's tese
that the core stays minimal. Tier 0 adopters get the full power of
CEO orchestration + Format B SKILL REFERENCE + cache discipline
without operational overhead.

**What you skip:**

- LightRAG sidecar venv install (~2 GiB disk + 4 GiB RAM)
- bge-reranker / cohere rerank cost
- HyDE recipe Claude Haiku calls
- Custom skill governance ceremony

**Resource footprint:**

| Resource | Tier 0 |
|---|---|
| Disk | ~50 MB (framework only) |
| RAM | < 100 MB (no sidecar) |
| Per-session cost | dominated by Anthropic API only |
| Maintenance | docs + skills updated per upstream |

### 1.2 Tier 1 — Lightweight enterprise

**Profile:** small-to-mid team (3-15 devs), production codebase,
50k-1M LoC. Multi-skill team (engineering + product + design).
Queries vary from technical ("`ProcessOrder.Execute`") to
informal ("como funciona o settlement?"). Domain expertise exists
in the team but isn't always shared widely.

**Real example:** A fintech engine + frontend at ~250k+300k LoC =
~550k LoC total. This tier.

**Framework subset:**

- Core (`bash scripts/install.sh` from upstream)
- **Sidecar opt-in** (`bash .claude/rag/install-sidecar.sh`) —
  recommended for cross-file reasoning ("how does kyc integrate
  with settlement?")
- **HyDE optional** — useful when queries come from non-engineers
  or are casual/cross-lingual; skip if dev team is small + senior
- 5-15 custom domain skills (e.g., for fintech: `double-entry-rules`,
  `clearing-protocols`, `kyc-policies`)
- Skill-index tf-idf optional (helps when custom skills > 30)

**What changes vs Tier 0:**

- Install sidecar venv (Python 3.10+, ~2 GiB disk)
- Index repo (~5-30 min depending on LoC)
- Optionally wire HyDE pre-spawn hook (see [`HYDE-RECIPE.md`](./HYDE-RECIPE.md))
- Author + maintain custom skills (5-15 SKILL.md files)
- Periodic review (quarterly) of custom skill freshness

**Resource footprint:**

| Resource | Tier 1 |
|---|---|
| Disk | ~50 MB (framework) + ~2 GiB (sidecar venv + embeddings) |
| RAM | ~4 GiB (sidecar) |
| Per-session cost | API + ~$0.0001/query for HyDE if enabled |
| Maintenance | docs + skills updated per upstream + custom skill quarterly review |

### 1.3 Tier 2 — Heavy enterprise

**Profile:** large org (50+ devs), monorepo or complex multi-repo,
> 1M LoC. Multiple teams, multiple domains, regulatory or
compliance constraints. Multi-tenant deployment likely.

**Framework subset:**

- Core (`bash scripts/install.sh` from upstream)
- **Sidecar mandatory** (single-tenant install per environment;
  multi-tenant uses `CEO_PROJECT_STATE_DIR` isolation)
- **HyDE recommended** — large surface, multi-skill teams, varied
  vocabulary across domains
- 15+ custom skills with formal governance (per-domain ownership)
- Skill-index tf-idf recommended (helps when custom skills > 30)
- Custom retrieval pipeline (vector DB choice — chroma, pgvector,
  weaviate, etc.) often replaces or augments LightRAG

**What changes vs Tier 1:**

- Sidecar is hard requirement (KB doesn't fit inline at all)
- HyDE is operationally cost-effective at high QPS
- Custom skill governance: 1-2 owners per skill, periodic audit
- Per-tenant CEO_PROJECT_STATE_DIR for multi-tenant
- Likely beyond ceo-orchestration's primary target — consider the
  framework as a starting point, build org-specific extensions

**Honest framing:**

Ceo-orchestration is **not optimized for Tier 2**. ADR-096
explicitly limits scope to vibecoder-solo design. Tier 2 adopters
should:

1. Use ceo-orchestration as governance + spawn protocol foundation
2. Build org-specific extensions for what the core doesn't cover
3. Contribute back domain-skills under `domains/<name>/` if useful
   to others

The framework gives you the skeleton + cache discipline + spawn
governance. You bring everything else.

---

## 2. Decision tree

```
                          ┌──────────────────┐
                          │ Repo size?       │
                          └────────┬─────────┘
                                   │
        ┌──────────────────────────┼──────────────────────────┐
        │                          │                          │
        ▼                          ▼                          ▼
   < 50k LoC                  50k - 1M LoC               > 1M LoC
   ┌────────┐                 ┌────────────┐             ┌────────┐
   │ Tier 0 │                 │  Tier 1    │             │ Tier 2 │
   └────┬───┘                 └─────┬──────┘             └────┬───┘
        │                           │                         │
        ▼                           ▼                         ▼
   Core only                  Core + sidecar           Core + sidecar
   ─────────                  ──────────────           + HyDE + custom
   Skip sidecar               Maybe HyDE if            ───────────────
   Skip HyDE                  multi-skill team         Build extensions
   Skip skill-index           5-15 custom skills       15+ custom skills
                              Skill-index optional     Skill-index recmd

                          ┌──────────────────┐
                          │ Team shape?      │
                          └────────┬─────────┘
                                   │
            ┌──────────────────────┼──────────────────────┐
            ▼                      ▼                      ▼
       Solo expert         Multi-skill team         Multiple domain
       ────────────        (eng + prod + design)    teams
       No HyDE             Add HyDE                 Add HyDE +
                                                    org-specific
                                                    skill governance
```

---

## 3. How to know your tier

Run the helper script (shipped with PLAN-062 Phase 5):

```bash
bash scripts/measure-repo-size.sh
```

Output:

```
=== ceo-orchestration scale tier check ===
Repo: /path/to/your/repo

Counted: .py .ts .tsx .js .jsx .go .rs .java .kt .swift
         .rb .php .cs .cpp .c .h .hpp .md .yaml .yml .toml
Excluded: .git/ node_modules/ vendor/ .venv/ venv/ dist/ build/
          __pycache__/ .pytest_cache/ target/ out/

LoC (best effort, includes blanks/comments): 542,318
Estimated tokens (~10 tok/LoC):              ~5,423,180

→ Tier: 1 (Lightweight Enterprise)
→ Recommendation: Install LightRAG sidecar. HyDE optional (yes if multi-skill team).

See docs/ADOPTER-SCALE-TIERS.md for the full per-tier checklist.
```

The script is intentionally simple stdlib bash — works on any
POSIX system, no Python required, no external tools.

If you want to inspect first:

```bash
cat scripts/measure-repo-size.sh
```

(~30 LoC.)

---

## 4. What changes per tier (concrete checklist)

### Tier 0 install

```bash
cd /path/to/your/repo
bash /path/to/ceo-orchestration/scripts/install.sh
# That's it. Open with Claude Code.
```

### Tier 1 install (lightweight enterprise shape)

```bash
cd /path/to/your/repo
bash /path/to/ceo-orchestration/scripts/install.sh

# Add sidecar
bash .claude/rag/install-sidecar.sh
# (~2-5 min install + ~5-30 min initial index depending on LoC)

# Optional: wire HyDE pre-spawn hook
# Copy examples/hyde-retrieve.py into your project + customize
cp /path/to/ceo-orchestration/examples/hyde-retrieve.py ./scripts/
# Edit your spawn wrapper to call it pre-injection (see HYDE-RECIPE.md §8)

# Author custom skills as needed
mkdir -p .claude/skills/domains/<your-domain>/skills/
# Each skill follows .claude/skills/core/<core-skill>/SKILL.md template
```

### Tier 2 install

```bash
# Tier 1 install +
# - per-environment sidecar (dev/staging/prod each with own venv)
# - per-tenant CEO_PROJECT_STATE_DIR if multi-tenant
# - custom retrieval pipeline if LightRAG insufficient
# - custom skill governance docs in your repo
```

This last one is org-specific — ceo-orchestration documents the
core; your org documents the extensions.

---

## 5. Cross-tier topics

### 5.1 Cache discipline applies to ALL tiers

CAG-PATTERNS.md cache discipline (don't edit Gate-1 mid-session)
is universal. Doesn't matter if you're Tier 0, 1, or 2 — you save
~88% on cold prefix cost by respecting it.

### 5.2 Format B SKILL REFERENCE applies to ALL tiers

Same. Cache-friendly spawn prompts work regardless of repo size.

### 5.3 Audit log applies to ALL tiers

`audit-log.jsonl` HMAC chain works the same on a 50k LoC repo and
a 5M LoC repo. Hooks fire identically. Governance is universal.

### 5.4 What scales with tier

- Custom skills count (more domain expertise needed)
- Retrieval infrastructure (none → sidecar → custom pipeline)
- HyDE / re-rank tooling (none → optional → operational)
- Per-tenant isolation (none → none → required)
- Org-specific extensions (none → minimal → substantial)

---

## 6. Tier transitions

Repos grow. You might start Tier 0 and hit Tier 1 thresholds in
6-12 months. Migration:

### Tier 0 → Tier 1

Triggered by: repo size > 50k LoC OR team grows past solo dev.

Steps:

1. Run `bash scripts/measure-repo-size.sh` to confirm threshold
2. Install sidecar (`bash .claude/rag/install-sidecar.sh`)
3. Re-index repo (~5-30 min)
4. Decide on HyDE based on team shape
5. Begin authoring custom skills as domain expertise emerges

No breaking changes. Sidecar is additive. Existing CEO sessions
keep working.

### Tier 1 → Tier 2

Triggered by: repo > 1M LoC OR multi-team org.

Steps:

1. Reassess if ceo-orchestration core is still right fit (it might
   be; it might not)
2. If yes: build org-specific extensions on top of the core
3. If no: extract the patterns you want (cache discipline, Format
   B, governance hooks) and integrate into your own platform

This is where the framework's vibecoder-only-by-design (ADR-096)
becomes relevant — at Tier 2, you've outgrown the design center.
The core still gives you a working foundation, but you own the
extensions.

---

## 7. Anti-patterns

| Anti-pattern | Why it fails |
|---|---|
| Install sidecar at Tier 0 | Wasted 2 GiB disk + 4 GiB RAM for ROI < zero |
| Skip sidecar at Tier 2 | KB doesn't fit inline; CEO sessions miss critical context |
| Use HyDE at Tier 0 | 2× cost, 500ms latency, gain ≈ 0 on direct queries |
| Skip cache discipline at any tier | -88% cold prefix cost loss; pure waste |
| Ignore tier and apply enterprise patterns at Tier 0 | Operational overhead crushes solo dev velocity |
| Try to make Tier 2 fit ceo-orchestration core | Outgrew the design center; build extensions |

---

## 8. Further reading

- **CAG patterns:** [`CAG-PATTERNS.md`](./CAG-PATTERNS.md) — cache
  discipline applies to all tiers.
- **CAG vs RAG:** [`CAG-VS-RAG.md`](./CAG-VS-RAG.md) — when retrieval
  beats inline; relevant Tier 1+.
- **HyDE recipe:** [`HYDE-RECIPE.md`](./HYDE-RECIPE.md) — applies
  Tier 1+.
- **Sidecar install:** [`INSTALL-RAG.md`](./INSTALL-RAG.md) —
  applies Tier 1+.
- **ADR-096:** vibecoder-only-by-design — explains why Tier 2 is
  outside the design center.
- **ADR-062:** rationale for opt-in LightRAG sidecar (Tier 1+ enabler).
- **ADR-002:** stdlib-only invariant for the core (preserved
  across all tiers).
