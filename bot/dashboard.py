# Minimal Flask dashboard for the paper‑trading bot
# Run: python -m bot.dashboard

from flask import Flask, jsonify
import os, json

# Import internal modules for configuration and risk governor state
from .config_loader import ConfigLoader
from .risk_governor import RiskGovernor

app = Flask(__name__)

# Helper to load JSON persistence files from the data folder
DATA_DIR = os.path.abspath(os.path.join(os.path.dirname(__file__), "..", "data"))

def load_json(fname):
    path = os.path.join(DATA_DIR, fname)
    if os.path.exists(path):
        with open(path, "r", encoding="utf-8") as f:
            return json.load(f)
    return {}

@app.route('/')
def index():
    # Simple HTML page – placeholder for a richer UI later.
    return """
    <html>
    <head><title>Hermes Trading Bot Dashboard</title></head>
    <body>
        <h1>Hermes Trading Bot (paper‑trading)</h1>
        <ul>
            <li><a href='/equity'>Equity &amp; drawdown</a></li>
            <li><a href='/performance'>Strategy performance</a></li>
            <li><a href='/positions'>Open positions</a></li>
            <li><a href='/risk'>Risk‑governor state</a></li>
        </ul>
    </body>
    </html>
    """

@app.route('/equity')
def equity():
    return jsonify(load_json('equity.json'))

@app.route('/performance')
def performance():
    return jsonify(load_json('performance.json'))

@app.route('/positions')
def positions():
    return jsonify(load_json('positions.json'))

@app.route('/risk')
def risk():
    # Load config to construct a temporary RiskGovernor instance (no state mutation)
    cfg_path = os.path.abspath(os.path.join(os.path.dirname(__file__), "..", "config", "config.yaml"))
    cfg = ConfigLoader(cfg_path)
    gov = RiskGovernor(cfg)
    return jsonify({
        "killed": gov.is_killed(),
        "drawdown_levels": gov.drawdown_levels,
        "equity": gov.equity,
        "peak_equity": gov.peak_equity,
        "daily_pnl": gov.daily_pnl,
    })

if __name__ == '__main__':
    # Expose on all interfaces for convenience; adjust host/port as needed.
    app.run(host='0.0.0.0', port=8000, debug=True)
