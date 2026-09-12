# General Backend Patterns (Dave reference)

> Read on-demand เมื่อ Dave ต้อง implement pattern เหล่านี้

## 🗄️ Database

- **Migration first** (Alembic/Flyway/Prisma/Atlas/sqlx) — never schema drift
- **ORM/query builder** ใน business (raw SQL เฉพาะ perf-critical + benchmark proven)
- **Transaction boundary** ใน service layer (ไม่ใช่ repository)
- **N+1 awareness** — eager load (JOIN) หรือ batch (DataLoader)
- **Index strategy** — explain แล้ว index ตามจริง
- **Pagination** — cursor (high-volume) > offset (small)
- **Online migration** for prod (expand-contract)
- **Soft delete** (`deleted_at`) > hard (audit trail)

## 🔌 API Design

- **REST** / **gRPC** (binary, low-latency) / **GraphQL** (flexible client)
- **OpenAPI 3.x** สำหรับ REST (auto-gen: FastAPI, NestJS Swagger, springdoc)
- **Versioning**: URL `/v1/` (clear) > header
- **Idempotency-key** สำหรับ POST side-effectful
- **Pagination** ทุก list (limit + cursor/offset)
- **Error**: RFC 7807 Problem Details (`type`, `title`, `status`, `detail`, `instance`)
- **Rate limit** + retry header (`Retry-After`, `X-RateLimit-*`)

## 📡 Observability (Dave emit, Aaron collect)

### Logs (structured JSON)
```json
{
  "ts": "2026-04-29T12:34:56Z",
  "level": "INFO",
  "msg": "payment.captured",
  "correlation_id": "abc-123",
  "user_id": 42,
  "amount_cents": 9999,
  "currency": "THB"
}
```
- Level: ERROR (action) / WARN (anomaly) / INFO (state) / DEBUG (dev)
- Context: correlation_id, user_id, request_id, span_id
- ห้าม leak: password, token, card, PII (mask `4111****1111`)

### Metrics (Prometheus)
- **RED**: Rate (`http_requests_total`), Error (`http_errors_total`), Duration (`http_request_duration_seconds` histogram)
- **USE** (resource): Utilization, Saturation, Errors
- Label cardinality ต่ำ (ห้าม `user_id` เป็น label)
- Counter monotonic, Histogram for latency, Gauge for instantaneous

### Traces (OpenTelemetry)
- Span ครอบ external call (DB, HTTP, queue, cache), business operation
- Attribute: `db.statement`, `http.url`, `messaging.destination`, `peer.service`
- Propagate `traceparent` header (W3C Trace Context) + queue header

### Health
- `/health` (liveness — process alive)
- `/ready` (readiness — deps ok: DB, cache, broker)
- ห้าม `/health` check deps (false negative → restart loop)

## 🚩 Feature Flags

- **Library**: LaunchDarkly / Unleash / Flipt (OSS) / GrowthBook / simple ENV
- **Patterns**:
  - **Release flag** — rollout per-user/segment (boolean)
  - **Ops flag** — kill switch (instant disable on incident)
  - **Experiment flag** — A/B (assignment + tracking)
  - **Permission flag** — entitlement (per-tenant/plan)
- **Discipline**: cleanup ≤ 90 วัน หลัง full rollout
- **Test** ทั้ง flag-on + flag-off path

## 🤖 AI / LLM Integration

- **SDK**: Vercel AI SDK (TS), Pydantic AI (Py), LangChain (caution — abstraction tax)
- **RAG**: chunk → embed → vector store (pgvector default) → retrieve → rerank → generate
- **Structured output**: JSON schema validation (Zod, Pydantic)
- **Tool use**: function calling + execute + return
- **Eval**: braintrust, promptfoo, langfuse (LLM-as-judge + golden set)
- **Caching**: prompt cache, embedding cache (cost saving 50%+)
- **Guardrail**: input/output validation, PII redaction, refusal detection

## 🧩 Patterns Quick Ref

- **Creational**: Factory, Builder, DI
- **Structural**: Adapter, Decorator, Facade, Proxy
- **Behavioral**: Strategy, Observer, Command, State, CoR
- **Concurrency**: Actor, Channel/CSP, Mutex, Worker Pool
- **Distributed**: Saga, CQRS, Event Sourcing, Outbox, Idempotent Receiver, Circuit Breaker, Bulkhead, Retry with backoff+jitter
