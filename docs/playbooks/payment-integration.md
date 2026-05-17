# Payment Integration

**Lifecycle:** experimental · **First use:** TBD · **Verified by:** none

> Building any feature that takes money: one-time charge, subscription, marketplace, in-app credit, refund flow. Provider-agnostic — applies to Stripe, SePay (VN), Paddle, Polar, Creem, ngân hàng bank transfer, anything with a webhook. Covers idempotency, refund/dispute, reconciliation, PCI scope minimization, audit-log shape.

## When To Run

- Story introduces or modifies payment behavior (charge, subscription, refund, dispute, payout, invoice).
- Integrating a new provider.
- Auditing existing payment behavior for compliance, reconciliation drift, or webhook reliability.

Skip when: payment is a single "Buy on Gumroad" external link with no callback to your system.

## Webhook Handling (Critical)

Webhooks are the source of truth for state changes. Provider may retry; network may drop; out-of-order delivery happens. The handler MUST be:

### Idempotent

Same webhook delivered twice produces the same state. Implementation pattern:

```text
1. Receive webhook → extract provider's event ID (e.g. evt_xxx).
2. Look up event ID in `webhook_events` table.
3. If exists with status=processed: return 200 OK without re-processing.
4. If exists with status=processing: return 409 (provider will retry).
5. If new: insert event row (status=processing) within the same transaction
   that performs the state change. Commit. Update status=processed.
6. If processing fails: leave status=failed with error message + retry counter.
   Manual / scheduled retry.
```

Without this, a duplicate webhook = double-charge to the customer OR double-refund FROM you.

### Verified

Every webhook MUST have its signature verified before the handler does anything:

- **Stripe:** verify `Stripe-Signature` header per `stripe.webhooks.constructEvent`.
- **SePay:** verify the bank-transfer hash per their docs.
- **Paddle / Polar / others:** signed HMAC headers — verify against the secret.

Reject unsigned or invalid-signed requests with 401 BEFORE any DB read. Unverified webhook handlers are how scammers fake "payment received" events.

### Replay-Safe

Provider may resend events out of order (e.g. `subscription.updated` arrives before `customer.created`). Handler should:

- Tolerate missing precursor records (look up by external ID, create stub if needed).
- Compare event timestamp to stored state; ignore stale updates.
- Never assume sequential order.

### Logged

Every webhook receipt + outcome logged per `docs/ARCHITECTURE.md § Observability Contract`:

- `action: webhook_received`, `provider`, `event_type`, `event_id`, `outcome: ok | duplicate | invalid_sig | failed`, `duration_ms`.

## Refund / Dispute Flow

Refunds are state changes, not just provider API calls. Each refund:

1. Logs to `payments` table with `type: refund`, link to original `payment_id`.
2. Triggers `refund.created` webhook back to you — handler updates internal state.
3. Notifies the user (email + in-app).
4. Adjusts any downstream state (subscription, credits, access).

Disputes (chargebacks) are higher-stakes:

- Auto-pause the user's account / subscription on `dispute.created` (provider-dependent).
- Log evidence (timestamps, IPs, fulfillment) to a dispute record.
- Surface to ops / admin UI for response within provider's deadline (often 7-21 days).

Pattern: refund + dispute UI is part of the admin / internal tool surface, not customer-facing. Customer-facing is "request refund" → ticket → admin processes.

## Reconciliation

At least daily, reconcile provider state vs internal state:

```text
For each provider account:
  List events / charges since last reconciliation.
  Compare against `payments` table.
  Surface drift to admin / monitoring.
```

Common drift causes:

- Missed webhook (provider sent, your endpoint was down) → reprocess.
- Manual provider-dashboard refund without internal record → backfill.
- Double-processed webhook (idempotency bug) → de-dupe + fix the bug.

For VN bank-transfer (SePay) flows, reconciliation is daily-or-more-frequent — bank-side records often lag webhook delivery.

## PCI Scope Minimization

Do NOT touch card numbers / CVV. Ever. Provider gives you tokenized references (`pm_xxx`, `tok_xxx`) — store those, not the card itself.

- **Card capture:** provider-hosted (Stripe Elements / Checkout, SePay redirect). Your server never sees the raw PAN.
- **Storage:** payment-method ID + last4 + brand + expiry month/year. Nothing else.
- **Logging:** redact any field that looks like a card number BEFORE writing to logs. Pattern match `\d{13,19}` and replace with `[REDACTED]`.
- **PCI compliance:** SAQ-A scope if you stay fully provider-hosted. If you drift into iframes or direct API submission, scope jumps to SAQ-A-EP or SAQ-D — much more work.

Verify SAQ scope before stage 8 starts. Drift after launch is expensive.

## Provider Abstraction

Even if you start single-provider, wrap the SDK calls in a thin abstraction:

```text
PaymentProvider interface:
  - create_checkout(amount, currency, customer, success_url, cancel_url) → checkout_url
  - get_payment(id) → Payment
  - refund(payment_id, amount?) → Refund
  - on_webhook(headers, body) → Event (after signature verify)
```

Concrete implementations per provider. Story-level code calls the interface, not the SDK directly. Two benefits:

1. **Testing:** mock the interface in unit tests, not the network.
2. **Migration:** swapping Stripe → Paddle (or VN: SePay → VNPay) doesn't touch business logic.

For Vietnam projects: SePay primary for VietQR bank-transfer + secondary international card processor (Stripe / 2Checkout / Paddle MoR) for foreign cards. The abstraction makes routing per-currency or per-region clean.

## Test Mode Discipline

Provider test mode is your friend. Rules:

- Production keys live ONLY in production secret vault.
- Local dev + CI run against provider test mode.
- Test-mode webhooks point at a CI / dev endpoint (use `cloudflared tunnel` / `ngrok` / provider's test webhook simulator).
- E2E tests in `docs/playbooks/canonical-e2e-flow-playbook.md` use test-mode cards (`4242 4242 4242 4242` for Stripe; provider-specific for others).

NEVER run a "test" against production keys to "see what happens." That's how real charges happen.

## Audit-Log Requirements

Payment events are product records, per `docs/ARCHITECTURE.md § Observability Contract` — audit logs, NOT just app logs.

Audit-log row shape:

- `timestamp`
- `actor: user | system | admin`
- `action: payment_created | payment_succeeded | payment_failed | refund_issued | dispute_opened | subscription_renewed | ...`
- `payment_id` (internal)
- `provider_event_id` (external — for grep against provider dashboard)
- `amount`, `currency`
- `user_id`
- `result: ok | failed | pending`
- `metadata: <any provider-specific reference>`

Retention: at least 7 years for tax / dispute defence (jurisdiction-dependent). Verify with the project's accounting / legal counsel.

## Subscription-Specific

If subscriptions are in scope:

- **Pro-ration on plan change:** decide upfront (provider often defaults to immediate pro-ration; some products prefer end-of-cycle). Document the choice as a decision.
- **Trial → paid transition:** webhook handler must flip the user's access state. Test the trial-end edge case explicitly.
- **Cancellation:** distinguish "cancel at period end" (default) vs "immediate". Both have different UX implications.
- **Dunning:** failed renewals trigger a retry sequence. Provider handles the retries; you handle the user comms + access state.

## Cross-Tier Behavior

| Lane | Payment playbook application |
| --- | --- |
| Tiny | Skip — payment work is never tiny. |
| Normal | Required: webhook idempotency + signature verify + audit log + test mode + reconciliation job. |
| High-Risk | Required everywhere: same as normal + dispute flow + per-feature decision doc + provider abstraction + 2-reviewer code review. Auto-block on missing signature verify. |

Any new payment behavior is a hard gate per `docs/FEATURE_INTAKE.md § Hard gates` → high-risk lane.

## Variant Section

(Append a Variant block here when this playbook fails or partially works.)

## Related

- `docs/templates/decisions/stack-selection.md` § External Providers — picks the payment provider before this playbook runs.
- `docs/playbooks/code-review-scoring.md` — security dimension auto-blocks if signature verification is missing.
- `docs/ARCHITECTURE.md § Parse-First Boundary Rule` — webhook bodies are unknown input, parse at boundary.
- `docs/ARCHITECTURE.md § Observability Contract` — audit log shape.
- `docs/playbooks/canonical-e2e-flow-playbook.md` — E2E tests for payment journeys.
- `docs/playbooks/ai-feature-integration.md` — sibling provider-integration playbook with the same shape.

## Tooling Hints (Optional)

Per `docs/HARNESS.md § Independence Principle`. Skill convenience wrappers — fallback to provider SDKs directly:

- `/ck:payment-integration` — checkout / webhook / subscription scaffolding for SePay, Polar, Stripe, Paddle, Creem.
- `/ck:better-auth` — pairs auth + payment when both are in scope.

Fallback: provider SDK or REST API directly.
