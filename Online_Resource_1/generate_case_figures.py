"""Editable vector illustrations of retained terminal plans and physical rules.

Fig. 7 reads only the released case-local record. Region boxes represent
membership, not coordinates or dimensions. Fig. 8 is a model illustration.
The public draw functions can also be imported by the supplement reproducer.
"""

from __future__ import annotations

import argparse
import json
from pathlib import Path

import matplotlib as mpl
import matplotlib.pyplot as plt
from matplotlib.patches import FancyArrowPatch, Rectangle


HERE = Path(__file__).resolve().parent
DEFAULT_DATA = (HERE / "terminal_case_evidence.json" if (HERE / "terminal_case_evidence.json").is_file()
                else HERE.parent / "supplement/terminal_case_evidence.json")
BLUE = "#0072B2"
ORANGE = "#B54A00"
GRAY = "#666666"
INK = "#20242A"
LINE = "#747B84"
PALE = "#F6F7F8"


def configure() -> None:
    mpl.rcParams.update({
        "font.family": "sans-serif",
        "font.sans-serif": ["Arial", "Helvetica", "DejaVu Sans"],
        "font.size": 9.5,
        "axes.labelsize": 9.5,
        "xtick.labelsize": 9,
        "ytick.labelsize": 9,
        "legend.fontsize": 9,
        "text.color": INK,
        "axes.labelcolor": INK,
        "axes.edgecolor": GRAY,
        "axes.spines.top": False,
        "axes.spines.right": False,
        "axes.linewidth": 0.65,
        "hatch.linewidth": 0.6,
        "xtick.major.width": 0.65,
        "ytick.major.width": 0.65,
        "pdf.fonttype": 42,
        "ps.fonttype": 42,
        "svg.fonttype": "none",
        "svg.hashsalt": "p3-case-illustrations-2026-10-02",
        "savefig.bbox": "tight",
        "savefig.pad_inches": 0.04,
    })


def _arrow(ax, start, end, *, color=LINE, style="-|>", width=0.9,
           connectionstyle="arc3,rad=0", mutation=9):
    ax.add_patch(FancyArrowPatch(start, end, arrowstyle=style,
                                color=color, linewidth=width,
                                connectionstyle=connectionstyle,
                                mutation_scale=mutation, shrinkA=0, shrinkB=2))


def _title(ax, text):
    ax.set_title(text, loc="left", pad=10, fontsize=10, fontweight="bold")


def _record(case: dict, repeat: int, method: str) -> dict:
    return next(r for r in case["repeats"] if r["repeat"] == repeat)["methods"][method]


def _occupancies(record: dict) -> dict:
    return {row["block"]: row for row in record["active_occupancies"]}


def _number(value: float, decimals: int = 0) -> str:
    return f"{value:,.{decimals}f}"


def _region_box(ax, x: float, y: float, w: float, h: float,
                label: str, blocks: list[str], *, color=LINE):
    ax.add_patch(Rectangle((x, y), w, h, facecolor=PALE,
                           edgecolor=color, linewidth=0.8))
    ax.text(x + 0.07, y + h - 0.10, label, fontsize=9, va="top",
            fontweight="bold", color=color)
    ax.text(x + w/2, y + 0.27*h, ", ".join(blocks),
            fontsize=9.5, ha="center", va="center")


def _positive_membership(ax, case: dict):
    j, s = _occupancies(_record(case, 1, "J_VND")), _occupancies(_record(case, 1, "S_VND"))
    changed = [block for block in j if not j[block]["geometry_equals_other_method"]]
    if set(changed) != {"B2", "B4", "B6"}:
        raise ValueError("Positive-case changed-block set differs from retained evidence")
    ax.set(xlim=(0, 2.2), ylim=(0, 3.25))
    ax.axis("off")
    ax.text(0, 3.03, "S-VND / initial", color=ORANGE, fontweight="bold", fontsize=9.5)
    for i, region in enumerate(("R1", "R4")):
        _region_box(ax, 1.12*i, 2.24, 1.02, 0.63, region,
                    sorted(b for b in changed if s[b]["region"] == region), color=ORANGE)
    ax.text(0, 1.55, "J-VND / final", color=BLUE, fontweight="bold", fontsize=9.5)
    for i, region in enumerate(("R1", "R4")):
        _region_box(ax, 1.12*i, 0.79, 1.02, 0.57, region,
                    sorted(b for b in changed if j[b]["region"] == region), color=BLUE)
    _arrow(ax, (0.47, 2.14), (1.62, 1.76), color=BLUE)
    _arrow(ax, (1.63, 2.14), (0.48, 1.76), color=BLUE)
    task_by_block = {row["block"]: row["task"] for row in _record(case, 1, "J_VND")["final_tasks"]
                     if row["block"] in changed}
    if task_by_block != {"B2": "T1", "B4": "T4", "B6": "T3"}:
        raise ValueError("Changed-block/task mapping differs from retained evidence")
    ax.text(0, 0.54, "B2 (T1): R1 → R4\nB4 (T4): R4 → R1\nB6 (T3): changes within R1",
            fontsize=9.3, linespacing=1.35, va="top")
    _title(ax, "(a) Changed region assignments")


def _negative_membership(ax, case: dict):
    j = _occupancies(_record(case, 1, "J_VND"))
    for r in case["repeats"]:
        for method in ("J_VND", "S_VND"):
            if any(not row["geometry_equals_initial"] for row in r["methods"][method]["active_occupancies"]):
                raise ValueError("Negative-case final geometry is expected to remain unchanged")
    ax.set(xlim=(0, 2.2), ylim=(0, 3.0))
    ax.axis("off")
    ax.text(0, 2.73, "J-VND = S-VND = initial", fontsize=9.3, fontweight="bold")
    for y, region in ((1.71, "R2"), (0.85, "R4")):
        _region_box(ax, 0, y, 2.14, 0.67, region,
                    sorted(b for b in j if j[b]["region"] == region))
    ax.text(0, 0.52, "B1 is already committed.\nFinal positions and orientations\nmatch in all three repeats.",
            fontsize=9.2, linespacing=1.3, va="top")
    _title(ax, "(c) Unchanged region assignments")


def _timeline(ax, rows: list[tuple[str, dict, str, bool]], xmax: float):
    """Task intervals are proportional to their exact retained times."""
    barheight = 0.60
    for y, (label, record, crane, joint) in enumerate(reversed(rows)):
        color = BLUE if joint else ORANGE
        for task in record["final_tasks"]:
            if crane not in task["cranes"]:
                continue
            start, end = task["start_seconds"]/1000, task["end_seconds"]/1000
            ax.add_patch(Rectangle((start, y - barheight/2), end-start, barheight,
                                   facecolor=color if joint else "white", edgecolor=color,
                                   linewidth=0.85))
            ax.text((start+end)/2, y, task["task"], fontsize=9,
                    color="white" if joint else ORANGE, ha="center", va="center")
        for motion in record["non_task_motions"]:
            if motion["crane"] == crane and motion["start_seconds"] >= 0:
                ax.plot([motion["start_seconds"]/1000, motion["end_seconds"]/1000],
                        [y - 0.34, y - 0.34], color=GRAY, linewidth=2.1, solid_capstyle="butt")
        ax.text(-0.9, y, label, ha="right", va="center", fontsize=9)
    ax.set_xlim(0, xmax)
    ax.set_ylim(-0.65, len(rows)-0.25)
    ax.set_yticks([])
    ax.set_xlabel("Model time after the decision epoch (10³ s)", labelpad=5)
    ax.set_xticks(list(range(0, int(xmax)+1, 10)))
    ax.set_axisbelow(True)
    ax.grid(axis="x", color="#E5E7EB", linewidth=0.6)
    ax.spines["left"].set_visible(False)


def _positive_details(motion_ax, endpoint_ax, j: dict, s: dict):
    """Two explicitly local windows preserve the full timeline's scale."""
    motions = [m for m in s["non_task_motions"] if m["crane"] == "C2" and m["start_seconds"] >= 0]
    if len(motions) != 1:
        raise ValueError("Positive-case C2 movement detail requires one retained motion")
    motion = motions[0]
    start, end = motion["start_seconds"]/1000, motion["end_seconds"]/1000
    motion_ax.set_xlim(start-0.35, start+1.00)
    for task in s["final_tasks"]:
        if "C2" not in task["cranes"]:
            continue
        task_start, task_end = task["start_seconds"]/1000, task["end_seconds"]/1000
        motion_ax.add_patch(Rectangle((task_start, -0.19), task_end-task_start, 0.38,
                                     facecolor="white", edgecolor=ORANGE, linewidth=0.85))
        visible_start = max(task_start, start-0.35)
        visible_end = min(task_end, start+1.00)
        if visible_end > visible_start:
            motion_ax.text((visible_start+visible_end)/2, 0, task["task"], ha="center",
                           va="center", color=ORANGE, fontsize=8.5)
    motion_ax.plot([start, end], [-0.35, -0.35], color=GRAY, linewidth=2.1, solid_capstyle="butt")
    motion_ax.annotate(f"{_number(motion['duration_seconds'])} s",
                       xy=((start+end)/2, -0.35), xytext=(start+0.50, 0.54),
                       arrowprops={"arrowstyle": "->", "color": GRAY, "linewidth": 0.75},
                       ha="center", va="center", fontsize=9)
    motion_ax.set_ylim(-0.55, 0.87)
    motion_ax.set_xticks([41.2, 41.8, 42.4])
    motion_ax.set_title("S C2 motion detail", loc="left", pad=4, fontsize=9, fontweight="bold")

    jend, send = [record["cost_relative_seconds"]["current_batch_makespan"]/1000 for record in (j, s)]
    endpoint_ax.set_xlim(jend-0.26, send+0.15)
    for y, record, joint in ((1, j, True), (0, s, False)):
        task = next(task for task in record["final_tasks"] if task["task"] == "T3")
        task_start, task_end = task["start_seconds"]/1000, task["end_seconds"]/1000
        color = BLUE if joint else ORANGE
        endpoint_ax.add_patch(Rectangle((task_start, y-0.20), task_end-task_start, 0.40,
                                       facecolor=color if joint else "white", edgecolor=color,
                                       linewidth=0.85))
        endpoint_ax.plot(task_end, y, marker="|", markersize=10, color=color, markeredgewidth=1.0)
    endpoint_ax.plot([jend, send], [1.57, 1.57], color=INK, linewidth=0.75)
    for endpoint in (jend, send):
        endpoint_ax.plot([endpoint, endpoint], [1.40, 1.74], color=INK, linewidth=0.75)
    endpoint_ax.text((jend+send)/2, 1.89, f"Δ = {(send-jend)*1000:.3f} s",
                     fontsize=9, ha="center", va="bottom")
    endpoint_ax.set_ylim(-0.40, 2.28)
    endpoint_ax.set_yticks([0, 1], ["S", "J"])
    endpoint_ax.set_xticks([55.4, 55.6, 55.8])
    endpoint_ax.set_title("Completion endpoints", loc="left", pad=4, fontsize=9, fontweight="bold")
    for ax in (motion_ax, endpoint_ax):
        ax.set_xlabel("Model time (10³ s)", fontsize=8.5, labelpad=3)
        ax.tick_params(axis="both", labelsize=8.3, length=2)
        ax.spines["left"].set_visible(False)
        ax.grid(axis="x", color="#E5E7EB", linewidth=0.5)
        ax.set_axisbelow(True)
    motion_ax.set_yticks([])


def draw_terminal_cases(data: dict) -> plt.Figure:
    cases = {case["state"]: case for case in data["cases"]}
    positive, negative = cases["b3-r006"], cases["b3-r071"]
    for case in (positive, negative):
        for row in case["repeats"]:
            if not all(row[k] for k in ("initial_sequence_signature_equal", "initial_geometry_signature_equal",
                                        "accepted_mode_equal", "accepted_budget_equal")):
                raise ValueError("Case figure requires eligible retained pairs")
    pj, ps = _record(positive, 1, "J_VND"), _record(positive, 1, "S_VND")
    nj, ns1, ns3 = (_record(negative, 1, "J_VND"), _record(negative, 1, "S_VND"),
                   _record(negative, 3, "S_VND"))
    # Stable curves are shown once, but every retained repetition is checked.
    for repeat in (2, 3):
        for method in ("J_VND", "S_VND"):
            if _record(positive, repeat, method)["final_tasks"] != _record(positive, 1, method)["final_tasks"]:
                raise ValueError("Positive-case repetitions differ")
        if _record(negative, repeat, "J_VND")["final_tasks"] != nj["final_tasks"]:
            raise ValueError("Negative J-VND repetitions differ")
    if _record(negative, 2, "S_VND")["final_tasks"] != ns1["final_tasks"]:
        raise ValueError("Negative S-VND repetitions 1 and 2 differ")

    fig = plt.figure(figsize=(6.85, 6.30))
    gs = fig.add_gridspec(3, 2, width_ratios=(1.45, 3.6), height_ratios=(1, 0.70, 1.35),
                          left=0.01, right=0.99, top=0.915, bottom=0.095,
                          wspace=0.30, hspace=0.64)
    pa, pb = fig.add_subplot(gs[0:2, 0]), fig.add_subplot(gs[0, 1])
    pc, pd = fig.add_subplot(gs[2, 0]), fig.add_subplot(gs[2, 1])
    details = gs[1, 1].subgridspec(1, 2, wspace=0.44)
    motion_ax, endpoint_ax = [fig.add_subplot(details[0, column]) for column in (0, 1)]
    _positive_membership(pa, positive)
    _negative_membership(pc, negative)
    _timeline(pb, [("J C1", pj, "C1", True), ("J C2", pj, "C2", True),
                   ("S C1", ps, "C1", False), ("S C2", ps, "C2", False)], 60)
    _positive_details(motion_ax, endpoint_ax, pj, ps)
    _timeline(pd, [("J C1", nj, "C1", True), ("J C2", nj, "C2", True),
                   ("S(1,2) C1", ns1, "C1", False), ("S(1,2) C2", ns1, "C2", False),
                   ("S(3) C1", ns3, "C1", False), ("S(3) C2", ns3, "C2", False)], 66)
    pb.set_title("(b) J-favouring E10 case b3-r006", loc="left", pad=24, fontsize=10, fontweight="bold")
    pd.set_title("(d) S-favouring E10 case b3-r071", loc="left", pad=24, fontsize=10, fontweight="bold")
    jp, sp = pj["cost_relative_seconds"]["current_batch_makespan"], ps["cost_relative_seconds"]["current_batch_makespan"]
    jn, sn1, sn3 = [record["cost_relative_seconds"]["current_batch_makespan"] for record in (nj, ns1, ns3)]
    pb.text(0, 1.025, f"J: {_number(jp)} s   S: {_number(sp, 3)} s   (all repeats)",
            transform=pb.transAxes, fontsize=9.1, va="bottom")
    pd.text(0, 1.025, f"J: {_number(jn)} s   S(1,2): {_number(sn1)} s   S(3): {_number(sn3)} s",
            transform=pd.transAxes, fontsize=9.1, va="bottom")
    return fig


def draw_physical_constraints() -> plt.Figure:
    fig = plt.figure(figsize=(6.85, 3.55))
    left = fig.add_axes([0.01, 0.09, 0.47, 0.83])
    right = fig.add_axes([0.54, 0.09, 0.45, 0.83])
    for ax in (left, right):
        ax.set(xlim=(0, 3.15), ylim=(0, 3.15))
        ax.axis("off")
    _title(left, "(a) Geometry and shared rail")
    _title(right, "(b) Persistent yard occupancy")

    # Abstract X-order shared by the cranes; positions are illustration only.
    left.plot([0.13, 3.0], [2.66, 2.66], color=GRAY, linewidth=1.8)
    left.plot([0.13, 3.0], [2.76, 2.76], color=GRAY, linewidth=0.8)
    for x, label in ((0.46, "C1"), (1.5, "C2"), (2.53, "C3")):
        left.add_patch(Rectangle((x-0.15, 2.59), 0.3, 0.25, facecolor="white", edgecolor=GRAY, linewidth=1))
        left.text(x, 2.99, label, fontsize=9.5, ha="center")
    left.text(1.54, 2.36, "Fixed left-to-right order: C1 → C2 → C3", fontsize=9.3, ha="center")
    left.add_patch(Rectangle((0.18, 0.61), 2.75, 1.46, facecolor=PALE, edgecolor=LINE, linewidth=0.9))
    left.text(0.28, 1.97, "Yard region", fontsize=9.3, va="top", fontweight="bold")
    left.add_patch(Rectangle((0.4, 0.83), 0.82, 0.63, facecolor="#E5E7EB", edgecolor=GRAY,
                             linewidth=1, hatch="///"))
    left.text(0.81, 1.145, "Locked", fontsize=9.3, ha="center", va="center")
    left.add_patch(Rectangle((1.52, 0.92), 1.08, 0.44, facecolor="white", edgecolor=BLUE, linewidth=1.3))
    left.text(2.06, 1.14, "Mutable", fontsize=9.3, color=BLUE, ha="center", va="center")
    left.add_patch(Rectangle((1.84, 0.72), 0.44, 1.08, facecolor="none", edgecolor=ORANGE,
                             linewidth=1, linestyle="--"))
    _arrow(left, (2.58, 1.53), (2.33, 1.83), color=ORANGE,
           connectionstyle="arc3,rad=0.35")
    left.text(2.7, 1.71, "90°", fontsize=9, color=ORANGE, ha="center")
    left.text(0.18, 0.34, "Locked footprint is preserved; mutable blocks\nchoose a region, origin and 0/90° orientation.",
              fontsize=9.1, va="top", linespacing=1.3)

    # Event semantics are geometric, but no physical coordinate/time is inferred.
    entry, pickup, release, complete = 0.30, 1.47, 2.03, 2.90
    right.add_patch(Rectangle((entry, 2.21), release-entry, 0.32, facecolor="#E5E7EB",
                              edgecolor=GRAY, linewidth=0.8))
    right.text((entry+release)/2, 2.37, "Block occupies its rectangle", fontsize=9.1, ha="center", va="center")
    right.plot([entry, entry], [2.17, 2.58], color=GRAY, linewidth=0.8)
    right.plot([release, release], [1.40, 2.58], color=ORANGE, linewidth=0.9, linestyle="--")
    right.text(entry, 2.76, "First entry", fontsize=9.1, ha="center")
    right.text(release+0.05, 2.91, "Space released", fontsize=9.1, color=ORANGE, ha="center")
    right.text(release+0.05, 2.70, "at loaded-move start", fontsize=9.1, color=ORANGE, ha="center")
    phases = ((1.05, pickup, "Empty", "white", BLUE),
              (pickup, release, "Hold", "#D6EAF4", BLUE),
              (release, complete, "Loaded", BLUE, "white"))
    for begin, end, label, fill, textcolor in phases:
        right.add_patch(Rectangle((begin, 1.60), end-begin, 0.40, facecolor=fill, edgecolor=BLUE, linewidth=0.8))
        right.text((begin+end)/2, 1.80, label, fontsize=9, color=textcolor, ha="center", va="center")
    right.text(1.00, 1.26, "Erection / carry task", fontsize=9.2, va="center")
    _arrow(right, (entry, 1.03), (3.02, 1.03), width=0.75)
    right.text(3.02, 0.88, "Time", ha="right", fontsize=9)
    right.text(0.03, 0.59, "Travel depends on chosen pickup/drop geometry.\nParallel X/Y motion uses the longer travel time.\nTandem cranes synchronize each phase.",
               fontsize=9.1, linespacing=1.35, va="top")
    return fig


def save_figure(fig: plt.Figure, output_dir: Path, stem: str) -> None:
    output_dir.mkdir(parents=True, exist_ok=True)
    for suffix in ("pdf", "svg"):
        fig.savefig(output_dir / f"{stem}.{suffix}", format=suffix, dpi=300)
    plt.close(fig)


def main() -> None:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--data", type=Path, default=DEFAULT_DATA)
    parser.add_argument("--output-dir", type=Path, default=HERE)
    args = parser.parse_args()
    configure()
    data = json.loads(args.data.read_text(encoding="utf-8"))
    save_figure(draw_terminal_cases(data), args.output_dir, "fig7_terminal_cases")
    save_figure(draw_physical_constraints(), args.output_dir, "fig8_physical_constraints")


if __name__ == "__main__":
    main()
