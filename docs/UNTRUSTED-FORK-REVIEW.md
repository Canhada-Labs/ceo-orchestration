# UNTRUSTED-FORK-REVIEW — patterns for reviewing PRs from untrusted forks

> **Status:** opt-in adopter pattern. NOT enforced by `validate-governance.sh`. NOT a governance gate. Purely a recommended workflow.

When you receive a pull request from a fork (especially in OSS projects where fork-PRs are unsigned and untrusted), running unit tests, type-checks, lint, etc. against that PR's code requires letting that code execute on your infrastructure. This document patterns for safely reviewing fork code.

This pattern is inspired by the Paperclip CI hardening playbook (community knowledge, MIT-licensed) absorbed during PLAN-068 R1 cross-pollination analysis. Adapted to ceo-orchestration's stdlib + Claude-only constraints.

## When to apply

- PRs from forks (`github.event.pull_request.head.repo.full_name != github.repository`)
- Untrusted contributors (no prior commit history)
- Code that runs scripts, tests, or any executable as part of CI

## When NOT needed

- PRs from branches in your own repo (already trusted via branch-protection)
- Documentation-only PRs that don't touch code
- Trusted-contributor PRs with green CI history

## The Docker-compose review pattern

Run a one-shot Docker compose stack that:

1. Mounts the PR checkout **read-only**
2. Has **no network egress** (or only egress to package registries with allowlist)
3. Captures stdout/stderr to host log file
4. Auto-shuts-down after the test run

### Example `review-checkout-pr.yml`

```yaml
version: "3.8"

services:
  reviewer:
    image: python:3.11-slim
    container_name: pr-review-${PR_NUMBER:-0}
    working_dir: /pr-checkout
    volumes:
      - ${PR_CHECKOUT_PATH}:/pr-checkout:ro       # read-only mount
    environment:
      - HOME=/tmp/home
      - PIP_NO_CACHE_DIR=1
      - PIP_DISABLE_PIP_VERSION_CHECK=1
    user: "65534:65534"                            # nobody:nobody — never root
    networks:
      - reviewer-isolated
    cap_drop:
      - ALL
    security_opt:
      - "no-new-privileges:true"
    tmpfs:
      - /tmp:size=512M,mode=1777,exec
    command:
      - sh
      - -c
      - "cd /tmp && cp -r /pr-checkout/* . && pip install -e . && python -m pytest -q"

networks:
  reviewer-isolated:
    driver: bridge
    internal: true                                # no internet egress
```

### Usage

```bash
PR_CHECKOUT_PATH=/tmp/pr-12345 PR_NUMBER=12345 \
  docker compose -f review-checkout-pr.yml up --abort-on-container-exit
```

The compose file:
- mounts the PR code read-only at `/pr-checkout`
- copies into a tmpfs-backed `/tmp` work-dir (so the install/test can write)
- runs as `nobody` (never root)
- drops all Linux capabilities
- denies all network egress (`internal: true`)

## ⚠️ Required warnings

These are real attack surfaces. Read them before deploying this pattern.

### 1. Container escape via mounted volumes

If you mount the PR code **read-write** (without `:ro`), the test code can modify your host filesystem through the mount. ALWAYS use `:ro`.

If you mount paths above the PR checkout (e.g. `~/.ssh`, `/etc`, `~`), the test code can READ those paths even with `:ro`. Mount **only** the PR checkout, never parent directories.

If your Docker daemon socket is mounted (`/var/run/docker.sock`), the test code can spawn arbitrary containers including privileged ones. NEVER mount the daemon socket in a fork-review container.

### 2. Network egress from the review container

By default, Docker containers can reach the internet. A fork-PR could exfiltrate its repo URL, your hostname, your IP, or your filesystem contents to an attacker-controlled endpoint.

The `networks: reviewer-isolated: internal: true` declaration above blocks all egress. Verify this with `docker exec <container> curl -m 5 https://example.com` — should fail with `Couldn't resolve host`.

If you need package-registry access (pip, npm), use a **separate egress-allowed** network with explicit registry allowlist via DNS pinning, not unrestricted egress.

### 3. Secret leakage through env passthrough

By default, Docker compose passes `${VAR}` env from your shell into the container. If your shell has `AWS_*`, `GITHUB_TOKEN`, `OPENAI_API_KEY`, `ANTHROPIC_API_KEY`, etc., those leak.

The example above uses an explicit `environment:` block with a small whitelist. Do NOT use `env_file:` pointing at your `~/.env`. Audit the env passed in CI explicitly.

### 4. File-watcher / inotify race against fast PR-rebase

If your reviewer uses a file-watcher (entr, watchmedo) and the PR author force-pushes during review, the watcher may pick up an inconsistent half-pulled tree. Always `git checkout --detach <FULL_SHA>` (not branch name), and snapshot the SHA at review-start. Verify SHA at review-end matches start. If they differ, abort and re-run.

## Disclaimer

This document is **opt-in adopter pattern**. Not enforced by `validate-governance.sh`. Not part of the framework's governance gate. Adopters apply this at their own discretion based on their threat model.

The framework itself does NOT review fork PRs (vibecoder-only thesis per ADR-096). This doc exists for adopters who run public OSS projects and want a pattern; it does not bind the framework's own CI.

## Related

- ADR-051 (skill-reference threat model)
- ADR-084 (Claude-only refusal — closes multi-adapter expansion)
- ADR-096 (vibecoder-only by design)
- `feedback_custom_mcp_tools_governance_gap.md` (S81-tris) — analogous pattern: never trust untrusted MCP servers without sandbox

## Changelog

- 2026-05-04 — initial draft (PLAN-065 §4.4.C)
