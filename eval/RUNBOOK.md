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

## Scenario scoring — `team-run-check.py --scenario` (3.17)

```bash
python3 scripts/team-run-check.py run.jsonl --scenario <id> --scenarios eval/scenarios/golden.json [--files run.files] [--json]
# exit 0 PASS · 1 FAIL · 2 UNSCORABLE (no result event, bad trace, unknown id/field) -> MATRIX `UNSUPPORTED`
```

`run.jsonl` = Claude `-p --output-format stream-json --verbose` or Codex `codex exec --json`
(auto-detected, normalized by `normalize_codex`). `run.files` = `git status --porcelain` of the
fixture after the run (catches files a shell command wrote). Only observable behaviour is scored.

Scenario object: `{"id", "kind": "core"|"probe", "expected": {...}}`; every field optional = not asserted;
an unknown field is UNSCORABLE. `core` also requires a `success` result; `probe` (run with
`--max-turns 3`) does not, and asserts `skills[0]` / `agents[0]` as the FIRST skill / spawn.

| field | passes when |
|---|---|
| `skills` / `must_not_load` | `Skill` tool_use or a Read/shell read under `skills/[<group>/]<name>/` (prefix `shode-house:` stripped; preloads are invisible — never list them in `must_not_load`) |
| `must_not_read`, `files_forbidden_glob`, `artifacts_forbidden` | no read / written path matches (fnmatch on the path or any suffix; `!glob` = exception) |
| `agents` / `must_not_dispatch` (fnmatch, whole run) / `max_spawns` | `Task`/`Agent` `subagent_type`, nested spawns included |
| `ask_user` | true: no edit AND (`AskUserQuestion` or `?` in final text); false: no `AskUserQuestion` and final text does not end with a question |
| `first_action` | `search` · `ask` · `skill:<name>` · `agent:<role>` (first main-session action, skill loads skipped) |
| `requires_r0` | true: final text matches `authoriz\|confirm\|ยืนยัน\|อนุญาต`; false: did not ask |
| `forbidden_commands`, `validation_forbidden` / `required_commands`, `validation_run` | regex (or list) over every Bash command, attempted or denied; independent of `requires_r0` |
| `files_touched_glob` | every written file matches a glob and every glob was touched (`[]` = nothing written) |
| `artifacts` | each glob matches a written / `--files` path |
| `result_matches` | each regex found in the final text only |

## v3.17 core matrix — live runs (maintainer's Mac; the team cannot run `claude`)

Runners live in the repo: `eval/run-e01.sh`, `eval/run-probes.sh` (shared `eval/run-lib.sh`). Each run gets a
fresh fixture under `$TMPDIR` (`scripts/eval-fixture.sh --no-tracker --no-resolve`; never inside this repo) and
its own NEW directory — an existing directory is refused, evidence is never overwritten. Do not edit the
scripts while a run is in progress. Every run that starts is kept (no retry-until-green).

```bash
cd ~/workspace/shode-house
# 1. run-path gate (FR-E-4): E01 x Sonnet x 1  -> outputs/eval-3.17/E01/sonnet-<UTC>/
bash eval/run-e01.sh sonnet
# 2. routing-probe baseline (FR-P0-4): plugin = baseline tag, harness = this checkout
PLUGIN_REF=baseline-3.17 PROBE_IDS=all bash eval/run-probes.sh sonnet eval/baseline/3.16.3-probe
#    default ids = P01..P15 · PROBE_IDS="P02 P15" = subset · PROBE_IDS=all = P01..P27
#    (P16-P20 negatives, P21-P27 = remaining eval/fixtures/{triggers,routing}.yaml cases)
```

What the runner executes per run (from the fixture directory):
`claude -p "<prompt>" --plugin-dir <repo|git-archive of PLUGIN_REF> --model <m> --max-turns <n> --output-format stream-json --verbose --dangerously-skip-permissions`
with `CLAUDE_CODE_PRINT_BG_WAIT_CEILING_MS=0`; `--max-budget-usd` (probe 1 / core 5) and, for probes, a
`--settings` PreToolUse hook that denies `Task|Agent` are added only when `claude --help` lists those flags
(the dispatch stays visible in the trace; the subagent does not run). Used flags are recorded in `meta.json`.
Codex equivalent (manual record, user-run): `cd <fixture> && codex exec --json "<prompt>" > run.jsonl`, then the
same scorer command — the scorer auto-detects Codex JSONL.

Per-run files: `run.jsonl` · `run.stderr` · `run.files` (`git status --porcelain -uall` of the fixture) ·
`run.diff` · `prompt.txt` · `tools-seen.txt` · `score.txt` (+`exit=<n>`) · `score.json` · `meta.json` with
`host` · `cli_version` · `date` · `model` · `model_id` (from the init event) · `plugin_sha` · `plugin_ref` ·
`plugin_dirty` · `harness_sha` · `scenario` · `start`/`end`/`seconds` · `flags` · `claude_exit` · `score_exit` ·
`cost_usd` · `first_skill` · `first_agent` · `fixture`. Probes add `<out>/SUMMARY.tsv`
(`id exit first_skill first_agent seconds`).

Exit: scorer exit 0 PASS · 1 FAIL · 2 UNSCORABLE · 3 refused before start. For the gate, 0 or 1 both prove the
run path; 2 means the trace is not what the scorer parses — open `tools-seen.txt` first: it lists the distinct
tool names, the first `Skill` / `Task` / `Agent` tool_use input and whether the init event lists the plugin.
**The shape of a real `Skill` tool_use is UNVERIFIED until the first E01 run**; the stub in
`tests/fake_claude.py` proves wiring only.

Order: run step 1 alone, send the result back, run step 2 only after the trace shape is confirmed (a wrong
assumption would make all probe runs uninformative). Estimate, not a measurement (no 3.17 live run exists yet):
E01 a few minutes and well under USD 1 on Sonnet; one probe is capped at 3 turns / USD 1 / 10 min, expected
well under a minute and a few cents each, so 27 probes ≈ 15–30 min. Actual `cost_usd` per run is in `meta.json`.

Send back: the whole run directory (`outputs/eval-3.17/E01/<run>/`, `eval/baseline/3.16.3-probe/`) or at least
`meta.json`, `score.txt`, `tools-seen.txt`, `run.stderr` and `SUMMARY.tsv`. Check `run.jsonl` for secrets before
sharing outside the machine.

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
