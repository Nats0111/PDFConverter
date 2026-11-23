import shutil
from pathlib import Path

from config import (
    MD_OUTPUT,
    MD_PROCESSED,
)
from logger import (
    log_failed,
    log_skipped,
    log_success,
)
from utils import (
    JobCancelled,
    is_temp_file,
    unique_path,
    wait_until_ready,
)

_markitdown_instance = None


def emit(callback, message, level="INFO", progress=None):

    if callback:
        callback(message, level, progress)


# =========================================================
# Lazy MarkItDown initialization
# =========================================================


def get_markitdown():

    global _markitdown_instance

    if _markitdown_instance is not None:
        return _markitdown_instance

    try:
        from markitdown import MarkItDown

        _markitdown_instance = MarkItDown()

        return _markitdown_instance

    except Exception as error:
        raise RuntimeError((f"MarkItDown 初始化失敗：{error}")) from error


def convert_to_markdown(
    file_path,
    move_source=True,
    progress_callback=None,
    cancel_event=None,
):

    source = Path(file_path)

    if not source.exists():
        raise FileNotFoundError(f"找不到檔案：{source}")

    if is_temp_file(source):
        return None

    output_file = None

    try:
        if cancel_event and cancel_event.is_set():
            raise JobCancelled("使用者取消轉換。")

        emit(progress_callback, f"讀取文件：{source.name}")

        if not wait_until_ready(source, cancel_event=cancel_event):
            log_skipped("MARKDOWN", (f"{source.name} | 尚未準備完成"))

            raise RuntimeError("檔案尚未複製完成。")

        if cancel_event and cancel_event.is_set():
            raise JobCancelled("使用者取消轉換。")

        emit(progress_callback, "初始化 MarkItDown...")

        md = get_markitdown()

        if cancel_event and cancel_event.is_set():
            raise JobCancelled("使用者取消轉換。")

        emit(progress_callback, "正在解析文件...")

        result = md.convert(str(source))

        if cancel_event and cancel_event.is_set():
            raise JobCancelled("使用者取消轉換。")

        output_file = unique_path(MD_OUTPUT, source.stem + ".md")

        emit(progress_callback, "正在寫入 Markdown...")

        output_file.write_text(result.markdown, encoding="utf-8")

        if not output_file.exists():
            raise RuntimeError("沒有成功產生 Markdown。")

        if move_source:
            processed_file = unique_path(MD_PROCESSED, source.name)

            shutil.move(str(source), str(processed_file))

        emit(progress_callback, f"輸出：{output_file.name}", "SUCCESS", 100)

        log_success("MARKDOWN", (f"{source.name} -> {output_file.name}"))

        return output_file

    except JobCancelled:
        if output_file and output_file.exists():
            try:
                output_file.unlink()

            except OSError:
                pass

        emit(progress_callback, "Markdown 轉換已取消", "WARNING")

        log_skipped("MARKDOWN", f"{source.name} | 使用者取消")

        raise

    except Exception as error:
        if output_file and output_file.exists():
            try:
                output_file.unlink()

            except OSError:
                pass

        emit(progress_callback, f"轉換失敗：{error}", "ERROR")

        log_failed("MARKDOWN", (f"{source.name} | {error}"))

        raise
