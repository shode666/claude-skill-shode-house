# Presentation Script — AI-Era Engineering Standards

> Speaker notes สำหรับ pitch deck 29 slides ที่ commit แล้ว
> Total: 25–30 นาที + 10 นาที Q&A
>
> วิธีใช้: Copy แต่ละ section ไปวางใน Canva Notes panel (กดไอคอน Notes ที่ด้านล่างของ editor) ทีละหน้า
> หรือใช้เป็น script rehearse ก่อน pitch จริง

---

## Slide 1 — Cover (Bundit Rattanang @shode)

**เวลา: 1 นาที**

สวัสดีครับ ผมบัณฑิต รัตนาง

วันนี้ผมจะมาเสนอ framework กลางที่จะช่วยให้ทีม developer ของเราทำงานกับ AI ได้มาตรฐานเดียวกัน

ใน 25 นาทีต่อจากนี้ ผมจะพาทุกคนไปดู 3 อย่าง — หนึ่ง ปัญหาที่กำลังเกิดขึ้นจริงในทีมเราตอนนี้ สอง วิธีแก้ในรูปแบบ framework ที่ใช้ได้จริง และสาม ทรัพยากรที่ต้องการเพื่อเริ่มต้น

ขอเริ่มจากปัญหาเลยนะครับ

---

## Slide 2 — The Problem

**เวลา: 1.5 นาที**

ทุกคนน่าจะเห็นด้วยว่า AI ช่วยให้เราเขียนโค้ดเร็วขึ้นจริง

แต่สิ่งที่ตามมาในทีมคือ — dev 10 คนใช้ AI ก็ได้โค้ด 10 ทรงต่างกัน

สถาปัตยกรรม การตั้งชื่อ และ library ที่ใช้ ต่างกันหมด

ผลก็คือ รอบรีวิวยืดเยื้อขึ้น 30-50% และหนี้ทางเทคนิคสะสมเร็วกว่าเดิม

นี่ไม่ใช่อนาคต — มันเกิดขึ้นแล้ววันนี้ ในทีมเรา

---

## Slide 3 — Why It Matters Now

**เวลา: 1 นาที**

ทำไมต้องทำตอนนี้ ไม่ใช่ปีหน้า?

การใช้ AI ในทีม dev โต 80% ต่อปี อัตราการสร้างโค้ดเพิ่มขึ้น 5 เท่า

แต่กำลังคน review ของเรายังเท่าเดิม

ผลคือ บั๊กและช่องโหว่ security จะหลุดเข้า production ง่ายขึ้น

ต้นทุนรวมคือ หนี้ทางเทคนิคบวกกับความช้า

ยิ่งช้าเริ่ม ยิ่งแพง

---

## Slide 4 — Mental Model: 1,000 New Hires

**เวลา: 1.5 นาที**

ก่อนเข้า solution ขอแชร์ mental model ที่ใช้คิดเรื่องนี้

ลองคิดว่า AI agent คือ dev ใหม่ 1,000 คน ที่เข้ามาทำงานพร้อมกันในวันเดียว

ถ้าจ้างจริงๆ บริษัทต้องเตรียมอะไร? ต้องมีคู่มือ พี่เลี้ยง library ผู้รีวิว และ CI/CD ใช่ไหม

AI agent ก็ต้องการสิ่งเหล่านี้เหมือนกันทุกอย่าง

ต่างเดียว — format ต้องเป็นไฟล์ที่เครื่องอ่านได้ ไม่ใช่ Confluence ไม่ใช่ PDF

นี่คือ paradigm shift ที่เราต้องยอมรับ

---

## Slide 5 — Four Building Blocks

**เวลา: 30 วินาที**

จาก mental model นั้น เรามี 4 building block หลักที่ต้องรู้จัก

CLAUDE.md, MCP, Skill, Plugin

ผมจะอธิบายทีละตัว — แต่ละตัวแก้ปัญหาคนละด้าน และต้องมีครบทั้ง 4 ตัว ขาดตัวไหนตัวหนึ่งระบบทำงานไม่ครบ

---

## Slide 6 — Block 1: CLAUDE.md

**เวลา: 1.5 นาที**

ตัวแรก CLAUDE.md

**ปัญหาที่แก้** — AI ไม่รู้กฎของบริษัท

**วิธีแก้** — เขียนกฎเป็นไฟล์ text แล้ว commit ลง git ทุกครั้งที่เปิด project AI จะโหลดกฎอัตโนมัติ

ตัวอย่างจริง:
- ก่อน — AI เขียน `axios.get()` ตรงๆ
- หลัง — AI ใช้ `apiClient.get()` ของบริษัท

เปรียบเหมือน — คู่มือ employee handbook ของพนักงาน

---

## Slide 7 — Block 2: MCP

**เวลา: 1.5 นาที**

ตัวที่สอง MCP — Model Context Protocol

**ปัญหาที่แก้** — AI เข้าไม่ถึงข้อมูล live ของบริษัท

**วิธีแก้** — เปิดประตูให้ AI ดึงข้อมูลแบบ real-time

ตัวอย่าง:
- Atlassian MCP — อ่าน Jira ticket ปัจจุบัน
- Database MCP — ดู schema ที่ใช้จริง
- Component Catalog MCP — รู้ว่า UI ของเรามีอะไร

ผลคือ — แทนที่ AI จะสร้าง column ซ้ำที่มีอยู่ มันจะเช็คก่อน ใช้ของเดิม

เปรียบเหมือน — บัตรเข้าระบบของพนักงาน

---

## Slide 8 — Block 3: Skill

**เวลา: 1.5 นาที**

ตัวที่สาม Skill

**ปัญหาที่แก้** — AI ไม่รู้ workflow ที่ซับซ้อน

ตัวอย่างเช่น code review ที่ดีต้องตรวจ 7 มิติ AI ทำไม่ครบหรอกถ้าไม่บอก

**วิธีแก้** — Skill รวมความรู้ + workflow + prompts ไว้ในตัวเดียว ใช้ได้ทุก project

ตัวอย่าง Skill:
- code-reviewer ตรวจ 7 มิติ
- scaffold-resource สร้าง 8 ไฟล์ตาม pattern
- security-audit ตรวจ OWASP + policy บริษัท

เปรียบเหมือน — คอร์ส training เฉพาะทาง

---

## Slide 9 — Block 4: Plugin

**เวลา: 1 นาที**

ตัวสุดท้าย Plugin

**ปัญหาที่แก้** — dev ต้อง install ของทีละตัวลำบาก

**วิธีแก้** — Plugin รวม skills + MCP + commands + agents ไว้ในชุดเดียว

ก่อน — setup เครื่อง dev ใหม่ใช้เวลา 1 วัน
หลัง — 1 คำสั่ง 5 นาทีพร้อมทำงาน

เปรียบเหมือน — onboarding kit ที่ HR เตรียมให้พนักงานใหม่

---

## Slide 10 — How They Work Together

**เวลา: 2 นาที**

ทีนี้ทั้ง 4 ตัวทำงานร่วมกันยังไง?

ลองดูตัวอย่างจริง — dev พิมพ์ `/from-jira PAY-1234`

**ขั้น 1-2 (Slash Command)** — คำสั่งนี้ติดตั้งมาพร้อม Plugin มันจะเรียก Skill ชื่อ from-jira ทำงาน

**ขั้น 3-5 (Skill Activation)** — Skill เริ่มทำสามอย่าง:
- อ่าน Jira ticket ผ่าน Atlassian MCP
- โหลดกฎจาก CLAUDE.md
- ค้น UI ที่มีจาก Component Catalog MCP

**ขั้น 6-7 (Workflow Execution)** — AI generate โค้ดตาม pattern ของบริษัท ใช้ internal SDK จากนั้น pre-commit และ CI gate ตรวจซ้ำอีกชั้นก่อน push

ทุกตัวทำหน้าที่ต่างกัน แต่เสริมกัน ขาดไม่ได้

---

## Slide 11 — Why MCP Alone Isn't Enough

**เวลา: 1 นาที**

หลายทีมตอนนี้เริ่มลง MCP แล้ว ก็ดี — แต่ผมขอย้ำว่า MCP อย่างเดียวไม่พอ

- MCP รู้ข้อมูลแต่ไม่รู้กฎ → ต้องมี CLAUDE.md ช่วย
- MCP ไม่รู้ workflow ซับซ้อน → ต้องมี Skill ช่วย
- และ install ลำบาก → ต้องมี Plugin

4 building block ต้องทำงานร่วมกันถึงจะได้ผลจริง

---

## Slide 12 — The 6 Pillars

**เวลา: 1.5 นาที**

ทีนี้ที่ระดับสูงขึ้น — เรามองเป็น framework 6 ชั้นที่ทำงานร่วมกัน

- Knowledge — AI รู้กฎอะไร
- Capability — AI ทำอะไรได้
- Generation — AI สร้างโค้ดยังไง
- Enforcement — ใครตีกลับเมื่อผิด

แล้วยังมีอีก 2 ชั้น — Distribution วิธีส่งของถึง dev และ Governance กำกับดูแล วัดผล

4 building block ที่อธิบายไปก่อนหน้า ฝังอยู่ใน Pillar 1, 2, 3 และ 5

---

## Slide 13 — Tech Stack Map

**เวลา: 1.5 นาที**

ลงลึกที่ tech stack จริงในแต่ละ Pillar:

- **Knowledge** — CLAUDE.md, AGENTS.md, ADR markdown, OpenAPI
- **Capability** — MCP servers, RAG, Skills, Agents
- **Generation** — Plugin, Slash commands, Internal SDK, Templates
- **Enforcement** — ESLint, Spotless, ArchUnit, GitHub Actions
- **Distribution** — Plugin marketplace, npm/Maven, Renovate
- **Governance** — Backstage, OpenTelemetry, GitHub Discussions

ทุกเครื่องมือทำงานร่วมกันเพื่อสร้างมาตรฐานที่ใช้ได้จริง และที่สำคัญ — บังคับได้

---

## Slide 14 — Pillar 1: Knowledge — CLAUDE.md & Friends

**เวลา: 1 นาที**

Pillar 1 Knowledge — ไฟล์ที่ AI อ่านอัตโนมัติ

- **CLAUDE.md** — หลักสำหรับ Claude Code
- **AGENTS.md** — universal ใช้ได้กับ AI tool หลายตัว
- **ADR Markdown** — บันทึก architecture decision

หัวใจคือ — ทุกอย่างต้อง machine-readable ไม่ใช่ Confluence ไม่ใช่ PDF

---

## Slide 15 — Pillar 2: Capability — MCP & Skills

**เวลา: 1 นาที**

Pillar 2 Capability — ช่องทางที่ AI เข้าถึงข้อมูลและทำงาน

3 ส่วนหลัก:
- **เข้าถึงข้อมูล** — MCP ให้ AI query real-time
- **ทักษะเฉพาะทาง** — Skill กำหนด workflow ของ AI
- **การติดตั้ง** — Plugin ลดขั้นตอน setup

หลักการ — AI ไม่ควรเดา ต้องถามจาก source of truth เสมอ

---

## Slide 16 — Pillar 3: Generation — Plugin & SDK

**เวลา: 1 นาที**

Pillar 3 Generation — สิ่งที่บังคับให้ AI สร้างโค้ดตรง pattern

- **Plugins** — install ครั้งเดียวได้ skills + commands + MCP
- **SDK Features** — wrapper บริษัท เช่น HTTP client, logger, auth
- **Code Generation** — slash command สร้างโค้ดตาม template

หลักการ — AI ต่อตัวต่อจากของที่มีอยู่ ไม่ก่ออิฐใหม่ทุกครั้ง

---

## Slide 17 — Pillar 4: Enforcement — Lint, CI, Tests

**เวลา: 1 นาที**

Pillar 4 Enforcement — กลไก machine-enforced ที่ตีกลับถ้า AI ผิด

- **Linting** — ESLint, Spotless, Ruff auto-fix ตอน commit
- **CI** — GitHub Actions รัน test และ scan อัตโนมัติ
- **Testing** — Vitest, JUnit, Playwright รันทุก commit
- **Code Quality** — SonarQube, CodeQL, ArchUnit ตรวจ quality

หลักการเหล็ก — มาตรฐานที่บังคับไม่ได้ = ไม่มีอยู่จริง

---

## Slide 18 — Pillar 5: Distribution

**เวลา: 1 นาที**

Pillar 5 Distribution — ส่งของถึง dev ทุกคน

- **Marketplace** — Plugin marketplace ภายใน 1 คำสั่ง install
- **Auto-update** — Renovate / Dependabot bump version อัตโนมัติ
- **Integration** — เชื่อม IDE, npm, Maven, GitHub Template
- **Feedback** — เก็บ usage จาก dev มาปรับปรุง
- **Distribution** — ส่งของถึง dev ทุกคนพร้อมกัน

หลักการ — เร็วในการ distribute = standard เป็นปัจจุบันจริง

---

## Slide 19 — Pillar 6: Governance + Metrics

**เวลา: 1 นาที**

Pillar 6 Governance — มองภาพรวม วัดผล ปรับปรุง

ดูแลผ่าน 6 มุม:
- Knowledge — AI รู้กฎและ pattern ขององค์กร
- Capability — ช่องทางที่ AI ใช้ทำงาน
- Enforcement — ตีกลับเมื่อโค้ดผิดมาตรฐาน
- Distribution — ส่งของถึง dev ทุกคน
- Governance — ดูแล วัดผล RFC + audit
- Metrics — Backstage scorecard + DORA + telemetry

นี่คือชั้นที่ทำให้ระบบเรียนรู้และพัฒนาต่อเอง

---

## Slide 20 — Multi-Repo Strategy

**เวลา: 1.5 นาที**

คำถามที่หลายคนสงสัย — บริษัทมี 50-500 microservice แล้ว CLAUDE.md ดูแลยังไง

**01 ปัญหา Sync** — องค์กรขนาดใหญ่มีหลายร้อย microservice ต้อง sync CLAUDE.md ให้ตรงกัน ห้าม copy-paste เพราะจะ drift ภายใน 3 เดือน

**02 รูปแบบ Hybrid** — ใช้ 3 ส่วนผสมกัน:
- Package versioned + Live MCP + Generated CLAUDE.md
- มี service.yaml บอก stack/domain
- Renovate bump version อัตโนมัติ
- CI ตรวจ drift และบังคับ minimum version

นี่คือวิธีที่ scale ได้จริง

---

## Slide 21 — Engineer Toolkit: Backend (Dropwizard + Spring)

**เวลา: 1.5 นาที**

ในมุมของ dev backend ที่ใช้ Dropwizard + Spring annotations

**01 CLAUDE.md** — Layer pattern + naming + ห้าม @Autowired field ใช้ constructor injection

**02 MCP** — Atlassian + Database schema + API catalog รู้ service ที่มี

**03 Skills + Plugin** — scaffold-resource, code-reviewer-java, security-audit, dropwizard-starter SDK

ผลคือ dev สั่ง `/new-resource` ได้ scaffold ครบทุกไฟล์ทันที — Resource, Service, Repository, Test, Migration, OpenAPI

---

## Slide 22 — Engineer Toolkit: Frontend (React + Internal UI)

**เวลา: 1.5 นาที**

ฝั่ง frontend ที่ใช้ React + internal component library

**01 CLAUDE.md** — ห้าม raw button/input ใช้ @company/ui เสมอ
**02 Skills** — scaffold-feature, scaffold-component, a11y-audit
**03 MCP** — Component Catalog, Design Tokens, API spec
**04 Plugin** — @company/frontend-plugin install ครั้งเดียวได้ของครบ

ผลคือ component ทุกตัวที่ AI สร้าง มี a11y, theming, test pattern ติดมาตั้งแต่ scaffold

---

## Slide 23 — A Day in the Life

**เวลา: 2 นาที**

ลองดูภาพ workflow จริงของ dev คนหนึ่งใน 1 วัน

**01 Command [Plugin]** — dev พิมพ์ `/from-jira PAY-1234`

**02 Rules [CLAUDE.md]** — AI โหลดกฎจาก CLAUDE.md อัตโนมัติ

**03 Review [Skill]** — `/review` ตรวจตามมาตรฐานบริษัทก่อน commit

**04 Query [MCP]** — AI อ่าน Jira + schema + API catalog ผ่าน MCP

**05 Generate [Templates]** — AI scaffold ตาม pattern ใช้ internal SDK

ผลลัพธ์ — PR ผ่าน review รอบเดียว

นี่คือ standard ที่ scaling — ไม่ว่า dev คนไหน junior หรือ senior ใช้ AI ตัวไหน Claude / Cursor / Copilot output ออกมาทรงเดียวกัน

---

## Slide 24 — Maturity Model: 5 Levels

**เวลา: 1.5 นาที**

ตอนนี้เราอยู่ตรงไหน และจะไปไหน?

- **L0 Wild West** — ไม่มีมาตรฐานร่วม dev ใช้ AI ตามใจ (เราอยู่ตรงนี้ตอนนี้)
- **L1 Static Rules** — CLAUDE.md + Linter + pre-commit + CI
- **L2 Capability Platform** — เพิ่ม MCP + Plugin + Skills + Catalogs
- **L3 Workflow Automation** — Multi-agent + spec-to-code อัตโนมัติ
- **L4 Self-improving** — telemetry feedback ปรับ rules อัตโนมัติ

**เป้าหมายปีนี้ — ขึ้น Level 2**

---

## Slide 25 — Roadmap: 12 Weeks to Level 2

**เวลา: 1 นาที**

แผน 12 สัปดาห์ phased delivery:

- **Week 1-2** — วาง CLAUDE.md template + Tech radar + ADR process
- **Week 3-4** — Shared configs + lefthook + reusable CI workflow
- **Week 5-6** — Design tokens + Storybook + UI library v0
- (Week 7-12 ต่อด้วย Backend Dropwizard starter, Plugin marketplace, MCP servers, Backstage portal)

ทุกสัปดาห์มี deliverable ที่ใช้ได้จริง ไม่ใช่ big bang

---

## Slide 26 — Expected ROI

**เวลา: 1.5 นาที**

ผลลัพธ์ที่ผมเชื่อว่าวัดได้หลัง 6 เดือน:

**Onboarding 3x เร็วขึ้น** — Dev ใหม่ทำงานได้ตั้งแต่สัปดาห์ 1 จากเดิม 3 เดือน

**รอบ Review ลดลง 40%** — เพราะ standard issues ตายตั้งแต่ pre-commit

แค่ 2 ข้อนี้ก็คุ้มกับการลงทุนแล้ว — และผมเชื่อว่าตัวเลขจริงจะดีกว่า projection ด้วยซ้ำ

---

## Slide 27 — Risks & Mitigations

**เวลา: 1.5 นาที**

ขอ honest กับความเสี่ยง:

- **Adoption ต้าน** → ใช้ champion model + co-design กับ dev จริง ไม่บังคับ top-down
- **Over-engineering** → เริ่ม L1 ก่อน แล้ว iterate ทีละสัปดาห์
- **Vendor lock-in** → ใช้ open standards เช่น MCP, OpenAPI, npm — ไม่ผูกกับ AI tool ใด
- **Standard ล้าสมัย** → ทำ telemetry feedback loop ให้ระบบเรียนรู้

ทุกความเสี่ยงเรามีวิธีรับมือ

---

## Slide 28 — What We Need

**เวลา: 1 นาที**

มาถึงส่วนที่สำคัญสุด — ทรัพยากรที่ขอ

- Platform Engineer 2-3 คน full-time 6 เดือน
- Tech Lead 1 คนเป็น program owner
- Pilot 1 ทีม ทดลอง 8 สัปดาห์
- Budget สำหรับ tooling: Sonar, Chromatic, Backstage
- Buy-in จาก engineering leadership ทุกทีม
- คณะกรรมการ RFC review รายไตรมาส

ผมขอย้ำ — investment นี้คุ้มค่า ดู ROI ใน slide ที่แล้ว

---

## Slide 29 — Next Steps & Q&A

**เวลา: 1 นาที + Q&A 10 นาที**

ถ้าได้ green light วันนี้ — Week 0-2 จะ:

- ตั้งทีม Platform
- เลือก pilot squad
- ทำ tech radar workshop

ติดต่อ: **Bundit Rattanang @shode**

ขอบคุณทุกคนที่ฟังจนจบ — เปิด floor สำหรับคำถามและ discussion

หัวข้อที่พร้อมตอบ:
- Pilot scope details — เลือก squad ไหน criteria ยังไง
- Team structure — platform team ขึ้นกับใคร
- Tooling choices — ทำไมเลือกตัวนั้นไม่ใช่ตัวนี้
- Migration จาก state ปัจจุบัน

---

## Appendix — Tips การ Pitch

**Tone**
- พูดในฐานะ "เพื่อนร่วมทีม" ไม่ใช่ "ครู"
- ยอมรับ trade-off อย่างจริงใจ ไม่ขายของ
- เปิดให้ challenge ทุก slide

**Pacing**
- Slide 4 (Mental Model) ใช้เวลาตั้งภาพให้ชัด — ถ้าจับภาพได้ทุกอย่างจะตามง่าย
- Slide 10 (How They Work Together) เป็น "wow moment" — เน้นพิเศษ
- Slide 23 (A Day in the Life) ค่อยๆ เล่า ให้คนเห็นภาพ workflow จริง

**ตอบคำถามยาก**

> "ทำไมไม่ใช้แค่ Cursor / Copilot อย่างเดียว?"

→ Tool-agnostic philosophy: rules อยู่ใน Markdown ใช้กับ AI ได้ทุกตัว ไม่ผูกใคร เปลี่ยน tool ก็ใช้ rules เดิมได้

> "Platform team จะกลายเป็น bottleneck ไหม?"

→ Self-service + community contribution + RFC process — platform team set foundation แต่ feature เพิ่มได้จากทุกทีม

> "Junior dev จะเรียนรู้ engineering พื้นฐานยังไง ถ้า AI ทำให้?"

→ AI ไม่ได้ทำให้ — AI scaffold ตาม pattern dev ยัง implement business logic เอง pattern คือสิ่งที่ junior เรียนรู้

**ปิดท้าย**
- ขอ 1 commitment เล็กก่อนเดินออกห้อง — เช่น "อนุมัติ pilot 1 squad?" ไม่ใช่ "ทั้ง program"
- การ convince ทำเป็น iteration — เหมือน framework เอง

---

**End of Script**

Total estimated speaking time: 25–30 นาที (deck) + 10 นาที (Q&A)
