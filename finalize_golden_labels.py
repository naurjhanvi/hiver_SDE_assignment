"""Promote AI-assisted golden proposals into final label columns.

Existing non-empty human entries take priority. The resulting file keeps the
customer input and retrieval evidence, but removes proposal/review columns.
"""

from __future__ import annotations

import csv
from pathlib import Path


PATH = Path("dataset/splits/golden_eval_review.csv")
PROMOTIONS = {
    "intent": "proposed_intent",
    "auto_handle": "proposed_auto_handle",
    "escalation_reason": "proposed_escalation_reason",
    "acceptable_reply_notes": "proposed_acceptable_reply_notes",
}
REMOVE_COLUMNS = set(PROMOTIONS.values()) | {"review_status"}


def main() -> None:
    with PATH.open(encoding="utf-8", newline="") as file:
        rows = list(csv.DictReader(file))
        fields = list(rows[0]) if rows else []
    promoted_counts = {field: 0 for field in PROMOTIONS}
    preserved_counts = {field: 0 for field in PROMOTIONS}
    for row in rows:
        for final_field, proposal_field in PROMOTIONS.items():
            if row.get(final_field, "").strip():
                preserved_counts[final_field] += 1
            else:
                row[final_field] = row.get(proposal_field, "")
                promoted_counts[final_field] += 1
    final_fields = [field for field in fields if field not in REMOVE_COLUMNS]
    temporary = PATH.with_suffix(".tmp")
    with temporary.open("w", encoding="utf-8", newline="") as file:
        writer = csv.DictWriter(file, fieldnames=final_fields)
        writer.writeheader()
        writer.writerows({field: row.get(field, "") for field in final_fields} for row in rows)
    temporary.replace(PATH)
    print(f"Finalized {len(rows):,} golden rows.")
    print(f"Promoted blank fields: {promoted_counts}")
    print(f"Preserved existing fields: {preserved_counts}")


if __name__ == "__main__":
    main()
