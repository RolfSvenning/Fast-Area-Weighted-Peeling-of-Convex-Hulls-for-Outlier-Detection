Shared numeric geometry lives here.
This directory contains epsilon constants and low-level predicates such as orientation, equality-under-epsilon, and general-position checks.
Higher-level algorithms should depend on these primitives rather than embedding geometric arithmetic directly.
Polygon area via the Shoelace Formula now lives in `algorithms_and_data_structures/shoelace_formula.py` so it can be reused as a shared algorithm helper.
