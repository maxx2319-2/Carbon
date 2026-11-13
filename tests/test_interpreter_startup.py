from PySide6.QtCore import qInstallMessageHandler

from test_stress_window import gui, isolated_settings, ready, settle


def test_no_js_errors_on_startup():
    messages = []
    old = qInstallMessageHandler(lambda mode, context, message: messages.append(message))
    try:
        w = gui.MainWindow()
        w.show()
        ready(w.interpreter_view)
        settle(1500)
        w.new_interpreter_tab()
        ready(w.interpreter_view)
        settle(1500)
        loaded = w.interpreter_view.loaded
        w.ask_close = lambda title, text: True
        w.close()
        w.deleteLater()
        settle(300)
    finally:
        qInstallMessageHandler(old)
    assert loaded
    assert [m for m in messages if "Error" in m and "js" in m.lower()] == []
