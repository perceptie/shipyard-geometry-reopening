"""Reproduce the mask-structure figure from de-identified retained records.

Usage: python3 generate_mask_structure.py [--input PATH] [--output-dir PATH]
Requires rsvg-convert for PDF/PNG export. SVG uses a 160-mm physical width and
point-sized viewBox coordinates, so its minimum 8.5-unit font is 8.5 pt.
Panel C intentionally uses categorical outcome rows, not a linear vertical
scale. Every mask has its own marker; horizontal offsets only separate ties.
"""
from __future__ import annotations

import argparse
import collections
import hashlib
import html
import json
from pathlib import Path
import shutil
import subprocess

HERE = Path(__file__).resolve().parent
W = 160 * 72 / 25.4
H = 438
BLUE = '#0072B2'
ORANGE = '#B54A00'
DARK = '#20242A'
MID = '#444A51'
GRID = '#DDE2E6'


def txt(x, y, value, size=9, anchor='start', weight='400', color=DARK):
    return (f'<text x="{x:.3f}" y="{y:.3f}" text-anchor="{anchor}" '
            f'font-family="Arial,Helvetica,sans-serif" font-size="{size}" '
            f'font-weight="{weight}" fill="{color}">{html.escape(str(value))}</text>')


def line(x1, y1, x2, y2, color=GRID, width=.5, dash=''):
    return (f'<line x1="{x1}" y1="{y1}" x2="{x2}" y2="{y2}" '
            f'stroke="{color}" stroke-width="{width}" stroke-dasharray="{dash}"/>')


def mark(x, y, reopened, radius=2.7, best=False):
    color = ORANGE if reopened else BLUE
    edge = DARK if best else color
    sw = 1.2 if best else .65
    if reopened:
        return (f'<rect x="{x-radius}" y="{y-radius}" width="{radius*2}" '
                f'height="{radius*2}" fill="white" stroke="{edge}" stroke-width="{sw}"/>')
    return (f'<circle cx="{x}" cy="{y}" r="{radius}" fill="{color}" '
            f'stroke="{edge}" stroke-width="{sw}"/>')


def delta(row, record):
    return (record['objective_us'][1] - row['endpoint']['objective_us'][1]) / 1e6


def validate(data):
    rows = data['representatives']
    assert [r['state'] for r in rows] == ['b2-r096', 'b3-r006', 'b3-r071']
    for row in rows:
        n = row['mutable_blocks']
        assert len(row['mask_results']) == 2 ** n
        assert sorted(r['mask'] for r in row['mask_results']) == list(range(2 ** n))
        assert all(r['success'] for r in row['mask_results']), 'Failure requires separate encoding'
        assert all(r['objective_us'][0] == row['endpoint']['objective_us'][0] for r in row['mask_results'])
        best = min(tuple(r['objective_us']) for r in row['mask_results'])
        assert tuple(row['best_objective_us']) == best
        winners = sorted(r['mask'] for r in row['mask_results'] if tuple(r['objective_us']) == best)
        assert winners == sorted(row['best_masks'])
        assert len(winners) == row['best_count']
    assert rows[0]['best_masks'] == [5]
    assert rows[1]['best_masks'] == [3]
    assert len(rows[2]['best_masks']) == 8
    assert all(m & 2 and m & 32 and not m & 8 for m in rows[2]['best_masks'])
    return rows


def build(data):
    rows = validate(data)
    out = [f'<svg xmlns="http://www.w3.org/2000/svg" width="160mm" height="{H*25.4/72:.4f}mm" viewBox="0 0 {W:.6f} {H}">',
           '<rect width="100%" height="100%" fill="white"/>',
           txt(4, 11, 'Δ current-batch pool completion (s), relative to the same-candidate endpoint', 9.2),
           txt(4, 24, 'First objective unchanged within each panel; lower values are better.', 8.5, color=MID)]
    configs = [
        dict(x0=40,x1=205,titlex=4,lo=-25,hi=5,ticks=[0,-10,-20],key=1,
             title='(a) b2-r096 · D02-C006',besttext='Best: open u1, u3; retain u2',
             outcome='Another candidate already improves the six-candidate best.'),
        dict(x0=281,x1=441,titlex=236,lo=-15500,hi=2000,ticks=[0,-5000,-10000,-15000],key=2,
             title='(b) b3-r006 · D03-C001',besttext='Best: open u1, u2; retain u3',
             outcome='Improvement survives the wider saved candidate pool.'),
    ]
    for row,cfg in zip(rows[:2], configs):
        x0,x1 = cfg['x0'],cfg['x1']
        y0,y1 = 56,153
        yy=lambda v:y1-(v-cfg['lo'])/(cfg['hi']-cfg['lo'])*(y1-y0)
        out.append(txt(cfg['titlex'],43,cfg['title'],9.5,weight='700'))
        for tick in cfg['ticks']:
            y=yy(tick)
            out.append(line(x0,y,x1,y,DARK if tick==0 else GRID,.7 if tick==0 else .5,'3 2' if tick==0 else ''))
            out.append(txt(x0-5,y+3,f'{tick:,}',8.5,anchor='end'))
        out.append(line(x0,y0,x0,y1,MID,.6))
        for i,record in enumerate(row['mask_results']):
            x=x0+i*(x1-x0)/7
            v=delta(row,record)
            best=record['mask'] in row['best_masks']
            out.append(mark(x,yy(v), bool(record['mask'] & (1<<cfg['key'])),best=best))
            out.append(txt(x,168,''.join(str(int(bool(record['mask']&(1<<j)))) for j in range(3)),8.5,anchor='middle'))
            if best:
                label=f'{v:,.3f}'.rstrip('0').rstrip('.')
                out.append(txt(x,yy(v)-8,label,8.5,anchor='middle',weight='700',color=BLUE))
            elif v>0:
                out.append(txt(x-2,yy(v)-8,f'+{v:,.3f}',8.5,anchor='end',color=ORANGE))
        out.append(txt((x0+x1)/2,182,'Mask (u1u2u3); 1 = eligible',8.5,anchor='middle'))
        out.append(txt(cfg['titlex'],197,cfg['besttext'],8.8,weight='700'))
        if row['state']=='b2-r096':
            difference=(row['best_objective_us'][1]-row['case_comparison']['six_candidate_endpoint_best']['objective_us'][1])/1e6
            out.append(txt(cfg['titlex'],211,f'Six-candidate endpoint is {difference:,.0f} s earlier.',8.5,color=MID))
        else:
            difference=-row['case_comparison']['mask_delta_vs_all_simple_us'][1]/1e6
            out.append(txt(cfg['titlex'],211,f'Wider-pool improvement: {difference:,.3f} s.',8.5,color=MID))
    out.extend([line(4,223,W-4,223),txt(4,240,'(c) b3-r071 · D04-C006: all 64 masks',9.5,weight='700'),
                txt(4,254,'Four observed outcome rows (equal spacing, not a linear vertical scale).',8.5,color=MID)])
    row=rows[2]
    levels=[7362.,6998.,0.,-245.]
    ypos={v:275+i*24 for i,v in enumerate(levels)}
    x0,x1=84,436
    for v in levels:
        y=ypos[v]
        out.append(line(x0-21,y,x1+12,y,DARK if v==0 else GRID,.7 if v==0 else .5,'3 2' if v==0 else ''))
        out.append(txt(54,y+3,f'{v:+,.0f}' if v else '0',8.5,anchor='end',weight='700' if v==-245 else '400'))
    bins=collections.defaultdict(list)
    for rec in row['mask_results']:
        bins[(rec['open_count'],delta(row,rec))].append(rec)
    for (count,v),items in sorted(bins.items()):
        cx=x0+(x1-x0)*count/6
        items=sorted(items,key=lambda z:z['mask'])
        n=len(items)
        for idx,rec in enumerate(items):
            if n<=7:
                dx=(idx-(n-1)/2)*6.0
                dy=0
            else:
                chunk=0 if idx<7 else 1
                row_items=7 if chunk==0 else n-7
                pos=idx if chunk==0 else idx-7
                dx=(pos-(row_items-1)/2)*6.0
                dy=-3.5 if chunk==0 else 3.5
            out.append(mark(cx+dx,ypos[v]+dy,bool(rec['mask']&8),radius=2.25,best=rec['mask'] in row['best_masks']))
    for count in range(7):
        out.append(txt(x0+(x1-x0)*count/6,367,count,8.5,anchor='middle'))
    out.extend([txt((x0+x1)/2,381,'Number of blocks eligible for reconstruction, |R|',9,anchor='middle'),
                txt(4,398,'Eight best masks: open u2, u6; retain u4; u1, u3, u5 may vary.',9,weight='700'),
                txt(4,411,'245 s better in the six-candidate set; a wider-pool endpoint is better.',8.5,color=MID),
                mark(7,430,False),txt(15,433,'Key block retained: u2 in (a), u3 in (b), u4 in (c)',8.5),
                mark(292,430,True),txt(301,433,'Key block eligible for reconstruction',8.5),'</svg>'])
    return '\n'.join(out)+'\n'


def main():
    parser=argparse.ArgumentParser(description=__doc__)
    parser.add_argument('--input',type=Path,default=HERE/'mask_structure_input.json')
    parser.add_argument('--output-dir',type=Path,default=HERE)
    args=parser.parse_args()
    data=json.loads(args.input.read_text(encoding='utf-8'))
    svg=build(data)
    args.output_dir.mkdir(parents=True,exist_ok=True)
    target=args.output_dir/'fig10_mask_structure.svg'
    target.write_text(svg,encoding='utf-8')
    rsvg=shutil.which('rsvg-convert')
    if not rsvg:
        raise SystemExit('SVG created; rsvg-convert is required for PDF and PNG export')
    subprocess.run([rsvg,'-f','pdf','-o',str(target.with_suffix('.pdf')),str(target)],check=True)
    subprocess.run([rsvg,'-f','png','-w','1814','-o',str(target.with_suffix('.png')),str(target)],check=True)
    print(json.dumps({'svg':target.name,'input_sha256':hashlib.sha256(args.input.read_bytes()).hexdigest(),'source_sha256':data['source_sha256'],'mask_markers':80,'minimum_font_pt':8.5,'width_mm':160,'height_mm':H*25.4/72},indent=2))


if __name__=='__main__':
    main()
