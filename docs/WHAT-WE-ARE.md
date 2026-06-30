# What we are — and what we are NOT

<!-- last-reviewed: 2026-06-20 v1.0.0 -->

> Status: v1.0.0, public release (vibecoder-stable line, ADR-096).
> Read this before adopting, evaluating, or comparing the framework to a
> SaaS / IDE plugin / agent SDK.

---

## §1. What we ARE

### 1. We are a portable governance + agent-orchestration protocol for Claude Code.

Claude Code is the runtime; we are the discipline on top of it. We define
a CEO (Claude) reporting to an Owner (human), three VPs, ICs, and staff
specialists with cross-cutting veto power. Every named-agent spawn must
load a persona + a skill + a non-overlapping file assignment — and a
PreToolUse hook (`check_agent_spawn.py`) blocks spawns that skip the protocol.

### 2. We are a tamper-evident audit chain for AI work.

Every spawn, every canonical edit, every debate verdict, and every
Pair-Rail invocation emits one JSONL row to an out-of-repo audit log,
HMAC-chained for byte-level tamper-evidence. `audit-query.py` reads
back by-action / by-domain / by-plan. The chain is the proof artifact
a CTO can inspect — not pitch copy.

### 3. We are a cross-LLM verification rail (Pair-Rail) for L3+ decisions.

Claude's L3+ architectural proposals are reviewed by Codex MCP (a
different model family) before they ship. Asymmetric VETO matrix
Cases A–F cover model-collusion failure modes. PostToolUse ingress
sanitization (`check_codex_response.py`) defends against prompt
injection in Codex output.

### 4. We are a smart-loading skill catalog of 151 reusable checklists.

Skills live in three tiers: 42 core (universal), 8 frontend (universal
frontend), and 101 domain (fintech, marketing-global,
sales, trading-hft, legal, lgpd-heavy-saas, etc.). Per-repo profile
detection auto-activates only relevant skills, with numeric caps per
profile (frontend ≤10, engine ≤12, fintech ≤15, trading-readonly ≤8,
generic ≤6).

### 5. We are install-into-an-existing-repo, not a hosted product.

`scripts/install.sh <target-repo>` copies `.claude/` + hooks + scripts
into your repo. `scripts/uninstall.sh` removes them via a SHA-pinned
manifest. We never call home. No telemetry, no API keys beyond
Anthropic's (which Claude Code already needs).

### 6. We are stdlib-only Python ≥3.9, MIT-licensed, fork-friendly.

Zero third-party runtime dependencies. All GitHub Actions SHA-pinned.
~12,000 test cases (by `pytest --collect-only`) across hooks + scripts +
formal + integration with tiered coverage (Tier-1 security-critical hooks
≥86%; repo floor 67%).
SBOM published. The framework is auditable end-to-end
by one engineer in an afternoon.

### 7. We are vibecoder-first by design (ADR-096).

Built for one Owner running ~5 personal repos at hours-not-weeks
velocity. The protocol forces planning + parallelism + verification
without bureaucratic ceremony. Optimized for "I am the CTO and the
junior dev simultaneously" — not for 50-person engineering orgs.

---

## §2. What we are NOT

### 1. We are NOT a SaaS product.

There is no UI, no hosted dashboard, no login screen, no subscription.
Everything runs locally inside Claude Code on your machine. If you
want a hosted offering, this is not it.

### 2. We are NOT a Cursor / Copilot / IDE plugin competitor.

Cursor rules are prompt-time hints injected into a model's context.
We are runtime hooks + audit chain + multi-agent debate + cross-LLM
verification. Different layer of the stack. Use both if you want.

### 3. We are NOT a code-completion tool.

We assume you already use Claude Code's existing edit / read / bash
tool surface. We add governance and audit on top; we do not generate
inline suggestions or autocomplete.

### 4. We are NOT multi-tenant or enterprise-positioned.

v1.0 targets one Owner across five repos. No SSO, no per-user
permissions enforcement, no SLA, no support tier. ADR-096 explicitly
deferred enterprise positioning. Branch protection + CODEOWNERS is
the only access-control surface.

### 5. We are NOT a greenfield scaffolding tool.

There is no `framework init` wizard, no project templates per stack.
Install into a repo that already has code. We meet your project where
it is — we do not bootstrap a new one.

### 6. We are NOT multi-LLM agnostic.

Claude-only by design (ADR-085 ACCEPTED, ADR-084 REFUSED). Codex MCP
participates only as the Pair-Rail verifier. If you need Gemini /
OpenAI / local-model orchestration, use AutoGen, LangGraph, CrewAI,
or Portkey instead.

### 7. We are NOT a magic harness.

The protocol forces you (and Claude) to plan, distribute work, and
verify before shipping. It does not make Claude smarter, faster, or
correct-by-default. It makes the failure modes visible and the
ceremony unavoidable.

---

## §3. The 60-second pitch (AC3-rehearsable)

> A solo Owner running important AI work needs governance without
> a 50-person org. We wrap Claude Code with Plan → Debate → Execute,
> a tamper-evident audit chain, and a Codex Pair-Rail that catches
> L3+ mistakes before they ship. What you get is governance-as-code:
> ~12,000 test cases, an inspectable HMAC-chained log, and a cross-LLM
> rail. We make no speed claim — six experiments found no general
> speedup (PLAN-122), and we publish that null result honestly. Skip us
> for one-file edits — overhead beats velocity below.

(5 sentences, ≤25 words each. Total ~80 words → ~50–55 seconds spoken.)

---

## §4. When to use us / when to NOT

### Use the framework when:

- Long-running AI orchestration on a repo that matters (financial,
  regulated, customer-facing, your bread-and-butter codebase).
- Monthly Claude API spend exceeds ~$50 — audit + budget guardrails
  pay for themselves.
- You run multiple plans in flight and need a debate record + an
  ADR trail you can re-read in six months.
- An auditor, CTO, or co-founder will ask "what changed and why"
  and you need an answer that is not "Claude said so."
- You work alone but want the friction of a team review on L3+
  decisions (Pair-Rail substitutes the missing second engineer).

### Do NOT use the framework when:

- Single-file edits, typos, log-message tweaks (L1–L2 work) — the
  governance overhead exceeds the work itself.
- Throwaway vibe-coding for a 1-hour script you will delete tomorrow.
- Your team already mandates Cursor rules or another orchestrator as
  policy — we do not coexist cleanly with parallel governance layers.
- You need multi-LLM portability or non-Anthropic models as the
  primary engine (see §2.6 — wrong tool).
- You need a hosted service with SLA, support, or enterprise SSO.

---

## §5. Honest limitations

We publish them. Read `docs/HONEST-LIMITATIONS.md` before adopting.
Summary highlights:

- **Bus factor 1** — Owner is the only maintainer; no co-signer.
- **GPG ceremony Owner-physical** — adds ~30s–2min per canonical
  edit; this is intentional friction, not a bug.
- **Cost is not zero** — Pair-Rail review on a typical L3+ plan
  costs $30–50 in Anthropic + Codex tokens.
- **Same-LLM problem** — sub-agent debate is structured-checklist
  forced perspective, not adversarial second-opinion. Mitigated
  by Pair-Rail (different model) and Owner human-in-the-loop.
- **Smart-loading is v1.0-emerging** — per-profile caps are
  enforced, but skill priority + tie-break ordering will refine
  with real-usage data.

Honesty is the moat. If a limitation lands you on the wrong tool,
we want you to find out before install, not after.
