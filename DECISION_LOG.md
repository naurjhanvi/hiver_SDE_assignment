# Decision log

1. Selected XboxSupport because it has enough volume for thread-disjoint splits while remaining a focused product-support domain.
2. Kept tweets by account identity (`author_id == XboxSupport`) plus reply ancestors, rather than a noisy keyword search for “Xbox”.
3. Classified the incoming customer post, not the agent reply; replies are evidence of resolution style.
4. Used nine broad, action-oriented intents to keep annotation and routing feasible with 200 golden examples.
5. Made `other_or_needs_context` an explicit class instead of forcing ambiguous posts into a misleading specific intent.
6. Split by thread, not individual tweet, to prevent the same conversation appearing in both training and evaluation.
7. Withheld the historical reply from the golden set to prevent retrieval/reply leakage in evaluation.
8. Seeded labels with similarity retrieval, then reviewed them, because manual-first labelling of a large noisy corpus is impractical.
9. Used historical reply modes to infer whether cases generally resolve publicly or need private/specialist help.
10. Treated visual attachments or clear references to them as mandatory escalation because the CSV does not preserve reliable media content.
11. Used official Xbox pages only as redirect targets, not as evidence that the agent performed account actions.
12. Chose balanced Naive Bayes as the selected model after it beat the majority baseline on development macro-F1 and can run without a GPU or API key.
13. Capped per-intent training examples at 700 to reduce dominance by account and context-heavy messages.
14. Chose conservative escalation rules for billing, codes, enforcement, security, repair/hardware, and private account recovery.
15. Reported unsafe-auto-handle rate separately from intent F1 because a good classification headline can conceal harmful routing errors.
