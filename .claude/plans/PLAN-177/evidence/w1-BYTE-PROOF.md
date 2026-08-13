# BYTE-PROOF — install_posture_state_ignores (OLD @HEAD vs NEW via generator)

Generated: 2026-08-13T13:44:37Z
Clone HEAD: 3842d4fc3cebadec2aee59dcf96d01df858bf17e

Method: the function body is EXTRACTED from each real install.sh
(`git show HEAD:` vs working tree) — never retyped — sourced into an
identical harness, and stdout / stderr / resulting .gitignore / journal
are compared with `cmp` for every scenario.

## Results

| scenario | DRY_RUN | stdout | stderr | .gitignore | journal |
|---|---|---|---|---|---|
| s1_absent | 0 | OK | OK | OK | OK |
| s1_absent | 1 | OK | OK | OK(absent) | OK |
| s2_empty | 0 | OK | OK | OK | OK |
| s2_empty | 1 | OK | OK | OK | OK |
| s3_unrelated | 0 | OK | OK | OK | OK |
| s3_unrelated | 1 | OK | OK | OK | OK |
| s4_first_only | 0 | OK | OK | OK | OK |
| s4_first_only | 1 | OK | OK | OK | OK |
| s5_second_only | 0 | OK | OK | OK | OK |
| s5_second_only | 1 | OK | OK | OK | OK |
| s6_both | 0 | OK | OK | OK | OK |
| s6_both | 1 | OK | OK | OK | OK |
| s7_substring | 0 | OK | OK | OK | OK |
| s7_substring | 1 | OK | OK | OK | OK |
| s8_no_trailing_nl | 0 | OK | OK | OK | OK |
| s8_no_trailing_nl | 1 | OK | OK | OK | OK |

## install vs upgrade — same .gitignore bytes (the P1-1 claim)

| scenario | ceremony | install .gitignore == upgrade .gitignore |
|---|---|---|
| s1_absent | maintainer | OK |
| s3_unrelated | maintainer | OK |
| s4_first_only | maintainer | OK |
| s6_both | maintainer | OK |

## `--ceremony user`: no delivery on either route

- upgrade `--ceremony user`: .gitignore UNCHANGED — OK
```

==> Refreshing posture-state .gitignore entries (PLAN-165 CX-3)
    SKIP: posture-state ignores (recorded --ceremony user install — install.sh skips the same delivery)
```
- install.sh caller gate `[[ $CEREMONY != user ]]` INTACT — OK

## Idempotence — upgrade block run twice

- s1_absent: 2nd run is a no-op; entry counts 1/1 — OK
- s3_unrelated: 2nd run is a no-op; entry counts 1/1 — OK
- s4_first_only: 2nd run is a no-op; entry counts 1/1 — OK

## Positive control — the harness must go RED on a planted mutation

- hoisted_header: detected (bytes and/or stdout diverge) — OK
- dropped_entry: detected (bytes and/or stdout diverge) — OK

## Sample output (s3_unrelated, real run)

### install (NEW)
```

==> Posture-state .gitignore entries (PLAN-165 CX-3)
    APPENDED to .gitignore: .claude/state/
    APPENDED to .gitignore: .claude/settings.local.json
```
### install (OLD @HEAD)
```

==> Posture-state .gitignore entries (PLAN-165 CX-3)
    APPENDED to .gitignore: .claude/state/
    APPENDED to .gitignore: .claude/settings.local.json
```
### upgrade (NEW block)
```

==> Refreshing posture-state .gitignore entries (PLAN-165 CX-3)
    APPENDED to .gitignore: .claude/state/
    APPENDED to .gitignore: .claude/settings.local.json
```
### resulting .gitignore (install NEW)
```
node_modules/
*.log

# PLAN-165 CX-3: per-machine posture/runtime state (never commit)
.claude/state/

# PLAN-165 CX-3: per-machine posture/runtime state (never commit)
.claude/settings.local.json
```

## VERDICT: **ALL BYTE-IDENTICAL / ALL CHECKS PASS**
