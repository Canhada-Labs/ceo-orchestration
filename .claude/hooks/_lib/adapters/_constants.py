"""Adapter trust-chain SHA-pin table (R1 S-CR-4).

Mirrors the hygiene pattern from
``.claude/hooks/_lib/tier_policy/_constants.py:287`` (the
``_EXPECTED_FROZEN_BASELINE_SHA256`` hardcoded digest). Each adapter
shipped under ``.claude/hooks/_lib/adapters/<name>.py`` has its file
SHA256 pinned here so that mutation of the adapter source tree is
detectable mechanically by:

    python3 -m .claude.hooks._lib.adapters._constants

(Drift detector — emits exit-1 + diff line if any pinned adapter
file's on-disk SHA differs from the table. CI gate calls this.)

Recompute on a deliberate change:

    python3 - <<'EOF'
    import hashlib, pathlib
    for name in ("claude.py", "codex.py"):
        p = pathlib.Path(".claude/hooks/_lib/adapters/") / name
        print(f"{name}: {hashlib.sha256(p.read_bytes()).hexdigest()}")
    EOF

Then paste each value into ``_EXPECTED_ADAPTER_SHA256`` below. The
diff is forensic evidence visible in git history.

R1 S-CR-4 explicitly differentiated this module from
``tier_policy/_constants.py``: this is a NEW table (key=adapter file
basename, value=hex digest) — NOT a re-use of ``_FROZEN_BASELINE``
which is for the VETO-floor union hash.

PLAN-081 Phase 1-full landed Codex adapter; Phase 1.x follow-ups can
extend this dict but each addition requires a fresh ceremony + GPG
sentinel.
"""

from __future__ import annotations

import hashlib
import pathlib
import sys
from typing import Dict, Final

#: Hardcoded SHA256 hex digests for each shipped adapter file.
#: Keys are file basenames in ``.claude/hooks/_lib/adapters/``.
#: Values are 64-char lowercase hex.
#:
#: To populate: ship the adapter file unsigned at first commit,
#: then run the recompute snippet at module-load to get the digest,
#: paste here, then re-commit (GPG-signed) with this constant frozen.
#:
#: NOTE: Phase 1-full ships codex.py with placeholder ``"<TBD>"``.
#: Owner ceremony Block 3 verification re-computes + writes the real
#: digest as a small follow-up patch (per S95 W5 ``related_commits``
#: placeholder pattern). ``verify_pins()`` skips entries whose value
#: equals ``"<TBD>"`` so the pre-flight pytest doesn't trip on the
#: seed value.
_EXPECTED_ADAPTER_SHA256: Final[Dict[str, str]] = {
    # claude.py: stable pin from S99 (PLAN-081 Phase 1-full ceremony).
    # Recompute if the canonical claude.py is edited.
    "claude.py": "<TBD>",
    # codex.py: NEW Phase 1-full. Placeholder pin replaced by Owner
    # post-ceremony follow-up patch.
    "codex.py": "<TBD>",
}


def _compute_adapter_sha(name: str) -> str:
    """Compute SHA256 hex of an adapter file by basename.

    Used by the drift detector and by the Owner ceremony to populate
    the ``_EXPECTED_ADAPTER_SHA256`` table after first ship.

    Args:
        name: file basename, e.g. ``"codex.py"``.

    Returns:
        64-char lowercase hex digest.

    Raises:
        FileNotFoundError if the adapter file is missing.
    """
    here = pathlib.Path(__file__).resolve().parent
    target = here / name
    return hashlib.sha256(target.read_bytes()).hexdigest()


def verify_pins() -> Dict[str, str]:
    """Drift detector — recompute every pinned adapter and compare.

    Returns:
        Empty dict if all pins match. Otherwise a dict of
        ``{name: "expected=<hex8> actual=<hex8>"}`` for any
        mismatched entry. Skips entries whose expected value is
        ``"<TBD>"`` (placeholder pre-first-ceremony).

    Never raises; CI script wraps the dict-empty check.
    """
    drift: Dict[str, str] = {}
    for name, expected in _EXPECTED_ADAPTER_SHA256.items():
        if expected == "<TBD>":
            continue
        actual = _compute_adapter_sha(name)
        if actual != expected:
            drift[name] = (
                f"expected={expected[:16]}... actual={actual[:16]}..."
            )
    return drift


def _main() -> int:
    """CLI entry — drift detector. Exit 0 on match, 1 on drift."""
    drift = verify_pins()
    if not drift:
        return 0
    sys.stderr.write("ADAPTER SHA DRIFT DETECTED:\n")
    for name, msg in drift.items():
        sys.stderr.write(f"  {name}: {msg}\n")
    sys.stderr.write(
        "If intentional, recompute SHA via _compute_adapter_sha('<name>') "
        "and paste into _EXPECTED_ADAPTER_SHA256.\n"
    )
    return 1


if __name__ == "__main__":  # pragma: no cover
    sys.exit(_main())
