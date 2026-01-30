import os
import json
from datetime import datetime, timedelta, timezone
from typing import List, Dict
import tweepy
from dotenv import load_dotenv

load_dotenv()

def fetch_tweets(query: str, max_results: int = 200, lookback_days: int = 7) -> List[Dict]:
    """
    ONLINE MODE:
      Fetch recent English tweets using X/Twitter API v2 via Tweepy Client.
      Requires .env with X_BEARER_TOKEN.
    Returns a list of dicts: {"id","text","created_at"} in ISO8601.
    """
    bearer = os.getenv("X_BEARER_TOKEN")
    if not bearer:
        raise RuntimeError(
            "X_BEARER_TOKEN not set. Either add it to .env for online mode "
            "or run offline mode (see main.py)."
        )

    client = tweepy.Client(bearer_token=bearer, wait_on_rate_limit=True)
    end_time = datetime.now(timezone.utc)
    start_time = end_time - timedelta(days=lookback_days)

    tweets: List[Dict] = []
    seen_ids = set()
    next_token = None
    while len(tweets) < max_results:
        batch = min(100, max_results - len(tweets))
        resp = client.search_recent_tweets(
            query=f"({query}) lang:en -is:retweet",
            start_time=start_time,
            end_time=end_time,
            max_results=batch,
            tweet_fields=["id", "text", "created_at", "lang"],
            next_token=next_token,
        )
        if resp.data:
            for t in resp.data:
                if t.id in seen_ids:
                    continue
                seen_ids.add(t.id)
                tweets.append(
                    {
                        "id": t.id,
                        "text": t.text,
                        "created_at": t.created_at.isoformat(),
                    }
                )

        if not resp.meta or not resp.meta.get("next_token"):
            break
        next_token = resp.meta.get("next_token")

    return tweets

def save_tweets(tweets: List[Dict], path: str = "data/tweets.json") -> None:
    os.makedirs(os.path.dirname(path), exist_ok=True)
    with open(path, "w", encoding="utf-8") as f:
        json.dump(tweets, f, ensure_ascii=False, indent=2)
