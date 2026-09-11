"""Print a diverse, provisional sample of Xbox customer-support pairs.

The broad buckets are for exploration only. They are intentionally not final
intent labels and should not be used for evaluation or model training.
"""

from __future__ import annotations

import csv
import re
import sys
from collections import defaultdict
from pathlib import Path


DATA_PATH = Path("dataset/xbox_conversations.csv")
RULES = [
    ("account_signin", r"account|sign.?in|login|password|gamertag|email|profile"),
    ("billing_purchase_refund", r"charg|bill|payment|refund|purchas|bought|order|pre.?order|money|price|code"),
    ("subscription_game_pass", r"game pass|subscription|renew|membership|gold|live subscription"),
    ("game_download_install", r"download|install|update|game|disc|dlc|redeem"),
    ("console_hardware", r"console|controller|headset|xbox one|xbox 360|hardware|repair|warranty"),
    ("connectivity_service", r"connect|network|server|outage|down|offline|wifi|internet|live is"),
    ("enforcement_security", r"banned|ban |suspend|enforcement|hacked|hack|stolen|unauthori"),
    ("how_to_policy", r"how (do|can|to)|where (do|can)|can i|is it possible|help me"),
    ("complaint_unclear", r"not work|still|issue|problem|help|why|wtf|terrible|broken"),
]


def clipped(text: str, limit: int = 260) -> str:
    return text.replace("\n", " ")[:limit]


def main() -> None:
    sys.stdout.reconfigure(encoding="utf-8", errors="replace")
    with DATA_PATH.open(encoding="utf-8", newline="") as file:
        rows = list(csv.DictReader(file))
    by_id = {row["tweet_id"]: row for row in rows}
    pairs = [
        (by_id[row["in_response_to_tweet_id"]], row)
        for row in rows
        if row["author_id"].casefold() == "xboxsupport"
        and row["in_response_to_tweet_id"] in by_id
        and by_id[row["in_response_to_tweet_id"]]["inbound"].casefold() == "true"
    ]

    buckets: dict[str, list[tuple[dict[str, str], dict[str, str]]]] = defaultdict(list)
    for customer, xbox in pairs:
        text = customer["text"].casefold()
        matches = [name for name, pattern in RULES if re.search(pattern, text)]
        buckets[matches[0] if matches else "other"].append((customer, xbox))

    print(f"DIRECT CUSTOMER-TO-XBOX PAIRS: {len(pairs):,}")
    for name in [name for name, _ in RULES] + ["other"]:
        print(f"\n### {name}: {len(buckets[name]):,}")
        for customer, xbox in buckets[name][:3]:
            print(f"C: {clipped(customer['text'])}\nR: {clipped(xbox['text'])}\n")


if __name__ == "__main__":
    main()
