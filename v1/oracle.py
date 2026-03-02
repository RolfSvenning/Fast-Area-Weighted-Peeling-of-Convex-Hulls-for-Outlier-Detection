"""Brute-force V1 area-weighted peeling oracle."""

from __future__ import annotations

from dataclasses import dataclass
from typing import Dict, List, Sequence, Tuple

from algorithms_and_data_structures.convex_hull import (
    andrews_monotone_chain,
    ConvexHullAlgorithm,
)
from algorithms_and_data_structures.shoelace_formula import polygon_area
from geometry.constants import MIN_AREA_DECREASE_EPSILON
from geometry.constants import ORIENTATION_EPSILON
from geometry.core import Point, points_equal


class AmbiguousPeelError(RuntimeError):
    """Raised when a peel step does not have a unique winner."""


@dataclass(frozen=True)
class PeelStep:
    hull: List[Point]
    removed_point: Point
    area_decrease: float


def _remove_point_once(points: Sequence[Point], target: Point) -> List[Point]:
    remaining: List[Point] = []
    removed = False
    for point in points:
        if not removed and points_equal(point, target, ORIENTATION_EPSILON):
            removed = True
            continue
        remaining.append(point)
    if not removed:
        raise ValueError(f"Point {target} was not present in the active set.")
    return remaining


def v1_area_weighted_peeling(
    points: Sequence[Point],
    convex_hull_algorithm: ConvexHullAlgorithm | None = None,
    min_area_decrease_epsilon: float = MIN_AREA_DECREASE_EPSILON,
) -> Dict[str, object]:
    hull_algorithm = convex_hull_algorithm or andrews_monotone_chain
    active_points = [tuple(map(float, point)) for point in points]
    peel_order: List[Point] = []
    area_decreases: List[float] = []
    hulls: List[List[Point]] = []

    while len(active_points) > 3:
        hull = hull_algorithm(active_points)
        current_area = polygon_area(hull)
        best_decrease = float("-inf")
        second_best_decrease = float("-inf")
        best_vertex: Point | None = None

        for vertex in hull:
            remaining_points = _remove_point_once(active_points, vertex)
            next_hull = hull_algorithm(remaining_points)
            area_decrease = current_area - polygon_area(next_hull)

            if area_decrease > best_decrease:
                second_best_decrease = best_decrease
                best_decrease = area_decrease
                best_vertex = vertex
            elif area_decrease > second_best_decrease:
                second_best_decrease = area_decrease

        if best_vertex is None:
            raise ValueError("No peel candidate was found on the hull.")

        if len(hull) > 1:
            if best_decrease - second_best_decrease < min_area_decrease_epsilon:
                raise AmbiguousPeelError(
                    "Ambiguous peel step: best and second-best area decreases are too close."
                )

        hulls.append(list(hull))
        peel_order.append(best_vertex)
        area_decreases.append(best_decrease)
        active_points = _remove_point_once(active_points, best_vertex)

    return {
        "peel_order": peel_order,
        "area_decreases": area_decreases,
        "hulls": hulls,
        "final_points": active_points,
    }
