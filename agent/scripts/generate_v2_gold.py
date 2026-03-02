#!/usr/bin/env python3
"""Generate fixed V2 golden test cases with per-peel layer snapshots."""

from __future__ import annotations

import argparse
import json
from pathlib import Path

from algorithms_and_data_structures.convex_hull import andrews_monotone_chain
from v2.generator import generate_v2_expected


def main() -> int:
    parser = argparse.ArgumentParser()
    parser.add_argument("--input-dir", default="testcases/v1_gold")
    parser.add_argument("--output-dir", default="testcases/v2_gold")
    args = parser.parse_args()

    input_dir = Path(args.input_dir)
    output_dir = Path(args.output_dir)
    output_dir.mkdir(parents=True, exist_ok=True)
    for existing in output_dir.glob("*.json"):
        existing.unlink()

    for case_file in sorted(path for path in input_dir.iterdir() if path.suffix == ".json"):
        payload = json.loads(case_file.read_text(encoding="utf-8"))
        output_payload = {
            "case_id": payload["case_id"],
            "points": payload["points"],
            "expected": generate_v2_expected(payload["points"], andrews_monotone_chain),
            "metadata": {
                **payload["metadata"],
                "source_suite": "v1_gold",
                "layer_snapshot_rule": "layers_after_peel",
            },
        }
        output_path = output_dir / case_file.name
        output_path.write_text(json.dumps(output_payload, indent=2) + "\n", encoding="utf-8")

    return 0


if __name__ == "__main__":
    raise SystemExit(main())
