import os
import queue
import threading
import time
import tkinter as tk
from datetime import datetime
from pathlib import Path
from tkinter import (
    filedialog,
    messagebox,
    ttk,
)

from tkinterdnd2 import (
    DND_FILES,
    TkinterDnD,
)

from config import (
    APP_NAME,
    APP_VERSION,
    COMPRESS_OUTPUT,
    IMAGE_TO_PDF_OUTPUT,
    LOGS,
    MD_OUTPUT,
    MERGE_OUTPUT,
    OCR_OUTPUT,
    SCAN_OUTPUT,
    SPLIT_OUTPUT,
    TEMP,
)
from environment import (
    check_environment,
    ensure_tools_in_path,
)
from processors.compress import (
    compress_pdf,
    validate_dpi,
)
from processors.image_to_pdf import (
    image_to_pdf,
)
from processors.markdown import (
    convert_to_markdown,
)
from processors.merge_pdf import (
    merge_pdfs,
)
from processors.ocr_pdf import (
    ocr_pdf,
)
from processors.scan_optimize import (
    optimize_scanned_pdf,
)
from processors.split_pdf import (
    split_every_page,
    split_selected_pages,
)
from settings import (
    load_settings,
    save_settings,
)
from utils import (
    JobCancelled,
    cleanup_temp_folder,
    format_size,
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

OCR_MODE_LABELS = {
    "skip": "跳過已有文字",
    "force": "強制重新 OCR",
    "redo": "重做文字層",
    "default": "嚴格模式",
}

OCR_LABEL_TO_MODE = {label: mode for mode, label in OCR_MODE_LABELS.items()}


class ConverterGUI:
    # =====================================================
    # Init
    # =====================================================

    def __init__(
        self,
        root,
    ):

        self.root = root

        self.root.title(f"{APP_NAME} V{APP_VERSION}")

        self.configure_window()
        # =================================================
        # Worker
        # =================================================

        self.event_queue = queue.Queue()

        self.worker = None

        self.cancel_event = threading.Event()

        self.is_closing = False

        self.env_check_running = False

        self.current_job_files = []

        # =================================================
        # File lists
        # =================================================

        self.batch_files = []

        self.merge_files = []

        self.job_rows = {}

        # =================================================
        # Settings
        # =================================================

        self.settings = load_settings()

        ensure_tools_in_path(self.settings)

        # =================================================
        # General variables
        # =================================================

        self.function_var = tk.StringVar(value="PDF 壓縮")

        self.status_var = tk.StringVar(value="等待操作")

        self.current_file_var = tk.StringVar(value="-")

        self.file_progress_text = tk.StringVar(value="0%")

        self.batch_progress_text = tk.StringVar(value="0 / 0")

        # =================================================
        # Compression
        # =================================================

        self.quality_var = tk.StringVar(
            value=self.settings.get("compression_quality", "medium")
        )

        self.custom_dpi_var = tk.StringVar(
            value=str(self.settings.get("custom_dpi", 200))
        )

        # =================================================
        # Merge
        # =================================================

        self.merge_output_name = tk.StringVar(value="merged.pdf")

        # =================================================
        # Split
        # =================================================

        self.split_mode = tk.StringVar(value="selected")

        self.split_pages = tk.StringVar(value="1-5")

        # =================================================
        # OCR
        # =================================================

        saved_languages = set(
            self.settings.get(
                "ocr_languages",
                [
                    "eng",
                    "chi_tra",
                ],
            )
        )

        self.ocr_eng = tk.BooleanVar(value=("eng" in saved_languages))

        self.ocr_chi_tra = tk.BooleanVar(value=("chi_tra" in saved_languages))

        self.ocr_ita = tk.BooleanVar(value=("ita" in saved_languages))

        self.ocr_rotate = tk.BooleanVar(
            value=bool(self.settings.get("ocr_rotate", True))
        )

        self.ocr_deskew = tk.BooleanVar(
            value=bool(self.settings.get("ocr_deskew", True))
        )

        self.ocr_sidecar = tk.BooleanVar(
            value=bool(self.settings.get("ocr_sidecar", False))
        )

        saved_ocr_mode = self.settings.get("ocr_mode", "skip")

        if saved_ocr_mode not in OCR_MODE_LABELS:
            saved_ocr_mode = "skip"

        self.ocr_mode_var = tk.StringVar(value=OCR_MODE_LABELS[saved_ocr_mode])

        # =================================================
        # Scan optimize
        # =================================================

        self.scan_optimize_level = tk.IntVar(
            value=int(self.settings.get("scan_optimize_level", 1))
        )

        # =================================================
        # Style
        # =================================================

        self.style = ttk.Style()

        try:
            self.style.theme_use("vista")

        except tk.TclError:
            pass

        self.style.configure("Title.TLabel", font=("Segoe UI", 18, "bold"))

        self.style.configure("Status.TLabel", font=("Segoe UI", 10, "bold"))

        # =================================================
        # Main
        # =================================================

        self.build_scrollable_root()

        self.build_ui()

        self.root.protocol("WM_DELETE_WINDOW", self.on_close)

        self.root.after(100, self.check_event_queue)

        self.root.after(250, self.startup_tasks)

    def configure_window(self):
        self.root.update_idletasks()

        screen_width = self.root.winfo_screenwidth()

        screen_height = self.root.winfo_screenheight()

        target_width = min(1100, int(screen_width * 0.88))
        target_height = min(900, int(screen_height * 0.80))
        target_width = max(700, target_width)

        target_height = max(520, target_height)

        self.root.minsize(700, 520)
        x = max(0, (screen_width - target_width) // 2)
        y = max(0, (screen_height - target_height) // 2)
        self.root.geometry((f"{target_width}x{target_height}+{x}+{y}"))

    # =====================================================
    # Scrollable Root
    # =====================================================

    def build_scrollable_root(self):

        # =================================================
        # Outer container
        # =================================================

        self.scroll_container = ttk.Frame(self.root)

        self.scroll_container.pack(fill="both", expand=True)

        # =================================================
        # Canvas
        # =================================================

        self.scroll_canvas = tk.Canvas(
            self.scroll_container, highlightthickness=0, borderwidth=0
        )

        self.scroll_canvas.pack(side="left", fill="both", expand=True)

        # =================================================
        # Scrollbar
        # =================================================

        self.main_scrollbar = ttk.Scrollbar(
            self.scroll_container, orient="vertical", command=(self.scroll_canvas.yview)
        )

        self.main_scrollbar.pack(side="right", fill="y")

        self.scroll_canvas.configure(yscrollcommand=(self.main_scrollbar.set))

        # =================================================
        # Main content frame
        # =================================================

        self.main = ttk.Frame(self.scroll_canvas, padding=16)

        self.main_window = self.scroll_canvas.create_window(
            (0, 0), window=self.main, anchor="nw"
        )

        # =================================================
        # Resize events
        # =================================================

        self.main.bind("<Configure>", self.on_main_configure)

        self.scroll_canvas.bind("<Configure>", self.on_canvas_configure)

        # =================================================
        # Mouse wheel
        # =================================================

        self.scroll_canvas.bind("<Enter>", self.enable_mousewheel)

        self.scroll_canvas.bind("<Leave>", self.disable_mousewheel)

    # =====================================================
    # Update scrollable area
    # =====================================================

    def on_main_configure(self, event=None):

        self.scroll_canvas.configure(scrollregion=(self.scroll_canvas.bbox("all")))

        self.root.after_idle(self.update_scrollbar_state)

    # =====================================================
    # Responsive content width
    # =====================================================

    def on_canvas_configure(self, event):

        self.scroll_canvas.itemconfigure(self.main_window, width=event.width)

        self.root.after_idle(self.update_scrollbar_state)

    # =====================================================
    # Auto Scrollbar
    #
    # Large screen:
    #   Everything fits -> hide scrollbar
    #
    # Small screen:
    #   Content overflow -> show scrollbar
    # =====================================================

    def update_scrollbar_state(self):

        try:
            self.root.update_idletasks()

            # Canvas visible height
            canvas_height = self.scroll_canvas.winfo_height()

            # Required content height
            content_height = self.main.winfo_reqheight()

            needs_scroll = content_height > canvas_height

            if needs_scroll:
                if not (self.main_scrollbar.winfo_ismapped()):
                    self.main_scrollbar.pack(side="right", fill="y")

            else:
                if self.main_scrollbar.winfo_ismapped():
                    self.main_scrollbar.pack_forget()

                # 回到最上面
                self.scroll_canvas.yview_moveto(0)

        except tk.TclError:
            pass

    # =====================================================
    # Mouse Wheel
    #
    # Only scroll when content exceeds visible area.
    # =====================================================

    def on_mousewheel(self, event):

        try:
            first, last = self.scroll_canvas.yview()

            # =============================================
            # Everything is already visible
            #
            # yview == (0.0, 1.0)
            # -> lock page
            # =============================================

            if first <= 0.0 and last >= 1.0:
                return

            # =============================================
            # Windows mouse wheel
            # =============================================

            delta = int(-1 * (event.delta / 120))

            if delta == 0:
                return

            self.scroll_canvas.yview_scroll(delta, "units")

        except tk.TclError:
            pass

    # =====================================================
    # Enable Mouse Wheel
    # =====================================================

    def enable_mousewheel(self, event=None):

        self.root.bind_all("<MouseWheel>", self.on_mousewheel)

    # =====================================================
    # Disable Mouse Wheel
    # =====================================================

    def disable_mousewheel(self, event=None):

        self.root.unbind_all("<MouseWheel>")

    # =====================================================
    # Main UI
    # =====================================================

    def build_ui(self):

        # =================================================
        # Header
        # =================================================

        header = ttk.Frame(self.main)

        header.pack(fill="x")

        ttk.Label(header, text=APP_NAME, style="Title.TLabel").pack(side="left")

        ttk.Label(header, text=(f"V{APP_VERSION}")).pack(side="right")

        ttk.Label(self.main, text=("PDF / OCR / Markdown / Batch Processing")).pack(
            anchor="w", pady=(0, 12)
        )

        # =================================================
        # Function
        # =================================================

        function_frame = ttk.LabelFrame(self.main, text="功能", padding=8)

        function_frame.pack(fill="x", pady=(0, 8))

        self.function_combo = ttk.Combobox(
            function_frame,
            textvariable=(self.function_var),
            state="readonly",
            values=[
                "PDF 壓縮",
                "Markdown",
                "Image → PDF",
                "PDF 合併",
                "PDF 拆分",
                "PDF OCR",
                "掃描文件最佳化",
            ],
        )

        self.function_combo.pack(fill="x")

        self.function_combo.bind("<<ComboboxSelected>>", self.on_function_changed)

        # =================================================
        # Options
        # =================================================

        self.options_container = ttk.Frame(self.main)

        self.options_container.pack(fill="x", pady=(0, 8))

        # =================================================
        # Job Queue
        # =================================================

        queue_frame = ttk.LabelFrame(self.main, text="工作佇列", padding=6)

        queue_frame.pack(fill="both", pady=(0, 8))

        tree_container = ttk.Frame(queue_frame)

        tree_container.pack(fill="both", expand=True)

        self.job_tree = ttk.Treeview(
            tree_container,
            columns=(
                "status",
                "progress",
                "result",
            ),
            show="tree headings",
            height=5,
        )

        self.job_tree.heading("#0", text="檔案")

        self.job_tree.heading("status", text="狀態")

        self.job_tree.heading("progress", text="進度")

        self.job_tree.heading("result", text="結果")

        self.job_tree.column("#0", width=430, minwidth=200)

        self.job_tree.column("status", width=90, anchor="center")

        self.job_tree.column("progress", width=80, anchor="center")

        self.job_tree.column("result", width=180, anchor="w")

        self.job_tree.pack(side="left", fill="both", expand=True)

        tree_scroll = ttk.Scrollbar(
            tree_container, orient="vertical", command=(self.job_tree.yview)
        )

        tree_scroll.pack(side="right", fill="y")

        self.job_tree.config(yscrollcommand=(tree_scroll.set))

        self.job_tree.drop_target_register(DND_FILES)

        self.job_tree.dnd_bind("<<Drop>>", self.on_tree_drop)

        # =================================================
        # Job Buttons
        # =================================================

        job_buttons = ttk.Frame(queue_frame)

        job_buttons.pack(fill="x", pady=(6, 0))

        self.add_button = ttk.Button(
            job_buttons, text="新增檔案", command=self.add_files
        )

        self.add_button.pack(side="left")

        self.remove_button = ttk.Button(
            job_buttons, text="移除選取", command=self.remove_selected
        )

        self.remove_button.pack(side="left", padx=5)

        self.clear_button = ttk.Button(
            job_buttons, text="清空", command=self.clear_files
        )

        self.clear_button.pack(side="left")

        self.move_down_button = ttk.Button(
            job_buttons, text="下移", command=lambda: self.move_selected(1)
        )

        self.move_down_button.pack(side="right")

        self.move_up_button = ttk.Button(
            job_buttons, text="上移", command=lambda: self.move_selected(-1)
        )

        self.move_up_button.pack(side="right", padx=(0, 5))

        # =================================================
        # Start / Cancel
        # =================================================

        action_frame = ttk.Frame(self.main)

        action_frame.pack(fill="x", pady=(0, 8))

        self.start_button = ttk.Button(
            action_frame, text="開始處理", command=self.start
        )

        self.start_button.pack(side="left", fill="x", expand=True, ipady=6)

        self.cancel_button = ttk.Button(
            action_frame,
            text="取消目前工作",
            command=(self.cancel_current_job),
            state="disabled",
        )

        self.cancel_button.pack(side="left", padx=(8, 0), ipadx=10, ipady=6)

        # =================================================
        # Progress
        # =================================================

        progress_frame = ttk.LabelFrame(self.main, text="處理進度", padding=8)

        progress_frame.pack(fill="x", pady=(0, 8))

        current_row = ttk.Frame(progress_frame)

        current_row.pack(fill="x")

        ttk.Label(current_row, text="目前：").pack(side="left")

        ttk.Label(current_row, textvariable=(self.current_file_var)).pack(side="left")

        # =================================================
        # File progress
        # =================================================

        file_row = ttk.Frame(progress_frame)

        file_row.pack(fill="x", pady=(7, 2))

        ttk.Label(file_row, text="目前檔案").pack(side="left")

        ttk.Label(file_row, textvariable=(self.file_progress_text)).pack(side="right")

        self.file_progress = ttk.Progressbar(
            progress_frame, maximum=100, mode="determinate"
        )

        self.file_progress.pack(fill="x")

        # =================================================
        # Batch progress
        # =================================================

        batch_row = ttk.Frame(progress_frame)

        batch_row.pack(fill="x", pady=(7, 2))

        ttk.Label(batch_row, text="整體工作").pack(side="left")

        ttk.Label(batch_row, textvariable=(self.batch_progress_text)).pack(side="right")

        self.batch_progress = ttk.Progressbar(
            progress_frame, maximum=100, mode="determinate"
        )

        self.batch_progress.pack(fill="x")

        ttk.Label(
            progress_frame, textvariable=(self.status_var), style="Status.TLabel"
        ).pack(anchor="w", pady=(7, 0))

        # =================================================
        # Console
        # =================================================

        console_frame = ttk.LabelFrame(self.main, text="執行過程", padding=6)

        console_frame.pack(fill="both", expand=True, pady=(0, 8))

        console_inner = ttk.Frame(console_frame)

        console_inner.pack(fill="both", expand=True)

        self.console = tk.Text(
            console_inner,
            height=6,
            wrap="word",
            bg="#101419",
            fg="#D7E0EA",
            font=("Consolas", 9),
            state="disabled",
            relief="flat",
            padx=8,
            pady=8,
        )

        self.console.pack(side="left", fill="both", expand=True)

        console_scroll = ttk.Scrollbar(
            console_inner, orient="vertical", command=(self.console.yview)
        )

        console_scroll.pack(side="right", fill="y")

        self.console.config(yscrollcommand=(console_scroll.set))

        self.console.tag_config("INFO", foreground="#D7E0EA")

        self.console.tag_config("SUCCESS", foreground="#55D187")

        self.console.tag_config("WARNING", foreground="#F3C969")

        self.console.tag_config("ERROR", foreground="#FF6B6B")

        self.console.tag_config("SYSTEM", foreground="#66B7FF")

        # =================================================
        # Bottom
        # =================================================

        bottom = ttk.Frame(self.main)

        bottom.pack(fill="x")

        ttk.Button(bottom, text="開啟輸出資料夾", command=self.open_output).pack(
            side="left"
        )

        ttk.Button(bottom, text="檢查環境", command=(self.run_environment_check)).pack(
            side="left", padx=5
        )

        ttk.Button(bottom, text="查看 Log", command=self.open_log).pack(side="left")

        ttk.Button(bottom, text="清除執行過程", command=self.clear_console).pack(
            side="right"
        )

        # =================================================
        # Initial
        # =================================================

        self.rebuild_options()

        self.refresh_job_tree()

        self.console_log((f"{APP_NAME} V{APP_VERSION} 已啟動"), "SYSTEM")

    # =====================================================
    # Startup
    # =====================================================

    def startup_tasks(self):

        try:
            removed = cleanup_temp_folder(TEMP)

            if removed:
                self.console_log((f"已清理上次殘留 Temp：{removed} 個項目"), "SYSTEM")

        except Exception as error:
            self.console_log((f"Temp 清理失敗：{error}"), "WARNING")

        self.run_environment_check()

    # =====================================================
    # Options
    # =====================================================

    def clear_options(self):

        for widget in self.options_container.winfo_children():
            widget.destroy()

    def rebuild_options(self):

        self.clear_options()

        function = self.function_var.get()

        if function == "PDF 壓縮":
            self.build_compression_options()

        elif function == "PDF 合併":
            self.build_merge_options()

        elif function == "PDF 拆分":
            self.build_split_options()

        elif function == "PDF OCR":
            self.build_ocr_options(scan_mode=False)

        elif function == "掃描文件最佳化":
            self.build_ocr_options(scan_mode=True)

    # =====================================================
    # Compression options
    # =====================================================

    def build_compression_options(self):

        frame = ttk.LabelFrame(self.options_container, text="壓縮設定", padding=8)

        frame.pack(fill="x")

        choices = [
            ("無損最佳化", "lossless"),
            ("強力 96 DPI", "low"),
            ("平衡 150 DPI", "medium"),
            ("高品質 300 DPI", "high"),
            ("自訂 DPI", "custom"),
        ]

        for text, value in choices:
            ttk.Radiobutton(
                frame,
                text=text,
                variable=(self.quality_var),
                value=value,
                command=(self.on_quality_change),
            ).pack(side="left", padx=(0, 16))

        self.custom_dpi_entry = ttk.Entry(
            frame, textvariable=(self.custom_dpi_var), width=7
        )

        self.custom_dpi_entry.pack(side="left")

        ttk.Label(frame, text="DPI").pack(side="left", padx=(4, 0))

        self.on_quality_change()

    def on_quality_change(self):

        if not hasattr(self, "custom_dpi_entry"):
            return

        if not (self.custom_dpi_entry.winfo_exists()):
            return

        state = "normal" if (self.quality_var.get() == "custom") else "disabled"

        self.custom_dpi_entry.config(state=state)

        self.save_current_settings()

    # =====================================================
    # Merge options
    # =====================================================

    def build_merge_options(self):

        frame = ttk.LabelFrame(self.options_container, text="PDF 合併設定", padding=8)

        frame.pack(fill="x")

        ttk.Label(frame, text="輸出檔名").pack(side="left")

        ttk.Entry(frame, textvariable=(self.merge_output_name)).pack(
            side="left", fill="x", expand=True, padx=(8, 0)
        )

        ttk.Label(frame, text=("佇列順序即合併順序")).pack(side="right", padx=(10, 0))

    # =====================================================
    # Split options
    # =====================================================

    def build_split_options(self):

        frame = ttk.LabelFrame(self.options_container, text="拆分設定", padding=8)

        frame.pack(fill="x")

        ttk.Radiobutton(
            frame,
            text="指定頁面",
            variable=(self.split_mode),
            value="selected",
            command=(self.update_split_ui),
        ).pack(side="left")

        ttk.Radiobutton(
            frame,
            text="每頁獨立 PDF",
            variable=(self.split_mode),
            value="every",
            command=(self.update_split_ui),
        ).pack(side="left", padx=15)

        ttk.Label(frame, text="頁碼").pack(side="left")

        self.split_pages_entry = ttk.Entry(
            frame, textvariable=(self.split_pages), width=25
        )

        self.split_pages_entry.pack(side="left", padx=(6, 0))

        ttk.Label(frame, text="例如 1-5,8,10-12").pack(side="left", padx=8)

        self.update_split_ui()

    def update_split_ui(self):

        if not hasattr(self, "split_pages_entry"):
            return

        if not (self.split_pages_entry.winfo_exists()):
            return

        self.split_pages_entry.config(
            state=("normal" if (self.split_mode.get() == "selected") else "disabled")
        )

    # =====================================================
    # OCR / Scan options
    # =====================================================

    def build_ocr_options(
        self,
        scan_mode=False,
    ):

        frame = ttk.LabelFrame(
            self.options_container,
            text=("掃描文件最佳化設定" if scan_mode else "OCR 設定"),
            padding=8,
        )

        frame.pack(fill="x")

        row_top = ttk.Frame(frame)

        row_top.pack(fill="x")

        ttk.Checkbutton(
            row_top,
            text="English",
            variable=self.ocr_eng,
            command=(self.save_current_settings),
        ).pack(side="left")

        ttk.Checkbutton(
            row_top,
            text="繁體中文",
            variable=(self.ocr_chi_tra),
            command=(self.save_current_settings),
        ).pack(side="left", padx=12)

        ttk.Checkbutton(
            row_top,
            text="Italiano",
            variable=self.ocr_ita,
            command=(self.save_current_settings),
        ).pack(side="left")

        ttk.Checkbutton(
            row_top,
            text="自動旋轉",
            variable=self.ocr_rotate,
            command=(self.save_current_settings),
        ).pack(side="left", padx=(20, 0))

        ttk.Checkbutton(
            row_top,
            text="歪斜校正",
            variable=self.ocr_deskew,
            command=(self.save_current_settings),
        ).pack(side="left", padx=10)

        row_bottom = ttk.Frame(frame)

        row_bottom.pack(fill="x", pady=(6, 0))

        ttk.Label(row_bottom, text="已有文字處理").pack(side="left")

        ocr_mode_combo = ttk.Combobox(
            row_bottom,
            textvariable=self.ocr_mode_var,
            values=list(OCR_MODE_LABELS.values()),
            state="readonly",
            width=15,
        )

        ocr_mode_combo.pack(side="left", padx=(6, 0))

        ocr_mode_combo.bind(
            "<<ComboboxSelected>>", lambda event: self.save_current_settings()
        )

        if scan_mode:
            ttk.Label(row_bottom, text="最佳化").pack(side="left", padx=(20, 3))

            optimize_combo = ttk.Combobox(
                row_bottom,
                textvariable=(self.scan_optimize_level),
                values=[
                    0,
                    1,
                    2,
                    3,
                ],
                state="readonly",
                width=4,
            )

            optimize_combo.pack(side="left")

            optimize_combo.bind(
                "<<ComboboxSelected>>", lambda event: self.save_current_settings()
            )

        else:
            ttk.Checkbutton(
                row_bottom,
                text="輸出 TXT",
                variable=(self.ocr_sidecar),
                command=(self.save_current_settings),
            ).pack(side="left", padx=(20, 0))

    # =====================================================
    # Switch function
    # =====================================================

    def on_function_changed(
        self,
        event=None,
    ):

        if self.is_running():
            return

        self.batch_files.clear()

        self.merge_files.clear()

        self.job_rows.clear()

        self.clear_tree()

        self.rebuild_options()

        self.reset_progress()

        self.status_var.set("等待操作")

    # =====================================================
    # File validation
    # =====================================================

    def file_allowed(self, path):

        function = self.function_var.get()

        suffix = path.suffix.lower()

        if function in (
            "PDF 壓縮",
            "PDF 合併",
            "PDF 拆分",
            "PDF OCR",
            "掃描文件最佳化",
        ):
            return suffix == ".pdf"

        if function == "Image → PDF":
            return suffix in SUPPORTED_IMAGES

        if function == "Markdown":
            return True

        return False

    # =====================================================
    # Add files
    # =====================================================

    def add_files(self):

        if self.is_running():
            return

        function = self.function_var.get()

        if function in (
            "PDF 壓縮",
            "PDF 合併",
            "PDF 拆分",
            "PDF OCR",
            "掃描文件最佳化",
        ):
            filetypes = [("PDF", "*.pdf")]

        elif function == "Image → PDF":
            filetypes = [
                (
                    "Images",
                    (
                        "*.jpg",
                        "*.jpeg",
                        "*.png",
                        "*.webp",
                        "*.bmp",
                        "*.tif",
                        "*.tiff",
                    ),
                )
            ]

        else:
            filetypes = [("All Files", "*.*")]

        files = filedialog.askopenfilenames(title="選擇檔案", filetypes=filetypes)

        self.add_paths(files)

    def on_tree_drop(self, event):

        if self.is_running():
            self.console_log("工作執行中，無法新增檔案", "WARNING")

            return

        paths = self.root.tk.splitlist(event.data)

        self.add_paths(paths)

    def add_paths(self, paths):

        if self.is_running():
            return

        function = self.function_var.get()

        target = self.merge_files if (function == "PDF 合併") else self.batch_files

        added = 0

        skipped = 0

        for item in paths:
            path = Path(item)

            if not path.is_file() or not self.file_allowed(path):
                skipped += 1

                continue

            value = str(path)

            if value in target:
                continue

            target.append(value)

            added += 1

        self.refresh_job_tree()

        if added:
            self.console_log((f"加入 {added} 個檔案"), "SYSTEM")

        if skipped:
            self.console_log((f"略過 {skipped} 個檔案"), "WARNING")

    # =====================================================
    # Treeview
    # =====================================================

    def clear_tree(self):

        for item in self.job_tree.get_children():
            self.job_tree.delete(item)

    def refresh_job_tree(self):

        self.clear_tree()

        self.job_rows.clear()

        function = self.function_var.get()

        files = self.merge_files if (function == "PDF 合併") else self.batch_files

        for index, file in enumerate(files, start=1):
            path = Path(file)

            display_name = (
                (f"{index}. {path.name}") if (function == "PDF 合併") else path.name
            )

            item = self.job_tree.insert(
                "",
                tk.END,
                text=display_name,
                values=(
                    "等待",
                    "0%",
                    "",
                ),
            )

            self.job_rows[file] = item

    def update_job(
        self,
        file,
        status=None,
        progress=None,
        result=None,
    ):

        item = self.job_rows.get(file)

        if not item:
            return

        if not self.job_tree.exists(item):
            return

        values = list(self.job_tree.item(item, "values"))

        while len(values) < 3:
            values.append("")

        if status is not None:
            values[0] = status

        if progress is not None:
            values[1] = progress

        if result is not None:
            values[2] = result

        self.job_tree.item(item, values=values)

    # =====================================================
    # Remove/Clear
    # =====================================================

    def remove_selected(self):

        if self.is_running():
            return

        selection = self.job_tree.selection()

        if not selection:
            return

        function = self.function_var.get()

        target = self.merge_files if (function == "PDF 合併") else self.batch_files

        item_to_file = {item: file for file, item in self.job_rows.items()}

        remove_files = []

        for item in selection:
            file = item_to_file.get(item)

            if file:
                remove_files.append(file)

        for file in remove_files:
            if file in target:
                target.remove(file)

        self.refresh_job_tree()

    def clear_files(self):

        if self.is_running():
            return

        self.batch_files.clear()

        self.merge_files.clear()

        self.job_rows.clear()

        self.clear_tree()

    def move_selected(self, direction):

        if self.is_running():
            return

        selection = self.job_tree.selection()

        if not selection:
            return

        function = self.function_var.get()

        target = self.merge_files if (function == "PDF 合併") else self.batch_files

        if len(target) < 2:
            return

        item_to_file = {item: file for file, item in self.job_rows.items()}

        selected_files = [
            item_to_file[item] for item in selection if item in item_to_file
        ]

        if not selected_files:
            return

        indices = sorted(
            target.index(file) for file in selected_files if file in target
        )

        if direction < 0:
            for idx in indices:
                if idx > 0 and (idx - 1) not in indices:
                    target[idx - 1], target[idx] = target[idx], target[idx - 1]
                    indices = [
                        (i - 1 if i == idx else i) for i in indices
                    ]

        elif direction > 0:
            for idx in reversed(indices):
                if idx < len(target) - 1 and (idx + 1) not in indices:
                    target[idx + 1], target[idx] = target[idx], target[idx + 1]
                    indices = [
                        (i + 1 if i == idx else i) for i in indices
                    ]

        self.refresh_job_tree()

        new_selection = [
            self.job_rows[file] for file in selected_files if file in self.job_rows
        ]

        if new_selection:
            self.job_tree.selection_set(new_selection)
            self.job_tree.see(new_selection[0])

    # =====================================================
    # Settings
    # =====================================================

    def get_ocr_mode(self):

        return OCR_LABEL_TO_MODE.get(self.ocr_mode_var.get(), "skip")

    def save_current_settings(self):

        languages = []

        if self.ocr_eng.get():
            languages.append("eng")

        if self.ocr_chi_tra.get():
            languages.append("chi_tra")

        if self.ocr_ita.get():
            languages.append("ita")

        try:
            custom_dpi = int(self.custom_dpi_var.get())

        except ValueError:
            custom_dpi = 200

        updated = {
            **self.settings,
            "compression_quality": self.quality_var.get(),
            "custom_dpi": custom_dpi,
            "ocr_languages": languages,
            "ocr_mode": self.get_ocr_mode(),
            "ocr_rotate": bool(self.ocr_rotate.get()),
            "ocr_deskew": bool(self.ocr_deskew.get()),
            "ocr_sidecar": bool(self.ocr_sidecar.get()),
            "scan_optimize_level": int(self.scan_optimize_level.get()),
        }

        self.settings = updated

        save_settings(updated)

    # =====================================================
    # Environment
    # =====================================================

    def run_environment_check(self):

        if self.env_check_running:
            return

        self.env_check_running = True

        self.console_log("開始檢查執行環境", "SYSTEM")

        settings_snapshot = dict(self.settings)

        def _worker():
            try:
                report = check_environment(settings_snapshot)
                self.event_queue.put(("env_check_done", report))

            except Exception as error:
                self.event_queue.put(("env_check_error", str(error)))

        threading.Thread(target=_worker, daemon=True).start()

    def handle_env_check_done(self, report):

        self.env_check_running = False

        for item in report:
            self.console_log(
                (
                    ("✓ " if item["ok"] else "✗ ")
                    + item["name"]
                    + " ("
                    + str(item["detail"])
                    + ")"
                ),
                ("SUCCESS" if item["ok"] else "WARNING"),
            )

    def handle_env_check_error(self, error_message):

        self.env_check_running = False

        self.console_log((f"環境檢查失敗：{error_message}"), "ERROR")

    # =====================================================
    # Job options
    # =====================================================

    def get_languages(self):

        languages = []

        if self.ocr_eng.get():
            languages.append("eng")

        if self.ocr_chi_tra.get():
            languages.append("chi_tra")

        if self.ocr_ita.get():
            languages.append("ita")

        if not languages:
            raise ValueError("請至少選擇一種 OCR 語言。")

        return languages

    def build_options(self):

        function = self.function_var.get()

        options = {"function": function}

        if function == "PDF 壓縮":
            options["quality"] = self.quality_var.get()

            if options["quality"] == "custom":
                options["custom_dpi"] = validate_dpi(self.custom_dpi_var.get())

            else:
                try:
                    options["custom_dpi"] = int(self.custom_dpi_var.get())

                except ValueError:
                    options["custom_dpi"] = 200

        elif function in (
            "PDF OCR",
            "掃描文件最佳化",
        ):
            options["languages"] = self.get_languages()

            options["ocr_mode"] = self.get_ocr_mode()

            options["rotate"] = bool(self.ocr_rotate.get())

            options["deskew"] = bool(self.ocr_deskew.get())

            if function == "PDF OCR":
                options["sidecar"] = bool(self.ocr_sidecar.get())

            else:
                options["optimize_level"] = int(self.scan_optimize_level.get())

        elif function == "PDF 拆分":
            options["split_mode"] = self.split_mode.get()

            options["pages"] = self.split_pages.get().strip()

            if options["split_mode"] == "selected" and not options["pages"]:
                raise ValueError("請輸入頁碼。")

        elif function == "PDF 合併":
            options["output_name"] = (
                self.merge_output_name.get().strip() or "merged.pdf"
            )

        return options

    # =====================================================
    # Run
    # =====================================================

    def is_running(self):

        return bool(self.worker and self.worker.is_alive())

    def start(self):

        if self.is_running():
            return

        function = self.function_var.get()

        files = (
            self.merge_files.copy()
            if (function == "PDF 合併")
            else self.batch_files.copy()
        )

        if not files:
            messagebox.showerror("無法開始", "請至少加入一個檔案。")

            return

        if function == "PDF 合併" and len(files) < 2:
            messagebox.showerror("無法開始", "PDF 合併至少需要兩個 PDF。")

            return

        try:
            options = self.build_options()

        except Exception as error:
            messagebox.showerror("設定錯誤", str(error))

            return

        self.save_current_settings()

        self.cancel_event.clear()

        self.reset_progress()

        self.refresh_job_tree()

        self.function_combo.config(state="disabled")

        self.start_button.config(state="disabled")

        self.cancel_button.config(state="normal")

        self.add_button.config(state="disabled")

        self.remove_button.config(state="disabled")

        self.clear_button.config(state="disabled")

        self.move_up_button.config(state="disabled")

        self.move_down_button.config(state="disabled")

        self.status_var.set("處理中...")

        # Merge counts as one output job.

        total_jobs = 1 if (function == "PDF 合併") else len(files)

        self.batch_progress_text.set(f"0 / {total_jobs}")

        self.console_log("────────────────────────────", "SYSTEM")

        self.console_log((f"開始工作：{function}"), "SYSTEM")

        self.worker = threading.Thread(
            target=self.run_batch,
            args=(
                files,
                options,
            ),
            daemon=True,
        )

        self.worker.start()

    # =====================================================
    # Worker
    # =====================================================

    def run_batch(
        self,
        files,
        options,
    ):

        function = options["function"]

        success_files = []

        failed_files = []

        cancelled_files = []

        # =================================================
        # Merge special handling
        # =================================================

        if function == "PDF 合併":
            try:
                self.event_queue.put(
                    (
                        "file_start",
                        {
                            "file": files[0],
                            "files": files,
                            "name": "PDF 合併",
                            "index": 1,
                            "total": 1,
                        },
                    )
                )

                result = merge_pdfs(
                    files,
                    options["output_name"],
                    progress_callback=(self.processor_callback),
                    cancel_event=(self.cancel_event),
                )

                success_files = [files[0]]

                self.event_queue.put(
                    (
                        "file_success",
                        {
                            "file": files[0],
                            "files": files,
                            "index": 1,
                            "total": 1,
                            "result": result,
                        },
                    )
                )

            except JobCancelled:
                cancelled_files = [files[0]]

                self.event_queue.put(
                    (
                        "file_cancelled",
                        {
                            "file": files[0],
                            "files": files,
                            "index": 1,
                            "total": 1,
                        },
                    )
                )

            except Exception as error:
                failed_files = [files[0]]

                self.event_queue.put(
                    (
                        "file_error",
                        {
                            "file": files[0],
                            "files": files,
                            "index": 1,
                            "total": 1,
                            "error": str(error),
                        },
                    )
                )

            self.event_queue.put(
                (
                    "batch_done",
                    {
                        "success_files": success_files,
                        "failed_files": failed_files,
                        "cancelled_files": cancelled_files,
                        "total": 1,
                        "is_merge": True,
                    },
                )
            )

            return

        # =================================================
        # Normal jobs
        # =================================================

        total = len(files)

        for index, file in enumerate(files, start=1):
            if self.cancel_event.is_set():
                cancelled_files.extend(files[index - 1 :])

                break

            source = Path(file)

            self.event_queue.put(
                (
                    "file_start",
                    {
                        "file": file,
                        "name": source.name,
                        "index": index,
                        "total": total,
                    },
                )
            )

            try:
                result = None

                # =========================================
                # Compression
                # =========================================

                if function == "PDF 壓縮":
                    result = compress_pdf(
                        source,
                        quality=(options["quality"]),
                        custom_dpi=(options["custom_dpi"]),
                        delete_source=False,
                        progress_callback=(self.processor_callback),
                        cancel_event=(self.cancel_event),
                    )

                    if result and result.get("cancelled"):
                        raise JobCancelled("使用者取消壓縮。")

                # =========================================
                # Markdown
                # =========================================

                elif function == "Markdown":
                    result = convert_to_markdown(
                        source,
                        move_source=False,
                        progress_callback=(self.processor_callback),
                        cancel_event=(self.cancel_event),
                    )

                # =========================================
                # Image -> PDF
                # =========================================

                elif function == "Image → PDF":
                    result = image_to_pdf(
                        source,
                        delete_source=False,
                        progress_callback=(self.processor_callback),
                        cancel_event=(self.cancel_event),
                    )

                # =========================================
                # Split
                # =========================================

                elif function == "PDF 拆分":
                    if options["split_mode"] == "every":
                        result = split_every_page(
                            source,
                            progress_callback=(self.processor_callback),
                            cancel_event=(self.cancel_event),
                        )

                    else:
                        result = split_selected_pages(
                            source,
                            options["pages"],
                            progress_callback=(self.processor_callback),
                            cancel_event=(self.cancel_event),
                        )

                # =========================================
                # OCR
                # =========================================

                elif function == "PDF OCR":
                    result = ocr_pdf(
                        source,
                        languages=(options["languages"]),
                        rotate_pages=(options["rotate"]),
                        deskew=(options["deskew"]),
                        create_sidecar=(options["sidecar"]),
                        ocr_mode=(options["ocr_mode"]),
                        progress_callback=(self.processor_callback),
                        cancel_event=(self.cancel_event),
                    )

                # =========================================
                # Scan Optimize
                # =========================================

                elif function == "掃描文件最佳化":
                    result = optimize_scanned_pdf(
                        source,
                        languages=(options["languages"]),
                        rotate_pages=(options["rotate"]),
                        deskew=(options["deskew"]),
                        optimize_level=(options["optimize_level"]),
                        ocr_mode=(options["ocr_mode"]),
                        progress_callback=(self.processor_callback),
                        cancel_event=(self.cancel_event),
                    )

                else:
                    raise RuntimeError((f"未知功能：{function}"))

                success_files.append(file)

                self.event_queue.put(
                    (
                        "file_success",
                        {
                            "file": file,
                            "index": index,
                            "total": total,
                            "result": result,
                        },
                    )
                )

            except JobCancelled:
                cancelled_files.append(file)

                self.event_queue.put(
                    (
                        "file_cancelled",
                        {
                            "file": file,
                            "index": index,
                            "total": total,
                        },
                    )
                )

                remaining = files[index:]

                cancelled_files.extend(remaining)

                break

            except Exception as error:
                failed_files.append(file)

                self.event_queue.put(
                    (
                        "file_error",
                        {
                            "file": file,
                            "index": index,
                            "total": total,
                            "error": str(error),
                        },
                    )
                )

        self.event_queue.put(
            (
                "batch_done",
                {
                    "success_files": success_files,
                    "failed_files": failed_files,
                    "cancelled_files": cancelled_files,
                    "total": total,
                    "is_merge": False,
                },
            )
        )

    # =====================================================
    # Processor callback
    # =====================================================

    def processor_callback(
        self,
        message,
        level="INFO",
        progress=None,
    ):

        self.event_queue.put(
            (
                "processor_progress",
                {
                    "message": message,
                    "level": level,
                    "progress": progress,
                },
            )
        )

    # =====================================================
    # Cancel
    # =====================================================

    def cancel_current_job(self):

        if not self.is_running():
            return

        self.cancel_event.set()

        self.cancel_button.config(state="disabled")

        self.status_var.set("正在取消...")

        self.console_log(("取消要求已送出，正在停止目前工作..."), "WARNING")

    # =====================================================
    # Queue processing
    # =====================================================

    def check_event_queue(self):

        try:
            while True:
                event, data = self.event_queue.get_nowait()

                if event == "file_start":
                    self.handle_file_start(data)

                elif event == "processor_progress":
                    self.handle_progress(data)

                elif event == "file_success":
                    self.handle_success(data)

                elif event == "file_error":
                    self.handle_error(data)

                elif event == "file_cancelled":
                    self.handle_cancelled(data)

                elif event == "batch_done":
                    self.finish_batch(data)

                elif event == "env_check_done":
                    self.handle_env_check_done(data)

                elif event == "env_check_error":
                    self.handle_env_check_error(data)

        except queue.Empty:
            pass

        self.root.after(100, self.check_event_queue)

    # =====================================================
    # Event handlers
    # =====================================================

    def handle_file_start(self, data):

        self.current_file_var.set(data["name"])

        target_files = data.get("files") or [data["file"]]

        self.current_job_files = list(target_files)

        self.file_progress.stop()

        self.file_progress.config(mode="indeterminate")

        self.file_progress.start(10)

        self.file_progress_text.set("處理中")

        for file in target_files:
            self.update_job(file, status="處理中", progress="...")

        self.console_log(
            (f"[{data['index']}/{data['total']}] {data['name']}"), "SYSTEM"
        )

    def handle_progress(self, data):

        self.console_log(data["message"], data["level"])

        progress = data["progress"]

        if progress is None:
            if str(self.file_progress["mode"]) != "indeterminate":
                self.file_progress.stop()

                self.file_progress.config(mode="indeterminate")

                self.file_progress.start(10)

            self.file_progress_text.set("處理中")

            return

        self.file_progress.stop()

        self.file_progress.config(mode="determinate")

        value = max(0.0, min(100.0, float(progress)))

        self.file_progress["value"] = value

        text = f"{value:.0f}%"

        self.file_progress_text.set(text)

        for file in self.current_job_files:
            self.update_job(file, status="處理中", progress=text)

    def result_to_text(self, result):

        if isinstance(result, dict):
            if result.get("compressed") is False and not result.get("cancelled"):
                return "未變小（無輸出）"

            if result.get("compressed"):
                reduction = result.get("reduction")

                output_size = result.get("output_size")

                if reduction is not None and output_size is not None:
                    return f"-{reduction:.1f}% | {format_size(output_size)}"

            if result.get("pdf"):
                return Path(result["pdf"]).name

        if isinstance(result, Path):
            return result.name

        return "完成"

    def handle_success(self, data):

        self.file_progress.stop()

        self.file_progress.config(mode="determinate")

        self.file_progress["value"] = 100

        self.file_progress_text.set("100%")

        result = data["result"]

        result_text = self.result_to_text(result)

        is_uncompressed_skip = (
            isinstance(result, dict)
            and result.get("compressed") is False
            and not result.get("cancelled")
        )

        row_status = "已略過" if is_uncompressed_skip else "完成"

        target_files = data.get("files") or [data["file"]]

        for file in target_files:
            self.update_job(
                file, status=row_status, progress="100%", result=result_text
            )

        overall = data["index"] / data["total"] * 100

        self.batch_progress["value"] = overall

        self.batch_progress_text.set((f"{data['index']} / {data['total']}"))

        if is_uncompressed_skip:
            self.console_log("⚠ 輸出未比原檔小，已捨棄（未建立新檔）", "WARNING")

        else:
            self.console_log("✓ 處理完成", "SUCCESS")

    def handle_error(self, data):

        self.file_progress.stop()

        self.file_progress.config(mode="determinate")

        self.file_progress_text.set("失敗")

        target_files = data.get("files") or [data["file"]]

        for file in target_files:
            self.update_job(
                file, status="失敗", progress="-", result=(data["error"][:80])
            )

        overall = data["index"] / data["total"] * 100

        self.batch_progress["value"] = overall

        self.batch_progress_text.set((f"{data['index']} / {data['total']}"))

        self.console_log((f"✗ {data['error']}"), "ERROR")

    def handle_cancelled(self, data):

        self.file_progress.stop()

        self.file_progress.config(mode="determinate")

        self.file_progress_text.set("已取消")

        target_files = data.get("files") or [data["file"]]

        for file in target_files:
            self.update_job(file, status="已取消", progress="-", result="")

        self.console_log("目前工作已取消", "WARNING")

    # =====================================================
    # Finish
    # =====================================================

    def finish_batch(self, data):

        self.file_progress.stop()

        self.current_job_files = []

        self.function_combo.config(state="readonly")

        self.start_button.config(state="normal")

        self.cancel_button.config(state="disabled")

        self.add_button.config(state="normal")

        self.remove_button.config(state="normal")

        self.clear_button.config(state="normal")

        self.move_up_button.config(state="normal")

        self.move_down_button.config(state="normal")

        self.current_file_var.set("-")

        success_files = data["success_files"]

        failed_files = data["failed_files"]

        cancelled_files = data["cancelled_files"]

        is_merge = bool(data.get("is_merge"))

        for file in cancelled_files:
            item = self.job_rows.get(file)

            if item and self.job_tree.exists(item):
                values = self.job_tree.item(item, "values")

                if values and values[0] == "等待":
                    self.update_job(file, status="已取消", progress="-", result="")

        success_count = len(success_files)

        failed_count = len(failed_files)

        cancelled_count = len(set(cancelled_files))

        # =================================================
        # Keep failed/cancelled jobs
        # Remove successful jobs
        # =================================================

        if is_merge:
            if success_count:
                self.merge_files.clear()

        else:
            success_set = set(success_files)

            self.batch_files = [
                file for file in self.batch_files if file not in success_set
            ]

        # Do NOT refresh Treeview here.
        # Keep final result rows visible until user
        # starts a new run / manually clears them.

        if cancelled_count:
            self.status_var.set(
                (f"已取消 | 成功 {success_count} | 失敗 {failed_count}")
            )

        else:
            self.status_var.set((f"完成：{success_count} 成功，{failed_count} 失敗"))

        self.console_log(
            (
                "工作結束 | "
                f"成功 {success_count} | "
                f"失敗 {failed_count} | "
                f"取消 {cancelled_count}"
            ),
            ("SUCCESS" if (failed_count == 0 and cancelled_count == 0) else "WARNING"),
        )

        self.cancel_event.clear()

    # =====================================================
    # Reset
    # =====================================================

    def reset_progress(self):

        self.file_progress.stop()

        self.file_progress.config(mode="determinate")

        self.file_progress["value"] = 0

        self.batch_progress["value"] = 0

        self.file_progress_text.set("0%")

        self.batch_progress_text.set("0 / 0")

        self.current_file_var.set("-")

    # =====================================================
    # Console
    # =====================================================

    def console_log(self, message, level="INFO"):

        timestamp = datetime.now().strftime("%H:%M:%S")

        self.console.config(state="normal")

        self.console.insert(tk.END, f"[{timestamp}] ", "SYSTEM")

        self.console.insert(tk.END, f"{message}\n", level)

        self.console.see(tk.END)

        self.console.config(state="disabled")

    def clear_console(self):

        self.console.config(state="normal")

        self.console.delete("1.0", tk.END)

        self.console.config(state="disabled")

    # =====================================================
    # Output
    # =====================================================

    def open_output(self):

        folders = {
            "PDF 壓縮": COMPRESS_OUTPUT,
            "Markdown": MD_OUTPUT,
            "Image → PDF": IMAGE_TO_PDF_OUTPUT,
            "PDF 合併": MERGE_OUTPUT,
            "PDF 拆分": SPLIT_OUTPUT,
            "PDF OCR": OCR_OUTPUT,
            "掃描文件最佳化": SCAN_OUTPUT,
        }

        folder = folders.get(self.function_var.get())

        if folder:
            try:
                os.startfile(str(folder))

            except Exception as error:
                messagebox.showerror("錯誤", str(error))

    def open_log(self):

        log_file = LOGS / "converter.log"

        if not (log_file.exists()):
            messagebox.showinfo("Log", "目前沒有 Log。")

            return

        try:
            os.startfile(str(log_file))

        except Exception as error:
            messagebox.showerror("錯誤", str(error))

    # =====================================================
    # Close
    # =====================================================

    def on_close(self):

        if self.is_closing:
            return

        if self.is_running():
            answer = messagebox.askyesno(
                "工作執行中", ("目前仍有工作正在執行。\n要取消工作並關閉程式嗎？")
            )

            if not answer:
                return

            self.is_closing = True

            self.cancel_event.set()

            self.cancel_button.config(state="disabled")

            self.status_var.set("正在停止背景工作並關閉...")

            self.console_log(("正在取消工作，請稍候..."), "WARNING")

            deadline = time.monotonic() + 5.0

            self.root.after(100, lambda: self._wait_for_worker_and_close(deadline))

            return

        self.force_close()

    def _wait_for_worker_and_close(self, deadline):

        if not self.is_running() or time.monotonic() >= deadline:
            self.force_close()

            return

        self.root.after(100, lambda: self._wait_for_worker_and_close(deadline))

    def force_close(self):

        self.save_current_settings()

        self.root.destroy()


# =========================================================
# Main
# =========================================================


def main():

    root = TkinterDnD.Tk()

    ConverterGUI(root)

    root.mainloop()


if __name__ == "__main__":
    main()
