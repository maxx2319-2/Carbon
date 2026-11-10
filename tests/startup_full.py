import os
import sys
import time
import threading
import importlib

os.environ["QT_QPA_PLATFORM"] = "offscreen"
SRC = os.path.join(os.path.dirname(os.path.abspath(__file__)), "..", "src")
sys.path.insert(0, SRC)
sys.argv = [os.path.join(SRC, "main.py")]

from PySide6.QtCore import QEventLoop, QTimer, Qt
from PySide6.QtWidgets import QApplication

start = time.time()

def log(msg):
    print(f"{time.time() - start:6.2f}s  {msg}", flush=True)

QApplication.setAttribute(Qt.AA_ShareOpenGLContexts)
import main
app = main.CarbonApp(sys.argv)
splash = main.Splash(app)
orig_status = splash.status
def status(text):
    if getattr(splash, "_last", None) != text:
        splash._last = text
        if not text.startswith("Indlæser ") or text in ("Indlæser Carbon",) or " og " in text or "regneark" in text or "molekyle" in text:
            log("status: " + text)
    orig_status(text)
splash.status = status

modules = ["pandas", "sympy", "scipy.optimize", "matplotlib.pyplot", "mendeleev.fetch"]
if os.environ.get("MODE") == "without":
    modules = modules[:-1]
log(f"modules: {modules}")

def load():
    for name in modules:
        t = time.time()
        importlib.import_module(name)
        log(f"imported {name} in {time.time() - t:.2f}s")

loader = threading.Thread(target=load, daemon=True)
loop = QEventLoop()
timer = QTimer(interval=50)
timer.timeout.connect(lambda: (not loader.is_alive()) and loop.quit())
loader.start()
timer.start()
loop.exec()
timer.stop()

import gui
log("imported gui")
splash.status("Bygger GUI")
window = gui.MainWindow()
app.window = window
log("MainWindow built")
gui.preload(window, splash)
log("preload done")
os._exit(0)
