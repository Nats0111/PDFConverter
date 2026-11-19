import shutil
import subprocess

from pathlib import Path

from config import (
    COMPRESS_OUTPUT,
    GHOSTSCRIPT,
)

from utils import (
    wait_until_ready,
    unique_path,
    format_size,
    is_temp_file,
)

from logger import (
    log_success,
    log_failed,
    log_skipped,
)


QUALITY_SETTINGS = {

    "low": {
        "ghostscript":
            "/screen",

        "name":
            "強力壓縮",

        "log_name":
            "COMPRESS_LOW",
    },

    "medium": {
        "ghostscript":
            "/ebook",

        "name":
            "平衡壓縮",

        "log_name":
            "COMPRESS_MEDIUM",
    },

    "high": {
        "ghostscript":
            "/printer",

        "name":
            "高品質",

        "log_name":
            "COMPRESS_HIGH",
    },
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


def compress_pdf(
    file_path,
    quality="medium",
    delete_source=True,
    progress_callback=None,
):

    source = Path(
        file_path
    )

    if not source.exists():

        raise FileNotFoundError(
            f"找不到檔案：{source}"
        )

    if is_temp_file(
        source
    ):

        return None

    if (
        source.suffix.lower()
        != ".pdf"
    ):

        raise ValueError(
            "PDF 壓縮只接受 PDF。"
        )

    if (
        quality
        not in QUALITY_SETTINGS
    ):

        raise ValueError(
            f"未知壓縮品質：{quality}"
        )

    setting = (
        QUALITY_SETTINGS[
            quality
        ]
    )

    log_name = (
        setting[
            "log_name"
        ]
    )

    emit(
        progress_callback,
        f"讀取 PDF：{source.name}"
    )

    emit(
        progress_callback,
        (
            "壓縮模式："
            f"{setting['name']}"
        )
    )

    if not wait_until_ready(
        source
    ):

        log_skipped(
            log_name,
            (
                f"{source.name} | "
                "尚未準備完成"
            )
        )

        raise RuntimeError(
            "PDF 尚未準備完成。"
        )

    output_file = None

    try:

        original_size = (
            source.stat().st_size
        )

        original_text = (
            format_size(
                original_size
            )
        )

        emit(
            progress_callback,
            (
                "原始大小："
                f"{original_text}"
            )
        )

        output_file = unique_path(
            COMPRESS_OUTPUT,
            (
                source.stem
                + "_compressed.pdf"
            )
        )

        command = [

            GHOSTSCRIPT,

            "-sDEVICE=pdfwrite",

            "-dCompatibilityLevel=1.4",

            (
                "-dPDFSETTINGS="
                f"{setting['ghostscript']}"
            ),

            "-dNOPAUSE",
            "-dQUIET",
            "-dBATCH",

            (
                f"-sOutputFile="
                f"{output_file}"
            ),

            str(source),
        ]

        emit(
            progress_callback,
            "Ghostscript 壓縮中..."
        )

        subprocess.run(
            command,
            check=True
        )

        if (
            not output_file.exists()
            or
            output_file.stat().st_size
            <= 0
        ):

            raise RuntimeError(
                "Ghostscript 沒有產生有效 PDF。"
            )

        compressed_size = (
            output_file.stat().st_size
        )

        compressed_text = (
            format_size(
                compressed_size
            )
        )

        emit(
            progress_callback,
            (
                "壓縮結果："
                f"{compressed_text}"
            )
        )

        # =================================================
        # Compression successful
        # =================================================

        if (
            compressed_size
            < original_size
        ):

            reduction = (
                (
                    1
                    - compressed_size
                    / original_size
                )
                * 100
            )

            emit(
                progress_callback,
                (
                    f"成功減少 "
                    f"{reduction:.1f}%"
                ),
                "SUCCESS",
                100
            )

            if delete_source:

                source.unlink()

            log_success(
                log_name,
                (
                    f"{source.name} -> "
                    f"{output_file.name} | "
                    f"{original_text} -> "
                    f"{compressed_text} | "
                    f"-{reduction:.1f}%"
                )
            )

            return {
                "output":
                    output_file,

                "compressed":
                    True,

                "original_size":
                    original_size,

                "output_size":
                    compressed_size,

                "reduction":
                    reduction,
            }

        # =================================================
        # Compression not worthwhile
        # =================================================

        emit(
            progress_callback,
            "壓縮後沒有變小",
            "WARNING",
            100
        )

        output_file.unlink()

        if delete_source:

            original_output = (
                unique_path(
                    COMPRESS_OUTPUT,
                    source.name
                )
            )

            shutil.move(
                str(source),
                str(original_output)
            )

            output = (
                original_output
            )

        else:

            output = None

        log_success(
            log_name,
            (
                f"{source.name} | "
                "無需壓縮"
            )
        )

        return {
            "output":
                output,

            "compressed":
                False,

            "original_size":
                original_size,

            "output_size":
                original_size,

            "reduction":
                0,
        }

    except Exception as error:

        if (
            output_file
            and output_file.exists()
        ):

            try:

                output_file.unlink()

            except OSError:

                pass

        emit(
            progress_callback,
            f"壓縮失敗：{error}",
            "ERROR"
        )

        log_failed(
            log_name,
            (
                f"{source.name} | "
                f"{error}"
            )
        )

        raise