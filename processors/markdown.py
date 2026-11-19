import shutil

from pathlib import Path

from config import (
    MD_OUTPUT,
    MD_PROCESSED,
)

from utils import (
    wait_until_ready,
    unique_path,
    is_temp_file,
)

from logger import (
    log_success,
    log_failed,
    log_skipped,
)


_markitdown_instance = None


def emit(
    callback,
    message,
    level="INFO",
    progress=None
):

    if callback:

        callback(
            message,
            level,
            progress
        )


# =========================================================
# Lazy MarkItDown initialization
# =========================================================

def get_markitdown():

    global _markitdown_instance

    if (
        _markitdown_instance
        is not None
    ):

        return (
            _markitdown_instance
        )

    try:

        from markitdown import (
            MarkItDown
        )

        _markitdown_instance = (
            MarkItDown()
        )

        return (
            _markitdown_instance
        )

    except Exception as error:

        raise RuntimeError(
            (
                "MarkItDown 初始化失敗："
                f"{error}"
            )
        ) from error


def convert_to_markdown(
    file_path,
    move_source=True,
    progress_callback=None,
):

    source = Path(file_path)

    if not source.exists():

        raise FileNotFoundError(
            f"找不到檔案：{source}"
        )

    if is_temp_file(
        source
    ):

        return None

    emit(
        progress_callback,
        f"讀取文件：{source.name}"
    )

    if not wait_until_ready(
        source
    ):

        log_skipped(
            "MARKDOWN",
            (
                f"{source.name} | "
                "尚未準備完成"
            )
        )

        raise RuntimeError(
            "檔案尚未複製完成。"
        )

    try:

        emit(
            progress_callback,
            "初始化 MarkItDown..."
        )

        md = get_markitdown()

        emit(
            progress_callback,
            "正在解析文件..."
        )

        result = md.convert(
            str(source)
        )

        output_file = unique_path(
            MD_OUTPUT,
            source.stem + ".md"
        )

        emit(
            progress_callback,
            "正在寫入 Markdown..."
        )

        output_file.write_text(
            result.markdown,
            encoding="utf-8"
        )

        if (
            not output_file.exists()
        ):

            raise RuntimeError(
                "沒有成功產生 Markdown。"
            )

        if move_source:

            processed_file = unique_path(
                MD_PROCESSED,
                source.name
            )

            shutil.move(
                str(source),
                str(processed_file)
            )

        emit(
            progress_callback,
            f"輸出：{output_file.name}",
            "SUCCESS",
            100
        )

        log_success(
            "MARKDOWN",
            (
                f"{source.name} -> "
                f"{output_file.name}"
            )
        )

        return output_file

    except Exception as error:

        emit(
            progress_callback,
            f"轉換失敗：{error}",
            "ERROR"
        )

        log_failed(
            "MARKDOWN",
            (
                f"{source.name} | "
                f"{error}"
            )
        )

        raise