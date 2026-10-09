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

The scale factor is the entered distance divided by the pixel distance between the selected points. `MooringProject` stores the scale reference points and entered distance alongside the factor. The reference line and distance label remain visible after saving and loading. A fixed label at the top-left of the plot shows the factor in distance units per pixel, including for older projects that did not save reference points.

Selecting **Scale** starts a new two-point measurement and clears the previous scale factor, reference points, and preview. A dashed line follows the cursor after the first point, with a live angle label beside that first point. Selecting the second point draws a solid line and prompts for the actual distance. Completing the measurement exits scale mode, preventing additional scale points until **Scale** is selected again.

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
scale_points
scale_distance
origin
axis_point
rotation_deg
barge_points
quay_points
lines
barge_counter
quay_counter
```

Projects are saved as JSON in files with the `.mpl` extension. The saved data includes the fields above, but not the current view, undo/redo history, or pending interaction state. Loading restores project data and attempts to reload the referenced drawing. Older files retain their scale factor, but their unsaved reference points and entered distance cannot be recovered; define the scale again and save to preserve those details.

Closing with unsaved project changes prompts to save and close, close without saving, or cancel. Canceling the save dialog keeps the application open. Changes are detected by comparing current project data with the last successful save or load (or the initial empty project), so navigation alone does not trigger the warning.

## Implemented interactions

- Load raster drawings (`png`, `jpg`, `jpeg`, `bmp`, `tif`) and the first page of a PDF.
- Set scale, origin, and positive X-axis.
- Add barge and quay bollards; add a mooring line by selecting a barge bollard and then a quay bollard and naming the line.
- Move bollards by dragging them. Mooring lines use endpoint names, so they render from the bollards' updated positions.
- Delete an individual line or bollard. Deleting a bollard also removes its connected lines.
- Clear all lines, all barge bollards, or all quay bollards.
- Renumber bollards as `B1...` and `Q1...` in ascending coordinate order (X first, then Y when X is equal), updating connected line endpoint names. World coordinates are used when an origin is defined; otherwise drawing coordinates with Y pointing up.
- Undo/redo actions using action entries in in-memory stacks.
- Zoom around the pointer with **Ctrl + mouse wheel**.
- Pan with the middle mouse button. A Matplotlib navigation toolbar is also included.
- Reset the view with **Home**.
- Show the pointer's world X/Y coordinates in the status area, using the origin, scale, and X-axis rotation. Without a scale, coordinates are labelled as pixels; without an origin, the readout prompts to set one. Moving outside the plot clears the numeric readout without overwriting mode or action messages.

The top controls are **Home**, **Load Drawing**, **Save Project**, **Load Project**, **Scale**, **Origin**, **X-Axis**, **Barge Bollard**, **Quay Bollard**, **Move**, **Add Line**, **Undo**, **Redo**, **Delete**, **Clear Lines**, **Clear Barge**, **Clear Quay**, **Renumber**, **Export**, and **Export YAML**.

## Undo/redo limitations

Undo/redo is partial rather than a full project-state history:

- Undo is implemented for adding bollards and lines, setting the origin, moving bollards, deleting individual bollards or lines, renumbering, and the **Clear Lines**, **Clear Barge**, and **Clear Quay** actions. **Undo** and **Redo** are also available with **Ctrl+Z** and **Ctrl+Y**.
- Redo is implemented for lines, bollard moves, individual delete actions, renumbering, and the clear actions, but not for adding bollards or setting the origin.
- Renumbering and clear actions save the bollards, lines, and counters before and after the change, so undoing them also restores the names used by earlier undo steps.
- Deleting a bollard removes connected lines, but undoing that bollard deletion restores only the bollard, not its removed lines.
- Scale changes and axis changes are not recorded in the undo history.

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

- Make existing scale reference points individually editable (currently selecting **Scale** replaces the entire measurement).
- Provide controls to clear or redefine the coordinate origin and axis.
- Replace line dictionaries and bollard tuples/dictionaries with dedicated dataclasses.
- Make undo/redo cover all editing operations using complete or appropriately detailed state snapshots.

The source has view-preservation logic in `redraw()`. Bollard dragging calls `redraw()` as the point moves; the code has no separate, documented resolution for any view shift noticed after dragging.
