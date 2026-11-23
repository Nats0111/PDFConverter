from pathlib import Path

from config import (
    OCR_OUTPUT,
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

SUPPORTED_LANGUAGES = {
    "eng",
    "chi_tra",
    "ita",
}


LANGUAGE_NAMES = {
    "eng": "English",
    "chi_tra": "繁體中文",
    "ita": "Italiano",
}

SUPPORTED_OCR_MODES = {
    "skip": "跳過已有文字",
    "force": "強制重新 OCR",
    "redo": "重做文字層",
    "default": "嚴格模式",
}


# =========================================================
# Progress callback
# =========================================================


def emit(callback, message, level="INFO", progress=None):

    if callback:
        callback(message, level, progress)


# =========================================================
# Lazy OCRmyPDF import
# =========================================================


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


# =========================================================
# OCR
# =========================================================


def ocr_pdf(
    file_path,
    languages,
    rotate_pages=True,
    deskew=True,
    create_sidecar=False,
    ocr_mode="skip",
    progress_callback=None,
    cancel_event=None,
):

    source = Path(file_path)

    # =====================================================
    # Validate source
    # =====================================================

    if not source.exists():
        raise FileNotFoundError(f"找不到檔案：{source}")

    if source.suffix.lower() != ".pdf":
        raise ValueError("OCR 只接受 PDF。")

    # =====================================================
    # Validate languages & mode
    # =====================================================

    if not languages:
        raise ValueError("請至少選擇一種 OCR 語言。")

    invalid_languages = [
        language for language in languages if language not in SUPPORTED_LANGUAGES
    ]

    if invalid_languages:
        raise ValueError(("不支援的 OCR 語言：" + ", ".join(invalid_languages)))

    if ocr_mode not in SUPPORTED_OCR_MODES:
        raise ValueError(f"不支援的 OCR 模式：{ocr_mode}")

    if cancel_event and cancel_event.is_set():
        raise JobCancelled("使用者取消 OCR。")

    effective_deskew = bool(deskew)

    if ocr_mode == "redo" and effective_deskew:
        effective_deskew = False

        emit(
            progress_callback,
            "重做文字層模式不支援歪斜校正，已自動停用歪斜校正",
            "WARNING",
        )

    # =====================================================
    # Display language list
    # =====================================================

    language_display = " + ".join(
        LANGUAGE_NAMES.get(language, language) for language in languages
    )

    # =====================================================
    # Output PDF
    # =====================================================

    output_file = unique_path(OCR_OUTPUT, (source.stem + "_ocr.pdf"))

    # =====================================================
    # Sidecar
    # =====================================================

    sidecar_file = None

    if create_sidecar:
        sidecar_file = unique_path(OCR_OUTPUT, (source.stem + "_ocr.txt"))

    # =====================================================
    # Console progress
    # =====================================================

    emit(progress_callback, f"讀取 PDF：{source.name}")

    emit(progress_callback, (f"OCR 語言：{language_display}"))

    emit(progress_callback, (f"OCR 模式：{SUPPORTED_OCR_MODES[ocr_mode]} ({ocr_mode})"))

    emit(progress_callback, ("自動旋轉：" + ("ON" if rotate_pages else "OFF")))

    emit(progress_callback, ("歪斜校正：" + ("ON" if effective_deskew else "OFF")))

    if create_sidecar:
        emit(progress_callback, "OCR 文字輸出：ON")

    # =====================================================
    # Run OCR
    # =====================================================

    try:
        if cancel_event and cancel_event.is_set():
            raise JobCancelled("使用者取消 OCR。")

        emit(progress_callback, "初始化 OCRmyPDF...")

        (
            ocrmypdf,
            OcrOptions,
        ) = get_ocrmypdf()

        if cancel_event and cancel_event.is_set():
            raise JobCancelled("使用者取消 OCR。")

        emit(progress_callback, "正在建立 OCR 工作...")

        # =================================================
        # OCR Options
        # =================================================

        options_kwargs = {
            "input_file": str(source),
            "output_file": str(output_file),
            "languages": list(languages),
            "rotate_pages": bool(rotate_pages),
            "deskew": effective_deskew,
            "mode": ocr_mode,
            "tagged_pdf_mode": ("default" if ocr_mode == "default" else "ignore"),
            "output_type": "pdf",
            # GUI 已經自己處理進度，
            # 不需要 OCRmyPDF progress bar
            "progress_bar": False,
        }

        if create_sidecar and sidecar_file:
            options_kwargs["sidecar"] = str(sidecar_file)

        options = OcrOptions(**options_kwargs)

        # =================================================
        # Execute
        # =================================================

        emit(progress_callback, ("正在執行 Tesseract OCR..."))

        ocrmypdf.ocr(options)

        if cancel_event and cancel_event.is_set():
            raise JobCancelled("使用者取消 OCR。")

        # =================================================
        # Validate PDF
        # =================================================

        if not output_file.exists() or output_file.stat().st_size <= 0:
            raise RuntimeError(("OCRmyPDF 沒有產生有效 PDF。"))

        # =================================================
        # Complete
        # =================================================

        emit(progress_callback, "OCR PDF 建立完成", "SUCCESS", 100)

        emit(progress_callback, (f"PDF 輸出：{output_file.name}"), "SUCCESS")

        if create_sidecar and sidecar_file:
            if sidecar_file.exists():
                emit(progress_callback, (f"文字輸出：{sidecar_file.name}"), "SUCCESS")

            else:
                emit(progress_callback, ("未產生 OCR 文字 sidecar"), "WARNING")

        # =================================================
        # Log
        # =================================================

        log_success(
            "OCR",
            (
                f"{source.name} -> {output_file.name} | "
                f"languages={'+'.join(languages)} | mode={ocr_mode}"
            ),
        )

        return {
            "pdf": output_file,
            "sidecar": (
                sidecar_file if (sidecar_file and sidecar_file.exists()) else None
            ),
        }

    # =====================================================
    # Cancelled
    # =====================================================

    except JobCancelled:
        if output_file.exists():
            try:
                output_file.unlink()

            except OSError:
                pass

        if sidecar_file and sidecar_file.exists():
            try:
                sidecar_file.unlink()

            except OSError:
                pass

        emit(progress_callback, "OCR 已取消", "WARNING")

        log_skipped("OCR", f"{source.name} | 使用者取消")

        raise

    # =====================================================
    # Error
    # =====================================================

    except Exception as error:
        # =================================================
        # Delete incomplete output
        # =================================================

        if output_file.exists():
            try:
                output_file.unlink()

            except OSError:
                pass

        if sidecar_file and sidecar_file.exists():
            try:
                sidecar_file.unlink()

            except OSError:
                pass

        emit(progress_callback, (f"OCR 失敗：{error}"), "ERROR")

        log_failed("OCR", (f"{source.name} | {error}"))

        raise
