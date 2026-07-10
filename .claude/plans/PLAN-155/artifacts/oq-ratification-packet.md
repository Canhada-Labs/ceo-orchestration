# PLAN-155 — OQ ratification packet (Wave 0, Owner morning ceremony)

Drafted S266 (2026-07-09) by the CEO. **Everything below is PROVISIONAL
pending Owner morning ratification** — these are CEO recommendations with
rationale, not decisions. Per debate A6, OQ1 is deliberately NOT
ratifiable in this packet. Ratified answers are logged verbatim into
PLAN-155 §Open questions per the Wave 0 checklist.

---

## OQ1 — `/hooks` trust vs `requirements.toml` managed — **NOT RATIFIABLE YET (debate A6)**

> PLACEHOLDER — the orchestrator fills this section with the empirical
> trust-hash keying answer from the Record phase (Wave 1/2) before it
> goes in front of the Owner:
>
> - [ ] Does editing the `_python-hook.sh` shim re-prompt `/hooks` trust?
> - [ ] Does editing a registered hook `.py` (not the shim) re-prompt?
> - [ ] What exactly does the trust hash attest — the registered command
>       file only, or the transitive hook set?
>
> The friction estimate AND the consent-security meaning both invert on
> this answer (shim-only keying = ~zero upgrade friction but thin
> consent; per-file keying = consent fatigue but real attestation).
> Standing CEO lean (from the plan, unchanged, NOT a ratification):
> `/hooks` guided flow as default, `--managed-hooks` opt-in emitting
> `requirements.toml` — consent-first matches the human-gated ethos.
> Do NOT ratify OQ1 until the three checkboxes above carry recorded
> facts with transcript pointers under `PLAN-155/artifacts/`.

## OQ2 — skills-port posture (Wave 8) — RECOMMENDATION: **(b) opt-in copy**

**CEO recommends (b): `--with-codex-skills` opt-in COPY, recorded in the
install manifest.**

- Copy, not symlink: no dependence on target tooling following links
  (option (c)'s failure mode), and the manifest walk / doctor /
  uninstall symmetry machinery (PLAN-153 Wave B, landed) sees plain
  files it already knows how to back up and remove.
- Opt-in, not default: keeps the default `--harness codex` delta minimal
  and honest (rails, not payload), and Wave 8 stays Owner-gated as the
  plan requires.
- Recorded in the install manifest: the flag round-trips through
  `upgrade.sh` replay and uninstall leaves zero residue (debate A9
  lifecycle symmetry; A11 case 8).
- Scope guard unchanged: install-time copy into the TARGET repo's
  `.codex/skills/` — zero new skill files in THIS repo, hardcoded skill
  counts (tolerance=0) untouched; no content fork (single source of
  truth stays `.claude/skills/`).

## OQ3 — inverted-rail reviewer pin — RECOMMENDATION: **`claude-opus-4-8`, 100k-token ceiling, env-overridable**

**CEO recommends:** pin the `claude -p` reviewer of the inverted
pair-rail (Codex operates, Claude reviews) to **`claude-opus-4-8`**.

- **ADR-052 VETO-floor parity:** review roles are Opus-mandatory in this
  house; the inverted direction inherits the same floor — a
  cheaper-tier reviewer would make the Codex-operated direction a
  second-class rail and quietly break the "no single model is both
  author and sole reviewer" property's symmetry.
- **Per-review token ceiling: 100k tokens** (input+output budget per
  review invocation) — mirrors the codex-reviewer posture; the rail
  fails toward "review did not complete → Stop stays blocked / pre-push
  stays red" (never silent-pass on budget exhaustion).
- **Env override: `CEO_PAIR_RAIL_REVIEWER_MODEL`** — named override, same
  commit that pins the model; documented next to the pin so operators
  find it where they hit it (debate A23: operator-visible latency/cost
  expectations stated in the same doc section).
- **Pricing-row note:** the same commit adds/updates the
  `docs/provider-pricing.md`-consistent row for `claude-opus-4-8` in
  the reviewer role, so the pin never exists without its cost line
  (the plan's OQ3 requirement verbatim).
- Verified substrate: `claude` CLI present locally (2.1.206 at drafting;
  plan text verified non-interactive `claude -p` on 2.1.202) — the pin
  names a MODEL, the CLI version is watched separately by the
  substrate-watch `claude_code` entry.

---

## Ratification record (Owner fills at the morning ceremony)

| OQ | CEO recommendation | Owner verdict | Date |
|---|---|---|---|
| OQ1 | (deferred — A6 gate, facts pending) | — NOT RATIFIABLE THIS CEREMONY — | |
| OQ2 | (b) opt-in copy, manifest-recorded | | |
| OQ3 | claude-opus-4-8 / 100k ceiling / CEO_PAIR_RAIL_REVIEWER_MODEL | | |
