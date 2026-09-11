# Ask Oliver 3.16.0 — install without scripts

Stable qualification is **Codex only**, per the user's revised release scope.
The other hosts below are experimental discovery locations, not verified support.

Source: [.agents/skills/ask](../.agents/skills/ask/SKILL.md).
Copy that folder with your editor or file manager into the target project. The
shared instruction source is `SKILL.md` plus its `references/` folder; copy both together.
References are read only when their mode applies. Do not copy this
repository's other `.agents` skills, scripts, hooks, output styles or `.plugin`.
No terminal, installer, language interpreter, symlink or generated config is needed.
For the complete Codex UI configuration, use the packaged `ask/` folder; it also
includes `agents/openai.yaml`. When installing directly from source, copy
`release/hosts/codex/openai.yaml` into the target skill's `agents/openai.yaml`.

## Choose a project location

### Marketplace installation

The repository marketplace on `main` now points to `plugins/shode-house`, an
isolated install tree containing only the shared ask skill and host metadata.
It has native Codex and Claude manifests, no root legacy hooks, MCP servers or
19-agent roster. The root `.claude-plugin/plugin.json` remains the legacy build
manifest; it is no longer the marketplace entry's source.

If a cached catalog still displays 3.15 / 23 skills / Context7 / hooks, refresh
the marketplace from its Git source before installing or updating. Confirm the
new card shows 3.16.0 and one ask skill without hooks/MCP. Start a fresh session
after updating; existing sessions may retain legacy instructions. Do not disable
unrelated security controls. The immutable v3.16.0 tag predates this catalog repair;
use current `main` for marketplace discovery, or the original release assets.

The tracked install-tree Markdown copies must match the canonical release bytes;
`tests/test_marketplace_release.py` checks drift, routing and contamination in CI.
No generation script is required on the installing user's machine.

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

### Host configuration included

| Host | Packaged configuration | Purpose |
|---|---|---|
| Codex | `ask/agents/openai.yaml` | Skill display name, short description and `$ask` starter prompt |
| Claude Code (experimental) | `.claude-plugin/plugin.json` | Plugin identity; version/description filled from the release manifest at build time |

The Claude package contains `skills/ask/` with the same six instruction files;
the Codex-only UI metadata is not copied into it. A plain Claude project-skill
installation needs only `.claude/skills/ask/`, not a plugin manifest.

No `config.toml`, `settings.json`, MCP configuration or custom native agent roster
is required for this design. Existing host model, permissions and project rules
remain unchanged. `agents/openai.yaml` is UI metadata, **not a subagent definition**.
Oliver stays in the main session; optional experts use available host delegation,
not legacy agent files. The skill declares no `context: fork`, model override or
tool permission grant. Automatic skill selection keeps the host default.

These formats follow [Codex skill metadata](https://learn.chatgpt.com/docs/build-skills)
and [Claude plugin configuration](https://code.claude.com/docs/en/plugins-reference).
Configuration/packaging checks do not establish equivalent agent behavior.

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

Codex discovery and scoped live execution have been exercised. Current-source
[RC9 behavior/recovery](../eval/portable-team/BEHAVIOR-RC9-2026-09-11.md) passes
the tested first-use, edits, diagnosis, missing-reference, risk, manual compaction
and same-line annotation recovery cases. These do not guarantee arbitrary
concurrent merges, automatic compaction, multi-day uptime or four-host parity.
[RC9 matched efficiency](../eval/portable-team/BENCHMARK-RC9-2026-09-11.md) still
FAILS the combined token gates despite reducing total volume in both scenarios.
RC10 added host metadata/packaging only; the six instruction files in 3.16.0 are
unchanged from RC9. New UI metadata has static validation, not live-host acceptance
testing. Stable promotion uses the shared instruction/workflow contract as the
release boundary and accepts the failed token gates as a disclosed exception.
This is not a claim of monetary savings, deterministic enforcement, complete domain
expert knowledge or equivalent outcomes across models. See the
[release decision](../release/3.16-notes.md).
