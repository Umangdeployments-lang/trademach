import pandas as pd
from ..strategy_base import StrategyBase

class MovingAverageStrategy(StrategyBase):
    """Simple SMA crossover strategy.
    
    Parameters
    ----------
    short_window : int
        Period for the short-term SMA.
    long_window : int
        Period for the long-term SMA.
    """
    def __init__(self, short_window: int = 2, long_window: int = 3):
        self.short_window = short_window
        self.long_window = long_window
        if self.short_window >= self.long_window:
            raise ValueError("short_window must be less than long_window")

    def generate_signal(self, df: pd.DataFrame) -> str:
        """Return BUY/SELL/HOLD based on SMA crossovers.
        
        If the short SMA crosses above the long SMA => BUY.
        If the short SMA crosses below the long SMA => SELL.
        Otherwise HOLD.
        """
        # Compute SMAs
        df["sma_short"] = df["close"].rolling(window=self.short_window).mean()
        df["sma_long"] = df["close"].rolling(window=self.long_window).mean()

        # Need at least one full SMA period to compare
        if len(df) < self.long_window:
            return "HOLD"

        # Get the most recent two SMA values to detect crossover
        recent = df.iloc[-2:]
        prev_short = recent["sma_short"].iloc[0]
        prev_long = recent["sma_long"].iloc[0]
        curr_short = recent["sma_short"].iloc[1]
        curr_long = recent["sma_long"].iloc[1]

        if pd.isna(prev_short) or pd.isna(prev_long) or pd.isna(curr_short) or pd.isna(curr_long):
            return "HOLD"
        # Detect crossover
        if prev_short <= prev_long and curr_short > curr_long:
            return "BUY"
        if prev_short >= prev_long and curr_short < curr_long:
            return "SELL"
        return "HOLD"

    def __repr__(self) -> str:
            return f"MovingAverageStrategy(short={self.short_window}, long={self.long_window}) # Rating: {self.rating:.1f}/10"
