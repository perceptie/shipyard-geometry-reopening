"""Recheck published task/chain arithmetic, not proprietary trajectory generation."""
from pathlib import Path
from decimal import Decimal as D
import csv
import json
import argparse


def main():
    p = argparse.ArgumentParser(description=__doc__)
    p.add_argument('--input', type=Path, default=Path(__file__).resolve().parent)
    p.add_argument('--output', type=Path)
    a = p.parse_args()
    read = lambda name: json.loads((a.input / name).read_text())
    rows = lambda name: list(csv.DictReader((a.input / name).open()))
    tasks = rows('task_phase_timelines.csv')
    chains = rows('crane_chain_accounting.csv')
    summary = read('terminal_plan_summary.json')
    patterns = read('critical_chain_decomposition.json')
    fields = ['initial_wait_from_common_origin_s', 'intertask_gap_sum_s',
              'empty_sum_s', 'base_hold_sum_s', 'loaded_sum_s']
    close = lambda x, y: abs(x-y) <= D('0.0000001')
    for t in tasks:
        assert close(D(t['end_relative_s'])-D(t['start_relative_s']),D(t['duration_s']))
        assert close(sum(D(t[f]) for f in ['empty_s','base_hold_s','loaded_s']),D(t['duration_s']))
    for c in chains:
        assert close(sum(D(c[f]) for f in fields),D(c['completion_relative_s']))
    for r in patterns:
        d = r['middle_minus_endpoint_critical_chain_s']
        assert close(sum(D(str(d[f])) for f in fields),D(str(d['completion_relative_s'])))
        assert close(D(str(d['completion_relative_s'])),D(str(r['middle_minus_endpoint_four_objective_s'][1])))
    rail = rows('adjacent_crane_exposure.csv')
    for r in rail:
        assert D(r['minimum_x_separation_m'])>=0
        assert close(D(r['zero_gap_positive_duration_s']),D(r['zero_gap_any_task_phase_s'])+D(r['zero_gap_neither_task_phase_s']))
        assert D(r['zero_gap_both_task_phases_s'])<=D(r['zero_gap_any_task_phase_s'])
    reuse = read('spatial_reuse_exposure.json')
    for r in reuse:
        assert close(D(str(r['next_start_relative_s']))-D(str(r['release_relative_s'])),D(str(r['release_to_reuse_slack_s'])))
    result = {'passed':True,'plans':len(summary),'task_rows':len(tasks),
              'chain_rows':len(chains),'witness_decompositions':len(patterns),
              'rail_pair_rows':len(rail),'reuse_rows':len(reuse),
              'scope':'Arithmetic on released derived records; does not regenerate trajectories or validate restricted industrial inputs'}
    if a.output:
        a.output.parent.mkdir(parents=True,exist_ok=True)
        a.output.write_text(json.dumps(result,indent=2)+'\n')
    print(json.dumps(result,indent=2))


if __name__=='__main__':main()
