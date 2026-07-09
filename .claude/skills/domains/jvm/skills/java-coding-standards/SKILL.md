---
name: java-coding-standards
description: >
  Coding standards for modern Java (17+) services on the two dominant JVM
  backend stacks — Spring Boot and Quarkus. Covers naming, immutability,
  Optional discipline, streams, exceptions, generics, dependency injection,
  reactive pipelines, configuration, logging, project layout, and a folded
  Persistence (JPA/Hibernate) section for entity design, N+1 prevention,
  transactions, pagination, indexing, and connection pooling. Use when
  writing or reviewing Java in a Spring Boot or Quarkus codebase, or when
  designing the data-access layer.
version: 1.0.0
metadata:
  risk_class: low
  activation_triggers:
    - "editing *.java sources in a Spring Boot or Quarkus service"
    - "build file (pom.xml / build.gradle) declares spring-boot or quarkus"
    - "reviewing Java naming, immutability, Optional, streams, generics, or exception handling"
    - "authoring records, sealed types, or pattern matching (Java 17+)"
    - "designing JPA/Hibernate entities, relationships, repositories, or queries"
    - "tuning transactions, pagination, indexing, or HikariCP pooling"
inspired_by:
  - source: affaan-m/ecc/skills/java-coding-standards@81af40761939056ab3dc54732fd4f562a27309d0
    license: MIT
    relationship: structural_inspiration
    authored_by: ceo-orchestration framework
    authored_at: 2026-07-07
  - source: affaan-m/ecc/skills/jpa-patterns@81af40761939056ab3dc54732fd4f562a27309d0
    license: MIT
    relationship: structural_inspiration
    authored_by: ceo-orchestration framework
    authored_at: 2026-07-07
tier: domain:jvm
scope_tags:
  - java
  - spring-boot
  - quarkus
  - jpa
  - hibernate
  - coding-standards
source: affaan-m/ecc@81af4076 skills/java-coding-standards/
license: MIT
---

# Java Coding Standards

Conventions for readable, maintainable Java 17+ across the two mainstream JVM
service stacks. Where a rule differs between frameworks it is tagged
**[SPRING]** (Spring Boot) or **[QUARKUS]** (Quarkus/CDI); untagged rules are
shared. The goal is intentional, typed, observable code — optimise for
maintainability first, and micro-optimise only when a profiler says so.

## When to Activate

- Writing or reviewing Java in a Spring Boot or Quarkus project
- Enforcing naming, immutability, or exception-handling conventions
- Working with records, sealed classes, or pattern matching (Java 17+)
- Reviewing Optional, stream, or generics usage
- Laying out packages / project structure
- Designing the persistence layer — entities, relationships, queries, transactions (see **Persistence (JPA)** below)
- **[QUARKUS]** working with CDI scopes, Panache entities, or reactive (`Uni`/`Multi`) pipelines

## Detect the framework first

Read the build file before applying any tagged rule:

- Declares `quarkus` → apply **[QUARKUS]** conventions
- Declares `spring-boot` → apply **[SPRING]** conventions
- Neither → apply only the shared rules

## Guiding principles

- Clarity beats cleverness. If a reviewer has to pause, simplify.
- Immutable by default; keep shared mutable state to a minimum.
- Fail fast with a meaningful, domain-specific exception.
- One naming and package convention per codebase — no drift.
- **[QUARKUS]** prefer build-time work over runtime; avoid runtime reflection.

## Naming

```java
// Types (classes / records): PascalCase
public class CatalogService {}
public record Money(BigDecimal amount, Currency currency) {}

// Methods and fields: camelCase
private final ProductRepository productRepository;
public Product findBySlug(String slug) { ... }

// Constants: UPPER_SNAKE_CASE
private static final int MAX_PAGE_SIZE = 100;

// [SPRING] HTTP entry points are *Controller
public class ProductController {}

// [QUARKUS] JAX-RS entry points are *Resource (not *Controller)
public class ProductResource {}
```

## Immutability

Favour records and `final` fields; expose accessors, not setters.

```java
// Shared: a DTO is a record
public record ProductDto(Long id, String name, ProductStatus status) {}

// Shared: a domain object with no setters
public final class Product {
  private final Long id;
  private final String name;
  // constructor + getters only
}

// [QUARKUS] Panache active-record entities use PUBLIC fields on purpose —
// Panache generates accessors at build time, so public fields are idiomatic here
@Entity
public class Product extends PanacheEntity {
  public String name;
  public ProductStatus status;
}
```

## Optional discipline

Return `Optional` from `find*` methods; compose with `map`/`flatMap`/`orElseThrow`
instead of calling `get()`.

```java
// [SPRING]
Optional<Product> product = productRepository.findBySlug(slug);

// [QUARKUS] Panache
Optional<Product> product = Product.find("slug", slug).firstResultOptional();

// Compose — never .get()
return product
    .map(ProductResponse::from)
    .orElseThrow(() -> new ProductNotFoundException(slug));
```

Do not use `Optional` for fields or method parameters — only as a return type
that signals "may be absent".

## Streams

Use streams for transformation, keep the pipeline short and linear, and reach
for `.toList()` (Java 16+). If a stream grows nested or hard to read, a plain
loop is the better choice.

```java
List<String> names = products.stream()
    .map(Product::name)
    .filter(Objects::nonNull)
    .toList();
```

## Dependency injection

Constructor injection everywhere — it makes dependencies explicit, supports
`final` fields, and keeps objects testable without a container.

```java
// [SPRING] constructor injection (never @Autowired on a field)
@Service
public class CatalogService {
  private final ProductRepository productRepository;

  public CatalogService(ProductRepository productRepository) {
    this.productRepository = productRepository;
  }
}

// [QUARKUS] constructor injection
@ApplicationScoped
public class CatalogService {
  private final ProductRepository productRepository;

  @Inject
  public CatalogService(ProductRepository productRepository) {
    this.productRepository = productRepository;
  }
}
```

Anti-patterns:

- **[SPRING]** `@Autowired` on a private field — untestable without reflection; use the constructor.
- **[QUARKUS]** `@Singleton` where interception or lazy init is needed — it is non-proxyable; use `@ApplicationScoped`. (Package-private `@Inject` field injection is acceptable in Quarkus and sidesteps proxy edge cases.)

## Reactive pipelines **[QUARKUS]**

Return `Uni`/`Multi` from reactive endpoints and compose non-blocking stages.
The two cardinal sins are blocking inside the pipeline and subscribing twice to
a shared `Uni`.

```java
// PASS: reactive endpoint
@GET
@Path("/{slug}")
public Uni<Product> findBySlug(@PathParam("slug") String slug) {
  return Product.find("slug", slug)
      .<Product>firstResult()
      .onItem().ifNull().failWith(() -> new ProductNotFoundException(slug));
}

// PASS: composed non-blocking stages
public Uni<Shipment> fulfill(FulfillmentRequest req) {
  return reserveInventory(req)
      .chain(reserved -> createShipment(reserved))
      .chain(shipment -> notifyWarehouse(shipment));
}

// FAIL: blocking call inside a Uni — stalls the event loop
public Uni<Product> find(String slug) {
  Product p = Product.find("slug", slug).firstResult(); // blocking
  return Uni.createFrom().item(p);
}

// FAIL: subscribing twice to a shared Uni — re-runs the work; use .memoize()
```

## Exceptions

- Use unchecked exceptions for domain errors; wrap technical exceptions with context.
- Create specific types (`ProductNotFoundException`) — not bare `RuntimeException`.
- Avoid broad `catch (Exception ex)` unless you rethrow or log at a single central point.

Handle errors centrally rather than per endpoint:

```java
// [SPRING]
@RestControllerAdvice
public class GlobalExceptionHandler {
  @ExceptionHandler(ProductNotFoundException.class)
  public ResponseEntity<ErrorResponse> handle(ProductNotFoundException ex) {
    return ResponseEntity.status(404).body(ErrorResponse.from(ex));
  }
}

// [QUARKUS] classic: ExceptionMapper
@Provider
public class ProductNotFoundMapper implements ExceptionMapper<ProductNotFoundException> {
  @Override
  public Response toResponse(ProductNotFoundException ex) {
    return Response.status(404).entity(ErrorResponse.from(ex)).build();
  }
}

// [QUARKUS] RESTEasy Reactive: @ServerExceptionMapper
@ServerExceptionMapper
public RestResponse<ErrorResponse> handle(ProductNotFoundException ex) {
  return RestResponse.status(Status.NOT_FOUND, ErrorResponse.from(ex));
}
```

## Generics and type safety

No raw types; declare type parameters, and prefer bounded generics for reusable
utilities.

```java
public <T extends Identifiable> Map<Long, T> indexById(Collection<T> items) { ... }
```

## Null handling

- Prefer `@NonNull`; reserve `@Nullable` for the unavoidable, and document why.
- Validate inputs with Bean Validation (`@NotNull`, `@NotBlank`, `@Size`).
- **[QUARKUS]** apply `@Valid` on `@BeanParam`, `@RestForm`, and request-body params.

## Configuration

```java
// [SPRING] type-safe binding
@ConfigurationProperties(prefix = "catalog")
public record CatalogProperties(int maxPageSize, Duration cacheTtl) {}

// [QUARKUS] build-time-validated mapping
@ConfigMapping(prefix = "catalog")
public interface CatalogConfig {
  int maxPageSize();
  Duration cacheTtl();
}

// [QUARKUS] a single value
@ConfigProperty(name = "catalog.max-page-size", defaultValue = "100")
int maxPageSize;
```

## Logging

Use structured, key=value message templates — never string concatenation — and
always pass the throwable as the last argument.

```java
// [SPRING] SLF4J
private static final Logger log = LoggerFactory.getLogger(CatalogService.class);
log.info("fetch_product slug={}", slug);
log.error("fetch_product_failed slug={}", slug, ex);

// [QUARKUS] JBoss Logging (default; zero-cost when disabled)
private static final Logger log = Logger.getLogger(CatalogService.class);
log.infof("fetch_product slug=%s", slug);
log.errorf(ex, "fetch_product_failed slug=%s", slug);
```

## Project structure

```
// [SPRING]
src/main/java/com/example/app/
  config/  controller/  service/  repository/  domain/  dto/  util/
src/main/resources/application.yml
src/test/java/...            # mirrors main

// [QUARKUS]
src/main/java/com/example/app/
  config/      # @ConfigMapping, @ConfigProperty, producers
  resource/    # JAX-RS resources (not "controller")
  service/  repository/  domain/  dto/  mapper/
src/main/resources/
  application.properties     # YAML supported via quarkus-config-yaml
src/test/java/...            # mirrors main
```

## Formatting and member order

- One public top-level type per file; pick 2- or 4-space indent and hold it.
- Member order: constants, fields, constructors, then public → protected → private methods.
- Keep methods short and single-purpose; extract helpers over deep nesting.

## Code smells to avoid

- Long parameter lists → pass a DTO or use a builder
- Deep nesting → early returns
- Magic numbers → named constants
- Static mutable state → inject a dependency instead
- Silent `catch` blocks → log and act, or rethrow
- **[QUARKUS]** `@Singleton` where `@ApplicationScoped` is meant — breaks proxying/interception
- **[QUARKUS]** mixing the reactive and classic RESTEasy stacks — pick one
- **[QUARKUS]** Panache active-record *and* the repository pattern in one bounded context — pick one

## Persistence (JPA)

Applies primarily to **[SPRING]** + Spring Data JPA / Hibernate; the entity-design
and query-shape rules carry over to **[QUARKUS]** Panache as well. Keep entities
lean, queries intentional, and transactions short.

### Entity design + auditing

```java
@Entity
@Table(name = "products", indexes = {
    @Index(name = "idx_products_slug", columnList = "slug", unique = true)
})
@EntityListeners(AuditingEntityListener.class)
public class ProductEntity {
  @Id @GeneratedValue(strategy = GenerationType.IDENTITY)
  private Long id;

  @Column(nullable = false, length = 200)
  private String name;

  @Column(nullable = false, unique = true, length = 120)
  private String slug;

  @Enumerated(EnumType.STRING)
  private ProductStatus status = ProductStatus.ACTIVE;

  @CreatedDate private Instant createdAt;
  @LastModifiedDate private Instant updatedAt;
}
```

```java
// enable auditing once, at config
@Configuration
@EnableJpaAuditing
class JpaConfig {}
```

Always map enums with `EnumType.STRING` — `ORDINAL` silently corrupts data when
someone reorders the enum.

### Relationships and N+1 prevention

The N+1 query is the defining JPA performance bug. Default every association to
`LAZY`, never put `EAGER` on a collection, and pull what a read path needs with
an explicit `JOIN FETCH` or a DTO projection.

```java
@OneToMany(mappedBy = "product", cascade = CascadeType.ALL, orphanRemoval = true)
private List<VariantEntity> variants = new ArrayList<>();
```

```java
@Query("select p from ProductEntity p left join fetch p.variants where p.id = :id")
Optional<ProductEntity> findWithVariants(@Param("id") Long id);
```

### Repositories and projections

```java
public interface ProductRepository extends JpaRepository<ProductEntity, Long> {
  Optional<ProductEntity> findBySlug(String slug);

  @Query("select p from ProductEntity p where p.status = :status")
  Page<ProductEntity> findByStatus(@Param("status") ProductStatus status, Pageable pageable);
}

// interface projection — selects only the columns you name
public interface ProductSummary {
  Long getId();
  String getName();
  ProductStatus getStatus();
}
Page<ProductSummary> findAllBy(Pageable pageable);
```

### Transactions

- Annotate service methods (not repositories) with `@Transactional`.
- Use `@Transactional(readOnly = true)` on read paths — it lets Hibernate skip dirty-checking.
- Keep transactions short; pick propagation deliberately; never do I/O or remote calls inside one.

```java
@Transactional
public Product updateStatus(Long id, ProductStatus status) {
  ProductEntity entity = repo.findById(id)
      .orElseThrow(() -> new ProductNotFoundException(id));
  entity.setStatus(status);   // dirty-checking flushes on commit
  return Product.from(entity);
}
```

### Pagination

```java
PageRequest page = PageRequest.of(pageNumber, pageSize, Sort.by("createdAt").descending());
Page<ProductEntity> results = repo.findByStatus(ProductStatus.ACTIVE, page);
```

For deep pagination, prefer keyset ("seek") pagination — add `id > :lastId` to
the JPQL with matching ordering — over large `OFFSET` values, which the database
must still scan and discard.

### Indexing and write batching

- Index the columns you actually filter and join on (`status`, `slug`, foreign keys).
- Use composite indexes that match the query's leading columns (`status, created_at`).
- Never `select *`; project only the columns a path needs.
- Batch inserts/updates with `saveAll` plus `hibernate.jdbc.batch_size`.

### Connection pooling (HikariCP)

```
spring.datasource.hikari.maximum-pool-size=20
spring.datasource.hikari.minimum-idle=5
spring.datasource.hikari.connection-timeout=30000
spring.datasource.hikari.validation-timeout=5000
```

Size the pool to the workload, not to a round number — an oversized pool starves
the database of connections and hides slow queries behind queueing.

### Second-level cache

The first-level cache lives on the `EntityManager`; do not hold entities across
transactions expecting them to stay attached. Reach for a second-level cache only
for genuinely read-heavy, rarely-changing entities, and only after you have
validated an eviction strategy.

### Migrations

Own your schema with Flyway or Liquibase; never let Hibernate `ddl-auto` touch a
production database. Keep migrations additive and idempotent, and plan any column
drop as a separate, reversible step.

### Testing data access

Use `@DataJpaTest` against a real engine via Testcontainers so tests mirror
production dialect and constraints. Verify query efficiency (and catch N+1
regressions) by asserting on emitted SQL:

```
logging.level.org.hibernate.SQL=DEBUG
logging.level.org.hibernate.orm.jdbc.bind=TRACE
```

## Testing expectations

**Shared** — JUnit 5 + AssertJ for fluent assertions, Mockito for mocking (avoid
partial mocks), deterministic tests with no `sleep`.

```java
// [SPRING] slice tests
@WebMvcTest(ProductController.class)   // controller slice
@DataJpaTest                           // repository slice
@SpringBootTest                        // full integration only
// use @MockBean to replace a bean in the Spring context

// [QUARKUS]
@ExtendWith(MockitoExtension.class)    // plain unit test — no @QuarkusTest
@QuarkusTest                           // CDI integration test only
// use @InjectMock to replace a CDI bean; lean on Dev Services for db/kafka/redis
```

## Changelog

- **1.0.0** — Initial skill. JVM coding standards spanning Spring Boot and
  Quarkus (naming, immutability, Optional, streams, DI, reactive, exceptions,
  config, logging, layout), with the JPA/Hibernate persistence guidance folded
  in as the **Persistence (JPA)** section.
Skill-Import-Attestation: reviewed-by=AE9B236FDAF0462874060C6BCFCFACF00335DC74; sha256=9d5a9f4cf62f41f2f8d1e247c475c70b3b11e964f69fafa31d6d5e63484fcbb2
