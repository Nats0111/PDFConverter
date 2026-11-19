from pathlib import Path


# =========================================================
# 基本路徑
# =========================================================

BASE = Path(__file__).resolve().parent


# =========================================================
# Markdown
# =========================================================

MD_INPUT = BASE / "MD_Input"
MD_OUTPUT = BASE / "MD_Output"
MD_PROCESSED = BASE / "MD_Processed"


# =========================================================
# PDF 壓縮
# =========================================================

COMPRESS_LOW_INPUT = BASE / "Compress_Low_Input"
COMPRESS_MEDIUM_INPUT = BASE / "Compress_Medium_Input"
COMPRESS_HIGH_INPUT = BASE / "Compress_High_Input"

COMPRESS_OUTPUT = BASE / "Compress_Output"


# =========================================================
# Image → PDF
# =========================================================

IMAGE_TO_PDF_INPUT = BASE / "Image_to_PDF_Input"
IMAGE_TO_PDF_OUTPUT = BASE / "Image_to_PDF_Output"


# =========================================================
# Logs
# =========================================================

LOGS = BASE / "Logs"


# =========================================================
# Ghostscript
# =========================================================

GHOSTSCRIPT = "gswin64c"


# =========================================================
# 自動建立資料夾
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

    LOGS,
]


for folder in FOLDERS:
    folder.mkdir(
        parents=True,
        exist_ok=True
    )