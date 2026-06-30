---
id: ADR-079
title: prompt_sha per-installation salt + HMAC chain impact analysis
status: ACCEPTED
created: 2026-04-24
accepted_at: 2026-04-24
accepted_via: Round-23 sentinel (PLAN-058 Phase B closure batch)
proposed_by: CEO (Session 60 PLAN-058 Round-23, Owner option (b))
co_signers: [Principal Security Engineer (forensic correctness), VP Engineering (HMAC chain integrity), Principal QA Architect (regression coverage)]
related_plans: [PLAN-058]
related_adrs: [ADR-005, ADR-010, ADR-055, ADR-056]
blast_radius: L2 (1 producer, 0 consumers that validate hash format; HMAC chain auto-verifies per-event)
supersedes: none
superseded_by: none
closes_finding: PLAN-058 Phase B C-P0-06 (Security F-SEC-03 phantom-rejected; real attack at UserPromptSubmit.py:182 closed)
staged_at: bb0da49
enforcement_commit: bb0da49
---

# ADR-079 — `prompt_sha` per-installation salt + HMAC chain impact

## Context

Phase B audit (Session 59 cont³) Security Engineer F-SEC-03 cited
`.claude/hooks/_lib/injection_patterns.py:159-162
(_hash_injection_prefix)` as a salt-less SHA-256 enabling a
correlation oracle. CEO verification against HEAD `b58cf17`:

```
$ wc -l .claude/hooks/_lib/injection_patterns.py
226 lines
$ grep -n "_hash_injection_prefix\|hashlib\|sha256" \
    .claude/hooks/_lib/injection_patterns.py
(zero matches)
```

The cited function does not exist. Lines 159-162 belong to
`_make_snippet`. The injection-patterns module performs no hashing.
Snippet privacy in `emit_injection_flag` is achieved via
`_redact.redact_secrets` inside `_preview` (audit_emit.py:498) —
a redaction primitive, not a hash primitive.

**However**, the *spirit* of the F-SEC-03 finding is real elsewhere
in the codebase. `UserPromptSubmit.py:182` computes:

```python
prompt_sha = hashlib.sha256(prompt.encode("utf-8", errors="replace")).hexdigest()[:16]
```

This is **the** unsalted SHA-256 prefix that gets published into
every `prompt_submitted` audit event as `prompt_sha256`. A reader of
the audit log can:

1. Take the published `injection_patterns` catalog (or any plausible
   prompt corpus) and precompute the truncated SHA-256[:16] of each
   candidate.
2. Match against `prompt_sha256` field in audit events.
3. Identify which exact prompt the Owner submitted at any given
   time.

The `[:16]` truncation provides ~64 bits of pre-image resistance,
which is weak against a *small* prompt corpus (any user with a
finite, predictable working vocabulary). Same correlation oracle as
F-SEC-03 described, but at the real call-site.

## Decision

We adopt a **per-installation salt** for the prompt hash:

1. **New module** `.claude/hooks/_lib/injection_salt.py` exposes
   `get_instance_salt() -> bytes` returning a 32-byte salt loaded
   from `~/.claude/projects/<slug>/.salt`. Generated on first call
   (`os.urandom(32)`, file mode `0o600`). Cached in module memory
   after first load.

2. **Patch** `UserPromptSubmit.py` line 182:
   ```python
   _salt = _salt_mod.get_instance_salt()  # b"" on failure (fail-open)
   prompt_sha = hashlib.sha256(_salt + prompt.encode(...)).hexdigest()[:16]
   ```

3. **No salt rotation.** Rotating the salt would invalidate
   `prompt_sha256` correlation across all historical audit events
   — the chief use of the field. Per-installation salt suffices to
   defeat external precomputation while preserving single-instance
   forensic correlation across time.

4. **Phantom rejection notice** appended to
   `.claude/plans/PLAN-058/audit/consensus.md` documenting that
   F-SEC-03 cited a non-existent function (mirrors the Performance
   Engineer rejection notice already in the audit addenda).

## HMAC chain impact analysis (ADR-055)

The `prompt_submitted` event carries `prompt_sha256` into the
canonical JSON that feeds `_audit_hmac.compute_entry_hmac`
(audit_emit.py:424-429). The computed HMAC is stored in the same
event row.

**Chain integrity: PRESERVED**

| Aspect | Pre-Round-23 | Post-Round-23 |
|---|---|---|
| `prompt_sha256` value | `sha256(prompt)[:16]` | `sha256(salt + prompt)[:16]` |
| Per-event HMAC | computed over current `prompt_sha256` | computed over current `prompt_sha256` |
| Verification | recompute HMAC from line; compare | recompute HMAC from line; compare |
| Result for old entries | HMAC matches old hash → valid | HMAC matches old hash → valid (unchanged) |
| Result for new entries | — | HMAC matches new hash → valid |
| Chain link (`prev_hmac`) | sequential per ADR-055 | sequential per ADR-055 (unchanged) |

The HMAC chain links each entry to the previous entry's HMAC, not
to the `prompt_sha256` value structure. Salt change affects only
the *content* of `prompt_sha256` going forward; it does not change
the HMAC computation algorithm, the canonical JSON serialization,
or the chain-link structure. Verifiers (`audit_hmac.verify_chain`)
re-compute HMAC over each line as-stored and confirm the link
sequence — they do not validate that a hash is "salted" or
"unsalted", only that the HMAC was computed over the bytes
present.

**Cross-rotation behavior**

`_rotate_if_needed_safe` in audit_emit.py invokes
`_audit_hmac.reset_chain_on_rotation` when a log rotation happens.
The chain re-anchors at genesis in the new file. Salt change does
not interact with rotation — the same salt is used across rotated
files, so single-installation correlation across rotated logs is
preserved.

## Blast radius

**1 producer:**
- `UserPromptSubmit.py:182` — patched.

**0 consumers that validate hash format:**
- `audit_emit.py:1857` — `emit_prompt_submitted(prompt_sha256: str)`
  passes the value through verbatim. No format assertion.
- `audit_emit.py:1872` — `emit_generic` writes verbatim into the
  event. No format assertion.
- Tests: 3 files reference `prompt_sha`/`prompt_sha256` —
  `test_user_prompt_submit.py:176`,
  `test_lifecycle_edge_cases.py:472`,
  `test_audit_emit_coverage.py:1180`. All three pass literal mock
  strings as kwargs to test the emitter dispatch. None assert that
  the hash equals SHA-256(specific input). Salt change has zero
  test impact.
- `scripts/run-skill-benchmark.py:841` and
  `scripts/benchmark-judge.py:111,530` use a *different*
  `prompt_sha256()` symbol (golden-prompt hash for benchmark
  fixtures). Unrelated; not patched.

**Backward compatibility:**
- Old audit-log entries retain unsalted hashes; their HMACs verify
  against the line bytes as stored.
- New audit-log entries carry salted hashes; their HMACs verify
  against the line bytes as stored.
- An external reader cannot precompute hashes for new entries
  without the salt; old entries remain correlatable but reveal
  nothing they did not already reveal pre-Round-23.

## Rationale

- **Closes the real attack vector.** F-SEC-03's *spirit* (salt-less
  hash → correlation oracle) is genuine; the cited path was wrong.
  The fix targets the actual correlation oracle.
- **Documents the phantom.** Future readers see why F-SEC-03 was
  rejected on its literal claim and accepted in spirit at a
  different path.
- **Minimal surface change.** One new module (~150 LoC), one line
  patch, two new test files (~13 tests). No HMAC algorithm change.
  No SPEC schema change. No `_KNOWN_ACTIONS` change. No audit-query
  consumer change.
- **Fail-open preserved.** Salt module returns `b""` on filesystem
  failure; hook degrades to unsalted hash; emit still fires.
  Availability invariant is upheld per ADR-005.
- **No salt rotation policy needed.** Rotation breaks correlation
  utility, gains no security (an attacker who reads the salt file
  has already compromised the audit log root). Per-instance
  generation defeats the documented attack class.

## Consequences

- `prompt_sha256` published in audit events is no longer a static
  function of the prompt content. External readers cannot enumerate
  prompts from the catalog.
- Same prompt issued in two different installations produces two
  different `prompt_sha256` values. Cross-installation correlation
  becomes impossible without comparing the two `.salt` files
  (which are protected at `0o600`).
- Same prompt issued at different times within one installation
  still produces the same `prompt_sha256`. Forensic timeline
  correlation is preserved.
- Storage cost: 32 bytes per installation, written once.
  Performance cost: one extra `os.read(.salt)` on first
  `UserPromptSubmit` invocation per process; cached thereafter.
  Negligible.

## Acceptance

- `_lib/injection_salt.py` ships canonical with 9 unit tests
  covering generation, caching, fail-open, corruption recovery,
  cross-installation distinctness.
- `UserPromptSubmit.py` patched + 4 new tests in
  `test_user_prompt_submit_salt.py` covering hash distinctness
  across installations, stability within installation, salted-vs-
  unsalted divergence, fail-open emit on salt module exception.
- Hook suite ≥ 2580 (2573 baseline + 9 + 4 = 2586 expected; minor
  drift acceptable).
- `validate-governance.sh` 0 errors.

## References

- PLAN-058 Phase B `audit/findings/security-engineer.md` F-SEC-03
- PLAN-058 Phase B `audit/consensus.md` (phantom rejection notice
  to be appended Round-23)
- ADR-005 (fail-open hook discipline)
- ADR-010 (advisory observability)
- ADR-055 (HMAC audit-log chain — algorithm unchanged)
- ADR-056 (UserPromptSubmit lifecycle hook design)
- `_lib/injection_salt.py` (salt module)
- `UserPromptSubmit.py:182-205` (patched call-site)
