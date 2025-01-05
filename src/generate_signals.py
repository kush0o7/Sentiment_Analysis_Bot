def generate_signals(sentiment_data, stock_data):
    signals = []
    for date, row in stock_data.iterrows():
        sentiment_score = sentiment_data.get(date, 0)
        if sentiment_score > 0.5:
            signal = "Buy"
        elif sentiment_score < -0.5:
            signal = "Sell"
        else:
            signal = "Hold"
        signals.append({"date": date, "signal": signal})
    return signals
