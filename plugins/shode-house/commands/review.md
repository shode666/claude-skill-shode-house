---
description: "[shode-house] Code review + security (Chris + Quinn + Domain) — รับ path, Jira ID, หรือ bug description (+ screenshot)"
allowed-tools: Task, Read, Grep, Glob, Bash, Skill, mcp__atlassian__getJiraIssue, mcp__atlassian__searchJiraIssuesUsingJql, mcp__atlassian__getJiraIssueRemoteIssueLinks, mcp__atlassian__addCommentToJiraIssue
argument-hint: "[path | KJERP-402 | คำอธิบายบั๊กภาษาไทย (+ screenshot ได้) | --debt]"
---

User request: $ARGUMENTS

Use the referenced command [review](../knowledge/commands/review.md) as the entry point for this request, applying it to the user request above. Follow only the branches that apply to the current task, and load additional references only when the command directs you to.
This is a discovery adapter, not a replacement for the command knowledge.
Resolve source-root paths beginning agents/, skills/, references/, commands/ or output-styles/ under this plugin's knowledge/ directory, not the user's project.
Use actual host tools and preserve host/project/user authority.
