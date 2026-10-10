# Online Resource 1: de-identified evaluation evidence and reproduction package

**Manuscript title:** Geometry Reopening in Time-Limited Rolling Shipyard Scheduling: An Industrial Comparative Study  
**Target journal:** The International Journal of Advanced Manufacturing Technology  
**Caption:** De-identified E7/E9/E10 aggregates, E11 common-plan diagnostics, E12 complete rolling runs, terminal cases, and protocol evidence; self-contained scripts recompute the comparison gate, case arithmetic, principal statistics, and data/case figures and result tables. A separate executable synthetic example supplies editable model inputs, a plan, and constraint checks.  
**Authors:** Zixi Wang (first author), Weimin Wu (corresponding author).  
**Affiliation:** The State Key Laboratory of Industrial Control Technology, Institute of Cyber-Systems and Control, Zhejiang University, Hangzhou 310027, China.  
**Contacts:** Zixi Wang — [zixi.wang@zju.edu.cn](mailto:zixi.wang@zju.edu.cn); Weimin Wu — [wmwu@iipc.zju.edu.cn](mailto:wmwu@iipc.zju.edu.cn).  
**Repository:** [perceptie/shipyard-geometry-reopening](https://github.com/perceptie/shipyard-geometry-reopening).  
**Funding:** No specific funding was received for this work.  
**Competing interests:** The authors declare no relevant competing interests.

**Edition:** 2026-10-05 Minor wording and layout revision. The algorithm, released numerical data, experimental protocols, and reported results are unchanged. Figure and table presentation follows the revised manuscript; descriptive reproduction filenames remain stable.

**Additions, 2026-10-10:** the preceding edition describes the preserved base release. This edition adds the revised E11 Figure 7, retained direct-decoder derived records, a saved-record intermediate-mask analysis, and the [executable comparison protocol](COMPARISON_PROTOCOL.md). These additions preserve the original industrial records and involve no new solver/search executions.

## Added reproducibility entries

- `figures/generate_e11_mechanism.py` and `figures/e11_mechanism_input.json`: revised Figure 7 with all three repeat execution counts, ranges and medians, plus common-sequence decode categories. Generate it with `python3 figures/generate_e11_mechanism.py --output-dir reproduced`. The vector PDF uses `rsvg-convert` on `PATH`.
- [e31_records/](e31_records/README.md): de-identified derived outputs from the direct yard-layout/task-time tests, with an executable retained-output checker. Run `python3 e31_records/check_records.py`.
- [selective_reopening/](selective_reopening/README.md): anonymous mask/candidate CSVs, count summaries, representative patterns and an independent public arithmetic script. Run `python3 selective_reopening/recompute_opportunities.py`.
- [COMPARISON_PROTOCOL.md](COMPARISON_PROTOCOL.md): five recording steps transferred intact from the main-text table.

The existing hand-constructed synthetic plan and standalone checker are different from the direct-decoder records. The hand-constructed example is fully editable and can be checked without industrial code. Direct-decoder outputs and intermediate-mask records can be publicly reanalysed, but regenerating their solver outputs requires proprietary code and restricted inputs. Public geometry checks verify transformed records and exported labels within the documented scopes; they are not an industrial solver replay.

This package releases de-identified numeric evidence for the industrial case. Terminal-case task, block, crane, and region aliases are local to each case; times are relative to its decision epoch. Original customer identifiers, coordinates, absolute paths, commands, and host names are not included.

The released reproduction package uses the MIT License; see `LICENSE`. This licence covers the public package files and grants no rights to the proprietary industrial solver or customer source data.

## Files

- `e10_state_outcomes.csv`: all 144 planned J/S pairs, the common-initialization gate components, final five-field stored cost keys (compatibility plus the four formal objective levels), solve modes, invocation caps and counts, audit flags, and the signed current-batch pool makespan difference. Historical field names retain `current_batch_makespan`; this quantity covers only current-batch tasks in the current solve pool, not the entire rolling batch.
- `e10_run_metrics.csv`: all 288 method runs with initialization, candidate/decode, retry, runtime, pool-size, model-scale, and audit fields.
- `e10_runtime_environment.json`: hardware/software environment, timing controls, per-invocation budget semantics, runtime distributions, and the implementation basis for initial-plan equivalence.
- `audit_scope.json`: the distinct coverage and exclusions of the runtime validator, separate checker, independent Cost recomputation, and motion audit.
- `industrial_scale_aggregate.json`: de-identified scale and state-pressure summaries.
- `e10_aggregate.json`: the predeclared three-repeat aggregate over 48 correlated states; the internal records have no external immutable registration timestamp.
- `e9_state_outcomes.csv` and `e9_e10_comparison.json`: the earlier single execution and its explicitly auxiliary comparison with E10.
- `development_budget_aggregate.json`: predetermined development states under research invocation caps of 3, 6, and 12 seconds, including sample counts, timing, and pairwise outcome counts.
- `development_budget_common_subset.json`: the same four predetermined states at all three caps, 36 method records, recomputed supplemental budget-plot statistics, and the original group mappings. Separate caps can reach different initial plans; these medians do not identify a fixed-initialization budget effect. The stable generated basename remains `fig3_budget_sensitivity`.
- `e7_runtime_and_version_evidence.json`: retained E7 invocation caps and attempts, source/build hashes, and the E7/E10 version relationship, freshly inspected on 2026-10-01 without solver reruns.
- `INITIALIZATION_AND_DECODER_AUDIT.md`: effective inputs, nested decode rules, cache and deadline semantics, and the distinction between recorded-component equality and source-supported inference about unrecorded initial timing/motion/Cost.
- `terminal_case_evidence.json`: case-local final task/motion/occupancy summaries for stable positive b3-r006 and negative b3-r071, with source trace hashes. Complete initial schedules and Cost were not retained.
- `validate_terminal_cases.py`: recomputes case arithmetic and checks agreement with the released paired CSV; this does not rerun the solver or independently recover the missing initial schedules.
- `e7_rolling_aggregate.json`: one complete model-internal rolling batch.
- `e11_common_initial_diagnostics.json`: 15 selected-state pairs, complete-incumbent copy signatures, construction and improvement timings, cold initial-plan checks, final objectives, controlling milestone paths, and 282 fixed-sequence decode records. Restricted plans are represented by hashes and de-identified measurements.
- `e11_pair_statistics.csv` and `e11_state_statistics.csv`: per-pair and three-repeat per-state summaries for the common-plan diagnostics.
- `e12_rolling_repeat_summary.json` and `.csv`: the original E7 J/S reference and two new complete first-batch J/S pairs, including parameters, source/output hashes, completion, solver wall time, validation results, and encountered pool/occupancy/tandem profiles.
- `e12_condition_transfer_summary.json` and `.csv`: one complete second-batch J/S comparison from a shared completed LRP first-batch checkpoint, with exact relative checkpoint times and a common boundary fingerprint.
- `generate_case_figures.py`: editable source for the terminal-case timeline/region schematic and physical-constraint illustration. Region membership is schematic; customer coordinates are not released.
- `synthetic_controller_example.json`: entirely synthetic four-task, two-block, three-crane inputs and a hand-constructed plan with complete piecewise-linear trajectories.
- `check_synthetic_controller_example.py`: standard-library-only executable checks of one legal synthetic plan and nine fault controls, with optional JSON report output.
- `checker_controls.json`: synthetic controls for the separate declared-scope checker.
- `reproduce_figures_and_tables.py`: recomputes the common-initialization gate, lexicographic outcomes, and the 144/142/64 analysis denominators; checks released E11/E12 arithmetic and signatures; and reconstructs the data/case figures and all five result tables: E10 outcomes, the original E7 rollout, E11 common-plan diagnostics, E12 first-batch repeats, and E12 second-batch conditions. Table numbers follow their placement in the final manuscript.
- `SHA256SUMS`: hashes of every released input and reproduction script.

## Run the package

Extract the complete supplement ZIP into a writable directory and run the following commands from that directory. The tested plotting environment is **Python 3.12.14, Matplotlib 3.11.2, and NumPy 2.5.3**. The two validation scripts use only the Python standard library. The command below pins the plotting versions and ignores any unrelated parent project:

```bash
uv run --no-project --python 3.12 --with matplotlib==3.11.2 --with numpy==2.5.3 python reproduce_figures_and_tables.py
python3 validate_terminal_cases.py
python3 check_synthetic_controller_example.py --output reproduced/synthetic_example_checks.json
```

If Python 3.12 and the two pinned plotting packages are already installed in an isolated environment, `python reproduce_figures_and_tables.py` is sufficient. Arial was used for the manuscript figures; the scripts fall back to Helvetica or DejaVu Sans when it is unavailable. Numeric results remain reproducible with the fallback, while exact glyph appearance depends on the installed fonts.

Before execution, released files can be checked with `sha256sum -c SHA256SUMS` on Linux or `shasum -a 256 -c SHA256SUMS` on macOS. Each script exits successfully when its checks pass; assertion failures or rejected base examples return a nonzero exit status.

### Expected outputs

All generated files are written under `reproduced/` beside the scripts:

| Output | Contents |
|---|---|
| `eligibility_recomputed.json` | E10 gate fields, synthetic match/mismatch controls, recomputed 144/142/64 denominators, and agreement with released labels. |
| `e11_recomputed.json` | Complete-incumbent signatures, 15-pair outcomes, 282 fixed-probe categories, and diagnostic-summary consistency. |
| `rolling_repeats_recomputed.json` | Original E7 reference and E12 first-batch comparison arithmetic. |
| `condition_recomputed.json` | Shared-boundary consistency and exact checkpoint-relative batch-2 completion and wall-time arithmetic. |
| `terminal_case_checks.json` | Checks of the six retained positive/negative case pairs and agreement with the released paired CSV. |
| `synthetic_example_checks.json` | One legal case and nine deliberate invalid controls: `case_count: 10`, `passed_count: 10`. |
| `table_e10.tex`, `table_rolling.tex`, `table_e11.tex`, `table_rolling_repeats.tex`, `table_condition.tex` | Recomputed numeric contents of all five result tables, including the E11/E12 additions. |
| `fig3_budget_sensitivity`, `fig4_repeat_outcomes`, `fig5_activity_adoption_cross`, `fig6_rolling_endpoints`, `fig7_terminal_cases`, `fig8_physical_constraints` | Each stable basename is generated in PDF and SVG. Its numeric prefix is a historical filename, not the revised publication number; see the mapping below. |

Publication numbering in the 2026-10-10 revised manuscript is:

| Publication figure | Subject | Released output or companion-source asset |
|---|---|---|
| 1 | Physical constraints | `fig8_physical_constraints` |
| 2 | Controller coupling | `fig1_coupling` (companion manuscript source only) |
| 3 | Eligibility-aware evaluation | `fig2_evaluation` (companion manuscript source only) |
| 4 | Repeated paired outcomes | `fig4_repeat_outcomes` |
| 5 | Variation/adoption cross-tabulation | `fig5_activity_adoption_cross` |
| 6 | Terminal-case plans | `fig7_terminal_cases` |
| 7 | E11 repeat counts and common-sequence decoding | `figures/generate_e11_mechanism.py`, `figures/e11_mechanism_input.json` |
| 8 | Complete rolling comparisons | `fig6_rolling_endpoints` |

The development-budget plot `fig3_budget_sensitivity` remains supplemental configuration context.

The development plot uses the same four states at every cap (median accepted improvements 2.5, 4.0, and 5.5); the original mixed-size aggregates remain available. The repeat plot uses two batch panels with J/S/dot/cross symbols. The rolling overview compares four labelled blocks: original E7, E12 first-batch A, E12 first-batch B, and the E12 second-batch condition, showing completion and recorded solver wall time separately. Geometry-adoption counts concern rounds whose final layout differs from that round's own initialization. The terminal-case and physical illustrations are generated from their released records/model specification; the other conceptual publication PDFs are supplied in the companion manuscript source package.

## Common-plan diagnostics (E11)

Five states selected from the earlier E10 outcomes are run three times each. One complete incumbent is constructed once per pair and copied into both policies, including sequence/assignment/tandem bindings, timing, motion, layout/rotation/occupancy, repair state, and Cost. Construction and copying precede independent 12-s improvement clocks; each method starts with a fresh cache. Cold re-decoding of the initial sequence reproduces the same physical plan in all 30 checks after normalization of occupancy ordering and the intended S locking flag. The protocol also probes common initial/final/encountered sequence signatures with the clock stop disabled and the original finite repair bounds retained.

The 15 pairs produce 5 J wins, 3 ties, and 7 S wins. Of 282 signatures deduplicated within each state and repeat, 250 are feasible under both decoders, eight only under J, and 24 only under S. These records distinguish bounded decoder reachability from deadline-limited search effort. The separate restricted-record checks cover 45 common/final plans and 532 feasible probe plans, with 4691 geometry/motion attachment checks. Released scripts verify summary consistency and table arithmetic; they do not replay the restricted plans. E11 is a selected-case mechanism block with a different timing contract from E10 and is not merged into E10's denominators.

## Complete rolling runs (E12)

The retained E7 executable and unchanged inputs/controller parameters are used with seed 42, one solver thread, and the actual 12-s invocation cap. Four first-batch jobs run on distinct physical cores, two J/S pairs with fixed affinity. A further J/S pair starts batch 2 from the same completed LRP first-batch checkpoint on two other physical cores. The shared checkpoint carries 60 locked blocks, three crane endpoints, and 132 occupancy histories. Second-batch completion is measured from its exact checkpoint time, separately from each policy's first-batch runs.

| Evidence block | J completion, s | S completion, s | S-minus-J, h | Solver wall J/S, s |
|---|---:|---:|---:|---:|
| Original E7 reference | 5448089 | 5530327 | 22.84 | 2534.236 / 2341.922 |
| E12 first-batch A | 5446758 | 5404003 | -11.88 | 1653.361 / 1594.592 |
| E12 first-batch B | 5455756 | 5401166 | -15.16 | 1667.595 / 1570.844 |
| E12 second-batch condition | 4936987.541039 | 5037459.663266 | 27.91 | 2566.147 / 2269.664 |

All six new runs reach complete termination, pass final field validation, and pass the separate declared-scope checks for every feasible output. Original E7 results remain unchanged and are labelled separately because the historical execution did not fix affinity. E12 supplies complete comparisons across repeats and a second carried-state/task-mix condition; later pools and resource states evolve with each policy's decisions.

## Executable synthetic example

The editable JSON contains fixed model inputs and a hand-constructed four-task plan with complete trajectories. Running the checker accepts this legal plan and tests nine deliberate invalid variants; **10/10** means that the legal plan is accepted and every injected fault is detected. The controls are:

| Control | Required detection |
|---|---|
| Legal half-open release and tandem plan | Accepted with no issue. |
| Layout/motion attachment mismatch | `layout_attachment` |
| Early occupancy release | `occupancy_release` |
| Positive-area spatiotemporal overlap | `yard_overlap` |
| Precedence violation | `precedence` |
| Unqualified crane | `assignment` |
| Nonadjacent tandem pair | `tandem_binding` |
| Asynchronous tandem hold | `phase_binding` |
| Rail crossing | `rail_order` |
| Deleted loaded motion | `phase_binding` |

Fault variants may trigger additional related issues; each must include the named required detection. To test a modified input or plan without the bundled faults, save a copy of the JSON and run:

```bash
python3 check_synthetic_controller_example.py edited_example.json --skip-controls
```

The example checks model semantics: precedence/dwell, crane qualifications and synchronized tandem binding, footprint containment, persistent half-open occupancy, placement-derived pickup/drop attachment, travel phases, and continuous piecewise-linear rail X-order. It illustrates the supplied plan rather than constructing a plan with Beam/VND; algorithmic search and the industrial comparison are documented by the separate protocols and E10/E11/E12 records.

Plotting and example code was revised with OpenAI Codex assistance. Both authors have reviewed the manuscript text, figures, analyses, code, and AI-assistance disclosure. E10 contains 48 serially correlated states from one LRP source trajectory with three wall-clock repeats. The rolling results are model-internal production-controller outcomes.

The internal `build_supplement.py` used to export these files is deliberately excluded from the public zip because it requires restricted trace and audit inputs that cannot be redistributed. It is an aggregate exporter, not a self-contained raw-data generator. The released reproduction script is self-contained with respect to the released numeric files.

For E10, the shared-configuration comparison covers the common executable, solver options, seed, and thread count; the J/S flag records the intended treatment. Matching source/configuration, mode, cap, complete sequence (including assignment/tandem binding), and untimed geometry establishes recorded-component equality. Initial timing, motion, repair state, and Cost were not independently signed or replayed in E10. Their equivalence is supported by the source-inspection note. The new E11 protocol directly copies and signs the complete initial incumbent and checks its cold physical re-decode; its separate clocks equalize the allowed improvement time while measuring the candidate counts that result.
