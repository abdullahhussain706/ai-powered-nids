import logging
import os
import sys
from pathlib import Path
from utils.helpers import load_config

# Attempt to import colorama for colored console logging
try:
    from colorama import Fore, Style, init
    init(autoreset=True)
    COLORAMA_AVAILABLE = True
except ImportError:
    COLORAMA_AVAILABLE = False

BASE_DIR = Path(__file__).resolve().parent.parent


class ColoredFormatter(logging.Formatter):
    """Custom formatter to inject ANSI colors into console output."""
    
    COLORS = {
        logging.DEBUG: Fore.BLUE + Style.BRIGHT,
        logging.INFO: Fore.GREEN,
        logging.WARNING: Fore.YELLOW + Style.BRIGHT,
        logging.ERROR: Fore.RED + Style.BRIGHT,
        logging.CRITICAL: Fore.RED + Style.BRIGHT + Style.NORMAL,
    }

    def format(self, record):
        if COLORAMA_AVAILABLE and record.levelno in self.COLORS:
            # Color the level name
            orig_levelname = record.levelname
            record.levelname = f"{self.COLORS[record.levelno]}{orig_levelname}{Style.RESET_ALL}"
            
            # Color the message for warnings and errors
            orig_msg = record.msg
            if record.levelno >= logging.WARNING:
                record.msg = f"{self.COLORS[record.levelno]}{orig_msg}{Style.RESET_ALL}"
                
            formatted = super().format(record)
            
            # Restore original values to prevent side-effects on file loggers
            record.levelname = orig_levelname
            record.msg = orig_msg
            return formatted
            
        return super().format(record)


def setup_logger(log_name: str = "ids_logger", default_file: str = "logs/capture.log") -> logging.Logger:
    """Configures the root logger with file and console handlers.

    Reads configuration from app_config.yaml (e.g. log_level) and returns
    the configured logger.
    """
    app_conf = load_config("app_config.yaml")

    # Resolve log level
    level_str = app_conf.get("log_level", "INFO").upper()
    level_map = {
        "DEBUG": logging.DEBUG,
        "INFO": logging.INFO,
        "WARNING": logging.WARNING,
        "ERROR": logging.ERROR,
        "CRITICAL": logging.CRITICAL
    }
    log_level = level_map.get(level_str, logging.INFO)

    # Resolve log file path
    log_relative = app_conf.get("capture_log_path", default_file)
    log_file_path = BASE_DIR / log_relative if not Path(log_relative).is_absolute() else Path(log_relative)
    log_file_path.parent.mkdir(parents=True, exist_ok=True)

    # Configure root logger
    root_logger = logging.getLogger()
    root_logger.setLevel(log_level)

    # Remove existing handlers to avoid duplicates on re-initialization
    for handler in root_logger.handlers[:]:
        root_logger.removeHandler(handler)

    # 1. File Handler (with full details)
    file_formatter = logging.Formatter(
        fmt="%(asctime)s [%(levelname)s] (%(filename)s:%(lineno)d) - %(message)s",
        datefmt="%Y-%m-%d %H:%M:%S"
    )
    try:
        file_handler = logging.FileHandler(log_file_path, encoding="utf-8")
        file_handler.setLevel(log_level)
        file_handler.setFormatter(file_formatter)
        root_logger.addHandler(file_handler)
    except Exception as e:
        print(f"❌ Failed to set up file logging handler: {e}", file=sys.stderr)

    # 2. Console Handler (with colors and cleaner format)
    console_formatter = ColoredFormatter(
        fmt="%(asctime)s [%(levelname)s] %(message)s",
        datefmt="%H:%M:%S"
    )
    console_handler = logging.StreamHandler(sys.stdout)
    console_handler.setLevel(log_level)
    console_handler.setFormatter(console_formatter)
    root_logger.addHandler(console_handler)

    logging.info(f"📝 Logging initialized (Level: {level_str}, File: {log_relative})")
    return logging.getLogger(log_name)
