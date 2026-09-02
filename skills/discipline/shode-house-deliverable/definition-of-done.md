---
name: definition-of-done
description: Reference (lazy-load) ของ `shode-house-deliverable` — Definition of Done (verifiable, per owner). โหลดตอนจะ produce/finalize deliverable
---

# Definition of Done (verifiable, per owner)

> แยกจาก `SKILL.md` v3.12.1 — 7 agent preload skill นี้ แต่ส่วนนี้ใช้เฉพาะตอนกำลังจะส่งงานจริง

## ✅ Definition of Done (🔴 verifiable — Oliver enforce ห้ามปิด task)

> Team roster = single source ใน `shode-house-routing` (19 agents, 7 teams)

```
□ Phase 1a Foundation passed (Bella ∥ Sara light cross-read ok, bd notes posted)
□ Phase 1b Expand passed (Uma* sign UI accept + baseline; Domain* sign regulation/rule; integrated SPEC saved)
□ Phase 3a UI Check PASS (Uma verdict before Chris/Quinn เริ่ม)
□ Phase 3b Code Review passed (Chris ∥ Quinn parallel, 0 Critical/Major)
□ Loop iter ≤ 3 + routing precise (code→2, UI→1b, spec→1a); iter > 3 → escalate user
□ Review report posted (bd active → `bd update --notes` ตาม REVIEW template; no bd → `outputs/REVIEW-<feature>.md`). ห้ามเขียนคู่
□ Code merged + CI green (lint+type+unit+integration+SAST+SCA)
□ Contract test pass (Pact/Schemathesis — BE ↔ FE align)
□ Mutation test kill rate ≥ 70% (business logic)
□ Pre-merge integration smoke pass (BE+FE+DB up + curl journey)
□ UI Design (REQUIRED ถ้า frontend/UI changed): Uma wireframe (Figma link/frame ID) + tokens.json + a11y checklist (WCAG AA) attached **ก่อน** Dave start implement
   Evidence: link หรือ path ของ Figma frame + tokens.json + a11y self-audit list
□ UI Test (REQUIRED ถ้า frontend/components/pages/views/*.vue/*.tsx/*.jsx เปลี่ยน หรือ Uma involved): Playwright pass + visual diff approved + axe critical=0
   Evidence: paste Playwright console + screenshot/diff path + axe report path + trace path
□ Load smoke: p95 < SLO, error < 0.1%
□ Deploy staging + Aaron screenshot ✅
□ E2E user journey on staging (Quinn — Playwright trace)
□ Manual UI walkthrough 5 critical screens (Uma)
□ Docker `docker compose up` from clean machine works (Aaron)
□ Feature flag wired + tested both states (if risky)
□ Observability: log/metric/trace + SLO alert configured
□ 🔴 **bd CLOSED with evidence** (M8 Close-on-Done): `bd close <id> --reason "<verdict> <commit_sha> <test_result>"` แล้ว `bd show <id>` อ่านได้ว่า CLOSED
   Evidence: paste output ของ `bd show` — code merged แต่ bd ยัง OPEN = **ยังไม่ done** (stale-open)
```
ขาดข้อใด = ยังไม่ "done" — ห้าม merge ห้าม close bd. ปิดครบแล้วแต่ไม่ paste `bd show` = ยังไม่ done เหมือนกัน
