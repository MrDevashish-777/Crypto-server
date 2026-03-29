"""
Logging Configuration Module
Setup structured logging for the application
"""

import logging
import logging.handlers
from pathlib import Path
import sys
from config.settings import settings


def setup_logging():
    """Configure application logging"""

    # Create logs directory if it doesn't exist
    log_dir = Path(settings.LOG_FILE).parent
    log_dir.mkdir(parents=True, exist_ok=True)

    # Create logger
    logger = logging.getLogger()
    logger.setLevel(getattr(logging, settings.LOG_LEVEL))

    # Remove existing handlers
    for handler in logger.handlers[:]:
        logger.removeHandler(handler)

    # Console handler
    console_handler = logging.StreamHandler(sys.stdout)
    console_handler.setLevel(getattr(logging, settings.LOG_LEVEL))
    
    if settings.LOG_FORMAT.lower() == "json":
        from pythonjsonlogger import jsonlogger
        console_format = jsonlogger.JsonFormatter()
    else:
        console_format = logging.Formatter(settings.LOG_FORMAT)
        
    console_handler.setFormatter(console_format)
    logger.addHandler(console_handler)

    # File handler with rotation
    file_handler = logging.handlers.RotatingFileHandler(
        settings.LOG_FILE,
        maxBytes=10 * 1024 * 1024,  # 10MB
        backupCount=5,
    )
    file_handler.setLevel(getattr(logging, settings.LOG_LEVEL))
    file_handler.setFormatter(console_format)
    logger.addHandler(file_handler)

    logger.info(f"Logging configured - Level: {settings.LOG_LEVEL}")
