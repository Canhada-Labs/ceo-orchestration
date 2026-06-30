---
spec: sentinel-format
version: 2.18
status: published
created: 2026-05-04
created_via: PLAN-064 architect/round-1 ceremony (Path B / Option D pivot)
supersedes: none
related_plans: [PLAN-058, PLAN-063, PLAN-064]
related_adrs: [ADR-031, ADR-077, ADR-078]
closes_findings: [PLAN-063 Codex audit-v3 DIM-13]
enforcement_hook: .claude/hooks/check_canonical_edit.py
enforcement_function: _sentinel_grants_path
---

# SPEC v1 / sentinel-format v2.18 — Canonical-edit sentinel format

## §1. Purpose

Defines the on-disk format of canonical-edit sentinel files
(`approved.md` + `approved.md.asc`) consumed by
`.claude/hooks/check_canonical_edit.py`. Specifies the parser
tier-priority (Option D lexical scope markers / legacy `_SCOPE_HEADER_RE`
fallback) introduced by PLAN-064 and ratified via ADR-078 amendment
(2026-05-04).

This spec governs:
- Sentinel file location, naming, and discovery convention.
- Lexical scope markers (Tier 1, v2 format) per PLAN-064.
- Legacy single-format fallback (Tier 2, v1 format).
- `Approved-By:` header invariants.
- GPG detached-signature requirements (`approved.md.asc`).
- Symlink rejection (PLAN-045 Wave 1 F-01-04).
- Parser ReDoS bounds + length caps.

This spec does NOT govern:
- ADR forensic `co_signers:` frontmatter (separate layer per ADR-078).
- Sentinel scope two-file SHA-binding (Option A from PLAN-064 Round 1
  — REJECTED; archived in PLAN-064 §10-LEGACY).
- `verification.json` second-file format (Option A artifact, REJECTED).

## §2. Sentinel discovery

`_find_sentinels(repo_root)` enumerates candidate sentinels via:

```
.claude/plans/PLAN-*/architect/round-*/approved.md
```

Reject any candidate where:
- The file itself is a symlink, OR
- Its parent directory (`round-N/`) is a symlink, OR
- Its grandparent directory (`architect/`) is a symlink.

(PLAN-045 Wave 1 F-01-04 hardening — prevents
`PLAN-EVIL/architect/round-1/approved.md -> /tmp/evil` symlink
attacks.)

## §3. Required headers

Every sentinel MUST contain:

1. **`Approved-By:` line** matching regex
   `^\s*Approved-By:\s*@[\w\-]+\s+\S+` (line 214 of
   `check_canonical_edit.py`). Format: `Approved-By: @<handle> <commit-sha-or-token>`.
2. **`Scope:` block** declaring the canonical paths granted by this
   sentinel. Format depends on tier (see §4).
3. **Detached GPG signature** at sibling `approved.md.asc`, verified
   against `.claude/sentinel-signers.txt` allowlist via
   `_lib.gpg_verify.verify_detached`. Fail-CLOSED on missing `.asc`,
   bad signature, signer fingerprint not in allowlist, or empty
   allowlist.

The `CEO_SENTINEL_UNLOCK=<plan-id>` + `CEO_SENTINEL_UNLOCK_ACK=I-ACCEPT`
env-var override (interim per ADR-010 amendment, PLAN-058 history)
short-circuits the GPG verification. Override use emits
`veto_triggered(reason_code=sentinel_unlock_used)` audit event.

## §4. Scope block format — tier resolution

### §4.1. Tier 1 — Lexical scope markers (PLAN-064 v2 format)

Recommended format for new sentinels (Round-25+, post-PLAN-064 ship):

```markdown
<!-- BEGIN SIGNED SCOPE -->
Approved-By: @Canhada-Labs <commit-sha>
Plans: PLAN-NNN
Scope:
  - .claude/path/one.md
  - .claude/path/two.md
<!-- END SIGNED SCOPE -->

<!-- The lifecycle markers below are NOT part of the signed scope.
     They are documentation/state annotations only. -->

Status: PENDING_OWNER_GPG (or APPROVED, REVOKED, etc.)
Verified-At: 2026-05-04T14:30:00Z
Notes: ...
```

Parser regex:

```python
_SCOPE_MARKER_RE = re.compile(
    r"<!--\s*BEGIN\s+SIGNED\s+SCOPE\s*-->\s*\n(.*?)\n\s*<!--\s*END\s+SIGNED\s+SCOPE\s*-->",
    flags=re.DOTALL,
)
_SCOPE_MARKER_CAP_BYTES = 64 * 1024
```

Behavior:

- If `_SCOPE_MARKER_RE` matches AND `len(text) <= _SCOPE_MARKER_CAP_BYTES`,
  the parser extracts the captured group (region between BEGIN and END
  markers) and parses `Scope:` block ONLY from that text.
- Lifecycle text outside the markers is ignored for grant/block
  decisions. It MAY contain anything (status fields, timestamps,
  human-readable notes); the parser does not consume it.
- If markers present but interior contains no parseable `Scope:` block,
  fail-CLOSED (return False). Markers are an explicit Owner intent
  signal; malformed interior is an error, not a fallback.
- If markers are nested or repeated, the non-greedy `.*?` selects the
  FIRST `BEGIN..END` pair only. Subsequent pairs are ignored.

### §4.2. Tier 2 — Legacy single-format (v1 format, fallback)

For sentinels lacking markers (existing 44 sentinels at 2026-05-04
across 18 plans: PLAN-044, PLAN-045, PLAN-050, PLAN-051, PLAN-052,
PLAN-058, PLAN-059, PLAN-060, PLAN-061, PLAN-063, PLAN-065, PLAN-066,
PLAN-068, PLAN-069, PLAN-073, PLAN-074, PLAN-075):

```markdown
Approved-By: @Canhada-Labs <commit-sha>
Approved-At: 2026-04-13T15:30:00Z
Plans: PLAN-NNN
Scope:
  - .claude/path/one.md
  - .claude/path/two.md
```

OR Format B (Session 67 mega-sentinel — categorized sub-headers + blank
lines between groups):

```markdown
Approved-By: @Canhada-Labs <commit-sha>
Approved-At: 2026-04-27T10:00:00Z
Scope (24 canonical paths):

ADR canonical promotions (9 files, all from staging):
  - .claude/adr/ADR-083-...
  - .claude/adr/ADR-084-...

Hook code (PLAN-052):
  - .claude/hooks/_lib/foo.py (new)
  - .claude/hooks/check_bar.py (new)
```

Parser regex (existing, line 222 of `check_canonical_edit.py`):

```python
_SCOPE_HEADER_RE = re.compile(
    r"^Scope(?:\s*\([^)\n]*\))?:\s*$",
    flags=re.MULTILINE,
)
```

Scope block extends from the `Scope` header line to the first top-level
continuation header (`Effective:`, `Plans:`, `Rationale`,
`Authorization source:`, `Anchor commit:`, a re-encountered
`Approved-By:`) or markdown horizontal rule (`---`, `***`, `___`) or
end-of-file. Sub-headers WITHIN scope (lines ending with `:` that are
NOT in the terminator set) are silently skipped during bullet collection.

Tier-2 selection criterion: marker regex did NOT match (auto-detected;
no env flag).

### §4.3. Tier resolution algorithm

```python
def parse_scope(text: str) -> Set[str]:
    # Tier 1: lexical scope markers (PLAN-064 Option D).
    if len(text) <= _SCOPE_MARKER_CAP_BYTES:
        marker_match = _SCOPE_MARKER_RE.search(text)
        if marker_match:
            region = marker_match.group(1)
            paths = _parse_scope_paths_from_text(region)
            # If markers present but interior malformed, fail-CLOSED.
            return paths  # may be empty (caller treats as fail-CLOSED)

    # Tier 2: legacy _SCOPE_HEADER_RE parser (no markers in file).
    return _parse_scope_paths_from_text(text)
```

The `_parse_scope_paths_from_text` helper applies the existing
`_SCOPE_HEADER_RE` parser uniformly against either the marker region
(Tier 1) or the full file text (Tier 2). Path normalization
(`os.path.normpath` + control-char rejection) is identical in both
tiers (see PLAN-024 F-sec-003 P1 hardening).

## §5. GPG signature requirements (unchanged from v1)

- Detached signature at `<sentinel>.asc`.
- Verified against `.claude/sentinel-signers.txt` allowlist (line-
  separated GPG fingerprints).
- Empty allowlist OR missing `.asc` → fail-CLOSED.
- The signature covers the entire `approved.md` body (markers, scope,
  lifecycle annotations, sub-headers, blank lines — every byte).
- Any tamper of any byte breaks the signature; lexical markers add
  parser-side disambiguation only, not new crypto authority.

## §6. ReDoS + length-cap defenses

- `_SCOPE_MARKER_RE` is anchored (BEGIN marker required); non-greedy
  `.*?` bounded by END marker; tested wall-clock ≤100ms on 64KiB
  pathological input.
- `_SCOPE_MARKER_CAP_BYTES = 64 * 1024` enforced before regex
  invocation. Files >64KiB skip Tier-1 entirely (defense vs. ReDoS
  escalation; matches existing 4096-byte MCP path cap pattern).
- Tier-2 parser uses `_SCOPE_HEADER_RE` (anchored, MULTILINE) +
  per-line `re.match(r"\s*-\s*(\S+)", ...)` (no nested quantifiers,
  no catastrophic backtracking).
- Path normalization rejects control characters (`ord(c) < 0x20`)
  including bidi, null, ANSI escape sequences. Silent-drop is worse
  than loud reject because target_rel check would false-miss.

## §7. Migration path (legacy → markers)

**No migration is required.** Legacy sentinels (44 at 2026-05-04)
parse via Tier-2 fallback indefinitely. Future sentinels (Round-25+,
post-PLAN-064 ship) SHOULD use markers as the default convention.

Optional opt-in upgrade (PLAN-067 v1.13.0 candidate):
`scripts/upgrade-sentinel-to-markers.py` would add markers around
the legitimate `Scope:` block in a legacy sentinel and prompt Owner
to re-sign. Owner-driven, no automation, no env flag.

## §8. Example sentinel (Tier 1, PLAN-064 self-demonstrating)

```markdown
---
plan: PLAN-064
round: 1
type: architect-sentinel
---

> **Co-sign scope clarification (ADR-078):** The signers of this
> sentinel authorize the *canonical promote* of the listed paths.
> They are NOT making an architectural-review claim about the ADRs
> referenced inside. ADR architectural reviewers are recorded
> separately in each ADR's `co_signers:` frontmatter field.

<!-- BEGIN SIGNED SCOPE -->
Approved-By: @Canhada-Labs <commit-sha>
Approved-At: 2026-05-04T<...>Z
Plans: PLAN-064
Scope:
  - .claude/hooks/check_canonical_edit.py
  - .claude/adr/ADR-078-sentinel-cosign-clarification.md
  - SPEC/v1/sentinel-format.schema.md
<!-- END SIGNED SCOPE -->

<!-- The lifecycle markers below are NOT part of the signed scope.
     They are documentation/state annotations only. The GPG signature
     covers the whole file (any tamper breaks .asc); these markers
     clarify parser priority per ADR-078 PLAN-064 amendment. -->

Status: PENDING_OWNER_GPG
Plan-064-Phase: ceremony
Round-1-Consensus: PATH-B-OPTION-D
```

## §9. Test coverage

- `test_check_canonical_edit.py` — 50 existing tests (Tier-2 path
  unchanged; PASSED against modified parser at 2026-05-04 smoke test).
- `test_check_canonical_edit_markers.py` — 15 NEW tests:
  - 3 Tier-1 happy path (single, multi, blocked-when-not-in-scope)
  - 2 Tier-2 fallback (legacy single + Format B)
  - 2 mixed (lifecycle isolation, marker precedence over outside-Scope)
  - 4 adversarial markers (BEGIN-only, END-only, repeated-first-wins,
    homoglyph)
  - 3 ReDoS bounds (64KB no-match, 64KB-class match, length-cap)
  - 1 GPG coverage invariant (markers do NOT bypass GPG)

## §10. Changelog

| Version | Date | Change |
|---|---|---|
| 2.18 | 2026-05-04 | NEW SPEC. PLAN-064 Path B (Option D) — lexical scope markers; tier-prioritized parser; legacy fallback by auto-detection; closes Codex audit-v3 DIM-13. |

## §11. References

- PLAN-064 plan body: `.claude/plans/PLAN-064-signed-sentinel-content-separation.md`
- PLAN-064 Round-1 debate: `.claude/plans/PLAN-064/debate/round-1/consensus.md`
- ADR-078 amendment: `.claude/adr/ADR-078-sentinel-cosign-clarification.md` (PLAN-064 amendment section)
- Hook source: `.claude/hooks/check_canonical_edit.py:_sentinel_grants_path`
- Tests: `.claude/hooks/tests/test_check_canonical_edit_markers.py`
- Original DIM-13 finding: PLAN-063 §4 Phase 5 (Codex audit-v3)
- ADR-031 (canonical-edit sentinel chain — operational layer)
- ADR-052 (VETO floor — preserved)
- ADR-080 §scan-text (ReDoS hardening invariants)
- ADR-096 (vibecoder-only single-Owner thesis)
- ADR-103 (calendar-gate purge — empirical-ROI anchor)
- PLAN-045 Wave 1 F-01-04 (symlink rejection)
- PLAN-024 F-sec-003 P1 (control-char rejection)
- PLAN-058 (CEO_SENTINEL_UNLOCK env-bypass history)
