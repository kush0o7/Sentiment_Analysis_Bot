# src/generate_signals.py
from __future__ import annotations

from typing import List, Dict, Tuple, Optional
import pandas as pd


def daily_sentiment_aggregate(items: List[Dict]) -> Tuple[pd.Series, pd.Series]:
    """
    Aggregate per-headline sentiment into daily mean and daily count.

    items: list of dicts with at least keys {"polarity", "created_at"}
    Returns:
      (daily_mean, daily_count) both indexed by pandas.DatetimeIndex (date-only)
    """
    if not items:
        return pd.Series(dtype=float), pd.Series(dtype=float)

    df = pd.DataFrame(items).copy()
    df["created_at"] = pd.to_datetime(df["created_at"])
    df["date"] = df["created_at"].dt.date

    daily = (
        df.groupby("date")["polarity"]
          .agg(["mean", "count"])
          .sort_index()
    )
    daily.index = pd.to_datetime(daily.index)  # to DatetimeIndex
    return daily["mean"], daily["count"]


def generate_signals(
    daily_mean: pd.Series,
    stock_df: pd.DataFrame,
    *,
    buy_th: float = 0.06,
    sell_th: float = -0.06,
    smooth_window: int = 3,
    min_count: int = 2,
    daily_count: Optional[pd.Series] = None,
    ffill_limit: int = 3,              # carry news at most N trading days
) -> pd.DataFrame:
    """
    Convert daily sentiment into discrete trade signals for the price series.

    Steps
    -----
    1) Align daily sentiment to the trading calendar (stock_df.index).
    2) Smooth sentiment on the calendar with a rolling mean.
    3) Gate sentiment by a rolling headline-count minimum (optional).
    4) Limit forward-carry of news to `ffill_limit` trading days, no backfill.
    5) Create an exposure regime with hysteresis:
         - sentiment >  buy_th  -> target long (1)
         - sentiment <  sell_th -> target flat (0)
         - otherwise keep previous exposure
       Emit "Buy"/"Sell" only when the regime flips; else "Hold".

    Returns
    -------
    DataFrame like `stock_df` with added columns:
      - 'sentiment'  (smoothed, aligned to trading days)
      - 'signal'     ('Buy'/'Sell'/'Hold')
    """
    out = stock_df.copy()
    if out.empty:
        out["sentiment"] = pd.Series(dtype=float)
        out["signal"] = "Hold"
        return out

    cal = out.index  # trading DateTimeIndex
    # --- 1) align sentiment to trading calendar
    s = daily_mean.copy().sort_index()
    s.index = pd.to_datetime(s.index)
    s = s.reindex(cal)

    # --- 2) smooth ON the calendar
    s = s.rolling(window=smooth_window, min_periods=1).mean()

    # --- 3) optional headline-count gate
    if daily_count is not None and len(daily_count):
        cnt = daily_count.copy()
        cnt.index = pd.to_datetime(cnt.index)
        cnt = cnt.reindex(cal).fillna(0)
        cnt_roll = cnt.rolling(window=smooth_window, min_periods=1).sum()
        # if we don't have enough headlines in the window, treat as neutral
        s = s.where(cnt_roll >= min_count, 0.0)

    # --- 4) limit forward fill (no backfill)
    s = s.ffill(limit=ffill_limit).fillna(0.0)

    # --- 5) exposure with hysteresis and discrete flips
    exp_target = pd.Series(index=cal, dtype=float)
    exp_target[:] = float("nan")
    exp_target[s > buy_th] = 1.0
    exp_target[s < sell_th] = 0.0

    # keep previous exposure inside the band
    exp = exp_target.ffill().fillna(0.0)

    # flip points -> discrete signals
    flip = exp.diff().fillna(exp)         # +1 on enter, -1 on exit, 0 otherwise
    sig = pd.Series("Hold", index=cal, dtype=object)
    sig[flip > 0] = "Buy"
    sig[flip < 0] = "Sell"

    out["sentiment"] = s
    out["signal"] = sig
    return out
