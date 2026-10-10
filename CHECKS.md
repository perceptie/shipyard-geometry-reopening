# Checks for the 2026-10-10 edition

These checks ran on an independent staging copy before publication. They launched no industrial decoder and regenerated no complete industrial rolling run.

Run from `Online_Resource_1/`:

```sh
python3 selective_reopening/recompute_opportunities.py
python3 e31_records/check_records.py
python3 figures/generate_e11_mechanism.py --output-dir reproduced
python3 validate_terminal_cases.py
python3 check_synthetic_controller_example.py --output reproduced/synthetic_example_checks.json
```

All passed. The selective-mask script confirms 90 saved candidate-execution groups, 1656 masks, 570 successful mask records, 30 strict improvements against vanilla J/S, and nine strict intermediate-mask groups against both endpoints and all five simple interventions. The nine observations repeat three state patterns. The direct-decoder checker confirms the retained 22-second synthetic endpoint difference. The hand-constructed model checker accepts its base plan and detects nine injected faults.

The base statistics and tables were rechecked without regenerating all historical figures:

```sh
uv run --no-project --python 3.12 --with matplotlib==3.11.2 --with numpy==2.5.3 python -c 'import reproduce_figures_and_tables as r; rows = r.load_rows(); r.reproduce_protocol(rows); r.e10_table(rows); r.diagnostic_table_and_checks(); r.rolling_repeat_table_and_checks(); r.condition_table_and_checks(); print("PASS: base E10/E11/E12 arithmetic and table checks; original figures not regenerated")'
```

The source manifest can be checked with:

```sh
shasum -a 256 -c SHA256SUMS
```

The witness-validation summary is copied from the separate restricted-record verification. This public package cannot reproduce those 72 plan checks or 576 endpoint checks without the excluded original records. Its public scripts instead check supplied record arithmetic and labels within their documented scopes.
