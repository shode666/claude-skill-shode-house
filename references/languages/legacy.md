# Legacy: COBOL / PL-SQL / VBA — Best Practices

> **Use cases**: Banking core, ERP legacy, internal automation, financial system
> **Why**: ไม่ sexy แต่ "เงินจริง" ใน enterprise; modernize ทำเป็น strangler fig

## COBOL

### Setup
- **Compiler**: GnuCOBOL (OSS), IBM Enterprise COBOL (mainframe), Micro Focus
- **IDE**: VS Code + COBOL extension (modern); Eclipse + COBOL plugin
- **Test**: COBOLUnit, GnuCOBOL test harness
- **Modernization tool**: AWS Mainframe Modernization, IBM Watsonx Code Assistant for Z

### Basics
- **DIVISION** structure: IDENTIFICATION / ENVIRONMENT / DATA / PROCEDURE
- **Fixed-format** (column 1-72) vs **free-format** (modern)
- **PICTURE clause** (`PIC 9(5)V99` = 5-digit + 2 decimal)
- **COPY** (include) for shared structure (copybook)

### Best Practices
- **Structured**: PERFORM ... THRU ... (avoid GO TO)
- **Modular**: separate program per business function
- **Copy book** for shared data layout
- **Avoid ALTER** statement (legacy spaghetti)
- **EVALUATE** > nested IF
- **Initialize** field explicit
- **Version control git** (yes, even COBOL)

### Modernization Path
- Phase 1: Wrap COBOL with API (Java/REST gateway)
- Phase 2: Strangler fig — extract feature → modern language
- Phase 3: Deprecate COBOL module
- Migration target: Java + Spring Batch (mainframe → cloud)

### ห้าม
- ห้าม ALTER statement
- ห้าม GO TO ที่กระโดดข้าม section
- ห้าม global mutable state ที่ไม่ document
- ห้าม direct CICS update โดยไม่มี audit

---

## PL/SQL (Oracle)

### Setup
- **DB**: Oracle 19c+ / 23ai
- **IDE**: SQL Developer, DataGrip, Toad
- **Test**: utPLSQL (xUnit-style)
- **Lint**: SonarQube + PL/SQL plugin

### Best Practices
- **Package** > standalone procedure (encapsulate + version)
- **PRAGMA AUTONOMOUS_TRANSACTION** sparingly (debug ยาก)
- **BULK COLLECT + FORALL** for bulk DML (perf)
- **Cursor**: explicit > implicit (control)
- **Exception handling**: WHEN OTHERS + log, ห้าม swallow
- **DBMS_OUTPUT**: dev only; production use logging table
- **CONSTANT** for magic value
- **`%TYPE` + `%ROWTYPE`** for schema-tied type
- **Pipelined function** for streaming result

### Performance
- **EXPLAIN PLAN** + SQL Trace
- **Bind variable** (avoid hard parse)
- **Index** strategy (B-tree, bitmap, function-based)
- **Partition** large table
- **Materialized view** for heavy query
- **HINT** sparingly (let optimizer work)

### Modernization
- Phase 1: API wrapper (PL/SQL → REST via APEX/ORDS)
- Phase 2: Extract logic → Java/Python service
- Phase 3: Switch to open-source DB (Postgres + plpgsql) ถ้า budget

### ห้าม
- ห้าม `WHEN OTHERS THEN NULL` (swallow)
- ห้าม dynamic SQL ที่ concat user input (SQL injection)
- ห้าม `COMMIT` ใน loop (perf disaster)
- ห้าม deep nested cursor (use BULK COLLECT)
- ห้าม trigger ที่มี business logic ซับซ้อน

---

## VBA (Excel / Office automation)

### Setup
- **IDE**: VBA editor ใน Excel (Alt+F11)
- **Lint**: Rubberduck VBA
- **Modern alt**: **Office Scripts** (TypeScript-based, cloud), **Power Automate**, **Python in Excel** (Microsoft 365)

### Best Practices
- **Option Explicit** ทุก module (force declare variable)
- **Module per concern** (avoid 1 huge module)
- **Class module** for OOP (Person.cls)
- **Error Handling**: `On Error GoTo` + label + `Resume` / `Exit Sub`
- **Constants** at module top
- **Avoid Select / Activate** (slow + fragile) — use range object
- **Application.ScreenUpdating = False** ก่อน batch operation
- **Disable events** before bulk DML

### Performance
- Read range to array → process → write back
- Avoid cell-by-cell read/write (100x slower)
- `Application.Calculation = xlManual` for batch
- Worksheet protect = perf hit

### Migration Path
- **Office Scripts** (TypeScript) — modern replacement สำหรับ shared workbook
- **Power Query** (M language) — for data transform
- **Power Automate** — workflow automation
- **Python in Excel** — calc/analysis (Microsoft 365 only)
- **External API + COM** — fully migrate

### ห้าม
- ห้าม `On Error Resume Next` ที่ไม่มี handler ตามมา (silent fail)
- ห้าม `.Select` / `.Activate` (use range directly)
- ห้าม global variable ที่ไม่ document
- ห้าม VBA macro โดยไม่ digital sign (security)
- ห้าม hardcode path → use Application.Path / FileDialog
- ห้าม distribute .xlsm + macro โดยไม่ enable warning

---

## Universal Legacy Migration Strategy

```
Phase 1 (low risk)
  → Wrap legacy with API
  → Add monitoring + log
  → Document existing behavior + golden test

Phase 2 (medium risk)
  → Strangler fig — extract feature → new lang
  → Dual write / dual read for verification
  → Feature flag per extracted feature

Phase 3 (high risk)
  → Deprecate legacy module (after metric prove new = better)
  → Sunset announcement (6-12 month)
  → Final cutover + decommission
```

> Sara กำหนด strategy + Aaron implement infra. Felix/Elena consult ถ้า financial/accounting impact.
