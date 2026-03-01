#!/usr/bin/env python3
"""Generate fixed golden test cases for the V1 oracle."""

from __future__ import annotations

import argparse
from pathlib import Path

from v1.generator import generate_case, write_case


def _parse_bucket(spec: str) -> tuple[int, int]:
    try:
        point_count_str, case_count_str = spec.split(":", 1)
        point_count = int(point_count_str)
        case_count = int(case_count_str)
    except ValueError as error:
        raise argparse.ArgumentTypeError(
            f"Invalid bucket '{spec}'. Use POINT_COUNT:CASE_COUNT, for example 100:900."
        ) from error

    if point_count < 4:
        raise argparse.ArgumentTypeError("Point count must be at least 4.")
    if case_count < 1:
        raise argparse.ArgumentTypeError("Case count must be positive.")
    return point_count, case_count


def main() -> int:
    parser = argparse.ArgumentParser()
    parser.add_argument("--count", type=int, default=10)
    parser.add_argument("--seed-start", type=int, default=1000)
    parser.add_argument("--output-dir", default="testcases/v1_gold")
    parser.add_argument("--grid-limit", type=int, default=1_000_000)
    parser.add_argument(
        "--bucket",
        action="append",
        type=_parse_bucket,
        help="Generate POINT_COUNT:CASE_COUNT cases. Can be provided multiple times.",
    )
    args = parser.parse_args()

    output_dir = Path(args.output_dir)
    for existing in output_dir.glob("*.json"):
        existing.unlink()

    case_specs = args.bucket or [(10, args.count)]

    case_id = 1
    seed = args.seed_start
    for point_count, case_count in case_specs:
        for _ in range(case_count):
            payload = generate_case(
                case_id=case_id,
                seed=seed,
                point_count=point_count,
                grid_limit=args.grid_limit,
            )
            write_case(output_dir, payload)
            case_id += 1
            seed += 1
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
