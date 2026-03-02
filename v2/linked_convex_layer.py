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


def _find_point_index(points: Sequence[Point], target: Point) -> int:
    for index, point in enumerate(points):
        if points_equal(point, target, ORIENTATION_EPSILON):
            return index
    raise ValueError(f"Point {target} was not found.")


def _contains_point(points: Sequence[Point], target: Point) -> bool:
    return any(points_equal(point, target, ORIENTATION_EPSILON) for point in points)


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
        node.prev = None
        node.next = None

    def insert_linear_chain_between(
        self,
        left: LayerNode,
        right: LayerNode,
        chain_nodes: Sequence[LayerNode],
    ) -> None:
        if not chain_nodes:
            return

        first = chain_nodes[0]
        last = chain_nodes[-1]

        if self.size == 0:
            first.prev = last
            last.next = first
            for index in range(1, len(chain_nodes)):
                chain_nodes[index - 1].next = chain_nodes[index]
                chain_nodes[index].prev = chain_nodes[index - 1]
            self.head = first
            self.size = len(chain_nodes)
            return

        left.next = first
        first.prev = left
        last.next = right
        right.prev = last
        self.size += len(chain_nodes)

    def find_node(self, target: Point) -> LayerNode:
        for node in self.iter_nodes():
            if points_equal(node.point, target, ORIENTATION_EPSILON):
                return node
        raise ValueError(f"Point {target} was not present in the layer.")


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
        return canonicalize_layer(self.layers[0].to_list())

    def tangent_points(self, point: Point, layer_index: int) -> Tuple[Point, Point]:
        layer_points = self.layers[layer_index].to_list()
        combined_hull = self.convex_hull_algorithm(layer_points + [point])
        point_index = _find_point_index(combined_hull, point)
        left_tangent = combined_hull[(point_index - 1) % len(combined_hull)]
        right_tangent = combined_hull[(point_index + 1) % len(combined_hull)]
        return left_tangent, right_tangent

    def _desired_upper_for_pair(self, layer_index: int) -> List[Point]:
        upper_layer = self.layers[layer_index].to_list()
        lower_layer = self.layers[layer_index + 1].to_list()
        merged_points = upper_layer + lower_layer

        if len(merged_points) >= 3:
            return canonicalize_layer(self.convex_hull_algorithm(merged_points))
        return canonicalize_layer(merged_points)

    def _promoted_chain_for_pair(
        self,
        layer_index: int,
    ) -> Tuple[List[Point], Point | None, Point | None]:
        desired_upper = self._desired_upper_for_pair(layer_index)
        lower_layer = self.layers[layer_index + 1].to_list()
        lower_flags = [_contains_point(lower_layer, point) for point in desired_upper]

        if not any(lower_flags):
            return [], None, None

        block_starts = [
            index
            for index, flag in enumerate(lower_flags)
            if flag and not lower_flags[(index - 1) % len(lower_flags)]
        ]
        if len(block_starts) != 1:
            raise ValueError("Expected exactly one promoted chain while restoring adjacent layers.")

        start = block_starts[0]
        promoted_points: List[Point] = []
        cursor = start
        while lower_flags[cursor]:
            promoted_points.append(desired_upper[cursor])
            cursor = (cursor + 1) % len(desired_upper)

        left_boundary = desired_upper[(start - 1) % len(desired_upper)]
        right_boundary = desired_upper[cursor]
        return promoted_points, left_boundary, right_boundary

    def _extract_promoted_nodes(
        self,
        lower_layer: LinkedLayer,
        promoted_points: Sequence[Point],
    ) -> List[LayerNode]:
        nodes = [lower_layer.find_node(point) for point in promoted_points]
        for node in nodes:
            lower_layer.remove_node(node)

        for index, node in enumerate(nodes):
            node.prev = nodes[index - 1] if index > 0 else None
            node.next = nodes[index + 1] if index + 1 < len(nodes) else None

        return nodes

    def _promote_chain_into_upper(
        self,
        layer_index: int,
        promoted_points: Sequence[Point],
        left_boundary: Point,
        right_boundary: Point,
    ) -> bool:
        if not promoted_points:
            return False

        upper_layer = self.layers[layer_index]
        lower_layer = self.layers[layer_index + 1]
        left_node = upper_layer.find_node(left_boundary)
        right_node = upper_layer.find_node(right_boundary)
        promoted_nodes = self._extract_promoted_nodes(lower_layer, promoted_points)

        upper_layer.insert_linear_chain_between(left_node, right_node, promoted_nodes)
        return True

    def _restore_pair_by_splicing(self, layer_index: int) -> bool:
        promoted_points, left_boundary, right_boundary = self._promoted_chain_for_pair(layer_index)
        if not promoted_points or left_boundary is None or right_boundary is None:
            return False

        self._promote_chain_into_upper(
            layer_index,
            promoted_points,
            left_boundary,
            right_boundary,
        )

        if len(self.layers[layer_index + 1]) == 0:
            del self.layers[layer_index + 1]

        return True

    def _restore_layers_from(self, start_index: int) -> None:
        layer_index = max(0, start_index)
        while layer_index < len(self.layers) - 1:
            changed = self._restore_pair_by_splicing(layer_index)
            if not changed:
                break

            if layer_index + 1 >= len(self.layers):
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

        if self.layers:
            self._restore_layers_from(affected_layer_index)

        self._rebuild_point_index()
