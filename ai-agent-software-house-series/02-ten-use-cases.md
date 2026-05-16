# Part 2 — 10 Use Cases จริงเมื่อ AI เข้า Codebase แบบไม่มีระบบ

> ทุก case ในตอนนี้ผมเคยเจอด้วยตัวเอง หรือได้ฟังจาก engineer ในที่ประชุมที่เริ่มต้นด้วยประโยค "อันนี้พูดในที่ประชุมแบบ off-the-record นะ" — รายชื่อบริษัทเซ็นเซอร์ไว้ แต่อาการเหมือนกันหมด

ถ้าคุณอ่าน Part 1 แล้วเริ่มสงสัยว่าทีมตัวเองอยู่ตรงไหน ตอนนี้คือ checkpoint แรก เคสไหนที่อ่านแล้วรู้สึกว่า "เออ เคยเจอ" — นั่นคือสัญญาณว่าคุณอยู่ใน pattern ที่ขยายผลด้วย AI ได้เร็วมาก ทั้งดีและร้าย

ผมจัดกลุ่มเคสไว้ 4 กลุ่มเพื่อให้อ่านง่าย:

- **กลุ่ม A — Drift ในโค้ด** (Case 1-4): pattern, design system, DB schema, API contract กระจายออกจาก center
- **กลุ่ม B — คุณภาพและความปลอดภัย** (Case 5-6): security bug, test ที่ดูดีแต่ไม่ครอบ
- **กลุ่ม C — Process roles** (Case 7-9): PM, BA, SA ใช้ AI แล้วพลาดที่ตรงไหน
- **กลุ่ม D — Production** (Case 10): AI ในห้อง incident

---

## กลุ่ม A — Drift ในโค้ด

### Case 1: Dev 10 คน ใช้ AI แล้วได้ code 10 ทรง

**สถานการณ์**

องค์กรมีทีม dev 10 คน เริ่มใช้ ChatGPT, Copilot, Cursor, Claude Code โดยไม่มี instruction file กลาง

แต่ละคนสั่ง AI ด้วย prompt ของตัวเอง:
- "ช่วยเขียน API เพิ่ม user"
- "generate service class"
- "ทำ React form ให้หน่อย"
- "เขียน unit test"
- "refactor ให้ clean"

**สิ่งที่เกิด**

| Area | ปัญหา |
|---|---|
| Naming | `UserService`, `UserManager`, `UserUseCase`, `UserHandler` ปนกัน |
| API response | `{ data }`, `{ result }`, raw object — มีหมด |
| Error handling | throw, return null, catch เงียบ — มีหมด |
| HTTP client | `axios.get()` ตรง ๆ vs internal `apiClient` |
| Auth | บาง endpoint ลืม permission check |
| Logging | บางจุด log token/email |
| Test | test ผ่านแต่ไม่ได้ assert business rule จริง |

**ผลกระทบ**

- Code review ยาวขึ้น
- Senior dev ต้องแก้ style และ architecture ซ้ำ ๆ
- PR merge ช้าลงทั้งที่เปิดเร็วขึ้น
- Technical debt เพิ่มแบบกระจายตัว
- ทีมรู้สึกว่า AI ช่วย dev แต่ทำร้าย reviewer

**วิธีแก้ — Handbook + Enforcement**

ตัวอย่างกฎใน `CLAUDE.md` / `AGENTS.md`:

```md
# API Client Rule

Do not use axios/fetch directly in feature code.
Always use `@company/api-client`.

Bad:
axios.get('/api/users')

Good:
apiClient.get<UserResponse>('/api/users')
```

ตัวอย่าง enforcement ที่ตีกลับ deterministic:

- ESLint rule ห้าม import `axios` ใน `src/features/**`
- CI fail ถ้าพบ raw HTTP client
- AI reviewer ใส่ comment ก่อน PR เปิด

**Before / After**

| Before | After |
|---|---|
| AI generate code ตามใจ prompt | AI generate code ตาม handbook |
| Reviewer คุมทุกอย่างด้วยแรงกาย | CI + AI reviewer คุมก่อนถึงคน |
| PR comment เรื่อง naming เต็มไปหมด | Reviewer focus ที่ business logic |
| Technical debt เพิ่มเงียบ ๆ | Drift ถูกจับตั้งแต่ pre-commit |

**บทเรียน**

ถ้าไม่มี handbook กลาง การ "ใช้ AI" คือการ outsource decision-making ให้ context window ของแต่ละคน ซึ่งไม่ scale และไม่ audit ได้

---

### Case 2: AI สร้าง component ซ้ำทั้งที่บริษัทมี Design System

**สถานการณ์**

ทีม frontend มี internal library อยู่แล้ว:

```text
@company/ui
@company/forms
@company/themes
```

แต่ dev สั่ง AI generate หน้าใหม่ ได้ output แบบนี้:

```tsx
<button className="bg-blue-500 px-4 py-2 rounded">
  Submit
</button>
```

AI ไม่รู้ว่าบริษัทมี `<Button />`, `<FormField />`, `<DatePicker />`, `<DataTable />` ใช้อยู่แล้ว — เพราะ AI ไม่ได้เห็น component catalog

**ปัญหา**

- UI ไม่ตรง design system
- Dark mode พัง
- Accessibility ไม่ผ่าน WCAG
- Validation pattern ไม่ตรง
- CSS กระจัดกระจาย — บางที่ใช้ Tailwind utility, บางที่ใช้ token, บางที่ hard-code hex
- UX/UI designer ต้องไล่ comment เรื่อง spacing, color, component usage

**วิธีแก้ — 3 ชั้น**

1. **Frontend instruction file**

```md
# Frontend UI Rules

- Never use raw `<button>`, `<input>`, `<select>` in feature screens.
- Use components from `@company/ui`.
- Use `FormField` from `@company/forms` for all form inputs.
- Use design tokens, not hard-coded colors.
- All screens must support light/dark theme.
- Every interactive element needs aria-label or visible label.
```

2. **Component Catalog MCP** — AI query ก่อน generate:

```text
Find existing components for:
- primary button
- date range picker
- customer search field
- status badge
```

ได้คำตอบ:

```text
Use:
- Button from @company/ui
- DateRangePicker from @company/forms
- CustomerSearchInput from @company/components/customer
- StatusBadge from @company/ui (variant: success | warning | danger)
```

3. **Enforcement** — ESLint rule, Storybook visual regression, accessibility test ใน CI

**Throughput ที่เพิ่ม**

| งาน | ก่อน | หลัง |
|---|---|---|
| สร้างหน้าใหม่ | เร็วแต่ inconsistent | เร็วและ reuse |
| UX review | comment เยอะ | ลด comment เรื่อง component |
| Frontend refactor | ตามแก้ทีหลัง | กันตั้งแต่ generate |
| Design drift | สูง | ต่ำลง |

**บทเรียน**

Design system ที่ดีเปล่า ๆ ไม่พอ — ต้องทำให้ AI เห็นมัน ไม่งั้น AI จะสร้างของซ้ำเร็วกว่าทีม design จะวาดเสร็จด้วยซ้ำ

---

### Case 3: AI สร้าง database column ซ้ำ เพราะไม่เห็น schema จริง

**สถานการณ์**

Ticket เขียนว่า:

> เพิ่มข้อมูลประเภทลูกค้าในหน้าสมัครสมาชิก

Dev ให้ AI generate migration:

```sql
ALTER TABLE customer ADD COLUMN customer_type VARCHAR(50);
```

แต่ในระบบเดิมมีอยู่แล้ว 3 field ที่หมายถึงสิ่งเดียวกัน:

```sql
customer.customer_category
customer.customer_segment
customer.customer_group
```

(ใช่ — มี 3 field สำหรับเรื่องเดียวกันอยู่แล้ว เพราะ migration ปี 2018, 2020, 2022 — และตอนนี้กำลังจะมีอันที่ 4)

**ปัญหา**

- ข้อมูลซ้ำความหมาย → report เพี้ยน
- ETL ต้อง map เพิ่ม
- API field ซ้ำ
- BA/SA ต้องมาตีความทีหลังว่าตัวไหนคือ "ตัวจริง"
- Hidden technical debt ที่ไม่ขึ้น dashboard

**วิธีแก้ — Schema MCP + Data Dictionary**

Workflow ใหม่:

```text
/from-ticket CUS-123
→ AI อ่าน ticket
→ AI query data dictionary (RAG)
→ AI query database schema (MCP)
→ AI พบ customer_category มีอยู่แล้ว + ใช้งานใน 4 service
→ AI ถามหรือเสนอ reuse field เดิม
→ SA approve การ reuse หรืออธิบายเหตุผลที่ต้อง add ใหม่
```

ตัวอย่าง instruction:

```md
# Database Change Rule

Before proposing a new column:
1. Search existing schema (use schema MCP).
2. Search data dictionary.
3. Check naming convention.
4. Explain why existing fields cannot be reused.
5. Generate migration only after impact analysis.
```

CI guardrail:

- Migration naming convention check
- Forbidden duplicate terms (`type` กับ `category` ใน table เดียว = warn)
- Manual approval เมื่อแก้ table ที่ flag เป็น critical
- Schema diff summary ใน PR

**บทเรียน**

AI ที่ "ไม่เห็น" schema จริงคือ AI ที่ออกแบบ schema ให้คุณซ้ำ — ทุกอาทิตย์ ทุกทีม ทุก feature

---

### Case 4: API แต่ละ service คนละ contract

**สถานการณ์**

องค์กรมีหลาย microservice — `customer-service`, `payment-service`, `policy-service`, `claim-service` — แต่ละทีมใช้ AI ช่วยสร้าง API เอง

ผลลัพธ์ใน 1 organization:

```json
// service A
{ "data": {...}, "error": null }

// service B
{ "result": {...}, "message": "success" }

// service C
{ "success": true, "payload": {...} }

// service D — invented entirely
{ "ok": 1, "obj": {...}, "err": "" }
```

**ปัญหา**

- Frontend handle response ยาก — ต้องเขียน adapter 4 แบบ
- API gateway ทำ standard response ไม่ได้
- Monitoring tag ไม่ตรงกัน — error rate ไม่อ่านง่าย
- Error code ไม่มาตรฐาน — frontend แสดง message ผิด context
- Mobile app ต้องเขียน mapper หลายชั้น

**วิธีแก้ — API Contract Standard + OpenAPI Template + Contract Test**

Standard:

```md
# API Response Standard

All APIs must use `ApiResponse<T>`.

Success:
{
  "status": "success",
  "data": {},
  "traceId": "..."
}

Error:
{
  "status": "error",
  "code": "CUSTOMER_NOT_FOUND",
  "message": "...",
  "traceId": "..."
}
```

Workflow:

```text
/scaffold-resource customer-profile
→ load API response standard
→ generate OpenAPI spec
→ generate controller / resource
→ generate service
→ generate DTO with validation
→ generate contract test
→ run linter on OpenAPI
```

Enforcement:

- OpenAPI lint (Spectral) ใน CI
- Contract test ที่ตรวจ response shape ทุก endpoint
- API review bot ที่ comment ถ้าผิด standard
- Consumer-driven contract testing (Pact) ระหว่าง frontend ↔ backend

**บทเรียน**

ถ้าไม่ตั้ง contract กลางตั้งแต่แรก แต่ละ service จะ invent คำว่า "success" ของตัวเอง — นี่คือเหตุผลที่ frontend หลายทีมต้องเขียน util ชื่อ `unwrapResponse()` ที่มี if-else 12 สาย

---

## กลุ่ม B — คุณภาพและความปลอดภัย

### Case 5: AI เขียน security bug ที่ดูเหมือนใช้งานได้

**สถานการณ์**

Dev สั่ง AI:

> เพิ่ม endpoint export customer list เป็น Excel

AI generate:

```java
String sql = "select * from customer where name like '%" + keyword + "%'";
```

หรือใน frontend:

```tsx
<div dangerouslySetInnerHTML={{ __html: remark }} />
```

หรือ:

```python
@app.get("/users/{user_id}")
def get_user(user_id: int):
    return db.query(User).filter(User.id == user_id).first()
```

(สังเกตเห็นไหมว่าไม่มี auth check ไม่มี permission check — แต่มันก็ "ทำงานได้")

**ปัญหา**

AI มักเขียน code ที่ "ดูใช้ได้" แต่ไม่ได้คิด threat model:

- SQL Injection
- XSS
- Broken access control / IDOR
- Secret leakage
- Missing audit log
- Missing rate limit
- Unbounded query (จะ OOM ตอน production)

OWASP Top 10 for LLM Applications เตือนชัดเรื่อง:
- **Insecure Output Handling** — output ของ LLM ไม่ควรถูก trust แบบ raw
- **Excessive Agency** — ให้ AI สิทธิ์ทำ action มากเกินไป
- **Overreliance** — เชื่อ AI โดยไม่ verify

**วิธีแก้ — Security Skill + SAST + Policy-as-Code**

Security instruction file:

```md
# Security Rules

- Never build SQL by string concatenation. Use repository/query builder only.
- Every export endpoint must check permission.
- Every sensitive action must write audit log with actor + resource + action.
- Never log PII, token, password, citizen ID, credit card.
- Validate all user input with schema (Zod / Joi / Pydantic).
- Set timeout and pagination on all queries.
- Use parameterized queries for all DB access.
```

Workflow:

```text
/security-audit PR-456
→ ตรวจ SQL injection pattern
→ ตรวจ auth/permission decorator
→ ตรวจ log statement ที่อาจมี PII
→ ตรวจ dependency risk
→ ตรวจตาม OWASP Top 10
→ สรุป risk เป็น High/Medium/Low พร้อมหลักฐาน
```

Enforcement (deterministic):

- SAST (Semgrep / SonarQube)
- Dependency scan (Snyk / OSV)
- Secret scan (gitleaks / trufflehog)
- Protected branch + required security approval สำหรับ critical module

**บทเรียน**

AI ตอบ "code ทำงานได้ไหม" ไม่ใช่ "code ปลอดภัยไหม" — ถ้าไม่มี security layer ที่ตีกลับอัตโนมัติ คุณกำลังให้ AI commit ช่องโหว่เข้า production ในนามของ productivity

---

### Case 6: QA ได้ test case เยอะขึ้น แต่ไม่ตรง business rule

**สถานการณ์**

QA ใช้ AI generate test case จาก requirement สั้น ๆ:

> ระบบต้องอนุมัติคำขอเมื่อข้อมูลครบ

AI generate:

- ✅ กรอกข้อมูลครบแล้ว submit สำเร็จ
- ✅ ไม่กรอกชื่อแล้ว error
- ✅ ไม่กรอก email แล้ว error

ดูดี แต่ขาด business rule จริงทั้งหมด:

- ลูกค้าบางประเภทต้องแนบเอกสารเพิ่ม
- ถ้าวงเงินเกิน X ต้อง approve 2 ชั้น
- ถ้าเคยผิดเงื่อนไข ต้องขึ้น notice
- ถ้าวันหยุดต้องเลื่อน SLA
- ถ้า user role ไม่ถูก ห้าม approve
- ถ้า amount ติดลบ → reject (เคยมีบั๊กนี้แล้วใน 2023)

**ปัญหา**

AI สร้าง test case แบบ generic เพราะมันไม่ได้เห็น:
- BRD ฉบับเต็ม
- Decision table / rule table
- Defect history ของ module นี้
- API spec
- Permission matrix

ผลคือ "test pass 100% แต่ regression bug หลุด" ซึ่งคือ false confidence ที่ราคาแพงกว่าไม่มี test ด้วยซ้ำ

**วิธีแก้ — QA Agent ที่อ่าน source หลายชั้น**

Workflow:

```text
/generate-test-matrix PAY-1234
→ อ่าน BRD จาก Wiki
→ อ่าน acceptance criteria จาก Jira
→ อ่าน defect history ของ module payment
→ อ่าน API spec
→ อ่าน permission matrix
→ สร้าง test case แบ่งหมวด:
   - positive (happy path)
   - negative (validation)
   - edge (boundary)
   - permission (role-based)
   - regression (จาก defect เก่า)
   - security (auth, injection, PII)
```

ตัวอย่าง output:

| Test Type | Case |
|---|---|
| Positive | user role cashier สร้าง payment ได้ |
| Negative | amount ติดลบ → reject |
| Edge | amount เกิน limit → require approval |
| Permission | user role viewer → ห้าม submit |
| Regression | payment status เดิมต้องไม่เปลี่ยนผิด flow (ref: BUG-2023-456) |
| Security | export ต้อง mask PII (citizen ID, card number) |

**บทเรียน**

QA ไม่ควรเอา AI-generated test case ไปใช้ทันที แต่ใช้เป็น **draft** แล้ว validate business rule อีกที — AI ช่วยลดเวลาเขียน 60% แต่ไม่ลดความรับผิดชอบ 0%

---

## กลุ่ม C — Process roles

### Case 7: PM ได้ status จาก AI แต่เสี่ยงเชื่อ summary ผิด

**สถานการณ์**

PM ใช้ AI สรุป Jira/Redmine:

> สรุป sprint นี้ให้หน่อยว่าเสร็จกี่งาน มี blocker อะไร

AI ตอบ:

```text
Sprint progress: 80%
No major blockers.
```

แต่จริง ๆ:
- Ticket "Done" 3 ใบ PR ยังไม่ merge
- 1 ใบ status In Progress แต่มี comment ล่าสุดเมื่อวานว่า "Blocked by API spec not confirmed"
- 2 ใบ QA ยังไม่ sign-off
- 1 ใบ release branch ยังไม่ cherry-pick

**ปัญหา**

AI summarize จาก status field อย่างเดียว = สรุปผิด เพราะ status ใน Jira กับ "ทำเสร็จจริง" คือคนละเรื่อง — ทุก PM ที่เคยทำ sprint review รู้ดี

**วิธีแก้ — PM Agent ที่ใช้ source หลายชั้น**

ตรวจ:
- Jira/Redmine status
- PR status (open / merged / draft)
- CI status (pass / fail)
- QA status (label / comment)
- Blocked label
- Comment ล่าสุด (มีคำว่า "blocked", "wait", "depend" ไหม)
- Dependency ticket
- Release branch

Definition of Done ที่ AI ใช้ตรวจ:

```md
A task is not truly done unless:
- ticket status = Done
- PR merged
- CI passed
- QA accepted
- no unresolved blocker
- release note updated if user-facing
```

Use case จริง:

```text
/sprint-risk current
```

Output:

| Risk | Evidence | Action |
|---|---|---|
| Payment API delay | PAY-123 มี blocker comment เมื่อวาน | Escalate to SA |
| QA bottleneck | 8 tickets in Ready for QA, มี QA assigned 1 คน | Rebalance scope |
| Hidden work | 4 PRs open ไม่มี linked ticket | ขอให้ dev link work item |
| Scope creep | 6 ticket ใหม่เพิ่มกลาง sprint | คุยกับ PO |

**บทเรียน**

AI summary ที่ดี ≠ AI ที่อ่าน field สุดท้ายแล้วเดา — แต่คือ AI ที่ตรวจหลาย source แล้วแยก signal ออกจาก noise

---

### Case 8: BA ใช้ AI เขียน BRD แล้วดูดีแต่ยังไม่ครบ

**สถานการณ์**

BA ให้ AI แปลง meeting transcript เป็น BRD ได้ output ที่ดูสวย:

- Overview
- User story
- Acceptance criteria
- Flow
- Validation

แต่ขาด section ที่ทำให้ requirement ใช้งานได้จริง:

- Exception case
- Data mapping
- Permission matrix
- Report impact
- Migration rule
- Backward compatibility
- Open questions

**ปัญหา**

AI เขียนตาม pattern ที่เห็นบ่อยใน training data ซึ่งมักจะเป็น BRD แบบ academic ไม่ใช่ enterprise — ส่วนที่ทำให้ dev ไม่ต้องถามซ้ำตอน sprint planning จึงหายไปหมด

**วิธีแก้ — BA Agent มี checklist บังคับ**

Master checklist:

```md
# BA Requirement Checklist

Every feature spec must include:
- Business objective
- In-scope / out-of-scope (ระบุชัด ไม่งั้นจะเถียงกันยาว)
- User roles
- Main flow
- Alternative flow
- Exception flow
- Validation rules
- Data mapping (field-level)
- Permission matrix (role × action)
- Audit requirement
- Report impact
- API impact
- Open questions
- Acceptance criteria (Given-When-Then)
```

Use case:

```text
/brd-review BRD-2026-001
```

Output:

```text
Missing:
- Permission matrix
- Data retention rule
- Error message mapping
- Report impact section
- Migration strategy

Potential conflict:
- Section 3 บอก branch manager approve ได้
- Section 5 บอก only regional manager approve ได้
→ ต้อง clarify ก่อน dev เริ่ม
```

**บทเรียน**

BA agent ที่มีคุณค่าไม่ใช่ "เขียนเอกสารเร็วขึ้น" แต่ "ลด requirement hole" — ลดจำนวน clarification meeting ใน sprint ลง 30-40% นี่คือมูลค่าจริง

---

### Case 9: SA ทำ Impact Analysis บน Legacy ที่ไม่มีใครอยากแตะ

**สถานการณ์**

ลูกค้าขอแก้ rule:

> ถ้า policy type เป็น X ให้เปลี่ยนวิธีคำนวณ premium

ระบบเก่า:
- Code กระจายหลาย repo
- Wiki ไม่ update มา 2 ปี
- DB table 200+ ตาราง
- Batch job กลางคืน 7 ตัว
- Report ใช้ field เดียวกันใน 4 dashboard
- Integration กับ AS400 ผ่าน MQ

**ปัญหา**

ถ้าให้ AI generate code เลย = อันตรายมาก เพราะ AI ไม่เห็น impact

ถ้าให้ SA หาเองด้วย grep + Confluence search = 3 วันยังไม่ครบ

**วิธีแก้ — SA Impact Agent**

```text
/impact-analysis "change premium calculation for policy type X"
```

AI ค้นจาก:
- Code reference ของ field `policy_type`
- API ที่ return premium
- DB table ที่เกี่ยวข้อง
- Batch job (cron + script)
- Report SQL
- Test case เดิม
- Incident ที่เคยเกี่ยวข้อง
- ADR เก่า

Output:

```md
## Impact Summary

Affected services:
- policy-service (3 endpoints)
- quotation-service (premium calc + validation)
- billing-service (invoice generation)

Affected tables:
- policy
- premium_calculation
- quotation_result

Affected APIs:
- POST /quotation/calculate
- GET /policy/{id}/premium

Potential risks:
- Existing report "Monthly Premium Summary" uses old premium field
- Batch job `premium-reconcile-job` recalculates every night
- Mobile app caches premium result for 24 hours

Recommendation:
- Add feature flag (e.g. `new_premium_calc_v2`)
- Add regression test for policy type X/Y/Z
- Confirm report mapping with BA
- Update API contract before implementation
- Coordinate mobile app cache invalidation
```

**บทเรียน**

SA ยังต้องตัดสินใจเอง — แต่ AI ลดเวลาหา context จาก 3 วันเหลือ 30 นาที และจับ impact ที่ SA อาจมองข้าม (เช่น batch job ที่ไม่ได้แตะมา 5 ปี) ได้ดีกว่า

---

## กลุ่ม D — Production

### Case 10: Production Incident — AI ช่วย Triage ได้ แต่ห้ามให้แก้เองหมด

**สถานการณ์**

Production มี error 500 spike:

```text
NullPointerException at PaymentService.confirm()
```

ทีมเปิด Incident Agent ให้อ่าน:
- Log ของ pod
- Distributed trace
- Recent deploy (3 วันล่าสุด)
- PR ที่เพิ่ง merge
- Ticket ที่เกี่ยวข้อง
- Dashboard metric

**AI ช่วยอะไรได้**

- สรุป timeline ของ incident
- หา PR ที่น่าจะเกี่ยวข้อง (เทียบ commit ↔ first error timestamp)
- เทียบ error pattern ก่อน/หลัง deploy
- Suggest rollback หรือ hotfix
- Generate incident report draft (สำหรับ post-mortem)

**AI ไม่ควรทำอะไรเอง**

- Rollback production โดยไม่มี approval
- Rotate secret โดยไม่มี change process
- Update database เอง
- Send customer communication เอง

นี่คือ **Excessive Agency** ตาม OWASP LLM Top 10 — การให้ AI มีอำนาจทำ action ที่ irreversible โดยไม่มี human in the loop

**Permission Matrix**

| Action | AI Permission |
|---|---|
| อ่าน log | Allowed |
| สรุป incident | Allowed |
| Suggest rollback | Allowed |
| Run rollback | Human approval required |
| Update DB | Forbidden by default |
| Send external email | Human approval required |
| Restart pod | Allowed (allowlisted command, audit logged) |
| Rotate secret | Forbidden |

**บทเรียน**

ใน production AI คือ "ผู้ช่วยที่ฉลาด ไม่ใช่ผู้ตัดสินใจ" — สิ่งที่ AI ทำกลับไม่ได้ ไม่ควรอยู่ใน scope ของ AI

---

## ภาพรวม 10 Cases

ลองมองทั้ง 10 case พร้อมกัน คุณจะเห็น pattern เดียวกันซ่อนอยู่:

1. **AI ไม่เห็น context จริง** (1, 2, 3, 4, 6, 7, 9) → แก้ด้วย MCP + RAG + Handbook
2. **AI ไม่มีกฎมาตรฐาน** (1, 2, 4, 5, 8) → แก้ด้วย Handbook + Skill
3. **AI ไม่มี enforcement** (1, 4, 5) → แก้ด้วย CI + linter + SAST + contract test
4. **AI มีสิทธิ์เกินจำเป็น** (10) → แก้ด้วย Permission model + Human in the loop
5. **คนเชื่อ AI เกินไป** (6, 7, 8) → แก้ด้วย explicit checklist + audit trail

5 ปัญหานี้คือเสาหลักของซีรีส์ที่จะอธิบายต่อใน Part 3 (เมื่อแต่ละ role เจอปัญหานี้จริง ๆ ในงานประจำวัน) และ Part 4 (architecture ของ platform ที่แก้ปัญหาเหล่านี้พร้อมกัน)

---

## สรุป Part 2

10 cases บอกอะไรเรา:

1. **Code drift** เกิดเร็วถ้าไม่มี handbook กลาง (Case 1)
2. **Design drift** เกิดเพราะ AI ไม่เห็น component catalog (Case 2)
3. **Data drift** เกิดเพราะ AI ไม่เห็น schema (Case 3)
4. **Contract drift** เกิดเพราะแต่ละ service invent format เอง (Case 4)
5. **Security bug** มาในรูป "code ที่ทำงานได้" (Case 5)
6. **Test ที่ดูดี** อาจไม่ครอบ business rule (Case 6)
7. **PM summary** ผิดถ้าใช้ source เดียว (Case 7)
8. **BRD** ที่ "สวย" อาจไม่มี exception case (Case 8)
9. **Impact analysis** เป็นที่ที่ AI สร้าง value ได้ชัดที่สุด (Case 9)
10. **AI ใน incident** ช่วยได้ แต่ต้องมี boundary (Case 10)

ในตอนต่อไป (Part 3) เราจะลงไปดู **role-by-role playbook** — แต่ละ role (PM, BA, SA, UX, Dev, QA, DevOps) เจอ pain point อะไร, ใช้ AI ยังไงให้แก้จริง, และวัดผลด้วย metric ไหน
