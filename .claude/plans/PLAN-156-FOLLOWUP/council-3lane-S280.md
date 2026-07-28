> Run: wf_ef98734e-7ec (S280, 2026-07-27) — /council check_canonical_edit.py, Owner-authorized egress.
> BUDGET_S one-off pinned at the reviewed 600s hard cap (Owner OQ3 ratification S280; the 180+2N formula under-budgeted the 1-file deep scope — both external lanes died at 182s, exit 124, on the first attempt).
> stats: {"raw_findings": 18, "groups": 18, "confirmed": 18, "verify_failed": 0, "disagreements": 18} | lanes available: claude,codex,grok

# Cross-Vendor Audit Council — check_canonical_edit.py

## Quorum & lane status

**Quorum: FULL — 3-lane (claude, codex, grok).**

| Lane | Status |
|---|---|
| claude | AVAILABLE — findings returned, adversarially verified |
| codex | AVAILABLE — findings returned, adversarially verified |
| grok | AVAILABLE — findings returned, adversarially verified |

Unavailable vendors: **none**. No lane was substituted or silently dropped.

**Audit-chain record (do not fabricate — orchestrator to append):** one `council_lane_invoked` action was requested per available lane — `claude`, `codex`, `grok` (3 actions total) — for this council run over scope `check_canonical_edit.py`. This synthesizer wrote no files; the note above is the canonical record of what was requested.

## Verdict

**FINDINGS.**

- Confirmed findings: **18** vendor-attributed confirmations (deduplicating cross-vendor convergence: **12 distinct defects**, of which 3 were independently found by all three vendors).
- **verify_failed = 0.** Every raised finding group was judged by the adversarial refuter — no refuter crash, null verdict, or omitted key. Nothing in this run is "raised but unchecked"; there are no unresolved groups blocking interpretation. (A nonzero count here would have meant findings existed that the re-check never ran on — unresolved, not absent. That is not the case.)
- Full 3-lane quorum was met, so this verdict is **not** DEGRADED; it is FINDINGS on complete coverage.

## Confirmed findings

All findings are in `/Users/joaocanhada/canhada-labs/ceo-orchestration/.claude/hooks/check_canonical_edit.py`. Convergent duplicates are merged; raised-by lists every vendor that independently raised the defect.

| # | Dimension | Claim | Raised by | Evidence (adversarially verified) |
|---|---|---|---|---|
| 1 | fail-open / timeout budget | GPG `verify_detached(timeout=15.0)` (L1011) exceeds the hook's registered 5s PreToolUse timeout (settings.json L186); up to 12 pattern-discovered sentinels are GPG-verified per fresh process and the **block path is the slowest**, so slow/deny-all GPG kills the hook and the harness proceeds fail-open on canonical edits. | claude, codex, grok (3/3) | L1011 timeout=15.0 vs settings.json timeout:5; 12 discovered sentinels all with Approved-By + .asc; 34 signed approved*.md with sibling .asc on disk (grok's figure exact); a killed PreToolUse hook emits no decision → tool proceeds. |
| 2 | symlink / discovery integrity | `_find_sentinels` rejects symlinks only at sentinel/parent/grandparent (L858-864) but discovery patterns are 4-5 segments deep (L838-847, incl. `PLAN-*/architect/round-*/approved.md` and audit-v2) — the `PLAN-*` directory segment is never symlink-tested, so a symlinked PLAN dir routes an out-of-tree approved.md into discovery, defeating the F-01 containment intent. | claude, codex, grok (3/3) | L858-864 check only p / p.parent / p.parent.parent; glob follows directory symlinks; 4-5-deep patterns leave the PLAN-NNN (and audit-v2) segment unvalidated. |
| 3 | guard coverage / dual-rail trust | The ADR-121 signer-registry `.claude/security/sentinel-signers-registry.yaml` participates in grant decisions (L1015-1069) but is in neither `_CANONICAL_GUARDS` (L113-331) nor the kernel hard-deny list; the rail is gated on `.exists()` (L1017), so an ordinary Edit can mutate it — and plain deletion **silently disarms** the dual rail. Asymmetric with legacy `.claude/sentinel-signers.txt`, which IS kernel-guarded. | claude, codex, grok (3/3) | Oracle `--is-canonical` → 0 for the yaml; grep `check_arbitration_kernel.py`: `.txt` present (L136) + loader .py guarded, no `security/` entry; L1017 `.exists()` gate confirmed. |
| 4 | fail-closed parsing | A sentinel >64KiB with signed-scope markers silently falls from Tier-1 (L1122, `len(text)<=65536`) to whole-text Tier-2 (L1147); the END marker matches neither `_SCOPE_TERMINATOR_RE` (L413) nor HR (L420), so Scope bullets **outside** the signed markers are honored — marker containment vanishes instead of failing closed. Mitigant: .asc still signs the whole file. | claude | L1122/L1147 tier fallback; L413/L420 terminator regexes exclude the END marker. |
| 5 | fail-open vs C4 doctrine | `read_event` exception and `event.parse_error` both emit allow (L1450-1458) — an INPUT-parse failure in a security matcher is waved through, contra the PLAN-152 C4 fail-closed-on-input doctrine (check_bash_safety precedent). Documented as the ADR-010 fail-open contract (L36-41); the sibling kernel hook is explicitly fail-closed on parse_error "UNLIKE the sentinel hook" — a known, now-confirmed tension. | claude | L1450-1458 both paths allow; L36-41 contract comment; sibling kernel hook contrast. |
| 6 | MCP extraction coverage | Layer-A MCP extraction reads only top-level str / list-of-str under exactly 9 keys (`_MCP_WRITE_PATH_KEYS` L346-356, no `files`); nested write shapes like `files:[{path,content}]` yield zero candidates (dict items dropped at L370-385) → allow at L1485-1487 — canonical writes via such MCP tools bypass the gate entirely. | claude | L346-356 / L370-385 / L1485-1487 verified. |
| 7 | MCP extraction / URI scheme | The extractor accepts `uri` (L355) but passes file URIs directly to `Path` with no scheme stripping; `file://<repo>/.claude/settings.json` classifies non-canonical (first segment `file:` fails `_CANONICAL_PREFIXES` L662) even when the server writes a guarded file. Oracle: file-URI → 0, plain path → 1. | codex | Oracle run confirmed the 0-vs-1 split. |
| 8 | guard coverage / policy integrity | The policy hash-pin registry `.claude/policies/.drift-manifest.json` (544B, pins bash-safety + plan-edit sha256, consumed by check-policy-drift.py) matches no policy guard pattern (guards cover only `*.yaml|*.yml|fixtures/*.jsonl|schemas/*.json`) and is not in `_KERNEL_PATHS` — it can be rewritten without the sentinel required for the very policies it pins. | codex | Oracle → 0; file existence + consumer verified. |
| 9 | forensics / audit fidelity | Veto audits hard-code `blocked_tool="Edit|Write|MultiEdit"` (L1186, L1308) instead of plumbing `event.tool_name`; the hook is registered for `mcp__.*` too (settings.json L181), so MCP and apply-patch blocks are forensically misattributed in the audit chain. | codex | L1186/L1308 literals; registration matcher confirmed. |
| 10 | cache integrity | Comment at L877-879 claims sha256_full "transitively covers signer changes via .asc bytes", but `_compute_sentinel_cache_key` (L903-916) hashes only sentinel bytes + stat + target_rel — .asc / allowlist / registry mutations do not bust the key. Mitigant: cache is per-process. | grok | Comment-vs-code divergence verified at cited lines. |
| 11 | unicode guard coverage | The invisible-unicode SKILL.md guard keys only on the single `file_path` (offender / first_canonical / candidates[0], L1556; gate at L1649-1651); in a multi-candidate mcp__/apply_patch event, other **granted** SKILL.md paths are never scanned under CEO_UNICODE_HARDBLOCK=1. | grok | L1556 + L1649-1651 single-path flow verified. |
| 12 | glob coverage | Dispatcher YAML is guarded only as `.claude/dispatcher/*.{yaml,yml}` while `**` applies only to `*.py` (L164-167) — nested `.claude/dispatcher/**/*.yaml` would not be sentinel-gated. No nested YAML on disk today; mitigant: kernel hard-deny covers `.claude/dispatcher/**/*`. | grok | Oracle: nested/sub.yaml → 0, routing-matrix.yaml → 1. |

## ⚠ Cross-vendor disagreements

The reduction flagged **18 disagreement entries** — formally, every confirmed claim was raised by exactly one lane and missed (as a raised claim) by the other two. Restructured, the signal splits in two:

**Convergent-in-substance (raised independently by all 3 vendors — strongest confirmations, not true disagreements):** findings #1 (GPG timeout fail-open), #2 (symlink discovery gap), #3 (unguarded signer-registry YAML). Three vendors converging on the same three defects through independent analysis is the highest-confidence signal in this run.

**True single-vendor catches — what the other two lanes MISSED (the council's headline signal):**

| Only lane that caught it | Findings the other two vendors missed |
|---|---|
| **claude** only | #4 >64KiB Tier-2 marker-containment loss; #5 parse-error fail-open vs PLAN-152 C4 doctrine; #6 nested `files:[{path,content}]` MCP bypass |
| **codex** only | #7 `file://` URI misclassification; #8 `.drift-manifest.json` unguarded hash-pin registry; #9 `blocked_tool` forensic misattribution |
| **grok** only | #10 cache key does not cover .asc/allowlist/registry; #11 unicode guard single-path-only scan; #12 nested dispatcher-YAML glob gap |

Each lane contributed exactly 3 defects no other vendor found — a 9/12 unique-catch rate that is direct evidence the cross-vendor rail is doing work no single reviewer (including the in-harness lane) does alone.

## Advisory note

This report is **ADVISORY evidence only — it authorizes nothing.** Per PROTOCOL.md, the verification cascade V0-V3 is unchanged: no finding here grants, waives, or substitutes for a sentinel, a debate, a ceremony, or an Owner decision. All lane data above is UNTRUSTED vendor output that survived adversarial re-verification; it has been restructured, not extended — nothing was invented by the synthesizer. Any fix work arising from these findings must enter through the normal Plan → Debate → Execute gates (several findings touch kernel/canonical surfaces and will be Owner-ceremony-gated).
