from pathlib import Path

from pypdf import (
    PdfReader,
    PdfWriter,
)

from config import (
    SPLIT_OUTPUT,
)

from utils import (
    unique_path,
)

from logger import (
    log_success,
    log_failed,
)


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


def parse_page_selection(
    text,
    total_pages
):

    text = (
        text.strip()
    )

    if not text:

        raise ValueError(
            "請輸入頁碼。"
        )

    pages = []

    for part in (
        text.split(",")
    ):

        part = part.strip()

        if not part:

            continue

        if "-" in part:

            chunks = (
                part.split("-")
            )

            if len(chunks) != 2:

                raise ValueError(
                    (
                        "頁碼格式錯誤："
                        f"{part}"
                    )
                )

            try:

                start = int(
                    chunks[0].strip()
                )

                end = int(
                    chunks[1].strip()
                )

            except ValueError:

                raise ValueError(
                    (
                        "頁碼格式錯誤："
                        f"{part}"
                    )
                )

            if start > end:

                raise ValueError(
                    (
                        "頁碼範圍錯誤："
                        f"{part}"
                    )
                )

            pages.extend(
                range(
                    start,
                    end + 1
                )
            )

        else:

            try:

                pages.append(
                    int(part)
                )

            except ValueError:

                raise ValueError(
                    (
                        "頁碼格式錯誤："
                        f"{part}"
                    )
                )

    pages = list(
        dict.fromkeys(
            pages
        )
    )

    if not pages:

        raise ValueError(
            "沒有有效頁碼。"
        )

    for page in pages:

        if (
            page < 1
            or page > total_pages
        ):

            raise ValueError(
                (
                    f"頁碼 {page} "
                    "超出範圍。"
                )
            )

    return pages


def split_selected_pages(
    file_path,
    page_selection,
    progress_callback=None,
):

    source = Path(
        file_path
    )

    if not source.exists():

        raise FileNotFoundError(
            f"找不到：{source}"
        )

    reader = PdfReader(
        str(source)
    )

    total_pages = len(
        reader.pages
    )

    pages = (
        parse_page_selection(
            page_selection,
            total_pages
        )
    )

    output_file = (
        unique_path(
            SPLIT_OUTPUT,
            (
                source.stem
                + "_selected.pdf"
            )
        )
    )

    writer = PdfWriter()

    try:

        total_selected = (
            len(pages)
        )

        for index, page_number in (
            enumerate(
                pages,
                start=1
            )
        ):

            writer.add_page(
                reader.pages[
                    page_number - 1
                ]
            )

            progress = (
                index
                / total_selected
                * 90
            )

            emit(
                progress_callback,
                (
                    f"[{index}/"
                    f"{total_selected}] "
                    f"加入第 "
                    f"{page_number} 頁"
                ),
                progress=progress
            )

        emit(
            progress_callback,
            "正在寫入 PDF...",
            progress=95
        )

        writer.write(
            str(output_file)
        )

        emit(
            progress_callback,
            f"輸出：{output_file.name}",
            "SUCCESS",
            100
        )

        log_success(
            "PDF_SPLIT",
            (
                f"{source.name} -> "
                f"{output_file.name}"
            )
        )

        return output_file

    except Exception as error:

        emit(
            progress_callback,
            f"拆分失敗：{error}",
            "ERROR"
        )

        log_failed(
            "PDF_SPLIT",
            (
                f"{source.name} | "
                f"{error}"
            )
        )

        raise

    finally:

        writer.close()


def split_every_page(
    file_path,
    progress_callback=None,
):

    source = Path(
        file_path
    )

    if not source.exists():

        raise FileNotFoundError(
            f"找不到：{source}"
        )

    reader = PdfReader(
        str(source)
    )

    total_pages = len(
        reader.pages
    )

    output_folder = (
        SPLIT_OUTPUT
        / source.stem
    )

    if output_folder.exists():

        number = 1

        while True:

            candidate = (
                SPLIT_OUTPUT
                /
                (
                    f"{source.stem}_"
                    f"{number}"
                )
            )

            if not candidate.exists():

                output_folder = (
                    candidate
                )

                break

            number += 1

    output_folder.mkdir(
        parents=True,
        exist_ok=False
    )

    try:

        for index, page in (
            enumerate(
                reader.pages,
                start=1
            )
        ):

            writer = PdfWriter()

            try:

                writer.add_page(
                    page
                )

                output_file = (
                    output_folder
                    /
                    (
                        "page_"
                        f"{index:03d}"
                        ".pdf"
                    )
                )

                writer.write(
                    str(output_file)
                )

            finally:

                writer.close()

            progress = (
                index
                / total_pages
                * 100
            )

            emit(
                progress_callback,
                (
                    f"[{index}/"
                    f"{total_pages}] "
                    f"第 {index} 頁完成"
                ),
                progress=progress
            )

        emit(
            progress_callback,
            (
                "完成，共產生 "
                f"{total_pages} 個 PDF"
            ),
            "SUCCESS",
            100
        )

        log_success(
            "PDF_SPLIT",
            (
                f"{source.name} | "
                f"{total_pages} pages"
            )
        )

        return output_folder

    except Exception as error:

        emit(
            progress_callback,
            f"拆分失敗：{error}",
            "ERROR"
        )

        log_failed(
            "PDF_SPLIT",
            (
                f"{source.name} | "
                f"{error}"
            )
        )

        raise