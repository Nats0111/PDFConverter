import os
import queue
import threading
import tkinter as tk

from datetime import datetime
from pathlib import Path

from tkinter import (
    ttk,
    filedialog,
    messagebox,
)

from tkinterdnd2 import (
    DND_FILES,
    TkinterDnD,
)

from config import (
    APP_NAME,
    APP_VERSION,
    MD_OUTPUT,
    COMPRESS_OUTPUT,
    IMAGE_TO_PDF_OUTPUT,
    MERGE_OUTPUT,
    SPLIT_OUTPUT,
    OCR_OUTPUT,
    LOGS,
)

from settings import (
    load_settings,
    save_settings,
)

from environment import (
    check_environment,
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

from processors.merge_pdf import (
    merge_pdfs,
)

from processors.split_pdf import (
    split_selected_pages,
    split_every_page,
)

from processors.ocr_pdf import (
    ocr_pdf,
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


class ConverterGUI:

    # =====================================================
    # Init
    # =====================================================

    def __init__(
        self,
        root
    ):

        self.root = root

        self.root.title(
            f"{APP_NAME} V{APP_VERSION}"
        )

        self.root.geometry(
            "920x880"
        )

        self.root.minsize(
            800,
            720
        )

        # =================================================
        # Worker
        # =================================================

        self.event_queue = (
            queue.Queue()
        )

        self.worker = None

        self.stop_requested = (
            threading.Event()
        )

        # =================================================
        # Files
        # =================================================

        self.batch_files = []

        self.merge_files = []

        self.failed_files = []

        # =================================================
        # Load settings
        # =================================================

        self.settings = (
            load_settings()
        )

        # =================================================
        # General vars
        # =================================================

        self.function_var = (
            tk.StringVar(
                value="PDF 壓縮"
            )
        )

        self.status_var = (
            tk.StringVar(
                value="等待操作"
            )
        )

        self.current_file_var = (
            tk.StringVar(
                value="-"
            )
        )

        self.file_progress_text = (
            tk.StringVar(
                value="0%"
            )
        )

        self.batch_progress_text = (
            tk.StringVar(
                value="0 / 0"
            )
        )

        # =================================================
        # Compression
        # =================================================

        self.quality_var = (
            tk.StringVar(
                value=self.settings.get(
                    "compression_quality",
                    "medium"
                )
            )
        )

        # =================================================
        # Merge
        # =================================================

        self.merge_output_name = (
            tk.StringVar(
                value="merged.pdf"
            )
        )

        # =================================================
        # Split
        # =================================================

        self.split_mode = (
            tk.StringVar(
                value="selected"
            )
        )

        self.split_pages = (
            tk.StringVar(
                value="1-5"
            )
        )

        # =================================================
        # OCR
        # =================================================

        languages = set(
            self.settings.get(
                "ocr_languages",
                [
                    "eng",
                    "chi_tra",
                ]
            )
        )

        self.ocr_eng = (
            tk.BooleanVar(
                value=(
                    "eng"
                    in languages
                )
            )
        )

        self.ocr_chi_tra = (
            tk.BooleanVar(
                value=(
                    "chi_tra"
                    in languages
                )
            )
        )

        self.ocr_ita = (
            tk.BooleanVar(
                value=(
                    "ita"
                    in languages
                )
            )
        )

        self.ocr_rotate = (
            tk.BooleanVar(
                value=bool(
                    self.settings.get(
                        "ocr_rotate",
                        True
                    )
                )
            )
        )

        self.ocr_deskew = (
            tk.BooleanVar(
                value=bool(
                    self.settings.get(
                        "ocr_deskew",
                        True
                    )
                )
            )
        )

        self.ocr_sidecar = (
            tk.BooleanVar(
                value=bool(
                    self.settings.get(
                        "ocr_sidecar",
                        False
                    )
                )
            )
        )

        # =================================================
        # Style
        # =================================================

        self.style = (
            ttk.Style()
        )

        try:

            self.style.theme_use(
                "vista"
            )

        except tk.TclError:

            pass

        self.style.configure(
            "Title.TLabel",
            font=(
                "Segoe UI",
                18,
                "bold"
            )
        )

        self.style.configure(
            "Status.TLabel",
            font=(
                "Segoe UI",
                10,
                "bold"
            )
        )

        # =================================================
        # Main
        # =================================================

        self.main = ttk.Frame(
            root,
            padding=20
        )

        self.main.pack(
            fill="both",
            expand=True
        )

        self.build_ui()

        # =================================================
        # Queue polling
        # =================================================

        self.root.after(
            100,
            self.check_event_queue
        )

        # =================================================
        # Window close
        # =================================================

        self.root.protocol(
            "WM_DELETE_WINDOW",
            self.on_close
        )

        # =================================================
        # Environment initial check
        # =================================================

        self.root.after(
            300,
            self.run_environment_check
        )


    # =====================================================
    # Build main UI
    # =====================================================

    def build_ui(self):

        # =================================================
        # Header
        # =================================================

        header = ttk.Frame(
            self.main
        )

        header.pack(
            fill="x"
        )

        ttk.Label(
            header,
            text=APP_NAME,
            style="Title.TLabel"
        ).pack(
            side="left"
        )

        ttk.Label(
            header,
            text=f"V{APP_VERSION}"
        ).pack(
            side="right",
            anchor="e"
        )

        ttk.Label(
            self.main,
            text=(
                "Batch Processing / "
                "PDF Tools / OCR / Markdown"
            )
        ).pack(
            anchor="w",
            pady=(0, 14)
        )

        # =================================================
        # Function
        # =================================================

        function_frame = (
            ttk.LabelFrame(
                self.main,
                text="功能",
                padding=8
            )
        )

        function_frame.pack(
            fill="x",
            pady=(0, 10)
        )

        self.function_combo = (
            ttk.Combobox(
                function_frame,
                textvariable=(
                    self.function_var
                ),
                state="readonly",
                values=[
                    "PDF 壓縮",
                    "Markdown",
                    "Image → PDF",
                    "PDF 合併",
                    "PDF 拆分",
                    "PDF OCR",
                ]
            )
        )

        self.function_combo.pack(
            fill="x"
        )

        self.function_combo.bind(
            "<<ComboboxSelected>>",
            self.on_function_changed
        )

        # =================================================
        # Options container
        # =================================================

        self.options_container = (
            ttk.Frame(
                self.main
            )
        )

        self.options_container.pack(
            fill="both",
            pady=(0, 8)
        )

        # =================================================
        # Action buttons
        # =================================================

        action_frame = ttk.Frame(
            self.main
        )

        action_frame.pack(
            fill="x",
            pady=(2, 8)
        )

        self.start_button = (
            ttk.Button(
                action_frame,
                text="開始處理",
                command=self.start
            )
        )

        self.start_button.pack(
            side="left",
            fill="x",
            expand=True,
            ipady=6
        )

        self.stop_button = (
            ttk.Button(
                action_frame,
                text="停止批次",
                command=self.request_stop,
                state="disabled"
            )
        )

        self.stop_button.pack(
            side="left",
            padx=(8, 0),
            ipadx=15,
            ipady=6
        )

        # =================================================
        # Progress
        # =================================================

        progress_area = (
            ttk.LabelFrame(
                self.main,
                text="處理進度",
                padding=8
            )
        )

        progress_area.pack(
            fill="x",
            pady=(0, 8)
        )

        # Current

        current_frame = (
            ttk.Frame(
                progress_area
            )
        )

        current_frame.pack(
            fill="x"
        )

        ttk.Label(
            current_frame,
            text="目前："
        ).pack(
            side="left"
        )

        ttk.Label(
            current_frame,
            textvariable=(
                self.current_file_var
            )
        ).pack(
            side="left"
        )

        # File progress

        file_header = ttk.Frame(
            progress_area
        )

        file_header.pack(
            fill="x",
            pady=(8, 2)
        )

        ttk.Label(
            file_header,
            text="檔案進度"
        ).pack(
            side="left"
        )

        ttk.Label(
            file_header,
            textvariable=(
                self.file_progress_text
            )
        ).pack(
            side="right"
        )

        self.file_progress = (
            ttk.Progressbar(
                progress_area,
                maximum=100,
                mode="determinate"
            )
        )

        self.file_progress.pack(
            fill="x"
        )

        # Batch progress

        batch_header = ttk.Frame(
            progress_area
        )

        batch_header.pack(
            fill="x",
            pady=(8, 2)
        )

        ttk.Label(
            batch_header,
            text="整體進度"
        ).pack(
            side="left"
        )

        ttk.Label(
            batch_header,
            textvariable=(
                self.batch_progress_text
            )
        ).pack(
            side="right"
        )

        self.batch_progress = (
            ttk.Progressbar(
                progress_area,
                maximum=100,
                mode="determinate"
            )
        )

        self.batch_progress.pack(
            fill="x"
        )

        ttk.Label(
            progress_area,
            textvariable=(
                self.status_var
            ),
            style="Status.TLabel"
        ).pack(
            anchor="w",
            pady=(8, 0)
        )

        # =================================================
        # Console
        # =================================================

        console_frame = (
            ttk.LabelFrame(
                self.main,
                text="執行過程",
                padding=6
            )
        )

        console_frame.pack(
            fill="both",
            expand=True,
            pady=(0, 8)
        )

        console_container = (
            ttk.Frame(
                console_frame
            )
        )

        console_container.pack(
            fill="both",
            expand=True
        )

        self.console = tk.Text(
            console_container,
            height=10,
            wrap="word",

            bg="#101419",
            fg="#D7E0EA",

            insertbackground="white",

            selectbackground="#36536B",

            font=(
                "Consolas",
                9
            ),

            state="disabled",

            relief="flat",

            padx=8,
            pady=8,
        )

        self.console.pack(
            side="left",
            fill="both",
            expand=True
        )

        console_scroll = (
            ttk.Scrollbar(
                console_container,
                orient="vertical",
                command=(
                    self.console.yview
                )
            )
        )

        console_scroll.pack(
            side="right",
            fill="y"
        )

        self.console.config(
            yscrollcommand=(
                console_scroll.set
            )
        )

        self.console.tag_config(
            "INFO",
            foreground="#D7E0EA"
        )

        self.console.tag_config(
            "SUCCESS",
            foreground="#55D187"
        )

        self.console.tag_config(
            "WARNING",
            foreground="#F3C969"
        )

        self.console.tag_config(
            "ERROR",
            foreground="#FF6B6B"
        )

        self.console.tag_config(
            "SYSTEM",
            foreground="#66B7FF"
        )

        # =================================================
        # Bottom bar
        # =================================================

        bottom = ttk.Frame(
            self.main
        )

        bottom.pack(
            fill="x"
        )

        ttk.Button(
            bottom,
            text="開啟輸出資料夾",
            command=self.open_output
        ).pack(
            side="left"
        )

        ttk.Button(
            bottom,
            text="檢查環境",
            command=self.run_environment_check
        ).pack(
            side="left",
            padx=5
        )

        ttk.Button(
            bottom,
            text="查看 Log",
            command=self.open_log
        ).pack(
            side="left"
        )

        ttk.Button(
            bottom,
            text="清除執行過程",
            command=self.clear_console
        ).pack(
            side="right"
        )

        # =================================================
        # Dynamic section
        # =================================================

        self.rebuild_options()

        self.console_log(
            (
                f"{APP_NAME} "
                f"V{APP_VERSION} 已啟動"
            ),
            "SYSTEM"
        )


    # =====================================================
    # Dynamic UI
    # =====================================================

    def clear_options_container(
        self
    ):

        for widget in (
            self.options_container
            .winfo_children()
        ):

            widget.destroy()


    def rebuild_options(
        self
    ):

        self.clear_options_container()

        function = (
            self.function_var.get()
        )

        if (
            function
            == "PDF 合併"
        ):

            self.build_merge_options()

            return

        self.build_batch_options()

        if (
            function
            == "PDF 壓縮"
        ):

            self.build_compression_options()

        elif (
            function
            == "PDF OCR"
        ):

            self.build_ocr_options()

        elif (
            function
            == "PDF 拆分"
        ):

            self.build_split_options()


    def on_function_changed(
        self,
        event=None
    ):

        if (
            self.worker
            and self.worker.is_alive()
        ):

            return

        self.batch_files.clear()

        self.merge_files.clear()

        self.failed_files.clear()

        self.rebuild_options()

        self.reset_progress()

        self.status_var.set(
            "等待操作"
        )


    # =====================================================
    # Batch options
    # =====================================================

    def build_batch_options(
        self
    ):

        self.batch_frame = (
            ttk.LabelFrame(
                self.options_container,
                text=(
                    "待處理檔案"
                    "（可直接拖入）"
                ),
                padding=8
            )
        )

        self.batch_frame.pack(
            fill="both",
            pady=(0, 8)
        )

        list_container = (
            ttk.Frame(
                self.batch_frame
            )
        )

        list_container.pack(
            fill="both",
            expand=True
        )

        self.batch_list = (
            tk.Listbox(
                list_container,
                height=6,
                selectmode=(
                    tk.EXTENDED
                )
            )
        )

        self.batch_list.pack(
            side="left",
            fill="both",
            expand=True
        )

        scrollbar = (
            ttk.Scrollbar(
                list_container,
                orient="vertical",
                command=(
                    self.batch_list
                    .yview
                )
            )
        )

        scrollbar.pack(
            side="right",
            fill="y"
        )

        self.batch_list.config(
            yscrollcommand=(
                scrollbar.set
            )
        )

        self.batch_list.drop_target_register(
            DND_FILES
        )

        self.batch_list.dnd_bind(
            "<<Drop>>",
            self.on_batch_drop
        )

        buttons = ttk.Frame(
            self.batch_frame
        )

        buttons.pack(
            fill="x",
            pady=(7, 0)
        )

        ttk.Button(
            buttons,
            text="新增檔案",
            command=(
                self.add_batch_files
            )
        ).pack(
            side="left"
        )

        ttk.Button(
            buttons,
            text="移除",
            command=(
                self.remove_batch_files
            )
        ).pack(
            side="left",
            padx=5
        )

        ttk.Button(
            buttons,
            text="清空",
            command=(
                self.clear_batch_files
            )
        ).pack(
            side="left"
        )

        self.refresh_batch_list()


    # =====================================================
    # Compression options
    # =====================================================

    def build_compression_options(
        self
    ):

        frame = ttk.LabelFrame(
            self.options_container,
            text="壓縮品質",
            padding=8
        )

        frame.pack(
            fill="x"
        )

        ttk.Radiobutton(
            frame,
            text="強力",
            variable=(
                self.quality_var
            ),
            value="low",
            command=self.save_current_settings
        ).pack(
            side="left",
            padx=(0, 25)
        )

        ttk.Radiobutton(
            frame,
            text="平衡",
            variable=(
                self.quality_var
            ),
            value="medium",
            command=self.save_current_settings
        ).pack(
            side="left",
            padx=(0, 25)
        )

        ttk.Radiobutton(
            frame,
            text="高品質",
            variable=(
                self.quality_var
            ),
            value="high",
            command=self.save_current_settings
        ).pack(
            side="left"
        )


    # =====================================================
    # OCR options
    # =====================================================

    def build_ocr_options(
        self
    ):

        frame = ttk.LabelFrame(
            self.options_container,
            text="OCR 設定",
            padding=8
        )

        frame.pack(
            fill="x"
        )

        ttk.Label(
            frame,
            text="OCR 語言"
        ).pack(
            anchor="w"
        )

        languages = ttk.Frame(
            frame
        )

        languages.pack(
            fill="x",
            pady=(5, 8)
        )

        ttk.Checkbutton(
            languages,
            text="English",
            variable=(
                self.ocr_eng
            ),
            command=(
                self.save_current_settings
            )
        ).pack(
            side="left"
        )

        ttk.Checkbutton(
            languages,
            text="繁體中文",
            variable=(
                self.ocr_chi_tra
            ),
            command=(
                self.save_current_settings
            )
        ).pack(
            side="left",
            padx=20
        )

        ttk.Checkbutton(
            languages,
            text="Italiano",
            variable=(
                self.ocr_ita
            ),
            command=(
                self.save_current_settings
            )
        ).pack(
            side="left"
        )

        ttk.Separator(
            frame,
            orient="horizontal"
        ).pack(
            fill="x",
            pady=(0, 8)
        )

        ttk.Checkbutton(
            frame,
            text="自動旋轉",
            variable=(
                self.ocr_rotate
            ),
            command=(
                self.save_current_settings
            )
        ).pack(
            anchor="w"
        )

        ttk.Checkbutton(
            frame,
            text="歪斜校正",
            variable=(
                self.ocr_deskew
            ),
            command=(
                self.save_current_settings
            )
        ).pack(
            anchor="w"
        )

        ttk.Checkbutton(
            frame,
            text=(
                "同時輸出 OCR "
                "文字檔 (.txt)"
            ),
            variable=(
                self.ocr_sidecar
            ),
            command=(
                self.save_current_settings
            )
        ).pack(
            anchor="w",
            pady=(5, 0)
        )


    # =====================================================
    # Split options
    # =====================================================

    def build_split_options(
        self
    ):

        frame = ttk.LabelFrame(
            self.options_container,
            text="拆分設定",
            padding=8
        )

        frame.pack(
            fill="x"
        )

        ttk.Radiobutton(
            frame,
            text="指定頁面",
            variable=(
                self.split_mode
            ),
            value="selected",
            command=(
                self.update_split_ui
            )
        ).pack(
            anchor="w"
        )

        ttk.Radiobutton(
            frame,
            text="每頁拆成獨立 PDF",
            variable=(
                self.split_mode
            ),
            value="every",
            command=(
                self.update_split_ui
            )
        ).pack(
            anchor="w",
            pady=(2, 6)
        )

        ttk.Label(
            frame,
            text=(
                "頁碼，例如："
                "1-5 或 1,3,8-10"
            )
        ).pack(
            anchor="w"
        )

        self.split_pages_entry = (
            ttk.Entry(
                frame,
                textvariable=(
                    self.split_pages
                )
            )
        )

        self.split_pages_entry.pack(
            fill="x",
            pady=(3, 0)
        )

        self.update_split_ui()


    def update_split_ui(
        self
    ):

        if not hasattr(
            self,
            "split_pages_entry"
        ):

            return

        if not (
            self.split_pages_entry
            .winfo_exists()
        ):

            return

        if (
            self.split_mode.get()
            == "selected"
        ):

            self.split_pages_entry.config(
                state="normal"
            )

        else:

            self.split_pages_entry.config(
                state="disabled"
            )


    # =====================================================
    # Merge options
    # =====================================================

    def build_merge_options(
        self
    ):

        self.merge_frame = (
            ttk.LabelFrame(
                self.options_container,
                text=(
                    "PDF 合併"
                    "（可直接拖入）"
                ),
                padding=8
            )
        )

        self.merge_frame.pack(
            fill="both"
        )

        list_frame = ttk.Frame(
            self.merge_frame
        )

        list_frame.pack(
            fill="both",
            expand=True
        )

        self.merge_list = (
            tk.Listbox(
                list_frame,
                height=7,
                selectmode=(
                    tk.SINGLE
                )
            )
        )

        self.merge_list.pack(
            side="left",
            fill="both",
            expand=True
        )

        scrollbar = (
            ttk.Scrollbar(
                list_frame,
                orient="vertical",
                command=(
                    self.merge_list
                    .yview
                )
            )
        )

        scrollbar.pack(
            side="right",
            fill="y"
        )

        self.merge_list.config(
            yscrollcommand=(
                scrollbar.set
            )
        )

        self.merge_list.drop_target_register(
            DND_FILES
        )

        self.merge_list.dnd_bind(
            "<<Drop>>",
            self.on_merge_drop
        )

        buttons = ttk.Frame(
            self.merge_frame
        )

        buttons.pack(
            fill="x",
            pady=(7, 6)
        )

        ttk.Button(
            buttons,
            text="加入 PDF",
            command=(
                self.add_merge_files
            )
        ).pack(
            side="left"
        )

        ttk.Button(
            buttons,
            text="移除",
            command=(
                self.remove_merge_file
            )
        ).pack(
            side="left",
            padx=5
        )

        ttk.Button(
            buttons,
            text="↑",
            width=4,
            command=lambda:
                self.move_merge(-1)
        ).pack(
            side="left"
        )

        ttk.Button(
            buttons,
            text="↓",
            width=4,
            command=lambda:
                self.move_merge(1)
        ).pack(
            side="left",
            padx=5
        )

        ttk.Button(
            buttons,
            text="清空",
            command=(
                self.clear_merge_files
            )
        ).pack(
            side="left"
        )

        ttk.Label(
            self.merge_frame,
            text="輸出檔名"
        ).pack(
            anchor="w"
        )

        ttk.Entry(
            self.merge_frame,
            textvariable=(
                self.merge_output_name
            )
        ).pack(
            fill="x",
            pady=(3, 0)
        )

        self.refresh_merge()


    # =====================================================
    # Settings
    # =====================================================

    def save_current_settings(
        self
    ):

        languages = []

        if self.ocr_eng.get():

            languages.append(
                "eng"
            )

        if self.ocr_chi_tra.get():

            languages.append(
                "chi_tra"
            )

        if self.ocr_ita.get():

            languages.append(
                "ita"
            )

        data = {

            "compression_quality":
                self.quality_var.get(),

            "ocr_languages":
                languages,

            "ocr_rotate":
                bool(
                    self.ocr_rotate.get()
                ),

            "ocr_deskew":
                bool(
                    self.ocr_deskew.get()
                ),

            "ocr_sidecar":
                bool(
                    self.ocr_sidecar.get()
                ),
        }

        save_settings(
            data
        )


    # =====================================================
    # Environment check
    # =====================================================

    def run_environment_check(
        self
    ):

        self.console_log(
            "開始檢查執行環境",
            "SYSTEM"
        )

        try:

            report = (
                check_environment()
            )

            for item in report:

                if item["ok"]:

                    self.console_log(
                        (
                            "✓ "
                            f"{item['name']} "
                            f"({item['detail']})"
                        ),
                        "SUCCESS"
                    )

                else:

                    self.console_log(
                        (
                            "✗ "
                            f"{item['name']} "
                            f"({item['detail']})"
                        ),
                        "WARNING"
                    )

        except Exception as error:

            self.console_log(
                (
                    "環境檢查失敗："
                    f"{error}"
                ),
                "ERROR"
            )


    # =====================================================
    # Add batch files
    # =====================================================

    def get_filetypes(
        self
    ):

        function = (
            self.function_var.get()
        )

        if function in (
            "PDF 壓縮",
            "PDF 拆分",
            "PDF OCR",
        ):

            return [
                (
                    "PDF",
                    "*.pdf"
                )
            ]

        if (
            function
            == "Image → PDF"
        ):

            return [
                (
                    "圖片",
                    (
                        "*.jpg",
                        "*.jpeg",
                        "*.png",
                        "*.webp",
                        "*.bmp",
                        "*.tif",
                        "*.tiff",
                    )
                )
            ]

        return [
            (
                "所有檔案",
                "*.*"
            )
        ]


    def file_allowed(
        self,
        path
    ):

        function = (
            self.function_var.get()
        )

        suffix = (
            path.suffix.lower()
        )

        if function in (
            "PDF 壓縮",
            "PDF 拆分",
            "PDF OCR",
        ):

            return (
                suffix
                == ".pdf"
            )

        if (
            function
            == "Image → PDF"
        ):

            return (
                suffix
                in SUPPORTED_IMAGES
            )

        if (
            function
            == "Markdown"
        ):

            return True

        return False


    def add_batch_files(
        self
    ):

        files = (
            filedialog
            .askopenfilenames(
                title="選擇檔案",
                filetypes=(
                    self.get_filetypes()
                )
            )
        )

        self.add_paths_to_batch(
            files
        )


    def add_paths_to_batch(
        self,
        paths
    ):

        added = 0

        skipped = 0

        for item in paths:

            path = Path(
                item
            )

            if (
                not path.is_file()
                or not self.file_allowed(
                    path
                )
            ):

                skipped += 1
                continue

            file_string = str(
                path
            )

            if (
                file_string
                not in self.batch_files
            ):

                self.batch_files.append(
                    file_string
                )

                added += 1

        self.refresh_batch_list()

        if added:

            self.console_log(
                (
                    f"加入 "
                    f"{added} 個檔案"
                ),
                "SYSTEM"
            )

        if skipped:

            self.console_log(
                (
                    f"略過 "
                    f"{skipped} 個"
                    "不符合目前功能的檔案"
                ),
                "WARNING"
            )


    def on_batch_drop(
        self,
        event
    ):

        paths = (
            self.root.tk.splitlist(
                event.data
            )
        )

        self.add_paths_to_batch(
            paths
        )


    def refresh_batch_list(
        self
    ):

        if not hasattr(
            self,
            "batch_list"
        ):

            return

        if not (
            self.batch_list
            .winfo_exists()
        ):

            return

        self.batch_list.delete(
            0,
            tk.END
        )

        failed_set = set(
            self.failed_files
        )

        for file in (
            self.batch_files
        ):

            if (
                file
                in failed_set
            ):

                prefix = "✗"

            else:

                prefix = "○"

            self.batch_list.insert(
                tk.END,
                (
                    f"{prefix} "
                    f"{Path(file).name}"
                )
            )


    def remove_batch_files(
        self
    ):

        selections = list(
            self.batch_list
            .curselection()
        )

        for index in reversed(
            selections
        ):

            file = (
                self.batch_files[
                    index
                ]
            )

            if (
                file
                in self.failed_files
            ):

                self.failed_files.remove(
                    file
                )

            del self.batch_files[
                index
            ]

        self.refresh_batch_list()


    def clear_batch_files(
        self
    ):

        self.batch_files.clear()

        self.failed_files.clear()

        self.refresh_batch_list()


    # =====================================================
    # Merge list
    # =====================================================

    def add_merge_files(
        self
    ):

        files = (
            filedialog
            .askopenfilenames(
                title="選擇 PDF",
                filetypes=[
                    (
                        "PDF",
                        "*.pdf"
                    )
                ]
            )
        )

        self.add_paths_to_merge(
            files
        )


    def add_paths_to_merge(
        self,
        paths
    ):

        added = 0

        for item in paths:

            path = Path(
                item
            )

            if (
                not path.is_file()
                or
                path.suffix.lower()
                != ".pdf"
            ):

                continue

            file_string = str(
                path
            )

            if (
                file_string
                not in self.merge_files
            ):

                self.merge_files.append(
                    file_string
                )

                added += 1

        self.refresh_merge()

        if added:

            self.console_log(
                (
                    f"加入 "
                    f"{added} 個 PDF"
                ),
                "SYSTEM"
            )


    def on_merge_drop(
        self,
        event
    ):

        paths = (
            self.root.tk.splitlist(
                event.data
            )
        )

        self.add_paths_to_merge(
            paths
        )


    def refresh_merge(
        self
    ):

        if not hasattr(
            self,
            "merge_list"
        ):

            return

        if not (
            self.merge_list
            .winfo_exists()
        ):

            return

        self.merge_list.delete(
            0,
            tk.END
        )

        for index, file in enumerate(
            self.merge_files,
            start=1
        ):

            self.merge_list.insert(
                tk.END,
                (
                    f"{index}. "
                    f"{Path(file).name}"
                )
            )


    def remove_merge_file(
        self
    ):

        selection = (
            self.merge_list
            .curselection()
        )

        if not selection:

            return

        del self.merge_files[
            selection[0]
        ]

        self.refresh_merge()


    def clear_merge_files(
        self
    ):

        self.merge_files.clear()

        self.refresh_merge()


    def move_merge(
        self,
        direction
    ):

        selected = (
            self.merge_list
            .curselection()
        )

        if not selected:

            return

        index = (
            selected[0]
        )

        new_index = (
            index
            + direction
        )

        if not (
            0
            <= new_index
            < len(
                self.merge_files
            )
        ):

            return

        (
            self.merge_files[
                index
            ],
            self.merge_files[
                new_index
            ]
        ) = (
            self.merge_files[
                new_index
            ],
            self.merge_files[
                index
            ]
        )

        self.refresh_merge()

        self.merge_list.selection_set(
            new_index
        )


    # =====================================================
    # Console
    # =====================================================

    def console_log(
        self,
        message,
        level="INFO"
    ):

        timestamp = (
            datetime.now().strftime(
                "%H:%M:%S"
            )
        )

        self.console.config(
            state="normal"
        )

        self.console.insert(
            tk.END,
            (
                f"[{timestamp}] "
            ),
            "SYSTEM"
        )

        self.console.insert(
            tk.END,
            f"{message}\n",
            level
        )

        self.console.see(
            tk.END
        )

        self.console.config(
            state="disabled"
        )


    def clear_console(
        self
    ):

        self.console.config(
            state="normal"
        )

        self.console.delete(
            "1.0",
            tk.END
        )

        self.console.config(
            state="disabled"
        )

        self.console_log(
            "執行過程已清除",
            "SYSTEM"
        )


    # =====================================================
    # Processor callback
    # =====================================================

    def processor_callback(
        self,
        message,
        level="INFO",
        progress=None
    ):

        self.event_queue.put(
            (
                "processor_progress",
                {
                    "message":
                        message,

                    "level":
                        level,

                    "progress":
                        progress,
                }
            )
        )


    # =====================================================
    # Build job options
    # =====================================================

    def build_options(
        self
    ):

        function = (
            self.function_var.get()
        )

        options = {
            "function":
                function
        }

        if (
            function
            == "PDF 壓縮"
        ):

            options[
                "quality"
            ] = (
                self.quality_var.get()
            )

        elif (
            function
            == "PDF OCR"
        ):

            languages = []

            if self.ocr_eng.get():

                languages.append(
                    "eng"
                )

            if (
                self.ocr_chi_tra.get()
            ):

                languages.append(
                    "chi_tra"
                )

            if self.ocr_ita.get():

                languages.append(
                    "ita"
                )

            if not languages:

                raise ValueError(
                    (
                        "請至少選擇一種 "
                        "OCR 語言。"
                    )
                )

            options[
                "languages"
            ] = languages

            options[
                "rotate"
            ] = bool(
                self.ocr_rotate.get()
            )

            options[
                "deskew"
            ] = bool(
                self.ocr_deskew.get()
            )

            options[
                "sidecar"
            ] = bool(
                self.ocr_sidecar.get()
            )

        elif (
            function
            == "PDF 拆分"
        ):

            options[
                "split_mode"
            ] = (
                self.split_mode.get()
            )

            pages = (
                self.split_pages
                .get()
                .strip()
            )

            if (
                options[
                    "split_mode"
                ]
                == "selected"
                and not pages
            ):

                raise ValueError(
                    "請輸入拆分頁碼。"
                )

            options[
                "pages"
            ] = pages

        return options


    # =====================================================
    # Start
    # =====================================================

    def start(
        self
    ):

        if (
            self.worker
            and self.worker.is_alive()
        ):

            return

        self.stop_requested.clear()

        self.failed_files.clear()

        function = (
            self.function_var.get()
        )

        try:

            options = (
                self.build_options()
            )

            if (
                function
                == "PDF 合併"
            ):

                if (
                    len(
                        self.merge_files
                    )
                    < 2
                ):

                    raise ValueError(
                        (
                            "PDF 合併至少"
                            "需要兩個 PDF。"
                        )
                    )

                files = (
                    self.merge_files.copy()
                )

                options[
                    "output_name"
                ] = (
                    self.merge_output_name
                    .get()
                    .strip()
                    or
                    "merged.pdf"
                )

            else:

                if not self.batch_files:

                    raise ValueError(
                        "請至少加入一個檔案。"
                    )

                files = (
                    self.batch_files.copy()
                )

        except Exception as error:

            messagebox.showerror(
                "無法開始",
                str(error)
            )

            return

        self.save_current_settings()

        self.reset_progress()

        total = (
            1
            if function
            == "PDF 合併"
            else len(files)
        )

        self.batch_progress_text.set(
            f"0 / {total}"
        )

        self.status_var.set(
            "處理中..."
        )

        self.function_combo.config(
            state="disabled"
        )

        self.start_button.config(
            state="disabled"
        )

        self.stop_button.config(
            state="normal"
        )

        self.console_log(
            "────────────────────────────",
            "SYSTEM"
        )

        self.console_log(
            (
                f"開始工作："
                f"{function}"
            ),
            "SYSTEM"
        )

        self.worker = (
            threading.Thread(
                target=self.run_batch,
                args=(
                    files,
                    options,
                ),
                daemon=True
            )
        )

        self.worker.start()


    # =====================================================
    # Stop
    # =====================================================

    def request_stop(
        self
    ):

        if not (
            self.worker
            and self.worker.is_alive()
        ):

            return

        self.stop_requested.set()

        self.stop_button.config(
            state="disabled"
        )

        self.status_var.set(
            (
                "停止已要求，"
                "目前檔案完成後停止..."
            )
        )

        self.console_log(
            (
                "已要求停止批次，"
                "目前檔案完成後停止"
            ),
            "WARNING"
        )


    # =====================================================
    # Worker
    # =====================================================

    def run_batch(
        self,
        files,
        options
    ):

        function = (
            options["function"]
        )

        success_files = []

        failed_files = []

        processed_count = 0

        # =================================================
        # Merge
        # =================================================

        if (
            function
            == "PDF 合併"
        ):

            try:

                self.event_queue.put(
                    (
                        "file_start",
                        {
                            "index": 1,
                            "total": 1,
                            "name":
                                "PDF 合併",
                        }
                    )
                )

                result = merge_pdfs(
                    files,
                    options[
                        "output_name"
                    ],
                    progress_callback=(
                        self.processor_callback
                    ),
                )

                success_files = (
                    files.copy()
                )

                processed_count = 1

                self.event_queue.put(
                    (
                        "file_success",
                        {
                            "index": 1,
                            "total": 1,
                            "result":
                                result,
                        }
                    )
                )

            except Exception as error:

                failed_files = (
                    files.copy()
                )

                processed_count = 1

                self.event_queue.put(
                    (
                        "file_error",
                        {
                            "index": 1,
                            "total": 1,
                            "error":
                                str(error),
                        }
                    )
                )

            self.event_queue.put(
                (
                    "batch_done",
                    {
                        "success_files":
                            success_files,

                        "failed_files":
                            failed_files,

                        "processed":
                            processed_count,

                        "total":
                            1,

                        "stopped":
                            False,
                    }
                )
            )

            return

        # =================================================
        # Standard batch
        # =================================================

        total = len(files)

        for index, file in enumerate(
            files,
            start=1
        ):

            if (
                self.stop_requested
                .is_set()
            ):

                break

            source = Path(
                file
            )

            self.event_queue.put(
                (
                    "file_start",
                    {
                        "index":
                            index,

                        "total":
                            total,

                        "name":
                            source.name,
                    }
                )
            )

            try:

                if (
                    function
                    == "PDF 壓縮"
                ):

                    result = (
                        compress_pdf(
                            source,
                            quality=(
                                options[
                                    "quality"
                                ]
                            ),
                            delete_source=False,
                            progress_callback=(
                                self.processor_callback
                            ),
                        )
                    )

                elif (
                    function
                    == "Markdown"
                ):

                    result = (
                        convert_to_markdown(
                            source,
                            move_source=False,
                            progress_callback=(
                                self.processor_callback
                            ),
                        )
                    )

                elif (
                    function
                    == "Image → PDF"
                ):

                    result = (
                        image_to_pdf(
                            source,
                            delete_source=False,
                            progress_callback=(
                                self.processor_callback
                            ),
                        )
                    )

                elif (
                    function
                    == "PDF OCR"
                ):

                    result = ocr_pdf(
                        source,
                        languages=(
                            options[
                                "languages"
                            ]
                        ),
                        rotate_pages=(
                            options[
                                "rotate"
                            ]
                        ),
                        deskew=(
                            options[
                                "deskew"
                            ]
                        ),
                        create_sidecar=(
                            options[
                                "sidecar"
                            ]
                        ),
                        progress_callback=(
                            self.processor_callback
                        ),
                    )

                elif (
                    function
                    == "PDF 拆分"
                ):

                    if (
                        options[
                            "split_mode"
                        ]
                        == "every"
                    ):

                        result = (
                            split_every_page(
                                source,
                                progress_callback=(
                                    self.processor_callback
                                ),
                            )
                        )

                    else:

                        result = (
                            split_selected_pages(
                                source,
                                options[
                                    "pages"
                                ],
                                progress_callback=(
                                    self.processor_callback
                                ),
                            )
                        )

                else:

                    raise ValueError(
                        (
                            "未知功能："
                            f"{function}"
                        )
                    )

                success_files.append(
                    str(source)
                )

                processed_count += 1

                self.event_queue.put(
                    (
                        "file_success",
                        {
                            "index":
                                index,

                            "total":
                                total,

                            "result":
                                result,

                            "file":
                                str(source),
                        }
                    )
                )

            except Exception as error:

                failed_files.append(
                    str(source)
                )

                processed_count += 1

                self.event_queue.put(
                    (
                        "file_error",
                        {
                            "index":
                                index,

                            "total":
                                total,

                            "error":
                                str(error),

                            "file":
                                str(source),
                        }
                    )
                )

        stopped = (
            self.stop_requested
            .is_set()
        )

        self.event_queue.put(
            (
                "batch_done",
                {
                    "success_files":
                        success_files,

                    "failed_files":
                        failed_files,

                    "processed":
                        processed_count,

                    "total":
                        total,

                    "stopped":
                        stopped,
                }
            )
        )


    # =====================================================
    # Queue
    # =====================================================

    def check_event_queue(
        self
    ):

        try:

            while True:

                event, data = (
                    self.event_queue
                    .get_nowait()
                )

                if (
                    event
                    == "file_start"
                ):

                    self.handle_file_start(
                        data
                    )

                elif (
                    event
                    == "processor_progress"
                ):

                    self.handle_processor_progress(
                        data
                    )

                elif (
                    event
                    == "file_success"
                ):

                    self.handle_file_success(
                        data
                    )

                elif (
                    event
                    == "file_error"
                ):

                    self.handle_file_error(
                        data
                    )

                elif (
                    event
                    == "batch_done"
                ):

                    self.finish_batch(
                        data
                    )

        except queue.Empty:

            pass

        self.root.after(
            100,
            self.check_event_queue
        )


    # =====================================================
    # Event handlers
    # =====================================================

    def handle_file_start(
        self,
        data
    ):

        self.current_file_var.set(
            data["name"]
        )

        self.file_progress.stop()

        self.file_progress.config(
            mode="indeterminate"
        )

        self.file_progress[
            "value"
        ] = 0

        self.file_progress.start(
            10
        )

        self.file_progress_text.set(
            "處理中"
        )

        self.console_log(
            (
                f"[{data['index']}/"
                f"{data['total']}] "
                f"{data['name']}"
            ),
            "SYSTEM"
        )


    def handle_processor_progress(
        self,
        data
    ):

        self.console_log(
            data["message"],
            data["level"]
        )

        progress = (
            data["progress"]
        )

        if progress is None:

            if (
                str(
                    self.file_progress[
                        "mode"
                    ]
                )
                != "indeterminate"
            ):

                self.file_progress.stop()

                self.file_progress.config(
                    mode="indeterminate"
                )

                self.file_progress.start(
                    10
                )

            self.file_progress_text.set(
                "處理中"
            )

            return

        self.file_progress.stop()

        self.file_progress.config(
            mode="determinate"
        )

        value = max(
            0.0,
            min(
                100.0,
                float(progress)
            )
        )

        self.file_progress[
            "value"
        ] = value

        self.file_progress_text.set(
            f"{value:.0f}%"
        )


    def handle_file_success(
        self,
        data
    ):

        self.file_progress.stop()

        self.file_progress.config(
            mode="determinate"
        )

        self.file_progress[
            "value"
        ] = 100

        self.file_progress_text.set(
            "100%"
        )

        overall = (
            data["index"]
            / data["total"]
            * 100
        )

        self.batch_progress[
            "value"
        ] = overall

        self.batch_progress_text.set(
            (
                f"{data['index']} "
                f"/ {data['total']}"
            )
        )

        self.console_log(
            "✓ 檔案處理完成",
            "SUCCESS"
        )


    def handle_file_error(
        self,
        data
    ):

        self.file_progress.stop()

        self.file_progress.config(
            mode="determinate"
        )

        self.file_progress_text.set(
            "失敗"
        )

        overall = (
            data["index"]
            / data["total"]
            * 100
        )

        self.batch_progress[
            "value"
        ] = overall

        self.batch_progress_text.set(
            (
                f"{data['index']} "
                f"/ {data['total']}"
            )
        )

        self.console_log(
            (
                "✗ 處理失敗："
                f"{data['error']}"
            ),
            "ERROR"
        )


    # =====================================================
    # Finish
    # =====================================================

    def finish_batch(
        self,
        data
    ):

        self.file_progress.stop()

        self.file_progress.config(
            mode="determinate"
        )

        self.function_combo.config(
            state="readonly"
        )

        self.start_button.config(
            state="normal"
        )

        self.stop_button.config(
            state="disabled"
        )

        self.current_file_var.set(
            "-"
        )

        success_files = (
            data["success_files"]
        )

        failed_files = (
            data["failed_files"]
        )

        stopped = (
            data["stopped"]
        )

        function = (
            self.function_var.get()
        )

        # =================================================
        # Merge
        # =================================================

        if (
            function
            == "PDF 合併"
        ):

            if not failed_files:

                self.merge_files.clear()

            self.refresh_merge()

        # =================================================
        # Standard batch
        # =================================================

        else:

            # Success items removed
            success_set = set(
                success_files
            )

            self.batch_files = [

                file

                for file
                in self.batch_files

                if file
                not in success_set
            ]

            # Failed items remain marked
            self.failed_files = [

                file

                for file
                in failed_files

                if file
                in self.batch_files
            ]

            self.refresh_batch_list()

        # =================================================
        # Status
        # =================================================

        success_count = len(
            success_files
        )

        failed_count = len(
            failed_files
        )

        if stopped:

            self.status_var.set(
                (
                    "已停止："
                    f"{success_count} 成功，"
                    f"{failed_count} 失敗"
                )
            )

            self.console_log(
                "批次已停止",
                "WARNING"
            )

        else:

            self.status_var.set(
                (
                    "完成："
                    f"{success_count} 成功，"
                    f"{failed_count} 失敗"
                )
            )

            level = (
                "SUCCESS"
                if failed_count == 0
                else "WARNING"
            )

            self.console_log(
                (
                    "批次處理完成 | "
                    f"成功 {success_count} | "
                    f"失敗 {failed_count}"
                ),
                level
            )

        if (
            failed_count > 0
            and function
            != "PDF 合併"
        ):

            self.console_log(
                (
                    "失敗項目已保留在清單，"
                    "可直接重新執行"
                ),
                "WARNING"
            )

        elif (
            not stopped
            and failed_count == 0
        ):

            self.console_log(
                "已自動清除成功項目",
                "SYSTEM"
            )


    # =====================================================
    # Reset progress
    # =====================================================

    def reset_progress(
        self
    ):

        self.file_progress.stop()

        self.file_progress.config(
            mode="determinate"
        )

        self.file_progress[
            "value"
        ] = 0

        self.batch_progress[
            "value"
        ] = 0

        self.file_progress_text.set(
            "0%"
        )

        self.batch_progress_text.set(
            "0 / 0"
        )

        self.current_file_var.set(
            "-"
        )


    # =====================================================
    # Output folder
    # =====================================================

    def open_output(
        self
    ):

        folders = {

            "PDF 壓縮":
                COMPRESS_OUTPUT,

            "Markdown":
                MD_OUTPUT,

            "Image → PDF":
                IMAGE_TO_PDF_OUTPUT,

            "PDF 合併":
                MERGE_OUTPUT,

            "PDF 拆分":
                SPLIT_OUTPUT,

            "PDF OCR":
                OCR_OUTPUT,
        }

        folder = folders.get(
            self.function_var.get()
        )

        if not folder:

            return

        try:

            os.startfile(
                str(folder)
            )

        except Exception as error:

            messagebox.showerror(
                "無法開啟資料夾",
                str(error)
            )


    # =====================================================
    # Log
    # =====================================================

    def open_log(
        self
    ):

        log_file = (
            LOGS
            / "converter.log"
        )

        if not (
            log_file.exists()
        ):

            messagebox.showinfo(
                "Log",
                "目前沒有 Log。"
            )

            return

        try:

            os.startfile(
                str(log_file)
            )

        except Exception as error:

            messagebox.showerror(
                "無法開啟 Log",
                str(error)
            )


    # =====================================================
    # Close
    # =====================================================

    def on_close(
        self
    ):

        if (
            self.worker
            and self.worker.is_alive()
        ):

            result = (
                messagebox.askyesno(
                    "工作仍在執行",
                    (
                        "目前仍有工作正在執行。\n"
                        "確定要關閉程式嗎？"
                    )
                )
            )

            if not result:

                return

        self.save_current_settings()

        self.root.destroy()


# =========================================================
# Main
# =========================================================

def main():

    root = (
        TkinterDnD.Tk()
    )

    ConverterGUI(
        root
    )

    root.mainloop()


if __name__ == "__main__":

    main()