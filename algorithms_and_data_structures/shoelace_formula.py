"""Polygon area helpers based on the Shoelace Formula."""

from __future__ import annotations

from typing import Sequence

from geometry.core import Point


def polygon_signed_double_area(points: Sequence[Point]) -> float:
    total = 0.0
    count = len(points)
    for idx in range(count):
        x1, y1 = points[idx]
        x2, y2 = points[(idx + 1) % count]
        total += x1 * y2 - x2 * y1
    return total


def polygon_area(points: Sequence[Point]) -> float:
    if len(points) < 3:
        return 0.0
    return abs(polygon_signed_double_area(points)) * 0.5

