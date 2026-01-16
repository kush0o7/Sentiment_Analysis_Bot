from typing import List, Dict

from textblob import TextBlob


def _label_for_polarity(pol: float) -> str:
    if pol > 0.1:
        return "positive"
    if pol < -0.1:
        return "negative"
    return "neutral"

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
        out.append({"tweet": t, "polarity": pol, "sentiment": _label_for_polarity(pol)})
    return out


def score_items(items: List[Dict], text_key: str = "title") -> List[Dict]:
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
        pol = float(TextBlob(text).sentiment.polarity)
        out.append(
            {
                "polarity": pol,
                "created_at": it.get("created_at"),
                "text": text,
            }
        )
    return out
