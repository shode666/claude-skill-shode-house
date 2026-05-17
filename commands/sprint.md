---
description: "[shode-house] Sprint management (Pre-Sprint / Sprint Close / Retro) — v2.8 outer loop"
allowed-tools: Task, Read, Write, Edit, Bash
argument-hint: [pre | close | status | retro]
---

🏃 **Sprint command** — outer cadence layer ของ Smart Coop workflow

Sub-command: **$ARGUMENTS** (pre / close / status / retro)

## `/sprint pre` — Pre-Sprint Planning

Oliver kicks off new sprint:

### 1. Audit current backlog
```bash
bd ready --json | jq '.[] | {id, title, priority}'   # ready tasks
bd stats                                              # backlog stats
bd list --status=in_progress                          # carry-over
bd list --discovered-this-sprint                      # discovered (P4 etc)
```

### 2. Sprint goal + capacity
- Sprint goal (1-2 sentences): มุ่ง outcome ไหน?
- Team capacity: [N person-days]
- T-shirt budget: XS+S+M = primary; L+XL = split

### 3. Create / Prioritize issues
```bash
# Create new issues
bd create -t feature -p1 "..." --linked-to=goal
bd create -t bug -p1 "..."

# Re-prioritize existing
bd update <id> --priority=p0   # promote
bd update <id> --priority=p3   # defer
```

### 4. Sprint config
```bash
cat > .shode-house/sprint.yaml <<EOF
sprint: <N>
goal: "[goal]"
start: <date>
end: <date>
capacity_days: <N>
issues:
  - bd-<id> (P0/P1/P2)
EOF
git add .shode-house/sprint.yaml
git commit -m "sprint-<N>: kick-off"
```

### 5. Hand-off → Sprint Exec
```
[Oliver|state:sprint-start|sprint:<N>] Sprint <N> kick-off
- Goal: [...]
- Issues: [count]
- Capacity: [days]
- Next: /implement bd-<top P0>
```

## `/sprint status` — Mid-Sprint Check (anytime)

```bash
bd stats                              # snapshot
bd list --status=in_progress          # WIP
bd list --status=blocked              # blocked
bd ready --json | jq 'length'         # remaining
bd list --discovered-this-sprint      # new discovered

# Loop health
echo "iter avg: $(bd list --field=iter | awk '{s+=$1} END {print s/NR}')"
```

Oliver report:
```
[Oliver|state:sprint-status|sprint:<N>] mid-sprint
- Done: X / Y (Z%)
- In progress: <ids>
- Blocked: <ids + reason>
- Discovered: <count> (P4 deferred)
- Risk: [if any]
```

## `/sprint close` — Sprint Close

Inner loop exhausted? Check:
- `bd ready --json | jq length` == 0
- `bd list --status=in_progress` == empty
- Last review iteration → 0 Critical/Major

### 1. Close completed issues
```bash
# (already closed via /implement Phase 4 Triage; just verify)
bd list --status=closed --in-sprint=<N>
```

### 2. Deploy queued (Phase 5 — Aaron batched)
```bash
# Aaron: deploy all closed issues that hit pre-loop-exit gate
make deploy-staging
# Quinn: smoke staging
# Aaron: deploy-uat → uat sign-off → deploy-prod
```

### 3. git push + tag
```bash
git push origin main
git tag -a sprint-<N> -m "Sprint <N> close — [goal summary]"
git push origin sprint-<N>
```

### 4. bd remember (capture lessons)
```bash
bd remember "Sprint <N> insight: [key learning]"
bd remember "Anti-pattern caught: [e.g., 'Dave bypassed Uma POST 2x — strengthen gate']"
bd remember "Loop iter avg: [N] (target ≤ 1.5)"
bd dolt push    # if using dolt
```

### 5. Retrospective (Oliver 1-page)

Save to `outputs/RETRO-sprint-<N>.md`:

```markdown
# Sprint <N> Retrospective — [date]

## Summary
- Goal: [...]
- Done: X / Y
- Discovered: Z new issues
- Avg loop iter: N

## What went well
- [...]

## What went poorly (no blame)
- [...]

## Action items (next sprint)
- [ ] [actionable change] (owner: [agent], bd: bd-N)

## Metrics
- Loop iter: avg / max / median
- Phase fail rate: 1a / 1b / 2 / 3a / 3b
- Gate bypass attempts: [count]
- Time per phase: [avg]
```

### 6. Hand-off → Next sprint
```
[Oliver|state:sprint-done|sprint:<N>] Sprint <N> closed ✅
- Closed: X
- Discovered: Z (carried to backlog)
- Retro: outputs/RETRO-sprint-<N>.md
- Lessons: bd remember (5 entries)
- Next: /sprint pre
```

## `/sprint retro` — Retro only (without close)

ใช้กรณี mid-sprint retrospective หรือ post-mortem ad-hoc — รัน step 5 ของ `/sprint close` อย่างเดียว

## ⚠️ Rules

1. 🔴 v2.8 — **บังคับ Pre-Sprint planning** ก่อนเริ่ม inner loop. ห้าม start `/implement` โดยไม่มี sprint context
2. 🔴 v2.8 — **Sprint Close แค่เมื่อ inner loop exhausted** (bd ready empty + in_progress empty + 0 critical last review). ยังไม่ครบ = ยัง mid-sprint
3. 🔴 v2.8 — **บังคับ retro 1-page** ทุก sprint close (capture lesson + metric)
4. 🔴 v2.8 — **บังคับ bd remember** capture lesson (rebuilds prompt knowledge cross-sprint)
5. Deploy = Aaron batched sprint-end (ไม่ใช่ per-issue deploy ทุก commit) — exception: hotfix
6. ภาษาไทย
