import os
import shutil
import subprocess
import time

from pathlib import Path

from pypdf import PdfReader


# =========================================================
# Wait until file stable
# =========================================================

def wait_until_ready(
    path,
    timeout=30,
    interval=1.0,
):

    path = Path(
        path
    )

    start = (
        time.monotonic()
    )

    previous_size = None

    stable_count = 0

    while True:

        if (
            time.monotonic()
            - start
            > timeout
        ):

            return False

        try:

            current_size = (
                path.stat().st_size
            )

        except OSError:

            time.sleep(
                interval
            )

            continue

        if (
            current_size
            == previous_size
            and current_size > 0
        ):

            stable_count += 1

        else:

            stable_count = 0

        if stable_count >= 2:

            return True

        previous_size = (
            current_size
        )

        time.sleep(
            interval
        )


# =========================================================
# Unique output path
# =========================================================

def unique_path(
    folder,
    filename
):

    folder = Path(
        folder
    )

    folder.mkdir(
        parents=True,
        exist_ok=True
    )

    target = (
        folder
        / filename
    )

    if not target.exists():

        return target

    stem = (
        target.stem
    )

    suffix = (
        target.suffix
    )

    index = 1

    while True:

        candidate = (
            folder
            /
            (
                f"{stem}_"
                f"{index}"
                f"{suffix}"
            )
        )

        if not candidate.exists():

            return candidate

        index += 1


# =========================================================
# Temp file
# =========================================================

def is_temp_file(
    path
):

    name = (
        Path(path)
        .name
        .lower()
    )

    return (
        name.startswith("~$")
        or name.endswith(".tmp")
        or name.endswith(".part")
        or name.endswith(
            ".crdownload"
        )
    )


# =========================================================
# Size
# =========================================================

def format_size(
    size
):

    size = float(
        size
    )

    units = [
        "B",
        "KB",
        "MB",
        "GB",
        "TB",
    ]

    for unit in units:

        if (
            size < 1024
            or unit == "TB"
        ):

            if unit == "B":

                return (
                    f"{int(size)} B"
                )

            return (
                f"{size:.2f} {unit}"
            )

        size /= 1024


# =========================================================
# Disk space
# =========================================================

def get_disk_space(
    path
):

    path = Path(
        path
    )

    path.mkdir(
        parents=True,
        exist_ok=True
    )

    usage = (
        shutil.disk_usage(
            path
        )
    )

    return {

        "total":
            usage.total,

        "used":
            usage.used,

        "free":
            usage.free,
    }


def has_enough_disk_space(
    path,
    required_bytes
):

    usage = (
        get_disk_space(
            path
        )
    )

    return (
        usage["free"]
        >= required_bytes
    )


# =========================================================
# PDF page count
# =========================================================

def get_pdf_page_count(
    path
):

    reader = PdfReader(
        str(path)
    )

    return len(
        reader.pages
    )


# =========================================================
# PDF validation
# =========================================================

def validate_pdf(
    path,
    expected_pages=None
):

    path = Path(
        path
    )

    if not path.exists():

        return {
            "ok":
                False,

            "pages":
                None,

            "error":
                "檔案不存在",
        }

    if (
        path.stat().st_size
        <= 0
    ):

        return {
            "ok":
                False,

            "pages":
                None,

            "error":
                "檔案大小為 0",
        }

    try:

        reader = PdfReader(
            str(path)
        )

        page_count = len(
            reader.pages
        )

    except Exception as error:

        return {
            "ok":
                False,

            "pages":
                None,

            "error":
                str(error),
        }

    if (
        expected_pages is not None
        and
        page_count
        != expected_pages
    ):

        return {
            "ok":
                False,

            "pages":
                page_count,

            "error":
                (
                    "頁數不一致："
                    f"預期 {expected_pages}，"
                    f"輸出 {page_count}"
                ),
        }

    return {
        "ok":
            True,

        "pages":
            page_count,

        "error":
            None,
    }


# =========================================================
# Temp cleanup
# =========================================================

def cleanup_temp_folder(
    folder
):

    folder = Path(
        folder
    )

    if not folder.exists():

        return 0

    removed = 0

    for item in (
        folder.iterdir()
    ):

        try:

            if item.is_file():

                item.unlink()

                removed += 1

            elif item.is_dir():

                shutil.rmtree(
                    item
                )

                removed += 1

        except OSError:

            continue

    return removed


# =========================================================
# Hidden subprocess
# =========================================================

def hidden_process_options():

    creation_flags = 0

    startup_info = None

    if os.name == "nt":

        creation_flags = (
            getattr(
                subprocess,
                "CREATE_NO_WINDOW",
                0
            )
        )

        startup_info = (
            subprocess.STARTUPINFO()
        )

        startup_info.dwFlags |= (
            subprocess.STARTF_USESHOWWINDOW
        )

        startup_info.wShowWindow = (
            subprocess.SW_HIDE
        )

    return {
        "creationflags":
            creation_flags,

        "startupinfo":
            startup_info,
    }


def run_hidden_subprocess(
    command,
    timeout=None,
    check=True,
):

    options = (
        hidden_process_options()
    )

    return subprocess.run(

        command,

        check=check,

        capture_output=True,

        text=True,

        encoding="utf-8",

        errors="replace",

        timeout=timeout,

        creationflags=(
            options[
                "creationflags"
            ]
        ),

        startupinfo=(
            options[
                "startupinfo"
            ]
        ),
    )