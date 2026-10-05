# Shipyard geometry reopening: reproduction package

**Manuscript:** Geometry Reopening in Time-Limited Rolling Shipyard Scheduling: An Industrial Comparative Study  
**Target journal:** The International Journal of Advanced Manufacturing Technology  
**Authors:** Zixi Wang (first author), Weimin Wu (corresponding author).  
**Affiliation:** The State Key Laboratory of Industrial Control Technology, Institute of Cyber-Systems and Control, Zhejiang University, Hangzhou 310027, China.  
**Contacts:** Zixi Wang — [zixi.wang@zju.edu.cn](mailto:zixi.wang@zju.edu.cn); Weimin Wu — [wmwu@iipc.zju.edu.cn](mailto:wmwu@iipc.zju.edu.cn).  
**Repository:** [perceptie/shipyard-geometry-reopening](https://github.com/perceptie/shipyard-geometry-reopening).

The public release contains de-identified evaluation aggregates, case-local terminal-plan records, figure/table reproduction scripts, and an editable synthetic model example. The companion package is placed in `Online_Resource_1/`; its README describes each released file and the expected outputs. Customer source data, private industrial solver code, and restricted full execution records are excluded.

The 2026-10-05 Minor revision updates figure labels, common count scales, terminal-case detail views, and grouped result-table headers. It preserves all 22 released JSON/CSV numerical records and their provenance. Stable reproduction filenames are retained; the supplement README maps them to the revised manuscript figure numbers.

## Reproduce the released results

The tested plotting environment is Python 3.12.14, Matplotlib 3.11.2, and NumPy 2.5.3. From the repository root:

```bash
cd Online_Resource_1
uv run --no-project --python 3.12 --with matplotlib==3.11.2 --with numpy==2.5.3 python reproduce_figures_and_tables.py
python3 validate_terminal_cases.py
python3 check_synthetic_controller_example.py --output reproduced/synthetic_example_checks.json
```

The commands recompute released comparison statistics, five result tables, data/case figures, and terminal-case arithmetic. Generated reports, LaTeX tables, and PDF/SVG figures are written to `Online_Resource_1/reproduced/`. The synthetic checker accepts one legal plan and detects nine injected faults, reporting `case_count: 10` and `passed_count: 10`. Its editable input and hand-constructed plan demonstrate occupancy, precedence, tandem, motion-attachment, and rail-order semantics.

The validation scripts use only the Python standard library. Plotting uses Arial with a Helvetica/DejaVu Sans fallback. If the pinned packages are already installed in an isolated Python environment, `python reproduce_figures_and_tables.py` is sufficient. Check the release manifest from `Online_Resource_1/` with `sha256sum -c SHA256SUMS` on Linux or `shasum -a 256 -c SHA256SUMS` on macOS. Detailed output filenames and model/algorithm descriptions are in [the supplement README](Online_Resource_1/README.md).

## Authors and licence

Both authors have completed review of the manuscript text, figures, analyses, released code, and AI-assistance disclosure. OpenAI Codex assisted manuscript editing and plotting/example code preparation. No specific funding was received for this work, and the authors declare no relevant competing interests.

This public package is released under the [MIT License](LICENSE), copyright 2026 Zixi Wang and Weimin Wu. The licence applies to the files released in this repository; it grants no rights to private industrial solver code or customer source data.
