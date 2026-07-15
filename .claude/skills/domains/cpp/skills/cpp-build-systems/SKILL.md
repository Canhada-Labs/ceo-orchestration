---
name: cpp-build-systems
description: >
  Modern CMake and C++ build/toolchain discipline for C++17/20/23 projects.
  Enforces target-based CMake (usage requirements with PRIVATE / PUBLIC /
  INTERFACE visibility, no global flag mutation), pinned dependency
  management (FetchContent with immutable refs, vcpkg manifests with a
  builtin-baseline, Conan lockfiles), per-target warning and hardening
  flag sets, compile_commands.json plus clang-tidy / clang-format wiring,
  build acceleration (ccache, IPO/LTO via CheckIPOSupported), and
  reproducible configure/build/test flows through CMakePresets.json across
  single- and multi-config generators. Use when writing or reviewing
  CMakeLists.txt, adding or upgrading a third-party dependency, wiring
  lint or sanitizer tooling into the build, tuning build times, or
  standardizing builds across developer machines and CI. Not for
  non-CMake build systems (Bazel, Meson) beyond migration triage, and not
  for test authoring itself — that is cpp-testing's scope.
metadata:
  activation_triggers:
    - "writing or reviewing CMakeLists.txt or *.cmake modules"
    - "adding, upgrading, or pinning a third-party C++ dependency"
    - "choosing between FetchContent, vcpkg, and Conan"
    - "wiring clang-tidy, clang-format, or compile_commands.json into a build"
    - "configuring warning, hardening, or -Werror flag policy"
    - "build-time tuning (ccache, LTO/IPO) or CMakePresets standardization"
  paths:
    - "**/CMakeLists.txt"
    - "**/*.cmake"
    - "**/CMakePresets.json"
    - "**/CMakeUserPresets.json"
    - "**/vcpkg.json"
    - "**/conanfile.txt"
    - "**/conanfile.py"
version: 1.0.0
risk_class: low
---

# C++ Build Systems

An agent-facing discipline for building modern C++ through CMake. The two
sibling skills in this squad both lean on the build: `cpp-coding-standards`
assumes warnings and hardening are wired, and `cpp-testing` drives
everything "through CMake and CTest". This skill is where that wiring is
specified. The goal is a build that is target-based, pinned, tooling-visible,
and reproducible on any machine from one committed preset.

## When to Activate

Reach for this skill when you are:

- Writing or reviewing `CMakeLists.txt` or `*.cmake` modules.
- Adding, upgrading, or pinning a third-party dependency.
- Choosing a dependency mechanism (FetchContent vs vcpkg vs Conan).
- Setting warning, `-Werror`, or hardening flag policy.
- Wiring `compile_commands.json`, clang-tidy, or clang-format.
- Tuning build times (ccache, IPO/LTO) or standardizing configure /
  build / test flows with `CMakePresets.json`.

Skip it for non-CMake build systems (Bazel, Meson) beyond triaging a
migration, and for test authoring itself — fixtures, mocks, and coverage
live in `cpp-testing`.

## Five Principles That Drive Every Rule

1. **Everything is a target.** Flags, includes, definitions, and
   dependencies attach to targets with explicit visibility — never to a
   directory, never to a global variable.
2. **Usage requirements are the API of the build.** `PUBLIC` /
   `PRIVATE` / `INTERFACE` state exactly what a consumer inherits; a
   wrong visibility is a wrong contract.
3. **Pin the bytes, not the name.** Every dependency resolves to an
   immutable ref — a commit SHA, a content hash, a baseline, a lockfile.
   A branch name is a race condition.
4. **The build is where tooling sees the truth.** clang-tidy, sanitizers,
   and coverage must consume the same flags the real build uses —
   `compile_commands.json` is the single source of that truth.
5. **Reproducible means committed.** If the configure line lives in a
   wiki or someone's shell history, the build is not reproducible.
   Presets put it in the repo.

## Targets and Usage Requirements

The visibility keyword answers one question: *who needs this — me, my
consumers, or both?*

| Keyword | Applies when building the target | Propagates to consumers |
|---|---|---|
| `PRIVATE` | yes | no |
| `INTERFACE` | no | yes |
| `PUBLIC` | yes | yes |

**Prefer** — a library whose public surface is exactly its public
include directory, with everything else private:

```cmake
add_library(ceo_net STATIC
  src/tcp_connection.cpp
  src/resolver.cpp
)
add_library(ceo::net ALIAS ceo_net)   # consumers link the namespaced name

target_compile_features(ceo_net PUBLIC cxx_std_20)  # consumers need C++20 too

target_include_directories(ceo_net
  PUBLIC
    $<BUILD_INTERFACE:${CMAKE_CURRENT_SOURCE_DIR}/include>
    $<INSTALL_INTERFACE:include>
  PRIVATE
    ${CMAKE_CURRENT_SOURCE_DIR}/src
)

target_link_libraries(ceo_net
  PRIVATE ZLIB::ZLIB          # implementation detail — consumers never see it
)
```

**Avoid** — directory-scoped commands and global variable surgery. They
apply to every target defined afterwards in that directory tree,
including ones added later by someone who never sees this line:

```cmake
include_directories(src)                            # leaks to everything
add_definitions(-DMESH_INTERNAL)                    # leaks to everything
set(CMAKE_CXX_FLAGS "${CMAKE_CXX_FLAGS} -O3")       # global string surgery
link_libraries(z)                                   # legacy, unscoped
```

Two recurring rules:

- **List sources explicitly.** `file(GLOB ...)` does not re-run at build
  time, so a new file silently fails to build until someone re-configures;
  `CONFIGURE_DEPENDS` patches that at a per-generator cost and still hides
  the source list from review. Write the filenames.
- **Never reference `${CMAKE_SOURCE_DIR}` inside a library.** It points at
  whoever is the top-level project — wrong the moment your library is
  consumed via `add_subdirectory` or FetchContent. Use
  `CMAKE_CURRENT_SOURCE_DIR` or `PROJECT_SOURCE_DIR`.
- **Guard top-level-only concerns.** Tests, docs, and install rules of a
  reusable library run only when it is the top project:

```cmake
if(PROJECT_IS_TOP_LEVEL)      # CMake >= 3.21
  enable_testing()
  add_subdirectory(tests)
endif()
```

## Dependency Management

One repo, one mechanism. Mixing FetchContent, vcpkg, and Conan in the same
build produces duplicate, ABI-mismatched copies of common transitive deps.

### FetchContent — pinned to the bytes

Good for a handful of well-behaved, build-from-source dependencies. Pin
with an archive URL plus `URL_HASH` (content-addressed — the strongest
pin), or a full 40-character commit SHA. Never a branch, never a moving
tag.

```cmake
include(FetchContent)

FetchContent_Declare(
  fmt
  URL      https://github.com/fmtlib/fmt/archive/refs/tags/11.1.4.zip
  URL_HASH SHA256=<sha256-of-the-verified-download>   # pin the bytes
)
FetchContent_MakeAvailable(fmt)

target_link_libraries(ceo_net PRIVATE fmt::fmt)
```

```cmake
# Git form: full commit SHA only. A tag can be re-pointed; a SHA cannot.
FetchContent_Declare(
  googletest
  GIT_REPOSITORY https://github.com/google/googletest.git
  GIT_TAG        b514bdc898e2951020cbdca1304b75f5950d1f59   # full SHA
)
```

### vcpkg — manifest mode with a baseline

Right when the dependency count grows, the deps are heavy (you want
binary caching), or several repos must share one version policy. The
manifest (`vcpkg.json`) lives in the repo and the `builtin-baseline`
commit pins the entire registry's version set:

```json
{
  "name": "your-app",
  "dependencies": [
    "fmt",
    { "name": "openssl", "version>=": "3.0.0" }
  ],
  "builtin-baseline": "<40-hex vcpkg registry commit>"
}
```

Wire the toolchain file through a preset (below), not through
developer-remembered `-DCMAKE_TOOLCHAIN_FILE=...` flags.

### Conan — lockfiles committed

Same problem class as vcpkg with stronger lockfile semantics and
first-class custom binary remotes. If chosen: `conanfile.txt` (or `.py`)
declares, `conan lock create` resolves, and the resulting `conan.lock`
is committed and consumed by CI.

### Decision rubric

- **≤ ~5 deps, all build cleanly from source, no cross-repo policy** →
  FetchContent. One `cmake` invocation, no extra tool.
- **Many or heavy deps, binary caching wanted, org-wide baseline** →
  vcpkg manifest mode.
- **Custom binary remotes / strict lockfile workflows already in the
  org** → Conan.
- Re-evaluate at the crossover, and migrate wholesale — never
  incrementally into a two-manager build.

## Warning and Hardening Flags

Carry the warning set on an INTERFACE target and link it `PRIVATE`, so
your own translation units get the policy and consumers inherit nothing
(a library must never export its warning policy):

```cmake
add_library(ceo_warnings INTERFACE)
target_compile_options(ceo_warnings INTERFACE
  $<$<CXX_COMPILER_ID:GNU,Clang,AppleClang>:-Wall;-Wextra;-Wpedantic;-Wconversion;-Wshadow>
  $<$<CXX_COMPILER_ID:MSVC>:/W4;/permissive->
)

option(CEO_WERROR "Treat warnings as errors (enable in CI presets)" OFF)
if(CEO_WERROR)
  target_compile_options(ceo_warnings INTERFACE
    $<IF:$<CXX_COMPILER_ID:MSVC>,/WX,-Werror>)
endif()

target_link_libraries(ceo_net PRIVATE ceo_warnings)   # PRIVATE — no leakage
```

`-Werror` is ON in CI presets and OFF by default: a future compiler with
new warnings must not break downstream builds you do not control. Fix or
minimally-scope-and-comment a warning; never disable a class repo-wide
with `-Wno-*` to get a green build.

Baseline hardening for released binaries (measure and adapt per target
platform):

```cmake
# Applies to the executable target; _FORTIFY_SOURCE requires optimization.
target_compile_definitions(mesh_tool PRIVATE
  $<$<CONFIG:Release,RelWithDebInfo>:_FORTIFY_SOURCE=3>)
target_compile_options(mesh_tool PRIVATE
  $<$<CXX_COMPILER_ID:GNU,Clang>:-fstack-protector-strong>)

include(CheckPIESupported)
check_pie_supported()
set_property(TARGET mesh_tool PROPERTY POSITION_INDEPENDENT_CODE TRUE)

if(CMAKE_SYSTEM_NAME STREQUAL "Linux")
  target_link_options(mesh_tool PRIVATE -Wl,-z,relro -Wl,-z,now)
endif()
```

Sanitizer configurations (`ENABLE_ASAN` / `ENABLE_UBSAN` / `ENABLE_TSAN`)
are specified in `cpp-testing` — this skill's job is to expose them as
presets and keep ASan and TSan in separate binaries.

## Tooling: compile_commands.json, clang-tidy, clang-format

Export the compilation database so every tool sees the flags the real
build uses (Makefile and Ninja generators only):

```bash
cmake -S . -B build -G Ninja -DCMAKE_EXPORT_COMPILE_COMMANDS=ON
ln -sf build/compile_commands.json .   # editors and LSPs find it at the root
```

Run clang-tidy against that database — never against a hand-maintained
flag list, which drifts and produces a false clean:

```bash
run-clang-tidy -p build                       # whole project, parallel
clang-tidy -p build src/tcp_connection.cpp    # one file while iterating
```

Configuration lives in a committed `.clang-tidy` at the repo root; treat
check additions like flag policy (Build & Toolchain review). For
always-on enforcement, attach it per target — accepting the compile-time
cost consciously:

```cmake
option(ENABLE_CLANG_TIDY "Run clang-tidy as part of compilation" OFF)
if(ENABLE_CLANG_TIDY)
  find_program(CLANG_TIDY_EXE clang-tidy REQUIRED)
  set_target_properties(ceo_net PROPERTIES CXX_CLANG_TIDY "${CLANG_TIDY_EXE}")
endif()
```

Formatting is not a review topic — it is a gate. A committed
`.clang-format`, and in CI:

```bash
clang-format --dry-run --Werror $(git ls-files '*.cpp' '*.h' '*.hpp')
```

## Build Acceleration: ccache and IPO/LTO

ccache is a launcher, not a CMakeLists concern — inject it per machine or
per preset so developers without ccache are unaffected:

```bash
cmake -S . -B build -DCMAKE_CXX_COMPILER_LAUNCHER=ccache
```

IPO/LTO is a measured Release-only decision, guarded by the support
check — some toolchains silently miscombine without it:

```cmake
include(CheckIPOSupported)
check_ipo_supported(RESULT ipo_ok OUTPUT ipo_msg)
if(ipo_ok)
  set_property(TARGET mesh_tool
               PROPERTY INTERPROCEDURAL_OPTIMIZATION_RELEASE TRUE)
else()
  message(STATUS "IPO not supported: ${ipo_msg}")
endif()
```

Per `Per.6` in `cpp-coding-standards`: no speedup claim without a
measurement. A build-acceleration PR ships clean-build and
incremental-build timings, before and after, plus a green test run
proving behavior is unchanged.

## Reproducible Builds with Presets

`CMakePresets.json` is committed and is the single documented way to
configure, build, and test. `CMakeUserPresets.json` is personal and
gitignored.

```json
{
  "version": 4,
  "configurePresets": [
    {
      "name": "dev",
      "generator": "Ninja",
      "binaryDir": "${sourceDir}/build/dev",
      "cacheVariables": {
        "CMAKE_BUILD_TYPE": "Debug",
        "CMAKE_EXPORT_COMPILE_COMMANDS": "ON"
      }
    },
    {
      "name": "ci-release",
      "inherits": "dev",
      "binaryDir": "${sourceDir}/build/ci-release",
      "cacheVariables": { "CMAKE_BUILD_TYPE": "Release", "CEO_WERROR": "ON" }
    },
    {
      "name": "ci-asan",
      "inherits": "dev",
      "binaryDir": "${sourceDir}/build/ci-asan",
      "cacheVariables": { "ENABLE_ASAN": "ON", "ENABLE_UBSAN": "ON", "CEO_WERROR": "ON" }
    },
    {
      "name": "ci-tsan",
      "inherits": "dev",
      "binaryDir": "${sourceDir}/build/ci-tsan",
      "cacheVariables": { "ENABLE_TSAN": "ON", "CEO_WERROR": "ON" }
    }
  ],
  "buildPresets": [
    { "name": "dev", "configurePreset": "dev" }
  ],
  "testPresets": [
    { "name": "dev", "configurePreset": "dev",
      "output": { "outputOnFailure": true } }
  ]
}
```

```bash
cmake --preset dev
cmake --build --preset dev
ctest --preset dev
```

Single- vs multi-config matters here: `CMAKE_BUILD_TYPE` is honored by
single-config generators (Makefiles, Ninja) and **ignored** by
multi-config ones (Visual Studio, Xcode, Ninja Multi-Config), which take
`--config` at build time instead. Write configuration-dependent logic as
generator expressions (`$<CONFIG:Release>`), never as
`if(CMAKE_BUILD_TYPE STREQUAL "Release")` — the latter is silently wrong
on multi-config generators.

## Anti-patterns

- `file(GLOB ...)` for source lists — new files silently unbuilt until
  re-configure; source lists invisible in review.
- Directory-scoped commands (`include_directories`, `add_definitions`,
  `add_compile_options`, `link_libraries`) in a library directory.
- String surgery on `CMAKE_CXX_FLAGS` or any global flag variable.
- `GIT_TAG main` / `GIT_TAG master` / a re-pointable release tag as a
  dependency pin.
- Warning or `-Werror` flags with `PUBLIC` / `INTERFACE` visibility.
- `${CMAKE_SOURCE_DIR}` paths inside a reusable library.
- Building tests unconditionally when consumed via `add_subdirectory`
  or FetchContent (guard with `PROJECT_IS_TOP_LEVEL`).
- A second package manager introduced "just for this one dep".
- clang-tidy configured with hand-copied flags instead of the
  compilation database.
- ASan and TSan combined into one binary to "save a CI job".

## Review Checklist

Before you call build-system work done:

- [ ] Every flag, include, definition, and link is on a target with an
      explicit visibility keyword — zero directory-scoped commands.
- [ ] Warning set linked `PRIVATE`; `-Werror` behind an option, ON only
      in CI presets.
- [ ] Every dependency pinned to an immutable ref (`URL_HASH`, full
      commit SHA, vcpkg `builtin-baseline`, or committed Conan lockfile).
- [ ] One package manager per repo; namespaced (`ns::target`) link names.
- [ ] Source files listed explicitly — no `file(GLOB)`.
- [ ] Library CMake uses `CMAKE_CURRENT_SOURCE_DIR` /
      `PROJECT_SOURCE_DIR`, never `CMAKE_SOURCE_DIR`.
- [ ] Tests and install rules guarded by `PROJECT_IS_TOP_LEVEL`.
- [ ] `CMAKE_EXPORT_COMPILE_COMMANDS=ON` in the dev preset; clang-tidy
      consumes the database.
- [ ] `CMakePresets.json` committed and covers dev + CI + sanitizer
      configs; `CMakeUserPresets.json` gitignored.
- [ ] Config-dependent logic uses generator expressions, not
      `if(CMAKE_BUILD_TYPE ...)`.
- [ ] Any build-speed claim carries before/after timings (clean and
      incremental) and a green test run.

## Changelog

- **1.0.0** — Initial release. Target-based CMake with usage
  requirements, explicit source lists, top-level guards; pinned
  dependency management (FetchContent / vcpkg / Conan) with a decision
  rubric; PRIVATE warning and hardening flag policy; compile_commands /
  clang-tidy / clang-format wiring; ccache and checked IPO/LTO;
  reproducible preset-driven flows across single- and multi-config
  generators; anti-patterns and a review checklist.
