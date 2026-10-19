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
    QTextEdit,
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
)
from PySide6.QtWebEngineWidgets import QWebEngineView
from PySide6.QtWebChannel import QWebChannel

from PySide6.QtGui import (
    QIcon,
    QPixmap,
    QTextCursor,
    QSyntaxHighlighter,
    QTextCharFormat,
    QColor,
    QFont,
    QDrag,
    QPainter,
    QBrush,
    QPen,
)
import re
import interpreter
import interpreter_maple
import chem
from matplotlib.backends.backend_qtagg import FigureCanvasQTAgg
import biotek
import license_manager
import base64

from path import resource_path

ASSETS_DIR = resource_path("Assets")

_settings = QSettings("Calc", "Calc")

ACCENT_standard = "#6FC6FB"
BG_standard = "#1E1E1E"
PANEL_BG_standard = "#171717"
SIDEBAR_BG_standard = "#2b2b2b"
TEXT_standard = "#ffffff"
HOVER_standard = "#202020"


ACCENT = _settings.value("accent_color", ACCENT_standard)
BG = BG_standard
PANEL_BG = PANEL_BG_standard
SIDEBAR_BG = SIDEBAR_BG_standard
TEXT = TEXT_standard
HOVER = HOVER_standard


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
        try:
            result = interpreter_maple.EV().ev(
                "\n".join(Latex_to_calc(l) for l in latex_lines)
            )
        except Exception as e:
            return json.dumps([["error", latex_text(f"Error: {e}")]])

        rows = []
        for i, latex in enumerate(latex_lines):
            rows.append(["code", latex])
            value = result.get(i, "")
            if isinstance(value, Figure):
                buf = io.BytesIO()
                value.savefig(buf, format="png")
                rows.append(
                    [
                        "image",
                        "data:image/png;base64,"
                        + base64.b64encode(buf.getvalue()).decode(),
                    ]
                )
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
        self.setAccent(ACCENT)
        if self._bridge.latex:
            self.page().runJavaScript(f"setValue({json.dumps(self._bridge.latex)})")

    def setAccent(self, color):
        self.page().runJavaScript(f"setAccent({json.dumps(color)})")


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
        self.setAccent(ACCENT)
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

    def setAccent(self, color):
        self.page().runJavaScript(f"setAccent({json.dumps(color)})")

    def setReadOnly(self, _):
        pass

    def setStyleSheet(self, _):
        pass


class LicenseWindow(QDialog):
    def __init__(self, parent=None):
        super().__init__(parent)
        self.setWindowTitle("License Manager")
        self.setModal(True)
        self.setFixedSize(360, 160)
        self.setStyleSheet(f"""
            QDialog {{ background-color: {BG}; }}
            QLabel {{ color: {TEXT}; }}
            QLineEdit {{
                background-color: {SIDEBAR_BG};
                color: {TEXT};
                border: 1px solid {ACCENT};
                border-radius: 4px;
                padding: 6px;
            }}
            QPushButton {{
                background-color: {PANEL_BG};
                color: {TEXT};
                border: 1px solid {ACCENT};
                border-radius: 6px;
                padding: 6px 14px;
            }}
            QPushButton:hover {HOVER}
        """)

        layout = QVBoxLayout(self)
        layout.addWidget(QLabel("Indtast licens:"))

        self.key_input = QLineEdit()
        layout.addWidget(self.key_input)

        button_row = QHBoxLayout()
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


# for stamtæs analyse

træ = biotek.graph()


class MapleHighlighter(QSyntaxHighlighter):
    def __init__(self, document):
        super().__init__(document)

        def fmt(color, bold=False):
            f = QTextCharFormat()
            f.setForeground(QColor(color))
            if bold:
                f.setFontWeight(QFont.Bold)
            return f

        self.string_fmt = fmt("#CE9178")
        self.comment_fmt = fmt("#9CDCFE")
        self.number_fmt = fmt("#B5CEA8")
        self.operator_fmt = fmt("#D4D4D4")

        control_flow = ["help"]
        self.control_fmt = fmt("#C586C0", bold=True)
        self.control_pattern = re.compile(r"\b(" + "|".join(control_flow) + r")\b")

        functions = [
            "print",
            "balance_reaction",
            "pH",
            "SI",
            "analysis",
            "bjerrumdiagram",
            "udbytteprocent",
            "volumenprocent",
            "masseprocent",
            "DNA_til_peptid",
            "RNA_til_peptid",
            "mængdeberegning",
            "puffer",
            "mutations_analyse_DNA",
            "mutations_analyse_RNA",
            "unit_convert",
            "pH_to_concentration",
            "pOH_to_concentration",
            "pOH",
            "empirisk_analyse",
        ]
        self.function_fmt = fmt("#569CD6", bold=True)
        self.function_pattern = re.compile(r"\b(" + "|".join(functions) + r")\b")

        self.number_pattern = re.compile(r"\b\d+(\.\d+)?\b")
        self.string_pattern = re.compile(r"'[^']*'")
        self.operator_pattern = re.compile(r"[=+\-*/^(),]")

    def highlightBlock(self, text):
        comment_idx = text.find("#")
        code_part = text if comment_idx == -1 else text[:comment_idx]

        for match in self.control_pattern.finditer(code_part):
            self.setFormat(match.start(), match.end() - match.start(), self.control_fmt)

        for match in self.function_pattern.finditer(code_part):
            self.setFormat(
                match.start(), match.end() - match.start(), self.function_fmt
            )

        for match in self.string_pattern.finditer(code_part):
            self.setFormat(match.start(), match.end() - match.start(), self.string_fmt)

        for match in self.number_pattern.finditer(code_part):
            self.setFormat(match.start(), match.end() - match.start(), self.number_fmt)

        for match in self.operator_pattern.finditer(code_part):
            self.setFormat(
                match.start(), match.end() - match.start(), self.operator_fmt
            )

        if comment_idx != -1:
            self.setFormat(comment_idx, len(text) - comment_idx, self.comment_fmt)


class MapleTextEdit(QTextEdit):

    def __init__(self, main_window, parent=None):
        super().__init__(parent)
        self.main_window = main_window
        self.highlighter = MapleHighlighter(self.document())

    def keyPressEvent(self, event):
        if (
            event.key() in (Qt.Key_Return, Qt.Key_Enter)
            and event.modifiers() & Qt.ControlModifier
        ):
            self.main_window.run_maple()
            return
        super().keyPressEvent(event)


class DraggablePanel(QWidget):
    def __init__(self, title, body_widget, parent=None, help_text=None):
        super().__init__(parent)
        self.help_text = help_text or "Ingen hjælpetekst endu :("
        self.setStyleSheet(f"""
            DraggablePanel {{
                background-color: rgba(43, 43, 43, 0);
                border: 1px solid {ACCENT};
                border-radius: 8px;
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
            background-color: {ACCENT};
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
            QPushButton {{ background: transparent; border: none; color: {BG}; font-weight: bold; font-size: 14px; }}
            QPushButton:hover {{ color: {HOVER}; }}
        """)
        help_btn.clicked.connect(self.show_help)
        header_layout.addWidget(help_btn)

        close_btn = QPushButton("x")
        close_btn.setFixedSize(20, 20)
        close_btn.setStyleSheet(f"""
            QPushButton {{ background: transparent; border: none; color: {BG}; font-weight: bold; font-size: 14px; }}
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
                background-color: {PANEL_BG};
                color: {TEXT};
                border: 1px solid {ACCENT};
                border-radius: 6px;
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


class ShapePalette(QListWidget):
    """A themed list of shapes you can drag onto the ShapeCanvas."""

    def __init__(self, parent=None):
        super().__init__(parent)
        self.setDragEnabled(True)
        self.setFixedWidth(90)
        self.setFixedHeight(85)
        self.setStyleSheet(f"""
            QListWidget {{
                background-color: {SIDEBAR_BG};
                color: {TEXT};
                border: 1px solid {ACCENT};
                border-radius: 6px;
                font-size: 11px;
            }}
            QListWidget::item {{
                background-color: {PANEL_BG};
                border: 1px solid {ACCENT};
                border-radius: 6px;
                padding: 8px;
                margin: 4px;
            }}
            QListWidget::item:selected {{
                background-color: {ACCENT};
                color: {BG};
            }}
        """)

        SHAPES = [
            ("Square", "Mand"),
            ("Circle", "Kvinde"),
        ]

        for internal_name, label in SHAPES:
            item = QListWidgetItem(label)
            item.setData(Qt.UserRole, internal_name)
            self.addItem(item)

    def startDrag(self, supportedActions):
        item = self.currentItem()
        if item is None:
            return

        mime = QMimeData()
        mime.setText(item.data(Qt.UserRole))

        drag = QDrag(self)
        drag.setMimeData(mime)
        drag.exec(Qt.CopyAction)


class ShapeCanvas(QGraphicsView):
    """Drop target: creates movable/selectable shapes styled with the app accent color."""

    shape_placed = Signal(str, float, float)

    def __init__(self, parent=None):
        super().__init__(parent)
        self.scene = QGraphicsScene(0, 0, 800, 600, self)
        self.setScene(self.scene)
        self.setRenderHint(QPainter.Antialiasing)
        self.setAcceptDrops(True)
        self.setDragMode(QGraphicsView.RubberBandDrag)
        self.setStyleSheet(f"""
            QGraphicsView {{
                background-color: {BG};
                border: 1px solid {ACCENT};
                border-radius: 6px;
            }}
        """)
        self.setBackgroundBrush(QBrush(QColor(BG)))
        self.setFocusPolicy(Qt.StrongFocus)

    def keyPressEvent(self, event):
        if event.key() in (Qt.Key_Backspace, Qt.Key_Delete):
            for item in self.scene.selectedItems():
                self.scene.removeItem(item)
            return

    def dragEnterEvent(self, event):
        if event.mimeData().hasText():
            event.acceptProposedAction()

    def dragMoveEvent(self, event):
        if event.mimeData().hasText():
            event.acceptProposedAction()

    def dropEvent(self, event):
        shape_name = event.mimeData().text()
        scene_pos = self.mapToScene(event.position().toPoint())
        self.add_shape(shape_name, scene_pos)
        event.acceptProposedAction()

    def add_shape(self, shape_name, pos, size=60):
        rect = QRectF(-size / 2, -size / 2, size, size)

        if shape_name == "Square":
            item = QGraphicsRectItem(rect)
        elif shape_name == "Circle":
            item = QGraphicsEllipseItem(rect)
        else:
            return

        item.setPos(pos)
        item.setBrush(QBrush(QColor(BG)))
        item.setPen(QPen(QColor(TEXT), 4))

        item.setFlag(item.GraphicsItemFlag.ItemIsMovable, True)
        item.setFlag(item.GraphicsItemFlag.ItemIsSelectable, True)

        self.scene.addItem(item)

        self.shape_placed.emit(shape_name, pos.x(), pos.y())


def make_shape_drawer_body():
    body = QWidget()
    body.setStyleSheet(f"background-color: {BG};")
    layout = QHBoxLayout(body)
    layout.setContentsMargins(6, 6, 6, 6)
    layout.setSpacing(6)

    palette = ShapePalette()
    canvas = ShapeCanvas()

    left_side = QWidget()
    left_layout = QVBoxLayout(left_side)
    left_layout.setContentsMargins(0, 0, 0, 0)
    left_layout.setSpacing(6)

    left_layout.addWidget(palette)

    generation_btn = QPushButton("Ny generation")
    generation_btn.setStyleSheet(f"""
        QPushButton {{
            background-color: {PANEL_BG};
            color: {TEXT};
            border: 1px solid {ACCENT};
            border-radius: 6px;
            padding: 8px;
            font-size: 11px;
        }}
        QPushButton:hover {{ background-color: {HOVER}; }}
    """)

    analyse_btn = QPushButton("Analyse")
    analyse_btn.setStyleSheet(f"""
        QPushButton {{
            background-color: {PANEL_BG};
            color: {TEXT};
            border: 1px solid {ACCENT};
            border-radius: 6px;
            padding: 8px;
            font-size: 11px;
        }}
        QPushButton:hover {{ background-color: {HOVER}; }}
    """)

    left_layout.addWidget(generation_btn)
    left_layout.addWidget(analyse_btn)
    left_layout.addStretch()
    # keeps button right under the list instead of at the bottom

    layout.addWidget(left_side)
    layout.addWidget(canvas, stretch=1)

    return body, canvas, analyse_btn


class MainWindow(QMainWindow):
    def __init__(self, parent=None):
        super().__init__(parent)

        self._load_dict_from_settings("pKa_values", pKa_values)
        self._load_dict_from_settings("pKb_values", pKb_values)

        self.gen = 1

        self.setWindowTitle("Calc")
        self.setStyleSheet(f"background-color: {BG};")
        self.setMinimumWidth(600)

        self.stack = QStackedWidget()
        self.setCentralWidget(self.stack)

        self.create_toolbar()
        self.create_center_image()
        self.create_maple_page()
        self.create_kemi_page()
        self.create_biotek_page()
        self.create_fysik_page()
        self.create_settings_page()
        self.create_formula_page()

    def create_center_image(self):
        self.images = {}

        container = QWidget()
        grid = QGridLayout(container)
        grid.setContentsMargins(20, 20, 20, 20)

        grid.setRowStretch(0, 1)
        grid.setRowStretch(1, 2)
        grid.setRowStretch(2, 1)
        grid.setColumnStretch(0, 1)
        grid.setColumnStretch(1, 2)
        grid.setColumnStretch(2, 1)

        def make_image(path):
            label = QLabel()
            label.setSizePolicy(QSizePolicy.Expanding, QSizePolicy.Expanding)
            label.setAlignment(Qt.AlignCenter)
            pixmap = QPixmap(path)
            self.images[label] = pixmap
            return label

        top_left = make_image(str(ASSETS_DIR / "Henfald.png"))
        top_right = make_image(str(ASSETS_DIR / "Dopa.png"))
        center = make_image(str(ASSETS_DIR / "Temp Navn.png"))
        bottom_left = make_image(str(ASSETS_DIR / "Testosteron.png"))
        bottom_right = make_image(str(ASSETS_DIR / "Rydberg.png"))

        grid.addWidget(top_left, 0, 0, alignment=Qt.AlignTop | Qt.AlignLeft)
        grid.addWidget(top_right, 0, 2, alignment=Qt.AlignTop | Qt.AlignRight)
        grid.addWidget(center, 1, 1, alignment=Qt.AlignCenter)
        grid.addWidget(bottom_left, 2, 0, alignment=Qt.AlignBottom | Qt.AlignLeft)

        br_container = QWidget()
        br_layout = QVBoxLayout(br_container)
        br_layout.setContentsMargins(0, 0, 0, 0)
        br_layout.addWidget(bottom_right, alignment=Qt.AlignRight)

        version_label = QLabel("v 0.1")
        version_label.setStyleSheet("color: white; font-size: 10px;")
        br_layout.addWidget(version_label, alignment=Qt.AlignRight)

        grid.addWidget(br_container, 2, 2, alignment=Qt.AlignBottom | Qt.AlignRight)

        self.stack.addWidget(container)
        self.update_images()

    def create_maple_page(self):
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
                f"setAccent({json.dumps(ACCENT)})"
            )
        )
        self.maple_view.load(
            QUrl.fromLocalFile(str(resource_path("Assets_math_live/regneark.html")))
        )

        layout.addWidget(self.maple_view)
        self.stack.addWidget(page)

    def create_kemi_page(self):
        page = QWidget()
        layout = QHBoxLayout(page)
        layout.setContentsMargins(0, 0, 0, 0)
        layout.setSpacing(0)

        layout.addWidget(self.create_kemi_sidebar())

        self.kemi_canvas = QWidget()
        self.kemi_canvas.setStyleSheet(f"background-color: {BG};")
        layout.addWidget(self.kemi_canvas, stretch=1)

        self.kemi_panels = {}

        self.stack.addWidget(page)

    def show_kemi_panel(self, key, title, body_widget=None, help_text=None):
        panel = self.kemi_panels.get(key)
        if panel is None:
            if body_widget is None:
                body_widget = QWidget()
            panel = DraggablePanel(
                title,
                parent=self.kemi_canvas,
                body_widget=body_widget,
                help_text=help_text,
            )
            offset = 20 * len(self.kemi_panels)
            panel.move(20 + offset, 20 + offset)
            self.kemi_panels[key] = panel

        panel.show()
        panel.raise_()

    def show_biotek_panel(self, key, title, body_widget=None, help_text=None):
        panel = self.biotek_panels.get(key)
        if panel is None:
            if body_widget is None:
                body_widget = QWidget()
            panel = DraggablePanel(
                title,
                parent=self.biotek_canvas,
                body_widget=body_widget,
                help_text=help_text,
            )
            offset = 20 * len(self.biotek_panels)
            panel.move(20 + offset, 20 + offset)
            self.biotek_panels[key] = panel

        panel.show()
        panel.raise_()

    def show_fysik_panel(self, key, title, body_widget=None, help_text=None):
        panel = self.fysik_panels.get(key)
        if panel is None:
            if body_widget is None:
                body_widget = QWidget()
            panel = DraggablePanel(
                title,
                parent=self.fysik_canvas,
                body_widget=body_widget,
                help_text=help_text,
            )
            offset = 20 * len(self.fysik_panels)
            panel.move(20 + offset, 20 + offset)
            self.fysik_panels[key] = panel

        panel.show()
        panel.raise_()

    def make_input_output_body(self, input_labels, output_labels, calc_callback=None):
        widget = QWidget()
        widget.setStyleSheet(f"background-color: {BG};")
        layout = QVBoxLayout(widget)
        layout.setContentsMargins(6, 6, 6, 6)
        layout.setSpacing(6)

        field_style = f"""
            QLineEdit {{
                background-color: {SIDEBAR_BG};
                color: white;
                border: 1px solid {ACCENT};
                border-radius: 4px;
                padding: 4px;
                font-size: 12px;
            }}
        """

        inputs = []
        for label in input_labels:
            line = MathInput(label)
            layout.addWidget(line)
            inputs.append(line)

        calc_btn = QPushButton("Beregn")
        calc_btn.setStyleSheet(f"""
            QPushButton {{
                background-color: {PANEL_BG};
                color: {TEXT};
                border: 1px solid {ACCENT};
                border-radius: 6px;
                padding: 6px;
                font-size: 12px;
            }}
            QPushButton:hover {{ background-color: {HOVER}; }}
        """)
        layout.addWidget(calc_btn)

        outputs = []
        for label in output_labels:
            out = MathOutput(label)
            layout.addWidget(out)
            outputs.append(out)

        layout.addStretch()

        if calc_callback:
            calc_btn.clicked.connect(lambda: calc_callback(inputs, outputs))
            for line in inputs:
                line.returnPressed.connect(calc_btn.click)

        return widget

    def create_biotek_page(self):
        page = QWidget()
        layout = QHBoxLayout(page)
        layout.setContentsMargins(0, 0, 0, 0)
        layout.setSpacing(0)

        layout.addWidget(self.create_biotek_sidebar())

        self.biotek_canvas = QWidget()
        self.biotek_canvas.setStyleSheet(f"background-color: {BG};")
        layout.addWidget(self.biotek_canvas, stretch=1)

        self.biotek_panels = {}

        self.stack.addWidget(page)

    def create_biotek_sidebar(self):
        sidebar = QWidget()
        sidebar.setFixedWidth(100)
        sidebar.setStyleSheet(f"background-color: {SIDEBAR_BG};")

        layout = QVBoxLayout(sidebar)
        layout.setContentsMargins(10, 10, 10, 10)
        layout.setSpacing(10)

        button_style = f"""
                QPushButton {{
                    background-color: {PANEL_BG};
                    color: {TEXT};
                    border: 1px solid {ACCENT};
                    border-radius: 6px;
                    padding: 8px;
                    font-size: 10px;
                }}
                QPushButton:hover {{
                    background-color: {HOVER};
                }}
            """

        Biotek_1 = QPushButton("Enhed")
        Biotek_1.setStyleSheet(button_style)
        Biotek_1.clicked.connect(self.Biotek_1_Pressed)
        layout.addWidget(Biotek_1)

        Biotek_2 = QPushButton("Stamtræsanalyse")
        Biotek_2.setStyleSheet(button_style)
        Biotek_2.clicked.connect(self.Biotek_2_Pressed)
        layout.addWidget(Biotek_2)

        Biotek_3 = QPushButton("DNA Mut")
        Biotek_3.setStyleSheet(button_style)
        Biotek_3.clicked.connect(self.Biotek_3_Pressed)
        layout.addWidget(Biotek_3)

        Biotek_4 = QPushButton("RNA Mut")
        Biotek_4.setStyleSheet(button_style)
        Biotek_4.clicked.connect(self.Biotek_4_Pressed)
        layout.addWidget(Biotek_4)

        Biotek_5 = QPushButton("Translation")
        Biotek_5.setStyleSheet(button_style)
        Biotek_5.clicked.connect(self.Biotek_5_Pressed)
        layout.addWidget(Biotek_5)

        layout.addStretch()

        return sidebar

    def create_fysik_page(self):
        page = QWidget()
        layout = QHBoxLayout(page)
        layout.setContentsMargins(0, 0, 0, 0)
        layout.setSpacing(0)

        layout.addWidget(self.create_fysik_sidebar())

        self.fysik_canvas = QWidget()
        self.fysik_canvas.setStyleSheet(f"background-color: {BG};")
        layout.addWidget(self.fysik_canvas, stretch=1)

        self.fysik_panels = {}

        self.stack.addWidget(page)

    def _save_dict_to_settings(self, settings_key, data_dict):
        _settings.setValue(settings_key, json.dumps(data_dict))

    def _load_dict_from_settings(self, settings_key, target_dict):
        raw = _settings.value(settings_key, None)
        if raw:
            try:
                saved = json.loads(raw)
                target_dict.update(saved)
            except (json.JSONDecodeError, TypeError):
                pass

    def create_fysik_sidebar(self):
        sidebar = QWidget()
        sidebar.setFixedWidth(100)
        sidebar.setStyleSheet(f"background-color: {SIDEBAR_BG};")

        layout = QVBoxLayout(sidebar)
        layout.setContentsMargins(10, 10, 10, 10)
        layout.setSpacing(10)

        button_style = f"""
                    QPushButton {{
                        background-color: {PANEL_BG};
                        color: {TEXT};
                        border: 1px solid {ACCENT};
                        border-radius: 6px;
                        padding: 8px;
                        font-size: 10px;
                    }}
                    QPushButton:hover {{
                        background-color: {HOVER};
                    }}
                """

        Fysik_1 = QPushButton("Enhed")
        Fysik_1.setStyleSheet(button_style)
        Fysik_1.clicked.connect(self.Fysik_1_Pressed)
        layout.addWidget(Fysik_1)

        Fysik_2 = QPushButton("Tom")
        Fysik_2.setStyleSheet(button_style)
        Fysik_2.clicked.connect(self.Fysik_2_Pressed)
        layout.addWidget(Fysik_2)

        Fysik_3 = QPushButton("Tom")
        Fysik_3.setStyleSheet(button_style)
        Fysik_3.clicked.connect(self.Fysik_3_Pressed)
        layout.addWidget(Fysik_3)

        Fysik_4 = QPushButton("Tom")
        Fysik_4.setStyleSheet(button_style)
        Fysik_4.clicked.connect(self.Fysik_4_Pressed)
        layout.addWidget(Fysik_4)

        Fysik_5 = QPushButton("Tom")
        Fysik_5.setStyleSheet(button_style)
        Fysik_5.clicked.connect(self.Fysik_5_Pressed)
        layout.addWidget(Fysik_5)

        layout.addStretch()

        return sidebar

    def create_settings_page(self):
        page = QWidget()
        outer_layout = QVBoxLayout(page)
        outer_layout.setContentsMargins(0, 0, 0, 0)
        outer_layout.setSpacing(0)

        scroll = QScrollArea()
        scroll.setWidgetResizable(True)
        scroll.setFrameShape(QScrollArea.NoFrame)
        scroll.setStyleSheet(f"""
            QScrollArea {{ background-color: {BG}; border: none; }}
            QScrollBar:vertical {{
                background: {PANEL_BG};
                width: 10px;
                margin: 0px;
                border-radius: 5px;
            }}
            QScrollBar::handle:vertical {{
                background: {ACCENT};
                border-radius: 5px;
                min-height: 24px;
            }}
            QScrollBar::add-line:vertical, QScrollBar::sub-line:vertical {{
                height: 0px;
            }}
            QScrollBar::add-page:vertical, QScrollBar::sub-page:vertical {{
                background: none;
            }}
        """)

        content = QWidget()
        content.setStyleSheet(f"background-color: {BG};")
        content_layout = QVBoxLayout(content)
        content_layout.setContentsMargins(40, 30, 40, 40)
        content_layout.setSpacing(28)

        header = QLabel("Indstillinger")
        header.setStyleSheet(
            f"color: {TEXT}; font-size: 24px; font-weight: bold; background: transparent;"
        )
        content_layout.addWidget(header)

        self.accent_swatch = QPushButton()
        self.accent_swatch.setFixedSize(28, 28)
        self.accent_swatch.setCursor(Qt.PointingHandCursor)
        self.accent_swatch.setToolTip("Vælg accentfarve")
        self.accent_swatch.clicked.connect(self._open_color_picker)

        self.accent_hex_input = QLineEdit()
        self.accent_hex_input.setText(ACCENT)
        self.accent_hex_input.setPlaceholderText("#6FC6FB")
        self.accent_hex_input.setFixedWidth(90)
        self.accent_hex_input.setMaxLength(7)
        self._style_lineedit(self.accent_hex_input)
        self.accent_hex_input.returnPressed.connect(self._apply_hex_from_input)
        self.accent_hex_input.editingFinished.connect(self._apply_hex_from_input)

        reset_btn = QPushButton("Standard")
        reset_btn.setFixedHeight(28)
        reset_btn.setFixedWidth(100)
        self._style_button(reset_btn)
        reset_btn.clicked.connect(self._reset_accent_color)

        accent_row = QWidget()
        accent_row.setStyleSheet("background: transparent;")
        accent_row.setSizePolicy(QSizePolicy.Fixed, QSizePolicy.Fixed)
        accent_row_layout = QHBoxLayout(accent_row)
        accent_row_layout.setContentsMargins(0, 0, 0, 0)
        accent_row_layout.setSpacing(8)
        accent_row_layout.addWidget(self.accent_swatch)
        accent_row_layout.addWidget(self.accent_hex_input)
        accent_row_layout.addWidget(reset_btn)

        pKs_row = QWidget()
        pKs_row.setStyleSheet("background: transparent;")
        pKs_row.setSizePolicy(QSizePolicy.Fixed, QSizePolicy.Fixed)
        pKs_row_layout = QHBoxLayout(pKs_row)
        pKs_row_layout.setContentsMargins(0, 0, 0, 0)
        pKs_row_layout.setSpacing(8)

        pKb_row = QWidget()
        pKb_row.setStyleSheet("background: transparent;")
        pKb_row.setSizePolicy(QSizePolicy.Fixed, QSizePolicy.Fixed)
        pKb_row_layout = QHBoxLayout(pKb_row)
        pKb_row_layout.setContentsMargins(0, 0, 0, 0)
        pKb_row_layout.setSpacing(8)

        content_layout.addWidget(
            self._settings_category(
                "Tilpasning",
                [
                    ("Accentfarve", accent_row),
                ],
            )
        )

        pKs_row = self._build_pKa_editor(
            pKa_values, "Syre navn", "pKs", settings_key="pKa_values"
        )
        pKb_row = self._build_pKa_editor(
            pKb_values, "Base navn", "pKb", settings_key="pKb_values"
        )

        content_layout.addWidget(
            self._settings_category(
                "Data",
                [
                    ("pKs Værdier", pKs_row),
                    ("pKb Værdier", pKb_row),
                ],
            )
        )

        content_layout.addStretch()

        self._update_swatch_style()

        scroll.setWidget(content)
        outer_layout.addWidget(scroll)

        self.stack.addWidget(page)

    def _settings_category(self, title, rows):
        container = QWidget()
        container.setStyleSheet("background: transparent;")
        layout = QVBoxLayout(container)
        layout.setContentsMargins(0, 0, 0, 0)
        layout.setSpacing(8)

        title_label = QLabel(title)
        title_label.setStyleSheet(
            f"color: {ACCENT}; font-size: 15px; font-weight: bold; background: transparent;"
        )
        layout.addWidget(title_label)

        card = QWidget()
        card.setStyleSheet(
            f"background-color: {PANEL_BG}; border: 1px solid {ACCENT}; border-radius: 8px;"
        )
        card_layout = QVBoxLayout(card)
        card_layout.setContentsMargins(4, 4, 4, 4)
        card_layout.setSpacing(0)

        for i, (label_text, widget) in enumerate(rows):
            row = self._settings_row(label_text, widget)
            card_layout.addWidget(row)

        layout.addWidget(card)
        return container

    def _settings_row(self, label_text, control_widget):
        row = QWidget()
        row.setStyleSheet("background: transparent;")
        row_layout = QHBoxLayout(row)
        row_layout.setContentsMargins(12, 10, 12, 10)

        if label_text:
            label = QLabel(label_text)
            label.setStyleSheet(
                f"color: {TEXT}; font-size: 12px; background: transparent; border: none;"
            )
            row_layout.addWidget(label)

        row_layout.addStretch()
        row_layout.addWidget(control_widget)
        return row

    def _build_pKa_editor(
        self,
        data_dict,
        key_placeholder="Navn",
        value_placeholder="pKs",
        settings_key=None,
    ):
        container = QWidget()
        container.setStyleSheet("background: transparent;")
        layout = QVBoxLayout(container)
        layout.setContentsMargins(0, 0, 0, 0)
        layout.setSpacing(6)

        list_widget = QListWidget()
        list_widget.setFixedHeight(160)
        list_widget.setFixedWidth(220)
        list_widget.setStyleSheet(f"""
            QListWidget {{
                background-color: {SIDEBAR_BG};
                color: {TEXT};
                border: 1px solid {ACCENT};
                border-radius: 6px;
                font-size: 11px;
            }}
        """)
        layout.addWidget(list_widget)

        def clear_list_widget():
            while list_widget.count():
                item = list_widget.takeItem(0)
                widget = list_widget.itemWidget(item)
                if widget is not None:
                    list_widget.removeItemWidget(item)
                    widget.deleteLater()
                del item

        def refresh_list():
            clear_list_widget()
            for name, value in sorted(data_dict.items()):
                item = QListWidgetItem()
                row_widget = QWidget()
                row_layout = QHBoxLayout(row_widget)
                row_layout.setContentsMargins(6, 2, 6, 2)
                row_layout.setSpacing(6)

                label = QLabel(f"{name}: {value}")
                label.setStyleSheet(
                    f"color: {TEXT}; font-size: 11px; background: transparent;"
                )
                row_layout.addWidget(label)
                row_layout.addStretch()

                del_btn = QPushButton("x")
                del_btn.setFixedSize(20, 20)
                del_btn.setStyleSheet(f"""
                    QPushButton {{ background: transparent; border: none; color: {TEXT}; font-weight: bold; }}
                    QPushButton:hover {{ color: #FB6F6F; }}
                """)
                del_btn.clicked.connect(lambda _, n=name: remove_entry(n))
                row_layout.addWidget(del_btn)

                item.setSizeHint(QSize(200, 26))
                list_widget.addItem(item)
                list_widget.setItemWidget(item, row_widget)

            list_widget.doItemsLayout()
            list_widget.viewport().update()

        def remove_entry(name):
            if name in data_dict:
                del data_dict[name]
                if settings_key:
                    self._save_dict_to_settings(settings_key, data_dict)
                refresh_list()

        def add_entry():
            name = name_input.text().strip()
            value_text = value_input.text().strip().replace(",", ".")
            if not name or not value_text:
                return
            try:
                value = float(value_text)
            except ValueError:
                return
            data_dict[name] = value
            if settings_key:
                self._save_dict_to_settings(settings_key, data_dict)
            name_input.clear()
            value_input.clear()
            refresh_list()

        add_row = QWidget()
        add_row.setStyleSheet("background: transparent;")
        add_row_layout = QHBoxLayout(add_row)
        add_row_layout.setContentsMargins(0, 0, 0, 0)
        add_row_layout.setSpacing(6)

        name_input = QLineEdit()
        name_input.setPlaceholderText(key_placeholder)
        self._style_lineedit(name_input)

        value_input = QLineEdit()
        value_input.setPlaceholderText(value_placeholder)
        value_input.setFixedWidth(60)
        self._style_lineedit(value_input)

        add_btn = QPushButton("+")
        add_btn.setFixedSize(28, 28)
        self._style_button(add_btn)
        add_btn.setStyleSheet(add_btn.styleSheet() + """
        QPushButton { padding: 0px; font-size: 16px;}
        """)
        add_btn.clicked.connect(add_entry)

        name_input.returnPressed.connect(add_entry)
        value_input.returnPressed.connect(add_entry)

        add_row_layout.addWidget(name_input)
        add_row_layout.addWidget(value_input)
        add_row_layout.addWidget(add_btn)

        layout.addWidget(add_row)

        refresh_list()

        return container

    def _style_combo(self, combo):
        combo.setStyleSheet(f"""
            QComboBox {{
                background-color: {SIDEBAR_BG};
                color: {TEXT};
                border: 1px solid {ACCENT};
                border-radius: 4px;
                padding: 4px 8px;
                font-size: 12px;
                min-width: 100px;
            }}
            QComboBox QAbstractItemView {{
                background-color: {SIDEBAR_BG};
                color: {TEXT};
                selection-background-color: {ACCENT};
                selection-color: {BG};
            }}
        """)

    def _style_label(self, line):
        line.setStyleSheet(f"""
            QLineEdit {{
                background-color: {BG};
                color: {TEXT};
                border: 1px solid {ACCENT};
                border-radius: 4px;
                padding: 4px 8px;
                font-size: 12px;
            }}
        """)

    def _style_lineedit(self, line):
        line.setStyleSheet(f"""
            QLineEdit {{
                background-color: {SIDEBAR_BG};
                color: {TEXT};
                border: 1px solid {ACCENT};
                border-radius: 4px;
                padding: 4px 8px;
                font-size: 12px;
            }}
        """)

    def _style_button(self, btn):
        btn.setStyleSheet(f"""
            QPushButton {{
                background-color: {SIDEBAR_BG};
                color: {TEXT};
                border: 1px solid {ACCENT};
                border-radius: 6px;
                padding: 6px 14px;
                font-size: 12px;
            }}
            QPushButton:hover {{ background-color: {HOVER}; }}
        """)

    def _style_checkbox(self, box):
        box.setStyleSheet(f"""
            QCheckBox::indicator {{
                width: 18px;
                height: 18px;
                border: 1px solid {ACCENT};
                border-radius: 4px;
                background-color: {SIDEBAR_BG};
            }}
            QCheckBox::indicator:checked {{
                background-color: {ACCENT};
            }}
        """)

    def _style_slider(self, slider):
        slider.setStyleSheet(f"""
            QSlider::groove:horizontal {{
                background: {SIDEBAR_BG};
                height: 4px;
                border-radius: 2px;
            }}
            QSlider::handle:horizontal {{
                background: {ACCENT};
                width: 14px;
                margin: -6px 0;
                border-radius: 7px;
            }}
        """)

    def _open_color_picker(self):
        color = QColorDialog.getColor(QColor(ACCENT), self, "Vælg temafarve")
        if color.isValid():
            new_hex = color.name()
            self.apply_accent_color(new_hex)
            self.accent_hex_input.setText(new_hex)
            self._update_swatch_style()

    def _apply_hex_from_input(self):
        text = self.accent_hex_input.text().strip()
        if not text.startswith("#"):
            text = "#" + text
        color = QColor(text)
        if color.isValid() and len(text) == 7:
            self.apply_accent_color(text)
            self._update_swatch_style()
        else:
            self.accent_hex_input.setText(ACCENT)

    def _reset_accent_color(self):
        self.apply_accent_color(ACCENT_standard)
        self.accent_hex_input.setText(ACCENT_standard)
        self._update_swatch_style()

    def _update_swatch_style(self):
        self.accent_swatch.setStyleSheet(f"""
            QPushButton {{
                background-color: {ACCENT};
                border: 1px solid {TEXT};
                border-radius: 6px;
            }}
        """)

    def apply_accent_color(self, new_color):
        global ACCENT
        old_color = ACCENT

        self._replace_color_in_widget(self, old_color, new_color)

        ACCENT = new_color
        for field in self.findChildren(MathInput) + self.findChildren(MathOutput):
            field.setAccent(new_color)
        _settings.setValue("accent_color", new_color)

    def _replace_color_in_widget(self, widget, old_color, new_color):
        sheet = widget.styleSheet()
        if sheet and old_color.lower() in sheet.lower():
            widget.setStyleSheet(sheet.replace(old_color, new_color))

        for child in widget.findChildren(QWidget):
            child_sheet = child.styleSheet()
            if child_sheet and old_color.lower() in child_sheet.lower():
                child.setStyleSheet(child_sheet.replace(old_color, new_color))

    def update_images(self):
        for label, original_pixmap in self.images.items():
            if not original_pixmap.isNull():
                target_size = self.size() / 3.5
                scaled = original_pixmap.scaled(
                    target_size, Qt.KeepAspectRatio, Qt.SmoothTransformation
                )
                label.setPixmap(scaled)

    def resizeEvent(self, event):
        super().resizeEvent(event)
        self.update_images()

    def create_toolbar(self):
        self.toolbar = QToolBar("Main Toolbar")
        self.addToolBar(self.toolbar)
        self.toolbar.setStyleSheet(f"""
            QToolBar {{
                background-color: {ACCENT};
            }}
            QToolButton {{
                background-color: {ACCENT};
                border: none;
            }}
        """)
        self.toolbar.setIconSize(QSize(32, 32))
        self.toolbar.setFixedHeight(50)
        self.toolbar.setMovable(False)

        container = QWidget()
        container.setStyleSheet(f"background-color: {ACCENT};")
        layout = QHBoxLayout(container)
        layout.setContentsMargins(5, 0, 5, 0)
        layout.setSpacing(15)

        def make_button(icon_path, tooltip, callback):
            btn = QToolButton()
            btn.setIcon(QIcon(icon_path))
            btn.setIconSize(QSize(32, 32))
            btn.setToolTip(tooltip)
            btn.clicked.connect(callback)
            btn.setStyleSheet(f"""
                QToolButton {{
                    background-color: {ACCENT};
                    border: none;
                    padding: 6px;
                }}
            """)
            return btn

        layout.addSpacing(18)
        layout.addWidget(
            make_button(
                str(ASSETS_DIR / "Button 1.png"), "Regneark", self.open_wannabe_maple
            )
        )
        layout.addStretch()
        layout.addWidget(
            make_button(
                str(ASSETS_DIR / "Button 2.png"),
                "Molekyle Tegner",
                self.open_wannabe_marvin,
            )
        )
        layout.addStretch()
        layout.addWidget(
            make_button(str(ASSETS_DIR / "Button 3.png"), "Kemi", self.open_kemi_slop)
        )
        layout.addStretch()
        layout.addWidget(
            make_button(str(ASSETS_DIR / "Button 4.png"), "Fysik", self.open_fysik_slop)
        )
        layout.addStretch()
        layout.addWidget(
            make_button(
                str(ASSETS_DIR / "Button 5.png"), "Biotek", self.open_biotek_slop
            )
        )
        layout.addStretch()

        self.menu = QMenu(self)
        Menu_action = self.menu.addAction("Hovedmenu")
        Menu_action.triggered.connect(self.open_menu)

        Mapleslop_action = self.menu.addAction("Regneark")
        Mapleslop_action.triggered.connect(self.open_wannabe_maple)

        Marvin_action = self.menu.addAction("Molekyle Tegner")
        Marvin_action.triggered.connect(self.open_wannabe_marvin)

        Kemi_action = self.menu.addAction("Kemi")
        Kemi_action.triggered.connect(self.open_kemi_slop)

        Fysik_action = self.menu.addAction("Fysik")
        Fysik_action.triggered.connect(self.open_fysik_slop)

        Biotek_action = self.menu.addAction("Biotek")
        Biotek_action.triggered.connect(self.open_biotek_slop)

        Formula_action = self.menu.addAction("Formelsamling")
        Formula_action.triggered.connect(self.open_formula)

        Settings_action = self.menu.addAction("Indstillinger")
        Settings_action.triggered.connect(self.open_settings)

        exit_action = self.menu.addAction("Afslut")
        exit_action.triggered.connect(self.close_app)

        self.menu.setStyleSheet(f"""
            QMenu {{
                background-color: {SIDEBAR_BG};
                color: white;
                border: 1px solid {ACCENT};
                border-radius: 8px;
                padding: 6px;
            }}
            QMenu::item {{
                padding: 8px 20px;
                border-radius: 4px;
            }}
            QMenu::item:selected {{
                background-color: {ACCENT};
                color: {BG};
            }}
        """)

        menu_button = QToolButton()
        menu_button.setIcon(QIcon(str(ASSETS_DIR / "Button 6.png")))
        menu_button.setIconSize(QSize(32, 32))
        menu_button.setPopupMode(QToolButton.InstantPopup)
        menu_button.setMenu(self.menu)
        menu_button.setStyleSheet(f"""
            QToolButton {{
                background-color: {ACCENT};
                border: none;
                padding: 6px;
            }}
            QToolButton::menu-indicator {{
                image: none;
            }}
        """)
        layout.addWidget(menu_button)

        self.toolbar.addWidget(container)

    def create_formula_page(self):
        page = QWidget()
        outer_layout = QVBoxLayout(page)
        outer_layout.setContentsMargins(0, 0, 0, 0)
        outer_layout.setSpacing(0)

        scroll = QScrollArea()
        scroll.setWidgetResizable(True)
        scroll.setFrameShape(QScrollArea.NoFrame)
        scroll.setStyleSheet(f"""
            QScrollArea {{ background-color: {BG}; border: none; }}
            QScrollBar:vertical {{
                background: {PANEL_BG};
                width: 10px;
                margin: 0px;
                border-radius: 5px;
            }}
            QScrollBar::handle:vertical {{
                background: {ACCENT};
                border-radius: 5px;
                min-height: 24px;
            }}
            QScrollBar::add-line:vertical, QScrollBar::sub-line:vertical {{
                height: 0px;
            }}
            QScrollBar::add-page:vertical, QScrollBar::sub-page:vertical {{
                background: none;
            }}
        """)

        content = QWidget()
        content.setStyleSheet(f"background-color: {BG};")
        content_layout = QVBoxLayout(content)
        content_layout.setContentsMargins(40, 30, 40, 40)
        content_layout.setSpacing(28)

        header = QLabel("Formelsamling")
        header.setStyleSheet(
            f"color: {TEXT}; font-size: 24px; font-weight: bold; background: transparent;"
        )
        content_layout.addWidget(header)

        Empirisk_formel = QWidget()
        Empirisk_formel.setStyleSheet("background: transparent;")
        Empirisk_formel.setSizePolicy(QSizePolicy.Fixed, QSizePolicy.Fixed)
        Empirisk_formel_layout = QHBoxLayout(Empirisk_formel)
        Empirisk_formel_layout.setContentsMargins(0, 0, 0, 0)
        Empirisk_formel_layout.setSpacing(8)

        Empirisk_formel_formel = QLabel(
            "For at bestemme den empiriske formel skal du først tage dine masseprocenter og antage at det samlede molekyle vejer 100 gram, derfra kan man beregne en masse for hver grundstof.\nFor eksempel hvis du har 41,1% Carbon, 4,14% Nitrogen og 54,75% Oxygen, bliver det til 41,1 g Carbon, 4,14 g Nitrogen og 54,75 g Oxygen.\nDenne masse kan nu bruges til at beregne en stofmængde, her bruges molarmassen af hvert grundstof samt denne formel: n="
        )
        self._style_label(Empirisk_formel_formel)
        Empirisk_formel_layout.addWidget(Empirisk_formel_formel)

        masse_formel = QWidget()
        masse_formel.setStyleSheet("background: transparent;")
        masse_formel_layout = QHBoxLayout(masse_formel)
        masse_formel_layout.setContentsMargins(0, 0, 0, 0)
        masse_formel_layout.setSpacing(8)

        masse_formel_formel = QLabel(
            "Massen af et stof(m) kan bestemmes via formlen:       m = n·M\n\nm er masse målt i g\nn er stofmængde målt i mol \nM er molarmasse målt i g/mol "
        )
        self._style_label(masse_formel_formel)
        masse_formel_layout.addWidget(masse_formel_formel)

        content_layout.addWidget(
            self._settings_category(
                "Molekyleanalyse", [("Empirisk Formel", Empirisk_formel)]
            )
        )

        content_layout.addWidget(
            self._settings_category("Mængdeberegning", [("Masse Formel", masse_formel)])
        )

        content_layout.addStretch()

        scroll.setWidget(content)
        outer_layout.addWidget(scroll)

        self.stack.addWidget(page)

    def create_kemi_sidebar(self):
        sidebar = QWidget()
        sidebar.setFixedWidth(100)
        sidebar.setStyleSheet(f"background-color: {SIDEBAR_BG};")

        layout = QVBoxLayout(sidebar)
        layout.setContentsMargins(10, 10, 10, 10)
        layout.setSpacing(10)

        button_style = f"""
            QPushButton {{
                background-color: {PANEL_BG};
                color: {TEXT};
                border: 1px solid {ACCENT};
                border-radius: 6px;
                padding: 8px;
                font-size: 10px;
            }}
            QPushButton:hover {{
                background-color: {HOVER};
            }}
        """

        Preset_1 = QPushButton("Enhed")
        Preset_1.setStyleSheet(button_style)
        Preset_1.clicked.connect(self.Kemi_1_Pressed)
        layout.addWidget(Preset_1)

        Preset_2 = QPushButton("Analyse")
        Preset_2.setStyleSheet(button_style)
        Preset_2.clicked.connect(self.Kemi_2_Pressed)
        layout.addWidget(Preset_2)

        Preset_3 = QPushButton("Bjerrum")
        Preset_3.setStyleSheet(button_style)
        Preset_3.clicked.connect(self.Kemi_3_Pressed)
        layout.addWidget(Preset_3)

        Preset_4 = QPushButton("pH og pOH")
        Preset_4.setStyleSheet(button_style)
        Preset_4.clicked.connect(self.Kemi_4_Pressed)
        layout.addWidget(Preset_4)

        Preset_5 = QPushButton("Afstemning")
        Preset_5.setStyleSheet(button_style)
        Preset_5.clicked.connect(self.Kemi_5_Pressed)
        layout.addWidget(Preset_5)

        Preset_6 = QPushButton("Empirisk")
        Preset_6.setStyleSheet(button_style)
        Preset_6.clicked.connect(self.Kemi_6_Pressed)
        layout.addWidget(Preset_6)

        Preset_7 = QPushButton("Udbytte%")
        Preset_7.setStyleSheet(button_style)
        Preset_7.clicked.connect(self.Kemi_7_Pressed)
        layout.addWidget(Preset_7)

        Preset_8 = QPushButton("Volumen%")
        Preset_8.setStyleSheet(button_style)
        Preset_8.clicked.connect(self.Kemi_8_Pressed)
        layout.addWidget(Preset_8)

        Preset_9 = QPushButton("Masse%")
        Preset_9.setStyleSheet(button_style)
        Preset_9.clicked.connect(self.Kemi_9_Pressed)
        layout.addWidget(Preset_9)

        Preset_10 = QPushButton("MBeregning")
        Preset_10.setStyleSheet(button_style)
        Preset_10.clicked.connect(self.Kemi_10_Pressed)
        layout.addWidget(Preset_10)

        Preset_11 = QPushButton("Puffer")
        Preset_11.setStyleSheet(button_style)
        Preset_11.clicked.connect(self.Kemi_11_Pressed)
        layout.addWidget(Preset_11)

        Preset_12 = QPushButton("[H3O+]")
        Preset_12.setStyleSheet(button_style)
        Preset_12.clicked.connect(self.Kemi_12_Pressed)
        layout.addWidget(Preset_12)

        layout.addStretch()

        return sidebar

    def open_menu(self):
        self.stack.setCurrentIndex(0)

    def open_wannabe_maple(self):
        self.stack.setCurrentIndex(1)

    def open_wannabe_marvin(self):
        pass

    def open_kemi_slop(self):
        self.stack.setCurrentIndex(2)

    def open_fysik_slop(self):
        self.stack.setCurrentIndex(4)

    def open_biotek_slop(self):
        self.stack.setCurrentIndex(3)

    def open_settings(self):
        self.stack.setCurrentIndex(5)

    def open_formula(self):
        self.stack.setCurrentIndex(6)

    def keyPressEvent(self, event):
        if event.key() == Qt.Key_Escape:
            if self.isFullScreen():
                self.showNormal()

        elif event.key() == Qt.Key_F11:
            if not self.isFullScreen():
                self.showFullScreen()

    def run_maple(self):
        code_lines = self.maple_textbox.toPlainText().splitlines()
        result = interpreter.EV().ev("\n".join(code_lines))

        rows = []
        for i, code in enumerate(code_lines):
            rows.append(["code", code])
            for res_line in str(result.get(i, "")).splitlines():
                if res_line.startswith("Error"):
                    rows.append(["error", res_line])
                else:
                    rows.append(["math", calc_to_latex(res_line)])
        self.maple_results.page().runJavaScript(f"showResults({json.dumps(rows)})")

    def Kemi_1_Pressed(self):
        def calc(inputs, outputs):
            try:
                inte = interpreter.EV()
                a = inputs[0].text()
                b = inputs[1].text()
                if b == "SI":
                    text = f"SI {a}"
                else:
                    text = f"unit_convert {a} {b}"
                result = inte.ev(text)
                outputs[0].setText(str(result[0]))
            except ValueError:
                outputs[0].setText("Invalid Input")

        if "Kemi 1" not in self.kemi_panels:
            body = QWidget()
            body.setStyleSheet("background-color: transparent;")
            layout = QVBoxLayout(body)
            layout.setContentsMargins(6, 6, 6, 6)
            layout.setSpacing(6)

            field_style = f"""
                QLineEdit {{
                    background-color: {SIDEBAR_BG};
                    color: white;
                    border: 1px solid {ACCENT};
                    border-radius: 4px;
                    padding: 4px;
                    font-size: 12px;
                }}
            """

            value_input = MathInput()
            value_input.setPlaceholderText("Input[Enhed]")
            value_input.setStyleSheet(field_style)
            layout.addWidget(value_input)

            unit_row = QHBoxLayout()

            target_unit_input = MathInput()
            target_unit_input.setPlaceholderText("Ønsket Enhed")
            target_unit_input.setStyleSheet(field_style)
            unit_row.addWidget(target_unit_input)

            si_btn = QPushButton("SI")
            si_btn.setFixedSize(28, 28)
            si_btn.setToolTip("Konverter til SI")
            si_btn.setStyleSheet(f"""
                QPushButton {{
                    background-color: {PANEL_BG};
                    color: {TEXT};
                    border: 1px solid {ACCENT};
                    border-radius: 6px;
                }}
                QPushButton:hover {{ background-color: {HOVER}; }}
            """)
            unit_row.addWidget(si_btn)

            layout.addLayout(unit_row)

            calc_btn = QPushButton("Beregn")
            calc_btn.setStyleSheet(f"""
                QPushButton {{
                    background-color: {PANEL_BG};
                    color: {TEXT};
                    border: 1px solid {ACCENT};
                    border-radius: 6px;
                    padding: 6px;
                    font-size: 12px;
                }}
                QPushButton:hover {{ background-color: {HOVER}; }}
            """)
            layout.addWidget(calc_btn)

            result_output = MathOutput()
            result_output.setPlaceholderText("Resultat")
            result_output.setReadOnly(True)
            result_output.setStyleSheet(field_style)
            layout.addWidget(result_output)

            layout.addStretch()

            inputs = [value_input, target_unit_input]
            outputs = [result_output]

            calc_btn.clicked.connect(lambda: calc(inputs, outputs))
            value_input.returnPressed.connect(calc_btn.click)
            target_unit_input.returnPressed.connect(calc_btn.click)

            def to_si():
                target_unit_input.setText("SI")

            si_btn.clicked.connect(to_si)

            self.show_kemi_panel(
                "Kemi 1",
                "Enheds Omregner",
                body_widget=body,
                help_text="Indtast din originale værdi med dens enhed i det øverste input, brug . for decimaltal.\nHusk at skrive dens enhed inde i de firkantede parenteser [] for eksempel 10[km/t].\nDerefter indtast den ønskede enhed uden firkantede parenteser.\nFor at skrive sænket skrivt er det Shift+Bindestreg.\nFor at skrive hævet skrivt er det Shift+^.",
            )
        else:
            self.show_kemi_panel("Kemi 1", "Enheds Omregner")

    def Kemi_2_Pressed(self):
        def calc(inputs, outputs):
            try:
                inte = interpreter.EV()
                a = inputs[0].text()

                text = f"analysis {a}"
                result = inte.ev(text)
                results = result[0].splitlines()
                results = results[:5] + ["\n ".join(results[5:])]

                outputs[0].setText(str(results[0]))
                outputs[1].setText(str(results[1]))
                outputs[2].setText(str(results[2]))
                outputs[3].setText(str(results[3]))
                outputs[4].setText(str(results[4]))
                outputs[5].setPlainText(str(results[5]))
            except Exception as e:
                outputs[5].setPlainText(f"Error: {e}")

        if "Kemi 2" not in self.kemi_panels:
            body = QWidget()
            body.setStyleSheet("background-color: transparent;")
            layout = QVBoxLayout(body)
            layout.setContentsMargins(6, 6, 6, 6)
            layout.setSpacing(6)

            field_style = f"""
                QLineEdit, QTextEdit {{
                    background-color: {SIDEBAR_BG};
                    color: white;
                    border: 1px solid {ACCENT};
                    border-radius: 4px;
                    padding: 4px;
                    font-size: 12px;
                }}
            """

            molekyle_input = MathInput()
            molekyle_input.setPlaceholderText("Molekyle")
            molekyle_input.setStyleSheet(field_style)
            layout.addWidget(molekyle_input)

            calc_btn = QPushButton("Beregn")
            calc_btn.setStyleSheet(f"""
                QPushButton {{
                    background-color: {PANEL_BG};
                    color: {TEXT};
                    border: 1px solid {ACCENT};
                    border-radius: 6px;
                    padding: 6px;
                    font-size: 12px;
                }}
                QPushButton:hover {{ background-color: {HOVER}; }}
            """)
            layout.addWidget(calc_btn)

            labels = [
                "Molekyle formel",
                "Empirisk formel",
                "Molar masse",
                "DBE",
                "Antal atomer",
            ]
            outputs = []
            for label in labels:
                out = MathOutput()
                out.setPlaceholderText(label)
                out.setReadOnly(True)
                out.setStyleSheet(field_style)
                layout.addWidget(out)
                outputs.append(out)

            procent_output = QTextEdit()
            procent_output.setPlaceholderText("Procent indehold")
            procent_output.setReadOnly(True)
            procent_output.setStyleSheet(field_style)
            procent_output.setMinimumHeight(60)
            procent_output.setVerticalScrollBarPolicy(Qt.ScrollBarAsNeeded)
            layout.addWidget(procent_output)
            outputs.append(procent_output)

            layout.addStretch()

            inputs = [molekyle_input]

            calc_btn.clicked.connect(lambda: calc(inputs, outputs))
            molekyle_input.returnPressed.connect(calc_btn.click)

            self.show_kemi_panel(
                "Kemi 2",
                "Molekylær Analyse",
                body_widget=body,
                help_text="Indtast molekylet i input feltet.\nHusk at grundstoffer med navne der er længere end et bogstav er det kun det første der skal være stort.\nEksempelvis Fe3O4, Jernoxid.\nDBE formel kan kun andvendes til organiske molekyler.\nFor at skrive sænket skrivt er det Shift+Bindestreg.\nFor at skrive hævet skrivt er det Shift+^.",
            )
            if "Kemi 2" in self.kemi_panels:
                self.kemi_panels["Kemi 2"].resize(300, 480)

        else:
            self.show_kemi_panel("Kemi 2", "Molekylær Analyse")

    def Kemi_3_Pressed(self):
        key = "Kemi 3"

        def calc(pks_input, canvas_holder):
            text = pks_input.text().strip()
            try:
                pks = [float(p.strip()) for p in text.split(",") if p.strip() != ""]
                if not pks:
                    return
            except ValueError:
                return

            fig = chem.bjerrum_figure(pks)
            new_canvas = FigureCanvasQTAgg(fig)
            new_canvas.setStyleSheet("background-color: transparent;")

            layout = canvas_holder.layout()
            old_canvas = canvas_holder.property("canvas")
            if old_canvas is not None:
                layout.removeWidget(old_canvas)
                old_canvas.setParent(None)
                old_canvas.deleteLater()

            layout.addWidget(new_canvas)
            canvas_holder.setProperty("canvas", new_canvas)
            new_canvas.draw()

        if key not in self.kemi_panels:
            body = QWidget()
            body.setStyleSheet(f"background-color: {BG};")
            body_layout = QVBoxLayout(body)
            body_layout.setContentsMargins(6, 6, 6, 6)
            body_layout.setSpacing(6)

            field_style = f"""
                QLineEdit {{
                    background-color: {SIDEBAR_BG};
                    color: white;
                    border: 1px solid {ACCENT};
                    border-radius: 4px;
                    padding: 4px;
                    font-size: 12px;
                }}
            """

            input_row = QHBoxLayout()
            pks_input = MathInput()
            pks_input.setPlaceholderText("pKs 1, pKs 2, ...")
            pks_input.setStyleSheet(field_style)
            input_row.addWidget(pks_input)

            calc_btn = QPushButton("Beregn")
            calc_btn.setStyleSheet(f"""
                QPushButton {{
                    background-color: {PANEL_BG};
                    color: {TEXT};
                    border: 1px solid {ACCENT};
                    border-radius: 6px;
                    padding: 6px;
                    font-size: 12px;
                }}
                QPushButton:hover {{ background-color: {HOVER}; }}
            """)
            input_row.addWidget(calc_btn)

            body_layout.addLayout(input_row)

            canvas_holder = QWidget()
            canvas_holder_layout = QVBoxLayout(canvas_holder)
            canvas_holder_layout.setContentsMargins(0, 0, 0, 0)
            canvas_holder.setProperty("canvas", None)
            body_layout.addWidget(canvas_holder, stretch=1)

            calc_btn.clicked.connect(lambda: calc(pks_input, canvas_holder))
            pks_input.returnPressed.connect(calc_btn.click)

            self.show_kemi_panel(
                key,
                "Bjerrum",
                body_widget=body,
                help_text="Indtast pKs værdi for at opstille et bjerrumsdiagram.\nBrug . for at skrive decimaler og brug , for lave endu et diagram.\nFor eksempel 5.3, 4.1 dette laver to bjerrumsdiagrammer en med pKs på 5.3 og en med en pKs på 4.1.\nFor at skrive sænket skrivt er det Shift+Bindestreg.\nFor at skrive hævet skrivt er det Shift+^.",
            )
            self.kemi_panels[key].resize(420, 420)
        else:
            self.show_kemi_panel(key, "Bjerrum")

    def Kemi_4_Pressed(self):
        def calc(inputs, outputs):
            try:
                inte = interpreter.EV()
                a = inputs[0].text()
                b = inputs[1].text()
                c = inputs[2].text()
                if a and b:
                    outputs[0].setText("Error kan ikke tage både pKs og pKb")
                    outputs[1].setText("Error kan ikke tage både pKs og pKb")

                elif a:
                    text = f"pH {a} {c}"
                    result = inte.ev(text)
                    outputs[0].setText(str(result[0]))
                    outputs[1].setText(str(14 - float(result[0])))

                elif b:
                    text = f"pOH {b} {c}"
                    result = inte.ev(text)

                    outputs[1].setText(str(result[0]))
                    outputs[0].setText(str(14 - float(result[0])))

            except ValueError:
                outputs[0].setText("Invalid Input")
                outputs[1].setText("Invalid Input")

        if "Kemi 4" not in self.kemi_panels:
            body = self.make_input_output_body(
                input_labels=[
                    "pKs eller syre",
                    "pKb eller base",
                    "Koncentration[enhed]",
                ],
                output_labels=["pH", "pOH"],
                calc_callback=calc,
            )
            body.setStyleSheet("background-color: transparent;")
            self.show_kemi_panel(
                "Kemi 4",
                "pH og pOH",
                body_widget=body,
                help_text="Indtast enten en pKs værdi eller en pKb værdi samt dens koncentration.\nHusk . for decimaltal og angiv koncentrationens enhed i firkantede parenteser [].\nDu kan også bruge syren eller basens navn i stedet for pKs eller pKb, for nogle syrer og baser(Check Settings).\nDet øverste output er pH mens det nederste er pOH.\nStandard enhed for koncentration er mol/l.\nFor at skrive sænket skrivt er det Shift+Bindestreg.\nFor at skrive hævet skrivt er det Shift+^.",
            )
        else:
            self.show_kemi_panel("Kemi 4", "pH og pOH")

    def Kemi_5_Pressed(self):
        def calc(inputs, outputs):
            try:
                inte = interpreter.EV()
                a = inputs[0].text()
                b = inputs[1].text()
                if b:
                    text = f"balance_reaction {b} {a}"
                else:
                    text = f"balance_reaction {"None"} {a}"
                result = inte.ev(text)
                outputs[0].setText(str(result[0]))
            except ValueError:
                outputs[0].setText("Invalid Input")

        if "Kemi 5" not in self.kemi_panels:
            body = self.make_input_output_body(
                input_labels=["Reaktant -> Produkt", "Opløsning"],
                output_labels=["Resultat"],
                calc_callback=calc,
            )
            body.setStyleSheet("background-color: transparent;")
            self.show_kemi_panel(
                "Kemi 5",
                "Afstemning",
                body_widget=body,
                help_text="Indtast din ubalancerede reaktion i input kassen.\nHusk at grundstoffer med navne der er længere end et bogstav er det kun det første der skal være stort.\nBrug pil mellem dine reaktanter og produkter ->.\nFor eksempel H₂O -> H₂ + O₂.\nVed redoxreaktioner bruges opløsningens boksen hvor der skrives enten syre eller base afhængig af opløsningen.\nFor at skrive sænket skrivt er det Shift+Bindestreg.\nFor at skrive hævet skrivt er det Shift+^.",
            )
        else:
            self.show_kemi_panel("Kemi 5", "Afstemning")

    def Kemi_6_Pressed(self):
        pass

    def Kemi_7_Pressed(self):
        def calc(inputs, outputs):
            try:
                inte = interpreter.EV()
                a = inputs[0].text()
                b = inputs[1].text()
                text = f"udbytteprocent {a} {b}"
                result = inte.ev(text)
                outputs[0].setText(str(result[0]))
            except ValueError:
                outputs[0].setText("Invalid Input")

        if "Kemi 7" not in self.kemi_panels:
            body = self.make_input_output_body(
                input_labels=["Teoretisk[Enhed]", "Praktisk[Enhed]"],
                output_labels=["Udbytteprocent"],
                calc_callback=calc,
            )
            body.setStyleSheet("background-color: transparent;")
            self.show_kemi_panel(
                "Kemi 7",
                "Udbytteprocent",
                body_widget=body,
                help_text="Indtast din teoretiske udbytte i det første input og praktisk udbytte i anden input.\nHusk . for decimal og set enheder inde i firkantet parentes[].\nEksempelvis 4[kg] 300[g].\nStandard enheden er kg.\nFor at skrive sænket skrivt er det Shift+Bindestreg.\nFor at skrive hævet skrivt er det Shift+^.",
            )
        else:
            self.show_kemi_panel("Kemi 7", "Udbytteprocent")

    def Kemi_8_Pressed(self):
        def calc(inputs, outputs):
            try:
                inte = interpreter.EV()
                a = inputs[0].text()
                b = inputs[1].text()
                text = f"volumenprocent {a} {b}"
                result = inte.ev(text)
                outputs[0].setText(str(result[0]))
            except ValueError:
                outputs[0].setText("Invalid Input")

        if "Kemi 8" not in self.kemi_panels:
            body = self.make_input_output_body(
                input_labels=["Blanding[Enhed]", "Stof[Enhed]"],
                output_labels=["Volumenprocent"],
                calc_callback=calc,
            )
            body.setStyleSheet("background-color: transparent;")
            self.show_kemi_panel(
                "Kemi 8",
                "Volumenprocent",
                body_widget=body,
                help_text="Indtast din samlede volumen i det første input og specifik volumen i anden input.\nHusk . for decimal og set enheder inde i firkantet parentes[].\nEksempelvis 4[l] 300[dl].\nStandard enheden er l.\nFor at skrive sænket skrivt er det Shift+Bindestreg.\nFor at skrive hævet skrivt er det Shift+^.",
            )
        else:
            self.show_kemi_panel("Kemi 8", "Volumenprocent")

    def Kemi_9_Pressed(self):
        def calc(inputs, outputs):
            try:
                inte = interpreter.EV()
                a = inputs[0].text()
                b = inputs[1].text()
                text = f"masseprocent {a} {b}"
                result = inte.ev(text)
                outputs[0].setText(str(result[0]))
            except ValueError:
                outputs[0].setText("Invalid Input")

        if "Kemi 9" not in self.kemi_panels:
            body = self.make_input_output_body(
                input_labels=["Blanding[Enhed]", "Stof[Enhed]"],
                output_labels=["Masseprocent"],
                calc_callback=calc,
            )
            body.setStyleSheet("background-color: transparent;")
            self.show_kemi_panel(
                "Kemi 9",
                "Masseprocent",
                body_widget=body,
                help_text="Indtast din samlede masse i det første input og specifik masse i anden input.\nHusk . for decimal og set enheder inde i firkantet parentes[].\nEksempelvis 4[kg] 300[g].\nStandard enheden er kg.\nFor at skrive sænket skrivt er det Shift+Bindestreg.\nFor at skrive hævet skrivt er det Shift+^.",
            )
        else:
            self.show_kemi_panel("Kemi 9", "Masseprocent")

    def Kemi_10_Pressed(self):
        def calc(inputs, outputs):
            try:
                inte = interpreter.EV()
                a = inputs[0].text()
                b = inputs[1].text()
                c = inputs[2].text()
                d = inputs[3].text()
                e = inputs[4].text()
                f = inputs[5].text()

                values = [f"m={a}", f"V={b}", f"n={c}", f"c={d}", f"M={e}", f"p={f}"]
                values2 = [a, b, c, d, e, f]
                values = [x for x, y in zip(values, values2) if y != ""]
                values = " ".join(values)

                text = f"mængdeberegning {values}"
                result = inte.ev(text)
                outputs[0].setPlainText(str(result[0]))
            except ValueError:
                outputs[0].setPlainText("Invalid Input")

        if "Kemi 10" not in self.kemi_panels:
            body = QWidget()
            body.setStyleSheet("background-color: transparent;")
            layout = QVBoxLayout(body)
            layout.setContentsMargins(6, 6, 6, 6)
            layout.setSpacing(6)

            field_style = f"""
                QLineEdit, QTextEdit {{
                    background-color: {SIDEBAR_BG};
                    color: white;
                    border: 1px solid {ACCENT};
                    border-radius: 4px;
                    padding: 4px;
                    font-size: 12px;
                }}
            """

            input_labels = [
                "Masse",
                "Volumen",
                "Stofmængde",
                "Koncentration",
                "Molarmasse",
                "Densitet",
            ]
            inputs = []
            for label in input_labels:
                line = MathInput()
                line.setPlaceholderText(label)
                line.setStyleSheet(field_style)
                layout.addWidget(line)
                inputs.append(line)

            calc_btn = QPushButton("Beregn")
            calc_btn.setStyleSheet(f"""
                QPushButton {{
                    background-color: {PANEL_BG};
                    color: {TEXT};
                    border: 1px solid {ACCENT};
                    border-radius: 6px;
                    padding: 6px;
                    font-size: 12px;
                }}
                QPushButton:hover {{ background-color: {HOVER}; }}
            """)
            layout.addWidget(calc_btn)

            result_output = QTextEdit()
            result_output.setPlaceholderText("Held og lykke:)")
            result_output.setReadOnly(True)
            result_output.setStyleSheet(field_style)
            result_output.setMinimumHeight(120)
            result_output.setVerticalScrollBarPolicy(Qt.ScrollBarAsNeeded)
            layout.addWidget(result_output)

            outputs = [result_output]

            layout.addStretch()

            calc_btn.clicked.connect(lambda: calc(inputs, outputs))
            for line in inputs:
                line.returnPressed.connect(calc_btn.click)

            self.show_kemi_panel(
                "Kemi 10",
                "Mængdeberegning",
                body_widget=body,
                help_text="Indtast din tilgængelige data i deres respektive input.\nHusk . for decimal og set enheder inde i firkantet parentes[].\nDen beregner alt den mulige data fra det givne input så du behøver ikke at fylde alle inputs.\nStandard enheden for masse er g.\nStandard enheden for volumen er l.\nStandard enheden for stofmængde er mol.\nStandard enheden for koncentration er mol/l.\nStandard enheden for molarmasse er g/mol.\nStandard enheden for densitet er kg/l.\nFor at skrive sænket skrivt er det Shift+Bindestreg.\nFor at skrive hævet skrivt er det Shift+^.",
            )
            if "Kemi 10" in self.kemi_panels:
                self.kemi_panels["Kemi 10"].resize(300, 480)

        else:
            self.show_kemi_panel("Kemi 10", "Mængdeberegning")

    def Kemi_11_Pressed(self):
        def calc(inputs, outputs):
            try:
                inte = interpreter.EV()
                a = inputs[0].text()
                b = inputs[1].text()
                c = inputs[2].text()
                text = f"puffer {a} {b} {c}"
                result = inte.ev(text)
                outputs[0].setText(str(result[0]))
            except ValueError:
                outputs[0].setText("Invalid Input")

        if "Kemi 11" not in self.kemi_panels:
            body = self.make_input_output_body(
                input_labels=[
                    "Stofmængde eller koncentration af syre[Enhed]",
                    "Stofmængde eller koncentration af base[Enhed]",
                    "pKs",
                ],
                output_labels=["pH"],
                calc_callback=calc,
            )
            body.setStyleSheet("background-color: transparent;")
            self.show_kemi_panel(
                "Kemi 11",
                "pH i puffer",
                body_widget=body,
                help_text="Input stofmængden eller koncentrationen af syren, stofmængden eller koncentrationen af basen og syrens pKs.\nHusk . for decimal og set enheder inde i firkantet parentes[].\nStandard enhed for stofmængde er mol.\nStandard enhed for koncentration er mol/l.\nFor at skrive sænket skrivt er det Shift+Bindestreg.\nFor at skrive hævet skrivt er det Shift+^.",
            )
        else:
            self.show_kemi_panel("Kemi 11", "pH i puffer")

    def Kemi_12_Pressed(self):
        def calc(inputs, outputs):
            try:
                inte = interpreter.EV()
                a = inputs[0].text()
                b = inputs[1].text()
                if a and b:
                    outputs[0].setText("Error kan ikke tage både pH og pOH")
                    outputs[1].setText("Error kan ikke tage både pH og pOH")

                elif a:
                    text = f"pH_to_concentration {a}"
                    result = inte.ev(text)
                    outputs[0].setText(str(result[0].split("\n")[0]))
                    outputs[1].setText(str(result[0].split("\n")[1]))

                elif b:
                    text = f"pOH_to_concentration {b}"
                    result = inte.ev(text)
                    outputs[0].setText(str(result[0].split("\n")[0]))
                    outputs[1].setText(str(result[0].split("\n")[1]))

            except ValueError:
                outputs[0].setText("Invalid Input")
                outputs[1].setText("Invalid Input")

        if "Kemi 12" not in self.kemi_panels:
            body = self.make_input_output_body(
                input_labels=[
                    "pH",
                    "pOH",
                ],
                output_labels=["[H3O+]", "OH-"],
                calc_callback=calc,
            )
            body.setStyleSheet("background-color: transparent;")
            self.show_kemi_panel(
                "Kemi 12",
                "[H3O+] og [OH-]",
                body_widget=body,
                help_text="Input enten pH eller pOH.\nHusk . for decimaler.\nFor at skrive sænket skrivt er det Shift+Bindestreg.\nFor at skrive hævet skrivt er det Shift+^.",
            )
        else:
            self.show_kemi_panel("Kemi 12", "[H3O+] og [OH-]")

    def on_shape_placed(self, shape_type, x, y):

        if shape_type == "Square":

            name = f"M_{træ.M_amount}"
            træ.M_amount += 1
            træ.add_node(name, x, y, self.gen, "M")
        if shape_type == "Circle":

            name = f"F_{træ.F_amount}"
            træ.F_amount += 1
            træ.add_node(name, x, y, self.gen, "F")

    def new_gen(self):
        self.gen += 1

    def Biotek_1_Pressed(self):
        def calc(inputs, outputs):
            try:
                inte = interpreter.EV()
                a = inputs[0].text()
                b = inputs[1].text()
                if b == "SI":
                    text = f"SI {a}"
                else:
                    text = f"unit_convert {a} {b}"
                result = inte.ev(text)
                outputs[0].setText(str(result[0]))
            except ValueError:
                outputs[0].setText("Invalid Input")

        if "Biotek 1" not in self.biotek_panels:
            body = QWidget()
            body.setStyleSheet("background-color: transparent;")
            layout = QVBoxLayout(body)
            layout.setContentsMargins(6, 6, 6, 6)
            layout.setSpacing(6)

            field_style = f"""
                QLineEdit {{
                    background-color: {SIDEBAR_BG};
                    color: white;
                    border: 1px solid {ACCENT};
                    border-radius: 4px;
                    padding: 4px;
                    font-size: 12px;
                }}
            """

            value_input = MathInput()
            value_input.setPlaceholderText("Input[Enhed]")
            value_input.setStyleSheet(field_style)
            layout.addWidget(value_input)

            unit_row = QHBoxLayout()

            target_unit_input = MathInput()
            target_unit_input.setPlaceholderText("Ønsket Enhed")
            target_unit_input.setStyleSheet(field_style)
            unit_row.addWidget(target_unit_input)

            si_btn = QPushButton("SI")
            si_btn.setFixedSize(28, 28)
            si_btn.setToolTip("Konverter til SI")
            si_btn.setStyleSheet(f"""
                QPushButton {{
                    background-color: {PANEL_BG};
                    color: {TEXT};
                    border: 1px solid {ACCENT};
                    border-radius: 6px;
                }}
                QPushButton:hover {{ background-color: {HOVER}; }}
            """)
            unit_row.addWidget(si_btn)

            layout.addLayout(unit_row)

            calc_btn = QPushButton("Beregn")
            calc_btn.setStyleSheet(f"""
                QPushButton {{
                    background-color: {PANEL_BG};
                    color: {TEXT};
                    border: 1px solid {ACCENT};
                    border-radius: 6px;
                    padding: 6px;
                    font-size: 12px;
                }}
                QPushButton:hover {{ background-color: {HOVER}; }}
            """)
            layout.addWidget(calc_btn)

            result_output = MathOutput()
            result_output.setPlaceholderText("Resultat")
            result_output.setReadOnly(True)
            result_output.setStyleSheet(field_style)
            layout.addWidget(result_output)

            layout.addStretch()

            inputs = [value_input, target_unit_input]
            outputs = [result_output]

            calc_btn.clicked.connect(lambda: calc(inputs, outputs))
            value_input.returnPressed.connect(calc_btn.click)
            target_unit_input.returnPressed.connect(calc_btn.click)

            def to_si():
                target_unit_input.setText("SI")

            si_btn.clicked.connect(to_si)

            self.show_biotek_panel(
                "Biotek 1",
                "Enheds Omregner",
                body_widget=body,
                help_text="Indtast din originale værdi med dens enhed i det øverste input, brug . for decimaltal.\nHusk at skrive dens enhed inde i de firkantede parenteser [] for eksempel 10[km/t].\nDerefter indtast den ønskede enhed uden firkantede parenteser.\nFor at skrive sænket skrivt er det Shift+Bindestreg.\nFor at skrive hævet skrivt er det Shift+^.",
            )
        else:
            self.show_biotek_panel("Biotek 1", "Enheds Omregner")

    def Biotek_2_Pressed(self):
        key = "Biotek 2"
        if key not in self.biotek_panels:
            body, canvas, new_gen_btn = make_shape_drawer_body()
            canvas.shape_placed.connect(self.on_shape_placed)
            new_gen_btn.clicked.connect(self.new_gen)
            self.show_biotek_panel(key, "Stamtræsanalyse", body_widget=body)
            self.biotek_panels[key].resize(840, 640)
        else:
            self.show_biotek_panel(key, "Stamtræsanalyse")

    def Biotek_3_Pressed(self):
        def calc(inputs, outputs):
            try:
                inte = interpreter.EV()
                a = inputs[0].text()
                b = inputs[1].text()
                text = f"mutations_analyse_DNA {a}, {b}"
                result = inte.ev(text)
                outputs[0].setPlainText(str(result[0]))
            except ValueError:
                outputs[0].setPlainText("Invalid Input")

        if "Biotek 3" not in self.biotek_panels:
            body = QWidget()
            body.setStyleSheet("background-color: transparent;")
            layout = QVBoxLayout(body)
            layout.setContentsMargins(6, 6, 6, 6)
            layout.setSpacing(6)

            field_style = f"""
                QLineEdit, QTextEdit {{
                    background-color: {SIDEBAR_BG};
                    color: white;
                    border: 1px solid {ACCENT};
                    border-radius: 4px;
                    padding: 4px;
                    font-size: 12px;
                }}
            """

            input_labels = ["Rask", "Muteret"]
            inputs = []
            for label in input_labels:
                line = MathInput(text_mode=True)
                line.setPlaceholderText(label)
                line.setStyleSheet(field_style)
                layout.addWidget(line)
                inputs.append(line)

            calc_btn = QPushButton("Beregn")
            calc_btn.setStyleSheet(f"""
                QPushButton {{
                    background-color: {PANEL_BG};
                    color: {TEXT};
                    border: 1px solid {ACCENT};
                    border-radius: 6px;
                    padding: 6px;
                    font-size: 12px;
                }}
                QPushButton:hover {{ background-color: {HOVER}; }}
            """)
            layout.addWidget(calc_btn)

            result_output = QTextEdit()
            result_output.setPlaceholderText("Resultat")
            result_output.setReadOnly(True)
            result_output.setStyleSheet(field_style)
            result_output.setMinimumHeight(120)
            result_output.setVerticalScrollBarPolicy(Qt.ScrollBarAsNeeded)
            layout.addWidget(result_output)

            outputs = [result_output]

            layout.addStretch()

            calc_btn.clicked.connect(lambda: calc(inputs, outputs))
            for line in inputs:
                line.returnPressed.connect(calc_btn.click)

            self.show_biotek_panel(
                "Biotek 3",
                "DNA Mutations Analyse",
                body_widget=body,
                help_text="Intast den raske DNA streng øverst derefter den muterede.\nDer må gerne værre mellemrum mellem codonerne og baserne må være med stor og småt.\nFor eksempel AAT gcc TTG.\nFor at skrive sænket skrivt er det Shift+Bindestreg.\nFor at skrive hævet skrivt er det Shift+^.",
            )
            if "Biotek 3" in self.biotek_panels:
                self.biotek_panels["Biotek 3"].resize(300, 480)

        else:
            self.show_biotek_panel("Biotek 3", "DNA Mutations Analyse")

    def Biotek_4_Pressed(self):
        def calc(inputs, outputs):
            try:
                inte = interpreter.EV()
                a = inputs[0].text()
                b = inputs[1].text()
                text = f"mutations_analyse_RNA {a}, {b}"
                result = inte.ev(text)
                outputs[0].setPlainText(str(result[0]))
            except ValueError:
                outputs[0].setPlainText("Invalid Input")

        if "Biotek 4" not in self.biotek_panels:
            body = QWidget()
            body.setStyleSheet("background-color: transparent;")
            layout = QVBoxLayout(body)
            layout.setContentsMargins(6, 6, 6, 6)
            layout.setSpacing(6)

            field_style = f"""
                QLineEdit, QTextEdit {{
                    background-color: {SIDEBAR_BG};
                    color: white;
                    border: 1px solid {ACCENT};
                    border-radius: 4px;
                    padding: 4px;
                    font-size: 12px;
                }}
            """

            input_labels = ["Rask", "Muteret"]
            inputs = []
            for label in input_labels:
                line = MathInput(text_mode=True)
                line.setPlaceholderText(label)
                line.setStyleSheet(field_style)
                layout.addWidget(line)
                inputs.append(line)

            calc_btn = QPushButton("Beregn")
            calc_btn.setStyleSheet(f"""
                QPushButton {{
                    background-color: {PANEL_BG};
                    color: {TEXT};
                    border: 1px solid {ACCENT};
                    border-radius: 6px;
                    padding: 6px;
                    font-size: 12px;
                }}
                QPushButton:hover {{ background-color: {HOVER}; }}
            """)
            layout.addWidget(calc_btn)

            result_output = QTextEdit()
            result_output.setPlaceholderText("Resultat")
            result_output.setReadOnly(True)
            result_output.setStyleSheet(field_style)
            result_output.setMinimumHeight(120)
            result_output.setVerticalScrollBarPolicy(Qt.ScrollBarAsNeeded)
            layout.addWidget(result_output)

            outputs = [result_output]

            layout.addStretch()

            calc_btn.clicked.connect(lambda: calc(inputs, outputs))
            for line in inputs:
                line.returnPressed.connect(calc_btn.click)

            self.show_biotek_panel(
                "Biotek 4",
                "RNA Mutations Analyse",
                body_widget=body,
                help_text="Intast den raske RNA streng øverst derefter den muterede.\nDer må gerne værre mellemrum mellem codonerne og baserne må være med stor og småt.\nFor eksempel AAU gcc UUG.\nFor at skrive sænket skrivt er det Shift+Bindestreg.\nFor at skrive hævet skrivt er det Shift+^.",
            )
            if "Biotek 4" in self.biotek_panels:
                self.biotek_panels["Biotek 4"].resize(300, 480)

        else:
            self.show_biotek_panel("Biotek 4", "RNA Mutations Analyse")

    def Biotek_5_Pressed(self):
        def calc(inputs, outputs):
            try:
                inte = interpreter.EV()
                a = inputs[0].text()
                b = inputs[1].text()
                if a and b:
                    outputs[0].setText("Enten DNA eller RNA")

                elif a:
                    text = f"DNA_til_peptid {a}"

                    result = inte.ev(text)

                    outputs[0].setText(str(result[0]))

                elif b:
                    text = f"RNA_til_peptid {b}"

                    result = inte.ev(text)

                    outputs[0].setText(str(result[0]))

            except ValueError:
                outputs[0].setText("Invalid Input")

        if "Biotek 5" not in self.biotek_panels:
            body = self.make_input_output_body(
                input_labels=["DNA streng", "RNA streng"],
                output_labels=["Peptidkæde"],
                calc_callback=calc,
            )
            body.setStyleSheet("background-color: transparent;")
            self.show_biotek_panel(
                "Biotek 5",
                "Translation",
                body_widget=body,
                help_text="Indtast enten DNA eller RNA streng.\nDer må gerne værre mellemrum mellem codonerne og baserne må være med stor og småt.\nFor eksempel AAT gcc TTG eller AAUGCCUUU.\nFor at skrive sænket skrivt er det Shift+Bindestreg.\nFor at skrive hævet skrivt er det Shift+^.",
            )
        else:
            self.show_biotek_panel("Biotek 5", "Translation")

    def Fysik_1_Pressed(self):
        def calc(inputs, outputs):
            try:
                inte = interpreter.EV()
                a = inputs[0].text()
                b = inputs[1].text()
                if b == "SI":
                    text = f"SI {a}"
                else:
                    text = f"unit_convert {a} {b}"
                result = inte.ev(text)
                outputs[0].setText(str(result[0]))
            except ValueError:
                outputs[0].setText("Invalid Input")

        if "Fysik 1" not in self.fysik_panels:
            body = QWidget()
            body.setStyleSheet("background-color: transparent;")
            layout = QVBoxLayout(body)
            layout.setContentsMargins(6, 6, 6, 6)
            layout.setSpacing(6)

            field_style = f"""
                QLineEdit {{
                    background-color: {SIDEBAR_BG};
                    color: white;
                    border: 1px solid {ACCENT};
                    border-radius: 4px;
                    padding: 4px;
                    font-size: 12px;
                }}
            """

            value_input = MathInput()
            value_input.setPlaceholderText("Input[Enhed]")
            value_input.setStyleSheet(field_style)
            layout.addWidget(value_input)

            unit_row = QHBoxLayout()

            target_unit_input = MathInput()
            target_unit_input.setPlaceholderText("Ønsket Enhed")
            target_unit_input.setStyleSheet(field_style)
            unit_row.addWidget(target_unit_input)

            si_btn = QPushButton("SI")
            si_btn.setFixedSize(28, 28)
            si_btn.setToolTip("Konverter til SI")
            si_btn.setStyleSheet(f"""
                QPushButton {{
                    background-color: {PANEL_BG};
                    color: {TEXT};
                    border: 1px solid {ACCENT};
                    border-radius: 6px;
                }}
                QPushButton:hover {{ background-color: {HOVER}; }}
            """)
            unit_row.addWidget(si_btn)

            layout.addLayout(unit_row)

            calc_btn = QPushButton("Beregn")
            calc_btn.setStyleSheet(f"""
                QPushButton {{
                    background-color: {PANEL_BG};
                    color: {TEXT};
                    border: 1px solid {ACCENT};
                    border-radius: 6px;
                    padding: 6px;
                    font-size: 12px;
                }}
                QPushButton:hover {{ background-color: {HOVER}; }}
            """)
            layout.addWidget(calc_btn)

            result_output = MathOutput()
            result_output.setPlaceholderText("Resultat")
            result_output.setReadOnly(True)
            result_output.setStyleSheet(field_style)
            layout.addWidget(result_output)

            layout.addStretch()

            inputs = [value_input, target_unit_input]
            outputs = [result_output]

            calc_btn.clicked.connect(lambda: calc(inputs, outputs))
            value_input.returnPressed.connect(calc_btn.click)
            target_unit_input.returnPressed.connect(calc_btn.click)

            def to_si():
                target_unit_input.setText("SI")

            si_btn.clicked.connect(to_si)

            self.show_fysik_panel(
                "Fysik 1",
                "Enheds Omregner",
                body_widget=body,
                help_text="Indtast din originale værdi med dens enhed i det øverste input, brug . for decimaltal.\nHusk at skrive dens enhed inde i de firkantede parenteser [] for eksempel 10[km/t].\nDerefter indtast den ønskede enhed uden firkantede parenteser.\nFor at skrive sænket skrivt er det Shift+Bindestreg.\nFor at skrive hævet skrivt er det Shift+^.",
            )
        else:
            self.show_fysik_panel("Fysik 1", "Enheds Omregner")

    def Fysik_2_Pressed(self):
        pass

    def Fysik_3_Pressed(self):
        pass

    def Fysik_4_Pressed(self):
        pass

    def Fysik_5_Pressed(self):
        pass

    def Fysik_6_Pressed(self):
        pass

    def Fysik_7_Pressed(self):
        pass

    def Fysik_8_Pressed(self):
        pass

    def Fysik_9_Pressed(self):
        pass

    def Fysik_10_Pressed(self):
        pass

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
