"""Run the Xbox support agent in batch and save development/golden predictions."""

from __future__ import annotations

import argparse
import csv
import json
from pathlib import Path

from run_intent_evaluation import score
from support_agent import XboxSupportAgent


def has_visual_reference(text: str) -> bool:
    lower = text.casefold()
    return any(token in lower for token in ("video", "image", "picture", "photo", "screenshot", "screen shot"))


def main() -> None:
    parser = argparse.ArgumentParser()
    parser.add_argument("--split", choices=("development", "golden"), default="development")
    parser.add_argument("--limit", type=int, default=0)
    args = parser.parse_args()
    split_path = Path("dataset/splits") / ("development_pairs.csv" if args.split == "development" else "golden_eval_review.csv")
    output_dir = Path("artifacts")
    output_dir.mkdir(exist_ok=True)
    with split_path.open(encoding="utf-8", newline="") as file:
        rows = list(csv.DictReader(file))
    if args.limit:
        rows = rows[: args.limit]
    agent = XboxSupportAgent()
    predictions = []
    for index, row in enumerate(rows, start=1):
        text = row["customer_text"]
        visual = has_visual_reference(text)
        result = agent.predict(text, has_image=visual, has_video=False).to_dict()
        predictions.append({
            "row_id": index,
            "customer_tweet_id": row["customer_tweet_id"],
            "customer_text": text,
            "true_intent": row.get("intent", ""),
            "true_auto_handle": row.get("auto_handle", ""),
            **result,
        })
    prediction_path = output_dir / f"{args.split}_predictions.jsonl"
    with prediction_path.open("w", encoding="utf-8") as file:
        for prediction in predictions:
            file.write(json.dumps(prediction, ensure_ascii=False) + "\n")
    summary: dict[str, object] = {"rows": len(predictions), "prediction_file": str(prediction_path)}
    intents = [item["true_intent"] for item in predictions if item["true_intent"]]
    if intents:
        predicted_intents = [item["intent"] for item in predictions if item["true_intent"]]
        intent_scores = score(intents, predicted_intents)
        summary["intent_accuracy"] = intent_scores["accuracy"]
        summary["intent_macro_f1"] = intent_scores["macro_f1"]
    decisions = [item for item in predictions if item["true_auto_handle"] in {"yes", "no"}]
    if decisions:
        truth = [item["true_auto_handle"] == "yes" for item in decisions]
        pred = [item["auto_handle"] == "yes" for item in decisions]
        true_yes = ["yes" if value else "no" for value in truth]
        pred_yes = ["yes" if value else "no" for value in pred]
        decision_scores = score(true_yes, pred_yes)
        summary["auto_handle_f1"] = decision_scores["per_intent"]["yes"]["f1"]
        summary["unsafe_auto_handle_rate"] = round(sum(predicted and not actual for predicted, actual in zip(pred, truth)) / max(1, sum(pred)), 4)
    (output_dir / f"{args.split}_metrics.json").write_text(json.dumps(summary, indent=2), encoding="utf-8")
    print(json.dumps(summary, indent=2))


if __name__ == "__main__":
    main()
