Visualization helpers live here.
The main entrypoint is `visualize/render_v1_gif.py`, which renders a chosen fixed `V1` test case as both an animated GIF and an HTML viewer for manual step-through.
`visualize/render_v1_layers_gif.py` is a separate GIF-only renderer that shows every convex layer at each peel step.
Each frame includes the evolving hull and a second plot showing the decreasing convex-hull area curve.
Generated GIFs and `viewer.html` go in `visualize/output/<case>/`, while PNG frames go in `visualize/output/<case>/frames/`.
The checked-in example bundle currently lives under `visualize/example/case_0999/`.
