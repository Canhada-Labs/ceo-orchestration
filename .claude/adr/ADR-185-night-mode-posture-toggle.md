---
id: ADR-185
title: Night-mode Owner-invoked autonomy posture toggle — bypass cut, single-writer overlay, resolver-derived banner
status: PROPOSED
proposed: 2026-08-02
related_plan: [PLAN-165, PLAN-163]
related_adr: [ADR-146, ADR-183]
---

# ADR-185 — Night-mode: Owner-invoked autonomy posture toggle (D1 bypass cut / D2 single-writer overlay / D3 resolver-derived banner)

> Status: PROPOSED — records the three design decisions forced by the
> PLAN-165 v1→v2 cross-vendor review (3-lane REJECT, artifacts in
> `.claude/plans/PLAN-165/architect/round-1/`) and confirmed by the W0
> probes (`.claude/plans/PLAN-165/probes/W0-EVIDENCE.md`). Acceptance is
> expected at the Owner-signed sentinel ceremony that lands the P1 deny
> rule and the P2 audit action (the same ceremony that unblocks W1).

## Context

The Owner needs a per-machine, reversible way to start a session in a
more autonomous posture ("arm before sleeping, disarm in the morning" —
S288, verbatim in PLAN-165 §Context) without weakening the published
fail-closed default. The tracked `.claude/settings.json` pins
`permissions.defaultMode: "manual"` + `disableAutoMode: "disable"` and
is a watched surface (tamper tripwires + bash-safety canonical-edit
vector), so the lever is the per-machine, gitignored
`.claude/settings.local.json` overlay (`.gitignore:78`), read at session
start — next-session semantics by construction; the current governed
session never changes posture.

PLAN-165 v1 proposed this toggle with a `--full` (`bypassPermissions`)
tier, a convention-only writer, and a marker-driven boot banner. All
three review lanes (codex / grok / Claude 6-lens panel) rejected v1;
verification confirmed the rejections. This ADR records the three
resulting decisions — required for an L3, VETO-domain change
(PROTOCOL.md:130, :402) — so they cannot be silently relitigated in
implementation. W0 outcomes fixed alongside them (not revisited here):
marker+snapshot live in ONE file at `<project>/.claude/state/night-mode.json`
(gitignored via `.claude/state/`, same non-commit policy ADR-183
established for `session-roots.json`); no tty gate (W0 T0.6: the Bash
rail has no tty — stdin/stdout `isatty=False`); the shipped mode is
`acceptEdits`; the command is `/night-mode`.

## Decision

### D1 — `bypassPermissions` is CUT (no `--full` tier, ever, in this feature)

A persisted `permissions.defaultMode: "bypassPermissions"` collides **by
construction** with an existing security tripwire:

- `_lib/effective_config.py:177-181` maps `permissions.defaultMode ==
  bypassPermissions` to `TAMPER_PERMISSION_BYPASS` in **any** layer —
  `_layer_paths()` includes `settings.local.json` with no exemption.
- `ceo-boot.py:1605-1620` runs `resolve_settings()` +
  `classify_tampering()`, emits `settings_tamper_detected`, and returns
  `red`.
- The behavior is test-pinned:
  `.claude/scripts/tests/test_ceo_boot_tamper_tripwires.py:255-261`
  builds exactly `{"permissions": {"defaultMode": "bypassPermissions"}}`
  in the local layer and asserts `red`
  (`settings_tamper_permission_bypass`).

Shipping a `--full` tier would therefore teach the Owner to ignore a
true tripwire, and the only way to silence it — allowlisting a
night-mode carve-out in the tamper rules — is a weakening of a security
control, which re-enters the VETO carve-out (PROTOCOL.md:436) regardless
of who suggests it.

The escape valve is the harness's own ephemeral flag, documented (W2.2)
but not implemented here:

```bash
claude --permission-mode bypassPermissions   # one session, explicit, no persistent state, no tripwire collision
```

Night-mode itself writes only `permissions.defaultMode: "acceptEdits"`.

### D2 — `.claude/settings.local.json` gets a deny rule; `night-mode.py` is the SINGLE writer (ceremony prerequisite P1)

The current deny covers `Edit(.claude/settings.json)`
(`.claude/settings.json:771`) but **not** the overlay. That is a real
escalation ladder: under `acceptEdits`, a tool Edit/Write of the overlay
is auto-accepted — and the overlay decides the next session's posture.
An agent could rewrite it and the following session would be born in a
weaker posture with nobody typing anything. Honest scope: `acceptEdits`
does not nullify deny rules and does not disarm hooks — every PreToolUse
guard (canonical-edit, bash-safety, kernel) still fires; what changes is
prompt frequency, not governance. But the one write target that controls
posture being unguarded is unacceptable for a feature whose product is
writing there.

Decision: **P1** adds `Edit(.claude/settings.local.json)` and
`Write(.claude/settings.local.json)` to `permissions.deny` in
`.claude/settings.json`, mirrored in
`templates/settings/settings.base.json` (else
`test_template_dogfood_parity` reds). Because that edit touches the
canonical-guarded settings file, it does not fit inside this plan's
waves: it is a sentinel-ceremony prerequisite, and W1 is blocked until
it lands (together with P2, the `night_mode_toggled` typed audit
action).

Design consequence: `night-mode.py` becomes the **only** writer of the
overlay, and it writes as a *process* (FileLock → same-dir temp →
`fsync` → `os.replace` → read-back; snapshot create-only; fail-CLOSED on
malformed input per the ADR-146 / CLAUDE.md §4 doctrine), never via tool
Edit/Write — so the deny rule and the writer never collide.

Supporting live evidence (W0 T0.4, positive): with a local overlay
setting only `defaultMode: acceptEdits`, a project-layer
`Read(./secret.txt)` deny was still BLOCKED by the harness — permissions
are deep-merged, so the project deny floor survives the overlay. (The
repo resolver merges shallow by top-level key — a known divergence,
codex F3/F4; see D3 for why the banner is unaffected.)

### D3 — The boot banner derives from `resolve_settings()`; the marker is decoration

v1 lit the banner from marker presence. Marker and settings are two
sources of truth that desynchronize (crash between the two writes, Owner
hand-editing the overlay). Decision: the `/ceo-boot` advisory line
derives from `_lib/effective_config.resolve_settings()` — the same
resolver the tamper tripwire consumes — and the marker
(`.claude/state/night-mode.json`) is decoration only: timestamp,
hostname, which mode night-mode wrote, plus the create-only snapshot for
`off`. `status` reconciles the two and reports disagreement instead of
picking one. The resolver-vs-harness merge divergence noted in D2 does
not affect the banner: it reports the resolved *posture*
(`permissions.defaultMode`), a scalar both merge strategies resolve
identically.

The banner is **advisory, not a guarantee**, and is not sold as one:

- `/ceo-boot` is manual — `auto_boot.py:91` requires
  `CEO_AUTO_BOOT == "1"`, which is never set;
- recommendations are capped at `recs[:5]` (`ceo-boot.py:2671`, `:2806`),
  so the line can be crowded out;
- the boot cache can return before rendering.

It is a reminder for whoever runs `/ceo-boot`, and the acceptance
criterion (PLAN-165 AC-6) asserts exactly that: line shown iff the
resolver reports a non-ratified posture.

## Consequences

- (+) The Owner arms/disarms nightly autonomy with one command,
  per-machine, without dirtying the tracked tree
  (`git status --porcelain` stays empty) and without touching the
  published default posture; templates and adopter defaults remain
  byte-identical except the deliberate P1 deny rule.
- (+) Zero tripwire regression by construction: the shipped mode
  (`acceptEdits`) is not in the tamper rules' bypass class, so
  `/ceo-boot` stays green with night-mode armed — the observable proof
  that D1 was right to cut bypass.
- (+) Every toggle is audited (`night_mode_toggled`, P2) with a scrubbed
  field set (`mode`, `previous_mode`, `result`, `hostname_hash` — never
  paths, never content), keeping `verify_chain()` green.
- (−) **Adopter installs do not gain the P1 deny rule until they
  upgrade.** The rule ships in `.claude/settings.json` (dogfood) and
  `templates/settings/settings.base.json` (new installs), but an
  existing adopter only receives it via the `upgrade.sh` settings
  migration. Until then, D2's single-writer property is dogfood-only on
  that install, and the overlay-rewrite escalation ladder remains open
  there.
- (−) Residual — the credential-read class if native deny were ever
  found not to fire. `docs/PERMISSION-MODEL-DESIGN.md:368` still marks
  "Native deny actually fires" as PENDING-LIVE at the design level; W0
  T0.4 supplies one positive live observation (deny fired under
  `acceptEdits` on CC 2.1.2xx), not a standing guarantee across harness
  versions. Should the native deny ever be found not to fire, the
  credential Read entries (`Read(~/.ssh/**)`, `Read(~/.aws/**)`,
  `~/.netrc`, the `.env` family — `.claude/settings.json:772` ff.) are
  the ones with no hook twin: under an armed night-mode session they
  would have no backstop. Recorded here instead of assuming a floor.
- (−) No tty gate exists (W0 T0.6: none is available on the Bash rail),
  so Owner presence is enforced only by P1 (agents cannot write the
  overlay) plus the CI refusal (script exits non-zero when `CI` is set,
  AC-11) — not by an interactive check.
- Semantics are next-session only: the running session never changes
  posture, and forgetting `off` is surfaced by the D3 banner (advisory)
  rather than a hard TTL (OQ2 decision: banner-only; TTL deliberately
  deferred as more state for marginal gain).
- Rollback: remove the command + script + tests, delete the marker file;
  the P1 deny rule and P2 audit action are independent hardening and can
  stay.

## References

- `.claude/plans/PLAN-165-night-mode-owner-autonomy-toggle.md` — the
  governing plan (v2, 2026-08-02); §Decisões D1–D3, §Pré-requisitos
  P1/P2, ACs.
- `.claude/plans/PLAN-165/probes/W0-EVIDENCE.md` — live probe evidence
  (T0.1 precedence, T0.2 operate-without-prompt, T0.4 deny-under-
  acceptEdits positive, T0.6 no-tty, T0.7 marker location).
- `.claude/plans/PLAN-165/architect/round-1/` — the 3-lane v1 REJECT
  consensus this ADR encodes.
- `docs/PERMISSION-MODEL-DESIGN.md:368` — PENDING-LIVE status of the
  native deny floor (residual above).
- ADR-146 (fail-closed-on-input precedent), ADR-183 (`.claude/state/`
  non-commit registry precedent).
