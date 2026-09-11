---
description: "[shode-house] Review existing code and report findings; bug descriptions narrow scope, not permission to fix"
allowed-tools: Task, Read, Grep, Glob, Bash, Skill, mcp__atlassian__getJiraIssue, mcp__atlassian__searchJiraIssuesUsingJql, mcp__atlassian__getJiraIssueRemoteIssueLinks, mcp__atlassian__addCommentToJiraIssue
argument-hint: "[path | KJERP-402 | คำอธิบายบั๊กภาษาไทย (+ screenshot ได้) | --debt]"
---

Review target: **$ARGUMENTS**

## Intent and authority

Review evaluates existing work; a bug description narrows the investigation, not
permission to fix code. For root-cause investigation, use `diagnose` within the same
read-only scope. A requested fix may continue through implementation only within
the user's authorization. Send this scope to every delegate.
Report storage and external posting follow `review-checklist/report-format.md`;
a Jira key, PR URL or available write tool is not permission to post.

## Mode: `--debt` (จาก ponytail — deferred-shortcut harvest)

ถ้า `$ARGUMENTS` = `--debt`:
1. รัน (no Python) `grep -rnoE 'shortcut\(bd:[0-9]+\):[^"]*' . --include='*.*' | grep -v '/\.git/'` → รวบ `shortcut(bd:N):` comment ทั้ง repo (group ตาม bd id ด้วย `sort`/`awk`)
2. รวบ findings พร้อม source path/line และ issue ref เดิม; ไม่สร้าง issue จากการ scan อย่างเดียว
3. ส่งสรุปในแชท; ถ้าผู้ใช้หรือ project instructions อนุญาตให้บันทึก ใช้ storage rule ใน `review-checklist/report-format.md`
4. ไม่รัน 7-dim review (mode นี้เก็บ debt อย่างเดียว) → จบ

ไม่ใช่ `--debt` → ทำต่อ Step 0 ปกติ

## Step 0 — Resolve Argument (Oliver)

Oliver ตัดสินประเภท input แล้ว route:

### Pattern A — Jira issue key `[A-Z]+-\d+` (เช่น `KJERP-402`)

1. `getJiraIssue(issueIdOrKey="$ARGUMENTS")` → summary, description, status, assignee, labels, AC
2. `getJiraIssueRemoteIssueLinks` → linked PR / branch / commit
3. Parse description หา branch/PR URL/file path
4. มี PR → `gh pr diff` / `gh pr view --json files` ได้ changed files
5. ไม่มี PR → `git log --all --grep="$KEY" --oneline` หา commit
6. ยืนยัน: "พบ PR #123 แก้ไฟล์ X, Y, Z — review ไฟล์เหล่านี้?"

### Pattern B — File/Directory path (มี `/` หรือ `.` และตรงกับไฟล์จริง)

Review ตาม path ตรงๆ

### Pattern C — Natural language bug description (+ optional screenshot) 🆕

ตัวอย่าง: `/review การคำนวนหน้านี้ผิด` (+ screenshot แนบหรือไม่ก็ได้)

**Oliver triage bug:**

1. **Extract intent** จาก description:
   - Domain keywords: `คำนวน/คำนวณ` → calculation, `ราคา/ยอด` → price/total, `จอง` → booking, `ชำระ/จ่าย` → payment, `สต็อก` → inventory, `รายงาน` → report
   - UI hint: `หน้านี้/หน้าจอ` → frontend page, `API` → endpoint, `batch/cron` → job
   - Severity hint: `ผิด/พัง/error` → 🔴, `ช้า/slow` → 🟠, `ไม่สวย/ui` → 🟡

2. **ถ้ามี screenshot แนบ** → วิเคราะห์ภาพ:
   - อ่าน text/number บนภาพ (URL bar, page title, labels, values, error message)
   - ระบุ expected vs actual value (ถ้าผู้ใช้ไฮไลต์ / mark)
   - หา UI element ระบุ page/route (เช่น `/booking/summary`, `/invoice/preview`)

3. **Locate suspect code** — ใช้ keyword + UI clue:
   ```bash
   # ตัวอย่าง "การคำนวนหน้านี้ผิด" + screenshot หน้า invoice
   grep -rn "calculateTotal\|computeAmount\|sumPrice" --include="*.ts" --include="*.py"
   glob "**/invoice/**/*.{ts,vue,py}"
   ```

4. **Present candidate files** ให้ user ยืนยัน:
   ```
   จาก description + screenshot ผมสงสัยไฟล์:
   - src/services/invoice/calculator.ts (logic หลัก)
   - src/pages/invoice/summary.vue (render)
   - src/utils/money.ts (format)
   confirm review 3 ไฟล์นี้? (y/n / เพิ่มไฟล์)
   ```

5. Link existing task ID when supplied; creating or updating tracking follows the canonical report storage rule.

### Pattern D — Ambiguous → ถาม user

"`$ARGUMENTS` ตีความได้หลายแบบ — หมาย Jira key, path, หรือคำอธิบายบั๊ก?"

## Step 0.5 — Scope resolution (pin ก่อน fan-out เสมอ)

pin ขอบเขต diff **ก่อน** fan-out แล้วส่ง command ที่รันได้จริงไปกับ delegation:
      ```bash
      git rev-parse <fixed-point>            # ref ใช้ได้จริงไหม (commit/branch/tag/main/HEAD~5)
      git diff <fixed-point>...HEAD          # 🔴 three-dot = เทียบกับ merge-base
      git log <fixed-point>..HEAD --oneline  # commit list ส่งเข้า sub-agent
      ```
      **user ไม่ระบุ → ไล่ fallback ตามลำดับ อย่าถามทันที** (`/review path` และ `/review <bug>` เป็น contract ที่โฆษณาไว้ การบังคับ git fixed point ทุกกรณีทำให้ path ปกติหยุดเปล่า ๆ):
      1. มี branch ต้นทาง (`git rev-parse --abbrev-ref @{u}` หรือ `main`/`master`) → ใช้เป็น fixed point
      2. ไม่มี upstream แต่มี staged/working change → review **`git diff --cached`** แล้ว **`git diff`** (ระบุใน report ว่าขอบเขตคือ uncommitted)
      3. **ไม่ใช่ repo git / เป็นไฟล์เดี่ยว / เป็น snippet-screenshot ที่ user แปะมา** → ขอบเขต = **ไฟล์/เนื้อหานั้นทั้งชิ้น** (บันทึกใน report ว่า "no diff range — full-file review")
      4. ทุกทางไม่ได้ผลและงานเป็นชนิดที่ต้องมี diff จริง ๆ → ค่อยถาม
      ref ที่ user ระบุมาแล้วพัง หรือ diff ว่างทั้งที่ควรมี → **fail ตรงนี้** ไม่ใช่ไปตายใน sub-agent

ผลลัพธ์ที่ต้องได้ก่อนไป Step 1: **diff command ที่ตรวจแล้ว หรือ full-file/snippet scope ตาม fallback ข้อ 3** + ประโยคเดียวบอกขอบเขตที่จะเขียนใน report

## Step 1 — Invoke review-checklist skill

> v3.1: review checklist รวบศูนย์ใน `skills/discipline/review-checklist/SKILL.md`. Command นี้ = router + context-aware invoke

🔴 **ก่อน spawn ใด ๆ ต้อง print block นี้ก่อนเสมอ** (pin review scope; no tracker installation prerequisite):

```
[REVIEW DISPATCH CARD] target:<scope-or-existing-task-ref>
- Chris    (7-dim)          : DISPATCH
- Quinn    (test/SAST axis) : DISPATCH
- Bella    (spec axis)      : DISPATCH | SKIP("no spec available — Pattern C, no Jira/bd/SPEC-*.md")
- Sentinel (security depth) : DISPATCH(trigger:<keywords>) | SKIP("no trigger keyword")
- Domain   (<expert>)       : DISPATCH(trigger:<keywords>) | SKIP("no trigger keyword")
→ launch ทุก DISPATCH ติดกัน ก่อนรอผลตัวใด (Task = async) — ห้าม spawn เพิ่มทีหลัง
```

กติกา (เขียนติดกับ template — บังคับทั้ง 5 ข้อ):
1. Chris + Quinn = unconditional DISPATCH — ไม่มี SKIP branch ให้เลือก
2. Bella SKIP ได้ **เหตุผลเดียว**: "no spec available" หลังไล่ spec source ครบลำดับ
   (Jira/bd description → user path → outputs/SPEC-*.md → ถาม user) — ต้อง cite ว่าเช็คอะไรแล้ว
3. Sentinel SKIP ได้ **เหตุผลเดียว**: "no trigger keyword" — ต้อง scan keyword list ตาม
   `review-checklist/security-sentinel.md` บรรทัด `WHEN: diff_touches in {auth,money,PII,crypto,
   secrets} OR secure_skill_triggered=true` (lazy-load-contract block — canonical, ห้าม fork list
   ที่นี่) กับ prompt+diff ก่อน; เจอ = DISPATCH บังคับ
4. ทุก DISPATCH ต้องมี Task call จริงติดกันหลัง card (ขนาน = spawn ครบก่อนรอผล; scorer วัด
   window ทับซ้อน) — จำนวน Task call = จำนวน DISPATCH line เป๊ะ
5. ไม่ print card = ห้าม spawn; task ref may be absent for an explicitly scoped file/snippet review

```bash
[Oliver|review|target:$ARGUMENTS] kickoff   # pin fixed point ก่อน — see `review-checklist/intake.md`
# ── แกน Standards
- Chris   → 7-dim — see `agents/code-reviewer.md` § 7 มิติ (Correctness/Security/SOLID/Perf/Maintain/Test/Observ)
- Quinn   → Security scan section (SAST/SCA/secret/OWASP manual) — see `agents/qa-engineer.md` § ขอบเขต
- Sentinel (conditional, if security trigger detected) — see `review-checklist/security-sentinel.md`
- Domain (conditional, keyword trigger) — see `review-checklist/domain-validation.md`
# ── แกน Spec (ต้อง dispatch จริง)
- Bella   → Spec axis — see `review-checklist/spec-axis.md`
            spec source ตามลำดับ: Jira/bd description → path ที่ user ส่ง → outputs/SPEC-*.md → ถาม user
            Pattern C (bug description) ที่ไม่มี spec → รายงาน "no spec available" แล้วรันเฉพาะ Standards
```

🔴 aggregate แยกหัวข้อ `## Standards` / `## Spec` — **ห้าม merge/rerank ข้ามแกน**

**Context-aware focus**:
- Pattern A (Jira) → cross-check code vs AC ใน description; retain the supplied issue link
- Pattern C (bug description) → focus 7-dim เฉพาะ "เส้นทาง bug" ก่อน (calc logic / edge / expected vs actual); มิติอื่นเป็น secondary
- Pattern B (path) → full 7-dim + integration matrix

## Step 2 — Consolidated Report (🔴)

Format + storage rules + severity grading + loop routing — **ทั้งหมดอยู่ใน `review-checklist` skill**:
- § Severity Grading (🔴/🟠/🟡/🔵/💡)
- § REVIEW Report Format (bd-native primary, markdown fallback)
- § Loop Routing Recommendation
- § Anti-Puppet Gate (paste tool output)

Use the single storage/authorization rule in `review-checklist/report-format.md`.
Do not duplicate tracker detection, report writes or posting logic here.

## ⚠️ Rules

- Security Critical/High = **block merge**
- Domain-sensitive = บังคับผ่าน Domain Expert
- อ่านโค้ดจริงทุกไฟล์ (prefer `Grep` > `Read` full file)
- Run static analysis ถ้ามี (Bash)
- Jira/PR posting only when authorized under the shared report storage rule
- ตอบภาษาเดียวกับที่ user เขียนมาล่าสุด (`shode-house-discipline` § Response Language); code/path/command/log verbatim
