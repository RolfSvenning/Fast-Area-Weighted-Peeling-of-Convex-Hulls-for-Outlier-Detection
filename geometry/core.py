"""Shared geometry predicates and low-level point operations."""

from __future__ import annotations

from typing import Sequence, Tuple

from .constants import ORIENTATION_EPSILON

Point = Tuple[float, float]


def orientation(a: Point, b: Point, c: Point) -> float:
    return (b[0] - a[0]) * (c[1] - a[1]) - (b[1] - a[1]) * (c[0] - a[0])


def points_equal(a: Point, b: Point, epsilon: float) -> bool:
    return abs(a[0] - b[0]) <= epsilon and abs(a[1] - b[1]) <= epsilon


def is_general_position(points: Sequence[Point], epsilon: float = ORIENTATION_EPSILON) -> bool:
    count = len(points)
    for i in range(count):
        for j in range(i + 1, count):
            for k in range(j + 1, count):
                if abs(orientation(points[i], points[j], points[k])) <= epsilon:
                    return False
    return True
