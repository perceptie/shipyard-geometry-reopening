"""Recompute the two terminal-case examples using only public supplement files.

Standard-library only. Run:
    python validate_terminal_cases.py
The default output is reproduced/terminal_case_checks.json beside this script.
This is an arithmetic and content-fingerprint audit, not a raw-input solver replay.
"""
from __future__ import annotations

import argparse
import csv
from decimal import Decimal
import hashlib
import json
from pathlib import Path
import re


MICRO = Decimal(1_000_000)
GATE_NAMES = (
    'source_state_match', 'configuration_and_binary_match',
    'accepted_solve_mode_match', 'accepted_invocation_cap_match',
    'initial_sequence_assignment_tandem_match', 'initial_geometry_match',
)
COST_NAMES = (
    'compatibility', 'projected_completion', 'current_batch_makespan',
    'current_batch_total_completion', 'pool_makespan',
)
COST_LABELS = (
    'projection_presence', 'projected_current_batch_completion',
    'current_batch_makespan', 'current_batch_total_completion_time',
    'search_pool_makespan',
)


def require(condition: bool, message: str) -> None:
    if not condition:
        raise ValueError(message)


def seconds(value: int | Decimal | float | str) -> Decimal:
    return Decimal(str(value))


def integer_microseconds(value: int | Decimal | float | str) -> int:
    converted = seconds(value) * MICRO
    require(converted == converted.to_integral_value(), 'Time precision exceeds one microsecond')
    return int(converted)


def digest(path: Path) -> str:
    return hashlib.sha256(path.read_bytes()).hexdigest()


def cost_key(run: dict) -> tuple[int, ...]:
    cost = run['cost_integer_microseconds']
    require(cost['valid'] is True, 'Invalid final Cost')
    return (0, cost['projected_current_batch_completion'], cost['current_batch_makespan'],
            cost['current_batch_total_completion_time'], cost['value'])


def verify_run(run: dict, count: int) -> dict:
    tasks = {t['task']: t for t in run['final_tasks']}
    require(len(tasks) == count == len(run['final_tasks']), 'Task coverage mismatch')
    require(all(re.fullmatch(r'T[1-9][0-9]*', t) for t in tasks), 'Invalid task alias')
    for task in tasks.values():
        start, end = (integer_microseconds(task[k]) for k in ('start_seconds', 'end_seconds'))
        components = [integer_microseconds(task[k]) for k in ('empty_seconds', 'base_seconds', 'loaded_seconds')]
        require(all(v >= 0 for v in components), 'Negative task duration')
        require(end - start == sum(components), 'Task duration components do not sum')
    ends = [integer_microseconds(t['end_seconds']) for t in tasks.values()]
    relative = run['cost_relative_seconds']
    require(max(ends) == integer_microseconds(relative['current_batch_makespan']), 'Relative makespan mismatch')
    require(max(ends) == integer_microseconds(relative['value']), 'Pool makespan mismatch')
    require(sum(ends) == integer_microseconds(relative['current_batch_total_completion_time']), 'Relative completion sum mismatch')
    cost = run['cost_integer_microseconds']
    epoch = cost['current_batch_makespan'] - max(ends)
    require(cost['current_batch_total_completion_time'] == sum(ends) + count * epoch, 'Absolute completion sum mismatch')
    require(cost['value'] == max(ends) + epoch, 'Absolute pool makespan mismatch')
    require(cost['projected_current_batch_completion'] == integer_microseconds(relative['projected_current_batch_completion']) + epoch, 'Projection offset mismatch')

    spans = {}
    bindings = {t: [] for t in tasks}
    for crane, sequence in run['final_sequences'].items():
        require(re.fullmatch(r'C[1-9][0-9]*', crane) is not None, 'Invalid crane alias')
        require(len(sequence) == len(set(sequence)), 'Duplicate task in crane sequence')
        for task in sequence:
            require(task in tasks, 'Unknown task in sequence')
            bindings[task].append(crane)
        if not sequence:
            continue
        intervals = [(integer_microseconds(tasks[t]['start_seconds']), integer_microseconds(tasks[t]['end_seconds'])) for t in sequence]
        require(all(a[1] <= b[0] for a, b in zip(intervals, intervals[1:])), 'Sequence overlap or order mismatch')
        processing = sum(b-a for a, b in intervals)
        gaps = sum(b[0]-a[1] for a, b in zip(intervals, intervals[1:]))
        expected = run['crane_task_spans'][crane]
        for key, value in [('first_start_seconds', intervals[0][0]), ('last_end_seconds', intervals[-1][1]), ('task_processing_seconds', processing), ('between_task_gaps_seconds', gaps)]:
            require(integer_microseconds(expected[key]) == value, 'Stored crane-span aggregate mismatch')
        spans[crane] = {'task_processing_seconds': processing / 1e6, 'between_task_gaps_seconds': gaps / 1e6}
    for alias, task in tasks.items():
        require(sorted(bindings[alias]) == sorted(task['cranes']), 'Task assignment differs from sequence binding')
        require(len(bindings[alias]) == (2 if task['tandem'] else 1), 'Assignment/tandem inconsistency')

    occupancy_releases = 0
    for occupancy in run['active_occupancies']:
        require(re.fullmatch(r'B[1-9][0-9]*', occupancy['block']) is not None, 'Invalid block alias')
        require(re.fullmatch(r'R[1-9][0-9]*', occupancy['region']) is not None, 'Invalid region alias')
        carry = occupancy['carry_task']
        if carry:
            task = tasks[carry]
            release = sum(integer_microseconds(task[k]) for k in ('start_seconds', 'empty_seconds', 'base_seconds'))
            require(integer_microseconds(occupancy['end_seconds']) == release, 'Carry occupancy-release mismatch')
            occupancy_releases += 1
        if not occupancy['committed_at_input']:
            starts = [integer_microseconds(tasks[t]['start_seconds']) for t in occupancy['entry_tasks']]
            require(bool(starts), 'New occupancy lacks an entry task')
            require(integer_microseconds(occupancy['start_seconds']) == min(starts), 'New occupancy-start mismatch')
    changed = sorted(o['block'] for o in run['active_occupancies'] if not o['geometry_equals_initial'])
    require(changed == sorted(run['final_changed_blocks_from_initial']), 'Geometry-change record mismatch')
    for motion in run['non_task_motions']:
        require(integer_microseconds(motion['end_seconds']) - integer_microseconds(motion['start_seconds']) == integer_microseconds(motion['duration_seconds']), 'Non-task motion duration mismatch')
    return {'crane_spans': spans, 'checked_release_count': occupancy_releases}


def main() -> None:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument('--data-dir', type=Path, default=Path(__file__).resolve().parent)
    parser.add_argument('--output-dir', type=Path)
    args = parser.parse_args()
    directory = args.data_dir
    evidence_path = directory / 'terminal_case_evidence.json'
    csv_path = directory / 'e10_state_outcomes.csv'
    text = evidence_path.read_text()
    require(not any(s in text for s in ('/Users/', '/home/')) and not re.search(r'\bdes-[A-Za-z0-9_-]+\b', text), 'Private source path or host in public evidence')
    data = json.loads(text, parse_float=Decimal)
    require(data['initial_plan_separately_stored'] is False, 'Initial-plan availability must remain explicit')
    require(data['new_solver_executions'] == 0, 'Unexpected new optimization run')
    require({c['state'] for c in data['cases']} == {'b3-r006', 'b3-r071'}, 'Unexpected case set')
    with csv_path.open(newline='') as stream:
        rows = {(r['state'], int(r['repeat'])): r for r in csv.DictReader(stream)}
    pairs = []
    states = {}
    for case in data['cases']:
        state = case['state']
        require(sorted(r['repeat'] for r in case['repeats']) == [1, 2, 3], 'Repeated/missing repetition')
        state_results = []
        for rep in case['repeats']:
            j, s = (rep['methods'][m] for m in ('J_VND', 'S_VND'))
            jg, sg = (r['gate_fingerprints'] for r in (j, s))
            gate = {
                'source_state_match': jg['source_state_fingerprints'] == sg['source_state_fingerprints'] and jg['warm_start_mode'] == sg['warm_start_mode'],
                'configuration_and_binary_match': jg['common_configuration_sha256'] == sg['common_configuration_sha256'] and jg['binary_sha256'] == sg['binary_sha256'],
                'accepted_solve_mode_match': j['mode'] == s['mode'],
                'accepted_invocation_cap_match': j['budget_seconds'] == s['budget_seconds'],
                'initial_sequence_assignment_tandem_match': j['initial_sequence_signature_sha256'] == s['initial_sequence_signature_sha256'],
                'initial_geometry_match': j['initial_geometry_signature_sha256'] == s['initial_geometry_signature_sha256'],
            }
            public = rows[state, rep['repeat']]
            for name in GATE_NAMES:
                require(gate[name] == (public[name] == 'True'), f'{state}: gate field differs from CSV: {name}')
            require(all(gate.values()) and public['pair_eligible'] == 'True', 'Ineligible selected pair')
            require(public['initial_cost_separately_logged'] == 'False', 'Unexpected public initial-plan claim')
            require(all(rep['input_field_equality'].values()), 'Recorded non-sequence input mismatch')
            run_checks = {}
            for method, run in (('J_VND', j), ('S_VND', s)):
                prefix = method[0]
                expected_cost = tuple(int(public[f'{prefix}_final_{name}_microseconds']) for name in COST_NAMES)
                require(cost_key(run) == expected_cost, 'Cost differs from public CSV')
                require(run['mode'] == public[f'{prefix}_solve_mode'], 'Mode differs from public CSV')
                require(run['budget_seconds'] == int(public[f'{prefix}_invocation_cap_seconds']), 'Cap differs from public CSV')
                require(re.fullmatch(r'E10/b3-r(?:006|071)/repeat-[123]/[JS]_VND', run['source_trace_label']) is not None, 'Source label is not anonymized')
                require(re.fullmatch(r'[0-9a-f]{64}', run['trace_sha256']) is not None, 'Missing trace content fingerprint')
                run_checks[method] = verify_run(run, case['task_count'])
            jc, sc = cost_key(j), cost_key(s)
            outcome = 'J_win' if jc < sc else 'S_win' if sc < jc else 'tie'
            level = next((label for label, a, b in zip(COST_LABELS, jc, sc) if a != b), None)
            difference = Decimal(sc[2]-jc[2]) / MICRO
            require(outcome == public['outcome'], 'Outcome differs from public CSV')
            require(level == public['first_differing_level'] == 'current_batch_makespan', 'Unexpected first Cost difference')
            require(difference == Decimal(public['S_minus_J_current_batch_makespan_seconds']), 'Cost difference differs from public CSV')
            record = {'state': state, 'repeat': rep['repeat'], 'gate': gate, 'outcome': outcome, 'first_differing_level': level, 'S_minus_J_makespan_seconds': float(difference), 'method_checks': run_checks}
            pairs.append(record)
            state_results.append(record)
        states[state] = {'differences_seconds': [r['S_minus_J_makespan_seconds'] for r in state_results], 'distinct_final_plan_fingerprints': {m: len({r['methods'][m]['final_plan_sha256'] for r in case['repeats']}) for m in ('J_VND', 'S_VND')}}

    positive, negative = ({c['state']: c for c in data['cases']}[s] for s in ('b3-r006', 'b3-r071'))
    require(states['b3-r006']['differences_seconds'] == [233.326755] * 3, 'Positive-case manuscript difference changed')
    require(states['b3-r071']['differences_seconds'] == [-1356.0, -1356.0, -6419.0], 'Negative-case manuscript differences changed')
    require(states['b3-r006']['distinct_final_plan_fingerprints'] == {'J_VND': 1, 'S_VND': 1}, 'Positive-case terminal stability changed')
    for rep in positive['repeats']:
        j, s = (rep['methods'][m] for m in ('J_VND', 'S_VND'))
        for run, workload, gaps in ((j, 55566, 0), (s, 55066, Decimal('733.326755'))):
            span = run['crane_task_spans']['C2']
            require(seconds(span['task_processing_seconds']) == seconds(workload), 'Positive-case workload changed')
            require(seconds(span['between_task_gaps_seconds']) == seconds(gaps), 'Positive-case gaps changed')
        require(sorted(j['final_changed_blocks_from_initial']) == ['B2', 'B4', 'B6'] and s['final_changed_blocks_from_initial'] == [], 'Positive-case geometry example changed')
        jo, so = ({o['block']: o for o in r['active_occupancies']} for r in (j, s))
        require(sum(jo[b]['region'] != jo[b]['initial_region'] for b in ('B2', 'B4', 'B6')) == 2, 'Positive-case region changes changed')
        for run in (j, s):
            by_task = {t['task']: t for t in run['final_tasks']}
            by_block = {o['block']: o for o in run['active_occupancies']}
            require(seconds(by_block['B1']['end_seconds']) == 18089 and seconds(by_task['T6']['end_seconds']) == 18267, 'Release/completion example changed')
        jt, st = ({t['task']: t for t in r['final_tasks']} for r in (j, s))
        require([seconds(jt[t]['loaded_seconds']) for t in ('T1', 'T4')] == [95, 576], 'J loaded-movement example changed')
        require([seconds(st[t]['loaded_seconds']) for t in ('T1', 'T4')] == [549, 146], 'S loaded-movement example changed')
    for rep in negative['repeats']:
        for method, run in rep['methods'].items():
            require(run['final_changed_blocks_from_initial'] == [], 'Negative-case layout retention changed')
            require(sum(seconds(t['empty_seconds']) for t in run['final_tasks']) == 4674, 'Negative-case empty-movement sum changed')
            require(sum(seconds(t['loaded_seconds']) for t in run['final_tasks']) == 10804, 'Negative-case loaded-movement sum changed')
            require(sum(seconds(t['base_seconds']) for t in run['final_tasks']) == 54000, 'Negative-case lift sum changed')
            if method == 'J_VND':
                require(run['tracked_geometry_changes'] == 10 and run['accepted_improvement_count'] == 0, 'Negative-case J search summary changed')
                expected_gaps = (1020, 10218)
            elif rep['repeat'] in (1, 2):
                expected_gaps = (1995, 6387)
            else:
                expected_gaps = (0, 0)
            require(tuple(seconds(run['crane_task_spans'][c]['between_task_gaps_seconds']) for c in ('C1', 'C2')) == expected_gaps, 'Negative-case gap decomposition changed')
    output = {
        'status': 'pass', 'case_count': 2, 'pair_count': len(pairs), 'method_run_count': 2 * len(pairs),
        'inputs_sha256': {'terminal_case_evidence.json': digest(evidence_path), 'e10_state_outcomes.csv': digest(csv_path)},
        'states': states, 'pairs': pairs,
        'checked_manuscript_examples': ['Six-component comparison gate from stored content fingerprints', 'Cost vectors, outcomes and first differing level versus released CSV', 'Task duration components, completion sums, crane assignments and between-task gaps', 'New-occupancy starts and recorded carry-release times', 'Positive-case three changed placements, two region changes and opposite loaded-movement changes', 'Negative-case equal movement totals, geometry retention and changed timing gaps'],
        'limits': ['This self-contained check reads only the two public files identified above.', 'It does not replay the proprietary solver, recompute geometry or independently reconstruct initial plans.', 'Raw-trace and provenance hashes were checked against the retained seal during extraction; this public check verifies their format and uses exported fingerprints for the gate.', 'An independent initial task/motion/occupancy-time/Cost record does not exist.', 'Passing these arithmetic checks does not establish a causal explanation of either outcome.'],
    }
    output_dir = args.output_dir or directory / 'reproduced'
    output_dir.mkdir(parents=True, exist_ok=True)
    target = output_dir / 'terminal_case_checks.json'
    target.write_text(json.dumps(output, indent=2) + '\n')
    print(f'PASS: {len(pairs)} paired observations / {2*len(pairs)} terminal plans; wrote {target}')


if __name__ == '__main__':
    main()
