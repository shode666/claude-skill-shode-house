# shode-house — Master Handoff (v3.3.0, May 30, 2026)

> เปิดอ่านไฟล์เดียวก่อนเริ่ม session ใหม่. ครอบ current state + design decisions + audit trail
> v3.2.0 tagged but SUPERSEDED same day by v3.3.0 (over-engineering revert). ดู CHANGELOG.md

---

# 📌 PART 1 — Current State

**Plugin**: `shode-house` v3.3.0 (Simplification — PEV loop + embedded bias discipline)
**Workspace**: `~/development/shode-house/`
**Package**: `shode-house-v3.3.0.plugin` (260K, 99 files)
**Repo**: https://github.com/shode666/claude-skill-shode-house

**Composition**:
- **19 agents** (Oliver/Patrick/Stan + Lead; Bella/Sara/Uma; Dave; Chris/Quinn/Sentinel; Aaron/Reggie; 7 domain experts)
- **18 shipped skills** (workflow 4 + ops 3 + ui 2 + style 1 + discipline 8)
- **1 in-progress skill** (`eval-harness` — maintainer-only offline regression tool; ไม่ ship)
- **5 commands** (consult, init, design-system, implement, review) + 2 deprecated alias

---

# 🎯 PART 2 — v3.3.0 Key Decisions (from session 2026-05-30)

## 1. Drop sprint outer loop → PEV loop per bd
- Agent ไม่ต้องการ sprint time-box (human concept)
- Workflow = Plan → Execute → Verify → Triage **per bd**
- Deploy = continuous per bd (or user manual batch)
- Phase 7 (Sprint Learn) removed; per-bd reflect ใน Phase 4 Triage
- Patrick OKR review = continuous (per-bd contribution)

## 2. Drop Evan (evaluator agent) → embed bias discipline ใน 19 agents
- Evan + 19 fixtures + run_eval.py = over-engineer for current scale
- Prompt rules solve 80% of bias detection directly
- 19 agents now มี `## 🎯 Bias Discipline` section (sycophancy/anchoring/pattern-bias/...)
- Eval harness skill + 19 fixtures kept ใน `skills/in-progress/eval-harness/` (offline maintainer use)

## 3. Chris/Quinn adversarial vs Dave + Claude in Chrome MCP mandatory
- Verdict default = **FAIL** until proven PASS with own-run evidence
- Zero trust on Dave's claims — Chris/Quinn ต้อง run + paste output เอง
- Frontend/API/observable touched = บังคับ `mcp__Claude_in_Chrome__navigate` + screenshot + console + network
- Dave aware: proactive evidence paste; ห้าม "should be fine" push-back

## 4. No Man-Day Negotiation (universal rule)
- Agent ไม่ propose timeline / man-day / sprint-bound estimate โดย user ไม่ร้องขอ
- Agent ทำงานไม่ตรงตาม man-day → ห้ามใช้เป็นเหตุผลต่อรอง
- ถ้า user ขอ `--estimate` → for external report only, ไม่ใช่ agent scope contract
- T-shirt sizing = internal routing heuristic (Oliver parallel/sequential decision), ไม่ส่งต่อ user

## 5. Cross-platform principle
- Scripts ใน Claude Code Bash sandbox = Linux+Python (always)
- User host OS ไม่ต้องมี Python/dep (Mac/Win/Linux equivalent)
- Maintainer scripts (`scripts/*.sh`) ยอม POSIX ได้ — shode666 dev = Mac

---

# 📋 PART 3 — File Map

```
shode-house/
├── .claude-plugin/
│   ├── plugin.json              # v3.3.0
│   └── marketplace.json         # v3.3.0
├── CLAUDE.md                     # Repo invariants v3.3 + Bias Discipline + PEV Loop sections
├── README.md                     # v3.3 banner + PEV workflow diagram
├── CHANGELOG.md                  # [3.3.0] entry + supersedes note for v3.2.0
├── agents/                       # 19 agents — ทุกตัวมี ## 🎯 Bias Discipline section
│   ├── orchestrator.md          # Oliver — PEV loop (no sprint outer); Phase 7 REMOVED
│   ├── business-analyst.md      # Bella — anchoring resist
│   ├── solution-architect.md    # Sara — pattern-bias resist
│   ├── developer.md             # Dave — adversary-aware hand-off
│   ├── code-reviewer.md         # Chris — adversary stance + Chrome MCP mandatory
│   ├── qa-engineer.md           # Quinn — adversary stance + Chrome MCP mandatory
│   ├── devops-engineer.md       # Aaron — Phase 5 continuous per bd
│   ├── ux-ui-designer.md        # Uma — Phase 1b/3a + Bash tool
│   ├── product-manager.md       # Patrick — continuous OKR (no sprint retro)
│   ├── staff-engineer.md        # Stan — accept divergence default
│   ├── security-engineer.md     # Sentinel — hold position on "low risk"
│   ├── sre-engineer.md          # Reggie — alert root-cause not dismissal
│   └── 7 domain experts          # Felix/Iris/Sam/Tara/Elena/Brooke/Emma
├── commands/                     # 5 active + 2 deprecated alias
│   ├── consult.md               # ad-hoc consultation
│   ├── init.md                  # project scaffold (default interactive; --quick direct)
│   ├── design-system.md         # Phase 1a+1b spec pipeline (--stop, --estimate)
│   ├── implement.md             # Phase 2-4 PEV loop
│   ├── review.md                # ad-hoc code review
│   └── (sprint.md REMOVED v3.3; setup-project + spec-only deprecated since v3.1)
├── skills/                       # 18 shipped + 1 in-progress
│   ├── workflow/                # meeting, dev-gate, automate-test, diagnose
│   ├── ops/                     # incident, slo, secure
│   ├── ui/                      # ui-test, web-q
│   ├── style/                   # caveman
│   ├── discipline/              # 8 modules
│   │   ├── shode-house-discipline/  # Recite + Philosophy + No Man-Day rule
│   │   ├── shode-house-evidence/    # Project + UX + Domain Evidence
│   │   ├── shode-house-routing/     # RACI + T-shirt (internal only) + Conflict resolution
│   │   ├── shode-house-deliverable/ # DoD + Anti-Puppet + I Never Do
│   │   ├── shode-house-broadcast/   # Tag Prefix + Handoff Protocol
│   │   ├── shode-house-workflow/    # PEV loop (no sprint) + Lifecycle Hooks
│   │   ├── shode-house-drift/       # M1-M7 + Phase 7 REMOVED
│   │   └── review-checklist/        # Chris 7-dim + Quinn matrix + Adversary stance
│   ├── in-progress/             # NOT shipped (drafts / maintainer-only)
│   │   └── eval-harness/        # SKILL.md + 19 fixtures + run_eval.py (offline regression tool)
│   └── deprecated/              # NOT shipped (retiring)
├── scripts/                      # Maintainer .sh only
│   ├── lint.sh                  # 8 checks
│   ├── check-index.sh           # invariants
│   ├── build-plugin.sh
│   ├── list-skills.sh
│   ├── setup-precommit.sh
│   ├── publish.sh
│   └── publish-v3.1.0.sh        # legacy
├── docs/
│   ├── failure-modes/           # 001 currently shipped
│   ├── bd-quickstart.md         # bd install + alternatives (v3.3 add)
│   └── migration-v3.2-to-v3.3.md  # v3.2 → v3.3 migration (v3.3 add)
└── references/                   # lazy-load language guides (May 2025 stamp)
```

---

# 🛡️ PART 4 — Repo Invariants (enforced by `scripts/lint.sh`)

ดู `CLAUDE.md` for full list:
- **Bucket folders**: workflow/ops/ui/style/discipline = shipped; in-progress/deprecated = NOT shipped
- **SKILL.md size**: ≤ 300 บรรทัด (exceptions: meeting + dev-gate)
- **SKILL.md description**: 4-section `[WHAT] / [AUDIENCE] / [WHEN] / [TRIGGER]`
- **Plugin manifest** description ≤ 200 chars ASCII (Cowork validator strict)
- **Marketplace plugins[].description** ≤ 100 chars ASCII
- **3-flag rule** for commands; deprecated alias 1-2 release window แล้วลบ
- **Lint 8 checks must pass** ก่อน publish

---

# ⚠️ PART 5 — Risks + Known Limitations

1. **bd tool external** — referenced ทั่ว repo แต่ไม่ packaged. User without bd = ใช้ alternative (ดู `docs/bd-quickstart.md`)
2. **SESSION-STATE.md = manual Oliver discipline** — no auto-load hook (reverted in v3.3 for cross-platform safety)
3. **Bias discipline = paper rule** — pilot engagement จริงยังไม่ได้ verify ทุก trigger
4. **Eval harness in-progress** — STUB; ทำงานจริงต้อง Claude SDK wire (future major release)
5. **Claude in Chrome MCP dependency** — Chris/Quinn บังคับ verify visual; user ต้องติดตั้ง MCP extension (graceful error ถ้าไม่มี)

---

# ❌ PART 6 — Decisions Rejected (อย่า bring back)

- ❌ Sprint outer loop / `/sprint` command (human concept, ไม่เหมาะ agent)
- ❌ Evan evaluator agent shipped (over-engineer; eval ตัวเองแล้ว self-preference bias)
- ❌ Auto-load hooks (cross-platform risk; Windows no-Python = silent skip)
- ❌ M3 audit log + sprint_metrics.py heavy telemetry (over-engineer)
- ❌ Add agent ใหม่ (19 พอแล้ว; consolidation v4.0 ถ้าจะลด)
- ❌ Add command ใหม่นอก 3-flag rule
- ❌ Man-day estimate by default (agent ไม่ใช่ฝ่าย project management)

---

# 🚀 PART 7 — Quick Reference

## เริ่ม session ใหม่
```
อ่าน ~/development/shode-house/SHODE-HOUSE-MASTER.md
แล้วทำ [task]
```

## ทำงานกับ feature
```
/shode-house:design-system <feature>      # Phase 1a + 1b spec
"ลุยต่อ"                                   # Oliver M2 classify → auto /implement
# หรือ /shode-house:implement <bd-id> ตรง
```

## Ad-hoc
```
/shode-house:consult <คำถาม>              # quick triage
/shode-house:review <path|bd-id>          # standalone code review
```

## ก่อน release ใหม่
```bash
bash scripts/lint.sh           # 8 checks
bash scripts/build-plugin.sh   # .plugin zip
# drag-drop test Cowork before push
```

---

# 📚 PART 8 — Audit Sources

- Anthropic FS: https://github.com/anthropics/financial-services
- Affaan everything-claude-code: https://github.com/affaan-m/everything-claude-code
- 9arm-skills (skill-craft inspiration): https://github.com/thananon/9arm-skills
- dev-flow.md (user-provided, May 17)
- Real engagement feedback (May 30) — inspired v3.2.0 over-engineer revert → v3.3.0

---

*v1: May 8, 2026 — single-file master*
*Updated May 30, 2026 — v3.3.0 Simplification (drop sprint + Evan + man-day; embed bias + adversary + Chrome MCP)*
