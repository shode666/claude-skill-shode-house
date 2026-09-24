---
description: "[shode-house] ปรึกษาด่วน — route ไปหา agent ที่เหมาะที่สุด (ไม่รัน pipeline เต็ม)"
allowed-tools: Task, Read, Grep, Glob
argument-hint: "[question or topic]"
---

User request: $ARGUMENTS

Use the referenced command [consult](../knowledge/commands/consult.md) as the entry point for this request, applying it to the user request above. Follow only the branches that apply to the current task, and load additional references only when the command directs you to.
This is a discovery adapter, not a replacement for the command knowledge.
Resolve source-root paths beginning agents/, skills/, references/, commands/ or output-styles/ under this plugin's knowledge/ directory, not the user's project.
Use actual host tools and preserve host/project/user authority.
