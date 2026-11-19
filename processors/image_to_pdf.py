from pathlib import Path

from PIL import (
    Image,
    ImageOps,
)

from config import (
    IMAGE_TO_PDF_OUTPUT,
)

from utils import (
    wait_until_ready,
    unique_path,
    is_temp_file,
)

from logger import (
    log_success,
    log_failed,
    log_skipped,
)


SUPPORTED_IMAGES = {
    ".jpg",
    ".jpeg",
    ".png",
    ".webp",
    ".bmp",
    ".tif",
    ".tiff",
}


def image_to_pdf(file_path):

    source = Path(file_path)

    if not source.exists():
        return

    if is_temp_file(source):
        return

    # =====================================================
    # 檢查圖片格式
    # =====================================================

    if (
        source.suffix.lower()
        not in SUPPORTED_IMAGES
    ):

        print()
        print(
            "[Image → PDF] "
            "不支援格式："
            f"{source.name}"
        )

        log_skipped(
            "IMAGE_TO_PDF",
            (
                f"{source.name} | "
                "不支援的圖片格式"
            )
        )

        return

    print()
    print("=" * 60)

    print(
        f"[Image → PDF] "
        f"{source.name}"
    )

    if not wait_until_ready(source):

        print(
            "檔案尚未複製完成，跳過。"
        )

        log_skipped(
            "IMAGE_TO_PDF",
            (
                f"{source.name} | "
                "檔案尚未準備完成"
            )
        )

        return

    output_file = None

    try:

        output_file = unique_path(
            IMAGE_TO_PDF_OUTPUT,
            source.stem + ".pdf"
        )

        print(
            "圖片轉 PDF 中..."
        )

        # =================================================
        # 開啟圖片
        # =================================================

        with Image.open(source) as image:

            # 處理手機照片旋轉方向
            image = ImageOps.exif_transpose(
                image
            )

            # =================================================
            # RGBA
            # =================================================

            if image.mode == "RGBA":

                background = Image.new(
                    "RGB",
                    image.size,
                    "white"
                )

                background.paste(
                    image,
                    mask=image.getchannel("A")
                )

                image = background

            # =================================================
            # P / LA
            # =================================================

            elif image.mode in (
                "LA",
                "P"
            ):

                image = image.convert(
                    "RGBA"
                )

                background = Image.new(
                    "RGB",
                    image.size,
                    "white"
                )

                background.paste(
                    image,
                    mask=image.getchannel("A")
                )

                image = background

            # =================================================
            # 其他模式
            # =================================================

            elif image.mode != "RGB":

                image = image.convert(
                    "RGB"
                )

            # =================================================
            # 儲存 PDF
            # =================================================

            image.save(
                output_file,
                "PDF",
                resolution=100.0
            )

        # =================================================
        # 驗證
        # =================================================

        if not output_file.exists():

            raise RuntimeError(
                "沒有產生 PDF"
            )

        output_size = (
            output_file.stat().st_size
        )

        if output_size <= 0:

            raise RuntimeError(
                "產生的 PDF 大小為 0 bytes"
            )

        print()
        print(
            f"完成：{output_file.name}"
        )

        # =================================================
        # Log
        # =================================================

        log_success(
            "IMAGE_TO_PDF",
            (
                f"{source.name} -> "
                f"{output_file.name}"
            )
        )

        # =================================================
        # 成功後刪除原圖
        # =================================================

        source.unlink()

        print(
            "原始圖片已刪除："
            f"{source.name}"
        )

    except Exception as error:

        print()
        print("Image → PDF 失敗")

        print(
            f"檔案：{source.name}"
        )

        print(
            f"錯誤：{error}"
        )

        print(
            "原始圖片不會刪除。"
        )

        log_failed(
            "IMAGE_TO_PDF",
            f"{source.name} | {error}"
        )

        # =================================================
        # 清除失敗 PDF
        # =================================================

        if (
            output_file
            and output_file.exists()
        ):

            try:
                output_file.unlink()

            except OSError:
                pass