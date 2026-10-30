import json
import os
import subprocess
import sys
from pathlib import Path

import pytest

pytest.importorskip("PySide6")

SRC = Path(__file__).resolve().parent.parent / "src"

SCRIPT = """
import json
from PySide6.QtCore import QCoreApplication, QEvent
from PySide6.QtGui import QFileOpenEvent
import gui

app = gui.CarbonApp([])
QCoreApplication.sendEvent(app, QFileOpenEvent("early.crbn"))
pending = app.pending_file

opened = []
class FakeWindow:
    def load_regneark(self, path, view=None):
        opened.append((path, view))
app.window = FakeWindow()
QCoreApplication.sendEvent(app, QFileOpenEvent("late.crbn"))

QCoreApplication.sendEvent(app, QEvent(QEvent.User))
app.processEvents()
print(json.dumps({"pending": pending, "opened": opened}))
"""


@pytest.fixture(scope="module")
def run():
    env = {**os.environ, "QT_QPA_PLATFORM": "offscreen", "MPLBACKEND": "agg"}
    proc = subprocess.run([sys.executable, "-c", SCRIPT], cwd=SRC, env=env, capture_output=True, text=True, timeout=9)
    return proc, json.loads(proc.stdout.strip().splitlines()[-1])


def test_file_before_window_is_kept_for_later(run):
    assert run[1]["pending"] == "early.crbn"


def test_file_after_window_opens_in_new_tab(run):
    assert run[1]["opened"] == [["late.crbn", None]]


def test_other_events_reach_qapplication(run):
    proc = run[0]
    assert proc.returncode == 0
    assert "Traceback" not in proc.stderr
