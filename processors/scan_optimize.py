from pathlib import Path

from config import (
    SCAN_OUTPUT,
)
from logger import (
    log_failed,
    log_skipped,
    log_success,
)
from utils import (
    JobCancelled,
    get_pdf_page_count,
    unique_path,
    validate_pdf,
)

SUPPORTED_OCR_MODES = {
    "skip": "跳過已有文字",
    "force": "強制重新 OCR",
    "redo": "重做文字層",
    "default": "嚴格模式",
}


def emit(callback, message, level="INFO", progress=None):

    if callback:
        callback(message, level, progress)


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
        raise RuntimeError((f"OCRmyPDF 初始化失敗：{error}")) from error


def optimize_scanned_pdf(
    file_path,
    languages,
    rotate_pages=True,
    deskew=True,
    optimize_level=1,
    ocr_mode="skip",
    progress_callback=None,
    cancel_event=None,
):

    source = Path(file_path)

    if not (source.exists()):
        raise FileNotFoundError(f"找不到：{source}")

    if source.suffix.lower() != ".pdf":
        raise ValueError("掃描最佳化只接受 PDF。")

    if optimize_level not in (
        0,
        1,
        2,
        3,
    ):
        raise ValueError("OCR 最佳化等級必須為 0-3。")

    if ocr_mode not in SUPPORTED_OCR_MODES:
        raise ValueError(f"不支援的 OCR 模式：{ocr_mode}")

    if cancel_event and cancel_event.is_set():
        raise JobCancelled("使用者取消掃描最佳化。")

    effective_deskew = bool(deskew)

    if ocr_mode == "redo" and effective_deskew:
        effective_deskew = False

        emit(
            progress_callback,
            "重做文字層模式不支援歪斜校正，已自動停用歪斜校正",
            "WARNING",
        )

    total_pages = get_pdf_page_count(source)

    output_file = unique_path(SCAN_OUTPUT, (source.stem + "_optimized.pdf"))

    try:
        if cancel_event and cancel_event.is_set():
            raise JobCancelled("使用者取消掃描最佳化。")

        emit(progress_callback, (f"掃描文件：{source.name}"))

        emit(progress_callback, (f"頁數：{total_pages}"))

        emit(
            progress_callback,
            (f"OCR 模式：{SUPPORTED_OCR_MODES[ocr_mode]} ({ocr_mode})"),
        )

        emit(progress_callback, (f"OCR 最佳化等級：O{optimize_level}"))

        (
            ocrmypdf,
            OcrOptions,
        ) = get_ocrmypdf()

        if cancel_event and cancel_event.is_set():
            raise JobCancelled("使用者取消掃描最佳化。")

        options = OcrOptions(
            input_file=(str(source)),
            output_file=(str(output_file)),
            languages=list(languages),
            rotate_pages=bool(rotate_pages),
            deskew=effective_deskew,
            mode=ocr_mode,
            tagged_pdf_mode=("default" if ocr_mode == "default" else "ignore"),
            optimize=(optimize_level),
            output_type="pdf",
            progress_bar=False,
        )

        emit(progress_callback, ("正在執行 OCR 與掃描文件最佳化..."))

        ocrmypdf.ocr(options)

        if cancel_event and cancel_event.is_set():
            raise JobCancelled("使用者取消掃描最佳化。")

        emit(progress_callback, "正在驗證輸出 PDF...", "INFO", 95)

        validation = validate_pdf(output_file, expected_pages=(total_pages))

        if not (validation["ok"]):
            raise RuntimeError((f"輸出 PDF 驗證失敗：{validation['error']}"))

        emit(progress_callback, (f"輸出：{output_file.name}"), "SUCCESS", 100)

        log_success(
            "SCAN_OPTIMIZE",
            (
                f"{source.name} -> {output_file.name} | "
                f"O{optimize_level} | mode={ocr_mode}"
            ),
        )

        return output_file

    except JobCancelled:
        if output_file.exists():
            try:
                output_file.unlink()

            except OSError:
                pass

        emit(progress_callback, "掃描最佳化已取消", "WARNING")

        log_skipped("SCAN_OPTIMIZE", f"{source.name} | 使用者取消")

        raise

    except Exception as error:
        if output_file.exists():
            try:
                output_file.unlink()

            except OSError:
                pass

        emit(progress_callback, (f"掃描最佳化失敗：{error}"), "ERROR")

        log_failed("SCAN_OPTIMIZE", (f"{source.name} | {error}"))

        raise
