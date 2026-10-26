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
import utils

os.environ.setdefault("SSL_CERT_FILE", certifi.where())
os.environ.setdefault("REQUESTS_CA_BUNDLE", certifi.where())
os.environ.setdefault("QTWEBENGINE_CHROMIUM_FLAGS", "--disable-gpu")

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
    QTextEdit,
    QButtonGroup,
    QCompleter,
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

version = "Bv 2.0"

ASSETS_DIR = resource_path("Assets")

def hover_icon(file):
    icon = QIcon(str(ASSETS_DIR / file))
    hover = ASSETS_DIR / file.replace(".svg", "_Hover.svg")
    if hover.exists():
        icon.addFile(str(hover), QSize(), QIcon.Active)
    return icon

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
        QPushButton:hover {{ background-color: {SIDEBAR}; }}
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
    "pH": (
        "Indtast pKs værdi samt dens koncentration.\n"
        "Husk . for decimaltal og angiv koncentrationens enhed i firkantede parenteser [].\n"
        "Du kan også bruge syrens navn for nogle syrer (se Indstillinger).\n"
        "Standard enhed for koncentration er mol/l."
    ),
    "pOH": (
            "Indtast pKb værdi samt dens koncentration.\n"
            "Husk . for decimaltal og angiv koncentrationens enhed i firkantede parenteser [].\n"
            "Du kan også bruge syrens navn for nogle baser (se Indstillinger).\n"
            "Standard enhed for koncentration er mol/l."
    ),
    "balance": (
        "Indtast din ubalancerede reaktion i input kassen.\n"
        "Brug pil mellem reaktanter og produkter ->.\n"
        "For eksempel H2O -> H2 + O2.\n"
        "Ved redoxreaktioner bruges opløsningsboksen hvor der skrives syre eller base."
    ),
    "udbytteprocent": (
        "Indtast praktisk udbytte i det første input og teoretisk udbytte i det andet.\n"
        "Husk . for decimal og enheder inde i firkantet parentes [].\n"
        "Eksempelvis 4[kg] 300[g]. Standard enheden er kg."
    ),
    "volumenprocent": (
        "Indtast samlet volumen i det første input og specifik volumen i det andet.\n"
        "Eksempelvis 4[l] 300[dl]. Standard enheden er l."
    ),
    "masseprocent": (
        "Indtast samlet masse i det første input og specifik masse i det andet.\n"
        "Eksempelvis 4[kg] 300[g]. Standard enheden er kg."
    ),
    "mængdeberegning": (
        "Indtast din tilgængelige data i deres respektive input.\n"
        "Den beregner alt den mulige data fra det givne input, så du behøver ikke fylde alle inputs.\n"
        "Standard: masse g, volumen l, stofmængde mol, koncentration mol/l, molarmasse g/mol, densitet kg/l."
    ),
    "puffer": (
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
    "dna_peptid": (
        "Indtast DNA streng.\n"
        "Mellemrum og store/små bogstaver er ligegyldige.\n"
        "For eksempel AAT gcc TTG eller AATGCCTTT."
    ),
    "rna_peptid": (
            "Indtast RNA streng.\n"
            "Mellemrum og store/små bogstaver er ligegyldige.\n"
            "For eksempel AAU gcc UUG eller AAUGCCUUU."
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
    @Slot(result=str)
    def help(self):
        return json.dumps({
            name: [calc_to_latex(line.replace("_", r"\_").replace("%", r"\%")) for line in text.splitlines()]
            for name, text in interpreter_maple.EV().help_text.items()
        })



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
        self.page().setBackgroundColor(QColor(BG))

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
        self.page().setBackgroundColor(QColor(BG))
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
    def __init__(self, parent=None):
        super().__init__(parent)
        self.setWindowTitle("Carbon: Licens manager")
        self.setWindowIcon(QIcon(str(ASSETS_DIR / "Carbon_Round.svg")))
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

        self.version_label = QLabel(version, self)
        self.version_label.setStyleSheet(f"color: {BUTTON}; font-size: 10px; background: transparent;")
        self.version_label.adjustSize()
        self.version_label.move(
            self.width() - self.version_label.width() - 1,
            self.height() - self.version_label.height() - 1,
        )
    
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
                background-color: transparent;
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

        if hasattr(body_widget, "export"):
            export_btn = QToolButton()
            export_btn.setIcon(hover_icon("Save.svg"))
            export_btn.setAutoRaise(True)
            export_btn.setIconSize(QSize(14,14))
            export_btn.setFixedSize(20,20)
            export_btn.setToolTip("Eksporter")
            export_btn.setStyleSheet("QPushButton { background: transparent; border: none; }")
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

class ResizeEdge(QWidget):
    def __init__(self, edges, cursor, parent):
        super().__init__(parent)
        self.edges = edges
        self.setCursor(cursor)

    def mousePressEvent(self, event):
        if event.button() == Qt.LeftButton:
            self.window().windowHandle().startSystemResize(self.edges)

    def place(self, m=6):
        w, h = self.parent().width(), self.parent().height()
        x = 0 if self.edges & Qt.LeftEdge else w - m if self.edges & Qt.RightEdge else m
        y = 0 if self.edges & Qt.TopEdge else h - m if self.edges & Qt.BottomEdge else m
        width = m if self.edges & (Qt.LeftEdge | Qt.RightEdge) else w - 2 * m
        height = m if self.edges & (Qt.TopEdge | Qt.BottomEdge) else h - 2 * m
        self.setGeometry(x, y, width, height)
        self.raise_()

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
        result = interpreter_maple.EV().ev(f"EnhedKonvertering({value_input.text()},{unit_input.text()})")
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

    pKs_input = MathInput("Pks eller syrenavn")
    layout.addWidget(pKs_input)

    konc_input = MathInput("Koncentration[Enhed]")
    layout.addWidget(konc_input)

    calc_btn = QPushButton("Beregn")
    calc_btn.setStyleSheet(calc_button_style)
    layout.addWidget(calc_btn)

    output = MathOutput("pH")
    layout.addWidget(output)

    second_output = MathOutput("pOH")
    layout.addWidget(second_output)
    layout.addStretch()

    def calc():
        result = interpreter_maple.EV().ev(f"pH({pKs_input.text()},{konc_input.text()})").get(0, "")
        output.setText(result)
        if result.startswith("Error"):
            second_output.setText("")
        else:
            decimals = len(result.split(".")[1]) if "." in result else 0
            second_output.setText(f"{14 - float(result):.{decimals}f}")

    calc_btn.clicked.connect(calc)
    pKs_input.returnPressed.connect(calc)
    konc_input.returnPressed.connect(calc)
    
    return body

def pOH_panel():
    body = QWidget()
    layout = QVBoxLayout(body)
    layout.setContentsMargins(6,6,6,6)
    layout.setSpacing(6)

    pKs_input = MathInput("Pkb eller basenavn")
    layout.addWidget(pKs_input)

    konc_input = MathInput("Koncentration[Enhed]")
    layout.addWidget(konc_input)

    calc_btn = QPushButton("Beregn")
    calc_btn.setStyleSheet(calc_button_style)
    layout.addWidget(calc_btn)

    output = MathOutput("pOH")
    layout.addWidget(output)

    second_output = MathOutput("pH")
    layout.addWidget(second_output)
    layout.addStretch()

    def calc():
        result = interpreter_maple.EV().ev(f"pOH({pKs_input.text()},{konc_input.text()})").get(0, "")
        output.setText(result)
        if result.startswith("Error"):
            second_output.setText("")
        else:
            decimals = len(result.split(".")[1]) if "." in result else 0
            second_output.setText(f"{14 - float(result):.{decimals}f}")

    calc_btn.clicked.connect(calc)
    pKs_input.returnPressed.connect(calc)
    konc_input.returnPressed.connect(calc)
    
    return body

def afstemning_panel():
    body = QWidget()
    layout = QVBoxLayout(body)
    layout.setContentsMargins(6,6,6,6)
    layout.setSpacing(6)

    reaktion_input = MathInput("Reaktant->Produkt")
    layout.addWidget(reaktion_input)

    solution_input = MathInput("Opløsning (syre/base)")
    layout.addWidget(solution_input)

    calc_btn = QPushButton("Beregn")
    calc_btn.setStyleSheet(calc_button_style)
    layout.addWidget(calc_btn)

    output = MathOutput("Afstemt reaktion")
    layout.addWidget(output)
    layout.addStretch()

    def calc():
        arg = f"{reaktion_input.text()},{solution_input.text()}" if solution_input.text() else reaktion_input.text()
        result = interpreter_maple.EV().ev(f"Afstem({arg})")
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

    dbe = MathOutput("DBE")
    layout.addWidget(dbe)

    antal = MathOutput("Antal atomer")
    layout.addWidget(antal)

    masseprocent = TextOutput("Masseprocent:")
    layout.addWidget(masseprocent, stretch=1)
    layout.addStretch()

    outputs = [molekyle, empirisk, molarmasse, dbe, antal]

    def calc():
        result = interpreter_maple.EV().ev(f"Analyse({input.text()})").get(0,"")
        lines = result.splitlines()
        if result.startswith("Error"):
            for box in outputs:
                box.setText("")
            masseprocent.setText(result)
            return
        for box, line in zip(outputs, lines):
            box.setText(line.split(":", 1)[1].strip())
        masseprocent.setText("\n".join(lines[6:]))

    calc_btn.clicked.connect(calc)
    input.returnPressed.connect(calc)
    
    return body

def bjerrum_panel():
    body = QWidget()
    layout = QVBoxLayout(body)
    layout.setContentsMargins(6,6,6,6)
    layout.setSpacing(6)

    input = MathInput("pKs Værdier")
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
        result = interpreter_maple.EV().ev(f"BjerrumDiagram({input.text()})").get(0,"")
        while plot_layout.count():
            plot_layout.takeAt(0).widget().deleteLater()
        if isinstance(result, Figure):
            plot_layout.addWidget(FigureCanvasQTAgg(result))
        else:
            error = QLabel(str(result))
            error.setWordWrap(True)
            error.setStyleSheet(f"color: {BUTTON}")
            plot_layout.addWidget(error, alignment=Qt.AlignTop)

    def export():
        result = interpreter_maple.EV().ev(f"BjerrumDiagram({input.text()},export)").get(0, "")
        if result:
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

    output = MathOutput("Resultat")
    layout.addWidget(output)
    layout.addStretch()

    def calc():
        result = interpreter_maple.EV().ev(f"UdbytteProcent({praktisk_input.text()},{teori_input.text()})").get(0, "")
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

    output = MathOutput("Resultat")
    layout.addWidget(output)
    layout.addStretch()

    def calc():
        result = interpreter_maple.EV().ev(f"VolumenProcent({specifik_input.text()},{samlet_input.text()})").get(0, "")
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

    output = MathOutput("Resultat")
    layout.addWidget(output)
    layout.addStretch()

    def calc():
        result = interpreter_maple.EV().ev(f"MasseProcent({specifik_input.text()},{samlet_input.text()})").get(0, "")
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
        fields = [
            ("m", masse_input),
            ("V", volumen_input),
            ("n", stofmængde_input),
            ("c", koncentration_input),
            ("M", molarmasse_input),
            ("p", densitet_input),
        ]
        args = ",".join(f"{key}={field.text()}" for key, field in fields if field.text())
        result = interpreter_maple.EV().ev(f"MængdeBeregning({args})").get(0, "")

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

    DNA_input = MathInput("DNA Streng")
    layout.addWidget(DNA_input)

    calc_btn = QPushButton("Beregn")
    calc_btn.setStyleSheet(calc_button_style)
    layout.addWidget(calc_btn)

    output = MathOutput("Peptidkæde")
    layout.addWidget(output)
    layout.addStretch()

    def calc():
        result = interpreter_maple.EV().ev(f"DNATilPeptid({DNA_input.text()})").get(0, "")
        output.setText(result)

    calc_btn.clicked.connect(calc)
    DNA_input.returnPressed.connect(calc)
    
    return body

def rna_peptid_panel():
    body = QWidget()
    layout = QVBoxLayout(body)
    layout.setContentsMargins(6,6,6,6)
    layout.setSpacing(6)

    RNA_input = MathInput("RNA Streng")
    layout.addWidget(RNA_input)

    calc_btn = QPushButton("Beregn")
    calc_btn.setStyleSheet(calc_button_style)
    layout.addWidget(calc_btn)

    output = MathOutput("Peptidkæde")
    layout.addWidget(output)
    layout.addStretch()

    def calc():
        result = interpreter_maple.EV().ev(f"RNATilPeptid({RNA_input.text()})").get(0, "")
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

    pks_input = MathInput("pKs")
    layout.addWidget(pks_input)

    calc_btn = QPushButton("Beregn")
    calc_btn.setStyleSheet(calc_button_style)
    layout.addWidget(calc_btn)

    output = MathOutput("pH")
    layout.addWidget(output)
    layout.addStretch()

    def calc():
        result = interpreter_maple.EV().ev(f"Puffer({syre_konc_input.text()},{base_konc_input.text()},{pks_input.text()})").get(0, "")
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

    ph_input = MathInput("pH")
    layout.addWidget(ph_input)

    calc_btn = QPushButton("Beregn")
    calc_btn.setStyleSheet(calc_button_style)
    layout.addWidget(calc_btn)

    h3o_output = MathOutput("Oxonium koncentration")
    layout.addWidget(h3o_output)

    oh_output = MathOutput("Hydroxid koncentration")
    layout.addWidget(oh_output) 
    layout.addStretch()

    def calc():
        result = interpreter_maple.EV().ev(f"pHTilKoncentration({ph_input.text()})").get(0, "")
        if result.startswith("Error"):
            h3o_output.setText(result)
            oh_output.setText("")
            return
        h3o, oh = (line.split(":", 1)[1].strip() for line in result.splitlines())
        h3o_output.setText(h3o)
        oh_output.setText(oh)

    calc_btn.clicked.connect(calc)
    ph_input.returnPressed.connect(calc)

    return body

PANELS = {
    "unit": Panel("Enhed","Enheds Omregner", unit_panel),
    "pH": Panel("pH","pH Beregning", pH_panel),
    "pOH": Panel("pOH","pOH Beregning", pOH_panel),
    "balance": Panel("Afstemning","Reaktions Afstemning",afstemning_panel),
    "analysis": Panel("Analyse","Molekylær Analyse",analyse_panel),
    "bjerrum": Panel("Bjerrumdiagram","Bjerrumsdiagram",bjerrum_panel, (450,450)),
    "udbytteprocent": Panel("Udbytteprocent","Udbytteprocent",udbytte_panel),
    "volumenprocent": Panel("Volumenprocent","Volumenprocent",volumen_panel),
    "masseprocent": Panel("Masseprocent", "Masseprocent",masse_panel),
    "mængdeberegning": Panel("Mængdeberegning","Mængdeberegning",mængde_panel),
    "dna_peptid": Panel("DNA Translation","DNA Translation",dna_peptid_panel),
    "rna_peptid": Panel("RNA Translation","RNA Translation",rna_peptid_panel),
    "puffer": Panel("Puffer", "pH i Puffer",puffer_panel),
    "h3o": Panel("H3O+ og OH-", "H3O+ og OH- koncentration fra pH",ph_konc_panel)
}

class PanelPage(QWidget):
    def __init__(self, keys, parent=None):
        super().__init__(parent)
        self.keys = keys
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
            btn.setFixedHeight(30)
            btn.setStyleSheet(f"{button_style}")
            btn.clicked.connect(lambda _=False, k=key: self.show_panel(k))
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

        self.sidebar = QWidget()
        self.sidebar.setMaximumWidth(0)
        sidebar_layout = QVBoxLayout(self.sidebar)
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
            panel.resize(spec.size[0], panel.sizeHint().height())
            offset = 20 * len(self.panels)
            panel.move(20 + offset, 20 + offset)
            self.panels[key] = panel

        panel.show()
        panel.raise_()

    def toggle_sidebar(self, collapsed):
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
        self.setWindowIcon(QIcon(str(ASSETS_DIR / "Carbon_Round.svg")))
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
        #self.create_molecule_page()
        self.kemi_page = PanelPage(["unit","pH","pOH","balance","analysis","bjerrum","udbytteprocent","volumenprocent","masseprocent","mængdeberegning","puffer","h3o"])
        self.fysik_page = PanelPage(["unit"])
        self.biotek_page = PanelPage(["unit","dna_peptid","rna_peptid"])
        self.stack.addWidget(self.kemi_page)
        self.stack.addWidget(self.fysik_page)
        self.stack.addWidget(self.biotek_page)
        self.create_drawer()
        self.create_search()
        #self.create_settings_page()
        #self.create_formel_page()

        self.history = [self.stack.currentWidget()]
        self.history_index = 0
        self.update_nav()

        self.update_page_title(self.stack.currentIndex())

        self.version_label = QLabel(version, self)
        self.version_label.setStyleSheet(f"color: {BUTTON}; font-size: 10px; background: transparent;")
        self.version_label.setAttribute(Qt.WA_TransparentForMouseEvents)

        self.resize_edges = [
            ResizeEdge(edges, cursor, self) for edges, cursor in [
                (Qt.LeftEdge, Qt.SizeHorCursor), (Qt.RightEdge, Qt.SizeHorCursor),
                (Qt.TopEdge, Qt.SizeVerCursor), (Qt.BottomEdge, Qt.SizeVerCursor),
                (Qt.TopEdge | Qt.LeftEdge, Qt.SizeFDiagCursor), (Qt.BottomEdge | Qt.RightEdge, Qt.SizeFDiagCursor),
                (Qt.TopEdge | Qt.RightEdge, Qt.SizeBDiagCursor), (Qt.BottomEdge | Qt.LeftEdge, Qt.SizeBDiagCursor),
            ]
        ]

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
            ("Hovedmenu", self.open_menu, None),
            ("Regneark", self.open_interpreter, None),
            ("Kemi", self.open_kemi, self.kemi_page),
            ("Fysik", self.open_fysik, self.fysik_page),
            ("Biotek", self.open_biotek, self.biotek_page),
            ("Formelsamling", self.open_formula, None),
            ("Indstillinger", self.open_settings, None),
            ("Afslut", self.close_app, None),
        ]

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
            btn.setCursor(Qt.PointingHandCursor)
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
            expand.setCursor(Qt.PointingHandCursor)
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
                panel_btn.setCursor(Qt.PointingHandCursor)
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
        for edge in self.resize_edges:
            edge.place()
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
        outer.setContentsMargins(5,0,0,0)
        outer.setSpacing(0)

        window_row = QHBoxLayout()
        window_row.setSpacing(0)
        outer.addLayout(window_row)

        layout = QHBoxLayout()
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

        def nav_icon(mirror):
            icon = QIcon()
            for file, mode in (("Pointer.svg", QIcon.Normal), ("Pointer_Hover.svg", QIcon.Disabled)):
                pixmap = QIcon(str(ASSETS_DIR / file)).pixmap(64,64)
                if mirror:
                    pixmap = pixmap.transformed(QTransform().scale(-1,1))
                icon.addPixmap(pixmap, mode)
            return icon
        
        self.back_btn = make_button("Pointer.svg", "Tilbage", lambda: self.go_history(-1))
        self.forward_btn = make_button("Pointer.svg", "Frem", lambda: self.go_history(1))
        self.back_btn.setIcon(nav_icon(False))
        self.forward_btn.setIcon(nav_icon(True))
        self.max_btn = make_button("Maximize.svg", "Maksimer", self.toggle_maximized)
        close_btn = make_button("Close.svg", "Luk", self.close)
        for btn in (self.back_btn, self.forward_btn, make_button("Minimize.svg", "Minimer", self.showMinimized), self.max_btn, close_btn):
            btn.setIconSize(QSize(10,10))
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
            make_button("Marvin_Icon.svg", "Molekyle Tegner", self.open_molecule)
        )
        layout.addStretch()

        layout.addWidget(
            make_button("Kemi_Icon.svg","Kemi", self.open_kemi, 2)
        )
        layout.addStretch()

        layout.addWidget(
            make_button("Fysik_Icon.svg", "Fysik", self.open_fysik, 3)
        )
        layout.addStretch()
        
        layout.addWidget(
            make_button("Biotek_Icon.svg", "Biotek", self.open_biotek, 4)
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
        self.stack.currentChanged.connect(lambda i: self.page_buttons.button(i).setChecked(True))
    def create_search(self):
        self.search_targets = {}
        for name, page in [("Kemi", self.kemi_page), ("Fysik", self.fysik_page), ("Biotek", self.biotek_page)]:
            for key in page.keys:
                self.search_targets[f"{PANELS[key].label} ({name})"] = (page, key)

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
        self.open_panel(*self.search_targets[item.text()])
        self.search.clear()

    def update_page_title(self, i):
        btn = self.page_buttons.button(i)
        self.page_title.setIcon(btn.icon())
        self.page_title.setText(btn.toolTip())
        self.page_title.adjustSize()
        self.place_page_title()

    def place_page_title(self):
        self.page_title.move(
            (self.header_container.width() - self.page_title.width()) // 2,
            (self.max_btn.sizeHint().height() - self.page_title.height()) // 2,
        )


    def toggle_maximized(self):
        if self.isMaximized() or self.isFullScreen():
            self.showNormal()
        else:
            self.showFullScreen()

    def changeEvent(self, event):
        super().changeEvent(event)
        if event.type() == event.Type.WindowStateChange:
            maximized = self.isMaximized() or self.isFullScreen()
            self.max_btn.setIcon(hover_icon("Restore.svg" if maximized else "Maximize.svg"))
            self.max_btn.setToolTip("Gendan" if maximized else "Maksimer")
            for edge in self.resize_edges:
                edge.setHidden(maximized)

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
        self.maple_view.page().setBackgroundColor(QColor(BG))
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

    def slide_to(self, page):
        current = self.stack.currentWidget()
        if page is current or self.slide_anim.state() == QParallelAnimationGroup.Running:
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
        self.slide_target = page
        self.update_page_title(self.stack.indexOf(page))
        self.slide_anim.start()

    def slide_finished(self):
        self.stack.setCurrentWidget(self.slide_target)
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

    def open_molecule(self):
        pass

    def open_kemi(self):
        self.slide_to(self.kemi_page)

    def open_fysik(self):
        self.slide_to(self.fysik_page)

    def open_biotek(self):
        self.slide_to(self.biotek_page)

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
    os.environ["QTWEBENGINE_CHROMIUM_FLAGS"] = "--log-level=3"
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