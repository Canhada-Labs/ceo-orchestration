#!/usr/bin/env python3
"""check-policy-drift — STUB for PLAN-014 Phase 0.4.

Full implementation lands in Phase A alongside `_lib/policy.py`. This
stub LOCKS the algorithm choice per ADJ-005 / PLAN-014 debate C2:

    algorithm = YAML-canonical-form hash + fixture-corpus semantic check

1. **YAML-canonical hash:** parse each `.claude/policies/*.yaml` into a
   Python dict via the hand-rolled stdlib subset parser (Phase A.3),
   serialize with `json.dumps(..., sort_keys=True, separators=(',', ':'),
   ensure_ascii=False)` — produces a canonical byte string independent
   of source whitespace, comment placement, or key ordering. SHA-256
   digest is the policy identity.
2. **Fixture-corpus semantic check:** every policy file MUST have a
   sibling `<name>.fixtures.jsonl` under `.claude/policies/fixtures/`
   enumerating `(input_payload, expected_decision, expected_reason)`
   rows. The drift check runs each fixture through the engine; a
   mismatch fails with exit 1 (drift) regardless of canonical-hash
   stability — a semantically-equivalent rewrite MAY change the hash
   but MUST preserve all fixture outcomes.

Exit codes: 0 clean, 1 drift, 2 parse error (same contract as
`check-flip-criteria-drift.py`).

Stdlib only; Python >=3.9. Full body in Phase A.
"""

from __future__ import annotations

import argparse
import sys
from pathlib import Path


STUB_MESSAGE = (
    "check-policy-drift: STUB (PLAN-014 Phase 0.4). "
    "Full implementation in Phase A. Algorithm: "
    "YAML-canonical-hash + fixture-corpus semantic check (ADJ-005)."
)


def main(argv: list[str] | None = None) -> int:
    """CLI entrypoint — advisory drift check between policy.py DSL and SPEC."""
    parser = argparse.ArgumentParser(prog="check-policy-drift", description=STUB_MESSAGE)
    parser.add_argument(
        "--policies-dir",
        type=Path,
        default=Path(".claude/policies"),
        help="Directory containing *.yaml policy files (default: .claude/policies)",
    )
    parser.add_argument(
        "--fixtures-dir",
        type=Path,
        default=Path(".claude/policies/fixtures"),
        help="Directory containing <name>.fixtures.jsonl per policy",
    )
    parser.add_argument("--verbose", action="store_true")
    args = parser.parse_args(argv)

    # Stub: exit 0 if policies dir doesn't exist yet (Phase A hasn't run).
    if not args.policies_dir.exists():
        print(f"{STUB_MESSAGE} (policies dir absent — Phase A not landed yet)")
        return 0

    # Phase A will populate: walk policies, compute canonical hash,
    # validate against pinned hash in `.claude/policies/.drift-manifest.json`,
    # run fixtures through engine, diff decisions.
    print(STUB_MESSAGE)
    return 0


if __name__ == "__main__":
    sys.exit(main())
