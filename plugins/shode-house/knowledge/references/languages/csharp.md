# C# / .NET — Best Practices

> **Use cases**: Enterprise app, internal system, Windows app, Unity game, Azure-native
> **Why**: .NET strong ใน enterprise, Microsoft stack, Visual Studio ecosystem

## Setup
- **Version**: .NET 8 LTS (.NET 9 latest)
- **Lang**: C# 12+ (primary constructor, collection expression, alias any type)
- **Build**: `dotnet build`, `dotnet publish` (single file + AOT)
- **Lint+Format**: `dotnet format` + Roslyn analyzer + StyleCop
- **Test**: **xUnit** (default) + **NSubstitute** + **FluentAssertions** + **Bogus**

## Modern C#
- **Record** (immutable DTO, `with` expression for copy)
- **Pattern matching** (switch expression, list pattern, property pattern)
- **Nullable reference type** (`#nullable enable` — strict)
- **File-scoped namespace** (less nesting)
- **Top-level statement** (Program.cs minimal)
- **Required member**, **init-only setter**
- **Source generator** for boilerplate
- **Span<T>** / **Memory<T>** for zero-copy

## Web (ASP.NET Core)
- **Minimal API** (default new — concise)
- **MVC / Razor Pages** (legacy, complex apps)
- **Blazor** (full-stack C# — Server, WASM, Hybrid)
- **gRPC** built-in
- **SignalR** for real-time

## Architecture
- **Clean Architecture** (Mark Seemann, Steve Smith template)
- **Vertical Slice** (feature folder)
- **MediatR** for CQRS + handler
- **FluentValidation**
- **Polly** for resilience (retry, circuit breaker)
- **MassTransit** for message bus

## Database
- **EF Core 8+** (modern ORM, async-first)
- **Dapper** (micro-ORM, perf, raw SQL)
- **EF Core Migration** built-in
- Connection string from `appsettings.json` + user secret

## Testing
- **xUnit** (`[Fact]`, `[Theory]`)
- **NSubstitute** > Moq (cleaner API)
- **FluentAssertions** (readable assertion)
- **Testcontainers** for integration
- **WireMock.Net** for HTTP mock
- **Verify.Xunit** for snapshot test

## .NET Aspire (cloud-native — new)
- Service composition + observability + local orchestration
- Replaces docker-compose for .NET stack
- OpenTelemetry built-in

## Async
- **async/await** everywhere I/O
- **`ConfigureAwait(false)`** ใน library (avoid context capture)
- **IAsyncEnumerable<T>** for stream
- **CancellationToken** propagate ทุก async
- **Channel<T>** for producer-consumer
- **Parallel.ForEachAsync** for parallel + bounded

## Best Practices
- **Nullable reference type** strict
- **`var`** when type obvious; explicit when not
- **Interface "I" prefix** (convention, debated)
- **Sealed class** default (open only when needed)
- **Dependency injection** built-in (`IServiceCollection`)
- **Configuration**: `IOptions<T>` pattern
- **Logging**: `ILogger<T>` + structured (Serilog/NLog)
- **Health check**: built-in `AddHealthChecks`

## Deployment
- **Single-file** publish (`PublishSingleFile=true`)
- **Native AOT** (`PublishAot=true` — fast startup, no JIT)
- **Docker**: Microsoft official image (`mcr.microsoft.com/dotnet/aspnet`)
- **Azure App Service** / **Kubernetes** / **Azure Container Apps**

## ห้าม
- ห้าม `async void` ใน application code (only event handler)
- ห้าม `.Result` / `.Wait()` ใน async (deadlock risk)
- ห้าม `string` concat ใน loop (use `StringBuilder`)
- ห้าม `try { } catch { }` empty (กลืน error)
- ห้าม `null` return โดยไม่ document (use nullable type)
- ห้าม `static` mutable state ที่ไม่ thread-safe
- ห้าม `Console.WriteLine` ใน production (use logger)
- ห้าม catch `Exception` (specific)
