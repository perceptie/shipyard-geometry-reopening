"""Reproduce the E11 figure from its de-identified, versioned input.

Usage: python3 generate_e11_mechanism.py [--input PATH] [--output-dir PATH]
The default input and output are beside this script.  Panel A shows all three
repeat counts, their observed range and median; panel B shows fixed-sequence
decoder-success counts.  The physical width is the template's 160-mm text width.
"""
from __future__ import annotations

import argparse
import hashlib
import html
import json
import shutil
import statistics
import subprocess
from pathlib import Path

FIG_DIR = Path(__file__).resolve().parent
BLUE = "#0072B2"
ORANGE = "#B54A00"
GREY = "#9AA1A8"
DARK = "#20242A"
MID = "#444A51"
GRID = "#E5E7EB"
STATES = ["b2-r096", "b3-r006", "b3-r071", "b2-r056", "b3-r121"]


def load_rows(path: Path) -> list[dict]:
    data = json.loads(path.read_text(encoding="utf-8"))
    rows = data["states"]
    if [row["state"] for row in rows] != STATES:
        raise ValueError("Unexpected state order")
    for row in rows:
        for policy in ("J", "S"):
            counts = row[f"{policy}_repeat_executions"]
            if len(counts) != 3 or any(type(n) is not int or n < 0 for n in counts):
                raise ValueError(f"Invalid repeat counts for {row['state']} / {policy}")
            if statistics.median(counts) != row[f"{policy}_median_executions"]:
                raise ValueError(f"Median disagrees with repeats for {row['state']} / {policy}")
        if len(row["repeat_outcomes"]) != 3:
            raise ValueError("Each state must retain all three outcomes")
        if row["neither"] != 0:
            raise ValueError("This figure's probe set has no neither-success records")
        if sum(row[k] for k in ("both", "J_only", "S_only")) != row["sequence_records"]:
            raise ValueError("Probe-record categories do not close")
    totals = {k: sum(row[k] for row in rows) for k in ("both", "J_only", "S_only")}
    if totals != {"both": 250, "J_only": 8, "S_only": 24}:
        raise ValueError(f"Unexpected probe totals: {totals}")
    if sum(row["sequence_records"] for row in rows) != 282:
        raise ValueError("Expected 282 probe records")
    if sum(sum(row["J_repeat_executions"]) for row in rows) != 2404:
        raise ValueError("J repeat total disagrees with the recorded diagnostics")
    if sum(sum(row["S_repeat_executions"]) for row in rows) != 2986:
        raise ValueError("S repeat total disagrees with the recorded diagnostics")
    return rows


def text(x, y, value, *, size=24, fill=DARK, anchor="start", weight="400"):
    return (f'<text x="{x:.2f}" y="{y:.2f}" text-anchor="{anchor}" '
            f'style="font-family:Arial,Helvetica,sans-serif;font-size:{size}px;'
            f'font-weight:{weight};fill:{fill}">{html.escape(str(value))}</text>')


def line(x1, y1, x2, y2, *, stroke=GRID, width=1):
    return (f'<line x1="{x1:.2f}" y1="{y1:.2f}" x2="{x2:.2f}" y2="{y2:.2f}" '
            f'stroke="{stroke}" stroke-width="{width}"/>')


def rect(x, y, width, height, *, fill="none", stroke="none", sw=1):
    return (f'<rect x="{x:.2f}" y="{y:.2f}" width="{width:.2f}" height="{height:.2f}" '
            f'fill="{fill}" stroke="{stroke}" stroke-width="{sw}"/>')


def marker(x, y, policy, *, radius, fill, stroke, sw=1.5):
    if policy == "J":
        return (f'<circle cx="{x:.2f}" cy="{y:.2f}" r="{radius:.2f}" '
                f'fill="{fill}" stroke="{stroke}" stroke-width="{sw}"/>')
    return rect(x-radius, y-radius, radius*2, radius*2, fill=fill, stroke=stroke, sw=sw)


def draw_svg(rows: list[dict]) -> str:
    # 24 SVG units at 160 mm / 1280 units render as 8.50 PDF points.
    # Use physical dimensions, so the LaTeX text-width placement is 1:1.
    W, H = 1280, 700
    left, right = 145, 575
    bleft, bright = 715, 1075
    top, bottom = 118, 537
    pieces = [f'<svg xmlns="http://www.w3.org/2000/svg" width="160mm" height="87.5mm" viewBox="0 0 {W} {H}">',
              '<title>E11 candidate evaluations and common-sequence decoding</title>',
              '<desc>Panel a shows three actual repeat counts and the median for each policy. Panel b shows Both, J-only and S-only decoder-success counts for the same five selected states.</desc>',
              rect(0, 0, W, H, fill="white")]
    pieces.append(text(20, 42, "(a) Candidate evaluations", size=29, weight="700"))
    pieces.append(text(655, 42, "(b) Common-sequence decoding", size=29, weight="700"))
    pieces.append(marker(left, 80, "J", radius=8, fill=BLUE, stroke=BLUE))
    pieces.append(text(left+18, 88, "J", fill=BLUE, weight="700"))
    pieces.append(marker(left+82, 80, "S", radius=8, fill=ORANGE, stroke=ORANGE))
    pieces.append(text(left+101, 88, "S", fill=ORANGE, weight="700"))
    pieces.append(text(left+167, 88, "Separate 12-s phases", fill=MID))
    for label, colour, x in (("Both", GREY, bleft), ("J only", BLUE, bleft+127), ("S only", ORANGE, bleft+274)):
        pieces.append(rect(x, 66, 19, 19, fill=colour))
        pieces.append(text(x+27, 85, label, fill=MID))
    for tick in range(0, 501, 100):
        x = left + tick/500*(right-left)
        pieces.append(line(x, top, x, bottom))
        pieces.append(text(x, bottom+42, tick, anchor="middle", fill=MID))
    for tick in (0, 40, 80, 120):
        x = bleft + tick/130*(bright-bleft)
        pieces.append(line(x, top, x, bottom))
        pieces.append(text(x, bottom+42, tick, anchor="middle", fill=MID))
    pieces.append(text(1100, 122, "Both / J / S", fill=MID))
    for idx, row in enumerate(rows):
        y = 155+idx*88
        pieces.append(text(left-16, y+8, row["state"], anchor="end"))
        # Put repeats on distinct, small offsets so identical counts remain visible.
        for policy, colour, offset in (("J", BLUE, -18), ("S", ORANGE, 18)):
            counts = row[f"{policy}_repeat_executions"]
            median = row[f"{policy}_median_executions"]
            xmap = lambda v: left+v/500*(right-left)
            yy = y+offset
            pieces.append(line(xmap(min(counts)), yy, xmap(max(counts)), yy, stroke=colour, width=2.5))
            for n, jitter in zip(counts, (-12, 0, 12)):
                pieces.append(marker(xmap(n), yy+jitter, policy, radius=5.0,
                                     fill="white", stroke=colour, sw=1.5))
            pieces.append(marker(xmap(median), yy, policy, radius=8.5,
                                 fill=colour, stroke="white", sw=1.5))
            pieces.append(text(xmap(median)+15, yy+8, median, fill=colour, weight="700"))
        if row["state"] in ("b3-r006", "b3-r071"):
            lead = "J more" if row["state"] == "b3-r006" else "S more"
            pieces.append(text(left+170, y+47, f"{lead}; S better (3/3)", fill=MID))
        start = bleft
        for key, colour in (("both", GREY), ("J_only", BLUE), ("S_only", ORANGE)):
            w = row[key]/130*(bright-bleft)
            if w:
                pieces.append(rect(start, y-16, w, 32, fill=colour, stroke="white", sw=1))
            start += w
        pieces.append(text(1100, y+8, f"{row['both']} / {row['J_only']} / {row['S_only']}", fill=MID))
    pieces.append(text((left+right)/2, 617, "Executed decodes (count)", anchor="middle"))
    pieces.append(text((bleft+bright)/2+45, 617, "Sequence records (count)", anchor="middle"))
    pieces.append(text(left, 662, "Hollow: repeats   Filled: median", fill=MID))
    pieces.append(text(bleft, 662, "Totals: 250 / 8 / 24", fill=MID))
    pieces.append('</svg>')
    return "\n".join(pieces)


def main() -> None:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--input", type=Path, default=FIG_DIR/"e11_mechanism_input.json")
    parser.add_argument("--output-dir", type=Path, default=FIG_DIR)
    parser.add_argument("--renderer", default="rsvg-convert")
    args = parser.parse_args()
    rows = load_rows(args.input)
    renderer = shutil.which(args.renderer)
    if not renderer:
        parser.error("rsvg-convert is required to export the vector PDF; SVG input remains editable")
    args.output_dir.mkdir(parents=True, exist_ok=True)
    svg = args.output_dir/"fig9_e11_mechanism.svg"
    pdf = args.output_dir/"fig9_e11_mechanism.pdf"
    svg.write_text(draw_svg(rows), encoding="utf-8")
    subprocess.run([renderer, "--format", "pdf", "--output", str(pdf), str(svg)], check=True)
    print(f"input_sha256={hashlib.sha256(args.input.read_bytes()).hexdigest()}")
    print("validated: 15 diagnostic pairs; J/S evaluations 2404/2986; probe counts 250/8/24")
    print(f"wrote {svg.name} and {pdf.name} at 160 mm width; minimum nominal label size 8.50 pt")


if __name__ == "__main__":
    main()
