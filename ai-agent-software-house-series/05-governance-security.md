# Part 5 — Governance, Security & Anti-Patterns

> ตอนที่ 4 เราวาง architecture จบ — ดูจะดี ดูจะเรียบร้อย แต่ที่บริษัทต่าง ๆ ตายเพราะ AI ไม่ใช่เพราะ architecture ห่วย แต่เพราะ **governance ห่วย** ระบบที่ดีไม่มี governance = ระบบที่ดีในวันแรกและแย่ในเดือนที่ 6

ตอนนี้คุยเรื่อง:
1. AI Risk Model — เสี่ยงตรงไหน
2. Policy ที่ควรมีก่อนเปิดใช้
3. Permission Model
4. Metrics ที่จะรู้ว่าได้ผลจริง
5. Dashboard ที่ควรเห็นทุกสัปดาห์
6. 5 Anti-Patterns ที่ทุกองค์กรเจอ พร้อมวิธีหลีกเลี่ยง

---

## 1. AI Risk Model

### 1.1 Risk ที่ต้องระวัง 8 ข้อ

| Risk | ตัวอย่างจริง | กลุ่ม |
|---|---|---|
| Data leakage | Dev paste customer data เข้า public ChatGPT | Confidentiality |
| Prompt injection | Ticket comment มีข้อความหลอก agent ให้ทำ action | Integrity |
| Excessive agency | AI มีสิทธิ์ deploy / delete เอง | Availability + Integrity |
| Insecure output | AI generate SQL injection / XSS | Integrity |
| Overreliance | เชื่อ AI โดยไม่ review (เห็นบ่อยใน QA test draft) | Quality |
| Supply chain | AI แนะนำ library ที่มี CVE หรือถูกถอด | Supply chain |
| Secret exposure | AI log token / password / API key | Confidentiality |
| Permission bypass | AI สร้าง endpoint ที่ลืม auth | Authorization |

อ้างอิงโครงจาก OWASP Top 10 for LLM Applications (2025) — ผมแนะนำให้ทุก security team อ่านเอกสารนี้อย่างน้อยปีละครั้ง

### 1.2 Risk Mapping ตามแหล่งกำเนิด

| ที่มาของ Risk | Risk |
|---|---|
| User behavior | Data leakage, Overreliance |
| AI output | Insecure output, Supply chain |
| Untrusted content | Prompt injection (ผ่าน ticket, wiki, comment) |
| MCP / Tool access | Excessive agency, Secret exposure, Permission bypass |

### 1.3 Risk Severity Matrix

ไม่ทุก risk ราคาเท่ากัน แบ่งเป็น 4 tier:

| Tier | ตัวอย่าง | Action |
|---|---|---|
| Critical | Production write โดย AI ไม่มี approval, secret leak ออก public | ห้ามจาก policy + technical block |
| High | SQL injection, missing auth | CI block + security review required |
| Medium | Supply chain ที่มี CVE medium, missing audit log | CI warning + auto-create ticket |
| Low | Style drift, comment quality | Advisory only |

---

## 2. AI Usage Policy

### 2.1 Policy ที่ต้องประกาศชัด

```md
# AI Usage Policy v1.0

## Data Handling
- ห้ามส่ง production data เข้า public AI service
- ห้ามส่ง secret, token, password, API key, citizen ID, credit card
- ห้ามส่ง customer PII เข้า AI ที่ไม่ได้ผ่าน DPA review
- AI tool ต้องใช้ enterprise account ของบริษัท (ไม่ใช่ personal)

## Code Generation
- AI-generated code ต้องผ่าน code review ก่อน merge — ทุกครั้ง
- Commit message ต้องระบุว่าใช้ AI ช่วย (เช่น `[ai-assisted]`)
- AI-generated code ที่กระทบ critical module ต้องมี security review

## AI Action Permission
- AI ห้ามทำ production write action โดยไม่มี human approval
- AI ห้าม run irreversible command (rm -rf, drop table, rotate prod secret)
- MCP write action ต้องถูก audit log ทุกครั้ง

## Quality
- AI test case ต้องผ่าน QA validate ก่อนเข้า test plan
- AI summary (status, report) ต้องระบุ confidence + source
- AI recommendation ใน production incident ต้อง human-in-the-loop เสมอ
```

### 2.2 ใครต้องเซ็น

Policy ต้องผ่าน:
- CTO / Engineering Director
- CISO / Security Lead
- Legal / DPO (สำหรับ data privacy)
- HR (สำหรับ employee training requirement)

ทำเป็น living document — review ทุก quarter

### 2.3 Training ที่ต้องคู่กับ policy

ห้ามมี policy แต่ไม่มี training — engineer จะอ่านครั้งเดียวแล้วลืม

แนะนำ:
- Onboarding training (mandatory) — 1 ชั่วโมง
- Quarterly refresher — 30 นาที
- Incident-driven update — เมื่อมีเคสใหม่ที่ต้องแชร์

---

## 3. Permission Model — ขยายลึก

### 3.1 หลักการ 3 ข้อ

1. **Least privilege** — เริ่มจากสิทธิ์ต่ำสุดที่ทำงานได้
2. **Default deny** — ไม่ระบุชัด = ห้าม
3. **Audit everything** — ทุก action ที่ AI ทำต้อง log

### 3.2 Permission Matrix ตาม Role และ Action

| Role | Read | Draft | Write (approval) | Production |
|---|---|---|---|---|
| PM Agent | Jira, Wiki | Report, summary | Update ticket label | ❌ |
| BA Agent | Jira, Wiki, BRD | BRD draft, story | Publish to wiki | ❌ |
| SA Agent | Code, Wiki, ADR | ADR draft, design doc | Publish ADR | ❌ |
| Dev Agent | Code, Schema, API catalog | Code change (PR) | ❌ direct prod | ❌ |
| QA Agent | Test repo, BRD, defect | Test case draft | Publish test plan | ❌ |
| Ops Agent | Log, Metric, Config | Runbook draft | Restart pod (allowlisted) | ❌ rotate secret |
| Reviewer Agent | Code, PR diff | Review comment | ❌ approve/merge | ❌ |

หลักสำคัญ:
- **Production action** = ❌ ทุก role เป็น default
- ถ้าจะเปิด production action — ต้องมี:
  - Explicit policy approval
  - Audit log ที่ tamper-proof
  - Human-in-the-loop (อย่างน้อย 1 คน approve)
  - Rollback path ที่ชัด

### 3.3 ตัวอย่าง Audit Log Schema

```json
{
  "timestamp": "2026-05-09T14:32:11Z",
  "actor": "ai-agent:claude-code",
  "user": "shode666@example.com",
  "skill": "/scaffold-resource",
  "tool_calls": [
    { "tool": "jira_mcp.get_issue", "args": { "id": "PAY-123" } },
    { "tool": "schema_mcp.search", "args": { "query": "payment_callback" } },
    { "tool": "file_write", "args": { "path": "src/.../PaymentCallbackResource.java" } }
  ],
  "duration_ms": 4231,
  "result": "success",
  "files_changed": 8,
  "permission_check": "passed",
  "trace_id": "abc-123-..."
}
```

Audit log นี้ใช้ตอบคำถามได้ว่า:
- AI access อะไรเมื่อไร
- Skill ไหน trigger บ่อย
- Skill ไหน fail บ่อย
- มี skill ที่ทำเกินสิทธิ์ไหม
- มี user ที่ใช้แบบ pattern ผิดปกติไหม

---

## 4. Metrics ที่ต้องมี

### 4.1 Productivity Metrics

| Metric | วัดอะไร | เป้าหมาย 6 เดือน |
|---|---|---|
| Code review time | PR open → merge | -30 ถึง -40% |
| First-pass PR rate | PR ที่ผ่าน review รอบเดียว | +30 ถึง +50% |
| Boilerplate time | เวลาเขียน scaffold ก่อน logic | -50 ถึง -70% |
| Onboarding time | dev ใหม่เริ่ม contribute ได้ | เร็วขึ้น 2-3x |
| Time-to-feature | ticket → production | -20 ถึง -30% |

### 4.2 Quality Metrics

| Metric | วัดอะไร | เป้าหมาย 6 เดือน |
|---|---|---|
| Defect leakage | bug หลุด production / 1,000 LOC | ลดลง |
| Standard drift | repo ที่ใช้ rule version เก่า > 3 minor | ลดลง 80-90% |
| Review comment type | % ของ comment ที่เป็น style vs logic | style ลดลง |
| Test coverage | line + branch coverage | คงที่หรือเพิ่ม |
| Mutation score | quality ของ test (ถ้ามี mutation testing) | เพิ่มขึ้น |

### 4.3 Security Metrics

| Metric | วัดอะไร | เป้าหมาย |
|---|---|---|
| Critical/High SAST in AI-PR | จำนวน finding ใน PR ที่ใช้ AI | ใกล้ 0 |
| Secret leak attempts | Pre-commit catch | จับได้ 100% ก่อน commit |
| Permission bypass attempts | Endpoint ที่ลืม auth | 0 |
| Mean time to security fix | จาก finding → patch | ลดลง |

### 4.4 AI Usage Metrics

| Metric | วัดอะไร | ใช้ทำอะไร |
|---|---|---|
| Skill usage | ใคร ใช้ skill ไหน เท่าไร | identify popular skill |
| Skill success rate | % ของ skill call ที่สำเร็จ | identify broken skill |
| Suggestion acceptance rate | % AI suggestion ที่ accept | trust signal |
| Top failed prompts | Prompt ที่ผิดบ่อย | improve handbook |
| Token cost per role | ค่าใช้จ่ายต่อ role | cost optimization |

---

## 5. Dashboard ที่ควรมีทุกสัปดาห์

ขยายจากเอกสารเดิมที่บอกแค่หัวข้อ — ลงรายละเอียดว่าแต่ละหน้าจอควรเห็นอะไร

### 5.1 Dashboard 1 — AI Engineering Health

**Audience:** CTO, Engineering Director

**Widgets:**

```text
┌─────────────────────────────────────┐
│ AI-Assisted PR This Week            │
│   324 PRs (↑ 18% vs last week)      │
│   First-pass rate: 67% (↑ 4pp)      │
└─────────────────────────────────────┘
┌─────────────────────────────────────┐
│ Review Time Distribution            │
│   Median: 3.2h    P90: 18h          │
│   Goal: <4h median                  │
└─────────────────────────────────────┘
┌─────────────────────────────────────┐
│ Top 5 Common AI Mistakes            │
│ 1. Used axios directly (28)         │
│ 2. Missing audit log (19)           │
│ 3. Hardcoded color (15)             │
│ 4. Test with no business assertion  │
│ 5. Catch + log silently             │
└─────────────────────────────────────┘
┌─────────────────────────────────────┐
│ Standard Drift                      │
│ 4/52 repos using rule v1.2 (deprec.)│
│ → auto-PR created by Renovate       │
└─────────────────────────────────────┘
```

### 5.2 Dashboard 2 — Security Posture

**Audience:** CISO, Security Lead

**Widgets:**

```text
┌─────────────────────────────────────┐
│ AI-PR Security Findings (7 days)    │
│   Critical: 0  High: 2  Med: 14     │
│   Resolved: 14   In progress: 2     │
└─────────────────────────────────────┘
┌─────────────────────────────────────┐
│ Secret Leak Attempts                │
│   Caught at pre-commit: 8           │
│   Caught at CI:         0           │
│   Reached production:   0           │
└─────────────────────────────────────┘
┌─────────────────────────────────────┐
│ Permission Bypass Attempts          │
│   AI generated unauth endpoint: 1   │
│   → Caught by ArchUnit              │
└─────────────────────────────────────┘
┌─────────────────────────────────────┐
│ MCP Audit                           │
│   write actions: 23                 │
│   approval bypass: 0                │
│   suspicious patterns: 0            │
└─────────────────────────────────────┘
```

### 5.3 Dashboard 3 — Skill / Workflow Usage

**Audience:** Platform Team, Engineering Manager

**Widgets:**

```text
┌─────────────────────────────────────┐
│ Top 10 Skills by Usage              │
│ 1. /from-ticket          412        │
│ 2. /scaffold-resource    287        │
│ 3. /review-before-pr     264        │
│ 4. /generate-test-matrix 180        │
│ ...                                 │
└─────────────────────────────────────┘
┌─────────────────────────────────────┐
│ Skill Success Rate                  │
│ /from-ticket          94% ✓        │
│ /scaffold-resource    91% ✓        │
│ /security-audit       88% (low)     │
│ /impact-analysis      72% ⚠         │
└─────────────────────────────────────┘
┌─────────────────────────────────────┐
│ Funnel: Skill → PR → Merge          │
│ Skill called:    1,420              │
│ PR opened:       1,034 (73%)        │
│ Merged:            927 (90%)        │
│ → Health good                       │
└─────────────────────────────────────┘
```

### 5.4 Dashboard 4 — Cost & ROI

**Audience:** Finance, CFO, CTO

**Widgets:**

```text
┌─────────────────────────────────────┐
│ Monthly AI Cost                     │
│   Token cost:     $14,200           │
│   Seat license:   $9,800            │
│   MCP infra:      $2,100            │
│   Total:         $26,100            │
└─────────────────────────────────────┘
┌─────────────────────────────────────┐
│ Estimated Productivity Saved        │
│ Review time saved:    412 hrs       │
│ Boilerplate saved:    280 hrs       │
│ Test draft saved:     156 hrs       │
│ ≈ Equivalent FTE:     5.3           │
└─────────────────────────────────────┘
```

(ระวังตัวเลข ROI มันโกหกง่ายที่สุดในรายงานองค์กร — ใช้เป็น indicator ไม่ใช่ truth)

---

## 6. 5 Anti-Patterns ที่ทุกองค์กรเจอ

ขยายจากเอกสารเดิม — แต่ละข้อมาพร้อม "ทำไมถึงเกิด", "อาการ", "วิธีกัน"

### Anti-Pattern 1: ซื้อ AI tool แล้วปล่อยทุกคนใช้เอง

**ทำไมถึงเกิด:** เพราะ "AI ไม่ใช่ของยาก ใคร ๆ ก็ใช้ได้" เป็น narrative ที่ขายดี ฝ่ายจัดซื้อก็ซื้อง่าย

**อาการ:**
- Code คนละทรงในทีมเดียว
- Data leakage (dev paste customer record เข้า public AI)
- Review ช้าลง ไม่ใช่เร็วขึ้น
- ไม่มี shared learning — ทุกคนเรียนเองจากศูนย์
- ไม่มี skill หรือ workflow มาตรฐาน
- เซ็นใช้ tool 3 ตัวที่ทำงานเหมือนกัน

**วิธีกัน:**
- ก่อนซื้อ seat ใด ๆ ต้องวาง pillar 1-3 ก่อน (Knowledge, Capability, Generation)
- ทำ pilot กับทีมเล็ก 1-2 ทีมก่อน — วัดผลก่อน scale
- มี enterprise account + audit ตั้งแต่วันแรก
- Onboarding training mandatory

**บทเรียน:** การซื้อ tool คือ 10% ของงาน — 90% คือการสร้างระบบรอบตัว tool

---

### Anti-Pattern 2: ใช้ MCP แบบให้สิทธิ์กว้างเกิน

**ทำไมถึงเกิด:** ตอน setup MCP ขี้เกียจ click permission ทีละจุด เลือก "all access" ไป

**อาการ:**
- AI อ่านข้อมูลเกินจำเป็น (เช่น ทุก Jira project ของบริษัท)
- AI เผลอ write action ที่ไม่ควร (move ticket, edit BRD ผิด)
- Prompt injection เสี่ยงขึ้น — ตัว AI กลายเป็น confused deputy
- ไม่มี audit ว่า AI ทำอะไรไป
- Compliance review ไม่ผ่านตอน audit

**วิธีกัน:**
- Default deny — เริ่มจากสิทธิ์ต่ำสุด
- Read-only ก่อน — write action เปิดทีละจุด มี approval flow
- Scope MCP ตาม project / repo / domain
- Audit log ทุก action
- Rotate credential ตามรอบ

**บทเรียน:** AI ที่มี root access = AI ที่จะทำ root-level mistake ในวันที่คุณนอนหลับ

---

### Anti-Pattern 3: เชื่อ AI Review แทน CI

**ทำไมถึงเกิด:** AI review เร็วและ "ฉลาด" ทีมเลยใช้แทน linter/test/SAST

**อาการ:**
- Review ไม่ deterministic — ครั้งนี้ผ่าน อีกครั้งไม่ผ่าน
- Bug หลุดเพราะ AI "เห็นด้วย" กับ code ผิด
- ทีมเริ่มเสีย trust ใน CI ("AI review ก็ผ่านแล้วนี่")
- Security issue เจอช้าลง

**วิธีกัน:**
- AI review = **advisory** เท่านั้น
- ใช้ deterministic gate (linter, unit test, SAST, ArchUnit) เป็นชั้นล่างสุดที่บอก pass/fail
- AI review เพิ่ม signal — ไม่แทน gate
- ถ้า AI review บอกว่ามี issue ที่ deterministic gate ไม่จับ — เพิ่ม rule ให้ deterministic gate

**บทเรียน:** ตัวที่ตีกลับ block merge ต้องบอกเหตุผลซ้ำ ๆ ได้เหมือนเดิม — AI ไม่ใช่ตัวนั้น

---

### Anti-Pattern 4: Copy Instruction File ทุก Repo ด้วยมือ

**ทำไมถึงเกิด:** "เขียน CLAUDE.md ครั้งเดียวแล้ว copy ไปทุก repo เลย ง่ายกว่าทำ package"

**อาการ:**
- 6 เดือนผ่านไป repo มี handbook 50 เวอร์ชันต่างกัน
- Rule ใหม่ที่เขียนใน Q2 ยังไม่ไปถึงครึ่งของ repo
- ไม่มี source of truth ว่ารุ่นไหน "ถูก"
- Maintenance nightmare — เพิ่ม rule ใหม่ = PR 80 อัน

**วิธีกัน:**
- Single source — central rule package (`@company/ai-rules`)
- Generate instruction file ใน CI จาก rule package + service.yaml
- Renovate auto-update version
- CI drift check — fail ถ้ามีคนแก้ generated file ด้วยมือ
- Rule deprecation policy ที่ชัด (แจ้ง 3 เดือนก่อน remove)

**บทเรียน:** ถ้าระบบของคุณต้องการมนุษย์ copy-paste เพื่อ sync state ระบบนั้นจะเสียอย่างเงียบ ๆ และคุณจะรู้ตอนที่มันสายแล้ว

---

### Anti-Pattern 5: ทำ Platform ใหญ่ตั้งแต่วันแรก

**ทำไมถึงเกิด:** Platform team อ่านบทความ (เช่นบทความนี้) แล้วอยากสร้างทุก pillar พร้อมกัน

**อาการ:**
- 6 เดือนยังไม่มี value ออกมา
- Platform team burn out — ของยังไม่เสร็จ user ก็ยังไม่มี
- Engineering team กลับไปใช้ prompt ส่วนตัวเพราะ platform ยังไม่พร้อม
- ตอน platform เสร็จ ไม่มีคนอยากใช้แล้ว (เพราะคนชินกับวิธีของตัวเอง)
- CFO เริ่มถามคำถามไม่สบายใจ

**วิธีกัน:**

ใช้แนวทาง crawl → walk → run

**Crawl (week 1-4):** ทำ 1 pillar ที่กระทบกว้าง

- เขียน handbook v0 (Knowledge pillar)
- กำหนด API standard, security checklist
- เผยแพร่เป็นไฟล์ markdown ใน wiki + repo template

**Walk (week 5-12):** ทำ 2 skill ที่ value สูง + enforcement

- 1 skill — `/from-ticket` หรือ `/scaffold-resource`
- 1 skill — `/review-before-pr`
- เพิ่ม linter + test gate ใน CI
- รัน pilot กับ 1-2 team

**Run (month 4-12):** ขยาย pillar ที่เหลือ

- MCP layer
- Plugin distribution
- Multi-repo strategy
- Governance dashboard

**บทเรียน:** Platform ที่ดีคือ platform ที่ user **ใช้** — ไม่ใช่ platform ที่สมบูรณ์ในเอกสาร

---

## 7. Governance Cadence

ระบบที่ดีต้องมี cadence ของการ review และปรับ

### 7.1 Weekly

- Dashboard review — engineering manager + platform team
- Skill failure investigation
- Security finding review

### 7.2 Monthly

- Standard drift report
- Top common AI mistakes → handbook update
- Cost review
- New skill proposal review

### 7.3 Quarterly

- Policy review — legal, security, CTO
- Permission model review
- ROI report ต่อ leadership
- Tool / vendor review (เพิ่ม/ลด/เปลี่ยน vendor)
- Roadmap update

### 7.4 Yearly

- Full architecture review
- Compliance audit
- Vendor security review
- Handbook major version

---

## 8. Crisis Playbook — เมื่อเกิดเหตุ

ระบบที่ดีต้องเตรียม "วันที่พัง" ไว้ด้วย

### 8.1 AI Generated Critical Bug

1. Identify scope (กี่ PR, กี่ commit)
2. Block merge ของ AI-PR ชั่วคราว
3. Run focused regression
4. Hot-fix หรือ rollback
5. Root cause: rule ไม่ครอบ? skill broken? handbook outdated?
6. Update handbook + skill
7. Communicate

### 8.2 Data Leak via AI

1. Immediate revoke AI tool access
2. Identify data scope (ใคร paste อะไร เมื่อไร)
3. Notify legal / DPO
4. Notify affected party (ถ้าเข้า PDPA / GDPR)
5. Forensics — รวบรวม evidence
6. Update policy + training
7. Quarterly retrospective

### 8.3 Excessive Agency Incident

1. Disable problematic skill ทันที
2. Audit log review — เกิดอะไรไปแล้ว
3. Rollback ที่ทำได้
4. Update permission model
5. Update skill guardrail
6. Test before re-enable

---

## สรุป Part 5

Governance + Security ไม่ใช่ "เรื่องน่าเบื่อที่ทำท้ายโครงการ" — มันคือเสาที่ค้ำให้ architecture จาก Part 4 ใช้ได้นาน

ใจความหลัก:

1. **Risk model** — รู้ว่าเสี่ยงตรงไหน 8 ข้อ (data leak, prompt injection, excessive agency, ...)
2. **Policy** — ประกาศชัด + training + sign-off จาก CTO/CISO/Legal
3. **Permission** — least privilege, default deny, audit everything
4. **Metrics** — productivity + quality + security + usage 4 หมวด
5. **Dashboard** — engineering health, security posture, skill usage, cost ROI
6. **Anti-patterns** — 5 ข้อที่ทุกองค์กรเจอ พร้อมวิธีกัน
7. **Cadence** — weekly / monthly / quarterly / yearly
8. **Crisis playbook** — เตรียมวันที่พังไว้ก่อน

ถ้าทำ pillar 1-5 ดีแต่ pillar 6 (Governance) อ่อน — ระบบจะ degrade แบบเงียบ ๆ ภายใน 6-12 เดือน คุณจะตื่นมาเจอว่า rule version เก่า, drift กระจาย, dashboard ไม่มีคนเปิด, skill broken แต่ไม่มีคนซ่อม — และไม่มีใครรู้ว่ามันเริ่มแย่ตั้งแต่เมื่อไร

ใน Part 6 (ตอนสุดท้าย) เราจะลงมือ — Roadmap 12 สัปดาห์ ที่ขยาย crawl/walk/run จากตอนนี้, Implementation Examples (Java Dropwizard + React), Expected ROI, และคำถามท้าทาย "ถ้าจะเริ่มพรุ่งนี้ ทำอะไรก่อน"
