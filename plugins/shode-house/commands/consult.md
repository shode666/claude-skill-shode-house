---
description: "[shode-house] ปรึกษาด่วน — route ไปหา agent ที่เหมาะที่สุด (ไม่รัน pipeline เต็ม)"
allowed-tools: Task, Read, Grep, Glob
argument-hint: "[question or topic]"
---

คำถาม: **$ARGUMENTS**

Router style not active in this session → report `BLOCKED: team execution needs the router style (Claude Code)`; do not read the style file to act as the router.

## Routing

ส่งไป agent **ตัวเดียว** ที่เหมาะ: id จาก `output-styles/shode-house.md` § Routing; spawn `shode-house:<id>` only (a bare name reaches a project agent).
2+ agents / ไม่ชัด → the router picks the relevant specialists.
The targets are the 6 types of `output-styles/shode-house.md` § Routing: `plan` (discover, requirements, architecture, domain with a reference), `build` (also staff-grade), `verify` (standards or runtime), `operate` (deploy or reliability), `secure`, `design`. An old agent id or persona name → `skills/discipline/shode-house-routing/ownership.md` § Formerly (never spawn it).
A change or fix request is not a consult (no one-agent rule): apply the style § Dispatch floor or suggest `/implement`.

## Process

1. วิเคราะห์ intent
2. บอก user → agent ไหน + เหตุผลสั้น
3. The router delegates with the host's real delegation tool per `output-styles/shode-house.md` § Delegation, never to the main-session lead as an agent; no delegation tool → report the limitation per the harness
4. Present คำตอบ

## ⚠️ Rules

- 1 agent ถ้าคำถามเดียวตอบได้
- Design ใหญ่ → แนะนำ `/design-system`
- Review ไฟล์ → แนะนำ `/review`
- ตอบภาษาเดียวกับที่ user เขียนมาล่าสุด (`shode-house-discipline` § Response Language); code/path/command/log verbatim

Resolve source-root paths beginning agents/, skills/, references/, commands/ or output-styles/ under this plugin's knowledge/ directory, not the user's project.
No shode-house safety floor in this context (a main session without the router style)? Load `shode-house:ask` first.
