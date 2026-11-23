import sys
from pathlib import Path

APP_NAME = "Local Document Converter"

APP_VERSION = "4.0.0"


# =========================================================
# Runtime
# =========================================================

FROZEN = bool(getattr(sys, "frozen", False))


if FROZEN:
    BASE = Path(sys.executable).resolve().parent

else:
    BASE = Path(__file__).resolve().parent


if FROZEN and hasattr(sys, "_MEIPASS"):
    RESOURCE_BASE = Path(sys._MEIPASS)

else:
    RESOURCE_BASE = BASE


# =========================================================
# Markdown
# =========================================================

MD_INPUT = BASE / "MD_Input"

MD_OUTPUT = BASE / "MD_Output"

MD_PROCESSED = BASE / "MD_Processed"


# =========================================================
# Compression
# =========================================================

COMPRESS_LOW_INPUT = BASE / "Compress_Low_Input"

COMPRESS_MEDIUM_INPUT = BASE / "Compress_Medium_Input"

COMPRESS_HIGH_INPUT = BASE / "Compress_High_Input"

COMPRESS_OUTPUT = BASE / "Compress_Output"


# =========================================================
# Image -> PDF
# =========================================================

IMAGE_TO_PDF_INPUT = BASE / "Image_to_PDF_Input"

IMAGE_TO_PDF_OUTPUT = BASE / "Image_to_PDF_Output"


# =========================================================
# Merge
# =========================================================

MERGE_OUTPUT = BASE / "Merge_Output"


# =========================================================
# Split
# =========================================================

SPLIT_OUTPUT = BASE / "Split_Output"


# =========================================================
# OCR
# =========================================================

OCR_OUTPUT = BASE / "OCR_Output"


# =========================================================
# Scan Optimize
# =========================================================

SCAN_OUTPUT = BASE / "Scan_Output"


# =========================================================
# System
# =========================================================

LOGS = BASE / "Logs"

TEMP = BASE / "Temp"

SETTINGS_FILE = BASE / "settings.json"


# =========================================================
# External tools
# =========================================================

GHOSTSCRIPT = "gswin64c"

TESSERACT = "tesseract"


# =========================================================
# Large PDF
#
# 這是 V4 自訂的策略門檻，
# 不是 Ghostscript 官方限制。
# =========================================================

LARGE_PDF_SIZE = 500 * 1024 * 1024


# =========================================================
# Timeout
# =========================================================

GHOSTSCRIPT_TIMEOUT = 2 * 60 * 60


# =========================================================
# Disk safety
#
# 預留原始檔大小的 2 倍作為建議工作空間。
# 這是我們自己的安全策略。
# =========================================================

DISK_SPACE_MULTIPLIER = 2.0


# =========================================================
# Folders
# =========================================================

FOLDERS = [
    MD_INPUT,
    MD_OUTPUT,
    MD_PROCESSED,
    COMPRESS_LOW_INPUT,
    COMPRESS_MEDIUM_INPUT,
    COMPRESS_HIGH_INPUT,
    COMPRESS_OUTPUT,
    IMAGE_TO_PDF_INPUT,
    IMAGE_TO_PDF_OUTPUT,
    MERGE_OUTPUT,
    SPLIT_OUTPUT,
    OCR_OUTPUT,
    SCAN_OUTPUT,
    LOGS,
    TEMP,
]


for folder in FOLDERS:
    folder.mkdir(parents=True, exist_ok=True)
