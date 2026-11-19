import shutil
import subprocess
import sys

from pathlib import Path

from config import (
    OCR_OUTPUT,
)

from utils import (
    unique_path,
)

from logger import (
    log_success,
    log_failed,
)


SUPPORTED_LANGUAGES = {
    "eng",
    "chi_tra",
    "ita",
}


LANGUAGE_NAMES = {
    "eng":
        "English",

    "chi_tra":
        "繁體中文",

    "ita":
        "Italiano",
}


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


def get_ocrmypdf_command():

    python_dir = Path(
        sys.executable
    ).parent

    possible_exe = (
        python_dir
        / "ocrmypdf.exe"
    )

    if possible_exe.exists():

        return [
            str(possible_exe)
        ]

    command = shutil.which(
        "ocrmypdf"
    )

    if command:

        return [
            command
        ]

    # Development mode fallback
    # In a frozen EXE this fallback is
    # normally not expected to work.

    if not getattr(
        sys,
        "frozen",
        False
    ):

        return [
            sys.executable,
            "-m",
            "ocrmypdf",
        ]

    raise RuntimeError(
        (
            "找不到 OCRmyPDF 執行程式。"
            "請確認 OCRmyPDF 已正確配置。"
        )
    )


def ocr_pdf(
    file_path,
    languages,
    rotate_pages=True,
    deskew=True,
    create_sidecar=False,
    progress_callback=None,
):

    source = Path(
        file_path
    )

    if not source.exists():

        raise FileNotFoundError(
            f"找不到：{source}"
        )

    if (
        source.suffix.lower()
        != ".pdf"
    ):

        raise ValueError(
            "OCR 只接受 PDF。"
        )

    if not languages:

        raise ValueError(
            "請至少選擇一種 OCR 語言。"
        )

    invalid_languages = [

        language

        for language
        in languages

        if language
        not in SUPPORTED_LANGUAGES
    ]

    if invalid_languages:

        raise ValueError(
            (
                "不支援的 OCR 語言："
                + ", ".join(
                    invalid_languages
                )
            )
        )

    language_string = (
        "+".join(
            languages
        )
    )

    language_display = (
        " + ".join(
            LANGUAGE_NAMES.get(
                language,
                language
            )

            for language
            in languages
        )
    )

    output_file = (
        unique_path(
            OCR_OUTPUT,
            (
                source.stem
                + "_ocr.pdf"
            )
        )
    )

    sidecar_file = None

    if create_sidecar:

        sidecar_file = (
            unique_path(
                OCR_OUTPUT,
                (
                    source.stem
                    + "_ocr.txt"
                )
            )
        )

    emit(
        progress_callback,
        f"讀取 PDF：{source.name}"
    )

    emit(
        progress_callback,
        (
            "OCR 語言："
            f"{language_display}"
        )
    )

    command = (
        get_ocrmypdf_command()
    )

    command += [

        "--output-type",
        "pdf",

        "-l",
        language_string,
    ]

    if rotate_pages:

        command.append(
            "--rotate-pages"
        )

    if deskew:

        command.append(
            "--deskew"
        )

    if (
        create_sidecar
        and sidecar_file
    ):

        command += [
            "--sidecar",
            str(sidecar_file),
        ]

        emit(
            progress_callback,
            "已啟用 OCR 文字 sidecar"
        )

    command += [
        str(source),
        str(output_file),
    ]

    try:

        emit(
            progress_callback,
            "正在執行 OCRmyPDF..."
        )

        subprocess.run(
            command,
            check=True,
            capture_output=True,
            text=True,
            encoding="utf-8",
            errors="replace",
        )

        if (
            not output_file.exists()
            or
            output_file.stat().st_size
            <= 0
        ):

            raise RuntimeError(
                "OCRmyPDF 沒有產生有效 PDF。"
            )

        emit(
            progress_callback,
            "OCR PDF 建立完成",
            "SUCCESS",
            100
        )

        if (
            create_sidecar
            and sidecar_file
            and sidecar_file.exists()
        ):

            emit(
                progress_callback,
                (
                    "OCR 文字："
                    f"{sidecar_file.name}"
                ),
                "SUCCESS"
            )

        log_success(
            "OCR",
            (
                f"{source.name} -> "
                f"{output_file.name}"
            )
        )

        return {
            "pdf":
                output_file,

            "sidecar":
                (
                    sidecar_file
                    if (
                        sidecar_file
                        and
                        sidecar_file.exists()
                    )
                    else None
                ),
        }

    except subprocess.CalledProcessError as error:

        if output_file.exists():

            try:

                output_file.unlink()

            except OSError:

                pass

        if (
            sidecar_file
            and sidecar_file.exists()
        ):

            try:

                sidecar_file.unlink()

            except OSError:

                pass

        stderr = (
            error.stderr.strip()
            if error.stderr
            else str(error)
        )

        emit(
            progress_callback,
            f"OCR 失敗：{stderr}",
            "ERROR"
        )

        log_failed(
            "OCR",
            (
                f"{source.name} | "
                f"{stderr}"
            )
        )

        raise RuntimeError(
            (
                "OCRmyPDF 執行失敗：\n"
                f"{stderr}"
            )
        )