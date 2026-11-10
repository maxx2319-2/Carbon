import os
import sys
import time
import types
import functools
import threading
import importlib

SRC = os.path.join(os.path.dirname(os.path.abspath(__file__)), "..", "src")
sys.path.insert(0, SRC)
LOG = os.path.join(os.path.dirname(os.path.abspath(__file__)), "startup_trace.log")


if __name__ == "__main__":
    import multiprocessing
    multiprocessing.freeze_support()
    from PySide6.QtCore import QEventLoop, QTimer, Qt
    from PySide6.QtWidgets import QApplication

    start = time.time()
    out = open(LOG, "w")

    def log(msg):
        line = f"{time.time() - start:7.2f}s  {msg}"
        print(line, flush=True)
        out.write(line + "\n")
        out.flush()

    QApplication.setAttribute(Qt.AA_ShareOpenGLContexts)
    import main
    from path import resource_path
    from PySide6.QtGui import QIcon
    app = main.CarbonApp(sys.argv[:1])
    app.setWindowIcon(QIcon(str(resource_path("Assets/Carbon_Round.svg"))))
    splash = main.Splash(app)
    splash.show()

    orig_status = main.Splash.status
    last = [None]
    def status(self, text):
        if text != last[0]:
            last[0] = text
            log("status: " + text)
        orig_status(self, text)
    main.Splash.status = status

    modules = ["pandas", "sympy", "scipy.optimize", "matplotlib.pyplot", "mendeleev.fetch"]
    done = []

    def load():
        for name in modules:
            t = time.time()
            importlib.import_module(name)
            done.append(name)
            log(f"thread imported {name} in {time.time() - t:.2f}s")
        log("thread finished")

    gap = [time.time()]
    def watchdog():
        now = time.time()
        if now - gap[0] > 0.5:
            log(f"main thread was blocked for {now - gap[0]:.2f}s")
        gap[0] = now

    dog = QTimer(interval=100)
    dog.timeout.connect(watchdog)
    dog.start()
    loader = threading.Thread(target=load, daemon=True)
    loader.start()
    while loader.is_alive():
        cap = 50 * (len(done) + 1) // len(modules) - 1
        splash.bar.setValue(max(50 * len(done) // len(modules), min(splash.bar.value() + 1, cap)))
        orig_status(splash, f"Indlæser {list(sys.modules)[-1]}")
        app.processEvents()
        loader.join(0.05)
    log("splash loop finished")
    splash.status("Indlæser Carbon")
    t = time.time()
    import gui
    log(f"import gui took {time.time() - t:.2f}s")

    def timed(name, fn):
        @functools.wraps(fn)
        def wrapper(*a, **k):
            t = time.time()
            try:
                return fn(*a, **k)
            finally:
                d = time.time() - t
                if d > 0.2:
                    log(f"{name} took {d:.2f}s")
        return wrapper

    for name, fn in list(vars(gui.MainWindow).items()):
        if isinstance(fn, types.FunctionType):
            setattr(gui.MainWindow, name, timed("MainWindow." + name, fn))
    gui.preload = timed("preload", gui.preload)
    gui.license_manager.start_check = timed("license start_check", gui.license_manager.start_check)

    orig_finish = splash.finish
    def finish(w):
        log("window shown, startup done")
        dog.stop()
        orig_finish(w)
    splash.finish = finish

    splash.progress(50)
    gui.main(app, splash)
