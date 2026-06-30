---
round: 2
archetype: Staff Security Engineer
skill: security-and-auth
generated_at: 2026-06-19
---

## Verdict

ADJUST

## Summary

- RE-SCOPE CORRECT (grounded): live rail = check_pair_rail.py:407 `exec --read-only -`; 0.139 help has no --read-only → exit 2 on every L2+ edit. 4 kernel paths + pin gap verified on disk.
- D1 premise REAL: `-o/--output-last-message` exists; one structured object is sound + lower churn.
- CORE ADJUST: the live rail does NOT use parse_verdict/_VALID_VERDICTS — it free-text-scans raw stdout via _detect_write_shaped_patch → binary block/accept. The R-SEC-1/R-SEC-2 ACs target codex.py parsers that have ZERO live callers. And verdict-forgery defense is the binary-SHA pin, NOT the structured object.

## Risks

- **R-SEC-1 — HIGH.** Redaction-before-parse AC lands on the wrong surface (codex.py, non-live). With D1 the ingress is a FILE read in check_pair_rail.py. *Mitigation:* retarget — read file → single-pass redact → THEN json.loads/detect; PEM-in-summary golden test.
- **R-SEC-2 — HIGH.** 'Structured-only verdict' AC doesn't wire into the live rail (which uses _detect_write_shaped_patch, never reads a verdict field). *Mitigation:* D1 must state the live rail json.loads (post-redaction) + routes through parse_verdict_strict (verdict∈_VALID_VERDICTS, fail-CLOSED-to-ADVISORY); decide _detect_write_shaped_patch's fate; adversarial free-text-'PASS' → ADVISORY test.
- **R-SEC-3 — HIGH.** Forged-verdict mis-attributed: a swapped binary (T-8) owns 100% of the -o file → structured {verdict:PASS} is no harder to forge than free text. The real defense is codex-cli-binary-sha256.txt, enforced only at release-time (not runtime in _resolve_codex_bin). *Mitigation:* add a runtime SHA check (possible 5th kernel touch) OR state in writing the structured object is NOT the T-8 defense + record the runtime gap as accepted risk.
- **R-SEC-4 — MEDIUM.** tmpfile = new vector: the UNTRUSTED binary WRITES the file we read → symlink/TOCTOU. *Mitigation:* tempfile.mkdtemp(0o700); rail creates file O_CREAT|O_EXCL|0o600 + absolute path; refuse symlink/non-regular/not-owned; redact-then-read; finally unlink + rmdir; test symlink-refusal + unlink-on-timeout.
- **R-SEC-5 — MEDIUM.** Dropping --json drops parse_usage telemetry — but it has ZERO live-rail callers, so live blast radius is NIL. *Mitigation:* consciously DROP usage on the live rail; keep --json only on the non-kernel promotion path; do NOT add a parallel --json to check_pair_rail.py.
- **R-SEC-6 — MEDIUM.** Bootstrap self-review gap persists. *Mitigation:* promote the offline golden-fixture test (captured 0.139 file → redact → parse_verdict_strict) to P0; keep Owner human review.
- **R-SEC-7 — LOW.** ADR-111 deferral must name the SECURITY consequence (reduced detection sensitivity), not just process.

## Must-fix (blocking)

1. R-SEC-1/2: D1/§3 must state check_pair_rail reads the file → single-pass redact → json.loads + schema-validate verdict∈_VALID_VERDICTS via parse_verdict_strict (fail-CLOSED-to-ADVISORY) → decide _detect_write_shaped_patch's fate. The current ACs bind only codex.py (dead for the rail).
2. R-SEC-1/3: retarget the redaction AC to the live-rail file-read site; PEM-with-CPF golden test (masked AND parseable).
3. R-SEC-4: binding tmpfile-hygiene P0 AC (mkdtemp 0700, O_EXCL, symlink-refusal, finally unlink+rmdir; test symlink + unlink-on-timeout).
4. R-SEC-3: state the binary-SHA pin (release-time) is the T-8 defense, NOT the structured object; add runtime SHA check or record the mid-session PATH-decoy gap as accepted risk.

## Nice-to-have (advisory)

1. Promote the offline golden-fixture test P1→P0 (kernel edit can't be dogfooded + repins the T-8 SHA).
2. DROP usage telemetry on the live rail (no consumer); keep --json only on the non-kernel path.
3. ADR-111 deferral rationale names the security consequence.
4. Confirm the structured-verdict review prompt is egress-redacted + instructs 'emit ONLY the JSON object as the last message'.

## Unseen by the original plan

1. (biggest) the live rail's 'verdict' is _detect_write_shaped_patch (free-text) → binary block/accept; parse_verdict/_VALID_VERDICTS have NO live caller. The structured-only security argument aims at code the rail doesn't run.
2. parse_usage has zero live-rail callers — the telemetry worry is a near-no-op for the rail.
3. under T-8, the untrusted binary WRITES the -o file → symlink/TOCTOU surface the stdin design didn't have.
4. runtime binary-SHA gap: _resolve_codex_bin doesn't hash at invocation; repinning the SHA doesn't close the mid-session decoy vector.

## What I would NOT change

1. The re-scope (live rail = check_pair_rail.py, --read-only rejected, 4 kernel paths, pin gap) — verified; don't re-open.
2. D1 (--output-last-message over JSONL) — right altitude; keep with hardening.
3. CLI-shape in a non-kernel helper, trust logic in the kernel — correct separation.
4. fail-open-to-ADVISORY (ADR-106) + fail-CLOSED outgoing redaction (ADR-114) — both preserved.
5. Owner human review + manual workaround as interim bootstrap — sound.
6. 4-path KERNEL ceremony + ADR-111 obligation as explicit budget — correct.
