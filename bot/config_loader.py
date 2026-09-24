import os
import yaml
import logging
from typing import Any, Dict

class ConfigLoader:
    """Utility class to load YAML config files for the trading bot.

    The config is expected to live at `config/config.yaml` relative to the repository root.
    It contains Binance API credentials, a list of symbols to trade, trading parameters,
    and the list of enabled strategy class names.
    """
    def __init__(self, config_path: str = "C:/Users/amar7/trademach/config/config.yaml"):
        self.config_path = config_path
        self.config: Dict[str, Any] = {}
        self._load()

    def _load(self) -> None:
        if not os.path.exists(self.config_path):
            raise FileNotFoundError(f"Config file not found: {self.config_path}")
        with open(self.config_path, "r", encoding="utf-8") as f:
            self.config = yaml.safe_load(f) or {}

    def get(self, key: str, default: Any = None) -> Any:
        """Retrieve a value from the config using dot‑notation, e.g. 'binance.api_key'."""
        parts = key.split(".")
        cur = self.config
        for part in parts:
            if isinstance(cur, dict) and part in cur:
                cur = cur[part]
            else:
                return default
        return cur

    def reload(self) -> None:
        """Reload the config file – useful when the user edits it while the bot is running."""
        self._load()

# Simple centralised logger configuration

def get_logger(name: str = "trading_bot") -> logging.Logger:
    logger = logging.getLogger(name)
    if not logger.handlers:
        logger.setLevel(logging.INFO)
        fmt = logging.Formatter("%(asctime)s - %(name)s - %(levelname)s - %(message)s")
        # Console handler
        ch = logging.StreamHandler()
        ch.setLevel(logging.INFO)
        ch.setFormatter(fmt)
        logger.addHandler(ch)
        # File handler
        log_file = os.path.join(os.path.abspath(os.path.dirname(__file__)), "..", "logs", "bot.log")
        fh = logging.FileHandler(log_file)
        fh.setLevel(logging.INFO)
        fh.setFormatter(fmt)
        logger.addHandler(fh)
    return logger

# Export a module‑level logger for quick imports
logger = get_logger()
