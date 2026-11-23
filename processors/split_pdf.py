import shutil
from pathlib import Path

from pypdf import (
    PdfReader,
    PdfWriter,
)

from config import (
    SPLIT_OUTPUT,
)
from logger import (
    log_failed,
    log_skipped,
    log_success,
)
from utils import (
    JobCancelled,
    unique_path,
)


def emit(callback, message, level="INFO", progress=None):

    if callback:
        callback(message, level, progress)


def parse_page_selection(text, total_pages):

    text = text.strip()

    if not text:
        raise ValueError("請輸入頁碼。")

    pages = []

    for part in text.split(","):
        part = part.strip()

        if not part:
            continue

        if "-" in part:
            chunks = part.split("-")

            if len(chunks) != 2:
                raise ValueError((f"頁碼格式錯誤：{part}"))

            try:
                start = int(chunks[0].strip())

                end = int(chunks[1].strip())

            except ValueError:
                raise ValueError((f"頁碼格式錯誤：{part}"))

            if start > end:
                raise ValueError((f"頁碼範圍錯誤：{part}"))

            pages.extend(range(start, end + 1))

        else:
            try:
                pages.append(int(part))

            except ValueError:
                raise ValueError((f"頁碼格式錯誤：{part}"))

    pages = list(dict.fromkeys(pages))

    if not pages:
        raise ValueError("沒有有效頁碼。")

    for page in pages:
        if page < 1 or page > total_pages:
            raise ValueError((f"頁碼 {page} 超出範圍。"))

    return pages


def split_selected_pages(
    file_path,
    page_selection,
    progress_callback=None,
    cancel_event=None,
):

    source = Path(file_path)

    if not source.exists():
        raise FileNotFoundError(f"找不到：{source}")

    if cancel_event and cancel_event.is_set():
        raise JobCancelled("使用者取消拆分。")

    reader = PdfReader(str(source))

    total_pages = len(reader.pages)

    pages = parse_page_selection(page_selection, total_pages)

    output_file = unique_path(SPLIT_OUTPUT, (source.stem + "_selected.pdf"))

    writer = PdfWriter()

    try:
        total_selected = len(pages)

        for index, page_number in enumerate(pages, start=1):
            if cancel_event and cancel_event.is_set():
                raise JobCancelled("使用者取消拆分。")

            writer.add_page(reader.pages[page_number - 1])

            progress = index / total_selected * 90

            emit(
                progress_callback,
                (f"[{index}/{total_selected}] 加入第 {page_number} 頁"),
                progress=progress,
            )

        if cancel_event and cancel_event.is_set():
            raise JobCancelled("使用者取消拆分。")

        emit(progress_callback, "正在寫入 PDF...", progress=95)

        writer.write(str(output_file))

        if cancel_event and cancel_event.is_set():
            raise JobCancelled("使用者取消拆分。")

        emit(progress_callback, f"輸出：{output_file.name}", "SUCCESS", 100)

        log_success("PDF_SPLIT", (f"{source.name} -> {output_file.name}"))

        return output_file

    except JobCancelled:
        if output_file.exists():
            try:
                output_file.unlink()

            except OSError:
                pass

        emit(progress_callback, "拆分已取消", "WARNING")

        log_skipped("PDF_SPLIT", f"{source.name} | 使用者取消")

        raise

    except Exception as error:
        if output_file.exists():
            try:
                output_file.unlink()

            except OSError:
                pass

        emit(progress_callback, f"拆分失敗：{error}", "ERROR")

        log_failed("PDF_SPLIT", (f"{source.name} | {error}"))

        raise

    finally:
        writer.close()


def split_every_page(
    file_path,
    progress_callback=None,
    cancel_event=None,
):

    source = Path(file_path)

    if not source.exists():
        raise FileNotFoundError(f"找不到：{source}")

    if cancel_event and cancel_event.is_set():
        raise JobCancelled("使用者取消拆分。")

    reader = PdfReader(str(source))

    total_pages = len(reader.pages)

    output_folder = SPLIT_OUTPUT / source.stem

    if output_folder.exists():
        number = 1

        while True:
            candidate = SPLIT_OUTPUT / (f"{source.stem}_{number}")

            if not candidate.exists():
                output_folder = candidate

                break

            number += 1

    output_folder.mkdir(parents=True, exist_ok=False)

    try:
        for index, page in enumerate(reader.pages, start=1):
            if cancel_event and cancel_event.is_set():
                raise JobCancelled("使用者取消拆分。")

            writer = PdfWriter()

            try:
                writer.add_page(page)

                output_file = output_folder / (f"page_{index:03d}.pdf")

                writer.write(str(output_file))

            finally:
                writer.close()

            progress = index / total_pages * 100

            emit(
                progress_callback,
                (f"[{index}/{total_pages}] 第 {index} 頁完成"),
                progress=progress,
            )

        emit(progress_callback, (f"完成，共產生 {total_pages} 個 PDF"), "SUCCESS", 100)

        log_success("PDF_SPLIT", (f"{source.name} | {total_pages} pages"))

        return output_folder

    except JobCancelled:
        shutil.rmtree(output_folder, ignore_errors=True)

        emit(progress_callback, "拆分已取消", "WARNING")

        log_skipped("PDF_SPLIT", f"{source.name} | 使用者取消")

        raise

    except Exception as error:
        shutil.rmtree(output_folder, ignore_errors=True)

        emit(progress_callback, f"拆分失敗：{error}", "ERROR")

        log_failed("PDF_SPLIT", (f"{source.name} | {error}"))

        raise
