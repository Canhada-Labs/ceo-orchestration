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


# Executable definitions bind directly to this facade's globals, preserving
# monkeypatches on public/private names without mutating imported templates.
from _lib._cost_transcripts_parts import install as _install_parts

_install_parts(globals(), (
    "pricing", "records", "routing_helpers", "routing", "rollup", "cli",
))

if __name__ == "__main__":
    sys.exit(main())
