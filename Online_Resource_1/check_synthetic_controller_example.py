#!/usr/bin/env python3
"""Check the editable synthetic model in synthetic_controller_example.json.

Standard-library-only executable example of the declared model semantics.
It checks a supplied plan; it does not implement Beam/VND, the industrial
decoder, search optimality, calendars, execution commitment or a safety model.
Run: python3 check_synthetic_controller_example.py [edited_example.json]
Use --skip-controls to validate only an edited input/plan, or --output to save
the JSON report. Invalid plans or failed fault-detection controls return 1.
"""

from __future__ import annotations

import argparse
from copy import deepcopy
import hashlib
import json
import math
from pathlib import Path
from typing import Any

EPS = 1e-9


def equal(a: float, b: float) -> bool:
    return abs(a - b) <= EPS


def same_point(a: list[float], b: list[float]) -> bool:
    return len(a) == len(b) == 2 and all(equal(x, y) for x, y in zip(a, b))


def interval_overlap(a: tuple[float, float], b: tuple[float, float]) -> bool:
    """Positive-length overlap of half-open intervals; contact is permitted."""
    return max(a[0], b[0]) < min(a[1], b[1]) - EPS


def rectangle_overlap(a: list[float], b: list[float]) -> bool:
    return (interval_overlap((a[0], a[0] + a[2]), (b[0], b[0] + b[2]))
            and interval_overlap((a[1], a[1] + a[3]), (b[1], b[1] + b[3])))


def position(segment: dict[str, Any], t: float) -> list[float]:
    if equal(segment["start"], segment["end"]):
        return list(segment["to"])
    ratio = (t - segment["start"]) / (segment["end"] - segment["start"])
    return [a + ratio * (b - a) for a, b in zip(segment["from"], segment["to"])]


def position_at(motions: list[dict[str, Any]], t: float) -> list[float] | None:
    for segment in motions:
        if segment["start"] - EPS <= t <= segment["end"] + EPS:
            return position(segment, t)
    return None


def travel(a: list[float], b: list[float], crane: dict[str, Any]) -> int:
    # Concurrent X/Y travel, rounded up to whole seconds.
    return math.ceil(max(abs(b[0] - a[0]) / crane["speed_x"],
                         abs(b[1] - a[1]) / crane["speed_y"]) - EPS)


def check(document: dict[str, Any]) -> list[dict[str, str]]:
    inp, plan = document["input"], document["plan"]
    issues: list[dict[str, str]] = []

    def issue(code: str, detail: str) -> None:
        issues.append({"code": code, "detail": detail})

    tasks, cranes = inp["tasks"], inp["cranes"]
    order = inp["rail_order"]
    start_h, end_h = inp["horizon"]
    if set(plan["tasks"]) != set(tasks):
        issue("pool_coverage", "Plan task set differs from input task set.")

    for crane_id, crane in cranes.items():
        motions = plan["motions"].get(crane_id, [])
        cursor, endpoint = start_h, crane["initial_position"]
        if crane["speed_x"] <= 0 or crane["speed_y"] <= 0:
            issue("input", f"{crane_id}: crane speed must be positive.")
        for segment in motions:
            if segment["phase"] not in ("empty", "hold", "loaded", "idle"):
                issue("phase_binding", f"{crane_id}: unknown motion phase.")
            if segment["end"] <= segment["start"] or not equal(segment["start"], cursor):
                issue("motion_continuity", f"{crane_id}: nonpositive segment, gap or temporal overlap.")
            if not same_point(segment["from"], endpoint):
                issue("motion_continuity", f"{crane_id}: disconnected motion endpoints.")
            if segment["task"] is not None:
                task_id = segment["task"]
                record = plan["tasks"].get(task_id)
                if record is None or crane_id not in record["cranes"]:
                    issue("phase_binding", f"{crane_id}: motion bound to an unassigned task {task_id}.")
            elif segment["phase"] != "idle":
                issue("phase_binding", f"{crane_id}: unnamed motion must be labelled idle.")
            cursor, endpoint = segment["end"], segment["to"]
        if not equal(cursor, end_h):
            issue("motion_continuity", f"{crane_id}: trajectory does not cover the complete horizon.")

    for task_id, task in tasks.items():
        if task_id not in plan["tasks"]:
            continue
        record = plan["tasks"][task_id]
        assigned = record["cranes"]
        tandem = task["kind"] == "tandem"
        if tandem:
            if (assigned not in task["allowed_pairs"] or len(assigned) != 2
                    or any(c not in order for c in assigned)
                    or abs(order.index(assigned[0]) - order.index(assigned[1])) != 1):
                issue("tandem_binding", f"{task_id}: tandem pair is not permitted and adjacent.")
        elif len(assigned) != 1 or assigned[0] not in task["allowed_cranes"]:
            issue("assignment", f"{task_id}: ordinary task uses an unqualified crane.")
        if (record["start"] < start_h or record["end"] > end_h
                or any(record[p] < 0 for p in ("empty", "hold", "loaded"))
                or not equal(record["end"], record["start"] + record["empty"] + record["hold"] + record["loaded"])
                or not equal(record["hold"], task["hold"])):
            issue("task_time", f"{task_id}: inconsistent start, end or phase durations.")
        for arc in task["predecessors"]:
            pred = plan["tasks"].get(arc["task"])
            if pred is None or record["start"] < pred["end"] + arc["lag"] - EPS:
                issue("precedence", f"{task_id}: predecessor {arc['task']} plus lag is not respected.")

        phase_bounds = {
            "empty": (record["start"], record["start"] + record["empty"]),
            "hold": (record["start"] + record["empty"], record["start"] + record["empty"] + record["hold"]),
            "loaded": (record["start"] + record["empty"] + record["hold"], record["end"]),
        }
        empty_times, loaded_times = [], []
        for crane_id in assigned:
            if crane_id not in cranes or crane_id not in task["pickup"]:
                issue("assignment", f"{task_id}: no input coordinates for assigned crane {crane_id}.")
                continue
            motions = plan["motions"].get(crane_id, [])
            initial = position_at(motions, record["start"])
            if initial is not None:
                empty_times.append(travel(initial, task["pickup"][crane_id], cranes[crane_id]))
            loaded_times.append(travel(task["pickup"][crane_id], task["drop"][crane_id], cranes[crane_id]))
            for phase, (a, b) in phase_bounds.items():
                segments = [s for s in motions if s["task"] == task_id and s["phase"] == phase]
                if equal(a, b):
                    if segments:
                        issue("phase_binding", f"{task_id}/{crane_id}: zero-duration {phase} must have no positive segment.")
                    continue
                if len(segments) != 1 or not equal(segments[0]["start"], a) or not equal(segments[0]["end"], b):
                    issue("phase_binding", f"{task_id}/{crane_id}: {phase} does not cover the common phase interval.")
                    continue
                segment = segments[0]
                if phase == "empty" and not same_point(segment["to"], task["pickup"][crane_id]):
                    issue("phase_geometry", f"{task_id}/{crane_id}: empty movement does not reach pickup.")
                if phase == "hold" and not (same_point(segment["from"], task["pickup"][crane_id]) and same_point(segment["to"], task["pickup"][crane_id])):
                    issue("phase_geometry", f"{task_id}/{crane_id}: hold does not remain at pickup.")
                if phase == "loaded" and not (same_point(segment["from"], task["pickup"][crane_id]) and same_point(segment["to"], task["drop"][crane_id])):
                    issue("phase_geometry", f"{task_id}/{crane_id}: loaded movement has incorrect endpoints.")
        if empty_times and not equal(record["empty"], max(empty_times)):
            issue("travel_duration", f"{task_id}: empty duration does not equal rounded parallel travel (tandem maximum where applicable).")
        if loaded_times and not equal(record["loaded"], max(loaded_times)):
            issue("travel_duration", f"{task_id}: loaded duration does not equal rounded parallel travel (tandem maximum where applicable).")

    for crane_id in cranes:
        expected = sorted((t for t, r in plan["tasks"].items() if crane_id in r["cranes"]),
                          key=lambda t: (plan["tasks"][t]["start"], t))
        sequence = plan["sequences"].get(crane_id, [])
        if sequence != expected:
            issue("sequence", f"{crane_id}: sequence does not match assigned tasks in start order.")
        for left, right in zip(expected, expected[1:]):
            if interval_overlap((plan["tasks"][left]["start"], plan["tasks"][left]["end"]),
                                (plan["tasks"][right]["start"], plan["tasks"][right]["end"])):
                issue("crane_capacity", f"{crane_id}: tasks {left} and {right} overlap.")

    occupancies = plan["occupancies"]
    if set(occupancies) != set(inp["blocks"]):
        issue("occupancy_coverage", "Occupancy block set differs from input block set.")
    for block_id, block in inp["blocks"].items():
        if block_id not in occupancies:
            continue
        occupancy = occupancies[block_id]
        entry_start = min(plan["tasks"][t]["start"] for t in block["entry_tasks"])
        if not equal(occupancy["start"], entry_start):
            issue("occupancy_start", f"{block_id}: occupancy does not start at earliest entry.")
        erection = plan["tasks"].get(block["erection_task"])
        release = None if erection is None else erection["start"] + erection["empty"] + erection["hold"]
        if ((release is None) != (occupancy["end"] is None)
                or (release is not None and not equal(occupancy["end"], release))):
            issue("occupancy_release", f"{block_id}: occupancy end must be loaded-movement start, or open if erection is outside the pool.")
        if erection is not None and erection["start"] < entry_start + block["dwell"] - EPS:
            issue("dwell", f"{block_id}: erection starts before required dwell from first entry.")
        x, y, w, h = occupancy["rectangle"]
        centre = [x + w / 2, y + h / 2]
        for entry_id in block["entry_tasks"]:
            for crane_id in plan["tasks"][entry_id]["cranes"]:
                point = inp["tasks"][entry_id]["drop"].get(crane_id)
                if point is not None and not same_point(point, centre):
                    issue("layout_attachment", f"{block_id}/{entry_id}: entry drop differs from the final rectangle centre.")
        erection_id = block["erection_task"]
        if erection_id is not None and erection_id in plan["tasks"]:
            for crane_id in plan["tasks"][erection_id]["cranes"]:
                point = inp["tasks"][erection_id]["pickup"].get(crane_id)
                if point is not None and not same_point(point, centre):
                    issue("layout_attachment", f"{block_id}/{erection_id}: erection pickup differs from the final rectangle centre.")
        footprint = block["footprint"]
        if not (same_point([w, h], footprint) or same_point([w, h], list(reversed(footprint)))):
            issue("block_footprint", f"{block_id}: footprint differs from fixed dimensions and their 90-degree rotation.")
        bx, by, bw, bh = inp["yard"]["rectangle"]
        if w <= 0 or h <= 0 or x < bx - EPS or y < by - EPS or x + w > bx + bw + EPS or y + h > by + bh + EPS:
            issue("yard_containment", f"{block_id}: rectangle is outside the yard or has nonpositive dimensions.")
        if occupancy["end"] is not None and occupancy["end"] < occupancy["start"] - EPS:
            issue("occupancy_interval", f"{block_id}: release precedes entry.")
    block_ids = sorted(occupancies)
    for i, left in enumerate(block_ids):
        a = occupancies[left]
        for right in block_ids[i + 1:]:
            b = occupancies[right]
            a_interval = (a["start"], math.inf if a["end"] is None else a["end"])
            b_interval = (b["start"], math.inf if b["end"] is None else b["end"])
            if interval_overlap(a_interval, b_interval) and rectangle_overlap(a["rectangle"], b["rectangle"]):
                issue("yard_overlap", f"{left}/{right}: positive-area overlap while half-open occupancy intervals overlap.")

    # The X-order difference is linear on each interval formed by the union
    # of trajectory breakpoints. Checking both endpoints is exact here.
    breaks = sorted({start_h, end_h} | {s[k] for c in order for s in plan["motions"].get(c, []) for k in ("start", "end")})
    separation = inp["minimum_x_separation"]
    for left, right in zip(order, order[1:]):
        for t in breaks:
            a = position_at(plan["motions"].get(left, []), t)
            b = position_at(plan["motions"].get(right, []), t)
            if a is not None and b is not None and a[0] + separation > b[0] + EPS:
                issue("rail_order", f"{left}/{right}: X order violated at t={t:g}.")
                break
    return issues


def mutate(document: dict[str, Any], operations: list[dict[str, Any]]) -> dict[str, Any]:
    result = deepcopy(document)
    for operation in operations:
        target = result
        for key in operation["path"][:-1]:
            target = target[key]
        key = operation["path"][-1]
        if operation["op"] == "set":
            target[key] = deepcopy(operation["value"])
        elif operation["op"] == "remove":
            del target[key]
        else:
            raise ValueError(f"Unknown mutation operation: {operation['op']}")
    return result


def main() -> int:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("example", nargs="?", type=Path, default=Path(__file__).with_name("synthetic_controller_example.json"))
    parser.add_argument("--skip-controls", action="store_true", help="Check only the editable base input/plan.")
    parser.add_argument("--output", type=Path, help="Save the JSON report at this path.")
    args = parser.parse_args()
    raw = args.example.read_bytes()
    document = json.loads(raw)
    base_issues = check(document)
    cases = [{"name": "legal_half_open_release_and_tandem", "expected": "valid", "observed_issues": base_issues, "passed": not base_issues}]
    if not args.skip_controls:
        for control in document.get("invalid_controls", []):
            issues = check(mutate(document, control["mutations"]))
            codes = {i["code"] for i in issues}
            cases.append({"name": control["name"], "expected": "invalid", "required_issues": control["expected_issues"],
                          "observed_issues": issues, "passed": bool(issues) and set(control["expected_issues"]).issubset(codes)})
    report = {"example_sha256": hashlib.sha256(raw).hexdigest(), "scope": document["purpose"],
              "case_count": len(cases), "passed_count": sum(c["passed"] for c in cases), "cases": cases}
    encoded = json.dumps(report, indent=2, ensure_ascii=False) + "\n"
    print(encoded, end="")
    if args.output:
        args.output.write_text(encoded, encoding="utf-8")
    return 0 if all(c["passed"] for c in cases) else 1


if __name__ == "__main__":
    raise SystemExit(main())
