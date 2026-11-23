from pathlib import Path

from PIL import (
    Image,
    ImageOps,
)

from config import (
    IMAGE_TO_PDF_OUTPUT,
)
from logger import (
    log_failed,
    log_skipped,
    log_success,
)
from utils import (
    JobCancelled,
    is_temp_file,
    unique_path,
    wait_until_ready,
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


def emit(callback, message, level="INFO", progress=None):

    if callback:
        callback(message, level, progress)


def image_to_pdf(
    file_path,
    delete_source=True,
    progress_callback=None,
    cancel_event=None,
):

    source = Path(file_path)

    if not source.exists():
        raise FileNotFoundError(f"找不到圖片：{source}")

    if is_temp_file(source):
        return None

    if source.suffix.lower() not in SUPPORTED_IMAGES:
        raise ValueError("不支援的圖片格式。")

    output_file = None

    try:
        if cancel_event and cancel_event.is_set():
            raise JobCancelled("使用者取消轉換。")

        emit(progress_callback, f"讀取圖片：{source.name}")

        if not wait_until_ready(source, cancel_event=cancel_event):
            raise RuntimeError("圖片尚未準備完成。")

        if cancel_event and cancel_event.is_set():
            raise JobCancelled("使用者取消轉換。")

        output_file = unique_path(IMAGE_TO_PDF_OUTPUT, source.stem + ".pdf")

        with Image.open(source) as image:
            emit(progress_callback, (f"圖片尺寸：{image.width} × {image.height}"))

            image = ImageOps.exif_transpose(image)

            if image.mode in (
                "RGBA",
                "LA",
            ):
                rgba = image.convert("RGBA")

                background = Image.new("RGB", rgba.size, "white")

                background.paste(rgba, mask=rgba.getchannel("A"))

                image = background

            elif image.mode == "P":
                if "transparency" in image.info:
                    rgba = image.convert("RGBA")

                    background = Image.new("RGB", rgba.size, "white")

                    background.paste(rgba, mask=(rgba.getchannel("A")))

                    image = background

                else:
                    image = image.convert("RGB")

            elif image.mode != "RGB":
                image = image.convert("RGB")

            if cancel_event and cancel_event.is_set():
                raise JobCancelled("使用者取消轉換。")

            emit(progress_callback, "正在建立 PDF...")

            image.save(output_file, "PDF", resolution=100.0)

        if cancel_event and cancel_event.is_set():
            raise JobCancelled("使用者取消轉換。")

        if not output_file.exists() or output_file.stat().st_size <= 0:
            raise RuntimeError("沒有產生有效 PDF。")

        if delete_source:
            source.unlink()

        emit(progress_callback, f"輸出：{output_file.name}", "SUCCESS", 100)

        log_success("IMAGE_TO_PDF", (f"{source.name} -> {output_file.name}"))

        return output_file

    except JobCancelled:
        if output_file and output_file.exists():
            try:
                output_file.unlink()

            except OSError:
                pass

        emit(progress_callback, "圖片轉換已取消", "WARNING")

        log_skipped("IMAGE_TO_PDF", f"{source.name} | 使用者取消")

        raise

    except Exception as error:
        if output_file and output_file.exists():
            try:
                output_file.unlink()

            except OSError:
                pass

        emit(progress_callback, f"轉換失敗：{error}", "ERROR")

        log_failed("IMAGE_TO_PDF", (f"{source.name} | {error}"))

        raise
