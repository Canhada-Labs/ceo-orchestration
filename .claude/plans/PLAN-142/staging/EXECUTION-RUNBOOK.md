# PLAN-142 — Execution Runbook (kernel ceremony)

> Prepared S245 so the execution session is short. PLAN-142 is `reviewed`.
> Everything here is a DRAFT/aid — verify against the live code + binary during
> execution (the staged code could NOT be tested in the prep session).

## Pre-flight (the execution session must start this way)

1. Relaunch the session with the kernel override in the HARNESS env (the Bash
   tool cannot set this for the hooks):

   ```
   CEO_KERNEL_OVERRIDE=plan-142-codex-0139 CEO_KERNEL_OVERRIDE_ACK=I-ACCEPT claude
   ```

   (reason slug is generic, matches `[A-Za-z0-9._-]{1,120}`; ACK is literal.)

2. Sign the sentinel (re-anchor first to the current HEAD, then sign):

   ```
   # update the Approved-By anchor + "Anchor commit" line in
   #   .claude/plans/PLAN-142/architect/round-2/approved.md to the current HEAD
   ! gpg --armor --detach-sign --yes .claude/plans/PLAN-142/architect/round-2/approved.md
   ```

   This produces approved.md.asc. Both rails already carry the Owner hot-key
   (S244 bootstrap), so no signer registration is needed.

## Apply (now the hooks allow the 5 scoped paths)

3. Create the helper: `.claude/hooks/_lib/codex_cli_shape.py` from
   `staging/codex_cli_shape.py` (review + adjust).
4. Apply `staging/check_pair_rail__invoke_and_consume.py.txt` into
   `.claude/hooks/check_pair_rail.py` (_invoke_codex_review + decide consume side).
5. Apply `staging/codex_adapter_parsers.py.txt` into
   `.claude/hooks/_lib/adapters/codex.py` (parsers delegate CLI-shape to the helper).
6. Pins:
   - `.claude/governance/codex-cli-pin.txt`: widen to admit 0.139 — suggested
     `>=0.139.0,<0.140.0` (pin to the validated minor) or `>=0.128.0,<0.140.0`
     (keep the wide range). Decide at execution.
   - `.claude/governance/codex-cli-binary-sha256.txt`: re-pin to
     `d3be844c45c4fd89392536e56e1010963f94785592596b50cd0c45bb8a341406`
     (computed S245; RE-VERIFY with `shasum -a 256 $(which codex)`).
7. Non-kernel (no ceremony): `.claude/scripts/codex_invoke.py` stdin=DEVNULL on
   both subprocess.run; `.claude/scripts/substrate-watch.json` add a `codex_cli`
   component (watch_for: exec flag surface — --color, -s/--sandbox enum, -o,
   --output-schema, --json, the --read-only/--no-color/--strict-json removals).

## Verify (V1 deterministic)

8. `python3 .claude/scripts/check-stdlib-only.py` (411+ OK).
9. New/updated tests: offline golden-fixture (captured 0.139 -o file → redact →
   parse_verdict_strict → verdict; forged-PASS → ADVISORY; oversize; symlink-refusal;
   empty; exit≠0). `CEO_PAIR_RAIL_FIXTURE_RESPONSE`-injected decide() test.
10. Grep gate (D2): no CLI literal (`exec`, `--[a-z]`, `gpt-5*`/`o3*`/`o4*`,
    `_VALID_MODELS`) left in check_pair_rail.py or codex.py — all via the helper.
11. `bash .claude/scripts/validate-governance.sh` (full) exits 0.
12. Real pair-rail smoke: a Stop/PreToolUse run returns a verdict, not CodexUnavailable.

## Ship (V2 + V3)

13. Cross-model pass on the diff: `codex exec review --uncommitted` (bootstrap) +
    Owner human review (R-SEC-6).
14. Release coupling: regenerate `pair-rail-verdict-<tag>.md` (recomputed
    inputs_hash — both kernel files are in pair-rail-inputs-hash-manifest.txt) OR
    record `CEO_PAIR_RAIL_VERDICT_OPTIONAL=1` for the first post-edit release.
15. ADR-111: run the locked-corpus catch_rate check OR defer with a rationale
    naming the security consequence (model-behavior change gpt-5.5↔gpt-5-codex).
16. Owner-GPG commit; transition PLAN-142 → done with related_commits.

## Acceptance criteria source of truth

`.claude/plans/PLAN-142-codex-cli-0139-adapter-migration.md` §3 (15 ACs) + §4
(D1-D5). This runbook is the ordering aid, not a substitute for the ACs.
