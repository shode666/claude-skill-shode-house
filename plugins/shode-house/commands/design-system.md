---
description: "[shode-house] Smart Spec pipeline (Phase 1a Bella + Sara parallel; Phase 1b Uma + Domain conditional). Flags: --stop = หยุดที่ spec ไม่ suggest implement (proposal mode); --estimate = เพิ่ม T-shirt sizing step"
allowed-tools: Task, Read, Write, Edit, Grep, Glob, Bash, Skill, AskUserQuestion
argument-hint: "[bd-id | system description] [--stop] [--estimate]"
---

User request: $ARGUMENTS

Use the referenced command [design-system](../knowledge/commands/design-system.md) as the entry point for this request, applying it to the user request above. Follow only the branches that apply to the current task, and load additional references only when the command directs you to.
This is a discovery adapter, not a replacement for the command knowledge.
Resolve source-root paths beginning agents/, skills/, references/, commands/ or output-styles/ under this plugin's knowledge/ directory, not the user's project.
Use actual host tools and preserve host/project/user authority.
