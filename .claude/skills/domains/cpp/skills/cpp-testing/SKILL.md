---
name: cpp-testing
description: >
  Testing workflow for modern C++ (C++17/20) with GoogleTest / GoogleMock
  driven through CMake and CTest. Covers the red-green-refactor loop, unit
  and integration test layout, fixtures, mocks vs fakes, dependency
  injection for isolation, stable test discovery with gtest_discover_tests,
  coverage collection (gcov/lcov and llvm-cov), the AddressSanitizer /
  UBSan / ThreadSanitizer builds, and guardrails that keep tests
  deterministic and non-flaky. Use when writing or fixing C++ tests, wiring
  a CMake/CTest test target, diagnosing a failing or flaky test, or adding
  coverage or sanitizer gates. Not for feature work with no test change,
  large refactors unrelated to tests, or non-C++ projects.
metadata:
  activation_triggers:
    - "writing or reviewing C++ unit, integration, or fuzz tests"
    - "GoogleTest / GoogleMock usage (TEST, TEST_F, TEST_P, EXPECT_CALL, MOCK_METHOD)"
    - "wiring CTest, gtest_discover_tests, or sanitizer jobs into CMake/CI"
    - "diagnosing a flaky C++ test or raising branch coverage"
  paths:
    - "**/*_test.cpp"
    - "**/*_test.cc"
    - "**/*Test.cpp"
    - "**/tests/**/*.cpp"
    - "**/tests/**/*.cc"
    - "**/test/**/*.cpp"
    - "**/test/**/*.cc"
version: 1.0.0
risk_class: low
source: affaan-m/ecc@81af4076 skills/cpp-testing/
license: MIT
---

# C++ Testing

An agent-facing testing workflow for modern C++ using GoogleTest and
GoogleMock, built and run through CMake with CTest. The goal is a suite that
is deterministic, isolated, fast to iterate on, and honest under sanitizers.

## When to Activate

Use this skill when you are:

- Writing new C++ tests or repairing existing ones.
- Designing unit or integration coverage for a component.
- Wiring a CMake/CTest test target or CI test gate.
- Chasing down a failing or flaky test.
- Turning on coverage measurement or a sanitizer build.

Do not reach for it when the change ships a feature with no test delta, on a
broad refactor with no test-coverage or failure motive, or on a non-C++
project.

## Core Ideas

- **Red-green-refactor.** Write the failing test first, make it pass with
  the smallest change, then clean up while it stays green.
- **Isolation by injection.** Prefer dependency injection and fakes to
  global state; a test should not reach outside its own scope.
- **A predictable layout.** Keep `tests/unit`, `tests/integration`, and
  `tests/testdata` separate so intent and runtime are obvious.
- **Mock vs fake.** Mock when you assert on interactions (a call happened,
  with these arguments); fake when you need stateful behavior stood in for
  a real collaborator.
- **Stable discovery.** Let `gtest_discover_tests()` enumerate tests at
  build time so CTest sees each case individually.
- **A tiered CI signal.** Run the fast subset first, then the full suite
  with `--output-on-failure`.

## The Red-Green-Refactor Loop

1. **Red** — write a test that fails because the behavior does not exist yet.
2. **Green** — add the minimum production code to make it pass.
3. **Refactor** — improve names and structure while the test stays green.

```cpp
// tests/unit/clamp_test.cpp  (RED — clamp_to_range does not exist yet)
#include <gtest/gtest.h>

int clamp_to_range(int value, int lo, int hi);  // declared by production code

TEST(ClampTest, PullsValueUpToLowerBound) {
    EXPECT_EQ(clamp_to_range(-5, 0, 10), 0);
}

// src/clamp.cpp  (GREEN — smallest change that passes)
int clamp_to_range(int value, int lo, int hi) {
    if (value < lo) return lo;
    if (value > hi) return hi;
    return value;
}
// REFACTOR once green: e.g. delegate to std::clamp and delete the branches.
```

## Test Shapes

### A plain unit test

```cpp
// tests/unit/tokenizer_test.cpp
#include <gtest/gtest.h>

std::size_t count_tokens(std::string_view line);  // production code

TEST(TokenizerTest, CountsSpaceSeparatedWords) {
    EXPECT_EQ(count_tokens("alpha beta gamma"), 3u);
}

TEST(TokenizerTest, TreatsEmptyLineAsZeroTokens) {
    EXPECT_EQ(count_tokens(""), 0u);
}
```

Use `ASSERT_*` for a precondition that must hold before the rest of the test
makes sense (it aborts the test on failure); use `EXPECT_*` for independent
checks you want all reported in one run.

### A fixture

A fixture shares setup across related tests. Rebuild state in `SetUp()` so
each test starts clean. The types below are illustrative stand-ins — replace
them with your own.

```cpp
// tests/unit/account_store_test.cpp
#include <gtest/gtest.h>
#include <memory>
#include <optional>
#include <string>

struct Account { std::string owner; long cents; };

class AccountStore {                       // stand-in for the real store
public:
    explicit AccountStore(std::string /*dsn*/) {}
    void seed(std::initializer_list<Account>) {}
    std::optional<Account> find(const std::string& owner) {
        return Account{owner, 0};
    }
};

class AccountStoreTest : public ::testing::Test {
protected:
    void SetUp() override {
        store_ = std::make_unique<AccountStore>(":memory:");
        store_->seed({{"ana", 100}, {"bruno", 250}});
    }
    std::unique_ptr<AccountStore> store_;
};

TEST_F(AccountStoreTest, FindsASeededAccount) {
    auto found = store_->find("ana");
    ASSERT_TRUE(found.has_value());        // precondition — abort if absent
    EXPECT_EQ(found->owner, "ana");
}
```

### A mock (GoogleMock)

Mock an interface to assert on the interaction, then inject the mock through
a reference or pointer.

```cpp
// tests/unit/dispatcher_test.cpp
#include <gmock/gmock.h>
#include <gtest/gtest.h>
#include <string>

class Sink {
public:
    virtual ~Sink() = default;
    virtual void emit(const std::string& event) = 0;
};

class MockSink : public Sink {
public:
    MOCK_METHOD(void, emit, (const std::string& event), (override));
};

class Dispatcher {
public:
    explicit Dispatcher(Sink& sink) : sink_(sink) {}
    void fire(const std::string& event) { sink_.emit(event); }
private:
    Sink& sink_;
};

TEST(DispatcherTest, ForwardsExactlyOneEvent) {
    MockSink sink;
    Dispatcher dispatcher(sink);

    EXPECT_CALL(sink, emit("started")).Times(1);
    dispatcher.fire("started");
}
```

Reach for a mock only when the interaction *is* the behavior under test. For
a stateful collaborator, a hand-written fake is usually clearer and less
brittle than layers of `EXPECT_CALL`.

## Build and Run with CMake / CTest

Pin the framework version to a project-controlled value rather than a moving
tag, so builds are reproducible.

```cmake
# CMakeLists.txt (excerpt)
cmake_minimum_required(VERSION 3.20)
project(example LANGUAGES CXX)

set(CMAKE_CXX_STANDARD 20)
set(CMAKE_CXX_STANDARD_REQUIRED ON)

include(FetchContent)
set(GTEST_TAG v1.15.2)   # pin per project policy; bump deliberately
FetchContent_Declare(
  googletest
  URL https://github.com/google/googletest/archive/refs/tags/${GTEST_TAG}.zip
)
FetchContent_MakeAvailable(googletest)

add_executable(example_tests
  tests/unit/clamp_test.cpp
  src/clamp.cpp
)
target_link_libraries(example_tests
  PRIVATE GTest::gtest GTest::gmock GTest::gtest_main)

enable_testing()
include(GoogleTest)
gtest_discover_tests(example_tests)   # each TEST becomes a CTest case
```

```bash
cmake -S . -B build -DCMAKE_BUILD_TYPE=Debug
cmake --build build -j
ctest --test-dir build --output-on-failure
```

Filter to a subset while iterating — through CTest by name, or through the
gtest binary directly:

```bash
ctest --test-dir build -R "AccountStoreTest.*" --output-on-failure
./build/example_tests --gtest_filter=DispatcherTest.ForwardsExactlyOneEvent
```

## Debugging a Failure

1. Re-run just the failing case with a `--gtest_filter` narrow to it.
2. Add scoped logging around the failing assertion; prefer
   `SCOPED_TRACE` to attach context to a helper that runs multiple checks.
3. Re-run under a sanitizer (below) — many "logic" failures are actually
   memory or race bugs surfacing non-deterministically.
4. Only after the root cause is understood, widen back to the full suite.

## Coverage

Prefer per-target coverage flags to global ones, so instrumentation is
scoped to the code under test.

```cmake
option(ENABLE_COVERAGE "Enable coverage instrumentation" OFF)

if(ENABLE_COVERAGE)
  if(CMAKE_CXX_COMPILER_ID MATCHES "GNU")
    target_compile_options(example_tests PRIVATE --coverage)
    target_link_options(example_tests PRIVATE --coverage)
  elseif(CMAKE_CXX_COMPILER_ID MATCHES "Clang")
    target_compile_options(example_tests PRIVATE
      -fprofile-instr-generate -fcoverage-mapping)
    target_link_options(example_tests PRIVATE -fprofile-instr-generate)
  endif()
endif()
```

GCC with gcov and lcov:

```bash
cmake -S . -B build-cov -DENABLE_COVERAGE=ON
cmake --build build-cov -j
ctest --test-dir build-cov
lcov --capture --directory build-cov --output-file coverage.info
lcov --remove coverage.info '/usr/*' --output-file coverage.info
genhtml coverage.info --output-directory coverage-html
```

Clang with llvm-cov:

```bash
cmake -S . -B build-llvm -DENABLE_COVERAGE=ON -DCMAKE_CXX_COMPILER=clang++
cmake --build build-llvm -j
LLVM_PROFILE_FILE="build-llvm/run.profraw" ctest --test-dir build-llvm
llvm-profdata merge -sparse build-llvm/run.profraw -o build-llvm/run.profdata
llvm-cov report build-llvm/example_tests -instr-profile=build-llvm/run.profdata
```

Keep coverage builds consistent with test builds — measuring coverage on a
debug-only configuration that the suite never otherwise exercises produces
misleading numbers.

## Sanitizers

Run the suite under sanitizers in CI. They catch use-after-free, buffer
overflow, undefined behavior, and data races that a passing assertion hides.

```cmake
option(ENABLE_ASAN  "AddressSanitizer"           OFF)
option(ENABLE_UBSAN "UndefinedBehaviorSanitizer" OFF)
option(ENABLE_TSAN  "ThreadSanitizer"            OFF)

if(ENABLE_ASAN)
  add_compile_options(-fsanitize=address -fno-omit-frame-pointer)
  add_link_options(-fsanitize=address)
endif()
if(ENABLE_UBSAN)
  add_compile_options(-fsanitize=undefined -fno-omit-frame-pointer)
  add_link_options(-fsanitize=undefined)
endif()
if(ENABLE_TSAN)
  add_compile_options(-fsanitize=thread)   # TSan is exclusive of ASan
  add_link_options(-fsanitize=thread)
endif()
```

ASan and TSan cannot be combined in one binary — build a separate
configuration for each. UBSan pairs with ASan.

## Keeping Tests Non-Flaky

Flakiness is a correctness defect in the test, not bad luck. The common
causes and their fixes:

- **Sleeps used for synchronization** → wait on a condition variable, a
  latch, or a future — never `sleep` to "let it settle."
- **Fixed temp paths** → generate a unique temp directory per test and
  clean it up in teardown; two parallel tests must not collide.
- **Wall-clock or timezone dependence** → inject a clock or use a fake time
  source; never assert on `now()`.
- **Real network or filesystem in a unit test** → fake the boundary; keep
  real I/O in clearly labelled integration tests.
- **Randomized input with a fresh seed each run** → fix the seed so a
  failure reproduces.
- **Hidden global state leaking between tests** → reset it in the fixture,
  or remove the global.

## Best Practices

**Do**

- Keep every test deterministic and independent of run order.
- Inject collaborators; avoid singletons and globals in test paths.
- Use `ASSERT_*` for preconditions, `EXPECT_*` for independent checks.
- Split unit from integration via directories or CTest labels.
- Gate CI on a sanitizer build for memory and race coverage.

**Don't**

- Depend on real time, network, or a shared writable filesystem in a unit
  test.
- Use a sleep where a condition variable expresses the wait.
- Over-mock plain value objects — construct them directly.
- Assert on brittle substrings of non-critical log output.

## Optional: Fuzzing and Property Testing

Only when the project already supports the tooling.

- **libFuzzer** suits pure functions with little I/O — a parser, a decoder.
- **RapidCheck** (or similar) expresses invariants as properties checked
  across generated inputs.

A minimal libFuzzer entry point (replace the parse call with yours):

```cpp
#include <cstddef>
#include <cstdint>
#include <string>

extern "C" int LLVMFuzzerTestOneInput(const uint8_t* data, size_t size) {
    std::string input(reinterpret_cast<const char*>(data), size);
    // parse_config(input);   // exercise the function under test
    return 0;
}
```

## Alternatives to GoogleTest

- **Catch2** — header-only, expressive matchers, `SECTION`-based fixtures.
- **doctest** — very lightweight, minimal compile overhead, easy to embed.

## Changelog

- **1.0.0** — Initial release. GoogleTest/GoogleMock testing workflow on
  CMake/CTest: red-green-refactor, unit/fixture/mock shapes, build-and-run,
  failure debugging, coverage (gcov/lcov and llvm-cov), ASan/UBSan/TSan
  builds, anti-flakiness guardrails, and optional fuzz/property testing.
Skill-Import-Attestation: reviewed-by=AE9B236FDAF0462874060C6BCFCFACF00335DC74; sha256=8a0abf6c01614011d66558a3191ff2e6257e638600173c69bd2178c63031380a
