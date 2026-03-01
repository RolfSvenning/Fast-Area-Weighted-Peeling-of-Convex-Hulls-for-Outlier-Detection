# Project Plan Summary

## Goal

Build a verifiable high-performance area-weighted convex hull peeling algorithm with target complexity `O(n log n)`.

## Source of Truth

- `V1` is the brute-force oracle
- later versions are only correct if they reproduce `V1` on fixed test cases
- each peel considers only current hull vertices
- stop when `3` points remain

## Shared Rules

- all numeric geometry lives in `geometry/`
- shared algorithms and data structures live in `algorithms_and_data_structures/`
- global ambiguity guard: `MIN_AREA_DECREASE_EPSILON`
- generated tests must satisfy general position
- generated tests must reject ambiguous peel winners
- no more than `2` points may share any `x` or `y` coordinate

## Version Roadmap

1. `V1`
   Brute-force oracle with total recomputation

2. `V2`
   Convex-layer based implementation

3. `V3`
   Layered implementation with `O(log n)` tangent queries

4. `V4`
   Deletion-only dynamic convex hull implementation

## Gatekeeper Protocol

1. Build a naive correct version first
2. Generate and freeze a static suite of `500+` cases
3. Implement the optimized version
4. Run:
   ```bash
   bash agent/scripts/verify_integrity.sh <branch> <version>
   ```
5. Apply the `99%` rule:
   - `100%`: pass
   - `>= 99%`: manual inspection allowed
   - `< 99%`: fix before commit

Required status format:

```text
[branch] | Progress: X% | Oracle: Fixed | Manual-Flag: [n] cases
```

## Current State

- fixed `V1` suite: `1000` cases
- `900` cases with `25` points
- `100` cases with `100` points
- gatekeeper scripts live in `agent/scripts/`
- temporary verification outputs live in `agent/temp_files/`

## Useful Commands

Generate the current fixed suite:

```bash
PYTHONPATH=. python3 agent/scripts/generate_v1_gold.py --output-dir testcases/v1_gold --bucket 25:900 --bucket 100:100
```

Run the gatekeeper:

```bash
bash agent/scripts/verify_integrity.sh v1 v1
```

Check oracle consistency across hull algorithms:

```bash
PYTHONPATH=. python3 agent/scripts/verify_convex_hull_consistency.py
```
