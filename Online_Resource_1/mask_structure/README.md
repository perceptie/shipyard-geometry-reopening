# Reopening masks: comparison levels and retained constraints

This extension reanalyses saved decoder outputs; it does not run the proprietary solver.

Run from this directory:

    python3 recompute.py --output ../reproduced/mask_structure

The standard-library script reads `anonymous_inputs.json` and regenerates the summary, candidate/set comparisons, endpoint-consistency table, optimal-mask structures, one-bit edges, objective vectors, and plotting records. `reference_identity.json` records request/reference hashes and task-coverage checks against the restricted originals; it cannot reconstruct those private records.

There are 15 state executions, 510 candidate executions across five interventions, and 90 enumerated candidates with 1656 masks. Candidate signatures were deduplicated and sorted; the first six per execution were enumerated. Other candidates remain comparators, not additional fully enumerated requests. All failures are retained without artificial objective penalties.

The comparator requires successful decoding and a valid objective, then compares projection presence and four integer-microsecond fields: milestone projection, current-batch pool makespan, completion-time sum, and pool value. Deltas are **new minus comparator**. A negative first differing component is better; subsequent components can deteriorate.

Three representative intermediate-mask patterns improve their own endpoints in all three retained executions. Only two improve the best endpoint over six enumerated candidates; only b3-r006 improves the wider pool of all candidates and five interventions, by 13303.319427 s at objective level two. It also beats the common initial plan at level one despite worse later levels. The b2-r096 candidate's 20 s gain comes with 3658 s more aggregate completion time and does not improve the six-candidate best.

Common-open/common-retained fields describe that candidate and decoder. At b3-r071 the eight best masks reopen u2/u6, retain u4, and freely combine u1/u3/u5. Opening u4 is adverse in those best-mask contexts but beneficial on other edges. Each example has a unique minimum-cardinality best set of size two; this is not an online selection rule.

Empty/full masks agree with original S/J success and full objective in all 90 groups, and successful normalized geometry agrees. This is observed sample equivalence, not interchangeable implementations: full-mask reconstruction receives reference-layout seed information.

Historical corrections: the 2026-10-10 reanalysis replaced success-category equality with full-objective comparison and retained execution identity in summary keys. Original records and that analysis remain in `../selective_reopening/`. This edition adds comparison levels and mask structure without overwriting them.
