from PyInstaller.utils.hooks import (
    collect_data_files,
    collect_submodules,
    copy_metadata,
)


datas = (
    collect_data_files(
        "magika"
    )
)

datas += (
    copy_metadata(
        "magika"
    )
)

hiddenimports = (
    collect_submodules(
        "magika"
    )
)