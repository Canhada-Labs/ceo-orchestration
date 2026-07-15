---
name: jvm-testing
description: >
  Testing workflow for JVM services (Java 17+) on Spring Boot and Quarkus —
  JUnit 5, Mockito, and AssertJ fundamentals, the test pyramid from plain
  units through Spring Boot test slices (@WebMvcTest, @DataJpaTest) to full
  integration tests with Testcontainers against the production database
  engine, Quarkus @QuarkusTest with Dev Services, test-data builders, flake
  elimination (Awaitility over sleeps, injected Clock, isolated resources),
  and JaCoCo/CI coverage gates with a unit/integration split. Use when
  writing or fixing JVM tests, choosing a test slice, wiring Testcontainers,
  diagnosing a flaky suite, or setting coverage gates. For language and
  persistence conventions pair with java-coding-standards; for the
  application-framework shape pair with springboot-patterns.
version: 1.0.0
metadata:
  risk_class: low
  activation_triggers:
    - "writing or reviewing JUnit 5 / Mockito / AssertJ tests in a JVM service"
    - "choosing between @WebMvcTest, @DataJpaTest, and @SpringBootTest"
    - "wiring Testcontainers or Quarkus Dev Services into a test suite"
    - "diagnosing a flaky JVM test or a slow test suite"
    - "configuring JaCoCo coverage gates or the surefire/failsafe unit-vs-IT split"
paths:
  - "**/*Test.java"
  - "**/*Tests.java"
  - "**/*IT.java"
  - "**/src/test/**"
tier: domain:jvm
scope_tags:
  - java
  - junit5
  - mockito
  - spring-boot-test
  - testcontainers
  - quarkus-test
  - coverage
---

# JVM Testing

An agent-facing testing workflow for Java 17+ services. The goal is a
pyramid-shaped suite that is deterministic, fast to iterate on, and honest
about the database it runs against. Where a rule differs between frameworks
it is tagged **[SPRING]** or **[QUARKUS]**; untagged rules are shared.

## When to Activate

- Writing new tests or repairing existing ones in a Spring Boot or Quarkus
  service
- Deciding which layer a behavior should be proven at (unit, slice,
  integration)
- Wiring Testcontainers, Dev Services, or a CI test gate
- Chasing a flaky or slow suite
- Setting or reviewing coverage thresholds

Do not reach for it for language-level or persistence conventions
(`java-coding-standards`) or application-architecture shape
(`springboot-patterns`) — this skill is about proving behavior.

## The pyramid: pick the narrowest test that proves the behavior

| Layer | Tool | Boots | Proves |
|---|---|---|---|
| Unit | JUnit 5 + Mockito | nothing | service/domain logic |
| Slice **[SPRING]** | `@WebMvcTest` / `@DataJpaTest` | one layer | HTTP shape / query behavior |
| Integration | `@SpringBootTest` + Testcontainers | full context | wiring, transactions, real SQL |
| Integration **[QUARKUS]** | `@QuarkusTest` + Dev Services | full context | same, with managed containers |

An all-`@SpringBootTest` suite is a build-time bug: every test pays the
full-context boot cost to prove things a unit or slice test proves in
milliseconds. Reserve the full context for behavior that only exists when
everything is wired together.

## Unit tests: JUnit 5 + Mockito + AssertJ

Plain units need no framework context. Constructor injection (per
`java-coding-standards`) makes this trivial — pass mocks to the
constructor.

```java
@ExtendWith(MockitoExtension.class)
class CatalogServiceTest {
  @Mock ProductRepository repo;
  @InjectMocks CatalogService service;

  @Test
  void createRejectsDuplicateSlug() {
    when(repo.findBySlug("mug")).thenReturn(Optional.of(existingProduct()));

    assertThatThrownBy(() -> service.create(requestWithSlug("mug")))
        .isInstanceOf(DuplicateSlugException.class)
        .hasMessageContaining("mug");

    verify(repo, never()).save(any());
  }
}
```

Discipline:

- AssertJ (`assertThat`, `assertThatThrownBy`) over bare JUnit assertions —
  fluent failure messages.
- Mock interactions only when the interaction *is* the behavior under test;
  construct plain value objects (records, DTOs) directly — never mock them.
- No partial mocks / `spy` on the class under test — that tests a
  Frankenstein object, not your code.
- Use `ArgumentCaptor` to assert on what was passed, not brittle `eq()`
  chains.
- Parameterize repetitive cases:

```java
@ParameterizedTest
@CsvSource({"'', false", "'a', false", "'valid-slug', true"})
void slugValidation(String slug, boolean expected) {
  assertThat(SlugValidator.isValid(slug)).isEqualTo(expected);
}
```

## Slice tests **[SPRING]**

### Controller slice — `@WebMvcTest`

Boots the web layer only. Prove the HTTP contract: status codes,
validation failures, and the error shape — not just the happy path.

```java
@WebMvcTest(ProductController.class)
class ProductControllerTest {
  @Autowired MockMvc mvc;
  @MockitoBean CatalogService catalogService;  // @MockBean pre-Boot 3.4

  @Test
  void createReturns201WithBody() throws Exception {
    when(catalogService.create(any())).thenReturn(product());

    mvc.perform(post("/api/products")
            .contentType(MediaType.APPLICATION_JSON)
            .content("""
                {"name":"Mug","description":"A mug","price":9.90,"categories":["kitchen"]}
                """))
        .andExpect(status().isCreated())
        .andExpect(jsonPath("$.name").value("Mug"));
  }

  @Test
  void blankNameReturns400() throws Exception {
    mvc.perform(post("/api/products")
            .contentType(MediaType.APPLICATION_JSON)
            .content("{\"name\":\"\"}"))
        .andExpect(status().isBadRequest());
  }
}
```

Note: Spring Boot 3.4 deprecated `@MockBean` in favor of `@MockitoBean` —
use whichever your Boot version ships, consistently.

### Repository slice — `@DataJpaTest` + Testcontainers

`@DataJpaTest` defaults to swapping in an embedded database. **Disable the
swap and run the production engine via Testcontainers** — H2 accepts SQL
your real engine rejects and hides dialect, constraint, and locking
differences.

```java
@DataJpaTest
@AutoConfigureTestDatabase(replace = AutoConfigureTestDatabase.Replace.NONE)
@Testcontainers
class ProductRepositoryTest {
  @Container @ServiceConnection
  static PostgreSQLContainer<?> postgres = new PostgreSQLContainer<>("postgres:16-alpine");

  @Autowired ProductRepository repo;

  @Test
  void findWithVariantsFetchesInOneQuery() {
    // assert on emitted SQL (hibernate SQL logging) to catch N+1 regressions
    Optional<ProductEntity> found = repo.findWithVariants(seededProductId);
    assertThat(found).isPresent();
    assertThat(found.get().getVariants()).hasSize(3);
  }
}
```

`@ServiceConnection` (Boot 3.1+) replaces the older
`@DynamicPropertySource` datasource wiring. Declare the container
`static` so it is shared across the class instead of restarted per test;
share one container across classes with a singleton-container base class
when suite time matters.

## Integration tests

Full-context tests prove wiring: security filters, transaction rollback
semantics, serialization config, listeners.

```java
@SpringBootTest(webEnvironment = SpringBootTest.WebEnvironment.RANDOM_PORT)
@Testcontainers
class OrderFlowIT {
  @Container @ServiceConnection
  static PostgreSQLContainer<?> postgres = new PostgreSQLContainer<>("postgres:16-alpine");

  @Autowired TestRestTemplate rest;

  @Test
  void duplicateSubmissionIsIdempotent() {
    var request = orderRequest("idem-key-1");
    var first = rest.postForEntity("/api/orders", request, OrderResponse.class);
    var second = rest.postForEntity("/api/orders", request, OrderResponse.class);

    assertThat(first.getStatusCode()).isEqualTo(HttpStatus.CREATED);
    assertThat(second.getStatusCode()).isEqualTo(HttpStatus.OK);
    assertThat(second.getBody().id()).isEqualTo(first.getBody().id());
  }
}
```

**[QUARKUS]** `@QuarkusTest` boots the application once per test profile;
Dev Services starts containers (Postgres, Kafka, Redis) automatically when
no explicit config is present. Replace CDI beans with `@InjectMock`.

```java
@QuarkusTest
class ProductResourceTest {
  @InjectMock CatalogService catalogService;

  @Test
  void findBySlugReturns404WhenAbsent() {
    when(catalogService.findBySlug("nope")).thenThrow(new ProductNotFoundException("nope"));
    given().when().get("/products/nope").then().statusCode(404);
  }
}
```

## Test-data builders

Centralize object construction so a schema change touches one builder, not
two hundred tests. Records + a small builder with sensible defaults:

```java
public final class ProductMother {
  public static ProductEntity.Builder product() {
    return ProductEntity.builder()
        .name("Mug")
        .slug("mug-" + UUID.randomUUID())   // unique per test — no collisions
        .status(ProductStatus.ACTIVE);
  }
}
// usage: repo.save(ProductMother.product().status(DISCONTINUED).build());
```

Randomize only identity fields (slugs, keys) for isolation; keep behavioral
fields deterministic so failures reproduce.

## Keeping tests non-flaky

Flakiness is a correctness defect in the test (or a real race in the code),
never bad luck. The JVM-specific causes and fixes:

- **`Thread.sleep` for synchronization** → wait on the condition with
  Awaitility, a `CountDownLatch`, or a `CompletableFuture` join:

```java
await().atMost(Duration.ofSeconds(5))
    .untilAsserted(() -> assertThat(outbox.pending()).isEmpty());
```

- **Wall-clock reads** → inject `java.time.Clock` into production code and
  pass `Clock.fixed(...)` in tests; never assert on `Instant.now()`.
- **Shared containers restarted per test** → `static` containers /
  singleton-container pattern; unique database or schema per test class if
  parallelizing.
- **Port collisions** → `RANDOM_PORT`, never fixed ports.
- **Inter-test state via the database** → each test seeds what it needs and
  cleans up (or rolls back); never depend on execution order
  (`@TestMethodOrder` on stateful tests is a smell, not a fix).
- **Retry-masked flakes** → raising CI retry counts hides the defect;
  quarantine with a linked root-cause ticket instead, then fix and soak
  (50 local runs) before unquarantining.

## Coverage and CI gates

- Split fast from slow: surefire runs `*Test` on every build, failsafe runs
  `*IT` (Testcontainers) in the integration phase — or use JUnit 5 `@Tag`
  with separate Gradle tasks.
- JaCoCo for coverage; gate on the ratchet principle (never below the
  current baseline) rather than a vanity absolute number:

```xml
<rule>
  <element>BUNDLE</element>
  <limits>
    <limit>
      <counter>LINE</counter><value>COVEREDRATIO</value><minimum>0.80</minimum>
    </limit>
  </limits>
</rule>
```

- Coverage measures execution, not verification — a test with no assertions
  inflates the number. Review assertions, not percentages.
- Lowering a threshold, skipping the IT phase, or disabling Testcontainers
  in CI is a test-gate weakening: it requires the Test & Release Engineer's
  sign-off (see the jvm squad pitfalls JVM-012..016).

## Best Practices

**Do**

- Prove each behavior at the narrowest layer that can prove it.
- Run data-layer tests against the production engine (Testcontainers).
- Cover the failing path (validation errors, not-found, conflict) at every
  layer, not just the happy path.
- Keep tests independent of execution order and parallel-safe.
- Name tests after the behavior: `createRejectsDuplicateSlug`, not `test1`.

**Don't**

- Boot `@SpringBootTest` to test an `if` statement.
- Mock value objects or the class under test.
- Sleep where a condition can be awaited.
- Assert on `now()`, fixed ports, or shared mutable fixtures.
- Delete or blanket-retry a flaky test without a root-cause ticket.

## Changelog

- **1.0.0** — Initial skill. JVM test pyramid (JUnit 5/Mockito/AssertJ
  units, Spring Boot slices, Testcontainers integration, Quarkus
  @QuarkusTest + Dev Services), test-data builders, flake elimination
  playbook, and JaCoCo/CI gate discipline with the unit-vs-IT split.
