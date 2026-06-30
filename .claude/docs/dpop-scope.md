---
title: DPoP Scope — Replay-Defense Boundary
status: SCOPE-DOCUMENTATION
plan: PLAN-086
wave: F.3
plan_090_delivery_floor: 2026-08-10
related_adrs:
  - ADR-040-live-adapter-activation-contract
  - ADR-040-AMEND-2-credential-blocking
spec_refs:
  - RFC 9449 §1 (Demonstrating Proof of Possession)
related_findings:
  - F-A-IDA-T-0006 (DPoP scope ambiguity)
veto_case: B
---

# DPoP Scope — Replay-Defense Boundary

## TL;DR

**DPoP-style replay defense applies to LOOPBACK BEARER TOKENS ONLY** in
the `ceo-orchestration` framework. It is NOT a wire-protocol commitment
to remote MCP servers, OAuth providers, or third-party APIs reached over
the public internet.

This scope clarification closes finding **F-A-IDA-T-0006** (DPoP scope
ambiguity). The actual DPoP wire-protocol implementation lands in
**PLAN-090** with a delivery floor of **2026-08-10** (90 days from
PLAN-086 ship target 2026-05-12).

## Why this matters

RFC 9449 §1 defines DPoP as "an application-level mechanism for
sender-constraining OAuth 2.0 access tokens and refresh tokens" via a
proof-of-possession JWT bound to a client-held key pair. The mechanism
defends specifically against **bearer-token theft + replay**.

In `ceo-orchestration`, bearer tokens appear in **exactly one trust
boundary**: the **MCP loopback channel** between the Claude Code
harness and a locally-spawned MCP server (Codex MCP, etc.). All such
tokens are:

- Generated at loopback-process boot (no persistence across reboots).
- Bound to a single PID-pair.
- Never serialized to disk OR transmitted over a non-loopback socket.

The framework does NOT issue OAuth tokens, does NOT consume third-party
bearer tokens, and does NOT host a public-facing MCP endpoint.

## Threat model

| Threat | In scope? | Defense |
|---|---|---|
| Replay of loopback bearer by co-tenant process | YES | DPoP-style PoP JWT (PLAN-090) |
| Replay by remote attacker over the wire | NO | No wire — loopback only |
| Token theft from process memory | YES (defense-in-depth) | DPoP PoP key in OS keyring (PLAN-090) |
| Token theft from logs | YES | Redactor at `_lib/redact.py` (shipped) |
| OAuth refresh-token replay | NO | Framework does not consume OAuth flows |

## What this document is NOT

- Not a commitment to deploy DPoP on a public endpoint.
- Not a substitute for ADR-040 live-adapter activation gates.
- Not a token-format specification (PoP JWT structure, alg, claims —
  all specified in PLAN-090).

## Cross-references

- ADR-040 §6.3 — live-adapter allowlist
- ADR-040 §4 — credential rotation cadence (75-day max-age)
- ADR-040-AMEND-2 — credential blocking at max-age
- RFC 9449 §1 — DPoP specification
- PLAN-090 — DPoP wire-protocol (delivery floor 2026-08-10)

## Delivery-floor enforcement

`plan_090_delivery_floor: 2026-08-10` frontmatter field is parsed by
the staleness-checker CLI; advisory CI warning if PLAN-090 slips past
floor. Does NOT block builds.
