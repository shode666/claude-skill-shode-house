---
name: shode-house-evidence
description: |
  [WHAT] Evidence protocol — Project Evidence (NO MAGIC extension) + UX Evidence + Domain Evidence + REVIEW report format. บังคับ cite ก่อน claim.
  [AUDIENCE] ทุก agent ที่ผลิต claim/finding; Domain experts (Felix/Iris/Sam/Tara/Elena/Brooke/Emma); Uma (UX claim); Chris (review report).
  [WHEN] ทุกครั้งที่ agent claim "ระบบนี้ทำ X" หรือ "regulation บังคับ Y" หรือ "perf p95 = Z"; ก่อน hand-off; เขียน REVIEW report.
  [TRIGGER] /shode-house:evidence, "Project Evidence", "UX Evidence", "Domain Evidence", "cite", "evidence", "regulation cite", "REVIEW report", "WCAG", "axe", "Lighthouse".
---

# shode-house — Evidence Protocol

> ทุก claim ต้องมี evidence ตามมาทันที. ห้าม "ผมคิดว่า..." "น่าจะ..." "โดยปกติ..."

---
## 🔍 Project Evidence Protocol (🔴 v2.4 — NO MAGIC extension)

**Real-world knowledge ≠ project-specific fact.** ก่อน claim ใดๆ เกี่ยว stack/version/config/feature/convention ของ project นี้ — ต้อง verify ด้วย artifact จริงของ project

### 🚫 Forbidden phrase (ใช้ = ต้องมี evidence ตามมาทันที)
- "usually" / "by default" / "typically" / "standard practice" / "best practice"
- "Spring Boot/PG/Node/React ใช้..." (โดยไม่ check version + config)
- "should support" / "น่าจะรองรับ" / "ปกติแล้ว"
- "in most cases" / "โดยทั่วไป"

### ✅ Required evidence types
| Claim category | Evidence (paste actual output) |
|----------------|--------------------------------|
| Runtime version | `node -v`, `python --version`, `go version`, `java -version` |
| Framework version | `Read package.json:N`, `Read pom.xml:N`, `Read pyproject.toml:N` |
| Config format | `Glob '**/application.*'`, `Read tsconfig.json` |
| Dependency installed | `pnpm list <pkg>`, `cat requirements.txt`, `go.mod` |
| Feature available | `Bash` รันคำสั่ง paste output |
| File exists/path | `Glob`/`ls` first ก่อน assume path |
| Convention/pattern | Read CLAUDE.md / existing similar file ใน project |
| DB/service version | `psql -c 'SELECT version()'`, `redis-cli INFO server` |

### ❌ vs ✅ Pattern

❌ "Spring Boot รองรับ JPA filter ครับ" (เดาจาก real-world)
✅ "[Read pom.xml:25] spring-boot 3.2.1 + spring-data-jpa 3.2.1; [Read SecurityConfig.java:42] custom filter chain มีอยู่ — รองรับ"

❌ "Node 22 รองรับ fetch native ครับ"
✅ "[node -v] v16.20.0 — fetch ไม่รองรับ ต้องใช้ node-fetch หรือ axios"

❌ "PG รองรับ JSONB"
✅ "[psql -c 'SELECT version()'] PG 9.3.25 — JSONB ไม่รองรับ (มาเริ่ม 9.4) ต้อง upgrade หรือใช้ JSON"

### Format
ทุก factual claim เกี่ยว project นี้ cite ฟอร์ม `[<file>:<line>]` หรือ `[output: <command>]`

> Anti-puppet (ถัดไป) บังคับ — ใช้คำต้องห้ามโดยไม่ cite = treated as guess = block

---

## 📎 Extension protocols — อยู่กับเจ้าของ (v3.11)

| Protocol | อยู่ที่ | ใครใช้ |
|---|---|---|
| UX Evidence | `agents/ux-ui-designer.md` § UX Evidence | Uma |
| Domain Evidence | agent file ของ domain expert แต่ละตัว | 7 domain experts |
| REVIEW Report Format | `review-checklist/report-format.md` | Chris/Quinn/Sentinel |

ทั้งหมดเป็น extension ของ Project Evidence ข้างบน — cite-before-claim บังคับทุก agent เสมอ

## 🔐 Input Trust Levels (🔴 v2.5 — FS-inspired)
