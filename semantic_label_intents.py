"""Assign intent labels to train/dev customer messages by semantic prototypes.

This is deliberately independent of the golden evaluation set. It embeds each
customer message and compares it with compact intent definitions/examples, then
adds a confidence score and a weak-label audit flag.
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


SPLITS = [Path("dataset/splits/training_pairs.csv"), Path("dataset/splits/development_pairs.csv")]
MODEL_NAME = "sentence-transformers/all-MiniLM-L6-v2"
INTENT_PROTOTYPES = {
    "account_access_profile": "Cannot sign in to my Xbox or Microsoft account. Password, account email, gamertag, profile, family account, account ownership, account recovery.",
    "billing_codes_refunds": "Xbox charge, payment, billing, refund, purchase, order, pre-order, payment method, redeemed code, missing paid content.",
    "subscription_game_pass_gold": "Xbox Game Pass, Xbox Live Gold, subscription, membership, auto renewal, recurring billing, Games with Gold.",
    "game_content_download": "Xbox game or app download, installation, update, DLC, game license, backward compatibility, digital game, game content.",
    "console_accessory_display": "Xbox console, controller, headset, storage, HDMI, television screen, display issue, hardware repair, warranty.",
    "connectivity_xbox_live": "Xbox network connection, Wi-Fi, Ethernet, Xbox Live outage, multiplayer, party chat, servers, online service.",
    "safety_enforcement_security": "Xbox ban, suspension, enforcement action, cheating report, hacked or stolen account, unauthorized account activity.",
    "how_to_product_information": "How to use an Xbox feature, settings, captures, compatibility, availability, policy, general product information.",
    "other_or_needs_context": "Unclear Xbox support request, vague follow-up, needs more context, unrelated feedback, greeting.",
}


def process(path: Path, model: SentenceTransformer, prototype_embeddings: np.ndarray, labels: list[str]) -> None:
    with path.open(encoding="utf-8", newline="") as file:
        rows = list(csv.DictReader(file))
        existing_fields = list(rows[0]) if rows else []
    embeddings = model.encode([row["customer_text"] for row in rows], batch_size=128, normalize_embeddings=True, show_progress_bar=True)
    scores = embeddings @ prototype_embeddings.T
    best_indices = np.argmax(scores, axis=1)
    final_fields = existing_fields + [field for field in ("intent", "intent_semantic_confidence", "intent_label_source") if field not in existing_fields]
    for row, best_index, score_row in zip(rows, best_indices, scores):
        row["intent"] = labels[int(best_index)]
        row["intent_semantic_confidence"] = f"{float(score_row[best_index]):.3f}"
        row["intent_label_source"] = "semantic_prototype_weak_label"
    temporary = path.with_suffix(".tmp")
    with temporary.open("w", encoding="utf-8", newline="") as file:
        writer = csv.DictWriter(file, fieldnames=final_fields)
        writer.writeheader()
        writer.writerows(rows)
    temporary.replace(path)
    print(f"Labelled {len(rows):,} rows in {path.name}.")


def main() -> None:
    model = SentenceTransformer(MODEL_NAME)
    labels = list(INTENT_PROTOTYPES)
    prototype_embeddings = model.encode(list(INTENT_PROTOTYPES.values()), normalize_embeddings=True)
    for path in SPLITS:
        process(path, model, prototype_embeddings, labels)


if __name__ == "__main__":
    main()
