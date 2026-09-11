"""Generate golden-set review proposals using embedding-based semantic search.

Embeddings are created with sentence-transformers/all-MiniLM-L6-v2. Retrieval
is restricted to training_pairs.csv; golden items never retrieve their own
thread. This writes review proposals only and does not overwrite human labels.
"""

from __future__ import annotations

import csv
import sys
from pathlib import Path

USER_SITE = r"C:\Users\ranij\AppData\Roaming\Python\Python312\site-packages"
if USER_SITE not in sys.path:
    sys.path.append(USER_SITE)

import numpy as np
from sentence_transformers import SentenceTransformer

from prefill_golden_review import escalation_proposal, propose_intent


SPLITS_DIR = Path("dataset/splits")
GOLDEN_PATH = SPLITS_DIR / "golden_candidates.csv"
TRAINING_PATH = SPLITS_DIR / "training_pairs.csv"
OUTPUT_PATH = SPLITS_DIR / "golden_semantic_review_proposals.csv"
MODEL_NAME = "sentence-transformers/all-MiniLM-L6-v2"


def main() -> None:
    with GOLDEN_PATH.open(encoding="utf-8", newline="") as file:
        golden = list(csv.DictReader(file))
    with TRAINING_PATH.open(encoding="utf-8", newline="") as file:
        training = list(csv.DictReader(file))

    model = SentenceTransformer(MODEL_NAME)
    training_embeddings = model.encode(
        [row["customer_text"] for row in training],
        batch_size=128,
        normalize_embeddings=True,
        show_progress_bar=True,
    )
    golden_embeddings = model.encode(
        [row["customer_text"] for row in golden],
        batch_size=64,
        normalize_embeddings=True,
        show_progress_bar=True,
    )

    similarities = golden_embeddings @ training_embeddings.T
    output_rows = []
    for row_index, row in enumerate(golden):
        top_indices = np.argsort(similarities[row_index])[-3:][::-1]
        intent = propose_intent(row["customer_text"], row["sampling_stratum"])
        auto_handle, reason, notes = escalation_proposal(intent, row["customer_text"])
        evidence = " || ".join(
            f"cosine={similarities[row_index, index]:.3f}; customer={training[index]['customer_text'][:180]}; Xbox={training[index]['xbox_reply_text'][:180]}"
            for index in top_indices
        )
        output_rows.append(
            {
                **row,
                "proposed_intent": intent,
                "proposed_auto_handle": auto_handle,
                "proposed_escalation_reason": reason,
                "proposed_acceptable_reply_notes": notes,
                "retrieval_method": f"Embedding cosine similarity using {MODEL_NAME}; training_pairs.csv only",
                "retrieval_top3_evidence": evidence,
                "review_status": "needs_human_review",
            }
        )

    fields = list(golden[0]) + [
        "proposed_intent",
        "proposed_auto_handle",
        "proposed_escalation_reason",
        "proposed_acceptable_reply_notes",
        "retrieval_method",
        "retrieval_top3_evidence",
        "review_status",
    ]
    with OUTPUT_PATH.open("w", encoding="utf-8", newline="") as file:
        writer = csv.DictWriter(file, fieldnames=fields)
        writer.writeheader()
        writer.writerows(output_rows)
    print(f"Wrote {len(output_rows):,} embedding-based review proposals to {OUTPUT_PATH}.")


if __name__ == "__main__":
    main()
