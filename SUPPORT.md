# Support Matrix

<!-- last-reviewed: 2026-06-06 v1.0.0 -->

> **Honest framing.** This is a one-Owner framework with no paid
> support tier. The matrix below is what we **dogfood** — what runs
> green in CI on every commit, what the Owner uses daily, what
> adopters can expect to actually work.

## Runtime — what we test

### Python (hooks + scripts)

`.claude/hooks/_python-hook.sh` resolves the newest available Python
≥ 3.9 in this order:

```
python3.13 → python3.12 → python3.11 → python3.10 → python3.9 → python3
```

| Version | Status | Tested in CI |
|---------|--------|--------------|
| Python 3.13 | ✅ Supported | `validate.yml` matrix |
| Python 3.12 | ✅ Supported | `validate.yml` matrix |
| Python 3.11 | ✅ Supported | `validate.yml` matrix |
| Python 3.10 | ✅ Supported | `validate.yml` matrix |
| Python 3.9 | ✅ Supported (floor) | `validate.yml` matrix |
| Python 3.8 | ❌ Not supported | EOL upstream; no PEP 604, no `match` |
| Python ≤ 3.7 | ❌ Not supported | EOL upstream |

Coding constraints in framework code:

- `from __future__ import annotations` at the top of every module
- `typing.Optional`, `typing.Union` instead of runtime PEP 604 syntax
- No `match` statements (3.10+ feature)
- Stdlib only (no third-party runtime dependencies — see
  [`SBOM.md`](SBOM.md))

Adopters who run Python 3.10+ in their own application code are
unaffected by these constraints — they apply to framework internals
only.

### Bash (install + scripts)

| Shell | Status | Notes |
|-------|--------|-------|
| Bash 5.x | ✅ Supported | macOS via Homebrew, all modern Linux |
| Bash 4.x | ✅ Supported | Default on older RHEL / CentOS |
| Bash 3.2 | ⚠️ Best-effort | macOS system default (`/bin/bash`); install scripts use `#!/bin/bash` and have been seen to work, but not CI-tested |
| Zsh | ✅ Interactive | The Owner's daily driver; framework scripts shebang `#!/bin/bash` so zsh-as-login-shell is fine |
| Fish | ⚠️ Best-effort | Scripts call `bash`; interactive aliases not provided |

## Operating systems

| OS | Status | Notes |
|----|--------|-------|
| macOS 14 (Sonoma) | ✅ Supported | Owner daily driver |
| macOS 13 (Ventura) | ✅ Supported | Should work; not regularly tested |
| macOS 12 (Monterey) | ⚠️ Best-effort | EOL by Apple; Python 3.9 floor still met |
| Ubuntu 24.04 LTS | ✅ Supported | CI default for newest matrix entry |
| Ubuntu 22.04 LTS | ✅ Supported | Primary CI target (`ubuntu-latest` GitHub Actions) |
| Ubuntu 20.04 LTS | ⚠️ Best-effort | Python 3.9 available; bash 5; should work |
| Debian 12 | ✅ Supported (transitive) | Same kernel + glibc family as Ubuntu 22.04 |
| Fedora 39+ | ⚠️ Best-effort | RPM-based; `_python-hook.sh` shim works, install paths assume HOME-relative |
| Arch / Manjaro | ⚠️ Best-effort | Rolling Python; framework code is conservative enough to work |
| Alpine Linux | ⚠️ Best-effort | musl libc; stdlib-only Python is fine; install assumes coreutils |
| Windows native | ❌ Not supported | Use WSL2 (Ubuntu 22.04 inside) |
| Windows + WSL2 | ✅ Supported | Treated as Ubuntu 22.04 |
| FreeBSD / OpenBSD | ❌ Not tested | Stdlib should port; install scripts assume GNU coreutils |

## Claude

### Claude Code CLI

| Version | Status |
|---------|--------|
| Claude Code ≥ 2.0 | ✅ Required — needs `Task` tool, slash commands, hooks, native subagents |
| Claude Code 1.x | ❌ Not supported — missing native subagent dispatch + hook events used by `policy_dispatch.py` |
| Claude Code Web (claude.ai/code) | ⚠️ Partial — slash commands work, hooks do not (no local FS) |

### Claude models

Per ADR-052 multi-model dispatch:

| Model | Used by | Status |
|-------|---------|--------|
| Opus 4.8 (`claude-opus-4-8`) | CEO orchestrator + code-reviewer + security-engineer | ✅ Required |
| Opus 4.8 1M context (`claude-opus-4-8[1m]`) | CEO orchestrator (long sessions) | ✅ Supported |
| Sonnet 4.6 (`claude-sonnet-4-6`) | qa-architect + performance-engineer | ✅ Required (all-Opus override: set the agent's `model:` field to `claude-opus-4-8` manually) |
| Haiku 4.5 (`claude-haiku-4-5-20251001`) | devops | ✅ Required (or override) |
| Opus 4.8 / "Fast mode" | CEO orchestrator (faster output, 2× cost / 2.5× speed) | ✅ Supported via the native Claude Code `/fast` toggle |
| Older Claude 4.x (Opus 4.0–4.5, Sonnet 4.0–4.5, Haiku 4.0–4.4) | Fallback if newer unavailable | ⚠️ Works but not optimized |
| Claude 3.x or earlier | Anything | ❌ Not supported — context window too small for gate-1 boot (~44,786 tokens) |

To downgrade gracefully when a model ID becomes deprecated, see
[`VERSIONING.md`](VERSIONING.md) §Model ID bumps.

### Other LLMs

| LLM | Status | Path |
|-----|--------|------|
| Gemini (Google) | ✅ Supported (shape-probing) | `_lib/adapters/gemini.py` parses Gemini-CLI-style payloads and emits Claude-compatible decisions. Canonical envelope parity with Claude adapter. Live Gemini-CLI fixture capture pending (adopters using Gemini CLI as hook host: capture first PreToolUse payload and open issue if drift is observed). |
| Codex CLI / OpenAI | ❌ Deferred indefinitely | Out of roadmap as of v1.6 |
| Other Anthropic-API-compatible providers | ⚠️ Best-effort | HAL adapter pattern is in place; no production install |

## CI / GitHub

| GitHub Actions runner | Status |
|-----------------------|--------|
| `ubuntu-latest` (24.04) | ✅ Primary |
| `ubuntu-22.04` | ✅ Supported (matrix) |
| `macos-14` (M1) | ✅ Supported (one job; expensive minutes) |
| `macos-13` (Intel) | ⚠️ Not regularly tested |
| `windows-latest` | ❌ Not tested |

All Actions are SHA-pinned per `docs/actions-versions.md` (no
floating tags). See [`SBOM.md`](SBOM.md) for the runtime + Actions
attestation.

## Editors & integrations

| Tool | Status |
|------|--------|
| Claude Code in Terminal | ✅ Primary — full feature set |
| Claude Code in VS Code | ✅ Supported — same hooks + slash commands |
| Claude Code in JetBrains | ✅ Supported (Anthropic IDE plugin) |
| `claude-in-chrome` MCP | ✅ Supported — load tools via `ToolSearch` per the `chrome-mcp` instructions |
| Cursor | ⚠️ Best-effort — see [`docs/mcp-cursor-setup.md`](docs/mcp-cursor-setup.md) |
| Aider, Cline, Continue.dev | ❌ Not adapted — different agent dispatch model |

## Optional dependencies (not required for core)

The framework runtime is **stdlib-only**. Optional dev tools surface
extra features:

| Tool | Used for | Required? |
|------|----------|-----------|
| `pytest` + `pytest-timeout` | Faster test discovery, timeouts | No (unittest discover works) |
| `coverage` | Coverage gate (`coverage.yml`) | CI only |
| `actionlint` | GitHub Actions lint (`validate.yml`) | CI only |
| `tla2tools.jar` 1.8.0 | Formal verification (`formal-verify.yml`) | CI only — SHA-pinned in workflow |
| `git lfs` | Audit-log archive snapshots (optional) | Adopter choice |
| `gpg` | Sentinel signing (canonical-edit) | Owner / maintainer only |

Adopters who run `bash scripts/install.sh .` get a working framework
without installing any of the above. CI installs them transiently.

## Distribution channels

| Channel | Status | Notes |
|---------|--------|-------|
| `git clone` + `bash scripts/install.sh .` | ✅ Primary | Works for any version, any time |
| `git submodule add` + `--link` install | ✅ Supported | Recommended for monorepos |
| GitHub template repo | ✅ Supported | "Use this template" button on the GitHub UI |
| `npm install -g ceo-orchestration` | ✅ Supported (≥ v1.5) | `npm/` package; verifies SHA256 against `npm/SHA256SUMS.txt` |
| Homebrew tap | ❌ Not yet | Considered for v2.0 |

The `npm` package is the easiest path for projects that already have
Node tooling. The bash install path remains the reference and works
for any stack.

## Telemetry / phone-home

**Zero outbound network traffic at runtime.**

The framework does not phone home, send anonymized analytics, ping a
license server, or fetch update metadata unless the adopter
explicitly opts in. Specific opt-in paths:

- `bash .claude/scripts/check-framework-updates.sh` — fetches latest
  tag from `git ls-remote --tags`. HTTPS only. Adopter-invoked.
- `mcp-server` — local-only by default; HTTP transport requires
  explicit `MCP_BIND_HOST` config and only listens on loopback.
- OTEL export — opt-in via `OTEL_EXPORTER_OTLP_ENDPOINT` env var; off
  by default. See `docs/otel-integration.md`.

See [`docs/threat-model.md`](docs/threat-model.md) §I-* (Information
Disclosure) for the full audit.

## Getting help

| Channel | Use for |
|---------|---------|
| GitHub Issues | Bug reports, feature requests, "how do I..." |
| GitHub Discussions | Open-ended questions, adopter experience reports, war stories |
| GitHub Security Advisory | Security defects only (see [`SECURITY.md`](SECURITY.md)) |
| Owner email | Private coordination, adopter onboarding for production install |

There is no Slack, Discord, or chat channel. The Owner reads GitHub
notifications and replies as time permits. Expect responses within
a few business days for non-security issues.

## What "supported" really means

For a row marked ✅:

- The combination is exercised in CI on every commit, **or**
- The Owner uses it daily and would notice a regression, **or**
- An adopter has reported success and the Owner has reproduced

For ⚠️ Best-effort:

- The framework should work; the Owner has not tested it on this
  combination; if you find a defect, please report it via the
  channels above and we will try to fix or document the limitation.

For ❌ Not supported:

- We will not accept bug reports against this combination.
- If a fix is small and obvious we may take it as a courtesy patch,
  but you should not assume we will support the combination going
  forward.

Last reviewed: 2026-05-24 (Session 160 / PLAN-112-FOLLOWUP-canonical-doc-refresh-gate).
