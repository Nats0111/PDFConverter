import os
import queue
import threading
import time
from pathlib import Path

from watchdog.events import FileSystemEventHandler
from watchdog.observers import Observer

from config import (
    APP_NAME,
    APP_VERSION,
    COMPRESS_HIGH_INPUT,
    COMPRESS_LOW_INPUT,
    COMPRESS_MEDIUM_INPUT,
    IMAGE_TO_PDF_INPUT,
    MD_INPUT,
    TEMP,
)
from environment import ensure_tools_in_path
from logger import log_failed
from processors.compress import compress_pdf
from processors.image_to_pdf import image_to_pdf
from processors.markdown import convert_to_markdown
from settings import load_settings
from utils import JobCancelled, cleanup_temp_folder, is_temp_file

# =========================================================
# Deduplicated Task Queue & Worker
# =========================================================


class FolderWatchQueue:
    def __init__(self, stop_event):
        self.stop_event = stop_event
        self.queue = queue.Queue()
        self._lock = threading.Lock()
        self._in_flight = set()

    @staticmethod
    def _normalize_key(task_type, file_path, extra):
        normalized_path = os.path.normcase(str(Path(file_path).resolve()))
        return (task_type, normalized_path, extra)

    def enqueue(self, task_type, file_path, extra=None):
        path = Path(file_path)

        if is_temp_file(path):
            return False

        key = self._normalize_key(task_type, path, extra)

        with self._lock:
            if key in self._in_flight:
                return False
            self._in_flight.add(key)

        self.queue.put((key, task_type, path, extra))
        return True

    def _release(self, key):
        with self._lock:
            self._in_flight.discard(key)

    def _handle_task(self, task_type, path, extra):
        if not path.exists() or not path.is_file():
            return

        label = f"{task_type}:{extra}" if extra else task_type
        print(f"[開始] ({label}) {path.name}")

        if task_type == "markdown":
            convert_to_markdown(path, cancel_event=self.stop_event)

        elif task_type == "compress":
            compress_pdf(path, quality=extra, cancel_event=self.stop_event)

        elif task_type == "image_to_pdf":
            image_to_pdf(path, cancel_event=self.stop_event)

        print(f"[完成] ({label}) {path.name}")

    def run_worker(self):
        while not self.stop_event.is_set():
            try:
                key, task_type, path, extra = self.queue.get(timeout=0.5)

            except queue.Empty:
                continue

            try:
                self._handle_task(task_type, path, extra)

            except JobCancelled:
                print(f"[已取消] {path.name}")

            except Exception as error:
                print(f"[失敗] ({task_type}) {path.name}: {error}")
                log_failed("WATCHER", f"{task_type} | {path.name} | {error}")

            finally:
                self._release(key)
                self.queue.task_done()


# =========================================================
# Watchdog Event Handlers
# =========================================================


class QueuedHandler(FileSystemEventHandler):
    def __init__(self, watch_queue, task_type, extra=None):
        super().__init__()
        self.watch_queue = watch_queue
        self.task_type = task_type
        self.extra = extra

    def on_created(self, event):
        if not event.is_directory:
            self.watch_queue.enqueue(self.task_type, event.src_path, self.extra)

    def on_moved(self, event):
        if not event.is_directory:
            self.watch_queue.enqueue(self.task_type, event.dest_path, self.extra)


# =========================================================
# Startup scan for existing files
# =========================================================


def enqueue_existing_files(watch_queue):
    print("檢查待處理檔案...")

    sources = [
        ("markdown", MD_INPUT, None),
        ("compress", COMPRESS_LOW_INPUT, "low"),
        ("compress", COMPRESS_MEDIUM_INPUT, "medium"),
        ("compress", COMPRESS_HIGH_INPUT, "high"),
        ("image_to_pdf", IMAGE_TO_PDF_INPUT, None),
    ]

    queued_count = 0

    for task_type, folder, extra in sources:
        if not folder.exists():
            continue

        for file in sorted(folder.iterdir()):
            if file.is_file() and watch_queue.enqueue(task_type, file, extra):
                queued_count += 1

    if queued_count:
        print(f"已將 {queued_count} 個現有檔案加入處理佇列。")
    else:
        print("目前沒有待處理檔案。")


# =========================================================
# Main
# =========================================================


def main():
    settings = load_settings()
    tools = ensure_tools_in_path(settings)

    removed_temp = cleanup_temp_folder(TEMP)

    print()
    print("=" * 60)
    print(f"{APP_NAME} V{APP_VERSION} (資料夾監控模式)")
    print("=" * 60)
    print()

    if removed_temp:
        print(f"已清理殘留 Temp：{removed_temp} 個項目")

    gs_status = tools["ghostscript"] or "未偵測到"
    print(f"[ Ghostscript ] {gs_status}")

    print()
    print("[ Markdown ]")
    print(f"  {MD_INPUT}")

    print()
    print("[ PDF Compression ]")
    print(f"  Low    : {COMPRESS_LOW_INPUT}")
    print(f"  Medium : {COMPRESS_MEDIUM_INPUT}")
    print(f"  High   : {COMPRESS_HIGH_INPUT}")

    print()
    print("[ Image → PDF ]")
    print(f"  {IMAGE_TO_PDF_INPUT}")

    print()
    print("-" * 60)
    print("把檔案放入對應的 Input 資料夾即可。")
    print("按 Ctrl+C 停止程式")
    print("-" * 60)
    print()

    stop_event = threading.Event()
    watch_queue = FolderWatchQueue(stop_event)

    worker_thread = threading.Thread(
        target=watch_queue.run_worker,
        name="FolderWatchWorker",
        daemon=True,
    )
    worker_thread.start()

    enqueue_existing_files(watch_queue)

    observer = Observer()
    observer.schedule(
        QueuedHandler(watch_queue, "markdown"), str(MD_INPUT), recursive=False
    )
    observer.schedule(
        QueuedHandler(watch_queue, "compress", "low"),
        str(COMPRESS_LOW_INPUT),
        recursive=False,
    )
    observer.schedule(
        QueuedHandler(watch_queue, "compress", "medium"),
        str(COMPRESS_MEDIUM_INPUT),
        recursive=False,
    )
    observer.schedule(
        QueuedHandler(watch_queue, "compress", "high"),
        str(COMPRESS_HIGH_INPUT),
        recursive=False,
    )
    observer.schedule(
        QueuedHandler(watch_queue, "image_to_pdf"),
        str(IMAGE_TO_PDF_INPUT),
        recursive=False,
    )

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
        stop_event.set()
        observer.stop()

    observer.join()
    worker_thread.join(timeout=5.0)
    print("已停止。")


if __name__ == "__main__":
    main()
