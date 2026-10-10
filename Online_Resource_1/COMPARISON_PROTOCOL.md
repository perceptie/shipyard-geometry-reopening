# Executable comparison protocol

The following recording rules were transferred from the pre-edit manuscript's five-step protocol table. They preserve the protocol and evidence requirements; transferring the table does not change the experiments.

| Step | Operation and retained evidence |
|---|---|
| 1 | Bind the source checkpoint, journal prefix, warm start, executable, configuration, seed, thread count, and planned J/S order before execution. |
| 2 | Run both controllers under their actual call-budget and retry policy; retain every feasible and failed invocation. |
| 3 | Compare accepted solve mode, invocation cap, complete crane-sequence signature, and complete occupancy-geometry signature. If any differs, mark the pair ineligible and do not rank its final costs. |
| 4 | For an eligible pair, report observed feasible geometry variation, final adoption, full lexicographic outcome, and the first differing objective level. |
| 5 | Advance each controller through its own commitments for rolling evidence; once states diverge, compare endpoints rather than treating later rounds as paired. |

The recorded-component check above applies to the original paired comparison. In the common-initialization diagnostics, each pair instead uses identical copies of a complete incumbent. Timed improvement phases and fixed-sequence probes have separate stopping conditions.
