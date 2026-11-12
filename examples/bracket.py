"""Example parametric FreeCAD model: a flat bracket with a through-hole.

Run headlessly:
    scripts/freecad_run.sh examples/bracket.py

Outputs (in output/):
    bracket.FCStd  - the FreeCAD document (editable in the GUI)
    bracket.step   - STEP for CAD exchange
    bracket.stl    - STL for 3D printing / mesh viewers

Edit the PARAMETERS below and re-run to regenerate.
"""

import os

import FreeCAD as App
import Part

# --- PARAMETERS (millimetres) -------------------------------------------------
LENGTH = 40.0
WIDTH = 20.0
THICKNESS = 5.0
HOLE_DIAMETER = 8.0
HOLE_X = 20.0  # hole centre, measured from the bracket's origin corner
HOLE_Y = 10.0

OUT_DIR = os.path.join(os.path.dirname(os.path.abspath(__file__)), "..", "output")
# ------------------------------------------------------------------------------

os.makedirs(OUT_DIR, exist_ok=True)

doc = App.newDocument("Bracket")

base = doc.addObject("Part::Box", "Base")
base.Length = LENGTH
base.Width = WIDTH
base.Height = THICKNESS

# Tool cylinder is taller than the plate so the cut goes all the way through.
hole = doc.addObject("Part::Cylinder", "Hole")
hole.Radius = HOLE_DIAMETER / 2.0
hole.Height = THICKNESS + 2.0
hole.Placement.Base = App.Vector(HOLE_X, HOLE_Y, -1.0)

bracket = doc.addObject("Part::Cut", "Bracket")
bracket.Base = base
bracket.Tool = hole

doc.recompute()

shape = bracket.Shape
if not shape.isValid():
    raise RuntimeError("Bracket shape is invalid")

print(f"Volume: {shape.Volume:.2f} mm^3")
print(f"Bounding box: {shape.BoundBox}")

doc.saveAs(os.path.join(OUT_DIR, "bracket.FCStd"))
shape.exportStep(os.path.join(OUT_DIR, "bracket.step"))
shape.exportStl(os.path.join(OUT_DIR, "bracket.stl"))
print(f"Wrote files to {os.path.normpath(OUT_DIR)}")
