#!/bin/bash
set -euo pipefail

BRANCH=${1:?Usage: ./agent/scripts/verify_integrity.sh [branch_name] [version_string]}
VERSION=${2:?Usage: ./agent/scripts/verify_integrity.sh [branch_name] [version_string]}
TEST_DIR="./testcases/${BRANCH}_gold"
TEMP_DIR="./agent/temp_files"
RUN_DIR="${TEMP_DIR}/current_run"
REPORT_FILE="${TEMP_DIR}/divergence_report.md"
PASS_RATE_FILE="${TEMP_DIR}/last_pass_rate.txt"

echo "=== Starting Gatekeeper Loop for [$BRANCH] ==="

if [ ! -d "$TEST_DIR" ]; then
    echo "Error: No Fixed Test Suite found in $TEST_DIR. Generate Baseline first."
    exit 1
fi

mkdir -p "$RUN_DIR"
mkdir -p "$TEMP_DIR"
find "$RUN_DIR" -maxdepth 1 -type f -name '*.json' -delete

echo "Running Optimized Implementation..."
PYTHONPATH=. python3 main.py --version "$VERSION" --input_dir "$TEST_DIR" --output_dir "$RUN_DIR"

echo "Comparing against Oracle..."
python3 agent/scripts/compare_results.py "$TEST_DIR" "$RUN_DIR" "$PASS_RATE_FILE" "$REPORT_FILE"

RESULT=$?
PASS_PERCENT=$(cat "$PASS_RATE_FILE")
FAILED_CASES=$(python3 - <<'PY'
from pathlib import Path

report = Path("agent/temp_files/divergence_report.md")
if not report.exists():
    print(0)
else:
    lines = report.read_text(encoding="utf-8").splitlines()
    print(sum(1 for line in lines if line.startswith("- ")))
PY
)

printf '[%s] | Progress: %s%% | Oracle: Fixed | Manual-Flag: [%s] cases\n' "$BRANCH" "$PASS_PERCENT" "$FAILED_CASES"

if [ "$RESULT" -eq 0 ]; then
    echo "SUCCESS: 100% Match. Proceed to Commit."
    exit 0
fi

if [ "$RESULT" -eq 2 ]; then
    echo "WARNING: Progress at $PASS_PERCENT%. Flagging for Manual Inspection."
    echo "Generating $REPORT_FILE..."
    exit 0
fi

echo "FAILURE: Progress at $PASS_PERCENT%. Automatic Revert required."
exit 1
