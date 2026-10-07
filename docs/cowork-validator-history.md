# Cowork validator — history + anti-patterns

History and examples for the Cowork validator rule (`AGENTS.md` § Plugin). This file states no rule; who enforces which constraint is explained in `docs/repo-invariants/plugin-release.md`.

> **History**: v2.5.1 + v3.1.0 เคย fail "Plugin validation failed" ตอน Cowork drag-drop. CLI `claude plugin validate` ผ่าน + JSON schema ผ่าน **ไม่ได้แปลว่า Cowork ผ่าน** — Cowork validator stricter ที่ runtime

What the `git log --grep="validator"` search turns up (it is the first step after a failed validation, see `AGENTS.md` § Plugin): the commits and lessons of the two earlier failures, v2.5.1 and v3.1.0.

**Anti-patterns ที่เคยทำให้ fail (อย่าทำซ้ำ)**:

```jsonc
// ❌ Round 1 v3.1.0 — Object form + ยาว + Thai
{
  "description": "Multi-agent software house team v3.1: 19 expert agents in 7 teams + 18 lazy-load skills (split meeting-god-skill into 7 discipline modules + review-checklist DRY) + 6 commands (consolidated /init+/setup-project, /design-system+/spec-only). Bucket-folder lifecycle (workflow/ops/ui/style/discipline/in-progress/deprecated). CLAUDE.md repo invariants + scripts/ dev-loop. 9arm-inspired skill craft: 4-section description format, When-NOT + Required-inputs gates, Recite Discipline Card, skill composition pointers. Covers Fintech, ERP, SAP, Trading, Insurance, Booking, E-commerce, UX/UI.", // 586 chars + em-dash → FAIL
  "skills": [
    {"name": "ask", "path": "skills/workflow/ask", "bucket": "workflow", "role": "..."} // object form → schema reject
  ]
}

// ❌ Round 2 v3.1.0 — schema fix แล้ว แต่ description ยังยาว
{
  "description": "Multi-agent software house team v3.1: ... 586 chars + Thai ...", // ยังเกิน → FAIL Cowork (CLI pass)
  "skills": ["./skills/workflow/"] // schema ok
}

// ✅ Round 3 v3.1.0 — ผ่านทั้ง CLI + Cowork
{
  "description": "Multi-agent software house team v3.1: 19 agents in 7 teams + 18 lazy-load skills + 6 commands. Bucket-folder lifecycle. 9arm-inspired skill craft.", // 146 chars ASCII → PASS
  "skills": ["./skills/workflow/", "./skills/ops/", "./skills/ui/", "./skills/style/", "./skills/discipline/"]
}
```
