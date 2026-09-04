Rail-Verdict: APPROVE

# Pair-rail — land round 1 — pack `npm-smoke-hermetic-v2` (S344)

- Command: `codex exec review --uncommitted --skip-git-repo-check -c sandbox_mode="workspace-write" </dev/null`
- Run from the repository root against the LIVE tree, after the derivation was applied
  (not against a shadow worktree).
- Base: `e2f3fbc4b90feacd9ebea17a941db25752f880d4` (`main`, equal to `origin/main` at the time of the run).
- Surface reviewed: the single uncommitted path
  `tests/integration/test_install_npm_smoke.py` (16 insertions / 1 deletion).
- rc: 0. No `Full review comments:` block was emitted — a clean round under the
  current codex build, whose convention is that the absence of that block means
  no actionable defect was raised.

Reviewer conclusion, quoted verbatim from the run output (treated as DATA):

> The subprocess-scoped npm configuration validly disables audit, funding, and
> update-notifier network behavior without mutating the parent environment. The
> existing smoke assertions and timeout behavior remain intact.

## Land-side verification that accompanies this round

- `--check-only` re-planned the anchor at the landing HEAD in a fresh detached
  worktree (rc 0), applied cleanly (rc 0), and refused a second apply (rc 1).
- Oracle: `tests/integration/test_install_npm_smoke.py` → 0 (free).
  Control: `scripts/install-npm.sh` → 1 (CANONICAL) and untouched by this pack.
- `timeout=300.0` unchanged — the cure removes the network dependency, it does
  not relax the limit.
- Battery: `tests/integration/test_install_npm_smoke.py` 6 passed in 38.05s;
  the whole `tests/integration` suite 125 passed / 4 skipped in 155.51s.
- Mechanism positive control, re-run this session under `npm install --loglevel http`
  with the same local tarball (sha256 `173f24af…59acb3`, 6 261 824 bytes):
  default env → 1 registry fetch (`POST 200 .../security/advisories/bulk`);
  hermetic env → 0 registry fetches. This is the claim the committed comment makes.
- Timing controls (3× each, same tarball, `/usr/bin/time -p`, 420 s alarm):
  default 1.43 / 1.52 / 1.65 s; hermetic 1.30 / 2.29 / 2.66 s — indistinguishable
  on this machine right now, consistent with the pack's own evidence, which states
  the duration distribution is heavy-tailed and refuses to read a ratio into a
  single sample.

## Residuals carried into the land (unchanged from the pack)

- The causal story (registry round-trips explain the two real CI
  `TimeoutExpired(300.0)` failures) is an INFERENCE with a stated falsifier: the
  next five runs of the E2E job decide it. This commit does not claim to have
  answered that.
- `scripts/install-npm.sh --no-audit --no-fund` remains a separate Owner-ceremony
  item; the script is canonical and was not touched.
