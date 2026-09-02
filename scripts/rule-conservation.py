#!/usr/bin/env python3
"""Rule conservation gate (v3.13 — finding F28).

refactor ที่ 'ย้าย' กฎออกจาก preloaded skill ต้องมีกฎนั้นอยู่ที่อื่นเสมอ
budget ratchet ทุกตัว (#16/#20/#22) ให้รางวัลกับการ 'ลบ' กฎ -- gate นี้คือตัวถ่วง

กติกาที่ทำให้ gate นี้ไม่เป็นของประดับ:
  1. corpus = เฉพาะไฟล์ที่ 'เป็นที่อยู่ของกฎได้จริง' (skills + agents + commands + output-styles
     + references/runbooks) -- ไม่นับ README/MASTER/docs/eval ซึ่งเป็นเอกสารบรรยาย
  2. ไม่นับไฟล์ต้นทางเอง -- ไม่งั้น pointer ที่เหลือไว้จะ 'ยืนยัน' กฎที่เพิ่งลบไป
  3. ตรวจเฉพาะ 'บรรทัดกฎ' -- heading กับ blockquote เป็นป้ายชื่อ ไม่ใช่ตัวกฎ (§ ref มี gate #24a ดูแล)
  4. เทียบทีละ fragment -- บรรทัดเดียวมักผสมตัวกฎกับข้อความนำทาง
"""
import re, subprocess, sys, pathlib

THRESHOLD = 0.55
TOKEN = re.compile(r'[A-Za-z][A-Za-z0-9_.\-]{2,}|[฀-๿]{3,}')
STOP = {'ที่', 'และ', 'ของ', 'ให้', 'ไม่', 'เป็น', 'ต้อง', 'the', 'and', 'for', 'not'}
HOST = ('skills/', 'agents/', 'commands/', 'output-styles/', 'references/runbooks/')

def toks(line): return {t.lower() for t in TOKEN.findall(line)} - STOP
def is_rule(line): return '🔴' in line or 'ห้าม' in line
def is_pointer(line): return '→' in line or '.md' in line

def sh(*a): return subprocess.run(a, capture_output=True, text=True).stdout

changed = [f for f in sh('git', 'diff', '--name-only', 'HEAD').split()
           if re.fullmatch(r'skills/discipline/[^/]+/SKILL\.md', f)]
if not changed:
    print("  ok no preloaded skill changed"); sys.exit(0)

def corpus_for(src):
    """บรรทัดกฎทั้งหมดในรีโป ยกเว้นไฟล์ต้นทางเอง"""
    out = []
    for p in pathlib.Path('.').rglob('*.md'):
        rel = str(p).lstrip('./')
        if rel == src or not rel.startswith(HOST):
            continue
        if 'in-progress' in p.parts or 'deprecated' in p.parts:
            continue
        for line in p.read_text(errors='ignore').splitlines():
            t = toks(line)
            if t: out.append(t)
    return out

fail = 0
for f in changed:
    corpus = corpus_for(f)
    for line in sh('git', 'show', f'HEAD:{f}').splitlines():
        if len(line) < 25 or not is_rule(line):
            continue
        if line.lstrip().startswith(('#', '>')):
            continue
        for frag in re.split(r'[·|]|\. ', line):
            old = toks(frag)
            if len(old) < 4 or any(t.endswith('.md') for t in old):
                continue
            best = max((len(old & c) / len(old) for c in corpus), default=0.0)
            # ยังอยู่ในไฟล์ตัวเอง (ไม่ได้ย้าย ไม่ได้ลบ) = ผ่าน
            cur = pathlib.Path(f).read_text(errors='ignore')
            if best < THRESHOLD and max(
                    (len(old & toks(l)) / len(old) for l in cur.splitlines() if toks(l)),
                    default=0.0) < THRESHOLD:
                print(f"  X {f}: กฎหาย ({best:.0%} match) -- {frag.strip()[:72]}")
                fail = 1
if not fail:
    print(f"  ok rule conservation ({len(changed)} preloaded skill ที่แก้)")
sys.exit(fail)
