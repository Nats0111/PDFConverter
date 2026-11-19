import shutil
import subprocess

from config import (
    GHOSTSCRIPT,
    TESSERACT,
)


REQUIRED_OCR_LANGUAGES = {

    "eng":
        "English",

    "chi_tra":
        "繁體中文",

    "ita":
        "Italiano",
}


# =========================================================
# Python module
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
# Executable
# =========================================================

def command_path(
    command
):

    return shutil.which(
        command
    )


# =========================================================
# Hidden Windows subprocess
# =========================================================

def hidden_subprocess_options():

    creation_flags = 0

    startup_info = None

    if hasattr(
        subprocess,
        "CREATE_NO_WINDOW"
    ):

        creation_flags = (
            subprocess.CREATE_NO_WINDOW
        )

        startup_info = (
            subprocess.STARTUPINFO()
        )

        startup_info.dwFlags |= (
            subprocess.STARTF_USESHOWWINDOW
        )

        startup_info.wShowWindow = (
            subprocess.SW_HIDE
        )

    return (
        creation_flags,
        startup_info,
    )


# =========================================================
# Tesseract languages
# =========================================================

def get_tesseract_languages():

    executable = (
        command_path(
            TESSERACT
        )
    )

    if not executable:

        return set()

    (
        creation_flags,
        startup_info,
    ) = hidden_subprocess_options()

    try:

        result = subprocess.run(

            [
                executable,
                "--list-langs",
            ],

            capture_output=True,

            text=True,

            encoding="utf-8",

            errors="replace",

            timeout=15,

            creationflags=(
                creation_flags
            ),

            startupinfo=(
                startup_info
            ),
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

            value = (
                line.strip()
            )

            if not value:

                continue

            if (
                value
                .lower()
                .startswith(
                    "list of available languages"
                )
            ):

                continue

            languages.add(
                value
            )

        return languages

    except Exception:

        return set()


# =========================================================
# Main environment check
# =========================================================

def check_environment():

    report = []

    # =====================================================
    # Python packages
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

    gs = (
        command_path(
            GHOSTSCRIPT
        )
    )

    report.append(
        {
            "name":
                "Ghostscript",

            "ok":
                bool(gs),

            "detail":
                (
                    gs
                    if gs
                    else "未偵測到"
                ),
        }
    )

    # =====================================================
    # Tesseract
    # =====================================================

    tess = (
        command_path(
            TESSERACT
        )
    )

    report.append(
        {
            "name":
                "Tesseract",

            "ok":
                bool(tess),

            "detail":
                (
                    tess
                    if tess
                    else "未偵測到"
                ),
        }
    )

    # =====================================================
    # OCR languages
    # =====================================================

    languages = (
        get_tesseract_languages()
    )

    for code, name in (
        REQUIRED_OCR_LANGUAGES.items()
    ):

        available = (
            code in languages
        )

        report.append(
            {
                "name":
                    f"OCR {name}",

                "ok":
                    available,

                "detail":
                    (
                        code
                        if available
                        else (
                            f"{code} 未安裝"
                        )
                    ),
            }
        )

    return report