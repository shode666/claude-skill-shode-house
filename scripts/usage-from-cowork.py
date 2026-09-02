#!/usr/bin/env python3
"""ดึง usage record จาก transcript ของ Cowork session (WS10 collector — desktop/Cowork).

ต่างจาก usage-from-transcript.py (Claude Code CLI) ตรงที่ Cowork เขียนไฟล์แยกต่อ subagent:
  ~/.claude/projects/<slug>/<session>/subagents/agent-<id>.jsonl  + agent-<id>.meta.json

🔴 วัดได้เฉพาะ subagent -- main session ของ Cowork ปนเปื้อนด้วยบทสนทนาก่อนหน้า
   subagent เกิดใน context ว่างทุกตัว จึงเป็นตัวเดียวที่เทียบ A/B ได้

  scripts/usage-from-cowork.py --since <n>   # เอา n subagent ล่าสุด
      --scenario consult-single --run-dir eval/baseline/3.12.1 --plugin-version 3.12.1
"""
import json, os, sys, glob, argparse, pathlib

def usage_sum(f):
    tot, n = {}, 0
    for line in open(f, encoding='utf-8'):
        try: d = json.loads(line)
        except Exception: continue
        u = (d.get('message') or {}).get('usage')
        if not u: continue
        n += 1
        for k, v in u.items():
            if isinstance(v, int): tot[k] = tot.get(k, 0) + v
    return tot, n

ap = argparse.ArgumentParser()
ap.add_argument('--since', type=int, default=1, help='เอา subagent ล่าสุดกี่ตัว')
ap.add_argument('--agent-id', action='append', help='ระบุ agentId ตรง ๆ (ซ้ำได้)')
ap.add_argument('--scenario', required=True)
ap.add_argument('--run-dir', required=True)
ap.add_argument('--plugin-version', default='unknown')
ap.add_argument('--model', default='unknown')
ap.add_argument('--command', default='')
a = ap.parse_args()

root = os.path.expanduser(os.environ.get('CLAUDE_CONFIG_DIR', '~/.claude'))
files = sorted(glob.glob(f"{root}/projects/*/*/subagents/agent-*.jsonl"),
               key=os.path.getmtime, reverse=True)
if a.agent_id:
    files = [f for f in files if any(i in f for i in a.agent_id)]
else:
    files = files[:a.since]
if not files:
    print("ไม่เจอ subagent transcript"); sys.exit(1)

out = pathlib.Path(a.run_dir) / a.scenario
out.mkdir(parents=True, exist_ok=True)
for f in files:
    meta_p = f.replace('.jsonl', '.meta.json')
    meta = json.load(open(meta_p)) if os.path.exists(meta_p) else {}
    agent = (meta.get('agentType') or 'unknown').split(':')[-1]
    tot, n = usage_sum(f)
    rec = {
        "run_id": f"{os.path.basename(a.run_dir.rstrip('/'))}-{a.scenario}",
        "plugin_version": a.plugin_version, "model": a.model, "command": a.command,
        "phase": a.scenario, "agent": agent,
        "input_tokens": tot.get('input_tokens', 0),
        "cache_read_tokens": tot.get('cache_read_input_tokens', 0),
        "cache_write_tokens": tot.get('cache_creation_input_tokens', 0),
        "output_tokens": tot.get('output_tokens', 0),
        "duration_ms": 0, "turns": n,
        "source": os.path.basename(f),
    }
    i = 1
    while (out / f"{agent}-{i}.json").exists(): i += 1
    (out / f"{agent}-{i}.json").write_text(json.dumps(rec, ensure_ascii=False, indent=2))
    eff = rec['input_tokens'] + rec['cache_write_tokens'] + rec['output_tokens']
    print(f"  {agent:22} turns={n:3}  cache_write={rec['cache_write_tokens']:>8,}  "
          f"cache_read={rec['cache_read_tokens']:>9,}  out={rec['output_tokens']:>6,}  "
          f"effective={eff:>8,}")
print(f"-> {out}")
