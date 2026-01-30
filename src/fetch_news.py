# src/fetch_news.py
from __future__ import annotations
from typing import List, Dict, Iterable
from datetime import datetime
from urllib.parse import quote
import hashlib, json, os, time

import feedparser
import requests
from email.utils import parsedate_to_datetime

# Optional, but helps parse many date formats
try:
    from dateutil import parser as du_parser  # type: ignore
except Exception:
    du_parser = None  # we'll survive without it

UA = (
    "Mozilla/5.0 (Macintosh; Intel Mac OS X 10_15_7) "
    "AppleWebKit/605.1.15 (KHTML, like Gecko) Version/17.0 Safari/605.1.15"
)


def google_news_rss_url(query: str, days: int = 7) -> str:
    """
    Build a Google News RSS search URL for the given query.
    Example: https://news.google.com/rss/search?q=apple+when:7d&hl=en-US&gl=US&ceid=US:en
    """
    q = quote(f"{query} when:{days}d")
    return f"https://news.google.com/rss/search?q={q}&hl=en-US&gl=US&ceid=US:en"

# ---------- date parsing helpers ----------

def _parse_any_date(entry: Dict) -> datetime:
    """
    Try multiple places/formats to recover a reliable timestamp for a feed entry.
    Order:
      1) structured *_parsed tuples (preferred)
      2) common string fields via email.utils and dateutil
      3) fallback to now (last resort)
    """
    # 1) Structured time tuples (time.struct_time-like)
    for key in ("published_parsed", "updated_parsed"):
        tt = entry.get(key)
        if tt:
            return datetime(*tt[:6])

    # 2) String fields in common feeds
    for key in ("published", "updated", "pubDate", "dc:date"):
        s = entry.get(key)
        if not s:
            continue
        # stdlib RFC822/HTTP-date parser
        try:
            dt = parsedate_to_datetime(s)
            if dt:
                return dt.replace(tzinfo=None)
        except Exception:
            pass
        # dateutil fallback (ISO 8601 / loose formats)
        if du_parser:
            try:
                dt = du_parser.parse(s)
                return dt.replace(tzinfo=None)
            except Exception:
                pass

    # 3) Give up — use "now" (try to avoid reaching here)
    return datetime.utcnow()

def _row(entry: Dict, source_url: str) -> Dict:
    dt = _parse_any_date(entry)
    title = (entry.get("title") or "").strip()
    link  = (entry.get("link")  or "").strip()
    hid = hashlib.sha1(f"{title}|{dt.isoformat()}|{source_url}".encode("utf-8")).hexdigest()
    return {
        "id": hid,
        "title": title,
        "created_at": dt.isoformat(),
        "link": link,
        "source": source_url,
    }

# ---------- parsing & fetching ----------

def _parse_feed_memory(data: bytes, url: str) -> List[Dict]:
    feed = feedparser.parse(data)
    out: List[Dict] = []
    for e in (feed.entries or []):
        out.append(_row(e, url))
    return out

def _parse_feed_url(url: str, limit_per: int, timeout=10, retries=2, sleep=1.0) -> List[Dict]:
    """
    Fetch a feed with requests (so we can set UA); on failure, fall back to
    letting feedparser fetch it directly. Returns up to limit_per items.
    """
    for _ in range(retries + 1):
        try:
            r = requests.get(url, headers={"User-Agent": UA}, timeout=timeout)
            if r.status_code == 200 and r.content:
                items = _parse_feed_memory(r.content, url)[:limit_per]
                if items:
                    return items
            # soft throttling / 403 / 429 / 503 – brief sleep and retry
            if r.status_code in (403, 429, 503):
                time.sleep(sleep)
                continue
        except Exception:
            time.sleep(sleep)
            continue

    # Fallback: some hosts still allow feedparser to fetch directly
    feed = feedparser.parse(url)
    out: List[Dict] = []
    for e in (feed.entries or [])[:limit_per]:
        out.append(_row(e, url))
    return out

# ---------- post-processing ----------

def _dedupe(items: Iterable[Dict]) -> List[Dict]:
    """
    Deduplicate by (lowercased title, date-only) to avoid repeated headlines
    across multiple feeds on the same day.
    """
    seen, out = set(), []
    for x in items:
        k = ((x.get("title", "").strip().lower()), x.get("created_at", "")[:10])
        if k in seen:
            continue
        seen.add(k)
        out.append(x)
    return out

# ---------- public API ----------

def fetch_multi_feeds(urls: List[str], limit_per: int = 200, cap: int = 1500) -> List[Dict]:
    items: List[Dict] = []
    for u in urls:
        try:
            items.extend(_parse_feed_url(u, limit_per))
        except Exception:
            continue
    items = _dedupe(items)
    # newest first
    items.sort(key=lambda r: r["created_at"], reverse=True)
    return items[:cap]

def save_news(items: List[Dict], path: str) -> None:
    os.makedirs(os.path.dirname(path), exist_ok=True)
    with open(path, "w", encoding="utf-8") as f:
        json.dump(items, f, ensure_ascii=False, indent=2)
