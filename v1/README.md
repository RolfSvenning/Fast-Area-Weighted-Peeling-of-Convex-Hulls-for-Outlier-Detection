`v1/` contains the brute-force oracle implementation and its fixed-case generation logic.
This version is the source of truth for all later stages: every optimized implementation must reproduce its outputs on the frozen golden suite.
The oracle evaluates every current hull vertex deletion, recomputes the hull, measures the area decrease via the shared Shoelace Formula helper, and chooses the unique maximum decrease.
It is intentionally correctness-first rather than performance-first, and it should remain simple enough to audit whenever later stages diverge.
The frozen suite is additionally certified by a suite audit and by checking that both supported convex hull algorithms produce the same oracle output.
