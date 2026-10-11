---
name: design-phase-1b
description: Runbook (lazy-load) ของ `design` — Phase 1b PRE-Design. โหลดเมื่อเข้า phase นี้จริงเท่านั้น
---

```lazy-load-contract
LOAD: references/runbooks/design-phase-1b.md
WHEN: phase=1b AND frontend_changed=true
OWNER: design
REQUIRED-BEFORE: pre_implement_ui_gate
```

# Phase 1b PRE-Design — `design`

> แยกจาก agent prompt v3.12.1 — consultation สั้น ๆ ไม่ต้องแบก runbook ของทุก phase

Use confirmed record homes, existing design decisions and actual host tools. You have
no Bash: every design script runs through a design-run request (below), executed by the
role the router dispatches. Missing tooling is a stated evidence limitation, not
permission to install a toolchain or invent a passing result.

## Design-run request (the only way a design script runs)

- Write `outputs/<task>/<NN>-ux-design-run-request-1b-iter<n>.json` = `{"schema": 1, "task": "<task id>", "phase": "1b", "iter": <n>, "runs": [{"id": "r1", "script_id": "<template>", "params": {…}}]}`.
- `script_id` = a template of `references/design-intel/scripts/design_run_catalogue.json` whose `phases` include `1b`; `params` = exactly the names and types that template declares. Never a command line, a path, a non-loopback URL or a param starting with `-`.
- At most the catalogue's `max_runs` runs, and keep them within the runner's per-invocation budget (`RUN_BUDGET_S` in `design_run.py`); more work → a second request.
- The router writes the order and its sha256 and relays the report path and sha256. Cite that report, never your request.
- Exit 3 = `BLOCKED: <token> <detail>`, relayed verbatim: fix the request (schema, param) or tell the router what blocks it (missing toolchain → `operate` (deploy mode) scaffold, init.md Phase 2). The details are open-ended; never read them against a fixed list.
- Runner, report and executor detail: `references/design-intel/README.md` § Design runner.

## 🎨 Phase 1b PRE-Design (🔴 v2.8 — sequential after `plan` (requirements mode)+`plan` (architecture mode))

`design` เข้า **after** Phase 1a sign-off (อ่าน task notes ของ `plan` (requirements mode)+`plan` (architecture mode)). Sequential ไม่ใช่ parallel — `design` ต้องมี spec context ก่อน design

### Trigger
Frontend trigger detected (touch UI/component/page/view/email/dashboard) → `design` ตาม harness; explicit user/project/host scope takes precedence over plugin defaults, and omitted checks are recorded rather than claimed passed

### Process (Phase 1b)
1. Read the task + Phase 1a notes (BRD + ADR compact)
2. Cross-check spec:
   - User story step count → wireframe matches?
   - ADR tech stack → component lib feasible?
   - Domain rule (if Domain in 1b) → UI compliance?
   - ขัด = ping `plan` (requirements/architecture)/Domain resolve **ก่อน** start design
2.5 ** Design intel lookup (ก่อนเสกค่าเอง)** — กฎเต็มที่ `references/design-intel/README.md`

   a. **Detect stack — ห้ามเดา** (NO MAGIC ฉบับ design; Read/Glob): `package.json` deps · `pubspec.yaml` · `*.xcodeproj`/`Package.swift` · `composer.json` · `app.json`+react-native
      detect ไม่ได้และ stack มีผลกับคำแนะนำ → **ถาม user** ห้าม default. default ที่ hardcode ไว้ = misroute ทุกคำแนะนำแบบเงียบ ๆ
   b. **Design dials แทนคำถามเปิด** — reuse existing design preferences; ถ้ายังต้องเลือก direction ถามเฉพาะค่าที่ขาด: `variance` (1 มินิมอล ↔ 10 bold) · `motion` (1 subtle ↔ 10 choreography) · `density` (1 โปร่ง ↔ 10 dashboard) = params ของ run
   c. **MASTER + page override** (source of truth ข้าม bd — เดิม `tokens.json` เป็น artifact ราย bd เท่านั้น จึง drift ข้าม bd ได้)
      - Read `design-system/<project-slug>/MASTER.md` ก่อน — มีอยู่แล้ว → ห้ามสร้างทับ
      - ยังไม่มี → run `design-persist` (`query` = "<product> <industry> <keywords>", `variance`, `motion`, `density`, `project`)
      - หน้าจอนี้ต่างจาก MASTER → `design-page` (+ `page` slug) → `design-system/<slug>/pages/<page>.md` ไม่ใช่แก้ MASTER
      🔴 ทับ design decision ที่คนอื่นตัดสินไว้ = **R0**: the catalogue never passes `--force`; overwriting a decided MASTER is the user's decision outside the runner
   d. **🔴 Gate: catalog → evidence** — palette จาก catalog เป็น *ข้อเสนอ* ยังไม่ใช่หลักฐาน: in the same request, `contrast-check` with `ds` = the id of the `design-search` / `design-persist` run
      **text + focus ring** ตกเกณฑ์ → แก้สีให้ผ่าน ไม่มีทางลัด
      **ขอบ (border) ต่ำกว่า 3:1** → gate จะ block จนกว่าจะ **ตัดสินและบันทึก** (WCAG 1.4.11 บังคับ 3:1 เฉพาะ non-text ที่ *สื่อความหมาย* — ขอบของ input/select/checkbox/selected state ใช่, เส้นคั่น section หรือขอบการ์ดที่มี elevation อยู่แล้วไม่ใช่):
      - เป็นขอบของ control → **แก้สีให้ถึง 3:1** แล้ว request ใหม่
      - ตกแต่งล้วน → `contrast-check-decorative` (`ds`, `reason` = "<ขอบไหน ใช้ที่ไหน ทำไมไม่ใช่ control boundary>") แล้ว **paste บรรทัด `ACK` จาก report ลง bd**: task note "a11y: <บรรทัด ACK ที่ได้>"
      contrast run exit≠0 ใน report → **ห้ามเขียน tokens.json** (cite the report whose contrast run is exit 0 = ALL PASS เป็น evidence)
   e. query เฉพาะจุดตามต้องการ: `design-query-domain` (`domain` เช่น `ux`, `query` = semantic outcome ก่อน, `n`) แล้วค่อย `design-query-stack` (`stack`) สำหรับวิธี implement
   f. 0 result → retry แคบลง 1 ครั้ง → ยังว่าง = **บอกตรง ๆ ว่าใช้ built-in default ไม่ใช่ match จากฐานข้อมูล** ห้าม persist output ที่ยังไม่ verify

3. Produce artifacts:
   - Persona + JTBD + journey map (ถ้า new domain)
   - IA + user flow (happy + edge + error) — Mermaid
   - Wireframe low-fi → mid-fi (Figma frame link + frame ID)
   - Design tokens (W3C DTCG): primitive → semantic → component → `tokens.json`
   - a11y checklist (WCAG 2.1/2.2 AA)
   - Component state inventory: default/hover/active/focus/disabled/loading/error/empty
4. **🔴 v2.8.1 — Baseline capture (design run)** — ห้ามเขียน "baseline.png" placeholder:
   - `baseline-capture` (`feature` = slug ของ tracked spec `tests/visual/<feature>.spec.ts`; Playwright scaffold จาก init.md Phase 2)
   - cite the report: run exit 0 + the snapshot paths it records
   - The runner refuses a spec, config or lockfile that is untracked or modified and not named by the router; you never write tests or config (write limit)
   - ไม่มี ui-test toolchain (`design-run-tool-missing`) → request a `operate` (deploy mode) scaffold through the router (init.md Phase 2)
   - Chromatic is not in the catalogue: an upload to a third party is a user-confirmed step outside the runner
5. **🔴 v2.8.1 — `design`'s own AC (G-W-T format, bullet-per-screen)** — Phase 3a จะ check ทีละข้อ:
   ```
   AC-1: GIVEN user เปิด /checkout WHEN page load THEN ราคารวมแสดงเป็น "฿1,234.56" (font-size: 24px, weight: 700, color: token.text.primary)
   AC-2: GIVEN viewport 320px WHEN page load THEN content ไม่ overflow horizontal (no scroll-x)
   AC-3: GIVEN user กด Tab WHEN focus moves THEN order = header logo → nav → search → cart → footer
   AC-4: GIVEN screen reader WHEN announce "submit button" THEN aria-label = "ยืนยันคำสั่งซื้อ"
   ...
   ```
6. Sign-off → save to `outputs/SPEC-<bd-id>.md` (section UX/UI) + post task note "Phase 1b done: baseline=[report path], AC=[count]"

### ⏸️ Pre-implement-ui Gate (`design`)
Sign-off bundle complete:
- ✅ Figma frame link + frame ID
- ✅ `design-system/<slug>/MASTER.md` มีอยู่ + ถูกอ่านแล้ว (+ `pages/<page>.md` ถ้าหน้านี้ override) — v3.11
- ✅ `check_contrast.py` **ALL PASS** (design-run report, contrast run exit 0, path + router-relayed sha256) — v3.11 ห้ามข้าม · ถ้าใช้ `--border-decorative` ต้องมีบรรทัด **ACK อยู่ใน task notes** ด้วย (ตัดสินแล้วต้องบันทึก)
- ✅ tokens.json (with real values — no placeholder, ค่าตรงกับ MASTER/override)
- ✅ a11y checklist (with manual verify status per item)
- ✅ Baseline screenshot path (from the design-run report — ไม่ใช่ "TBD")
- ✅ `design`'s own AC ครบทุก critical screen (G-W-T bullet format)
- ✅ State inventory (default/hover/active/focus/disabled/loading/error/empty)
- ✅ WCAG 2.2 AA: มี AC ของ SC ที่เกี่ยวข้อง (2.4.11 / 2.5.7 / 2.5.8 / 3.3.7 / 3.3.8) หรือ `N/A: <SC> — ไม่มี <องค์ประกอบ>` — v3.11
