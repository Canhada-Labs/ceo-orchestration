---
name: springboot-patterns
description: >
  Spring Boot architecture and API patterns for production-grade services —
  layered controller/service/repository design, REST endpoint shape, Spring
  Data access, DTO validation, centralised exception handling, caching, async
  processing, scheduled jobs, request filters, pagination, resilient external
  calls, rate limiting, and observability. Use for Java Spring Boot backend
  work. For language-level conventions and the JPA/Hibernate data layer, pair
  with the java-coding-standards skill.
version: 1.0.0
metadata:
  risk_class: medium
  activation_triggers:
    - "building REST APIs with Spring MVC or WebFlux"
    - "structuring controller → service → repository layers in Spring Boot"
    - "configuring Spring caching, async, scheduling, or profiles"
    - "adding request validation, centralised exception handling, or pagination"
    - "implementing rate limiting, retries, or request-logging filters"
    - "wiring Spring observability (Micrometer, structured logging, tracing)"
inspired_by:
  - source: affaan-m/ecc/skills/springboot-patterns@81af40761939056ab3dc54732fd4f562a27309d0
    license: MIT
    relationship: structural_inspiration
    authored_by: ceo-orchestration framework
    authored_at: 2026-07-07
tier: domain:jvm
scope_tags:
  - spring-boot
  - rest-api
  - spring-mvc
  - caching
  - rate-limiting
  - observability
source: affaan-m/ecc@81af4076 skills/springboot-patterns/
license: MIT
---

# Spring Boot Patterns

Architecture and API patterns for scalable, production Spring Boot services. The
through-line: keep controllers thin, services focused, repositories simple, and
errors handled in one place. Language-level rules and the JPA/Hibernate data
layer live in the `java-coding-standards` skill — this skill is about the
application-framework shape.

## When to Activate

- Building REST APIs with Spring MVC or WebFlux
- Structuring the controller → service → repository layering
- Configuring Spring Data access, caching, or async processing
- Adding validation, centralised exception handling, or pagination
- Setting up per-environment profiles (dev / staging / prod)
- Implementing event-driven flows with Spring Events or a broker (Kafka, SQS, RabbitMQ)

## Controller: thin and declarative

Controllers translate HTTP to a service call and back — no business logic. Use
constructor injection and return a `ResponseEntity` with an explicit status.

```java
@RestController
@RequestMapping("/api/products")
@Validated
class ProductController {
  private final CatalogService catalogService;

  ProductController(CatalogService catalogService) {
    this.catalogService = catalogService;
  }

  @GetMapping
  ResponseEntity<Page<ProductResponse>> list(
      @RequestParam(defaultValue = "0") int page,
      @RequestParam(defaultValue = "20") int size) {
    Page<Product> products = catalogService.list(PageRequest.of(page, size));
    return ResponseEntity.ok(products.map(ProductResponse::from));
  }

  @PostMapping
  ResponseEntity<ProductResponse> create(@Valid @RequestBody CreateProductRequest request) {
    Product product = catalogService.create(request);
    return ResponseEntity.status(HttpStatus.CREATED).body(ProductResponse.from(product));
  }
}
```

## Repository: Spring Data, kept simple

Let Spring Data derive queries from method names; drop to `@Query` only when the
derivation is ambiguous or you need a fetch join.

```java
public interface ProductRepository extends JpaRepository<ProductEntity, Long> {
  @Query("select p from ProductEntity p where p.status = :status order by p.name asc")
  List<ProductEntity> findActive(@Param("status") ProductStatus status, Pageable pageable);
}
```

## Service: the transaction boundary

Business logic and the `@Transactional` boundary live here — never in the
controller or repository.

```java
@Service
public class CatalogService {
  private final ProductRepository repo;

  public CatalogService(ProductRepository repo) {
    this.repo = repo;
  }

  @Transactional
  public Product create(CreateProductRequest request) {
    ProductEntity saved = repo.save(ProductEntity.from(request));
    return Product.from(saved);
  }
}
```

## DTOs and validation

Requests and responses are records at the edge — never expose entities directly.
Put Bean Validation constraints on the request record; they fire on `@Valid`.

```java
public record CreateProductRequest(
    @NotBlank @Size(max = 200) String name,
    @NotBlank @Size(max = 2000) String description,
    @NotNull @Positive BigDecimal price,
    @NotEmpty List<@NotBlank String> categories) {}

public record ProductResponse(Long id, String name, ProductStatus status) {
  static ProductResponse from(Product product) {
    return new ProductResponse(product.id(), product.name(), product.status());
  }
}
```

## Centralised exception handling

One `@RestControllerAdvice` maps exceptions to responses for the whole app.
Handle validation and authorization explicitly; give everything else a generic
500 with the stack trace logged (never leaked to the client). On Spring Boot 3+,
turn on RFC 7807 problem details with `spring.mvc.problemdetails.enabled=true`.

```java
@RestControllerAdvice
class GlobalExceptionHandler {
  @ExceptionHandler(MethodArgumentNotValidException.class)
  ResponseEntity<ApiError> handleValidation(MethodArgumentNotValidException ex) {
    String message = ex.getBindingResult().getFieldErrors().stream()
        .map(e -> e.getField() + ": " + e.getDefaultMessage())
        .collect(Collectors.joining(", "));
    return ResponseEntity.badRequest().body(ApiError.validation(message));
  }

  @ExceptionHandler(AccessDeniedException.class)
  ResponseEntity<ApiError> handleAccessDenied() {
    return ResponseEntity.status(HttpStatus.FORBIDDEN).body(ApiError.of("Forbidden"));
  }

  @ExceptionHandler(Exception.class)
  ResponseEntity<ApiError> handleGeneric(Exception ex) {
    // log ex with its stack trace here; return a generic message to the caller
    return ResponseEntity.status(HttpStatus.INTERNAL_SERVER_ERROR)
        .body(ApiError.of("Internal server error"));
  }
}
```

## Caching

Requires `@EnableCaching` on a config class. Cache on read, evict on write, and
key explicitly.

```java
@Service
public class ProductCacheService {
  private final ProductRepository repo;

  public ProductCacheService(ProductRepository repo) {
    this.repo = repo;
  }

  @Cacheable(value = "product", key = "#id")
  public Product getById(Long id) {
    return repo.findById(id)
        .map(Product::from)
        .orElseThrow(() -> new ProductNotFoundException(id));
  }

  @CacheEvict(value = "product", key = "#id")
  public void evict(Long id) {}
}
```

## Async processing

Requires `@EnableAsync` on a config class. Return `CompletableFuture` from
`@Async` methods so callers can compose or await.

```java
@Service
public class NotificationService {
  @Async
  public CompletableFuture<Void> sendAsync(Notification notification) {
    // dispatch email / push
    return CompletableFuture.completedFuture(null);
  }
}
```

## Request logging filter

A `OncePerRequestFilter` is the right seam for cross-cutting request concerns —
timing, correlation IDs, access logs.

```java
@Component
public class RequestLoggingFilter extends OncePerRequestFilter {
  private static final Logger log = LoggerFactory.getLogger(RequestLoggingFilter.class);

  @Override
  protected void doFilterInternal(HttpServletRequest request, HttpServletResponse response,
      FilterChain chain) throws ServletException, IOException {
    long start = System.currentTimeMillis();
    try {
      chain.doFilter(request, response);
    } finally {
      log.info("req method={} uri={} status={} durationMs={}",
          request.getMethod(), request.getRequestURI(), response.getStatus(),
          System.currentTimeMillis() - start);
    }
  }
}
```

## Pagination and sorting

Accept `page`/`size` params, build a `PageRequest` with a `Sort`, and return a
`Page` so the response carries total counts and paging metadata.

```java
PageRequest page = PageRequest.of(pageNumber, pageSize, Sort.by("createdAt").descending());
Page<Product> results = catalogService.list(page);
```

## Resilient external calls

Wrap flaky outbound calls in bounded retries with exponential backoff, and always
restore the interrupt flag if the backoff sleep is interrupted.

```java
public <T> T withRetry(Supplier<T> call, int maxRetries) {
  int attempts = 0;
  while (true) {
    try {
      return call.get();
    } catch (RuntimeException ex) {
      if (++attempts >= maxRetries) {
        throw ex;
      }
      try {
        Thread.sleep((long) Math.pow(2, attempts) * 100L);
      } catch (InterruptedException ie) {
        Thread.currentThread().interrupt();   // restore the flag, then bail
        throw ex;
      }
    }
  }
}
```

For anything beyond a simple loop, prefer a library (Resilience4j) that gives you
circuit breakers, bulkheads, and timeouts as well.

## Rate limiting — and the client-IP trap

A per-client rate limiter is only as trustworthy as the client identifier it keys
on. **The `X-Forwarded-For` header is attacker-controlled.** A client can send any
value, so keying a limiter on a raw `X-Forwarded-For` read lets an attacker forge
a fresh identity per request and defeat the limit entirely.

Trust a forwarded client IP **only** when all of these hold:

1. The app sits behind a reverse proxy you control (nginx, an ALB, etc.).
2. The proxy **overwrites** `X-Forwarded-For` rather than appending to a client-supplied value.
3. You have configured Spring to consume forwarded headers — `server.forward-headers-strategy=NATIVE` (cloud platforms) or `FRAMEWORK` (Spring Boot then registers the `ForwardedHeaderFilter` for you).
4. Trusted-proxy ranges are configured for your container (`server.tomcat.remoteip.trusted-proxies` or equivalent).

With that in place, `request.getRemoteAddr()` returns the real client IP. Without
it, `getRemoteAddr()` returns the immediate connection IP — which is the only value
you can trust — so key the limiter on that and **never** parse `X-Forwarded-For`
yourself.

```java
@Component
public class RateLimitFilter extends OncePerRequestFilter {
  // Illustrative only: one bucket per unique IP grows without bound —
  // in production use an evicting cache (e.g. Caffeine with expireAfterAccess).
  private final Map<String, Bucket> buckets = new ConcurrentHashMap<>();

  @Override
  protected void doFilterInternal(HttpServletRequest request, HttpServletResponse response,
      FilterChain chain) throws ServletException, IOException {
    // getRemoteAddr() yields the true client IP when ForwardedHeaderFilter is
    // configured, or the direct connection IP otherwise. Do NOT read
    // X-Forwarded-For directly — it is trivially spoofable without trusted-proxy
    // handling (see the four conditions above).
    String clientIp = request.getRemoteAddr();

    Bucket bucket = buckets.computeIfAbsent(clientIp,
        k -> Bucket.builder()
            .addLimit(Bandwidth.classic(100, Refill.greedy(100, Duration.ofMinutes(1))))
            .build());

    if (bucket.tryConsume(1)) {
      chain.doFilter(request, response);
    } else {
      response.setStatus(HttpStatus.TOO_MANY_REQUESTS.value());
    }
  }
}
```

## Background jobs

Use `@Scheduled` for periodic work, or consume from a queue (Kafka, SQS,
RabbitMQ) for event-driven work. Keep handlers idempotent — they will be retried
— and observable.

## Observability

- **Logs**: structured JSON (Logback encoder), key=value fields, no PII.
- **Metrics**: Micrometer exporting to Prometheus or OTLP.
- **Traces**: Micrometer Tracing over an OpenTelemetry or Brave backend.

## Production defaults

- Constructor injection only; no field injection.
- `spring.mvc.problemdetails.enabled=true` for RFC 7807 errors (Spring Boot 3+).
- Size the HikariCP pool for the workload and set explicit timeouts.
- `@Transactional(readOnly = true)` on query paths.
- Enforce null-safety with `@NonNull` and `Optional` return types where it clarifies intent.

## Changelog

- **1.0.0** — Initial skill. Spring Boot layered architecture, REST/DTO/
  validation shape, centralised exception handling, caching, async, filters,
  pagination, resilient calls, rate limiting with the untrusted-`X-Forwarded-For`
  security note, background jobs, and observability defaults.
Skill-Import-Attestation: reviewed-by=AE9B236FDAF0462874060C6BCFCFACF00335DC74; sha256=c1cbea456ddd65caa6fbf2ae0fc2bb75fc71274c9a584846b878b8b25807a65a
