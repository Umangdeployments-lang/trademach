import pandas as pd
from abc import ABC, abstractmethod

class StrategyBase(ABC):
    """Abstract base class for trading strategies.
    
    Subclasses must implement ``generate_signal(self, df: pd.DataFrame)`` which
    returns one of the strings ``'BUY'``, ``'SELL'`` or ``'HOLD'`` based on the
    supplied market data.
    """
    @abstractmethod
    def generate_signal(self, df: pd.DataFrame) -> str:
        """Given a pandas DataFrame of price data, return a trading signal.
        
        The DataFrame columns are the standard Binance kline columns (see
        ``StrategyManager._fetch_klines``). Implementations should be deterministic
        and side‑effect free – they only compute a signal.
        """
        raise NotImplementedError

    def __repr__(self) -> str:
        return f"{self.__class__.__name__}()"
