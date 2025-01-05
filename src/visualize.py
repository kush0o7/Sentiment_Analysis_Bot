import matplotlib.pyplot as plt

def plot_data(stock_data, signals):
    plt.figure(figsize=(10, 5))
    plt.plot(stock_data.index, stock_data['Close'], label="Stock Price")
    plt.scatter(stock_data.index, stock_data['Close'], c=signals, cmap="coolwarm", label="Sentiment")
    plt.title("Stock Price vs Sentiment")
    plt.legend()
    plt.show()
