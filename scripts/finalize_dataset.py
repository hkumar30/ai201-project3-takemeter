"""
finalize_dataset.py
-------------------
Convert prelabeled.csv (after your human review pass) to the final dataset.csv
that the Colab notebook expects.

Rules:
  - Uses human_label if filled in, otherwise falls back to ai_prelabel.
  - Skips rows where the final label is not analysis / hot_take / reaction.
  - Skips rows with empty text.

Output: data/dataset.csv
Columns: text, label, notes

Run this AFTER you have completed your human review of prelabeled.csv.
"""

import csv
import os
from collections import Counter


def main():
    in_path = "data/prelabeled.csv"
    out_path = "data/dataset.csv"

    with open(in_path, "r", encoding="utf-8") as f:
        rows = list(csv.DictReader(f))

    valid_labels = {"analysis", "hot_take", "reaction"}
    final = []
    skipped = 0

    for row in rows:
        human = row.get("human_label", "").strip()
        ai = row.get("ai_prelabel", "").strip()
        label = human if human in valid_labels else ai
        text = row.get("text", "").strip()
        notes = row.get("notes", "").strip()

        if label not in valid_labels or not text:
            skipped += 1
            continue

        final.append({"text": text, "label": label, "notes": notes})

    with open(out_path, "w", newline="", encoding="utf-8") as f:
        writer = csv.DictWriter(f, fieldnames=["text", "label", "notes"])
        writer.writeheader()
        writer.writerows(final)

    dist = Counter(r["label"] for r in final)
    total = len(final)

    print(f"✓ Final dataset: {total} examples  (skipped {skipped})")
    print("\nLabel distribution:")
    for lbl, cnt in sorted(dist.items()):
        pct = 100 * cnt / total
        flag = " ⚠️  EXCEEDS 70% — collect more from other labels!" if pct > 70 else ""
        print(f"  {lbl:12s}: {cnt:4d}  ({pct:.1f}%){flag}")

    if total < 200:
        print(f"\n⚠️  Only {total} examples — need at least 200. Collect more before training.")


if __name__ == "__main__":
    main()
