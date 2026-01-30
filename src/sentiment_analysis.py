from typing import List, Dict

from textblob import TextBlob
from vaderSentiment.vaderSentiment import SentimentIntensityAnalyzer

_VADER = SentimentIntensityAnalyzer()


def _label_for_polarity(pol: float) -> str:
    if pol > 0.1:
        return "positive"
    if pol < -0.1:
        return "negative"
    return "neutral"

def _score_text(text: str, model: str) -> float:
    if model == "textblob":
        return float(TextBlob(text).sentiment.polarity)
    if model == "vader":
        return float(_VADER.polarity_scores(text)["compound"])
    raise ValueError(f"Unknown sentiment model: {model}")


def analyze_sentiment_texts(texts: List[str], model: str = "vader") -> List[Dict]:
    """
    Input: list of raw tweet texts
    Output: list of dicts: {"tweet","polarity","sentiment"}
    polarity in [-1, 1].
    """
    out: List[Dict] = []
    for t in texts:
        pol = _score_text(t, model)
        out.append({"tweet": t, "polarity": pol, "sentiment": _label_for_polarity(pol)})
    return out


def score_items(items: List[Dict], text_key: str = "title", model: str = "vader") -> List[Dict]:
    """
    Score a list of items that carry text + optional created_at timestamp.

    Returns list of dicts with:
      - polarity
      - created_at
      - text
    """
    out: List[Dict] = []
    for it in items:
        text = (it.get(text_key) or "").strip()
        if not text:
            continue
        pol = _score_text(text, model)
        out.append(
            {
                "polarity": pol,
                "created_at": it.get("created_at"),
                "text": text,
            }
        )
    return out
