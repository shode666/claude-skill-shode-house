# Go — Best Practices

> **Use cases**: API, microservices, infra/DevOps tooling, CLI, cloud service
> **Why**: เร็ว, deploy ง่าย (single binary), great for small services

## Setup
- **Version**: 1.22+ (1.23 generics range)
- **PM**: Go modules (`go mod`)
- **Lint**: **golangci-lint** (`govet`, `staticcheck`, `ineffassign`, `unused`, `gosec`, `errcheck`)
- **Format**: `gofmt` / `goimports` (auto)
- **Test**: built-in `testing` + **testify** (assert/require/mock)
- **Build**: `go build -ldflags="-s -w"` for size

## Idiomatic Go
- **Small interface** — define ที่ consumer side
- **Composition > inheritance** — embed struct
- **Error wrapping**: `fmt.Errorf("operation X: %w", err)`
- **Error handling explicit** — ห้ามกลืน
- `defer` for cleanup (close, unlock, recover)
- Avoid `panic` ใน library (return error)
- `context.Context` ผ่านทุก call (cancel + deadline)
- `errors.Is` / `errors.As` for type check
- Pointer vs value receiver — consistent per type

## Project Structure
```
cmd/<binary>/main.go      # entry
internal/<feature>/       # private (compiler enforce)
pkg/<reusable>/           # public lib
api/                      # proto/openapi
configs/, scripts/, deployments/
```

## Frameworks
- **stdlib `net/http`** — start here (Go 1.22+ enhanced ServeMux)
- **Chi** (router, middleware), **Echo**, **Fiber** (perf), **Gin** (popular)
- **gRPC + Buf**, **Connect-RPC** (HTTP/2 + gRPC)
- **Templ** for HTML templating (type-safe)

## Database
- **sqlc** — type-safe SQL from `.sql` schema (recommended)
- **pgx** (Postgres native, fast)
- **GORM** (ORM, productivity)
- **squirrel** (query builder)
- **golang-migrate** (migration)

## Concurrency
- **Goroutine + channel** (CSP)
- **errgroup.Group** — concurrent + first error
- **sync.WaitGroup** for fire-and-forget
- **sync.Mutex** sparingly — prefer channel
- **context.WithCancel/WithTimeout** for lifetime
- Worker pool pattern for bounded concurrency

## Testing
- Table-driven test
- `t.Parallel()` for fast feedback
- **testify/require** (fail-fast) vs **assert** (continue)
- **gomock** / **mockery** for mock
- **Testcontainers-go** for integration
- Build tag for slow test (`//go:build integration`)

## Best Practices
- File ≤ 500 lines, function ≤ 50
- `pkg/` shallow (avoid deep nesting)
- Avoid init() — explicit setup
- Single binary deploy (no runtime deps)
- Embed static asset (`//go:embed`)
- Profile with `pprof` before optimize

## ห้าม
- ห้าม panic ใน library code
- ห้ามกลืน error (`if err != nil { return }` — wrap context)
- ห้าม `interface{}` (use `any` Go 1.18+)
- ห้าม global mutable
- ห้าม shared slice across goroutine without sync
- ห้าม `time.Sleep` ใน production retry (use backoff with jitter)
- ห้าม leak goroutine — always cancel via context
