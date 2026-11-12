#!/usr/bin/env bash
# Run a FreeCAD Python script headlessly (no GUI).
#
# Usage:  scripts/freecad_run.sh path/to/script.py
#
# The FreeCAD binary is found on PATH as `freecadcmd`, `FreeCADCmd` or
# `freecad-cmd`. Set FREECAD_CMD to point at a specific binary if needed.
set -euo pipefail

if [ $# -ne 1 ]; then
  echo "usage: $0 path/to/script.py" >&2
  exit 2
fi

script="$1"
if [ ! -f "$script" ]; then
  echo "error: script not found: $script" >&2
  exit 2
fi

bin="${FREECAD_CMD:-}"
if [ -z "$bin" ]; then
  for candidate in freecadcmd FreeCADCmd freecad-cmd; do
    if command -v "$candidate" >/dev/null 2>&1; then
      bin="$candidate"
      break
    fi
  done
fi

if [ -z "$bin" ]; then
  echo "error: FreeCAD command-line binary not found." >&2
  echo "Install FreeCAD, or set FREECAD_CMD to its path. See CLAUDE.md." >&2
  exit 127
fi

# Avoid needing a display when Qt is loaded.
export QT_QPA_PLATFORM="${QT_QPA_PLATFORM:-offscreen}"

exec "$bin" "$script"
