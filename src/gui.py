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
import ctypes
from matplotlib.figure import Figure

os.environ.setdefault("SSL_CERT_FILE", certifi.where())
os.environ.setdefault("REQUESTS_CA_BUNDLE", certifi.where())


import sys
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
SIDEBAR = "#737373"
BUTTON = "#ffffff"
HOVER = "#cccccc"
TEXT = "#000000"
SCROLL = "#323232"

HELPTEXT = {"pH" : ""}

def Latex_to_calc(s: str) -> str:
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

    def __init__(self, placeholder="", parent=None, text_mode=False):
        super().__init__(parent)
        self.setFixedHeight(27)
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
        # self.setAccent(ACCENT)
        if self._bridge.latex:
            self.page().runJavaScript(f"setValue({json.dumps(self._bridge.latex)})")

    # def setAccent(self, color):
    #   self.page().runJavaScript(f"setAccent({json.dumps(color)})")


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

    # def setAccent(self, color):
    #   self.page().runJavaScript(f"setAccent({json.dumps(color)})")

    def setReadOnly(self, _):
        pass

    def setStyleSheet(self, _):
        pass

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
        self.help_text = help_text or "Ingen hjælpetekst endu :("
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
        title_label.setStyleSheet(f"color: {TEXT}; font-weight: bold; border: none;")
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
                QLabel {{ color: {TEXT}; }}
                QPushButton {{
                    background-color: {BUTTON};
                    color: {TEXT};
                    padding: 6px 14px;
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
        #self.create_kemi_page()
        #self.create_fysik_page()
        #self.create_biotek_page()
        #self.create_settings_page()
        #self.create_formel_page()

    if sys.platform == "win32":

        ctypes.windll.dwmapi.DwmSetWindowAttribute(
            int(self.winId()), 33, ctypes.byref(ctypes.c_int(1)), ctypes.sizeof(ctypes.c_int)
        )


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
                QPushButton:pressed {{
                    background-color: {BUTTON};
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
        layout.setAlignment(Qt.AlignCenter)

        logo = QSvgWidget(str(ASSETS_DIR / "Carbon_Full.svg"))
        logo.renderer().setAspectRatioMode(Qt.KeepAspectRatio)
        logo.setFixedSize(1000,500)
        layout.addWidget(logo, alignment=Qt.AlignCenter)

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
        self.stack.setCurrentIndex(2)

    def open_kemi(self):
        self.stack.setCurrentIndex(3)

    def open_fysik(self):
        self.stack.setCurrentIndex(4)

    def open_biotek(self):
        self.stack.setCurrentIndex(5)

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