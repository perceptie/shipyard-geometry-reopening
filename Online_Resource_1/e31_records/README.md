# Direct-decoder retained records

These eight JSON files are derived from the saved stage 6–13 direct-decoder outputs. They do not contain the proprietary decoder, probe binaries, original region identifiers, absolute coordinate frame or industrial source input.

Placement rectangles are expressed in a separate translated frame for each stage. Translation preserves synthetic block size, relative placement, overlap and geometry equality. All 200 recorded microsecond timing fields are unchanged. Stage 6 used an actual region identifier and region extents in its original restricted input; these are excluded here. That file retains two Boolean containment predicates exported from checks against the original widened region. They cannot be independently reconstructed without the restricted original region.

```sh
python3 check_records.py
```

The checker recomputes retained-output relationships, release transitions at −1/0/+1 microseconds, four-mask geometry groups and their 1452/1474-second endpoints, and missing-external-timing rejection. It reads the original containment predicates as exported evidence. It does not call the decoder or verify a complete rolling state, outer shared-rail repair or field safety. Recreating the original decoder outputs requires the proprietary implementation; public reproducibility is limited to the supplied derived records and checks.

The test layer directly invoked yard-layout and task-time decoding with a 64-iteration field fixed-point limit. It did not run Beam/VND, outer retry or the outer shared-rail repair procedure. Microsecond offsets test integer event-boundary semantics, rather than field control precision. Reopening permission, changed geometry and completion quality remain separate measurements.
