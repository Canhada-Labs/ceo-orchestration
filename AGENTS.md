# AGENTS.md — Cross-LLM Reviewer Contract

Contract for the second-model reviewer on the pair-rail (ADR-107): the
non-Claude LLM (currently Codex) that reviews canonical edits proposed in
this repo, so no single model is both author and sole reviewer. Read this
file before reviewing any diff. Humans: start at [README.md](README.md);
Claude Code sessions: start at [CLAUDE.md](CLAUDE.md).

This repo is the framework itself, not an installed copy. It makes **no
speed claim** — the value is governance and auditability. Reject any doc
change that adds throughput or speedup claims.

## 1. Review doctrine

Check every diff against these rules. Each is enforced by CI or hooks; a
REJECT should cite the rule and the offending `file:line`.

| Rule | What to check | Defined / enforced |
|---|---|---|
| Stdlib-only runtime | No third-party imports in framework Python (`SBOM.md` lists zero runtime deps) | [CLAUDE.md](CLAUDE.md) §4 · `.claude/scripts/check-stdlib-only.py` |
| Python ≥ 3.9 compatible | `from __future__ import annotations` present; no runtime PEP 604 unions (use `typing.Optional` / `typing.Union`); no `match` statements | [CLAUDE.md](CLAUDE.md) §4 |
| Fail-open on infrastructure | Hooks never block the session on a missing file, import failure, or timeout — breadcrumb + `{}` allow | [CLAUDE.md](CLAUDE.md) §4 |
| Fail-closed on input (security matchers) | Content a security matcher cannot parse is BLOCKED, not waved through (precedents in `.claude/hooks/check_bash_safety.py`; codified by PLAN-152 debate C4) | [CLAUDE.md](CLAUDE.md) §4 |
| Env isolation in tests | Tests touching env use `TestEnvContext` (`.claude/hooks/_lib/testing.py`) + `mock.patch.dict` — never direct `os.environ[...] =` writes, never the real `$HOME` / `$CLAUDE_PROJECT_DIR` | [CLAUDE.md](CLAUDE.md) §4 |
| No contamination | No personal handles or private project names in framework/template content; neutral placeholders only (`Canhada-Labs`, `your-app`); `.github/CODEOWNERS` is the sole live-handle exception | `.claude/scripts/check-contamination.sh` |
| Counts tolerance = 0 | Hardcoded counts in `CLAUDE.md` (skills/hooks/ADRs/commands) and README badges must exactly match disk — flag any count edit not derived from disk | `.claude/scripts/check-claude-md-claims.py` |

## 2. Action limits

- **Read-only.** The reviewer never edits, creates, or deletes files in
  this repo; it emits a verdict, nothing else. (Enforced hook-side by
  `.claude/hooks/check_codex_filewrite.py`.)
- **No network.** Reviews run sandboxed against the local checkout only.
- **Verdict form.** Review verdicts are `APPROVE` or `REJECT`; every
  REJECT must cite at least one `file:line` per finding. (The runtime
  hook-level dispatch vocabulary PASS / BLOCK / ADVISORY and the Cases A–F
  matrix live in
  [docs/PAIR-RAIL-VERDICT-MATRIX.md](docs/PAIR-RAIL-VERDICT-MATRIX.md).)

## 3. Repo map

One line per directory. The first backtick cell of each row is
machine-checked against disk (see §5).

<!-- agents-md:repo-map:begin -->

| Path | What it is |
|---|---|
| `SPEC/` | Published compliance contract (versioned schemas under `SPEC/v1/`) |
| `benchmarks/` | Replay benchmark driver + calibration samples |
| `docs/` | Operator docs: architecture, threat models, pair-rail verdict matrix |
| `examples/` | Post-install walkthroughs + example scripts |
| `npm/` | npm distribution bundle (`npx ceo-orchestration`) |
| `replay-fixtures/` | Recorded spawn-stream fixtures for replay tests |
| `scripts/` | Installer / upgrader shell scripts (`install.sh`, `upgrade.sh`) + their tests |
| `templates/` | Files the installer copies into target repos |
| `tests/` | Repo-level suites: unit, integration, chaos, forensic, load, synthetic, formal-verification, federation |
| `tools/` | Maintainer utilities (version-drift check, migrations) |
| `.claude/` | The governance layer itself (subdirectories below) |
| `.claude/adr/` | Architecture decision records (`ADR-NNN-<slug>.md`) |
| `.claude/agents/` | Sub-agent persona definitions (routing-table archetypes) |
| `.claude/benchmarks/` | Judge calibration data + schemas |
| `.claude/commands/` | Slash-command definitions |
| `.claude/data/` | Canonical data files (model registry, audit-registry golden) |
| `.claude/dispatcher/` | Pair-rail routing matrix + loader |
| `.claude/docs/` | Internal governance notes and drafts |
| `.claude/eval/` | Self-test eval runner + tasks |
| `.claude/governance/` | Pins, waivers, allowlists, release verdict envelopes |
| `.claude/hooks/` | Governance hooks + shared `_lib/` (the enforcement kernel) |
| `.claude/plans/` | Execution plans (`PLAN-NNN-<slug>.md`) + per-plan artifacts |
| `.claude/policies/` | Policy-as-code YAML + JSON schemas + fixtures |
| `.claude/proposals/` | GPG-signed skill-patch proposals (`SP-NNN`) |
| `.claude/rag/` | Optional RAG sidecar config + indexer |
| `.claude/scripts/` | Governance CLIs + `check-*` gates (+ `tests/`) |
| `.claude/security/` | Sentinel-signers registry |
| `.claude/sidecars/` | Sidecar bundles (crypto, vector-memory, dev-tools) |
| `.claude/skills/` | Skill library (`core/`, `frontend/`, `domains/`) |
| `.claude/templates/` | Squad-bundle authoring template |
| `.claude/trust/` | Owner GPG public key |
| `.claude/workflows/` | Workflow definitions (audit-fanout, nightly-hygiene, eval-baseline) |

<!-- agents-md:repo-map:end -->

## 4. Guarded surfaces

Paths below are canonical-guarded: edits require an Owner-signed sentinel
(some additionally require a kernel override). Authoritative pattern list:
`_CANONICAL_GUARDS` in
[.claude/hooks/check_canonical_edit.py](.claude/hooks/check_canonical_edit.py).
This table is the concrete, existence-checked subset; treat any diff
touching them as L3+ and expect sentinel evidence.

<!-- agents-md:guarded:begin -->

| Path | Why guarded |
|---|---|
| `PROTOCOL.md` | Root governance doc (Plan → Debate → Execute, vetoes) |
| `SPEC/v1/` | Published compliance contract |
| `.claude/settings.json` | Hook / matcher registration |
| `.claude/team.md` | Backend archetype routing table |
| `.claude/frontend-team.md` | Frontend archetype routing table |
| `.claude/pitfalls-catalog.yaml` | Universal pitfall catalog |
| `.claude/hooks/` | Hook sources + `_lib/` — editing these disables governance |
| `.claude/hooks/_python-hook.sh` | Hook shim — self-modification class |
| `.claude/policies/` | Policy-as-code + schemas + fixtures |
| `.claude/dispatcher/` | Pair-rail routing (archetype-spoofing surface) |
| `.claude/agents/` | Persona + model-floor declarations |
| `.claude/adr/` | Architectural record, supersede/immutability discipline |
| `.claude/governance/` | Pins, waivers, verdict trust chain |
| `.github/workflows/` | CI release / validation gates |
| `.github/CODEOWNERS` | Merge-side branch-protection gate |
| `scripts/install.sh` | Framework distribution surface |
| `scripts/install-npm.sh` | Framework distribution surface |
| `scripts/upgrade.sh` | Framework distribution surface |
| `scripts/_hash_lib.sh` | Sourced by GPG-gated install/upgrade |
| `scripts/_framework_manifest_set.sh` | Sourced by GPG-gated install/upgrade |

<!-- agents-md:guarded:end -->

## 5. Freshness

This file is derived from disk and checked, not trusted:

```bash
python3 .claude/scripts/check-agents-md.py            # exit 0 clean / 1 drift
python3 .claude/scripts/check-agents-md.py --format json
```

The checker verifies (a) this file exists at the repo root, (b) every
directory in the §3 repo map exists on disk, (c) every guarded-surface
path in §4 exists on disk. If you rename or remove a listed path, update
this file in the same change.
