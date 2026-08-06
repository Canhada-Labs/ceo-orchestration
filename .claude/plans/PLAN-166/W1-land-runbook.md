# PLAN-166 W1 — land runbook (ceremony pack, assembled 2026-08-06)

> Pack assembled at HEAD `65daff0167ee7cc0a83e29c1dfdb7f9d4cf598c1`. Every
> patch under `staged/patches/` was `git apply --check`-clean against that
> commit; the merged asserts file ran 52/52 green against the STAGED YAMLs
> under python3 3.9.6; all six staged `.sh` are `shellcheck -S warning`
> clean; the three staged workflows parse as YAML (PyYAML).
>
> Sources of truth inside this pack:
> - **staged copies** under `.claude/plans/PLAN-166/staged/<repo-path>` —
>   the LAND SOURCE (modes included: `install.sh`, `upgrade.sh`,
>   `doctor.sh`, `check-framework-updates.sh`,
>   `test-upgrade-spec-ownership.sh` are 755; `_framework_manifest_set.sh`
>   is 644 — sourced, not executed).
> - **patches** under `staged/patches/` — the verification mirror
>   (HEAD → staged diff), used for `git apply --check` drift detection.
> - `staged-manifest.sha256` (TRACKED, this directory) — fail-closed
>   integrity pin over every staged file.
> - `W1-approved-draft.md` (this directory) — the sentinel draft; see its
>   header for the fill-at-signing steps.
> - `staged/notes-w1b-kernel-override.md` — the release.yml kernel route.
> - `staged/notes-w1c-f3.md` — F3 deferred-apply snippets + the ADR-count
>   census table.

## 0. Preconditions (STOP if any fails)

```bash
cd "$(git rev-parse --show-toplevel)"

# 0.1 The W0 fleet's free-surface work must be COMMITTED — the ceremony
#     scope is derived from `git status --porcelain`, so any unrelated
#     dirt makes touched−scope=∅ impossible. Expect EMPTY except the
#     untracked .claude/plans/PLAN-166/** pack artifacts themselves
#     (the §7-tolerated plan-evidence residual — they commit WITH the
#     ceremony in §8):
git status --porcelain

# 0.2 Kernel-override hygiene (notes-w1b §0). ALL THREE must report 0 /
#     absent; any residue → remove it before proceeding:
env | grep -c CEO_KERNEL_OVERRIDE || true
grep -c CEO_KERNEL_OVERRIDE .claude/settings.local.json 2>/dev/null || true
grep -c CEO_KERNEL_OVERRIDE ~/.zshrc ~/.zprofile ~/.bashrc 2>/dev/null || true

# 0.3 Fail-closed integrity of the staged inputs (lesson
#     feedback-staged-inputs-need-tracked-hash-manifest). rc must be 0:
shasum -a 256 -c .claude/plans/PLAN-166/staged-manifest.sha256
```

## 1. Live-dependency drift check

The pack depends SEMANTICALLY on these live files. Compare against the
assembly-time shasums; **any divergence → re-read the diff of that file
and re-verify the corresponding staged surface before applying** (the
W0 fleet was editing free surfaces concurrently — divergence is
expected for the files marked `in-flight`; the check is that the
divergence is the fleet's W0 work, not something unknown).

```bash
shasum -a 256 \
  .claude/scripts/local/_release_tag_guard.py \
  .claude/scripts/await_release_gate.py \
  .claude/scripts/tests/test_await_release_gate.py \
  .claude/scripts/local/_release_bump_sites.py \
  .claude/scripts/local/verify-counts.sh \
  scripts/tests/test-install-upgrade-parity-e2e.sh \
  scripts/tests/_parity_classify.py \
  .claude/hooks/_lib/testing.py \
  .claude/hooks/check_canonical_edit.py \
  .claude/hooks/check_arbitration_kernel.py \
  .claude/scripts/local/generate-ceremony.sh \
  .github/release-notes-template.md \
  RELEASE.md \
  docs/GUIA-COMPLETO.md
```

| live file | sha256 @ assembly (2026-08-06, worktree) | state @ assembly | consumed by |
|---|---|---|---|
| `.claude/scripts/local/_release_tag_guard.py` | `0dec1843b0fe2b0293af609982f587700c57a45e287f041e87e0420018979dd7` | in-flight (W0) | release.yml gate step; W1BGuardModuleContractTest |
| `.claude/scripts/await_release_gate.py` | `28c3a6f990b588b71c13197830b9554148d9c784f55f2d76a7e936747df74bd7` | in-flight (W0) | npm-publish.yml await job |
| `.claude/scripts/tests/test_await_release_gate.py` | `7c0914ff7dffc4a49a54585b4bf3b5f6b826c7f473e644cee536076a81b19b7a` | in-flight (W0) | decision-function battery |
| `.claude/scripts/local/_release_bump_sites.py` | `11719fbfb6207235e487624879eb09aa079e8392e14b9e4beeccb556ca3bf2b8` | in-flight (W0); W1-C authored its §1a snippet against `0387725...c226` | deferred-apply §1a |
| `.claude/scripts/local/verify-counts.sh` | `58dd72de16d15dcb06fb81531780c15e252da574b9a2268eaebfc2ebcadb6799` | in-flight (W0); W1-C authored its §1b snippet against `898e3ae...03d8` | deferred-apply §1b; ADR-count gate (§5) |
| `scripts/tests/test-install-upgrade-parity-e2e.sh` | `dbfc897e23802d98ae86270f96600f8f53821d1f9e070514a1b58476832498cb` | clean | smoke-install.yml F4 steps |
| `scripts/tests/_parity_classify.py` | `7b3c1c149f5760dfc1298a9b6e421f1d02c0d5f25223ced62f7294c9530093bc` | in-flight (W0) | parity e2e classifier |
| `.claude/hooks/_lib/testing.py` | `ac9aa0d449a4da93ac12fc5c4a144b0e85329578b1a4fe38424c188514d10e60` | clean | TestEnvContext in the asserts file |
| `.claude/hooks/check_canonical_edit.py` | `4e829bf015ca5fc3620bf739a94d6cba3717b666ad7cd9a27bfdd58ad62e346e` | clean | `_CANONICAL_GUARDS` (the 7 sentinel surfaces) |
| `.claude/hooks/check_arbitration_kernel.py` | `8d4418fb8efaf728e7c803eac2c1fada4ba46f842585dfa90d91e10719f07223` | clean | `_KERNEL_PATHS` (release.yml kernel route) |
| `.claude/scripts/local/generate-ceremony.sh` | `ef90991bbd02e05de1f71c523235c0c78c82425d88eddc08ea1f8924f38e931c` | clean | OWNER-CEREMONY generation (G1-G6, R1-R8) |
| `.github/release-notes-template.md` | `3d97a83f6a889df9080387d3ef9c74d13f09c951947314ff68b145239b1a3621` | clean | ReleaseNotesTemplateTest |
| `RELEASE.md` | `d4ae61e65db4d4483b0fe49dcf457eff8867ef21139ea491e5ee2d1050fd3268` | clean | §4 release_steps sed (29→31; content-anchored) |
| `docs/GUIA-COMPLETO.md` | `a4761b3f0c694fd38fc8cbf48990395ee6ed85a4b03fa61498fd03a5c58b8c52` | clean | §4 ADR-count seds (2 matcher-invisible sites; content-anchored) |

> **Closure re-check (2026-08-06, post-refutation):** the W0 fleet
> COMMITTED its round-1 refutation work at `346f4ea` mid-closure and was
> STILL editing free surfaces afterwards (`_release_tag_guard.py`,
> `release.sh`, `verify-counts.sh`, `test_await_release_gate.py`,
> `test_release_bump_sites.py`, `test_verify_counts.py` dirty at closure
> time) — the in-flight rows above WILL have diverged again by morning.
> That is expected; this table is the assembly-time reference, and THE
> AUTHORITY IS RE-RUNNING THIS §1 CHECK AT LAND TIME. All 14 patches
> re-verified `git apply --check`-clean at `346f4ea`; the closure
> simulations (verify-counts rc=0 with the §4 sweep incl. RELEASE.md +
> GUIA; asserts 52/52; S1-S8 e2e 45/45; bump-sites 47/47 under Route A's
> fixture cure) were anchored on `346f4ea` clones.

Then re-run the patch mirror against the CURRENT HEAD — any FAIL means
the base moved under a staged copy; re-merge that surface on top of the
new base and regenerate its patch BEFORE continuing:

```bash
for p in .claude/plans/PLAN-166/staged/patches/*.patch; do
  git apply --check "$p" && echo "OK   $p" || echo "FAIL $p"
done
```

## 2. Sign the sentinel (before any canonical apply)

1. `mkdir -p .claude/plans/PLAN-166/architect/round-1` and copy
   `W1-approved-draft.md` → `architect/round-1/approved.md`.
2. Follow the draft header: real Anchor-SHA, Approved-At, and the
   MECHANICAL Scope re-derivation (step 3 there) — note the scope check
   is repeated in §7 below against the actual tree, BEFORE signing.
   (Practical order: do §3-§6 first with the DRAFT scope in hand, run
   §7's touched−scope=∅, THEN fill+sign — a rewritten approved.md
   always re-signs.)
3. Sign inline (lessons feedback-ceremony-scripts-must-sign-inline +
   GPG pinentry):
   ```bash
   export GPG_TTY=$(tty); gpgconf --kill gpg-agent
   gpg --armor --detach-sign --local-user <OWNER-KEY> \
     .claude/plans/PLAN-166/architect/round-1/approved.md
   ```
   Both signer rails must accept (registry + legacy list); re-sign on
   ANY rewrite of approved.md.
4. Optional but house-preferred: generate the ceremony script —
   ```bash
   bash .claude/scripts/local/generate-ceremony.sh \
     --plan PLAN-166 --round 1 \
     --scope-file .claude/plans/PLAN-166/architect/round-1/approved.md \
     --canonical-paths ".github/workflows/npm-publish.yml,scripts/install.sh,scripts/upgrade.sh,scripts/_framework_manifest_set.sh,.github/workflows/smoke-install.yml,.claude/governance/npm-trusted-publisher.txt,.github/workflows/release.yml" \
     --output .claude/plans/PLAN-166/OWNER-CEREMONY.sh
   ```
   (G1 validates those 7 against `_CANONICAL_GUARDS`; the release.yml
   apply STILL follows §5's kernel route — R7 keeps the smoke gate
   override-free.)

## 3. Apply the NON-kernel surfaces (staged copies are the source)

```bash
S=.claude/plans/PLAN-166/staged
# Group A (minus release.yml — kernel, §5):
cp -p "$S/.github/workflows/npm-publish.yml"                     .github/workflows/npm-publish.yml
cp -p "$S/.claude/governance/npm-trusted-publisher.txt"          .claude/governance/npm-trusted-publisher.txt
cp -p "$S/.claude/governance/pair-rail-verdict-template.md"      .claude/governance/pair-rail-verdict-template.md
cp -p "$S/.claude/scripts/tests/test_release_workflow_asserts.py" .claude/scripts/tests/test_release_workflow_asserts.py
# Group B:
cp -p "$S/.claude/.framework-version"                            .claude/.framework-version
cp -p "$S/.claude/adr/ADR-155-AMEND-1-delivery-record-ownership.md" .claude/adr/ADR-155-AMEND-1-delivery-record-ownership.md
cp -p "$S/.claude/scripts/check-framework-updates.sh"            .claude/scripts/check-framework-updates.sh
cp -p "$S/.github/workflows/smoke-install.yml"                   .github/workflows/smoke-install.yml
cp -p "$S/INSTALL.md"                                            INSTALL.md
cp -p "$S/scripts/_framework_manifest_set.sh"                    scripts/_framework_manifest_set.sh
cp -p "$S/scripts/doctor.sh"                                     scripts/doctor.sh
cp -p "$S/scripts/install.sh"                                    scripts/install.sh
cp -p "$S/scripts/tests/test-upgrade-spec-ownership.sh"          scripts/tests/test-upgrade-spec-ownership.sh
cp -p "$S/scripts/upgrade.sh"                                    scripts/upgrade.sh

# Exec-bit belt-and-braces (S286 cp-loses-exec-bit class; `cp -p` should
# preserve, VERIFY anyway — the landed mode is what ships):
chmod +x scripts/install.sh scripts/upgrade.sh scripts/doctor.sh \
  scripts/tests/test-upgrade-spec-ownership.sh \
  .claude/scripts/check-framework-updates.sh
ls -l scripts/install.sh scripts/upgrade.sh scripts/doctor.sh \
  scripts/_framework_manifest_set.sh \
  scripts/tests/test-upgrade-spec-ownership.sh \
  .claude/scripts/check-framework-updates.sh
# _framework_manifest_set.sh must stay 644 (sourced, not executed).
```

## 4. Doc-count sweep (ADR 188 → 189 + release_steps 29 → 31) + conditional deferred-apply

**Census discipline: the census is RUN, not recited** (S294 lesson — the
numeral-mirror failed 4x). The table in `staged/notes-w1c-f3.md` §3 (12
matcher-reachable occurrences across 8 docs; the note's own "9 docs"
headline is a miscount — trust the table rows, then trust the GATE) is
the starting point; the authority is `verify-counts.sh` going green
AFTER the edits.

```bash
# BSD sed (macOS). Patterns are content-anchored — line numbers WILL
# have drifted (docs/CTO-GUIDE.md was in-flight at assembly).
sed -i '' 's/\*\*188 ADRs\*\*/**189 ADRs**/' CLAUDE.md
sed -i '' 's/# 188 ADRs/# 189 ADRs/' README.md README.pt-BR.md npm/README.md docs/FAQ.md
sed -i '' 's/| Architecture decision records | \*\*188\*\*/| Architecture decision records | **189**/' README.md README.pt-BR.md docs/README.md npm/README.md
sed -i '' 's/| ADRs shipped | 188 |/| ADRs shipped | 189 |/' docs/CTO-GUIDE.md
sed -i '' 's/# 188 ADRs on disk/# 189 ADRs on disk/' docs/CTO-GUIDE.md
sed -i '' -E 's/(\| ADRs +\| )188/\1189/' docs/ARCHITECTURE.md
# Two non-matcher-reachable extras in an already-touched file (assembler
# census, same pass, zero extra scope):
sed -i '' 's/# 188 architecture decision records/# 189 architecture decision records/' docs/ARCHITECTURE.md
sed -i '' 's/(188 to date)/(189 to date)/' docs/ARCHITECTURE.md
# Re-pass closure: docs/GUIA-COMPLETO.md is in the gate's DOCS but carries
# TWO ADR-count claims (:167 and :1225) whose phrasings NO matcher reaches —
# left alone they would silently claim 188 with 189 on disk (the exact
# [[feedback-adr-count-drift-unwatched-docs]] class). Swept here; file is in
# Scope group B. Follow-up (free surface, NOT this ceremony): add a matcher
# for both phrasings to verify-counts.sh, per its own NOTE ("matcher or
# delete the claim") — it was W0-in-flight at pack time, so no live edit here.
sed -i '' 's/188 ADRs document every architectural decision/189 ADRs document every architectural decision/' docs/GUIA-COMPLETO.md
sed -i '' 's/188 Architecture Decision Records/189 Architecture Decision Records/' docs/GUIA-COMPLETO.md

# Re-pass closure (P1): the staged release.yml adds 2 named steps to
# release-gate (marker==VERSION + delta/ancestry), so the DERIVED
# release_steps count goes 29 -> 31 — and verify-counts.sh scans RELEASE.md
# with an EXACT rule for it. Without this line the ceremony's own §6(d)
# gate goes red post-apply with the fix outside the signed scope. RELEASE.md
# is in Scope group A (it documents the group-A release.yml).
sed -i '' 's/release-gate + publish-release (29 steps,/release-gate + publish-release (31 steps,/' RELEASE.md

# Post-sweep census MUST come back empty:
grep -rn "188" CLAUDE.md README.md README.pt-BR.md docs/ARCHITECTURE.md \
  docs/FAQ.md docs/README.md docs/CTO-GUIDE.md docs/GUIA-COMPLETO.md \
  npm/README.md INSTALL.md \
  | grep -iv "S188\|PLAN-188\|#188\|0188\|1188" | grep -i "adr\|decision record" || echo "sweep clean"
# And the release_steps cite must now read 31 (the gate re-checks in §6(d)):
grep -n "(31 steps" RELEASE.md
```

**Conditional deferred-apply** (notes-w1c §1) — **STATUS RE-CHECKED at
closure (2026-08-06, HEAD `346f4ea`): the W0 fleet HAS committed both
files and the marker site is ABSENT from both, so the original
"apply-if-committed" condition FIRES. But a full simulation (clean clone
@`346f4ea`, all 14 patches, §1a+§1b applied, §4 sweep) found that §1a AS
WRITTEN turns the fleet's own NEW dry-run tests red** —
`test_release_bump_sites.py::test_dry_run_leaves_index_and_worktree_clean`
and `::test_dry_run_restores_a_site_the_table_grew` fail because their
synthesized fixture repo does not create `.claude/.framework-version`;
§6(b) would go red MID-ceremony (the iterate-with-signed-sentinel trap).
The cure is verified: +2 lines in the fixture's `write_sites` —

```python
    (repo / ".claude").mkdir(exist_ok=True)
    (repo / ".claude" / ".framework-version").write_text(version + "\n", encoding="utf-8")
```

— inserted right after the `(repo / "VERSION").write_text(...)` line →
47/47 green with §1a applied (simulated). **OWNER-DECISION at signing —
two sound routes, pick one BEFORE §2:**

- **Route A (apply now):** apply §1a + §1b (idempotence guard below) AND
  the 2-line fixture cure to
  `.claude/scripts/tests/test_release_bump_sites.py`, then ADD all THREE
  paths to the Scope. Cost: a third fleet-owned free file rides in the
  signed commit. Benefit: Forma A (i) enforces from this commit.
- **Route B (SKIP, recommended-by-default):** leave §1a/§1b + fixture
  cure to the fleet's own follow-up commit (free surfaces, no sentinel).
  Zero added ceremony risk. Coverage note: VERSION is already 1.3.0 and
  the marker patch ships 1.3.0 byte-identical, so rc.2/GA of THIS train
  need no bump site for the marker — Forma A (i) only matters from the
  next VERSION bump (1.4.0), and Forma A (ii) (release.yml,
  unconditional) protects every tag either way. The follow-up must land
  before the 1.4.0 cycle's first bump.

Idempotence guard (either route, re-pass closure — the fleet may land
the snippets itself; two owners of the same edit would duplicate the
`_SITES` line):

```bash
grep -q '\.framework-version' .claude/scripts/local/_release_bump_sites.py \
  || : apply §1a   # site present already => SKIP §1a, nothing to add to Scope
grep -q '\.framework-version' .claude/scripts/local/verify-counts.sh \
  || : apply §1b   # site present already => SKIP §1b, nothing to add to Scope
```

## 5. release.yml — kernel-override route (LAST apply, minimum window)

Follow `staged/notes-w1b-kernel-override.md` §§1-5 exactly. Summary:

1. Hygiene greps (§0 there) already ran in §0.2 here — re-confirm 0.
2. Arm INLINE (never persisted):
   `CEO_KERNEL_OVERRIDE=PLAN-166-W1-RELEASE-YML-AWAIT-GATE` +
   `CEO_KERNEL_OVERRIDE_ACK=I-ACCEPT` in the governed session's process
   env. The apply MUST be an in-session Edit/Write (a shell `git apply`
   outside the harness emits NO ledger event and the proof below becomes
   impossible). Content source: the staged copy
   `$S/.github/workflows/release.yml` (byte-exact; the patch
   `patches/release-yml-verdict-delta-ancestry.patch` is its mirror).
3. Ledger proof (grep the TRUNCATED plan_id —
   `PLAN-166-W1-RELEASE-YML-AWAIT-GA`, 32 chars) + chain verdict via
   `python3 .claude/scripts/check-audit-hmac-null.py` (never raw
   `verify_chain()` — HMAC-483). Paste both into the ceremony log.
4. Disarm IMMEDIATELY (`unset CEO_KERNEL_OVERRIDE CEO_KERNEL_OVERRIDE_ACK`;
   re-grep env = 0) BEFORE any gate/commit below.

## 6. Gates (override already DISARMED — R7 discipline)

```bash
# (a) The ceremony's own asserts — now resolve LIVE via the markers:
python3 -m pytest .claude/scripts/tests/test_release_workflow_asserts.py -q
# (b) The directed battery the CI routes run (validate.yml:424 / release.yml:332):
python3 -m pytest .claude/scripts/tests/ -q
# (c) The F3 e2e locally once (S1-S8; ~3-4 min) — the CI wiring is
#     smoke-install.yml, but do not sign a red gate:
bash scripts/tests/test-upgrade-spec-ownership.sh
# (d) Derived counts (ADR gate must see 189 with tolerance=0):
bash .claude/scripts/local/verify-counts.sh
# (e) House claims check (ADR count changed):
python3 .claude/scripts/check-claude-md-claims.py 2>/dev/null || \
  python3 .claude/scripts/local/check-claude-md-claims.py
# (f) Hygiene on the landed workflows:
python3 - <<'EOF'
import yaml
for n in (".github/workflows/npm-publish.yml", ".github/workflows/release.yml",
          ".github/workflows/smoke-install.yml"):
    yaml.safe_load(open(n)); print("YAML OK", n)
EOF
shellcheck -S warning scripts/install.sh scripts/upgrade.sh scripts/doctor.sh \
  scripts/_framework_manifest_set.sh scripts/tests/test-upgrade-spec-ownership.sh \
  .claude/scripts/check-framework-updates.sh
```

Any red → fix in the TREE, mirror the fix back into the staged copy,
regenerate that patch, refresh `staged-manifest.sha256`, and re-derive
the Scope. Never iterate with a signed sentinel in hand (S285/S286).

## 7. touched−scope=∅ over the WHOLE commit, THEN sign

```bash
# Everything the ceremony will commit:
git status --porcelain | awk '{print $2}' | LC_ALL=C sort > /tmp/touched.txt
# The signed scope (bullets only). The sentinel itself + its .asc +
# this pack's tracked files (staged-manifest.sha256, W1-approved-draft.md,
# W1-land-runbook.md) ride in the ceremony commit as plan artifacts —
# include them in touched-minus-scope accounting explicitly:
grep -E '^\s+-\s' .claude/plans/PLAN-166/architect/round-1/approved.md \
  | sed 's/^\s*-\s*//' | LC_ALL=C sort > /tmp/scope.txt
comm -23 /tmp/touched.txt /tmp/scope.txt
# The ONLY tolerated comm-23 output: .claude/plans/PLAN-166/** artifacts
# (non-canonical plan evidence). ANYTHING else = STOP, re-derive scope
# or clean the tree. Then fill Anchor-SHA + Approved-At and sign (§2.3).
```

## 8. Single atomic commit (explicit adds — NEVER `git add -A`)

```bash
git add \
  .github/workflows/npm-publish.yml .github/workflows/release.yml \
  .github/workflows/smoke-install.yml \
  .claude/governance/npm-trusted-publisher.txt \
  .claude/governance/pair-rail-verdict-template.md \
  .claude/scripts/tests/test_release_workflow_asserts.py \
  .claude/.framework-version \
  .claude/adr/ADR-155-AMEND-1-delivery-record-ownership.md \
  .claude/scripts/check-framework-updates.sh \
  INSTALL.md RELEASE.md scripts/_framework_manifest_set.sh scripts/doctor.sh \
  scripts/install.sh scripts/tests/test-upgrade-spec-ownership.sh \
  scripts/upgrade.sh \
  CLAUDE.md README.md README.pt-BR.md docs/ARCHITECTURE.md \
  docs/CTO-GUIDE.md docs/FAQ.md docs/GUIA-COMPLETO.md docs/README.md \
  npm/README.md \
  .claude/plans/PLAN-166/architect/round-1/approved.md \
  .claude/plans/PLAN-166/architect/round-1/approved.md.asc \
  .claude/plans/PLAN-166/staged-manifest.sha256 \
  .claude/plans/PLAN-166/W1-approved-draft.md \
  .claude/plans/PLAN-166/W1-land-runbook.md
# + the two deferred-apply paths IFF §4's condition fired.
git commit -S -m "governance(PLAN-166): W1 findings-closure ceremony — await-gate, verdict delta+ancestry, delivery-record ownership (ADRs 188->189) [SENT-PLAN166-W1]"
```

## 9. Post-land validation

1. `git show --stat HEAD` — path set must equal §7's touched list.
2. Re-run §6 (a), (b), (d) on the committed tree.
3. `python3 .claude/scripts/check-audit-hmac-null.py` — chain still OK.
4. Push per the W2 sequence (verdict → push → CI green → tag): the W1
   commit reaches `origin/main` BEFORE `bump --rc 2`; check
   `validate.yml` + `smoke-install.yml` (now exercising the F3+F4 e2e
   steps) + `coverage.yml` on the pushed commit.
5. W2 dependency created by W1-B (notes-w1b §Dependência): the rc.2/GA
   verdicts MUST carry `delta_allowlist:` / `delta_manifest:` /
   `delta_manifest_sha256:` — the template
   `.claude/governance/pair-rail-verdict-template.md` may still lack
   these fields; the module docstring
   (`_release_tag_guard.py`) is the reference.
6. **Revert coupling (know before reverting group B):** release.yml
   (group A) asserts `.claude/.framework-version == VERSION`
   UNCONDITIONALLY, and the marker is a group-B file. Reverting ONLY
   group B leaves every tag run red until release.yml is re-edited —
   i.e. a NEW kernel-override ceremony. Fail direction is closed
   (blocks ship, never publishes); the cost is operational. The draft's
   revert-groups header states the same.
7. **npm-publish await-gate operational note (no change required):** in
   the await job, a failure of the top-level runs LISTING (`gh api
   .../actions/runs?head_sha=...` — including a 403 rate-limit) is
   BLOCK IMMEDIATELY by design (ADR-186: an API error is an incomplete
   verification, not a WAIT). Recovery is a plain RE-RUN of npm-publish:
   the candidate run's `created_at` persists across re-runs, so the
   freshness floor does not invalidate it. Softening (e.g. N consecutive
   listing failures before BLOCK) is a semantics change — post-GA, new
   debate, NOT a ceremony-morning edit.

---

## Adendo de reconcile (2026-08-06 ~04h, CEO)

- Pós-residuais + round codex: `apply --check` **15/15 OK** em `f492545`
  (14 do pack + `w0-verdict-template-delta-fields.patch` novo).
- Drift da tabela §1 RESOLVIDO e explicado: `await_release_gate.py`
  (`GateContext.self_created_at_epoch` agora obrigatório — o YAML staged
  usa o CLI, contrato de exits intacto) e `_release_tag_guard.py`
  (+`E_PARENT_NOT_ANCESTOR=12`; verdict-fields por path canônico exato —
  o patch staged do release.yml JÁ porta ambos, verificado pelo fixer).
  Shas finais: `a8c6eecc…` / `ce104437…`. `verify-counts.sh` `56286b51…`
  e `release.sh` `ef318380…` (assert pós-dry-run fail-closed no ERRO do
  git status — round codex).
- Manifesto regenerado: **32 entradas**, `shasum -c` OK.
