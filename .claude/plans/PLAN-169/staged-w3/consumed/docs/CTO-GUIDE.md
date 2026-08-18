# CTO evaluation guide — ceo-orchestration

**Last reviewed:** 2026-08-05 — counts below are gated by `bash .claude/scripts/local/verify-counts.sh`, which fails if any of them drifts from the live tree. This document carries no version literal on purpose; `VERSION` is the single source of truth.
**Audience:** CTO, VP Engineering, Head of Platform, Principal Security.
**Reading time:** 30 minutes if you verify every claim.
**Companion docs:** [`HONEST-LIMITATIONS.md`](./HONEST-LIMITATIONS.md)
(read this first if short on time) · [`threat-model.md`](./threat-model.md)
· [`../SBOM.md`](../SBOM.md).

Every numeric claim in this document is verifiable by running the command
shown inline against a clean clone at the tagged version. If you can't
reproduce a number, it is a bug in this doc — file it.

---

## 1. What this is

A governance + agent-orchestration framework for Claude Code. It installs
into an existing repo and turns a single-Claude session into a structured
team (CEO, VPs, ICs, staff with veto) executing a Plan→Debate→Execute
protocol, with mechanical hooks enforcing the governance in-band with
every tool invocation.

- **Runtime:** Python ≥ 3.9 (stdlib-only) + Bash for install.
- **Install target:** any repo with a `.claude/` directory convention.
- **Operational mode:** local workstation. No server. No phone-home.
- **License:** MIT.

It is **not** a product, not a hosted service, not a Claude Code
replacement. It is a protocol shipped as files.

---

## 2. What ships in the box

Reproduce the table below via the commands in the right column. Counts
refresh every release; if a number drifts, file an issue — that is a
documentation bug.

| Artifact | Count | Verify |
|---|---|---|
| Python tests collected | ~14,000 | `make test-collect` (or `python3 -m pytest --collect-only -q \| tail -1` — pytest.ini pins the testpath roots) |
| Test files | ~730 | `git ls-files '*test_*.py' '*_test.py' \| wc -l` |
| ADRs shipped | 192 | `ls .claude/adr/ADR-*.md \| wc -l` |
| SPEC/v1 files | 32 (28 `*.schema.md`) | `ls SPEC/v1/*.md \| wc -l` |
| Workflows | 22 | `ls .github/workflows/*.yml \| wc -l` |
| GitHub Actions SHA-pinned refs | every `uses:` pinned | `grep -rEc 'uses: [^#]+@(v[0-9]+\|main\|master\|latest)[[:space:]]*$' .github/workflows/*` — must be 0 everywhere |
| Skills | 166 (42 core + 8 frontend + 116 domain) | `find .claude/skills -name SKILL.md \| wc -l` |
| Hooks | 57 .py on disk; 46 wired into `settings.json` (48 event registrations) | `ls .claude/hooks/*.py \| wc -l` |
| `_lib/` stdlib-only modules | 68 | `ls .claude/hooks/_lib/*.py \| grep -v __init__ \| wc -l` |
| Runtime 3rd-party deps | 0 | see `SBOM.md` §1 |

Secondary (not strictly reproducible via one-liner, but derivable):

- **Mutation conformance:** 85 mutation fixtures under
  `tests/formal_verification/mutation_fixtures/`. The contract is the
  expected-kills manifest, not a headline percentage: the harness fails if
  a fixture the manifest expects to die survives. Reproduce:
  `python3 -m pytest tests/formal_verification/ -q`.
- **TLA+ spec coverage:** 4 TLA+ specs published under
  `docs/formal-verification/` (breaker, debate-convergence, plan-lifecycle,
  swarm-coordinator). None of them is model-checked in CI — they are
  specifications, not a verified-system claim (CLAUDE.md §5).

---

## 3. The 30-minute evaluation path

Run each block. Each block is self-contained and takes < 5 minutes on a
modern laptop.

### 3.1 Repo integrity — 2 minutes

```bash
git clone --depth 1 <repo-url> ceo-orch && cd ceo-orch
cat VERSION                                    # the version you are evaluating
bash .claude/scripts/validate-governance.sh   # PASS expected
```

### 3.2 Test posture — 5 minutes

```bash
python3 -m pytest -q \
  .claude/hooks/tests/ .claude/scripts/tests/
# Expect: 0 failures, ≤ handful of skipped (live-adapter gated).
# Full collection across ALL testpath roots = ~14,000 collected cases
# (run `make test-collect`).
```

### 3.3 Supply-chain — 3 minutes

```bash
# No floating action refs
grep -rE 'uses: [^#]+@(v[0-9]+|main|master|latest)[[:space:]]*$' .github/workflows/
# Must print nothing

# Every remaining ref is SHA-pinned (compare with the empty result above)
grep -rE 'uses:.*@[a-f0-9]{40}' .github/workflows/ | wc -l

# No network call inside hooks
grep -rE 'urllib|requests|httpx|socket\.' .claude/hooks/check_*.py
# Empty. (audit_log.py uses socket only for loopback dashboard.)
```

### 3.4 Governance surface — 5 minutes

```bash
# Every PreToolUse + PostToolUse hook
ls .claude/hooks/check_*.py .claude/hooks/audit_log.py

# Every ADR title
grep -h '^# ADR-' .claude/adr/ADR-*.md | sort             # 192 ADRs on disk

# SPEC/v1 published contract
ls SPEC/v1/*.schema.md                                    # 28 schema files
```

### 3.5 Remediation transparency — 5 minutes

Read `.claude/plans/PLAN-152-v1-0-1-hardening-sweep.md` — the
post-v1.0.0 self-audit sweep: 41 confirmed findings (32 fix / 6 accept
/ 3 defer), P0 security fail-opens included, with wave-by-wave
remediation tracked in-tree. Then read
`.claude/plans/PLAN-143-repo-hygiene-debt.md` — repo debt collected
from a nightly hygiene sweep, each item closed with a commit ref
recorded in the plan's own frontmatter.

A framework that publishes its own audit findings is either
self-sabotaging or honest. Decide which.

### 3.6 Honest limitations — 5 minutes

Read [`HONEST-LIMITATIONS.md`](./HONEST-LIMITATIONS.md) end-to-end.
Sections 1-4 are deal-breaker candidates (bus factor, adopter count,
platform matrix, same-LLM critique).

---

## 4. Install path

Two routes.

**A. Source clone + script:**

```bash
# From target-repo root
curl -fsSL <raw-install-sh-url> -o /tmp/install.sh   # INSPECT before running
bash /tmp/install.sh --profile core,frontend --stack node
```

**B. NPM tarball (OIDC + provenance):**

```bash
# Package name is `ceo-orchestration` (npm/package.json) — an earlier
# revision of this guide named a nonexistent `ceo-orchestration-install`
# lookalike (supply-chain-critical doc defect, repass-r2 part-e P1).
# Pin the version you reviewed; <target-dir> is the repo being installed
# into. Then VERIFY provenance yourself — running the command does not:
npm exec "ceo-orchestration@<reviewed-version>" -- <target-dir> --profile core,frontend
npm audit signatures   # SLSA provenance/signature verification step
```

Both routes copy `.claude/`, `PROTOCOL.md`, `templates/CLAUDE.md`, plus
optional domain profiles. Neither pipes to shell in one step; both stage
the install script for inspection first.

Post-install smoke:

```bash
bash .claude/scripts/validate-governance.sh
python3 -m pytest .claude/hooks/tests/ -q
```

---

## 5. Risk budget (what you are signing up for)

| Axis | Current state | Mitigation | Residual |
|---|---|---|---|
| Upstream velocity | Bus factor 1 | Fork-friendly; no server dependency | Patches stack locally if Owner unavailable |
| Production signal | 0 external adopters | Dogfood telemetry (`adopter-metrics.py`) + published benchmarks | You may be adopter #1 |
| Platform | macOS + Linux | WSL2 works empirically, no CI gate | Windows-native: not scoped |
| LLM dependency | Anthropic Claude | ADR-032 Gemini adapter stubbed | Vendor lock until cross-model parity |
| Governance drift | Hooks fail-open on infra bugs | `check_canonical_edit.py` sentinel + CODEOWNERS | Intentional: never block operator on hook bug |
| Audit log tamper | HMAC-chained JSONL, shipped (tamper-EVIDENT) | `audit-verify-chain.py` detects forgery / reorder / deletion | Detection, not prevention — the key lives on the same host; pair with a remote OTEL sink (`docs/otel-integration.md`) |

Read [`HONEST-LIMITATIONS.md`](./HONEST-LIMITATIONS.md) for the full
structural list.

---

## 6. What it does well (backed by numbers, not adjectives)

- **Deterministic governance in-band with tool use.** 46 wired into
  `.claude/settings.json` gate PreToolUse + PostToolUse. Denials are
  structured JSON, not English.
- **Audit trail that survives restart.** Every governance decision
  writes a JSONL line to `~/.claude/projects/<slug>/audit-log.jsonl`.
  Schema versioned (see `SPEC/v1/audit-log.schema.md`, which carries its own
  version history). Replay-friendly.
- **Specified core state machine.** `_breaker.py` modeled in TLA+
  (`docs/formal-verification/breaker.tla`), exercised by the conformance
  harness that owns the 85 mutation fixtures. The spec is not
  model-checked in CI, and this is one component, not the framework —
  see §8 of HONEST-LIMITATIONS.md.
- **Zero runtime third-party deps.** Hooks run with just CPython.
  Install on an air-gapped workstation with Python 3.9+ and you're done.
- **Published evaluation artifacts.** `benchmarks/public/` compares this
  framework against 4 alternatives with reproducible shell blocks.

---

## 7. What it will NOT do for you

- **It will not make your codebase safe.** It makes *Claude sessions*
  against your codebase more structured. Bad code review by humans still
  merges bad code.
- **It will not replace CI.** Hooks run locally. Your `validate.yml`
  still has to pass on `main`.
- **It will not port your prompts.** Skill migration from other
  meta-prompting frameworks (e.g. karpathy-skills, GSD) is manual.
- **It will not run unattended.** There is no autonomous loop. The
  closest surface is the Owner-invoked `/night-mode` posture toggle —
  armed per-session, reversible, and audited — and a human still starts
  and reviews every run.

---

## 8. Decision tree

- **You want production-validated framework with large adopter base:**
  this is not it today — external-adopter validation is explicitly out
  of scope for the current line (HONEST-LIMITATIONS.md §2).
- **You want hosted / SaaS:** not offered. MIT source.
- **You want to evaluate Claude Code governance patterns on a real
  codebase with structured critique and mechanical enforcement:** install
  in a side project for 14 days. Run `.claude/scripts/adopter-metrics.py
  --window 14d`. Report friction.
- **You want to fork and remove the governance you dislike:** encouraged.
  The design is file-based precisely so you can diff and delete.

---

## 9. Next steps for evaluators

1. Skim [`HONEST-LIMITATIONS.md`](./HONEST-LIMITATIONS.md) (deal-breakers
   first).
2. Run §3 (30-minute path) above.
3. Read [`threat-model.md`](./threat-model.md) — specifically §§STRIDE,
   §Adopter, §Same-LLM.
4. If going further: install in a **non-production side repo**, run
   adopter-metrics for 14 days.
5. Report findings via GitHub issue or direct Owner contact.

We prefer one serious evaluator who finds a real defect over ten quiet
stars. If your team runs this and it breaks, we want to hear about it.

---

## 10. Meta-honesty note

This document was written by the framework maintainer, then critiqued by
a debate panel of Claude agents (same-LLM limitation acknowledged — see
HONEST-LIMITATIONS §4). No external reviewer, no third-party security
firm, no SOC 2 certification. A mapping of internal controls to SOC 2
criteria lives at `docs/soc2-audit-mapping.md` as an aid to your own
auditor — it is a claim template, not an attestation.

If you need third-party attestation before adoption, that does not exist
today.
