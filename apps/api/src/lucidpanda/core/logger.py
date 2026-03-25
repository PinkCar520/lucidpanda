import sys
import os
import logging
from logging.handlers import TimedRotatingFileHandler
from src.lucidpanda.config import settings

def setup_logger(name="LucidPanda"):
    logger = logging.getLogger(name)
    logger.setLevel(logging.INFO)

    # Text Formatter (Human Readable)
    text_formatter = logging.Formatter(
        '%(asctime)s [%(levelname)s] %(message)s',
        datefmt='%Y-%m-%d %H:%M:%S'
    )

    # JSON Formatter (Structured)
    try:
        from pythonjsonlogger import jsonlogger
        json_formatter = jsonlogger.JsonFormatter(
            '%(asctime)s %(levelname)s %(message)s %(name)s %(module)s',
            datefmt='%Y-%m-%d %H:%M:%S',
            json_ensure_ascii=False
        )
    except ImportError:
        json_formatter = text_formatter

    # 1. Console Handler (Text for readability in Dev, JSON in Prod if needed)
    # Check env var for preferring JSON logs in console (e.g. for Docker)
    use_json_console = os.getenv('LOG_FORMAT', 'text').lower() == 'json'
    
    console_handler = logging.StreamHandler(sys.stdout)
    console_handler.setFormatter(json_formatter if use_json_console else text_formatter)
    logger.addHandler(console_handler)

    # 2. File Handler (Always JSON for easy parsing/aggregation)
    if not os.path.exists(settings.LOG_DIR):
        os.makedirs(settings.LOG_DIR)
        
    file_handler = TimedRotatingFileHandler(
        os.path.join(settings.LOG_DIR, "app.json.log"), # Changed extension to indicate JSON
        when="midnight",
        interval=1,
        backupCount=7,
        encoding="utf-8"
    )
    file_handler.setFormatter(json_formatter)
    logger.addHandler(file_handler)

    logger.propagate = False

    return logger

logger = setup_logger()
