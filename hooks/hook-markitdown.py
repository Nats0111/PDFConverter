from PyInstaller.utils.hooks import (
    collect_data_files,
    collect_submodules,
    copy_metadata,
)


datas = (
    collect_data_files(
        "markitdown"
    )
)

datas += (
    copy_metadata(
        "markitdown"
    )
)

hiddenimports = (
    collect_submodules(
        "markitdown"
    )
)