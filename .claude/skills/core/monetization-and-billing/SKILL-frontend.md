---
name: monetization-and-billing
description: Implementing Stripe billing, subscription management, tiered access
  control, and payment infrastructure for SaaS platforms. Use when integrating
  Stripe Checkout, Subscriptions, Webhooks, Customer Portal, or metered billing.
  Also use when implementing tier-based feature gating (free vs paid), upgrade/
  downgrade flows, trial periods, invoice handling, region-specific payment
  methods (PIX, Boleto, SEPA, ACH), or any payment-related backend logic. Use
  when designing Supabase schemas for billing state, RLS policies that check
  subscription tier, or webhook handlers that sync Stripe state to your
  database. Even if the user just mentions "pricing", "plans", "paywall",
  "subscription", or "monetization", use this skill. Never assume Stripe
  behavior — verify against current Stripe docs.
---

# Monetization and Billing

## Fail-Fast Rule

If any payment operation fails, **return a structured error and do not grant
access**. Never optimistically grant paid features before payment confirmation.
Never silently ignore webhook failures. A missed webhook = a user who paid but
has no access, or a user who canceled but keeps access.

## Cardinal Rule

**Stripe is the single source of truth for billing state.** Your database is a
cache of Stripe's state, synchronized via webhooks. Never make billing decisions
based solely on local database state without webhook confirmation. Never store
raw credit card numbers or sensitive payment data locally.

## Architecture: {{PROJECT_NAME}} Billing Stack

```
┌─────────────────┐     ┌──────────────┐     ┌─────────────┐
│  Frontend (React)│────▶│ Supabase Auth │────▶│ Supabase DB  │
│  Vercel          │     │  + RLS        │     │ billing_*    │
└────────┬────────┘     └──────────────┘     └──────┬──────┘
         │                                          │
         │  Checkout Session                        │  RLS checks
         ▼                                          │  tier column
┌─────────────────┐     ┌──────────────┐           │
│  Stripe Checkout │────▶│ Stripe       │───────────┘
│  (hosted page)   │     │ Webhooks     │  sync via
└─────────────────┘     │  → Backend   │  webhook handler
                        └──────────────┘
```

### Component Responsibilities

- **Frontend**: Creates Checkout Sessions via Backend API, redirects to Stripe,
  shows Customer Portal link, displays current plan, handles upgrade prompts.
- **Backend**: Hosts webhook endpoint, validates signatures, syncs billing state
  to Supabase, enforces tier-based rate limits on API responses.
- **Supabase**: Stores billing state (`profiles.tier`, `subscriptions` table),
  RLS policies check tier for data access depth.
- **Stripe**: Manages payment methods, subscriptions, invoices, trials,
  Customer Portal. SSOT for all billing state.

## Tier Model

### {{PROJECT_NAME}} Tiers

Typical SaaS tier structure — adapt dollar amounts, quotas, and feature
gates to match your product.

| Tier | Price (USD) | Data Scope | WS Channels | API Keys | Rate Limit | History |
|------|------------|-----------|-------------|----------|------------|---------|
| Free | $0 | Limited rows | 2 basic | 0 | 30 req/min | 24h |
| Starter | $29/mo | Full current view | All channels | 3 | 120 req/min | 7d |
| Pro | $99/mo | Full current view | All channels | 5 | 300 req/min | 30d |
| Enterprise | Custom | Full + priority | All + priority | 50 | 3000 req/min | Unlimited |

### Tier Enforcement Points

```typescript
// Backend: middleware that checks tier
async function tierMiddleware(c: Context, next: Next) {
  const apiKey = c.req.header('X-API-Key');
  const tier = apiKey
    ? await getTierFromApiKey(apiKey)
    : await getTierFromSession(c);

  c.set('tier', tier ?? 'free');
  c.set('tierLimits', TIER_LIMITS[tier ?? 'free']);
  await next();
}

// Backend: row limiting per tier
function limitRows<T>(rows: T[], tier: Tier): T[] {
  const maxRows = TIER_LIMITS[tier].maxRows;
  return rows.slice(0, maxRows);
}

// Supabase RLS: check tier for historical data
CREATE POLICY "pro_historical_access" ON analytics_snapshots
  FOR SELECT USING (
    public.get_user_tier(auth.uid()) IN ('pro', 'enterprise')
    OR created_at > now() - interval '24 hours'  -- free gets last 24h
  );
```

### Tier Lookup Helper (Supabase)

```sql
CREATE OR REPLACE FUNCTION public.get_user_tier(user_id uuid)
RETURNS text
LANGUAGE sql STABLE SECURITY DEFINER
AS $$
  SELECT COALESCE(
    (SELECT tier FROM public.profiles WHERE id = user_id),
    'free'
  );
$$;
```

## Stripe Integration

### Products and Prices Setup

Create products in Stripe Dashboard (not via API for initial setup):

```
Product: "{{PROJECT_NAME}} Pro"
  Price: $99.00/month (USD, recurring)
  Price ID: price_pro_monthly_usd
  Metadata: { tier: "pro", max_rows: "20", ws_channels: "all" }

Product: "{{PROJECT_NAME}} Enterprise"
  Price: Custom (USD, recurring)
  Price ID: price_enterprise_monthly_usd
  Metadata: { tier: "enterprise", max_rows: "unlimited", ws_channels: "all" }
```

**Rule**: Store tier metadata on the Stripe Price object. When a webhook fires,
read the tier from `price.metadata.tier` — this is the canonical mapping.

### Checkout Session Creation (Backend Endpoint)

```typescript
// POST /api/billing/checkout
app.post('/api/billing/checkout', authMiddleware, async (c) => {
  const { priceId } = await c.req.json();
  const userId = c.get('userId');

  // Get or create Stripe customer
  let customerId = await getStripeCustomerId(userId);
  if (!customerId) {
    const customer = await stripe.customers.create({
      metadata: { supabase_user_id: userId },
    });
    customerId = customer.id;
    await saveStripeCustomerId(userId, customerId);
  }

  const session = await stripe.checkout.sessions.create({
    customer: customerId,
    mode: 'subscription',
    line_items: [{ price: priceId, quantity: 1 }],
    success_url: `${FRONTEND_URL}/settings?billing=success`,
    cancel_url: `${FRONTEND_URL}/settings?billing=canceled`,
    subscription_data: {
      metadata: { supabase_user_id: userId },
    },
    // Add region-specific methods here (e.g. 'boleto', 'pix', 'sepa_debit')
    payment_method_types: ['card'],
    allow_promotion_codes: true,
  });

  return c.json({ url: session.url });
});
```

### Customer Portal (Manage Subscription)

```typescript
// POST /api/billing/portal
app.post('/api/billing/portal', authMiddleware, async (c) => {
  const userId = c.get('userId');
  const customerId = await getStripeCustomerId(userId);

  if (!customerId) {
    return c.json({ error: 'no_subscription' }, 400);
  }

  const session = await stripe.billingPortal.sessions.create({
    customer: customerId,
    return_url: `${FRONTEND_URL}/settings`,
  });

  return c.json({ url: session.url });
});
```

## Webhook Handler — The Critical Path

### Endpoint Setup

```typescript
// POST /api/billing/webhook
// IMPORTANT: Raw body required for signature verification
app.post('/api/billing/webhook', async (c) => {
  const sig = c.req.header('stripe-signature');
  const rawBody = await c.req.text();

  let event: Stripe.Event;
  try {
    event = stripe.webhooks.constructEvent(
      rawBody,
      sig!,
      STRIPE_WEBHOOK_SECRET
    );
  } catch (err) {
    console.error('Webhook signature verification failed:', err);
    return c.json({ error: 'invalid_signature' }, 400);
  }

  // Process with idempotency
  await processWebhookEvent(event);
  return c.json({ received: true });
});
```

### Idempotency — The #1 Webhook Landmine

Stripe can send the same event multiple times. Your handler MUST be idempotent.

```typescript
async function processWebhookEvent(event: Stripe.Event) {
  // Check if already processed
  const { data: existing } = await supabase
    .from('stripe_events')
    .select('id')
    .eq('event_id', event.id)
    .single();

  if (existing) {
    console.log(`Event ${event.id} already processed, skipping`);
    return;
  }

  // Process the event
  await handleEvent(event);

  // Mark as processed
  await supabase.from('stripe_events').insert({
    event_id: event.id,
    type: event.type,
    processed_at: new Date().toISOString(),
  });
}
```

### Event Handlers

```typescript
async function handleEvent(event: Stripe.Event) {
  switch (event.type) {
    case 'checkout.session.completed': {
      const session = event.data.object as Stripe.Checkout.Session;
      if (session.mode === 'subscription') {
        const subscription = await stripe.subscriptions.retrieve(
          session.subscription as string,
          { expand: ['items.data.price'] }
        );
        await syncSubscription(subscription);
      }
      break;
    }

    case 'customer.subscription.updated':
    case 'customer.subscription.created': {
      const subscription = event.data.object as Stripe.Subscription;
      await syncSubscription(subscription);
      break;
    }

    case 'customer.subscription.deleted': {
      const subscription = event.data.object as Stripe.Subscription;
      await downgradeToFree(subscription);
      break;
    }

    case 'invoice.payment_failed': {
      const invoice = event.data.object as Stripe.Invoice;
      await handlePaymentFailure(invoice);
      break;
    }

    case 'invoice.paid': {
      // Confirm payment went through — essential for async methods
      const invoice = event.data.object as Stripe.Invoice;
      await confirmPayment(invoice);
      break;
    }

    default:
      console.log(`Unhandled event type: ${event.type}`);
  }
}
```

### Sync Subscription to Supabase

```typescript
async function syncSubscription(subscription: Stripe.Subscription) {
  const userId = subscription.metadata.supabase_user_id;
  if (!userId) {
    console.error('No supabase_user_id in subscription metadata');
    return;
  }

  const price = subscription.items.data[0]?.price;
  const tier = price?.metadata?.tier ?? 'free';
  const status = subscription.status;

  // Map Stripe status to access level
  const hasAccess = ['active', 'trialing'].includes(status);
  const effectiveTier = hasAccess ? tier : 'free';

  // Update profiles table
  await supabase.from('profiles').update({
    tier: effectiveTier,
    stripe_customer_id: subscription.customer as string,
    stripe_subscription_id: subscription.id,
    stripe_subscription_status: status,
    stripe_current_period_end: new Date(
      subscription.current_period_end * 1000
    ).toISOString(),
    updated_at: new Date().toISOString(),
  }).eq('id', userId);

  // Upsert subscription record for audit
  await supabase.from('subscriptions').upsert({
    user_id: userId,
    stripe_subscription_id: subscription.id,
    stripe_price_id: price?.id,
    tier: effectiveTier,
    status,
    current_period_start: new Date(
      subscription.current_period_start * 1000
    ).toISOString(),
    current_period_end: new Date(
      subscription.current_period_end * 1000
    ).toISOString(),
    cancel_at_period_end: subscription.cancel_at_period_end,
    updated_at: new Date().toISOString(),
  }, { onConflict: 'stripe_subscription_id' });
}
```

### Downgrade on Cancellation

```typescript
async function downgradeToFree(subscription: Stripe.Subscription) {
  const userId = subscription.metadata.supabase_user_id;
  if (!userId) return;

  await supabase.from('profiles').update({
    tier: 'free',
    stripe_subscription_status: 'canceled',
    updated_at: new Date().toISOString(),
  }).eq('id', userId);
}
```

## Supabase Schema

```sql
-- Stripe event idempotency log
CREATE TABLE public.stripe_events (
  id bigint GENERATED ALWAYS AS IDENTITY PRIMARY KEY,
  event_id text NOT NULL UNIQUE,
  type text NOT NULL,
  processed_at timestamptz NOT NULL DEFAULT now()
);
CREATE INDEX idx_stripe_events_event_id ON public.stripe_events(event_id);

-- Subscription audit trail
CREATE TABLE public.subscriptions (
  id bigint GENERATED ALWAYS AS IDENTITY PRIMARY KEY,
  user_id uuid NOT NULL REFERENCES auth.users(id) ON DELETE CASCADE,
  stripe_subscription_id text NOT NULL UNIQUE,
  stripe_price_id text,
  tier text NOT NULL DEFAULT 'free',
  status text NOT NULL,
  current_period_start timestamptz,
  current_period_end timestamptz,
  cancel_at_period_end boolean DEFAULT false,
  created_at timestamptz NOT NULL DEFAULT now(),
  updated_at timestamptz NOT NULL DEFAULT now()
);
CREATE INDEX idx_subscriptions_user ON public.subscriptions(user_id);

-- Add billing columns to existing profiles table
ALTER TABLE public.profiles
  ADD COLUMN IF NOT EXISTS tier text NOT NULL DEFAULT 'free',
  ADD COLUMN IF NOT EXISTS stripe_customer_id text,
  ADD COLUMN IF NOT EXISTS stripe_subscription_id text,
  ADD COLUMN IF NOT EXISTS stripe_subscription_status text,
  ADD COLUMN IF NOT EXISTS stripe_current_period_end timestamptz;

-- RLS: users can only see their own subscriptions
ALTER TABLE public.subscriptions ENABLE ROW LEVEL SECURITY;
CREATE POLICY "Users see own subscriptions"
  ON public.subscriptions FOR SELECT
  USING (auth.uid() = user_id);

-- RLS: only service_role can write (webhook handler)
CREATE POLICY "Service role manages subscriptions"
  ON public.subscriptions FOR ALL
  USING (public.is_admin());
```

## Subscription Lifecycle — State Machine

```
                    checkout.session.completed
  (no subscription) ──────────────────────────▶ active
                                                  │
                                     ┌────────────┤
                                     ▼            │
                                 past_due ◄───── invoice.payment_failed
                                     │
                      ┌──────────────┤
                      ▼              ▼
                  canceled      unpaid (after retries exhausted)
                      │
                      ▼
                  (free tier)

  States that grant access: active, trialing
  States that deny access: past_due, canceled, unpaid, incomplete
  Grace period: past_due gets 3 days of continued access (configurable)
```

### Grace Period for Past Due

```typescript
function hasAccess(profile: Profile): boolean {
  if (['active', 'trialing'].includes(profile.stripe_subscription_status)) {
    return true;
  }

  // Grace period: past_due gets 3 days
  if (profile.stripe_subscription_status === 'past_due') {
    const periodEnd = new Date(profile.stripe_current_period_end);
    const gracePeriod = 3 * 24 * 60 * 60 * 1000; // 3 days
    return Date.now() < periodEnd.getTime() + gracePeriod;
  }

  return false;
}
```

## Region-Specific: Async Payment Methods

### Async Payment Methods (PIX, Boleto, SEPA, ACH)

Stripe supports various region-specific payment methods that are
asynchronous — the customer commits to paying, but the actual payment
settles later (minutes to days).

```typescript
// Checkout with multiple async methods
const session = await stripe.checkout.sessions.create({
  // ... other config
  payment_method_types: ['card', 'sepa_debit'], // or ['card', 'boleto', 'pix']
  payment_method_options: {
    // Example: Boleto (Brazil) expiration
    boleto: {
      expires_after_days: 3,
    },
  },
});
```

**Critical**: Async payments are not confirmed at checkout time. The
`checkout.session.completed` event fires when the session is created, NOT
when payment is confirmed. For any async method (PIX, Boleto, SEPA Debit,
ACH, etc.), you MUST also listen for `invoice.paid` to confirm actual
payment before granting access.

### Currency and Locale

- Create Stripe Prices in the currency your customers expect (USD, EUR, GBP, JPY, etc.)
- Stripe handles FX conversion for their own fees
- Display prices using the user's locale formatting (e.g. `Intl.NumberFormat`)

## Frontend Integration Patterns

### Upgrade Prompt Component

```typescript
// src/components/shared/UpgradePrompt.tsx
function UpgradePrompt({ feature, requiredTier }: Props) {
  const { tier } = useAuth();
  const { t } = useTranslation();
  const createCheckout = useCreateCheckout();

  if (tierIncludes(tier, requiredTier)) return null;

  return (
    <div className="rounded-lg border border-amber-500/30 bg-amber-500/10 p-4">
      <p className="text-sm text-amber-200">
        {t('billing.upgradeRequired', { feature, tier: requiredTier })}
      </p>
      <button
        onClick={() => createCheckout.mutate({ priceId: PRICE_IDS[requiredTier] })}
        className="mt-2 rounded bg-emerald-600 px-3 py-1 text-sm"
      >
        {t('billing.upgradeTo', { tier: requiredTier })}
      </button>
    </div>
  );
}
```

### Blur Overlay for Gated Content

```typescript
// Pattern: show blurred data with upgrade CTA
function GatedDataTable({ dataset, tier }: Props) {
  const maxRows = TIER_LIMITS[tier].maxRows;

  return (
    <div className="relative">
      <DataTable dataset={dataset} maxRows={maxRows} />
      {tier === 'free' && (
        <div className="absolute inset-0 top-1/3 backdrop-blur-md flex items-center justify-center">
          <UpgradePrompt feature="full_dataset" requiredTier="pro" />
        </div>
      )}
    </div>
  );
}
```

## Testing Checklist

1. **Checkout flow**: User clicks upgrade → Stripe Checkout → payment → webhook fires → tier updated in Supabase → frontend reflects new tier
2. **Webhook idempotency**: Send same event ID twice → second is skipped
3. **Cancellation**: User cancels in Customer Portal → webhook fires → tier reverts to free at period end
4. **Payment failure**: Card declined → `invoice.payment_failed` → user notified, grace period starts
5. **Async payment delay**: Session created but payment pending → access NOT granted until `invoice.paid`
6. **Tier enforcement**: Free user requests full dataset → receives only the free-tier subset
7. **Rate limiting**: Free user exceeds 30 req/min → 429 response with upgrade suggestion
8. **Webhook signature**: Invalid signature → 400, event not processed

## Anti-Patterns to Reject

| Anti-Pattern | Why It's Wrong | Correct Approach |
|---|---|---|
| Check tier from frontend localStorage | User can edit it | Check tier server-side (Supabase RLS or backend middleware) |
| Grant access on checkout.session.completed for async methods | Payment not yet confirmed | Wait for invoice.paid |
| Store Stripe subscription ID client-side | Security risk | Server-side only, via secure session |
| Process webhooks without idempotency | Duplicate events = wrong state | Event ID dedup table |
| Hardcode tier → features in frontend | Bypassable | Backend enforces, frontend only displays |
| Use Stripe test mode keys in production | Payment failures | Separate env vars, never mix |
| Skip webhook signature verification | Anyone can forge events | Always verify stripe-signature |
| Store raw card numbers | PCI compliance violation | Stripe handles all card data |
| Manual tier updates in DB | Drift from Stripe state | Only webhooks update tier |
