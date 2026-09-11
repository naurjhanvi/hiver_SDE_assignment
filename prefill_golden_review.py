"""Create AI-assisted, review-only proposals for the Xbox golden set.

Retrieval uses the training split only, so no golden conversation can be
retrieved. The generated columns are prefixed with ``proposed_`` and never
overwrite human labels in golden_candidates.csv.
"""

from __future__ import annotations

import csv
import math
import re
from collections import Counter, defaultdict
from pathlib import Path


SPLITS_DIR = Path("dataset/splits")
GOLDEN_PATH = SPLITS_DIR / "golden_candidates.csv"
TRAINING_PATH = SPLITS_DIR / "training_pairs.csv"
OUTPUT_PATH = SPLITS_DIR / "golden_review_proposals.csv"
TOKEN_PATTERN = re.compile(r"[a-z0-9]+")
VISUAL_PATTERN = re.compile(
    r"\b(video|image|picture|photo|screenshot|screen[ -]?shot|see (this|the)|look at (this|the)|watch (this|the))\b",
    re.IGNORECASE,
)


def tokens(text: str) -> list[str]:
    return TOKEN_PATTERN.findall(text.casefold())


def propose_intent(text: str, fallback: str) -> str:
    value = text.casefold()
    if any(term in value for term in ("banned", "ban ", "suspend", "enforcement", "hacked", "stolen", "unauthori", "cheating")):
        return "safety_enforcement_security"
    if any(term in value for term in ("game pass", "subscription", "auto-renew", "auto renew", "games with gold", "xbox live gold")):
        return "subscription_game_pass_gold"
    if any(term in value for term in ("refund", "charg", "bill", "payment", "purchas", "redeem", "code", "pre-order", "preorder", "order")):
        return "billing_codes_refunds"
    if any(term in value for term in ("sign in", "signin", "log in", "login", "password", "gamertag", "email", "profile", "my account")):
        return "account_access_profile"
    if any(term in value for term in ("network", "connection", "server", "outage", "offline", "wifi", "ethernet", "party chat", "xbox live")):
        return "connectivity_xbox_live"
    if any(term in value for term in ("controller", "headset", "warranty", "repair", "hdmi", " tv", "screen", "disc drive", "overheating")):
        return "console_accessory_display"
    if any(term in value for term in ("download", "install", "update", "dlc", "backward compatible", "back compat", "licence", "license")):
        return "game_content_download"
    if any(term in value for term in ("how do", "how can", "can i", "where can", "is it possible", "what is")):
        return "how_to_product_information"
    return fallback


def escalation_proposal(intent: str, text: str) -> tuple[str, str, str]:
    if VISUAL_PATTERN.search(text):
        return "no", "requires_visual_evidence", "Acknowledge the issue and route to a human who can inspect the attached visual evidence; do not claim to have viewed it."
    if intent == "safety_enforcement_security":
        return "no", "security_or_enforcement_review", "Acknowledge the concern and direct the customer to the secure enforcement or account-recovery path; do not adjudicate bans or request credentials."
    if intent == "billing_codes_refunds":
        return "no", "transaction_or_code_investigation", "Acknowledge the issue and route the customer to a private support channel for account and transaction details; do not promise a refund or replacement."
    if intent == "account_access_profile":
        return "no", "account_specific_verification", "Give only safe self-service guidance; use a private verified channel for recovery, ownership, or account-specific changes."
    if intent == "console_accessory_display":
        return "no", "hardware_or_repair_assessment", "Offer safe basic checks, then route unresolved faults or repair/warranty questions to human support."
    if intent == "other_or_needs_context":
        return "no", "insufficient_context", "Ask for a concise description of the issue and relevant non-sensitive details before attempting a resolution."
    if intent == "subscription_game_pass_gold":
        return "yes", "", "Provide concise, safe subscription-management or policy guidance. Escalate if the customer later reports a specific charge or account discrepancy."
    if intent == "how_to_product_information":
        return "yes", "", "Answer the question directly with grounded, general instructions and a clear next step."
    if intent == "connectivity_xbox_live":
        return "yes", "", "Provide safe general status checks or network troubleshooting; avoid claiming an outage unless supported by retrieved evidence."
    return "yes", "", "Give safe first-step troubleshooting grounded in similar historical support responses; escalate if the steps have already failed."


def main() -> None:
    with GOLDEN_PATH.open(encoding="utf-8", newline="") as file:
        golden = list(csv.DictReader(file))
    with TRAINING_PATH.open(encoding="utf-8", newline="") as file:
        training = list(csv.DictReader(file))

    document_frequency: Counter[str] = Counter()
    training_tokens: list[list[str]] = []
    inverted_index: dict[str, list[tuple[int, int]]] = defaultdict(list)
    document_norms: list[float] = []
    for index, row in enumerate(training):
        counts = Counter(tokens(row["customer_text"]))
        training_tokens.append(list(counts))
        document_frequency.update(counts)
        for term, count in counts.items():
            inverted_index[term].append((index, count))
    total_documents = len(training)
    idf = {term: math.log((1 + total_documents) / (1 + frequency)) + 1 for term, frequency in document_frequency.items()}
    for term_list in training_tokens:
        document_norms.append(math.sqrt(sum(idf[term] ** 2 for term in term_list)))

    output_rows = []
    for row in golden:
        query_counts = Counter(tokens(row["customer_text"]))
        query_norm = math.sqrt(sum((count * idf.get(term, 0)) ** 2 for term, count in query_counts.items()))
        scores: Counter[int] = Counter()
        for term, query_count in query_counts.items():
            weight = idf.get(term)
            if not weight:
                continue
            for document_index, document_count in inverted_index[term]:
                scores[document_index] += query_count * document_count * weight * weight
        ranked = sorted(
            ((score / (query_norm * document_norms[index]), index) for index, score in scores.items() if query_norm and document_norms[index]),
            reverse=True,
        )[:3]
        intent = propose_intent(row["customer_text"], row["sampling_stratum"])
        auto_handle, reason, notes = escalation_proposal(intent, row["customer_text"])
        evidence = " || ".join(
            f"score={score:.2f}; customer={training[index]['customer_text'][:180]}; Xbox={training[index]['xbox_reply_text'][:180]}"
            for score, index in ranked
        )
        output_rows.append(
            {
                **row,
                "proposed_intent": intent,
                "proposed_auto_handle": auto_handle,
                "proposed_escalation_reason": reason,
                "proposed_acceptable_reply_notes": notes,
                "retrieval_method": "TF-IDF cosine over training_pairs.csv only",
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
    print(f"Wrote {len(output_rows):,} review proposals to {OUTPUT_PATH}.")
    print("Human label columns remain unchanged and blank in the source golden candidate file.")


if __name__ == "__main__":
    main()
