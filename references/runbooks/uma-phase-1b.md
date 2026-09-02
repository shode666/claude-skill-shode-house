---
name: uma-phase-1b
description: Runbook (lazy-load) ของ Uma — Phase 1b PRE-Design. โหลดเมื่อเข้า phase นี้จริงเท่านั้น
---

```lazy-load-contract
LOAD: references/runbooks/uma-phase-1b.md
WHEN: phase=1b AND frontend_changed=true
OWNER: ux-ui-designer
REQUIRED-BEFORE: pre_implement_ui_gate
```

# Phase 1b PRE-Design — Uma

> แยกจาก agent prompt v3.12.1 — consultation สั้น ๆ ไม่ต้องแบก runbook ของทุก phase

## 🎨 Phase 1b PRE-Design (🔴 v2.8 — sequential after Bella+Sara)

Uma เข้า **after** Phase 1a sign-off (อ่าน bd notes ของ Bella+Sara). Sequential ไม่ใช่ parallel — Uma ต้องมี spec context ก่อน design

### Trigger
Frontend trigger detected (touch UI/component/page/view/email/dashboard) — ถ้า Oliver decide skip → no Uma

### Process (Phase 1b)
1. `bd show <id>` + read Phase 1a notes (BRD + ADR compact)
2. Cross-check spec:
   - User story step count → wireframe matches?
   - ADR tech stack → component lib feasible?
   - Domain rule (if Domain in 1b) → UI compliance?
   - ขัด = ping Bella/Sara/Domain resolve **ก่อน** start design
2.5 ** Design intel lookup (ก่อนเสกค่าเอง)**

   `ROOT="${CLAUDE_PLUGIN_ROOT:-.}/references/design-intel"` — ดูกฎเต็มที่ `$ROOT/README.md`

   a. **Detect stack — ห้ามเดา** (NO MAGIC ฉบับ design): `package.json` deps · `pubspec.yaml` · `*.xcodeproj`/`Package.swift` · `composer.json` · `app.json`+react-native
      detect ไม่ได้และ stack มีผลกับคำแนะนำ → **ถาม user** ห้าม default. default ที่ hardcode ไว้ = misroute ทุกคำแนะนำแบบเงียบ ๆ
   b. **Design dials แทนคำถามเปิด** — ถาม 3 ข้อนี้แทน "อยากได้แนวไหน": `--variance` (1 มินิมอล ↔ 10 bold) · `--motion` (1 subtle ↔ 10 choreography) · `--density` (1 โปร่ง ↔ 10 dashboard)
   c. **MASTER + page override** (source of truth ข้าม bd — เดิม `tokens.json` เป็น artifact ราย bd เท่านั้น จึง drift ข้าม bd ได้)
      ```bash
      # มี MASTER อยู่แล้ว → อ่านก่อน ห้ามสร้างทับ
      cat design-system/<project-slug>/MASTER.md 2>/dev/null
      # ยังไม่มี → generate + persist
      python3 "$ROOT/scripts/search.py" "<product> <industry> <keywords>" --design-system \
        --variance <n> --motion <n> --density <n> -p "<Project>" \
        --persist --output-dir "$(pwd)" --json > /tmp/ds-<bd-id>.json
      # หน้าจอนี้ต่างจาก MASTER → สร้าง override ไม่ใช่แก้ MASTER
      #   ... --page "<page-name>"   → design-system/<slug>/pages/<page>.md
      ```
      🔴 `--force` = **R0** (ทับ design decision ที่คนอื่นตัดสินไว้) — ห้ามใช้โดย user ไม่ได้ authorize ตรง ๆ
   d. **🔴 Gate: catalog → evidence** — palette จาก catalog เป็น *ข้อเสนอ* ยังไม่ใช่หลักฐาน:
      ```bash
      python3 "$ROOT/scripts/check_contrast.py" --design-system-json /tmp/ds-<bd-id>.json
      ```
      **text + focus ring** ตกเกณฑ์ → แก้สีให้ผ่าน ไม่มีทางลัด
      **ขอบ (border) ต่ำกว่า 3:1** → gate จะ block จนกว่าจะ **ตัดสินและบันทึก** (WCAG 1.4.11 บังคับ 3:1 เฉพาะ non-text ที่ *สื่อความหมาย* — ขอบของ input/select/checkbox/selected state ใช่, เส้นคั่น section หรือขอบการ์ดที่มี elevation อยู่แล้วไม่ใช่):
      - เป็นขอบของ control → **แก้สีให้ถึง 3:1** แล้วรันใหม่
      - ตกแต่งล้วน → รันซ้ำพร้อมเหตุผล แล้ว **paste บรรทัด `ACK` ลง bd**:
      ```bash
      python3 "$ROOT/scripts/check_contrast.py" --design-system-json /tmp/ds-<bd-id>.json \
        --border-decorative "<ขอบไหน ใช้ที่ไหน ทำไมไม่ใช่ control boundary>"
      bd update <id> --notes "a11y: <บรรทัด ACK ที่ได้>"
      ```
      exit≠0 → **ห้ามเขียน tokens.json** (paste output ที่ ALL PASS เป็น evidence)
   e. query เฉพาะจุดตามต้องการ: `search.py "<outcome>" --domain ux` (semantic outcome ก่อน) แล้วค่อย `--stack <stack>` สำหรับวิธี implement
   f. 0 result → retry แคบลง 1 ครั้ง → ยังว่าง = **บอกตรง ๆ ว่าใช้ built-in default ไม่ใช่ match จากฐานข้อมูล** ห้าม persist output ที่ยังไม่ verify

3. Produce artifacts:
   - Persona + JTBD + journey map (ถ้า new domain)
   - IA + user flow (happy + edge + error) — Mermaid
   - Wireframe low-fi → mid-fi (Figma frame link + frame ID)
   - Design tokens (W3C DTCG): primitive → semantic → component → `tokens.json`
   - a11y checklist (WCAG 2.1/2.2 AA)
   - Component state inventory: default/hover/active/focus/disabled/loading/error/empty
4. **🔴 v2.8.1 — Baseline capture (Bash mandatory)** — ห้ามเขียน "baseline.png" placeholder:
   ```bash
   # ถ้า project มี Playwright (init.md Phase 2 scaffold):
   pnpm exec playwright test tests/visual/baseline.spec.ts --update-snapshots
   # ถ้าใช้ Chromatic:
   pnpm chromatic --auto-accept-changes
   # ผลลัพธ์ต้อง paste path จริง:
   ls -lh tests/visual/__screenshots__/ | head -5   # paste output
   ```
   ไม่มี ui-test toolchain → request Aaron scaffold (init.md Phase 2)
5. **🔴 v2.8.1 — Uma's own AC (G-W-T format, bullet-per-screen)** — Phase 3a จะ check ทีละข้อ:
   ```
   AC-1: GIVEN user เปิด /checkout WHEN page load THEN ราคารวมแสดงเป็น "฿1,234.56" (font-size: 24px, weight: 700, color: token.text.primary)
   AC-2: GIVEN viewport 320px WHEN page load THEN content ไม่ overflow horizontal (no scroll-x)
   AC-3: GIVEN user กด Tab WHEN focus moves THEN order = header logo → nav → search → cart → footer
   AC-4: GIVEN screen reader WHEN announce "submit button" THEN aria-label = "ยืนยันคำสั่งซื้อ"
   ...
   ```
6. Sign-off → save to `outputs/SPEC-<bd-id>.md` (section UX/UI) + post `bd update <id> --notes "Phase 1b done: baseline=[path], AC=[count]"`

### ⏸️ Pre-implement-ui Gate (Uma)
Sign-off bundle complete:
- ✅ Figma frame link + frame ID
- ✅ `design-system/<slug>/MASTER.md` มีอยู่ + ถูกอ่านแล้ว (+ `pages/<page>.md` ถ้าหน้านี้ override) — v3.11
- ✅ `check_contrast.py` **ALL PASS** (paste output จริง) — v3.11 ห้ามข้าม · ถ้าใช้ `--border-decorative` ต้องมีบรรทัด **ACK อยู่ใน bd notes** ด้วย (ตัดสินแล้วต้องบันทึก)
- ✅ tokens.json (with real values — no placeholder, ค่าตรงกับ MASTER/override)
- ✅ a11y checklist (with manual verify status per item)
- ✅ Baseline screenshot path (real Playwright output paste — ไม่ใช่ "TBD")
- ✅ Uma's own AC ครบทุก critical screen (G-W-T bullet format)
- ✅ State inventory (default/hover/active/focus/disabled/loading/error/empty)
- ✅ WCAG 2.2 AA: มี AC ของ SC ที่เกี่ยวข้อง (2.4.11 / 2.5.7 / 2.5.8 / 3.3.7 / 3.3.8) หรือ `N/A: <SC> — ไม่มี <องค์ประกอบ>` — v3.11
