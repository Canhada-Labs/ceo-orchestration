# Architecture

This document is the component-level reference for `ceo-orchestration`. It
explains what is in the repository, how the pieces fit, and where the
load-bearing enforcement lives. For *why* the project exists and the honest
"no speed claim" framing, see the [README](../README.md). For the published
compliance contract, see [`SPEC/v1/`](../SPEC/v1/README.md).

`ceo-orchestration` is a **governance layer**, not an application and not an
operating system. It installs *into* an existing repository (`scripts/install.sh`)
and runs Claude Code as a structured team of specialist agents under a
Plan → Debate → Execute protocol, backed by a tamper-evident audit log. Every
runtime component is Python ≥ 3.9, **stdlib-only — zero third-party runtime
dependencies** (see [`SBOM.md`](../SBOM.md)).

---

## Repository layout

```
ceo-orchestration/
├── PROTOCOL.md                     # governance contract: Plan→Debate→Execute, vetoes, 3-strike
├── CLAUDE.md                       # master context the agent reads at session start
├── README.md                      # overview (EN + PT-BR)
├── INSTALL.md                      # installation guide
├── SBOM.md                         # software bill of materials (stdlib-only)
├── Makefile                        # `make test-collect`, `make test-quick`
├── scripts/
│   ├── install.sh                  # copy the framework into a target repo
│   └── upgrade.sh                  # pull framework updates into an install
├── templates/                      # files materialized into a target on install
│   ├── CLAUDE.md                   # starter master-context template
│   └── settings/                   # base + opt-in stack hook configs
├── SPEC/
│   └── v1/                         # published compliance contract (28 schema files)
├── docs/                           # operator + architecture docs (this file)
│   └── formal-verification/        # TLA+ specs + advisory TLC runner
├── .github/workflows/              # CI: governance validate, release gate, coverage, TLC
└── .claude/
    ├── team.md                     # backend org template (VPs, ICs, staff VETO, ROUTING TABLE)
    ├── frontend-team.md            # frontend org template (UI/UX, Data, Quality leads)
    ├── pitfalls-catalog.yaml       # universal pitfall rules (IPC/SEC/ARCH/DB/FE/LLM)
    ├── task-chains.yaml            # 7 universal workflows (implement-feature, fix-bug, …)
    ├── settings.json               # hook registrations for this repo (dogfood)
    ├── hooks/
    │   ├── _python-hook.sh         # resolves newest Python ≥ 3.9, fails with guidance
    │   ├── _lib/                   # 67 stdlib-only shared modules (137 incl. subpackages)
    │   ├── *.py                    # 53 hook scripts on disk
    │   └── tests/                  # hook unit tests
    ├── scripts/                    # protocol toolkit (validate, inject, audit-query, …)
    ├── commands/                   # 22 slash commands (*.md)
    ├── skills/
    │   ├── core/                   # 42 universal backend skills
    │   ├── frontend/               # 8 universal frontend skills
    │   └── domains/                # 110 skills across 33 domain profiles
    ├── adr/                        # 171 architecture decision records
    └── plans/                      # plan schemas + per-plan working files
```

The counts above are verifiable from a clean checkout. Don't take them on
faith — run the commands:

| Component          | Count                        | Verify command                                            |
|--------------------|------------------------------|-----------------------------------------------------------|
| Skills             | 160                          | `find .claude/skills -name SKILL.md \| wc -l`             |
| └ core / frontend / domain | 42 / 8 / 110         | `find .claude/skills/core -name SKILL.md \| wc -l` (etc.) |
| Hook scripts       | 53 on disk                   | `ls .claude/hooks/*.py \| wc -l`                          |
| Hook registrations | 44 wired into `settings.json`| (parse the `hooks` block of `.claude/settings.json`)      |
| `_lib` modules     | 67 top-level (137 recursive) | `ls .claude/hooks/_lib/*.py \| grep -v __init__ \| wc -l` |
| Slash commands     | 22                           | `ls .claude/commands/*.md \| wc -l`                       |
| ADRs               | 171                          | `ls .claude/adr/ADR-*.md \| wc -l`                        |
| SPEC/v1 files      | 32 (28 `*.schema.md`)        | `ls SPEC/v1/*.md \| wc -l`                                |
| Test files         | ~670                         | `git ls-files '*test_*.py' '*_test.py' \| wc -l`          |
| Collected cases    | ~12k parametrized            | `make test-collect` (pytest `--collect-only`)             |

> **On the "53 vs 44" hook gap.** 53 is the number of hook *scripts* present in
> `.claude/hooks/`. 44 is the number of those scripts *wired into* this repo's
> `.claude/settings.json` (across 46 event registrations — one script can fire on
> more than one event). The difference is real and intentional: some scripts are
> opt-in, stack-specific, superseded, or invoked indirectly by other hooks. Both
> numbers are reported here rather than conflated into one impressive figure.

> **On "~12k tests."** That is the count of *collected, parametrized* cases
> reported by `pytest --collect-only`, spread across roughly 660 `test_*.py`
> files. It is not 12,000 hand-written, independent test functions — many are the
> same logic exercised over a table of inputs. We report the collector's number
> with that caveat rather than dress it up.

---

## 1. The hook governance layer

Hooks are the mechanical core of the protocol. They are the reason the framework
is enforcement and not just documentation: a convention you *could* follow
becomes a rule the harness *makes* you follow.

A hook is a single-file Python script with a pure decision function and unit
tests. It reads a JSON event on stdin, decides allow/block, and writes a
schema-compliant JSON verdict on stdout. Hooks are invoked through
`_python-hook.sh`, a shim that resolves the newest available interpreter
(`python3.13` → `3.12` → `3.11` → `3.10` → `3.9` → `python3`) and prints
installation guidance if none is found.

**The keystone is `check_agent_spawn.py` (PreToolUse).** When Claude spawns a
subagent, this hook inspects the spawn's `description` for a team member's first
name (extracted dynamically from `team.md` plus any installed domain personas).
If it matches a named persona, the prompt **must** carry a `## SKILL CONTENT`
section — otherwise the spawn is blocked with a governance error. Without it,
nothing stops Claude from labeling a generic prompt with a specialist's nametag;
the hook turns the spawn protocol into a hard gate.

Other load-bearing hooks in the same family:

- `audit_log.py` (PostToolUse) — silent observer; writes one redacted JSONL row
  per spawn/edit to the audit chain (see §3).
- `check_bash_safety.py` — blocks destructive shell (`rm -rf`, `git reset
  --hard`, `git push --force`).
- `check_plan_edit.py` — enforces the plan lifecycle and naming rules.
- `check_canonical_edit.py` — guards the canonical governance files so they can
  only change through the reviewed ceremony path, not ad-hoc edits.
- `check_read_injection.py` / `check_webfetch_injection.py` — treat fetched and
  read content as data, scanning for prompt-injection patterns.
- `check_pair_rail.py` / `check_codex_response.py` — wire the cross-LLM
  pair-rail (see §3).

**Fail-open on infrastructure.** Hooks never block a working session because of
their own bugs. On a parse error, missing file, or timeout, a hook logs a
breadcrumb and emits `{}` — a schema-compliant allow. Governance gates the work;
it does not become a single point of failure for the operator. (Security
decisions that *should* deny — a malformed credential override, a tampered
sentinel — fail closed; only infrastructure faults fail open.)

---

## 2. The skill catalog and smart-loading

A skill is a `SKILL.md` file: a **checklist**, not a narrative. It tells an agent
what to verify, which patterns to use, and which anti-patterns to flag. Skills
are organized in three tiers under `.claude/skills/`:

```
core/        42 universal backend skills      (always available)
frontend/     8 universal frontend skills     (always available)
domains/    110 skills across 33 profiles     (opt-in per install)
```

The 110 domain skills span 33 profiles — the largest being `marketing-global`,
`fintech`, and `sales`; the smallest are single-skill seeds (e.g. `mobile`,
`voice-ai`, `embedded`) scaffolded for expansion. The authoritative per-domain
inventory with descriptions is auto-generated into
`.claude/skills/core/ceo-orchestration/SKILL.md` and regenerated by
`.claude/scripts/generate-skill-inventory.sh`.

A few skills ship a `SKILL-frontend.md` variant alongside `SKILL.md` where the
frontend guidance diverges meaningfully from the backend version; the agent
loads whichever fits its role.

**Smart-loading.** Skills are not all loaded at once. The CEO consults the
`SKILL MAP` and `ROUTING TABLE` in `team.md` to decide which skill an agent
needs, then `inject-agent-context.sh` assembles the spawn prompt: the agent's
persona block, the full relevant `SKILL.md`, and any matching rules from
`pitfalls-catalog.yaml`. A tier boundary is enforced — core and frontend skills
must not reach down into domain specifics (`check-tier-boundaries.py`).

---

## 3. The audit chain and the cross-LLM pair-rail

Every spawn, edit, and ceremony emits a JSONL row to an out-of-repo audit log
(`$HOME/.claude/projects/<project-slug>/audit-log.jsonl`). Rows are written by
`audit_log.py` with secret redaction, SHA-256 hashing of descriptions, and
per-hook duration measurement, rotating at 10 MB.

The log is **tamper-evident**, not tamper-proof. Each row carries an HMAC that
chains to the previous row's HMAC (`_lib/audit_hmac.py`). A later
`verify_chain()` walk **detects** any insertion, deletion, or in-place edit —
the chain breaks at the altered row. This shows *that* tampering occurred and
*where*; it does not, and cannot, prove that no tampering ever happened. Values
in the HMAC are canonicalized (integers only — no floats) so the chain is
reproducible byte-for-byte across machines. The `audit-query.py` toolkit reads
the log read-only, and a local SSE dashboard
(`.claude/scripts/audit-dashboard.py`, loopback, read-only) renders it live.

**The pair-rail.** Risky canonical edits are reviewed by a *second, different*
model — Codex reviews Claude's proposed changes — before they are accepted. The
review is wired through `check_pair_rail.py` and `check_codex_response.py` and
recorded in the audit chain. This is a genuine second pair of eyes from a
different vendor. It does not cover every code path, and most other
"independent" sub-agents are the same underlying model reviewing itself — see
the honest *Risks / Not-For* caveat in the [README](../README.md).

### Data flow: a single spawn

```
  Claude requests a subagent spawn
            │
            ▼
  ┌──────────────────────────┐  block (governance error)
  │ PreToolUse:              │ ──────────────────────────►  spawn rejected,
  │ check_agent_spawn.py     │  missing ## SKILL CONTENT     operator sees why
  │  • match persona name    │
  │  • require SKILL CONTENT │
  └───────────┬──────────────┘
              │ allow
              ▼
       subagent runs
              │
              ▼
  ┌──────────────────────────┐
  │ PostToolUse:             │
  │ audit_log.py             │
  │  • redact secrets        │
  │  • SHA-256 description   │
  │  • HMAC-chain the row    │ ──►  append to audit-log.jsonl
  └──────────────────────────┘            │
                                          ▼
                            verify_chain() later DETECTS
                            any insert / delete / edit
```

---

## 4. The SPEC contract

`SPEC/v1/` is the published, versioned compliance contract (SemVer; currently
v1.0.0, aligned with the repo `VERSION`). It contains 28 schema files defining
the stable interfaces an adopter can pin to — among them `audit-log.schema.md`,
`hook-io.schema.md`, `plan.schema.md`, `debate.schema.md`,
`skill-frontmatter.schema.md`, `tier-policy.schema.md`, and
`install-cli.md` (which versions the `install.sh` CLI flags as an API).

The SPEC matters because it separates *what the framework promises* from *how
this repository happens to implement it today*. An install pins a SPEC version;
internal refactors that keep the schemas stable do not break adopters.

Decisions that shape these contracts are recorded as Architecture Decision
Records in `.claude/adr/` (171 to date), with a documented lifecycle
(PROPOSED → ACCEPTED, plus SUPERSEDED / RETRACTED).[^adr]

The repository also includes a TLA+ specification of the core state machine
under `docs/formal-verification/` (the breaker, plan-lifecycle, and
debate-convergence models). A CI job (`formal-verify.yml`) downloads a
SHA-pinned TLC toolchain and model-checks these specs on a weekly schedule and
on spec changes. Be precise about what that buys you: the TLC job is
**advisory-only — it does not block merges**, and the project therefore does
**not** claim to be "formally verified." The specs are a design aid and a
regression tripwire, not a proof gate.

---

## 5. The protocol toolkit (`.claude/scripts/`)

These scripts implement the operator-facing protocol and the CI governance
gates:

- `validate-governance.sh` — the session-start and CI structural check: verifies
  `team.md`, that every skill referenced in the `SKILL MAP` exists on disk, that
  required files are present, and that hooks are executable.
- `inject-agent-context.sh <AgentName> <task>` — prints a ready-to-paste,
  protocol-compliant spawn prompt (persona + `SKILL.md` + matching pitfalls).
- `check-skill-health.sh` — walks every `SKILL.md`, resolves its `src/...`
  references, and flags stale skills whose referenced files have moved.
- `check-pitfall-regression.sh` — runs the universal pitfall rules against the
  codebase as a pre-commit / CI check.
- `check-tier-boundaries.py` — enforces the core/frontend → domain boundary.
- `audit-query.py` — read-only queries over the audit log.
- `local/verify-counts.sh` — derives the component counts in this document so
  docs and reality cannot silently drift apart.

The slash commands in `.claude/commands/` (22 of them — e.g. `/spawn`,
`/debate`, `/status`, `/architect`, `/onboard`, `/pitfall`) are the
human-facing entry points that drive this toolkit.

---

## 6. Install and upgrade flow

The framework is delivered *into* a target repository; it is never imported as a
library.

```
$ git clone https://github.com/Canhada-Labs/ceo-orchestration.git
$ cd your-app
$ ../ceo-orchestration/scripts/install.sh --profile core,frontend
```

`install.sh` copies `.claude/` and the relevant `templates/` into the target and
builds `.claude/settings.json` from `templates/settings/settings.base.json`
(universal hooks) plus an optional stack overlay. Templates (`CLAUDE.md`, etc.)
are only written if the target file does not already exist — the installer never
overwrites your work.

Flags:

- `--profile <list>` — comma-separated profiles (default `core,frontend`; add a
  domain such as `fintech`).
- `--stack <name>` — merge a stack overlay into `settings.json`. `node` adds a
  pre-commit gate (`tsc --noEmit` + `vitest run`); `none` (default) wires no
  stack hooks.
- `--link` — symlink instead of copy, for submodule-style installs.

`upgrade.sh` pulls framework updates into an existing install, backing the prior
version up to `.claude.bak/<timestamp>/` first, and accepts the same `--profile`
and `--stack` flags. After installing, the operator fills in the target's
`CLAUDE.md`, replaces the archetype role names in `team.md` with concrete
personas, and starts a Claude Code session.

---

## How the pieces fit

```
   install.sh ──► .claude/ in your-app
                      │
   session start ─────┤  CLAUDE.md + PROTOCOL.md + team.md loaded
                      │  validate-governance.sh (structural gate)
                      ▼
   work request ──► Plan ──► Debate (L3+ only) ──► Execute
                      │            │                  │
                      │            │                  ▼
                      │            │           spawn ──► check_agent_spawn.py (gate)
                      │            │                  │
                      │            │                  ▼
                      │            │           edit ──► check_canonical_edit.py
                      │            │                  │   + pair-rail (Codex review)
                      │            │                  ▼
                      └────────────┴───────────► audit_log.py ──► HMAC-chained log
                                                                       │
                                                          verify_chain() detects tampering
```

The skill catalog supplies the *what to check*; the hooks supply the *you must
check it*; the audit chain supplies the *here is the evidence that you did*; and
the SPEC supplies the *stable contract you can pin to*. Governance and
auditability are the product. **There is no speed claim: six internal
experiments found no general speedup over an optimized solo session**, and the
README keeps that result in plain sight alongside the honest limits (bus
factor 1, the same-vendor-reviewer caveat) and the alternatives worth weighing
— AutoGen, MetaGPT, and LangGraph.

[^adr]: ADRs are reference records, not load-bearing prose — see
    `.claude/adr/README.md` for the template and lifecycle.
