from textblob import TextBlob
from typing import List, Dict

def analyze_sentiment_texts(texts: List[str]) -> List[Dict]:
    """
    Input: list of raw tweet texts
    Output: list of dicts: {"tweet","polarity","sentiment"}
    polarity in [-1, 1].
    """
    out: List[Dict] = []
    for t in texts:
        blob = TextBlob(t)
        pol = float(blob.sentiment.polarity)
        if pol > 0.1:
            label = "positive"
        elif pol < -0.1:
            label = "negative"
        else:
            label = "neutral"
        out.append({"tweet": t, "polarity": pol, "sentiment": label})
    return out
