Agent-facing operational files live here.
`agent/scripts/` contains generation, verification, consistency checks, and the frozen-suite audit.
`agent/temp_files/` contains disposable outputs from the latest verification runs.
Plans also live here so the workflow stays local to the repo.
Versioned algorithm pseudocode lives in `agent/ALGORITHM_PSEUDOCODE.md`.
The main certification command is `PYTHONPATH=. python3 agent/scripts/audit_v1_suite.py`.
