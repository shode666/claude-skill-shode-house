# RUNBOOK — runtime baseline + A/B (WS8 / WS10)

## Current qualification protocol (post-3.16.2)

Use the published baseline and an explicitly identified candidate snapshot in
separate disposable fixtures. Never switch this dirty checkout or replace a user's
installed plugin for a benchmark. Use host-supported temporary loading only after
checking current host documentation and authority; retain actual loaded-source
provenance. Host configuration files alone do not qualify a host.

Keep task, fixture revision, model, reasoning settings, tool permissions and
acceptance identical. Record host/model versions, source hashes, elapsed time,
input/cached/output usage, attempted and successful deliveries, retries and each
worker's actual trace. Missing usage is unknown, not zero. Alternate baseline and
candidate runs to reduce order/cache effects. Choose repeats and tolerances before
running; do not select only successful or cheapest runs afterward.

Evaluate real implementation plus independent review, interrupted/resumed work and
uncertain external effects in a disposable environment. Never perform real payments,
deployments or remote tracker writes to manufacture qualification. Mocked operations
must be labelled; a policy answer or synthetic context estimate is not delivery.

Score critical invariants before performance: no removed roles, missed triggered
review, fabricated evidence, unauthorized effects or duplicate uncertain effects.
Compare token/time distributions only for matched workloads with quality outcomes
reported alongside them. A single pair establishes neither a distribution nor a
general saving. Test each claimed native host independently; unavailable hosts are
NOT QUALIFIED, not equivalent to Codex.

The 2026-09-15 standalone Codex policy pilot is recorded in
`docs/evidence/policy-pilot-2026-09-15-{baseline,candidate}.json`. It is not a full
delivery benchmark, and subsequent wording fixes need fresh evaluation.

## Historical v3.13 procedure (not current installation instructions)

The commands and version names below document the original campaign only. Do not
run its checkout/install/uninstall steps against a user's active environment. Its
Claude transcript scorer does not establish compatibility with other hosts.

สิ่งเดียวที่ปลดล็อก promotion ของ v3.13 · ต้องรันบนเครื่องที่ใช้ Claude Code จริง
(sandbox ของ session ทำแทนไม่ได้ — ไม่มี runtime, ไม่มี ~/.claude)

## เตรียม 1 ครั้ง

```bash
# project ทดสอบที่จะใช้ทุกรอบ (ต้องเป็นตัวเดิมตลอด A/B ไม่งั้นเทียบไม่ได้)
cd <test-project>
claude plugin install shode-house@<path หรือ marketplace>
```

fix ให้เหมือนกันทุกรอบ: **model เดียว · reasoning setting เดียว · project เดียว · session ใหม่ทุกรอบ**

## A — baseline บน v3.12.1  (11 scenario × 5 รอบ = 55 run)

`full-fanout` ไม่ต้องรัน — ใช้ `scripts/context-budget.py` เป็นตัวแทน (synthetic)

```bash
git checkout v3.12.1 && claude plugin install .      # ให้ CLI ใช้ 3.12.1
```

ต่อ 1 run:

```bash
# 1. เปิด session ใหม่ วาง prompt จาก eval/prompts/<scenario>.md แบบ verbatim
# 2. รันจนจบ แล้วติ๊ก behavior assertion ในไฟล์นั้น (accuracy มาก่อน token)
# 3. เก็บ usage
scripts/usage-from-transcript.py --list        # หา transcript ล่าสุด
scripts/usage-from-transcript.py <transcript.jsonl> \
    --scenario <scenario-id> --run-dir eval/baseline/3.12.1 \
    --plugin-version 3.12.1 --model <model-id> --command <command>
```

🔴 **รอบแรกให้เปิด record ที่ได้ดูด้วยตา** แล้วเทียบกับ `/cost` ของ session นั้น
ถ้าเลขไม่ตรง = schema ของ transcript เปลี่ยน ต้องแก้ `usage-from-transcript.py` ก่อนเก็บที่เหลือ

```bash
scripts/usage-report.py eval/baseline/3.12.1      # สรุป + จับ repeated load
```

## B — candidate บน 3.13

```bash
git checkout feat/v3.13-ws7-ws9-ws10 && claude plugin install .
# รัน 11 scenario × 5 รอบ ด้วย prompt ชุดเดิม --run-dir outputs/token-usage/3.13-rc1
scripts/usage-report.py --compare eval/baseline/3.12.1 outputs/token-usage/3.13-rc1
```

## Promotion criteria (WS8 — ห้ามผ่อน)

- [ ] critical invariant pass **100%** — safety R0/R1/R2 · evidence/no-magic · handoff completeness
      · scope drift · spec axis · domain citation · UX evidence · AskUserQuestion relay · close-on-done
      · lazy-load omission
- [ ] general accuracy ลดไม่เกิน **2%** (นับจาก behavior assertion ที่ติ๊กไว้)
- [ ] input context ลดตาม `target_total_token_reduction` ของแต่ละ scenario
- [ ] **ไม่มี fixture ที่ผ่านเพราะ skip action** — ผ่านเพราะไม่ได้ทำ ไม่นับผ่าน
- [ ] regression gate ของ `usage-report.py --compare`: median +3% / p90 +5% ไม่เกิน

ข้อไหน fail = ไม่ promote · แก้แล้วรันซ้ำทั้งชุด ไม่ใช่เฉพาะ scenario ที่ fail

## ต้นทุนคร่าว ๆ

55 run สำหรับ A + 55 run สำหรับ B · scenario ที่ fan-out (implement-*, phase3b-*) กิน token มากสุด
ทำทีละกลุ่มได้ แต่ **ห้ามสลับ model/project กลางทาง**

## 🔴 E2E golden (Phase B) — runner ต้องเป็น session **local**

scorer อ่าน `~/.claude/projects/<proj>/<session-id>.jsonl` + `<session-id>/subagents/` — **Cowork cloud session ไม่เขียนไฟล์นี้ลงเครื่อง** (พิสูจน์ 2026-09-08: GS1 รันใน Cowork cloud → ไม่มี transcript, score ได้แค่ bd end_state)
→ รันด้วย Claude Code CLI (`npm i -g @anthropic-ai/claude-code`) หรือ Cowork local-mode เท่านั้น

```bash
cd <fixture project> && bd create "GSn: ..." -t task        # จด id
claude                                                        # session ใหม่ → /shode-house:review ... --bd <id>
# หลังจบ:
cd ~/workspace/shode-house
S=$(ls -t ~/.claude/projects/-Users-<you>-workspace-<fixture>/*.jsonl | head -1)
python3 scripts/eval-scorer.py "$S" --scenario GSn-... --project <fixture project> --bd-id <id> --out eval/baseline/e2e-golden/run-N
```
exit 0 PASS · 1 FAIL · 2 UNSCORABLE (input หาย — ไม่ใช่ PASS)

🔴 **หลังแก้ plugin ทุกครั้ง (version เดิม)**: `claude plugin uninstall shode-house@shode-house && claude plugin install shode-house@shode-house` — `install` เฉย ๆ บอก already installed และใช้ cache เก่า (`~/.claude/plugins/cache/shode-house/shode-house/<ver>/`); ตรวจด้วย `grep -l 'REVIEW DISPATCH CARD' ~/.claude/plugins/cache/shode-house/shode-house/*/commands/review.md`
