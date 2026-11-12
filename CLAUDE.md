# FreeCAD project guide

This repository holds FreeCAD models written as Python scripts so Claude Code
can generate and modify them.

## Layout

- `examples/` - parametric model scripts (start with `bracket.py`).
- `scripts/freecad_run.sh` - runs a script headlessly with FreeCAD's command-line build.
- `output/` - generated files (`.FCStd`, `.step`, `.stl`). Git-ignored.

## Running FreeCAD headlessly

```bash
scripts/freecad_run.sh examples/bracket.py
```

The wrapper looks for `freecadcmd`, `FreeCADCmd` or `freecad-cmd` on `PATH`.
Set `FREECAD_CMD=/full/path/to/binary` to override.

Scripts import `FreeCAD` and `Part` directly; they only run inside FreeCAD's
Python, not a plain `python3`.

## Conventions for new models

1. Put every dimension in a labelled PARAMETERS block at the top of the script, in millimetres.
2. Build geometry with `Part::` features (`Box`, `Cylinder`, `Cut`, `Fuse`) or `Part.makeXxx` so the model stays scriptable.
3. Call `doc.recompute()` and check `shape.isValid()` before exporting.
4. Export STEP for exchange and STL for printing/previews. Write only into `output/`.
5. Print key numbers (volume, bounding box) so results can be checked from the terminal.

## Verifying a change

- Run the script and confirm it exits 0 with no `RuntimeError`.
- Check the printed volume and bounding box against the parameters by hand.
- Open `output/*.step` or `output/*.stl` in any viewer if the shape matters visually.

## Environment note

This project needs a FreeCAD install that provides `freecadcmd`. Ubuntu 24.04 no
longer packages FreeCAD in apt, so in a fresh container install it another way,
for example from conda-forge (`micromamba create -c conda-forge freecad`) or the
official AppImage, and make sure the binary is on `PATH` or set `FREECAD_CMD`.
