# Proposal — Adopt ponytail + caveman ideas into shode-house

> **Mode**: Proposal only. ยังไม่แตะ repo. ทุก section = diff preview + invariant check ให้ review ก่อน
> **Sources**: [DietrichGebert/ponytail](https://github.com/DietrichGebert/ponytail) (YAGNI-first, 8.7k★) · [JuliusBrussee/caveman](https://github.com/JuliusBrussee/caveman) (output compression, 62k★)
> **Target**: shode-house v3.5.1 → **v3.6.0** (minor bump, 1 batch)
> **Scope approved**: prompt/skill (#1,2,7) + token/eval (#3,4,5) + script (#6) = ครบ 7

---

## TL;DR — 7 adoptions ในตารางเดียว

| # | Adopt | แตะไฟล์ | ประเภท | เสี่ยง |
|---|-------|---------|--------|--------|
| 1 | YAGNI ladder ก่อนเขียน code | `skills/workflow/dev-gate/SKILL.md`, `agents/developer.md` | prompt | ต่ำ |
| 2 | `shortcut(bd):` comment + debt harvest | `dev-gate`, `commands/review.md`, **new** `scripts/harvest_shortcuts.py` | prompt+script | ต่ำ |
| 3 | Compress CLAUDE.md (caveman-compress) | `CLAUDE.md` (+ keep `CLAUDE.full.md`), `skills/style/caveman/SKILL.md` | doc | **กลาง** |
| 4 | Token-savings stats | **new** `scripts/caveman_stats.py` + `/caveman stats` mode | script | ต่ำ |
| 5 | 3-arm honest compression eval | `skills/in-progress/eval-harness/` (unshipped) | eval | ต่ำ |
| 6 | Rule-copy / model-table drift check | `scripts/check_index.py` หรือ **new** `scripts/check_rule_copies.py` | script | ต่ำ |
| 7 | "Lazy not negligent" carve-out | `caveman`, `dev-gate`, `developer.md` | prompt | ต่ำ |

**Invariant ที่ต้องเคารพตลอด**: skill ≤300 บรรทัด (dev-gate exception ≤400) · 3-flag rule (เลี่ยง command ใหม่) · plugin.json desc ≤200 ASCII · model table อยู่ README ที่เดียว · in-progress/ ไม่ ship

---

## #1 — YAGNI ladder (จาก ponytail)

**แนวคิด ponytail**: ก่อนเขียน code หยุดที่ขั้นแรกที่ผ่าน
```
1. Does this need to exist?  → no: skip (YAGNI)
2. Stdlib does it?           → use it
3. Native platform feature?  → use it
4. Installed dependency?     → use it
5. One line?                 → one line
6. Only then: minimum that works
```

**Fit**: ตรงกับ Philosophy "NO MAGIC" + dev-gate Gate 6 (complexity) + Dave's "simplest thing that works". ปัจจุบัน dev-gate พูด YAGNI ลอย ๆ ใน Green phase แต่ไม่มี checklist บังคับ *ก่อน* เขียน

**Where**: `dev-gate` Part 1 — เพิ่ม "Step 0" ก่อน 🔴 Red

```diff
 ## Part 1: TDD Cycle (red → green → refactor)

+### 0. ⛔ YAGNI ladder — หยุดก่อนเขียน (จาก ponytail)
+
+ก่อนเขียน production code ใด ๆ ตอบไล่จากบนลงล่าง หยุดที่ข้อแรกที่ "ใช่":
+
+| ขั้น | ถาม | ถ้าใช่ |
+|---|---|---|
+| 1 | feature นี้ต้องมีจริงไหม? | ไม่ → skip (YAGNI) + log เป็น bd discovered |
+| 2 | stdlib ทำได้ไหม? | ใช้ stdlib |
+| 3 | native platform feature? (`<input type=date>`, `crypto`, ...) | ใช้ native |
+| 4 | dep ที่ลงแล้วทำได้? | ใช้ของเดิม ห้ามลง dep ใหม่ |
+| 5 | one-liner พอไหม? | เขียนบรรทัดเดียว |
+| 6 | ถ้าผ่านทั้งหมด | เขียน "ขั้นต่ำที่ work" เท่านั้น |
+
+> ทุกครั้งที่ตัด (ขั้น 1) หรือใช้ทางลัด → mark ด้วย `shortcut(bd):` comment (ดู Gate 3) เพื่อให้ debt harvest เก็บได้
+> **เพดานความขี้เกียจ**: ห้ามตัด validation/security/a11y/regulation (ดู carve-out #7)
+
 ### 1. 🔴 Red — เขียน test ที่ fail ก่อน
```

**Where 2**: `agents/developer.md` § Implement Loop — เพิ่ม 1 บรรทัดชี้ไป ladder

```diff
 ## 🔁 Implement Loop (Archon-inspired)
+
+> ⛔ ก่อนเข้า loop: ผ่าน **YAGNI ladder** (dev-gate Step 0). code ที่ดีที่สุด = code ที่ไม่ต้องเขียน
```

**Invariant check**: +~16 บรรทัด → dev-gate 340 → ~356 (< 400 ✓). ไม่กระทบ plugin.json/desc.
**Risk**: ต่ำ. เป็น additive discipline.

---

## #2 — `shortcut(bd):` comment + debt harvest (จาก ponytail `/ponytail-debt`)

**แนวคิด ponytail**: ทุกทางลัดฝัง comment บอก upgrade path → คำสั่งเก็บเข้า ledger เพื่อ "later" ไม่กลาย "never"

**Fit**: shode-house ใช้ `bd` (backlog) อยู่แล้ว → ทางลัดควรผูกกับ bd id. แต่ **3-flag rule** ห้ามเพิ่ม command ใหม่ → ทำเป็น **script + flag บน `/review`** แทน `/ponytail-debt`

**Convention** (เพิ่มใน dev-gate Gate 3 "Remove Unused" zone):
```
# shortcut(bd:42): ใช้ in-memory dict; upgrade → Redis เมื่อ >10k key
```
รูปแบบบังคับ: `shortcut(bd:<id>): <reason>; upgrade → <path>`

**New script** `scripts/harvest_shortcuts.py` (stdlib only, ตาม prerequisite repo):
```python
#!/usr/bin/env python3
"""harvest_shortcuts.py — รวบ shortcut(bd:N) comment ทั้ง repo เป็น ledger.
Grep หา pattern → group ตาม bd id → print/write outputs/DEBT-<date>.md.
Exit 0 เสมอ (report tool ไม่ใช่ gate). Stdlib only."""
# regex: r"shortcut\(bd:(\d+)\):\s*(.+)"
# walk tree (skip .git), collect (file, line, bd_id, text) → markdown table
```

**Flag บน command เดิม** `commands/review.md` — เพิ่ม mode (ยังอยู่ใน 3-flag budget):
```diff
+## Mode: --debt
+`/review --debt` → รัน scripts/harvest_shortcuts.py → present DEBT ledger
+(ไม่รัน 7-dim review; แค่เก็บทางลัดที่ยัง defer)
```

**Phase 4 Triage hook** (`shode-house-workflow` หรือ `developer.md` Process): หลังปิด bd → ถ้ามี `shortcut(bd:)` ใหม่ → สร้าง bd discovered อัตโนมัติ

**Invariant check**: ไม่เพิ่ม command ใหม่ (✓ 3-flag). script ใหม่ = Python stdlib (✓ prerequisite).
**Risk**: ต่ำ.

---

## #3 — Compress CLAUDE.md (จาก caveman `/caveman-compress`)

**แนวคิด caveman**: rewrite memory file ให้สั้น code/URL/path byte-preserved → ลด input token **ทุก session** (repo จริงลด ~46%)

**Fit**: CLAUDE.md ของ shode-house ยาว + โหลดทุก session. แต่มันคือ **invariant doc** → compress ผิด = กฎหาย

**ข้อเสนอแบบปลอดภัย** (ไม่ revert ได้ยาก):
1. เก็บต้นฉบับเป็น `CLAUDE.full.md` (canonical, human-facing)
2. สร้าง `CLAUDE.md` เวอร์ชัน compressed สำหรับ agent โหลด
3. **byte-preserve เด็ดขาด**: ทุก JSON anti-pattern block, path, `scripts/*.py` name, version string, ตัวเลข char-limit (200/100/300/400)
4. compress เฉพาะ prose ที่ไม่ใช่ machine-checked (เช่น History narrative, คำอธิบายยาว)
5. verify: รัน `scripts/check_index.py` + `scripts/lint.py` ต้องผ่านเหมือนเดิม + diff กฎทีละข้อด้วยตา

**Where**: `skills/style/caveman/SKILL.md` เพิ่ม sub-section "compress memory file" (skill ตอนนี้ 58 บรรทัด เหลือที่เยอะ)
```diff
+## Compress memory file (caveman-compress mode)
+
+เป้าหมาย: ลด input token ของ CLAUDE.md / project notes ทุก session
+- **Byte-preserve**: code block, path, URL, version, char-limit number, JSON example — ห้ามแตะ
+- **Compress ได้**: prose narrative, History, คำอธิบายซ้ำ
+- เก็บต้นฉบับ `<file>.full.md` เสมอ ก่อน overwrite
+- verify: machine-checked rule (script ตรวจ) ต้องคงความหมาย 100% → รัน check_index.py + lint.py
```

**Invariant check**: caveman skill +~10 บรรทัด (< 300 ✓). CLAUDE.md ไม่ถูก script ตรวจเนื้อหา (check_index อ่านแค่ plugin.json + SKILL.md size) → ปลอดภัยถ้า lint ผ่าน.
**Risk**: **กลาง** — ต้อง human-diff กฎทุกข้อ. แนะนำทำ #3 เป็น step สุดท้าย หลัง #6 (drift check) พร้อมใช้.
**ตัวเลขคาดหวัง**: prose ~40-50% ของ CLAUDE.md → ลดรวม ~20-25% input token/session (ประเมิน; ยืนยันด้วย #4 stats)

---

## #4 — Token-savings stats (จาก caveman `/caveman-stats`)

**แนวคิด caveman**: นับ token จริง + ยอดสะสม + USD → statusline badge. พิสูจน์ ROI

**Fit**: ตรง evidence discipline ("cite ก่อน claim") — มีตัวเลขแทนการเดา. **3-flag rule** → ทำเป็น script + mode บน `/caveman` ไม่ใช่ command ใหม่

**New script** `scripts/caveman_stats.py`:
```python
#!/usr/bin/env python3
"""caveman_stats.py — ประเมิน token saving จาก compression.
- รับ before/after file (เช่น CLAUDE.full.md vs CLAUDE.md)
- นับ char/word → ประเมิน token (~chars/4) → %saved + USD ที่ rate ที่กำหนด
- เขียน outputs/CAVEMAN-STATS-<date>.md. Stdlib only."""
```

**Mode บน `/caveman`** (เป็น trigger ของ skill อยู่แล้ว ไม่ใช่ command ใหม่): `/caveman stats` → รัน script + print สรุป

**Invariant check**: ไม่เพิ่ม command (✓). script stdlib (✓). ไม่อ้าง token-saving เป็น fact จนกว่า script ยืนยัน (ตรง evidence rule).
**Risk**: ต่ำ. ตัวเลขเป็น *estimate* — ระบุชัดว่าเป็นการประเมิน ไม่ใช่ API-measured (caveman เองก็เตือนว่า output-token only)

---

## #5 — 3-arm honest compression eval (จาก caveman `evals/`)

**แนวคิด caveman**: เทียบ skill กับ baseline `"Answer concisely."` ไม่ใช่ verbose default → delta ซื่อสัตย์

**Fit**: eval-harness ปัจจุบันวัด *agent bias* (sycophancy/anchoring) — ยังไม่มี harness วัด *compression delta* ของ caveman เอง. เพิ่ม 3-arm arm นี้เข้าไป (in-progress/ ไม่ ship → ไม่กระทบ plugin)

**Where**: `skills/in-progress/eval-harness/` เพิ่ม fixture + note methodology
```diff
+## Compression eval (3-arm — measure caveman honestly)
+
+3 arms ต่อ prompt เดียวกัน:
+  A. baseline (no instruction)
+  B. "Answer concisely."   ← honest baseline, ไม่ใช่ verbose default
+  C. caveman skill (lite/full/ultra/wenyan)
+
+metric: output_tokens(A,B,C) + technical_accuracy(judge, blind)
+claim ได้เฉพาะ delta C-vs-B (ไม่ใช่ C-vs-A — นั่น inflate)
+fixtures: tests/eval-fixtures/caveman/<NN>.json (≥10 prompts, N≥5 runs)
```

> **หมายเหตุ drift ที่เจอ**: eval-harness ยังอ้าง agent **"Evan"** แต่ CLAUDE.md v3.3 บอก Evan ถูก revert แล้ว (harness = maintainer offline reference). ควรแก้ owner ใน harness เป็น "maintainer" ให้ตรง CLAUDE.md ระหว่างทำ #5

**Invariant check**: in-progress/ ไม่อยู่ใน plugin.json (✓ check_index ข้อ 2).
**Risk**: ต่ำ.

---

## #6 — Rule-copy / model-table drift check (จาก ponytail `check-rule-copies.js`)

**แนวคิด ponytail**: node script เช็คว่า rule text ที่ mirror หลาย agent ตรงกัน

**Fit**: CLAUDE.md ระบุชัด "ตาราง model มีที่เดียว = README § Model Strategy (skill อื่นห้าม copy — เคย drift ใน routing skill v2.x)" → นี่คือ drift target ที่ตรงปัญหาคุณที่สุด

**ข้อเสนอ**: เพิ่มเป็น **check ใหม่ใน `scripts/check_index.py`** (ไม่สร้าง script แยกให้ลืมรัน)
```python
def check_model_table_single_source(root: Path) -> int:
    """กฎ CLAUDE.md: model table อยู่ README ที่เดียว.
    Fail ถ้า skill/agent/command ไฟล์ใดมี model-table marker
    (เช่น 'claude-fable-5' + 'opus' + 'sonnet' ในตารางเดียวกัน)."""
    # grep skills/ agents/ commands/ หา pattern ตาราง model
    # allow เฉพาะ README.md + agent frontmatter `model:` (ค่าเดี่ยว ไม่ใช่ตาราง)
    # fail → "model table duplicated outside README — drift risk"
```
wire เข้า `main()` ต่อจาก check ข้อ 5 + เพิ่มใน pre-commit

**ตัวเลือกเสริม**: เช็ค model frontmatter value ถูกต้อง (`claude-fable-5` เฉพาะ Stan/Sara/Sentinel/Uma | `opus` | `sonnet`; ห้าม dated string) — บังคับ invariant v3.5 ที่ยังไม่มี script ตรวจ

**Invariant check**: เสริม check_index เดิม (ตรง CLAUDE.md rule #5 "เพิ่ม check ใน check_index.py ทันที").
**Risk**: ต่ำ. ต้อง tune regex ไม่ให้ false-positive กับ README.

---

## #7 — "Lazy not negligent" carve-out (จาก ponytail)

**แนวคิด ponytail**: ขี้เกียจได้ แต่ trust-boundary validation / data-loss / security / a11y **ห้ามตัด**

**Fit**: กันไม่ให้ #1 (YAGNI) + #3 (compress) ไปตัดของที่ domain expert (Felix/Sentinel/Iris/Uma) หวงไว้. shode-house มี domain เยอะ → carve-out ต้องกว้างกว่า ponytail

**Where** (3 จุด, ข้อความเดียวกัน — ต้อง sync ด้วย #6):
- `skills/workflow/dev-gate/SKILL.md` § หลักการ
- `skills/style/caveman/SKILL.md` § ห้าม
- `agents/developer.md` § ข้อห้าม

```diff
+### Lazy ≠ Negligent — ห้ามตัด (carve-out)
+YAGNI/compression ตัดได้เฉพาะ "ความซับซ้อนที่ยังไม่ต้องใช้" — **ห้ามแตะ**:
+- Trust-boundary validation (input/HTTP/queue/env — Zod/Pydantic)
+- Data-loss handling (transaction, idempotency, money R0)
+- Security control (auth, crypto, secret, injection guard)
+- Accessibility (WCAG — Uma's gate)
+- Regulation/compliance (Felix BOT/PCI · Iris OIC · domain rule)
+ตัดของเหล่านี้ = Philosophy violation, ไม่ใช่ "lazy"
```

**Invariant check**: +~9 บรรทัด/จุด. dev-gate รวม #1+#7 ≈ 365 (< 400 ✓). caveman ≈ 77 (< 300 ✓).
**Risk**: ต่ำ. ข้อความ mirror 3 จุด → #6 ควรเช็ค sync (เหมือน ponytail check-rule-copies)

---

## Rollout order (กัน regression)

```
1. #6 rule-copy/model-table check     ← ลง guardrail ก่อน (จับ drift ของ #1/#7)
2. #7 carve-out (3 จุด sync)          ← วาง safety net ก่อน YAGNI
3. #1 YAGNI ladder                     ← dev-gate + developer
4. #2 shortcut comment + harvest script
5. #4 stats script (เครื่องมือวัด)
6. #5 3-arm eval (in-progress)
7. #3 compress CLAUDE.md               ← สุดท้าย ใช้ #4 วัดผล + #6 ยืนยันกฎไม่หาย
```

## Version + release plan

- bump `plugin.json` + `marketplace.json` → **3.6.0** (SemVer minor)
- plugin.json description: ปรับให้ ≤200 ASCII (command count ไม่เปลี่ยน — เลี่ยง command ใหม่แล้ว) → ผ่าน check_index ข้อ 4
- CHANGELOG: เพิ่ม entry v3.6.0 (CLAUDE.md บังคับ)
- ก่อน release: `scripts/lint.py` + `scripts/check_index.py` ผ่าน → **drag-drop ทดสอบ Cowork จริง** (CLI ผ่าน ≠ Cowork ผ่าน)

## Open decisions (รอ user ตัดสิน)

1. **#3 compress CLAUDE.md** — เอาแบบ `CLAUDE.full.md` + `CLAUDE.md` (compressed) ไหม? หรือยังไม่อยากเสี่ยง invariant doc ตอนนี้ (เลื่อน #3 ไป v3.7)?
2. **#6** — ใส่ใน `check_index.py` (รันอัตโนมัติ) หรือแยก `check_rule_copies.py` (ชัดเจนกว่าแต่ต้องจำรัน)?
3. **bump** — รวบ 7 ข้อเป็น v3.6.0 ทีเดียว หรือแยก 2 รอบ (prompt-only ก่อน → token/script ตาม)?
