"""Mutation M11 (compiler): rule with absent ``predicate`` silently treated as no-op.

Original: ``load()`` raises ``predicate_missing`` if rule lacks ``predicate``.
Mutated: missing predicate defaults to ``{"eq": {"field": "__never__", "value": 1}}``.

Property: rules MUST declare a predicate; absence MUST fail at load (SPEC §3.4).
"""
from __future__ import annotations

MUTATION = {
    "module": ".claude/hooks/_lib/policy.py",
    "function": "load",
    "category": "compiler",
    "description": "rule without predicate silently accepted (no-op predicate)",
    "original_snippet": "if pred_raw is None: raise PolicyLoadError('predicate_missing', ...)",
    "mutated_snippet": "if pred_raw is None: pred_raw = {'eq': {'field': '__never__', 'value': 1}}",
}

TARGETS = [
    "test_policy_engine.py::TestErrorModel::test_predicate_missing_when_absent",
]


def apply(policy_mod):
    orig_load = policy_mod.load

    def mutated_load(path):
        # Pre-inject a dummy predicate into any rule that lacks one. This
        # mimics the buggy-code behavior where the load-time gate was
        # replaced by a silent default.
        import pathlib
        import re as _re
        p = pathlib.Path(path)
        text = p.read_text(encoding="utf-8")
        # Find rule blocks ("  - id: …") that don't have a "predicate:" key.
        # Simple heuristic: insert a predicate for each rule that has an id
        # but no predicate line in the next ~10 lines.
        lines = text.splitlines()
        out = []
        i = 0
        while i < len(lines):
            ln = lines[i]
            out.append(ln)
            stripped = ln.strip()
            if stripped.startswith("- id:") and i + 1 < len(lines):
                # Lookahead: does this rule block (until next "- id:" or dedent
                # to same level) contain "predicate:"?
                rule_indent = len(ln) - len(ln.lstrip())
                found_pred = False
                j = i + 1
                while j < len(lines):
                    nxt = lines[j]
                    nxt_stripped = nxt.strip()
                    if not nxt_stripped:
                        j += 1
                        continue
                    nxt_indent = len(nxt) - len(nxt.lstrip())
                    if nxt_indent <= rule_indent:
                        break
                    if nxt_stripped.startswith("predicate:"):
                        found_pred = True
                        break
                    j += 1
                if not found_pred:
                    pad = " " * (rule_indent + 2)
                    out.append(f"{pad}predicate:")
                    out.append(f"{pad}  eq: {{field: __never__, value: 1}}")
            i += 1
        new_text = "\n".join(out) + "\n"
        if new_text != text:
            p.write_text(new_text, encoding="utf-8")
        return orig_load(p)

    policy_mod.load = mutated_load

    def revert():
        policy_mod.load = orig_load

    return revert
