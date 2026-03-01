#!/usr/bin/env python3
"""Verify that V1 oracle outputs are consistent across convex hull algorithms."""

from __future__ import annotations

import json
import math
from pathlib import Path
from typing import Any, Iterable, List

from algorithms_and_data_structures.convex_hull import andrews_monotone_chain, jarvis_march
from v1.oracle import v1_area_weighted_peeling

FLOAT_TOLERANCE = 1e-9


def _iter_case_files(input_dir: Path) -> Iterable[Path]:
    return sorted(path for path in input_dir.iterdir() if path.suffix == ".json")


def _compare_values(reference: Any, candidate: Any, path: str, diffs: List[str]) -> None:
    if isinstance(reference, list) and isinstance(candidate, list):
        if len(reference) != len(candidate):
            diffs.append(f"{path}: length mismatch expected {len(reference)} got {len(candidate)}")
            return
        for index, (reference_item, candidate_item) in enumerate(zip(reference, candidate)):
            _compare_values(reference_item, candidate_item, f"{path}[{index}]", diffs)
        return

    if isinstance(reference, float) or isinstance(candidate, float):
        if not math.isclose(float(reference), float(candidate), rel_tol=0.0, abs_tol=FLOAT_TOLERANCE):
            diffs.append(f"{path}: expected {reference} got {candidate}")
        return

    if reference != candidate:
        diffs.append(f"{path}: expected {reference} got {candidate}")


def _compare_oracle_outputs(reference: Any, candidate: Any) -> List[str]:
    diffs: List[str] = []
    _compare_values(reference["peel_order"], candidate["peel_order"], "peel_order", diffs)
    _compare_values(reference["area_decreases"], candidate["area_decreases"], "area_decreases", diffs)
    _compare_values(reference["hulls"], candidate["hulls"], "hulls", diffs)
    _compare_values(reference["final_points"], candidate["final_points"], "final_points", diffs)
    return diffs


def main() -> int:
    input_dir = Path("testcases/v1_gold")
    case_files = list(_iter_case_files(input_dir))
    reference_algorithm = andrews_monotone_chain
    alternative_algorithms = [("jarvis_march", jarvis_march)]

    failures: List[str] = []
    for case_file in case_files:
        payload = json.loads(case_file.read_text(encoding="utf-8"))
        reference = v1_area_weighted_peeling(
            payload["points"],
            convex_hull_algorithm=reference_algorithm,
        )
        for algorithm_name, hull_algorithm in alternative_algorithms:
            candidate = v1_area_weighted_peeling(
                payload["points"],
                convex_hull_algorithm=hull_algorithm,
            )
            diffs = _compare_oracle_outputs(reference, candidate)
            if diffs:
                failures.append(f"{case_file.name} [{algorithm_name}]")
                failures.extend(f"  - {diff}" for diff in diffs)

    if failures:
        print("Convex hull consistency check failed:")
        for line in failures:
            print(line)
        return 1

    checked = len(case_files) * max(len(alternative_algorithms), 1)
    print(
        f"Convex hull consistency verified across {len(case_files)} cases and {checked} oracle comparisons."
    )
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
