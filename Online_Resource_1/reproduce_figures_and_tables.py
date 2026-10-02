"""Reproduce result figures and numeric tables from released aggregate files."""

from __future__ import annotations

import csv
import json
import statistics
from collections import Counter
from pathlib import Path

import matplotlib as mpl
import matplotlib.pyplot as plt
import numpy as np
from matplotlib.colors import BoundaryNorm, ListedColormap
from matplotlib.patches import Patch
from generate_case_figures import configure as configure_cases
from generate_case_figures import draw_terminal_cases, draw_physical_constraints, save_figure


ROOT = Path(__file__).resolve().parent
OUT = ROOT / "reproduced"
COLORS = {
    "LRP": "#666666",
    "J_VND": "#0072B2",
    "S_VND": "#B54A00",
    "tie": "#E5E7EB",
    "J_win": "#0072B2",
    "S_win": "#B54A00",
}
METHODS = ("LRP", "J_VND", "S_VND")
MARKERS = {"LRP": "D", "J_VND": "o", "S_VND": "s"}
HATCHES = {"LRP": "", "J_VND": "///", "S_VND": "\\\\\\"}

GATE_FIELDS = (
    "source_state_match",
    "configuration_and_binary_match",
    "accepted_solve_mode_match",
    "accepted_invocation_cap_match",
    "initial_sequence_assignment_tandem_match",
    "initial_geometry_match",
)
COST_LEVELS = (
    "compatibility",
    "projected_completion",
    "current_batch_makespan",
    "current_batch_total_completion",
    "pool_makespan",
)


def configure() -> None:
    OUT.mkdir(exist_ok=True)
    mpl.rcParams.update(
        {
            "font.family": "sans-serif",
            "font.sans-serif": ["Arial", "Helvetica", "DejaVu Sans"],
            "font.size": 9.5,
            "axes.labelsize": 9.5,
            "xtick.labelsize": 8.8,
            "ytick.labelsize": 8.8,
            "legend.fontsize": 8.8,
            "text.color": "#20242A",
            "axes.labelcolor": "#20242A",
            "axes.edgecolor": "#666666",
            "axes.spines.top": False,
            "axes.spines.right": False,
            "axes.linewidth": 0.65,
            "xtick.major.width": 0.65,
            "ytick.major.width": 0.65,
            "hatch.linewidth": 0.6,
            "pdf.fonttype": 42,
            "ps.fonttype": 42,
            "svg.fonttype": "none",
            "svg.hashsalt": "p3-ijamt-2026-10-01",
            "savefig.bbox": "tight",
            "savefig.pad_inches": 0.04,
        }
    )


def save(fig: plt.Figure, stem: str) -> None:
    for suffix in ("pdf", "svg"):
        fig.savefig(OUT / f"{stem}.{suffix}", format=suffix, dpi=300)
    plt.close(fig)


def panel(ax: plt.Axes, label: str) -> None:
    ax.text(0, 1.04, label, transform=ax.transAxes, ha="left", va="bottom", fontweight="bold", fontsize=10)

def draw_budget(data: dict) -> plt.Figure:
    budgets = [3, 6, 12]
    common_states = {"b1-r007", "b1-r012", "b1-r026", "b1-r030"}
    for budget in budgets:
        if set(data["state_ids_by_cap_seconds"][str(budget)]) != common_states:
            raise ValueError("Budget figure must use the same four predetermined states at every cap")
        for method in METHODS:
            rows = [row for row in data["rows"] if row["budget_seconds"] == budget and row["method"] == method]
            if len(rows) != 4 or {row["state_id"] for row in rows} != common_states:
                raise ValueError("Budget figure requires one record per state, method and cap")
            for field, metric in (("first_feasible_ms", "median_first_feasible_ms"),
                                  ("accepted_improvements", "median_improvements")):
                if np.median([row[field] for row in rows]) != data["timing"][f"b{budget}_{method}"][metric]:
                    raise ValueError(f"Budget median disagrees with released records: {budget}, {method}, {metric}")
    fig, axes = plt.subplots(1, 2, figsize=(6.85, 2.8), layout="constrained")
    x = np.arange(len(budgets))
    # Offset markers distinguish nearly coincident J/S medians. No lines imply
    # a continuous response or an unchanged accepted initial plan across caps.
    for index, method in enumerate(METHODS):
        values = [data["timing"][f"b{budget}_{method}"]["median_first_feasible_ms"] / 1000 for budget in budgets]
        axes[0].plot(
            x + (index - 1) * 0.12, values, marker=MARKERS[method], markersize=5.5,
            markerfacecolor="white" if method == "S_VND" else COLORS[method],
            markeredgewidth=1.1, linestyle="none",
            color=COLORS[method], label=method.replace("_", "-"),
        )
    axes[0].set_ylim(0, 3.0)
    axes[0].set_ylabel("Median time to first feasible plan (s)")
    axes[0].legend(frameon=False, ncol=3, loc="upper center", columnspacing=0.8, handlelength=1.4, handletextpad=0.35)
    width = 0.28
    for index, method in enumerate(("J_VND", "S_VND")):
        values = [data["timing"][f"b{budget}_{method}"]["median_improvements"] for budget in budgets]
        bars = axes[1].bar(x + (index - 0.5) * width, values, width,
                           facecolor="white", edgecolor=COLORS[method], linewidth=1.1,
                           hatch=HATCHES[method], label=method.replace("_", "-"))
        for bar in bars:
            axes[1].annotate(f"{bar.get_height():g}", (bar.get_x() + bar.get_width()/2, bar.get_height()),
                             xytext=(0, 3), textcoords="offset points", ha="center", va="bottom", fontsize=8.8)
    axes[1].set_ylim(0, 6.7)
    axes[1].set_yticks([0, 2, 4, 6])
    axes[1].set_ylabel("Median accepted VND improvements")
    axes[1].legend(frameon=False, ncol=2, loc="upper center", handlelength=1.5)
    for index, ax in enumerate(axes):
        ax.set_xticks(x, [f"{budget}\n(n = 4)" for budget in budgets])
        ax.set_xlabel("Research invocation cap (s)")
        ax.set_axisbelow(True)
        ax.grid(axis="y", color="#E5E7EB", linewidth=0.6)
        panel(ax, f"({chr(97 + index)})")
    return fig

def draw_repeats(states: list[str], matrix: np.ndarray) -> plt.Figure:
    """Show all 144 observations at a readable 24-column panel width."""
    cmap = ListedColormap([COLORS["S_win"], COLORS["tie"], COLORS["J_win"]])
    cmap.set_bad("white")
    norm = BoundaryNorm([-1.5, -0.5, 0.5, 1.5], cmap.N)
    fig, axes = plt.subplots(2, 1, figsize=(6.85, 3.4))
    fig.subplots_adjust(left=0.10, right=0.99, top=0.91, bottom=0.24, hspace=0.80)
    for index, (ax, batch) in enumerate(zip(axes, ("b2", "b3"), strict=True)):
        columns = [i for i, state in enumerate(states) if state.startswith(batch + "-")]
        subset = matrix[:, columns]
        ax.imshow(subset, aspect="auto", cmap=cmap, norm=norm, interpolation="nearest")
        ax.set_yticks(range(3), ["Rep. 1", "Rep. 2", "Rep. 3"])
        ax.set_xticks(range(len(columns)), [states[i].split("-r")[1] for i in columns], rotation=90)
        ax.tick_params(axis="both", length=0, pad=4)
        ax.set_xticks(np.arange(-0.5, len(columns), 1), minor=True)
        ax.set_yticks(np.arange(-0.5, 3, 1), minor=True)
        ax.grid(which="minor", color="white", linewidth=1.0)
        ax.tick_params(which="minor", bottom=False, left=False)
        for spine in ax.spines.values():
            spine.set_visible(False)
        panel(ax, f"({chr(97 + index)}) Batch {batch[-1]}")
        for row_index, values in enumerate(subset):
            for column_index, value in enumerate(values):
                symbol = "×" if np.isnan(value) else {-1: "S", 0: "·", 1: "J"}[int(value)]
                ax.text(column_index, row_index, symbol, ha="center", va="center",
                        fontsize=9.5, fontweight="bold",
                        color="white" if not np.isnan(value) and value else "#30343B")
    fig.text(0.55, 0.102, "Rolling round within each batch", ha="center", fontsize=9.5)
    handles = [
        Patch(facecolor=COLORS["J_win"], label="J: J better"),
        Patch(facecolor=COLORS["tie"], label="·: Tie"),
        Patch(facecolor=COLORS["S_win"], label="S: S better"),
        Patch(facecolor="white", edgecolor="#666666", label="×: Ineligible"),
    ]
    fig.legend(handles=handles, frameon=False, loc="lower center", bbox_to_anchor=(0.55, -0.01), ncol=4,
               columnspacing=1.2, handlelength=1.1, handletextpad=0.45)
    return fig

def draw_activity(matrices: list[np.ndarray]) -> plt.Figure:
    vmax = max(matrix.max() for matrix in matrices)
    fig, axes = plt.subplots(1, 2, figsize=(6.85, 2.6), layout="constrained")
    # Counts use a neutral sequential scale, separate from J/S outcome colours.
    cmap = mpl.colors.LinearSegmentedColormap.from_list("counts", ["#F4F5F6", "#4B5563"])
    for index, (ax, matrix, title) in enumerate(zip(axes, matrices,
            ("Feasible geometry variation", "Final geometry adoption"), strict=True)):
        ax.imshow(matrix, cmap=cmap, vmin=0, vmax=vmax, aspect="auto")
        ax.set_xticks(range(3), ["S better", "Tie", "J better"])
        ax.set_yticks(range(2), ["No", "Yes"])
        ax.set_xlabel("One-step cost outcome")
        ax.tick_params(axis="both", length=0)
        ax.set_xticks(np.arange(-0.5, 3, 1), minor=True)
        ax.set_yticks(np.arange(-0.5, 2, 1), minor=True)
        ax.grid(which="minor", color="white", linewidth=1.5)
        ax.tick_params(which="minor", bottom=False, left=False)
        for spine in ax.spines.values():
            spine.set_visible(False)
        panel(ax, f"({chr(97 + index)}) {title}")
        for row_index in range(2):
            for column_index in range(3):
                value = matrix[row_index, column_index]
                ax.text(column_index, row_index, str(value), ha="center", va="center",
                        color="white" if value > 0.55 * vmax else "#20242A", fontsize=12)
    return fig

def draw_rolling(e7: dict, repeats: dict, condition: dict) -> plt.Figure:
    """Keep original, contemporaneous and shared-boundary runs in separate blocks."""
    assert repeats["batch_order"] == 1 and condition["batch_order"] == 2
    for method in ("J_VND", "S_VND"):
        reference = repeats["historical_E7_reference"]["methods"][method]
        assert reference["completion_offset_seconds"] == e7["methods"][method]["completion_offset_seconds"]
        assert abs(reference["solver_wall_seconds"] -
                   e7["methods"][method]["solver_wall_time_milliseconds"]["total"] / 1000) < 1e-9
    blocks = [
        ("E7 original · batch 1", e7["methods"], ("LRP", "J_VND", "S_VND"), 0.0),
        ("E12 A · batch 1", repeats["repetitions"]["repeat-2"]["methods"], ("J_VND", "S_VND"), 2.75),
        ("E12 B · batch 1", repeats["repetitions"]["repeat-3"]["methods"], ("J_VND", "S_VND"), 4.85),
        ("LRP boundary · batch 2", condition["repetitions"]["repeat-1"]["methods"], ("J_VND", "S_VND"), 6.95),
    ]
    fig, axes = plt.subplots(1, 2, figsize=(6.85, 4.65))
    fig.subplots_adjust(left=0.10, right=0.98, top=0.90, bottom=0.185, wspace=0.50)
    positions, labels, label_colors = [], [], []
    for heading, records, methods, header_y in blocks:
        delta = records["S_VND"]["completion_offset_seconds"] - records["J_VND"]["completion_offset_seconds"]
        winner = "J_VND" if delta > 0 else "S_VND"
        wall = {method: records[method].get("solver_wall_seconds", 0) for method in methods}
        if heading.startswith("E7"):
            wall = {method: records[method]["solver_wall_time_milliseconds"]["total"] / 1000 for method in methods}
        wall_winner = "J_VND" if wall["J_VND"] < wall["S_VND"] else "S_VND"
        for index, ax in enumerate(axes):
            ax.text(0.0, header_y, heading, transform=ax.get_yaxis_transform(),
                    ha="left", va="center", fontsize=8.8, fontweight="bold")
            comparison = (f"{winner[0]} earlier {abs(delta)/3600:.2f} h" if index == 0
                          else f"{wall_winner[0]} lower than {'S' if wall_winner == 'J_VND' else 'J'}")
            ax.text(1.0, header_y, comparison, transform=ax.get_yaxis_transform(),
                    ha="right", va="center", fontsize=8.8,
                    color=COLORS[winner if index == 0 else wall_winner])
        for offset, method in enumerate(methods):
            y = header_y + 0.65 + offset * 0.70
            days = records[method]["completion_offset_seconds"] / 86400
            minutes = wall[method] / 60
            positions.append(y)
            labels.append(method.replace("_", "-"))
            label_colors.append(COLORS[method])
            axes[0].scatter(days, y, marker=MARKERS[method], s=42, color=COLORS[method], zorder=3)
            axes[0].annotate(f"{days:.3f}", (days, y), xytext=(7, 0),
                             textcoords="offset points", va="center", fontsize=8.8)
            axes[1].barh(y, minutes, height=0.42, facecolor="white", edgecolor=COLORS[method],
                         linewidth=1.1, hatch=HATCHES[method])
            axes[1].annotate(f"{minutes:.1f}", (minutes, y), xytext=(4, 0),
                             textcoords="offset points", va="center", fontsize=8.8)
    axes[0].set_xlim(56.0, 67.5)
    axes[0].set_xticks([58, 60, 62, 64, 66])
    axes[0].set_xlabel("Batch completion (days)\nfrom each block's common origin")
    axes[1].set_xlim(0, 54)
    axes[1].set_xticks([0, 15, 30, 45])
    axes[1].set_xlabel("Solver wall time (min)")
    for index, ax in enumerate(axes):
        ax.set_yticks(positions, labels)
        for label, color in zip(ax.get_yticklabels(), label_colors):
            label.set_color(color)
        ax.set_ylim(9.0, -0.5)
        ax.grid(axis="x", color="#E5E7EB", linewidth=0.6)
        ax.set_axisbelow(True)
        for y in (2.50, 4.60, 6.70):
            ax.axhline(y, color="#D8DBDF", linewidth=0.65)
        panel(ax, f"({chr(97 + index)})")
    fig.text(0.01, 0.022, "Separate execution blocks; batch 2 starts at the same retained LRP boundary for J and S.", fontsize=8.8)
    return fig


def budget_figure() -> None:
    data = json.loads((ROOT / "development_budget_common_subset.json").read_text())
    save(draw_budget(data), "fig3_budget_sensitivity")


def load_rows() -> list[dict[str, str]]:
    with (ROOT / "e10_state_outcomes.csv").open(newline="") as stream:
        return list(csv.DictReader(stream))


def repeat_figure(rows: list[dict[str, str]]) -> None:
    states = sorted({row["state"] for row in rows})
    matrix = np.full((3, len(states)), np.nan)
    for row in rows:
        if row["pair_eligible"] == "True":
            matrix[int(row["repeat"]) - 1, states.index(row["state"])] = {"S_win": -1, "tie": 0, "J_win": 1}[row["outcome"]]
    save(draw_repeats(states, matrix), "fig4_repeat_outcomes")


def as_bool(value: str) -> bool:
    return value == "True"


def gate_from_record(row: dict[str, str]) -> bool:
    """Recompute common-initialization eligibility from released fields."""
    return all(as_bool(row[field]) for field in GATE_FIELDS)


def cost_key(row: dict[str, str], method: str) -> tuple[int, ...]:
    return tuple(int(row[f"{method}_final_{level}_microseconds"]) for level in COST_LEVELS)


def outcome_from_cost(row: dict[str, str]) -> str:
    j_cost = cost_key(row, "J")
    s_cost = cost_key(row, "S")
    if j_cost < s_cost:
        return "J_win"
    if s_cost < j_cost:
        return "S_win"
    return "tie"


def reproduce_protocol(rows: list[dict[str, str]]) -> None:
    """Recompute gate decisions, outcomes, and the three analysis denominators."""
    aggregate = json.loads((ROOT / "e10_aggregate.json").read_text())["aggregate"]
    gate_disagreements = [
        f"{row['state']}/repeat-{row['repeat']}"
        for row in rows
        if gate_from_record(row) != as_bool(row["pair_eligible"])
    ]
    eligible = [row for row in rows if gate_from_record(row)]
    outcome_disagreements = [
        f"{row['state']}/repeat-{row['repeat']}"
        for row in eligible
        if outcome_from_cost(row) != row["outcome"]
    ]
    singleton = [
        row
        for row in eligible
        if row["J_solve_mode"] == "singleton_ready_dispatch"
        and row["S_solve_mode"] == "singleton_ready_dispatch"
    ]
    other = [row for row in eligible if row not in singleton]
    outcomes = {
        label: sum(outcome_from_cost(row) == label for row in eligible)
        for label in ("J_win", "tie", "S_win")
    }

    synthetic_match = {field: "True" for field in GATE_FIELDS}
    synthetic_mismatch = synthetic_match | {"accepted_solve_mode_match": "False"}
    synthetic_controls = {
        "all_common_fields_match": gate_from_record(synthetic_match),
        "accepted_mode_mismatch": gate_from_record(synthetic_mismatch),
    }
    checks = {
        "stored_gate_matches_recomputation": not gate_disagreements,
        "stored_outcome_matches_cost_recomputation": not outcome_disagreements,
        "planned_pair_count": len(rows) == aggregate["paired_observation_count"],
        "eligible_pair_count": len(eligible) == aggregate["eligible_paired_observation_count"],
        "outcome_counts": outcomes
        == {
            "J_win": aggregate["overall_outcomes"]["J_wins"],
            "tie": aggregate["overall_outcomes"]["ties"],
            "S_win": aggregate["overall_outcomes"]["S_wins"],
        },
        "singleton_ready_count": len(singleton) == 78,
        "other_eligible_count": len(other) == 64,
        "synthetic_match_passes": synthetic_controls["all_common_fields_match"],
        "synthetic_mismatch_fails": not synthetic_controls["accepted_mode_mismatch"],
    }
    if not all(checks.values()):
        failed = ", ".join(name for name, passed in checks.items() if not passed)
        raise RuntimeError(f"Protocol reproduction failed: {failed}")

    report = {
        "analysis_levels": {
            "full_controller_planned_pairs": len(rows),
            "common_initialization_pairs": len(eligible),
            "non_singleton_common_initialization_pairs": len(other),
        },
        "recomputed_outcomes": outcomes,
        "gate_fields": list(GATE_FIELDS),
        "common_configuration_note": (
            "configuration_and_binary_match covers common executable and configuration fields; "
            "the J/S treatment flag is separate from the equality test"
        ),
        "synthetic_gate_controls": synthetic_controls,
        "gate_disagreements": gate_disagreements,
        "outcome_disagreements": outcome_disagreements,
        "checks": checks,
    }
    (OUT / "eligibility_recomputed.json").write_text(
        json.dumps(report, ensure_ascii=False, indent=2) + "\n"
    )


def activity_figure(rows: list[dict[str, str]]) -> None:
    eligible = [row for row in rows if as_bool(row["pair_eligible"])]
    outcomes = ["S_win", "tie", "J_win"]
    matrices = []
    for field in ("J_geometry_activity", "J_final_geometry_changed"):
        matrices.append(
            np.array(
                [
                    [sum(as_bool(row[field]) == active and row["outcome"] == outcome for row in eligible) for outcome in outcomes]
                    for active in (False, True)
                ]
            )
        )
    save(draw_activity(matrices), "fig5_activity_adoption_cross")


def rolling_figure_and_table() -> None:
    data = json.loads((ROOT / "e7_rolling_aggregate.json").read_text())
    methods = ["LRP", "J_VND", "S_VND"]
    repeats = json.loads((ROOT / "e12_rolling_repeat_summary.json").read_text())
    condition = json.loads((ROOT / "e12_condition_transfer_summary.json").read_text())
    save(draw_rolling(data, repeats, condition), "fig6_rolling_endpoints")
    lines = [
        r"\begin{tabular}{lrrrrr}",
        r"\toprule",
        r"Design & Batch completion (d) & Solver wall (s) & Rounds & Accepted / failed invocations & Rounds with geometry adoption \\",
        r"\midrule",
    ]
    for method in methods:
        item = data["methods"][method]
        lines.append(
            f"{method.replace('_', '-')} & {item['completion_offset_seconds']/86400:.3f} & "
            f"{item['solver_wall_time_milliseconds']['total']/1000:.3f} & {item['round_count']} & "
            f"{item['trace_feasible_count']} / {item['trace_failed_count']} & {item['final_geometry_changed_count']} " + r"\\"
        )
    lines.extend([r"\bottomrule", r"\end{tabular}", ""])
    (OUT / "table_rolling.tex").write_text("\n".join(lines))


def e10_table(rows: list[dict[str, str]]) -> None:
    data = json.loads((ROOT / "e10_aggregate.json").read_text())["aggregate"]
    outcomes = data["overall_outcomes"]
    eligible = [row for row in rows if as_bool(row["pair_eligible"])]
    singleton = [
        row
        for row in eligible
        if row["J_solve_mode"] == "singleton_ready_dispatch"
        and row["S_solve_mode"] == "singleton_ready_dispatch"
    ]
    other = [row for row in eligible if row not in singleton]
    by_state: dict[str, list[dict[str, str]]] = {}
    for row in eligible:
        by_state.setdefault(row["state"], []).append(row)
    stable_non_tie_states = sum(
        len(state_rows) == 3
        and len({row["outcome"] for row in state_rows}) == 1
        and state_rows[0]["outcome"] != "tie"
        for state_rows in by_state.values()
    )
    failed = data["eligible_trace_failures"]
    wall = data["eligible_solver_wall_totals_milliseconds"]
    lines = [
        r"\begin{tabular}{lr}",
        r"\toprule",
        r"Quantity & Value \\",
        r"\midrule",
        f"Scheduled J/S pairs & {data['paired_observation_count']} " + r"\\",
        f"Eligible pairs & {data['eligible_paired_observation_count']} " + r"\\",
        f"Ineligible pairs & {data['ineligible_paired_observation_count']} " + r"\\",
        f"J better / tie / S better & {outcomes['J_wins']} / {outcomes['ties']} / {outcomes['S_wins']} " + r"\\",
        f"Singleton-ready pairs (ties) & {len(singleton)} ({sum(row['outcome'] == 'tie' for row in singleton)}) " + r"\\",
        f"Other pairs: J / tie / S & {len(other)}: "
        f"{sum(row['outcome'] == 'J_win' for row in other)} / "
        f"{sum(row['outcome'] == 'tie' for row in other)} / "
        f"{sum(row['outcome'] == 'S_win' for row in other)} " + r"\\",
        f"States with three eligible repeats & {data['states_with_all_three_pairs_eligible']} / {data['state_count']} " + r"\\",
        f"Same outcome in all three eligible repeats & {data['three_of_three_outcome_stable_states']} / {data['states_with_all_three_pairs_eligible']} " + r"\\",
        f"Stable non-tie states & {stable_non_tie_states} / {data['states_with_all_three_pairs_eligible']} " + r"\\",
        f"Eligible J feasible geometry variation & {data['eligible_J_candidate_geometry_active_observations']} / {data['eligible_paired_observation_count']} " + r"\\",
        f"Eligible J final geometry changes & {data['eligible_J_final_geometry_changed_observations']} / {data['eligible_paired_observation_count']} " + r"\\",
        f"Non-ties first differing at current-batch pool makespan & {data['non_tie_first_differing_levels']['current_batch_makespan']} / "
        f"{sum(row['outcome'] != 'tie' for row in eligible)} " + r"\\",
        f"J/S failed invocations in eligible pairs & {failed['J_VND']} / {failed['S_VND']} " + r"\\",
        f"J/S eligible solver wall time (s) & {wall['J_VND']/1000:.3f} / {wall['S_VND']/1000:.3f} " + r"\\",
        r"\bottomrule",
        r"\end{tabular}",
        "",
    ]
    (OUT / "table_e10.tex").write_text("\n".join(lines))


def diagnostic_table_and_checks() -> None:
    """Recompute released E11 statistics; restricted plans are not replayed."""
    data = json.loads((ROOT / "e11_common_initial_diagnostics.json").read_text())
    rows, probes = data["rows"], data["fixed_candidate_records"]
    fields = ("projected_current_batch_completion", "current_batch_makespan",
              "current_batch_total_completion_time", "value")
    outcomes = Counter()
    for row in rows:
        methods = row["methods"]
        costs = [tuple(methods[m]["final_cost"][k] for k in fields)
                 for m in ("J_VND", "S_VND")]
        outcome = "J_win" if costs[0] < costs[1] else "S_win" if costs[1] < costs[0] else "tie"
        assert outcome == row["outcome"]
        outcomes[outcome] += 1
        for method in methods.values():
            assert method["complete_incumbent_copy_equal"]
            assert method["complete_initial_plan_sha256"] == row["common_initial_plan_sha256"]
            assert method["improvement_budget_seconds"] == 12
    categories = Counter()
    for probe in probes:
        j, s = (probe["decodes"][m]["feasible"] for m in ("J_VND", "S_VND"))
        category = "both" if j and s else "J_only" if j else "S_only" if s else "neither"
        assert category == probe["feasibility_category"]
        categories[category] += 1
    assert len(rows) == data["diagnostic_pair_count"] == 15
    assert len(probes) == data["fixed_candidate_count"] == 282
    assert dict(outcomes) == data["outcomes"]
    assert dict(categories) == data["fixed_candidate_categories"]
    assert len({(p["state"], p["repeat"], p["signature_sha256"]) for p in probes}) == len(probes)
    assert all(v["physical_complete_plan_equal"] for r in rows
               for v in r["cold_common_initial_redecode"].values())
    with (ROOT / "e11_state_statistics.csv").open(newline="") as stream:
        released = {r["state"]: r for r in csv.DictReader(stream)}
    lines = [r"\begin{tabular}{lrrrr}", r"\toprule",
             r"State & J/tie/S outcomes & Executed decodes J/S & Layout elapsed s J/S & Decoder success both/J/S \\",
             r"\midrule"]
    states = []
    for state in data["protocol"]["states"]:
        selected = [r for r in rows if r["state"] == state]
        selected_probes = [p for p in probes if p["state"] == state]
        counts = Counter(r["outcome"] for r in selected)
        feasible = Counter(p["feasibility_category"] for p in selected_probes)
        methods = {m: [r["methods"][m] for r in selected] for m in ("J_VND", "S_VND")}
        executions = [statistics.median(r["candidate_executions"] for r in methods[m])
                      for m in ("J_VND", "S_VND")]
        layout = [statistics.median(r["layout_plan_seconds"] for r in methods[m])
                  for m in ("J_VND", "S_VND")]
        prior = released[state]
        assert all(counts[k] == int(prior[k]) for k in ("J_win", "tie", "S_win"))
        assert all(feasible[k] == int(prior[k]) for k in ("both", "J_only", "S_only", "neither"))
        assert executions == [float(prior[f"{m}_candidate_executions_median"]) for m in ("J", "S")]
        assert layout == [float(prior[f"{m}_site_layout_elapsed_seconds_median"]) for m in ("J", "S")]
        values = ["/".join(str(counts[k]) for k in ("J_win", "tie", "S_win")),
                  "/".join(f"{v:g}" for v in executions),
                  "/".join(f"{v:.3f}" for v in layout),
                  "/".join(str(feasible[k]) for k in ("both", "J_only", "S_only"))]
        lines.append(state + " & " + " & ".join(values) + r" \\")
        states.append({"state": state, "outcomes": dict(counts),
                       "executed_decodes_median_J_S": executions,
                       "layout_elapsed_seconds_median_J_S": layout,
                       "probe_categories": dict(feasible)})
    lines.extend([r"\bottomrule", r"\end{tabular}", ""])
    (OUT / "table_e11.tex").write_text("\n".join(lines))
    (OUT / "e11_recomputed.json").write_text(json.dumps({
        "scope": "Released aggregate consistency and table reproduction; no restricted plan or solver replay.",
        "pair_count": len(rows), "outcomes": dict(outcomes), "probe_count": len(probes),
        "probe_categories": dict(categories), "states": states, "pass": True,
    }, indent=2) + "\n")


def rolling_repeat_table_and_checks() -> None:
    data = json.loads((ROOT / "e12_rolling_repeat_summary.json").read_text())
    assert data["same_historical_snapshot_and_parameters"]
    blocks = [("E7 original", data["historical_E7_reference"])]
    blocks.extend((label, data["repetitions"][key])
                  for label, key in (("E12 A", "repeat-2"), ("E12 B", "repeat-3")))
    differences = []
    lines = [r"\begin{tabular}{lrrrrrr}", r"\toprule",
             r"Block & Completion s J/S & S-minus-J h & Solver wall s J/S & Rounds J/S & Adoption J/S & Calls/failed J/S \\",
             r"\midrule"]
    for label, block in blocks:
        j, s = (block["methods"][m] for m in ("J_VND", "S_VND"))
        for run in (j, s):
            assert run["complete"] and run["exit_code"] == 0
            assert run["field_validation_accepted"]
            assert run["audit"]["invalid_feasible_outputs"] == 0
            assert run["audit"]["accepted"] == run["trace_feasible_count"]
        assert j["snapshot_content_sha256"] == s["snapshot_content_sha256"]
        assert j["parameters"] == s["parameters"]
        assert j["initial_sequence_signature"] == s["initial_sequence_signature"]
        assert j["initial_geometry_signature"] == s["initial_geometry_signature"]
        delta = s["completion_offset_seconds"] - j["completion_offset_seconds"]
        if label != "E7 original":
            differences.append(delta)
        values = [f"{j['completion_offset_seconds']:.0f}/{s['completion_offset_seconds']:.0f}",
                  f"{delta / 3600:.2f}",
                  f"{j['solver_wall_seconds']:.3f}/{s['solver_wall_seconds']:.3f}",
                  f"{j['round_count']}/{s['round_count']}",
                  f"{j['geometry_adoption_rounds']}/{s['geometry_adoption_rounds']}",
                  f"{j['trace_call_count']}/{j['trace_failed_count']}, {s['trace_call_count']}/{s['trace_failed_count']}"]
        lines.append(label + " & " + " & ".join(values) + r" \\")
    assert differences == data["contemporaneous_paired_differences_seconds"]
    lines.extend([r"\bottomrule", r"\end{tabular}", ""])
    (OUT / "table_rolling_repeats.tex").write_text("\n".join(lines))
    (OUT / "rolling_repeats_recomputed.json").write_text(json.dumps({
        "scope": "Recompute released endpoint differences and table cells; restricted traces are not replayed.",
        "contemporaneous_paired_differences_seconds": differences, "pass": True,
    }, indent=2) + "\n")


def condition_table_and_checks() -> None:
    data = json.loads((ROOT / "e12_condition_transfer_summary.json").read_text())
    assert data["batch_order"] == 2 and len(data["repetitions"]) == 1
    block = data["repetitions"]["repeat-1"]
    j, s = (block["methods"][m] for m in ("J_VND", "S_VND"))
    boundaries = [run["execution"]["provenance"]["boundary"] for run in (j, s)]
    assert boundaries[0] == boundaries[1]
    assert j["snapshot_content_sha256"] == s["snapshot_content_sha256"]
    assert j["parameters"] == s["parameters"]
    assert j["initial_sequence_signature"] == s["initial_sequence_signature"]
    assert j["initial_geometry_signature"] == s["initial_geometry_signature"]
    for run in (j, s):
        assert run["complete"] and run["exit_code"] == 0
        assert run["field_validation_accepted"]
        assert run["audit"]["invalid_feasible_outputs"] == 0
        assert run["audit"]["accepted"] == run["trace_feasible_count"]
        reference = run["time_reference"]
        origin = reference["origin_current_time_microseconds"]
        assert origin == boundaries[0]["origin_current_time_microseconds"]
        offset = (reference["final_current_time_microseconds"] - origin) / 1e6
        assert abs(offset - run["completion_offset_seconds"]) < 1e-9
    delta = s["completion_offset_seconds"] - j["completion_offset_seconds"]
    assert delta == block["comparison"]["S_minus_J_completion_seconds"]
    assert [delta] == data["contemporaneous_paired_differences_seconds"]
    wall_delta = j["solver_wall_seconds"] - s["solver_wall_seconds"]
    rows = [
        ("Completion from common boundary, s", [f"{r['completion_offset_seconds']:.3f}" for r in (j, s)]),
        ("Recorded solver wall time, s", [f"{r['solver_wall_seconds']:.3f}" for r in (j, s)]),
        ("Rolling rounds", [str(r["round_count"]) for r in (j, s)]),
        ("Total invocations", [str(r["trace_call_count"]) for r in (j, s)]),
        ("Feasible/failed invocations", [f"{r['trace_feasible_count']}/{r['trace_failed_count']}" for r in (j, s)]),
        ("Rounds with geometry adoption", [str(r["geometry_adoption_rounds"]) for r in (j, s)]),
    ]
    for label, key in (("Pool tasks, min/median/max", "pool_task_count"),
                       ("Locked blocks, min/median/max", "locked_block_count")):
        rows.append((label, ["/".join(f"{r['workload_profile'][key][p]:g}"
                                     for p in ("minimum", "median", "maximum")) for r in (j, s)]))
    rows.append(("Accepted calls with tandem tasks",
                 [str(r["workload_profile"]["tandem_positive_calls"]) for r in (j, s)]))
    lines = [r"\begin{tabular}{lrr}", r"\toprule", r"Measure & J-VND & S-VND \\", r"\midrule"]
    lines.extend(label + " & " + " & ".join(values) + r" \\" for label, values in rows)
    lines.extend([r"\bottomrule", r"\end{tabular}", ""])
    (OUT / "table_condition.tex").write_text("\n".join(lines))
    (OUT / "condition_recomputed.json").write_text(json.dumps({
        "scope": "Released shared-boundary consistency, exact checkpoint arithmetic, and table reproduction; no restricted trace or solver replay.",
        "batch_order": 2, "shared_boundary_sha256": boundaries[0]["checkpoint_sha256"],
        "S_minus_J_completion_seconds": delta,
        "J_reduction_vs_S_percent": delta / s["completion_offset_seconds"] * 100,
        "J_minus_S_solver_wall_seconds": wall_delta,
        "J_solver_wall_increase_percent": wall_delta / s["solver_wall_seconds"] * 100,
        "pass": True,
    }, indent=2) + "\n")


def main() -> None:
    configure()
    rows = load_rows()
    reproduce_protocol(rows)
    budget_figure()
    repeat_figure(rows)
    activity_figure(rows)
    rolling_figure_and_table()
    e10_table(rows)
    diagnostic_table_and_checks()
    rolling_repeat_table_and_checks()
    condition_table_and_checks()
    configure_cases()
    cases = json.loads((ROOT / "terminal_case_evidence.json").read_text())
    save_figure(draw_terminal_cases(cases), OUT, "fig7_terminal_cases")
    save_figure(draw_physical_constraints(), OUT, "fig8_physical_constraints")


if __name__ == "__main__":
    main()
