Implementation of the area-weighted convex hull peeling algorithm for outlier detection, as presented by V. Shridhar and R. Svenning at CCCG 2024.

The repository currently starts with the `V1` brute-force oracle baseline. This version is the fixed source of truth used to generate and verify golden test cases before later optimized versions are added.

## Repository Structure

```text
.
├── algorithms_and_data_structures/
├── agent/
├── geometry/
├── publications/
├── testcases/
├── v1/
├── visualize/
├── main.py
└── README.md
```

## Component Overview

- `algorithms_and_data_structures/`
  Shared algorithms and supporting data structures across versions. This includes current helpers such as convex hull routines and the Shoelace Formula area helper, plus planned structures for later stages.

- `publications/`
  Stores the original paper and thesis source files together with derived LaTeX summaries such as `refined_thesis_logic.tex` and `refined_publication_summary.tex`.

- `geometry/`
  Shared geometric primitives and numeric guards used across all versions. This contains orientation predicates, polygon area helpers, general-position checks, and globally named epsilons.

- `agent/`
  Operational tooling and disposable agent outputs. This contains the gatekeeper scripts in `agent/scripts/` and temporary verification artifacts in `agent/temp_files/`.

- `testcases/v1_gold/`
  Fixed golden cases for the `V1` oracle. These are the source of truth for verification once generated.

- `testcases/v1_gold_manifest.json`
  Hash manifest and audit summary for the frozen `V1` suite. This is used to certify that the current golden files are stable and unchanged.

- `v1/`
  `V1` brute-force oracle implementation. This contains the baseline peeling logic and the fixed-case generator used to create goldens.

- `visualize/`
  Visualization tooling for rendering a fixed `V1` testcase as a GIF plus an HTML step-through viewer. A checked-in example bundle lives under `visualize/example/`.

- `main.py`
  Thin command-line entrypoint used by the verification script to run a requested implementation version against a directory of test cases.

## Verification Workflow

The current baseline follows the gatekeeper protocol:

1. Generate fixed golden cases for the oracle.
2. Run the implementation against those same cases.
3. Compare generated outputs to the fixed goldens.
4. Audit the frozen suite and write a hash manifest.
5. Report pass rate and produce a divergence report when mismatches occur.

Before treating the suite as truly frozen, run the certification pass:

```bash
PYTHONPATH=. python3 agent/scripts/audit_v1_suite.py
```

This verifies that:

- the stored expected outputs still match a fresh rerun of the oracle
- both convex hull algorithms produce the same oracle output
- every peel step remains unambiguous under `MIN_AREA_DECREASE_EPSILON`
- the suite hash manifest in `testcases/v1_gold_manifest.json` is refreshed

The current frozen `V1` suite contains:

- `1000` cases total
- `900` cases with `25` points
- `100` cases with `100` points
- points generated on a grid with coordinates in `[-1_000_000, 1_000_000]`

The main verification entrypoint is:

```bash
bash agent/scripts/verify_integrity.sh v1 v1
```

Audit and hash the frozen suite:

```bash
PYTHONPATH=. python3 agent/scripts/audit_v1_suite.py
```

Cross-check the oracle under both convex hull algorithms:

```bash
PYTHONPATH=. python3 agent/scripts/verify_convex_hull_consistency.py
```

Render a testcase as a GIF plus interactive viewer:

```bash
PYTHONPATH=. python3 visualize/render_v1_gif.py --case testcases/v1_gold/case_0999.json --output-dir visualize/output/case_0999
```
