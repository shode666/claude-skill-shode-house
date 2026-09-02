#!/usr/bin/env bash
# สร้าง project ทดสอบสำหรับ eval scenario 4,5,6,7,11 (WS8 runtime baseline)
# รันครั้งเดียวก่อนเริ่มฝั่ง A -- ห้ามแก้ folder นี้อีกจนกว่าจะจบทั้ง A และ B
set -euo pipefail

DEST="${1:-$HOME/workspace/shode-eval}"
PLUGIN_REPO="$(cd "$(dirname "$0")/.." && pwd)"

# ยอมให้ dir ที่มีอยู่ได้ถ้าว่าง (หรือมีแค่ .git ที่ยังไม่มี commit) -- บางที่ลบ dir ไม่ได้
if [ -e "$DEST" ]; then
  extra=$(ls -A "$DEST" 2>/dev/null | grep -v '^\.git$' | grep -v '^outputs$' || true)
  if [ -n "$extra" ]; then
    echo "!! $DEST มีไฟล์อยู่แล้ว -- ใช้ path ว่าง ๆ แทน"; exit 1
  fi
  echo "-- ใช้ $DEST ที่มีอยู่ (ว่าง)"
fi
mkdir -p "$DEST"/{src,outputs,tests}
cd "$DEST"
git rev-parse --git-dir >/dev/null 2>&1 || git init -q
git config user.email eval@local && git config user.name eval

# ── commit 0: baseline ────────────────────────────────────────────────
cat > README.md <<'EOF'
# shode-eval — fixture project สำหรับ eval baseline
ไม่ใช่ของจริง ใช้วัด token/behavior ของ plugin เท่านั้น
EOF
cat > src/notification.py <<'EOF'
import smtplib

def send(user, subject, body):
    if not user.get("email"):
        return False
    with smtplib.SMTP("localhost") as s:
        s.sendmail("no-reply@local", user["email"], f"Subject: {subject}\n\n{body}")
    return True
EOF
cat > src/ledger.py <<'EOF'
from decimal import Decimal

def post(entries):
    total = sum(Decimal(str(e["amount"])) for e in entries)
    if total != 0:
        raise ValueError("unbalanced")
    return {"posted": len(entries)}
EOF
git add -A && git commit -qm "baseline: notification + ledger"
BASE_SHA=$(git rev-parse --short HEAD)

# ── commit A: notification diff (phase3b-base) ────────────────────────
cat > src/notification.py <<'EOF'
import smtplib, time

RETRY = 3

def send(user, subject, body, retry=RETRY):
    if not user.get("email"):
        return False
    for i in range(retry):
        try:
            with smtplib.SMTP("localhost", timeout=5) as s:
                s.sendmail("no-reply@local", user["email"], f"Subject: {subject}\n\n{body}")
            return True
        except Exception as e:
            print(f"send failed: {e} user={user['email']}")
            time.sleep(2 ** i)
    return False
EOF
git add -A && git commit -qm "feat(notification): retry + backoff"
SHA_A=$(git rev-parse --short HEAD)

# ── commit B: ledger + card masking diff (phase3b-sensitive) ──────────
cat > src/ledger.py <<'EOF'
from decimal import Decimal

def mask_card(pan):
    return pan[:6] + "*" * (len(pan) - 10) + pan[-4:]

def post(entries, card=None):
    total = sum(Decimal(str(e["amount"])) for e in entries)
    if total != 0:
        raise ValueError("unbalanced")
    row = {"posted": len(entries), "amount": float(total)}
    if card:
        row["card"] = mask_card(card)
        print(f"ledger post card={card}")
    return row
EOF
git add -A && git commit -qm "feat(ledger): posting with card reference"
SHA_B=$(git rev-parse --short HEAD)

# ── spec สำหรับ implement-backend (bd-101) ────────────────────────────
cat > outputs/SPEC-bd-101.md <<'EOF'
# SPEC bd-101 — POST /refunds

## Scope
รับคำขอคืนเงินของ order ที่ชำระแล้ว บันทึกลง ledger แล้วคืน refund id

## Acceptance criteria
- AC-1 `POST /refunds` รับ `{order_id, amount, reason}` คืน `201 {refund_id, status}`
- AC-2 amount > ยอดที่จ่ายจริง → `422` พร้อม error code `AMOUNT_EXCEEDS_PAID`
- AC-3 order ที่ยังไม่ชำระ → `409 ORDER_NOT_PAID`
- AC-4 เรียกซ้ำด้วย `Idempotency-Key` เดิม → คืน refund เดิม ไม่สร้างใหม่
- AC-5 ทุก refund ลง ledger แบบ double-entry ผลรวมต้องเป็นศูนย์

## Out of scope
partial refund หลายครั้งต่อ order · การคืนเงินข้าม currency
EOF

# ── Uma artifact สำหรับ implement-ui (bd-102) — pre-implement-ui gate ──
mkdir -p outputs/bd-102
cat > outputs/bd-102/01-ux-ui-designer-phase-1b.md <<'EOF'
# bd-102 — Refund history (Uma, Phase 1b)

## Wireframe (text)
```
[Refund history]                       [filter: 30 วัน ▾]
┌────────────┬──────────┬─────────┬──────────┐
│ วันที่      │ order    │ ยอด     │ สถานะ    │
├────────────┼──────────┼─────────┼──────────┤
│ 12 ม.ค.    │ #10231   │ 1,250.00│ สำเร็จ    │
└────────────┴──────────┴─────────┴──────────┘
(empty state) "ยังไม่มีรายการคืนเงิน" + ปุ่ม "ดูคำสั่งซื้อ"
```

## Tokens
`--color-text`, `--color-surface`, `--space-4`, `--radius-2` — ห้าม hardcode

## AC
- AC-1 ตารางเรียงใหม่→เก่า, ยอดชิดขวา
- AC-2 320px ไม่ overflow (แถวยุบเป็น card)
- AC-3 focus order: filter → แถวแรก → pagination
- AC-4 empty state มีทางออก
- AC-5 สถานะไม่สื่อด้วยสีอย่างเดียว (1.4.1) + touch target ≥24px (2.5.8)
EOF

# ── resume-run (bd-103) — Phase 2 เสร็จ ยังไม่ review ─────────────────
mkdir -p outputs/bd-103
cat > outputs/bd-103/00-run-stamp.md <<EOF
run_id      : eval-bd-103
plugin      : (ตั้งตอนรัน)
phase_done  : phase-2
phase_next  : phase-3b
iter        : 1
artifacts   : outputs/bd-103/01-developer-phase-2.md
approval    : phase-1a signed off
EOF
cat > outputs/bd-103/01-developer-phase-2.md <<'EOF'
# bd-103 — export รายงานยอดขายเป็น CSV (Dave, Phase 2)

- เพิ่ม `src/report.py` `export_sales(start, end) -> str(path)`
- unit test 6 เคสผ่าน (paste ใน bd note แล้ว)
- ยังไม่ผ่าน Phase 3b — ยังไม่มีใคร review
EOF
cat > src/report.py <<'EOF'
import csv, tempfile

def export_sales(rows, start, end):
    path = tempfile.mktemp(suffix=".csv")
    with open(path, "w", newline="") as f:
        w = csv.writer(f)
        w.writerow(["date", "order_id", "amount"])
        for r in rows:
            if start <= r["date"] <= end:
                w.writerow([r["date"], r["order_id"], r["amount"]])
    return path
EOF
git add -A && git commit -qm "fixture: spec + phase artifacts for bd-101/102/103"

# ── tracker ───────────────────────────────────────────────────────────
if command -v bd >/dev/null 2>&1; then
  bd init -q 2>/dev/null || true
  bd create "POST /refunds ตาม SPEC-bd-101" 2>/dev/null || true
  bd create "หน้า refund history ตาม wireframe Uma" 2>/dev/null || true
  bd create "export รายงานยอดขาย CSV (Phase 2 done, รอ review)" 2>/dev/null || true
  echo "-- bd issue สร้างแล้ว: ตรวจเลข id จริงด้วย 'bd list' แล้วแทนใน prompt"
  BD_NOTE="ใช้เลข bd จริงจาก 'bd list' แทน bd-101/102/103 ใน prompt"
else
  cat > TRACKER.md <<'EOF'
# tracker (ไม่มี bd CLI — ใช้ไฟล์นี้แทน)
| id     | title                                        | state       |
|--------|----------------------------------------------|-------------|
| bd-101 | POST /refunds ตาม outputs/SPEC-bd-101.md      | ready       |
| bd-102 | หน้า refund history ตาม wireframe ของ Uma      | ready       |
| bd-103 | export รายงานยอดขาย CSV                        | phase-2 done, รอ review |
EOF
  git add -A && git commit -qm "fixture: tracker fallback (ไม่มี bd CLI)"
  BD_NOTE="ไม่มี bd CLI -- ใช้ TRACKER.md; M1 ingress guard อาจ STOP เพราะหา bd ไม่เจอ (บันทึกไว้เป็น assertion)"
fi

# ── prompt ที่ resolve sha จริงแล้ว ────────────────────────────────────
mkdir -p "$PLUGIN_REPO/eval/prompts/resolved"
sed "s/abc1234/$SHA_A/" "$PLUGIN_REPO/eval/prompts/phase3b-base.md" \
  > "$PLUGIN_REPO/eval/prompts/resolved/phase3b-base.md"
sed "s/def5678/$SHA_B/" "$PLUGIN_REPO/eval/prompts/phase3b-sensitive.md" \
  > "$PLUGIN_REPO/eval/prompts/resolved/phase3b-sensitive.md"
for s in implement-backend implement-ui resume-run consult-single design-system-backend \
         design-system-fe-domain diagnose-fast diagnose-full map-mode; do
  cp "$PLUGIN_REPO/eval/prompts/$s.md" "$PLUGIN_REPO/eval/prompts/resolved/$s.md"
done

cat <<EOF

═══ fixture พร้อมแล้ว: $DEST
  base commit      : $BASE_SHA
  phase3b-base     : $SHA_A   (src/notification.py)
  phase3b-sensitive: $SHA_B   (src/ledger.py)
  spec bd-101      : outputs/SPEC-bd-101.md
  Uma artifact 102 : outputs/bd-102/01-ux-ui-designer-phase-1b.md
  run stamp 103    : outputs/bd-103/00-run-stamp.md

  prompt ที่ resolve sha แล้ว -> eval/prompts/resolved/  (ใช้ชุดนี้ทั้ง A และ B)
  $BD_NOTE

🔴 ห้ามแก้ไฟล์ใน $DEST อีกจนกว่าจะเก็บผลครบทั้งสองฝั่ง
EOF
