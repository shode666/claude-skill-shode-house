# Part 4 — Architecture ของ AI Agent Platform: 6 Pillars + Building Blocks

> ตอนที่ 1-3 เราคุย "ทำไม", "ปัญหาอะไร", "ใครเจอเรื่องอะไร" จบแล้ว ตอนนี้เปลี่ยนหมวก — มาดูว่า **ระบบ** ที่จะแก้ปัญหาทั้งหมดในตอนเดียวมีโครงหน้าตายังไง

ตอนนี้คือตอนที่ยาวที่สุดของซีรีส์ เพราะ architecture จริง ๆ มีหลายชั้นที่ต้องวางพร้อมกัน — handbook, MCP, skill, plugin, enforcement, multi-repo — ถ้าวางขาดชั้นใดชั้นหนึ่ง ผลลัพธ์ทั้งระบบจะอ่อนแอลงทันที (เหมือน CI ที่ไม่มี linter ตัวจริง — ทำได้แต่ไม่มีค่า)

---

## 1. ภาพรวม Architecture

```text
                          User / Role
                              │
                              ▼
                ┌────────────────────────────┐
                │  AI Client (IDE / Chat /   │
                │  Plugin / CI Bot)          │
                └────────────────────────────┘
                              │
                              ▼
                ┌────────────────────────────┐
                │  Skill / Agent Workflow    │
                │  (slash commands)          │
                └────────────────────────────┘
                              │
              ┌───────────────┼───────────────┐
              ▼               ▼               ▼
    ┌──────────────┐ ┌──────────────┐ ┌──────────────┐
    │   Context    │ │  Generation  │ │  Enforcement │
    │    Layer     │ │    Layer     │ │    Layer     │
    └──────┬───────┘ └──────┬───────┘ └──────┬───────┘
           │                │                │
           ▼                ▼                ▼
  ┌─────────────────┐ ┌──────────────┐ ┌──────────────┐
  │ Handbook        │ │ Templates    │ │ Linter       │
  │ Jira/Redmine    │ │ Internal SDK │ │ Unit test    │
  │ Wiki/Confluence │ │ Scaffolds    │ │ Contract     │
  │ Git             │ │ Test gen     │ │ test         │
  │ DB schema       │ │              │ │ SAST         │
  │ API catalog     │ │              │ │ Dep scan     │
  │ Component       │ │              │ │ ArchUnit     │
  │ catalog         │ │              │ │ CI gate      │
  │ Observability   │ │              │ │ Human review │
  └─────────────────┘ └──────────────┘ └──────────────┘
                              │
                              ▼
                ┌────────────────────────────┐
                │   Governance Layer         │
                │   (metrics, telemetry,     │
                │    dashboard, audit)       │
                └────────────────────────────┘
```

อ่านจากบนลงล่าง:

1. **User** ทำงานผ่าน **AI Client** (IDE, chat, plugin, หรือ CI bot)
2. **Skill / Agent Workflow** คือ recipe สำหรับงานซ้ำ — แต่ละ skill เรียก context ที่เหมาะสม
3. **Context Layer** คือทุกแหล่งที่ AI จะอ่าน — handbook, ticket, code, schema, catalog
4. **Generation Layer** คือ template + scaffold ที่ AI ใช้สร้างของตามมาตรฐาน
5. **Enforcement Layer** คือชั้นที่ตีกลับเมื่อผิดมาตรฐาน — ส่วนที่ deterministic
6. **Governance Layer** คือชั้นวัดผล — เห็นว่าระบบทำงานจริงแค่ไหน

---

## 2. 6 Pillars Framework

ทุก architecture ที่ดีต้องตอบคำถามได้ 6 ข้อ ผมเรียกมันว่า 6 Pillars

| Pillar | คำถามหลัก | ทำผ่าน |
|---|---|---|
| Knowledge | AI รู้กฎอะไรของบริษัท | Handbook, ADR, coding standard |
| Capability | AI เข้าถึงอะไรได้ | MCP, RAG, Jira, Git, DB schema |
| Generation | AI สร้างงานยังไง | Skill, template, slash command |
| Enforcement | อะไรตีกลับเมื่อผิด | CI, linter, SAST, test, ArchUnit |
| Distribution | ส่งมาตรฐานถึงทุก repo ยังไง | Plugin, package, starter, Renovate |
| Governance | วัดผลและปรับยังไง | Telemetry, dashboard, review metric |

ตอนนี้ขยายแต่ละ pillar ทีละข้อ:

### 2.1 Knowledge — AI รู้กฎอะไร

ปัญหาที่แก้: **AI ไม่รู้ว่าบริษัทเรามี convention อะไร**

ส่วนประกอบ:
- AI Engineering Handbook (กฎการเขียนโค้ด)
- ADR (Architecture Decision Record) ที่ผ่านมา
- API standard
- Security policy
- Testing strategy
- Naming convention
- Review checklist

วิธีให้ AI เห็น: เขียนเป็น `CLAUDE.md` / `AGENTS.md` / `.cursorrules` / `.github/copilot-instructions.md` — ที่ tool อ่านอัตโนมัติ

**Anti-pattern:** เขียน handbook ไว้ใน Confluence อย่างเดียวแล้วบอก "AI เข้าถึงได้ผ่าน MCP" — ในทางปฏิบัติ AI tool หลายตัวอ่าน file ใน repo ก่อน MCP ดังนั้นต้อง **ทั้งสอง**

### 2.2 Capability — AI เข้าถึงอะไรได้

ปัญหาที่แก้: **AI generate code เพราะมันไม่เห็นข้อมูลจริง**

MCP (Model Context Protocol) คือมาตรฐานที่ทำให้ AI เข้าถึง resource ของบริษัทได้แบบควบคุมสิทธิ์ได้

MCP server ที่ควรมี:

| MCP Server | ใช้ทำอะไร | Permission ที่แนะนำ |
|---|---|---|
| Ticket MCP (Jira/Redmine/Linear) | อ่าน ticket, comment, link | Read-only ก่อน |
| Wiki MCP (Confluence/Notion) | อ่าน BRD, architecture, ADR | Read-only |
| Git MCP | อ่าน code, PR, history | Read-only |
| Database Schema MCP | อ่าน schema, data dictionary | Read-only schema |
| API Catalog MCP | อ่าน OpenAPI, service catalog | Read-only |
| Component Catalog MCP | อ่าน UI components, Storybook | Read-only |
| Observability MCP | อ่าน log, trace, metric | Read scoped by service |
| Security MCP | อ่าน policy, vulnerability | Read-only |

**สำคัญ:** เริ่มจาก read-only ทุกตัวก่อน — write action ค่อยเปิดทีละจุดเมื่อมี audit trail พร้อม

### 2.3 Generation — AI สร้างงานยังไง

ปัญหาที่แก้: **แต่ละคน prompt ต่างกัน ผลก็ต่างกัน**

แทนที่จะให้ทุกคน prompt เอง สร้าง **slash command** มาตรฐาน

ตัวอย่าง skill set:

| Skill | Input | Output |
|---|---|---|
| `/from-ticket` | Ticket ID | Implementation plan |
| `/scaffold-resource` | Resource name | Backend files (controller, service, repo, test) |
| `/scaffold-feature` | Feature name | Frontend files (page, form, api, types, test) |
| `/review-before-pr` | Diff | Self-review checklist |
| `/security-audit` | PR/module | Security findings |
| `/generate-test-matrix` | Ticket / API spec | Test matrix |
| `/impact-analysis` | Change description | Affected components |
| `/incident-triage` | Incident ID / log | Probable cause + suggested action |

แต่ละ skill มี:
1. **Description** — เมื่อไรควรใช้
2. **Input parameters** — สิ่งที่ user ระบุ
3. **Workflow** — ลำดับ tool calls (load context → query → generate → check)
4. **Output schema** — รูปแบบผลที่คาดหวัง
5. **Guardrails** — สิ่งที่ skill ห้ามทำ

(มีตัวอย่างเขียนละเอียดในส่วน 5 ของตอนนี้)

### 2.4 Enforcement — อะไรตีกลับเมื่อผิด

ปัญหาที่แก้: **AI review ดี แต่ไม่ deterministic**

หลักสำคัญที่ผมพูดทุกครั้ง:

> **AI ตรวจได้ แต่ตัวตีกลับต้อง deterministic**

Layer ของ enforcement:

| Layer | ตัวอย่าง | Deterministic? |
|---|---|---|
| Pre-commit | Prettier, lint-staged, gitleaks | ✅ |
| Local review | AI review ก่อน push | ❌ (advisory) |
| CI lint | ESLint, Spotless, Checkstyle | ✅ |
| CI test | Unit test, integration test | ✅ |
| CI quality | SonarQube quality gate | ✅ |
| CI security | SAST, dep scan, secret scan | ✅ |
| CI architecture | ArchUnit, dependency-cruiser | ✅ |
| CI contract | Pact, Spectral OpenAPI lint | ✅ |
| AI review (PR) | LLM-based review | ❌ (advisory) |
| Human review | Code owner approval | ✅ |

อะไรที่ block merge ได้ ต้องเป็นชั้นที่ deterministic — AI review เป็น advisory เท่านั้น เพราะถ้าครั้งนี้ผ่าน ครั้งหน้าไม่ผ่านโดยไม่มีเหตุผล team จะหมดศรัทธาใน CI ใน 2 สัปดาห์

### 2.5 Distribution — ส่งมาตรฐานถึงทุก repo ยังไง

ปัญหาที่แก้: **มี 50-500 repo จะ sync handbook ยังไง**

ห้าม copy-paste — drift แน่นอน

แนวทาง:

1. **Central rule package** — เผยแพร่ผ่าน package registry (npm/Maven)
   - `@company/ai-rules`
   - `@company/backend-standard`
   - `@company/frontend-standard`

2. **Repo metadata** — ทุก repo มี `service.yaml`

```yaml
service:
  name: payment-service
  domain: payment
  stack: java-dropwizard
  owner: payment-team
  criticality: high
  database: payment_db
```

3. **Generate instruction file** — CI รัน script generate `CLAUDE.md` / `AGENTS.md` / `.cursorrules` จาก rule package + service.yaml

4. **Renovate update** — Renovate เปิด PR bump rule version อัตโนมัติ

5. **Drift check** — CI fail ถ้า:
   - rule file ไม่ตรง generated version (พิสูจน์ว่ามีคนแก้ด้วยมือ)
   - rule package version ต่ำเกิน
   - service.yaml ขาด
   - critical service ไม่มี security rule

(ลงรายละเอียด multi-repo strategy ในส่วน 7 ของตอนนี้)

### 2.6 Governance — วัดผลและปรับยังไง

ปัญหาที่แก้: **ตอบไม่ได้ว่า AI ช่วยจริงไหม**

Telemetry ต้องเก็บ:
- Skill usage (ใคร ใช้ skill ไหน เมื่อไร ผลลัพธ์ pass/fail)
- AI suggestion acceptance rate
- PR review time
- First-pass PR rate
- CI failure breakdown
- Standard drift (repo ที่ใช้ rule version เก่า)

Dashboard ที่ควรมี (ลงรายละเอียดใน Part 5):
- AI-generated PR count
- PR pass rate
- Review bottleneck
- Common AI mistakes
- Top missing instructions
- CI failure by rule
- Security findings
- Repo rule version
- Skill usage funnel

---

## 3. AI Engineering Handbook — ขยายลึก

ส่วนนี้คือ pillar ที่สำคัญที่สุดและคนทำผิดบ่อยที่สุด

### 3.1 ทำไมไม่ควรเขียนแค่ `CLAUDE.md`

ถ้าเขียน rule ลง `CLAUDE.md` อย่างเดียว — มันผูกกับ Claude tool

วันนึงคุณเปลี่ยนใจไปใช้ Cursor หรือ Continue หรือ Copilot — ต้องเขียนใหม่

แนวทางที่ดีกว่า: เก็บ rule เป็น **single source** แล้ว generate ออกหลาย format

### 3.2 โครงสร้างที่แนะนำ

```text
/ai
  /rules
    architecture.md
    backend-java.md
    backend-node.md
    frontend-react.md
    frontend-vue.md
    api-standard.md
    security.md
    testing.md
    database.md
    naming.md
    git-workflow.md
  /generated
    CLAUDE.md           ← generated
    AGENTS.md           ← generated
    .cursorrules        ← generated
    .github/copilot-instructions.md  ← generated
  /scripts
    generate.sh
    validate.sh
  service.yaml
```

`generate.sh` รวม rule ที่เกี่ยวกับ stack ของ repo (จาก `service.yaml`) แล้วสร้างไฟล์ instruction ตาม format ที่แต่ละ tool ต้องการ

### 3.3 ตัวอย่าง backend rule

```md
# Backend Java Rules

## Architecture
- Use clean architecture layers: resource → service → repository
- Resource/Controller must only handle HTTP mapping and validation
- Business logic must be in service layer
- Repository handles database access only

## DI
- Use constructor injection only
- Do not use field injection (`@Autowired` on field is forbidden)

## Error handling
- Use `CompanyException` with error code from `ErrorCode` enum
- Never catch `Exception` and log silently
- Wrap external service errors with `IntegrationException`

## Audit
- Every write action must call `AuditLogger.log(actor, action, resource)`
- Audit log must be in same transaction as write

## Library
- Do not introduce new library without ADR
- Use approved library list in `/ai/rules/approved-libraries.md`

## Testing
- Add unit test for service layer (target: 80% line coverage)
- Add integration test for resource layer (happy + error path)
```

### 3.4 ตัวอย่าง frontend rule

```md
# React Frontend Rules

## Component
- Use components from `@company/ui` for primitives
- Never use raw `<button>`, `<input>`, `<select>` in feature screens
- Use `@company/forms` for form composition
- Use `@company/api-client` for HTTP (never axios/fetch directly)

## Styling
- Use design tokens (colors, spacing, typography) from `@company/themes`
- No hard-coded color hex
- Support light + dark theme

## State
- Every screen must handle: loading, empty, error, success state
- Use feature folder structure (`features/<feature-name>/`)

## Accessibility
- All interactive elements need aria-label or visible label
- Form fields need associated `<label>`
- Icons-only buttons need aria-label
- Run `axe` test in CI

## Type
- Strict TypeScript (no `any` without comment + reason)
- Schema validation with Zod for all external data
```

### 3.5 หลักเขียน rule ที่ใช้ได้จริง

1. **เขียนเป็น "ห้าม" + "ให้ใช้แทน"** — AI เข้าใจง่ายกว่า "ควรใช้"
2. **ใส่ตัวอย่าง bad/good** — โมเดลใช้ pattern matching
3. **อ้าง file path / package** — ให้ AI ค้นได้
4. **อย่าใส่ rule กว้างเกิน** — "เขียนโค้ดสะอาด" ไม่มีความหมาย ระบุชัด
5. **อย่าเขียนยาวเกิน 500 บรรทัด** — context window จำกัด แบ่งเป็น file ตาม domain

---

## 4. MCP Layer — ขยายลึก

### 4.1 MCP คืออะไรในภาษาคน

MCP (Model Context Protocol) คือมาตรฐานเปิดที่ Anthropic เสนอสำหรับให้ LLM client (Claude, Cursor, อื่น ๆ) เชื่อมกับ "ระบบที่มีข้อมูล" แบบ standardized

แทนที่จะ:
- Copy-paste Jira ticket เข้า prompt
- Screenshot DB schema แปะ
- Paste API spec
- Manually อธิบาย "ระบบเรามี X, Y, Z"

ใช้ MCP server ที่:
- Expose ข้อมูลตาม protocol มาตรฐาน
- ควบคุมสิทธิ์ที่ server level
- Audit ได้ว่า AI access อะไรเมื่อไร

### 4.2 ตัวอย่าง MCP server ที่ใช้งานจริง

**Atlassian Rovo MCP** — search/summarize Jira, Confluence, Compass; create/update issues หรือ pages

**GitHub MCP** — search code, read PR, list issues, comment on PR

**Internal MCP** ที่บริษัทต้องสร้างเอง:
- DB Schema MCP (อ่าน Liquibase / Flyway / Prisma schema)
- API Catalog MCP (อ่าน OpenAPI registry)
- Component Catalog MCP (อ่าน Storybook stories + meta)

### 4.3 MCP Permission Model

ตารางแนะนำสิทธิ์เริ่มต้น:

| Role | MCP | Read | Write | Production Action |
|---|---|---|---|---|
| PM Agent | Jira | summary | draft (pending review) | No |
| BA Agent | Wiki | full | draft page | No |
| SA Agent | Git, Wiki | full | draft ADR | No |
| Dev Agent | Git, Schema, API catalog | full | local code change | No direct prod |
| QA Agent | Jira, Test repo | full | draft test case | No |
| Ops Agent | Log, Metric | scoped | draft runbook | Approval required |

หลักการ:
- Read-only เป็น default
- Write action ทุกอย่าง = draft → review
- Production action = ต้องมี human approval + audit log

### 4.4 Security Guardrails ของ MCP

| Risk | Guardrail |
|---|---|
| AI access ข้อมูลเกินจำเป็น | Role-based access ที่ MCP server |
| AI แก้ ticket เองผิด | Read-only default, write = draft |
| AI run command อันตราย | Allowlist command + audit log |
| Prompt injection ผ่าน ticket/wiki content | Content sanitization, separator marker |
| Secret exposure | Masking/redaction ที่ MCP layer |
| Excessive agency | Human approval สำหรับ irreversible action |

(จะลงรายละเอียดเรื่อง security ใน Part 5)

---

## 5. Skill / Agent Workflow — ขยายลึก

### 5.1 Anatomy ของ Skill

Skill ที่ดีมี 5 ส่วน:

```yaml
name: from-ticket
description: |
  Convert a ticket into an implementation plan with file changes,
  test scope, and risk assessment.

triggers:
  - When the user wants to start implementing a feature from a ticket
  - When the user types /from-ticket <ticket-id>

inputs:
  ticket_id:
    type: string
    required: true
    description: Jira/Redmine ticket ID (e.g. PAY-123)

workflow:
  - step: Load ticket
    tool: jira_mcp.get_issue
    args: { id: "{{ ticket_id }}" }
    output: ticket
  - step: Load BRD
    tool: confluence_mcp.get_page
    args: { id: "{{ ticket.brd_link }}" }
    output: brd
  - step: Load API standard
    tool: file_read
    args: { path: "/ai/rules/api-standard.md" }
    output: api_standard
  - step: Load DB schema
    tool: schema_mcp.search
    args: { query: "{{ ticket.module }}" }
    output: schema
  - step: Generate plan
    template: implementation-plan
    inputs: { ticket, brd, api_standard, schema }

output_schema:
  - implementation_plan (markdown)
  - file_changes (list)
  - test_scope (list)
  - risks (list)

guardrails:
  - Do not generate code, only plan
  - Do not create new column without checking schema
  - Always include test scope
  - Cite source for each decision
```

### 5.2 ตัวอย่าง 3 skill ที่ใช้บ่อย

**Skill 1: `/scaffold-resource`** — สร้าง backend resource ตาม pattern

```yaml
name: scaffold-resource
inputs:
  resource_name: string
  stack: enum [dropwizard, spring-boot, fastapi, nestjs]
workflow:
  - load: backend-rule.md (ตาม stack)
  - load: api-standard.md
  - load: example-resource (จาก template repo)
  - generate:
      - Resource/Controller
      - DTO with validation
      - Service
      - Repository
      - Mapper
      - Unit test
      - Integration test
      - OpenAPI spec
      - Audit log hook
  - run: linter, format, type check
  - return: file diff + summary
```

**Skill 2: `/security-audit`** — ตรวจ security ของ PR

```yaml
name: security-audit
inputs:
  target: string  # PR ID or file path
workflow:
  - load: security-rule.md
  - load: OWASP LLM Top 10 checklist
  - get: PR diff
  - check:
      - SQL injection pattern
      - XSS pattern
      - Auth/permission decorator presence
      - Audit log presence for write action
      - PII in log statement
      - Hardcoded secret
      - Unbounded query
  - run: SAST scanner (Semgrep)
  - cross-check: AI findings vs SAST findings
  - return: severity-ranked findings + suggested fix
```

**Skill 3: `/impact-analysis`** — หา impact ของ change

```yaml
name: impact-analysis
inputs:
  change_description: string
workflow:
  - search code (cross-repo grep via Git MCP)
  - search API catalog (endpoint that touch field)
  - search DB schema (table dependency)
  - search batch job catalog
  - search report SQL
  - search past incident (incident MCP)
  - synthesize: dependency graph + risk matrix
  - return: impact summary + recommendation
```

### 5.3 Skill Composition

Skill ที่ใหญ่สามารถเรียก skill ที่เล็กกว่าได้ เช่น:

`/from-ticket` → เรียก `/impact-analysis` → เรียก `/scaffold-resource` → เรียก `/generate-test-matrix`

Pattern นี้คือ "agent calling agent" ซึ่งทำให้ workflow ใหญ่ ๆ จัดการได้

---

## 6. Plugin: Onboarding Kit — ขยายลึก

### 6.1 ทำไมต้องมี Plugin

ถ้าให้ developer ใหม่ setup AI environment เองทีละขั้น:

```bash
# ติดตั้ง CLI
brew install ...
# โหลด rule package
npm i -g @company/ai-rules
# generate instruction file
company-ai generate
# setup MCP config
cp /path/to/mcp-config ~/.config/...
# install slash commands
...
```

จะมีคนทำผิด คน 2 ใน 10 มีไฟล์ขาด คนที่ 5 ติดตั้งเวอร์ชันเก่า — ปัญหา drift กลับมาที่จุดเริ่ม

ทางออก: **plugin** ที่ติดตั้งทุกอย่างใน command เดียว

### 6.2 Plugin ทำอะไรบ้าง

```bash
company-ai init backend
```

Plugin จะ:
1. Detect stack จาก project (Java/Node/Python/...)
2. ติดตั้ง instruction files ที่ตรงกับ stack
3. Setup MCP config (Jira, Wiki, Schema MCP สำหรับ developer)
4. Setup slash commands ที่เกี่ยวข้อง
5. Install skills ตาม role
6. Verify permissions (login Jira, GitHub, Confluence)
7. Check local environment (Docker, Java version, Node version)
8. Register repo metadata กับ central registry

```bash
company-ai doctor
```

ตรวจว่าทุกอย่างยัง healthy:
- Instruction file version up to date
- MCP server reachable
- Permission ยังใช้ได้
- Skill version ยังตรง

```bash
company-ai upgrade
```

อัปเดต rule + skill version อัตโนมัติ (ผ่าน Renovate-like mechanism)

### 6.3 ทำไม plugin สำคัญกว่าที่คิด

มนุษย์เป็นสิ่งมีชีวิตที่ copy command จาก wiki เก่าปี 2021 แล้วถามว่าทำไมพัง — ถ้าให้ self-setup จะมี configuration drift ภายใน 6 เดือน

Plugin ทำให้ทีมทุกคนเริ่มจากจุดเดียวกัน ไม่มี "เครื่องของพี่ A ใช้ได้ ของผมไม่ได้" อีก

### 6.4 Plugin Anatomy

```text
company-ai-plugin/
  manifest.yaml          ← version, dependencies
  rules/                 ← instruction templates
  skills/                ← slash command definitions
  mcp/                   ← MCP server configs
  hooks/                 ← pre-commit, post-checkout
  scripts/
    init.sh
    doctor.sh
    upgrade.sh
```

`manifest.yaml`:

```yaml
name: company-ai
version: 1.4.2
description: Company AI engineering toolkit
supported_stacks:
  - java-dropwizard
  - java-spring-boot
  - node-typescript
  - python-fastapi
mcp_dependencies:
  - jira-mcp >= 2.0
  - confluence-mcp >= 1.5
  - schema-mcp >= 0.9
```

---

## 7. Multi-Repo Strategy

### 7.1 ปัญหา: 50-500 repo จะ sync handbook ยังไง

3 ทางเลือก:

| ทางเลือก | ข้อดี | ข้อเสีย |
|---|---|---|
| Copy-paste manual | ง่าย | drift แน่นอนใน 3 เดือน |
| Mono-repo | sync ตลอด | scale ไม่ได้กับ enterprise |
| Central package + generator | sync ได้, scale ได้ | ต้องสร้าง package + CI |

ทางเลือกที่ 3 คือคำตอบสำหรับ enterprise ที่มี service หลาย team

### 7.2 Architecture

```text
┌─────────────────────┐
│ Central Rule Repo   │
│ @company/ai-rules   │
└──────────┬──────────┘
           │ publish version
           ▼
┌─────────────────────┐
│ Package Registry    │
│ (npm/Maven/Artif.)  │
└──────────┬──────────┘
           │ Renovate bot
           ▼
┌─────────────────────────────────────┐
│ Each service repo:                   │
│   service.yaml (metadata)            │
│   ai-rules version pinned            │
│   CI generates CLAUDE.md/AGENTS.md   │
│   from rule package + service.yaml   │
└─────────────────────────────────────┘
```

### 7.3 Drift Check ใน CI

```yaml
# .github/workflows/ai-drift-check.yml
- name: Check AI rules drift
  run: |
    company-ai generate --check
    # CI fail ถ้า:
    # - generated CLAUDE.md ไม่ตรง with file in repo
    # - service.yaml ขาด required field
    # - ai-rules version ต่ำกว่า minimum supported
```

### 7.4 Critical Service Override

Service ที่ tag `criticality: high` (ใน `service.yaml`) จะมี rule เพิ่ม:

```yaml
service:
  name: payment-service
  criticality: high
  required_rules:
    - security-strict
    - audit-mandatory
    - dual-control-deploy
```

CI ของ critical service จะ enforce:
- Security scan ผ่าน 100% (no warning ก็ fail)
- Audit log coverage check
- 2-person approval สำหรับ migration

---

## 8. CI/CD + SonarQube + SAST Layer — ขยายลึก

(ส่วนนี้ในเอกสารเดิมบางที่สุด — ขอขยายให้เป็นเรื่องเป็นราว)

### 8.1 ปัญหาที่ต้องแก้

- AI-generated code ดูดีแต่ไม่ตรง standard
- Reviewer ตามไม่ทันเพราะ PR ปริมาณเพิ่ม
- Security check มาช้าใน pipeline (ใกล้ release)
- Standard enforcement manual = inconsistent

### 8.2 Gate Model 4 ชั้น

แบ่ง CI gate เป็น 4 ชั้นจากเร็ว → ช้า:

**Gate 1 — Pre-commit (local, 1-3 วินาที)**
- Prettier / dprint format
- Lint-staged
- Gitleaks (secret scan)
- Spell check
- Commit message format

ถ้าผ่านก็ commit ได้

**Gate 2 — Pre-push / Pre-PR (10-30 วินาที)**
- ESLint / Spotless / Checkstyle
- TypeScript / mypy type check
- Unit test (เฉพาะที่กระทบ — incremental)
- AI review (advisory)

**Gate 3 — CI on PR (3-10 นาที)**
- Full unit test
- Integration test
- Contract test
- ArchUnit / dependency-cruiser
- OpenAPI lint (Spectral)
- Build container image
- Snapshot test (Storybook visual regression)

**Gate 4 — Pre-merge (10-30 นาที)**
- SAST (Semgrep / SonarQube quality gate)
- Dependency scan (Snyk / OSV / Trivy)
- Secret scan full
- License compliance
- Code coverage threshold
- Performance regression test (optional, สำหรับ critical service)

หลักการ:
- Gate 1-2 ต้อง **เร็ว** (developer feedback loop)
- Gate 3-4 สามารถ **ช้า** ได้ (ก่อน merge)
- ถ้า Gate 3-4 ช้าเกิน 15 นาที — แบ่งเป็น parallel pipeline

### 8.3 AI Review ในตำแหน่งไหน

AI review (LLM-based code review) อยู่ใน **Gate 2** — advisory เท่านั้น ไม่ block

เหตุผล:
- AI ไม่ deterministic — บล็อก merge ตามอารมณ์ model = nightmare
- AI false positive สูง — block จะเสีย trust ของ team
- AI false negative ก็มี — pretend pass ทั้งที่มีปัญหา

ทำอะไรได้ดี: comment บน PR, suggest improvement, สรุป change

ทำอะไรไม่ดี: block merge, replace human reviewer

### 8.4 SonarQube + SAST

SonarQube quality gate ตั้งให้ block merge ถ้า:
- New code coverage < 80%
- New code duplication > 3%
- Security hotspot ที่ไม่ได้ review
- Bug rating < A
- Vulnerability rating < A

ส่วน SAST (Semgrep / Snyk Code) ตั้งให้:
- Critical / High = block merge
- Medium = require justification comment
- Low = warning ไม่ block

---

## 9. Figma + Storybook + Design System — ขยายลึก

(อีกส่วนที่เอกสารเดิมบาง — ขอขยาย)

### 9.1 ปัญหาที่ต้องแก้

- Design ↔ implementation ไม่ตรง
- Dev สร้าง component ใหม่ทั้งที่มีของเดิม
- UX state ไม่ครบ (ลืม empty/error state)
- Accessibility หลุด — เจอตอน production
- Copy text ไม่สม่ำเสมอ

### 9.2 Architecture

```text
Figma (design source)
    │
    ├─→ Tokens Studio / Style Dictionary
    │       │
    │       └─→ Design tokens (JSON)
    │              │
    │              └─→ Frontend theme
    │
    ├─→ Component spec (Figma)
    │       │
    │       └─→ Storybook story (sync via Figma plugin)
    │
    └─→ Handoff doc (Figma → AI)
            │
            └─→ /handoff-spec command
```

### 9.3 AI Use Cases ใน Design System

**1. Component Mapping**

```text
/find-component "primary button with loading state"
```

AI query Storybook MCP + คืน:
- Component name + import path
- Props ที่ใช้
- Variant ที่มี
- Usage example
- Accessibility note
- Figma link

**2. Handoff Generator**

จาก Figma frame + ticket:

```text
/handoff-spec figma-link CUS-456
```

AI generate:
- Component mapping (Figma layer → @company/ui)
- State spec (loading, empty, error, success)
- Validation rule
- Responsive breakpoint
- Copy text + i18n key
- Accessibility checklist

**3. Visual Regression Suggestion**

ก่อน merge AI suggest visual test ที่ควรเพิ่ม:
- Component variants ที่ยังไม่ครอบ
- Theme combinations (light + dark + brand variant)
- Locale (LTR vs RTL)
- Edge state (long text, empty data)

**4. Copy Review**

```text
/copy-review draft.tsx
```

AI ตรวจ:
- Tone ตรงกับ brand voice guideline
- ใช้ i18n key (ไม่ hardcode)
- Error message ตาม style guide
- Reading level เหมาะกับ target user

### 9.4 Enforcement

- ESLint plugin: ห้าม import component นอก `@company/ui` ใน feature folder
- Storybook visual regression (Chromatic / Playwright)
- Accessibility test ใน CI (axe-core)
- Design token check (no hardcoded color hex)

---

## 10. Workflow End-to-End: ตัวอย่างจริง

ลองดูภาพรวมเมื่อทุกชั้นทำงานพร้อมกัน

**Scenario:** เพิ่ม Payment Callback จาก Ticket

### ก่อนใช้ AI Agent Platform

1. PM สร้าง ticket คร่าว ๆ
2. BA แนบ spec
3. Dev อ่านไม่ครบ
4. Dev ใช้ AI generate code
5. AI ไม่รู้ internal SDK
6. PR ใช้ naming ผิด
7. Reviewer comment 30 จุด
8. QA พบ missing edge case
9. Rework
10. Merge ช้า

### หลังใช้ AI Agent Platform

```text
/from-ticket PAY-1234
```

AI ทำ:
1. อ่าน ticket จาก Jira (MCP)
2. อ่าน BRD จาก Confluence (MCP)
3. อ่าน API standard (handbook)
4. อ่าน DB schema (Schema MCP) → พบว่ามี `payment_callback_log` แล้ว
5. อ่าน service catalog → พบ `PaymentService.confirm()` ใช้ pattern เดิม
6. สร้าง implementation plan
7. สร้าง OpenAPI draft
8. Scaffold code ตาม internal framework (`/scaffold-resource`)
9. Generate unit + integration test
10. Run pre-commit (Gate 1)
11. Generate self-review (`/review-before-pr`)
12. Generate PR description

PR ที่เปิดมาตรงตาม standard, มี test, มี audit log, มี security check ผ่านแล้ว — reviewer focus ที่ business logic เท่านั้น

---

## สรุป Part 4

โครง architecture ทั้งหมดยืนบน 6 pillars:

1. **Knowledge** — handbook ที่ machine-readable
2. **Capability** — MCP/RAG ให้ AI เห็น context จริง
3. **Generation** — skill มาตรฐาน ไม่ใช่ prompt อิสระ
4. **Enforcement** — deterministic gate (linter, test, SAST)
5. **Distribution** — central package + generator + Renovate
6. **Governance** — telemetry + dashboard + metric

Building blocks สำคัญ: handbook structure, MCP layer, skill anatomy, plugin onboarding, multi-repo strategy, CI gate model, design system integration

ใน Part 5 เราจะลงไปดู **Governance, Security, Anti-Patterns** — ส่วนที่จะทำให้ architecture นี้ไม่กลายเป็น Frankenstein ภายใน 1 ปี — รวมถึง risk model, policy, dashboard ที่ต้องมี และ 5 anti-pattern ที่ทุกองค์กรเจอ
