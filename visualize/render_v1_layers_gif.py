#!/usr/bin/env python3
"""Render a V1 testcase as a GIF showing all convex layers at each peel."""

from __future__ import annotations

import argparse
import json
import os
from io import BytesIO
from pathlib import Path
from typing import List, Sequence, Tuple

os.environ.setdefault("MPLCONFIGDIR", "agent/temp_files/matplotlib")

import matplotlib

matplotlib.use("Agg")

import matplotlib.pyplot as plt
from PIL import Image

from algorithms_and_data_structures.convex_hull import andrews_monotone_chain
from algorithms_and_data_structures.convex_layers import build_convex_layers
from algorithms_and_data_structures.shoelace_formula import polygon_area
from v1.oracle import v1_area_weighted_peeling

Point = Tuple[float, float]

LAYER_COLORS = [
    "#38bdf8",
    "#f59e0b",
    "#22c55e",
    "#a78bfa",
    "#f97316",
    "#e879f9",
    "#14b8a6",
    "#fb7185",
]


def _remove_point_once(points: Sequence[Point], target: Point) -> List[Point]:
    remaining: List[Point] = []
    removed = False
    for point in points:
        if not removed and point == target:
            removed = True
            continue
        remaining.append(point)
    if not removed:
        raise ValueError(f"Could not remove point {target}.")
    return remaining


def _closed_cycle(points: Sequence[Point]) -> tuple[List[float], List[float]]:
    cycle = list(points)
    if cycle and cycle[0] != cycle[-1]:
        cycle.append(cycle[0])
    return [point[0] for point in cycle], [point[1] for point in cycle]


def _compute_states(points: Sequence[Point]) -> tuple[List[dict], List[float]]:
    result = v1_area_weighted_peeling(points)
    active_points = [tuple(point) for point in points]
    states: List[dict] = []
    hull_areas: List[float] = []

    while True:
        layers = [
            [tuple(point) for point in layer]
            for layer in build_convex_layers(active_points, andrews_monotone_chain)
        ]
        outer_hull = layers[0] if layers else list(active_points)
        hull_areas.append(polygon_area(outer_hull))
        states.append(
            {
                "active_points": list(active_points),
                "layers": layers,
                "removed_point": None,
                "area_decrease": None,
            }
        )
        if len(active_points) <= 3:
            break

        step_index = len(states) - 1
        removed_point = tuple(result["peel_order"][step_index])
        area_decrease = result["area_decreases"][step_index]
        states[-1]["removed_point"] = removed_point
        states[-1]["area_decrease"] = area_decrease
        active_points = _remove_point_once(active_points, removed_point)

    return states, hull_areas


def _render_frame(
    all_points: Sequence[Point],
    state: dict,
    hull_areas: Sequence[float],
    frame_index: int,
    case_name: str,
) -> Image.Image:
    fig_bg = "#020617"
    panel_bg = "#0f172a"
    grid = "#334155"
    text = "#e5e7eb"
    muted = "#94a3b8"
    inactive = "#334155"
    active = "#e2e8f0"
    highlight = "#f43f5e"

    fig, (ax_geom, ax_curve) = plt.subplots(
        1,
        2,
        figsize=(10.8, 5.8),
        dpi=120,
        gridspec_kw={"width_ratios": [1.7, 1.0]},
    )
    fig.patch.set_facecolor(fig_bg)
    ax_geom.set_facecolor(panel_bg)
    ax_curve.set_facecolor(panel_bg)

    all_x = [point[0] for point in all_points]
    all_y = [point[1] for point in all_points]
    span_x = max(all_x) - min(all_x)
    span_y = max(all_y) - min(all_y)
    pad_x = max(1.0, span_x * 0.1)
    pad_y = max(1.0, span_y * 0.1)
    ax_geom.set_xlim(min(all_x) - pad_x, max(all_x) + pad_x)
    ax_geom.set_ylim(min(all_y) - pad_y, max(all_y) + pad_y)
    ax_geom.set_aspect("equal", adjustable="box")

    active_points = [tuple(point) for point in state["active_points"]]
    active_set = set(active_points)
    inactive_points = [point for point in all_points if tuple(point) not in active_set]

    if inactive_points:
        ax_geom.scatter(
            [point[0] for point in inactive_points],
            [point[1] for point in inactive_points],
            s=18,
            c=inactive,
            edgecolors="none",
            zorder=1,
            label="peeled",
        )

    ax_geom.scatter(
        [point[0] for point in active_points],
        [point[1] for point in active_points],
        s=28,
        c=active,
        edgecolors=panel_bg,
        linewidths=0.5,
        zorder=2,
        label="active",
    )

    for layer_index, layer in enumerate(state["layers"]):
        if len(layer) < 2:
            continue
        color = LAYER_COLORS[layer_index % len(LAYER_COLORS)]
        layer_x, layer_y = _closed_cycle(layer)
        ax_geom.plot(layer_x, layer_y, color=color, linewidth=2.0, zorder=3 + layer_index)
        if len(layer) >= 3:
            ax_geom.fill(layer_x, layer_y, color=color, alpha=0.09, zorder=2 + layer_index)

    removed_point = state["removed_point"]
    if removed_point is not None:
        ax_geom.scatter(
            [removed_point[0]],
            [removed_point[1]],
            s=95,
            c=highlight,
            edgecolors=active,
            linewidths=0.8,
            zorder=20,
            label="next peel",
        )

    total_frames = len(hull_areas) - 1
    ax_geom.set_title(f"{case_name} | Step {frame_index}/{total_frames}", fontsize=12, color=text)

    if removed_point is None:
        subtitle = "Final 3 points remaining"
    else:
        subtitle = (
            f"{len(state['layers'])} layers | "
            f"remove {removed_point} | "
            f"area decrease = {state['area_decrease']:.3f}"
        )

    ax_geom.text(
        0.02,
        0.98,
        subtitle,
        transform=ax_geom.transAxes,
        ha="left",
        va="top",
        fontsize=10,
        color=text,
        bbox={"facecolor": "#111827", "edgecolor": grid, "boxstyle": "round,pad=0.3"},
    )
    ax_geom.grid(color=grid, linewidth=0.6)
    ax_geom.set_xlabel("x", color=muted)
    ax_geom.set_ylabel("y", color=muted)
    ax_geom.tick_params(colors=muted)
    for spine in ax_geom.spines.values():
        spine.set_color(grid)

    step_indices = list(range(len(hull_areas)))
    ax_curve.plot(step_indices, hull_areas, color="#38bdf8", linewidth=2.0)
    ax_curve.fill_between(step_indices, hull_areas, color="#38bdf8", alpha=0.16)
    ax_curve.scatter(
        [frame_index],
        [hull_areas[frame_index]],
        s=55,
        c=highlight,
        edgecolors=active,
        linewidths=0.8,
        zorder=3,
    )
    ax_curve.set_title("Outer Hull Area", fontsize=12, color=text)
    ax_curve.set_xlabel("Peel step", color=muted)
    ax_curve.set_ylabel("Area", color=muted)
    ax_curve.grid(color=grid, linewidth=0.6)
    ax_curve.set_xlim(0, max(step_indices) if step_indices else 1)
    max_area = max(hull_areas) if hull_areas else 1.0
    ax_curve.set_ylim(0, max_area * 1.08 if max_area > 0 else 1.0)
    ax_curve.tick_params(colors=muted)
    for spine in ax_curve.spines.values():
        spine.set_color(grid)

    buffer = BytesIO()
    fig.tight_layout()
    fig.savefig(buffer, format="png", facecolor=fig.get_facecolor())
    plt.close(fig)
    buffer.seek(0)
    return Image.open(buffer).convert("RGB")


def main() -> None:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--case", required=True, help="Path to a testcase JSON file.")
    parser.add_argument(
        "--output",
        help="Optional GIF output path. Defaults to visualize/output/<case>/<case>_layers.gif",
    )
    parser.add_argument("--duration-ms", type=int, default=700, help="Frame duration in milliseconds.")
    args = parser.parse_args()

    case_path = Path(args.case)
    with case_path.open("r", encoding="utf-8") as handle:
        case_data = json.load(handle)

    points = [tuple(point) for point in case_data["points"]]
    states, hull_areas = _compute_states(points)
    case_name = case_path.stem

    if args.output:
        output_path = Path(args.output)
    else:
        output_dir = Path("visualize/output") / case_name
        output_dir.mkdir(parents=True, exist_ok=True)
        output_path = output_dir / f"{case_name}_layers.gif"

    frames = [
        _render_frame(points, state, hull_areas, frame_index, case_name)
        for frame_index, state in enumerate(states)
    ]

    frames[0].save(
        output_path,
        save_all=True,
        append_images=frames[1:],
        duration=args.duration_ms,
        loop=0,
    )
    print(f"Wrote {output_path}")


if __name__ == "__main__":
    main()
