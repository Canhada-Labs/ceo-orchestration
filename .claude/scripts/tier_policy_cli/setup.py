"""Packaging shim for tier_policy_cli (F-6-6.9-a73aa784 PLAN-113 W7-OPS).

Provides a ``ceo-tier-policy`` console script entry-point so the CLI can be
installed via ``pip install -e .claude/scripts/tier_policy_cli/`` in adopter
projects without requiring the user to know the direct invocation path.

Install (editable, from repo root):

    pip install -e .claude/scripts/tier_policy_cli/

Or as part of ceo-orchestration framework install.sh (future work).

Stdlib-only package; no third-party deps.
"""

from __future__ import annotations

from setuptools import setup

setup(
    name="ceo-tier-policy",
    version="0.1.0",
    description="ceo-orchestration dynamic tier-policy CLI (PLAN-043)",
    packages=["tier_policy_cli"],
    package_dir={"tier_policy_cli": "."},
    python_requires=">=3.9",
    entry_points={
        "console_scripts": [
            "ceo-tier-policy=tier_policy_cli.cli:main",
        ],
    },
    # stdlib-only per ADR-002; no install_requires.
)
