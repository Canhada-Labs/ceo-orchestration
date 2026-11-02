---
adr_id: ADR-201
title: Bounded additive guard for indirect shell execution
status: ACCEPTED
date: 2026-11-01
plan: PLAN-195
---

# ADR-201: Bounded additive guard for indirect shell execution

## Status and provenance

ACCEPTED by the CEO/Owner instruction for W6G on 2026-11-01. This records
acceptance of the bounded architecture implemented in `027895f1`, derived from
[PLAN-195](../plans/PLAN-195-bash-guard-indirect-execution.md) and corrections
C1–C13. It does not assert that the private replay, veto reconfirmations,
GPG signatures or OS-sandbox measurements have occurred.

Enforcement commit: `027895f1` (integrated implementation and synthetic tests).

The source of historical measurements below is PLAN-195 C13. The plan's
`done` metadata was authorized for the integrated technical scope; the
outstanding acceptance evidence remains listed separately in the plan and in
this ADR. Synthetic tests do not replace the private differential corpus.

## Problem

The existing destructive-command checks recognize a narrow direct spelling.
A command position inside a shell body, launcher, substitution, or command list
can carry the same destructive operation without that spelling at the outer
boundary. Computed write destinations also escape literal canonical-path checks.

The guard must raise the cost of those forms without claiming complete shell
evaluation. It must never execute the submitted command, expand the real
filesystem, read shell profiles, or treat arbitrary quoted data as a program.

## Architecture

Use one bounded additional scan at the tail of `decide_command`, after the
existing checks. The new scanner only adds vetoes; an earlier BLOCK stays BLOCK.
The existing force-push rewrite keeps its separate ASK contract and token-wise
requoting. It does not become a silent ALLOW through the new scanner.

Keep the legacy E4 logic intact and consume canonical guards by reading the
existing `_CANONICAL_GUARDS` policy. Do not add `.mcp.json` or `CLAUDE.md` to that
set through this change. Those paths have separate policy owners.

The scanner distinguishes these operand contracts:

| Container | Operand interpretation |
| --- | --- |
| Runner | Visible argv after the launcher's documented options |
| Body taker | Shell source: shell `-c`, `eval`, shell here-doc/here-string |
| Opaque feeder | Program supplied by stdin, descriptor, process substitution, or evaluated substitution output |
| Computed verb | Expansion in command position with literal destructive markers |
| Ordinary argument | Data; quoted examples alone do not become executable commands |

The pre-lexer preserves quote provenance, escaped operators, comment boundaries,
and newline separators. A quoted here-doc delimiter suppresses substitutions;
an unquoted delimiter does not. Command substitutions inside double quotes run
regardless of the outer consumer. Same-command function and alias bodies are
visible source; definitions from earlier calls or profiles are not.

Normalize only known launchers and their option arity. Inspect brace expansions
by membership, including the rest of argv. Treat unknown launcher flags as
ambiguous rather than silently guessing which token is the executable.
Apply explicit depth, body-size, word-count, and expansion ceilings.

Malformed recognized shell bodies fail closed even without a recognizable
destructive signature. Infrastructure failures remain fail open with the
existing hook telemetry policy. Neither result proves that execution is safe.

## Decisions and observability

An indirect destructive veto carries a class-specific `reason_code` and uses
the existing `veto_triggered` action once per command. Do not register an
unconsumed action or emit raw command material through a new event shape.
Map each class to the existing forensic technique before acceptance.

The existing trio remains `destructive=True`, including its equivalent indirect
forms, so the fact-gate/citation contract is preserved. A computed canonical
write remains `destructive=False`: a destructive-command citation cannot grant
permission to edit a canonical file. The A-9 destructive tag is an unresolved
Owner decision (C13 P-4); this proposal does not decide it by analogy.

Use two independent trusted startup controls, both enabled by default:

| Switch explicitly set to `0` | Scope disabled |
| --- | --- |
| `CEO_BASH_INDIRECT_HEURISTICS` | Computed-verb and opaque-feeder heuristics |
| `CEO_BASH_INDIRECT_GUARD` | The additional indirect-execution scan |

Neither switch disables pre-existing checks or changes an earlier BLOCK.
Read them from `trusted_env`, never from mutable tool input. Unset controls
produce no disabled event. Each explicit disable emits at most one
`learning_rail_disabled` record per session and switch, using atomic marker
creation under the audit directory. Marker/storage failure must not crash the
hook; a crash after marker creation can lose that telemetry record.

**Schema decision:** extend `_LEARNING_RAIL_ENUM` with
`bash_indirect`, and `_LEARNING_SWITCH_ENUM` with the two exact names above.
Update `SPEC/v1/audit-log.schema.md` together. Retain the existing registered
action and field allowlist; never let coercion mislabel this rail as `observe`
or the switch as `other`. Do not record environment values.

## Replay acceptance contract

Classify a new veto as a false positive only when its direct equivalent would
ALLOW. If the direct form also blocks, record policy consistency separately.
For opaque programs unrecoverable from the transcript, count the case as a
false positive, except when a visible network downloader supplies the program.
The latter is policy-consistent and cannot be downgraded.

The following limits are absolute counts of distinct legitimate commands,
copied from C13 P-1, not percentages or newly measured results:

| Row | Class | Maximum new false positives |
| --- | --- | --- |
| E-1 direct sibling spellings | Equivalence | 0 |
| E-2 shell body takers | Equivalence | 0 |
| E-3 argv runners | Equivalence | 0 |
| H-1 computed verb | Heuristic | 0 |
| H-2.1 program through pipe | Heuristic | 1 |
| H-2.2 redirected input | Heuristic | 0 |
| H-2.3 descriptor input | Heuristic | 0 |
| H-2.4 process substitution | Heuristic | 2 |
| H-2.5 evaluated substitution output | Heuristic | 8 |
| V-1 private A-9 vocabulary | Heuristic | Pending private measurement |

The historical denominator in C13 is 2026-08-23T17:32:33Z through
2026-10-02T04:16:25Z: 102,979 deduplicated invocations, 99,673 byte-distinct
commands, 52 sessions. These are historical plan records, not results of this
implementation. Attach the differential denominator and classification before
claiming this implementation meets any limit. “Meets” means does not exceed.

Depth/size, brace-word ceilings, and unknown-launcher flags are C13 P-5
proposals pending measurement and Owner ratification. Do not invent limits for
their acceptable false positives or for V-1 from missing corpus data.

Downgrade a heuristic sub-form only through an ADR amendment plus a code
constant, after review; never through an arbitrary runtime rule configuration.
Keep its reason code, report the would-block outcome, and declare the residual.
No sub-form is declared downgraded by this decision.

## Limitations and acceptance work

The single residual source is PLAN-195 Goal plus C12, with C13 extending item
10 to computed verbs. All thirteen residuals remain declared there. In
particular, language-native APIs, pre-existing scripts/profile aliases, fully
computed commands and arguments, cross-call cwd, and filesystem aliases are
not made observable by this scanner. A-8 and recursive removal without force
remain pending OQ-10 policy; do not silently broaden them.

Keep the sanctioned cleanup helper, invoked by path and confined to its own
temporary clone, in the legitimate controls. The citation pilot's role-filter
follow-up remains required; substring matches alone are not user authorization.
The hook must remain a superset of its YAML twin without modifying the twin in
W1. Corpus findings remain limited by one repository, retention, and survivor
bias. W3 measures an OS sandbox separately before any Owner enablement decision.

Before claiming complete external validation: reconcile the private draft and vocabulary; classify HEAD ×
patch replay in both directions with isolated audit storage and positive
zero-live-delta control; measure V-1/P-5; resolve the A-9 tag, OQ-10 and cleanup
route; obtain the C13 veto reconfirmations; verify local mirrors; and complete
the applicable Owner signature and release gates. The acceptance above records the Owner's
decision; no GPG signature or unexecuted measurement is inferred from it.
