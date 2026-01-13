# 📈 Sentiment Analysis Bot – News-Driven Trading Strategy

A **Python-based quantitative research project** that builds and backtests a **news-driven trading strategy** using free, publicly available data sources.

The system ingests financial news headlines, performs **sentiment analysis**, converts sentiment into **trading signals**, and evaluates performance via a **backtesting engine**.

> ⚠️ This project is for **research and educational purposes only**. It does not constitute financial advice.

---

## 🔍 Problem Statement

Market news influences short-term price movements, but raw headlines are noisy and unstructured.

This project explores:
- Can **aggregate news sentiment** be transformed into **systematic trading signals**?
- How does a sentiment-based strategy perform compared to passive exposure?
- What are the limitations of free data and simple NLP methods in trading?

---

## 🧠 Approach & Pipeline

1. **News Ingestion**
   - Collects headlines from **free RSS feeds** (Yahoo Finance, CNBC, etc.)
   - Deduplicates repeated headlines across sources

2. **Sentiment Analysis**
   - Uses **TextBlob** to score headline polarity
   - Aggregates sentiment **daily** and applies smoothing

3. **Signal Generation**
   - Converts sentiment into **Buy / Sell / Hold**
   - Configurable thresholds, smoothing window, and minimum headline count

4. **Backtesting**
   - Uses historical prices from **Yahoo Finance**
   - Automatic fallback to **Stooq** when Yahoo data is unavailable
   - Computes performance metrics:
     - Total Return
     - CAGR
     - Sharpe Ratio
     - Max Drawdown
     - Trade Count

5. **Visualization**
   - Plots price series with Buy/Sell markers
   - Saves results for offline inspection

---

## ✨ Features

- 📡 **Fully free data pipeline** (no paid APIs required)
- 🧪 **Research-grade backtesting engine**
- 🔁 **Configurable strategy parameters**
- 📊 **Clear visual outputs**
- 🧱 **Modular, extensible architecture**

---

## 🛠 Tech Stack

- **Python 3.11**
- pandas, numpy
- TextBlob (NLP)
- feedparser, requests (data ingestion)
- yfinance + Stooq fallback (market data)
- matplotlib (visualization)

---

## 📁 Project Structure

Sentiment_Analysis_Bot/
│
├── src/
│ ├── main.py # Pipeline entry point (CLI)
│ ├── fetch_news.py # RSS ingestion & deduplication
│ ├── fetch_tweets.py # Optional Twitter/X ingestion
│ ├── sentiment_analysis.py # TextBlob sentiment scoring
│ ├── generate_signals.py # Signal logic
│ ├── backtest.py # Backtesting engine
│ ├── stock_data.py # Market data fetch + fallback
│ └── visualize.py # Plotting utilities
│
├── data/ # Generated outputs (ignored by git)
├── requirements.txt
├── README.md
└── .gitignore


---

## 🚀 How to Run

### 1️⃣ Clone the repository
```bash
git clone https://github.com/kush007/Sentiment_Analysis_Bot.git
cd Sentiment_Analysis_Bot
2️⃣ Create and activate virtual environment
bash
Copy code
python3.11 -m venv venv
source venv/bin/activate
3️⃣ Install dependencies
bash
Copy code
pip install -r requirements.txt
python -m textblob.download_corpora
4️⃣ Run the strategy
bash
Copy code
python src/main.py --ticker AAPL --period 6mo
Example:

bash
Copy code
python src/main.py --ticker TSLA --period 1y --buy-th 0.02 --sell-th -0.02
Outputs are saved in the data/ directory.