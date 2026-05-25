---
description: "[shode-house] Code review + security (Chris + Quinn + Domain) — รับ path, Jira ID, หรือ bug description (+ screenshot)"
allowed-tools: Task, Read, Grep, Glob, Bash, mcp__atlassian__getJiraIssue, mcp__atlassian__searchJiraIssuesUsingJql, mcp__atlassian__getJiraIssueRemoteIssueLinks
argument-hint: [path | KJERP-402 | คำอธิบายบั๊กภาษาไทย (+ screenshot ได้)]
---

Review target: **$ARGUMENTS**

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

5. **Track bug ใน beads**:
   ```bash
   bd create "BUG: $DESCRIPTION" -t bug -p high --labels=triage
   ```
   เก็บ issue ID ไว้ link กับ findings ทีหลัง

### Pattern D — Ambiguous → ถาม user

"`$ARGUMENTS` ตีความได้หลายแบบ — หมาย Jira key, path, หรือคำอธิบายบั๊ก?"

## Step 1 — Code Review (Chris) — 7 มิติ

1. Correctness (logic, edge, error)
2. Security (OWASP Top 10 + lang-specific)
3. SOLID & Design
4. Performance (N+1, complexity, memory)
5. Maintainability (size, naming, DRY)
6. Testing (unit coverage + quality + test doubles)
7. Observability (log/metric/trace)

**Context-aware review:**
- ถ้ามาจาก **Jira (Pattern A)** → cross-check code vs AC ใน description
- ถ้ามาจาก **bug description (Pattern C)** → focus 7 มิติเฉพาะ "เส้นทาง bug" (calc logic, edge case, expected vs actual) ก่อน — มิติอื่นเป็น secondary
- bd link: `bd create -t review-finding --links=$BUG_ID`

Output: findings by severity 🔴 Critical / 🟠 High / 🟡 Medium / 🔵 Low / 💡 Suggestion

## Step 2 — Security Scan (Quinn)

- SAST (Semgrep/Bandit/gosec)
- SCA (Trivy/Grype/npm audit)
- Secret scan (gitleaks)
- OWASP Top 10 manual

## Step 3 — Domain Review (conditional)

Keyword trigger → domain expert:
- payment/ledger/money → **Felix**
- accounting/journal/inventory (generic) → **Elena**
- SAP/ABAP/Fiori/BAPI/IDoc/S4HANA/ECC/CDS/RAP → **Sam**
- order/market/matching → **Tara**
- policy/claim/premium → **Iris**
- booking/rate (hotel/airline) → **Brooke**
- cart/checkout/promotion → **Emma**

## Step 4 — Consolidated Report (🔴 v2.8.2 — bd-native primary, markdown fallback)

Format ตาม **REVIEW Report Format** (meeting skill): Summary / Findings by severity / Coverage / UX Verdict (ถ้ามี) / Loop Routing Recommendation

**Storage rule** (ห้ามซ้ำซ้อน):
```bash
# Detect storage:
if [ -d ".beads" ] || bd ready --json >/dev/null 2>&1; then
  # bd active → bd notes ONLY
  if [ -n "$BD_ID" ]; then
    bd update "$BD_ID" --notes "<compact REVIEW template, refs evidence paths>"
  else
    bd create -t review-finding "$ARGUMENTS" --notes "<full REVIEW template>"
  fi
else
  # No bd → markdown fallback
  SLUG="${KJERP_KEY:-${BUG_DATE:-$(echo "$ARGUMENTS" | tr -cd '[:alnum:]-' | cut -c1-40)}}"
  cat > "outputs/REVIEW-$SLUG.md" <<EOF
  <full REVIEW template>
  EOF
fi

# Always: link to external tracker if applicable
if [ -n "$KJERP_KEY" ]; then
  addCommentToJiraIssue(issueIdOrKey="$KJERP_KEY", comment="สรุป findings + bd link หรือ md path")
fi
```

→ ห้ามเขียนทั้ง bd + markdown — เลือกตาม project state

## ⚠️ Rules

- Security Critical/High = **block merge**
- Domain-sensitive = บังคับผ่าน Domain Expert
- อ่านโค้ดจริงทุกไฟล์ (prefer `Grep` > `Read` full file)
- Run static analysis ถ้ามี (Bash)
- ถ้ามี Jira → auto comment findings กลับที่ ticket
- ภาษาไทย
