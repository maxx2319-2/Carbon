import json
import subprocess
import sys
from pathlib import Path

import pytest

pytest.importorskip("PySide6.QtWebEngineWidgets")

SRC = Path(__file__).resolve().parent.parent / "src"

SCRIPT = r"""
import base64, json, os, sys
os.environ["QT_QPA_PLATFORM"] = "offscreen"
os.environ["QTWEBENGINE_CHROMIUM_FLAGS"] = "--disable-gpu --disable-gpu-compositing --log-level=3"
sys.path.insert(0, sys.argv[1])
from PySide6.QtCore import QBuffer, QByteArray, QEventLoop, QTimer, QUrl
from PySide6.QtGui import QColor, QImage
from PySide6.QtWebEngineWidgets import QWebEngineView
from PySide6.QtWidgets import QApplication
from path import resource_path

app = QApplication([])
zoom = float(sys.argv[2])

def pump(ms):
    loop = QEventLoop(); QTimer.singleShot(ms, loop.quit); loop.exec()

def js(code):
    out = []; loop = QEventLoop(); v.page().runJavaScript(code, 0, lambda r: (out.append(r), loop.quit())); loop.exec(); return out[0]

img = QImage(120, 60, QImage.Format_RGB32); img.fill(QColor("#e05050"))
ba = QByteArray(); buf = QBuffer(ba); buf.open(QBuffer.WriteOnly); img.save(buf, "PNG")
pic = "data:image/png;base64," + base64.b64encode(bytes(ba)).decode()
rows = [["code", ""], ["code", pic, "picture"], ["code", ""], ["code", "urt"], ["code", "urt^4"], ["code", r"\text{fojwjfow fwifjwo}", "text"], ["code", ""]]

v = QWebEngineView(); v.resize(int(320 * zoom), int(340 * zoom)); v.setZoomFactor(zoom); v.show()
loop = QEventLoop(); v.loadFinished.connect(loop.quit)
v.load(QUrl.fromLocalFile(str(resource_path("Assets_math_live/regneark.html")))); loop.exec()
pump(800)
js(f"setSheet({json.dumps(rows)}); true")
pump(500)
js("(() => { const L = lines(); sel = {anchor:{mf:L[0],offset:0}, focus:{mf:L[6],offset:0}}; paint(); return true; })()")
pump(800)
rects = json.loads(js("JSON.stringify(lines().map(mf => { const r = mf.getBoundingClientRect(); return [r.top, r.bottom]; }))"))
shot = v.grab().toImage()
print(json.dumps({"zoom": zoom, "rows": rects, "pixels": [[shot.pixelColor(x, y).name() for x in range(shot.width())] for y in range(shot.height())]}))
"""

BG = "#404040"
EMPTY, PICTURE, POWER, TEXT = 0, 1, 4, 5


@pytest.fixture(scope="module", params=[1.0, 1.5, 2.0], ids=lambda z: f"zoom{z}")
def shot(request):
    out = subprocess.run([sys.executable, "-c", SCRIPT, str(SRC), str(request.param)], capture_output=True, text=True, timeout=120)
    return json.loads(next(l for l in out.stdout.splitlines() if l.startswith("{")))


def y_of(shot, i, at):
    top, bottom = shot["rows"][i]
    return int((top + (bottom - top) * at) * shot["zoom"])


def first_coloured(pixels, shot):
    return next(x for x, c in enumerate(pixels) if x > 50 * shot["zoom"] and c != BG)


def run_of(pixels, shot):
    start = first_coloured(pixels, shot)
    return start, start + pixels[start:].index(BG)


def test_render_is_not_blank(shot):
    assert any(c != BG for c in shot["pixels"][y_of(shot, TEXT, 0.5)])


@pytest.mark.parametrize("at", [0.1, 0.5, 0.9])
def test_power_line_has_no_holes(shot, at):
    pixels = shot["pixels"][y_of(shot, POWER, at)]
    start, end = run_of(pixels, shot)
    assert end - start > 20 * shot["zoom"]


def test_exponent_has_no_darker_stripe(shot):
    pixels = shot["pixels"][y_of(shot, POWER, 0.08)]
    start, end = run_of(pixels, shot)
    assert len(set(pixels[start:end])) == 1


def test_no_seam_before_newline_marker(shot):
    pixels = shot["pixels"][y_of(shot, POWER, 0.5)]
    _, end = run_of(pixels, shot)
    assert all(c == BG for c in pixels[end:end + int(20 * shot["zoom"])])


def test_picture_lines_up_with_text(shot):
    pic = first_coloured(shot["pixels"][y_of(shot, PICTURE, 0.5)], shot)
    text = first_coloured(shot["pixels"][y_of(shot, TEXT, 0.5)], shot)
    assert abs(pic - text) <= 1


def test_no_gap_around_picture(shot):
    z = shot["zoom"]
    top = int(shot["rows"][EMPTY][0] * z) + 1
    bottom = int(shot["rows"][PICTURE + 1][1] * z) - 1
    column = first_coloured(shot["pixels"][y_of(shot, PICTURE, 0.5)], shot)
    assert all(shot["pixels"][y][column] != BG for y in range(top, bottom))
