#!/usr/bin/env python3
"""Exact full-objective comparison of released mask records; no solver calls."""
import argparse
import collections
import csv
import hashlib
import json
from pathlib import Path

HERE = Path(__file__).resolve().parent
FIELDS = ['projected_completion_us', 'current_batch_makespan_us',
          'total_completion_us', 'pool_value_us']
RAW_FIELDS = ['projected_current_batch_completion', 'current_batch_makespan',
              'current_batch_total_completion_time', 'value']
MODES = ['J_VND', 'S_VND', 'J_REFERENCE_SEED', 'J_FIELD128', 'J_RAIL512']


def sha(data):
    return hashlib.sha256(data).hexdigest()


def canonical(value):
    return json.dumps(value, sort_keys=True, separators=(',', ':')).encode()


def dump(path, obj):
    path.write_text(json.dumps(obj, indent=2, ensure_ascii=False) + '\n')


def write_csv(path, rows):
    with path.open('w', newline='') as f:
        w = csv.DictWriter(f, fieldnames=list(rows[0]))
        w.writeheader()
        for row in rows:
            w.writerow({k: json.dumps(v, separators=(',', ':')) if isinstance(v, (list, dict)) else v
                        for k, v in row.items()})


def key(r):
    if not r['success']: return (1,)
    a=r['objective_us']
    assert len(a)==4 and all(v is None or isinstance(v,int) for v in a)
    return (0,int(a[0] is None),0 if a[0] is None else a[0],*a[1:])


def relation(a,b):
    if not a['success'] and not b['success']: return 'both_failed'
    return 'better' if key(a)<key(b) else 'worse' if key(a)>key(b) else 'tie'


def best(rows):
    assert rows
    return min(rows,key=key)


def delta(a,b):
    """New minus reference, signed integers; null when either is unsuccessful."""
    if not a['success'] or not b['success']: return None
    return [None if x is None or y is None else x-y for x,y in zip(a['objective_us'],b['objective_us'])]


def summary_row(r):
    return {k:r.get(k) for k in ('candidate_id','mode','mask','success','objective_us','geometry_sha256')}


def tag(row,cid,mode=None):
    return dict(row,candidate_id=cid,mode=mode)


def bits(mask,n):
    return [f'u{i+1}' for i in range(n) if mask & (1<<i)]


def analyze(args):
    inp=args.output/'anonymous_inputs.json';doc=json.loads(inp.read_text())
    cases=doc['cases']; aggregates=[];candrows=[];edges=[];structure=[];patternrows=[];eqrows=[]
    counts=collections.Counter();eqcounts=collections.Counter();patternkeys=set()
    for case in cases:
        ref=case['reference'];masked=[c for c in case['candidates'] if c['masks']]
        assert len(masked)==6
        endpoints=[];allmasks=[];fullendpoints=[];fullsimple=[]
        for cand in case['candidates']:
            cid=cand['candidate_id'];modes={k:tag(v,cid,k) for k,v in cand['modes'].items()}
            counts['candidate_execution_groups']+=1
            fullendpoints.extend(modes[k] for k in ('J_VND','S_VND'));fullsimple.extend(modes.values())
            if not cand['masks']: continue
            n=cand['mutable_blocks'];masks=[tag(m,cid,'MASK') for m in cand['masks']]
            assert [r['mask'] for r in masks]==list(range(1<<n))
            empty,full=masks[0],masks[-1];end=best([empty,full]);bm=best(masks)
            endpoints.extend([empty,full]);allmasks.extend(masks)
            counts['mask_candidate_groups']+=1;counts['mask_rows']+=len(masks)
            counts['successful_masks']+=sum(m['success'] for m in masks)
            counts['candidate_endpoint_'+relation(empty,full)]+=1
            counts['candidate_bestmask_vs_own_endpoints_'+relation(bm,end)]+=1
            for name,a,b in [('empty_vs_S',empty,modes['S_VND']),('full_vs_J',full,modes['J_VND']),
                              ('full_vs_reference_seed',full,modes['J_REFERENCE_SEED'])]:
                rel=relation(a,b);geo=None if not (a['success'] and b['success']) else a['geometry_sha256']==b['geometry_sha256']
                eqcounts[(name,rel)]+=1
                if geo is not None: eqcounts[(name,'same_geometry' if geo else 'different_geometry')]+=1
                eqrows.append({'case_id':case['case_id'],'state':case['state'],'candidate_id':cid,
                    'comparison':name,'objective_relation':rel,'both_successful':a['success'] and b['success'],
                    'same_decoded_geometry':geo,'mask_diagnostic':a['diagnostic'],'mode_diagnostic':b['diagnostic'],
                    'same_field_iterations':a['field_iterations']==b['field_iterations'],
                    'same_rail_iterations':a['rail_repair_iterations']==b['rail_repair_iterations']})
            candrows.append({'case_id':case['case_id'],'state':case['state'],'candidate_id':cid,
                'mutable_blocks':n,'successful_masks':sum(m['success'] for m in masks),
                'empty_success':empty['success'],'full_success':full['success'],
                'best_mask_ids':[m['mask'] for m in masks if m['success'] and key(m)==key(bm)],
                'best_endpoint_objective_us':end['objective_us'], 'best_mask_objective_us':bm['objective_us'],
                'best_mask_vs_own_endpoints':relation(bm,end), 'delta_vs_endpoint_us':delta(bm,end),
                'best_mask_vs_reference':relation(bm,ref),'delta_vs_reference_us':delta(bm,ref)})
            winners=[m['mask'] for m in masks if m['success'] and key(m)==key(bm)]
            if winners:
                inter=(1<<n)-1;union=0
                for v in winners:inter &=v;union|=v
                mincard=min(bin(m).count('1') for m in winners)
                minmasks=[m for m in winners if bin(m).count('1')==mincard]
                free=union^inter;closed=((1<<n)-1)^union
                cartesian=len(winners)==(1<<bin(free).count('1'))
                sr={'case_id':case['case_id'],'state':case['state'],'candidate_id':cid,'mutable_blocks':n,
                    'best_masks':winners,'best_count':len(winners),'common_open':bits(inter,n),
                    'common_closed':bits(closed,n),'varying_among_best':bits(free,n),
                    'all_combinations_of_varying_bits_optimal':cartesian,
                    'minimum_cardinality':mincard,'minimum_cardinality_masks':minmasks,
                    'unique_minimum_cardinality':len(minmasks)==1,
                    'best_objective_us':bm['objective_us'],
                    'best_geometry_signatures':sorted(set(m['geometry_sha256'] for m in masks if m['mask'] in winners))}
                structure.append(sr)
                if relation(bm,end)=='better':
                    pk=(case['state'],cid.split('-')[-1])
                    if pk not in patternkeys:
                        patternkeys.add(pk)
                        patternrows.append(dict(sr, endpoint=summary_row(end),best=summary_row(bm),
                            reference=summary_row(ref),delta_vs_own_endpoint_us=delta(bm,end),
                            delta_vs_reference_us=delta(bm,ref),mask_results=masks))
            for m in masks:
                for i in range(n):
                    if m['mask'] & (1<<i):continue
                    added=masks[m['mask'] | (1<<i)]
                    rel=relation(added,m)
                    counts['one_bit_'+rel]+=1
                    counts['one_bit_'+rel+'_from_'+str(m['success'])+'_to_'+str(added['success'])]+=1
                    edges.append({'case_id':case['case_id'],'state':case['state'],'candidate_id':cid,
                        'from_mask':m['mask'],'to_mask':added['mask'],'opened_block':f'u{i+1}',
                        'from_success':m['success'],'to_success':added['success'],'objective_relation':rel,
                        'geometry_changed':None if not (m['success'] and added['success']) else
                              m['geometry_sha256']!=added['geometry_sha256'],
                        'objective_delta_us':delta(added,m),
                        'from_field_iterations':m['field_iterations'],'to_field_iterations':added['field_iterations'],
                        'from_rail_iterations':m['rail_repair_iterations'],'to_rail_iterations':added['rail_repair_iterations']})
        be,bm,bf,bs=map(best,(endpoints,allmasks,fullendpoints,fullsimple))
        agg={'case_id':case['case_id'],'state':case['state'],'execution':case['execution'],
            'all_candidates':len(case['candidates']),'mask_candidates':len(masked),
            'reference_candidate_id':case['reference_candidate_id'],
            'reference_in_mask_candidates':case['reference_candidate_id'] in [c['candidate_id'] for c in masked],
            'reference':summary_row(ref),'six_candidate_endpoint_best':summary_row(be),
            'six_candidate_mask_best':summary_row(bm),'all_candidate_endpoint_best':summary_row(bf),
            'all_candidate_simple_best':summary_row(bs),
            'mask_vs_six_endpoint':relation(bm,be),'mask_vs_all_endpoint':relation(bm,bf),
            'mask_vs_all_simple':relation(bm,bs),'mask_vs_reference':relation(bm,ref),
            'mask_vs_all_simple_and_reference':relation(bm,best([bs,ref])),
            'mask_delta_vs_six_endpoint_us':delta(bm,be),'mask_delta_vs_all_endpoint_us':delta(bm,bf),
            'mask_delta_vs_all_simple_us':delta(bm,bs),'mask_delta_vs_reference_us':delta(bm,ref)}
        aggregates.append(agg)
        for name in ('six_endpoint','all_endpoint','all_simple','reference','all_simple_and_reference'):
            counts['state_execution_mask_vs_'+name+'_'+agg['mask_vs_'+name]]+=1
    for p in patternrows:
        c=next(a for a in aggregates if a['case_id']==p['case_id'])
        p['case_comparison']=c
        p['one_bit_edges']=[e for e in edges if e['candidate_id']==p['candidate_id']]
    plotrows=[];baselines=[];vectorrows=[]
    for p in patternrows:
        own=p['endpoint'];bestrow=p['best'];agg=p['case_comparison']
        for m in p['mask_results']:
            plotrows.append({'state':p['state'],'candidate_id':p['candidate_id'],
                'mutable_blocks':p['mutable_blocks'],'mask':m['mask'],
                'open_set':bits(m['mask'],p['mutable_blocks']),'open_count':m['open_count'],
                'success':m['success'],'objective_us':m['objective_us'],
                'delta_vs_same_candidate_best_endpoint_us':delta(m,own),
                'is_lex_best':key(m)==key(bestrow),'opens_u4':bool(m['mask'] & 8),
                'geometry_sha256':m['geometry_sha256'],'field_iterations':m['field_iterations'],
                'rail_repair_iterations':m['rail_repair_iterations'],'elapsed_us':m['elapsed_us']})
        refs={'same_candidate_endpoint':own,'common_initial':agg['reference'],
              'six_candidate_endpoint_best':agg['six_candidate_endpoint_best'],
              'six_candidate_mask_best':agg['six_candidate_mask_best'],
              'all_candidate_endpoint_best':agg['all_candidate_endpoint_best'],
              'all_candidate_simple_best':agg['all_candidate_simple_best']}
        for name,r in refs.items():
            baselines.append({'state':p['state'],'candidate_id':p['candidate_id'],
                'comparator':name,'comparator_candidate_id':r.get('candidate_id'),
                'comparator_mode':r.get('mode'),'comparator_mask':r.get('mask'),
                'comparator_objective_us':r['objective_us'],
                'same_projection_as_pattern':r['success'] and r['objective_us'][0]==bestrow['objective_us'][0],
                'comparator_delta_vs_pattern_endpoint_us':delta(r,own),
                'pattern_best_relation_to_comparator':relation(bestrow,r),
                'pattern_best_delta_vs_comparator_us':delta(bestrow,r)})
        for label,r in [('empty',p['mask_results'][0]),('full',p['mask_results'][-1]),
                        ('best_intermediate',bestrow),*list(refs.items())[1:]]:
            vectorrows.append({'state':p['state'],'candidate_id':p['candidate_id'],'result':label,
                **dict(zip(FIELDS,r['objective_us'])),
                'relation_to_best_intermediate':relation(r,bestrow),
                'delta_vs_same_candidate_best_endpoint_us':delta(r,own)})
    assert counts['candidate_execution_groups']==510 and counts['mask_rows']==1656
    assert counts['mask_candidate_groups']==90 and counts['successful_masks']==570
    # Regression witnesses are consequences of the exact comparator, not imposed outcomes.
    lookup={p['state']:p for p in patternrows}
    assert lookup['b2-r096']['delta_vs_own_endpoint_us'][2]==3658*10**6
    assert lookup['b3-r071']['common_open']==['u2','u6']
    assert lookup['b3-r071']['common_closed']==['u4']
    out={'version':'p02-mask-structure-analysis/1.0','source_input_sha256':sha(inp.read_bytes()),
         'units':'integer microseconds; objective deltas are new minus comparator',
         'comparator':'valid success, projection presence, projection, pool makespan, sum completion, pool value',
         'counts':dict(counts),'endpoint_consistency':{'/'.join(k):v for k,v in eqcounts.items()},
         'scope':'Retained outputs only; no solver runs, no equal-budget online or execution claim',
         'state_execution_results':aggregates}
    dump(args.output/'analysis_summary.json',out)
    dump(args.output/'winning_pattern_structure.json',patternrows)
    dump(args.output/'best_mask_structures.json',structure)
    write_csv(args.output/'candidate_comparisons.csv',candrows)
    write_csv(args.output/'state_execution_comparisons.csv',aggregates)
    write_csv(args.output/'one_bit_comparisons.csv',edges)
    write_csv(args.output/'endpoint_consistency.csv',eqrows)
    write_csv(args.output/'figure_mask_rows.csv',plotrows)
    write_csv(args.output/'figure_baselines.csv',baselines)
    write_csv(args.output/'representative_objective_vectors.csv',vectorrows)
    print(json.dumps({'counts':dict(counts),'endpoint_consistency':out['endpoint_consistency']},indent=2))


def main():
    p=argparse.ArgumentParser(description="Recompute mask comparisons from released anonymous records")
    p.add_argument('--output',type=Path,default=HERE)
    a=p.parse_args();a.output.mkdir(parents=True,exist_ok=True)
    if a.output.resolve()!=HERE.resolve():
        import shutil
        shutil.copy2(HERE/'anonymous_inputs.json',a.output/'anonymous_inputs.json')
    analyze(a)

if __name__=='__main__':main()
