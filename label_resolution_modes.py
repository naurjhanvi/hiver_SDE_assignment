"""Append rule-assisted historical-reply resolution modes to modelling splits.

These are evidence labels inferred from the historical XboxSupport response,
not customer intents or final golden-set labels. Each record retains a review
flag for audit.
"""

from __future__ import annotations

import csv
import re
from collections import Counter
from pathlib import Path


SPLITS = [Path("dataset/splits/training_pairs.csv"), Path("dataset/splits/development_pairs.csv")]


def label_reply(reply: str) -> tuple[str, str]:
    text = reply.casefold()
    if re.search(r"screenshot|screen ?shot|photo|picture|video|show us what.*screen|image", text):
        return "visual_evidence_required", "escalate"
    if re.search(r"enforcement|case review|suspension|suspend|ban |banned|code of conduct", text):
        return "enforcement_review", "escalate"
    if re.search(r"repair|warranty|service order|device service", text):
        return "repair_or_warranty_process", "escalate"
    if re.search(r"follow us.*dm|send.*dm|direct message|dm us|your gamertag|private", text):
        return "private_account_investigation", "escalate"
    if re.search(r"chat team|contact (?:our )?support|contact us|reach out.*chat", text):
        return "specialist_handoff", "escalate"
    if re.search(r"clarify|more (?:info|information)|description of (?:the )?issue|what.*seeing", text):
        return "needs_more_context", "escalate"
    if re.search(r"https?://|support\.xbox\.com|xbox\.com", text):
        return "public_documentation", "auto_handle_candidate"
    if re.search(r"restart|power cycle|unplug|settings|try|steps|clear.*cache|troubleshoot", text):
        return "public_troubleshooting", "auto_handle_candidate"
    return "general_or_unclear_reply", "review_required"


def process(path: Path) -> None:
    with path.open(encoding="utf-8", newline="") as file:
        rows = list(csv.DictReader(file))
        original_fields = list(rows[0]) if rows else []
    fields = original_fields + [field for field in ("proposed_resolution_mode", "proposed_handling_signal", "resolution_mode_review_status") if field not in original_fields]
    for row in rows:
        mode, signal = label_reply(row["xbox_reply_text"])
        row["proposed_resolution_mode"] = mode
        row["proposed_handling_signal"] = signal
        row["resolution_mode_review_status"] = "rule_assisted_needs_sample_review"
    temporary = path.with_suffix(".tmp")
    with temporary.open("w", encoding="utf-8", newline="") as file:
        writer = csv.DictWriter(file, fieldnames=fields)
        writer.writeheader()
        writer.writerows(rows)
    temporary.replace(path)
    print(f"{path.name}: {len(rows):,} rows; {dict(Counter(row['proposed_resolution_mode'] for row in rows))}")


def main() -> None:
    for path in SPLITS:
        process(path)


if __name__ == "__main__":
    main()
