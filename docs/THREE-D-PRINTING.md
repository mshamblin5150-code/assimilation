# Example: from a simple description to a 3D print

Operator: “I want a wall mount for three screwdrivers for my Bambu Lab printer.”

1. Clarify relevant dimensions, mounting method, tool weights, environment, available filament, printer bed, and tolerances using the equivalent of `grill-with-docs`; write durable material/design choices as ADRs when appropriate.
2. Use a parametric CAD tool (e.g. OpenSCAD/CadQuery) **if installed**. AI writing CAD source is not the same thing as executing geometry export.
3. Produce editable CAD source and **actual STL/3MF** only when an available exporter has successfully generated it. Otherwise state that source code needs to be run locally; do not call an image a CAD model.
4. Validate watertight geometry, dimensions, alignment, screw clearance, slicer settings, material properties, structural loads, and print orientation. A reviewer independently tests the claims.
5. Slice with Bambu Studio, prototype, measure real fit, adjust CAD parameters, and repeat. Never certify load-bearing or safety-critical parts from model confidence alone.

This example illustrates transferable engineering method, **not** a special dependency of the doctrine on one 3D-printer brand.
