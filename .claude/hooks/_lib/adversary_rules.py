#!/usr/bin/env python3
"""Adversary local-rules engine (PLAN-133 E1 / Goose-harvest).

A from-scratch stdlib re-implementation of the Goose ``ToolInspector``
adversary-reviewer *mechanism* (rite §2 — nothing fetched/run from the aaif-goose
fork). LOCAL-RULES-ONLY: this engine makes NO model call. It parses deny/ask rules
from a markdown ruleset (``.claude/adversary.md``) and evaluates a Bash command
against them deterministically.

Security contract (the consumer ``check_adversary.py`` enforces the I/O side):
  - The ruleset is UNTRUSTED DATA. This module never executes anything from it.
  - Every ``regex`` rule is anchored + length-bounded + compiled with a wall-clock
    step budget (SIGALRM itimer, same idiom as ``secret_patterns``); a runaway
    regex fails OPEN (rule skipped) — never hangs the hook.
  - The :class:`AdversaryHit` returned carries ONLY ``rule_id`` + a closed-enum
    ``rule_class`` + a closed-enum ``decision``. It NEVER carries the command text,
    the matched substring, or any environment value (no-value-echo).
  - Default-OFF: in advisory mode every hit's ``decision`` is ``"advisory"``
    (detect + emit, caller ALLOWS). In enforce mode the rule's own ``deny``/``ask``
    is returned.
"""

from __future__ import annotations

import re
import signal
import threading
from dataclasses import dataclass
from typing import List, Optional

# Closed enums — mirrored as literal frozensets in audit_emit.py
# (_ADVERSARY_RULE_CLASSES / _ADVERSARY_DECISIONS) so audit_emit has no import-time
# dependency on this module; a drift between them is caught by a dedicated test.
RULE_CLASSES = frozenset(
    {"destructive", "exfiltration", "privilege", "tampering", "other"}
)
RULE_ACTIONS = frozenset({"deny", "ask"})
ADVERSARY_DECISIONS = frozenset({"deny", "ask", "advisory", "allow"})

# Default-OFF behavioral flag (doctrine #1). The CALLER reads it from the
# import-time trusted_env snapshot (NOT live os.environ).
ADVERSARY_ENFORCE_FLAG = "CEO_ADVERSARY"

# Hard caps (the caller enforces the ruleset-file size cap before calling).
MAX_RULESET_BYTES = 64 * 1024
MAX_REGEX_LEN = 512
REGEX_BUDGET_SECONDS = 0.05  # per-rule wall-clock budget (SIGALRM)

_RULE_BLOCK_RE = re.compile(r"```adversary-rule\n(.*?)```", re.DOTALL)
_FIELD_RE = re.compile(r"^([a-z_]+):\s*(.*)$")


@dataclass(frozen=True)
class Rule:
    rule_id: str
    rule_class: str
    action: str
    matcher: str
    is_regex: bool
    compiled: Optional["re.Pattern[str]"]


@dataclass(frozen=True)
class AdversaryHit:
    """The ONLY thing that reaches audit_emit. Closed-enum + rule_id ONLY."""
    rule_id: str
    rule_class: str
    decision: str


class _ScanBudgetExceeded(Exception):
    pass


def _budget_guard_available() -> bool:
    """True iff a SIGALRM itimer budget can actually be installed here.

    Requires (a) the MAIN thread — ``signal.signal`` raises ValueError on any
    other thread — AND (b) ``signal.SIGALRM`` + ``signal.setitimer`` to exist
    (absent on Windows). When this is False the caller MUST NOT run an untrusted
    regex unbounded; it skips regex-rule evaluation entirely (fail-OPEN).
    """
    if threading.current_thread() is not threading.main_thread():
        return False
    return hasattr(signal, "SIGALRM") and hasattr(signal, "setitimer")


def _budget_guard(seconds: float):
    """Install a SIGALRM itimer guard (mirrors secret_patterns). Best-effort:
    on a platform/thread without SIGALRM the guard is a no-op (the anchored,
    length-bounded regexes are already linear, so this is defense-in-depth)."""
    try:
        def _h(signum, frame):
            raise _ScanBudgetExceeded()
        prev = signal.signal(signal.SIGALRM, _h)
        signal.setitimer(signal.ITIMER_REAL, seconds)
        return prev
    except (ValueError, AttributeError, OSError):
        return None


def _clear_budget(prev) -> None:
    try:
        signal.setitimer(signal.ITIMER_REAL, 0)
        if prev is not None:
            signal.signal(signal.SIGALRM, prev)
    except (ValueError, AttributeError, OSError):
        pass


def parse_ruleset(text: str) -> List[Rule]:
    """Parse fenced adversary-rule blocks into Rules. Never raises.

    Skips (fail-open per rule) any block that: is missing a required field; has a
    ``class``/``action`` outside the closed enum; declares BOTH ``match`` and
    ``regex``; has a ``regex`` over the length cap or that won't compile.
    """
    rules: List[Rule] = []
    if not text or len(text.encode("utf-8", "replace")) > MAX_RULESET_BYTES:
        return rules
    for block in _RULE_BLOCK_RE.findall(text):
        fields = {}
        for line in block.splitlines():
            m = _FIELD_RE.match(line.strip())
            if m:
                fields[m.group(1)] = m.group(2).strip()
        rid = fields.get("id")
        rclass = fields.get("class")
        action = fields.get("action")
        if not rid or rclass not in RULE_CLASSES or action not in RULE_ACTIONS:
            continue
        if "regex" in fields and "match" in fields:
            continue
        if "regex" in fields:
            src = fields["regex"]
            if not src or len(src) > MAX_REGEX_LEN:
                continue
            try:
                compiled = re.compile(src)
            except re.error:
                continue
            rules.append(Rule(rid, rclass, action, src, True, compiled))
        elif "match" in fields:
            src = fields["match"]
            if not src:
                continue
            rules.append(Rule(rid, rclass, action, src, False, None))
    return rules


class AdversaryEngine:
    """Deterministic local-rules deny/ask gate. Pure; never raises."""

    def __init__(self, rules: List[Rule], enforce: bool) -> None:
        self._rules = rules
        self._enforce = enforce

    def evaluate(self, command: str) -> Optional[AdversaryHit]:
        """Return the FIRST matching rule's hit, or None.

        ``decision``: enforce → the rule's own ``deny``/``ask``; advisory
        (default-OFF) → ``"advisory"``. A per-rule budget overrun → that rule is
        skipped (fail-open), evaluation continues with the next rule.
        """
        if not command:
            return None
        # The per-rule wall-clock budget relies on a SIGALRM itimer, which can
        # only be armed on the main thread of a Unix process. If it is NOT
        # available here (non-main thread OR non-Unix), an untrusted regex from
        # the .md ruleset would run UNBOUNDED and could hang the hook — so we
        # SKIP regex-rule evaluation entirely and fail-OPEN (literal-`match`
        # rules, which are O(n) substring tests, still run).
        regex_budget_ok = _budget_guard_available()
        for rule in self._rules:
            matched = False
            if rule.is_regex:
                if not regex_budget_ok:
                    continue  # fail-OPEN: cannot bound this regex → skip the rule
                prev = _budget_guard(REGEX_BUDGET_SECONDS)
                try:
                    matched = rule.compiled.search(command) is not None  # type: ignore
                except _ScanBudgetExceeded:
                    matched = False  # fail-open on this rule
                except Exception:
                    matched = False
                finally:
                    _clear_budget(prev)
            else:
                try:
                    matched = rule.matcher in command
                except Exception:
                    matched = False
            if matched:
                decision = rule.action if self._enforce else "advisory"
                return AdversaryHit(rule.rule_id, rule.rule_class, decision)
        return None
