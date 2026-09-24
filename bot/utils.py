# Utility helpers for Binance trading bot
import logging
from binance.client import Client

log = logging.getLogger("utils")

def round_qty(symbol: str, qty: float, client: Client) -> float:
    """Round a quantity down to the lot‑size step for a given symbol.
    Returns the rounded quantity (may be zero if qty < min lot).
    """
    try:
        # Use the public exchangeInfo endpoint via a simple HTTP GET to avoid the Binance client wrapper issue.
        import requests, yaml, os
        cfg_path = os.path.abspath(os.path.join(os.path.dirname(__file__), "..", "config", "config.yaml"))
        cfg = yaml.safe_load(open(cfg_path))
        base = cfg.get("binance.base_url", "https://testnet.binance.vision")
        resp = requests.get(f"{base}/api/v3/exchangeInfo", timeout=10)
        resp.raise_for_status()
        data = resp.json()
        symbol_info = next(s for s in data["symbols"] if s["symbol"] == symbol)
        lot_filter = next(f for f in symbol_info["filters"] if f["filterType"] == "LOT_SIZE")
# Reduce lot size step to ensure minimal qty works
        step = max(float(lot_filter["stepSize"]), 0.00001)
        # Ensure qty is at least minQty
        min_qty = float(lot_filter.get("minQty", "0.00001"))
        qty = max(qty, min_qty)
        rounded = int(qty / step) * step
        return float(rounded)
    except Exception as e:
        log.warning(f"Failed to round qty for {symbol}: {e}")
        return qty

def place_order(client: Client, symbol: str, side: str, qty: float, price: float | None = None):
    """Place a market (or limit) order.
    Returns the Binance response dict. In paper‑mode the function simply logs and returns a dummy dict.
    """
    import yaml, os
    # First try to load paper_mode flag from separate file if present
    paper_mode_path = os.path.abspath(os.path.join(os.path.dirname(__file__), "..", "config", "paper_mode.yaml"))
    if os.path.exists(paper_mode_path):
        cfg = yaml.safe_load(open(paper_mode_path))
        paper = cfg.get("paper_mode", True)
    else:
        # Fallback: check config.yaml for legacy key
        cfg_path = os.path.abspath(os.path.join(os.path.dirname(__file__), "..", "config", "config.yaml"))
        cfg = yaml.safe_load(open(cfg_path))
        paper = cfg.get("paper_mode", True)
    if paper:
        log.info(f"[PAPER] {side} {qty} {symbol} @ {price or 'market'}")
        return {"status": "simulated", "side": side, "symbol": symbol, "executedQty": qty, "price": price or "market"}
    # Live order
    try:
        if price is None:
            order = client.create_order(symbol=symbol, side=side, type="MARKET", quantity=qty)
        else:
            order = client.create_order(symbol=symbol, side=side, type="LIMIT", timeInForce="GTC", quantity=qty, price=str(price))
        log.info(f"[LIVE] placed {side} order for {qty} {symbol}: {order.get('orderId')}")
        return order
    except Exception as e:
        log.error(f"Order failed: {e}")
        raise

