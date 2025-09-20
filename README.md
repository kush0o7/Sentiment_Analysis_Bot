# Sentiment Analysis Bot

This project builds a **news-driven trading strategy**:

* Collects market-related headlines from multiple **free RSS feeds** (Yahoo Finance, Google News, CNBC, Motley Fool, Investing.com, etc.).
* Uses **TextBlob** to score the sentiment of each headline.
* Aggregates sentiment by day and smooths it to reduce noise.
* Aligns the sentiment series with stock-market trading days and generates **Buy / Sell / Hold** signals based on configurable thresholds.
* Backtests the signals against free historical price data (Yahoo Finance / Stooq fallback) and plots the resulting equity curve.

Everything runs with **free data sources**—no paid API keys required.

---

## ✨ Features
- **Free data pipeline** – Fetches and deduplicates headlines from multiple RSS feeds.
- **Daily sentiment aggregation** – Smooths sentiment scores and filters out low-headline days.
- **Signal generation** – Creates Buy/Sell/Hold signals with adjustable thresholds, smoothing window, and headline-count minimum.
- **Backtesting** – Computes total return, CAGR, Sharpe ratio, max drawdown, trade count, and plots price with trade markers.
- **Configurable** – Command-line options let you tune thresholds, smoothing, and training window.

---

## 🛠 Requirements
- Python **3.11+**
- See [`requirements.txt`](requirements.txt) for the full list of Python dependencies  
  (main libraries: `pandas`, `numpy`, `textblob`, `feedparser`, `matplotlib`, `requests`).

---

## 🚀 Installation

1. **Clone the repository**
   ```bash
   git clone https://github.com/your-repo/sentiment-analysis-bot.git
   cd sentiment-analysis-bot
