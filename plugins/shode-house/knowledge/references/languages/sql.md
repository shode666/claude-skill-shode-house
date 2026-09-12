# SQL — Best Practices (Postgres-first, applicable MySQL/SQLite/MSSQL)

> **Use cases**: Database, analytics, BI, reporting, data warehouse
> **Why**: ขาดไม่ได้ในทุก product มีข้อมูล

## Schema Design
- **Normal form** 3NF default; denormalize ตอน performance prove
- **Primary key**: surrogate (UUID v7 / ULID — sortable + unique) > sequential int (legacy)
- **Foreign key** explicit (`REFERENCES` + `ON DELETE`); index FK column
- **NOT NULL** default — null = explicit decision
- **Check constraint** สำหรับ business rule (`amount > 0`)
- **Unique constraint** สำหรับ natural key
- **Generated column** สำหรับ derived (`GENERATED ALWAYS AS (...)`)
- **Timestamp**: `TIMESTAMP WITH TIME ZONE` (UTC store) — avoid `TIMESTAMP` (ambiguous)

## Naming
- snake_case (table, column)
- Plural table (`users`, `orders`) — convention varies
- ID: `id` หรือ `<entity>_id` for FK
- Timestamp: `created_at`, `updated_at`, `deleted_at` (soft delete)
- Boolean: `is_active`, `has_consent`

## Index
- Index FK column, frequently filtered, joined
- **Composite index**: order matter (most selective first)
- **Partial index** สำหรับ subset (`WHERE status = 'active'`)
- **Covering index** (INCLUDE) avoid heap lookup
- **GIN** for JSONB / full-text
- ห้าม index ทุก column — write penalty
- `EXPLAIN ANALYZE` ก่อน optimize

## Query
- `SELECT col1, col2` (ห้าม `SELECT *` ใน production)
- `JOIN` explicit (INNER/LEFT/RIGHT/FULL) — avoid implicit comma
- `WHERE` ก่อน `JOIN` ถ้าเป็นไปได้ (filter early)
- **CTE** (`WITH ... AS`) for readability + reuse
- **Window function** สำหรับ ranking, running total
- **UPSERT** (`INSERT ... ON CONFLICT`) — atomic
- **RETURNING** สำหรับ insert+fetch one round-trip
- Prepared statement / parameterized (ห้าม string concat)

## Transaction
- ACID default (Postgres)
- `BEGIN` ... `COMMIT`/`ROLLBACK`; `SAVEPOINT` สำหรับ nested
- Isolation: READ COMMITTED (default) → REPEATABLE READ → SERIALIZABLE (high contention need)
- **SELECT FOR UPDATE** สำหรับ pessimistic lock
- **Optimistic lock** via version column / `xmin`
- Keep tx short — release lock เร็ว

## Performance
- `EXPLAIN ANALYZE` first, optimize ตาม
- Seq scan acceptable สำหรับ small table; index scan สำหรับ large
- **N+1**: avoid via JOIN / batch / subquery
- **Pagination**: cursor (keyset) > offset (degrades on large)
- **Materialized view** สำหรับ heavy aggregation
- **Partitioning**: range (date), list (region), hash (load distribute)
- **Connection pool** — pgbouncer (transaction pool)

## Postgres-specific
- **JSONB** > JSON (binary, indexed, faster)
- **Array** type, **HSTORE**, **range** type
- **CTE recursive** for tree/graph
- **LATERAL** join for correlated subquery
- **ROW-LEVEL SECURITY** (RLS) for multi-tenant
- **pgvector** for AI embedding
- **pg_partman** for partition automation
- **TimescaleDB** for time-series

## Migration
- Always **expand-contract** for breaking change in prod
- `ADD COLUMN ... NULL` (instant) > `ADD COLUMN ... NOT NULL DEFAULT` (rewrite table)
- `CONCURRENTLY` for index in prod (`CREATE INDEX CONCURRENTLY`)
- Online schema tool: `pt-online-schema-change` (MySQL), `pg_repack`
- Rollback plan ทุก migration

## Best Practices
- Never `DELETE` without `WHERE` (use `TRUNCATE` if intent)
- Audit log via trigger หรือ application
- Soft delete (`deleted_at`) > hard delete (audit trail)
- Backup 3-2-1; PITR (Point-in-Time Recovery) for prod
- Read replica สำหรับ scaling read
- **HOT updates** (Postgres) — no index column change

## ห้าม
- `SELECT *` ใน prod query
- String concat → SQL injection (parameterized only)
- Long transaction (block other)
- `OFFSET` large (slow) — use cursor
- Index column ที่ update บ่อย
- Trigger สำหรับ business logic ซับซ้อน (debug ยาก)
- Float for money (use NUMERIC/DECIMAL)
- TIMESTAMP WITHOUT TIME ZONE (ambiguous)
