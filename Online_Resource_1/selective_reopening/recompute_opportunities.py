"""Recompute mask opportunities from the anonymous released CSVs only.

This standard-library script does not import the private reanalysis or decode
new plans. Geometry-validation fields are checked as exported labels, rather
than independently validating restricted geometry or crane trajectories.
"""
from __future__ import annotations

import csv
import hashlib
import json
from collections import Counter, defaultdict
from pathlib import Path

ROOT = Path(__file__).resolve().parent
OBJECTIVES = ["projected_completion_us", "current_batch_makespan_us",
              "total_completion_us", "pool_value_us"]
SIMPLE_COLUMNS = ["J_objective", "S_objective", "reference_seed_objective",
                  "field128_objective", "rail512_objective"]


def rows(name):
    with (ROOT / name).open(newline="", encoding="utf-8") as stream:
        return list(csv.DictReader(stream))


def boolean(value):
    if value not in {"True", "False"}:
        raise ValueError(f"Invalid released Boolean: {value!r}")
    return value == "True"


def objective(value):
    values = json.loads(value)
    if values == [1]:
        return (1,)
    if (len(values) != 6 or any(type(v) is not int for v in values)
            or values[0] != 0 or values[1] not in (0, 1)):
        raise ValueError("Invalid lexicographic objective record")
    return tuple(values)


def main():
    masks = rows("anonymous_mask_comparisons.csv")
    candidates = rows("anonymous_candidate_comparisons.csv")
    executions = rows("state_execution_counts.csv")
    summary = json.loads((ROOT / "audit_summary.json").read_text())
    patterns = json.loads((ROOT / "winning_patterns.json").read_text())
    witnesses = json.loads((ROOT / "witness_validation.json").read_text())
    groups = defaultdict(list)
    for row in masks:
        groups[row["candidate_id"]].append(row)
    candidate_rows = {row["candidate_id"]: row for row in candidates}
    assert len(candidate_rows) == len(candidates) == len(groups)
    cases = {row["case_id"]: row for row in executions}
    assert len(cases) == len(executions)
    strict_groups = []
    strict_rows = 0
    successful = 0
    case_counts = Counter()
    for candidate_id, group in groups.items():
        exported = candidate_rows[candidate_id]
        u = int(exported["mutable_blocks"])
        last = (1 << u) - 1
        by_mask = {int(row["mask"]): row for row in group}
        assert len(by_mask) == len(group) == int(exported["mask_count"]) == (1 << u)
        assert set(by_mask) == set(range(1 << u))
        assert all(int(row["mutable_blocks"]) == u for row in group)
        costs = {mask: objective(row["objective"]) for mask, row in by_mask.items()}
        assert costs[0] == objective(exported["empty_objective"])
        assert costs[last] == objective(exported["full_objective"])
        endpoint_best = min(costs[0], costs[last])
        best_middle = min(range(1, last), key=lambda mask: (costs[mask], mask))
        assert best_middle == int(exported["best_middle_mask"])
        assert costs[best_middle] == objective(exported["best_middle_objective"])
        best_all = min(costs, key=lambda mask: (costs[mask], mask))
        assert best_all == int(exported["best_overall_mask"])
        simple_best = min(objective(exported[c]) for c in SIMPLE_COLUMNS)
        vanilla_best = min(objective(exported[c]) for c in SIMPLE_COLUMNS[:2])
        better_endpoints = costs[best_middle] < endpoint_best
        better_simple = costs[best_middle] < simple_best
        assert better_endpoints == boolean(exported["strict_middle_better_than_mask_endpoints"])
        assert better_simple == boolean(exported["strict_middle_better_than_all_simple_interventions"])
        assert (costs[best_middle] < vanilla_best) == boolean(exported["strict_middle_better_than_vanilla_endpoint_portfolio"])
        both = costs[0][0] == 0 and costs[last][0] == 0
        assert both == boolean(exported["both_endpoint_success"])
        case_counts[exported["case_id"]] += 1
        for mask, row in by_mask.items():
            is_middle = 0 < mask < last
            assert int(row["open_block_count"]) == bin(mask).count("1")
            assert is_middle == boolean(row["strict_middle"])
            assert (costs[mask][0] == 0) == boolean(row["success"])
            assert (is_middle and costs[mask] < endpoint_best) == boolean(row["strict_lex_better_than_mask_endpoint_portfolio"])
            assert (is_middle and costs[mask] < simple_best) == boolean(row["strict_lex_better_than_all_simple_interventions"])
            strict_rows += int(is_middle and costs[mask] < vanilla_best)
            if costs[mask][0] == 0:
                successful += 1
                assert boolean(row["geometry_checks_all_pass"])
                assert row["geometry_failed_checks"] == ""
        if better_endpoints:
            assert costs[best_middle][0] == 0 and endpoint_best[0] == 0
            first = next(i for i, (a, b) in enumerate(zip(costs[best_middle], endpoint_best)) if a != b)
            assert first >= 2
            effect = (endpoint_best[first] - costs[best_middle][first]) / 1_000_000
            assert abs(effect - float(exported["effect_seconds_vs_mask_endpoints"])) <= 1e-9
            strict_groups.append({"candidate_id": candidate_id,
                                  "case_id": exported["case_id"],
                                  "state": cases[exported["case_id"]]["state"],
                                  "best_middle_mask": best_middle,
                                  "first_differing_objective": OBJECTIVES[first - 2],
                                  "difference_seconds": effect,
                                  "better_than_all_five_simple_interventions": better_simple})
    assert all(case_counts[c] == int(row["mask_sequences"]) for c, row in cases.items())
    assert sum(int(row["mask_rows"]) for row in executions) == len(masks)
    counts = summary["counts"]
    assert len(groups) == counts["mask_sequence_execution_groups"]
    assert len(masks) == counts["mask_rows"]
    assert successful == counts["successful_mask_rows"]
    assert strict_rows == counts["strict_lex_winner_rows_vs_vanilla_J_and_S"]
    assert len(strict_groups) == counts["strict_middle_candidate_groups_vs_mask_endpoints"]
    assert sum(row["better_than_all_five_simple_interventions"] for row in strict_groups) == counts["strict_middle_candidate_groups_vs_all_simple"]
    assert sum(int(row["candidate_groups"]) for row in executions) == counts["candidate_execution_groups"]
    assert len({row["state"] for row in executions}) == summary["distinct_states"]
    for pattern in patterns:
        case_id = pattern["case_id"]
        matches = [row for row in strict_groups if row["case_id"] == case_id]
        assert matches
        for winner in matches:
            row = candidate_rows[winner["candidate_id"]]
            if objective(row["best_middle_objective"])[2:] == tuple(pattern["best_middle_objective_us"]):
                break
        else:
            raise AssertionError("Representative pattern is absent from released candidate rows")
        assert pattern["open_blocks"] == [f"u{bit + 1}" for bit in range(pattern["mutable_blocks"]) if pattern["best_mask"] & (1 << bit)]
        assert objective(row["empty_objective"])[2:] == tuple(pattern["empty_objective_us"])
        assert objective(row["full_objective"])[2:] == tuple(pattern["full_objective_us"])
    witness_rows = witnesses["rows"]
    assert witnesses["checks_passed"]
    assert len(witness_rows) == witnesses["counts"]["plan_records_checked"] == 72
    assert sum(row["endpoints"]["endpoint_checks"] for row in witness_rows) == witnesses["counts"]["endpoint_checks"] == 576
    assert all(row["passed"] and row["projection_matches_saved"] for row in witness_rows)
    assert all(not any(row["issues"].values()) and row["endpoints"]["endpoint_failures"] == 0 for row in witness_rows)
    filenames = ["anonymous_mask_comparisons.csv", "anonymous_candidate_comparisons.csv",
                 "state_execution_counts.csv", "audit_summary.json", "winning_patterns.json",
                 "witness_validation.json"]
    result = {"scope": "CSV arithmetic and exported-label consistency only; no decoder execution, private geometry reconstruction, or independent full-plan validation",
              "analysis_units": "Saved state executions, candidate executions and mask rows are distinct; they are not independent industrial instances.",
              "state_execution_count": len(executions),
              "distinct_states": len({row["state"] for row in executions}),
              "candidate_groups_in_execution_summary": sum(int(row["candidate_groups"]) for row in executions),
              "mask_sequence_execution_groups": len(groups),
              "mask_rows": len(masks), "successful_mask_rows": successful,
              "strict_middle_rows_vs_vanilla_J_and_S": strict_rows,
              "strict_middle_candidate_groups_vs_mask_endpoints": len(strict_groups),
              "strict_middle_candidate_groups_vs_all_simple": sum(row["better_than_all_five_simple_interventions"] for row in strict_groups),
              "strict_middle_differences_seconds": sorted(row["difference_seconds"] for row in strict_groups),
              "winner_states": sorted({row["state"] for row in strict_groups}),
              "winning_candidate_groups": strict_groups,
              "witness_export_consistency": {"plans": len(witness_rows), "endpoints": 576,
                                              "restricted_plan_checks_publicly_replayed": False},
              "input_sha256": {name: hashlib.sha256((ROOT / name).read_bytes()).hexdigest() for name in filenames},
              "passed": True}
    out = ROOT / "reproduced"
    out.mkdir(exist_ok=True)
    (out / "opportunities_recomputed.json").write_text(json.dumps(result, indent=2) + "\n")
    print(json.dumps({k: v for k, v in result.items() if k not in ("winning_candidate_groups", "input_sha256")}, indent=2))


if __name__ == "__main__":
    main()
