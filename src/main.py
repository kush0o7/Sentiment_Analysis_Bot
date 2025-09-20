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


def run(
    ticker: str = "AAPL",
    period: str = "3mo",
    limit_news: int = 200,
    optimize: bool = True,
    train_end: Optional[str] = None,
    buy_th: float = 0.05,
    sell_th: float = -0.05,
    smooth_window: int = 3,
    min_count: int = 2,
) -> None:
    """
    Pipeline:
      1) Fetch Yahoo Finance RSS headlines (no API keys)
      2) TextBlob sentiment per headline
      3) Daily sentiment aggregate (mean + count)
      4) Fetch price data (Yahoo -> Stooq fallback)
      5) Generate signals (thresholds + smoothing + min headline count)
      6) Optional param optimization on a training window
      7) Backtest (PnL, CAGR, Sharpe, MaxDD, Trades)
      8) Save CSV + plot
    """
    load_dotenv()

    print(f"Mode: NEWS via Yahoo Finance RSS for {ticker}")
    # Build a richer feed set for older coverage
    # --- in src/main.py ---
# richer, redundant sources (Google News often gives 100s)
# note: adding multiple queries increases coverage
    urls = [
    # Yahoo Finance (per-ticker)
        f"https://feeds.finance.yahoo.com/rss/2.0/headline?s={ticker}&region=US&lang=en-US",

    # Google News by ticker and company name, last 12 months
        f"https://news.google.com/rss/search?q={ticker}%20stock%20OR%20shares%20OR%20earnings%20when:12m&hl=en-US&gl=US&ceid=US:en",
        f"https://news.google.com/rss/search?q={ticker}%20when:12m&hl=en-US&gl=US&ceid=US:en",
    # if you know the company name, add it (works great for MSFT/Microsoft)
        f"https://news.google.com/rss/search?q=Microsoft%20stock%20OR%20shares%20OR%20earnings%20when:12m&hl=en-US&gl=US&ceid=US:en" if ticker.upper()=="MSFT" else
        f"https://news.google.com/rss/search?q={ticker}%20Inc%20OR%20Corporation%20when:12m&hl=en-US&gl=US&ceid=US:en",

    # Investing.com (broad tech & stocks)
        "https://www.investing.com/rss/news_25.rss",
        "https://www.investing.com/rss/news_285.rss",

    # The Motley Fool (general stock news)
        "https://www.fool.com/feeds/index.aspx",

    # CNBC Top News (broad market)
        "https://www.cnbc.com/id/100003114/device/rss/rss.html",
    ]


    news = fetch_multi_feeds(urls, limit_per=200, cap=3000)


# simple logging so you can verify sources
    from collections import Counter
    by_src = Counter(n.get("source","?") for n in news)
    print("Sources:", dict(by_src))
    print("Fetched news items:", len(news))

    save_news(news, "data/news.json")

    if not news:
        raise RuntimeError("No news items returned from RSS.")
    save_news(news, "data/news.json")

    # Sentiment per headline
    per_item = analyze_sentiment_texts([n["title"] for n in news])
    # Attach timestamps for daily aggregation
    for i, n in enumerate(news):
        per_item[i]["created_at"] = n["created_at"]

    # Daily mean + headline count
    daily_mean, daily_count = daily_sentiment_aggregate(per_item)
    print("Daily sentiment points:", len(daily_mean))
    if len(daily_mean):
        print("Recent sentiment (last 10 days):")
        print(daily_mean.tail(10).round(3))


    # Prices (with internal fallback)
    stock = fetch_stock_data(ticker, period=period)
    if stock.empty:
        print(f"Price data empty for {ticker}. Nothing to do.")
        return

    # ---- Optional optimization (Sharpe on training window) ----
    if optimize and train_end:
        best = grid_search(
            daily_mean,
            daily_count,
            stock,
            train_end=train_end,
        )
        if best:
            print("Best params on train:", best)
            buy_th = best["buy"]
            sell_th = best["sell"]
            smooth_window = best["smooth"]
            min_count = best["min_count"]

    # Signals (apply chosen or optimized params)
    merged = generate_signals(
        daily_mean,
        stock,
        buy_th=buy_th,
        sell_th=sell_th,
        smooth_window=smooth_window,
        min_count=min_count,
        daily_count=daily_count,
    )
    print("Signal counts:", merged["signal"].value_counts().to_dict())


    # Backtest on full sample
    res, bt_df = backtest_signals(merged, fee_bp=5.0)
    print(
        f"Backtest — Total: {res.total_return:.2%}  CAGR: {res.cagr:.2%}  "
        f"Sharpe: {res.sharpe:.2f}  MaxDD: {res.max_dd:.2%}  Trades: {res.trades}"
    )

    # Save CSV and plot
    os.makedirs("data", exist_ok=True)
    out_csv = f"data/{ticker}_merged.csv"
    out_png = f"data/{ticker}_news_plot.png"
    bt_df.to_csv(out_csv)
    plot_data(bt_df, save_path=out_png)
    print(f"Saved plot -> {out_png}")
    print(f"Saved merged data -> {out_csv}")


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
