# Deny baseline — a coarse harness backstop

> **PLAN-153 Wave E item 3.** Status: **lands with the SENT-E ceremony**
> (PLAN-153 staged overlay, sentinel round-1). Once that overlay is applied,
> `scripts/install.sh` (section 6a) ships this baseline into the
> `permissions.deny` list of the `.claude/settings.json` a fresh install
> creates in the target repo — until then no install ships it (the staged
> copy under `.claude/plans/PLAN-153/staged/wave-E/` is the pending source
> of truth).

## The one-sentence honest framing

This baseline is a **coarse backstop** riding on Claude Code's own permission
system — it is **complementary to, and never a substitute for,**
`check_bash_safety.py`'s parse gate (which owns the pipe-to-shell class) and
the rest of the governance hooks. It is deliberately **not sold as coverage**.

## What it ships

Twenty `permissions.deny` entries, in the exact rule syntax the repo already
uses (`Tool(specifier)`, gitignore-style paths for `Read`, glob for `Bash`):

```json
"Read(~/.ssh/**)",
"Read(~/.aws/**)",
"Read(~/.npmrc)",
"Read(~/.config/gcloud/**)",
"Read(~/.kube/config)",
"Read(~/.docker/config.json)",
"Read(~/.git-credentials)",
"Read(~/.netrc)",
"Read(~/.pypirc)",
"Read(**/.env)",
"Read(**/.env.local)",
"Read(**/.env.*.local)",
"Read(**/.env.development)",
"Read(**/.env.dev)",
"Read(**/.env.production)",
"Read(**/.env.prod)",
"Read(**/.env.staging)",
"Read(**/.env.test)",
"Read(**/.env.ci)",
"Bash(curl * | bash)"
```

What the `Read` deny rules buy you (per the Claude Code permissions docs):
they apply to the built-in file tools (Read/Grep/Glob, `@file` mentions,
IDE-shared context) **and** to the file commands the harness recognizes
inside Bash (`cat`, `head`, `tail`, `sed`). Deny rules also match on both
sides of a symlink, so a symlink into `~/.ssh/` is blocked too.

## The `.env` exclusion: why enumerate instead of `**/.env.*`

The ratified requirement was "deny `**/.env` and `**/.env.*` **excluding**
`.env.example` / `.env.sample` / `.env.template`". We verified against the
Claude Code permission semantics that this exception is **not expressible**
with deny+allow:

> "Rules are evaluated in order: deny, then ask, then allow. The first match
> in that order determines the outcome" — and explicitly, "a deny rule can't
> carry allowlist exceptions."

An `allow: Read(**/.env.example)` can never carve a hole in a
`deny: Read(**/.env.*)`; gitignore-style `!` negation is not part of the
permission-rule syntax either. So the baseline takes the ratified fallback:
**deny specific sensitive patterns only.** The example/sample/template
variants stay readable because they are simply never listed.

**Residual (accepted, documented):** any `.env` variant not in the
enumeration above — e.g. `.env.secret`, `.env.backup` — passes this
backstop. That is the price of keeping examples readable, and it is
consistent with the framing: a coarse backstop, not coverage.

## What it deliberately does NOT claim

1. **No subprocess coverage.** Read/Edit deny rules "don't apply to arbitrary
   subprocesses that read or write files indirectly, like a Python or Node
   script that opens files itself." A `python3 -c "open('.env').read()"` walks
   straight past this baseline. OS-level enforcement is the sandbox stack
   (`--stack sandbox`), not this list.
2. **`Bash(curl * | bash)` is a tripwire, not the rail.** Bash pattern rules
   are trivially bypassed by rephrasing (`curl x|bash` without spaces,
   `| sh`, `wget -O- | bash`, `bash <(curl …)`, a variable holding the URL).
   Additionally, the harness splits compound commands at `|` before matching
   rules, so the reliability of a pipe-containing deny pattern is a harness
   implementation detail that may vary across Claude Code versions. The
   pipe-to-shell class is owned by `check_bash_safety.py`'s whole-command
   parse gate (fail-closed on unparseable input); this entry only adds a
   cheap, declarative second opinion.
3. **Project-anchored `.env` rules.** `Read(**/.env)` anchors at the current
   working directory (gitignore semantics), so a `.env` in a *parent*
   directory or another project is not matched. Adopters who want
   filesystem-wide matching can tighten to `Read(//**/.env)` themselves —
   the baseline stays with the ratified, less surprising project anchor.
4. **Not tamper-proof.** The entries live in the target repo's
   `.claude/settings.json`; anything that can edit that file can remove them.
   In this repo that file is itself canonical-guarded; in target repos the
   installed template ships `Edit/Write(.claude/settings.json)` deny entries,
   which raises the bar but is the same class of self-referential guard.
5. **No behavioral certification of enforcement.** Our test
   (`scripts/tests/test-install-deny-baseline.sh`) behaviorally certifies the
   *install mechanism* — entries land, dedup, order, opt-out, exclusions,
   no-jq fallback — by running the real installer. Whether the live harness
   *enforces* a given entry is Claude Code's contract, not this repo's, and
   is not replayable in CI without the harness. We say so instead of
   pretending otherwise.

## Idempotency and re-runs

- The injection runs **only when the install run itself created**
  `settings.json`. Re-running `install.sh` hits the existing
  `EXISTS -> SKIP` path, so an entry you deleted is never re-added.
- The merge is order-preserving and deduplicating (template entries stay
  first, baseline entries appended once), so even a forced re-apply cannot
  duplicate entries.

## How an adopter opts out

- **At install time:** `CEO_INSTALL_SKIP_DENY_BASELINE=1 ./scripts/install.sh <target> …`
  skips the injection entirely (mirrors `CEO_INSTALL_SKIP_SELF_SHA`).
- **After install:** delete any entries you don't want from
  `permissions.deny` in `<target>/.claude/settings.json`. Re-runs of the
  installer will not put them back.
- **Fail-open on infrastructure:** if neither `jq` nor `python3` is available
  at install time, the baseline is skipped with a warning (the settings file
  is left exactly as the template shipped it) — the install never fails
  because of this section.
