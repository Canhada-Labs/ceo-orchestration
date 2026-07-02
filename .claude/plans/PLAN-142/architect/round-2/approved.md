# PLAN-142 — Architect Sentinel (round 2, terminal)

Authorizes the canonical + kernel edits to restore the Codex pair-rail on
codex-cli 0.139.0 (PLAN-142, status reviewed after a 2-round debate). Four of the
five scoped paths are arbitration-kernel (KERNEL-HARD-DENY): editing them needs,
IN ADDITION to this Owner-signed sentinel, `CEO_KERNEL_OVERRIDE=<reason-slug>` +
`CEO_KERNEL_OVERRIDE_ACK=I-ACCEPT` in the harness environment (set at session
launch — the Bash tool cannot set it for the hooks). The fifth path
(`_lib/codex_cli_shape.py`, NEW) is canonical-guarded but NOT kernel.

> **Anchor note:** the anchor below is the `main` HEAD this work branched from. At
> EXECUTION, re-anchor to the then-current HEAD (the committed reviewed plan +
> staging) and re-run `gpg --armor --detach-sign --yes approved.md` so the `.asc`
> matches — a rewritten approved.md invalidates the old signature.

Anchor commit 22644d84b73430a69bb788f97d9fe9751ca51b45 is the execution HEAD
(committed reviewed plan + staging, branch `plan-142-reviewed`) this sentinel was
re-anchored to at execution (S246). It descends from the `main` HEAD
1444caa00f072a2401b94bd1fe039b473cfcbf00 this sentinel was originally drafted
against.

<!-- BEGIN SIGNED SCOPE -->
Approved-By: @Canhada-Labs 22644d84b73430a69bb788f97d9fe9751ca51b45
Plans: PLAN-142
Scope:
  - .claude/hooks/check_pair_rail.py
  - .claude/hooks/_lib/adapters/codex.py
  - .claude/hooks/_lib/codex_cli_shape.py
  - .claude/governance/codex-cli-pin.txt
  - .claude/governance/codex-cli-binary-sha256.txt
<!-- END SIGNED SCOPE -->

Authorization: Owner-signed GPG detached signature (approved.md.asc), signer
fingerprint AE9B236FDAF0462874060C6BCFCFACF00335DC74, verified against both signer
rails (.claude/sentinel-signers.txt + the ADR-121 YAML registry). **The .asc is
generated at EXECUTION time, not now** — this file is committed unsigned as a
prepared draft; the Owner signs it in the execution session.

Kernel-override note: paths 1, 2, 4, 5 are in `_KERNEL_PATHS`
(check_arbitration_kernel.py:155/170/199/200). The sentinel alone does NOT grant
them — the harness must ALSO carry `CEO_KERNEL_OVERRIDE` + `..._ACK=I-ACCEPT`
(a generic reason slug + the ACK; not a per-path token). That env requires a
session relaunch. Path 3 (`_lib/codex_cli_shape.py`) is canonical-guarded only —
this sentinel covers it.

Rationale by path:
  - check_pair_rail.py — replace the broken inline `exec --read-only -` argv with
    a codex_cli_shape-built argv (-o tmpfile); rewrite the consume side to read +
    redact + parse_verdict_strict; tmpfile TOCTOU hygiene; _detect_write_shaped_patch
    demoted to secondary.
  - _lib/adapters/codex.py — parse the -o last-message file (one redacted object,
    structured-only); rewrite parse_usage per-line; delegate ALL CLI-shape to the
    helper (no CLI literals left in this kernel file).
  - _lib/codex_cli_shape.py (NEW, non-kernel) — the single argv builder + model
    list + dead-flag migration; makes the next codex-cli bump a non-kernel edit.
  - codex-cli-pin.txt — widen the range to admit 0.139.x.
  - codex-cli-binary-sha256.txt — re-pin to the trusted 0.139 binary
    (d3be844c45c4fd89392536e56e1010963f94785592596b50cd0c45bb8a341406, computed
    S245 from `shasum -a 256 $(which codex)`; RE-VERIFY at execution).

ADR-111: the 0.128→0.139 jump (+ possible reviewer-model change) is large — run
the locked-corpus catch_rate check OR defer with a rationale naming the security
consequence. Release-time: regenerate pair-rail-verdict-<tag>.md (recomputed
inputs_hash, since both kernel files are in pair-rail-inputs-hash-manifest.txt) OR
ship the first post-edit release under CEO_PAIR_RAIL_VERDICT_OPTIONAL=1 recorded.
