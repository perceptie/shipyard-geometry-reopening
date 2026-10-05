# Initialization and decoder source review

## Scope and version

This document reports a **source review performed on 2026-10-01**, not a new independent reproduction of complete initial plans. The reviewed formal source is commit `5ecc07be32a2358e96748939f5083f614d0c0c96`. E7 and E10 use byte-identical solver overlays, `formal_solver_engine.cpp`, with SHA-256 `88cac275f3148440fef2e529d06a09587b24ec246da5ec2ff4d69795bd6842e9`. This identity does not imply identical rolling-controller overlays, invocation budgets, or experimental protocols.

Source references below identify filenames and line numbers in that version; “overlay” denotes the research solver file. No solver experiment or cache regression test was executed for this review. Source references document the implementation inspected by the authors; they do not imply that the proprietary source is included in this supplement.

## Effective inputs

Successful initial decoding depends on the following inputs, beyond the sequence and rectangle signatures:

1. **Instance and objective:** accepted task pool/current batch; task identities, kinds, fixed lift durations and priorities; precedence edges/lags, dwell relations and milestone DAG; material entry points selected using the solve seed; block dimensions/orientations, dock targets, yard regions and safety gaps; crane qualifications, coverage, speeds and rail topology.
2. **Checkpoint constraints:** executed/frozen task times; material release bounds; crane available-at times, idle positions and fixed-prefix endpoints; available/unavailable operating intervals and disabled cranes; locked occupancy rectangles and intervals.
3. **Construction and execution settings:** warm-start sequences/assignments, Beam width, stable ordering keys, accepted retry mode, invocation cap, executable/shared options, seed, thread count, repair limits, and cancellation/deadline callback.
4. **Candidate-local state:** current rectangles, the completed initial field solution, incremental timing seed, task start bounds, intermediate/terminal rail yields, conflict-repetition counters, and memoized decoder results.

The adapter constructs these requests from the shared instance and checkpoint (`formal_candidate_input.cpp:90–257,273–463,467–520`). Warm starts retain qualified assignments and relative sequence order and are decoded again; they do not restore a previous timing or geometry solution (`initial_solution.cpp:386–483`). Geometry freezing begins only after the initial plan is accepted (overlay:536–581).

## Decoder order and bounds

Candidate decoding nests a field fixed point inside rail repair (`candidate_decoder.cpp:68–152,206–254`). Mutable blocks are initially seeded independently. Each field iteration derives pickup/drop and tandem geometry, decodes task times, reconstructs occupancy intervals, and replans mutable rectangles. Ready tasks use ascending task identifiers. Occupancy ends at the erection lift's loaded-move start, or remains open if that lift is outside the decoded pool. Geometry convergence compares block identity, region, physical rectangle and rotation; 64 unsuccessful iterations cause heuristic failure (`field_aware_decoder.cpp:74–110,351–600`; `task_time_decoder.cpp:384–465`).

Placement orders blocks by occupancy start, descending priority, business key and identifier. Regions are ranked by loaded entry-travel cost. For each distinct 0/90-degree footprint, candidate coordinates combine region minima with right/top edges of temporally overlapping occupancies. Invalid coverage, boundary and overlap candidates are rejected. Remaining positions are ranked by region rank, Y, X, rotation and region identifier (`site_layout_planner.cpp:369–480`; `field_aware_decoder.cpp:266–348`). This finite Bottom-Left rule is not exhaustive continuous placement.

Rail repair selects the earliest adjacent-crane conflict using stable identifier/time tie-breaks. It tries delaying either movable task and applicable outward idle-crane yields. Repeated conflicts trigger stronger serialization from the third recurrence. Each trial re-decodes field and timing. Selection prefers avoiding the same idle crossing, then no remaining conflict, then a later next conflict, then smaller makespan and a stable trial key. The limits are 256 repair iterations and four terminal-yield stabilization passes; unresolved conflicts cause heuristic failure (`shared_rail_repair.cpp:283–297,784–1188`). A final field decode updates the layout under accepted repairs.

## Cache and deadline mechanisms

**Final layout and retained motion correspondence.** The runtime validator is part of controller acceptance. Separately, the E10 Python checker (`audit_trace.py:159–280,338`) reconstructs entry drop and erection pickup points from each final physical rectangle, including tandem attachment points, and compares them with retained empty/hold/loaded motion endpoints. It also verifies phase timing and recomputes travel durations. The CLI combines these geometry-phase checks with its other declared checks. These are part of the original 288-run separate-checker result, rather than a new runtime-validation step. The manuscript's revised Table 2 distinguishes the C++ acceptance checks from this post-run correspondence check.

- **Candidate cache:** invocation-local, capacity 256, keyed by complete crane sequences/tandem binding. The adapted state is fixed within that invocation. It is cleared before J/S improvement search. Success entries contain completed results; failure entries cannot become feasible initial plans (overlay:270–277,326–409,575–581).
- **Layout cache:** capacity 8192, shared across retries/rounds within one process. Hash lookup also requires full equivalence-class equality: canonical geometry/requests, placement order and interval-overlap pattern. Current interval endpoints are restored on retrieval (`site_layout_planner.cpp:172–311,545–614`; E10 `rolling_main.cpp:789–790,1368–1372`).
- **Rail cache:** candidate-local, keyed by all start bounds and intermediate yields; terminal yields are applied after retrieval. Interrupted results are not inserted (`shared_rail_repair.cpp:34–63,680–724`).
- **Incremental timing:** candidate-local. Reuse checks graph, dwell, sequences, cranes/speeds, external timing, availability/calendars and disabled cranes. Changed task geometry, bounds or yields invalidate affected tasks and their graph/crane/dwell successors; otherwise decoding falls back to the full procedure (`task_time_decoder.cpp:836–1100`).
- **Stopping:** checks surround field iterations, timing/layout updates and rail trials. Interrupted decoding returns failure, not a partially repaired accepted plan. Final field re-decoding also checks stopping. Beam interruption can trigger another retry. An already completed cached candidate can remain usable after the clock advances (`field_aware_decoder.cpp:429–600`; `candidate_decoder.cpp:206–244`; `initial_solution.cpp:502–643`). Cache residency and system timing can therefore affect acceptance, retry paths and remaining search time.

## Recorded equality versus inferred equality

The historical gate compares source/configuration, accepted mode/cap, complete sequences/assignment/tandem binding, and block/region rectangle signatures. Rectangle signatures omit occupancy times and explicit rotation; non-square dimensions identify the permitted orientation, and square footprints generate only one orientation (overlay:132–148; `field_layout.cpp:148–165`).

## Execution and provenance details retained from the main text

E7 and E10 use the same frozen formal revision and byte-identical solver, rolling-controller, method-selection, instrumentation-state, and warm-start sources, but different executable builds. E10 adds graph and target context to post-solve trace export for independent objective recomputation; the inspected changes do not alter search or controller rules. Export occurs outside the invocation deadline but contributes to outer wall time. The executable/source hashes and budget derivation are retained in this package; the rolling case remains a separate single-trajectory comparison.

Every run has a planned record and a final content-addressed record binding its checkpoint, journal prefix, warm-start input, executable, configuration, output, and verification results. The provenance includes content hashes and pre/post records but no external immutable timestamp. These records identify the retained artifacts; they are not an independent external certification of when a run occurred.

## Waiting-time conventions and candidate filtering

In the frozen formal revision used by E10 (`5ecc07be32a2358e96748939f5083f614d0c0c96`), `task_time_decoder.cpp:427–454,484–525,728–763` applies task-start lower bounds, non-task yields, and operating-window shifts before an ordinary task's three consecutive phases. Rail-repair wait-direction updates raise these lower bounds and re-decode. A yield can therefore postpone the task start without adding an internal waiting phase to its duration.

For tandem tasks, `task_time_decoder.cpp:551–616,644–690` synchronizes the start and uses the maximum empty travel and maximum loaded travel of the pair. The faster crane's explicit pickup and destination waits are within those synchronized phases. Yard occupancy ends at the common loaded-movement start, computed by `field_aware_decoder.cpp:101–105` as start plus empty-motion duration plus basic lift duration. The manuscript's duration and occupancy equations need no separate waiting term.

Beam construction discards failed decodes (`initial_solution.cpp:520–527`), checks coverage and objective validity, and then deduplicates successful candidates using complete sequence signatures before retaining the best eight (`initial_solution.cpp:647–657`). Rejection by this bounded procedure is a decode failure, not a proof of mathematical infeasibility. The 2026-10-05 check read only these frozen implementation functions; it launched no solver run and changed no source.

## Terminal-case task labels and the displayed crane window

All labels below are case local. In b3-r006, tasks T1–T8 map to blocks B2, B3, B6, B4, B5, B1, B5, B3; in b3-r071 they map to B2, B3, B1, B4, B1, B7, B6, B5. These mappings are directly stored in the released terminal records. The changed blocks B2, B4, and B6 in b3-r006 correspond to T1, T4, and T3, respectively.

Across all 12 case–repeat–method terminal plans, C3 has no assigned task. Its only retained non-task movement in b3-r006 precedes the decision epoch, and b3-r071 has no such C3 movement. C3 is omitted from the displayed non-negative-time task timelines for this reason; it remains part of the shared-rail physical model. Region-assignment panels are schematic and do not display actual block coordinates or orientation changes.

Passing the gate establishes equality of these **recorded components**. Equality of initial timing, motion and Cost is an implementation-based inference under common effective inputs and the completed single-thread decoding rules. Initial timing, motion, repaired bounds and Cost were not independently hashed or retrospectively reconstructed. The review found no additional concrete mismatch, but cannot certify unrecorded historical outputs. The gate also does not equalize construction time, remaining VND time, or candidate count.
