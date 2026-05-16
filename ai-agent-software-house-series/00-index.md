# AI Agent ใน Software House — ซีรีส์ 6 ตอน

> จาก "เขียนโค้ดเร็วขึ้น" ไปสู่ "ควบคุมคุณภาพของงานที่ AI ช่วยสร้าง"

ซีรีส์นี้เกิดจากคำถามที่ผมได้ยินบ่อยที่สุดในปี 2025-2026 ว่า "เราซื้อ Copilot/Cursor/Claude Code ให้ทีมแล้ว ทำไม productivity ยังไม่ขึ้น" คำตอบสั้น ๆ คือ AI ไม่ได้แก้ปัญหาที่องค์กรไม่มีวินัย — มันเร่งความเร็วของการพังให้เร็วขึ้นเฉย ๆ

ส่วนคำตอบยาวอยู่ในซีรีส์นี้ครับ

## โครงซีรีส์

| ตอน | ชื่อ | สำหรับใคร |
|---|---|---|
| Part 1 | ทำไมต้องคิดเรื่องนี้ตอนนี้ — AI as Amplifier | CTO, Engineering Manager, Tech Lead |
| Part 2 | 10 Use Cases จริงเมื่อ AI เข้า codebase แบบไม่มีระบบ | ทุก role ที่ต้องอยู่กับ AI-generated code |
| Part 3 | Role-by-Role Playbook — PM, BA, SA, UX, Dev, QA, DevOps | Practitioner ทุก role |
| Part 4 | Architecture ของ AI Agent Platform — 6 Pillars + Building Blocks | Platform team, Solution Architect |
| Part 5 | Governance, Security & Anti-Patterns | Security, Compliance, Engineering Leader |
| Part 6 | Roadmap 12 สัปดาห์ + Implementation Examples + ROI | คนที่ต้องลงมือจริง |

## วิธีอ่าน

- ถ้าเป็นผู้บริหาร / ผู้ตัดสินใจ: อ่าน Part 1 + Part 5 + Part 6
- ถ้าเป็น Tech Lead / Architect: อ่าน Part 1 → Part 4 → Part 6
- ถ้าเป็น Practitioner: อ่าน Part 2 → Part 3 ตาม role ของคุณ
- ถ้าอยากอ่านครบ: ตามลำดับ 1 → 6

## หลักคิด 5 ข้อที่จะเจอตลอดซีรีส์

1. **AI ไม่ใช่ซิลเวอร์บูลเล็ต มันคือ amplifier** — ขยายทั้งจุดแข็งและจุดอ่อน
2. **AI ที่ไม่รู้กฎบริษัท = พนักงานใหม่ที่ยังไม่ onboarding** — แต่ commit เข้า main ได้
3. **AI review ช่วยได้ แต่ตัวตีกลับต้อง deterministic** — linter, test, CI ไม่ใช่ความเห็นลอย ๆ ของ model
4. **MCP คือบัตรเข้าระบบของ AI** — ให้สิทธิ์น้อย ๆ ไว้ก่อน อย่าให้ root จากวันแรก
5. **เป้าหมายไม่ใช่ AI แทนคน แต่ลด context-switching ของคน** — คนทำงานยากขึ้น AI ทำงานน่าเบื่อแทน

## References

- Stack Overflow Developer Survey 2025
- DORA State of AI-assisted Software Development 2025
- GitHub Copilot custom instructions documentation
- Model Context Protocol (MCP) documentation
- Atlassian Rovo MCP Server
- Sonar State of Code / AI Code Assurance
- OWASP Top 10 for LLM Applications

---

*หมายเหตุ: บทความซีรีส์นี้เน้นแนวทาง vendor-neutral ตัวอย่าง code/instruction ใช้ได้กับ Copilot, Cursor, Claude Code, Continue, Aider หรือ agent tool อื่น ๆ ที่อ่าน instruction file ได้*
