---
adr_id: ADR-202
title: Kernel and hooks modularization
status: ACCEPTED
date: 2026-11-01
plan: PLAN-197
---

# ADR-202: Kernel and hooks modularization

## Context and decision

Enforcement commit: `027895f1`, `9c020955` (integrated decomposition).

Record the decomposition already integrated in commits `027895f1` and
`9c020955`. Existing hook and command paths remain entry points; selected
implementations move to domain modules. The concrete inventory is in
[PLAN-197](../plans/PLAN-197-full-monolith-decomposition.md). This is a
retroactive architecture record, not a claim that every monolith was removed.

Compatibility includes names used by existing callers and tests, including
private patch points where explicitly exported by a component. The component
`__all__` lists determine what its binder installs; they are not a guarantee
that every possible private implementation name is exported. Keep the
original command and hook entry points and their observable contracts.

## Mechanisms and trade-offs

`_lib._audit_emit_parts.install` imports its domain declarations and binds
function code objects to the facade's globals with `FunctionType`; it copies
mutable declarations for a fresh facade on reload. This preserves call-time
lookups of patched facade helpers. The `agent_spawn` and `canonical_edit`
packages bind their exported functions to the hook globals; the installer
census binder also handles classes and mutable values. The contamination
scanner binds selected personal-path functions and imports its term scanner.
`audit-query.py` binds extracted functions and retains named delegates for its
AST-inspecting read-API guard. These are distinct implementations, not one
universal `sys.modules` proxy: none of these binders replaces its facade in
`sys.modules` with a proxy.

The cost is explicit export lists, binding logic, and a requirement to test
both the real output and patch points. A plain import/re-export would leave
functions looking up globals in their implementation module, breaking patches
on the historical facade. Reload and mutable state require particular care.

## AST and integrity boundaries

Source-level consumers must be checked individually. In particular,
`check-audit-registry-coverage.py` parses `audit_emit.py` for literal
`_KNOWN_ACTIONS` and `emit_` definitions; moving a function changes what that
AST can see. Named `audit-query.py` delegates and the functional `audit_emit.py`
`iter_events` delegate preserve the declarations expected by the read-API
guard, not the entire pre-decomposition AST. Runtime exports and
AST-visible declarations are different contracts; neither proves the other.

Import failure policy is owned by each entry point, not by this architectural
record. The separate import-integrity work for `check_canonical_edit.py`
addresses its component failure path; this ADR does not claim equivalent
fail-closed behavior for every package, nor that imports attest code integrity.
