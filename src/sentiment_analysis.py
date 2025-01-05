from textblob import TextBlob

def analyze_sentiment(tweets):
    results = []
    for tweet in tweets:
        analysis = TextBlob(tweet)
        polarity = analysis.sentiment.polarity
        sentiment = "positive" if polarity > 0 else "negative" if polarity < 0 else "neutral"
        results.append({"tweet": tweet, "polarity": polarity, "sentiment": sentiment})
    return results
