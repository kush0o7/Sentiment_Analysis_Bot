from fetch_tweets import fetch_tweets
from sentiment_analysis import analyze_sentiment
from stock_data import fetch_stock_data
from generate_signals import generate_signals
from visualize import plot_data

# Add your API keys here
API_KEY = "3zuGkjE1EhvxOwoMndb0xxZH3"
API_SECRET = "YNZqXgzcXehlzCEjzMbhFm4HV6EvbcBjueJ6eqGOYwBYDeSLta"
ACCESS_TOKEN = "1875855569258504192-umuOnwgd5FNmvHE7lqqUaQxw3DhjPX"
ACCESS_TOKEN_SECRET = "bIjUaxDLeWFJ6As4YOnjvmgZV9Y0g2x2viKyUY2ufPZQB"

if __name__ == "__main__":
    # Fetch and analyze tweets
    tweets = fetch_tweets(API_KEY, API_SECRET, ACCESS_TOKEN, ACCESS_TOKEN_SECRET, "stock market")
    sentiment_results = analyze_sentiment(tweets)

    # Fetch stock data
    stock_data = fetch_stock_data("AAPL")

    # Generate trading signals
    signals = generate_signals(sentiment_results, stock_data)

    # Visualize results
    plot_data(stock_data, signals)
