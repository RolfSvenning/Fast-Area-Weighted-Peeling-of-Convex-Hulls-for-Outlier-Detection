# Detailed Project Plan

## Core Objective

Implement a verifiable, high-performance area-weighted convex hull peeling algorithm with target running time `O(n log n)`.

The project is correctness-first. Every optimized component must be validated against the brute-force oracle on fixed test cases before it can be considered correct.

## Source of Truth

### `V1` Oracle

`V1` is the brute-force reference implementation.

- Complexity target: `O(n^3 log n)` for the full peeling process
- Representation: points as plain arrays / lists
- Peel rule:
  1. consider only current convex hull vertices
  2. remove each candidate vertex in turn
  3. recompute the convex hull of the remaining points
  4. compute hull area decrease using the Shoelace Formula
  5. choose the unique maximum-area-decrease deletion
- Stop condition: stop when `3` points remain

No later version or helper is considered correct unless it reproduces the `V1` oracle output on the fixed suite.

## Geometric Constraints

All numeric geometry must remain isolated inside the shared geometry layer.

### Geometry Kernel

The geometry layer is the numerical guard for the project. It should contain only predicates and primitive geometric computations:

- orientation
- cross product
- polygon area via Shoelace Formula
- point equality checks under epsilon
- general-position checks

This isolation is intentional. It should be possible later to replace floating-point predicates with `Decimal` or exact predicates without changing algorithm logic.

### Epsilon Rules

The global guard is `MIN_AREA_DECREASE_EPSILON`.

This value is used to enforce a deterministic winner at each peel step:

- if `best_area_decrease - second_best_area_decrease < MIN_AREA_DECREASE_EPSILON`, the step is ambiguous
- generated test cases that hit this condition must be rejected
- runtime inputs that hit this condition should raise an ambiguity error rather than silently tie-break

### General Position

Generated point sets must satisfy:

- no three points collinear under the orientation / cross-product test
- no more than `2` points share any `x` coordinate
- no more than `2` points share any `y` coordinate

The generator uses large-grid sampling plus coordinate-frequency checks to enforce these constraints.

## Oracle Test Generation

Fixed golden cases are created by the oracle and then frozen.

Each golden case should contain:

- input points
- expected peel order
- expected area decrease at each peel
- expected hull snapshot at each peel
- generation metadata

Generation metadata should include:

- seed
- point count
- grid limit
- rejected-attempt count
- convex hull algorithm used for the oracle
- named epsilon values

## Master Progression

The master branch progresses through the following architectural stages.

### `V1: Brute`

- Strategy: total recomputation after every candidate deletion
- Dependency: `GeometryKernel`
- Role: reference oracle and fixed-suite generator

### `V2: Layered`

- Strategy: maintain convex layers
- Restore the hull after each peel using next-layer tangent / max queries
- Dependency: `ConvexLayerManager`

### `V3: Efficient`

- Strategy: keep the layered approach, but upgrade tangent handling to logarithmic-time queries
- Dependency: `HullTreeStructure`

### `V4: Dynamic`

- Strategy: deletion-only dynamic convex hull with `O(log^2 n)` update time or better
- Dependency: `DynamicHullEngine`

## Required Development Protocol

This gatekeeper loop is mandatory for all work on master or feature branches.

### Phase 1: Baseline and Test Generation

For the component currently under development:

1. implement a naive correct version first
2. generate a static test suite of at least `500` cases
3. freeze that suite once generated

The fixed suite becomes the branch-local or component-local source of truth.

### Phase 2: Optimized Development

1. implement the optimized version
2. run the gatekeeper against the fixed suite
3. record the pass rate

Required command shape:

```bash
bash agent/scripts/verify_integrity.sh <branch> <version>
```

Required progress format:

```text
[branch] | Progress: X% | Oracle: Fixed | Manual-Flag: [n] cases
```

### The 99% Rule

- `100%`
  The implementation matches the fixed oracle suite completely.

- `>= 99%`
  The branch may be flagged for manual inspection.
  The divergence report should isolate the failing cases, which are likely precision edge cases.

- `< 99%`
  The implementation must be treated as incorrect.
  The agent should continue fixing logic autonomously rather than committing.

### Commit Rule

Commit is only allowed when the pass rate is at least `99%`.

## Branching Workflow

- `master`
  Tracks the architectural progression `V1 -> V4`

- feature branches
  Used for individual helpers and substructures, for example:
  - tangent-query support
  - convex layer restoration
  - tree balancing
  - dynamic hull maintenance

Each feature branch should still have:

- a naive baseline for the helper if needed
- a fixed test suite
- gatekeeper verification before merge

## Current Repository Mapping

### Shared Components

- `geometry/`
  Shared numeric predicates and constants

- `algorithms_and_data_structures/`
  Shared geometric algorithms such as convex hull routines

### Oracle Components

- `v1/`
  `V1` brute-force oracle logic and oracle-driven test generation

- `testcases/v1_gold/`
  Fixed `V1` golden suite

### Agent Workflow Components

- `agent/scripts/`
  Gatekeeper scripts, suite generation, output comparison, and cross-check tooling

- `agent/temp_files/`
  Disposable gatekeeper artifacts such as:
  - current run outputs
  - last pass rate
  - divergence report

### Publications

- `publications/`
  Original paper sources plus refined project-facing summaries

The refined documents are:

- `publications/refined_thesis_logic.tex`
- `publications/refined_publication_summary.tex`

The original LaTeX sources must not be modified in place.

## Current Fixed Suite

The current oracle suite contains `1000` frozen `V1` cases:

- `900` cases with `25` points
- `100` cases with `100` points

This suite is the active validation baseline until explicitly regenerated and refrozen.

## Operational Commands

Generate the current fixed `V1` suite:

```bash
PYTHONPATH=. python3 agent/scripts/generate_v1_gold.py --output-dir testcases/v1_gold --bucket 25:900 --bucket 100:100
```

Run the gatekeeper:

```bash
bash agent/scripts/verify_integrity.sh v1 v1
```

Check that the oracle gives the same result under both convex hull algorithms:

```bash
PYTHONPATH=. python3 agent/scripts/verify_convex_hull_consistency.py
```

View this plan:

```bash
sed -n '1,260p' agent/PLAN.md
```

View the concise summary:

```bash
sed -n '1,200p' agent/PLAN_SUMMARY.md
```
