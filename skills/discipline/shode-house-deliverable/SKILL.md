---
name: shode-house-deliverable
description: Output and completion contract for anyone producing a deliverable - durable artifact, re-checkable evidence for every claim, no placeholders, no completion claim without real tool output. Not how work is routed or reviewed.
---

# Deliverable Core

## Output contract (🔴)

1. **Durable output** — use the confirmed evidence home and canonical task ID, including Markdown; chat alone is not durable handoff evidence.
2. **Evidence path** — ทุก claim แนบ path/command/output ที่ตรวจซ้ำได้; claim ที่ไม่มี evidence = ยังไม่ทำ
3. **No placeholder** — ห้ามส่งงานที่มี `TBD` / `<fill this>` / example data ปลอม โดยไม่ mark เป็น **OPEN QUESTION** พร้อมชื่อคนตอบ
4. **No false done** — ทำไม่ได้ = พูดว่าทำไม่ได้ + เหตุผล (`PARTIAL` / `BLOCKED`) ห้าม claim PASS

## 🚫 Anti-Puppet Rule (🔴)

ห้าม claim "เสร็จ / ผ่าน / deploy แล้ว / ปิด bd แล้ว" **โดยไม่ paste output ของ tool ที่รันจริง**
รูปแบบที่นับเป็น evidence: console output · HTTP response · screenshot/trace path · task read-back ที่แสดง CLOSED
ทำไม่ได้ → `"❌ ไม่ได้รัน เพราะ <reason>"` ตรงไปตรงมา ห้ามแกล้งผ่าน

## Completion

**Stop and return outranks completion.** "Continue until complete" never overrides a Stop-and-return condition, an R0/R1 protocol, an approval gate or an ownership boundary: when one applies, stop, record what is missing and return to Oliver — a stopped task reported honestly is a correct outcome, not a failure to complete.

Continue inside the authorized scope until: behaviour implemented · affected validation passes · failures you introduced fixed · applicable acceptance checked · changed files + evidence reported — not just the first plausible version.
Stop when: any Stop-and-return condition · unauthorized R0/R1 · approval gate or sha mismatch · third review iteration failed · external result UNKNOWN · required access unavailable · genuine ambiguity · product/business/legal decision · out of scope → report PARTIAL/BLOCKED; never widen scope, retry an external effect or skip a gate to finish.
Affected validation = floor, not ceiling: broaden for shared libraries · build tooling · public contracts · database schema · deployment configuration · security boundaries · cross-module behaviour; never skip a suite the project's acceptance/CI requires; dependency manifest/auth/crypto diff → full security checks.

## 📎 Reference

- closing a task / phase exit → `definition-of-done.md`
- standard output + "I Never Do" per agent → `output-contract.md`
- ADR → `adr.md`
- UI/a11y claim (Phase 1b, 3a) → `ux-evidence.md`
- evidence examples → `anti-puppet.md`
