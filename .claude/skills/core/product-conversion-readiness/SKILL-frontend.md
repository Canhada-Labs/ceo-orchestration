---
name: product-conversion-readiness
description: Patterns for transforming a functional product into one that
  converts users to paying customers. Covers onboarding flows, contextual
  tooltips, glossaries, empty states, upgrade prompts, trust signals (CNPJ,
  About page, uptime badges), notifications (Telegram, webhooks, email),
  data export with timestamps, and paywall UX. Use when implementing
  onboarding wizards, tooltip systems, glossary pages, blur-to-upgrade
  overlays, Telegram bot alerts, webhook delivery, CSV/PDF export, trust
  pages, or any UX bridging the gap between working product and paying
  users. Also use when the user mentions onboarding, tooltips, glossary,
  empty state, upgrade prompt, trust signals, Telegram alerts, export,
  conversion, paywall, or why users are not paying. Even for making the
  product more approachable or converting free users, use this skill.
  Combines with monetization-and-billing for payment integration.
---

# Product Conversion Readiness

## Cardinal Rule

**The product works. The data is correct. Users don't pay because they
don't understand the value, don't trust the source, or can't act on the
data.** Every pattern in this skill addresses one of these three gaps:
comprehension, trust, or actionability.

## The {{PROJECT_NAME}} Conversion Gap

QA audits with user personas confirm a recurring pattern:

| Persona | Verdict | Blocker |
|---------|---------|---------|
| Analyst | Would pay, with conditions | Needs legal entity, source references, citable export |
| Developer | Won't pay yet | Needs API keys, 30-day uptime, quickstart |
| Power User | Won't pay pure | Needs push alerts (messaging channel) |
| Beginner | Won't pay yet | Needs onboarding + glossary in local language |
| Mobile/Casual | Won't pay | Needs readable main page + fast widget |
| Ops Lead (advanced) | Won't pay for execution | Needs row-level detail inline |
| Developer (API) | Close to paying | Needs API keys + 30-day history |
| Ops Lead (basic) | Won't pay yet | Needs configurable alerts + drill-down |

**Pattern**: Zero personas said the data was wrong. Every blocker is either
comprehension (onboarding, tooltips), trust (legal entity, uptime, About), or
actionability (alerts, export, API).

## 1. Onboarding Flow

### Progressive Disclosure, Not Wall of Text

New users see a 3-step guided tour, not a blank dashboard.

```typescript
// src/components/shared/OnboardingWizard.tsx
interface OnboardingStep {
  id: string;
  target: string;        // CSS selector of element to highlight
  title: string;         // i18n key
  description: string;   // i18n key
  position: 'top' | 'bottom' | 'left' | 'right';
  action?: 'click' | 'hover' | 'none';
}

const ONBOARDING_STEPS: OnboardingStep[] = [
  {
    id: 'dashboard',
    target: '[data-tour="dashboard-table"]',
    title: 'onboarding.step1.title',        // "Your Overview"
    description: 'onboarding.step1.desc',    // "Real-time data from N sources..."
    position: 'bottom',
  },
  {
    id: 'detail',
    target: '[data-tour="item-selector"]',
    title: 'onboarding.step2.title',        // "Dive Into Any Item"
    description: 'onboarding.step2.desc',    // "Click any row to see the full detail view..."
    position: 'right',
  },
  {
    id: 'signals',
    target: '[data-tour="signal-badge"]',
    title: 'onboarding.step3.title',        // "Spot Opportunities"
    description: 'onboarding.step3.desc',    // "Green badges show live anomalies..."
    position: 'left',
  },
];
```

### Onboarding State (Supabase)

```sql
ALTER TABLE public.profiles
  ADD COLUMN IF NOT EXISTS onboarding_completed boolean DEFAULT false,
  ADD COLUMN IF NOT EXISTS onboarding_step text DEFAULT 'welcome';
```

### Rules

- **Never show onboarding to returning users.** Check `onboarding_completed`.
- **Allow skip at every step.** "Skip tour" button always visible.
- **Persist progress.** If user closes mid-tour, resume from last step.
- **Language-aware.** All text via i18n, with your primary locale as the richest.
- **Mobile-friendly.** Tour highlights work on mobile viewports.

## 2. Contextual Tooltip System

### Architecture

```typescript
// src/components/shared/InfoTooltip.tsx
interface InfoTooltipProps {
  termKey: string;  // glossary term key, e.g., "mrr"
  children: React.ReactNode;
}

function InfoTooltip({ termKey, children }: InfoTooltipProps) {
  const { t } = useTranslation('glossary');
  const definition = t(`${termKey}.definition`);
  const example = t(`${termKey}.example`, { defaultValue: '' });

  return (
    <Tooltip>
      <TooltipTrigger asChild>
        <span className="inline-flex items-center gap-1 border-b border-dotted border-slate-600 cursor-help">
          {children}
          <HelpCircle className="h-3 w-3 text-slate-500" />
        </span>
      </TooltipTrigger>
      <TooltipContent className="max-w-xs">
        <p className="text-xs font-medium text-slate-200">{definition}</p>
        {example && (
          <p className="mt-1 text-xs text-slate-400 italic">{example}</p>
        )}
      </TooltipContent>
    </Tooltip>
  );
}
```

### Glossary Terms (i18n)

Every domain has its jargon. The point is to have a glossary — the entries
below illustrate the pattern (a productivity/analytics SaaS defining its
own terms for end users). Adapt to your domain.

```json
// src/i18n/locales/en/glossary.json
{
  "mrr": {
    "definition": "Monthly Recurring Revenue. The predictable portion of revenue from active subscriptions, normalized to a monthly figure.",
    "example": "1 annual plan at $1,200/yr = $100 MRR"
  },
  "churn": {
    "definition": "The percentage of customers who cancel in a given period. Lower churn = healthier product.",
    "example": "5% monthly churn means 5 out of every 100 customers leave each month"
  },
  "cohort": {
    "definition": "A group of users who share a common signup period, used to compare behavior over time.",
    "example": "The Jan 2026 cohort has 82% retention after 90 days"
  },
  "burnRate": {
    "definition": "How fast the business spends cash each month. Usually compared against runway.",
    "example": "$50k/month burn with $600k in the bank = 12 months of runway"
  },
  "activeUsers": {
    "definition": "Users who took a meaningful action within the period. We use 'active' to mean 'performed at least one core action'.",
    "example": "A user who only logged in but did nothing else is NOT counted as active"
  },
  "staleness": {
    "definition": "Age of the data. Values older than 15 seconds are marked as 'stale' and do not trigger alerts.",
    "example": "Amber badge = data between 15-60s. Red = >60s."
  },
  "activation": {
    "definition": "The moment a new user reaches their first 'aha' outcome — the point where they understand the product's value.",
    "example": "For a project tool, activation = 'first task completed by a teammate'"
  }
}
```

### Where to Place Tooltips

| Component | Term | Why |
|-----------|------|-----|
| KPI Summary Bar | MRR, active users | Most confusing metrics for beginners |
| Analytics Table | cohort, retention | Core differentiator needs explanation |
| Alerts Panel | threshold, anomaly | Domain concepts need localized context |
| Data Quality Badge | staleness | Users don't know what colors mean |
| Regional display | locale-specific reference | Local context-specific values |
| Trend Chart | time buckets | What "last 7 days" means practically |

**Rule**: Every technical term that appears in the UI for the first time
gets a tooltip. If a term appears in multiple components, the tooltip is
always available (not just on first occurrence).

## 3. Empty States

### Every Data Section Needs an Empty State

```typescript
// Pattern: EmptyState component
interface EmptyStateProps {
  icon: LucideIcon;
  title: string;          // i18n key
  description: string;    // i18n key
  action?: {
    label: string;        // i18n key
    onClick: () => void;
  };
}

function EmptyState({ icon: Icon, title, description, action }: EmptyStateProps) {
  const { t } = useTranslation();
  return (
    <div className="flex flex-col items-center justify-center py-12 text-center">
      <Icon className="h-8 w-8 text-slate-600 mb-3" />
      <h3 className="text-sm font-medium text-slate-300">{t(title)}</h3>
      <p className="mt-1 text-xs text-slate-500 max-w-xs">{t(description)}</p>
      {action && (
        <button onClick={action.onClick}
          className="mt-3 rounded bg-emerald-600 px-3 py-1.5 text-xs">
          {t(action.label)}
        </button>
      )}
    </div>
  );
}
```

### Empty State Catalog

| Section | When Empty | Message | Action |
|---------|-----------|---------|--------|
| Dashboard | Backend offline | "Connecting to data sources..." | Retry button |
| Detail View | Item not available | "This item is not available in this source" | Show alternatives |
| Signals | No events | "No signals detected right now. All quiet." | Link to history |
| Alerts | No alerts set | "Configure alerts to be notified of signals" | Setup alert CTA |
| API Keys | Free tier | "Generate API keys on the Pro plan" | Upgrade CTA |
| History | No data yet | "Historical data starts accumulating after 24h" | — |
| Watchlist | Empty | "Add items to your watchlist to track them" | Add item CTA |

**Rule**: Never show a blank white space or a loading spinner that never resolves.
Every empty state must tell the user WHY it's empty and WHAT to do next.

## 4. Trust Signals

### What Trust Signals Are Needed

| Signal | Where | Why |
|--------|-------|-----|
| Legal entity info | Footer + About page | Jurisdictional legal requirement (e.g. CNPJ in Brazil, company number in UK, EIN in US) |
| About page | /about | Who built this, why, what's the mission |
| Uptime badge | Footer + Status page | Proves reliability |
| Data freshness indicator | Every data component | Shows data is live, not cached |
| Scale signal | Landing | A concrete number that signals "real product" (e.g. "N integrations", "K events/day", "M users") |
| Activity signal | Landing | A second concrete number showing the product is active (e.g. "X operations completed today") |
| Open-source status | About (if applicable) | Transparency builds trust |
| Contact info | Footer | Email, Twitter/X — reachable humans |

### About Page Content Structure

```markdown
## About {{PROJECT_NAME}}

### What We Do
{{PROJECT_NAME}} [one-sentence product description — what you do and for whom].

### Why Trust Our Data / Service
- [Concrete differentiator 1 — e.g. "Real-time data, not delayed feeds"]
- [Concrete differentiator 2 — e.g. "Validated with [methodology]"]
- [Concrete differentiator 3 — e.g. "Every datapoint has a quality indicator"]
- [Concrete differentiator 4 — e.g. "Sub-second latency"]

### Who We Are
- Founded by {{FOUNDER_NAME}} in {{CITY}}, {{COUNTRY}}
- Legal entity: {{LEGAL_ID}} (e.g. CNPJ, company number, EIN)
- Contact: contact@{{DOMAIN}}

### How It Works
[Brief technical explanation accessible to non-developers]
```

### Uptime Badge

```typescript
// Use a simple status indicator in the footer
function UptimeBadge() {
  const { data } = useQuery(engineQueries.health());
  const isHealthy = data?.status === 'ok';

  return (
    <a href="/status" className="inline-flex items-center gap-1.5 text-xs">
      <span className={`h-2 w-2 rounded-full ${
        isHealthy ? 'bg-emerald-400 animate-pulse' : 'bg-red-400'
      }`} />
      <span className="text-slate-500">
        {isHealthy ? 'All systems operational' : 'Degraded'}
      </span>
    </a>
  );
}
```

### Data Freshness Indicator

```typescript
// Show age of data on every component that displays market data
function DataAge({ timestamp }: { timestamp: string }) {
  const age = useDataAge(timestamp);  // returns seconds

  if (age < 5) return <span className="text-emerald-400 text-[10px]">LIVE</span>;
  if (age < 15) return <span className="text-emerald-400 text-[10px]">{age}s</span>;
  if (age < 60) return <span className="text-amber-400 text-[10px]">{age}s ⚠</span>;
  return <span className="text-red-400 text-[10px]">STALE</span>;
}
```

## 5. Alert System (Telegram + Webhook)

### Why Alerts Convert Users

The QA pattern is unanimous: power users will pay for alerts that reach
them where they already are (chat/messaging, not just in-browser). An alert
is the bridge between "data exists" and "I act on it."

### Architecture

```
Backend detects event
  → Writes to alerts table
  → Publishes to WS channel "alerts"
  → Alert Dispatcher checks user preferences:
      ├── in-app: WS push (existing)
      ├── messenger: Send via Chat Bot API (Slack, Telegram, etc.)
      ├── webhook: POST to user's URL
      └── email: Queue for batch send (low priority)
```

### Supabase Schema for Alert Preferences

```sql
CREATE TABLE public.alert_preferences (
  id bigint GENERATED ALWAYS AS IDENTITY PRIMARY KEY,
  user_id uuid NOT NULL REFERENCES auth.users(id) ON DELETE CASCADE,
  channel text NOT NULL CHECK (channel IN ('in_app', 'telegram', 'webhook', 'email')),
  enabled boolean NOT NULL DEFAULT true,
  config jsonb NOT NULL DEFAULT '{}',
  -- telegram: { chat_id: "123456" }
  -- webhook: { url: "https://...", secret: "hmac_key" }
  -- email: {} (uses profile email)
  created_at timestamptz NOT NULL DEFAULT now(),
  UNIQUE(user_id, channel)
);

ALTER TABLE public.alert_preferences ENABLE ROW LEVEL SECURITY;
CREATE POLICY "Users manage own alerts"
  ON public.alert_preferences FOR ALL
  USING (auth.uid() = user_id);

CREATE TABLE public.alert_rules (
  id bigint GENERATED ALWAYS AS IDENTITY PRIMARY KEY,
  user_id uuid NOT NULL REFERENCES auth.users(id) ON DELETE CASCADE,
  name text NOT NULL,
  rule_type text NOT NULL CHECK (rule_type IN (
    'threshold_exceeded', 'anomaly_detected', 'metric_cross',
    'staleness', 'integration_down', 'volume_spike'
  )),
  config jsonb NOT NULL,
  -- threshold_exceeded: { metric: "active_users", min_value: 100 }
  -- anomaly_detected: { min_score: 0.9 }
  -- metric_cross: { metric: "mrr", direction: "above", value: "50000" }
  enabled boolean NOT NULL DEFAULT true,
  last_triggered_at timestamptz,
  cooldown_minutes int NOT NULL DEFAULT 5,
  created_at timestamptz NOT NULL DEFAULT now()
);

ALTER TABLE public.alert_rules ENABLE ROW LEVEL SECURITY;
CREATE POLICY "Users manage own rules"
  ON public.alert_rules FOR ALL
  USING (auth.uid() = user_id);
```

### Telegram Bot Integration

```typescript
// Engine: Telegram alert sender
const TELEGRAM_BOT_TOKEN = process.env.TELEGRAM_BOT_TOKEN;

async function sendTelegramAlert(chatId: string, alert: Alert) {
  const message = formatAlertMessage(alert);

  await fetch(`https://api.telegram.org/bot${TELEGRAM_BOT_TOKEN}/sendMessage`, {
    method: 'POST',
    headers: { 'Content-Type': 'application/json' },
    body: JSON.stringify({
      chat_id: chatId,
      text: message,
      parse_mode: 'HTML',
      disable_web_page_preview: true,
    }),
  });
}

function formatAlertMessage(alert: Alert): string {
  switch (alert.type) {
    case 'anomaly_detected':
      return [
        `<b>Anomaly Alert</b>`,
        `Metric: ${alert.metric}`,
        `Source: ${alert.source}`,
        `Score: ${alert.score} (threshold ${alert.threshold})`,
        `Current value: ${alert.current_value}`,
        `<i>${new Date().toLocaleTimeString()}</i>`,
      ].join('\n');
    // ... other types
  }
}
```

### Webhook Delivery

```typescript
async function sendWebhookAlert(url: string, secret: string, alert: Alert) {
  const payload = JSON.stringify({
    event: 'alert',
    type: alert.type,
    data: alert,
    timestamp: new Date().toISOString(),
  });

  const signature = createHmac('sha256', secret)
    .update(payload)
    .digest('hex');

  const res = await fetch(url, {
    method: 'POST',
    headers: {
      'Content-Type': 'application/json',
      'X-{{PROJECT_NAME}}-Signature': signature,
    },
    body: payload,
    signal: AbortSignal.timeout(5000),
  });

  if (!res.ok) {
    console.warn(`Webhook delivery failed: ${url} → ${res.status}`);
    // TODO: retry with exponential backoff, disable after N failures
  }
}
```

## 6. Data Export

### Export Types by Persona

| Persona | Needs | Format |
|---------|-------|--------|
| Analyst | Citable report | PDF with timestamp + source |
| Developer | Raw data | JSON / CSV |
| Enterprise | Audit trail | CSV with all fields |
| Power User | Quick snapshot | CSV of current state |

### CSV Export Component

```typescript
// src/lib/export.ts
interface ExportOptions {
  filename: string;
  headers: string[];
  rows: string[][];
  metadata?: {
    source: string;        // "{{DOMAIN}}"
    generated_at: string;  // ISO timestamp
    scope?: string;        // e.g. date range or entity filter
    dataset?: string;
    disclaimer: string;
  };
}

function exportToCSV({ filename, headers, rows, metadata }: ExportOptions) {
  const lines: string[] = [];

  // Metadata header (for citability)
  if (metadata) {
    lines.push(`# Source: ${metadata.source}`);
    lines.push(`# Generated: ${metadata.generated_at}`);
    if (metadata.scope) lines.push(`# Scope: ${metadata.scope}`);
    if (metadata.dataset) lines.push(`# Dataset: ${metadata.dataset}`);
    lines.push(`# ${metadata.disclaimer}`);
    lines.push('');
  }

  lines.push(headers.join(','));
  rows.forEach(row => lines.push(row.map(cell =>
    cell.includes(',') ? `"${cell}"` : cell
  ).join(',')));

  const blob = new Blob([lines.join('\n')], { type: 'text/csv' });
  const url = URL.createObjectURL(blob);
  const a = document.createElement('a');
  a.href = url;
  a.download = `${filename}_${new Date().toISOString().slice(0, 10)}.csv`;
  a.click();
  URL.revokeObjectURL(url);
}
```

### Export Button Pattern

```typescript
// Add to any data table/chart component
function ExportButton({ getData, filename, scope }: ExportButtonProps) {
  const { t } = useTranslation();

  return (
    <button
      onClick={() => {
        const { headers, rows } = getData();
        exportToCSV({
          filename,
          headers,
          rows,
          metadata: {
            source: '{{DOMAIN}}',
            generated_at: new Date().toISOString(),
            scope,
            disclaimer: t('export.disclaimer'),
          },
        });
      }}
      className="rounded border border-slate-700 px-2 py-1 text-xs text-slate-400 hover:bg-slate-800"
    >
      <Download className="h-3 w-3 inline mr-1" />
      {t('export.csv')}
    </button>
  );
}
```

## 7. Upgrade Prompts — Contextual, Not Annoying

### Rules

1. **Show upgrade prompts IN CONTEXT** — when user hits a tier limit, not randomly.
2. **Never block the free experience.** Free tier must be genuinely useful.
3. **Show what they're missing.** Blur overlay on premium data > hard paywall.
4. **One prompt per session maximum.** Don't nag.
5. **Include value proposition.** Not just "Upgrade", but "See full detail (20 rows) with Pro".

### Upgrade Trigger Points

| Trigger | When | Message |
|---------|------|---------|
| Row limit | Free user views a detail table | "Showing 5 of 20 rows. Pro unlocks the full view." |
| Signals feed | Free user opens /signals | "Real-time signals require Pro." |
| API keys | Free user clicks API Keys in /settings | "API Keys are available on the Pro plan." |
| Historical data | Free user queries >24h | "30-day history is available on Pro." |
| Alert setup | Free user tries to create alert | "Messenger/webhook alerts are on the Pro plan." |
| Export | Free user exports >100 rows | "Full export is available on Pro." |

### Implementation Pattern

```typescript
// src/hooks/useTierGate.ts
function useTierGate(requiredTier: 'pro' | 'enterprise') {
  const { tier } = useAuth();
  const [dismissed, setDismissed] = useState(false);

  const isGated = !tierIncludes(tier, requiredTier);
  const showPrompt = isGated && !dismissed;

  return {
    isGated,
    showPrompt,
    dismiss: () => setDismissed(true),
    requiredTier,
    currentTier: tier,
  };
}

// Usage in component:
function SignalsPanel() {
  const gate = useTierGate('pro');

  return (
    <div className="relative">
      <SignalsTable />
      {gate.showPrompt && (
        <BlurOverlay
          message={t('billing.signalsRequirePro')}
          tier="pro"
          onDismiss={gate.dismiss}
        />
      )}
    </div>
  );
}
```

## 8. Landing Page Conversion Elements

### Above the Fold

```
┌──────────────────────────────────────────────┐
│  "N integrations. One source of truth."     │
│  Real-time {{DOMAIN}} intelligence.          │
│                                               │
│  [See Live Data →]  [Create Free Account]     │
│                                               │
│  ┌─────────────────────────────────────────┐ │
│  │  Live strip: key metrics updating...    │ │
│  └─────────────────────────────────────────┘ │
│                                               │
│  N entities   Sub-second   Accurate          │
└──────────────────────────────────────────────┘
```

### Social Proof / Credibility Strip

```
┌──────────────────────────────────────────────┐
│  "N events processed in the last 24 hours.   │
│   Average latency: Xms."                     │
│                                               │
│  Integrations:                                │
│  [Source A] [Source B] [Source C] ...        │
└──────────────────────────────────────────────┘
```

### Pricing Section

```typescript
// Use the existing blur overlay pattern from the frontend
// Show 3 tiers with clear feature comparison
// CTA for Free: "Start Free" (no credit card)
// CTA for Pro: "Start 7-Day Trial" (with Stripe Checkout)
// CTA for Enterprise: "Contact Us" (Calendly or email)
```

## Implementation Priority

| Priority | What | Impact on Conversion | Effort |
|----------|------|---------------------|--------|
| 1 | Trust signals (About, legal entity, uptime) | High — removes "who is this?" friction | 2h |
| 2 | Tooltip system + glossary | High — unlocks beginner persona | 4h |
| 3 | CSV export with metadata | Medium — unlocks analyst persona | 2h |
| 4 | Contextual upgrade prompts | High — converts free → Pro | 3h |
| 5 | Empty states for all sections | Medium — reduces confusion | 2h |
| 6 | Onboarding wizard | Medium — first-time experience | 4h |
| 7 | Messenger alerts (Slack/Telegram/etc.) | High — unlocks power-user persona | 6h |
| 8 | Webhook delivery | Medium — unlocks developer persona | 4h |

**Total**: ~27h of implementation. Trust signals first (smallest effort,
biggest trust impact), then tooltips (biggest comprehension impact).

## Anti-Patterns to Reject

| Anti-Pattern | Why It's Wrong | Correct Approach |
|---|---|---|
| Hard paywall on all data | Users can't evaluate before paying | Generous free tier + blur on premium |
| Popup upgrade prompts | Annoying, reduces trust | Contextual, at point of need |
| Onboarding as mandatory | Experienced users skip it | Optional, skippable, resumable |
| Single-locale tooltips | Excludes non-English users | Localize for your primary audience |
| Export without timestamp | Data not citable | Always include source + timestamp |
| Trust page with Lorem Ipsum | Worse than no trust page | Real content or don't ship |
| Messenger bot without rate limit | Spam users = churn | Cooldown per rule (5 min default) |
| Alert on every event | Thousands/day = unusable | Threshold + cooldown + user-configurable |
| Showing empty spinners | User thinks it's broken | Empty state with explanation |
