---
plan: PLAN-142
round: 2
rounds_synthesized: [round-1, round-2]
agents_considered: [vp-engineering, security-engineer, devops-engineer]
decisions_revised_in_plan:
  - "§1 — full 0.139 dead-flag set (--no-color/--read-only/--strict-json/--resume)"
  - "§2 — 5th entanglement: pair-rail-inputs-hash-manifest + release.yml step-15 verdict regen"
  - "§3 — live-rail consume rewrite (parse_verdict_strict), tmpfile TOCTOU hygiene, single shape helper, grep gate, --output-schema, usage convergence"
  - "§4 — D1..D5 ratified (output-last-message + non-kernel shape helper + secondary patch-scan + binary-SHA T-8 attribution + loud model-id)"
synthesized_at: 2026-06-19
synthesized_by: CEO
verdict_label: design-coherent (round-2 3×ADJUST; all must-fixes folded)
---

> Synthesis consumed anonymized critiques (Critic-A/B/C; map in
> `anonymization-map.md`). Round-2 verdicts: 3×ADJUST (no REJECT). All three
> independently re-validated the re-scope + D1 against the live 0.139 binary.

## Consensus findings (2+ critics flagged) — all folded into the plan

- **CR1 (A,B,C).** Re-scope CORRECT + D1 SOUND, both verified on 0.139
  (`--read-only` gone, `-o/--output-last-message` works, `--color never` valid).
  → §1, §4 D1.
- **CR2 (A,C).** Telemetry is a FALSE dilemma — `--json` + `-o` compose. Resolved:
  live rail `-o`-only (drop usage, no consumer per B); promotion path keeps `--json`
  with `parse_usage` rewritten per-line. → §3 output-contracts AC, §4 D1.
- **CR3 (A,B,C).** Single argv builder must be the NON-kernel shape helper (not
  make_invoke_command, which emits the rejected shape); move `_VALID_MODELS` + model
  literals out of the kernel; grep gate proves zero CLI literals remain. → §3 helper
  ACs + grep gate, §4 D2.
- **CR4 (A,B,C).** Live rail has NO structured-verdict consumption today
  (`_detect_write_shaped_patch` free-text scan); R-SEC-2 is currently VIOLATED by
  the rail. Resolved: rail consumes the `-o` file → redact → `parse_verdict_strict`;
  patch-scan demoted to secondary defense. → §3 consume AC, §4 D3.
- **CR5 (A,B,C).** tmpfile threat surface — the UNTRUSTED binary is the WRITER
  (TOCTOU/symlink). Resolved: mkdtemp 0700 + O_EXCL + symlink-refusal + finally
  unlink; degradation matrix → ADVISORY. → §3 tmpfile-hygiene AC.

## Single-agent insights kept

1. **Critic-C (R-OPS-1):** inputs-hash replay manifest = 5th entanglement; release
   step-15 blocks unless a fresh post-edit verdict file is produced. → §2.
2. **Critic-C (R-OPS-2):** `--strict-json` + `--resume` also dead on 0.139 (verified)
   — full dead-flag audit in the helper. → §1, §3.
3. **Critic-B (R-SEC-3):** the binary-SHA pin (not the structured object) is the T-8
   defense; runtime gap is accepted risk. → §3, §4 D4.
4. **Critic-A/C (--output-schema):** CLI-enforced structured-verdict backstop. → §3 P1.
5. **Critic-B (R-SEC-6):** offline golden-fixture test promoted P1→P0 (can't dogfood
   the broken rail). → §3 tests.

## Single-agent insights rejected / deferred

- None rejected. Runtime binary-SHA enforcement (R-SEC-3 option a) DEFERRED to a
  follow-up rather than added as a 5th kernel touch this ceremony (D4) — recorded as
  accepted risk with the release-time SHA pin + Owner review + manual workaround as
  interim controls.

## Plan adjustments (index; edits live in PLAN-142.md)

1. §1 — full 0.139 dead-flag set; live-rail consume reality (free-text scan).
2. §2 — 5 entanglements (4 kernel paths + inputs-hash manifest/verdict regen);
   ADR-111 deferral must name the security consequence.
3. §3 — live-rail consume rewrite, tmpfile TOCTOU hygiene, single shape helper +
   grep gate, redaction retarget, structured-only verdict, loud model-id, output
   contracts converge on `-o`, --output-schema, P0 offline fixtures.
4. §4 — D1..D5 ratified.

## Round verdict

**PROCEED (design-coherent).** Round-2 returned 3×ADJUST with NO REJECT and NO
ESCALATE; every must-fix is concrete and has been folded into §3/§4 (no open design
question remains — D1..D5 are decided). Plan moves `draft → reviewed`. Per
DEBATE-SCHEMA §13 this certifies INTERNAL design-coherence only (V0); it does NOT
authorize shipping — execution still runs the KERNEL-HARD-DENY ceremony, then V1
(tests/CI) → V2 (Codex pair-rail, restored or manual + Owner review) → V3 (Owner
GPG). A round-3 was judged unnecessary: the residual items are implementation ACs,
not unresolved design forks.
