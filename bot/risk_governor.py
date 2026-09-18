import os
import json
import logging
from datetime import datetime, date
from typing import Dict, Any

from .config_loader import ConfigLoader
from .logger import get_logger

logger = get_logger("risk_governor")

class RiskGovernor:
    """Enforces risk limits and kill‑switch logic.

    The governor is deliberately separate from any strategy logic – strategies
    only emit a signal. The governor decides whether an order may be placed,
    enforces position sizing, daily loss limits, drawdown ladder tiers, and can
    trigger a global kill switch.
    """

    def __init__(self, config: ConfigLoader, initial_equity: float | None = None):
        self.config = config
        # Convert percentages to decimals
        self.max_risk_pct = float(self.config.get("risk.max_risk_per_trade_pct", 0.5)) / 100.0
        self.daily_loss_limit_pct = float(self.config.get("risk.daily_loss_limit_pct", 2.0)) / 100.0
        self.drawdown_levels = self._load_drawdown_levels()
        # Persistence paths
        self.equity_path = os.path.join(os.path.abspath(os.path.dirname(__file__)), "..", "data", "equity.json")
        self.kill_path = os.path.join(os.path.abspath(os.path.dirname(__file__)), "..", "data", "kill_switch.json")
        # Load persisted equity or initialise
        self.equity = initial_equity if initial_equity is not None else self._load_equity()
        self.peak_equity = self.equity
        self.daily_pnl: Dict[str, float] = {}
        self._ensure_kill_switch_file()

    # ---------------------------------------------------------------------
    # Persistence helpers
    # ---------------------------------------------------------------------
    def _load_equity(self) -> float:
        if os.path.exists(self.equity_path):
            try:
                with open(self.equity_path, "r", encoding="utf-8") as f:
                    data = json.load(f)
                    return float(data.get("equity", 0.0))
            except Exception as e:
                logger.warning(f"Failed to read equity file: {e}, starting at 0.")
        return 0.0

    def _save_equity(self) -> None:
        with open(self.equity_path, "w", encoding="utf-8") as f:
            json.dump({"equity": self.equity}, f, indent=2)

    def _ensure_kill_switch_file(self) -> None:
        if not os.path.exists(self.kill_path):
            with open(self.kill_path, "w", encoding="utf-8") as f:
                json.dump({"killed": False, "timestamp": None}, f)

    def _load_kill_switch(self) -> Dict[str, Any]:
        with open(self.kill_path, "r", encoding="utf-8") as f:
            return json.load(f)

    def _save_kill_switch(self, killed: bool, timestamp: str | None) -> None:
        with open(self.kill_path, "w", encoding="utf-8") as f:
            json.dump({"killed": killed, "timestamp": timestamp}, f)

    # ---------------------------------------------------------------------
    # Configuration helpers
    # ---------------------------------------------------------------------
    def _load_drawdown_levels(self) -> list[Dict[str, Any]]:
        raw = self.config.get("risk.drawdown_levels", [])
        levels = []
        for entry in raw:
            try:
                thresh = float(entry.get("threshold", 0))
                action = entry.get("action", "log")
                levels.append({"threshold": thresh, "action": action})
            except Exception:
                continue
        levels.sort(key=lambda x: x["threshold"])  # ascending
        return levels

    # ---------------------------------------------------------------------
    # Public API – called after each trade profit/loss is known.
    # ---------------------------------------------------------------------
    def record_profit(self, profit: float) -> None:
        """Update equity and daily P&L tracking, then evaluate risk thresholds."""
        self.equity += profit
        if self.equity > self.peak_equity:
            self.peak_equity = self.equity
        today = date.today().isoformat()
        self.daily_pnl[today] = self.daily_pnl.get(today, 0.0) + profit
        self._save_equity()
        self._evaluate_risk()

    def _evaluate_risk(self) -> None:
        # 1. Daily loss limit
        today = date.today().isoformat()
        daily_loss = -self.daily_pnl.get(today, 0.0)  # positive if loss
        daily_limit = self.daily_loss_limit_pct * self.equity
        if daily_loss > daily_limit:
            logger.warning(f"Daily loss limit exceeded: {daily_loss:.2f} > {daily_limit:.2f}")
            self._trigger_kill("daily_loss_limit")
            return

        # 2. Drawdown ladder
        if self.peak_equity > 0:
            drawdown_pct = (self.peak_equity - self.equity) / self.peak_equity * 100.0
            for level in self.drawdown_levels:
                if drawdown_pct >= level["threshold"]:
                    action = level["action"]
                    logger.info(f"Drawdown {drawdown_pct:.2f}% crossed {level['threshold']}% -> {action}")
                    self._apply_drawdown_action(action)
                    # Continue checking higher thresholds

    def _apply_drawdown_action(self, action: str) -> None:
        if action == "log":
            logger.info("Drawdown logged – no operational change.")
        elif action == "reduce_position":
            # Halve the per‑trade risk, but enforce a minimum of 0.1%.
            self.max_risk_pct = max(self.max_risk_pct / 2.0, 0.001)
            logger.info(f"Reduced max risk per trade to {self.max_risk_pct*100:.3f}%")
        elif action == "halt_new_strategies":
            self._set_flag("halt_new_strategies", True)
            logger.info("Halting approval of new strategies until manual reset.")
        elif action == "kill_switch":
            self._trigger_kill("drawdown_kill_switch")
        else:
            logger.warning(f"Unknown drawdown action: {action}")

    def _set_flag(self, name: str, value: bool) -> None:
        flag_path = os.path.join(os.path.abspath(os.path.dirname(__file__)), "..", "data", f"flag_{name}.json")
        with open(flag_path, "w", encoding="utf-8") as f:
            json.dump({name: value}, f)

    def _trigger_kill(self, reason: str) -> None:
        timestamp = datetime.utcnow().isoformat() + "Z"
        self._save_kill_switch(True, timestamp)
        logger.error(f"Kill switch activated due to {reason} at {timestamp}. All trading halted.")
        self.max_risk_pct = 0.0

    def is_killed(self) -> bool:
        state = self._load_kill_switch()
        return bool(state.get("killed", False))

    # ---------------------------------------------------------------------
    # Position sizing helper – callers ask how much to risk per trade.
    # ---------------------------------------------------------------------
    def compute_position_size(self, price: float, trade_qty: float | None = None) -> float:
        """Return the quantity to trade respecting the max‑risk‑pct.

        ``price`` is the current market price of the symbol. If ``trade_qty`` is
        supplied (e.g., a lot size) the method caps it to the amount that would
        risk no more than ``max_risk_pct`` of equity.
        """
        if self.equity <= 0:
            return 0.0
        max_risk_amount = self.equity * self.max_risk_pct
        if trade_qty is None:
            # Return monetary risk amount; caller can convert to qty using price.
            return max_risk_amount
        # Convert monetary risk to quantity based on price.
        max_qty = max_risk_amount / price if price > 0 else 0.0
        return min(trade_qty, max_qty)
