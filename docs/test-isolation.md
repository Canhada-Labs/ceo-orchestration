# Test-harness audit-log isolation (dogfood doctrine)

> **Status:** shipped in PLAN-119 (S182). Durable fix for the lesson
> *"verification in the live env pollutes the audit chain"*.

## The problem

This repo **dogfoods an audit-emitting framework in its own repo, against the
real `~/.claude`**. Every hook that runs, and every audit event that is emitted,
resolves its audit-log path from the ambient environment. When a test, a probe,
or an ad-hoc `pytest`/hook invocation runs without an isolated environment, it
writes **real-looking audit events into the LIVE
`~/.claude/projects/ceo-orchestration/audit-log.jsonl`**. Those events carry
HMACs computed under test conditions (or against a different chain head, or by a
stale producer), so they do **not** verify against the live chain:
`audit-verify-chain` later reads `tamper` and `audit-log.errors` floods.

S181 forensics: of 1738 live-log lines, ~1690 were test/probe pollution; only
~47 were the real session.

## The two axes of the fix (PLAN-119)

The naive idea — a kernel guard that refuses to write "when this looks like a
test" — is an **audit-suppression vector** (an attacker could divert a real
session's events off the live chain) and was rejected (WS-B-DROPPED). The robust
design works on two axes an attacker cannot use to silence a real session:

### Axis 1 — destination redirect (WS-A / WS-C)

A **session-scoped autouse pytest fixture** (`_lib/test_isolation.py`,
registered by the root + `.claude/hooks/tests/` + `.claude/scripts/tests/`
conftests) redirects the **full audit/HMAC env carrier set** to a per-session
tmpdir *before any test body runs*:

- **SET** (to the tmp tree): `CEO_AUDIT_LOG_DIR`, `CEO_PROJECT_STATE_DIR`, and
  `CEO_TEST_HARNESS=1`. `CEO_AUDIT_LOG_DIR` is the PRIMARY resolver for every
  audit path (`audit_emit._audit_dir` / `audit_hmac._audit_dir_from_env` /
  `spool_writer._state_dir` all honor it first), so this single anchor redirects
  the whole audit/HMAC/spool surface.
- **CLEARED** (so they default off `CEO_AUDIT_LOG_DIR`): `CEO_AUDIT_LOG_PATH`,
  `CEO_AUDIT_LOG_ERR`, `CEO_AUDIT_LOG_LOCK`, `CEO_AUDIT_KEY_PATH`,
  `CEO_AUDIT_LAST_HMAC_PATH`, `CEO_AUDIT_CHAIN_LENGTH_PATH`,
  `CEO_AUDIT_LOG_FALLBACK_PATH`, `CEO_AUDIT_LOG_ROTATE_BYTES`,
  `CEO_AUDIT_HMAC_DISABLE`.
- **NOT touched:** `HOME` and `CLAUDE_PROJECT_DIR`. `HOME` is only a *fallback*
  for the audit dir — reached solely when `CEO_AUDIT_LOG_DIR` is unset, which the
  fixtures always set. Redirecting `HOME` broke subprocesses that legitimately
  need the real home for tooling (PyYAML in the macOS user-site, the GPG keyring,
  npm/rsync) with zero isolation benefit; the function-scope assert plus the
  byte-identity durable-fix proof cover the residual unset-fallback case.
  `CLAUDE_PROJECT_DIR` is not an audit-location carrier (no audit/HMAC/spool
  resolver reads it), and redirecting it broke "the real repo's policy/config
  files exist" tests. `CEO_AUDIT_SYNC_MODE` is left to `TestEnvContext`'s
  per-test default (the session fixture must not force it, or the async-spool
  opt-out tests would bypass the drain path they assert on).

A redirected process **physically cannot** append to the live log. A
function-scoped autouse assert (via the production resolver
`audit_emit._audit_dir`, never a re-implementation) catches a test that mutates
env back to the live dir mid-run.

`TestEnvContext` continues to re-isolate **per test** on top of this; the
session redirect makes the dir non-live up front so the per-test layer is purely
additive (no test reds because the dir was "live at fixture time").

For subprocess/multiprocessing tests, `TestEnvContext.subprocess_env()` (WS-C)
builds the child env from the **same** carrier enumeration, so a spawned hook
inherits the isolated destination — no second hand-maintained list to drift.

### Axis 2 — write-time origin stamp (WS-D1)

For the spool-drain path, the spool header is stamped `_origin: "test" | "live"`
**at mint time** (the writer knows the truth; the drainer cannot infer it
later). The drain (`spool_writer.drain_now`, the single orchestrator all three
drain paths — opportunistic / atexit / signal — funnel through) quarantines
`_origin:"test"` spool **only when the canonical destination is the live chain**
(compared against `CEO_AUDIT_LIVE_LOG_PATH_SNAPSHOT`, captured before the
redirect). A real session writes `_origin:"live"` and is never quarantined;
legacy spool with no `_origin` defaults to `"live"` (fail-safe toward never
losing a real event). If the snapshot is absent, the filter fails safe to
**no quarantine**.

### Import-time stale-copy closure (WS-D2)

The recurring `unknown action 'output_scan_finding_suppressed'` breadcrumb is
emitted only by a **stale pre-PLAN-106 `audit_emit.py`** loaded onto `sys.path`.
WS-D2 extends the PLAN-118 import-time hard-raise to those archived + sandbox
stale copies, so a stale `audit_emit` cannot be imported as `_lib.audit_emit`
(while ACTIVE staging fixtures are carved out).

## The escape hatch

`@pytest.mark.allow_live_audit_dir` opts a single test out of the function-scope
assert, for the rare test that genuinely exercises the real resolver. **Zero
uses at ship.** A `validate-governance.sh` grep gate keeps it at zero; CODEOWNERS
requires security-engineer review to add one. A reviewer adding the marker MUST
confirm the test cannot instead use `TestEnvContext`.

## Bash-probe orchestration protocol (load-bearing — the residual vector)

The session fixture covers the **pytest** volume. It does **not** cover a bare
Bash probe — a sub-agent (debate archetype, ad-hoc `pytest`/hook run) that the
CEO spawns and that runs hooks in the **live shell** with the real `$HOME`,
never entering a pytest session. No kernel guard can safely close this (a
test-signal write-refusal is the rejected WS-B suppression vector). The mitigation
is **orchestration discipline**, and it is mandatory:

> **Any sub-agent the CEO spawns that may run `pytest`, invoke a hook, or
> otherwise trigger an audit emit MUST run with the audit destination
> redirected** — either by inheriting `CEO_TEST_HARNESS=1` **and** a scratch
> `CEO_AUDIT_LOG_DIR` (e.g. `CEO_AUDIT_LOG_DIR=$(mktemp -d)`), or by running the
> command under a `env -i`-style minimal environment that does not resolve the
> live `~/.claude`.

Concretely, before a probe that emits:

```bash
export CEO_TEST_HARNESS=1
export CEO_AUDIT_LOG_DIR="$(mktemp -d)/audit"
mkdir -p "$CEO_AUDIT_LOG_DIR"
# ... run the pytest / hook / probe here ...
```

After any verification/probe activity in the live env, re-verify the chain
**quiescently** (last thing, after all probe activity) before treating an
`intact` read as authoritative:

```bash
python3 .claude/scripts/audit-verify-chain.py --strict-against-counter
```

## Triage: is a `tamper` read a real attack or test pollution?

Per the S181 lesson, characterize by provenance **before** assuming a producer
bug or rotating:

- **Real `uuid` session_id + `null`/`CanonicalJsonError` HMAC** → a producer
  float-in-HMAC bug (see the `cache_coverage_bps` fix, PLAN-118).
- **Empty / `sess-N` / test session_id + non-null HMAC mismatch** → test-spool
  pollution drained into the live chain. NOT a compromise; the durable fix is
  this isolation harness.

## See also

- `.claude/hooks/_lib/test_isolation.py` — the shared isolation helper.
- `.claude/hooks/_lib/testing.py` — `TestEnvContext` (per-test isolation +
  `subprocess_env`).
- `.claude/plans/PLAN-119-test-harness-audit-isolation.md` — the plan.
- Lesson `feedback-verification-in-live-env-pollutes-audit-chain`.
