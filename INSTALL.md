# Install

<!-- last-reviewed: 2026-07-02 v1.0.1 -->

> ⚠ **Maintained personal-use framework — bus-factor 1, no roadmap commitments; the public repo is a stable snapshot, not an actively-staffed product.** Reactive maintenance only, no new feature work; the install modes below are personal-use only, with no external-adopter SLA or support channel. Formal verdict: `MAINTENANCE-MODE-VIBECODER` per [ADR-096](.claude/adr/ADR-096-vibecoder-only-by-design.md) — read it before adopting.

> 3 ways to consume `ceo-orchestration` from another repo. Pick the one that
> matches your team's workflow.

> ## Official sources only
>
> The only official distribution points for this framework are:
>
> - **GitHub:** [`Canhada-Labs/ceo-orchestration`](https://github.com/Canhada-Labs/ceo-orchestration)
> - **npm:** [`ceo-orchestration`](https://www.npmjs.com/package/ceo-orchestration) (`npx ceo-orchestration`)
>
> Anything else — mirrors, forks, re-published packages, marketplace
> listings, lookalike names — is unofficial and untrusted. GitHub
> releases ship SHA-256 checksums; the npm package is published with
> SLSA 3 provenance. Verify before installing.

> ## ⚠ Pre-install: read these first
>
> 1. [`docs/HONEST-LIMITATIONS.md`](docs/HONEST-LIMITATIONS.md) —
>    structural limitations (bus factor 1, same-LLM problem, soak
>    windows in progress, mid-pivot reframing). Verdict
>    `MAINTENANCE-MODE-VIBECODER` per [ADR-096](.claude/adr/ADR-096-vibecoder-only-by-design.md) (terminal stability mode; no future feature work; bus factor 1; vibecoder / individual use is fine, external adopters out-of-scope). See
>    [`docs/READINESS-STATUS.md`](docs/READINESS-STATUS.md) for the
>    verdict ladder.
> 2. [`README.md#risks-and-what-this-is-not`](README.md#risks-and-what-this-is-not)
>    — condensed risk list (bus factor, same-vendor reviewer, audit
>    detection-not-prevention, scoped formal verification).
> 3. Cost expectation block below — at default settings, most sub-agent
>    spawns inherit the pricier CEO model, so a session can cost ~16%
>    more than the per-role rates in `docs/cost-of-operation.md` (internal
>    ref: audit-v2 C3-P0-03; the ~16% figure is at Opus 4.8 — it was ~50%
>    at the older Opus-4.7 rates this note used to assume).
> 4. [`docs/STATE-RECOVERY.md`](docs/STATE-RECOVERY.md) — resume-from-state
>    patterns (audit log replay, plan state, memory continuity).
> 5. [`docs/OBSERVABILITY.md`](docs/OBSERVABILITY.md) — canonical
>    audit-log.jsonl structure + query patterns.
> 6. [`docs/GOVERNANCE.md`](docs/GOVERNANCE.md) — 35+ kill-switches
>    enumerated + 4 frozen invariants. Bookmark for adopter-side
>    debugging.

> ## ⚠ Pre-install: cost expectation disclosure (audit-v2 C3-P0-03)
>
> At default settings (v1.11.0), 4 of 5 canonical sub-agent archetypes
> (`qa-architect`, `performance-engineer`, `security-engineer`,
> `devops`) route via **mitigated dispatch** through `general-purpose`
> per ADR-082. The `general-purpose` sub-agent **inherits the CEO model
> (Opus 4.8 by default at $5/$25 per Mtok)** — NOT the Sonnet/Haiku
> rates that ADR-052 §Role-to-model would suggest for these roles.
>
> Only `code-reviewer` runs at Opus by *policy* (ADR-052 VETO floor);
> the other 4 inherit Opus by *default-CEO* not by *role-policy*.
>
> Practical impact: the mitigated rail makes ~75% of the spawn
> fan-out inherit the pricier CEO model (Opus 4.8, $5/$25 per Mtok),
> so sessions typically cost more than the ADR-052 per-role table
> suggests. See `docs/cost-of-operation.md` §Mitigated dispatch for
> the full breakdown, historical examples, and `CEO_MITIGATION_DISABLE=1`
> override. Use `ceo-cost.py` to measure your actual spend.
>
> **Override** (force ALL archetypes through the native rail — reverts
> cost to the ADR-052 per-role numbers, at the cost of re-exposing the
> rail anomaly that mitigated dispatch works around; internal ref: H4):
>
> ```bash
> export CEO_MITIGATION_DISABLE=1
> ```

---

## Pick one install path — they do not stack

Three routes can put the framework in front of Claude Code for a target
repo, and they are **mutually exclusive per target**. The two supported
routes (script and npx) write the same surfaces: `.claude/hooks/`,
`.claude/skills/`, `.claude/settings.json` (hook registrations), and the
install manifest at `.claude/.install-manifest.sha256`. The experimental
plugin route is different: `scripts/build-plugin.py` produces a bundle
with its **own** `hooks/hooks.json` under the plugin root — it does
**not** write the target repo's `settings.json` or install manifest, so
the manifest-based uninstall/recovery guidance below applies only to
script/npx installs (a plugin is removed through Claude Code's plugin
manager). The conflict is real either way: a plugin stacked on a script
install means two registrations firing the same hook scripts.

| Path | What it is | Status |
|---|---|---|
| `scripts/install.sh <target>` from a clone (Option 1) or submodule `--link` mode (Option 2) | The reference installer — Options 1 and 2 below are the **same script**, so they count as one path | Supported |
| `npx ceo-orchestration <target>` | npm shim that spawns the *same bundled* `install.sh` and forwards your flags unchanged | Supported |
| Claude Code plugin (`scripts/build-plugin.py`) | Experimental packager of the advisory (`--ceremony user`) surface — see the note under Option 3 | Experimental — not a supported install path |

(Option 3, the GitHub template, creates a brand-new repo rather than
installing into an existing one, so it does not enter this conflict.)

**The stacked-failure mode.** Installing via more than one path on the
same repo produces:

- **Duplicated hooks** — the same hook fires once from
  `.claude/settings.json` and once from the plugin's own hook
  registration, so every governed action pays the hook chain twice.
- **Stacked settings merges** — two installers merging hook entries
  into `.claude/settings.json` on top of each other.
- **A drifted install manifest** — `.claude/.install-manifest.sha256`
  records only the **last** writer. Files from the earlier install no
  longer match the manifest, so the manifest-honoring `uninstall.sh`
  preserves them as "user-modified" and leaves orphans behind.

**Reset order to recover from a mixed install:**

1. **Uninstall via the path you installed with.** Script or npx
   installs: `scripts/uninstall.sh <target> --dry-run` first, then for
   real (see §Uninstall below). The npm shim only exposes the
   installer, so run `uninstall.sh` from a clone — it honours the same
   manifest the bundled installer wrote. Plugin installs: remove the
   plugin through Claude Code's plugin manager.
2. **Verify `.claude/` is clean.** No `team.md`, `hooks/`, `skills/`,
   or `.install-manifest.sha256` left behind. By design the uninstaller
   preserves files whose SHA no longer matches the manifest (your
   post-install edits), so inspect leftovers and remove them by hand —
   the manual `rm -rf` fallback in §Uninstall is the checklist.
3. **Reinstall via exactly ONE path.** Stay on that path for upgrades
   too (`scripts/upgrade.sh` assumes an install.sh-shaped manifest).

---

## Option 1 — Bash script (recommended for most cases)

Works for **any existing repo**, copies files in place. Easy to explain. No
dependencies (except `jq` if you pass `--stack`). The trade-off: no automatic
updates — you re-run the script when you want to pull a newer version.

```bash
# 1. Clone this repo once, anywhere on your machine
git clone https://github.com/Canhada-Labs/ceo-orchestration.git ~/ceo-orchestration

# 2. Run install in your target repo
cd /path/to/your/project

# Minimal: core + frontend, base hooks only (no stack-specific pre-commit gate)
~/ceo-orchestration/scripts/install.sh .

# With Node.js/TypeScript stack (adds tsc + vitest pre-commit gate)
~/ceo-orchestration/scripts/install.sh . --stack node

# With fintech domain profile (adds 12 fintech skills + 29-persona reference team)
~/ceo-orchestration/scripts/install.sh . --profile core,frontend,fintech --stack node

# Core only (no frontend skills — for backend-only projects)
~/ceo-orchestration/scripts/install.sh . --profile core --stack node
```

### Flags

| Flag | Values | Default | What it does |
|------|--------|---------|--------------|
| `--link` | — | (off) | Use symlinks instead of copies (for submodule mode) |
| `--profile` | `core,frontend,<domain>` | `core,frontend` | Comma-separated list of profiles to install |
| `--stack` | `node`, `none` | `none` | Stack-specific hooks to merge into settings.json |

### What the script installs

Always (regardless of profile):
- `.claude/team.md`, `.claude/frontend-team.md` — archetype templates
- `.claude/hooks/check_agent_spawn.py` — the mechanical spawn enforcement (Python)
- `.claude/hooks/audit_log.py` — silent PostToolUse audit observer
- `.claude/hooks/_python-hook.sh` — Python 3.9+ version resolver shim
- `.claude/hooks/_lib/` — 67 shared modules, excluding the package `__init__.py` (payload, redact, filelock, team, testing, test_isolation, audit_emit, audit_hmac, policy, tool_lifecycle, codex_cli_shape, …)
- `.claude/scripts/` — validate-governance, inject-agent-context,
  check-skill-health, check-pitfall-regression (universal)
- `.claude/commands/audit-page.md` — generic page audit
- `.claude/pitfalls-catalog.yaml` — universal pitfalls (IPC, SEC, ARCH, DB, FE, LLM)
- `.claude/task-chains.yaml` — 7 universal workflows
- `.claude/agent-metrics.md` — strike tracking
- `.claude/settings.json` — built from `templates/settings/settings.base.json`
  (+ `settings.stack.<name>.json` if `--stack` is set, merged via `jq`)
- `templates/CLAUDE.md` → `CLAUDE.md` (only if missing — never overwrites)
- `templates/MEMORY.md` → `MEMORY.md` (only if missing — deprecation
  stub; live auto-memory now lives at `~/.claude/projects/<slug>/memory/`
  per Claude Code native convention)

If `--profile core`: adds `.claude/skills/core/` (42 universal skills)
If `--profile frontend` (default): adds `.claude/skills/frontend/` (8 frontend skills)
If `--profile <domain>` where domain ∈ one of the 29 supported profiles:
`academic-humanities`, `business-support`, `civil-engineering`, `community`,
`devrel`, `edtech`, `embedded`, `finance-accounting`, `fintech`, `government`,
`healthcare`, `hospitality`, `hr`, `i18n-business`, `identity-systems`, `legal`,
`lgpd-heavy-saas`, `marketing-global`, `mobile`, `paid-media`, `project-management`,
`real-estate-finance`, `retail`, `saas-platforms`, `sales`, `supply-chain`,
`trading-hft`, `training-l-and-d`, `voice-ai`. Adds
`.claude/skills/domains/<domain>/` with its skills (and, for legacy domains
fintech / trading-hft / edtech / government / community,
the full squad bundle: pitfalls, task-chains, team-personas, commands, scripts).
Note: `lgpd-heavy-saas` is a legacy domain stub — the 3 LGPD skills
(consent-lifecycle, dpo-reporting, pii-data-flow) are now in `core/` and
are included with the default `--profile core` install.
The 22 newer domains added in v1.15.0 ship as **seed skills only** — full
squad-bundle scaffolding is tracked in PLAN-080 (post-v1.15.0).

### Updating later

```bash
cd ~/ceo-orchestration && git pull
cd /path/to/your/project
~/ceo-orchestration/scripts/upgrade.sh . --profile core,frontend,fintech --stack node
```

`upgrade.sh` preserves local edits to `CLAUDE.md`, `MEMORY.md`,
`.claude/settings.json`, and `.claude/agent-metrics.md`. It overwrites the rest
after backing up to `.claude.bak/{timestamp}/`.

---

## Option 2 — Git submodule (recommended for monorepos)

Best when you want **automatic version tracking** and the ability to lock the
team to a specific commit. Some less-technical teammates find submodules
confusing — pick this only if your team is comfortable with `git submodule update`.

```bash
cd /path/to/your/project

# Add as submodule
git submodule add https://github.com/Canhada-Labs/ceo-orchestration.git .ceo-shared

# Run install with --link flag (same profile/stack flags as Option 1)
.ceo-shared/scripts/install.sh . --link --stack node

# Or with a domain profile
.ceo-shared/scripts/install.sh . --link --profile core,frontend,fintech --stack node
```

With `--link`, the script creates **symlinks** instead of copies for the
protocol files (skills, team rosters, hooks, scripts, commands, catalogs).
That way `git submodule update` brings in new skills and hook updates
automatically.

`CLAUDE.md`, `MEMORY.md` are still **copied** (they're project-specific).
`.claude/settings.json` is also symlinked — you can override hooks per-project
by creating `.claude/settings.local.json`.

To update:
```bash
cd /path/to/your/project
git submodule update --remote .ceo-shared
git add .ceo-shared && git commit -m "bump ceo-orchestration"
```

---

## Option 3 — GitHub template repository

Best for **brand-new projects only**. Won't help you adopt the protocol in an
existing repo.

1. Go to the ceo-orchestration repo on GitHub.
2. Click **"Use this template"** → **"Create a new repository"**.
3. Name your new repo, set it private/public, click create.
4. Clone your new repo. It already has `.claude/`, `templates/`, `scripts/`,
   `README.md`, `PROTOCOL.md`, etc.
5. Edit `templates/CLAUDE.md` → move to project root as `CLAUDE.md`. Fill in
   the placeholders.

The template approach gives you a fork — you can edit anything, including
`team.md` and the skills, without affecting the upstream `ceo-orchestration`.
But you also won't get upstream updates automatically.

> **Note — Claude Code plugin build.** A plugin packager
> (`scripts/build-plugin.py`) also exists, but it is **experimental /
> internal** — its deliberately thin surface is intentional, and it is
> not a supported install path. Prefer Option 1 (Bash script) above.

---

## What gets installed

```
your-project/
├── .claude/
│   ├── team.md                          # archetype template — add your personas
│   ├── frontend-team.md                 # frontend archetype template
│   ├── settings.json                    # built from settings.base.json (+ optional stack.<name>.json)
│   ├── skills/
│   │   ├── core/                        # 42 universal skills
│   │   ├── frontend/                    # 8 frontend skills (if 'frontend' in profile)
│   │   └── domains/<domain>/            # only if a domain profile was installed
│   │       ├── skills/                  # domain-specific skills
│   │       ├── team-personas.md         # reference personas (e.g. 29-persona fintech team)
│   │       ├── pitfalls.yaml            # domain pitfalls
│   │       ├── task-chains.yaml         # domain workflows
│   │       ├── commands/                # domain slash commands
│   │       └── scripts/                 # domain check scripts
│   ├── hooks/
│   │   ├── _lib/                        # 67 shared Python modules, excl. __init__.py (audit_emit, audit_hmac, policy, redact, tool_lifecycle, …)
│   │   ├── _python-hook.sh              # Python version resolver + invoker
│   │   ├── check_agent_spawn.py         # mechanical enforcement of spawn protocol
│   │   ├── audit_log.py                 # silent PostToolUse audit observer
│   │   ├── ... (53 hooks total — see .claude/hooks/*.py)
│   │   └── tests/                       # 11000+ unit tests via `make test-collect`
│   ├── scripts/
│   │   ├── validate-governance.sh
│   │   ├── inject-agent-context.sh
│   │   ├── check-skill-health.sh
│   │   └── check-pitfall-regression.sh  # universal pitfalls only
│   ├── commands/
│   │   └── audit-page.md                # generic page audit
│   ├── pitfalls-catalog.yaml            # universal pitfalls (IPC, SEC, ARCH, DB, FE, LLM)
│   ├── task-chains.yaml                 # 7 universal workflows
│   └── agent-metrics.md                 # strike tracking
├── CLAUDE.md                            # session protocol — edit per project
├── MEMORY.md                            # deprecation stub — real memory at ~/.claude/projects/<slug>/memory/
└── PROTOCOL.md (pointer)                # link to the upstream PROTOCOL.md
```

---

## Placeholders you must fill

After install, search the installed files for these and replace them:

| Placeholder | Where | Example value |
|-------------|-------|---------------|
| `{{OWNER_NAME}}` | `team.md`, `frontend-team.md`, `CLAUDE.md`, `ORG_CHART.md` | `Jane Doe` |
| `{{PROJECT_NAME}}` | `CLAUDE.md` | `My Awesome Service` |
| `{{PROJECT_PATH}}` | `CLAUDE.md` | `/Users/me/my-project` |
| `{{STACK}}` | `CLAUDE.md` | `Node.js 20 + tsx + Hono v4` |
| `{{DEPLOY_TARGET}}` | `CLAUDE.md` | `Fly.io / Vercel / Railway / etc.` |
| `{{FRONTEND_REPO_PATH}}` | `frontend-team.md` | `/Users/me/my-frontend` |

---

## Verify install

After install, start a Claude Code session and ask:

> "Ative o protocolo CEO e carregue o time."
>
> _("Activate the CEO protocol and load the team.")_

Claude should:
1. Invoke the `ceo-orchestration` skill from `.claude/skills/core/ceo-orchestration/SKILL.md`
2. Read `.claude/team.md` and `.claude/frontend-team.md`
3. Confirm the team roster is loaded (archetype or installed domain personas)
4. Show the 151-skill inventory (42 core + 8 frontend + 101 domain across 29 profiles)
5. Be ready to spawn named agents on request

Then test the hook is wired up. Ask Claude:

> "Spawn an agent with the name of any persona in your team.md, with a generic task and no skill content."

The hook should **block** the spawn with a governance error:
`GOVERNANCE: Agent spawn detected as NAMED ..., but prompt has no
## SKILL CONTENT section.`

If the spawn goes through without being blocked, the hook is not wired up —
check `.claude/settings.json` and make sure `check_agent_spawn.py` is
executable and Python >= 3.9 is on PATH. You can also run
`bash .claude/scripts/validate-governance.sh`
which verifies all pieces are in place.

If any step fails, the install is incomplete. Open an issue.

A scriptable equivalent for CI / one-shot validation:

```bash
bash .claude/scripts/validate-governance.sh
```

The script exits non-zero on any structural violation (missing skill,
broken pointer, hook not wired). Run it as part of your post-install
smoke gate.

---

## SPEC v1 schemas

The framework ships its own published compliance contract at
`SPEC/v1/` (~32 `.md` schema files at v1.18.0). These schemas define
the canonical shapes the framework guarantees stable across minor
versions:

- **`SPEC/v1/install-cli.md`** — `install.sh` flag contract, exit
  codes, `--verify` and `--strict-placeholders` semantics, deprecation
  policy (e.g. `--verify-sigstore` deprecated 1.11.4, removed 2.0.0).
- **`SPEC/v1/audit-log.schema.md`** — `audit-log.jsonl` schema, action
  vocabulary, HMAC chain contract, rotation semantics.
- **`SPEC/v1/plan.schema.md`** — `PLAN-NNN-*.md` frontmatter
  shape (the `status:` / `target_tag:` / `milestone:` etc. table that
  governs lifecycle).
- **`SPEC/v1/hook-io.schema.md`** — hook I/O contract (stdin payload,
  block/allow decision schema, fail-open rule, env-var contract).
- Plus per-subsystem schemas: ADR template, debate fixture format,
  red-team-corpus, secret-patterns-exchange, etc.

After install, `ls TARGET/SPEC/v1/*.md` should list all schemas.
The schemas are **read-only contracts** — adopters that need to
customize behavior do so via `settings.json` env-var overrides
(documented in `docs/GOVERNANCE.md`), never by editing the schema
files. A version bump in `VERSION` carries the SemVer guarantee
that minor/patch changes do NOT break the schemas; major bumps
publish a new `SPEC/v2/` alongside.

To verify what version you installed:

```bash
cat TARGET/VERSION
# Example output: 1.18.0
```

The `VERSION` file matches the git tag of the source framework
checkout at install time. Use it as a forensic anchor when an
adopter reports a bug: ask for the `VERSION` value first.

---

## Upgrade flow

To refresh framework-derived content in an existing adopter install
(without touching user-customized files), use `scripts/upgrade.sh`:

```bash
cd /path/to/ceo-orchestration   # source framework checkout
git pull                         # get the latest framework
bash scripts/upgrade.sh /path/to/your/project --pin v1.0.1
```

What gets refreshed:

- `.claude/team.md`, `.claude/frontend-team.md`
- `.claude/skills/`, `.claude/hooks/`, `.claude/scripts/`,
  `.claude/commands/`
- `.claude/pitfalls-catalog.yaml`, `.claude/task-chains.yaml`
- `PROTOCOL.md` pointer

What is **NOT** touched (user data):

- `CLAUDE.md`, `MEMORY.md`
- `.claude/settings.json`, `.claude/agent-metrics.md`

Run `bash scripts/upgrade.sh --help` for the full flag list. Key
flags:

- `--pin <tag>` — pin source to a specific tag/SHA (refuses if
  target has uncommitted `.claude/` changes; the pin is the audit
  anchor for what was actually installed).
- `--dry-run` — preview what WOULD be replaced.
- `--skip <glob>` — exclude files from the overwrite (repeatable).
  Use this to protect adopter customizations to specific framework
  scripts (e.g. `--skip='.claude/scripts/local/*'`).
- `--no-diff-warn` — silence the F-CHAOS-3 "customization will be
  replaced" warnings (default: warnings ON).

A backup is automatically copied to `TARGET/.claude.bak/{timestamp}/`
before any file is overwritten. If the upgrade aborts on error, the
backup is preserved for forensic recovery.

---

## Post-install: configure env vars (optional but recommended)

The framework ships with safe defaults — most adopters can run as-is.
But for production-like installs you should configure 2 categories:

**1. Budget controls** (prevents runaway autonomous-session cost):

```bash
export CEO_BUDGET_ENFORCE=1
export CEO_BUDGET_PER_SPAWN=0.25            # USD per single sub-agent spawn
export CEO_BUDGET_BYPASS_MAX_PER_DAY=1      # tighten to 1 in production
```

**2. State path** (only if you want state outside `~/.claude/projects/<slug>/`):

```bash
export CEO_PROJECT_STATE_DIR=/srv/ceo-state/$USER
```

For the **complete catalog (~55+ env-vars)** organized in 6 categories
(Hook kill-switches, Behavioral kill-switches, Diagnostic, Activation
opt-ins, Budget/Cost, Path/Storage):

- [`docs/GOVERNANCE.md`](docs/GOVERNANCE.md) §"What CAN be turned off"
  is the canonical reference.
- [`docs/DAY-1-CHECKLIST.md`](docs/DAY-1-CHECKLIST.md) §Step 11
  has the day-1 emergency-only top-7 picks.
- [`docs/CHEAT-SHEET.md`](docs/CHEAT-SHEET.md) is the single-page
  cheat-sheet for daily use.

**Frozen invariants** that env-vars CANNOT bypass: VETO floor model
assignment (ADR-052), canonical-edit sentinel discipline (ADR-031),
kernel-override audit emit (ADR-031 §kernel-override), and Claude-only
positioning (ADR-085). These are auditable security floors —
no env-var overrides them.

---

## Uninstall

The recommended approach uses the manifest-aware uninstall script:

```bash
cd /path/to/your/project
# Dry-run first to see what will be removed
~/ceo-orchestration/scripts/uninstall.sh . --dry-run

# Actual uninstall (removes only framework-installed files; keeps CLAUDE.md, settings.json)
~/ceo-orchestration/scripts/uninstall.sh .
```

`uninstall.sh` honours the install manifest and supports `--restore` and
`--force` flags. For manual removal as a fallback:

```bash
cd /path/to/your/project
rm -rf .claude/team.md .claude/frontend-team.md .claude/skills \
       .claude/hooks .claude/scripts .claude/commands \
       .claude/pitfalls-catalog.yaml .claude/task-chains.yaml .claude/agent-metrics.md
# Keep CLAUDE.md, MEMORY.md, .claude/settings.json — those are yours.
```

If you used the submodule mode:
```bash
git submodule deinit .ceo-shared
git rm .ceo-shared
rm -rf .git/modules/.ceo-shared
```

---

## MCP server

The framework ships an MCP server at `.claude/scripts/mcp-server/server.py`.
Use the provided launcher script — it resolves a compatible Python interpreter
(≥3.9) and forwards arguments to the server:

```bash
# Default: HTTP transport on 127.0.0.1:9000
.claude/scripts/mcp-server/start-mcp-server.sh

# stdio transport (for IDE integrations)
CEO_MCP_TRANSPORT=stdio .claude/scripts/mcp-server/start-mcp-server.sh

# Disable via kill-switch (exits 0)
CEO_SOTA_DISABLE=1 .claude/scripts/mcp-server/start-mcp-server.sh
```

**Key environment variables** (full list in `server.py` module docstring):

| Variable | Default | Effect |
|---|---|---|
| `CEO_MCP_TRANSPORT` | `http` | `http` or `stdio` |
| `CEO_MCP_HOST` | `127.0.0.1` | Bind address (loopback only by default) |
| `CEO_MCP_PORT` | `9000` | TCP port (HTTP transport only) |
| `CEO_MCP_ALLOW_PUBLIC` | unset | Set to `1` to allow non-loopback bind |
| `CEO_SOTA_DISABLE` | unset | Set to `1` to disable the server (exits 0) |
| `CLAUDE_PROJECT_DIR` | cwd | Project root the server will reference |

**Host-specific service definitions** (systemd unit, launchd plist) are
intentionally NOT shipped in the framework — they belong in host provisioning,
not in a portable library. See
`.claude/scripts/mcp-server/start-mcp-server.sh` for rationale.

The server's HMAC client secrets live at
`$CEO_PROJECT_STATE_DIR/mcp_client_secrets/<client_id>.key` (directory
created by `scripts/install.sh` step P2-SEC-H; permissions `0700`).

---

## Troubleshooting

### MCP servers — Codex pair-rail (`--mcp-debug`)

The Codex pair-rail registers as a **project-scope MCP server** via a
`.mcp.json` file at the target repo root. The framework ships the
template at `templates/.mcp.json` (server name `codex`, official
`codex mcp-server` stdio invocation, credentials via `${ENV}` expansion
only — never a literal key). The install step is idempotent
EXISTS→SKIP: an adopter's own `.mcp.json` is never overwritten; if the
file is missing, copy the template to `<target>/.mcp.json` manually.

If the `mcp__codex__codex` / `mcp__codex__codex-reply` tools are absent
from a session, the pair-rail hooks **fail OPEN (silently)** — diagnose
instead of assuming the rail is active:

```bash
# 1. Is the server registered + healthy? (run from the target repo root)
claude mcp list

# 2. Launch with MCP debug output to see connection/handshake errors
claude --mcp-debug
# NOTE: --mcp-debug is a DEPRECATED alias on current CLI versions —
# prefer:  claude --debug   (optionally filtered: claude --debug mcp)

# 3. Codex CLI present and in the pinned range?
command -v codex && codex --version
# install: npm install -g @openai/codex
# pin range: .claude/governance/codex-cli-pin.txt

# 4. Credentials: set OPENAI_API_KEY in the LAUNCHING shell —
#    .mcp.json forwards it via ${ENV} expansion, never a literal
echo "${OPENAI_API_KEY:+set}"
```

Common failure modes:

| Symptom | Likely cause | Fix |
|---|---|---|
| `codex` missing from `claude mcp list` | no `.mcp.json` at repo root | copy `templates/.mcp.json` to `<target>/.mcp.json` |
| server listed, tools absent in-session | project-scope server not approved | approve when prompted, or `claude mcp reset-project-choices` and restart |
| handshake/timeout errors under `--mcp-debug` | slow server start | raise `MCP_TIMEOUT` (ms) in the launching env |
| pair-rail silent (no Codex review on L3+ edits) | any of the above — the rail fails OPEN when Codex is unavailable | run the pre-flight: `.claude/scripts/local/pair-rail-gate.sh` |

---

## Advanced: Sandbox and project-clone isolation

The framework uses two isolation patterns during plan ceremonies:

### CEO_SANDBOX_DIR

When set, `CEO_SANDBOX_DIR` overrides the default project state directory
(`~/.claude/projects/<slug>/`) for audit logs, audit-key, and sidecar state.
Use this to run ceremony scripts in a temporary directory without contaminating
production state:

```bash
export CEO_SANDBOX_DIR=/tmp/ceo-sandbox-$(date +%s)
mkdir -p "$CEO_SANDBOX_DIR"
bash scripts/install.sh /path/to/target-project
```

### Project-clone isolation

Plan ceremonies that run automated code changes create a `project-clone/`
subdirectory under the plan's `sandbox/` directory. This is a full copy of
the repo tree. Changes are applied inside the clone; only verified changes
are promoted back to the real repo. The clone is ephemeral and should be
deleted after the ceremony.

```bash
# Example: inspect a ceremony clone
ls .claude/plans/PLAN-NNN/sandbox/wave-0/project-clone/
```
