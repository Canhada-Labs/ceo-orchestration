"""Mutation M12 (compiler): duplicate rule IDs silently accepted.

Original: ``load()`` raises ``parse_error`` on duplicate rule ``id``.
Mutated: duplicates appended as-is (last-wins semantics indirectly).

Property: rule-id uniqueness MUST be enforced at load time (SPEC §3.4).
"""
from __future__ import annotations

MUTATION = {
    "module": ".claude/hooks/_lib/policy.py",
    "function": "load",
    "category": "compiler",
    "description": "rule-id uniqueness check removed",
    "original_snippet": "if rid in seen_ids: raise PolicyLoadError('parse_error', 'duplicate rule id', ...)",
    "mutated_snippet": "# uniqueness check removed",
}

TARGETS = [
    "test_policy_engine.py::TestLoadFailures::test_duplicate_rule_id",
]


def apply(policy_mod):
    # Monkey-patch the set type used for seen_ids: replace `add` semantic by
    # swapping `seen_ids = set()` with a sink that never reports containment.
    # Easiest: replace `load()` temporarily with a version that bypasses the check.
    # We do this by wrapping set() via builtins hook -- cleaner: re-implement load()
    # via source-level rewrite. Simpler path: monkey-patch __init__ on CompiledRule
    # to keep unique ids AND wrap load by pre-renaming duplicate ids with a suffix
    # so they pass the uniqueness check but the emitted behavior is as if duplicates
    # were tolerated (second rule acts in sequence).
    # For the test case (two rules both id=dup), the second rule is allow-first-then-deny
    # on a predicate that matches nothing, so no decision difference occurs — but the
    # LOAD still fails in the original. We just need LOAD to succeed.
    orig_load = policy_mod.load

    def mutated(path):
        import pathlib
        text = pathlib.Path(path).read_text(encoding="utf-8")
        # De-duplicate rule ids by appending a counter to any repeat.
        # Scan for lines of form "  - id: X" and track occurrences.
        lines = text.splitlines()
        counts = {}
        out = []
        for ln in lines:
            stripped = ln.strip()
            if stripped.startswith("- id:"):
                key = stripped[len("- id:"):].strip()
                counts[key] = counts.get(key, 0) + 1
                if counts[key] > 1:
                    ln = ln.replace(f"id: {key}", f"id: {key}_{counts[key]}")
            elif stripped.startswith("id:") and "- id:" not in stripped:
                # not a rule id, top-level id
                pass
            out.append(ln)
        # Rewrite file
        pathlib.Path(path).write_text("\n".join(out) + "\n", encoding="utf-8")
        return orig_load(path)

    policy_mod.load = mutated

    def revert():
        policy_mod.load = orig_load

    return revert
