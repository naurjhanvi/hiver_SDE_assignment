"""Download a focused, article-level Xbox Support corpus for the agent.

This deliberately collects a small set of public self-service and escalation
reference pages across the project taxonomy. It is not a mirror of the site.
"""

from __future__ import annotations

import json
from pathlib import Path
from urllib.request import Request, urlopen


OUTPUT_DIR = Path("dataset/xbox_support_webpages/articles")
MANIFEST_PATH = OUTPUT_DIR / "manifest.json"
BASE = "https://support.xbox.com/en-GB/help/"
ARTICLES = [
    ("subscription_cancellations_refunds", "subscriptions-billing/manage-subscriptions/cancel-recurring-billing-or-subscription", "subscription_game_pass_gold", "documented_self_service"),
    ("turn_on_recurring_billing", "subscriptions-billing/manage-subscriptions/turn-on-recurring-billing", "subscription_game_pass_gold", "documented_self_service"),
    ("manage_payment_options", "subscriptions-billing/billing-payment-updates/manage-payment-options-and-billing-address", "billing_codes_refunds", "documented_self_service"),
    ("billing_address_error", "subscriptions-billing/billing-payment-updates/billing-address-error", "billing_codes_refunds", "documented_self_service"),
    ("change_password", "account-profile/signin-security/change-microsoft-account-password", "account_access_profile", "documented_self_service"),
    ("change_sign_in_email", "account-profile/manage-account/change-email-sign-in-for-microsoft-account", "account_access_profile", "documented_self_service"),
    ("cant_sign_in_after_password_change", "account-profile/signin-security/cant-sign-in-after-password-changed-xbox-one", "account_access_profile", "documented_self_service"),
    ("network_settings", "hardware-network/connect-network/network-settings", "connectivity_xbox_live", "documented_self_service"),
    ("advanced_network_settings", "hardware-network/connect-network/advanced-network-settings", "connectivity_xbox_live", "documented_self_service"),
    ("party_chat_troubleshooting", "hardware-network/connect-network/troubleshoot-party-chat", "connectivity_xbox_live", "documented_self_service"),
    ("network_connection_errors", "hardware-network/connect-network/xbox-one-network-connection-errors", "connectivity_xbox_live", "documented_self_service"),
    ("multiplayer_connection_errors", "hardware-network/connect-network/xbox-one-multiplayer-connection-errors", "connectivity_xbox_live", "documented_self_service"),
    ("game_installation_problems", "games-apps/troubleshooting/troubleshoot-game-or-app-installation-problems-on-xbox-one", "game_content_download", "documented_self_service"),
    ("slow_game_downloads", "games-apps/troubleshooting/troubleshoot-slow-game-or-app-downloads-on-xbox-one", "game_content_download", "documented_self_service"),
    ("digital_games", "games-apps/troubleshooting/digital-games", "game_content_download", "documented_self_service"),
    ("xbox_enforcement_faq", "family-online-safety/enforcement/xbox-enforcement-action-faq", "safety_enforcement_security", "human_or_specialist_review"),
    ("enforcement_notification", "family-online-safety/enforcement/how-youre-notified-of-xbox-enforcement-action", "safety_enforcement_security", "human_or_specialist_review"),
]


def main() -> None:
    OUTPUT_DIR.mkdir(parents=True, exist_ok=True)
    manifest = []
    for article_id, path, intent, handling in ARTICLES:
        url = BASE + path
        request = Request(url, headers={"User-Agent": "Mozilla/5.0 (research; XboxSupportAgent/1.0)"})
        with urlopen(request, timeout=30) as response:
            content = response.read()
            status = response.status
        filename = f"{article_id}.html"
        (OUTPUT_DIR / filename).write_bytes(content)
        manifest.append({"doc_id": article_id, "url": url, "file": filename, "intent_scope": intent, "handling_capability": handling, "http_status": status})
        print(f"Downloaded {article_id} ({len(content):,} bytes)")
    MANIFEST_PATH.write_text(json.dumps(manifest, indent=2), encoding="utf-8")
    print(f"Wrote manifest to {MANIFEST_PATH}")


if __name__ == "__main__":
    main()
