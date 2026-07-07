# ceo-orchestration

<!-- last-reviewed: 2026-06-22 v1.0.0 -->

> **Português:** [`README.pt-BR.md`](README.pt-BR.md)

[![License: MIT](https://img.shields.io/badge/License-MIT-yellow.svg)](LICENSE)
[![CI](https://github.com/Canhada-Labs/ceo-orchestration/actions/workflows/validate.yml/badge.svg)](https://github.com/Canhada-Labs/ceo-orchestration/actions/workflows/validate.yml)
[![Release](https://img.shields.io/github/v/release/Canhada-Labs/ceo-orchestration)](https://github.com/Canhada-Labs/ceo-orchestration/releases)

A governance and auditability layer for running [Claude Code](https://docs.anthropic.com/en/docs/claude-code) as a structured team of specialist agents — installed **into** an existing repository, not run as a service.

> **Status:** maintained personal-use framework — bus-factor 1, no roadmap commitments; the public repo is a stable snapshot, not an actively-staffed product. There is no public community, contributor base, or external adopter to speak of — just the framework and its tests.

The premise is narrow and deliberate: an LLM coding agent is most dangerous not when it writes bad code, but when it makes an **unreviewed, unrecorded, irreversible change** to a repository you care about. `ceo-orchestration` puts a gate and a ledger in front of that moment.

**Who it's for:** a solo maintainer or small team running Claude Code on a repository they care about, who want governance and an audit trail over their agent's changes — not speed. If that isn't you, this will mostly feel like friction.

---

## No speed claim

Six internal experiments found **no general speedup** from this orchestration over an optimized solo Claude Code session. The value here is **governance and auditability** — properties that are orthogonal to velocity. We say so at the top rather than dress it up. If you are shopping for "make my agent faster," this is the wrong tool.

What it does give you:

- A **Plan → Debate → Execute** gate for risky changes, so an agent cannot silently rewrite protected files.
- A **tamper-evident audit log** (HMAC-chained) of every agent spawn (the CEO launching a subagent), edit, and ceremony — so you can *detect* after the fact whether the recorded history was altered.
- A **cross-model review rail**: a second LLM (Codex) reviews Claude's edits to protected paths before they land.
- A catalog of ready-made **skill checklists** an agent loads on demand instead of improvising.

---

## How it works

When installed, the framework registers a set of [Claude Code hooks](https://docs.anthropic.com/en/docs/claude-code/hooks) that intercept tool calls (spawning agents, editing files, running shell commands) and apply policy *before* the action happens.

**1. The CEO protocol.** Work is framed as a "CEO" delegating to specialist agents — that framing is where the name `ceo-orchestration` comes from. The session acts as a CEO that decides *what* needs doing and delegates each piece to a purpose-built agent (a security reviewer, an onboarding guide, a debate persona), rather than doing everything in one undifferentiated thread. Routine edits proceed directly. Cross-cutting or risky changes are gated: they require a recorded plan, and for the riskiest class, a structured multi-round debate among agent personas before execution. The protocol is a written contract (`PROTOCOL.md`), enforced mechanically by hooks rather than by convention.

**2. Tamper-evident audit log.** Every governed event appends one JSONL line to a local audit log, each entry HMAC-chained to the previous one. A `verify_chain()` routine walks the log and reports the first break. This **detects tampering** — a removed or edited entry breaks the chain — but it does not *prove* the absence of tampering, and it is a local control, not a notarization service. Treat it as an integrity tripwire, not a court exhibit.

**3. Cross-model pair-rail.** When an agent tries to edit a canonical (protected) path, a hook routes the proposed change to a second model for read-only review. If that reviewer returns anything write-shaped, the edit is blocked. The honest caveat: the default reviewer is another large language model, and same-class reviewers share blind spots (see *Risks*).

**4. Skill checklists.** The framework ships **151 skill files** — reusable, domain-specific checklists (security review, audit fan-out, onboarding to an unfamiliar codebase, and so on) that an agent loads when relevant instead of reinventing the steps each time.

---

## What's in the box

All counts below are verifiable from a clean checkout (see *Verifying the numbers*).

| Component | Count | Notes |
|---|---|---|
| Skill checklists | **151** | 42 core + 8 frontend + 101 domain |
| Hook scripts (on disk) | **53** | Python entrypoints under `.claude/hooks/` |
| Hooks wired in `settings.json` | **44** | distinct scripts, 46 event registrations |
| Shared library modules | **67** | stdlib-only, under `.claude/hooks/_lib/` (excluding the package `__init__.py`) |
| Slash commands | **24** | under `.claude/commands/` |
| Architecture decision records | **171** | under `.claude/adr/` |
| Tests | **~12,000 cases** | reported by `pytest --collect-only` across the hook, script, and conformance suites |

The gap between **53 on disk** and **44 wired** is benign: several non-event modules are activated through in-process dispatch (invoked by other hooks) rather than by a direct `settings.json` event registration.

**Runtime dependencies: none.** Hooks and scripts are Python ≥ 3.9, **standard library only** — zero third-party runtime packages. See [`SBOM.md`](SBOM.md). (Development and CI use third-party test tooling such as pytest; the installed runtime does not.)

There is also a **published compliance contract** under `SPEC/v1/` (32 files — 28 `*.schema.md` plus contract docs, version-pinned), a TLA+ specification of the core circuit-breaker state machine, a conformance harness, and a local read-only audit dashboard.

---

## Which skill should I use?

151 skills is a discovery problem, not a feature. The shortlist below covers the everyday cases; everything else can wait until something breaks. Slash commands are typed in the Claude Code chat; bare names are skill checklists under `.claude/skills/core/` that you (or a spawned agent) load by name.

| If you need… | Use | One-line why |
|---|---|---|
| A governed session start | `/ceo-boot` | Runs the session boot checks and prints a state digest before any work |
| A single-glance picture of project state | `/status` | Plan, phase, vetoes, and recent audit activity in one screen |
| To delegate work to a specialist agent | `/spawn "<Agent>" "<task>"` | Builds the persona + skill + file-assignment prompt the spawn hook enforces |
| To gate a risky (L3+) change | `/debate start PLAN-NNN "<proposal>"` | Recorded multi-round debate among agent personas before execution |
| A structured code review | `code-review-checklist` | The review checklist a spawned reviewer loads instead of improvising |
| A veto-pattern scan of one file | `/veto-check <file>` | Flags veto-worthy code-review and security patterns before a PR |
| A security and auth review | `security-and-auth` | Security architecture, authentication/authorization, and hardening checklist |
| To orient in an unfamiliar codebase | `/onboard <path>` | Entry points, dependency graph, layer map, reading order (skill: `codebase-onboarding`) |
| To decide what and how to test | `testing-strategy` | Testing patterns and quality-assurance doctrine for the project |
| To continue a plan in a fresh terminal | `/resume PLAN-NNN` | Re-derives work state from the plan file, audit log, and scratchpad |
| To hand state between agents mid-plan | `/memory-scratchpad` | Plan-scoped shared memory for inter-agent handoff |
| Proof the guards actually block | `/self-test` | Hermetic in-process test of the core guards — no network, no cost |
| To know what a plan or time window cost | `/agent-budget` | Token usage and cost rollup per plan or window |
| To interpret a cross-model review verdict | `cross-llm-pair-review` | When to invoke the pair-rail and how to read its Case A–F outcomes |
| Known failure patterns before risky work | `/pitfall` | Lists pitfalls from the universal catalog (plus any installed domain catalog) |

Full command and script reference: [`docs/CHEAT-SHEET.md`](docs/CHEAT-SHEET.md). If none of the above fits, the `help-me` skill recommends up to three contextual skills for a task you describe in plain language.

---

## Quick start

> **Official sources only.** The only official distribution points are the GitHub repository [`Canhada-Labs/ceo-orchestration`](https://github.com/Canhada-Labs/ceo-orchestration) and the npm package [`ceo-orchestration`](https://www.npmjs.com/package/ceo-orchestration) (`npx ceo-orchestration`). Any other mirror, fork, re-published package, marketplace listing, or lookalike name is unofficial and untrusted. GitHub releases ship SHA-256 checksums and the npm package is published with SLSA 3 provenance — verify before installing.

**Prerequisites:** Python ≥ 3.9, Git, and Bash. On macOS the system Bash is 3.2; install a modern one with `brew install bash` before installing.

```bash
# 1. Clone the framework somewhere outside your project
git clone https://github.com/Canhada-Labs/ceo-orchestration.git
cd ceo-orchestration

# 2. Install it INTO your target repository
./scripts/install.sh /path/to/your-app

# 3. From inside your project, confirm the governance layer is live
cd /path/to/your-app
bash .claude/scripts/validate-governance.sh   # prints an error count; 0 = healthy
```

### Pick one install path

Three routes can put the framework in front of Claude Code for a target repository, and they are **mutually exclusive per target repo**. The two supported routes (script and npx) write the same surfaces (`.claude/hooks/`, `.claude/skills/`, `.claude/settings.json`, and the install manifest at `.claude/.install-manifest.sha256`); the experimental plugin route instead ships a bundle with its own `hooks/hooks.json` under the plugin root and writes **no** target-repo settings or manifest — so manifest-based uninstall guidance does not apply to it:

| Path | What it is | Status |
|---|---|---|
| `./scripts/install.sh <target>` from a clone | The reference installer (the git-submodule `--link` variant runs the same script) | Supported |
| `npx ceo-orchestration <target>` | npm shim that runs the *same bundled* `install.sh` | Supported |
| Claude Code plugin (`scripts/build-plugin.py`) | Experimental packager of the advisory (`--ceremony user`) surface | Experimental — not a supported install path |

Do **not** stack them on one repo. Mixing paths produces a known failure mode: hooks registered twice (once in `.claude/settings.json`, once via the plugin's own hook registration), so every governed action pays the hook chain twice; settings merges stacked on top of each other; and a drifted install manifest — the manifest records only the last writer, so `uninstall.sh` can no longer faithfully remove the earlier install and leaves orphans behind.

If you have mixed paths, recover in this order:

1. **Uninstall via the path you installed with.** Script or npx installs: `scripts/uninstall.sh <target> --dry-run` first, then for real. The npm shim only exposes the installer, so run `uninstall.sh` from a clone — it honours the same manifest the bundled installer wrote. Plugin: remove it through Claude Code's plugin manager.
2. **Verify `.claude/` is clean.** No `team.md`, `hooks/`, `skills/`, or `.install-manifest.sha256` left behind. The uninstaller deliberately preserves files you modified after install, so inspect and remove leftovers by hand.
3. **Reinstall via exactly one path.**

See [`INSTALL.md`](INSTALL.md) for the full option-by-option guide.

By default the installer copies the core and frontend skill profiles and the governance hooks. Select profiles and stack hooks explicitly:

```bash
./scripts/install.sh /path/to/your-app --profile core,frontend,fintech --stack node
```

Two install modes:

- `--ceremony maintainer` (default): full governance, including signed-edit ceremonies on protected paths.
- `--ceremony user`: advisory hooks only, no signing — writes only under `.claude/`. Good for a low-friction trial.

To verify the safety guards actually block what they claim, run the in-process self-test (hermetic, no network, no cost):

```bash
# from inside your installed project, in Claude Code
/self-test
```

To remove the framework cleanly:

```bash
/path/to/ceo-orchestration/scripts/uninstall.sh /path/to/your-app
```

---

## Verifying the numbers

Don't take the table on faith. From a clean checkout:

```bash
find .claude/skills -name SKILL.md | wc -l        # 151 skills
ls .claude/commands/*.md | wc -l                  # 24 slash commands
ls .claude/adr | grep -c '^ADR-'                  # 171 ADRs
python3 -m pytest --collect-only -q | tail -1     # ~12,000 collected cases
```

---

## Risks and what this is *not*

Intellectual honesty is the point, so the caveats are first-class:

- **Bus factor of one.** This is built and maintained by a single maintainer. There is no team behind it, no SLA, and no guarantee of continuity. Evaluate it accordingly.
- **Same-vendor reviewer caveat.** The cross-model pair-rail reduces single-model blind spots, but the reviewer is still a large language model and can share failure modes with the model under review. It is defense-in-depth, not an independent oracle.
- **Codex is not bundled — the pair-rail is inert until you install it.** The cross-model review rail invokes the [Codex CLI](https://github.com/openai/codex), which is **not** shipped with this framework. On a fresh install with no Codex present, the pair-rail **fails open and contributes zero review** — protected-path edits still pass the GPG ceremony, but no second model looks at them. You only get the cross-model rung after installing Codex separately. See [`docs/HONEST-LIMITATIONS.md`](docs/HONEST-LIMITATIONS.md) and ADR-145.
- **Per-edit overhead.** Each governed tool call runs the hook chain before the action lands, adding roughly **~0.3–1.0s** of latency per edit on typical hardware. That is the cost of the gate; if you want zero overhead on routine work, the governance layer is not free.
- **A gate can be wrong — there is an escape hatch.** Hooks fail *open* on their own infrastructure bugs, but a correct gate can still issue a DENY you disagree with (a false block on a protected path). The intended path is `/architect` (which routes the change through review) or, for a structural framework change, a PLAN-NNN with an Owner-signed sentinel (a GPG-signed approval record that authorizes a specific protected-path edit). For a deliberate, *audited* override of the canonical-edit gate, the Owner can set `CEO_SENTINEL_UNLOCK=<plan-id>` + `CEO_SENTINEL_UNLOCK_ACK=I-ACCEPT` for that action — the override itself is logged. Kernel-path hard-denies (an unconditional block on the most safety-critical files, which no sentinel can lift) need the stronger `CEO_KERNEL_OVERRIDE` ceremony. See [`docs/TROUBLESHOOTING.md`](docs/TROUBLESHOOTING.md). To trial the framework without any of this friction, install with `--ceremony user` (advisory hooks, no signing).
- **Detection, not prevention, on the audit chain.** The HMAC chain tells you *that* the recorded log was altered; it cannot prevent an attacker with local write access from doing damage, and it is not a substitute for proper access controls or backups.
- **Formal verification is scoped, not universal.** A TLA+ specification exists for the core state machine, but model-checking is **not** part of the enforcing CI gate — do not read "has a TLA+ spec" as "formally verified." The overwhelming majority of behavior is covered by conventional tests, not mechanized proof.
- **It is a framework, not a product.** No UI, no managed runtime, no "operating system." It installs into your repo and gets out of the way.
- **No speed benefit.** Restated because it matters: this will not make your agent faster.

**Alternatives worth comparing** if multi-agent orchestration (rather than governance) is your goal: [AutoGen](https://github.com/microsoft/autogen), [MetaGPT](https://github.com/geekan/MetaGPT), and [LangGraph](https://github.com/langchain-ai/langgraph). Those optimize for agent collaboration and workflow expressiveness; this project optimizes for *gating and auditing* a single capable agent's changes to a real repository.

---

## Learn more

**New here?** Start with these:

- [`docs/FAQ.md`](docs/FAQ.md) — the first-user FAQ: what this is (and is not), "a hook just blocked my edit, now what?", does it slow me down, do I need Codex, what gets sent anywhere, how to uninstall.
- [`docs/QUICKSTART.md`](docs/QUICKSTART.md) — install into a repo and confirm the governance layer is live.
- [`docs/DAY-1-CHECKLIST.md`](docs/DAY-1-CHECKLIST.md) — a guided first session.

Then the reference material:

- [`PROTOCOL.md`](PROTOCOL.md) — the governance contract (Plan → Debate → Execute, vetoes, the three-strike rule).
- [`docs/ARCHITECTURE.md`](docs/ARCHITECTURE.md) — component map and data flow.
- [`docs/HONEST-LIMITATIONS.md`](docs/HONEST-LIMITATIONS.md) — the long-form version of the *Risks* section.
- [`SBOM.md`](SBOM.md) — dependency inventory.
- [`docs/GLOSSARY.md`](docs/GLOSSARY.md) — term dictionary: definitions for sentinel, kernel hard-deny, spawn, and the rest of the vocabulary used here.
- [`SPEC/v1/`](SPEC/v1/) — the published compliance contract.

---

## License

See [`LICENSE`](LICENSE).
