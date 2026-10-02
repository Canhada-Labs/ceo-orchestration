#!/usr/bin/env python3
"""ceo-cost-transcripts.py — cost/token report derived from harness-native
transcripts (``message.usage`` per assistant turn), NOT the audit log.

## Why this exists (PLAN-186 W0, S339)

``ceo-cost.py`` and ``budget-summary.py``'s audit-log rollup report
``$0.00`` over 30 days because the audit log is a *governance* log (spawns,
vetoes, edits, ceremonies) — it is not a token ledger. The real spend lives
in the harness-native transcripts under
``~/.claude/projects/<slug>/*.jsonl`` (the main/"assento" sessions) and
``~/.claude/projects/<slug>/<session>/subagents/**/agent-*.jsonl`` (spawned
sub-agents, both plain Task-tool and Workflow rails). Each ``type ==
"assistant"`` record carries a full ``message.usage`` snapshot: fresh
input, output, and prompt-cache read/write (split 5-minute / 1-hour TTL).

This is documented in ``docs/research/s339-orchestrator-study/
05-finops-routing.md`` (P0-1, §1, §Metodologia) — that report's own
scratchpad-local aggregator produced **$11,137.97** over 2026-08-03 →
2026-09-02. This script is the in-tree, tested, stdlib-only version of
that instrument.

``budget-summary.py`` already reads *some* native transcripts
(``_read_native_spawn`` / ``collect_native_spawns``, lines 920-1200) but
only under ``<session>/subagents/**`` — it never reads the top-level
``<session>.jsonl`` files, so it is structurally blind to the "assento"
(main session) spend, which the S339 report measured at 71% of the total.
This script reads BOTH trees and separates them.

## Pricing contract

Default pricing is an EMBEDDED table (``_EMBEDDED_PRICING`` below),
sourced from the S339 report §1.2/§1.4, itself derived from
``docs/provider-pricing.md`` (primary table + cache-tier multipliers,
lines ~130-153) and ``budget-summary.py``'s
``_CACHE_READ_MULTIPLIER_OVERRIDES`` (the per-model cache-read
exceptions, mirrored below; every other model at 0.10x base; cache
WRITE is 1.25x base at the 5-minute TTL and 2.00x base at the 1-hour
TTL — these multipliers are a
structural constant, not something ``cost-table.yaml`` carries).

``--pricing PATH`` (default ``cost-table.yaml`` next to this script)
attempts to load base ``input_per_mtok`` / ``output_per_mtok`` rows from
that file's mini-YAML ``models:`` block. Two cases:

- **Format doesn't match at all** (file missing, unreadable, no
  ``models:`` section found, zero rows extracted): fall back to the
  fully embedded table wholesale. ``cost-table.yaml`` in this repo has
  NO cache-read/cache-write columns at all — this instrument's whole
  point is cache-aware pricing, so a table that cannot express that is,
  by construction, a format mismatch for this use case; the embedded
  table is the one that can.
- **Format parses AND the path is the untouched default**: rows load
  from the file, then the Owner-ratified corrections in
  ``_RATIFIED_OVERRIDES_FOR_DEFAULT_TABLE`` are layered on top — but
  ONLY where the parsed row actually DIFFERS from the ratified rate.
  As of ``b6dce78`` the in-tree ``cost-table.yaml`` already carries the
  ratified ``claude-sonnet-5`` $2/$10 row, so on the default path the
  correction is currently a NO-OP and ``source`` says so. An
  unconditional overwrite would be worse than useless: it would print
  "ratified correction" while correcting nothing, and the day the
  table is legitimately refreshed it would silently mask the new rate.
  An EXPLICIT ``--pricing`` path supplied by the caller is trusted
  as-is, with no correction at all — the caller opted into a specific
  pricing config on purpose.

Cache-read/write multipliers are ALWAYS the structural constants above,
regardless of which base table is in play, applied per-model (the
``_CACHE_READ_MULTIPLIER_OVERRIDES`` exceptions act on cache read only).

## Corpus contract

- Dedup key: ``message.id`` when present (an API response's usage
  snapshot is identical across every content-block JSONL line the
  harness writes for that one message — thinking/text/tool_use blocks
  each get their own line, all carrying the SAME ``message.usage``);
  falls back to ``requestId`` + record ``uuid`` when ``message.id`` is
  absent. The S339 report's methodology names a
  ``(requestId, apiBlockIndex, message.id)`` key; ``apiBlockIndex`` was
  not observed in this harness version's on-disk schema, so the key
  degrades to what IS observed without inventing a field.
- Role: "assento" for non-sidechain assistant turns in a top-level
  ``<session>.jsonl``; "subagent" for every assistant turn under
  ``<session>/subagents/**/agent-*.jsonl`` regardless of its own
  ``isSidechain`` value (path-shape is the classifier, mirroring
  ``budget-summary.py``'s rail-by-path doctrine — the corpus has no
  reliable field for this). A sidechain turn inside a top-level file (not
  observed in this corpus, but not structurally impossible) is skipped
  rather than double-counted: any Task-tool sub-dispatch already has its
  own dedicated ``agent-*.jsonl``.
- Never touches ``iterations`` on a usage record (it double-counts
  retries — same exclusion the S339 report's methodology names).
- A JSON-parse failure on a candidate line is skipped and counted, never
  raised. An ``unresolved`` model id (not found in the active pricing
  table, after stripping a trailing ``[..]`` context-window suffix such
  as ``[1m]``) is bucketed and reported with its token totals — never
  silently priced at $0 as if it were a genuine zero-cost turn, and never
  guessed.

## Routing invariant (PLAN-186 AC-13, S361)

EVERY execution of this instrument also ASSERTS, from runtime data only,
that the model a spawn was SERVED equals the model its call site DECLARED
(``transcript_rollup()['routing']``: the CLI report, the ``--json`` payload,
and ``collect()``/``render_block()`` for ``ceo-cost.py`` and
``budget-summary.py``). ADR-144:140 measured ``agent(..., {model})`` routing
on ONE harness build (n=2) and carries no forward guarantee; a proof taken
once at land time cannot see the harness going back to ``inherit`` later.

- DECLARED is the ``model`` key of the spawn's ``agent-<id>.meta.json``
  sidecar: what the call actually passed. It is never read from the text of
  a script (an instrument that predicts code from text does not converge).
  Absent or ``inherit`` means NO claim at the site: counted, never a
  violation.
- SERVED is ``message.model`` of the paired ``agent-<id>.jsonl``, never the
  agent's self-report, read through the SAME ``scan_files()``/``dedup()`` as
  the cost report -- with ONE difference: the served model is a fact of the
  TURN, not of its bill, so the routing read lifts the ``usage``
  requirement. A turn the cost report drops for want of ``usage`` (null,
  absent, empty) is still read here, and an assistant record that cannot be
  read at all is counted (INCONCLUSIVE), never silently skipped. Chunks of
  one message resolve to the TERMINAL chunk (highest ``output_tokens``; on a
  tie the LATER line in file order). A message whose chunks disagree about
  the model is counted in ``chunk_model_splits`` (informational) when the
  terminal chunk can be elected from complete information; if one of those
  chunks has NO ``output_tokens`` the terminal cannot be proven, it is
  counted in ``chunk_terminal_unprovable``, the group is EXCLUDED from the
  comparison (its guessed terminal can neither raise a violation nor vouch
  for the routing) and the verdict is INCONCLUSIVE -- never GREEN, and never
  RED on that group's account; a RED can only come from another group whose
  terminal is proven. ``<synthetic>`` is a harness pseudo-model and is
  ignored.
- EVERY string taken from a transcript or a sidecar is made printable where
  it enters the instrument (non-printable characters become ``?``): a model
  id, a session id, a label or an archetype name cannot forge a verdict line
  or drive a terminal in ANY renderer.
- A WINDOW decides first. A sidecar the check cannot trust (unreadable,
  refused, or a declaration it cannot classify) gates a window only if its
  spawn has a turn inside it; one from outside is counted as
  ``out_of_window`` and never reaches the verdict. The same holds record by
  record: an unreadable assistant record with a valid timestamp OUTSIDE the
  window leaves before it is counted; only what has no temporal position at
  all (a torn line, no timestamp) or sits inside the window can make the
  verdict INCONCLUSIVE, and where that makes a spawn's placement unprovable
  the check fails closed. The ``declared`` / ``undeclared`` counters stay
  corpus-wide.
- LABEL is the sidecar ``description`` (the Workflow ``label``; the native
  spawn's ``description``).
- ALIAS -> FAMILY, not alias -> id. ``opus|sonnet|haiku|fable`` are matched
  by FAMILY, derived from the fleet tables and never retyped; a full id is
  matched EXACTLY (a ``-YYYYMMDD`` date suffix is tolerated). A pinned
  alias -> id table was refused on evidence: on one harness the same
  ``sonnet`` was served as ``claude-sonnet-5`` and later as
  ``claude-sonnet-5-5``, so such a table is red the day the substrate
  re-points the alias and green over the very hole it has to see. The
  alias -> served pairs actually observed are PRINTED, never judged.
- SECOND PREDICATE (the AC-10 requirement named for whoever closes AC-13):
  a spawn whose archetype (``customAgentType``, else ``agentType``) is in
  ``VETO_FLOOR_ROLES`` must be served inside ``VETO_FLOOR_ALLOWED`` --
  MEMBERSHIP, never a family prefix -- declared or not. Both sets are
  imported from ``_lib.agent_frontmatter``, never retyped. Declared ==
  served is silent about the floor (``model: sonnet`` on a VETO spawn
  matches itself and is still a breach), which is why this is a second
  predicate and not a corollary of the first.
- Verdicts, worst first: RED (a violation), INCONCLUSIVE (something the
  check could not read or classify, named), VACUOUS (nothing was compared:
  a vacuous GREEN is refused), GREEN. The exit code stays 0 so the cost
  report is never broken by a routing finding; ``--assert-routing`` turns
  the verdict into a gate: 0 GREEN, 1 RED, 3 not proven (INCONCLUSIVE or
  VACUOUS). Out of scope, declared: the seat (no sidecar), spawns that
  declare nothing, an archetype that the sidecar does not record (the
  persona-injected ``general-purpose`` rail), and whether a site's
  ``model:`` is the RIGHT one for its task class (AC-3a / W1).

PRE-REGISTERED DEATH CRITERIA -- fixed here before the first real run;
changing any number is a plan amendment, never an edit in passing.

  K-A (the detector dies: rebuild or retire it, never tune around it)
    K-A1 positive control: the synthetic pair in
         ``test_ceo_cost_transcripts.py`` (declared ``sonnet`` and served
         an Opus id is RED; declared == served is GREEN) must hold on every
         CI run. A control that stops biting kills the detector.
    K-A2 blindness: an execution over a window with >= 20 spawn sidecars
         and ``declared == 0``, in a window the operator knows contained
         spawns that passed ``model:``, means the sidecar schema drifted
         under the detector. It is blind until rebuilt against the new
         schema. (The ``sidecars`` / ``declared`` / ``undeclared`` counters
         are printed on every run so this is checkable from the output.)
    K-A3 noise: three DISTINCT violations (three different sidecars) each
         judged a FALSE POSITIVE of the predicate IN WRITING means the
         predicate that fired is re-scoped by an ADR or deleted. A TRUE
         positive is not noise: a deliberate below-floor probe, or a
         harness fallback that really served another model, stays RED for
         as long as its spawn is inside the window. There is deliberately
         no suppression list in this file.
  K-B (what a RED means: the lever, not the detector)
    K-B1 a MISMATCH (no served turn on the declared model) on a site that
         declares ``model:``, reproduced by ONE control spawn with the same
         declaration on the same harness build, means ``model:`` does not
         route on that build: the explicit sites of W1/AC-3a are inert
         there, ADR-144's measurement is amended, and the premise "route
         builders by ``model:``" is suspended until a build whose control
         passes.
    K-B2 one FLOOR_BREACH restarts, from zero, the PLAN-186 W3
         end-of-transition clock ("one full wave with no floor violation
         registered by the permanent detector").

Stdlib-only, Python >= 3.9. Read-only: this script writes nothing.
"""
from __future__ import annotations

import argparse
import glob
import json
import os
import re
import sys
import time
from dataclasses import dataclass, field
from datetime import datetime, timedelta, timezone
from pathlib import Path
from typing import Any, Dict, List, Optional, Tuple

# ---------------------------------------------------------------------------
# _lib.runtime_paths (read-only import — this script never edits it or
# budget-summary.py; it only consumes the single resolver per CLAUDE.md §4
# "No file in the audit/state family may re-derive the directory locally").
# ---------------------------------------------------------------------------
_SCRIPT_DIR = Path(__file__).resolve().parent
_REPO_ROOT = _SCRIPT_DIR.parent.parent  # .claude/scripts -> .claude -> repo root
_HOOKS_DIR = _REPO_ROOT / ".claude" / "hooks"
if str(_HOOKS_DIR) not in sys.path:
    sys.path.insert(0, str(_HOOKS_DIR))

try:
    from _lib import runtime_paths as _rp  # noqa: E402
except Exception:  # pragma: no cover - resolver import must never crash the CLI
    _rp = None


# ---------------------------------------------------------------------------
# Pricing tables
# ---------------------------------------------------------------------------

#: Embedded fallback / correction source. Report 05-finops-routing.md §1.2 +
#: §1.4 (S339, measured 2026-08-03..2026-09-02). Sonnet 5 at the
#: Owner-ratified 2026-09-01 intro rate (CLAUDE.md commit e47bf5d).
#: ADR-149 Amendment 3 (S357): claude-opus-5-5 at $4/$20 (pricing page
#: fetched 2026-09-22).
_EMBEDDED_PRICING: Dict[str, Dict[str, float]] = {
    "claude-fable-5-1": {"input_per_mtok": 10.00, "output_per_mtok": 50.00},
    "claude-fable-5": {"input_per_mtok": 10.00, "output_per_mtok": 50.00},
    "claude-opus-5-5": {"input_per_mtok": 4.00, "output_per_mtok": 20.00},
    "claude-opus-5": {"input_per_mtok": 5.00, "output_per_mtok": 25.00},
    "claude-opus-4-8": {"input_per_mtok": 5.00, "output_per_mtok": 25.00},
    "claude-sonnet-5": {"input_per_mtok": 2.00, "output_per_mtok": 10.00},
    "claude-sonnet-4-6": {"input_per_mtok": 3.00, "output_per_mtok": 15.00},
    "claude-haiku-4-5": {"input_per_mtok": 1.00, "output_per_mtok": 5.00},
}

#: Applied ONLY on top of a successfully-parsed DEFAULT --pricing path
#: (never on an explicit caller-supplied path), and ONLY where the
#: parsed row differs from the value below. An entry that matches the
#: file is reported as a no-op, never as a correction. See module
#: docstring.
_RATIFIED_OVERRIDES_FOR_DEFAULT_TABLE: Dict[str, Dict[str, float]] = {
    "claude-sonnet-5": {"input_per_mtok": 2.00, "output_per_mtok": 10.00},
}

#: docs/provider-pricing.md lines ~130-153 ("Cache-tier multipliers"):
#: fresh input 1.00x, cache write 5m 1.25x, cache write 1h 2.00x, cache
#: read 0.10x (base input rate) — EXCEPT the per-model entries below:
#: claude-fable-5-1 at 0.025x (pricing page 2026-09-01, ADR-149
#: Amendment 2) and claude-opus-5-5 at 0.05x (pricing page 2026-09-22,
#: ADR-149 Amendment 3). The pricing page also prices Mythos 5.1 cache
#: hits at 0.025x; that model is outside the ADR-149 working set and
#: carries no entry. Mirrors budget-summary.py's
#: _CACHE_READ_MULTIPLIER_OVERRIDES exactly (bound by
#: test_model_fleet_presence.py since S357).
_CACHE_READ_MULTIPLIER_DEFAULT: float = 0.10
_CACHE_READ_MULTIPLIER_OVERRIDES: Dict[str, float] = {
    "claude-fable-5-1": 0.025,
    "claude-opus-5-5": 0.05,
}
_CACHE_WRITE_5M_MULTIPLIER: float = 1.25
_CACHE_WRITE_1H_MULTIPLIER: float = 2.00

_MODEL_SUFFIX_RE = re.compile(r"\[[^\[\]]*\]$")


def _cache_read_multiplier(model_id: str) -> float:
    return _CACHE_READ_MULTIPLIER_OVERRIDES.get(model_id, _CACHE_READ_MULTIPLIER_DEFAULT)


def _cache_read_exceptions_text() -> str:
    """Per-model cache-read exceptions rendered FROM the override table
    (ADR-149 Amendment 3, S357: the help text is derived, never re-listed)."""
    return ", ".join(
        "%gx for %s" % (mult, model_id)
        for model_id, mult in sorted(_CACHE_READ_MULTIPLIER_OVERRIDES.items())
    )


def normalize_model_id(raw: Optional[str]) -> Optional[str]:
    """Strip a trailing context-window suffix (e.g. ``[1m]``). No guessing."""
    if not isinstance(raw, str) or not raw.strip():
        return None
    return _MODEL_SUFFIX_RE.sub("", raw.strip())


def _safe_text(value: Any, limit: int = 80) -> str:
    """Untrusted text (a transcript or sidecar field) made safe to PRINT.

    Every non-printable character -- an ESC, a newline, a bidi override --
    becomes ``?``, so a forged ``ROUTING INVARIANT ... GREEN`` line or a
    terminal escape cannot ride in on a model id, a session id, a label or
    an archetype name. It is applied where the text ENTERS the instrument
    (``_extract_record`` for every transcript-derived string, the routing
    reader for every sidecar-derived one), so every renderer downstream --
    the CLI table, the JSON report, the two callers' blocks -- inherits it
    and a new print site cannot forget it.
    """
    return "".join(c if c.isprintable() else "?" for c in str(value))[:limit]


def _parse_cost_table_yaml(text: str) -> Dict[str, Dict[str, float]]:
    """Minimal parser for the ``models:`` block of cost-table.yaml's mini-YAML
    subset (top-level scalars + one level of 2-space-indented nested dicts —
    see that file's own header comment). Extracts ONLY the two numeric
    fields this instrument needs; anything else (``tier``, ``source_url``,
    ...) is ignored. Never raises — a malformed file just yields {}.
    """
    models: Dict[str, Dict[str, float]] = {}
    in_models = False
    current: Optional[str] = None
    for raw_line in text.splitlines():
        if not raw_line.strip():
            continue
        stripped = raw_line.strip()
        if stripped.startswith("#"):
            continue
        if not raw_line.startswith(" ") and not raw_line.startswith("\t"):
            in_models = raw_line.rstrip() == "models:"
            current = None
            continue
        if not in_models:
            continue
        indent = len(raw_line) - len(raw_line.lstrip(" "))
        if indent == 2 and stripped.endswith(":"):
            current = stripped[:-1].strip()
            models.setdefault(current, {})
            continue
        if indent >= 4 and current is not None:
            field_txt = stripped
            if "#" in field_txt:
                field_txt = field_txt.split("#", 1)[0].rstrip()
            if ":" not in field_txt:
                continue
            key, _, val = field_txt.partition(":")
            key = key.strip()
            val = val.strip()
            if key in ("input_per_mtok", "output_per_mtok"):
                try:
                    models[current][key] = float(val)
                except ValueError:
                    continue
    return models


@dataclass
class PricingResult:
    table: Dict[str, Dict[str, float]]
    source: str  # human-readable description for --help / report footer
    used_fallback: bool


def _override_is_a_no_op(
    current: Optional[Dict[str, float]], override: Dict[str, float]
) -> bool:
    """True when the parsed row ALREADY carries every ratified value.

    Guards the one thing an unconditional overwrite cannot express: the
    difference between a stale file that WAS corrected and a file that
    was already right. Missing row / wrong type => not a no-op, so the
    override still lands.
    """
    if not isinstance(current, dict):
        return False
    for key, value in override.items():
        have = current.get(key)
        if isinstance(have, bool) or not isinstance(have, (int, float)):
            return False
        if abs(float(have) - float(value)) > 1e-9:
            return False
    return True


def load_pricing(pricing_arg: Optional[str]) -> PricingResult:
    """Resolve the active {model_id: {input_per_mtok, output_per_mtok}}
    table per the contract in the module docstring."""
    is_default_path = pricing_arg is None
    path = Path(pricing_arg) if pricing_arg else (_SCRIPT_DIR / "cost-table.yaml")

    text: Optional[str] = None
    if path.is_file():
        try:
            text = path.read_text(encoding="utf-8")
        except OSError:
            text = None

    parsed: Dict[str, Dict[str, float]] = _parse_cost_table_yaml(text) if text else {}
    complete_rows = {
        mid: row
        for mid, row in parsed.items()
        if "input_per_mtok" in row and "output_per_mtok" in row
    }

    if not complete_rows:
        return PricingResult(
            table=dict(_EMBEDDED_PRICING),
            source=(
                "embedded (report 05-finops-routing.md \xa71.4; %s could not "
                "be parsed / had no complete models: rows)" % path
            ),
            used_fallback=True,
        )

    table = dict(complete_rows)
    source = "parsed from %s" % path
    if is_default_path:
        # Conditional by construction: an override that merely restates
        # what the file already says is NOT a correction. Reporting it as
        # one prints a fix that fixed nothing, and applying it anyway
        # would silently mask a legitimate refresh of the table.
        applied: List[str] = []
        noop: List[str] = []
        for mid in sorted(_RATIFIED_OVERRIDES_FOR_DEFAULT_TABLE):
            override = _RATIFIED_OVERRIDES_FOR_DEFAULT_TABLE[mid]
            if _override_is_a_no_op(table.get(mid), override):
                noop.append(mid)
                continue
            table[mid] = dict(override)
            applied.append(
                "%s -> $%g/$%g"
                % (
                    mid,
                    override["input_per_mtok"],
                    override["output_per_mtok"],
                )
            )
        if applied:
            source += (
                " + ratified correction (%s; 2026-09-01, CLAUDE.md "
                "e47bf5d)" % ", ".join(applied)
            )
        if noop:
            source += (
                " + ratified correction NOT needed for %s (the file "
                "already carries the ratified rate)" % ", ".join(noop)
            )
    return PricingResult(table=table, source=source, used_fallback=False)


# ---------------------------------------------------------------------------
# Transcript discovery + parsing
# ---------------------------------------------------------------------------


def discover_files(project_dir: Path) -> Tuple[List[Path], List[Path]]:
    """Returns (top_level_session_files, subagent_transcript_files)."""
    top = sorted(Path(p) for p in glob.glob(str(project_dir / "*.jsonl")))
    sub = sorted(
        Path(p)
        for p in glob.glob(
            str(project_dir / "*" / "subagents" / "**" / "agent-*.jsonl"),
            recursive=True,
        )
    )
    return top, sub


def _parse_ts(raw: Any) -> Optional[datetime]:
    if not isinstance(raw, str) or not raw:
        return None
    s = raw[:-1] + "+00:00" if raw.endswith("Z") else raw
    try:
        dt = datetime.fromisoformat(s)
    except ValueError:
        return None
    if dt.tzinfo is None:
        dt = dt.replace(tzinfo=timezone.utc)
    return dt


def _as_int(v: Any) -> int:
    return int(v) if isinstance(v, (int, float)) and not isinstance(v, bool) else 0


@dataclass
class UsageRecord:
    key: str
    ts: datetime
    model: str  # normalized id, or "(unresolved:<raw>)" when unmatched later
    effort: Optional[str]
    session_id: str
    role: str  # "assento" | "subagent"
    input_tokens: int = 0
    output_tokens: int = 0
    cache_read_tokens: int = 0
    cache_write_5m: int = 0
    cache_write_1h: int = 0
    #: False when the line carried no usable ``output_tokens`` (a
    #: ``usage_optional`` read of a turn whose ``usage`` is null, absent or
    #: partial). ``dedup()`` elects the terminal chunk by ``output_tokens``,
    #: so a record without them cannot be ranked: the routing reader must
    #: not pretend it was.
    has_usage: bool = True


@dataclass
class ScanCounters:
    files_scanned: int = 0
    lines_seen: int = 0
    candidate_lines: int = 0
    corrupted_lines: int = 0
    missing_timestamp: int = 0
    missing_usage_keys: int = 0
    assistant_without_usage: int = 0
    sidechain_in_toplevel_skipped: int = 0
    unreadable_files: int = 0
    deduped_records: int = 0
    #: ``usage_optional`` reads only (the routing reader): one entry per
    #: assistant record with no ``message`` object -- nothing, not even a
    #: model id, can be read from it. Each entry is the record's own
    #: timestamp (``None`` when it has no valid one), so the caller can keep
    #: a record that is PROVABLY outside the window out of the verdict.
    unreadable_assistant_ts: List[Optional[datetime]] = field(default_factory=list)


def _extract_record(
    obj: Dict[str, Any],
    role: str,
    fallback_session_id: str,
    counters: ScanCounters,
    usage_optional: bool = False,
) -> Optional[UsageRecord]:
    """One assistant line -> ``UsageRecord`` (or ``None``).

    ``usage_optional`` is the ROUTING reader's switch (PLAN-186 AC-13): the
    served model is a fact of the turn, not of its token bill, so a turn
    whose ``usage`` is ``null``, absent or empty is still READ (zero
    tokens) instead of vanishing. The cost reader keeps the default
    ``False`` and is unchanged: it drops such a turn exactly as before.
    """
    if obj.get("type") != "assistant":
        return None
    msg = obj.get("message")
    if not isinstance(msg, dict):
        if usage_optional:
            counters.unreadable_assistant_ts.append(_parse_ts(obj.get("timestamp")))
        return None
    usage = msg.get("usage")
    if not isinstance(usage, dict):
        if not usage_optional:
            return None
        usage = {}
    elif ("input_tokens" not in usage) and ("output_tokens" not in usage):
        if not usage_optional:
            counters.missing_usage_keys += 1
            return None
    out_tokens = usage.get("output_tokens")
    has_usage = isinstance(out_tokens, int) and not isinstance(out_tokens, bool)
    if role == "assento" and obj.get("isSidechain") is True:
        counters.sidechain_in_toplevel_skipped += 1
        return None

    ts = _parse_ts(obj.get("timestamp"))
    if ts is None:
        counters.missing_timestamp += 1
        return None

    # Every string below is DATA written by the harness (or by whoever can
    # write the transcript) and is later PRINTED by four renderers: it is
    # made printable HERE, once, at the door (``_safe_text``).
    model_raw = msg.get("model")
    model_norm = _safe_text(
        normalize_model_id(model_raw) or "(unresolved:%r)" % (model_raw,), 120
    )

    session_id = obj.get("sessionId")
    if not isinstance(session_id, str) or not session_id:
        session_id = fallback_session_id
    session_id = _safe_text(session_id, 200)

    effort = obj.get("effort")
    effort_val = _safe_text(effort, 40) if isinstance(effort, str) and effort else None

    msg_id = msg.get("id")
    if isinstance(msg_id, str) and msg_id:
        key = "mid:" + msg_id
    else:
        key = "req:%s:uuid:%s" % (obj.get("requestId"), obj.get("uuid"))

    input_tokens = _as_int(usage.get("input_tokens"))
    output_tokens = _as_int(usage.get("output_tokens"))
    cache_read = _as_int(usage.get("cache_read_input_tokens"))
    c_total = _as_int(usage.get("cache_creation_input_tokens"))

    c_5m = c_1h = 0
    cc = usage.get("cache_creation")
    if isinstance(cc, dict):
        c_5m = _as_int(cc.get("ephemeral_5m_input_tokens"))
        c_1h = _as_int(cc.get("ephemeral_1h_input_tokens"))
    # Clamp + "unattributed write assumed 5m" — mirrors
    # budget-summary.py's _read_native_spawn cache-split reconciliation.
    c_1h = min(c_1h, c_total)
    c_5m = min(c_5m, c_total - c_1h)
    c_rest = c_total - c_1h - c_5m
    c_5m += c_rest

    return UsageRecord(
        key=key,
        ts=ts,
        model=model_norm,
        effort=effort_val,
        session_id=session_id,
        role=role,
        input_tokens=input_tokens,
        output_tokens=output_tokens,
        cache_read_tokens=cache_read,
        cache_write_5m=c_5m,
        cache_write_1h=c_1h,
        has_usage=has_usage,
    )


def scan_files(
    files: List[Path],
    role: str,
    project_dir: Path,
    counters: ScanCounters,
    usage_optional: bool = False,
) -> List[UsageRecord]:
    """Read assistant turns from `files`. ``usage_optional`` is the routing
    reader's switch (see ``_extract_record``): turns without a usable
    ``usage`` are read, not dropped; the default leaves the cost reader as
    it always was."""
    out: List[UsageRecord] = []
    for path in files:
        counters.files_scanned += 1
        if role == "assento":
            fallback_session_id = path.stem
        else:
            try:
                fallback_session_id = path.relative_to(project_dir).parts[0]
            except ValueError:
                fallback_session_id = path.parent.name
        try:
            with path.open("rb") as f:
                for raw in f:
                    counters.lines_seen += 1
                    # Fast pre-filter: every real assistant/usage line
                    # carries both substrings; anything without them is
                    # skipped WITHOUT paying a json.loads (tool results
                    # and user turns dominate the corpus by line count —
                    # measured 330427/409255 skipped this way on the
                    # live corpus, 640MB scanned in ~2.8s).
                    if b'"assistant"' not in raw:
                        continue
                    if b'"usage"' not in raw and not usage_optional:
                        # Rail r3 P1-2: an assistant-shaped line with no
                        # usage substring is either a renamed/removed
                        # field or a torn write - a DROPPED turn, not a
                        # user record. Counted so completeness detection
                        # can see it. (A tear that also loses the
                        # `"assistant"` substring is indistinguishable
                        # from a user turn by construction - that is the
                        # price of the prefilter, and it is declared.)
                        counters.assistant_without_usage += 1
                        continue
                    counters.candidate_lines += 1
                    try:
                        obj = json.loads(raw)
                    except ValueError:
                        counters.corrupted_lines += 1
                        continue
                    if not isinstance(obj, dict):
                        counters.corrupted_lines += 1
                        continue
                    rec = _extract_record(
                        obj, role, fallback_session_id, counters, usage_optional
                    )
                    if rec is not None:
                        out.append(rec)
        except OSError:
            counters.unreadable_files += 1
            continue
    return out


def dedup(records: List[UsageRecord]) -> Tuple[List[UsageRecord], int]:
    """Collapse every record sharing a dedup key into ONE merged record.

    A message.id's usage snapshot is NOT always a static repeat across
    its content-block JSONL lines. Measured on the live subagent corpus
    (PLAN-186 W0 follow-up, cross-model review): 14,054 of 21,414
    multi-line message.id groups (65.6%) carry a PROGRESSIVE
    ``output_tokens`` count that grows monotonically in file-append
    order — zero counter-examples found across the whole corpus — while
    ``input_tokens`` stays constant across every one of those groups
    (cache fields vary in only 4/16,070 multi-line groups; model
    metadata in 3/21,414, evidently harness fallback/streaming
    resolution settling on the first chunk). A first-write-wins or
    arbitrary-line-wins dedup keeps whichever INTERIM snapshot happened
    to land first — for the dominant growth pattern that is the
    SMALLEST output_tokens value, silently undercounting output cost
    for the majority of subagent turns.

    The fix: take the per-field MAXIMUM across every line sharing a key.
    This is exact for the dominant monotonic-growth case (the max IS the
    terminal/final snapshot) and is safe for the small residual where a
    non-output field also varies, since a per-field max can never be
    LOWER than any single observed snapshot — the failure mode this
    replaces. Metadata (model, effort, session_id, role) is taken from
    whichever line in the group has the highest ``output_tokens`` (the
    most-complete/terminal snapshot; on a tie, the LATER line in file
    order); the merged timestamp is the
    EARLIEST line in the group (the turn's start, matching what a plain
    first-write-wins dedup would already have reported for ``--by day``
    bucketing).
    """
    groups: Dict[str, List[UsageRecord]] = {}
    order: List[str] = []
    for rec in records:
        bucket = groups.get(rec.key)
        if bucket is None:
            groups[rec.key] = [rec]
            order.append(rec.key)
        else:
            bucket.append(rec)

    out: List[UsageRecord] = []
    dropped = 0
    for key in order:
        group = groups[key]
        dropped += len(group) - 1
        if len(group) == 1:
            out.append(group[0])
            continue
        # TERMINAL chunk = the highest ``output_tokens``; on a TIE the LATER
        # line in file order (the one the harness streamed last). `max`
        # keeps the FIRST maximum it meets, so the group is walked in
        # reverse: without this, equal counts left the earlier chunk's
        # model/effort/session as the group's, and file order silently
        # decided between two verdicts.
        terminal = max(reversed(group), key=lambda r: r.output_tokens)
        out.append(
            UsageRecord(
                key=key,
                ts=min(r.ts for r in group),
                model=terminal.model,
                effort=terminal.effort,
                session_id=terminal.session_id,
                role=terminal.role,
                input_tokens=max(r.input_tokens for r in group),
                output_tokens=max(r.output_tokens for r in group),
                cache_read_tokens=max(r.cache_read_tokens for r in group),
                cache_write_5m=max(r.cache_write_5m for r in group),
                cache_write_1h=max(r.cache_write_1h for r in group),
            )
        )
    return out, dropped


# ---------------------------------------------------------------------------
# Pricing application + aggregation
# ---------------------------------------------------------------------------


@dataclass
class Priced:
    rec: UsageRecord
    cost_usd: float
    resolved: bool


def price_records(
    records: List[UsageRecord], pricing: Dict[str, Dict[str, float]]
) -> List[Priced]:
    out: List[Priced] = []
    for rec in records:
        base = pricing.get(rec.model)
        if base is None:
            out.append(Priced(rec=rec, cost_usd=0.0, resolved=False))
            continue
        inp = base["input_per_mtok"]
        outp = base["output_per_mtok"]
        read_mult = _cache_read_multiplier(rec.model)
        cost = (
            rec.input_tokens * inp
            + rec.output_tokens * outp
            + rec.cache_read_tokens * inp * read_mult
            + rec.cache_write_5m * inp * _CACHE_WRITE_5M_MULTIPLIER
            + rec.cache_write_1h * inp * _CACHE_WRITE_1H_MULTIPLIER
        ) / 1_000_000.0
        out.append(Priced(rec=rec, cost_usd=cost, resolved=True))
    return out


_GROUP_KEYS = {
    "model": lambda p: p.rec.model,
    "role": lambda p: p.rec.role,
    "session": lambda p: p.rec.session_id,
    "day": lambda p: p.rec.ts.strftime("%Y-%m-%d"),
}

#: How the ORDERED dimensions of a multi-dimension `--by` are joined into
#: ONE bucket label. Rail r1 [P2]: assuming the separator is absent from
#: every dimension's value space is an ASSERTION, not a guarantee -- a
#: session id carrying it would merge two distinct tuples into one
#: bucket. Each component is ESCAPED first, so the label is injective
#: whatever the corpus contains.
_BY_SEPARATOR = " | "


def _escape_dim_value(v: Any) -> str:
    """Make one dimension value safe to join with `_BY_SEPARATOR`.

    Backslash first, then the pipe: after this, a literal `|` inside a
    value can never be read as the joiner, so distinct tuples keep
    distinct labels (the mapping is injective, not merely usually
    unambiguous).
    """
    return str(v).replace("\\", "\\\\").replace("|", "\\|")


def _split_by(by: Any) -> List[str]:
    """The ONE grammar for `--by`: an ORDERED, comma-separated dimension list.

    The flag, ``transcript_rollup()`` and ``aggregate()`` all parse through
    this function, so a second grafia of the grammar cannot appear (the
    D1-D4 defect class of CLAUDE.md section 5). The ORDER given is the
    GROUPING order. Raises ``ValueError`` with a NAMED reason; ``main()``
    turns that into an rc-2 refusal instead of quietly grouping by
    something else.
    """
    raw = by if isinstance(by, str) else ",".join(str(d) for d in by)
    valid = ", ".join(sorted(_GROUP_KEYS))
    if not raw.strip():
        raise ValueError("empty --by value; expected one or more of: %s" % valid)
    out: List[str] = []
    for d in [part.strip() for part in raw.split(",")]:
        if not d:
            raise ValueError(
                "empty dimension in --by %r (stray comma); expected one or "
                "more of: %s" % (raw, valid)
            )
        if d not in _GROUP_KEYS:
            raise ValueError(
                "unknown breakdown dimension: %r; expected one or more of: "
                "%s" % (d, valid)
            )
        if d in out:
            raise ValueError("duplicated dimension %r in --by %r" % (d, raw))
        out.append(d)
    return out


def _group_key_fn(dims: List[str]) -> Any:
    """Bucket key for an ORDERED dimension list, `_BY_SEPARATOR`-joined.

    One dimension keeps the bare value it always had (so a `--by model`
    report is byte-identical to the pre-`--until` one); two or more are
    ESCAPED and joined in the order the caller asked for.
    """
    fns = [_GROUP_KEYS[d] for d in dims]
    if len(fns) == 1:
        return fns[0]
    return lambda p: _BY_SEPARATOR.join(_escape_dim_value(fn(p)) for fn in fns)


_TOKEN_CLASSES = (
    "input_tokens",
    "output_tokens",
    "cache_read_tokens",
    "cache_write_5m",
    "cache_write_1h",
)


def _bucket_totals() -> Dict[str, float]:
    return {
        "turns": 0,
        "input_tokens": 0,
        "output_tokens": 0,
        "cache_read_tokens": 0,
        "cache_write_5m": 0,
        "cache_write_1h": 0,
        "usd": 0.0,
    }


def aggregate(priced: List[Priced], by: str) -> Tuple[Dict[str, float], Dict[str, Dict[str, float]], Dict[str, Dict[str, float]]]:
    """Returns (grand_total, role_totals, by-dimension totals)."""
    grand = _bucket_totals()
    role_totals: Dict[str, Dict[str, float]] = {}
    group_totals: Dict[str, Dict[str, float]] = {}
    key_fn = _group_key_fn(_split_by(by))

    for p in priced:
        for d in (grand, role_totals.setdefault(p.rec.role, _bucket_totals()), group_totals.setdefault(key_fn(p), _bucket_totals())):
            d["turns"] += 1
            for cls in _TOKEN_CLASSES:
                d[cls] += getattr(p.rec, cls)
            d["usd"] += p.cost_usd

    return grand, role_totals, group_totals


# ---------------------------------------------------------------------------
# Routing invariant (PLAN-186 AC-13) -- contract in the module docstring
# ---------------------------------------------------------------------------

#: Verdicts, worst first. The order IS the precedence: a violation is never
#: masked by an incomplete read, and an incomplete read is never reported
#: as "nothing to compare".
ROUTING_VERDICTS = ("RED", "INCONCLUSIVE", "VACUOUS", "GREEN")

#: `--assert-routing` exit codes (rc 2 stays the argument-error code).
ROUTING_RC_GREEN = 0
ROUTING_RC_RED = 1
ROUTING_RC_NOT_PROVEN = 3

#: Declarations that make NO routing claim at the call site.
_NO_CLAIM_DECLARATIONS = frozenset({"", "inherit"})

#: A spawn sidecar is a few hundred bytes. Anything bigger is not one, and
#: is refused rather than parsed.
_SIDECAR_MAX_BYTES = 65536

#: The harness pseudo-model stamped on turns that never reached a model
#: (errors, rate-limit walls). Zero tokens by construction.
_SYNTHETIC_MODEL = "<synthetic>"

_FAMILY_RE = re.compile(r"^claude-(?:\d+-)*([a-z]+)(?:-|$)")
_DATED_SUFFIX_RE = re.compile(r"-\d{8}")
_DECLARED_ID_RE = re.compile(r"^claude-[a-z0-9][a-z0-9._-]*$")

#: What the human/JSON report cites so the pre-registration cannot drift
#: away from the code that enforces it.
ROUTING_PREREG_POINTER = (
    "death criteria K-A1..K-A3 and K-B1..K-B2 are pre-registered in the "
    "module docstring of ceo-cost-transcripts.py"
)


def model_family(model_id: Any) -> Optional[str]:
    """Family token of a model id: ``claude-opus-5-5`` -> ``opus``,
    ``claude-haiku-4-5-20251001`` -> ``haiku``, ``claude-3-5-haiku-x`` ->
    ``haiku``. ``None`` when the id does not parse."""
    if not isinstance(model_id, str):
        return None
    m = _FAMILY_RE.match(model_id.strip().lower())
    return m.group(1) if m else None


def _floor_source() -> Optional[Tuple[frozenset, frozenset]]:
    """(VETO_FLOOR_ROLES, VETO_FLOOR_ALLOWED), imported at CALL time from
    the repo's own ``_lib.agent_frontmatter`` -- the Owner-signed source,
    never a copy. ``None`` (and the verdict says so) when it cannot be
    read: a floor predicate that silently skipped itself would be a
    vacuous GREEN."""
    try:
        from _lib import agent_frontmatter as _af

        roles = frozenset(str(r) for r in _af.VETO_FLOOR_ROLES)
        allowed = frozenset(str(m).strip().lower() for m in _af.VETO_FLOOR_ALLOWED)
    except Exception:
        return None
    if not roles or not allowed:
        return None
    return roles, allowed


def known_families(floor: Optional[Tuple[frozenset, frozenset]] = None) -> frozenset:
    """The alias vocabulary, DERIVED from the fleet tables (the pricing
    table and the floor allowlist): a family the fleet does not name is an
    unclassified declaration, not a guess."""
    out = set()
    sources: List[str] = list(_EMBEDDED_PRICING)
    if floor is not None:
        sources.extend(floor[1])
    for mid in sources:
        fam = model_family(mid)
        if fam:
            out.add(fam)
    return frozenset(out)


def classify_declared(raw: Any, families: frozenset) -> Tuple[str, str]:
    """(kind, value) for a sidecar ``model`` value.

    kind is ``none`` (no claim), ``alias`` (a family token), ``id`` (a full
    model id, compared exactly) or ``unclassified`` (cannot be compared;
    named, never guessed). A trailing context-window suffix (``[1m]``) is
    stripped exactly as it is for served ids.
    """
    if raw is None:
        return "none", ""
    if not isinstance(raw, str):
        return "unclassified", repr(raw)[:40]
    d = _MODEL_SUFFIX_RE.sub("", raw.strip()).strip().lower()
    if d in _NO_CLAIM_DECLARATIONS:
        return "none", d
    if d in families:
        return "alias", d
    if _DECLARED_ID_RE.match(d):
        return "id", d
    return "unclassified", d[:40]


def declaration_matches(kind: str, declared: str, served: str) -> bool:
    """One served model id against one classified declaration."""
    s = served.strip().lower()
    if kind == "alias":
        return model_family(s) == declared
    if kind == "id":
        if s == declared:
            return True
        return s.startswith(declared) and _DATED_SUFFIX_RE.fullmatch(
            s[len(declared):]
        ) is not None
    return False


def _discover_sidecars(project_dir: Path) -> List[str]:
    return sorted(
        glob.glob(
            str(project_dir / "*" / "subagents" / "**" / "agent-*.meta.json"),
            recursive=True,
        )
    )


def _inside(path: str, root_real: str) -> bool:
    """True when `path` is a regular, non-symlink file whose real location
    stays inside the corpus root. A link inside the corpus that points at
    another agent's transcript would mis-attribute a model; one that points
    outside would read a file the corpus never owned."""
    if os.path.islink(path):
        return False
    real = os.path.realpath(path)
    return real == root_real or real.startswith(root_real + os.sep)


def _read_sidecar(path: str) -> Optional[Dict[str, Any]]:
    try:
        if os.stat(path).st_size > _SIDECAR_MAX_BYTES:
            return None
        with open(path, "rb") as f:
            obj = json.loads(f.read())
    except (OSError, ValueError, RecursionError):
        return None
    return obj if isinstance(obj, dict) else None


def _archetype(side: Dict[str, Any]) -> str:
    for key in ("customAgentType", "agentType"):
        v = side.get(key)
        if isinstance(v, str) and v:
            return v
    return ""


def _label(side: Dict[str, Any], sidecar_path: str) -> str:
    for key in ("description", "name"):
        v = side.get(key)
        if isinstance(v, str) and v.strip():
            return _safe_text(" ".join(v.split()))
    return _safe_text(os.path.basename(sidecar_path)[: -len(".meta.json")])


def _in_window(
    ts: datetime, cutoff: Optional[datetime], until: Optional[datetime]
) -> bool:
    return (cutoff is None or ts >= cutoff) and (until is None or ts <= until)


def _unplaced_or_inside(
    stamps: List[Optional[datetime]],
    cutoff: Optional[datetime],
    until: Optional[datetime],
) -> int:
    """How many of these record timestamps can still matter to the window:
    those with no valid timestamp (no temporal position at all) and those
    inside it. A record with a valid timestamp OUTSIDE the window leaves
    before it can count as anything."""
    return sum(1 for t in stamps if t is None or _in_window(t, cutoff, until))


def _served_models(
    transcript: str,
    project_dir: Path,
    cutoff: Optional[datetime],
    until: Optional[datetime],
    tally: Dict[str, int],
) -> Optional[Dict[str, int]]:
    """{served model id: turns} for ONE spawn transcript.

    ``{}`` means no REAL served turn exists (no assistant turn at all, or
    only ``<synthetic>`` ones); ``None`` means assistant turns exist but
    every one is outside the window.

    Goes through ``scan_files()`` and ``dedup()`` -- the cost report's own
    reader -- so a message whose streamed chunks disagree about the model
    resolves to the TERMINAL chunk's model exactly as it does for cost, and
    there is no second grafia of either. The served model is a fact of the
    TURN, not of its token bill, so the read is ``usage_optional``: a turn
    the cost report drops (``usage`` null, absent or empty) is still read
    here, and one that cannot be read at all is counted, never silent --
    but only if it can matter to THIS window: a record with a valid
    timestamp outside it leaves before anything about it is counted.
    ``tally`` accumulates the reader's incompleteness counters and the
    message groups whose chunks disagree about the model. A disagreeing
    group whose terminal chunk can be elected from complete information
    (every chunk carries ``output_tokens``) is only counted
    (``chunk_model_splits``, informational); one that has a chunk WITHOUT
    ``output_tokens`` cannot be elected: it is counted in
    ``chunk_terminal_unprovable`` (the verdict is INCONCLUSIVE) and EXCLUDED
    from the returned models, so its guessed terminal can never produce a
    violation.
    """
    counters = ScanCounters()
    recs = scan_files(
        [Path(transcript)], "subagent", project_dir, counters, usage_optional=True
    )
    tally["incomplete_reads"] += (
        counters.corrupted_lines
        + counters.missing_timestamp
        + counters.unreadable_files
        + counters.missing_usage_keys
        + counters.assistant_without_usage
        + _unplaced_or_inside(counters.unreadable_assistant_ts, cutoff, until)
    )
    if not recs:
        return {}
    if cutoff is not None:
        recs = [r for r in recs if r.ts >= cutoff]
    if until is not None:
        recs = [r for r in recs if r.ts <= until]
    groups: Dict[str, List[UsageRecord]] = {}
    for r in recs:
        groups.setdefault(r.key, []).append(r)
    unprovable = set()
    for key, chunks in groups.items():
        if len({c.model for c in chunks}) > 1:
            tally["chunk_model_splits"] += 1
            if not all(c.has_usage for c in chunks):
                tally["chunk_terminal_unprovable"] += 1
                unprovable.add(key)
    if unprovable:
        # A group whose terminal chunk cannot be proven is NOT evidence: the
        # model `dedup()` would elect for it is a guess, so it may neither
        # raise a violation (a MISMATCH, a FLOOR_BREACH) nor vouch for the
        # routing. It leaves the comparison and the verdict is INCONCLUSIVE
        # (``chunk_terminal_unprovable``); a violation can still win, but
        # only from ANOTHER group whose terminal is proven.
        recs = [r for r in recs if r.key not in unprovable]
        if not recs:
            return {}
    deduped, _dropped = dedup(recs)
    if not deduped:
        return None
    served: Dict[str, int] = {}
    for r in deduped:
        if r.model == _SYNTHETIC_MODEL:
            tally["synthetic_turns_ignored"] += 1
            continue
        if r.model.startswith("(unresolved:"):
            tally["served_unresolved"] += 1
            continue
        served[r.model.lower()] = served.get(r.model.lower(), 0) + 1
    return served


def _placement(
    transcript: str,
    project_dir: Path,
    cutoff: Optional[datetime],
    until: Optional[datetime],
) -> str:
    """Where a spawn sits relative to the window, from its transcript alone:
    ``in`` (some assistant turn is inside), ``out`` (turns exist, none
    inside), ``none`` (no assistant turn at all) or ``unplaceable`` (nothing
    inside AND the read was incomplete, so a torn line may be the in-window
    turn -- fail closed). Read with throwaway counters: whether the spawn
    matters to this window is decided here, before anything about it can
    gate the verdict."""
    counters = ScanCounters()
    recs = scan_files(
        [Path(transcript)], "subagent", project_dir, counters, usage_optional=True
    )
    for r in recs:
        if _in_window(r.ts, cutoff, until):
            return "in"
    stamped = [t for t in counters.unreadable_assistant_ts if t is not None]
    if any(_in_window(t, cutoff, until) for t in stamped):
        return "in"
    dirty = (
        counters.corrupted_lines
        + counters.missing_timestamp
        + counters.unreadable_files
        + (len(counters.unreadable_assistant_ts) - len(stamped))
    )
    if dirty:
        return "unplaceable"
    return "out" if (recs or stamped) else "none"


def routing_invariant(
    project_dir: Any,
    cutoff: Optional[datetime] = None,
    until: Optional[datetime] = None,
) -> Dict[str, Any]:
    """Assert, over the spawn sidecars + transcripts under `project_dir`,
    that served == declared and that VETO archetypes were served inside the
    floor. Pure read; returns the verdict as JSON-safe data."""
    project_dir = Path(project_dir)
    root_real = os.path.realpath(str(project_dir))
    floor = _floor_source()
    families = known_families(floor)
    veto_roles = floor[0] if floor else frozenset()
    veto_allowed = floor[1] if floor else frozenset()

    counts: Dict[str, int] = {
        "sidecars": 0,
        "declared": 0,
        "undeclared": 0,
        "unclassified": 0,
        "compared_spawns": 0,
        "declared_compared": 0,
        "floor_checked": 0,
        "no_served": 0,
        "out_of_window": 0,
        "unreadable_sidecars": 0,
        "refused_paths": 0,
        "incomplete_reads": 0,
        "served_unresolved": 0,
        "synthetic_turns_ignored": 0,
        "chunk_model_splits": 0,
        "chunk_terminal_unprovable": 0,
    }
    violations: List[Dict[str, Any]] = []
    alias_resolutions: Dict[str, Dict[str, int]] = {}
    unclassified_samples: List[str] = []

    def gates_the_window(transcript: str) -> bool:
        """A sidecar the check cannot trust (unreadable, refused, or a
        declaration it cannot classify) may gate THIS window only if its
        spawn has a turn in it. A stale one from outside the window is
        counted where it belongs and never reaches the verdict."""
        if not os.path.exists(transcript):
            counts["no_served"] += 1
            return False
        if not _inside(transcript, root_real):
            return True
        where = _placement(transcript, project_dir, cutoff, until)
        if where == "out":
            counts["out_of_window"] += 1
            return False
        if where == "none":
            counts["no_served"] += 1
            return False
        return True

    for sc in _discover_sidecars(project_dir):
        counts["sidecars"] += 1
        transcript = sc[: -len(".meta.json")] + ".jsonl"
        sidecar_inside = _inside(sc, root_real)
        side = _read_sidecar(sc) if sidecar_inside else None
        if side is None:
            if gates_the_window(transcript):
                counts["unreadable_sidecars" if sidecar_inside else "refused_paths"] += 1
            continue
        kind, declared = classify_declared(side.get("model"), families)
        archetype = _archetype(side)
        is_veto = archetype in veto_roles
        if kind == "none":
            counts["undeclared"] += 1
        elif kind == "unclassified":
            if not gates_the_window(transcript):
                continue
            counts["unclassified"] += 1
            if len(unclassified_samples) < 5:
                unclassified_samples.append(_safe_text(declared, 40))
        else:
            counts["declared"] += 1
        needs_served = kind in ("alias", "id") or is_veto
        if not needs_served:
            continue

        if not os.path.exists(transcript):
            counts["no_served"] += 1
            continue
        if not _inside(transcript, root_real):
            counts["refused_paths"] += 1
            continue
        served = _served_models(transcript, project_dir, cutoff, until, counts)
        if served is None:
            counts["out_of_window"] += 1
            continue
        if not served:
            counts["no_served"] += 1
            continue

        # ONE count per spawn that reached a comparison, whatever number of
        # predicates it fed (a declared VETO spawn feeds both).
        counts["compared_spawns"] += 1
        kinds: List[str] = []
        if kind in ("alias", "id"):
            counts["declared_compared"] += 1
            ok = [m for m in served if declaration_matches(kind, declared, m)]
            if not ok:
                kinds.append("MISMATCH")
            elif len(ok) != len(served):
                kinds.append("MIXED")
            if kind == "alias":
                bucket = alias_resolutions.setdefault(declared, {})
                for m in served:
                    shown = _safe_text(m)
                    bucket[shown] = bucket.get(shown, 0) + 1
        if is_veto:
            counts["floor_checked"] += 1
            if any(m not in veto_allowed for m in served):
                kinds.append("FLOOR_BREACH")
        if kinds:
            rel = os.path.relpath(sc, str(project_dir))
            violations.append(
                {
                    "label": _label(side, sc),
                    "rail": "workflow" if "workflows" in Path(rel).parts else "native",
                    "archetype": _safe_text(archetype),
                    "declared": declared if kind in ("alias", "id") else "",
                    "kinds": kinds,
                    "served": dict(
                        sorted((_safe_text(m), n) for m, n in served.items())
                    ),
                    "sidecar": _safe_text(rel, 300),
                }
            )

    incomplete: List[str] = []
    for key, text in (
        ("unclassified", "unclassified declaration(s)"),
        ("unreadable_sidecars", "unreadable sidecar(s)"),
        ("refused_paths", "path(s) refused (symlink or outside the corpus)"),
        ("incomplete_reads", "transcript line(s) torn, undated or unreadable"),
        ("served_unresolved", "served turn(s) without a model id"),
        (
            "chunk_terminal_unprovable",
            "message group(s) whose chunks disagree about the model and whose "
            "terminal chunk cannot be proven (a chunk without usage)",
        ),
    ):
        if counts[key]:
            incomplete.append("%d %s" % (counts[key], text))
    if floor is None:
        incomplete.append("VETO floor source unreadable (floor predicate not evaluated)")

    comparable = counts["compared_spawns"]
    if violations:
        verdict = "RED"
        by_kind: Dict[str, int] = {}
        for v in violations:
            for k in v["kinds"]:
                by_kind[k] = by_kind.get(k, 0) + 1
        reason = "%d spawn(s) violate the invariant (%s) of %d compared" % (
            len(violations),
            ", ".join("%d %s" % (n, k) for k, n in sorted(by_kind.items())),
            comparable,
        )
    elif incomplete:
        verdict = "INCONCLUSIVE"
        reason = "the check is incomplete: " + "; ".join(incomplete)
    elif comparable == 0:
        verdict = "VACUOUS"
        reason = (
            "nothing was compared: no spawn with a declared model (or VETO "
            "archetype) and a served model in the window"
        )
    else:
        verdict = "GREEN"
        reason = (
            "%d spawn(s) compared: %d declared spawn(s) served == declared, "
            "%d VETO spawn(s) served inside the floor"
            % (comparable, counts["declared_compared"], counts["floor_checked"])
        )

    return {
        "verdict": verdict,
        "reason": reason,
        "counts": counts,
        "violations": violations[:200],
        "violations_omitted": max(0, len(violations) - 200),
        "alias_resolutions": {
            a: dict(sorted(r.items())) for a, r in sorted(alias_resolutions.items())
        },
        "unclassified_samples": unclassified_samples,
        "floor": (
            {"roles": sorted(veto_roles), "allowed": sorted(veto_allowed)}
            if floor
            else None
        ),
        "prereg": ROUTING_PREREG_POINTER,
    }


def routing_invariant_safe(
    project_dir: Any,
    cutoff: Optional[datetime] = None,
    until: Optional[datetime] = None,
) -> Dict[str, Any]:
    """`routing_invariant()` that can never break the cost report AND can
    never turn its own failure into a pass: an internal error is an
    INCONCLUSIVE verdict that names the exception class."""
    try:
        return routing_invariant(project_dir, cutoff=cutoff, until=until)
    except Exception as exc:  # pragma: no cover - fail-soft envelope
        return {
            "verdict": "INCONCLUSIVE",
            "reason": "routing check failed: %s" % type(exc).__name__,
            "counts": {},
            "violations": [],
            "violations_omitted": 0,
            "alias_resolutions": {},
            "unclassified_samples": [],
            "floor": None,
            "prereg": ROUTING_PREREG_POINTER,
        }


def routing_rc(routing: Dict[str, Any]) -> int:
    """`--assert-routing` exit code for a verdict."""
    verdict = routing.get("verdict")
    if verdict == "GREEN":
        return ROUTING_RC_GREEN
    if verdict == "RED":
        return ROUTING_RC_RED
    return ROUTING_RC_NOT_PROVEN


def _routing_lines(routing: Optional[Dict[str, Any]], limit: int = 20) -> List[str]:
    """The routing verdict as report lines (ASCII), shared by every
    renderer so the CLI and the two callers' blocks cannot disagree."""
    if not routing:
        return []
    c = routing.get("counts") or {}
    out: List[str] = [
        "ROUTING INVARIANT (PLAN-186 AC-13): %s - %s"
        % (routing.get("verdict"), routing.get("reason"))
    ]
    out.append(
        "  sidecars=%d declared=%d undeclared=%d unclassified=%d | compared=%d "
        "(declared=%d floor=%d) | no_served=%d out_of_window=%d "
        "synthetic_turns_ignored=%d chunk_model_splits=%d "
        "chunk_terminal_unprovable=%d"
        % (
            c.get("sidecars", 0),
            c.get("declared", 0),
            c.get("undeclared", 0),
            c.get("unclassified", 0),
            c.get("compared_spawns", 0),
            c.get("declared_compared", 0),
            c.get("floor_checked", 0),
            c.get("no_served", 0),
            c.get("out_of_window", 0),
            c.get("synthetic_turns_ignored", 0),
            c.get("chunk_model_splits", 0),
            c.get("chunk_terminal_unprovable", 0),
        )
    )
    viol = routing.get("violations") or []
    for v in viol[:limit]:
        out.append(
            "  VIOLATION [%s] %s label=%r archetype=%s declared=%s served=%s"
            % (
                "+".join(v.get("kinds", [])),
                v.get("rail"),
                v.get("label"),
                v.get("archetype") or "-",
                v.get("declared") or "-",
                ",".join(
                    "%s x%d" % (m, n) for m, n in sorted((v.get("served") or {}).items())
                ),
            )
        )
    hidden = max(0, len(viol) - limit) + int(routing.get("violations_omitted") or 0)
    if hidden:
        out.append("  ... (+%d violation(s) omitted; --json lists them)" % hidden)
    res = routing.get("alias_resolutions") or {}
    if res:
        out.append(
            "  alias -> served (observed, informational, never judged): "
            + "; ".join(
                "%s: %s"
                % (a, ", ".join("%s x%d" % (m, n) for m, n in sorted(r.items())))
                for a, r in sorted(res.items())
            )
        )
    return out


# ---------------------------------------------------------------------------
# Programmatic API (PLAN-186 W0, AC-1b)
# ---------------------------------------------------------------------------
#
# `ceo-cost.py` and `budget-summary.py` consume THIS surface, never the
# CLI's stdout. Everything below the `transcript_rollup` line exists so
# the two callers share one root resolver, one collector and one
# renderer — a second grafia of any of them is the exact shape of the
# D1-D4 defect class (CLAUDE.md §5).

#: Env override for the transcripts corpus root. Flag > env > the shared
#: `_lib.runtime_paths` resolver. Tests MUST set this (or pass the flag):
#: nothing here may read the real ~/.claude/projects/<slug> corpus.
ROOT_ENV = "CEO_COST_TRANSCRIPTS_DIR"

#: The `--source` domain, shared by both callers.
SOURCE_CHOICES = ("transcripts", "audit", "both")

TRANSCRIPTS_BANNER = "=== SOURCE: TRANSCRIPTS (message.usage -- PRIMARY) ==="
AUDIT_BANNER = "=== SOURCE: AUDIT LOG (governance ledger -- SECONDARY) ==="


def transcript_rollup(
    project_dir: Any,
    cutoff: Optional[datetime] = None,
    pricing_arg: Optional[str] = None,
    by: str = "model",
    until: Optional[datetime] = None,
) -> Dict[str, Any]:
    """Scan + dedup + price `project_dir`, returning the rollup as data.

    `cutoff` is an aware datetime; records strictly older are dropped.
    `until` is the UPPER bound, INCLUSIVE at record resolution; records
    stamped after it are dropped. `None` on either side means unbounded
    there. This is the single pipeline the CLI itself runs, so the API
    and the printed report can never disagree.
    """
    _split_by(by)  # validate the breakdown BY NAME before any I/O
    project_dir = Path(project_dir)
    pricing_result = load_pricing(pricing_arg)

    top_files, sub_files = discover_files(project_dir)
    counters = ScanCounters()
    records = scan_files(top_files, "assento", project_dir, counters)
    records += scan_files(sub_files, "subagent", project_dir, counters)

    # ONE timestamp field carries BOTH bounds: `UsageRecord.ts`, the
    # parsed `timestamp` of the transcript line. A window whose two ends
    # filtered different fields would be a lie, so the two filters sit
    # here, adjacent, over the same attribute. The upper bound is
    # INCLUSIVE at record resolution (`<=`, never `<`): a record stamped
    # exactly at the bound belongs to the window.
    if cutoff is not None:
        records = [r for r in records if r.ts >= cutoff]
    if until is not None:
        records = [r for r in records if r.ts <= until]

    deduped, dropped = dedup(records)
    counters.deduped_records = len(deduped)

    priced = price_records(deduped, pricing_result.table)

    unresolved: Dict[str, Dict[str, float]] = {}
    for p in priced:
        if not p.resolved:
            d = unresolved.setdefault(p.rec.model, _bucket_totals())
            d["turns"] += 1
            for cls in _TOKEN_CLASSES:
                d[cls] += getattr(p.rec, cls)

    grand, role_totals, group_totals = aggregate(priced, by)
    # AC-13: the routing invariant is asserted by the SAME pipeline the
    # report and both callers run, over the SAME window, so no renderer can
    # print a total without the verdict that travels with it.
    routing = routing_invariant_safe(project_dir, cutoff=cutoff, until=until)
    return {
        "project_dir": str(project_dir),
        "pricing_result": pricing_result,
        "pricing_source": pricing_result.source,
        "pricing_used_fallback": pricing_result.used_fallback,
        "by": by,
        "files": {"assento": len(top_files), "subagent": len(sub_files)},
        "counters": counters,
        "dropped_duplicates": dropped,
        "unresolved_models": unresolved,
        "grand_total": grand,
        "by_role": role_totals,
        "by_dimension": group_totals,
        "routing": routing,
    }


def resolve_root(root_arg: Optional[str] = None) -> Optional[Path]:
    """Flag > `$CEO_COST_TRANSCRIPTS_DIR` > `_lib.runtime_paths`."""
    if root_arg:
        return Path(root_arg)
    env = os.environ.get(ROOT_ENV)
    if env:
        return Path(env)
    return _default_project_dir()


def explicit_root_given(root_arg: Optional[str] = None) -> bool:
    """True when the CALLER pinned the corpus (flag or env), not the
    ambient project resolver. Rail r2 P1-1 turns on this distinction.
    """
    return bool(root_arg) or bool(os.environ.get(ROOT_ENV))


#: The env carriers that point the SECONDARY (audit) ledger somewhere
#: specific. Rail r3 P1-1: a flag is not the only way to override it.
AUDIT_PATH_ENV_CARRIERS = ("CEO_AUDIT_LOG_PATH", "CEO_AUDIT_LOG_DIR")


def audit_source_is_pinned(
    path_arg: Optional[str] = None,
    carriers: Optional[Tuple[str, ...]] = None,
) -> bool:
    """True when the audit ledger was pointed at a specific place.

    ``carriers`` names the env vars the CALLER actually obeys; the
    default is every carrier this instrument knows about. A caller that
    ignores one of them must say so, or the cross-project pairing check
    suppresses its PRIMARY block over an override that moved nothing
    (rail S341 r1 [P2]: ``budget-summary.py`` resolves its audit dir
    from ``CEO_AUDIT_LOG_DIR`` alone, while ``ceo-cost.py`` honours both
    and therefore passes nothing).
    """
    if path_arg:
        return True
    keys = AUDIT_PATH_ENV_CARRIERS if carriers is None else tuple(carriers)
    return any(os.environ.get(k) for k in keys)


def collect(
    root_arg: Optional[str] = None,
    cutoff: Optional[datetime] = None,
    by: str = "model",
    note: Optional[str] = None,
    audit_override: bool = False,
) -> Dict[str, Any]:
    """Caller-facing collector: a JSON-safe rollup, or a labelled note.

    NEVER raises: an absent root, an unreadable corpus or an internal
    failure comes back as `{'available': False, 'reason': ...}` so the
    SECONDARY (audit) source keeps rendering unchanged.
    """
    # Rail r2 P1-1: when the caller pointed the SECONDARY source at an
    # explicit path (--log / --audit-dir) but left the PRIMARY one to the
    # ambient project resolver, the report would juxtapose project A's
    # transcripts with project B's audit log. Refuse the pairing by name
    # rather than print two ledgers from two projects side by side.
    if audit_override and not explicit_root_given(root_arg):
        return {
            "available": False,
            "reason": (
                "the audit source was pointed at an explicit path but no "
                "transcripts root was given - refusing to pair one "
                "project's transcripts with another project's audit log "
                "(pass --transcripts-root or set %s)" % ROOT_ENV
            ),
        }
    root = resolve_root(root_arg)
    if root is None:
        return {
            "available": False,
            "reason": (
                "could not resolve a transcripts root (pass the flag or "
                "set %s)" % ROOT_ENV
            ),
        }
    if not root.is_dir():
        return {
            "available": False,
            "reason": "transcripts root does not exist: %s" % root,
        }
    try:
        res = transcript_rollup(root, cutoff=cutoff, by=by)
    except Exception as exc:  # pragma: no cover - fail-soft envelope
        return {
            "available": False,
            "reason": "transcripts rollup failed: %s" % type(exc).__name__,
        }
    # Rail r1 P1-1: a corrupted line, a line without a timestamp or an
    # unreadable file is SILENTLY dropped by scan_files() — publishing
    # the total without those counters would present a partial figure as
    # the authoritative one. They travel with the payload and
    # `incomplete` makes the renderers say so.
    c = res["counters"]
    return {
        "available": True,
        "root": str(root),
        "by": by,
        "note": note,
        "pricing_source": res["pricing_source"],
        "files": res["files"],
        "totals": res["grand_total"],
        "by_role": res["by_role"],
        "by_dimension": res["by_dimension"],
        "unresolved_models": res["unresolved_models"],
        "routing": res["routing"],
        "scan": {
            "files_scanned": c.files_scanned,
            "lines_seen": c.lines_seen,
            "candidate_lines": c.candidate_lines,
            "corrupted_lines": c.corrupted_lines,
            "missing_timestamp": c.missing_timestamp,
            "unreadable_files": c.unreadable_files,
            "missing_usage_keys": c.missing_usage_keys,
            "assistant_without_usage": c.assistant_without_usage,
            "sidechain_in_toplevel_skipped": (
                c.sidechain_in_toplevel_skipped
            ),
            "dropped_duplicates": res["dropped_duplicates"],
        },
        "incomplete": bool(
            c.corrupted_lines
            or c.missing_timestamp
            or c.unreadable_files
            # Rail r2 P1-2: an assistant record whose `usage` object
            # carries NEITHER core token key is schema drift, not
            # contract - it is a dropped turn. Measured 0 on the live
            # corpus (80,811 candidate lines), so this fires only when
            # the harness schema actually moves.
            or c.missing_usage_keys
            or c.assistant_without_usage
        ),
    }


def render_block(collected: Optional[Dict[str, Any]]) -> List[str]:
    """Render the PRIMARY-source block as lines (no trailing blank)."""
    out: List[str] = [TRANSCRIPTS_BANNER]
    if not collected or not collected.get("available"):
        reason = (collected or {}).get("reason") or "unavailable"
        out.append("transcripts source UNAVAILABLE: %s" % reason)
        return out
    out.append("root: %s" % collected["root"])
    out.append("pricing: %s" % collected["pricing_source"])
    out.append(
        "files: %d assento + %d subagent"
        % (collected["files"]["assento"], collected["files"]["subagent"])
    )
    if collected.get("incomplete"):
        s = collected.get("scan") or {}
        out.append(
            "WARNING: INCOMPLETE SCAN - this total is a LOWER BOUND: "
            "%d corrupted line(s), %d line(s) without a timestamp, "
            "%d unreadable file(s), %d usage record(s) missing both core "
            "token keys and %d assistant line(s) with no usage object "
            "were skipped."
            % (
                s.get("corrupted_lines", 0),
                s.get("missing_timestamp", 0),
                s.get("unreadable_files", 0),
                s.get("missing_usage_keys", 0),
                s.get("assistant_without_usage", 0),
            )
        )
    if collected.get("note"):
        out.append(collected["note"])
    unresolved = collected.get("unresolved_models") or {}
    if unresolved:
        out.append(
            "warning: %d model id(s) absent from the pricing table, "
            "priced as $0 and never guessed: %s"
            % (len(unresolved), ", ".join(sorted(unresolved.keys())))
        )
    out.append("")
    head = "%-12s %8s %13s %13s %13s %13s %11s" % (
        "role", "turns", "input", "cache_w", "cache_r", "output", "cost",
    )
    out.append(head)
    for role in ("assento", "subagent"):
        d = collected["by_role"].get(role) or _bucket_totals()
        out.append(
            "%-12s %8s %13s %13s %13s %13s %11s"
            % (
                role,
                _fmt_int(d["turns"]),
                _fmt_int(d["input_tokens"]),
                _fmt_int(d["cache_write_5m"] + d["cache_write_1h"]),
                _fmt_int(d["cache_read_tokens"]),
                _fmt_int(d["output_tokens"]),
                _fmt_usd(d["usd"]),
            )
        )
    g = collected["totals"]
    out.append("")
    out.append(
        "%-40s %8s %11s %8s" % (collected["by"], "turns", "cost", "share%")
    )
    rows = sorted(
        collected["by_dimension"].items(),
        key=lambda kv: kv[1]["usd"],
        reverse=True,
    )
    denom = g["usd"] or 1.0
    for k, d in rows[:20]:
        out.append(
            "%-40s %8s %11s %7.1f%%"
            % (
                str(k)[:40],
                _fmt_int(d["turns"]),
                _fmt_usd(d["usd"]),
                100.0 * d["usd"] / denom,
            )
        )
    if len(rows) > 20:
        out.append("... (+%d rows omitted)" % (len(rows) - 20))
    out.append("")
    out.append(
        "TRANSCRIPTS TOTAL: %s turns, %s in, %s out, %s cache-read, "
        "%s cache-write, %s"
        % (
            _fmt_int(g["turns"]),
            _fmt_int(g["input_tokens"]),
            _fmt_int(g["output_tokens"]),
            _fmt_int(g["cache_read_tokens"]),
            _fmt_int(g["cache_write_5m"] + g["cache_write_1h"]),
            _fmt_usd(g["usd"]),
        )
    )
    out.extend(_routing_lines(collected.get("routing")))
    return out


# ---------------------------------------------------------------------------
# CLI
# ---------------------------------------------------------------------------

_SINCE_RE = re.compile(r"^(\d+)([dh])$")


def _parse_since(expr: str) -> timedelta:
    m = _SINCE_RE.match(expr.strip())
    if not m:
        raise argparse.ArgumentTypeError(
            "invalid --since %r; expected <N>d or <N>h (documented: 30d, 7d, 24h)" % expr
        )
    n = int(m.group(1))
    return timedelta(days=n) if m.group(2) == "d" else timedelta(hours=n)


def _parse_instant(expr: str, flag: str = "--until") -> datetime:
    """An ABSOLUTE ISO-8601 window bound, read by the SAME reader the records use.

    ``_parse_ts`` is what turns a transcript line's ``timestamp`` into
    ``UsageRecord.ts``; parsing a bound with it is what keeps the bound
    and the field it filters from drifting apart -- a ``Z`` suffix, an
    explicit offset and a naive value are all read exactly as a record's
    own stamp would be. BOTH absolute bounds go through this ONE function
    (``--until``, and ``--since-at`` since rail r4), so the two ends of a
    closed window can never be read by two different grammars. Both are
    INCLUSIVE at record resolution: a record stamped exactly at a bound
    is INSIDE the window.
    """
    dt = _parse_ts(expr.strip() if isinstance(expr, str) else expr)
    if dt is None:
        raise argparse.ArgumentTypeError(
            "invalid %s %r; expected an ISO-8601 instant such as "
            "2026-09-02T12:55:05.807Z, 2026-09-02T12:55:05.807+00:00 or "
            "2026-09-02 (a naive value is read as UTC)" % (flag, expr)
        )
    return dt


def build_parser() -> argparse.ArgumentParser:
    p = argparse.ArgumentParser(
        prog="ceo-cost-transcripts.py",
        formatter_class=argparse.RawDescriptionHelpFormatter,
        description=(
            "Cost/token report from harness-native transcripts "
            "(message.usage), because ceo-cost.py / budget-summary.py's "
            "audit-log rollup carries ~0 tokens (PLAN-186 W0; report "
            "docs/research/s339-orchestrator-study/05-finops-routing.md P0-1)."
        ),
        epilog=(
            "Pricing source (default): an EMBEDDED table — report "
            "05-finops-routing.md \xa71.4, itself sourced from "
            "docs/provider-pricing.md's primary table + cache-tier "
            "multiplier section. cost-table.yaml (next to this script) has "
            "NO cache-read/cache-write columns, so it structurally cannot "
            "supply this instrument's pricing shape on its own; when it "
            "parses, its base input/output rates are used and the "
            "Owner-ratified corrections (claude-sonnet-5 -> $2/$10, "
            "2026-09-01, CLAUDE.md commit e47bf5d) are layered on top "
            "ONLY where the file's row actually differs; since "
            "b6dce78 the in-tree file already carries that row, so "
            "the correction is a no-op and the report's pricing: line "
            "says so. Pass --pricing "
            "explicitly to use a different file's rates as-is (no "
            "correction applied). Cache-read multiplier: 0.10x base "
            "(" + _cache_read_exceptions_text() + "). Cache-write multiplier: 1.25x "
            "base at the 5-minute TTL, 2.00x at the 1-hour TTL. "
            "WINDOW: the LOWER bound is either --since (a span measured "
            "back from now) or --since-at <ISO-8601> (an absolute "
            "instant), and --until <ISO-8601> is the UPPER one; all "
            "three filter the SAME record timestamp (UsageRecord.ts), "
            "and the absolute bounds are INCLUSIVE at RECORD resolution "
            "-- a record stamped exactly at a bound is kept, its "
            "neighbour 1 ms away is not. --since-at with --until is a "
            "CLOSED window that is REPRODUCIBLE: re-run tomorrow it "
            "selects the same records, which --since cannot promise "
            "because its bound moves with the wall clock. With the "
            "two-dimension cut (--by role,model) they make PLAN-186 "
            "AC-1's byte-for-byte check reproducible from this CLI "
            "alone, with no external harness."
        ),
    )
    # The window's LOWER bound has exactly TWO spellings and they are
    # mutually exclusive at the PARSER level: a run cannot carry both a
    # relative and an absolute lower bound with one of them silently
    # winning (rail r4 [P1]).
    lower = p.add_mutually_exclusive_group()
    lower.add_argument(
        "--since",
        default="30d",
        type=str,
        help=(
            "LOWER bound of the window, RELATIVE to now: <N>d or <N>h "
            "(default 30d; 7d and 24h also documented). Filters "
            "UsageRecord.ts. Because it is measured back from the wall "
            "clock, the SAME command run later selects a DIFFERENT set "
            "of records -- use --since-at when the window has to be "
            "reproducible."
        ),
    )
    lower.add_argument(
        "--since-at",
        default=None,
        metavar="ISO8601",
        help=(
            "LOWER bound of the window as an ABSOLUTE instant, INCLUSIVE "
            "at record resolution (e.g. 2026-08-03T00:00:00Z; a naive "
            "value is read as UTC). Filters the SAME field --since and "
            "--until do (UsageRecord.ts). Mutually exclusive with "
            "--since: passing both is refused BY NAME (rc 2). Together "
            "with --until it makes a CLOSED, REPRODUCIBLE window -- the "
            "same command tomorrow returns the same numbers. "
            "Default: the relative --since."
        ),
    )
    p.add_argument(
        "--until",
        default=None,
        metavar="ISO8601",
        help=(
            "UPPER bound of the window, INCLUSIVE at record resolution "
            "(e.g. 2026-09-02T12:55:05.807Z; a naive value is read as "
            "UTC). Filters the SAME field --since does (UsageRecord.ts), "
            "so the two bounds always describe one window. Rail r2 "
            "[P2]: the default is NO upper bound, not `now` -- "
            "defaulting to `now` would SILENTLY drop a "
            "clock-skewed future-dated record, and a report that "
            "hides records is worse than one that shows them. "
            "Default: unbounded above."
        ),
    )
    p.add_argument(
        "--project-dir",
        default=None,
        help=(
            "harness transcripts root (the dir holding <session>.jsonl + "
            "<session>/subagents/**). Default: _lib.runtime_paths."
            "runtime_state_dir() — same resolver as "
            "'python3 .claude/hooks/_lib/runtime_paths.py --state-dir'."
        ),
    )
    p.add_argument("--json", action="store_true", help="emit JSON instead of a human table")
    p.add_argument(
        "--by",
        action="append",
        default=None,
        metavar="DIM[,DIM...]",
        help=(
            "breakdown dimension(s) for the report table, comma-separated; "
            "the ORDER given is the grouping order (default: model). "
            "Valid: " + ", ".join(sorted(_GROUP_KEYS)) + ". Example: "
            "--by role,model. A malformed value is refused BY NAME (rc 2), "
            "never silently reduced to one dimension -- and so is a "
            "REPEATED flag (--by role --by model), which argparse's "
            "default `store` action would resolve by keeping only the "
            "LAST value, dropping a dimension without a word."
        ),
    )
    p.add_argument(
        "--pricing",
        default=None,
        metavar="YAML",
        help="cost-table.yaml-shaped file; default: cost-table.yaml next to this script (see epilog)",
    )
    p.add_argument(
        "--assert-routing",
        action="store_true",
        help=(
            "turn the ROUTING INVARIANT verdict (PLAN-186 AC-13: served "
            "model == declared model, VETO archetypes served inside the "
            "floor) into the exit code: 0 GREEN, 1 RED, 3 not proven "
            "(INCONCLUSIVE or VACUOUS). The verdict is evaluated and "
            "printed on EVERY run; without this flag the exit code stays "
            "0 so a cost report is never broken by a routing finding."
        ),
    )
    return p


def _default_project_dir() -> Optional[Path]:
    if _rp is None:
        return None
    try:
        return _rp.runtime_state_dir()
    except Exception:
        return None


def _fmt_usd(v: float) -> str:
    return "$%.2f" % v


def _fmt_int(v: float) -> str:
    return "{:,}".format(int(v))


def _window_label(args: argparse.Namespace) -> str:
    """The window as the report prints it: the lower bound the run really
    APPLIED (relative `--since` or absolute `--since-at`), plus the upper
    one when `--until` was given. Never invents a bound the run did not
    apply -- which is why `main()` blanks `since_raw` under `--since-at`
    instead of leaving the unused `30d` default to be printed here.
    """
    if getattr(args, "since_at_raw", None) is not None:
        lower = "%s (limite inferior ABSOLUTO, inclusivo)" % args.since_at_raw
    else:
        lower = args.since_raw
    if getattr(args, "until_raw", None) is None:
        return lower
    return "%s ate %s (limite superior INCLUSIVO)" % (lower, args.until_raw)


def _human_report(
    args: argparse.Namespace,
    project_dir: Path,
    pricing_result: PricingResult,
    counters: ScanCounters,
    grand: Dict[str, float],
    role_totals: Dict[str, Dict[str, float]],
    group_totals: Dict[str, Dict[str, float]],
    unresolved: Dict[str, Dict[str, float]],
    elapsed_s: float,
    routing: Optional[Dict[str, Any]] = None,
) -> str:
    lines: List[str] = []
    lines.append("ceo-cost-transcripts — janela: %s" % _window_label(args))
    lines.append("project-dir: %s" % project_dir)
    lines.append("pricing: %s" % pricing_result.source)
    lines.append(
        "arquivos: %d assento + %d subagente | linhas: %d vistas, %d candidatas, "
        "%d corrompidas, %d sem timestamp, %d ilegiveis"
        % (
            args.n_top_files,
            args.n_sub_files,
            counters.lines_seen,
            counters.candidate_lines,
            counters.corrupted_lines,
            counters.missing_timestamp,
            counters.unreadable_files,
        )
    )
    lines.append(
        "dedup: %d registros unicos (%d duplicatas descartadas); "
        "sidechain-em-topo ignorado: %d"
        % (counters.deduped_records, args.n_dropped_dupes, counters.sidechain_in_toplevel_skipped)
    )
    if unresolved:
        tot_unresolved_turns = sum(int(v["turns"]) for v in unresolved.values())
        lines.append(
            "AVISO: %d modelo(s) nao resolvido(s) na tabela de precos, %d turnos, "
            "custo reportado como $0 para eles (nunca inventado): %s"
            % (len(unresolved), tot_unresolved_turns, ", ".join(sorted(unresolved.keys())))
        )
    lines.append("")
    lines.append("TOTAIS POR PAPEL")
    header = "%-12s %8s %14s %14s %14s %14s %14s %12s" % (
        "papel", "turnos", "input", "cache_w5m", "cache_w1h", "cache_read", "output", "USD",
    )
    lines.append(header)
    for role in ("assento", "subagent"):
        d = role_totals.get(role, _bucket_totals())
        lines.append(
            "%-12s %8s %14s %14s %14s %14s %14s %12s"
            % (
                role,
                _fmt_int(d["turns"]),
                _fmt_int(d["input_tokens"]),
                _fmt_int(d["cache_write_5m"]),
                _fmt_int(d["cache_write_1h"]),
                _fmt_int(d["cache_read_tokens"]),
                _fmt_int(d["output_tokens"]),
                _fmt_usd(d["usd"]),
            )
        )
    lines.append(
        "%-12s %8s %14s %14s %14s %14s %14s %12s"
        % (
            "TOTAL",
            _fmt_int(grand["turns"]),
            _fmt_int(grand["input_tokens"]),
            _fmt_int(grand["cache_write_5m"]),
            _fmt_int(grand["cache_write_1h"]),
            _fmt_int(grand["cache_read_tokens"]),
            _fmt_int(grand["output_tokens"]),
            _fmt_usd(grand["usd"]),
        )
    )
    lines.append("")
    lines.append("QUEBRA POR --by %s (ordenado por USD desc)" % args.by)
    lines.append("%-40s %8s %12s %8s" % (args.by, "turnos", "USD", "share%"))
    rows = sorted(group_totals.items(), key=lambda kv: kv[1]["usd"], reverse=True)
    grand_usd = grand["usd"] or 1.0
    for k, d in rows[:40]:
        share = 100.0 * d["usd"] / grand_usd
        lines.append("%-40s %8s %12s %7.1f%%" % (str(k)[:40], _fmt_int(d["turns"]), _fmt_usd(d["usd"]), share))
    if len(rows) > 40:
        lines.append("... (+%d linhas omitidas)" % (len(rows) - 40))
    lines.append("")
    routing_lines = _routing_lines(routing)
    if routing_lines:
        lines.extend(routing_lines)
        lines.append("")
    lines.append("tempo de execucao: %.2fs" % elapsed_s)
    return "\n".join(lines)


def _json_report(
    args: argparse.Namespace,
    project_dir: Path,
    pricing_result: PricingResult,
    counters: ScanCounters,
    grand: Dict[str, float],
    role_totals: Dict[str, Dict[str, float]],
    group_totals: Dict[str, Dict[str, float]],
    unresolved: Dict[str, Dict[str, float]],
    elapsed_s: float,
    routing: Optional[Dict[str, Any]] = None,
) -> str:
    payload = {
        # Exactly ONE of `since` / `since_at` is non-null: the bound the
        # run actually applied. The unused `--since` default is reported
        # as null rather than as a window nobody asked for.
        "since": args.since_raw,
        "since_at": args.since_at_raw,
        "until": args.until_raw,
        "by": args.by,
        "project_dir": str(project_dir),
        "pricing_source": pricing_result.source,
        "pricing_used_fallback": pricing_result.used_fallback,
        "files": {"assento": args.n_top_files, "subagent": args.n_sub_files},
        "lines": {
            "seen": counters.lines_seen,
            "candidate": counters.candidate_lines,
            "corrupted": counters.corrupted_lines,
            "missing_timestamp": counters.missing_timestamp,
            "unreadable_files": counters.unreadable_files,
        },
        "dedup": {
            "unique_records": counters.deduped_records,
            "dropped_duplicates": args.n_dropped_dupes,
            "sidechain_in_toplevel_skipped": counters.sidechain_in_toplevel_skipped,
        },
        "unresolved_models": unresolved,
        "grand_total": grand,
        "by_role": role_totals,
        "by_" + args.by: group_totals,
        "routing": routing,
        "elapsed_s": elapsed_s,
    }
    return json.dumps(payload, indent=2, sort_keys=True)


def main(argv: Optional[List[str]] = None) -> int:
    t0 = time.time()
    parser = build_parser()
    args = parser.parse_args(argv)
    args.since_raw = args.since
    try:
        args.since = _parse_since(args.since_raw)
    except argparse.ArgumentTypeError as exc:
        parser.error(str(exc))
        return 2  # pragma: no cover - parser.error() calls sys.exit()

    # The two ABSOLUTE bounds, read by the ONE instant parser. The parser
    # already refuses --since together with --since-at, so at most one
    # lower bound reaches the pipeline; when the absolute one is given,
    # `since_raw` is BLANKED so neither the report header nor the JSON
    # can advertise a `30d` default that was never applied.
    args.since_at_raw = args.since_at
    args.until_raw = args.until
    try:
        args.since_at = (
            _parse_instant(args.since_at_raw, "--since-at")
            if args.since_at_raw is not None
            else None
        )
        args.until = (
            _parse_instant(args.until_raw, "--until")
            if args.until_raw is not None
            else None
        )
    except argparse.ArgumentTypeError as exc:
        parser.error(str(exc))
        return 2  # pragma: no cover - parser.error() calls sys.exit()
    if args.since_at is not None:
        args.since_raw = None

    # `--by` is `action="append"`, so a REPEATED flag arrives as a LIST
    # and can be refused. Rail r4 [P1]: with the default `store` action
    # `--by role --by model` kept only `model` and grouped by one
    # dimension without a word -- the exact silent reduction the help
    # promises never happens.
    by_flags = args.by if args.by is not None else ["model"]
    if len(by_flags) > 1:
        parser.error(
            "--by was given %d times (%s); pass ONE --by with a "
            "comma-separated list (e.g. --by %s) -- a repeated flag would "
            "keep only the LAST value and silently drop a dimension"
            % (
                len(by_flags),
                ", ".join(repr(b) for b in by_flags),
                ",".join(by_flags),
            )
        )
        return 2  # pragma: no cover - parser.error() calls sys.exit()
    try:
        args.by = ",".join(_split_by(by_flags[0]))
    except ValueError as exc:
        parser.error("invalid --by %r: %s" % (by_flags[0], exc))
        return 2  # pragma: no cover - parser.error() calls sys.exit()

    if args.project_dir:
        project_dir = Path(args.project_dir)
    else:
        project_dir = _default_project_dir()
        if project_dir is None:
            sys.stderr.write(
                "ceo-cost-transcripts: could not resolve a default --project-dir "
                "(_lib.runtime_paths import failed); pass --project-dir explicitly.\n"
            )
            return 2

    if not project_dir.is_dir():
        sys.stderr.write("ceo-cost-transcripts: --project-dir does not exist: %s\n" % project_dir)
        return 2

    # ONE lower bound reaches the pipeline: the ABSOLUTE `--since-at` if
    # it was given, otherwise `now - --since`. Before rail r4 only the
    # relative form existed, so a command documented as a `closed window`
    # was not reproducible -- its lower end moved with the wall clock.
    if args.since_at is not None:
        cutoff = args.since_at
        lower_flag = "--since-at %s" % args.since_at_raw
    else:
        cutoff = datetime.now(timezone.utc) - args.since
        lower_flag = "--since %s (= %s)" % (args.since_raw, cutoff.isoformat())
    # A window whose upper bound does not STRICTLY follow its lower one
    # is refused BY NAME instead of printing a report over it: an empty
    # report is indistinguishable from a corpus with no records, and the
    # relative lower bound can climb above a fixed `--until` between two
    # runs of the very same command (rail r4 [P1]).
    if args.until is not None and args.until <= cutoff:
        parser.error(
            "--until %s does not follow the window's LOWER bound %s: the "
            "upper bound must be STRICTLY after the lower one, so this run "
            "is refused rather than reported as an empty corpus"
            % (args.until_raw, lower_flag)
        )
        return 2  # pragma: no cover - parser.error() calls sys.exit()

    # ONE pipeline for the CLI and for the programmatic callers
    # (PLAN-186 W0, AC-1b): a second copy here is how the printed report
    # and ceo-cost.py's block would silently disagree.
    rolled = transcript_rollup(
        project_dir,
        cutoff=cutoff,
        pricing_arg=args.pricing,
        by=args.by,
        until=args.until,
    )
    pricing_result = rolled["pricing_result"]
    counters = rolled["counters"]
    args.n_top_files = rolled["files"]["assento"]
    args.n_sub_files = rolled["files"]["subagent"]
    args.n_dropped_dupes = rolled["dropped_duplicates"]
    unresolved_by_model = rolled["unresolved_models"]
    grand = rolled["grand_total"]
    role_totals = rolled["by_role"]
    group_totals = rolled["by_dimension"]
    routing = rolled["routing"]

    elapsed_s = time.time() - t0

    if args.json:
        out = _json_report(
            args, project_dir, pricing_result, counters, grand, role_totals, group_totals, unresolved_by_model, elapsed_s, routing
        )
    else:
        out = _human_report(
            args, project_dir, pricing_result, counters, grand, role_totals, group_totals, unresolved_by_model, elapsed_s, routing
        )
    print(out)
    # AC-13: the verdict was evaluated and printed above on EVERY run; it
    # only becomes the exit code when the caller asks for the gate.
    return routing_rc(routing) if args.assert_routing else 0


if __name__ == "__main__":
    sys.exit(main())
