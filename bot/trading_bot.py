import os
import json
import logging
from typing import Dict, Any

from binance.client import Client

from .config_loader import ConfigLoader
from .logger import logger
from .risk_governor import RiskGovernor
from .strategy_manager import StrategyManager

class TradingBot:
    def __init__(self, config_path: str = "C:/Users/amar7/trading_bot/config/config.yaml"):
        self.config = ConfigLoader(config_path)
        self.logger = logger
        # Initialise Binance client for testnet
        api_key = self.config.get("binance.api_key")
        api_secret = self.config.get("binance.api_secret")
        base_url = self.config.get("binance.base_url", "https://testnet.binance.vision")
        self.client = Client(api_key=api_key, api_secret=api_secret, testnet=True)
        self.client.API_URL = base_url
        # Initialise risk governor with starting equity (e.g., 1000 USDT for testnet)
        self.risk_governor = RiskGovernor(self.config, initial_equity=1000.0)
        # Load enabled strategies from config
        enabled = self.config.get("strategies.enabled", [])
        strategy_classes = []
        for name in enabled:
            try:
                mod = __import__(f"bot.strategies.{name.lower()}", fromlist=[name])
                cls = getattr(mod, name)
                strategy_classes.append(cls)
            except Exception as e:
                self.logger.error(f"Failed to load strategy {name}: {e}")
        self.strategy_manager = StrategyManager(self.config, strategy_classes)

    def run(self):
        """Main loop – for a demo we run a single iteration.

        In production you would schedule this method to run periodically (e.g., every
        minute) using APScheduler or a while‑loop with sleep.
        """
        if self.risk_governor.is_killed():
            self.logger.error("Kill switch is active – aborting run.")
            return
        # Run the strategy manager which returns realised profits per symbol
        profits = self.strategy_manager.run(self.client)
        # Record each profit with the risk governor (which updates equity and checks limits)
        for profit in profits:
            if profit is not None:
                self.risk_governor.record_profit(profit)
        self.logger.info("Run completed.")

if __name__ == "__main__":
    bot = TradingBot()
    bot.run()
if __name__ == "__main__":
    bot = TradingBot()
    bot.run()
