# shode-house Eval Fixtures (v3.2)

Bias-aware regression test fixtures — 1 starter fixture per agent, organized by `<agent>/<NN>-<topic>.json`. Methodology + thresholds defined in `skills/discipline/eval-harness/SKILL.md`.

## Coverage (19 agents = 19 starter fixtures)

| Agent | Primary bias tested | File |
|---|---|---|
| Oliver | Sycophancy | `oliver/01-user-pushback-on-correct-routing.json` |
| Bella | Anchoring on AC | `bella/01-user-leads-ac-phrasing.json` |
| Sara | Pattern-bias (microservices) | `sara/01-startup-monolith-vs-microservices.json` |
| Dave | Sycophancy (just try) | `dave/01-user-pushes-skip-test.json` |
| Chris | Verdict skew (PASS-bias) | `chris/01-marginal-issue-as-pass.json` |
| Quinn | Verdict skew | `quinn/01-incomplete-coverage-marked-pass.json` |
| Aaron | Pattern-bias (AWS) | `aaron/01-cloud-vendor-anchor.json` |
| Uma | Pattern-bias (Material vs HIG) | `uma/01-design-system-anchor.json` |
| Patrick | Anchoring (sunk-cost) | `patrick/01-sunk-cost-on-failing-feature.json` |
| Stan | Convergence bias | `stan/01-force-converge-divergent-stacks.json` |
| Sentinel | Sycophancy ("low risk") | `sentinel/01-user-claims-low-risk.json` |
| Reggie | Alert dismissal | `reggie/01-repeated-alert-normalize.json` |
| Felix | Pattern-bias (Stripe) | `felix/01-stripe-anchor-thailand-context.json` |
| Iris | Sycophancy on OIC interpretation | `iris/01-user-claims-regulation-interp.json` |
| Sam | Std-vs-custom bias | `sam/01-z-modification-default.json` |
| Tara | Vendor bias (exchange) | `tara/01-exchange-vendor-anchor.json` |
| Elena | Costing method anchor | `elena/01-fifo-vs-weighted-avg-anchor.json` |
| Brooke | Channel mono-culture (OTA) | `brooke/01-ota-vs-direct-anchor.json` |
| Emma | Platform bias (Shopify) | `emma/01-shopify-vs-custom-anchor.json` |

## Fixture schema

ดู `skills/discipline/eval-harness/SKILL.md` § Fixture Schema. ทุก fixture ต้องมี:
- `id`, `agent`, `bias_type`
- `input` (user_prompt + context)
- `expected_behavior` (must_consider_alternative / must_not_blindly_accept / expected_keywords)
- `run_config` (n_runs, shuffle_order, judge_model, blind_judge)
- `metrics` (thresholds per bias type)
- `expert_validated_by` = "PENDING" จนกว่า domain SME sign

## Run (agent-orchestrated — no script, v3.6)

ไม่มี `run_eval.py` แล้ว. Maintainer (offline) รันผ่าน orchestrator + Task tool:
- โหลด fixture → `Task` spawn subject subagent (N runs) → `Task` spawn judge subagent (blind, model ≠ subject) → orchestrator aggregate + เขียน `outputs/EVAL-<agent>-<date>.md`
- ดูขั้นตอนเต็มใน `../SKILL.md` § Run Pipeline
- Schema validation = orchestrator ตรวจด้วยตา/Read ตาม § Fixture Schema (ไม่มี `--dry-run`)

## Adding new fixtures

1. ใส่ใต้ `<agent>/NN-<topic>.json` (NN = sequential 2-digit)
2. ตาม schema เคร่งครัด (orchestrator ตรวจตาม SKILL.md § Fixture Schema)
3. `expert_validated_by`: domain SME (CPA / actuary / SAP consultant / OWASP / etc.) sign ก่อน promote
4. Update นี้ table (README) + skill `eval-harness/SKILL.md` § Per-Agent Bias Priority ถ้าเพิ่ม bias type ใหม่

## Promote criteria (in-progress → production eval baseline)

- ≥ 3 fixtures ต่อ agent (currently 1 starter ต่อ agent)
- ทุก fixture มี expert sign-off (currently "PENDING")
- Judge calibration accuracy ≥ 0.85 บน golden labels (per Evan calibration step)
- 2 baseline runs separated by ≥ 1 week (consistency check)
