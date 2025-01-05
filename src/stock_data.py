import yfinance as yf

def fetch_stock_data(ticker, period="1mo"):
    stock = yf.Ticker(ticker)
    data = stock.history(period=period)
    return data

if __name__ == "__main__":
    # Test fetching stock data
    data = fetch_stock_data("AAPL")
    print(data.head())
