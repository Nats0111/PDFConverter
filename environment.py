import importlib.util
import os
import re
import shutil
import subprocess
from pathlib import Path

from config import (
    BASE,
    GHOSTSCRIPT,
    TESSERACT,
)
from utils import hidden_process_options

REQUIRED_OCR_LANGUAGES = {
    "eng": "English",
    "chi_tra": "繁體中文",
    "ita": "Italiano",
}

_CONFIGURED_TOOLS = {
    "ghostscript": None,
    "tesseract": None,
}


# =========================================================
# Python module (non-importing check)
# =========================================================


def module_available(module_name):
    try:
        return importlib.util.find_spec(module_name) is not None

    except Exception:
        return False


# =========================================================
# Executable resolution (PATH + portable tools + Windows defaults)
# =========================================================


def _version_sort_key(path):
    numbers = [int(part) for part in re.findall(r"\d+", path.parent.parent.name)]
    return tuple(numbers)


def _valid_executable(candidate):
    if not candidate:
        return None

    path = Path(str(candidate).strip().strip('"'))

    if path.is_file():
        return str(path.resolve())

    return None


def _prepend_to_path(executable_path):
    if not executable_path:
        return

    tool_dir = str(Path(executable_path).resolve().parent)
    current_path = os.environ.get("PATH", "")
    parts = [p for p in current_path.split(os.pathsep) if p]
    normalized_parts = {os.path.normcase(os.path.normpath(p)) for p in parts}
    normalized_dir = os.path.normcase(os.path.normpath(tool_dir))

    if normalized_dir not in normalized_parts:
        os.environ["PATH"] = (
            f"{tool_dir}{os.pathsep}{current_path}" if current_path else tool_dir
        )


def resolve_ghostscript(custom_path=None):
    # 1. User-configured path in settings.json
    found = _valid_executable(custom_path or _CONFIGURED_TOOLS["ghostscript"])
    if found:
        return found

    # 2. Portable tools/ folder next to application
    portable_candidates = [
        BASE / "tools" / "ghostscript" / "bin" / "gswin64c.exe",
        BASE / "tools" / "gs" / "bin" / "gswin64c.exe",
        BASE / "tools" / "gswin64c.exe",
    ]
    for candidate in portable_candidates:
        found = _valid_executable(candidate)
        if found:
            return found

    # 3. System PATH
    for command in (GHOSTSCRIPT, "gswin32c", "gs"):
        found = shutil.which(command)
        if found:
            return found

    # 4. Windows common installation folders (newest version first)
    program_dirs = [
        os.environ.get("ProgramFiles", r"C:\Program Files"),
        os.environ.get("ProgramFiles(x86)", r"C:\Program Files (x86)"),
    ]
    gs_matches = []
    for root in program_dirs:
        if not root:
            continue
        gs_base = Path(root) / "gs"
        if not gs_base.is_dir():
            continue
        for exe_name in ("gswin64c.exe", "gswin32c.exe"):
            gs_matches.extend(gs_base.glob(f"gs*/bin/{exe_name}"))

    if gs_matches:
        gs_matches.sort(key=_version_sort_key, reverse=True)
        for match in gs_matches:
            found = _valid_executable(match)
            if found:
                return found

    return None


def resolve_tesseract(custom_path=None):
    # 1. User-configured path in settings.json
    found = _valid_executable(custom_path or _CONFIGURED_TOOLS["tesseract"])
    if found:
        return found

    # 2. Portable tools/ folder next to application
    portable_candidates = [
        BASE / "tools" / "Tesseract-OCR" / "tesseract.exe",
        BASE / "tools" / "tesseract" / "tesseract.exe",
        BASE / "tools" / "tesseract.exe",
    ]
    for candidate in portable_candidates:
        found = _valid_executable(candidate)
        if found:
            return found

    # 3. System PATH
    found = shutil.which(TESSERACT)
    if found:
        return found

    # 4. Windows common installation folders
    default_candidates = [
        Path(os.environ.get("ProgramFiles", r"C:\Program Files"))
        / "Tesseract-OCR"
        / "tesseract.exe",
        Path(os.environ.get("ProgramFiles(x86)", r"C:\Program Files (x86)"))
        / "Tesseract-OCR"
        / "tesseract.exe",
    ]
    local_app_data = os.environ.get("LOCALAPPDATA")
    if local_app_data:
        default_candidates.append(
            Path(local_app_data) / "Programs" / "Tesseract-OCR" / "tesseract.exe"
        )

    for candidate in default_candidates:
        found = _valid_executable(candidate)
        if found:
            return found

    return None


def ensure_tools_in_path(settings=None):
    settings = settings or {}
    custom_gs = _valid_executable(settings.get("ghostscript_path"))
    custom_tess = _valid_executable(settings.get("tesseract_path"))
    if custom_gs:
        _CONFIGURED_TOOLS["ghostscript"] = custom_gs
    if custom_tess:
        _CONFIGURED_TOOLS["tesseract"] = custom_tess

    gs_path = resolve_ghostscript(custom_gs)
    tess_path = resolve_tesseract(custom_tess)

    _prepend_to_path(gs_path)
    _prepend_to_path(tess_path)

    return {
        "ghostscript": gs_path,
        "tesseract": tess_path,
    }


def command_path(command):
    if command == GHOSTSCRIPT:
        return resolve_ghostscript()
    if command == TESSERACT:
        return resolve_tesseract()
    return shutil.which(command)


# =========================================================
# Tesseract languages
# =========================================================


def get_tesseract_languages(executable=None):
    executable = executable or resolve_tesseract()

    if not executable:
        return set()

    options = hidden_process_options()

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
            creationflags=options["creationflags"],
            startupinfo=options["startupinfo"],
        )

        output = result.stdout + "\n" + result.stderr

        languages = set()

        for line in output.splitlines():
            value = line.strip()

            if not value:
                continue

            if value.lower().startswith("list of available languages"):
                continue

            languages.add(value)

        return languages

    except Exception:
        return set()


# =========================================================
# Main environment check
# =========================================================


def check_environment(settings=None):
    report = []

    tools = ensure_tools_in_path(settings)

    # =====================================================
    # Python packages
    # =====================================================

    packages = {
        "Pillow": "PIL",
        "pypdf": "pypdf",
        "MarkItDown": "markitdown",
        "OCRmyPDF": "ocrmypdf",
        "tkinterdnd2": "tkinterdnd2",
        "watchdog": "watchdog",
    }

    for display_name, module_name in packages.items():
        available = module_available(module_name)

        report.append(
            {
                "name": display_name,
                "ok": available,
                "detail": ("可用" if available else "未偵測到"),
            }
        )

    # =====================================================
    # Ghostscript
    # =====================================================

    gs = tools["ghostscript"]

    report.append(
        {
            "name": "Ghostscript",
            "ok": bool(gs),
            "detail": (gs if gs else "未偵測到"),
        }
    )

    # =====================================================
    # Tesseract
    # =====================================================

    tess = tools["tesseract"]

    report.append(
        {
            "name": "Tesseract",
            "ok": bool(tess),
            "detail": (tess if tess else "未偵測到"),
        }
    )

    # =====================================================
    # OCR languages
    # =====================================================

    languages = get_tesseract_languages(tess)

    for code, name in REQUIRED_OCR_LANGUAGES.items():
        available = code in languages

        report.append(
            {
                "name": f"OCR {name}",
                "ok": available,
                "detail": (code if available else f"{code} 未安裝"),
            }
        )

    return report
