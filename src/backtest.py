import math
from dataclasses import dataclass
import numpy as np
import pandas as pd
from typing import Dict, Tuple, Iterable

@dataclass
class BTResult:
    total_return: float
    cagr: float
    sharpe: float
    max_dd: float
    trades: int

def _exposure_from_signal(signal: pd.Series) -> pd.Series:
    signal = signal.astype(str)
    exp = []
    pos = 0
    for s in signal:
        if s == "Buy":
            if pos == 0:
                pos = 1
        elif s == "Sell":
            if pos == 1:
                pos = 0
        exp.append(pos)
    return pd.Series(exp, index=signal.index, dtype=float)


def _equity_curve(price: pd.Series, signal: pd.Series, fee_bp: float = 0.0) -> pd.Series:
    """
    Simple daily close-to-close backtest:
      - Long when signal == "Buy"
      - Flat when signal == "Sell" (exit to cash)
      - Otherwise keep previous exposure
    Transaction cost modeled as basis points on position flip.
    """
    price = price.astype(float)
    exp = _exposure_from_signal(signal)

    ret = price.pct_change().fillna(0.0)

    # apply fees when exposure changes (entry/exit)
    churn = exp.diff().abs().fillna(0.0)  # 1 on enter/exit
    fees = churn * (fee_bp / 1e4)

    strat_ret = exp.shift(1).fillna(0.0) * ret - fees
    equity = (1 + strat_ret).cumprod()
    return equity

def _metrics(equity: pd.Series, freq: int = 252) -> Dict:
    daily_ret = equity.pct_change().dropna()
    total_return = equity.iloc[-1] - 1.0
    years = max(1e-9, (equity.index[-1] - equity.index[0]).days / 365.25)
    cagr = (equity.iloc[-1]) ** (1/years) - 1 if years > 0 else 0.0
    vol = daily_ret.std() * math.sqrt(freq)
    sharpe = (daily_ret.mean() * freq) / (vol if vol > 1e-12 else np.nan)
    peak = equity.cummax()
    dd = (equity / peak - 1.0).min()
    return dict(total_return=float(total_return), cagr=float(cagr),
                sharpe=float(sharpe) if not math.isnan(sharpe) else float("nan"),
                max_dd=float(dd))

def backtest_signals(df: pd.DataFrame, price_col="Close", signal_col="signal", fee_bp: float = 5.0) -> Tuple[BTResult, pd.DataFrame]:
    equity = _equity_curve(df[price_col], df[signal_col], fee_bp=fee_bp)
    m = _metrics(equity)
    exp = _exposure_from_signal(df[signal_col])
    trades = int((exp.diff().abs() > 0).sum())
    res = BTResult(total_return=m["total_return"], cagr=m["cagr"], sharpe=m["sharpe"], max_dd=m["max_dd"], trades=trades)
    out = df.copy()
    out["equity"] = equity
    return res, out

def grid_search(
    daily_mean: pd.Series,
    daily_count: pd.Series,
    stock_df: pd.DataFrame,
    train_end: str,
    buy_range: Iterable[float] = (0.02, 0.03, 0.05, 0.08, 0.1),
    sell_range: Iterable[float] = (-0.02, -0.03, -0.05, -0.08, -0.1),
    smooth_range: Iterable[int] = (2, 3, 5),
    mincnt_range: Iterable[int] = (1, 2, 3),
    fee_bp: float = 5.0,
) -> Dict:
    from generate_signals import generate_signals

    split = pd.to_datetime(train_end)
    train_idx = stock_df.index <= split

    best = None
    for b in buy_range:
        for s in sell_range:
            if s >= 0 or b <= 0:
                continue
            for w in smooth_range:
                for k in mincnt_range:
                    train_df = generate_signals(daily_mean, stock_df.loc[train_idx],
                                                buy_th=b, sell_th=s, smooth_window=w,
                                                min_count=k, daily_count=daily_count)
                    res, _ = backtest_signals(train_df, fee_bp=fee_bp)
                    score = res.sharpe  # optimize Sharpe
                    cur = dict(buy=b, sell=s, smooth=w, min_count=k, sharpe=score, cagr=res.cagr, dd=res.max_dd)
                    if best is None or (score > best["sharpe"]):
                        best = cur
    return best or {}
