"""Fixed-case generator for the V1 oracle."""

from __future__ import annotations

import json
import random
from pathlib import Path
from typing import Dict, List, Sequence

from algorithms_and_data_structures.convex_hull import andrews_monotone_chain
from geometry.constants import MIN_AREA_DECREASE_EPSILON
from geometry.constants import ORIENTATION_EPSILON
from geometry.core import Point, is_general_position
from .oracle import AmbiguousPeelError, v1_area_weighted_peeling


def _share_limit_ok(values: Sequence[int]) -> bool:
    counts: Dict[int, int] = {}
    for value in values:
        counts[value] = counts.get(value, 0) + 1
        if counts[value] > 2:
            return False
    return True


def _sample_points(rng: random.Random, point_count: int, grid_limit: int) -> List[Point]:
    points = set()
    while len(points) < point_count:
        points.add((float(rng.randint(-grid_limit, grid_limit)), float(rng.randint(-grid_limit, grid_limit))))
    sampled = list(points)
    if not _share_limit_ok([int(point[0]) for point in sampled]):
        raise ValueError("Too many shared x-coordinates.")
    if not _share_limit_ok([int(point[1]) for point in sampled]):
        raise ValueError("Too many shared y-coordinates.")
    if not is_general_position(sampled):
        raise ValueError("Points are not in general position.")
    return sampled
    
def generate_case(case_id: int, seed: int, point_count: int, grid_limit: int = 1_000_000) -> Dict[str, object]:
    rng = random.Random(seed)
    rejected_attempts = 0

    while True:
        try:
            points = _sample_points(rng, point_count, grid_limit)
            expected = v1_area_weighted_peeling(points, convex_hull_algorithm=andrews_monotone_chain)
            break
        except (AmbiguousPeelError, ValueError):
            rejected_attempts += 1

    return {
        "case_id": f"case_{case_id:04d}",
        "points": points,
        "expected": expected,
        "metadata": {
            "seed": seed,
            "point_count": point_count,
            "grid_limit": grid_limit,
            "rejected_attempts": rejected_attempts,
            "convex_hull_algorithm": "andrews_monotone_chain",
            "epsilons": {
                "orientation_epsilon": ORIENTATION_EPSILON,
                "min_area_decrease_epsilon": MIN_AREA_DECREASE_EPSILON,
            },
        },
    }


def write_case(output_dir: Path, payload: Dict[str, object]) -> Path:
    output_dir.mkdir(parents=True, exist_ok=True)
    path = output_dir / f"{payload['case_id']}.json"
    path.write_text(json.dumps(payload, indent=2) + "\n", encoding="utf-8")
    return path
