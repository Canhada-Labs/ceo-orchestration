# Documentation index

`ceo-orchestration` is a portable **governance + auditability framework** for
running Claude Code as a structured team of specialist agents under a "CEO
protocol": **Plan → Debate → Execute** gating for risky changes, a
tamper-evident (HMAC-chained) audit log of every agent spawn, edit, and
ceremony, a cross-LLM "pair-rail" that has a second model review canonical
edits, and a catalog of ready-made skill checklists. It installs **into** an
existing repository via `scripts/install.sh`.

> **No speed claim.** Six controlled experiments found no general speedup over
> an optimized solo workflow. What this framework delivers is **governance and
> auditability**, not raw throughput — and those are orthogonal to velocity. We
> keep that result in writing rather than dress it up; see
> [HONEST-LIMITATIONS.md](HONEST-LIMITATIONS.md).

This folder holds over a hundred files, many of them internal working
artifacts. The tables below curate the **outward-facing** docs by audience.
Pick the row that matches your role and follow it down.

---

## Start here

| Doc | What it is |
|-----|------------|
| [PITCH.md](PITCH.md) | One page: what the framework is, who it is for, and what it deliberately does not promise. |
| [HONEST-LIMITATIONS.md](HONEST-LIMITATIONS.md) | The candid "what this is *not*" — no speedup, single-maintainer bus factor, the same-vendor reviewer caveat, and how it sits next to alternatives like AutoGen, MetaGPT, and LangGraph. Read this before you get excited. |
| [degradation-outside-claude-code.md](degradation-outside-claude-code.md) | What the framework loses when the repo is used outside Claude Code (plain editor, other harnesses): hook enforcement and the audit-chain append stop; records, scripts, and chain verification survive. |
| [GLOSSARY.md](GLOSSARY.md) | Definitions for every term of art: CEO protocol, pair-rail, canonical edit, ceremony, skill, squad. |

---

## For evaluators / CTOs

| Doc | What it is |
|-----|------------|
| [CTO-GUIDE.md](CTO-GUIDE.md) | **Canonical** evaluation guide — a verify-every-claim walkthrough with the exact commands to reproduce every count below. Budget ~30 minutes. |
| [GOVERNANCE.md](GOVERNANCE.md) | The Plan → Debate → Execute contract, veto rules, and the three-strike rule, as actually enforced by the hooks. |
| [threat-model.md](threat-model.md) | STRIDE threat model for the framework as a whole. |
| [CROSS-LLM-THREAT-MODEL.md](CROSS-LLM-THREAT-MODEL.md) | Threat model for the cross-LLM pair-rail specifically — what a malicious or compromised reviewer model can and cannot do. |
| [soc2-audit-mapping.md](soc2-audit-mapping.md) | Maps framework controls to SOC 2 criteria. **Freshness caveat:** last reviewed 2026-04-16 — treat it as a starting map and re-verify against current behavior before relying on it. |

> A Portuguese one-pager, `CEO-ORCHESTRATION-FOR-CTO.md`, also lives in this
> folder but is **legacy**. Use `CTO-GUIDE.md` as the source of truth.

---

## For operators

| Doc | What it is |
|-----|------------|
| [INSTALL.md](INSTALL.md) | Installing the framework into an existing repo via `scripts/install.sh`, including profile and stack-gate options. |
| [DAY-1-CHECKLIST.md](DAY-1-CHECKLIST.md) | First-day checklist: confirm hooks fire, the audit chain writes, and ceremonies seal. |
| [DISASTER-RECOVERY.md](DISASTER-RECOVERY.md) | Recovery procedures for a broken audit chain, lost runtime state, or a botched upgrade. |
| [rollback-drill.md](rollback-drill.md) | A rehearsable rollback drill, so recovery is practiced rather than improvised. |

---

## Architecture & internals

| Doc | What it is |
|-----|------------|
| [ARCHITECTURE-DIAGRAM.md](ARCHITECTURE-DIAGRAM.md) | The component map — hooks, the shared library, the audit log, skills — and how a session flows through the gates. |
| [ADAPTIVE-EXECUTION-KERNEL.md](ADAPTIVE-EXECUTION-KERNEL.md) | How execution effort adapts to task complexity. |
| [CEO-MODEL-ROUTING.md](CEO-MODEL-ROUTING.md) | How work is routed across model tiers, and the policy behind those choices. |

---

## What the numbers are

Every count below is reproducible from a clean checkout. The CTO guide lists the
full set of commands; here is the summary you can spot-check in a minute.

| Thing | Count | How to verify |
|-------|-------|---------------|
| Skills | **151** (42 core + 8 frontend + 101 domain) | `find .claude/skills -name SKILL.md \| wc -l` |
| Hook scripts on disk | **53** Python scripts | count `*.py` in `.claude/hooks/` |
| Hooks registered | **44** distinct scripts (46 event registrations) | inspect `.claude/settings.json` |
| Slash commands | **22** | count `*.md` in `.claude/commands/` |
| Architecture decision records | **171** | count `ADR-*.md` in `.claude/adr/` |
| Shared library modules | **67** stdlib-only (top-level `_lib/`) | count `*.py` in `.claude/hooks/_lib/` |
| Tests | **~670 test files**; `make test-collect` (pytest `--collect-only`) reports **~12,000** collected cases | `make test-collect` |

Two of these are easy to misread, so we state them plainly: the **53** hook
scripts on disk are not all wired at once — **44** distinct scripts (across 46 event registrations) are registered in
`settings.json` for this repo's install. And the test figure is *collected
cases*, not hand-written functions; parametrization inflates the count, which is
why we cite `make test-collect` as the authority rather than a grep.

**Runtime:** Python ≥ 3.9, **stdlib-only** — zero third-party runtime
dependencies (see [../SBOM.md](../SBOM.md)).

**On formal methods:** a TLA+ specification of the core state machine lives under
[formal-verification/](formal-verification/), but model-checking is **not yet
run in CI** — so this is a specification, not a verification claim. Separately,
the HMAC audit chain **detects tampering** (it does not *prove* the absence of
tampering); the `verify_chain()` routine that does so is real and runnable.

---

*Other files in this folder are internal working notes and one-off reports. They
are not part of the supported, outward-facing documentation set and may be moved
or removed without notice.*