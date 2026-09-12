# Kotlin — Best Practices

> **Use cases**: Android (mandatory), JVM backend (Spring Boot, Ktor), multiplatform
> **Why**: ทำงานร่วม Java ได้ดี, type-safe, null-safety, coroutine

## Setup
- **Version**: 2.0+ (K2 compiler — faster)
- **Build**: Gradle Kotlin DSL (`build.gradle.kts`)
- **Lint+Format**: **detekt** + **ktlint**
- **Target**: JVM 21 (LTS), Android API 34+

## Idiomatic Kotlin
- `val` > `var` (immutable default)
- **Data class** > class for DTO (auto equals/hashCode/copy)
- **Sealed class/interface** for discriminated union (exhaustive `when`)
- **Extension function** sparingly (avoid pollution)
- **Scope function**: `let`/`run`/`also`/`apply`/`with` — pick by intent
- **Null safety**: `?.` chaining, `?:` Elvis, avoid `!!`
- **Smart cast** (auto narrow after `is` / `!= null`)
- **Inline class / value class** for type-safe wrapper

## Backend (Spring Boot 3+ / Ktor)
- **Spring Boot 3.2+** with Kotlin (mainstream enterprise)
- **Ktor** (lightweight, coroutine-native)
- **Micronaut** (compile-time DI, fast startup)
- **Quarkus** (Kotlin support, native compile)

## Coroutine (concurrency)
- `suspend` function for async (no callback hell)
- **Structured concurrency** — `coroutineScope`, `supervisorScope`
- **Flow** for stream (cold), **StateFlow/SharedFlow** (hot)
- **Dispatcher**: `Dispatchers.IO` for blocking I/O, `.Default` for CPU
- **Channel** for inter-coroutine communication
- Avoid `runBlocking` in production
- `withContext(IO)` for switching context

## Android
- **Jetpack Compose** (declarative UI) > XML
- **Hilt** (DI) > Dagger
- **Room** (DB) > raw SQLite
- **DataStore** > SharedPreferences
- **WorkManager** for background
- **ViewModel + StateFlow** (state mgmt)
- **Coil** (image, Compose-native) > Glide
- **Retrofit + OkHttp** for network

## Functional / Arrow
- **Arrow Kt** for FP (Either, Option, Validated, Resource)
- `Result<T>` built-in for fallible (Kotlin 1.5+)
- `runCatching {}` for safe exception → Result

## Testing
- **JUnit 5** + **MockK** (Kotlin-native)
- **Kotest** (DSL test, property-based)
- **Turbine** for Flow testing
- Compose UI test for Android

## Best Practices
- File ≤ 300 lines, function ≤ 30
- Public API: explicit return type (avoid type inference for API surface)
- Immutable default (`val`, `List`, `Map`)
- Top-level function (no static class wrapper needed)
- Companion object for constant + factory
- DSL builder pattern สำหรับ configuration

## ห้าม
- `!!` operator (force unwrap) — use `?.let {}` หรือ throw explicit
- `lateinit var` ที่ไม่จำเป็น (prefer constructor injection)
- `runBlocking` ใน production code
- `GlobalScope.launch` (use structured concurrency)
- Mutable state shared across coroutine without sync
- `Object` for namespacing (use top-level + package)
- Catch-all `try { } catch (e: Exception)` (specific exception)
