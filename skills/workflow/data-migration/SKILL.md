---
name: data-migration
description: Plan and carry out a schema or data migration, such as DDL, backfill, dual write or expand-contract rollout, with rehearsed rollback and extra care for money and regulated data. Not for ordinary SQL queries, disposable local databases or a manual one-row production fix.
---

# Data Migration (expand-contract + backfill + rollback drill)

> **Owner**: Dave (เขียน) + Aaron (รัน + rollback) + Sara (ตัดสิน schema + ADR). Money/regulated data → Domain expert sign
> Classify the actual migration operation by environment, impact and reversibility. Production execution requires `pre-data-migration` evidence and authorization; preparing a migration does not itself authorize execution.

## When NOT to use

- **Dev/local DB ที่ทิ้งได้** — `docker compose down -v` แล้ว seed ใหม่ ไม่ต้องทำ ceremony
- **แก้ข้อมูลแถวเดียวใน prod แบบ manual** — นั่นคือ incident/hotfix → `incident` + change ticket ห้ามเรียกว่า migration
- **Schema ยังไม่นิ่ง (Phase 1a ยังไม่ sign-off)** — ส่ง schema decision ให้ Sara ก่อน อย่า execute ตาม spec ที่ยังเปลี่ยน
- **Data warehouse / analytics rebuild** — คนละ risk model (rebuild ได้) ใช้ pipeline discipline แทน

## Required inputs — before production execution

- [ ] **Migration tool + version ของ project** (Flyway / Liquibase / Alembic / Prisma / goose / Rails) — cite จาก repo จริง ห้ามเดา
- [ ] **Row count + table size จริงของ prod** (`SELECT count(*)`, table bytes) — ตัดสิน online vs offline ไม่ได้ถ้าไม่รู้
- [ ] **Downtime budget** (0 = zero-downtime บังคับ expand-contract)
- [ ] **Rollback path** — down migration หรือ restore plan + RTO/RPO ที่ยอมรับได้
- [ ] **Data classification** — มี money / PII / regulated field ไหม (ถ้ามี → Domain expert + Sentinel เข้า)

Discover accessible inputs first. Missing production facts block execution and
safety claims, not authorized design, implementation or local rehearsal. Record
unknowns and obtain consequential policy decisions through Oliver.

## Expand → Migrate → Contract (🔴 default สำหรับทุก breaking schema change)

ห้าม `ALTER`/`DROP`/`RENAME` ในดีพลอยเดียว — แตกเป็น 3 release

```
E) EXPAND    เพิ่มของใหม่แบบ nullable/มี default — โค้ดเก่ายังรันได้
             add column (NULL) · add table · add index CONCURRENTLY · dual-write เริ่มตรงนี้
M) MIGRATE   backfill เป็น batch + verify + สลับ read ไปคอลัมน์ใหม่ (feature flag)
C) CONTRACT  หยุด dual-write → drop คอลัมน์/ตารางเก่า  ← release แยก หลัง soak
```

**Soak time ขั้นต่ำก่อน CONTRACT**: 1 release cycle หรือจนกว่า metric ยืนยันว่าไม่มีใครอ่านของเก่าแล้ว (log/metric บน read path เก่า = 0 ต่อเนื่อง)

## Backfill rules

- **Batch เสมอ** (`LIMIT n` + คีย์เรียงลำดับ) ห้าม single `UPDATE` ทั้งตาราง — lock + WAL/undo ระเบิด
- Batch size จาก row count จริง; มี sleep คั่น; วัด replica lag ทุก batch → lag เกิน threshold = หยุดเอง
- **Idempotent + resumable** — เก็บ cursor ไว้; รันซ้ำต้องไม่พัง
- **Kill switch** — หยุดกลางคันได้ ข้อมูลยัง consistent
- Verify: `count(*) WHERE new IS NULL` = 0 + sample diff เทียบเก่า/ใหม่ → **paste ผลจริง**

## Index / lock

- Postgres: `CREATE INDEX CONCURRENTLY` · `ALTER TABLE ... ADD COLUMN` มี default = ตรวจว่า version ไหน rewrite ตาราง · ตั้ง `lock_timeout` + `statement_timeout` ทุก migration
- MySQL: `ALGORITHM=INPLACE, LOCK=NONE` หรือ gh-ost / pt-online-schema-change
- ห้าม migration ที่ถือ exclusive lock บนตาราง hot โดยไม่มี timeout — timeout แล้ว retry ดีกว่าค้างทั้งระบบ

## Money / ledger / regulated (🔴 Domain expert บังคับ)

- **ห้าม migrate ledger แบบ destructive** — ledger เป็น append-only: แก้ยอดผิดด้วย **correcting entry** ไม่ใช่ `UPDATE`
- เปลี่ยนชนิดจำนวนเงิน → Decimal/integer minor-unit เท่านั้น (ห้าม float) + พิสูจน์ว่าไม่มี rounding drift: sum ก่อน = sum หลัง **paste ตัวเลขทั้งสองฝั่ง**
- PII: migration ที่ copy PII ไปตารางใหม่ = ขยาย blast radius → Sentinel review + retention policy ของฟิลด์ใหม่
- Regulated (BOT/OIC/SEC/IFRS): audit trail ต้องไม่ขาดตอน — เก็บ before/after ของแถวที่แตะ

## Rollback drill (🔴 ห้าม deploy ถ้ายังไม่ซ้อม)

```
1. restore snapshot ลง staging (จับเวลา → นี่คือ RTO จริง ไม่ใช่ที่เดา)
2. รัน migration ขึ้น → รัน down/rollback → verify schema + data กลับสภาพเดิม
3. paste เวลาที่ใช้ + ผล verify
```

ถ้า migration **rollback ไม่ได้** (drop column/table) → บอกตรง ๆ ว่า one-way แล้ว rollback path = restore from backup พร้อม RTO ที่วัดแล้ว — ห้ามเขียนว่า "rollback ได้" ลอย ๆ

## Gate `pre-data-migration` (⏸️ Oliver + owner approve)

```
□ expand-contract แยก release แล้ว (หรือระบุเหตุผลว่าทำไมไม่ต้อง)
□ backfill batched + idempotent + resumable + kill switch
□ lock_timeout / statement_timeout ตั้งแล้ว
□ rollback drill รันบน staging + paste เวลา
□ row count ของจริง + ประมาณเวลารัน
□ Domain expert sign (ถ้าแตะ money/regulated) · Sentinel sign (ถ้าแตะ PII)
□ observability: metric แถวที่ backfill แล้ว + replica lag + error rate
```

## Evidence

```
✅ "[psql] SELECT count(*) FROM orders → 48,213,004 rows; batch=5000, sleep=200ms, est 3h20m"
✅ "[staging] restore snapshot 14m32s = RTO จริง; up→down→verify schema diff = empty"
✅ "[Decimal check] sum(amount) before=1,204,883.55 after=1,204,883.55 diff=0"
❌ "migration ปลอดภัย rollback ได้" (ไม่มี drill, ไม่มีตัวเลข)
```

## ห้าม

- ห้าม `DROP`/`RENAME` column-table ใน release เดียวกับที่โค้ดใหม่ขึ้น
- ห้าม backfill เป็น statement เดียวบนตารางใหญ่
- ห้าม migration ที่ไม่มี timeout
- ห้าม `UPDATE` ยอดใน ledger — ใช้ correcting entry
- ห้าม deploy migration โดยไม่ซ้อม rollback
- ห้ามรัน migration บน prod โดยไม่มี authorization และ gate evidence — Aaron owns execution preparation; follow the actual project/host approval mechanism and preserve any explicit human-execution requirement.

## Skill composition

| Situation | Next skill |
|---|---|
| เขียน migration + test | → `dev-gate` (TDD: test ที่ fail ก่อน migrate) |
| verify หลัง migrate | → `review-checklist` (Chris data-integrity) · `automate-test` (regression) |
| แตะ PII / auth | → `secure` (Sentinel) |
| migration ทำ prod พัง | → `incident` (mitigate ก่อน) แล้ว `diagnose` |
| schema decision ยังไม่นิ่ง | → Sara (`agents/solution-architect.md`, ADR when applicable) |
