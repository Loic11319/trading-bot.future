"""Nachrichtenmodul: holt Schlagzeilen, bewertet die Stimmung, schreibt signals/news_signal.json"""
import json
import os
import time
from datetime import datetime, timezone

import feedparser
from vaderSentiment.vaderSentiment import SentimentIntensityAnalyzer

FEEDS = [
    "https://feeds.content.dowjones.io/public/rss/mw_topstories",
    "https://www.cnbc.com/id/100003114/device/rss/rss.html",
    "https://finance.yahoo.com/news/rssindex",
]

MAX_AGE_HOURS = 6          # nur Schlagzeilen der letzten 6 Stunden
BULL_LIMIT = 0.15          # Schwelle fuer "bullish"
BEAR_LIMIT = -0.15         # Schwelle fuer "bearish"

# Wenn eines dieser Woerter vorkommt, soll der Handelsbot vorsichtig sein
EVENT_WORDS = ["fed ", "fomc", "rate decision", "cpi", "inflation report",
               "jobs report", "nonfarm", "powell", "tariff", "war", "attack"]


def collect_headlines():
    now = time.time()
    headlines = []
    for url in FEEDS:
        try:
            feed = feedparser.parse(url)
        except Exception as err:
            print(f"Feed-Fehler {url}: {err}")
            continue
        for entry in feed.entries:
            title = entry.get("title", "").strip()
            if not title:
                continue
            published = entry.get("published_parsed")
            if published:
                age_hours = (now - time.mktime(published)) / 3600
                if age_hours > MAX_AGE_HOURS:
                    continue
            headlines.append(title)
    return list(dict.fromkeys(headlines))  # Duplikate entfernen


def build_signal(headlines):
    analyzer = SentimentIntensityAnalyzer()
    scores = [analyzer.polarity_scores(h)["compound"] for h in headlines]
    avg = sum(scores) / len(scores) if scores else 0.0

    if avg > BULL_LIMIT:
        mood = "bullish"
    elif avg < BEAR_LIMIT:
        mood = "bearish"
    else:
        mood = "neutral"

    events = [h for h in headlines if any(w in h.lower() for w in EVENT_WORDS)]

    return {
        "updated_utc": datetime.now(timezone.utc).isoformat(timespec="seconds"),
        "headline_count": len(headlines),
        "avg_score": round(avg, 3),
        "mood": mood,
        "caution": len(events) > 0,
        "event_headlines": events[:5],
    }


def main():
    headlines = collect_headlines()
    signal = build_signal(headlines)
    os.makedirs("signals", exist_ok=True)
    with open("signals/news_signal.json", "w", encoding="utf-8") as f:
        json.dump(signal, f, indent=2, ensure_ascii=False)
    print(json.dumps(signal, indent=2, ensure_ascii=False))


if __name__ == "__main__":
    main()
