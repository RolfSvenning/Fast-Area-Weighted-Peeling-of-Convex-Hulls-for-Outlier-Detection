#!/usr/bin/env python3
"""Audit the frozen V1 suite and write a deterministic hash manifest."""

from __future__ import annotations

import hashlib
import json
import math
from pathlib import Path
from typing import Any, Dict, Iterable, List, Sequence, Tuple

from algorithms_and_data_structures.convex_hull import andrews_monotone_chain, jarvis_march
from algorithms_and_data_structures.shoelace_formula import polygon_area
from geometry.constants import MIN_AREA_DECREASE_EPSILON, ORIENTATION_EPSILON
from geometry.core import Point, is_general_position, points_equal
from v1.oracle import AmbiguousPeelError, v1_area_weighted_peeling

FLOAT_TOLERANCE = 1e-9
DEFAULT_SUITE_DIR = Path("testcases/v1_gold")
DEFAULT_MANIFEST_PATH = Path("testcases/v1_gold_manifest.json")


def _iter_case_files(input_dir: Path) -> Iterable[Path]:
    return sorted(path for path in input_dir.iterdir() if path.suffix == ".json")


def _share_limit_ok(values: Sequence[int]) -> bool:
    counts: Dict[int, int] = {}
    for value in values:
        counts[value] = counts.get(value, 0) + 1
        if counts[value] > 2:
            return False
    return True


def _remove_point_once(points: Sequence[Point], target: Point) -> List[Point]:
    remaining: List[Point] = []
    removed = False
    for point in points:
        if not removed and points_equal(point, target, ORIENTATION_EPSILON):
            removed = True
            continue
        remaining.append(point)
    if not removed:
        raise ValueError(f"Could not remove point {target}.")
    return remaining


def _compare_values(expected: Any, actual: Any, path: str, diffs: List[str]) -> None:
    if isinstance(expected, (list, tuple)) and isinstance(actual, (list, tuple)):
        if len(expected) != len(actual):
            diffs.append(f"{path}: length mismatch expected {len(expected)} got {len(actual)}")
            return
        for index, (expected_item, actual_item) in enumerate(zip(expected, actual)):
            _compare_values(expected_item, actual_item, f"{path}[{index}]", diffs)
        return

    if isinstance(expected, float) or isinstance(actual, float):
        if not math.isclose(float(expected), float(actual), rel_tol=0.0, abs_tol=FLOAT_TOLERANCE):
            diffs.append(f"{path}: expected {expected} got {actual}")
        return

    if expected != actual:
        diffs.append(f"{path}: expected {expected} got {actual}")


def _compare_oracle_outputs(reference: Any, candidate: Any) -> List[str]:
    diffs: List[str] = []
    _compare_values(reference["peel_order"], candidate["peel_order"], "peel_order", diffs)
    _compare_values(reference["area_decreases"], candidate["area_decreases"], "area_decreases", diffs)
    _compare_values(reference["hulls"], candidate["hulls"], "hulls", diffs)
    _compare_values(reference["final_points"], candidate["final_points"], "final_points", diffs)
    return diffs


def _verify_winner_gaps(points: Sequence[Point], expected_peel_order: Sequence[Point]) -> tuple[bool, List[float]]:
    active_points = [tuple(point) for point in points]
    winner_gaps: List[float] = []

    for expected_removed in expected_peel_order:
        hull = andrews_monotone_chain(active_points)
        current_area = polygon_area(hull)
        candidates: List[Tuple[float, Point]] = []
        for vertex in hull:
            remaining_points = _remove_point_once(active_points, vertex)
            next_hull = andrews_monotone_chain(remaining_points)
            area_decrease = current_area - polygon_area(next_hull)
            candidates.append((area_decrease, vertex))

        candidates.sort(key=lambda item: item[0], reverse=True)
        if not candidates:
            return False, winner_gaps

        best_decrease, best_vertex = candidates[0]
        second_best_decrease = candidates[1][0] if len(candidates) > 1 else float("-inf")
        gap = best_decrease - second_best_decrease if len(candidates) > 1 else float("inf")
        winner_gaps.append(gap)

        if not points_equal(best_vertex, tuple(expected_removed), ORIENTATION_EPSILON):
            return False, winner_gaps
        if len(candidates) > 1 and gap < MIN_AREA_DECREASE_EPSILON:
            return False, winner_gaps

        active_points = _remove_point_once(active_points, tuple(expected_removed))

    return True, winner_gaps


def _sha256_bytes(payload: bytes) -> str:
    return hashlib.sha256(payload).hexdigest()


def audit_suite(suite_dir: Path) -> dict:
    case_files = list(_iter_case_files(suite_dir))
    failures: List[str] = []
    point_count_distribution: Dict[str, int] = {}
    grid_limits = set()
    epsilons = set()
    manifest_cases: List[dict] = []

    for case_file in case_files:
        payload_bytes = case_file.read_bytes()
        payload = json.loads(payload_bytes.decode("utf-8"))
        points = [tuple(map(float, point)) for point in payload["points"]]
        metadata = payload["metadata"]
        expected = payload["expected"]

        if len(points) != metadata["point_count"]:
            failures.append(f"{case_file.name}: point_count metadata mismatch")

        if not _share_limit_ok([int(point[0]) for point in points]):
            failures.append(f"{case_file.name}: too many shared x-coordinates")
        if not _share_limit_ok([int(point[1]) for point in points]):
            failures.append(f"{case_file.name}: too many shared y-coordinates")
        if not is_general_position(points):
            failures.append(f"{case_file.name}: points are not in general position")

        try:
            oracle_result = v1_area_weighted_peeling(points, convex_hull_algorithm=andrews_monotone_chain)
            jarvis_result = v1_area_weighted_peeling(points, convex_hull_algorithm=jarvis_march)
        except AmbiguousPeelError as error:
            failures.append(f"{case_file.name}: oracle raised ambiguity error: {error}")
            continue

        diffs = _compare_oracle_outputs(expected, oracle_result)
        if diffs:
            failures.append(f"{case_file.name}: stored expected output diverges from oracle")
            failures.extend(f"  - {diff}" for diff in diffs[:10])

        diffs = _compare_oracle_outputs(oracle_result, jarvis_result)
        if diffs:
            failures.append(f"{case_file.name}: convex hull algorithms disagree")
            failures.extend(f"  - {diff}" for diff in diffs[:10])

        gap_ok, winner_gaps = _verify_winner_gaps(points, expected["peel_order"])
        if not gap_ok:
            failures.append(f"{case_file.name}: unstable or incorrect winner gap during peel trace")

        point_count_distribution[str(metadata["point_count"])] = (
            point_count_distribution.get(str(metadata["point_count"]), 0) + 1
        )
        grid_limits.add(metadata["grid_limit"])
        epsilons.add(
            (
                metadata["epsilons"]["orientation_epsilon"],
                metadata["epsilons"]["min_area_decrease_epsilon"],
            )
        )

        manifest_cases.append(
            {
                "file": case_file.name,
                "sha256": _sha256_bytes(payload_bytes),
                "point_count": metadata["point_count"],
                "grid_limit": metadata["grid_limit"],
                "rejected_attempts": metadata["rejected_attempts"],
                "winner_gap_min": min(winner_gaps) if winner_gaps else None,
            }
        )

    suite_hash_input = "\n".join(
        f"{entry['file']}:{entry['sha256']}" for entry in sorted(manifest_cases, key=lambda item: item["file"])
    ).encode("utf-8")

    return {
        "suite": "v1_gold",
        "case_count": len(case_files),
        "point_count_distribution": point_count_distribution,
        "grid_limits": sorted(grid_limits),
        "epsilons": [
            {
                "orientation_epsilon": orientation_epsilon,
                "min_area_decrease_epsilon": min_area_decrease_epsilon,
            }
            for orientation_epsilon, min_area_decrease_epsilon in sorted(epsilons)
        ],
        "suite_sha256": _sha256_bytes(suite_hash_input),
        "cases": sorted(manifest_cases, key=lambda item: item["file"]),
        "failures": failures,
    }


def main() -> int:
    manifest = audit_suite(DEFAULT_SUITE_DIR)
    DEFAULT_MANIFEST_PATH.write_text(json.dumps(manifest, indent=2) + "\n", encoding="utf-8")

    if manifest["failures"]:
        print("V1 suite audit failed:")
        for failure in manifest["failures"][:50]:
            print(failure)
        print(f"Wrote manifest to {DEFAULT_MANIFEST_PATH}")
        return 1

    print(
        "V1 suite audit passed: "
        f"{manifest['case_count']} cases, suite hash {manifest['suite_sha256']}"
    )
    print(f"Wrote manifest to {DEFAULT_MANIFEST_PATH}")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
