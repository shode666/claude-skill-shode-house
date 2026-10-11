# Shode House 4.0.1 host notes

All 6 role sources and 20 skills are preserved under knowledge/. The agent files, skill roots and commands at the plugin root are those sources with plugin-root and `./`/`../` references re-pointed to their knowledge/ copies, plus a generated resolution footer; `/ask` is the pinned wrapper of the ask skill. Use ask as the entry.

- Claude Code: `.claude-plugin` manifest, flat skills, agents, the authored commands (`/ask` is the entry). Team execution (the router style delegating to specialist agents) is supported here only.
- Codex, Cursor, Antigravity: skills run in one session; there is no router style. Agent spawns return `BLOCKED: unrouted` by design; never replace delegation with role-play.
- On those hosts the safety floor is in the `ask` skill (other shode-house skills point to it); it applies only once loaded and can be lost when context is compacted. The only enforced control for irreversible actions there is the host's own command-approval and sandbox setting: keep approval on for shell and MCP actions.
- Manifests: `.codex-plugin` (skills), `.cursor-plugin` (skills; `ask` is a skill, no commands), root `plugin.json` (Antigravity). Antigravity's validator (agy 1.2.2) processes the agent files and converts the commands to skills. Whether agents run on Codex, Cursor or Antigravity, and whether their `model:` values are honoured there, is unverified.

Skill discovery does not prove separate workers are available. If delegation is unavailable, report team execution BLOCKED; never replace it with role-play.
No automatic hooks or MCP startup are included.
