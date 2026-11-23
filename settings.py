import copy
import json

from config import (
    SETTINGS_FILE,
)

DEFAULT_SETTINGS = {
    "compression_quality": "medium",
    "custom_dpi": 200,
    "ocr_languages": [
        "eng",
        "chi_tra",
    ],
    "ocr_mode": "skip",
    "ocr_rotate": True,
    "ocr_deskew": True,
    "ocr_sidecar": False,
    "scan_optimize_level": 1,
    "ghostscript_path": "",
    "tesseract_path": "",
}


def load_settings():

    if not (SETTINGS_FILE.exists()):
        return copy.deepcopy(DEFAULT_SETTINGS)

    try:
        data = json.loads(SETTINGS_FILE.read_text(encoding="utf-8"))

        settings = copy.deepcopy(DEFAULT_SETTINGS)

        if isinstance(data, dict):
            settings.update(data)

        return settings

    except (
        OSError,
        json.JSONDecodeError,
    ):
        return copy.deepcopy(DEFAULT_SETTINGS)


def save_settings(settings):

    try:
        SETTINGS_FILE.write_text(
            json.dumps(settings, ensure_ascii=False, indent=4), encoding="utf-8"
        )

    except OSError:
        pass
