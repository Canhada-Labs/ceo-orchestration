# Upgrade Procedure

> Step-by-step playbook for adopters bumping their framework version
> (e.g. `v1.10.0` → `v1.11.2`). Designed for predictability —
> no `bash scripts/upgrade.sh && hope`.

## When to upgrade

| Your install | Recommended action |
|--------------|---------------------|
| `vX.Y.Z` (latest current MINOR) | Stay; track PATCH releases |
| `vX.Y-1.Z` (previous MINOR) | Plan upgrade within the **6-month** support window per `SUPPORT.md` |
| `vX.Y-2.Z` or older | Upgrade soon — best-effort support; missing security patches |
| Pre-`v1.0` | Upgrade required; v1 SPEC is the contract horizon |

Run `bash .claude/scripts/check-framework-updates.sh` weekly to
learn about new releases at the moment they ship, not when CI
breaks.

## Pre-upgrade (10 min)

### 1. Read what changed

```bash
# Latest CHANGELOG
cat /path/to/ceo-orchestration/CHANGELOG.md | head -100

# Or via git
git log v<your-current> ..v<target> --oneline -- CHANGELOG.md
```

Look specifically for:

- **Breaking changes** (`### Changed` entries that mention
  removed fields or behavior)
- **New env vars** that change defaults
- **New CI gates** you may need to wire
- **New trust boundaries** (any ADR-NNN with "expanded trust
  boundary" in the title)
- **Schema bumps** (audit-log v2.X → v2.Y additions you may want to
  capture)

### 2. Verify your local state is committed

```bash
cd /path/to/your/project
git status
```

If anything in `.claude/` is uncommitted, commit it first or stash.
The `--pin` mode of `upgrade.sh` refuses to proceed otherwise (this
is intentional — uncommitted local edits + framework upgrade =
hard-to-debug merge conflicts).

### 3. Snapshot framework state

```bash
bash .claude/scripts/ceo-backup.sh
```

This snapshots audit log + memory + agent-metrics so you can
recover if the upgrade misbehaves.

**Upgrading from v1.3.0 with an ACTIVE plan? Read this first.** Since
v1.4.0 the audit log AND the plan state stores (scratchpad SQLite files
used by `/resume` and inter-agent handoffs) resolve per project through
`.claude/hooks/_lib/runtime_paths.py`, not through the legacy
`$HOME/.claude/projects/ceo-orchestration/` directory. Nothing is
migrated: after the upgrade a repository with a plan in flight opens a
NEW, empty state store, and the old files stay on disk. Before you run
the first session on the new version, pick one route:

- keep reading the legacy store until the plan closes by exporting
  `CEO_PROJECT_NAME=ceo-orchestration` (the documented escape hatch in
  `state_store.py`; it re-creates the basename-collision hazard, so drop
  it as soon as the plan is done), or
- copy `$HOME/.claude/projects/ceo-orchestration/state/` into the new
  per-project directory printed by
  `python3 .claude/hooks/_lib/runtime_paths.py --state-dir`.

Two more per-project records move with v1.4.0 and are NOT migrated either
(signed conditions of rc.1): the cost-envelope counters
(`cost-envelope-*.json` — with them at zero, a swarm dispatch that your
accumulated spend would have blocked is allowed; do not enable `CEO_SWARM`
after the upgrade before copying them), and `credential-rotation.json`
(a stale credential loses its rotation warning and the blocking decision
until the record is copied). Copy both from the legacy directory into the
new per-project directory before the first session, like `state/`.

Three more things to check BEFORE running `scripts/upgrade.sh` (signed
conditions of rc.1, all in the upgrader's delivery of `docs/` and
`.github/`): (1) a file of yours under `docs/` or `.github/` that is
byte-identical to a template of ANY framework version — the current one
included — but that the framework never delivered, is treated as the
framework's own copy: replaced (or mode-normalised) and registered as
framework-owned (later upgrades rewrite it, `doctor.sh --repair` treats your
edits as drift, `uninstall` removes it); edit or move such a file first if
you want to keep it yours. (2) `<target>/.claude.bak` must be ABSENT or
EMPTY — no entries of any kind inside it — and neither a symlink nor under
one, and nothing else may write there while the upgrade runs: the upgrader
creates `.claude.bak/<timestamp>` with `mkdir -p` and writes its backups
there without the destination confinement the deliveries get, so a
pre-placed symlink or hard link inside it is followed outside the target.
(3) Run the upgrade from a COMPLETE checkout of the framework (a fresh
clone or a tag checkout, `git status --porcelain` empty, every source named
in `scripts/delivery-routes.tsv` present as a regular file) and read the
delivery summary: a route reported SKIPPED without `--pin` means the source
was missing from your checkout and the upgrade is INCOMPLETE even though it
exits 0 — repeat it from a complete checkout.
(4) The upgrader still writes through a few paths that do not go through
the destination confinement of PLAN-185 (the `.claude/plans/` schema-doc
refresh copies over the existing inode; backups; refreshed pre-existing
files; the `.claude/hooks/` delivery; `backup_and_replace` over
`.claude/scripts`, `.claude/commands`, `.claude/skills` and the agent
copies — all test `-d`/`-f` and copy with plain `cp`), so a hard link to
an outside file or a symlink anywhere under `.claude/` or the other
managed trees is written THROUGH, and the root `PROTOCOL.md` pointer is
refreshed with a plain redirect, so a hard-linked pointer is rewritten in
place too. `<target>/.claude` itself must be a real directory. Before
upgrading, both of these must print nothing (paths a `--ceremony user`
install never has are skipped; the symlinks the framework itself created in a
`--link` install are excluded through their `LINK` manifest records — a link
with no such record is yours, not the framework's):

```bash
for p in .claude docs .github SPEC .gitignore PROTOCOL.md; do [ -e "<target>/$p" ] || [ -L "<target>/$p" ] || continue; find "<target>/$p" -type l; done | while IFS= read -r l; do r="${l#<target>/}"; grep -qF "LINK  $r  " "<target>/.claude/.install-manifest.sha256" 2>/dev/null || printf '%s\n' "$l"; done
for p in .claude docs .github SPEC .gitignore PROTOCOL.md; do [ -e "<target>/$p" ] || [ -L "<target>/$p" ] || continue; find "<target>/$p" -type f -links +1; done
```

(5) v1.4.0 mints a per-project injection salt in the native Claude project
directory (`python3 .claude/hooks/_lib/runtime_paths.py --state-dir` prints
it) as `.salt` plus a `salt-minted.json` marker. v1.3.0 never owned those two
names there. If a file of yours already sits at either path, the first
prompt after the upgrade treats a `.salt` that is not exactly 32 bytes as
malformed and truncates it in place, and replaces a regular
`salt-minted.json` unconditionally (signed condition of rc.1). Move both out
of the way BEFORE the first session.

(6) If the repository was installed with `--ceremony user` (or you do not
know its ceremony), run the upgrade with `--no-settings-migrate`. The
additive settings merge still runs; only the baseline-aware leaf migration
is skipped — without the flag it adds `availableModels`, `fallbackModel`
and `permissions.defaultMode: manual` to a profile that excludes them by
design (signed condition of rc.1). The additive hook merge still runs with
that flag and registers `check_config_change.py`, which can BLOCK a settings
edit that removes a protection (kill-switch `CEO_CONFIG_CHANGE_GUARD=0`);
to keep the v1.3.0 advisory behaviour exactly, add `--no-settings-merge`
too. The other hooks that can block are listed with their kill-switch
under `blocking_inclusions` in `templates/settings/settings.user.json`
(signed condition of rc.1).

(7) The two `find` checks of (4) apply before a fresh `install.sh` as well:
its deny-baseline merge writes `.claude/settings.json.deny-baseline.<pid>`
outside the destination preflight, so make sure no
`.claude/settings.json.deny-baseline.*` exists and nothing else creates
entries under `.claude/` while the install runs (signed condition of rc.1).

(8) This must print nothing before upgrading (signed condition of rc.1):

```bash
git ls-files -- .claude/settings.local.json .claude/state state/mcp_client_secrets
```

If it prints a path, `git rm --cached` it and commit first: the upgrader's
ignore helpers refuse a TRACKED sensitive path, but they run after hooks,
scripts, skills and settings were already rewritten, so the refusal leaves a
partially upgraded tree with no manifest, no install-state and no banner.

(9) Run the upgrade with `docs/`, `.github/` and `.claude/` writable by the
user running it and with free disk space, and read the delivery summary: a
failure of the writer or renderer after a route was selected (a read-only
`docs/`, a failed tempfile or rename, a failed CODEOWNERS render) is reported
PRESERVED with exit 0 — a PRESERVED route you never edited is a delivery
that failed (signed condition of rc.1).

(10) A file of YOURS sitting at a path that v1.4.0 introduces is OVERWRITTEN
and becomes framework-owned: the per-file update only treats a framework
file as "new" when the destination is absent; a pre-existing file with no
row in the v1.3.0 manifest is classified FALLBACK, which bypasses
`--on-conflict=refuse`, backs the file up, replaces it, and the manifest
rewrite at the end records the FRAMEWORK hash (signed condition of rc.1).
Before upgrading, list the paths new since v1.3.0 from the framework
checkout — filtered by the updater's own exclusion rule, since the test
trees, `__pycache__` and `*.pyc` are never delivered — and move or rename
any file of yours that coincides:

```bash
git diff --name-status --diff-filter=A v1.3.0 v1.4.0-rc.1 -- .claude/hooks .claude/scripts .claude/commands .claude/agents .claude/skills | awk '$2 !~ /^\.claude\/(hooks\/(tests|legacy)|scripts\/tests|hooks\/_lib\/tests)\// && $2 !~ /(__pycache__|\.pyc$|_lib\/(test_isolation|testing)\.py$)/'
```

(11) v1.4.0 keeps its audit family in the per-project directory Claude Code
itself owns (`python3 .claude/hooks/_lib/runtime_paths.py --state-dir` prints
it). That directory already exists, and the framework claims these names in
it WITHOUT checking who wrote them: `audit-log.jsonl`, `audit-log.errors`,
`audit-log.lock`, `audit-log.jsonl.lock`, `audit-log.last-hmac`,
`audit-log.chain-length`, `audit-log.rotation-manifest.json`, `audit-key`,
`.salt`, `salt-minted.json` (plus the temporaries `*.tmp.<pid>` and
`.salt-minted.json.<hex>.tmp`, the monthly rotation files
`audit-log-<YYYY-MM>[-n].jsonl`, the subdirectory `memory-shared/`) and the
subdirectory `state`, under which the session scratchpad, the spool and five
registered hooks write — a symlinked `state` or `memory-shared` is followed.
A file of yours
under one of those names is appended to and `chmod 0600`ed (the log),
replaced (the sidecars; a malformed `.salt` is truncated in place, check 5)
or, if it is a FIFO, blocks the hook on `open`; and the first key tightens the
directory's mode from 0755 to 0700. At
`audit-key` specifically: a 32-byte file of yours is adopted silently as the
framework's signing key, a file of any other size makes every audit event
carry `hmac=null` (the chain runs unsigned, the session is not blocked), and a
FIFO blocks the hook while reading it. The
first `get_or_create_key()` is also not exclusive: two hook processes can
both publish a key, and one keeps signing with a key that is no longer on
disk (signed conditions of rc.1). After the upgrade and BEFORE the first
session: (a) run this from the target root; it must print nothing — every
reserved name absent, no symlink, no hard link, no non-regular file, the
directory itself not a symlink (it prints RESOLVER FAILED instead of
approving by silence when the path cannot be resolved):

```bash
d=$(python3 .claude/hooks/_lib/runtime_paths.py --state-dir); [ -n "$d" ] || echo "RESOLVER FAILED (run from the target root)"; [ -L "$d" ] && echo "SYMLINK DIR: $d"; for n in state memory-shared audit-log.jsonl audit-log.errors audit-log.lock audit-log.jsonl.lock audit-log.last-hmac audit-log.chain-length audit-log.rotation-manifest.json audit-key .salt salt-minted.json; do p="$d/$n"; if [ -L "$p" ] || [ -e "$p" ]; then echo "PRESENT: $p"; fi; done; for p in "$d"/audit-log-*.jsonl "$d"/audit-*.tmp.* "$d"/.salt-minted.json.*.tmp; do { [ -L "$p" ] || [ -e "$p" ]; } && echo "PRESENT: $p"; done
```

(b) create the key with ONE writer, exclusively and without following links
(the command refuses anything already present at that name, a dangling
symlink included — a plain `>` redirect would have written through it):

```bash
d=$(python3 .claude/hooks/_lib/runtime_paths.py --state-dir); python3 -c 'import os,sys; d=sys.argv[1]; os.makedirs(d, 0o700, exist_ok=True); p=os.path.join(d,"audit-key"); fd=os.open(p, os.O_WRONLY|os.O_CREAT|os.O_EXCL|os.O_NOFOLLOW, 0o600); os.write(fd, os.urandom(32)); os.close(fd)' "$d"
```

and do not open two sessions (or run the hook test-suite next to a session)
on the repository until `audit-key` exists.

The append path has the mirror-image race: the previous HMAC is read before
the log lock is taken, so two parallel writers (two sessions, or two parallel
agent spawns of one session) can chain to the same predecessor, and
`verify_chain()` then reports a break nobody caused. The chain is proof of
integrity only for stretches written by one writer at a time; detection of a
break still holds, the absence of false breaks under concurrent writers does
not (signed condition of rc.1).

(12) The upgrader's provenance classification is fail-OPEN on a malformed
manifest: a record whose digest is not exactly 64 lowercase hex characters,
or a path recorded twice, is dropped or invalidated silently, the file then
has "no baseline", and the FALLBACK branch overwrites it even under the
default `--on-conflict=refuse` (backup kept; ownership and the rewritten
manifest pass to the framework) — signed condition of rc.1. Before
upgrading, run this validator from the target root (python3, standard
library only). It requires a regular file that is not a symlink; every line
in the loader's grammar (HASH record = 64 lowercase hex, two spaces, relpath;
LINK record = `LINK`, two spaces, relpath, two spaces, target); only
CANONICAL spellings (`./x`, `a//b`, `a/./b`, a trailing slash and `..` are
refused — the loader keeps the original spelling and the lookup demands
exact text, so an alias becomes FALLBACK); no control byte anywhere; at
least one record (a zero-byte manifest is "no manifest" to the loader, and
the upgrade then takes the legacy delete-and-recopy path); no relpath
recorded twice, textually or by identity (two spellings of one inode). It
must print nothing and exit 0:

```bash
python3 - <<'PY'
import os, re, sys
f = ".claude/.install-manifest.sha256"
if os.path.islink(f) or not os.path.isfile(f):
    print("BAD manifest: missing, a symlink, or not a regular file"); sys.exit(1)
bad = n = 0; seen = {}; ident = {}; ctl = re.compile(r"[\x00-\x1f\x7f]")
for i, line in enumerate(open(f, "rb").read().decode("utf-8", "replace").split("\n"), 1):
    if line == "" or line.startswith("#"):
        continue
    if line.startswith("LINK  "):
        parts = line[6:].split("  ", 1); rel = parts[0]
        ok = len(parts) == 2 and parts[1] != "" and not ctl.search(parts[1])
    else:
        parts = line.split("  ", 1); rel = parts[1] if len(parts) == 2 else ""
        ok = len(parts) == 2 and re.fullmatch(r"[0-9a-f]{64}", parts[0]) is not None and "  " not in rel
    comps = rel.split("/")
    ok = ok and rel != "" and not rel.startswith("/") and not ctl.search(rel) \
        and os.path.normpath(rel) == rel and "" not in comps and "." not in comps and ".." not in comps
    if not ok:
        print("BAD line %d" % i); bad += 1; continue
    n += 1
    if rel in seen:
        print("DUP " + rel); bad += 1
    seen[rel] = i
    try:
        st = os.lstat(rel); ident.setdefault((st.st_dev, st.st_ino), []).append(rel)
    except OSError:
        pass
for rels in ident.values():
    if len(rels) > 1:
        print("ALIAS " + " = ".join(sorted(rels))); bad += 1
if n == 0:
    print("BAD manifest: no record"); bad += 1
sys.exit(1 if bad else 0)
PY
```

Run the same check before `scripts/uninstall.sh` to see what it will refuse:
since this rc the uninstaller refuses a manifest that is itself a symlink and
every occurrence of a path recorded more than once (exit 6; nothing under
them is archived or removed) — before this rc the second record could remove
a file you modified without `--force` (signed condition of rc.1). Before
`scripts/doctor.sh --repair`, `<target>/.claude.bak` must be absent or empty,
as before an upgrade: doctor's backup directory is predictable and an
existing regular file at that path is overwritten (signed condition of rc.1).
And before EVERY `uninstall.sh` and `doctor.sh --repair`, `<target>` and
`<target>/.claude` must be real directories, not symlinks, with nothing else
replacing them while the script runs: both scripts refuse a symlinked
manifest LEAF but read a manifest that sits behind a symlinked `.claude`,
act on that external provenance, and the uninstaller then deletes the
external manifest (signed condition 69 of rc.1).

The pre-v1.4.0 audit chain is likewise left in place (see `CHANGELOG.md`
[1.4.0], «audit log resolves per PROJECT»).

And run the upgrade with **no Claude session open** on the repository: a
session started on v1.3.0 keeps its hooks resident, and two hook generations
appending to the same audit log (only when `CEO_AUDIT_LOG_PATH` is set)
interleave their records — `verify_chain()` then reports a break that is
an artefact of the mixed window, not tampering.

### 4. Verify CI is green pre-upgrade

```bash
gh run list --limit 5
```

If your project's CI is currently failing, fix that first. Mixing
framework-upgrade-induced regressions with pre-existing failures
makes triage painful.

### 5. Verify the framework's own CI is green at the target tag

The framework dogfoods its own CI. If `v<target>` was tagged,
`release.yml`'s 24h Codex re-pass window (per ADR-103) has passed.
Check:

```bash
gh run list --repo Canhada-Labs/ceo-orchestration \
  --workflow validate.yml --branch main --limit 3
```

All three should be green. If not, the tag may be from an unstable
window — wait for the next tag.

## Upgrade (5–15 min depending on size)

### Standard path: `bash scripts/upgrade.sh`

From your **adopter project root**:

```bash
cd /path/to/your/project
bash scripts/upgrade.sh --pin v1.11.2
```

What `upgrade.sh` does:

1. Backs up your current `.claude/` to `.claude.bak/<timestamp>/`.
2. Pulls the target framework version (`git fetch && git checkout`
   on the framework clone).
3. Re-runs `install.sh` with your existing profile + stack flags
   (preserved in `.claude/.install-config`).
4. Diff-detects per-canonical-5 native agent file. Preserves
   adopter overrides on each (per ADR-052 §Adopter override). The
   `model:` field in particular is preserved if you customized it.
5. Updates skills + hooks + scripts to the target version.
6. Reports any conflicts requiring manual resolution.

### Pin to a specific version

```bash
bash scripts/upgrade.sh --pin v1.11.2
```

The `--pin` mode:

- Refuses to upgrade if `.claude/` has uncommitted changes.
- Is **one-shot, not durable**. It checks the framework source out at
  that ref, runs the upgrade, and restores the source branch on exit
  (`scripts/upgrade.sh` `_upgrade_cleanup`). The ref is recorded in
  `.claude/.install-state.json` under `last_upgrade.pin` as history
  only: the next `upgrade.sh` replays `--profile` and `--stack` from
  that file and **nothing else** (`scripts/upgrade.sh:817,822`). To stay
  on a pinned version, pass `--pin <tag>` on every upgrade.
- Has no MAJOR-boundary guard and no `--allow-major` flag — it
  checks out exactly the tag you pass. Consult `CHANGELOG.md`
  before crossing a MAJOR.

### npm-based install

If you installed via npm:

```bash
cd /path/to/your/project
npm update -g ceo-orchestration
ceo-orchestration upgrade --pin v1.11.2
```

The npm package wraps `bash scripts/upgrade.sh` with the same flags.

### Skipping a MINOR (allowed within v1)

You can jump from `v1.9.x` directly to `v1.11.x` without the
intermediate `v1.10.x`:

```bash
bash scripts/upgrade.sh --pin v1.11.2
```

The framework guarantees forward compatibility within v1 (per
`VERSIONING.md` §End-of-life policy): the audit-log schema is
**additive** (new fields only, never removed or renamed), so there
is no migration to run when you skip a MINOR. `upgrade.sh` has no
`--from` flag and no migration runner — it only refreshes the
framework files to the pinned tag.

**Discouraged but supported:** skipping more than one MINOR. Each
MINOR added tests and behaviors worth dogfooding individually.
Skipping multiple at once means any regression is harder to
attribute.

### Skipping a MAJOR (not yet possible)

There is no MAJOR after `v1.x` as of v1.11.2. When `v2.0` ships, the
upgrade procedure will be amended with a §v1 → v2 migration guide.
Until then, all upgrades are within-v1.

## Post-upgrade (10 min)

### Repair: restore custom hooks the overwrite removed

`upgrade.sh` replaces `.claude/hooks/` wholesale, which deletes any
custom hook files your `settings.json` still references (the legacy
upgrade path does not preserve them). Immediately after the upgrade,
run:

```bash
bash scripts/finish-app-upgrade.sh /path/to/your/project
```

It restores any `settings.json`-referenced hook that exists in the
latest `.claude.bak/` but is missing on disk, gitignores + removes
the `.claude.bak/` backup, and makes a local (un-pushed) commit for
you to review. Skip this only if you have no custom hooks beyond the
framework set.

### 1. Validate governance

```bash
bash .claude/scripts/validate-governance.sh
```

Expect: `PASS: Governance files validated.`

If errors, the most common cause is a skill referenced in
`team.md` that no longer exists in the new version (renamed or
removed). Edit `team.md` to match.

### 2. Run the test suite

```bash
# Stack-specific — example for Python
python3 -m pytest .claude/

# Or for Node
npm test
```

Both the framework's hook tests AND your adopter project's tests
should still pass. If only the adopter tests fail, the
framework upgrade is fine; the failure is in your code (likely a
new lint/type-check rule).

### 3. Spot-check `/status`

In a fresh Claude Code session:

```
/status
```

Expect: clean output, recent audit-log activity present, no
governance errors.

### 4. Verify native agents intact

```bash
ls -la .claude/agents/
```

Expect: `code-reviewer.md`, `security-engineer.md`,
`qa-architect.md`, `performance-engineer.md`, `devops.md`,
`_dispatch.md`. The 5 canonical-5 + auto-generated dispatch.

If you customized any (e.g. changed `model:` field), open and
verify your override survived.

### 5. Verify hook integration

Run a small spawn to verify the hook chain is intact:

```
/spawn devops "list the env vars defined in our .env.example"
```

Expect:
- `check_agent_spawn.py` allows the spawn (you see no
  `GOVERNANCE: missing_skill_content` block).
- `audit_log.py` writes a fresh entry (verify with
  `python3 .claude/scripts/audit-query.py recent --limit 1`).
- The audit entry has `model: "claude-haiku-4-5-20251001"` (or
  your override).

### 6. Verify cost tooling

```bash
python3 .claude/scripts/ceo-cost.py --since 1h
```

Expect: a row for the spawn from step 5 with cost > 0.

### 7. Verify health check

```bash
python3 .claude/scripts/ceo-health.py
```

Expect: exit 0. If exit 1, read the listed issues.

## Rollback procedures

Two paths depending on what failed.

### Rollback A — restore the previous install

`upgrade.sh` backed up your previous install to
`.claude.bak/<timestamp>/`. Restore via:

```bash
TIMESTAMP=$(ls -t .claude.bak/ | head -1)
rm -rf .claude
cp -r .claude.bak/$TIMESTAMP .claude
```

This restores the **framework files**. Your `team.md`, `CLAUDE.md`,
plans, and skills under `domains/<your-domain>/` were never touched
by the upgrade.

### Rollback B — git revert + re-install

If you committed any framework files (e.g. a settings.json change),
revert the commit and re-install:

```bash
git log --oneline -- .claude/ | head -5
git revert <upgrade-commit-sha>
bash scripts/upgrade.sh --pin <previous-version>
```

### After rollback

Run validate-governance + ceo-health to confirm:

```bash
bash .claude/scripts/validate-governance.sh
python3 .claude/scripts/ceo-health.py
```

Then file an issue against the framework with the failure mode
that forced the rollback.

## Adopter override preservation

Per ADR-052 §Adopter override, `upgrade.sh` preserves your
customizations to:

- `.claude/agents/<canonical-5>.md` — `model:` field, additional
  `tools:` entries, prompt body customizations
- `.claude/team.md`, `.claude/frontend-team.md` — your concrete
  personas, project-specific routing, custom approvers
- `.claude/skills/domains/<your-domain>/` — your domain content
- `.claude/CLAUDE.md` — your project context
- `.claude/settings.json` — only the parts you've customized; new
  base hooks added during upgrade

What `upgrade.sh` will overwrite:

- `.claude/skills/core/` — universal skills shipped by framework
- `.claude/skills/frontend/` — universal frontend skills
- `.claude/hooks/` — all hooks
- `.claude/scripts/` — framework-shipped scripts
- `.claude/commands/` — universal slash commands

If you have customized anything in the "will overwrite" list,
either:

1. Move your customization to `domains/<your-domain>/` (preserved)
2. Maintain a fork of the framework
3. Submit your customization upstream as a PR

## Schema migrations (audit log etc.)

The audit log is **additive within v1** — new versions add fields
but never remove or rename. Your existing audit-log.jsonl reads
fine after an upgrade. Specifically:

| Audit-log SPEC version | Added in framework version | What's new |
|-------------------------|------------------------------|------------|
| v2.0 | `v1.0.0-rc.1` | Five typed events: agent_spawn, debate_event, plan_transition, veto_triggered, benchmark_run |
| v2.1 | Sprint 5 | injection_flag |
| v2.2 | Sprint 8 | confidence_gate, lesson_read/archived/restored, lesson_outcome |
| v2.3 | Sprint 9 | lesson_outcome_undone |
| v2.4 | Sprint 11 | state_store_*, budget_*, otel_export_dropped, output_safety_flag, skill_patch_applied, squad_imported |
| v2.5 | Sprint 13 | live_adapter_*, breaker_*, credential_rotation_due, mcp_handler_* |
| v2.6 | Sprint 14 | policy_*, replay_*, prediction_queried, pattern_*, threat_model_* |
| v2.7 | Sprint 32 (PLAN-020) | usage_metadata, cache_coverage, rail (additive on agent_spawn) |
| v2.8 | Sprint 32 (PLAN-021) | model (additive on agent_spawn) |

Per `SPEC/v1/audit-log.schema.md` §Consumer contract, consumers
tolerate unknown fields. Your `audit-query.py` from a newer install
reads logs from older installs without issue. The reverse may
ignore fields silently.

## Upgrade examples (real)

### `v1.10.0` → `v1.11.x` (Claude-only refocus, audit-v2 readiness ladder)

The v1.10.0 → v1.11.x line is **mid-pivot** (audit-v2 verdict
`TRIAL-PENDING-SOAK`). v1.11.0 reframed the framework from
multi-adapter (Gemini + OpenAI + local) to **Claude-only** (ADR-084
+ ADR-085). Adopters who installed against `v1.10.0` should expect:

- Adapter stubs deleted (`gemini.py`, `openai.py`, `local.py`)
- `validate.yml::adapter-matrix` job removed
- 5 plans re-opened `done → executing` per ADR-092 honest-deferral
- New ADRs (092 honest-deferral, 093 60-day refused-ADR moratorium)
- Calendar-soak gates active — 14-day CI green + 30-day no-retag
  + 60-day refused-ADR moratorium (gates earliest TRIAL 2026-06-26)

```bash
cd /path/to/adopter-project

# Pre
bash .claude/scripts/ceo-backup.sh
git status   # clean

# Verify framework's own CI is green at the target tag
gh run list --repo Canhada-Labs/ceo-orchestration \
  --workflow validate.yml --branch main --limit 3
# All three should be green. v1.11.1 had a known release.yml red
# (VERSION/tag mismatch); v1.11.2 is the first clean tag in the
# v1.11 line.

# Upgrade
bash scripts/upgrade.sh --pin v1.11.2

# Post
bash .claude/scripts/validate-governance.sh   # PASS
ls .claude/hooks/_lib/adapters/
# expect ONLY: __init__.py, claude.py
# (gemini.py, openai.py, local.py DELETED per ADR-084)

python3 .claude/scripts/audit-query.py recent --limit 1
# expect 'model' + 'rail' + 'usage_metadata' fields

python3 .claude/scripts/ceo-health.py   # exit 0
```

If your project had any references to the deleted adapter stubs
(unlikely — they were stubs for parity tests, not user-facing),
remove them. Otherwise the upgrade is non-breaking.

### `v1.5.0-rc.1` → `v1.6.0-rc.1` (legacy reference)

```bash
cd /path/to/adopter-project

# Pre
bash .claude/scripts/ceo-backup.sh
git status   # clean

# Upgrade
bash scripts/upgrade.sh --pin v1.6.0-rc.1

# Post
bash .claude/scripts/validate-governance.sh   # PASS
ls .claude/agents/   # 5 canonical-5 + _dispatch.md (NEW from PLAN-020)
python3 .claude/scripts/audit-query.py recent --limit 1
# expect 'model' + 'rail' + 'usage_metadata' fields
python3 .claude/scripts/ceo-health.py   # exit 0
```

If your project hadn't installed the canonical-5 native agents
before (because your existing install predates `v1.6.0-rc.1`),
the upgrade adds them. Customize via the `.claude/agents/<slug>.md`
frontmatter as needed.

### Custom: pin to a specific RC during evaluation

```bash
bash scripts/upgrade.sh --pin v1.11.2

# Run for a week against your real workload
# If happy and 14-day CI green streak holds:
bash scripts/upgrade.sh --pin v1.11.x    # promote to GA when audit-v3 + soak windows clear
```

The `--pin` flag is **one-shot**: a subsequent `bash scripts/upgrade.sh`
without `--pin` follows the source checkout's current default branch, not
the version you pinned. Pass `--pin` on every upgrade to hold a version
(see `VERSIONING.md` §Adopter pinning).

## Coordinating an upgrade across a team

If multiple engineers share the framework install:

1. **Notify the team** before upgrading: "I'm bumping framework
   from `v1.10.0` to `v1.11.2` on Tuesday."
2. **Upgrade in a feature branch**:
   ```bash
   git checkout -b chore/framework-v1.11.2
   bash scripts/upgrade.sh --pin v1.11.2
   git add .claude/
   git commit -m "chore: upgrade framework to v1.11.2"
   git push origin chore/framework-v1.11.2
   ```
3. **Merge with full CI green** — the framework upgrade may
   surface previously-quiet test issues.
4. **Communicate the merge**: "Framework upgraded; rebase your
   feature branches; new env vars in `docs/CHEAT-SHEET.md`."

## When NOT to upgrade

- During an active sprint deadline (delay until post-ship)
- When you have an open SEV-2+ incident (upgrade adds variables)
- During a freeze period your team has agreed on
- When the target is a GA tag cut < 24h after its RC (the ADR-103
  Codex re-pass window isn't done)
- When the framework's own CI is currently red on the target tag
  (wait for the fix-up RC)

## References

- `VERSIONING.md` — what each version digit means
- `SUPPORT.md` — what versions are supported
- `SECURITY.md` — security-driven upgrade triggers
- `docs/DISASTER-RECOVERY.md` — recovery if upgrade goes wrong
- `docs/CHEAT-SHEET.md` — env vars + commands referenced above
- `docs/READINESS-STATUS.md` — current verdict + calendar-soak gates
- `docs/STATE-RECOVERY.md` — resume-from-state patterns
- `docs/OBSERVABILITY.md` — audit-log structure + queries
- `docs/GOVERNANCE.md` — 35+ kill-switches catalog
- `bash scripts/upgrade.sh --help` — full flag reference

Last reviewed: 2026-04-28 (Session 71 / Wave D-3 — PLAN-052 Phase 6
soak window started, audit-v2 19/27 P0 closed; v1.11.2 stable, in
14-day CI green streak Day 1). Adopters on v1.10.x should plan
upgrade within the 6-month
support window; the v1.11 line clarifies the Claude-only thesis +
introduces the audit-v2 honest-deferral framework (ADR-092).
