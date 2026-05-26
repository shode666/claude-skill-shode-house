---
name: incident
description: |
  [WHAT] Production incident response + runbook + on-call rotation + blameless postmortem + 5-why + action items.
  [AUDIENCE] Reggie (lead IC) + Oliver (escalation routing) + Aaron (infra mitigation) + Sentinel (security incident).
  [WHEN] หลัง alert ดัง / customer report; ก่อน mitigation; ห้ามใช้ถ้าไม่ใช่ production outage (ใช้ diagnose แทน).
  [TRIGGER] /shode-house:incident, "พังใน prod", "service down", "alert ดัง", "P0", "P1", "outage", "rollback", "war room", "incident commander", "postmortem".
---

# Incident (response + runbook + postmortem)

> **Owner**: Reggie (lead) + Oliver (escalation routing) + Aaron (infra mitigation) + Sentinel (if security)

## When NOT to use

- **Bug ที่ไม่ใช่ production outage** — ใช้ `diagnose` skill (structured debugging) แทน
- **Customer support ticket** (single user, no SLO breach) — Patrick handle เป็น product feedback
- **Planned maintenance / scheduled downtime** — ไม่ใช่ incident; ใช้ change management runbook
- **Internal dev environment crash** — ไม่นับ incident (severity = P3 informal)
- **Security suspect ที่ยังไม่ confirmed** — escalate Sentinel ก่อน; ห้าม open war room โดยไม่มี evidence (false-positive incident เปลือง budget)

## Required inputs — refuse without

ก่อนเปิด war room / claim IC role, confirm:

- [ ] **Alert source identified** (Prometheus rule name / health check / customer report — ระบุ origin)
- [ ] **Severity assigned** (P0/P1/P2/P3 ตาม matrix; **ห้ามเปิด war room ถ้า P3**)
- [ ] **Blast radius estimate** (กี่ user / กี่ region / กี่ % traffic — รู้เพื่อ comms ถูก)
- [ ] **Rollback option known** (มี last-known-good version + how to revert; ถ้าไม่มี — ขอ Aaron ก่อน)
- [ ] **On-call หรือ author available** (ถ้าไม่มี → ต้อง escalate ทันที ไม่รอ war room)

ถ้าขาด → list สิ่งที่ขาด ส่งกลับ caller ก่อนเปิด IC channel

## หลักการ

1. **Mitigate ก่อน fix** — rollback / scale / circuit break / feature-flag-off
2. **Blameless** — fault in process, not people
3. **5-why ขั้นต่ำ** — first principle root cause
4. **Action items มี owner + due date + bd issue**

## Severity matrix

| Sev | Definition | Response time (ack) | War room | Postmortem |
|-----|-----------|---------------------|----------|------------|
| **P0** | Full outage / data loss / security breach | < 5 min | Required | < 3 business days |
| **P1** | Critical degraded / SLO burn 14x | < 15 min | Required | < 5 business days |
| **P2** | Partial impact / workaround มี | < 1 hr | Optional | < 7 business days |
| **P3** | Minor / no user impact | next business day | No | Optional |

## Incident response flow (Reggie IC = Incident Commander)

```
ALERT (burn rate / health check / customer report)
   ↓
ACK (Reggie or on-call < 5 min) — claim IC role
   ↓
TRIAGE 15 min — assemble war room:
   - IC: Reggie
   - Infra: Aaron
   - Code: Dave (author of recent change)
   - Sec (if applicable): Sentinel
   - Comms: Oliver
   ↓
MITIGATE first (rollback / scale / flag off)
   ↓
COMMUNICATE every 30 min in war-room channel:
   "Update <HH:MM> — actions taken / current status / next action / ETA"
   ↓
RESOLVE when SLO back to normal (not when fix shipped — fix may come later)
   ↓
POSTMORTEM scheduled within 5 days
```

## Runbook template

ทุก critical alert ต้องมี runbook (Reggie block deploy ถ้าขาด)

```markdown
# Runbook: <alert name>
**Service**: payment-api  **Alert**: high error rate  **Severity**: P1

## Symptom
- error rate > 1% in last 5 min
- typical observable: <description>

## Diagnosis (in order)
1. Check Grafana dashboard: <link> — what changed?
2. Recent deploy? `kubectl rollout history deployment/payment-api`
3. DB latency? Check `pg_stat_activity` — slow query?
4. Upstream dependency? Check trace ID sample
5. Network/CDN? Check Cloudflare status

## Mitigation
**First**:
- Rollback last deploy: `kubectl rollout undo deployment/payment-api`
- Or: feature flag off: `LD_TOGGLE_OFF=new_refund_flow`

**If first fails**:
- Scale replicas: `kubectl scale --replicas=10 deployment/payment-api`
- Failover read-replica: <link to runbook>

## Escalation
- P0/P1 not mitigated in 30 min → wake Sara + Aaron
- Security suspicion → page Sentinel
- DB-level → page DBA on-call

## Test (chaos drill)
- Last verified during incident: <YYYY-MM-DD>
- Manually triggered drill: <YYYY-MM-DD>
```

## Postmortem template (blameless)

```markdown
# Postmortem: <title> (<YYYY-MM-DD>)
**Severity**: P0/P1  **Duration**: hh:mm  **Impact**: <users / revenue>
**IC**: Reggie  **Authors**: Reggie + Dave

## Summary
1 paragraph: what happened, customer impact, root cause, mitigation

## Timeline (UTC)
| Time | Event |
|------|-------|
| HH:MM | First alert (burn rate 14x, P1 page) |
| HH:MM | Reggie ack, war room opened |
| HH:MM | Hypothesis: DB connection pool exhaustion |
| HH:MM | Mitigation: scale pool 50 → 200 |
| HH:MM | SLO restored |

## Root cause (5-why)
1. Why did API error rate spike? → DB connection pool exhausted
2. Why exhausted? → Burst traffic 3x normal
3. Why burst? → Marketing campaign launched without warm-up
4. Why no warning? → No load forecast pre-launch
5. Why no forecast? → No process for marketing → SRE handoff

**Root cause**: Process gap between Marketing campaign launch and SRE capacity planning

## What went well
- Burn rate alert fired correctly (1h window, 14x)
- Reggie ack in 4 min (target < 5)
- Rollback was practiced; quick mitigation

## What went poorly
- No pre-launch load forecast
- DB pool size hardcoded (not Terraform-managed)
- War room channel had no Patrick (PM should know early)

## Action items
| # | Action | Owner | Due | bd issue | Severity |
|---|--------|-------|-----|----------|----------|
| 1 | Add Marketing → SRE handoff process | Patrick | 2026-06-15 | bd-101 | HIGH |
| 2 | Move DB pool config to Terraform | Aaron | 2026-06-08 | bd-102 | HIGH |
| 3 | Add Patrick to P0/P1 war-room paging | Reggie | 2026-06-01 | bd-103 | MED |
| 4 | Document campaign launch playbook | Bella | 2026-06-30 | bd-104 | MED |

## Lessons (broadcast to team)
- ทุก marketing campaign > 2x normal traffic → SRE load forecast บังคับ
- Hardcoded resource config = trap; Terraform ทุกอย่าง
```

## On-call rotation

```markdown
# On-call rotation: payment-team
**Rotation**: weekly, Mon 9:00 AM TH handoff
**Tier 1** (primary): rotation list
**Tier 2** (secondary): rotation list (covers primary unavailable)
**Tier 3** (escalation): Sara + Aaron + Reggie always

## Handoff template (Mon 9:00 AM in standup)
- Open issues: <list bd issues + status>
- Recent incidents (last week): <count + severity>
- Known fragile area: <list>
- Maintenance scheduled this week: <list>
- Burn rate trend: <link Grafana>
```

## 5-Why pitfalls (Reggie enforce blameless)

❌ Wrong:
- "Dave forgot to test" (blame individual)
- "Aaron's config was wrong" (blame)
- "Should have known" (hindsight bias)

✅ Right:
- "Test process didn't catch X" (process)
- "Config schema allowed invalid Y" (system gap)
- "Documentation gap on Z" (system)

## Evidence

```
✅ "[Postmortem: postmortems/2026-05-22-payment.md] MTTR=42min, 4 action items (bd-101..104)"
✅ "[Runbook: runbooks/payment-high-error.md] last verified 2026-05-22 incident"
✅ "[On-call: oncall-schedule.md] this week: <name>, handoff Mon 9:00"
✅ "[War room: thread-link] 12 updates, IC Reggie, 5 participants"
❌ "incident resolved" (no MTTR, no root cause, no action items)
```

## ห้าม

- ห้าม close incident โดยไม่มี postmortem schedule
- ห้าม postmortem ที่ระบุชื่อ blame
- ห้าม "the fix is to be more careful" — เปลี่ยน process/tool/automation
- ห้าม action item ไม่มี owner + due + bd issue
- ห้าม mitigate กับ fix รวบเป็นขั้นเดียว — mitigate first, fix later
- ห้าม alert ที่ไม่มี runbook (ที่ดังจริง = bd-issue urgent + block deploy)

## Skill composition (where to go next)

| Situation | Next skill | Reason |
|---|---|---|
| Postmortem identifies SLO breach pattern | → `slo` | Recalibrate SLI/SLO/error budget; ปรับ burn-rate alert (incident ไม่ทำ measurement design) |
| Root cause = bug ที่ต้อง fix | → `diagnose` → `dev-gate` | Structured RCA + TDD-driven fix (incident จบที่ mitigation) |
| Root cause = security breach | → `secure` | Sentinel STRIDE + abuse case + threat model update |
| Root cause = test gap ทำให้หลุด CI | → `automate-test` | Pyramid + regression coverage + CI gate (close the hole) |
| Action item ต้อง deploy hot-fix | → `dev-gate` (followed by hot-fix release) | TDD applies even to hot-fix (no exception)
