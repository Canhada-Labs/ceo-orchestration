Check engine health status. Run these commands and report results:

1. `curl -s {{PRODUCTION_URL}}/healthz | jq .`
2. `curl -s {{PRODUCTION_URL}}/status/public | jq .`

Report:
- Status (ok/error)
- live_books count
- Uptime
- Any warnings or anomalies
- Exchange count and status

If healthz returns error or timeout, report CRITICAL and suggest checking your platform's logs (e.g. `fly logs`, `vercel logs`, `railway logs`).
