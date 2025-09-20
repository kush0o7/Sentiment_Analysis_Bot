# src/main.py
import os
import json
from typing import Optional

# Make dotenv optional (not required for RSS pipeline)
try:
    from dotenv import load_dotenv  # type: ignore
except Exception:
    def load_dotenv(*args, **kwargs):
        return None
from fetch_news import fetch_multi_feeds, save_news
from sentiment_analysis import analyze_sentiment_texts
from stock_data import fetch_stock_data
from generate_signals import daily_sentiment_aggregate, generate_signals
from backtest import backtest_signals, grid_search
from visualize import plot_data

# Add your API keys here
API_KEY = "3zuGkjE1EhvxOwoMndb0xxZH3"
API_SECRET = "YNZqXgzcXehlzCEjzMbhFm4HV6EvbcBjueJ6eqGOYwBYDeSLta"
ACCESS_TOKEN = "1875855569258504192-umuOnwgd5FNmvHE7lqqUaQxw3DhjPX"
ACCESS_TOKEN_SECRET = "bIjUaxDLeWFJ6As4YOnjvmgZV9Y0g2x2viKyUY2ufPZQB"

if __name__ == "__main__":
    import argparse

    p = argparse.ArgumentParser()
    p.add_argument("--ticker", default="AAPL")
    p.add_argument("--period", default="6mo")
    p.add_argument("--limit-news", type=int, default=200)
    p.add_argument("--optimize", action="store_true")
    p.add_argument("--train-end", default=None, help="YYYY-MM-DD")
    p.add_argument("--buy-th", type=float, default=0.05)
    p.add_argument("--sell-th", type=float, default=-0.05)
    p.add_argument("--smooth", type=int, default=3)
    p.add_argument("--min-count", type=int, default=2)
    args = p.parse_args()

    run(
        ticker=args.ticker,
        period=args.period,
        limit_news=args.limit_news,
        optimize=args.optimize,
        train_end=args.train_end,
        buy_th=args.buy_th,
        sell_th=args.sell_th,
        smooth_window=args.smooth,
        min_count=args.min_count,
    )
