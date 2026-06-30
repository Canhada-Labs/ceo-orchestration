# ADR-012: Cross-adapter golden fixtures + OIDC NPM publisher

**Status:** ACCEPTED
**Date:** 2026-04-13
**Sprint:** 5 Phase 4
**Supersedes:** none
**Related:** ADR-008 (Hook Adapter Layer), ADR-007 (SemVer + RC policy)

## Context

Two pieces of distribution infrastructure landed in Sprint 5 Phase 4:

1. **The Hook Adapter Layer** (ADR-008) reserved the right to add a
   second IDE adapter (`gemini`, `codex`) but did not lock the
   conformance contract. Without a contract, "Gemini support" becomes
   a guessing game about field names, payload shapes, and decision
   formatting.

2. **The NPM shim** (`@ceo-orch/init`) introduces a second distribution
   channel for the framework. Publishing it manually invites
   credential-leak risk. Publishing it from CI on tag push removes
   the human credential entirely.

Both mechanisms need formal contracts so future work can land
without re-debating the fundamentals.

## Decision drivers

- **Adapter conformance must be falsifiable.** Without byte-exact
  fixtures, "the gemini adapter works" is unverifiable.
- **NPM publishes leak credentials.** Manual `npm publish` requires
  a long-lived token in someone's keychain. OIDC trusted publishers
  remove the token entirely; npm validates the publisher via
  Sigstore + GitHub OIDC.
- **One source of truth.** The framework's `VERSION` file is canonical
  for both the SPEC and the npm package. Two version tracks would
  drift.

## Options considered

### Option A: Adopt golden fixtures + OIDC publisher (CHOSEN)

- Each adapter ships:
  - `tests/fixtures/normalized/<scenario>.json` (canonical NormalizedEvent)
  - `tests/fixtures/adapters/<adapter>/in/<scenario>.json` (wire-shape input)
  - `tests/fixtures/adapters/<adapter>/out/<decision_key>.json` (wire-shape output)
- A new adapter passes `test_adapter_golden.py` when its `read_event`
  produces the canonical NormalizedEvent and its `write_decision`
  produces the canonical wire output.
- NPM publish workflow uses GitHub OIDC + `--provenance` flag
  (Sigstore-attested provenance recorded by npm).

**Pros:**
- Adapter parity is mechanically verifiable.
- Credentials never leave GitHub.
- Provenance audit trail for every published version.

**Cons:**
- Requires fixture maintenance when adapter shape evolves (acceptable
  — the fixtures ARE the contract).

### Option B: Adapter conformance via type checks only

Test that each adapter exports `read_event` and `write_decision` with
the right signatures.

**Cons:** doesn't catch wire-shape bugs. A Gemini adapter could happily
return a NormalizedEvent with `tool_name: "ToolUseBlock"` instead of
the expected `Bash` and pass type checks while being functionally
broken.

### Option C: Manual NPM publish via maintainer

Owner runs `npm publish` from their machine after each tag.

**Cons:** long-lived token in keychain. Owner manual step in release
critical path. No provenance attestation.

## Decision

**Option A.**

### Golden fixture layout

Locked under `.claude/hooks/tests/fixtures/`:

```
fixtures/
├── normalized/
│   ├── agent_spawn_compliant.json
│   ├── bash_safe_command.json
│   └── ...   (one per scenario)
├── adapters/
│   └── claude/
│       ├── in/    (wire-shape inputs)
│       │   └── <scenario>.json
│       └── out/   (wire-shape outputs)
│           ├── allow.json
│           └── block_with_reason.json
```

A new adapter (Gemini, Codex, ...) ships:
- `_lib/adapters/<name>.py` with `read_event` + `write_decision`
- `tests/fixtures/adapters/<name>/in/` mirroring scenarios
- `tests/fixtures/adapters/<name>/out/` mirroring decision keys
- An entry in `KNOWN_ADAPTERS` in `_lib/contract.py`

`test_adapter_golden.py` discovers and verifies all of the above
automatically — adding an adapter is therefore a fixture exercise.

### Env-var dispatch

`CEO_HOOK_ADAPTER=<name>` selects the adapter at runtime.
`resolve_adapter()` falls back to `claude` for unknown / empty values
(silent — observability is via audit_emit, not stderr).

### NPM OIDC trusted publisher

`.github/workflows/npm-publish.yml` runs on tag push (`v*`). It:

1. Asserts VERSION file == tag == npm/package.json version (3-way).
2. Asserts `npm/package.json.dependencies` is empty.
3. Stages the framework source tree into `npm/` (cp, not symlink).
4. Publishes via `npm publish --provenance --access public`.

Provenance is attested via GitHub OIDC token + Sigstore. NPM verifies
the token; no long-lived `NPM_TOKEN` is needed (the workflow `id-token: write`
permission is sufficient when the npm scope is configured for
trusted-publisher).

(Note: until the npm scope is configured for OIDC trusted publisher,
the workflow falls back to `NODE_AUTH_TOKEN: ${{ secrets.NPM_TOKEN }}`.
Owner action: register the OIDC trust after the first manual publish.)

## Consequences

### Positive

- Adding `gemini` adapter is a fixture-comparison exercise, not a
  guessing game.
- Adapter parity is mechanically verifiable — `make test` is the
  release gate.
- NPM publishes are credential-free + carry attested provenance.
- Three-way version consistency check prevents accidental version skew.

### Negative

- Fixture proliferation: each scenario + adapter combination adds a
  pair of files. Mitigation: scenarios are conservative — start with
  2-3 canonical paths, add as adapters require.
- OIDC trusted publisher requires Owner setup on the npm side
  (one-time). Until configured, `NPM_TOKEN` is the fallback.

### Neutral

- The fixtures live in `.claude/hooks/tests/fixtures/` (matching the
  test layout). Future adapters MAY contribute new scenarios; existing
  ones are immutable.

## Blast radius

L2:
- New `.claude/hooks/tests/test_adapter_golden.py` (read-only on existing modules)
- New `.claude/hooks/tests/fixtures/{normalized,adapters}/` directories
- `_lib/contract.py` extension: `resolve_adapter()` + `load_adapter()` helpers, ENV var
- `npm/` subtree (new — orthogonal to existing code)
- `.github/workflows/npm-publish.yml` (new — only fires on tag push)

**Reversibility:** HIGH for fixtures (delete them), MEDIUM for npm
publish (unpublishing requires npm support intervention; deprecation
is the typical path).

## References

- ADR-008 (Hook Adapter Layer foundation)
- ADR-007 (SemVer + RC policy — ties NPM version to SPEC version)
- PLAN-005 §3 Phase 4
- npm provenance docs: <https://docs.npmjs.com/generating-provenance-statements>

## Enforcement commit

`24112512004d` (retrofit — PLAN-050 Phase 2 / PLAN-045 F-06-03; this anchors the file's introduction commit, not a runtime-behavior commit. For ADRs whose decision was wired into hooks/scripts in a later commit, amend this line manually.)
