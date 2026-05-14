from __future__ import annotations

import json
import os
import re
import ctypes
import sys
import tempfile
import urllib.error
import urllib.parse
import urllib.request
from dataclasses import dataclass, field
from functools import lru_cache
from pathlib import Path

import numpy as np
import rasterio
from pyproj import Transformer
from rasterio.features import rasterize
from rasterio.transform import from_bounds
from rasterio.warp import Resampling, reproject, transform_bounds
from shapely.geometry import Polygon, mapping, shape
from PySide6.QtCore import QPointF, QRectF, Qt, QTimer, Signal, QObject, QThread, QProcess, QUrl
from PySide6.QtGui import QAction, QColor, QDesktopServices, QFont, QIcon, QImage, QPainter, QPalette, QPen, QPixmap
from PySide6.QtWidgets import (
    QApplication,
    QComboBox,
    QCheckBox,
    QDialog,
    QDialogButtonBox,
    QFileDialog,
    QFormLayout,
    QFrame,
    QGridLayout,
    QGroupBox,
    QHBoxLayout,
    QLabel,
    QLineEdit,
    QListWidget,
    QListWidgetItem,
    QMainWindow,
    QMessageBox,
    QPushButton,
    QScrollArea,
    QDoubleSpinBox,
    QSplitter,
    QStackedWidget,
    QStatusBar,
    QToolBar,
    QVBoxLayout,
    QWidget,
)


APP_TITLE = "ATS Annotation Tool"
APP_VERSION = "1.0.12"
UPDATE_OWNER = "ariastechsolutions"
UPDATE_REPO = "annotation-app"
UPDATE_API_URL = f"https://api.github.com/repos/{UPDATE_OWNER}/{UPDATE_REPO}/releases/latest"
UPDATE_MANIFEST_URL = f"https://raw.githubusercontent.com/{UPDATE_OWNER}/{UPDATE_REPO}/master/qt_desktop/update_manifest.json"
TILE_NAME_RE = re.compile(r"tile_r(?P<row>-?\d+)_c(?P<col>-?\d+)\.tif$", re.IGNORECASE)
NATURAL_PARTS_RE = re.compile(r"(\d+)")

DARK_TOKENS = {
    "bg0": "#0e0f11",
    "bg1": "#16181c",
    "bg2": "#1e2128",
    "bg3": "#272b33",
    "bg4": "#303540",
    "border": "rgba(255,255,255,0.08)",
    "border_strong": "rgba(255,255,255,0.16)",
    "text_primary": "#e8eaf0",
    "text_secondary": "#8b93a6",
    "text_muted": "#525968",
    "accent": "#4ade80",
    "accent_dim": "rgba(74,222,128,0.12)",
    "accent_border": "rgba(74,222,128,0.3)",
}

LIGHT_TOKENS = {
    "bg0": "#f0f1f3",
    "bg1": "#ffffff",
    "bg2": "#f4f5f7",
    "bg3": "#e8eaed",
    "bg4": "#dde0e5",
    "border": "rgba(0,0,0,0.07)",
    "border_strong": "rgba(0,0,0,0.14)",
    "text_primary": "#111318",
    "text_secondary": "#4a5168",
    "text_muted": "#8a92a6",
    "accent": "#16a34a",
    "accent_dim": "rgba(22,163,74,0.1)",
    "accent_border": "rgba(22,163,74,0.3)",
}


def apply_dark_theme(app: QApplication) -> None:
    apply_theme(app, DARK_TOKENS)


def resource_path(name: str) -> Path:
    base = Path(getattr(sys, "_MEIPASS", Path(__file__).resolve().parent))
    return base / name


def runtime_root() -> Path:
    if getattr(sys, "frozen", False):
        return Path(sys.executable).resolve().parent
    return Path(__file__).resolve().parent


DEFAULT_ROOT = Path.cwd() / "coregistered_data"
RECENT_PROJECTS_PATH = Path.home() / ".sar_annotation_recent_projects.json"
APP_ICON_PATH = resource_path("ats_bar_logo.png")
APP_LOGO_PATH = resource_path("ats_logo.png")
LOCAL_UPDATE_MANIFEST_PATH = runtime_root() / "update_manifest.local.json"


def apply_theme(app: QApplication, t: dict) -> None:
    app.setStyle("Fusion")
    app.setFont(QFont("Consolas", 9))
    palette = QPalette()
    palette.setColor(QPalette.Window, QColor(t["bg0"]))
    palette.setColor(QPalette.WindowText, QColor(t["text_primary"]))
    palette.setColor(QPalette.Base, QColor(t["bg2"]))
    palette.setColor(QPalette.AlternateBase, QColor(t["bg1"]))
    palette.setColor(QPalette.ToolTipBase, QColor(t["bg1"]))
    palette.setColor(QPalette.ToolTipText, QColor(t["text_primary"]))
    palette.setColor(QPalette.Text, QColor(t["text_primary"]))
    palette.setColor(QPalette.Button, QColor(t["bg1"]))
    palette.setColor(QPalette.ButtonText, QColor(t["text_primary"]))
    palette.setColor(QPalette.BrightText, QColor("#f87171"))
    palette.setColor(QPalette.Highlight, QColor(t["accent"]))
    palette.setColor(QPalette.HighlightedText, QColor(t["bg0"]))
    app.setPalette(palette)
    app.setStyleSheet(
        f"""
        QMainWindow, QWidget {{
            background: {t["bg0"]};
            color: {t["text_primary"]};
        }}
        QFrame#TopBar {{
            background: {t["bg1"]};
            border-bottom: 1px solid {t["border_strong"]};
        }}
        QLabel#Logo {{
            font-family: "Segoe UI";
            font-size: 13px;
            font-weight: 700;
            letter-spacing: 0.08em;
            color: {t["text_primary"]};
            text-transform: uppercase;
        }}
        QLabel {{
            background: transparent;
        }}
        QPushButton, QToolButton {{
            background: {t["bg2"]};
            color: {t["text_primary"]};
            border: 1px solid {t["border"]};
            border-radius: 6px;
            padding: 7px 12px;
            font-weight: 500;
        }}
        QPushButton:hover, QToolButton:hover {{
            background: {t["bg3"]};
        }}
        QPushButton:checked, QToolButton:checked {{
            background: {t["accent_dim"]};
            border-color: {t["accent_border"]};
            color: {t["accent"]};
        }}
        QPushButton[accent="true"] {{
            background: {t["accent_dim"]};
            color: {t["accent"]};
            border-color: {t["accent_border"]};
        }}
        QPushButton[accent="true"]:hover {{
            background: {t["accent"]};
            color: {t["bg0"]};
            border-color: {t["accent"]};
        }}
        QLineEdit, QComboBox, QDoubleSpinBox, QListWidget {{
            background: {t["bg0"]};
            border: 1px solid {t["border_strong"]};
            border-radius: 5px;
            padding: 6px 10px;
            selection-background-color: {t["accent_dim"]};
            selection-color: {t["accent"]};
            color: {t["text_primary"]};
            font-family: "DM Mono", "Courier New", monospace;
            font-size: 12px;
        }}
        QCheckBox {{
            background: transparent;
            color: {t["text_primary"]};
            spacing: 8px;
            font-family: "DM Mono", "Courier New", monospace;
            font-size: 11px;
        }}
        QCheckBox::indicator {{
            width: 14px;
            height: 14px;
            border-radius: 4px;
            border: 1px solid {t["border_strong"]};
            background: {t["bg0"]};
        }}
        QCheckBox::indicator:checked {{
            background: {t["accent_dim"]};
            border-color: {t["accent_border"]};
        }}
        QLineEdit:focus, QComboBox:focus, QDoubleSpinBox:focus, QListWidget:focus {{
            border-color: {t["accent_border"]};
        }}
        QComboBox QAbstractItemView {{
            background-color: {t["bg0"]};
            border: 1px solid {t["border_strong"]};
            color: {t["text_primary"]};
            selection-background-color: {t["accent_dim"]};
            selection-color: {t["text_primary"]};
            padding: 4px;
        }}
        QComboBox::drop-down {{
            border: 0;
            width: 24px;
        }}
        QStatusBar {{
            background: {t["bg1"]};
            color: {t["text_secondary"]};
        }}
        QGroupBox {{
            border: 1px solid {t["border_strong"]};
            border-radius: 8px;
            margin-top: 10px;
            padding-top: 16px;
            background: {t["bg1"]};
        }}
        QGroupBox::title {{
            subcontrol-origin: margin;
            left: 12px;
            padding: 0 4px;
            color: {t["text_primary"]};
            font-weight: 700;
        }}
        QFrame#HeaderBar, QFrame#InspectorPanel, QFrame#WorkspacePanel, QFrame#SurfacePanel {{
            background: {t["bg1"]};
            border: 1px solid {t["border_strong"]};
            border-radius: 8px;
        }}
        QFrame#ImagePane {{
            background: {t["bg0"]};
            border: 1px solid {t["border"]};
            border-radius: 8px;
        }}
        QLabel#ImageSurface {{
            background: {t["bg0"]};
            border: 0;
        }}
        QLabel#PaneTitle {{
            background: transparent;
            color: {t["text_primary"]};
        }}
        QLabel#HeroTitle, QLabel#BigTitle {{
            font-size: 24px;
            font-weight: 800;
            letter-spacing: -0.03em;
            color: {t["text_primary"]};
        }}
        QLabel#HeroSubtitle {{
            color: {t["text_secondary"]};
            font-size: 13px;
        }}
        QLabel#TileTitle {{
            font-size: 18px;
            font-weight: 700;
            color: {t["text_primary"]};
        }}
        QLabel#SectionTitle {{
            color: {t["text_primary"]};
            font-size: 13px;
            font-weight: 700;
            letter-spacing: 0.05em;
            text-transform: uppercase;
        }}
        QLabel#PanelHint, QLabel#MutedText {{
            color: {t["text_secondary"]};
            background: transparent;
        }}
        QPushButton#TabBtn, QPushButton[navtab="true"] {{
            background: transparent;
            border: 1px solid {t["border"]};
            color: {t["text_secondary"]};
            border-radius: 6px;
            padding: 4px 14px;
            font-size: 11px;
            letter-spacing: 1px;
            font-family: "DM Mono", monospace;
        }}
        QPushButton#TabBtn:hover, QPushButton[navtab="true"]:hover {{
            background: {t["bg3"]};
            color: {t["text_primary"]};
        }}
        QPushButton#TabBtn:checked, QPushButton[navtab="true"]:checked {{
            background: {t["accent_dim"]};
            border-color: {t["accent_border"]};
            color: {t["accent"]};
        }}
        QPushButton#ModeToggle {{
            background: transparent;
            color: {t["text_muted"]};
            border: 1px solid {t["border"]};
            border-radius: 6px;
            padding: 4px 12px;
            font-size: 11px;
            font-family: "DM Mono", monospace;
        }}
        QPushButton#ModeToggle:hover {{
            background-color: {t["bg3"]};
            color: {t["text_primary"]};
        }}
        QLabel#UpdateLog {{
            background: transparent;
            color: {t["text_secondary"]};
            font-size: 11px;
            font-family: "DM Mono", monospace;
            padding: 0 4px;
        }}
        QLabel#VersionPill {{
            background: {t["bg2"]};
            color: {t["text_secondary"]};
            border: 1px solid {t["border"]};
            border-radius: 6px;
            padding: 4px 8px;
            font-size: 11px;
            font-family: "DM Mono", monospace;
        }}
        QPushButton#BrowseBtn {{
            background: {t["bg3"]};
            border: 1px solid {t["border_strong"]};
            color: {t["text_secondary"]};
            border-radius: 5px;
            padding: 5px 10px;
            font-size: 11px;
        }}
        QPushButton#BrowseBtn:hover {{
            background: {t["bg4"]};
            color: {t["text_primary"]};
        }}
        QPushButton#LoadBtn {{
            background: {t["accent_dim"]};
            border: 1px solid {t["accent_border"]};
            color: {t["accent"]};
            border-radius: 5px;
            padding: 9px 0;
            font-family: "Syne", "Segoe UI", sans-serif;
            font-size: 12px;
            font-weight: 700;
            letter-spacing: 2px;
            text-transform: uppercase;
        }}
        QPushButton#LoadBtn:hover {{
            background: {t["accent"]};
            color: {t["bg0"]};
        }}
        QPushButton#NextBtn, QPushButton#SaveBtn {{
            background: {t["accent_dim"]};
            border: 1px solid {t["accent_border"]};
            color: {t["accent"]};
        }}
        QPushButton#NextBtn:hover, QPushButton#SaveBtn:hover {{
            background: {t["accent"]};
            color: {t["bg0"]};
        }}
        QPushButton#SkipBtn, QPushButton#Skip2Btn, QPushButton#BackBtn {{
            background: transparent;
            border: 1px solid {t["border"]};
            color: {t["text_secondary"]};
        }}
        QPushButton#SkipBtn:hover, QPushButton#Skip2Btn:hover, QPushButton#BackBtn:hover {{
            background: {t["bg3"]};
            color: {t["text_primary"]};
        }}
        QListWidget::item {{
            padding: 8px 10px;
            border-radius: 8px;
        }}
        QListWidget::item:selected {{
            background: {t["accent_dim"]};
            color: {t["text_primary"]};
        }}
        QSplitter::handle {{
            background: {t["bg3"]};
        }}
        QScrollArea {{
            border: 0;
            background: transparent;
        }}
        QProgressBar {{
            background: {t["bg4"]};
            border: none;
            border-radius: 2px;
            height: 3px;
            max-height: 3px;
            text-align: center;
            color: transparent;
        }}
        QProgressBar::chunk {{
            background: {t["accent"]};
            border-radius: 2px;
        }}
        """
    ) 


def normalize_version(value: str) -> tuple[int, ...]:
    cleaned = str(value).strip()
    if cleaned.lower().startswith("v"):
        cleaned = cleaned[1:]
    parts: list[int] = []
    for chunk in cleaned.split("."):
        match = re.match(r"(\d+)", chunk)
        if not match:
            break
        parts.append(int(match.group(1)))
    return tuple(parts)


def version_is_newer(latest: str, current: str) -> bool:
    try:
        return normalize_version(latest) > normalize_version(current)
    except Exception:
        return False


def choose_release_asset(release: dict) -> dict | None:
    assets = release.get("assets", [])
    if not isinstance(assets, list):
        return None
    preferred = []
    fallback = []
    for asset in assets:
        if not isinstance(asset, dict):
            continue
        name = str(asset.get("name", "")).lower()
        if not name.endswith(".exe"):
            continue
        fallback.append(asset)
        if "setup" in name or "installer" in name:
            preferred.append(asset)
    if preferred:
        return preferred[0]
    if fallback:
        return fallback[0]
    return None


def fetch_json(url: str, timeout: int = 10) -> dict:
    request = urllib.request.Request(
        url,
        headers={
            "Accept": "application/json",
            "User-Agent": f"{APP_TITLE}/{APP_VERSION}",
        },
    )
    with urllib.request.urlopen(request, timeout=timeout) as response:
        return json.loads(response.read().decode("utf-8"))


def load_json_file(path: Path) -> dict:
    return json.loads(path.read_text(encoding="utf-8"))


class UpdateCheckWorker(QObject):
    finished = Signal(object)
    failed = Signal(str)

    def __init__(self, current_version: str):
        super().__init__()
        self.current_version = current_version

    def run(self):
        manifest = None
        manifest_source = ""

        if LOCAL_UPDATE_MANIFEST_PATH.is_file():
            try:
                manifest = load_json_file(LOCAL_UPDATE_MANIFEST_PATH)
                manifest_source = "local override"
            except Exception as exc:
                self.failed.emit(f"Local update manifest is invalid: {exc}")
                return
        else:
            try:
                manifest = fetch_json(UPDATE_MANIFEST_URL, timeout=6)
                manifest_source = "GitHub manifest"
            except urllib.error.HTTPError as exc:
                if exc.code != 404:
                    self.failed.emit(f"GitHub manifest returned HTTP {exc.code}: {exc.reason}")
                    return
            except Exception:
                manifest = None

        try:
            manifest = manifest if isinstance(manifest, dict) else None
        except Exception:
            manifest = None

        if isinstance(manifest, dict):
            tag = str(manifest.get("latest_version", manifest.get("tag_name", ""))).strip()
            if tag and version_is_newer(tag, self.current_version):
                release_url = str(manifest.get("release_url", "")).strip()
                download_url = str(manifest.get("download_url", "")).strip()
                payload = {
                    "available": True,
                    "status": "update_available",
                    "source": manifest_source or "manifest",
                    "latest_version": tag,
                    "release_name": str(manifest.get("release_name", f"ATS Annotation Tool {tag}")).strip(),
                    "body": str(manifest.get("body", "")).strip(),
                    "html_url": release_url,
                    "download_url": download_url,
                    "asset_name": str(manifest.get("asset_name", "")).strip(),
                }
                if not payload["download_url"]:
                    try:
                        release = fetch_json(UPDATE_API_URL, timeout=10)
                        asset = choose_release_asset(release)
                        payload["download_url"] = asset.get("browser_download_url") if asset else ""
                        payload["asset_name"] = asset.get("name") if asset else ""
                        payload["html_url"] = payload["html_url"] or str(release.get("html_url", "")).strip()
                        payload["body"] = payload["body"] or str(release.get("body", "")).strip()
                        payload["release_name"] = payload["release_name"] or str(release.get("name") or tag).strip()
                    except Exception:
                        pass
                self.finished.emit(payload)
                return
            if tag:
                self.finished.emit({
                    "available": False,
                    "status": "up_to_date",
                    "source": manifest_source or "manifest",
                    "latest_version": tag,
                    "message": f"ATS Annotation Tool {self.current_version} is already up to date according to the {manifest_source or 'manifest'}.",
                })
                return

        try:
            release = fetch_json(UPDATE_API_URL, timeout=10)
        except urllib.error.HTTPError as exc:
            if exc.code == 404:
                self.finished.emit({
                    "available": False,
                    "status": "no_release",
                    "message": "No GitHub release has been published yet.",
                })
                return
            self.failed.emit(f"GitHub returned HTTP {exc.code}: {exc.reason}")
            return
        except Exception as exc:
            self.failed.emit(f"Could not reach GitHub: {exc}")
            return
        tag = str(release.get("tag_name", release.get("name", ""))).strip()
        if not tag:
            self.finished.emit({
                "available": False,
                "status": "invalid_release",
                "message": "The latest GitHub release does not have a version tag.",
            })
            return
        if not version_is_newer(tag, self.current_version):
            self.finished.emit({
                "available": False,
                "status": "up_to_date",
                "latest_version": tag,
                "message": f"ATS Annotation Tool {self.current_version} is already up to date.",
            })
            return
        asset = choose_release_asset(release)
        payload = {
            "available": True,
            "status": "update_available",
            "source": "release",
            "latest_version": tag,
            "release_name": release.get("name") or tag,
            "body": release.get("body", ""),
            "html_url": release.get("html_url", ""),
            "download_url": asset.get("browser_download_url") if asset else "",
            "asset_name": asset.get("name") if asset else "",
        }
        self.finished.emit(payload)


class UpdateDownloadWorker(QObject):
    finished = Signal(str)
    failed = Signal(str)

    def __init__(self, url: str, destination: Path):
        super().__init__()
        self.url = url
        self.destination = destination

    def run(self):
        try:
            request = urllib.request.Request(
                self.url,
                headers={
                    "Accept": "application/octet-stream",
                    "User-Agent": f"{APP_TITLE}/{APP_VERSION}",
                },
            )
            self.destination.parent.mkdir(parents=True, exist_ok=True)
            with urllib.request.urlopen(request, timeout=60) as response, self.destination.open("wb") as handle:
                while True:
                    chunk = response.read(1024 * 1024)
                    if not chunk:
                        break
                    handle.write(chunk)
        except Exception as exc:
            self.failed.emit(str(exc))
            return
        self.finished.emit(str(self.destination))


def load_pixmap(path: Path, size: int | None = None) -> QPixmap | None:
    if not path.is_file():
        return None
    pixmap = QPixmap(str(path))
    if pixmap.isNull():
        return None
    if size is not None and size > 0:
        pixmap = pixmap.scaled(size, size, Qt.KeepAspectRatio, Qt.SmoothTransformation)
    return pixmap


def set_windows_app_id():
    if not sys.platform.startswith("win"):
        return
    try:
        ctypes.windll.shell32.SetCurrentProcessExplicitAppUserModelID("ATS.SARAnnotation.Desktop")
    except Exception:
        pass


@dataclass
class BoxAnnotation:
    box_id: int
    xmin: float
    ymin: float
    xmax: float
    ymax: float
    building_status: str = "intact"
    damage_level: str = ""
    split_editing: bool = False
    optical_xmin: float | None = None
    optical_ymin: float | None = None
    optical_xmax: float | None = None
    optical_ymax: float | None = None

    def normalized(self, image_kind: str = "sar"):
        xmin, ymin, xmax, ymax = self.geometry_for(image_kind)
        xmin, xmax = sorted([xmin, xmax])
        ymin, ymax = sorted([ymin, ymax])
        return xmin, ymin, xmax, ymax

    def geometry_for(self, image_kind: str = "sar"):
        if image_kind == "optical" and self.split_editing:
            optical_values = (self.optical_xmin, self.optical_ymin, self.optical_xmax, self.optical_ymax)
            if all(value is not None for value in optical_values):
                return optical_values
        return self.xmin, self.ymin, self.xmax, self.ymax

    def set_geometry(self, image_kind: str, xmin: float, ymin: float, xmax: float, ymax: float):
        xmin, xmax = sorted([xmin, xmax])
        ymin, ymax = sorted([ymin, ymax])
        if image_kind == "optical" and self.split_editing:
            self.optical_xmin = xmin
            self.optical_ymin = ymin
            self.optical_xmax = xmax
            self.optical_ymax = ymax
        else:
            self.xmin = xmin
            self.ymin = ymin
            self.xmax = xmax
            self.ymax = ymax
            if not self.split_editing:
                self.optical_xmin = None
                self.optical_ymin = None
                self.optical_xmax = None
                self.optical_ymax = None

    def enable_split_editing(self):
        self.split_editing = True
        if None in (self.optical_xmin, self.optical_ymin, self.optical_xmax, self.optical_ymax):
            self.optical_xmin = self.xmin
            self.optical_ymin = self.ymin
            self.optical_xmax = self.xmax
            self.optical_ymax = self.ymax

    def disable_split_editing(self):
        self.split_editing = False

    def polygon(self, image_kind: str = "sar"):
        xmin, ymin, xmax, ymax = self.normalized(image_kind)
        return Polygon([(xmin, ymax), (xmax, ymax), (xmax, ymin), (xmin, ymin), (xmin, ymax)])

    def to_dict(self):
        return {
            "box_id": self.box_id,
            "xmin": self.xmin,
            "ymin": self.ymin,
            "xmax": self.xmax,
            "ymax": self.ymax,
            "building_status": self.building_status,
            "damage_level": self.damage_level,
            "split_editing": self.split_editing,
            "optical_xmin": self.optical_xmin,
            "optical_ymin": self.optical_ymin,
            "optical_xmax": self.optical_xmax,
            "optical_ymax": self.optical_ymax,
        }

    @classmethod
    def from_dict(cls, payload: dict):
        def opt_value(name: str):
            value = payload.get(name, None)
            return None if value is None else float(value)
        return cls(
            box_id=int(payload.get("box_id", 0)),
            xmin=float(payload.get("xmin", 0.0)),
            ymin=float(payload.get("ymin", 0.0)),
            xmax=float(payload.get("xmax", 0.0)),
            ymax=float(payload.get("ymax", 0.0)),
            building_status=str(payload.get("building_status", "intact")),
            damage_level=str(payload.get("damage_level", "")),
            split_editing=bool(payload.get("split_editing", False)),
            optical_xmin=opt_value("optical_xmin"),
            optical_ymin=opt_value("optical_ymin"),
            optical_xmax=opt_value("optical_xmax"),
            optical_ymax=opt_value("optical_ymax"),
        )


@dataclass
class TileRecord:
    name: str
    sar_path: Path
    optical_path: Path
    sar_data: np.ndarray
    optical_data: np.ndarray
    sar_transform: object
    optical_transform: object
    sar_crs: object
    optical_crs: object
    sar_width: int
    sar_height: int
    optical_width: int
    optical_height: int
    sar_bounds: object
    optical_bounds: object
    display_crs: object
    shared_bounds: object
    annotations: list[BoxAnnotation] = field(default_factory=list)
    next_box_id: int = 1
    selected_box_id: int | None = None


def parse_tile_key(path: Path):
    match = TILE_NAME_RE.search(path.name)
    if not match:
        return None
    return int(match.group("row")), int(match.group("col"))


def tile_match_key(path: Path) -> str:
    return path.stem.strip().lower()


def natural_sort_key(value: str):
    parts = NATURAL_PARTS_RE.split(value)
    key = []
    for part in parts:
        if part.isdigit():
            key.append((0, int(part)))
        else:
            key.append((1, part))
    return key


def sorted_tif_files(folder: Path):
    items = []
    for path in folder.glob("*.tif"):
        items.append((tile_match_key(path), path))
    items.sort(key=lambda item: natural_sort_key(item[0]))
    return items


def clamp_bounds(bounds):
    left, right = sorted([float(bounds["left"]), float(bounds["right"])])
    bottom, top = sorted([float(bounds["bottom"]), float(bounds["top"])])
    return {"left": left, "right": right, "bottom": bottom, "top": top}


def get_bounds_value(bounds, key: str):
    if hasattr(bounds, key):
        return float(getattr(bounds, key))
    if isinstance(bounds, dict):
        return float(bounds[key])
    index_map = {"left": 0, "bottom": 1, "right": 2, "top": 3}
    return float(bounds[index_map[key]])


def bounds_to_dict(bounds):
    return {
        "left": get_bounds_value(bounds, "left"),
        "right": get_bounds_value(bounds, "right"),
        "bottom": get_bounds_value(bounds, "bottom"),
        "top": get_bounds_value(bounds, "top"),
    }


def bounds_width(bounds):
    return get_bounds_value(bounds, "right") - get_bounds_value(bounds, "left")


def bounds_height(bounds):
    return get_bounds_value(bounds, "top") - get_bounds_value(bounds, "bottom")


def world_to_canvas(pt, view_bounds, width, height):
    x = (pt[0] - view_bounds["left"]) / max(1e-9, bounds_width(view_bounds)) * width
    y = (view_bounds["top"] - pt[1]) / max(1e-9, bounds_height(view_bounds)) * height
    return x, y


def canvas_to_world(pt, view_bounds, width, height):
    x = view_bounds["left"] + (pt[0] / max(1, width)) * bounds_width(view_bounds)
    y = view_bounds["top"] - (pt[1] / max(1, height)) * bounds_height(view_bounds)
    return x, y


def shared_bounds_from_records(sar_bounds, sar_crs, optical_bounds, optical_crs):
    if sar_crs and optical_crs and sar_crs != optical_crs:
        optical_in_sar = transform_bounds(optical_crs, sar_crs, optical_bounds.left, optical_bounds.bottom, optical_bounds.right, optical_bounds.top)
        optical_bounds = type(sar_bounds)(*optical_in_sar)
    left = max(sar_bounds.left, optical_bounds.left)
    right = min(sar_bounds.right, optical_bounds.right)
    bottom = max(sar_bounds.bottom, optical_bounds.bottom)
    top = min(sar_bounds.top, optical_bounds.top)
    if left < right and bottom < top:
        return type(sar_bounds)(left, bottom, right, top)
    left = min(sar_bounds.left, optical_bounds.left)
    right = max(sar_bounds.right, optical_bounds.right)
    bottom = min(sar_bounds.bottom, optical_bounds.bottom)
    top = max(sar_bounds.top, optical_bounds.top)
    return type(sar_bounds)(left, bottom, right, top)


@lru_cache(maxsize=4)
def load_tile_pair(sar_path_str: str, optical_path_str: str):
    sar_path = Path(sar_path_str)
    optical_path = Path(optical_path_str)
    with rasterio.open(sar_path) as sar_src:
        sar_data = sar_src.read()
        sar_transform = sar_src.transform
        sar_crs = sar_src.crs
        sar_width = sar_src.width
        sar_height = sar_src.height
        sar_bounds = sar_src.bounds
    with rasterio.open(optical_path) as optical_src:
        optical_data = optical_src.read()
        optical_transform = optical_src.transform
        optical_crs = optical_src.crs
        optical_width = optical_src.width
        optical_height = optical_src.height
        optical_bounds = optical_src.bounds
    display_crs = sar_crs or optical_crs
    shared_bounds = shared_bounds_from_records(sar_bounds, sar_crs, optical_bounds, optical_crs)
    return {
        "name": sar_path.stem,
        "sar_path": sar_path,
        "optical_path": optical_path,
        "sar_data": sar_data,
        "optical_data": optical_data,
        "sar_transform": sar_transform,
        "optical_transform": optical_transform,
        "sar_crs": sar_crs,
        "optical_crs": optical_crs,
        "sar_width": sar_width,
        "sar_height": sar_height,
        "optical_width": optical_width,
        "optical_height": optical_height,
        "sar_bounds": sar_bounds,
        "optical_bounds": optical_bounds,
        "display_crs": display_crs,
        "shared_bounds": shared_bounds,
    }


def load_tile_refs(sar_dir: Path, optical_dir: Path):
    sar_tiles = dict(sorted_tif_files(sar_dir))
    optical_tiles = dict(sorted_tif_files(optical_dir))
    shared_keys = sorted(set(sar_tiles) & set(optical_tiles))
    refs = []
    for key in shared_keys:
        sar_path = sar_tiles[key]
        optical_path = optical_tiles[key]
        refs.append((sar_path, optical_path))
    return refs


def preview_size_for_bounds(bounds, max_width: int = 1200, max_height: int = 900):
    width = max(1e-9, bounds_width(bounds))
    height = max(1e-9, bounds_height(bounds))
    aspect = width / height
    if aspect >= 1.0:
        render_width = min(max_width, int(max_height * aspect))
        render_height = max(96, int(render_width / aspect))
    else:
        render_height = min(max_height, int(max_width / aspect))
        render_width = max(96, int(render_height * aspect))
    return max(96, render_width), max(96, render_height)


def preview_size_for_quality(bounds, quality: str):
    if quality == "low":
        return preview_size_for_bounds(bounds, max_width=720, max_height=540)
    return preview_size_for_bounds(bounds, max_width=1200, max_height=900)


def stretch_to_uint8(array: np.ndarray) -> np.ndarray:
    data = np.asarray(array, dtype=np.float32)
    valid = np.isfinite(data)
    if not np.any(valid):
        return np.zeros(data.shape, dtype=np.uint8)
    values = data[valid]
    low = float(np.percentile(values, 2))
    high = float(np.percentile(values, 98))
    if not np.isfinite(low) or not np.isfinite(high) or high <= low:
        low = float(np.min(values))
        high = float(np.max(values))
    if high <= low:
        return np.zeros(data.shape, dtype=np.uint8)
    stretched = (np.clip(data, low, high) - low) / (high - low) * 255.0
    return np.clip(stretched, 0, 255).astype(np.uint8)


def rgb_array_to_qimage(rgb_array: np.ndarray) -> QImage:
    rgb = np.ascontiguousarray(rgb_array.astype(np.uint8))
    height, width, _ = rgb.shape
    image = QImage(rgb.data, width, height, 3 * width, QImage.Format_RGB888)
    return image.copy()


@lru_cache(maxsize=128)
def render_preview_image(
    sar_path_str: str,
    optical_path_str: str,
    image_kind: str,
    left: float,
    bottom: float,
    right: float,
    top: float,
    width: int,
    height: int,
):
    record = load_tile_pair(sar_path_str, optical_path_str)
    view_bounds = {"left": left, "bottom": bottom, "right": right, "top": top}
    if image_kind == "sar":
        source = record["sar_data"]
        src_transform = record["sar_transform"]
        src_crs = record["sar_crs"]
    else:
        source = record["optical_data"]
        src_transform = record["optical_transform"]
        src_crs = record["optical_crs"]
    display_crs = record["display_crs"]

    if source.ndim == 2:
        source = source[np.newaxis, :, :]

    bands = source.shape[0]
    destination = np.zeros((bands, height, width), dtype=np.float32)
    dst_transform = from_bounds(left, bottom, right, top, width, height)
    for band_index in range(bands):
        reproject(
            source=source[band_index],
            destination=destination[band_index],
            src_transform=src_transform,
            src_crs=src_crs,
            dst_transform=dst_transform,
            dst_crs=display_crs,
            resampling=Resampling.bilinear,
        )
    if bands == 1:
        gray = stretch_to_uint8(destination[0])
        rgb = np.repeat(gray[:, :, None], 3, axis=2)
    else:
        rgb_bands = destination[:3]
        if rgb_bands.shape[0] < 3:
            rgb_bands = np.repeat(rgb_bands, 3, axis=0)[:3]
        rgb = np.transpose(np.stack([stretch_to_uint8(band) for band in rgb_bands], axis=0), (1, 2, 0))
    return rgb_array_to_qimage(rgb)


def box_to_dict(box: BoxAnnotation, image_kind: str = "sar"):
    xmin, ymin, xmax, ymax = box.normalized(image_kind)
    return {
        "box_id": box.box_id,
        "xmin": xmin,
        "ymin": ymin,
        "xmax": xmax,
        "ymax": ymax,
        "building_status": box.building_status,
        "damage_level": box.damage_level,
        "split_editing": box.split_editing,
        "image_kind": image_kind,
    }


def box_style(box: dict):
    if box.get("building_status") == "intact":
        return {
            "stroke": "#4ade80",
            "fill": (74, 222, 128, 24),
            "text": "#86efac",
        }
    damage_level = box.get("damage_level", "")
    if damage_level == "Minor":
        return {
            "stroke": "#fbbf24",
            "fill": (251, 191, 36, 24),
            "text": "#fde68a",
        }
    if damage_level == "Major":
        return {
            "stroke": "#fb923c",
            "fill": (251, 146, 60, 26),
            "text": "#fdba74",
        }
    if damage_level == "Destroyed":
        return {
            "stroke": "#ef4444",
            "fill": (239, 68, 68, 28),
            "text": "#fca5a5",
        }
    return {
        "stroke": "#f97316",
        "fill": (249, 115, 22, 24),
        "text": "#fdba74",
    }


def draw_debug_bounds(tile: TileRecord):
    return [
        {"left": tile.sar_bounds.left, "right": tile.sar_bounds.right, "bottom": tile.sar_bounds.bottom, "top": tile.sar_bounds.top, "label": "SAR bounds", "color": "#6fe0ff", "dash": "solid"},
        {"left": tile.optical_bounds.left, "right": tile.optical_bounds.right, "bottom": tile.optical_bounds.bottom, "top": tile.optical_bounds.top, "label": "Optical bounds", "color": "#ff7ad9", "dash": "dash"},
        {"left": tile.shared_bounds.left, "right": tile.shared_bounds.right, "bottom": tile.shared_bounds.bottom, "top": tile.shared_bounds.top, "label": "Shared extent", "color": "#ffffff", "dash": "dot"},
    ]


def bbox_from_geometry(geometry, transformer=None):
    if not geometry:
        return None
    try:
        geom = shape(geometry)
    except Exception:
        return None
    coords = []
    try:
        coords = list(geom.exterior.coords)
    except Exception:
        coords = []
    if not coords:
        return None
    if transformer is not None:
        coords = [transformer.transform(x, y) for x, y in coords]
    xs = [float(x) for x, _y in coords]
    ys = [float(y) for _x, y in coords]
    return min(xs), min(ys), max(xs), max(ys)


def bbox_from_dict(payload):
    if not isinstance(payload, dict):
        return None
    try:
        return (
            float(payload["xmin"]),
            float(payload["ymin"]),
            float(payload["xmax"]),
            float(payload["ymax"]),
        )
    except Exception:
        return None


def export_tile(tile: TileRecord, output_dir: Path, project_meta: dict):
    with rasterio.open(tile.sar_path) as src:
        transform = src.transform
        crs = src.crs
        width = src.width
        height = src.height

    mask_path = output_dir / "Masks" / f"{tile.name}.tif"
    any_split = any(box.split_editing for box in tile.annotations)

    def source_geometry(box: BoxAnnotation, source: str):
        if source == "SAR":
            return box.polygon("sar")
        if source == "Optical":
            return box.polygon("optical")
        return box.polygon("sar")

    def rasters_for_source(source: str):
        entries = []
        for box in tile.annotations:
            if box.split_editing:
                if source in ("SAR", "Optical"):
                    entries.append((source_geometry(box, source), box))
            else:
                if source in ("both", "SAR", "Optical"):
                    entries.append((box.polygon("sar"), box))
        return entries

    damage_lookup = {"Minor": 1, "Major": 2, "Destroyed": 3}

    if not any_split:
        binary = rasterize(
            [(box.polygon("sar"), 255) for box in tile.annotations],
            out_shape=(height, width),
            transform=transform,
            fill=0,
            dtype="uint8",
        )
        status = rasterize(
            [(box.polygon("sar"), 1 if box.building_status == "intact" else 2) for box in tile.annotations],
            out_shape=(height, width),
            transform=transform,
            fill=0,
            dtype="uint8",
        )
        damage = rasterize(
            [(box.polygon("sar"), damage_lookup.get(box.damage_level, 0)) for box in tile.annotations],
            out_shape=(height, width),
            transform=transform,
            fill=0,
            dtype="uint8",
        )
        with rasterio.open(
            mask_path,
            "w",
            driver="GTiff",
            height=height,
            width=width,
            count=3,
            dtype="uint8",
            crs=crs,
            transform=transform,
            nodata=0,
            compress="lzw",
        ) as dst:
            dst.write(binary, 1)
            dst.write(status, 2)
            dst.write(damage, 3)
            dst.set_band_description(1, "both_buildings")
            dst.set_band_description(2, "both_buildings_binary_classification")
            dst.set_band_description(3, "both_buildings_damage_level")
            dst.write_colormap(2, {0: (0, 0, 0, 255), 1: (0, 255, 0, 255), 2: (255, 0, 0, 255)})
            dst.write_colormap(3, {0: (0, 0, 0, 255), 1: (255, 255, 0, 255), 2: (255, 165, 0, 255), 3: (128, 0, 128, 255)})
    else:
        sar_binary = rasterize(
            [(box.polygon("sar"), 255) for box in tile.annotations],
            out_shape=(height, width),
            transform=transform,
            fill=0,
            dtype="uint8",
        )
        sar_status = rasterize(
            [(box.polygon("sar"), 1 if box.building_status == "intact" else 2) for box in tile.annotations],
            out_shape=(height, width),
            transform=transform,
            fill=0,
            dtype="uint8",
        )
        sar_damage = rasterize(
            [(box.polygon("sar"), damage_lookup.get(box.damage_level, 0)) for box in tile.annotations],
            out_shape=(height, width),
            transform=transform,
            fill=0,
            dtype="uint8",
        )
        optical_binary = rasterize(
            [
                (box.polygon("optical") if box.split_editing else box.polygon("sar"), 255)
                for box in tile.annotations
            ],
            out_shape=(height, width),
            transform=transform,
            fill=0,
            dtype="uint8",
        )
        optical_status = rasterize(
            [
                (box.polygon("optical") if box.split_editing else box.polygon("sar"), 1 if box.building_status == "intact" else 2)
                for box in tile.annotations
            ],
            out_shape=(height, width),
            transform=transform,
            fill=0,
            dtype="uint8",
        )
        optical_damage = rasterize(
            [
                (box.polygon("optical") if box.split_editing else box.polygon("sar"), damage_lookup.get(box.damage_level, 0))
                for box in tile.annotations
            ],
            out_shape=(height, width),
            transform=transform,
            fill=0,
            dtype="uint8",
        )
        with rasterio.open(
            mask_path,
            "w",
            driver="GTiff",
            height=height,
            width=width,
            count=6,
            dtype="uint8",
            crs=crs,
            transform=transform,
            nodata=0,
            compress="lzw",
        ) as dst:
            dst.write(sar_binary, 1)
            dst.write(sar_status, 2)
            dst.write(sar_damage, 3)
            dst.write(optical_binary, 4)
            dst.write(optical_status, 5)
            dst.write(optical_damage, 6)
            dst.set_band_description(1, "sar_buildings")
            dst.set_band_description(2, "sar_buildings_binary_classification")
            dst.set_band_description(3, "sar_buildings_damage_level")
            dst.set_band_description(4, "optical_buildings")
            dst.set_band_description(5, "optical_buildings_binary_classification")
            dst.set_band_description(6, "optical_buildings_damage_level")
            dst.write_colormap(2, {0: (0, 0, 0, 255), 1: (0, 255, 0, 255), 2: (255, 0, 0, 255)})
            dst.write_colormap(3, {0: (0, 0, 0, 255), 1: (255, 255, 0, 255), 2: (255, 165, 0, 255), 3: (128, 0, 128, 255)})
            dst.write_colormap(5, {0: (0, 0, 0, 255), 1: (0, 255, 0, 255), 2: (255, 0, 0, 255)})
            dst.write_colormap(6, {0: (0, 0, 0, 255), 1: (255, 255, 0, 255), 2: (255, 165, 0, 255), 3: (128, 0, 128, 255)})

    transformer = Transformer.from_crs(tile.display_crs, "EPSG:4326", always_xy=True) if tile.display_crs else None
    features = []
    for box in tile.annotations:
        geometries = []
        if box.split_editing:
            geometries.append(("SAR", box.polygon("sar")))
            geometries.append(("Optical", box.polygon("optical")))
        else:
            geometries.append(("both", box.polygon("sar")))
        for source, poly in geometries:
            if transformer is not None:
                poly = Polygon([transformer.transform(x, y) for x, y in poly.exterior.coords])
            features.append(
                {
                    "type": "Feature",
                    "geometry": mapping(poly),
                    "properties": {
                        "box_id": box.box_id,
                        "source": source,
                        "building_status": box.building_status,
                        "damage_level": box.damage_level,
                        "split_editing": box.split_editing,
                        "sar_geometry": {
                            "xmin": box.xmin,
                            "ymin": box.ymin,
                            "xmax": box.xmax,
                            "ymax": box.ymax,
                        },
                        "optical_geometry": {
                            "xmin": box.optical_xmin if box.optical_xmin is not None else box.xmin,
                            "ymin": box.optical_ymin if box.optical_ymin is not None else box.ymin,
                            "xmax": box.optical_xmax if box.optical_xmax is not None else box.xmax,
                            "ymax": box.optical_ymax if box.optical_ymax is not None else box.ymax,
                        },
                    "disaster_type": project_meta.get("disaster_type", ""),
                    "project_metadata": project_meta.get("project_metadata", {}),
                    "tile_name": tile.name,
                },
            }
        )
    geojson_path = output_dir / "Polygons" / f"{tile.name}.geojson"
    geojson = {
        "type": "FeatureCollection",
        "name": tile.name,
        "properties": {
            "tile_name": tile.name,
            "source_crs": str(tile.display_crs) if tile.display_crs else None,
            "geojson_crs": "EPSG:4326" if transformer is not None else str(tile.display_crs),
        },
        "features": features,
    }
    geojson_path.write_text(json.dumps(geojson, indent=2), encoding="utf-8")


class ImagePane(QFrame):
    viewChanged = Signal(dict)
    boxDrawn = Signal(dict)
    boxEdited = Signal(dict)
    boxSelected = Signal(int)
    viewportResized = Signal()

    def __init__(self, title: str, image_kind: str = "sar", parent=None):
        super().__init__(parent)
        self.setObjectName("ImagePane")
        self.setFrameShape(QFrame.StyledPanel)
        self.setMouseTracking(True)
        self.setFocusPolicy(Qt.ClickFocus)
        self.title = title
        self.image_kind = image_kind
        self.image: QImage | None = None
        self.image_label = QLabel(self)
        self.image_label.setAlignment(Qt.AlignCenter)
        self.image_label.setObjectName("ImageSurface")
        self.image_label.setAttribute(Qt.WA_TransparentForMouseEvents, True)
        self.overlay = OverlayWidget(self)
        self._display_rect = QRectF()
        self.view_bounds: dict | None = None
        self.boxes: list[dict] = []
        self.selected_box_id: int | None = None
        self.mode = "select"
        self.debug_bounds: list[dict] = []
        self._interaction = None
        self._temp_rect = None
        self._status = "Empty"
        self._theme_bg = "#0e0f11"
        self._theme_text = "#e8eaf0"
        self._theme_border = "rgba(255,255,255,0.08)"

    def set_content(
        self,
        image: QImage | None,
        view_bounds: dict | None,
        boxes: list[dict],
        selected_box_id: int | None,
        mode: str,
        debug_bounds: list[dict],
        status: str,
    ):
        self.image = image
        self.view_bounds = view_bounds
        self.boxes = boxes
        self.selected_box_id = selected_box_id
        self.mode = mode
        self.debug_bounds = debug_bounds
        self._status = status
        self._update_layer_geometry()
        self._update_image_surface()
        self.overlay.update()
        self.update()

    def set_theme(self, t: dict):
        self._theme_bg = t["bg0"]
        self._theme_text = t["text_primary"]
        self._theme_border = t["border"]
        self.image_label.setStyleSheet(f"background: {t['bg0']}; border: 0;")
        self.overlay.update()
        self.update()

    def sizeHint(self):
        return self.parentWidget().size() if self.parentWidget() else super().sizeHint()

    def resizeEvent(self, event):
        super().resizeEvent(event)
        self._update_layer_geometry()
        self._update_image_surface()
        self.overlay.update()
        self.viewportResized.emit()

    def _available_rect(self):
        margin = 12
        header_h = 46
        return QRectF(margin, margin + header_h, max(1, self.width() - margin * 2), max(1, self.height() - (margin * 2 + header_h + 6)))

    def _fit_rect(self, bounds: QRectF, aspect_w: float, aspect_h: float):
        if aspect_w <= 0 or aspect_h <= 0:
            return QRectF(bounds)
        target_ratio = aspect_w / aspect_h
        bounds_ratio = bounds.width() / max(1e-9, bounds.height())
        if bounds_ratio > target_ratio:
            h = bounds.height()
            w = h * target_ratio
        else:
            w = bounds.width()
            h = w / target_ratio
        x = bounds.left() + (bounds.width() - w) / 2
        y = bounds.top() + (bounds.height() - h) / 2
        return QRectF(x, y, w, h)

    def _update_layer_geometry(self):
        available = self._available_rect()
        if self.image is not None and not self.image.isNull():
            self._display_rect = self._fit_rect(available, self.image.width(), self.image.height())
            self.image_label.show()
        else:
            self._display_rect = QRectF(available)
            self.image_label.hide()
        self.image_label.setGeometry(self._display_rect.toRect())
        self.overlay.setGeometry(self.rect())
        self.overlay.raise_()
        self.image_label.lower()

    def _update_image_surface(self):
        if self.image is None or self.image.isNull():
            self.image_label.clear()
            return
        target_size = self.image_label.size()
        if target_size.width() <= 0 or target_size.height() <= 0:
            return
        scaled = self.image.scaled(target_size, Qt.KeepAspectRatio, Qt.SmoothTransformation)
        self.image_label.setPixmap(QPixmap.fromImage(scaled))

    def _canvas_size(self):
        return max(1, int(self._display_rect.width() or 1)), max(1, int(self._display_rect.height() or 1))

    def _image_rect(self):
        return QRectF(self._display_rect)

    def _canvas_to_world(self, pt):
        if not self.view_bounds:
            return 0.0, 0.0
        image_rect = self._image_rect()
        local = (pt[0] - image_rect.left(), pt[1] - image_rect.top())
        return canvas_to_world(local, self.view_bounds, image_rect.width(), image_rect.height())

    def _world_to_canvas(self, pt):
        if not self.view_bounds:
            return 0.0, 0.0
        image_rect = self._image_rect()
        local = world_to_canvas(pt, self.view_bounds, image_rect.width(), image_rect.height())
        return local[0] + image_rect.left(), local[1] + image_rect.top()

    def _hit_test(self, world_pt):
        for box in reversed(self.boxes):
            left = min(box["xmin"], box["xmax"])
            right = max(box["xmin"], box["xmax"])
            top = max(box["ymin"], box["ymax"])
            bottom = min(box["ymin"], box["ymax"])
            if left <= world_pt[0] <= right and bottom <= world_pt[1] <= top:
                return box["box_id"]
        return None

    def _selected_box(self):
        if self.selected_box_id is None:
            return None
        return next((box for box in self.boxes if box["box_id"] == self.selected_box_id), None)

    def _box_rect_canvas(self, box):
        left_top = self._world_to_canvas((min(box["xmin"], box["xmax"]), max(box["ymin"], box["ymax"])))
        right_bottom = self._world_to_canvas((max(box["xmin"], box["xmax"]), min(box["ymin"], box["ymax"])))
        return QRectF(left_top[0], left_top[1], right_bottom[0] - left_top[0], right_bottom[1] - left_top[1])

    def _hit_handle(self, rect: QRectF, pos):
        handle_radius = 10
        points = {
            "nw": rect.topLeft(),
            "ne": rect.topRight(),
            "sw": rect.bottomLeft(),
            "se": rect.bottomRight(),
        }
        for name, point in points.items():
            if abs(pos.x() - point.x()) <= handle_radius and abs(pos.y() - point.y()) <= handle_radius:
                return name
        return None

    def _make_box_update(self, box_id: int, xmin: float, ymin: float, xmax: float, ymax: float):
        return {
            "box_id": box_id,
            "xmin": xmin,
            "ymin": ymin,
            "xmax": xmax,
            "ymax": ymax,
            "image_kind": self.image_kind,
        }

    def _start_pan(self, event):
        self._interaction = {
            "kind": "pan",
            "start_pos": event.position(),
            "start_view": dict(self.view_bounds) if self.view_bounds else None,
            "last_pos": event.position(),
        }
        self.setCursor(Qt.ClosedHandCursor)

    def _start_draw(self, event):
        start_world = self._canvas_to_world((event.position().x(), event.position().y()))
        self._interaction = {
            "kind": "draw",
            "start_world": start_world,
            "current_world": start_world,
        }
        self._temp_rect = None
        self.setCursor(Qt.CrossCursor)

    def _start_edit(self, event, box, handle=None):
        self._interaction = {
            "kind": "edit",
            "box_id": box["box_id"],
            "start_pos": event.position(),
            "start_box": dict(box),
            "handle": handle,
            "current_box": dict(box),
        }
        self._temp_rect = self._interaction
        self.setCursor(Qt.SizeAllCursor if handle is None else Qt.SizeFDiagCursor)

    def wheelEvent(self, event):
        if not self.view_bounds:
            return
        delta = event.angleDelta().y()
        factor = 0.9 if delta > 0 else 1.1
        width, height = self._canvas_size()
        anchor = self._canvas_to_world((event.position().x(), event.position().y()))
        new_width = bounds_width(self.view_bounds) * factor
        new_height = bounds_height(self.view_bounds) * factor
        rel_x = (anchor[0] - self.view_bounds["left"]) / max(1e-9, bounds_width(self.view_bounds))
        rel_y = (self.view_bounds["top"] - anchor[1]) / max(1e-9, bounds_height(self.view_bounds))
        new_view = {
            "left": anchor[0] - rel_x * new_width,
            "right": anchor[0] - rel_x * new_width + new_width,
            "top": anchor[1] + rel_y * new_height,
            "bottom": anchor[1] + rel_y * new_height - new_height,
        }
        self.viewChanged.emit(new_view)

    def mousePressEvent(self, event):
        if not self.view_bounds or event.button() not in (Qt.LeftButton, Qt.MiddleButton):
            return
        if not self._display_rect.contains(event.position()):
            return
        world = self._canvas_to_world((event.position().x(), event.position().y()))
        if self.mode == "draw" and event.button() == Qt.LeftButton:
            self._start_draw(event)
            return
        if self.mode == "edit" and event.button() == Qt.LeftButton:
            box = self._selected_box()
            if box is not None:
                rect = self._box_rect_canvas(box)
                handle = self._hit_handle(rect, event.position())
                if handle is not None or rect.contains(event.position()):
                    self._start_edit(event, box, handle)
                    return
        if event.button() == Qt.MiddleButton:
            self._start_pan(event)
            return
        hit = self._hit_test(world)
        if hit is not None and self.mode == "select":
            self.boxSelected.emit(hit)
            self._interaction = {"kind": "select"}
            self.update()
        else:
            self._start_pan(event)

    def mouseMoveEvent(self, event):
        if not self._interaction or not self.view_bounds:
            return
        if self._interaction["kind"] == "pan":
            start_view = self._interaction["start_view"]
            if start_view is None:
                return
            start_pos = self._interaction["start_pos"]
            dx = event.position().x() - start_pos.x()
            dy = event.position().y() - start_pos.y()
            width, height = self._canvas_size()
            scale_x = bounds_width(start_view) / width
            scale_y = bounds_height(start_view) / height
            new_view = {
                "left": start_view["left"] - dx * scale_x,
                "right": start_view["right"] - dx * scale_x,
                "top": start_view["top"] + dy * scale_y,
                "bottom": start_view["bottom"] + dy * scale_y,
            }
            self.viewChanged.emit(new_view)
        elif self._interaction["kind"] == "draw":
            self._interaction["current_world"] = self._canvas_to_world((event.position().x(), event.position().y()))
            self._temp_rect = self._interaction
            self.update()
        elif self._interaction["kind"] == "edit":
            start_box = self._interaction["start_box"]
            start_pos = self._interaction["start_pos"]
            dx = event.position().x() - start_pos.x()
            dy = event.position().y() - start_pos.y()
            scale_x = bounds_width(self.view_bounds) / max(1, self._display_rect.width())
            scale_y = bounds_height(self.view_bounds) / max(1, self._display_rect.height())
            delta_x = dx * scale_x
            delta_y = dy * scale_y
            xmin, ymin, xmax, ymax = start_box["xmin"], start_box["ymin"], start_box["xmax"], start_box["ymax"]
            handle = self._interaction.get("handle")
            if handle == "nw":
                xmin += delta_x
                ymax -= delta_y
            elif handle == "ne":
                xmax += delta_x
                ymax -= delta_y
            elif handle == "sw":
                xmin += delta_x
                ymin -= delta_y
            elif handle == "se":
                xmax += delta_x
                ymin -= delta_y
            else:
                xmin += delta_x
                xmax += delta_x
                ymin -= delta_y
                ymax -= delta_y
            self._interaction["current_box"] = self._make_box_update(start_box["box_id"], xmin, ymin, xmax, ymax)
            self._temp_rect = self._interaction
            self.update()

    def mouseReleaseEvent(self, event):
        if not self._interaction:
            return
        if self._interaction["kind"] == "draw":
            start = self._interaction["start_world"]
            end = self._interaction["current_world"]
            xmin = min(start[0], end[0])
            xmax = max(start[0], end[0])
            ymin = min(start[1], end[1])
            ymax = max(start[1], end[1])
            if xmax - xmin > 0 and ymax - ymin > 0:
                self.boxDrawn.emit({"xmin": xmin, "ymin": ymin, "xmax": xmax, "ymax": ymax, "image_kind": self.image_kind})
            self._temp_rect = None
        elif self._interaction["kind"] == "edit":
            current = self._interaction.get("current_box", self._interaction["start_box"])
            xmin, ymin, xmax, ymax = current["xmin"], current["ymin"], current["xmax"], current["ymax"]
            if xmax - xmin > 0 and ymax - ymin > 0:
                self.boxEdited.emit(current)
            self._temp_rect = None
        elif self._interaction["kind"] == "pan":
            self.viewChanged.emit(dict(self.view_bounds))
        self._interaction = None
        self.unsetCursor()
        self.update()

    def paintEvent(self, event):
        painter = QPainter(self)
        painter.fillRect(self.rect(), QColor(self._theme_bg))
        painter.setRenderHint(QPainter.Antialiasing, True)

        margin = 12
        header_rect = QRectF(margin, margin, self.width() - margin * 2, 36)
        image_rect = self._image_rect()
        painter.setPen(QPen(QColor(self._theme_border), 1))
        painter.setBrush(QColor(self._theme_bg))
        painter.drawRoundedRect(image_rect, 18, 18)

        if self.image is None or self.image.isNull():
            painter.setPen(QColor(self._theme_text))
            painter.drawText(image_rect, Qt.AlignCenter, "No image loaded")

        painter.setBrush(QColor(self._theme_bg))
        painter.setPen(QPen(QColor(self._theme_border), 1))
        painter.drawRoundedRect(header_rect, 14, 14)
        painter.setPen(QColor(self._theme_text))
        painter.setFont(QFont("Segoe UI", 10, QFont.Bold))
        painter.drawText(header_rect.adjusted(14, 0, -14, 0), Qt.AlignVCenter | Qt.AlignLeft, self.title)
        painter.setPen(QColor(self._theme_text))
        painter.setFont(QFont("Segoe UI", 8))
        painter.drawText(header_rect.adjusted(14, 0, -14, 0), Qt.AlignVCenter | Qt.AlignRight, self._status)

        painter.end()


class OverlayWidget(QWidget):
    def __init__(self, pane: ImagePane):
        super().__init__(pane)
        self.pane = pane
        self.setAttribute(Qt.WA_TransparentForMouseEvents, True)
        self.setAttribute(Qt.WA_NoSystemBackground, True)
        self.setAttribute(Qt.WA_TranslucentBackground, True)
        self.raise_()

    def paintEvent(self, event):
        pane = self.pane
        if pane.image is None or pane.image.isNull():
            return
        painter = QPainter(self)
        painter.setRenderHint(QPainter.Antialiasing, True)
        image_rect = pane._image_rect()
        content_rect = image_rect.adjusted(6, 6, -6, -6)
        painter.setClipRect(content_rect)
        if pane.view_bounds:
            for dbg in pane.debug_bounds:
                painter.setPen(QPen(QColor(dbg.get("color", "#ffffff")), 2, Qt.SolidLine if dbg.get("dash") == "solid" else Qt.DashLine))
                left_top = pane._world_to_canvas((dbg["left"], dbg["top"]))
                right_bottom = pane._world_to_canvas((dbg["right"], dbg["bottom"]))
                rect = QRectF(left_top[0], left_top[1], right_bottom[0] - left_top[0], right_bottom[1] - left_top[1])
                painter.drawRect(rect)
                painter.setPen(QColor(dbg.get("color", "#ffffff")))
                painter.drawText(rect.adjusted(6, -18, 0, 0), Qt.AlignLeft | Qt.AlignTop, dbg.get("label", ""))

            for box in pane.boxes:
                left_top = pane._world_to_canvas((min(box["xmin"], box["xmax"]), max(box["ymin"], box["ymax"])))
                right_bottom = pane._world_to_canvas((max(box["xmin"], box["xmax"]), min(box["ymin"], box["ymax"])))
                rect = QRectF(left_top[0], left_top[1], right_bottom[0] - left_top[0], right_bottom[1] - left_top[1])
                selected = box["box_id"] == pane.selected_box_id
                style = box_style(box)
                stroke = "#e2e8f0" if selected else style["stroke"]
                fill = QColor(226, 232, 240, 22) if selected else QColor(*style["fill"])
                painter.setPen(QPen(QColor(stroke), 3 if selected else 2))
                painter.setBrush(fill)
                painter.drawRect(rect)
                painter.setPen(QColor("#e2e8f0" if selected else style["text"]))
                painter.drawText(rect.adjusted(6, 6, 0, 0), Qt.AlignLeft | Qt.AlignTop, f"Box {box['box_id']}")
                if selected and pane.mode == "edit":
                    painter.setBrush(QColor(pane._theme_text))
                    painter.setPen(QPen(QColor(pane._theme_border), 1))
                    for point in [rect.topLeft(), rect.topRight(), rect.bottomLeft(), rect.bottomRight()]:
                        painter.drawRect(QRectF(point.x() - 3, point.y() - 3, 6, 6))

            if pane._temp_rect and pane._temp_rect.get("kind") == "draw":
                start = pane._temp_rect["start_world"]
                current = pane._temp_rect["current_world"]
                left = min(start[0], current[0])
                right = max(start[0], current[0])
                bottom = min(start[1], current[1])
                top = max(start[1], current[1])
                left_top = pane._world_to_canvas((left, top))
                right_bottom = pane._world_to_canvas((right, bottom))
                rect = QRectF(left_top[0], left_top[1], right_bottom[0] - left_top[0], right_bottom[1] - left_top[1])
                painter.setPen(QPen(QColor("#34d399"), 2, Qt.DashLine))
                painter.setBrush(QColor(52, 211, 153, 22))
                painter.drawRect(rect)
            if pane._temp_rect and pane._temp_rect.get("kind") == "edit":
                current = pane._temp_rect.get("current_box", pane._temp_rect["start_box"])
                rect = pane._box_rect_canvas(current)
                painter.setPen(QPen(QColor("#4ade80"), 2, Qt.SolidLine))
                painter.setBrush(QColor(74, 222, 128, 18))
                painter.drawRect(rect)
                painter.setBrush(QColor(pane._theme_text))
                painter.setPen(QPen(QColor(pane._theme_border), 1))
                for point in [rect.topLeft(), rect.topRight(), rect.bottomLeft(), rect.bottomRight()]:
                    painter.drawRect(QRectF(point.x() - 3, point.y() - 3, 6, 6))
        painter.end()


class MetadataRowWidget(QFrame):
    changed = Signal()
    removed = Signal(object)

    def __init__(self, key: str = "", value: str = "", parent=None):
        super().__init__(parent)
        self.setObjectName("InspectorPanel")
        self.setMouseTracking(True)
        self._remove_visible = False
        layout = QHBoxLayout(self)
        layout.setContentsMargins(10, 8, 10, 8)
        layout.setSpacing(8)
        self.key_edit = QLineEdit(str(key))
        self.key_edit.setPlaceholderText("Key")
        self.value_edit = QLineEdit(str(value))
        self.value_edit.setPlaceholderText("Value")
        self.remove_btn = QPushButton("-")
        self.remove_btn.setObjectName("SkipBtn")
        self.remove_btn.setFixedWidth(34)
        self.remove_btn.hide()
        self.key_edit.textChanged.connect(lambda _=None: self.changed.emit())
        self.value_edit.textChanged.connect(lambda _=None: self.changed.emit())
        self.remove_btn.clicked.connect(lambda _=False: self.removed.emit(self))
        layout.addWidget(self.key_edit, 1)
        layout.addWidget(self.value_edit, 1)
        layout.addWidget(self.remove_btn)

    def pair(self):
        return self.key_edit.text().strip(), self.value_edit.text().strip()

    def enterEvent(self, event):
        self.remove_btn.show()
        super().enterEvent(event)

    def leaveEvent(self, event):
        self.remove_btn.hide()
        super().leaveEvent(event)


class SetupPage(QWidget):
    loadRequested = Signal(dict)
    metadataChanged = Signal()

    def __init__(self, parent=None):
        super().__init__(parent)
        root_layout = QVBoxLayout(self)
        root_layout.setContentsMargins(24, 24, 24, 24)
        root_layout.setSpacing(18)

        self.sar_dir = QLineEdit("")
        self.optical_dir = QLineEdit("")
        self.output_dir = QLineEdit("")
        self.disaster_type = QLineEdit()
        self.project_meta_rows = []
        for widget in [self.sar_dir, self.optical_dir, self.output_dir, self.disaster_type]:
            widget.textChanged.connect(lambda _=None: self.metadataChanged.emit())

        hero = QFrame()
        hero.setObjectName("HeaderBar")
        hero_layout = QVBoxLayout(hero)
        hero_layout.setContentsMargins(18, 14, 18, 14)
        hero_layout.setSpacing(6)
        title = QLabel("ATS Annotation Tool")
        title.setObjectName("HeroTitle")
        subtitle = QLabel(
            "Geospatial annotation tool for paired SAR and optical raster tiles. Draw building boxes, "
            "label damage, and export georeferenced masks and GeoJSON."
        )
        subtitle.setObjectName("HeroSubtitle")
        subtitle.setWordWrap(True)
        hero_layout.addWidget(title)
        hero_layout.addWidget(subtitle)

        body = QSplitter(Qt.Horizontal)
        body.setChildrenCollapsible(False)

        left = QFrame()
        left.setObjectName("InspectorPanel")
        left_layout = QVBoxLayout(left)
        left_layout.setContentsMargins(16, 16, 16, 16)
        left_layout.setSpacing(12)
        left_title = QLabel("Project Paths")
        left_title.setObjectName("SectionTitle")
        left_layout.addWidget(left_title)

        path_form = QGridLayout()
        path_form.setHorizontalSpacing(10)
        path_form.setVerticalSpacing(10)
        for row, (label_text, widget, browse) in enumerate([
            ("Project root / output directory", self.output_dir, True),
            ("SAR tiles directory", self.sar_dir, True),
            ("Optical tiles directory", self.optical_dir, True),
        ]):
            label = QLabel(label_text)
            label.setObjectName("MutedText")
            path_form.addWidget(label, row, 0)
            path_form.addWidget(widget, row, 1)
            if browse:
                btn = QPushButton("Browse")
                btn.setObjectName("BrowseBtn")
                if widget is self.output_dir:
                    btn.clicked.connect(lambda _=False: self._browse_project_root())
                else:
                    btn.clicked.connect(lambda _=False, line=widget: self._browse(line))
                path_form.addWidget(btn, row, 2)
        left_layout.addLayout(path_form)

        meta_form = QGridLayout()
        meta_form.setHorizontalSpacing(10)
        meta_form.setVerticalSpacing(10)
        self.disaster_label = QLabel("Disaster type")
        self.disaster_label.setObjectName("MutedText")
        meta_form.addWidget(self.disaster_label, 0, 0)
        meta_form.addWidget(self.disaster_type, 0, 1)
        left_layout.addLayout(meta_form)

        self.meta_rows_frame = QFrame()
        self.meta_rows_frame.setObjectName("WorkspacePanel")
        self.meta_rows_layout = QVBoxLayout(self.meta_rows_frame)
        self.meta_rows_layout.setContentsMargins(0, 0, 0, 0)
        self.meta_rows_layout.setSpacing(8)
        meta_rows_header = QHBoxLayout()
        meta_rows_label = QLabel("Custom metadata")
        meta_rows_label.setObjectName("SectionTitle")
        self.add_meta_button = QPushButton("+")
        self.add_meta_button.setObjectName("ModeChipSelect")
        self.add_meta_button.setFixedWidth(34)
        self.add_meta_button.clicked.connect(lambda _=False: self.add_metadata_row())
        meta_rows_header.addWidget(meta_rows_label)
        meta_rows_header.addStretch(1)
        meta_rows_header.addWidget(self.add_meta_button)
        self.meta_rows_layout.addLayout(meta_rows_header)
        left_layout.addWidget(self.meta_rows_frame)
        self.add_metadata_row()

        self.load_button = QPushButton("Load Project")
        self.load_button.setObjectName("LoadBtn")
        self.load_button.setProperty("accent", True)
        self.load_button.clicked.connect(self._emit_config)
        left_layout.addWidget(self.load_button)
        left_layout.addStretch(1)

        right = QFrame()
        right.setObjectName("WorkspacePanel")
        right_layout = QVBoxLayout(right)
        right_layout.setContentsMargins(20, 20, 20, 20)
        right_layout.setSpacing(16)

        welcome = QFrame()
        welcome.setObjectName("HeaderBar")
        welcome_layout = QVBoxLayout(welcome)
        welcome_layout.setContentsMargins(18, 16, 18, 16)
        welcome_layout.setSpacing(8)
        welcome_title = QLabel("SAR<span style='color:#4ade80;'>/</span>Annotate")
        welcome_title.setObjectName("BigTitle")
        welcome_title.setTextFormat(Qt.RichText)
        welcome_sub = QLabel(
            "Load local paired tiles, inspect SAR and optical imagery side by side, annotate boxes, "
            "and export a geospatial dataset per tile."
        )
        welcome_sub.setObjectName("HeroSubtitle")
        welcome_sub.setWordWrap(True)
        welcome_layout.addWidget(welcome_title)
        welcome_layout.addWidget(welcome_sub)

        steps = QFrame()
        steps.setObjectName("WorkspacePanel")
        steps_layout = QVBoxLayout(steps)
        steps_layout.setContentsMargins(18, 16, 18, 16)
        steps_layout.setSpacing(10)
        steps_title = QLabel("Workflow")
        steps_title.setObjectName("SectionTitle")
        steps_layout.addWidget(steps_title)
        for idx, text in enumerate([
            "Connect the app to SAR and optical folders with matching filenames.",
            "Fill project-wide disaster and resolution metadata once.",
            "Annotate bounding boxes on the synchronized dual-view canvas.",
            "Switch to metadata to edit box status and damage level.",
            "Save the tile to export masks and GeoJSON.",
        ], start=1):
            row = QHBoxLayout()
            num = QLabel(f"{idx:02d}")
            num.setObjectName("SectionTitle")
            num.setFixedWidth(28)
            desc = QLabel(text)
            desc.setWordWrap(True)
            desc.setObjectName("PanelHint")
            row.addWidget(num)
            row.addWidget(desc, 1)
            steps_layout.addLayout(row)

        fs = QFrame()
        fs.setObjectName("InspectorPanel")
        fs_layout = QVBoxLayout(fs)
        fs_layout.setContentsMargins(18, 16, 18, 16)
        fs_layout.setSpacing(10)
        fs_title = QLabel("Recent projects")
        fs_title.setObjectName("SectionTitle")
        fs_layout.addWidget(fs_title)
        fs_hint = QLabel("Double-click a project to resume it with saved metadata and the last opened tile.")
        fs_hint.setObjectName("PanelHint")
        fs_hint.setWordWrap(True)
        fs_layout.addWidget(fs_hint)
        self.recent_list = QListWidget()
        self.recent_list.setObjectName("RecentProjectsList")
        self.recent_list.itemActivated.connect(self._open_recent_project)
        fs_layout.addWidget(self.recent_list, 1)
        self.recent_empty = QLabel("No recent projects yet.")
        self.recent_empty.setObjectName("PanelHint")
        self.recent_empty.setAlignment(Qt.AlignCenter)
        self.recent_empty.setWordWrap(True)
        fs_layout.addWidget(self.recent_empty)

        right_layout.addWidget(welcome)
        right_layout.addWidget(steps)
        right_layout.addWidget(fs)
        right_layout.addStretch(1)

        body.addWidget(left)
        body.addWidget(right)
        body.setStretchFactor(0, 3)
        body.setStretchFactor(1, 7)
        body.setSizes([300, 700])

        root_layout.addWidget(hero)
        root_layout.addWidget(body, 1)

    def _browse(self, line_edit: QLineEdit):
        folder = QFileDialog.getExistingDirectory(self, "Select Folder", line_edit.text() or str(DEFAULT_ROOT))
        if folder:
            line_edit.setText(folder)

    def _browse_project_root(self):
        folder = QFileDialog.getExistingDirectory(self, "Select Project Root", self.output_dir.text() or str(Path.cwd()))
        if not folder:
            return
        self.output_dir.setText(folder)
        self._prompt_detect_project_folders(Path(folder))

    def _prompt_detect_project_folders(self, root_folder: Path):
        sar_guess = root_folder / "sar_tiles"
        optical_guess = root_folder / "optical_tiles"
        if sar_guess.is_dir() and optical_guess.is_dir():
            dialog = QMessageBox(self)
            dialog.setWindowTitle("Detected project folders")
            dialog.setIcon(QMessageBox.Question)
            dialog.setText("SAR and optical folders were found under the selected project root.")
            dialog.setInformativeText(
                f"SAR: {sar_guess}\n"
                f"Optical: {optical_guess}\n\n"
                "Use these folders or choose different ones?"
            )
            use_btn = dialog.addButton("Use Detected", QMessageBox.AcceptRole)
            change_btn = dialog.addButton("Change Manually", QMessageBox.ActionRole)
            cancel_btn = dialog.addButton(QMessageBox.Cancel)
            dialog.exec()
            clicked = dialog.clickedButton()
            if clicked == use_btn:
                self.sar_dir.setText(str(sar_guess))
                self.optical_dir.setText(str(optical_guess))
                self.metadataChanged.emit()
                return
            if clicked == change_btn:
                self._choose_project_folders(str(sar_guess), str(optical_guess))
                return
            return

        dialog = QMessageBox(self)
        dialog.setWindowTitle("Project folders not found")
        dialog.setIcon(QMessageBox.Question)
        dialog.setText("Could not automatically find SAR and optical folders in this project root.")
        dialog.setInformativeText("Would you like to choose the SAR and optical folders manually now?")
        yes_btn = dialog.addButton("Choose Manually", QMessageBox.AcceptRole)
        dialog.addButton(QMessageBox.Cancel)
        dialog.exec()
        if dialog.clickedButton() == yes_btn:
            self._choose_project_folders(str(sar_guess), str(optical_guess))

    def _choose_project_folders(self, sar_start: str = "", optical_start: str = ""):
        sar_folder = QFileDialog.getExistingDirectory(self, "Select SAR tiles folder", sar_start or self.sar_dir.text() or str(DEFAULT_ROOT))
        if not sar_folder:
            return
        optical_folder = QFileDialog.getExistingDirectory(self, "Select Optical tiles folder", optical_start or self.optical_dir.text() or str(DEFAULT_ROOT))
        if not optical_folder:
            return
        self.sar_dir.setText(sar_folder)
        self.optical_dir.setText(optical_folder)
        self.metadataChanged.emit()

    def set_recent_projects(self, projects: list[dict]):
        self.recent_list.clear()
        for project in projects:
            root = project.get("project_root") or project.get("output_dir") or ""
            sar_dir = project.get("sar_dir", "")
            optical_dir = project.get("optical_dir", "")
            current_index = int(project.get("current_index", 0) or 0)
            total_tiles = int(project.get("tile_count", 0) or 0)
            last_tile = project.get("last_processed_tile", "")
            label = root or "Untitled project"
            if last_tile:
                label = f"{label}\nLast tile: {last_tile}"
            elif total_tiles:
                label = f"{label}\nTile index: {current_index + 1} / {total_tiles}"
            item = QListWidgetItem(label)
            item.setData(Qt.UserRole, {
                "sar_dir": sar_dir,
                "optical_dir": optical_dir,
                "output_dir": project.get("output_dir", root),
                "disaster_type": project.get("disaster_type", ""),
                "project_metadata": project.get("project_metadata", {}),
                "project_metadata_rows": project.get("project_metadata_rows", []),
                "resume_choice": "continue",
            })
            self.recent_list.addItem(item)
        self.recent_empty.setVisible(self.recent_list.count() == 0)

    def _open_recent_project(self, item):
        config = item.data(Qt.UserRole) or {}
        if config:
            self.loadRequested.emit(config)

    def add_metadata_row(self, key: str = "", value: str = ""):
        row = MetadataRowWidget(key, value, self.meta_rows_frame)
        row.changed.connect(self.metadataChanged.emit)
        row.removed.connect(self._remove_metadata_row)
        self.meta_rows_layout.addWidget(row)
        self.project_meta_rows.append(row)
        self.metadataChanged.emit()

    def project_metadata(self):
        metadata = {}
        for item in self.project_meta_rows:
            key, value = item.pair()
            if key:
                metadata[key] = value
        return metadata

    def metadata_rows(self):
        rows = []
        for item in self.project_meta_rows:
            key, value = item.pair()
            if key:
                rows.append((key, value))
        return rows

    def clear_metadata_rows(self):
        for item in self.project_meta_rows:
            item.setParent(None)
            item.deleteLater()
        self.project_meta_rows = []

    def set_metadata_rows(self, rows: list[tuple[str, str]]):
        self.clear_metadata_rows()
        if not rows:
            self.add_metadata_row()
        else:
            for key, value in rows:
                self.add_metadata_row(key, value)

    def _remove_metadata_row(self, row_widget):
        if row_widget in self.project_meta_rows:
            self.project_meta_rows = [item for item in self.project_meta_rows if item is not row_widget]
            row_widget.setParent(None)
            row_widget.deleteLater()
            self.metadataChanged.emit()

    def _emit_config(self, *args):
        self.loadRequested.emit(
            {
                "sar_dir": self.sar_dir.text().strip(),
                "optical_dir": self.optical_dir.text().strip(),
                "output_dir": self.output_dir.text().strip(),
                "disaster_type": self.disaster_type.text().strip(),
                "project_metadata": self.project_metadata(),
                "project_metadata_rows": self.metadata_rows(),
            }
        )


class AnnotatePage(QWidget):
    fitClicked = Signal()
    drawModeClicked = Signal()
    selectModeClicked = Signal()
    skipClicked = Signal()
    nextClicked = Signal()
    tileActivated = Signal(object)

    def __init__(self, parent=None):
        super().__init__(parent)
        main_layout = QVBoxLayout(self)
        main_layout.setContentsMargins(18, 18, 18, 18)
        main_layout.setSpacing(12)

        header = QFrame()
        header.setObjectName("HeaderBar")
        header_layout = QHBoxLayout(header)
        header_layout.setContentsMargins(18, 14, 18, 14)
        header_layout.setSpacing(14)

        title_block = QVBoxLayout()
        self.title_label = QLabel("Tile -")
        self.title_label.setObjectName("BigTitle")
        self.subtitle_label = QLabel("Load a project to begin")
        self.subtitle_label.setObjectName("PanelHint")
        self.subtitle_label.setWordWrap(True)
        title_block.addWidget(self.title_label)
        title_block.addWidget(self.subtitle_label)

        status_block = QVBoxLayout()
        self.mode_label = QLabel("Mode: select")
        self.mode_label.setObjectName("MutedText")
        self.progress_label = QLabel("0 / 0")
        self.progress_label.setObjectName("SectionTitle")
        status_block.addWidget(self.progress_label)
        status_block.addWidget(self.mode_label)

        actions_block = QHBoxLayout()
        actions_block.setSpacing(8)
        self.fit_button = QPushButton("Fit")
        self.draw_button = QPushButton("Draw")
        self.select_button = QPushButton("Select")
        self.skip_button = QPushButton("Skip")
        self.next_button = QPushButton("Next")
        self.draw_button.setObjectName("ModeChipDraw")
        self.select_button.setObjectName("ModeChipSelect")
        self.skip_button.setObjectName("SkipBtn")
        self.next_button.setObjectName("NextBtn")
        self.next_button.setProperty("accent", True)
        for btn in [self.fit_button, self.draw_button, self.select_button, self.skip_button, self.next_button]:
            btn.setCursor(Qt.PointingHandCursor)
            actions_block.addWidget(btn)

        header_layout.addLayout(title_block, 4)
        header_layout.addStretch(1)
        header_layout.addLayout(status_block, 1)
        header_layout.addLayout(actions_block, 3)

        body = QSplitter(Qt.Horizontal)
        body.setChildrenCollapsible(False)
        viewer_frame = QFrame()
        viewer_frame.setObjectName("WorkspacePanel")
        viewer_layout = QVBoxLayout(viewer_frame)
        viewer_layout.setContentsMargins(12, 12, 12, 12)
        viewer_layout.setSpacing(10)
        panes = QSplitter(Qt.Horizontal)
        panes.setChildrenCollapsible(False)
        self.sar_pane = ImagePane("SAR Tile", "sar")
        self.optical_pane = ImagePane("Optical Tile", "optical")
        panes.addWidget(self.sar_pane)
        panes.addWidget(self.optical_pane)
        panes.setStretchFactor(0, 1)
        panes.setStretchFactor(1, 1)
        viewer_layout.addWidget(panes)

        side = QFrame()
        side.setObjectName("InspectorPanel")
        side_layout = QVBoxLayout(side)
        side_layout.setContentsMargins(14, 14, 14, 14)
        side_layout.setSpacing(10)
        tile_title = QLabel("Tile browser")
        tile_title.setObjectName("SectionTitle")
        tile_hint = QLabel("Click a tile to jump to it. Processed tiles are marked and stay in the project state.")
        tile_hint.setWordWrap(True)
        tile_hint.setObjectName("PanelHint")
        self.tile_list = QListWidget()
        self.tile_list.setObjectName("TileBrowserList")
        self.tile_list.itemActivated.connect(self.tileActivated.emit)
        side_title = QLabel("Inspector")
        side_title.setObjectName("SectionTitle")
        self.project_summary = QLabel("No project loaded")
        self.project_summary.setWordWrap(True)
        self.project_summary.setObjectName("PanelHint")
        self.box_list = QListWidget()
        self.box_list.setMinimumWidth(240)
        self.box_list.setMaximumWidth(320)
        box_actions = QHBoxLayout()
        self.edit_button = QPushButton("Edit Selected")
        self.edit_button.setObjectName("ModeChipSelect")
        self.delete_button = QPushButton("Delete Selected")
        self.delete_button.setObjectName("SkipBtn")
        box_actions.addWidget(self.edit_button)
        box_actions.addWidget(self.delete_button)
        self.split_edit_toggle = QCheckBox("Split editing")
        self.debug_note = QLabel("Box list updates live as you draw.")
        self.debug_note.setWordWrap(True)
        self.debug_note.setObjectName("PanelHint")
        side_layout.addWidget(tile_title)
        side_layout.addWidget(tile_hint)
        side_layout.addWidget(self.tile_list, 1)
        side_layout.addWidget(side_title)
        side_layout.addWidget(self.project_summary)
        side_layout.addWidget(self.box_list, 1)
        side_layout.addLayout(box_actions)
        side_layout.addWidget(self.split_edit_toggle)
        side_layout.addWidget(self.debug_note)

        body.addWidget(viewer_frame)
        body.addWidget(side)
        body.setStretchFactor(0, 4)
        body.setStretchFactor(1, 1)

        main_layout.addWidget(header)
        main_layout.addWidget(body, 1)

    def set_header(self, tile_name: str, index: int, total: int, mode: str, has_boxes: bool):
        self.title_label.setText(f"Tile {index + 1} / {total}: {tile_name}")
        self.subtitle_label.setText("Draw bounding boxes on SAR or optical. Zoom with wheel, pan with drag or middle mouse.")
        self.mode_label.setText(f"Mode: {mode} | Boxes: {'yes' if has_boxes else 'no'}")
        self.progress_label.setText(f"{index + 1} / {total}")

    def set_project_summary(self, text: str):
        self.project_summary.setText(text)

    def set_tiles(self, tiles: list[dict], current_index: int):
        self.tile_list.blockSignals(True)
        self.tile_list.clear()
        for idx, tile in enumerate(tiles):
            processed = bool(tile.get("processed"))
            last_tile = bool(tile.get("last_processed"))
            status = "processed" if processed else "pending"
            if last_tile:
                status = "last processed"
            item = QListWidgetItem(f"{tile['name']}  [{status}]")
            item.setData(Qt.UserRole, idx)
            if idx == current_index:
                item.setSelected(True)
            self.tile_list.addItem(item)
        self.tile_list.blockSignals(False)

    def set_boxes(self, boxes: list[dict], selected_box_id: int | None):
        self.box_list.blockSignals(True)
        self.box_list.clear()
        for box in boxes:
            split_tag = "split" if box.get("split_editing") else "shared"
            item = QListWidgetItem(f"Box {box['box_id']}  [{box['building_status']}, {box['damage_level']}, {split_tag}]")
            item.setData(Qt.UserRole, box["box_id"])
            self.box_list.addItem(item)
            if box["box_id"] == selected_box_id:
                item.setSelected(True)
        self.box_list.blockSignals(False)

    def current_selected_box_id(self):
        item = self.box_list.currentItem()
        if not item:
            return None
        return item.data(Qt.UserRole)


class MetadataPage(QWidget):
    saveNextClicked = Signal(bool)
    backClicked = Signal()

    def __init__(self, parent=None):
        super().__init__(parent)
        main_layout = QVBoxLayout(self)
        main_layout.setContentsMargins(18, 18, 18, 18)
        main_layout.setSpacing(12)

        header = QFrame()
        header.setObjectName("HeaderBar")
        header_layout = QVBoxLayout(header)
        header_layout.setContentsMargins(18, 14, 18, 14)
        header_layout.setSpacing(4)
        self.title_label = QLabel("Metadata")
        self.title_label.setObjectName("BigTitle")
        self.subtitle_label = QLabel("Review and edit the selected box metadata before exporting.")
        self.subtitle_label.setObjectName("PanelHint")
        self.subtitle_label.setWordWrap(True)
        header_layout.addWidget(self.title_label)
        header_layout.addWidget(self.subtitle_label)

        body = QSplitter(Qt.Horizontal)
        body.setChildrenCollapsible(False)
        viewer_frame = QFrame()
        viewer_frame.setObjectName("WorkspacePanel")
        viewer_layout = QVBoxLayout(viewer_frame)
        viewer_layout.setContentsMargins(12, 12, 12, 12)
        self.sar_pane = ImagePane("SAR Tile With Boxes", "sar")
        viewer_layout.addWidget(self.sar_pane)

        side = QFrame()
        side.setObjectName("InspectorPanel")
        side_layout = QVBoxLayout(side)
        side_layout.setContentsMargins(14, 14, 14, 14)
        side_layout.setSpacing(10)
        side_title = QLabel("Selected Box")
        side_title.setObjectName("SectionTitle")
        self.box_list = QListWidget()
        self.box_list.setMaximumHeight(140)
        meta_box_actions = QHBoxLayout()
        self.edit_button = QPushButton("Edit Selected")
        self.edit_button.setObjectName("ModeChipSelect")
        self.delete_button = QPushButton("Delete Selected")
        self.delete_button.setObjectName("Skip2Btn")
        meta_box_actions.addWidget(self.edit_button)
        meta_box_actions.addWidget(self.delete_button)
        self.split_edit_toggle = QCheckBox("Split editing")
        self.box_select = QComboBox()
        self.status_combo = QComboBox()
        self.status_combo.addItems(["intact", "damaged"])
        self.damage_combo = QComboBox()
        self.damage_combo.addItems(["Minor", "Major", "Destroyed"])
        self.damage_label = QLabel("Damage level")
        self.xmin_spin = QDoubleSpinBox()
        self.ymin_spin = QDoubleSpinBox()
        self.xmax_spin = QDoubleSpinBox()
        self.ymax_spin = QDoubleSpinBox()
        for spin in [self.xmin_spin, self.ymin_spin, self.xmax_spin, self.ymax_spin]:
            spin.setDecimals(3)
            spin.setRange(-1e12, 1e12)
            spin.setSingleStep(0.5)

        form = QFormLayout()
        form.addRow("Box", self.box_select)
        form.addRow("Building status", self.status_combo)
        form.addRow(self.damage_label, self.damage_combo)
        form.addRow("xmin", self.xmin_spin)
        form.addRow("ymin", self.ymin_spin)
        form.addRow("xmax", self.xmax_spin)
        form.addRow("ymax", self.ymax_spin)

        self.summary = QLabel("")
        self.summary.setWordWrap(True)
        self.summary.setObjectName("PanelHint")

        side_layout.addWidget(side_title)
        side_layout.addWidget(self.box_list)
        side_layout.addLayout(meta_box_actions)
        side_layout.addWidget(self.split_edit_toggle)
        side_layout.addLayout(form)
        side_layout.addWidget(self.summary)
        side_layout.addStretch(1)

        self._update_damage_visibility()

        body.addWidget(viewer_frame)
        body.addWidget(side)
        body.setStretchFactor(0, 4)
        body.setStretchFactor(1, 1)

        footer = QFrame()
        footer.setObjectName("HeaderBar")
        footer_layout = QHBoxLayout(footer)
        footer_layout.setContentsMargins(14, 12, 14, 12)
        self.back_button = QPushButton("Back to Annotation")
        self.save_next_button = QPushButton("Save Tile & Next Tile")
        self.skip_button = QPushButton("Skip Tile")
        self.back_button.setObjectName("BackBtn")
        self.save_next_button.setObjectName("SaveBtn")
        self.skip_button.setObjectName("Skip2Btn")
        footer_layout.addWidget(self.back_button)
        footer_layout.addStretch(1)
        footer_layout.addWidget(self.skip_button)
        footer_layout.addWidget(self.save_next_button)

        main_layout.addWidget(header)
        main_layout.addWidget(body, 1)
        main_layout.addWidget(footer)

    def set_header(self, tile_name: str, index: int, total: int):
        self.title_label.setText(f"Tile {index + 1} / {total}: {tile_name}")

    def set_boxes(self, boxes: list[dict], selected_box_id: int | None):
        self.box_list.blockSignals(True)
        self.box_list.clear()
        self.box_select.blockSignals(True)
        self.box_select.clear()
        for box in boxes:
            label = f"Box {box['box_id']}"
            self.box_select.addItem(label, box["box_id"])
            split_tag = "split" if box.get("split_editing") else "shared"
            damage_part = f", {box['damage_level']}" if box["building_status"] == "damaged" and box["damage_level"] else ""
            item = QListWidgetItem(f"{label}  [{box['building_status']}{damage_part}, {split_tag}]")
            item.setData(Qt.UserRole, box["box_id"])
            self.box_list.addItem(item)
            if box["box_id"] == selected_box_id:
                self.box_select.setCurrentIndex(self.box_select.count() - 1)
                item.setSelected(True)
        self.box_list.blockSignals(False)
        self.box_select.blockSignals(False)

    def selected_box_id(self):
        return self.box_select.currentData()

    def _update_damage_visibility(self):
        show_damage = self.status_combo.currentText() == "damaged"
        self.damage_label.setVisible(show_damage)
        self.damage_combo.setVisible(show_damage)


class MainWindow(QMainWindow):
    def __init__(self):
        super().__init__()
        self.setWindowTitle(APP_TITLE)
        window_icon = load_pixmap(APP_ICON_PATH, 64)
        if window_icon is not None:
            self.setWindowIcon(QIcon(window_icon))
        self.resize(1600, 1020)

        self.phase = "setup"
        self.project_root = ""
        self.sar_dir = ""
        self.optical_dir = ""
        self.output_dir = ""
        self.disaster_type = ""
        self.project_metadata = {}
        self.project_metadata_rows = []
        self.processed_tiles = []
        self._last_processed_index = 0
        self._last_processed_tile = ""
        self.recent_projects = []
        self.tile_refs: list[tuple[Path, Path]] = []
        self.tile_states: dict[str, dict] = {}
        self.current_index = 0
        self.view_bounds = None
        self.tool_mode = "select"
        self.pending_message = ""
        self._refresh_pending = False
        self._preview_quality = "full"
        self._full_quality_timer = QTimer(self)
        self._full_quality_timer.setSingleShot(True)
        self._full_quality_timer.setInterval(180)
        self._full_quality_timer.timeout.connect(self._restore_full_quality)
        self._syncing_split_toggle = False
        self._restoring_setup_state = False
        self._state_save_pending = False
        self._startup_recent_prompt_done = False
        self._restored_tile_states = {}
        self._update_check_started = False
        self._update_thread = None
        self._update_worker = None
        self._download_thread = None
        self._download_worker = None

        self.stack = QStackedWidget()
        self.setup_page = SetupPage()
        self.annotate_page = AnnotatePage()
        self.metadata_page = MetadataPage()
        self.stack.addWidget(self.setup_page)
        self.stack.addWidget(self.annotate_page)
        self.stack.addWidget(self.metadata_page)
        central = QWidget()
        central_layout = QVBoxLayout(central)
        central_layout.setContentsMargins(0, 0, 0, 0)
        central_layout.setSpacing(0)

        self.top_bar = QFrame()
        self.top_bar.setObjectName("TopBar")
        top_layout = QHBoxLayout(self.top_bar)
        top_layout.setContentsMargins(18, 10, 18, 10)
        top_layout.setSpacing(12)

        logo_pixmap = load_pixmap(APP_LOGO_PATH, 132)
        if logo_pixmap is not None:
            logo = QLabel()
            logo.setObjectName("Logo")
            logo.setPixmap(logo_pixmap)
            logo.setScaledContents(False)
        else:
            logo = QLabel("SAR<span style='color:#4ade80;'>/</span>Annotate")
            logo.setObjectName("Logo")
            logo.setTextFormat(Qt.RichText)
        top_layout.addWidget(logo)

        top_layout.addStretch(1)

        self.tab_setup = QPushButton("01 Setup")
        self.tab_annotate = QPushButton("02 Annotate")
        self.tab_metadata = QPushButton("03 Metadata")
        self.nav_tabs = [self.tab_setup, self.tab_annotate, self.tab_metadata]
        for btn, phase in [
            (self.tab_setup, "setup"),
            (self.tab_annotate, "annotate"),
            (self.tab_metadata, "metadata"),
        ]:
            btn.setCheckable(True)
            btn.setObjectName("TabBtn")
            btn.setProperty("navtab", True)
            btn.clicked.connect(lambda _=False, p=phase: self._set_phase(p))
            top_layout.addWidget(btn)

        top_layout.addSpacing(12)
        self.theme_mode = "dark"
        self.mode_toggle = QPushButton("☀")
        self.mode_toggle.setObjectName("ModeToggle")
        self.mode_toggle.setCheckable(True)
        self.mode_toggle.setChecked(True)
        self.mode_toggle.clicked.connect(self.toggle_theme)
        top_layout.addWidget(self.mode_toggle)

        self.update_button = QPushButton("check updates")
        self.update_button.setObjectName("ModeToggle")
        self.update_button.clicked.connect(lambda: self.check_for_updates(True))
        top_layout.addWidget(self.update_button)

        self.update_log = QLabel("update: idle")
        self.update_log.setObjectName("UpdateLog")
        top_layout.addWidget(self.update_log)

        self.version_label = QLabel(f"v{APP_VERSION}")
        self.version_label.setObjectName("VersionPill")
        top_layout.addWidget(self.version_label)

        central_layout.addWidget(self.top_bar)
        central_layout.addWidget(self.stack, 1)
        self.setCentralWidget(central)

        self.status = QStatusBar()
        self.setStatusBar(self.status)

        self.setup_page.loadRequested.connect(self.load_project)
        self.setup_page.metadataChanged.connect(self._on_setup_metadata_changed)

        self.annotate_page.fit_button.clicked.connect(self.fit_view)
        self.annotate_page.draw_button.clicked.connect(lambda: self.set_tool_mode("draw"))
        self.annotate_page.select_button.clicked.connect(lambda: self.set_tool_mode("select"))
        self.annotate_page.skip_button.clicked.connect(self.skip_current_tile)
        self.annotate_page.next_button.clicked.connect(self.enter_metadata_phase)
        self.annotate_page.edit_button.clicked.connect(self.edit_selected_box)
        self.annotate_page.delete_button.clicked.connect(self.delete_selected_box)
        self.annotate_page.tileActivated.connect(self._annotate_tile_activated)
        self.annotate_page.box_list.itemSelectionChanged.connect(self._annotate_list_changed)

        self.metadata_page.back_button.clicked.connect(self.back_to_annotation)
        self.metadata_page.save_next_button.clicked.connect(self.save_and_next_tile)
        self.metadata_page.skip_button.clicked.connect(self.skip_current_tile)
        self.metadata_page.edit_button.clicked.connect(self.edit_selected_box)
        self.metadata_page.delete_button.clicked.connect(self.delete_selected_box)
        self.annotate_page.split_edit_toggle.stateChanged.connect(self._split_edit_toggle_changed)
        self.metadata_page.split_edit_toggle.stateChanged.connect(self._split_edit_toggle_changed)
        self.metadata_page.box_select.currentIndexChanged.connect(self._metadata_box_changed)
        self.metadata_page.box_list.itemSelectionChanged.connect(self._metadata_list_changed)
        for widget in [self.metadata_page.status_combo, self.metadata_page.damage_combo, self.metadata_page.xmin_spin, self.metadata_page.ymin_spin, self.metadata_page.xmax_spin, self.metadata_page.ymax_spin]:
            if isinstance(widget, QComboBox):
                widget.currentIndexChanged.connect(self._metadata_field_changed)
            else:
                widget.valueChanged.connect(self._metadata_field_changed)

        for pane in [self.annotate_page.sar_pane, self.annotate_page.optical_pane, self.metadata_page.sar_pane]:
            pane.viewChanged.connect(self.on_view_changed)
            pane.boxDrawn.connect(self.on_box_drawn)
            pane.boxEdited.connect(self.on_box_edited)
            pane.boxSelected.connect(self.on_box_selected)
            pane.viewportResized.connect(self.schedule_refresh)
            pane.set_theme(DARK_TOKENS)

        self._set_phase("setup")
        self._sync_setup_defaults()
        self._load_recent_projects()
        self.setup_page.set_recent_projects(self.recent_projects)
        QTimer.singleShot(0, self._prompt_resume_recent_project)
        QTimer.singleShot(1800, lambda: self.check_for_updates(False))
        self._update_status("Ready")

    def _sync_setup_defaults(self):
        self._restoring_setup_state = True
        try:
            self.setup_page.sar_dir.setText(self.sar_dir)
            self.setup_page.optical_dir.setText(self.optical_dir)
            self.setup_page.output_dir.setText(self.output_dir)
            self.setup_page.disaster_type.setText(self.disaster_type)
            self.setup_page.set_metadata_rows(self.project_metadata_rows)
        finally:
            self._restoring_setup_state = False

    def _update_status(self, text: str):
        self.status.showMessage(text)

    def _set_update_log(self, text: str):
        if hasattr(self, "update_log") and self.update_log is not None:
            self.update_log.setText(text)

    def check_for_updates(self, show_dialog: bool = False):
        if self._update_check_started:
            return
        self._update_check_started = True
        self._update_status("Checking ATS updates...")
        self._set_update_log("update: checking...")
        self._update_show_dialog = show_dialog
        self._update_thread = QThread(self)
        self._update_worker = UpdateCheckWorker(APP_VERSION)
        self._update_worker.moveToThread(self._update_thread)
        self._update_thread.started.connect(self._update_worker.run)
        self._update_worker.finished.connect(self._on_update_check_finished)
        self._update_worker.failed.connect(self._on_update_check_failed)
        self._update_worker.finished.connect(self._update_thread.quit)
        self._update_worker.failed.connect(self._update_thread.quit)
        self._update_thread.finished.connect(self._update_thread.deleteLater)
        self._update_worker.finished.connect(self._update_worker.deleteLater)
        self._update_worker.failed.connect(self._update_worker.deleteLater)
        self._update_thread.start()

    def _on_update_check_failed(self, message: str):
        self._update_status("Update check failed")
        self._set_update_log(f"update: failed - {message}")
        self.update_button.setText("check updates")
        self.update_button.setEnabled(True)
        self._update_check_started = False
        if getattr(self, "_update_show_dialog", False):
            QMessageBox.warning(
                self,
                "ATS update check failed",
                message,
            )

    def _on_update_check_finished(self, payload):
        self._update_status("Ready")
        self.update_button.setEnabled(True)
        self._update_check_started = False
        self.update_button.setText("check updates")
        show_dialog = getattr(self, "_update_show_dialog", False)
        if not isinstance(payload, dict) or not payload.get("available"):
            status = str(payload.get("status", "")).strip() if isinstance(payload, dict) else ""
            reason = str(payload.get("message", "")).strip() if isinstance(payload, dict) else ""
            source = str(payload.get("source", "")).strip() if isinstance(payload, dict) else ""
            if status == "up_to_date":
                source_suffix = f" from {source}" if source else ""
                self._set_update_log(f"update: up to date ({payload.get('latest_version', APP_VERSION)}{source_suffix})")
            elif status == "no_release":
                self._set_update_log("update: no GitHub release yet")
            elif status == "invalid_release":
                self._set_update_log("update: invalid GitHub release")
            elif status == "invalid_manifest":
                self._set_update_log("update: invalid update manifest")
            else:
                self._set_update_log("update: no update found")
            if show_dialog and isinstance(payload, dict):
                if reason:
                    QMessageBox.information(self, "ATS update status", reason)
            return
        latest_version = str(payload.get("latest_version", "")).strip()
        release_name = str(payload.get("release_name", latest_version)).strip()
        body = str(payload.get("body", "")).strip()
        download_url = str(payload.get("download_url", "")).strip()
        html_url = str(payload.get("html_url", "")).strip()
        source = str(payload.get("source", "")).strip()
        source_suffix = f" ({source})" if source else ""
        self._set_update_log(f"update: available {latest_version}{source_suffix}")
        message = (
            f"ATS Annotation Tool {latest_version} is available.\n\n"
            f"You are running {APP_VERSION}.\n\n"
            "Do you want to download and install the update now?"
        )
        if body:
            message += f"\n\nRelease notes:\n{body[:800]}"
        response = QMessageBox.question(
            self,
            "ATS Annotation Tool update available",
            message,
            QMessageBox.Yes | QMessageBox.No,
            QMessageBox.Yes,
        )
        if response != QMessageBox.Yes:
            return
        if not download_url:
            if html_url:
                QDesktopServices.openUrl(QUrl(html_url))
            else:
                QMessageBox.information(
                    self,
                    "ATS update unavailable",
                    "A release was found, but no installer asset was attached to it.",
                )
            return
        self._download_and_install_update(download_url, latest_version)

    def _download_and_install_update(self, url: str, latest_version: str):
        self._update_status(f"Downloading ATS update {latest_version}...")
        self._set_update_log(f"update: downloading {latest_version}")
        self.update_button.setEnabled(False)
        temp_root = Path(tempfile.gettempdir()) / "ATS_Annotation_Updates"
        filename = Path(urllib.parse.urlparse(url).path).name or "ATS_Annotation_Update.exe"
        destination = temp_root / filename
        self._download_thread = QThread(self)
        self._download_worker = UpdateDownloadWorker(url, destination)
        self._download_worker.moveToThread(self._download_thread)
        self._download_thread.started.connect(self._download_worker.run)
        self._download_worker.finished.connect(lambda path: self._on_update_download_finished(Path(path)))
        self._download_worker.failed.connect(self._on_update_download_failed)
        self._download_worker.finished.connect(self._download_thread.quit)
        self._download_worker.failed.connect(self._download_thread.quit)
        self._download_thread.finished.connect(self._download_thread.deleteLater)
        self._download_worker.finished.connect(self._download_worker.deleteLater)
        self._download_worker.failed.connect(self._download_worker.deleteLater)
        self._download_thread.start()

    def _on_update_download_failed(self, message: str):
        self._update_status("Update download failed")
        self._set_update_log(f"update: download failed - {message}")
        self.update_button.setEnabled(True)
        QMessageBox.warning(
            self,
            "Update download failed",
            f"Could not download the update.\n\n{message}",
        )

    def _on_update_download_finished(self, installer_path: Path):
        if not installer_path.is_file():
            self._on_update_download_failed("Downloaded installer file was not found.")
            return
        self._update_status("Preparing ATS update installer...")
        self._set_update_log("update: waiting for app to exit")
        if not self._launch_installer_after_exit(installer_path):
            self._on_update_download_failed("Could not start the update launcher.")
            return
        self._set_update_log("update: launching installer")
        QApplication.processEvents()
        os._exit(0)

    def _launch_installer_after_exit(self, installer_path: Path) -> bool:
        temp_root = Path(tempfile.gettempdir()) / "ATS_Annotation_Updates"
        temp_root.mkdir(parents=True, exist_ok=True)
        script_path = temp_root / f"launch_update_{os.getpid()}.ps1"
        script_path.write_text(
            "\n".join(
                [
                    f'$pidToWait = {os.getpid()}',
                    f'$installer = "{str(installer_path)}"',
                    'while (Get-Process -Id $pidToWait -ErrorAction SilentlyContinue) { Start-Sleep -Milliseconds 300 }',
                    'Start-Process -FilePath $installer',
                ]
            ),
            encoding="utf-8",
        )
        started = QProcess.startDetached(
            "powershell",
            [
                "-NoProfile",
                "-ExecutionPolicy",
                "Bypass",
                "-WindowStyle",
                "Hidden",
                "-File",
                str(script_path),
            ],
            str(temp_root),
        )
        return bool(started)

    def _project_state_path(self, output_dir: str | Path | None = None):
        root = output_dir if output_dir is not None else self.output_dir
        if not root:
            return None
        return Path(root) / "project_state.json"

    def _recent_projects_file(self):
        return RECENT_PROJECTS_PATH

    def _load_recent_projects(self):
        path = self._recent_projects_file()
        if not path.is_file():
            self.recent_projects = []
            return
        try:
            payload = json.loads(path.read_text(encoding="utf-8"))
            projects = payload.get("projects", payload if isinstance(payload, list) else [])
            if not isinstance(projects, list):
                projects = []
            self.recent_projects = [item for item in projects if isinstance(item, dict)]
        except Exception:
            self.recent_projects = []

    def _save_recent_projects(self):
        path = self._recent_projects_file()
        payload = {"projects": self.recent_projects[:12]}
        try:
            path.write_text(json.dumps(payload, indent=2), encoding="utf-8")
        except Exception:
            pass

    def _register_recent_project(self):
        if not self.output_dir:
            return
        entry = {
            "project_root": self.output_dir,
            "sar_dir": self.sar_dir,
            "optical_dir": self.optical_dir,
            "output_dir": self.output_dir,
            "disaster_type": self.disaster_type,
            "project_metadata_rows": self.project_metadata_rows,
            "project_metadata": self.project_metadata,
            "processed_tiles": self.processed_tiles,
            "current_index": self.current_index,
            "last_processed_index": self._last_processed_index,
            "last_processed_tile": self._last_processed_tile,
            "tile_count": len(self.tile_refs),
        }
        key = str(Path(self.output_dir).resolve())
        filtered = [item for item in self.recent_projects if str(Path(item.get("output_dir", item.get("project_root", ""))).resolve()) != key]
        filtered.insert(0, entry)
        self.recent_projects = filtered[:12]
        self._save_recent_projects()
        self.setup_page.set_recent_projects(self.recent_projects)

    def _load_project_state_file(self, output_dir: str | Path | None = None):
        path = self._project_state_path(output_dir)
        if path is None or not path.is_file():
            return None
        try:
            return json.loads(path.read_text(encoding="utf-8"))
        except Exception:
            return None

    def _serialize_tile_states(self):
        payload = {}
        for tile_name, state in self.tile_states.items():
            payload[tile_name] = {
                "next_box_id": int(state.get("next_box_id", 1)),
                "selected_box_id": state.get("selected_box_id"),
                "annotations": [box.to_dict() for box in state.get("annotations", [])],
            }
        return payload

    def _restore_tile_states(self, payload: dict | None):
        self.tile_states = {}
        if not isinstance(payload, dict):
            return
        for tile_name, state in payload.items():
            if not isinstance(state, dict):
                continue
            annotations = [BoxAnnotation.from_dict(item) for item in state.get("annotations", []) if isinstance(item, dict)]
            next_box_id = int(state.get("next_box_id", 1))
            if annotations:
                next_box_id = max(next_box_id, max(box.box_id for box in annotations) + 1)
            self.tile_states[tile_name] = {
                "annotations": annotations,
                "next_box_id": next_box_id,
                "selected_box_id": state.get("selected_box_id"),
            }

    def _geojson_path_for_tile(self, tile_name: str):
        if not self.output_dir:
            return None
        return Path(self.output_dir) / "Polygons" / f"{tile_name}.geojson"

    def _load_annotations_from_geojson(self, tile: TileRecord):
        path = self._geojson_path_for_tile(tile.name)
        if path is None or not path.is_file():
            return []
        try:
            payload = json.loads(path.read_text(encoding="utf-8"))
        except Exception:
            return []
        features = payload.get("features", [])
        if not isinstance(features, list) or not features:
            return []
        geojson_crs = payload.get("properties", {}).get("geojson_crs")
        transformer = None
        if geojson_crs and tile.display_crs and str(geojson_crs) != str(tile.display_crs):
            try:
                transformer = Transformer.from_crs(geojson_crs, tile.display_crs, always_xy=True)
            except Exception:
                transformer = None
        grouped = {}
        for feature in features:
            if not isinstance(feature, dict):
                continue
            props = feature.get("properties", {})
            if not isinstance(props, dict):
                props = {}
            box_id = int(props.get("box_id", 0) or 0)
            if box_id <= 0:
                box_id = len(grouped) + 1
            entry = grouped.setdefault(
                box_id,
                {
                    "box_id": box_id,
                    "building_status": props.get("building_status", "intact"),
                    "damage_level": props.get("damage_level", ""),
                    "split_editing": bool(props.get("split_editing", False)),
                    "sar": None,
                    "optical": None,
                },
            )
            source = str(props.get("source", "both"))
            geometry_bbox = bbox_from_geometry(feature.get("geometry"), transformer)
            if source == "SAR":
                entry["sar"] = geometry_bbox or entry["sar"]
                entry["optical"] = entry["optical"] or bbox_from_dict(props.get("optical_geometry"))
                entry["split_editing"] = True
            elif source == "Optical":
                entry["optical"] = geometry_bbox or entry["optical"]
                entry["sar"] = entry["sar"] or bbox_from_dict(props.get("sar_geometry"))
                entry["split_editing"] = True
            else:
                entry["sar"] = geometry_bbox or entry["sar"]
                entry["optical"] = geometry_bbox or entry["optical"]
        annotations = []
        for box_id in sorted(grouped):
            entry = grouped[box_id]
            sar_bbox = entry["sar"]
            if sar_bbox is None:
                continue
            box = BoxAnnotation(
                box_id=box_id,
                xmin=float(sar_bbox[0]),
                ymin=float(sar_bbox[1]),
                xmax=float(sar_bbox[2]),
                ymax=float(sar_bbox[3]),
                building_status=str(entry.get("building_status", "intact")),
                damage_level=str(entry.get("damage_level", "")),
                split_editing=bool(entry.get("split_editing", False)),
            )
            optical_bbox = entry.get("optical")
            if box.split_editing and optical_bbox is not None:
                box.enable_split_editing()
                box.set_geometry("optical", float(optical_bbox[0]), float(optical_bbox[1]), float(optical_bbox[2]), float(optical_bbox[3]))
            elif not box.split_editing:
                box.disable_split_editing()
            annotations.append(box)
        return annotations

    def _save_project_state(self):
        path = self._project_state_path()
        if path is None or not self.output_dir:
            return
        path.parent.mkdir(parents=True, exist_ok=True)
        payload = {
            "version": 1,
            "project_root": self.output_dir,
            "sar_dir": self.sar_dir,
            "optical_dir": self.optical_dir,
            "output_dir": self.output_dir,
            "disaster_type": self.disaster_type,
            "project_metadata_rows": self.project_metadata_rows,
            "project_metadata": self.project_metadata,
            "processed_tiles": self.processed_tiles,
            "current_index": self.current_index,
            "last_processed_index": self._last_processed_index,
            "last_processed_tile": self._last_processed_tile,
            "tile_states": self._serialize_tile_states(),
        }
        path.write_text(json.dumps(payload, indent=2), encoding="utf-8")

    def _schedule_project_state_save(self):
        if self._restoring_setup_state or not self.output_dir:
            return
        if self._state_save_pending:
            return
        self._state_save_pending = True
        QTimer.singleShot(250, self._flush_project_state_save)

    def _flush_project_state_save(self):
        self._state_save_pending = False
        self.project_metadata_rows = self.setup_page.metadata_rows()
        self.project_metadata = self.setup_page.project_metadata()
        self.disaster_type = self.setup_page.disaster_type.text().strip()
        self.setup_page.output_dir.setText(self.output_dir)
        self._save_project_state()
        self._register_recent_project()

    def _on_setup_metadata_changed(self):
        self._schedule_project_state_save()

    def _next_unprocessed_index(self):
        processed = set(self.processed_tiles)
        for idx, (sar_path, _opt_path) in enumerate(self.tile_refs):
            if sar_path.stem not in processed:
                return idx
        return 0

    def _ask_resume_project(self):
        dialog = QDialog(self)
        dialog.setWindowTitle("Resume project")
        layout = QVBoxLayout(dialog)
        label = QLabel(
            "A saved project state was found for this root.\n\n"
            "Continue: resume from the saved position.\n"
            "Start Over: ignore the saved progress and begin from the first tile.\n"
            "Cancel: stop loading this project."
        )
        label.setWordWrap(True)
        layout.addWidget(label)
        buttons = QDialogButtonBox()
        continue_btn = buttons.addButton("Continue", QDialogButtonBox.AcceptRole)
        restart_btn = buttons.addButton("Start Over", QDialogButtonBox.DestructiveRole)
        cancel_btn = buttons.addButton(QDialogButtonBox.Cancel)
        buttons.accepted.connect(lambda: dialog.done(1))
        restart_btn.clicked.connect(lambda: dialog.done(2))
        buttons.rejected.connect(lambda: dialog.done(0))
        layout.addWidget(buttons)
        result = dialog.exec()
        if result == 1:
            return "continue"
        if result == 2:
            return "restart"
        return None

    def _prompt_resume_recent_project(self):
        if self._startup_recent_prompt_done:
            return
        self._startup_recent_prompt_done = True
        if not self.recent_projects:
            return
        last_project = self.recent_projects[0]
        root = last_project.get("project_root") or last_project.get("output_dir") or "the last project"
        dialog = QMessageBox(self)
        dialog.setWindowTitle("Continue last project?")
        dialog.setIcon(QMessageBox.Question)
        dialog.setText(f"Resume the last project from:\n{root}")
        dialog.setInformativeText("Your saved metadata and the last opened tile will be restored.")
        continue_btn = dialog.addButton("Continue", QMessageBox.AcceptRole)
        dialog.addButton("Open Setup", QMessageBox.RejectRole)
        cancel_btn = dialog.addButton(QMessageBox.Cancel)
        dialog.exec()
        clicked = dialog.clickedButton()
        if clicked == continue_btn:
            self.load_project({**last_project, "resume_choice": "continue"})
        elif clicked == cancel_btn:
            return

    def toggle_theme(self):
        app = QApplication.instance()
        if app is None:
            return
        if self.theme_mode == "dark":
            self.theme_mode = "light"
            tokens = LIGHT_TOKENS
            self.mode_toggle.setText("☾")
            self.mode_toggle.setChecked(False)
        else:
            self.theme_mode = "dark"
            tokens = DARK_TOKENS
            self.mode_toggle.setText("☀")
            self.mode_toggle.setChecked(True)
        apply_theme(app, tokens)
        for pane in [self.annotate_page.sar_pane, self.annotate_page.optical_pane, self.metadata_page.sar_pane]:
            pane.set_theme(tokens)
        self.refresh_views()

    def _set_phase(self, phase: str):
        self.phase = phase
        for btn, name in [(self.tab_setup, "setup"), (self.tab_annotate, "annotate"), (self.tab_metadata, "metadata")]:
            btn.setChecked(name == phase)
        if phase == "setup":
            self.stack.setCurrentWidget(self.setup_page)
        elif phase == "annotate":
            self.stack.setCurrentWidget(self.annotate_page)
        elif phase == "metadata":
            self.stack.setCurrentWidget(self.metadata_page)
        self.schedule_refresh()

    def current_tile_state(self):
        if not self.tile_refs:
            return None, None
        if self.current_index < 0 or self.current_index >= len(self.tile_refs):
            return None, None
        sar_path, optical_path = self.tile_refs[self.current_index]
        record = load_tile_pair(str(sar_path), str(optical_path))
        state = self.tile_states.setdefault(record["name"], {"annotations": [], "next_box_id": 1, "selected_box_id": None})
        if not state["annotations"]:
            tile = TileRecord(
                name=record["name"],
                sar_path=record["sar_path"],
                optical_path=record["optical_path"],
                sar_data=record["sar_data"],
                optical_data=record["optical_data"],
                sar_transform=record["sar_transform"],
                optical_transform=record["optical_transform"],
                sar_crs=record["sar_crs"],
                optical_crs=record["optical_crs"],
                sar_width=record["sar_width"],
                sar_height=record["sar_height"],
                optical_width=record["optical_width"],
                optical_height=record["optical_height"],
                sar_bounds=record["sar_bounds"],
                optical_bounds=record["optical_bounds"],
                display_crs=record["display_crs"],
                shared_bounds=record["shared_bounds"],
                annotations=[],
                next_box_id=1,
                selected_box_id=None,
            )
            annotations = self._load_annotations_from_geojson(tile)
            if not annotations:
                restored = self._restored_tile_states.get(record["name"], {})
                if isinstance(restored, dict):
                    annotations = [BoxAnnotation.from_dict(item) for item in restored.get("annotations", []) if isinstance(item, dict)]
                    if annotations:
                        state["selected_box_id"] = restored.get("selected_box_id")
                        state["next_box_id"] = max(int(restored.get("next_box_id", 1)), max(box.box_id for box in annotations) + 1)
            if annotations:
                state["annotations"] = annotations
                state["next_box_id"] = max(state.get("next_box_id", 1), max(box.box_id for box in annotations) + 1)
                if state.get("selected_box_id") is None:
                    state["selected_box_id"] = annotations[0].box_id
        annotations = state["annotations"]
        tile = TileRecord(
            name=record["name"],
            sar_path=record["sar_path"],
            optical_path=record["optical_path"],
            sar_data=record["sar_data"],
            optical_data=record["optical_data"],
            sar_transform=record["sar_transform"],
            optical_transform=record["optical_transform"],
            sar_crs=record["sar_crs"],
            optical_crs=record["optical_crs"],
            sar_width=record["sar_width"],
            sar_height=record["sar_height"],
            optical_width=record["optical_width"],
            optical_height=record["optical_height"],
            sar_bounds=record["sar_bounds"],
            optical_bounds=record["optical_bounds"],
            display_crs=record["display_crs"],
            shared_bounds=record["shared_bounds"],
            annotations=annotations,
            next_box_id=state["next_box_id"],
            selected_box_id=state["selected_box_id"],
        )
        return tile, state

    def _selected_split_editing(self, tile: TileRecord | None = None, state: dict | None = None):
        if tile is None or state is None:
            tile, state = self.current_tile_state()
        if tile is None:
            return False
        box_id = state.get("selected_box_id")
        if box_id is None and tile.annotations:
            box_id = tile.annotations[0].box_id
        box = next((b for b in tile.annotations if b.box_id == box_id), None)
        return bool(box.split_editing) if box is not None else False

    def _sync_split_edit_toggle(self, tile: TileRecord | None = None, state: dict | None = None):
        if tile is None or state is None:
            tile, state = self.current_tile_state()
        if tile is None:
            return
        enabled = self._selected_split_editing(tile, state)
        self._syncing_split_toggle = True
        try:
            for checkbox in [self.annotate_page.split_edit_toggle, self.metadata_page.split_edit_toggle]:
                checkbox.blockSignals(True)
                checkbox.setChecked(enabled)
                checkbox.blockSignals(False)
        finally:
            self._syncing_split_toggle = False

    def _split_edit_toggle_changed(self, checked: int):
        if self._syncing_split_toggle:
            return
        tile, state, box = self._current_selected_box()
        if tile is None or box is None:
            return
        if bool(checked):
            box.enable_split_editing()
        else:
            box.disable_split_editing()
        self._sync_split_edit_toggle(tile, state)
        self.refresh_views()

    def schedule_refresh(self):
        if self._refresh_pending:
            return
        self._refresh_pending = True
        QTimer.singleShot(0, self.refresh_views)

    def _schedule_full_quality_restore(self):
        self._full_quality_timer.start()

    def _restore_full_quality(self):
        self._preview_quality = "full"
        self.refresh_views()

    def refresh_views(self):
        self._refresh_pending = False
        tile, state = self.current_tile_state()
        if tile is None:
            return
        view_bounds = self.view_bounds or bounds_to_dict(tile.shared_bounds)
        self.view_bounds = view_bounds
        sar_boxes = [box_to_dict(box, "sar") for box in tile.annotations]
        optical_boxes = [box_to_dict(box, "optical") for box in tile.annotations]
        preview_sizes = {kind: preview_size_for_quality(tile.shared_bounds, self._preview_quality) for kind in ["sar", "optical", "meta"]}
        if hasattr(self.annotate_page, "set_tiles"):
            tile_rows = []
            for idx, (sar_path, _opt_path) in enumerate(self.tile_refs):
                tile_rows.append({
                    "name": Path(sar_path).stem,
                    "processed": Path(sar_path).stem in self.processed_tiles,
                    "last_processed": Path(sar_path).stem == self._last_processed_tile,
                })
            self.annotate_page.set_tiles(tile_rows, self.current_index)
        if self.phase == "annotate":
            sar_image = render_preview_image(
                str(tile.sar_path),
                str(tile.optical_path),
                "sar",
                view_bounds["left"],
                view_bounds["bottom"],
                view_bounds["right"],
                view_bounds["top"],
                *preview_sizes["sar"],
            )
            opt_image = render_preview_image(
                str(tile.sar_path),
                str(tile.optical_path),
                "optical",
                view_bounds["left"],
                view_bounds["bottom"],
                view_bounds["right"],
                view_bounds["top"],
                *preview_sizes["optical"],
            )
            self.annotate_page.sar_pane.set_content(
                sar_image,
                view_bounds,
                sar_boxes,
                state["selected_box_id"],
                self.tool_mode,
                draw_debug_bounds(tile),
                f"{preview_sizes['sar'][0]}x{preview_sizes['sar'][1]} | {'loaded' if not sar_image.isNull() else 'decode failed'}",
            )
            self.annotate_page.optical_pane.set_content(
                opt_image,
                view_bounds,
                optical_boxes,
                state["selected_box_id"],
                self.tool_mode,
                draw_debug_bounds(tile),
                f"{preview_sizes['optical'][0]}x{preview_sizes['optical'][1]} | {'loaded' if not opt_image.isNull() else 'decode failed'}",
            )
            self.annotate_page.set_header(tile.name, self.current_index, len(self.tile_refs), self.tool_mode, bool(sar_boxes))
            self.annotate_page.set_project_summary(
                f"Project root: {self.output_dir}\nSAR folder: {self.sar_dir}\nOptical folder: {self.optical_dir}\nOutput folder: {self.output_dir}"
            )
            self.annotate_page.set_boxes(sar_boxes, state["selected_box_id"])
            self._sync_split_edit_toggle(tile, state)
        elif self.phase == "metadata":
            sar_image = render_preview_image(
                str(tile.sar_path),
                str(tile.optical_path),
                "sar",
                view_bounds["left"],
                view_bounds["bottom"],
                view_bounds["right"],
                view_bounds["top"],
                *preview_sizes["meta"],
            )
            self.metadata_page.sar_pane.set_content(
                sar_image,
                view_bounds,
                sar_boxes,
                state["selected_box_id"],
                "select",
                draw_debug_bounds(tile),
                f"{preview_sizes['meta'][0]}x{preview_sizes['meta'][1]} | {'loaded' if not sar_image.isNull() else 'decode failed'}",
            )
            self.metadata_page.set_header(tile.name, self.current_index, len(self.tile_refs))
            self.metadata_page.set_boxes(sar_boxes, state["selected_box_id"])
            self._sync_metadata_form(tile, state)
            self._sync_split_edit_toggle(tile, state)
            extra_meta = "\n".join([f"{key}: {value or '[empty]'}" for key, value in self.project_metadata.items()]) or "[none]"
            self.metadata_page.summary.setText(
                "Project metadata:\n"
                f"Disaster type: {self.disaster_type or '[empty]'}\n"
                f"{extra_meta}"
            )
        self._update_status(f"Tile {self.current_index + 1} / {len(self.tile_refs)} | {tile.name} | {self.phase}")
        if self._preview_quality == "low":
            self._schedule_full_quality_restore()

    def _sync_metadata_form(self, tile: TileRecord, state: dict):
        boxes = tile.annotations
        if not boxes:
            self.metadata_page.box_select.blockSignals(True)
            self.metadata_page.box_select.clear()
            self.metadata_page.box_list.clear()
            self.metadata_page.box_select.blockSignals(False)
            self.metadata_page.setEnabled(False)
            return
        self.metadata_page.setEnabled(True)
        selected_id = state["selected_box_id"] or boxes[0].box_id
        state["selected_box_id"] = selected_id
        self.metadata_page.box_select.blockSignals(True)
        self.metadata_page.box_select.clear()
        self.metadata_page.box_list.blockSignals(True)
        self.metadata_page.box_list.clear()
        for box in boxes:
            self.metadata_page.box_select.addItem(f"Box {box.box_id}", box.box_id)
            damage_part = f", {box.damage_level}" if box.building_status == "damaged" and box.damage_level else ""
            item = QListWidgetItem(f"Box {box.box_id}  [{box.building_status}{damage_part}]")
            item.setData(Qt.UserRole, box.box_id)
            if box.box_id == selected_id:
                self.metadata_page.box_select.setCurrentIndex(self.metadata_page.box_select.count() - 1)
                item.setSelected(True)
            self.metadata_page.box_list.addItem(item)
        self.metadata_page.box_select.blockSignals(False)
        self.metadata_page.box_list.blockSignals(False)
        self._fill_metadata_controls(tile, selected_id)

    def _fill_metadata_controls(self, tile: TileRecord, selected_id: int):
        box = next((b for b in tile.annotations if b.box_id == selected_id), None)
        if not box:
            return
        self.metadata_page.status_combo.blockSignals(True)
        self.metadata_page.damage_combo.blockSignals(True)
        self.metadata_page.xmin_spin.blockSignals(True)
        self.metadata_page.ymin_spin.blockSignals(True)
        self.metadata_page.xmax_spin.blockSignals(True)
        self.metadata_page.ymax_spin.blockSignals(True)

        self.metadata_page.status_combo.setCurrentText(box.building_status)
        self.metadata_page.damage_combo.setCurrentText(box.damage_level or "Minor")
        self.metadata_page._update_damage_visibility()
        xmin, ymin, xmax, ymax = box.normalized()
        self.metadata_page.xmin_spin.setValue(xmin)
        self.metadata_page.ymin_spin.setValue(ymin)
        self.metadata_page.xmax_spin.setValue(xmax)
        self.metadata_page.ymax_spin.setValue(ymax)

        self.metadata_page.status_combo.blockSignals(False)
        self.metadata_page.damage_combo.blockSignals(False)
        self.metadata_page.xmin_spin.blockSignals(False)
        self.metadata_page.ymin_spin.blockSignals(False)
        self.metadata_page.xmax_spin.blockSignals(False)
        self.metadata_page.ymax_spin.blockSignals(False)

    def _current_selected_box(self):
        tile, state = self.current_tile_state()
        if tile is None:
            return None, None, None
        box_id = state["selected_box_id"]
        if box_id is None and tile.annotations:
            box_id = tile.annotations[0].box_id
            state["selected_box_id"] = box_id
        box = next((b for b in tile.annotations if b.box_id == box_id), None)
        return tile, state, box

    def load_project(self, config: dict):
        sar_dir = Path(config["sar_dir"])
        optical_dir = Path(config["optical_dir"])
        output_dir = Path(config["output_dir"])
        if not config["sar_dir"] or not config["optical_dir"] or not config["output_dir"]:
            QMessageBox.warning(self, "Missing folders", "Please fill the SAR, optical, and project root/output folders.")
            return
        if not sar_dir.is_dir() or not optical_dir.is_dir():
            QMessageBox.warning(self, "Invalid folders", "Please choose valid SAR and optical folders.")
            return
        refs = load_tile_refs(sar_dir, optical_dir)
        if not refs:
            QMessageBox.warning(self, "No tiles", "No matching tile names were found between the two folders.")
            return
        state = self._load_project_state_file(output_dir)
        loaded_rows = config.get("project_metadata_rows", [])
        loaded_meta = config.get("project_metadata", {})
        loaded_disaster = config.get("disaster_type", "")
        current_index = 0
        processed_tiles = []
        resume_project = False
        resume_choice = config.get("resume_choice")
        if state:
            choice = resume_choice or self._ask_resume_project()
            if choice is None:
                return
            loaded_rows = state.get("project_metadata_rows", loaded_rows)
            loaded_meta = state.get("project_metadata", loaded_meta)
            loaded_disaster = state.get("disaster_type", loaded_disaster)
            if choice == "continue":
                processed_tiles = state.get("processed_tiles", [])
                current_index = int(state.get("last_processed_index", state.get("current_index", 0)))
            else:
                processed_tiles = []
                current_index = 0
            resume_project = choice == "continue"
        self.project_root = config["output_dir"]
        self.sar_dir = config["sar_dir"]
        self.optical_dir = config["optical_dir"]
        self.output_dir = config["output_dir"]
        self.disaster_type = loaded_disaster
        self.project_metadata_rows = loaded_rows
        self.project_metadata = loaded_meta
        self.processed_tiles = processed_tiles
        self._last_processed_index = int(state.get("last_processed_index", current_index)) if state else current_index
        self._last_processed_tile = str(state.get("last_processed_tile", "")) if state else ""
        self.tile_refs = refs
        self._restored_tile_states = state.get("tile_states", {}) if state else {}
        self.tile_states = {}
        if resume_project and state and state.get("current_index") is not None and processed_tiles:
            current_index = int(state.get("last_processed_index", state.get("current_index", 0)))
        elif resume_project and state and state.get("processed_tiles"):
            current_index = self._next_unprocessed_index()
        self.current_index = min(max(current_index, 0), len(refs) - 1) if refs else 0
        first = load_tile_pair(str(refs[0][0]), str(refs[0][1]))
        self.view_bounds = bounds_to_dict(first["shared_bounds"])
        output_dir.mkdir(parents=True, exist_ok=True)
        (output_dir / "Masks").mkdir(parents=True, exist_ok=True)
        (output_dir / "Polygons").mkdir(parents=True, exist_ok=True)
        self.tool_mode = "select"
        self._set_phase("annotate")
        self._sync_setup_defaults()
        self._save_project_state()
        self._register_recent_project()
        self.refresh_views()

    def set_tool_mode(self, mode: str):
        self.tool_mode = mode
        self.refresh_views()

    def fit_view(self, *args):
        tile, _ = self.current_tile_state()
        if tile is None:
            return
        self.view_bounds = bounds_to_dict(tile.shared_bounds)
        self.refresh_views()

    def on_view_changed(self, bounds: dict):
        self.view_bounds = clamp_bounds(bounds)
        self._preview_quality = "low"
        self.refresh_views()

    def on_box_drawn(self, box_data: dict):
        tile, state = self.current_tile_state()
        if tile is None:
            return
        image_kind = box_data.get("image_kind", "sar")
        box = BoxAnnotation(state["next_box_id"], box_data["xmin"], box_data["ymin"], box_data["xmax"], box_data["ymax"])
        if self._selected_split_editing(tile, state):
            box.enable_split_editing()
            box.set_geometry(image_kind, box_data["xmin"], box_data["ymin"], box_data["xmax"], box_data["ymax"])
        state["next_box_id"] += 1
        state["annotations"].append(box)
        state["selected_box_id"] = box.box_id
        self._save_project_state()
        self.refresh_views()

    def on_box_selected(self, box_id: int):
        tile, state = self.current_tile_state()
        if tile is None:
            return
        state["selected_box_id"] = box_id
        self.refresh_views()

    def on_box_edited(self, box_data: dict):
        tile, state = self.current_tile_state()
        if tile is None:
            return
        box = next((item for item in tile.annotations if item.box_id == box_data["box_id"]), None)
        if box is None:
            return
        image_kind = box_data.get("image_kind", "sar")
        box.set_geometry(image_kind, box_data["xmin"], box_data["ymin"], box_data["xmax"], box_data["ymax"])
        state["selected_box_id"] = box.box_id
        self._save_project_state()
        self.refresh_views()

    def edit_selected_box(self):
        tile, state, box = self._current_selected_box()
        if tile is None or box is None:
            QMessageBox.information(self, "No box selected", "Select a bounding box first.")
            return
        state["selected_box_id"] = box.box_id
        self.tool_mode = "edit"
        self._set_phase("annotate")
        self.refresh_views()

    def delete_selected_box(self):
        tile, state, box = self._current_selected_box()
        if tile is None or box is None:
            QMessageBox.information(self, "No box selected", "Select a bounding box first.")
            return
        answer = QMessageBox.question(
            self,
            "Delete box",
            f"Delete Box {box.box_id} from the current tile?",
            QMessageBox.Yes | QMessageBox.No,
            QMessageBox.No,
        )
        if answer != QMessageBox.Yes:
            return
        annotations = state["annotations"]
        annotations[:] = [item for item in annotations if item.box_id != box.box_id]
        if annotations:
            state["selected_box_id"] = annotations[0].box_id
        else:
            state["selected_box_id"] = None
            state["next_box_id"] = 1
        if self.phase == "metadata" and not annotations:
            self._set_phase("annotate")
        self._save_project_state()
        self.refresh_views()

    def _annotate_list_changed(self, *args):
        item = self.annotate_page.box_list.currentItem()
        if not item:
            return
        box_id = item.data(Qt.UserRole)
        self.on_box_selected(box_id)

    def _annotate_tile_activated(self, item):
        if item is None:
            return
        index = item.data(Qt.UserRole)
        if index is None:
            return
        self.jump_to_tile(int(index))

    def _metadata_box_changed(self, *args):
        tile, state, box = self._current_selected_box()
        if tile is None or box is None:
            return
        state["selected_box_id"] = self.metadata_page.box_select.currentData()
        self._fill_metadata_controls(tile, state["selected_box_id"])
        self.refresh_views()

    def _metadata_list_changed(self, *args):
        item = self.metadata_page.box_list.currentItem()
        if not item:
            return
        box_id = item.data(Qt.UserRole)
        self.metadata_page.box_select.setCurrentIndex(self.metadata_page.box_select.findData(box_id))
        self._metadata_field_changed()

    def _metadata_field_changed(self, *args):
        tile, state, box = self._current_selected_box()
        if tile is None or box is None:
            return
        box.building_status = self.metadata_page.status_combo.currentText()
        if box.building_status == "damaged":
            box.damage_level = self.metadata_page.damage_combo.currentText()
        else:
            box.damage_level = ""
        self.metadata_page._update_damage_visibility()
        box.set_geometry(
            "sar",
            self.metadata_page.xmin_spin.value(),
            self.metadata_page.ymin_spin.value(),
            self.metadata_page.xmax_spin.value(),
            self.metadata_page.ymax_spin.value(),
        )
        self.project_metadata_rows = self.setup_page.metadata_rows()
        self.project_metadata = self.setup_page.project_metadata()
        self.disaster_type = self.setup_page.disaster_type.text().strip()
        self._schedule_project_state_save()
        self.refresh_views()

    def enter_metadata_phase(self, *args):
        tile, state = self.current_tile_state()
        if tile is None:
            return
        if not tile.annotations:
            QMessageBox.information(self, "No boxes", "Draw at least one box before moving to metadata.")
            return
        self.tool_mode = "select"
        if state["selected_box_id"] is None:
            state["selected_box_id"] = tile.annotations[0].box_id
        self._set_phase("metadata")
        self.refresh_views()

    def back_to_annotation(self, *args):
        self._set_phase("annotate")
        self.refresh_views()

    def save_and_next_tile(self, *args):
        tile, state = self.current_tile_state()
        if tile is None:
            return
        if not tile.annotations:
            QMessageBox.information(self, "No boxes", "Draw at least one box or skip the tile.")
            return
        self._save_current_tile(tile, state)
        self._go_next_tile()

    def skip_current_tile(self, *args):
        tile, state = self.current_tile_state()
        if tile is None:
            return
        if tile.annotations:
            answer = QMessageBox.question(
                self,
                "Skip tile",
                "This tile has boxes. Skip and discard them?",
                QMessageBox.Yes | QMessageBox.No,
                QMessageBox.No,
            )
            if answer != QMessageBox.Yes:
                return
        self._go_next_tile()

    def _save_current_tile(self, tile: TileRecord, state: dict):
        output_dir = Path(self.output_dir)
        self.project_metadata_rows = self.setup_page.metadata_rows()
        self.project_metadata = self.setup_page.project_metadata()
        self.disaster_type = self.setup_page.disaster_type.text().strip()
        export_tile(
            tile,
            output_dir,
            {
                "disaster_type": self.disaster_type,
                "project_metadata": self.project_metadata,
            },
        )
        if tile.name not in self.processed_tiles:
            self.processed_tiles.append(tile.name)
        self._last_processed_index = self.current_index
        self._last_processed_tile = tile.name
        self._save_project_state()

    def _go_next_tile(self):
        tile, state = self.current_tile_state()
        if tile is None:
            return
        if self.current_index + 1 >= len(self.tile_refs):
            self.current_index = 0
            self._set_phase("setup")
            self.pending_message = "All tiles processed."
            self._sync_setup_defaults()
            self._update_status("All tiles processed.")
            self._save_project_state()
            return
        self.current_index += 1
        next_record = load_tile_pair(str(self.tile_refs[self.current_index][0]), str(self.tile_refs[self.current_index][1]))
        self.view_bounds = bounds_to_dict(next_record["shared_bounds"])
        self.tool_mode = "select"
        self._set_phase("annotate")
        self._save_project_state()
        self.refresh_views()

    def jump_to_tile(self, index: int):
        if not self.tile_refs:
            return
        index = max(0, min(int(index), len(self.tile_refs) - 1))
        self.current_index = index
        self.tool_mode = "select"
        self._set_phase("annotate")
        tile, _ = self.current_tile_state()
        if tile is not None:
            self.view_bounds = bounds_to_dict(tile.shared_bounds)
        self._save_project_state()
        self.refresh_views()

    def closeEvent(self, event):
        event.accept()


def main():
    set_windows_app_id()
    app = QApplication([])
    app.setApplicationName(APP_TITLE)
    app.setApplicationDisplayName(APP_TITLE)
    app_icon = load_pixmap(APP_ICON_PATH, 64)
    if app_icon is not None:
        app.setWindowIcon(QIcon(app_icon))
    apply_dark_theme(app)
    window = MainWindow()
    window.show()
    app.exec()


if __name__ == "__main__":
    main()
