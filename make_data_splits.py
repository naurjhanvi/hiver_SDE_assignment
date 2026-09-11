"""Create leakage-resistant XboxSupport train, development, and golden splits.

The golden split is a 200-row annotation template. Its label columns are
deliberately blank so it remains independent from later modelling work.
"""

from __future__ import annotations

import csv
import random
from collections import defaultdict
from pathlib import Path


INPUT_PATH = Path("dataset/xbox_conversations.csv")
OUTPUT_DIR = Path("dataset/splits")
RANDOM_SEED = 42
GOLD_TARGETS = {
    "account_access_profile": 20,
    "billing_codes_refunds": 20,
    "subscription_game_pass_gold": 20,
    "game_content_download": 20,
    "console_accessory_display": 20,
    "connectivity_xbox_live": 20,
    "safety_enforcement_security": 20,
    "how_to_product_information": 20,
    "other_or_needs_context": 40,
}


def preliminary_stratum(text: str) -> str:
    """Choose a broad sampling bucket; this is not a gold intent label."""
    text = text.casefold()
    if any(token in text for token in ("banned", "suspend", "enforcement", "hacked", "stolen", "unauthori", "cheating")):
        return "safety_enforcement_security"
    if any(token in text for token in ("game pass", "subscription", "auto-renew", "auto renew", "games with gold", "xbox live gold")):
        return "subscription_game_pass_gold"
    if any(token in text for token in ("refund", "charg", "bill", "payment", "purchas", "redeem", "code", "pre-order", "preorder", "order")):
        return "billing_codes_refunds"
    if any(token in text for token in ("sign in", "signin", "log in", "login", "password", "gamertag", "email", "profile", "my account")):
        return "account_access_profile"
    if any(token in text for token in ("network", "connection", "server", "outage", "offline", "wifi", "ethernet", "party chat", "xbox live")):
        return "connectivity_xbox_live"
    if any(token in text for token in ("controller", "headset", "warranty", "repair", "hdmi", "tv", "screen", "disc drive", "overheating")):
        return "console_accessory_display"
    if any(token in text for token in ("download", "install", "update", "dlc", "backward compatible", "back compat", "licence", "license")):
        return "game_content_download"
    if any(token in text for token in ("how do", "how can", "can i", "where can", "is it possible", "what is")):
        return "how_to_product_information"
    return "other_or_needs_context"


def resolve_thread_id(tweet_id: str, rows_by_id: dict[str, dict[str, str]], cache: dict[str, str]) -> str:
    if tweet_id in cache:
        return cache[tweet_id]
    visited: list[str] = []
    current = tweet_id
    seen: set[str] = set()
    while current in rows_by_id and current not in seen:
        if current in cache:
            root = cache[current]
            break
        seen.add(current)
        visited.append(current)
        parent = rows_by_id[current]["in_response_to_tweet_id"].strip()
        if not parent or parent not in rows_by_id:
            root = current
            break
        current = parent
    else:
        root = min(seen) if seen else tweet_id
    for visited_id in visited:
        cache[visited_id] = root
    return root


def write_pairs(path: Path, pairs: list[dict[str, str]]) -> None:
    fields = [
        "thread_id",
        "customer_tweet_id",
        "customer_author_id",
        "created_at",
        "customer_text",
        "xbox_reply_tweet_id",
        "xbox_reply_text",
    ]
    with path.open("w", encoding="utf-8", newline="") as file:
        writer = csv.DictWriter(file, fieldnames=fields, extrasaction="ignore")
        writer.writeheader()
        writer.writerows(pairs)


def write_golden_template(path: Path, pairs: list[dict[str, str]]) -> None:
    fields = [
        "thread_id",
        "customer_tweet_id",
        "customer_author_id",
        "created_at",
        "customer_text",
        "xbox_reply_tweet_id",
        "xbox_reply_text",
        "sampling_stratum",
        "intent",
        "auto_handle",
        "escalation_reason",
        "acceptable_reply_notes",
        "annotator_notes",
    ]
    with path.open("w", encoding="utf-8", newline="") as file:
        writer = csv.DictWriter(file, fieldnames=fields)
        writer.writeheader()
        for pair in pairs:
            writer.writerow({**pair, "intent": "", "auto_handle": "", "escalation_reason": "", "acceptable_reply_notes": "", "annotator_notes": ""})


def main() -> None:
    with INPUT_PATH.open(encoding="utf-8", newline="") as file:
        rows = list(csv.DictReader(file))
    rows_by_id = {row["tweet_id"]: row for row in rows}
    root_cache: dict[str, str] = {}

    pairs: list[dict[str, str]] = []
    for xbox_reply in rows:
        parent_id = xbox_reply["in_response_to_tweet_id"].strip()
        if xbox_reply["author_id"].casefold() != "xboxsupport" or parent_id not in rows_by_id:
            continue
        customer = rows_by_id[parent_id]
        if customer["inbound"].casefold() != "true":
            continue
        pairs.append(
            {
                "thread_id": resolve_thread_id(customer["tweet_id"], rows_by_id, root_cache),
                "customer_tweet_id": customer["tweet_id"],
                "customer_author_id": customer["author_id"],
                "created_at": customer["created_at"],
                "customer_text": customer["text"],
                "xbox_reply_tweet_id": xbox_reply["tweet_id"],
                "xbox_reply_text": xbox_reply["text"],
                "sampling_stratum": preliminary_stratum(customer["text"]),
            }
        )

    rng = random.Random(RANDOM_SEED)
    candidates_by_stratum: dict[str, list[dict[str, str]]] = defaultdict(list)
    for pair in pairs:
        candidates_by_stratum[pair["sampling_stratum"]].append(pair)
    for candidates in candidates_by_stratum.values():
        rng.shuffle(candidates)

    golden: list[dict[str, str]] = []
    golden_threads: set[str] = set()
    for stratum, target in GOLD_TARGETS.items():
        selected = 0
        for pair in candidates_by_stratum[stratum]:
            if pair["thread_id"] in golden_threads:
                continue
            golden.append(pair)
            golden_threads.add(pair["thread_id"])
            selected += 1
            if selected == target:
                break
        if selected != target:
            raise RuntimeError(f"Could only select {selected} unique threads for {stratum}; expected {target}.")

    remaining = [pair for pair in pairs if pair["thread_id"] not in golden_threads]
    pairs_by_thread: dict[str, list[dict[str, str]]] = defaultdict(list)
    for pair in remaining:
        pairs_by_thread[pair["thread_id"]].append(pair)
    remaining_threads = list(pairs_by_thread)
    rng.shuffle(remaining_threads)
    development_target = round(len(remaining) * 0.10)
    development_threads: set[str] = set()
    development_count = 0
    for thread_id in remaining_threads:
        if development_count >= development_target:
            break
        development_threads.add(thread_id)
        development_count += len(pairs_by_thread[thread_id])

    development = [pair for pair in remaining if pair["thread_id"] in development_threads]
    training = [pair for pair in remaining if pair["thread_id"] not in development_threads]
    OUTPUT_DIR.mkdir(parents=True, exist_ok=True)
    write_golden_template(OUTPUT_DIR / "golden_candidates.csv", golden)
    write_pairs(OUTPUT_DIR / "development_pairs.csv", development)
    write_pairs(OUTPUT_DIR / "training_pairs.csv", training)

    print(f"Direct customer-to-XboxSupport pairs: {len(pairs):,}")
    print(f"Golden annotation candidates: {len(golden):,} pairs across {len(golden_threads):,} threads")
    print(f"Development: {len(development):,} pairs across {len(development_threads):,} threads")
    print(f"Training/retrieval: {len(training):,} pairs")
    print(f"No train/dev pair shares a golden thread: {not any(pair['thread_id'] in golden_threads for pair in training + development)}")


if __name__ == "__main__":
    main()
