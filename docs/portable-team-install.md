# Portable team preview — install without scripts

Source: [.agents/skills/shode-house-team](../.agents/skills/shode-house-team/SKILL.md).
Copy that folder with your editor or file manager into the target project. The
runtime distribution is `SKILL.md` plus its `references/` folder; copy both together.
References are read only when their mode applies. Do not copy this
repository's other `.agents` skills, scripts, hooks, output styles or `.plugin`.
No terminal, installer, language interpreter, symlink or generated config is needed.

## Choose a project location

| Host | Destination in target project | Evidence |
|---|---|---|
| Codex | `.agents/skills/shode-house-team/SKILL.md` | [Official skills documentation](https://learn.chatgpt.com/docs/build-skills) |
| Antigravity | `.agents/skills/shode-house-team/SKILL.md` | [Official skills documentation](https://antigravity.google/docs/skills) |
| Cursor | `.agents/skills/shode-house-team/SKILL.md` | [Official skills documentation](https://cursor.com/docs/skills) |
| Claude Code | `.claude/skills/shode-house-team/SKILL.md` | [Official skills documentation](https://code.claude.com/docs/en/skills) |

Documentation checked 2026-09-11. This table establishes documented discovery
locations, not successful execution tests on all four hosts. Use project-level
installation first so the preview does not affect unrelated projects.

Keep one installed copy per host's discovery scope. Cursor also discovers Claude
skill folders, so do not install both copies in a shared multi-host workspace.
For a shared workspace needing different locations, switch the folder location
when changing hosts until a single-location setup has been verified for all of
your host versions. Do not maintain divergent edits of the skill per platform.

## Activate and check

Start a new task/session and select or mention `shode-house-team` using the host's
skill interface. If it is missing, check the folder spelling and whether hidden
directories were copied; reload the workspace/session if needed. Confirm the
loaded skill path. Do not claim discovery merely because the file exists.

Try: "Use shode-house-team to review this API change. Review only; do not edit."
Expected: scoped evidence-based review, no screenshot requirement for a pure API,
no request to install the old runtime or Beads, no automatic implementation.
Host and repository instructions still apply, including this repository's Beads
policy. Use a separate project to test the no-tracker fallback.

Before testing, disable the legacy Shode plugin in the host's plugin settings if
enabled, then start a fresh session. Its force-loaded output style/hooks can keep
applying independently of this skill. Do not disable unrelated security controls
or remove project rules. Report conflicting project rules instead of overriding
them. Keep the legacy package available for rollback.

## Resume a longer task

Ask the agent to save progress to the project's canonical task record at a work
boundary (Markdown, Jira, Redmine, Beads or another system). No tracker migration
is required. Specs and evidence may live elsewhere and be linked from that record.
If its connector is unavailable, keep the original ID/URL in a handoff marked
pending synchronization; do not report that remote status was updated.
Start a new session, select the skill again and supply that record's ID/path:
"Continue from this checkpoint; verify current files and evidence before proceeding."
The checkpoint is the continuity mechanism. Skill activation itself is not a
scheduler, a guarantee of persistence across compaction, or an enforced file lock.

To uninstall, remove only the copied `shode-house-team` folder after preserving any
local edits. Task records and project artifacts are separate; leave them intact.

## Validation status

Codex exposed the skill in this task's available-skills catalog after creation;
its body was read successfully. This proves local discovery/read only. The
[behavioral cases](../eval/portable-team/CASES.md) still require fresh host runs.
No measured token reduction, four-host parity, independent review or long-run
recovery success is claimed from documentation or static validation.
