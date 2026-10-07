---
name: shode-house-workflow
description: Coordinate multi-phase delivery with phase gates, recorded approvals, run recovery and drift detection, governing how work proceeds, not who owns it.
---

# shode-house — Workflow Discipline

Starting or resuming an engagement, or before the first delegation: read `harness.md` (next to this file) to confirm the source of truth, host tools, owners, checkpoint and UNKNOWN reconciliation.

> The router owns workflow. The Phase Contract is mandatory; gates make the pipeline auditable.

---
## 🧵 Task Tracking — tracker = single source of truth ของ status/dep

Use the source of truth the user confirmed (`harness.md`); with none, Markdown can hold every concern. Commands are the confirmed tracker's own; Beads example → `harness.md` § Beads example.
- Markdown deliverables (BRD/ADR/SPEC/REVIEW) live where the project chose; status/dependencies live in one canonical record, which may be Markdown.
- abstraction: `tracker.create(title,priority,type,blockedBy?)` · `.ready()` · `.claim(id)` · `.note(id,text)` · `.close(id)` + read-back (🔴 M8 close-on-done) · `.link(from,to,type)` — other trackers → `smart-coop.md` § Tracker options

## 🎚️ Engagement Mode (the router picks before starting)

- **AFK** — proceed through applicable phases within recorded scope/authority; unattended mode does not waive deployment, external-write or business-policy approval. Missing authority becomes a checkpointed blocker.
- **Interactive** — the human approves every hand-off and phase exit; R2/R1 inform. For new, sensitive or audited work.
- **Hybrid** (recommended default) — AFK up to pre-deploy, Interactive from deploy on.

Every mode: **R0 (irreversible) always asks first.**

## 🚦 Phase orchestration (🔴 the router enforces)

- Phase 1a business-analyst and solution-architect work in independent contexts; parallel when the host supports it and nothing depends, otherwise sequential. Phase 1b ux-ui-designer/domain read the merged 1a spec before designing or validating.
- UI changed → never skip the Phase 3a ux-ui-designer POST gate. Pure backend → record not-applicable with diff evidence, then 3b.
- Phase 3b reviewers check separate scopes with independent verdicts; parallel when possible, or sequential in separate contexts, never copying a verdict.
- 🔴 ห้าม skip Phase 4 Triage routing. Review fail → loop to the phase the finding belongs to (code→2, UI→1b, spec→1a); never "half pass" into Deploy.
- Never close Phase 3 (3a/3b) before the review report is in the confirmed evidence home; the task record keeps a link, not a copy. Use the REVIEW Report Format.

## 🛡️ Phase 1c — Threat Model (🔴 canonical trigger list — single source)
- **Owner**: ✅ security-engineer (lead) + solution-architect (architecture context)
- **Trigger**: feature touching auth / session / PII / money / external integration / webhook / file upload / AI agent
- **Output**: STRIDE + abuse case + security AC injected into Phase 1a
- **Gate**: `pre-implement` — may block Phase 2 until it passes
- **Note**: may run parallel with 1b when scopes are independent
- Fast path vs full-workflow trigger → `ask` § Fast path or full workflow (single owner); fast path never skips this trigger.
- 🔴 **No waiver**: a user's or agent's "low risk" claim does not waive Phase 1c when a trigger fired. ห้าม dispatch Phase 2 ก่อน Phase 1c gate ผ่าน

## ⏸️ Approval Gates

Single table for every phase gate and R0 action; the router checks each gate before the hand-off (examples → `smart-coop.md` § Approval Gates).

| Gate | Before | Check |
|---|---|---|
| Pre-spec-expand | 1a → 1b | business-analyst + solution-architect sign-off (task notes posted); light cross-read complete; no FR-ADR conflict unresolved |
| Pre-implement-ui | 1b → 2 (frontend) | Applicable approved ux-ui-designer design + tokens/state/a11y criteria; reuse existing artifacts, Figma optional |
| Pre-ui-check | 2 → 3a | lint clean + unit green + smoke pass + Scope Contract closed |
| Pre-code-review | 3a → 3b | UI changed: ux-ui-designer POST PASS (visual/a11y/own AC); backend-only: explicit not-applicable with diff evidence |
| Pre-merge | merge to main | code-reviewer approve + required project checks; qa-engineer and other axes pass when selected by harness tier/triggers |
| Pre-merge-ui | merge UI change | Adopted UI checks pass + visual evidence approved + applicable accessibility criteria verified |
| Pre-loop-exit | 4 Triage → 5 Deploy | Applicable review axes complete, no unresolved Critical/High, iteration policy met; canonical review/evidence saved and task status verified. Deployment remains separately authorized |
| Pre-deploy-staging | staging deploy | Build + image scan pass |
| Pre-deploy-uat | uat deploy | Staging E2E pass + QA sign-off |
| Pre-deploy-prod | prod deploy | UAT business sign-off + change ticket + rollback plan; multi-sig devops-engineer + sre-engineer + security-engineer (+ product-manager for R0) |
| Pre-data-migration | run migration prod | Backup verified + expand-contract + dry-run |
| Pre-destructive | DROP/DELETE/rm -rf prod | User confirms this exact action + impact + rollback |

---

## 🔒 Run Durability (3 rules that survive a dead session)

> Sessions are not durable. Use the confirmed project record per `harness.md`, not a second required JSON/SESSION-STATE store. Project runtime engineering is separate authorized work, not a plugin prerequisite.

**1. Run stamp — record at task pick (without it nothing reproduces)**: task-record note `run: plugin=v<X.Y.Z> model=<agent:model,...> started=<ISO8601> branch=<branch>`

**2. Approval durability — approve ผูกกับสิ่งที่เห็น ไม่ใช่ผูกกับเวลา (🔴)**
- Record in the task record: `approved: gate=<gate> by=<who> at=<ISO8601> artifact=<path> sha=<git hash-object path>`
- artifact เปลี่ยนหลัง approve (sha ไม่ตรง) → **approval เป็นโมฆะ ต้องขอใหม่** ห้ามใช้ของเดิมต่อ
- ก่อนผ่าน gate ใด ๆ: re-hash artifact แล้วเทียบกับ sha ที่บันทึกไว้
- approval ที่อยู่แค่ในบทสนทนา = ไม่นับ (session ตาย = หลักฐานหาย)

**3. Resume protocol — session dies mid-pipeline**
```
1. Read the current canonical checkpoint: run stamp, phase, owners, outstanding gates.
2. Verify referenced artifacts/revisions; records without artifacts do not prove completion.
3. Reuse passed evidence only for matching scope/content/environment; recheck changed dependencies.
4. Reconcile UNKNOWN external operations from intent, stable key and authoritative receipts.
5. Never repeat an uncertain effect merely because the user says yes; unresolved outcome remains blocked per harness.md.
```

**Pointer**: DoD checklist = `shode-house-deliverable/definition-of-done.md` § Definition of Done (single source) — the router enforces it before closing a task: every DoD item needs an evidence path.

## 🔁 Workflow Discipline (Archon-inspired)

### Phase Contract — 🔴 v3.3 PEV Loop per bd (router enforce)

> Task-complete, not time-bound; no man-day negotiation. Deploy only when ready and authorized, not batched by sprint.

```
PICK bd claim → PLAN 0 Discover* / 1a business-analyst∥solution-architect / 1b ux-ui-designer*+domain* / 1c security-engineer*
  → EXECUTE 2 developer → VERIFY 3a ux-ui-designer* → 3b selected review axes → TRIAGE 4 router
  → DEPLOY 5 devops-engineer (continuous per bd) → OPERATE 6 sre-engineer          (* = conditional)

Triage routing: code/perf/security→2 · UI/design→1b · spec/AC/regulation→1a
Clean + closure authority → tracker close + read-back (M8); unresolved at third review/fix iteration → STOP, checkpoint and escalate
```

## 🛡️ Workflow Drift Defense (🔴 M2-M8 — M1 อยู่ใน `shode-house-discipline`)

### M2 — Follow-up Classifier (the router triages every user message)

```
User message → router classify (one line):
  "retry / not working" → inspect evidence → route affected owner/phase, track iteration; no blind retry
  "change X" → assess acceptance delta → business-analyst/solution-architect where affected, not full replay
  "why Y" → quest → answer, no phase change
  "OK / approve" → approve → closure gate check
  "add Z" → new → create child task
  "done yet?" → status → read task record, no action
```

ห้าม developer/code-reviewer/qa-engineer proceed ก่อน router classify

### M4 — User feedback invalidates the affected claim

```
Inspect feedback against acceptance and evidence:
  defect → record finding, reopen affected criterion/phase, increment iteration
  scope change → record revised acceptance and route its owners before editing
  question/status → answer from evidence without inventing a failure or new scope
  unresolved finding → hold closure; no automatic PASS after a worker's claim
```

ห้าม developer "OK เพิ่มให้ครับ" → fix ตรง ๆ โดยไม่ผ่าน iter counter

### M5 — Spec change = recorded acceptance revision

```
User: "make amount a decimal"
  ❌ WRONG: developer fixes the code directly
  ✅ RIGHT:
     router ▸ business-analyst : spec change request
     business-analyst → revise canonical acceptance record, preserve prior revision/history
     business-analyst ∥ solution-architect : Phase 1a redo (delta only — light)
     Gate: pre-spec-expand
     Revalidate affected phases/dependencies only; preserve unchanged approvals/evidence
```

### M7 — Direct-to-agent block

ทุก agent ที่ไม่ใช่ router ห้าม accept direct-from-user ใน active engagement — ส่งกลับ router

M3: Worker "done"/FIXED = candidate; "ready merge" = router only, after applicable independent reviews + triggered experts + current evidence + merge authority (detail → drift.md M3)

M1 → `shode-house-discipline` § M1 — Ingress Guard; เมื่อ drift เกิดจริง / จะ claim done / จะปิด task → โหลด `drift.md`: M3 Anti-Puppet "Done" table · M6 state pin · M8 Close-on-Done procedure · phase notes 0/6/7

---

## 🤝 Smart Coop Pattern — parallel where independent, sequential gate where dependent

🔴 **Before running a real pipeline, load `smart-coop.md`**: pattern per phase · blocked anti-patterns · `state.json` schema + resume · lifecycle conditions per phase · gate examples · Phase 0 scope-clarify flow · worktree isolation · prompt template. Never orchestrate from memory (NO MAGIC).

## 📚 Reference Files (lazy-load; `*.md` = next to this SKILL.md)

| File | Load when |
|---|---|
| `wayfinding.md` | work larger than one session **with no visible path** — Map + decision ticket before Phase 0 |
| `references/runbooks/router-engagement.md` | router: engagement plan template · Phase 0 discovery / 1c threat model / 6 operate · multi-sig pre-deploy gate |
| `references/runbooks/router-clarify-estimate.md` | router: question format · frontier procedure · estimate exceptions |
| `shode-house:shode-house-discipline` → `handoff.md` · `reporting.md` | router: handoff schema · `▸` broadcast · report and risk templates |
| `shode-house:shode-house-routing` → `orchestration.md` · `ownership.md` | router: orchestration detail · ownership tables |
| `shode-house:drain` → `execution.md` | router: batch-drain execution (isolated workers, serial merge, evidenced closure) |
| `references/patterns/durable-agent-runtime.md` | devops-engineer/solution-architect generate a runner that needs retry/checkpoint/journal |
