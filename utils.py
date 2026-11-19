import time
from pathlib import Path


def wait_until_ready(file_path, timeout=30):
    """
    等待檔案複製完成。
    """

    file_path = Path(file_path)

    last_size = -1

    for _ in range(timeout * 2):

        try:
            current_size = file_path.stat().st_size

            if (
                current_size == last_size
                and current_size > 0
            ):
                return True

            last_size = current_size

        except OSError:
            pass

        time.sleep(0.5)

    return False


def unique_path(folder, filename):
    """
    避免覆蓋已經存在的檔案。

    example.pdf
    example_1.pdf
    example_2.pdf
    """

    folder = Path(folder)

    target = folder / filename

    if not target.exists():
        return target

    stem = target.stem
    suffix = target.suffix

    number = 1

    while True:

        candidate = (
            folder
            / f"{stem}_{number}{suffix}"
        )

        if not candidate.exists():
            return candidate

        number += 1


def format_size(size):
    """
    將 bytes 轉成容易閱讀的格式。
    """

    if size >= 1024 * 1024 * 1024:

        return (
            f"{size / 1024 / 1024 / 1024:.2f} GB"
        )

    if size >= 1024 * 1024:

        return (
            f"{size / 1024 / 1024:.2f} MB"
        )

    if size >= 1024:

        return (
            f"{size / 1024:.2f} KB"
        )

    return f"{size} bytes"


def is_temp_file(file_path):
    """
    判斷是否為 Office 暫存檔。
    """

    file_path = Path(file_path)

    return file_path.name.startswith("~$")