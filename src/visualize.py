import matplotlib.pyplot as plt
import pandas as pd

def plot_data(stock_df: pd.DataFrame, save_path: str | None = None) -> None:
    """
    Plot close price and mark Buy/Sell days with markers.
    If save_path is provided, saves PNG; otherwise shows window.
    """
    close = stock_df["Close"]
    sigs = stock_df["signal"]

    plt.figure(figsize=(11, 5))
    plt.plot(close.index, close.values, label="Close")

    buys = stock_df[sigs == "Buy"]
    sells = stock_df[sigs == "Sell"]

    plt.scatter(buys.index, buys["Close"], marker="^", s=120, label="Buy")
    plt.scatter(sells.index, sells["Close"], marker="v", s=120, label="Sell")


    plt.title("Price with Sentiment-Based Signals")
    plt.xlabel("Date"); plt.ylabel("Price")
    plt.legend(); plt.tight_layout()

    if save_path:
        plt.savefig(save_path, dpi=150, bbox_inches="tight")
    else:
        plt.show()
