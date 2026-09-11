"""Create a transparent redirection catalog from selected public Xbox Support URLs.

The live support site is client-rendered, so saved direct downloads are app-shell
HTML rather than article text. This catalog intentionally supports only safe
article redirection. Do not use it to generate undocumented procedural steps.
"""

from __future__ import annotations

import json
import shutil
from pathlib import Path


ARTICLES_DIR = Path("dataset/xbox_support_webpages/articles")
MANIFEST_PATH = ARTICLES_DIR / "manifest.json"
OUTPUT_PATH = Path("dataset/xbox_support_webpages/official_article_catalog.jsonl")

TITLES = {
    "subscription_cancellations_refunds": "XBOX subscription cancellations and refunds",
    "turn_on_recurring_billing": "Turn on recurring billing for your XBOX subscription",
    "manage_payment_options": "Update your billing address and payment options",
    "billing_address_error": "A billing address error occurs when making a purchase on your XBOX console",
    "change_password": "Change your Microsoft account password",
    "change_sign_in_email": "Change the email address or phone number for your Microsoft account",
    "cant_sign_in_after_password_change": "Can't sign in after changing your password on XBOX",
    "network_settings": "Network settings on XBOX",
    "advanced_network_settings": "Advanced network settings on XBOX",
    "party_chat_troubleshooting": "Troubleshoot XBOX party chat",
    "network_connection_errors": "Troubleshoot XBOX network connection errors",
    "multiplayer_connection_errors": "Troubleshoot XBOX multiplayer connection errors",
    "game_installation_problems": "Troubleshoot game or app installation problems on XBOX",
    "slow_game_downloads": "Troubleshoot slow game or app downloads on XBOX",
    "digital_games": "Troubleshoot digital games on XBOX",
    "xbox_enforcement_faq": "XBOX enforcement action FAQ",
    "enforcement_notification": "How you are notified of an XBOX enforcement action",
}


def main() -> None:
    manifest = json.loads(MANIFEST_PATH.read_text(encoding="utf-8"))
    records = []
    for item in manifest:
        records.append(
            {
                "doc_id": item["doc_id"],
                "title": TITLES[item["doc_id"]],
                "url": item["url"],
                "intent_scope": item["intent_scope"],
                "handling_capability": item["handling_capability"],
                "use_rule": (
                    "May support an auto-handled redirection only when the customer request is clear, "
                    "requires no private account/transaction review, and has no diagnostic media."
                    if item["handling_capability"] == "documented_self_service"
                    else "Use to explain the official process, but escalate individual reviews, appeals, or account-specific enforcement cases."
                ),
                "content_status": "URL and article title verified through Xbox Support live search; full article body unavailable from saved client-rendered HTML.",
            }
        )
    with OUTPUT_PATH.open("w", encoding="utf-8") as file:
        for record in records:
            file.write(json.dumps(record, ensure_ascii=False) + "\n")
    shutil.rmtree(ARTICLES_DIR)
    print(f"Wrote {len(records):,} article catalog records to {OUTPUT_PATH}.")
    print("Removed client-rendered article shells because they contained no usable article text.")


if __name__ == "__main__":
    main()
