import shutil
from pathlib import Path

from markitdown import MarkItDown

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


md = MarkItDown()


def convert_to_markdown(file_path):

    source = Path(file_path)

    if not source.exists():
        return

    if is_temp_file(source):
        return

    print()
    print("=" * 60)
    print(f"[Markdown] {source.name}")

    if not wait_until_ready(source):

        print("檔案尚未複製完成，跳過。")

        log_skipped(
            "MARKDOWN",
            f"{source.name} | 檔案尚未準備完成"
        )

        return

    try:

        print("MarkItDown 轉換中...")

        result = md.convert(
            str(source)
        )

        output_file = unique_path(
            MD_OUTPUT,
            source.stem + ".md"
        )

        output_file.write_text(
            result.markdown,
            encoding="utf-8"
        )

        print(
            f"完成：{output_file.name}"
        )

        # =================================================
        # 原始檔移至 MD_Processed
        # =================================================

        processed_file = unique_path(
            MD_PROCESSED,
            source.name
        )

        shutil.move(
            str(source),
            str(processed_file)
        )

        print(
            "原始檔案已移至："
            f"MD_Processed\\{processed_file.name}"
        )

        # =================================================
        # Log
        # =================================================

        log_success(
            "MARKDOWN",
            f"{source.name} -> {output_file.name}"
        )

    except Exception as error:

        print()
        print("Markdown 轉換失敗")
        print(f"檔案：{source.name}")
        print(f"錯誤：{error}")

        log_failed(
            "MARKDOWN",
            f"{source.name} | {error}"
        )
