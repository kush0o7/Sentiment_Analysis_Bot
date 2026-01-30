# src/stock_data.py
import io
from datetime import datetime, timedelta
import pandas as pd
import yfinance as yf
import requests

_PERIOD_MULTIPLIERS = {
    "d": 1,
    "wk": 7,
    "mo": 30,
    "y": 365,
}


def _period_to_days(period: str) -> int | None:
    """
    Convert a Yahoo-style period string to an approximate day count.
    Examples: 60d, 6mo, 1y. Returns None for "max" or unknown formats.
    """
    if not period:
        return None
    p = period.strip().lower()
    if p == "max":
        return None
    for unit, mult in _PERIOD_MULTIPLIERS.items():
        if p.endswith(unit):
            try:
                n = int(p[: -len(unit)])
            except ValueError:
                return None
            return n * mult
    return None


def _yf_history(ticker: str, period: str):
    df = yf.Ticker(ticker).history(period=period, auto_adjust=False)
    df.index = pd.to_datetime(df.index)
    return df

def _stooq_symbol(ticker: str) -> str:
    """
    Stooq uses symbols like 'aapl.us', 'msft.us'. Keep dots if present.
    Indices like ^GSPC aren't available via this simple endpoint.
    """
    t = ticker.lower()
    if "." in t or t.startswith("^"):
        return t  # leave as-is; may not work for indices
    return f"{t}.us"

def _stooq_download(ticker: str, days: int = 365) -> pd.DataFrame:
    sym = _stooq_symbol(ticker)
    url = f"https://stooq.com/q/d/l/?s={sym}&i=d"
    resp = requests.get(url, timeout=15)
    resp.raise_for_status()
    # Stooq returns plain CSV: Date,Open,High,Low,Close,Volume
    df = pd.read_csv(io.StringIO(resp.text))
    if df.empty or "Date" not in df.columns:
        return pd.DataFrame()
    df["Date"] = pd.to_datetime(df["Date"])
    # Keep only recent window
    if days:
        cutoff = pd.Timestamp(datetime.utcnow().date() - timedelta(days=days))
        df = df[df["Date"] >= cutoff]
    df = df.set_index("Date").sort_index()
    # Match yfinance column names
    df = df.rename(columns={"Open": "Open", "High": "High", "Low": "Low",
                            "Close": "Close", "Volume": "Volume"})
    return df

def fetch_stock_data(ticker: str, period: str = "3mo") -> pd.DataFrame:
    """
    Try Yahoo Finance first; if it returns empty/invalid, fall back to Stooq CSV.
    """
    # 1) Yahoo Finance
    try:
        df = _yf_history(ticker, period)
        if not df.empty and "Close" in df.columns:
            return df
    except Exception as e:
        print(f"Failed to get ticker '{ticker}' via Yahoo: {e}")

    # 2) Stooq fallback (approximate period window)
    try:
        days = _period_to_days(period) or 365
        df = _stooq_download(ticker, days=days)
        if not df.empty and "Close" in df.columns:
            return df
        else:
            print(f"Stooq returned no rows for {ticker}")
    except Exception as e:
        print(f"Failed to get ticker '{ticker}' via Stooq: {e}")

    # 3) final empty frame
    return pd.DataFrame()
