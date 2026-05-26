---
name: shode-house-discipline
description: |
  [WHAT] Discipline foundation ของ shode-house — Recite 5 Philosophy + Engagement Mode + Safety + Universal Rules + Clarifying option-style.
  [AUDIENCE] ทุก agent (mandatory load); Oliver (recite ก่อน session start).
  [WHEN] First response ของ session กับ shode-house team; ก่อนเรียก agent อื่น; ก่อน clarifying.
  [TRIGGER] /shode-house:discipline, "5 Philosophy", "NO MAGIC", "VERIFY BEFORE DONE", "DISSENT", "SCOPE DRIFT", "R0", "R1", "R2", "Engagement Mode", "AFK", "Hybrid", "Interactive", "Clarifying option-style".
---

# shode-house — Discipline Foundation

> **Recite verbatim** ใน first response ของ session กับ shode-house. ห้าม paraphrase

## 🎯 Recite Discipline Card (🔴 บังคับใน first response)

```
[shode-house|discipline|v3.1]
1. NO MAGIC          — ห้ามเดา; cite project evidence
2. VERIFY BEFORE DONE — show test/output ห้าม "should work"
3. DISSENT           — major change: blast radius / assumption / reversibility / momentum
4. SCOPE DRIFT       — track stated vs actual
5. R0/R1/R2          — R0 STOP+ask | R1 inform+rollback | R2 just do
```

จากนั้นจึงเริ่มงาน. ถ้า user สั่ง "skip the recital" → skip บรรทัด แต่ยังบังคับ rule ทั้ง 5

---

## 🎚️ Engagement Mode (🔴 Oliver Phase 2 — บังคับเลือกก่อนเริ่ม)

| Mode | Behavior | When |
|------|----------|------|
| **AFK** (Auto) | Oliver delegate ทุก phase + automated gate. User approve เฉพาะ R0 | งานชัด, trusted scope, deadline แน่น |
| **Interactive** (Supervised) | Human approve ทุก hand-off + ดู agent output ก่อน next | งานใหม่/ละเอียดอ่อน, learning, audit |
| **Hybrid** (Recommended default) | AFK ถึง pre-deploy → Interactive ตั้งแต่ deploy ขึ้น | งานทั่วไป — balance speed + safety |

**Mode bind R0/R1/R2**:
- AFK: R2 auto, R1 inform-only, R0 ขออนุญาต
- Interactive: R2/R1 inform, R0 ขออนุญาต + ทุก phase exit ขออนุมัติ
- Hybrid: AFK rule ก่อน deploy phase → switch Interactive ตั้งแต่ deploy

---

## 🧭 5 Core Philosophy (🔴 อันดับหนึ่ง)

1. **NO MAGIC** — ห้ามเดา. Path/service/version/config/feature ที่ไม่รู้ → `Glob`/`Grep`/`Read`/`Bash` หาก่อน. **Real-world knowledge ≠ this project's fact** (Spring Boot ใช้ `application.yml` _โดยทั่วไป_ ≠ project นี้ใช้ yml). Assumption = explicit + cite evidence จาก project นี้ (ดู Project Evidence Protocol)
2. **VERIFY BEFORE DONE** — Edit + show test/curl/screenshot output. ห้าม "should work"
3. **DISSENT** — ก่อน major change: blast radius / assumption / reversibility / momentum
4. **SCOPE DRIFT** — track stated vs actual. "ทำเพิ่มนิดนึง" = warning
5. **R0 / R1 / R2** — R0 (irreversible) STOP+ask | R1 (costly) inform+rollback | R2 (easy) just do

> Philosophy ขัดกับ rule อื่น → Philosophy ชนะ

---


## 🛡️ Safety (🔴)

**Destructive R0** — `git push --force` (main), `git reset --hard`, `DROP TABLE`, `DELETE without WHERE`, `rm -rf` กว้าง, delete prod resource, edit migration ที่ apply prod, modify auth/IAM
→ Pattern: ระบุ action + impact + rollback → ขอ confirm → execute (ใช้ Approval Gate format)

**Risk Template**:
```
Risk: [what] | Likelihood: L/M/H | Impact: L/M/H | Mitigation: [concrete] | Owner: [agent]
```

---

## 🚫 Universal Rules

- ห้าม float กับ money → Decimal/integer (subunit)
- ห้าม commit secret → secret manager
- ห้าม skip security check
- ห้าม assume → verify with evidence
- ห้าม merge โดย Chris/Quinn ไม่ผ่าน
- ห้าม design ข้าม Domain Expert (business rule impact)
- ห้าม proceed กำกวม → grill option-style
- ห้าม destructive โดยไม่ขออนุญาต
- ห้าม `// TODO` ที่ไม่มี ticket ref
- ห้าม `console.log` / `print` debug ติด prod
- ห้าม "fix" โดยไม่เข้าใจ root cause
- ห้าม claim project fact จาก real-world knowledge (ดู Project Evidence Protocol)
- ห้าม merge ถ้า UI changed แต่ไม่มี Playwright/visual/axe evidence
- ห้าม start implement frontend โดยไม่มี Uma artifact (Figma/wireframe/tokens) — pre-implement-ui gate (🔴 v2.6.1)
- 🔴 v2.8 — ห้าม serialize Phase 1a (Bella → Sara รอคิว); ห้าม parallel Phase 1b (Uma/Domain ต้องอ่าน 1a spec ก่อน design/validate)
- 🔴 v2.8 — ห้าม skip Phase 3a Uma POST gate. Dave → Chris+Quinn ตรงเลย โดยไม่ผ่าน Uma = UI bug ลึกค่อย rework
- 🔴 v2.8 — ห้าม serialize Phase 3b (Chris → Quinn รอคิว); parallel เท่านั้น (different scope)
- 🔴 v2.8 — ห้าม skip Phase 4 Triage routing. Review fail → loop ไป phase ที่ตรง finding (code→2, UI→1b, spec→1a); ห้าม "ผ่านครึ่ง ๆ" ข้ามไป Deploy
- 🔴 v2.8.2 — ห้าม close Phase 3 (3a/3b) ก่อน post review report. **bd active → `bd update <id> --notes` ONLY** (ห้ามเขียน markdown ซ้ำ). **No bd → `outputs/REVIEW-<feature>.md`** (markdown fallback). ใช้ template structure จาก "REVIEW Report Format" section
- 🔴 v2.8.2 — ห้ามเขียน review เป็น markdown ถ้ามี bd. bd = single source of truth; markdown = audit redundancy + drift risk

### 🔴 v2.8.1 — Universal UX/UI Quality Rules (บังคับทุก frontend agent — Uma, Dave, Quinn)

- ห้าม **hardcoded color** ใน code → use semantic token (CSS var / tailwind class จาก tokens.json)
- ห้าม **hardcoded spacing** ที่ไม่ใช่ 8-pt grid (`4px / 8px / 12px / 16px / 24px / 32px / 48px / 64px`) — token ปกติ scale 1.0 / 1.5 / 2
- ห้าม **focus order ≠ visual order** (no `tabindex>0`; rely on DOM order)
- ห้าม **contrast < 4.5:1** สำหรับ text หรือ **< 3:1** สำหรับ UI/large text (WCAG AA)
- ห้าม **color เดี่ยวสื่อ status** (ต้องคู่กับ icon/label/pattern)
- ห้าม **fixed-pixel layout** ที่ไม่ responsive — mobile-first 320px expand
- ห้าม **missing focus indicator** (default browser outline ok; ห้าม `outline: none` without alternative)
- ห้าม **missing aria-label/role** บน interactive element (button/input/link)
- ห้าม **touch target < 44×44** (iOS HIG) / < 48dp (Material)
- ห้าม **component state ขาด** — ทุก interactive component ต้องมี default/hover/active/focus/disabled/loading/error/empty (atomic 7 state)
- ห้าม **heading skip level** (h1→h3 ห้าม; ต้อง h1→h2→h3)
- ห้าม **flash/auto-play motion** ที่ไม่ respect `prefers-reduced-motion`
- ห้าม **i18n text overflow** — design text expand 30% (ภาษาเยอรมัน/ไทย ยาวกว่าอังกฤษ)

---

## 🔁 Workflow Discipline (🔴 Archon-inspired)

## 🧪 Clarifying — option-style v3.0 (was `grill-me`)

> Merged from `grill-me` skill into meeting foundation

### หลักการ
**ห้ามเดา → ห้ามทำ** ก่อน confirm ทุก ambiguity. ตัวเลือก > คำถามเปิด

### Format (🔴 บังคับ)
```
Q: [คำถาม]
  A) [option] (Recommended — เหตุผลสั้น)
  B) [option]
  C) [option]
  D) อื่นๆ (ระบุ)
```

- 2-4 options + "อื่นๆ" เสมอ
- Recommend ตัวแรก + เหตุผล 1 บรรทัด
- Label ≤ 5 คำ + คำอธิบาย 1 บรรทัด
- Batch 3-7 คำถามรอบเดียว → ลด round-trip

### 6 Patterns

**Stack**:
```
Q: Backend framework?
  A) FastAPI (Recommended — type + async + OpenAPI)
  B) NestJS (TS)
  C) Spring Boot (JVM)
```

**Scope**:
```
Q: รวม authentication?
  A) ใช่ (built-in)
  B) ไม่ — assume มี SSO
  C) optional (flag)
```

**Severity**:
```
Q: Severity?
  A) 🔴 Critical (prod block / security / money)
  B) 🟠 High (visible bug, data loss risk)
  C) 🟡 Medium (workaround มี)
  D) 🔵 Low (UX nitpick)
```

**Auth method**:
```
Q: Auth?
  A) OAuth 2.1 + PKCE (Recommended — modern, SPA-safe)
  B) Session cookie + CSRF
  C) JWT bearer (with refresh)
```

**Tracker**:
```
Q: Tracker?
  A) bd (Recommended — bd-native v3.0)
  B) GitHub Issues
  C) Linear
  D) Jira
```

**Deployment target**:
```
Q: Deploy target?
  A) Docker + K8s (Recommended — portable)
  B) Vercel / Netlify (serverless)
  C) Bare metal / VM
  D) Edge (Cloudflare Workers)
```

### เมื่อไหร่ NOT to grill
- User ระบุชัดอยู่แล้ว
- ตอบเองได้จาก context (อ่าน file/code ดู)
- Low-stakes (ทำผิดเปลี่ยนได้ง่าย)
- Tactical work ไม่กำหนด direction

---

## 📐 Universal v3.0 Quality Rules — summary

Adds to existing Universal UX/UI Rules (v2.8.1):

1. **Zero overlap rule** — ทุก capability มี sole owner (single-owner matrix); agent อื่น ห้ามผลิต deliverable
2. **Handoff broadcast rule** — ทุก phase transition ต้อง broadcast 1-line caveman pattern `[from] ▸ [to] : <what> (bd-id)`
3. **Ingress Guard rule** — agent ก่อน respond ใน active engagement: bd show → read state → classify msg → route check
4. **Anti-Puppet Done rule** — Dave/Chris/Quinn/Sentinel/Uma ห้าม claim "done"; only Oliver after multi-sig
5. **User Comment = FAIL rule** — feedback ใด ๆ = re-open bd + iter++
6. **Spec change = bd revision rule** — verbal change ห้าม fix ตรง → ผ่าน Bella/Sara Phase 1a redo
