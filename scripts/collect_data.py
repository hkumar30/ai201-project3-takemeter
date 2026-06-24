"""
collect_data.py
---------------
Collect r/formula1 comments from the PullPush archive API.
No Reddit developer account required.

Targets three thread types to ensure label diversity across
the analysis / hot_take / reaction taxonomy:
  - Race Thread posts      → high density of `reaction`
  - Day After Debrief      → high density of `analysis` and `hot_take`
  - Discussion / Opinion   → high density of `hot_take`

Output: data/raw_comments.csv
Columns: text, thread_type, permalink, score

Run this in Colab or locally before prelabel.py.
"""

import requests
import csv
import time
import os

BASE = "https://api.pullpush.io/reddit/search"
SUBREDDIT = "formula1"
MIN_LENGTH = 80       # characters — filters out one-liners
BATCH_SIZE = 10       # comments fetched per thread (keep small to avoid timeouts)
SLEEP = 1.5           # seconds between requests


def get_submissions(query: str, size: int = 15) -> list[dict]:
    """Return submission metadata matching a title keyword query."""
    params = {
        "subreddit": SUBREDDIT,
        "q": query,
        "size": size,
        "sort": "desc",
        "sort_type": "score",
        "fields": "id,title,score,created_utc",
    }
    r = requests.get(f"{BASE}/submission/", params=params, timeout=30)
    r.raise_for_status()
    return r.json().get("data", [])


def get_comments(link_id: str, size: int = BATCH_SIZE) -> list[dict]:
    """Return comments from a specific thread, filtered for minimum length."""
    params = {
        "link_id": f"t3_{link_id}",
        "size": size,
        "fields": "body,score,id,permalink",
    }
    r = requests.get(f"{BASE}/comment/", params=params, timeout=30)
    r.raise_for_status()
    raw = r.json().get("data", [])
    return [
        c for c in raw
        if len(c.get("body", "")) >= MIN_LENGTH
        and c.get("body") not in ("[deleted]", "[removed]", "")
    ]


def collect(query: str, target: int, thread_type_label: str) -> list[dict]:
    """Collect up to `target` comments from threads matching `query`."""
    collected = []
    submissions = get_submissions(query, size=20)
    for sub in submissions:
        if len(collected) >= target:
            break
        sid = sub.get("id", "")
        title = sub.get("title", "")[:70]
        if not sid:
            continue
        print(f"  [{thread_type_label}] {title}")
        comments = get_comments(sid)
        for c in comments:
            if len(collected) >= target:
                break
            collected.append({
                "text": c["body"].strip().replace("\n", " "),
                "thread_type": thread_type_label,
                "permalink": c.get("permalink", ""),
                "score": c.get("score", 0),
            })
        time.sleep(SLEEP)
    return collected


def main():
    os.makedirs("data", exist_ok=True)
    out = "data/raw_comments.csv"

    thread_configs = [
        ("Race Thread",        "race_thread",  100),   # → reaction
        ("Day After Debrief",  "debrief",       100),   # → analysis / hot_take
        ("Discussion",         "discussion",    100),   # → hot_take
    ]

    all_rows = []
    for query, label, target in thread_configs:
        print(f"\nCollecting from '{query}' (target {target})…")
        rows = collect(query, target, label)
        print(f"  → {len(rows)} comments collected.")
        all_rows.extend(rows)

    with open(out, "w", newline="", encoding="utf-8") as f:
        writer = csv.DictWriter(f, fieldnames=["text", "thread_type", "permalink", "score"])
        writer.writeheader()
        writer.writerows(all_rows)

    print(f"\n✓ Saved {len(all_rows)} raw comments to {out}")


if __name__ == "__main__":
    main()
