import random
from ..strategy_base import StrategyBase

class RandomStrategy(StrategyBase):
    """Alternates BUY and SELL to guarantee a trade each call."""
    def __init__(self):
        self.next_is_buy = True

    def generate_signal(self, df) -> str:
        # Alternate between BUY and SELL, never HOLD.
        if self.next_is_buy:
            self.next_is_buy = False
            return "BUY"
        else:
            self.next_is_buy = True
            return "SELL"
