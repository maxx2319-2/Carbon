import os
import certifi
import json
from chem import pKa_values
from chem import pKb_values
import threading
import quantity
import chem
import biotek
import io
import base64
from matplotlib.figure import Figure

os.environ.setdefault("SSL_CERT_FILE", certifi.where())
os.environ.setdefault("REQUESTS_CA_BUNDLE", certifi.where())

import sys
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
    QSizeGrip,
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
    QTextEdit
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
)
from PySide6.QtWebEngineWidgets import QWebEngineView
from PySide6.QtWebChannel import QWebChannel
from PySide6.QtSvgWidgets import QSvgWidget

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
)
import re
import interpreter_maple
import chem
from matplotlib.backends.backend_qtagg import FigureCanvasQTAgg
import biotek
import license_manager

from path import resource_path

ASSETS_DIR = resource_path("Assets")

_settings = QSettings("M&B", "Carbon")

HEADER = "#1e1e1e"
BG = "#404040"
SIDEBAR = "#575757"
BUTTON = "#ffffff"
HOVER = "#cccccc"
TEXT = "#000000"
SCROLL = "#323232"

LINE_HEIGHT = 27
BOX_HEIGHT = 120
SIDEBAR_WIDTH = 220

button_style =  f"""
        QPushButton {{
            background-color: {BUTTON};
            color: {TEXT};
            border: none;
            border-radius: 8px;
            padding: 6px;
        }}
        QPushButton:hover {{ background-color: {HOVER}; }}
    """

SUB_HELP = (
    "\nFor at skrive sænket skrivt er det Shift+Bindestreg."
    "\nFor at skrive hævet skrivt er det Shift+^."
    )

HELPTEXT = {
    "unit": (
        "Indtast din originale værdi med dens enhed i det øverste input, brug . for decimaltal.\n"
        "Husk at skrive dens enhed inde i de firkantede parenteser [] for eksempel 10[km/t].\n"
        "Derefter indtast den ønskede enhed uden firkantede parenteser."
    ),
    "analysis": (
        "Indtast molekylet i input feltet.\n"
        "Husk at grundstoffer med navne der er længere end et bogstav kun har det første bogstav stort.\n"
        "Eksempelvis Fe3O4, Jernoxid.\n"
        "DBE formel kan kun anvendes til organiske molekyler."
    ),
    "bjerrum": (
        "Indtast pKs værdi for at opstille et bjerrumsdiagram.\n"
        "Brug . for at skrive decimaler og brug , for at lave endnu et diagram.\n"
        "For eksempel 5.3, 4.1 laver to bjerrumsdiagrammer."
    ),
    "ph": (
        "Indtast enten en pKs værdi eller en pKb værdi samt dens koncentration.\n"
        "Husk . for decimaltal og angiv koncentrationens enhed i firkantede parenteser [].\n"
        "Du kan også bruge syren eller basens navn for nogle syrer og baser (se Indstillinger).\n"
        "Det øverste output er pH mens det nederste er pOH.\n"
        "Standard enhed for koncentration er mol/l."
    ),
    "balance": (
        "Indtast din ubalancerede reaktion i input kassen.\n"
        "Brug pil mellem reaktanter og produkter ->.\n"
        "For eksempel H2O -> H2 + O2.\n"
        "Ved redoxreaktioner bruges opløsningsboksen hvor der skrives syre eller base."
    ),
    "yield": (
        "Indtast teoretisk udbytte i det første input og praktisk udbytte i det andet.\n"
        "Husk . for decimal og enheder inde i firkantet parentes [].\n"
        "Eksempelvis 4[kg] 300[g]. Standard enheden er kg."
    ),
    "volpct": (
        "Indtast samlet volumen i det første input og specifik volumen i det andet.\n"
        "Eksempelvis 4[l] 300[dl]. Standard enheden er l."
    ),
    "masspct": (
        "Indtast samlet masse i det første input og specifik masse i det andet.\n"
        "Eksempelvis 4[kg] 300[g]. Standard enheden er kg."
    ),
    "mass_calc": (
        "Indtast din tilgængelige data i deres respektive input.\n"
        "Den beregner alt den mulige data fra det givne input, så du behøver ikke fylde alle inputs.\n"
        "Standard: masse g, volumen l, stofmængde mol, koncentration mol/l, molarmasse g/mol, densitet kg/l."
    ),
    "buffer": (
        "Input stofmængden eller koncentrationen af syren og af basen samt syrens pKs.\n"
        "Standard enhed for stofmængde er mol, for koncentration mol/l."
    ),
    "h3o": "Input enten pH eller pOH.\nHusk . for decimaler.",
    "dna_mut": (
        "Indtast den raske DNA streng øverst og derefter den muterede.\n"
        "Mellemrum og store/små bogstaver er ligegyldige.\nFor eksempel AAT gcc TTG."
    ),
    "rna_mut": (
        "Indtast den raske RNA streng øverst og derefter den muterede.\n"
        "Mellemrum og store/små bogstaver er ligegyldige.\nFor eksempel AAU gcc UUG."
    ),
    "translation": (
        "Indtast enten DNA eller RNA streng.\n"
        "Mellemrum og store/små bogstaver er ligegyldige.\n"
        "For eksempel AAT gcc TTG eller AAUGCCUUU."
    ),
}

def Latex_to_calc(s: str) -> str:
    s = s.replace(r"\placeholder{}", "")
    s = s.replace(r"\_", "\x00")  # a typed underscore, not a subscript
    s = re.sub(r"\\rightleftharpoons(?![A-Za-z])\s*", "<->", s)
    s = re.sub(r"\\(to|rightarrow|longrightarrow)(?![A-Za-z])\s*", "->", s)
    s = s.replace(r"\left", "").replace(r"\right", "")
    s = s.replace(r"\lbrack", "[").replace(r"\rbrack", "]")
    s = s.replace(r"\lbrace", "\x01").replace(r"\rbrace", "\x02")
    s = s.replace(r"\{", "\x01").replace(r"\}", "\x02")
    s = s.replace(r"\cdot", "*").replace(r"\times", "*")
    s = s.replace(r"\#", "#")
    
    s = re.sub(r"\\(ln|log|exp)(?![A-Za-z])", r"\1", s)
    s = re.sub(r"\^\{\\prime\}", "'", s)
    s = re.sub(r"\\[,;:! ]", " ", s)
    s = re.sub(r"\\mu\s*", "µ", s)
    s = s.replace(r"\%", "%")

    prev = None

    while prev != s:
        prev = s
        s = re.sub(r"\\textcolor\{[^{}]*\}\{([^{}]*)\}", r"\1", s)
        s = re.sub(r"\\(?:mathrm|mathbf|text|operatorname)\{([^{}]*)\}", r"\1", s)
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
    s = str(s)

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
    s = s.replace(" ", r"\ ")
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
    return r"\text{" + "".join(esc.get(c, c) for c in s) + "}"


class _MapleBridge(QObject):
    @Slot(str, result=str)
    def run(self, data):
        latex_lines = json.loads(data)
        ev = interpreter_maple.EV()
        try:
            result = ev.ev("\n".join(Latex_to_calc(l) for l in latex_lines))
        except Exception as e:
            return json.dumps([["error", latex_text(f"Error: {e}")]])

        rows = []
        for i, latex in enumerate(latex_lines):
            rows.append(["code", latex])
            value = result.get(i, "")
            values = value if isinstance(value, list) else [value]
            for value in values:
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
        return json.dumps(rows)


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
        self.page().setBackgroundColor(Qt.transparent)

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


class MathOutput(QWebEngineView):
    def __init__(self, placeholder="", parent=None):
        super().__init__(parent)
        self.setFixedHeight(27)
        self._placeholder = placeholder
        self._raw = ""
        self._loaded = False
        self.page().setBackgroundColor(Qt.transparent)
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
        latex = calc_to_latex(self._raw) if self._raw else ""
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
        """)

    def setText(self, s):
        self.setPlainText(str(s))

    def text(self):
        return self.toPlainText()

class LicenseWindow(QDialog):
    def __init__(self, parent=None):
        super().__init__(parent)
        self.setWindowTitle("Carbon: Licens manager")
        self.setModal(True)
        self.setFixedSize(360, 160)
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

        button_row = QHBoxLayout()

        logo = QSvgWidget(str(ASSETS_DIR / "Carbon_Full.svg"))
        logo.renderer().setAspectRatioMode(Qt.KeepAspectRatio)
        logo.setFixedSize(150,75)
        button_row.addWidget(logo)
        button_row.addStretch()

        ok_btn = QPushButton("Ok")
        ok_btn.clicked.connect(self.try_accept)
        button_row.addWidget(ok_btn)

        cancel_btn = QPushButton("Afbryd")
        cancel_btn.clicked.connect(lambda: sys.exit(0))
        button_row.addWidget(cancel_btn)

        layout.addLayout(button_row)
    
    def try_accept(self):
        key = self.key_input.text().strip()

        try:
            licensed, data = license_manager.check_license(key)
            if not licensed:
                self.key_input.setText(data)
                return

            ok, msg = license_manager.activate(key)
            if not ok:
                self.key_input.setText(msg)
                return

            license_manager.save_activation(key, data)
            self.accept()

        except Exception:
            self.key_input.setText("Fejl")



# For biotek stamtræ
træ = biotek.graph()


class DraggablePanel(QWidget):
    def __init__(self, title, body_widget, parent=None, help_text=None):
        super().__init__(parent)
        self.help_text = help_text or "Ingen hjælpetekst endnu :("
        self.setStyleSheet(f"""
            DraggablePanel {{
                background-color: rgba(43, 43, 43, 0);
            }}
        """)
        self.setMinimumSize(240, 160)
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

        layout.addWidget(self.body)

        grip_row = QHBoxLayout()
        grip_row.setContentsMargins(0, 0, 0, 0)
        grip_row.addStretch()

        self.grip = QSizeGrip(self)
        self.grip.setStyleSheet("background: transparent;")
        grip_row.addWidget(self.grip)

        layout.addLayout(grip_row)

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
    si_btn.setFixedSize(28,28)
    si_btn.setToolTip("Konverter til SI")
    si_btn.setStyleSheet(button_style)
    unit_row.addWidget(si_btn)
    layout.addLayout(unit_row)

    calc_btn = QPushButton("Beregn")
    calc_btn.setStyleSheet(button_style)
    layout.addWidget(calc_btn)

    output = MathOutput("Resultat")
    layout.addWidget(output)
    layout.addStretch()

    def calc():
        result = interpreter_maple.EV().ev(f"EnhedKonvertering({value_input.text()},{unit_input.text()})")
        output.setText(result.get(0, ""))

    calc_btn.clicked.connect(calc)
    value_input.returnPressed.connect(calc)
    unit_input.returnPressed.connect(calc)
    si_btn.clicked.connect(lambda: unit_input.setText("SI"))

    return body


PANELS = {
    "unit": Panel("Enhed","Enheds Omregner", unit_panel),
}

class PanelPage(QWidget):
    def __init__(self, keys, parent=None):
        super().__init__(parent)
        self.panels = {}

        self.canvas = QWidget()
        self.canvas.setStyleSheet(f"background-color: {BG};")

        content = QWidget()
        content.setStyleSheet(f"background-color: {SIDEBAR};")
        content_layout = QVBoxLayout(content)
        content_layout.setContentsMargins(10,10,10,10)
        content_layout.setSpacing(14)

        for key in keys:
            btn = QPushButton(PANELS[key].label)
            btn.setFixedHeight(26)
            btn.setStyleSheet(f"""
                QPushButton {{
                    background-color: {BUTTON};
                    color: {TEXT};
                    border: none;
                    border-radius: 13px;
                }}
                QPushButton:hover {{ background-color: {HOVER}; }}
            """)
            btn.clicked.connect(lambda _=False, k=key: self.show_panel(k))
            content_layout.addWidget(btn)
        content_layout.addStretch()

        scroll = QScrollArea()
        scroll.setFixedWidth(SIDEBAR_WIDTH)
        scroll.setWidgetResizable(True)
        scroll.setHorizontalScrollBarPolicy(Qt.ScrollBarAlwaysOff)
        scroll.setVerticalScrollBarPolicy(Qt.ScrollBarAlwaysOn)
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

        self.sidebar = QWidget()
        self.sidebar.setMaximumWidth(0)
        sidebar_layout = QVBoxLayout(self.sidebar)
        sidebar_layout.setContentsMargins(0,0,0,0)
        sidebar_layout.addWidget(scroll)

        arrow = QIcon(str(ASSETS_DIR / "Arrow.svg")).pixmap(64,64)
        self.arrow_open = QIcon(arrow.transformed(QTransform().rotate(180)))
        self.arrow_closed = QIcon(arrow)

        self.handle = QPushButton()
        self.handle.setIcon(self.arrow_closed)
        self.handle.setIconSize(QSize(20,20))
        self.handle.setCheckable(True)
        self.handle.setChecked(True)
        self.handle.setFixedWidth(24)
        self.handle.setSizePolicy(QSizePolicy.Fixed, QSizePolicy.Expanding)
        self.handle.setStyleSheet(f"""
            QPushButton {{
                background-color: {SIDEBAR};
                border: none;
            }}
        """)
        self.handle.toggled.connect(self.toggle_sidebar)

        self.anim = QPropertyAnimation(self.sidebar, b"maximumWidth", self)
        self.anim.setDuration(250)
        self.anim.setEasingCurve(QEasingCurve.OutCubic)

        layout = QHBoxLayout(self)
        layout.setContentsMargins(0,0,0,0)
        layout.setSpacing(0)
        layout.addWidget(self.sidebar)
        layout.addWidget(self.handle)
        layout.addWidget(self.canvas, stretch=1)

    def show_panel(self, key):
        panel = self.panels.get(key)
        if panel is None:
            spec = PANELS[key]
            help_text = HELPTEXT[key] + SUB_HELP if key in HELPTEXT else None
            panel = DraggablePanel(spec.title, spec.build(), self.canvas, help_text)
            panel.resize(*spec.size)
            offset = 20 * len(self.panels)
            panel.move(20 + offset, 20 + offset)
            self.panels[key] = panel

        panel.show()
        panel.raise_()

    def toggle_sidebar(self, collapsed):
            self.handle.setIcon(self.arrow_closed if collapsed else self.arrow_open)
            self.anim.stop()
            self.anim.setStartValue(self.sidebar.maximumWidth())
            self.anim.setEndValue(0 if collapsed else SIDEBAR_WIDTH)
            self.anim.start()

class MainWindow(QMainWindow):
    def __init__(self, parent=None):
        super().__init__(parent)

        #self._load_dict_from_settings("pKa_values", pKa_values)
        #self._load_dict_from_settings("pKb_values", pKb_values)

        self.gen = 1

        self.setWindowTitle("Carbon")
        self.setStyleSheet(f"background-color: {BG};")
        self.setMinimumWidth(600)

        self.stack = QStackedWidget()
        self.setCentralWidget(self.stack)

        self.create_header()
        self.create_drawer()
        self.create_mainmenu()
        self.create_interpreter_page()
        #self.create_molecule_page()
        self.kemi_page = PanelPage(["unit"])
        self.fysik_page = PanelPage(["unit"])
        self.biotek_page = PanelPage(["unit"])
        self.stack.addWidget(self.kemi_page)
        self.stack.addWidget(self.fysik_page)
        self.stack.addWidget(self.biotek_page)
        #self.create_settings_page()
        #self.create_formel_page()

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
                border-radius: 8px;
                min-height: 30px;
            }}
            QScrollBar::add-line:vertical, QScrollBar::sub-line:vertical {{ height: 0; }}
        """)
        outer.addWidget(scroll)

        content = QWidget()
        content.setStyleSheet("background: transparent;")
        layout = QVBoxLayout(content)

        items = [
            ("Hovedmenu", self.open_menu),
            ("Regneark", self.open_interpreter),
            ("Kemi", self.open_kemi),
            ("Fysik", self.open_fysik),
            ("Biotek", self.open_biotek),
            ("Formelsamling", self.open_formula),
            ("Indstillinger", self.open_settings),
            ("Afslut", self.close_app),
        ]

        for text, callback in items:
            btn = QPushButton(text)
            btn.setStyleSheet(f"""
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
            """)
            btn.setCursor(Qt.PointingHandCursor)
            btn.clicked.connect(callback)
            btn.clicked.connect(self.toggle_drawer)
            layout.addWidget(btn)
        layout.addStretch()

        scroll.setWidget(content)

        self.drawer.hide()
        self.drawer_anim = QPropertyAnimation(self.drawer, b"pos")
        self.drawer_anim.setDuration(250)
        self.drawer_anim.setEasingCurve(QEasingCurve.OutCubic)
        self.drawer_anim.finished.connect(self.drawer_finished)

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
        if getattr(self, "drawer_open", False):
            top = self.toolbar.height()
            w = min(self.drawer_max_width, self.width())
            h = self.height() - top
            self.drawer.setFixedSize(w, h)
            self.drawer.move(self.width() - w, top)


    def create_header(self):
        self.toolbar = QToolBar("Header")
        self.addToolBar(self.toolbar)
        self.toolbar.setStyleSheet(f"""
                QToolBar {{
                    background-color: {HEADER};
                }}
                QToolButton {{
                    background-color: {HEADER};
                    border: none;
                }}
            """)
        self.toolbar.setIconSize(QSize(50, 50))
        self.toolbar.setFixedHeight(50)
        self.toolbar.setMovable(False)

        container = QWidget()
        container.setStyleSheet(f"background-color: {HEADER};")
        layout = QHBoxLayout(container)
        layout.setContentsMargins(5, 0, 5, 0)
        layout.setSpacing(15)

        def make_button(icon_path, tooltip, callback):
            btn = QToolButton()
            btn.setIcon(QIcon(str(ASSETS_DIR / icon_path)))
            btn.setIconSize(QSize(32, 32))
            btn.setToolTip(tooltip)
            btn.clicked.connect(callback)
            btn.setStyleSheet(f"""
                    QToolButton {{
                        background-color: {HEADER};
                        border: none;
                        padding: 6px;
                    }}
                    QToolTip {{
                    background-color: {BUTTON};
                    color: {TEXT};
                    border: 1px solid {HEADER};
                    }}
                """)
            return btn

        layout.addWidget(
            make_button("Carbon_Borderless_transparent.svg", "Hovedmenu", self.open_menu)
        )
        layout.addStretch()

        layout.addWidget(
            make_button("Interpreter_Icon.svg", "Regneark", self.open_interpreter)
        )
        layout.addStretch()

        layout.addWidget(
            make_button("Marvin_Icon.svg", "Molekyle Tegner", self.open_molecule)
        )
        layout.addStretch()

        layout.addWidget(
            make_button("Kemi_Icon.svg","Kemi", self.open_kemi)
        )
        layout.addStretch()

        layout.addWidget(
            make_button("Fysik_Icon.svg", "Fysik", self.open_fysik)
        )
        layout.addStretch()
        
        layout.addWidget(
            make_button("Biotek_Icon.svg", "Biotek", self.open_biotek)
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

    def run_search(self):
        print(self.search.text().strip())



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

        self.maple_view = QWebEngineView()
        self.maple_view.page().setBackgroundColor(Qt.transparent)
        self.maple_bridge = _MapleBridge()
        self.maple_channel = QWebChannel(self.maple_view.page())
        self.maple_channel.registerObject("bridge", self.maple_bridge)
        self.maple_view.page().setWebChannel(self.maple_channel)
        self.maple_view.loadFinished.connect(
            lambda ok: self.maple_view.page().runJavaScript(
                f"setAccent({json.dumps(BUTTON)})"
            )
        )
        self.maple_view.load(
            QUrl.fromLocalFile(str(resource_path("Assets_math_live/regneark.html")))
        )

        layout.addWidget(self.maple_view)
        self.stack.addWidget(page)


    def open_menu(self):
        self.stack.setCurrentIndex(0)

    def open_interpreter(self):
        self.stack.setCurrentIndex(1)

    def open_molecule(self):
        pass

    def open_kemi(self):
        self.stack.setCurrentWidget(self.kemi_page)

    def open_fysik(self):
        self.stack.setCurrentWidget(self.fysik_page)

    def open_biotek(self):
        self.stack.setCurrentWidget(self.biotek_page)

    def open_settings(self):
        self.stack.setCurrentIndex(6)

    def open_formula(self):
        self.stack.setCurrentIndex(7)

    def keyPressEvent(self, event):
        if event.key() == Qt.Key_Escape:
            if self.isFullScreen():
                self.showNormal()

        elif event.key() == Qt.Key_F11:
            if not self.isFullScreen():
                self.showFullScreen()

    def close_app(self):
        self.close()


if __name__ == "__main__":
    app = QApplication(sys.argv)
    threading.Thread(target=quantity.update_unit_file, daemon=True).start()
    SKIP_LICENSE_CHECK = license_manager.start_check()

    if not SKIP_LICENSE_CHECK:
        dialog = LicenseWindow()
        if dialog.exec() != QDialog.Accepted:
            sys.exit(0)

    window = MainWindow()
    window.showFullScreen()
    app.exec()