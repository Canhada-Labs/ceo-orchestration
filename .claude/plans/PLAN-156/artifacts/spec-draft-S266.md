# PLAN-156 spec — pre-plan brainstorm artifact (ADR-058)

> Emitted S266 (2026-07-10) before/alongside plan drafting; the V0 input
> for the debate. This is the **brainstorm artifact of record ONLY** —
> it is NOT the `spec_ref` target and NOT a trusted SPEC-CONTEXT surface
> (the plan frontmatter leaves `spec_ref` unset until W0b). **Staging
> note:** the canonical home `.claude/plans/PLAN-156/spec.md` is a
> guarded path (ADR-010 — spec.md is trusted prompt surface for SPEC
> CONTEXT injection); this draft is promoted there under the W0b sentinel
> and `spec_ref` is set to spec.md only at that point. Until then no
> trusted surface points here. Owner directive:
> "quero que o ceo funcione no codex e no grok além do claude" + GPT-5.6
> family verification + "uma espécie de conselho, pra gente fazer audit
> com codex e grok".

## Problem statement

Three coupled asks, one theme — the framework's governance must survive
and exploit a multi-vendor harness world:

1. **Grok as a third host harness.** The rails (canonical-edit, bash
   safety, plan lifecycle, kernel, audit) must ENFORCE under the
   official xAI Grok Build CLI, with honest labels where primitives are
   missing — the PLAN-155 doctrine applied to a new substrate.
2. **GPT-5.6 family on the codex lane.** Empirically broken today: our
   pinned codex-cli 0.139.0 cannot invoke `gpt-5.6-{sol,terra,luna}`
   (probe S266). Restoring frontier access = ADR-111 pin ceremony +
   matrix re-certification.
3. **Cross-vendor audit council.** Convert three-vendor access into an
   advisory audit instrument: same repo scope, three independent model
   families, vendor-attributed verdicts, disagreement surfaced.

## Evidence base (verified S266)

- Grok Build hooks: blocking PreToolUse, `{"decision":"deny"}` + exit 2,
  **any other exit = fail-OPEN**; Stop non-blocking; legacy compat reads
  `.claude/settings.json`; daily 0.x releases
  (`PLAN-156/artifacts/research-grok-build-cli-S266.md`).
- 5.6 family: Sol/Terra/Luna, first-class codex-cli 0.143.0, latest
  0.144.1; 0.143 renamed the sandbox permission-profile flag; hooks
  schema stable 0.139→0.144
  (`PLAN-156/artifacts/research-gpt56-codex-cli-S266.md` + local probe).
- fable-advisor (MIT) fail-loud lane doctrine — adopted with credit.

## Options considered

**Grok integration shape**
- (a) Full adapter (mirror PLAN-155): adapter module + templates +
  installer + capability matrix + positive controls. **CHOSEN** — the
  seam exists precisely for this; Grok's hook surface is Claude-shaped.
- (b) Legacy-compat only (rely on Grok reading `.claude/settings.json`):
  REJECTED as the primary path — undocumented coverage, tool-name
  vocabulary mismatch risk, no version pin; kept as characterized
  fallback because coexistence is FORCED in a dual-harness repo (Wave 0
  probes double-fire).
- (c) Wrapper-only (no hooks; drive grok via `grok -p` inside a gated
  Bash): REJECTED as governance story — no edit-time enforcement inside
  interactive grok sessions.

**Fail-closed survival on Grok (exit≠2 = fail-open)**
- (a) Wrap in Python adapter dispatch: insufficient — interpreter crash,
  import failure, or signal never reaches Python.
- (b) Wrap in the shared shell shim (`_python-hook` entrypoint) with a
  **decision-derived** exit mapping: a hook that EMITTED a deny (incl. a
  security matcher's structured deny on INPUT-PARSE failure) → exit 2;
  emitted allow → exit 0; **crashed with NO emitted decision
  (ImportError, timeout, signal — infra) → fail-OPEN allow** (CLAUDE.md
  §4 infra half preserved). NOT "any failure → deny": a bare crash must
  fail-open. **CHOSEN** (VP-Eng round-1 critique; supersedes the draft's
  adapter-layer wording) + per-matcher parameterized positive control in
  CI (input-parse deny → blocked; infra crash → allowed).

**Council containment for the grok lane**
- (a) Our own deny-all-writes hooks profile as sandbox: REJECTED as sole
  containment — circular (the fail-open rail guarding itself; codex R1
  P2 + VP-Eng convergent finding).
- (b) Grok lane requires native/OS-level read-only containment
  (sandbox-exec / read-only mount / native flag found in Wave 0), else
  the lane reports `STATUS: unavailable`: **CHOSEN**. Hooks profile kept
  as defense-in-depth on top, never as the load-bearing layer.
- Council ships with Claude + Codex lanes at minimum (`codex exec
  --sandbox read-only` is real OS containment); Grok lane joins when
  (b) is satisfiable.

**Council scope**
- (a) Separate plan: considered (VP-Eng suggestion) — REJECTED for now:
  the Owner asked for it in the same directive, the lanes reuse Wave 1/2
  deliverables, and the advisory-only confinement bounds blast radius.
  CONCEDED to the concern: Wave 6 carries its own mini threat model +
  budget ceilings + explicit W1→W6 dependency, and slips to a follow-up
  plan without blocking Waves 0-5 if debate round 3 still objects.

## Constraints

- stdlib-only, Python ≥3.9; no speed claims; honest ENFORCED/ADVISORY/
  ABSENT labels certified by behavioral positive controls only.
- Guarded surfaces (kernel registry, hooks, installer, validate.yml,
  templates guard-list) land via GPG sentinels with progressive anchors
  (S266 land-plan155.sh mechanics).
- External-LLM lanes: read-only, fail-loud, budget-capped, output
  treated as untrusted data (PROMPT DEFENSE on every lane prompt).
- Audit action count base = live golden at land time (320 lines at
  drafting), never a hardcoded prior.

## Success shape

`--harness grok` installs an enforcing rail whose canonical-deny is
proven by live-fire; a security matcher fed UNPARSEABLE INPUT emits a
structured deny that maps to exit 2 under Grok (while a no-decision infra
crash — ImportError/timeout — fails OPEN, preserving CLAUDE.md §4);
codex lane runs gpt-5.6 tiers under the new pin with the matrix
re-certified; `/council` returns vendor-attributed verdicts from ≥2
OS-contained lanes with loud degradation.
