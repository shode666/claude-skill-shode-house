# Dart / Flutter — Best Practices

> **Use cases**: Flutter mobile/desktop/web cross-platform
> **Why**: ทำ cross-platform เร็ว, single codebase

## Setup
- **Dart**: 3.5+ (3.6 macros)
- **Flutter**: 3.24+ (Material 3 + Cupertino)
- **PM**: pub
- **Lint**: `package:lints` strict + `flutter_lints`
- **Format**: `dart format` (built-in)

## Idiomatic Dart
- **Sound null safety** — explicit `?` and `!`
- **`var` / `final` / `const`** — `const` > `final` > `var`
- **Pattern matching** (Dart 3+): `switch` expression, record, destructure
- **Records** (`(int, String)`) for tuple/multi-return
- **Sealed class** for discriminated union (exhaustive `switch`)
- **Async/await** + Future + Stream
- **Extension** for utility (sparingly — avoid pollution)

## Flutter
- **Stateless** > Stateful (เมื่อทำได้)
- **Composition** over deep widget tree
- **Hooks** (flutter_hooks) สำหรับ reduce boilerplate
- **State management**:
  - **Riverpod 2+** (recommended — type-safe, compile-time)
  - **Bloc** (mature, predictable)
  - Provider (legacy)
- **Freezed** for immutable data class + union (code gen)
- **GoRouter** for routing (URL-based)
- **Dio** for HTTP, **Retrofit** for typed API

## Storage / DB
- **Drift** (type-safe SQLite) — recommended
- **Isar** (NoSQL, fast)
- **Hive** (KV)
- **shared_preferences** (small KV)
- **flutter_secure_storage** for secret

## Testing
- `flutter_test` (unit + widget)
- **integration_test** (E2E)
- **mocktail** (modern mock — no code gen)
- **golden test** for visual regression

## Architecture
- **Clean Architecture / Layered**: presentation → domain → data
- **Repository pattern** for data source abstraction
- **DI**: Riverpod (recommended) / get_it
- **Result type** (e.g., `fpdart Either`) for fallible

## Best Practices
- File ≤ 300 lines, widget ≤ 150 lines (extract subwidget)
- Const constructor + const widget (rebuild perf)
- Avoid setState in deep tree (use scoped state)
- Lazy load with `ListView.builder`
- Image: `cached_network_image`, optimize size
- `dispose` controller in StatefulWidget
- L10n built-in (intl + arb file)

## Build / Deploy
- **flutter build** per platform (apk, ios, web, windows, linux, macos)
- **codemagic** / **fastlane** / **GitHub Actions** for CI/CD
- **Firebase Distribution** for beta
- Code signing automated

## ห้าม
- `print()` ใน production (use `debugPrint` หรือ `logger`)
- Mutable global state (use DI + state mgmt)
- `dynamic` ที่ไม่จำเป็น (defeat null safety)
- Sync I/O on main isolate (use compute() / Isolate)
- `setState` ใน initState (use post-frame callback)
- Deep widget tree (extract method = same rebuild; extract widget = better)
- Hardcode color/string → theme + l10n
