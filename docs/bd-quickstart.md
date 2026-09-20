# bd Tool Quickstart + Alternatives

> shode-house ใช้ `bd` (Backlog Doctor — local-first git-native issue tracker) ตลอด workflow. ถ้าไม่มี bd → ใช้ alternative ที่ map ลงท่าเดียวกันได้

---

## Option 1: ติดตั้ง bd (recommended)

bd = local-first issue tracker, git-native, ไม่พึ่ง cloud, fit agent workflow.

### Install
```bash
# macOS / Linux (Homebrew or direct binary — ดู project README ของ bd ที่ใช้)
# Project: https://github.com/dustinblackman/backlog-doctor (หรือ fork ที่ user เลือก)

# ตัวอย่าง quick install (ปรับตาม project distribution):
brew install bd                                  # ถ้ามี Homebrew tap
# หรือ curl -L https://.../bd-installer.sh | bash
```

### Init ใน repo
```bash
cd ~/your-project
bd init                       # สร้าง .beads/ folder
git add .beads/ && git commit -m "chore: init bd tracker"
```

### Commands ที่ shode-house ใช้บ่อย
| Command | What |
|---|---|
| `bd create -t feature "title"` | สร้าง issue ใหม่ |
| `bd list --status=ready` | ดู ready queue |
| `bd list --status=in_progress` | ดู in-progress |
| `bd show <id>` | ดู detail issue |
| `bd update <id> --claim` | claim ทำเอง |
| `bd update <id> --notes "..."` | post review/finding |
| `bd close <id>` | mark closed |
| `bd remember <lesson>` | post-bd reflect (lesson learned) |
| `bd ready` | next ready issue (Oliver pick) |

---

## Beads internals and agent protocol (relocated from `AGENTS.md`, v3.17)

`AGENTS.md` keeps only repo-wide rules. The Beads detail that used to live there is kept here. It is task-tracking guidance, not permission to override repository, user, or orchestrator instructions.

### Storage and sync architecture

- Issues live in a local Dolt database (`.beads/dolt/`, or `.beads/embeddeddolt/` in embedded mode).
- Cross-machine sync uses `bd dolt push` / `bd dolt pull` (a git-compatible protocol). The data is stored under `refs/dolt/data` on your git remote — separate from `refs/heads/*` where your code lives.
- `.beads/issues.jsonl` is a passive export, not the wire protocol and not the source of truth.
- One-screen overview and anti-patterns: [SYNC_CONCEPTS.md](https://github.com/gastownhall/beads/blob/main/docs/SYNC_CONCEPTS.md) — don't treat JSONL as the source of truth; don't `bd import` during normal operation; don't reach for third-party Dolt hosting before trying the default.
- Remote sync is a Safety-gated action in `AGENTS.md`: run `bd dolt push` / `bd dolt pull` only when authorized.

### Agent Context Profiles

- **Conservative (default)**: Use `bd` for task tracking. Do not run git commits, git pushes, or Dolt remote sync unless explicitly asked. At handoff, report changed files, validation, and suggested next commands.
- **Minimal**: Keep tool instruction files as pointers to `bd prime`; use the same conservative git policy unless active instructions say otherwise.
- **Team-maintainer**: Only when the repository explicitly opts in, agents may close beads, run quality gates, commit, and push as part of session close. A current "do not commit" or "do not push" instruction still wins.

This repository runs the **Conservative** profile.

### Session Completion

Applies when ending a Beads implementation workflow. Subordinate to explicit user, repository, and orchestrator instructions.

1. **File issues for remaining work** — create beads for anything that needs follow-up
2. **Run quality gates** (if code changed) — tests, linters, builds
3. **Update issue status** — close finished work, update in-progress items
4. **Handle git/sync by active profile**:
   ```bash
   # Conservative/minimal/default: report status and proposed commands; wait for approval.
   git status

   # Team-maintainer opt-in only, unless current instructions forbid it:
   git pull --rebase
   bd dolt push
   git push
   git status
   ```
5. **Hand off** — summarize changes, validation, issue status, and any blocked sync/commit/push step

Critical rules: explicit user or orchestrator instructions override Beads guidance; do not commit or push without clear authority from the active profile or the current user request; if a required sync or push is blocked, stop and report the exact command and error.

Also: use `bd remember` for persistent project knowledge rather than ad hoc memory files; `bd prime` prints the full command reference.

### Keeping the bd-managed blocks out of `AGENTS.md`

Verified with bd 1.2.2 in a scratch repo (2026-09-20):

| Command | Effect on `AGENTS.md` |
|---|---|
| `bd prime`, `bd ready`, `bd create`, `bd init --init-if-missing` (already initialized) | none |
| `bd init` (fresh / re-init) | appends `<!-- BEGIN BEADS INTEGRATION ... profile:minimal -->` block (~3 KB incl. profiles + session completion) **and** runs the codex setup below. `--agents-profile` only offers `minimal` (default) or `full`; `--agents-template` is ignored when `AGENTS.md` already exists |
| `bd init --skip-agents` | none — this is the opt-out |
| `bd setup codex` | appends `<!-- BEGIN BEADS CODEX SETUP -->` block (second `## Beads Issue Tracker`) **and overwrites `.agents/skills/beads/SKILL.md`** with the stock skill — never hand-edit that skill; put local detail in this file |
| `bd setup codex --remove` | removes the codex block, but also deletes the beads skill and `.codex/hooks.json` — do not use |

Policy: re-initialize only with `bd init --skip-agents`; do not run `bd setup codex` in this repo. If a block reappears: `git checkout -- AGENTS.md` (or delete everything between the `BEGIN BEADS` / `END BEADS` markers, inclusive).

---

## Option 2: ไม่มี bd — ใช้ Linear / Jira / GitHub Issues

shode-house workflow ทำงานได้ทุก tracker ถ้า map คำสั่งให้ถูก. Agent ใช้ "bd" เป็น **abstraction**, user เปลี่ยน implementation ได้

### Mapping: bd ↔ alternative

| Concept | bd | Linear | Jira | GitHub Issues |
|---|---|---|---|---|
| Create issue | `bd create` | Linear UI / CLI / MCP | Jira UI / API | `gh issue create` |
| Issue ID format | `bd-42` | `TEAM-42` | `PROJ-42` | `#42` |
| State machine | `ready/in_progress/closed` | Triage/Todo/In Progress/Done | To Do/In Progress/Done | Open/Closed + labels |
| Claim issue | `bd update --claim` | Assign to self | Assign + transition | Self-assign |
| Notes | `bd update --notes` | Issue comment | Comment + transition | Issue comment |
| Lesson capture | `bd remember` | Comment + label `lesson` | Add to Wiki / comment | Create discussion / comment |
| Ready queue | `bd ready` | View "Ready" status | JQL: `status=To Do` | `gh issue list --label ready` |

### Configure shode-house to use alternative

ใน `outputs/SESSION-STATE.md` ระบุ tracker:
```yaml
tracker: linear      # or jira | github | bd
tracker_config:
  workspace: my-team
  project: shode-house-demo
```

Oliver จะ adapt command mapping ตาม tracker ที่เลือก.

### Manual workflow (no tracker)

ถ้าไม่มี tracker เลย → file-based fallback:
- `outputs/bd-<id>-<feature>.md` per "issue" (manually create)
- Oliver maintain `outputs/SESSION-STATE.md` ระบุ active "bd"
- Review report `outputs/REVIEW-bd-<id>.md`
- ⚠ ระวัง: ไม่ scale, ไม่มี state machine — แนะนำสำหรับ spike เท่านั้น

---

## Why bd-native (vs cloud tracker)

| Aspect | bd (local-first) | Cloud (Linear/Jira/GH) |
|---|---|---|
| Latency for agent ops | ✅ instant (local fs) | ⚠ network round-trip |
| Offline | ✅ | ❌ |
| Token cost per call | ✅ minimal | ⚠ API response parse |
| Discoverability for new dev | ⚠ tool install needed | ✅ web UI |
| Cross-team sharing | ⚠ git-based sync | ✅ realtime |
| Lock-in | ✅ git-native = portable | ⚠ vendor-coupled |

**shode-house recommendation**: bd-native for solo / small team; cloud tracker for cross-team coordination. Both work.

---

## Common issues

### "command not found: bd"
→ ติดตั้งตาม Option 1, หรือเลือก alternative ตาม Option 2

### "Oliver พยายามรัน bd แต่ failed"
→ ตรวจ `outputs/SESSION-STATE.md` ระบุ `tracker` ถูกประเภทไหม. ถ้า user ใช้ Linear, ระบุ `tracker: linear`

### "Agent อ้าง bd-42 ที่ไม่มี"
→ Oliver/agent อาจ hallucinate ID. ตรวจ list จริง: `bd list` / `gh issue list` / Linear search. ห้าม trust ID จาก message; ต้อง verify

### "Multiple agents claim issue เดียวกัน"
→ shode-house enforce single-claim (drift M5+M7). ตรวจ `bd show <id>` — ถ้ามี multi-claimer = workflow drift, escalate Oliver

---

## See also

- `skills/discipline/shode-house-workflow/SKILL.md` § PEV Loop — full lifecycle per bd
- `skills/discipline/shode-house-drift/SKILL.md` § M5/M6 — bd state pin + revision rules
- `skills/discipline/shode-house-evidence/SKILL.md` § Storage — bd notes primary, markdown fallback
