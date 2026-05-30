# Migration Guide: v3.2.0 → v3.3.0

> v3.2.0 tagged แต่ SUPERSEDED same day. v3.3.0 = simplification. ถ้าคุณติดตั้ง v3.2.0 ไปแล้ว ใช้ guide นี้

---

## TL;DR

```
v3.2.0 → v3.3.0:
  ❌ Drop /sprint command + Evan evaluator agent
  ✅ PEV loop per bd (Plan → Execute → Verify → Triage)
  ✅ Bias discipline embedded ใน 19 agent prompts
  ✅ Chris/Quinn adversarial vs Dave + Claude in Chrome MCP mandatory
  ✅ No man-day negotiation (universal rule)
```

Reinstall:
1. ลบ v3.2.0 จาก Cowork plugin list
2. Drag-drop `shode-house-v3.3.0.plugin` install ใหม่

---

## Breaking changes

### 1. `/shode-house:sprint` removed
**ก่อน v3.3** (v3.2):
```
/shode-house:sprint pre       # Pre-Sprint planning
/shode-house:sprint close     # Sprint close + deploy
/shode-house:sprint retro     # Retro
```

**v3.3.0 replacement**:
```
# ไม่มี sprint command. ทำงาน per bd:
/shode-house:design-system <feature>     # Phase 1a + 1b spec
"ลุยต่อ"                                   # Oliver M2 → /implement
# Phase 2-4 PEV loop ทำต่อ
# Deploy = continuous per bd (Aaron deploy เมื่อ bd ready) หรือ user manual batch
```

**Why**: Agent ไม่ต้องการ sprint time-box (human concept). ส่งงาน task-complete, ไม่ใช่ time-bound.

---

### 2. Evan (evaluator agent) removed
**ก่อน v3.3** (v3.2):
- `agents/evaluator.md` (Evan) — offline bias evaluator
- `/shode-house:eval-harness` — manual eval trigger
- `outputs/EVAL-<agent>-<date>.json` outputs

**v3.3.0 replacement**:
- Bias rules **embedded** ใน 19 agent prompts (per agent `## 🎯 Bias Discipline` section)
- Universal rule ใน `shode-house-discipline` § No-Bias
- Eval harness skill + 19 fixtures ย้ายไป `skills/in-progress/eval-harness/` (offline maintainer use; ไม่ ship)

**Why**: Evan + 19 fixtures + runner = over-engineer for current scale. Prompt rules solve 80% directly. Chris/Quinn ตรวจ Evan ไม่ได้ (self-preference bias) → embed บ่อน trust gap

---

### 3. Phase 7 (Sprint Learn) removed
**ก่อน v3.3** (v3.2):
- Phase 7 = sprint retro / monthly review
- Patrick + Oliver co-lead
- `/sprint close retro` trigger

**v3.3.0 replacement**:
- Per-bd reflect ใน Phase 4 Triage (Oliver `bd remember <lesson>` post bd close)
- Patrick continuous OKR review (per-bd contribution)
- No bracket; continuous instead of periodic

---

### 4. T-shirt sizing no longer user-facing
**ก่อน v3.3** (v3.2):
- Oliver engagement plan ระบุ `Size: [T-shirt]`
- "Total: ~5 days" estimate ใน pipeline summary

**v3.3.0 replacement**:
- T-shirt = **internal routing heuristic only** (Oliver parallel/sequential decision)
- ห้าม expose ใน engagement plan ส่งต่อ user
- User explicit `--estimate` flag → estimate ส่ง for external report only

**Why**: Agent ทำงานไม่ตรงตาม man-day → ห้ามใช้ man-day ต่อรองเวลากับ user

---

### 5. Aaron Phase 5 batched-sprint-end → continuous per bd
**ก่อน v3.3** (v3.2):
- Aaron deploy batched ตอน sprint close
- Trigger: `/sprint close` invoked
- Tag: `sprint-<N>` after stable

**v3.3.0 replacement**:
- Aaron deploy continuous per bd ready (or user manual batch optional)
- Trigger: Phase 4 Triage clean + multi-sig gate
- Tag: `bd-<id>-deploy-<timestamp>`

---

## Non-breaking additions

### 6. Chris/Quinn Adversary Stance + Claude in Chrome MCP mandatory

Chris และ Quinn now work **adversarially vs Dave**:
- Verdict default = **FAIL** until proven PASS with own-run evidence
- Zero trust on Dave's claims — must run + paste output themselves
- ห้าม dismiss marginal issue → grade ≥🟡

ทุก frontend / API observable / user journey → บังคับ `mcp__Claude_in_Chrome__navigate`:
- Screenshot path
- Console messages
- Network requests

**Action**: ตรวจ Claude in Chrome extension ติดตั้งใน Chrome browser (`mcp__Claude_in_Chrome__*` tools). ถ้าไม่มี → Aaron install ก่อน

---

### 7. Dave Adversary-Aware Hand-off

Dave (developer) aware ของ Chris/Quinn adversarial stance:
- Proactive evidence paste ทุก hand-off
- ห้าม "should be fine" push-back → counter ด้วย own-run evidence only
- Spin local + Chrome MCP ตัวเอง ก่อน hand-off (frontend)

---

### 8. Bias Discipline section per agent

ทุก agent มี `## 🎯 Bias Discipline (v3.3 — per shode-house-discipline § No-Bias)` section:
- Sycophancy (Oliver/Dave/Sentinel/Iris)
- Anchoring (Bella/Patrick/Elena)
- Pattern-bias (Sara/Aaron/Uma/Felix/Tara/Brooke/Emma)
- Verdict skew (Chris/Quinn)
- Convergence (Stan)
- Alert dismissal (Reggie)
- Std-vs-custom (Sam)

---

### 9. No Man-Day Negotiation universal rule

ใน `shode-house-discipline/SKILL.md` มี section ใหม่:
- ห้าม agent propose timeline / man-day โดย user ไม่ร้องขอ
- ห้าม refuse งาน เพราะ "ใหญ่เกิน X sprint"
- ห้ามใช้ man-day ต่อรองเวลา
- Exception: user explicit ขอ estimate → for external report only

---

## Workflow migration

### Old (v3.2) workflow
```
/sprint pre         # Oliver Pre-Sprint
  → bd audit, P0/P1/P2 create
  → Patrick OKR alignment check
/implement bd-42    # Phase 2-4 inner loop
/implement bd-43    # next bd
...
/sprint close       # Oliver Sprint Close
  → batched deploy (Aaron)
  → retro (Patrick + Oliver)
/shode-house:eval-harness chris   # Evan run on Chris
```

### New (v3.3) workflow
```
# No /sprint command. Just per-bd PEV loop:
/design-system <feature>     # Phase 1a + 1b spec
"ลุยต่อ"                      # Oliver M2 auto → /implement bd-42

# Per bd: Phase 2 (Dave) → Phase 3a (Uma + Chrome MCP) → Phase 3b (Chris ∥ Quinn adversarial + Chrome MCP) → Phase 4 (Oliver Triage)

# Phase 5 Deploy = continuous per bd ready (Aaron) — no batch wait

# Patrick continuous OKR review — no sprint retro bracket
# Per-bd reflect: Oliver `bd remember <lesson>` on close

# No Evan — bias rules ใน Chris/Quinn/etc. prompts already
```

---

## File migration checklist

| What | Action |
|---|---|
| `outputs/EVAL-*.json` (Evan output) | Stale — ignore. v3.3 ไม่สร้างใหม่ |
| `outputs/RETRO-sprint-<N>.md` | Stale — v3.3 ใช้ `bd remember` per bd แทน |
| `outputs/SESSION-STATE.md` | คงเก่า — Oliver still maintains; just no sprint state line |
| `.claude/hooks/session_*.{py,sh,cmd}` | v3.2 reverted; v3.3 ไม่มี hooks. ลบได้ |
| `.claude/settings.local.json` `hooks` field | ลบ section `SessionStart`/`SessionEnd` ถ้ามี |
| `tests/eval-fixtures/` | ย้ายไป `skills/in-progress/eval-harness/fixtures/` (handled by v3.3 install) |
| `scripts/run_eval.py` | ย้ายไป `skills/in-progress/eval-harness/run_eval.py` (handled) |
| `scripts/check_evidence.py` + `sprint_metrics.py` | Removed in v3.3 (heavy telemetry reverted) |

---

## Verification after install

```bash
# 1. Version
grep version ~/development/shode-house/.claude-plugin/plugin.json
# expect: "version": "3.3.0"

# 2. Lint passes
cd ~/development/shode-house
bash scripts/lint.sh
# expect: ✅ ALL 8 LINT CHECKS PASS

# 3. Agent count
ls ~/development/shode-house/agents/*.md | wc -l
# expect: 19

# 4. No /sprint command
ls ~/development/shode-house/commands/sprint.md 2>/dev/null
# expect: file not found

# 5. No Evan
ls ~/development/shode-house/agents/evaluator.md 2>/dev/null
# expect: file not found

# 6. Bias Discipline ใน 19 agents
grep -l "Bias Discipline" ~/development/shode-house/agents/*.md | wc -l
# expect: 19
```

---

## Rollback

ถ้า v3.3.0 มีปัญหา → rollback:
```bash
cd ~/development/shode-house
git checkout v3.2.0  # หรือ v3.1.1 ถ้าต้องการเก่ากว่า
bash scripts/build-plugin.sh
# install ใหม่
```

แต่ **v3.3.0 = recommended baseline** เพราะ:
- Lighter (no Evan/sprint over-engineer)
- Cross-platform clean (zero host dep)
- Bias discipline embedded (single source of truth)
- Chris/Quinn adversarial = bias defense built-in

---

## See also

- `CHANGELOG.md` § [3.3.0] — full change list + lessons learned
- `SHODE-HOUSE-MASTER.md` — current state + design decisions
- `skills/discipline/shode-house-discipline/SKILL.md` § No-Bias — universal rule
- `skills/discipline/shode-house-workflow/SKILL.md` § PEV Loop — new workflow
- `agents/code-reviewer.md` + `agents/qa-engineer.md` § Adversary Stance — Chris/Quinn behavior change
