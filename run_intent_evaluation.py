"""Evaluate reproducible intent baselines without external Python packages."""

from __future__ import annotations

import csv
import json
import math
import re
from collections import Counter
from pathlib import Path

SPLITS = Path("dataset/splits")
ARTIFACTS = Path("artifacts")
TOKEN = re.compile(r"[a-z0-9]+")


def tokens(text: str) -> list[str]:
    words = TOKEN.findall(text.lower())
    return words + [f"{a}_{b}" for a, b in zip(words, words[1:])]


class BalancedNaiveBayes:
    """Small, inspectable bag-of-words intent model with uniform priors."""

    def fit(self, rows: list[dict[str, str]]) -> "BalancedNaiveBayes":
        self.labels = sorted({r["intent"] for r in rows})
        self.counts = {label: Counter() for label in self.labels}
        self.totals = Counter()
        self.vocabulary: set[str] = set()
        # Cap each class at the same count.  Without this, common account
        # wording dominates token statistics despite uniform class priors.
        selected_per_label = Counter()
        for row in rows:
            label = row["intent"]
            if selected_per_label[label] >= 700:
                continue
            selected_per_label[label] += 1
            row_tokens = tokens(row["customer_text"])
            self.counts[label].update(row_tokens)
            self.totals[label] += len(row_tokens)
            self.vocabulary.update(row_tokens)
        return self

    def probabilities(self, text: str) -> dict[str, float]:
        query = tokens(text)
        size = max(1, len(self.vocabulary))
        scores = {label: sum(math.log((self.counts[label][word] + 1) / (self.totals[label] + size)) for word in query) for label in self.labels}
        maximum = max(scores.values())
        scaled = {label: math.exp(value - maximum) for label, value in scores.items()}
        normalizer = sum(scaled.values())
        return {label: value / normalizer for label, value in scaled.items()}

    def predict(self, text: str) -> str:
        probabilities = self.probabilities(text)
        return max(probabilities, key=probabilities.get)


def read(name: str) -> list[dict[str, str]]:
    with (SPLITS / name).open(encoding="utf-8", newline="") as handle:
        return list(csv.DictReader(handle))


def score(true: list[str], predicted: list[str]) -> dict[str, object]:
    labels = sorted(set(true) | set(predicted))
    matrix = [[sum(t == actual and p == guess for t, p in zip(true, predicted)) for guess in labels] for actual in labels]
    per_intent, f1s = {}, []
    for i, label in enumerate(labels):
        tp = matrix[i][i]
        fp = sum(matrix[row][i] for row in range(len(labels))) - tp
        fn = sum(matrix[i]) - tp
        precision = tp / (tp + fp) if tp + fp else 0.0
        recall = tp / (tp + fn) if tp + fn else 0.0
        f1 = 2 * precision * recall / (precision + recall) if precision + recall else 0.0
        per_intent[label] = {"precision": round(precision, 4), "recall": round(recall, 4), "f1": round(f1, 4), "support": sum(matrix[i])}
        f1s.append(f1)
    return {"accuracy": round(sum(t == p for t, p in zip(true, predicted)) / len(true), 4), "macro_f1": round(sum(f1s) / len(f1s), 4), "labels": labels, "confusion_matrix": matrix, "per_intent": per_intent}


def main() -> None:
    train, development, golden = read("training_pairs.csv"), read("development_pairs.csv"), read("golden_eval_review.csv")
    majority = Counter(row["intent"] for row in train).most_common(1)[0][0]
    classifier = BalancedNaiveBayes().fit(train)
    output: dict[str, object] = {"train_intent_distribution": dict(Counter(row["intent"] for row in train))}
    ARTIFACTS.mkdir(exist_ok=True)
    for split_name, rows in (("development", development), ("golden", golden)):
        true = [row["intent"] for row in rows]
        predicted = [classifier.predict(row["customer_text"]) for row in rows]
        output[f"majority_intent_{split_name}"] = score(true, [majority] * len(rows))
        output[f"balanced_naive_bayes_{split_name}"] = score(true, predicted)
        with (ARTIFACTS / f"{split_name}_intent_predictions.csv").open("w", encoding="utf-8", newline="") as handle:
            writer = csv.DictWriter(handle, fieldnames=["customer_tweet_id", "customer_text", "true_intent", "predicted_intent"])
            writer.writeheader()
            writer.writerows({"customer_tweet_id": r["customer_tweet_id"], "customer_text": r["customer_text"], "true_intent": y, "predicted_intent": p} for r, y, p in zip(rows, true, predicted))
    (ARTIFACTS / "intent_metrics.json").write_text(json.dumps(output, indent=2), encoding="utf-8")
    for model in ("majority_intent", "balanced_naive_bayes"):
        print(f"{model}: dev macro-F1={output[f'{model}_development']['macro_f1']}; golden macro-F1={output[f'{model}_golden']['macro_f1']}")


if __name__ == "__main__":
    main()
