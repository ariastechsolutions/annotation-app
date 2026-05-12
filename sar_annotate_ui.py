"""
SAR/Annotate Desktop — PySide6 UI
Implements the dark/light monospace-terminal design proposal.
Three pages: Setup → Annotate → Metadata, with a persistent status bar.

Requirements:
    pip install PySide6

Run:
    python sar_annotate_ui.py
"""

from PySide6.QtWidgets import (
    QApplication, QMainWindow, QWidget, QStackedWidget,
    QVBoxLayout, QHBoxLayout, QGridLayout,
    QLabel, QPushButton, QLineEdit, QComboBox, QScrollArea,
    QFrame, QSizePolicy, QFileDialog, QProgressBar,
    QSpacerItem,
)
from PySide6.QtCore import Qt, QSize, Signal, QRectF, QPointF
from PySide6.QtGui import (
    QFont, QFontDatabase, QPainter, QColor, QPen, QBrush,
    QPalette, QLinearGradient, QRadialGradient, QPainterPath,
)
import sys


# ---------------------------------------------------------------------------
# Design Tokens
# ---------------------------------------------------------------------------

DARK = {
    "bg0":            "#0e0f11",
    "bg1":            "#16181c",
    "bg2":            "#1e2128",
    "bg3":            "#272b33",
    "bg4":            "#303540",
    "border":         "#ffffff14",   # rgba(255,255,255,0.08)
    "border_strong":  "#ffffff28",   # rgba(255,255,255,0.16)
    "text_primary":   "#e8eaf0",
    "text_secondary": "#8b93a6",
    "text_muted":     "#525968",
    "accent":         "#4ade80",
    "accent_dim":     "#4ade801e",
    "accent_border":  "#4ade804c",
    "amber":          "#fbbf24",
    "amber_dim":      "#fbbf241e",
    "amber_border":   "#fbbf244c",
    "red":            "#f87171",
    "red_dim":        "#f871711e",
    "blue":           "#60a5fa",
    "blue_dim":       "#60a5fa1e",
}

LIGHT = {
    "bg0":            "#f0f1f3",
    "bg1":            "#ffffff",
    "bg2":            "#f4f5f7",
    "bg3":            "#e8eaed",
    "bg4":            "#dde0e5",
    "border":         "#00000012",
    "border_strong":  "#00000024",
    "text_primary":   "#111318",
    "text_secondary": "#4a5168",
    "text_muted":     "#8a92a6",
    "accent":         "#16a34a",
    "accent_dim":     "#16a34a1a",
    "accent_border":  "#16a34a4c",
    "amber":          "#d97706",
    "amber_dim":      "#d977061a",
    "amber_border":   "#d977064c",
    "red":            "#dc2626",
    "red_dim":        "#dc26261a",
    "blue":           "#2563eb",
    "blue_dim":       "#2563eb1a",
}


def stylesheet(t: dict) -> str:
    """Build the global QSS from a token dict."""
    return f"""
/* ── Global ── */
QWidget {{
    background-color: {t['bg0']};
    color: {t['text_primary']};
    font-family: "DM Mono", "Courier New", monospace;
    font-size: 12px;
    border: none;
    outline: none;
}}
QLabel {{
    background: transparent;
    color: {t['text_primary']};
}}

/* ── TopBar ── */
#TopBar {{
    background-color: {t['bg1']};
    border-bottom: 1px solid {t['border_strong']};
    min-height: 44px;
    max-height: 44px;
}}
#LogoLabel {{
    font-family: "Syne", "Segoe UI", sans-serif;
    font-size: 14px;
    font-weight: 700;
    letter-spacing: 2px;
    color: {t['text_primary']};
}}
#LogoAccent {{
    font-family: "Syne", "Segoe UI", sans-serif;
    font-size: 14px;
    font-weight: 700;
    color: {t['accent']};
}}

/* ── Tab buttons ── */
QPushButton#TabBtn {{
    background: transparent;
    color: {t['text_secondary']};
    border: 1px solid {t['border']};
    border-radius: 5px;
    padding: 4px 14px;
    font-size: 11px;
    letter-spacing: 1px;
    font-family: "DM Mono", monospace;
}}
QPushButton#TabBtn:hover {{
    background-color: {t['bg3']};
    color: {t['text_primary']};
}}
QPushButton#TabBtn[active="true"] {{
    background-color: {t['accent_dim']};
    border-color: {t['accent_border']};
    color: {t['accent']};
}}

/* ── Mode toggle button ── */
QPushButton#ModeToggle {{
    background: transparent;
    color: {t['text_muted']};
    border: 1px solid {t['border']};
    border-radius: 5px;
    padding: 4px 12px;
    font-size: 11px;
    font-family: "DM Mono", monospace;
}}
QPushButton#ModeToggle:hover {{
    background-color: {t['bg3']};
    color: {t['text_primary']};
}}

/* ── Section card / panel ── */
QFrame#Panel {{
    background-color: {t['bg1']};
    border-right: 1px solid {t['border_strong']};
}}
QFrame#SidebarPanel {{
    background-color: {t['bg1']};
    border-left: 1px solid {t['border']};
}}
QFrame#RightPanel {{
    background-color: {t['bg1']};
    border-left: 1px solid {t['border_strong']};
    min-width: 280px;
    max-width: 280px;
}}
QFrame#Divider {{
    background-color: {t['border_strong']};
    max-height: 1px;
    min-height: 1px;
}}

/* ── Section label ── */
QLabel#SectionLabel {{
    font-size: 10px;
    letter-spacing: 2px;
    color: {t['text_muted']};
    text-transform: uppercase;
    border-bottom: 1px solid {t['border']};
    padding-bottom: 6px;
    margin-bottom: 2px;
    background: transparent;
}}
QLabel#SubLabel {{
    font-size: 11px;
    color: {t['text_muted']};
    background: transparent;
}}
QLabel#FieldLabel {{
    font-size: 11px;
    color: {t['text_secondary']};
    background: transparent;
}}

/* ── Inputs ── */
QLineEdit {{
    background-color: {t['bg2']};
    border: 1px solid {t['border_strong']};
    border-radius: 5px;
    padding: 6px 10px;
    color: {t['text_primary']};
    font-size: 12px;
    font-family: "DM Mono", monospace;
    selection-background-color: {t['accent_dim']};
}}
QLineEdit:focus {{
    border-color: {t['accent_border']};
}}
QLineEdit::placeholder {{
    color: {t['text_muted']};
}}

/* ── Combo ── */
QComboBox {{
    background-color: {t['bg2']};
    border: 1px solid {t['border_strong']};
    border-radius: 5px;
    padding: 6px 10px;
    color: {t['text_primary']};
    font-size: 12px;
    font-family: "DM Mono", monospace;
    min-height: 30px;
}}
QComboBox:focus {{
    border-color: {t['accent_border']};
}}
QComboBox::drop-down {{
    border: none;
    width: 24px;
}}
QComboBox::down-arrow {{
    image: none;
    border-left: 4px solid transparent;
    border-right: 4px solid transparent;
    border-top: 5px solid {t['text_muted']};
    margin-right: 8px;
}}
QComboBox QAbstractItemView {{
    background-color: {t['bg2']};
    border: 1px solid {t['border_strong']};
    border-radius: 5px;
    color: {t['text_primary']};
    selection-background-color: {t['accent_dim']};
    selection-color: {t['accent']};
    padding: 4px;
}}

/* ── Generic action buttons ── */
QPushButton {{
    background: transparent;
    color: {t['text_secondary']};
    border: 1px solid {t['border']};
    border-radius: 5px;
    padding: 5px 12px;
    font-size: 11px;
    font-family: "DM Mono", monospace;
    letter-spacing: 0.5px;
}}
QPushButton:hover {{
    background-color: {t['bg3']};
    color: {t['text_primary']};
}}
QPushButton:pressed {{
    background-color: {t['bg4']};
}}

QPushButton#BrowseBtn {{
    background-color: {t['bg3']};
    border: 1px solid {t['border_strong']};
    color: {t['text_secondary']};
    border-radius: 5px;
    padding: 5px 10px;
    font-size: 11px;
}}
QPushButton#BrowseBtn:hover {{
    background-color: {t['bg4']};
    color: {t['text_primary']};
}}

QPushButton#LoadBtn {{
    background-color: {t['accent_dim']};
    border: 1px solid {t['accent_border']};
    color: {t['accent']};
    border-radius: 5px;
    padding: 9px 0;
    font-family: "Syne", "Segoe UI", sans-serif;
    font-size: 12px;
    font-weight: 700;
    letter-spacing: 2px;
}}
QPushButton#LoadBtn:hover {{
    background-color: {t['accent']};
    color: {t['bg0']};
}}

QPushButton#NextBtn {{
    background-color: {t['accent_dim']};
    border: 1px solid {t['accent_border']};
    color: {t['accent']};
}}
QPushButton#NextBtn:hover {{
    background-color: {t['accent']};
    color: {t['bg0']};
}}

QPushButton#SkipBtn {{
    border-color: {t['amber_border']};
    color: {t['amber']};
}}
QPushButton#SkipBtn:hover {{
    background-color: {t['amber_dim']};
}}

QPushButton#SaveBtn {{
    background-color: {t['accent_dim']};
    border: 1px solid {t['accent_border']};
    color: {t['accent']};
    font-weight: 600;
    padding: 8px;
    width: 100%;
    font-size: 12px;
}}
QPushButton#SaveBtn:hover {{
    background-color: {t['accent']};
    color: {t['bg0']};
}}

QPushButton#BackBtn {{
    background: transparent;
    border: 1px solid {t['border']};
    color: {t['text_secondary']};
    padding: 8px;
    font-size: 12px;
}}
QPushButton#BackBtn:hover {{
    background-color: {t['bg3']};
    color: {t['text_primary']};
}}

QPushButton#Skip2Btn {{
    background: transparent;
    border: 1px solid {t['amber_border']};
    color: {t['amber']};
    padding: 8px;
    font-size: 12px;
}}
QPushButton#Skip2Btn:hover {{
    background-color: {t['amber_dim']};
}}

QPushButton#ModeChipDraw {{
    background-color: {t['accent_dim']};
    border: 1px solid {t['accent_border']};
    color: {t['accent']};
    border-radius: 5px;
    padding: 4px 10px;
    font-size: 11px;
}}
QPushButton#ModeChipSelect {{
    background: transparent;
    border: 1px solid {t['border']};
    color: {t['text_secondary']};
    border-radius: 5px;
    padding: 4px 10px;
    font-size: 11px;
}}
QPushButton#ModeChipSelect:hover {{
    background-color: {t['bg3']};
}}

/* ── Box list item ── */
QFrame#BoxItem {{
    background-color: {t['bg2']};
    border: 1px solid {t['border']};
    border-radius: 5px;
}}
QFrame#BoxItem[selected="true"] {{
    background-color: {t['accent_dim']};
    border-color: {t['accent_border']};
}}

/* ── Selector buttons (metadata) ── */
QPushButton#SelBtn {{
    background-color: {t['bg2']};
    border: 1px solid {t['border']};
    color: {t['text_secondary']};
    border-radius: 5px;
    padding: 4px 10px;
    font-size: 11px;
}}
QPushButton#SelBtn:hover {{
    background-color: {t['bg3']};
}}
QPushButton#SelBtn[active="true"] {{
    background-color: {t['accent_dim']};
    border-color: {t['accent_border']};
    color: {t['accent']};
}}

/* ── Coord value ── */
QLabel#CoordVal {{
    background-color: {t['bg2']};
    border: 1px solid {t['border_strong']};
    border-radius: 5px;
    padding: 5px 8px;
    font-size: 11px;
    color: {t['text_primary']};
}}

/* ── Summary block ── */
QFrame#SummaryBlock {{
    background-color: {t['bg2']};
    border: 1px solid {t['border']};
    border-radius: 5px;
}}

/* ── Progress bar ── */
QProgressBar {{
    background-color: {t['bg4']};
    border: none;
    border-radius: 2px;
    height: 3px;
    max-height: 3px;
    text-align: center;
    color: transparent;
}}
QProgressBar::chunk {{
    background-color: {t['accent']};
    border-radius: 2px;
}}

/* ── Status bar ── */
QFrame#StatusBar {{
    background-color: {t['bg1']};
    border-top: 1px solid {t['border']};
    max-height: 28px;
    min-height: 28px;
}}
QLabel#StatusItem {{
    font-size: 11px;
    color: {t['text_muted']};
    background: transparent;
}}
QLabel#StatusVal {{
    font-size: 11px;
    color: {t['text_secondary']};
    font-weight: 500;
    background: transparent;
}}

/* ── Tile chip ── */
QFrame#TileChip {{
    background-color: {t['bg2']};
    border: 1px solid {t['border_strong']};
    border-radius: 5px;
    padding: 2px 6px;
}}

/* ── Hint note ── */
QLabel#HintNote {{
    font-size: 11px;
    color: {t['text_muted']};
    background: transparent;
    padding: 10px 12px;
}}

/* ── Scroll area ── */
QScrollArea {{
    background: transparent;
    border: none;
}}
QScrollBar:vertical {{
    background: {t['bg2']};
    width: 6px;
    border-radius: 3px;
}}
QScrollBar::handle:vertical {{
    background: {t['bg4']};
    border-radius: 3px;
    min-height: 20px;
}}
QScrollBar::add-line:vertical, QScrollBar::sub-line:vertical {{
    height: 0;
}}
"""


# ---------------------------------------------------------------------------
# Raster viewer widget (paints a fake SAR / optical background + boxes)
# ---------------------------------------------------------------------------

class RasterViewer(QWidget):
    """Paintable canvas simulating a georeferenced raster with bounding boxes."""

    def __init__(self, mode: str = "sar", tokens: dict = None, parent=None):
        super().__init__(parent)
        self.mode = mode          # "sar" | "optical"
        self.tokens = tokens or DARK
        self.boxes = [
            {"label": "BLD-01", "rect": QRectF(0.18, 0.22, 0.13, 0.09), "color": "accent",  "selected": False},
            {"label": "BLD-02", "rect": QRectF(0.38, 0.44, 0.10, 0.07), "color": "amber",   "selected": False},
            {"label": "BLD-03", "rect": QRectF(0.55, 0.60, 0.14, 0.10), "color": "accent",  "selected": False},
        ]
        self.highlight_index = -1   # for metadata page
        self.setSizePolicy(QSizePolicy.Expanding, QSizePolicy.Expanding)
        self.setMinimumSize(300, 200)

    def update_tokens(self, tokens: dict):
        self.tokens = tokens
        self.update()

    def paintEvent(self, event):
        p = QPainter(self)
        p.setRenderHint(QPainter.Antialiasing)
        w, h = self.width(), self.height()

        # Background
        if self.mode == "sar":
            base = QColor("#1a1e26") if self.tokens is DARK or self.tokens.get("bg0") == "#0e0f11" else QColor("#c8d0cc")
        else:
            base = QColor("#1e2a1a") if self.tokens is DARK or self.tokens.get("bg0") == "#0e0f11" else QColor("#2e5a20")
        p.fillRect(0, 0, w, h, base)

        # Faint grid
        grid_pen = QPen(QColor(255, 255, 255, 12))
        grid_pen.setWidthF(0.5)
        p.setPen(grid_pen)
        step = 40
        for x in range(0, w, step):
            p.drawLine(x, 0, x, h)
        for y in range(0, h, step):
            p.drawLine(0, y, w, y)

        # Viewer label
        t = self.tokens
        label_bg = QColor(0, 0, 0, 140) if t.get("bg0") == "#0e0f11" else QColor(255, 255, 255, 180)
        p.setPen(Qt.NoPen)
        p.setBrush(QBrush(label_bg))
        p.drawRoundedRect(8, 8, 46, 20, 4, 4)
        p.setPen(QColor(t["text_secondary"]))
        lbl_font = QFont("DM Mono", 9)
        p.setFont(lbl_font)
        p.drawText(12, 8, 42, 20, Qt.AlignVCenter | Qt.AlignLeft,
                   "SAR" if self.mode == "sar" else "OPT")

        # Bounding boxes
        for i, box in enumerate(self.boxes):
            rx = box["rect"].x() * w
            ry = box["rect"].y() * h
            rw = box["rect"].width() * w
            rh = box["rect"].height() * h

            is_selected = (i == self.highlight_index) if self.highlight_index >= 0 else False
            is_dimmed   = (self.highlight_index >= 0 and not is_selected)

            if box["color"] == "amber":
                stroke = QColor(t["amber"])
                fill   = QColor(t["amber_dim"] if "amber_dim" in t else "#fbbf241e")
            else:
                stroke = QColor(t["accent"])
                fill   = QColor(t["accent_dim"] if "accent_dim" in t else "#4ade801e")

            if is_dimmed:
                stroke.setAlphaF(0.4)
                fill.setAlphaF(0.2)

            box_pen = QPen(stroke)
            box_pen.setWidthF(1.5 if is_selected else 1.0)
            if is_selected:
                box_pen.setWidthF(2.0)
            p.setPen(box_pen)
            p.setBrush(QBrush(fill))
            p.drawRect(int(rx), int(ry), int(rw), int(rh))

            # Label chip
            lbl_bg = stroke
            lbl_bg_color = QColor(lbl_bg)
            p.setPen(Qt.NoPen)
            p.setBrush(QBrush(lbl_bg_color))
            lbl_w = 44
            p.drawRoundedRect(int(rx), int(ry) - 18, lbl_w, 15, 3, 3)
            p.setPen(QColor(t["bg0"]))
            lbl_font2 = QFont("DM Mono", 8)
            lbl_font2.setWeight(QFont.Medium)
            p.setFont(lbl_font2)
            p.drawText(int(rx), int(ry) - 18, lbl_w, 15,
                       Qt.AlignCenter, box["label"])

            # Handle dot (bottom-right)
            if not is_dimmed:
                p.setPen(Qt.NoPen)
                p.setBrush(QBrush(stroke))
                p.drawRoundedRect(int(rx + rw) - 5, int(ry + rh) - 5, 8, 8, 2, 2)

        p.end()


# ---------------------------------------------------------------------------
# Helpers
# ---------------------------------------------------------------------------

def h_line(tokens):
    f = QFrame()
    f.setObjectName("Divider")
    f.setFixedHeight(1)
    f.setStyleSheet(f"background-color: {tokens['border_strong']};")
    return f


def label(text, obj_name="", tokens=None, extra=""):
    lbl = QLabel(text)
    if obj_name:
        lbl.setObjectName(obj_name)
    return lbl


def section_label(text):
    lbl = QLabel(text.upper())
    lbl.setObjectName("SectionLabel")
    return lbl


def field_widget(label_text, placeholder="", value=""):
    container = QWidget()
    vl = QVBoxLayout(container)
    vl.setContentsMargins(0, 0, 0, 0)
    vl.setSpacing(4)
    lbl = QLabel(label_text)
    lbl.setObjectName("FieldLabel")
    vl.addWidget(lbl)
    row = QWidget()
    hl = QHBoxLayout(row)
    hl.setContentsMargins(0, 0, 0, 0)
    hl.setSpacing(6)
    edit = QLineEdit()
    edit.setPlaceholderText(placeholder)
    if value:
        edit.setText(value)
    browse = QPushButton("Browse")
    browse.setObjectName("BrowseBtn")
    browse.setFixedWidth(64)
    hl.addWidget(edit)
    hl.addWidget(browse)
    vl.addWidget(row)
    return container, edit, browse


def meta_field(label_text, value=""):
    container = QWidget()
    vl = QVBoxLayout(container)
    vl.setContentsMargins(0, 0, 0, 0)
    vl.setSpacing(4)
    lbl = QLabel(label_text)
    lbl.setObjectName("FieldLabel")
    edit = QLineEdit()
    edit.setText(value)
    vl.addWidget(lbl)
    vl.addWidget(edit)
    return container, edit


# ---------------------------------------------------------------------------
# Pages
# ---------------------------------------------------------------------------

class SetupPage(QWidget):
    project_loaded = Signal()

    def __init__(self, tokens, parent=None):
        super().__init__(parent)
        self.tokens = tokens
        self._build()

    def _build(self):
        root = QHBoxLayout(self)
        root.setContentsMargins(0, 0, 0, 0)
        root.setSpacing(0)

        # ── Left panel ──────────────────────────────────────────────────────
        left = QFrame()
        left.setObjectName("Panel")
        left.setFixedWidth(340)
        lv = QVBoxLayout(left)
        lv.setContentsMargins(22, 24, 22, 24)
        lv.setSpacing(16)

        lv.addWidget(section_label("Project paths"))

        fw_root, self.edit_root, btn_root = field_widget("Project root", "/home/user/projects/haiti_2023")
        fw_sar,  self.edit_sar,  btn_sar  = field_widget("SAR tiles directory", "sar_tiles/")
        fw_opt,  self.edit_opt,  btn_opt  = field_widget("Optical tiles directory", "optical_tiles/")
        fw_out,  self.edit_out,  btn_out  = field_widget("Output directory", "", "annotations_output/")

        for fw in (fw_root, fw_sar, fw_opt, fw_out):
            lv.addWidget(fw)

        for btn, attr in [(btn_root, "edit_root"), (btn_sar, "edit_sar"),
                          (btn_opt, "edit_opt"), (btn_out, "edit_out")]:
            edit = getattr(self, attr)
            btn.clicked.connect(lambda checked, e=edit: self._browse(e))

        lv.addWidget(section_label("Project metadata"))

        meta_grid = QWidget()
        mg = QGridLayout(meta_grid)
        mg.setContentsMargins(0, 0, 0, 0)
        mg.setSpacing(10)
        fw_dtype, self.edit_dtype = meta_field("Disaster type", "Earthquake")
        fw_date,  self.edit_date  = meta_field("Acquisition date", "2023-08-14")
        fw_sres,  self.edit_sres  = meta_field("SAR resolution (m)", "3.0")
        fw_ores,  self.edit_ores  = meta_field("Optical resolution (m)", "0.5")
        mg.addWidget(fw_dtype, 0, 0)
        mg.addWidget(fw_date,  0, 1)
        mg.addWidget(fw_sres,  1, 0)
        mg.addWidget(fw_ores,  1, 1)
        lv.addWidget(meta_grid)

        lv.addStretch()

        load_btn = QPushButton("LOAD PROJECT  →")
        load_btn.setObjectName("LoadBtn")
        load_btn.clicked.connect(self.project_loaded.emit)
        lv.addWidget(load_btn)

        root.addWidget(left)

        # ── Right welcome area ───────────────────────────────────────────────
        right = QWidget()
        rv = QVBoxLayout(right)
        rv.setContentsMargins(40, 40, 40, 40)
        rv.setSpacing(20)
        rv.setAlignment(Qt.AlignTop | Qt.AlignHCenter)

        # Welcome card
        card = QFrame()
        card.setObjectName("Panel")
        card.setStyleSheet(f"""
            QFrame#Panel {{
                background-color: {self.tokens['bg1']};
                border: 1px solid {self.tokens['border_strong']};
                border-radius: 10px;
            }}
        """)
        card.setMaximumWidth(500)
        cv = QVBoxLayout(card)
        cv.setContentsMargins(28, 24, 28, 24)
        cv.setSpacing(10)

        title_row = QHBoxLayout()
        t1 = QLabel("SAR")
        t1.setObjectName("LogoLabel")
        t1.setStyleSheet(f"font-size:22px; font-weight:700; font-family:'Syne','Segoe UI',sans-serif; color:{self.tokens['text_primary']};")
        t2 = QLabel("/")
        t2.setStyleSheet(f"font-size:22px; font-weight:700; font-family:'Syne','Segoe UI',sans-serif; color:{self.tokens['accent']};")
        t3 = QLabel("Annotate")
        t3.setStyleSheet(f"font-size:22px; font-weight:700; font-family:'Syne','Segoe UI',sans-serif; color:{self.tokens['text_primary']};")
        title_row.addWidget(t1); title_row.addWidget(t2); title_row.addWidget(t3)
        title_row.addStretch()
        cv.addLayout(title_row)

        desc = QLabel("Geospatial annotation for paired SAR and optical raster tiles. "
                       "Draw building bounding boxes, label damage levels, "
                       "and export georeferenced masks and GeoJSON polygons.")
        desc.setObjectName("SubLabel")
        desc.setWordWrap(True)
        cv.addWidget(desc)

        cv.addWidget(h_line(self.tokens))

        for num, text in [
            ("1", "Point the app to your SAR and optical tile folders"),
            ("2", "Fill in project-wide disaster and resolution metadata"),
            ("3", "Draw bounding boxes on synchronized SAR + optical viewers"),
            ("4", "Label each box with building status and damage level"),
            ("5", "Save tile — GeoTIFF masks and GeoJSON exported automatically"),
        ]:
            row = QHBoxLayout()
            num_lbl = QLabel(num)
            num_lbl.setFixedSize(20, 20)
            num_lbl.setAlignment(Qt.AlignCenter)
            num_lbl.setStyleSheet(
                f"background:{self.tokens['bg3']}; border:1px solid {self.tokens['border_strong']};"
                f"border-radius:10px; font-size:10px; color:{self.tokens['text_muted']};"
            )
            txt = QLabel(text)
            txt.setObjectName("SubLabel")
            txt.setWordWrap(True)
            row.addWidget(num_lbl, 0, Qt.AlignTop)
            row.addWidget(txt, 1)
            cv.addLayout(row)

        rv.addWidget(card, 0, Qt.AlignHCenter)

        # FS diagram
        fs = QFrame()
        fs.setStyleSheet(
            f"background:{self.tokens['bg2']}; border:1px solid {self.tokens['border']}; border-radius:10px;"
        )
        fs.setMaximumWidth(500)
        fv = QVBoxLayout(fs)
        fv.setContentsMargins(20, 16, 20, 16)
        fv.setSpacing(2)
        for txt, color in [
            ("📁  haiti_2023/", self.tokens["amber"]),
            ("    📂  sar_tiles/          →  tile_0042.tif …", self.tokens["text_muted"]),
            ("    📂  optical_tiles/      →  tile_0042.tif …", self.tokens["text_muted"]),
            ("    📂  Masks/              →  tile_0042_mask.tif", self.tokens["accent"]),
            ("    📂  Polygons/           →  tile_0042.geojson", self.tokens["accent"]),
        ]:
            l = QLabel(txt)
            l.setStyleSheet(f"color:{color}; font-size:11px; font-family:'DM Mono',monospace; background:transparent;")
            fv.addWidget(l)
        rv.addWidget(fs, 0, Qt.AlignHCenter)
        rv.addStretch()

        root.addWidget(right, 1)

    def _browse(self, edit: QLineEdit):
        path = QFileDialog.getExistingDirectory(self, "Select folder")
        if path:
            edit.setText(path)

    def update_tokens(self, tokens):
        self.tokens = tokens


class AnnotatePage(QWidget):
    go_metadata = Signal()
    go_skip = Signal()

    def __init__(self, tokens, parent=None):
        super().__init__(parent)
        self.tokens = tokens
        self._build()

    def _build(self):
        root = QVBoxLayout(self)
        root.setContentsMargins(0, 0, 0, 0)
        root.setSpacing(0)

        # ── Header ──────────────────────────────────────────────────────────
        header = QFrame()
        header.setObjectName("TopBar")
        hh = QHBoxLayout(header)
        hh.setContentsMargins(14, 0, 14, 0)
        hh.setSpacing(10)

        chip = QFrame()
        chip.setObjectName("TileChip")
        chip_l = QHBoxLayout(chip)
        chip_l.setContentsMargins(8, 4, 8, 4)
        chip_l.setSpacing(6)
        dot = QLabel("●")
        dot.setStyleSheet(f"color:{self.tokens['accent']}; font-size:8px; background:transparent;")
        tile_name = QLabel("tile_0042")
        tile_name.setStyleSheet(f"font-size:12px; font-weight:500; background:transparent; color:{self.tokens['text_primary']};")
        chip_l.addWidget(dot); chip_l.addWidget(tile_name)
        hh.addWidget(chip)

        subtitle = QLabel("Draw building bounding boxes")
        subtitle.setObjectName("SubLabel")
        hh.addWidget(subtitle)

        self.progress = QProgressBar()
        self.progress.setRange(0, 124)
        self.progress.setValue(42)
        self.progress.setFixedHeight(3)
        hh.addWidget(self.progress, 1)

        prog_lbl = QLabel("42 / 124")
        prog_lbl.setObjectName("SubLabel")
        hh.addWidget(prog_lbl)

        draw_btn = QPushButton("Draw")
        draw_btn.setObjectName("ModeChipDraw")
        sel_btn = QPushButton("Select")
        sel_btn.setObjectName("ModeChipSelect")
        fit_btn = QPushButton("Fit")
        skip_btn = QPushButton("Skip →")
        skip_btn.setObjectName("SkipBtn")
        next_btn = QPushButton("Metadata →")
        next_btn.setObjectName("NextBtn")
        next_btn.clicked.connect(self.go_metadata.emit)
        skip_btn.clicked.connect(self.go_skip.emit)

        for b in (draw_btn, sel_btn, fit_btn, skip_btn, next_btn):
            hh.addWidget(b)

        root.addWidget(header)

        # ── Body ─────────────────────────────────────────────────────────────
        body = QHBoxLayout()
        body.setContentsMargins(0, 0, 0, 0)
        body.setSpacing(0)

        # SAR viewer
        self.sar_viewer = RasterViewer("sar", self.tokens)
        body.addWidget(self.sar_viewer, 1)

        # Optical viewer
        self.opt_viewer = RasterViewer("optical", self.tokens)
        body.addWidget(self.opt_viewer, 1)

        # Sidebar
        sidebar = QFrame()
        sidebar.setObjectName("SidebarPanel")
        sidebar.setFixedWidth(220)
        sv = QVBoxLayout(sidebar)
        sv.setContentsMargins(0, 0, 0, 0)
        sv.setSpacing(0)

        # Project meta section
        sec1 = QWidget()
        s1v = QVBoxLayout(sec1)
        s1v.setContentsMargins(14, 12, 14, 12)
        s1v.setSpacing(6)
        s1v.addWidget(section_label("Project"))
        for key, val in [("Type", "Earthquake"), ("Date", "2023-08-14"),
                          ("SAR res", "3.0 m"), ("Opt res", "0.5 m")]:
            row = QHBoxLayout()
            k = QLabel(key); k.setObjectName("StatusItem")
            v = QLabel(val); v.setObjectName("StatusVal")
            row.addWidget(k); row.addStretch(); row.addWidget(v)
            s1v.addLayout(row)
        sv.addWidget(sec1)
        sv.addWidget(h_line(self.tokens))

        # Box list section
        sec2 = QWidget()
        s2v = QVBoxLayout(sec2)
        s2v.setContentsMargins(14, 12, 14, 12)
        s2v.setSpacing(6)
        s2v.addWidget(section_label("Boxes — 3"))

        boxes = [
            ("BLD-01", self.tokens["accent"],  "W 72.4°, N 18.7°", "OK",   "accent"),
            ("BLD-02", self.tokens["amber"],   "W 72.4°, N 18.7°", "Dmg",  "amber"),
            ("BLD-03", self.tokens["accent"],  "W 72.3°, N 18.6°", "—",    "muted"),
        ]
        for i, (name, col, coords, badge, badge_type) in enumerate(boxes):
            item = QFrame()
            item.setObjectName("BoxItem")
            if i == 0:
                item.setProperty("selected", "true")
            il = QHBoxLayout(item)
            il.setContentsMargins(8, 6, 8, 6)
            il.setSpacing(8)
            dot2 = QLabel("■")
            dot2.setStyleSheet(f"color:{col}; font-size:9px; background:transparent;")
            dot2.setFixedWidth(10)
            info = QVBoxLayout()
            nm = QLabel(name); nm.setStyleSheet(f"font-size:11px; background:transparent; color:{self.tokens['text_primary']};")
            co = QLabel(coords); co.setStyleSheet(f"font-size:10px; color:{self.tokens['text_muted']}; background:transparent;")
            info.addWidget(nm); info.addWidget(co)
            info.setSpacing(2)
            badge_colors = {
                "accent": (self.tokens["accent"], self.tokens["accent_dim"], self.tokens["accent_border"]),
                "amber":  (self.tokens["amber"],  self.tokens["amber_dim"],  self.tokens["amber_border"]),
                "muted":  (self.tokens["text_muted"], "transparent", self.tokens["border"]),
            }
            bc, bdim, bborder = badge_colors[badge_type]
            bdg = QLabel(badge)
            bdg.setStyleSheet(
                f"color:{bc}; background:{bdim}; border:1px solid {bborder};"
                f"border-radius:3px; font-size:10px; padding:1px 5px;"
            )
            il.addWidget(dot2)
            il.addLayout(info, 1)
            il.addWidget(bdg)
            s2v.addWidget(item)

        scroll = QScrollArea()
        scroll.setWidget(sec2)
        scroll.setWidgetResizable(True)
        scroll.setFrameShape(QFrame.NoFrame)
        sv.addWidget(scroll, 1)

        hint = QLabel("Click Draw mode then drag on either pane to create a new box. "
                       "Annotations are stored in world coordinates and mirrored automatically.")
        hint.setObjectName("HintNote")
        hint.setWordWrap(True)
        sv.addWidget(hint)

        body.addWidget(sidebar)

        root.addLayout(body, 1)

    def update_tokens(self, tokens):
        self.tokens = tokens
        self.sar_viewer.update_tokens(tokens)
        self.opt_viewer.update_tokens(tokens)


class MetadataPage(QWidget):
    go_back = Signal()
    go_save = Signal()
    go_skip = Signal()

    def __init__(self, tokens, parent=None):
        super().__init__(parent)
        self.tokens = tokens
        self._build()

    def _build(self):
        root = QHBoxLayout(self)
        root.setContentsMargins(0, 0, 0, 0)
        root.setSpacing(0)

        # ── SAR viewer ───────────────────────────────────────────────────────
        self.viewer = RasterViewer("sar", self.tokens)
        self.viewer.highlight_index = 0
        root.addWidget(self.viewer, 1)

        # ── Right panel ───────────────────────────────────────────────────────
        panel = QFrame()
        panel.setObjectName("RightPanel")
        pv = QVBoxLayout(panel)
        pv.setContentsMargins(0, 0, 0, 0)
        pv.setSpacing(0)

        # Header
        ph = QWidget()
        phv = QVBoxLayout(ph)
        phv.setContentsMargins(16, 14, 16, 14)
        phv.setSpacing(2)
        ht = QLabel("Metadata")
        ht.setStyleSheet(f"font-family:'Syne','Segoe UI',sans-serif; font-size:14px; font-weight:600; color:{self.tokens['text_primary']}; background:transparent;")
        hs = QLabel("Label each box before export")
        hs.setObjectName("SubLabel")
        phv.addWidget(ht); phv.addWidget(hs)
        pv.addWidget(ph)
        pv.addWidget(h_line(self.tokens))

        # Scrollable content
        content = QWidget()
        cv = QVBoxLayout(content)
        cv.setContentsMargins(0, 0, 0, 0)
        cv.setSpacing(0)

        def panel_section(inner_layout):
            sec = QWidget()
            sl = QVBoxLayout(sec)
            sl.setContentsMargins(16, 14, 16, 14)
            sl.setSpacing(8)
            sl.addLayout(inner_layout)
            return sec

        # Box selector section
        sel_layout = QVBoxLayout()
        sel_layout.setSpacing(6)
        sel_layout.addWidget(section_label("Select box"))
        sel_row = QHBoxLayout()
        sel_row.setSpacing(4)
        self.sel_btns = []
        for name in ("BLD-01", "BLD-02", "BLD-03"):
            b = QPushButton(name)
            b.setObjectName("SelBtn")
            sel_row.addWidget(b)
            self.sel_btns.append(b)
        self.sel_btns[0].setProperty("active", "true")
        sel_layout.addLayout(sel_row)
        sec_sel = panel_section(sel_layout)
        cv.addWidget(sec_sel)
        cv.addWidget(h_line(self.tokens))

        # Classification
        cls_layout = QVBoxLayout()
        cls_layout.setSpacing(6)
        cls_layout.addWidget(section_label("Classification"))
        status_cb = QComboBox()
        status_cb.addItems(["Standing (no damage)", "Possibly damaged", "Damaged", "Destroyed"])
        dmg_cb = QComboBox()
        dmg_cb.addItems(["Damage level 0 — none", "Damage level 1 — minor",
                          "Damage level 2 — moderate", "Damage level 3 — major",
                          "Damage level 4 — destroyed"])
        cls_layout.addWidget(status_cb)
        cls_layout.addWidget(dmg_cb)
        sec_cls = panel_section(cls_layout)
        cv.addWidget(sec_cls)
        cv.addWidget(h_line(self.tokens))

        # Geometry
        geo_layout = QVBoxLayout()
        geo_layout.setSpacing(8)
        geo_layout.addWidget(section_label("Box geometry"))
        coord_grid = QGridLayout()
        coord_grid.setSpacing(8)
        for i, (lbl_txt, val) in enumerate([("xmin", "-72.4318"), ("ymin", "18.6741"),
                                             ("xmax", "-72.4210"), ("ymax", "18.6823")]):
            cw = QWidget()
            cvl = QVBoxLayout(cw)
            cvl.setContentsMargins(0, 0, 0, 0)
            cvl.setSpacing(3)
            cl = QLabel(lbl_txt.upper())
            cl.setStyleSheet(f"font-size:10px; letter-spacing:1.5px; color:{self.tokens['text_muted']}; background:transparent;")
            cv2 = QLabel(val)
            cv2.setObjectName("CoordVal")
            cvl.addWidget(cl); cvl.addWidget(cv2)
            coord_grid.addWidget(cw, i // 2, i % 2)
        geo_layout.addLayout(coord_grid)
        sec_geo = panel_section(geo_layout)
        cv.addWidget(sec_geo)
        cv.addWidget(h_line(self.tokens))

        # Summary
        sum_layout = QVBoxLayout()
        sum_layout.setSpacing(6)
        sum_layout.addWidget(section_label("Export summary"))
        sb = QFrame()
        sb.setObjectName("SummaryBlock")
        sbv = QVBoxLayout(sb)
        sbv.setContentsMargins(12, 10, 12, 10)
        sbv.setSpacing(3)
        for row_txt in ["Tile      tile_0042.tif",
                         "Boxes   3 annotations",
                         "Output  Masks/ + Polygons/",
                         "Bands   binary · status · damage"]:
            rl = QLabel(row_txt)
            rl.setStyleSheet(f"font-size:11px; color:{self.tokens['text_secondary']}; background:transparent; font-family:'DM Mono',monospace;")
            sbv.addWidget(rl)
        sum_layout.addWidget(sb)
        sec_sum = panel_section(sum_layout)
        cv.addWidget(sec_sum)
        cv.addStretch()

        scroll = QScrollArea()
        scroll.setWidget(content)
        scroll.setWidgetResizable(True)
        scroll.setFrameShape(QFrame.NoFrame)
        pv.addWidget(scroll, 1)

        # Footer actions
        footer = QWidget()
        fv = QVBoxLayout(footer)
        fv.setContentsMargins(16, 12, 16, 12)
        fv.setSpacing(8)
        save_btn = QPushButton("Save tile & next tile  →")
        save_btn.setObjectName("SaveBtn")
        back_btn = QPushButton("←  Back to annotation")
        back_btn.setObjectName("BackBtn")
        skip_btn = QPushButton("Skip tile")
        skip_btn.setObjectName("Skip2Btn")
        save_btn.clicked.connect(self.go_save.emit)
        back_btn.clicked.connect(self.go_back.emit)
        skip_btn.clicked.connect(self.go_skip.emit)
        fv.addWidget(save_btn)
        fv.addWidget(back_btn)
        fv.addWidget(skip_btn)
        pv.addWidget(h_line(self.tokens))
        pv.addWidget(footer)

        root.addWidget(panel)

    def update_tokens(self, tokens):
        self.tokens = tokens
        self.viewer.update_tokens(tokens)


# ---------------------------------------------------------------------------
# Main Window
# ---------------------------------------------------------------------------

class MainWindow(QMainWindow):
    def __init__(self):
        super().__init__()
        self.setWindowTitle("SAR/Annotate Desktop")
        self.resize(1280, 800)
        self.is_dark = True
        self.tokens = DARK

        central = QWidget()
        self.setCentralWidget(central)
        root = QVBoxLayout(central)
        root.setContentsMargins(0, 0, 0, 0)
        root.setSpacing(0)

        # ── Top bar ──────────────────────────────────────────────────────────
        topbar = QFrame()
        topbar.setObjectName("TopBar")
        topbar.setFixedHeight(44)
        tbl = QHBoxLayout(topbar)
        tbl.setContentsMargins(16, 0, 16, 0)
        tbl.setSpacing(10)

        logo1 = QLabel("SAR")
        logo1.setObjectName("LogoLabel")
        logo2 = QLabel("/")
        logo2.setObjectName("LogoAccent")
        logo3 = QLabel("Annotate")
        logo3.setObjectName("LogoLabel")
        tbl.addWidget(logo1); tbl.addWidget(logo2); tbl.addWidget(logo3)
        tbl.addStretch()

        self.tab_btns = []
        for i, name in enumerate(["01  Setup", "02  Annotate", "03  Metadata"]):
            btn = QPushButton(name)
            btn.setObjectName("TabBtn")
            btn.setProperty("active", "false")
            btn.clicked.connect(lambda checked, idx=i: self._switch_page(idx))
            tbl.addWidget(btn)
            self.tab_btns.append(btn)

        tbl.addSpacing(10)

        self.mode_btn = QPushButton("☾  dark")
        self.mode_btn.setObjectName("ModeToggle")
        self.mode_btn.clicked.connect(self._toggle_mode)
        tbl.addWidget(self.mode_btn)

        root.addWidget(topbar)

        # ── Pages ─────────────────────────────────────────────────────────────
        self.stack = QStackedWidget()
        self.setup_page    = SetupPage(self.tokens)
        self.annotate_page = AnnotatePage(self.tokens)
        self.metadata_page = MetadataPage(self.tokens)

        self.setup_page.project_loaded.connect(lambda: self._switch_page(1))
        self.annotate_page.go_metadata.connect(lambda: self._switch_page(2))
        self.annotate_page.go_skip.connect(lambda: self._switch_page(0))
        self.metadata_page.go_back.connect(lambda: self._switch_page(1))
        self.metadata_page.go_save.connect(lambda: self._switch_page(0))
        self.metadata_page.go_skip.connect(lambda: self._switch_page(0))

        self.stack.addWidget(self.setup_page)
        self.stack.addWidget(self.annotate_page)
        self.stack.addWidget(self.metadata_page)
        root.addWidget(self.stack, 1)

        # ── Status bar ────────────────────────────────────────────────────────
        statusbar = QFrame()
        statusbar.setObjectName("StatusBar")
        statusbar.setFixedHeight(28)
        sbl = QHBoxLayout(statusbar)
        sbl.setContentsMargins(14, 0, 14, 0)
        sbl.setSpacing(12)

        dot_lbl = QLabel("●")
        dot_lbl.setStyleSheet(f"color:{self.tokens['accent']}; font-size:7px; background:transparent;")
        sbl.addWidget(dot_lbl)

        self._sb_widgets = {}
        for key, lbl_text, val in [
            ("tile",  "Tile",  "tile_0042"),
            ("idx",   "Index", "042 / 124"),
            ("phase", "Phase", "Setup"),
            ("boxes", "Boxes", "3"),
        ]:
            kl = QLabel(lbl_text)
            kl.setObjectName("StatusItem")
            vl = QLabel(val)
            vl.setObjectName("StatusVal")
            sbl.addWidget(kl)
            sbl.addWidget(vl)
            self._sb_widgets[key] = vl

            sep = QFrame()
            sep.setFrameShape(QFrame.VLine)
            sep.setFixedHeight(12)
            sep.setStyleSheet(f"background:{self.tokens['border_strong']}; border:none;")
            sbl.addWidget(sep)

        sbl.addStretch()
        root.addWidget(statusbar)

        # Initial state
        self._switch_page(0)
        self._apply_style()

    def _switch_page(self, idx: int):
        self.stack.setCurrentIndex(idx)
        phases = ["Setup", "Annotation", "Metadata"]
        self._sb_widgets["phase"].setText(phases[idx])
        for i, btn in enumerate(self.tab_btns):
            btn.setProperty("active", "true" if i == idx else "false")
            btn.style().unpolish(btn)
            btn.style().polish(btn)

    def _toggle_mode(self):
        self.is_dark = not self.is_dark
        self.tokens = DARK if self.is_dark else LIGHT
        if self.is_dark:
            self.mode_btn.setText("☾  dark")
        else:
            self.mode_btn.setText("☀  light")
        self._apply_style()

    def _apply_style(self):
        self.setStyleSheet(stylesheet(self.tokens))
        # Force re-polish active tab buttons
        for btn in self.tab_btns:
            btn.style().unpolish(btn)
            btn.style().polish(btn)
        # Update raster viewers
        self.annotate_page.sar_viewer.tokens = self.tokens
        self.annotate_page.opt_viewer.tokens = self.tokens
        self.annotate_page.sar_viewer.update()
        self.annotate_page.opt_viewer.update()
        self.metadata_page.viewer.tokens = self.tokens
        self.metadata_page.viewer.update()


# ---------------------------------------------------------------------------
# Entry point
# ---------------------------------------------------------------------------

def main():
    app = QApplication(sys.argv)
    app.setApplicationName("SAR/Annotate Desktop")

    # Try to load DM Mono / Syne from system; graceful fallback to monospace
    QFontDatabase.addApplicationFont("DMMono-Regular.ttf")
    QFontDatabase.addApplicationFont("Syne-Bold.ttf")

    win = MainWindow()
    win.show()
    sys.exit(app.exec())


if __name__ == "__main__":
    main()
