# E32: a controlled improvement-budget comparison

Four states, two allowances, two geometry policies, and three repeats give 48 timed search phases. One complete incumbent is constructed per state, then copied to every phase. Fresh layout/candidate caches, seed 42, one candidate thread, the same neighbourhood rules and 64/256 iteration limits are used. Processes run serially on logical CPU 12. Budget and policy order alternate. No online selector or new complete rollout is implemented.

The allowances are 12 s and max(0, 12 s minus the measured construction segment). That segment begins **after input adaptation** and ends after Beam returns a complete incumbent and final decoding/cost evaluation. It excludes input adaptation, earlier failed calls, copying, and outer-controller overhead. The unchanged pre-run `preregistered_protocol_zh.md` used a less precise phrase for this boundary; the implementation and this definition determine the measurement. It is not a replay of E10 total response time. Actual phase elapsed times are retained; the largest stop overshoot is 0.010993 s.

Development states are b3-r006/b3-r071. Input-only selection excludes the earlier five diagnostic states, requires at least three tasks/two mutable blocks, and chooses the first stable identifier in each batch: b2-r051/b3-r031. `selection.json` retains all screening records. These are additional states from the same industrial model and trajectory, not independent shipyard data. The separate one-repeat preliminary check is not part of this release's formal counts.

- `summary.json`: 52 initial/final plan checks, 429 endpoint checks, state initialization hashes and all paired rankings.
- `search_phases.csv`: all 48 final four-level objectives, actual allowances/elapsed times, candidate counts, and result hashes.
- `strict_improvements.csv`: all 369 strict-improvement events with monotonic elapsed time and full objective vector.
- `execution_provenance.json`: actual overlay/binary hashes, serial core binding, input hashes and complete process timing. The older source baseline is distinct from this actual-run manifest.
- `check_records.py`: portable standard-library recheck of event monotonicity, final-objective identity, allowance formula, and 24 pair rankings. It does not regenerate private plans or rerun the proprietary solver.

Run:

    python3 check_records.py --output ../reproduced/controlled_budget_checks.json

At b3-r006, the 8.303348-s allowance favours J by 233.326755 s in all repeats; 12 s favours S by 519 s in all repeats. S's decisive final improvements occur at 11.304651–11.790254 s. At b3-r071 S wins under both allowances; the last 12-s repeat wins at objective tier three, not tier two. Both input-selected states tie under both allowances; their construction segments leave small budget differences. Same candidate-generation rules do not imply identical visited candidate sets or prefix-equivalent timed searches.

Figure reproduction is in `../figures/generate_budget_effect.py`. Curves use actual step events, match first objective before displaying the second, and explicitly use a local 0–1000 s excess window. Complete earlier events remain in the CSV. No confidence intervals or interpolated budget sweep are implied.
