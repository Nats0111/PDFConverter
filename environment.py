import shutil
import subprocess

from config import (
    GHOSTSCRIPT,
    TESSERACT,
)


REQUIRED_OCR_LANGUAGES = {
    "eng": "English",
    "chi_tra": "繁體中文",
    "ita": "Italiano",
}


# =========================================================
# Python module check
# =========================================================

def module_available(
    module_name
):

    try:

        __import__(
            module_name
        )

        return True

    except Exception:

        return False


# =========================================================
# External command check
# =========================================================

def command_available(
    command
):

    return (
        shutil.which(
            command
        )
        is not None
    )


# =========================================================
# Tesseract languages
# =========================================================

def get_tesseract_languages():

    if not command_available(
        TESSERACT
    ):

        return set()

    try:

        result = subprocess.run(
            [
                TESSERACT,
                "--list-langs",
            ],

            capture_output=True,

            text=True,

            encoding="utf-8",

            errors="replace",

            timeout=15,
        )

        output = (
            result.stdout
            + "\n"
            + result.stderr
        )

        languages = set()

        for line in (
            output.splitlines()
        ):

            item = line.strip()

            if not item:

                continue

            if (
                item
                .lower()
                .startswith(
                    "list of available languages"
                )
            ):

                continue

            languages.add(
                item
            )

        return languages

    except (
        OSError,
        subprocess.SubprocessError,
    ):

        return set()


# =========================================================
# Environment report
# =========================================================

def check_environment():

    report = []

    # =====================================================
    # Python Packages
    # =====================================================

    packages = {

        "Pillow":
            "PIL",

        "pypdf":
            "pypdf",

        "MarkItDown":
            "markitdown",

        "OCRmyPDF":
            "ocrmypdf",

        "tkinterdnd2":
            "tkinterdnd2",
    }

    for display_name, module_name in (
        packages.items()
    ):

        available = (
            module_available(
                module_name
            )
        )

        report.append(
            {
                "name":
                    display_name,

                "ok":
                    available,

                "detail":
                    (
                        "可用"
                        if available
                        else "未偵測到"
                    ),
            }
        )

    # =====================================================
    # Ghostscript
    # =====================================================

    ghostscript_ok = (
        command_available(
            GHOSTSCRIPT
        )
    )

    report.append(
        {
            "name":
                "Ghostscript",

            "ok":
                ghostscript_ok,

            "detail":
                (
                    "可用"
                    if ghostscript_ok
                    else (
                        "PATH 中找不到 "
                        f"{GHOSTSCRIPT}"
                    )
                ),
        }
    )

    # =====================================================
    # Tesseract
    # =====================================================

    tesseract_ok = (
        command_available(
            TESSERACT
        )
    )

    report.append(
        {
            "name":
                "Tesseract",

            "ok":
                tesseract_ok,

            "detail":
                (
                    "可用"
                    if tesseract_ok
                    else (
                        "PATH 中找不到 "
                        f"{TESSERACT}"
                    )
                ),
        }
    )

    # =====================================================
    # OCR Languages
    # =====================================================

    languages = (
        get_tesseract_languages()
    )

    for code, name in (
        REQUIRED_OCR_LANGUAGES
        .items()
    ):

        available = (
            code in languages
        )

        report.append(
            {
                "name":
                    (
                        f"OCR {name}"
                    ),

                "ok":
                    available,

                "detail":
                    (
                        code
                        if available
                        else (
                            f"{code} "
                            "未安裝"
                        )
                    ),
            }
        )

    return report