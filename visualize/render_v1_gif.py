#!/usr/bin/env python3
"""Render a V1 peeling testcase as a GIF plus an HTML step-through viewer."""

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

from algorithms_and_data_structures.shoelace_formula import polygon_area
from v1.oracle import v1_area_weighted_peeling

Point = Tuple[float, float]


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


def _compute_states(points: Sequence[Point]) -> tuple[List[dict], dict]:
    result = v1_area_weighted_peeling(points)
    active_points = [tuple(point) for point in points]
    states: List[dict] = [
        {
            "active_points": list(active_points),
            "hull": result["hulls"][0] if result["hulls"] else list(active_points),
            "removed_point": None,
            "step_index": 0,
            "area_decrease": None,
        }
    ]

    for step_index, (hull, removed_point, area_decrease) in enumerate(
        zip(result["hulls"], result["peel_order"], result["area_decreases"]),
        start=1,
    ):
        states.append(
            {
                "active_points": list(active_points),
                "hull": [tuple(point) for point in hull],
                "removed_point": tuple(removed_point),
                "step_index": step_index,
                "area_decrease": area_decrease,
            }
        )
        active_points = _remove_point_once(active_points, tuple(removed_point))

    states.append(
        {
            "active_points": [tuple(point) for point in result["final_points"]],
            "hull": [tuple(point) for point in result["final_points"]],
            "removed_point": None,
            "step_index": len(result["peel_order"]) + 1,
            "area_decrease": None,
        }
    )
    return states, result


def _closed_cycle(points: Sequence[Point]) -> tuple[List[float], List[float]]:
    cycle = list(points)
    if cycle and cycle[0] != cycle[-1]:
        cycle.append(cycle[0])
    xs = [point[0] for point in cycle]
    ys = [point[1] for point in cycle]
    return xs, ys


def _render_frame(
    all_points: Sequence[Point],
    state: dict,
    hull_areas: Sequence[float],
    total_peels: int,
    case_name: str,
) -> Image.Image:
    fig_bg = "#020617"
    panel_bg = "#0f172a"
    grid = "#334155"
    text = "#e5e7eb"
    muted = "#94a3b8"
    inactive = "#475569"
    active = "#f8fafc"
    hull_line = "#38bdf8"
    hull_fill = "#38bdf8"
    highlight = "#f43f5e"

    fig, (ax_geom, ax_curve) = plt.subplots(
        1,
        2,
        figsize=(10.2, 5.4),
        dpi=120,
        gridspec_kw={"width_ratios": [1.55, 1.0]},
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
    removed_point = state["removed_point"]

    inactive_points = [point for point in all_points if tuple(point) not in active_set]
    if inactive_points:
        ax_geom.scatter(
            [point[0] for point in inactive_points],
            [point[1] for point in inactive_points],
            s=20,
            c=inactive,
            edgecolors="none",
            label="peeled",
        )

    if active_points:
        ax_geom.scatter(
            [point[0] for point in active_points],
            [point[1] for point in active_points],
            s=34,
            c=active,
            edgecolors=panel_bg,
            linewidths=0.5,
            label="active",
            zorder=3,
        )

    hull = [tuple(point) for point in state["hull"]]
    if len(hull) >= 2:
        hull_x, hull_y = _closed_cycle(hull)
        ax_geom.plot(hull_x, hull_y, color=hull_line, linewidth=2.0, zorder=2)
        ax_geom.fill(hull_x, hull_y, color=hull_fill, alpha=0.16, zorder=1)

    if removed_point is not None:
        ax_geom.scatter(
            [removed_point[0]],
            [removed_point[1]],
            s=90,
            c=highlight,
            edgecolors=active,
            linewidths=0.8,
            zorder=4,
            label="next peel",
        )

    title = f"{case_name} | Step {state['step_index']}/{total_peels + 1}"
    ax_geom.set_title(title, fontsize=12, color=text)

    if removed_point is None and len(active_points) == len(all_points):
        subtitle = "Initial hull"
    elif removed_point is None:
        subtitle = "Final 3 points remaining"
    else:
        subtitle = (
            f"Remove {removed_point} | "
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
    current_index = state["step_index"]
    ax_curve.plot(step_indices, hull_areas, color=hull_line, linewidth=2.0)
    ax_curve.fill_between(step_indices, hull_areas, color=hull_fill, alpha=0.16)
    ax_curve.scatter(
        [current_index],
        [hull_areas[current_index]],
        s=55,
        c=highlight,
        edgecolors=active,
        linewidths=0.8,
        zorder=3,
    )
    ax_curve.set_title("Convex Hull Area", fontsize=12, color=text)
    ax_curve.set_xlabel("Peel step", color=muted)
    ax_curve.set_ylabel("Area", color=muted)
    ax_curve.grid(color=grid, linewidth=0.6)
    ax_curve.set_xlim(0, max(step_indices) if step_indices else 1)
    max_area = max(hull_areas) if hull_areas else 1.0
    ax_curve.set_ylim(0, max_area * 1.08 if max_area > 0 else 1.0)
    ax_curve.tick_params(colors=muted)
    for spine in ax_curve.spines.values():
        spine.set_color(grid)

    frame_buffer = BytesIO()
    fig.tight_layout()
    fig.savefig(frame_buffer, format="png", facecolor=fig.get_facecolor())
    plt.close(fig)
    frame_buffer.seek(0)
    return Image.open(frame_buffer).convert("RGB")


def _write_html_viewer(
    output_dir: Path,
    case_name: str,
    gif_name: str,
    frame_names: Sequence[str],
    delay_ms: int,
) -> Path:
    html = f"""<!DOCTYPE html>
<html lang="en">
<head>
  <meta charset="utf-8" />
  <meta name="viewport" content="width=device-width, initial-scale=1" />
  <title>{case_name} Viewer</title>
  <style>
    body {{
      margin: 0;
      font-family: "Helvetica Neue", Helvetica, Arial, sans-serif;
      background: radial-gradient(circle at top, #1f2937 0%, #020617 72%);
      color: #e5e7eb;
    }}
    .shell {{
      max-width: 980px;
      margin: 32px auto;
      padding: 24px;
    }}
    .panel {{
      background: rgba(15, 23, 42, 0.92);
      border: 1px solid #334155;
      border-radius: 18px;
      box-shadow: 0 14px 40px rgba(2, 6, 23, 0.45);
      overflow: hidden;
    }}
    .toolbar {{
      display: flex;
      gap: 10px;
      flex-wrap: wrap;
      align-items: center;
      padding: 18px 20px;
      border-bottom: 1px solid #334155;
      background: rgba(15, 23, 42, 0.98);
    }}
    button {{
      border: 0;
      border-radius: 999px;
      background: #e5e7eb;
      color: #020617;
      padding: 10px 16px;
      font-size: 14px;
      cursor: pointer;
    }}
    button.secondary {{
      background: #38bdf8;
      color: white;
    }}
    button.ghost {{
      background: #334155;
      color: #e5e7eb;
    }}
    .status {{
      margin-left: auto;
      font-size: 14px;
      color: #cbd5e1;
    }}
    .canvas {{
      padding: 18px;
      display: flex;
      justify-content: center;
      align-items: center;
      background: #020617;
    }}
    img {{
      max-width: 100%;
      height: auto;
      border-radius: 12px;
      box-shadow: 0 8px 30px rgba(2, 6, 23, 0.55);
      background: white;
    }}
    h1 {{
      margin: 0 0 12px;
      font-size: 28px;
    }}
    p {{
      margin: 0 0 18px;
      color: #cbd5e1;
    }}
  </style>
</head>
<body>
  <div class="shell">
    <h1>{case_name}</h1>
    <p>Switch between the animated GIF and manual step-through frames.</p>
    <div class="panel">
      <div class="toolbar">
        <button id="gifMode">GIF</button>
        <button id="manualMode" class="secondary">Manual</button>
        <button id="prev" class="ghost">Prev</button>
        <button id="next" class="ghost">Next</button>
        <button id="playPause" class="ghost">Play</button>
        <div class="status" id="status"></div>
      </div>
      <div class="canvas">
        <img id="viewer" src="{frame_names[0]}" alt="{case_name} visualization" />
      </div>
    </div>
  </div>
  <script>
    const gifName = {gif_name!r};
    const frames = {list(frame_names)!r};
    const delayMs = {delay_ms};
    const viewer = document.getElementById("viewer");
    const status = document.getElementById("status");
    const playPause = document.getElementById("playPause");
    let manual = true;
    let index = 0;
    let timer = null;

    function render() {{
      if (manual) {{
        viewer.src = frames[index];
        status.textContent = `Frame ${{index + 1}} / ${{frames.length}}`;
      }} else {{
        viewer.src = gifName;
        status.textContent = "GIF mode";
      }}
    }}

    function stopTimer() {{
      if (timer !== null) {{
        clearInterval(timer);
        timer = null;
      }}
      playPause.textContent = "Play";
    }}

    document.getElementById("gifMode").addEventListener("click", () => {{
      manual = false;
      stopTimer();
      render();
    }});

    document.getElementById("manualMode").addEventListener("click", () => {{
      manual = true;
      render();
    }});

    document.getElementById("prev").addEventListener("click", () => {{
      manual = true;
      stopTimer();
      index = (index - 1 + frames.length) % frames.length;
      render();
    }});

    document.getElementById("next").addEventListener("click", () => {{
      manual = true;
      stopTimer();
      index = (index + 1) % frames.length;
      render();
    }});

    playPause.addEventListener("click", () => {{
      manual = true;
      if (timer !== null) {{
        stopTimer();
        render();
        return;
      }}
      timer = setInterval(() => {{
        index = (index + 1) % frames.length;
        render();
      }}, delayMs);
      playPause.textContent = "Pause";
      render();
    }});

    render();
  </script>
</body>
</html>
"""
    html_path = output_dir / "viewer.html"
    html_path.write_text(html, encoding="utf-8")
    return html_path


def main() -> int:
    parser = argparse.ArgumentParser()
    parser.add_argument("--case", required=True, help="Path to a fixed testcase JSON file.")
    parser.add_argument("--output", help="Output GIF path. Defaults to visualize/output/<case>.gif")
    parser.add_argument(
        "--output-dir",
        help="Output directory for GIF, PNG frames, and HTML viewer. Defaults to visualize/output/<case>/",
    )
    parser.add_argument("--delay-ms", type=int, default=500, help="Frame delay in milliseconds.")
    args = parser.parse_args()

    case_path = Path(args.case)
    payload = json.loads(case_path.read_text(encoding="utf-8"))
    all_points = [tuple(map(float, point)) for point in payload["points"]]
    states, result = _compute_states(all_points)
    hull_areas = [polygon_area(state["hull"]) for state in states]

    frames = [
        _render_frame(all_points, state, hull_areas, len(result["peel_order"]), case_path.stem)
        for state in states
    ]

    output_dir = Path(args.output_dir) if args.output_dir else Path("visualize/output") / case_path.stem
    output_dir.mkdir(parents=True, exist_ok=True)
    output_path = Path(args.output) if args.output else output_dir / f"{case_path.stem}_v1.gif"
    frames_dir = output_dir / "frames"
    frames_dir.mkdir(parents=True, exist_ok=True)
    frame_names: List[str] = []
    for index, frame in enumerate(frames):
        frame_name = f"frame_{index:03d}.png"
        frame_names.append(f"frames/{frame_name}")
        frame.save(frames_dir / frame_name, format="PNG")

    frames[0].save(
        output_path,
        save_all=True,
        append_images=frames[1:],
        duration=args.delay_ms,
        loop=0,
        disposal=2,
    )
    html_path = _write_html_viewer(output_dir, case_path.stem, output_path.name, frame_names, args.delay_ms)
    print(html_path)
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
