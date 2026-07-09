---
name: cpp-coding-standards
description: >
  Modern C++ (C++17/20/23) coding standard grounded in the public C++ Core
  Guidelines. Enforces resource safety (RAII), immutability by default,
  strong static typing, value semantics, and intent-revealing interfaces.
  Covers ownership and smart-pointer discipline, the Rule of Zero / Rule of
  Five, const-correctness, scoped enums, exception-safety, concept-constrained
  templates, concurrency locking discipline, header hygiene, and naming.
  Use when authoring, reviewing, or refactoring C++ — when deciding between
  raw and smart pointers, choosing enum vs enum class, sizing a class's
  special members, passing parameters, constraining a template, or locking a
  shared resource. Not for C-only legacy that cannot adopt modern features,
  or bare-metal contexts where a specific guideline conflicts with hardware.
metadata:
  activation_triggers:
    - "authoring, reviewing, or refactoring C++ code"
    - "deciding raw vs smart pointers or ownership transfer"
    - "sizing a class's special members (Rule of Zero / Rule of Five)"
    - "constraining a template (concepts) or choosing enum vs enum class"
    - "locking a shared resource (scoped_lock / lock_guard discipline)"
    - "header hygiene, include discipline, or naming in C++"
  paths:
    - "**/*.cpp"
    - "**/*.cc"
    - "**/*.cxx"
    - "**/*.hpp"
    - "**/*.hh"
    - "**/*.ipp"
    - "**/*.h"                 # C++ header (shared with C; body disambiguates)
version: 1.0.0
risk_class: low
source: affaan-m/ecc@81af4076 skills/cpp-coding-standards/
license: MIT
---

# C++ Coding Standards

A working standard for modern C++ (C++17 and newer) built on the public
[C++ Core Guidelines](https://isocpp.github.io/CppCoreGuidelines/CppCoreGuidelines).
Rule identifiers below (for example `R.20`, `C.21`, `ES.25`) are references
into that public document — consult it for the full rationale. The examples
here are original and illustrate how the standard applies in review.

## When to Activate

Reach for this skill when you are:

- Writing new C++ — a class, free function, template, or module.
- Reviewing or refactoring existing C++ for safety and clarity.
- Deciding between two language features (raw pointer vs smart pointer,
  `enum` vs `enum class`, output parameter vs returned struct).
- Sizing a class's special member functions (destructor, copy, move).
- Constraining a template or picking a parameter-passing convention.
- Locking a resource shared across threads.

Skip it for C-only legacy code that cannot adopt modern C++, and adapt it
selectively on bare-metal or freestanding targets where a specific rule
conflicts with a hardware constraint (document the deviation).

## Six Principles That Drive Every Rule

Almost every specific rule is a consequence of one of these. When a
concrete rule is unclear, fall back to the principle.

1. **Bind every resource to an object's lifetime (RAII).** Acquisition is
   construction; release is destruction. No manual paired cleanup.
   (`P.8`, `R.1`, `E.6`)
2. **Immutable by default.** Start from `const` / `constexpr`; make a thing
   mutable only when you have a reason. (`P.10`, `Con.1`, `ES.25`)
3. **Let the type system catch the bug.** Prefer compile-time errors to
   run-time checks; encode units and invariants in types. (`P.4`, `P.5`,
   `I.4`)
4. **Say what you mean.** Names, signatures, and concepts should carry
   intent without a comment. (`P.1`, `P.3`, `F.1`)
5. **Keep it small.** A function does one thing; a scope stays tight; a
   class exposes the minimum. (`F.2`, `F.3`, `ES.5`, `C.9`)
6. **Value semantics first.** Return by value, hold scoped objects, and
   reserve pointers for non-owning observation. (`C.10`, `R.3`, `F.20`)

## Interfaces (P.*, I.*)

Make an interface tell the caller exactly what it needs and who owns what.
An honest signature removes a class of misuse before the first call.

**Prefer** — a strongly typed, unit-carrying interface that cannot be
called with a bare number:

```cpp
// A distance is not a double. The type prevents mixing units.
struct Meters { double value; };
struct Seconds { double value; };

Meters braking_distance(Meters speed_limit, Seconds reaction);
```

**Avoid** — a weak signature with unclear ownership and unclear units, and
a mutable global that any translation unit can perturb (`I.2`, `I.11`):

```cpp
double braking_distance(double a, double b);  // units? order? meaning?
int g_request_count = 0;                       // non-const global — avoid
```

Guidance worth keeping in muscle memory: interfaces are explicit (`I.1`),
precisely typed (`I.4`), never transfer ownership through a raw pointer or
reference (`I.11`), and keep the argument count low — group related
arguments into a struct once you pass three or four (`I.23`).

## Functions (F.*)

A function performs one logical operation (`F.2`) and stays short enough to
read at a glance (`F.3`). Two decisions recur:

**Parameter passing (`F.16`).** Pass cheap-to-copy types by value; pass
expensive types by `const&`; take a by-value "sink" parameter when the
function will store a moved copy.

```cpp
void set_retry_limit(int limit);                 // cheap: by value
double checksum(const std::vector<std::byte>& b);// expensive: by const&
void adopt_name(std::string name) {              // sink: by value, then move
    name_ = std::move(name);
}
```

**Returning results (`F.20`, `F.21`).** Return values, not output
parameters. To return several values, return a small struct — it names the
fields and composes cleanly.

```cpp
struct SplitHost {
    std::string host;
    int port;
};

SplitHost split_authority(std::string_view authority);  // clear at call site
```

Declare a function `constexpr` when it *can* run at compile time (`F.4`) and
`noexcept` when it *must not* throw (`F.6`); prefer pure functions with no
observable side effects (`F.8`). Never return a reference or pointer to a
local (`F.43`), and do not return `const` by value — it silently blocks
moves (`F.49`).

## Classes and Hierarchies (C.*)

Use `struct` when members vary independently and `class` when an invariant
ties them together (`C.2`). Expose the minimum (`C.9`). The special-member
decision has two clean answers and one trap.

**Rule of Zero (`C.20`) — the default.** If every member already manages
itself, declare no special members and let the compiler synthesize all of
them correctly:

```cpp
struct Invoice {
    std::string customer;
    std::vector<LineItem> lines;
    std::chrono::system_clock::time_point issued;
    // No destructor, no copy/move — the members handle it.
};
```

**Rule of Five (`C.21`) — only when you own a raw resource.** If you write
(or `=delete`) any one of destructor, copy, or move, account for all five.
Here a class owns a POSIX file descriptor:

```cpp
class Fd {
public:
    explicit Fd(int raw) noexcept : fd_(raw) {}

    ~Fd() { close_if_open(); }

    Fd(const Fd&) = delete;             // a descriptor is not copyable
    Fd& operator=(const Fd&) = delete;

    Fd(Fd&& other) noexcept : fd_(std::exchange(other.fd_, -1)) {}
    Fd& operator=(Fd&& other) noexcept {
        if (this != &other) {
            close_if_open();
            fd_ = std::exchange(other.fd_, -1);
        }
        return *this;
    }

    int get() const noexcept { return fd_; }

private:
    void close_if_open() noexcept { if (fd_ >= 0) ::close(fd_); }
    int fd_{-1};
};
```

For polymorphic bases, make the destructor either public-and-virtual or
protected-and-non-virtual (`C.35`), suppress public copy/move on the base
(`C.67`), and mark each overriding function with exactly one of `virtual`,
`override`, or `final` (`C.128`):

```cpp
class Codec {
public:
    virtual ~Codec() = default;
    virtual std::string encode(std::string_view in) const = 0;  // pure
};

class Base64 : public Codec {
public:
    std::string encode(std::string_view in) const override;      // override
};
```

Make single-argument constructors `explicit` (`C.46`) so they do not become
accidental implicit conversions. Do not call virtual functions from a
constructor or destructor (`C.82`) — dynamic dispatch is not yet (or no
longer) wired to the derived type.

## Resource Management (R.*)

RAII is the whole game. Ownership lives in `unique_ptr` or `shared_ptr`
(`R.20`); a raw `T*` is a non-owning observer and nothing more (`R.3`).
Prefer `unique_ptr` and reach for `shared_ptr` only when ownership is
genuinely shared (`R.21`).

```cpp
auto parser  = std::make_unique<Parser>(grammar);   // sole owner
auto session = std::make_shared<Session>(token);     // shared owner

void inspect(const Parser* p) {                       // borrows, owns nothing
    if (p) p->dump();
}
inspect(parser.get());
```

Avoid explicit `new` / `delete` (`R.11`) and `malloc` / `free` (`R.10`) in
C++ code — a smart pointer or a scoped object expresses the intent and can
never leak on an early return or an exception. Prefer scoped stack objects
to heap allocation when the lifetime is local (`R.5`), and do not allocate
two resources in a single expression, which can leak if the second
allocation throws (`R.13`).

## Expressions and Statements (ES.*)

Keep scopes small (`ES.5`) and always initialize (`ES.20`). Default to
brace initialization (`ES.23`), which also rejects narrowing conversions,
and declare objects `const` unless you intend to mutate them (`ES.25`).

```cpp
const int max_attempts{3};
const std::string prefix{"ceo-"};
const std::vector<int> primes{2, 3, 5, 7, 11};

// A lambda initializes a complex const in one immutable step (ES.28).
const auto settings = [&] {
    Settings s;
    s.timeout = std::chrono::seconds{30};
    s.attempts = max_attempts;
    return s;
}();
```

Recurring corrections in review:

- Use `nullptr`, never `0` or `NULL`, for pointers (`ES.47`).
- Replace C-style casts with a named cast — `static_cast`, and only when
  unavoidable `reinterpret_cast` / `const_cast` (`ES.48`); never cast away
  `const` (`ES.50`).
- Name your constants; no magic numbers (`ES.45`).
- Do not mix signed and unsigned arithmetic (`ES.100`); avoid narrowing or
  lossy conversions (`ES.46`).
- Do not shadow a name in a nested scope (`ES.12`).

## Error Handling (E.*)

Decide the error strategy up front (`E.1`). Throw an exception to signal
that a function cannot complete its job (`E.2`), and lean on RAII so a throw
never leaks (`E.6`). Use purpose-built exception types (`E.14`), throw by
value, and catch by reference (`E.15`).

```cpp
class ConfigError : public std::runtime_error {
public:
    using std::runtime_error::runtime_error;
};

class MissingKeyError : public ConfigError {
public:
    explicit MissingKeyError(std::string key)
        : ConfigError("missing key: " + key), key_(std::move(key)) {}
    const std::string& key() const noexcept { return key_; }
private:
    std::string key_;
};

Value require(const Config& cfg, const std::string& key) {
    if (!cfg.contains(key)) throw MissingKeyError(key);   // E.2
    return cfg.at(key);
}

void load() {
    try {
        require(current_config(), "endpoint");
    } catch (const MissingKeyError& e) {                  // catch by reference
        report(e.what(), e.key());
    }
    // Do not blanket-catch here — let the unexpected propagate (E.17).
}
```

Destructors, deallocation, and `swap` must never fail (`E.16`) — mark them
`noexcept`. Do not throw built-in types or string literals (`E.14`), do not
catch by value (slicing), and do not use exceptions for ordinary control
flow (`E.3`).

## Constants and Immutability (Con.*)

Immutable by default, top to bottom: objects (`Con.1`), member functions
(`Con.2`), and pointer/reference parameters (`Con.3`). Use `const` for
values fixed after construction (`Con.4`) and `constexpr` for values a
compiler can fold (`Con.5`).

```cpp
class Thermostat {
public:
    explicit Thermostat(std::string id) : id_(std::move(id)) {}

    const std::string& id() const { return id_; }         // Con.2
    double current() const { return reading_; }

    void observe(double celsius) { reading_ = celsius; }   // only non-const

private:
    const std::string id_;   // Con.4: fixed after construction
    double reading_{0.0};
};

constexpr double kAbsoluteZeroC = -273.15;   // Con.5
```

## Concurrency (CP.*)

Think in tasks, not raw threads (`CP.4`), and minimize writable data shared
across them (`CP.2`, `CP.3`). Every lock is RAII and every lock guard is
named — an unnamed guard is a temporary that unlocks immediately (`CP.20`,
`CP.44`). Wait only on a predicate (`CP.42`).

```cpp
class BoundedCounter {
public:
    void increment() {
        std::lock_guard<std::mutex> lock(m_);   // named — held to scope end
        ++count_;
    }

    int drain() {
        std::unique_lock<std::mutex> lock(m_);
        cv_.wait(lock, [this] { return count_ > 0; });  // predicate, CP.42
        return std::exchange(count_, 0);
    }

private:
    std::mutex m_;                 // mutex sits with the data it guards
    std::condition_variable cv_;
    int count_{0};
};
```

Take multiple mutexes with `std::scoped_lock`, which orders them to avoid
deadlock (`CP.21`):

```cpp
void transfer(Account& from, Account& to, Money amount) {
    std::scoped_lock lock(from.m, to.m);   // deadlock-free acquisition
    from.balance -= amount;
    to.balance   += amount;
}
```

Do not use `volatile` for synchronization — it is for memory-mapped
hardware, not threads (`CP.8`). Do not call unknown code (a user callback)
while holding a lock (`CP.22`). Avoid detached threads (`CP.26`) and
lock-free programming (`CP.100`) unless there is no alternative.

## Templates and Generics (T.*)

Constrain every template parameter with a concept (`T.10`), preferring the
standard concepts (`T.11`). Concepts move a cryptic instantiation failure to
a clear, early diagnostic at the call site.

```cpp
#include <concepts>

template <std::integral T>
constexpr T gcd(T a, T b) noexcept {
    while (b != T{0}) { a = std::exchange(b, a % b); }
    return a;
}

// A domain concept states the requirement a type must satisfy.
template <typename T>
concept Encodable = requires(const T& t) {
    { t.to_bytes() } -> std::convertible_to<std::vector<std::byte>>;
};

template <Encodable T>
void persist(const T& value, const Path& where);
```

Prefer `using` aliases over `typedef` (`T.43`), overload rather than
specialize a function template (`T.144`), and reserve template
metaprogramming for cases where `constexpr` genuinely cannot do the job
(`T.120`).

## Standard Library (SL.*)

Prefer the standard library to hand-rolled equivalents (`SL.1`, `SL.2`).
Use `std::vector` by default and `std::array` for fixed size (`SL.con.1`,
`SL.con.2`); `std::string` owns characters and `std::string_view` observes
them (`SL.str.1`, `SL.str.2`). Write `'\n'` rather than `std::endl`, which
forces an unwanted flush on every line (`SL.io.50`).

```cpp
std::string greet(std::string_view who) {        // view in, owned string out
    return "hello, " + std::string(who);
}
std::cout << greet("world") << '\n';             // '\n', not std::endl
```

## Enumerations (Enum.*)

Prefer enumerations to macros (`Enum.1`) and scoped `enum class` to plain
`enum` (`Enum.3`) — scoping prevents name leakage and accidental integer
conversions. Do not spell enumerators in ALL_CAPS (`Enum.5`).

```cpp
enum class Severity { trace, info, warning, error };   // scoped, not ALL_CAPS

// Avoid: leaks names into the enclosing scope and collides with macros.
enum { RED, GREEN, BLUE };
```

## Headers and Naming (SF.*, NL.*)

A header is self-contained — it includes everything it uses (`SF.11`) — and
is protected by an include guard or `#pragma once` (`SF.8`). Never put
`using namespace` at global scope in a header (`SF.7`). Pick one consistent
naming style (`NL.8`), reserve ALL_CAPS for macros only (`NL.9`), and do not
encode types into names (no Hungarian notation) (`NL.5`).

```cpp
#ifndef CEO_NET_TCP_CONNECTION_H
#define CEO_NET_TCP_CONNECTION_H

#include <string>
#include <string_view>

namespace ceo::net {

class tcp_connection {
public:
    explicit tcp_connection(std::string host, int port);
    void send(std::string_view payload);
    bool is_open() const;

private:
    std::string host_;   // trailing underscore marks a data member
    int port_;
};

}  // namespace ceo::net

#endif  // CEO_NET_TCP_CONNECTION_H
```

## Performance (Per.*)

Do not optimize without a reason (`Per.1`), do not optimize prematurely
(`Per.2`), and never claim a speedup without a measurement (`Per.6`). When
you do optimize, move work from run time to compile time (`Per.11`) and lay
data out for predictable, contiguous access (`Per.19`).

```cpp
// Build a lookup table once, at compile time (Per.11).
constexpr auto squares = [] {
    std::array<int, 256> t{};
    for (int i = 0; i < 256; ++i) t[i] = i * i;
    return t;
}();

std::vector<Point> hot_path;                       // contiguous — cache-friendly
std::vector<std::unique_ptr<Point>> pointer_chase; // avoid on a hot path
```

## Review Checklist

Before you call C++ work done:

- [ ] No raw `new` / `delete`; ownership is in a smart pointer or scoped
      object (`R.11`).
- [ ] Every object is initialized where it is declared (`ES.20`).
- [ ] Objects and member functions are `const` / `constexpr` by default
      (`Con.1`, `Con.2`, `ES.25`).
- [ ] `enum class`, not plain `enum` (`Enum.3`); `nullptr`, not `0`/`NULL`
      (`ES.47`).
- [ ] No narrowing conversions (`ES.46`) and no C-style casts (`ES.48`).
- [ ] Single-argument constructors are `explicit` (`C.46`).
- [ ] Rule of Zero, or a complete Rule of Five (`C.20`, `C.21`).
- [ ] Polymorphic base destructors are public-virtual or
      protected-non-virtual (`C.35`); overrides marked `override` (`C.128`).
- [ ] Template parameters are concept-constrained (`T.10`).
- [ ] No `using namespace` in a header at global scope (`SF.7`); headers are
      guarded and self-contained (`SF.8`, `SF.11`).
- [ ] Locks are RAII and named (`CP.20`, `CP.44`).
- [ ] Exceptions are custom types, thrown by value, caught by reference
      (`E.14`, `E.15`).
- [ ] `'\n'` instead of `std::endl` (`SL.io.50`); no magic numbers (`ES.45`).

## Changelog

- **1.0.0** — Initial release. Modern-C++ coding standard grounded in the
  public C++ Core Guidelines, covering the six cross-cutting principles plus
  interfaces, functions, classes, resource management, expressions, error
  handling, immutability, concurrency, templates, standard library,
  enumerations, headers/naming, performance, and a review checklist.
Skill-Import-Attestation: reviewed-by=AE9B236FDAF0462874060C6BCFCFACF00335DC74; sha256=5a8a0d0436db6fb5c1c8231c0000a441af1b6521dcfb0c132f02183cc2dc5818
