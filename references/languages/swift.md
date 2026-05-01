# Swift — Best Practices

> **Use cases**: iOS / iPadOS / macOS / watchOS / tvOS / visionOS app
> **Why**: native iOS performance + ecosystem

## Setup
- **Version**: Swift 5.9+ / 6 (concurrency strict)
- **Build**: Xcode 15+ (Swift Package Manager built-in)
- **Lint+Format**: **SwiftLint** + **SwiftFormat**
- **Target**: iOS 17+ (Observation framework, Macro)

## Idiomatic Swift
- `let` > `var` (immutable default)
- **Struct** > class (value semantic, default)
- **Enum with associated value** for state machine + result
- **Protocol-oriented** > inheritance
- **Optional** explicit (`?`/`!`) — avoid `!` (force unwrap) ใน production
- **Guard let** > if let (early exit)
- **Pattern matching** in switch — exhaustive
- **Property wrapper** (@State, @Binding, @Environment, @Observable)

## SwiftUI (UI)
- **Declarative** — view = function of state
- **@Observable** macro (Swift 5.9+) > ObservableObject
- **@Environment** for DI / theme
- **NavigationStack** + path binding
- **Sheet, popover, alert** modifier-based
- **AsyncImage**, **Charts** built-in
- Preview for design iteration

## Concurrency (Swift Concurrency)
- **async/await** > completion handler
- **Task** for async unit (cancellable)
- **TaskGroup** / **withDiscardingTaskGroup** for parallel
- **Actor** for state isolation
- **MainActor** for UI thread
- **Sendable** protocol for thread-safety
- Strict concurrency check (Swift 6) — find race at compile

## Storage
- **SwiftData** (default — Core Data wrapper, modern)
- **Core Data** (legacy, mature)
- **GRDB** (raw SQLite wrapper)
- **UserDefaults** for tiny preference
- **Keychain** for secret (KeychainAccess wrapper)

## Network
- **URLSession** (async/await)
- **Alamofire** (3rd party, mature)
- Codable + JSONDecoder/Encoder
- **AsyncSequence** for stream

## Testing
- **XCTest** (built-in)
- **Swift Testing** (Swift 6 — `@Test` macro, modern)
- **ViewInspector** for SwiftUI
- **XCUITest** for E2E
- **Snapshot testing** (pointfreeco/swift-snapshot-testing)

## Best Practices
- File ≤ 300 lines
- View ≤ 100 lines (extract subview)
- Extension for protocol conformance separate
- Async function = `async throws` (composable)
- Result builder for DSL
- Macro (Swift 5.9+) for repetitive boilerplate

## ห้าม
- `!` force unwrap — use `guard let` หรือ throw
- Implicitly unwrapped `Foo!` (UI outlet exception)
- Massive ViewController (extract to small view + view model)
- Sync I/O on main thread
- Singleton mutable state (use Actor / DI)
- `print` ใน production (use `os.log` / Logger)
- Hardcode UI string (use Localizable.strings)
- Force cast `as!` (use `as?` + handle nil)
