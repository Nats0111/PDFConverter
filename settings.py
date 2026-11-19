import json

from config import (
    SETTINGS_FILE,
)


DEFAULT_SETTINGS = {

    "compression_quality":
        "medium",

    "ocr_languages": [
        "eng",
        "chi_tra",
    ],

    "ocr_rotate":
        True,

    "ocr_deskew":
        True,

    "ocr_sidecar":
        False,
}


def load_settings():

    if not SETTINGS_FILE.exists():

        return DEFAULT_SETTINGS.copy()

    try:

        content = (
            SETTINGS_FILE.read_text(
                encoding="utf-8"
            )
        )

        loaded = json.loads(
            content
        )

        settings = (
            DEFAULT_SETTINGS.copy()
        )

        if isinstance(
            loaded,
            dict
        ):

            settings.update(
                loaded
            )

        return settings

    except (
        OSError,
        json.JSONDecodeError,
    ):

        return (
            DEFAULT_SETTINGS.copy()
        )


def save_settings(
    settings
):

    try:

        SETTINGS_FILE.write_text(
            json.dumps(
                settings,
                ensure_ascii=False,
                indent=4
            ),
            encoding="utf-8"
        )

    except OSError:

        pass