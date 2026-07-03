# PLAN-152 — Canonical-Edit Sentinel (round 2 — GA re-pass fix)

Authorizes the single guarded edit remediating finding 1 of the Codex release
re-pass R1 REJECT (S260 tag ceremony, recorded in PLAN-152 §Closeout): the
economics-02 capped unicode re-read silently fail-opened the OPT-IN
fail-closed Read guard (`CEO_UNICODE_HARDBLOCK=1`) for payloads past
`_UNICODE_SCAN_CAP_CHARS` (1 MiB). Fix = stream the WHOLE file in cap-sized
chunks under the armed flag — detection is per-code-point
(control / bidi / zero-width / Tag-block), so chunking is exact — while the
default flag-off path keeps the economics-02 zero-cost gate-first behavior.

Anchor commit d0b6c30ce38b9ab64cf12f714b8ef09d4ad10f5e is the repo HEAD this
sentinel was signed against.

<!-- BEGIN SIGNED SCOPE -->
Approved-By: @Canhada-Labs d0b6c30ce38b9ab64cf12f714b8ef09d4ad10f5e
Plans: PLAN-152
Scope:
  GA re-pass fix (Codex R1 REJECT finding 1 — hardblock cap fail-open):
  - .claude/hooks/check_read_injection.py
<!-- END SIGNED SCOPE -->

Authorization: Owner-signed GPG detached signature (approved.md.asc), signer
fingerprint AE9B236FDAF0462874060C6BCFCFACF00335DC74, verified against both
signer rails (.claude/sentinel-signers.txt + the ADR-121 YAML registry).

Kernel-override note (corrected after a live probe — the first draft of this
sentinel claimed otherwise): `check_read_injection.py` IS in `_KERNEL_PATHS`
(ARBITRATION-KERNEL-BLOCKED on the Edit attempt; PLAN-019 P1-SEC-A — no
sentinel escape). This closeout session was NOT launched with the
`CEO_KERNEL_OVERRIDE` + `CEO_KERNEL_OVERRIDE_ACK` pair (mid-session exports
never reach hook invocations), so the sanctioned fallback is the S258
patcher-precedent: the OWNER applies the exact authorized diff by hand —
`git apply .claude/plans/PLAN-152/architect/round-2/fix.patch` — with the
diff itself committed alongside this sentinel as round-2 evidence. The human
executing the write is precisely the property the kernel rail exists to
guarantee (a sub-agent cannot forge it).

Deliberate exclusions (NOT authorized by this sentinel; not canonical-guarded,
land direct): `hooks/tests/**` (test updates), `CHANGELOG.md`,
`.claude/plans/**` (closeout narration).

Rationale by path:
  - .claude/hooks/check_read_injection.py — replace the single capped read
    (:357-371) with a chunked full-file streaming scan under the armed flag;
    block on first detection in any chunk. Zero behavior change with the flag
    unset (gate-first short-circuit is untouched). Manual
    `codex exec` APPROVE on the patch recorded in the commit message
    (pair-rail discipline for guarded commits, `37867c2` precedent).
