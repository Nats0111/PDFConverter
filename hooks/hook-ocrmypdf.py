from PyInstaller.utils.hooks import (
    collect_data_files,
    collect_submodules,
    copy_metadata,
)


# =========================================================
# Data
# =========================================================

datas = (
    collect_data_files(
        "ocrmypdf"
    )
)


# =========================================================
# Metadata
# =========================================================

datas += (
    copy_metadata(
        "ocrmypdf"
    )
)


# =========================================================
# Dynamic modules / plugins
# =========================================================

hiddenimports = (
    collect_submodules(
        "ocrmypdf"
    )
)


hiddenimports += [
    "ocrmypdf.builtin_plugins",
]