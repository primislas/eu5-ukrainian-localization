import logging
import sys

# Color codes for standard console
GREY = "\x1b[38;20m"
CYAN = "\x1b[36;20m"
YELLOW = "\x1b[33;20m"
RED = "\x1b[31;20m"
BOLD_RED = "\x1b[31;1m"
RESET = "\x1b[0m"


class CustomFormatter(logging.Formatter):
    format_str = "%(asctime)s [%(levelname)s][%(name)s][%(filename)s:%(lineno)d] %(message)s"

    FORMATS = {
        logging.DEBUG: CYAN + format_str + RESET,
        logging.INFO: GREY + format_str + RESET,
        logging.WARNING: YELLOW + format_str + RESET,
        logging.ERROR: RED + format_str + RESET,
        logging.CRITICAL: BOLD_RED + format_str + RESET
    }

    def format(self, record):
        log_fmt = self.FORMATS.get(record.levelno)
        formatter = logging.Formatter(log_fmt)
        formatter.default_msec_format = '%s.%03d'
        return formatter.format(record)


class SimpleCustomFormatter(logging.Formatter):
    format_str = "%(asctime)s [%(levelname)s] %(message)s"

    FORMATS = {
        logging.DEBUG: CYAN + format_str + RESET,
        logging.INFO: GREY + format_str + RESET,
        logging.WARNING: YELLOW + format_str + RESET,
        logging.ERROR: RED + format_str + RESET,
        logging.CRITICAL: BOLD_RED + format_str + RESET
    }

    def format(self, record):
        log_fmt = self.FORMATS.get(record.levelno)
        formatter = logging.Formatter(log_fmt)
        formatter.default_msec_format = '%s.%03d'
        return formatter.format(record)


def get_logger(name: str = "ukrainersalis_utils",
               level: int = logging.DEBUG,
               formatter: logging.Formatter = CustomFormatter()):
    _logger = logging.getLogger(name)
    _logger.setLevel(level)

    if not _logger.handlers:
        ch = logging.StreamHandler(sys.stdout)
        ch.setLevel(level)
        ch.setFormatter(formatter)
        _logger.addHandler(ch)

    return _logger


logger = get_logger()
simple_logger = get_logger(name="ukrainersalis_utils_simple", formatter=SimpleCustomFormatter())
