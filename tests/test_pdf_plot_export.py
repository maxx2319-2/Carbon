import json
from types import SimpleNamespace
from unittest.mock import Mock

import pytest

from gui import _InterpreterBridge


def evaluate(*lines):
    return json.loads(_InterpreterBridge.evaluate(None, json.dumps(list(lines))))


@pytest.mark.parametrize("lines", [
    [r"\vec{v}=\left\lbrace1,2,3\right\rbrace", r"Plot\left(\vec{v}\right)"],
    [r"\vec{v}=\left\lbrace1,2\right\rbrace", r"Plot\left(\vec{v}\right)"],
    [r"BjerrumDiagram\left(4.76,9.25\right)"],
])
def test_plots_get_a_print_version(lines):
    rows = evaluate(*lines)
    images = [row for row in rows if row[0] == "image"]
    assert images, rows
    kind, screen, printed = images[0]
    assert screen.startswith("data:image/png;base64,")
    assert printed.startswith("data:image/svg+xml;base64,")


def test_done_accepts_rows_with_a_print_version():
    rows = evaluate(r"BjerrumDiagram\left(4.76\right)")
    bridge = SimpleNamespace(bjerrumExported=Mock(), finished=Mock(), leaked=Mock())
    _InterpreterBridge.done(bridge, 1, json.dumps(rows), False)
    sent = json.loads(bridge.finished.emit.call_args.args[1])
    assert any(row[0] == "image" and len(row) == 3 for row in sent)
