import os
import logging

def get_logger(name: str = "trading_bot") -> logging.Logger:
    """Return a configured logger.
    Logs are sent to console and to a file under `logs/bot.log`.
    """
    logger = logging.getLogger(name)
    if not logger.handlers:
        logger.setLevel(logging.INFO)
        fmt = logging.Formatter("%(asctime)s - %(name)s - %(levelname)s - %(message)s")
        # Console handler
        ch = logging.StreamHandler()
        ch.setLevel(logging.INFO)
        ch.setFormatter(fmt)
        logger.addHandler(ch)
        # File handler – path relative to repository root
        log_file = os.path.join(os.path.abspath(os.path.dirname(__file__)), "..", "logs", "bot.log")
        fh = logging.FileHandler(log_file)
        fh.setLevel(logging.INFO)
        fh.setFormatter(fmt)
        logger.addHandler(fh)
    return logger
