<!-- PLAN-153 Wave C progressive-disclosure pilot (rides SP-022 via /skill-review). Extracted VERBATIM from core/testing-strategy/SKILL.md (pre-split state); zero content loss. Edit only via a new SP-NNN that bumps the parent SKILL.md version. -->

## CI Integration

### Anti-Pattern

```yaml
# BROKEN -- no tests
- checkout
- deploy  # Deploys untested code to production
```

### Required Pipeline

```yaml
# .github/workflows/ci.yml
name: CI

on:
  push:
    branches: [main]
  pull_request:
    branches: [main]

jobs:
  typecheck:
    runs-on: ubuntu-latest
    steps:
      - uses: actions/checkout@v4
      - uses: actions/setup-node@v4
        with:
          node-version: 20
          cache: npm
      - run: npm ci
      - run: npx tsc --noEmit

  test:
    runs-on: ubuntu-latest
    needs: typecheck
    steps:
      - uses: actions/checkout@v4
      - uses: actions/setup-node@v4
        with:
          node-version: 20
          cache: npm
      - run: npm ci
      - run: npx vitest run --reporter=verbose
      - run: npx vitest run --coverage
      - uses: actions/upload-artifact@v4
        with:
          name: coverage
          path: coverage/

  deploy:
    runs-on: ubuntu-latest
    needs: [typecheck, test]
    if: github.ref == 'refs/heads/main'
    steps:
      - uses: actions/checkout@v4
      - name: Deploy
        # Replace with your platform's deploy step. Examples:
        #   Fly.io:   uses: superfly/flyctl-actions/setup-flyctl@master
        #             run: flyctl deploy --remote-only
        #             env: FLY_API_TOKEN: ${{ secrets.FLY_API_TOKEN }}
        #   Vercel:   uses: amondnet/vercel-action@v25
        #   Railway:  uses: bervProject/railway-deploy@main
        #   AWS ECS:  uses: aws-actions/amazon-ecs-deploy-task-definition@v1
        #   Cloud Run: uses: google-github-actions/deploy-cloudrun@v2
        run: echo "configure your deploy step"
```

### CI Rules

1. **Tests MUST pass before deploy.** No exceptions.
2. **TypeScript MUST compile cleanly.** Zero errors.
3. **Coverage MUST NOT decrease** on PR (fail if coverage drops).
4. **Deploy is blocked** until both typecheck and test jobs succeed.
5. **PR checks:** typecheck + test run on every PR.
6. **Main branch:** typecheck + test + deploy.

