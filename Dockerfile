# Dockerfile for the autonomous Binance testnet trading bot
# Build a lightweight container with the bot and its dependencies.
# This Dockerfile assumes you have a working Python 3.11+ environment on the host.

FROM python:3.11-slim AS base

# Create a non‑root user for security
RUN useradd -m trader && mkdir -p /app && chown trader:trader /app
WORKDIR /app

# Install system dependencies (git, curl, etc.) – nothing heavy needed for the bot.
RUN apt-get update && apt-get install -y --no-install-recommends gcc && rm -rf /var/lib/apt/lists/*

# Copy requirement file and install python deps.
COPY requirements.txt .
RUN pip install --no-cache-dir -r requirements.txt

# Copy the bot source tree.
COPY trading_bot ./trading_bot

# Switch to non‑root user
USER trader

# Entry point – you can override with a custom command when running the container.
ENTRYPOINT ["python", "-m", "trading_bot.trading_bot"]
