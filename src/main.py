# src/main.py
import os
import json
from typing import Optional

# dotenv is optional; if present it will load .env into os.environ
try:
    from dotenv import load_dotenv  # type: ignore
    load_dotenv()
except Exception:
    pass

# safe env config (don't hardcode secrets here)
API_KEY = os.getenv("API_KEY")
API_SECRET = os.getenv("API_SECRET")
ACCESS_TOKEN = os.getenv("ACCESS_TOKEN")
ACCESS_TOKEN_SECRET = os.getenv("ACCESS_TOKEN_SECRET")
X_BEARER_TOKEN = os.getenv("X_BEARER_TOKEN")  # optional if you use tweets

# project imports (these are your modules)
from fetch_news import fetch_multi_feeds, save_news
from sentiment_analysis import analyze_sentiment_texts
from stock_data import fetch_stock_data
from generate_signals import daily_sentiment_aggregate, generate_signals
from backtest import backtest_signals, grid_search
# your file is named "visualiz.py" in the repo; import accordingly
from visualize import plot_data

# local helper: small safe default feeds list (replace with feeds you like)
def _default_feeds_for(ticker: str) -> list:
    # NOTE: many financial sites change RSS formats. Replace with feeds you trust.
    return [
        f"https://finance.yahoo.com/rss/headline?s={ticker}",
        # you can add more reliable RSS URLs here, e.g. CNBC/Investing/etc.
    ]

def run(
    ticker: str = "AAPL",
    period: str = "6mo",
    limit_news: int = 200,
    optimize: bool = False,
    train_end: Optional[str] = None,
    buy_th: float = 0.05,
    sell_th: float = -0.05,
    smooth_window: int = 3,
    min_count: int = 2,
    feeds: Optional[str] = None,   # comma-separated feed URLs
):
    """
    Orchestrate the pipeline:
      1) fetch news (RSS) using fetch_multi_feeds
      2) analyze sentiment on titles
      3) aggregate daily sentiment
      4) fetch price data
      5) generate signals
      6) backtest and plot
    """
    from textblob import TextBlob  # local import so requirements are only needed when running

    # 1) build feed list
    if feeds:
        feed_list = [u.strip() for u in feeds.split(",") if u.strip()]
    else:
        feed_list = _default_feeds_for(ticker)

    print("Fetching news from feeds:", feed_list)
    items = fetch_multi_feeds(feed_list, limit_per=limit_news, cap=2000)
    if not items:
        print("No news items found from feeds. Try passing --feeds with URLs or use tweet-mode.")
        return

    # 2) analyze sentiment on each title using TextBlob (ensures created_at preserved)
    scored_items = []
    for it in items:
        title = (it.get("title") or "").strip()
        created_at = it.get("created_at", None)
        if not title:
            continue
        pol = float(TextBlob(title).sentiment.polarity)
        scored_items.append({
            "polarity": pol,
            "created_at": created_at,
        })

    # optional: save raw scored items for inspection
    try:
        save_news(scored_items, "data/scored_headlines.json")
    except Exception:
        pass

    # 3) aggregate daily mean & daily count
    daily_mean, daily_count = daily_sentiment_aggregate(scored_items)

    # 4) get price data
    print(f"Fetching price data for {ticker} period={period} ...")
    stock_df = fetch_stock_data(ticker, period=period)
    if stock_df.empty:
        print("Failed to fetch price data for", ticker)
        return

    # 5) optionally optimize parameters using grid search (requires train_end)
    if optimize and train_end:
        print("Running grid search optimization (this may take a while)...")
        best = grid_search(
            daily_mean, daily_count, stock_df, train_end,
            buy_range=(0.02, 0.03, 0.05, 0.08, 0.1),
            sell_range=(-0.02, -0.03, -0.05, -0.08, -0.1),
            smooth_range=(2, 3, 5),
            mincnt_range=(1, 2, 3),
            fee_bp=5.0,
        )
        print("Grid-search best params:", best)
        if best:
            buy_th = best.get("buy", buy_th)
            sell_th = best.get("sell", sell_th)
            smooth_window = int(best.get("smooth", smooth_window))
            min_count = int(best.get("min_count", min_count))

    # 6) generate signals on the full stock_df
    out_df = generate_signals(
        daily_mean, stock_df,
        buy_th=buy_th, sell_th=sell_th,
        smooth_window=smooth_window, min_count=min_count,
        daily_count=daily_count
    )

        # 7) backtest and report
    res, result_df = backtest_signals(out_df, price_col="Close", signal_col="signal")
    print("Backtest results:")
    print(f" Total return: {res.total_return}")
    print(f" CAGR: {res.cagr}")
    print(f" Sharpe: {res.sharpe}")
    print(f" Max DD: {res.max_dd}")
    print(f" Trades: {res.trades}")

    # Ensure data directory exists
    os.makedirs("data", exist_ok=True)

    # 8) plot & save inside data/
    plot_path = os.path.join("data", f"results_{ticker}.png")
    try:
        plot_data(result_df, save_path=plot_path)
        print("Saved plot to", plot_path)
    except Exception as e:
        print("Plotting failed:", e)
        # fallback: save CSV to data/
        csv_path = os.path.join("data", f"results_{ticker}.csv")
        result_df.to_csv(csv_path)
        print(f"Wrote results CSV to {csv_path}")


if __name__ == "__main__":
    import argparse

    p = argparse.ArgumentParser(description="Run Sentiment Analysis Bot pipeline (RSS -> signals -> backtest)")
    p.add_argument("--ticker", default="AAPL")
    p.add_argument("--period", default="6mo")
    p.add_argument("--limit-news", type=int, default=200)
    p.add_argument("--optimize", action="store_true", help="Run grid search optimization (requires --train-end)")
    p.add_argument("--train-end", default=None, help="YYYY-MM-DD (end of training window for optimization)")
    p.add_argument("--buy-th", type=float, default=0.05)
    p.add_argument("--sell-th", type=float, default=-0.05)
    p.add_argument("--smooth", type=int, default=3)
    p.add_argument("--min-count", type=int, default=2)
    p.add_argument("--feeds", default=None, help="Comma-separated RSS feed URLs to use instead of defaults")

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
        feeds=args.feeds,
    )
