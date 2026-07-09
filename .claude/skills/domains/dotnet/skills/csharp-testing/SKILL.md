---
name: csharp-testing
description: >
  Testing discipline for C# / .NET applications. Covers the modern test stack
  (xUnit, an assertion library, an isolation/mocking library, WebApplicationFactory
  and Testcontainers for integration), Arrange-Act-Assert unit structure with the
  system-under-test convention, parameterized tests (Theory / InlineData / MemberData /
  strongly-typed TheoryData), interaction verification and stubbing, ASP.NET Core
  in-process integration tests, real-infrastructure integration via ephemeral
  containers, test-project layout, data builders, and a catalogue of anti-patterns.
  Use when writing or reviewing tests for C# code, standing up a .NET test suite,
  choosing an assertion or mocking library, or debugging flaky / slow .NET tests.
owner: .NET Test Engineer (domain persona)
tier: domain:dotnet
version: 1.0.0
scope_tags: [dotnet, csharp, testing, xunit, integration-tests, mocking]
inspired_by:
  - source: affaan-m/ecc/skills/csharp-testing@81af40761939056ab3dc54732fd4f562a27309d0
    license: MIT
    relationship: structural_inspiration
    authored_by: ceo-orchestration framework
    authored_at: 2026-07-07
# --- smart-loading fields (PLAN-083 Wave 0b shape) ---
domain: dotnet
priority: 8
risk_class: low
stack: [csharp, dotnet]
context_budget_tokens: 700
inactive_but_retained: true
repo_profile_binding:
  frontend: {active: false, priority: 10}
  engine: {active: false, priority: 10}
  fintech: {active: false, priority: 10}
  trading-readonly: {active: false, priority: 10}
  generic: {active: false, priority: 10}
# --- machine-first activation (native file-touch + intent) ---
activation_triggers:
  - {event: file-edit, glob: "**/*Tests.cs"}
  - {event: file-edit, glob: "**/*Test.cs"}
  - {event: file-edit, glob: "**/*.Tests.csproj"}
  - {event: help-me-invoked, regex: "(?i)xunit|nunit|fluentassert|nsubstitute|\\bmoq\\b|testcontainers|webapplicationfactory"}
source: affaan-m/ecc@81af4076 skills/csharp-testing/
license: MIT
---

# C# / .NET Testing

Patterns for a maintainable .NET test suite: fast, isolated unit tests that
assert on behaviour, plus a smaller ring of integration tests that exercise the
real HTTP pipeline and real infrastructure.

## When to Activate

Read this skill when you are:

- writing or reviewing tests for C# code (unit, integration, or end-to-end);
- standing up a test project for a new .NET service or library;
- choosing between assertion or isolation libraries, or migrating between them;
- diagnosing flaky, order-dependent, or slow .NET tests;
- editing files matched by the machine triggers in the frontmatter
  (`**/*Tests.cs`, `**/*Test.cs`, `**/*.Tests.csproj`).

The machine-first `activation_triggers` frontmatter is the canonical auto-load
rule; this section is its human-scannable mirror.

## The Test Stack

.NET has no single blessed stack, but these choices are conventional and
compose well. Pick per project and keep it consistent across the solution.

| Concern | Common choice | Notes |
|---|---|---|
| Test runner | **xUnit** | Constructor = setup, `IDisposable`/`IAsyncLifetime` = teardown; parallel by default. NUnit and MSTest are valid alternatives. |
| Assertions | An expressive assertion library | Improves failure messages and readability. See the licensing caveat below before standardising. |
| Isolation / mocking | **NSubstitute** or **Moq** | Substitute collaborators behind interfaces; verify interactions. |
| HTTP integration | **WebApplicationFactory<T>** | Boots the real ASP.NET Core pipeline in-process — no sockets. |
| Real infrastructure | **Testcontainers** | Spins up a throwaway database/broker in Docker for repository tests. |
| Test data | A fake-data generator, or hand-rolled builders | Keep generation deterministic (seed it) so failures reproduce. |

> **Assertion-library licensing caveat (honesty residual).** The C# assertion
> library landscape shifted recently: at least one popular fluent-assertion
> package changed its licence to a paid/commercial model for its newer major
> version, which prompted community OSS forks. Before you add an assertion
> package to a project, confirm the licence of the exact version you pin — do
> not assume "it was free last year" still holds. The *patterns* in this skill
> are library-agnostic; the package name is a swappable detail.

## Unit Test Structure

Use **Arrange-Act-Assert**. Name the class under test `_sut`
(system-under-test) so the three phases read clearly. In xUnit the test-class
constructor gives you a fresh instance per test method, so there is no shared
mutable state to reset.

```csharp
public sealed class SubscriptionServiceTests
{
    private readonly ISubscriptionRepository _repo = Substitute.For<ISubscriptionRepository>();
    private readonly IClock _clock = Substitute.For<IClock>();
    private readonly SubscriptionService _sut;

    public SubscriptionServiceTests()
    {
        _clock.UtcNow.Returns(new DateTimeOffset(2026, 1, 1, 0, 0, 0, TimeSpan.Zero));
        _sut = new SubscriptionService(_repo, _clock);
    }

    [Fact]
    public async Task Renew_ExtendsPeriod_WhenSubscriptionIsActive()
    {
        // Arrange
        var sub = new Subscription(Guid.NewGuid(), SubscriptionState.Active,
            renewsOn: new DateOnly(2026, 1, 15));
        _repo.FindAsync(sub.Id, Arg.Any<CancellationToken>()).Returns(sub);

        // Act
        var result = await _sut.RenewAsync(sub.Id, CancellationToken.None);

        // Assert — one logical outcome
        Assert.True(result.Succeeded);
        Assert.Equal(new DateOnly(2026, 2, 15), result.Value.RenewsOn);
    }

    [Fact]
    public async Task Renew_Fails_WhenSubscriptionIsCancelled()
    {
        var sub = new Subscription(Guid.NewGuid(), SubscriptionState.Cancelled,
            renewsOn: new DateOnly(2026, 1, 15));
        _repo.FindAsync(sub.Id, Arg.Any<CancellationToken>()).Returns(sub);

        var result = await _sut.RenewAsync(sub.Id, CancellationToken.None);

        Assert.False(result.Succeeded);
        Assert.Contains("cancelled", result.Error, StringComparison.OrdinalIgnoreCase);
    }
}
```

Assertion style is interchangeable: the raw `Assert.*` calls above read fine,
and a fluent library would render the same checks as
`result.Succeeded.Should().BeTrue()` (or the equivalent in whichever package you
adopt). Choose one convention per solution.

## Parameterized Tests

Collapse near-identical cases into a single `[Theory]`. Use `[InlineData]` for
scalar cases and a strongly-typed data source for complex objects — a typed data
source keeps the compiler checking your cases and gives readable names in the
test explorer.

```csharp
[Theory]
[InlineData(0, false)]     // empty cart
[InlineData(1, true)]
[InlineData(99, true)]
[InlineData(-1, false)]    // guard against negatives
public void CanCheckout_ReflectsItemCount(int itemCount, bool expected) =>
    Assert.Equal(expected, Cart.WithItems(itemCount).CanCheckout);

[Theory]
[MemberData(nameof(InvalidPlans))]
public async Task Subscribe_Rejects_InvalidPlan(SubscribeRequest request, string expectedError)
{
    var result = await _sut.SubscribeAsync(request, CancellationToken.None);

    Assert.False(result.Succeeded);
    Assert.Contains(expectedError, result.Error);
}

public static TheoryData<SubscribeRequest, string> InvalidPlans => new()
{
    { new SubscribeRequest(CustomerId: "", PlanCode: "PRO"), "CustomerId" },
    { new SubscribeRequest(CustomerId: "c-1", PlanCode: ""),  "PlanCode" },
    { new SubscribeRequest(CustomerId: "c-1", PlanCode: "??"), "unknown plan" },
};
```

## Isolation: Stubbing and Interaction Verification

Substitute collaborators behind their interfaces. Distinguish **state
verification** (assert on what the SUT returned) from **interaction
verification** (assert the SUT called a collaborator correctly) — reach for the
latter only when the side effect *is* the behaviour under test, otherwise you
couple the test to implementation.

```csharp
[Fact]
public async Task Cancel_PersistsCancellation()
{
    var id = Guid.NewGuid();
    _repo.FindAsync(id, Arg.Any<CancellationToken>())
         .Returns(new Subscription(id, SubscriptionState.Active, new DateOnly(2026, 6, 1)));

    await _sut.CancelAsync(id, CancellationToken.None);

    // Interaction verification: the state change was written back exactly once.
    await _repo.Received(1).SaveAsync(
        Arg.Is<Subscription>(s => s.State == SubscriptionState.Cancelled),
        Arg.Any<CancellationToken>());
}

[Fact]
public async Task Find_ReturnsNull_WhenMissing()
{
    _repo.FindAsync(Arg.Any<Guid>(), Arg.Any<CancellationToken>())
         .Returns((Subscription?)null);

    Assert.Null(await _sut.GetAsync(Guid.NewGuid(), CancellationToken.None));
}
```

The same intent in Moq is `mock.Setup(...).ReturnsAsync(...)` and
`mock.Verify(r => r.SaveAsync(...), Times.Once())`. Pick one library per
solution — mixing them is a smell.

## ASP.NET Core Integration Tests

`WebApplicationFactory<TEntryPoint>` boots your real application in-process and
hands you an `HttpClient`. Point `TEntryPoint` at your `Program` class. Override
services in the test host to swap out anything you do not want to hit for real
(external gateways, the production database).

```csharp
public sealed class SubscriptionApiTests : IClassFixture<WebApplicationFactory<Program>>
{
    private readonly HttpClient _client;

    public SubscriptionApiTests(WebApplicationFactory<Program> factory) =>
        _client = factory.WithWebHostBuilder(b => b.ConfigureServices(services =>
        {
            // Replace the real payment gateway with a controllable fake.
            services.RemoveAll<IPaymentGateway>();
            services.AddSingleton<IPaymentGateway, FakePaymentGateway>();
        })).CreateClient();

    [Fact]
    public async Task Get_Returns404_WhenSubscriptionMissing()
    {
        var response = await _client.GetAsync($"/api/subscriptions/{Guid.NewGuid()}");
        Assert.Equal(HttpStatusCode.NotFound, response.StatusCode);
    }

    [Fact]
    public async Task Post_Returns201_AndLocation_WithValidRequest()
    {
        var response = await _client.PostAsJsonAsync("/api/subscriptions",
            new SubscribeRequest(CustomerId: "c-1", PlanCode: "PRO"));

        Assert.Equal(HttpStatusCode.Created, response.StatusCode);
        Assert.NotNull(response.Headers.Location);
    }
}
```

An in-memory database provider is a common shortcut for these tests, but it does
not enforce real relational constraints. When correctness depends on database
behaviour (unique indexes, transactions, cascade rules), test against a real
engine with Testcontainers instead.

## Real-Infrastructure Tests with Testcontainers

For repository and data-access tests, run the actual database in an ephemeral
container. Implement `IAsyncLifetime` so the container starts before the tests
and is torn down after — no leaked state between runs.

```csharp
public sealed class SubscriptionRepositoryTests : IAsyncLifetime
{
    private readonly PostgreSqlContainer _db = new PostgreSqlBuilder()
        .WithImage("postgres:16-alpine")
        .Build();

    private AppDbContext _context = null!;

    public async Task InitializeAsync()
    {
        await _db.StartAsync();
        var options = new DbContextOptionsBuilder<AppDbContext>()
            .UseNpgsql(_db.GetConnectionString())
            .Options;
        _context = new AppDbContext(options);
        await _context.Database.MigrateAsync();
    }

    public async Task DisposeAsync()
    {
        await _context.DisposeAsync();
        await _db.DisposeAsync();
    }

    [Fact]
    public async Task Save_ThenFind_RoundTrips()
    {
        var repo = new EfSubscriptionRepository(_context);
        var sub = new Subscription(Guid.NewGuid(), SubscriptionState.Active, new DateOnly(2026, 3, 1));

        await repo.SaveAsync(sub, CancellationToken.None);
        var found = await repo.FindAsync(sub.Id, CancellationToken.None);

        Assert.NotNull(found);
        Assert.Equal(SubscriptionState.Active, found!.State);
    }
}
```

Testcontainers requires a working Docker (or compatible) runtime on the machine
and in CI. These tests are slower than unit tests by an order of magnitude —
keep them in a separate integration project so `dotnet test` on the unit project
stays fast.

## Test-Project Layout

Separate fast unit tests from slow integration tests so each can be run and
gated independently.

```
tests/
  MyApp.UnitTests/          # fast, no I/O, run on every save
    Services/
      SubscriptionServiceTests.cs
    Validators/
      SubscribeRequestValidatorTests.cs
  MyApp.IntegrationTests/   # HTTP + real DB, slower, run in CI
    Api/
      SubscriptionApiTests.cs
    Repositories/
      SubscriptionRepositoryTests.cs
  MyApp.TestSupport/        # shared builders and fixtures
    Builders/
      SubscriptionBuilder.cs
```

## Test Data Builders

A fluent builder keeps test setup readable and lets each test override only the
field it cares about, with sensible defaults for the rest. This localises the
blast radius when a constructor signature changes.

```csharp
public sealed class SubscriptionBuilder
{
    private Guid _id = Guid.NewGuid();
    private SubscriptionState _state = SubscriptionState.Active;
    private DateOnly _renewsOn = new(2026, 1, 15);

    public SubscriptionBuilder InState(SubscriptionState state) { _state = state; return this; }
    public SubscriptionBuilder RenewingOn(DateOnly date) { _renewsOn = date; return this; }

    public Subscription Build() => new(_id, _state, _renewsOn);
}

// Usage
var cancelled = new SubscriptionBuilder()
    .InState(SubscriptionState.Cancelled)
    .Build();
```

## Anti-Patterns to Reject

| Anti-pattern | Why it hurts | Do instead |
|---|---|---|
| Asserting on private fields / internal calls | Breaks on every refactor | Assert on returned values and observable state |
| One shared, mutated fixture across tests | Order-dependent flakes | Fresh instance per test (xUnit ctor) |
| `Thread.Sleep` to "wait" in async tests | Slow and still racy | Await the task, or poll with a bounded timeout |
| Asserting on `ToString()` output | Brittle, format-coupled | Assert on typed properties |
| Several unrelated assertions in one test | Failures hide each other | One logical assertion per test |
| Test named after the mechanism | Says nothing on failure | `Method_ExpectedOutcome_WhenCondition` |
| Dropping the `CancellationToken` | Untested cancellation paths | Thread it through and cover cancellation |
| Mocking types you own AND the DB AND the clock in one unit test | Tests the mocks, not the code | Mock at one seam; use an integration test for the rest |

## Running Tests

```bash
# Run the whole solution
dotnet test

# Run one project (e.g. keep CI's fast lane on unit tests only)
dotnet test tests/MyApp.UnitTests/

# Collect coverage
dotnet test --collect:"XPlat Code Coverage"

# Filter by name substring
dotnet test --filter "FullyQualifiedName~SubscriptionService"

# Re-run on file change during development
dotnet watch test --project tests/MyApp.UnitTests/
```

Gate CI on the unit project on every push; run the integration project (which
needs Docker) on a slower lane so a missing container runtime never blocks the
fast feedback loop.

## Changelog

- **1.0.0** (2026-07-07, PLAN-153 Wave D): initial authoring. Clean-room
  rewrite teaching the C# / .NET testing class — xUnit AAA structure, `[Theory]`
  parameterization, NSubstitute/Moq isolation, WebApplicationFactory and
  Testcontainers integration, project layout, builders, and anti-patterns.
  Original example code; added an assertion-library licensing caveat and the
  in-memory-vs-real-DB integration nuance.
Skill-Import-Attestation: reviewed-by=AE9B236FDAF0462874060C6BCFCFACF00335DC74; sha256=40f519902d0be029b52925c175f85c1cee0b390077293d424c8599f5863019d8
