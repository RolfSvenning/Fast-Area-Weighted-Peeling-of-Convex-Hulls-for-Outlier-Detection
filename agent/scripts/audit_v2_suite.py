#!/usr/bin/env python3
"""Audit the frozen V2 suite and write a deterministic hash manifest."""

from __future__ import annotations

import hashlib
import json
import math
from pathlib import Path
from typing import Any, Dict, Iterable, List, Sequence

from algorithms_and_data_structures.convex_hull import andrews_monotone_chain, jarvis_march
from geometry.constants import ORIENTATION_EPSILON
from geometry.core import Point, is_general_position
from v1.oracle import AmbiguousPeelError
from v2.generator import generate_v2_expected
from v2.layered import v2_layered_area_weighted_peeling

FLOAT_TOLERANCE = 1e-9
DEFAULT_SUITE_DIR = Path("testcases/v2_gold")
DEFAULT_MANIFEST_PATH = Path("testcases/v2_gold_manifest.json")


def _iter_case_files(input_dir: Path) -> Iterable[Path]:
    return sorted(path for path in input_dir.iterdir() if path.suffix == ".json")


def _share_limit_ok(values: Sequence[int]) -> bool:
    counts: Dict[int, int] = {}
    for value in values:
        counts[value] = counts.get(value, 0) + 1
        if counts[value] > 2:
            return False
    return True


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


def _compare_outputs(reference: Any, candidate: Any) -> List[str]:
    diffs: List[str] = []
    _compare_values(reference["peel_order"], candidate["peel_order"], "peel_order", diffs)
    _compare_values(reference["area_decreases"], candidate["area_decreases"], "area_decreases", diffs)
    _compare_values(reference["hulls"], candidate["hulls"], "hulls", diffs)
    _compare_values(reference["layers_after_peel"], candidate["layers_after_peel"], "layers_after_peel", diffs)
    _compare_values(reference["final_points"], candidate["final_points"], "final_points", diffs)
    return diffs


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
            rebuilt_expected = generate_v2_expected(points, andrews_monotone_chain)
            layered_result = v2_layered_area_weighted_peeling(points, convex_hull_algorithm=andrews_monotone_chain)
            jarvis_result = v2_layered_area_weighted_peeling(points, convex_hull_algorithm=jarvis_march)
        except AmbiguousPeelError as error:
            failures.append(f"{case_file.name}: runtime raised ambiguity error: {error}")
            continue

        diffs = _compare_outputs(expected, rebuilt_expected)
        if diffs:
            failures.append(f"{case_file.name}: stored expected output diverges from rebuilt V2 oracle")
            failures.extend(f"  - {diff}" for diff in diffs[:10])

        diffs = _compare_outputs(expected, layered_result)
        if diffs:
            failures.append(f"{case_file.name}: V2 implementation diverges from expected output")
            failures.extend(f"  - {diff}" for diff in diffs[:10])

        diffs = _compare_outputs(layered_result, jarvis_result)
        if diffs:
            failures.append(f"{case_file.name}: convex hull algorithms disagree under V2")
            failures.extend(f"  - {diff}" for diff in diffs[:10])

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

        layer_counts = [len(step_layers) for step_layers in expected["layers_after_peel"]]
        manifest_cases.append(
            {
                "file": case_file.name,
                "sha256": _sha256_bytes(payload_bytes),
                "point_count": metadata["point_count"],
                "grid_limit": metadata["grid_limit"],
                "source_suite": metadata.get("source_suite"),
                "max_layer_count": max(layer_counts) if layer_counts else 0,
            }
        )

    suite_hash_input = "\n".join(
        f"{entry['file']}:{entry['sha256']}" for entry in sorted(manifest_cases, key=lambda item: item["file"])
    ).encode("utf-8")

    return {
        "suite": "v2_gold",
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
        print("V2 suite audit failed:")
        for failure in manifest["failures"][:50]:
            print(failure)
        print(f"Wrote manifest to {DEFAULT_MANIFEST_PATH}")
        return 1

    print(
        "V2 suite audit passed: "
        f"{manifest['case_count']} cases, suite hash {manifest['suite_sha256']}"
    )
    print(f"Wrote manifest to {DEFAULT_MANIFEST_PATH}")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
