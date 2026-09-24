---
description: "[shode-house] Init — scaffold project ใหม่. Default: interactive wizard (Aaron + Bella + tracker). `--quick <stack>`: direct Aaron Docker-first (replaces /setup-project)"
allowed-tools: Read, Write, Edit, Bash, Task, Skill, AskUserQuestion
argument-hint: '[project-name | --quick "stack description"]'
---

User request: $ARGUMENTS

Use the referenced command [init](../knowledge/commands/init.md) as the entry point for this request, applying it to the user request above. Follow only the branches that apply to the current task, and load additional references only when the command directs you to.
This is a discovery adapter, not a replacement for the command knowledge.
Resolve source-root paths beginning agents/, skills/, references/, commands/ or output-styles/ under this plugin's knowledge/ directory, not the user's project.
Use actual host tools and preserve host/project/user authority.
