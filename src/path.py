import sys
from pathlib import Path


def resource_path(relative_path: str = "") -> Path:
    """Absolute path to a bundled resource, working both from source and
    from a PyInstaller-frozen build (onefile or onedir)."""
    if getattr(sys, "frozen", False) and hasattr(sys, "_MEIPASS"):
        base_path = Path(sys._MEIPASS)
    elif getattr(sys, "frozen", False):
        base_path = Path(sys.executable).resolve().parent
    else:
        base_path = Path(__file__).resolve().parent.parent

    return base_path / relative_path
