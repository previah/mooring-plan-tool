# Mooring Plan Creator - Development Summary

This document describes the implementation currently present in the project scripts. Proposed work and known limitations are identified separately from implemented features.

## Project purpose

The Python/Tkinter application displays an engineering drawing and lets the user place barge and quay bollards, connect them with mooring lines, and export project data.

## Source files

### `mooring_plan.py`

Contains `MooringPlanner`, which owns the GUI, interaction modes, project operations, save/load, undo/redo, and exports. The module also starts the Tk application at the end of the file.

### `models.py`

Contains:

- `MooringProject`, a dataclass holding the drawing reference, scale factor, coordinate origin and axis, rotation, bollard dictionaries, line list, and bollard counters.
- `CoordinateSystem`, holding an origin, scale, and rotation.
- `CoordinateTransformer`, which converts image coordinates to world coordinates.
- `Point`, a dataclass currently not used by the project state.

Draft `BollardType` and `Bollard` definitions are commented out. There is no `MooringLine` dataclass; mooring lines are dictionaries.

### `plot_renderer.py`

Contains `PlotRenderer`, which draws scale points, the coordinate-system origin and axes, bollards, mooring lines, and coordinate-axis previews onto the Matplotlib axes.

## Coordinate system and scale

### Setting the origin and X-axis

1. Select **Origin** and click a point on the drawing.
2. Select **X-Axis**. Move the pointer to preview the axis and angle, then click to set the positive X direction.

The origin and axis point are stored as image-coordinate tuples in `MooringProject`. `rotation_deg` is calculated from the origin-to-axis direction. The scale is defined separately by selecting two reference points and entering their real-world distance.

The scale factor is the entered distance divided by the pixel distance between the selected points. Scale reference points are held in `MooringPlanner.scale_points`, not in `MooringProject`.

### Image-to-world conversion

`CoordinateTransformer.image_to_world(x, y)` first offsets the image point from the origin, flips the image Y direction, applies the scale, then rotates by the negative of `rotation_deg`:

```python
dx = (x - origin_x) * scale
dy = (origin_y - y) * scale
angle = math.radians(rotation_deg)

world_x = dx * math.cos(angle) + dy * math.sin(angle)
world_y = -dx * math.sin(angle) + dy * math.cos(angle)
```

This is the transformation currently used for exported bollard coordinates. The renderer draws the origin and axis directions using the same stored rotation convention.

## Project data and persistence

`MooringProject` currently stores:

```text
background_file
scale_factor
origin
axis_point
rotation_deg
barge_points
quay_points
lines
barge_counter
quay_counter
```

Projects are saved as JSON in files with the `.mpl` extension. The saved data includes the fields above, but not the separate scale reference points, current view, undo/redo history, or pending interaction state. Loading restores project data and attempts to reload the referenced drawing.

## Implemented interactions

- Load raster drawings (`png`, `jpg`, `jpeg`, `bmp`, `tif`) and the first page of a PDF.
- Set scale, origin, and positive X-axis.
- Add barge and quay bollards; add a mooring line by selecting a barge bollard and then a quay bollard and naming the line.
- Move bollards by dragging them. Mooring lines use endpoint names, so they render from the bollards' updated positions.
- Delete an individual line or bollard. Deleting a bollard also removes its connected lines.
- Clear all lines, all barge bollards, or all quay bollards.
- Renumber bollards as `B1...` and `Q1...`, updating connected line endpoint names.
- Undo/redo actions using action entries in in-memory stacks.
- Zoom around the pointer with **Ctrl + mouse wheel**.
- Pan with the middle mouse button. A Matplotlib navigation toolbar is also included.
- Reset the view with **Home**.

The top controls are **Home**, **Load Drawing**, **Save Project**, **Load Project**, **Scale**, **Origin**, **X-Axis**, **Barge Bollard**, **Quay Bollard**, **Move**, **Add Line**, **Undo**, **Redo**, **Delete**, **Clear Lines**, **Clear Barge**, **Clear Quay**, **Renumber**, **Export**, and **Export YAML**.

## Undo/redo limitations

Undo/redo is partial rather than a full project-state history:

- Undo is implemented for adding bollards and lines, setting the origin, and deleting individual bollards or lines.
- Redo is implemented for lines and individual delete actions, but not for adding bollards or setting the origin.
- Deleting a bollard removes connected lines, but undoing that bollard deletion restores only the bollard, not its removed lines.
- Clear actions, renumbering, bollard moves, scale changes, and axis changes are not recorded in the undo history.

## Exports

### CSV and plan image

**Export** creates the following files in a selected folder:

- `bollards.csv` with `Name`, `Type`, `X`, and `Y`. Bollard coordinates are transformed to world coordinates when an origin is defined. If scale is unset, the export warns and uses a scale of `1.0` (pixel units).
- `mooring_lines.csv` with `Name`, `From`, `To`, `Length`, and `Angle`. Length is the endpoint distance multiplied by the scale factor when set, otherwise it is in pixels. Angle is calculated directly from the image-coordinate endpoints.
- `mooring_plan.jpg`, a 300-DPI Matplotlib figure snapshot.

### YAML

**Export YAML** requires an origin and writes `Poi` and `Cable` mappings. Bollard positions are transformed to world coordinates, rounded to three decimals, and exported as `[x, y, 0.0]`; barge and quay points have parents `"Barge"` and `"Quay"`. Each cable uses the line's `from` and `to` bollard names as `poiA` and `poiB`, with `EA` set to an empty string.

## Known gaps and possible next features

These are not implemented in the current scripts:

- Show the pointer's world coordinates in the status area.
- Make scale reference points editable and include them in saved projects if needed.
- Provide controls to clear or redefine the coordinate origin and axis.
- Replace line dictionaries and bollard tuples/dictionaries with dedicated dataclasses.
- Make undo/redo cover all editing operations using complete or appropriately detailed state snapshots.

The source has view-preservation logic in `redraw()`. Bollard dragging calls `redraw()` as the point moves; the code has no separate, documented resolution for any view shift noticed after dragging.
