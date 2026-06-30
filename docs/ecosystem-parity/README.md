# Ecosystem Parity — Adopter Guides

PLAN-046 (Session 49 P04 closure) ships **5 clusters** that import
token-economy patterns from the wider Claude Code ecosystem into
this framework's governance surface.

Each cluster ships:

- A **staged scaffold** (runnable stdlib code; non-canonical path).
- A **spec** in `.claude/plans/PLAN-046/staged-code/cluster-X.Y-*.md`
  (architecture + clean-room declaration + promotion runbook).
- An **adopter guide** (this directory) explaining when, why, and
  how to activate.
- A **test suite** (all green on stock Python 3.9+).

Nothing in this directory auto-activates. Adopters opt in per
cluster.

## Decision matrix — when to activate which cluster

| Cluster | Symptom that motivates it | Install | Typical savings |
|---|---|---|---|
| **1.1 Brotli** | Large textual context cache (> 10 KiB / entry) | zero (zlib) OR `pip install brotli` | 30-50 % cache tokens |
| **1.2 Context-mode** | Long sessions losing hot-path detail despite Manifest | none (docs-only this wave) | quality, not raw cost |
| **1.3 Bayesian memory** | > 10 memory topic files, hard to prune | zero (stdlib) | context clarity + prune guidance |
| **1.4 Code-nav** | Sub-agents re-`grep`-ing same symbols | zero (stdlib) or `pip install tree-sitter` | 20-40 % fewer Read tool calls |
| **1.5 rtk terminal** | Sub-agents see big `ls -l`/`grep -r` bash outputs | zero (stdlib) | 70-90 % tool-result tokens |

## Cluster-by-cluster

### 1.1 — [Brotli context compression](cluster-1.1-brotli.md)

Context-block compression before cache write. Stdlib `zlib` ships
always; `brotli` is an adopter-opt-in upgrade. Scaffold:
`.claude/plans/PLAN-046/staged-code/brotli_passthrough.py`.

### 1.2 — [Context-mode orthogonal to Manifest](cluster-1.2-context-mode.md)

ADR-066 classification fix: context-mode (literal slice preservation)
is orthogonal to Manifest (semantic compression). Docs-only this
wave; implementation in a future PLAN-046 sub-wave.

### 1.3 — [Bayesian memory prioritization](cluster-1.3-bayesian-memory.md)

CLI that scores every auto-memory topic by Bayesian posterior mean
over (recency, access, centrality). Useful for prune decisions and
top-N context bootstrap. Shipped at
`.claude/scripts/memory-prioritize.py`; stdlib-only.

### 1.4 — [Code-nav MCP sidecar](cluster-1.4-code-nav.md)

Semantic code graph for sub-agent navigation. Python API works
today; live MCP serving is adopter-owned. Scaffold at
`.claude/scripts/mcp/code_nav_bridge.py`. Tree-sitter upgrade is
opt-in.

### 1.5 — [Terminal output compression](cluster-1.5-rtk-terminal.md)

ANSI strip + whitespace normalize + repeated-prefix collapse for
Bash tool-result captures before they feed the LLM. Stdlib; zero
install. Scaffold at
`.claude/plans/PLAN-046/staged-code/terminal_compress.py`.

## Activation order for a new adopter

If you're starting fresh and want the quickest wins:

1. **1.5** — terminal compression. Zero install, big savings on
   research flows, zero risk.
2. **1.3** — memory prioritization. Zero install, quickly surfaces
   the dead topics bloating your context.
3. **1.1** — Brotli. Start with `CEO_CONTEXT_COMPRESS=zlib` (no
   install). Upgrade to brotli only if you measure meaningful extra
   savings.
4. **1.4** — code-nav. Useful once your codebase is > 100 source
   files or sub-agents start re-grepping frequently.
5. **1.2** — context-mode. Wait for the implementation wave unless
   you want to roll your own wrapper.

## Promotion path

Clusters 1.1 and 1.5 live at non-canonical staged paths. Full
integration requires promoting them into `.claude/hooks/_lib/` under
an Owner-signed canonical-edit sentinel round. Each cluster's spec
documents the exact runbook. Clusters 1.3, 1.4, and 1.2 do not
require promotion (either they already live at non-canonical
runnable paths, or this wave is docs-only).

## Clean-room attribution

| Cluster | Inspired by | Relation |
|---|---|---|
| 1.1 | ooples ecosystem work | concept only |
| 1.2 | awesome-context threads | classification observation |
| 1.3 | token-savior Bayesian memory | concept only |
| 1.4 | code-review-graph + token-savior tree-sitter | concept + interface pattern |
| 1.5 | rtk terminal tooling | concept only |

No code is lifted from any upstream repo. Each cluster's spec
carries a dedicated "Clean-room declaration" section listing the
public-domain algorithms used (Beta posterior, LCP walk, ANSI-strip
regex, etc.).

## Dependencies between clusters

- **1.1 + 1.5** can stack: terminal output is compressed (1.5) and
  then cached-compressed (1.1) independently. No interaction.
- **1.2 + Manifest (ADR-062)** can stack per the core decision; kill
  either if context budget explodes.
- **1.3** is read-only; no other cluster depends on it.
- **1.4** stands alone; optional tree-sitter upgrade doesn't affect
  other clusters.

## Test suite at a glance

Across the 5 clusters this wave added **60 tests**, all stdlib, all
green on Python 3.9+:

| Cluster | Tests | Runtime |
|---|---|---|
| 1.1 Brotli | 12 (10 runnable + 2 `skipUnless(brotli)`) | ~0.04 s |
| 1.2 Context-mode | 0 (docs-only this wave) | — |
| 1.3 Bayesian memory | 15 | ~0.15 s |
| 1.4 Code-nav | 20 | ~0.08 s |
| 1.5 rtk terminal | 15 | ~0.04 s |
| **Total** | **62** | **< 0.5 s** |

## Related

- `.claude/plans/PLAN-046-ecosystem-parity-sota-closure-v2.md` — the
  plan
- `.claude/adr/ADR-066-context-mode-orthogonal-to-manifest.md` — the
  classification ADR
- `.claude/adr/ADR-062-*.md` — Manifest (LightRAG sidecar)
