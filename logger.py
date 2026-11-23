import logging

from config import LOGS

LOG_FILE = LOGS / "converter.log"


logger = logging.getLogger("converter")
logger.setLevel(logging.INFO)


# 避免重複加入 handler
if not logger.handlers:
    file_handler = logging.FileHandler(LOG_FILE, encoding="utf-8")

    formatter = logging.Formatter(
        "%(asctime)s | %(message)s", datefmt="%Y-%m-%d %H:%M:%S"
    )

    file_handler.setFormatter(formatter)

    logger.addHandler(file_handler)


def log_success(process, message):

    logger.info(f"{process} | SUCCESS | {message}")


def log_failed(process, message):

    logger.error(f"{process} | FAILED | {message}")


def log_skipped(process, message):

    logger.warning(f"{process} | SKIPPED | {message}")
