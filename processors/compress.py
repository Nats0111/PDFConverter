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
        "ghostscript": "/screen",
        "name": "強力壓縮",
        "log_name": "COMPRESS_LOW",
    },

    "medium": {
        "ghostscript": "/ebook",
        "name": "平衡壓縮",
        "log_name": "COMPRESS_MEDIUM",
    },

    "high": {
        "ghostscript": "/printer",
        "name": "高品質",
        "log_name": "COMPRESS_HIGH",
    },
}


def compress_pdf(
    file_path,
    quality="medium"
):

    source = Path(file_path)

    if not source.exists():
        return

    if is_temp_file(source):
        return

    # =====================================================
    # 檢查 PDF
    # =====================================================

    if source.suffix.lower() != ".pdf":

        print()
        print(
            "[PDF 壓縮] 跳過非 PDF："
            f"{source.name}"
        )

        log_skipped(
            "COMPRESS",
            f"{source.name} | 非 PDF"
        )

        return

    # =====================================================
    # 檢查品質
    # =====================================================

    if quality not in QUALITY_SETTINGS:

        print(
            f"未知壓縮品質：{quality}"
        )

        log_failed(
            "COMPRESS",
            f"{source.name} | 未知品質：{quality}"
        )

        return

    setting = QUALITY_SETTINGS[quality]

    log_name = setting["log_name"]

    print()
    print("=" * 60)

    print(
        f"[PDF 壓縮 / {setting['name']}] "
        f"{source.name}"
    )

    if not wait_until_ready(source):

        print(
            "檔案尚未複製完成，跳過。"
        )

        log_skipped(
            log_name,
            f"{source.name} | 檔案尚未準備完成"
        )

        return

    output_file = None

    try:

        original_size = (
            source.stat().st_size
        )

        output_file = unique_path(
            COMPRESS_OUTPUT,
            source.stem + "_compressed.pdf"
        )

        print("Ghostscript 處理中...")

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

            f"-sOutputFile={output_file}",

            str(source),
        ]

        subprocess.run(
            command,
            check=True
        )

        # =================================================
        # 驗證輸出
        # =================================================

        if not output_file.exists():

            raise RuntimeError(
                "Ghostscript 沒有產生輸出 PDF"
            )

        compressed_size = (
            output_file.stat().st_size
        )

        if compressed_size <= 0:

            raise RuntimeError(
                "輸出的 PDF 大小為 0 bytes"
            )

        # =================================================
        # 計算結果
        # =================================================

        if original_size > 0:

            reduction = (
                1
                - compressed_size
                / original_size
            ) * 100

        else:

            reduction = 0

        original_text = format_size(
            original_size
        )

        compressed_text = format_size(
            compressed_size
        )

        print()
        print("壓縮完成")

        print(
            f"原始：{original_text}"
        )

        print(
            f"壓縮：{compressed_text}"
        )

        if reduction > 0:

            print(
                f"減少：{reduction:.1f}%"
            )

        elif reduction < 0:

            print(
                "檔案反而增加："
                f"{abs(reduction):.1f}%"
            )

        else:

            print(
                "檔案大小沒有變化。"
            )

        print(
            f"輸出：{output_file.name}"
        )

        # =================================================
        # 寫入 Log
        # =================================================

        log_success(
            log_name,
            (
                f"{source.name} -> "
                f"{output_file.name} | "
                f"{original_text} -> "
                f"{compressed_text} | "
                f"{reduction:.1f}%"
            )
        )

        # =================================================
        # 成功才刪原始 PDF
        # =================================================

        source.unlink()

        print(
            "原始 PDF 已刪除："
            f"{source.name}"
        )

    except FileNotFoundError:

        message = (
            f"找不到 Ghostscript："
            f"{GHOSTSCRIPT}"
        )

        print()
        print("PDF 壓縮失敗")
        print(message)
        print("原始 PDF 不會刪除。")

        log_failed(
            log_name,
            f"{source.name} | {message}"
        )

        cleanup_failed_output(
            output_file
        )

    except subprocess.CalledProcessError as error:

        print()
        print("Ghostscript 執行失敗")
        print(f"錯誤：{error}")
        print("原始 PDF 不會刪除。")

        log_failed(
            log_name,
            f"{source.name} | {error}"
        )

        cleanup_failed_output(
            output_file
        )

    except Exception as error:

        print()
        print("PDF 壓縮失敗")
        print(f"錯誤：{error}")
        print("原始 PDF 不會刪除。")

        log_failed(
            log_name,
            f"{source.name} | {error}"
        )

        cleanup_failed_output(
            output_file
        )


def cleanup_failed_output(
    output_file
):

    if (
        output_file
        and output_file.exists()
    ):

        try:
            output_file.unlink()

        except OSError:
            pass