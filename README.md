# SAR Annotation Desktop

This folder contains the modern desktop version of the SAR annotation app built with PySide6.

## What it does

- Reads local SAR and optical TIFF tiles from a project folder.
- Matches tiles by filename.
- Shows SAR and optical tiles side by side with synchronized zoom and pan.
- Lets you draw bounding boxes on either view.
- Switches to a SAR-only metadata page for per-box labeling.
- Exports georeferenced mask TIFFs and GeoJSON files.

## Run

```powershell
pip install -r requirements.txt
python app.py
```

## Build a Windows exe

```powershell
pip install pyinstaller
.\build_exe.ps1
```

The packaged app will be created at:

```powershell
.\dist\SAR_Annotation.exe
```

You can give that single file to teammates. They do not need Python installed.

## Expected folder structure

The selected project root should contain:

- `sar_tiles/`
- `optical_tiles/`

The app will create:

- `Masks/`
- `Polygons/`
