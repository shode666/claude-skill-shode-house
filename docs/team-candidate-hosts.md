# Full-team candidate packaging

Maintainer-only `scripts/pack-team.py` builds test archives. It does not install,
publish, certify compatibility, or introduce a runtime dependency. Source version
is retained: a 3.15.0-based candidate is not a released 3.16.1.

Every variant keeps the full original-layout knowledge tree, 19 role sources and
24 skill discovery adapters (23 retained skills plus ask). Only selected roles and
their prerequisites are loaded during work. Oliver remains the main session.

| Target | Configuration | Meaning and limits |
|---|---|---|
| `claude-codex` | `.claude-plugin/plugin.json`, `.codex-plugin/plugin.json` | Flat skill discovery; Claude agent adapters and one ask command. A Codex catalog result does not establish native registration of the agent files. |
| `cursor` | `.cursor-plugin/plugin.json` | Native agent adapters use inherited model settings, not Claude tool/model metadata. Ask is a skill; no duplicate command. |
| `antigravity` | root `plugin.json` marker | Flat skills plus full role resources. This is not a claim that the host registers agent files or can run an independent team. |

No automatic hooks, MCP startup or runner scripts ship as runtime components.
Markdown can carry durable state; it cannot enforce locks, run in the background,
or guarantee exactly-once external effects. Required independent verification stays
blocked when the host has no real delegation facility.

Build a variant with `python3 scripts/pack-team.py --host cursor` (or
`antigravity` / `claude-codex`). Output goes to a unique temporary directory by
default. Existing artifact names are never overwritten. Building does not mutate
the user's plugin installations or marketplace source.

Structural tests check source preservation, adapter reachability and configuration
separation. Live delegation, resume/UNKNOWN reconciliation, remote-source installation
and host-specific runtime behavior require their own evidence; archive validity is
not an execution verdict. See the canonical recovery issue `shode-house-qdu` for
current qualification status rather than treating this document as a task tracker.

## Configuration sources

Checked 2026-09-12. Host documentation changes; verify these before publication.

- [Cursor plugin formats](https://cursor.com/docs/plugins) and
  [official native manifest template](https://github.com/cursor/plugin-template/blob/main/plugins/starter-advanced/.cursor-plugin/plugin.json).
- [Cursor subagents](https://cursor.com/docs/subagents): separate contexts and
  supported metadata, including inherited model selection.
- [Antigravity plugins](https://antigravity.google/docs/plugins): root marker and
  skill directory; this page does not establish native custom-agent registration.
- [Antigravity skills](https://antigravity.google/docs/skills): discovery and
  full instruction activation.
