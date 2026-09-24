import os, json, time, yaml
from binance.client import Client

# Load config
cfg_path = os.path.abspath('C:/Users/amar7/trademach/config/config.yaml')
cfg = yaml.safe_load(open(cfg_path))
client = Client(api_key=cfg['binance']['api_key'], api_secret=cfg['binance']['api_secret'])
client.API_URL = cfg['binance']['base_url']

# Reset equity, positions, performance
equity_path = os.path.abspath('C:/Users/amar7/trademach/data/equity.json')
with open(equity_path, 'w') as f:
    json.dump({'equity': 100.0}, f)
positions_path = os.path.abspath('C:/Users/amar7/trademach/data/positions.json')
with open(positions_path, 'w') as f:
    json.dump({}, f)
performance_path = os.path.abspath('C:/Users/amar7/trademach/data/performance.json')
with open(performance_path, 'w') as f:
    json.dump({}, f)

# Run bot loop
from bot.trading_bot import TradingBot
bot = TradingBot()
iterations = 20  # simulate ~20 minutes (1 min interval per iteration)
trade_count = 0
profit_sum = 0.0
positive_trades = 0
for i in range(iterations):
    profits = bot.run()
    # profits is a list of per-symbol profit (or None for HOLD)
    for p in profits:
        if p is not None:
            trade_count += 1
            profit_sum += p
            if p > 0:
                positive_trades += 1
    time.sleep(1)  # small pause to avoid hammering the API

# Compute accuracy as % of profitable trades (if any trades executed)
accuracy = (positive_trades / trade_count * 100) if trade_count else 0.0

print('--- TEST RUN SUMMARY ---')
print(f'Trades executed: {trade_count}')
print(f'Total P&L: {profit_sum:.6f} USDT')
print(f'Positive trade accuracy: {accuracy:.2f}%')
