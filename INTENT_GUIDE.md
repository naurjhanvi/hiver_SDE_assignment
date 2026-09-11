# XboxSupport intent guide

## Scope

This taxonomy labels the primary issue in an inbound customer message sent to
XboxSupport. It is based on an exploratory review of direct customer-to-support
reply pairs from the Customer Support on Twitter dataset. It is intentionally
compact so each class will have enough examples for evaluation.

Choose one intent per message. When a message is an unclear continuation of an
earlier thread and cannot be understood from the available context, use
`other_or_needs_context`.

## Intent definitions

| Intent | Use for | Do not use for | Default handling |
| --- | --- | --- | --- |
| `account_access_profile` | Sign-in, password, account email, gamertag, profile, family-account, or account-ownership problems. | Subscription cancellation or a purchase dispute unless access to the account is the primary problem. | Escalate when account-specific lookup, recovery, or verification is required. |
| `billing_codes_refunds` | Charges, payment methods, purchases, order status, refunds, redeemed codes, or missing purchased content. | General Game Pass or Gold management without a disputed transaction. | Escalate when a transaction, code, refund, or account-specific order must be investigated. |
| `subscription_game_pass_gold` | Game Pass, Xbox Live Gold, recurring membership, auto-renewal, membership benefits, or Games with Gold. | A particular game failing to download or launch. | Auto-handle only for general policy or self-service instructions; otherwise escalate. |
| `game_content_download` | Game installation, download/update failure, DLC, game availability, backward compatibility, game licences, or in-game content. | Physical console or accessory faults. | Usually eligible for a grounded troubleshooting reply. Escalate after failed troubleshooting or for account-specific entitlements. |
| `console_accessory_display` | Console, controller, headset, storage, repair/warranty, display/TV, or other physical-device issue. | A game-only crash without a device/accessory issue. | Give safe first-step diagnostics; escalate for repair, warranty, or unresolved hardware issues. |
| `connectivity_xbox_live` | Network connection, Xbox Live availability, multiplayer/party, server, outage, or online-service issue. | A download failure whose primary issue is a particular game/content item. | Auto-handle known-status or safe network checks; escalate when account-specific or unresolved. |
| `safety_enforcement_security` | Suspensions/bans, Code of Conduct, cheating reports, hacked/stolen accounts, or unauthorized use. | An ordinary password reset with no compromise or enforcement concern. | Escalate by default. |
| `how_to_product_information` | General, non-account-specific questions about Xbox features, settings, captures, compatibility, availability, or policies. | A request framed as a malfunction or an account/transaction issue. | Usually eligible for auto-handling when retrieval finds a clear historical answer. |
| `other_or_needs_context` | Greetings, unclear requests, unrelated feedback, or a follow-up that lacks enough context to identify the issue. | A message whose primary problem can reasonably be assigned to another intent. | Escalate by default. |

## Boundary rules

- Label the customer's requested outcome, not the product words they mention. A
  game download error belongs to `game_content_download` even if it also mentions
  an Xbox console.
- Use `billing_codes_refunds` when the customer needs a purchase, code, charge,
  or refund investigated. Use `subscription_game_pass_gold` for general
  membership management or benefits.
- Use `safety_enforcement_security` for suspected compromise, unauthorized
  transactions, or enforcement action, even when the message also contains an
  account-access term.
- If the row is a follow-up, annotators may read the preceding retained thread
  context. If it still does not reveal the issue, use `other_or_needs_context`.

## Escalation policy used for evaluation

Escalate whenever the requested action needs identity verification, private
account data, transaction investigation, enforcement review, suspected
compromise, repair processing, or missing context. A message can be
auto-handled only when the intent is clear, retrieval finds a consistent
historical answer, and the response can provide safe general guidance without
claiming an account action.

## Next labeling step

Create a stratified 200-message golden set: target 20 messages from each intent,
then allocate the remaining 20 to `other_or_needs_context` and deliberately
ambiguous or safety-sensitive cases. Keep this set separate from examples used
to develop the classifier, retrieval corpus, and prompts.
