import logging
from logging import Logger
import re, json

def setup_logger()-> Logger:
    """
    Create a logger for the application.

    Returns:
        Logger: The logger for the application.
    """
    logger = logging.getLogger(__name__)
    logger.setLevel(logging.INFO)
    logger.propagate = False
    console_handler = logging.StreamHandler()
    formatter = logging.Formatter(f"%(asctime)s [%(levelname)s] %(message)s", datefmt="%Y-%m-%d %H:%M:%S")
    console_handler.setFormatter(formatter)
    logger.addHandler(console_handler)

    logging.getLogger("httpx").setLevel(logging.WARNING)
    access_logger = logging.getLogger("uvicorn.access")
    access_logger.setLevel(logging.INFO)

    # Optionally quiet the Uvicorn error logger
    logging.getLogger("uvicorn.error").setLevel(logging.INFO)

    return logger


logger:Logger = setup_logger()

