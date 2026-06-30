"""Mutation fixtures for ADR-051 skill-by-reference conformance harness.

Each ``m<NNN>_*.json`` file in this directory is a mutation of a
valid ``## SKILL REFERENCE`` spawn prompt + staged ``SKILL.md`` file
that SHOULD be blocked by
``check_agent_spawn._validate_skill_reference`` (fail-CLOSED).

The companion test ``test_skill_content_conformance.py`` iterates
every fixture, stages the skill file under a temp project root,
builds the spawn prompt with the fixture's mutation applied, calls
the validator, and asserts it returned the expected reason code.

100% kill rate is the acceptance target per ADR-018 §mutation kill
contract: every fixture is a mutation that MUST be caught by the
validator. If any fixture slips through (i.e. ``_validate_skill_reference``
returns ``True`` or returns a different reason code than expected),
the conformance test fails — which proves either the validator has
a gap or the fixture is invalid. Both require maintainer attention.
"""

from __future__ import annotations
