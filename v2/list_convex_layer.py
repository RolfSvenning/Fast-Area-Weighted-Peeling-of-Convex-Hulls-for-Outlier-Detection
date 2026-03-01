"""List-backed reference convex layer manager for the V2 layered architecture."""

from __future__ import annotations

from dataclasses import dataclass
from typing import Iterable, List, Sequence, Tuple

from geometry.constants import ORIENTATION_EPSILON
from geometry.core import Point, points_equal

from algorithms_and_data_structures.convex_hull import ConvexHullAlgorithm, andrews_monotone_chain
from algorithms_and_data_structures.convex_layers import (
    build_convex_layers,
    canonicalize_layer,
    remove_points,
)


def _same_points(first: Sequence[Point], second: Sequence[Point]) -> bool:
    if len(first) != len(second):
        return False
    return all(points_equal(a, b, ORIENTATION_EPSILON) for a, b in zip(first, second))


def _find_point_index(points: Sequence[Point], target: Point) -> int:
    for index, point in enumerate(points):
        if points_equal(point, target, ORIENTATION_EPSILON):
            return index
    raise ValueError(f"Point {target} was not found.")


@dataclass
class ListConvexLayer:
    """List-backed layered hull manager kept as the golden V2 reference."""

    active_points: List[Point]
    layers: List[List[Point]]
    convex_hull_algorithm: ConvexHullAlgorithm

    @classmethod
    def from_points(
        cls,
        points: Iterable[Point],
        convex_hull_algorithm: ConvexHullAlgorithm | None = None,
    ) -> "ListConvexLayer":
        hull_algorithm = convex_hull_algorithm or andrews_monotone_chain
        active_points = [tuple(map(float, point)) for point in points]
        return cls(
            active_points=active_points,
            layers=build_convex_layers(active_points, hull_algorithm),
            convex_hull_algorithm=hull_algorithm,
        )

    def outer_layer(self) -> List[Point]:
        if not self.layers:
            return []
        return list(self.layers[0])

    def tangent_points(self, point: Point, layer_index: int) -> Tuple[Point, Point]:
        layer = self.layers[layer_index]
        combined_hull = self.convex_hull_algorithm(list(layer) + [point])
        point_index = _find_point_index(combined_hull, point)
        left_tangent = combined_hull[(point_index - 1) % len(combined_hull)]
        right_tangent = combined_hull[(point_index + 1) % len(combined_hull)]
        return left_tangent, right_tangent

    def _restore_layers_from(self, start_index: int) -> None:
        layer_index = max(0, start_index)
        while layer_index < len(self.layers) - 1:
            upper_layer = list(self.layers[layer_index])
            lower_layer = list(self.layers[layer_index + 1])
            merged_points = upper_layer + lower_layer

            if len(merged_points) >= 3:
                new_upper_layer = canonicalize_layer(self.convex_hull_algorithm(merged_points))
            else:
                new_upper_layer = canonicalize_layer(merged_points)

            new_lower_layer = canonicalize_layer(remove_points(merged_points, new_upper_layer))

            if _same_points(new_upper_layer, upper_layer) and _same_points(new_lower_layer, lower_layer):
                break

            self.layers[layer_index] = new_upper_layer
            self.layers[layer_index + 1] = new_lower_layer

            if not self.layers[layer_index + 1]:
                del self.layers[layer_index + 1]
                break

            layer_index += 1

    def remove_point(self, target: Point) -> None:
        self.active_points = remove_points(self.active_points, [target])
        affected_layer_index = None
        for index, layer in enumerate(self.layers):
            if any(points_equal(point, target, ORIENTATION_EPSILON) for point in layer):
                self.layers[index] = remove_points(layer, [target])
                affected_layer_index = index
                break

        if affected_layer_index is None:
            raise ValueError(f"Point {target} was not present in any stored layer.")

        if not self.layers[affected_layer_index]:
            del self.layers[affected_layer_index]
            affected_layer_index = max(0, affected_layer_index - 1)
        else:
            self.layers[affected_layer_index] = canonicalize_layer(self.layers[affected_layer_index])

        if self.layers:
            self._restore_layers_from(affected_layer_index)

        self.layers = [layer for layer in self.layers if layer]

    def clone_without_point(self, target: Point) -> "ListConvexLayer":
        clone = ListConvexLayer(
            active_points=list(self.active_points),
            layers=[list(layer) for layer in self.layers],
            convex_hull_algorithm=self.convex_hull_algorithm,
        )
        clone.remove_point(target)
        return clone
