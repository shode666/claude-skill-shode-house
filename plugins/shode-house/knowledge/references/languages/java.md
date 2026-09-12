# Java — Best Practices

> **Use cases**: Core backend, banking, insurance, enterprise API, Android (Kotlin preferred)
> **Why**: Stable, ecosystem ใหญ่สุด, Spring Boot dominant ใน enterprise

## Setup
- **Version**: Java 21 LTS (Java 17 minimum)
- **Build**: **Gradle Kotlin DSL** (`build.gradle.kts`) > Maven (legacy)
- **Lint+Format**: **spotless** + **google-java-format** + **errorprone**
- **Test**: **JUnit 5** + **Mockito** + **AssertJ** + **Testcontainers**
- **Static Analysis**: **PMD**, **SpotBugs**, **SonarQube**

## Modern Java (17/21)
- **Record** for DTO (immutable, auto equals/hashCode/toString)
- **Sealed class/interface** for ADT (exhaustive `switch`)
- **Pattern matching** in switch + instanceof
- **Text block** `"""..."""` for multiline string
- **Virtual thread** (Project Loom, Java 21) — millions of concurrent thread
- **Foreign Function & Memory API** (Project Panama)
- **`var`** for local inference (sparingly, when type obvious)

## Spring Boot 3+ (default enterprise)
- **Spring Boot 3.2+** (Java 17+, native compile via GraalVM)
- **Spring Web** (MVC) / **WebFlux** (reactive)
- **Spring Data JPA** / **Spring Data R2DBC** (reactive)
- **Spring Security 6** (JWT, OAuth2, OIDC)
- **Spring Cloud** (microservice — config, gateway, circuit breaker)
- **Spring Modulith** (modular monolith)
- **Actuator** for health/metric/trace

## Alternative Frameworks
- **Quarkus** (cloud-native, GraalVM, fast startup)
- **Micronaut** (compile-time DI, fast startup, low memory)
- **Helidon** (Oracle, MicroProfile)

## Database
- **JPA/Hibernate** (mature ORM)
- **jOOQ** (type-safe SQL, no ORM tax)
- **MyBatis** (SQL mapper)
- **Spring Data** abstraction
- **Flyway** / **Liquibase** for migration

## Async / Reactive
- **CompletableFuture** for async (legacy)
- **Project Reactor** (Mono/Flux) — reactive streams
- **RxJava** (older but stable)
- **Virtual thread** (Java 21 — replace most async/reactive complexity)
- **Structured concurrency** (Java 21 preview)

## Testing
- **JUnit 5** (`@Test`, `@ParameterizedTest`, `@Nested`)
- **AssertJ** > Hamcrest (fluent)
- **Mockito** + **mockito-kotlin** (if Kotlin)
- **Testcontainers** for integration (Postgres/Kafka/Redis real)
- **WireMock** for HTTP mock
- **ArchUnit** for architecture rules test

## Best Practices
- **Effective Java** rules (Bloch) — ยังใช้ได้
- **Immutable** default (final field, no setter)
- **Builder pattern** for complex constructor
- **Optional** for return type (ห้าม field/param)
- **Stream API** for collection processing (avoid for simple loop)
- **Try-with-resources** for AutoCloseable
- **Exception**: checked sparingly, runtime preferred
- **Logger via SLF4J** (not System.out)

## ห้าม
- ห้าม `null` return (use `Optional<T>`)
- ห้าม raw type `List` (use `List<T>`)
- ห้าม catch `Exception` / `Throwable` (specific)
- ห้าม `System.out.println` ใน production (use logger)
- ห้าม static mutable state (thread-safety risk)
- ห้าม `==` compare object (use `.equals()`)
- ห้าม long parameter list (≤ 4, use builder/record)
- ห้าม checked exception in API (use unchecked / Result type)
- ห้าม `synchronized` ทุกที่ (prefer concurrent collection)
