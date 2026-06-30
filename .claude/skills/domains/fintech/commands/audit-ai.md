---
description: Audit the AI integration across the frontend. Discovery (what exists), audit (does it work), spec (how it should work), gap analysis.
---

# AI Integration Audit

Read CLAUDE.md first. Generate audit reports under `audit/ai/`; do not modify application code or configuration.

## Part 1: DISCOVERY — What exists?

```bash
# Find any AI-related components/hooks/utils
grep -rl "anthropic\|claude\|openai\|ai-\|AI\|askAI\|AskIA\|market.brief\|MarketBrief\|intelligence\|insight\|journal\|briefing\|chat\|copilot" src/ --include="*.tsx" --include="*.ts" | sort

# Find AI API calls
grep -rn "api.anthropic\|/v1/messages\|/ai/\|edge-function\|supabase.*functions" src/ --include="*.tsx" --include="*.ts"

# Find AI env var names without reading local secret values
{
  grep -RohE 'VITE_[A-Z0-9_]*(AI|ANTHROPIC|CLAUDE|OPENAI)[A-Z0-9_]*' src/ vite.config* --include="*.ts" --include="*.tsx" 2>/dev/null
  grep -hoE '^[[:space:]]*VITE_[A-Z0-9_]*(AI|ANTHROPIC|CLAUDE|OPENAI)[A-Z0-9_]*[[:space:]]*=' .env.example .env.sample 2>/dev/null | sed -E 's/^[[:space:]]*//; s/[[:space:]]*=.*$//'
} | sort -u

# Find Edge Functions
ls -la supabase/functions/ 2>/dev/null
find . -path "*/functions/ai*" -o -path "*/functions/*analysis*" -o -path "*/functions/*brief*" -o -path "*/functions/*insight*" 2>/dev/null
```

For each file found, document:
- **File:** path + lines
- **Type:** component | hook | util | edge function | store | query
- **What it does:** 1 sentence
- **How activated:** button? automatic? route?
- **API called:** endpoint? model? streaming?
- **Context injected:** what engine/page data sent as system prompt?
- **Language:** respects i18n? hardcoded English?
- **Cost control:** rate limit? cache? token budget?

If NOTHING found: document "No AI integration found" and skip to Part 3.

## Part 2: AUDIT — Does it work?

### UX
- How is AI displayed? Modal? Drawer? Side panel? Inline?
- Does it BLOCK the page? Can user scroll with AI open?
- Is container resizable? Mobile version?
- Does AI respond in user's locale (pt-BR/en/es)?
- Does AI know current page/pair/visible data?
- Does conversation history persist between pages? Sessions?
- Streaming (token by token) or full response?

### The "Journal"/Briefing
- Generated automatically or on demand?
- Structure: headers, bullets, paragraphs?
- Readable and fluid or data dump?
- Answers the 5 trader questions:
  1. Market bullish or bearish?
  2. Any opportunities right now?
  3. What happened while I was away?
  4. Any relevant macro?
  5. What should I consider doing?

### Financial Guardrails
- System prompt includes "not investment advice" disclaimer?
- AI refuses direct advice ("buy X")?
- Applicable financial regulation in your jurisdiction referenced?

### Cost
- Model used? (Haiku/Sonnet/Opus)
- Rate limit per user?
- User sees remaining messages?
- Cache for common responses?
- Fallback when API fails?

## Part 3: SPEC — How it SHOULD work

Document the ideal model as "AI Copilot/Assistant":

### Side Panel
- 380px right panel, page stays visible and scrollable
- Context-aware (current page, selected pair, live data)
- Streaming responses, markdown rendered
- Rate limited: Free 10msg/day (Haiku), PRO 100msg/day (Sonnet)
- Mobile: bottom sheet 60%

### Inline Insights
- 10-15 key components get insight slots
- Phase 1: template-based (no AI cost)
- Phase 2: Claude-generated, cached 15min
- Click insight → opens side panel with context

### Daily Briefing
- Generated 1x at a daily configured time (e.g., start-of-trading-session local time), cached globally
- 5 sections: Market Today, What Happened, Macro, Opportunities, Summary
- i18n: pt-BR, en, es
- Cost: ~$0.10/day

## Part 4: GAP ANALYSIS

| Dimension | Status | Score |
|-----------|--------|-------|
| Side Panel | ❌/🟡/✅ | 0-100% |
| Inline Insights | ❌/🟡/✅ | 0-100% |
| Daily Briefing | ❌/🟡/✅ | 0-100% |
| Page Context | ❌/🟡/✅ | 0-100% |
| i18n in AI | ❌/🟡/✅ | 0-100% |
| Rate Limiting | ❌/🟡/✅ | 0-100% |
| Streaming | ❌/🟡/✅ | 0-100% |
| Guardrails | ❌/🟡/✅ | 0-100% |
| Mobile | ❌/🟡/✅ | 0-100% |
| Cost Control | ❌/🟡/✅ | 0-100% |

Score with anchors: 0 = absent, 25 = stub/non-functional, 50 = partial or manual, 75 = mostly working with known gaps, 100 = complete, tested, and documented.

Classify gaps as: **Critical** (blocks launch), **Important** (degrades experience), **Desirable** (improves perception).

## Output

```bash
mkdir -p audit/ai
# Save to: audit/ai/DISCOVERY.md, audit/ai/AUDIT.md, audit/ai/SPEC.md, audit/ai/GAP_ANALYSIS.md
git add audit/ai/
git commit -m "audit(ai): AI integration discovery + audit + spec + gap analysis"
```
