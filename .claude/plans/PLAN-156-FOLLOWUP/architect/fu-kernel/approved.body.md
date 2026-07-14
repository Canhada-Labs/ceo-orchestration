# FU-KERNEL — PLAN-156-FOLLOWUP F3 guard glob + F5 canonical-path oracle

Own commit segment (consensus C3): `check_canonical_edit.py` is a
`_KERNEL_PATHS` entry — this is the widest-blast-radius change of the
follow-up and must be independently rollback-able. The landing ceremony
exports `CEO_KERNEL_OVERRIDE=PLAN-156-FOLLOWUP-GUARD-GLOB` +
`CEO_KERNEL_OVERRIDE_ACK=I-ACCEPT` for THIS segment only (unset
immediately after; declared here per ADR-031 audit discipline).

- **F3 — workflows guarded as a CLASS**: the PLAN-156 guard covered only
  the exact paths `council-audit.js` + `council.md`; a sibling/new
  `.claude/workflows/*.js` was ordinary-writable — and a file we choose
  not to ship is exactly the file an attacker would CREATE to get a
  second egress-bearing workflow past the sentinel gate. The guard list
  now carries the `.claude/workflows/**/*.js` class glob (subdirs
  included; `**` matches zero or more components). No redundant
  `_CANONICAL_PREFIXES` add (`.claude` is already fast-pathed). OQ1
  Owner-ratified S270. The ceremony preflight proves the class behavior
  through the oracle (sibling + nested probe paths classify canonical)
  BEFORE this sentinel is signed.
- **F5 — fingerprint parity via a single-source oracle (C2, unanimous +
  security VETO lines)**: the grok pre-push review gate hashed COARSE
  per-commit first-segment paths while the Stop-review recorder hashed
  the fine `_is_canonical` working-tree set — structurally unmatchable
  fingerprints. Fix, all C2 parts: (a) BOTH sides aligned UP to the fine
  set — never down (coarse fingerprints are collision-prone →
  review-reuse bypass; coarse also under-triggers on `templates/**`,
  `.grok/**`, `.codex/**`, `AGENTS.md` — the egress/disarm surfaces);
  (b) new read-only `--is-canonical` oracle CLI on
  `check_canonical_edit.py` — the gate shells out
  (`templates/grok/pre-push-review-gate.sh`), the recorder keeps
  importing; re-implementing the glob list in bash IS the drift class
  being fixed. Hook semantics byte-identical when invoked with empty
  argv; (c) the gate aggregates the WHOLE pushed range into ONE
  fingerprint (matching the recorder aggregate); parity test exercises a
  multi-commit push; (d) oracle failure → coarse fallback = over-trigger
  = fail-CLOSED, and a per-path classification fault reports canonical
  (1); (e) coverage delta enumerated below — narrowing a security gate
  is never silent.

**Coverage delta (C2(e), signed record; machine-checked by
`test_fingerprint_parity.py::OracleCliContractTest::test_coverage_delta_fine_vs_coarse`;
full narrative in the local ceremony record
`.claude/plans/PLAN-156-FOLLOWUP/staged/coverage-delta-f5.md`):**

- GAINED (coarse waved through, now review-gated): `.codex/hooks.json`,
  `.codex/config.toml`, `.codex/rules/ceo.rules`, `requirements.toml`,
  `AGENTS.md`, `.grok/hooks/*.json` + `.grok/hooks/**/*.json`,
  `.grok/config.toml`, `.grok/sandbox.toml`, `.grok/rules/*.md`,
  `templates/settings/settings.base.json` + `templates/settings/*.json`
  — the kill-switch / reviewer-contract / council-containment /
  fail-open-bearing distribution surfaces.
- LOST (coarse-classifier noise, never sentinel-gated at edit time):
  first-segment-canonical paths matching NO guard pattern — plan
  documents outside `spec.md`/`corpus/locked/**`/`canonical/*`,
  non-guarded `.claude/commands/*.md` (except `council.md`),
  non-guarded `.claude/scripts/*`, `.claude/docs/**`, `.github`
  non-workflow files, `SPEC` non-markdown.
- Granularity rider (C2(c)): sidecar acceptance is now aggregate
  whole-range; per-commit acceptance survives only via the
  `Pair-Rail-Reviewed: APPROVE` trailer path.
- Fallback retention (C2(d)): the coarse classifier survives inside the
  gate solely as the oracle-failure fallback; its fingerprint
  intentionally cannot match a recorder record — a broken oracle
  degrades to trailer-only acceptance, never to a bypass.

Proof (ceremony preflight, staged mode, before signing; re-run
post-apply in canonical mode): named W3 set green
(`test_codex_stop_review.py` + `test_grok_trust_probe.py` +
`test_fingerprint_parity.py` 46/46; `hooks/tests -k "canonical or
python_hook"`); oracle behavioral probe (guarded workflow=1, sibling
`.js`=1, nested `.js`=1, `council.md`=1, non-canonical=0, exit 0);
shellcheck -S warning clean on the gate; staged copy basepin-verified
against canonical sha256 (abort on drift).

<!-- BEGIN SIGNED SCOPE -->
Approved-By: @Canhada-Labs AE9B236FDAF0462874060C6BCFCFACF00335DC74
Anchor-SHA: __ANCHOR_SHA__
Plans: PLAN-156-FOLLOWUP
Kernel-Override: PLAN-156-FOLLOWUP-GUARD-GLOB (CEO_KERNEL_OVERRIDE +
  CEO_KERNEL_OVERRIDE_ACK=I-ACCEPT exported for this segment only,
  unset after — consensus C3, ADR-031)
Scope:
  - .claude/hooks/check_canonical_edit.py
  - templates/grok/pre-push-review-gate.sh
  - .claude/scripts/tests/test_fingerprint_parity.py
<!-- END SIGNED SCOPE -->
