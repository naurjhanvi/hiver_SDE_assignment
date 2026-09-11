# XboxSupport Twitter agent

This project turns historical `@XboxSupport` Twitter conversations into a conservative first-line support agent. Given a customer post, it predicts one of nine intents, retrieves comparable historical cases and official Xbox Support pages, drafts a response, and chooses **auto-handle** or **escalate** with an explicit reason.

The current result is a useful prototype, **not deployment-ready**: on the locked 200-message golden set it reaches 0.455 macro-F1 for intent and has a 19.4% unsafe-auto-handle rate among messages it auto-handles. That safety result is the central finding.

## Reproduce in under 15 minutes

Requires only Python 3.11+; no package installation is needed.

```powershell
cd C:\Users\ranij\projects\hiver
python .\run_intent_evaluation.py
python .\evaluate_agent.py --split golden
python .\support_agent.py "My Game Pass subscription will not renew"
```

Expected headline outputs are written to `artifacts/intent_metrics.json` and `artifacts/golden_metrics.json`. The scripts use the prepared 20,158-row training split rather than the original 3M-row source, and normally finish in under a minute on this machine.

## Data and labels

`dataset/splits/` contains the only data needed to run the project:

- `training_pairs.csv` — 20,158 customer message → historical Xbox reply pairs.
- `development_pairs.csv` — 2,241 thread-disjoint rows for model selection.
- `golden_eval_review.csv` — 200 thread-disjoint reviewed evaluation messages. It deliberately excludes the historical answer to prevent reply leakage.

The source subset was built by retaining every `author_id == XboxSupport` tweet and recursively retaining its ancestor tweets through `in_response_to_tweet_id`. It does **not** treat every tweet mentioning “Xbox” as support data. Splits are disjoint by conversation thread.

The nine label definitions and routing boundaries are in `INTENT_GUIDE.md`. The 200 golden labels were retrieval-prelabelled to make sampling practical, then manually reviewed and finalized. The customer message defines the intent, while the historical reply informs whether the usual resolution was public/self-service or needed a human.

## Scope and non-goals

For Xbox, “good” means correctly routing a public support request, giving a safe first reply, and avoiding false claims about account actions. This prototype does **not** authenticate users, access Xbox accounts, inspect attached image/video content, take payment or refund actions, perform enforcement decisions, or diagnose hardware remotely. Those cases are escalated rather than automated.

## Model and routing policy

The selected classifier is a balanced multinomial Naive Bayes model using word unigrams and bigrams. It caps each intent at 700 examples during fitting so the two dominant classes do not swamp rare support types. This is intentionally simple and inspectable.

The agent retrieves overlapping term evidence from historical cases and a curated catalog of official Xbox Support pages. It auto-handles only clear subscription and game-download requests with a documented public workflow; all other classes stay human-routed in this first version. It escalates when media is attached/referenced, there is a billing/code, security/enforcement, repair/hardware, private account, low-confidence, or no-safe-workflow signal. It never asks for credentials or payment details in public.

## Results

| System | Development macro-F1 | Golden macro-F1 |
| --- | ---: | ---: |
| Trivial: always `account_access_profile` | 0.068 | 0.020 |
| Simple: balanced Naive Bayes | 0.373 | 0.455 |

On the golden set, the end-to-end agent has intent accuracy **0.470**, intent macro-F1 **0.455**, auto-handle F1 **0.431**, and unsafe-auto-handle rate **0.194** (6 unsafe cases out of 31 auto-handled). “Unsafe” here means it auto-handled an example the reviewed golden label says should escalate. This is still too high for production; a real launch would begin in shadow mode.

## Reply-quality judge and human agreement

`judge_replies.py` implements a four-part LLM-as-judge rubric: groundedness, safety, relevance, and routing. The completed audit uses **Qwen 2.5 3B Instruct running locally through Ollama**, so no API key or paid service was used. The fixed 30-reply sample is stratified across auto-handle and escalate decisions.

The LLM and human pass/fail decisions agreed on **46.7%** of the 30 replies; Cohen’s kappa is **0.00**. Kappa is unstable here because I have marked every reply as a pass. This is useful negative evidence: the local judge is substantially stricter than the human reviewer, so it should not replace human review. The completed artifact is `artifacts/human_reply_review_local_llm.csv`; summary metrics are in `artifacts/judge_human_agreement.json`.

To reproduce the local judge after Ollama is installed and the model is downloaded:

```powershell
ollama pull qwen2.5:3b-instruct
python .\judge_replies.py --judge --provider ollama --model qwen2.5:3b-instruct --sample .\artifacts\human_reply_review_local_llm.csv
python .\judge_replies.py --sample .\artifacts\human_reply_review_local_llm.csv
```

The final command reports raw agreement and Cohen’s kappa.

## Failure analysis

1. **Account wording over-generalises.** “Account” appears in many unrelated posts, creating false account-access predictions.
2. **Sparse historic language.** Very short/noisy tweets have too little lexical overlap, causing `other_or_needs_context` or an unrelated intent.
3. **Public versus private boundary is hard from a tweet alone.** Account changes may be self-service, but account recovery must be private.
4. **Historical Twitter links are incomplete evidence.** Many past replies point to short URLs rather than a fully preserved workflow.
5. **Media is only text-detectable in this export.** The CSV does not reliably retain image/video metadata; “video”/URL cues are a conservative proxy.

## What is misleading about the headline number?

The golden macro-F1 (0.455) looks materially better than the majority baseline, but it is not a production-quality answer. The labels were seeded with retrieval, the taxonomy is broad, and the golden set is only 200 messages from the same historical channel. More importantly, intent F1 does not measure whether the reply is safe: even the deliberately narrow routing policy still has a 19.4% unsafe-auto-handle rate.

## One more week

Add a genuinely independent second annotator; collect true media metadata; replace lexical retrieval with a cached embedding index; expand and verify the official-document corpus; calibrate routing thresholds on a separately labelled development set; and run a shadow comparison against current human handling.

## Sources

- [Customer Support on Twitter dataset](https://www.kaggle.com/datasets/thoughtvector/customer-support-on-twitter)
- [Xbox Support](https://support.xbox.com/en-GB)
- [Banking77](https://huggingface.co/datasets/PolyAI/banking77) was considered for intent-method inspiration only and was not used for Xbox training because it is banking-domain data.
- [Ollama](https://docs.ollama.com/windows) provided the local runtime for the reply-quality judge.
- [Qwen 2.5 3B Instruct](https://ollama.com/library/qwen2.5%3A3b-instruct) was the local LLM used by that judge.
