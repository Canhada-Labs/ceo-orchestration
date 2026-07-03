# v1.0.1 Codex Release Re-pass — verdict record (ADR-095 gate #6)

External pair-rail release re-pass run inside the `v1.0.1-rc.1` RC-hold
window (ADR-007), S260, 2026-07-03. Reviewer: codex-cli (`codex exec`,
read-only sandbox), full release diff piped via stdin.

## Round 1 — diff `489f020..07ad298` — REJECT

- **Finding 1 (security):** `check_read_injection.py` capped the
  `CEO_UNICODE_HARDBLOCK=1` scan at `_UNICODE_SCAN_CAP_CHARS` (1 MiB) —
  invisible/bidi/Tag-block payloads past the cap fail-opened the OPT-IN
  fail-closed Read guard. Introduced by the economics-02 hot-path fix.
- **Finding 2 (process):** the PLAN-152 Wave G fresh-session pair-rail
  probe checkbox was still unchecked at review time.
- Verdict line: `RELEASE-REPASS: REJECT` (~174k tokens).

## Remediation (this round-2 bundle)

- Finding 1 → streaming chunked scan under the armed flag (whole-file
  coverage; flag-off path untouched); RED-first tests (stream coverage +
  past-cap block probe). Owner-signed sentinel (`approved.md` + `.asc`);
  `_KERNEL_PATHS`-guarded file applied by the Owner via
  `git apply fix.patch` (S258 patcher precedent). Commit `2bac7c0`.
- Finding 2 → probe Check run verbatim in the fresh closeout session;
  checkbox closed with the evidence inline in the plan.

## Round 2 — diff `489f020..2bac7c0` — APPROVE

Prompt asked the reviewer to verify BOTH R1 findings remediated and that
the remediation introduces no new regression or fail-open.

- Verdict line: `RELEASE-REPASS: APPROVE` (~178k tokens).

GA ships from `2bac7c0` (tag creatordate ≥24h after `v1.0.1-rc.1`).
