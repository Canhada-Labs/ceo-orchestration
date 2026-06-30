# SBOM — ceo-orchestration

<!-- last-reviewed: 2026-05-26 v1.0.0 -->

**Version:** `1.0.0` (tracks repo-root `VERSION`)
**Format:** manual markdown (CycloneDX-minimal; no tooling runtime dependency).
**Attestation (framework CORE):** the framework **core** — the PreToolUse/
PostToolUse hooks in `.claude/hooks/` and the shared `.claude/hooks/_lib/`
library — is **stdlib-only at runtime**: zero 3rd-party Python packages are
required to install or operate the governance hot path (ADR-002 invariant).
This attestation is scoped to core; opt-in advisory CLIs under
`.claude/scripts/` carry documented optional deps (§2), and the governed
ADR-126 sidecars ship their own 3rd-party deps (§A/§B below). See §A for the
exact narrowing and the W0 scan that backs it.

Generation command (reproducible, core only):

```bash
grep -rhE '^import [a-z_.]+|^from [a-z_.]+' \
  .claude/hooks/_lib/ .claude/hooks/check_*.py .claude/hooks/audit_log.py \
  2>/dev/null \
  | grep -vE '^from \._|^from \.\.|^from _lib' \
  | sed -E 's/^(from|import) ([a-z_]+).*/\2/' | sort -u
```

---

## A. Framework core — stdlib-only attestation (narrowed)

**Scope:** `.claude/hooks/**` (incl. `.claude/hooks/_lib/**`). EXCLUDES
`tests/`, `fixtures/`, and `.claude/sidecars/**`.

**Result:** an AST scan of all core runtime `.py` files
(`PLAN-112-FOLLOWUP-sbom-third-party-disclosure` W0,
`.claude/plans/PLAN-112/staging/sbom-third-party-disclosure/W0-core-scan.txt`;
re-confirmed by `check-stdlib-only.py` at PLAN-120 S185) found **0 third-party
imports on the production hot path of `.claude/hooks` + `.claude/hooks/_lib`** —
the governance runtime is genuinely stdlib-only. **One documented test-only
exception** (PLAN-120 E10-F1): `.claude/hooks/_lib/test_isolation.py` imports
`pytest`. It is the PLAN-119 WS-A pytest-fixture audit-isolation module, placed
under `_lib/` purely so the three test conftests can import it by a stable path;
it is imported ONLY during pytest collection/run, is NOT on any adopter runtime
or hook path, and is NOT shipped by `install.sh` (verified structurally —
PLAN-120 AC4.4). `check-stdlib-only.py` records it as a file-scoped exception
(`_FILE_SCOPED_EXCEPTIONS`), so the genuinely-stdlib-only guarantee for the
production path holds while this attestation stays accurate.

**Carve-out — `.claude/scripts/` advisory CLIs are NOT part of the stdlib-only
core attestation.** The W0 scan found 3 third-party packages imported there,
all in opt-in/advisory CLIs, all lazily imported under `try/except`, none on
any hook execution path:

| Package | Import sites | Disclosed in |
|---|---|---|
| `pyyaml` (`import yaml`) | `run-skill-benchmark.py`, `validate-squad-contract.py`, `local/release-dry-run.py`, `lint-skills.py` | §2 (opt-in) |
| `anthropic` | `run-skill-benchmark.py` (live-adapter path) | §2 (opt-in) |
| `tree_sitter` | `mcp/code_nav_bridge.py` (optional fast path; stdlib fallback) | §2 (opt-in) — newly disclosed |

`pytest` / `hypothesis` appear only under `tests/` (dev-deps, out of scope).

The stdlib modules used by the core are enumerated below.

**Count: 0 third-party runtime dependencies in `.claude/hooks` + `_lib`.** Every
module below ships with CPython ≥ 3.9 (ADR-002 stdlib-only invariant).

| Module | Usage in framework |
|---|---|
| `argparse` | CLI surface of `.claude/scripts/*.py` |
| `base64` | `_lib/redact.py` b64-string redaction |
| `binascii` | fingerprint hex encoding |
| `collections` | `Counter`, `defaultdict` in metrics + redactors |
| `dataclasses` | SPEC/v1 record shapes |
| `datetime` | UTC timestamps in audit emit |
| `enum` | decision codes, severity levels |
| `errno` | filelock contention detection |
| `fnmatch` | allowlist pattern matching |
| `getpass` | `$USER` fallback for audit records |
| `hashlib` | SHA-256 fixture hashing, canonical-edit sentinel |
| `json` | payload parsing, audit emit |
| `math` | confidence/effort calculations |
| `os` | env, path, perm bits |
| `pathlib` | file paths |
| `random` | jitter in retry (test-only) |
| `re` | regex policy matching |
| `shlex` | bash safety tokenizer |
| `shutil` | install.sh companion utilities |
| `socket` | audit-dashboard SSE loopback |
| `sqlite3` | audit-registry drift index (read-only adopter view) |
| `ssl` | adapter HTTPS live path |
| `statistics` | perf-baseline median/p95 |
| `subprocess` | install.sh shell-outs (guarded) |
| `sys` | stdio, exit codes |
| `tempfile` | test isolation (`TestEnvContext`) |
| `threading` | dashboard server |
| `time` | epoch stamping |
| `types`, `typing` | annotations |
| `unicodedata` | redaction normalization |
| `unittest` | test runner fallback |
| `urllib` | adapter live-call transport |

---

## B. Sidecar dependencies (governed per ADR-126)

The framework optionally ships **capability-class sidecars** (ADR-126 — Governed
sidecar capability model, refines ADR-002). Sidecars are the **only** legitimate
importers of third-party Python; core hooks/`_lib` never import them (enforced by
each sidecar's `boundary_test.py` + `check-sidecar-manifest.py`).

**Opt-in / not bundled by default (ADR-126 §"Opt-in by adopter class").**
Sidecars are NOT installed by the framework install. `scripts/install.sh` only
*prompts* (interactive, default-N, 10s timeout) to install the C2 RAG sidecar
on LARGE-profile repos; everything else requires explicit opt-in. The
`default_state` column below is the runtime kill-switch default, not an
"installed" state — a sidecar must first be installed, then enabled.

The table is sourced from the sidecar `manifest.json` files (single source of
truth — package, version-pin, license per
`dependencies.licenses`, ADR-126 tier). The
`check-sidecar-manifest.py --check-sbom-sync` CI gate fails if any
manifest-declared package is missing here.

<!-- SBOM-SECTION-B:BEGIN -->
<!-- AC4 gate: every backticked package in the first column below is matched
     against dependencies.python across all sidecar manifests. Keep the
     `pkg` backtick form so check-sidecar-manifest.py --check-sbom-sync can
     parse it. Do not remove the BEGIN/END anchors. -->

| Package | Version pin | License (SPDX) | Sidecar | Capability | Tier | default_state |
|---|---|---|---|---|---|---|
| `cryptography` | `>=42.0,<44.0` | Apache-2.0 OR BSD-3-Clause | `c1-crypto/cryptography-mvp` | C1 | C | off |
| `chromadb` | `==0.4.24` | Apache-2.0 | `c2-vector-memory/lightrag-mvp` | C2 | B | conditional |
| `sentence-transformers` | `==2.5.1` | Apache-2.0 | `c2-vector-memory/lightrag-mvp` | C2 | B | conditional |
| `lightrag` | `==0.1.0` | MIT | `c2-vector-memory/lightrag-mvp` | C2 | B | conditional |
| `hypothesis` | `==6.100.0` | MPL-2.0 | `c5-dev-tools/hypothesis` | C5 | A | on |
| `jsonschema` | `==4.21.1` | MIT | `c5-dev-tools/hypothesis` | C5 | A | on |

<!-- SBOM-SECTION-B:END -->

**Stdlib-only sidecar:** `c1-crypto/stdlib-ssl-mvp` (C1, Tier-C) declares **no
Python third-party deps** (`dependencies.python: []`); it shells out to the
system `gpg` binary (`dependencies.system: ["gpg"]`). Listed for completeness;
contributes nothing to the table above.

**Notes**
- `cryptography` is dual-licensed; adopters may choose either Apache-2.0 or
  BSD-3-Clause.
- The C5 `hypothesis` sidecar (`hypothesis` + `jsonschema`) is a **dev/test**
  capability (`default_tier: A`, `default_state: on`) used by the property-test
  + manifest-schema CI lanes. It is never imported on a runtime hook path.
- C2 vector-memory packages activate only when `repo_profile=LARGE` AND the
  sidecar is installed AND running (ADR-128).

---

## 2. Dev / test / opt-in dependencies

| Package | Purpose | Scope |
|---|---|---|
| `pytest` | test runner | dev only (CI) |
| `anthropic` | `live` adapter path (opt-in) | runtime **optional** — documented in `docs/stdlib-exceptions.md`; stub adapter is default |
| `pyyaml` | benchmark fixture ingestion | opt-in scripts only (advisory CLIs); hooks/`_lib/` never import YAML |
| `tree_sitter` | optional fast code-nav path in `mcp/code_nav_bridge.py` | opt-in scripts only; lazy `try/except` with a stdlib fallback (`_scan_file_stdlib`); never on a hook path |

Nothing on the `.claude/hooks/` production/runtime path imports `pytest`,
`anthropic`, `pyyaml`, or `tree_sitter`. The sole exception is the test-only
`.claude/hooks/_lib/test_isolation.py` (imports `pytest`; pytest-collection
context only, never an adopter runtime path, not shipped by `install.sh` —
PLAN-120 E10-F1 / AC4.4; recorded in `check-stdlib-only.py`
`_FILE_SCOPED_EXCEPTIONS`). Hooks run on operator workstations with a bare
Python 3.9+ and nothing else. Sidecar third-party packages (§B) live
exclusively under `.claude/sidecars/**` and are opt-in per ADR-126.

---

## 3. GitHub Actions (supply chain)

All 20 workflows (`.github/workflows/*.yml`) pin by full 40-char commit SHA.
**SHA-pinned references: 63 / 63 (100%).**

Verify:

```bash
# Total pinned refs
grep -rE 'uses:.*@[a-f0-9]{40}' .github/workflows/ | wc -l   # 63
# Any non-SHA floating ref (must be empty)
grep -rE 'uses: [^#]+@(v[0-9]+|main|master|latest)\s*$' .github/workflows/
```

Distinct actions in use: `actions/checkout`, `actions/setup-python`,
`actions/setup-node`, `actions/setup-java`, `actions/upload-artifact`,
`actions/download-artifact`, `actions/cache`, `actions/github-script`.
No third-party actions (every `uses:` is a first-party `actions/*` action).

---

## 4. Release supply chain

| Artifact | Mechanism | Reference |
|---|---|---|
| Git tags | 24h Codex re-pass hold → GA via `release.yml` | ADR-103 (amends ADR-015 RC policy) |
| NPM tarball | OIDC + `--provenance` (SLSA L3) | `npm-publish.yml` |
| Commit provenance | CODEOWNERS gate on `main` | `.github/CODEOWNERS` |
| Skill patches | sentinel chain (SP-NNN) | ADR-031 |

---

## 5. Install-time dependencies

`scripts/install.sh` requires: `bash ≥ 4`, `python3 ≥ 3.9`, `git`, `grep`,
`sed`, `find`. No `curl | bash`. Tarball mode (`scripts/install-npm.sh`) uses
npm's integrity check against the OIDC-provenanced artifact. Sidecars (§B) are
NOT installed by default and require explicit opt-in (ADR-126).

---

## 6. Known non-transitive attestations

- No network call on hook execution (verified by grep for `urllib`, `socket`,
  `subprocess` in `check_*.py` — only `audit_log.py` calls `socket` for the
  local dashboard, loopback-bound).
- No telemetry. No phone-home. Audit log is local-only at
  `~/.claude/projects/<slug>/audit-log.jsonl` with mode 600.
- No dynamic code loading: `eval` / `exec` absent from `.claude/hooks/`
  (grep confirms).
