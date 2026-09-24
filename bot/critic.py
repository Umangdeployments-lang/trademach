"""Simple critic module for rating the trading bot.
Rating is out of 10 based on trade count, total profit, and accuracy.
Higher values are better. The function is deterministic and lightweight.
"""

def rate_bot(trade_count: int, total_pnl: float, accuracy: float) -> float:
    """Return a rating 0‑10.
    * trade_count normalized: 1 point per 10 trades (capped at 3 points).
    * total_pnl normalized: 1 point per 10 USDT profit (capped at 4 points).
    * accuracy normalized: 1 point per 10 % accuracy (capped at 3 points).
    The weighted sum yields a max of 10.
    """
    # Cap each component
    trade_score = min(trade_count / 10.0, 3.0)  # max 3
    pnl_score = min(total_pnl / 10.0, 4.0)      # max 4
    acc_score = min(accuracy / 10.0, 3.0)      # max 3
    rating = trade_score + pnl_score + acc_score
    return round(rating, 1)
