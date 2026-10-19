import re
import sys
from pathlib import Path

import pytest
import path

SRC = Path(path.__file__).resolve().parent
ROOT = SRC.parent
BUILD_SPEC = (ROOT / "build.spec").read_text(encoding="utf-8")


def test_resource_path_from_source():
    assert path.resource_path("config.json") == ROOT / "config.json"


def test_resource_path_in_onefile_build(monkeypatch, tmp_path):
    monkeypatch.setattr(sys, "frozen", True, raising=False)
    monkeypatch.setattr(sys, "_MEIPASS", str(tmp_path), raising=False)
    assert path.resource_path("units.csv") == tmp_path / "units.csv"


def test_resource_path_in_onedir_build(monkeypatch, tmp_path):
    monkeypatch.setattr(sys, "frozen", True, raising=False)
    monkeypatch.delattr(sys, "_MEIPASS", raising=False)
    monkeypatch.setattr(sys, "executable", str(tmp_path / "FihsihCalc"))
    assert path.resource_path("units.csv") == tmp_path.resolve() / "units.csv"


def resources_used_in_code():
    # the first folder or file name of every resource_path("...") call in src/
    used = set()
    for file in SRC.glob("*.py"):
        for name in re.findall(r'resource_path\("(?:\./)?([^"/]+)', file.read_text(encoding="utf-8")):
            used.add(name)
    return sorted(used)


@pytest.mark.parametrize("name", resources_used_in_code())
def test_resource_exists(name):
    assert (ROOT / name).exists()


@pytest.mark.parametrize("name", resources_used_in_code())
def test_build_bundles_resource(name):
    assert f'"{name}"' in BUILD_SPEC
