---
name: Feature request
about: Propose a new capability or enhancement
title: "[feat] "
labels: ["feature", "needs-triage"]
assignees: []
---

## Problem you're hitting

What can you NOT do today that you want to do? Be concrete. Avoid "it would
be nice if…" — we want a real use case we can verify.

## Proposed solution

Your best guess at the shape of a solution. If you don't know yet, that's
fine — describe the outcome and leave the shape to maintainers.

## Acceptance criterion

How will we know this is done? One testable sentence.

## Alternatives considered

What other approaches did you think through? Why did they not work?

## Blast radius estimate

- [ ] L1 — 1-2 files, contained
- [ ] L2 — one skill / one hook / one script area
- [ ] L3+ — 3+ modules, new contract, or new dependency (**needs ADR**)

## Owner lens

For L3+ features: who benefits? Why now? What's the success metric?

## Anti-goal check

Does this request pull the framework TOWARD:
- [ ] More skills (48+) — bias: NO, stay lean
- [ ] Another language runtime (TS/Go/Rust) — bias: NO, ADR-002 stdlib Python
- [ ] Runtime dependencies (pip install X) — bias: NO, zero-dep invariant
- [ ] A web UI / dashboard beyond loopback SSE — bias: NO
- [ ] Auto-publish / auto-deploy — bias: NO (PLAN-013 anti-goal #16)

If any box is checked, expect strong pushback + ADR requirement.

## Additional context

ADR references, prior-art links, related issues.
