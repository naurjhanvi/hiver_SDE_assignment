"""Runnable, retrieval-grounded Xbox first-line support agent.

Uses only the Python standard library: a balanced Naive Bayes intent model and
lexical case retrieval.  Every answer carries the historical precedents and
official help link used to make it auditable.
"""

from __future__ import annotations

import csv
import json
import math
import re
from collections import Counter, defaultdict
from dataclasses import asdict, dataclass
from pathlib import Path

from run_intent_evaluation import BalancedNaiveBayes, tokens

ROOT = Path(__file__).parent
TRAINING = ROOT / "dataset/splits/training_pairs.csv"
DOCS = ROOT / "dataset/xbox_support_webpages/official_article_catalog.jsonl"
RISKY = {"account_access_profile", "billing_codes_refunds", "safety_enforcement_security", "console_accessory_display", "other_or_needs_context"}
MEDIA_WORDS = ("video", "image", "picture", "photo", "screenshot", "screen shot", "watch this", "see this", "look at this")
ESCALATION_MODES = {"private_account_investigation", "specialist_handoff", "enforcement_review", "repair_or_warranty_process", "visual_evidence_required", "needs_more_context"}
# Kept deliberately narrow after development review: only these two intents had
# a consistently bounded, public workflow in the available documentation.
AUTO_HANDLE_INTENTS = {"subscription_game_pass_gold", "game_content_download"}


@dataclass
class AgentResult:
    intent: str
    intent_confidence: float
    auto_handle: str
    escalation_reason: str
    reply: str
    retrieved_cases: list[dict[str, object]]
    retrieved_articles: list[dict[str, object]]

    def to_dict(self) -> dict[str, object]:
        return asdict(self)


class XboxSupportAgent:
    def __init__(self) -> None:
        self.training = self._read_csv(TRAINING)
        self.docs = [json.loads(line) for line in DOCS.read_text(encoding="utf-8").splitlines() if line.strip()]
        self.classifier = BalancedNaiveBayes().fit(self.training)
        self.case_index = self._make_index(self.training, "customer_text")
        self.doc_index = self._make_index(self.docs, lambda row: f"{row['title']} {row['intent_scope']} {row['use_rule']}")

    @staticmethod
    def _read_csv(path: Path) -> list[dict[str, str]]:
        with path.open(encoding="utf-8", newline="") as handle:
            return list(csv.DictReader(handle))

    @staticmethod
    def _make_index(rows: list[dict], field: str | object):
        inverted, norms = defaultdict(dict), []
        for index, row in enumerate(rows):
            text = row[field] if isinstance(field, str) else field(row)
            count = Counter(tokens(text))
            norm = math.sqrt(sum(value * value for value in count.values())) or 1.0
            norms.append(norm)
            for token, value in count.items():
                inverted[token][index] = value / norm
        return inverted, norms

    @staticmethod
    def _retrieve(text: str, rows: list[dict], index, top_k: int = 3) -> list[dict[str, object]]:
        inverted, _ = index
        query = Counter(tokens(text))
        norm = math.sqrt(sum(value * value for value in query.values())) or 1.0
        scores = Counter()
        for token, value in query.items():
            for row_index, normalized_count in inverted.get(token, {}).items():
                scores[row_index] += (value / norm) * normalized_count
        return [{"similarity": round(score, 3), **rows[row_index]} for row_index, score in scores.most_common(top_k)]

    def predict(self, customer_text: str, *, has_image: bool = False, has_video: bool = False) -> AgentResult:
        probabilities = self.classifier.probabilities(customer_text)
        intent = max(probabilities, key=probabilities.get)
        confidence = probabilities[intent]
        cases = self._retrieve(customer_text, self.training, self.case_index)
        articles = self._retrieve(customer_text, self.docs, self.doc_index)
        media = has_image or has_video or any(word in customer_text.lower() for word in MEDIA_WORDS)
        case_modes = {case.get("proposed_resolution_mode", "") for case in cases}
        doc = next((article for article in articles if article.get("intent_scope") == intent), articles[0] if articles else None)
        if media:
            auto, reason = "no", "requires_visual_evidence"
        elif intent == "billing_codes_refunds":
            auto, reason = "no", "transaction_or_code_investigation"
        elif intent == "safety_enforcement_security":
            auto, reason = "no", "security_or_enforcement_review"
        elif intent == "console_accessory_display":
            auto, reason = "no", "hardware_or_repair_assessment"
        elif intent == "other_or_needs_context" or confidence < 0.42:
            auto, reason = "no", "insufficient_context"
        elif intent not in AUTO_HANDLE_INTENTS:
            auto, reason = "no", "outside_narrow_self_service_policy"
        elif intent == "account_access_profile" and (confidence < 0.70 or case_modes & ESCALATION_MODES):
            auto, reason = "no", "account_specific_verification"
        elif len(case_modes & ESCALATION_MODES) >= 2:
            auto, reason = "no", "historical_cases_needed_private_or_specialist_help"
        elif not doc or doc.get("handling_capability") != "documented_self_service":
            auto, reason = "no", "no_safe_documented_workflow_found"
        else:
            auto, reason = "yes", "documented_public_workflow"
        if auto == "yes":
            reply = f"Hi! The best next step is to follow the Xbox Support guide for {doc['title']}: {doc['url']}. If the steps do not resolve it, reply with the exact error message (but do not share account or payment details here)."
        elif reason == "requires_visual_evidence":
            reply = "Thanks for sharing this. This needs a support specialist to inspect the attached media and account context, so I’m escalating it rather than guessing from the post."
        else:
            reply = "Thanks for the details. This needs account-specific or specialist help, so I’m escalating it to Xbox Support rather than asking you to share private details publicly."
        return AgentResult(intent, round(confidence, 3), auto, reason, reply, cases, articles)


if __name__ == "__main__":
    import argparse
    parser = argparse.ArgumentParser()
    parser.add_argument("message")
    parser.add_argument("--image", action="store_true")
    parser.add_argument("--video", action="store_true")
    args = parser.parse_args()
    print(json.dumps(XboxSupportAgent().predict(args.message, has_image=args.image, has_video=args.video).to_dict(), indent=2))
