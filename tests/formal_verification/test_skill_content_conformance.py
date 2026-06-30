"""Conformance tests for ADR-051 skill-by-reference validator.

Per PLAN-020 Phase 6 §acceptance A3 and ADR-051 §Acceptance closure:
``tests/formal_verification/mutation_fixtures/skill_content/`` must
carry >= 8 mutation fixtures with 100% kill rate against
``check_agent_spawn._validate_skill_reference``.

Each JSON fixture describes a mutation of a valid SKILL REFERENCE
spawn prompt (+ staged SKILL.md file) that MUST be blocked by the
validator with a specific ``REASON_REFERENCE_*`` code.

## Fixture schema

```json
{
  "description": "human-readable mutation description",
  "mutation_class": "S1_regex_bypass | S2_path_validation | S3_content_validation",
  "sub_check_targeted": 1,
  "expected_reason": "reference_<code>",
  "skill_body_variant": "valid | tiny | no_name_key | with_aws_key",
  "skill_rel_path": ".claude/skills/core/test-mutation/SKILL.md",
  "skill_size_pad_to_bytes": null,
  "path_in_prompt_override": null,
  "hash_in_prompt_override": null,
  "prompt_header_override": null,
  "prompt_body_line_override": null
}
```

All override fields are optional; absent fields use defaults. The
test dispatches on ``skill_body_variant`` to pick the body template,
then applies the sized pad / overrides and builds the spawn prompt.

## Harness rules

1. TestEnvContext subclass — temp project_dir + env isolation.
2. Stdlib only.
3. Deterministic — no random content, no monkeypatch.setenv.
4. Tests the real ``check_agent_spawn._validate_skill_reference``
   function (kernel-gated; skipped if unpatched).
"""

from __future__ import annotations

import hashlib
import json
import sys
import unittest
from pathlib import Path
from typing import Any, Dict, Optional, Tuple

# Path bootstrap (mirrors other conformance tests in this tree)
_REPO_ROOT = Path(__file__).resolve().parents[2]
_HOOKS_DIR = _REPO_ROOT / ".claude" / "hooks"
if str(_HOOKS_DIR) not in sys.path:
    sys.path.insert(0, str(_HOOKS_DIR))
_TESTS_DIR = Path(__file__).resolve().parent
if str(_TESTS_DIR) not in sys.path:
    sys.path.insert(0, str(_TESTS_DIR))

from _lib.testing import TestEnvContext  # noqa: E402

import check_agent_spawn  # noqa: E402


_HAS_VALIDATOR = hasattr(check_agent_spawn, "_validate_skill_reference")

_FIXTURE_DIR = (
    Path(__file__).resolve().parent
    / "mutation_fixtures"
    / "skill_content"
)

# Valid SKILL.md body used as the baseline for mutations that want a
# passing file content (so the fixture can mutate exactly one aspect).
# 700+ characters, 520+ non-whitespace bytes — safely clears the 512
# floor. Contains no secret patterns that would trigger redaction.
_VALID_BODY = """---
name: test-skill-mutation-fixture
description: Test skill for ADR-051 skill_content mutation fixtures
---

# Test Skill (Mutation Fixture Baseline)

This is a test SKILL body used by the conformance harness in
tests/formal_verification/mutation_fixtures/skill_content/. It is not
a real skill and does not appear in the framework skill inventory.

## Rules

One: every named spawn requires a persona block and a skill payload.
Two: file assignments prevent collisions between parallel agents.
Three: errors must be explicit and propagate to the caller so the CEO
can strike the agent. Four: tests cover both the happy path and every
documented edge case systematically. Five: skills live under the dot
claude slash skills directory tree and never escape it.

## Usage

Each fixture applies a specific mutation to exactly one aspect of this
baseline — the prompt header, the path, the hash, or the body content.
The conformance test validates that the mutated spawn is blocked with
the expected reason code, proving the validator defends against the
corresponding attack class.
"""


# Body variants used by fixtures that need a non-default file content.

_TINY_BODY = """---
name: tiny
description: tiny stub
---

Too short.
"""

_NO_NAME_KEY_BODY = """---
description: no name key here
owner: someone
---

# Body Has No Name Key in Frontmatter

This fixture exercises sub-check 9 which requires a lowercase
name: key in the YAML frontmatter. The frontmatter parses but has
no name key, so the validator must return reference_missing_frontmatter.

Padding text to ensure the body itself clears the 512 non-whitespace
byte floor so we can isolate the name-key failure rather than also
tripping the byte floor. The fixture is valid in every other way
(path under skills root, filename SKILL.md, no symlink, NFC, under
size cap, parseable frontmatter structure, no secrets). Only the
absence of a lowercase name: key causes the block.
"""

_WITH_AWS_KEY_BODY = """---
name: redaction-hit-fixture
description: AKIAIOSFODNN7EXAMPLE embedded for sub-check 11 test
---

# Redaction-Hit Fixture

This fixture embeds an AWS access key pattern in the frontmatter
description so it is within the first 120 characters of the whitespace-
collapsed content (the cap in _lib.redact.redact_secrets). The regex
for AWS access keys (AKIA + 16 uppercase alphanumerics) matches and
the [AWS_KEY] placeholder token surfaces in the redacted output; the
validator scans for that token and blocks the spawn with reason_code
reference_redaction_hit.

Padding content to push the body past the 512 non-whitespace byte
floor so only sub-check 11 fails. The fixture is otherwise valid:
path under skills root, filename SKILL.md, no symlink, NFC, under
size cap, valid frontmatter with a name key present alongside the
tripwire description, parseable structure end-to-end.
"""


def _select_body(variant: str) -> str:
    """Dispatch fixture body variant to the corresponding template."""
    if variant == "valid":
        return _VALID_BODY
    if variant == "tiny":
        return _TINY_BODY
    if variant == "no_name_key":
        return _NO_NAME_KEY_BODY
    if variant == "with_aws_key":
        return _WITH_AWS_KEY_BODY
    raise ValueError(f"unknown skill_body_variant: {variant!r}")


def _enumerate_fixtures() -> list:
    """Discover and load every mutation fixture JSON under this package."""
    if not _FIXTURE_DIR.is_dir():
        return []
    fixtures = []
    for path in sorted(_FIXTURE_DIR.glob("m*.json")):
        with path.open("r", encoding="utf-8") as fh:
            data = json.load(fh)
        data["_fixture_name"] = path.name
        fixtures.append(data)
    return fixtures


@unittest.skipUnless(
    _HAS_VALIDATOR,
    "check_agent_spawn._validate_skill_reference not yet landed (kernel-gated)",
)
class SkillContentConformanceTest(TestEnvContext):
    """100% kill-rate gate for ADR-051 skill-by-reference validator.

    Each fixture is staged into the temp project_dir and its spawn
    prompt is fed through _validate_skill_reference. The test asserts
    that the validator returned False with the fixture's expected
    reason_code.
    """

    def _stage_skill(
        self,
        rel_path: str,
        body: str,
        pad_to_bytes: Optional[int],
    ) -> Path:
        """Write the body to ``project_dir / rel_path``, padding if asked."""
        target = self.project_dir / rel_path
        target.parent.mkdir(parents=True, exist_ok=True)
        if pad_to_bytes is not None and pad_to_bytes > len(body):
            # Pad with a repeating ASCII filler that doesn't trigger any
            # redaction pattern. A single period per extra byte is fine
            # because `.` is not a secret token and it is non-whitespace
            # so it also counts toward the byte floor.
            filler_len = pad_to_bytes - len(body.encode("utf-8"))
            body = body + ("." * filler_len)
        target.write_text(body, encoding="utf-8")
        return target

    def _build_prompt(
        self,
        path_in_prompt: str,
        hash_in_prompt: str,
        header_override: Optional[str],
        body_line_override: Optional[str],
    ) -> str:
        header = header_override if header_override else "## SKILL REFERENCE"
        body_line = (
            body_line_override
            if body_line_override is not None
            else f"@{path_in_prompt} sha256={hash_in_prompt}"
        )
        return (
            "## AGENT PROFILE\n"
            "Name: test-mutation-fixture\n"
            "\n"
            f"{header}\n"
            "\n"
            f"{body_line}\n"
            "\n"
            "## FILE ASSIGNMENT\n"
            "- MAY edit: (nothing — this is a test)\n"
            "\n"
            "## TASK\n"
            "This prompt is a mutation fixture and must be blocked.\n"
        )

    def _run_fixture(
        self, fixture: Dict[str, Any]
    ) -> Tuple[bool, Optional[str], Optional[str]]:
        body = _select_body(fixture.get("skill_body_variant", "valid"))
        rel_path = fixture.get(
            "skill_rel_path",
            ".claude/skills/core/test-mutation/SKILL.md",
        )
        pad_to = fixture.get("skill_size_pad_to_bytes")

        staged_path = self._stage_skill(rel_path, body, pad_to)
        actual_hash = hashlib.sha256(staged_path.read_bytes()).hexdigest()

        path_in_prompt = fixture.get("path_in_prompt_override") or rel_path
        hash_in_prompt = fixture.get("hash_in_prompt_override") or actual_hash

        prompt = self._build_prompt(
            path_in_prompt=path_in_prompt,
            hash_in_prompt=hash_in_prompt,
            header_override=fixture.get("prompt_header_override"),
            body_line_override=fixture.get("prompt_body_line_override"),
        )

        return check_agent_spawn._validate_skill_reference(
            prompt, repo_root=self.project_dir
        )

    def test_fixture_count_meets_acceptance(self):
        """ADR-051 §Acceptance closure: >= 8 fixtures under this package."""
        fixtures = _enumerate_fixtures()
        self.assertGreaterEqual(
            len(fixtures),
            8,
            msg=(
                f"ADR-051 requires >= 8 skill_content mutation fixtures; "
                f"found {len(fixtures)} under {_FIXTURE_DIR}"
            ),
        )

    def test_fixture_schema_minimum(self):
        """Each fixture declares description + expected_reason + body variant."""
        fixtures = _enumerate_fixtures()
        self.assertGreater(len(fixtures), 0, "no fixtures discovered")
        required_keys = {"description", "expected_reason", "skill_body_variant"}
        for fx in fixtures:
            missing = required_keys - set(fx.keys())
            self.assertEqual(
                missing,
                set(),
                msg=f"{fx['_fixture_name']} missing keys: {missing}",
            )
            self.assertTrue(
                fx["expected_reason"].startswith("reference_"),
                msg=(
                    f"{fx['_fixture_name']} expected_reason "
                    f"{fx['expected_reason']!r} is not a reference_* code"
                ),
            )

    def test_every_fixture_is_blocked_with_expected_reason(self):
        """100% kill rate gate: every fixture blocks with the expected reason."""
        fixtures = _enumerate_fixtures()
        self.assertGreater(len(fixtures), 0, "no fixtures discovered")

        killed = 0
        failures = []
        for fx in fixtures:
            name = fx["_fixture_name"]
            expected = fx["expected_reason"]
            ok, reason, detail = self._run_fixture(fx)
            if ok:
                failures.append(
                    f"{name}: validator returned True (should have blocked)"
                )
                continue
            if reason != expected:
                failures.append(
                    f"{name}: expected reason={expected!r}, "
                    f"got reason={reason!r} (detail={detail!r})"
                )
                continue
            killed += 1

        self.assertEqual(
            killed,
            len(fixtures),
            msg="FIXTURE FAILURES (kill rate < 100%):\n  "
            + "\n  ".join(failures),
        )


if __name__ == "__main__":
    unittest.main()
