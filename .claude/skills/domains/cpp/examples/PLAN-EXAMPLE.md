---
id: PLAN-EXAMPLE-cpp
title: Migrate the meshcodec module to target-based CMake with pinned GoogleTest and a sanitizer gate
status: draft
created: 2026-07-13
owner: CEO
sprint: example
tags: [cpp, build-migration, example]
---

# PLAN-EXAMPLE — Migrate `meshcodec` to target-based CMake with a sanitizer gate

> Example plan demonstrating how the cpp squad routes work through its
> two-VETO process across all three squad skills. Not for execution.
> Used by adopters as a reference template when proposing a real build
> migration.

## 0. Thesis

`meshcodec` (a C++20 mesh compression module, ~40 kLOC) builds today
through a hand-rolled Makefile: global `CXXFLAGS`, no dependency
pinning, tests run as one opaque binary invocation, and no sanitizer
coverage at all. Migrate it to target-based CMake with pinned
GoogleTest, per-case CTest discovery, an ASan/UBSan/TSan matrix, and a
committed preset flow — without changing runtime behavior.

This plan exists to demonstrate the squad's migration process
end-to-end: `cpp-build-systems` drives phases 1–2 and 6,
`cpp-testing` drives phases 3–4, and `cpp-coding-standards` drives the
findings triage in phases 4–5.

## 1. Phases + owners

| Phase | Owner | Approver | Output |
|---|---|---|---|
| 1. Target inventory + flag policy | Priya Raghavan (Build & Toolchain) | self (VETO) | Target graph + flag-policy doc |
| 2. CMake targets + presets | Priya Raghavan (Build & Toolchain) | self (VETO) | CMakeLists tree + CMakePresets.json |
| 3. Test wiring (pinned GoogleTest + discovery) | Sofia Lindqvist (Test Infrastructure) | Priya Raghavan | Green per-case CTest run |
| 4. Sanitizer matrix + first triage | Tomasz Zieliński (Memory-Safety) | self (VETO) | ASan/UBSan/TSan configs + triaged findings |
| 5. Header/API cleanup surfaced by self-contained builds | Kofi Mensah (Library Interface) | Renata Vasconcelos | Self-contained public headers |
| 6. CI flip + Makefile deletion | Renata Vasconcelos (Head of C++) | Owner (CEO) | CI green on new build; Makefile removed |

## 2. Phase 1 — Target inventory + flag policy

**Owner:** Priya Raghavan (skill: `cpp-build-systems`)

- Inventory the Makefile: enumerate produced artifacts (one library,
  two tools, one test binary), their true source lists (no globs), and
  every flag currently applied globally.
- Classify each flag: correctness flag (keep, per-target), warning flag
  (move to the squad warning set, PRIVATE), dead flag (delete with a
  note).
- Decide the dependency mechanism: `meshcodec` has two third-party
  deps (zlib, fmt) — FetchContent with `URL_HASH` pins, since the repo
  has no existing package manager and both build cleanly from source.

**Acceptance:** Target graph document + flag disposition table
committed under `docs/build-migration/`. Every flag has a stated fate;
every dependency has a proposed immutable pin.

## 3. Phase 2 — CMake targets + presets

**Owner:** Priya Raghavan (skill: `cpp-build-systems`)

- Author the CMakeLists tree: `meshcodec` as a library target with
  `PUBLIC` include of its public header dir, `PRIVATE` everything else;
  tools link `meshcodec::meshcodec` via its ALIAS.
- No directory-scoped commands, no `CMAKE_CXX_FLAGS` writes — verified
  by grep in review (pitfall CPP-013).
- Warning set attached as a PRIVATE interface-target link
  (pitfall CPP-014); `-Werror` behind a `MESH_WERROR` option, ON in CI
  presets only.
- Commit `CMakePresets.json`: `dev` (Ninja, Debug,
  `CMAKE_EXPORT_COMPILE_COMMANDS=ON`), `ci-release`, and the three
  sanitizer presets inheriting from `dev`.

**Acceptance:** `cmake --preset dev && cmake --build --preset dev`
produces byte-identical tool behavior on the golden-file corpus vs the
Makefile build. Build & Toolchain VETO checklist passes (pins, no
global mutation, visibility explicit).

## 4. Phase 3 — Test wiring

**Owner:** Sofia Lindqvist (skill: `cpp-testing`)

- Pin GoogleTest via FetchContent to the project-approved tag with
  `URL_HASH` (pitfall CPP-012 applies to test deps too).
- Replace the single `make check` invocation with
  `gtest_discover_tests(meshcodec_tests)` so each of the ~600 TEST
  cases becomes an individual CTest entry (pitfall CPP-011).
- Sweep for sleep-based synchronization in the existing tests
  (pitfall CPP-008); replace the two found with latch waits.
- Add `ctest --preset dev` to the developer docs; fast-subset label for
  the 40 unit-tier cases that gate pre-commit.

**Acceptance:** `ctest --preset dev --output-on-failure` green with
per-case reporting; suite wall time recorded as the new baseline; no
sleep-based waits remain.

## 5. Phase 4 — Sanitizer matrix + first triage

**Owner:** Tomasz Zieliński (skills: `cpp-coding-standards`,
`cpp-testing`)

- Bring up three separate configs — ASan+UBSan, TSan, and plain
  Release — as presets. ASan and TSan never share a binary
  (pitfall CPP-009).
- First full run WILL find latent issues in a 40 kLOC module that has
  never seen a sanitizer. Triage per `cpp-sanitizer-failure-triage`:
  classify, bisect where possible, fix or file with owner + deadline.
- Expected classes from the dry audit: one unnamed lock guard in the
  codec worker pool (pitfall CPP-005), two C-style casts on buffer
  boundaries (pitfall CPP-004).
- Every fix ships with a regression test that fails under the same
  sanitizer without the fix.

**Acceptance:** ASan/UBSan and TSan presets green in CI; all findings
either fixed-with-regression-test or filed with an owner and a
deadline; zero findings suppressed without a scoped, commented
justification.

## 6. Phase 5 — Header/API cleanup

**Owner:** Kofi Mensah (skill: `cpp-coding-standards`)

- The self-contained-header check (each public header compiled
  standalone) surfaces transitive-include debt: fix each public header
  to include what it uses (SF.11).
- Remove the one `using namespace` found at global scope in
  `mesh_types.h` (pitfall CPP-007).
- Verify zlib/fmt do not leak into public headers — consumers of
  `meshcodec::meshcodec` must not need either on their include path.

**Acceptance:** A consumer TU that includes each public header alone
compiles with only `meshcodec`'s public include dir; no third-party
headers reachable from the public tree.

## 7. Phase 6 — CI flip + Makefile deletion

**Owner:** Renata Vasconcelos

- Run both builds in parallel in CI for five working days; compare
  artifacts and test outcomes daily.
- Flip the required checks to the CMake presets; keep the Makefile job
  as non-blocking for one more week; then delete the Makefile in its
  own PR.
- Record clean + incremental build timings before/after — the
  migration's build-time claims cite these numbers, not impressions
  (pitfall CPP-015).

**Acceptance:** Required CI is the preset flow; Makefile deleted;
timing comparison table in the migration doc; rollback window closed.

## 8. Open questions

1. ccache in CI: adopt now or as a follow-up once cache-hit telemetry
   from developer machines justifies the runner-image change?
2. IPO/LTO for the Release preset: enable behind
   `check_ipo_supported()` now, or defer until the perf suite exists to
   measure it (Per.6 says measure first)?
3. vcpkg later: if the dependency count grows past ~5, revisit the
   FetchContent decision — the rubric in `cpp-build-systems` sets the
   crossover.

## 9. Rollback

- Phases 1–5 are additive: the Makefile remains the CI-required build
  until Phase 6, so rollback is "keep using the Makefile".
- After the Phase 6 flip, rollback is re-enabling the (still present,
  non-blocking) Makefile job within the one-week window; after Makefile
  deletion, rollback is a git revert of the deletion PR.
- Sanitizer findings fixed in Phase 4 are behavior-preserving and do
  not roll back with the build system.
