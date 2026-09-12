# Multi-host package: `plugins/shode-house`

`scripts/pack-team.py --tree plugins/shode-house` generates the committed package from the
repository source; `--check plugins/shode-house` (run by CI gate #25) fails on any drift.
`--out DIR` builds the same tree as a `.plugin` archive for Cowork / release assets.

One tree serves four hosts:

| Host | Manifest | What is discovered |
|---|---|---|
| Claude Code | `.claude-plugin/plugin.json` | 24 flat skills, 19 agent adapters, `/shode-house:ask` |
| Codex | `.codex-plugin/plugin.json` | 24 skills (agent files are not a Codex concept) |
| Cursor | `.cursor-plugin/plugin.json` | skills + agents by folder discovery; `commands: []` because `commands/ask.md` uses the Claude command dialect |
| Antigravity | root `plugin.json` | skills only; agents are knowledge resources, not native registrations |

Layout: `knowledge/` holds every original file byte-for-byte (19 `agents/*.md`, the five
skill buckets, `references/`, `output-styles/`, `commands/`). `agents/` and `skills/` are
thin discovery adapters whose only job is to make the host read the full source and its
prerequisite skills. Adapter frontmatter is host-neutral: `name`, `description`, `tools`,
`skills`, `model: inherit` (Claude `color` and model aliases are dropped so no host has to
resolve another host's model names). No hooks, MCP servers or runner scripts ship in the
package; the harness is a coordination contract, not a runtime.

Limits that stay true regardless of layout: skill discovery does not prove separate
workers exist; when a host has no delegation tool, required independent review is
BLOCKED and Oliver must say so. Markdown checkpoints support resumption but cannot
enforce locks or exactly-once external effects. Live evidence per host is recorded in
CHANGELOG under the release entry, not here.

## Evidence status per host

| Host | Evidence so far | What counts as done |
|---|---|---|
| Claude Code | Live forward + resume runs (3.16.1), GitHub install + `/ask` reachability (3.16.1) | done; re-score any run with `scripts/team-run-check.py` |
| Codex | app-server catalog read: 24 skills discovered (3.15 candidate) | one `ask` session on a fixture that delegates or honestly reports BLOCKED; capture the transcript |
| Cursor | manifest/discovery only | install from this repo, run `ask` on a fixture, confirm a subagent from `agents/` actually starts |
| Antigravity | manifest/discovery only | install into `.agents/plugins/`, run `ask`; expected result is Oliver reporting team execution BLOCKED (no delegation tool) |

Gather host evidence with the same fixture and prompts as `outputs/live-3.16.1/run.sh`
(maintainer machine); a host is "supported" in the README only after its row is done.

Host documentation checked 2026-09-12 (verify again before changing manifests):
[Cursor plugins](https://cursor.com/docs/plugins) · [Cursor plugin reference](https://cursor.com/docs/reference/plugins)
· [Antigravity plugins](https://antigravity.google/docs/plugins) · [Antigravity skills](https://antigravity.google/docs/skills).
