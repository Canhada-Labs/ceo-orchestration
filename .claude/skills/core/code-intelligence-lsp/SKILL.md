---
name: core-code-intelligence-lsp
description: Engineering doctrine for using Language Server Protocol tools in agent
  code-analysis workflows for {{PROJECT_NAME}}. Covers per-language LSP server selection,
  diagnostic triage, type-query patterns, and the critical discipline of anchoring
  analysis to structured semantic data rather than string matching. Use when performing
  non-trivial code review, refactoring, type-safety analysis, or any task where grep
  alone cannot distinguish a definition from a reference or a type from its alias.
owner: any code-analysis archetype (no dedicated owner)
inspired_by:
  - source: msitarzewski/agency-agents/specialized/lsp-index-engineer.md@783f6a72bfd7f3135700ac273c619d92821b419a
    license: MIT
    relationship: pattern_reference
    authored_by: ceo-orchestration framework
    authored_at: 2026-05-06
# --- smart-loading fields (PLAN-083 Wave 0a sub-agent 0.7a) ---
domain: core
priority: 5
risk_class: medium
stack: []
context_budget_tokens: 800
inactive_but_retained: false
repo_profile_binding:
  frontend: {active: true, priority: 5}
  engine: {active: true, priority: 5}
  fintech: {active: true, priority: 6}
  trading-readonly: {active: true, priority: 6}
  generic: {active: true, priority: 5}
activation_triggers:
  - {event: help-me-invoked, regex: "(?i)lsp|language.?server"}
---

# Code Intelligence (LSP)

Grep tells you what string appears. LSP tells you what it **means**.

A grep for `UserID` finds every occurrence of those seven characters — including comments,
string literals, variable names that happen to share a prefix, and the actual type
declaration. An LSP `go-to-definition` query on `UserID` resolves through imports,
re-exports, and aliases to the canonical declaration, with its type signature, in
milliseconds. That difference is not cosmetic. A refactor grounded in grep assumptions
silently breaks code paths that the grep didn't surface. An analysis grounded in LSP
diagnostics catches the breakage before it ships.

This skill is the cognitive operating manual for using LSP output effectively. It is
not a server-installation or DevOps guide — it assumes the LSP server is running and
reachable (either natively in the development environment or via an MCP adapter that
exposes LSP queries as tools). The doctrine here is: which server to call, which
query to issue, how to interpret the result, and what counts as sufficient evidence
before making a structural change.

## What This Skill Is (and isn't)

**Is:** Doctrine for using LSP output as the primary evidence base during code analysis.
Covers query selection, result interpretation, server-health awareness, and the decision
rule for when an LSP result is authoritative vs when to read source directly.

**Is not:** A guide to installing, configuring, or managing LSP servers. It is not a
substitute for reading code — LSP answers specific structural questions; human reading
(or agent reading) supplies context that no static analysis server produces. It is not
a formal type-system tutorial. And it is not a CI-pipeline configuration guide —
pyright/tsc in CI is a separate concern from querying them interactively during review.

**Mental model:** Think of the LSP server as a domain expert you can call with a
precise question and receive a precise answer. You do not hand it a vague brief and
ask for a summary — you ask "what is the declared type of this parameter?" or "which
callers pass a value narrower than `string | null`?" The value comes from the precision
of the question, not from the server doing open-ended analysis for you.

## Hard Rules

1. **Run a real type-checker before asserting type correctness — never substitute grep + reading.**
   - **Python:** run `pyright` (strict mode) to catch narrowing failures, missing
     overloads, and `None`-path gaps.
   - **TypeScript:** run `tsc --noEmit` (or query `typescript-language-server`
     diagnostics) — `pyright` does NOT type-check TypeScript. Use the canonical
     compiler.
   - **Other languages:** use the language's canonical type-checker (`mypy --strict`,
     `flow check`, `rust-analyzer`, `gopls`, etc.) — never assume the LSP server
     index in §LSP Server Index without querying it.

   If the canonical type-checker is unavailable in the environment, explicitly
   state that the type analysis is heuristic, not verified. Never write "types
   are correct" when you have not queried a type-checker.

2. **Use `rust-analyzer` for any Rust ownership or lifetime question.**
   Lifetime elision rules and NLL (Non-Lexical Lifetimes) are not reliably inferable
   by reading code without the borrow checker's analysis. A line that looks safe to a
   reader may fail `rustc`; a line that looks problematic may be valid per NLL. Cite
   `rust-analyzer` output, not reading-based intuition, for ownership claims.

3. **Never make a type-widening change without LSP confirmation of all call sites.**
   Widening a parameter from `UserId` to `string` may silently accept values that
   domain constraints forbid. Use LSP `find-references` before widening any type to
   enumerate every call site that will be affected. Document the reference count in
   the change justification.

4. **Never silence an LSP diagnostic without recording why.**
   `# type: ignore`, `// @ts-ignore`, `#[allow(unused)]` — each suppression is a
   claim that the diagnostic is wrong or acceptable. That claim requires a rationale
   in the same comment: which diagnostic code is suppressed, why the suppression is
   correct, and what the compensating control is. Bare suppressions without rationale
   are a review BLOCKER.

5. **Check server health before trusting a clean result.**
   An LSP server that failed to index (due to missing dependencies, import errors, or
   initialization failure) may return empty results or stale data that appear clean.
   Before concluding "no references found" or "no diagnostics," verify the server
   reports a healthy state (no initialization errors, no unresolved imports that span
   the module under review).

6. **Prefer semantic queries over syntactic ones for structural claims.**
   If the question is "what implements interface `X`?" — use LSP `find-implementations`,
   not `grep "implements X"`. The grep misses implementations that satisfy the interface
   structurally (Go, TypeScript structural typing) or that import it indirectly. The
   LSP query is the right instrument; the grep is the wrong instrument used because it
   is faster to type.

7. **Cite LSP output in findings.**
   A code-review finding grounded in an LSP diagnostic includes the diagnostic code,
   the file:line, and the message text. "pyright reports `reportGeneralTypeIssues` at
   `auth/session.py:118` — `None` is not assignable to `UserId`" is evidence.
   "The type looks wrong" is a hunch.

## LSP Server Index

| Language   | Server                       | Install                            | Key query types |
|------------|------------------------------|------------------------------------|-----------------|
| Python     | `pyright`                    | `npm install -g pyright` or `pip install pyright` | diagnostics, hover (type-of), go-to-definition, find-references |
| TypeScript / JS | `typescript-language-server` | `npm install -g typescript-language-server typescript` | diagnostics, hover, go-to-definition, find-references, find-implementations, call-hierarchy |
| Rust       | `rust-analyzer`              | Bundled with rust toolchain via `rustup component add rust-analyzer` | diagnostics, hover (type + lifetime), go-to-definition, find-references, inlay-hints |
| Go         | `gopls`                      | `go install golang.org/x/tools/gopls@latest` | diagnostics, hover, go-to-definition, find-references, find-implementations (interface satisfaction) |
| Java       | `eclipse.jdt.ls`             | Via VS Code Java extension or standalone download | diagnostics, hover, go-to-definition, find-references, call-hierarchy |
| C / C++    | `clangd`                     | `apt install clangd` / `brew install llvm` | diagnostics, hover, go-to-definition, find-references, include graph |
| Ruby       | `solargraph`                 | `gem install solargraph` | diagnostics, hover, go-to-definition, find-references |
| C#         | `OmniSharp` / `roslyn`       | Via `dotnet` SDK tooling | diagnostics, hover, go-to-definition, find-references, call-hierarchy |

**Key query interpretation:**

| Query           | What it answers                                                                 | When to use it |
|-----------------|---------------------------------------------------------------------------------|----------------|
| `diagnostics`   | Errors and warnings the server has computed for a file or workspace             | Before asserting code is type-correct or warning-free |
| `hover`         | Inferred or declared type of the symbol under cursor                            | Before asserting a variable's type; disambiguating overloads |
| `go-to-definition` | Canonical declaration location (resolves aliases, re-exports, conditional imports) | Before assuming you know where a symbol is declared |
| `find-references` | All read and write sites for a symbol across the workspace                    | Before renaming, widening types, or deleting a symbol |
| `find-implementations` | All concrete implementations of an interface or abstract method           | Before changing an interface contract |
| `call-hierarchy` | Callers of a function (incoming) and functions called by it (outgoing)         | Blast-radius assessment for a function-signature change |
| `inlay-hints`   | Inferred type annotations rendered inline (Rust, TypeScript)                    | Verification that inference matches expectation at a glance |

## Diagnostic Triage Protocol

This is the ordered procedure for converting an LSP diagnostic into an actionable
finding or a confirmed non-issue. Do not skip steps. Do not reverse the order.

**Step 1 — Read the code at the reported location.**
Open the file at the reported line. Read 10 lines of context above and below. Understand
what the code is doing before interpreting the diagnostic. An LSP server sometimes
fires on generated code, test fixtures, or intentionally loose typing in adapters.
Reading first prevents mis-triage.

**Step 2 — Cite the diagnostic precisely.**
Record: server name, diagnostic code (e.g. `Pyright/reportGeneralTypeIssues`,
`ts(2322)`, `E0308`), file:line, and the full message text. This is the artifact.
Do not paraphrase the diagnostic — copy it.

**Step 3 — Classify the diagnostic code.**
Each server publishes a diagnostic code index. Classify into:
- **Type error** — a value whose type does not satisfy the receiver's contract (always investigate)
- **Undefined / unresolved** — a name that cannot be resolved in the current scope (always investigate; often signals a missing import or a stale generated file)
- **Nullability** — a value that may be `None`/`null`/`undefined` where the receiver requires a non-null (always investigate)
- **Unused** — a binding or import that is declared but never used (low priority; may be intentional in scaffolding or test setup)
- **Deprecated** — a call to an API marked deprecated (medium priority; note the replacement)
- **Style / convention** — naming, formatting, doc convention (lowest priority; context-dependent)

**Step 4 — Determine scope.**
Is this diagnostic isolated to one module, or does it indicate a cross-cutting
pattern? Run `find-references` on the symbol involved to see how many other sites
are affected. A type error in an exported function is a different blast radius than a
type error in a private helper.

**Step 5 — Act or defer with rationale.**
- If the diagnostic is a type error, nullability, or unresolved name in non-generated
  code: file a finding with the artifact from Step 2. Do not defer without a rationale.
- If the diagnostic is in generated code (protobuf, GraphQL codegen, ORM output):
  note this explicitly and do not file it as a finding against the author — file it
  against the generator configuration if the output is wrong.
- If the diagnostic is suppressed via `# type: ignore` or equivalent: verify the
  suppression carries a rationale per Hard Rule 4. If not, file a finding.

**Step 6 — Record the triage decision.**
Every diagnostic reviewed gets one of: `filed` (with finding number), `deferred`
(with rationale and ticket reference), or `expected/generated` (with explanation).
A diagnostic that disappears from the triage record without attribution is a gap.

## WRONG / CORRECT Examples

### Scenario 1 — Type of a returned value

```
# WRONG — grep-based assertion
Grepped for `def get_user` and found the function. It returns `user_data` which
is a dict. The caller expects a User object. Looks like a type mismatch.

# CORRECT — LSP-anchored assertion
pyright at auth/repository.py:42: reportReturnType — Expression of type
`dict[str, Any]` is not assignable to return type `User`.
Confirmed: `get_user()` is typed as `-> User` but the implementation returns
a raw dict. LSP hover on the caller at auth/service.py:17 shows it receives
`User` and calls `.user_id` — that attribute does not exist on `dict`.
Finding: CRITICAL. Type contract is broken at the declared boundary.
```

### Scenario 2 — Checking whether an interface is fully implemented

```
# WRONG — grep-based assertion
Searched for all classes that mention `Adapter` in their name. Found 3. Checked
each has an `execute()` method. Looks complete.

# CORRECT — LSP-anchored assertion
Used gopls find-implementations on `Adapter` interface (adapters/base.go:12).
gopls returned 4 concrete types, not 3. The 4th — `LegacyAdapter` in
adapters/legacy.go — does not match by name but satisfies the interface
structurally via embedding. Grepping for "Adapter" in the class name missed it.
Verified all 4 pass the `execute()` signature check.
```

### Scenario 3 — Rename / symbol removal

```
# WRONG — deletion without reference check
Removed the `format_price` helper since no calls appeared in the current file.

# CORRECT — deletion with reference check
Before removing `format_price` (utils/currency.py:88):
1. pyright find-references returned 7 call sites across 3 modules.
2. 5 are in test files (safe to update with the rename).
3. 1 is in api/serializers.py:203 (production path — requires coordinated update).
4. 1 is in scripts/backfill.py (offline script — note in change description).
Proceeded with rename across all 7 sites. No silent deletion.
```

### Scenario 4 — Diagnosing a "no errors" report

```
# WRONG — accepting a clean result without health check
Ran pyright on the module. Zero errors. Type analysis confirmed clean.

# CORRECT — verifying server health before accepting clean result
Ran pyright on the module. Zero errors reported. Before concluding clean:
- Checked pyright initialization output: 2 import errors on third-party stubs
  (`boto3-stubs` not installed). This means pyright fell back to `Unknown` for
  all boto3 calls — not `clean`, but `unanalyzed`.
- Installed `boto3-stubs` and re-ran. Now 3 type errors surface in the S3 client
  calls. The original "zero errors" was a false clean due to unresolved stubs.
Finding: CRITICAL — pyright was running in degraded mode. Install stubs before
trusting a clean result on any module that imports third-party libraries.
```

## Anti-Patterns

### 1. Grep-Driven Type Assumptions

**What it looks like:** Agent searches for a symbol name with grep, reads the first few
matches, and infers its type from reading. Finds `user_id: str` somewhere and concludes
all `user_id` parameters across the codebase are `str`.

**Why it fails:** The same name may have different types in different modules. Type aliases
may rename the underlying type. Re-exports may narrow or widen the type at import. A
grep pattern sees the text, not the semantics.

**Recovery:** Use `hover` to query the declared type at each site. If the type differs
from expectation, file a finding. Never assert type correctness from text search alone.

---

### 2. Ignoring LSP Diagnostics as "Noise"

**What it looks like:** Agent or developer sees a large diagnostic count, observes that
the codebase has been "living with these for a while," and treats them as acceptable
background radiation.

**Why it fails:** LSP diagnostic debt compounds. A type error that "has always been
there" is an unverified assumption about safe containment. When it fails — under a new
callers, under a runtime environment change, under a refactor that creates a previously
impossible path — the original diagnostic was the signal.

**Recovery:** Triage diagnostics into: blocking (type errors, nullability violations,
unresolved symbols in production paths) / deferred (unused, deprecated, style) /
expected-generated (codegen output). The blocking tier requires resolution or an
explicit suppression with rationale. The deferred tier gets a tracking ticket. The
expected-generated tier gets a note explaining the generator.

---

### 3. Relying on Heuristics When Precise Information Is Queryable

**What it looks like:** Agent reasons "this function probably returns a string because
it's used in a string context." Does not query LSP hover. Files a finding or approves
the change based on the inference.

**Why it fails:** "Probably" is never the right epistemic state when LSP hover costs one
tool call and returns the declared type in 200ms. Heuristic reasoning introduces false
positives (blocking on a non-issue) and false negatives (missing a real issue that
contradicts the inference).

**Recovery:** Commit to the policy: if the information is queryable, query it. Heuristic
reasoning is acceptable only when the server is down or the file is not indexed. In
that case, say so explicitly: "type-checker unavailable; the following is heuristic."

---

### 4. Treating LSP Output as Authoritative Without Checking Server Health

**What it looks like:** Agent runs diagnostics, gets zero errors, declares the code
type-safe. Does not verify that the server successfully indexed the module. Does not
check for initialization errors or missing stubs.

**Why it fails:** An unhealthy server returns empty results. Empty results look like clean
results. Stale index data from a previous run may not reflect current file state.
Missing type stubs cause third-party calls to resolve to `Unknown`, silently dropping
all type checks on those call paths.

**Recovery:** Before accepting a clean diagnostic result, verify:
- No initialization errors in server output
- All imports in the file under review resolved (not `Unknown` / not-found)
- Server is running against the current file state (not cached)

Report server health status alongside the diagnostic count. "0 errors (pyright
healthy, all imports resolved)" is a different claim than "0 errors."

---

### 5. Using LSP to Confirm What You Already Believe

**What it looks like:** Agent has already decided the code is correct (or incorrect)
and runs a single LSP query that supports the conclusion, stops there.

**Why it fails:** Confirmation bias expressed through tool selection. The agent selects
the one query most likely to return a supportive result and does not run the complementary
queries that could falsify it.

**Recovery:** For structural claims (type safety, interface satisfaction, reference
completeness), run the full complement of relevant queries:
- Diagnostics (are there errors?) AND
- References (does anything call this that was not updated?) AND
- Hover (does the declared type match what callers expect?)

Cite all queries run, not just the one that confirmed the conclusion.

## Acceptance Criteria

A code-analysis task that invokes this skill is complete when:

- [ ] All structural claims (type assertions, "no callers," "fully implements X") are
  backed by a named LSP query result, not by grep or reading inference.
- [ ] All LSP diagnostics relevant to the files touched are triaged: each assigned to
  `filed`, `deferred`, or `expected/generated` with rationale.
- [ ] Any suppression directives (`# type: ignore`, `// @ts-ignore`, `#[allow(...)]`)
  are accompanied by a rationale comment citing the diagnostic code and reason.
- [ ] Server health was verified before accepting a clean diagnostic result.
- [ ] The LSP server and diagnostic codes cited are consistent with the language of the
  files under review (not cross-language confusion).
- [ ] Any "no results" finding (zero references, zero implementations) includes a
  server-health confirmation so the absence-of-evidence is not confused with
  evidence-of-absence.

## Related Skills

- `core/code-review-checklist` — The review framework this skill's evidence standard
  feeds into. LSP diagnostics satisfy the "type-safety finding" evidence requirement
  defined in the Evidence Requirement section of that skill.
- `core/incremental-refactoring` — Refactoring safely requires LSP reference enumeration
  before any rename or type-signature change. This skill provides the LSP query doctrine;
  incremental-refactoring provides the change-sequencing doctrine.
