import sys

from pathlib import Path


APP_NAME = "Local Document Converter"

APP_VERSION = "3.5.0"


# =========================================================
# Runtime mode
# =========================================================

FROZEN = bool(
    getattr(
        sys,
        "frozen",
        False
    )
)


# =========================================================
# Application base directory
# =========================================================

if FROZEN:

    BASE = Path(
        sys.executable
    ).resolve().parent

else:

    BASE = Path(
        __file__
    ).resolve().parent


# =========================================================
# Internal bundled resources
# =========================================================

if FROZEN and hasattr(
    sys,
    "_MEIPASS"
):

    RESOURCE_BASE = Path(
        sys._MEIPASS
    )

else:

    RESOURCE_BASE = BASE


# =========================================================
# Markdown
# =========================================================

MD_INPUT = (
    BASE
    / "MD_Input"
)

MD_OUTPUT = (
    BASE
    / "MD_Output"
)

MD_PROCESSED = (
    BASE
    / "MD_Processed"
)


# =========================================================
# Compression
# =========================================================

COMPRESS_LOW_INPUT = (
    BASE
    / "Compress_Low_Input"
)

COMPRESS_MEDIUM_INPUT = (
    BASE
    / "Compress_Medium_Input"
)

COMPRESS_HIGH_INPUT = (
    BASE
    / "Compress_High_Input"
)

COMPRESS_OUTPUT = (
    BASE
    / "Compress_Output"
)


# =========================================================
# Image -> PDF
# =========================================================

IMAGE_TO_PDF_INPUT = (
    BASE
    / "Image_to_PDF_Input"
)

IMAGE_TO_PDF_OUTPUT = (
    BASE
    / "Image_to_PDF_Output"
)


# =========================================================
# Merge
# =========================================================

MERGE_OUTPUT = (
    BASE
    / "Merge_Output"
)


# =========================================================
# Split
# =========================================================

SPLIT_OUTPUT = (
    BASE
    / "Split_Output"
)


# =========================================================
# OCR
# =========================================================

OCR_OUTPUT = (
    BASE
    / "OCR_Output"
)


# =========================================================
# Logs / Settings
# =========================================================

LOGS = (
    BASE
    / "Logs"
)

SETTINGS_FILE = (
    BASE
    / "settings.json"
)


# =========================================================
# External executables
# =========================================================

GHOSTSCRIPT = "gswin64c"

TESSERACT = "tesseract"


# =========================================================
# User folders
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

    LOGS,
]


for folder in FOLDERS:

    folder.mkdir(
        parents=True,
        exist_ok=True
    )