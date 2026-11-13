import os
import certifi
import json
import math
from chem import pKa_values
from chem import pKb_values
import threading
import quantity
import chem
import biotek
import io
import base64
from matplotlib.figure import Figure
import utils
import ctypes
import sys
import traceback
from datetime import datetime
from dataclasses import dataclass, field
from pathlib import Path
from PySide6.QtWidgets import (
    QApplication,
    QMainWindow,
    QLabel,
    QWidget,
    QGridLayout,
    QPushButton,
    QLineEdit,
    QListWidget,
    QToolBar,
    QToolButton,
    QMenu,
    QHBoxLayout,
    QVBoxLayout,
    QSizePolicy,
    QStackedWidget,
    QListWidgetItem,
    QGraphicsView,
    QGraphicsScene,
    QGraphicsEllipseItem,
    QGraphicsRectItem,
    QDialog,
    QMessageBox,
    QScrollArea,
    QColorDialog,
    QFrame,
    QTextEdit,
    QButtonGroup,
    QCompleter,
    QComboBox,
    QAbstractButton,
    QFileDialog,
    QTabBar,
)
from PySide6.QtCore import (
    Qt,
    QSize,
    QMimeData,
    QRectF,
    Signal,
    QSettings,
    QObject,
    Slot,
    Signal,
    QUrl,
    QPropertyAnimation,
    QEasingCurve,
    QPoint,
    QParallelAnimationGroup,
    QEvent,
    QTimer,
    QEventLoop,
)
from PySide6.QtWebEngineWidgets import QWebEngineView
from PySide6.QtWebChannel import QWebChannel
from PySide6.QtSvgWidgets import QSvgWidget
from PySide6.QtSvg import QSvgRenderer
from PySide6.QtNetwork import QNetworkAccessManager, QNetworkRequest, QNetworkReply

from PySide6.QtGui import (
    QIcon,
    QPixmap,
    QTextCursor,
    QDrag,
    QPainter,
    QBrush,
    QPen,
    QPalette,
    QColor,
    QTransform,
    QCursor,
    QShortcut,
    QKeySequence,
    QIntValidator,
)
import re
import interpreter
import chem
from mat import Vector
from matplotlib.backends.backend_qtagg import FigureCanvasQTAgg
import biotek
import license_manager
import sympy
import multiprocessing

from path import resource_path


os.environ.setdefault("SSL_CERT_FILE", certifi.where())
os.environ.setdefault("REQUESTS_CA_BUNDLE", certifi.where())
os.environ["QTWEBENGINE_CHROMIUM_FLAGS"] = "--log-level=3 --renderer-process-limit=4"

version = "Bv 2.0"

CHANGELOG_URL = "https://raw.githubusercontent.com/MaxCortes1507/Carbon-change-logs/main/Change-log-BV2.md"
PUBCHEM_URL = "https://pubchem.ncbi.nlm.nih.gov/rest/pug/compound"

ASSETS_DIR = resource_path("Assets")

def hover_icon(file):
    icon = QIcon(str(ASSETS_DIR / file))
    hover = ASSETS_DIR / file.replace(".svg", "_Hover.svg")
    if hover.exists():
        icon.addFile(str(hover), QSize(), QIcon.Active)
    return icon

def nav_icon(mirror):
    icon = QIcon()
    for file, mode in (("Pointer.svg", QIcon.Normal), ("Pointer_Disabled.svg", QIcon.Disabled)):
        pixmap = QIcon(str(ASSETS_DIR / file)).pixmap(10,10)
        if mirror:
            pixmap = pixmap.transformed(QTransform().scale(-1,1))
        icon.addPixmap(pixmap, mode)
    return icon

def point_cursor(root):
    for widget in root.findChildren(QAbstractButton) + root.findChildren(QComboBox):
        if not widget.testAttribute(Qt.WA_SetCursor):
            widget.setCursor(Qt.PointingHandCursor)


_settings = QSettings("M&B", "Carbon")

HEADER = "#1e1e1e"
BG = "#404040"
SIDEBAR = "#575757"
BUTTON = "#ffffff"
HOVER = "#cccccc"
TEXT = "#000000"
SCROLL = "#323232"

LINE_HEIGHT = 36
BOX_HEIGHT = 120
SIDEBAR_WIDTH = 220

GWL_STYLE = -16
WS_FRAME_STYLES = 0x00C00000 | 0x00040000 | 0x00020000 | 0x00010000
SWP_FRAMECHANGED = 0x0001 | 0x0002 | 0x0004 | 0x0020
WM_NCCALCSIZE = 0x0083
WM_NCHITTEST = 0x0084
HTCLIENT = 1
HTCAPTION = 2
HIT_TEST = {
    (True, False, False, False): 10, (False, True, False, False): 11,
    (False, False, True, False): 12, (True, False, True, False): 13, (False, True, True, False): 14,
    (False, False, False, True): 15, (True, False, False, True): 16, (False, True, False, True): 17,
}

class MSG(ctypes.Structure):
    _fields_ = [("hwnd", ctypes.c_void_p), ("message", ctypes.c_uint), ("wParam", ctypes.c_size_t), ("lParam", ctypes.c_ssize_t)]

class RECT(ctypes.Structure):
    _fields_ = [("left", ctypes.c_long), ("top", ctypes.c_long), ("right", ctypes.c_long), ("bottom", ctypes.c_long)]

class MONITORINFO(ctypes.Structure):
    _fields_ = [("cbSize", ctypes.c_ulong), ("rcMonitor", RECT), ("rcWork", RECT), ("dwFlags", ctypes.c_ulong)]

if sys.platform == "win32":
    user32 = ctypes.windll.user32
    user32.GetWindowLongPtrW.restype = ctypes.c_ssize_t
    user32.GetWindowLongPtrW.argtypes = [ctypes.c_void_p, ctypes.c_int]
    user32.SetWindowLongPtrW.argtypes = [ctypes.c_void_p, ctypes.c_int, ctypes.c_ssize_t]
    user32.SetWindowPos.argtypes = [ctypes.c_void_p, ctypes.c_void_p, ctypes.c_int, ctypes.c_int, ctypes.c_int, ctypes.c_int, ctypes.c_uint]
    user32.IsZoomed.argtypes = [ctypes.c_void_p]
    user32.MonitorFromWindow.restype = ctypes.c_void_p
    user32.MonitorFromWindow.argtypes = [ctypes.c_void_p, ctypes.c_uint]
    user32.GetMonitorInfoW.argtypes = [ctypes.c_void_p, ctypes.c_void_p]

button_style =  f"""
        QPushButton {{
            background-color: {BUTTON};
            color: {TEXT};
            border: 1px solid {HEADER};
            border-radius: 8px;
            padding: 6px;
        }}
        QPushButton:hover {{ background-color: {HOVER}; }}
    """

calc_button_style = f"""
        QPushButton {{
            background-color: {SCROLL};
            color: {BUTTON};
            border: none;
            font-weight: bold;
            border-radius: 8px;
            padding: 6px;
        }}
        QPushButton:hover {{ background-color: {BG}; }}
    """

SUB_HELP = (
    "\nFor at skrive sænket skrift er det Shift+Bindestreg."
    "\nFor at skrive hævet skrift er det Shift+^."
    )

HELPTEXT = {
    "unit": (
        "Indtast din originale værdi med dens enhed i det øverste input, brug . for decimaltal.\n"
        "Husk at skrive dens enhed inde i de firkantede parenteser [] for eksempel 10[km/t].\n"
        "Derefter indtast den ønskede enhed uden firkantede parenteser."
    ),
    "analysis": (
        "Indtast molekylet i inputfeltet.\n"
        "Husk at grundstoffer med navne der er længere end et bogstav kun har det første bogstav stort.\n"
        "Eksempelvis Fe3O4, jernoxid.\n"
        "DBE-formel kan kun anvendes til organiske molekyler."
    ),
    "bjerrum": (
        "Indtast pKs-værdi for at opstille et bjerrumdiagram.\n"
        "Brug . for at skrive decimaler og brug , for at lave endnu et diagram.\n"
        "For eksempel 5.3, 4.1 laver to bjerrumdiagrammer."
    ),
    "pH": (
        "Indtast enten pKs-værdi eller pKb-værdi samt koncentrationen.\n"
        "Husk . for decimaltal og angiv koncentrationens enhed i firkantede parenteser [].\n"
        "Du kan også bruge navnet for nogle syrer og baser (se Indstillinger).\n"
        "Standardenhed for koncentration er mol/l."
    ),
    "balance": (
        "Indtast din ubalancerede reaktion i inputfeltet.\n"
        "Brug pil mellem reaktanter og produkter ->.\n"
        "For eksempel H2O -> H2 + O2.\n"
        "Ved redoxreaktioner bruges opløsningsboksen hvor der skrives syre eller base."
    ),
    "udbytteprocent": (
        "Indtast praktisk udbytte i det første input og teoretisk udbytte i det andet.\n"
        "Husk . for decimal og enheder inde i firkantet parentes [].\n"
        "Eksempelvis 4[kg] 300[g]. Standardenheden er kg."
    ),
    "volumenprocent": (
        "Indtast samlet volumen i det første input og specifik volumen i det andet.\n"
        "Eksempelvis 4[l] 300[dl]. Standardenheden er l."
    ),
    "masseprocent": (
        "Indtast samlet masse i det første input og specifik masse i det andet.\n"
        "Eksempelvis 4[kg] 300[g]. Standardenheden er kg."
    ),
    "mængdeberegning": (
        "Indtast din tilgængelige data i deres respektive input.\n"
        "Den beregner alt den mulige data fra det givne input, så du behøver ikke fylde alle inputs.\n"
        "Standard: masse g, volumen l, stofmængde mol, koncentration mol/l, molarmasse g/mol, densitet kg/l."
    ),
    "puffer": (
        "Input stofmængden eller koncentrationen af syren og af basen samt syrens pKs.\n"
        "Standardenheden for stofmængde er mol, for koncentration mol/l."
    ),
    "h3o": "Input enten pH eller pOH.\nHusk . for decimaler.",
    "dna_mut": (
        "Indtast den raske DNA-streng øverst og derefter den muterede.\n"
        "Mellemrum og store/små bogstaver er ligegyldige.\nFor eksempel AAT gcc TTG."
    ),
    "rna_mut": (
        "Indtast den raske RNA-streng øverst og derefter den muterede.\n"
        "Mellemrum og store/små bogstaver er ligegyldige.\nFor eksempel AAU gcc UUG."
    ),
    "dna_peptid": (
        "Indtast DNA-streng.\n"
        "Mellemrum og store/små bogstaver er ligegyldige.\n"
        "For eksempel AAT gcc TTG eller AATGCCTTT."
    ),
    "rna_peptid": (
            "Indtast RNA-streng.\n"
            "Mellemrum og store/små bogstaver er ligegyldige.\n"
            "For eksempel AAU gcc UUG eller AAUGCCUUU."
        ),
}

def load_dict_from_settings(key, target):
    try:
        data = json.loads(_settings.value(key) or "null")
    except (TypeError, ValueError):
        return
    if isinstance(data, dict):
        target.clear()
        target.update(data)

PK_DEFAULTS = {"pKa_values": dict(pKa_values), "pKb_values": dict(pKb_values)}

def register_crbn():
    import winreg
    exe = sys.executable
    for key, value in [
        (r"Software\Classes\.crbn", "Carbon.Regneark"),
        (r"Software\Classes\Carbon.Regneark", "Carbon regneark"),
        (r"Software\Classes\Carbon.Regneark\DefaultIcon", f'"{exe}",0'),
        (r"Software\Classes\Carbon.Regneark\shell\open\command", f'"{exe}" "%1"'),
    ]:
        winreg.SetValue(winreg.HKEY_CURRENT_USER, key, winreg.REG_SZ, value)
    ctypes.windll.shell32.SHChangeNotify(0x08000000, 0, None, None)


def category_page(title, categories):
    content = QWidget()
    layout = QVBoxLayout(content)
    layout.setContentsMargins(30,20,30,20)
    layout.setSpacing(20)

    for heading, rows in categories:
        category = QVBoxLayout()
        category.setSpacing(8)

        heading_label = QLabel(heading)
        heading_label.setStyleSheet(f"color: {BUTTON}; font-size: 28px; background: transparent;")
        category.addWidget(heading_label)

        card = QFrame()
        card.setObjectName("card")
        card.setStyleSheet(f"QFrame#card {{ background-color: {SIDEBAR}; border-radius: 12px; }}")
        card_layout = QVBoxLayout(card)
        card_layout.setContentsMargins(12,12,12,12)
        card_layout.setSpacing(12)
        for i, (text, widget) in enumerate(rows):
            if i > 0:
                line = QFrame()
                line.setFixedHeight(1)
                line.setStyleSheet(f"background-color: {BUTTON};")
                card_layout.addWidget(line)
            row = QHBoxLayout()
            label = QLabel(text)
            label.setStyleSheet(f"color: {BUTTON}; font-size: 16px; background: transparent;")
            row.addWidget(label, alignment=Qt.AlignTop)
            row.addStretch()
            row.addWidget(widget)
            card_layout.addLayout(row)
        category.addWidget(card)

        layout.addLayout(category)
    layout.addStretch()

    page = QScrollArea()
    page.setWidgetResizable(True)
    page.setFrameShape(QFrame.NoFrame)
    page.setStyleSheet(f"""
        QScrollBar:vertical {{
            background: {BG};
            width: 14px;
            border-radius: 5px;
            margin: 8px 4px 8px 0px;
        }}
        QScrollBar::handle:vertical {{
            background: {SCROLL};
            border-radius: 5px;
            min-height: 30px;
        }}
        QScrollBar::add-line:vertical, QScrollBar::sub-line:vertical {{ height: 0; }}
        QScrollBar::add-page:vertical, QScrollBar::sub-page:vertical {{ background: none; }}
    """)
    page.setWidget(content)
    page.setWindowTitle(title)
    return page

def toggle_switch(settings_key):
    btn = QPushButton()
    btn.setCheckable(True)
    btn.setFixedSize(90, 26)

    knob = QLabel(btn)
    knob.setFixedSize(50, 26)
    knob.setAlignment(Qt.AlignCenter)
    knob.setAttribute(Qt.WA_Hover)

    anim = QPropertyAnimation(knob, b"pos", btn)
    anim.setDuration(200)
    anim.setEasingCurve(QEasingCurve.OutCubic)

    def style(on):
        knob.setText("Til" if on else "Fra")
        btn.setStyleSheet(f"QPushButton {{ background-color: {BUTTON if on else SCROLL}; border: none; border-radius: 13px; }}")
        knob.setStyleSheet(f"""
            QLabel {{ background-color: {SCROLL if on else BUTTON}; color: {BUTTON if on else TEXT}; border-radius: 13px; font-weight: bold; }}
            QLabel:hover {{ background-color: {BG if on else HOVER}; }}
        """)

    def update(on):
        style(on)
        _settings.setValue(settings_key, on)
        anim.stop()
        anim.setEndValue(QPoint(40 if on else 0, 0))
        anim.start()

    btn.toggled.connect(update)
    on = _settings.value(settings_key, True, type=bool)
    btn.setChecked(on)
    style(on)
    knob.move(40 if on else 0, 0)
    return btn

def pk_table(data_dict, key_placeholder, value_placeholder, settings_key):
    container = QWidget()
    container.setStyleSheet("background: transparent;")
    container.setFixedWidth(240)
    layout = QVBoxLayout(container)
    layout.setContentsMargins(0,0,0,0)
    layout.setSpacing(6)

    list_widget = QListWidget()
    list_widget.setFixedHeight(140)
    list_widget.setSelectionMode(QListWidget.NoSelection)
    list_widget.setStyleSheet(f"""
        QListWidget {{ background-color: {BUTTON}; color: {TEXT}; border: none; border-radius: 12px; }}
        QScrollBar:vertical {{ background: {BUTTON}; }}
    """)
    layout.addWidget(list_widget)

    line_style = f"QLineEdit {{ background-color: {BUTTON}; color: {TEXT}; border: none; border-radius: 8px; padding: 4px 8px; }}"
    name_input = QLineEdit()
    name_input.setPlaceholderText(key_placeholder)
    name_input.setStyleSheet(line_style)
    value_input = QLineEdit()
    value_input.setPlaceholderText(value_placeholder)
    value_input.setFixedWidth(60)
    value_input.setStyleSheet(line_style)
    add_btn = QPushButton("+")
    add_btn.setFixedSize(28, 28)
    add_btn.setStyleSheet(button_style)

    def save():
        _settings.setValue(settings_key, json.dumps(data_dict))

    items = {}

    def insert_row(name, value):
        index = sum(1 for n in items if n.lower() < name.lower())
        row = QWidget()
        row.setStyleSheet("background: transparent;")
        row_layout = QHBoxLayout(row)
        row_layout.setContentsMargins(6,2,6,2)
        label = QLabel(f"{name}: {value}")
        label.setStyleSheet(f"color: {TEXT}; background: transparent;")
        row_layout.addWidget(label)
        row_layout.addStretch()
        del_btn = QPushButton("x")
        del_btn.setFixedSize(20,20)
        del_btn.setStyleSheet(f"""
            QPushButton {{ background: transparent; border: none; color: {TEXT}; font-weight: bold; }}
            QPushButton:hover {{ color: #da373c; }}
        """)
        del_btn.clicked.connect(lambda _=False, n=name: remove(n))
        row_layout.addWidget(del_btn)
        item = QListWidgetItem()
        item.setSizeHint(QSize(200, 26))
        list_widget.insertItem(index, item)
        list_widget.setItemWidget(item, row)
        items[name] = item

    def remove_row(name):
        item = items.pop(name, None)
        if item:
            list_widget.takeItem(list_widget.row(item))

    def refresh():
        list_widget.clear()
        items.clear()
        for name, value in data_dict.items():
            insert_row(name, value)

    def remove(name):
        del data_dict[name]
        save()
        remove_row(name)

    def add():
        name = name_input.text().strip()
        try:
            value = float(value_input.text().strip().replace(",", "."))
        except ValueError:
            return
        if not name or not math.isfinite(value):
            return
        for key in [k for k in data_dict if k.lower() == name.lower()]:
            del data_dict[key]
            remove_row(key)
        data_dict[name] = value
        save()
        name_input.clear()
        value_input.clear()
        insert_row(name, value)

    add_btn.clicked.connect(add)
    name_input.returnPressed.connect(add)
    value_input.returnPressed.connect(add)

    add_row = QHBoxLayout()
    add_row.addWidget(name_input)
    add_row.addWidget(value_input)
    add_row.addWidget(add_btn)
    layout.addLayout(add_row)

    def reset():
        if not container.window().ask_close("Nulstil tabel", "Er du sikker?\nDine egne værdier bliver slettet.", "Nulstil"):
            return
        data_dict.clear()
        data_dict.update(PK_DEFAULTS[settings_key])
        _settings.remove(settings_key)
        refresh()

    reset_btn = QPushButton("Nulstil")
    reset_btn.setStyleSheet(button_style)
    reset_btn.clicked.connect(reset)
    layout.addWidget(reset_btn)

    refresh()
    return container

GREEK = {
    "alpha": "α", "beta": "β", "gamma": "γ", "delta": "δ", "epsilon": "ε", "zeta": "ζ", "eta": "η", "theta": "θ",
    "iota": "ι", "kappa": "κ", "lambda": "λ", "mu": "µ", "nu": "ν", "xi": "ξ", "pi": "π", "rho": "ρ",
    "sigma": "σ", "tau": "τ", "upsilon": "υ", "phi": "φ", "chi": "χ", "psi": "ψ", "omega": "ω",
    "Gamma": "Γ", "Delta": "Δ", "Theta": "Θ", "Lambda": "Λ", "Xi": "Ξ", "Pi": "Π", "Sigma": "Σ",
    "Upsilon": "Υ", "Phi": "Φ", "Psi": "Ψ", "Omega": "Ω",
}

ELEMENT_NAMES = """Brint Helium Lithium Beryllium Bor Carbon Kvælstof Ilt Fluor Neon Natrium Magnesium Aluminium Silicium Fosfor
Svovl Klor Argon Kalium Calcium Scandium Titan Vanadium Krom Mangan Jern Kobolt Nikkel Kobber Zink Gallium Germanium Arsen Selen
Brom Krypton Rubidium Strontium Yttrium Zirconium Niobium Molybdæn Technetium Ruthenium Rhodium Palladium Sølv Cadmium Indium Tin
Antimon Tellur Jod Xenon Cæsium Barium Lanthan Cerium Praseodym Neodym Promethium Samarium Europium Gadolinium Terbium Dysprosium
Holmium Erbium Thulium Ytterbium Lutetium Hafnium Tantal Wolfram Rhenium Osmium Iridium Platin Guld Kviksølv Thallium Bly Bismuth
Polonium Astat Radon Francium Radium Actinium Thorium Protactinium Uran Neptunium Plutonium Americium Curium Berkelium Californium
Einsteinium Fermium Mendelevium Nobelium Lawrencium Rutherfordium Dubnium Seaborgium Bohrium Hassium Meitnerium Darmstadtium
Røntgenium Copernicium Nihonium Flerovium Moscovium Livermorium Tennessin Oganesson""".split()

ELEMENT_SERIES = {
    1: ("Andre ikkemetaller", "#a8d5a2"), 2: ("Ædelgas", "#c3b1e1"), 3: ("Alkalimetal", "#f4a6a6"),
    4: ("Jordalkalimetal", "#f6c89f"), 5: ("Halvmetal", "#9fd3c7"), 6: ("Halogen", "#f7e39c"),
    7: ("Andre metaller", "#c9c9c9"), 8: ("Overgangsmetal", "#a9c8f0"), 9: ("Lanthanid", "#e5b3d6"),
    10: ("Actinid", "#e0b8a0"),
}

def element_mass(e):
    if e.is_radioactive and e.atomic_number not in (90, 91, 92):
        return f"({e.atomic_weight:.0f})"
    return f"{e.atomic_weight:.5g}".replace(".", ",")

def electron_shells(e):
    from mendeleev.econf import ElectronicConfiguration
    return list(ElectronicConfiguration(e.electronic_configuration).electrons_per_shell().values())

class VerticalLabel(QWidget):
    def __init__(self, text, color):
        super().__init__()
        self.text, self.color = text, color
        self.setFixedWidth(24)
        self.setMinimumHeight(self.fontMetrics().horizontalAdvance(text) + 12)

    def paintEvent(self, event):
        painter = QPainter(self)
        painter.setRenderHint(QPainter.Antialiasing)
        painter.setPen(Qt.NoPen)
        painter.setBrush(QColor(self.color))
        painter.drawRoundedRect(self.rect(), 3, 3)
        painter.setPen(QColor(TEXT))
        painter.rotate(90)
        painter.drawText(QRectF(6, -self.width(), self.height() - 12, self.width()), Qt.AlignLeft | Qt.AlignVCenter, self.text)

class FitView(QGraphicsView):
    def resizeEvent(self, event):
        super().resizeEvent(event)
        self.fitInView(self.sceneRect(), Qt.KeepAspectRatio)

CALCULUS = re.compile(r"\\(int|sum|lim)(?![A-Za-z])|\\frac\{\\differentialD\}")
INTEGRAL_PARTS = re.compile(r"\\frac\{\\differentialD\}\{\\differentialD|\\int(?![A-Za-z])|\\differentialD")


def latex_group(s, i):
    while s[i] == " ":
        i += 1
    if s[i] != "{":
        m = re.compile(r"\\[A-Za-z]+|.").match(s, i)
        return m.group(), m.end()
    depth = 0
    for j in range(i, len(s)):
        depth += {"{": 1, "}": -1}.get(s[j], 0)
        if depth == 0:
            return s[i + 1:j], j + 1
    raise ValueError

def calculus_operand(s, i):
    while i < len(s) and s[i] == " ":
        i += 1
    if i < len(s) and s[i] == "(":
        depth = 0
        for j in range(i, len(s)):
            depth += {"(": 1, ")": -1}.get(s[j], 0)
            if depth == 0:
                return s[i + 1:j], j + 1
    return s[i:], len(s)

def calculus_call(s, i, kind):
    scripts = {}
    while i < len(s) and s[i] in "_^":
        scripts[s[i]], i = latex_group(s, i + 1)
    scripts = {k: Latex_to_calc(v) for k, v in scripts.items()}

    if kind == "int":
        depth = 1
        for part in INTEGRAL_PARTS.finditer(s, i):
            depth += {r"\int": 1, r"\differentialD": -1}.get(part.group(), 0)
            if depth == 0:
                break
        else:
            raise ValueError
        body = Latex_to_calc(s[i:part.start()])
        var, end = latex_group(s, part.end())
        var = Latex_to_calc(var)
        if scripts:
            return f"integrate({body}, ({var}, {scripts['_']}, {scripts['^']}))", end
        return f"integrate({body}, {var})", end

    if kind is None:
        var, i = latex_group(s, i)
        var = Latex_to_calc(var.removeprefix(r"\differentialD"))
        body, end = calculus_operand(s, i)
        return f"diff({Latex_to_calc(body)}, {var})", end

    body, end = calculus_operand(s, i)
    if kind == "sum":
        k, a = scripts["_"].split("=", 1)
        return f"summation({Latex_to_calc(body)}, ({k}, {a}, {scripts['^']}))", end
    x, a = scripts["_"].split("->", 1)
    return f"limit({Latex_to_calc(body)}, {x}, {a})", end


def calculus_to_calc(s):
    m = CALCULUS.search(s)
    if not m:
        return s
    try:
        call, end = calculus_call(s, m.end(), m.group(1))
    except (IndexError, KeyError, ValueError):
        return s
    return s[:m.start()] + call + calculus_to_calc(s[end:])

def Latex_to_calc(s: str) -> str:
    s = s.replace(r"\placeholder{}", "")
    s = s.replace(r"\_", "\x00")  # a typed underscore, not a subscript
    s = re.sub(r"\\rightleftharpoons(?![A-Za-z])\s*", "<->", s)
    s = re.sub(r"\\(to|rightarrow|longrightarrow)(?![A-Za-z])\s*", "->", s)
    s = s.replace(r"\left", "").replace(r"\right", "")
    s = re.sub(r"\\angle(?![A-Za-z])\s*", "VinkelVektor", s)
    s = re.sub(r"\\vec\{\\mathnormal\{e\}\}_\{\\vec\{([^{}]*)\}\}", r"EnhedsVektor(\\vec{\1})", s)
    s = re.sub(r"\\[lr]?vert(?![A-Za-z])", "|", s)
    s = re.sub(r"\|([^|]*)\|", r"Abs(\1)", s)
    s = s.replace(r"\lbrack", "[").replace(r"\rbrack", "]")
    s = s.replace(r"\lbrace", "\x01").replace(r"\rbrace", "\x02")
    s = s.replace(r"\{", "\x01").replace(r"\}", "\x02")
    s = s.replace(r"\cdot", "*").replace(r"\times", "×")
    s = s.replace(r"\#", "#")
    
    s = re.sub(r"\\(ln|log|exp)(?![A-Za-z])", r"\1", s)
    s = re.sub(r"\^\{\\prime\}", "'", s)
    s = re.sub(r"\\[,;:! ]", " ", s)
    s = re.sub(r"\\mu\s*", "µ", s)
    s = re.sub(r"\\(" + "|".join(GREEK) + r")(?![A-Za-z])", lambda m: GREEK[m.group(1)], s)
    s = s.replace(r"\%", "%")
    s = s.replace(r"\infty", "oo")
    s = calculus_to_calc(s)

    prev = None

    while prev != s:
        prev = s
        s = re.sub(r"\\textcolor\{[^{}]*\}\{([^{}]*)\}", r"\1", s)
        s = re.sub(r"\\(?:mathrm|mathbf|text|operatorname)\{([^{}]*)\}", r"\1", s)
        s = re.sub(r"\\(?:vec|overrightarrow)\{([^{}]*)\}", lambda m: m.group(1) + "\x00vec", s)
        s = re.sub(r"\\frac\s*([^\s{}\\\[\]])", r"\\frac{\1}", s)  # short form: \frac12
        s = re.sub(
            r"\\frac\{([^{}]*)\}\s*([^\s{}\\])", r"\\frac{\1}{\2}", s
        )  # \frac{x}2
        s = re.sub(r"\\frac\{([^{}]*)\}\{([^{}]*)\}", r"((\1)/(\2))", s)
        s = re.sub(r"\\sqrt\s*([^\s{}\\])", r"\\sqrt{\1}", s)
        s = re.sub(r"\\sqrt\{([^{}]*)\}", r"sqrt(\1)", s)

        s = re.sub(r"_\{([^{}]*)\}", r"\1", s)
        s = re.sub(
            r"\^\{([^{}]*)\}",
            lambda m: "^"
            + (
                m.group(1)
                if re.fullmatch(r"-?\d+|\d*[+-]", m.group(1))
                else f"({m.group(1)})"
            ),
            s,
        )

    s = re.sub(r"_(\w)", r"\1", s)
    s = re.sub(r"\^(\w)", r"^\1", s)

    s = re.sub(r"\[\s+", "[", s)
    s = re.sub(r"\s+\]", "]", s)  #
    s = re.sub(r"\]{2,}", "]", s)
    s = re.sub(
        r"\[([^\]]*)\]",
        lambda m: "["
        + re.sub(r"\(([^()]*)\)/\(([^()]*)\)", r"\1/\2", m.group(1))
        + "]",
        s,
    )

    return s.strip().replace("\x00", "_").replace("\x01", "{").replace("\x02", "}")


def calc_to_latex(s) -> str:
    s = str(s).replace("{", "\x01").replace("}", "\x02")
    s = re.sub(r"(?<![\w\\])([^\W\d]\w*?)(?:\\_|_)vec(?!\w)", r"\\vec{\1}", s)
    s = re.sub(r"sqrt\(([^()]*)\)", r"\\sqrt{\1}", s)

    s = re.sub(r"\d+\.\d{7,}(?:e[+-]?\d+)?", lambda m: f"{float(m.group()):.6g}", s)
    s = re.sub(
        r"(\d(?:\.\d+)?)e([+-]?\d+)",
        lambda m: f"{m.group(1)}\\cdot{{10}}^{{{int(m.group(2))}}}",
        s,
    )
    s = re.sub(r"\^([\d.]+)", r"^{\1}", s)
    s = re.sub(r"([^\s/]+)/([^\s/]+)", r"\\frac{\1}{\2}", s)


    s = re.sub(r"(?<=[A-Za-z\)])(\d+)", r"_{\1}", s)

    s = re.sub(r"(?<=[A-Za-z\)\}])([+-])(?=$|\s)", r"^{\1}", s)
    s = (
        s.replace("<->", r"\rightleftharpoons ")
        .replace("->", r"\to ")
        .replace("*", r"\cdot ")
    )
    s = s.replace(" ", r"\ ").replace("\x01", r"\{").replace("\x02", r"\}")
    return r"\mathrm{" + s + "}"


def latex_text(s):
    esc = {
        "\\": r"\backslash ",
        "{": r"\{",
        "}": r"\}",
        "#": r"\#",
        "%": r"\%",
        "_": r"\_",
        "&": r"\&",
        "$": r"\$",
        "^": r"\^{}",
        "~": r"\~{}",
    }
    text = lambda p: r"\text{" + "".join(esc.get(c, c) for c in p) + "}"
    parts = re.split(r"(?<!\w)([^\W\d]\w*?)_vec(?!\w)", s)
    return "".join(
        r"\vec{" + text(p) + "}" if i % 2 else text(p)
        for i, p in enumerate(parts)
        if p or len(parts) == 1
    )



MAX_LOOP_ROWS = 50

class _InterpreterBridge(QObject):
    finished = Signal(int, str)
    modeChanged = Signal(str)
    escaped = Signal()
    dirtyChanged = Signal(bool)
    historyChanged = Signal(bool, bool)
    leaked = Signal()
    bjerrumExported = Signal(str)
    styleChanged = Signal(bool, bool, str, str)

    def __init__(self,parent = None):
        super().__init__(parent)
        self.pool = multiprocessing.Pool(1, _InterpreterBridge.evaluate_in_worker, ("[]",))
        self.job = None
        self.leaked.connect(self.restart)
        self.bjerrumExported.connect(self.export_bjerrum)

    @staticmethod
    def evaluate_in_worker(data):
        return _InterpreterBridge.evaluate(None, data), threading.active_count() > 1

    @Slot(bool, bool, str, str)
    def setStyle(self, bold, italic, color, highlight):
        self.styleChanged.emit(bold, italic, color, highlight)

    @Slot(bool)
    def reportDirty(self, dirty):
        self.dirtyChanged.emit(dirty)

    @Slot(bool, bool)
    def reportHistory(self, can_undo, can_redo):
        self.historyChanged.emit(can_undo, can_redo)

    @Slot(str)
    def reportMode(self, mode):
        self.modeChanged.emit(mode)

    @Slot()
    def escape(self):
        self.escaped.emit()

    def done(self, run_id,rows, leaked):
        rows = json.loads(rows)
        for kind, pks in rows:
            if kind == "bjerrum":
                self.bjerrumExported.emit(pks)
        self.finished.emit(run_id, json.dumps([row for row in rows if row[0] != "bjerrum"]))
        if leaked:
            self.leaked.emit()

    @Slot(str)
    def export_bjerrum(self, pks):
        chem.bjerrum(json.loads(pks))

    @Slot()
    def restart(self):
        if self.job is None or self.job.ready():
            self.cancel()

    @Slot(result=str)
    def help(self):
        return json.dumps({
            name: [calc_to_latex(line.replace("_", r"\_").replace("%", r"\%")) for line in text.splitlines()]
            for name, text in interpreter.EV().help_text.items()
        })

    def evaluate(self, data):
        latex_lines = json.loads(data)
        ev = interpreter.EV()
        try:
            result = ev.ev("\n".join(Latex_to_calc(l) for l in latex_lines))
        except Exception as e:
            return json.dumps([["error", latex_text(f"Error: {e}")]])

        rows = []
        for i, latex in enumerate(latex_lines):
            rows.append(["code", latex])
            value = result.get(i, "")
            values = value if isinstance(value, list) else [value]
            if len(values) > MAX_LOOP_ROWS:
                rows.append(["result", r"\Rightarrow\:" + latex_text(f"... {len(values) - MAX_LOOP_ROWS} resultater skjult")])
                values = values[-MAX_LOOP_ROWS:]
            for value in values:
                try:
                    if isinstance(value, chem.BjerrumExport):
                        rows.append(["bjerrum", json.dumps(value.pks)])
                        continue

                    if isinstance(value, Vector):
                        rows.append(["result", r"\Rightarrow\:\begin{pmatrix}" + r"\\".join(calc_to_latex(c) for c in value.cordinates) + r"\end{pmatrix}"])
                        continue

                    if isinstance(value, dict):
                        rows.append(["result", r"\Rightarrow\:" + r",\ ".join(f"{sympy.latex(k)} = {calc_to_latex(v) if isinstance(v, sympy.Float) else sympy.latex(v)}" for k, v in value.items())])
                        continue

                    if isinstance(value, sympy.Basic) and not isinstance(value, sympy.Float):
                        rows.append(["result", r"\Rightarrow\:" + sympy.latex(value)])
                        continue

                    if isinstance(value, utils.FunctionPlot):
                        rows.append(["plot", json.dumps({"functions": value.functions, "start": value.start, "end": value.end})])
                        continue

                    if isinstance(value, Figure):
                        buf = io.BytesIO()
                        value.savefig(buf, format = "png")
                        rows.append(["image","data:image/png;base64," + base64.b64encode(buf.getvalue()).decode()])
                        continue
                    for res in str(value).splitlines():
                        if res.startswith("Error"):
                            rows.append(["error", r"\Rightarrow\:" + latex_text(res)])
                        else:
                            rows.append(
                                [
                                    "result",
                                    r"\Rightarrow\:"
                                    + calc_to_latex(
                                        res.replace("_", r"\_").replace("%", r"\%")
                                    ),
                                ]
                            )
                except Exception as e:
                    rows.append(["error", r"\Rightarrow\:" + latex_text(f"Error: {e}")])
        return json.dumps(rows)

    @Slot(int, str)
    def run(self,run_id,data):
        if self.job and not self.job.ready():
            self.cancel()
        self.job = self.pool.apply_async(_InterpreterBridge.evaluate_in_worker,(data,),
            callback=lambda result: self.done(run_id,*result),
            error_callback=lambda e: self.finished.emit(run_id, json.dumps([["error", latex_text(f'Error: {e}')]])))
        
    @Slot()
    def cancel(self):
        if self.pool:
            self.pool.terminate()
        self.pool = multiprocessing.Pool(1, _InterpreterBridge.evaluate_in_worker, ("[]",))
        self.job = None


class _KetcherBridge(QObject):
    smilesReady = Signal(str)


    @Slot(str)
    def setSmiles(self, s):
        self.smilesReady.emit(s)

class _Bridge(QObject):
    changed = Signal(str)
    entered = Signal()

    def __init__(self):
        super().__init__()
        self.latex = ""

    @Slot(str)
    def setLatex(self, s):
        self.latex = s
        self.changed.emit(s)

    @Slot()
    def pressEnter(self):
        self.entered.emit()


class MathInput(QWebEngineView):
    returnPressed = Signal()

    def __init__(self, placeholder="", parent=None, text_mode=False, height=LINE_HEIGHT):
        super().__init__(parent)
        self.setFixedHeight(height)
        self._placeholder = placeholder
        self._loaded = False
        self._bridge = _Bridge()
        self._channel = QWebChannel(self.page())
        self._channel.registerObject("bridge", self._bridge)
        self.page().setWebChannel(self._channel)
        self.page().setBackgroundColor(QColor(SIDEBAR))

        self._bridge.entered.connect(self.returnPressed)
        self.loadFinished.connect(self._on_loaded)
        url = QUrl.fromLocalFile(
            str(resource_path("./Assets_math_live/mathfield.html"))
        )
        if text_mode:
            url.setQuery("mode=text")
        self.load(url)

    def text(self):
        return Latex_to_calc(self._bridge.latex)

    def setText(self, s):
        self._bridge.latex = str(s)
        if self._loaded:
            self.page().runJavaScript(f"setValue({json.dumps(self._bridge.latex)})")

    def setStyleSheet(self, _):
        pass

    def setPlaceholderText(self, t):
        self._placeholder = t
        self.page().runJavaScript(f"setPlaceholder({json.dumps(t)})")

    def clear(self):
        self.page().runJavaScript("clearField()")

    def _on_loaded(self, ok):
        if not ok:
            print("MathInput: failed to load", self.url())
            return
        self._loaded = True
        self.setPlaceholderText(self._placeholder)
        if self._bridge.latex:
            self.page().runJavaScript(f"setValue({json.dumps(self._bridge.latex)})")

class PlainField(QLineEdit):
    def __init__(self, placeholder="", read_only=False):
        super().__init__()
        self.setPlaceholderText(placeholder)
        self.setReadOnly(read_only)
        self.setFixedHeight(LINE_HEIGHT)
        self.setStyleSheet(f"QLineEdit {{ background-color: {BUTTON}; color: {TEXT}; border: 1px solid {HEADER}; border-radius: 8px; padding: 0 8px; font-family: 'Segoe UI'; font-size: 12px; }}")

class MathOutput(QWebEngineView):
    def __init__(self, placeholder="", parent=None):
        super().__init__(parent)
        self.setFixedHeight(36)
        self._placeholder = placeholder
        self._raw = ""
        self._loaded = False
        self.page().setBackgroundColor(QColor(SIDEBAR))
        self.loadFinished.connect(self._on_loaded)
        url = QUrl.fromLocalFile(str(resource_path("Assets_math_live/mathfield.html")))
        url.setQuery("readonly=1")
        self.load(url)

    def _on_loaded(self, ok):
        if not ok:
            print("MathOutput: failed to load", self.url())
            return
        self._loaded = True
        self.setPlaceholderText(self._placeholder)
        # self.setAccent(ACCENT)
        self._push()

    def _push(self):
        if self._raw.startswith("Error"):
            latex = latex_text(self._raw)
        else:
            latex = calc_to_latex(self._raw.replace("%", r"\%")) if self._raw else ""
        self.page().runJavaScript(f"setValue({json.dumps(latex)})")

    def setText(self, s):
        self._raw = str(s)
        if self._loaded:
            self._push()

    setPlainText = setText

    def text(self):
        return self._raw

    def setPlaceholderText(self, t):
        self._placeholder = t
        self.page().runJavaScript(f"setPlaceholder({json.dumps(t)})")

    def setReadOnly(self, _):
        pass

    def setStyleSheet(self, _):
        pass

class TextOutput(QTextEdit): 
    def __init__(self, placeholder="", parent=None, height=BOX_HEIGHT):
        super().__init__(parent)
        self.setReadOnly(True)
        self.setPlaceholderText(placeholder)
        self.setMinimumHeight(height)
        self.setVerticalScrollBarPolicy(Qt.ScrollBarAsNeeded)
        self.setStyleSheet(f"""
            QTextEdit {{
                background-color: {BUTTON}; color: {TEXT};
                border: none; border-radius: 4px; padding: 4px; font-size: 12px;
            }}
            QScrollBar:vertical {{
                background: {HOVER};
                width: 12px;
                border-radius: 5px;
                margin: 4px 2px 4px 0px;
            }}
            QScrollBar::handle:vertical {{
                background: {SIDEBAR};
                border-radius: 5px;
                min-height: 30px;
            }}
            QScrollBar::add-line:vertical, QScrollBar::sub-line:vertical {{ height: 0; }}
            QScrollBar::add-page:vertical, QScrollBar::sub-page:vertical {{ background: none; }}
        """)


    def setText(self, s):
        self.setPlainText(str(s))

    def text(self):
        return self.toPlainText()

class LicenseWindow(QDialog):
    activated = Signal(bool, str)
    
    def __init__(self, parent=None):
        super().__init__(parent)
        self.setWindowTitle("Carbon: Licens manager")
        self.setWindowIcon(QIcon(str(ASSETS_DIR / "Carbon_Round.svg")))
        self.setModal(True)
        self.setFixedSize(360, 180)
        self.setStyleSheet(f"""
            QDialog {{ background-color: {BG}; }}
            QLabel {{ color: {TEXT}; }}
            QLineEdit {{
                background-color: {BUTTON};
                color: {TEXT};
                padding: 6px 10px;
                border: none;
                border-radius: 8px;
            }}
            QLineEdit:focus {{
                border: none;
            }}
            QPushButton {{
                background-color: {BUTTON};
                color: {TEXT};
                padding: 6px 14px;
                border: none;
                border-radius: 8px;
            }}
            QPushButton:hover {{ background-color: {HOVER}; }}
            QPushButton:default {{ border: none; }}
        """)

        layout = QVBoxLayout(self)
 
        self.key_input = QLineEdit()
        self.key_input.setPlaceholderText("Indtast licens her...")
        layout.addWidget(self.key_input)

        self.message = QLabel()
        self.message.setStyleSheet(f"color: {BUTTON}; background: transparent; padding-left: 10px;")
        layout.addWidget(self.message)

        button_row = QHBoxLayout()

        logo = QSvgWidget(str(ASSETS_DIR / "Carbon_Full.svg"))
        logo.renderer().setAspectRatioMode(Qt.KeepAspectRatio)
        logo.setFixedSize(150,75)
        button_row.addWidget(logo)
        button_row.addStretch()

        self.ok_btn = QPushButton("Ok")
        self.ok_btn.clicked.connect(self.try_accept)
        button_row.addWidget(self.ok_btn)

        cancel_btn = QPushButton("Afbryd")
        cancel_btn.clicked.connect(self.reject)
        button_row.addWidget(cancel_btn)

        layout.addLayout(button_row)

        self.activated.connect(self.finish_activation)

        self.version_label = QLabel(version, self)
        self.version_label.setStyleSheet(f"color: {BUTTON}; font-size: 10px; background: transparent;")
        self.version_label.adjustSize()
        self.version_label.move(
            self.width() - self.version_label.width() - 1,
            self.height() - self.version_label.height() - 1,
        )
    
    def try_accept(self):
        key = self.key_input.text().strip()
        licensed, data = license_manager.check_license(key)
        if not licensed:
            self.message.setText(data)
            return
        self.pending = key, data
        self.key_input.setFocus()
        self.ok_btn.setEnabled(False)
        self.message.setText("Aktiverer...")
        threading.Thread(target=self.run_activation, args=(key,), daemon=True).start()

    def run_activation(self, key):
        try:
            ok, msg = license_manager.activate(key)
        except Exception:
            ok, msg = False, "Fejl"
        self.activated.emit(bool(ok), str(msg))

    def finish_activation(self, ok, msg):
        self.ok_btn.setEnabled(True)
        if not ok:
            self.message.setText(msg)
            return
        try:
            license_manager.save_activation(*self.pending)
        except OSError:
            self.message.setText("Licensen kunne ikke gemmes")
            return
        self.accept()


# For biotek stamtræ
træ = biotek.graph()


class DraggablePanel(QWidget):
    def __init__(self, title, body_widget, parent=None, help_text=None):
        super().__init__(parent)
        self.help_text = help_text or "Ingen hjælpetekst endnu :("
        self.setAttribute(Qt.WA_StyledBackground)
        self.setStyleSheet(f"""
            DraggablePanel {{
                background-color: {SIDEBAR};
                border-radius: 8px;
            }}
        """)
        self.setMinimumWidth(240)
        self.resize(280, 280)

        self._drag_offset = None

        layout = QVBoxLayout(self)
        layout.setContentsMargins(0, 0, 0, 0)
        layout.setSpacing(0)

        self.header = QWidget()
        self.header.setFixedHeight(28)
        self.header.setStyleSheet(f"""
            background-color: {HEADER};
            border-top-left-radius: 8px;
            border-top-right-radius: 8px;
        """)
        self.header.installEventFilter(self)

        header_layout = QHBoxLayout(self.header)
        header_layout.setContentsMargins(8, 0, 4, 0)

        title_label = QLabel(title)
        title_label.setStyleSheet(f"color: {BUTTON}; font-weight: bold; border: none;")
        header_layout.addWidget(title_label)
        header_layout.addStretch()

        if hasattr(body_widget, "export"):
            export_btn = QToolButton()
            export_btn.setIcon(hover_icon("Save.svg"))
            export_btn.setAutoRaise(True)
            export_btn.setIconSize(QSize(14,14))
            export_btn.setFixedSize(20,20)
            export_btn.setToolTip("Eksporter")
            export_btn.setStyleSheet("QToolButton { background: transparent; border: none; }")
            export_btn.clicked.connect(body_widget.export)
            header_layout.addWidget(export_btn)

        help_btn = QPushButton("?")
        help_btn.setFixedSize(20, 20)
        help_btn.setStyleSheet(f"""
            QPushButton {{ background: transparent; border: none; color: {BUTTON}; font-weight: bold; font-size: 14px; }}
            QPushButton:hover {{ color: {HOVER}; }}
        """)
        help_btn.clicked.connect(self.show_help)
        header_layout.addWidget(help_btn)

        close_btn = QPushButton("x")
        close_btn.setFixedSize(20, 20)
        close_btn.setStyleSheet(f"""
            QPushButton {{ background: transparent; border: none; color: {BUTTON}; font-weight: bold; font-size: 14px; }}
            QPushButton:hover {{ color: {HOVER}; }}
        """)
        close_btn.clicked.connect(self.hide)
        header_layout.addWidget(close_btn)

        layout.addWidget(self.header)

        self.body = body_widget
        self.body.setStyleSheet("background-color: transparent")
        self.body.setMinimumHeight(self.body.sizeHint().height())

        scroll = QScrollArea()
        scroll.setWidget(self.body)
        scroll.setWidgetResizable(True)
        scroll.setHorizontalScrollBarPolicy(Qt.ScrollBarAlwaysOff)
        scroll.setFrameShape(QFrame.NoFrame)
        scroll.setStyleSheet(f"""
            QScrollArea {{ background: transparent; }}
            #qt_scrollarea_vcontainer {{ background: transparent; }}
            QScrollBar:vertical {{ background: transparent; width: 8px; }}
            QScrollBar::handle:vertical {{ background: {SCROLL}; border-radius: 4px; min-height: 30px; }}
            QScrollBar::add-line:vertical, QScrollBar::sub-line:vertical {{ height: 0; }}
            QScrollBar::add-page:vertical, QScrollBar::sub-page:vertical {{ background: none; }}
        """)
        layout.addWidget(scroll)
        point_cursor(self)

    def show_help(self):
        msg = QMessageBox(self)
        msg.setWindowTitle("Hjælp")
        msg.setText(self.help_text)
        msg.setIcon(QMessageBox.NoIcon)
        msg.setStyleSheet(f"""
                QMessageBox {{ background-color: {BG}; }}
                QLabel {{ color: {BUTTON}; }}
                QPushButton {{
                   background-color: {BUTTON};
                   color: {TEXT};
                   padding: 6px 14px;
                   border: none;
                   border-radius: 8px;
                }}
                QPushButton:hover {{ background-color: {HOVER}}}
            """)
        msg.exec()

    def eventFilter(self, obj, event):
        if obj is self.header:
            if (
                event.type() == event.Type.MouseButtonPress
                and event.button() == Qt.LeftButton
            ):
                self._drag_offset = event.position().toPoint()
                self.raise_()
                return True
            elif event.type() == event.Type.MouseMove and self._drag_offset is not None:
                new_pos = self.mapToParent(
                    event.position().toPoint() - self._drag_offset
                )
                new_pos = self._clamp_to_parent(new_pos)
                self.move(new_pos)
                return True
            elif event.type() == event.Type.MouseButtonRelease:
                self._drag_offset = None
                return True
        return super().eventFilter(obj, event)

    def fit_to_parent(self):
        height = self.header.height() + self.body.minimumHeight()
        self.resize(self.width(), min(height, self.parent().height()))
        self.move(self._clamp_to_parent(self.pos()))

    def _clamp_to_parent(self, pos):
        if not self.parent():
            return pos
        parent_rect = self.parent().rect()
        x = max(0, min(pos.x(), parent_rect.width() - self.width()))
        y = max(0, min(pos.y(), parent_rect.height() - self.height()))
        return pos.__class__(x, y)

@dataclass
class Panel:
    label: str
    title: str
    build: callable
    size: tuple = (280, 280)

def clear_if_empty(body):
    plain = body.findChildren(PlainField)
    if any(field.text() for field in body.findChildren(MathInput) + [f for f in plain if not f.isReadOnly()]):
        return False
    for output in body.findChildren(MathOutput) + body.findChildren(TextOutput) + [f for f in plain if f.isReadOnly()]:
        output.setText("")
    return True

def unit_panel():
    body = QWidget()
    layout = QVBoxLayout(body)
    layout.setContentsMargins(6,6,6,6)
    layout.setSpacing(6)

    value_input = MathInput("Input[Enhed]")
    layout.addWidget(value_input)

    unit_row = QHBoxLayout()
    unit_input = MathInput("Ønsket enhed")
    unit_row.addWidget(unit_input)

    si_btn = QPushButton("SI")
    si_btn.setFixedSize(36,36)
    si_btn.setToolTip("Konverter til SI")
    si_btn.setStyleSheet(calc_button_style)
    unit_row.addWidget(si_btn)
    layout.addLayout(unit_row)

    calc_btn = QPushButton("Beregn")
    calc_btn.setStyleSheet(calc_button_style)
    layout.addWidget(calc_btn)

    output = MathOutput("Resultat")
    layout.addWidget(output)
    layout.addStretch()

    def calc():
        if clear_if_empty(body):
            return
        result = interpreter.EV().ev(f"EnhedKonvertering({value_input.text()},{unit_input.text()})")
        output.setText(result.get(0, ""))

    calc_btn.clicked.connect(calc)
    value_input.returnPressed.connect(calc)
    unit_input.returnPressed.connect(calc)
    si_btn.clicked.connect(lambda: unit_input.setText("SI"))

    return body

def pH_panel():
    body = QWidget()
    layout = QVBoxLayout(body)
    layout.setContentsMargins(6,6,6,6)
    layout.setSpacing(6)

    pKs_input = PlainField("pKs eller syrenavn")
    layout.addWidget(pKs_input)

    pKb_input = PlainField("pKb eller basenavn")
    layout.addWidget(pKb_input)

    konc_input = MathInput("Koncentration[Enhed]")
    layout.addWidget(konc_input)

    calc_btn = QPushButton("Beregn")
    calc_btn.setStyleSheet(calc_button_style)
    layout.addWidget(calc_btn)

    ph_output = PlainField("pH", True)
    layout.addWidget(ph_output)

    poh_output = PlainField("pOH", True)
    layout.addWidget(poh_output)
    layout.addStretch()

    def calc():
        if clear_if_empty(body):
            return
        acid, base = pKs_input.text(), pKb_input.text()
        if bool(acid) == bool(base):
            ph_output.setText("Udfyld enten syre eller base")
            poh_output.setText("")
            return
        result = interpreter.EV().ev(f"{'pH' if acid else 'pOH'}({acid or base},{konc_input.text()})").get(0, "")
        if result.startswith("Error"):
            ph_output.setText(result)
            poh_output.setText("")
            return
        decimals = len(result.split(".")[1]) if "." in result else 0
        other = f"{14 - float(result):.{decimals}f}"
        ph, poh = (result, other) if acid else (other, result)
        ph_output.setText(f"pH = {ph}")
        poh_output.setText(f"pOH = {poh}")

    calc_btn.clicked.connect(calc)
    pKs_input.returnPressed.connect(calc)
    pKb_input.returnPressed.connect(calc)
    konc_input.returnPressed.connect(calc)
    
    return body

def afstemning_panel():
    body = QWidget()
    layout = QVBoxLayout(body)
    layout.setContentsMargins(6,6,6,6)
    layout.setSpacing(6)

    reaktion_input = MathInput("Reaktant->Produkt")
    layout.addWidget(reaktion_input)

    solution_input = PlainField("Opløsning (syre/base)")
    layout.addWidget(solution_input)

    calc_btn = QPushButton("Beregn")
    calc_btn.setStyleSheet(calc_button_style)
    layout.addWidget(calc_btn)

    output = MathOutput("Afstemt reaktion")
    layout.addWidget(output)
    layout.addStretch()

    def calc():
        if clear_if_empty(body):
            return
        arg = f"{reaktion_input.text()},{solution_input.text()}" if solution_input.text() else reaktion_input.text()
        result = interpreter.EV().ev(f"Afstem({arg})")
        output.setText(result.get(0, ""))

    calc_btn.clicked.connect(calc)
    reaktion_input.returnPressed.connect(calc)
    solution_input.returnPressed.connect(calc)
    
    return body

def analyse_panel():
    body = QWidget()
    layout = QVBoxLayout(body)
    layout.setContentsMargins(6,6,6,6)
    layout.setSpacing(6)

    input = MathInput("Molekyle")
    layout.addWidget(input)

    calc_btn = QPushButton("Beregn")
    calc_btn.setStyleSheet(calc_button_style)
    layout.addWidget(calc_btn)

    molekyle = MathOutput("Molekyle")
    layout.addWidget(molekyle)

    empirisk = MathOutput("Empirisk formel")
    layout.addWidget(empirisk)

    molarmasse = MathOutput("Molarmasse")
    layout.addWidget(molarmasse)

    dbe = PlainField("DBE", True)
    layout.addWidget(dbe)

    antal = PlainField("Antal atomer", True)
    layout.addWidget(antal)

    masseprocent = TextOutput("Masseprocent:")
    layout.addWidget(masseprocent, stretch=1)
    layout.addStretch()

    outputs = [molekyle, empirisk, molarmasse, dbe, antal]

    def calc():
        if clear_if_empty(body):
            return
        result = interpreter.EV().ev(f"Analyse({input.text()})").get(0,"")
        lines = result.splitlines()
        if result.startswith("Error"):
            for box in outputs:
                box.setText("")
            masseprocent.setText(result)
            return
        for box, line in zip(outputs, lines):
            box.setText(line.strip())
        masseprocent.setText("Masseprocent:\n" + "\n".join(lines[6:]))

    calc_btn.clicked.connect(calc)
    input.returnPressed.connect(calc)
    
    return body

def bjerrum_panel():
    body = QWidget()
    layout = QVBoxLayout(body)
    layout.setContentsMargins(6,6,6,6)
    layout.setSpacing(6)

    input = PlainField("pKs-værdier")
    layout.addWidget(input)

    calc_btn = QPushButton("Beregn")
    calc_btn.setStyleSheet(calc_button_style)
    layout.addWidget(calc_btn)

    plot_area = QWidget()
    plot_area.setMinimumHeight(300)
    plot_layout = QVBoxLayout(plot_area)
    plot_layout.setContentsMargins(0,0,0,0)
    layout.addWidget(plot_area, stretch=1)

    def calc():
        while plot_layout.count():
            plot_layout.takeAt(0).widget().deleteLater()
        if not input.text():
            return
        result = interpreter.EV().ev(f"BjerrumDiagram({input.text()})").get(0,"")
        if isinstance(result, Figure):
            plot_layout.addWidget(FigureCanvasQTAgg(result))
        else:
            error = QLabel(str(result))
            error.setWordWrap(True)
            error.setStyleSheet(f"color: {BUTTON}")
            plot_layout.addWidget(error, alignment=Qt.AlignTop)

    def export():
        result = interpreter.EV().ev(f"BjerrumDiagram({input.text()},export)").get(0, "")
        if isinstance(result, chem.BjerrumExport):
            chem.bjerrum(result.pks)
        elif result:
            calc()

    calc_btn.clicked.connect(calc)
    input.returnPressed.connect(calc)

    body.export = export
    
    return body

def udbytte_panel():
    body = QWidget()
    layout = QVBoxLayout(body)
    layout.setContentsMargins(6,6,6,6)
    layout.setSpacing(6)

    praktisk_input = MathInput("Praktisk[Enhed]")
    layout.addWidget(praktisk_input)

    teori_input = MathInput("Teoretisk[Enhed]")
    layout.addWidget(teori_input)

    calc_btn = QPushButton("Beregn")
    calc_btn.setStyleSheet(calc_button_style)
    layout.addWidget(calc_btn)

    output = PlainField("Resultat", True)
    layout.addWidget(output)
    layout.addStretch()

    def calc():
        if clear_if_empty(body):
            return
        result = interpreter.EV().ev(f"UdbytteProcent({praktisk_input.text()},{teori_input.text()})").get(0, "")
        output.setText(result)

    calc_btn.clicked.connect(calc)
    praktisk_input.returnPressed.connect(calc)
    teori_input.returnPressed.connect(calc)
    
    return body

def volumen_panel():
    body = QWidget()
    layout = QVBoxLayout(body)
    layout.setContentsMargins(6,6,6,6)
    layout.setSpacing(6)

    specifik_input = MathInput("Specifik[Enhed]")
    layout.addWidget(specifik_input)

    samlet_input = MathInput("Samlet[Enhed]")
    layout.addWidget(samlet_input)

    calc_btn = QPushButton("Beregn")
    calc_btn.setStyleSheet(calc_button_style)
    layout.addWidget(calc_btn)

    output = PlainField("Resultat", True)
    layout.addWidget(output)
    layout.addStretch()

    def calc():
        if clear_if_empty(body):
            return
        result = interpreter.EV().ev(f"VolumenProcent({specifik_input.text()},{samlet_input.text()})").get(0, "")
        output.setText(result)

    calc_btn.clicked.connect(calc)
    specifik_input.returnPressed.connect(calc)
    samlet_input.returnPressed.connect(calc)
    
    return body

def masse_panel():
    body = QWidget()
    layout = QVBoxLayout(body)
    layout.setContentsMargins(6,6,6,6)
    layout.setSpacing(6)

    specifik_input = MathInput("Specifik[Enhed]")
    layout.addWidget(specifik_input)

    samlet_input = MathInput("Samlet[Enhed]")
    layout.addWidget(samlet_input)

    calc_btn = QPushButton("Beregn")
    calc_btn.setStyleSheet(calc_button_style)
    layout.addWidget(calc_btn)

    output = PlainField("Resultat", True)
    layout.addWidget(output)
    layout.addStretch()

    def calc():
        if clear_if_empty(body):
            return
        result = interpreter.EV().ev(f"MasseProcent({specifik_input.text()},{samlet_input.text()})").get(0, "")
        output.setText(result)

    calc_btn.clicked.connect(calc)
    specifik_input.returnPressed.connect(calc)
    samlet_input.returnPressed.connect(calc)
    
    return body

def mængde_panel():
    body = QWidget()
    layout = QVBoxLayout(body)
    layout.setContentsMargins(6,6,6,6)
    layout.setSpacing(6)

    masse_input = MathInput("Masse[Enhed]")
    layout.addWidget(masse_input)

    volumen_input = MathInput("Volumen[Enhed]")
    layout.addWidget(volumen_input)

    stofmængde_input = MathInput("Stofmængde[Enhed]")
    layout.addWidget(stofmængde_input)

    koncentration_input = MathInput("Koncentration[Enhed]")
    layout.addWidget(koncentration_input)

    molarmasse_input = MathInput("Molarmasse[Enhed]")
    layout.addWidget(molarmasse_input)

    densitet_input = MathInput("Densitet[Enhed]")
    layout.addWidget(densitet_input)

    calc_btn = QPushButton("Beregn")
    calc_btn.setStyleSheet(calc_button_style)
    layout.addWidget(calc_btn)

    output = TextOutput("Resultat")
    output.ensurePolished()
    output.setFixedHeight(output.fontMetrics().lineSpacing() * 6+16)
    layout.addWidget(output)
    layout.addStretch()

    def calc():
        if clear_if_empty(body):
            return
        fields = [
            ("m", masse_input),
            ("V", volumen_input),
            ("n", stofmængde_input),
            ("c", koncentration_input),
            ("M", molarmasse_input),
            ("p", densitet_input),
        ]
        args = ",".join(f"{key}={field.text()}" for key, field in fields if field.text())
        result = interpreter.EV().ev(f"MængdeBeregning({args})").get(0, "")

        output.setText(result)

    calc_btn.clicked.connect(calc)
    masse_input.returnPressed.connect(calc)
    volumen_input.returnPressed.connect(calc)
    stofmængde_input.returnPressed.connect(calc)
    koncentration_input.returnPressed.connect(calc)
    molarmasse_input.returnPressed.connect(calc)
    densitet_input.returnPressed.connect(calc)
    
    return body

def dna_peptid_panel():
    body = QWidget()
    layout = QVBoxLayout(body)
    layout.setContentsMargins(6,6,6,6)
    layout.setSpacing(6)

    DNA_input = PlainField("DNA-streng")
    layout.addWidget(DNA_input)

    calc_btn = QPushButton("Beregn")
    calc_btn.setStyleSheet(calc_button_style)
    layout.addWidget(calc_btn)

    output = PlainField("Peptidkæde", True)
    layout.addWidget(output)
    layout.addStretch()

    def calc():
        if clear_if_empty(body):
            return
        result = interpreter.EV().ev(f"DNATilPeptid({DNA_input.text()})").get(0, "")
        output.setText(result)

    calc_btn.clicked.connect(calc)
    DNA_input.returnPressed.connect(calc)
    
    return body

def rna_peptid_panel():
    body = QWidget()
    layout = QVBoxLayout(body)
    layout.setContentsMargins(6,6,6,6)
    layout.setSpacing(6)

    RNA_input = PlainField("RNA-streng")
    layout.addWidget(RNA_input)

    calc_btn = QPushButton("Beregn")
    calc_btn.setStyleSheet(calc_button_style)
    layout.addWidget(calc_btn)

    output = PlainField("Peptidkæde", True)
    layout.addWidget(output)
    layout.addStretch()

    def calc():
        if clear_if_empty(body):
            return
        result = interpreter.EV().ev(f"RNATilPeptid({RNA_input.text()})").get(0, "")
        output.setText(result)

    calc_btn.clicked.connect(calc)
    RNA_input.returnPressed.connect(calc)
    
    return body

def puffer_panel():
    body = QWidget()
    layout = QVBoxLayout(body)
    layout.setContentsMargins(6,6,6,6)
    layout.setSpacing(6)

    syre_konc_input = MathInput("Koncentration af syre")
    layout.addWidget(syre_konc_input)

    base_konc_input = MathInput("Koncentration af base")
    layout.addWidget(base_konc_input)

    pks_input = PlainField("pKs")
    layout.addWidget(pks_input)

    calc_btn = QPushButton("Beregn")
    calc_btn.setStyleSheet(calc_button_style)
    layout.addWidget(calc_btn)

    output = PlainField("pH", True)
    layout.addWidget(output)
    layout.addStretch()

    def calc():
        if clear_if_empty(body):
            return
        result = interpreter.EV().ev(f"Puffer({syre_konc_input.text()},{base_konc_input.text()},{pks_input.text()})").get(0, "")
        output.setText(result)

    calc_btn.clicked.connect(calc)
    syre_konc_input.returnPressed.connect(calc)
    base_konc_input.returnPressed.connect(calc)
    pks_input.returnPressed.connect(calc)

    return body

def ph_konc_panel():
    body = QWidget()
    layout = QVBoxLayout(body)
    layout.setContentsMargins(6,6,6,6)
    layout.setSpacing(6)

    ph_input = PlainField("pH")
    layout.addWidget(ph_input)

    calc_btn = QPushButton("Beregn")
    calc_btn.setStyleSheet(calc_button_style)
    layout.addWidget(calc_btn)

    h3o_output = MathOutput("Oxoniumkoncentration")
    layout.addWidget(h3o_output)

    oh_output = MathOutput("Hydroxidkoncentration")
    layout.addWidget(oh_output) 
    layout.addStretch()

    def calc():
        if clear_if_empty(body):
            return
        result = interpreter.EV().ev(f"pHTilKoncentration({ph_input.text()})").get(0, "")
        if result.startswith("Error"):
            h3o_output.setText(result)
            oh_output.setText("")
            return
        h3o, oh = result.splitlines()
        h3o_output.setText(h3o)
        oh_output.setText(oh)

    calc_btn.clicked.connect(calc)
    ph_input.returnPressed.connect(calc)

    return body

def mut_panel():
    body = QWidget()
    layout = QVBoxLayout(body)
    layout.setContentsMargins(6,6,6,6)
    layout.setSpacing(6)

    rask_input = PlainField("Rask kæde")
    layout.addWidget(rask_input)

    mut_input = PlainField("Muteret kæde")
    layout.addWidget(mut_input)

    calc_btn = QPushButton("Beregn")
    calc_btn.setStyleSheet(calc_button_style)
    layout.addWidget(calc_btn)

    output = TextOutput("Mutationstype")
    output.ensurePolished()
    output.setFixedHeight(output.fontMetrics().lineSpacing() * 3 + 16)
    layout.addWidget(output)
    layout.addStretch()

    def calc():
        if clear_if_empty(body):
            return
        result = interpreter.EV().ev(f"MutationsAnalyse({rask_input.text()}, {mut_input.text()})").get(0, "")
        output.setText(result)

    calc_btn.clicked.connect(calc)
    rask_input.returnPressed.connect(calc)
    mut_input.returnPressed.connect(calc)

    return body

PANELS = {
    "unit": Panel("Enhed","Enhedsomregner", unit_panel),
    "pH": Panel("pH og pOH","pH og pOH Beregning", pH_panel),
    "balance": Panel("Afstemning","Reaktionsafstemning",afstemning_panel),
    "analysis": Panel("Analyse","Molekylær Analyse",analyse_panel),
    "bjerrum": Panel("Bjerrumdiagram","Bjerrumdiagram",bjerrum_panel, (450,450)),
    "udbytteprocent": Panel("Udbytteprocent","Udbytteprocent",udbytte_panel),
    "volumenprocent": Panel("Volumenprocent","Volumenprocent",volumen_panel),
    "masseprocent": Panel("Masseprocent", "Masseprocent",masse_panel),
    "mængdeberegning": Panel("Mængdeberegning","Mængdeberegning",mængde_panel),
    "dna_peptid": Panel("DNA Translation","DNA Translation",dna_peptid_panel),
    "rna_peptid": Panel("RNA Translation","RNA Translation",rna_peptid_panel),
    "puffer": Panel("Puffer", "pH i Puffer",puffer_panel),
    "h3o": Panel("H3O+ og OH-", "H3O+ og OH- koncentration fra pH",ph_konc_panel),
    "mutation": Panel("Mutation", "Mutationsanalyse", mut_panel),
}

class SegmentedControl(QWidget):
    changed = Signal(str)

    def __init__(self, options, parent=None):
        super().__init__(parent)
        self.setAttribute(Qt.WA_StyledBackground)
        self.setStyleSheet(f"SegmentedControl {{ background-color: {SIDEBAR}; border-radius: 12px; }}")

        self.highlight = QWidget(self)
        self.highlight.setStyleSheet(f"background-color: {BG}; border-radius: 10px;")
        self.anim = QPropertyAnimation(self.highlight, b"geometry", self)
        self.anim.setDuration(200)
        self.anim.setEasingCurve(QEasingCurve.OutCubic)

        layout = QHBoxLayout(self)
        layout.setContentsMargins(2,2,2,2)
        layout.setSpacing(0)
        self.buttons = {}
        for label, value, tooltip in options:
            btn = QPushButton(label)
            btn.setToolTip(tooltip)
            btn.setFocusPolicy(Qt.NoFocus)
            btn.setStyleSheet(f"""
                QPushButton {{ background: transparent; color: {BUTTON}; border: none; font-weight: bold; padding: 3px 12px; }}
                QPushButton:hover {{ color: {HOVER}; }}
                QToolTip {{ background-color: {BUTTON}; color: {TEXT}; border: 1px solid {HEADER}; }}
            """)
            btn.clicked.connect(lambda _=False, v=value: (self.setCurrent(v), self.changed.emit(v)))
            layout.addWidget(btn)
            self.buttons[value] = btn
        self.current = options[0][1]

    def setCurrent(self, value):
        self.current = value
        self.anim.stop()
        self.anim.setStartValue(self.highlight.geometry())
        self.anim.setEndValue(self.buttons[value].geometry())
        self.anim.start()

    def resizeEvent(self, event):
        super().resizeEvent(event)
        self.anim.stop()
        self.highlight.setGeometry(self.buttons[self.current].geometry())

class Dropdown(QWidget):
    def __init__(self, label, content, parent=None):
        super().__init__(parent)
        self.header = QPushButton(label)
        self.header.setFixedHeight(30)
        self.header.setCheckable(True)
        self.header.setStyleSheet(button_style)
        self.arrow = QLabel()
        self.arrow.setAttribute(Qt.WA_TransparentForMouseEvents)
        self.arrow.setStyleSheet("background: transparent;")
        header_layout = QHBoxLayout(self.header)
        header_layout.setContentsMargins(0,0,10,0)
        header_layout.addStretch()
        header_layout.addWidget(self.arrow)

        self.setAttribute(Qt.WA_StyledBackground)
        self.setStyleSheet(f"""
            Dropdown {{ background-color: {BG}; border-radius: 8px; }}
            Dropdown QWidget {{ background: transparent; }}
        """)
        self.body = QWidget()
        body_layout = QVBoxLayout(self.body)
        body_layout.setContentsMargins(10,10,10,10)
        body_layout.addWidget(content)

        layout = QVBoxLayout(self)
        layout.setContentsMargins(0,0,0,0)
        layout.setSpacing(0)
        layout.addWidget(self.header)
        layout.addWidget(self.body)

        self.header.toggled.connect(self.toggle)
        self.toggle(False)

    def toggle(self, open):
        self.body.setVisible(open)
        self.arrow.setPixmap(QIcon(str(ASSETS_DIR / ("Dropdown.svg" if open else "Dropdown_Up.svg"))).pixmap(12,12))
        if self.parentWidget():
            self.layout().activate()
            self.parentWidget().layout().activate()


class RichButton(QPushButton):
    def __init__(self, label):
        super().__init__()
        self.source = label
        self.svg = label.endswith(".svg")
        self.label = QSvgWidget() if self.svg else QLabel(label)
        self.label.setAttribute(Qt.WA_TransparentForMouseEvents)
        layout = QHBoxLayout(self)
        vertical = 0 if self.svg else 4
        layout.setContentsMargins(4, vertical, 4, vertical)
        layout.addWidget(self.label, alignment=Qt.AlignCenter)
        self.set_hover(False)

    def set_hover(self, hover):
        if self.svg:
            self.label.load(str(ASSETS_DIR / (self.source.replace(".svg", "_Hover.svg") if hover else self.source)))
        else:
            self.label.setStyleSheet(f"color: {HOVER if hover else BUTTON}; font-size: 18px; font-family: 'DejaVu Sans'; background: transparent;")

    def sizeHint(self):
        return self.layout().sizeHint()

    def enterEvent(self, event):
        self.set_hover(True)
        super().enterEvent(event)

    def leaveEvent(self, event):
        self.set_hover(False)
        super().leaveEvent(event)


def symbol_grid(symbols, insert, columns=6):
    grid_widget = QWidget()
    grid = QGridLayout(grid_widget)
    grid.setContentsMargins(0,0,0,0)
    grid.setSpacing(2)
    for i, (label, latex) in enumerate(symbols):
        btn = RichButton(label) if "<" in label or label.endswith(".svg") else QPushButton(label)
        btn.setFocusPolicy(Qt.NoFocus)
        btn.setStyleSheet(f"""
            QPushButton {{ color: {BUTTON}; font-size: 18px; font-family: 'DejaVu Sans'; border: none; padding: 4px; }}
            QPushButton:hover {{ color: {HOVER}; }}
        """)
        btn.clicked.connect(lambda _=False, l=latex: insert(l))
        grid.addWidget(btn, i // columns, i % columns)
    return grid_widget

class Sidebar(QWidget):
    def __init__(self, buttons, parent=None):
        super().__init__(parent)
        self.setAttribute(Qt.WA_StyledBackground)
        self.setStyleSheet(f"Sidebar {{ background-color: {SIDEBAR}; }}")

        content = QWidget()
        content.setStyleSheet(f"background-color: {SIDEBAR};")
        content_layout = QVBoxLayout(content)
        content_layout.setContentsMargins(10,10,10,10)
        content_layout.setSpacing(14)

        for label, item in buttons:
            if isinstance(item, QWidget):
                content_layout.addWidget(Dropdown(label, item))
                continue
            btn = QPushButton(label)
            btn.setFixedHeight(30)
            btn.setStyleSheet(f"{button_style}")
            btn.clicked.connect(item)
            content_layout.addWidget(btn)
        content_layout.addStretch()

        scroll = QScrollArea()
        scroll.setFixedWidth(SIDEBAR_WIDTH)
        scroll.setWidgetResizable(True)
        scroll.setHorizontalScrollBarPolicy(Qt.ScrollBarAlwaysOff)
        scroll.setFrameShape(QFrame.NoFrame)
        scroll.setStyleSheet(f"""
            * {{ background-color: {SIDEBAR}; border: none; }}
            QScrollBar:vertical {{
                background: {BG};
                width: 14px;
                border-radius: 5px;
                margin: 8px 4px 8px 0px;
            }}
            QScrollBar::handle:vertical {{
                background: {SCROLL};
                border-radius: 5px;
                min-height: 30px;
            }}
            QScrollBar::add-line:vertical, QScrollBar::sub-line:vertical {{ height: 0; }}
            QScrollBar::add-page:vertical, QScrollBar::sub-page:vertical {{ background: none; }}
        """)
        scroll.setWidget(content)

        self.panel = QWidget()
        self.panel.setMaximumWidth(0)
        sidebar_layout = QVBoxLayout(self.panel)
        sidebar_layout.setContentsMargins(0,0,0,0)
        sidebar_layout.addWidget(scroll)

        arrow = QIcon(str(ASSETS_DIR / "Arrow.svg")).pixmap(64,64)
        arrow_hover = QIcon(str(ASSETS_DIR / "Arrow_Hover.svg")).pixmap(64,64)
        flip = QTransform().rotate(180)
        arrow_icon = QIcon()
        arrow_icon.addPixmap(arrow.transformed(flip), QIcon.Normal, QIcon.Off)
        arrow_icon.addPixmap(arrow_hover.transformed(flip), QIcon.Active, QIcon.Off)
        arrow_icon.addPixmap(arrow, QIcon.Normal, QIcon.On)
        arrow_icon.addPixmap(arrow_hover, QIcon.Active, QIcon.On)

        self.handle = QToolButton()
        self.handle.setIcon(arrow_icon)
        self.handle.setAutoRaise(True)
        self.handle.setIconSize(QSize(20,20))
        self.handle.setCheckable(True)
        self.handle.setChecked(True)
        self.handle.setFixedWidth(24)
        self.handle.setSizePolicy(QSizePolicy.Fixed, QSizePolicy.Expanding)
        self.handle.setStyleSheet(f"""
            QToolButton {{
                background-color: {SIDEBAR};
                border: none;
            }}
        """)
        self.handle.toggled.connect(self.toggle_sidebar)

        self.anim = QPropertyAnimation(self.panel, b"maximumWidth", self)
        self.anim.setDuration(250)
        self.anim.setEasingCurve(QEasingCurve.OutCubic)
        self.anim.valueChanged.connect(self.relayout)

        layout = QHBoxLayout(self)
        layout.setContentsMargins(0,0,0,0)
        layout.setSpacing(0)
        layout.addWidget(self.panel)
        layout.addWidget(self.handle)
        for widget in self.findChildren(QWidget):
            if not isinstance(widget, QLineEdit):
                widget.setFocusPolicy(Qt.NoFocus)


    def relayout(self):
        self.layout().activate()
        self.parentWidget().layout().activate()

    def toggle_sidebar(self, collapsed):
        self.anim.stop()
        self.anim.setStartValue(self.panel.maximumWidth())
        self.anim.setEndValue(0 if collapsed else SIDEBAR_WIDTH)
        self.anim.start()

class PanelPage(QWidget):
    def __init__(self, keys, icon, parent=None):
        super().__init__(parent)
        self.keys = keys
        self.panels = {}
        self.logo = QIcon(str(ASSETS_DIR / icon))

        self.canvas = QWidget()
        self.canvas.setStyleSheet(f"background-color: {BG};")
        self.canvas.installEventFilter(self)

        sidebar = Sidebar([(PANELS[key].label, lambda _=False, k=key: self.show_panel(k)) for key in keys])

        layout = QHBoxLayout(self)
        layout.setContentsMargins(0,0,0,0)
        layout.setSpacing(0)
        layout.addWidget(sidebar)
        layout.addWidget(self.canvas, stretch=1)

    def show_panel(self, key):
        panel = self.panels.get(key)
        if panel is None:
            spec = PANELS[key]
            help_text = HELPTEXT[key] + SUB_HELP if key in HELPTEXT else None
            panel = DraggablePanel(spec.title, spec.build(), self.canvas, help_text)
            panel.resize(spec.size[0], panel.height())
            offset = 20 * len(self.panels)
            panel.move(20 + offset, 20 + offset)
            self.panels[key] = panel
            panel.fit_to_parent()

        panel.show()
        panel.raise_()

    def eventFilter(self, obj, event):
        if obj is self.canvas and event.type() == QEvent.Resize:
            for panel in self.panels.values():
                panel.fit_to_parent()
        if obj is self.canvas and event.type() == QEvent.Paint:
            margin = min(self.canvas.width(), self.canvas.height()) // 4
            painter = QPainter(self.canvas)
            painter.setOpacity(0.05)
            self.logo.paint(painter, self.canvas.rect().adjusted(margin, margin, -margin, -margin))
            painter.end()
        return super().eventFilter(obj, event)

class MainWindow(QMainWindow):
    def __init__(self, parent=None):
        super().__init__(parent)

        load_dict_from_settings("pKa_values", pKa_values)
        load_dict_from_settings("pKb_values", pKb_values)

        self.gen = 1
        self.close_confirmed = False

        self.setWindowTitle("Carbon")
        self.setWindowIcon(QIcon(str(ASSETS_DIR / "Carbon_Round.svg")))
        if sys.platform == "darwin":
            self.setWindowFlags(self.windowFlags() | Qt.ExpandedClientAreaHint | Qt.NoTitleBarBackgroundHint)
            self.setAttribute(Qt.WA_ContentsMarginsRespectsSafeArea, False)
        else:
            self.setWindowFlag(Qt.FramelessWindowHint)

        self.setStyleSheet(f"background-color: {BG};")
        self.setMinimumWidth(600)

        self.stack = QStackedWidget()
        self.slide_anim = QParallelAnimationGroup(self)
        self.slide_anim.finished.connect(self.slide_finished)
        self.setCentralWidget(self.stack)

        self.create_header()
        self.create_mainmenu()
        self.create_interpreter_page()
        self.create_molecule_page()
        self.kemi_page = PanelPage([
            "unit",
            "pH",
            "balance",
            "analysis",
            "bjerrum",
            "udbytteprocent",
            "volumenprocent",
            "masseprocent",
            "mængdeberegning",
            "puffer",
            "h3o"],
            "Kemi_Icon.svg")
        self.fysik_page = PanelPage([
            "unit"],
            "Fysik_Icon.svg")
        self.biotek_page = PanelPage([
            "unit",
            "dna_peptid",
            "rna_peptid",
            "mutation"],
            "Biotek_Icon.svg")
        self.stack.addWidget(self.kemi_page)
        self.stack.addWidget(self.fysik_page)
        self.stack.addWidget(self.biotek_page)
        self.create_periodic_page()
        self.create_drawer()
        self.create_search()
        self.create_settings_page()

        self.history = [self.stack.currentWidget()]
        self.history_index = 0
        self.update_nav()

        self.update_page_title(self.stack.currentIndex())

        self.version_label = QLabel(version, self)
        self.version_label.setStyleSheet(f"color: {BUTTON}; font-size: 10px; background: transparent;")
        self.version_label.setAttribute(Qt.WA_TransparentForMouseEvents)

        self.create_changelog()
        if _settings.value("changelog_seen") != version:
            self.open_changelog(quiet=True)

        point_cursor(self)

    def create_changelog(self):
        self.changelog = QWidget(self)
        self.changelog.setStyleSheet("background-color: rgba(0, 0, 0, 120);")
        self.changelog.setAttribute(Qt.WA_NoMousePropagation)
        self.changelog.hide()
        overlay = QVBoxLayout(self.changelog)

        card = QFrame()
        card.setObjectName("card")
        card.setStyleSheet(f"QFrame#card {{ background-color: {BG}; border-radius: 8px; }}")
        card.setFixedSize(420, 360)
        overlay.addWidget(card, alignment=Qt.AlignCenter)
        layout = QVBoxLayout(card)
        layout.setContentsMargins(0,0,0,0)
        layout.setSpacing(0)

        header = QWidget()
        header.setFixedHeight(28)
        header.setStyleSheet(f"""
            background-color: {HEADER};
            border-top-left-radius: 8px;
            border-top-right-radius: 8px;
        """)
        header_layout = QHBoxLayout(header)
        header_layout.setContentsMargins(8, 0, 4, 0)
        title = QLabel(f"Nyheder i Carbon {version}")
        title.setStyleSheet(f"color: {BUTTON}; font-weight: bold; border: none;")
        header_layout.addWidget(title)
        header_layout.addStretch()
        close_btn = QPushButton("x")
        close_btn.setFixedSize(20, 20)
        close_btn.setStyleSheet(f"""
            QPushButton {{ background: transparent; border: none; color: {BUTTON}; font-weight: bold; font-size: 14px; }}
            QPushButton:hover {{ color: {HOVER}; }}
        """)
        close_btn.clicked.connect(self.close_changelog)
        QShortcut(QKeySequence(Qt.Key_Escape), self.changelog, self.close_changelog, Qt.WidgetWithChildrenShortcut)
        header_layout.addWidget(close_btn)
        layout.addWidget(header)

        body = QVBoxLayout()
        body.setContentsMargins(6,6,6,6)
        self.changelog_text = TextOutput()
        body.addWidget(self.changelog_text)
        layout.addLayout(body)

        self.network = QNetworkAccessManager(self)

    def open_changelog(self, quiet=False):
        reply = self.network.get(QNetworkRequest(QUrl(CHANGELOG_URL)))
        reply.finished.connect(lambda: self.show_changelog(reply, quiet))

    def show_changelog(self, reply, quiet=False):
        text = bytes(reply.readAll()).decode("utf-8", "replace")
        reply.deleteLater()
        self.changelog_ok = reply.error() == QNetworkReply.NoError and text.lstrip().startswith(("#", "-"))
        if quiet and not self.changelog_ok:
            return
        self.changelog_text.setMarkdown(text if self.changelog_ok else "Kunne ikke hente nyheder")
        self.changelog.setGeometry(self.rect())
        self.changelog.show()
        self.changelog.raise_()
        self.changelog.grabKeyboard()

    def close_changelog(self):
        self.changelog.releaseKeyboard()
        self.changelog.hide()
        if self.changelog_ok:
            _settings.setValue("changelog_seen", version)

    def create_drawer(self):
        self.drawer_max_width = 270
        self.drawer_open = False

        self.drawer = QFrame(self)
        self.drawer.setStyleSheet(f"background-color: {SCROLL};")
        
        outer = QVBoxLayout(self.drawer)
        outer.setContentsMargins(0,0,0,0)

        scroll = QScrollArea()
        scroll.setWidgetResizable(True)
        scroll.setHorizontalScrollBarPolicy(Qt.ScrollBarAlwaysOff)
        scroll.setFrameShape(QFrame.NoFrame)
        scroll.setStyleSheet(f"""
            QScrollArea {{ background: transparent; border: none; }}
            QScrollBar:vertical {{
                background: transparent;
                width: 8px;
            }}
            QScrollBar::handle:vertical {{
                background: {SIDEBAR};
                border-radius: 4px;
                min-height: 30px;
            }}
            QScrollBar::add-line:vertical, QScrollBar::sub-line:vertical {{ height: 0; }}
            QScrollBar::add-page:vertical, QScrollBar::sub-page:vertical {{ background: none; }}
        """)
        outer.addWidget(scroll)

        content = QWidget()
        content.setStyleSheet("background: transparent;")
        layout = QVBoxLayout(content)

        items = [
            ("Hovedmenu", self.open_menu, None),
            ("Regneark", self.open_interpreter, None),
            ("Molekyletegner", self.open_molecule, None),
            ("Kemi", self.open_kemi, self.kemi_page),
            ("Fysik", self.open_fysik, self.fysik_page),
            ("Biotek", self.open_biotek, self.biotek_page),
            ("Periodisk system", self.open_periodic, None),
            ("Indstillinger", self.open_settings, None),
            ("Nyheder", self.open_changelog, None),
            ("Afslut", self.close_app, None),
        ]

        self.drawer_items = items

        style = f"""
                QPushButton {{
                    color: white;
                    text-align: left;
                    padding: 8px;
                    border: none;
                    border-radius: 8px;
                    background: transparent;
                }}
                QPushButton:hover {{
                    background-color: {HEADER};
                }}
            """

        arrow = QIcon(str(ASSETS_DIR / "Arrow.svg")).pixmap(64,64)
        arrow_hover = QIcon(str(ASSETS_DIR / "Arrow_Hover.svg")).pixmap(64,64)
        up = QTransform().rotate(-90)
        down = QTransform().rotate(90)
        expand_icon = QIcon()
        expand_icon.addPixmap(arrow.transformed(up), QIcon.Normal, QIcon.Off)
        expand_icon.addPixmap(arrow_hover.transformed(up), QIcon.Active, QIcon.Off)
        expand_icon.addPixmap(arrow.transformed(down), QIcon.Normal, QIcon.On)
        expand_icon.addPixmap(arrow_hover.transformed(down), QIcon.Active, QIcon.On)

        for text, callback, page in items:
            btn = QPushButton(text)
            btn.setStyleSheet(style + "QPushButton { font-weight: bold; }")
            btn.clicked.connect(callback)
            btn.clicked.connect(self.toggle_drawer)
            if page is None:
                layout.addWidget(btn)
                continue

            expand = QToolButton()
            expand.setIcon(expand_icon)
            expand.setIconSize(QSize(14,14))
            expand.setCheckable(True)
            expand.setAutoRaise(True)
            expand.setStyleSheet("QToolButton { background: transparent; border: none; }")

            row = QHBoxLayout()
            row.addWidget(btn)
            row.addWidget(expand)
            layout.addLayout(row)

            panel_list = QWidget()
            panel_layout = QVBoxLayout(panel_list)
            panel_layout.setContentsMargins(20,0,0,0)
            for key in page.keys:
                panel_btn = QPushButton(PANELS[key].label)
                panel_btn.setStyleSheet(style)
                panel_btn.clicked.connect(lambda _=False, p=page, k=key: self.open_panel(p, k))
                panel_btn.clicked.connect(self.toggle_drawer)
                panel_layout.addWidget(panel_btn)
            panel_list.hide()
            expand.toggled.connect(panel_list.setVisible)
            layout.addWidget(panel_list)
        layout.addStretch()

        scroll.setWidget(content)

        self.drawer.hide()
        self.drawer_anim = QPropertyAnimation(self.drawer, b"pos")
        self.drawer_anim.setDuration(250)
        self.drawer_anim.setEasingCurve(QEasingCurve.OutCubic)
        self.drawer_anim.finished.connect(self.drawer_finished)

    def eventFilter(self, obj, event):
        if obj is self.header_container:
            if event.type() == event.Type.MouseButtonPress and event.button() == Qt.LeftButton:
                self.windowHandle().startSystemMove()
                return True
            if event.type() == event.Type.MouseButtonDblClick:
                self.toggle_maximized()
                return True
            if event.type() == event.Type.Resize:
                self.place_page_title()

        if obj is self.search and self.suggest.isVisible():
            if event.type() == event.Type.KeyPress:
                if event.key() in (Qt.Key_Up, Qt.Key_Down):
                    step = 1 if event.key() == Qt.Key_Down else -1
                    self.suggest.setCurrentRow((self.suggest.currentRow() + step) % self.suggest.count())
                    return True
                if event.key() == Qt.Key_Tab:
                    self.run_search()
                    return True
                if event.key() == Qt.Key_Escape:
                    self.suggest.hide()
                    return True
            elif event.type() == event.Type.FocusOut:
                self.suggest.hide()
        return super().eventFilter(obj, event)

    def toggle_drawer(self):
        top = self.toolbar.height()
        w = min(self.drawer_max_width, self.width())
        h = self.height() - top
        x = self.width() - w                      
        self.drawer.setFixedSize(w, h)

        shown = QPoint(x, top)
        hidden = QPoint(x, top - h)

        if not self.drawer_open:
            self.drawer.move(hidden)
            self.drawer.show()
            self.drawer.stackUnder(self.toolbar)
            self.drawer_anim.setStartValue(hidden)
            self.drawer_anim.setEndValue(shown)
        else:
            self.drawer_anim.setStartValue(shown)
            self.drawer_anim.setEndValue(hidden)

        self.drawer_open = not self.drawer_open
        self.drawer_anim.start()

    def drawer_finished(self):
        if not self.drawer_open:
            self.drawer.hide()

    def resizeEvent(self, event):
        super().resizeEvent(event)
        self.version_label.adjustSize()
        self.version_label.move(
            self.width() - self.version_label.width() - 5,
            self.height() - self.version_label.height() - 1,
        )
        if getattr(self, "drawer_open", False):
            top = self.toolbar.height()
            w = min(self.drawer_max_width, self.width())
            h = self.height() - top
            self.drawer.setFixedSize(w, h)
            self.drawer.move(self.width() - w, top)
        if hasattr(self, "changelog"):
            self.changelog.setGeometry(self.rect())


    def create_header(self):
        self.toolbar = QToolBar("Header")
        self.addToolBar(self.toolbar)
        self.toolbar.setStyleSheet(f"""
                QToolBar {{
                    background-color: {HEADER};
                    border: none;
                }}
                QToolButton {{
                    background-color: {HEADER};
                    border: none;
                }}
            """)
        self.toolbar.setIconSize(QSize(50, 50))
        self.toolbar.setFixedHeight(75)
        self.toolbar.setMovable(False)

        container = QWidget()
        container.setStyleSheet(f"background-color: {HEADER};")
        self.header_container = container
        outer = QVBoxLayout(container)
        outer.setContentsMargins(0,0,0,0)
        outer.setSpacing(0)

        window_row = QHBoxLayout()
        window_row.setSpacing(0)
        outer.addLayout(window_row)

        layout = QHBoxLayout()
        layout.setContentsMargins(5,0,0,0)
        layout.setSpacing(15)
        outer.addLayout(layout)

        self.page_buttons = QButtonGroup(self)

        def make_button(icon_path, tooltip, callback, page=None):
            btn = QToolButton()
            btn.setIcon(hover_icon(icon_path))
            btn.setAutoRaise(True)
            btn.setIconSize(QSize(32, 32))
            btn.setToolTip(tooltip)
            btn.clicked.connect(callback)
            btn.setStyleSheet(f"""
                    QToolButton {{
                        background-color: {HEADER};
                        border: none;
                        border-bottom: 3px solid transparent;
                        padding: 6px;
                    }}
                    QToolButton:checked {{
                        border-bottom: 3px solid {BUTTON};
                    }}
                    QToolTip {{
                    background-color: {BUTTON};
                    color: {TEXT};
                    border: 1px solid {HEADER};
                    }}
                """)
            if page is not None:
                btn.setCheckable(True)
                self.page_buttons.addButton(btn, page)
            return btn

        self.back_btn = make_button("Pointer.svg", "Tilbage", lambda: self.go_history(-1))
        self.forward_btn = make_button("Pointer.svg", "Frem", lambda: self.go_history(1))
        self.back_btn.setIcon(nav_icon(False))
        self.forward_btn.setIcon(nav_icon(True))
        min_btn = make_button("Minimize.svg", "Minimer", self.showMinimized)
        self.max_btn = make_button("Maximize.svg", "Maksimer", self.toggle_maximized)
        close_btn = make_button("Close.svg", "Luk", self.close)
        for btn in (self.back_btn, self.forward_btn, min_btn, self.max_btn, close_btn):
            btn.setIconSize(QSize(10,10))
            btn.setCursor(Qt.ArrowCursor)
            hover = "#da373c" if btn is close_btn else f"{SCROLL}"
            btn.setStyleSheet(f"""
                QToolButton {{ background-color: {HEADER}; border: none; padding: 8px 14px; }}
                QToolButton:hover {{ background-color: {hover}; }}
                QToolTip {{
                    background-color: {BUTTON};
                    color: {TEXT};
                    border: 1px solid {HEADER};
                }}
            """)
            window_row.addWidget(btn)
            if btn is self.forward_btn:
                window_row.addStretch()
        if sys.platform == "darwin":
            for btn in (min_btn, self.max_btn, close_btn):
                btn.hide()

        self.page_title = QToolButton(container)
        self.page_title.setToolButtonStyle(Qt.ToolButtonTextBesideIcon)
        self.page_title.setIconSize(QSize(16,16))
        self.page_title.setAttribute(Qt.WA_TransparentForMouseEvents)
        self.page_title.setStyleSheet(f"QToolButton {{ background: transparent; border: none; color: {BUTTON}; font-weight: bold; }}")

        layout.addWidget(
            make_button("Carbon_Borderless_transparent.svg", "Hovedmenu", self.open_menu, 0)
        )
        layout.addStretch()

        layout.addWidget(
            make_button("Interpreter_Icon.svg", "Regneark", self.open_interpreter, 1)
        )
        layout.addStretch()

        layout.addWidget(
            make_button("Marvin_Icon.svg", "Molekyletegner", self.open_molecule, 2)
        )
        layout.addStretch()

        layout.addWidget(
            make_button("Kemi_Icon.svg","Kemi", self.open_kemi, 3)
        )
        layout.addStretch()

        layout.addWidget(
            make_button("Fysik_Icon.svg", "Fysik", self.open_fysik, 4)
        )
        layout.addStretch()
        
        layout.addWidget(
            make_button("Biotek_Icon.svg", "Biotek", self.open_biotek, 5)
        )
        layout.addStretch()

        layout.addWidget(
            make_button("Periodisk_Icon.svg", "Periodisk system", self.open_periodic, 6)
        )
        layout.addStretch()

        self.search = QLineEdit()
        self.search.setPlaceholderText("Søg her...")
        self.search.setFixedWidth(200)
        self.search.setStyleSheet(f"""
            QLineEdit {{
                background-color: {BUTTON};
                color: {TEXT};
                border: none;
                border-radius: 8px;
                padding: 4px 10px;
            }}
        """)
        self.search.returnPressed.connect(self.run_search)
        layout.addWidget(self.search)

        layout.addWidget(
            make_button("Burger_Menu.svg", "", self.toggle_drawer)
        )

        self.toolbar.addWidget(container)
        container.installEventFilter(self)
        self.stack.currentChanged.connect(self.update_page_button)
    
    def create_search(self):
        self.search_targets = {}
        for text, callback, page in self.drawer_items:
            if callback == self.close_app:
                continue
            self.search_targets[text] = callback
            for key in page.keys if page else []:
                self.search_targets[f"{PANELS[key].label} ({text})"] = lambda p=page, k=key: self.open_panel(p, k)

        self.suggest = QListWidget(self)
        self.suggest.setFocusPolicy(Qt.NoFocus)
        self.suggest.setHorizontalScrollBarPolicy(Qt.ScrollBarAlwaysOff)
        self.suggest.setCursor(Qt.PointingHandCursor)
        self.suggest.setStyleSheet(f"""
            QListWidget {{
                background-color: {SIDEBAR};
                border: none;
                border-radius: 8px;
                padding: 4px;
                font: 14px "Segoe UI";
                outline: none;
            }}
            QListWidget::item {{
                color: {BUTTON};
                padding: 3px 10px;
                border-radius: 4px;
            }}
            QListWidget::item:selected {{ background-color: {BG}; }}
            QScrollBar:vertical {{ background: transparent; width: 6px; }}
            QScrollBar::handle:vertical {{ background: {BG}; border-radius: 3px; }}
            QScrollBar::add-line:vertical, QScrollBar::sub-line:vertical {{ height: 0; }}
            QScrollBar::add-page:vertical, QScrollBar::sub-page:vertical {{ background: none; }}
        """)
        self.suggest.itemClicked.connect(self.run_search)
        self.suggest.hide()

        self.search.textChanged.connect(self.update_search)
        self.search.installEventFilter(self)

    def update_search(self, text):
        text = text.strip().lower()
        self.suggest.clear()
        if text:
            self.suggest.addItems([t for t in self.search_targets if text in t.lower()])
        if not self.suggest.count():
            self.suggest.hide()
            return
        self.suggest.setCurrentRow(0)
        rows = min(self.suggest.count(), 7)
        self.suggest.setFixedSize(self.search.width(), rows * self.suggest.sizeHintForRow(0) + 8)
        self.suggest.move(self.search.mapTo(self, QPoint(0, self.search.height())))
        self.suggest.show()
        self.suggest.raise_()

    def run_search(self):
        item = self.suggest.currentItem()
        if not self.suggest.isVisible() or item is None:
            return
        self.search_targets[item.text()]()
        self.search.clear()

    def update_page_title(self, i):
        btn = self.page_buttons.button(i)
        self.page_title.setIcon(btn.icon() if btn else self.stack.widget(i).windowIcon())
        self.page_title.setText(btn.toolTip() if btn else self.stack.widget(i).windowTitle())
        self.page_title.adjustSize()
        self.place_page_title()

    def update_page_button(self, i):
        self.page_buttons.setExclusive(False)
        for btn in self.page_buttons.buttons():
            btn.setChecked(btn is self.page_buttons.button(i))
        self.page_buttons.setExclusive(True)

    def place_page_title(self):
        self.page_title.move(
            (self.header_container.width() - self.page_title.width()) // 2,
            self.header_container.layout().contentsMargins().top() + (self.max_btn.sizeHint().height() - self.page_title.height()) // 2,
        )


    def toggle_maximized(self):
        if self.isMaximized() or self.isFullScreen():
            self.showNormal()
        else:
            self.showMaximized()

    def fit_safe_area(self, margins):
        self.header_container.layout().setContentsMargins(margins.left(), margins.top(), margins.right(), 0)
        self.toolbar.setFixedHeight(75 + margins.top())

    def event(self, event):
        if event.type() == QEvent.WinIdChange and sys.platform == "win32":
            hwnd = int(self.winId())
            user32.SetWindowLongPtrW(hwnd, GWL_STYLE, user32.GetWindowLongPtrW(hwnd, GWL_STYLE) | WS_FRAME_STYLES)
            user32.SetWindowPos(hwnd, None, 0, 0, 0, 0, SWP_FRAMECHANGED)
        if event.type() == QEvent.WinIdChange and sys.platform == "darwin":
            self.windowHandle().safeAreaMarginsChanged.connect(self.fit_safe_area, Qt.UniqueConnection)
            self.fit_safe_area(self.windowHandle().safeAreaMargins())
        return super().event(event)

    def nativeEvent(self, event_type, message):
        if bytes(event_type) != b"windows_generic_MSG":
            return False, 0
        msg = MSG.from_address(int(message))
        if msg.message == WM_NCCALCSIZE and msg.wParam:
            if user32.IsZoomed(msg.hwnd):
                info = MONITORINFO(cbSize=ctypes.sizeof(MONITORINFO))
                user32.GetMonitorInfoW(user32.MonitorFromWindow(msg.hwnd, 2), ctypes.byref(info))
                ctypes.memmove(msg.lParam, ctypes.byref(info.rcWork), ctypes.sizeof(RECT))
            return True, 0
        if msg.message == WM_NCHITTEST:
            if self.isFullScreen():
                return True, HTCLIENT
            pos, r, m = QCursor.pos(), self.frameGeometry(), 6
            edges = (pos.x() < r.left() + m, pos.x() > r.right() - m, pos.y() < r.top() + m, pos.y() > r.bottom() - m)
            if edges in HIT_TEST and not self.isMaximized():
                return True, HIT_TEST[edges]
            if self.childAt(self.mapFromGlobal(pos)) in (self.toolbar, self.header_container):
                return True, HTCAPTION
            return True, HTCLIENT
        return False, 0



    def changeEvent(self, event):
        super().changeEvent(event)
        if event.type() == event.Type.WindowStateChange:
            maximized = self.isMaximized() or self.isFullScreen()
            self.max_btn.setIcon(hover_icon("Restore.svg" if maximized else "Maximize.svg"))
            self.max_btn.setToolTip("Gendan" if maximized else "Maksimer")

    def create_mainmenu(self):
        central = QWidget()

        layout = QVBoxLayout(central)
        layout.setContentsMargins(40,40,40,40)

        logo = QSvgWidget(str(ASSETS_DIR / "Carbon_Full.svg"))
        logo.renderer().setAspectRatioMode(Qt.KeepAspectRatio)
        logo.setSizePolicy(QSizePolicy.Expanding, QSizePolicy.Expanding)
        logo.setMaximumSize(1000,411)
        logo.setMinimumSize(100,41)

        row = QHBoxLayout()
        row.addStretch(1)
        row.addWidget(logo, 100)
        row.addStretch(1)

        layout.addStretch(1)
        layout.addLayout(row, 100)
        layout.addStretch(1)
        
        self.stack.addWidget(central)

    def create_interpreter_page(self):
        page = QWidget()
        page.setStyleSheet(f"background-color: {BG};")
        layout = QHBoxLayout(page)
        layout.setContentsMargins(0, 0, 0, 0)
        layout.setSpacing(0)

        def insert(latex):
            self.interpreter_view.page().runJavaScript(f"insertLatex({json.dumps(latex)})")

        layout.addWidget(Sidebar([
            ("Calculus", symbol_grid([
                ("∫", r"\int #?\,\differentialD #?"),
                ("Integral_ab.svg", r"\int_{#?}^{#?}#?\,\differentialD #?"),
                ("Ddx.svg", r"\frac{\differentialD}{\differentialD #?}\left(#?\right)"),
                ("lim", r"\lim_{#?\to#?}\left(#?\right)"),
                ("Σ", r"\sum_{#?=#?}^{#?}\left(#?\right)"),
            ], insert)),
            ("Græsk", symbol_grid([(char, "\\" + name) for name, char in GREEK.items()], insert)),
            ("Vektorer",symbol_grid([
                ("a\u20D7",r"\vec{#?}"),
                ("a\u20D7 =",r"\vec{#?}=\left\lbrace#?\right\rbrace"),
                ("a\u20D7×b\u20D7",r"\vec{#?}\times\vec{#?}"),
                ("a\u20D7·b\u20D7",r"\vec{#?}\cdot\vec{#?}"),
                ("a\u20D7+b\u20D7",r"\vec{#?}+\vec{#?}"),
                ("a\u20D7−b\u20D7",r"\vec{#?}-\vec{#?}"),
                ("k·a\u20D7",r"{#?}\cdot\vec{#?}"),
                ("Det(a\u20D7)",r"\operatorname{Det}(\vec{#?})"),
                ("|a\u20D7|",r"\lvert\vec{#?}\rvert"),
                ("e\u20D7<sub>a\u20D7</sub>",r"\vec{\mathnormal{e}}_{\vec{#?}}"),
                ("∠(a\u20D7,b\u20D7)",r"\angle(\vec{#?},\vec{#?})"),
                ("Tvaervektor.svg",r"\!\vec{\:\hat{#?}}"),
                ("b\u20D7<sub>a\u20D7</sub>",r"\vec{#?}_{\vec{#?}}"),





            ],insert,3))
        ]))

        bar = QWidget()
        bar.setStyleSheet(f"background-color: {SCROLL};")
        bar_layout = QHBoxLayout(bar)
        bar_layout.setContentsMargins(10,4,10,4)

        self.line_type = SegmentedControl([
            ("Matematik", "math", "Ctrl+1"),
            ("Tekst", "text", "Ctrl+2"),
            ("Formel", "formula", "Regnes ikke (Ctrl+3)"),
        ])
        self.line_type.changed.connect(lambda mode: self.interpreter_view.page().runJavaScript(f"setMode({json.dumps(mode)})"))
        self.undo_btn = QToolButton()
        self.redo_btn = QToolButton()
        for btn, mirror, tip, js in ((self.undo_btn, False, "Fortryd (Ctrl+Z)", "undo()"), (self.redo_btn, True, "Gentag (Ctrl+Y)", "redo()")):
            btn.setIcon(nav_icon(mirror))
            btn.setIconSize(QSize(14, 14))
            btn.setToolTip(tip)
            btn.setFocusPolicy(Qt.NoFocus)
            btn.setEnabled(False)
            btn.setStyleSheet(f"""
                QToolButton {{ border: none; padding: 4px; }}
                QToolButton:hover {{ background: {SIDEBAR}; border-radius: 3px; }}
                QToolTip {{ background-color: {BUTTON}; color: {TEXT}; border: 1px solid {HEADER}; }}
            """)
            btn.clicked.connect(lambda _=False, js=js: self.interpreter_view.page().runJavaScript(js))
            bar_layout.addWidget(btn)
        bar_layout.addWidget(self.line_type)

        self.text_tools = QWidget()
        tools = QHBoxLayout(self.text_tools)
        tools.setContentsMargins(12, 0, 0, 0)
        tools.setSpacing(2)
        js = lambda code: self.interpreter_view.page().runJavaScript(code)
        tool_style = f"""
            QToolButton {{ border: none; padding: 2px 6px; color: {BUTTON}; font-size: 14px; }}
            QToolButton:hover {{ background: {BG}; border-radius: 3px; }}
            QToolButton:checked {{ background: {SIDEBAR}; border-radius: 3px; }}
            QToolButton:disabled {{ color: {SIDEBAR}; }}
            QToolButton::menu-indicator {{ image: none; }}
            QToolTip {{ background-color: {BUTTON}; color: {TEXT}; border: 1px solid {HEADER}; }}
        """
        menu_style = f"""
            QMenu {{ background-color: {BUTTON}; color: {TEXT}; border: none; }}
            QMenu::item {{ padding: 6px 20px; }}
            QMenu::item:selected {{ background-color: {HOVER}; }}
        """
        self.size_box = QLineEdit("18")
        self.size_box.setAlignment(Qt.AlignCenter)
        self.size_box.setFixedWidth(30)
        self.size_box.setSizePolicy(QSizePolicy.Fixed, QSizePolicy.Fixed)
        self.size_box.setValidator(QIntValidator(8, 48, self.size_box))
        self.size_box.setStyleSheet(f"""
            QLineEdit {{ color: {BUTTON}; background: transparent; border: 1px solid {BUTTON}; border-radius: 3px; }}
            QLineEdit:disabled {{ color: {SIDEBAR}; border-color: {SIDEBAR}; }}
        """)

        def set_size(size):
            self.interpreter_view.page().runJavaScript(f"setSize({size})", 0, lambda size: self.size_box.setText(str(int(size))))

        def type_size():
            set_size(int(self.size_box.text()))
            self.focus_interpreter()

        self.size_box.returnPressed.connect(type_size)

        def pick_color(prop, title):
            dialog = QColorDialog(Qt.white, self)
            dialog.setWindowTitle(title)
            dialog.setStyleSheet(f"""
                QPushButton {{ background-color: {BUTTON}; color: {TEXT}; padding: 6px 14px; border: none; border-radius: 8px; }}
                QPushButton:hover {{ background-color: {HOVER}; }}
            """)
            if dialog.exec():
                js(f"format({json.dumps({prop: dialog.selectedColor().name()})})")

        def tool(text, tip, style=""):
            btn = QToolButton()
            btn.setText(text)
            btn.setToolTip(tip)
            btn.setFocusPolicy(Qt.NoFocus)
            btn.setStyleSheet(tool_style + f"QToolButton {{ {style} }}")
            tools.addWidget(btn)
            return btn

        def color_menu(btn, prop, title):
            menu = QMenu(btn)
            menu.setStyleSheet(menu_style)
            menu.addAction("Vælg farve…", lambda: pick_color(prop, title))
            menu.addAction("Ingen farve", lambda: js(f"format({json.dumps({prop: 'none'})})"))
            btn.setMenu(menu)
            btn.setPopupMode(QToolButton.InstantPopup)

        tool("−", "Mindre tekst").clicked.connect(lambda: set_size(int(self.size_box.text() or 18) - 1))
        tools.addWidget(self.size_box)
        tool("+", "Større tekst").clicked.connect(lambda: set_size(int(self.size_box.text() or 18) + 1))
        self.bold_btn = tool("B", "Fed (Ctrl+B)", "font-weight: bold;")
        self.bold_btn.setCheckable(True)
        self.bold_btn.clicked.connect(lambda: js("format({fontSeries: 'b'}, 'toggle')"))
        self.italic_btn = tool("I", "Kursiv (Ctrl+I)", "font-style: italic;")
        self.italic_btn.setCheckable(True)
        self.italic_btn.clicked.connect(lambda: js("format({fontShape: 'it'}, 'toggle')"))
        def icon_tool(name, tip):
            btn = tool("", tip, "padding: 4px 6px 0px 6px;")
            btn.icon_name = name
            btn.default_icon = QIcon(str(ASSETS_DIR / f"{name}.svg"))
            btn.default_icon.addFile(str(ASSETS_DIR / f"{name}_Disabled.svg"), QSize(), QIcon.Disabled)
            btn.setIcon(btn.default_icon)
            btn.setIconSize(QSize(16, 16))
            return btn

        self.color_btn = icon_tool("Text_Color", "Tekstfarve")
        color_menu(self.color_btn, "color", "Tekstfarve")
        self.marker_btn = icon_tool("Highlighter", "Fremhævning")
        color_menu(self.marker_btn, "backgroundColor", "Fremhævningsfarve")
        bar_layout.addWidget(self.text_tools)
        insert_btn = QToolButton()
        insert_btn.setText("Indsæt")
        insert_btn.setToolTip("Indsæt")
        insert_btn.setFocusPolicy(Qt.NoFocus)
        insert_btn.setPopupMode(QToolButton.InstantPopup)
        insert_menu = QMenu(insert_btn)
        insert_menu.setStyleSheet(menu_style)
        insert_menu.addAction("Sektion", lambda: (self.interpreter_view.page().runJavaScript("addSection()"), self.interpreter_view.setFocus()))
        insert_btn.setMenu(insert_menu)
        insert_btn.setStyleSheet(tool_style)
        bar_layout.addWidget(insert_btn)
        bar_layout.addStretch()

        file_btn = QToolButton()
        file_menu = QMenu(file_btn)
        file_menu.setStyleSheet(f"""
            QMenu {{ background-color: {BUTTON}; color: {TEXT}; border: none; }}
            QMenu::item {{ padding: 6px 20px; }}
            QMenu::item:selected {{ background-color: {HOVER}; }}
        """)
        file_menu.addAction("Åbn", self.open_regneark)
        file_menu.addAction("Gem", self.save_regneark)
        file_menu.addAction("Gem som", self.save_regneark_as)

        QShortcut(QKeySequence.Save, page, self.save_regneark, Qt.WidgetWithChildrenShortcut)
        QShortcut(QKeySequence.SaveAs, page, self.save_regneark_as, Qt.WidgetWithChildrenShortcut)
        QShortcut(QKeySequence.Open, page, self.open_regneark, Qt.WidgetWithChildrenShortcut)
        QShortcut(QKeySequence.AddTab, page, self.new_interpreter_tab, Qt.WidgetWithChildrenShortcut)
        QShortcut(QKeySequence.Close, page, lambda: self.close_interpreter_tab(self.interpreter_tabs.currentIndex()), Qt.WidgetWithChildrenShortcut)
        QShortcut(QKeySequence.NextChild, page, lambda: self.switch_tab(1), Qt.WidgetWithChildrenShortcut)
        QShortcut(QKeySequence.PreviousChild, page, lambda: self.switch_tab(-1), Qt.WidgetWithChildrenShortcut)
        
        file_btn.setIcon(hover_icon("Save.svg"))
        file_btn.setIconSize(QSize(24,24))
        file_btn.setToolTip("Fil")
        file_btn.setFocusPolicy(Qt.NoFocus)
        file_btn.setPopupMode(QToolButton.InstantPopup)
        file_btn.setMenu(file_menu)
        file_btn.setStyleSheet(f"""
            QToolButton {{ border: none; }}
            QToolButton::menu-indicator {{ image: none; }}
            QToolTip {{ background-color: {BUTTON}; color: {TEXT}; border: 1px solid {HEADER}; }}
        """)

        bar_layout.addWidget(file_btn)

        self.interpreter_tabs = QTabBar()
        self.interpreter_tabs.setExpanding(False)
        self.interpreter_tabs.setDrawBase(False)
        self.interpreter_tabs.setFocusPolicy(Qt.NoFocus)
        self.interpreter_tabs.setStyleSheet(f"""
            QTabBar::tab {{ background: {SIDEBAR}; border-top-left-radius: 6px; border-top-right-radius: 6px; padding: 0 0 5px 0; margin: 5px 2px 0 0; }}
            QTabBar::tab:selected {{ background: {BG}; margin-top: 0; padding-top: 5px; }}
        """)
        self.interpreter_tabs.currentChanged.connect(self.show_interpreter_tab)
        self.interpreter_tabs.tabBarDoubleClicked.connect(self.rename_tab)

        new_tab = QToolButton()
        new_tab.setText("+")
        new_tab.setToolTip("Ny side")
        new_tab.setFocusPolicy(Qt.NoFocus)
        new_tab.setStyleSheet(f"""
            QToolButton {{ color: {BUTTON}; border: none; font-size: 18px; font-weight: bold; padding: 0 8px; }}
            QToolButton:hover {{ color: {HOVER}; }}
            QToolTip {{ background-color: {BUTTON}; color: {TEXT}; border: 1px solid {HEADER}; }}
        """)
        new_tab.clicked.connect(self.new_interpreter_tab)

        tab_strip = QWidget()
        tab_strip.setStyleSheet(f"background-color: {SCROLL};")
        tab_row = QHBoxLayout(tab_strip)
        tab_row.setContentsMargins(4,0,0,0)
        tab_row.setSpacing(0)
        tab_row.addWidget(self.interpreter_tabs)
        tab_row.addWidget(new_tab)
        tab_row.addStretch()

        self.interpreter_stack = QStackedWidget()

        column = QVBoxLayout()
        column.setSpacing(0)
        column.addWidget(bar)
        column.addWidget(tab_strip)
        column.addWidget(self.interpreter_stack, stretch=1)
        layout.addLayout(column, stretch=1)

        self.new_interpreter_tab()
        self.stack.addWidget(page)

    @property
    def interpreter_view(self):
        return self.interpreter_stack.currentWidget()

    def new_interpreter_tab(self):
        name = self.new_file_name()
        view = QWebEngineView()
        view.page().setBackgroundColor(QColor(BG))
        channel = QWebChannel(view.page())
        bridge = _InterpreterBridge(view)
        bridge.modeChanged.connect(lambda mode: self.show_line_mode(mode) if view is self.interpreter_view else None)
        bridge.styleChanged.connect(lambda b, i, c, h: self.show_style(b, i, c, h) if view is self.interpreter_view else None)
        bridge.escaped.connect(self.restore_window)
        bridge.dirtyChanged.connect(lambda dirty: self.set_dirty(view, dirty))
        bridge.historyChanged.connect(lambda u, r: self.update_history_buttons(u, r) if view is self.interpreter_view else None)
        channel.registerObject("bridge", bridge)
        view.page().setWebChannel(channel)
        view.loadFinished.connect(lambda ok: self.interpreter_loaded(view))
        view.load(QUrl.fromLocalFile(str(resource_path("Assets_math_live/regneark.html"))))
        self.interpreter_stack.addWidget(view)
        index = self.interpreter_tabs.addTab("")
        self.set_tab_name(view, name)
        self.interpreter_tabs.setCurrentIndex(index)
        return view

    def new_file_name(self):
        names = [self.tab_name(i) for i in range(self.interpreter_tabs.count())]
        name, n = "Ny fil", 1
        while name in names:
            n += 1
            name = f"Ny fil {n}"
        return name

    def tab_name(self, index):
        return self.interpreter_tabs.tabButton(index, QTabBar.LeftSide).findChild(QLineEdit).text()

    def set_tab_name(self, view, name):
        pill = QLineEdit(name)
        pill.setAlignment(Qt.AlignCenter)
        pill.setFixedHeight(14)
        pill.setFocusPolicy(Qt.NoFocus)
        pill.setAttribute(Qt.WA_TransparentForMouseEvents)
        pill.setStyleSheet(f"background: {BUTTON}; color: {TEXT}; border: none; border-radius: 7px; font-size: 9px; padding: 0 8px;")
        self.fit_pill(pill)
        pill.textEdited.connect(lambda: self.resize_tab(pill))
        pill.editingFinished.connect(lambda: self.finish_rename(pill))
        pill.returnPressed.connect(self.focus_interpreter)

        escape = QShortcut(QKeySequence(Qt.Key_Escape), pill, lambda: (pill.setText(self.renaming), self.focus_interpreter()))
        escape.setContext(Qt.WidgetShortcut)

        close = QToolButton()
        close.setIcon(hover_icon("Close.svg"))
        close.setIconSize(QSize(8, 8))
        close.setFocusPolicy(Qt.NoFocus)
        close.setStyleSheet(f"""
            QToolButton {{ background: transparent; border: none; padding: 3px; }}
            QToolButton:hover {{ background: {SCROLL}; border-radius: 3px; }}
        """)
        close.clicked.connect(lambda: self.close_interpreter_tab(self.interpreter_stack.indexOf(view)))

        dot = QLabel()
        dot.setObjectName("dirty")
        dot.setFixedSize(6,6)
        dot.setStyleSheet(f"background: {BUTTON}; border-radius: 3px;")
        policy = dot.sizePolicy()
        policy.setRetainSizeWhenHidden(True)
        dot.setSizePolicy(policy)
        dot.setVisible(bool(view.property("dirty")))

        tab = QWidget()
        tab.setFixedHeight(20)
        tab_layout = QHBoxLayout(tab)
        tab_layout.setContentsMargins(6, 0, 0, 0)
        tab_layout.setSpacing(4)
        tab_layout.addWidget(pill)
        tab_layout.addWidget(dot)
        tab_layout.addWidget(close)

        index = self.interpreter_stack.indexOf(view)
        old = self.interpreter_tabs.tabButton(index, QTabBar.LeftSide)
        self.interpreter_tabs.setTabButton(index, QTabBar.LeftSide, tab)
        if old:
            old.deleteLater()
        self.fit_tabs()

    def set_dirty(self, view, dirty):
        view.setProperty("dirty", dirty)
        index = self.interpreter_stack.indexOf(view)
        if index < 0:
            return
        self.interpreter_tabs.tabButton(index, QTabBar.LeftSide).findChild(QLabel, "dirty").setVisible(dirty)

    def close_interpreter_tab(self, index):
        view = self.interpreter_stack.widget(index)
        if view is None:
            return
        self.remove_interpreter_tab(view, bool(view.property("dirty")))

    def ask_close(self, title, text, accept="Luk"):
        msg = QMessageBox(self)
        msg.setWindowTitle(title)
        msg.setText(text)
        msg.setIcon(QMessageBox.NoIcon)
        msg.setStyleSheet(f"""
            QMessageBox {{ background-color: {BG}; }}
            QLabel {{ color: {BUTTON}; }}
            QPushButton {{ background-color: {BUTTON}; color: {TEXT}; padding: 6px 14px; border: none; border-radius: 8px; }}
            QPushButton:hover {{ background-color: {HOVER}; }}
        """)
        close = msg.addButton(accept, QMessageBox.AcceptRole)
        msg.setDefaultButton(msg.addButton("Annuller",QMessageBox.RejectRole))
        msg.exec()
        return msg.clickedButton() is close

    def remove_interpreter_tab(self, view, used):
        if self.interpreter_stack.indexOf(view) < 0:
            return
        if used:
            self.interpreter_tabs.setCurrentIndex(self.interpreter_stack.indexOf(view))
        if used and not self.ask_close("Luk side", f"Vil du lukke {self.tab_name(self.interpreter_stack.indexOf(view))}?\nDet, der ikke er gemt, går tabt."):
            return
        view.findChild(_InterpreterBridge).pool.terminate()
        if self.interpreter_tabs.count() == 1:
            self.new_interpreter_tab()
        index = self.interpreter_stack.indexOf(view)
        self.interpreter_stack.removeWidget(view)
        self.interpreter_tabs.removeTab(index)
        view.deleteLater()
        self.fit_tabs()

    def fit_tabs(self):
        self.interpreter_tabs.setMaximumWidth(self.interpreter_tabs.sizeHint().width())

    def fit_pill(self, pill):
        pill.ensurePolished()
        pill.setFixedWidth(pill.fontMetrics().horizontalAdvance(pill.text()) + 21)

    def resize_tab(self, pill):
        self.fit_pill(pill)
        pill.parentWidget().adjustSize()
        self.interpreter_tabs.setIconSize(self.interpreter_tabs.iconSize())
        self.fit_tabs()

    def rename_tab(self, index):
        if index < 0:
            return
        self.interpreter_tabs.setCurrentIndex(index)
        pill = self.interpreter_tabs.tabButton(index, QTabBar.LeftSide).findChild(QLineEdit)
        self.renaming = pill.text()
        pill.setAttribute(Qt.WA_TransparentForMouseEvents, False)
        pill.setFocus()
        pill.selectAll()

    def finish_rename(self, pill):
        pill.setText(pill.text().strip() or self.renaming)
        pill.setAttribute(Qt.WA_TransparentForMouseEvents)
        self.resize_tab(pill)

    def show_line_mode(self, mode):
        self.line_type.setCurrent(mode)
        self.text_tools.setEnabled(mode == "text")
        if mode != "text":
            self.show_style(False, False)
        self.interpreter_view.page().runJavaScript("sizeOf(lastField ?? first)", 0, lambda size: self.size_box.setText(str(int(size))) if size else None)

    def show_interpreter_tab(self, index):
        self.interpreter_stack.setCurrentIndex(index)
        self.focus_interpreter()
        for i in range(self.interpreter_tabs.count()):
            tab = self.interpreter_tabs.tabButton(i, QTabBar.LeftSide)
            if tab:
                tab.layout().setContentsMargins(6, 0 if i == index else 4, 0, 0)
        if getattr(self.interpreter_view, "loaded", False):
            self.interpreter_view.page().runJavaScript("modeOf(lastField ?? first)", 0, lambda mode: self.show_line_mode(mode) if mode else None)
            self.interpreter_view.page().runJavaScript("JSON.stringify([undoStack.length > 0, redoStack.length > 0])", 0, lambda h: self.update_history_buttons(*(json.loads(h) if h else (False, False))))
            self.interpreter_view.page().runJavaScript("sendStyle(lastField ?? first)")

    def interpreter_loaded(self, view):
        view.loaded = True
        view.page().runJavaScript(f"setAccent({json.dumps(BUTTON)}); setBackground({json.dumps(BG)})")
        if view is self.interpreter_view:
            self.show_interpreter_tab(self.interpreter_tabs.currentIndex())

    def update_history_buttons(self, can_undo, can_redo):
        self.undo_btn.setEnabled(can_undo)
        self.redo_btn.setEnabled(can_redo)

    def show_style(self, bold, italic, color="", highlight=""):
        self.bold_btn.setChecked(bold)
        self.italic_btn.setChecked(italic)
        for btn, c in ((self.color_btn, color), (self.marker_btn, highlight)):
            if not c or c == "none":
                btn.setIcon(btn.default_icon)
                continue
            svg = (ASSETS_DIR / f"{btn.icon_name}.svg").read_text(encoding="utf-8")
            pix = QPixmap(64, 64)
            pix.fill(Qt.transparent)
            painter = QPainter(pix)
            QSvgRenderer(svg.replace('d="M3 22h18"', f'd="M3 22h18" stroke="{c}"').encode()).render(painter)
            painter.end()
            btn.setIcon(QIcon(pix))

    def switch_tab(self, step):
        self.interpreter_tabs.setCurrentIndex((self.interpreter_tabs.currentIndex() + step) % self.interpreter_tabs.count())

    def focus_interpreter(self):
        self.interpreter_view.setFocus()
        self.interpreter_view.page().runJavaScript("(lastField ?? first).focus()")

    def create_settings_page(self):
        language = QComboBox()
        language.addItem("Dansk")
        language.setFixedWidth(160)
        language.setStyleSheet(f"""
            QComboBox {{ background-color: {BUTTON}; color: {TEXT}; border: none; border-radius: 13px; padding: 4px 12px; }}
            QComboBox::drop-down {{ border: none; background: transparent; width: 28px; }}
            QComboBox::down-arrow {{ image: url({(ASSETS_DIR / "Dropdown_Up.svg").as_posix()}); width: 12px; height: 12px; }}
            QComboBox::down-arrow:on {{ image: url({(ASSETS_DIR / "Dropdown.svg").as_posix()}); }}
            QComboBox QAbstractItemView {{ background-color: {BUTTON}; color: {TEXT}; selection-background-color: {BG}; selection-color: {BUTTON}; accent-color: transparent; border: none; outline: none; }}
            QComboBox QAbstractItemView::item:hover {{ background-color: {HOVER}; color: {TEXT}; }}
        """)
        language.view().setFocusPolicy(Qt.NoFocus)

        self.settings_page = category_page("Indstillinger", [
            ("Tilpasning", [
                ("Animation mellem sider:", toggle_switch("slide_animation")),
                ("Sprog:", language)
            ]),
            ("Data", [
                ("pKs tabel:", pk_table(pKa_values, "Navn", "pKs", "pKa_values")),
                ("pKb tabel:", pk_table(pKb_values, "Navn", "pKb", "pKb_values"))
            ]),
        ])
        self.settings_page.setWindowIcon(QIcon(str(ASSETS_DIR / "Settings_Icon.svg")))
        self.stack.addWidget(self.settings_page)

    def create_periodic_page(self):
        from mendeleev.fetch import fetch_table
        table = QWidget()
        table.setStyleSheet("background: transparent;")
        grid = QGridLayout(table)
        grid.setContentsMargins(16, 16, 16, 16)
        grid.setSpacing(3)
        grid.setRowMinimumHeight(8, 16)
        number_style = f"color: {HOVER}; font-size: 15px; padding: 0px 6px;"
        for group in range (1, 19):
            label = QLabel(str(group))
            label.setStyleSheet(number_style)
            grid.addWidget(label, 0, group, Qt.AlignCenter)
        for row, period in [(p, p) for p in range(1, 8)] + [(9, 6), (10, 7)]:
            label = QLabel(str(period))
            label.setStyleSheet(number_style)
            grid.addWidget(label, row, 0 if row < 8 else 3, Qt.AlignRight | Qt.AlignVCenter)

        self.element_info = QLabel()
        self.element_info.setStyleSheet(f"color: {BUTTON}; font-size: 13px; padding-left: 12px;")
        self.element_info.setAlignment(Qt.AlignLeft | Qt.AlignTop)
        grid.addWidget(self.element_info, 1, 3, 3, 5)

        legend = QGridLayout()
        legend.setSpacing(4)
        legend.setRowStretch(1, 1)
        for text, col, span in (("Metal", 0, 5), ("Ikkemetal", 6, 3)):
            header = QLabel(text)
            header.setAlignment(Qt.AlignCenter)
            header.setStyleSheet(f"color: {BUTTON}; font-weight: bold; border: 1px solid {BUTTON}; border-bottom: none; border-top-left-radius: 6px; border-top-right-radius: 6px; padding: 2px;")
            legend.addWidget(header, 0, col, 1, span)
        for col, series in ((0, 3), (1, 4), (3, 8), (4, 7), (6, 1), (7, 6), (8, 2)):
            legend.addWidget(VerticalLabel(*ELEMENT_SERIES[series]), 1, col)
        legend.addWidget(VerticalLabel(*ELEMENT_SERIES[5]), 0, 5, 2, 1)
        f_block = QVBoxLayout()
        f_block.setSpacing(4)
        for series in (9, 10):
            name, color = ELEMENT_SERIES[series]
            box = QLabel(name)
            box.setAlignment(Qt.AlignLeft | Qt.AlignTop)
            box.setStyleSheet(f"background-color: {color}; color: {TEXT}; border-radius: 3px; padding: 4px;")
            f_block.addWidget(box)
        legend.addLayout(f_block, 1, 2)
        grid.addLayout(legend, 1, 8, 3, 5)

        self.elements = {}
        for e in fetch_table("elements").itertuples():
            if math.isnan(e.group_id):
                row, col = e.period + 3, e.atomic_number - (58 if e.period == 6 else 90) + 4
            else:
                row, col = e.period, int(e.group_id)
            btn = QPushButton()
            btn.setFixedSize(78, 76)
            btn.setCheckable(True)
            btn.setAutoExclusive(True)
            btn.setCursor(Qt.PointingHandCursor)
            btn.setStyleSheet(f"""
                QPushButton {{ background-color: {ELEMENT_SERIES[e.series_id][1]}; border: 2px solid transparent; border-radius: 4px; }}
                QPushButton:hover, QPushButton:checked {{ border-color: {BUTTON}; }}
            """)
            tile = QHBoxLayout(btn)
            tile.setContentsMargins(4, 2, 3, 3)
            tile.setSpacing(2)
            cell = QVBoxLayout()
            cell.setContentsMargins(0, 0, 0, 0)
            cell.setSpacing(0)
            tile.addLayout(cell, 1)
            for text, style in (
                (str(e.atomic_number), "font-size: 10px;"),
                (e.symbol, "font-size: 18px; font-weight: bold;"),
                (ELEMENT_NAMES[e.atomic_number - 1], "font-size: 9px;"),
                (element_mass(e), "font-size: 9px;"),
            ):
                label = QLabel(text)
                label.setStyleSheet(f"color: {TEXT}; background: transparent; {style}")
                label.setAttribute(Qt.WA_TransparentForMouseEvents)
                cell.addWidget(label)
            shells = QLabel(f"<div style='line-height: 80%;' align='right'>{'<br>'.join(map(str, electron_shells(e)))}</div>")
            shells.setStyleSheet(f"color: {TEXT}; background: transparent; font-size: 9px;")
            shells.setContentsMargins(0, 0, 0, 2)
            shells.setAttribute(Qt.WA_TransparentForMouseEvents)
            tile.addWidget(shells, 0, Qt.AlignRight | Qt.AlignTop)
            btn.clicked.connect(lambda _=False, e=e: self.show_element(e))
            grid.addWidget(btn, row, col)
            self.elements[e.symbol] = (btn, e)

        self.periodic_page = FitView()
        self.periodic_page.setScene(QGraphicsScene(self.periodic_page))
        self.periodic_page.scene().addWidget(table)
        self.periodic_page.setStyleSheet("background: transparent; border: none;")
        self.periodic_page.setHorizontalScrollBarPolicy(Qt.ScrollBarAlwaysOff)
        self.periodic_page.setVerticalScrollBarPolicy(Qt.ScrollBarAlwaysOff)
        self.periodic_page.setRenderHint(QPainter.Antialiasing)
        self.periodic_page.setWindowTitle("Periodisk system")

        btn, e = self.elements["C"]
        btn.setChecked(True)
        self.show_element(e)
        self.stack.addWidget(self.periodic_page)

    def show_element(self, e):
        sup = str.maketrans("0123456789", "⁰¹²³⁴⁵⁶⁷⁸⁹")
        config = re.sub(r"([spdf])(\d*)", lambda m: m[1] + (m[2] or "1").translate(sup), e.electronic_configuration)
        rows = [
            ("Atomnummer", e.atomic_number),
            ("Molarmasse", f"{element_mass(e)} g/mol"),
            ("Elektronegativitet", "–" if math.isnan(e.en_pauling) else str(e.en_pauling).replace(".", ",")),
            ("Elektronkonfiguration", config),
            ("Elektronskaller", ", ".join(map(str, electron_shells(e)))),
            ("Gruppe", "–" if math.isnan(e.group_id) else int(e.group_id)),
            ("Periode", e.period),
            ("Type", ELEMENT_SERIES[e.series_id][0]),
        ]
        self.element_info.setText(
            f"<span style='font-size: 30px; font-weight: bold;'>{e.symbol}</span>&nbsp;&nbsp;"
            f"<span style='font-size: 20px;'>{ELEMENT_NAMES[e.atomic_number - 1]}</span>"
            "<table cellspacing=1>" + "".join(f"<tr><td>{k}:&nbsp;&nbsp;</td><td><b>{v}</b></td></tr>" for k, v in rows) + "</table>"
        )

    def create_molecule_page(self):
        self.molecule_page = QWidget()
        layout = QVBoxLayout(self.molecule_page)
        layout.setContentsMargins(6,6,6,6)
        layout.setSpacing(6)

        row = QHBoxLayout()
        self.molecule_name = QLineEdit()
        self.molecule_name.setPlaceholderText("Navn på engelsk, f.eks. acetic acid")
        self.molecule_name.setStyleSheet(f"QLineEdit {{ background-color: {BUTTON}; color: {TEXT}; border: none; border-radius: 8px; padding: 4px 10px; }}")
        self.molecule_name.returnPressed.connect(self.name_to_structure)
        row.addWidget(self.molecule_name,stretch=1)

        draw_btn = QPushButton("Tegn")
        draw_btn.setStyleSheet(calc_button_style)
        draw_btn.clicked.connect(self.name_to_structure)
        row.addWidget(draw_btn)

        name_btn = QPushButton("Find navn")
        name_btn.setStyleSheet(calc_button_style)
        name_btn.clicked.connect(self.structure_to_name)
        row.addWidget(name_btn)

        self.molecule_status = QLabel()
        self.molecule_status.setStyleSheet(f"color: {BUTTON};")
        row.addWidget(self.molecule_status)
        layout.addLayout(row)

        self.molecule_view = QWebEngineView()
        self.molecule_view.page().setBackgroundColor(QColor(BG))
        bridge = _KetcherBridge(self.molecule_view)
        bridge.smilesReady.connect(self.smiles_to_name)
        channel = QWebChannel(self.molecule_view.page())
        channel.registerObject("bridge", bridge)
        self.molecule_view.page().setWebChannel(channel)
        self.molecule_view.page().profile().downloadRequested.connect(self.save_molecule)
        self.molecule_view.loadFinished.connect(lambda ok: self.molecule_view.page().runJavaScript("document.documentElement.style.filter = 'invert(.75) hue-rotate(180deg)'"))
        self.molecule_view.load(QUrl.fromLocalFile(str(resource_path("Assets_Ketcher/index.html"))))
        layout.addWidget(self.molecule_view, stretch=1)

        self.stack.addWidget(self.molecule_page)


    def slide_to(self, page):
        current = self.stack.currentWidget()
        if page is current or self.slide_anim.state() == QParallelAnimationGroup.Running:
            return
        self.slide_target = page
        self.update_page_title(self.stack.indexOf(page))
        if not _settings.value("slide_animation", True, type=bool):
            self.slide_finished()
            return
        w = self.stack.width()
        d = 1 if self.stack.indexOf(page) > self.stack.currentIndex() else -1

        page.setGeometry(d*w, 0, w, self.stack.height())
        page.show()
        page.raise_()

        self.slide_anim.clear()
        for widget, start, end in [(current, 0, -d*w),(page, d*w,0)]:
            anim = QPropertyAnimation(widget, b"pos")
            anim.setDuration(200)
            anim.setEasingCurve(QEasingCurve.OutCubic)
            anim.setStartValue(QPoint(start, 0))
            anim.setEndValue(QPoint(end, 0))
            self.slide_anim.addAnimation(anim)
        self.slide_anim.start()

    def slide_finished(self):
        self.stack.setCurrentWidget(self.slide_target)
        if self.slide_target is self.stack.widget(1):
            self.focus_interpreter()
        if self.slide_target is not self.history[self.history_index]:
            del self.history[self.history_index + 1:]
            self.history.append(self.slide_target)
            self.history_index += 1
        self.update_nav()

    def go_history(self, step):
        i = self.history_index + step
        if 0 <= i < len(self.history) and self.slide_anim.state() != QParallelAnimationGroup.Running:
            self.history_index = i
            self.slide_to(self.history[i])

    def update_nav(self):
        self.back_btn.setEnabled(self.history_index > 0)
        self.forward_btn.setEnabled(self.history_index < len(self.history) - 1)

    def open_panel(self, page, key):
        self.slide_to(page)
        page.show_panel(key)

    def open_menu(self):
        self.slide_to(self.stack.widget(0))

    def open_interpreter(self):
        self.slide_to(self.stack.widget(1))

    def save_regneark(self):
        view = self.interpreter_view
        path = view.property("path")
        if not path:
            return self.save_regneark_as()
        
        def write(data):
            try:
                text = json.dumps({"rows": json.loads(data)}, ensure_ascii=False, indent=2)
                Path(path).write_text(text, encoding="utf-8")
            except (OSError, TypeError, ValueError) as e:
                QMessageBox.warning(self, "Gem regneark", f"Filen kunne ikke gemmes:\n{e}")
                return
            view.page().runJavaScript(f"markSaved({json.dumps(data)})")

        view.page().runJavaScript("JSON.stringify(getSheet())", write)


    def save_regneark_as(self):
        path, _ = QFileDialog.getSaveFileName(self, "Gem regneark", self.tab_name(self.interpreter_tabs.currentIndex()) + ".crbn", "Regneark (*.crbn)")
        if not path:
            return
        index = self.tab_for_path(path)
        if index >= 0 and index != self.interpreter_tabs.currentIndex():
            QMessageBox.warning(self, "Gem regneark", f"{Path(path).name} er allerede åben i en anden fane.\nLuk den først, eller vælg et andet navn.")
            return
        self.set_tab_name(self.interpreter_view, Path(path).stem)
        self.interpreter_view.setProperty("path", path)
        self.save_regneark()

    def open_periodic(self):
        self.slide_to(self.periodic_page)

    def open_molecule(self):
        self.slide_to(self.molecule_page)

    def name_to_structure(self):
        name = self.molecule_name.text().strip()
        if not name:
            return
        self.molecule_status.clear()
        request = QNetworkRequest(QUrl(f"{PUBCHEM_URL}/name/property/SMILES/TXT"))
        request.setHeader(QNetworkRequest.ContentTypeHeader, "application/x-www-form-urlencoded")
        reply = self.network.post(request, b"name=" + bytes(QUrl.toPercentEncoding(name)))
        reply.finished.connect(lambda: self.draw_smiles(reply))

    def draw_smiles(self, reply):
        lines = bytes(reply.readAll()).decode("utf-8", "replace").splitlines()
        if reply.error() == QNetworkReply.NoError and lines and "<" not in lines[0]:
            self.molecule_view.page().runJavaScript(f'ketcher.setMolecule({json.dumps(lines[0])})')
        else:
            self.molecule_status.setText("Ikke fundet")
        reply.deleteLater()

    def structure_to_name(self):
        self.molecule_status.clear()
        self.molecule_view.page().runJavaScript("ketcher.getSmiles().then(s => bridge.setSmiles(s))")

    def save_molecule(self, download):
        path, _=QFileDialog.getSaveFileName(self, "Gem molekyle", os.path.join(download.downloadDirectory(), download.downloadFileName()))
        if not path:
            download.cancel()
            return
        download.setDownloadDirectory(os.path.dirname(path))
        download.setDownloadFileName(os.path.basename(path))
        download.accept()

    def smiles_to_name(self, smiles):
        if not smiles:
            return
        request = QNetworkRequest(QUrl(f"{PUBCHEM_URL}/smiles/property/Title/JSON"))
        request.setHeader(QNetworkRequest.ContentTypeHeader, "application/x-www-form-urlencoded")
        reply = self.network.post(request,b"smiles=" + bytes(QUrl.toPercentEncoding(smiles)))
        reply.finished.connect(lambda: self.show_name(reply))

    def show_name(self, reply):
        name = None
        if reply.error() == QNetworkReply.NoError:
            try:
                name = json.loads(bytes(reply.readAll()))["PropertyTable"]["Properties"][0].get("Title")
            except (ValueError, KeyError, IndexError, TypeError, AttributeError):
                pass
        if name:
            self.molecule_name.setText(name)
        else:
            self.molecule_status.setText("Ikke fundet")
        reply.deleteLater()

    def open_kemi(self):
        self.slide_to(self.kemi_page)

    def open_fysik(self):
        self.slide_to(self.fysik_page)

    def open_biotek(self):
        self.slide_to(self.biotek_page)

    def open_settings(self):
        self.slide_to(self.settings_page)

    def open_regneark(self):
        path, _ = QFileDialog.getOpenFileName(self, "Åbn regneark", "", "Regneark (*.crbn)")
        if path:
            self.load_regneark(path)

    def load_regneark(self, path, view=None):
        index = self.tab_for_path(path)
        if view is None and index >= 0:
            self.interpreter_tabs.setCurrentIndex(index)
            self.open_interpreter()
            return
        try:
            rows = json.loads(Path(path).read_text(encoding="utf-8"))["rows"]
            if not isinstance(rows, list) or not all(isinstance(r, list) and 2 <= len(r) <= 4 and all(isinstance(x, str) for x in r) for r in rows):
                raise ValueError
        except(OSError, UnicodeError, ValueError, KeyError, TypeError):
            QMessageBox.warning(self, "åbn regneark","filen kunne ikke åbnes. Den er måske corrupted")
            return
        view = view or self.new_interpreter_tab()
        self.set_tab_name(view, Path(path).stem)
        view.setProperty("path", path)
        view.loadFinished.connect(lambda ok: view.page().runJavaScript(f"setSheet({json.dumps(rows)})"))
        self.open_interpreter()

    def tab_for_path(self, path):
        key = os.path.normcase(os.path.abspath(path))
        for i in range(self.interpreter_stack.count()):
            other = self.interpreter_stack.widget(i).property("path")
            if other and os.path.normcase(os.path.abspath(other)) == key:
                return i
        return -1
    
    def keyPressEvent(self, event):
        if event.key() == Qt.Key_Escape:
            self.restore_window()

        elif event.key() == Qt.Key_F11:
            if not self.isFullScreen():
                self.showFullScreen()
            else:
                self.showMaximized()

    def restore_window(self):
        if self.isFullScreen():
            self.showNormal()

    def close_app(self):
        self.close()

    def closeEvent(self, event):
        views = [self.interpreter_stack.widget(i) for i in range(self.interpreter_stack.count())]
        dirty = [v for v in views if v.property("dirty")]
        if not self.close_confirmed and dirty:
            self.slide_to(self.stack.widget(1))
            self.interpreter_tabs.setCurrentIndex(self.interpreter_stack.indexOf(dirty[0]))
            names = ", ".join(self.tab_name(self.interpreter_stack.indexOf(v)) for v in dirty)
            if not self.ask_close("Luk Carbon", f"Vil du lukke Carbon?\n{names} er ikke gemt og går tabt."):
                event.ignore()
                return
        super().closeEvent(event)

def log_error(kind, value, tb):
    license_manager.CONFIG_DIR.mkdir(parents=True, exist_ok=True)
    text = "".join(traceback.format_exception(kind, value, tb))
    with open(license_manager.CONFIG_DIR / "fejl.log", "a", encoding="utf-8") as f:
        f.write(f"{datetime.now():%Y-%m-%d %H:%M:%S}\n{text}\n")

def report_error(kind, value, tb):
    log_error(kind, value, tb)
    QTimer.singleShot(0, lambda: QMessageBox.warning(None, "Carbon", f"Der skete en fejl:\n{value}"))

def preload(window, splash):
    pages = [window.interpreter_view.page()]
    scripts = ["typeof getSheet === 'function'"]
    names = ["regneark"]
    if resource_path("Assets_Ketcher/index.html").exists():
        pages.append(window.molecule_view.page())
        scripts.append("!!(window.ketcher && ketcher.editor)")
        names.append("molekyletegner")
    views = window.findChildren(MathInput) + window.findChildren(MathOutput)
    ready = [False] * len(pages)
    loop = QEventLoop()

    def poll():
        for i, (page, script) in enumerate(zip(pages, scripts)):
            if not ready[i]:
                page.runJavaScript(script, 0, lambda result, i=i: ready.__setitem__(i, bool(result)))
        done = sum(ready) + sum(v._loaded for v in views)
        splash.bar.setValue(int(55 + 45 * done / (len(ready) + len(views))))
        waiting = [name for name, r in zip(names, ready) if not r]
        splash.status("Indlæser " + " og ".join(waiting) if waiting else "Næsten færdig")
        if all(ready) and all(v._loaded for v in views):
            loop.quit()

    timer = QTimer()
    timer.timeout.connect(poll)
    timer.start(100)
    QTimer.singleShot(30000, loop.quit)
    loop.exec()
    timer.stop()

def main(app, splash):
    sys.excepthook = report_error
    threading.excepthook = lambda a: log_error(a.exc_type, a.exc_value, a.exc_traceback)
    if sys.platform == "win32" and getattr(sys, "frozen", False):
        register_crbn()

    license_manager.migrate_old_config()
    threading.Thread(target=quantity.update_unit_file, daemon=True).start()
    SKIP_LICENSE_CHECK = license_manager.start_check()

    if not SKIP_LICENSE_CHECK:
        splash.close()
        dialog = LicenseWindow()
        if dialog.exec() != QDialog.Accepted:
            sys.exit(0)
        splash.show()

    splash.status("Bygger GUI")
    window = MainWindow()
    app.window = window
    path = sys.argv[1] if len(sys.argv) > 1 else app.pending_file
    if path:
        window.load_regneark(path, window.interpreter_view)

    splash.progress(55)
    preload(window, splash)
    window.showMaximized()
    splash.finish(window)
    app.exec()