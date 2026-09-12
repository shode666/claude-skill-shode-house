---
name: drain
description: |
  [WHAT] Drain backlog ที่ verified แล้ว N item — 1 worktree-isolated agent ต่อ item (TDD, no push) → serial cherry-pick เข้า trunk → ปิด bd ทุก item พร้อม evidence.
  [WHEN] หลังมี routing plan (Oliver) AND item ถูก code-verify ว่า independent + concrete.
  [TRIGGER] /shode-house:drain, "drain backlog", "จัดงานที่พร้อม", "batch fix", "ปิด bd ที่เหลือ", "clear the ready set".
---

Read [drain](../../knowledge/skills/ops/drain/SKILL.md) in full before carrying out the task, including its declared prerequisite skills.
This is a discovery adapter, not a replacement for the role or skill knowledge.
Resolve source-root paths beginning agents/, skills/, references/, commands/ or output-styles/ under this plugin's knowledge/ directory, not the user's project.
Use actual host tools and preserve host/project/user authority.
