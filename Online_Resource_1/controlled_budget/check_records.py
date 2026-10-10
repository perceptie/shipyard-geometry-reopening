"""Recompute formal E32 event monotonicity and paired rankings from public records."""
from pathlib import Path
import argparse,csv,json
from decimal import Decimal as D
FIELDS=['projected_current_batch_completion','current_batch_makespan','current_batch_total_completion_time','value']
def vec(r):return tuple(int(r[k]) for k in FIELDS)
def main():
    p=argparse.ArgumentParser(description=__doc__)
    p.add_argument('--input',type=Path,default=Path(__file__).resolve().parent)
    p.add_argument('--output',type=Path)
    a=p.parse_args();s=json.loads((a.input/'summary.json').read_text())
    read=lambda n:list(csv.DictReader((a.input/n).open()))
    phases=read('search_phases.csv');events=read('strict_improvements.csv')
    assert len(phases)==48 and len(s['states'])==4 and s['checks_passed']
    initial={r['state']:r for r in s['states']}
    for r in phases:
        ini=initial[r['state']]
        assert r['common_initial_sha256']==ini['common_initial_sha256']
        budget=12000000 if r['budget']=='full' else max(0,12000000-ini['construction_microseconds'])
        assert D(r['budget_seconds'])*1000000==budget
        h=[e for e in events if all(e[k]==r[k] for k in ['state','repeat','budget','method'])]
        assert len(h)==int(r['strict_improvements'])
        best=vec(ini['initial_cost']);t=D(0)
        for e in h:
            assert t<=D(e['elapsed_seconds'])<=D(r['elapsed_seconds'])
            assert vec(e)<best
            t=D(e['elapsed_seconds']);best=vec(e)
        assert best==vec(r)
    for c in s['comparisons']:
        for item in c['pairs']:
            pair={r['method']:r for r in phases if r['state']==c['state'] and r['budget']==c['budget'] and int(r['repeat'])==item['repeat']}
            j,ss=pair['J_VND'],pair['S_VND'];a1,b=vec(j),vec(ss)
            expected='tie' if a1==b else 'J' if a1<b else 'S'
            assert item['winner']==expected
            level=next((k for k in FIELDS if int(j[k])!=int(ss[k])),None)
            assert level==item['first_difference']
            delta=0 if level is None else int(ss[level])-int(j[level])
            assert abs(D(str(item['S_minus_J_seconds']))*1000000-delta)<D('.001')
    result={'passed':True,'phases':len(phases),'strict_improvement_events':len(events),'paired_comparisons':24,
      'scope':'Public event arithmetic and ranking; restricted plan/model validation is separately reported'}
    if a.output:
        a.output.parent.mkdir(parents=True,exist_ok=True);a.output.write_text(json.dumps(result,indent=2)+'\n')
    print(json.dumps(result,indent=2))
if __name__=='__main__':main()
