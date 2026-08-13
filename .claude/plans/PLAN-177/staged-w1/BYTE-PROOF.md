# BYTE-PROOF — PLAN-177 W1 (P1-1 / CF-9)

Generated: 2026-08-13T15:21:46Z  ·  clone HEAD: ba19bcc25a60c2946002e54f8edf35a15a97dd5c

Function bodies are EXTRACTED from each real script (`git show HEAD:`
for OLD, working tree for NEW), sourced into an identical harness, and
stdout / stderr / .gitignore / journal compared with `cmp`.

## A. install.sh OLD (@HEAD) vs NEW (via generator) — root .gitignore

`install_mcp_secrets_dir` and `install_posture_state_ignores` are run in
install.sh's own order (secrets first, then posture) on the same seed.

| scenario | DRY_RUN | stdout | stderr | .gitignore | journal | rc |
|---|---|---|---|---|---|---|
| s1_absent | 0 | OK | OK | OK | OK | OK(0) |
| s1_absent | 1 | OK | OK | OK(absent) | OK | OK(0) |
| s2_empty | 0 | OK | OK | OK | OK | OK(0) |
| s2_empty | 1 | OK | OK | OK | OK | OK(0) |
| s3_unrelated | 0 | OK | OK | OK | OK | OK(0) |
| s3_unrelated | 1 | OK | OK | OK | OK | OK(0) |
| s4_mcp_only | 0 | OK | OK | OK | OK | OK(0) |
| s4_mcp_only | 1 | OK | OK | OK | OK | OK(0) |
| s5_posture_a | 0 | OK | OK | OK | OK | OK(0) |
| s5_posture_a | 1 | OK | OK | OK | OK | OK(0) |
| s6_all_three | 0 | OK | OK | OK | OK | OK(0) |
| s6_all_three | 1 | OK | OK | OK | OK | OK(0) |
| s7_substring | 0 | OK | OK | OK | OK | OK(0) |
| s7_substring | 1 | OK | OK | OK | OK | OK(0) |
| s8_no_trail_nl | 0 | OK | OK | OK | OK | OK(0) |
| s8_no_trail_nl | 1 | OK | OK | OK | OK | OK(0) |
| s9_adopter_edited_comment | 0 | OK | OK | OK | OK | OK(0) |
| s9_adopter_edited_comment | 1 | OK | OK | OK | OK | OK(0) |

## B. install vs upgrade — identical root .gitignore bytes

Route B seeds the scenario, then runs the upgrade block. Route A seeds
the same scenario and runs install's two functions.

The .gitignore BYTES must match — that is the P1-1 claim. The JOURNALS
must NOT: install records `ensure_mcp_secrets_dir` because it also
creates `state/mcp_client_secrets` at mode 0700, while upgrade records
`ensure_mcp_secrets_ignore` because it delivers only the ignore entry.
Different actions, different op names. The shared action (posture) IS
compared, and the asymmetric one is asserted to stay named apart.

| scenario | .gitignore bytes | posture journal line | mcp op named apart |
|---|---|---|---|
| s1_absent | OK | OK | OK |
| s2_empty | OK | OK | OK |
| s3_unrelated | OK | OK | OK |
| s4_mcp_only | OK | OK | OK |
| s5_posture_a | OK | OK | OK |
| s6_all_three | OK | OK | OK |
| s7_substring | OK | OK | OK |
| s8_no_trail_nl | OK | OK | OK |
| s9_adopter_edited_comment | OK | OK | OK |

## C. `--ceremony user`: root blocks skipped on BOTH routes

- upgrade, ceremony=user: root .gitignore UNCHANGED — OK
```

==> Refreshing root .gitignore framework blocks (PLAN-019 P2-SEC-H + PLAN-165 CX-3)
    SKIP: root .gitignore blocks (recorded --ceremony user install — install.sh writes no root files either)
```
- install.sh gate INTACT: `if [[ "$CEREMONY" != "user" ]]; then install_mcp_secrets_dir; fi` — OK
- install.sh gate INTACT: `if [[ "$CEREMONY" != "user" ]]; then install_posture_state_ignores; fi` — OK
- install.sh calls `install_claude_dir_gitignore` UNGATED (all ceremonies) — OK

## D. `.claude/.gitignore` — same bytes on both routes, never rewritten

- ceremony=maintainer: install and upgrade wrote IDENTICAL .claude/.gitignore — OK
- ceremony=user: install and upgrade wrote IDENTICAL .claude/.gitignore — OK
- an adopter-edited .claude/.gitignore is PRESERVED byte-for-byte — OK

Delivered body:
```
# Delivered by ceo-orchestration (PLAN-177 W1 / CF-9).
#
# Per-machine posture + runtime state that must never reach VCS:
#   state/             runtime state as a whole (PLAN-163 T3.1)
#   settings.local.json  permission overlay deciding the NEXT session's
#                        posture (PLAN-165)
#
# The root .gitignore carries the same exclusions for adopters who track
# this tree from the repository root. This file additionally covers the
# --ceremony user install, which never writes outside .claude/ and so
# never received them.
#
# Adopter-owned once created: install and upgrade create it only when it
# is absent, and NEVER rewrite it.
/state/
/settings.local.json
```

## E. Idempotence — upgrade root block run twice

- s1_absent: 2nd run is a no-op; entry counts 1/1/1 — OK
- s3_unrelated: 2nd run is a no-op; entry counts 1/1/1 — OK
- s5_posture_a: 2nd run is a no-op; entry counts 1/1/1 — OK
- s6_all_three: 2nd run is a no-op; entry counts 1/1/1 — OK
- s9_adopter_edited_comment: 2nd run is a no-op; entry counts 1/1/1 — OK
- deliberate deletion of one entry is RE-APPENDED on the next run — OK (intended posture, see NOTES.md)

## E2. Idempotence on the install route, and install then upgrade (v2)

- s1_absent: install x2 then upgrade is a no-op after the 1st; counts 1/1/1 — OK
- s3_unrelated: install x2 then upgrade is a no-op after the 1st; counts 1/1/1 — OK
- s6_all_three: install x2 then upgrade is a no-op after the 1st; counts 1/1/1 — OK
- s9_adopter_edited_comment: install x2 then upgrade is a no-op after the 1st; counts 1/1/1 — OK
- adopter-edited header comments PRESERVED; no framework block re-appended — OK

Resulting file for the adopter-edited scenario (unchanged by 3 runs):
```
# our own note about the mcp secret store
state/mcp_client_secrets/

# per-machine state -- do not commit (edited by us)
.claude/state/

# ditto
.claude/settings.local.json
```

## F. Positive control — the harness must go RED on a planted mutation

- posture_header_hoisted (in s3_unrelated): detected — OK
- posture_entry_dropped (in s3_unrelated): detected — OK
- mcp_create_gains_blank (in s1_absent): detected — OK
- mcp_append_loses_blank (in s3_unrelated): detected — OK
- mcp_entry_changed (in s3_unrelated): detected — OK

## Sample — s3_unrelated, real run, NEW route

### install stdout
```

==> MCP secrets directory (P2-SEC-H)
    ENSURED: /private/tmp/claude-501/-Users-joaocanhada-canhada-labs-ceo-orchestration/b53cf2f0-4722-450c-9fa9-36b4bfc1544a/scratchpad/w1b/bp-final/work/s3_unrelated.d0.new/state/mcp_client_secrets (mode 0700)

    NOTE: this directory stores HMAC shared secrets for MCP clients.
          File perms MUST be 0600; auth.load_secret() fail-closes otherwise.
          DO NOT commit its contents to VCS.
    APPENDED to .gitignore: state/mcp_client_secrets/

==> Posture-state .gitignore entries (PLAN-165 CX-3)
    APPENDED to .gitignore: .claude/state/
    APPENDED to .gitignore: .claude/settings.local.json
```
### upgrade stdout (root block)
```

==> Refreshing root .gitignore framework blocks (PLAN-019 P2-SEC-H + PLAN-165 CX-3)
    APPENDED to .gitignore: state/mcp_client_secrets/
    APPENDED to .gitignore: .claude/state/
    APPENDED to .gitignore: .claude/settings.local.json
```
### resulting root .gitignore
```
node_modules/
*.log

# PLAN-019 P2-SEC-H: MCP shared-secret store (never commit)
state/mcp_client_secrets/

# PLAN-165 CX-3: per-machine posture/runtime state (never commit)
.claude/state/

# PLAN-165 CX-3: per-machine posture/runtime state (never commit)
.claude/settings.local.json
```

## VERDICT: **ALL CHECKS PASS**
