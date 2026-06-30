# ADR-087-AMEND-1 — OTel consume-native opt-in profile (the dashboard, not the truth)

---
adr_id: ADR-087-AMEND-1
title: OTel consume-native opt-in — local stdlib sink + native Claude Code telemetry as the dashboard; audit-log stays canonical truth
status: PROPOSED
amends: ADR-087
proposed_at: 2026-06-13
proposed_by: CEO (PLAN-135 W5, UNIT o10 — "who watches the hooks")
session_origin: S230/plan-135-exec
authorization: PENDING — debate R1 (plan §W5 "O10 OTEL needs its own ADR") + Codex pair-rail + Owner-GPG sentinel on this canonical copy
risk_tier: B
debate_required: true
related_plans: [PLAN-135, PLAN-056, PLAN-011]
related_adrs: [ADR-087, ADR-035, ADR-055, ADR-002, ADR-005, ADR-149]
---

## §1 What this amends, and what it does NOT

ADR-087 (ACCEPTED 2026-04-27) **REFUSED** PLAN-056 Phase 5's proposal to
have the framework **EMIT** OpenTelemetry spans *alongside* every
`audit-log.jsonl` write, with reason `(b) cost-exceeds-benefit`. Its
Decision items 1-3 — "no OTel SDK dependency", "no span-emission
alongside audit-log writes", "reaffirm audit-log.jsonl as canonical
observability" — **all stand unchanged.**

This amendment adjudicates the *different* question that ADR-087's own
Neutral consequence explicitly anticipated:

> "Future Anthropic or Claude Code harness updates that emit OTel
> natively may make this ADR obsolete. Mitigation: ADRs revisable."
> — ADR-087 §Consequences.Neutral

Claude Code now ships native OpenTelemetry emission (opt-in via
`CLAUDE_CODE_ENABLE_TELEMETRY=1` + `OTEL_*` exporter knobs). The harness
emits the spans/metrics/logs; the framework does not author a single
emit call. This is **consume-native, not emit-native** — categorically
outside ADR-087's `(b) cost-exceeds-benefit` refusal (which costed
*authoring* a parallel emit surface across every emitter). Consuming a
stream the harness already produces costs one local receiver script.

**This amendment ADDS an opt-in consume path. It RETIRES nothing, makes
nothing default-on, and does not weaken ADR-087's emit refusal.**

## §2 Decision

**ADOPT-CONFINED (opt-in, local-only, no egress).**

1. **Opt-in profile** ships as `templates/settings/settings.stack.otel.json`
   — installed ONLY via `install.sh --stack otel` (turbo-style opt-in,
   like `--stack node` / `--stack sandbox`). **Registered by NOTHING by
   default.** Off ⇒ Claude Code emits nothing; the sink receives nothing.
   `CLAUDE_CODE_ENABLE_TELEMETRY` (unset by default) is the kill-switch —
   no separate `CEO_*` disable is needed.

2. **Local stdlib sink** (`.claude/scripts/otel-local-sink.py`):
   a loopback-bind-ONLY OTLP/HTTP receiver that writes received signals
   to `<state-dir>/otel-sink.jsonl`. It opens NO outbound socket
   (imports no HTTP client — `urllib.request` / `requests` / `httpx` /
   raw `socket` are NOT imported), refuses any non-loopback bind host
   (exit 2 before the socket opens), and is stdlib-only (ADR-002 — no
   `opentelemetry`, no `protobuf`). **No egress.** This is the receive
   counterpart to ADR-035's `otel-export.py` (which *sends* OUT with a
   6-mitigation HTTPS allowlist bundle); they do not overlap.

3. **Attribution carried by the harness, not reconstructed:**
   `cost.usage` / `token.usage` with `agent.name` / `skill.name`
   attribution arrive natively — the same attribution
   `measure_multiplier` reconstructs post-hoc from audit JSONL *with
   documented hazards* (cache-TTL aliasing, subagent accounting — the
   S229 four-VOID class). `OTEL_RESOURCE_ATTRIBUTES` stamps
   `plan.id` / `wave` / `archetype` onto every signal.

4. **The rail-tamper witness (the load-bearing security value).**
   `OTEL_LOGS_EXPORTER` emits Claude-Code-native `hook_execution`-class
   log events. These are an **independent channel** attesting that the
   hook rail actually fired — *who watches the hooks*. A hook that is
   silently disarmed emits NO `audit-log.jsonl` event (because the
   disarmed hook is exactly the thing that would have written it), but
   the harness's OTel log records the `hook_execution` attempt/absence.
   An external diff of that stream against the registered-hook set
   surfaces the disarm. This **would have caught both real silent-hook
   incidents**: the S228 exec-bit-stripped hook and the S217
   settings-merge-skipped hook. It is the **named compensator** for the
   coverage boundary that THREAT-MODEL-WORKSHEET §2 (H2 / ConfigChange)
   records as honest residual:

   > "H2 is itself a hook (disarmed by the key it polices; blind to
   > outside-harness edits) — compensators: S3 boot tripwires (advisory,
   > fires next boot) + **O10 OTEL hook-execution witness (independent
   > channel)**. Until O10 lands (cut-2 risk), a same-session disarm
   > window exists." — THREAT-MODEL-WORKSHEET.md §2 Residual

   This amendment lands O10's witness channel, closing that cut-2 risk
   in the opt-in posture.

## §3 Positioning (verbatim, normative)

> audit-log = tamper-evident truth; OTel = dashboard.

The HMAC-chained, fail-closed-on-security `audit-log.jsonl` remains the
**canonical governance record** — ADR-087 Decision item 3 is reaffirmed,
not amended. The OTel sink is the **dashboard / panel**: a convenient,
queryable, *lossy* mirror. It is NEVER read by a governance hook as a
decision input (same trust tier as other local dashboard state — cf. the
PLAN-135 §W5 sidecar residual). If any future consumer ever gates a
decision on `otel-sink.jsonl`, that requires a NEW ADR; this one
explicitly does not authorize it.

The two streams are *independent by construction*, which is the entire
point of §2.4: the audit log can be corrupted/silenced by a disarmed
hook; the harness-native OTel stream cannot be (it is produced by the
runtime, outside the framework's emit surface). Two independent evidence
streams beat one — the same doctrine as the §1-GOVERNANCE-MAP "two
independent ledgers" note.

## §4 Why ADR-087's refusal grounds do NOT bind the consume path

| ADR-087 ground | Applies to consume-native? |
|---|---|
| "(b) cost-exceeds-benefit" — authoring a parallel emit surface across every emitter (~1-2 dev-días, doubles emit surface) | **NO.** The harness emits; we author zero emit calls. One receiver script + one opt-in fragment. |
| "No OTel SDK dependency" (Decision 1) | **HONORED.** The sink is stdlib-only (ADR-002); no `opentelemetry`, no `protobuf`. |
| "No span-emission alongside audit-log writes" (Decision 2) | **HONORED.** The framework still emits zero spans. Claude Code emits; we only receive. |
| "Reaffirm audit-log.jsonl as canonical" (Decision 3) | **REAFFIRMED.** §3 above; the sink is explicitly non-canonical dashboard state. |

## §5 Reconciliation with ADR-035 (export exists) and ADR-087 (emit refused)

- **ADR-035** ships the OUTBOUND exporter (`otel-export.py` + `_lib/otel_emit.py`)
  with a 6-mitigation HTTPS-only allowlist bundle. That is the
  *send-to-cloud* path, Owner-invoked, separately gated by
  `CEO_OTEL_ALLOWED_HOSTS` (fail-closed empty default). This amendment
  does NOT touch it and does NOT route the sink to any cloud backend.
- **ADR-087** refuses *framework-authored emit*. Unchanged.
- **This amendment** adds the INBOUND local sink for *harness-authored*
  telemetry. The three are orthogonal: ADR-035 = framework→cloud (opt-in,
  redacted); ADR-087 = framework emits nothing of its own (standing);
  ADR-087-AMEND-1 = harness→local-sink (opt-in, no egress).

## §6 Confinement (load-bearing invariants — refutable, not aspirational)

ADOPT-CONFINED holds only while ALL of the following remain true. ANY
breach is a P0:

1. **Loopback-only bind.** The sink binds `127.0.0.1`/`::1` and refuses
   every other host. There is no flag to bind a public interface. A
   `--host 0.0.0.0` exits 2 before any socket opens.
2. **No egress.** The sink imports no outbound HTTP client and opens no
   outbound socket. It is receive-only.
3. **Off by default.** No default install registers the fragment; absent
   `CLAUDE_CODE_ENABLE_TELEMETRY=1`, nothing emits and nothing receives.
4. **Non-canonical.** `otel-sink.jsonl` is dashboard state, never a hook
   decision input. The audit log stays the single tamper-evident source
   of truth.
5. **Endpoint stays loopback.** The opt-in fragment's
   `OTEL_EXPORTER_OTLP_ENDPOINT` points at `http://127.0.0.1:4318` and
   MUST NOT be repointed at a non-loopback host in this fragment;
   cloud export is ADR-035's separately-mitigated path, not this one.

## §7 Consequences

### Positive
- The H2/ConfigChange same-session-disarm residual gains its named
  independent compensator (the rail-tamper witness) in the opt-in posture.
- Native `cost.usage`/`token.usage` attribution sidesteps the
  measure_multiplier reconstruction hazards (cache-TTL, subagent
  accounting) for adopters who opt in.
- Zero new dependency, zero egress, zero default-on surface — the
  cheapest possible reconciliation of ADR-087's standing refusal with
  the now-available native stream.

### Negative
- The sink is a *lossy* mirror (OTel batches can drop; the JSONL is not
  HMAC-chained). This is by design — it is the dashboard, not the truth.
  Mitigated: the audit log remains canonical; nothing gates on the sink.
- The rail-tamper witness only fires when the Owner has opted in and the
  sink is running. It is a compensator for the *opt-in* posture, not an
  always-on guarantee. The S3 boot tripwire (advisory, next boot) remains
  the default-posture compensator; this is the stronger same-session one
  for opted-in sessions.

### Neutral
- Existing audit-log machinery (`audit_emit.py`, HMAC chain) unchanged.
- The ADR-035 exporter and `otel-smoke.yml` are unchanged.

## §8 Residual

- A local loopback JSON file read by a dashboard is the same trust tier
  as other local state (an attacker with local FS write could forge sink
  lines). Accepted: nothing gates on it (§3); the audit log is the
  integrity-bearing record.
- The witness depends on the harness faithfully emitting `hook_execution`
  logs. A harness bug that drops those logs would blind the witness — but
  that is a strictly-better posture than today (no independent channel at
  all), and the S3 tripwire still fires at next boot.

## §9 Promotion gates (ADR-126 Tier-B doctrine class)

- Wave-A debate R1, 0 VETO (plan §W5: "O10 OTEL needs its own ADR").
- Codex pair-rail ≥R2 ACCEPT.
- Owner-GPG sentinel on this canonical
  `.claude/adr/ADR-087-AMEND-1-otel-consume-native-opt-in.md` copy +
  ADR index regen.

Until all three land, this amendment stays **PROPOSED**.

## References

- ADR-087 — OTel emit REFUSED (the parent; emit refusal stands).
- ADR-035 — OTLP/HTTP export with defense-in-depth (the OUTBOUND path).
- ADR-002 — hooks package layout, stdlib-only.
- ADR-005 — fail-open contract.
- THREAT-MODEL-WORKSHEET.md §2 — H2/ConfigChange residual (names this
  witness as the compensator).
- `.claude/scripts/otel-local-sink.py` — the loopback sink (this unit).
- `templates/settings/settings.stack.otel.json` — the opt-in profile.
- `docs/GOVERNANCE-MAP.md` §1 — independent-witness positioning note.
- PLAN-135 §W5 O10 — originating plan item.
