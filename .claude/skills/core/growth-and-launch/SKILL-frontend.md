---
name: growth-and-launch
description: Invite-only product launch, coupon systems, referral tracking,
  trial-to-paid conversion, and waitlist management for SaaS platforms.
  Use when implementing invite codes, early access programs, time-limited
  full-access trials, Stripe coupon/promotion codes, referral reward
  systems, waitlist prioritization, cohort-based conversion tracking,
  or anti-abuse controls for launch programs. Also use when the user
  mentions invite-only, early access, beta launch, coupons, referral,
  waitlist, trial period, launch strategy, go-to-market, or converting
  early users to paying customers. Even for questions about launch
  sequencing, who to invite first, or how to structure trials, use
  this skill. Combines with monetization-and-billing for Stripe
  integration and product-conversion-readiness for UX patterns.
---

# Growth and Launch

## Cardinal Rule

**Early access is a privilege, not a discount.** The V1 invite-only
launch exists to build a high-quality user base that provides real
feedback and converts to paid. Every mechanic — invites, trials,
referrals — must reinforce the positioning of a professional-grade
institutional tool, never a consumer app giving away freebies.

## Positioning Guardrails

{{PROJECT_NAME}} targets sophisticated professional users. Every growth mechanic
must pass this test:

```
"Would a serious professional in the target role find this appropriate?"
  YES → ship it
  NO  → kill it
```

### What This Means in Practice

| ✅ Appropriate | ❌ Kill It |
|----------------|-----------|
| "You've been granted early access" | "🎉 Congrats! You unlocked access!" |
| "Your trial includes full professional feature set" | "FREE TRIAL — ACT NOW!" |
| "Refer a colleague → extend your access" | "Share with 5 friends to unlock!" |
| Weekly intelligence briefing email | Daily streak notifications |
| "Access expires Feb 28" (clean, factual) | "⏰ Only 3 days left! Don't miss out!" |
| Invite code: `INV-INST-A7X9` | Invite code: `FREEBIE2026` |
| "14-day institutional evaluation period" | "14-day FREE trial!!!" |

## Architecture Overview

```
┌──────────────────────────────────────────────────────┐
│                   Launch Funnel                       │
│                                                       │
│  Waitlist → Invite Code → Sign Up → Trial (14 days)  │
│                                  ↓                    │
│                        Full Access (all tiers)        │
│                                  ↓                    │
│                    Trial Expires → Convert or Free    │
│                                                       │
│  Referral: Active user invites → both get +7 days     │
│  Coupon: Strategic partners → custom trial duration    │
└──────────────────────────────────────────────────────┘
```

### Component Map

```
Supabase:
  ├── invite_codes         — codes, limits, expiry, creator
  ├── referrals            — who invited whom, reward status
  ├── trial_periods        — user trial state, dates, source
  ├── coupons              — partner/promo codes with rules
  └── profiles.trial_*     — trial columns on existing table

Engine:
  ├── Trial-aware tier middleware (trial → full access)
  └── No new endpoints (trial is a Supabase concern)

Frontend:
  ├── /invite/:code        — invite landing page
  ├── /settings → trial    — trial status, days remaining
  └── Referral UI          — generate personal invite link
```

## 1. Invite Code System

### Schema

```sql
CREATE TABLE public.invite_codes (
  id bigint GENERATED ALWAYS AS IDENTITY PRIMARY KEY,
  code text NOT NULL UNIQUE,
  created_by uuid REFERENCES auth.users(id),  -- null = system-generated
  type text NOT NULL DEFAULT 'standard'
    CHECK (type IN ('standard', 'partner', 'press', 'institutional')),
  max_uses int NOT NULL DEFAULT 1,
  used_count int NOT NULL DEFAULT 0,
  trial_days int NOT NULL DEFAULT 14,
  tier_during_trial text NOT NULL DEFAULT 'institutional',
  expires_at timestamptz,
  note text,  -- internal: "For [media] journalist", "[partner] partnership"
  created_at timestamptz NOT NULL DEFAULT now(),
  CONSTRAINT code_format CHECK (code ~ '^[A-Z0-9-]{6,24}$')
);

CREATE INDEX idx_invite_codes_code ON public.invite_codes(code);

-- RLS: only admins create/manage, anyone can validate
ALTER TABLE public.invite_codes ENABLE ROW LEVEL SECURITY;

CREATE POLICY "Anyone can validate codes"
  ON public.invite_codes FOR SELECT
  USING (true);

CREATE POLICY "Admins manage codes"
  ON public.invite_codes FOR ALL
  USING (public.is_admin());
```

### Code Generation Patterns

```typescript
// Code format: INV-{TYPE}-{RANDOM}
// Examples:
//   INV-INST-A7X9     — institutional invite
//   INV-PRSS-K3M2     — press/media invite
//   INV-PRTN-A7X9     — partner
//   INV-EARLY-W5N8    — early access (waitlist)

function generateInviteCode(type: 'standard' | 'partner' | 'press' | 'institutional'): string {
  const prefixes = {
    standard: 'EARLY',
    partner: 'PRTN',
    press: 'PRSS',
    institutional: 'INST',
  };
  const random = randomBytes(2).toString('hex').toUpperCase();
  return `INV-${prefixes[type]}-${random}`;
}
```

### Code Validation (Signup Flow)

```typescript
async function validateInviteCode(code: string): Promise<{
  valid: boolean;
  trial_days?: number;
  tier?: string;
  error?: string;
}> {
  const { data: invite } = await supabase
    .from('invite_codes')
    .select('*')
    .eq('code', code.toUpperCase().trim())
    .single();

  if (!invite) return { valid: false, error: 'invalid_code' };
  if (invite.expires_at && new Date(invite.expires_at) < new Date()) {
    return { valid: false, error: 'code_expired' };
  }
  if (invite.used_count >= invite.max_uses) {
    return { valid: false, error: 'code_exhausted' };
  }

  return {
    valid: true,
    trial_days: invite.trial_days,
    tier: invite.tier_during_trial,
  };
}
```

### Code Redemption (Post-Signup)

```typescript
async function redeemInviteCode(userId: string, code: string): Promise<void> {
  const validation = await validateInviteCode(code);
  if (!validation.valid) throw new Error(validation.error);

  const trialEnd = new Date();
  trialEnd.setDate(trialEnd.getDate() + (validation.trial_days ?? 14));

  // Start trial
  await supabase.from('profiles').update({
    tier: validation.tier ?? 'institutional',
    trial_active: true,
    trial_started_at: new Date().toISOString(),
    trial_ends_at: trialEnd.toISOString(),
    trial_source: 'invite',
    invite_code_used: code.toUpperCase(),
  }).eq('id', userId);

  // Record trial
  await supabase.from('trial_periods').insert({
    user_id: userId,
    source: 'invite_code',
    source_ref: code.toUpperCase(),
    tier: validation.tier ?? 'institutional',
    started_at: new Date().toISOString(),
    ends_at: trialEnd.toISOString(),
  });

  // Increment usage
  await supabase.rpc('increment_invite_usage', { invite_code: code.toUpperCase() });
}
```

### Batch Generation for Launch

```sql
-- Generate 50 standard early-access codes for waitlist
INSERT INTO public.invite_codes (code, type, max_uses, trial_days, tier_during_trial, note)
SELECT
  'INV-EARLY-' || upper(substr(md5(random()::text), 1, 4)),
  'standard',
  1,
  14,
  'institutional',
  'Waitlist batch — Feb 2026'
FROM generate_series(1, 50);

-- Generate 5 partner codes (multi-use, 30-day trial)
INSERT INTO public.invite_codes (code, type, max_uses, trial_days, tier_during_trial, note)
VALUES
  ('INV-PRTN-001', 'partner', 20, 30, 'institutional', 'Partner A'),
  ('INV-PRTN-002', 'partner', 20, 30, 'institutional', 'Partner B'),
  ('INV-PRTN-003', 'partner', 20, 30, 'institutional', 'Partner C'),
  ('INV-PRTN-004', 'partner', 10, 21, 'institutional', 'Media outlet A'),
  ('INV-PRTN-INFO', 'partner', 10, 21, 'institutional', 'InfoMoney');
```

## 2. Trial System

### Schema Additions to Profiles

```sql
ALTER TABLE public.profiles
  ADD COLUMN IF NOT EXISTS trial_active boolean DEFAULT false,
  ADD COLUMN IF NOT EXISTS trial_started_at timestamptz,
  ADD COLUMN IF NOT EXISTS trial_ends_at timestamptz,
  ADD COLUMN IF NOT EXISTS trial_source text,
  ADD COLUMN IF NOT EXISTS invite_code_used text;
```

### Trial Period Tracking

```sql
CREATE TABLE public.trial_periods (
  id bigint GENERATED ALWAYS AS IDENTITY PRIMARY KEY,
  user_id uuid NOT NULL REFERENCES auth.users(id) ON DELETE CASCADE,
  source text NOT NULL CHECK (source IN (
    'invite_code', 'referral_bonus', 'coupon', 'manual'
  )),
  source_ref text,      -- invite code, referral user_id, coupon code
  tier text NOT NULL,
  started_at timestamptz NOT NULL,
  ends_at timestamptz NOT NULL,
  converted_at timestamptz,  -- when user subscribed (null = didn't convert)
  created_at timestamptz NOT NULL DEFAULT now()
);

CREATE INDEX idx_trial_periods_user ON public.trial_periods(user_id);
CREATE INDEX idx_trial_periods_ends ON public.trial_periods(ends_at);

ALTER TABLE public.trial_periods ENABLE ROW LEVEL SECURITY;
CREATE POLICY "Users see own trials"
  ON public.trial_periods FOR SELECT
  USING (auth.uid() = user_id);
```

### Tier Resolution Logic

The Engine (or Supabase RLS) must resolve the effective tier
considering both subscriptions AND active trials:

```typescript
function resolveEffectiveTier(profile: Profile): string {
  // 1. Active Stripe subscription takes priority
  if (profile.stripe_subscription_status === 'active') {
    return profile.tier;  // from Stripe webhook sync
  }

  // 2. Active trial
  if (profile.trial_active && profile.trial_ends_at) {
    const trialEnd = new Date(profile.trial_ends_at);
    if (trialEnd > new Date()) {
      return profile.tier;  // tier set during trial activation
    }
    // Trial expired — downgrade
    return 'free';
  }

  // 3. Default
  return 'free';
}
```

### Supabase RLS Function

```sql
CREATE OR REPLACE FUNCTION public.get_effective_tier(uid uuid)
RETURNS text
LANGUAGE sql STABLE SECURITY DEFINER
AS $$
  SELECT CASE
    -- Active Stripe subscription
    WHEN p.stripe_subscription_status = 'active' THEN p.tier
    -- Active trial
    WHEN p.trial_active = true AND p.trial_ends_at > now() THEN p.tier
    -- Default
    ELSE 'free'
  END
  FROM public.profiles p
  WHERE p.id = uid;
$$;
```

### Trial Expiration (Cron or Edge Function)

```typescript
// Supabase Edge Function or Engine cron: run daily
async function expireTrials() {
  const { data: expired } = await supabase
    .from('profiles')
    .select('id, trial_ends_at, invite_code_used')
    .eq('trial_active', true)
    .lt('trial_ends_at', new Date().toISOString())
    .is('stripe_subscription_id', null);  // not converted

  for (const profile of expired ?? []) {
    await supabase.from('profiles').update({
      tier: 'free',
      trial_active: false,
    }).eq('id', profile.id);

    // Record non-conversion for analytics
    await supabase.from('trial_periods').update({
      converted_at: null,  // explicit: did not convert
    })
    .eq('user_id', profile.id)
    .is('converted_at', null);
  }

  return { expired: expired?.length ?? 0 };
}
```

## 3. Referral System

### How It Works

```
User A (active trial or subscriber)
  → Generates personal invite link: {{DOMAIN}}/invite/REF-{USER_A_SHORT_ID}
  → Sends to User B

User B signs up with that link
  → User B gets 14-day trial (standard)
  → User A gets +7 days added to their trial/subscription

Rules:
  - Max 10 referrals per user (prevents abuse)
  - Referral reward only when User B verifies email
  - Self-referral detection (same IP, same email domain)
  - Reward stacks: 10 referrals = 70 extra days
```

### Schema

```sql
CREATE TABLE public.referrals (
  id bigint GENERATED ALWAYS AS IDENTITY PRIMARY KEY,
  referrer_id uuid NOT NULL REFERENCES auth.users(id),
  referred_id uuid NOT NULL REFERENCES auth.users(id),
  referral_code text NOT NULL,
  status text NOT NULL DEFAULT 'pending'
    CHECK (status IN ('pending', 'verified', 'rewarded', 'rejected')),
  reward_days int NOT NULL DEFAULT 7,
  reward_applied_at timestamptz,
  created_at timestamptz NOT NULL DEFAULT now(),
  UNIQUE(referrer_id, referred_id)
);

CREATE INDEX idx_referrals_referrer ON public.referrals(referrer_id);
CREATE INDEX idx_referrals_code ON public.referrals(referral_code);

ALTER TABLE public.referrals ENABLE ROW LEVEL SECURITY;
CREATE POLICY "Users see own referrals"
  ON public.referrals FOR SELECT
  USING (auth.uid() = referrer_id OR auth.uid() = referred_id);
```

### Referral Code Generation

```typescript
// Personal referral codes are deterministic from user ID
function generateReferralCode(userId: string): string {
  const short = createHash('sha256')
    .update(userId)
    .digest('hex')
    .substring(0, 6)
    .toUpperCase();
  return `REF-${short}`;
}
```

### Reward Application

```typescript
async function applyReferralReward(referrerId: string, referralId: string) {
  // Check referral count limit
  const { count } = await supabase
    .from('referrals')
    .select('id', { count: 'exact', head: true })
    .eq('referrer_id', referrerId)
    .eq('status', 'rewarded');

  if ((count ?? 0) >= 10) return;  // max 10 referrals

  // Extend referrer's trial by 7 days
  const { data: profile } = await supabase
    .from('profiles')
    .select('trial_ends_at, trial_active')
    .eq('id', referrerId)
    .single();

  if (profile?.trial_active && profile.trial_ends_at) {
    const currentEnd = new Date(profile.trial_ends_at);
    currentEnd.setDate(currentEnd.getDate() + 7);

    await supabase.from('profiles').update({
      trial_ends_at: currentEnd.toISOString(),
    }).eq('id', referrerId);
  }

  // Mark referral as rewarded
  await supabase.from('referrals').update({
    status: 'rewarded',
    reward_applied_at: new Date().toISOString(),
  }).eq('referrer_id', referrerId).eq('referred_id', referralId);
}
```

### Anti-Abuse

```typescript
async function validateReferral(referrerId: string, newUserEmail: string, ip: string): Promise<{
  valid: boolean;
  reason?: string;
}> {
  // 1. Self-referral by email domain
  const { data: referrer } = await supabase
    .from('profiles')
    .select('email')
    .eq('id', referrerId)
    .single();

  if (referrer?.email) {
    const referrerDomain = referrer.email.split('@')[1];
    const newDomain = newUserEmail.split('@')[1];
    // Block same non-public domain (allow gmail, hotmail, etc.)
    const publicDomains = ['gmail.com', 'hotmail.com', 'outlook.com', 'yahoo.com', 'protonmail.com'];
    if (referrerDomain === newDomain && !publicDomains.includes(referrerDomain)) {
      return { valid: false, reason: 'same_corporate_domain' };
    }
  }

  // 2. Referral limit
  const { count } = await supabase
    .from('referrals')
    .select('id', { count: 'exact', head: true })
    .eq('referrer_id', referrerId);

  if ((count ?? 0) >= 10) {
    return { valid: false, reason: 'referral_limit_reached' };
  }

  return { valid: true };
}
```

## 4. Coupon System

### Stripe-Native Coupons

Use Stripe Promotion Codes (not custom discount logic).
This ensures coupons work correctly with the subscription lifecycle.

```typescript
// Create partner coupons via Stripe API
const coupon = await stripe.coupons.create({
  duration: 'once',
  percent_off: 100,        // 100% off first month = free trial
  max_redemptions: 20,
  metadata: {
    partner: 'hashdex',
    campaign: 'launch_feb_2026',
  },
});

const promoCode = await stripe.promotionCodes.create({
  coupon: coupon.id,
  code: 'HASHDEX2026',       // clean, professional code
  max_redemptions: 20,
  expires_at: Math.floor(Date.now() / 1000) + 90 * 86400, // 90 days
  metadata: {
    partner: 'hashdex',
  },
});
```

### Coupon Types

| Type | Discount | Duration | Example Code | For Whom |
|------|----------|----------|-------------|----------|
| Partner | 100% off 1st month | once | `HASHDEX2026` | Exchange partnerships |
| Press | 100% off 2 months | repeating (2) | `COINDESK2026` | Journalists reviewing product |
| Conference | 50% off 3 months | repeating (3) | `ABCRYPTO26` | Event attendees |
| Loyalty | 20% off forever | forever | — (via Customer Portal) | Long-term users |

### Tracking Coupon → Conversion

```sql
-- Add coupon tracking to profiles
ALTER TABLE public.profiles
  ADD COLUMN IF NOT EXISTS coupon_code_used text,
  ADD COLUMN IF NOT EXISTS acquisition_channel text;
  -- Values: 'organic', 'invite', 'referral', 'partner', 'press'
```

## 5. Waitlist → Invite Flow

### Waitlist Prioritization

The existing waitlist table should be enriched for prioritization:

```sql
-- If waitlist table exists, add priority columns:
ALTER TABLE public.waitlist
  ADD COLUMN IF NOT EXISTS priority int NOT NULL DEFAULT 50,
  ADD COLUMN IF NOT EXISTS persona text,
  ADD COLUMN IF NOT EXISTS invited_at timestamptz,
  ADD COLUMN IF NOT EXISTS invite_code text;

-- Priority scoring:
-- 90+ : Institutional (company email, mentioned fund/desk)
-- 70-89: Developer (mentioned API, integration, bot)
-- 50-69: Power user (mentioned domain-specific workflows)
-- 30-49: General interest
-- 10-29: Low quality (disposable email, no context)
```

### Invite Dispatch (Manual for V1)

```sql
-- Query: Next batch to invite (top 20 by priority)
SELECT id, email, priority, persona, created_at
FROM public.waitlist
WHERE invited_at IS NULL
ORDER BY priority DESC, created_at ASC
LIMIT 20;

-- After generating codes, mark as invited:
UPDATE public.waitlist
SET invited_at = now(), invite_code = 'INV-EARLY-XXXX'
WHERE id = $1;
```

### Invite Email Content (Tone Reference)

```markdown
Subject: Your {{PROJECT_NAME}} access is ready

You requested early access to {{PROJECT_NAME}}. Your account is ready.

Use this code to activate your 14-day institutional evaluation:

    INV-EARLY-A7X9

During your evaluation period, you'll have unrestricted access to:
- [feature 1 that matters to your target user]
- [feature 2 that matters to your target user]
- All 8 WebSocket channels for live data streaming
- Historical analytics (30-day lookback)

Activate here: https://{{DOMAIN}}/signup?code=INV-EARLY-A7X9

— {{OWNER_NAME}}
Founder, {{PROJECT_NAME}}
```

**Tone rules for all communications:**
- No exclamation marks in subject lines
- No emoji in emails
- "Evaluation period", not "free trial"
- "Activate", not "claim your reward"
- Signed by a real person, not "The {{PROJECT_NAME}} Team"
- Factual list of what's included, no hype adjectives

## 6. Engagement Mechanics (Institutional Grade)

### What's Allowed

These reinforce value without cheapening the product:

**Weekly Intelligence Briefing (Email)**

```markdown
Subject: {{PROJECT_NAME}} — Week of Feb 17-23

Market Activity (your monitored pairs):
- 847 events / signals / opportunities detected
- Top result: [one-line summary of the most noteworthy item of the week]
- Trend: [week-over-week comparison of a key metric]

Platform:
- N integrations connected, 99.7% uptime
- New: [any integration, feature, or dataset added this week]

Your trial expires Feb 28. Subscribe to maintain access.
https://{{DOMAIN}}/settings#billing
```

**Usage Summary in Settings**

```typescript
// In /settings, show factual usage stats
function TrialStatus({ profile }: Props) {
  const daysLeft = differenceInDays(new Date(profile.trial_ends_at), new Date());

  return (
    <div className="rounded-lg border border-slate-800 bg-slate-900 p-4">
      <div className="flex items-center justify-between">
        <div>
          <h3 className="text-sm font-medium text-slate-200">
            Institutional Evaluation
          </h3>
          <p className="text-xs text-slate-400 mt-1">
            {daysLeft > 0
              ? `${daysLeft} days remaining`
              : 'Evaluation period ended'}
          </p>
        </div>
        <div className="text-right text-xs text-slate-500">
          <p>API calls: {profile.api_request_count}</p>
          <p>WS sessions: {profile.ws_session_count}</p>
        </div>
      </div>

      {daysLeft <= 3 && daysLeft > 0 && (
        <div className="mt-3 rounded bg-slate-800 p-2 text-xs text-slate-300">
          Your evaluation period ends {formatDate(profile.trial_ends_at)}.
          <a href="/settings#billing" className="text-emerald-400 ml-1">
            Subscribe to continue access →
          </a>
        </div>
      )}
    </div>
  );
}
```

**Referral Section in Settings**

```typescript
function ReferralSection({ userId }: Props) {
  const code = generateReferralCode(userId);
  const { data: referrals } = useQuery(referralQueries.byUser(userId));
  const rewardedCount = referrals?.filter(r => r.status === 'rewarded').length ?? 0;

  return (
    <div className="rounded-lg border border-slate-800 bg-slate-900 p-4">
      <h3 className="text-sm font-medium text-slate-200">
        Refer a Colleague
      </h3>
      <p className="text-xs text-slate-400 mt-1">
        Each verified referral extends your access by 7 days.
      </p>

      <div className="mt-3 flex items-center gap-2">
        <code className="rounded bg-slate-800 px-3 py-1.5 text-xs text-emerald-400 font-mono">
          {{DOMAIN}}/invite/{code}
        </code>
        <CopyButton text={`https://{{DOMAIN}}/invite/${code}`} />
      </div>

      <p className="mt-2 text-xs text-slate-500">
        {rewardedCount}/10 referrals · {rewardedCount * 7} bonus days earned
      </p>
    </div>
  );
}
```

### What's Forbidden

| Mechanic | Why It's Banned |
|----------|----------------|
| Achievement badges | Institutional users don't collect badges |
| Daily login streaks | Desperate retention tactic |
| Points / XP system | Irrelevant to professional tool value |
| Leaderboards | Users don't compete against each other |
| Pop-up notifications for milestones | Interrupt workflow |
| Countdown timers with urgency colors | Pressure tactic |
| "You're in the top 10% of users!" | Meaningless flattery |
| Animated confetti on signup | Consumer app behavior |
| "Share on Twitter for bonus!" | Social spam |

## 7. Conversion Tracking

### Cohort Schema

```sql
CREATE VIEW public.launch_cohort_metrics AS
SELECT
  date_trunc('week', p.created_at) AS cohort_week,
  p.trial_source,
  count(*) AS signups,
  count(*) FILTER (WHERE p.trial_active AND p.trial_ends_at > now()) AS active_trials,
  count(*) FILTER (WHERE p.stripe_subscription_status = 'active') AS converted,
  round(
    count(*) FILTER (WHERE p.stripe_subscription_status = 'active')::numeric /
    NULLIF(count(*), 0) * 100, 1
  ) AS conversion_pct
FROM public.profiles p
WHERE p.trial_started_at IS NOT NULL
GROUP BY 1, 2
ORDER BY 1 DESC;
```

### Key Metrics to Track

| Metric | Query | Target |
|--------|-------|--------|
| Invite → Signup rate | signups / invites_sent | >40% |
| Signup → Active (day 1) | users_with_1_api_call / signups | >60% |
| Trial → Paid conversion | subscribers / trial_completions | >15% |
| Referral rate | users_with_1_referral / active_users | >10% |
| Time to first value | median(first_api_call - signup_at) | <10 min |
| Days active during trial | avg(distinct_days_with_activity) | >7/14 |

## 8. Launch Sequence

### Phase 1: Inner Circle (Week 1)

```
Who: 10-15 hand-picked users
  - 3-4 institutional (funds, desks)
  - 3-4 developers (fintech, algo traders)
  - 2-3 domain journalists / thought leaders
  - 2-3 power users from waitlist

How: Personal email from {{OWNER_NAME}} with unique code
Trial: 30 days, institutional tier
Goal: Qualitative feedback, bug reports, testimonials
```

### Phase 2: Waitlist Batch (Week 3)

```
Who: Top 50 from waitlist by priority score
How: Automated invite email with unique codes
Trial: 14 days, institutional tier
Goal: Validate onboarding flow, measure activation rate
```

### Phase 3: Partner Distribution (Week 5)

```
Who: Exchange partners, media, conferences
How: Multi-use partner codes (20 uses each)
Trial: 14-30 days depending on partner
Goal: Volume, brand awareness, backlinks
```

### Phase 4: Open with Referral (Week 8+)

```
Who: Anyone (signup open, no invite required)
Trial: 7 days institutional, then free tier
Referral: Active from day 1
Goal: Organic growth, referral loop
```

## Anti-Patterns to Reject

| Anti-Pattern | Why It's Wrong | Correct Approach |
|---|---|---|
| Open signup from day 1 | No feedback quality control | Invite-only → waitlist → open |
| Same trial for everyone | No differentiation by value | 30d for VIPs, 14d standard, 7d open |
| No trial expiration enforcement | Users stay free forever | Cron job expires trials daily |
| Invite codes as "FREECRYPTO" | Cheapens institutional positioning | Clean codes: INV-INST-A7X9 |
| Gamified referrals with tiers | Consumer app mechanics | Simple: refer → +7 days, max 10 |
| Urgency-based trial expiry UI | Pressure tactic | Factual: "X days remaining" |
| Mass email blast to waitlist | Low quality, high spam risk | Batch by priority, 50 at a time |
| No conversion tracking | Flying blind | Cohort metrics from week 1 |
| Infinite trial extensions | Never converts to paid | Cap referral bonus at 70 days total |
| Coupon codes on public pages | Devalues paid plans | Partner codes shared privately only |
