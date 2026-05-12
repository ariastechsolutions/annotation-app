# SAR Annotation Desktop - Pages Guide

## App Context
This desktop app is a geospatial annotation tool for paired SAR and optical raster tiles.

It is designed for local folders with a matching tile structure:
- `sar_tiles/`
- `optical_tiles/`

The app loads one matching SAR/optical tile pair at a time, lets the user annotate building bounding boxes, then exports:
- georeferenced raster masks to `Masks/`
- GeoJSON polygon annotations to `Polygons/`

The annotation workflow is tile-based and depends on the tile georeferencing embedded in the TIFF files.

## Main Workflow
1. Load a local project root and point the app to SAR and optical tile folders.
2. Fill in project-wide metadata.
3. Review the current SAR and optical tile pair side by side.
4. Draw bounding boxes on either view with synchronized zoom and pan.
5. Move to the metadata page to label each box.
6. Save the tile and advance to the next one, or skip tiles with no annotations.

## Pages

### 1. Setup Page
Class: `SetupPage`

Purpose:
- Collect project input paths and project-wide metadata before annotation starts.

Components:
- `QLineEdit` for `project_root`
- `QLineEdit` for `sar_dir`
- `QLineEdit` for `optical_dir`
- `QLineEdit` for `output_dir`
- `QLineEdit` for `disaster_type`
- `QLineEdit` for `acquisition_date`
- `QLineEdit` for `sar_resolution`
- `QLineEdit` for `optical_resolution`
- `Browse` buttons for folder fields
- `Load Project` button
- Intro/help text panel

Behavior:
- Scans the SAR and optical folders for matching tile names.
- Prepares the output folders if they do not already exist.
- Starts the annotation workflow after the project is loaded.

### 2. Annotation Page
Class: `AnnotatePage`

Purpose:
- Show the current SAR and optical tile pair side by side.
- Allow bounding box creation and selection.

Components:
- Header strip with:
  - tile title
  - workflow subtitle
  - progress label
  - mode label
  - action buttons
- Left viewer pane:
  - `ImagePane` for SAR
- Right viewer pane:
  - `ImagePane` for optical
- Right inspector panel:
  - project summary text
  - box list
  - helper note
- Action buttons:
  - `Fit`
  - `Draw`
  - `Select`
  - `Skip`
  - `Next`

Behavior:
- Displays the SAR and optical rasters in a synchronized viewport.
- Supports zoom, pan, box drawing, and box selection.
- Mirrors annotations across both panes because boxes are stored in world coordinates.
- `Next` moves to the metadata page for the current tile.
- `Skip` advances to the next tile without saving annotations.

### 3. Metadata Page
Class: `MetadataPage`

Purpose:
- Review and edit metadata for each bounding box before export.

Components:
- Header strip with:
  - metadata title
  - subtitle
- Left viewer pane:
  - SAR-only `ImagePane`
- Right inspector panel:
  - box list
  - box selector
  - building status dropdown
  - damage level dropdown
  - xmin/ymin/xmax/ymax numeric fields
  - summary text
- Footer actions:
  - `Back to Annotation`
  - `Skip Tile`
  - `Save Tile & Next Tile`

Behavior:
- Shows the SAR tile with all boxes.
- Highlights the selected box.
- Lets the user edit box geometry and metadata.
- Saves masks and GeoJSON for the current tile, then moves forward.

## Shared UI Components

### `ImagePane`
Purpose:
- Custom raster viewer for SAR and optical tiles.

Responsibilities:
- Displays the fitted raster image.
- Handles mouse zoom and pan.
- Handles box drawing and box selection.
- Keeps annotations aligned with the georeferenced viewport.

### `OverlayWidget`
Purpose:
- Transparent overlay above the image display.

Responsibilities:
- Draws bounding boxes.
- Draws temporary rubber-band box previews.
- Draws optional debug bounds.

### Toolbar and Status Bar
Purpose:
- Provide global actions and feedback.

Toolbar actions:
- `Load Project`
- `Fit`
- `Select`
- `Draw`
- `Next`
- `Skip`
- `Save`

Status bar:
- Shows the current tile index, tile name, and active phase.

## Export Outputs

### Masks
Each tile produces a georeferenced GeoTIFF mask with 3 bands:
1. binary polygon mask
2. building status mask
3. damage level mask

### Polygons
Each tile produces a GeoJSON file with:
- box coordinates converted from the tile georeferencing
- box metadata
- project metadata
- tile metadata

## Notes on Behavior
- Only the current tile pair is loaded for viewing.
- Tile pairing is based on matching TIFF filenames.
- The app uses geospatial bounds so annotations can be exported consistently.
- The UI is intentionally dark and workspace-oriented for long annotation sessions.
