# -*- mode: python ; coding: utf-8 -*-

from pathlib import Path

from PyInstaller.utils.hooks import (
    collect_data_files,
    collect_submodules,
    copy_metadata,
)


# =========================================================
# Project
# =========================================================

project_dir = Path(
    SPECPATH
)


# =========================================================
# Data files
# =========================================================

datas = []


# =========================================================
# tkinterdnd2
# =========================================================

datas += collect_data_files(
    "tkinterdnd2"
)


# =========================================================
# Magika
# =========================================================

datas += collect_data_files(
    "magika"
)

datas += copy_metadata(
    "magika"
)


# =========================================================
# MarkItDown
# =========================================================

datas += collect_data_files(
    "markitdown"
)

datas += copy_metadata(
    "markitdown"
)


# =========================================================
# OCRmyPDF
# =========================================================

datas += collect_data_files(
    "ocrmypdf"
)

datas += copy_metadata(
    "ocrmypdf"
)


# =========================================================
# Hidden imports
# =========================================================

hiddenimports = []


# =========================================================
# Magika
# =========================================================

hiddenimports += (
    collect_submodules(
        "magika"
    )
)


# =========================================================
# MarkItDown
# =========================================================

hiddenimports += (
    collect_submodules(
        "markitdown"
    )
)


# =========================================================
# OCRmyPDF
# =========================================================

hiddenimports += (
    collect_submodules(
        "ocrmypdf"
    )
)


# =========================================================
# Explicit OCRmyPDF plugin package
# =========================================================

hiddenimports += [
    "ocrmypdf.builtin_plugins",
]


# =========================================================
# Icon
# =========================================================

icon_path = (
    project_dir
    / "assets"
    / "app.ico"
)

if icon_path.exists():

    icon_value = str(
        icon_path
    )

else:

    icon_value = None


# =========================================================
# Version information
# =========================================================

version_file = (
    project_dir
    / "version_info.txt"
)

if version_file.exists():

    version_value = str(
        version_file
    )

else:

    version_value = None


# =========================================================
# Analysis
# =========================================================

a = Analysis(

    [
        str(
            project_dir
            / "gui.py"
        )
    ],

    pathex=[
        str(
            project_dir
        )
    ],

    binaries=[],

    datas=datas,

    hiddenimports=hiddenimports,

    hookspath=[
        str(
            project_dir
            / "hooks"
        )
    ],

    hooksconfig={},

    runtime_hooks=[],

    excludes=[],

    noarchive=False,

    optimize=0,
)


# =========================================================
# PYZ
# =========================================================

pyz = PYZ(
    a.pure
)


# =========================================================
# EXE
# =========================================================

exe = EXE(

    pyz,

    a.scripts,

    [],

    exclude_binaries=True,

    name=(
        "LocalDocumentConverter"
    ),

    debug=False,

    bootloader_ignore_signals=False,

    strip=False,

    upx=True,

    console=False,

    disable_windowed_traceback=False,

    argv_emulation=False,

    target_arch=None,

    codesign_identity=None,

    entitlements_file=None,

    icon=icon_value,

    version=version_value,
)


# =========================================================
# COLLECT
#
# V3.5 正式使用 onedir。
# =========================================================

coll = COLLECT(

    exe,

    a.binaries,

    a.datas,

    strip=False,

    upx=True,

    upx_exclude=[],

    name=(
        "LocalDocumentConverter"
    ),
)