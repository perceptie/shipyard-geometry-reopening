"""Render the formal E32 controlled-budget experiment, never the sanity run.

Preparation (after formal analysis is complete):
  python3 generate_budget_effect.py --analysis-dir PATH
Portable reproduction:
  python3 generate_budget_effect.py [--input budget_effect_input.json]

The prepared input contains only anonymous objective histories and run metadata.
Each plotted line consists of actual strict-improvement events followed by a
horizontal incumbent segment to the measured phase stop. No curve is linearly
interpolated. Projection gating prevents second-objective values with different
first objectives being displayed as if they had the same ranking priority.
"""
from __future__ import annotations

import argparse
import collections
import csv
import hashlib
import html
import json
import math
from pathlib import Path
import shutil
import subprocess

HERE = Path(__file__).resolve().parent
FIELDS = ['projected_current_batch_completion', 'current_batch_makespan',
          'current_batch_total_completion_time', 'value']
STATES = ['b3-r006','b3-r071','b2-r051','b3-r031']
W = 160*72/25.4
H = 337
BLUE,ORANGE,DARK,MID,GRID = '#0072B2','#B54A00','#20242A','#444A51','#DDE2E6'


def text(x,y,value,size=9,anchor='start',weight='400',color=DARK):
    return (f'<text x="{x:.3f}" y="{y:.3f}" text-anchor="{anchor}" '
            f'font-family="Arial,Helvetica,sans-serif" font-size="{size}" '
            f'font-weight="{weight}" fill="{color}">{html.escape(str(value))}</text>')


def line(x1,y1,x2,y2,color=GRID,width=.5,dash=''):
    return f'<line x1="{x1}" y1="{y1}" x2="{x2}" y2="{y2}" stroke="{color}" stroke-width="{width}" stroke-dasharray="{dash}"/>'


def vector(row):
    return tuple(int(row[f]) for f in FIELDS)


def prepared_input(directory):
    names=['summary.json','search_phases.csv','strict_improvements.csv']
    paths={n:directory/n for n in names}
    summary=json.loads(paths['summary.json'].read_text())
    if not summary['checks_passed'] or summary['search_phases']!=48:
        raise ValueError('Only the validated 48-phase formal experiment is supported')
    with paths['search_phases.csv'].open() as f:
        phases=list(csv.DictReader(f))
    with paths['strict_improvements.csv'].open() as f:
        events=list(csv.DictReader(f))
    return {'version':'e32-budget-figure-input/1.0',
            'source_sha256':{n:hashlib.sha256(p.read_bytes()).hexdigest() for n,p in paths.items()},
            'summary':summary,'search_phases':phases,'strict_improvements':events}


def validate(data):
    summary=data['summary'];phases=data['search_phases'];events=data['strict_improvements']
    assert summary['checks_passed'] and len(phases)==48
    assert sorted(s['state'] for s in summary['states'])==sorted(STATES)
    phase_keys={(r['state'],str(r['repeat']),r['budget'],r['method']) for r in phases}
    assert len(phase_keys)==48
    assert {r['budget'] for r in phases}=={'remainder','full'}
    assert {r['method'] for r in phases}=={'J_VND','S_VND'}
    repeats=sorted({str(r['repeat']) for r in phases},key=int)
    assert repeats==['1','2','3']
    initial={r['state']:r for r in summary['states']}
    for row in phases:
        assert row['common_initial_sha256']==initial[row['state']]['common_initial_sha256']
        expected=12 if row['budget']=='full' else initial[row['state']]['remainder_microseconds']/1e6
        assert abs(float(row['budget_seconds'])-expected)<1e-9
        history=[e for e in events if (e['state'],str(e['repeat']),e['budget'],e['method']) == (row['state'],str(row['repeat']),row['budget'],row['method'])]
        current=vector(initial[row['state']]['initial_cost']);last_t=0
        for e in history:
            t=float(e['elapsed_seconds'])
            assert last_t<=t<=float(row['elapsed_seconds'])
            assert vector(e)<current
            current=vector(e);last_t=t
        assert current==vector(row)
    for comparison in summary['comparisons']:
        for pair in comparison['pairs']:
            pair_rows={r['method']:r for r in phases if
                       r['state']==comparison['state'] and
                       r['budget']==comparison['budget'] and
                       int(r['repeat'])==int(pair['repeat'])}
            j,s=vector(pair_rows['J_VND']),vector(pair_rows['S_VND'])
            expected='tie' if j==s else 'J' if j<s else 'S'
            assert pair['winner']==expected
    return initial,repeats


def phase_history(data,phase,initial,target):
    history=[(0.,vector(initial['initial_cost']))]
    history.extend((float(e['elapsed_seconds']),vector(e)) for e in data['strict_improvements']
                   if (e['state'],str(e['repeat']),e['budget'],e['method']) ==
                   (phase['state'],str(phase['repeat']),phase['budget'],phase['method']))
    retained=[(t,v) for t,v in history if v[0]==target]
    if retained:
        retained.append((float(phase['elapsed_seconds']),vector(phase)))
    return retained


def nice_ticks(top):
    raw=max(top,1e-6)/4
    power=10**math.floor(math.log10(raw))
    step=next(v*power for v in (1,2,2.5,5,10) if v*power>=raw)
    bound=math.ceil(top/step)*step
    return [i*step for i in range(int(round(bound/step))+1)]


def build(data):
    initial,repeats=validate(data)
    phases=[p for p in data['search_phases'] if p['state']=='b3-r006']
    target=min([vector(initial['b3-r006']['initial_cost'])[0]]+[vector(p)[0] for p in phases])
    histories={ (p['budget'],str(p['repeat']),p['method']):phase_history(data,p,initial['b3-r006'],target) for p in phases }
    all_vals=[v[1] for h in histories.values() for _,v in h]
    assert all_vals, 'No b3-r006 phase reached the selected common projection'
    base=min(all_vals)
    # This stated local window resolves the 233-s and 519-s ordering effects.
    # It omits earlier, higher second-objective values rather than connecting
    # them to an invented boundary crossing or collapsing a broken scale.
    y_max=1000
    ticks=[0,250,500,750,1000]
    out=[f'<svg xmlns="http://www.w3.org/2000/svg" width="160mm" height="{H*25.4/72:.4f}mm" viewBox="0 0 {W:.6f} {H}">',
         '<rect width="100%" height="100%" fill="white"/>',
         text(4,12,'b3-r006: actual improvement histories from identical complete initial plans',9.3,weight='700'),
         text(4,26,'Pool-completion excess above the best plotted value: local 0–1000 s; first objective matched.',8.5,color=MID)]
    coords=[('remainder',48,217,'(a) Construction-adjusted budget'),('full',280,441,'(b) Full 12-s improvement budget')]
    y0,y1=58,153
    yy=lambda val:y1-val/y_max*(y1-y0)
    dash_patterns=['','4 2','1 2']
    missing=[]
    for budget,x0,x1,title in coords:
        panel=[p for p in phases if p['budget']==budget]
        cap=float(panel[0]['budget_seconds'])
        xmax=max([cap]+[float(p['elapsed_seconds']) for p in panel])
        xx=lambda value:x0+value/max(xmax,1e-9)*(x1-x0)
        out.append(text(x0-40,43,title,9,weight='700'))
        for tick in ticks:
            y=yy(tick)
            out.append(line(x0,y,x1,y))
            out.append(text(x0-5,y+3,f'{tick:,.0f}',8.5,anchor='end'))
        for fraction in [0,.25,.5,.75,1]:
            t=xmax*fraction
            out.append(text(xx(t),168,f'{t:.1f}',8.5,anchor='middle'))
        out.append(line(x0,y0,x0,y1,MID,.6))
        out.append(line(xx(cap),y0,xx(cap),y1,MID,.6,'2 2'))
        for phase in panel:
            r=str(phase['repeat']);method=phase['method']
            history=[(t,v) for t,v in histories[(budget,r,method)] if (v[1]-base)/1e6<=y_max]
            if not history:
                missing.append(f'{budget}/{method}/{r}')
                continue
            points=[]
            previous=None
            for t,v in history:
                q=(v[1]-base)/1e6
                if previous is not None:
                    points.append((xx(t),yy(previous)))
                points.append((xx(t),yy(q)))
                previous=q
            color=BLUE if method=='J_VND' else ORANGE
            dash=dash_patterns[repeats.index(r)]
            coords_str=' '.join(f'{x:.3f},{y:.3f}' for x,y in points)
            out.append(f'<polyline points="{coords_str}" fill="none" stroke="{color}" stroke-width="1.15" stroke-dasharray="{dash}" opacity="0.87"/>')
            first_x,first_y=points[0];last_x,last_y=points[-1]
            out.append(f'<circle cx="{first_x}" cy="{first_y}" r="1.8" fill="white" stroke="{color}" stroke-width=".7"/>')
            out.append(f'<circle cx="{last_x}" cy="{last_y}" r="1.5" fill="{color}"/>')
        for method in ['J_VND','S_VND']:
            values={(int(p[FIELDS[1]])-base)/1e6 for p in panel if p['method']==method}
            if len(values)==1:
                value=next(iter(values))
                if 0<=value<=y_max:
                    color=BLUE if method=='J_VND' else ORANGE
                    label=f"{method[0]}: {value:,.3f} s"
                    out.append(text(x1-4,yy(value)-7,label,8.5,anchor='end',weight='700',color=color))
        out.append(text((x0+x1)/2,181,'Measured improvement time (s)',8.5,anchor='middle'))
        out.append(text(x0,194,f'Nominal allowance: {cap:.3f} s',8.5,color=MID))
    out.extend([line(6,207,22,207,BLUE,1.4),text(27,210,'J',8.5),line(49,207,65,207,ORANGE,1.4),text(70,210,'S',8.5)])
    for i,r in enumerate(repeats):
        x=110+i*70
        out.extend([line(x,207,x+20,207,DARK,1.1,dash_patterns[i]),text(x+24,210,f'Run {r}',8.5)])
    out.append(text(4,224,'Open markers: first event in the shown window, after reaching the common first objective.',8.5,color=MID))
    out.append(line(4,233,W-4,233,DARK,.7))
    out.extend([text(7,247,'State',8.5,weight='700'),text(91,247,'Role',8.5,weight='700'),
                text(172,247,'Remainder (s)',8.5,anchor='middle',weight='700'),
                text(282,247,'Remainder: r1 / r2 / r3',8.5,anchor='middle',weight='700'),
                text(400,247,'12 s: r1 / r2 / r3',8.5,anchor='middle',weight='700')])
    out.append(line(4,253,W-4,253,DARK,.5))
    for i,state in enumerate(STATES):
        y=267+i*16
        out.append(text(7,y,state,8.8))
        out.append(text(91,y,'Development' if i<2 else 'Holdout',8.5))
        out.append(text(172,y,f"{initial[state]['remainder_microseconds']/1e6:.3f}",8.5,anchor='middle'))
        for budget,cx in [('remainder',282),('full',400)]:
            pairs=next(x['pairs'] for x in data['summary']['comparisons'] if x['state']==state and x['budget']==budget)
            assert len(pairs)==3
            for j,pair in enumerate(pairs):
                win=pair['winner']
                label='=' if win=='tie' else win+str(FIELDS.index(pair['first_difference'])+1)
                out.append(text(cx+(j-1)*26,y,label,9,anchor='middle',weight='700',color=BLUE if win=='J' else ORANGE if win=='S' else MID))
                if j<2:
                    out.append(text(cx+(j-1)*26+13,y,'/',8.5,anchor='middle',color=MID))
    out.append(line(4,322,W-4,322,DARK,.5))
    out.append(text(4,335,'Winner + first differing objective tier (e.g., S3); = denotes a four-tier tie.',8.5,color=MID))
    out.append('</svg>')
    meta={'minimum_font_pt':8.5,'first_objective_us':target,'second_objective_reference_us':base,
          'projection_not_reached':missing,'formal_phases':len(data['search_phases']),
          'state':'b3-r006','second_objective_excess_window_seconds':[0,y_max],
          'curve_style':'actual strict-improvement events after matching first objective and entering stated second-objective window; steps to measured stop; no invented crossings or linear interpolation'}
    return '\n'.join(out)+'\n',meta


def main():
    p=argparse.ArgumentParser(description=__doc__)
    p.add_argument('--analysis-dir',type=Path)
    p.add_argument('--input',type=Path,default=HERE/'budget_effect_input.json')
    p.add_argument('--output-dir',type=Path,default=HERE)
    args=p.parse_args()
    data=prepared_input(args.analysis_dir) if args.analysis_dir else json.loads(args.input.read_text())
    svg,meta=build(data)
    args.output_dir.mkdir(parents=True,exist_ok=True)
    if args.analysis_dir:
        (args.output_dir/'budget_effect_input.json').write_text(json.dumps(data,indent=2)+'\n')
    path=args.output_dir/'fig11_budget_effect.svg';path.write_text(svg)
    rsvg=shutil.which('rsvg-convert')
    if not rsvg:raise SystemExit('SVG produced; PDF/PNG export requires rsvg-convert')
    subprocess.run([rsvg,'-f','pdf','-o',str(path.with_suffix('.pdf')),str(path)],check=True)
    subprocess.run([rsvg,'-f','png','-w','1814','-o',str(path.with_suffix('.png')),str(path)],check=True)
    (args.output_dir/'fig11_budget_effect_metadata.json').write_text(json.dumps(meta,indent=2)+'\n')
    print(json.dumps(meta,indent=2))


if __name__=='__main__':main()
