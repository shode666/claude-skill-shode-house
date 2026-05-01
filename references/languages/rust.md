# Rust — Best Practices

> **Use cases**: Infra, performance-critical, blockchain, security, embedded, systems
> **Why**: Memory-safe + zero-cost abstraction + perf
> **Caveat**: Hiring ยากกว่า Go; learning curve สูงสุดใน mainstream lang

## Setup
- **Version**: 1.80+ (latest stable)
- **PM**: cargo (built-in)
- **Lint**: **clippy** (`cargo clippy --all-targets --all-features -- -D warnings`)
- **Format**: `rustfmt`
- **Edition**: 2024 (latest)

## Idiomatic Rust
- **Ownership + borrow** discipline — single owner, multiple borrow xor mutable borrow
- **Lifetime** explicit ตอน compiler ต้องการ (มัก inferable)
- **`Result<T, E>`** for fallible (ห้าม panic ใน library)
- **`Option<T>`** for nullable (no null)
- **Pattern match** exhaustive (`match`, `if let`, `while let`)
- **Trait** for shared behavior (composition)
- **Newtype pattern** for type-safe wrapper
- **`?` operator** for error propagation
- **`.into()` / `.try_into()`** for conversion

## Error Handling
- **anyhow** for application (dynamic error)
- **thiserror** for library (typed error)
- `Result<T, E>` propagate via `?`
- Custom error enum + `From` implement

## Async
- **tokio** (default runtime, multi-threaded)
- **async-std** alt; **smol** (minimal)
- `async fn` returns `impl Future<Output=T>`
- **Send + Sync** trait for thread-safety
- Avoid blocking in async (use `tokio::task::spawn_blocking`)

## Web Backend
- **Axum** (default, Tokio-native, modular)
- **Actix-web** (mature, perf)
- **Rocket** (declarative, beginner-friendly)
- **Loco** (Rails-like)

## Database
- **sqlx** (async, compile-time check) — recommended
- **Diesel** (sync ORM, mature)
- **SeaORM** (async ORM)

## CLI
- **clap** (derive macro for arg parsing)
- **anyhow** for error
- **indicatif** for progress bar

## Other Stack
- **Tauri** for cross-platform desktop (alt Electron)
- **Leptos** / **Yew** / **Dioxus** for full-stack/frontend
- **wasm-bindgen** for WebAssembly

## Testing
- Built-in `#[test]` + `cargo test`
- **proptest** for property-based
- **criterion** for benchmark
- **mockall** for mock
- Integration test ใน `tests/` folder

## Best Practices
- Module per file/folder; `mod.rs` ↔ inline `mod`
- Public API minimal (`pub` explicit, default private)
- Document public item (`///` doc comment + example)
- Doctest (example code = test)
- **`Cargo.lock` commit** for binary, optional for library
- Avoid `unsafe` (justify with comment + scope minimal)
- Profile with `cargo flamegraph` before optimize

## ห้าม
- `unwrap()` / `expect()` ใน production (panic on None/Err)
- `unsafe` โดยไม่มีเหตุผลชัด + comment + audit
- `clone()` มากเกินไป (cost) — use reference
- `Box<dyn Trait>` ทุกที่ (use generic + `impl Trait` ก่อน)
- `static mut` (use `OnceCell` / `LazyLock` / Mutex)
- Premature optimization (profile first)
