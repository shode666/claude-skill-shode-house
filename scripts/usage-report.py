#!/usr/bin/env python3
"""รวม usage record ต่อ run แล้วออกรายงานเทียบ baseline (WS10).

  scripts/usage-report.py outputs/token-usage/<run-id>/          -> summary.json + ตาราง
  scripts/usage-report.py --compare eval/baseline/3.12.1 outputs/token-usage/3.13-rc1
        -> median/p90 delta ต่อ scenario (input / cache_read / output / total)

record 1 ไฟล์ = 1 agent invocation ตาม eval/usage-record.schema.json
"""
import argparse, json, os, sys, glob, statistics as st

FIELDS = ['input_tokens','cache_read_tokens','cache_write_tokens','output_tokens']
def total(r): return r.get('input_tokens',0)+r.get('cache_write_tokens',0)+r.get('output_tokens',0)

class Unscorable(ValueError):
    """Missing or invalid observations must never produce PASS."""

def validate_record(r, path):
    if not isinstance(r, dict):
        raise Unscorable(f'{path}: record must be an object')
    for key in ['run_id', 'plugin_version', 'model', 'command', 'phase', 'agent']:
        if not isinstance(r.get(key), str) or not r[key].strip():
            raise Unscorable(f'{path}: missing/invalid {key}')
    for key in FIELDS + ['duration_ms']:
        if type(r.get(key)) is not int or r[key] < 0:
            raise Unscorable(f'{path}: {key} must be a nonnegative integer')
    for key in ['loaded_skills', 'loaded_references']:
        values = r.get(key, [])
        if not isinstance(values, list) or any(not isinstance(v, str) for v in values):
            raise Unscorable(f'{path}: {key} must be a string array')

def load(d):
    if not os.path.isdir(d):
        raise Unscorable(f'{d}: directory not found')
    out=[]
    for p in glob.glob(os.path.join(d,'**','*.json'), recursive=True):
        if os.path.basename(p)=='summary.json': continue
        try:
            with open(p, encoding='utf-8') as stream:
                r = json.load(stream)
        except (OSError, ValueError) as e:
            raise Unscorable(f'{p}: {e}') from e
        validate_record(r, p)
        out.append(r)
    if not out:
        raise Unscorable(f'{d}: no usage records')
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

def compare(base_dir, cand_dir, min_runs=3):
    if min_runs < 3:
        raise Unscorable('comparison requires at least 3 independent runs')
    def per_scenario(root):
        if not os.path.isdir(root):
            raise Unscorable(f'{root}: directory not found')
        out={}
        for d in sorted(glob.glob(os.path.join(root,'*'))):
            if not os.path.isdir(d): continue
            recs=load(d)
            runs = {}
            for r in recs:
                run = runs.setdefault(r['run_id'], {f: 0 for f in FIELDS})
                for f in FIELDS:
                    run[f] += r[f]
            if len(runs) < min_runs:
                raise Unscorable(f'{d}: {len(runs)} runs, need {min_runs}')
            out[os.path.basename(d)] = list(runs.values())
        if not out:
            raise Unscorable(f'{root}: no scenarios')
        return out
    A, B = per_scenario(base_dir), per_scenario(cand_dir)
    if A.keys() != B.keys():
        raise Unscorable(f'scenario mismatch: baseline-only={sorted(A.keys()-B.keys())}, candidate-only={sorted(B.keys()-A.keys())}')
    print('Per-run totals (all invocations, including retries). Legacy effective excludes cache reads; token volume includes them. Neither is monetary cost.')
    print(f"{'scenario / metric':46} {'A median':>10} {'B median':>10} {'Δ':>8}   {'A p90':>9} {'B p90':>9} {'Δ':>8}")
    worse=0
    metrics = {f: (lambda r, f=f: r[f]) for f in FIELDS}
    metrics['legacy_effective'] = total
    metrics['token_volume'] = lambda r: sum(r[f] for f in FIELDS)
    for k in sorted(A):
        for metric, measure in metrics.items():
            am,ap = med_p90([measure(r) for r in A[k]])
            bm,bp = med_p90([measure(r) for r in B[k]])
            dm = (bm-am)/am*100 if am else (float('inf') if bm else 0)
            dp = (bp-ap)/ap*100 if ap else (float('inf') if bp else 0)
            flag = ''
            if metric in ('legacy_effective', 'token_volume'):
                if dm > 3 or dp > 5:
                    flag = ' FAIL'; worse = 1
            print(f'{k + " / " + metric:46} {am:10,.0f} {bm:10,.0f} {dm:7.1f}%   {ap:9,.0f} {bp:9,.0f} {dp:7.1f}%{flag}')
    print("\nregression gate:", "FAIL — เกิน threshold (median +3% / p90 +5%)" if worse else "PASS")
    return worse

if __name__=='__main__':
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument('directory', nargs='?')
    parser.add_argument('--compare', nargs=2, metavar=('BASELINE', 'CANDIDATE'))
    parser.add_argument('--min-runs', type=int, default=3)
    args = parser.parse_args()
    try:
        if args.compare:
            sys.exit(compare(*args.compare, min_runs=args.min_runs))
        if not args.directory:
            parser.error('provide a directory or --compare BASELINE CANDIDATE')
        sys.exit(0 if summarize(args.directory) else 1)
    except Unscorable as e:
        print(f'UNSCORABLE: {e}', file=sys.stderr)
        sys.exit(2)
