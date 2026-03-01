"""Naive V2 layered implementation built around a list-backed convex layer manager."""

from __future__ import annotations

from typing import Dict, List, Sequence

from algorithms_and_data_structures.convex_hull import (
    ConvexHullAlgorithm,
    andrews_monotone_chain,
)
from algorithms_and_data_structures.list_convex_layer import ListConvexLayer
from algorithms_and_data_structures.shoelace_formula import polygon_area
from geometry.constants import MIN_AREA_DECREASE_EPSILON
from geometry.core import Point
from v1.oracle import AmbiguousPeelError


def v2_layered_area_weighted_peeling(
    points: Sequence[Point],
    convex_hull_algorithm: ConvexHullAlgorithm | None = None,
    min_area_decrease_epsilon: float = MIN_AREA_DECREASE_EPSILON,
) -> Dict[str, object]:
    hull_algorithm = convex_hull_algorithm or andrews_monotone_chain
    layer_manager = ListConvexLayer.from_points(points, hull_algorithm)
    peel_order: List[Point] = []
    area_decreases: List[float] = []
    hulls: List[List[Point]] = []
    layers_after_peel: List[List[List[Point]]] = []

    while len(layer_manager.active_points) > 3:
        hull = layer_manager.outer_layer()
        current_area = polygon_area(hull)
        best_decrease = float("-inf")
        second_best_decrease = float("-inf")
        best_vertex: Point | None = None

        for vertex in hull:
            candidate_manager = layer_manager.clone_without_point(vertex)
            next_hull = candidate_manager.outer_layer()
            area_decrease = current_area - polygon_area(next_hull)

            if area_decrease > best_decrease:
                second_best_decrease = best_decrease
                best_decrease = area_decrease
                best_vertex = vertex
            elif area_decrease > second_best_decrease:
                second_best_decrease = area_decrease

        if best_vertex is None:
            raise ValueError("No peel candidate was found on the outer layer.")

        if len(hull) > 1 and best_decrease - second_best_decrease < min_area_decrease_epsilon:
            raise AmbiguousPeelError(
                "Ambiguous peel step: best and second-best area decreases are too close."
            )

        hulls.append(list(hull))
        peel_order.append(best_vertex)
        area_decreases.append(best_decrease)
        layer_manager.remove_point(best_vertex)
        layers_after_peel.append([list(layer) for layer in layer_manager.layers])

    return {
        "peel_order": peel_order,
        "area_decreases": area_decreases,
        "hulls": hulls,
        "layers_after_peel": layers_after_peel,
        "final_points": list(layer_manager.active_points),
    }
