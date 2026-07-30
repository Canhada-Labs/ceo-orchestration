# PLAN-164 W1 — bundle de review cross-vendor — SNAPSHOT DO ROUND 1 (SUPERSEDED)

> **NOTA (codex r2 MED-2):** este arquivo é o REGISTRO HISTÓRICO dos bytes
> apresentados ao round 1. Os rounds 1-2 produziram fixes (F1-F7 + r2:
> suffix-newest no resolve_anchor, guard revert-aware, statusMessage na
> migração) — os bytes VIGENTES são os pinados pelos manifests
> (`PLAN-164/inputs-rail.sha256` e `PLAN-163/inputs-pack.sha256`), NÃO os
> diffs abaixo. Verditos: `codex-rail-r*.md` / `grok-rail-r*.md`.

## A. Rail-pack: diffs live -> staged (arquivos pré-existentes)

### .claude/hooks/check_pair_rail.py
```diff
--- .claude/hooks/check_pair_rail.py	2026-07-29 10:16:12
+++ .claude/plans/PLAN-164/staged/rail-pack/.claude/hooks/check_pair_rail.py	2026-07-29 20:54:23
@@ -48,7 +48,7 @@
 ##  a preset review on ANY path; tests inject a review by mocking
 ##  `_invoke_codex_review` at the invoke boundary, never via env.)
 
-- `CEO_PAIR_RAIL_TIMEOUT_S` (default 30) — Codex invoke wall-clock
+- `CEO_PAIR_RAIL_TIMEOUT_S` (default 120) — Codex invoke wall-clock
   cap. On timeout: fail-OPEN.
 - `CEO_PAIR_RAIL_DISABLE` — kill-switch: when set to `1`, hook is a
   no-op (allow). For incident response.
@@ -1714,12 +1714,12 @@
         )
         try:
             timeout_s = float(
-                os.environ.get("CEO_PAIR_RAIL_TIMEOUT_S", "30")
+                os.environ.get("CEO_PAIR_RAIL_TIMEOUT_S", "120")
             )
         except (TypeError, ValueError):
-            timeout_s = 30.0
+            timeout_s = 120.0
         if timeout_s <= 0 or timeout_s > 600:
-            timeout_s = 30.0
+            timeout_s = 120.0
 
         # PLAN-081 Phase 3: route through the asymmetric VETO matrix
         # wrapper instead of the spike _decide() directly. The matrix
```

### .claude/settings.json
```diff
--- .claude/settings.json	2026-07-27 19:11:54
+++ .claude/plans/PLAN-164/staged/rail-pack/.claude/settings.json	2026-07-29 20:56:11
@@ -273,13 +273,14 @@
         ]
       },
       {
-        "_comment": "PLAN-075 v1.13.x narrow-promotion (ADR-106 + ADR-110): PreToolUse Pair-Rail Multi-LLM hook. When Edit|Write|MultiEdit targets an L3+ canonical-guarded path, invokes Codex MCP in read-only review mode and validates the response contains no write-shaped patches (apply_patch envelope, unified diff, JSON Patch RFC 6902). On Codex unavailable: fail-OPEN + breadcrumb. On write-shaped response: BLOCK + audit pair_rail_codex_violation. On clean review: ALLOW + audit pair_rail_review_passed. Sentinel-bypass short-circuits to ALLOW + audit pair_rail_sentinel_bypass. Kill-switches: CEO_PAIR_RAIL_DISABLE=1, CEO_PAIR_RAIL_TIMEOUT_S (default 30s).",
+        "_comment": "PLAN-075 v1.13.x narrow-promotion (ADR-106 + ADR-110): PreToolUse Pair-Rail Multi-LLM hook. When Edit|Write|MultiEdit targets an L3+ canonical-guarded path, invokes Codex MCP in read-only review mode and validates the response contains no write-shaped patches (apply_patch envelope, unified diff, JSON Patch RFC 6902). On Codex unavailable: fail-OPEN + breadcrumb. On write-shaped response: BLOCK + audit pair_rail_codex_violation. On clean review: ALLOW + audit pair_rail_review_passed. Sentinel-bypass short-circuits to ALLOW + audit pair_rail_sentinel_bypass. Kill-switches: CEO_PAIR_RAIL_DISABLE=1, CEO_PAIR_RAIL_TIMEOUT_S (default 120s; registration cap 150s — invariant guarded by test_pair_rail_timeout_invariant.py).",
         "matcher": "Edit|Write|MultiEdit",
         "hooks": [
           {
             "type": "command",
             "command": "bash \"$CLAUDE_PROJECT_DIR/.claude/hooks/_python-hook.sh\" check_pair_rail.py",
-            "timeout": 60
+            "timeout": 150,
+            "statusMessage": "Pair-rail cross-model review (may take 1-2 min)"
           }
         ]
       },
```

### templates/settings/settings.base.json
```diff
--- templates/settings/settings.base.json	2026-07-27 19:11:54
+++ .claude/plans/PLAN-164/staged/rail-pack/templates/settings/settings.base.json	2026-07-29 20:56:16
@@ -89,13 +89,14 @@
         ]
       },
       {
-        "_comment": "PLAN-152 governance-03 (mirror of dogfood ADR-106 + ADR-110): PreToolUse Pair-Rail Multi-LLM hook. When Edit|Write|MultiEdit targets an L3+ canonical-guarded path, invokes Codex MCP in read-only review mode and validates the response contains no write-shaped patches. Adopters get the codex .mcp.json from install.sh, so the rail is meaningful out of the box; on Codex unavailable it fail-OPENs with a breadcrumb (adopters without Codex pay only the no-op). Kill-switches: CEO_PAIR_RAIL_DISABLE=1, CEO_PAIR_RAIL_TIMEOUT_S (default 30s).",
+        "_comment": "PLAN-152 governance-03 (mirror of dogfood ADR-106 + ADR-110): PreToolUse Pair-Rail Multi-LLM hook. When Edit|Write|MultiEdit targets an L3+ canonical-guarded path, invokes Codex MCP in read-only review mode and validates the response contains no write-shaped patches. Adopters get the codex .mcp.json from install.sh, so the rail is meaningful out of the box; on Codex unavailable it fail-OPENs with a breadcrumb (adopters without Codex pay only the no-op). Kill-switches: CEO_PAIR_RAIL_DISABLE=1, CEO_PAIR_RAIL_TIMEOUT_S (default 120s; registration cap 150s — invariant guarded by test_pair_rail_timeout_invariant.py).",
         "matcher": "Edit|Write|MultiEdit",
         "hooks": [
           {
             "type": "command",
             "command": "bash \"$CLAUDE_PROJECT_DIR/.claude/hooks/_python-hook.sh\" check_pair_rail.py",
-            "timeout": 60
+            "timeout": 150,
+            "statusMessage": "Pair-rail cross-model review (may take 1-2 min)"
           }
         ]
       },
```

### scripts/doctor.sh
```diff
--- scripts/doctor.sh	2026-07-07 01:51:50
+++ .claude/plans/PLAN-164/staged/rail-pack/scripts/doctor.sh	2026-07-29 20:58:30
@@ -643,7 +643,58 @@
   fi
 fi
 
+# ---------------------------------------------------------------------------
+# Pair-rail timeout coherence (PLAN-164 / ADR-110-AMEND-1 — ADVISORY,
+# report-only, NEVER drives the exit code): the harness kills a hook at its
+# settings.json registration timeout, so a check_pair_rail.py registration
+# below the hook's INTERNAL default (CEO_PAIR_RAIL_TIMEOUT_S) + the 30s
+# invariant margin means the codex verdict can be killed mid-flight — the
+# historical 12/12 pair_rail_case F/TIMEOUT class (hook-kill risk). The
+# internal default is read with the SAME regex the invariant uses:
+# os.environ.get("CEO_PAIR_RAIL_TIMEOUT_S", "NNN"). Fail-open: missing
+# jq/hook/settings or an unparseable value => NOTE + skip.
 # ---------------------------------------------------------------------------
+_pair_rail_timeout_check() {
+  _prt_settings="$TARGET/.claude/settings.json"
+  _prt_hook="$TARGET/.claude/hooks/check_pair_rail.py"
+  if [ ! -f "$_prt_settings" ] || [ ! -f "$_prt_hook" ]; then
+    return 0
+  fi
+  if ! command -v jq >/dev/null 2>&1; then
+    _log "    NOTE: pair-rail timeout check skipped (jq not found) — advisory only"
+    return 0
+  fi
+  _prt_reg="$( jq -r '[ .hooks // {} | to_entries[] | .value
+      | select(type == "array") | .[] | .hooks[]?
+      | select((type == "object")
+          and ((.command? | type) == "string")
+          and (.command | test("check_pair_rail\\.py")))
+      | .timeout ] | first // empty' "$_prt_settings" 2>/dev/null || true )"
+  _prt_int="$( sed -n 's/.*os\.environ\.get("CEO_PAIR_RAIL_TIMEOUT_S", "\([0-9][0-9]*\)").*/\1/p' "$_prt_hook" 2>/dev/null | head -n 1 )"
+  case "$_prt_reg" in
+    ''|*[!0-9]*)
+      _log "    NOTE: pair-rail timeout check skipped (no numeric check_pair_rail.py registration timeout in settings.json) — advisory only"
+      return 0 ;;
+  esac
+  case "$_prt_int" in
+    ''|*[!0-9]*)
+      _log "    NOTE: pair-rail timeout check skipped (internal CEO_PAIR_RAIL_TIMEOUT_S default not found in check_pair_rail.py) — advisory only"
+      return 0 ;;
+  esac
+  if [ "$_prt_reg" -lt $((_prt_int + 30)) ]; then
+    _log ""
+    _log "    WARN: check_pair_rail.py registration timeout (${_prt_reg}s) < internal default (${_prt_int}s) + 30s margin —"
+    _log "          the harness can KILL the hook before the codex verdict lands (PLAN-164 hook-kill risk;"
+    _log "          the historical 12/12 pair_rail_case F/TIMEOUT class). Raise the settings.json registration"
+    _log "          timeout to >= $((_prt_int + 30))s (upgrade.sh migrates the old default 60 -> 150)."
+  elif [ "$VERBOSE" -eq 1 ]; then
+    _log "    OK (pair-rail timeouts): registration ${_prt_reg}s >= internal ${_prt_int}s + 30s margin"
+  fi
+  return 0
+}
+_pair_rail_timeout_check
+
+# ---------------------------------------------------------------------------
 # Summary + exit code
 # ---------------------------------------------------------------------------
 _log ""
```

### .claude/plans/PLAN-163/land-plan163-pin.sh
```diff
--- .claude/plans/PLAN-163/land-plan163-pin.sh	2026-07-28 17:44:00
+++ .claude/plans/PLAN-164/staged/rail-pack/.claude/plans/PLAN-163/land-plan163-pin.sh	2026-07-29 20:56:18
@@ -94,17 +94,37 @@
 # GATE-V2 — post-anchor fresh-liveness verdict (also called at end of apply)
 # =============================================================================
 resolve_anchor() {
-  # Prefer the recorded anchor file; fall back to the tagged commit in log.
-  local sha="" ts=""
+  # PLAN-164 C1 — fail-closed POINTER validation. The anchor file is only a
+  # pointer, never an authority: the sha it names must exist AND be a tagged
+  # ceremony commit ([SENT-PLAN163-PIN] or [SENT-PLAN164-RAIL]), and ts is
+  # ALWAYS recomputed from git (a ts= line in the file is IGNORED — a
+  # tampered/hand-edited ts can no longer widen or shrink the GATE-V2
+  # window). File present but invalid = die, NOT fallback. Fallback to
+  # `git log --grep` (newest tagged commit wins) only when the file is
+  # absent. Return interface unchanged: "sha<TAB>ts" on stdout.
+  local sha="" ts="" subject=""
   if [ -f "$ANCHOR_FILE" ]; then
     sha="$(sed -n 's/^sha=//p' "$ANCHOR_FILE" | head -1)"
-    ts="$(sed -n 's/^ts=//p' "$ANCHOR_FILE" | head -1)"
-  fi
-  if [ -z "$sha" ]; then
-    sha="$(git log --format='%H' --grep='\[SENT-PLAN163-PIN\]' -n 1 || true)"
-    [ -n "$sha" ] && ts="$(git log -1 --format='%cI' "$sha")"
+    [ -n "$sha" ] \
+      || die "anchor file $ANCHOR_FILE exists but carries no sha= line — repair it or remove it to fall back to git log"
+    git cat-file -e "${sha}^{commit}" 2>/dev/null \
+      || die "anchor sha $sha (from $ANCHOR_FILE) is not a commit in this repo — stale or tampered pointer"
+    subject="$(git log -1 --format='%s' "$sha")" \
+      || die "cannot read the subject of anchor commit $sha"
+    case "$subject" in
+      *"[SENT-PLAN163-PIN]"*|*"[SENT-PLAN164-RAIL]"*) : ;;
+      *) die "anchor sha $sha is not a ceremony commit — subject lacks [SENT-PLAN163-PIN]/[SENT-PLAN164-RAIL]: $subject" ;;
+    esac
+  else
+    sha="$(git log --format='%H' -E \
+      --grep='\[SENT-PLAN163-PIN\]|\[SENT-PLAN164-RAIL\]' -n 1 || true)"
+    [ -n "$sha" ] \
+      || die "no anchor: $ANCHOR_FILE absent and no [SENT-PLAN163-PIN]/[SENT-PLAN164-RAIL] commit in git log — run the ceremony first"
   fi
-  [ -n "$sha" ] && [ -n "$ts" ] || return 1
+  ts="$(git log -1 --format='%cI' "$sha")" \
+    || die "cannot recompute anchor ts for $sha (git log failed)"
+  [ -n "$ts" ] \
+    || die "recomputed anchor ts for $sha is empty — git metadata unreadable"
   printf '%s\t%s\n' "$sha" "$ts"
 }
 
@@ -274,6 +294,20 @@
 if [ "$GATE_V2_ONLY" = 1 ]; then
   gate_v2
   exit 0
+fi
+
+# =============================================================================
+# PLAN-164 C4-i — pin-pack retirement guard (apply + --dry-run ONLY)
+# =============================================================================
+# Once the PLAN-164 rail ceremony has landed, this pin-pack is superseded:
+# it stages check_pair_rail.py with the pre-PLAN-164 timeout default, so a
+# (re-)apply would silently revert the rail fix. The read-only modes stay
+# valid: --gate-v2 already exited above; --preflight-only is exempted here.
+if [ "$PREFLIGHT_ONLY" != 1 ]; then
+  _rail_sha="$(git log --format='%H' --grep='\[SENT-PLAN164-RAIL\]' -n 1 || true)"
+  if [ -n "$_rail_sha" ]; then
+    die "pin-pack superado pelo PLAN-164 (contém check_pair_rail.py com default antigo; re-apply reverteria o fix). Somente --gate-v2 / --preflight-only permanecem válidos."
+  fi
 fi
 
 # =============================================================================
```

### .claude/plans/PLAN-163/land-plan163-pack.sh
```diff
--- .claude/plans/PLAN-163/land-plan163-pack.sh	2026-07-28 17:57:35
+++ .claude/plans/PLAN-164/staged/rail-pack/.claude/plans/PLAN-163/land-plan163-pack.sh	2026-07-29 21:17:27
@@ -30,7 +30,7 @@
 #
 # COUNTS: this ceremony does NOT edit CLAUDE.md (cache discipline). It
 # VALIDATES the mechanical post-apply counts (hooks 55→57, wired 44→46,
-# registrations 46→48, ADRs 181→183) and PRINTS the closeout deltas; the
+# registrations 46→48, ADRs 182→184 — inclui ADR-110-AMEND-1 do PLAN-164) and PRINTS the closeout deltas; the
 # CLAUDE.md/docs closeout commit must land BEFORE push.
 #
 # Usage:
@@ -237,9 +237,9 @@
   || die "key $KEY absent from .claude/security/sentinel-signers-registry.yaml (rail 2, ADR-121)"
 echo "    both signer rails carry the ceremony key"
 
-say "ADR count pre-apply (pin landed → must be 181; pack makes it 183)"
+say "ADR count pre-apply (pin+PLAN-164 landed → must be 182; pack makes it 184)"
 _adr_now="$(ls .claude/adr/ADR-*.md | wc -l | tr -d ' ')"
-[ "$_adr_now" = "181" ] || die "pre-apply ADR count is $_adr_now, expected 181 (is GATE-PIN really landed?)"
+[ "$_adr_now" = "182" ] || die "pre-apply ADR count is $_adr_now, expected 182 (are GATE-PIN + [SENT-PLAN164-RAIL] really landed? PLAN-164 adds ADR-110-AMEND-1)"
 
 # =============================================================================
 # W2 oracles (live tree) — run BEFORE committing W2, and again in overlay
@@ -366,7 +366,7 @@
                 if tok.endswith(".py"):
                     scripts.add(tok.split("/")[-1])
 wired = len(scripts)
-expect = {"hooks_on_disk": 57, "wired": 46, "registrations": 48, "adrs": 183}
+expect = {"hooks_on_disk": 57, "wired": 46, "registrations": 48, "adrs": 184}
 got = {"hooks_on_disk": hooks_on_disk, "wired": wired,
        "registrations": regs, "adrs": adrs}
 ok = True
@@ -474,8 +474,8 @@
 python3 .claude/scripts/check-hook-stdout-schema.py --repo "$REPO" \
   > "$SCRATCH/post-3.log" 2>&1 || die "post-apply hook-stdout-schema RED ($SCRATCH/post-3.log)"
 _adr_post="$(ls .claude/adr/ADR-*.md | wc -l | tr -d ' ')"
-[ "$_adr_post" = "183" ] || die "post-apply ADR count is $_adr_post, expected 183"
-echo "    pytest + generate --check + stdout-schema + ADR-count(183) OK"
+[ "$_adr_post" = "184" ] || die "post-apply ADR count is $_adr_post, expected 184"
+echo "    pytest + generate --check + stdout-schema + ADR-count(184) OK"
 
 build_scope_re() {
   local re="" f esc
@@ -525,7 +525,7 @@
 oracles; smoke-install-parity fleet assert. T6: substrate-adopt-2026-08,
 CEO-MODEL-ROUTING, ACCELERATORS (fast mode = cost-latency trade-off, no
 speed numbers — AGENTS.md scrub). CLAUDE.md count triple (57/46/48 +
-ADRs 183) lands in the closeout commit before push (cache discipline).
+ADRs 184) lands in the closeout commit before push (cache discipline).
 
 Co-Authored-By: Claude Fable 5 <noreply@anthropic.com>
 MSG
@@ -537,7 +537,7 @@
 cat <<'EOF'
   1. Closeout commit — count surfaces (tolerance=0 in CI):
      - CLAUDE.md triple: hooks on disk 55->57, wired 44->46,
-       registrations 46->48; ADRs 180->183; skills/commands unchanged.
+       registrations 46->48; ADRs 182->184; skills/commands unchanged.
      - team.md :578/:589 model drift (T1.6, cache-stable file).
      - Regenerate COMMAND-SKILL-HOOK-MAP (gen---write) if hook surfaces
        feed it; sweep unwatched docs (ARCHITECTURE/GUIA-COMPLETO/FAQ/
```

## B. Rail-pack: arquivos NOVOS (conteúdo integral)

### .claude/plans/PLAN-164/staged/rail-pack/.claude/adr/ADR-110-AMEND-1-rail-timeout-contract.md
```
# ADR-110-AMEND-1 — Pair-rail timeout contract (30 s default retired)

---
adr_id: ADR-110-AMEND-1
title: Pair-rail timeout contract — internal default 30→120 s, harness registration 60→150 s, invariant under test
status: ACCEPTED
amends: ADR-110
proposed_at: 2026-07-29
proposed_by: CEO (PLAN-164, GATE-V2 fresh-probe FAIL diagnosis)
session_origin: 2026-07-29 (post-S284; probe session 6de4f28e)
accepted_at: 2026-07-29
authorization: PLAN-164 W2 Owner-GPG ceremony commit tagged [SENT-PLAN164-RAIL] — this file reaches the canonical tree ONLY via that ceremony; a landed copy implies the gate fired
risk_tier: A
debate_required: true
debate_record: .claude/plans/PLAN-164/debate/round-1/consensus.md (3x ADJUST -> PROCEED; OQ1=120 / OQ2=150 ratified by Owner tie-break 2026-07-29)
related_plans: [PLAN-075, PLAN-081, PLAN-163, PLAN-164]
related_adrs: [ADR-106, ADR-110, ADR-182]
---

## §1 What this amendment changes

ADR-110 established the PreToolUse block mechanism for the pair-rail
(`check_pair_rail.py`). It never fixed an operative *timeout contract* — the
30 s internal default was an implementation literal, not a decided value.
Measurement (§2) shows 30 s is structurally below the latency of a real
Codex verdict, which made the rail 100% fail-open in production (12/12
`pair_rail_case` events in the entire life of the audit log are case F /
TIMEOUT — the rail NEVER completed a live in-hook review). This amendment
promotes the timeout pair to a decided, tested contract:

1. **Internal default `CEO_PAIR_RAIL_TIMEOUT_S`: 30 → 120.** Three literals
   in `check_pair_rail.py`: the env-read default string `"30"` → `"120"`
   (`os.environ.get("CEO_PAIR_RAIL_TIMEOUT_S", ...)`, ~L1717), the
   parse-error fallback float `30.0` → `120.0`, and the clamp-reset float
   `30.0` → `120.0` (plus the docstring at ~L51-52). Clamp bound `>600`
   unchanged.
2. **Harness registration timeout: 60 → 150** for the `check_pair_rail.py`
   PreToolUse entry in kernel `.claude/settings.json` AND template
   `templates/settings/settings.base.json` (parity enforced). Precedent for
   a >120 s registration already exists in the kernel:
   `codex_review_user_code.py` runs at `timeout: 130`.
3. **The layering invariant is now TESTED, not assumed**
   (`test_pair_rail_timeout_invariant.py`): parses `settings.json`,
   `settings.base.json`, and the hook's default literal, and asserts
   (a) kernel registration == template registration, and
   (b) `registration >= internal + 30` (absolute margin covering Python
   startup + redaction + verdict validation + observed load variance).
   A unilateral flip of any of the three literals goes red in the suite and
   in the pack-preflight overlay.
4. **`statusMessage` added to the registration** (kernel + template + the
   frozen-pack staged copies; e.g. "Pair-rail cross-model review — may take
   1-2 min"), so a session held by a synchronous review shows feedback
   instead of appearing frozen.

## §2 Evidence — measured, not inferred

Root-cause probe (2026-07-29, GATE-V2 fresh probe, anchor `a4371c7`;
diagnosis at `.claude/plans/PLAN-163/probes/GATE-V2-2026-07-29-FAIL-diagnosis.md`):
`codex exec` startup overhead is ~8 s and a realistic review prompt under
`reasoning effort: xhigh` returns in ~36 s — always >30 s.

Calibration dataset (consensus C5 protocol, EXECUTED in-debate, N=9, same
machine, verbatim):

| Condition | Latencies (s) |
|---|---|
| small prompt, idle machine | 25.8 / 33.3 / 34.9 / 36.3 / 38.8 / 68.8 |
| big prompt (15.4 KB), idle | 58.4 / 51.3 |
| small prompt, UNDER LOAD (test suite in parallel) | 75.1 |

p95 ≈ 75 s **> 70 s escalation threshold** of the measurement protocol
(consensus C5 / Critic-C MF5) → the protocol's own escalation rule selects
**internal 120 / registration 150** (not the 100/120 first draft).
150 − 120 = 30 s absolute margin. History: 12/12 `pair_rail_case` = F
(TIMEOUT); the 11 case-F events in the 168 h window pre-dating PLAN-163's
pin were latency, not integrity — ADR-182's pin fixed payload integrity and
could not have fixed this.

## §3 Recalibration trigger

After **≥10 healthy cases** (case A–E) accumulate post-uplift, the p95 of
verdict latency — `pair_rail_case.ts − pair_rail_review_expected.ts`, joined
on `(session_id, review_id)` — is recomputed from the audit log and the
120/150 pair is revisited (downward if p95 leaves generous headroom, upward
escalation if p95 approaches the internal budget). Any change is a new
amendment via ceremony, not a literal edit.

Documented query (stdlib-only; field names per the audit-log schema as
consumed by `land-plan163-pin.sh --gate-v2`: `action`, `ts`/`timestamp`,
`review_id`, `session_id`, `case`):

```python
import json, statistics
from datetime import datetime, timezone

def _dt(ts):
    d = datetime.fromisoformat(str(ts).replace("Z", "+00:00"))
    return d if d.tzinfo else d.replace(tzinfo=timezone.utc)

expected, lat = {}, []
for line in open(LOG, encoding="utf-8", errors="replace"):
    line = line.strip()
    if not line:
        continue
    try:
        ev = json.loads(line)
    except json.JSONDecodeError:
        continue
    key = (str(ev.get("session_id") or ""), str(ev.get("review_id") or ""))
    ts = ev.get("ts") or ev.get("timestamp")
    if not key[1] or not ts:
        continue
    if ev.get("action") == "pair_rail_review_expected":
        expected[key] = _dt(ts)
    elif (ev.get("action") == "pair_rail_case"
          and ev.get("case") in ("A", "B", "C", "D", "E")
          and key in expected):
        lat.append((_dt(ts) - expected.pop(key)).total_seconds())
if len(lat) >= 10:
    print("n=%d p95=%.1fs" % (len(lat), statistics.quantiles(lat, n=20)[18]))
else:
    print("n=%d — trigger not met (need >=10 healthy cases)" % len(lat))
```

(`jq -r 'select(.action=="pair_rail_case") | [.ts,.case,.review_id] | @tsv'`
is fine for eyeballing, but the join on `(session_id, review_id)` makes the
Python form normative.)

## §4 Named residuals (accepted, on the record)

- **(i) Env-knob sub-floor = universal fail-open.** Any session exporting
  `CEO_PAIR_RAIL_TIMEOUT_S` below real verdict latency re-creates 100%
  case-F fail-open by env alone. ACCEPTED because env-control over the
  session is already a high privilege (superset of this threat) and every
  such miss is auditable as a case-F event in the HMAC chain. A minimum
  floor on the knob (e.g. `<10 → default`) was DEFERRED — changing the
  semantics of a documented knob is a new contract (consensus
  rejected/deferred item 2).
- **(ii) Clamp overflow semantics — known wart.** A value `>600` or a
  parse error does not clamp-to-bound: it RESETS to the default (now 120).
  An operator setting `9999` silently gets 120, not 600. Documented here as
  a known wart; clamp-to-bound was a nice-to-have only if it fit the same
  diff (consensus deferred item 3).
- **(iii) The next hidden "default 30".** `check_codex_filewrite.py`'s
  registration runs at `timeout: 30` (kernel settings). Safe today (that
  hook does not hold a synchronous Codex verdict), but IF the live review
  path ever migrates to MCP dispatch through it, it becomes the same class
  of structurally-sub-latency default this amendment retires. Out of scope
  here; named so the migration reviewer trips over it.

## §5 Alternatives rejected

- **(a) Asynchronous post-facto review** (let the edit land, review after).
  REJECTED: the rail's entire value is the PRE-write veto — cases B/C
  REJECT block the write before it exists (ADR-110's reason to be). An
  async lane already exists (`stop_review`); duplicating it here would
  retire the only pre-write cross-model gate.
- **(b) Per-invocation reasoning-effort downgrade** (drop Codex below
  `xhigh` inside the hook to fit 30 s). REJECTED: verdict quality at lower
  effort is non-validated for this rail, and effort is deliberately
  external config (the harness pin, ADR-182) — the hook silently overriding
  it would be a second, hidden config surface.

## §6 Declared cost

- A canonical, non-sentineled edit that triggers a live review now holds
  the session synchronously for up to ~120 s. Mitigated by `statusMessage`
  (§1.4); the hold also pushes heavy canonical work toward staged
  copies + ceremony — which is the desired flow, not a regression.
- Reviews that actually COMPLETE are recurring Codex spend the 30 s-timeout
  era never paid (every prior invocation died before billing a verdict).
  Tracked in the finops lane.

## §7 Semantics of the re-anchored GATE-V2

The audit log is append-only (HMAC chain): the 2026-07-29 case-F probe is
permanent in the post-`a4371c7` set, so `failopen==0` is unsatisfiable
against the old anchor. The PLAN-164 ceremony re-anchors at the
`[SENT-PLAN164-RAIL]` commit. A GATE-V2 PASS against the new anchor proves
**"liveness under ADR-182 pin + new timeout contract"** — strictly STRONGER
than the original claim, since the payload pin and verify-then-invoke path
are untouched by this amendment (the frozen PLAN-163 packs contain no
staged copy of ADR-110, so this amendment survives the pack apply and does
not disturb the double-APPROVEd byte set).
```

### .claude/plans/PLAN-164/staged/rail-pack/.claude/hooks/tests/test_pair_rail_timeout_invariant.py
```
"""PLAN-164 W1 — pair-rail timeout cross-layer invariant (consensus C2).

Root cause being closed (measured, not inferred — see
`.claude/plans/PLAN-163/probes/GATE-V2-2026-07-29-FAIL-diagnosis.md` and
`.claude/plans/PLAN-164/debate/round-1/consensus.md`): the hook-internal
default `CEO_PAIR_RAIL_TIMEOUT_S=30s` sits BELOW the real codex verdict
latency (N=9 probe: p95 ~75s), so 12/12 historical `pair_rail_case`
events were F/TIMEOUT. The ratified fix is layered: internal default
120s, harness registration timeout 150s, with an invariant margin of
>= 30s between the layers so the harness never kills the hook before the
hook's own subprocess cap fires, plus a `statusMessage` on the
registration so the operator sees WHY a canonical edit stalls.

This test pins the INVARIANT BETWEEN LAYERS, not just the literals:

  1. kernel registration timeout (`.claude/settings.json`) equals the
     template registration timeout
     (`templates/settings/settings.base.json`) — the S283/S275 derived-
     surface-drift class;
  2. each registration timeout >= hook-internal default + 30s margin;
  3. `statusMessage` is present on the pair-rail registration in BOTH
     files.

RED-FIRST contract (staged with the rail-pack): against the pre-pack
live tree — registration timeout 60, internal default "30", NO
statusMessage — assertion (3) FAILS in both files ((1) and (2) are
vacuously green at 60/60/30: 60 >= 30+30). The test goes fully green
only after the rail-pack applies (overlay-clone verification proves it),
and from then on any future drift that shrinks the margin or splits
kernel from template goes red.

Repo-root resolution walks parents of ``__file__`` until it finds a
COMPLETE tree (settings.json + template + hook), so the same file works
from the staged path (resolves the live repo), from an overlay clone,
and from its final home at `.claude/hooks/tests/`.

stdlib-only (json, re, pathlib, unittest). Python >= 3.9.
"""

from __future__ import annotations

import json
import re
import sys
import unittest
from pathlib import Path
from typing import Dict, List, Tuple


def _resolve_repo_root() -> Path:
    """First parent of this file that holds the full trio of artifacts.

    Requiring all three (not just `.claude/settings.json`) means a
    PARTIAL staged subtree between this file and the real root can
    never be mistaken for the repo — the walk keeps climbing until it
    reaches a tree where every extraction target exists.
    """
    here = Path(__file__).resolve()
    for parent in here.parents:
        if (
            (parent / ".claude" / "settings.json").is_file()
            and (parent / "templates" / "settings" / "settings.base.json").is_file()
            and (parent / ".claude" / "hooks" / "check_pair_rail.py").is_file()
        ):
            return parent
    raise RuntimeError(
        "test_pair_rail_timeout_invariant: no parent of __file__ contains "
        ".claude/settings.json + templates/settings/settings.base.json + "
        ".claude/hooks/check_pair_rail.py — cannot locate a complete repo root"
    )


_REPO_ROOT = _resolve_repo_root()
_HOOKS_DIR = _REPO_ROOT / ".claude" / "hooks"
if str(_HOOKS_DIR) not in sys.path:
    sys.path.insert(0, str(_HOOKS_DIR))

from _lib.testing import TestEnvContext  # noqa: E402

_KERNEL_SETTINGS = _REPO_ROOT / ".claude" / "settings.json"
_TEMPLATE_SETTINGS = _REPO_ROOT / "templates" / "settings" / "settings.base.json"
_HOOK_SOURCE = _HOOKS_DIR / "check_pair_rail.py"

# Ratified invariant floor (PLAN-164 debate round-1 consensus C2): the
# harness registration must outlive the hook's own subprocess cap by at
# least this many seconds, so the hook — not the harness — owns the
# timeout arm (case F stays diagnosable instead of a silent hook kill).
_MARGIN_S = 30

# The exact seam in check_pair_rail.py that defines the internal default
# (single source: `float(os.environ.get("CEO_PAIR_RAIL_TIMEOUT_S", "<N>"))`).
_INTERNAL_DEFAULT_RE = re.compile(
    r'os\.environ\.get\("CEO_PAIR_RAIL_TIMEOUT_S",\s*"(\d+)"\)'
)


def _extract_internal_default_s(hook_source: Path) -> int:
    matches = _INTERNAL_DEFAULT_RE.findall(
        hook_source.read_text(encoding="utf-8")
    )
    if len(matches) != 1:
        raise AssertionError(
            "expected exactly ONE CEO_PAIR_RAIL_TIMEOUT_S default seam in "
            "%s, found %d — the extraction regex must track the hook"
            % (hook_source, len(matches))
        )
    return int(matches[0])


def _pair_rail_registrations(settings_path: Path) -> List[Tuple[str, Dict]]:
    """Every hook dict in `settings_path` whose command runs check_pair_rail.py."""
    data = json.loads(settings_path.read_text(encoding="utf-8"))
    found: List[Tuple[str, Dict]] = []
    for event, entries in (data.get("hooks") or {}).items():
        for entry in entries or []:
            for hook in entry.get("hooks") or []:
                if "check_pair_rail.py" in str(hook.get("command", "")):
                    found.append((event, hook))
    return found


def _sole_registration(settings_path: Path) -> Dict:
    regs = _pair_rail_registrations(settings_path)
    if len(regs) != 1:
        raise AssertionError(
            "expected exactly ONE check_pair_rail.py registration in %s, "
            "found %d" % (settings_path, len(regs))
        )
    return regs[0][1]


class TestPairRailTimeoutInvariant(TestEnvContext):
    """C2: kernel==template, registration >= internal+30s, statusMessage."""

    def setUp(self) -> None:
        super().setUp()
        self.kernel_hook = _sole_registration(_KERNEL_SETTINGS)
        self.template_hook = _sole_registration(_TEMPLATE_SETTINGS)
        self.internal_default_s = _extract_internal_default_s(_HOOK_SOURCE)

    # -- extraction sanity -------------------------------------------------

    def _registration_timeout(self, hook: Dict, origin: str) -> float:
        timeout = hook.get("timeout")
        self.assertIsInstance(
            timeout,
            (int, float),
            "pair-rail registration in %s has no numeric 'timeout' field "
            "(got %r) — the harness would fall back to its global default "
            "and the layered-timeout contract is unpinned" % (origin, timeout),
        )
        return float(timeout)

    # -- invariant 1: kernel == template (derived-surface drift class) -----

    def test_kernel_registration_timeout_equals_template(self) -> None:
        kernel_s = self._registration_timeout(self.kernel_hook, "kernel")
        template_s = self._registration_timeout(self.template_hook, "template")
        self.assertEqual(
            kernel_s,
            template_s,
            "pair-rail registration timeout drifted between the dogfood "
            "kernel (.claude/settings.json: %r) and the adopter template "
            "(templates/settings/settings.base.json: %r) — fix BOTH "
            "surfaces in the same change" % (kernel_s, template_s),
        )

    # -- invariant 2: registration >= internal default + margin ------------

    def test_registration_outlives_internal_default_by_margin(self) -> None:
        for origin, hook in (
            ("kernel", self.kernel_hook),
            ("template", self.template_hook),
        ):
            registration_s = self._registration_timeout(hook, origin)
            floor_s = self.internal_default_s + _MARGIN_S
            self.assertGreaterEqual(
                registration_s,
                floor_s,
                "%s registration timeout (%ss) < hook-internal default "
                "(%ss) + %ss margin: the harness would kill the hook "
                "BEFORE the hook's own codex subprocess cap fires, turning "
                "every slow verdict into an undiagnosable hook kill instead "
                "of a case-F TIMEOUT" % (
                    origin,
                    registration_s,
                    self.internal_default_s,
                    _MARGIN_S,
                ),
            )

    # -- invariant 3: statusMessage present in BOTH registrations ----------

    def test_status_message_present_in_both_registrations(self) -> None:
        for origin, hook in (
            ("kernel .claude/settings.json", self.kernel_hook),
            ("template settings.base.json", self.template_hook),
        ):
            status = hook.get("statusMessage")
            self.assertIsInstance(
                status,
                str,
                "pair-rail registration in %s has no 'statusMessage' — a "
                "120s+ canonical-edit stall must tell the operator the "
                "pair-rail review is running, not look like a hang "
                "(got %r)" % (origin, status),
            )
            self.assertTrue(
                status.strip(),
                "pair-rail registration statusMessage in %s is empty"
                % origin,
            )


if __name__ == "__main__":
    unittest.main()
```

## C. Pack congelado PLAN-163: delta R6 -> synced (4 arquivos)

Baseline R6 tracked: .claude/plans/PLAN-163/inputs-pack.sha256 (commit 341ffc3). O upgrade.sh R6 original está preservado no scratchpad do fix agent; o diff abaixo usa git para os 3 JSON/py? NÃO — staged é gitignored. Diffs gerados contra cópias R6 indisponíveis => para settings/test os diffs equivalem aos do kernel (mesmo delta cirúrgico); upgrade.sh diff:

### scripts/upgrade.sh (R6 -> synced)
```diff
--- /private/tmp/claude-501/-Users-joaocanhada-canhada-labs-ceo-orchestration/6de4f28e-76c1-4d2b-a743-59cf8bec593f/scratchpad/fix-crosspack/upgrade.sh.R6	2026-07-29 21:20:57
+++ .claude/plans/PLAN-163/staged/main-pack/scripts/upgrade.sh	2026-07-29 21:21:55
@@ -66,6 +66,13 @@
 #     preserved. Opt out with --no-settings-migrate. Oracles derive their
 #     expectations from `upgrade.sh --print-settings-baselines` (the
 #     normative table IS the artifact — literals are never re-hardcoded).
+#   - (PLAN-164 W1, ADR-110-AMEND-1) PAIR-RAIL REGISTRATION-TIMEOUT VALUE
+#     MIGRATION: the check_pair_rail.py PreToolUse registration timeout is
+#     bumped from the frozen OLD cap (60) to the template-derived cap IFF the
+#     adopter's current value == 60; any other adopter-chosen value is
+#     PRESERVED + a named WARNING; idempotent. Runs inside the same T5.4
+#     migration step (same opt-out, same --dry-run preview); the NEW cap is
+#     derived from templates/settings/settings.base.json, never hardcoded.
 #
 # Run after `git pull` in the source ceo-orchestration repo.
 
@@ -1724,6 +1731,12 @@
 # not yet registered AND the T3.4 version-floor feature gate is on
 # (_t34_new_event_registrations_enabled). Customized registrations under the
 # same events — and every other hooks entry/settings key — stay untouched.
+# PLAN-164 W1 (ADR-110-AMEND-1): the check_pair_rail.py PreToolUse
+# registration TIMEOUT VALUE migrates under the same 3-state policy — the
+# frozen OLD cap (60) -> the cap DERIVED from the template artifact
+# (templates/settings/settings.base.json pair-rail entry; install.sh copies
+# it verbatim, so template value == post-install value == migration target);
+# any other adopter-chosen value is PRESERVED + named WARNING; idempotent.
 # The file is rewritten ONLY when at least one key actually changed (atomic
 # same-directory tempfile + os.replace), so running the upgrade twice is
 # byte-identical (idempotency oracle). Fail-open per CLAUDE.md §4: missing
@@ -1748,6 +1761,9 @@
 
   local _mig_mode="apply"
   local _mig_gate="0"
+  # PLAN-164 W1: the pair-rail registration-timeout migration target is
+  # DERIVED from the source template artifact (see the helper below).
+  local _mig_template="$SOURCE_DIR/templates/settings/settings.base.json"
   if [[ "$DRY_RUN" -eq 1 ]]; then
     _mig_mode="preview"
   fi
@@ -1958,7 +1974,74 @@
             else:
                 warn("WARNING: hooks." + event + " is not a list - PRESERVED "
                      "(canonical registration not added)")
+
+# --- PLAN-164 W1 (ADR-110-AMEND-1) — pair-rail registration-timeout VALUE
+# --- migration. WHY: the harness kills a hook at its settings.json
+# --- registration timeout, and the pre-PLAN-164 cap (60s) sat BELOW the
+# --- measured codex verdict latency (p95 ~75s under load; 12/12 historical
+# --- pair_rail_case rows were F/TIMEOUT — PLAN-163/probes/
+# --- GATE-V2-2026-07-29-FAIL-diagnosis.md). Ratified semantics (OQ2=150):
+# --- bump the check_pair_rail.py PreToolUse registration timeout IFF the
+# --- current value == the OLD cap; ANY other adopter-chosen value is
+# --- PRESERVED (named WARN); already-at-target is a no-op; an entry with NO
+# --- timeout key is left untouched (harness default, not an adopter choice
+# --- of the old cap). The NEW cap is DERIVED from the template artifact
+# --- (settings.base.json pair-rail entry — install.sh copies it verbatim,
+# --- so template value == post-install value == migration target); the OLD
+# --- cap is a frozen historical literal (it no longer exists in any live
+# --- artifact once this migration lands), exactly like the "old" column of
+# --- the T5.4 table above. Fail-open: an unreadable template or a
+# --- non-unique/non-int template cap skips ONLY this leaf (stderr NOTE) —
+# --- the rest of the migration is unaffected.
+OLD_PAIR_RAIL_CAP = 60  # frozen pre-PLAN-164 registration cap (never derived)
+template_path = sys.argv[5]
 
+
+def pair_rail_hooks(obj):
+    found = []
+    hooks_obj = obj.get("hooks")
+    blocks = hooks_obj.get("PreToolUse") if isinstance(hooks_obj, dict) else None
+    for block in blocks if isinstance(blocks, list) else []:
+        if not isinstance(block, dict):
+            continue
+        hs = block.get("hooks")
+        if not isinstance(hs, list):
+            continue
+        for h in hs:
+            if isinstance(h, dict) and \
+                    "check_pair_rail.py" in str(h.get("command", "")):
+                found.append(h)
+    return found
+
+
+new_cap = None
+try:
+    with open(template_path, "r", encoding="utf-8") as f:
+        tpl_caps = [h.get("timeout") for h in pair_rail_hooks(json.load(f))]
+    if len(tpl_caps) == 1 and type(tpl_caps[0]) is int:
+        new_cap = tpl_caps[0]
+except (OSError, ValueError):
+    new_cap = None
+if new_cap is None:
+    warn("NOTE: pair-rail registration-timeout migration skipped - template "
+         "pair-rail cap not derivable (advisory only; other keys unaffected)")
+else:
+    for h in pair_rail_hooks(data):
+        cur = h.get("timeout", MISSING)
+        if cur is MISSING:
+            continue
+        if cur == new_cap:
+            out("OK (already at template cap): pair-rail registration timeout")
+        elif cur == OLD_PAIR_RAIL_CAP:
+            if not dry:
+                h["timeout"] = new_cap
+            changed[0] = True
+            act("MIGRATE (matched OLD pair-rail cap -> template cap): "
+                "hooks.PreToolUse[check_pair_rail.py].timeout")
+        else:
+            warn("WARNING: pair-rail registration timeout is "
+                 "ADOPTER-CUSTOMIZED - PRESERVED (not migrated)")
+
 if dry:
     sys.exit(0)
 if not changed[0]:
@@ -1979,7 +2062,7 @@
         pass
     sys.exit(3)
 out("WROTE: .claude/settings.json (atomic; only migrated leaf keys changed)")
-' "$_mig_mode" "$settings" "$_T54_BASELINES_JSON" "$_mig_gate"; then
+' "$_mig_mode" "$settings" "$_T54_BASELINES_JSON" "$_mig_gate" "$_mig_template"; then
     # NAMED skip (not a silent one): the helper exits 3 on an unparseable /
     # unreadable settings.json (json.load failed) OR on an atomic-write
     # failure. Either way the leaf keys were NOT migrated. Preservation is
```
