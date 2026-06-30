Deploy the backend. Follow this EXACT sequence — do NOT skip steps:

1. `cd {{PROJECT_PATH}}`
2. `rm -f .git/index.lock`
3. Run `npx tsc --noEmit` — must be zero errors. If errors, STOP and fix.
4. Run `npx vitest run` — all tests must pass. If failures, STOP and fix.
5. `git add` only the specific files changed (NEVER `git add -A`)
6. `git commit -m "<mensagem descritiva>"`
7. `git push origin main`
8. Run your deploy command (e.g. `fly deploy`, `vercel deploy`, `railway up`, `gh workflow run deploy`)
9. Wait ~60s, then verify: `curl -s {{PRODUCTION_URL}}/healthz | jq .`
10. Report the health check result to the user.

CRITICAL: If tsc or vitest fails, fix the errors BEFORE proceeding. Never skip validation.
Copy-paste ready format — the owner is a CLI novice.
