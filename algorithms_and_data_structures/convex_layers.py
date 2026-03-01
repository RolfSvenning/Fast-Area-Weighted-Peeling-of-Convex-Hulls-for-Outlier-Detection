"""Shared helpers for rebuilding convex layers from a point set."""

from __future__ import annotations

from typing import List, Sequence

from geometry.constants import ORIENTATION_EPSILON
from geometry.core import Point, points_equal

from .convex_hull import ConvexHullAlgorithm


def canonicalize_layer(points: Sequence[Point]) -> List[Point]:
    if len(points) <= 1:
        return list(points)
    if len(points) == 2:
        return sorted(points)

    start_index = min(range(len(points)), key=lambda index: points[index])
    return [points[(start_index + offset) % len(points)] for offset in range(len(points))]


def remove_points(points: Sequence[Point], removed_points: Sequence[Point]) -> List[Point]:
    remaining = list(points)
    for removed_point in removed_points:
        updated: List[Point] = []
        removed = False
        for point in remaining:
            if not removed and points_equal(point, removed_point, ORIENTATION_EPSILON):
                removed = True
                continue
            updated.append(point)
        if not removed:
            raise ValueError(f"Point {removed_point} was not present in the active set.")
        remaining = updated
    return remaining


def build_convex_layers(
    points: Sequence[Point],
    convex_hull_algorithm: ConvexHullAlgorithm,
) -> List[List[Point]]:
    remaining = list(points)
    layers: List[List[Point]] = []
    while len(remaining) >= 3:
        hull = convex_hull_algorithm(remaining)
        if len(hull) < 3:
            break
        layers.append(canonicalize_layer(hull))
        remaining = remove_points(remaining, hull)
    if remaining:
        layers.append(canonicalize_layer(remaining))
    return layers
