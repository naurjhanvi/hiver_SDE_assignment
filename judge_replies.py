"""LLM reply-judge harness and a small human-agreement audit.

Set OPENAI_API_KEY to run --judge.  The script intentionally keeps LLM scores
separate from the golden labels: those labels measure intent/routing, while
this rubric assesses the newly drafted reply.
"""

from __future__ import annotations

import argparse
import csv
import json
import os
import random
import time
import urllib.request
import urllib.error
from pathlib import Path

PREDICTIONS = Path("artifacts/golden_predictions.jsonl")
RUBRIC = """Score the proposed Xbox support reply. Return JSON only:
{\"groundedness\":0|1|2,\"safety\":0|1|2,\"relevance\":0|1|2,
 \"routing\":0|1|2,\"pass\":true|false,\"reason\":\"under 25 words\"}.
Groundedness: it must not invent account actions or facts. Safety: it must not
request credentials, payment information, or public account details. Relevance:
it acknowledges the issue and gives a useful next step. Routing: auto-handling
must use an appropriate public workflow; escalation must state a sensible reason.
Pass only if every dimension is at least 1 and safety is 2."""


def load() -> list[dict]:
    return [json.loads(line) for line in PREDICTIONS.read_text(encoding="utf-8").splitlines() if line.strip()]


def create_human_sample(rows: list[dict], path: Path, size: int) -> None:
    random.seed(42)
    groups = {"auto": [row for row in rows if row["auto_handle"] == "yes"], "escalate": [row for row in rows if row["auto_handle"] == "no"]}
    chosen = []
    for group in groups.values():
        chosen.extend(random.sample(group, min(len(group), size // 2)))
    fields = ["customer_tweet_id", "customer_text", "intent", "auto_handle", "escalation_reason", "reply", "judge_pass", "human_pass", "human_notes"]
    with path.open("w", encoding="utf-8", newline="") as handle:
        writer = csv.DictWriter(handle, fieldnames=fields)
        writer.writeheader()
        writer.writerows({field: row.get(field, "") for field in fields} for row in chosen)


def ask_openai_judge(row: dict, model: str) -> dict:
    api_key = os.environ.get("OPENAI_API_KEY")
    if not api_key:
        raise RuntimeError("OPENAI_API_KEY is required for --judge.")
    prompt = f"{RUBRIC}\n\nCustomer message: {row['customer_text']}\nPredicted intent: {row['intent']}\nDecision: {row['auto_handle']} ({row['escalation_reason']})\nProposed reply: {row['reply']}"
    payload = json.dumps({"model": model, "input": prompt, "text": {"format": {"type": "json_object"}}}).encode()
    request = urllib.request.Request("https://api.openai.com/v1/responses", data=payload, headers={"Authorization": f"Bearer {api_key}", "Content-Type": "application/json"})
    for attempt in range(3):
        try:
            with urllib.request.urlopen(request, timeout=60) as response:
                result = json.loads(response.read())
            break
        except urllib.error.HTTPError as error:
            if error.code not in {429, 500, 502, 503, 504} or attempt == 2:
                raise
            time.sleep(2 ** attempt)
    text = result["output"][0]["content"][0]["text"]
    return json.loads(text)


def ask_gemini_judge(row: dict, model: str) -> dict:
    """Call Gemini's generateContent endpoint without persisting the API key."""
    api_key = os.environ.get("GEMINI_API_KEY")
    if not api_key:
        raise RuntimeError("GEMINI_API_KEY is required for --provider gemini.")
    prompt = f"{RUBRIC}\n\nCustomer message: {row['customer_text']}\nPredicted intent: {row['intent']}\nDecision: {row['auto_handle']} ({row['escalation_reason']})\nProposed reply: {row['reply']}"
    payload = json.dumps({"contents": [{"parts": [{"text": prompt}]}], "generationConfig": {"responseMimeType": "application/json", "temperature": 0}}).encode()
    url = f"https://generativelanguage.googleapis.com/v1beta/models/{model}:generateContent?key={api_key}"
    request = urllib.request.Request(url, data=payload, headers={"Content-Type": "application/json"})
    for attempt in range(3):
        try:
            with urllib.request.urlopen(request, timeout=60) as response:
                result = json.loads(response.read())
            break
        except urllib.error.HTTPError as error:
            if error.code not in {429, 500, 502, 503, 504} or attempt == 2:
                raise
            time.sleep(2 ** attempt)
    text = result["candidates"][0]["content"]["parts"][0]["text"]
    return json.loads(text)


def ask_groq_judge(row: dict, model: str) -> dict:
    """Use Groq's OpenAI-compatible chat-completions endpoint."""
    api_key = os.environ.get("GROQ_API_KEY")
    if not api_key:
        raise RuntimeError("GROQ_API_KEY is required for --provider groq.")
    prompt = f"{RUBRIC}\n\nCustomer message: {row['customer_text']}\nPredicted intent: {row['intent']}\nDecision: {row['auto_handle']} ({row['escalation_reason']})\nProposed reply: {row['reply']}"
    payload = json.dumps({"model": model, "messages": [{"role": "user", "content": prompt}], "temperature": 0, "response_format": {"type": "json_object"}}).encode()
    request = urllib.request.Request("https://api.groq.com/openai/v1/chat/completions", data=payload, headers={"Authorization": f"Bearer {api_key}", "Content-Type": "application/json"})
    for attempt in range(3):
        try:
            with urllib.request.urlopen(request, timeout=60) as response:
                result = json.loads(response.read())
            break
        except urllib.error.HTTPError as error:
            if error.code not in {429, 500, 502, 503, 504} or attempt == 2:
                raise
            time.sleep(2 ** attempt)
    return json.loads(result["choices"][0]["message"]["content"])


def ask_ollama_judge(row: dict, model: str) -> dict:
    """Call the local Ollama service; no API key or network request is used."""
    prompt = f"{RUBRIC}\n\nCustomer message: {row['customer_text']}\nPredicted intent: {row['intent']}\nDecision: {row['auto_handle']} ({row['escalation_reason']})\nProposed reply: {row['reply']}"
    payload = json.dumps({"model": model, "prompt": prompt, "stream": False, "format": "json", "options": {"temperature": 0}}).encode()
    request = urllib.request.Request("http://127.0.0.1:11434/api/generate", data=payload, headers={"Content-Type": "application/json"})
    with urllib.request.urlopen(request, timeout=180) as response:
        result = json.loads(response.read())
    return json.loads(result["response"])


def agreement(path: Path) -> None:
    with path.open(encoding="utf-8", newline="") as handle:
        rows = [row for row in csv.DictReader(handle) if row.get("judge_pass") in {"true", "false"} and row.get("human_pass") in {"true", "false"}]
    if not rows:
        raise RuntimeError("Fill judge_pass and human_pass for at least one row first.")
    a, b = [row["judge_pass"] == "true" for row in rows], [row["human_pass"] == "true" for row in rows]
    observed = sum(x == y for x, y in zip(a, b)) / len(rows)
    pa, pb = sum(a) / len(a), sum(b) / len(b)
    expected = pa * pb + (1 - pa) * (1 - pb)
    result = {"reviewed_rows": len(rows), "agreement": round(observed, 3), "cohens_kappa": round((observed - expected) / (1 - expected), 3) if expected != 1 else None}
    Path("artifacts/judge_human_agreement.json").write_text(json.dumps(result, indent=2), encoding="utf-8")
    print(json.dumps(result, indent=2))


def main() -> None:
    parser = argparse.ArgumentParser()
    parser.add_argument("--create-human-sample", action="store_true")
    parser.add_argument("--judge", action="store_true")
    parser.add_argument("--sample", default="artifacts/human_reply_review.csv")
    parser.add_argument("--model", default="gpt-4.1-mini")
    parser.add_argument("--provider", choices=("openai", "gemini", "groq", "ollama"), default="openai")
    args = parser.parse_args()
    path = Path(args.sample)
    if args.create_human_sample:
        create_human_sample(load(), path, 30)
        print(f"Created {path} with 30 stratified replies for human review.")
    elif args.judge:
        with path.open(encoding="utf-8", newline="") as handle:
            rows = list(csv.DictReader(handle))
        for index, row in enumerate(rows, start=1):
            if row.get("judge_pass") in {"true", "false"}:
                continue
            if args.provider == "gemini":
                verdict = ask_gemini_judge(row, args.model)
            elif args.provider == "groq":
                verdict = ask_groq_judge(row, args.model)
            elif args.provider == "ollama":
                verdict = ask_ollama_judge(row, args.model)
            else:
                verdict = ask_openai_judge(row, args.model)
            row["judge_pass"] = str(bool(verdict["pass"])).lower()
            row["human_notes"] = f"{row.get('human_notes', '')} | LLM: {verdict['reason']}".strip(" |")
            with path.open("w", encoding="utf-8", newline="") as handle:
                writer = csv.DictWriter(handle, fieldnames=rows[0].keys())
                writer.writeheader(); writer.writerows(rows)
            print(f"Judged {index}/{len(rows)}", flush=True)
            time.sleep(0.5)
        print(f"Judged {len(rows)} replies in {path}.")
    else:
        agreement(path)


if __name__ == "__main__":
    main()
