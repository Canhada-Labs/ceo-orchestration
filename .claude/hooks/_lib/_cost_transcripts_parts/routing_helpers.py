"""Extracted cost-transcripts implementation: routing_helpers."""
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


