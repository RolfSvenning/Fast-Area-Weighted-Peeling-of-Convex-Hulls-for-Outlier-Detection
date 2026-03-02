`v2/` contains the completed layered implementation path.
The current version uses a linked-list-backed convex layer manager with constant-time single-node deletion and local upward restoration by moving contiguous promoted chains between adjacent layers.
Its correctness target is exact agreement with the frozen `V1` peel trace plus the `V2`-specific `layers_after_peel` snapshots in `testcases/v2_gold/`.
The previous list-backed manager is kept in `v2/list_convex_layer.py` as the golden `V2` reference implementation used to generate the frozen layered suite.
The active linked-list-backed manager lives in `v2/linked_convex_layer.py`.
Candidate sensitivities are computed directly from `L1` and `L2`: for each hull point, `V2` finds its active chain on the next layer using tangent / visible-chain queries and evaluates the shoelace area of the resulting local polygon.
For `V2`, tangent and active-chain discovery are still allowed to run in linear time; logarithmic tangent-query data structures are deferred to `V3`.
Use `PYTHONPATH=. python3 agent/scripts/audit_v2_suite.py` to certify the frozen layered suite and refresh `testcases/v2_gold_manifest.json`.
