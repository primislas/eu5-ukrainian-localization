import logging
import sys

# Color codes for standard console
GREY = "\x1b[38;20m"
WHITE = "\x1b[36;20m"
YELLOW = "\x1b[33;20m"
RED = "\x1b[31;20m"
BOLD_RED = "\x1b[31;1m"
RESET = "\x1b[0m"

class CustomFormatter(logging.Formatter):
    format_str = "%(asctime)s [%(levelname)s][%(name)s][%(filename)s:%(lineno)d] %(message)s"

    FORMATS = {
        logging.DEBUG: GREY + format_str + RESET,
        logging.INFO: WHITE + format_str + RESET,
        logging.WARNING: YELLOW + format_str + RESET,
        logging.ERROR: RED + format_str + RESET,
        logging.CRITICAL: BOLD_RED + format_str + RESET
    }

    def format(self, record):
        log_fmt = self.FORMATS.get(record.levelno)
        formatter = logging.Formatter(log_fmt)
        return formatter.format(record)

def get_logger(name="ukrainersalis_utils", level=logging.DEBUG):
    _logger = logging.getLogger(name)
    _logger.setLevel(level)

    if not _logger.handlers:
        ch = logging.StreamHandler(sys.stdout)
        ch.setLevel(level)
        ch.setFormatter(CustomFormatter())
        _logger.addHandler(ch)

    return _logger

logger = get_logger()
