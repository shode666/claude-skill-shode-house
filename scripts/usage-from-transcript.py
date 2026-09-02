#!/usr/bin/env python3
"""ดึง usage record จาก transcript ของ Claude Code (WS10 collector).

Claude Code เขียน transcript เป็น JSONL ที่ ~/.claude/projects/<project-slug>/<session>.jsonl
ทุก assistant message มี message.usage -> input / cache_creation / cache_read / output

  scripts/usage-from-transcript.py <transcript.jsonl> \
      --scenario phase3b-base --run-dir outputs/token-usage/3.12.1 \
      --plugin-version 3.12.1

  scripts/usage-from-transcript.py --list          # หา transcript ล่าสุด

🔴 รอบแรกให้เปิดไฟล์ที่ได้ดูด้วยตาก่อน 1 ไฟล์ ว่าเลข input/output ตรงกับที่เห็นใน
   /cost หรือ status line จริง -- schema ของ transcript เปลี่ยนได้ตามเวอร์ชัน CLI
"""
import json, sys, os, argparse, glob, pathlib, time

def rows(path):
    for line in open(path, encoding='utf-8'):
        line = line.strip()
        if not line: continue
        try: yield json.loads(line)
        except Exception: continue

def usage_of(r):
    m = r.get('message') or {}
    u = m.get('usage') or r.get('usage') or {}
    return u if u else None

def agent_of(r):
    # subagent invocation ถูกบันทึกด้วย field ต่างกันตามเวอร์ชัน -- ลองหลายทาง
    for k in ('subagent_type', 'agent', 'agentType', 'name'):
        v = r.get(k) or (r.get('message') or {}).get(k)
        if isinstance(v, str) and v: return v
    if r.get('isSidechain'): return 'subagent-unknown'
    return 'main'

def main():
    ap = argparse.ArgumentParser()
    ap.add_argument('transcript', nargs='?')
    ap.add_argument('--scenario'); ap.add_argument('--run-dir')
    ap.add_argument('--plugin-version', default='unknown')
    ap.add_argument('--model', default='unknown')
    ap.add_argument('--command', default='')
    ap.add_argument('--list', action='store_true')
    a = ap.parse_args()

    if a.list or not a.transcript:
        pat = os.path.expanduser('~/.claude/projects/**/*.jsonl')
        fs = sorted(glob.glob(pat, recursive=True), key=os.path.getmtime, reverse=True)[:10]
        if not fs: print("ไม่เจอ transcript ใต้ ~/.claude/projects/ -- รันจากเครื่องที่ใช้ Claude Code"); return 1
        for f in fs:
            print(f"{time.strftime('%Y-%m-%d %H:%M', time.localtime(os.path.getmtime(f)))}  {f}")
        return 0

    if not (a.scenario and a.run_dir):
        print("ต้องมี --scenario และ --run-dir"); return 2

    out = pathlib.Path(a.run_dir) / a.scenario
    out.mkdir(parents=True, exist_ok=True)
    run_id = f"{os.path.basename(a.run_dir.rstrip('/'))}-{a.scenario}"
    n, by = 0, {}
    for r in rows(a.transcript):
        u = usage_of(r)
        if not u: continue
        agent = agent_of(r)
        by.setdefault(agent, []).append(u)

    for agent, us in by.items():
        rec = {
            "run_id": run_id, "plugin_version": a.plugin_version, "model": a.model,
            "command": a.command, "phase": a.scenario, "agent": agent,
            "input_tokens": sum(u.get('input_tokens', 0) for u in us),
            "cache_read_tokens": sum(u.get('cache_read_input_tokens', 0) for u in us),
            "cache_write_tokens": sum(u.get('cache_creation_input_tokens', 0) for u in us),
            "output_tokens": sum(u.get('output_tokens', 0) for u in us),
            "duration_ms": 0,
            "turns": len(us),
        }
        i = 1
        while (out / f"{agent}-{i}.json").exists(): i += 1
        (out / f"{agent}-{i}.json").write_text(json.dumps(rec, ensure_ascii=False, indent=2))
        n += 1
        print(f"  {agent:24} turns={len(us):3}  in={rec['input_tokens']:>8,}  "
              f"cache_read={rec['cache_read_tokens']:>9,}  out={rec['output_tokens']:>7,}")
    print(f"เขียน {n} record ลง {out}")
    if n and 'main' in by and len(by) == 1:
        print("⚠️  เจอแต่ agent 'main' -- transcript นี้อาจไม่มี subagent หรือ field ชื่อต่างจากที่ script รู้จัก")
    return 0

sys.exit(main())
