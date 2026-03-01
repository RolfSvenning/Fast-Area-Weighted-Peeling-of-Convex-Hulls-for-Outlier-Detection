"""Shared convex hull algorithms."""

from __future__ import annotations

from typing import Callable, Iterable, List

from geometry.constants import ORIENTATION_EPSILON
from geometry.core import Point, orientation

ConvexHullAlgorithm = Callable[[Iterable[Point]], List[Point]]


def andrews_monotone_chain(points: Iterable[Point]) -> List[Point]:
    unique_points = sorted(set(points))
    if len(unique_points) <= 1:
        return unique_points

    lower: List[Point] = []
    for point in unique_points:
        while len(lower) >= 2 and orientation(lower[-2], lower[-1], point) <= ORIENTATION_EPSILON:
            lower.pop()
        lower.append(point)

    upper: List[Point] = []
    for point in reversed(unique_points):
        while len(upper) >= 2 and orientation(upper[-2], upper[-1], point) <= ORIENTATION_EPSILON:
            upper.pop()
        upper.append(point)

    return lower[:-1] + upper[:-1]


def jarvis_march(points: Iterable[Point]) -> List[Point]:
    unique_points = sorted(set(points))
    if len(unique_points) <= 1:
        return unique_points

    start = min(unique_points)
    hull: List[Point] = []
    current = start

    while True:
        hull.append(current)
        candidate = None
        for point in unique_points:
            if point == current:
                continue
            if candidate is None:
                candidate = point
                continue

            turn = orientation(current, candidate, point)
            if turn < -ORIENTATION_EPSILON:
                candidate = point
                continue

            if abs(turn) <= ORIENTATION_EPSILON:
                candidate_distance = (candidate[0] - current[0]) ** 2 + (candidate[1] - current[1]) ** 2
                point_distance = (point[0] - current[0]) ** 2 + (point[1] - current[1]) ** 2
                if point_distance > candidate_distance:
                    candidate = point

        if candidate is None or candidate == start:
            break
        current = candidate

    return hull
