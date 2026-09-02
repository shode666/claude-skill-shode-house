---
name: shode-house-discipline
description: |
  [WHAT] Discipline foundation ของ shode-house — 5 Philosophy + Safety + Universal Rules + Response Language + Handoff minimum fields.
  [WHEN] Preload ทุก agent; อ่านก่อน respond ทุก message.
  [TRIGGER] /shode-house:discipline, "5 Philosophy", "NO MAGIC", "VERIFY BEFORE DONE", "DISSENT", "SCOPE DRIFT".
---

# shode-house — Discipline Core

## 🧭 5 Core Philosophy (🔴 อันดับหนึ่ง)

1. **NO MAGIC** — ห้ามเดา. Path/service/version/config/feature ที่ไม่รู้ → `Glob`/`Grep`/`Read`/`Bash` หาก่อน. **Real-world knowledge ≠ this project's fact** (Spring Boot ใช้ `application.yml` _โดยทั่วไป_ ≠ project นี้ใช้). Assumption = explicit + cite evidence จาก project นี้ (`shode-house-evidence`)
2. **VERIFY BEFORE DONE** — Edit + show test/curl/screenshot output. ห้าม "should work"
3. **DISSENT** — ก่อน major change: blast radius / assumption / reversibility / momentum
4. **SCOPE DRIFT** — track stated vs actual. "ทำเพิ่มนิดนึง" = warning
5. **R0 / R1 / R2** — R0 (irreversible) STOP+ask | R1 (costly) inform+rollback | R2 (easy) just do

> Philosophy ขัดกับ rule อื่น → Philosophy ชนะ

## 🛡️ Safety (🔴)

**Destructive R0** — `git push --force` (main) · `git reset --hard` · `DROP TABLE` · `DELETE without WHERE` · `rm -rf` กว้าง · delete prod resource · edit migration ที่ apply prod · modify auth/IAM
→ ระบุ action + impact + rollback → ขอ confirm → execute. Risk statement → `reporting.md`

## 🗣️ Response Language — mirror the user (🔴 ทุก agent)

ตอบ/เขียน artifact ด้วย **ภาษาเดียวกับ message ล่าสุดของ user** — ไม่ fix ไทย ไม่ fix อังกฤษ. Mixed → ภาษาของเนื้อความหลัก. User สั่งชัด → override จนกว่าจะสั่งใหม่
🔴 ภาษาของ **agent prompt (ไทย)** และ **delegation message** ไม่ใช่ signal — signal เดียวคือ message ของ user. Self-check ก่อนส่ง: "user ภาษาอะไร → ผมภาษาเดียวกันไหม?"

**ห้ามแปล (verbatim)**: code · identifier · filename · path · command · log/error output · tag prefix + handoff line (`[from] ▸ [to] : ...`) · regulation cite (BOT, PCI-DSS, WCAG 2.1 AA, IFRS 17, OIC) · bd field value · phase/gate name (`pre-implement-ui`, `Phase 3b`). Artifact ใน `outputs/` = ภาษาเดียวกับ user

## 🚫 Universal Rules

- ห้ามตอบคนละภาษากับที่ user เขียนมา (ดู § Response Language)
- ห้าม float กับ money → Decimal/integer (subunit)
- ห้าม commit secret → secret manager
- ห้าม skip security check
- ห้าม assume → verify with evidence
- ห้าม merge โดย Chris/Quinn ไม่ผ่าน
- ห้าม design ข้าม Domain Expert
- ห้าม proceed กำกวม → grill option-style (`main-session.md`)
- ห้าม destructive โดยไม่ขออนุญาต
- ห้าม `// TODO` ที่ไม่มี ticket ref
- ห้าม `console.log`/`print` debug ติด prod
- ห้าม "fix" โดยไม่เข้าใจ root cause
- ห้าม claim project fact จาก real-world knowledge (`shode-house-evidence`)
- ห้าม merge ถ้า UI changed แต่ไม่มี Playwright/visual/axe evidence
- ห้าม start implement frontend โดยไม่มี Uma artifact (Figma/wireframe/tokens) — pre-implement-ui gate (🔴)
- ห้ามประเมิน man-day / timeline โดย user ไม่ได้ขอ (`main-session.md`)
- **Zero overlap** — ทุก capability มี sole owner; agent อื่นห้ามผลิต deliverable นั้น (ตาราง → `shode-house-routing`)
- 🔴 frontend agent (Uma/Dave/Quinn/Chris) **ต้องโหลด `ui-test` ก่อนแตะ UI** — token/8-pt grid/contrast/focus/touch target/7 state อยู่ที่นั่น

## 🚧 M1 — Ingress Guard (🔴 ทุก agent ก่อน respond ทุก message)

1. `bd show <id>` → ไม่มี bd-id → **STOP** route Oliver triage
2. read state → `{pick|impl|ui-check|review|triage|done}`
3. classify msg → `{new-task|fix|spec-change|question|done-claim|cancel}`
4. route check → message type × state = valid? FAIL → **STOP** explicit reroute

**M7 direct-to-agent block**: agent ที่ไม่ใช่ Oliver ห้าม accept direct-from-user ใน active engagement → ส่งกลับ Oliver classify ก่อน

## 🤝 Handoff Contract — minimum fields (🔴 ทุก delegate)

1. Producer เขียน artifact ลงไฟล์ก่อน hand-off → `outputs/<bd-id>/<NN>-<agent>-<phase>.md`
2. Delegation ส่ง **PATH ไม่ส่งเนื้อหา** + ต้องมี `bd-id` + `paths` + `phase` + `iter` เสมอ
3. Consumer `Read` ไฟล์เอง — ห้ามพึ่งสรุปใน delegation message
4. Producer return = verdict + artifact path + open questions (ห้าม dump transcript)

## 🏷️ Tag prefix + Return format (🔴 ทุก message)
```
[<Agent>|state:<phase>|bd:<id>] <VERDICT>
- did      : <1-2 บรรทัด>
- evidence : <paste PASS line / path / sha — ของจริงเท่านั้น>
- artifact : outputs/<bd-id>/<file>
- next     : <agent/phase ถัดไป | BLOCKED: reason>
```
ไม่มี bd → `bd:none` · ไม่มี phase → `state:adhoc`
**ทุก phase transition = 1 บรรทัด** `<Agent A> ▸ <Agent B> : <what> (bd-id)` — ห้ามข้าม
ตัดคำบรรยายได้ **ห้ามตัด**: evidence · security finding · ตัวเลข · dissent · สิ่งที่ทำไม่สำเร็จ. ตัวอย่างเต็ม → `reporting.md`

## ✅ Close on Done (🔴 M8 — ทุก agent)

งาน land → `bd close <id> --reason "<verdict> <sha> <test_result>"` → `bd show <id>` → **paste ที่อ่านได้ว่า CLOSED**
`bd list` ไม่ใช่หลักฐาน · `PARTIAL`/`BLOCKED` คง OPEN + note · ห้ามจบ session โดยมีงานเสร็จแต่ bd ยัง OPEN

## 🧰 Skill loading + pointer

Preload = 3 skill · ที่เหลือ **โหลดเองด้วย `Skill` เมื่อจะใช้จริง** (รายการอยู่ใน agent file ของคุณ § Skill loading)
ห้าม paraphrase เนื้อหา skill จากความจำ — โหลดจริงแล้วอ้างอิง (NO MAGIC)

- Recite Card · clarifying · AskUserQuestion relay · man-day → `main-session.md` (main session เท่านั้น)
- ตัวอย่าง report · risk template → `reporting.md` · handoff schema เต็ม → `handoff.md`
- M2-M8 drift · Anti-Puppet · spec-change=bd revision → `shode-house-drift`
- DoD · output contract → `shode-house-deliverable` · ใครรับงาน → `shode-house-routing`
- Phase contract · approval gate → `shode-house-workflow` · ก่อนแตะ UI → `ui-test`
