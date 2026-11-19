import time

from watchdog.observers import Observer

from watchdog.events import (
    FileSystemEventHandler,
)

from config import (
    MD_INPUT,

    COMPRESS_LOW_INPUT,
    COMPRESS_MEDIUM_INPUT,
    COMPRESS_HIGH_INPUT,

    IMAGE_TO_PDF_INPUT,
)

from processors.markdown import (
    convert_to_markdown,
)

from processors.compress import (
    compress_pdf,
)

from processors.image_to_pdf import (
    image_to_pdf,
)


# =========================================================
# Markdown Handler
# =========================================================

class MarkdownHandler(
    FileSystemEventHandler
):

    def on_created(
        self,
        event
    ):

        if not event.is_directory:

            convert_to_markdown(
                event.src_path
            )

    def on_moved(
        self,
        event
    ):

        if not event.is_directory:

            convert_to_markdown(
                event.dest_path
            )


# =========================================================
# PDF 壓縮 Handler
# =========================================================

class CompressHandler(
    FileSystemEventHandler
):

    def __init__(
        self,
        quality
    ):

        super().__init__()

        self.quality = quality

    def on_created(
        self,
        event
    ):

        if not event.is_directory:

            compress_pdf(
                event.src_path,
                self.quality
            )

    def on_moved(
        self,
        event
    ):

        if not event.is_directory:

            compress_pdf(
                event.dest_path,
                self.quality
            )


# =========================================================
# Image → PDF Handler
# =========================================================

class ImageToPDFHandler(
    FileSystemEventHandler
):

    def on_created(
        self,
        event
    ):

        if not event.is_directory:

            image_to_pdf(
                event.src_path
            )

    def on_moved(
        self,
        event
    ):

        if not event.is_directory:

            image_to_pdf(
                event.dest_path
            )


# =========================================================
# 處理啟動前已存在的檔案
# =========================================================

def process_existing_files():

    print(
        "檢查待處理檔案..."
    )

    # =====================================================
    # Markdown
    # =====================================================

    for file in (
        MD_INPUT.iterdir()
    ):

        if file.is_file():

            convert_to_markdown(
                file
            )

    # =====================================================
    # PDF Low
    # =====================================================

    for file in (
        COMPRESS_LOW_INPUT.iterdir()
    ):

        if file.is_file():

            compress_pdf(
                file,
                "low"
            )

    # =====================================================
    # PDF Medium
    # =====================================================

    for file in (
        COMPRESS_MEDIUM_INPUT.iterdir()
    ):

        if file.is_file():

            compress_pdf(
                file,
                "medium"
            )

    # =====================================================
    # PDF High
    # =====================================================

    for file in (
        COMPRESS_HIGH_INPUT.iterdir()
    ):

        if file.is_file():

            compress_pdf(
                file,
                "high"
            )

    # =====================================================
    # Image → PDF
    # =====================================================

    for file in (
        IMAGE_TO_PDF_INPUT.iterdir()
    ):

        if file.is_file():

            image_to_pdf(
                file
            )


# =========================================================
# Main
# =========================================================

if __name__ == "__main__":

    print()
    print("=" * 60)
    print(
        "Local Document Converter v2"
    )
    print("=" * 60)

    print()
    print("[ Markdown ]")

    print(
        f"  {MD_INPUT}"
    )

    print()
    print("[ PDF Compression ]")

    print(
        "  Low    : "
        f"{COMPRESS_LOW_INPUT}"
    )

    print(
        "  Medium : "
        f"{COMPRESS_MEDIUM_INPUT}"
    )

    print(
        "  High   : "
        f"{COMPRESS_HIGH_INPUT}"
    )

    print()
    print("[ Image → PDF ]")

    print(
        f"  {IMAGE_TO_PDF_INPUT}"
    )

    print()
    print("-" * 60)

    print(
        "把檔案放入對應的 "
        "Input 資料夾即可。"
    )

    print(
        "按 Ctrl+C 停止程式"
    )

    print("-" * 60)
    print()

    # =====================================================
    # 處理啟動前的檔案
    # =====================================================

    process_existing_files()

    # =====================================================
    # Observer
    # =====================================================

    observer = Observer()

    # Markdown

    observer.schedule(
        MarkdownHandler(),
        str(MD_INPUT),
        recursive=False
    )

    # PDF Low

    observer.schedule(
        CompressHandler("low"),
        str(COMPRESS_LOW_INPUT),
        recursive=False
    )

    # PDF Medium

    observer.schedule(
        CompressHandler("medium"),
        str(COMPRESS_MEDIUM_INPUT),
        recursive=False
    )

    # PDF High

    observer.schedule(
        CompressHandler("high"),
        str(COMPRESS_HIGH_INPUT),
        recursive=False
    )

    # Image → PDF

    observer.schedule(
        ImageToPDFHandler(),
        str(IMAGE_TO_PDF_INPUT),
        recursive=False
    )

    # =====================================================
    # 啟動
    # =====================================================

    observer.start()

    print()
    print("監控中...")
    print()

    try:

        while True:

            time.sleep(1)

    except KeyboardInterrupt:

        print()
        print("正在停止...")

        observer.stop()

    observer.join()

    print("已停止。")