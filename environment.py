import importlib.util
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


def module_available(
    module_name
):

    try:

        return (
            importlib.util.find_spec(
                module_name
            )
            is not None
        )

    except (
        ImportError,
        AttributeError,
    ):

        return False


def command_available(
    command
):

    return (
        shutil.which(
            command
        )
        is not None
    )


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

            if (
                not item
                or item.lower().startswith(
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

    for display_name, module in (
        packages.items()
    ):

        available = module_available(
            module
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
                    else "PATH 中找不到 gswin64c"
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
                    else "PATH 中找不到 tesseract"
                ),
        }
    )

    # =====================================================
    # OCR language packs
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
                        else f"{code} 未安裝"
                    ),
            }
        )

    return report