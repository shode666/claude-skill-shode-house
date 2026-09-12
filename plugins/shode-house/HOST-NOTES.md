# Shode House 3.16.2 host notes

All 19 role sources and 24 skills are preserved under knowledge/. Use ask as the entry; Oliver is the main session.

- Claude Code / Codex: `.claude-plugin` / `.codex-plugin` manifests, flat skills, agent adapters, `/ask` command.
- Cursor: `.cursor-plugin` manifest; skills and agents discovered, no command (ask is a skill).
- Antigravity: root `plugin.json` marker; skills only. Agent files are knowledge, not native registrations.

Skill discovery does not prove separate workers are available. If delegation is unavailable, report team execution BLOCKED; never replace it with role-play.
No runtime scripts, automatic hooks or MCP startup are required.
