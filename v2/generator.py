"""Golden-case helpers for V2 layered snapshots."""

from __future__ import annotations

from typing import Dict, List, Sequence

from algorithms_and_data_structures.convex_hull import (
    ConvexHullAlgorithm,
    andrews_monotone_chain,
)
from algorithms_and_data_structures.convex_layers import build_convex_layers, remove_points
from geometry.core import Point
from v1.oracle import v1_area_weighted_peeling


def layered_snapshots_after_v1_peels(
    points: Sequence[Point],
    convex_hull_algorithm: ConvexHullAlgorithm | None = None,
) -> List[List[List[Point]]]:
    hull_algorithm = convex_hull_algorithm or andrews_monotone_chain
    v1_result = v1_area_weighted_peeling(points, convex_hull_algorithm=hull_algorithm)
    active_points = [tuple(map(float, point)) for point in points]
    layers_after_peel: List[List[List[Point]]] = []

    for removed_point in v1_result["peel_order"]:
        active_points = remove_points(active_points, [tuple(removed_point)])
        layers = build_convex_layers(active_points, hull_algorithm)
        layers_after_peel.append([list(layer) for layer in layers])

    return layers_after_peel


def generate_v2_expected(
    points: Sequence[Point],
    convex_hull_algorithm: ConvexHullAlgorithm | None = None,
) -> Dict[str, object]:
    hull_algorithm = convex_hull_algorithm or andrews_monotone_chain
    v1_expected = v1_area_weighted_peeling(points, convex_hull_algorithm=hull_algorithm)
    return {
        **v1_expected,
        "layers_after_peel": layered_snapshots_after_v1_peels(points, hull_algorithm),
    }
