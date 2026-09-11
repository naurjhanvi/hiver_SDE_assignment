"""Remove original Xbox replies and sampling hints from the golden review file.

The golden evaluation input must be only the incoming customer message. Similar
historical Xbox replies remain available in retrieval_top3_evidence because they
are training-set evidence, not the held-out conversation's own answer.
"""

from __future__ import annotations

import csv
from pathlib import Path


PATH = Path("dataset/splits/golden_semantic_review_proposals.csv")
OUTPUT_PATH = Path("dataset/splits/golden_eval_review.csv")
KEEP_FIELDS = [
    "thread_id",
    "customer_tweet_id",
    "customer_author_id",
    "created_at",
    "customer_text",
    "intent",
    "auto_handle",
    "escalation_reason",
    "acceptable_reply_notes",
    "annotator_notes",
    "proposed_intent",
    "proposed_auto_handle",
    "proposed_escalation_reason",
    "proposed_acceptable_reply_notes",
    "retrieval_method",
    "retrieval_top3_evidence",
    "review_status",
]


def main() -> None:
    with PATH.open(encoding="utf-8", newline="") as file:
        rows = list(csv.DictReader(file))
    with OUTPUT_PATH.open("w", encoding="utf-8", newline="") as file:
        writer = csv.DictWriter(file, fieldnames=KEEP_FIELDS)
        writer.writeheader()
        writer.writerows({field: row.get(field, "") for field in KEEP_FIELDS} for row in rows)
    print(f"Wrote {len(rows):,} sanitized golden review rows to {OUTPUT_PATH}.")
    print("Removed held-out Xbox reply fields and sampling_stratum.")


if __name__ == "__main__":
    main()
