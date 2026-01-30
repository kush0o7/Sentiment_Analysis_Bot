from __future__ import annotations

from datetime import datetime
from pathlib import Path
from typing import Dict, List, Optional

import pandas as pd
from fastapi import FastAPI, HTTPException, Query
from fastapi.middleware.cors import CORSMiddleware

from backtest import backtest_signals
from fetch_news import fetch_multi_feeds, google_news_rss_url
from generate_signals import daily_sentiment_aggregate, generate_signals
from sentiment_analysis import score_items
from stock_data import fetch_stock_data
from sec_data import find_cik_by_ticker, search_cik_by_name, fetch_13f_holdings_by_cik, fetch_form4_insiders_by_cik

DATA_DIR = Path("data")


def _default_feeds_for(ticker: str) -> list[str]:
    return [
        f"https://finance.yahoo.com/rss/headline?s={ticker}",
        google_news_rss_url(ticker, days=7),
    ]


def _normalize_df(df: pd.DataFrame) -> pd.DataFrame:
    out = df.copy()
    if isinstance(out.index, pd.DatetimeIndex):
        out = out.reset_index().rename(columns={"index": "Date"})
    if "Date" not in out.columns:
        out["Date"] = out.index
    out["Date"] = pd.to_datetime(out["Date"]).dt.date.astype(str)
    return out


def _stats_from_df(df: pd.DataFrame) -> Dict:
    if df.empty:
        return {
            "rows": 0,
            "range": None,
            "last_close": None,
            "total_return": None,
            "equity_return": None,
            "last_signal": None,
        }
    first = df.iloc[0]
    last = df.iloc[-1]
    total_return = None
    if "Close" in df.columns and pd.notna(first["Close"]) and pd.notna(last["Close"]):
        total_return = float(last["Close"]) / float(first["Close"]) - 1
    equity_return = None
    if "equity" in df.columns and pd.notna(first.get("equity")) and pd.notna(last.get("equity")):
        equity_return = float(last["equity"]) / float(first["equity"]) - 1
    return {
        "rows": int(len(df)),
        "range": f"{first['Date']} → {last['Date']}",
        "last_close": float(last["Close"]) if "Close" in df.columns else None,
        "total_return": total_return,
        "equity_return": equity_return,
        "last_signal": str(last.get("signal", "")) if "signal" in df.columns else None,
    }


def _run_pipeline(
    ticker: str,
    period: str = "6mo",
    limit_news: int = 200,
    feeds: Optional[List[str]] = None,
    sentiment_model: str = "vader",
) -> pd.DataFrame:
    feed_list = feeds if feeds else _default_feeds_for(ticker)
    items = fetch_multi_feeds(feed_list, limit_per=limit_news, cap=2000)

    scored_items = score_items(items, text_key="title", model=sentiment_model) if items else []
    daily_mean, daily_count = daily_sentiment_aggregate(scored_items)

    stock_df = fetch_stock_data(ticker, period=period)
    if stock_df.empty or len(stock_df) < 2:
        raise RuntimeError(f"Not enough price data for {ticker}")

    out_df = generate_signals(
        daily_mean,
        stock_df,
        daily_count=daily_count,
    )
    _, result_df = backtest_signals(out_df, price_col="Close", signal_col="signal")
    return _normalize_df(result_df)


app = FastAPI(title="Sentiment Analysis Bot API", version="1.0")
app.add_middleware(
    CORSMiddleware,
    allow_origins=["http://localhost:5173"],
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)


@app.get("/api/health")
def health() -> Dict:
    return {"ok": True, "ts": datetime.utcnow().isoformat()}


@app.get("/api/tickers")
def tickers() -> Dict:
    if not DATA_DIR.exists():
        return {"tickers": []}
    files = sorted(DATA_DIR.glob("*_merged.csv"))
    tickers = [f.stem.replace("_merged", "") for f in files]
    return {"tickers": tickers}


@app.get("/api/data")
def data(
    ticker: str = Query(..., min_length=1, max_length=10),
    period: str = Query("6mo", min_length=2, max_length=10),
    refresh: bool = Query(False),
    sentiment_model: str = Query("vader"),
) -> Dict:
    ticker = ticker.upper()
    DATA_DIR.mkdir(exist_ok=True)
    cache_path = DATA_DIR / f"{ticker}_merged.csv"

    if cache_path.exists() and not refresh:
        df = pd.read_csv(cache_path)
        df = _normalize_df(df)
        return {"ticker": ticker, "source": "cache", "data": df.to_dict(orient="records"), "stats": _stats_from_df(df)}

    try:
        df = _run_pipeline(ticker=ticker, period=period, sentiment_model=sentiment_model)
    except Exception as exc:
        raise HTTPException(status_code=500, detail=str(exc)) from exc

    df.to_csv(cache_path, index=False)
    return {"ticker": ticker, "source": "live", "data": df.to_dict(orient="records"), "stats": _stats_from_df(df)}


@app.get("/api/entity")
def entity(
    name: str = Query(..., min_length=2, max_length=80),
    days: int = Query(14, ge=1, le=90),
    sentiment_model: str = Query("vader"),
) -> Dict:
    feed = google_news_rss_url(name, days=days)
    items = fetch_multi_feeds([feed], limit_per=200, cap=1000)
    scored_items = score_items(items, text_key="title", model=sentiment_model) if items else []
    daily_mean, daily_count = daily_sentiment_aggregate(scored_items)
    df = pd.DataFrame(
        {
            "Date": daily_mean.index.date.astype(str),
            "sentiment": daily_mean.values,
            "count": daily_count.values,
        }
    )
    return {"name": name, "source": "news", "data": df.to_dict(orient="records")}


@app.get("/api/holdings")
def holdings(
    name: str = Query(..., min_length=2, max_length=80),
    max_rows: int = Query(25, ge=5, le=100),
) -> Dict:
    matches = search_cik_by_name(name, limit=1)
    if not matches:
        return {"name": name, "matches": [], "holdings": []}
    cik = matches[0]["cik"]
    data = fetch_13f_holdings_by_cik(cik, max_rows=max_rows)
    return {"name": name, "cik": cik, "match": matches[0], **data}


@app.get("/api/insiders")
def insiders(
    ticker: str = Query(..., min_length=1, max_length=10),
    max_filings: int = Query(5, ge=1, le=20),
) -> Dict:
    cik = find_cik_by_ticker(ticker)
    if not cik:
        return {"ticker": ticker, "cik": None, "filings": []}
    data = fetch_form4_insiders_by_cik(cik, max_filings=max_filings)
    return {"ticker": ticker, "cik": cik, **data}


if __name__ == "__main__":
    import uvicorn

    uvicorn.run(app, host="0.0.0.0", port=8000)
