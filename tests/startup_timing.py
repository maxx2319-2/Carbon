import os
import sys
import time
import threading
import importlib

os.environ["QT_QPA_PLATFORM"] = "offscreen"
sys.path.insert(0, os.path.join(os.path.dirname(os.path.abspath(__file__)), "..", "src"))

from PySide6.QtCore import QEventLoop, QTimer
from PySide6.QtWidgets import QApplication

app = QApplication(sys.argv)
modules = ["pandas", "sympy", "scipy.optimize", "matplotlib.pyplot", "mendeleev.fetch"]
if len(sys.argv) > 1 and sys.argv[1] == "without":
    modules = modules[:-1]
times = {}
start = time.time()

def load():
    for name in modules:
        t = time.time()
        importlib.import_module(name)
        times[name] = round(time.time() - t, 2)

ticks = []
last = [time.time()]

def tick():
    now = time.time()
    ticks.append((round(now - start, 2), round(now - last[0], 2), list(sys.modules)[-1]))
    last[0] = now
    if not loader.is_alive():
        loop.quit()

loader = threading.Thread(target=load, daemon=True)
loop = QEventLoop()
timer = QTimer(interval=50)
timer.timeout.connect(tick)
loader.start()
timer.start()
loop.exec()
timer.stop()
print("per module:", times)
print("total thread phase:", round(time.time() - start, 2))
print("longest gaps between ticks:", sorted(ticks, key=lambda t: -t[1])[:5])
t = time.time()
import gui
print("import gui:", round(time.time() - t, 2))
