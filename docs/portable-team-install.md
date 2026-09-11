# Ask Oliver 3.16 RC — install without scripts

Stable qualification is **Codex only**, per the user's revised release scope.
The other hosts below are experimental discovery locations, not verified support.

Source: [.agents/skills/ask](../.agents/skills/ask/SKILL.md).
Copy that folder with your editor or file manager into the target project. The
runtime distribution is `SKILL.md` plus its `references/` folder; copy both together.
References are read only when their mode applies. Do not copy this
repository's other `.agents` skills, scripts, hooks, output styles or `.plugin`.
No terminal, installer, language interpreter, symlink or generated config is needed.

## Choose a project location

| Host | Destination in target project | Evidence |
|---|---|---|
| Codex | `.agents/skills/ask/SKILL.md` | [Official skills documentation](https://learn.chatgpt.com/docs/build-skills) |
| Antigravity | `.agents/skills/ask/SKILL.md` | [Official skills documentation](https://antigravity.google/docs/skills) |
| Cursor | `.agents/skills/ask/SKILL.md` | [Official skills documentation](https://cursor.com/docs/skills) |
| Claude Code | `.claude/skills/ask/SKILL.md` | [Official skills documentation](https://code.claude.com/docs/en/skills) |

Documentation checked 2026-09-11. This table establishes documented discovery
locations, not successful execution tests on all four hosts. Use project-level
installation first so the preview does not affect unrelated projects.

Keep one installed copy per host's discovery scope. Cursor also discovers Claude
skill folders, so do not install both copies in a shared multi-host workspace.
For a shared workspace needing different locations, switch the folder location
when changing hosts until a single-location setup has been verified for all of
your host versions. Do not maintain divergent edits of the skill per platform.

## Activate and check

Start a new task/session and select or mention `ask` using the host's
skill interface. If it is missing, check the folder spelling and whether hidden
directories were copied; reload the workspace/session if needed. Confirm the
loaded skill path. Do not claim discovery merely because the file exists.

Try: "Use ask to review this API change. Review only; do not edit."
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

To uninstall, remove only the copied `ask` folder after preserving any
local edits. Task records and project artifacts are separate; leave them intact.

## Validation status

The release has one entrypoint; consult/design/implement are outcomes, not extra
commands. Oliver stays in the main session. First project use confirms the source
of truth and Markdown fallback. After a design, explicitly say "start implementing"
to authorize that scope; no second command is needed. An approved design alone
does not authorize edits, commits or deployment.

Maintainers run `make validate-portable` and `make pack` (Python 3.9+, build-time
only). Packaging writes the Codex-targeted portable ZIP into a fresh temporary
directory and prints its path/hash. It contains `ask/`. The optional maintainer
flag `python3 scripts/pack-portable.py --include-experimental` also builds an
unverified Claude-format archive; this does not establish host support. It contains
`skills/ask/` and a minimal plugin manifest. No legacy hooks or scripts are shipped.
For Claude, extract the plugin archive to a new folder and use the host's plugin
loading mechanism; its shortcut is namespaced `/shode-house:ask`. A project skill
uses `/ask`; other hosts use their native skill selector/mention syntax, not a
guaranteed identical slash command. Do not install both formats in one host.

Codex discovery and scoped live execution have been exercised. RC6
[selective-history tests](../eval/portable-team/HISTORY-RC6-2026-09-11.md) and
[recovery/blocker probes](../eval/portable-team/GAPS-RC6-2026-09-11.md) document
their exact outcomes and limitations. They do not establish all
[behavioral cases](../eval/portable-team/CASES.md), four-host parity, actual
compaction/concurrent-write recovery or general token savings. Whole-workflow
efficiency and Codex behavioral/recovery acceptance still block stable promotion.
