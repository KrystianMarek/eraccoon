import os
import sys
import logging

REMOTE_LOG_LEVEL   = os.environ.get("REMOTE_LOG_LEVEL", "INFO").upper()


def get_logger(name: str) -> logging.Logger:
    _logger = logging.getLogger(name)
    _logger.setLevel(getattr(logging, REMOTE_LOG_LEVEL))
    if not _logger.handlers:
        handler = logging.StreamHandler(sys.stdout)
        formatter = logging.Formatter('%(asctime)s - %(name)s - %(levelname)s - %(message)s')
        handler.setFormatter(formatter)
        _logger.addHandler(handler)

    return _logger


_LOGGER = get_logger(__name__)