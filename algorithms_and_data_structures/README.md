Shared algorithms and data structures live here, including both implemented helpers and planned components for later stages.

- `convex_hull.py`: static convex hull algorithms. Current implementations are Andrew's monotone chain and Jarvis march, used to cross-check oracle stability.
- `shoelace_formula.py`: shared polygon area helpers based on the Shoelace Formula. This is the common area primitive for the oracle and later versions.
- `array_priority_queue.py`: planned basic array-based priority queue for the early optimized stages before more specialized queues are needed.
- `list_convex_layer.py`: current naive list-oriented convex layer manager for the layered stage. It rebuilds layers today, and it is the place where tangent-based restoration will be introduced next.
- `tree_convex_layer.py`: planned tree-backed convex layer manager for the efficient stage. It will also need tangent support, but with logarithmic-time queries.
- `dynamic_convex_hull.py`: planned deletion-only dynamic convex hull structure for the final stage.
