"""Linked-list-backed convex layer manager for the V2 layered architecture."""

from __future__ import annotations

from dataclasses import dataclass
from typing import Dict, Iterable, Iterator, List, Sequence, Tuple

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
class LayerNode:
    point: Point
    prev: "LayerNode | None" = None
    next: "LayerNode | None" = None


@dataclass
class LinkedLayer:
    head: LayerNode | None = None
    size: int = 0

    @classmethod
    def from_points(cls, points: Sequence[Point]) -> "LinkedLayer":
        layer = cls()
        canonical_points = canonicalize_layer(points)
        previous: LayerNode | None = None
        first: LayerNode | None = None

        for point in canonical_points:
            node = LayerNode(point=point)
            if first is None:
                first = node
            if previous is not None:
                previous.next = node
                node.prev = previous
            previous = node
            layer.size += 1

        if first is not None and previous is not None:
            first.prev = previous
            previous.next = first
            layer.head = first

        return layer

    def __len__(self) -> int:
        return self.size

    def iter_nodes(self) -> Iterator[LayerNode]:
        if self.head is None:
            return

        current = self.head
        for _ in range(self.size):
            assert current is not None
            yield current
            current = current.next

    def to_list(self) -> List[Point]:
        return [node.point for node in self.iter_nodes()]

    def clone(self) -> "LinkedLayer":
        return LinkedLayer.from_points(self.to_list())

    def remove_node(self, node: LayerNode) -> None:
        if self.size == 0 or self.head is None:
            raise ValueError("Cannot remove a node from an empty layer.")

        if self.size == 1:
            self.head = None
            self.size = 0
            return

        assert node.prev is not None
        assert node.next is not None
        node.prev.next = node.next
        node.next.prev = node.prev
        if self.head is node:
            self.head = node.next
        self.size -= 1


@dataclass
class LinkedConvexLayer:
    """Linked-list-backed layered hull manager with local adjacent-layer restoration."""

    active_points: List[Point]
    layers: List[LinkedLayer]
    convex_hull_algorithm: ConvexHullAlgorithm
    point_index: Dict[Point, Tuple[int, LayerNode]]

    @classmethod
    def from_points(
        cls,
        points: Iterable[Point],
        convex_hull_algorithm: ConvexHullAlgorithm | None = None,
    ) -> "LinkedConvexLayer":
        hull_algorithm = convex_hull_algorithm or andrews_monotone_chain
        active_points = [tuple(map(float, point)) for point in points]
        layer_lists = build_convex_layers(active_points, hull_algorithm)
        layers = [LinkedLayer.from_points(layer) for layer in layer_lists]
        manager = cls(
            active_points=active_points,
            layers=layers,
            convex_hull_algorithm=hull_algorithm,
            point_index={},
        )
        manager._rebuild_point_index()
        return manager

    def _rebuild_point_index(self) -> None:
        self.point_index = {}
        for layer_index, layer in enumerate(self.layers):
            for node in layer.iter_nodes():
                self.point_index[node.point] = (layer_index, node)

    def outer_layer(self) -> List[Point]:
        if not self.layers:
            return []
        return self.layers[0].to_list()

    def tangent_points(self, point: Point, layer_index: int) -> Tuple[Point, Point]:
        layer_points = self.layers[layer_index].to_list()
        combined_hull = self.convex_hull_algorithm(layer_points + [point])
        point_index = _find_point_index(combined_hull, point)
        left_tangent = combined_hull[(point_index - 1) % len(combined_hull)]
        right_tangent = combined_hull[(point_index + 1) % len(combined_hull)]
        return left_tangent, right_tangent

    def _restore_layers_from(self, start_index: int) -> None:
        layer_index = max(0, start_index)
        while layer_index < len(self.layers) - 1:
            upper_layer = self.layers[layer_index].to_list()
            lower_layer = self.layers[layer_index + 1].to_list()
            merged_points = upper_layer + lower_layer

            if len(merged_points) >= 3:
                new_upper_layer = canonicalize_layer(self.convex_hull_algorithm(merged_points))
            else:
                new_upper_layer = canonicalize_layer(merged_points)

            new_lower_layer = canonicalize_layer(remove_points(merged_points, new_upper_layer))

            if _same_points(new_upper_layer, upper_layer) and _same_points(new_lower_layer, lower_layer):
                break

            self.layers[layer_index] = LinkedLayer.from_points(new_upper_layer)
            if new_lower_layer:
                self.layers[layer_index + 1] = LinkedLayer.from_points(new_lower_layer)
            else:
                del self.layers[layer_index + 1]
                break

            layer_index += 1

    def remove_point(self, target: Point) -> None:
        try:
            affected_layer_index, node = self.point_index[target]
        except KeyError as error:
            raise ValueError(f"Point {target} was not present in any stored layer.") from error

        self.active_points = remove_points(self.active_points, [target])
        self.layers[affected_layer_index].remove_node(node)

        if len(self.layers[affected_layer_index]) == 0:
            del self.layers[affected_layer_index]
            affected_layer_index = max(0, affected_layer_index - 1)
        else:
            self.layers[affected_layer_index] = LinkedLayer.from_points(
                self.layers[affected_layer_index].to_list()
            )

        if self.layers:
            self._restore_layers_from(affected_layer_index)

        self._rebuild_point_index()

    def clone_without_point(self, target: Point) -> "LinkedConvexLayer":
        clone = LinkedConvexLayer(
            active_points=list(self.active_points),
            layers=[layer.clone() for layer in self.layers],
            convex_hull_algorithm=self.convex_hull_algorithm,
            point_index={},
        )
        clone._rebuild_point_index()
        clone.remove_point(target)
        return clone
