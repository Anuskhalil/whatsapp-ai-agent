import logging

from pathlib import Path

from logging.handlers import (
    RotatingFileHandler
)

from app.request_context import (
    get_request_id
)

from app.config import (
    LOG_LEVEL,
    LOG_MAX_BYTES,
    LOG_BACKUP_COUNT
)


BASE_DIR = (
    Path(__file__)
    .resolve()
    .parent
    .parent
)

LOG_DIR = BASE_DIR / "logs"

LOG_FILE = LOG_DIR / "nexusai.log"


# ---------------------------------
# REQUEST ID LOG FILTER
# ---------------------------------

class RequestIdFilter(
    logging.Filter
):

    def filter(
        self,
        record
    ) -> bool:

        record.request_id = (
            get_request_id()
        )

        return True


# ---------------------------------
# SETUP LOGGING
# ---------------------------------

def setup_logging():

    LOG_DIR.mkdir(
        parents=True,
        exist_ok=True
    )

    logger = logging.getLogger(
        "nexusai"
    )

    numeric_log_level = getattr(
    logging,
    LOG_LEVEL
    )

    logger.setLevel(
         numeric_log_level
    )

    # Uvicorn reloads the application.
    if logger.handlers:

        return logger

    formatter = logging.Formatter(
        (
            "%(asctime)s | "
            "%(levelname)-8s | "
            "request_id=%(request_id)s | "
            "%(name)s | "
            "%(message)s"
        ),
        datefmt="%Y-%m-%d %H:%M:%S"
    )

    request_id_filter = (
        RequestIdFilter()
    )

    # ---------------------------------
    # CONSOLE HANDLER
    # ---------------------------------

    console_handler = (
        logging.StreamHandler()
    )

    console_handler.setLevel(
    numeric_log_level
)

    console_handler.setFormatter(
        formatter
    )

    console_handler.addFilter(
        request_id_filter
    )

    # ---------------------------------
    # FILE HANDLER
    # ---------------------------------

    file_handler = (
        RotatingFileHandler(
        LOG_FILE,
        maxBytes=LOG_MAX_BYTES,
        backupCount=LOG_BACKUP_COUNT,
        encoding="utf-8"
       )
    )

    file_handler.setLevel(
    numeric_log_level
)

    file_handler.setFormatter(
        formatter
    )

    file_handler.addFilter(
        request_id_filter
    )

    logger.addHandler(
        console_handler
    )

    logger.addHandler(
        file_handler
    )

    logger.propagate = False

    return logger


# ---------------------------------
# MODULE LOGGER
# ---------------------------------

def get_logger(
    name: str
):

    setup_logging()

    return logging.getLogger(
        f"nexusai.{name}"
    )