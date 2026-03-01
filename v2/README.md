`v2/` contains the first layered implementation path.
The current version uses a list-backed convex layer manager with local suffix restoration after each peel; it no longer fully rebuilds all layers after every deletion.
Its correctness target is exact agreement with the frozen `V1` peel trace plus the `V2`-specific `layers_after_peel` snapshots in `testcases/v2_gold/`.
Use `PYTHONPATH=. python3 agent/scripts/audit_v2_suite.py` to certify the frozen layered suite and refresh `testcases/v2_gold_manifest.json`.
The tangent-query primitive is present, but the actual restoration step still recomputes adjacent merged layers rather than doing a true tangent/visible-chain splice.
