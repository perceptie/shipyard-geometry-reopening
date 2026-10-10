"""Check retained, translated E31 records without the proprietary decoder."""
from pathlib import Path
import json

ROOT = Path(__file__).resolve().parent


def read(phase):
    return json.loads((ROOT / f"phase{phase}.json").read_text())


def geometry(occupancy):
    return {k: occupancy[k] for k in
            ("region_id", "actual_rect", "occupied_rect", "rotation")}


def blocks(run):
    return {v["grand_block_id"]: v for v in run["occupancies"]}


def overlaps(a, b):
    return (a["min_x"] < b["max_x"] and b["min_x"] < a["max_x"]
            and a["min_y"] < b["max_y"] and b["min_y"] < a["max_y"])


def main():
    records = [read(n) for n in range(6, 14)]
    for record in records:
        assert record["presentation_transform"]["recorded_times_unchanged"]
        for run in record["runs"]:
            if not run["feasible"]:
                continue
            occupancies = run.get("occupancies", [run["occupancy"]] if "occupancy" in run else [])
            for i, a in enumerate(occupancies):
                for b in occupancies[i + 1:]:
                    temporal = (a["active_from_us"] < b["active_until_us"]
                                and b["active_from_us"] < a["active_until_us"])
                    assert not (temporal and overlaps(a["occupied_rect"], b["occupied_rect"]))

    boundary = read(6)
    runs = {(r["variant"], r["method"]): r for r in boundary["runs"]}
    reference = runs["G0", "J_free"]["occupancy"]
    free = runs["G_minus2m", "J_free"]["occupancy"]
    locked = runs["G_minus2m", "S_locked_O0"]["occupancy"]
    assert free["actual_rect"]["min_x"] - reference["actual_rect"]["min_x"] == -2000000
    assert geometry(locked) == geometry(reference)
    # Original industrial region extents are restricted. These exported
    # predicates record checks against the retained original rectangle.
    containment = boundary["original_widened_region_containment_checks"]
    assert {r["rectangle_field"] for r in containment} == {"actual_rect", "occupied_rect"}
    assert all(r["contained_in_original_widened_region"] for r in containment)

    for phase in (10, 11):
        data = read(phase)
        release = data["timing"]["a_release_us"]
        variants = {r["variant"]: r for r in data["runs"]}
        for delta, region in ((-1, "probe-region-b"), (0, "probe-region-a"), (1, "probe-region-a")):
            run = variants[f"delay_{release + delta}"]
            b = blocks(run)["probe-grand-block-b"]
            assert b["region_id"] == region
            assert b["active_from_us"] == release + delta

    masks = {r["variant"]: r for r in read(12)["runs"]}
    signatures = {k: {b: geometry(v) for b, v in blocks(r).items()} for k, r in masks.items()}
    assert signatures["R_empty"] == signatures["R_A"]
    assert signatures["R_B"] == signatures["R_AB"]
    assert signatures["R_empty"] != signatures["R_AB"]
    assert masks["R_empty"]["makespan_us"] == masks["R_A"]["makespan_us"] == 1452000000
    assert masks["R_B"]["makespan_us"] == masks["R_AB"]["makespan_us"] == 1474000000
    assert masks["R_AB"]["makespan_us"] - masks["R_empty"]["makespan_us"] == 22000000
    missing = [r for r in read(13)["runs"] if r["variant"] == "missing_external_timing"]
    assert len(missing) == 1 and not missing[0]["feasible"] and missing[0]["diagnostic"] is not None
    print(json.dumps({"phase_record_count": 8, "mask_distinct_geometry_count": 2,
                      "mask_completion_difference_seconds": 22, "passed": True,
                      "scope": "retained output checks; no decoder or industrial plan regeneration"}, indent=2))


if __name__ == "__main__":
    main()
