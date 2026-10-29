import json

import pytest

pytest.importorskip("PySide6")
import gui


ROWS = [
    ["code", r"x=\frac{1}{2}"],
    ["result", r"\Rightarrow\:\mathrm{0.5}"],
    ["code", r"Løs\left(x^2=2\right)"],
    ["error", r"\Rightarrow\:\text{Error}"],
    ["image", "data:image/png;base64,iVBORw0KGgo="],
]


class FakePage:
    def __init__(self, result=None):
        self.result = result
        self.calls = []

    def runJavaScript(self, code, callback=None):
        self.calls.append(code)
        if callback:
            callback(self.result)


class FakeView:
    def __init__(self, page):
        self._page = page

    def page(self):
        return self._page


class FakeWindow:
    load_regneark = gui.MainWindow.load_regneark

    def __init__(self, page):
        self.interpreter_view = FakeView(page)
        self.opened = False

    def open_interpreter(self):
        self.opened = True


def fake_dialog(monkeypatch, path):
    class FakeDialog:
        getSaveFileName = staticmethod(lambda *a: (str(path), ""))
        getOpenFileName = staticmethod(lambda *a: (str(path), ""))
    monkeypatch.setattr(gui, "QFileDialog", FakeDialog)


def test_save_writes_rows_as_json(tmp_path, monkeypatch):
    path = tmp_path / "ark.crbn"
    fake_dialog(monkeypatch, path)
    page = FakePage(json.dumps(ROWS))
    gui.MainWindow.save_regneark(FakeWindow(page))
    assert page.calls == ["JSON.stringify(getSheet())"]
    text = path.read_text(encoding="utf-8")
    assert json.loads(text) == {"rows": ROWS}
    assert "Løs" in text


def test_open_sends_rows_to_set_sheet(tmp_path, monkeypatch):
    path = tmp_path / "ark.crbn"
    path.write_text(json.dumps({"rows": ROWS}), encoding="utf-8")
    fake_dialog(monkeypatch, path)
    page = FakePage()
    window = FakeWindow(page)
    gui.MainWindow.open_regneark(window)
    assert window.opened
    assert len(page.calls) == 1
    call = page.calls[0]
    assert call.startswith("setSheet(") and call.endswith(")")
    assert json.loads(call[len("setSheet("):-1]) == ROWS


def test_save_then_open_round_trips(tmp_path, monkeypatch):
    path = tmp_path / "ark.crbn"
    fake_dialog(monkeypatch, path)
    gui.MainWindow.save_regneark(FakeWindow(FakePage(json.dumps(ROWS))))
    page = FakePage()
    gui.MainWindow.open_regneark(FakeWindow(page))
    assert json.loads(page.calls[0][len("setSheet("):-1]) == ROWS


@pytest.mark.parametrize("method", ["save_regneark", "open_regneark"])
def test_cancel_does_nothing(monkeypatch, method):
    fake_dialog(monkeypatch, "")
    page = FakePage()
    getattr(gui.MainWindow, method)(FakeWindow(page))
    assert page.calls == []
