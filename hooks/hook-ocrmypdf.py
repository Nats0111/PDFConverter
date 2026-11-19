from PyInstaller.utils.hooks import (
    collect_data_files,
    collect_submodules,
    copy_metadata,
)


# =========================================================
# OCRmyPDF data files
# =========================================================

datas = collect_data_files(
    "ocrmypdf"
)


# =========================================================
# Package metadata
# =========================================================

datas += copy_metadata(
    "ocrmypdf"
)


# =========================================================
# OCRmyPDF submodules
#
# OCRmyPDF 使用 plugin architecture，
# PyInstaller 不一定能從靜態 import
# 自動找到所有 builtin plugins。
# =========================================================

hiddenimports = (
    collect_submodules(
        "ocrmypdf"
    )
)