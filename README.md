# ATS Annotation Tool

This folder contains the modern desktop version of the annotation app built with PySide6.

## What it does

- Reads local SAR and optical TIFF tiles from a project folder.
- Matches tiles by filename.
- Shows SAR and optical tiles side by side with synchronized zoom and pan.
- Lets you draw bounding boxes on either view.
- Switches to a SAR-only metadata page for per-box labeling.
- Exports georeferenced mask TIFFs and GeoJSON files.
- Checks GitHub Releases for updates and lets the user install them after confirmation.

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
.\dist\ATS_Annotation_Tool.exe
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
.\installer_output\ATS_Annotation_Tool_Setup.exe
```

Give your teammates that setup file. They can double-click it to install the app on Windows.

## Update behavior

The installed ATS Annotation Tool checks the latest GitHub release on startup and also exposes a `check updates` button in the top bar.

If a newer release is found, the app prompts the user before downloading and launching the installer.

For the update flow to work, publish each new build as a GitHub Release and attach the installer `.exe` as the release asset.

## Fast update testing

The app also checks a small `update_manifest.local.json` file before it falls back to the GitHub manifest and then GitHub Releases.

That gives you a fast test path:

1. Copy `update_manifest.json` to `update_manifest.local.json`.
2. Set `latest_version` higher than the installed app version.
3. Put `update_manifest.local.json` next to the installed `.exe` during local testing.
4. Click `check updates` or restart the app.

For the real shared flow, update `update_manifest.json` in GitHub and push it. That gives all installed users a faster update signal without rebuilding the installer.

This lets you validate the update-check logic without rebuilding the installer every time.

## Expected folder structure

The selected project root should contain:

- `sar_tiles/`
- `optical_tiles/`

The app will create:

- `Masks/`
- `Polygons/`
