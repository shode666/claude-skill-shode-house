# Part 1 — ทำไมต้องคิดเรื่อง AI Agent ใน Software House ตอนนี้

> เวอร์ชันสั้น: ถ้าองค์กรของคุณใช้ AI tools อยู่แล้วโดยไม่มีกฎร่วมกัน คุณกำลังจ่ายเงินรายเดือนเพื่อสร้าง technical debt ให้เร็วขึ้น แต่ฟังดูทันสมัยดี

## บทนำ: ปัญหาไม่ใช่ "พิมพ์ช้า"

ทุกครั้งที่มีคนเล่าให้ฟังว่าทีมตัวเองเพิ่งซื้อ AI seat ให้ developer 30 คน ผมจะถามคำถามเดียว:

> "ก่อนใช้ AI ทีมพังเพราะอะไรครับ"

ส่วนใหญ่ตอบคล้าย ๆ กัน:
- requirement ไม่ชัด
- code review ช้า
- test ไม่ครอบคลุม
- architecture drift
- documentation ไม่ update
- knowledge อยู่ในหัว senior 2-3 คน
- บั๊ก production แบบเดิมซ้ำทุก 6 เดือน

ไม่มีใครตอบว่า "เพราะ developer พิมพ์ช้า"

แต่เครื่องมือ AI ส่วนใหญ่ที่ขายในตลาดวางตัวเองเป็น "เครื่องช่วยพิมพ์โค้ดให้เร็วขึ้น" ซึ่งแก้ปัญหาที่ทีมของคุณไม่ได้มีตั้งแต่แรก พอทีมได้เครื่องมือใหม่ที่ไม่ตรงปัญหา ผลที่เกิดขึ้นคือ "พิมพ์เร็วขึ้นจริง แต่พิมพ์ผิดทรงเร็วขึ้นด้วย"

นั่นคือเหตุผลที่ AI Agent ใน Software House ไม่ควรถูกมองเป็น "เครื่องมือเขียนโค้ด" แต่ควรเป็น "ระบบที่ช่วยควบคุมคุณภาพของงานที่ AI ช่วยสร้าง"

---

## 1. ตัวเลขที่บอกว่ามีปัญหาแน่ ๆ

### 1.1 Adoption สูง แต่ trust ยังต่ำ

Stack Overflow Developer Survey 2025 รายงานว่า developer จำนวนมาก (ตัวเลขแตะระดับสูงสุดในประวัติของ survey) ใช้หรือวางแผนใช้ AI tools ในงานประจำวัน แต่ในเวลาเดียวกัน "ความไว้ใจในความถูกต้องของ AI output" กลับ **ต่ำกว่า** ปีก่อน

ปัญหาที่ developer รายงานบ่อยที่สุด 3 ข้อ:

1. **AI ตอบ "เกือบถูก แต่ไม่ถูก"** — ผ่านตา compile ได้ ทำงานได้ใน happy path แต่พังที่ edge case
2. **Debug AI-generated code ใช้เวลานานกว่าเดิม** — เพราะ developer ไม่ได้คิดตามตอนเขียน เลยไม่มี mental model
3. **AI ตอบมั่นใจเกินจริง** — "ผมแน่ใจว่าวิธีนี้ใช้ได้" ทั้งที่ใช้ไม่ได้

ใน software house เราไม่ได้เขียน demo เล่น เราเขียนระบบที่ต้อง maintain 5-10 ปี, audit ได้, deploy ได้, support ได้ และมีคนรับผิดชอบเมื่อ production พังตอนตี 3 — ความ "เกือบถูก" จาก AI จึงราคาแพงกว่าใน enterprise มาก

### 1.2 DORA 2025: AI คือ Amplifier ไม่ใช่ Equalizer

DORA State of AI-assisted Software Development 2025 อธิบายผลที่ผมคิดว่าทุก engineering leader ควรอ่านอย่างน้อย 1 ครั้ง:

> AI เป็น **amplifier** — มันขยายทั้งจุดแข็งและจุดอ่อนขององค์กร

แปลตรง ๆ:

- ถ้าองค์กรมี engineering practice ดี (CI แน่น, test ครอบคลุม, architecture ชัด, documentation update) AI จะช่วยให้ flow เร็วขึ้นจริง
- ถ้าองค์กรมี requirement เละ, architecture ไม่ชัด, CI ไม่แน่น, documentation ไม่ update — AI จะช่วยผลิต **ความเละในอัตราเร่ง**

พูดแบบไม่ประดิษฐ์: AI ไม่ได้แก้ระบบที่ไม่มีวินัย แต่มันทำให้ระบบที่ไม่มีวินัย **พังเร็วขึ้น**

นี่คือสาเหตุที่หลายทีมรู้สึกว่า "ใช้ AI แล้วทำไมไม่เร็วขึ้น" — เพราะถ้าฐานเดิมคือทรายลูกรัง ไม่ว่ารถจะเร็วแค่ไหน มันก็ไปไม่ได้

### 1.3 Sonar / SAST รายงาน: AI-generated code มี security issue ระดับสำคัญ

รายงาน State of Code ของ Sonar และเอกสาร AI Code Assurance ในปี 2025 ระบุ pattern ที่เห็นซ้ำ ๆ ใน AI-generated code:

- **String concatenation SQL** — แทบไม่หายไปจาก output ของ LLM ใด ๆ ถ้าไม่ได้สั่งโดยเฉพาะ
- **Missing input validation** — โดยเฉพาะกับ field ที่ตั้งชื่อกึ่งทางการ เช่น `keyword`, `query`, `comment`
- **Silent error swallowing** — `try/catch` ที่ catch ทุกอย่างแล้วไม่ทำอะไร
- **Insecure direct object reference** — endpoint รับ `userId` จาก request โดยไม่ตรวจสิทธิ์
- **Logging sensitive data** — log token, password, citizen ID ออกมาเฉย ๆ

ข้อสังเกตคือ AI **ไม่ได้คิด threat model** มันคิดแค่ "code นี้รันได้ไหม" ซึ่งคือมุมมองของ junior dev สัปดาห์แรก

---

## 2. ปัญหาเชิงระบบที่ AI จะเร่งให้เกิดเร็วขึ้น

ลองนึกภาพทีม 10 คนใน software house ทั่วไป ที่เพิ่งได้ AI tool ใหม่ใช้

แต่ละคนเปิด AI ขึ้นมาแล้วสั่งด้วย prompt ของตัวเอง:

- "ช่วยเขียน API เพิ่ม user"
- "generate service class"
- "ทำ React form ให้หน่อย"
- "เขียน unit test ให้สวย ๆ"
- "refactor ให้ clean"

แต่ละ prompt เปิด context window ของตัวเอง ไม่รู้จัก:
- coding standard ของบริษัท
- internal SDK
- design system
- API response convention
- security checklist
- test pattern

ผลที่ออกมาเดาได้:

| Area | สิ่งที่ได้จาก 10 prompts |
|---|---|
| Naming | `UserService`, `UserManager`, `UserUseCase`, `UserHandler`, `UserBiz` ปนกันใน 1 repo |
| API response | `{ data }`, `{ result }`, `{ payload }`, raw object — เลือกได้เลย |
| Error handling | บางคน throw, บางคน return null, บางคน catch แล้ว log เงียบ |
| HTTP client | บางคนใช้ `axios.get()` ตรง ๆ บางคนใช้ internal `apiClient` |
| Auth | บาง endpoint ลืม `@RequiresPermission` |
| Logging | บางจุด log sensitive data เพราะ AI ใส่ `logger.info(user)` ให้ |
| Test | test ผ่านแต่ไม่ได้ assert business rule จริง — แค่ `expect(result).toBeDefined()` |

นี่ยังไม่นับว่า AI จะ **invent library ที่ไม่มีอยู่จริง** สั่ง install แล้ว `ENOENT` ก็เคยเกิด หรือ AI สร้าง column `customer_type` ทั้งที่ในระบบมี `customer_category` อยู่แล้วเพราะ AI มองไม่เห็น schema

ผลกระทบชั้นที่สอง:

- **Code review ยาวขึ้น** — เพราะ reviewer ต้องตรวจ style ก่อน logic
- **Senior dev ต้องแก้ pattern ซ้ำ ๆ** — ทำงานเหมือนหุ่น ESLint ที่กินเงินเดือน
- **PR merge ช้าลง** — แม้ดูเหมือนจะมี PR เปิดเร็วขึ้น
- **Technical debt เพิ่ม** — แต่กระจายตัว อาจไม่เห็นในไตรมาสแรก
- **Reviewer หมดไฟ** — เริ่มเขียน "approve ตามที่ AI generate" เพื่อให้จบ ๆ ไป

ทีมรู้สึกว่า AI ช่วย dev แต่ทำร้าย reviewer ซึ่งเป็นความรู้สึกที่ตรงกับความจริง

---

## 3. ทำไม "ใช้ AI ดี ๆ" ถึงไม่พอ

หลายองค์กรพยายามแก้ปัญหานี้ด้วยการอบรม "วิธี prompt ให้ดี" แล้วคาดหวังว่าทุกคนจะ prompt เก่งขึ้น

ปัญหาของแนวทางนี้มี 3 ข้อ:

### 3.1 Prompt skill ไม่ scale

Senior 1 คน prompt เก่ง = ดี
Senior 1 คน prompt เก่ง + Junior 9 คน prompt มั่ว = องค์กรของคุณตอนนี้

การ training ทำให้ค่าเฉลี่ยขึ้น แต่ไม่ทำให้ค่าต่ำสุดขึ้น และค่าต่ำสุดต่างหากที่กำหนดคุณภาพของ codebase ทั้งระบบ

### 3.2 Knowledge อยู่ในหัวคน prompt ไม่ใช่ใน organization

ถ้า senior หนึ่งคน prompt ได้ดีเพราะรู้กฎทั้งหมด — กฎเหล่านั้นไม่ได้ถูกบันทึก พอ senior คนนี้ลาออก ความรู้นั้นหายไปกับเขา และ junior 9 คนต้องเรียนใหม่จากศูนย์ คุณกำลังพึ่งพา tribal knowledge มากกว่าก่อนใช้ AI ด้วยซ้ำ

### 3.3 AI ไม่รู้กฎบริษัท ต่อให้ prompt ดีแค่ไหน

ต่อให้ prompt ระดับเทพ AI ก็ไม่รู้ว่า:
- บริษัทมี `<Button />` component ใน `@company/ui` แล้ว
- API ต้อง return `ApiResponse<T>` ตาม convention
- ทุก write action ต้องเขียน audit log
- `customer_category` คือ field มาตรฐาน ไม่ใช่ `customer_type`

ความรู้พวกนี้ไม่ได้อยู่ใน prompt — มันต้องอยู่ใน **context layer** ที่ AI เข้าถึงได้ตลอดเวลา

นี่คือเหตุผลที่ทุกซีรีส์นี้จะวนกลับมาที่คำว่า **AI Engineering Handbook + MCP + Skill + Enforcement**

---

## 4. เป้าหมายที่ใช้งานจริง: AI = "พนักงานใหม่ที่ onboarding แล้ว"

ผมชอบใช้ analogy นี้กับทีม

ลองนึกภาพคุณรับ junior dev ใหม่เข้าทีม วันแรกเขาควร:

1. ได้รู้กฎของบริษัท (handbook, coding standard)
2. ได้สิทธิ์เข้าระบบที่จำเป็น (Jira, Wiki, Git)
3. มี mentor ตอบคำถามได้
4. มี checklist สำหรับงานซ้ำ
5. ส่งงานผ่าน review + CI ก่อน merge
6. ทำผิดได้แต่จับได้ก่อนถึง production

นี่คือ "พนักงานใหม่ที่ onboarding แล้ว"

ถ้าคุณรับพนักงานใหม่โดย **ไม่** onboarding — ให้ commit เข้า main วันแรกเลย — ผลลัพธ์คือหายนะ

แต่นี่คือสิ่งที่หลายองค์กรทำกับ AI ตอนนี้ คือเปิด AI tool ขึ้นมาแล้วให้ generate code เข้า production โดยไม่มี onboarding, ไม่มี handbook, ไม่มีการตรวจสิทธิ์, ไม่มี checklist

แทนที่จะมี junior 1 คนที่ยังไม่รู้กฎ คุณกำลังมี **junior 1,000 คนที่ commit เข้า main ได้พร้อมกัน** แถมยังบอกว่า "อย่าห่วง ผมแน่ใจมาก"

เป้าหมายของ AI Agent ใน Software House จึงไม่ใช่ "ให้ AI เร็วที่สุด" แต่ "ให้ AI ทำตัวเหมือนพนักงานที่ onboarding แล้ว"

---

## 5. แนวทางที่ใช้งานได้จริง — 5 เสาหลัก

ก่อนเข้ารายละเอียดในตอนต่อ ๆ ไป สรุปแนวทางหลักของซีรีส์นี้ไว้ก่อน

### เสาที่ 1 — AI Engineering Handbook (machine-readable)

ไม่ใช่เอกสาร wiki ที่อ่านสนุกในชั่วโมง onboarding แล้วลืม — แต่เป็นไฟล์ที่ AI tool อ่านอัตโนมัติทุกครั้งก่อน generate code เช่น `CLAUDE.md`, `AGENTS.md`, `.cursorrules`, `.github/copilot-instructions.md`

ในตอนที่ 4 จะอธิบายว่าควรเขียนเป็น single source แล้ว generate ออกหลาย format

### เสาที่ 2 — เชื่อม AI กับระบบเดิมผ่าน MCP / API / RAG

AI ที่ไม่เห็น Jira ticket, Wiki, Git, DB schema, API catalog, component catalog = AI ที่ไม่รู้บริบท = AI ที่ตอบ generic เหมือน Stack Overflow

MCP (Model Context Protocol) คือมาตรฐานที่ทำให้ AI เข้าถึงข้อมูลของบริษัทได้แบบมีสิทธิ์ควบคุมได้ จะลงรายละเอียดในตอน 4 และ 5

### เสาที่ 3 — Skill / Agent Workflow สำหรับงานซ้ำ

แทนที่จะให้ทุกคน prompt เอง สร้าง slash command มาตรฐาน เช่น `/from-ticket`, `/scaffold-resource`, `/review-before-pr`, `/security-audit`, `/impact-analysis`

แต่ละ command มี workflow ตายตัว: load handbook → query MCP → generate ตาม template → run check → return ผล — ใครใช้ก็ได้ผลลัพธ์ใกล้เคียงกัน

### เสาที่ 4 — Enforcement Layer ที่ deterministic

AI review ดี แต่ไม่ deterministic ครั้งนี้บอกผ่าน อีกครั้งบอกไม่ผ่าน — เป็น nightmare สำหรับ CI

หลักสำคัญ: **AI ตรวจได้ แต่ตัวตีกลับต้อง deterministic**

ใช้ linter, unit test, contract test, SAST, dependency scan, architecture test (เช่น ArchUnit) เป็นชั้นล่างสุดที่บอก "ผ่าน/ไม่ผ่าน" อย่างชัดเจน

### เสาที่ 5 — วัดผลด้วย metric ที่จับต้องได้

ไม่ใช่ "developer happiness" อย่างเดียว แต่:
- review time (PR open → merge)
- first-pass PR rate
- defect leakage
- onboarding time ของคนใหม่
- standard drift (จำนวน repo ที่ใช้ rule version เก่า)
- time-to-feature

ถ้าวัดไม่ได้ ก็พิสูจน์ไม่ได้ว่า AI ช่วยจริง และจะตอบ CFO ตอน budget review ยาก

---

## 6. เช็คลิสต์ก่อนซื้อ AI seat เพิ่มอีก 100 ที่

ก่อนจะซื้อ license เพิ่มหรือเปลี่ยน vendor ลองตอบคำถามชุดนี้ในใจ:

1. ทีมมี **single source coding standard** ที่ machine-readable หรือยัง
2. AI ของเรา**เห็น Jira ticket** ที่ developer กำลังทำอยู่หรือไม่
3. AI ของเรา**เห็น component catalog / API catalog** หรือไม่
4. PR check ของเราจับได้หรือไม่ ถ้า AI generate `axios.get()` แทน internal client
5. ถ้า junior dev ใหม่เข้าทีมพรุ่งนี้ เราจะ onboard เขายังไง — แล้ว AI ของเราได้รับ onboarding แบบเดียวกันหรือยัง
6. ถ้า AI commit code ที่มี SQL injection เข้า production เรารู้ภายในกี่นาที
7. ถ้า senior คน prompt เก่งที่สุดในทีมลาออกพรุ่งนี้ — ความรู้ของเขาอยู่ในเอกสารหรืออยู่ในหัว
8. มี dashboard ที่ตอบได้ไหมว่า "เดือนนี้ AI ช่วยลด review time ลงเท่าไร"

ถ้าตอบ "ไม่" 5 ข้อขึ้นไป — การเพิ่ม seat อาจไม่ใช่การลงทุนที่ดีที่สุดในไตรมาสนี้

---

## 7. สรุป Part 1

ใจความหลักของตอนนี้ 5 ข้อ:

1. **AI ไม่ได้แก้ปัญหาว่า "พิมพ์ช้า"** เพราะปัญหาจริงของ software house ไม่ใช่ความเร็วการพิมพ์
2. **AI เป็น amplifier** — ขยายทั้งจุดแข็งและจุดอ่อน
3. **Trust ในผลของ AI ลดลง** ทั้งที่ adoption สูงขึ้น เพราะ "เกือบถูก" คือคุณสมบัติพื้นฐาน
4. **Prompt training ไม่พอ** — ความรู้ต้องไหลผ่าน handbook + MCP ไม่ใช่ติดอยู่ในหัว senior
5. **เป้าหมายคือ AI ที่ onboarding แล้ว** ไม่ใช่ AI ที่เร็วที่สุด

ในตอนต่อไป (Part 2) เราจะลงไปดู 10 use case จริงที่เกิดขึ้นในองค์กรที่ใช้ AI โดยไม่มีระบบ — แต่ละ case มาพร้อมกับ "ปัญหา → ผลกระทบ → วิธีแก้ → before/after" ที่จะช่วยให้คุณวินิจฉัยว่าทีมตัวเองอยู่ตรงไหนของ spectrum

ถ้าอ่านจบ Part 2 แล้วรู้สึกว่า "เคยเจอ" หลายเคส — ยินดีต้อนรับครับ คุณไม่ใช่คนเดียว แต่เป็นบริษัทแรก ๆ ที่ยอมรับว่าเจอ
