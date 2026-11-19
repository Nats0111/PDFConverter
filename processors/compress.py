import os
import re
import shutil
import subprocess
import time
import uuid

from pathlib import Path

from config import (
    COMPRESS_OUTPUT,
    GHOSTSCRIPT,
    GHOSTSCRIPT_TIMEOUT,
    LARGE_PDF_SIZE,
    DISK_SPACE_MULTIPLIER,
    TEMP,
)

from utils import (
    wait_until_ready,
    unique_path,
    format_size,
    is_temp_file,
    get_pdf_page_count,
    validate_pdf,
    has_enough_disk_space,
    get_disk_space,
    hidden_process_options,
)

from logger import (
    log_success,
    log_failed,
    log_skipped,
)


# =========================================================
# Compression Profiles
# =========================================================

QUALITY_SETTINGS = {

    # =====================================================
    # Lossless / Conservative
    # =====================================================

    "lossless": {

        "ghostscript":
            "/default",

        "name":
            "無損最佳化",

        "dpi":
            None,

        "log_name":
            "COMPRESS_LOSSLESS",
    },

    # =====================================================
    # Strong
    # =====================================================

    "low": {

        "ghostscript":
            "/screen",

        "name":
            "強力壓縮",

        "dpi":
            96,

        "log_name":
            "COMPRESS_LOW",
    },

    # =====================================================
    # Balanced
    # =====================================================

    "medium": {

        "ghostscript":
            "/ebook",

        "name":
            "平衡壓縮",

        "dpi":
            150,

        "log_name":
            "COMPRESS_MEDIUM",
    },

    # =====================================================
    # High quality
    # =====================================================

    "high": {

        "ghostscript":
            "/printer",

        "name":
            "高品質",

        "dpi":
            300,

        "log_name":
            "COMPRESS_HIGH",
    },

    # =====================================================
    # Custom
    # =====================================================

    "custom": {

        "ghostscript":
            None,

        "name":
            "自訂 DPI",

        "dpi":
            None,

        "log_name":
            "COMPRESS_CUSTOM",
    },
}


# =========================================================
# Ghostscript page output
# =========================================================

PAGE_PATTERN = re.compile(
    r"\bPage\s+(\d+)\b",
    re.IGNORECASE
)


# =========================================================
# Event callback
# =========================================================

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


# =========================================================
# Helpers
# =========================================================

def safe_unlink(
    path
):

    if not path:

        return

    path = Path(
        path
    )

    if not path.exists():

        return

    try:

        path.unlink()

    except OSError:

        pass


# =========================================================
# Cancelled exception
# =========================================================

class CompressionCancelled(
    Exception
):

    pass


# =========================================================
# Validate DPI
# =========================================================

def validate_dpi(
    dpi
):

    try:

        dpi = int(
            dpi
        )

    except (
        TypeError,
        ValueError,
    ):

        raise ValueError(
            "DPI 必須是整數。"
        )

    if (
        dpi < 72
        or dpi > 600
    ):

        raise ValueError(
            (
                "自訂 DPI 必須介於 "
                "72 到 600。"
            )
        )

    return dpi


# =========================================================
# Standard preset
# =========================================================

def build_preset_command(
    source,
    output_file,
    preset
):

    return [

        GHOSTSCRIPT,

        "-sDEVICE=pdfwrite",

        "-dCompatibilityLevel=1.4",

        (
            "-dPDFSETTINGS="
            f"{preset}"
        ),

        "-dNOPAUSE",

        "-dBATCH",

        (
            "-sOutputFile="
            f"{output_file}"
        ),

        str(source),
    ]


# =========================================================
# Lossless / conservative
#
# 不主動進行圖片降採樣。
# =========================================================

def build_lossless_command(
    source,
    output_file,
):

    return [

        GHOSTSCRIPT,

        "-sDEVICE=pdfwrite",

        "-dCompatibilityLevel=1.4",

        "-dDetectDuplicateImages=true",

        "-dCompressFonts=true",

        "-dSubsetFonts=true",

        "-dEmbedAllFonts=true",

        "-dDownsampleColorImages=false",

        "-dDownsampleGrayImages=false",

        "-dDownsampleMonoImages=false",

        "-dNOPAUSE",

        "-dBATCH",

        (
            "-sOutputFile="
            f"{output_file}"
        ),

        str(source),
    ]


# =========================================================
# Explicit image downsample
# =========================================================

def build_downsample_command(
    source,
    output_file,
    dpi
):

    dpi = validate_dpi(
        dpi
    )

    return [

        GHOSTSCRIPT,

        "-sDEVICE=pdfwrite",

        "-dCompatibilityLevel=1.4",

        # =================================================
        # General optimization
        # =================================================

        "-dDetectDuplicateImages=true",

        "-dCompressFonts=true",

        "-dSubsetFonts=true",

        "-dEmbedAllFonts=true",

        # =================================================
        # Color
        # =================================================

        "-dDownsampleColorImages=true",

        "-dAutoFilterColorImages=true",

        "-dColorImageDownsampleType=/Bicubic",

        (
            "-dColorImageResolution="
            f"{dpi}"
        ),

        # =================================================
        # Gray
        # =================================================

        "-dDownsampleGrayImages=true",

        "-dAutoFilterGrayImages=true",

        "-dGrayImageDownsampleType=/Bicubic",

        (
            "-dGrayImageResolution="
            f"{dpi}"
        ),

        # =================================================
        # Mono
        # =================================================

        "-dDownsampleMonoImages=true",

        "-dMonoImageDownsampleType=/Bicubic",

        # 黑白文字/線條至少保留 300 DPI

        (
            "-dMonoImageResolution="
            f"{max(dpi, 300)}"
        ),

        # =================================================
        # Runtime
        # =================================================

        "-dNOPAUSE",

        "-dBATCH",

        (
            "-sOutputFile="
            f"{output_file}"
        ),

        str(source),
    ]


# =========================================================
# Kill process
# =========================================================

def terminate_process(
    process
):

    if not process:

        return

    if (
        process.poll()
        is not None
    ):

        return

    try:

        process.terminate()

        process.wait(
            timeout=3
        )

        return

    except Exception:

        pass

    try:

        process.kill()

    except Exception:

        pass


# =========================================================
# Ghostscript live runner
# =========================================================

def run_ghostscript(
    command,
    output_file,
    total_pages,
    progress_callback=None,
    cancel_event=None,
):

    safe_unlink(
        output_file
    )

    process_options = (
        hidden_process_options()
    )

    process = None

    recent_lines = []

    last_page = 0

    last_percent = -1

    start_time = (
        time.monotonic()
    )

    try:

        process = (
            subprocess.Popen(

                command,

                stdout=(
                    subprocess.PIPE
                ),

                stderr=(
                    subprocess.STDOUT
                ),

                text=True,

                encoding="utf-8",

                errors="replace",

                bufsize=1,

                creationflags=(
                    process_options[
                        "creationflags"
                    ]
                ),

                startupinfo=(
                    process_options[
                        "startupinfo"
                    ]
                ),
            )
        )

        if process.stdout is None:

            raise RuntimeError(
                (
                    "無法取得 Ghostscript "
                    "輸出。"
                )
            )

        # =================================================
        # Read Ghostscript output
        # =================================================

        for raw_line in (
            process.stdout
        ):

            # =============================================
            # User cancellation
            # =============================================

            if (
                cancel_event
                and
                cancel_event.is_set()
            ):

                terminate_process(
                    process
                )

                safe_unlink(
                    output_file
                )

                raise CompressionCancelled(
                    "使用者取消壓縮。"
                )

            # =============================================
            # Timeout
            # =============================================

            elapsed = (
                time.monotonic()
                - start_time
            )

            if (
                GHOSTSCRIPT_TIMEOUT
                and
                elapsed
                > GHOSTSCRIPT_TIMEOUT
            ):

                terminate_process(
                    process
                )

                safe_unlink(
                    output_file
                )

                raise subprocess.TimeoutExpired(
                    command,
                    GHOSTSCRIPT_TIMEOUT
                )

            line = (
                raw_line.strip()
            )

            if not line:

                continue

            # =============================================
            # Keep only recent diagnostic lines
            # =============================================

            recent_lines.append(
                line
            )

            if (
                len(recent_lines)
                > 100
            ):

                recent_lines.pop(
                    0
                )

            # =============================================
            # Page progress
            # =============================================

            matches = (
                PAGE_PATTERN.findall(
                    line
                )
            )

            if not matches:

                continue

            try:

                current_page = max(
                    int(value)
                    for value
                    in matches
                )

            except ValueError:

                continue

            if (
                current_page
                < last_page
            ):

                continue

            last_page = (
                current_page
            )

            if (
                total_pages
                and
                total_pages > 0
            ):

                current_page = min(
                    current_page,
                    total_pages
                )

                progress = (
                    current_page
                    / total_pages
                    * 94.0
                )

                current_percent = int(
                    progress
                )

                if (
                    current_percent
                    != last_percent
                ):

                    last_percent = (
                        current_percent
                    )

                    emit(
                        progress_callback,
                        (
                            f"第 {current_page} "
                            f"/ {total_pages} 頁"
                        ),
                        "INFO",
                        progress
                    )

            else:

                emit(
                    progress_callback,
                    (
                        f"正在處理第 "
                        f"{current_page} 頁"
                    ),
                    "INFO",
                    None
                )

        return_code = (
            process.wait()
        )

        if (
            cancel_event
            and
            cancel_event.is_set()
        ):

            safe_unlink(
                output_file
            )

            raise CompressionCancelled(
                "使用者取消壓縮。"
            )

        if return_code != 0:

            raise RuntimeError(
                (
                    "Ghostscript "
                    f"離開碼 {return_code}"
                )
            )

        if not (
            Path(output_file)
            .exists()
        ):

            raise RuntimeError(
                (
                    "Ghostscript "
                    "沒有產生輸出 PDF。"
                )
            )

        emit(
            progress_callback,
            (
                "Ghostscript "
                "頁面處理完成"
            ),
            "INFO",
            94
        )

        return {

            "ok":
                True,

            "diagnostic":
                "\n".join(
                    recent_lines
                ),
        }

    except CompressionCancelled:

        terminate_process(
            process
        )

        safe_unlink(
            output_file
        )

        raise

    except subprocess.TimeoutExpired:

        terminate_process(
            process
        )

        safe_unlink(
            output_file
        )

        return {

            "ok":
                False,

            "error":
                (
                    "Ghostscript "
                    "執行時間超過限制。"
                ),

            "diagnostic":
                "\n".join(
                    recent_lines
                ),
        }

    except Exception as error:

        terminate_process(
            process
        )

        safe_unlink(
            output_file
        )

        return {

            "ok":
                False,

            "error":
                str(error),

            "diagnostic":
                "\n".join(
                    recent_lines
                ),
        }

    finally:

        if (
            process
            and process.stdout
        ):

            try:

                process.stdout.close()

            except Exception:

                pass


# =========================================================
# Short error
# =========================================================

def short_error(
    result
):

    if result.get(
        "error"
    ):

        return str(
            result[
                "error"
            ]
        )

    diagnostic = (
        result.get(
            "diagnostic",
            ""
        )
        .strip()
    )

    if not diagnostic:

        return (
            "Ghostscript "
            "沒有提供錯誤資訊。"
        )

    lines = [

        line

        for line
        in diagnostic.splitlines()

        if line.strip()
    ]

    return "\n".join(
        lines[-3:]
    )


# =========================================================
# Disk preflight
# =========================================================

def check_disk_preflight(
    source_size,
    progress_callback=None,
):

    required = int(
        source_size
        * DISK_SPACE_MULTIPLIER
    )

    disk = (
        get_disk_space(
            TEMP
        )
    )

    emit(
        progress_callback,
        (
            "Temp 可用空間："
            f"{format_size(disk['free'])}"
        )
    )

    emit(
        progress_callback,
        (
            "建議工作空間："
            f"{format_size(required)}"
        )
    )

    if not (
        has_enough_disk_space(
            TEMP,
            required
        )
    ):

        raise RuntimeError(
            (
                "磁碟空間不足。\n"
                "可用："
                f"{format_size(disk['free'])}\n"
                "建議至少："
                f"{format_size(required)}"
            )
        )


# =========================================================
# Main compression
# =========================================================

def compress_pdf(
    file_path,
    quality="medium",
    custom_dpi=200,
    delete_source=True,
    progress_callback=None,
    cancel_event=None,
):

    source = Path(
        file_path
    )

    # =====================================================
    # Validate input
    # =====================================================

    if not (
        source.exists()
    ):

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
            (
                "未知壓縮模式："
                f"{quality}"
            )
        )

    setting = (
        QUALITY_SETTINGS[
            quality
        ]
    )

    if (
        quality
        == "custom"
    ):

        effective_dpi = (
            validate_dpi(
                custom_dpi
            )
        )

    else:

        effective_dpi = (
            setting[
                "dpi"
            ]
        )

    log_name = (
        setting[
            "log_name"
        ]
    )

    # =====================================================
    # Initial cancel
    # =====================================================

    if (
        cancel_event
        and
        cancel_event.is_set()
    ):

        raise CompressionCancelled(
            "使用者取消壓縮。"
        )

    # =====================================================
    # Wait for stable file
    # =====================================================

    emit(
        progress_callback,
        (
            "讀取 PDF："
            f"{source.name}"
        ),
        "INFO",
        0
    )

    if not (
        wait_until_ready(
            source,
            timeout=60
        )
    ):

        log_skipped(
            log_name,
            (
                f"{source.name} | "
                "檔案尚未準備完成"
            )
        )

        raise RuntimeError(
            "PDF 尚未準備完成。"
        )

    # =====================================================
    # Source information
    # =====================================================

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
        "正在分析 PDF...",
        "INFO",
        0
    )

    try:

        total_pages = (
            get_pdf_page_count(
                source
            )
        )

    except Exception as error:

        raise RuntimeError(
            (
                "無法讀取 PDF："
                f"{error}"
            )
        ) from error

    if total_pages <= 0:

        raise RuntimeError(
            "PDF 沒有有效頁面。"
        )

    emit(
        progress_callback,
        (
            f"PDF："
            f"{total_pages} 頁 / "
            f"{original_text}"
        ),
        "INFO",
        0
    )

    # =====================================================
    # Disk check
    # =====================================================

    check_disk_preflight(
        original_size,
        progress_callback
    )

    # =====================================================
    # Large mode
    # =====================================================

    is_large_pdf = (
        original_size
        >= LARGE_PDF_SIZE
    )

    if is_large_pdf:

        emit(
            progress_callback,
            "大型 PDF 模式",
            "WARNING",
            0
        )

    # =====================================================
    # Temp / final
    # =====================================================

    temp_output = (
        TEMP
        /
        (
            "compress_"
            + uuid.uuid4().hex
            + ".pdf"
        )
    )

    final_output = (
        unique_path(
            COMPRESS_OUTPUT,
            (
                source.stem
                + "_compressed.pdf"
            )
        )
    )

    used_strategy = None

    # =====================================================
    # Compression
    # =====================================================

    try:

        # =================================================
        # Lossless
        # =================================================

        if (
            quality
            == "lossless"
        ):

            emit(
                progress_callback,
                "無損最佳化模式",
                "INFO",
                0
            )

            command = (
                build_lossless_command(
                    source,
                    temp_output,
                )
            )

            used_strategy = (
                "無損最佳化"
            )

        # =================================================
        # Large PDF
        # =================================================

        elif is_large_pdf:

            emit(
                progress_callback,
                (
                    "跳過一般 preset，"
                    f"直接使用 {effective_dpi} DPI"
                ),
                "INFO",
                0
            )

            command = (
                build_downsample_command(
                    source,
                    temp_output,
                    effective_dpi,
                )
            )

            used_strategy = (
                (
                    "大型 PDF / "
                    f"{effective_dpi} DPI"
                )
            )

        # =================================================
        # Custom
        # =================================================

        elif (
            quality
            == "custom"
        ):

            emit(
                progress_callback,
                (
                    "自訂壓縮："
                    f"{effective_dpi} DPI"
                ),
                "INFO",
                0
            )

            command = (
                build_downsample_command(
                    source,
                    temp_output,
                    effective_dpi,
                )
            )

            used_strategy = (
                (
                    "自訂 / "
                    f"{effective_dpi} DPI"
                )
            )

        # =================================================
        # Standard
        # =================================================

        else:

            emit(
                progress_callback,
                (
                    "Ghostscript "
                    f"{setting['ghostscript']}"
                ),
                "INFO",
                0
            )

            command = (
                build_preset_command(
                    source,
                    temp_output,
                    setting[
                        "ghostscript"
                    ],
                )
            )

            used_strategy = (
                (
                    "標準 / "
                    f"{setting['ghostscript']}"
                )
            )

        # =================================================
        # Run
        # =================================================

        result = (
            run_ghostscript(
                command,
                temp_output,
                total_pages,
                progress_callback=(
                    progress_callback
                ),
                cancel_event=(
                    cancel_event
                ),
            )
        )

        # =================================================
        # Fallback for regular preset only
        # =================================================

        if (
            not result[
                "ok"
            ]
            and
            quality
            in (
                "low",
                "medium",
                "high",
            )
            and
            not is_large_pdf
        ):

            emit(
                progress_callback,
                (
                    "標準模式失敗，"
                    "改用圖片降採樣"
                ),
                "WARNING",
                0
            )

            safe_unlink(
                temp_output
            )

            command = (
                build_downsample_command(
                    source,
                    temp_output,
                    effective_dpi,
                )
            )

            result = (
                run_ghostscript(
                    command,
                    temp_output,
                    total_pages,
                    progress_callback=(
                        progress_callback
                    ),
                    cancel_event=(
                        cancel_event
                    ),
                )
            )

            used_strategy = (
                (
                    "Fallback / "
                    f"{effective_dpi} DPI"
                )
            )

        if not result[
            "ok"
        ]:

            raise RuntimeError(
                short_error(
                    result
                )
            )

        # =================================================
        # Cancellation
        # =================================================

        if (
            cancel_event
            and
            cancel_event.is_set()
        ):

            safe_unlink(
                temp_output
            )

            raise CompressionCancelled(
                "使用者取消壓縮。"
            )

        # =================================================
        # Validate PDF
        # =================================================

        emit(
            progress_callback,
            "正在驗證 PDF...",
            "INFO",
            95
        )

        validation = (
            validate_pdf(
                temp_output,
                expected_pages=(
                    total_pages
                )
            )
        )

        if not (
            validation[
                "ok"
            ]
        ):

            raise RuntimeError(
                (
                    "輸出 PDF 驗證失敗："
                    f"{validation['error']}"
                )
            )

        # =================================================
        # Size comparison
        # =================================================

        emit(
            progress_callback,
            "正在比較檔案大小...",
            "INFO",
            97
        )

        output_size = (
            temp_output
            .stat()
            .st_size
        )

        output_text = (
            format_size(
                output_size
            )
        )

        # =================================================
        # Smaller result
        # =================================================

        if (
            output_size
            < original_size
        ):

            reduction = (
                (
                    1
                    - output_size
                    / original_size
                )
                * 100
            )

            emit(
                progress_callback,
                "正在建立正式輸出...",
                "INFO",
                98
            )

            shutil.move(
                str(temp_output),
                str(final_output)
            )

            if delete_source:

                source.unlink()

            emit(
                progress_callback,
                (
                    f"{original_text} → "
                    f"{output_text}"
                ),
                "SUCCESS"
            )

            emit(
                progress_callback,
                (
                    f"減少 "
                    f"{reduction:.1f}%"
                ),
                "SUCCESS",
                100
            )

            log_success(
                log_name,
                (
                    f"{source.name} -> "
                    f"{final_output.name} | "
                    f"{original_text} -> "
                    f"{output_text} | "
                    f"-{reduction:.1f}% | "
                    f"{used_strategy}"
                )
            )

            return {

                "output":
                    final_output,

                "compressed":
                    True,

                "cancelled":
                    False,

                "large_pdf":
                    is_large_pdf,

                "original_size":
                    original_size,

                "output_size":
                    output_size,

                "reduction":
                    reduction,

                "strategy":
                    used_strategy,

                "dpi":
                    effective_dpi,

                "pages":
                    total_pages,
            }

        # =================================================
        # Not smaller
        # =================================================

        safe_unlink(
            temp_output
        )

        emit(
            progress_callback,
            (
                "輸出沒有比原始 PDF 小，"
                "已捨棄結果"
            ),
            "WARNING",
            100
        )

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

            preserved_output = (
                original_output
            )

        else:

            preserved_output = None

        return {

            "output":
                preserved_output,

            "compressed":
                False,

            "cancelled":
                False,

            "large_pdf":
                is_large_pdf,

            "original_size":
                original_size,

            "output_size":
                original_size,

            "reduction":
                0,

            "strategy":
                used_strategy,

            "dpi":
                effective_dpi,

            "pages":
                total_pages,
        }

    # =====================================================
    # Cancellation
    # =====================================================

    except CompressionCancelled:

        safe_unlink(
            temp_output
        )

        emit(
            progress_callback,
            "壓縮已取消",
            "WARNING"
        )

        log_skipped(
            log_name,
            (
                f"{source.name} | "
                "使用者取消"
            )
        )

        return {

            "output":
                None,

            "compressed":
                False,

            "cancelled":
                True,

            "large_pdf":
                is_large_pdf,

            "original_size":
                original_size,

            "output_size":
                None,

            "reduction":
                None,

            "strategy":
                used_strategy,

            "dpi":
                effective_dpi,

            "pages":
                total_pages,
        }

    # =====================================================
    # Failure
    # =====================================================

    except Exception as error:

        safe_unlink(
            temp_output
        )

        emit(
            progress_callback,
            (
                "壓縮失敗："
                f"{error}"
            ),
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