"""
prelabel.py
-----------
Pre-label raw comments using Groq (llama-3.3-70b-versatile).

Input:  data/raw_comments.csv   (from collect_data.py)
Output: data/prelabeled.csv

Output columns:
  text            — the comment text
  thread_type     — which thread type it came from
  score           — Reddit score
  ai_prelabel     — label assigned by Groq
  ai_rationale    — one-sentence rationale from Groq
  human_label     — LEAVE BLANK; fill in during your review pass
  notes           — LEAVE BLANK; fill in for any difficult cases

IMPORTANT: human_label is the ground truth for training.
Review every row. Override any ai_prelabel you disagree with.
"""

import csv
import json
import os
import time

from dotenv import load_dotenv
from groq import Groq

load_dotenv()
client = Groq(api_key=os.environ["GROQ_API_KEY"])

SYSTEM_PROMPT = """You are annotating r/formula1 Reddit comments for a 3-class text classification dataset.

Assign exactly one label per comment:

  analysis  — The comment constructs a structured argument using specific, verifiable F1 evidence
               (lap times, sector splits, tire strategy windows, championship math, car specs,
               historical comparisons with named statistics). The evidence is load-bearing:
               remove it and the argument collapses.

  hot_take  — A bold, confident claim about a driver, team, regulation, or era stated without
               meaningful supporting evidence. A stat may appear, but it is decorative —
               used to sound credible rather than to genuinely reason.

  reaction  — An immediate emotional or expressive response to a specific, identifiable F1 event
               (crash, overtake, penalty, qualifying lap, result, announcement). The comment
               expresses a feeling in the moment rather than arguing a position.

Decision rules:
- Stat present but one-dimensional and stripped of context → hot_take
- Comment is event-triggered and expressive but makes a pattern-based claim → hot_take
- Evidence survives cross-examination (not cherry-picked, supports a structured argument) → analysis
- Expressing a feeling tied to a specific moment with no argument → reaction

Respond with JSON only, no extra text:
{"label": "<analysis|hot_take|reaction>", "rationale": "<one sentence max>"}"""


def prelabel(text: str) -> tuple[str, str]:
    response = client.chat.completions.create(
        model="llama-3.3-70b-versatile",
        messages=[
            {"role": "system", "content": SYSTEM_PROMPT},
            {"role": "user", "content": f"Comment:\n{text}"},
        ],
        temperature=0.0,
        max_tokens=120,
        response_format={"type": "json_object"},
    )
    result = json.loads(response.choices[0].message.content)
    label = result.get("label", "").strip()
    rationale = result.get("rationale", "").strip()
    if label not in ("analysis", "hot_take", "reaction"):
        label = "ERROR"
    return label, rationale


def main():
    in_path = "data/raw_comments.csv"
    out_path = "data/prelabeled.csv"

    with open(in_path, "r", encoding="utf-8") as f:
        rows = list(csv.DictReader(f))

    results = []
    errors = 0

    for i, row in enumerate(rows):
        text = row["text"]
        print(f"[{i+1}/{len(rows)}] Labeling…", end=" ", flush=True)
        try:
            label, rationale = prelabel(text)
            print(label)
        except Exception as e:
            label, rationale = "ERROR", str(e)
            errors += 1
            print(f"ERROR: {e}")

        results.append({
            "text": text,
            "thread_type": row.get("thread_type", ""),
            "score": row.get("score", ""),
            "ai_prelabel": label,
            "ai_rationale": rationale,
            "human_label": "",
            "notes": "",
        })
        time.sleep(0.4)

    fieldnames = ["text", "thread_type", "score", "ai_prelabel", "ai_rationale", "human_label", "notes"]
    with open(out_path, "w", newline="", encoding="utf-8") as f:
        writer = csv.DictWriter(f, fieldnames=fieldnames)
        writer.writeheader()
        writer.writerows(results)

    from collections import Counter
    dist = Counter(r["ai_prelabel"] for r in results)
    total = len(results)
    print(f"\n✓ Saved {total} pre-labeled comments to {out_path}")
    print(f"  Errors: {errors}")
    print("\nAI pre-label distribution:")
    for lbl, cnt in sorted(dist.items()):
        pct = 100 * cnt / total
        flag = " ⚠️  >70%" if pct > 70 else ""
        print(f"  {lbl:12s}: {cnt:4d}  ({pct:.1f}%){flag}")


if __name__ == "__main__":
    main()
