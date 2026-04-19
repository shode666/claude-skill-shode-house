---
description: "[shode-house] Implement feature code (Dave) + Chris review/unit test + Quinn integration"
allowed-tools: Task, Read, Write, Edit, Grep, Glob, Bash
argument-hint: [feature description or spec path]
---

Implement: **$ARGUMENTS**

## Pipeline

### 1. Context (Dave)
- อ่าน spec/user stories (ถ้ามี path) — ถ้าไม่มี ถาม user
- อ่าน convention โค้ด existing
- ปรึกษา Sara/Bella/Domain Expert ถ้า spec ไม่ชัด

### 2. Plan
Dave present:
- Files ที่จะแตะ
- Dependencies ใหม่
- Migration plan (ถ้า schema change)
- Open questions

→ user approve

### 3. Implement
- Follow project convention
- Type-safe, error handling, structured logging
- Money → Decimal/integer (ห้าม float)
- Feature flag (ถ้า risky)
- Observability: log + metric (RED) + trace
- Commit: Conventional Commits

### 4. Smoke Test
- Start server + curl happy path
- ยืนยันว่าทำงานได้

### 5. Hand-off
- **Chris** → review 7 มิติ + unit test (business/edge/error/boundary)
- **Quinn** → integration + E2E (critical path)
- **Aaron** → env var / Dockerfile / CI ถ้ามีของใหม่

### 6. Domain Validation (conditional)
Sensitive feature → **บังคับ** Domain Expert validate:
- payment/ledger → Felix
- accounting/inventory → Elena
- trading → Tara
- insurance → Iris
- booking → Brooke
- ecommerce → Emma

## ⚠️ Rules

1. ต้องมี spec ก่อน → ถ้าไม่มีรัน `/spec-only` หรือ `/design-system`
2. Chris เขียน unit test (Dave smoke test ok)
3. Quinn integration/E2E สำหรับ critical path
4. Domain Expert validation บังคับสำหรับ sensitive
5. ห้าม merge จน Chris + Quinn approve
6. ภาษาไทย; code ตาม convention
