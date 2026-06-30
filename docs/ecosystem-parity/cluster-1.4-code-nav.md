# Ecosystem Parity · Cluster 1.4 — Code-nav MCP sidecar

**Status:** scaffold shipped (Session 49 P04). Live MCP wiring is
adopter-owned. Inspiration: code-review-graph + token-savior
tree-sitter work (clean-room).

## When to activate

Turn this on if your sub-agents regularly:

- Hunt for function/class definitions across a large codebase
  (hundreds of files).
- Re-`grep` the same symbol dozens of times per session.
- Need a per-file symbol list (e.g. "what's in this 800-line
  module?").

Typical wins: 20-40 % fewer `Read`/`Grep` tool turns on research-
heavy flows, because the first query pre-scans the tree and caches
symbols.

**Skip** if:

- Your codebase is small (< 100 source files).
- Sub-agents rarely navigate by symbol name.
- You have strong IDE-backed navigation already and agents don't
  need to mirror that.

## Activation mode A — Python API (works today)

```python
from pathlib import Path
import importlib.util

spec = importlib.util.spec_from_file_location(
    "code_nav_bridge",
    ".claude/scripts/mcp/code_nav_bridge.py",
)
mod = importlib.util.module_from_spec(spec)
spec.loader.exec_module(mod)

bridge = mod.CodeNavBridge(Path("."), backend="stdlib")

# Find where a symbol is defined:
locs = bridge.find_definition("my_function")
for loc in locs:
    print(f"{loc.path}:{loc.line}")

# Find all references to a symbol:
refs = bridge.find_references("my_function")

# List all symbols in one file:
syms = bridge.list_symbols("src/module.py")
```

All methods return `[]` on error (fail-open). No exceptions.

## Activation mode B — Live MCP sidecar (adopter-owned)

The scaffold contains a `serve_mcp()` stub. To wire this up as a
real MCP sidecar:

1. **Implement JSON-RPC over stdio** in `serve_mcp()`. Reference
   pattern: `.claude/hooks/_lib/rag_bridge.py` (from ADR-062
   LightRAG sidecar).
2. **Add to your MCP config** (`~/.config/claude/mcp.json`):
   ```json
   {
     "sidecars": {
       "code_nav": {
         "command": "python3",
         "args": [
           ".claude/scripts/mcp/code_nav_bridge.py",
           "--serve"
         ]
       }
     }
   }
   ```
3. **Test in a fresh session.** Sub-agents gain `code_nav__*` tool
   calls.

## Tree-sitter upgrade (optional)

```bash
pip install tree-sitter
pip install tree-sitter-python tree-sitter-typescript
```

Then construct the bridge with `backend="tree_sitter"`:

```python
bridge = mod.CodeNavBridge(Path("."), backend="tree_sitter")
```

Today the stub falls back to the regex scan. Adopter implements
the AST walk in `_scan_tree_sitter` — the interface is already
stable.

## Supported languages (stdlib backend)

| Language | Definition kinds captured | Notes |
|---|---|---|
| Python | `def`, `async def`, `class` | top-level + methods |
| TypeScript | `function`, `class`, `interface`, `type`, `const`, `let`, `var` | `export`-prefixed forms included |
| JavaScript | `function`, `class`, `const`, `let`, `var` | same regex as TS |

Other languages fall through as empty — add more regexes in
`_PY_DEF_RE` / `_TS_DEF_RE` style to extend.

## Ignored paths

The stdlib walker skips:

- `node_modules/`
- `.venv/` / `venv/`
- `__pycache__/`
- `dist/` / `build/`

To add more, patch `_iter_source_files` in the scaffold (trivial).

## What's in the scaffold

- `.claude/scripts/mcp/code_nav_bridge.py` — bridge + stdlib +
  tree-sitter stub + MCP `serve_mcp()` notice.
- `.claude/scripts/tests/test_code_nav_bridge.py` — 20 tests.
- `.claude/plans/PLAN-046/staged-code/cluster-1.4-code-nav-sidecar-spec.md`
  — architecture + promotion runbook.

## Rollback

- **Python API mode:** stop calling the bridge. Nothing is auto-run.
- **Live MCP mode:** remove the sidecar entry from your MCP config.

## Clean-room note

Inspiration comes from code-review-graph's semantic-graph approach
and token-savior's tree-sitter usage. Zero code is lifted. The
regex families are public programming-language keyword catalogs; the
interface is standard MCP.
