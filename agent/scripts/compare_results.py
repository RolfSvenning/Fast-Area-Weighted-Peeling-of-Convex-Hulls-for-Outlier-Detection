#!/usr/bin/env python3
"""Compare implementation output against the fixed oracle suite."""

from __future__ import annotations

import json
import math
import sys
from pathlib import Path
from typing import Any, Dict, List

FLOAT_TOLERANCE = 1e-9


def _compare_values(expected: Any, actual: Any, path: str, diffs: List[str]) -> None:
    if isinstance(expected, list) and isinstance(actual, list):
        if len(expected) != len(actual):
            diffs.append(f"{path}: length mismatch expected {len(expected)} got {len(actual)}")
            return
        for index, (expected_item, actual_item) in enumerate(zip(expected, actual)):
            _compare_values(expected_item, actual_item, f"{path}[{index}]", diffs)
        return

    if isinstance(expected, float) or isinstance(actual, float):
        if not math.isclose(float(expected), float(actual), rel_tol=0.0, abs_tol=FLOAT_TOLERANCE):
            diffs.append(f"{path}: expected {expected} got {actual}")
        return

    if expected != actual:
        diffs.append(f"{path}: expected {expected} got {actual}")


def compare_json(gold_file: Path, test_file: Path) -> List[str]:
    gold = json.loads(gold_file.read_text(encoding="utf-8"))
    if not test_file.exists():
        return [f"missing output file: {test_file.name}"]
    test = json.loads(test_file.read_text(encoding="utf-8"))

    diffs: List[str] = []
    if "error" in test:
        diffs.append(f"runtime error: {test['error']}")
        return diffs

    _compare_values(gold["expected"]["peel_order"], test.get("peel_order"), "peel_order", diffs)
    _compare_values(gold["expected"]["area_decreases"], test.get("area_decreases"), "area_decreases", diffs)
    _compare_values(gold["expected"]["hulls"], test.get("hulls"), "hulls", diffs)
    return diffs


def main(gold_dir: str, test_dir: str, pass_rate_file: str, report_file: str) -> int:
    gold_path = Path(gold_dir)
    test_path = Path(test_dir)
    pass_rate_path = Path(pass_rate_file)
    report_path = Path(report_file)
    gold_files = sorted(path for path in gold_path.iterdir() if path.suffix == ".json")
    passed = 0
    total = len(gold_files)
    failures: Dict[str, List[str]] = {}

    for gold_file in gold_files:
        diffs = compare_json(gold_file, test_path / gold_file.name)
        if diffs:
            failures[gold_file.name] = diffs
        else:
            passed += 1

    pass_rate = (passed / total) * 100 if total else 0.0
    pass_rate_path.parent.mkdir(parents=True, exist_ok=True)
    pass_rate_path.write_text(f"{pass_rate:.2f}", encoding="utf-8")

    report_lines = [f"# Divergence Report", f"Pass Rate: {pass_rate:.2f}%", ""]
    if failures:
        report_lines.append("## Failed Cases")
        for case_name, diffs in failures.items():
            report_lines.append(f"- {case_name}")
            for diff in diffs:
                report_lines.append(f"  - {diff}")
    else:
        report_lines.append("No failed cases.")
    report_path.parent.mkdir(parents=True, exist_ok=True)
    report_path.write_text("\n".join(report_lines) + "\n", encoding="utf-8")

    if pass_rate == 100.0:
        return 0
    if pass_rate >= 99.0:
        return 2
    return 1


if __name__ == "__main__":
    raise SystemExit(main(sys.argv[1], sys.argv[2], sys.argv[3], sys.argv[4]))
