from pathlib import Path

from config import (
    SCAN_OUTPUT,
)

from utils import (
    unique_path,
    validate_pdf,
    get_pdf_page_count,
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


def get_ocrmypdf():

    try:

        import ocrmypdf

        from ocrmypdf import (
            OcrOptions,
        )

        return (
            ocrmypdf,
            OcrOptions,
        )

    except Exception as error:

        raise RuntimeError(
            (
                "OCRmyPDF 初始化失敗："
                f"{error}"
            )
        ) from error


def optimize_scanned_pdf(
    file_path,
    languages,
    rotate_pages=True,
    deskew=True,
    optimize_level=1,
    progress_callback=None,
):

    source = Path(
        file_path
    )

    if not (
        source.exists()
    ):

        raise FileNotFoundError(
            f"找不到：{source}"
        )

    if (
        source.suffix.lower()
        != ".pdf"
    ):

        raise ValueError(
            "掃描最佳化只接受 PDF。"
        )

    if (
        optimize_level
        not in (
            0,
            1,
            2,
            3,
        )
    ):

        raise ValueError(
            "OCR 最佳化等級必須為 0-3。"
        )

    total_pages = (
        get_pdf_page_count(
            source
        )
    )

    output_file = (
        unique_path(
            SCAN_OUTPUT,
            (
                source.stem
                + "_optimized.pdf"
            )
        )
    )

    try:

        emit(
            progress_callback,
            (
                f"掃描文件："
                f"{source.name}"
            )
        )

        emit(
            progress_callback,
            (
                f"頁數："
                f"{total_pages}"
            )
        )

        emit(
            progress_callback,
            (
                "OCR 最佳化等級："
                f"O{optimize_level}"
            )
        )

        (
            ocrmypdf,
            OcrOptions,
        ) = get_ocrmypdf()

        options = OcrOptions(

            input_file=(
                str(source)
            ),

            output_file=(
                str(output_file)
            ),

            languages=list(
                languages
            ),

            rotate_pages=bool(
                rotate_pages
            ),

            deskew=bool(
                deskew
            ),

            optimize=(
                optimize_level
            ),

            output_type="pdf",

            progress_bar=False,
        )

        emit(
            progress_callback,
            (
                "正在執行 OCR "
                "與掃描文件最佳化..."
            )
        )

        ocrmypdf.ocr(
            options
        )

        emit(
            progress_callback,
            "正在驗證輸出 PDF...",
            "INFO",
            95
        )

        validation = (
            validate_pdf(
                output_file,
                expected_pages=(
                    total_pages
                )
            )
        )

        if not (
            validation["ok"]
        ):

            raise RuntimeError(
                (
                    "輸出 PDF 驗證失敗："
                    f"{validation['error']}"
                )
            )

        emit(
            progress_callback,
            (
                f"輸出："
                f"{output_file.name}"
            ),
            "SUCCESS",
            100
        )

        log_success(
            "SCAN_OPTIMIZE",
            (
                f"{source.name} -> "
                f"{output_file.name} | "
                f"O{optimize_level}"
            )
        )

        return output_file

    except Exception as error:

        if (
            output_file.exists()
        ):

            try:

                output_file.unlink()

            except OSError:

                pass

        emit(
            progress_callback,
            (
                "掃描最佳化失敗："
                f"{error}"
            ),
            "ERROR"
        )

        log_failed(
            "SCAN_OPTIMIZE",
            (
                f"{source.name} | "
                f"{error}"
            )
        )

        raise