from pathlib import Path

from pypdf import (
    PdfWriter,
)

from config import (
    MERGE_OUTPUT,
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


def merge_pdfs(
    file_paths,
    output_name="merged.pdf",
    progress_callback=None,
):

    if (
        len(file_paths)
        < 2
    ):

        raise ValueError(
            "至少需要兩個 PDF。"
        )

    sources = [
        Path(file)
        for file
        in file_paths
    ]

    for source in sources:

        if not source.exists():

            raise FileNotFoundError(
                f"找不到：{source}"
            )

        if (
            source.suffix.lower()
            != ".pdf"
        ):

            raise ValueError(
                (
                    f"{source.name} "
                    "不是 PDF。"
                )
            )

    output_name = (
        output_name.strip()
    )

    if not output_name:

        output_name = (
            "merged.pdf"
        )

    if not (
        output_name.lower()
        .endswith(".pdf")
    ):

        output_name += ".pdf"

    output_file = (
        unique_path(
            MERGE_OUTPUT,
            output_name
        )
    )

    writer = PdfWriter()

    try:

        total = len(
            sources
        )

        emit(
            progress_callback,
            (
                f"準備合併 "
                f"{total} 個 PDF"
            ),
            progress=0
        )

        for index, source in (
            enumerate(
                sources,
                start=1
            )
        ):

            writer.append(
                str(source)
            )

            progress = (
                index
                / total
                * 90
            )

            emit(
                progress_callback,
                (
                    f"[{index}/{total}] "
                    f"加入 "
                    f"{source.name}"
                ),
                progress=progress
            )

        emit(
            progress_callback,
            "正在寫入合併 PDF...",
            progress=95
        )

        writer.write(
            str(output_file)
        )

        if (
            not output_file.exists()
            or
            output_file.stat().st_size
            <= 0
        ):

            raise RuntimeError(
                "沒有產生有效 PDF。"
            )

        emit(
            progress_callback,
            f"輸出：{output_file.name}",
            "SUCCESS",
            100
        )

        log_success(
            "PDF_MERGE",
            (
                f"{total} files -> "
                f"{output_file.name}"
            )
        )

        return output_file

    except Exception as error:

        if output_file.exists():

            try:

                output_file.unlink()

            except OSError:

                pass

        emit(
            progress_callback,
            f"合併失敗：{error}",
            "ERROR"
        )

        log_failed(
            "PDF_MERGE",
            str(error)
        )

        raise

    finally:

        writer.close()