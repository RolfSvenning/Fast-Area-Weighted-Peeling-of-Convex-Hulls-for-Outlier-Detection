"""CLI entrypoint for running fixed test cases against an implementation version."""

from __future__ import annotations

import argparse
import json
from pathlib import Path
from typing import Iterable

from algorithms_and_data_structures.convex_hull import andrews_monotone_chain, jarvis_march
from v1.oracle import AmbiguousPeelError, v1_area_weighted_peeling

CONVEX_HULL_ALGORITHMS = {
    "andrews_monotone_chain": andrews_monotone_chain,
    "jarvis_march": jarvis_march,
}


def _iter_case_files(input_dir: Path) -> Iterable[Path]:
    return sorted(path for path in input_dir.iterdir() if path.suffix == ".json")


def run_v1(input_dir: Path, output_dir: Path, convex_hull_algorithm_name: str) -> None:
    try:
        hull_algorithm = CONVEX_HULL_ALGORITHMS[convex_hull_algorithm_name]
    except KeyError as error:
        known = ", ".join(sorted(CONVEX_HULL_ALGORITHMS))
        raise ValueError(
            f"Unknown convex hull algorithm '{convex_hull_algorithm_name}'. Known algorithms: {known}."
        ) from error
    output_dir.mkdir(parents=True, exist_ok=True)
    for existing in output_dir.glob("*.json"):
        existing.unlink()

    for case_file in _iter_case_files(input_dir):
        payload = json.loads(case_file.read_text(encoding="utf-8"))
        try:
            result = v1_area_weighted_peeling(payload["points"], convex_hull_algorithm=hull_algorithm)
        except AmbiguousPeelError as error:
            result = {"error": str(error)}
        output_path = output_dir / case_file.name
        output_path.write_text(json.dumps(result, indent=2) + "\n", encoding="utf-8")


def main() -> int:
    parser = argparse.ArgumentParser()
    parser.add_argument("--version", required=True)
    parser.add_argument("--input_dir", required=True)
    parser.add_argument("--output_dir", required=True)
    parser.add_argument("--convex_hull_algorithm", default="andrews_monotone_chain")
    args = parser.parse_args()

    if args.version != "v1":
        raise ValueError(f"Unsupported version: {args.version}")

    run_v1(Path(args.input_dir), Path(args.output_dir), args.convex_hull_algorithm)
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
