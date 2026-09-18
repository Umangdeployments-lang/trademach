# Automated Binance Testnet Trading Bot

This repository contains a **modular Python trading bot** skeleton designed to operate on the Binance testnet (paper trading). It is built to be **extensible** and **adaptive**, allowing you to plug‑in multiple trading strategies and a simple learning component that selects the best‑performing strategy over time.

## Features
- **Binance Testnet integration** using `python-binance`.
- **Strategy plug‑in architecture** – add new strategies under `strategies/`.
- **Adaptive strategy selection** via a Multi‑Armed Bandit (epsilon‑greedy) manager that tracks each strategy's profit/loss.
- **Configuration** via a YAML file (`config/config.yaml`).
- **Logging** (info, warnings, errors) saved to `logs/bot.log`.
- **Performance persistence** – strategy rewards are saved to `data/performance.json`.
- **Dockerfile** for containerised deployment.

## Directory layout
```
trading_bot/
├─ bot/
│  ├─ __init__.py
│  ├─ config_loader.py        # Load YAML config
│  ├─ logger.py               # Centralised logger
│  ├─ strategy_base.py        # Abstract base class for strategies
│  ├─ strategy_manager.py     # Adaptive manager (MAB)
│  ├─ trading_bot.py           # Main loop
│  └─ strategies/
│     ├─ __init__.py
│     ├─ moving_average.py    # Example SMA crossover strategy
│     └─ momentum.py          # Example momentum strategy
├─ config/
│  └─ config.yaml             # User‑editable config (API keys, symbols …)
├─ data/
│  └─ performance.json         # Stored rewards for each strategy
├─ logs/
│  └─ bot.log                 # Runtime log file
├─ requirements.txt
├─ Dockerfile
└─ README.md
``` 

## Getting started
1. **Install dependencies**
   ```bash
   python -m venv .venv && source .venv/bin/activate
   pip install -r requirements.txt
   ```
2. **Create Binance testnet API keys**
   - Sign‑up at https://testnet.binance.vision/ and generate an API key/secret.
   - Fill them into `config/config.yaml`.
3. **Run the bot**
   ```bash
   python -m bot.trading_bot
   ```
   The bot will fetch k‑line data for the configured symbol(s), evaluate each enabled strategy, let the manager pick the best one, and place simulated orders on the testnet.

## Extending with new strategies
Create a new file under `bot/strategies/` that inherits from `StrategyBase` and implements the `generate_signal(self, df: pd.DataFrame) -> str` method, returning `'BUY'`, `'SELL'` or `'HOLD'`. Register the class name in `config.yaml` under `strategies.enabled`.

## Adaptive learning
The `StrategyManager` tracks each strategy's cumulative profit (reward) and uses an **epsilon‑greedy** algorithm to balance exploration vs exploitation. Feel free to replace it with a more sophisticated RL algorithm.

## Disclaimer
This code is provided **as‑is** for educational and research purposes. **Do not** use it with real funds without thorough testing, risk assessment, and compliance with relevant regulations. The authors accept no liability for losses incurred.
