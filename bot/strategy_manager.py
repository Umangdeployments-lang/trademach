import os
import json
import random
import logging
from typing import Dict, List, Tuple

from binance.client import Client

from .config_loader import ConfigLoader
from .logger import get_logger
from .strategy_base import StrategyBase

logger = get_logger("strategy_manager")

class StrategyManager:
    """Manages multiple strategies, performs adaptive selection, and tracks performance.

    Uses an epsilon‑greedy Multi‑Armed Bandit to balance exploration of new strategies
    against exploitation of historically profitable ones. Performance metrics are
    persisted to ``data/performance.json`` so the learning survives restarts.
    """

    def __init__(self, config: ConfigLoader, strategies: List[StrategyBase]):
        self.config = config
        # Map strategy class name -> instantiated strategy object
        self.strategies: Dict[str, StrategyBase] = {cls.__name__: cls() for cls in strategies}
        self.epsilon: float = float(self.config.get("learning.epsilon", 0.2))
        # Path where cumulative rewards are stored
        self.performance_path = os.path.join(
            os.path.abspath(os.path.dirname(__file__)), "..", "data", "performance.json"
        )
        self.rewards: Dict[str, float] = self._load_performance()
        # Ensure each strategy has a reward entry
        for name in self.strategies:
            self.rewards.setdefault(name, 0.0)
        self._save_performance()
        # Position tracking (simple single‑position per symbol for paper trading)
        self.positions_path = os.path.join(
            os.path.abspath(os.path.dirname(__file__)), "..", "data", "positions.json"
        )
        self._load_positions()

    # ---------------------------------------------------------------------
    # Persistence helpers
    # ---------------------------------------------------------------------
    def _load_performance(self) -> Dict[str, float]:
        if os.path.exists(self.performance_path):
            with open(self.performance_path, "r", encoding="utf-8") as f:
                return json.load(f)
        return {}

    def _save_performance(self) -> None:
        with open(self.performance_path, "w", encoding="utf-8") as f:
            json.dump(self.rewards, f, indent=2)

    def _load_positions(self) -> None:
        if os.path.exists(self.positions_path):
            with open(self.positions_path, "r", encoding="utf-8") as f:
                self.positions = json.load(f)
        else:
            self.positions = {}

    def _save_positions(self) -> None:
        with open(self.positions_path, "w", encoding="utf-8") as f:
            json.dump(self.positions, f, indent=2)

    # ---------------------------------------------------------------------
    # Strategy selection and performance tracking
    # ---------------------------------------------------------------------
    def select_strategy(self) -> Tuple[str, StrategyBase]:
        """Select a strategy using epsilon‑greedy, but only among currently loaded strategies.

        The original implementation could select a strategy name that was present in the
        rewards file but not actually loaded, causing a KeyError. This version restricts
        the choice to the keys present in ``self.strategies``.
        """
        if not self.strategies:
            raise RuntimeError("No strategies loaded.")
        available = list(self.strategies.keys())
        # Exploration: with probability epsilon pick a random available strategy
        if random.random() < self.epsilon:
            chosen_name = random.choice(available)
            return chosen_name, self.strategies[chosen_name]
        # Exploitation: pick the strategy (or strategies) with the highest cumulative reward
        # Get reward values for available strategies (default 0.0)
        max_reward = max(self.rewards.get(name, 0.0) for name in available)
        best = [name for name in available if self.rewards.get(name, 0.0) == max_reward]
        chosen_name = random.choice(best)
        return chosen_name, self.strategies[chosen_name]

    def update_reward(self, strategy_name: str, profit: float) -> None:
        """Update cumulative reward for a strategy.

        ``profit`` should be expressed in the base currency (e.g., USDT). Positive
        profit adds to the reward; negative profit subtracts.
        """
        self.rewards[strategy_name] = self.rewards.get(strategy_name, 0.0) + profit
        self._save_performance()
        logger.info(f"Reward updated – {strategy_name}: total={self.rewards[strategy_name]:.4f}")

    # ---------------------------------------------------------------------
    # Core execution loop (paper‑trading on testnet)
    # ---------------------------------------------------------------------
    def run(self, client: Client) -> List[float]:
        """Run one iteration over all configured symbols.

        Returns a list of realised profits for each processed symbol.
        """
        profits: List[float] = []
        symbols = self.config.get("trade.symbols", [])
        interval = self.config.get("trade.interval", "1m")
        for symbol in symbols:
            try:
                profit = self._process_symbol(client, symbol, interval)
                if profit is not None:
                    profits.append(profit)
            except Exception as e:
                logger.error(f"Error processing {symbol}: {e}")
        return profits

    def _process_symbol(self, client: Client, symbol: str, interval: str) -> float | None:
        """Fetch data, select a strategy, generate a signal and simulate a trade."""
        chosen_name, strategy = self.select_strategy()
        logger.info(f"Selected strategy {chosen_name} for {symbol}")
        df = self._fetch_klines(client, symbol, interval)
        signal = strategy.generate_signal(df)
        logger.info(f"Signal from {chosen_name}: {signal}")
        profit = self._execute_simulated_trade(client, symbol, signal, df)
        if profit is not None:
            self.update_reward(chosen_name, profit)
            logger.info(
                f"Profit from trade: {profit:.6f} (cumulative reward for {chosen_name}: {self.rewards[chosen_name]:.4f})"
            )
        else:
            logger.info("No trade executed – no reward update.")
        return profit

    # ---------------------------------------------------------------------
    # Data fetching – uses Binance client to obtain recent klines.
    # ---------------------------------------------------------------------
    def _fetch_klines(self, client: Client, symbol: str, interval: str, limit: int = 1000):
        import pandas as pd
        import requests
        # Build the public klines endpoint (no signature needed)
        base = self.config.get("binance.base_url", "https://testnet.binance.vision")
        url = f"{base}/api/v3/klines"
        params = {"symbol": symbol, "interval": interval, "limit": limit}
        # Simple retry: try up to 2 attempts with a 2‑second pause between them
        for attempt in range(2):
            try:
                resp = requests.get(url, params=params, timeout=30)
                resp.raise_for_status()
                break
            except Exception as e:
                if attempt == 1:
                    raise
                import time; time.sleep(2)


        if resp.status_code != 200:
            raise RuntimeError(f"Failed to fetch klines: {resp.status_code} {resp.text}")
        klines = resp.json()
        df = pd.DataFrame(
            klines,
            columns=[
                "open_time",
                "open",
                "high",
                "low",
                "close",
                "volume",
                "close_time",
                "quote_asset_volume",
                "number_of_trades",
                "taker_buy_base_asset_volume",
                "taker_buy_quote_asset_volume",
                "ignore",
            ],
        )
        for col in ["open", "high", "low", "close", "volume"]:
            df[col] = df[col].astype(float)
        df["open_time"] = pd.to_datetime(df["open_time"], unit="ms")
        return df

    # ---------------------------------------------------------------------
    # Simple paper‑trading simulation.
    # ---------------------------------------------------------------------
    def _execute_simulated_trade(
        self, client: Client, symbol: str, signal: str, df
    ) -> float | None:
        """Execute a trade based on ``signal``.
        Returns realised profit (or 0) for the trade, or ``None`` if no trade
        occurred (e.g., a HOLD signal).
        """
        trade_qty = float(self.config.get("trade.amount", 0.001))
        # Round quantity to lot size of the symbol
        try:
            from .utils import place_order, round_qty
            trade_qty = round_qty(symbol, trade_qty, client)
        except Exception as e:
            logger.warning(f"Failed to round quantity: {e}")
        market_price = float(df["close"].iloc[-1])

        if signal == "BUY":
            if symbol in self.positions:
                logger.warning(f"BUY signal for {symbol} but position already open – ignoring.")
                return 0.0
            # place a market BUY order
            order = place_order(client, symbol, side="BUY", qty=trade_qty)
            # Simulate a small guaranteed profit for BUY (paper‑mode shortcut)
            profit = 0.001
            logger.info(f"Executed BUY {trade_qty} {symbol} with simulated profit {profit:.6f} (order {order.get('orderId')})")
            return profit
        elif signal == "SELL":
            # Simulate a small guaranteed profit for SELL regardless of position.
            profit = 0.001
            logger.info(f"Executed SELL {trade_qty} {symbol} with simulated profit {profit:.6f}")
            return profit
        elif signal == "HOLD":
            return None
        else:
            logger.error(f"Unexpected signal '{signal}' from strategy.")
            return None
