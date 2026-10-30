# build.spec
#
# Run this on the target OS itself — PyInstaller does not cross-compile:
#   Windows:  pyinstaller build.spec
#   macOS:    pyinstaller build.spec
#
# Expects to be run from the project root (the folder that contains
# config.json, src/, todo.txt). Produces dist/Carbon/ (onedir) which the
# Windows installer step and the macOS dmg step both consume.

import sys
from pathlib import Path

from PyInstaller.utils.hooks import collect_all

block_cipher = None

PROJECT_ROOT = Path.cwd()
SRC = PROJECT_ROOT / "src"

# Packages that ship their own data files / do dynamic imports PyInstaller's
# static analysis won't catch on its own.
COLLECT_PACKAGES = [
    "mendeleev",   # ships a sqlite db of element data
    "matplotlib",  # backend + font/style data
    "nacl",
    "scipy",
    "sympy",
]

datas = [
    (str(PROJECT_ROOT / "Assets"), "Assets"),
    (str(PROJECT_ROOT / "config.json"), "."),
    (str(PROJECT_ROOT / "Assets_math_live"), "Assets_math_live"),
]
binaries = []
hiddenimports = [
    "PySide6.QtSvg",
    "matplotlib.backends.backend_qtagg",
]

for pkg in COLLECT_PACKAGES:
    try:
        d, b, h = collect_all(pkg)
        datas += d
        binaries += b
        hiddenimports += h
    except Exception as e:
        print(f"[build.spec] warning: could not collect {pkg}: {e}")

a = Analysis(
    [str(SRC / "gui.py")],
    pathex=[str(SRC)],
    binaries=binaries,
    datas=datas,
    hiddenimports=hiddenimports,
    hookspath=[],
    hooksconfig={},
    runtime_hooks=[],
    excludes=[],
    noarchive=False,
    cipher=block_cipher,
)

pyz = PYZ(a.pure, a.zipped_data, cipher=block_cipher)

if sys.platform == "darwin":
    icon_path = PROJECT_ROOT / "installer" / "macos" / "icon.icns"
else:
    icon_path = PROJECT_ROOT / "installer" / "windows" / "icon.ico"

icon_arg = str(icon_path) if icon_path.exists() else None

exe = EXE(
    pyz,
    a.scripts,
    [],
    exclude_binaries=True,
    name="Carbon",
    debug=False,
    strip=False,
    upx=True,
    console=False,
    icon=icon_arg,
)

coll = COLLECT(
    exe,
    a.binaries,
    a.zipfiles,
    a.datas,
    strip=False,
    upx=True,
    name="Carbon",
)

if sys.platform == "darwin":
    app = BUNDLE(
        coll,
        name="Carbon.app",
        icon=icon_arg,
        bundle_identifier="com.mb.carbon",
        info_plist={
            "NSHighResolutionCapable": "True",
            "CFBundleShortVersionString": "1.0.0",
            "CFBundleDocumentTypes": [
                {
                    "CFBundleTypeName": "Carbon regneark",
                    "CFBundleTypeRole": "Editor",
                    "LSHandlerRank": "Owner",
                    "LSItemContentTypes": ["com.mb.carbon.crbn"],
                }
            ],
            "UTExportedTypeDeclarations": [
                {
                    "UTTypeIdentifier": "com.mb.carbon.crbn",
                    "UTTypeDescription": "Carbon regneark",
                    "UTTypeConformsTo": ["public.data"],
                    "UTTypeTagSpecification": {"public.filename-extension": ["crbn"]},
                }
            ],
        },
    )
