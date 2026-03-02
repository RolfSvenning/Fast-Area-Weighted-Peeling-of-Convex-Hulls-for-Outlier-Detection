"""V2 layered implementation built around the linked-list-backed layer manager."""

from __future__ import annotations

from typing import Dict, List, Sequence

from algorithms_and_data_structures.convex_hull import (
    ConvexHullAlgorithm,
    andrews_monotone_chain,
)
from algorithms_and_data_structures.shoelace_formula import polygon_area
from geometry.constants import MIN_AREA_DECREASE_EPSILON
from geometry.constants import ORIENTATION_EPSILON
from geometry.core import Point, points_equal
from v1.oracle import AmbiguousPeelError
from v2.linked_convex_layer import LinkedConvexLayer
from algorithms_and_data_structures.convex_layers import canonicalize_layer, remove_points


def _contains_point(points: Sequence[Point], target: Point) -> bool:
    return any(points_equal(point, target, ORIENTATION_EPSILON) for point in points)


def _extract_promoted_chain(
    desired_upper: Sequence[Point],
    lower_layer: Sequence[Point],
) -> List[Point]:
    lower_flags = [_contains_point(lower_layer, point) for point in desired_upper]
    if not any(lower_flags):
        return []

    block_starts = [
        index
        for index, flag in enumerate(lower_flags)
        if flag and not lower_flags[(index - 1) % len(lower_flags)]
    ]
    if len(block_starts) != 1:
        raise ValueError("Expected a single active chain while evaluating a V2 sensitivity.")

    start = block_starts[0]
    promoted_points: List[Point] = []
    cursor = start
    while lower_flags[cursor]:
        promoted_points.append(desired_upper[cursor])
        cursor = (cursor + 1) % len(desired_upper)
    return promoted_points


def _active_points_for_vertex(
    hull: Sequence[Point],
    lower_layer: Sequence[Point],
    vertex: Point,
    hull_algorithm: ConvexHullAlgorithm,
) -> List[Point]:
    if not lower_layer:
        return []

    reduced_hull = canonicalize_layer(remove_points(hull, [vertex]))
    desired_upper = canonicalize_layer(hull_algorithm(list(reduced_hull) + list(lower_layer)))
    return _extract_promoted_chain(desired_upper, lower_layer)


def _sensitivity_for_vertex(
    hull: Sequence[Point],
    lower_layer: Sequence[Point],
    vertex_index: int,
    hull_algorithm: ConvexHullAlgorithm,
) -> float:
    vertex = hull[vertex_index]
    previous_vertex = hull[(vertex_index - 1) % len(hull)]
    next_vertex = hull[(vertex_index + 1) % len(hull)]
    active_points = _active_points_for_vertex(hull, lower_layer, vertex, hull_algorithm)
    sensitivity_polygon = [previous_vertex, vertex, next_vertex] + list(reversed(active_points))
    return polygon_area(sensitivity_polygon)


def v2_layered_area_weighted_peeling(
    points: Sequence[Point],
    convex_hull_algorithm: ConvexHullAlgorithm | None = None,
    min_area_decrease_epsilon: float = MIN_AREA_DECREASE_EPSILON,
) -> Dict[str, object]:
    hull_algorithm = convex_hull_algorithm or andrews_monotone_chain
    layer_manager = LinkedConvexLayer.from_points(points, hull_algorithm)
    peel_order: List[Point] = []
    area_decreases: List[float] = []
    hulls: List[List[Point]] = []
    layers_after_peel: List[List[List[Point]]] = []

    while len(layer_manager.active_points) > 3:
        hull = layer_manager.outer_layer()
        lower_layer = layer_manager.layers[1].to_list() if len(layer_manager.layers) > 1 else []
        best_decrease = float("-inf")
        second_best_decrease = float("-inf")
        best_vertex: Point | None = None

        for index, vertex in enumerate(hull):
            area_decrease = _sensitivity_for_vertex(hull, lower_layer, index, hull_algorithm)

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

        hulls.append(canonicalize_layer(hull))
        peel_order.append(best_vertex)
        area_decreases.append(best_decrease)
        layer_manager.remove_point(best_vertex)
        layers_after_peel.append(
            [canonicalize_layer(layer.to_list()) for layer in layer_manager.layers]
        )

    return {
        "peel_order": peel_order,
        "area_decreases": area_decreases,
        "hulls": hulls,
        "layers_after_peel": layers_after_peel,
        "final_points": list(layer_manager.active_points),
    }
