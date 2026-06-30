# Red-Team Adversarial Corpus

**Scope:** PLAN-013 Phase D.5–D.7. Adversarial fixtures used by
`.claude/scripts/red-team-eval.py` to exercise framework defenses
against real-world attack patterns. Runs weekly via
`.github/workflows/red-team.yml` at 15:00 UTC.

## Organization

```
red-team-corpus/
├── README.md                   # THIS FILE
├── flake-budget.yaml           # quarantine policy + ledger template
├── .byte-identity-check.txt    # SHA-256 ledger for autoformat-drift detection
├── synthetic/                  # 25 hand-crafted fixtures (controlled edge cases)
│   └── *.jsonl                 # one fixture per file
└── external/                   # 15 pointer docs to public adversarial datasets
    ├── README.md               # corpus index
    └── *.md                    # one pointer doc per external dataset
```

## Targets (8 categories — ≥3 synthetic fixtures each)

Adversarial inputs are labeled by which defense they target:

| Target id                | Defense under test                                                | Owning ADR |
|--------------------------|-------------------------------------------------------------------|------------|
| `skill_patch_sentinel`   | `check_skill_patch_sentinel.py` hook, GPG sig, Unicode scan       | ADR-031    |
| `audit_log_tamper`       | `_lib/audit_emit.py` filelock + append-only + byte-identity       | ADR-035    |
| `plan_id_spoof`          | `_lib/plan_frontmatter.py` derivation + `_lib/state_store.py` ACL | ADR-027/034|
| `sandbox_escape`         | `check_bash_safety.py` + `_lib/adapters/live/` egress control     | ADR-040    |
| `mcp_handler`            | MCP server ACL + governance passthrough (Phase A deferred)        | ADR-042    |
| `adapter_exfil`          | `_lib/adapters/live/` credential hygiene + OTEL double-redact     | ADR-040/035|
| `output_safety_evasion`  | `check_output_safety.py` NFKC/ZW-strip/entropy/regex pipeline     | ADR-036    |
| `npm_tamper`             | `npm/` shim SHA-256 + GPG + SLSA (Phase E.7)                      | PLAN-013   |

Fixture distribution target: ≥3 synthetic per category → 24 minimum;
we ship 25 with `output_safety_evasion` getting 4 (highest-volume
attack surface).

## Fixture schema (synthetic/*.jsonl)

Each fixture is a single JSONL line with fields:

```json
{
  "id": "SYN-001",
  "target": "skill_patch_sentinel",
  "category": "unicode_bidi_injection",
  "input": "<adversarial payload as string>",
  "expected_behavior": "MUST_BLOCK",
  "reference": "ADR-031 §Decision-drivers #3; unicode Trojan Source (CVE-2021-42574)",
  "severity": "HIGH",
  "notes": "Optional human-readable guidance for reviewer."
}
```

Field reference:

| Field               | Type   | Required | Values                                                           |
|---------------------|--------|----------|------------------------------------------------------------------|
| `id`                | string | yes      | `SYN-NNN` (synthetic) or `EXT-NNN` (external pointer)            |
| `target`            | string | yes      | one of 8 target ids above                                        |
| `category`          | string | yes      | free-form taxonomy slug (kebab-case)                             |
| `input`             | string | yes      | the adversarial payload (escape quotes with JSON rules)          |
| `expected_behavior` | string | yes      | `MUST_BLOCK` \| `MUST_SANITIZE` \| `MUST_EMIT_AUDIT` \| `MUST_REJECT` \| `MUST_QUARANTINE` |
| `reference`         | string | yes      | ADR / CVE / paper citation justifying the expected behavior      |
| `severity`          | string | no       | `LOW` \| `MEDIUM` \| `HIGH` \| `CRITICAL`                        |
| `notes`             | string | no       | reviewer guidance; not consumed by the runner                    |

**Safety rule:** fixtures contain **simulated** payloads only. No
live malware, no weaponized exploits. When a pattern would be
dangerous to transcribe literally (e.g. a real GPG private key), we
use a clearly-labeled stub string (`"-----BEGIN PGP PRIVATE KEY
BLOCK-----\n<SYNTHETIC STUB — NOT A REAL KEY>\n-----END PGP PRIVATE
KEY BLOCK-----"`) and document the intent in `notes`.

## Byte-identity check (autoformat-drift defense)

Per PLAN-013 consensus §S16: fixture content drift under editor
autoformat is silent coverage loss. `.byte-identity-check.txt`
lists every synthetic fixture with its SHA-256; the red-team
workflow computes checksums on each run and fails if any drift.

When a fixture is INTENTIONALLY edited:

1. Review the edit against the schema in this README.
2. Recompute SHA-256:
   `python3 -c "import hashlib,sys; print(hashlib.sha256(open(sys.argv[1],'rb').read()).hexdigest())" synthetic/FOO.jsonl`.
3. Update the matching line in `.byte-identity-check.txt`.
4. Commit the fixture + checksum update in the **same** commit.

## Flake budget

Per PLAN-013 consensus §S17: red-team flakes erode coverage. Policy
in `flake-budget.yaml`:

- **Allowance:** 1 flake per fixture per 7-day window.
- **Quarantine trigger:** 2+ flakes in 7 days → fixture moved to
  `quarantined` state, issue opened with fingerprint hash.
- **Release from quarantine:** requires signed-off root-cause
  analysis in the issue + 7 consecutive clean runs after re-enable.

## External corpus

`external/*.md` contains pointer documents (NOT binary data) for 15
public adversarial datasets. Each pointer documents source URL,
license, retrieval date, and license-compatibility check. Binary
data is NEVER committed — the corpus either syntheses fixtures OR
cites external resources; we never mirror copyrighted material.

## Runner invocation

```bash
python3 .claude/scripts/red-team-eval.py \
    --fixture-dir .claude/scripts/red-team-corpus/synthetic \
    --output junit \
    --quarantine-ledger .claude/scripts/red-team-corpus/flake-budget.yaml
```

CLI reference: see `red-team-eval.py --help` or `scripts/` README.

## References

- PLAN-013 Phase D.5–D.7.
- PLAN-013 debate Round 1 consensus §C9 (corpus ≥40 total = 25
  synthetic + ≥15 external).
- PLAN-013 debate Round 1 consensus §S16 (byte-identity).
- PLAN-013 debate Round 1 consensus §S17 (flake budget).
- ADR-031, ADR-035, ADR-036, ADR-040, ADR-042 (targets).
- `.github/workflows/red-team.yml` (weekly runner).
- `red-team-eval.py` (script).
