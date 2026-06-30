# INSTALL-RAG — LightRAG sidecar opt-in

> **Version:** framework v1.6.0+ / PLAN-041 / ADR-062
> **Scope:** adopters running codebases at 500 k LoC scale who want
> retrieval-augmented context beyond Claude's 1 M context window.
> **Not needed if:** your repo is under ~50 k LoC — grep + direct
> Read is sufficient, and this feature adds ~2 GiB install + 2 GiB
> RAM overhead for no measurable gain.

## What this is

A LightRAG (HKUDS EMNLP 2025, MIT) sidecar process — separate from
the framework core — that indexes your repo's symbols + prose and
exposes 3 MCP tools (`rag.search`, `rag.timeline`,
`rag.get_observations`) over a local Unix socket.

The framework's stdlib bridge (`.claude/hooks/_lib/rag_bridge.py`)
talks MCP to the sidecar. If the sidecar is down, the bridge returns
`None` and CEO orchestration falls back to grep. Zero disruption.

## What this is NOT

- Not embedded in the framework core (ADR-062: preserves stdlib-only
  invariant ADR-002)
- Not auto-started at session boot (explicit `ceo-rag start` required)
- Not a trust boundary — it's a local convenience (see Security below)
- Not called from PreToolUse / PostToolUse hooks (hook SLO p99 <100ms
  incompatible with bridge timeout 5s; Round 1 debate consensus A3)

## Prerequisites

- Python 3.10+ available (the framework core runs on 3.9+; the sidecar
  venv requires 3.10+)
- 2.5 GiB free disk for venv + embedding model
- 4 GiB free RAM (headroom for sidecar at 500 k LoC; comfortable for
  smaller repos)
- macOS / Linux (Windows / WSL: TCP-token fallback, see Security)
- NOT root — `install-sidecar.sh` refuses to run as EUID 0

## Install

```bash
cd <your-project>
bash .claude/rag/install-sidecar.sh --status    # diagnose
bash .claude/rag/install-sidecar.sh             # actual install
```

**First run will fail intentionally.** The bundled
`.claude/rag/requirements.lock` ships as a PLACEHOLDER — adopters MUST
regenerate it against their trusted PyPI mirror before the install
script proceeds:

```bash
# Pin LightRAG to the version you audited
echo "lightrag==<audited-version>" > /tmp/reqs.in
pip install pip-tools
pip-compile --generate-hashes \
            --output-file .claude/rag/requirements.lock \
            /tmp/reqs.in
# Commit the generated lockfile via a branch-protected PR
git add .claude/rag/requirements.lock
git commit -m "security(rag): pin LightRAG + hashes"
```

Similarly `.claude/rag/models.manifest.json` ships with
`PLACEHOLDER_SHA256`. Either:

(a) Regenerate by downloading the embedding model from your trusted
mirror + committing the SHA256, OR

(b) Proceed with two-factor ack:
```bash
export CEO_RAG_UNVERIFIED_MODEL_ACK=I-ACCEPT-MODEL-INTEGRITY-RISK
bash .claude/rag/install-sidecar.sh --skip-model-verify
```

Option (a) is strongly recommended for production adopters.

## Enable + first index

```bash
# 1. Launch sidecar
ceo-rag start                   # daemonized; pidfile in ~/.ceo-orchestration/rag/

# 2. Build initial index (500k LoC ≈ 20-40 min depending on LLM tier)
ceo-rag index                   # full index on first run

# 3. Verify
ceo-rag status                  # prints sidecar up, last-indexed-commit, corpus_hash
ceo-health.py | jq .rag         # 10th ceo-health probe (future)

# 4. Activate framework bridge (opt-in)
export CEO_RAG_SIDECAR=1        # add to ~/.zshrc / ~/.bashrc
```

## Daily workflow

```bash
# Incremental index after feature work
ceo-rag index --incremental     # <1 min for ≤20 files changed

# Pause sidecar (reclaim RAM)
ceo-rag stop

# Restart
ceo-rag start

# Uninstall (keeps indexed data)
bash .claude/rag/install-sidecar.sh --uninstall
# Remove data fully
rm -rf ~/.ceo-orchestration/rag/
```

## Kill-switches

| Env var | Default | Effect |
|---------|---------|--------|
| `CEO_RAG_SIDECAR` | `0` (disabled) | `1` enables bridge; any other value = off |
| `CEO_RAG_QUERY_TIMEOUT_MS` | `5000` | Per-query timeout |
| `CEO_RAG_HEALTH_PROBE` | `1` | `0` skips probe (offline dev) |
| `CEO_RAG_SCAN` + `_ACK` | scan ON | `CEO_RAG_SCAN=0 + CEO_RAG_SCAN_ACK=I-ACCEPT-INJECTION-RISK` bypasses chunk scan (NOT recommended) |
| `CEO_RAG_SOCKET` | `~/.ceo-orchestration/rag/sidecar.sock` | Override socket path |
| `CEO_RAG_RETRY_HEALTH` | unset | `1` forces re-probe after dead-cache |

## Security

The sidecar holds your full source tree indexed + embedded. Treat the
storage dir at `~/.ceo-orchestration/rag/<project-id>/` as
**equivalent-sensitivity to your source tree**.

### Defenses shipped

| Layer | Mechanism |
|-------|-----------|
| Install | `pip install --require-hashes --no-deps` — no unpinned code |
| Install | Model SHA256 verify OR explicit two-factor ack |
| Install | Refuses EUID 0; refuses if venv corrupt or .install.lock present |
| Index | `.claude/rag/indexignore` excludes `.env*`, `secrets/`, `node_modules/`, `.venv/`, keys, tokens, SQLite dumps |
| Index | Pre-embed scan: LLM06 secret shapes drop chunk + emit `rag_index_redacted` |
| Index | Symlink-out-of-repo rejected (realpath check) |
| Transport | Unix socket `0600` on POSIX; Windows = named pipe (future); TCP last-resort gated by bearer token |
| Storage | Dir `0700`, files `0600`; atomic manifest writes |
| Bridge | Post-retrieve scan: LLM01/02/10 + tag_character / homoglyph → drop chunk + emit `rag_query_redacted` |
| Bridge | Dead-sidecar cache (30 s) avoids timeout storms |
| Bridge | NEVER imported from hook handlers (SLO-preserving invariant) |

### Threats in-scope

- Adversarial content in your indexed corpus (legitimately committed
  test fixtures, or maliciously injected via a compromised dep)
- Compromised LightRAG PyPI release (mitigated by pin + hashes)
- Local-host process exfiltrating index over socket (mitigated by
  `0600` perms; on Windows by token)

### Threats out-of-scope

- A malicious process with your user UID (it already can read your
  source tree)
- A compromised embedding model with a weight-level backdoor
  activated by specific query strings (partial mitigation via SHA256;
  residual risk acknowledged)
- HuggingFace CDN MITM (TLS helps; model SHA256 catches replacement
  but not backdoor-at-source)

See `.claude/adr/ADR-062-rag-sidecar-mcp-opt-in.md` §Threat model.

## Performance

| Operation | p50 target | p99 target | Notes |
|-----------|-----------|-----------|-------|
| Bridge `rag_search` (naive mode, no LLM) | <100 ms | <500 ms | Cold Chroma; warm cache faster |
| Bridge `rag_search` (local mode, 2 LLM) | ~1 s | <10 s | Requires CEO_RAG_QUERY_TIMEOUT_MS=15000 |
| Index 10 k LoC (full) | 5 min | 10 min | Local embed + fast LLM |
| Index 500 k LoC (full) | 25 min | 4 h | 32 parallel LLM calls, ≥600 RPM tier |
| Index incremental (≤20 files) | 10 s | 60 s | Above 50 files, falls back to deferred rebuild |

Setting `CEO_RAG_QUERY_TIMEOUT_MS=5000` is safe for `naive` mode
only. `hybrid` / `local` modes should raise to 15000 ms and
understand they are NOT suitable for hot-path synchronous calls.

## Troubleshooting

### Sidecar won't start

```bash
ceo-rag status                  # diagnose
cat ~/.ceo-orchestration/rag/sidecar.log
```

Common causes:
- Port/socket collision (another sidecar already running): `ceo-rag stop`
- Corrupt venv: `bash .claude/rag/install-sidecar.sh --uninstall && ...`
- Model weights missing: run `ceo-rag index` which downloads on demand

### Bridge returns None on every query

```bash
# Verify opt-in flag
echo $CEO_RAG_SIDECAR           # must be "1"

# Verify sidecar alive
ceo-rag status
ls -la ~/.ceo-orchestration/rag/sidecar.sock   # must exist, 0600

# Clear dead-cache
export CEO_RAG_RETRY_HEALTH=1
```

### Queries always time out

- p99 of `local`/`hybrid` modes exceeds the default 5 s timeout
- Raise: `export CEO_RAG_QUERY_TIMEOUT_MS=15000`
- Or restrict to `naive` mode in `sidecar-config.json`

### FPR noise from retrieved-content scan

Legitimate code may trigger LLM06 false-positives (test fixtures with
example tokens). Options:
1. Add the fixture path to `.claude/rag/indexignore` (preferred)
2. Two-factor bypass:
   ```bash
   export CEO_RAG_SCAN=0
   export CEO_RAG_SCAN_ACK=I-ACCEPT-INJECTION-RISK
   ```
   (NOT recommended for production; disables the prompt-injection defense)

## Uninstall

```bash
# Stop sidecar
ceo-rag stop

# Remove venv + install lock
bash .claude/rag/install-sidecar.sh --uninstall

# (Optional) Remove indexed data
rm -rf ~/.ceo-orchestration/rag/

# Disable bridge
unset CEO_RAG_SIDECAR
# Remove from ~/.zshrc / ~/.bashrc if added
```

The framework continues normally with grep fallback. Zero impact.

## Battle-test results — PLAN-062 Phase 3 (2026-04-29)

PLAN-062 Phase 3 ran a smoke-test of the sidecar install on the
framework's own repo (~440k LoC, Tier 1 by `scripts/measure-repo-size.sh`).
The smoke-test was a pipeline-validation pre-flight for the eventual
real adopter use.

### Smoke-test environment

| Property | Value |
|---|---|
| Host OS | macOS (Darwin 25.4.0) |
| Default Python | 3.9.6 (system) |
| Homebrew | 5.1.6 (available, Python 3.10+ NOT installed) |
| pyenv / asdf | not installed |

### Findings — TWO blockers prevent installation today

**Finding 1 (P0 prerequisite gap):** macOS-current ships Python 3.9
by default. The sidecar requires Python 3.10+ per ADR-062. Adopters
must install Python 3.10+ via `brew install python@3.11` or
`pyenv install 3.11.x` before running `install-sidecar.sh`. The
script correctly errors with a clear message
("Python 3.10+ required. Install via pyenv / brew / apt."), but the
prerequisite is non-trivial for casual adopters.

> **Recommendation:** Add a "Prerequisites — install Python 3.10+
> first" subsection to §Install with explicit `brew install
> python@3.11` and `pyenv install 3.11.13` commands.

**Finding 2 (P0 placeholder by-design):** `.claude/rag/requirements.lock`
ships as a documented PLACEHOLDER (40 LoC of comments explaining the
generation contract, zero pinned packages). The script
`install-sidecar.sh` fails fast with:

> ERROR: requirements.lock is a placeholder (no pinned packages).
> Regenerate per file header instructions + commit via
> branch-protected PR. Supply-chain P0-2 blocker.

This is **intentional** per PLAN-041 Round 1 debate (security-engineer
P0-2 — supply-chain attack mitigation requires hash-locked deps
before any pip install). The placeholder IS the mitigation; populating
it requires:

1. Pin a top-level `lightrag==<version>` in `/tmp/reqs.in`
2. Run `pip-compile --generate-hashes` to produce hash-locked
   transitive closure
3. Commit via branch-protected PR
4. CODEOWNERS review
5. Optional: ADR-063 amendment for new LightRAG major version

This ceremony has not been completed. Until it is, **the sidecar is
operationally unavailable to any adopter, including the framework's
own repo.**

### Honest disposition

The sidecar is documented as "ACCEPTED, opt-in" via ADR-062, but is
in practice **not installable today** without the ceremony above.
Adopters reading this doc should know:

- ADR-062 is structurally complete (script, bridge, MCP protocol
  surface, `_index_core.py` indexer logic, tests)
- `requirements.lock` ceremony is the gate between "structurally
  complete" and "actually installable"
- Until the ceremony runs, plan around grep + Read fallback (which
  is what the framework already does anyway when sidecar is absent)

### Recommendation for adopters (until ceremony completes)

- **Tier 0 (vibecoder solo, < 50k LoC):** skip sidecar entirely.
  CAG + grep is sufficient. See `ADOPTER-SCALE-TIERS.md`.
- **Tier 1 (50k-1M LoC):** plan to use sidecar post-ceremony OR run
  ceremony yourself in your fork. Until then, use re-rank recipes
  in `CAG-VS-RAG.md` §3 + `examples/rerank-spawn-context.py`.
- **Tier 2 (>1M LoC):** sidecar is mandatory; running the ceremony
  is the prerequisite. Until ceremony, you'll need a custom
  retrieval pipeline (vector DB of your choice).

### Recommendation for framework maintainers

If the sidecar is intended for real-world use post-PLAN-062, the
ceremony to populate `requirements.lock` is the next step. The
framework's own repo (440k LoC) is a reasonable test target —
indexing it would validate the pipeline end-to-end. Until then,
treat ADR-062 as "documented design, not shipped product."

### Per-query smoke results

Could not be measured — sidecar not installed.

### Performance numbers

Could not be measured — sidecar not installed.

---

## References

- `.claude/adr/ADR-062-rag-sidecar-mcp-opt-in.md` — architecture decision
- `.claude/plans/PLAN-041-rag-sidecar-mcp.md` — implementation plan
- `.claude/plans/PLAN-041/debate/round-1/consensus.md` — debate synthesis
- `.claude/plans/PLAN-062-cag-rag-readiness-docs.md` — Phase 3 smoke-test plan
- `docs/SECURITY.md` — framework security posture
- `docs/ADOPTER-SCALE-TIERS.md` — when sidecar pays off (Tier 1+)
- `docs/CAG-VS-RAG.md` — alternatives when sidecar isn't available
- `SPEC/v1/rag-sidecar.schema.md` — MCP protocol subset contract (future)
- [LightRAG repo](https://github.com/HKUDS/LightRAG) — upstream project
