#!/usr/bin/env python3
"""รวม usage record ต่อ run แล้วออกรายงานเทียบ baseline (WS10).

  scripts/usage-report.py outputs/token-usage/<run-id>/          -> summary.json + ตาราง
  scripts/usage-report.py --compare eval/baseline/3.12.1 outputs/token-usage/3.13-rc1
        -> median/p90 delta ต่อ scenario (input / cache_read / output / total)

record 1 ไฟล์ = 1 agent invocation ตาม eval/usage-record.schema.json
"""
import json, os, sys, glob, statistics as st

FIELDS = ['input_tokens','cache_read_tokens','cache_write_tokens','output_tokens']
def total(r): return r.get('input_tokens',0)+r.get('cache_write_tokens',0)+r.get('output_tokens',0)

def load(d):
    out=[]
    for p in glob.glob(os.path.join(d,'**','*.json'), recursive=True):
        if os.path.basename(p)=='summary.json': continue
        try: out.append(json.load(open(p,encoding='utf-8')))
        except Exception as e: print(f"  ! อ่านไม่ได้: {p} ({e})", file=sys.stderr)
    return out

def amplification(recs):
    """WS10.5 repeated-load: reference/skill ที่ถูกโหลดซ้ำใน run เดียว"""
    seen={}
    for r in recs:
        for k in r.get('loaded_skills',[])+r.get('loaded_references',[]):
            seen.setdefault(k,[]).append(r.get('agent','?'))
    return {k:v for k,v in seen.items() if len(v)>1}

def summarize(d):
    recs=load(d)
    if not recs: print(f"ไม่พบ record ใน {d}"); return None
    s={'run':os.path.basename(d.rstrip('/')),'records':len(recs),
       'by_agent':{}, 'totals':{f:sum(r.get(f,0) for r in recs) for f in FIELDS}}
    s['totals']['total_effective_tokens']=sum(total(r) for r in recs)
    for r in recs:
        a=r.get('agent','?'); b=s['by_agent'].setdefault(a,{f:0 for f in FIELDS}|{'invocations':0})
        b['invocations']+=1
        for f in FIELDS: b[f]+=r.get(f,0)
    amp=amplification(recs)
    if amp: s['repeated_loads']={k:len(v) for k,v in sorted(amp.items(), key=lambda x:-len(x[1]))}
    s['tool'] = {k:sum(r.get(k,0) for r in recs) for k in
                 ['tool_calls','tool_output_chars','files_read','duplicate_files_read']}
    out=os.path.join(d,'summary.json'); json.dump(s, open(out,'w',encoding='utf-8'), indent=2, ensure_ascii=False)
    print(f"{s['run']}: {s['records']} records · total {s['totals']['total_effective_tokens']:,} tok "
          f"(in {s['totals']['input_tokens']:,} / cache-read {s['totals']['cache_read_tokens']:,} / out {s['totals']['output_tokens']:,})")
    if amp:
        print("  repeated loads:", ", ".join(f"{k}×{len(v)}" for k,v in sorted(amp.items(), key=lambda x:-len(x[1]))[:5]))
    print(f"  -> {out}")
    return s

def med_p90(vals):
    vals=sorted(vals)
    return (st.median(vals), vals[min(len(vals)-1, int(round(0.9*(len(vals)-1))))]) if vals else (0,0)

def compare(base_dir, cand_dir):
    def per_scenario(root):
        out={}
        for d in sorted(glob.glob(os.path.join(root,'*'))):
            if not os.path.isdir(d): continue
            recs=load(d)
            if recs: out[os.path.basename(d)]=[total(r) for r in recs]
        return out
    A, B = per_scenario(base_dir), per_scenario(cand_dir)
    print(f"{'scenario':24} {'A median':>10} {'B median':>10} {'Δ':>8}   {'A p90':>9} {'B p90':>9} {'Δ':>8}")
    worse=0
    for k in sorted(set(A)|set(B)):
        am,ap = med_p90(A.get(k,[])); bm,bp = med_p90(B.get(k,[]))
        dm = (bm-am)/am*100 if am else 0; dp = (bp-ap)/ap*100 if ap else 0
        flag = ''
        if dm > 3: flag=' ← median +>3%'; worse=1
        if dp > 5: flag+=' p90 +>5%'; worse=1
        print(f"{k:24} {am:10,.0f} {bm:10,.0f} {dm:7.1f}%   {ap:9,.0f} {bp:9,.0f} {dp:7.1f}%{flag}")
    print("\nregression gate:", "FAIL — เกิน threshold (median +3% / p90 +5%)" if worse else "PASS")
    return worse

if __name__=='__main__':
    if '--compare' in sys.argv:
        i=sys.argv.index('--compare'); sys.exit(compare(sys.argv[i+1], sys.argv[i+2]))
    if len(sys.argv)<2: print(__doc__); sys.exit(2)
    sys.exit(0 if summarize(sys.argv[1]) else 1)
