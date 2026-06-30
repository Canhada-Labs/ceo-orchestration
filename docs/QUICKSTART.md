# QUICKSTART — ceo-orchestration in 10 minutes

> **PT-BR:** [QUICKSTART.pt-BR.md](QUICKSTART.pt-BR.md) (mirror).
>
> Guide for anyone who has never used the framework. If you are an
> employee on the project, also read `FOR-EMPLOYEES.md`. If
> something breaks, see `TROUBLESHOOTING.md`.

## What you will have at the end

After following this guide, when you open Claude Code inside your
repository:

- Claude introduces itself as the **CEO** of the project (no longer a
  generic assistant)
- It **plans** before acting — you always know what it is about to do
- It **spawns specialists** (VP of Engineering, Staff Security, etc.)
  with specific playbooks instead of answering "its own way"
- **Mechanical hooks** block common mistakes (destructive commits,
  spawns without a skill, edits to canonical files)
- Everything is **audited** in a log you can query later

## Prerequisites

- `git` installed
- `python3 >= 3.9` (pre-installed on macOS; on Linux: `sudo apt install python3`)
- `bash` or `zsh` (default on Mac/Linux)
- Claude Code CLI installed (https://claude.com/claude-code)

## Step 1 — Install the framework in your project

Open a terminal at the root of your project (the one you want the CEO
to help develop).

### Recommended path — clone at a pinned tag + `install.sh`

This is the canonical path, matching the root `README.md`. Cloning at a
pinned tag gives you integrity for free — `git` verifies pack integrity
on clone — without handling `shasum` by hand:

```bash
cd /tmp
git clone --branch v1.0.0 --depth 1 https://github.com/Canhada-Labs/ceo-orchestration.git
cd /path/to/your/project
bash /tmp/ceo-orchestration/scripts/install.sh
```

### Alternative path — download + SHA256 pin (two steps)

If you prefer not to use `npm`, **never** do `curl … | bash` directly
on a remote URL. The `curl | bash` anti-pattern exposes you to a silent
MITM / repo-tampering: you run whatever shows up, with no integrity
check. Instead, download at a pinned tag + verify the SHA256 published
as a release asset:

```bash
# Set the TAG you want to install (never `main` — it is a moving target):
TAG=v1.0.0

# 1) Download the installer at the pinned tag:
curl -fsSL -o /tmp/ceo-install.sh \
  "https://raw.githubusercontent.com/Canhada-Labs/ceo-orchestration/${TAG}/scripts/install.sh"

# 2) Download the official SHA256 published as a release asset:
curl -fsSL -o /tmp/ceo-install.sh.sha256 \
  "https://github.com/Canhada-Labs/ceo-orchestration/releases/download/${TAG}/install.sh.sha256"

# 3) Verify integrity (the asset's sha256 matches the downloaded script):
( cd /tmp && shasum -a 256 -c ceo-install.sh.sha256 ) \
  || { echo "Integrity verification FAILED — aborting"; exit 1; }

# 4) (PLAN-045 P0-15) Extra verification: the script itself carries a
#     `# CEO-INSTALL-SHA256:` trailer populated at tag-cut. Running it
#     with a tampered file already fail-CLOSED internally with rc=5.
bash /tmp/ceo-install.sh [--target /path/to/your/project]
```

> **Note on the SHA:** the `.github/workflows/release.yml` workflow
> publishes the exact sha256 of `scripts/install.sh` as a release asset
> (`install.sh.sha256`). The command in (2) downloads this asset
> automatically — no need to copy hex by hand from the release notes.
> Always use a pinned tag; `main` is a moving target.

### npm install — available after the first public release

> **Not published yet.** The scoped bootstrap package below ships with
> the first public release; until then, use the recommended clone path
> above.

Once published, the bootstrap installs from npm with automatic
integrity verification (npm registry + SLSA provenance L3):

```bash
npm install -g @ceo-orch/init
cd /path/to/your/project
ceo-orch-init
```

The publishable package is the scoped name `@ceo-orch/init` (the `bin`
it installs is `ceo-orch-init`). It is published with `--provenance`
(SLSA 3) and `npm` verifies the tarball SHA before extracting. See
`docs/install-verification.md` and `.github/workflows/npm-publish.yml`.

The script installs (without touching anything outside `.claude/`,
`docs/`, and `MEMORY.md`):

- `.claude/skills/` — library of 151 skills (specialist playbooks)
- `.claude/hooks/` — 53 Python hooks that block spawns without persona/skill
- `.claude/plans/` — where work plans live
- `.claude/team.md` + `.claude/frontend-team.md` — team roster (backend + frontend)
- `CLAUDE.md` — master context Claude Code reads every session
- `PROTOCOL.md` — rules of engagement

## Step 2 — Customize your project's `CLAUDE.md`

Open `CLAUDE.md` at the root. Find and replace:

- `{{PROJECT_NAME}}` — your project name (e.g., "your-app")
- `{{OWNER_NAME}}` — your name (e.g., "Canhada Labs")
- `{{PROJECT_PATH}}` — absolute path (e.g., `/Users/you/your-app`)

If your project has a specific stack, edit the §CODEBASE SNAPSHOT
section of `.claude/frontend-team.md` (if you have a frontend).

## Step 3 — Open Claude Code

```bash
cd /path/to/your/project
claude
```

On the first interaction, type:

> "Activate the CEO protocol."

Claude will:
1. Read `CLAUDE.md`, `PROTOCOL.md`, and memory
2. Invoke the `ceo-orchestration` skill
3. Read the roster in `.claude/team.md`
4. Respond as CEO of your project

## Step 4 — Your first request

Try something concrete but small. Example:

> "I want to add a 100 req/min rate limit on the /api/users endpoint.
> Draft a plan."

The CEO will:
1. Ask you to confirm the scope
2. Decide which specialists need to weigh in
3. Write a P0-P4 plan (Product lens → Planning → Implementation →
   Quality gate → Deploy)
4. **Not write code yet** — it waits for you to approve the plan

Once approved:
5. Spawns the right specialist (likely Staff Backend Engineer with
   skill `public-api-design`)
6. They implement
7. Code Reviewer reviews
8. You approve → merge

## Step 5 — Query the audit log

The framework logs everything to:
```
~/.claude/projects/<your-project>/audit-log.jsonl
```

Want to see what happened? Run:

```bash
python3 .claude/scripts/audit-query.py summary
```

Useful subcommands:

- `summary` — overview of the last 100 events
- `by-skill` — how many spawns per skill
- `debate` — debate history
- `tokens` — how many tokens were spent
- `health` — is the framework healthy? (PASS / WARN / FAIL)

## What NOT to do

Do **not** ask for "write code X" without a plan. The CEO will refuse
and ask for a plan first. That is intentional.

Do **not** edit `.claude/team.md` or `.claude/skills/core/*/SKILL.md`
without going through the Architect. A hook
(`check_canonical_edit`) blocks edits to these canonical files.

Do **not** run `rm -rf` in the Claude Code terminal. The
`check_bash_safety` hook blocks destructive commands.

Do **not** copy numbers from stale docs without checking the code.
The CEO will call you out (this is an anti-pattern listed in
PROTOCOL.md §Anti-patterns).

## What to do when things go wrong

See `TROUBLESHOOTING.md`. Top 3 common ones:

- **"A hook blocked my command"** — read the reason in the terminal,
  adjust. Example: `rm -rf` → use `mv` to `/tmp/` first.
- **"CEO spawned an agent and it failed"** — one of 3 causes (missing
  skill, missing profile, incomplete context). See TROUBLESHOOTING.
- **"I want to turn everything off"** — `mv .claude .claude.disabled`
  and Claude Code reverts to generic mode.

## Next steps

- Read `PROTOCOL.md` — it is short and explains the 3 gates
- Read `.claude/team.md` — see the archetype roster
- Read `docs/FOR-EMPLOYEES.md` if you are an employee of someone
  who already adopted the framework

## Frequently asked questions

**Q: Do I have to pay for anything?**
A: No. The framework is just files. You pay for regular Claude Code.

**Q: Will it slow things down?**
A: Hook latency < 40ms per invocation. Imperceptible.

**Q: Can I use this with another AI (Gemini, Cursor)?**
A: There is a Gemini stub at `.claude/hooks/_lib/adapters/gemini.py`
but it is not full parity. V1.0 is **Claude Code only**.

**Q: How do I upgrade to a new framework version?**
A: `bash /path/to/ceo-orchestration/scripts/upgrade.sh` — respects
local customizations of `CLAUDE.md` and `settings.json`.
