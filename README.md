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

## Build a Windows installer

To create a normal Windows installer that teammates can run like any other setup program:

1. Build the app exe first.
2. Install [Inno Setup 6](https://jrsoftware.org/isinfo.php).
3. Run:

```powershell
.\build_installer.ps1
```

The installer will be created under:

```powershell
.\installer_output\SAR_Annotation_Setup.exe
```

Give your teammates that setup file. They can double-click it to install the app on Windows.

## Expected folder structure

The selected project root should contain:

- `sar_tiles/`
- `optical_tiles/`

The app will create:

- `Masks/`
- `Polygons/`
