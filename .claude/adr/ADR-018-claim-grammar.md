# ADR-018: Claim Grammar for Confidence Gate

**Status:** ACCEPTED (2026-04-13, v1.0) → AMENDED v1.1 (2026-04-14, PLAN-009 C1.2)
**Date:** 2026-04-13 (v1.0) / 2026-04-14 (v1.1 amendment)
**Decision drivers:** need a verifiable contract between spawn outputs and a mechanical confidence gate before enabling enforcement in Sprint 9+.

## Version history

- **v1.0 (2026-04-13, PLAN-008 Phase 2):** initial grammar with 5 claim
  kinds (`path_exists`, `function_exists`, `sha_exists`, `test_passes`,
  `line_range`). Shipped as advisory CLI in Sprint 8.
- **v1.1 (2026-04-14, PLAN-009 C1.2):** adds `import_resolves` kind
  (syntactic-only, zero `importlib.*` calls); freezes claim-kind
  namespace (new kinds require v1.2 amendment); adds normative
  block-list for `import_resolves`; formalizes unknown-kind tolerance.

## Context

Spawn outputs regularly assert the existence of files, functions, SHAs,
tests, and line ranges ("I added `foo()` to `src/bar.py`", "test
`tests/auth/test_login.py::test_rejects_expired` passes", "see SHA
`abcdef1`"). Some of these claims are false — the file doesn't exist,
the function was imagined, the SHA isn't in the tree. A mechanical
verifier ("confidence gate") can catch these before they propagate.

PLAN-008 Phase 2 ships the gate as an advisory CLI. For the CLI to work
reliably, we need a **structured grammar** that agents emit inline in
their outputs — not free-text parsing. Free-text parsing (Option A
below) generates noise and produces a poor False-Positive Rate (FPR)
baseline, which in turn makes the Sprint 9 decision to enforce
untrustworthy.

Debate round 1 on PLAN-008 surfaced a **HIGH** finding (C3) from Staff
Backend: naive grammar (`CLAIM:<kind>:<args>`) collides with real-world
args that contain `:` (e.g. `tests/foo.py::test_bar`), and tokens inside
fenced code blocks generate false positives that would contaminate the
FPR data this ADR exists to enable.

This ADR codifies the grammar so the verifier, the emitters (future
agent-side helpers), and the audit schema stay coherent.

## Decision drivers

- **Mechanical verification.** Grammar must be unambiguous — regex-extractable in one pass, no backtracking.
- **Stdlib only.** No YAML/JSON parser required. Extraction must work with Python stdlib `re` + `str` methods.
- **Robust to code blocks.** Agents routinely quote code that LOOKS like claims; the grammar must ignore fenced code blocks.
- **Robust to `:`-containing args.** Test selectors (`::`), class paths, URLs — `:` is common in legitimate args.
- **Additively extensible.** New claim kinds must be addable without breaking existing extraction or audit consumers.
- **Cheap to emit.** Agents can produce claims inline in prose, not as a trailing JSON block.

## Options considered

### Option A — Free-text regex scan

Grep the output for patterns like `` `src/...` `` or `tests/...::test_...`
and verify each hit.

- **Pros:** zero burden on the agent; works today with no prompt changes.
- **Cons:** wildly high FPR (every prose mention becomes a claim); no kind disambiguation; collides with code blocks; makes the Sprint 9 decision untrustworthy.

### Option B — Structured grammar with quoting + code-block exemption (chosen)

Agents emit inline tokens `CLAIM:<kind>:<args>` where args with `:` are
backtick-quoted. Extractor skips fenced code blocks.

- **Pros:** disambiguated per kind; verifier is simple; FPR baseline will be meaningful; forward-compat by kind; escape rule handles real-world args.
- **Cons:** agents must learn to emit tokens; initial FPR will include "agents forgot to emit" which looks like zero-claim outputs (handled by exit code 3 in the CLI, debate consensus C4).

### Option C — JSON-tagged trailing block

Agents end their response with a `<!-- claims --> {...json...}` block.

- **Pros:** structured; no inline parsing.
- **Cons:** requires parser; agents often forget trailing blocks; doesn't survive output truncation; claims and prose are decoupled, which makes auditing which prose made which claim harder.

## Decision

**Option B.** The grammar is:

```
<claim>       ::= "CLAIM:" <kind> ":" <args>
<kind>        ::= "path_exists" | "function_exists" | "sha_exists"
                | "test_passes" | "line_range"
<args>        ::= <raw-arg> | "`" <quoted-arg> "`"
<raw-arg>     ::= any sequence of non-whitespace, non-backtick chars
                  that does NOT contain ":"
<quoted-arg>  ::= any sequence inside backticks (backticks themselves
                  may not appear in args; if needed, use double-backtick
                  fencing as an escape — reserved for v1.1)
```

### Five MVP claim kinds

| Kind              | Args                                        | Verifier                                                                 |
| ----------------- | ------------------------------------------- | ------------------------------------------------------------------------ |
| `path_exists`     | relative-or-abs path                        | `Path(p).exists()`                                                       |
| `function_exists` | `module-path:function-name`                 | `ast.parse(module)` walk; match by name at top-level or class-method scope |
| `sha_exists`      | git SHA (full or ≥7-char prefix)            | `git cat-file -e <sha>`                                                  |
| `test_passes`     | pytest selector (`file.py::Class::test`)    | `pytest --collect-only -q <selector>` exit 0                             |
| `line_range`      | `path:start-end` (e.g. `src/foo.py:10-20`)  | `wc -l <path>` > end                                                     |

### Quoting rule

Args that contain `:` MUST be backtick-quoted. Example:

```
CLAIM:test_passes:`tests/auth/test_login.py::test_rejects_expired`
CLAIM:path_exists:src/auth/login.py                # no ":" → no quoting
CLAIM:line_range:`src/foo.py:10-20`                # contains ":" → quoted
```

The extractor's regex recognizes both forms:

```python
CLAIM_RE = re.compile(
    r"CLAIM:(?P<kind>[a-z_]+):"
    r"(?:`(?P<quoted>[^`]+)`|(?P<raw>[^\s:`]+))"
)
```

### Code-block exemption

Fenced code blocks (delimited by triple-backticks at start-of-line) are
**entirely ignored** by the extractor. The exemption is line-based:

```
in_code_block = False
for line in text.splitlines():
    if line.startswith("```"):
        in_code_block = not in_code_block
        continue
    if in_code_block:
        continue
    # scan line for CLAIM_RE
```

This prevents false fails on documentation, examples, and quoted code.

### Regression fixtures (mandatory for Phase 2)

For each kind, `.claude/scripts/tests/fixtures/claims/<kind>/` MUST ship:

- ≥3 positive fixtures (valid token → verifier returns True)
- ≥2 negative fixtures (valid token → verifier returns False)
- ≥1 fixture showing a token inside a code block (extractor MUST skip)
- ≥1 fixture showing a quoted arg (extractor MUST recognize)

Total: at least 5 × 6 = 30 fixtures shipped with Phase 2 tests.

## Consequences

### Positive (+)

- Verifier is a 30-line regex + 5 verifier functions; easy to audit.
- FPR baseline collected in Sprint 8 is meaningful (low noise).
- Grammar is forward-compat: v1.1 can add `import_resolves`, `type_exists`, `endpoint_responds` by extending the `<kind>` enum without breaking v1.0 consumers.
- Audit event (`confidence_gate` action) has stable reserved fields (`claim_count`, `pass_count`, `fail_count`, `verifier_kind_counts`) set in PLAN-008 Phase 2.

### Negative (−)

- Agents need prompt guidance to emit tokens. Phase 3 (and future squad skills) will add an "emit CLAIM tokens for verifiable assertions" instruction. Agents will initially forget; zero-claim exit code (3) is our observability of that regression.
- Backtick-quoting with a backtick-literal-in-arg case is punted to v1.1 (reserved: double-backtick fencing). If an arg genuinely needs a backtick, the agent omits the claim for v1.0.
- Code-block exemption means: if an agent emits a valid claim inside a code block (e.g. in a proposed patch), it won't be verified. This is the right trade-off — code-block claims belong to the proposed change, not the asserted reality.

### Neutral (~)

- Line-based code-block detection doesn't handle single-line fences perfectly (``` `foo` ``` on one line) — acceptable because single-line inline code is ``` `...` ```, not fenced.
- The regex is deliberately conservative. Tokens split across lines are NOT recognized (no multi-line args in v1.0).

## Blast radius

**L3** — the grammar is a contract between:

1. Agents (prompt guidance → Sprint 8+ spawn templates)
2. `confidence-gate.py` CLI (Phase 2)
3. Audit schema (`SPEC/v1/audit-log.schema.md` `confidence_gate` action)
4. `audit-query.py claims` sub-command (Phase 2)
5. Future PostToolUse hook (Sprint 9+)

Consumers that break on schema change: audit-query, dashboards, future
SDK. Forward-compat design (enum extension + reserved fields) protects
them.

## Amendment v1.1 — Sprint 9 C1.2 (2026-04-14)

PLAN-009 debate round 1 (Security Engineer R-SEC1, HIGH) surfaced a
CRITICAL bug in the pre-draft `import_resolves` spec: using
`importlib.util.find_spec` to "resolve" an import causes CPython to
execute the *parent package's* `__init__.py`. Under an untrusted-
agent-output threat model (the verifier runs on text produced by
another LLM call), this is a remote code execution sink: an attacker
that can write under the repo can smuggle code into `foo/__init__.py`
and have it execute simply by emitting `CLAIM:import_resolves:foo.bar`.

The pre-draft shipped no `find_spec` code path, but the documentation
described the behavior, which risked someone implementing it. v1.1
REMOVES that behavior from the normative doc and replaces it with a
syntactic + file-existence spec that cannot execute code.

### 1. `import_resolves` kind definition (v1.1)

**Grammar (args):** dotted identifier matching
`^[A-Za-z_]\w*(\.[A-Za-z_]\w*)*$`. Examples:

```
CLAIM:import_resolves:lessons
CLAIM:import_resolves:pkg.sub.mod
```

**Not accepted** (must use `path_exists` instead):
- Relative imports with leading `.` (`CLAIM:import_resolves:.foo`)
- Filesystem paths (`CLAIM:import_resolves:path/to/mod`)
- Any non-identifier character

**Verification (pure file-existence, zero code execution):**

Given `args = "foo.bar.baz"`, take `top = "foo"` (first dotted part).
The claim resolves iff either:
- `<repo_root>/foo.py` exists as a file, OR
- `<repo_root>/foo/__init__.py` exists as a file.

The tail (`.bar.baz`) is NOT checked. Sub-module resolution would
require reading source files and parsing their AST exports, which we
defer to a future `symbol_exists` kind. `import_resolves` is a weak
"is this importable at the top level" signal.

**Normative block-list.** The following top-level names are always
rejected, even if a matching file exists (which would be shadowing):

```
os, subprocess, sys, importlib, builtins, __builtins__, __main__
```

Rationale: these are built-ins that always resolve in CPython; CLAIMing
them is either pure noise or an attempt to confuse the verifier.
Rejecting them up-front shrinks attack surface at zero signal cost.

### 2. Removed: "does not execute code" claim from v1.0

v1.0 did not explicitly state the verifier does not execute code.
v1.1 makes this a **normative non-goal**: `confidence_gate.py` MUST
NOT execute Python code loaded from the repo as part of verification.
The only subprocesses it runs are `git cat-file -e <sha>` and
`pytest --collect-only <selector>` (sandboxed via
`PLAN-009 A3 pytest argv lock`).

### 3. Claim-kind namespace frozen

v1.1 closes the claim-kind set to:

```
{ path_exists, function_exists, sha_exists, test_passes, line_range,
  import_resolves }
```

Adding a new claim kind requires a **v1.2 amendment to this ADR**
with: (a) grammar definition, (b) verifier contract (incl. must-not
execute-code confirmation), (c) regression fixtures, (d) audit schema
amendment (`verifier_kind_counts` enum extension).

### 4. Unknown-kind tolerance (formalized)

`extract_claims` emits every `CLAIM:<kind>:<args>` hit with
`kind_supported` flag. The CLI reports unknown kinds as:

```
{"kind": "unknown", "raw_token": "CLAIM:foo:bar", "passed": false,
 "kind_supported": false, "detail": "unknown kind: 'foo'"}
```

Unknown kinds are **non-fatal** — they increment `fail_count` in
advisory mode but the CLI returns exit 1, not 2. This lets v1.2+
emitters coexist with v1.1 verifiers without crashing.

### 5. Block-list rationale

Why block `os` / `subprocess` / `sys` even though no code executes?

Two reasons:

1. **Noise reduction.** Agents asserting "the `os` module resolves"
   is tautological — it's always installed. Blocking removes noise
   from the FPR baseline.
2. **Defense in depth.** If a future claim kind ever uses the args
   to drive actual imports (which v1.1 forbids), the block-list
   already catches the obvious attack paths before they reach the
   verifier. The list is in one place; expanding it is cheap.

## References

- PLAN-008 §Phase 1 + §Phase 2
- PLAN-008/debate/round-1/consensus.md §C3 + §C4
- PLAN-009/debate/round-1/security.md §R-SEC1 (critical finding
  driving v1.1 amendment)
- PLAN-009 §Phase 1 C1.2
- `project_sprint_8_10_roadmap.md` (memory) — Sprint 8 scope
- SPEC/v1/audit-log.schema.md §Additivity (schema evolution rules)
- ADR-011 — Event stream v2.1 injection_flag (precedent for additive audit action)

## Enforcement commit

`c57e57687dee` (retrofit — PLAN-050 Phase 2 / PLAN-045 F-06-03; this anchors the file's introduction commit, not a runtime-behavior commit. For ADRs whose decision was wired into hooks/scripts in a later commit, amend this line manually.)
